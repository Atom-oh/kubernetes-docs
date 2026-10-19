# Infraestructura avanzada

> **Baseline de revisión**: Terraform 1.15.7, AWS Provider 6.69.1, AWS Load Balancer Controller 3.5.0, Boto3 1.43.92
> **Última revisión**: 16 de octubre de 2026. Los ejemplos se comprobaron localmente con esquemas y dobles de prueba; no se realizó ningún cambio de tráfico real en AWS.

< [Anterior: Infraestructura de Terraform](01-infrastructure-setup.md) | [Tabla de contenido](README.md) | [Siguiente: Pipelines de CI](03-ci-pipelines.md) >

Esta guía separa dos diseños de tráfico: **un NLB con grupos de destino ponderados** y la **selección DNS entre dos balanceadores de carga independientes**. Son alternativas; no son dos controles que puedan seleccionar clústeres por separado detrás del mismo NLB compartido.

## 1. Resumen de la arquitectura Blue/Green

Blue/Green proporciona otro entorno para validar y una ruta para devolver el tráfico. No garantiza tiempo de inactividad cero, reversión instantánea, replicación automática de datos ni coste cero entre zonas de disponibilidad. Dimensiona el destino para la carga entrante y mantén los cambios de base de datos/esquema compatibles con ambas versiones.

El [ejemplo de base](01-infrastructure-setup.md) usa varias zonas de disponibilidad y los grupos integrados de Auto Mode. El color de un clúster no fija sus nodos de trabajo a una zona. El plano de control administrado de EKS es regional; una celda de **nodos de trabajo** en una sola zona requiere restricciones de NodePool/NodeClass independientes y capacidad de recuperación. Consulta [Operaciones por zona](15-zonal-operations-guide.md).

| Aspecto | Planificación requerida |
|---|---|
| Transición del tráfico | Flujos nuevos, conexiones persistentes, propagación, reintentos del cliente, SLO |
| Datos | Replicación, coherencia, propiedad de escritura, compatibilidad de migraciones, punto de recuperación |
| Capacidad | Destinos saludables en el entorno de destino y capacidad probada bajo carga, incluso si falla una AZ |
| Propiedad de configuración | Un solo escritor para las acciones del listener; coordina Terraform, scripts y automatización |
| Costes | Ambas flotas de clústeres, balanceadores/endpoints, replicación y rutas entre zonas; mide el uso real |

![Un listener NLB compartido selecciona los grupos de destino Blue/Green; cada clúster usa un AWS Load Balancer Controller instalado por separado para registrar los destinos de servicio TLS.](../.gitbook/assets/en-ops-02-infrastructure-advanced-0.png)

[Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-ops-02-infrastructure-advanced-0.html)

## 2. Grupos de destino ponderados de NLB

El ejemplo tiene un **listener TCP/443 con paso directo de TLS al puerto 8443 del Pod**. Cada clúster debe tener ya `production/app-https`, el puerto 443 del Service asignado a targetPort 8443, un endpoint TLS funcional y una ruta HTTPS `/healthz` que devuelva 200. El backend termina TLS y presenta el certificado de la aplicación. Un listener TCP de NLB no puede generar una redirección de HTTP a HTTPS.

Usa el estado de red del capítulo 01. Coloca los siguientes archivos en una nueva raíz Terraform `nlb/`; inicializa su backend S3 con una clave independiente, como `nlb/terraform.tfstate`. Proporciona el bucket de estado real, el CIDR de VPC y los CIDR de clientes aprobados. Las direcciones de documentación no son permisos de cliente válidos.

### NLB y grupos de destino

```hcl
# nlb/main.tf
terraform {
  required_version = ">= 1.10.0"
  backend "s3" {}
  required_providers {
    aws = { source = "hashicorp/aws", version = "6.69.1" }
  }
}
provider "aws" { region = var.region }
data "aws_caller_identity" "current" {}
data "terraform_remote_state" "network" {
  backend = "s3"
  config = {
    bucket = var.state_bucket_name
    key    = "network/terraform.tfstate"
    region = var.region
  }
}
locals {
  name_prefix = "${var.project_name}-${var.environment}"
  tags        = { Project = var.project_name, Environment = var.environment, ManagedBy = "terraform" }
  alarm_names = { for color in ["blue", "green"] : color => "${local.name_prefix}-${color}-no-healthy" }
  alarm_arns  = { for color, name in local.alarm_names : color => "arn:aws:cloudwatch:${var.region}:${data.aws_caller_identity.current.account_id}:alarm:${name}" }
}
resource "aws_security_group" "nlb" {
  name_prefix = "docs-nlb-"
  description = "Approved clients to the TLS passthrough listener"
  vpc_id      = data.terraform_remote_state.network.outputs.vpc_id
  tags        = local.tags
}
resource "aws_vpc_security_group_ingress_rule" "clients" {
  for_each          = toset(var.allowed_client_cidrs)
  security_group_id = aws_security_group.nlb.id
  cidr_ipv4         = each.value
  ip_protocol       = "tcp"
  from_port         = 443
  to_port           = 443
}
resource "aws_vpc_security_group_egress_rule" "targets" {
  security_group_id = aws_security_group.nlb.id
  cidr_ipv4         = var.target_vpc_cidr
  ip_protocol       = "tcp"
  from_port         = var.backend_port
  to_port           = var.backend_port
}
resource "aws_lb" "shared" {
  name_prefix                      = "docs-"
  internal                         = false
  load_balancer_type               = "network"
  subnets                          = data.terraform_remote_state.network.outputs.public_subnet_ids
  security_groups                  = [aws_security_group.nlb.id]
  enable_cross_zone_load_balancing = true
  enable_deletion_protection       = var.environment == "prod"
  tags                             = local.tags
}
resource "aws_lb_target_group" "cluster" {
  for_each    = toset(["blue", "green"])
  name_prefix = each.key == "blue" ? "doc-b-" : "doc-g-"
  port        = var.backend_port
  protocol    = "TCP"
  target_type = "ip"
  vpc_id      = data.terraform_remote_state.network.outputs.vpc_id
  health_check {
    enabled             = true
    protocol            = "HTTPS"
    port                = "traffic-port"
    path                = "/healthz"
    matcher             = "200"
    interval            = 10
    healthy_threshold   = 2
    unhealthy_threshold = 2
  }
  deregistration_delay   = 30
  connection_termination = true
  preserve_client_ip     = true
  proxy_protocol_v2      = false
  lifecycle { create_before_destroy = true }
  tags = merge(local.tags, { Cluster = each.key })
}
resource "aws_lb_listener" "tls_passthrough" {
  load_balancer_arn = aws_lb.shared.arn
  port              = 443
  protocol          = "TCP"
  default_action {
    type = "forward"
    forward {
      target_group {
        arn    = aws_lb_target_group.cluster["blue"].arn
        weight = var.traffic_weights.blue
      }
      target_group {
        arn    = aws_lb_target_group.cluster["green"].arn
        weight = var.traffic_weights.green
      }
    }
  }
  tags = local.tags
}
```

