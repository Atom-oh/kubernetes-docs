# Infraestructura de IA en EKS

> **Última actualización**: October 16, 2026
> **Versiones de referencia**: GPU Operator26.7.2 / NVIDIA DRA0.5.0 / Argo Workflows4.1.3 / JupyterHub chart4.4.2 / Mountpoint CSI2.8.0

La infraestructura de IA combina notebooks, pipelines, runtimes distribuidos, dispositivos/nodos, almacenamiento/redes y autorización. Una lista de herramientas o una release de Helm exitosa no garantiza la seguridad ni la disponibilidad de la plataforma, ni la ejecución de modelos.

## Capas y responsabilidades

![Capas que separan las responsabilidades de las cargas de trabajo, la plataforma, el cómputo y los cimientos de EKS.](../.gitbook/assets/en-ai-ml-06-ai-infrastructure-0.png)

[Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-ai-ml-06-ai-infrastructure-0.html)

Las cargas de trabajo se encargan del código de modelos/datos/ejecución; las plataformas, de los workflows, runtimes y registros; el cómputo, de los dispositivos reales, los Pods y la capacidad de los nodos. Las identidades de IAM, redes y almacenamiento abarcan estas capas. Un NodePool habilitado para Spot no garantiza capacidad, recuperación ni ahorro.

## Stack JARK

JARK combina JupyterHub, Argo Workflows, Ray y Karpenter. Es un patrón de integración, no un producto que se conecte automáticamente. Conecta explícitamente la autorización de notebooks, el envío de workflows, los trabajos de Ray, la programación de Kubernetes y el aprovisionamiento de nodos.

![JupyterHub/Argo/Ray crean cargas de trabajo de Kubernetes; el scheduler coloca los Pods y Karpenter aprovisiona nodos.](../.gitbook/assets/en-ai-ml-06-ai-infrastructure-1.png)

[Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-ai-ml-06-ai-infrastructure-1.html)

### Autenticación y perfiles de notebooks de JupyterHub

Chart4.4.2 declara appVersion5.5.2, distinta de la versión más reciente de Hub inspeccionada en PyPI: 6.1.0 (2026-10-14). Las comprobaciones locales de la API usaron Hub6.0.0/OAuthenticator17.4.0/KubeSpawner7.1.0; verifica las combinaciones reales de paquetes dentro de la imagen del chart operativo.

Cognito es una opción de proveedor OIDC. Haz coincidir las URL de callback, los endpoints de token/userInfo, los scopes y un claim de nombre de usuario estable, y configura una política de autorización explícita. MFA/la federación corporativa deben configurarse en el proveedor; GenericOAuthenticator no las habilita automáticamente.

Esta configuración de Hub presupone que existe un volumen Secret montado en /run/secrets/oidc. Mantén los secretos reales fuera de ConfigMaps, el código fuente y las variables de entorno. Conecta este archivo Python con la ruta de configuración real de Hub y sustituye los URI/valores de sub aprobados según tu entorno.

```python
from pathlib import Path

c.JupyterHub.authenticator_class = "oauthenticator.generic.GenericOAuthenticator"
c.GenericOAuthenticator.client_id = "prepared-client-id"
c.GenericOAuthenticator.client_secret = Path("/run/secrets/oidc/client-secret").read_text().strip()
c.GenericOAuthenticator.oauth_callback_url = "https://jupyter.example.com/hub/oauth_callback"
c.GenericOAuthenticator.authorize_url = "https://prepared-domain.auth.us-west-2.amazoncognito.com/oauth2/authorize"
c.GenericOAuthenticator.token_url = "https://prepared-domain.auth.us-west-2.amazoncognito.com/oauth2/token"
c.GenericOAuthenticator.userdata_url = "https://prepared-domain.auth.us-west-2.amazoncognito.com/oauth2/userInfo"
c.GenericOAuthenticator.scope = ["openid", "profile", "email"]
c.GenericOAuthenticator.username_claim = "sub"
c.GenericOAuthenticator.allow_all = False
c.GenericOAuthenticator.allow_existing_users = False
c.GenericOAuthenticator.allowed_users = {"replace-with-approved-cognito-sub"}
```

El ejemplo establece allow_all=False, allowed_users explícitos y allow_existing_users=False. Las comprobaciones locales permitieron una identidad aprobada y rechazaron usuarios no aprobados o anteriores. No se ejecutó ningún inicio de sesión OAuth ni intercambio de tokens real.

