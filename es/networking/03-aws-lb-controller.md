# Controlador de AWS Load Balancer

> **Base de revisión**: AWS Load Balancer Controller / Helm chart v3.6.0
> **Última actualización**: 16 de octubre de 2026

## Descripción general

AWS Load Balancer Controller es un controlador que administra los Elastic Load Balancers (ELB) de AWS para los clústeres de Kubernetes. Integra automáticamente los recursos Ingress y Service de Kubernetes con los Application Load Balancer (ALB) y Network Load Balancer (NLB) de AWS.

### Características principales

- **Application Load Balancer (ALB)**: tráfico HTTP/HTTPS, enrutamiento basado en rutas y en hosts
- **Network Load Balancer (NLB)**: tráfico TCP/UDP, balanceo de carga L4 de alto rendimiento
- **TargetGroupBinding**: conecta los grupos de destino existentes con los Services de Kubernetes
- **Integración con AWS WAF**: aplicación de reglas de Web Application Firewall
- **AWS Shield**: protección contra DDoS

![Diagrama que muestra los recursos Ingress y Service de un clúster de EKS que activan AWS Load Balancer Controller, el cual crea un Application Load Balancer y un Network Load Balancer, cada uno con su propio grupo de destino, mientras que TargetGroupBinding vincula directamente un grupo de destino existente; ambos grupos de destino registran los mismos Pods de backend.](../.gitbook/assets/en-networking-03-aws-lb-controller-0.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-networking-03-aws-lb-controller-0.html)

## Arquitectura

### Cómo funciona el controlador

![Secuencia en la que AWS Load Balancer Controller reacciona ante un nuevo Ingress o Service creando el ALB o NLB, el grupo de destino y las reglas de escucha mediante la API ELBv2; actualiza el estado del recurso y sigue registrando destinos a medida que cambian los Pods.](../.gitbook/assets/en-networking-03-aws-lb-controller-1.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-networking-03-aws-lb-controller-1.html)

### Estructura de los componentes

Instale el chart publicado completo, incluidos RBAC, CRD, sondas y certificados de webhook. El controlador observa los objetos de Kubernetes y llama a las API de AWS; el tráfico de las aplicaciones pasa por el balanceador de carga y sus destinos, no por el pod del controlador. Con la elección de líder, una réplica realiza la reconciliación mientras las demás ofrecen capacidad en espera y disponibilidad del webhook. El número de réplicas, por sí solo, no garantiza la distribución entre nodos o zonas de disponibilidad.

## Requisitos previos

### Propiedad y compatibilidad

Este capítulo configura el **controlador de código abierto autoadministrado**. EKS Auto Mode proporciona su propio balanceo de carga administrado: los Services NLB usan `eks.amazonaws.com/nlb`, la IngressClass ALB usa `eks.amazonaws.com/alb` y su API TargetGroupBinding es distinta de `elbv2.k8s.aws/v1beta1`. Consulte la guía de migración de Auto Mode en lugar de cambiar una clase o copiar todas las anotaciones tal cual. Las clases explícitas evitan ambigüedades cuando están presentes ambos modelos.

Use una versión de Kubernetes de EKS que tenga soporte vigente y verifique todos los controladores que compartan CRD de ámbito de clúster. **v3.6.0** de LBC se publicó el **2026-10-05**; el chart **3.6.0** verificado incluye ese controlador. v3.6.0 conserva la misma base de CRD de Gateway API **v1.6.0** que v3.5.0, por lo que quienes usen Gateway API necesitan los CRD v1.6.0 antes de actualizar. Las notas de la versión solicitan aplicar los CRD de LBC más recientes proporcionados por AWS (la salida de `helm show crds` del chart) antes de actualizar el controlador, y los CRD de Gateway específicos de LBC usan `gateway.k8s.aws/v1`. Esto no significa que una versión cualquiera más reciente de Gateway API o Kubernetes sea compatible. El antiguo requisito genérico de instalación de “Kubernetes 1.22+” no es una matriz vigente de compatibilidad con EKS.

El webhook del controlador necesita conectividad TCP en el puerto 9443 desde el plano de control. Configure explícitamente los valores de región y VPC cuando IMDS esté restringido o el controlador se ejecute en Fargate o Hybrid Nodes; elija un mecanismo de credenciales compatible con ese tipo de cómputo. Los destinos IP necesitan direcciones de pod enrutables desde la VPC y detección compatible de endpoints/ENI. Amazon VPC CNI es la opción común en EKS, pero no es la única configuración posible de CNI. Los destinos de tipo instancia requieren un Service compatible con NodePort y una red de nodos adecuada.

### 1. Crear la política de IAM

Use la política de IAM incluida con **v3.6.0** y la partición de AWS correcta. Revise sus permisos amplios de detección y de grupos de seguridad, las condiciones sobre recursos/etiquetas y las características habilitadas en esta implementación. Guarde la política revisada antes de crearla. No considere que la política original garantiza el mínimo privilegio ni copie una política antigua de v2.8 en una instalación actual. Las credenciales de AWS del controlador pueden usar **IRSA o EKS Pod Identity** en los nodos compatibles; son independientes del RBAC de la API de Kubernetes.

### 2. Configuración de IRSA

```bash
export AWS_REGION=us-east-1
export CLUSTER_NAME=my-cluster
export AWS_ACCOUNT_ID="$(aws sts get-caller-identity --query Account --output text)"
export VPC_ID="$(aws eks describe-cluster --name "$CLUSTER_NAME" \
  --query 'cluster.resourcesVpcConfig.vpcId' --output text)"
kubectl config current-context

aws eks describe-cluster --name "$CLUSTER_NAME" \
  --query cluster.identity.oidc.issuer --output text
# Only if this cluster's IAM OIDC provider does not already exist:
eksctl utils associate-iam-oidc-provider --cluster "$CLUSTER_NAME" \
  --region "$AWS_REGION" --approve

curl --fail --location --output iam-policy-upstream.json \
  https://raw.githubusercontent.com/kubernetes-sigs/aws-load-balancer-controller/v3.6.0/docs/install/iam_policy.json
export REVIEWED_POLICY_FILE=iam-policy-reviewed.json
test -s "$REVIEWED_POLICY_FILE"
export CONTROLLER_POLICY_ARN="$(aws iam create-policy \
  --policy-name AWSLoadBalancerControllerIAMPolicy \
  --policy-document "file://$REVIEWED_POLICY_FILE" --query Policy.Arn --output text)"
eksctl create iamserviceaccount --cluster "$CLUSTER_NAME" --region "$AWS_REGION" \
  --namespace kube-system --name aws-load-balancer-controller \
  --attach-policy-arn "$CONTROLLER_POLICY_ARN" --approve
```

