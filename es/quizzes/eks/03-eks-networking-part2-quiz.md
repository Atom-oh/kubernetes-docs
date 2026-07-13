# Quiz de networking de EKS - Parte 2

Este quiz evalúa tu comprensión de conceptos avanzados de networking en Amazon EKS, AWS Load Balancer Controller, recursos Ingress, service mesh y seguridad de red.

## Preguntas de opción múltiple

### 1. ¿Qué tipo de load balancer de AWS aprovisiona AWS Load Balancer Controller de forma predeterminada para recursos Kubernetes Ingress?

A. Classic Load Balancer (CLB) B. Network Load Balancer (NLB) C. Application Load Balancer (ALB) D. Gateway Load Balancer (GWLB)

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: C. Application Load Balancer (ALB)**

**Explicación:** AWS Load Balancer Controller aprovisiona un Application Load Balancer (ALB) de forma predeterminada para recursos Kubernetes Ingress. ALB es un load balancer de capa 7 que maneja tráfico HTTP/HTTPS y proporciona características como routing basado en rutas, routing basado en hosts y terminación TLS para cumplir con los requisitos de los recursos Ingress.

**Características clave:**

1. **Routing basado en rutas**: ALB puede enrutar tráfico a diferentes services según las rutas URL, lo que lo hace adecuado para implementar reglas de routing basado en rutas en Ingress.
2. **Routing basado en hosts**: Se pueden manejar varios dominios con un único ALB, compatible con Ingress con múltiples reglas de host.
3. **Terminación TLS**: ALB puede administrar certificados SSL/TLS y terminar tráfico HTTPS.
4. **Soporte para WebSockets**: ALB admite el protocolo WebSockets, adecuado para aplicaciones en tiempo real.
5. **Integración de autenticación**: Puede integrarse con Amazon Cognito u OIDC para proporcionar autenticación a nivel de aplicación.

**Ejemplo de configuración:**

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: example-ingress
  annotations:
    kubernetes.io/ingress.class: alb
    alb.ingress.kubernetes.io/scheme: internet-facing
    alb.ingress.kubernetes.io/target-type: ip
spec:
  rules:
  - host: example.com
    http:
      paths:
      - path: /api
        pathType: Prefix
        backend:
          service:
            name: api-service
            port:
              number: 80
      - path: /
        pathType: Prefix
        backend:
          service:
            name: frontend-service
            port:
              number: 80
```

**Anotaciones clave:**

* `kubernetes.io/ingress.class: alb`: Especifica el uso de ALB Ingress Controller
* `alb.ingress.kubernetes.io/scheme: internet-facing`: Crea un ALB orientado a internet
* `alb.ingress.kubernetes.io/target-type: ip`: Usa IPs de pods como targets (en lugar de instance)
* `alb.ingress.kubernetes.io/listen-ports: '[{"HTTP": 80}, {"HTTPS": 443}]'`: Configura los puertos listener
* `alb.ingress.kubernetes.io/certificate-arn: arn:aws:acm:region:account-id:certificate/certificate-id`: Especifica el certificado SSL

Problemas con las otras opciones:

* **A. Classic Load Balancer (CLB)**: AWS Load Balancer Controller no usa CLB para recursos Ingress. CLB se considera un load balancer legacy.
* **B. Network Load Balancer (NLB)**: NLB se usa principalmente para Service de tipo LoadBalancer y no se usa de forma predeterminada para recursos Ingress.
* **D. Gateway Load Balancer (GWLB)**: GWLB es para appliances virtuales de red y no se usa con recursos Kubernetes Ingress.

</details>

### 2. ¿Qué anotación se debe agregar a un recurso Ingress en Amazon EKS para crear un Application Load Balancer interno usando AWS Load Balancer Controller?

A. `service.beta.kubernetes.io/aws-load-balancer-internal: "true"` B. `alb.ingress.kubernetes.io/scheme: internal` C. `kubernetes.io/ingress.class: internal-alb` D. `aws-load-balancer-type: internal`

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B. `alb.ingress.kubernetes.io/scheme: internal`**

**Explicación:** Para crear un Application Load Balancer interno usando AWS Load Balancer Controller en Amazon EKS, se debe agregar la anotación `alb.ingress.kubernetes.io/scheme: internal` al recurso Ingress. Esta anotación configura el ALB para que sea accesible solo dentro de la VPC.

**Ejemplo de configuración de ALB interno:**

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: internal-ingress
  annotations:
    kubernetes.io/ingress.class: alb
    alb.ingress.kubernetes.io/scheme: internal
spec:
  rules:
  - host: internal.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: internal-service
            port:
              number: 80
```

**Consideraciones clave:**

1.  **Selección de subnets**: Los ALB internos se crean en subnets privadas. Las subnets se pueden especificar explícitamente:

    ```yaml
    alb.ingress.kubernetes.io/subnets: subnet-0123456789abcdef0,subnet-0123456789abcdef1
    ```
2.  **Security Groups**: Se pueden aplicar security groups específicos a ALB internos:

    ```yaml
    alb.ingress.kubernetes.io/security-groups: sg-0123456789abcdef0
    ```
3.  **Restricción de CIDR entrante**: El acceso se puede permitir solo desde bloques CIDR específicos:

    ```yaml
    alb.ingress.kubernetes.io/inbound-cidrs: 10.0.0.0/16,192.168.0.0/16
    ```
4.  **DNS interno**: El ALB interno se puede integrar con zonas hosted privadas de Route 53 dentro de la VPC:

    ```yaml
    alb.ingress.kubernetes.io/load-balancer-attributes: routing.http.drop_invalid_header_fields.enabled=true,access_logs.s3.enabled=true
    ```

**Casos de uso para ALB interno:**

* Comunicación interna entre microservices
* Services de API backend
* Interfaces administrativas
* Entornos de desarrollo y prueba
* Workloads con requisitos regulatorios

**Verificar la instalación de AWS Load Balancer Controller:**

```bash
kubectl get deployment -n kube-system aws-load-balancer-controller
```

Problemas con las otras opciones:

* **A. `service.beta.kubernetes.io/aws-load-balancer-internal: "true"`**: Esta anotación se usa para Service de tipo LoadBalancer y no aplica a recursos Ingress.
* **C. `kubernetes.io/ingress.class: internal-alb`**: El ingress.class correcto es 'alb'; 'internal-alb' no es un valor válido.
* **D. `aws-load-balancer-type: internal`**: Esta anotación no existe.

</details>

### 3. ¿Qué anotación se usa para configurar AWS Load Balancer Controller para usar IPs de pods directamente como targets en Amazon EKS?

A. `alb.ingress.kubernetes.io/target-type: pod` B. `alb.ingress.kubernetes.io/target-type: ip` C. `service.beta.kubernetes.io/aws-load-balancer-target-type: ip` D. `aws-load-balancer-target-node-labels: ip-mode=true`

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B. `alb.ingress.kubernetes.io/target-type: ip`**

