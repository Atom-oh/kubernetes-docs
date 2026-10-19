# Amazon OpenSearch Service {#amazon-opensearch-service}

> **Última actualización**: 13 de septiembre de 2026
> **Versiones de referencia del ejemplo**: OpenSearch Service 3.5 aprovisionado; Terraform 1.15.7/proveedor de AWS 6.69.1; AWS for Fluent Bit 3.4.15 (Fluent Bit 5.0.9). Solo se realizaron comprobaciones locales de configuración; no se desplegó ningún dominio ni recopilador, ni se probaron sesiones SAML o la entrega de datos.

Amazon OpenSearch Service gestiona clústeres de búsqueda y admite determinadas versiones de OpenSearch y de Elasticsearch OSS anteriores. Este capítulo aborda un dominio en una VPC y los niveles tradicionales hot, UltraWarm y cold. Las colecciones Serverless y las opciones más recientes de almacenamiento para instancias optimizadas tienen sus propios requisitos de configuración, API y disponibilidad.

<span id="table-of-contents"></span>
<span id="opensearch-vs-elasticsearch"></span>
<span id="amazon-opensearch-service-features"></span>
<span id="key-use-cases"></span>

## Descripción general {#overview}

OpenSearch es un proyecto de búsqueda con licencia Apache-2.0. Su origen en Elasticsearch 7.10 no implica compatibilidad con todos los clientes, plugins o API actuales de Elasticsearch. Las opciones actuales de licencia del código fuente de Elastic incluyen AGPLv3 para las partes que cumplen sus condiciones, además de SSPL y Elastic License 2.0. Compruebe el componente y la distribución concretos, en lugar de dar por hecho que Elasticsearch mantiene un único modelo de licencia sin cambios.

La tabla de soporte de AWS incluye actualmente OpenSearch 3.5 entre las versiones admitidas. El ejemplo anterior con 2.11 **mantiene el soporte estándar hasta el 7 de noviembre de 2027**; que exista una versión más reciente no significa que esa versión carezca de soporte. Para un dominio existente, compruebe las rutas de actualización admitidas, los cambios incompatibles, las instantáneas y la compatibilidad de los clientes antes de solicitar una actualización.

OpenSearch Service puede utilizarse para análisis de registros, búsqueda de texto completo, agregaciones y flujos de análisis de seguridad. Habilitar un servicio o conservar registros de auditoría no satisface por sí solo un requisito de cumplimiento.

<span id="node-types"></span>

## Arquitectura {#architecture}

### Arquitectura del clúster de OpenSearch {#opensearch-cluster-architecture}

![Flujo conceptual de ingesta de un dominio aprovisionado y de almacenamiento en los niveles tradicionales hot, UltraWarm y cold.](../../.gitbook/assets/en-observability-logging-02-opensearch-0.png)

[Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-observability-logging-02-opensearch-0.html)

El diagrama es esquemático; no representa una distribución exacta de réplicas o zonas de disponibilidad ni recomienda tamaños concretos. Su etiqueta «Master» designa la función dedicada de gestión del clúster; los campos de configuración de AWS siguen utilizando `dedicated_master_*`. «Kinesis Data Firehose» es el nombre anterior de **Amazon Data Firehose**. Tanto UltraWarm como cold utilizan almacenamiento respaldado por S3; para consultar datos cold, primero debe volver a asociarlos a UltraWarm.

| Rol o nivel | Función |
|---|---|
| Nodos dedicados de gestión del clúster | Gestionan el estado del clúster, los metadatos y la asignación de shards. Tres nodos es la configuración convencional de gestores dedicados; no son réplicas de datos. |
| Nodos de datos / almacenamiento hot | Realizan la indexación y las consultas. La disponibilidad y los límites de EBS dependen de la familia de instancias seleccionada. |
| UltraWarm | Índices de solo lectura respaldados por S3, con caché y cómputo en nodos warm. Compruebe los requisitos del motor, de las instancias y de los gestores dedicados. |
| Almacenamiento cold | Almacena índices desvinculados con un ciclo de vida independiente. Vuelva a asociar los índices seleccionados a UltraWarm para consultarlos. |

Multi-AZ with Standby tiene requisitos adicionales de topología y réplicas. Habilitar la distribución entre zonas no habilita Standby ni proporciona sus garantías de disponibilidad. Revise las restricciones actuales de las instancias, incluidos VPC Encryption Controls y la compatibilidad del almacenamiento. Los tamaños originales r6g/m6g son valores de ejemplo, no resultados de una prueba de rendimiento.