Reutilice las políticas y los roles existentes que ya se hayan revisado en lugar de volver a crearlos. Un rol IRSA reutilizado necesita una instrucción de confianza para el proveedor OIDC de este clúster y la cuenta de servicio prevista. Si la cuenta de servicio ya existe, revise su propiedad y sus anotaciones antes de cambiarla. Pod Identity usa su propio agente/asociación y configuración de confianza del rol; no copie claves de acceso estáticas en los valores del chart.

## Instalación

### Instalación con Helm

```bash
helm repo add eks https://aws.github.io/eks-charts
helm repo update eks
helm pull eks/aws-load-balancer-controller --version 3.6.0

# Review cluster-wide CRD changes and other controllers before applying.
curl --fail --location --output gateway-api-v1.6.0.yaml \
  https://github.com/kubernetes-sigs/gateway-api/releases/download/v1.6.0/standard-install.yaml
kubectl apply --server-side -f gateway-api-v1.6.0.yaml
helm show crds ./aws-load-balancer-controller-3.6.0.tgz > lbc-crds.yaml
kubectl apply --server-side -f lbc-crds.yaml

# Save the values below as controller-values.yaml and replace its cluster/region/VPC.
helm install aws-load-balancer-controller ./aws-load-balancer-controller-3.6.0.tgz \
  -n kube-system -f controller-values.yaml --wait --timeout 5m
```

```yaml
# values.yaml example
clusterName: my-cluster
serviceAccount:
  create: false
  name: aws-load-balancer-controller

region: us-east-1
vpcId: vpc-0123456789abcdef0

# Resource settings
resources:
  requests:
    cpu: 100m
    memory: 128Mi
  limits:
    cpu: 200m
    memory: 256Mi

# Replica count
replicaCount: 2

# Pod Disruption Budget
podDisruptionBudget:
  minAvailable: 1

# Anti-Affinity for HA
affinity:
  podAntiAffinity:
    preferredDuringSchedulingIgnoredDuringExecution:
      - weight: 100
        podAffinityTerm:
          labelSelector:
            matchExpressions:
              - key: app.kubernetes.io/name
                operator: In
                values:
                  - aws-load-balancer-controller
          topologyKey: kubernetes.io/hostname

# Webhook certificates
enableCertManager: false

# Log level
logLevel: info

# IngressClass settings
ingressClass: alb
createIngressClassResource: true

# Additional settings
enableShield: false
enableWaf: false
enableWafv2: true
# Use explicit Service classes; do not claim unclassified LoadBalancer Services.
enableServiceMutatorWebhook: false
enableEndpointSlices: true
keepTLSSecret: true
clusterSecretsPermissions:
  allowAllSecrets: false
```

Los valores de recursos son ejemplos, no mediciones del dimensionamiento de producción. Las versiones instaladas requieren un `helm upgrade` revisado con los valores guardados; Helm no actualiza los CRD automáticamente. Con `enableServiceMutatorWebhook: false`, los Services NLB de este capítulo seleccionan explícitamente `service.k8s.aws/nlb`. De lo contrario, el webhook predeterminado modifica los Services LoadBalancer recién creados, pero no un Service existente cuyo tipo se cambia más adelante. `keepTLSSecret: true` reutiliza el Secret del webhook administrado por Helm cuando está disponible; coordine el paquete de CA y el certificado del pod durante las operaciones de GitOps o la rotación, o use un cert-manager compatible instalado por separado. No elimine CRD compartidos para forzar una actualización.

### Verificar la instalación

```bash
# Check Deployment status
kubectl get deployment -n kube-system aws-load-balancer-controller

# Check Pod status
kubectl get pods -n kube-system -l app.kubernetes.io/name=aws-load-balancer-controller

# Check logs
kubectl logs -n kube-system -l app.kubernetes.io/name=aws-load-balancer-controller

# Check IngressClass
kubectl get ingressclass
```

## Application Load Balancer (ALB)

Considere cada manifiesto siguiente como un ejemplo independiente. Sustituya los ID de cuenta y recursos, los dominios, las subredes, los grupos de seguridad y los ARN de certificados por valores verificados de la región correcta. Cree primero los espacios de nombres, Services y cargas de trabajo de backend listas que se mencionan; el puerto 80 del Service y el puerto de destino 8080 cumplen funciones distintas. Declarar un containerPort no hace que una aplicación escuche ni que implemente /health. El endpoint de comprobación de estado, el puerto de destino real, el protocolo HTTP/TLS, los grupos de seguridad y las NetworkPolicies deben ser coherentes. La imagen de la descripción general ilustra **destinos IP**; los destinos de tipo instancia registran nodos y usan NodePorts. Este controlador también reconcilia TargetGroupBinding, y el diagrama de secuencia es ilustrativo, no representa una transacción atómica.

### Configuración básica de Ingress

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: my-ingress
  namespace: default
  annotations:
    # ALB scheme (internet-facing or internal)
    alb.ingress.kubernetes.io/scheme: internet-facing

    # Target Type (ip or instance)
    alb.ingress.kubernetes.io/target-type: ip

    # Listener ports
    alb.ingress.kubernetes.io/listen-ports: '[{"HTTP": 80}, {"HTTPS": 443}]'

    # SSL redirect
    alb.ingress.kubernetes.io/ssl-redirect: "443"

    # ACM certificate
    alb.ingress.kubernetes.io/certificate-arn: arn:aws:acm:us-east-1:ACCOUNT:certificate/CERT_ID

    # Subnet specification
    alb.ingress.kubernetes.io/subnets: subnet-xxx,subnet-yyy,subnet-zzz

    # Security groups
    alb.ingress.kubernetes.io/security-groups: sg-xxxxxxxxx
    alb.ingress.kubernetes.io/manage-backend-security-group-rules: "true"

    # Health check settings
    alb.ingress.kubernetes.io/healthcheck-path: /health
    alb.ingress.kubernetes.io/healthcheck-interval-seconds: "15"
    alb.ingress.kubernetes.io/healthcheck-timeout-seconds: "5"
    alb.ingress.kubernetes.io/healthy-threshold-count: "2"
    alb.ingress.kubernetes.io/unhealthy-threshold-count: "2"