**Explicación:** Para configurar AWS Load Balancer Controller para usar IPs de pods directamente como targets en Amazon EKS, se debe usar la anotación `alb.ingress.kubernetes.io/target-type: ip`. Esta configuración permite que el load balancer enrute el tráfico directamente a las IPs de los pods en lugar de a las IPs de los nodes.

**Opciones de tipo de target:**

1. **instance**: (predeterminado) Enruta tráfico usando la IP del node y NodePort.
2. **ip**: Enruta tráfico directamente a los pods usando la IP del pod y el puerto del container.

**Ejemplo de configuración de modo IP:**

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: example-ingress
  annotations:
    kubernetes.io/ingress.class: alb
    alb.ingress.kubernetes.io/target-type: ip
spec:
  rules:
  - http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: example-service
            port:
              number: 80
```

**Ventajas del modo IP:**

1. **Resiliencia ante fallos de node**: Incluso si un node falla, el tráfico continúa enrutándose a pods en otros nodes.
2. **Routing directo**: El tráfico se entrega directamente a los pods sin saltos adicionales a través de NodePort.
3. **Compatibilidad con Fargate**: Requerido para pods que se ejecutan en AWS Fargate.
4. **Integración de Security Group**: Los security groups se pueden aplicar a nivel de pod.

**Requisitos del modo IP:**

1. **VPC CNI**: Se requiere el plugin Amazon VPC CNI.
2. **Configuración de subnets**: Las subnets donde se ejecutan los pods deben poder enrutar hacia las subnets del load balancer.
3. **Reglas de Security Group**: El security group del load balancer debe permitir tráfico hacia las IPs de los pods.

**Comparación de modo IP vs modo Instance:**

| Característica  | Modo IP            | Modo Instance                       |
| --------------- | ------------------ | ----------------------------------- |
| Target          | IP del Pod         | IP del Node                         |
| Puerto          | Puerto del container | NodePort                          |
| Ruta de tráfico | LB -> Pod          | LB -> Node -> Pod                   |
| En fallo de Node | Sin impacto       | Pods en ese node inaccesibles       |
| Rendimiento     | Mejor rendimiento  | Ligero overhead por salto adicional |
| Soporte Fargate | Compatible         | No compatible                       |

**Opciones de configuración adicionales:**

```yaml
# Target group attributes setting
alb.ingress.kubernetes.io/target-group-attributes: deregistration_delay.timeout_seconds=30,stickiness.enabled=true

# Health check settings
alb.ingress.kubernetes.io/healthcheck-path: /health
alb.ingress.kubernetes.io/healthcheck-interval-seconds: '15'
alb.ingress.kubernetes.io/healthcheck-timeout-seconds: '5'
alb.ingress.kubernetes.io/success-codes: '200'
alb.ingress.kubernetes.io/healthy-threshold-count: '2'
alb.ingress.kubernetes.io/unhealthy-threshold-count: '2'
```

Problemas con las otras opciones:

* **A. `alb.ingress.kubernetes.io/target-type: pod`**: El valor correcto es 'ip', no 'pod'.
* **C. `service.beta.kubernetes.io/aws-load-balancer-target-type: ip`**: Esta anotación se usa para Service de tipo LoadBalancer y no aplica a recursos Ingress.
* **D. `aws-load-balancer-target-node-labels: ip-mode=true`**: Esta anotación no existe.

</details>

### 4. ¿Qué anotación se usa para integrar Kubernetes Service con AWS PrivateLink para crear un VPC endpoint service en Amazon EKS?

A. `service.beta.kubernetes.io/aws-load-balancer-type: nlb` B. `service.beta.kubernetes.io/aws-load-balancer-private-link: "true"` C. `service.beta.kubernetes.io/aws-load-balancer-type: nlb-ip` D. `service.beta.kubernetes.io/aws-vpc-endpoint-service: "true"`

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: C. `service.beta.kubernetes.io/aws-load-balancer-type: nlb-ip`**

**Explicación:** Para integrar Kubernetes Service con AWS PrivateLink para crear un VPC endpoint service en Amazon EKS, se debe usar la anotación `service.beta.kubernetes.io/aws-load-balancer-type: nlb-ip`. Esta anotación crea un Network Load Balancer (NLB) en modo IP, que es un requisito previo para integrarse con AWS PrivateLink.

**Pasos de configuración de VPC Endpoint Service:**

1. **Crear Kubernetes Service con modo NLB-IP:**

```yaml
apiVersion: v1
kind: Service
metadata:
  name: privatelink-service
  annotations:
    service.beta.kubernetes.io/aws-load-balancer-type: nlb-ip
    service.beta.kubernetes.io/aws-load-balancer-internal: "true"
spec:
  type: LoadBalancer
  ports:
  - port: 80
    targetPort: 8080
  selector:
    app: my-app
```

2. **Crear VPC Endpoint Service usando AWS CLI:**

```bash
# Get NLB ARN
NLB_ARN=$(aws elbv2 describe-load-balancers --names $(kubectl get svc privatelink-service -o jsonpath='{.status.loadBalancer.ingress[0].hostname}' | cut -d- -f1) --query 'LoadBalancers[0].LoadBalancerArn' --output text)

# Create VPC endpoint service
aws ec2 create-vpc-endpoint-service-configuration \
  --network-load-balancer-arns $NLB_ARN \
  --acceptance-required \
  --private-dns-name service.example.com
```

3. **Configurar la allow list de VPC Endpoint Service:**

```bash
aws ec2 modify-vpc-endpoint-service-permissions \
  --service-id vpce-svc-0123456789abcdef0 \
  --add-allowed-principals arn:aws:iam::111122223333:root
```

**Consideraciones clave:**

1. **Requisito de NLB interno**: PrivateLink requiere un NLB interno, por lo que también se necesita la anotación `service.beta.kubernetes.io/aws-load-balancer-internal: "true"`.
2. **Importancia del modo IP**: El modo NLB-IP proporciona resiliencia ante fallos de node usando IPs de pods directamente como targets.
3. **Resolución de nombres de Service**: Los nombres de DNS privados se pueden configurar para simplificar la resolución de nombres de service dentro de la VPC.
4. **Control de acceso**: El flag `acceptance-required` se puede usar para aprobar manualmente solicitudes de conexión de endpoint.
5. **Network ACLs y Security Groups**: Asegúrate de que las reglas adecuadas de network ACL y security group estén configuradas.

**Beneficios de la integración con PrivateLink:**

* **Seguridad mejorada**: El tráfico permanece dentro de la red de AWS sin atravesar internet público.
* **Compliance**: Cumple requisitos de soberanía de datos y compliance.
* **Networking simplificado**: Se puede acceder a los services sin VPC peering, Transit Gateway ni conexiones VPN.
* **Escalabilidad**: Se puede acceder a los services desde miles de VPCs.

**Configuración del lado del cliente:**

```bash
# Create VPC endpoint
aws ec2 create-vpc-endpoint \
  --vpc-id vpc-0123456789abcdef0 \
  --service-name com.amazonaws.vpce.us-east-1.vpce-svc-0123456789abcdef0 \
  --vpc-endpoint-type Interface \
  --subnet-ids subnet-0123456789abcdef0 subnet-0123456789abcdef1 \
  --security-group-ids sg-0123456789abcdef0
