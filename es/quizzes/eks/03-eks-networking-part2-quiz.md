# Cuestionario de redes de EKS - Parte 2

> **Última actualización**: October 12, 2026

Estas respuestas usan la propiedad del controlador y los requisitos previos de la [Parte 2](../../eks/03-eks-networking-part2.md): LBC 3.5.0 y Gateway API 1.6.0. Los comandos son ejemplos que modifican recursos al ejecutarse; las pruebas locales de esquemas/simulaciones no constituyen una implementación de EKS. Sustituya los marcadores de posición de cuenta/Región/recurso, use el kubeconfig previsto y preserve la propiedad de IAM/Helm/IaC de la plataforma.

### 1. ¿Qué tipo de balanceador de carga de AWS aprovisiona AWS Load Balancer Controller de forma predeterminada para los recursos Ingress de Kubernetes?

A. Classic Load Balancer (CLB) B. Network Load Balancer (NLB) C. Application Load Balancer (ALB) D. Gateway Load Balancer (GWLB)

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: C. Application Load Balancer (ALB)**

**Explicación:** AWS Load Balancer Controller aprovisiona de forma predeterminada un Application Load Balancer (ALB) para los recursos Ingress de Kubernetes. ALB es un balanceador de carga de capa 7 que gestiona tráfico HTTP/HTTPS y proporciona características como el enrutamiento basado en rutas, el enrutamiento basado en hosts y la terminación TLS para cumplir los requisitos de los recursos Ingress.

LBC debe seleccionar la clase Ingress; otro controlador puede implementar un Ingress de forma diferente. El esquema público siguiente requiere subredes públicas configuradas intencionalmente, acceso de clientes mediante SG y Services de backend listos.

**Características principales:**

1. **Enrutamiento basado en rutas**: ALB puede enrutar tráfico a distintos servicios según las rutas de URL, por lo que es adecuado para implementar reglas de enrutamiento basadas en rutas en Ingress.
2. **Enrutamiento basado en hosts**: Se pueden gestionar varios dominios con un único ALB, lo que admite Ingress con varias reglas de host.
3. **Terminación TLS**: ALB puede administrar certificados SSL/TLS y terminar el tráfico HTTPS.
4. **Compatibilidad con WebSockets**: ALB admite el protocolo WebSockets, adecuado para aplicaciones en tiempo real.
5. **Integración de autenticación**: Puede integrarse con Amazon Cognito u OIDC para proporcionar autenticación de nivel de aplicación.

**Ejemplo de configuración:**

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: example-ingress
  annotations:
    alb.ingress.kubernetes.io/scheme: internet-facing
    alb.ingress.kubernetes.io/target-type: ip
spec:
  ingressClassName: alb
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

**Anotaciones principales:**

* `spec.ingressClassName: alb`: Selecciona una IngressClass cuyo controlador es `ingress.k8s.aws/alb`
* `alb.ingress.kubernetes.io/scheme: internet-facing`: Crea un ALB público
* `alb.ingress.kubernetes.io/target-type: ip`: Usa las IP de Pod como destinos (en lugar de instancias)
* `alb.ingress.kubernetes.io/listen-ports: '[{"HTTP": 80}, {"HTTPS": 443}]'`: Configura los puertos del listener
* `alb.ingress.kubernetes.io/certificate-arn: arn:aws:acm:region:account-id:certificate/certificate-id`: Especifica el certificado SSL

Problemas con las demás opciones:

* **A. Classic Load Balancer (CLB)**: AWS Load Balancer Controller no usa CLB para recursos Ingress. CLB se considera un balanceador de carga heredado.
* **B. Network Load Balancer (NLB)**: NLB se usa principalmente para Service de tipo LoadBalancer y no se usa de forma predeterminada para recursos Ingress.
* **D. Gateway Load Balancer (GWLB)**: GWLB es para dispositivos virtuales de red y no se usa con recursos Ingress de Kubernetes.

</details>

### 2. ¿Qué anotación de Ingress selecciona un ALB interno?

- A. Anotación de Service `aws-load-balancer-internal`
- B. Anotación de Ingress `alb.ingress.kubernetes.io/scheme: internal`
- C. Cualquier clase denominada `internal-alb`
- D. `aws-load-balancer-type: internal`

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. `alb.ingress.kubernetes.io/scheme: internal`**

Un ALB interno tiene direcciones privadas. Los clientes enrutados en VPC conectadas o redes locales también pueden alcanzarlo cuando el enrutamiento, DNS y los controles de seguridad lo permiten; por definición, no se restringe a los Pods ni a su propia VPC.
```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: internal-ingress
  annotations:
    alb.ingress.kubernetes.io/scheme: internal
    alb.ingress.kubernetes.io/target-type: ip
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
            name: internal-service
            port:
              number: 80
```
El descubrimiento de subredes o los ID de subred explícitos seleccionan la ubicación; los SG controlan el acceso. `inbound-cidrs` configura un SG de frontend creado por el controlador, pero se ignora cuando se proporcionan SG personalizados. Se debe crear por separado un alias/CNAME privado de Route 53; los atributos de logs de ALB no crean registros DNS. Los nombres personalizados de IngressClass, como `internal-alb`, son posibles cuando existe una configuración real de IngressClass/controlador coincidente, pero el nombre por sí solo no selecciona el esquema.