spec:
  ingressClassName: alb
  rules:
    - host: api.example.com
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: api-service
                port:
                  number: 80
```

### Configuración avanzada de Ingress

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: advanced-ingress
  annotations:
    alb.ingress.kubernetes.io/scheme: internet-facing
    alb.ingress.kubernetes.io/target-type: ip

    # Group multiple Ingresses into single ALB
    alb.ingress.kubernetes.io/group.name: my-app-group
    alb.ingress.kubernetes.io/group.order: "10"

    # Target group attributes
    alb.ingress.kubernetes.io/target-group-attributes: >-
      stickiness.enabled=true,
      stickiness.lb_cookie.duration_seconds=60,
      slow_start.duration_seconds=30,
      deregistration_delay.timeout_seconds=30

    # IP address type
    alb.ingress.kubernetes.io/ip-address-type: dualstack

    # Load balancer attributes
    alb.ingress.kubernetes.io/load-balancer-attributes: >-
      idle_timeout.timeout_seconds=60,
      routing.http2.enabled=true,
      routing.http.drop_invalid_header_fields.enabled=true,
      access_logs.s3.enabled=true,
      access_logs.s3.bucket=my-alb-logs,
      access_logs.s3.prefix=my-app

    # Tags
    alb.ingress.kubernetes.io/tags: Environment=production,Team=platform

    # WAF v2 integration
    alb.ingress.kubernetes.io/wafv2-acl-arn: arn:aws:wafv2:us-east-1:ACCOUNT:regional/webacl/my-acl/xxx

    # Shield Advanced
    alb.ingress.kubernetes.io/shield-advanced-protection: "true"

spec:
  ingressClassName: alb
  tls:
    - hosts:
        - api.example.com
        - www.example.com
  rules:
    - host: api.example.com
      http:
        paths:
          - path: /v1
            pathType: Prefix
            backend:
              service:
                name: api-v1
                port:
                  number: 80
          - path: /v2
            pathType: Prefix
            backend:
              service:
                name: api-v2
                port:
                  number: 80
    - host: www.example.com
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: web-frontend
                port:
                  number: 80
```

### Enrutamiento basado en rutas

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: path-based-routing
  annotations:
    alb.ingress.kubernetes.io/scheme: internet-facing
    alb.ingress.kubernetes.io/target-type: ip

    # Condition-based routing
    alb.ingress.kubernetes.io/conditions.api-v2: >-
      [{"field":"http-header","httpHeaderConfig":{"httpHeaderName":"X-Api-Version","values":["v2"]}}]

spec:
  ingressClassName: alb
  rules:
    - host: api.example.com
      http:
        paths:
          # Exact path matching
          - path: /health
            pathType: Exact
            backend:
              service:
                name: health-service
                port:
                  number: 80

          # API version routing
          - path: /api
            pathType: Prefix
            backend:
              service:
                name: api-v2
                port:
                  number: 80
          - path: /api
            pathType: Prefix
            backend:
              service:
                name: api-v1
                port:
                  number: 80

          # Static files
          - path: /static
            pathType: Prefix
            backend:
              service:
                name: static-service
                port:
                  number: 80

          # Default path
          - path: /
            pathType: Prefix
            backend:
              service:
                name: default-service
                port:
                  number: 80
```

### Configuración de autenticación

Estos ejemplos requieren un certificado HTTPS existente y una aplicación de proveedor de identidad. Configure la URL de retorno `https://app.example.com/oauth2/idpresponse`, el flujo de código de autorización, los ámbitos permitidos y el secreto de cliente requerido. El ALB debe poder acceder a los endpoints de token e información de usuario del proveedor mediante IPv4; un ALB interno puede necesitar una ruta de salida/NAT adecuada. La autenticación se realiza solo en los listeners HTTPS. El valor `allow` para solicitudes no autenticadas no protege el backend. Restrinja el acceso directo al backend y verifique las declaraciones de usuario firmadas por el ALB según lo requiera la aplicación.

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: auth-ingress
  annotations:
    alb.ingress.kubernetes.io/scheme: internet-facing
    alb.ingress.kubernetes.io/target-type: ip
    alb.ingress.kubernetes.io/listen-ports: '[{"HTTPS": 443}]'
    alb.ingress.kubernetes.io/certificate-arn: arn:aws:acm:us-east-1:123456789012:certificate/12345678-1234-1234-1234-123456789012

    # Cognito authentication
    alb.ingress.kubernetes.io/auth-type: cognito
    alb.ingress.kubernetes.io/auth-idp-cognito: >-
      {"userPoolARN":"arn:aws:cognito-idp:us-east-1:ACCOUNT:userpool/us-east-1_xxxxx",
       "userPoolClientID":"xxxxxxxxx",
       "userPoolDomain":"my-domain"}
    alb.ingress.kubernetes.io/auth-on-unauthenticated-request: authenticate
    alb.ingress.kubernetes.io/auth-scope: "openid profile email"
    alb.ingress.kubernetes.io/auth-session-cookie: "AWSELBAuthSessionCookie"
    alb.ingress.kubernetes.io/auth-session-timeout: "3600"

spec:
  ingressClassName: alb
  rules:
    - host: app.example.com
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: protected-app
                port:
                  number: 80
```

```yaml
# OIDC Authentication Example
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: oidc-ingress
  annotations:
    alb.ingress.kubernetes.io/scheme: internet-facing
    alb.ingress.kubernetes.io/target-type: ip
    alb.ingress.kubernetes.io/listen-ports: '[{"HTTPS": 443}]'
    alb.ingress.kubernetes.io/certificate-arn: arn:aws:acm:us-east-1:123456789012:certificate/12345678-1234-1234-1234-123456789012

    # OIDC authentication
    alb.ingress.kubernetes.io/auth-type: oidc
    alb.ingress.kubernetes.io/auth-idp-oidc: >-
      {"issuer":"https://accounts.google.com",
       "authorizationEndpoint":"https://accounts.google.com/o/oauth2/v2/auth",
       "tokenEndpoint":"https://oauth2.googleapis.com/token",
       "userInfoEndpoint":"https://openidconnect.googleapis.com/v1/userinfo",
       "secretName":"oidc-secret"}
    alb.ingress.kubernetes.io/auth-on-unauthenticated-request: authenticate