```

Problemas con las otras opciones:

* **A. `service.beta.kubernetes.io/aws-load-balancer-type: nlb`**: Esta anotación crea un NLB en modo instance y no está optimizada para la integración con PrivateLink.
* **B. `service.beta.kubernetes.io/aws-load-balancer-private-link: "true"`**: Esta anotación no existe.
* **D. `service.beta.kubernetes.io/aws-vpc-endpoint-service: "true"`**: Esta anotación no existe.

</details>

### 5. ¿Qué componente adicional se puede usar con Amazon VPC CNI para implementar recursos Kubernetes NetworkPolicy en Amazon EKS?

A. AWS Network Firewall B. Calico C. AWS Security Groups for Pods D. VPC Flow Logs

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B. Calico**

**Explicación:** Calico es el componente adicional que se puede usar con Amazon VPC CNI para implementar recursos Kubernetes NetworkPolicy en Amazon EKS. Calico es una solución open-source de networking y seguridad de red que admite la API Kubernetes NetworkPolicy y funciona junto con Amazon VPC CNI para aplicar políticas de red detalladas en clústeres EKS.

**Instalación y configuración de Calico:**

1. **Instalar Calico:**

```bash
kubectl apply -f https://raw.githubusercontent.com/aws/amazon-vpc-cni-k8s/master/config/master/calico-operator.yaml
kubectl apply -f https://raw.githubusercontent.com/aws/amazon-vpc-cni-k8s/master/config/master/calico-crs.yaml
```

2. **Verificar la instalación:**

```bash
kubectl get pods -n calico-system
```

3. **Ejemplo básico de NetworkPolicy:**

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny
  namespace: default
spec:
  podSelector: {}
  policyTypes:
  - Ingress
  - Egress
```

**Características clave de Calico:**

1. **Soporte de Kubernetes NetworkPolicy**: Implementa completamente la API estándar Kubernetes NetworkPolicy.
2. **Características de políticas extendidas**: Proporciona políticas de red avanzadas más allá de Kubernetes NetworkPolicy mediante recursos personalizados como GlobalNetworkPolicy y NetworkSet de Calico.
3. **Control detallado**: Puede filtrar tráfico según protocolos, puertos, bloques CIDR, service accounts, etc.
4. **Logging y monitoreo**: Puede registrar y monitorear violaciones de políticas de red.
5. **Protección de Host Endpoint**: Puede aplicar políticas de red a los propios nodes de Kubernetes.

**Ejemplo de política avanzada de Calico:**

```yaml
# GlobalNetworkPolicy example (cluster-wide policy)
apiVersion: projectcalico.org/v3
kind: GlobalNetworkPolicy
metadata:
  name: allow-cluster-internal-traffic
spec:
  selector: all()
  types:
  - Ingress
  - Egress
  ingress:
  - action: Allow
    source:
      selector: all()
  egress:
  - action: Allow
    destination:
      selector: all()

# Restrict access to specific IP ranges
apiVersion: projectcalico.org/v3
kind: NetworkSet
metadata:
  name: external-services
spec:
  nets:
  - 203.0.113.0/24
  - 198.51.100.0/24
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-external-services
  namespace: app
spec:
  podSelector:
    matchLabels:
      role: frontend
  policyTypes:
  - Egress
  egress:
  - to:
    - namespaceSelector:
        matchLabels:
          kubernetes.io/metadata.name: kube-system
    ports:
    - protocol: UDP
      port: 53
    - protocol: TCP
      port: 53
  - to:
    - ipBlock:
        cidr: 203.0.113.0/24
    - ipBlock:
        cidr: 198.51.100.0/24
```

**Integración de Amazon VPC CNI y Calico:**

1. **Modo de red**: Cuando se usa con Amazon VPC CNI, Calico opera en modo solo políticas en lugar de modo overlay.
2. **Rendimiento**: Mantiene el rendimiento de networking nativo de VPC de Amazon VPC CNI mientras aprovecha las características de políticas de red de Calico.
3. **Compatibilidad**: Calico es compatible con todas las características de Amazon VPC CNI (delegación de prefijos, networking personalizado, etc.).
4. **Actualizaciones**: Calico y Amazon VPC CNI se pueden actualizar de forma independiente.

**Buenas prácticas:**

* Comienza con una política default deny y permite explícitamente solo las comunicaciones necesarias.
* Define políticas claras para la comunicación entre namespaces.
* Prueba las políticas en modo logging antes de aplicarlas.
* Permite siempre la comunicación con componentes esenciales del clúster.
* Revisa y actualiza las políticas regularmente.

Problemas con las otras opciones:

* **A. AWS Network Firewall**: AWS Network Firewall es un servicio de firewall a nivel de VPC y no tiene integración directa con Kubernetes NetworkPolicy.
* **C. AWS Security Groups for Pods**: Security Groups for Pods es una característica que aplica security groups de AWS a pods, pero no implementa la API Kubernetes NetworkPolicy.
* **D. VPC Flow Logs**: VPC Flow Logs es una herramienta para monitorear tráfico de red y no aplica políticas de red.

</details>

## Preguntas de respuesta corta

### 6. ¿Qué anotación se usa para asignar security groups específicos a un Application Load Balancer al crearlo usando AWS Load Balancer Controller en Amazon EKS?

<details>

<summary>Mostrar respuesta</summary>

**Respuesta:** `alb.ingress.kubernetes.io/security-groups: sg-xxxx,sg-yyyy`

**Explicación detallada:**

Al crear un Application Load Balancer (ALB) usando AWS Load Balancer Controller, la anotación `alb.ingress.kubernetes.io/security-groups` se puede usar para asignar security groups específicos. Esta anotación especifica los IDs de security group que se adjuntarán al ALB, separados por comas.

**Método de implementación:**

1.  **Especificar IDs de Security Group:**

    ```yaml
    apiVersion: networking.k8s.io/v1
    kind: Ingress
    metadata:
      name: example-ingress
      annotations:
        kubernetes.io/ingress.class: alb
        alb.ingress.kubernetes.io/security-groups: sg-0123456789abcdef0,sg-0123456789abcdef1
    spec:
      rules:
      - http:
          paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: example-service
                port:
                  number: 80
    ```
2.  **Especificar nombres de Security Group (método alternativo):**

    ```yaml
    alb.ingress.kubernetes.io/security-groups: my-security-group-name
    ```
3.  **Crear Security Groups automáticamente:**

    ```yaml
    alb.ingress.kubernetes.io/manage-backend-security-group-rules: "true"
    ```

**Consideraciones clave:**

1. **Reglas de Security Group:**
   * Reglas entrantes: Deben permitir el tráfico de clientes (normalmente HTTP/80, HTTPS/443).
   * Reglas salientes: Deben permitir tráfico a los target groups (pods o nodes).
