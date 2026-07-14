# Cuestionario de AWS Load Balancer Controller

Este cuestionario evalúa tu comprensión de la arquitectura de AWS Load Balancer Controller, la configuración de ALB/NLB y las operaciones.

## Preguntas del cuestionario

### 1. ¿Qué componente existente de Kubernetes reemplaza AWS Load Balancer Controller?

A. kube-proxy
B. in-tree AWS cloud provider
C. CoreDNS
D. CNI plugin

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. in-tree AWS cloud provider**

**Explicación:**
AWS Load Balancer Controller reemplaza la funcionalidad de load balancer del in-tree AWS cloud provider existente de Kubernetes:
- Más funcionalidades (configuración avanzada de ALB, NLB)
- Actualizaciones y correcciones de errores más rápidas
- Mejor integración con servicios de AWS

El in-tree provider solo admitía ELB Classic básico, mientras que AWS Load Balancer Controller admite todas las funcionalidades de ALB y NLB.

</details>

### 2. ¿Cuál es la diferencia correcta entre las anotaciones de target type `ip` e `instance` en ALB Ingress?

A. `ip` apunta directamente a la IP del Pod, `instance` enruta a través de NodePort
B. `ip` enruta a través de NodePort, `instance` apunta directamente a la IP del Pod
C. Ambas opciones se comportan de la misma manera
D. `ip` admite solo IPv4, `instance` admite solo IPv6

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A. `ip` apunta directamente a la IP del Pod, `instance` enruta a través de NodePort**

**Explicación:**
Comparación de Target Type:

| Target Type | Comportamiento | Ventajas | Desventajas |
|-------------|----------|------|------|
| `ip` | Registra directamente la IP del Pod | Baja latencia, eficiente | Requiere VPC CNI |
| `instance` | Enruta al NodePort del Node | Universal | Salto adicional |

Al usar el tipo `ip`, se requiere AWS VPC CNI y las IP de los Pods se registran directamente en el Target Group.

</details>

### 3. ¿Por qué se requiere IRSA (IAM Roles for Service Accounts) para AWS Load Balancer Controller?

A. Para la comunicación de Pod a Pod
B. Para que el controller llame a las API de AWS para crear/administrar recursos
C. Para la autenticación del API server de Kubernetes
D. Para la administración de certificados TLS

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Para que el controller llame a las API de AWS para crear/administrar recursos**

**Explicación:**
AWS Load Balancer Controller necesita llamar a las API de AWS para:
- Crear y administrar ALB/NLB
- Crear Target Groups y registrar targets
- Configurar Listeners y reglas
- Administrar security groups
- Consultar certificados ACM

Con IRSA vinculando IAM Role a Service Account:
- Los Pods pueden autenticarse en la API de AWS
- Se aplica el principio de mínimo privilegio
- Se conceden permisos a Pods específicos, no a Nodes completos

</details>

### 4. ¿Cómo se consolidan varios recursos de Ingress en un único ALB?

A. Desplegarlos en el mismo namespace
B. Usar la anotación `alb.ingress.kubernetes.io/group.name`
C. Usar el mismo IngressClass
D. ALB siempre admite solo un Ingress

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Usar la anotación `alb.ingress.kubernetes.io/group.name`**

**Explicación:**
Funcionalidad de Ingress Group:

```yaml
# Ingress 1
metadata:
  annotations:
    alb.ingress.kubernetes.io/group.name: my-app-group
    alb.ingress.kubernetes.io/group.order: "1"
---
# Ingress 2
metadata:
  annotations:
    alb.ingress.kubernetes.io/group.name: my-app-group
    alb.ingress.kubernetes.io/group.order: "2"
```

Beneficios:
- Ahorro de costos de ALB (varios servicios comparten un ALB)
- Administración centralizada
- Control de prioridad de reglas mediante la especificación de orden

</details>

### 5. ¿Cuál es la anotación para implementar TLS termination en un Service NLB?

A. `service.beta.kubernetes.io/aws-load-balancer-ssl-cert`
B. `alb.ingress.kubernetes.io/certificate-arn`
C. `service.beta.kubernetes.io/aws-load-balancer-tls-termination`
D. `nlb.kubernetes.io/ssl-certificate`

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A. `service.beta.kubernetes.io/aws-load-balancer-ssl-cert`**

