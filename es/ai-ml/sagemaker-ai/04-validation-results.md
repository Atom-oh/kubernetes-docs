# Parte 5: Resultados de validación de PII de Qwen en SageMaker basados en hechos

> **Última actualización**: 12 de septiembre de 2026
> **Fecha de validación de AWS**: 1 de septiembre de 2026
> **Estado histórico**: bloqueado antes del entrenamiento en GPU; registro de recursos residuales fechado el 2 de septiembre

## Conclusión

Este capítulo describe los **registros del experimento del 1 al 2 de septiembre de 2026** del repositorio. Conserva las comprobaciones locales, los intentos de aprovisionamiento de AWS y la limpieza parcial observados en ese momento; no es una consulta nueva del estado de la cuenta. La revisión de la fuente del 12 de septiembre detectó defectos adicionales de tokenización, evaluación, ejecución y limpieza que las 30 pruebas originales no detectaron.

El tercer intento de aprovisionamiento omitió la pertenencia al proyecto, lo que impidió que el solicitante eliminara el proyecto creado. Se detuvo la creación de más recursos, por lo que **no se ejecutó ni el SageMaker Training Job ni el EKS GPU Job**.

## Hechos verificados

| Elemento | Resultado |
|---|---|
| Modelo base | `Qwen/Qwen3-30B-A3B-Instruct-2507` |
| Registros sintéticos | 2,200 |
| Entrenamiento / Validación / Prueba | 1,600 / 200 / 400 |
| Coreano / Inglés | 80% / 20% |
| Contrato histórico de Python y pruebas de regresión | 30 superadas; no constituyen evidencia de ejecución en GPU ni de ausencia de todos los defectos |
| Contrato de extracción | `TYPE<TAB>ORIGINAL` |
| Versión observada de la MLflow App de SageMaker | `3.10.1` |
| Entrenamiento de SageMaker ejecutado | `false` |
| Entrenamiento de EKS ejecutado | `false` |
| Proyectos restantes el 2 de septiembre de 2026 | 1, `ACTIVE` |

## Secuencia de ejecución real

La figura muestra las **comprobaciones locales, la revisión previa de AWS, los tres intentos de aprovisionamiento, la limpieza y el punto de detención** que constan en los registros almacenados. Termina antes del entrenamiento en GPU. Que no se haya ejecutado en GPU no implica que el costo total del experimento haya sido cero.

![Flujo de trabajo de validación real que muestra la validación local, tres intentos de aprovisionamiento de SageMaker y Unified Studio, la limpieza parcial, un proyecto ACTIVE y el entrenamiento en GPU no ejecutado.](../../.gitbook/assets/en-ai-ml-sagemaker-ai-04-validation-results-0.png)

[🔍 Ver el flujo de trabajo de validación interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-ai-ml-sagemaker-ai-04-validation-results-0.html)

## Tres intentos de aprovisionamiento

| Intento | Resultado real | Entrenamiento en GPU | Limpieza |
|---|---|---|---|
| 1 | La MLflow App llegó al estado `Created`, pero el script inicial esperó un estado `ACTIVE` inexistente para la App | no iniciado | Se eliminaron la App, S3 y IAM; 0 recursos restantes |
| 2 | El dominio de Unified Studio rechazó las etiquetas personalizadas de recursos del proyecto | no iniciado | Se eliminaron la App, S3 y IAM; 0 recursos restantes |
| 3 | Se creó el proyecto sin incluir el perfil del grupo de roles del solicitante entre sus miembros | no iniciado | Se eliminaron la App, S3 y IAM; 1 proyecto restante |

## Correcciones aplicadas

El informe histórico registró cambios en la disponibilidad de la App, el tratamiento de las etiquetas del proyecto, la pertenencia del propietario y los reintentos. Esa afirmación no demuestra que la automatización actual esté completa.