2. **Comportamiento predeterminado:** Cuando no se especifica la anotación, AWS Load Balancer Controller crea automáticamente un security group y configura las reglas necesarias.
3. **Requisitos de permisos:** El IAM role de AWS Load Balancer Controller necesita los siguientes permisos:
   * ec2:CreateSecurityGroup
   * ec2:DeleteSecurityGroup
   * ec2:DescribeSecurityGroups
   * ec2:AuthorizeSecurityGroupIngress
   * ec2:RevokeSecurityGroupIngress
4.  **Administración de Security Group:**

    ```yaml
    # Set controller to manage security group rules
    alb.ingress.kubernetes.io/manage-backend-security-group-rules: "true"
    ```
5.  **Etiquetado:** Se pueden agregar tags a los security groups creados:

    ```yaml
    alb.ingress.kubernetes.io/tags: Environment=prod,Team=devops
    ```

**Buenas prácticas:**

1. **Principio de mínimo privilegio:** Usa reglas de security group restrictivas que permitan solo el tráfico necesario.
2. **Reutilización de Security Group:** Reutiliza los mismos security groups en varios recursos Ingress para simplificar la administración.
3. **Documentación:** Documenta los security groups usados y sus reglas para seguimiento.
4. **Revisión periódica:** Revisa regularmente las reglas de security group para eliminar accesos innecesarios.
5. **Monitoreo:** Monitorea conexiones denegadas para evaluar la efectividad de las reglas de security group.

**Anotaciones relacionadas:**

*   **Restricción de CIDR entrante:**

    ```yaml
    alb.ingress.kubernetes.io/inbound-cidrs: 10.0.0.0/16,192.168.0.0/16
    ```
*   **Tags de Security Group:**

    ```yaml
    alb.ingress.kubernetes.io/load-balancer-attributes: load_balancing.cross_zone.enabled=true
    ```
*   **Política SSL:**

    ```yaml
    alb.ingress.kubernetes.io/ssl-policy: ELBSecurityPolicy-TLS-1-2-2017-01
    ```

Usar AWS Load Balancer Controller permite un control detallado de los security groups de ALB mediante recursos Kubernetes Ingress, lo que ayuda a fortalecer la postura de seguridad de red de tu clúster.

</details>

### 7. ¿Qué anotación se usa para preservar las direcciones IP de cliente al exponer un recurso Kubernetes Service como Network Load Balancer en Amazon EKS?

<details>

<summary>Mostrar respuesta</summary>

**Respuesta:** `service.beta.kubernetes.io/aws-load-balancer-target-group-attributes: preserve_client_ip.enabled=true`

**Explicación detallada:**

Al exponer un recurso Kubernetes Service como Network Load Balancer (NLB) en Amazon EKS, se debe usar la anotación `service.beta.kubernetes.io/aws-load-balancer-target-group-attributes: preserve_client_ip.enabled=true` para preservar las direcciones IP de cliente. Esta configuración hace que el NLB mantenga las direcciones IP originales de los clientes.

**Método de implementación:**

1.  **Configuración básica de Service NLB:**

    ```yaml
    apiVersion: v1
    kind: Service
    metadata:
      name: example-service
      annotations:
        service.beta.kubernetes.io/aws-load-balancer-type: nlb
        service.beta.kubernetes.io/aws-load-balancer-target-group-attributes: preserve_client_ip.enabled=true
    spec:
      type: LoadBalancer
      ports:
      - port: 80
        targetPort: 8080
      selector:
        app: example
    ```
2.  **Uso con NLB en modo IP:**

    ```yaml
    apiVersion: v1
    kind: Service
    metadata:
      name: example-service
      annotations:
        service.beta.kubernetes.io/aws-load-balancer-type: nlb-ip
        service.beta.kubernetes.io/aws-load-balancer-target-group-attributes: preserve_client_ip.enabled=true
    spec:
      type: LoadBalancer
      ports:
      - port: 80
        targetPort: 8080
      selector:
        app: example
    ```

**Importancia de preservar la IP de cliente:**

1. **Seguridad y control de acceso:**
   * Implementar control de acceso basado en IP de cliente
   * Bloquear direcciones IP sospechosas
   * Aplicar rate limiting basado en IP
2. **Logging y auditoría:**
   * Rastrear orígenes de solicitudes
   * Investigar eventos de seguridad
   * Cumplir requisitos de compliance
3. **Características basadas en geolocalización:**
   * Servir contenido específico por región
   * Realizar análisis geográfico

**Cómo funciona:**

1. **Modo Instance (aws-load-balancer-type: nlb):**
   * Para tráfico TCP, la IP de cliente se preserva automáticamente.
   * Para tráfico UDP, se requiere la configuración preserve\_client\_ip.enabled=true.
2. **Modo IP (aws-load-balancer-type: nlb-ip):**
   * Tanto el tráfico TCP como UDP requieren la configuración preserve\_client\_ip.enabled=true.

**Limitaciones y consideraciones:**

1. **Proxy Protocol:** La preservación de IP de cliente se realiza mediante routing directo de paquetes sin usar proxy protocol.
2. **Tipos de Target Group:**
   * Modo Instance: Usa IP del node y NodePort.
   * Modo IP: Usa directamente IP y puerto del pod.
3. **Impacto en el rendimiento:** La preservación de IP de cliente puede generar un ligero overhead de rendimiento.
4. **Compatibilidad:** Algunas aplicaciones legacy pueden no ser compatibles con la preservación de IP de cliente.

**Acceso a la IP de cliente en aplicaciones:**

1.  **Aplicaciones HTTP:**

    ```python
    # Python Flask example
    from flask import Flask, request

    app = Flask(__name__)

    @app.route('/')
    def index():
        client_ip = request.remote_addr
        return f"Your IP address is: {client_ip}"
    ```
2.  **Aplicaciones TCP/UDP:**

    ```go
    // Go example
    package main

    import (
        "fmt"
        "net"
    )

    func handleConnection(conn net.Conn) {
        addr := conn.RemoteAddr().String()
        fmt.Printf("Client connected from: %s\n", addr)
        // ...
    }
    ```

**Anotaciones relacionadas:**

*   **Configuración de NLB interno:**

    ```yaml
    service.beta.kubernetes.io/aws-load-balancer-internal: "true"
    ```
*   **Cross-Zone Load Balancing:**

    ```yaml
    service.beta.kubernetes.io/aws-load-balancer-target-group-attributes: load_balancing.cross_zone.enabled=true
    ```
*   **TCP Connection Keep-Alive:**

    ```yaml
    service.beta.kubernetes.io/aws-load-balancer-target-group-attributes: preserve_client_ip.enabled=true,deregistration_delay.timeout_seconds=30
    ```

La preservación de IP de cliente es importante para diversos propósitos, incluidos seguridad, logging y control de acceso, y se puede configurar fácilmente en clústeres EKS usando la anotación adecuada.

</details>

### 8. ¿Qué anotación se usa para adjuntar AWS WAF (Web Application Firewall) a un recurso Kubernetes Ingress en Amazon EKS?

<details>

<summary>Mostrar respuesta</summary>

**Respuesta:** `alb.ingress.kubernetes.io/wafv2-acl-arn: arn:aws:wafv2:region:account-id:global/webacl/name/id`

**Explicación detallada:**

