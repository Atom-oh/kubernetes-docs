# Cuestionario de VPC Lattice

Este cuestionario evalúa tu comprensión de Amazon VPC Lattice.

## Preguntas de opción múltiple

1. ¿Cuál es el propósito principal de Amazon VPC Lattice?
   - A) Gestionar el tráfico externo desde Internet hacia los recursos de AWS
   - B) Comunicación interna entre servicios en diferentes VPC y cuentas
   - C) Replicación de datos entre regiones de AWS
   - D) Balanceo de carga global basado en DNS

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Comunicación interna entre servicios en diferentes VPC y cuentas**

**Explicación:**
VPC Lattice es un servicio de redes de aplicaciones de AWS cuyo propósito principal es conectar y gestionar de forma segura servicios en múltiples VPC y cuentas de AWS. Proporciona descubrimiento de servicios, enrutamiento de tráfico, autenticación y autorización dentro de un límite lógico llamado Service Network. La gestión del tráfico externo se realiza mediante API Gateway o ALB, y la replicación entre regiones se realiza mediante servicios como S3 Cross-Region Replication.
</details>

2. ¿Cuál afirmación es correcta sobre el Service Network de VPC Lattice?
   - A) Una capa que conecta equipos de red físicos
   - B) Un límite lógico que agrupa servicios y gestiona su comunicación
   - C) Una tabla de enrutamiento que conecta subnets dentro de una VPC
   - D) Un servicio de reemplazo para Internet Gateway

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Un límite lógico que agrupa servicios y gestiona su comunicación**

**Explicación:**
Service Network es un componente central de VPC Lattice que agrupa lógicamente múltiples servicios. Cuando asocias una VPC con un Service Network, los recursos de esa VPC pueden comunicarse con los servicios de la red. Se pueden conectar varias VPC (incluidas las de diferentes cuentas) a un único Service Network, y las políticas de autenticación y los controles de acceso para cada servicio se pueden gestionar de forma centralizada.
</details>

3. ¿Cuál es la diferencia entre VPC Lattice y AWS App Mesh?
   - A) VPC Lattice requiere proxies sidecar, pero App Mesh no
   - B) App Mesh se basa en proxies sidecar, mientras que VPC Lattice no requiere sidecars
   - C) VPC Lattice solo admite TCP y App Mesh solo admite HTTP
   - D) Ambos servicios utilizan la misma arquitectura

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) App Mesh se basa en proxies sidecar, mientras que VPC Lattice no requiere sidecars**

**Explicación:**
AWS App Mesh es un service mesh que inserta proxies sidecar de Envoy en cada Pod de servicio para controlar el tráfico. Por otro lado, VPC Lattice es un servicio de AWS completamente administrado que proporciona comunicación entre servicios, enrutamiento y autenticación sin proxies sidecar. Esto hace que VPC Lattice tenga una menor complejidad operativa y una menor sobrecarga de recursos, aunque algunas de las capacidades de control de tráfico detallado que ofrece App Mesh pueden ser limitadas.
</details>

4. ¿Qué API de Kubernetes se utiliza al integrar EKS con VPC Lattice?
   - A) Ingress API
   - B) Service API
   - C) Gateway API
   - D) NetworkPolicy API

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: C) Gateway API**

**Explicación:**
AWS Gateway API Controller convierte recursos de Kubernetes Gateway API (GatewayClass, Gateway, HTTPRoute, etc.) en recursos de VPC Lattice. Gateway API es la especificación de ingress de próxima generación para Kubernetes, y proporciona más capacidades y extensibilidad que Ingress. Al especificar el controlador amazon-vpc-lattice con GatewayClass y crear Gateway y HTTPRoute, el controlador crea automáticamente VPC Lattice Services y Target Groups.
</details>