spec:
  ingressClassName: alb
  rules:
    - host: app.example.com
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: protected-app
                port:
                  number: 80
---
# OIDC Secret
apiVersion: v1
kind: Secret
metadata:
  name: oidc-secret
type: Opaque
stringData:
  clientID: your-client-id
  clientSecret: your-client-secret
```

El Secret OIDC debe estar en el espacio de nombres de Ingress. El valor predeterminado del chart es `clusterSecretsPermissions.allowAllSecrets: false`; conceda a este controlador solo el acceso necesario a los Secret. v3.6.0 observa un Secret mediante un selector de campo `metadata.name`, por lo que el Role puede limitarse con `resourceNames`. Cree el Secret real mediante el flujo de trabajo aprobado de administración de secretos; no incluya un secreto de cliente real en el repositorio.

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: lbc-oidc-secret
  namespace: default
rules:
- apiGroups:
  - ''
  resources:
  - secrets
  resourceNames:
  - oidc-secret
  verbs:
  - get
  - list
  - watch
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: lbc-oidc-secret
  namespace: default
subjects:
- kind: ServiceAccount
  name: aws-load-balancer-controller
  namespace: kube-system
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: Role
  name: lbc-oidc-secret
```

## Network Load Balancer (NLB)

### Configuración básica de un Service NLB

```yaml
apiVersion: v1
kind: Service
metadata:
  name: nlb-service
  annotations:
    # Specify NLB type
    service.beta.kubernetes.io/aws-load-balancer-nlb-target-type: "ip"

    # Scheme
    service.beta.kubernetes.io/aws-load-balancer-scheme: "internet-facing"

    # Subnet specification
    service.beta.kubernetes.io/aws-load-balancer-subnets: subnet-xxx,subnet-yyy

    # Health check
    service.beta.kubernetes.io/aws-load-balancer-healthcheck-protocol: "HTTP"
    service.beta.kubernetes.io/aws-load-balancer-healthcheck-path: "/health"
    service.beta.kubernetes.io/aws-load-balancer-healthcheck-port: "8080"
    service.beta.kubernetes.io/aws-load-balancer-healthcheck-interval: "10"
    service.beta.kubernetes.io/aws-load-balancer-healthcheck-healthy-threshold: "2"
    service.beta.kubernetes.io/aws-load-balancer-healthcheck-unhealthy-threshold: "2"

spec:
  type: LoadBalancer
  loadBalancerClass: service.k8s.aws/nlb
  selector:
    app: my-app
  ports:
    - name: tcp
      port: 80
      targetPort: 8080
      protocol: TCP
```

### Grupos de destino ponderados

El Service siguiente asigna un peso de 90 a su propio grupo de destino implícito y un peso de 10 al backend existente `service-canary:8080`. Ambos Services deben tener los endpoints listos previstos y una configuración de destinos compatible; esta anotación no crea la carga de trabajo canary. El sufijo de la anotación corresponde al protocolo y puerto del listener: **`actions.TCP-80`**.

Los pesos son valores relativos de **0 a 999** y se aplican a las conexiones nuevas. Los cambios de peso habituales conservan las conexiones existentes; **si se establece en 0 el peso de un grupo de destino, sus conexiones existentes se cierran tras un breve periodo**, además de dejar de aceptar conexiones nuevas. No describa esto como un drenaje con tiempo de inactividad cero garantizado. Los listeners TLS requieren protocolos de grupo de destino compatibles y no admiten afinidad de grupo de destino.

```yaml
apiVersion: v1
kind: Service
metadata:
  name: nlb-weighted
  namespace: default
  annotations:
    service.beta.kubernetes.io/aws-load-balancer-nlb-target-type: ip
    service.beta.kubernetes.io/aws-load-balancer-scheme: internal
    service.beta.kubernetes.io/actions.TCP-80: '{"type":"forward","forwardConfig":{"baseServiceWeight":90,"targetGroups":[{"serviceName":"service-canary","servicePort":8080,"weight":10}]}}'
spec:
  type: LoadBalancer
  loadBalancerClass: service.k8s.aws/nlb
  selector:
    app: my-app
    version: stable
  ports:
  - name: tcp
    port: 80
    targetPort: 8080
    protocol: TCP
```

### Terminación TLS en NLB

```yaml
apiVersion: v1
kind: Service
metadata:
  name: nlb-tls-service
  annotations:
    service.beta.kubernetes.io/aws-load-balancer-nlb-target-type: "ip"
    service.beta.kubernetes.io/aws-load-balancer-scheme: "internet-facing"

    # TLS configuration
    service.beta.kubernetes.io/aws-load-balancer-ssl-cert: "arn:aws:acm:us-east-1:ACCOUNT:certificate/CERT_ID"
    service.beta.kubernetes.io/aws-load-balancer-ssl-ports: "443"
    service.beta.kubernetes.io/aws-load-balancer-ssl-negotiation-policy: "ELBSecurityPolicy-TLS13-1-2-2021-06"

    # Backend is HTTP
    service.beta.kubernetes.io/aws-load-balancer-backend-protocol: "tcp"

spec:
  type: LoadBalancer
  loadBalancerClass: service.k8s.aws/nlb
  selector:
    app: my-app
  ports:
    - name: https
      port: 443
      targetPort: 8080
      protocol: TCP
```

### NLB interno

```yaml
apiVersion: v1
kind: Service
metadata:
  name: internal-nlb
  annotations:
    service.beta.kubernetes.io/aws-load-balancer-nlb-target-type: "ip"

    # Internal scheme
    service.beta.kubernetes.io/aws-load-balancer-scheme: "internal"

    # Cross-zone load balancing
    service.beta.kubernetes.io/aws-load-balancer-attributes: "load_balancing.cross_zone.enabled=true"

    # Private subnets
    service.beta.kubernetes.io/aws-load-balancer-subnets: subnet-private-a,subnet-private-b

    # Security groups (optional)
    service.beta.kubernetes.io/aws-load-balancer-security-groups: sg-xxxxxxxxx
    service.beta.kubernetes.io/aws-load-balancer-manage-backend-security-group-rules: "true"

spec:
  type: LoadBalancer
  loadBalancerClass: service.k8s.aws/nlb
  selector:
    app: internal-service
  ports:
    - port: 80
      targetPort: 8080
```

### Compatibilidad con UDP en NLB