</details>

### 3. ¿Qué anotación de Ingress selecciona destinos de IP de Pod?

- A. `target-type: pod`
- B. `alb.ingress.kubernetes.io/target-type: ip`
- C. `service.beta.kubernetes.io/aws-load-balancer-target-type: ip`
- D. `aws-load-balancer-target-node-labels: ip-mode=true`

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. `alb.ingress.kubernetes.io/target-type: ip`**

`ip` registra IP de Pod enrutable y puertos de destino de Service resueltos. `instance` normalmente registra nodos y NodePorts (sujeto a los valores predeterminados de controlador/IngressClass). Los destinos IP son necesarios para EKS Fargate. Seleccionar destinos IP no crea por sí mismo grupos de seguridad para Pods, elimina fallas de nodos ni garantiza mayor rendimiento.
```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: ip-ingress
  annotations:
    alb.ingress.kubernetes.io/scheme: internal
    alb.ingress.kubernetes.io/target-type: ip
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
            name: example-service
            port:
              number: 80
```
| Propiedad | Destinos IP | Destinos de instancia |
|---|---|---|
| Ruta | LB → destino Pod | LB → NodePort → endpoint seleccionado |
| Falla de nodo | Los Pods del nodo fallido se pierden; las comprobaciones de estado/la reconciliación convergen | Se elimina el destino del nodo fallido; otros nodos en buen estado pueden permanecer |
| Tipo de Service | ClusterIP es suficiente | NodePort o LoadBalancer con NodePorts asignados |
| Fargate | Ruta compatible | Sin destino NodePort de EC2 |

Use redes de Pod enrutables mediante VPC y permita tanto el tráfico de aplicación como el de comprobación de estado. El VPC CNI nativo es la vía habitual para EC2; los diseños híbridos/de red compatibles necesitan su propia validación de conectividad. `service.beta.kubernetes.io/aws-load-balancer-nlb-target-type: ip` es la anotación equivalente para Service de NLB; la opción que omite `nlb` no es la anotación correcta.

</details>

### 4. ¿La anotación NLB-IP crea un servicio de endpoint de PrivateLink?

- A. Cualquier Service `LoadBalancer` crea PrivateLink
- B. `nlb-ip` lo crea y autoriza automáticamente
- C. Configuración independiente de NLB, servicio de endpoint y consumidor
- D. Solo los destinos de instancia pueden usar PrivateLink

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C. No; cree por separado el NLB, la configuración del servicio de endpoint y el acceso del consumidor.**

La respuesta original de `nlb-ip` confundía la selección de destinos con el aprovisionamiento de PrivateLink. Un servicio de endpoint usa un NLB (o GWLB para dispositivos); no requiere destinos IP ni un NLB interno. Este ejemplo elige deliberadamente un NLB interno con destinos IP para acceso privado a Pods.
```yaml
apiVersion: v1
kind: Service
metadata:
  name: privatelink-service
  annotations:
    service.beta.kubernetes.io/aws-load-balancer-scheme: internal
    service.beta.kubernetes.io/aws-load-balancer-nlb-target-type: ip
spec:
  type: LoadBalancer
  loadBalancerClass: service.k8s.aws/nlb
  allocateLoadBalancerNodePorts: false
  selector:
    app: my-app
  ports:
  - port: 80
    targetPort: 8080
```
Cree este Service en el namespace previsto con Pods coincidentes listos y espere al NLB. Identifíquelo mediante el DNSName exacto, no dividiendo su nombre de host con guiones:
```bash
set -euo pipefail
: "${AWS_REGION:?Set the provider Region}"
: "${SERVICE_NAMESPACE:?Set the Service namespace}"
NLB_DNS=$(kubectl -n "$SERVICE_NAMESPACE" get service privatelink-service \
  -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')
test -n "$NLB_DNS"
aws elbv2 describe-load-balancers --region "$AWS_REGION" --output json > privatelink-load-balancers.json
NLB_ARN=$(python3 - "$NLB_DNS" <<'PY'
import json, sys
with open("privatelink-load-balancers.json") as stream:
    matches = [lb for lb in json.load(stream)["LoadBalancers"]
               if lb["DNSName"] == sys.argv[1] and lb["Type"] == "network"]
if len(matches) != 1:
    raise SystemExit("Expected exactly one matching NLB; check Region, account and readiness")
print(matches[0]["LoadBalancerArn"])
PY
)
printf '%s\n' "$NLB_ARN"
```
Los siguientes comandos del lado del proveedor crean recursos facturables y conceden acceso al servicio de endpoint a una cuenta de consumidor. Ejecútelos bajo el propietario de infraestructura revisado, registre los ID devueltos y evite volver a ejecutar la creación como si fuera idempotente. Este ejemplo es para la partición comercial de AWS; adapte los ARN para otra partición.
```bash
set -euo pipefail
: "${AWS_REGION:?Set the provider Region}"
: "${NLB_ARN:?Use the NLB ARN verified above}"
: "${CONSUMER_ACCOUNT_ID:?Set the allowed consumer account}"
aws ec2 create-vpc-endpoint-service-configuration \
  --region "$AWS_REGION" --network-load-balancer-arns "$NLB_ARN" \
  --acceptance-required --output json > endpoint-service-created.json
SERVICE_ID=$(python3 -c 'import json; print(json.load(open("endpoint-service-created.json"))["ServiceConfiguration"]["ServiceId"])')
SERVICE_NAME=$(python3 -c 'import json; print(json.load(open("endpoint-service-created.json"))["ServiceConfiguration"]["ServiceName"])')
aws ec2 modify-vpc-endpoint-service-permissions \
  --region "$AWS_REGION" --service-id "$SERVICE_ID" \
  --add-allowed-principals "arn:aws:iam::$CONSUMER_ACCOUNT_ID:root"
printf 'Service name: %s\n' "$SERVICE_NAME"
```
En la cuenta de consumidor, elija AZ compatibles (compare los ID de AZ entre cuentas), SG de endpoint que permitan los clientes previstos y el nombre de servicio devuelto exacto. Este ejemplo de misma Región no configura PrivateLink entre Regiones.
```bash
set -euo pipefail
: "${CONSUMER_REGION:?Set the consumer Region}"
: "${CONSUMER_VPC_ID:?Set the consumer VPC}"
: "${CONSUMER_SUBNET_A:?Set a subnet in an available service AZ}"
: "${CONSUMER_SUBNET_B:?Set another supported AZ subnet}"
: "${CONSUMER_SG_ID:?Set the endpoint security group}"
: "${SERVICE_NAME:?Copy the exact name returned by the provider}"
aws ec2 create-vpc-endpoint \
  --region "$CONSUMER_REGION" --vpc-id "$CONSUMER_VPC_ID" \
  --service-name "$SERVICE_NAME" --vpc-endpoint-type Interface \
  --subnet-ids "$CONSUMER_SUBNET_A" "$CONSUMER_SUBNET_B" \
  --security-group-ids "$CONSUMER_SG_ID"
```
El proveedor debe aceptar la solicitud de endpoint pendiente específica porque se requiere aceptación. El DNS privado opcional requiere verificación de propiedad del dominio antes de que los consumidores lo habiliten. Valide los destinos en buen estado, el estado del endpoint y la autenticación de la aplicación. Las IP de origen de PrivateLink en el destino son direcciones de NLB; Proxy Protocol v2 puede transportar metadatos del consumidor si el backend lo comprende. No satisface automáticamente el cumplimiento ni autoriza solicitudes de aplicación. Retire los endpoints de consumidor, las asociaciones de servicio de endpoint y los recursos de balanceador de carga de Kubernetes a través de sus respectivos propietarios.