5. ¿Cuál es el formato correcto de nombre DNS para los servicios de VPC Lattice?
   - A) service-name.region.amazonaws.com
   - B) service-name.vpc-lattice-svcs.region.on.aws
   - C) service-name.internal.aws
   - D) service-name.lattice.region.aws

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) service-name.vpc-lattice-svcs.region.on.aws**

**Explicación:**
A los servicios de VPC Lattice se les asignan automáticamente nombres DNS. El formato es `<service-name>.<service-network-id>.vpc-lattice-svcs.<region>.on.aws`. Este nombre DNS se puede resolver desde todas las VPC conectadas al Service Network. Los clientes acceden a los servicios mediante este nombre DNS, y VPC Lattice realiza internamente el enrutamiento hacia los targets adecuados. Para utilizar dominios personalizados, puedes configurar registros CNAME o Alias en Route 53, etc.
</details>

6. ¿Qué métodos de autenticación admite VPC Lattice?
   - A) Solo API Key
   - B) Solo OAuth 2.0
   - C) AWS IAM o sin autenticación
   - D) Solo SAML

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: C) AWS IAM o sin autenticación**

**Explicación:**
VPC Lattice admite dos modos de autenticación. En el modo AWS_IAM, las solicitudes requieren firmas SigV4 (Signature Version 4), y el acceso se controla mediante políticas de IAM y políticas de recursos. En el modo NONE, se permiten todas las solicitudes sin autenticación. El uso de autenticación de IAM permite un control detallado sobre qué roles/usuarios de IAM pueden acceder a qué rutas de qué servicios.
</details>

7. ¿Cuál NO es un tipo de target admitido en los Target Groups de VPC Lattice?
   - A) Instancias EC2
   - B) Pods de EKS (tipo IP)
   - C) Funciones Lambda
   - D) Bases de datos RDS

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: D) Bases de datos RDS**

**Explicación:**
Los Target Groups de VPC Lattice admiten instancias EC2, direcciones IP (incluidos los Pods de EKS), funciones Lambda y ALB como targets. Las bases de datos RDS no pueden ser targets de VPC Lattice porque utilizan protocolos de bases de datos en lugar de HTTP/HTTPS. Para los Pods de EKS, se utilizan Target Groups de tipo IP, y AWS Gateway API Controller registra/anula automáticamente el registro de las IP de los Pods.
</details>

8. ¿Cuál es el principal caso de uso del enrutamiento ponderado en VPC Lattice?
   - A) Solo balanceo de carga
   - B) Despliegues canary y despliegues blue-green
   - C) Enrutamiento basado en la ubicación geográfica
   - D) Sesiones persistentes

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Despliegues canary y despliegues blue-green**

**Explicación:**
El enrutamiento ponderado distribuye el tráfico proporcionalmente entre varios Target Groups. En los despliegues canary, el 10 % del tráfico se envía a la nueva versión para validación y luego se incrementa gradualmente. En los despliegues blue-green, el 100 % se cambia de blue a green de una vez. Ejemplo: configurar `service-v1: weight 90, service-v2: weight 10` envía solo el 10 % del tráfico a v2. Si se detectan problemas, los pesos se pueden ajustar para realizar un rollback.
</details>

## Preguntas de respuesta corta

9. Explica cómo compartir un Service Network de VPC Lattice entre cuentas.

<details>

<summary>Mostrar respuesta</summary>

**Respuesta:**
Utiliza AWS Resource Access Manager (RAM) para compartir el Service Network con otras cuentas u organizaciones de AWS.

**Explicación:**
Proceso de uso compartido entre cuentas:
1. **Cuenta propietaria**: Crea un recurso compartido para el Service Network en RAM
   ```bash
   aws ram create-resource-share \
     --name my-service-network-share \
     --resource-arns arn:aws:vpc-lattice:region:account:servicenetwork/sn-xxx \
     --principals 123456789012  # Target account ID
   ```
