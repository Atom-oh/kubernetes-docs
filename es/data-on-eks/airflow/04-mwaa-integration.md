# Parte 4: Integración con Amazon MWAA

> **Última actualización**: 12 de octubre de 2026; MWAA Airflow 3.3.1 / Python 3.12; proveedor de Kubernetes 10.21.0.
> **Último parche upstream comprobado**: Airflow 3.3.2 (MWAA no lo incluía al 12 de octubre de 2026).

Este capítulo se dirige a **entornos aprovisionados de Amazon MWAA** que envían trabajo a clústeres EKS del cliente. **MWAA Serverless**, con definiciones de flujos de trabajo YAML, es otra opción de implementación; no transfiera a ese servicio sin cambios este modelo de entorno/archivos DAG/costos.

## 1. Límites de administración y versiones actuales

Los planificadores/workers de MWAA usan infraestructura Fargate administrada por AWS, conectada a subredes privadas de la VPC del cliente seleccionada. AWS también administra la base de datos de metadatos. Por ello, la VPC del cliente sí forma parte de la arquitectura del servicio. Sin embargo, **los Pods del planificador de MWAA no se implementan en el clúster EKS del cliente para administrarlos con kubectl**. En Airflow 3, el servidor web de MWAA también aloja la API de ejecución.

AWS opera el servicio subyacente. Usted sigue administrando los DAG, las dependencias, IAM, la conectividad de VPC, los ajustes de capacidad, las alarmas, los procedimientos de recuperación y las actualizaciones a versiones compatibles. La infraestructura administrada no elimina los fallos del entorno ni la planificación de capacidad.