```yaml
apiVersion: v1
kind: Service
metadata:
  name: udp-nlb
  annotations:
    service.beta.kubernetes.io/aws-load-balancer-enable-tcp-udp-listener: "true"
    service.beta.kubernetes.io/aws-load-balancer-nlb-target-type: "ip"
    service.beta.kubernetes.io/aws-load-balancer-scheme: "internet-facing"

spec:
  type: LoadBalancer
  loadBalancerClass: service.k8s.aws/nlb
  selector:
    app: dns-server
  ports:
    - name: dns-udp
      port: 53
      targetPort: 53
      protocol: UDP
    - name: dns-tcp
      port: 53
      targetPort: 53
      protocol: TCP
```

### Proxy Protocol v2

Proxy Protocol v2 transmite la dirección original del cliente como metadatos binarios de conexión; **no** conserva la dirección de origen del paquete IP. El ejemplo deshabilita la conservación de la IP del cliente a nivel de paquete para dejar clara la diferencia. El backend debe analizar Proxy Protocol antes de los datos de la aplicación, incluidas las conexiones de comprobación de estado aplicables. Un servidor HTTP/TLS normal no puede consumir ese prefijo sin configuración.

`preserve_client_ip.enabled` controla la conservación del origen del paquete por parte del NLB cuando sea compatible con el tipo de destino, el protocolo y la ruta de red. Con destinos de tipo instancia/NodePort, `externalTrafficPolicy: Local` puede evitar un salto posterior de SNAT de kube-proxy; no sustituye de manera universal la conservación del NLB. La traducción entre familias IP y las rutas de tránsito o hairpin no compatibles requieren consideración aparte.

```yaml
apiVersion: v1
kind: Service
metadata:
  name: proxy-protocol-nlb
  annotations:
    service.beta.kubernetes.io/aws-load-balancer-nlb-target-type: "ip"
    service.beta.kubernetes.io/aws-load-balancer-scheme: "internet-facing"

    # Enable Proxy Protocol v2

    # Target Group attributes
    service.beta.kubernetes.io/aws-load-balancer-target-group-attributes: >-
      proxy_protocol_v2.enabled=true,
      preserve_client_ip.enabled=false

spec:
  type: LoadBalancer
  loadBalancerClass: service.k8s.aws/nlb
  selector:
    app: proxy-aware-app
  ports:
    - port: 80
      targetPort: 8080
```

## IngressClass e IngressClassParams

Esta clase opcional se llama `alb-platform` para evitar sobrescribir la clase `alb` que administra el chart. Etiquete los espacios de nombres previstos con `alb-enabled=true` y establezca `spec.ingressClassName: alb-platform` en su Ingress. No la convierta en la clase predeterminada del clúster salvo que esa sea la política prevista. La configuración de IngressClassParams tiene prioridad sobre las anotaciones correspondientes.

### Definición de IngressClass

```yaml
apiVersion: networking.k8s.io/v1
kind: IngressClass
metadata:
  name: alb-platform
spec:
  controller: ingress.k8s.aws/alb
  parameters:
    apiGroup: elbv2.k8s.aws
    kind: IngressClassParams
    name: alb-params
```

### Configuración de IngressClassParams

```yaml
apiVersion: elbv2.k8s.aws/v1beta1
kind: IngressClassParams
metadata:
  name: alb-params
spec:
  # Default scheme
  scheme: internet-facing

  # IP address type
  ipAddressType: dualstack

  # Namespace selector (allow only specific namespaces)
  namespaceSelector:
    matchLabels:
      alb-enabled: "true"

  # Default tags
  tags:
    - key: Environment
      value: production
    - key: ManagedBy
      value: aws-load-balancer-controller

  # Load balancer attributes
  loadBalancerAttributes:
    - key: idle_timeout.timeout_seconds
      value: "60"
    - key: routing.http2.enabled
      value: "true"

  # Subnet selection
  # subnets:
  #   ids:
  #     - subnet-xxx
  #     - subnet-yyy
  #   tags:
  #     kubernetes.io/role/elb: ["1"]

  # Group settings
  group:
    name: my-default-group
```

## TargetGroupBinding

El CRD TargetGroupBinding permite conectar directamente los grupos de destino de AWS existentes con los Services de Kubernetes.

### TargetGroupBinding básico

```yaml
apiVersion: elbv2.k8s.aws/v1beta1
kind: TargetGroupBinding
metadata:
  name: my-tgb
  namespace: default
spec:
  # Existing Target Group ARN
  targetGroupARN: arn:aws:elasticloadbalancing:us-east-1:ACCOUNT:targetgroup/my-tg/xxxxxxxxxxxx

  # Service to connect
  serviceRef:
    name: my-service
    port: 80

  # Target Type (ip or instance)
  targetType: ip

  # Networking settings
  networking:
    ingress:
      - from:
          - securityGroup:
              groupID: sg-xxxxxxxxx
        ports:
          - port: 80
            protocol: TCP
```

Un TGB administra los registros, no el ciclo de vida del balanceador de carga o del listener existentes. Mantenga coherentes el puerto del Service, el protocolo/la familia IP del grupo de destino, el puerto de destino del backend y las reglas del grupo de seguridad. `nodeSelector` solo filtra los destinos de **tipo instancia**; no elige Pods en modo IP. Restrinja la creación y actualización de TGB a operadores de confianza, ya que los permisos de IAM del controlador pueden permitir referencias a otros grupos de destino de la cuenta.

Cuando varios clústeres o TGB comparten un grupo de destino, configure `spec.multiClusterTargetGroup: true` **desde la creación en todos los TGB participantes**. El valor predeterminado `false` supone la propiedad exclusiva y puede anular el registro de destinos de otros clústeres. No cambie esta marca a la ligera después de crear el recurso; el cambio documentado puede dejar destinos huérfanos. Usar grupos de destino separados por clúster es otro modelo de propiedad.

### TargetGroupBinding avanzado