2. **Cuenta de destino**: Acepta la invitación de RAM
3. **Cuenta de destino**: Asocia su VPC con el Service Network compartido
4. Después de eso, los servicios de la cuenta de destino también pueden registrarse en el Service Network

También es posible compartir automáticamente con toda la organización cuando se utiliza Organizations.
</details>

10. Explica por qué es importante la configuración de Health Check en VPC Lattice.

<details>

<summary>Mostrar respuesta</summary>

**Respuesta:**
Los Health Checks excluyen automáticamente los targets no saludables del enrutamiento de tráfico para garantizar la disponibilidad del servicio.

**Explicación:**
Cómo funcionan los Health Checks de VPC Lattice:
1. **Comprobaciones periódicas**: Se envían solicitudes a los endpoints de Health Check de los targets en los intervalos configurados (por ejemplo, 30 segundos)
2. **Determinación basada en umbrales**: El estado se determina mediante recuentos de éxitos/fallos consecutivos (healthyThresholdCount/unhealthyThresholdCount)
3. **Exclusión/recuperación automática**: Los targets no saludables se excluyen del tráfico y se restauran automáticamente cuando se recuperan
4. **Ejemplo de configuración**:
   ```yaml
   healthCheck:
     enabled: true
     protocol: HTTP
     path: /health
     healthCheckIntervalSeconds: 30
     healthyThresholdCount: 5
     unhealthyThresholdCount: 2
     matcher:
       httpCode: "200-299"
   ```
Una configuración adecuada de Health Check evita el tiempo de inactividad durante las actualizaciones rolling y protege la experiencia del usuario al evitar solicitudes a targets con fallos.
</details>

11. Explica las diferencias entre VPC Lattice y Transit Gateway.

<details>

<summary>Mostrar respuesta</summary>

**Respuesta:**
Transit Gateway proporciona enrutamiento IP entre VPC en la capa de red (L3), mientras que VPC Lattice proporciona comunicación basada en servicios en la capa de aplicación (L7).

**Explicación:**
Diferencias clave:

| Aspecto | Transit Gateway | VPC Lattice |
|--------|-----------------|-------------|
| Nivel de abstracción | Red (basada en IP) | Servicio (basado en nombres) |
| Enrutamiento | Tablas de enrutamiento IP | Basado en rutas/headers de HTTP |
| Protocolos | Todo el tráfico IP | HTTP/HTTPS/gRPC |
| Autenticación | Security Groups, NACL | AWS IAM, políticas de recursos |
| Visibilidad | Logs de flujo de red | Métricas/logs a nivel de aplicación |

Transit Gateway se utiliza cuando se necesita toda la comunicación IP entre VPC, mientras que VPC Lattice es adecuado para la comunicación basada en HTTP entre microservicios. Ambos servicios pueden utilizarse juntos.
</details>

12. Explica el rol de Auth Policy en VPC Lattice y los niveles en los que se puede aplicar.

<details>

<summary>Mostrar respuesta</summary>

**Respuesta:**
Auth Policy define el control de acceso basado en IAM y se aplica tanto en el nivel de Service Network como en el nivel de Service individual.

**Explicación:**
Niveles de aplicación de Auth Policy:
1. **Nivel de Service Network**: Política predeterminada aplicada a toda la red
   - Controla qué principales de IAM pueden conectarse a la red
2. **Nivel de Service**: Política detallada aplicada a servicios individuales
   - Controla qué principales pueden acceder a qué rutas de un servicio específico