Distingue las garantías de CPU/RAM de los notebooks de sus límites, y hazlas coincidir con las imágenes GPU, etiquetas, tolerations y drivers reales. No des por hecho que las etiquetas antiguas jupyter/*:gpu incluyen CUDA. Los PVC deben estar en el mismo namespace que el Pod que los consume; un Pod de jupyterhub no puede hacer referencia a un PVC de ml-platform solo por su nombre. Revisa los puntos de acceso por usuario, UID/GID, cuotas y permisos de escritura de modelos compartidos. storage_capacity de EFS no es un límite de capacidad física.

### Flujo de datos de Argo Workflows

El workflow anterior hacía referencia a templates, artifacts y scripts que no existían. Este **fixture mínimo de flujo de datos** tiene seis etapas. Pasa parámetros mediante variables de entorno y JSON en lugar de insertar valores en el código fuente de Python. Elige entre dos coeficientes; no es un pipeline real de entrenamiento de clasificación de imágenes, clúster Ray ni registro externo.

Se validaron localmente el lint sin conexión de Argo4.1.3 y los cuerpos de los seis scripts de Python. Prepara prepared-workflow-runner con privilegios mínimos y configura por separado los digests de imagen, las cuotas y el almacenamiento de artifacts antes de usarlo en operaciones.

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Workflow
metadata:
  generateName: toy-dataflow-
  namespace: argo
spec:
  entrypoint: pipeline
  serviceAccountName: prepared-workflow-runner
  parallelism: 1
  activeDeadlineSeconds: 600
  arguments:
    parameters:
    - name: data
      value: '[[1,2],[2,4],[3,6],[4,8]]'
  templates:
  - name: pipeline
    dag:
      tasks:
      - name: validate
        template: validate
        arguments:
          parameters:
          - name: data
            value: '{{workflow.parameters.data}}'
      - name: prepare
        template: prepare
        arguments:
          parameters:
          - name: data
            value: '{{tasks.validate.outputs.result}}'
        dependencies:
        - validate
      - name: tune
        template: tune
        arguments:
          parameters:
          - name: data
            value: '{{tasks.prepare.outputs.result}}'
        dependencies:
        - prepare
      - name: train
        template: train
        arguments:
          parameters:
          - name: scale
            value: '{{tasks.tune.outputs.result}}'
        dependencies:
        - tune
      - name: evaluate
        template: evaluate
        arguments:
          parameters:
          - name: model
            value: '{{tasks.train.outputs.result}}'
          - name: data
            value: '{{tasks.prepare.outputs.result}}'
        dependencies:
        - train
      - name: register
        template: register
        arguments:
          parameters:
          - name: model
            value: '{{tasks.train.outputs.result}}'
        dependencies:
        - evaluate
        when: '{{tasks.evaluate.outputs.result}} == 0'
  - name: validate
    inputs:
      parameters:
      - name: data
    script:
      image: python:3.12.14-slim-trixie
      command:
      - python
      env:
      - name: DATA
        value: '{{inputs.parameters.data}}'
      resources:
        requests:
          cpu: 100m
          memory: 64Mi
        limits:
          cpu: 500m
          memory: 128Mi
      source: 'import json, os

        rows = json.loads(os.environ["DATA"])

        assert rows and all(len(row) == 2 for row in rows)

        assert all(isinstance(v, (int, float)) for row in rows for v in row)

        print(json.dumps(rows))

        '
  - name: prepare
    inputs:
      parameters:
      - name: data
    script:
      image: python:3.12.14-slim-trixie
      command:
      - python
      env:
      - name: DATA
        value: '{{inputs.parameters.data}}'
      resources:
        requests:
          cpu: 100m
          memory: 64Mi
        limits:
          cpu: 500m
          memory: 128Mi
      source: 'import json, os

        rows = json.loads(os.environ["DATA"])

        print(json.dumps({"train": rows[:2], "test": rows[2:]}))

        '
  - name: tune
    inputs:
      parameters:
      - name: data
    script:
      image: python:3.12.14-slim-trixie
      command:
      - python
      env:
      - name: DATA
        value: '{{inputs.parameters.data}}'
      resources:
        requests:
          cpu: 100m
          memory: 64Mi
        limits:
          cpu: 500m
          memory: 128Mi
      source: 'import json, os

        data = json.loads(os.environ["DATA"])

        candidates = [1.0, 2.0]

        loss = lambda scale: sum((scale*x-y)**2 for x,y in data["train"]) / len(data["train"])

        print(min(candidates, key=loss))

        '
  - name: train
    inputs:
      parameters:
      - name: scale
    script:
      image: python:3.12.14-slim-trixie
      command:
      - python
      env:
      - name: SCALE
        value: '{{inputs.parameters.scale}}'
      resources:
        requests:
          cpu: 100m
          memory: 64Mi
        limits:
          cpu: 500m
          memory: 128Mi
      source: 'import json, os

        print(json.dumps({"scale": float(os.environ["SCALE"]), "fixture": True}))

        '
  - name: evaluate
    inputs:
      parameters:
      - name: model
      - name: data
    script:
      image: python:3.12.14-slim-trixie
      command:
      - python
      env:
      - name: MODEL
        value: '{{inputs.parameters.model}}'
      - name: DATA
        value: '{{inputs.parameters.data}}'
      resources:
        requests:
          cpu: 100m
          memory: 64Mi
        limits:
          cpu: 500m
          memory: 128Mi
      source: 'import json, os

        model = json.loads(os.environ["MODEL"])

        held_out = json.loads(os.environ["DATA"])["test"]

        print(sum((model["scale"]*x-y)**2 for x,y in held_out) / len(held_out))

        '
  - name: register
    inputs:
      parameters:
      - name: model
    script:
      image: python:3.12.14-slim-trixie
      command:
      - python
      env:
      - name: MODEL
        value: '{{inputs.parameters.model}}'
      resources:
        requests:
          cpu: 100m
          memory: 64Mi
        limits:
          cpu: 500m
          memory: 128Mi
      source: 'import json, os

        model = json.loads(os.environ["MODEL"])

        print(json.dumps({"candidate": model, "note": "fixture output only; no registry write"}))

        '
```

El MSE0 del fixture procede de cuatro muestras sintéticas, no de una medición real de la calidad del modelo. Los workflows de producción necesitan separación entre entrenamiento y prueba, revisiones de datos/modelos, reglas de fallos/reintentos/idempotencia y transferencias reales de artifacts. artifactRepositoryRef no instala boto3 ni concede permisos de descarga a la aplicación.

### Ray y Karpenter

Usa las rutas auditadas de Ray2.58/KubeRay1.7 en la [guía de Ray](ray/README.md). GCS significa Global Control Service; la programación interactúa con raylets. El head puede ejecutar trabajo si anuncia CPU. Evita combinaciones de Ray/Python no verificadas en workers de CPU/GPU/Neuron; las imágenes de Neuron también necesitan Ray y frameworks compatibles.

El autoscaling de Ray expresa la demanda de worker-Pod, el scheduler de Kubernetes coloca los Pods y Karpenter proporciona capacidad de nodo compatible. Los workers de Ray no invocan directamente las API de Karpenter. Haz coincidir las etiquetas de producto de memoria/GPU con los nodos reales; no selecciones A100 de 40GB p4d con una etiqueta de 80GB.

No dupliques drivers en AMI NVIDIA de AL2023 ni sobrescribas toda la configuración de containerd. Los límites de Karpenter no son topes absolutos de admisión/costo, y la consolidación no usa directamente un umbral de utilización de DCGM del 20%. Inspecciona las solicitudes, la viabilidad de la programación, los precios y las restricciones de interrupción.

## API de DRA y límites de compatibilidad

DRA representa los atributos, las solicitudes y la asignación de dispositivos mediante DeviceClass, ResourceSlice y ResourceClaim/Template. Los drivers publican slices; los componentes del scheduler/driver asignan y preparan los claims. Los ResourceSlices escritos manualmente no crean GPU reales. La madurez de la API de Kubernetes y la madurez de las funcionalidades del driver NVIDIA son independientes.

![Rutas de recursos extendidos de device-plugin frente a DeviceClass/ResourceSlice/ResourceClaim de DRA; el uso compartido y la topología dependen del driver, el hardware y los feature gates.](../.gitbook/assets/en-ai-ml-06-ai-infrastructure-2.png)

[Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-ai-ml-06-ai-infrastructure-2.html)

### Ejemplo actual de claim

El esquema resource.k8s.io/v1 inspeccionado en Kubernetes1.36.2 usa requests.exactly. Los requisitos previos del driver NVIDIA0.5 distinguen la asignación de GPU (1.34.2+) de ComputeDomains (1.32+). Verifica las API y las versiones de parches/plataforma que realmente ofrece EKS. «Todas las funcionalidades de DRA en 1.31+» es inexacto.

Este **ejemplo de esquema** define un claim de GPU y un Pod de comando de inventario. Prepara por separado el namespace ml-workloads, DeviceClass gpu.nvidia.com, driver/CDI, nodos y permisos. En esta auditoría no se ejecutó ninguna GPU.

```yaml
apiVersion: resource.k8s.io/v1
kind: ResourceClaimTemplate
metadata:
  namespace: ml-workloads
  name: single-gpu
spec:
  spec:
    devices:
      requests:
      - name: gpu
        exactly:
          deviceClassName: gpu.nvidia.com
          count: 1
---
apiVersion: v1
kind: Pod
metadata:
  name: gpu-inventory-demo
  namespace: ml-workloads
spec:
  restartPolicy: Never
  automountServiceAccountToken: false
  containers:
  - name: inspect
    image: ubuntu:24.04
    command:
    - nvidia-smi
    - -L
    resources:
      claims:
      - name: gpu
      requests:
        cpu: 100m
        memory: 64Mi
      limits:
        cpu: 500m
        memory: 128Mi
  resourceClaims:
  - name: gpu
    resourceClaimTemplateName: single-gpu
  tolerations:
  - key: nvidia.com/gpu
    operator: Exists
    effect: NoSchedule
```

CEL debe usar los atributos tipados/la estructura de dominio que se hayan publicado realmente. device.topology.node==device.topology.node, usado anteriormente, no expresa la colocación en el mismo nodo ni coincide con la API. matchAttribute necesita un atributo cualificado real. Un claim de GPU normal para un solo Pod no asigna automáticamente 72 GPU en un rack NVL72.

### NVIDIA0.5 y GPU Operator26.7

El README de 0.5 todavía describe la asignación de GPU como experimental y deshabilitada de forma predeterminada, en conflicto con la documentación de instalación/chart y Operator26.7. Los valores predeterminados del chart independiente real son resources.gpus.enabled=true, pero **se rechaza el renderizado** si no se habilita explícitamente para evitar conflictos con device-plugin. No describas la instalación predeterminada como una que deshabilita GPU silenciosamente y termina correctamente.

La ruta gestionada de Operator26.7 usa el singleton GPUCluster llamado gpu-cluster, que es mutuamente excluyente con ClusterPolicy. Su ruta con driver preinstalado establece clusterPolicy.deployCR=false, gpuCluster.deployCR=true y driver.enabled=false. GPUCluster no sustituye toda la preparación de driver/toolkit; proporciona los requisitos previos de driver/CDI. No instales un release DRA independiente duplicado. El renderizado local simuló una API DeviceClass disponible; no habilitó una funcionalidad de clúster real.

Distingue la compatibilidad con GPU completa/MIG existente y ComputeDomain de las funcionalidades alpha DynamicMIG, MPS y TimeSlicingSettings. El código de feature gates inspeccionado de 0.5 declara esas tres como false/Alpha. Algunas etiquetas GA de la documentación también difieren de las etiquetas Beta del código fuente; registra conjuntamente la matriz de compatibilidad, el código y la configuración de la versión exacta. GPU Operator25.3 por sí solo no demuestra que todo esté admitido.

Los device plugins también admiten rutas de MIG existente, time-slicing y MPS experimental; el uso compartido de GPU no es exclusivo de DRA. 3g.20gb identifica un perfil de instancia, no tres instancias de 20GB. La asignación MIG/exclusiva no aísla automáticamente el host, el driver, los privilegios ni todos los canales laterales; MPS/time-slicing no son límites de seguridad.

### NVLink multinodo y ComputeDomains

GB200 es Grace Blackwell, no Grace Hopper. ComputeDomains coordinan recursos MNNVL/IMEX entre Pods/nodos. Distingue racks, instancias EC2, nodos de Kubernetes y Pods, y verifica la compatibilidad real de clique/fabric/dispositivo/driver. Los campos inventados nvswitchEnabled/graceHopperMode o las puertas de programación no configuran la topología. Una puerta de programación sin un controlador que la retire deja el Pod en espera.

## Plataformas de agentes y MCP

Usa las API actuales de Kagent/LangGraph/Langfuse/Milvus en la [guía de IA agentic](03-agentic-ai-platform.md). GitLab es una plataforma opcional de origen/CI; los runners con privilegios y el ingreso público no son requisitos básicos. Separa la identidad de los trabajos, las redes, los secretos y los permisos para crear imágenes, y verifica la entrega de credenciales del proveedor.

MCP define operaciones de protocolo como listar/llamar herramientas; no es un controlador estándar de autodetección de Kubernetes ni una distribución de gateway. La imagen anterior ghcr.io/anthropics/mcp-gateway:latest y la etiqueta/configuración mcp.anthropic.com/tool eran implementaciones no verificadas y se eliminaron. Selecciona una versión real de servidor/gateway y valida el transporte, la autenticación, la autorización, los tiempos de espera y los esquemas de entrada de las herramientas. Una variable de entorno URL no implementa esas operaciones.

Solicitar recursos GPU para Milvus no habilita la indexación GPU. Haz coincidir las dimensiones de embedding/revisiones del modelo, los parámetros del índice, el ciclo de vida de eliminación/actualización y los filtros por tenant. No uses un Deployment de Langfuse2.x como instalación actual de la plataforma4.x; comprueba las dependencias del backend, las credenciales de archivos, las API de instrumentación y la retención de datos sensibles.

## Almacenamiento y redes

Verifica IAM/UID/GID del punto de acceso de EFS, los permisos de directorio y el consumo del PVC en el mismo namespace. La opción de montaje IAM no configura por sí sola las credenciales del controlador/la identidad de montaje.

Usa parámetros CSI de FSx y unidades de capacidad compatibles. No copies configuraciones inventadas s3ImportPath/s3ExportPath para PERSISTENT_2 ni una capacidad inválida de 10Ti. Distingue los sistemas de archivos existentes/estáticos de los aprovisionados recientemente, DRA y la compatibilidad con copias de seguridad en la [guía de almacenamiento](01-ai-ml-workloads.md).

Mountpoint CSI2.8.0 admite **PV estáticos** para buckets de S3 existentes. Se eliminó el ejemplo de bucket dinámico que solo usaba StorageClass/PVC. Mountpoint no es completamente POSIX; comprueba el comportamiento de rename, escritura aleatoria, bloqueo y checkpoint. La tabla de compatibilidad de 2.8 elimina AL2/Ubuntu22.04 y dirige las instalaciones a complementos de EKS o charts oficiales, en lugar de ramas del repositorio.

No multipliques el número de interfaces por un ancho de banda de instancia que ya sea agregado. Las cifras anteriores «4×400Gbps» de p4d y «16×1600Gbps» de trn1n eran incorrectas. Consulta la [guía de redes para entrenamiento](05-model-training.md) para la colocación en la misma AZ, las interfaces reales, driver/libfabric/NCCL, la asignación de dispositivo/Pod y los grupos de seguridad. Las etiquetas RAID0 y efa-enabled no habilitan EFA.

Las subredes son solo una parte del aislamiento. Configura el ingreso/egreso de las cargas de trabajo y los requisitos de autorreferencia de EFA mediante recursos SG/IAM reales. Un YAML con apariencia de Terraform almacenado en un ConfigMap no aplica reglas de red. Evita el acceso predeterminado desde un CIDR de toda la VPC.

## Observabilidad y alertas de GPU

DCGM Exporter4.6.0-4.8.3 define XID_ERRORS como la última **métrica gauge de código** de error. increase(XID_ERRORS) no es un recuento de errores y puede interpretar incorrectamente un cambio de código 31→13 como un reinicio. Observa el código actual o habilita por separado el contador XID_ERRORS_TOTAL. No todos los XID indican un fallo de hardware.

FB_USED/FB_FREE son métricas gauge en MiB; la proporción de abajo va de 0 a 1. Un valor alto de VRAM reservada no significa necesariamente OOM: inspecciona conjuntamente los fallos de asignación, el comportamiento de la carga de trabajo, la caché del modelo y la memoria disponible. Los umbrales fijos de 85C/20% no son estándares universales de fallo/recuperación de recursos. Comprueba los tipos/unidades reales de las métricas antes de aplicar rate() al caudal de PCIe o al ancho de banda de NVLink medidos por gauges.

Estas reglas presuponen un clúster por Prometheus. Para clústeres combinados, incluye etiquetas de clúster en las agregaciones/uniones. Inspecciona las etiquetas reales de nodo/UUID/MIG y la normalización de etiquetas de recursos de kube-state-metrics.

```yaml
groups:
- name: gpu-observations
  rules:
  - record: gpu:framebuffer_used_ratio
    expr: DCGM_FI_DEV_FB_USED / (DCGM_FI_DEV_FB_USED + DCGM_FI_DEV_FB_FREE)
  - alert: GPUReportedXIDCode
    expr: DCGM_FI_DEV_XID_ERRORS > 0
    for: 1m
    labels:
      severity: warning
    annotations:
      summary: "Inspect the reported XID code and workload context"
  - record: namespace:pending_gpu_requesting_pods:count
    expr: |
      count by (namespace) (
        max by (namespace, pod) (kube_pod_status_phase{phase="Pending"} == 1)
        and on (namespace, pod)
        max by (namespace, pod) (kube_pod_container_resource_requests{resource="nvidia_com_gpu"} > 0)
      )
```

La regla de pendientes cuenta los Pods en espera que solicitan GPU; no demuestra que la espera se deba a una escasez de GPU. Varios contenedores que soliciten GPU se cuentan una sola vez por Pod. Inspecciona los eventos, PVC, afinidad, taints, cuotas, claims y descargas de imágenes. No des por hecho que una etiqueta de nodo existe en todas las alertas.

Configura la selección real de reglas de Prometheus y el scraping correcto del Service/puerto para DCGM, Ray y Karpenter. El aprovisionamiento de archivos de Grafana difiere de un wrapper HTTP de dashboards; una etiqueta por sí sola no conecta datasources. La salida del monitor de Neuron y los endpoints del exporter requieren una preparación aparte.

## Alcance de la verificación

Se revisaron todos los textos originales de la guía/el cuestionario y 58 bloques de código únicos. Las comprobaciones abarcan los esquemas de DRA/Pod, Helm oficial, las políticas de autorización de OAuthenticator, el lint sin conexión/cuerpos de scripts de Argo y los fixtures de Prometheus. No se ejecutaron OAuth/clúster/asignaciones de GPU/DRA, modelos, montajes de S3 ni servidores MCP reales; tampoco se crearon recursos en la nube ni se hicieron llamadas de pago.

## Referencias

- [Instalación de DRA de GPU Operator26.7](https://docs.nvidia.com/datacenter/cloud-native/gpu-operator/26.7/dra-intro-install.html)
- [Código fuente de NVIDIA DRA0.5](https://github.com/kubernetes-sigs/dra-driver-nvidia-gpu/tree/v0.5.0)
- [Requisitos previos de DRA0.5](https://github.com/kubernetes-sigs/dra-driver-nvidia-gpu/blob/v0.5.0/site/content/docs/prerequisites.md)
- [Feature gates de DRA0.5](https://github.com/kubernetes-sigs/dra-driver-nvidia-gpu/blob/v0.5.0/pkg/featuregates/featuregates.go)
- [OAuthenticator17.4](https://github.com/jupyterhub/oauthenticator/tree/17.4.0)
- [JupyterHub chart4.4.2](https://github.com/jupyterhub/zero-to-jupyterhub-k8s/releases/tag/4.4.2)
- [Argo Workflows4.1.3](https://github.com/argoproj/argo-workflows/tree/v4.1.3)
- [Mountpoint CSI2.8.0](https://github.com/awslabs/mountpoint-s3-csi-driver/tree/v2.8.0)
- [Definiciones de contadores de DCGM Exporter](https://github.com/NVIDIA/dcgm-exporter/blob/4.6.0-4.8.3/etc/default-counters.csv)
- [Especificación de herramientas MCP](https://modelcontextprotocol.io/specification/2025-11-25/server/tools)

## Cuestionario

[Cuestionario sobre infraestructura de IA](../quizzes/ai-ml/06-ai-infrastructure-quiz.md)
