# Knative

> **Versiones de ejemplo**: Serving/Eventing/Kourier 1.23.0; Operator 1.23.1. Verifique la compatibilidad de Kubernetes/EKS antes de la instalación.
> **Última actualización**: October 16, 2026

## Tabla de contenido

- [Descripción general y objetivos de aprendizaje](#overview-and-learning-objectives)
- [Arquitectura de Knative](#knative-architecture)
- [Instalación y configuración en EKS](#eks-installation-and-configuration)
- [Análisis detallado de Knative Serving](#knative-serving-deep-dive)
- [Análisis detallado de Knative Eventing](#knative-eventing-deep-dive)
- [Comparación entre KEDA y Knative](#keda-vs-knative-comparison)
- [Operaciones en producción](#production-operations)
- [Buenas prácticas](#best-practices)
- [Referencias](#references)

---

## Descripción general y objetivos de aprendizaje {#overview-and-learning-objectives}

### ¿Qué es Knative?

Knative es un proyecto **Graduado de CNCF** que amplía Kubernetes para ofrecer un conjunto de componentes de middleware con los que se pueden crear, implementar y administrar cargas de trabajo serverless modernas. En lugar de reemplazar las primitivas de Kubernetes, Knative se construye sobre ellas y ofrece abstracciones de nivel superior que simplifican patrones habituales, como el escalado automático basado en solicitudes, la entrega de eventos y la administración del tráfico.

CNCF aceptó Knative en el nivel Incubating el 2 de marzo de 2022 y lo graduó el 11 de septiembre de 2025. La madurez del proyecto no establece que una implementación particular esté lista para producción.

Knative consta de dos componentes que se pueden instalar de forma independiente:

- **Knative Serving** -- Administra el ciclo de vida de las cargas de trabajo serverless. Automatiza la implementación, el escalado (incluido el escalado a cero), el seguimiento de revisiones y el enrutamiento del tráfico.
- **Knative Eventing** -- Proporciona infraestructura para producir, enrutar y consumir eventos conforme a la especificación CloudEvents. Desacopla a los productores de eventos de los consumidores, lo que permite crear arquitecturas basadas en eventos con bajo acoplamiento.

### Serverless en Kubernetes

Los Deployments tradicionales de Kubernetes requieren que los operadores configuren de antemano los recuentos de réplicas, los umbrales de HPA y los presupuestos de recursos. Knative reduce esta carga:

1. Las cargas de trabajo escalan automáticamente desde cero hasta muchas réplicas según la concurrencia de solicitudes entrantes o las solicitudes por segundo (RPS).
2. Las especificaciones de las revisiones guardan una instantánea de la plantilla de la carga de trabajo; el tráfico se puede dirigir a Revisions conservadas y listas. Las Secrets/ConfigMaps referenciadas, el acceso al registro y el estado externo no quedan congelados, y el enrutamiento o la reversión requieren tiempo de reconciliación.
3. Los Sources/adaptadores y los Triggers separan la ingesta de eventos de su entrega. Algunos adaptadores sondean sistemas externos, y la aplicación sigue necesitando implementar el procesamiento, la autenticación y la gestión de errores.

El resultado es una plataforma que conserva toda la potencia de Kubernetes (programación, RBAC, redes y almacenamiento) y, a la vez, ofrece una experiencia para desarrolladores más cercana a la de una plataforma serverless completamente administrada.

### Knative Serving frente a Eventing

| Aspecto | Knative Serving | Knative Eventing |
|--------|----------------|-----------------|
| Propósito principal | Ciclo de vida de las cargas de trabajo impulsado por solicitudes | Enrutamiento y entrega de eventos |
| Desencadenante de escalado | Concurrencia de solicitudes HTTP / RPS | Específico del consumidor/adaptador; un Broker/Trigger no escala de forma genérica a todos los suscriptores |
| Escalado a cero | Sí (integrado) | Depende del consumidor (los consumidores respaldados por Serving pueden hacerlo) |
| Recursos principales | Service, Configuration, Revision, Route | Broker, Trigger, Channel, Subscription, Source |
| Caso de uso habitual | API, aplicaciones web y microservicios | Canalizaciones asíncronas, webhooks y flujos CDC |

### Knative frente a AWS Lambda y AWS Fargate

| Característica | Knative Serving en EKS | AWS Lambda (cómputo estándar) | AWS Fargate |
|---|---|---|---|
| Entorno de ejecución | Contenedores que cumplen el contrato de ejecución de Serving | Entornos de ejecución de Lambda compatibles o imágenes que implementan su API de ejecución | Tareas de ECS/Pods de EKS compatibles; se aplican restricciones de la plataforma |
| Duración de la solicitud/ejecución | Tiempo de espera de solicitud configurable; el valor predeterminado es 300 s y el máximo permitido es 600 s, salvo que se reconfigure | Tiempo de espera de función estándar de hasta 900 s | Regida por el ciclo de vida de la tarea/Pod, no por un límite de invocación al estilo de Lambda |
| Escalado a cero | KPA admite el escalado a cero de Revisions inactivas | Ejecución bajo demanda | Las tareas deseadas de ECS o las réplicas de Kubernetes pueden ser 0; la activación requiere un controlador/métrica apropiado |
| Arranques en frío | Réplicas de referencia, ajuste de imágenes/inicio/preparación | Optimización específica del entorno de ejecución y concurrencia aprovisionada | Inicio de tareas/Pods y configuración de imagen/red; no hay una comparación de tiempos fija |
| Memoria | Capacidad asignable del nodo, solicitudes de contenedor y sidecars | 128–10 240 MB configurables | Slots de EKS Fargate de hasta 120 GB; se aplican la sobrecarga de la plataforma y las combinaciones compatibles de CPU/memoria |
| GPU | Requiere nodos adecuados, complementos de dispositivos, solicitudes de recursos y funciones de PodSpec habilitadas | No hay GPU en el cómputo estándar de Lambda | Las GPU no están disponibles en Fargate |
| Redes | Kubernetes/CNI y configuración de la gateway | La conexión a la VPC del cliente es opcional | Redes de VPC; EKS Fargate tiene restricciones de plataforma |
| Portabilidad | API de Kubernetes/Knative; las integraciones de identidad/almacenamiento en la nube siguen siendo relevantes | API de servicios/entorno de ejecución específicas de AWS | Integración con ECS o EKS y API de plataforma compatibles |
| Entrada de eventos | HTTP/CloudEvents y adaptadores configurados | Integraciones de eventos de AWS compatibles | Integraciones de aplicación/controlador; no es un servicio genérico de enrutamiento de eventos |
| Pruebas locales | Kubernetes local es útil, pero el comportamiento en la nube aún debe validarse | Las herramientas/emuladores locales son opcionales y tienen límites de fidelidad | La lógica del contenedor se puede probar localmente; el comportamiento de la plataforma es distinto |
| Observabilidad | Configurar exportadores de métricas, registros y trazas | CloudWatch e integraciones de trazas compatibles | Configurar la recopilación compatible de AWS/OpenTelemetry |
| Base de costos | Recursos asignados del clúster, almacenamiento, balanceador de carga y recursos auxiliares | Solicitudes/duración más las funciones seleccionadas | CPU y memoria asignadas a tareas/Pods, más los recursos asociados |

Esta tabla se limita a Lambda con cómputo estándar. Las invocaciones asíncronas o desde fuentes de eventos que cumplen los requisitos en Lambda Managed Instances pueden permitir hasta 90 minutos (con excepciones específicas del servicio); tienen restricciones operativas distintas. El escalado de Pods a cero no elimina por sí mismo los cargos de nodos EC2, almacenamiento persistente ni balanceadores de carga.

### Objetivos de aprendizaje

Al finalizar este documento, podrá:

1. Explicar la arquitectura de Knative y cómo se complementan Serving y Eventing.
2. Instalar y configurar Knative en Amazon EKS con Kourier, DNS y TLS.
3. Implementar cargas de trabajo serverless con escalado automático detallado basado en la concurrencia.
4. Implementar estrategias de división del tráfico (canary, blue-green) con Revisions y Routes.
5. Crear canalizaciones basadas en eventos con Brokers, Triggers y CloudEvents.
6. Comparar KEDA y Knative, y decidir cuándo usar cada uno (o ambos).
7. Operar Knative en producción con supervisión, alta disponibilidad y políticas de recolección de basura.

---

## Arquitectura de Knative {#knative-architecture}

### Arquitectura de Serving

Serving tiene componentes del plano de control en `knative-serving` y un Queue Proxy en el namespace de la carga de trabajo de cada Pod de Revision. Sus responsabilidades incluyen la reconciliación, el enrutamiento, la admisión y el escalado; no son cinco Deployments en un mismo namespace.

![Los componentes del plano de control de Serving se ejecutan en el namespace de Serving, mientras que cada Pod de Revision tiene un Queue Proxy en su namespace de carga de trabajo. El enrutamiento puede incluir Activator cuando está en cero o para gestionar capacidad ante ráfagas; el escalador automático reconcilia la escala objetivo.](../.gitbook/assets/en-autoscaling-03-knative-0.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-autoscaling-03-knative-0.html)

**Responsabilidades de los componentes:**

| Componente | Función |
|-----------|------|
| **Activator** | Recibe solicitudes cuando una Revision se escala a cero. Almacena las solicitudes en búfer, activa el escalado y, una vez que los Pods están listos, reenvía las solicitudes almacenadas. También actúa como balanceador de carga cuando el sistema está en modo de «capacidad para ráfagas». |
| **Autoscaler** | Recopila métricas de concurrencia y RPS de los sidecars Queue Proxy. KPA y su reconciliador determinan la escala objetivo; la integración opcional con HPA administra los recursos HPA de Kubernetes. El Serving Controller reconcilia los recursos de la carga de trabajo; no es un intermediario universal para cada decisión de escalado. |
| **Queue Proxy** | Se inyecta como sidecar en cada Pod de Knative. Aplica los límites de `containerConcurrency`, informa la concurrencia en tiempo real al Autoscaler, realiza comprobaciones de estado y gestiona el apagado ordenado durante el escalado hacia abajo. |
| **Controller** | Reconcilia las CRD de Knative (Service, Configuration, Revision, Route) con los recursos subyacentes de Kubernetes (Deployments, Services y objetos Ingress). Administra la creación de revisiones y la recolección de basura. |
| **Webhook** | Valida y aplica valores predeterminados a las especificaciones de recursos de Knative durante la admisión. Se asegura de que las configuraciones no válidas se rechacen antes de que lleguen al Controller. |

### Arquitectura de Eventing

Knative Eventing proporciona una forma declarativa de vincular fuentes de eventos con consumidores. Admite dos patrones de entrega: **Broker/Trigger** (enrutamiento basado en contenido) y **Channel/Subscription** (pub-sub directo).

![Patrón Broker/Trigger de Knative, en el que un Broker enruta eventos según el filtro de Trigger a los servicios consumidores y envía las entregas fallidas a un Dead Letter Sink, junto al patrón Channel/Subscription, en el que un Channel distribuye los eventos a las Subscriptions.](../.gitbook/assets/en-autoscaling-03-knative-1.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-autoscaling-03-knative-1.html)

**Conceptos centrales de Eventing:**

| Concepto | Descripción |
|---------|-------------|
| **Event Source** | Recurso que genera o importa eventos. Knative proporciona fuentes integradas (ApiServerSource, PingSource) y la comunidad mantiene fuentes para Kafka, AWS SQS, GitHub y otros sistemas. |
| **Broker** | Recibe eventos y los entrega a los Triggers coincidentes mediante la implementación seleccionada. El almacenamiento en búfer, la persistencia y el comportamiento ante errores dependen de la clase/transporte subyacente. |
| **Trigger** | Filtro asociado a un Broker. Cada Trigger selecciona eventos mediante atributos de CloudEvent (type, source, extensiones) y enruta las coincidencias a un suscriptor. |
| **Channel** | Transporte de eventos duradero o en memoria. A diferencia de los Brokers, los Channels no filtran: cada Subscription recibe todos los eventos. |
| **Subscription** | Conecta un Channel con un suscriptor y, de forma opcional, un destino de respuesta. |
| **Dead Letter Sink** | Destino alternativo para los eventos que no se pueden entregar tras agotar las políticas de reintento. |
| **CloudEvents** | Formato estándar de sobre de CNCF (v1.0) que usan todos los componentes de Knative Eventing. Proporciona interoperabilidad entre fuentes y consumidores. |

---

## Instalación y configuración en EKS {#eks-installation-and-configuration}

Los fragmentos de instalación están destinados a un entorno de prueba aislado y contienen marcadores de posición. Aplicar Serving con un LoadBalancer puede aprovisionar recursos de AWS mediante el controlador instalado; en esta auditoría no se ejecutó ninguna acción de ese tipo. Los ConfigMaps, Services y cargas de trabajo propiedad de Operator se configuran a través de los recursos KnativeServing/KnativeEventing. Al preparar parches de combinación, conserve la configuración existente, especialmente los campos de tipo lista. Cree los namespaces de las aplicaciones, ServiceAccounts, Secrets, imágenes, recursos Kafka/SQS y roles de IAM referenciados antes de usar los ejemplos posteriores. Las comprobaciones de esquema no establecen que algo esté listo para producción.

### Requisitos previos

- Una versión de EKS existente y compatible con el proveedor, cuya compatibilidad se haya validado con los componentes de Knative seleccionados. Los ejemplos utilizan Serving/Eventing/Kourier 1.23.0 y Operator 1.23.1; esto no constituye una afirmación abierta de compatibilidad con Kubernetes 1.28 o versiones posteriores.
- `kubectl` configurado con acceso de administrador al clúster.
- (`helm` v3.12+ opcional para instalaciones basadas en Helm).

### Paso 1: Instalar Knative Operator

Knative Operator administra la instalación y el ciclo de vida de los componentes de Knative Serving y Eventing. El uso de Operator simplifica las actualizaciones de versión y la administración de la configuración.

```bash
# Fresh installation on the intended test cluster; review versioned upgrade guidance for existing installs.
kubectl config current-context
kubectl apply --server-side -f https://github.com/knative/operator/releases/download/knative-v1.23.1/operator.yaml
kubectl wait --for=condition=Established crd/knativeservings.operator.knative.dev crd/knativeeventings.operator.knative.dev --timeout=120s
kubectl wait --for=condition=Available deployment/knative-operator deployment/operator-webhook -n knative-operator --timeout=300s
```

### Paso 2: Instalar Knative Serving mediante Operator

Cree un recurso personalizado `KnativeServing` para implementar los componentes de Serving:

```yaml
apiVersion: operator.knative.dev/v1beta1
kind: KnativeServing
metadata:
  name: knative-serving
  namespace: knative-serving
spec:
  version: 1.23.0
  ingress:
    kourier:
      enabled: true
  config:
    network:
      ingress-class: kourier.ingress.networking.knative.dev
    autoscaler:
      pod-autoscaler-class: kpa.autoscaling.knative.dev
      container-concurrency-target-percentage: '70'
      enable-scale-to-zero: 'true'
    defaults:
      revision-timeout-seconds: '300'
      max-revision-timeout-seconds: '600'
    deployment:
      queue-sidecar-cpu-request: 25m
      queue-sidecar-memory-request: 400Mi
      queue-sidecar-memory-limit: 800Mi
  services:
  - name: kourier
    annotations:
      service.beta.kubernetes.io/aws-load-balancer-type: external
      service.beta.kubernetes.io/aws-load-balancer-nlb-target-type: ip
      service.beta.kubernetes.io/aws-load-balancer-scheme: internet-facing
```

```bash
kubectl create namespace knative-serving --dry-run=client -o yaml | kubectl apply -f -
kubectl create namespace knative-demo --dry-run=client -o yaml | kubectl apply -f -
kubectl apply -f knative-serving.yaml
kubectl wait --for=condition=Ready knativeserving/knative-serving -n knative-serving --timeout=600s
kubectl get deployments,pods,services -n knative-serving
```

### Paso 3: Instalar Kourier (Ingress ligero)

Kourier es una implementación de redes basada en Envoy para Knative. Es una opción adecuada cuando sus funciones compatibles satisfacen las necesidades de la carga de trabajo; cualquier ventaja en recursos o latencia requiere mediciones.

Operator instala Kourier a partir del paquete de Serving seleccionado. En este flujo de trabajo, el Service de la gateway está en `knative-serving`. Un manifiesto independiente de Kourier instalado manualmente normalmente usa `kourier-system`; no lo aplique sobre la instalación administrada por Operator. Inspeccione los recursos administrados:

```bash
# Operator-managed Kourier uses the KnativeServing namespace.
kubectl get deployment net-kourier-controller 3scale-kourier-gateway -n knative-serving
kubectl get service kourier -n knative-serving -o yaml
```

El recurso KnativeServing base anterior configura anotaciones del Service de Kourier para un **NLB administrado por AWS Load Balancer Controller**. El controlador, IAM y las subredes seleccionadas deben estar preparados previamente. Una anotación de Service no crea un ALB; para un ALB se necesita un controlador L7 y un diseño de enrutamiento adecuados. EKS Auto Mode utiliza otra ruta de administración de balanceadores de carga. Verifique la clase/anotaciones reales en lugar de asumir que todos los Services LoadBalancer de EKS tienen NLB de forma predeterminada:

```bash
kubectl get service kourier -n knative-serving -o jsonpath='{.spec.loadBalancerClass}{"\n"}{.metadata.annotations}{"\n"}'
```

### Paso 4: Configuración de DNS

Knative genera URL para cada Service con el formato `<service>.<namespace>.<domain>`. Debe configurar DNS para que estas URL se resuelvan en la gateway de Ingress.

#### Opción A: Magic DNS (sslip.io) -- Solo para desarrollo

sslip.io resuelve nombres compatibles con direcciones IP codificadas y resulta útil en entornos de desarrollo adecuados. Un nombre de host de balanceador de carga de AWS y las IP de backend que cambian no constituyen un mapeo DNS de producción duradero. Este flujo de trabajo de Operator usa un dominio explícito; el asistente de dominio predeterminado independiente no debe competir con la configuración propiedad de Operator.

```bash
# Inspect the address type; this Operator workflow uses an explicitly configured domain.
kubectl get service kourier -n knative-serving -o jsonpath='{.status.loadBalancer.ingress}'
kubectl get ksvc -n knative-demo
```

#### Opción B: DNS real con Amazon Route 53 -- Producción

Prepare un dominio/zona alojada que controle e inspeccione el cambio generado antes de aplicarlo. Al ejecutarse, los comandos siguientes actualizan esa zona; esta auditoría no los ejecutó. Use un único propietario de DNS (manual/IaC o ExternalDNS) por registro. ExternalDNS requiere su fuente `knative-serving`, permisos y un nombre de host que coincida con la Route/DomainMapping real; una anotación de nombre de host por sí sola no crea una ruta nueva de Knative.

```bash
# Review the intended zone/domain and wait for the NLB hostname before preparing a DNS change.
set -euo pipefail
export KOURIER_HOST
KOURIER_HOST=$(kubectl get service kourier -n knative-serving -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')
: "${KOURIER_HOST:?Wait for the load-balancer hostname}"
export KNATIVE_DOMAIN="knative.example.com"
export HOSTED_ZONE_ID="REPLACE_WITH_HOSTED_ZONE_ID"
python3 - <<'PYDNS'
import json, os
from pathlib import Path
host = os.environ["KOURIER_HOST"].strip()
if not host or any(c.isspace() for c in host):
    raise SystemExit("Invalid load-balancer hostname")
change = {"Changes": [{"Action": "UPSERT", "ResourceRecordSet": {
    "Name": "*." + os.environ["KNATIVE_DOMAIN"], "Type": "CNAME", "TTL": 300,
    "ResourceRecords": [{"Value": host}]
}}]}
Path("knative-dns-change.json").write_text(json.dumps(change, indent=2))
patch = {"spec": {"config": {"domain": {os.environ["KNATIVE_DOMAIN"]: ""}}}}
Path("knative-domain.patch.json").write_text(json.dumps(patch))
PYDNS
# These commands change the selected DNS zone and Operator configuration when run.
aws route53 change-resource-record-sets --hosted-zone-id "$HOSTED_ZONE_ID" --change-batch file://knative-dns-change.json
kubectl patch knativeserving knative-serving -n knative-serving --type merge --patch-file knative-domain.patch.json
```

### Paso 5: TLS con cert-manager

Serving 1.23 incluye la integración con cert-manager en su controlador. El antiguo repositorio net-certmanager independiente está archivado; no instale desde allí una versión 1.16/1.23 inexistente. Instale y configure por separado una versión compatible de cert-manager antes de habilitar la integración, incluida su propia identidad DNS01 de Route53 y acceso a la zona con privilegios mínimos.

```bash
kubectl get deployments -n cert-manager
kubectl get crd certificates.cert-manager.io clusterissuers.cert-manager.io
```

Guarde este parche de combinación para el recurso KnativeServing existente como `serving-tls.patch.yaml`. No es un ConfigMap independiente que deba aplicarse sobre el estado administrado por Operator:

```yaml
spec:
  config:
    network:
      certificate-class: cert-manager.certificate.networking.knative.dev
      external-domain-tls: Enabled
      http-protocol: Redirected
    certmanager:
      issuerRef: |
        group: cert-manager.io
        kind: ClusterIssuer
        name: letsencrypt-staging
```

Para la primera validación de DNS/IAM, utilice un ClusterIssuer de pruebas. Sustituya el contacto, la zona alojada y la región por valores revisados. Los certificados de pruebas no son de confianza pública; cambie a un emisor de producción solo después de validar el flujo del desafío y el ciclo de vida del certificado:

```yaml
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-staging
spec:
  acme:
    server: https://acme-staging-v02.api.letsencrypt.org/directory
    email: REPLACE_WITH_CERTIFICATE_CONTACT_EMAIL
    privateKeySecretRef:
      name: letsencrypt-staging-key
    solvers:
    - dns01:
        route53:
          region: us-west-2
          hostedZoneID: REPLACE_WITH_HOSTED_ZONE_ID
```

Guarde el emisor como `cluster-issuer.yaml` y el parche de Operator anterior como `serving-tls.patch.yaml`; luego aplíquelos en este orden:

```bash
# cert-manager and its Route 53 identity must already be configured.
kubectl apply -f cluster-issuer.yaml
kubectl wait --for=condition=Ready clusterissuer/letsencrypt-staging --timeout=180s
kubectl patch knativeserving knative-serving -n knative-serving --type merge --patch-file serving-tls.patch.yaml
# The integration starts in the Serving controller after the setting is effective.
kubectl get configmap config-network -n knative-serving -o yaml
kubectl rollout restart deployment/controller -n knative-serving
kubectl rollout status deployment/controller -n knative-serving --timeout=300s
```

### Paso 6: Selección del escalador automático HPA o KPA

Knative admite dos implementaciones de escalador automático. La elección afecta significativamente el comportamiento del escalado.

| Característica | KPA (Knative Pod Autoscaler) | HPA (Kubernetes HPA) |
|---------|------------------------------|----------------------|
| Escalado a cero | Sí | No |
| Métricas | Concurrencia, RPS | CPU, memoria, métricas personalizadas |
| Velocidad de escalado | Rápida (ventanas panic/stable) | Intervalos estándar de HPA |
| Configuración | Anotaciones de Knative | Especificación estándar de HPA |
| Ideal para | Cargas de trabajo HTTP y sensibles a la latencia | Cargas de trabajo limitadas por CPU/memoria |

Configure la clase predeterminada del escalador automático mediante Operator. La extensión HPA opcional y una API funcional de métricas de recursos de Kubernetes son requisitos previos para las Revisions de clase HPA; este parche incluye un manifiesto HPA fijado a una versión. Evite la administración duplicada si su distribución ya lo proporciona:

```yaml
spec:
  additionalManifests:
  - URL: https://github.com/knative/serving/releases/download/knative-v1.23.0/serving-hpa.yaml
  config:
    autoscaler:
      pod-autoscaler-class: kpa.autoscaling.knative.dev
      stable-window: 60s
      panic-window-percentage: '10'
      panic-threshold-percentage: '200'
      scale-to-zero-grace-period: 30s
      scale-to-zero-pod-retention-period: 0s
      target-burst-capacity: '211'
      requests-per-second-target-default: '200'
      container-concurrency-target-default: '100'
```

Guárdelo como `serving-autoscaler.patch.yaml` y combínelo con el recurso Operator existente. Al preparar el parche, conserve las demás entradas de `additionalManifests`:

```bash
kubectl patch knativeserving knative-serving -n knative-serving --type merge --patch-file serving-autoscaler.patch.yaml
kubectl get deployment autoscaler-hpa -n knative-serving
```

Anule la configuración por Revision en `spec.template.metadata.annotations` del Knative Service (lo siguiente es un fragmento de plantilla):

```yaml
metadata:
  annotations:
    autoscaling.knative.dev/class: "hpa.autoscaling.knative.dev"
    autoscaling.knative.dev/metric: "cpu"
    autoscaling.knative.dev/target: "70"
```

### Paso 7: Instalar Knative Eventing

```yaml
apiVersion: operator.knative.dev/v1beta1
kind: KnativeEventing
metadata:
  name: knative-eventing
  namespace: knative-eventing
spec:
  version: 1.23.0
  defaultBrokerClass: MTChannelBasedBroker
  config:
    default-ch-webhook:
      default-ch-config: "clusterDefault:\n  apiVersion: messaging.knative.dev/v1\n\
        \  kind: InMemoryChannel\n"
  sinkBindingSelectionMode: inclusion
```

```bash
kubectl create namespace knative-eventing --dry-run=client -o yaml | kubectl apply -f -
kubectl apply -f knative-eventing.yaml
kubectl wait --for=condition=Ready knativeeventing/knative-eventing -n knative-eventing --timeout=600s
kubectl get deployments,pods -n knative-eventing
kubectl get crd inmemorychannels.messaging.knative.dev integrationsources.sources.knative.dev
```

---

## Análisis detallado de Knative Serving {#knative-serving-deep-dive}

### Modelo de recursos

Knative Serving introduce cuatro recursos personalizados principales que trabajan en conjunto para administrar el ciclo de vida completo de una carga de trabajo serverless.

![Un Service es propietario de una Configuration y una Route; los cambios en la plantilla de la carga de trabajo crean especificaciones de Revision inmutables, mientras que las referencias externas pueden cambiar. Route envía porcentajes de tráfico configurados a Revisions conservadas; no siempre dirige el 100 % a la más reciente.](../.gitbook/assets/en-autoscaling-03-knative-2.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-autoscaling-03-knative-2.html)

| Recurso | Descripción |
|----------|-------------|
| **Service** (`ksvc`) | Recurso de nivel superior. Administra todo el ciclo de vida al ser propietario de una Configuration y una Route. La mayoría de los usuarios solo interactúa con Services. |
| **Configuration** | Describe la plantilla de la carga de trabajo; los cambios pertinentes en la plantilla crean una Revision. Los cambios solo en los metadatos o en el tráfico no necesariamente crean una. |
| **Revision** | Especificación inmutable de la carga de trabajo, con referencias externas que aún pueden cambiar. La retención/recolección de basura determina si una Revision antigua sigue disponible. |
| **Route** | Asigna el tráfico de red a una o varias Revisions. Permite implementaciones canary, versiones blue-green y la división del tráfico por porcentaje. |

### YAML completo de Knative Service

Proporcione primero la imagen, ServiceAccount y Secret referenciados. El controlador de Serving debe resolver las etiquetas/digest de los registros, mientras que el nodo debe poder descargar la imagen por separado; las credenciales del nodo de EKS por sí solas no establecen el acceso del controlador al registro. Las rutas de preparación y actividad deben coincidir con la aplicación real y no deberían causar reinicios en cascada por interrupciones de servicios dependientes.

Lo siguiente es un ejemplo de configuración, no una implementación de producción probada. Define un Knative Service con escalado automático explícito, límites de recursos, comprobaciones de estado y límites de escalado:

```yaml
apiVersion: serving.knative.dev/v1
kind: Service
metadata:
  name: order-api
  namespace: knative-demo
  labels:
    app.kubernetes.io/name: order-api
    app.kubernetes.io/part-of: ecommerce
    app.kubernetes.io/managed-by: knative
spec:
  template:
    metadata:
      annotations:
        autoscaling.knative.dev/class: kpa.autoscaling.knative.dev
        autoscaling.knative.dev/metric: concurrency
        autoscaling.knative.dev/target: '100'
        autoscaling.knative.dev/target-utilization-percentage: '70'
        autoscaling.knative.dev/min-scale: '2'
        autoscaling.knative.dev/max-scale: '50'
        autoscaling.knative.dev/initial-scale: '3'
        autoscaling.knative.dev/scale-down-delay: 15m
        autoscaling.knative.dev/window: 60s
      name: order-api-v1
    spec:
      containerConcurrency: 0
      timeoutSeconds: 300
      containers:
      - image: 123456789012.dkr.ecr.us-west-2.amazonaws.com/order-api:v1.2.3
        ports:
        - containerPort: 8080
          protocol: TCP
        env:
        - name: DB_HOST
          valueFrom:
            secretKeyRef:
              name: db-credentials
              key: host
        - name: LOG_LEVEL
          value: info
        resources:
          requests:
            cpu: 250m
            memory: 512Mi
          limits:
            cpu: 1000m
            memory: 1Gi
        readinessProbe:
          httpGet:
            path: /healthz
            port: 8080
          initialDelaySeconds: 5
          periodSeconds: 10
        livenessProbe:
          httpGet:
            path: /healthz
            port: 8080
          initialDelaySeconds: 15
          periodSeconds: 20
      serviceAccountName: order-api-sa
```

### División del tráfico: implementaciones canary

La división del tráfico permite trasladarlo gradualmente entre Revisions. Es la base de las estrategias de implementación canary y blue-green.

#### Implementación canary

Estos son ejercicios alternativos que parten del Service base completo anterior y de su Revision `order-api-v1` lista. Reemplace las imágenes y los nombres por artefactos verificados; cada cambio de plantilla necesita un nombre de Revision nuevo y sin usar. El parche JSON conserva las variables de entorno, ServiceAccount, sondas y configuración de recursos en lugar de reemplazar toda la lista de contenedores. Presupone que el ejemplo base tiene un único contenedor de entrada en el índice 0. Una etiqueta con el 0 % hace que una ruta esté disponible para las pruebas; no garantiza que haya toda la capacidad lista.

Guárdelo como `canary-template.patch.json`:

```json
[
  {
    "op": "add",
    "path": "/spec/traffic",
    "value": [
      {
        "revisionName": "order-api-v1",
        "percent": 100
      },
      {
        "revisionName": "order-api-v2",
        "percent": 0,
        "tag": "canary"
      }
    ]
  },
  {
    "op": "add",
    "path": "/spec/template/metadata/name",
    "value": "order-api-v2"
  },
  {
    "op": "replace",
    "path": "/spec/template/spec/containers/0/image",
    "value": "123456789012.dkr.ecr.us-west-2.amazonaws.com/order-api:v1.3.0"
  }
]
```

```bash
kubectl wait --for=condition=Ready revision/order-api-v1 -n knative-demo --timeout=300s
kubectl patch ksvc order-api -n knative-demo --type json --patch-file canary-template.patch.json
kubectl wait --for=jsonpath='{.status.latestCreatedRevisionName}'=order-api-v2 ksvc/order-api -n knative-demo --timeout=180s
kubectl wait --for=condition=Ready revision/order-api-v2 -n knative-demo --timeout=300s
kubectl get ksvc order-api -n knative-demo -o jsonpath='{.status.traffic}'

# Route10%, then50%, then100% only after validating each stage.
kubectl patch ksvc order-api -n knative-demo --type merge --patch '{"spec":{"traffic":[{"revisionName":"order-api-v1","percent":90},{"revisionName":"order-api-v2","percent":10,"tag":"canary"}]}}'
kubectl patch ksvc order-api -n knative-demo --type merge --patch '{"spec":{"traffic":[{"revisionName":"order-api-v1","percent":50},{"revisionName":"order-api-v2","percent":50,"tag":"canary"}]}}'
kubectl patch ksvc order-api -n knative-demo --type merge --patch '{"spec":{"traffic":[{"revisionName":"order-api-v1","percent":0},{"revisionName":"order-api-v2","percent":100,"tag":"canary"}]}}'
```

Lea la URL de etiqueta real desde `status.traffic`; depende de las plantillas de dominio/etiqueta y de la configuración TLS. Compruebe que Route esté lista, la configuración observada y las señales de la aplicación entre los cambios. Los porcentajes se aplican a la política de enrutamiento, no representan un recuento exacto en una muestra pequeña de solicitudes.

#### Implementación blue-green

Use esto como ejercicio independiente de `order-api-v1` base, o actualice el nombre estable para que coincida con la Revision que sirve actualmente de referencia verificada. Guarde lo siguiente como `green-template.patch.json`:

```json
[
  {
    "op": "add",
    "path": "/spec/traffic",
    "value": [
      {
        "revisionName": "order-api-v1",
        "percent": 100
      },
      {
        "revisionName": "order-api-green",
        "percent": 0,
        "tag": "green"
      }
    ]
  },
  {
    "op": "add",
    "path": "/spec/template/metadata/name",
    "value": "order-api-green"
  },
  {
    "op": "replace",
    "path": "/spec/template/spec/containers/0/image",
    "value": "123456789012.dkr.ecr.us-west-2.amazonaws.com/order-api:v2.0.0"
  }
]
```

```bash
kubectl patch ksvc order-api -n knative-demo --type json --patch-file green-template.patch.json
kubectl wait --for=jsonpath='{.status.latestCreatedRevisionName}'=order-api-green ksvc/order-api -n knative-demo --timeout=180s
kubectl wait --for=condition=Ready revision/order-api-green -n knative-demo --timeout=300s
kubectl get ksvc order-api -n knative-demo -o jsonpath='{.status.traffic}'
# Validate the green tag URL and capacity before requesting this switch.
kubectl patch ksvc order-api -n knative-demo --type merge --patch '{"spec":{"traffic":[{"revisionName":"order-api-v1","percent":0},{"revisionName":"order-api-green","percent":100,"tag":"green"}]}}'
```

El cambio de tráfico se reconcilia de forma asíncrona; las conexiones y solicitudes en curso todavía pueden usar la Revision anterior. Conserve la Revision antigua y sus dependencias externas para poder revertir, y mida la propagación/preparación reales. Estos comandos no se ejecutaron en un clúster.

### Comportamiento del escalado a cero

El escalado a cero es una característica definitoria de Knative Serving. Cuando una Revision puede escalarse a cero, su ventana de inactividad, demora de escalado hacia abajo, retención y disponibilidad interna del enrutamiento influyen en el momento en que se elimina el último Pod. Cuando llega una solicitud nueva, Activator la almacena en búfer, activa el escalado y la reenvía cuando un Pod está listo.

![El escalado a cero prepara la ruta de Activator antes de eliminar el último Pod. Una nueva solicitud puede esperar a que haya capacidad lista dentro de los límites de búfer/tiempo de espera; Activator puede permanecer en la ruta según la configuración de capacidad para ráfagas.](../.gitbook/assets/en-autoscaling-03-knative-3.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-autoscaling-03-knative-3.html)

Parámetros clave que controlan el escalado a cero:

| Anotación / configuración | Valor predeterminado | Descripción |
|---------------------|---------|-------------|
| `scale-to-zero-grace-period` (global) | 30 s | Límite superior para la preparación interna del enrutamiento desde cero antes de eliminar la última réplica; no es un temporizador garantizado de retención por inactividad. |
| `scale-to-zero-pod-retention-period` (global) | 0 s | Retención mínima del último Pod después de que el escalador automático decide escalar a cero. |
| `autoscaling.knative.dev/scale-to-zero-pod-retention-period` (por Revision) | heredado | Anulación por Revision del período de retención global. |
| `enable-scale-to-zero` (global) | true | Interruptor principal. Establezca el valor en false para deshabilitar el escalado a cero en todo el clúster. |

### Escalado basado en la concurrencia

KPA de Knative escala según la concurrencia observada (solicitudes en curso) o las solicitudes por segundo (RPS). El algoritmo mantiene dos ventanas:

- **Ventana estable** (60 s de forma predeterminada): la concurrencia media durante este período determina la decisión de escala en estado estable.
- **Ventana de pánico** (6 s de forma predeterminada, es decir, el 10 % de la ventana estable): si la concurrencia media en esta ventana supera el umbral de pánico (el 200 % del objetivo de forma predeterminada), el sistema escala rápidamente hacia arriba.

**Anotaciones clave:**

| Anotación | Ejemplo | Descripción |
|------------|---------|-------------|
| `autoscaling.knative.dev/metric` | `"concurrency"` o `"rps"` | Métrica que se usará para el escalado. |
| `autoscaling.knative.dev/target` | `"100"` | Valor objetivo de la métrica (por ejemplo, 100 solicitudes concurrentes por Pod). |
| `autoscaling.knative.dev/target-utilization-percentage` | `"70"` | El Autoscaler intenta mantener el uso medio en este porcentaje del objetivo. Objetivo efectivo = objetivo * uso / 100. |
| `spec.template.spec.containerConcurrency` | `0` | Límite de concurrencia de las solicitudes reenviadas por Pod; `0` deshabilita este límite estricto. Se siguen aplicando la espera/rechazo limitados y el escalado automático. El valor `1` no hace que los hilos de la aplicación ni todas las réplicas sean seriales a escala global. |

**Fórmula de escalado:**

```
desiredReplicas = ceil( observedConcurrency / (target * targetUtilization / 100) )
```

Por ejemplo, con `target=100`, `targetUtilization=70%` y 350 solicitudes concurrentes observadas:

```
desiredReplicas = ceil(350 / (100 * 0.70)) = ceil(350 / 70) = ceil(5.0) = 5
```

### Optimización de arranques en frío

Los arranques en frío —la penalización de latencia al escalar desde cero— son una preocupación habitual. Knative ofrece varios mecanismos para mitigarlos:

| Estrategia | Configuración | Compensación |
|----------|---------------|-----------|
| **minScale** | `autoscaling.knative.dev/min-scale: "2"` | Mantiene capacidad de referencia durante la inactividad normal; las Revisions nuevas, los reinicios y el escalado hacia arriba aún pueden inicializarse en frío. |
| **initialScale** | `autoscaling.knative.dev/initial-scale: "3"` | Número de Pods que se crean al implementar por primera vez una Revision. No evita que posteriormente se escale a cero. |
| **scale-down-delay** | `autoscaling.knative.dev/scale-down-delay: "15m"` | Retrasa las decisiones de escalado hacia abajo. Es útil para cargas de trabajo con ráfagas, ya que evita arranques en frío frecuentes. |
| **Almacenamiento en caché de imágenes de contenedor** | Use el almacenamiento en caché de imágenes a nivel de nodo de EKS o DaemonSets de descarga previa | Reduce el tiempo de descarga del contenedor durante el arranque en frío. |
| **Imágenes base ligeras** | Use imágenes distroless o basadas en Alpine | Reduce el tamaño de la imagen y el tiempo de descarga. |
| **Calentamiento de la aplicación** | Implemente sondas de preparación que cumplan el contrato de preparación real | Evita anunciar la preparación antes de tiempo; el rendimiento con carga completa aún debe medirse. |

```yaml
apiVersion: serving.knative.dev/v1
kind: Service
metadata:
  name: latency-critical-api
  namespace: knative-demo
spec:
  template:
    metadata:
      annotations:
        autoscaling.knative.dev/min-scale: '3'
        autoscaling.knative.dev/initial-scale: '5'
        autoscaling.knative.dev/scale-down-delay: 10m
        autoscaling.knative.dev/target: '50'
        autoscaling.knative.dev/window: 30s
    spec:
      containerConcurrency: 100
      containers:
      - image: 123456789012.dkr.ecr.us-west-2.amazonaws.com/api:v1.0.0
        ports:
        - containerPort: 8080
        readinessProbe:
          httpGet:
            path: /ready
            port: 8080
          initialDelaySeconds: 3
          periodSeconds: 5
```

### Services privados y públicos

De forma predeterminada, los Knative Services se exponen externamente a través de la gateway de Ingress. Puede hacer que un Service solo sea interno al clúster:

```yaml
apiVersion: serving.knative.dev/v1
kind: Service
metadata:
  name: internal-processor
  namespace: knative-demo
  labels:
    networking.knative.dev/visibility: cluster-local
spec:
  template:
    spec:
      containers:
      - image: 123456789012.dkr.ecr.us-west-2.amazonaws.com/processor:v1.0.0
```

La etiqueta cluster-local cambia la visibilidad del enrutamiento de Knative y las URL internas generadas. No es una política de autenticación ni un límite completo de aislamiento de red; las rutas de red privadas, NetworkPolicy y la autorización de la aplicación siguen siendo importantes.

La versión seleccionada no incluye una configuración `config-network.visibility`. Aplique la etiqueta de visibilidad a cada Service o aplíquela mediante una política de admisión adecuada. `default-external-scheme` solo afecta los esquemas de URL externas generadas; por sí solo no hace que un Service sea privado ni configura TLS. Lo siguiente es un fragmento de metadatos de Service:

```yaml
metadata:
  labels:
    networking.knative.dev/visibility: cluster-local
```

---

## Análisis detallado de Knative Eventing {#knative-eventing-deep-dive}

### Fuentes de eventos

Las fuentes de eventos son recursos de Knative que conectan sistemas externos con la malla de eventos. Cada Source emite CloudEvents a un sink configurado (un Broker, Channel o Knative Service directamente).

#### ApiServerSource

Observa el servidor de API de Kubernetes para detectar eventos de recursos y los reenvía como CloudEvents:

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: k8s-events-sa
  namespace: knative-demo
---
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: k8s-events-reader
  namespace: knative-demo
rules:
- apiGroups:
  - ''
  resources:
  - pods
  verbs:
  - get
  - list
  - watch
- apiGroups:
  - apps
  resources:
  - deployments
  verbs:
  - get
  - list
  - watch
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: k8s-events-reader
  namespace: knative-demo
subjects:
- kind: ServiceAccount
  name: k8s-events-sa
  namespace: knative-demo
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: Role
  name: k8s-events-reader
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: knative-demo-namespace-discovery
rules:
- apiGroups:
  - ''
  resources:
  - namespaces
  verbs:
  - get
  - list
  - watch
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: knative-demo-namespace-discovery
subjects:
- kind: ServiceAccount
  name: k8s-events-sa
  namespace: knative-demo
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: knative-demo-namespace-discovery
---
apiVersion: sources.knative.dev/v1
kind: ApiServerSource
metadata:
  name: k8s-events
  namespace: knative-demo
spec:
  serviceAccountName: k8s-events-sa
  mode: Reference
  resources:
  - apiVersion: v1
    kind: Pod
  - apiVersion: apps/v1
    kind: Deployment
  sink:
    ref:
      apiVersion: eventing.knative.dev/v1
      kind: Broker
      name: default
  namespaceSelector:
    matchLabels:
      kubernetes.io/metadata.name: knative-demo
```

#### SinkBinding

La configuración de Eventing seleccionada usa el modo inclusion. Incluya solo el namespace de demostración en la inyección de bindings y asegúrese de que el Deployment sujeto exista en ese namespace con las etiquetas/nombre de metadatos correspondientes. Los cambios en una carga de trabajo que ya está en ejecución pueden requerir su ciclo normal de implementación antes de que se usen las nuevas variables de entorno inyectadas:

```bash
kubectl label namespace knative-demo bindings.knative.dev/include=true --overwrite
```

Inyecta variables de entorno (específicamente, `K_SINK`) en cualquier carga de trabajo de Kubernetes para que pueda enviar eventos a un sink sin codificar el destino:

```yaml
apiVersion: sources.knative.dev/v1
kind: SinkBinding
metadata:
  name: order-producer-binding
  namespace: knative-demo
spec:
  subject:
    apiVersion: apps/v1
    kind: Deployment
    name: order-producer
  sink:
    ref:
      apiVersion: eventing.knative.dev/v1
      kind: Broker
      name: default
  ceOverrides:
    extensions:
      producer: order-system
```

La aplicación debe leer `K_SINK` y aplicar `K_CE_OVERRIDES`; SinkBinding no reescribe solicitudes Python arbitrarias salientes. El productor siguiente usa codificación HTTP estructurada (el cuerpo completo de CloudEvent con el tipo de contenido correspondiente), un tiempo de espera limitado y comprobaciones de estado. Mantenga un solo `event_id` en los reintentos del mismo evento lógico:

```python
import json
import os
import re

import requests
from cloudevents.http import CloudEvent
from cloudevents.conversion import to_structured

CORE_ATTRIBUTES = {"specversion", "id", "source", "type", "time", "subject", "datacontenttype", "dataschema"}


def emit_order_event(order_id, event_type, data, event_id):
    """Use one stable event_id for retries of the same logical event."""
    attributes = {
        "specversion": "1.0", "id": event_id,
        "type": f"com.example.order.{event_type}",
        "source": "/orders/api", "subject": f"order/{order_id}",
        "datacontenttype": "application/json",
    }
    overrides = json.loads(os.environ.get("K_CE_OVERRIDES", "{}"))
    for key, value in overrides.get("extensions", {}).items():
        if key in CORE_ATTRIBUTES or not re.fullmatch(r"[a-z0-9]+", key):
            raise ValueError("Only valid extension attributes may be overridden")
        attributes[key] = value
    event = CloudEvent(attributes, data)
    headers, body = to_structured(event)
    response = requests.post(
        os.environ["K_SINK"], data=body, headers=headers, timeout=(3, 10)
    )
    response.raise_for_status()
    return response.status_code
```

#### KafkaSource

KafkaSource/KafkaChannel requieren la extensión Kafka correspondiente y un clúster Kafka existente y configurado (incluidos bootstrap/TLS/SASL y suficientes brokers para el factor de replicación solicitado). Combine estas URL de addons 1.23.2 con los elementos `additionalManifests` existentes en el recurso KnativeEventing; no habilite simultáneamente otra vía de administración para el mismo addon. Guárdelo como eventing-kafka.patch.yaml:

```yaml
spec:
  additionalManifests:
  - URL: https://github.com/knative-extensions/eventing-kafka-broker/releases/download/knative-v1.23.2/eventing-kafka-controller.yaml
  - URL: https://github.com/knative-extensions/eventing-kafka-broker/releases/download/knative-v1.23.2/eventing-kafka-source.yaml
  - URL: https://github.com/knative-extensions/eventing-kafka-broker/releases/download/knative-v1.23.2/eventing-kafka-channel.yaml
```

```bash
kubectl patch knativeeventing knative-eventing -n knative-eventing --type merge --patch-file eventing-kafka.patch.yaml
GENERATION=$(kubectl get knativeeventing knative-eventing -n knative-eventing -o jsonpath='{.metadata.generation}')
kubectl wait --for=jsonpath='{.status.observedGeneration}'="$GENERATION" knativeeventing/knative-eventing -n knative-eventing --timeout=600s
kubectl wait --for=condition=Ready knativeeventing/knative-eventing -n knative-eventing --timeout=600s
kubectl get crd kafkasources.sources.knative.dev kafkachannels.messaging.knative.dev
```

Consume mensajes de temas de Apache Kafka y los entrega como CloudEvents:

```yaml
apiVersion: sources.knative.dev/v1
kind: KafkaSource
metadata:
  name: payment-events
  namespace: knative-demo
spec:
  consumerGroup: knative-payment-consumer
  bootstrapServers:
  - kafka-bootstrap.kafka.svc.cluster.local:9092
  topics:
  - payment-events
  sink:
    ref:
      apiVersion: eventing.knative.dev/v1
      kind: Broker
      name: default
  net:
    sasl:
      enable: true
      type:
        secretKeyRef:
          name: kafka-credentials
          key: sasl-type
      user:
        secretKeyRef:
          name: kafka-credentials
          key: username
      password:
        secretKeyRef:
          name: kafka-credentials
          key: password
    tls:
      enable: true
```

#### SQSSource (AWS)

IntegrationSource de core 1.23 admite SQS y reemplaza aquí el ejemplo archivado de TriggerMesh. Es una API alfa; verifique la CRD instalada y las imágenes del adaptador. La cola dedicada y su rol de IAM deben existir de antemano. Esta fuente consume/elimina mensajes cuando se ejecuta; durante la auditoría no se implementó ninguna fuente:

```bash
# Verify the core IntegrationSource CRD
kubectl get crd integrationsources.sources.knative.dev
```

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: sqs-event-source
  namespace: knative-demo
  annotations:
    eks.amazonaws.com/role-arn: arn:aws:iam::123456789012:role/KnativeSqsSourceRole
---
apiVersion: sources.knative.dev/v1alpha1
kind: IntegrationSource
metadata:
  name: sqs-order-events
  namespace: knative-demo
spec:
  aws:
    sqs:
      arn: arn:aws:sqs:us-west-2:123456789012:knative-demo-orders
      region: us-west-2
      autoCreateQueue: false
      deleteAfterRead: true
      visibilityTimeout: 120
    auth:
      serviceAccountName: sqs-event-source
  sink:
    ref:
      apiVersion: eventing.knative.dev/v1
      kind: Broker
      name: default
```

El ejemplo usa un ServiceAccount dedicado con un rol IRSA existente. Limite los permisos ReceiveMessage/DeleteMessage/GetQueueAttributes/GetQueueUrl a la cola de prueba y valide los acuses de recibo, los tiempos de espera de visibilidad y el comportamiento ante errores. autoCreateQueue es false. El tipo/source de CloudEvent emitido proviene del adaptador; inspecciónelo antes de copiar los filtros manuales de Trigger para eventos de pedido. EKS Pod Identity es otra opción de credenciales cuando el cómputo EKS seleccionado, el agente y el SDK la admiten; Fargate no admite EKS Pod Identity.

### Patrón Broker/Trigger

El patrón Broker/Trigger proporciona enrutamiento de eventos basado en contenido. Un Broker actúa como concentrador de eventos; los Triggers filtran eventos por atributos de CloudEvent y los enrutan a suscriptores.

#### Ejemplo completo de Broker/Trigger

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: demo-broker-channel
  namespace: knative-demo
data:
  channel-template-spec: |
    apiVersion: messaging.knative.dev/v1
    kind: InMemoryChannel
---
apiVersion: eventing.knative.dev/v1
kind: Broker
metadata:
  name: default
  namespace: knative-demo
  annotations:
    eventing.knative.dev/broker.class: MTChannelBasedBroker
spec:
  config:
    apiVersion: v1
    kind: ConfigMap
    name: demo-broker-channel
    namespace: knative-demo
  delivery:
    retry: 5
    backoffPolicy: exponential
    backoffDelay: PT2S
    deadLetterSink:
      ref:
        apiVersion: serving.knative.dev/v1
        kind: Service
        name: dead-letter-handler
---
apiVersion: eventing.knative.dev/v1
kind: Trigger
metadata:
  name: order-created-trigger
  namespace: knative-demo
spec:
  broker: default
  filter:
    attributes:
      type: com.example.order.created
      source: /orders/api
  subscriber:
    ref:
      apiVersion: serving.knative.dev/v1
      kind: Service
      name: order-processor
---
apiVersion: eventing.knative.dev/v1
kind: Trigger
metadata:
  name: payment-processed-trigger
  namespace: knative-demo
spec:
  broker: default
  filter:
    attributes:
      type: com.example.payment.processed
  subscriber:
    ref:
      apiVersion: serving.knative.dev/v1
      kind: Service
      name: payment-reconciler
  delivery:
    retry: 10
    backoffPolicy: exponential
    backoffDelay: PT5S
    deadLetterSink:
      ref:
        apiVersion: serving.knative.dev/v1
        kind: Service
        name: payment-dead-letter
---
apiVersion: eventing.knative.dev/v1
kind: Trigger
metadata:
  name: analytics-trigger
  namespace: knative-demo
spec:
  broker: default
  subscriber:
    ref:
      apiVersion: serving.knative.dev/v1
      kind: Service
      name: analytics-collector
```

### Estándar CloudEvents

La entrega de eventos de Knative Eventing utiliza la especificación [CloudEvents](https://cloudevents.io/) (v1.0); las operaciones del plano de control de Kubernetes mantienen sus propias API. CloudEvents define un sobre común con atributos obligatorios y opcionales:

| Atributo | Obligatorio | Ejemplo | Descripción |
|-----------|----------|---------|-------------|
| `specversion` | Sí | `"1.0"` | Versión de la especificación CloudEvents. |
| `type` | Sí | `"com.example.order.created"` | Tipo de evento. Se usa para el enrutamiento mediante Triggers. |
| `source` | Sí | `"/orders/api"` | Origen del evento. Se combina con el tipo para filtrar. |
| `id` | Sí | `"evt-abc123"` | Identificador único dentro de su origen; deduplique con `(source, id)`. |
| `time` | No | `"2025-06-15T10:30:00Z"` | Marca de tiempo de la ocurrencia del evento. |
| `datacontenttype` | No | `"application/json"` | Tipo de contenido del atributo `data`. |
| `subject` | No | `"order-12345"` | Asunto del evento en el contexto del origen. |
| `data` | No | `{"orderId": "12345"}` | Carga del evento. |

#### Ejemplo de consumidor que solo confirma la recepción

Guarde esta aplicación Flask independiente como `app.py` y ejecútela con un servidor WSGI. Valida CloudEvents y confirma su recepción; no implementa transacciones de pedidos/pagos ni procesamiento duradero. Los consumidores de aplicaciones deben completar la transacción/idempotencia prevista antes de confirmar.

```python
import json

from flask import Flask, request
from cloudevents.http import from_http


def create_app():
    app = Flask(__name__)
    app.config["MAX_CONTENT_LENGTH"] = 1024 * 1024

    @app.post("/")
    def receive_event():
        try:
            event = from_http(request.headers, request.get_data())
            metadata = {key: event[key] for key in ("source", "id", "type")}
        except Exception:
            # This boundary converts malformed input into a client error.
            return "invalid CloudEvent", 400
        app.logger.info("Received CloudEvent metadata: %s", json.dumps(metadata))
        # Receipt-only demo. Real consumers must commit processing before acknowledging.
        return "", 204

    return app
```

### Patrón Channel/Subscription

Cree primero todos los suscriptores/Channels de respuesta referenciados. Un destino de respuesta recibe un CloudEvent válido devuelto por el suscriptor; una respuesta vacía 204 de confirmación no genera un evento de respuesta. La durabilidad de Kafka también depende de la replicación/retención/confirmaciones del broker y de la gestión de errores, no solo del tipo KafkaChannel.

El patrón Channel/Subscription proporciona pub-sub directo sin filtrado basado en contenido. Cada Subscription de un Channel recibe todos los eventos.

```yaml
apiVersion: messaging.knative.dev/v1
kind: KafkaChannel
metadata:
  name: audit-events
  namespace: knative-demo
spec:
  numPartitions: 6
  replicationFactor: 3
  retentionDuration: PT168H
---
apiVersion: messaging.knative.dev/v1
kind: Subscription
metadata:
  name: audit-log-subscription
  namespace: knative-demo
spec:
  channel:
    apiVersion: messaging.knative.dev/v1
    kind: KafkaChannel
    name: audit-events
  subscriber:
    ref:
      apiVersion: serving.knative.dev/v1
      kind: Service
      name: audit-logger
  reply:
    ref:
      apiVersion: serving.knative.dev/v1
      kind: Service
      name: audit-response-handler
---
apiVersion: messaging.knative.dev/v1
kind: Subscription
metadata:
  name: compliance-subscription
  namespace: knative-demo
spec:
  channel:
    apiVersion: messaging.knative.dev/v1
    kind: KafkaChannel
    name: audit-events
  subscriber:
    ref:
      apiVersion: serving.knative.dev/v1
      kind: Service
      name: compliance-checker
  delivery:
    deadLetterSink:
      ref:
        apiVersion: serving.knative.dev/v1
        kind: Service
        name: dead-letter-handler
    retry: 3
    backoffPolicy: linear
    backoffDelay: PT10S
```

### Dead Letter Sink

Cuando la política de entrega configurada no puede entregar un evento a su suscriptor, la implementación puede intentar enviarlo al DLS configurado. El controlador debe persistirlo/procesarlo antes de confirmar; el nombre de un Service DLS o una variable S3_BUCKET por sí solos no crean comportamiento de almacenamiento, permisos ni una garantía de que no se pierdan datos.

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: dead-letter-writer
  namespace: knative-demo
  annotations:
    eks.amazonaws.com/role-arn: arn:aws:iam::123456789012:role/KnativeDeadLetterWriterRole
---
apiVersion: serving.knative.dev/v1
kind: Service
metadata:
  name: dead-letter-handler
  namespace: knative-demo
  labels:
    networking.knative.dev/visibility: cluster-local
spec:
  template:
    metadata:
      annotations:
        autoscaling.knative.dev/min-scale: '1'
    spec:
      containers:
      - image: 123456789012.dkr.ecr.us-west-2.amazonaws.com/dead-letter:v1.0.0
        env:
        - name: S3_BUCKET
          value: REPLACE_WITH_EXISTING_BUCKET
        - name: AWS_REGION
          value: us-west-2
        ports:
        - containerPort: 8080
        command:
        - gunicorn
        args:
        - --bind
        - 0.0.0.0:8080
        - --workers
        - '1'
        - --threads
        - '4'
        - --timeout
        - '90'
        - --graceful-timeout
        - '60'
        - app:create_app()
      serviceAccountName: dead-letter-writer
      timeoutSeconds: 60
```

La configuración de entrega puede existir en los niveles de Broker, Trigger y Subscription, con compatibilidad y herencia específicas de la implementación. Verifique la clase seleccionada y su estado, incluido el DLS resuelto. Un DLS configurado también puede fallar; no garantiza que no se pierdan datos.

#### Ejemplo de controlador de mensajes fallidos respaldado por S3

Compile este archivo `app.py` independiente con Flask, CloudEvents, boto3 y Gunicorn. Use un bucket protegido existente, un ServiceAccount de carga de trabajo dedicado con permiso `s3:PutObject` limitado, los permisos KMS necesarios y una ruta de red verificada. Configure `S3_BUCKET` y `AWS_REGION`; no incruste credenciales estáticas de AWS. El contenedor debe ejecutar `gunicorn --bind 0.0.0.0:8080 --workers 1 --threads 4 --timeout 90 --graceful-timeout 60 app:create_app()`. Ajuste estos tiempos de espera de ejemplo a los valores de terminación de Knative/proxy/Pod.

```python
import base64
import hashlib
import json
import os

import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError
from cloudevents.http import from_http
from flask import Flask, request


def create_app(s3_client=None):
    app = Flask(__name__)
    app.config["MAX_CONTENT_LENGTH"] = 1024 * 1024
    bucket = os.environ["S3_BUCKET"]
    if s3_client is None:
        # Create once per application worker; IRSA/Pod Identity uses the credential chain.
        s3_client = boto3.client(
            "s3", region_name=os.environ["AWS_REGION"],
            config=Config(connect_timeout=3, read_timeout=10,
                          retries={"mode": "standard", "total_max_attempts": 2}),
        )

    @app.post("/")
    def store_dead_letter():
        raw_body = request.get_data()
        try:
            event = from_http(request.headers, raw_body)
            source, event_id = str(event["source"]), str(event["id"])
        except Exception:
            return "invalid CloudEvent", 400
        identity = json.dumps([source, event_id], ensure_ascii=False,
                              separators=(",", ":")).encode("utf-8")
        key = "dead-letters/" + hashlib.sha256(identity).hexdigest() + ".json"
        record = {
            "source": source, "id": event_id,
            "content_type": request.headers.get("Content-Type", "application/octet-stream"),
            # Preserve CloudEvents transport attributes, never Authorization/Cookie headers.
            "ce_headers": {k.lower(): v for k, v in request.headers.items()
                           if k.lower().startswith("ce-")},
            "body_base64": base64.b64encode(raw_body).decode("ascii"),
        }
        try:
            s3_client.put_object(
                Bucket=bucket, Key=key,
                Body=json.dumps(record, ensure_ascii=False).encode("utf-8"),
                ContentType="application/json", IfNoneMatch="*",
            )
        except ClientError as exc:
            # HTTP boundary: acknowledge a stored duplicate; retry other storage failures.
            status = exc.response.get("ResponseMetadata", {}).get("HTTPStatusCode")
            if status == 412:
                return "", 204
            app.logger.error("DLS storage failed: %s", exc.response.get("Error", {}).get("Code"))
            return "storage unavailable", 503
        except BotoCoreError as exc:
            app.logger.error("DLS storage unavailable: %s", type(exc).__name__)
            return "storage unavailable", 503
        return "", 204

    return app
```

El controlador almacena el cuerpo original en Base64 y solo los encabezados de transporte de CloudEvents, por lo que conserva los eventos binarios y excluye los encabezados Authorization/Cookie. Una clave determinista `(source, id)` junto con una escritura condicional evita sobrescribir un evento existente; 412 confirma la existencia de una clave, mientras que 409 y otros errores de almacenamiento devuelven 503 para que se reintente según la política de entrega. La retención/eliminación y la reutilización de ID por parte del productor afectan la deduplicación; esto no garantiza un procesamiento empresarial exactamente una vez. Se rechazan las solicitudes de más de 1 MiB. El código se probó con simulaciones locales, no con un bucket activo ni una implementación de Eventing.

### Filtrado de eventos

Los Triggers admiten el filtrado por atributos y extensiones de CloudEvent.

#### Filtrado de atributos

```yaml
spec:
  filter:
    attributes:
      type: com.example.order.created
      source: /orders/api
```

Este Trigger se activa solo cuando coinciden `type` Y `source` (AND lógico).

#### Filtrado de extensiones

Puede filtrar por extensiones personalizadas de CloudEvent establecidas por los productores:

```yaml
spec:
  filter:
    attributes:
      type: com.example.order.created
      myextension: priority-high
```

#### Varios Triggers para la lógica OR

`spec.filter.attributes` heredado combina atributos con AND. El `spec.filters` actual admite expresiones más avanzadas, como `any`, `all` y `not`. Los Triggers múltiples son otra opción, pero las coincidencias superpuestas pueden producir duplicados. Use una forma de filtro a la vez y verifique la compatibilidad del broker:

```yaml
apiVersion: eventing.knative.dev/v1
kind: Trigger
metadata:
  name: order-created
  namespace: knative-demo
spec:
  broker: default
  filter:
    attributes:
      type: com.example.order.created
  subscriber:
    ref:
      apiVersion: serving.knative.dev/v1
      kind: Service
      name: notification-service
---
apiVersion: eventing.knative.dev/v1
kind: Trigger
metadata:
  name: order-cancelled
  namespace: knative-demo
spec:
  broker: default
  filter:
    attributes:
      type: com.example.order.cancelled
  subscriber:
    ref:
      apiVersion: serving.knative.dev/v1
      kind: Service
      name: notification-service
```

---

## Comparación entre KEDA y Knative {#keda-vs-knative-comparison}

Tanto KEDA como Knative permiten el escalado basado en eventos en Kubernetes, pero operan en distintos niveles de abstracción y cumplen funciones complementarias.

### Diferencias en el modelo de escalado

| Aspecto | KEDA | Knative |
|--------|------|---------|
| **Nivel de abstracción** | Amplía HPA con fuentes de métricas personalizadas | Plataforma serverless completa (implementación, enrutamiento, escalado) |
| **Mecanismo de escalado** | ScaledObject: activación del operador más HPA; ScaledJob: creación directa de Jobs | KPA o la extensión HPA opcional |
| **Métrica principal** | Métricas externas (profundidad de colas, filas de BD, personalizadas) | Concurrencia HTTP / RPS |
| **Tipo de carga de trabajo** | Cualquier Deployment, StatefulSet o Job | Knative Service (administra su propio Deployment) |
| **CRD** | ScaledObject, ScaledJob, TriggerAuthentication | Service, Configuration, Revision, Route |
| **Enrutamiento integrado** | No | Sí (división del tráfico, revisiones, canary) |
| **Eventing integrado** | No (se centra solo en el escalado) | Sí (Broker/Trigger, Channel/Subscription) |

### Diferencias en el comportamiento del escalado a cero

| Comportamiento | KEDA | Knative (KPA) |
|----------|------|---------------|
| Desencadenante del escalado a cero | Los desencadenantes de activación configurados quedan inactivos con cero habilitado; también importan el comportamiento de cooldown/errores | Elegibilidad por inactividad/escalado hacia abajo, retención y preparación del enrutamiento |
| Mecanismo de activación | El operador activa las réplicas distintas de cero según la configuración de desencadenador/mínimo/inactividad | Activator almacena solicitudes en búfer dentro de límites y activa el escalado |
| Almacenamiento de solicitudes en búfer | KEDA principal no almacena solicitudes HTTP en búfer; existe un complemento HTTP independiente | Activator las almacena en búfer dentro de los límites de capacidad y tiempo de espera |
| Período de cooldown | `cooldownPeriod` en ScaledObject | `scale-to-zero-grace-period` + `stable-window` |
| Jobs | ScaledJob deja de crear Jobs mientras está inactivo; los Jobs existentes pueden continuar | Serving administra Revisions de cargas de trabajo HTTP, no el ciclo de vida de Jobs por lotes |

### Funciones en una arquitectura basada en eventos

![ScaledObject de KEDA usa la activación del operador y HPA para las réplicas distintas de cero de workers; ScaledJob crea Jobs por separado. Knative Eventing enruta CloudEvents a los consumidores configurados, cuyo escalado y almacenamiento en búfer dependen de su implementación.](../.gitbook/assets/en-autoscaling-03-knative-4.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-autoscaling-03-knative-4.html)

### Cuándo usar KEDA o Knative

| Caso de uso | Recomendación | Motivo |
|----------|-------------|--------|
| Escalar workers según la profundidad de la cola SQS | **KEDA** | KEDA tiene un escalador SQS nativo; no se necesita enrutamiento HTTP. |
| Implementar API HTTP con escalado automático y división del tráfico | **Knative** | Serving proporciona administración de revisiones, división del tráfico y escalado automático compatible con HTTP. |
| Escalar según métricas de Prometheus | **KEDA** | El escalador de Prometheus de KEDA es maduro y está bien probado. |
| Microservicios basados en eventos con CloudEvents | **Knative** | Eventing proporciona Broker/Trigger, gestión de mensajes fallidos y compatibilidad con CloudEvents. |
| Jobs programados / procesamiento por lotes basado en eventos | **CronJob / KEDA** | Use CronJob de Kubernetes para un Job programado; ScaledJob crea Jobs según la demanda de eventos. Un Trigger Cron de KEDA proporciona un objetivo de réplicas basado en una ventana, no escala un CronJob. |
| CPU/memoria más activación desde cero | **Requiere una señal de activación externa** | Las métricas que solo usan CPU/memoria no pueden medir un worker ausente; combine un desencadenante de eventos apropiado en lugar de prometer activación desde cero con esas métricas por sí solas. |
| Plataforma serverless para desarrolladores | **Knative** | Abstracción de nivel superior; los desarrolladores implementan mediante `kn service create`. |

### Uso conjunto de KEDA y Knative

KEDA y Knative no se excluyen mutuamente. Una arquitectura habitual usa:

- **Knative Serving** para servicios orientados a HTTP (API y aplicaciones web) con escalado automático basado en la concurrencia.
- **KEDA** para workers en segundo plano (consumidores de colas y procesadores por lotes) con escalado automático basado en métricas externas.
- **Knative Eventing** para el enrutamiento de eventos. SinkBinding configura el destino/anulaciones de los productores; no permite activar un worker HTTP arbitrario con cero réplicas. Use una ruta adecuada de cola/adaptador y un único responsable del escalado por carga de trabajo.

```yaml
apiVersion: keda.sh/v1alpha1
kind: TriggerAuthentication
metadata:
  name: keda-aws-credentials
  namespace: knative-demo
spec:
  podIdentity:
    provider: aws
    identityOwner: keda
---
apiVersion: serving.knative.dev/v1
kind: Service
metadata:
  name: event-enricher
  namespace: knative-demo
spec:
  template:
    spec:
      containers:
      - image: event-enricher:v1
---
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: sqs-worker-scaler
  namespace: knative-demo
spec:
  scaleTargetRef:
    name: sqs-worker
  minReplicaCount: 0
  maxReplicaCount: 100
  triggers:
  - type: aws-sqs-queue
    metadata:
      queueURL: https://sqs.us-west-2.amazonaws.com/123456789012/enriched-events
      queueLength: '5'
      awsRegion: us-west-2
    authenticationRef:
      name: keda-aws-credentials
```

---

## Operaciones en producción {#production-operations}

### Límites de recursos y QoS

Planifique las solicitudes y límites para los contenedores de la aplicación y Queue Proxy según las necesidades de la carga de trabajo medidas. QoS depende de todos los contenedores relevantes: Guaranteed requiere solicitudes y límites de CPU/memoria coincidentes y distintos de cero; otros presupuestos especificados suelen ser Burstable. Ninguna de las clases evita OOM, desalojos o interferencias, y un límite de memoria puede provocar un OOM kill.

```yaml
spec:
  config:
    deployment:
      queue-sidecar-cpu-request: 50m
      queue-sidecar-cpu-limit: 500m
      queue-sidecar-memory-request: 400Mi
      queue-sidecar-memory-limit: 800Mi
```

Guárdelo como serving-deployment.patch.yaml y combínelo con el recurso Operator; no es un ConfigMap independiente.

```bash
kubectl patch knativeserving knative-serving -n knative-serving --type merge --patch-file serving-deployment.patch.yaml
```

### Recolección de basura de Revisions

Con el tiempo, se acumulan Revisions antiguas. Configure la recolección de basura para limitar el número de Revisions conservadas:

```yaml
spec:
  config:
    gc:
      min-non-active-revisions: '2'
      max-non-active-revisions: '10'
      retain-since-create-time: 48h
      retain-since-last-active-time: 24h
```

Guárdelo como serving-gc.patch.yaml y combínelo con el recurso Operator; no es un ConfigMap independiente.

```bash
kubectl patch knativeserving knative-serving -n knative-serving --type merge --patch-file serving-gc.patch.yaml
```

### Configuración de alta disponibilidad

Para cargas de trabajo de producción, configure los componentes de Knative Serving para obtener alta disponibilidad:

```yaml
spec:
  version: 1.23.0
  high-availability:
    replicas: 3
  ingress:
    kourier:
      enabled: true
  workloads:
  - name: activator
    replicas: 3
    resources:
    - container: activator
      requests:
        cpu: 300m
        memory: 256Mi
      limits:
        cpu: 1000m
        memory: 512Mi
  - name: controller
    replicas: 2
  - name: webhook
    replicas: 2
```

Guarde este parche de combinación de Operator como serving-ha.patch.yaml; conserve las entradas/listas de cargas de trabajo existentes. Verifique la ubicación, los recursos y el comportamiento ante errores, en vez de asumir que las réplicas por sí solas proporcionan alta disponibilidad.

```bash
kubectl patch knativeserving knative-serving -n knative-serving --type merge --patch-file serving-ha.patch.yaml
```

Además, configure Pod Disruption Budgets para los componentes del sistema de Knative:

```yaml
spec:
  podDisruptionBudgets:
  - name: activator-pdb
    minAvailable: 2
  - name: webhook-pdb
    minAvailable: 1
```

Guárdelo como serving-pdb.patch.yaml y aplíquelo al recurso KnativeServing. Esto reemplaza los PDB existentes administrados por Operator; limita los desalojos voluntarios y no garantiza la disponibilidad del servicio.

```bash
kubectl patch knativeserving knative-serving -n knative-serving --type merge --patch-file serving-pdb.patch.yaml
```

Distribuya los Pods del sistema entre las zonas de disponibilidad mediante restricciones de distribución de topología:

```yaml
spec:
  workloads:
  - name: activator
    topologySpreadConstraints:
    - maxSkew: 1
      topologyKey: topology.kubernetes.io/zone
      whenUnsatisfiable: DoNotSchedule
      labelSelector:
        matchLabels:
          app: activator
      minDomains: 3
```

Este fragmento de Operator requiere tres zonas aptas y capacidad suficiente; DoNotSchedule puede dejar Pods pendientes. Combínelo con las anulaciones existentes de cargas de trabajo antes de aplicarlo.

### Supervisión con Prometheus

Knative 1.23 usa OpenTelemetry y la exportación de métricas está desactivada de forma predeterminada. Este ejemplo presupone que existe una implementación de Prometheus/Prometheus Operator. Habilite su receptor OTLP (`--web.enable-otlp-receiver` o la configuración equivalente admitida por Operator), restrinja adecuadamente el acceso y configure la promoción de atributos de recursos. Lo siguiente es un **fragmento de configuración nativa de Prometheus**, no valores de Helm; compruebe la compatibilidad con la versión de Prometheus instalada:

```yaml
otlp:
  translation_strategy: UnderscoreEscapingWithSuffixes
  convert_histograms_to_nhcb: false
  promote_resource_attributes:
  - k8s.namespace.name
  - k8s.pod.name
  - kn.service.name
  - kn.configuration.name
  - kn.revision.name
```

Configure el recurso Serving administrado por Operator con este parche de combinación, guardado como `serving-metrics.patch.yaml`. Reemplace el endpoint por el receptor OTLP real; no se garantiza que exista de antemano un Service con ese nombre. Esta configuración recopila métricas del plano de control y envía métricas de solicitudes, por lo que no recopila el puerto administrativo de Queue Proxy:

```yaml
spec:
  config:
    observability:
      metrics-protocol: prometheus
      request-metrics-protocol: http/protobuf
      request-metrics-endpoint: http://prometheus-operated.monitoring.svc.cluster.local:9090/api/v1/otlp/v1/metrics
      request-metrics-export-interval: 10s
```

```bash
kubectl patch knativeserving knative-serving -n knative-serving --type merge --patch-file serving-metrics.patch.yaml
kubectl patch knativeeventing knative-eventing -n knative-eventing --type merge --patch '{"spec":{"config":{"observability":{"metrics-protocol":"prometheus"}}}}'
kubectl get service prometheus-operated -n monitoring
```

El selector ServiceMonitor siguiente coincide con los Services del plano de control publicados y su puerto de Service `http-metrics`. El namespace/las etiquetas también deben coincidir con los selectores de monitor del recurso Prometheus. Verifique los endpoints instalados después de la configuración o de cualquier rollout necesario:

```yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: knative-serving-control-plane
  namespace: monitoring
  labels:
    release: prometheus
spec:
  namespaceSelector:
    matchNames:
    - knative-serving
  selector:
    matchExpressions:
    - key: app
      operator: In
      values:
      - controller
      - webhook
      - autoscaler
      - activator
  endpoints:
  - port: http-metrics
    path: /metrics
    interval: 30s
    honorLabels: true
```

**Vocabulario actual de métricas** (nombres de instrumentos OTel; la traducción seleccionada de Prometheus sustituye los puntos y agrega sufijos de unidad reales):

| Instrumento | Significado |
|---|---|
| `kn.serving.invocation.duration` | Histograma de duración de finalización de solicitudes en segundos; su recuento permite derivar la tasa de solicitudes completadas. |
| `kn.serving.queue.depth` | Muestra de cola/solicitudes en curso de Queue Proxy; no es un recuento global exacto y siempre actualizado de la concurrencia. |
| `kn.revision.pods.desired` / `kn.revision.pods.requested` / `kn.revision.pods.count` | Indicadores de Pods deseados, solicitados y actualmente asignados por Autoscaler. |
| `kn.revision.pods.not_ready.count` / `kn.revision.pods.pending.count` | Indicadores de Pods no listos/pendientes. |
| `kn.revision.concurrency.stable` / `kn.revision.concurrency.panic` | Promedios de concurrencia por Pod observado durante las dos ventanas; no los vuelva a dividir por el recuento de Pods. |
| `kn.revision.request.concurrency` | Solicitudes enrutadas a través de Activator; el tráfico de Activator no equivale a un contador de arranques en frío. |
| `kn.workqueue.depth` / `kn.workqueue.process.duration` | Profundidad de cola y duración de procesamiento de las colas del controlador. |

Las métricas de Eventing para brokers/fuentes/backend varían según la implementación. Su página oficial de métricas advierte que algunas partes de la antigua tabla de OpenCensus aún no han completado la migración; no suponga que existen `broker_event_count` o `trigger_filter_event_count`. Inspeccione las métricas exportadas y el estado de entrega de la implementación seleccionada. En esta auditoría no se realizó ninguna recopilación en tiempo real ni exportación de trazas.

### Dashboard de Grafana

Esta es una definición JSON de dashboard, no el contenedor `dashboard` de la API HTTP. Reemplace el UID de la fuente de datos antes de importarlo. Las consultas presuponen la estrategia de traducción, los buckets de histogramas clásicos y los atributos promocionados anteriores; deben comprobarse el endpoint/las etiquetas de recopilación y la agregación en su implementación. La serie de la ventana panic no es un indicador booleano del modo de pánico, y puede haber actividad de Activator aunque las réplicas no sean cero:

```json
{
  "id": null,
  "uid": "knative-demo-overview",
  "title": "Knative Demo Overview",
  "schemaVersion": 39,
  "version": 1,
  "refresh": "30s",
  "time": {
    "from": "now-1h",
    "to": "now"
  },
  "panels": [
    {
      "id": 1,
      "title": "Completed Request Rate",
      "type": "timeseries",
      "gridPos": {
        "x": 0,
        "y": 0,
        "w": 12,
        "h": 8
      },
      "datasource": {
        "type": "prometheus",
        "uid": "REPLACE_WITH_PROMETHEUS_DATASOURCE_UID"
      },
      "fieldConfig": {
        "defaults": {
          "unit": "reqps"
        },
        "overrides": []
      },
      "targets": [
        {
          "refId": "A",
          "expr": "sum by (k8s_namespace_name, kn_revision_name) (rate(kn_serving_invocation_duration_seconds_count{k8s_namespace_name=\"knative-demo\"}[5m]))",
          "legendFormat": "{{kn_revision_name}}"
        }
      ]
    },
    {
      "id": 2,
      "title": "Request Duration P99",
      "type": "timeseries",
      "gridPos": {
        "x": 12,
        "y": 0,
        "w": 12,
        "h": 8
      },
      "datasource": {
        "type": "prometheus",
        "uid": "REPLACE_WITH_PROMETHEUS_DATASOURCE_UID"
      },
      "fieldConfig": {
        "defaults": {
          "unit": "s"
        },
        "overrides": []
      },
      "targets": [
        {
          "refId": "A",
          "expr": "histogram_quantile(0.99, sum by (le, k8s_namespace_name, kn_revision_name) (rate(kn_serving_invocation_duration_seconds_bucket{k8s_namespace_name=\"knative-demo\"}[5m])))",
          "legendFormat": "{{kn_revision_name}}"
        }
      ]
    },
    {
      "id": 3,
      "title": "Queue Depth Sample",
      "type": "timeseries",
      "gridPos": {
        "x": 0,
        "y": 8,
        "w": 12,
        "h": 8
      },
      "datasource": {
        "type": "prometheus",
        "uid": "REPLACE_WITH_PROMETHEUS_DATASOURCE_UID"
      },
      "fieldConfig": {
        "defaults": {
          "unit": "short"
        },
        "overrides": []
      },
      "targets": [
        {
          "refId": "A",
          "expr": "max by (k8s_namespace_name, kn_revision_name) (kn_serving_queue_depth{k8s_namespace_name=\"knative-demo\"})",
          "legendFormat": "{{kn_revision_name}}"
        }
      ]
    },
    {
      "id": 4,
      "title": "Desired and Actual Pods",
      "type": "timeseries",
      "gridPos": {
        "x": 12,
        "y": 8,
        "w": 12,
        "h": 8
      },
      "datasource": {
        "type": "prometheus",
        "uid": "REPLACE_WITH_PROMETHEUS_DATASOURCE_UID"
      },
      "fieldConfig": {
        "defaults": {
          "unit": "short"
        },
        "overrides": []
      },
      "targets": [
        {
          "refId": "A",
          "expr": "max by (k8s_namespace_name, kn_revision_name) (kn_revision_pods_desired{k8s_namespace_name=\"knative-demo\"})",
          "legendFormat": "{{kn_revision_name}}"
        },
        {
          "refId": "B",
          "expr": "max by (k8s_namespace_name, kn_revision_name) (kn_revision_pods_count{k8s_namespace_name=\"knative-demo\"})",
          "legendFormat": "actual {{kn_revision_name}}"
        }
      ]
    },
    {
      "id": 5,
      "title": "Stable and Panic Window Concurrency",
      "type": "timeseries",
      "gridPos": {
        "x": 0,
        "y": 16,
        "w": 12,
        "h": 8
      },
      "datasource": {
        "type": "prometheus",
        "uid": "REPLACE_WITH_PROMETHEUS_DATASOURCE_UID"
      },
      "fieldConfig": {
        "defaults": {
          "unit": "short"
        },
        "overrides": []
      },
      "targets": [
        {
          "refId": "A",
          "expr": "max by (k8s_namespace_name, kn_revision_name) (kn_revision_concurrency_stable{k8s_namespace_name=\"knative-demo\"})",
          "legendFormat": "{{kn_revision_name}}"
        },
        {
          "refId": "B",
          "expr": "max by (k8s_namespace_name, kn_revision_name) (kn_revision_concurrency_panic{k8s_namespace_name=\"knative-demo\"})",
          "legendFormat": "panic window {{kn_revision_name}}"
        }
      ]
    },
    {
      "id": 6,
      "title": "Requests Through Activator",
      "type": "timeseries",
      "gridPos": {
        "x": 12,
        "y": 16,
        "w": 12,
        "h": 8
      },
      "datasource": {
        "type": "prometheus",
        "uid": "REPLACE_WITH_PROMETHEUS_DATASOURCE_UID"
      },
      "fieldConfig": {
        "defaults": {
          "unit": "short"
        },
        "overrides": []
      },
      "targets": [
        {
          "refId": "A",
          "expr": "max by (k8s_namespace_name, kn_revision_name) (kn_revision_request_concurrency{k8s_namespace_name=\"knative-demo\"})",
          "legendFormat": "{{kn_revision_name}}"
        }
      ]
    }
  ]
}
```

Guárdelo como `knative-overview.json`. Un sidecar de Grafana puede cargarlo desde un ConfigMap solo si está configurada la selección de etiquetas/namespace; no incruste un contenedor `dashboard` adicional. La representación en Grafana y la ingesta real de métricas siguen sin verificarse.

```bash
kubectl create configmap knative-serving-dashboard -n monitoring --from-file=knative-serving.json=knative-overview.json --dry-run=client -o yaml | kubectl apply -f -
kubectl label configmap knative-serving-dashboard -n monitoring grafana_dashboard=1 --overwrite
```

### Solución de problemas

Los cambios en anotaciones con alcance de Revision deben borrar el valor existente de `spec.template.metadata.name` (`null` en un parche de combinación JSON) o usar un nombre de Revision nuevo y sin usar. Para aplicar la nueva configuración a todo el Service de demostración, establezca `spec.traffic` en `[{"latestRevision": true, "percent": 100}]`. Esto reemplaza cualquier división canary o enrutamiento fijado a una Revision; si esas rutas deben conservarse, valide la nueva Revision en una ruta de prueba independiente antes de cambiar el tráfico.

#### La latencia de arranque en frío es demasiado alta

**Síntomas:** La primera solicitud tras un período de inactividad tarda varios segundos.

**Diagnóstico:**

```bash
# Check if the Revision is scaled to zero
kubectl get ksvc order-api -n knative-demo -o jsonpath='{.status.conditions}' | jq .

# Check Activator logs for buffering duration
kubectl logs -l app=activator -n knative-serving --tail=50

# Check pod startup time
kubectl get pods -l serving.knative.dev/service=order-api -n knative-demo \
  -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.status.conditions}{"\n"}{end}'
```

**Soluciones:**
1. Establezca `autoscaling.knative.dev/min-scale: "1"` para mantener al menos un Pod listo.
2. Reduzca el tamaño de la imagen del contenedor.
3. Use sondas de preparación con intervalos cortos.
4. Descargue previamente las imágenes mediante un DaemonSet.

#### El escalado es demasiado lento o presenta oscilaciones

**Síntomas:** El recuento de Pods no se mantiene al ritmo de la carga o escala repetidamente hacia arriba y hacia abajo.

**Diagnóstico:**

```bash
# Check Autoscaler metrics
kubectl logs -l app=autoscaler -n knative-serving --tail=100

# View current scale decisions
kubectl get podautoscaler -n knative-demo
kubectl describe podautoscaler order-api-00001 -n knative-demo
```

**Soluciones:**
1. Reduzca `stable-window` para lograr una respuesta más rápida (por ejemplo, `30s`).
2. Baje el uso objetivo cuando necesite más capacidad disponible; subirlo generalmente hace que cada Pod gestione más carga antes de escalar.
3. Ajuste `panic-window-percentage` y `panic-threshold-percentage` para gestionar ráfagas.
4. La sincronización de HPA es una configuración independiente del plano de control; aumentar su período ralentiza el muestreo. No dé por hecho que EKS expone esa marca. Inspeccione el comportamiento de HPA compatible, la disponibilidad de métricas y los límites de la carga de trabajo.

#### Los eventos no se entregan

**Síntomas:** Se producen eventos, pero los Triggers no se activan.

**Diagnóstico:**

```bash
# Verify Broker is ready
kubectl get broker default -n knative-demo -o yaml

# Check Trigger status
kubectl get triggers -n knative-demo
kubectl describe trigger order-created-trigger -n knative-demo

# Inspect Eventing controller logs
kubectl logs -l app=eventing-controller -n knative-eventing --tail=100

# Check dead letter sink for failed events
kubectl logs -l serving.knative.dev/service=dead-letter-handler -n knative-demo --tail=50
```

**Soluciones:**
1. Verifique que los atributos de filtro del Trigger coincidan exactamente con los atributos del CloudEvent (distinguen mayúsculas de minúsculas).
2. Compruebe que el Service suscriptor esté listo y sea accesible.
3. Asegúrese de que el Channel subyacente del Broker esté en buen estado.
4. Distinga los permisos de la API de Kubernetes para leer recursos de la fuente de la autenticación y autorización HTTP/Eventing en el Broker. Inspeccione el error HTTP real y el mecanismo de identidad/EventPolicies configurado.

#### Errores de resolución DNS

**Síntomas:** Las URL de Knative Service devuelven `NXDOMAIN` o se agotan los tiempos de espera de conexión.

**Diagnóstico:**

```bash
# Verify Kourier service has an external address
kubectl get svc kourier -n kourier-system

# Check config-domain
kubectl get cm config-domain -n knative-serving -o yaml

# Test DNS resolution
nslookup order-api.knative-demo.knative.example.com

# Check the Knative Service URL
kubectl get ksvc order-api -n knative-demo -o jsonpath='{.status.url}'
```

**Soluciones:**
1. Para sslip.io: asegúrese de que la IP externa sea accesible y que los grupos de seguridad no bloqueen los puertos 80/443.
2. Para Route 53: verifique que el registro CNAME comodín se resuelva en el balanceador de carga de Kourier.
3. Compruebe que `config-domain` tenga la entrada de dominio correcta.

---

## Buenas prácticas {#best-practices}

### Patrones de diseño de Service

1. **Un contenedor por Knative Service.** Los Knative Services están diseñados para un único contenedor de aplicación más el sidecar Queue Proxy. Evite los Pods con varios contenedores salvo que sea absolutamente necesario (Knative los admite, pero el modelo de escalado presupone un contenedor principal).

2. **Use `containerConcurrency` deliberadamente.** Establézcalo en `0` (sin límite) para aplicaciones seguras para hilos que gestionan muchas solicitudes concurrentes. Establézcalo en `1` para procesadores de un solo hilo (por ejemplo, inferencia de ML en una sola GPU) en los que las solicitudes concurrentes reducirían el rendimiento.

3. **Separe las rutas de lectura y escritura.** Implemente API con muchas lecturas y procesadores con muchas escrituras como Knative Services independientes con perfiles de escalado distintos. Los servicios de lectura pueden tener un `target` alto (100 o más de concurrencia), mientras que los servicios de escritura pueden necesitar un `target` bajo (10-20) para evitar sobrecargar la base de datos.

4. **Conserve objetivos de reversión probados.** Mantenga las Revisions que se sabe que funcionan referenciadas/conservadas según sea necesario y verifique sus dependencias. El cambio de ruta requiere tiempo de reconciliación:

```bash
kn service update order-api --namespace knative-demo --tag order-api-v1=stable --tag @latest=canary
```

5. **Controle la visibilidad del enrutamiento interno.** Aplique la etiqueta cluster-local cuando corresponda y, por separado, exija autorización de red/aplicación. Es posible que siga existiendo una gateway/balanceador de carga compartido de Knative, por lo que la etiqueta no garantiza una reducción independiente de los costos del balanceador de carga.

### Patrones de microservicios basados en eventos

Para CQRS/abastecimiento de eventos, la ruta de comandos debe confirmar el evento autoritativo o una outbox transaccional antes de confirmar el comando. Un Broker es una capa de entrega, no el almacén de eventos autoritativo. Un consumidor de archivo asíncrono por sí solo no hace transaccional la gestión de comandos; valide el orden, la idempotencia, la reproducción y las ventanas de fallo.

1. **Use Brokers para el enrutamiento a varios consumidores.** Cuando varios servicios deban reaccionar al mismo tipo de evento, use un único Broker con varios Triggers en vez de duplicar la fuente del evento.

2. **Configure siempre Dead Letter Sinks.** Los eventos que no se puedan entregar nunca deben descartarse silenciosamente. Configure un DLS en el nivel de Broker como protección y en los niveles de Trigger individuales para las rutas críticas.

3. **Adopte una convención de nomenclatura para CloudEvents.** Use la notación DNS inversa para los tipos de eventos: `com.<company>.<domain>.<action>` (por ejemplo, `com.example.order.created`). Esto evita colisiones de nombres y aclara los filtros de Trigger.

4. **Consumidores idempotentes.** Los reintentos pueden entregar duplicados. Use el par CloudEvent `(source, id)` y un diseño duradero de transacciones/desduplicación de la aplicación; `id` no es necesariamente único de forma global y Eventing no garantiza un procesamiento empresarial exactamente una vez.

5. **Planifique un transporte duradero antes de la ingesta.** InMemoryChannel no es duradero. Un transporte basado en Kafka configurado correctamente puede conservar eventos, pero cambiar la configuración subyacente de un Broker activo no es una migración de datos. Cree y valide una configuración/Broker independiente, y planifique la reproducción/vaciado de colas para cualquier transición. Lo siguiente es un fragmento de plantilla de Channel para esa nueva configuración:

```yaml
# config-br-default-channel ConfigMap
data:
  channel-template-spec: |
    apiVersion: messaging.knative.dev/v1
    kind: KafkaChannel
    spec:
      numPartitions: 6
      replicationFactor: 3
```

### Optimización de costos con escalado a cero

1. **Habilite el escalado a cero para servicios no críticos.** Los servicios de desarrollo, pruebas y producción con poco tráfico deberían escalar a cero cuando estén inactivos. La cifra original del 60–80 % se conserva únicamente como estimación histórica sin fuente, no como resultado medido ni promesa de ahorro actual. Los costos asignados de nodos/almacenamiento/balanceadores de carga y los compromisos deben evaluarse por separado.

2. **Use `scale-down-delay` para cargas de trabajo con ráfagas.** Si el tráfico llega en ráfagas separadas por breves períodos de inactividad, configurar una demora de escalado hacia abajo (por ejemplo, 5-15 minutos) evita arranques en frío repetidos sin mantener los Pods en ejecución indefinidamente.

3. **Combine con Karpenter para optimizar a nivel de nodo.** Cuando Knative escala Pods a cero, la capacidad liberada permite que Karpenter consolide o termine los nodos infrautilizados:

| Capa | Herramienta | Acción |
|-------|------|--------|
| Aplicación (Pods) | Knative Serving | Escalar Pods a cero cuando están inactivos |
| Infraestructura (nodos) | Karpenter | Consolidar y terminar nodos vacíos |
| Visibilidad de costos | AWS Cost Explorer / Kubecost | Seguir los ahorros del escalado a cero |

4. **Establezca `minScale` solo donde sea necesario.** Reserve `minScale > 0` para rutas críticas para la latencia. Para todo lo demás, permita que los Pods escalen a cero.

### Ilustraciones originales de costos (sin verificar)

Las cifras ilustrativas originales siguientes se conservan sin tratarlas como mediciones ni precios actuales. Las horas de Pod no son lo mismo que las horas de nodo facturadas, y estas cifras omiten los costos del plano de control, el almacenamiento, el balanceador de carga y los compromisos.

| Entorno | Services | Supuesto de ejecución permanente | Supuesto de escalado a cero | Ahorro indicado originalmente |
|---|---|---|---|---|
| Desarrollo | 30 | 30 Pods × 24 h | Promedio de 5 Pods × 8 h | ~83 % |
| Pruebas | 20 | 20 Pods × 24 h | Promedio de 3 Pods × 12 h | ~92 % |
| Producción por la noche | 10 | 10 Pods × 24 h | 2 Pods × 8 h durante la noche | ~33 % |

Los porcentajes indicados no se deducen todos de los supuestos mostrados. Con cero Pods durante las horas restantes, desarrollo pasa de 720 a 40 horas de Pod (94,4 %) y pruebas, de 480 a 36 (92,5 %). Si producción significa 10 Pods durante 16 horas diurnas más 2 durante 8 horas nocturnas, pasa de 240 a 176 (26,7 %). Son comprobaciones aritméticas condicionales, no pruebas de rendimiento repetidas.

La ilustración original de GPU suponía una instancia p3.2xlarge a 3,06 $/hora: 24 horas = 73,44 $/día; 4 horas = 12,24 $/día, aproximadamente un 83 % menos. Aquí no se ha verificado la procedencia por región/fecha de la tarifa y no es una cotización actual. Un Service con cero réplicas no garantiza la terminación inmediata del nodo GPU; tenga en cuenta las demoras de retención, las réplicas de referencia, el almacenamiento de modelos y los costos de nodo/compromiso.

### Knative con cargas de trabajo de GPU

Para un PVC de modelo, llénelo primero y utilice CSI/modos de acceso compatibles con Pods/nodos/AZ simultáneos (como un almacenamiento ReadOnlyMany/ReadWriteMany adecuado), o copias por Pod. RWO no significa un solo Pod, pero puede bloquear la asociación entre nodos. El ejemplo monta los modelos como solo lectura, por lo que no se habilita persistent-volume-write. min-scale 0 permite la activación en frío; elija una referencia positiva solo cuando lo requiera la política de latencia/costo. La ventana de promediado no es el tiempo de espera de la solicitud.

Las extensiones de PodSpec siguientes deben habilitarse para los selectores de nodo, las tolerations y el ejemplo opcional de PVC de solo lectura. Guárdelo como serving-gpu-features.patch.yaml y combínelo con el recurso Operator existente. El NodePool gpu referenciado debe proporcionar suficiente capacidad asignable de CPU/memoria/GPU después de considerar la sobrecarga del sistema y Queue Proxy, además del controlador/complemento de dispositivos necesarios. Son ejemplos de inferencia de modelos sin verificar, no estimaciones de dimensionamiento de GPU basadas en mediciones.

```yaml
spec:
  config:
    features:
      kubernetes.podspec-nodeselector: enabled
      kubernetes.podspec-tolerations: enabled
      kubernetes.podspec-persistent-volume-claim: enabled
```

```bash
kubectl patch knativeserving knative-serving -n knative-serving --type merge --patch-file serving-gpu-features.patch.yaml
```

Knative puede servir cargas de trabajo aceleradas por GPU (por ejemplo, inferencia de ML) programando Pods en nodos GPU. Consideraciones clave:

```yaml
apiVersion: serving.knative.dev/v1
kind: Service
metadata:
  name: llm-inference
  namespace: knative-demo
spec:
  template:
    metadata:
      annotations:
        autoscaling.knative.dev/class: kpa.autoscaling.knative.dev
        autoscaling.knative.dev/metric: concurrency
        autoscaling.knative.dev/target: '1'
        autoscaling.knative.dev/min-scale: '1'
        autoscaling.knative.dev/max-scale: '4'
    spec:
      containerConcurrency: 1
      timeoutSeconds: 600
      containers:
      - image: 123456789012.dkr.ecr.us-west-2.amazonaws.com/llm-server:v1
        ports:
        - containerPort: 8080
        resources:
          requests:
            cpu: '4'
            memory: 16Gi
            nvidia.com/gpu: '1'
          limits:
            cpu: '6'
            memory: 24Gi
            nvidia.com/gpu: '1'
      nodeSelector:
        karpenter.sh/nodepool: gpu
      tolerations:
      - key: nvidia.com/gpu
        operator: Exists
        effect: NoSchedule
```

**Consejos específicos para GPU:**
- Establezca `containerConcurrency: 1` si el modelo no puede procesar lotes de solicitudes concurrentes. Auméntelo si el framework de servicio admite el procesamiento dinámico por lotes (por ejemplo, vLLM o Triton Inference Server).
- Considere un min-scale positivo como referencia activa. Las Revisions nuevas, los reinicios y las réplicas GPU adicionales aún pueden cargarse en frío; mida el inicio de la imagen/modelo.
- Use Karpenter con NodePools GPU para aprovisionar nodos GPU dinámicamente a medida que Knative escala hacia arriba.
- Supervise la utilización de GPU con DCGM Exporter y las métricas de NVIDIA GPU Operator.

---

## Referencias {#references}

### Documentación oficial

- [Documentación oficial de Knative](https://knative.dev/docs/)
- [Organización de Knative en GitHub](https://github.com/knative)
- [Referencia de API de Knative Serving](https://knative.dev/docs/reference/api/serving-api/)
- [Referencia de API de Knative Eventing](https://knative.dev/docs/reference/api/eventing-api/)
- [Repositorio de Kourier en GitHub](https://github.com/knative-extensions/net-kourier)
- [Especificación CloudEvents](https://cloudevents.io/)
- [Página del proyecto Knative en CNCF](https://www.cncf.io/projects/knative/)

### Recursos de AWS y EKS

- [Blog de AWS: contenedores serverless con Knative y EKS](https://aws.amazon.com/blogs/containers/)
- [Guía de buenas prácticas de EKS](https://aws.github.io/aws-eks-best-practices/)
- [Guía para desarrolladores de Amazon Route 53](https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/)
- [cert-manager en EKS](https://cert-manager.io/docs/installation/compatibility/)

### Documentación interna relacionada

- [KEDA -- Autoescalado basado en eventos de Kubernetes](./01-keda.md)
- [Karpenter -- Autoescalador de clúster](./02-karpenter.md)
- [Optimización de costos de EKS](../eks/07-eks-cost-optimization.md)

---

**Anterior:** [Karpenter](./02-karpenter.md) | **Siguiente:** Ninguno

Referencias principales verificadas para esta revisión: [Serving 1.23](https://github.com/knative/serving/releases/tag/knative-v1.23.0), [Operator 1.23.1](https://github.com/knative/operator/releases/tag/knative-v1.23.1), [hito de CNCF](https://www.cncf.io/projects/knative/), [configuración de Operator](https://knative.dev/docs/install/operator/configuring-serving-cr/), [semántica del escalado a cero](https://knative.dev/docs/serving/autoscaling/scale-to-zero/), [implementación de HPA](https://github.com/knative/serving/blob/knative-v1.23.0/pkg/reconciler/autoscaling/hpa/resources/hpa.go), [SQS IntegrationSource](https://knative.dev/docs/eventing/sources/integration-source/aws_sqs/), [vinculación HTTP de CloudEvents](https://github.com/cloudevents/spec/blob/v1.0.2/cloudevents/bindings/http-protocol-binding.md), [escritura condicional de S3](https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/s3/client/put_object.html), [métricas de Serving](https://knative.dev/docs/serving/observability/metrics/serving-metrics/), [configuración OTLP de Prometheus](https://github.com/prometheus/prometheus/blob/main/docs/configuration/configuration.md).