Ejemplo de política:
```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {
      "AWS": "arn:aws:iam::123456789012:role/MyAppRole"
    },
    "Action": "vpc-lattice-svcs:Invoke",
    "Resource": "*",
    "Condition": {
      "StringEquals": {
        "vpc-lattice-svcs:RequestPath": "/api/*"
      }
    }
  }]
}
```
Esta política restringe MyAppRole para que solo acceda a la ruta /api/*.
</details>

## Preguntas prácticas

13. Escribe la política de IAM y la configuración de IRSA para instalar AWS Gateway API Controller en EKS.

<details>

<summary>Mostrar respuesta</summary>

**Respuesta:**
```bash
# 1. Create IAM policy for VPC Lattice permissions
cat <<EOF > vpc-lattice-controller-policy.json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "vpc-lattice:*",
        "iam:CreateServiceLinkedRole",
        "ec2:DescribeVpcs",
        "ec2:DescribeSubnets",
        "ec2:DescribeSecurityGroups",
        "ec2:DescribeAvailabilityZones"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogDelivery",
        "logs:GetLogDelivery",
        "logs:UpdateLogDelivery",
        "logs:DeleteLogDelivery",
        "logs:ListLogDeliveries"
      ],
      "Resource": "*"
    }
  ]
}
EOF

aws iam create-policy \
  --policy-name VPCLatticeControllerPolicy \
  --policy-document file://vpc-lattice-controller-policy.json

# 2. Create service account using IRSA
eksctl create iamserviceaccount \
  --cluster=my-cluster \
  --namespace=aws-application-networking-system \
  --name=gateway-api-controller \
  --attach-policy-arn=arn:aws:iam::123456789012:policy/VPCLatticeControllerPolicy \
  --override-existing-serviceaccounts \
  --approve

# 3. Install AWS Gateway API Controller
kubectl apply -f https://raw.githubusercontent.com/aws/aws-application-networking-k8s/main/files/controller-installation/deploy-v1.0.yaml
```

**Explicación:**
AWS Gateway API Controller observa los recursos de Gateway API en el clúster de Kubernetes y crea/gestiona recursos de VPC Lattice. A través de IRSA (IAM Roles for Service Accounts), el Pod del controlador obtiene permisos para llamar a las API de AWS requeridas. La política incluye operaciones de vpc-lattice, búsqueda de VPC/subnet y permisos de entrega de logs.
</details>

14. Escribe un HTTPRoute que configure el enrutamiento ponderado (90:10) entre dos servicios utilizando VPC Lattice.

<details>

<summary>Mostrar respuesta</summary>

**Respuesta:**
```yaml
# GatewayClass definition
apiVersion: gateway.networking.k8s.io/v1beta1
kind: GatewayClass
metadata:
  name: amazon-vpc-lattice
spec:
  controllerName: application-networking.k8s.aws/gateway-api-controller
---
# Gateway definition
apiVersion: gateway.networking.k8s.io/v1beta1
kind: Gateway
metadata:
  name: my-gateway
  namespace: default
spec:
  gatewayClassName: amazon-vpc-lattice
  listeners:
  - name: http
    protocol: HTTP
    port: 80
---
# Weighted routing HTTPRoute
apiVersion: gateway.networking.k8s.io/v1beta1
kind: HTTPRoute
metadata:
  name: weighted-routing
  namespace: default
spec:
  parentRefs:
  - name: my-gateway
    sectionName: http
  rules:
  - matches:
    - path:
        type: PathPrefix
        value: /api
    backendRefs:
    - name: service-stable
      port: 80
      weight: 90
    - name: service-canary
      port: 80
      weight: 10
---
# Stable service
apiVersion: v1
kind: Service
metadata:
  name: service-stable
spec:
  selector:
    app: myapp
    version: stable
  ports:
  - port: 80
    targetPort: 8080
---
# Canary service
apiVersion: v1
kind: Service
metadata:
  name: service-canary
spec:
  selector:
    app: myapp
    version: canary
  ports:
  - port: 80
    targetPort: 8080
```

**Explicación:**
En esta configuración, el 90 % del tráfico a la ruta `/api` se enruta a service-stable y el 10 % a service-canary. Cuando AWS Gateway API Controller detecta este HTTPRoute, crea dos Target Groups en VPC Lattice y configura reglas de listener para distribuir el tráfico según los pesos especificados. Después de validar el despliegue canary, los pesos se pueden ajustar gradualmente.
</details>

15. Escribe una Auth Policy basada en IAM para un servicio de VPC Lattice. (Permite que solo roles específicos de IAM accedan a la ruta /admin)

<details>

<summary>Mostrar respuesta</summary>

**Respuesta:**
```bash
# Apply Auth Policy to VPC Lattice service
aws vpc-lattice put-auth-policy \
  --resource-identifier svc-0123456789abcdef0 \
  --policy '{
    "Version": "2012-10-17",
    "Statement": [
      {
        "Sid": "AllowGeneralAccess",
        "Effect": "Allow",
        "Principal": "*",
        "Action": "vpc-lattice-svcs:Invoke",
        "Resource": "*",
        "Condition": {
          "StringNotEquals": {
            "vpc-lattice-svcs:RequestPath": "/admin/*"
          }
        }
      },
      {
        "Sid": "AllowAdminAccess",
        "Effect": "Allow",
        "Principal": {
          "AWS": [
            "arn:aws:iam::123456789012:role/AdminRole",
            "arn:aws:iam::123456789012:role/DevOpsRole"
          ]
        },
        "Action": "vpc-lattice-svcs:Invoke",
        "Resource": "*",
        "Condition": {
          "StringLike": {
            "vpc-lattice-svcs:RequestPath": "/admin/*"
          }
        }
      },
      {
        "Sid": "DenyUnauthorizedAdmin",
        "Effect": "Deny",
        "Principal": "*",
        "Action": "vpc-lattice-svcs:Invoke",
        "Resource": "*",
        "Condition": {
          "StringLike": {
            "vpc-lattice-svcs:RequestPath": "/admin/*"
          },
          "StringNotEquals": {
            "aws:PrincipalArn": [
              "arn:aws:iam::123456789012:role/AdminRole",
              "arn:aws:iam::123456789012:role/DevOpsRole"
            ]
          }
        }
      }
    ]
  }'
```

**Método de Kubernetes Gateway API:**
```yaml
apiVersion: gateway.networking.k8s.io/v1beta1
kind: Gateway
metadata:
  name: secure-gateway
  namespace: default
  annotations:
    application-networking.k8s.aws/auth-type: "AWS_IAM"
spec:
  gatewayClassName: amazon-vpc-lattice
  listeners:
  - name: http
    protocol: HTTP
    port: 80
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: vpc-lattice-auth-policy
  namespace: default
  annotations:
    application-networking.k8s.aws/auth-policy: |
      {
        "Version": "2012-10-17",
        "Statement": [
          {
            "Effect": "Allow",
            "Principal": {
              "AWS": "arn:aws:iam::123456789012:role/AdminRole"
            },
            "Action": "vpc-lattice-svcs:Invoke",
            "Resource": "*"
          }
        ]
      }
data: {}
```

**Explicación:**
Esta Auth Policy consta de tres reglas:
1. **AllowGeneralAccess**: Permite a todos los principales todas las rutas excepto /admin/*
2. **AllowAdminAccess**: Permite a AdminRole y DevOpsRole acceder a la ruta /admin/*
3. **DenyUnauthorizedAdmin**: Deniega explícitamente el acceso a /admin/* para principales distintos de los roles anteriores

Los clientes deben firmar las solicitudes con SigV4. Puedes utilizar AWS SDK o la biblioteca aws-sigv4 para la firma.
</details>

---

**Puntuación:**
- 13-15 correctas: Excelente (nivel experto en VPC Lattice)
- 10-12 correctas: Bien (capaz de aplicar los conocimientos en la práctica)
- 7-9 correctas: Promedio (se recomienda aprendizaje adicional)
- 4-6 correctas: Básico (se necesita repasar los conceptos básicos)
- 0-3 correctas: Insuficiente (se necesita volver a estudiar todo el contenido)