Para adjuntar AWS WAF (Web Application Firewall) a un recurso Kubernetes Ingress en Amazon EKS, se debe usar la anotación `alb.ingress.kubernetes.io/wafv2-acl-arn`. Esta anotación adjunta un AWS WAF WebACL al Application Load Balancer (ALB) creado por AWS Load Balancer Controller.

**Método de implementación:**

1.  **Crear AWS WAF WebACL:** Primero, crea un WAF WebACL usando AWS Management Console, AWS CLI o AWS CloudFormation.

    ```bash
    # AWS CLI example
    aws wafv2 create-web-acl \
      --name "eks-ingress-protection" \
      --scope "REGIONAL" \
      --default-action Allow={} \
      --visibility-config SampledRequestsEnabled=true,CloudWatchMetricsEnabled=true,MetricName=eks-ingress-protection \
      --region us-west-2
    ```
2.  **Especificar el ARN del WAF WebACL en el recurso Ingress:**

    ```yaml
    apiVersion: networking.k8s.io/v1
    kind: Ingress
    metadata:
      name: example-ingress
      annotations:
        kubernetes.io/ingress.class: alb
        alb.ingress.kubernetes.io/scheme: internet-facing
        alb.ingress.kubernetes.io/wafv2-acl-arn: arn:aws:wafv2:us-west-2:111122223333:regional/webacl/eks-ingress-protection/a1b2c3d4-5678-90ab-cdef
    spec:
      rules:
      - host: example.com
        http:
          paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: example-service
                port:
                  number: 80
    ```

**Características clave de protección de AWS WAF:**

1. **Defensa contra vulnerabilidades web comunes:**
   * Ataques de SQL injection
   * Cross-site scripting (XSS)
   * Ataques de path traversal
   * Command injection
2. **Control de tráfico de bots:**
   * Bloquear bots maliciosos
   * Prevenir scraping
   * Prevenir ataques de credential stuffing
3. **Rate Limiting:**
   * Mitigación de ataques DDoS
   * Prevenir ataques de fuerza bruta
4. **Restricciones geográficas:**
   * Restringir acceso desde países o regiones específicos
5. **Filtrado por reputación de IP:**
   * Bloquear direcciones IP maliciosas conocidas

**Ejemplos de grupos de reglas de AWS WAF:**

1. **Reglas administradas por AWS:**
   * AWS Core rule set (CRS)
   * Reglas de bases de datos SQL
   * Reglas de sistema operativo Linux
   * Reglas de aplicaciones PHP
2.  **Reglas personalizadas:**

    ```json
    {
      "Name": "block-specific-uri-paths",
      "Priority": 1,
      "Action": { "Block": {} },
      "VisibilityConfig": {
        "SampledRequestsEnabled": true,
        "CloudWatchMetricsEnabled": true,
        "MetricName": "block-specific-uri-paths"
      },
      "Statement": {
        "ByteMatchStatement": {
          "SearchString": "/admin",
          "FieldToMatch": { "UriPath": {} },
          "TextTransformations": [
            { "Priority": 0, "Type": "NONE" }
          ],
          "PositionalConstraint": "STARTS_WITH"
        }
      }
    }
    ```

**Monitoreo y logging:**

1.  **Habilitar CloudWatch Logs:**

    ```yaml
    alb.ingress.kubernetes.io/load-balancer-attributes: access_logs.s3.enabled=true,access_logs.s3.bucket=my-alb-logs,access_logs.s3.prefix=ingress-logs
    ```
2.  **Configurar logging de WAF:**

    ```bash
    aws wafv2 put-logging-configuration \
      --logging-configuration ResourceArn=arn:aws:wafv2:us-west-2:111122223333:regional/webacl/eks-ingress-protection/a1b2c3d4-5678-90ab-cdef,LogDestinationConfigs=arn:aws:firehose:us-west-2:111122223333:deliverystream/aws-waf-logs \
      --region us-west-2
    ```

**Requisitos de permisos:**

El IAM role de AWS Load Balancer Controller necesita los siguientes permisos:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "wafv2:AssociateWebACL",
        "wafv2:DisassociateWebACL",
        "wafv2:GetWebACL",
        "wafv2:GetWebACLForResource"
      ],
      "Resource": "*"
    }
  ]
}
```

**Buenas prácticas:**

1. **Defense in Depth:** Usa WAF junto con otros controles de seguridad como seguridad de red, autenticación y autorización.
2. **Actualizaciones periódicas de reglas:** Revisa y actualiza las reglas de WAF regularmente para responder a nuevas amenazas.
3. **Logging y monitoreo:** Analiza los logs de WAF para identificar patrones de ataque y mejorar las reglas.
4. **Pruebas:** Valida las reglas de WAF en entornos de prueba antes de aplicarlas a producción.
5. **Modo Count:** Al desplegar reglas nuevas por primera vez, configúralas en modo count en lugar de block para monitorear falsos positivos.

La integración de AWS WAF con EKS Ingress es una forma poderosa de mejorar la seguridad de las aplicaciones y se puede configurar fácilmente usando la anotación adecuada.

</details>

## Preguntas prácticas

### 9. Escribe un recurso Ingress que cree un Application Load Balancer usando AWS Load Balancer Controller en un clúster Amazon EKS y enrute el tráfico a diferentes services según rutas específicas.

<details>

<summary>Mostrar respuesta</summary>

**Respuesta:** El siguiente es un recurso Ingress que crea un Application Load Balancer usando AWS Load Balancer Controller y enruta el tráfico a diferentes services según rutas específicas:

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: multi-path-ingress
  namespace: default
  annotations:
    kubernetes.io/ingress.class: alb
    alb.ingress.kubernetes.io/scheme: internet-facing
    alb.ingress.kubernetes.io/target-type: ip
    alb.ingress.kubernetes.io/listen-ports: '[{"HTTP": 80}, {"HTTPS": 443}]'
    alb.ingress.kubernetes.io/certificate-arn: arn:aws:acm:region:account-id:certificate/certificate-id
    alb.ingress.kubernetes.io/ssl-redirect: '443'
    alb.ingress.kubernetes.io/healthcheck-path: /health
    alb.ingress.kubernetes.io/success-codes: '200'
    alb.ingress.kubernetes.io/healthcheck-interval-seconds: '15'
    alb.ingress.kubernetes.io/healthcheck-timeout-seconds: '5'
spec:
  rules:
  - host: example.com
    http:
      paths:
      - path: /api
        pathType: Prefix
        backend:
          service:
            name: api-service
            port:
              number: 80
      - path: /admin
        pathType: Prefix
        backend:
          service:
            name: admin-service
            port:
              number: 80
      - path: /
        pathType: Prefix
        backend:
          service:
            name: frontend-service
            port:
              number: 80
```

**Explicación detallada:**

