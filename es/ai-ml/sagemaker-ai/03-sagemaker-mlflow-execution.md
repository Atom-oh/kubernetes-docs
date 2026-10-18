# Parte 3: Ejecución de SageMaker AI y MLflow

Para seguir una ruta práctica de aprendizaje, comienza con el [taller de entrenamiento QLoRA](05-qlora-finetuning-workshop.md). Este capítulo documenta la implementación existente y el contrato operativo.

> **Última actualización**: September 12, 2026

## Aviso de ejecución

**La ruta de ejecución con GPU confirmada en el repositorio está bloqueada actualmente porque su imagen llegó al fin del período de parches.** El catálogo oficial indica `2026-08-06` como fecha de fin del período de parches para `2.8.0-gpu-py312-cu129-ubuntu22.04-sagemaker`. `src/runtime_contract.py` comprueba este límite antes de las verificaciones previas, el aprovisionamiento, el envío de Training Jobs, la creación de EKS y el entrenamiento. Actualiza la imagen, `torch` y el grupo de dependencias a la vez, y valida una prueba rápida con GPU; eliminar solamente la comprobación de la fecha no constituye una actualización del entorno de ejecución.

Este capítulo describe el contrato corregido en `examples/ai-ml/qwen-pii-finetuning/`. Las pruebas locales, las vistas previas de solicitudes y la limpieza de recursos propios siguen disponibles. El experimento de AWS del 1 de septiembre de 2026 **se detuvo antes de enviar la solicitud de entrenamiento**. Esta revisión tampoco creó recursos de AWS ni realizó entrenamiento con GPU.

AWS recomienda **MLflow Apps** para las nuevas implementaciones de MLflow administradas de SageMaker. Los Tracking Servers existentes son un recurso distinto. La documentación actual de Apps indica MLflow `3.10`; este ejemplo histórico fija el cliente y el servidor de EKS en `3.1.4`. Una exportación local correcta de artefactos con la versión 3.1.4 no valida la compatibilidad completa con la App administrada. Incluye esa combinación en la validación de la actualización del entorno de ejecución.

## Ocho pasos de la ruta administrada

### 1. Verificaciones previas de solo lectura

Ejecuta estos comandos con el **entorno virtual de Python 3.12 activado** y las dependencias del README del paquete instaladas.

```bash
cd examples/ai-ml/qwen-pii-finetuning
export AWS_REGION=ap-northeast-2
python3 src/runtime_contract.py --check-execution
```

Hoy este comando debería fallar con una explicación sobre el fin del período de parches. Después de actualizar el ejemplo a un entorno de ejecución compatible, establece `EXPECTED_ACCOUNT_ID`, `DATAZONE_DOMAIN_ID`, `DATAZONE_PROJECT_PROFILE_ID` y `DATAZONE_OWNER_GROUP_ID`, verificados por un administrador, y luego ejecuta `./launch/aws/preflight.sh`. Estas variables contienen identificadores de recursos, no contraseñas ni claves de cuentas de servicio.

Las verificaciones previas comprueban las herramientas, la identidad que llama, la región, las cuotas, DLC y las colisiones con experimentos existentes. No reconstruyen un dominio, perfil o grupo a partir de un nombre visible o una cadena de rol STS. Una lista vacía no demuestra ausencia universal ni permisos para creaciones posteriores. Revisa la propiedad de los recursos que compartan un prefijo; no los elimines indiscriminadamente.

### 2. Crear el paquete de código fuente

```bash
./launch/aws/build_source_bundle.sh
```

El paquete incluye `src/*.py`, `config/experiment.yaml`, `requirements.lock` y un `requirements.txt` idéntico. No incluye datos ni archivos de credenciales locales de forma recursiva. No detecta valores sensibles insertados directamente en el código fuente o la configuración, así que inspecciona el paquete. Su SHA-256 identifica **esa compilación**; no se garantiza que las marcas de tiempo de tar sean reproducibles.

### 3. Crear la MLflow App y el proyecto de Unified Studio

Este paso **modifica AWS y crea recursos facturables**; solo está disponible después de validar el entorno de ejecución y los permisos.

```bash
./launch/aws/provision.sh
```