```yaml
apiVersion: elbv2.k8s.aws/v1beta1
kind: TargetGroupBinding
metadata:
  name: advanced-tgb
  namespace: production
spec:
  targetGroupARN: arn:aws:elasticloadbalancing:us-east-1:ACCOUNT:targetgroup/prod-tg/xxxxxxxxxxxx

  serviceRef:
    name: production-service
    port: 8080

  targetType: ip

  # IP address type
  ipAddressType: ipv4

  # VPC ID (auto-detected, can be explicit)
  # vpcID: vpc-xxxxxxxxx

  # Networking settings
  networking:
    ingress:
      # Allow traffic from multiple security groups
      - from:
          - securityGroup:
              groupID: sg-alb-sg
          - securityGroup:
              groupID: sg-internal-sg
        ports:
          - port: 8080
            protocol: TCP
          - port: 8443
            protocol: TCP

  # Node selector applies to instance targets, not IP-mode pod selection
  # nodeSelector:
  #   matchLabels:
  #     node-type: compute
```

### TargetGroupBinding para varios puertos

```yaml
# Separate TargetGroupBindings for multiple ports
---
apiVersion: elbv2.k8s.aws/v1beta1
kind: TargetGroupBinding
metadata:
  name: http-tgb
spec:
  targetGroupARN: arn:aws:elasticloadbalancing:...:targetgroup/http-tg/xxx
  serviceRef:
    name: multi-port-service
    port: 80
  targetType: ip
---
apiVersion: elbv2.k8s.aws/v1beta1
kind: TargetGroupBinding
metadata:
  name: https-tgb
spec:
  targetGroupARN: arn:aws:elasticloadbalancing:...:targetgroup/https-tg/yyy
  serviceRef:
    name: multi-port-service
    port: 443
  targetType: ip
```

## Integración con WAF y Shield

Use una Web ACL regional existente en la región del ALB y configure las reglas previstas. Los valores de instalación habilitan WAF v2, pero deshabilitan la integración con Shield; para usar el ejemplo de Shield Advanced, primero organice la suscripción y los permisos necesarios, y habilite la integración de Shield del controlador. La anotación por sí sola no activa una suscripción de pago ni anula la deshabilitación de una característica del controlador. Estas integraciones de ALB no implican que WAF inspeccione tráfico TCP/UDP arbitrario de NLB. El ejemplo de registros de acceso en S3 también requiere un bucket de destino existente y la política documentada del bucket para la entrega de registros de ALB.

### Integración con AWS WAF v2

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: waf-protected-ingress
  annotations:
    alb.ingress.kubernetes.io/scheme: internet-facing
    alb.ingress.kubernetes.io/target-type: ip

    # Connect WAF v2 WebACL
    alb.ingress.kubernetes.io/wafv2-acl-arn: arn:aws:wafv2:us-east-1:ACCOUNT:regional/webacl/my-webacl/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx

spec:
  ingressClassName: alb
  rules:
    - host: api.example.com
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: api-service
                port:
                  number: 80
```

### AWS Shield Advanced

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: shield-protected-ingress
  annotations:
    alb.ingress.kubernetes.io/scheme: internet-facing
    alb.ingress.kubernetes.io/target-type: ip

    # Enable Shield Advanced protection
    alb.ingress.kubernetes.io/shield-advanced-protection: "true"

spec:
  ingressClassName: alb
  rules:
    - host: critical-app.example.com
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: critical-service
                port:
                  number: 80
```

## Actualizaciones de versión destacadas

- **v2.16.0 (2025-11-20):** ALB Target Optimizer y grupos de destino ponderados de NLB. Target Optimizer requiere su agente de control de destinos y su configuración; no se habilita simplemente con instalar LBC.
- **v2.17.0 (2025-12-19):** compatibilidad con Global Accelerator mediante el único CRD `GlobalAccelerator` de `aga.k8s.aws/v1beta1`, con listeners, grupos de endpoints y endpoints anidados; Gateway API alcanza el estado de candidato a versión GA. Global Accelerator requiere permisos IAM adicionales y configuración de la característica.
- **v3.5.0 (2026-08-03):** conformidad con Gateway API v1.6.0 y compatibilidad estable con v1 TCPRoute/UDPRoute. Los recursos de configuración de Gateway de LBC usan `gateway.k8s.aws/v1`; la versión v1beta1 que sigue ofreciéndose está obsoleta.
- **v3.6.0 (2026-10-05):** la base de CRD de Gateway API se mantiene en v1.6.0 y la versión recomienda aplicar los CRD de LBC más recientes proporcionados por AWS antes de actualizar. Añade el registro IP basado en Pod-AZ, opcional, para TargetGroupBinding entre cuentas, así como la anotación Ingress `frontend-nlb-status-only`.

La versión actual v3.6 admite la configuración QUIC/TCP_QUIC y la validación JWT de ALB. Son características distintas con restricciones específicas de protocolo. La validación JWT solo funciona con HTTPS y su JSON usa **`jwksEndpoint`**, no `jwksUri`. Añada lo siguiente a las anotaciones de un Ingress HTTPS que tenga un certificado válido, un endpoint JWKS de confianza accesible y un emisor/declaraciones revisados:

```yaml
alb.ingress.kubernetes.io/jwt-validation: >-
  {"issuer":"https://accounts.example.com","jwksEndpoint":"https://accounts.example.com/.well-known/jwks.json"}
```

Este es un fragmento de anotación, no un objeto de Kubernetes completo. Valide la audiencia y las demás declaraciones requeridas por la aplicación, en lugar de suponer que la validación de la firma basta para autorizar el acceso. Consulte la [guía de Gateway API](./04-gateway-api.md) para ver la configuración de Gateway correspondiente.

## Referencia de anotaciones

### Anotaciones de Ingress para ALB