El seguimiento del 12 de septiembre detectó la posible eliminación de recursos preexistentes, errores de permisos interpretados como ausencia, una ruta de configuración incorrecta, adaptadores de EKS perdidos y deficiencias en el manejo de interrupciones. Sigue el procedimiento corregido de ejecución y exportación del [capítulo de ejecución](03-sagemaker-mlflow-execution.md). Las nuevas comprobaciones usan datos de prueba locales y API simuladas; no son una nueva ejecución en AWS.

La ausencia de un proyecto en `ListProjects` por sí sola no demuestra que se haya eliminado. Comprueba la visibilidad, los filtros y la paginación; luego utiliza una consulta directa autorizada o solicita la confirmación de un administrador. Los errores de permisos y los tiempos de espera siguen siendo **desconocidos**.

## Estado de limpieza del 2 de septiembre de 2026

Nueva comprobación de solo lectura almacenada del 2 de septiembre:

| Tipo de recurso | Estado |
|---|---|
| MLflow App de SageMaker | no queda ninguna |
| Bucket S3 del experimento | no queda ninguno |
| Roles de IAM del experimento | no queda ninguno |
| Clúster de EKS / instancia GPU | nunca se crearon |
| Proyecto `qwen-pii-*` de Unified Studio | 1 `ACTIVE` |

Si ese estado aún existe, el administrador del dominio y el propietario actual del proyecto deben verificar los permisos y la titularidad antes de realizar la limpieza. No deduzcas la pertenencia ni la titularidad históricas a partir del nombre de un rol nuevo.

## Qué no se midió

| Elemento | Por qué no se publica ningún resultado |
|---|---|
| F1 de entidades ajustadas | No se ejecutaron el entrenamiento del adaptador ni la evaluación ajustada |
| Mejora respecto de la línea base | No hay un par de resultados de línea base y ajuste del mismo entorno GPU |
| Duración del entrenamiento | No se ejecutó ningún SageMaker ni EKS Training Job |
| Memoria GPU máxima | No se ejecutó ningún proceso en GPU |
| Costo de GPU | No se inició ningún GPU Job, por lo que no hay un resultado medido comparable |
| Costo total del experimento | No hay un informe de facturación conciliado para otros recursos, como la MLflow App y S3 |

Un tiempo de ejecución máximo o un número de pasos configurados son parámetros de diseño, no resultados observados.

## Requisitos para volver a ejecutar

Completa todas las condiciones en orden:

1. Concilia el inventario anterior con los recursos reales y resuelve los **recursos propiedad del experimento** que sigan existiendo o cuyo estado sea desconocido. Un prefijo de nombre compartido no autoriza su eliminación.
2. Vuelve a comprobar la cuenta, la Región, las cuotas, la imagen, el dominio, el perfil y la pertenencia del propietario actuales.
3. Fija la configuración, el código fuente y los hashes del conjunto de datos revisados; verifica los objetos cargados.
4. Ejecuta el trabajo de prueba facturable de SageMaker y conserva sus archivos de resultados.
5. Revisa CloudWatch y MLflow para detectar filtraciones de datos sin procesar. El estado de éxito o el uso exclusivo de nombres de archivo permitidos no bastan para superar esta comprobación.
6. Decide si ejecutar el Job completo basándote en la evidencia verificada del trabajo de prueba.

Ejecuta la comparación con EKS como una secuencia de prueba/completa separada, después de fijar el resultado del trabajo de prueba de SageMaker y los hashes del conjunto de datos.

## Ubicaciones de la evidencia

- Resultado estructurado: `examples/ai-ml/qwen-pii-finetuning/results/provisioning-validation.json`
- Registro detallado de validación: `docs/superpowers/reports/2026-09-01-sagemaker-qwen-pii-validation.md`
- Paquete ejecutable: `examples/ai-ml/qwen-pii-finetuning/`

Anterior: [Parte 4: Gobernanza de Unified Studio](../../data-on-eks/sagemaker-unified-studio/01-domains-projects-governance.md)

Volver al inicio: [Guía de SageMaker Qwen PII](README.md)