Crea un bucket para experimentos, roles de ejecución y de MLflow, una MLflow App y un proyecto con membresía de propietario. El bucket usa Block Public Access, AES-256 y control de versiones; las políticas de IAM se comprueban con Access Analyzer. El estado de disponibilidad de la App es `Created`/`Updated`. El estado `ACTIVE` del proyecto no demuestra que se hayan implementado correctamente todos los entornos del proyecto.

El inventario privado distingue la intención de creación de las respuestas satisfactorias. Una colisión de nombres o la pérdida de una respuesta no autoriza a eliminar recursos por nombre. La limpieza de errores actúa sobre recursos cuya propiedad está confirmada; una creación de estado desconocido requiere conciliación. Un proceso o una instancia detenidos a la fuerza quizá nunca ejecuten una trampa de shell.

### 4. Cargar el conjunto de datos

Crea el bucket y el inventario antes de cargar los datos. Valida las cinco entradas:

```bash
python3 -m launch.aws.upload_inputs \
  --inventory results/resource-inventory.json
# Actual S3 upload and SHA-256 readback verification:
python3 -m launch.aws.upload_inputs \
  --inventory results/resource-inventory.json --execute
```

Las entradas son `generated/source.tar.gz`, `data/{train,validation,test}.jsonl` y `data/dataset-manifest.json`. El helper comprueba los hashes de las particiones, que el bucket pertenezca a la cuenta y las etiquetas del experimento; luego escribe en los prefijos específicos de ejecución `qwen-pii/<experiment-id>/source/` y `dataset/`. Lee los objetos para comparar sus SHA-256. Este pequeño ejemplo sintético limita cada archivo a 64 MiB. Una carga fallida puede dejar algunos objetos, así que conserva el inventario.

Usa identificadores y hashes en los registros operativos privados. Las URL prefirmadas otorgan acceso y no deben publicarse en documentación pública ni en registros.

### 5. Enviar la solicitud de SageMaker Training Job

```bash
python3 -m launch.sagemaker_train \
  --mode smoke --inventory results/resource-inventory.json
```

De forma predeterminada, esto escribe un archivo JSON con un nombre único en `results/previews/`, sin enviar nada a AWS. No sobrescribe los archivos enviados `<job-name>-request.json` ni `<job-name>-job.json`. Después de validar un entorno de ejecución compatible, añade `--execute` para enviar la solicitud. La ejecución completa requiere por separado `--mode full --execute`. El iniciador no aprueba automáticamente las evidencias de la prueba rápida ni los hashes de entrada.

La configuración se lee desde `/opt/ml/code/config/experiment.yaml` en el paquete de código fuente. Los cuatro archivos de datos se encuentran en `/opt/ml/input/data/dataset/`. Crea la configuración local `--config` y el paquete a partir de la misma fuente para que coincidan.

Antes del envío, el iniciador reserva tanto la solicitud como el registro del job con el bloqueo compartido de la herramienta de limpieza. Si la creación de un job se completó correctamente, un fallo o una interrupción durante la supervisión activa un intento de detenerlo. `stop_requested` no significa que se haya confirmado la terminación. Concilia el estado de AWS y la propiedad después de `submission_unknown`, `stop_unconfirmed` o la pérdida del host; no sobrescribas un registro existente ni una solicitud huérfana para volver a enviarla.

La configuración histórica especifica un `ml.g6e.4xlarge`, 300 GiB, 10 pasos para la prueba rápida y 80 para la completa, y `MaxRuntimeInSeconds: 10800`. Ese límite no limita el costo total, incluidos la terminación, las cargas, MLflow, S3 y otros recursos.

### 6. Puerta de control para prueba rápida/completa

Antes de volver a habilitar la ejecución, valida la imagen compatible, las dependencias y la combinación de MLflow. Luego inspecciona el estado terminal de la prueba rápida, los hashes del conjunto de datos, las métricas y los archivos del adaptador. Revisa los registros y MLflow para detectar texto de origen, valores de entidades, correspondencias o completados sin procesar. **Una lista permitida de nombres de artefactos no demuestra que su contenido sea seguro.** Este procedimiento no implica que se haya implementado un escáner automático de PII.

### 7. Exportar resultados agregados