**Explicación:**
Configuración de TLS termination de NLB:

```yaml
apiVersion: v1
kind: Service
metadata:
  annotations:
    service.beta.kubernetes.io/aws-load-balancer-type: "external"
    service.beta.kubernetes.io/aws-load-balancer-nlb-target-type: "ip"
    service.beta.kubernetes.io/aws-load-balancer-ssl-cert: "arn:aws:acm:..."
    service.beta.kubernetes.io/aws-load-balancer-ssl-ports: "443"
spec:
  type: LoadBalancer
  ports:
    - port: 443
      targetPort: 8080
```

`alb.ingress.kubernetes.io/certificate-arn` es la anotación para ALB Ingress.

</details>

### 6. ¿Cuál es el propósito principal del CRD TargetGroupBinding?

A. Crear automáticamente nuevos Target Groups
B. Conectar Target Groups de AWS existentes con Services de Kubernetes
C. Definir reglas de ALB Listener
D. Crear automáticamente security groups

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Conectar Target Groups de AWS existentes con Services de Kubernetes**

**Explicación:**
Casos de uso de TargetGroupBinding:
1. Migración de infraestructura existente - Aprovechar Target Groups existentes
2. Uso compartido entre varios clusters - Usar un ALB/NLB en varios clusters
3. Cuando se necesita la administración directa de Target Groups

```yaml
apiVersion: elbv2.k8s.aws/v1beta1
kind: TargetGroupBinding
metadata:
  name: my-tgb
spec:
  targetGroupARN: arn:aws:elasticloadbalancing:...
  serviceRef:
    name: my-service
    port: 80
  targetType: ip
```

</details>

### 7. ¿Cuál es la anotación para integrar WAF v2 con ALB Ingress?

A. `alb.ingress.kubernetes.io/waf-acl-id`
B. `alb.ingress.kubernetes.io/wafv2-acl-arn`
C. `alb.ingress.kubernetes.io/web-acl`
D. `alb.ingress.kubernetes.io/firewall-rules`

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. `alb.ingress.kubernetes.io/wafv2-acl-arn`**

**Explicación:**
Integración de AWS WAF v2:

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  annotations:
    alb.ingress.kubernetes.io/wafv2-acl-arn: arn:aws:wafv2:us-east-1:ACCOUNT:regional/webacl/my-acl/xxx
```

Funcionalidades de WAF v2:
- Protección contra inyección SQL y XSS
- Limitación de tasa
- Bloqueo/autorización según IP
- Reglas personalizadas

Se requiere la configuración `enableWafv2: true` al instalar el controller.

</details>

### 8. ¿Cuáles son las etiquetas para el descubrimiento automático de subnet en AWS Load Balancer Controller?

A. `kubernetes.io/cluster/<cluster-name>=owned`
B. `kubernetes.io/role/elb=1` (pública), `kubernetes.io/role/internal-elb=1` (privada)
C. `aws:cloudformation:stack-name`
D. `Name=kubernetes-subnet`

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. `kubernetes.io/role/elb=1` (pública), `kubernetes.io/role/internal-elb=1` (privada)**

**Explicación:**
Reglas de etiquetado de subnet:

```bash
# Public subnets (for internet-facing ALB/NLB)
kubernetes.io/role/elb=1

# Private subnets (for internal ALB/NLB)
kubernetes.io/role/internal-elb=1

# Cluster ownership (optional)
kubernetes.io/cluster/<cluster-name>=shared or owned
```

Sin estas etiquetas, el controller podría no encontrar las subnets adecuadas y la creación del load balancer fallará.

</details>

### 9. ¿Cuál es la anotación para habilitar Sticky Sessions en ALB Ingress?

A. `alb.ingress.kubernetes.io/sticky-sessions=true`
B. `alb.ingress.kubernetes.io/target-group-attributes: stickiness.enabled=true`
C. `alb.ingress.kubernetes.io/session-affinity=cookie`
D. `alb.ingress.kubernetes.io/cookie-based-routing=true`

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. `alb.ingress.kubernetes.io/target-group-attributes: stickiness.enabled=true`**

**Explicación:**
Configuración de Sticky Session:

```yaml
metadata:
  annotations:
    alb.ingress.kubernetes.io/target-group-attributes: >-
      stickiness.enabled=true,
      stickiness.lb_cookie.duration_seconds=3600
