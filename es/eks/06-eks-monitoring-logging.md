# Monitoreo y logging de Amazon EKS

> **Última actualización**: July 3, 2026

El monitoreo y el logging efectivos son esenciales para mantener la confiabilidad, disponibilidad y rendimiento de los clusters de Amazon EKS. Este documento cubre varias herramientas, técnicas y mejores prácticas para implementar monitoreo y logging en clusters de EKS.

## Tabla de contenidos

1. [Descripción general de monitoreo y logging](#monitoring-and-logging-overview)
2. [Logging del Control Plane de EKS](#eks-control-plane-logging)
3. [Logging de contenedores](#container-logging)
4. [Monitoreo del cluster](#cluster-monitoring)
5. [Alertas y gestión de eventos](#alerting-and-event-management)
6. [Análisis y visualización de logs](#log-analysis-and-visualization)
7. [Mejores prácticas de monitoreo y logging](#monitoring-and-logging-best-practices)
8. [Solución de problemas y depuración](#troubleshooting-and-debugging)

## Descripción general de monitoreo y logging

### Importancia del monitoreo y logging

El monitoreo y logging en clusters de Amazon EKS son importantes por las siguientes razones:

1. **Visibilidad**: Proporciona visibilidad del estado, rendimiento y comportamiento del cluster
2. **Detección de problemas**: Detecta problemas de forma temprana antes de que se vuelvan críticos
3. **Análisis de tendencias**: Identifica tendencias de rendimiento y uso de recursos a lo largo del tiempo
4. **Planificación de capacidad**: Pronostica y planifica los requisitos de recursos
5. **Seguridad y auditoría**: Detecta eventos de seguridad y cumple requisitos de conformidad
6. **Solución de problemas**: Permite un diagnóstico y resolución rápidos cuando ocurren problemas

### Arquitectura de monitoreo y logging

Una arquitectura integral de monitoreo y logging para un cluster de EKS consta de los siguientes componentes:

```mermaid
flowchart TD
    subgraph EKS["Amazon EKS Cluster"]
        CP[Control Plane Logs] --> CWL
        subgraph Nodes["Worker Nodes"]
            Pods[Pods/Containers] --> Fluent
            NodeExporter[Node Exporter] --> Prometheus
            kubelet --> Prometheus
        end
    end

    subgraph AWS["AWS Services"]
        CWL[CloudWatch Logs]
        CWM[CloudWatch Metrics]
        XRay[X-Ray]
        ES[Amazon OpenSearch]
    end

    subgraph Monitoring["Monitoring Stack"]
        Prometheus[Prometheus] --> Alertmanager
        Alertmanager[Alertmanager] --> Notification[Notification Channels]
        Prometheus --> Grafana
    end

    subgraph Logging["Logging Stack"]
        Fluent[Fluent Bit/Fluentd] --> CWL
        Fluent --> ES
        ES --> Kibana[OpenSearch Dashboards]
    end

    CWL --> ES
    Prometheus --> CWM

    %% Class definitions
    classDef awsService fill:#FF9900,stroke:#333,stroke-width:1px,color:black;
    classDef k8sComponent fill:#326CE5,stroke:#333,stroke-width:1px,color:white;
    classDef userApp fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;
    classDef dataStore fill:#3B48CC,stroke:#333,stroke-width:1px,color:white;
    classDef default fill:#f9f9f9,stroke:#333,stroke-width:1px,color:black;

    %% Class application
    class CWL,CWM,XRay,ES awsService;
    class CP,Pods,NodeExporter,kubelet,Prometheus,Alertmanager k8sComponent;
    class Fluent,Grafana,Kibana,Notification userApp;
```

### Estrategia de monitoreo y logging

Sigue estos pasos para desarrollar una estrategia efectiva de monitoreo y logging:

1. **Definir objetivos**: Define los objetivos y requisitos de monitoreo y logging
2. **Identificar métricas y logs**: Identifica las métricas y logs clave que se deben recopilar
3. **Seleccionar herramientas**: Selecciona herramientas de monitoreo y logging que cumplan los requisitos
4. **Establecer líneas base**: Establece líneas base para el comportamiento normal
5. **Configurar alertas**: Configura alertas para eventos y umbrales importantes
6. **Automatizar**: Automatiza los procesos de monitoreo y logging tanto como sea posible
7. **Revisión periódica**: Revisa y mejora periódicamente la estrategia de monitoreo y logging

## Logging del Control Plane de EKS

Amazon EKS proporciona la capacidad de enviar logs del Control Plane del cluster a Amazon CloudWatch Logs. Esto proporciona visibilidad de los componentes de control del cluster.

### Tipos de logs del Control Plane

EKS admite los siguientes tipos de logs del Control Plane:

1. **API Server (api)**: Logs del Kubernetes API server
2. **Audit (audit)**: Logs de auditoría de Kubernetes
3. **Authenticator (authenticator)**: Logs del autenticador AWS IAM
4. **Controller Manager (controllerManager)**: Logs del Controller manager
5. **Scheduler (scheduler)**: Logs del Kubernetes scheduler

### Habilitar logging del Control Plane

Puedes habilitar el logging del Control Plane usando AWS Management Console, AWS CLI o eksctl:

#### Usando AWS CLI

```bash
aws eks update-cluster-config \
  --region us-west-2 \
  --name my-cluster \
  --logging '{"clusterLogging":[{"types":["api","audit","authenticator","controllerManager","scheduler"],"enabled":true}]}'
```

#### Usando eksctl

```bash
eksctl utils update-cluster-logging \
  --region us-west-2 \
  --cluster my-cluster \
  --enable-types api,audit,authenticator,controllerManager,scheduler
```

### Consultar logs del Control Plane

Puedes consultar los logs del Control Plane usando CloudWatch Logs Insights:

#### Consulta de errores del API Server

```
fields @timestamp, @message
| filter @message like /Error/
| sort @timestamp desc
| limit 20
```

#### Consulta de fallos de autenticación

```
fields @timestamp, @message
| filter @message like /authentication failed/
| sort @timestamp desc
| limit 20
```

#### Consulta de logs de auditoría

```
fields @timestamp, @message
| filter @message like /responseStatus.code="403"/
| sort @timestamp desc
| limit 20
```

### Retención de logs del Control Plane y gestión de costos

Puedes configurar períodos de retención de logs en CloudWatch Logs para gestionar costos:

```bash
aws logs put-retention-policy \
  --log-group-name /aws/eks/my-cluster/cluster \
  --retention-in-days 30
```

### Logging de EKS Capabilities (GitOps, ACK, kro)

EKS Capabilities ejecuta Argo CD, AWS Controllers for Kubernetes (ACK) y kro como controladores gestionados en el Control Plane de EKS. Sus logs de controlador ahora pueden entregarse directamente a CloudWatch Logs, S3 o Kinesis Data Firehose, las mismas opciones de entrega usadas para el logging del Control Plane, sin ejecutar un recopilador de logs separado en el cluster para extraer logs de los pods de controlador.

Esto cierra una brecha de visibilidad que antes requería inspeccionar directamente los pods de controlador:

- **Errores de sincronización de GitOps** desde Argo CD
- **Conciliación fallida de recursos** desde ACK
- **Transiciones de estado de workflow** desde kro

Habilita la entrega de logs para las capacidades que ejecutas junto con el logging estándar del Control Plane; luego consulta los resultados con CloudWatch Logs Insights del mismo modo en que consultarías logs del API server o de auditoría. Consulta el [announcement](https://aws.amazon.com/about-aws/whats-new/2026/06/amazon-eks-capabilities-logging/) (June 4, 2026) para ver la lista actual de tipos de logs de capacidades admitidos.

## Logging de contenedores

Los logs de contenedores proporcionan información importante para diagnosticar y resolver problemas de aplicaciones. En EKS, puedes recopilar y gestionar logs de contenedores de varias maneras.

### Arquitectura de logging

Una arquitectura típica de logging de contenedores en EKS se ve así:

```mermaid
flowchart LR
    subgraph Node["Worker Node"]
        Containers[Containers] --> |stdout/stderr| kubelet
        kubelet --> |/var/log/containers/| LogAgent[Log Agent]
    end

    LogAgent --> CWL[CloudWatch Logs]
    LogAgent --> ES[Amazon OpenSearch]
    LogAgent --> S3[Amazon S3]

    %% Class definitions
    classDef awsService fill:#FF9900,stroke:#333,stroke-width:1px,color:black;
    classDef k8sComponent fill:#326CE5,stroke:#333,stroke-width:1px,color:white;
    classDef userApp fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;
    classDef dataStore fill:#3B48CC,stroke:#333,stroke-width:1px,color:white;
    classDef default fill:#f9f9f9,stroke:#333,stroke-width:1px,color:black;

    %% Class application
    class CWL,ES,S3 awsService;
    class kubelet k8sComponent;
    class Containers userApp;
    class LogAgent default;
```

### Recopilación de logs con Fluent Bit

Fluent Bit es un recopilador de logs ligero ampliamente utilizado para recopilar logs de contenedores en clusters de EKS:

#### Instalación de Fluent Bit

Instala Fluent Bit usando Helm:

```bash
helm repo add aws-for-fluent-bit https://aws.github.io/eks-charts
helm repo update
helm install aws-for-fluent-bit aws-for-fluent-bit/aws-for-fluent-bit \
  --namespace kube-system \
  --set cloudWatch.region=us-west-2 \
  --set cloudWatch.logGroupName=/aws/eks/my-cluster/fluentbit
```

#### Configuración de Fluent Bit

ConfigMap para configuración personalizada:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: fluent-bit-config
  namespace: kube-system
data:
  fluent-bit.conf: |
    [SERVICE]
        Flush         5
        Log_Level     info
        Daemon        off
        Parsers_File  parsers.conf

    [INPUT]
        Name              tail
        Tag               kube.*
        Path              /var/log/containers/*.log
        Parser            docker
        DB                /var/log/flb_kube.db
        Mem_Buf_Limit     5MB
        Skip_Long_Lines   On
        Refresh_Interval  10

    [FILTER]
        Name                kubernetes
        Match               kube.*
        Kube_URL            https://kubernetes.default.svc:443
        Kube_CA_File        /var/run/secrets/kubernetes.io/serviceaccount/ca.crt
        Kube_Token_File     /var/run/secrets/kubernetes.io/serviceaccount/token
        Merge_Log           On
        K8S-Logging.Parser  On
        K8S-Logging.Exclude Off

    [OUTPUT]
        Name              cloudwatch
        Match             kube.*
        region            us-west-2
        log_group_name    /aws/eks/my-cluster/fluentbit
        log_stream_prefix container-
        auto_create_group true

    [OUTPUT]
        Name              es
        Match             kube.*
        Host              search-my-es-domain.us-west-2.es.amazonaws.com
        Port              443
        TLS               On
        AWS_Auth          On
        AWS_Region        us-west-2
        Index             eks-logs
        Suppress_Type_Name On
```

### CloudWatch Container Insights

CloudWatch Container Insights recopila, agrega y resume métricas y logs de aplicaciones y microservicios en contenedores:

#### Instalación de Container Insights

```bash
ClusterName=my-cluster
RegionName=us-west-2
FluentBitHttpPort='2020'
FluentBitReadFromHead='Off'
[[ ${FluentBitReadFromHead} = 'On' ]] && FluentBitReadFromTail='Off'|| FluentBitReadFromTail='On'
[[ -z ${FluentBitHttpPort} ]] && FluentBitHttpServer='Off' || FluentBitHttpServer='On'

kubectl apply -f https://raw.githubusercontent.com/aws-samples/amazon-cloudwatch-container-insights/latest/k8s-deployment-manifest-templates/deployment-mode/daemonset/container-insights-monitoring/quickstart/cwagent-fluent-bit-quickstart.yaml
```

#### Dashboard de Container Insights

Accede al dashboard de Container Insights en la consola de CloudWatch para monitorear:
- Uso de CPU y memoria a nivel de Node, pod y contenedor
- E/S de red y disco
- Estado de pod y contenedor
- Fallos y eventos del cluster

### Soluciones de logging personalizadas

Puedes implementar soluciones de logging personalizadas para requisitos específicos:

#### Stack EFK (Elasticsearch, Fluentd, Kibana)

```bash
# Install Elasticsearch
helm repo add elastic https://helm.elastic.co
helm repo update
helm install elasticsearch elastic/elasticsearch \
  --namespace logging \
  --create-namespace \
  --set replicas=3

# Install Fluentd
helm install fluentd stable/fluentd \
  --namespace logging \
  --set output.host=elasticsearch-master.logging.svc.cluster.local

# Install Kibana
helm install kibana elastic/kibana \
  --namespace logging \
  --set service.type=LoadBalancer
```

#### Stack PLG (Promtail, Loki, Grafana)

```bash
# Install Loki and Promtail
helm repo add grafana https://grafana.github.io/helm-charts
helm repo update
helm install loki grafana/loki-stack \
  --namespace logging \
  --create-namespace \
  --set grafana.enabled=true \
  --set promtail.enabled=true \
  --set loki.persistence.enabled=true \
  --set loki.persistence.size=10Gi
```

### Estructuración y análisis de logs

Se recomienda usar formatos de logs estructurados para un análisis de logs efectivo:

#### Formato de logs JSON

Emite logs en formato JSON desde tu aplicación:

```json
{
  "timestamp": "2025-07-11T13:00:00Z",
  "level": "INFO",
  "message": "Request processed successfully",
  "request_id": "12345",
  "user_id": "user-789",
  "duration_ms": 45,
  "status_code": 200
}
```

#### Configuración del parser de logs

Configuración para el análisis de logs en Fluent Bit:

```
[PARSER]
    Name        json
    Format      json
    Time_Key    timestamp
    Time_Format %Y-%m-%dT%H:%M:%S%z
```

## Monitoreo del cluster

El monitoreo efectivo del cluster es esencial para hacer seguimiento del estado, rendimiento y uso de recursos de tu cluster de EKS. Esta sección explora varias herramientas y técnicas para monitorear clusters de EKS.

```mermaid
flowchart TD
    subgraph Monitoring_Solutions ["Monitoring Solutions"]
        subgraph AWS_Solutions ["AWS Solutions"]
            CW_CI["CloudWatch
                Container Insights"]
            CW_LA["CloudWatch
                Logs Insights"]
            CW_Alarms["CloudWatch
                Alarms"]
            AMP["Amazon Managed
                Prometheus"]
            AMG["Amazon Managed
                Grafana"]
        end

        subgraph K8s_Solutions ["Kubernetes Solutions"]
            Prometheus[Prometheus]
            Grafana[Grafana]
            Kube_State[kube-state-metrics]
            Node_Exporter[Node Exporter]
            K8s_Dashboard["Kubernetes
                Dashboard"]
        end

        subgraph Tracing_Solutions ["Tracing Solutions"]
            XRay[AWS X-Ray]
            Jaeger[Jaeger]
            OpenTelemetry[OpenTelemetry]
        end
    end

    subgraph Monitoring_Targets ["Monitoring Targets"]
        subgraph Cluster_Level ["Cluster Level"]
            Control_Plane[Control Plane]
            API_Server[API Server]
            Scheduler[Scheduler]
            Controller[Controller Manager]
        end

        subgraph Node_Level ["Node Level"]
            CPU[CPU Usage]
            Memory[Memory Usage]
            Disk[Disk I/O]
            Network[Network I/O]
        end

        subgraph Pod_Level ["Pod Level"]
            Pod_CPU[Pod CPU]
            Pod_Memory[Pod Memory]
            Pod_Network[Pod Network]
            Restarts[Restart Count]
        end
    end

    CW_CI --> Cluster_Level
    CW_CI --> Node_Level
    CW_CI --> Pod_Level

    Prometheus --> Kube_State
    Prometheus --> Node_Exporter
    Kube_State --> Cluster_Level
    Node_Exporter --> Node_Level

    Prometheus --> Grafana
    AMP --> AMG

    XRay --> API_Server
    OpenTelemetry --> Pod_Level

    %% Class definitions
    classDef awsService fill:#FF9900,stroke:#333,stroke-width:1px,color:black;
    classDef k8sComponent fill:#326CE5,stroke:#333,stroke-width:1px,color:white;
    classDef userApp fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;
    classDef dataStore fill:#3B48CC,stroke:#333,stroke-width:1px,color:white;
    classDef default fill:#f9f9f9,stroke:#333,stroke-width:1px,color:black;

    %% Class application
    class CW_CI,CW_LA,CW_Alarms,AMP,AMG,XRay awsService;
    class Prometheus,Grafana,Kube_State,Node_Exporter,K8s_Dashboard,Control_Plane,API_Server,Scheduler,Controller k8sComponent;
    class Jaeger,OpenTelemetry userApp;
    class CPU,Memory,Disk,Network,Pod_CPU,Pod_Memory,Pod_Network,Restarts default;
```

### CloudWatch Container Insights

Amazon CloudWatch Container Insights recopila, agrega y resume métricas, logs y eventos de aplicaciones y microservicios en contenedores:

#### Habilitar Container Insights

Habilita Container Insights usando el agente de CloudWatch:

```bash
ClusterName=my-cluster
RegionName=us-west-2
FluentBitHttpPort='2020'
FluentBitReadFromHead='Off'
[[ ${FluentBitReadFromHead} = 'On' ]] && FluentBitReadFromTail='Off'|| FluentBitReadFromTail='On'
[[ -z ${FluentBitHttpPort} ]] && FluentBitHttpServer='Off' || FluentBitHttpServer='On'

curl https://raw.githubusercontent.com/aws-samples/amazon-cloudwatch-container-insights/latest/k8s-deployment-manifest-templates/deployment-mode/daemonset/container-insights-monitoring/quickstart/cwagent-fluent-bit-quickstart.yaml | sed 's/{{cluster_name}}/'${ClusterName}'/;s/{{region_name}}/'${RegionName}'/;s/{{http_server_toggle}}/"'${FluentBitHttpServer}'"/;s/{{http_server_port}}/"'${FluentBitHttpPort}'"/;s/{{read_from_head}}/"'${FluentBitReadFromHead}'"/;s/{{read_from_tail}}/"'${FluentBitReadFromTail}'"/' | kubectl apply -f -
```

#### Métricas de Container Insights

Container Insights recopila las siguientes métricas:

- **Nivel de cluster**: Cantidad de Node, cantidad de pod, cantidad de pods fallidos
- **Nivel de Node**: Uso de CPU, uso de memoria, E/S de red, E/S de disco
- **Nivel de Pod**: Uso de CPU, uso de memoria, E/S de red
- **Nivel de Service**: Cantidad de Pod, uso de CPU, uso de memoria

#### Dashboard de Container Insights

Accede al dashboard de Container Insights en la consola de CloudWatch para visualizar el rendimiento del cluster:

1. Inicia sesión en AWS Management Console
2. Navega al servicio CloudWatch
3. Selecciona "Insights" > "Container Insights" en el panel de navegación izquierdo
4. Selecciona la vista de cluster, Node, pod o service

#### Alertas de Container Insights

Configura alarmas de CloudWatch para recibir notificaciones cuando las métricas superen umbrales específicos:

```bash
aws cloudwatch put-metric-alarm \
  --alarm-name "High-CPU-Cluster" \
  --alarm-description "Alarm when cluster CPU exceeds 80%" \
  --metric-name pod_cpu_utilization \
  --namespace ContainerInsights \
  --statistic Average \
  --period 300 \
  --threshold 80 \
  --comparison-operator GreaterThanThreshold \
  --dimensions Name=ClusterName,Value=my-cluster \
  --evaluation-periods 2 \
  --alarm-actions arn:aws:sns:us-west-2:123456789012:my-topic
```

#### Add-on de CloudWatch Observability 5.0.0

A partir de la versión 5.0.0 (February 2026) del add-on de EKS `amazon-cloudwatch-observability`, Application Signals (APM) se entrega **habilitado de forma predeterminada** en lugar de requerir una activación manual. El add-on ahora agrupa Enhanced Container Insights, Container Logs y Application Signals en un solo paquete, e instrumenta workloads para traces, métricas y logs sin requerir anotaciones de pod:

```bash
aws eks update-addon \
  --cluster-name my-cluster \
  --addon-name amazon-cloudwatch-observability \
  --addon-version v5.0.0-eksbuild.1
```

Consulta las [release notes](https://aws.amazon.com/about-aws/whats-new/2026/02/application-performance-monitoring-cloudwatch-eks/) (February 26, 2026) para obtener orientación de actualización si estás pasando desde una versión del add-on donde Application Signals era opcional. Para la evolución más reciente basada en OTel de la recopilación de métricas de Container Insights, consulta [CloudWatch Metrics](../observability/metrics/04-cloudwatch-metrics.md#opentelemetry-based-container-insights-preview).

### EKS Node Monitoring Agent

El EKS Node Monitoring Agent observa los worker nodes para detectar problemas de sistema, almacenamiento, red y aceleradores (GPU), y los publica como Kubernetes Node Conditions, sobre las cuales la característica de reparación automática de nodes de EKS puede actuar automáticamente. A partir de February 2026, el código fuente del agente es público en GitHub, por lo que puede personalizarse o ampliarse más allá de las verificaciones integradas.

El agente se incluye de forma predeterminada en EKS Auto Mode y también está disponible como add-on independiente para grupos de nodes gestionados estándar:

```bash
aws eks create-addon \
  --cluster-name my-cluster \
  --addon-name eks-node-monitoring-agent
```

Revisa las condiciones que reporta con:

```bash
kubectl get nodes -o custom-columns='NAME:.metadata.name,CONDITIONS:.status.conditions[*].type'
kubectl describe node <node-name>
```

Consulta el [announcement](https://aws.amazon.com/about-aws/whats-new/2026/02/amazon-eks-node-monitoring-agent-open-source/) (February 24, 2026) para ver el repositorio de GitHub y los tipos de condiciones admitidos.

### Prometheus y Grafana

Prometheus es una base de datos de series temporales y un sistema de monitoreo, y Grafana es una herramienta de dashboards para visualizar métricas. Puedes usar estas dos herramientas juntas para un monitoreo integral de tu cluster de EKS.

#### Amazon Managed Service for Prometheus y Grafana

AWS proporciona servicios gestionados para Prometheus y Grafana:

1. Configuración de **Amazon Managed Service for Prometheus (AMP)**:

```bash
# Create AMP workspace
aws amp create-workspace --alias my-amp-workspace

# Install Prometheus server and configure remote write to AMP
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update
helm install prometheus prometheus-community/prometheus \
  --namespace prometheus \
  --create-namespace \
  --set server.remoteWrite[0].url=https://aps-workspaces.us-west-2.amazonaws.com/workspaces/ws-12345678-1234-1234-1234-123456789012/api/v1/remote_write \
  --set server.remoteWrite[0].sigv4.region=us-west-2
```

2. Configuración de **Amazon Managed Grafana (AMG)**:

```bash
# Create AMG workspace
aws grafana create-workspace \
  --name my-grafana-workspace \
  --authentication-providers AWS_SSO \
  --permission-type SERVICE_MANAGED

# Add AMP data source
aws grafana create-workspace-service-account \
  --workspace-id g-12345678 \
  --name amp-datasource \
  --service-account-role ADMIN
```

#### Prometheus y Grafana autogestionados

También puedes desplegar Prometheus y Grafana autogestionados en tu cluster de EKS:

1. **Instalar kube-prometheus-stack**:

```bash
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update
helm install monitoring prometheus-community/kube-prometheus-stack \
  --namespace monitoring \
  --create-namespace \
  --set grafana.service.type=LoadBalancer
```

2. **Acceder a Grafana**:

```bash
# Get Grafana service URL
kubectl get svc -n monitoring monitoring-grafana -o jsonpath='{.status.loadBalancer.ingress[0].hostname}'

# Get default username and password
kubectl get secret -n monitoring monitoring-grafana -o jsonpath='{.data.admin-user}' | base64 --decode
kubectl get secret -n monitoring monitoring-grafana -o jsonpath='{.data.admin-password}' | base64 --decode
```

#### Métricas clave de Prometheus

Prometheus recopila las siguientes métricas importantes de Kubernetes:

- **Métricas de Node**: Uso de CPU, memoria, disco y red
- **Métricas de Pod**: Uso de CPU y memoria, cantidad de reinicios
- **Métricas de contenedor**: Uso de CPU y memoria, uso del filesystem
- **Métricas del API server**: Latencia de solicitudes, cantidad de solicitudes, tasa de errores
- **Métricas de etcd**: Latencia, E/S de disco, cambios de líder

#### Dashboards útiles de Grafana

Puedes importar los siguientes dashboards útiles en Grafana:

1. **Kubernetes Cluster Monitoring** (ID: 15661)
2. **Node Exporter Full** (ID: 1860)
3. **Kubernetes Pod Monitoring** (ID: 6417)
4. **Kubernetes API Server** (ID: 12006)
5. **Kubernetes Resource Requests/Limits** (ID: 13770)

#### Ejemplos de consultas PromQL

Puedes escribir consultas útiles usando Prometheus Query Language (PromQL):

```
# CPU usage by node
sum(rate(node_cpu_seconds_total{mode!="idle"}[5m])) by (instance) / count(node_cpu_seconds_total{mode="idle"}) by (instance) * 100

# Memory usage by pod (top 10)
topk(10, sum(container_memory_usage_bytes{container!=""}) by (pod))

# Container restart count
sum(kube_pod_container_status_restarts_total) by (pod)

# Disk usage percentage by node
100 - ((node_filesystem_avail_bytes{mountpoint="/"} * 100) / node_filesystem_size_bytes{mountpoint="/"})
```
### Distributed Tracing con AWS X-Ray

AWS X-Ray recopila datos sobre las solicitudes que procesa tu aplicación y los usa para identificar problemas de aplicación y oportunidades de optimización.

#### Configuración de X-Ray

1. **Instalar el daemon de X-Ray**:

```yaml
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: xray-daemon
  namespace: default
spec:
  selector:
    matchLabels:
      app: xray-daemon
  template:
    metadata:
      labels:
        app: xray-daemon
    spec:
      containers:
      - name: xray-daemon
        image: amazon/aws-xray-daemon:latest
        ports:
        - containerPort: 2000
          hostPort: 2000
          protocol: UDP
        resources:
          limits:
            memory: 256Mi
          requests:
            memory: 256Mi
        env:
        - name: AWS_REGION
          value: us-west-2
      serviceAccountName: xray-daemon
---
apiVersion: v1
kind: ServiceAccount
metadata:
  name: xray-daemon
  namespace: default
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: xray-daemon
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: cluster-admin
subjects:
- kind: ServiceAccount
  name: xray-daemon
  namespace: default
```

2. **Integrar el SDK de X-Ray en tu aplicación**:

Ejemplo de aplicación Java:

```java
import com.amazonaws.xray.AWSXRay;
import com.amazonaws.xray.AWSXRayRecorderBuilder;
import com.amazonaws.xray.plugins.EKSPlugin;

public class Application {
    static {
        AWSXRayRecorderBuilder builder = AWSXRayRecorderBuilder.standard().withPlugin(new EKSPlugin());
        AWSXRay.setGlobalRecorder(builder.build());
    }

    // Application code
}
```

#### Mapa de servicios de X-Ray

Usa el mapa de servicios de X-Ray para visualizar relaciones y comunicación entre componentes en tu arquitectura de microservicios:

1. Inicia sesión en AWS Management Console
2. Navega al servicio X-Ray
3. Selecciona "Service Map" en el panel de navegación izquierdo
4. Revisa latencia, errores y puntos de fallo entre servicios

#### Análisis e insights de X-Ray

Usa X-Ray Analytics para analizar datos de traces e identificar cuellos de botella de rendimiento:

1. Navega al servicio X-Ray en AWS Management Console
2. Selecciona "Analytics" en el panel de navegación izquierdo
3. Analiza la distribución del tiempo de respuesta, la tasa de errores y los puntos de fallo

### Kubernetes Dashboard

Kubernetes Dashboard proporciona una interfaz web para gestionar recursos del cluster y solucionar problemas:

#### Instalación de Kubernetes Dashboard

```bash
kubectl apply -f https://raw.githubusercontent.com/kubernetes/dashboard/v2.7.0/aio/deploy/recommended.yaml

# Create service account and cluster role binding for dashboard access
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: ServiceAccount
metadata:
  name: admin-user
  namespace: kubernetes-dashboard
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: admin-user
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: cluster-admin
subjects:
- kind: ServiceAccount
  name: admin-user
  namespace: kubernetes-dashboard
EOF

# Generate access token
kubectl -n kubernetes-dashboard create token admin-user
```

#### Acceder al Dashboard

```bash
# Start dashboard proxy
kubectl proxy

# Access the following URL in browser
# http://localhost:8001/api/v1/namespaces/kubernetes-dashboard/services/https:kubernetes-dashboard:/proxy/
```

### Métricas personalizadas y monitoreo

Puedes implementar soluciones personalizadas para recopilar y monitorear métricas específicas de la aplicación:

#### Integración de bibliotecas cliente de Prometheus

Integra bibliotecas cliente de Prometheus en tu aplicación para exponer métricas personalizadas:

Ejemplo de aplicación Java:

```java
import io.prometheus.client.Counter;
import io.prometheus.client.Histogram;
import io.prometheus.client.exporter.HTTPServer;

public class Application {
    static final Counter requests = Counter.build()
        .name("app_requests_total")
        .help("Total requests.")
        .register();

    static final Histogram requestLatency = Histogram.build()
        .name("app_request_latency_seconds")
        .help("Request latency in seconds.")
        .register();

    public static void main(String[] args) throws IOException {
        HTTPServer server = new HTTPServer(8080);
        // Application code
    }

    public void processRequest() {
        requests.inc();
        Histogram.Timer timer = requestLatency.startTimer();
        try {
            // Process request
        } finally {
            timer.observeDuration();
        }
    }
}
```

#### Recopilación de métricas personalizadas

Usa Prometheus ServiceMonitor para recopilar métricas personalizadas:

```yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: app-monitor
  namespace: monitoring
spec:
  selector:
    matchLabels:
      app: my-app
  endpoints:
  - port: metrics
    interval: 15s
    path: /metrics
```

#### Dashboards personalizados

Crea dashboards personalizados en Grafana para visualizar métricas de aplicación:

1. Inicia sesión en Grafana
2. Haz clic en el icono "+" y selecciona "Dashboard"
3. Haz clic en "Add panel"
4. Selecciona "Prometheus" como data source
5. Escribe una consulta PromQL (por ejemplo, `rate(app_requests_total[5m])`)
6. Configura el título del panel, la descripción y el tipo de visualización
7. Haz clic en "Save"
## Alertas y gestión de eventos

Las alertas y la gestión de eventos efectivas son esenciales para detectar y responder rápidamente a problemas en tu cluster de EKS. Esta sección explora varias herramientas y técnicas para gestionar alertas y eventos en clusters de EKS.

```mermaid
flowchart TD
    subgraph Alert_Sources ["Alert Sources"]
        subgraph Metrics ["Metric-based"]
            CW_Metrics[CloudWatch Metrics]
            Prom_Metrics[Prometheus Metrics]
            Custom_Metrics[Custom Metrics]
        end

        subgraph Logs ["Log-based"]
            CW_Logs[CloudWatch Logs]
            ES_Logs[OpenSearch Logs]
            Loki_Logs[Loki Logs]
        end

        subgraph Events ["Event-based"]
            K8s_Events[Kubernetes Events]
            AWS_Events[AWS Events]
            App_Events[Application Events]
        end
    end

    subgraph Alert_Processing ["Alert Processing"]
        CW_Alarms[CloudWatch Alarms]
        Prom_AM["Prometheus
                Alertmanager"]
        EventBridge[Amazon EventBridge]
        Event_Router[Event Router]
    end

    subgraph Notification_Channels ["Notification Channels"]
        SNS[Amazon SNS]
        SQS[Amazon SQS]
        Lambda[AWS Lambda]
        Email[Email]
        Slack[Slack]
        PagerDuty[PagerDuty]
        OpsGenie[OpsGenie]
    end

    CW_Metrics --> CW_Alarms
    Prom_Metrics --> Prom_AM
    Custom_Metrics --> Prom_AM

    CW_Logs --> CW_Alarms
    ES_Logs --> Event_Router
    Loki_Logs --> Prom_AM

    K8s_Events --> Event_Router
    AWS_Events --> EventBridge
    App_Events --> Event_Router

    CW_Alarms --> SNS
    Prom_AM --> Slack
    Prom_AM --> PagerDuty
    EventBridge --> Lambda
    EventBridge --> SNS
    Event_Router --> OpsGenie

    SNS --> Email
    SNS --> SQS

    %% Class definitions
    classDef awsService fill:#FF9900,stroke:#333,stroke-width:1px,color:black;
    classDef k8sComponent fill:#326CE5,stroke:#333,stroke-width:1px,color:white;
    classDef userApp fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;
    classDef dataStore fill:#3B48CC,stroke:#333,stroke-width:1px,color:white;
    classDef default fill:#f9f9f9,stroke:#333,stroke-width:1px,color:black;

    %% Class application
    class CW_Metrics,CW_Logs,CW_Alarms,EventBridge,SNS,SQS,Lambda,AWS_Events awsService;
    class K8s_Events,Prom_AM k8sComponent;
    class Prom_Metrics,Custom_Metrics,ES_Logs,Loki_Logs,App_Events,Event_Router,Email,Slack,PagerDuty,OpsGenie userApp;
```

### CloudWatch Alarms

Usa Amazon CloudWatch alarms para recibir notificaciones cuando las métricas superen umbrales específicos:

#### Alarma de uso de CPU del cluster

```bash
aws cloudwatch put-metric-alarm \
  --alarm-name "EKS-Cluster-High-CPU" \
  --alarm-description "Alarm when cluster CPU exceeds 80%" \
  --metric-name pod_cpu_utilization \
  --namespace ContainerInsights \
  --statistic Average \
  --period 300 \
  --threshold 80 \
  --comparison-operator GreaterThanThreshold \
  --dimensions Name=ClusterName,Value=my-cluster \
  --evaluation-periods 2 \
  --alarm-actions arn:aws:sns:us-west-2:123456789012:my-topic
```

#### Alarma de uso de memoria

```bash
aws cloudwatch put-metric-alarm \
  --alarm-name "EKS-Cluster-High-Memory" \
  --alarm-description "Alarm when cluster memory exceeds 80%" \
  --metric-name pod_memory_utilization \
  --namespace ContainerInsights \
  --statistic Average \
  --period 300 \
  --threshold 80 \
  --comparison-operator GreaterThanThreshold \
  --dimensions Name=ClusterName,Value=my-cluster \
  --evaluation-periods 2 \
  --alarm-actions arn:aws:sns:us-west-2:123456789012:my-topic
```

#### Alarma de uso de disco

```bash
aws cloudwatch put-metric-alarm \
  --alarm-name "EKS-Node-High-Disk" \
  --alarm-description "Alarm when node disk usage exceeds 85%" \
  --metric-name node_filesystem_utilization \
  --namespace ContainerInsights \
  --statistic Maximum \
  --period 300 \
  --threshold 85 \
  --comparison-operator GreaterThanThreshold \
  --dimensions Name=ClusterName,Value=my-cluster \
  --evaluation-periods 2 \
  --alarm-actions arn:aws:sns:us-west-2:123456789012:my-topic
```

### Prometheus Alertmanager

Prometheus Alertmanager gestiona las alertas generadas por Prometheus y las enruta a canales de notificación apropiados:

#### Configuración de Alertmanager

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: alertmanager-config
  namespace: monitoring
data:
  alertmanager.yml: |
    global:
      resolve_timeout: 5m
      slack_api_url: 'https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXXXXXX'

    route:
      group_by: ['alertname', 'job']
      group_wait: 30s
      group_interval: 5m
      repeat_interval: 12h
      receiver: 'slack-notifications'
      routes:
      - match:
          severity: critical
        receiver: 'slack-notifications'
        continue: true

    receivers:
    - name: 'slack-notifications'
      slack_configs:
      - channel: '#eks-alerts'
        send_resolved: true
        title: '[{{ .Status | toUpper }}] {{ .CommonLabels.alertname }}'
        text: >-
          {{ range .Alerts }}
            *Alert:* {{ .Annotations.summary }}
            *Description:* {{ .Annotations.description }}
            *Severity:* {{ .Labels.severity }}
            *Details:*
            {{ range .Labels.SortedPairs }} • *{{ .Name }}:* `{{ .Value }}`
            {{ end }}
          {{ end }}
```

#### Configuración de reglas de alerta

```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: kubernetes-alerts
  namespace: monitoring
spec:
  groups:
  - name: kubernetes
    rules:
    - alert: KubernetesPodCrashLooping
      expr: rate(kube_pod_container_status_restarts_total[5m]) * 60 * 5 > 5
      for: 5m
      labels:
        severity: critical
      annotations:
        summary: "Pod {{ $labels.namespace }}/{{ $labels.pod }} is crash looping"
        description: "Pod {{ $labels.namespace }}/{{ $labels.pod }} is restarting {{ $value }} times / 5 minutes"

    - alert: KubernetesNodeMemoryPressure
      expr: kube_node_status_condition{condition="MemoryPressure", status="true"} == 1
      for: 5m
      labels:
        severity: warning
      annotations:
        summary: "Node {{ $labels.node }} is under memory pressure"
        description: "Node {{ $labels.node }} has been under memory pressure for more than 5 minutes"

    - alert: KubernetesNodeDiskPressure
      expr: kube_node_status_condition{condition="DiskPressure", status="true"} == 1
      for: 5m
      labels:
        severity: warning
      annotations:
        summary: "Node {{ $labels.node }} is under disk pressure"
        description: "Node {{ $labels.node }} has been under disk pressure for more than 5 minutes"
```

### Reglas de eventos de EventBridge

Usa Amazon EventBridge para crear reglas que respondan a eventos en tu cluster de EKS:

#### Regla de evento de cambio de estado del cluster de EKS

```bash
aws events put-rule \
  --name "EKS-Cluster-State-Change" \
  --event-pattern '{
    "source": ["aws.eks"],
    "detail-type": ["EKS Cluster State Change"],
    "detail": {
      "clusterName": ["my-cluster"]
    }
  }'

aws events put-targets \
  --rule "EKS-Cluster-State-Change" \
  --targets '[
    {
      "Id": "1",
      "Arn": "arn:aws:sns:us-west-2:123456789012:my-topic"
    }
  ]'
```

#### Regla de evento de EKS Node Group

```bash
aws events put-rule \
  --name "EKS-NodeGroup-Events" \
  --event-pattern '{
    "source": ["aws.eks"],
    "detail-type": ["EKS Node Group State Change"],
    "detail": {
      "clusterName": ["my-cluster"]
    }
  }'

aws events put-targets \
  --rule "EKS-NodeGroup-Events" \
  --targets '[
    {
      "Id": "1",
      "Arn": "arn:aws:sns:us-west-2:123456789012:my-topic"
    }
  ]'
```

### Monitoreo de eventos de Kubernetes

Los eventos de Kubernetes proporcionan información sobre actividades importantes que ocurren en el cluster:

#### Instalación de herramientas de monitoreo de eventos

```bash
# Install event-exporter
kubectl apply -f https://raw.githubusercontent.com/opsgenie/kubernetes-event-exporter/master/deploy/01-cluster-role.yaml
kubectl apply -f https://raw.githubusercontent.com/opsgenie/kubernetes-event-exporter/master/deploy/02-service-account.yaml
kubectl apply -f https://raw.githubusercontent.com/opsgenie/kubernetes-event-exporter/master/deploy/03-cluster-role-binding.yaml
```

#### Configuración de Event Exporter

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: event-exporter-config
  namespace: default
data:
  config.yaml: |
    logLevel: info
    logFormat: json
    route:
      routes:
        - match:
            - type: "Warning"
          receivers:
            - webhook:
                endpoint: "http://alertmanager:9093/api/v1/alerts"
                headers:
                  Content-Type: application/json
        - match:
            - type: "Normal"
              reason: "Created|Started|Killing|Scheduled|Pulled"
          receivers:
            - file:
                path: "/tmp/normal-events.log"
    receivers:
      - name: "dump"
        file:
          path: "/tmp/all-events.log"
      - name: "slack"
        slack:
          channel: "#kubernetes-events"
          token: "xoxb-1234-1234-1234"
```

#### Deployment de Event Exporter

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: event-exporter
  namespace: default
spec:
  replicas: 1
  selector:
    matchLabels:
      app: event-exporter
  template:
    metadata:
      labels:
        app: event-exporter
    spec:
      serviceAccountName: event-exporter
      containers:
      - name: event-exporter
        image: opsgenie/kubernetes-event-exporter:latest
        args:
        - -conf=/etc/config/config.yaml
        volumeMounts:
        - name: config
          mountPath: /etc/config
      volumes:
      - name: config
        configMap:
          name: event-exporter-config
```

### Integración de canales de notificación

Puedes integrar varios canales de notificación para entregar alertas a tu equipo:

#### Integración con Slack

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: slack-webhook
  namespace: monitoring
type: Opaque
stringData:
  url: https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXXXXXX
---
apiVersion: notification.toolkit.fluxcd.io/v1beta1
kind: Provider
metadata:
  name: slack
  namespace: monitoring
spec:
  type: slack
  channel: eks-alerts
  secretRef:
    name: slack-webhook
```

#### Integración con PagerDuty

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: pagerduty-api-key
  namespace: monitoring
type: Opaque
stringData:
  token: your-pagerduty-api-key
---
apiVersion: notification.toolkit.fluxcd.io/v1beta1
kind: Provider
metadata:
  name: pagerduty
  namespace: monitoring
spec:
  type: pagerduty
  serviceKey: your-pagerduty-service-key
  secretRef:
    name: pagerduty-api-key
```

#### Integración con email

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: smtp-credentials
  namespace: monitoring
type: Opaque
stringData:
  username: your-smtp-username
  password: your-smtp-password
---
apiVersion: notification.toolkit.fluxcd.io/v1beta1
kind: Provider
metadata:
  name: email
  namespace: monitoring
spec:
  type: smtp
  server: smtp.example.com
  port: "587"
  from: eks-alerts@example.com
  to:
  - team@example.com
  secretRef:
    name: smtp-credentials
```

### Gestión y escalamiento de alertas

Implementa estrategias para gestionar y escalar alertas de manera efectiva:

#### Niveles de severidad de alertas

Clasifica las alertas en los siguientes niveles de severidad:

- **Critical**: Problemas graves que requieren acción inmediata
- **Warning**: Problemas que requieren atención, pero no acción inmediata
- **Info**: Alertas informativas

#### Política de escalamiento de alertas

Implementa políticas de escalamiento de alertas usando herramientas como PagerDuty:

1. **First Response**: Alertar al ingeniero de guardia
2. **Escalation 1**: Alertar al ingeniero de respaldo si no hay respuesta después de 15 minutos
3. **Escalation 2**: Alertar al líder del equipo si no hay respuesta después de 30 minutos
4. **Escalation 3**: Alertar al gerente si no hay respuesta después de 45 minutos

#### Reducir la fatiga por alertas

Implementa estrategias para reducir la fatiga por alertas:

1. **Agrupación de alertas**: Agrupa alertas relacionadas para reducir notificaciones duplicadas
2. **Filtrado de alertas**: Filtra para entregar solo alertas importantes
3. **Limitación de alertas**: Limita la frecuencia de alertas repetidas
4. **Ventanas horarias de alertas**: Entrega alertas no críticas para el negocio solo durante horario laboral
## Análisis y visualización de logs

El análisis y la visualización de logs desempeñan un papel importante en el diagnóstico y la resolución de problemas que ocurren en tu cluster de EKS. Esta sección explora varias herramientas y técnicas para analizar y visualizar logs en clusters de EKS.

```mermaid
flowchart TD
    subgraph Log_Sources ["Log Sources"]
        CP_Logs[Control Plane Logs]
        Container_Logs[Container Logs]
        App_Logs[Application Logs]
        AWS_Service_Logs[AWS Service Logs]
    end

    subgraph Log_Collection ["Log Collection"]
        Fluent_Bit[Fluent Bit]
        Fluentd[Fluentd]
        CloudWatch_Agent[CloudWatch Agent]
        Vector[Vector]
    end

    subgraph Log_Storage ["Log Storage"]
        CW_Logs[CloudWatch Logs]
        OpenSearch[Amazon OpenSearch]
        S3[Amazon S3]
        Loki[Grafana Loki]
    end

    subgraph Log_Analysis ["Log Analysis"]
        CW_Insights[CloudWatch Logs Insights]
        OS_Dashboards[OpenSearch Dashboards]
        Athena[Amazon Athena]
        Grafana_Explore[Grafana Explore]
    end

    subgraph Visualization ["Visualization"]
        OS_Visualizations[OpenSearch Visualizations]
        Grafana_Dashboards[Grafana Dashboards]
        QuickSight[Amazon QuickSight]
        Custom_Dashboards[Custom Dashboards]
    end

    CP_Logs --> CW_Logs
    Container_Logs --> Fluent_Bit
    App_Logs --> Fluent_Bit
    AWS_Service_Logs --> CW_Logs

    Fluent_Bit --> CW_Logs
    Fluent_Bit --> OpenSearch
    Fluent_Bit --> S3
    Fluentd --> Loki
    CloudWatch_Agent --> CW_Logs
    Vector --> OpenSearch

    CW_Logs --> CW_Insights
    OpenSearch --> OS_Dashboards
    S3 --> Athena
    Loki --> Grafana_Explore

    CW_Insights --> Custom_Dashboards
    OS_Dashboards --> OS_Visualizations
    Athena --> QuickSight
    Grafana_Explore --> Grafana_Dashboards

    %% Class definitions
    classDef awsService fill:#FF9900,stroke:#333,stroke-width:1px,color:black;
    classDef k8sComponent fill:#326CE5,stroke:#333,stroke-width:1px,color:white;
    classDef userApp fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;
    classDef dataStore fill:#3B48CC,stroke:#333,stroke-width:1px,color:white;
    classDef default fill:#f9f9f9,stroke:#333,stroke-width:1px,color:black;

    %% Class application
    class CW_Logs,CW_Insights,OpenSearch,S3,Athena,QuickSight,CloudWatch_Agent,AWS_Service_Logs awsService;
    class CP_Logs k8sComponent;
    class Fluent_Bit,Fluentd,Vector,Container_Logs,App_Logs userApp;
    class OS_Dashboards,OS_Visualizations,Grafana_Dashboards,Grafana_Explore,Custom_Dashboards,Loki dataStore;
```

### CloudWatch Logs Insights

Usa CloudWatch Logs Insights para consultar y analizar logs de tu cluster de EKS:

#### Consulta de logs de contenedor

```
fields @timestamp, kubernetes.pod_name, log
| filter kubernetes.namespace_name = "default"
| filter kubernetes.container_name = "app"
| filter log like /ERROR/
| sort @timestamp desc
| limit 20
```

#### Consulta de errores del API Server

```
fields @timestamp, @message
| filter @logStream like /kube-apiserver/
| filter @message like /Error/
| sort @timestamp desc
| limit 20
```

#### Consulta de fallos de autenticación

```
fields @timestamp, @message
| filter @logStream like /authenticator/
| filter @message like /authentication failed/
| sort @timestamp desc
| limit 20
```

#### Análisis de patrones de logs

```
fields @timestamp, @message
| parse @message "* * * [*] *" as date, time, level, component, message
| stats count(*) as count by level, component
| sort count desc
```

### Amazon OpenSearch Service

Usa Amazon OpenSearch Service (anteriormente Amazon Elasticsearch Service) para almacenar, analizar y visualizar logs de tu cluster de EKS:

#### Crear un dominio de OpenSearch

```bash
aws opensearch create-domain \
  --domain-name eks-logs \
  --engine-version OpenSearch_1.3 \
  --cluster-config InstanceType=r6g.large.search,InstanceCount=2 \
  --ebs-options EBSEnabled=true,VolumeType=gp3,VolumeSize=100 \
  --node-to-node-encryption-options Enabled=true \
  --encryption-at-rest-options Enabled=true \
  --domain-endpoint-options EnforceHTTPS=true \
  --advanced-security-options Enabled=true,InternalUserDatabaseEnabled=true,MasterUserOptions='{MasterUserName=admin,MasterUserPassword=Admin123!}' \
  --access-policies '{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"AWS":"*"},"Action":"es:*","Resource":"arn:aws:es:us-west-2:123456789012:domain/eks-logs/*"}]}'
```

#### Enviar logs a OpenSearch usando Fluent Bit

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: fluent-bit-config
  namespace: kube-system
data:
  fluent-bit.conf: |
    [SERVICE]
        Flush         5
        Log_Level     info
        Daemon        off
        Parsers_File  parsers.conf

    [INPUT]
        Name              tail
        Tag               kube.*
        Path              /var/log/containers/*.log
        Parser            docker
        DB                /var/log/flb_kube.db
        Mem_Buf_Limit     5MB
        Skip_Long_Lines   On
        Refresh_Interval  10

    [FILTER]
        Name                kubernetes
        Match               kube.*
        Kube_URL            https://kubernetes.default.svc:443
        Kube_CA_File        /var/run/secrets/kubernetes.io/serviceaccount/ca.crt
        Kube_Token_File     /var/run/secrets/kubernetes.io/serviceaccount/token
        Merge_Log           On
        K8S-Logging.Parser  On
        K8S-Logging.Exclude Off

    [OUTPUT]
        Name            es
        Match           kube.*
        Host            search-eks-logs-abcdefghijklmnopqrstuvwxyz.us-west-2.es.amazonaws.com
        Port            443
        TLS             On
        AWS_Auth        On
        AWS_Region      us-west-2
        Index           eks-logs
        Suppress_Type_Name On
```

#### Visualización de logs con OpenSearch Dashboards

Crea las siguientes visualizaciones en OpenSearch Dashboards:

1. **Log Explorer**: Búsqueda y filtrado de logs
2. **Dashboards**: Crear dashboards basados en datos de logs
3. **Visualizations**: Crear gráficos y diagramas basados en datos de logs
4. **Alerts**: Configurar alertas basadas en patrones de logs

### Grafana Loki

Grafana Loki es un sistema de agregación de logs que usa un enfoque basado en labels similar a Prometheus:

#### Instalación de Loki

```bash
helm repo add grafana https://grafana.github.io/helm-charts
helm repo update
helm install loki grafana/loki-stack \
  --namespace logging \
  --create-namespace \
  --set grafana.enabled=true \
  --set promtail.enabled=true \
  --set loki.persistence.enabled=true \
  --set loki.persistence.size=10Gi
```

#### Ejemplos de consultas LogQL

```
# Search error logs in a specific namespace
{namespace="default"} |= "ERROR"

# Search logs for a specific pod
{namespace="default", pod=~"app-.*"} | json

# Count logs by log level
sum by (level) (count_over_time({namespace="default"} | json | level=~"info|warn|error" [5m]))
```

#### Crear dashboards de Grafana

Crea dashboards de logs en Grafana usando el data source de Loki:

1. Inicia sesión en Grafana
2. Haz clic en el icono "+" y selecciona "Dashboard"
3. Haz clic en "Add panel"
4. Selecciona "Loki" como data source
5. Escribe una consulta LogQL
6. Configura el título del panel, la descripción y el tipo de visualización
7. Haz clic en "Save"

### AWS CloudTrail

Usa AWS CloudTrail para registrar y analizar llamadas a la API de AWS relacionadas con tu cluster de EKS:

#### Crear un trail de CloudTrail

```bash
aws cloudtrail create-trail \
  --name eks-api-trail \
  --s3-bucket-name my-cloudtrail-bucket \
  --is-multi-region-trail \
  --include-global-service-events

aws cloudtrail start-logging --name eks-api-trail
```

#### Filtrar eventos de CloudTrail

```bash
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=EventSource,AttributeValue=eks.amazonaws.com
```

#### Consulta de CloudTrail Lake

```sql
SELECT eventTime, eventName, userIdentity.arn, requestParameters
FROM eks_events
WHERE eventSource = 'eks.amazonaws.com'
  AND eventName LIKE '%Cluster%'
  AND eventTime >= '2025-07-01T00:00:00Z'
  AND eventTime <= '2025-07-11T23:59:59Z'
ORDER BY eventTime DESC
```

### Mejores prácticas de análisis de logs

Mejores prácticas para analizar efectivamente logs de tu cluster de EKS:

#### Logging estructurado

Usa formatos de logs estructurados (por ejemplo, JSON) en tus aplicaciones:

```json
{
  "timestamp": "2025-07-11T13:00:00Z",
  "level": "INFO",
  "message": "Request processed successfully",
  "request_id": "12345",
  "user_id": "user-789",
  "duration_ms": 45,
  "status_code": 200
}
```

#### IDs de correlación

Usa IDs de correlación para rastrear solicitudes a través de sistemas distribuidos:

```java
import org.slf4j.MDC;

public class RequestHandler {
    public void handleRequest(Request request) {
        String correlationId = request.getHeader("X-Correlation-ID");
        if (correlationId == null) {
            correlationId = UUID.randomUUID().toString();
        }

        MDC.put("correlation_id", correlationId);

        try {
            // Process request
        } finally {
            MDC.remove("correlation_id");
        }
    }
}
```

#### Uso de niveles de log

Usa niveles de log apropiados para indicar la importancia de los logs:

- **ERROR**: Errores y excepciones de la aplicación
- **WARN**: Problemas potenciales o situaciones inesperadas
- **INFO**: Eventos generales de la aplicación
- **DEBUG**: Información detallada útil para depuración
- **TRACE**: Información de depuración muy detallada

#### Política de retención de logs

Establece políticas de retención de logs según los requisitos de costo y conformidad:

```bash
# Set CloudWatch Logs log group retention period
aws logs put-retention-policy \
  --log-group-name /aws/eks/my-cluster/cluster \
  --retention-in-days 30

# Set S3 bucket lifecycle policy
aws s3api put-bucket-lifecycle-configuration \
  --bucket my-logs-bucket \
  --lifecycle-configuration file://lifecycle-config.json
```

lifecycle-config.json:
```json
{
  "Rules": [
    {
      "ID": "Delete old logs",
      "Status": "Enabled",
      "Prefix": "logs/",
      "Expiration": {
        "Days": 90
      }
    },
    {
      "ID": "Archive old logs",
      "Status": "Enabled",
      "Prefix": "logs/",
      "Transitions": [
        {
          "Days": 30,
          "StorageClass": "STANDARD_IA"
        },
        {
          "Days": 60,
          "StorageClass": "GLACIER"
        }
      ]
    }
  ]
}
```
## Mejores prácticas de monitoreo y logging

Exploremos mejores prácticas para implementar efectivamente monitoreo y logging en clusters de EKS.

### Mejores prácticas de monitoreo

#### Monitoreo multicapa

Monitorea todas las capas de tu cluster de EKS:

1. **Capa de infraestructura**: Instancias EC2, VPC, subnets, security groups
2. **Capa de cluster**: Control Plane, nodes, pods, services
3. **Capa de aplicación**: Rendimiento de la aplicación, experiencia del usuario

#### Monitoreo de Golden Signals

Enfócate en las "4 Golden Signals" sugeridas en el libro SRE de Google:

1. **Latencia**: Tiempo necesario para procesar solicitudes
2. **Tráfico**: Número de solicitudes al sistema
3. **Errores**: Tasa de solicitudes fallidas
4. **Saturación**: Qué tan "lleno" está el sistema (por ejemplo, uso de memoria)

#### Monitoreo proactivo

Implementa monitoreo proactivo para detectar problemas antes de que ocurran:

1. **Análisis de tendencias**: Analiza tendencias de uso de recursos a lo largo del tiempo
2. **Detección de anomalías**: Detecta patrones anormales
3. **Análisis predictivo**: Pronostica requisitos futuros de recursos

#### Escalado automatizado

Implementa escalado automatizado basado en datos de monitoreo:

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: app-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: app
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

#### Monitoreo de métricas de negocio

Monitorea métricas de negocio además de métricas técnicas:

1. **Actividad de usuarios**: Número de usuarios activos, duración de sesión
2. **Transacciones**: Cantidad de transacciones, valor de transacción
3. **Tasa de conversión**: Tasa de conversión de usuarios, tasa de abandono
4. **Cumplimiento de SLA**: Si se están cumpliendo los Service Level Objectives (SLOs)

### Mejores prácticas de logging

#### Logging centralizado

Agrega todos los logs en una ubicación central:

1. **Formato consistente**: Usa un formato de log consistente en todas las aplicaciones
2. **Repositorio central**: Usa un repositorio central de logs como CloudWatch Logs, OpenSearch o Loki
3. **Reenvío de logs**: Usa agentes de reenvío de logs como Fluent Bit o Fluentd

#### Incluir información de contexto

Incluye suficiente información de contexto en los logs:

1. **Timestamp**: Timestamp preciso (se recomienda formato ISO 8601)
2. **Request ID**: ID único para seguimiento de solicitudes en sistemas distribuidos
3. **Información de usuario**: ID de usuario o ID de sesión (excluyendo información de identificación personal)
4. **Información de Service**: Nombre del Service, versión, ID de instancia
5. **Detalles de error**: Código de error, mensaje de error, stack trace

#### Filtrado por nivel de log

Establece niveles de log apropiados según el entorno:

1. **Entorno de desarrollo**: Nivel DEBUG o TRACE
2. **Entorno de staging**: Nivel INFO
3. **Entorno de producción**: Nivel INFO o WARN (DEBUG puede habilitarse según sea necesario)

#### Protección de información confidencial

Protege la información confidencial en logs:

1. **Enmascaramiento de PII**: Enmascara información de identificación personal (PII)
2. **Excluir credenciales**: Excluye credenciales como contraseñas, tokens y API keys
3. **Cifrado**: Cifra logs en reposo y en tránsito

### Mejores prácticas de alertas

#### Prioridad de alertas

Prioriza alertas para reducir la fatiga por alertas:

1. **P1 (Critical)**: Problemas graves que requieren acción inmediata
2. **P2 (High)**: Problemas importantes que requieren acción dentro del horario laboral
3. **P3 (Medium)**: Problemas que requieren acción durante mantenimiento programado
4. **P4 (Low)**: Alertas informativas

#### Agrupación de alertas

Agrupa alertas relacionadas para reducir notificaciones duplicadas:

```yaml
route:
  group_by: ['alertname', 'job', 'instance']
  group_wait: 30s
  group_interval: 5m
  repeat_interval: 4h
```

#### Alertas accionables

Incluye suficiente información en las alertas para solucionar problemas:

1. **Título claro**: Título que describa claramente el problema
2. **Descripción detallada**: Descripción detallada de la causa y el impacto
3. **Pasos de solución de problemas**: Pasos o enlaces para solucionar problemas
4. **Métricas y logs relacionados**: Enlaces a métricas y logs útiles para el diagnóstico

#### Pruebas de alertas

Prueba periódicamente tu sistema de alertas:

1. **Simulación de alertas**: Genera alertas de prueba
2. **Pruebas de escalamiento**: Prueba rutas de escalamiento
3. **Inyección de fallos**: Inyecta fallos en entornos controlados

### Mejores prácticas de optimización de costos

#### Optimización del volumen de logs

Optimiza el volumen de logs para reducir costos:

1. **Muestreo**: Muestrea logs de alto volumen
2. **Filtrado**: Filtra logs innecesarios
3. **Compresión**: Comprime logs

#### Gestión de cardinalidad de métricas

Gestiona la cardinalidad de métricas para reducir costos:

1. **Límites de labels**: Limita el número de labels usados en métricas
2. **Agregación**: Agrega métricas detalladas a niveles superiores
3. **Muestreo**: Muestrea métricas de alta resolución

#### Jerarquización de almacenamiento

Implementa una jerarquización de almacenamiento rentable:

1. **Hot Storage**: Logs recientes y consultados frecuentemente
2. **Warm Storage**: Logs consultados con menor frecuencia
3. **Cold Storage**: Logs archivados

## Solución de problemas y depuración

Exploremos varias técnicas para solucionar problemas y depurar incidencias en clusters de EKS.

```mermaid
flowchart TD
    subgraph Troubleshooting_Areas ["Troubleshooting Areas"]
        subgraph Cluster_Issues ["Cluster Issues"]
            Control_Plane[Control Plane Issues]
            Node_Issues[Node Issues]
            Networking[Networking Issues]
            Auth_Issues[Authentication/Authorization Issues]
        end

        subgraph Workload_Issues ["Workload Issues"]
            Pod_Issues[Pod Issues]
            Service_Issues[Service Issues]
            Deployment_Issues[Deployment Issues]
            Resource_Issues[Resource Issues]
        end

        subgraph Common_Problems ["Common Problems"]
            ImagePull[ImagePullBackOff]
            CrashLoop[CrashLoopBackOff]
            NodeNotReady[Node NotReady]
            Connection[Service Connection Issues]
        end
    end

    subgraph Debugging_Tools ["Debugging Tools"]
        subgraph K8s_Tools ["Kubernetes Tools"]
            Kubectl[kubectl]
            K8s_Debug[kubectl debug]
            K8s_Events[kubectl events]
            K8s_Logs[kubectl logs]
        end

        subgraph AWS_Tools ["AWS Tools"]
            AWS_CLI[AWS CLI]
            CloudWatch[CloudWatch]
            CloudTrail[CloudTrail]
            X_Ray[X-Ray]
        end

        subgraph Network_Tools ["Network Tools"]
            Netshoot[Netshoot]
            TCPDump[tcpdump]
            Dig[dig/nslookup]
            Curl[curl/wget]
        end
    end

    Control_Plane --> Kubectl
    Control_Plane --> AWS_CLI
    Control_Plane --> CloudWatch

    Node_Issues --> K8s_Debug
    Node_Issues --> AWS_CLI

    Networking --> Netshoot
    Networking --> TCPDump

    Pod_Issues --> K8s_Logs
    Pod_Issues --> K8s_Debug

    Service_Issues --> K8s_Events
    Service_Issues --> Dig
    Service_Issues --> Curl

    ImagePull --> K8s_Events
    ImagePull --> K8s_Logs

    CrashLoop --> K8s_Logs
    CrashLoop --> K8s_Debug

    NodeNotReady --> AWS_CLI
    NodeNotReady --> K8s_Events

    Connection --> Netshoot
    Connection --> TCPDump

    %% Class definitions
    classDef awsService fill:#FF9900,stroke:#333,stroke-width:1px,color:black;
    classDef k8sComponent fill:#326CE5,stroke:#333,stroke-width:1px,color:white;
    classDef userApp fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;
    classDef dataStore fill:#3B48CC,stroke:#333,stroke-width:1px,color:white;
    classDef default fill:#f9f9f9,stroke:#333,stroke-width:1px,color:black;

    %% Class application
    class AWS_CLI,CloudWatch,CloudTrail,X_Ray awsService;
    class Kubectl,K8s_Debug,K8s_Events,K8s_Logs,Control_Plane,Node_Issues,Pod_Issues,Service_Issues,Deployment_Issues k8sComponent;
    class Netshoot,TCPDump,Dig,Curl userApp;
    class ImagePull,CrashLoop,NodeNotReady,Connection,Networking,Auth_Issues,Resource_Issues default;
```

### Solución de problemas del cluster

#### Comprobar el estado del cluster

```bash
# Check cluster status
aws eks describe-cluster --name my-cluster --query "cluster.status"

# Check cluster endpoint
aws eks describe-cluster --name my-cluster --query "cluster.endpoint"

# Check cluster logs
aws eks update-cluster-config \
  --name my-cluster \
  --logging '{"clusterLogging":[{"types":["api","audit","authenticator","controllerManager","scheduler"],"enabled":true}]}'

# Check cluster logs in CloudWatch Logs
aws logs get-log-events \
  --log-group-name /aws/eks/my-cluster/cluster \
  --log-stream-name kube-apiserver-12345abcde \
  --limit 10
```

#### Solución de problemas de Node

```bash
# Check node status
kubectl get nodes
kubectl describe node <node-name>

# Check node group status
aws eks describe-nodegroup \
  --cluster-name my-cluster \
  --nodegroup-name my-nodegroup

# Check node logs
aws ec2 get-console-output \
  --instance-id i-1234567890abcdef0

# Access node via SSH
ssh -i ~/.ssh/my-key.pem ec2-user@<node-ip>
```

#### Solución de problemas de Pod

```bash
# Check pod status
kubectl get pods -A
kubectl describe pod <pod-name> -n <namespace>

# Check pod logs
kubectl logs <pod-name> -n <namespace>
kubectl logs <pod-name> -n <namespace> --previous  # Logs from previous container

# Check pod events
kubectl get events -n <namespace> --sort-by='.lastTimestamp'

# Access pod shell
kubectl exec -it <pod-name> -n <namespace> -- /bin/bash
```

### Solución de problemas de red

#### Solución de problemas de Service

```bash
# Check service status
kubectl get svc -A
kubectl describe svc <service-name> -n <namespace>

# Check endpoints
kubectl get endpoints <service-name> -n <namespace>

# DNS check
kubectl run -it --rm --restart=Never busybox --image=busybox:1.28 -- nslookup <service-name>.<namespace>.svc.cluster.local

# Port forwarding
kubectl port-forward svc/<service-name> 8080:80 -n <namespace>
```

#### Solución de problemas de Network Policy

```bash
# Check network policies
kubectl get networkpolicies -A
kubectl describe networkpolicy <policy-name> -n <namespace>

# Test network connectivity
kubectl run -it --rm --restart=Never busybox --image=busybox:1.28 -- wget -O- <service-name>.<namespace>.svc.cluster.local

# Packet capture
kubectl debug node/<node-name> -it --image=nicolaka/netshoot -- tcpdump -i any port 80
```

### Solución de problemas de logging y monitoreo

#### Solución de problemas de Fluent Bit

```bash
# Check Fluent Bit pod status
kubectl get pods -n kube-system -l app=aws-for-fluent-bit

# Check Fluent Bit logs
kubectl logs -n kube-system -l app=aws-for-fluent-bit

# Check Fluent Bit configuration
kubectl get cm -n kube-system fluent-bit-config -o yaml
```

#### Solución de problemas de Prometheus

```bash
# Check Prometheus pod status
kubectl get pods -n monitoring -l app=prometheus

# Check Prometheus logs
kubectl logs -n monitoring -l app=prometheus-server

# Check Prometheus targets
kubectl port-forward -n monitoring svc/prometheus-server 9090:80
# Access http://localhost:9090/targets in browser
```

#### Solución de problemas de Grafana

```bash
# Check Grafana pod status
kubectl get pods -n monitoring -l app=grafana

# Check Grafana logs
kubectl logs -n monitoring -l app=grafana

# Check Grafana data sources
kubectl port-forward -n monitoring svc/grafana 3000:80
# Access http://localhost:3000/datasources in browser
```

### Problemas comunes y soluciones

#### Error ImagePullBackOff

Problema: Pod atascado en estado ImagePullBackOff

Soluciones:
1. Verifica que el nombre y tag de la imagen sean correctos
2. Revisa el image pull secret para registros privados
3. Verifica que el Node tenga acceso a internet

```bash
# Create image pull secret
kubectl create secret docker-registry regcred \
  --docker-server=<registry-server> \
  --docker-username=<username> \
  --docker-password=<password> \
  --docker-email=<email>

# Apply secret to pod
kubectl patch serviceaccount default -p '{"imagePullSecrets": [{"name": "regcred"}]}'
```

#### Error CrashLoopBackOff

Problema: Pod que se reinicia repetidamente en estado CrashLoopBackOff

Soluciones:
1. Revisa los logs del pod
2. Revisa los resource limits
3. Revisa la configuración de la aplicación

```bash
# Check pod logs
kubectl logs <pod-name> -n <namespace>

# Check pod events
kubectl describe pod <pod-name> -n <namespace>

# Add debug container
kubectl debug <pod-name> -n <namespace> --image=busybox:1.28 --target=<container-name>
```

#### Estado Node NotReady

Problema: Node mostrado en estado NotReady

Soluciones:
1. Revisa el estado y los eventos del Node
2. Revisa los logs de kubelet
3. Revisa el uso de recursos del Node

```bash
# Check node status
kubectl describe node <node-name>

# Access node via SSH
ssh -i ~/.ssh/my-key.pem ec2-user@<node-ip>

# Check kubelet logs
sudo journalctl -u kubelet

# Check node resource usage
top
df -h
```

#### Problemas de conexión de Service

Problema: No se puede conectar al Service

Soluciones:
1. Revisa el Service y los endpoints
2. Revisa las labels y selectors del pod
3. Revisa las network policies

```bash
# Check service and endpoints
kubectl get svc <service-name> -n <namespace>
kubectl get endpoints <service-name> -n <namespace>

# Check pod labels
kubectl get pods -n <namespace> --show-labels

# Check service selector
kubectl get svc <service-name> -n <namespace> -o jsonpath='{.spec.selector}'

# Check network policies
kubectl get networkpolicies -n <namespace>
```

### Herramientas de depuración

#### Herramientas de depuración de kubectl

```bash
# Pod debugging
kubectl debug <pod-name> -n <namespace> --image=busybox:1.28 --target=<container-name>

# Node debugging
kubectl debug node/<node-name> -it --image=busybox:1.28

# Create temporary debugging pod
kubectl run debug --rm -it --image=nicolaka/netshoot -- /bin/bash
```

#### Herramientas de depuración de AWS CLI

```bash
# Describe EKS cluster
aws eks describe-cluster --name my-cluster

# Describe EKS node group
aws eks describe-nodegroup --cluster-name my-cluster --nodegroup-name my-nodegroup

# CloudWatch Logs query
aws logs start-query \
  --log-group-name /aws/eks/my-cluster/cluster \
  --start-time $(date -u -v-1H +%s) \
  --end-time $(date -u +%s) \
  --query-string 'fields @timestamp, @message | filter @message like /Error/'
```

#### Herramientas de depuración de red

```bash
# Create network debugging pod
kubectl run netshoot --rm -it --image=nicolaka/netshoot -- /bin/bash

# Test network connectivity
nc -zv <service-name> <port>
curl -v <service-name>:<port>

# DNS check
dig <service-name>.<namespace>.svc.cluster.local

# Packet capture
tcpdump -i any port <port> -w capture.pcap
```

## Conclusión

En este documento, exploramos varias herramientas, técnicas y mejores prácticas para monitoreo y logging en clusters de Amazon EKS. Implementar una estrategia efectiva de monitoreo y logging te permite comprender continuamente el estado de tu cluster, detectar problemas de forma temprana y responder rápidamente cuando ocurren problemas.

Temas clave cubiertos:

1. **Descripción general de monitoreo y logging**: Importancia y arquitectura del monitoreo y logging
2. **Logging del Control Plane de EKS**: Tipos de logs del Control Plane y cómo habilitarlos
3. **Logging de contenedores**: Recopilación de logs de contenedores usando Fluent Bit y CloudWatch Container Insights
4. **Monitoreo del cluster**: Monitoreo del cluster usando CloudWatch, Prometheus y Grafana
5. **Alertas y gestión de eventos**: Configuración de alertas usando CloudWatch alarms y Prometheus Alertmanager
6. **Análisis y visualización de logs**: Análisis de logs usando CloudWatch Logs Insights, OpenSearch y Grafana Loki
7. **Mejores prácticas de monitoreo y logging**: Mejores prácticas para monitoreo y logging efectivos
8. **Solución de problemas y depuración**: Problemas comunes y soluciones

El monitoreo y logging en clusters de EKS es un proceso continuo que debe mejorarse constantemente para cumplir los requisitos de tu cluster y aplicaciones.

## Referencias

- [Amazon EKS Monitoring Best Practices](https://aws.github.io/aws-eks-best-practices/observability/monitoring/)
- [Amazon EKS Logging Best Practices](https://aws.github.io/aws-eks-best-practices/observability/logging/)
- [Kubernetes Monitoring Architecture](https://kubernetes.io/docs/tasks/debug-application-cluster/resource-usage-monitoring/)
- [Prometheus Documentation](https://prometheus.io/docs/introduction/overview/)
- [Grafana Documentation](https://grafana.com/docs/grafana/latest/)
- [Fluent Bit Documentation](https://docs.fluentbit.io/manual/)
- [Amazon CloudWatch Documentation](https://docs.aws.amazon.com/cloudwatch/)
- [Amazon OpenSearch Service Documentation](https://docs.aws.amazon.com/opensearch-service/)

## Quiz

Para comprobar lo que aprendiste en este capítulo, intenta el [topic quiz](../quizzes/eks/06-eks-monitoring-logging-quiz.md).
