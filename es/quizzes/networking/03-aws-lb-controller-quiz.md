# Cuestionario de AWS Load Balancer Controller

Basado en la guía de LBC v3.6.0 autoadministrado.

## 1. ¿Qué administra AWS Load Balancer Controller?

- A. Todas las responsabilidades del proveedor de nube, incluido el ciclo de vida de los nodos
- B. Recursos de balanceo de carga de AWS compatibles, reconciliados a partir de recursos de Kubernetes
- C. El reenvío de paquetes de kube-proxy
- D. Los registros de CoreDNS para todos los Pods

<details>
<summary>Mostrar respuesta</summary>

B. LBC administra los ALB/NLB, grupos de destino, listeners y recursos relacionados compatibles. No reemplaza kube-proxy, el CNI, DNS ni todas las responsabilidades del controlador de nube. El comportamiento del proveedor AWS heredado y EKS Auto Mode son implementaciones distintas; no afirme que LBC implemente todas las funciones de cada producto ELB.

</details>

## 2. ¿En qué se diferencian los destinos `ip` e `instance` de ALB?

- A. `ip` registra las IP de los Pods; `instance` enruta a través de NodePorts del nodo
- B. `ip` siempre enruta a través de NodePort
- C. Son idénticos
- D. `instance` solo funciona con IPv6

<details>
<summary>Mostrar respuesta</summary>

A. Los destinos IP requieren direcciones de Pod compatibles y enrutables en VPC, además del descubrimiento de endpoints/ENI. Amazon VPC CNI es la opción común en EKS, pero es posible usar una configuración compatible con otro CNI. Los destinos de instancia requieren un Service compatible con NodePort y una red de nodos adecuada. El direccionamiento directo no demuestra una ventaja de latencia concreta para todas las cargas de trabajo.

</details>

## 3. ¿Por qué necesita el controlador un rol IAM mediante IRSA o EKS Pod Identity?

- A. Para reemplazar las redes de los Pods
- B. Para autenticar y autorizar sus llamadas a las API de AWS
- C. Para reemplazar RBAC de Kubernetes
- D. Para autenticar todas las solicitudes de backend

<details>
<summary>Mostrar respuesta</summary>

B. El controlador llama a las API de AWS para crear/administrar balanceadores de carga, grupos de destino, listeners y los grupos de seguridad pertinentes. IRSA y las configuraciones compatibles de Pod Identity son alternativas. Un rol solo concede los permisos de la política asociada; usar un rol no hace automáticamente que la política aplique el principio de privilegio mínimo. RBAC de Kubernetes y la autenticación de aplicaciones son aspectos independientes.

</details>

## 4. ¿Cómo pueden varias Ingress compartir un mismo ALB?

- A. Basta con que estén en el mismo espacio de nombres
- B. Usar el mismo `alb.ingress.kubernetes.io/group.name`
- C. Todas las Ingress comparten siempre un ALB
- D. Establecer el mismo nombre de Pod

<details>
<summary>Mostrar respuesta</summary>

B. IngressGroup comparte el ALB y el espacio de reglas. Los valores más bajos de `group.order` se evalúan primero; los empates se resuelven por espacio de nombres/nombre. Úselo solo dentro de un límite de confianza aplicado, porque un usuario no confiable que pueda unirse al grupo puede afectar el enrutamiento. Revise el comportamiento de combinación/exclusividad de anotaciones, los límites y los costos; no suponga que siempre se ahorra.

</details>

## 5. ¿Qué anotación proporciona un certificado TLS de NLB?

- A. `service.beta.kubernetes.io/aws-load-balancer-ssl-cert`
- B. `alb.ingress.kubernetes.io/certificate-arn`
- C. `service.beta.kubernetes.io/aws-load-balancer-tls-termination`
- D. `nlb.kubernetes.io/ssl-certificate`

<details>
<summary>Mostrar respuesta</summary>

A. Este es un ejemplo completo de Service para LBC autoadministrado:

```yaml
apiVersion: v1
kind: Service
metadata:
  name: nlb-tls-service
  namespace: default
  annotations:
    service.beta.kubernetes.io/aws-load-balancer-nlb-target-type: ip
    service.beta.kubernetes.io/aws-load-balancer-scheme: internal
    service.beta.kubernetes.io/aws-load-balancer-ssl-cert: arn:aws:acm:us-east-1:123456789012:certificate/12345678-1234-1234-1234-123456789012
    service.beta.kubernetes.io/aws-load-balancer-ssl-ports: '443'
    service.beta.kubernetes.io/aws-load-balancer-backend-protocol: tcp
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

Reemplace el ARN del certificado y proporcione Pods de backend coincidentes que escuchen en 8080. TLS hacia el cliente termina en el NLB; aquí `tcp` deja sin TLS la conexión al backend. Use la política de certificado/seguridad y los controles de red adecuados. Auto Mode usa su propia `loadBalancerClass` y el conjunto de anotaciones compatibles.

</details>

## 6. ¿Para qué sirve un TargetGroupBinding creado por separado?

- A. Crear automáticamente todos los balanceadores de carga y listeners
- B. Registrar los destinos de un Service de Kubernetes en un grupo de destino existente
- C. Definir reglas de enrutamiento HTTP de listener ALB
- D. Reemplazar la autorización IAM

<details>
<summary>Mostrar respuesta</summary>

B. El balanceador de carga, el listener y el grupo de destino ya existen y deben coincidir con el Service y con el protocolo, la familia de direcciones y los puertos del destino.

```yaml
apiVersion: elbv2.k8s.aws/v1beta1
kind: TargetGroupBinding
metadata:
  name: my-tgb
  namespace: default
spec:
  targetGroupARN: arn:aws:elasticloadbalancing:us-east-1:123456789012:targetgroup/my-tg/1234567890abcdef
  serviceRef:
    name: my-service
    port: 80
  targetType: ip