1. **Explicación de componentes del recurso Ingress**:
   * **metadata.annotations**: Especifica opciones de configuración para AWS Load Balancer Controller.
     * `kubernetes.io/ingress.class: alb`: Especifica el uso de AWS Load Balancer Controller.
     * `alb.ingress.kubernetes.io/scheme: internet-facing`: Crea un ALB accesible desde internet.
     * `alb.ingress.kubernetes.io/target-type: ip`: Usa IPs de pods como targets.
     * `alb.ingress.kubernetes.io/listen-ports`: Escucha en los puertos HTTP(80) y HTTPS(443).
     * `alb.ingress.kubernetes.io/certificate-arn`: Especifica el certificado ACM para HTTPS.
     * `alb.ingress.kubernetes.io/ssl-redirect`: Redirige tráfico HTTP a HTTPS.
     * `alb.ingress.kubernetes.io/healthcheck-*`: Configura los ajustes de health check.
   * **spec.rules**: Define reglas de routing basadas en host y ruta.
     * La ruta `/api` se enruta a `api-service`.
     * La ruta `/admin` se enruta a `admin-service`.
     * La ruta `/` (root) se enruta a `frontend-service`.
2.  **Pasos de implementación**:

    a. **Crear los Services requeridos**:

    ```yaml
    # api-service.yaml
    apiVersion: v1
    kind: Service
    metadata:
      name: api-service
    spec:
      ports:
      - port: 80
        targetPort: 8080
      selector:
        app: api
    ---
    # admin-service.yaml
    apiVersion: v1
    kind: Service
    metadata:
      name: admin-service
    spec:
      ports:
      - port: 80
        targetPort: 8080
      selector:
        app: admin
    ---
    # frontend-service.yaml
    apiVersion: v1
    kind: Service
    metadata:
      name: frontend-service
    spec:
      ports:
      - port: 80
        targetPort: 8080
      selector:
        app: frontend
    ```

    b. **Crear Deployments para los Services**:

    ```yaml
    # api-deployment.yaml
    apiVersion: apps/v1
    kind: Deployment
    metadata:
      name: api-deployment
    spec:
      replicas: 2
      selector:
        matchLabels:
          app: api
      template:
        metadata:
          labels:
            app: api
        spec:
          containers:
          - name: api
            image: nginx
            ports:
            - containerPort: 8080
            readinessProbe:
              httpGet:
                path: /health
                port: 8080
    ```

    (Se necesitan configuraciones similares para los deployments de admin y frontend)

    c. **Verificar la instalación de AWS Load Balancer Controller**:

    ```bash
    kubectl get deployment -n kube-system aws-load-balancer-controller
    ```

    d. **Aplicar el recurso Ingress**:

    ```bash
    kubectl apply -f multi-path-ingress.yaml
    ```

    e. **Comprobar el estado de Ingress**:

    ```bash
    kubectl get ingress multi-path-ingress
    ```
3.  **Método de prueba**:

    a. **Configuración de DNS**: Obtén el nombre DNS del ALB creado por Ingress:

    ```bash
    kubectl get ingress multi-path-ingress -o jsonpath='{.status.loadBalancer.ingress[0].hostname}'
    ```

    Configura este nombre DNS como un registro CNAME para `example.com`.

    b. **Probar routing basado en rutas**:

    ```bash
    # Test API service
    curl https://example.com/api

    # Test admin service
    curl https://example.com/admin

    # Test frontend service
    curl https://example.com/
    ```
4.  **Notas y consideraciones**:

    a. **Certificado SSL**: Se requiere un certificado SSL válido para usar HTTPS. Crea un certificado en AWS Certificate Manager (ACM) y especifica el ARN en la anotación.

    b. **Permisos IAM**: AWS Load Balancer Controller necesita permisos IAM adecuados para crear y administrar ALB y recursos relacionados.

    c. **Health Checks**: Cada service debe proporcionar un endpoint de health check (`/health`).

    d. **Configuración de Target Group**: Usar `target-type: ip` significa que las IPs de los pods se usan directamente como targets. Esto proporciona resiliencia ante fallos de node y admite pods Fargate.

    e. **Security Groups**: Si es necesario, se pueden aplicar security groups específicos al ALB:

    ```yaml
    alb.ingress.kubernetes.io/security-groups: sg-0123456789abcdef0
    ```
5.  **Opciones de configuración adicionales**:

    a. **Habilitar Session Stickiness**:

    ```yaml
    alb.ingress.kubernetes.io/target-group-attributes: stickiness.enabled=true,stickiness.lb_cookie.duration_seconds=86400
    ```

    b. **Habilitar Access Logs**:

    ```yaml
    alb.ingress.kubernetes.io/load-balancer-attributes: access_logs.s3.enabled=true,access_logs.s3.bucket=my-alb-logs,access_logs.s3.prefix=ingress-logs
    ```

    c. **Restricciones basadas en IP**:

    ```yaml
    alb.ingress.kubernetes.io/inbound-cidrs: 192.168.0.0/16,10.0.0.0/8
    ```

    d. **Weighted Routing**:

    ```yaml
    alb.ingress.kubernetes.io/actions.weighted-routing: >
      {"Type":"forward","ForwardConfig":{"TargetGroups":[{"ServiceName":"service-v1","ServicePort":"80","Weight":80},{"ServiceName":"service-v2","ServicePort":"80","Weight":20}]}}
    ```

Usar AWS Load Balancer Controller y recursos Ingress permite implementar reglas de routing complejas en clústeres EKS y aprovechar varias características de ALB para mejorar la disponibilidad, escalabilidad y seguridad de las aplicaciones.

</details>

## Preguntas avanzadas

### 10. Explica las consideraciones clave y los cambios de arquitectura de networking al implementar un service mesh (por ejemplo, Istio, AWS App Mesh) en un clúster Amazon EKS. Explica también cómo se integra el service mesh con el modelo de networking predeterminado de EKS.

<details>

<summary>Mostrar respuesta</summary>

**Respuesta:** A continuación se explican las consideraciones clave y los cambios de arquitectura de networking al implementar un service mesh (por ejemplo, Istio, AWS App Mesh) en un clúster Amazon EKS, y cómo se integra el service mesh con el modelo de networking predeterminado de EKS:

### 1. Descripción general de Service Mesh y componentes clave

**¿Qué es un Service Mesh?** Un service mesh es una capa de infraestructura que administra la comunicación entre microservices y proporciona características como service discovery, administración de tráfico, seguridad y observabilidad.

**Componentes clave:**

1. **Data Plane**:
   * Los sidecar proxies (normalmente Envoy) se inyectan en cada pod.
   * Intercepta y procesa todo el tráfico entrante y saliente.
2. **Control Plane**:
   * Administra políticas y configuración.
   * Configura los proxies del data plane.
   * Proporciona service discovery e información de routing.

### 2. Cambios en la arquitectura de networking de EKS

**Modelo de networking predeterminado de EKS:**

* Usa Amazon VPC CNI para asignar direcciones IP de VPC a los pods.
* Los pods se comunican directamente dentro de la VPC.
* Los recursos Kubernetes Service proporcionan service discovery y load balancing.

**Cambios después de introducir Service Mesh:**

1.  **Cambio de flujo de tráfico**:

    ```
    Default EKS: Client -> Service -> Target Pod
    Service Mesh: Client -> Client Sidecar -> Service -> Target Sidecar -> Target Pod
    ```