| Anotación | Descripción | Valor predeterminado |
|------------|-------------|---------|
| `alb.ingress.kubernetes.io/scheme` | internet-facing o internal | internal |
| `alb.ingress.kubernetes.io/target-type` | ip o instance | instance |
| `alb.ingress.kubernetes.io/subnets` | ID o nombres de subredes | Detección automática |
| `alb.ingress.kubernetes.io/security-groups` | ID de grupos de seguridad | Creación automática |
| `alb.ingress.kubernetes.io/listen-ports` | JSON de puertos de escucha | HTTP 80, o HTTPS 443 si se especifica certificate-arn |
| `alb.ingress.kubernetes.io/certificate-arn` | ARN del certificado de ACM | - |
| `alb.ingress.kubernetes.io/ssl-redirect` | Puerto de redirección SSL | - |
| `alb.ingress.kubernetes.io/ssl-policy` | Política SSL | ELBSecurityPolicy-2016-08 |
| `alb.ingress.kubernetes.io/healthcheck-path` | Ruta de comprobación de estado | / |
| `alb.ingress.kubernetes.io/healthcheck-port` | Puerto de comprobación de estado | traffic-port |
| `alb.ingress.kubernetes.io/healthcheck-protocol` | Protocolo de comprobación de estado | HTTP |
| `alb.ingress.kubernetes.io/healthcheck-interval-seconds` | Intervalo de comprobación de estado | 15 |
| `alb.ingress.kubernetes.io/healthcheck-timeout-seconds` | Tiempo de espera de comprobación de estado | 5 |
| `alb.ingress.kubernetes.io/healthy-threshold-count` | Umbral de estado saludable | 2 |
| `alb.ingress.kubernetes.io/unhealthy-threshold-count` | Umbral de estado no saludable | 2 |
| `alb.ingress.kubernetes.io/group.name` | Nombre del grupo Ingress | - |
| `alb.ingress.kubernetes.io/group.order` | Prioridad dentro del grupo | 0 |
| `alb.ingress.kubernetes.io/ip-address-type` | ipv4 o dualstack | ipv4 |
| `alb.ingress.kubernetes.io/load-balancer-attributes` | Atributos del LB | - |
| `alb.ingress.kubernetes.io/target-group-attributes` | Atributos del grupo de destino | - |
| `alb.ingress.kubernetes.io/tags` | Etiquetas de recursos | - |
| `alb.ingress.kubernetes.io/wafv2-acl-arn` | ARN de WebACL de WAF v2 | - |
| `alb.ingress.kubernetes.io/shield-advanced-protection` | Protección de Shield | false |
| `alb.ingress.kubernetes.io/auth-type` | Tipo de autenticación (none, cognito, oidc) | none |

### Anotaciones de Service para NLB

| Anotación | Descripción | Valor predeterminado |
|------------|-------------|---------|
| `service.beta.kubernetes.io/aws-load-balancer-type` | external (NLB) o nlb | - |
| `service.beta.kubernetes.io/aws-load-balancer-nlb-target-type` | ip o instance | instance |
| `service.beta.kubernetes.io/aws-load-balancer-scheme` | internet-facing o internal | internal |
| `service.beta.kubernetes.io/aws-load-balancer-subnets` | ID de subredes | Detección automática |
| `service.beta.kubernetes.io/aws-load-balancer-ssl-cert` | ARN del certificado de ACM | - |
| `service.beta.kubernetes.io/aws-load-balancer-ssl-ports` | Puertos con SSL habilitado | - |
| `service.beta.kubernetes.io/aws-load-balancer-ssl-negotiation-policy` | Política SSL | - |
| `service.beta.kubernetes.io/aws-load-balancer-backend-protocol` | Protocolo del backend | - |
| `service.beta.kubernetes.io/aws-load-balancer-proxy-protocol` | Proxy Protocol | - |
| `service.beta.kubernetes.io/aws-load-balancer-cross-zone-load-balancing-enabled` | Obsoleta; use aws-load-balancer-attributes | false |
| `service.beta.kubernetes.io/aws-load-balancer-healthcheck-protocol` | Protocolo de comprobación de estado | TCP |
| `service.beta.kubernetes.io/aws-load-balancer-healthcheck-path` | Ruta de comprobación de estado | - |
| `service.beta.kubernetes.io/aws-load-balancer-healthcheck-port` | Puerto de comprobación de estado | - |
| `service.beta.kubernetes.io/aws-load-balancer-attributes` | Atributos del LB | - |
| `service.beta.kubernetes.io/aws-load-balancer-target-group-attributes` | Atributos del grupo de destino | - |
| `service.beta.kubernetes.io/aws-load-balancer-security-groups` | Grupos de seguridad | Creación automática |

## Prácticas recomendadas para EKS

### 1. Etiquetado de subredes

Las etiquetas de función son una forma clara de seleccionar las subredes públicas/privadas previstas. En LBC autoadministrado v2.12.1 y posteriores, si no hay subredes con etiquetas de función coincidentes, el comportamiento predeterminado `SubnetDiscoveryByReachability` puede clasificarlas a partir de las tablas de rutas. También se pueden especificar explícitamente los ID de subred o usar filtros de etiquetas de IngressClassParams. EKS Auto Mode sigue exigiendo las etiquetas de subred documentadas. Compruebe el filtrado de etiquetas del clúster, las IP disponibles y que haya una subred apta por cada zona de disponibilidad seleccionada; un ALB normal requiere al menos dos zonas de disponibilidad. Etiquetar una subred no cambia su tabla de rutas ni la convierte en pública.

```bash
# Public subnets (for internet-facing ALB/NLB)
aws ec2 create-tags \
  --resources subnet-xxx \
  --tags Key=kubernetes.io/role/elb,Value=1

# Private subnets (for internal ALB/NLB)
aws ec2 create-tags \
  --resources subnet-yyy \
  --tags Key=kubernetes.io/role/internal-elb,Value=1

# Cluster-specific tag (optional)
aws ec2 create-tags \
  --resources subnet-xxx subnet-yyy \
  --tags Key=kubernetes.io/cluster/my-cluster,Value=shared
```

### 2. Administración de grupos de seguridad

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: secure-ingress
  annotations:
    alb.ingress.kubernetes.io/scheme: internet-facing
    alb.ingress.kubernetes.io/target-type: ip

    # Explicit security group specification
    alb.ingress.kubernetes.io/security-groups: sg-alb-external

    # Configure approved inbound sources on this explicit security group.
    # inbound-cidrs is ignored when security-groups is specified.

    # Additional security groups (for backend communication)
    alb.ingress.kubernetes.io/manage-backend-security-group-rules: "true"

spec:
  ingressClassName: alb
  rules:
    - host: api.example.com
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: api-service
                port:
                  number: 80
```

### 3. Optimización de costos

IngressGroup comparte un ALB y su espacio de reglas. Úselo únicamente dentro de un límite de confianza: un usuario capaz de crear un Ingress que se una al grupo puede afectar el enrutamiento y la prioridad. Aplique controles RBAC o de admisión y revise la configuración de anotaciones combinadas o exclusivas. La pertenencia a un grupo no es una característica de aislamiento entre espacios de nombres ni una garantía incondicional de ahorro de costos.

```yaml
# Share ALB using Ingress groups
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: app1-ingress
  annotations:
    alb.ingress.kubernetes.io/group.name: shared-alb
    alb.ingress.kubernetes.io/group.order: "1"