```

Para compartir un grupo de destino entre varios clústeres/TGB, todos los participantes necesitan `multiClusterTargetGroup: true` desde su creación. De forma predeterminada se supone que hay propiedad completa, y se pueden dar de baja destinos ajenos. `nodeSelector` se aplica a destinos de instancia, no al filtrado de Pods en modo IP. Limite los permisos de TGB a usuarios de confianza.

</details>

## 7. ¿Qué anotación asocia un Web ACL regional de WAF v2 con un ALB?

- A. `alb.ingress.kubernetes.io/waf-acl-id`
- B. `alb.ingress.kubernetes.io/wafv2-acl-arn`
- C. `alb.ingress.kubernetes.io/web-acl`
- D. `alb.ingress.kubernetes.io/firewall-rules`

<details>
<summary>Mostrar respuesta</summary>

B. Proporcione el ARN del Web ACL regional existente en la región del ALB, configure sus reglas y otorgue los permisos necesarios al controlador. La integración de WAF v2 debe estar habilitada; está habilitada de forma predeterminada, así que no siempre es necesario especificar `enableWafv2`. Si la integración está deshabilitada, la anotación no se aplica. WAF y la protección de pago Shield Advanced son funciones distintas.

</details>

## 8. ¿Cuáles son las etiquetas convencionales para la función de las subredes?

- A. Solo `kubernetes.io/cluster/CLUSTER_NAME`
- B. `kubernetes.io/role/elb` para subredes públicas y `kubernetes.io/role/internal-elb` para privadas
- C. `aws:cloudformation:stack-name`
- D. Solo `Name=kubernetes-subnet`

<details>
<summary>Mostrar respuesta</summary>

B. En el descubrimiento de LBC autoadministrado, los valores pueden ser `1` o estar vacíos. Desde v2.12.1+, la alternativa predeterminada basada en accesibilidad puede clasificar subredes a partir de las tablas de rutas cuando faltan etiquetas de función coincidentes. Otras vías de selección son las subredes explícitas y los filtros de etiquetas de IngressClassParams. Auto Mode sigue requiriendo las etiquetas documentadas. Compruebe las etiquetas del clúster, las IP libres y los requisitos de zonas de disponibilidad; las etiquetas no modifican el enrutamiento.

</details>

## 9. ¿Cómo se configuran las sesiones persistentes de ALB?

- A. `alb.ingress.kubernetes.io/sticky-sessions=true`
- B. `target-group-attributes` con `stickiness.enabled=true`
- C. `session-affinity=cookie` en Ingress
- D. Siempre están habilitadas de forma predeterminada

<details>
<summary>Mostrar respuesta</summary>

B. Establezca `alb.ingress.kubernetes.io/target-type: ip` y combine `stickiness.enabled=true` con los atributos de cookie adecuados en una sola anotación `target-group-attributes`. No repita la clave YAML para el inicio lento ni el retraso de baja, porque las claves duplicadas pueden descartar ajustes. En una acción de reenvío ponderada, configure de manera coherente la persistencia del grupo de destino, según la documentación.

</details>

## 10. ¿Qué afirmación sobre la identidad del cliente en NLB es correcta?

- A. Proxy Protocol v2 cambia la dirección de origen del paquete IP por la del cliente
- B. `externalTrafficPolicy: Local` garantiza la conservación en todos los modos de destino
- C. Proxy Protocol transporta metadatos; la conservación del origen del paquete es un ajuste independiente con restricciones de red/protocolo
- D. NLB siempre conserva la IP del cliente

<details>
<summary>Mostrar respuesta</summary>

C. El backend debe analizar Proxy Protocol v2 antes de los datos de la aplicación y admitir las comprobaciones de estado aplicables. `preserve_client_ip.enabled` controla la conservación del origen del paquete cuando es compatible. En modo instancia/NodePort, `externalTrafficPolicy: Local` puede evitar un salto SNAT posterior de kube-proxy; no resuelve todas las rutas de NLB ni los casos de traducción entre familias IP. En destinos NLB ponderados, el cambio normal de pesos afecta a conexiones nuevas, pero asignar peso cero cierra las conexiones existentes al cabo de un período breve.

</details>

## 11. ¿Qué anotación configura la redirección HTTP a HTTPS de ALB?

- A. `alb.ingress.kubernetes.io/force-ssl-redirect`
- B. `alb.ingress.kubernetes.io/ssl-redirect: "443"`
- C. `alb.ingress.kubernetes.io/http-to-https`
- D. Siempre hace falta una HTTPRoute

<details>
<summary>Mostrar respuesta</summary>

B. Configure los listeners HTTP y HTTPS de destino, además de un certificado adecuado. Una vez habilitado, los listeners HTTP usan la acción de redirección predeterminada y se omiten sus demás reglas de enrutamiento. Afecta al IngressGroup, así que revise el comportamiento de todo el grupo. La autenticación Cognito/OIDC/JWT requiere HTTPS; una redirección por sí sola no autoriza la aplicación.

</details>

## 12. ¿Qué debe inspeccionar primero cuando no se crea un ALB?

- A. Solo los registros de kube-proxy
- B. El contenido de las cookies de la aplicación
- C. Los registros/eventos del controlador, la selección de clase, IAM, la elegibilidad de subredes y el estado de webhook/CRD
- D. Solo la cantidad de réplicas de Pods

<details>
<summary>Mostrar respuesta</summary>

C. Primero compruebe la ruta de reconciliación/plano de control. kube-proxy o un reemplazo eBPF pueden importar más adelante para el tráfico de nodo/servicio, pero no son el primer diagnóstico cuando falla una operación AWS CreateLoadBalancer. Que `kubectl apply` termine bien no demuestra que la reconciliación con AWS haya tenido éxito. Use ID de recursos y espacios de nombres reales, y limite la salida de los registros.

</details>

[Volver a la guía](../../networking/03-aws-lb-controller.md)