</details>

### 5. ¿Qué motor de políticas adicional puede funcionar con Amazon VPC CNI?

- A. AWS Network Firewall
- B. Calico
- C. Security Groups for Pods
- D. VPC Flow Logs

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Calico**

Calico puede aplicar políticas mientras VPC CNI conserva IPAM/redes. Es una alternativa al motor de políticas nativo de VPC CNI, no un complemento obligatorio. Siga el [procedimiento oficial de EKS solo para políticas](https://docs.tigera.io/calico/latest/getting-started/kubernetes/managed-public-cloud/eks), incluidas las versiones compatibles, `cni.type: AmazonVPC`, `ANNOTATE_POD_IP` y el permiso de parche de Pod requerido. No habilite ambos motores simultáneamente ni aplique un manifiesto de reemplazo VXLAN al clúster en ejecución.

Las API de Calico también proporcionan reglas ordenadas/por niveles, GlobalNetworkPolicy, NetworkSet, selectores de cuentas de servicio y políticas de endpoint de host. Su semántica difiere de Kubernetes NetworkPolicy aditivo; un NetworkSet no restringe tráfico hasta que una política de Calico lo referencia. Una política global de permitir todo no es una base de mínimo privilegio. No suponga que todos los modos de VPC CNI son compatibles: la guía actual de Calico EKS excluye específicamente la aplicación para Pods IPv6 con `ENABLE_V4_EGRESS=true`.

Para un ejemplo de política de Kubernetes propiedad de un namespace, cree `policy-lab` y un Pod gestionado por controlador con la etiqueta `role=frontend`. Esta política de salida permite únicamente CoreDNS habitual y destinos HTTPS aprobados, sujeta a todas las demás políticas aditivas. Sustituya el CIDR de documentación por el destino real; adapte DNS para NodeLocal DNS.
```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: frontend-egress
  namespace: policy-lab
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
      podSelector:
        matchLabels:
          k8s-app: kube-dns
    ports:
    - protocol: UDP
      port: 53
    - protocol: TCP
      port: 53
  - to:
    - ipBlock:
        cidr: 203.0.113.0/24
    ports:
    - protocol: TCP
      port: 443
```
Verifique la conectividad de referencia y las rutas TCP permitidas/denegadas antes de confiar en la aplicación. NetworkPolicy no tiene un modo portátil de solo auditoría. Use las características documentadas de registros/preparación del motor seleccionado donde estén disponibles. Los SG para Pods y los firewalls de VPC son controles independientes; Flow Logs observa el tráfico en vez de aplicar esta API.

</details>

### 6. ¿En qué se diferencian los grupos de seguridad de frontend ALB personalizados y las reglas de backend?

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: `alb.ingress.kubernetes.io/security-groups`**

Combine este fragmento de anotación en el Ingress previsto. Los ID de SG son inequívocos; una búsqueda por nombre coincide con la etiqueta `Name` de AWS, no con el atributo EC2 `groupName`.
```yaml
metadata:
  annotations:
    alb.ingress.kubernetes.io/security-groups: sg-0123456789abcdef0
    alb.ingress.kubernetes.io/manage-backend-security-group-rules: "true"
    alb.ingress.kubernetes.io/tags: Environment=training,Team=platform
```
Configure usted mismo las reglas de entrada/salida de frontend personalizadas. Las anotaciones `inbound-cidrs` y de lista de prefijos se ignoran para los SG de frontend proporcionados. `manage-backend-security-group-rules: "true"` autoriza al controlador a gestionar el acceso a destinos mediante su mecanismo de SG de backend; no crea reglas que restrinjan el acceso de clientes en el SG de frontend personalizado. Sin ella, organice usted mismo el acceso de SG de nodo/Pod. Permita los puertos de aplicación y de comprobación de estado, y revise las etiquetas de selección de SG cuando los ENI de destino tengan varios SG.

La política IAM de la versión incluye los permisos EC2/ELB necesarios para todo el controlador; una lista corta de acciones de SG no es una política de rol completa. Reutilizar SG en dominios de confianza amplía la exposición e incrementa el acoplamiento de cambios. Revise las reglas reales y los rechazos de VPC Flow Log. `tags` añade etiquetas de recurso compatibles; `load_balancing.cross_zone.enabled` es un atributo de balanceo, no una etiqueta. Seleccione una política de seguridad TLS compatible según la compatibilidad y los requisitos de los clientes en lugar de copiar como guía actual el nombre de una política heredada.

</details>

### 7. ¿Cómo se configura la conservación de la IP de cliente de NLB y cuáles son sus límites?

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: `service.beta.kubernetes.io/aws-load-balancer-target-group-attributes: preserve_client_ip.enabled=true`**

Para los grupos de destino TCP/TLS, el atributo es configurable: los destinos de instancia se habilitan de forma predeterminada, los destinos IP se deshabilitan de forma predeterminada. Los grupos de destino UDP/TCP_UDP/QUIC/TCP_QUIC siempre conservan la IP de cliente y no pueden deshabilitarla. Este ejemplo TCP de destino IP IPv4 cambia el caso configurable:
```yaml
apiVersion: v1
kind: Service
metadata:
  name: my-service
  annotations:
    service.beta.kubernetes.io/aws-load-balancer-target-group-attributes: preserve_client_ip.enabled=true
    service.beta.kubernetes.io/aws-load-balancer-scheme: internal
    service.beta.kubernetes.io/aws-load-balancer-nlb-target-type: ip
spec:
  type: LoadBalancer
  loadBalancerClass: service.k8s.aws/nlb
  allocateLoadBalancerNodePorts: false
  selector:
    app: my-app
  ports:
  - port: 80
    targetPort: 8080
```
La dirección que ve la aplicación sigue dependiendo de la ruta completa. El reenvío de NodePort puede aplicar SNAT salvo que la política/topología de tráfico local la conserve; ALB usa encabezados HTTP reenviados; la traducción de IPv6 a IPv4 y PrivateLink no conservan el origen del paquete original. La conservación requiere rutas directas de misma VPC o peering de misma Región compatibles y no funciona a través de un transit gateway. Las conexiones hairpin de NLB interno de vuelta al mismo destino registrado pueden fallar.

Proxy Protocol v2 puede transmitir metadatos de dirección original, pero requiere un listener/analizador compatible; no lo habilite indiscriminadamente. `remote_addr` del framework o `RemoteAddr()` de TCP informa del par inmediato, no automáticamente del cliente original de Internet. Confíe solo en encabezados reenviados por proxies explícitamente confiables. Cambiar la conservación afecta las nuevas conexiones TCP. `deregistration_delay.timeout_seconds` controla el drenaje, no el keep-alive de TCP. Mida el rendimiento en lugar de asignar un valor de sobrecarga no compatible.

</details>

### 8. ¿Cómo se asocia AWS WAF a un ALB gestionado por LBC?

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: `alb.ingress.kubernetes.io/wafv2-acl-arn` con una Web ACL REGIONAL de la misma Región.**

Use un ARN real `regional/webacl/...`. Un ARN `global/webacl/...` de CloudFront no se puede asociar al ALB regional. La asociación protege el tráfico que pasa por ese ALB; no asocia WAF a Pods, NLB ni al servidor de API de Kubernetes.
```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: waf-ingress
  annotations:
    alb.ingress.kubernetes.io/scheme: internal
    alb.ingress.kubernetes.io/target-type: ip
    alb.ingress.kubernetes.io/wafv2-acl-arn: arn:aws:wafv2:us-west-2:123456789012:regional/webacl/eks-ingress-protection/00000000-0000-4000-8000-000000000000
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
            name: example-service
            port:
              number: 80
```
Una Web ACL vacía con Allow predeterminado no bloquea nada. Para un ejemplo aislado de desarrollo de reglas, guarde la siguiente matriz como `waf-rules.json`. Esta regla **cuenta**, en lugar de bloquear, los prefijos `/admin`; no es un control de autenticación ni una base completa de reglas administradas.
```json
[
  {
    "Name": "count-admin-path",
    "Priority": 1,
    "Action": {
      "Count": {}
    },
    "VisibilityConfig": {
      "SampledRequestsEnabled": true,
      "CloudWatchMetricsEnabled": true,
      "MetricName": "count-admin-path"
    },
    "Statement": {
      "ByteMatchStatement": {
        "SearchString": "/admin",
        "FieldToMatch": {
          "UriPath": {}
        },
        "TextTransformations": [
          {
            "Priority": 0,
            "Type": "NONE"
          }
        ],
        "PositionalConstraint": "STARTS_WITH"
      }
    }
  }
]
```
Un propietario de seguridad puede crear esa ACL de entrenamiento con el siguiente comando; use el ARN que devuelve al asociarla. La marca de formato binario hace que el JSON SearchString sean bytes literales en AWS CLI v2.
```bash
set -euo pipefail
: "${AWS_REGION:?Set the ALB Region}"
aws wafv2 create-web-acl --region "$AWS_REGION" \
  --name eks-ingress-training --scope REGIONAL \
  --default-action '{"Allow":{}}' --rules file://waf-rules.json \
  --cli-binary-format raw-in-base64-out \
  --visibility-config SampledRequestsEnabled=true,CloudWatchMetricsEnabled=true,MetricName=eks-ingress-training
```
Las reglas administradas de SQLi/XSS, bots, reputación, basadas en tasa y personalizadas proporcionan sus respectivas protecciones solo después de configurarse y ajustarse; los cargos/características varían. Revise los falsos positivos en modo Count antes de habilitar la aplicación. Allow predeterminado sigue siendo permisivo mientras una regla cuenta.

Los atributos `access_logs.s3.*` de ALB configuran logs de acceso de ALB en S3, no logs de WAF ni CloudWatch Logs. Configure los registros de WAF por separado con un destino aprobado de CloudWatch Logs/S3/Firehose y los permisos necesarios; las solicitudes muestreadas y las métricas de CloudWatch son independientes de los logs de solicitudes completos. Use la política IAM de controlador de versión revisada para la asociación y un rol de administración de seguridad separado para creación de ACL/reglas/logs. Aplique permisos de recursos con alcance donde sea compatible; no pegue una política comodín independiente sin restricciones como un rol completo de controlador.

</details>

### 9. Cree y verifique el enrutamiento de rutas para tres backends distinguibles.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: Ingress + Services ClusterIP + cargas de trabajo HTTP listas.**

Requisitos previos: LBC con IAM/subredes revisados, un cliente de prueba privado enrutable, un certificado ACM para un nombre de host que controle y permiso para crear un namespace dedicado. El ejemplo crea un ALB interno; `/admin` es solo una etiqueta de enrutamiento y no tiene autenticación. Es un ejercicio de entrenamiento acotado, no evidencia de preparación para producción. Ejecute los bloques en una shell con `set -euo pipefail`; conserve LAB_NS/LAB_UID hasta la limpieza.
```bash
set -euo pipefail
LAB_NS="alb-paths-$(date -u +%Y%m%d%H%M%S)-$RANDOM"
kubectl create namespace "$LAB_NS"
LAB_UID=$(kubectl get namespace "$LAB_NS" -o jsonpath='{.metadata.uid}')
test -n "$LAB_UID"
kubectl label namespace "$LAB_NS" \
  pod-security.kubernetes.io/enforce=restricted \
  pod-security.kubernetes.io/enforce-version=v1.36
printf 'Namespace: %s UID: %s\n' "$LAB_NS" "$LAB_UID"
```
El servidor HTTP realmente escucha en 8080 y responde a `/health` más todas las rutas solicitadas con el nombre de su backend. Declarar solo `containerPort: 8080` no reconfiguraría un servidor nginx predeterminado. La etiqueta mutable de Python es un entorno de ejecución ilustrativo; fije un digest de imagen aprobado para un uso reproducible.
```bash
for APP in api admin frontend; do
  kubectl -n "$LAB_NS" apply -f - <<EOF
apiVersion: apps/v1
kind: Deployment
metadata:
  name: $APP
spec:
  replicas: 2
  selector:
    matchLabels:
      app: $APP
  template:
    metadata:
      labels:
        app: $APP
    spec:
      automountServiceAccountToken: false
      securityContext:
        runAsNonRoot: true
        runAsUser: 10001
        runAsGroup: 10001
        seccompProfile:
          type: RuntimeDefault
      containers:
      - name: http
        image: python:3.13-alpine
        command: ["python", "-u", "-c"]
        args:
        - |
          import os
          from http.server import BaseHTTPRequestHandler, HTTPServer
          class Handler(BaseHTTPRequestHandler):
              def do_GET(self):
                  self.send_response(200)
                  self.end_headers()
                  self.wfile.write((os.environ["APP_NAME"] + "\\n").encode())
          HTTPServer(("0.0.0.0", 8080), Handler).serve_forever()
        env:
        - name: APP_NAME
          value: $APP
        ports:
        - name: http
          containerPort: 8080
        readinessProbe:
          httpGet:
            path: /health
            port: http
        resources:
          requests:
            cpu: 50m
            memory: 32Mi
          limits:
            cpu: 200m
            memory: 64Mi
        securityContext:
          allowPrivilegeEscalation: false
          readOnlyRootFilesystem: true
          capabilities:
            drop: ["ALL"]
---
apiVersion: v1
kind: Service
metadata:
  name: $APP-service
spec:
  type: ClusterIP
  selector:
    app: $APP
  ports:
  - port: 80
    targetPort: http
EOF
  kubectl -n "$LAB_NS" rollout status "deployment/$APP" --timeout=180s
done
```

```bash
set -euo pipefail
: "${LAB_NS:?Run the namespace setup first}"
: "${LAB_HOST:?Set a DNS hostname you control, for example app.example.com}"
: "${ACM_CERT_ARN:?Set a matching certificate ARN in the ALB Region}"
: "${CLIENT_CIDR:?Set the permitted private client CIDR}"
kubectl -n "$LAB_NS" apply -f - <<EOF
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: multi-path-ingress
  annotations:
    alb.ingress.kubernetes.io/scheme: internal
    alb.ingress.kubernetes.io/target-type: ip
    alb.ingress.kubernetes.io/inbound-cidrs: "$CLIENT_CIDR"
    alb.ingress.kubernetes.io/listen-ports: '[{"HTTP":80},{"HTTPS":443}]'
    alb.ingress.kubernetes.io/certificate-arn: "$ACM_CERT_ARN"
    alb.ingress.kubernetes.io/ssl-redirect: "443"
    alb.ingress.kubernetes.io/healthcheck-path: /health
spec:
  ingressClassName: alb
  rules:
  - host: "$LAB_HOST"
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
EOF
kubectl -n "$LAB_NS" get ingress multi-path-ingress
kubectl -n "$LAB_NS" get endpointslices
```
Espere a que haya un nombre de host de ALB, destinos en buen estado y reconciliación del controlador. Ante un error, inspeccione eventos de Ingress, logs del controlador, EndpointSlices y rutas de SG/comprobación de estado. Desde el cliente privado permitido, esta prueba conserva el encabezado Host y SNI de TLS mientras se conecta directamente al nombre de host del ALB; no requiere un registro DNS ni deshabilita la verificación de certificados.
```bash
ALB_DNS=$(kubectl -n "$LAB_NS" get ingress multi-path-ingress \
  -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')
test -n "$ALB_DNS"
for ROUTE in api admin frontend; do
  URL_PATH="/$ROUTE"
  test "$ROUTE" != frontend || URL_PATH=/
  RESPONSE=$(curl --fail --show-error --silent --max-time 15 \
    --connect-to "$LAB_HOST:443:$ALB_DNS:443" "https://$LAB_HOST$URL_PATH")
  test "$RESPONSE" = "$ROUTE" || { printf 'Unexpected backend: %s\n' "$RESPONSE"; exit 1; }
done
```
Para DNS persistente, cree un alias adecuado de Route 53; se permite un CNAME en un subdominio, no en el ápice de zona. No use un ARN de marcador de posición de CA pública ni `curl -k` para ocultar una falta de coincidencia de certificado.

El enrutamiento ponderado opcional es un ejemplo independiente con backends `service-v1`/`service-v2` existentes. La acción debe referenciarse mediante el backend `use-annotation`; añadir solo la anotación de acción no tiene efecto. Ejecútelo en el namespace previsto y evite rutas en conflicto.
```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: weighted-ingress
  annotations:
    alb.ingress.kubernetes.io/scheme: internal
    alb.ingress.kubernetes.io/target-type: ip
    alb.ingress.kubernetes.io/actions.weighted-routing: >-
      {"type":"forward","forwardConfig":{"targetGroups":[{"serviceName":"service-v1","servicePort":"80","weight":80},{"serviceName":"service-v2","servicePort":"80","weight":20}]}}
spec:
  ingressClassName: alb
  rules:
  - http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: weighted-routing
            port:
              name: use-annotation
```
Limpie solo el namespace de este ejercicio después de comprobar su UID guardado. Deje que LBC elimine el balanceador de carga de Ingress antes de eliminar el namespace. Si la finalización falla, diagnostique el estado de controlador/IAM/protección contra eliminación; no fuerce la eliminación de finalizers. Los certificados compartidos, roles de controlador y registros DNS no se eliminan mediante este bloque.
```bash
set -euo pipefail
: "${LAB_NS:?Use the namespace from this exercise}"
: "${LAB_UID:?Use the UID saved when that namespace was created}"
case "$LAB_NS" in alb-paths-*) ;; *) echo "Unexpected namespace"; exit 1 ;; esac
CURRENT_UID=$(kubectl get namespace "$LAB_NS" -o jsonpath='{.metadata.uid}')
test "$CURRENT_UID" = "$LAB_UID" || { echo "Namespace identity changed"; exit 1; }
kubectl -n "$LAB_NS" delete ingress multi-path-ingress --ignore-not-found --wait=true --timeout=300s
kubectl delete namespace "$LAB_NS" --wait=true --timeout=300s
```

</details>

### 10. ¿Cómo cambia una malla de servicios las redes de EKS y qué se debe validar?

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: Añade procesamiento de tráfico/seguridad/telemetría sobre una red de Pod compatible.**

Un plano de control distribuye la configuración y la identidad de carga de trabajo; los proxies del plano de datos procesan el tráfico inscrito. En un diseño sidecar, la aplicación y el proxy comparten el **mismo namespace/IP de red de Pod**. Un sidecar no consume inherentemente otra IP o ENI de VPC. Los Pods adicionales de gateway/plano de control de la malla sí consumen recursos/IP. En cambio, los diseños Ambient usan proxies de nodo y waypoints opcionales, de modo que «cada Pod recibe un sidecar» no es universal.
```text
Client application → client proxy → Pod network → destination proxy → destination application
```
Esta es una ruta lógica de sidecar, no una promesa de que cada paquete atraviese una IP virtual de Service ni de que sea interceptado. Los puertos excluidos, UDP, el tráfico de red de host, la inscripción en namespace y el modo son importantes. Las rutas de VPC, los SG y NetworkPolicy siguen aplicándose. La política L3/L4 debe permitir las rutas necesarias del plano de datos, DNS, plano de control y de estado; mTLS autentica/cifra pares de la malla y no sustituye la autorización de la aplicación.

Para Istio, elija una instalación documentada de sidecar/ambient para el tipo de cómputo. Fargate no puede ejecutar los DaemonSets/componentes privilegiados de nodo requeridos por algunos modos; verifique la compatibilidad en lugar de afirmar compatibilidad universal. No habilite dos inyectores de malla en un namespace. Configure recursos de proxy mediante configuraciones compatibles de Helm/instalación/carga de trabajo, no sobrescribiendo un ConfigMap de inyector con `pilot.resources` no relacionado. Mantenga la implementación de Prometheus/tracing y la configuración de exportación de malla separadas; los eliminados `IstioOperator.addonComponents.prometheus` y el inventado `App Mesh Mesh.spec.tracing` no son recetas de instalación utilizables.

**Comparación histórica:** AWS finalizó el soporte de App Mesh el **September 30, 2026**; su consola y recursos ya no están disponibles. Una implementación existente de App Mesh debe migrar; no la introduzca como una nueva opción predeterminada de EKS. Su integración histórica con Fargate no es una garantía de compatibilidad futura. ECS Service Connect es una opción de ECS, no un reemplazo directo de EKS. Use un diseño de malla/plano de datos de EKS compatible y verifique la paridad de características para enrutamiento, reintentos, certificados, autorización, tracing y manejo de fallas.

Las cifras originales de latencia «normalmente <10 ms» y sobrecarga de CPU/memoria «10–15 %» no tienen una fuente de medición verificada en este documento. Se conservan aquí como **estimaciones históricas no verificadas**, no como benchmarks ni garantías de dimensionamiento. Mida la latencia p50/p95/p99, el rendimiento, los errores y CPU/memoria con la misma combinación de solicitudes, TLS, muestreo de telemetría y carga antes/después de la inscripción. Incluya pruebas de despliegue de proxy, pérdida de nodo, pérdida de plano de control, rotación de certificados y amplificación por reintentos.

Adopte gradualmente en un namespace dedicado, valide un inyector, cargas de trabajo listas, mTLS y pruebas de políticas positivas/negativas y luego amplíe. Para LBC frente a un gateway de entrada de malla, exponga el Service de gateway y verifique los puertos/sondas de destino; el objeto API de Ingress es configuración, no otro salto de proxy. Use IAM de controlador con alcance donde se requiera; `cloudmap:*` no es un sustituto válido del prefijo de servicio IAM `servicediscovery`. La delegación de prefijo es una decisión de diseño de capacidad de IP, no un requisito previo de sidecar. Consulte los capítulos mantenidos de [instalación de Istio](../../service-mesh/istio/01-installation.md) e [integración con AWS](../../service-mesh/istio/04-aws-integration.md) para la implementación.

</details>

### 11. ¿Qué recurso de enrutamiento se usa para el balanceo de carga L7 (ALB) en Kubernetes Gateway API?

A. IngressRoute B. HTTPRoute C. VirtualService D. ServiceRoute

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B. HTTPRoute**

**Explicación:** En Kubernetes Gateway API, el recurso HTTPRoute se usa para el balanceo de carga L7. HTTPRoute define reglas para enrutar tráfico HTTP/HTTPS a servicios y, cuando se usa con AWS Load Balancer Controller, distribuye tráfico mediante un ALB.

**Jerarquía de recursos de Gateway API:**

1. **GatewayClass**: Define el tipo de balanceador de carga (por ejemplo, `amazon-alb`, `amazon-nlb`)
2. **Gateway**: Instancia real de balanceador de carga (puertos de listener, configuración TLS, etc.)
3. **HTTPRoute**: Reglas de enrutamiento L7 (enrutamiento basado en host, ruta y encabezado)
4. **TCPRoute**: Reglas de enrutamiento L4 (tráfico TCP)

LBC usa Gateways de ALB y NLB independientes; controllerName selecciona la implementación, no el nombre arbitrario del objeto GatewayClass. Confirme los filtros compatibles en la tabla de conformidad de la versión.

**Características principales de HTTPRoute:**

* Enrutamiento basado en rutas y hosts
* División de tráfico nativa basada en peso
* Coincidencia de encabezados y parámetros de consulta
* Enrutamiento a varios servicios de backend

Problemas con las demás opciones:

* **A. IngressRoute**: No es un recurso estándar de Gateway API.
* **C. VirtualService**: Es un recurso de la malla de servicios Istio.
* **D. ServiceRoute**: Este recurso no existe.

</details>

### 12. ¿Cómo se habilitan los controladores Gateway de LBC 3.5.0?

- A. Siempre pase `--enable-gateway-api`
- B. Detecte CRD compatibles con las gates reales habilitadas de forma predeterminada
- C. Use `--feature-gates=EnableGatewayAPI=true`
- D. Instale solo CRD experimentales de 1.2.1

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Detecte los CRD requeridos; ALBGatewayAPI/NLBGatewayAPI se habilitan de forma predeterminada.**

Instale los CRD estándar de Gateway API 1.6.0 compatibles con la versión y los CRD Gateway específicos de LBC. Las gates predeterminadas son `ALBGatewayAPI` y `NLBGatewayAPI`; `EnableGatewayAPI` es un nombre de característica desconocido. TCPRoute/UDPRoute ahora se sirven como v1 en el canal estándar. Las versiones anteriores del controlador tienen requisitos de compatibilidad/gating distintos: la compatibilidad L4 comienza en 2.13.3 y L7 en 2.14.0. Compruebe el inicio/logs del controlador después de instalar los CRD; los CRD por sí solos no proporcionan IAM, subredes ni backends de aplicación.

</details>

### 13. ¿Qué recurso se usa para enrutar tráfico TCP de nivel L4 a través de un NLB en Gateway API?

A. HTTPRoute B. TLSRoute C. TCPRoute D. GRPCRoute

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: C. TCPRoute**

**Explicación:** En Gateway API, el recurso TCPRoute se usa para enrutar tráfico TCP de nivel L4. Cuando se usa con AWS Load Balancer Controller, TCPRoute reenvía tráfico TCP a servicios de backend mediante un NLB (Network Load Balancer).

**Ejemplo de configuración de TCPRoute:**

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: TCPRoute
metadata:
  name: db-route
  namespace: gateway-demo
spec:
  parentRefs:
  - name: my-nlb-gateway
    sectionName: tcp
  rules:
  - backendRefs:
    - name: postgres-service
      port: 5432
```

**Uso de recursos de enrutamiento de Gateway API:**

| Recurso  | Protocolo   | Tipo de LB de AWS |
| --------- | ---------- | ----------- |
| HTTPRoute | HTTP/HTTPS | ALB         |
| TCPRoute  | TCP        | NLB         |
| TLSRoute  | TLS        | NLB         |
| GRPCRoute | gRPC       | ALB         |

Problemas con las demás opciones:

* **A. HTTPRoute**: Se usa para tráfico L7 HTTP/HTTPS con ALB.
* **B. TLSRoute**: Para el enrutamiento de tráfico TLS, pero TCPRoute es adecuado para el nivel TCP.
* **D. GRPCRoute**: Un recurso de enrutamiento específico para el protocolo gRPC.

</details>
El listener `my-nlb-gateway` y el Service de backend deben existir en `gateway-demo`. TLSRoute con esta implementación no proporciona enrutamiento NLB basado en SNI; use el comportamiento TLS específico de la versión en lugar de suponer que todas las implementaciones de Gateway API se comportan igual.

### 14. ¿Cómo configura LBC 3.5.0 un certificado estático para un ALB Gateway?

- A. Cree cualquier Secret llamado tls-cert
- B. Use el ARN de ACM en LoadBalancerConfiguration
- C. Añada solo un nombre de host de Route
- D. Configure el puerto 443 del Service de backend

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. `LoadBalancerConfiguration.spec.listenerConfigurations[].defaultCertificate`**

Use un ARN de certificado ACM válido de la misma Región para el listener HTTPS. Kubernetes Secret `certificateRefs` no es compatible con esta implementación. El descubrimiento de nombre de host también necesita un certificado ACM coincidente existente y un listener seguro. Un HTTPRoute con solo el puerto 443 de backend no configura HTTPS del lado del cliente.

</details>

### 15. ¿Una política de entrada solo de frontend restringe una política allow-all existente en el mismo namespace?

- A. Sí, gana la política más reciente
- B. Sí, gana el selector más específico
- C. No, los allow coincidentes forman una unión
- D. Solo si el nombre de la política se ordena primero

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C. No; los allow de NetworkPolicy coincidentes son aditivos.**

Ambas políticas seleccionan el backend, por lo que el allow más amplio del mismo namespace sigue permitiendo otros llamadores del mismo namespace. Elimine o restrinja la política más amplia a través de su propietario y luego pruebe conexiones permitidas y denegadas. El aislamiento de entrada y salida son independientes; la salida DNS y la entrada de destino pueden afectar cada una el resultado de una prueba.

</details>

Referencias oficiales: [LBC Gateway API](https://kubernetes-sigs.github.io/aws-load-balancer-controller/latest/guide/gateway/gateway/), [PrivateLink](https://docs.aws.amazon.com/vpc/latest/privatelink/create-endpoint-service.html), [IP de cliente de NLB](https://docs.aws.amazon.com/elasticloadbalancing/latest/network/edit-target-group-attributes.html), [asociaciones de WAF](https://docs.aws.amazon.com/waf/latest/developerguide/web-acl-associating-aws-resource.html), [retirada de App Mesh](https://docs.aws.amazon.com/app-mesh/latest/userguide/what-is-app-mesh.html).