| Archivo | Significado |
|---|---|
| `dataset-manifest.json` | ajustes del generador, cantidades y hashes de las particiones |
| `resolved-config.json` | ajustes reales, entorno y pasos |
| `dependency-versions.json` | versiones instaladas observadas; no garantiza un bloqueo completo |
| `baseline-metrics.json`, `tuned-metrics.json` | evaluación agregada en la misma partición de prueba |
| `run-summary.json` | tiempos por fase, métricas e inventario del adaptador |
| `adapter/adapter_config.json`, `adapter/adapter_model.safetensors` | adaptadores finales conservados en MLflow |

La salida de SageMaker `/opt/ml/model` y los artefactos de MLflow se almacenan en ubicaciones distintas. Descarga y verifica los resultados necesarios antes de eliminar el bucket o la App. Revisa el contenido del adaptador y los permisos de acceso antes de compartirlo. No se exportan predicciones sin procesar, correspondencias de tokens ni puntos de control intermedios.

`peak_gpu_memory_bytes` es el pico de memoria asignada por PyTorch en el dispositivo CUDA predeterminado, después de un reinicio del contador posterior a la carga del modelo. No es la memoria total de la GPU, el pico durante la carga ni una suma entre dispositivos. No hay resultados de entrenamiento que justifiquen publicar mejoras de rendimiento o una comparación de costos.

### 8. Desmantelamiento y verificación

```bash
./launch/aws/teardown.sh
./launch/aws/verify_cleanup.sh
```

Primero comprueba y detén los Training Jobs registrados. Si existen registros de entrenamiento, el desmantelamiento vuelve a detenerse para impedir que se elimine su bucket de artefactos antes de exportarlos. Solo después de conservar por separado los artefactos necesarios de SageMaker/MLflow, continúa con:

```bash
./launch/aws/teardown.sh results/resource-inventory.json \
  --discard-training-artifacts
```

Esta opción no realiza una copia de seguridad. El desmantelamiento compartido también se detiene mientras queden recursos propios de EKS. Completa primero la exportación/eliminación verificada mediante la ruta de EKS o la recuperación manual que se describe más abajo. Después limpia los recursos confirmados como propios: App, proyecto, S3 e IAM. Los errores `AccessDenied` de AWS, los fallos de transporte, los tiempos de espera de eliminación y los errores de S3 por objeto no deben considerarse prueba de ausencia. Los inventarios antiguos que no contengan evidencia de propiedad requieren conciliación por parte de un administrador. Esta herramienta no elimina el grupo de registros compartido de TrainingJobs ni los recursos no relacionados.

Los estados restantes o desconocidos hacen que la verificación falle. El éxito se limita a la cuenta, región, inventario y comprobaciones consultados; no demuestra que la cuenta de AWS esté vacía. Una limpieza incompleta o un clúster conservado pueden seguir generando cargos.

## Ruta de comparación de EKS + MLflow

Después de actualizar el entorno de ejecución, los puntos de entrada son `./launch/eks/run.sh smoke` y, tras una revisión independiente, `./launch/eks/run.sh full`. Hoy se detienen en la comprobación del fin del período de parches.

| Elemento | Contrato y limitación del ejemplo |
|---|---|
| Clúster | EKS `1.36` mediante plantilla, un `g6e.4xlarge`; vuelve a comprobar la disponibilidad y la compatibilidad regionales |
| Complemento de GPU | versión fijada en `0.20.0`; valida con el nuevo DLC, AMI y controlador |
| kubeconfig | archivo por ejecución y contexto explícito; rechaza colisiones con clústeres preexistentes |
| MLflow | ClusterIP, SQLite, `emptyDir`; sin autenticación de aplicación, almacenamiento duradero ni aislamiento de inquilinos |
| Datos | SDK de S3 con permisos de AWS delimitados al ServiceAccount; verifica SHA-256 del manifiesto y la cuenta propietaria del bucket |
| Job | `backoffLimit: 0`, `activeDeadlineSeconds: 10800`; no garantiza que se recuperen todos los recursos en un plazo de tres horas si se producen fallos |
| Exportación | verifica ocho artefactos y sus SHA-256 a partir de una ejecución completada que coincida con el experimento, el clúster y los ID de ejecución |
| Apagado | limpia el clúster propio tras verificar la exportación y los hashes; un fallo de exportación puede hacer que se conserve para su recuperación |