2. **Topología de red**:
   * Se agregan sidecar containers a cada pod.
   * Las aplicaciones y los sidecars se comunican a través de la red local dentro del pod.
   * La comunicación sidecar-a-sidecar sigue usando VPC CNI.
3. **Asignación de puertos**:
   * Los sidecar proxies usan puertos adicionales (administración, métricas, health checks, etc.).
   * La redirección de puertos ocurre dentro del pod.

### 3. Comparación de las principales opciones de Service Mesh

#### Istio

**Integración de arquitectura:**

```yaml
# Istio sidecar injection example
apiVersion: apps/v1
kind: Deployment
metadata:
  name: example-app
  labels:
    app: example
spec:
  replicas: 3
  selector:
    matchLabels:
      app: example
  template:
    metadata:
      labels:
        app: example
      annotations:
        sidecar.istio.io/inject: "true"  # Automatic sidecar injection
    spec:
      containers:
      - name: example
        image: example:latest
        ports:
        - containerPort: 8080
```

**Características de networking:**

* Administración avanzada de tráfico (weighted routing, canary deployments)
* Circuit breakers e inyección de fallos
* Cifrado service-to-service mediante mTLS
* Control de acceso detallado

**Consideraciones de integración con EKS:**

* Altos requisitos de recursos (especialmente control plane)
* Compatibilidad limitada con Fargate
* Configuración y administración complejas

#### AWS App Mesh

**Integración de arquitectura:**

```yaml
# App Mesh sidecar injection example
apiVersion: apps/v1
kind: Deployment
metadata:
  name: example-app
  labels:
    app: example
spec:
  replicas: 3
  selector:
    matchLabels:
      app: example
  template:
    metadata:
      labels:
        app: example
      annotations:
        appmesh.k8s.aws/mesh: my-mesh  # App Mesh mesh name
        appmesh.k8s.aws/virtualNode: example-vn  # Virtual node name
    spec:
      containers:
      - name: example
        image: example:latest
        ports:
        - containerPort: 8080
```

**Características de networking:**

* Integración fluida con servicios de AWS
* Soporte de mesh entre cuentas e híbrido
* Integración con AWS X-Ray
* Configuración relativamente simple

**Consideraciones de integración con EKS:**

* Excelente integración con servicios de AWS
* Compatible con Fargate
* Algunas características avanzadas pueden ser limitadas

### 4. Consideraciones de networking

#### Impacto en el rendimiento

1. **Latencia**:
   * Ligero aumento de latencia debido a saltos adicionales a través de sidecar proxies (normalmente <10ms)
   *   Técnicas de optimización:

       ```yaml
       # Istio example: Proxy resource optimization
       apiVersion: v1
       kind: ConfigMap
       metadata:
         name: istio-sidecar-injector
         namespace: istio-system
       data:
         values: |-
           pilot:
             resources:
               requests:
                 cpu: 500m
                 memory: 2048Mi
       ```
2. **Uso de recursos**:
   * Overhead adicional de CPU y memoria por pod (normalmente 10-15%)
   * Posible reducción de la densidad de nodes

#### Integración de Network Policy

1. **Relación con Kubernetes NetworkPolicy**:
   * Service mesh proporciona políticas L7, mientras que NetworkPolicy proporciona políticas L3/L4.
   * Ambos tipos de políticas se pueden usar juntos para implementar defense in depth.
2.  **Ejemplo de política**:

    ```yaml
    # Istio authentication policy
    apiVersion: security.istio.io/v1beta1
    kind: PeerAuthentication
    metadata:
      name: default
      namespace: istio-system
    spec:
      mtls:
        mode: STRICT
    ---
    # Kubernetes NetworkPolicy
    apiVersion: networking.k8s.io/v1
    kind: NetworkPolicy
    metadata:
      name: allow-same-namespace
    spec:
      podSelector: {}
      ingress:
      - from:
        - namespaceSelector:
            matchLabels:
              kubernetes.io/metadata.name: default
    ```

### 5. Pasos de implementación de Service Mesh

#### 1. Verificar requisitos previos

* Comprobar compatibilidad de versión del clúster
* Evaluar requisitos de recursos
* Revisar el modelo de networking

#### 2. Instalar Control Plane

**Ejemplo de Istio:**

```bash
istioctl install --set profile=default
```

**Ejemplo de App Mesh:**

```bash
helm repo add eks https://aws.github.io/eks-charts
helm install appmesh-controller eks/appmesh-controller \
  --namespace appmesh-system \
  --create-namespace
```

#### 3. Configurar la inyección de Sidecar

**Inyección automática:**

```yaml
# Add label to namespace
apiVersion: v1
kind: Namespace
metadata:
  name: my-app
  labels:
    istio-injection: enabled  # Istio
    appmesh.k8s.aws/sidecarInjectorWebhook: enabled  # App Mesh
```

#### 4. Definir recursos de Service Mesh

**Istio Virtual Service y Destination Rule:**

```yaml
apiVersion: networking.istio.io/v1alpha3
kind: VirtualService
metadata:
  name: reviews
spec:
  hosts:
  - reviews
  http:
  - route:
    - destination:
        host: reviews
        subset: v1
      weight: 90
    - destination:
        host: reviews
        subset: v2
      weight: 10
---
apiVersion: networking.istio.io/v1alpha3
kind: DestinationRule
metadata:
  name: reviews
spec:
  host: reviews
  subsets:
  - name: v1
    labels:
      version: v1
  - name: v2
    labels:
      version: v2
```

**App Mesh Virtual Service y Virtual Router:**

```yaml
apiVersion: appmesh.k8s.aws/v1beta2
kind: VirtualService
metadata:
  name: reviews
  namespace: my-app
spec:
  awsName: reviews.my-app.svc.cluster.local
  provider:
    virtualRouter:
      virtualRouterRef:
        name: reviews-router
---
apiVersion: appmesh.k8s.aws/v1beta2
kind: VirtualRouter
metadata:
  name: reviews-router
  namespace: my-app
spec:
  listeners:
    - portMapping:
        port: 9080
        protocol: http
  routes:
    - name: reviews-route
      httpRoute:
        match:
          prefix: /
        action:
          weightedTargets:
            - virtualNodeRef:
                name: reviews-v1
              weight: 90
            - virtualNodeRef:
                name: reviews-v2
              weight: 10
```

### 6. Monitoreo y observabilidad

#### Recolección de métricas

**Integración con Prometheus:**

```yaml
# Istio Prometheus configuration
apiVersion: install.istio.io/v1alpha1
kind: IstioOperator
spec:
  addonComponents:
    prometheus:
      enabled: true
```

#### Distributed Tracing

**Integración con X-Ray (App Mesh):**

```yaml
apiVersion: appmesh.k8s.aws/v1beta2
kind: Mesh
metadata:
  name: my-mesh
spec:
  serviceDiscovery:
    ipPreference: IPv4_PREFERRED
  egressFilter:
    type: ALLOW_ALL
  tracing:
    awsXRay:
      logLevel: INFO
```

### 7. Buenas prácticas para la adopción de Service Mesh