### Entradas

```hcl
# nlb/variables.tf
variable "region" {
  type    = string
  default = "ap-northeast-2"
}
variable "project_name" {
  type    = string
  default = "eks-platform"
}
variable "environment" {
  type    = string
  default = "dev"
}
variable "state_bucket_name" { type = string }
variable "target_vpc_cidr" {
  description = "CIDR of the same VPC containing the target Pods"
  type        = string
}
variable "allowed_client_cidrs" {
  description = "Approved IPv4 client CIDRs. Supply real values, not documentation addresses"
  type        = list(string)
  validation {
    condition     = length(var.allowed_client_cidrs) > 0 && alltrue([for cidr in var.allowed_client_cidrs : can(cidrnetmask(cidr)) && cidr != "0.0.0.0/0"])
    error_message = "Supply explicit IPv4 CIDRs. Do not expose this example to 0.0.0.0/0."
  }
}
variable "traffic_weights" {
  type    = object({ blue = number, green = number })
  default = { blue = 100, green = 0 }
  validation {
    condition     = alltrue([for value in values(var.traffic_weights) : value >= 0 && value <= 999 && floor(value) == value]) && var.traffic_weights.blue + var.traffic_weights.green > 0
    error_message = "Use integer weights 0..999 with at least one positive weight. The sum need not be 100."
  }
}
variable "automatic_failover" {
  description = "Opt in only after validating capacity, reconnection behavior, and single-writer ownership"
  type        = bool
  default     = false
}
variable "minimum_destination_targets" {
  description = "A demo health gate, not proof of enough capacity. Size from load testing"
  type        = number
  default     = 1
  validation {
    condition     = var.minimum_destination_targets >= 1 && floor(var.minimum_destination_targets) == var.minimum_destination_targets
    error_message = "Use a positive integer destination target count."
  }
}
variable "notification_email" {
  type    = string
  default = null
}

variable "backend_port" {
  description = "Actual Pod TLS targetPort, shared with the Service/TGB networking example"
  type        = number
  default     = 8443
  validation {
    condition     = var.backend_port >= 1 && var.backend_port <= 65535 && floor(var.backend_port) == var.backend_port
    error_message = "Use an integer TCP backend port."
  }
}
```

Los pesos son **enteros relativos de 0–999**, no porcentajes obligatorios. 5:5 y 50:50 expresan la misma proporción relativa. El tamaño de los flujos, las sesiones persistentes y el muestreo pueden hacer que las proporciones observadas de solicitudes/bytes sean distintas. Este ejemplo rechaza explícitamente una configuración con todos los pesos en cero.