spec:
  ingressClassName: alb
  rules:
    - host: app1.example.com
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: app1
                port:
                  number: 80
---
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: app2-ingress
  annotations:
    alb.ingress.kubernetes.io/group.name: shared-alb
    alb.ingress.kubernetes.io/group.order: "2"
spec:
  ingressClassName: alb
  rules:
    - host: app2.example.com
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: app2
                port:
                  number: 80
```

### 4. Configuración de alta disponibilidad

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: ha-ingress
  annotations:
    alb.ingress.kubernetes.io/scheme: internet-facing
    alb.ingress.kubernetes.io/target-type: ip

    # Specify subnets in 3+ AZs
    alb.ingress.kubernetes.io/subnets: subnet-az-a,subnet-az-b,subnet-az-c

    # ALB cross-zone is enabled at the load-balancer level.
    # Review target-group overrides separately.

    # Health check optimization
    alb.ingress.kubernetes.io/healthcheck-interval-seconds: "10"
    alb.ingress.kubernetes.io/healthy-threshold-count: "2"
    alb.ingress.kubernetes.io/unhealthy-threshold-count: "2"

    # Draining timeout
    alb.ingress.kubernetes.io/target-group-attributes: deregistration_delay.timeout_seconds=30

spec:
  ingressClassName: alb
  rules:
    - host: api.example.com
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: api-service
                port:
                  number: 80
```

## Solución de problemas

Establezca las variables con nombre que aparecen a continuación a partir del inventario real de espacios de nombres y recursos. Inspeccione el motivo del evento o error del controlador antes de cambiar la infraestructura. La comprobación de estado opcional con exec presupone que la imagen de la aplicación contiene curl; de lo contrario, use un contenedor de diagnóstico aprobado. Proteja los registros y las credenciales al recopilar evidencias. Un 502 puede deberse a un restablecimiento de conexión, una respuesta malformada o problemas de TLS; inspeccione los detalles de error de los registros de acceso de ALB en lugar de suponer que todos los destinos no saludables producen el mismo estado HTTP.

### Problemas comunes

#### 1. No se crea el ALB

```bash
# Check controller logs
kubectl logs -n kube-system -l app.kubernetes.io/name=aws-load-balancer-controller

# Check Ingress events
kubectl describe ingress "$INGRESS_NAME" -n "$NAMESPACE"

# Common causes:
# - Insufficient IAM permissions
# - Missing subnet tags
# - IngressClass not specified
```

#### 2. Destinos no saludables

```bash
# Check Target Group status
aws elbv2 describe-target-health \
  --target-group-arn "$TARGET_GROUP_ARN"

# Check Pod logs
kubectl logs "$POD_NAME" -n "$NAMESPACE" --tail=100

# Test health check endpoint
kubectl exec "$POD_NAME" -n "$NAMESPACE" -- curl --fail --max-time 5 http://localhost:8080/health

# Check security groups
aws ec2 describe-security-groups --group-ids "$SECURITY_GROUP_ID"
```

#### 3. 502 Bad Gateway

```bash
# Root cause analysis:
# 1. Pod not ready
kubectl get pods -l app=my-app

# 2. Target Group draining
aws elbv2 describe-target-health --target-group-arn "$TARGET_GROUP_ARN"

# 3. Health check failure
# - Verify health check path
# - Adjust health check timeout

# 4. Security group rules
# - Verify ALB -> Pod communication allowed
```

#### 4. Problemas con el certificado SSL

```bash
# Check ACM certificate status
aws acm describe-certificate --certificate-arn "$ACM_CERTIFICATE_ARN"

# Verify certificate is ISSUED status
# Check domain validation completed

# Verify region (must be same region as ALB)
```

### Comandos de depuración

```bash
# Controller detailed logs
kubectl logs -n kube-system deployment/aws-load-balancer-controller -f

# Ingress status check
kubectl get ingress -o wide
kubectl describe ingress "$INGRESS_NAME" -n "$NAMESPACE"

# Service status check
kubectl get svc -o wide
kubectl describe svc "$SERVICE_NAME" -n "$NAMESPACE"

# TargetGroupBinding status check
kubectl get targetgroupbindings -A
kubectl describe targetgroupbinding "$TGB_NAME" -n "$NAMESPACE"

# AWS resource check
aws elbv2 describe-load-balancers --query 'LoadBalancers[?contains(LoadBalancerName, `k8s`)]'
aws elbv2 describe-target-groups --query 'TargetGroups[?contains(TargetGroupName, `k8s`)]'
```

---

## Referencias

- [Documentación de AWS Load Balancer Controller](https://kubernetes-sigs.github.io/aws-load-balancer-controller/)
- [Repositorio de GitHub](https://github.com/kubernetes-sigs/aws-load-balancer-controller)
- [Guía del usuario de EKS](https://docs.aws.amazon.com/eks/latest/userguide/aws-load-balancer-controller.html)
- [Documentación de ALB](https://docs.aws.amazon.com/elasticloadbalancing/latest/application/)
- [Documentación de NLB](https://docs.aws.amazon.com/elasticloadbalancing/latest/network/)

- [Versión v3.6.0 de LBC](https://github.com/kubernetes-sigs/aws-load-balancer-controller/releases/tag/v3.6.0)
- [Anotaciones de Ingress de LBC v3.6.0](https://github.com/kubernetes-sigs/aws-load-balancer-controller/blob/v3.6.0/docs/guide/ingress/annotations.md)
- [Anotaciones de Service de LBC v3.6.0](https://github.com/kubernetes-sigs/aws-load-balancer-controller/blob/v3.6.0/docs/guide/service/annotations.md)
- [Propiedad de TargetGroupBinding](https://github.com/kubernetes-sigs/aws-load-balancer-controller/blob/v3.6.0/docs/guide/targetgroupbinding/targetgroupbinding.md)
- [Detección de subredes](https://github.com/kubernetes-sigs/aws-load-balancer-controller/blob/v3.6.0/docs/deploy/subnet_discovery.md)
- [Pesos de listeners y conexiones de NLB](https://docs.aws.amazon.com/elasticloadbalancing/latest/network/load-balancer-listeners.html)
- [Requisitos previos para la autenticación de ALB](https://docs.aws.amazon.com/elasticloadbalancing/latest/application/listener-authenticate-users.html)
- [NLB de EKS Auto Mode](https://docs.aws.amazon.com/eks/latest/userguide/auto-configure-nlb.html)