```

Se configura como atributos de Target Group:
- `stickiness.enabled=true` - Habilitar
- `stickiness.lb_cookie.duration_seconds` - Duración de validez de la cookie
- `stickiness.type` - lb_cookie o app_cookie

Las Sticky Sessions son útiles para aplicaciones heredadas que necesitan mantener el estado de la sesión.

</details>

### 10. ¿Cómo se conserva la IP de origen del cliente en NLB?

A. Usar `service.beta.kubernetes.io/aws-load-balancer-proxy-protocol: "*"`
B. Usar externalTrafficPolicy: Local
C. Ambos métodos son posibles
D. NLB siempre conserva la IP del cliente

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C. Ambos métodos son posibles**

**Explicación:**
Métodos para conservar la IP del cliente:

1. **Proxy Protocol v2**:
```yaml
annotations:
  service.beta.kubernetes.io/aws-load-balancer-proxy-protocol: "*"
  service.beta.kubernetes.io/aws-load-balancer-target-group-attributes: proxy_protocol_v2.enabled=true
```
- La aplicación debe admitir Proxy Protocol

2. **externalTrafficPolicy: Local**:
```yaml
spec:
  externalTrafficPolicy: Local
```
- Enruta solo a Pods en el mismo Node sin saltos adicionales
- Es posible una distribución desigual del tráfico

3. **IP Target Type** (modo ip):
```yaml
annotations:
  service.beta.kubernetes.io/aws-load-balancer-target-group-attributes: preserve_client_ip.enabled=true
```

</details>

### 11. ¿Cuál es la anotación para redirigir HTTP a HTTPS en ALB Ingress?

A. `alb.ingress.kubernetes.io/actions.ssl-redirect`
B. `alb.ingress.kubernetes.io/ssl-redirect: "443"`
C. `alb.ingress.kubernetes.io/force-ssl-redirect: "true"`
D. `alb.ingress.kubernetes.io/http-to-https: "true"`

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. `alb.ingress.kubernetes.io/ssl-redirect: "443"`**

**Explicación:**
Configuración de redirección SSL:

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  annotations:
    alb.ingress.kubernetes.io/listen-ports: '[{"HTTP": 80}, {"HTTPS": 443}]'
    alb.ingress.kubernetes.io/ssl-redirect: "443"
    alb.ingress.kubernetes.io/certificate-arn: arn:aws:acm:...
```

Comportamiento:
- Redirige con 301 las solicitudes que llegan a HTTP(80) hacia HTTPS(443)
- Recomendado como práctica recomendada de seguridad
- Requiere certificado ACM

</details>

### 12. ¿Cuál NO es algo que se debe verificar cuando AWS Load Balancer Controller no está creando un ALB?

A. Verificar los permisos de IAM
B. Verificar las etiquetas de subnet
C. Verificar la especificación de IngressClass
D. Verificar los logs de kube-proxy

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: D. Verificar los logs de kube-proxy**

**Explicación:**
Aspectos que se deben verificar cuando falla la creación de ALB:

1. **Permisos de IAM**: Si el IAM Role de Service Account tiene los permisos requeridos
2. **Etiquetas de subnet**: `kubernetes.io/role/elb=1` o `kubernetes.io/role/internal-elb=1`
3. **IngressClass**: Especificar `ingressClassName: alb` o mediante anotación
4. **Logs del controller**: `kubectl logs -n kube-system deployment/aws-load-balancer-controller`
5. **Eventos de Ingress**: `kubectl describe ingress <name>`

kube-proxy maneja el enrutamiento de Service ClusterIP/NodePort y no está relacionado con la creación de ALB.

</details>

---

## Recursos de aprendizaje adicionales

- [Documentación de AWS Load Balancer Controller](https://kubernetes-sigs.github.io/aws-load-balancer-controller/)
- [Guía del usuario de EKS](https://docs.aws.amazon.com/eks/latest/userguide/aws-load-balancer-controller.html)
- [Referencia de anotaciones de ALB](https://kubernetes-sigs.github.io/aws-load-balancer-controller/v2.8/guide/ingress/annotations/)