La [documentación de listeners NLB](https://docs.aws.amazon.com/elasticloadbalancing/latest/network/load-balancer-listeners.html) distingue los cambios de peso normales del valor cero: poco después de establecer cero, dejan de aceptarse conexiones nuevas y se cierran las existentes. El retraso de anulación del registro es un control diferente. Valida el comportamiento de conexiones y reintentos antes de cambiar un peso a cero; después del cambio, observa `NewFlowCount`, `ActiveFlowCount`, los errores y la latencia.

El balanceo entre zonas está habilitado porque un grupo restringido a una AZ debe seguir siendo accesible desde los otros nodos del NLB durante la transición de la flota. Deshabilitarlo cambia las restricciones de enrutamiento y puede impedir la división prevista. Ten en cuenta la ruta real entre zonas y su coste. Los grupos de seguridad se asocian al crear el NLB: un NLB que se crea sin ellos no puede adquirirlos después.

### Registro dinámico de destinos

Instala y configura el **AWS Load Balancer Controller autogestionado** en cada clúster. Usa TGB `elbv2.k8s.aws/v1beta1`, un grupo de destino distinto por clúster. Terraform es propietario del LB/TG y del grupo de seguridad frontal; la configuración de red del TGB solicita las reglas de backend a ese controlador. No administres también con Terraform esas mismas reglas de backend ni los cambios de asociaciones de IP de Pods.

```yaml
# tgb.yaml
# Separately installed AWS Load Balancer Controller, not the built-in Auto Mode TGB API.
# Replace all IDs. The production/app-https Service and its TLS targetPort 8443 must exist.
apiVersion: elbv2.k8s.aws/v1beta1
kind: TargetGroupBinding
metadata:
  name: app-tls
  namespace: production
spec:
  targetGroupARN: arn:aws:elasticloadbalancing:ap-northeast-2:111122223333:targetgroup/REPLACE_BLUE_GROUP/0000000000000001
  targetType: ip
  vpcID: vpc-REPLACE_ME
  serviceRef:
    name: app-https
    port: 443
  networking:
    ingress:
      - from:
          - securityGroup:
              groupID: sg-REPLACE_NLB_SG
        ports:
          - protocol: TCP
            port: 8443
```

Usa el ARN de Blue en el clúster Blue y el ARN de Green en el clúster Green, y reemplaza los ID del grupo de seguridad de VPC/NLB. Si cambia el targetPort del Pod, actualiza tanto `backend_port` como el puerto de red del TGB. El controlador necesita permisos para registrar destinos y reconciliar los grupos de seguridad de backend correspondientes.

El TGB integrado de Auto Mode usa `eks.amazonaws.com/v1`. Sus [reglas de etiquetas y ciclo de vida](https://docs.aws.amazon.com/eks/latest/userguide/auto-configure-alb.html) son distintas: AWS documenta que se elimina el grupo de destino cuando se elimina ese TGB o el clúster. No lo sustituyas por el grupo de destino de propiedad externa de este ejemplo. `multiClusterTargetGroup` es pertinente cuando se comparte intencionadamente un TG entre clústeres; esta receta usa TG distintos.

### Salidas

```hcl
# nlb/outputs.tf
output "nlb_arn" { value = aws_lb.shared.arn }
output "nlb_dns_name" { value = aws_lb.shared.dns_name }
output "nlb_zone_id" { value = aws_lb.shared.zone_id }
output "listener_arn" { value = aws_lb_listener.tls_passthrough.arn }
output "nlb_security_group_id" { value = aws_security_group.nlb.id }
output "target_group_arns" { value = { for color, group in aws_lb_target_group.cluster : color => group.arn } }
output "traffic_weights" { value = var.traffic_weights }
output "automatic_failover" { value = var.automatic_failover }
output "minimum_destination_targets" { value = var.minimum_destination_targets }

output "backend_port" { value = var.backend_port }
```

## 3. Cambio de tráfico basado en DNS

Para seleccionar destinos mediante DNS, proporciona **dos endpoints reales e independientes de ALB/NLB**, cada uno dirigido a su clúster correspondiente. Apuntar `blue.example.com` y `green.example.com` al mismo NLB compartido no selecciona grupos de destino diferentes, ni siquiera con distintos pesos de registro o nombres de comprobación de estado.

Esta raíz `dns/` independiente supone que esos dos balanceadores ya existen. Muestra `app.<domain>` ponderado, registros directos por color y un nombre aparte `failover.<domain>`. Elige los nombres que necesites; no combines políticas de enrutamiento incompatibles en un mismo nombre/tipo.

```hcl
# dns/main.tf
terraform {
  required_version = ">= 1.10.0"
  backend "s3" {}
  required_providers {
    aws = { source = "hashicorp/aws", version = "6.69.1" }
  }
}
provider "aws" { region = var.region }
# This is an ALTERNATIVE with two independently provisioned load balancers.
# Supplying the shared NLB from the first example for both entries is rejected.
resource "aws_route53_record" "weighted" {
  for_each       = var.endpoints
  zone_id        = var.hosted_zone_id
  name           = "app.${var.domain_name}"
  type           = "A"
  set_identifier = each.key
  weighted_routing_policy { weight = each.value.weight }
  alias {
    name                   = each.value.dns_name
    zone_id                = each.value.zone_id
    evaluate_target_health = true
  }
}
resource "aws_route53_record" "direct" {
  for_each = var.endpoints
  zone_id  = var.hosted_zone_id
  name     = "${each.key}.${var.domain_name}"
  type     = "A"
  alias {
    name                   = each.value.dns_name
    zone_id                = each.value.zone_id
    evaluate_target_health = true
  }
}
# Different DNS name from the weighted example: don't mix policies on one name/type.
resource "aws_route53_record" "failover" {
  for_each       = var.endpoints
  zone_id        = var.hosted_zone_id
  name           = "failover.${var.domain_name}"
  type           = "A"
  set_identifier = each.key
  failover_routing_policy {
    type = each.key == "blue" ? "PRIMARY" : "SECONDARY"
  }
  alias {
    name                   = each.value.dns_name
    zone_id                = each.value.zone_id
    evaluate_target_health = true
  }
}
```

```hcl
# dns/variables.tf
variable "region" {
  type    = string
  default = "ap-northeast-2"
}
variable "hosted_zone_id" { type = string }
variable "domain_name" { type = string }
variable "endpoints" {
  description = "Two existing independent ALB/NLB endpoints with healthy targets"
  type        = map(object({ dns_name = string, zone_id = string, weight = number }))
  validation {
    condition     = toset(keys(var.endpoints)) == toset(["blue", "green"])
    error_message = "Exactly blue and green endpoints are required."
  }
  validation {
    condition     = length(distinct([for e in values(var.endpoints) : trimprefix(lower(trimsuffix(e.dns_name, ".")), "dualstack.")])) == 2
    error_message = "Two records pointing at the same shared NLB cannot select different clusters."
  }
  validation {
    condition     = alltrue([for e in values(var.endpoints) : e.weight >= 0 && e.weight <= 255 && floor(e.weight) == e.weight]) && sum([for e in values(var.endpoints) : e.weight]) > 0
    error_message = "Use integer DNS weights0..255 with a positive total for this example."
  }
}
```

Los pesos de Route 53 son enteros de **0–255**, a diferencia de los pesos de ELB. Los registros ponderados comparten un mismo nombre/tipo DNS y tienen identificadores de conjunto distintos. Las respuestas DNS quedan en caché y las conexiones pueden durar más que las entradas DNS. Los registros Alias heredan el TTL del destino ELB; no reemplaces los endpoints DNS generados por el balanceador con direcciones IP copiadas manualmente solo para establecer un TTL.

`evaluate_target_health` evalúa el balanceador de destino, no una transacción específica de la aplicación. Si ninguna opción está saludable, las políticas DNS tienen un comportamiento alternativo; no garantizan detener el tráfico. El TTL, la detección de estado, el comportamiento del resolver, la propagación y la reconexión determinan conjuntamente el tiempo de recuperación. No interpretes un TTL de 60 segundos como un SLA de recuperación de 60 segundos.

## 4. Ubicación de nodos de datos

Las restricciones de topología controlan la ubicación, no la replicación ni la recuperación. Un volumen EBS zonal y quien lo consume deben ser compatibles; `WaitForFirstConsumer` permite que el aprovisionamiento siga al nodo elegido por el planificador. nodeSelector/afinidad del Pod selecciona nodos aptos, mientras que los requisitos de NodePool limitan el aprovisionamiento del autoescalador y NodeClass controla la selección de subredes.

El siguiente **laboratorio de PostgreSQL de instancia única no es una base de datos de alta disponibilidad**. Supone que los grupos integrados de Auto Mode del capítulo 01 ya crearon la NodeClass predeterminada, que hay capacidad en la AZ seleccionada y que se preparó `data-demo/postgresql-auth` con una clave `password` mediante el flujo aprobado de secretos. Crea el namespace y el secreto antes de la carga de trabajo. El digest de imagen y los UID/GID 999 se comprobaron con la imagen oficial de PostgreSQL 17 Bookworm.

```yaml
# data-placement.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: data-demo
---
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: database-a
spec:
  template:
    metadata:
      labels:
        workload-type: database
    spec:
      nodeClassRef:
        group: eks.amazonaws.com
        kind: NodeClass
        name: default
      requirements:
        - key: topology.kubernetes.io/zone
          operator: In
          values: [ap-northeast-2a]
        - key: karpenter.sh/capacity-type
          operator: In
          values: [on-demand]
        - key: node.kubernetes.io/instance-type
          operator: In
          values: [r6i.2xlarge, r6i.4xlarge]
      taints:
        - key: dedicated
          value: database
          effect: NoSchedule
  limits:
    cpu: "100"
    memory: 400Gi
  disruption:
    consolidationPolicy: WhenEmpty
    consolidateAfter: 30m
---
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: demo-gp3-auto
provisioner: ebs.csi.eks.amazonaws.com
parameters:
  type: gp3
  encrypted: "true"
volumeBindingMode: WaitForFirstConsumer
reclaimPolicy: Retain
allowVolumeExpansion: true
allowedTopologies:
  - matchLabelExpressions:
      - key: eks.amazonaws.com/compute-type
        values: [auto]
---
apiVersion: v1
kind: Service
metadata:
  name: postgresql
  namespace: data-demo
spec:
  clusterIP: None
  selector:
    app: postgresql
  ports:
    - name: postgres
      port: 5432
      targetPort: postgres
---
# Create data-demo/postgresql-auth with a password key through the approved
# secret-management workflow before deploying this single-instance lab.
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: postgresql
  namespace: data-demo
spec:
  serviceName: postgresql
  replicas: 1
  selector:
    matchLabels:
      app: postgresql
  template:
    metadata:
      labels:
        app: postgresql
    spec:
      nodeSelector:
        workload-type: database
        topology.kubernetes.io/zone: ap-northeast-2a
        eks.amazonaws.com/compute-type: auto
      tolerations:
        - key: dedicated
          operator: Equal
          value: database
          effect: NoSchedule
      securityContext:
        runAsNonRoot: true
        runAsUser: 999
        runAsGroup: 999
        fsGroup: 999
        seccompProfile:
          type: RuntimeDefault
      containers:
        - name: postgres
          image: docker.io/library/postgres@sha256:051f7b7b3abdd564d5d1bd1e8c4b9c1b6e77087d1dd22020ede611c096a272e0
          env:
            - name: POSTGRES_USER
              value: app
            - name: POSTGRES_DB
              value: app
            - name: POSTGRES_PASSWORD_FILE
              value: /run/postgresql-auth/password
            - name: PGDATA
              value: /var/lib/postgresql/data/pgdata
          ports:
            - name: postgres
              containerPort: 5432
          securityContext:
            allowPrivilegeEscalation: false
            capabilities:
              drop: [ALL]
          readinessProbe:
            exec:
              command: [pg_isready, -U, app, -d, app]
            initialDelaySeconds: 10
            periodSeconds: 5
          resources:
            requests:
              cpu: "2"
              memory: 4Gi
            limits:
              cpu: "4"
              memory: 8Gi
          volumeMounts:
            - name: data
              mountPath: /var/lib/postgresql/data
            - name: auth
              mountPath: /run/postgresql-auth
              readOnly: true
      volumes:
        - name: auth
          secret:
            secretName: postgresql-auth
            defaultMode: 0440
  volumeClaimTemplates:
    - metadata:
        name: data
      spec:
        accessModes: [ReadWriteOnce]
        storageClassName: demo-gp3-auto
        resources:
          requests:
            storage: 10Gi
```

El Pod selecciona la etiqueta del grupo de base de datos, tolera su taint y selecciona AZ-a. StorageClass usa el aprovisionador de Auto Mode; WFFC selecciona el almacenamiento para esa ubicación. El subdirectorio `pgdata` evita inicializar PostgreSQL en la raíz de un sistema de archivos EBS que contiene `lost+found`. `Retain` conserva el volumen tras eliminar el claim; no es una copia de seguridad. Al limpiar el laboratorio, revisa los PV y recursos EBS retenidos.

Para usar otra AZ, cambia a la vez el requisito de NodePool y la ubicación del consumidor. Un volumen no se mueve a otra AZ cuando cambia el peso de un NLB. Producción necesita copias de seguridad, replicación/conmutación por error, migraciones y procedimientos de recuperación medidos; consulta [Almacenamiento](../core/04-storage.md) y [Kafka en EKS](../data-on-eks/kafka/README.md).

### Fragmentos de distribución y afinidad

Para distribuir réplicas entre nodos aptos, integra una regla de distribución de topología en una carga de trabajo existente. `maxSkew: 1` con `DoNotSchedule` limita el desequilibrio entre dominios aptos; no crea los nodos que faltan ni garantiza que existan tres AZ.

```yaml
# Fragment under spec.template.spec of an existing Deployment.
topologySpreadConstraints:
  - maxSkew: 1
    topologyKey: kubernetes.io/hostname
    whenUnsatisfiable: DoNotSchedule
    labelSelector:
      matchLabels:
        app: api-server
```

Una caché que está en otro namespace debe especificar dónde están sus pares de afinidad. Es una preferencia flexible por AZ, no una configuración de replicación ni una garantía de que los Pods se ubiquen en el mismo nodo:

```yaml
# Fragment under spec.template.spec.
affinity:
  podAffinity:
    preferredDuringSchedulingIgnoredDuringExecution:
      - weight: 100
        podAffinityTerm:
          namespaces: [production]
          labelSelector:
            matchLabels:
              app: api-server
          topologyKey: topology.kubernetes.io/zone
```

El antiguo StatefulSet básico de Kafka/ZooKeeper no es un despliegue completo de Kafka: el nombre de un Pod no es un ID numérico de broker, y el quorum, los listeners, las direcciones anunciadas, el almacenamiento y la replicación deben configurarse en conjunto. Usa la [guía de Strimzi](../data-on-eks/kafka/02-strimzi-operator.md) y la [explicación de rack awareness](15-zonal-operations-guide.md). Distribuir solo los Pods de Kubernetes no crea replicación de Kafka entre clústeres.

## 5. Automatización de la conmutación por error

Esta es una **referencia para un solo listener**, no una garantía de conmutación por error segura en producción. El valor predeterminado `automatic_failover=false` solo propone un cambio y no concede permiso `ModifyListener`. Actívalo únicamente después de validar la capacidad del destino, la terminación/reconexión de las conexiones, la monitorización y un procedimiento operativo con un solo escritor.

Usa una sola ruta de eventos: **alarma de métrica de CloudWatch → SNS de entrada de alarmas → Lambda**. Envía las decisiones y los fallos a otro tema SNS. No añadas también el ARN de Lambda directamente a las acciones de la alarma: las acciones directas de CloudWatch para Lambda usan `alarmData.state.value`, mientras que este handler acepta deliberadamente solo la envoltura SNS.

```hcl
# nlb/failover.tf
resource "aws_sns_topic" "alarm_input" {
  name = "${local.name_prefix}-alarm-input"
  tags = local.tags
}
resource "aws_sns_topic" "notifications" {
  name = "${local.name_prefix}-transition-notifications"
  tags = local.tags
}
resource "aws_sns_topic_policy" "alarms" {
  for_each = { input = aws_sns_topic.alarm_input.arn, output = aws_sns_topic.notifications.arn }
  arn      = each.value
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "cloudwatch.amazonaws.com" }
      Action    = "sns:Publish"
      Resource  = each.value
      Condition = {
        StringEquals = { "aws:SourceAccount" = data.aws_caller_identity.current.account_id }
        ArnEquals    = { "aws:SourceArn" = values(local.alarm_arns) }
      }
    }]
  })
}

resource "aws_cloudwatch_metric_alarm" "health" {
  for_each            = toset(["blue", "green"])
  alarm_name          = local.alarm_names[each.key]
  namespace           = "AWS/NetworkELB"
  metric_name         = "HealthyHostCount"
  statistic           = "Maximum"
  period              = 60
  evaluation_periods  = 2
  datapoints_to_alarm = 2
  comparison_operator = "LessThanThreshold"
  threshold           = 1
  treat_missing_data  = "missing"
  dimensions = {
    LoadBalancer = aws_lb.shared.arn_suffix
    TargetGroup  = aws_lb_target_group.cluster[each.key].arn_suffix
  }
  alarm_actions             = [aws_sns_topic.alarm_input.arn]
  ok_actions                = [aws_sns_topic.notifications.arn]
  insufficient_data_actions = [aws_sns_topic.notifications.arn]
  depends_on                = [aws_sns_topic_policy.alarms]
  tags                      = local.tags
}
resource "aws_iam_role" "failover" {
  name_prefix = "docs-failover-"
  assume_role_policy = jsonencode({
    Version   = "2012-10-17"
    Statement = [{ Effect = "Allow", Action = "sts:AssumeRole", Principal = { Service = "lambda.amazonaws.com" } }]
  })
  tags = local.tags
}
resource "aws_cloudwatch_log_group" "failover" {
  name              = "/aws/lambda/${local.name_prefix}-failover"
  retention_in_days = 30
  tags              = local.tags
}
resource "aws_iam_role_policy" "failover" {
  role = aws_iam_role.failover.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = concat([
      {
        Effect    = "Allow"
        Action    = ["elasticloadbalancing:DescribeListeners", "elasticloadbalancing:DescribeTargetHealth", "cloudwatch:DescribeAlarms"]
        Resource  = "*"
        Condition = { StringEquals = { "aws:RequestedRegion" = var.region } }
      },
      {
        Effect   = "Allow"
        Action   = ["logs:CreateLogStream", "logs:PutLogEvents"]
        Resource = "${aws_cloudwatch_log_group.failover.arn}:*"
      },
      {
        Effect   = "Allow"
        Action   = "sns:Publish"
        Resource = aws_sns_topic.notifications.arn
      }
      ], var.automatic_failover ? [{
        Effect   = "Allow"
        Action   = "elasticloadbalancing:ModifyListener"
        Resource = aws_lb_listener.tls_passthrough.arn
    }] : [])
  })
}
resource "aws_lambda_function" "failover" {
  function_name                  = "${local.name_prefix}-failover"
  filename                       = "${path.module}/lambda/failover.zip"
  source_code_hash               = filebase64sha256("${path.module}/lambda/failover.zip")
  handler                        = "failover.lambda_handler"
  runtime                        = "python3.12"
  timeout                        = 60
  memory_size                    = 256
  reserved_concurrent_executions = 1
  role                           = aws_iam_role.failover.arn
  environment {
    variables = {
      ACCOUNT_ID                  = data.aws_caller_identity.current.account_id
      LISTENER_ARN                = aws_lb_listener.tls_passthrough.arn
      ALARM_ARNS_JSON             = jsonencode(local.alarm_arns)
      TARGET_GROUP_ARNS_JSON      = jsonencode({ for color, group in aws_lb_target_group.cluster : color => group.arn })
      ALARM_TOPIC_ARN             = aws_sns_topic.alarm_input.arn
      NOTIFICATION_TOPIC_ARN      = aws_sns_topic.notifications.arn
      AUTOMATIC_FAILOVER          = tostring(var.automatic_failover)
      MINIMUM_DESTINATION_TARGETS = tostring(var.minimum_destination_targets)
    }
  }
  depends_on = [aws_iam_role_policy.failover, aws_cloudwatch_log_group.failover]
  tags       = local.tags
}
resource "aws_lambda_permission" "sns" {
  statement_id   = "AlarmTopicOnly"
  action         = "lambda:InvokeFunction"
  function_name  = aws_lambda_function.failover.function_name
  principal      = "sns.amazonaws.com"
  source_arn     = aws_sns_topic.alarm_input.arn
  source_account = data.aws_caller_identity.current.account_id
}
resource "aws_sns_topic_subscription" "lambda" {
  topic_arn  = aws_sns_topic.alarm_input.arn
  protocol   = "lambda"
  endpoint   = aws_lambda_function.failover.arn
  depends_on = [aws_lambda_permission.sns, aws_lambda_function_event_invoke_config.failover]
}
resource "aws_sns_topic_subscription" "operator" {
  for_each = var.notification_email == null ? {} : {
    alarms    = aws_sns_topic.alarm_input.arn
    decisions = aws_sns_topic.notifications.arn
  }
  topic_arn = each.value
  protocol  = "email"
  endpoint  = var.notification_email
}
resource "aws_lambda_function_event_invoke_config" "failover" {
  function_name                = aws_lambda_function.failover.function_name
  maximum_event_age_in_seconds = 300
  maximum_retry_attempts       = 1
  destination_config {
    on_failure { destination = aws_sns_topic.notifications.arn }
  }
}
```

La alarma de estado usa Maximum de HealthyHostCount para detectar la ausencia de destinos saludables en todos los informes. Si faltan métricas, el estado permanece en `INSUFFICIENT_DATA` y se notifica a los operadores; no se inventa un cero ni se activa a ciegas una conmutación. Que el destino tenga más de cero destinos es una comprobación necesaria, no una prueba de capacidad suficiente ni de que la aplicación esté saludable de extremo a extremo.

### Handler y paquete

El handler comprueba la identidad exacta de alarma/origen/cuenta, la antigüedad del evento, los estados actuales de la alarma, el estado actual de los destinos y la asignación exacta de listener/TG. Conserva los demás atributos de la acción de reenvío y omite una transición ya aplicada. No deduce puertos del texto del ARN del listener. Las notificaciones no pueden retroalimentar la entrada de alarmas.

```python
# nlb/lambda/failover.py
"""SNS alarm -> checked proposal or single-listener update. No automatic failback."""
import copy
import json
import logging
import os
from datetime import datetime, timezone
from functools import lru_cache

import boto3
from botocore.config import Config

LOG = logging.getLogger(__name__)
LOG.setLevel(logging.INFO)


def timestamp(value):
    parsed = value if isinstance(value, datetime) else datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("Timezone is required")
    return parsed.astimezone(timezone.utc)


def configuration(env):
    alarms = json.loads(env["ALARM_ARNS_JSON"])
    targets = json.loads(env["TARGET_GROUP_ARNS_JSON"])
    if set(alarms) != {"blue", "green"} or set(targets) != {"blue", "green"}:
        raise ValueError("Exactly blue and green are required")
    if len(set(alarms.values())) != 2 or len(set(targets.values())) != 2:
        raise ValueError("Alarm and target-group ARNs must be distinct")
    if env["ALARM_TOPIC_ARN"] == env["NOTIFICATION_TOPIC_ARN"]:
        raise ValueError("Alarm input and notification output must be separate")
    minimum = int(env.get("MINIMUM_DESTINATION_TARGETS", "1"))
    if minimum < 1:
        raise ValueError("Destination target minimum must be positive")
    return {
        "alarms": alarms, "targets": targets,
        "listener": env["LISTENER_ARN"], "account": env["ACCOUNT_ID"],
        "input_topic": env["ALARM_TOPIC_ARN"], "output_topic": env["NOTIFICATION_TOPIC_ARN"],
        "apply": env.get("AUTOMATIC_FAILOVER", "false") == "true",
        "minimum": minimum,
    }


def healthy_count(elb, arn):
    response = elb.describe_target_health(TargetGroupArn=arn)
    return sum(t["TargetHealth"]["State"] == "healthy" for t in response["TargetHealthDescriptions"])


def listener_actions(elb, cfg):
    listeners = elb.describe_listeners(ListenerArns=[cfg["listener"]])["Listeners"]
    if len(listeners) != 1 or listeners[0]["Port"] != 443 or listeners[0]["Protocol"] != "TCP":
        raise ValueError("Expected the configured TCP/443 listener")
    actions = listeners[0]["DefaultActions"]
    if len(actions) != 1 or actions[0]["Type"] != "forward":
        raise ValueError("Expected one forward action")
    groups = actions[0].get("ForwardConfig", {}).get("TargetGroups", [])
    if len(groups) != 2 or {g["TargetGroupArn"] for g in groups} != set(cfg["targets"].values()):
        raise ValueError("Unexpected target groups: refusing to overwrite listener configuration")
    return actions


def process_record(record, cfg, clients, now):
    if not isinstance(record, dict):
        return {"status": "invalid_record"}
    if record.get("EventSource") != "aws:sns" or record.get("Sns", {}).get("TopicArn") != cfg["input_topic"]:
        return {"status": "ignored_source"}
    try:
        message = json.loads(record["Sns"]["Message"])
        if not isinstance(message, dict) or message.get("NewStateValue") != "ALARM":
            return {"status": "ignored_state"}
        source = next((color for color, arn in cfg["alarms"].items() if message.get("AlarmArn") == arn), None)
        if source is None or str(message.get("AWSAccountId")) != cfg["account"]:
            return {"status": "ignored_alarm"}
        changed = timestamp(message["StateChangeTime"])
    except (KeyError, ValueError, TypeError, AttributeError):
        return {"status": "invalid_message"}
    age = (now - changed).total_seconds()
    if age < -30 or age > 300:
        return {"status": "stale_message"}

    destination = "green" if source == "blue" else "blue"
    names = [arn.split(":alarm:", 1)[1] for arn in cfg["alarms"].values()]
    alarms = clients["cloudwatch"].describe_alarms(AlarmNames=names)["MetricAlarms"]
    states = {alarm["AlarmArn"]: alarm for alarm in alarms}
    current = states.get(cfg["alarms"][source])
    other = states.get(cfg["alarms"][destination])
    if not current or not other or current["StateValue"] != "ALARM" or other["StateValue"] != "OK":
        return {"status": "alarm_state_changed"}
    transition = timestamp(current.get("StateTransitionedTimestamp") or current.get("StateUpdatedTimestamp"))
    if abs((transition - changed).total_seconds()) > 1:
        return {"status": "stale_transition"}

    elb = clients["elbv2"]
    if healthy_count(elb, cfg["targets"][source]) != 0:
        return {"status": "source_recovered"}
    if healthy_count(elb, cfg["targets"][destination]) < cfg["minimum"]:
        return {"status": "destination_not_ready"}
    before = listener_actions(elb, cfg)
    groups = before[0]["ForwardConfig"]["TargetGroups"]
    weights = {g["TargetGroupArn"]: g.get("Weight", 1) for g in groups}
    if weights[cfg["targets"][source]] == 0 and weights[cfg["targets"][destination]] > 0:
        return {"status": "already_shifted"}
    proposed = copy.deepcopy(before)
    for group in proposed[0]["ForwardConfig"]["TargetGroups"]:
        group["Weight"] = 100 if group["TargetGroupArn"] == cfg["targets"][destination] else 0

    status = "proposal"
    if cfg["apply"]:
        # Point-in-time checks, not an atomic compare-and-swap with external writers.
        if listener_actions(elb, cfg) != before:
            return {"status": "concurrent_change"}
        if healthy_count(elb, cfg["targets"][destination]) < cfg["minimum"]:
            return {"status": "destination_changed"}
        elb.modify_listener(ListenerArn=cfg["listener"], DefaultActions=proposed)
        status = "weights_updated"
    result = {"status": status, "from": source, "to": destination}
    try:
        clients["sns"].publish(
            TopicArn=cfg["output_topic"], Subject="EKS traffic transition decision",
            Message=json.dumps(result),
        )
    except Exception:
        # Do not replay a successful listener mutation merely because notification failed.
        LOG.exception("Decision notification failed", extra={"decision_status": status})
        result["notification_failed"] = True
    LOG.info("Traffic transition decision: %s", json.dumps(result))
    return result


def handle(event, cfg, clients, now):
    if not isinstance(event, dict) or not isinstance(event.get("Records"), list):
        return [{"status": "unsupported_envelope"}]
    return [process_record(record, cfg, clients, now) for record in event["Records"]]


@lru_cache(maxsize=1)
def aws_clients():
    config = Config(connect_timeout=2, read_timeout=5, retries={"mode": "standard", "total_max_attempts": 2})
    return {name: boto3.client(name, config=config) for name in ("elbv2", "cloudwatch", "sns")}


def lambda_handler(event, context):
    return handle(event, configuration(os.environ), aws_clients(), datetime.now(timezone.utc))
```

`nlb/lambda/requirements.txt`:

```text
boto3==1.43.92
botocore==1.43.92
jmespath==1.1.0
python-dateutil==2.9.0.post0
s3transfer==0.19.2
six==1.17.0
urllib3==2.7.0
```

Compila el artefacto antes de planificar con Terraform. Las dependencias se empaquetan junto a `failover.py`, en concordancia con el punto de entrada configurado `failover.lambda_handler`:

```bash
# From nlb/, in a clean build environment with Python 3.12.
python3.12 -m pip install --target lambda/package -r lambda/requirements.txt
cp lambda/failover.py lambda/package/failover.py
python3.12 - <<'PYCODE'
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
package = Path("lambda/package")
with ZipFile("lambda/failover.zip", "w", ZIP_DEFLATED) as archive:
    for file in sorted(package.rglob("*")):
        if file.is_file() and "__pycache__" not in file.parts:
            archive.write(file, file.relative_to(package))
PYCODE
terraform init -backend-config=../environment.backend.json -backend-config=key=nlb/terraform.tfstate
terraform validate
terraform plan -var-file=environment.tfvars.json
# Review the plan; apply only after prerequisites and notification subscriptions are ready.
terraform apply -var-file=environment.tfvars.json
```

Los archivos de backend y variables deben contener los valores reales del entorno. Usa un directorio de paquete limpio para cada compilación. El hash del código de Lambda corresponde al ZIP resultante. Las dependencias de Python puro de este ejemplo son compatibles con el entorno de ejecución de Lambda y no requieren compilar una rueda nativa.

La concurrencia reservada serializa las invocaciones de esta función; no serializa Terraform ni a los escritores de API manuales. Las comprobaciones finales de estado y salud son puntuales, no una comparación e intercambio atómicos. Coordina con los demás escritores, pausa la automatización durante despliegues planificados y reconcilia los pesos resultantes en IaC antes de una aplicación posterior. Los fallos de API, límites de cuota, entrega de notificaciones y falta de disponibilidad del plano de control requieren tratamiento operativo. No hay un temporizador de recuperación automática a 80/20.

No se declara intencionadamente un verificador de estado programado de EventBridge sin su propia implementación y permisos. CloudWatch ya evalúa estas métricas de salud. Si se necesitan sondeos periódicos de la aplicación, define y prueba esa carga de trabajo independiente y su contrato de eventos.

### Transiciones manuales y graduales

Usa lo siguiente solo en una raíz NLB inicializada con el backend/caché previsto y un archivo completo de variables. Primero pausa la conmutación automática y los demás escritores. Valida los pesos numéricos, comprueba la salud de los destinos, muestra un plan completo y exige la aprobación de ese plan. No utiliza `-target` como práctica habitual, un destino predeterminado ni un bucle con temporizador sin límite.

```bash
# traffic-shift.sh
#!/usr/bin/env bash
set -euo pipefail
if (( $# != 4 )); then
  echo "Usage: $0 <initialized-nlb-root> <variables-file> <blue-weight> <green-weight>" >&2
  exit 2
fi
DOCS_NLB_ROOT="$(cd -- "$1" && pwd -P)"
DOCS_VARIABLES_FILE="$(cd -- "$(dirname -- "$2")" && pwd -P)/$(basename -- "$2")"
[[ -f "$DOCS_VARIABLES_FILE" ]] || exit 2
for value in "$3" "$4"; do
  [[ "$value" =~ ^[0-9]{1,3}$ ]] || { echo "Weights must be integers 0..999" >&2; exit 2; }
done
blue_weight=$((10#$3))
green_weight=$((10#$4))
(( blue_weight + green_weight > 0 )) || { echo "At least one weight must be positive" >&2; exit 2; }
: "${AWS_REGION:?Set the intended AWS region}"
outputs="$(terraform -chdir="$DOCS_NLB_ROOT" output -json)"
[[ "$(jq -er '.automatic_failover.value | tostring' <<<"$outputs")" == false ]] || {
  echo "Pause automatic failover and other writers before manual changes" >&2
  exit 1
}
listener="$(jq -er '.listener_arn.value' <<<"$outputs")"
minimum="$(jq -er '.minimum_destination_targets.value' <<<"$outputs")"
[[ "$minimum" =~ ^[1-9][0-9]*$ ]] || exit 1
aws elbv2 describe-listeners --region "$AWS_REGION" --listener-arns "$listener" \
  --query 'Listeners[0].DefaultActions' --output json
for color in blue green; do
  weight="$blue_weight"
  [[ "$color" == green ]] && weight="$green_weight"
  target="$(jq -er --arg color "$color" '.target_group_arns.value[$color]' <<<"$outputs")"
  count="$(aws elbv2 describe-target-health --region "$AWS_REGION" \
    --target-group-arn "$target" --output json | jq '[.TargetHealthDescriptions[] | select(.TargetHealth.State == "healthy")] | length')"
  if (( weight > 0 )) && ! jq -en --argjson count "$count" --argjson minimum "$minimum" '$count >= $minimum' >/dev/null; then
    echo "$color has insufficient healthy targets ($count < $minimum)" >&2
    exit 1
  fi
done
workdir="$(mktemp -d "${TMPDIR:-/tmp}/docs-traffic.XXXXXX")"
plan="$workdir/traffic.tfplan"
trap 'rm -f -- "$plan"; rmdir -- "$workdir"' EXIT
terraform -chdir="$DOCS_NLB_ROOT" plan -input=false -out="$plan" -var-file="$DOCS_VARIABLES_FILE" \
  -var=automatic_failover=false -var="traffic_weights={blue=$blue_weight,green=$green_weight}"
terraform -chdir="$DOCS_NLB_ROOT" show -no-color "$plan"
echo "Review the FULL plan and capacity/SLO checks. Weight zero can close existing connections."
read -r -p "Type apply to execute this reviewed plan: " confirmation
[[ "$confirmation" == apply ]] || { echo "No changes applied"; exit 0; }
terraform -chdir="$DOCS_NLB_ROOT" apply "$plan"
echo "Configuration applied. Verify new/active flows, errors, and latency before another step."
```

```bash
# One reviewed step at a time; replace paths and AWS context.
export AWS_REGION=ap-northeast-2
bash traffic-shift.sh ./nlb ./nlb/environment.tfvars.json 95 5
# Check new/active flows, errors, latency, destination capacity, and data compatibility.
bash traffic-shift.sh ./nlb ./nlb/environment.tfvars.json 50 50
# Only after the checks pass and reconnection behavior is acceptable:
bash traffic-shift.sh ./nlb ./nlb/environment.tfvars.json 0 100
```

Una llamada de API/aplicación exitosa cambia la configuración; no demuestra que todo el tráfico o las conexiones existentes se hayan desplazado. Elige los umbrales de detención/reversión de acuerdo con el SLO de la carga de trabajo, no con una regla universal de «5 % de errores / 200 % de latencia».

## Referencias

- [Listeners NLB y grupos ponderados](https://docs.aws.amazon.com/elasticloadbalancing/latest/network/load-balancer-listeners.html)
- [Grupos de seguridad de NLB](https://docs.aws.amazon.com/elasticloadbalancing/latest/network/load-balancer-security-groups.html)
- [Métricas de CloudWatch para NLB](https://docs.aws.amazon.com/elasticloadbalancing/latest/network/load-balancer-cloudwatch-metrics.html)
- [Valores de registros ponderados de Route 53](https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/resource-record-sets-values-weighted.html)
- [Formato de eventos de Lambda directa de CloudWatch](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/alarms-and-actions-Lambda.html)
- [TargetGroupBinding de LBC 3.5.0](https://github.com/kubernetes-sigs/aws-load-balancer-controller/blob/v3.5.0/docs/guide/targetgroupbinding/targetgroupbinding.md)

< [Anterior: Infraestructura de Terraform](01-infrastructure-setup.md) | [Tabla de contenido](README.md) | [Siguiente: Pipelines de CI](03-ci-pipelines.md) >