El cargador de entradas lee del ConfigMap el código y los hashes de carga, y luego usa EKS Pod Identity para descargar solo cinco objetos de S3. El ServiceAccount es `qwen-input-reader`; se requieren Pod Identity Agent, un SDK compatible y la asociación. La alternativa de credenciales de metadatos de instancia EC2 está deshabilitada. Esto no elimina la restricción de ejecución por DLC vencido.

Los datos de `emptyDir` de los Pod de entrenamiento y MLflow desaparecen al eliminar el Pod o el clúster. `results/eks-<mode>.<suffix>/mlflow-export-<mode>.tar.gz` y el recibo de exportación de cada ejecución son archivos locales, no una copia de seguridad externa. Cópialos en otro almacenamiento aprobado y verifica la limpieza.

Una ejecución de entrenamiento fallida sin una ejecución o exportación completada no puede cumplir la condición de eliminación automática. Concilia el ID de cuenta, el ARN del clúster, la fecha de creación, las etiquetas de propiedad y los ID de pila del inventario privado con AWS; recupera o descarta explícitamente los resultados necesarios y, luego, elimina **solo ese clúster propio** con `eksctl delete cluster --name ... --region ... --wait`. La creación parcial o las respuestas perdidas también requieren conciliación manual. Ejecuta `verify_cleanup.sh` después y revisa los recursos que se conserven tras eliminar la pila. No inventes indicadores de propiedad para eludir la verificación.

## Errores observados y condiciones de detención

| Condición | Gestión |
|---|---|
| DLC llegó al fin del período de parches | bloquea la creación y el entrenamiento; actualiza el grupo del entorno de ejecución |
| ruta de configuración incorrecta | lee la configuración del paquete de código fuente |
| colisión de nombres o respuesta de creación perdida | rechaza la eliminación automática sin confirmar la propiedad |
| exportación ausente o fallida | no declares el éxito antes de verificar los adaptadores y los archivos agregados |
| error de autorización en una consulta o tiempo de espera de eliminación | registra un estado desconocido o un fallo |
| omisión histórica de la membresía del proyecto | concilia con el administrador del dominio y el propietario del proyecto |

## Cómo elegir una ruta

SageMaker reduce el trabajo operativo de Training Job y MLflow, pero la conservación de artefactos, los permisos y la limpieza de experimentos siguen requiriendo intervención. EKS ofrece control de Kubernetes y añade responsabilidad sobre los clústeres, los complementos de GPU y el almacenamiento de MLflow. Al compararlos, registra conjuntamente la configuración, los hashes de los datos, la revisión del modelo, las dependencias reales y el entorno de GPU.

## Fuentes principales

- [Catálogo de AWS DLC PyTorch 2.8 y fin del período de parches](https://github.com/aws/deep-learning-containers/blob/main/docs/src/data/pytorch-training/2.8-gpu-sagemaker.yml)
- [Directorio de código de SageMaker Training Toolkit](https://github.com/aws/sagemaker-training-toolkit/blob/master/src/sagemaker_training/entry_point.py)
- [Configuración de MLflow App](https://docs.aws.amazon.com/sagemaker/latest/dg/mlflow-app-setup.html)
- [Versiones de SageMaker MLflow](https://docs.aws.amazon.com/sagemaker/latest/dg/mlflow.html)
- [Expiración de URL prefirmadas de S3](https://docs.aws.amazon.com/AmazonS3/latest/userguide/using-presigned-url.html)
- [Comportamiento y restricciones de EKS Pod Identity](https://docs.aws.amazon.com/eks/latest/userguide/pod-identities.html)
- [Fallos y terminación de Kubernetes Job](https://kubernetes.io/docs/concepts/workloads/controllers/job/)

Anterior: [Parte 2: Datos sintéticos de PII y tokenización](02-pii-data-tokenization.md)

Siguiente: [Parte 4: Gobernanza de Unified Studio](../../data-on-eks/sagemaker-unified-studio/01-domains-projects-governance.md)