La tabla oficial de compatibilidad indica que Airflow **3.3.1 está disponible desde el 2026-09-01** y que 3.2.1 está disponible desde el 2026-05-19. La versión upstream 3.3.1 se publicó el 2026-08-12. La versión upstream 3.3.2 se publicó después, el 2026-09-17; al 2026-10-12 la tabla de MWAA todavía mostraba 3.3.1 como la versión más reciente. Un parche upstream no está disponible automáticamente en MWAA. Consulte la [tabla de versiones compatibles de AWS MWAA](https://docs.aws.amazon.com/mwaa/latest/userguide/airflow-versions.html) para ver las versiones actuales y la disponibilidad por región. En vez de dar por sentado un retraso fijo de tres meses, compruebe el parche, los proveedores, la región y la versión real del entorno que necesita. Los entornos existentes no cambian automáticamente a cada nueva versión compatible de Airflow.

| Aspecto | Airflow autoadministrado en EKS | MWAA aprovisionado |
| --- | --- | --- |
| Operaciones | Diseñar recursos de Kubernetes, base de datos, actualizaciones y recuperación | AWS administra la infraestructura del servicio; los usuarios siguen siendo responsables de los DAG, permisos, conectividad, decisiones de capacidad y actualizaciones |
| Versiones/ejecutores | Validar las combinaciones elegidas | Elegir entre las opciones de runtime/configuración compatibles |
| Paquetes de Python | Crear imágenes propias u otros mecanismos de entrega | requirements.txt en S3 con restricciones de versión correspondientes |
| Dependencias del sistema | Configurarlas en las políticas de imagen/nodo | Los scripts de inicio pueden instalar runtimes de Linux; validar la compatibilidad, el tiempo de inicio y la red |
| Entrega de DAG | Configurar GitDagBundle, git-sync u otras rutas | Configuración base documentada: carpeta de DAG en S3 y sincronización de archivos complementarios |
| Cargas de trabajo externas | Usar KPO y otras integraciones para imágenes separadas | La integración KPO/EKS también puede ejecutar imágenes de carga separadas |

Los scripts de inicio se ejecutan antes de instalar los requisitos y arrancar Airflow; los ejemplos oficiales incluyen la instalación de runtimes mediante sudo. Por ello, es incorrecto prohibir en bloque los paquetes del sistema. Esta capacidad no equivale a poder reemplazar libremente la imagen base administrada o el ejecutor.

Este ejemplo usa Git → CI → S3 → MWAA. La entrega mediante S3 por sí sola no permite concluir que todas las capacidades de bundles de Airflow 3 estén indisponibles. Antes de adoptar una configuración independiente de bundles, valide la configuración permitida y la compatibilidad con una versión concreta de MWAA. Tanto el sondeo de Git como la sincronización de S3 tienen retrasos de análisis; ninguno garantiza la ejecución inmediatamente después de un push o merge.

## 2. Tres requisitos para acceder a EKS

1. **Red:** las subredes de workers necesitan acceso DNS y HTTPS 443 al endpoint de la API de EKS. Para endpoints privados, compruebe las rutas, los grupos de seguridad y DNS. Añadir autenticación no resuelve un tiempo de espera de conexión.
2. **Autenticación:** el rol de ejecución de MWAA debe reconocerse mediante una entrada de acceso de EKS o una configuración `aws-auth` existente. El complemento exec de kubeconfig usa las credenciales IAM disponibles en el momento de la ejecución.
3. **Autorización:** vincule el grupo de Kubernetes asignado a un Role del espacio de nombres. La autenticación de EKS, RBAC de Kubernetes y los permisos de datos de AWS del Pod secundario son capas distintas.

Use un entorno MWAA 3.3.1 existente, un clúster EKS existente, AWS CLI v2 y kubectl. Compruebe la compatibilidad actual de EKS y la compatibilidad del proveedor/cliente. Este capítulo no requiere un clúster nuevo ni permisos administrativos amplios.

### Entrada de acceso y RBAC del espacio de nombres

La configuración siguiente la realiza un administrador del clúster. Sustituya el ARN del rol, el clúster y la región, e inspeccione primero cualquier entrada de acceso existente.

```bash
aws eks describe-cluster \
  --name data-eks-cluster --region us-east-1 \
  --query 'cluster.accessConfig.authenticationMode'

# Administrator action; API or API_AND_CONFIG_MAP mode is required.
aws eks create-access-entry \
  --cluster-name data-eks-cluster --region us-east-1 \
  --principal-arn arn:aws:iam::123456789012:role/mwaa-execution-role-my-environment \
  --type STANDARD \
  --kubernetes-groups mwaa-pod-launcher
```

Las entradas de acceso también funcionan en modo API_AND_CONFIG_MAP. Editar `aws-auth` no concede acceso en modo solo API. Para clústeres heredados CONFIG_MAP, use la asignación existente o planifique una migración. Las transiciones del modo de autenticación incluyen cambios irreversibles, por lo que este ejemplo no cambia el modo silenciosamente.

Guarde y aplique el siguiente archivo `workload-access.yaml`. El RoleBinding limita esta concesión a `data-processing`. Un ClusterRoleBinding no expresa ese límite de espacio de nombres.

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: data-processing
---
apiVersion: v1
kind: ServiceAccount
metadata:
  name: workload-smoke
  namespace: data-processing
automountServiceAccountToken: false
---
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: mwaa-pod-launcher
  namespace: data-processing
rules:
- apiGroups:
  - ''
  resources:
  - pods
  verbs:
  - create
  - get
  - list
  - watch
  - patch
  - delete
- apiGroups:
  - ''
  resources:
  - pods/log
  verbs:
  - get
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: mwaa-pod-launcher
  namespace: data-processing
subjects:
- kind: Group
  name: mwaa-pod-launcher
  apiGroup: rbac.authorization.k8s.io
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: Role
  name: mwaa-pod-launcher
```

El Role puede afectar a los Pods de todo ese espacio de nombres. Otras concesiones de políticas de acceso/RBAC son aditivas, así que inspeccione el conjunto completo de permisos. Use controles de admisión para autores no confiables que podrían seleccionar otras cuentas de servicio o especificaciones de Pod peligrosas. Este ejemplo síncrono no requiere permisos de XCom/exec.

## 3. Kubeconfig y entrega de dependencias

Genere un archivo nuevo en vez de combinar contextos personales de kubeconfig en el artefacto. El administrador que lo genere necesita `eks:DescribeCluster` en el destino.

```bash
set -eu
mkdir -p ./mwaa-staging
test ! -e ./mwaa-staging/kube_config.yaml
aws eks update-kubeconfig \
  --name data-eks-cluster --region us-east-1 \
  --alias data-eks-cluster \
  --kubeconfig ./mwaa-staging/kube_config.yaml
```

Inspeccione el clúster, el contexto, la CA y `exec.command` generados. Quite las entradas `exec.env` que hagan referencia al `AWS_PROFILE` local de un desarrollador, para que pueda usarse la cadena de credenciales predeterminada del rol de ejecución de MWAA. No añada argumentos `exec --role` a menos que pretenda asumir otro rol por separado. No almacene claves de larga duración ni un token estático. Compruebe también el ejecutable `aws` y la ruta `get-token` en el runtime de MWAA.

El siguiente requirements.txt está dirigido al **entorno 3.3.1/Python 3.12 de este capítulo**. Inspeccione primero los proveedores que ya incluye la imagen; después de añadirlos o cambiarlos, valide las versiones realmente instaladas. No use un extra `apache-airflow` sin versión, pues podría cambiar involuntariamente la versión principal de Airflow.

```text
--constraint https://raw.githubusercontent.com/apache/airflow/constraints-3.3.1/constraints-3.12.txt
apache-airflow-providers-cncf-kubernetes==10.21.0
```

Habilite el versionado del bucket y Block Public Access según los requisitos de MWAA. Después de cargar requirements.txt, actualice la versión del objeto que referencia el entorno y compruebe los registros de instalación. Sobrescribir el objeto por sí solo no completa el procedimiento de actualización de dependencias.

Conserve esta estructura bajo el prefijo DAG configurado en S3. Revise el `kube_config.yaml` generado antes de colocarlo junto al DAG.

```text
dags/
  mwaa_eks_smoke.py
  kube_config.yaml
  templates/
    base-pod-template.yaml
```

```yaml
apiVersion: v1
kind: Pod
metadata:
  labels:
    app: airflow-kpo-smoke
spec:
  serviceAccountName: workload-smoke
  automountServiceAccountToken: false
  restartPolicy: Never
  securityContext:
    runAsNonRoot: true
    runAsUser: 65532
    seccompProfile:
      type: RuntimeDefault
  containers:
  - name: base
    image: python:3.12-slim
    resources:
      requests:
        cpu: 100m
        memory: 64Mi
      limits:
        cpu: 500m
        memory: 128Mi
    securityContext:
      allowPrivilegeEscalation: false
      readOnlyRootFilesystem: true
      capabilities:
        drop:
        - ALL
```

```python
from datetime import datetime, timedelta, timezone
from pathlib import Path

from airflow.sdk import DAG
from airflow.providers.cncf.kubernetes.operators.pod import KubernetesPodOperator

BUNDLE_DIR = Path(__file__).resolve().parent

with DAG(
    dag_id="mwaa_eks_smoke",
    start_date=datetime(2026, 9, 1, tzinfo=timezone.utc),
    schedule=None,
    catchup=False,
) as dag:
    run_smoke = KubernetesPodOperator(
        task_id="run_smoke",
        name="mwaa-eks-smoke",
        namespace="data-processing",
        image="python:3.12-slim",
        cmds=["python", "-B", "-c"],
        arguments=["import sys; print('MWAA_EKS_OK run_id=' + sys.argv[1])", "{{ run_id }}"],
        pod_template_file=str(BUNDLE_DIR / "templates/base-pod-template.yaml"),
        in_cluster=False,
        config_file=str(BUNDLE_DIR / "kube_config.yaml"),
        service_account_name="workload-smoke",
        random_name_suffix=True,
        reattach_on_restart=True,
        deferrable=False,
        do_xcom_push=False,
        get_logs=True,
        log_events_on_failure=False,
        startup_timeout_seconds=120,
        active_deadline_seconds=180,
        execution_timeout=timedelta(minutes=5),
        on_finish_action="delete_pod",
        on_kill_action="delete_pod",
    )
```

![Un worker de MWAA llega a EKS a través de la conectividad de red, la autenticación IAM y RBAC del espacio de nombres para ejecutar un Pod de carga de trabajo independiente.](../../.gitbook/assets/en-data-on-eks-airflow-04-mwaa-integration-0.png)

[Diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-data-on-eks-airflow-04-mwaa-integration-0.html)

## 4. Verificar la ejecución y elegir un modelo operativo

Después de que el DAG se analice correctamente, active manualmente `mwaa_eks_smoke` e inspeccione el estado de la tarea y los registros `MWAA_EKS_OK`. Mientras se ejecuta, inspeccione la cuenta de servicio, la imagen y los recursos reales del Pod. La eliminación después del éxito es un comportamiento de limpieza configurado. Use el registro de tareas de CloudWatch de MWAA para conservar los registros.

| Síntoma | Límite que se debe inspeccionar |
| --- | --- |
| Tiempo de espera de DNS/conexión | Rutas, DNS y grupos de seguridad entre la subred de workers y la API de EKS |
| No autorizado | Credenciales exec, rol IAM real y entrada de acceso |
| Prohibido | Espacio de nombres, grupo, RoleBinding y verbos necesarios |
| ImagePullBackOff | Identidad de extracción de imágenes del nodo/Fargate de EKS y conectividad con el registro |
| Error de importación de DAG/ejecutable exec | Paquetes instalados en MWAA, archivos sincronizados y ejecutable aws |

El Pod de carga de trabajo no hereda automáticamente el rol de ejecución de MWAA. El trabajo real con S3 necesita permisos de datos independientes, como IRSA o Pod Identity para su cuenta de servicio. KPO puede ejecutar otras imágenes; MWAA no se limita a canalizaciones solo de PyPI ni a canalizaciones de poca importancia.

Compare la flexibilidad de ejecutor/runtime, las versiones compatibles, la capacidad operativa, los límites de red y los requisitos de recuperación. Para los costos, mantenga constantes los objetivos de rendimiento/latencia e incluya la clase del entorno/rango de workers, EKS, la base de datos, el almacenamiento, NAT, los registros y el esfuerzo de ingeniería. No base la decisión en una afirmación sin fundamento de que autoadministrar ahorra entre el 30 % y el 60 %.

## Alcance de la validación y referencias

Se revisaron la tabla de versiones, las restricciones oficiales, el código fuente del proveedor y la estructura de ejemplo de Python/YAML/shell. No se actualizó MWAA ni se creó una entrada de acceso de EKS; tampoco se aplicó RBAC ni se ejecutó un flujo integral. Verifique la conectividad y la ejecución específicas de la cuenta con las comprobaciones anteriores.


- [Versiones compatibles y fechas de disponibilidad de MWAA](https://docs.aws.amazon.com/mwaa/latest/userguide/airflow-versions.html)
- [Arquitectura de MWAA](https://docs.aws.amazon.com/mwaa/latest/userguide/what-is-mwaa.html)
- [Scripts de inicio y runtimes de Linux](https://docs.aws.amazon.com/mwaa/latest/userguide/using-startup-script.html)
- [Dependencias y restricciones de Python](https://docs.aws.amazon.com/mwaa/latest/userguide/working-dags-dependencies.html)
- [MWAA con EKS](https://docs.aws.amazon.com/mwaa/latest/userguide/mwaa-eks-example.html)
- [Administración del acceso a EKS](https://aws.amazon.com/blogs/containers/a-deep-dive-into-simplified-amazon-eks-access-management-controls/)
- [MWAA Serverless](https://docs.aws.amazon.com/mwaa/latest/mwaa-serverless-userguide/what-is-mwaa-serverless.html)

[Parte 5: Operaciones](05-operations.md)

[README](README.md)

[Cuestionario](../../quizzes/data-on-eks/airflow/04-mwaa-integration-quiz.md)