Recurso complementario: [AWS Instance Benchmark](https://benchmark.aws.atomai.click/). Para determinar la capacidad del servicio, sigue siendo necesaria una prueba con una carga de trabajo representativa de OpenSearch.

### Flujo de datos {#data-flow}

![Ciclo de vida ilustrativo de índices diarios: ingesta en almacenamiento hot y transición mediante ISM a UltraWarm y almacenamiento cold.](../../.gitbook/assets/en-observability-logging-02-opensearch-1.png)

[Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-observability-logging-02-opensearch-1.html)

Las etiquetas de 7 y 30 días son ejemplos de **condiciones de antigüedad del índice**, no valores predeterminados automáticos ni una retención exacta basada en la antigüedad de cada evento. ISM se ejecuta periódicamente y la migración es asíncrona. Con índices basados en fechas, los eventos tardíos o reprocesados pueden dirigirse a un índice antiguo de solo lectura; decida cómo dirigirlos o archivarlos antes de habilitar la migración.

<span id="creation-via-aws-console"></span>

## Creación de dominios {#domain-creation}

### Requisitos previos {#prerequisites}

Prepare tres subredes privadas en distintas zonas de disponibilidad de la misma VPC, grupos de seguridad de clientes con conectividad, un rol vinculado al servicio existente y roles IAM aprobados para administradores, escritores y lectores. El ejemplo valida que los identificadores de subred sean distintos, pero no comprueba remotamente sus zonas, rutas, capacidad ni propiedad.

El perfil de Terraform utiliza **solicitudes a la API firmadas con IAM** y un rol IAM de administrador principal. Evita guardar una contraseña interna de administrador principal en el estado de Terraform. Configure las asignaciones de roles FGAC antes de enviar registros. El SSO del navegador es un perfil de acceso distinto que se explica más adelante; una política de dominio con principales IAM requiere SigV4 y no acepta automáticamente solicitudes SAML del navegador sin firmar.

### Creación mediante Terraform {#creation-via-terraform}

El ejemplo utiliza la partición comercial de AWS y la región de Seúl. Sustituya los valores de forma coherente y compruebe la disponibilidad regional. Aplicar esta configuración crea recursos; la revisión solo realizó validaciones locales.

```hcl
terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "6.69.1"
    }
  }
}

variable "region" {
  type    = string
  default = "ap-northeast-2"
}

variable "account_id" {
  type = string
  validation {
    condition     = can(regex("^[0-9]{12}$", var.account_id))
    error_message = "Use the owning AWS account ID."
  }
}

variable "vpc_id" {
  type = string
}

variable "subnet_ids" {
  type = list(string)
  validation {
    condition     = length(var.subnet_ids) == 3 && length(distinct(var.subnet_ids)) == 3
    error_message = "Provide three distinct subnet IDs, one in each intended AZ."
  }
}

variable "client_security_group_ids" {
  type = set(string)
}

variable "admin_role_arn" {
  type = string
}

variable "writer_role_arns" {
  type = set(string)
}

variable "reader_role_arns" {
  type    = set(string)
  default = []
}

provider "aws" {
  region = var.region
}

locals {
  domain_name = "logs-production"
  domain_arn  = "arn:aws:es:${var.region}:${var.account_id}:domain/${local.domain_name}"
  log_types   = toset(["INDEX_SLOW_LOGS", "SEARCH_SLOW_LOGS", "ES_APPLICATION_LOGS", "AUDIT_LOGS"])
  callers     = setunion(toset([var.admin_role_arn]), var.writer_role_arns, var.reader_role_arns)
}

resource "aws_security_group" "search" {
  name_prefix = "logs-search-"
  description = "OpenSearch HTTPS from approved client security groups"
  vpc_id      = var.vpc_id
}

resource "aws_vpc_security_group_ingress_rule" "clients" {
  for_each                     = var.client_security_group_ids
  security_group_id            = aws_security_group.search.id
  referenced_security_group_id = each.value
  from_port                    = 443
  to_port                      = 443
  ip_protocol                  = "tcp"
}

resource "aws_vpc_security_group_egress_rule" "outbound" {
  security_group_id = aws_security_group.search.id
  cidr_ipv4         = "0.0.0.0/0"
  ip_protocol       = "-1"
}

resource "aws_cloudwatch_log_group" "search" {
  for_each          = local.log_types
  name              = "/aws/opensearch/${local.domain_name}/${lower(each.value)}"
  retention_in_days = 30
}

resource "aws_cloudwatch_log_resource_policy" "search" {
  policy_name = "logs-production-opensearch"
  policy_document = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "es.amazonaws.com" }
      Action    = ["logs:CreateLogStream", "logs:PutLogEvents"]
      Resource  = [for group in aws_cloudwatch_log_group.search : "${group.arn}:*"]
      Condition = {
        StringEquals = { "aws:SourceAccount" = var.account_id }
        ArnEquals    = { "aws:SourceArn" = local.domain_arn }
      }
    }]
  })
}

resource "aws_opensearch_domain" "logs" {
  domain_name    = local.domain_name
  engine_version = "OpenSearch_3.5"

  cluster_config {
    instance_type                 = "r6g.xlarge.search"
    instance_count                = 3
    dedicated_master_enabled      = true
    dedicated_master_type         = "m6g.large.search"
    dedicated_master_count        = 3
    zone_awareness_enabled        = true
    multi_az_with_standby_enabled = false
    zone_awareness_config {
      availability_zone_count = 3
    }
    warm_enabled = true
    warm_type    = "ultrawarm1.medium.search"
    warm_count   = 2
    cold_storage_options {
      enabled = true
    }
  }

  ebs_options {
    ebs_enabled = true
    volume_type = "gp3"
    volume_size = 500
  }

  vpc_options {
    subnet_ids         = var.subnet_ids
    security_group_ids = [aws_security_group.search.id]
  }

  encrypt_at_rest {
    enabled = true
  }
  node_to_node_encryption {
    enabled = true
  }
  domain_endpoint_options {
    enforce_https       = true
    tls_security_policy = "Policy-Min-TLS-1-2-PFS-2023-10"
  }
  advanced_security_options {
    enabled                        = true
    internal_user_database_enabled = false
    master_user_options {
      master_user_arn = var.admin_role_arn
    }
  }

  access_policies = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { AWS = sort(tolist(local.callers)) }
      Action    = ["es:ESHttp*"]
      Resource  = "${local.domain_arn}/*"
    }]
  })

  dynamic "log_publishing_options" {
    for_each = aws_cloudwatch_log_group.search
    content {
      cloudwatch_log_group_arn = log_publishing_options.value.arn
      log_type                 = log_publishing_options.key
      enabled                  = true
    }
  }

  depends_on = [aws_cloudwatch_log_resource_policy.search]
}

output "domain_endpoint" {
  value = aws_opensearch_domain.logs.endpoint
}

output "dashboards_endpoint" {
  value = aws_opensearch_domain.logs.dashboard_endpoint
}
```

Los tamaños iniciales, los volúmenes EBS de 500 GiB y la retención de CloudWatch de 30 días son ejemplos. El perfil utiliza expresamente Multi-AZ **sin Standby**. En esta referencia, el acceso saliente del grupo de seguridad sigue siendo amplio; antes de utilizarla en producción, diseñe restricciones de salida para las conexiones reales admitidas.

La política de acceso al dominio permite a los roles IAM indicados realizar operaciones HTTP; **FGAC** debe restringir sus permisos sobre índices y clústeres. Los permisos IAM basados únicamente en URI no limitan los nombres de índice incluidos dentro de los cuerpos de solicitudes bulk. Asigne al rol del recopilador solo el rol de escritura previsto.

El rol vinculado al servicio de la plataforma es una dependencia de la cuenta. Reutilícelo o impórtelo en el estado de infraestructura que lo gestiona, en lugar de intentar crear el mismo rol en cada despliegue.

Los dominios OpenSearch generan instantáneas automáticas cada hora y las conservan durante 14 días, hasta un máximo de 336. El antiguo ejemplo `automated_snapshot_start_hour` corresponde a versiones mucho anteriores de Elasticsearch, no a este perfil de OpenSearch. Las instantáneas son mecanismos de recuperación; no sustituyen un plan de retención y restauración probado. El estado rojo del clúster puede impedir que se generen.

Antes de configurar el dominio para publicar en CloudWatch, debe existir la política de recursos con el alcance correspondiente. Configurar destinos para los registros de consultas lentas no habilita todos sus umbrales, y publicar registros de auditoría no configura todos los eventos auditados. Configure expresamente los ajustes del motor y de auditoría pertinentes. Las consultas y el contenido de los documentos presentes en los registros también necesitan controles de acceso y retención.

<span id="index-aliases"></span>

## Administración de índices {#index-management}

El recopilador principal siguiente escribe **índices diarios** llamados `logs-production-YYYY.MM.DD`. La plantilla, el patrón ISM y los ejemplos de consulta utilizan ese patrón. Más adelante se presenta un ejercicio independiente de rollover; mantenga separadas ambas estrategias de escritura.

Los bloques de solicitudes siguientes utilizan la sintaxis de Dev Tools de OpenSearch Dashboards. No son archivos JSON independientes ni comandos ejecutados durante la revisión. Utilice un cliente autorizado del plano de datos y el dominio previsto.

### Plantillas de índices {#index-templates}

```http
PUT _index_template/logs-template
{
  "index_patterns": [
    "logs-production-*"
  ],
  "priority": 100,
  "template": {
    "settings": {
      "number_of_shards": 3,
      "number_of_replicas": 1,
      "refresh_interval": "5s",
      "index.codec": "best_compression",
      "index.translog.durability": "request"
    },
    "mappings": {
      "dynamic": false,
      "properties": {
        "@timestamp": {
          "type": "date"
        },
        "cluster_name": {
          "type": "keyword"
        },
        "environment": {
          "type": "keyword"
        },
        "stream": {
          "type": "keyword"
        },
        "log": {
          "type": "text",
          "index": false
        },
        "kubernetes": {
          "properties": {
            "namespace_name": {
              "type": "keyword"
            },
            "pod_name": {
              "type": "keyword"
            },
            "container_name": {
              "type": "keyword"
            },
            "host": {
              "type": "keyword"
            }
          }
        },
        "app": {
          "properties": {
            "level": {
              "type": "keyword"
            },
            "message": {
              "type": "text",
              "fields": {
                "keyword": {
                  "type": "keyword",
                  "ignore_above": 256
                }
              }
            },
            "error_type": {
              "type": "keyword"
            },
            "trace_id": {
              "type": "keyword"
            },
            "span_id": {
              "type": "keyword"
            },
            "request_id": {
              "type": "keyword"
            },
            "http": {
              "properties": {
                "method": {
                  "type": "keyword"
                },
                "status_code": {
                  "type": "integer"
                },
                "path": {
                  "type": "keyword"
                },
                "response_time_ms": {
                  "type": "float"
                }
              }
            }
          }
        }
      }
    }
  }
}
```

El filtro de Kubernetes genera `kubernetes.namespace_name`, no `kubernetes.namespace`. El JSON de la aplicación se anida bajo `app` para separarlo de los metadatos del recopilador. Las aplicaciones deben emitir los campos y las unidades documentados; los ejemplos utilizan `app.level` en minúsculas y milisegundos para `app.http.response_time_ms`.

Este es un ejemplo de registro de aplicación de una sola línea, antes de que el recopilador añada metadatos:

```json
{"level":"error","message":"request failed","error_type":"upstream_timeout","http":{"method":"GET","path":"/orders","status_code":503,"response_time_ms":1250}}
```

El subcampo `message.keyword` se define expresamente como `app.message.keyword`; una definición de tipo `text` por sí sola no lo crea automáticamente. Los valores que superan su límite `ignore_above` no se indexan en ese subcampo. Para las agregaciones, considere una clasificación limitada de `error_type` en lugar de mensajes arbitrarios.

`dynamic: false` limita la creación de nuevos campos mapeados, pero **no elimina los campos desconocidos de `_source`**. El campo `log` original se almacena sin indexarse para búsquedas. Revise la duplicación, la eliminación o el enmascaramiento de datos sensibles y el acceso a los datos originales. `translog.durability: request` es una referencia más segura que aceptar, sin explicación, el compromiso de durabilidad de async/30s; ninguno de los ajustes garantiza la recuperación ante todos los fallos de almacenamiento o réplicas.

### Políticas ISM (Index State Management) {#ism-index-state-management-policies}

```http
PUT _plugins/_ism/policies/logs-lifecycle
{
  "policy": {
    "description": "Illustrative daily-index hot/warm/cold retention; confirm ownership and late-arrival handling.",
    "schema_version": 1,
    "default_state": "hot",
    "states": [
      {
        "name": "hot",
        "actions": [],
        "transitions": [
          {
            "state_name": "warm",
            "conditions": {
              "min_index_age": "7d"
            }
          }
        ]
      },
      {
        "name": "warm",
        "actions": [
          {
            "warm_migration": {}
          }
        ],
        "transitions": [
          {
            "state_name": "cold",
            "conditions": {
              "min_index_age": "30d"
            }
          }
        ]
      },
      {
        "name": "cold",
        "actions": [
          {
            "cold_migration": {
              "timestamp_field": "@timestamp"
            }
          }
        ],
        "transitions": [
          {
            "state_name": "delete",
            "conditions": {
              "min_index_age": "90d"
            }
          }
        ]
      },
      {
        "name": "delete",
        "actions": [
          {
            "cold_delete": {}
          }
        ],
        "transitions": []
      }
    ],
    "ism_template": [
      {
        "index_patterns": [
          "logs-production-*"
        ],
        "priority": 100
      }
    ]
  }
}
```

Esta política se asocia a los nuevos índices que coincidan con su patrón. Para los índices existentes, debe realizar expresamente una operación de asociación de política; examine `_plugins/_ism/explain/INDEX` y las versiones de las políticas antes de modificarlos.

Cada objeto de acción contiene una sola acción, junto con los metadatos de reintento o tiempo de espera admitidos. Las operaciones gestionadas `warm_migration`, `cold_migration` y **`cold_delete`** difieren de las operaciones ISM de instalaciones autogestionadas. Los índices cold necesitan `cold_delete`, y la migración a cold mediante ISM exige un campo explícito de marca de tiempo. No combine una migración a warm, cambios de réplicas y force merge en un único objeto de acción.

ISM suele evaluar los trabajos cada 5–8 minutos y no los ejecuta mientras el clúster esté en estado rojo. La antigüedad del índice se mide desde su creación. El ejemplo de eliminación a los 90 días es una decisión de la organización, no un requisito legal universal ni una expiración exacta de cada registro. Antes de habilitar la eliminación, verifique el tratamiento de los datos tardíos, las instantáneas y la recuperación.

### Alias de índices y rollover {#index-aliases-and-rollover}

Este ejercicio independiente utiliza el prefijo `rollover-logs-*` y un alias de escritura. No modifica la configuración de índices diarios del recopilador.

```http
PUT _index_template/rollover-logs
{
  "index_patterns": [
    "rollover-logs-*"
  ],
  "priority": 100,
  "template": {
    "settings": {
      "number_of_shards": 3,
      "number_of_replicas": 1,
      "plugins.index_state_management.rollover_alias": "rollover-logs-write"
    },
    "mappings": {
      "properties": {
        "@timestamp": {
          "type": "date"
        },
        "message": {
          "type": "text"
        }
      }
    }
  }
}

PUT _plugins/_ism/policies/rollover-logs
{
  "policy": {
    "description": "Independent rollover example; not attached to date-based collector indexes.",
    "schema_version": 1,
    "default_state": "write",
    "states": [
      {
        "name": "write",
        "actions": [
          {
            "rollover": {
              "min_index_age": "1d",
              "min_primary_shard_size": "30gb"
            }
          }
        ],
        "transitions": []
      }
    ],
    "ism_template": [
      {
        "index_patterns": [
          "rollover-logs-*"
        ],
        "priority": 100
      }
    ]
  }
}

PUT rollover-logs-000001
{
  "aliases": {
    "rollover-logs-write": {
      "is_write_index": true
    }
  }
}

POST rollover-logs-write/_doc
{
  "@timestamp": "2026-09-13T00:00:00Z",
  "message": "synthetic rollover example"
}

GET _plugins/_ism/explain/rollover-logs-000001

POST rollover-logs-write/_rollover
{
  "conditions": {
    "max_age": "1d",
    "max_size": "90gb"
  }
}
```

El rollover automático de ISM necesita la configuración del alias de rollover, un índice numerado adecuado y el alias de escritura. Un proceso que escribe en índices diarios por fecha no utilizará ese alias simplemente porque exista.

`min_primary_shard_size: 30gb` de ISM se refiere a un único shard primario. El analizador de la API REST de rollover de OpenSearch 3.5 admite `max_age`, `max_docs` y `max_size`; `max_size` mide el **almacenamiento total de los shards primarios**, sin réplicas. Por tanto, el ejemplo REST de 90 GB no representa la misma condición que un umbral de 30 GB por shard primario. Las condiciones de rollover son alternativas; no es necesario cumplir todos los umbrales a la vez.

<span id="direct-ingestion-from-fluentbit-to-opensearch"></span>
<span id="fluentbit-daemonset-using-irsa"></span>

## Ingesta de datos {#data-ingestion}

### Ingesta directa desde Fluent Bit {#direct-ingestion-from-fluent-bit}

Los seis recursos siguientes forman una configuración de referencia del recopilador para **nodos EC2 Linux** que cumplan los requisitos. Fargate utiliza el router de registros de su plataforma; Windows y otras plataformas de nodos necesitan sus propias rutas y su propio modelo de despliegue. Antes de desplegar un lector de registros del nodo, confirme las rutas del host, las excepciones de las políticas de admisión y los recursos necesarios.

Configure el nombre real del host del dominio, la región y el rol IRSA. La relación de confianza OIDC del rol debe coincidir con `system:serviceaccount:logging:fluent-bit`; autorice también su acceso IAM al plano de datos y su rol de escritura FGAC. Pod Identity solo es una alternativa si el nodo, el agente y el SDK son compatibles.

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: logging
---
apiVersion: v1
kind: ServiceAccount
metadata:
  name: fluent-bit
  namespace: logging
  annotations:
    eks.amazonaws.com/role-arn: arn:aws:iam::123456789012:role/FluentBitOpenSearchRole
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: fluent-bit-metadata
rules:
- apiGroups:
  - ''
  resources:
  - namespaces
  - pods
  verbs:
  - get
  - list
  - watch
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: fluent-bit-metadata
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: fluent-bit-metadata
subjects:
- kind: ServiceAccount
  name: fluent-bit
  namespace: logging
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: fluent-bit-config
  namespace: logging
data:
  fluent-bit.conf: |
    [SERVICE]
        Flush          5
        Log_Level      info
        HTTP_Server    Off
        storage.path   /buffers/storage
        storage.sync   normal

    [INPUT]
        Name               tail
        Tag                kube.*
        Path               /var/log/containers/*.log
        Exclude_Path       /var/log/containers/fluent-bit-*_logging_fluent-bit-*.log
        multiline.parser   docker, cri
        DB                 /buffers/tail.db
        Mem_Buf_Limit      50MB
        Skip_Long_Lines    On
        Refresh_Interval   10
        storage.type       filesystem

    [FILTER]
        Name                kubernetes
        Match               kube.*
        Kube_Tag_Prefix     kube.var.log.containers.
        Merge_Log           On
        Merge_Log_Key       app
        Keep_Log            On
        Labels              Off
        Annotations         Off
        K8S-Logging.Parser  Off
        K8S-Logging.Exclude Off

    [FILTER]
        Name    modify
        Match   kube.*
        Set     cluster_name example-eks
        Set     environment example

    [OUTPUT]
        Name                    opensearch
        Match                   kube.*
        Host                    REPLACE_WITH_DOMAIN_ENDPOINT
        Port                    443
        tls                     On
        tls.verify              On
        AWS_Auth                On
        AWS_Region              ap-northeast-2
        Suppress_Type_Name      On
        Logstash_Format         On
        Logstash_Prefix         logs-production
        Time_Key                @timestamp
        Generate_ID             On
        Retry_Limit             5
        Buffer_Size             5MB
        Compress                gzip
        storage.total_limit_size 1G
---
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: fluent-bit
  namespace: logging
spec:
  selector:
    matchLabels:
      app: fluent-bit
  template:
    metadata:
      labels:
        app: fluent-bit
    spec:
      serviceAccountName: fluent-bit
      nodeSelector:
        kubernetes.io/os: linux
      tolerations:
      - operator: Exists
        effect: NoSchedule
      containers:
      - name: fluent-bit
        image: public.ecr.aws/aws-observability/aws-for-fluent-bit:3.4.15@sha256:88e1b56cedb230486afeca6eeb26c5f6bd59c48879d0054d1674d5a58838c607
        args:
        - -c
        - /fluent-bit/custom/fluent-bit.conf
        securityContext:
          runAsUser: 0
          allowPrivilegeEscalation: false
          readOnlyRootFilesystem: true
          capabilities:
            drop:
            - ALL
          seccompProfile:
            type: RuntimeDefault
        resources:
          requests:
            cpu: 100m
            memory: 128Mi
          limits:
            memory: 512Mi
        volumeMounts:
        - name: logs
          mountPath: /var/log
          readOnly: true
        - name: buffers
          mountPath: /buffers
        - name: config
          mountPath: /fluent-bit/custom
          readOnly: true
        - name: tmp
          mountPath: /tmp
        command:
        - /fluent-bit/bin/fluent-bit
      volumes:
      - name: logs
        hostPath:
          path: /var/log
          type: Directory
      - name: buffers
        hostPath:
          path: /var/lib/fluent-bit-opensearch
          type: DirectoryOrCreate
      - name: config
        configMap:
          name: fluent-bit-config
      - name: tmp
        emptyDir: {}
```

El índice de la imagen está fijado y se comprobaron sus metadatos para Linux amd64/arm64. El CMD predeterminado de esta imagen ejecuta un script de entrada; el ejemplo invoca expresamente `/fluent-bit/bin/fluent-bit` con la **salida nativa de OpenSearch**. No carga los plugins de salida antiguos escritos en Go ni prueba la imagen en ejecución.

Relaciones de configuración importantes:

- `multiline.parser docker, cri` procesa los formatos admitidos de registros de contenedores; después, el filtro de Kubernetes incorpora el JSON de la aplicación bajo `app`.
- El montaje de solo lectura de `/var/log` sirve como entrada de registros. La base de datos de Tail y los búferes del sistema de archivos utilizan otra ruta del nodo con permisos de escritura. Solo sobreviven a un reinicio del pod mientras ese nodo y esa ruta sigan existiendo; no constituyen almacenamiento duradero entre nodos.
- El RBAC de metadatos se limita a leer pods y espacios de nombres. El agente también lee los registros del nodo, por lo que debe proteger su espacio de nombres, su rol y su configuración.
- En este ejemplo, las anotaciones de las aplicaciones no pueden modificar de forma inadvertida el análisis ni excluir registros. Los valores de clúster y entorno generados por el recopilador se configuran expresamente. Excluya de este flujo los registros del propio recopilador para reducir los bucles de retroalimentación.
- `Suppress_Type_Name On` es necesario para la API sin tipos de OpenSearch 2.x/3.x. `Type _doc` no es un sustituto compatible.
- `Logstash_Format On` crea nombres de índice basados en fechas y el campo `@timestamp`. No escribe en el alias opcional de rollover.
- Los reintentos, `Generate_ID`, los búferes de memoria y el límite de almacenamiento de la salida no garantizan una entrega exactamente una vez ni sin pérdidas. Pruebe los errores parciales de solicitudes bulk, las líneas demasiado grandes, las posiciones de lectura tras reinicios, el límite de reintentos, la presión sobre el disco y los registros tardíos. El límite de la salida no limita todo el uso de disco del nodo.

El registro original conservado puede contener datos que también figuren bajo `app`. Elimine o enmascare el contenido prohibido antes de almacenarlo y supervise los registros rechazados. No mantenga habilitada la trazabilidad de los cuerpos de solicitudes como ajuste permanente de diagnóstico.

<span id="ingestion-via-kinesis-data-firehose"></span>

### Ingesta mediante Amazon Data Firehose {#ingestion-via-amazon-data-firehose}

Data Firehose ofrece una ruta alternativa de entrega gestionada con controles de almacenamiento en búfer, reintento y copia de seguridad. No es automáticamente la opción más barata o sencilla para todas las cargas de trabajo. Su recurso de Terraform sigue llamándose `aws_kinesis_firehose_delivery_stream`.

Este archivo opcional de recursos utiliza el dominio anterior y valores ya existentes y aprobados para el rol de entrega, las subredes, los grupos de seguridad y el bucket privado de copia de seguridad:

```hcl
variable "firehose_role_arn" {
  type = string
}

variable "firehose_subnet_ids" {
  type = list(string)
}

variable "firehose_security_group_ids" {
  type = list(string)
}

variable "backup_bucket_arn" {
  type = string
}

resource "aws_cloudwatch_log_group" "firehose" {
  name              = "/aws/kinesisfirehose/logs-to-opensearch"
  retention_in_days = 30
}

resource "aws_cloudwatch_log_stream" "firehose" {
  name           = "opensearch-delivery"
  log_group_name = aws_cloudwatch_log_group.firehose.name
}

resource "aws_kinesis_firehose_delivery_stream" "logs" {
  name        = "logs-to-opensearch"
  destination = "opensearch"

  opensearch_configuration {
    domain_arn            = aws_opensearch_domain.logs.arn
    role_arn              = var.firehose_role_arn
    index_name            = "logs-production-firehose"
    index_rotation_period = "OneDay"
    buffering_interval    = 60
    buffering_size        = 5
    retry_duration        = 300
    s3_backup_mode        = "FailedDocumentsOnly"

    vpc_config {
      subnet_ids         = var.firehose_subnet_ids
      security_group_ids = var.firehose_security_group_ids
      role_arn           = var.firehose_role_arn
    }

    cloudwatch_logging_options {
      enabled         = true
      log_group_name  = aws_cloudwatch_log_group.firehose.name
      log_stream_name = aws_cloudwatch_log_stream.firehose.name
    }

    s3_configuration {
      role_arn           = var.firehose_role_arn
      bucket_arn         = var.backup_bucket_arn
      prefix             = "opensearch-failed/"
      buffering_size     = 10
      buffering_interval = 400
      compression_format = "GZIP"
    }
  }
}
```

El rol de entrega necesita los permisos correspondientes de OpenSearch/FGAC, S3, CloudWatch y VPC/ENI, además de los permisos KMS necesarios. Su relación de confianza y los permisos `iam:PassRole` de quien despliega son requisitos independientes. Incluya el rol de entrega entre los clientes autorizados del dominio y en la asignación del rol de escritura; permita sus conexiones desde la VPC al puerto 443.

`FailedDocumentsOnly` selecciona el modo de copia de seguridad; utilizar un prefijo de S3 llamado `failed/` no lo configura por sí solo. Pruebe los fallos y el reprocesamiento desde el bucket privado de copia de seguridad. Los registros de Firehose necesitan un esquema compatible con el mapping del índice, incluidas las marcas de tiempo. El servicio no crea automáticamente la estructura de metadatos de Kubernetes y de aplicación mostrada aquí.

<span id="dashboard-access-setup"></span>
<span id="create-index-pattern"></span>
<span id="visualization-creation"></span>

## OpenSearch Dashboards {#opensearch-dashboards}

### Acceso y patrones de índices {#access-and-index-patterns}

Utilice conectividad VPC aprobada y un método de autenticación compatible con la política de acceso al dominio. Un túnel SSH por sí solo no conserva el nombre original del host TLS, las redirecciones SSO ni la firma SigV4. No deshabilite la verificación de certificados para hacer que `https://localhost:9200` parezca funcionar. Un ALB no constituye una solución completa de integración nativa del dominio y Dashboards.

Después de configurar el acceso autenticado, cree una vista de datos o patrón de índices para `logs-production-*` y seleccione `@timestamp`. Los nombres de los menús varían según la versión de Dashboards y la experiencia habilitada.

### Ejemplos de consultas de búsqueda {#search-query-examples}

```http
GET logs-production-*/_search
{
  "query": {
    "bool": {
      "filter": [
        {
          "term": {
            "app.level": "error"
          }
        },
        {
          "range": {
            "@timestamp": {
              "gte": "now-1h"
            }
          }
        },
        {
          "term": {
            "kubernetes.namespace_name": "production"
          }
        }
      ]
    }
  },
  "sort": [
    {
      "@timestamp": {
        "order": "desc"
      }
    }
  ],
  "size": 100
}

GET logs-production-*/_search
{
  "size": 0,
  "query": {
    "bool": {
      "filter": [
        {
          "term": {
            "app.level": "error"
          }
        },
        {
          "range": {
            "@timestamp": {
              "gte": "now-24h"
            }
          }
        }
      ]
    }
  },
  "aggs": {
    "by_namespace": {
      "terms": {
        "field": "kubernetes.namespace_name",
        "size": 20
      },
      "aggs": {
        "by_type": {
          "terms": {
            "field": "app.error_type",
            "size": 10
          }
        }
      }
    }
  }
}

GET logs-production-*/_search
{
  "size": 0,
  "query": {
    "bool": {
      "filter": [
        {
          "exists": {
            "field": "app.http.response_time_ms"
          }
        },
        {
          "range": {
            "@timestamp": {
              "gte": "now-1h"
            }
          }
        }
      ]
    }
  },
  "aggs": {
    "response_time_percentiles": {
      "percentiles": {
        "field": "app.http.response_time_ms",
        "percents": [
          50,
          75,
          90,
          95,
          99
        ]
      }
    }
  }
}
```

Estos ejemplos utilizan el contexto de filtro para condiciones exactas sobre palabras clave y tiempo. La segunda consulta filtra los errores antes de agregar los espacios de nombres. La agregación terms devuelve un conjunto seleccionado de los N resultados principales y puede producir aproximaciones distribuidas u omitir grupos; no proporciona un recuento completo de todos los espacios de nombres. Los percentiles son aproximados y utilizan el campo mapeado en milisegundos.

Para las visualizaciones, seleccione `app.level`, un histograma temporal sobre `@timestamp` o los campos expresamente mapeados `app.message.keyword`/`app.error_type`. Mencionar un nombre de campo en un dashboard no crea su mapping.

<span id="fine-grained-access-control-fgac"></span>
<span id="document-level-security-dls"></span>
<span id="field-level-security-fls"></span>

## Configuración de seguridad {#security-configuration}

### Control de acceso granular {#fine-grained-access-control}

El acceso de red, la política de recursos del dominio y FGAC son capas independientes. La política de Terraform con principales IAM requiere SigV4. Ni una regla de grupo de seguridad ni una solicitud IAM aceptada conceden automáticamente acceso a los índices.

Un administrador puede definir un rol de escritura para el recopilador y un rol de lectura restringido por espacio de nombres:

```http
PUT _plugins/_security/api/roles/logs-writer
{
  "cluster_permissions": [
    "cluster_composite_ops"
  ],
  "index_permissions": [
    {
      "index_patterns": [
        "logs-production-*"
      ],
      "allowed_actions": [
        "create_index",
        "write"
      ]
    }
  ]
}

PUT _plugins/_security/api/rolesmapping/logs-writer
{
  "backend_roles": [
    "arn:aws:iam::123456789012:role/FluentBitOpenSearchRole"
  ]
}

PUT _plugins/_security/api/roles/team-a-logs
{
  "cluster_permissions": [
    "cluster_composite_ops_ro"
  ],
  "index_permissions": [
    {
      "index_patterns": [
        "logs-production-*"
      ],
      "dls": "{\"term\":{\"kubernetes.namespace_name\":\"team-a\"}}",
      "allowed_actions": [
        "read"
      ]
    }
  ]
}

PUT _plugins/_security/api/rolesmapping/team-a-logs
{
  "backend_roles": [
    "arn:aws:iam::123456789012:role/TeamAReaderRole"
  ]
}
```

Sustituya los ARN de los roles por los de las identidades aprobadas. Si utiliza Firehose, la asignación de escritura también debe incluir su rol de entrega. No conceda `cluster_all` ni el rol de administrador principal a los lectores habituales. Las asignaciones de backend roles IAM y los nombres de usuario internos o de SAML son mecanismos de identidad distintos.

### Seguridad a nivel de documento y seguridad a nivel de campo {#document-level-security-and-field-level-security}

DLS filtra documentos a partir de campos almacenados. En este ejemplo, los metadatos del espacio de nombres deben proceder del recopilador de confianza; las cadenas proporcionadas por la aplicación no demuestran la identidad del tenant.

Para un lector con acceso más restringido, el rol **combinado** siguiente mantiene la restricción por espacio de nombres y solo incluye determinados campos de respuesta:

```http
PUT _plugins/_security/api/roles/team-a-limited
{
  "cluster_permissions": [
    "cluster_composite_ops_ro"
  ],
  "index_permissions": [
    {
      "index_patterns": [
        "logs-production-*"
      ],
      "fls": [
        "@timestamp",
        "kubernetes.namespace_name",
        "app.level",
        "app.message"
      ],
      "allowed_actions": [
        "read"
      ],
      "dls": "{\"term\":{\"kubernetes.namespace_name\":\"team-a\"}}"
    }
  ]
}
```

Utilice la asignación de rol prevista, en lugar de añadir un rol restringido a una identidad que ya tenga un acceso más amplio. Evalúe el conjunto completo de roles efectivos. El campo `log` original se excluye expresamente de esta lista de campos permitidos porque puede duplicar campos JSON que, de otro modo, quedarían ocultos.

FLS controla los campos devueltos, no el contenido de una cadena de mensaje permitida. No elimina información de `_source`, de las instantáneas ni de los archivos de registros. Pruebe el acceso mediante search, get, multi-search y agregaciones, e impida desde el principio que se registren datos prohibidos.

### Configuración de autenticación SAML {#saml-authentication-setup}

En OpenSearch Service gestionado, SAML se configura mediante la **API de configuración de dominios de AWS**, no cargando un archivo `opensearch-security/config.yml` de una instalación autogestionada.

El script auxiliar local siguiente serializa el XML aprobado del IdP sin tener que escapar su contenido manualmente. Sustituya el grupo de administración de ejemplo y la clave del atributo de rol por los de la configuración del IdP que haya revisado:

```python
from pathlib import Path
import json
import xml.etree.ElementTree as ET

metadata = Path("idp-metadata.xml").read_text(encoding="utf-8")
root = ET.fromstring(metadata)
if root.tag.rsplit("}", 1)[-1] != "EntityDescriptor" or not root.get("entityID"):
    raise ValueError("Provide approved metadata for one IdP EntityDescriptor")
options = {
    "SAMLOptions": {
        "Enabled": True,
        "Idp": {"EntityId": root.get("entityID"), "MetadataContent": metadata},
        "MasterBackendRole": "opensearch-admin",
        "RolesKey": "Role",
        "SessionTimeoutMinutes": 60,
    }
}
Path("advanced-security-saml.json").write_text(json.dumps(options, indent=2) + "\n")
```

```bash
aws opensearch update-domain-config \
  --domain-name logs-production --region ap-northeast-2 \
  --advanced-security-options file://advanced-security-saml.json
```

Este es un ejemplo del cuerpo de una solicitud, no un despliegue SSO completo. Valide la confianza en los metadatos, el identificador de entidad, los certificados, las URL de ACS y Dashboards, y las asignaciones. El tráfico SAML del navegador necesita una política de acceso al dominio compatible; habilitar `SAMLOptions` no convierte ese tráfico en SigV4 para la política anterior, que solo admite IAM. Siga un único perfil de autenticación coherente y pruebe la recuperación del acceso administrativo antes de modificar un dominio existente.

<span id="storage-tiering"></span>
<span id="cost-comparison-based-on-100gb-day"></span>
<span id="index-optimization"></span>
<span id="reserved-instances"></span>

## Optimización de costes {#cost-optimization}

### Ajustes de almacenamiento e índices {#storage-and-index-settings}

Calcule el coste de la región elegida, las familias y cantidades de nodos, las réplicas, EBS, el cómputo y almacenamiento de nodos warm, el almacenamiento cold y las rutas de transferencia e ingesta de datos. Los antiguos totales en dólares para 100 GB/día y los porcentajes fijos de ahorro no incluían suficientes supuestos para reproducirlos; no son un presupuesto actual ni una comparación basada en mediciones.

La compresión de índices, el intervalo de actualización, la cantidad de shards y los mappings de campos implican compromisos entre almacenamiento y CPU, actualización de los resultados de búsqueda, capacidad de consulta y coste de recuperación. Defina las opciones estáticas, como `index.codec`, en la plantilla de creación. No envíe indiscriminadamente cambios de ajustes estáticos a todos los índices abiertos de producción. Eliminar las posiciones del texto o deshabilitar campos puede impedir que determinadas consultas funcionen.

El ahorro de Reserved Instances depende del uso que cumpla los requisitos, la región, el plazo y la modalidad de pago. Planificar a un año no justifica por sí solo una compra, y un descuento en los nodos no elimina los cargos de almacenamiento y entrega. Utilice precios actuales y demanda medida, en lugar de las antiguas cifras fijas de 21/24/36%.

<span id="inverted-index-inefficiency"></span>
<span id="aggregation-query-performance-degradation"></span>
<span id="scaling-cost-issues"></span>
<span id="clickhouse-migration-decision-criteria"></span>

## Limitaciones en entornos de registros a gran escala {#limitations-in-large-scale-log-environments}

OpenSearch combina índices invertidos con **doc values almacenados por columnas** para muchas agregaciones y ordenaciones. Una agregación no requiere siempre volver a leer cada documento `_source` completo. Los mappings, la selectividad, los shards, las cachés, la distribución de segmentos y el trabajo concurrente influyen en el rendimiento.

Las cifras originales de latencia y compresión de OpenSearch y ClickHouse no especificaban hardware, versiones, datos ni consultas que permitieran reproducirlas. No las convierta en un umbral universal de migración de 100 GB ni afirme que el 90% de las consultas de todas las organizaciones siguen un único patrón.

Compare consultas representativas de texto completo, filtros, agregaciones e investigación con los mismos datos y los mismos requisitos de retención, durabilidad y concurrencia. Evalúe el coste de ingesta y carga de datos históricos, la evolución de esquemas, los permisos, los dashboards, los conocimientos operativos y la reversión. Una prueba de escritura dual necesita conciliación de datos y controles de costes; un calendario fijo de dos semanas o dos meses no garantiza el resultado.

<span id="feature-comparison"></span>
<span id="recommendations-by-use-case"></span>
<span id="migration-considerations"></span>

## Comparación con Loki {#comparison-with-loki}

| Aspecto | OpenSearch | Loki |
|---|---|---|
| Modelo de indexación y consulta | Campos mapeados, índices invertidos y doc values; Query DSL y funciones SQL/PPL admitidas | Índice de etiquetas de flujos, lectura de chunks y procesamiento y métricas con LogQL |
| Búsqueda de texto | Analizadores, relevancia y consultas de texto completo | Filtrado y búsqueda de texto en los flujos e intervalos temporales seleccionados |
| Control de acceso | Red, IAM, FGAC y controles configurados de documentos y campos | Gateway con autenticación, autorización de tenants y controles de políticas y operación |
| Costes y operación | Dependen del modelo aprovisionado o gestionado y de la carga de trabajo | Dependen del modo de despliegue, los flujos, el almacenamiento de objetos, las cachés y las consultas |
| Migración | Reconstruir mappings y consultas; validar permisos y exactitud de los datos | Rediseñar etiquetas, metadatos y consultas; validar permisos y exactitud de los datos |

Ninguno de los productos garantiza por sí solo el cumplimiento ni es automáticamente la opción más barata o sencilla de operar. Loki también admite búsquedas de texto y métricas derivadas. Una migración cambia la semántica y las capacidades; no se ajusta a una regla fija de costes de 3–5× o ahorros del 60–80%.

## Validación y referencias {#validation-and-references}

Las comprobaciones locales abarcan la configuración de recursos de Terraform y los contratos publicados de datos y configuración. No demuestran la autorización real en AWS, la capacidad de los SKU admitidos en una región, la entrega del recopilador, las transiciones o eliminaciones de ISM, la autenticación SAML ni el rendimiento de las consultas. Los metadatos del índice y la configuración de la imagen se inspeccionaron sin descargar sus capas ejecutables ni ejecutar un contenedor.

- [Soporte de servicio/versión](https://docs.aws.amazon.com/opensearch-service/latest/developerguide/what-is.html)
- [Tipos de instancia admitidos](https://docs.aws.amazon.com/opensearch-service/latest/developerguide/supported-instance-types.html) y [Multi-AZ](https://docs.aws.amazon.com/opensearch-service/latest/developerguide/managedomains-multiaz.html)
- [Acceso VPC](https://docs.aws.amazon.com/opensearch-service/latest/developerguide/vpc.html), [políticas de acceso](https://docs.aws.amazon.com/opensearch-service/latest/developerguide/ac.html) y [FGAC](https://docs.aws.amazon.com/opensearch-service/latest/developerguide/fgac.html)
- [UltraWarm](https://docs.aws.amazon.com/opensearch-service/latest/developerguide/ultrawarm.html), [almacenamiento cold](https://docs.aws.amazon.com/opensearch-service/latest/developerguide/cold-storage.html), [ISM administrado](https://docs.aws.amazon.com/opensearch-service/latest/developerguide/ism.html) y [referencia de políticas ISM](https://docs.opensearch.org/latest/im-plugin/ism/policies/)
- [API de rollover](https://docs.opensearch.org/latest/api-reference/index-apis/rollover/) y [valores de documento](https://docs.opensearch.org/latest/field-types/mapping-parameters/doc-values/)
- [Instantáneas](https://docs.aws.amazon.com/opensearch-service/latest/developerguide/managedomains-snapshots.html), [Registros de CloudWatch](https://docs.aws.amazon.com/opensearch-service/latest/developerguide/createdomain-configure-slow-logs.html) y [SAML](https://docs.aws.amazon.com/opensearch-service/latest/developerguide/saml.html)
- [Historial de versiones de AWS for Fluent Bit](https://github.com/aws/aws-for-fluent-bit/blob/mainline/CHANGELOG.md) y [configuración de salida OpenSearch](https://raw.githubusercontent.com/fluent/fluent-bit-docs/master/pipeline/outputs/opensearch.md)
- [Configuración de destino de Data Firehose](https://docs.aws.amazon.com/firehose/latest/dev/create-destination.html)
- [Precios actuales del servicio](https://aws.amazon.com/opensearch-service/pricing/)
- [Preguntas frecuentes sobre licencias de Elastic](https://www.elastic.co/pricing/faq/licensing)

## Cuestionario {#quiz}

Repase estas distinciones con el [cuestionario de OpenSearch](../../quizzes/observability/logging/02-opensearch-quiz.md).