1. **Adopción gradual**:
   * Comienza con workloads no críticos para el negocio
   * Expande por etapas
2. **Planificación de recursos**:
   * Considera aumentar el tamaño y la cantidad de nodes
   * Usa node groups dedicados para el control plane
3. **Optimización de networking**:
   * Evita la inyección innecesaria de sidecar
   * Configura timeouts y retry policies adecuados
4. **Mejora de seguridad**:
   * Adopción gradual de mTLS
   * Aplica el principio de mínimo privilegio
5. **Estrategia de monitoreo**:
   * Compara el rendimiento antes y después de adoptar service mesh
   * Configura dashboards de métricas clave

### 8. Consideraciones específicas de EKS

1. **Compatibilidad con Fargate**:
   * Istio: Soporte limitado (algunas características no disponibles)
   * App Mesh: Soporte completo
2. **Integración con AWS Load Balancer Controller**:
   *   Integración de Ingress gateway y ALB:

       ```yaml
       apiVersion: networking.k8s.io/v1
       kind: Ingress
       metadata:
         annotations:
           kubernetes.io/ingress.class: alb
           alb.ingress.kubernetes.io/scheme: internet-facing
           alb.ingress.kubernetes.io/target-type: ip
       ```
3. **IAM Roles y permisos**:
   * Permisos IAM requeridos para App Mesh controller:
     * appmesh:\*
     * servicediscovery:\*
     * cloudmap:\*
4. **Configuración de VPC CNI**:
   * Considera requisitos adicionales de ENI y direcciones IP debido a service mesh
   *   Se recomienda habilitar la delegación de prefijos:

       ```bash
       kubectl set env daemonset aws-node -n kube-system ENABLE_PREFIX_DELEGATION=true
       ```

### 9. Guía de selección de Service Mesh

| Factor                | Istio                   | AWS App Mesh             |
| --------------------- | ----------------------- | ------------------------ |
| Conjunto de características | Muy completo       | Enfocado en características principales |
| Integración con AWS   | Integración de terceros | Integración nativa       |
| Complejidad           | Alta                    | Media                    |
| Requisitos de recursos | Altos                  | Medios                   |
| Soporte Fargate       | Limitado                | Soporte completo         |
| Comunidad             | Muy activa              | En crecimiento           |
| Híbrido/Multi-cloud   | Soporte sólido          | Centrado en AWS          |

Service mesh trae cambios significativos a la arquitectura de networking de los clústeres EKS, pero proporciona herramientas poderosas para administrar la complejidad de la arquitectura de microservices. La integración con el modelo de networking predeterminado de EKS se realiza mediante el patrón sidecar, que permite agregar características avanzadas de networking sin cambiar el código existente de la aplicación. Al adoptar un service mesh, se deben considerar cuidadosamente el impacto en el rendimiento, la complejidad operativa y los requisitos de recursos, y se recomienda un enfoque gradual.

</details>

### 11. ¿Qué recurso de routing se usa para load balancing L7 (ALB) en Kubernetes Gateway API?

A. IngressRoute B. HTTPRoute C. VirtualService D. ServiceRoute

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B. HTTPRoute**

**Explicación:** En Kubernetes Gateway API, el recurso HTTPRoute se usa para load balancing L7. HTTPRoute define reglas para enrutar tráfico HTTP/HTTPS a services y, cuando se usa con AWS Load Balancer Controller, distribuye tráfico mediante un ALB.

**Jerarquía de recursos de Gateway API:**

1. **GatewayClass**: Define el tipo de load balancer (por ejemplo, `amazon-alb`, `amazon-nlb`)
2. **Gateway**: Instancia real del load balancer (puertos listener, configuración TLS, etc.)
3. **HTTPRoute**: Reglas de routing L7 (host, ruta, routing basado en headers)
4. **TCPRoute**: Reglas de routing L4 (tráfico TCP)

**Características clave de HTTPRoute:**

* Routing basado en ruta y host
* División de tráfico basada en pesos de forma nativa
* Coincidencia de headers y parámetros de query
* Routing a múltiples backend services

Problemas con las otras opciones:

* **A. IngressRoute**: Este no es un recurso estándar de Gateway API.
* **C. VirtualService**: Este es un recurso del service mesh Istio.
* **D. ServiceRoute**: Este recurso no existe.

</details>

### 12. ¿Qué feature gate flag se requiere para habilitar Gateway API en AWS Load Balancer Controller?

A. `--enable-gateway-api` B. `--feature-gates=EnableGatewayAPI=true` C. `--gateway-api-enabled=true` D. `--enable-feature=gateway-api`

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B. `--feature-gates=EnableGatewayAPI=true`**

**Explicación:** Para habilitar Gateway API en AWS Load Balancer Controller, se debe agregar el flag `--feature-gates=EnableGatewayAPI=true` al desplegar el controller. Este feature gate permite que el controller observe y procese recursos Gateway API (GatewayClass, Gateway, HTTPRoute, TCPRoute, etc.).

**Requisitos previos completos para la activación de Gateway API:**

1. Instalar AWS Load Balancer Controller v2.13.0 o posterior
2. Agregar el flag `--feature-gates=EnableGatewayAPI=true`
3. Instalar los CRDs estándar de Gateway API
4. Instalar CRDs experimentales (cuando se usa TCPRoute, etc.)
5. Instalar CRDs específicos de AWS LBC

Problemas con las otras opciones:

* **A, C, D**: Estos flags tienen formatos incorrectos que no usa AWS Load Balancer Controller.

</details>

### 13. ¿Qué recurso se usa para enrutar tráfico TCP de nivel L4 mediante un NLB en Gateway API?

A. HTTPRoute B. TLSRoute C. TCPRoute D. GRPCRoute

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: C. TCPRoute**

**Explicación:** En Gateway API, el recurso TCPRoute se usa para enrutar tráfico TCP de nivel L4. Cuando se usa con AWS Load Balancer Controller, TCPRoute reenvía tráfico TCP a backend services mediante un NLB (Network Load Balancer).

**Ejemplo de configuración de TCPRoute:**

```yaml
apiVersion: gateway.networking.k8s.io/v1alpha2
kind: TCPRoute
metadata:
  name: db-route
spec:
  parentRefs:
  - name: my-nlb-gateway
    sectionName: tcp
  rules:
  - backendRefs:
    - name: postgres-service
      port: 5432
```

**Uso de recursos de routing de Gateway API:**

| Recurso   | Protocolo  | Tipo de AWS LB |
| --------- | ---------- | -------------- |
| HTTPRoute | HTTP/HTTPS | ALB            |
| TCPRoute  | TCP        | NLB            |
| TLSRoute  | TLS        | NLB            |
| GRPCRoute | gRPC       | ALB            |

Problemas con las otras opciones:

* **A. HTTPRoute**: Se usa para tráfico HTTP/HTTPS L7 con ALB.
* **B. TLSRoute**: Para routing de tráfico TLS, pero TCPRoute es adecuado para routing a nivel TCP.
* **D. GRPCRoute**: Un recurso de routing específicamente para el protocolo gRPC.

</details>
