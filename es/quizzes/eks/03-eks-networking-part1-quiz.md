# Cuestionario de redes de EKS - Parte 1

> **Última actualización**: 11 de septiembre de 2026

Este cuestionario repasa las redes de EKS, la planificación de direcciones, las políticas y la gestión de controladores. Salvo que se indique lo contrario, los ejemplos utilizan el modelo de red convencional de Linux en EC2. Las API y la configuración se contrastaron con fuentes oficiales y esquemas locales; no se modificó la red en la nube ni se hicieron pruebas de paquetes en vivo.

## Preguntas de opción múltiple

1. ¿Cuál es el CNI predeterminado para los nodos EC2 convencionales de EKS?
   * A) Calico
   * B) Flannel
   * C) Amazon VPC CNI
   * D) Weave Net

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Amazon VPC CNI**

Los nodos EC2 convencionales de EKS utilizan Amazon VPC CNI. Auto Mode ofrece capacidades de red administradas, y Hybrid Nodes utiliza un CNI alternativo compatible; por tanto, afirmar que «todos los clústeres de EKS ejecutan este DaemonSet» es demasiado general.

El CNI configura la red normal de los pods con direcciones de la VPC y distintas rutas para IP secundarias, prefijos y grupos de seguridad para pods. Tener una dirección enrutable no evita las rutas, los grupos de seguridad, las NACL ni las políticas; además, evitar una superposición de red no constituye una garantía de rendimiento medida.

En Linux, el antiguo ConfigMap `amazon-vpc-cni` con claves en minúsculas `warm-ip-target` y `enable-pod-eni` no es el mecanismo de configuración que se muestra aquí. Utiliza el esquema real del add-on, los valores de Helm o las variables de entorno admitidas de `aws-node`, gestionándolos desde su propietario. Primero inspecciona la versión instalada:

```bash
set -euo pipefail
CNI_ADDON_VERSION=$(aws eks describe-addon --cluster-name "${EXAMPLE_CLUSTER:?}" \
  --region "${EXAMPLE_REGION:?}" --addon-name vpc-cni --query addon.addonVersion --output text)
aws eks describe-addon-configuration --region "$EXAMPLE_REGION" --addon-name vpc-cni \
  --addon-version "$CNI_ADDON_VERSION" --query configurationSchema --output text
kubectl --kubeconfig "${EXAMPLE_KUBECONFIG:?}" -n kube-system get daemonset aws-node \
  -o jsonpath='{range .spec.template.spec.containers[*]}{.name}{": "}{.image}{"\n"}{end}'
```

Por ejemplo, lo siguiente es un **fragmento de configuración del add-on**, no un ConfigMap de Kubernetes. Los valores ilustran objetivos de reserva de IP; combínalos con la configuración existente que ya se haya revisado y comprueba el esquema de la versión elegida. La configuración del ConfigMap de IPAM de Windows es una interfaz distinta.

```json
{"env":{"WARM_IP_TARGET":"5","MINIMUM_IP_TARGET":"10"}}
```

Los grupos de seguridad para pods y NetworkPolicy nativa tienen requisitos previos propios. No los habilites como efectos secundarios ajenos a un ejemplo de pool de direcciones IP ni superpongas un segundo CNI sin configurar sobre un clúster en funcionamiento.

</details>

2. ¿Cómo se asignan direcciones a los pods normales en el modo IPv4 de IP secundaria?
   * A) Una VPC dedicada por pod
   * B) Una dirección del pool de ENI/IP del nodo
   * C) Solo una dirección de superposición
   * D) Una subred distinta para cada pod

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Una dirección del pool de ENI/IP del nodo**

En el modo normal de IP secundaria IPv4, IPAMD administra pools de ENI/IP en el nodo y la configuración del CNI asigna una dirección del pool al namespace de red del pod. Después de limpiar el CNI y de cualquier demora de reutilización aplicable, las direcciones pueden volver al pool de reserva; no necesariamente se desasignan de EC2 de inmediato.

El cálculo convencional de maxPods que aparece a continuación corresponde a ese modo. Se reserva la dirección principal de cada ENI; los dos adicionales que se suman históricamente corresponden a pods del sistema con hostNetwork:

```text
ENIs × (IPv4 addresses per ENI − 1) + 2
m5.large: 3 × (10 − 1) + 2 = 29
```

No es un límite universal de cargas de trabajo. También influyen el espacio de la subred, maxPods de kubelet, los recursos de cómputo, la red personalizada y los límites de branch ENI. El modo de prefijos asigna un `/28` a una ranura de dirección de ENI; no asigna exactamente un prefijo por ENI. Los grupos de seguridad para pods usan una ruta independiente de branch ENI. Los pods con hostNetwork comparten la red del nodo y son otra excepción a la descripción simple de una IP secundaria por pod.

</details>

3. ¿Qué permite el modelo normal de enrutamiento intra-VPC de VPC CNI?
   * A) Que todos los pods utilicen una sola subred
   * B) Que todos los pods compartan la red del host
   * C) Direcciones de pods enrutables en la VPC y las rutas y controles necesarios
   * D) Un service mesh obligatorio

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Direcciones de pods enrutables en la VPC y las rutas y controles necesarios**

En la ruta normal de VPC CNI, los pods tienen direcciones enrutables en la VPC. El tráfico entre nodos puede utilizar el enrutamiento de los nodos/ENI y de la VPC; el tráfico en el mismo nodo puede permanecer en la pila de red del host. Los grupos de seguridad, las NACL, las reglas de políticas y las rutas de inspección personalizadas siguen determinando la conectividad.

El ejemplo `10.0.1.23 → 10.0.2.45` describe una ruta intra-VPC normal; no demuestra que todos los paquetes atraviesen siempre una tabla de rutas de la VPC ni que nunca sigan una ruta configurada hacia un dispositivo de red. El tráfico de pods en el mismo nodo no se ve por completo en VPC Flow Logs. La mayoría de los pods tienen su propio namespace de red; los pods con hostNetwork son una excepción.

No deduzcas mejoras garantizadas de latencia o rendimiento por la ausencia de una red de superposición. Mide la ruta real y ten en cuenta el tráfico entre zonas de disponibilidad, el tipo de destino, SNAT y el comportamiento de la carga de trabajo. El service mesh es una capa adicional opcional, no un requisito para el enrutamiento normal de pods.

</details>

4. ¿Qué recurso de Kubernetes expresa las políticas de entrada y salida de los pods?
   * A) Service
   * B) Ingress
   * C) NetworkPolicy
   * D) SecurityContext

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) NetworkPolicy**

NetworkPolicy selecciona pods y aísla solo las direcciones de tráfico especificadas. Si ninguna política selecciona un pod y una dirección de tráfico, ese tráfico no está aislado. Las políticas son aditivas: una política adicional que parezca más restrictiva no puede retirar tráfico que otra política ya permite.

Utiliza una implementación de aplicación de políticas compatible. Amazon VPC CNI admite actualmente políticas de red nativas cuando se habilitan; es incorrecto afirmar que no puede aplicarlas. El add-on administrado utiliza el campo de configuración `enableNetworkPolicy`, no la variable de entorno `ENABLE_NETWORK_POLICY` que a veces se supone:

```json
{"enableNetworkPolicy":"true"}
```

Este es un fragmento que se debe combinar según el esquema de la versión elegida del add-on. Antes de probarlo, comprueba el agente de políticas y sus limitaciones de cómputo de AWS, kernel, propietario del pod e interfaz. El modo de inicio estándar puede permitir tráfico brevemente antes de asociar la política; el modo estricto requiere todas las excepciones necesarias para el sistema y DNS. No instales manifiestos flotantes de Calico junto con la aplicación de políticas nativa sin un plan de migración compatible.

Lo siguiente está pensado para namespaces de laboratorio revisados y cargas de trabajo gestionadas por controladores. Los selectores de namespace y de pod dentro del **mismo elemento peer se combinan con AND**; elementos peer separados se combinarían con OR. La excepción de DNS es explícita:

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: api-allow
  namespace: policy-lab
spec:
  podSelector:
    matchLabels: {app: api}
  policyTypes: [Ingress, Egress]
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          kubernetes.io/metadata.name: frontend-lab
      podSelector:
        matchLabels: {role: frontend}
    ports:
    - {protocol: TCP, port: 8080}
  egress:
  - to:
    - namespaceSelector:
        matchLabels:
          kubernetes.io/metadata.name: database-lab
      podSelector:
        matchLabels: {app: database}
    ports:
    - {protocol: TCP, port: 5432}
  - to:
    - namespaceSelector:
        matchLabels:
          kubernetes.io/metadata.name: kube-system
      podSelector:
        matchLabels: {k8s-app: kube-dns}
    ports:
    - {protocol: UDP, port: 53}
    - {protocol: TCP, port: 53}
```

Utiliza las etiquetas reales de namespaces y pods, y los puertos de escucha reales. NodeLocal DNSCache y otras rutas de DNS requieren excepciones distintas. Service e Ingress enrutan tráfico; no sustituyen estas reglas de acceso L3/L4. SecurityContext controla los privilegios de una carga de trabajo, no es una lista declarativa de permisos de red.

</details>

5. ¿Qué componente DNS se suele configurar para el descubrimiento de servicios en un clúster convencional de EKS?
   * A) Solo zonas alojadas privadas de Route 53
   * B) CoreDNS
   * C) Un despliegue kube-dns heredado obligatorio
   * D) Solo Cloud Map

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) CoreDNS**

EKS convencional utiliza CoreDNS para el DNS del clúster. No supongas que todos los modos de EKS crean automáticamente un Deployment de CoreDNS visible: Auto Mode proporciona DNS administrado y las herramientas que deshabilitan los add-ons de arranque predeterminados deben configurar explícitamente los add-ons que elijan.

Para el add-on de CoreDNS administrado por EKS, conserva la configuración personalizada mediante el valor de configuración `corefile` admitido y el esquema de la versión exacta. El add-on puede sobrescribir los cambios directos al ConfigMap. Si CoreDNS es autogestionado, cambia la configuración mediante el propietario de su manifiesto/GitOps. Revisa las zonas de Kubernetes necesarias, `ready`, el reenvío y el comportamiento de recarga en vez de sustituir todo el ConfigMap con un ejemplo genérico.

Las respuestas DNS dependen del tipo de recurso:

| Recurso | Comportamiento DNS habitual |
| --- | --- |
| Service normal | `<service>.<namespace>.svc.<cluster-domain>` resuelve a la familia de direcciones IP del Service |
| Service sin cabecera (headless) | Direcciones de endpoints, según la configuración de readiness/publicación |
| Service ExternalName | CNAME al nombre externo configurado |
| Registro heredado de pod IPv4 | Dirección con guiones, como `10-0-1-23.<namespace>.pod.<cluster-domain>`, según el modo `pods` de CoreDNS |

`cluster.local` es un valor predeterminado común, no un dominio universal. `pods insecure` proporciona respuestas heredadas basadas en IP sin comprobar que exista el pod; no constituye una garantía de seguridad. Prueba DNS desde una carga de diagnóstico aprobada dentro del clúster, no desde el resolver arbitrario de un portátil.

CoreDNS administrado por EKS admite el escalado automático configurado en versiones compatibles del add-on. Mantén un solo propietario del número de réplicas: `kubectl scale` manual no es el bucle de control adecuado cuando el escalado automático administrado o HPA está activo.

El siguiente **fragmento de Corefile** sustituye una directiva `cache` existente después de revisarla; no es YAML. CoreDNS 1.14.7 acepta `denial 1000`, pero normaliza el valor a una capacidad efectiva mínima de 1024. El ejemplo especifica esa capacidad; `success 10000` se redondea a 9984:

```text
cache {
    success 10000
    denial 1024
    prefetch 10 10m 20%
}
```

Las capacidades de caché, TTL y prefetch requieren mediciones de la carga de trabajo; esto no es una prueba de rendimiento. Después de un cambio controlado, observa los errores DNS, el comportamiento de la caché y el consumo de CPU y memoria.

</details>

## Preguntas de respuesta corta

6. ¿Qué limita la densidad de pods y cómo la modifica la delegación de prefijos?

<details>
<summary>Mostrar respuesta</summary>

Distingue tres límites: capacidad de interfaces/direcciones de EC2, direcciones disponibles en la subred y capacidad de Kubernetes/cómputo. Requieren soluciones distintas. En el modo normal de IP secundaria IPv4, la fórmula histórica es `ENIs × (IPs por ENI − 1) + 2`: t3.small da 11, m5.large da 29 y c5.4xlarge da 234. Son resultados de la fórmula, no el límite efectivo de todos los grupos administrados.

En modo de prefijos IPv4, un `/28` aporta 16 direcciones y ocupa una ranura de dirección secundaria. Una ENI puede alojar varios prefijos. El antiguo cálculo «un prefijo por ENI menos una dirección», que daba 47 para m5.large, era incorrecto. Los grupos administrados compatibles limitan maxPods a 110 si tienen menos de 30 vCPU y a 250 en los demás casos; la CPU, la memoria y la configuración real del CNI pueden reducir aún más la capacidad de carga utilizable.

Este es un ejemplo de fragmento de configuración de add-on administrado:

```json
{"env":{"ENABLE_PREFIX_DELEGATION":"true","WARM_PREFIX_TARGET":"1"}}
```

Revisa el esquema de la versión exacta y la configuración existente antes de combinar el fragmento. WARM_PREFIX_TARGET es la capacidad de prefijos de reserva, no un máximo de un prefijo por ENI. Si se configuran WARM_IP_TARGET o MINIMUM_IP_TARGET, modifican ese comportamiento. El modo de prefijos requiere espacio contiguo `/28` y una instancia/CNI compatible; no amplía la subred.

La delegación de prefijos puede coexistir con grupos de seguridad para pods. Los pods con branch ENI siguen sujetos a su propia capacidad por instancia y no obtienen la densidad de prefijos. Planifica nodos nuevos o renovados y una migración compatible con PDB; no te limites a cambiar variables suponiendo que cambiarán todos los pods en ejecución o maxPods. Las AMI AL2023 personalizadas pueden requerir un maxPods revisado en NodeConfig; aumentar solo el límite de kubelet no crea direcciones IP ni CPU.

```bash
kubectl --kubeconfig "${EXAMPLE_KUBECONFIG:?}" get nodes \
  -o custom-columns=NAME:.metadata.name,PODS:.status.allocatable.pods,POD_ENI:.status.allocatable.vpc\\.amazonaws\\.com/pod-eni
```

Inspecciona la capacidad asignable real y la asignación del CNI/EC2. No supongas que el contenedor aws-node incluye curl; utiliza la ruta documentada de introspección/depuración para la versión instalada y el nodo elegido.

</details>

7. ¿Cómo se asignan grupos de seguridad a determinados pods en nodos EC2 convencionales de EKS?

<details>
<summary>Mostrar respuesta</summary>

Security Groups for Pods utiliza una **trunk ENI en el nodo y branch ENI para los pods seleccionados**. El controlador de recursos de VPC de EKS crea y gestiona esta ruta con permisos del **rol IAM del clúster**, incluido `AmazonEKSVPCResourceController`; no se trata simplemente de permisos de ServiceAccount por pod.

Para el ejemplo convencional de Linux en EC2, comprueba que el tipo de instancia admite trunking (no todos los tipos Nitro cumplen este requisito), que VPC CNI es compatible y que `ENABLE_POD_ENI=true` se configura a través de su propietario. Revisa `POD_SECURITY_GROUP_ENFORCING_MODE`, DNS, sondas, rutas y reglas de los grupos de seguridad. Los modos estricto y estándar difieren en SNAT y en los grupos de seguridad aplicables, especialmente fuera de la VPC y en rutas locales al nodo.

Crea el namespace dedicado `sgp-lab` y sustituye el marcador del grupo de seguridad por uno aprobado en la VPC correcta. Este cliente de laboratorio gestionado por un controlador que permanece inactivo demuestra la selección, no que se haya accedido correctamente a una base de datos:

```yaml
apiVersion: vpcresources.k8s.aws/v1beta1
kind: SecurityGroupPolicy
metadata:
  name: db-client-policy
  namespace: sgp-lab
spec:
  podSelector:
    matchLabels: {role: db-client}
  securityGroups:
    groupIds: [sg-REPLACE_WITH_APPROVED_GROUP]
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: db-client
  namespace: sgp-lab
spec:
  replicas: 1
  selector:
    matchLabels: {role: db-client}
  template:
    metadata:
      labels: {role: db-client}
    spec:
      automountServiceAccountToken: false
      securityContext:
        runAsNonRoot: true
        runAsUser: 1000
        seccompProfile: {type: RuntimeDefault}
      containers:
      - name: client
        image: public.ecr.aws/docker/library/busybox:1.38.0
        command: [sleep, '3600']
        resources:
          requests: {cpu: 10m, memory: 16Mi}
          limits: {cpu: 100m, memory: 32Mi}
        securityContext:
          allowPrivilegeEscalation: false
          readOnlyRootFilesystem: true
          capabilities: {drop: [ALL]}
```

Utiliza un selector de pods o un selector de ServiceAccount, según corresponda. Comprueba el pod recién creado, el CNINode/capacidad de branch ENI y las conexiones permitidas y denegadas a la aplicación. Cambiar la selección de SecurityGroupPolicy no modifica retroactivamente los pods en ejecución; los cambios independientes de reglas de SG tienen su propio comportamiento de seguimiento de conexiones. Los pods con hostNetwork utilizan la red del nodo.

La delegación de prefijos es compatible, pero no aumenta la capacidad de los pods con branch ENI. La función tradicional SecurityGroupPolicy no es la función de selección de subredes/SG de NodeClass de Auto Mode; sigue la API correspondiente al tipo de cómputo en vez de tratarlas como si fueran iguales.

</details>

8. ¿Qué balanceador crea AWS Load Balancer Controller para un Service de tipo LoadBalancer y cómo se configura su propietario?

<details>
<summary>Mostrar respuesta</summary>

AWS Load Balancer Controller reconcilia un Service LoadBalancer como un **NLB**, no como un CLB. El antiguo cuestionario lo confundía con el controlador de Service integrado heredado. LBC utiliza `service.k8s.aws/nlb` para indicar explícitamente quién administra el recurso y, desde v2.2, los NLB nuevos tienen como valor predeterminado el esquema **internal**. Configura explícitamente el esquema deseado.

Este ejemplo crea un Service nuevo para una carga de trabajo `app=echo` existente y revisada en `lb-lab`, después de instalar y autorizar el controlador y validar las subredes/grupos de seguridad aptos. Aprovisiona un NLB interno con coste; no lo apliques a la ligera en un namespace de producción:

```yaml
apiVersion: v1
kind: Service
metadata:
  name: echo-nlb
  namespace: lb-lab
  annotations:
    service.beta.kubernetes.io/aws-load-balancer-scheme: internal
    service.beta.kubernetes.io/aws-load-balancer-nlb-target-type: ip
spec:
  type: LoadBalancer
  loadBalancerClass: service.k8s.aws/nlb
  allocateLoadBalancerNodePorts: false
  selector: {app: echo}
  ports:
  - name: http
    port: 8080
    targetPort: 8080
    protocol: TCP
```

Los destinos IP envían tráfico a las IP de pods aptas; los destinos instance utilizan rutas de nodo/NodePort. En modo IP, el ejemplo deshabilita la asignación de NodePort no utilizada. Auto Mode utiliza su propia clase de propietario (`eks.amazonaws.com/nlb`) y un conjunto de configuración compatible. No cambies las anotaciones/clases de selección del controlador de un Service heredado existente para intentar una migración no revisada; podrías filtrar o exponer recursos.

Las **opciones de configuración** deben coincidir con la versión del controlador y el diseño de listeners elegidos. En la tabla se omite el prefijo común `service.beta.kubernetes.io/` de los nombres de anotación.

| Requisito | Configuración/consideración actual |
| --- | --- |
| Esquema interno o público | `aws-load-balancer-scheme: internal` o `internet-facing`; las rutas y subredes deben coincidir |
| Destinos IP | `aws-load-balancer-nlb-target-type: ip` |
| Grupos de seguridad frontend personalizados | `aws-load-balancer-security-groups`; revisa la gestión de reglas backend y las rutas de health check |
| Subredes explícitas | `aws-load-balancer-subnets`; siguen aplicándose los requisitos de aptitud, zona de disponibilidad e IP |
| Comportamiento entre zonas | `aws-load-balancer-attributes` con `load_balancing.cross_zone.enabled`; evalúa disponibilidad, topología y coste |
| Registros S3 heredados | `aws-load-balancer-attributes` con `access_logs.s3.*`; los registros de acceso de NLB solo cubren solicitudes TLS y requieren revisar el bucket y los permisos de entrega |
| Terminación TLS | `aws-load-balancer-ssl-cert` y los puertos de listener del Service correspondientes en `aws-load-balancer-ssl-ports`; es terminación TLS de NLB, no enrutamiento HTTP de ALB |

Las anotaciones antiguas `aws-load-balancer-internal`, de balanceo entre zonas y de registro de acceso están obsoletas y se sustituyen por opciones de esquema/atributos. El NLB actual también ofrece entrega mejorada de registros de CloudWatch; utiliza su integración documentada en vez de suponer que las anotaciones S3 la configuran. Los registros de acceso son de mejor esfuerzo, no un registro exhaustivo de solicitudes.

**Alternativa ALB:** utiliza un Ingress con una IngressClass `alb` configurada y destinos IP hacia un backend ClusterIP. Así se evita crear por accidente un NLB y un ALB para el mismo backend de ejemplo:

```yaml
apiVersion: v1
kind: Service
metadata:
  name: echo-backend
  namespace: lb-lab
spec:
  type: ClusterIP
  selector: {app: echo}
  ports:
  - {port: 8080, targetPort: 8080, protocol: TCP}
---
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: echo-alb
  namespace: lb-lab
  annotations:
    alb.ingress.kubernetes.io/scheme: internal
    alb.ingress.kubernetes.io/target-type: ip
spec:
  ingressClassName: alb
  rules:
  - http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: echo-backend
            port: {number: 8080}
```

Antes de instalarlo, prepara el ServiceAccount del controlador y permisos IAM de alcance limitado. El chart revisado 3.5.0 contiene el controlador v3.5.0; la región y la VPC se especifican explícitamente en entornos donde no está disponible la detección por IMDS. Renderiza e inspecciona antes de desplegar:

```bash
helm repo add eks https://aws.github.io/eks-charts
helm repo update eks
helm template aws-load-balancer-controller eks/aws-load-balancer-controller \
  --version 3.5.0 --kube-version 1.36.0 --namespace kube-system \
  --set-string clusterName="${EXAMPLE_CLUSTER:?}" \
  --set-string region="${EXAMPLE_REGION:?}" --set-string vpcId="${EXAMPLE_VPC_ID:?}" \
  --set serviceAccount.create=false --set-string serviceAccount.name=aws-load-balancer-controller \
  > lbc-reviewed.yaml
```

| Capacidad | CLB (heredado) | NLB | ALB |
| --- | --- | --- | --- |
| Capa principal de enrutamiento | Listeners L4/L7 heredados | L4 | L7 HTTP/HTTPS |
| Destinos IP directos | No | Sí | Sí |
| Opción de dirección estática por zona | No | Sí | No tiene una IP frontend estática nativa |
| Enrutamiento por ruta HTTP | No | No | Sí |

NLB admite actualmente listeners TCP, TLS, UDP, TCP_UDP, QUIC y TCP_QUIC. El soporte y la configuración del controlador deben comprobarse por separado (LBC 3.5 documenta anotaciones de puerto QUIC). La antigua tabla cualitativa «bueno/muy bueno» no era un benchmark. Elige y mide según la aplicación; habilitar universalmente el tráfico entre zonas o aplicar una clasificación general de latencia no es una regla de producción.

</details>

## Preguntas prácticas

9. Implementa y valida tráfico dentro del mismo namespace con una excepción DNS y rutas TCP bloqueadas entre namespaces.

<details>
<summary>Mostrar respuesta</summary>

Utiliza una política que seleccione todos los pods del namespace previsto y permita los pods del mismo namespace más una excepción DNS explícita. Es una política L3/L4, no una prueba de aislamiento completo de tenants o nodos.

**Requisitos previos:** un clúster de prueba aprobado, convencional, Linux e IPv4, con NetworkPolicy nativa de VPC CNI ya habilitada mediante el propietario/mecanismo de configuración admitido; pods de prueba gestionados por controladores; CoreDNS operativo; y ninguna política organizativa en conflicto. No instales Calico ni cambies como parte de este laboratorio una variable `ENABLE_NETWORK_POLICY` inventada.

Crea dos namespaces nuevos y registra sus UID. Utiliza una única sesión de Bash para los siguientes fragmentos:

```bash
set -euo pipefail
umask 077
: "${EXAMPLE_KUBECONFIG:?Use the reviewed IPv4 Linux lab cluster kubeconfig}"
NP_LAB_DIR=$(mktemp -d /tmp/eks-network-policy.XXXXXX)
NP_LAB_ID="$(date +%s)-$$"
NP_NAMESPACE_A="np-a-$NP_LAB_ID"
NP_NAMESPACE_B="np-b-$NP_LAB_ID"
for ns in "$NP_NAMESPACE_A" "$NP_NAMESPACE_B"; do
  kubectl --kubeconfig "$EXAMPLE_KUBECONFIG" create namespace "$ns" -o json \
    > "$NP_LAB_DIR/$ns-created.json"
  jq -e '.metadata.uid | type == "string" and length > 0' \
    "$NP_LAB_DIR/$ns-created.json" >/dev/null
done
```

Los servidores HTTP también ofrecen un diagnóstico TCP conocido en Python. Cada Service y contenedor utiliza el puerto 8080. Son cargas de prueba, no valores de dimensionamiento para producción; registra los digest de imagen para poder repetir la prueba.

```bash
for ns in "$NP_NAMESPACE_A" "$NP_NAMESPACE_B"; do
  kubectl --kubeconfig "$EXAMPLE_KUBECONFIG" -n "$ns" create -f - <<'EOF'
apiVersion: apps/v1
kind: Deployment
metadata:
  name: network-probe
spec:
  replicas: 1
  selector:
    matchLabels: {app: network-probe}
  template:
    metadata:
      labels: {app: network-probe}
    spec:
      automountServiceAccountToken: false
      nodeSelector: {kubernetes.io/os: linux}
      securityContext:
        runAsNonRoot: true
        runAsUser: 1000
        seccompProfile: {type: RuntimeDefault}
      containers:
      - name: probe
        image: python:3.13-alpine
        command: [python, -m, http.server, "8080", --directory, /tmp]
        ports:
        - containerPort: 8080
        readinessProbe:
          tcpSocket: {port: 8080}
        resources:
          requests: {cpu: 50m, memory: 64Mi}
          limits: {cpu: 200m, memory: 128Mi}
        securityContext:
          allowPrivilegeEscalation: false
          readOnlyRootFilesystem: true
          capabilities: {drop: [ALL]}
---
apiVersion: v1
kind: Service
metadata:
  name: network-probe
spec:
  type: ClusterIP
  selector: {app: network-probe}
  ports:
  - {port: 8080, targetPort: 8080, protocol: TCP}
EOF
  kubectl --kubeconfig "$EXAMPLE_KUBECONFIG" -n "$ns" \
    rollout status deployment/network-probe --timeout=180s
done
```

**Línea base:** antes de aplicar una política, exige que funcionen las conexiones TCP dentro del mismo namespace y entre namespaces. Los fallos de DNS/exec no son lo mismo que las conexiones TCP denegadas. Hacer ping por ICMP no es una prueba portátil de aplicación de NetworkPolicy.

```bash
check_tcp() {
  kubectl --kubeconfig "$EXAMPLE_KUBECONFIG" -n "$1" exec deployment/network-probe \
    -c probe -- python -c '
import socket, sys
try:
    address = socket.gethostbyname(sys.argv[1])
except OSError as error:
    print("DNS failed:", error, file=sys.stderr)
    sys.exit(43)
try:
    connection = socket.create_connection((address, 8080), timeout=3)
    connection.close()
except OSError as error:
    print("TCP failed:", error, file=sys.stderr)
    sys.exit(42)
print("TCP succeeded")
' "network-probe.$2"
}

# All four paths must work before applying the policy.
check_tcp "$NP_NAMESPACE_A" "$NP_NAMESPACE_A"
check_tcp "$NP_NAMESPACE_B" "$NP_NAMESPACE_B"
check_tcp "$NP_NAMESPACE_A" "$NP_NAMESPACE_B"
check_tcp "$NP_NAMESPACE_B" "$NP_NAMESPACE_A"
```

**Aplicar solo al namespace A:** un podSelector peer vacío selecciona los pods de ese namespace de política. El peer DNS combina el namespace kube-system con la etiqueta del pod CoreDNS. Adáptalo si utilizas NodeLocal DNSCache u otra ruta DNS. La asociación de políticas estándar es asíncrona; prueba su propagación con controles positivos y las dos direcciones bloqueadas:

```bash
kubectl --kubeconfig "$EXAMPLE_KUBECONFIG" -n "$NP_NAMESPACE_A" create -f - <<'EOF'
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: namespace-boundary
spec:
  podSelector: {}
  policyTypes: [Ingress, Egress]
  ingress:
  - from:
    - podSelector: {}
  egress:
  - to:
    - podSelector: {}
  - to:
    - namespaceSelector:
        matchLabels:
          kubernetes.io/metadata.name: kube-system
      podSelector:
        matchLabels:
          k8s-app: kube-dns
    ports:
    - {protocol: UDP, port: 53}
    - {protocol: TCP, port: 53}
EOF

expect_tcp_block() {
  if check_tcp "$1" "$2"; then
    return 1
  else
    result=$?
    [ "$result" -eq 42 ] || {
      printf '%s\n' 'DNS or exec failure is not proof of policy denial.' >&2
      exit 1
    }
    return 0
  fi
}
NP_VERIFIED=false
for attempt in $(seq 1 30); do
  check_tcp "$NP_NAMESPACE_A" "$NP_NAMESPACE_A"
  check_tcp "$NP_NAMESPACE_B" "$NP_NAMESPACE_B"
  if expect_tcp_block "$NP_NAMESPACE_A" "$NP_NAMESPACE_B" &&
     expect_tcp_block "$NP_NAMESPACE_B" "$NP_NAMESPACE_A"; then
    # Repeat positive controls after observing both blocked cross-namespace paths.
    check_tcp "$NP_NAMESPACE_A" "$NP_NAMESPACE_A"
    check_tcp "$NP_NAMESPACE_B" "$NP_NAMESPACE_B"
    NP_VERIFIED=true
    break
  fi
  sleep 2
done
[ "$NP_VERIFIED" = true ] || {
  printf '%s\n' 'Expected policy behavior was not observed; inspect the enforcement path.' >&2
  exit 1
}
```

El resultado correcto significa que las rutas TCP probadas se comportaron como se esperaba y que las comprobaciones de DNS y disponibilidad del servidor pasaron. No demuestra que se filtren todos los protocolos o interfaces. Mantén aparte los controles de nodo, el servicio de metadatos y los grupos de seguridad de la plataforma.

**Extensiones:** para permitir únicamente ciertos pods o puertos del mismo namespace, sustituye/revisa las reglas amplias que los permiten. Añadir una política más estrecha no puede retirar una regla de permiso amplia ya existente. Para una API externa revisada, una política adicional de egress puede seleccionar el CIDR/puerto requerido; el prefijo de documentación de este ejemplo no es un destino activo:

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-reviewed-external-api
  namespace: app-namespace
spec:
  podSelector:
    matchLabels: {app: web}
  policyTypes: [Egress]
  egress:
  - to:
    - ipBlock:
        cidr: 203.0.113.0/24
    ports:
    - {protocol: TCP, port: 443}
```

NetworkPolicy estándar no proporciona una lista de permitidos por FQDN. NAT y la selección de endpoints pueden afectar a la IP evaluada. Una regla general `0.0.0.0/0` que solo excluya rangos RFC1918 no es una regla específica para un servicio externo ni una protección completa para los endpoints de metadatos link-local.

Después de la prueba, elimina solo los namespaces cuyos UID registraste:

```bash
for ns in "${NP_NAMESPACE_A:?}" "${NP_NAMESPACE_B:?}"; do
  expected_uid=$(jq -er '.metadata.uid' "${NP_LAB_DIR:?}/$ns-created.json") || exit 1
  current_uid=$(kubectl --kubeconfig "${EXAMPLE_KUBECONFIG:?}" get namespace "$ns" \
    --ignore-not-found -o jsonpath='{.metadata.uid}') || exit 1
  if [ -z "$current_uid" ]; then
    continue
  elif [ "$current_uid" = "$expected_uid" ]; then
    kubectl --kubeconfig "$EXAMPLE_KUBECONFIG" delete namespace "$ns" --wait=true || exit 1
  else
    printf '%s\n' 'Namespace UID changed; no deletion attempted for this namespace.' >&2
    exit 1
  fi
done
```

</details>

## Preguntas avanzadas

10. Compara soluciones para el agotamiento de direcciones de VPC CNI y distingue la densidad de nodos del espacio total de direcciones.

<details>
<summary>Mostrar respuesta</summary>

Primero identifica qué recurso se agotó: direcciones de subred, bloques de prefijos contiguos, ranuras de ENI por nodo, branch ENI, maxPods de kubelet o capacidad de cómputo. Cada caso necesita una solución distinta. La conclusión anterior de que «la delegación de prefijos siempre es la solución más sencilla» era demasiado general.

| Enfoque | Para qué ayuda | Limitación importante |
| --- | --- | --- |
| Delegación de prefijos | Más direcciones de pods por ranura de ENI normal; eficiencia de asignación | Requiere `/28` contiguos; no amplía el espacio IPv4 ni la capacidad de branch ENI |
| Ajuste de pools warm/minimum | Direcciones preasignadas sin utilizar | Intercambia disponibilidad inmediata de asignación/llamadas de API por uso de direcciones |
| Red personalizada | Separa la demanda de subred de nodos y pods | Mismos requisitos de VPC/zona de disponibilidad, rutas/SG y migración planificada de nodos |
| CIDR/subredes adicionales de VPC | Más espacio de direcciones asignables | Hay que revisar solapamientos/cuotas/enrutamiento y reconciliación del plano de control |
| Rangos mayores en subredes nuevas | Crecimiento planificado de direcciones | Las subredes existentes no se pueden ampliar sin más; los rangos deben caber en CIDR de VPC asociados |
| Diseño de clúster IPv6 | Elimina gran parte de la presión de direcciones IPv4 compartidas para pods | Planificación de nuevo clúster/familia IP, cómputo/CNI compatible y requisitos de egress |
| CNI alternativo | Otro modelo de IPAM/enrutamiento | Requiere una migración compatible y probada; no basta con cambiar un manifiesto en el sitio |
| Fargate | Delega operaciones de asignación de nodos/IP | Cada pod sigue consumiendo direcciones de subred/VPC; no soluciona el agotamiento de una subred |

**Modo de prefijos:** los prefijos IPv4 normales son bloques `/28`, cada uno de los cuales consume una ranura de dirección. La afirmación original de «hasta 5x» es genérica y no está verificada como benchmark; utiliza los límites reales de instancia/CNI/kubelet. Los grupos de seguridad para pods pueden coexistir, pero los pods con branch ENI conservan sus propios límites. Si es necesario, comprueba la fragmentación y reserva espacio para prefijos o utiliza subredes nuevas; no supongas que el número de IP individuales libres demuestra que hay un bloque contiguo disponible.

**Pools warm:** `WARM_IP_TARGET` es el margen de direcciones libres y `MINIMUM_IP_TARGET` es la asignación total mínima. Pueden prevalecer sobre el comportamiento de objetivos warm para prefijos/ENI. Los valores de ejemplo 5/10 deben ajustarse a la carga de trabajo y al presupuesto de llamadas de API:

```json
{"env":{"WARM_IP_TARGET":"5","MINIMUM_IP_TARGET":"10"}}
```

`MAX_ENI` limita las asignaciones del nodo hasta el máximo permitido por el tipo de instancia EC2; establecerlo en 5 no permite utilizar cinco ENI en un tipo que admita menos. Revisa las métricas de asignación reales antes de cambiar los límites.

**Red personalizada:** combina esta configuración a través del propietario existente del CNI, después de preparar subredes de pods y grupos de seguridad en la misma VPC y zona de disponibilidad. La etiqueta de zona estable es `topology.kubernetes.io/zone`, no la etiqueta beta obsoleta:

```json
{
  "env": {
    "AWS_VPC_K8S_CNI_CUSTOM_NETWORK_CFG": "true",
    "ENI_CONFIG_LABEL_DEF": "topology.kubernetes.io/zone"
  }
}
```

```yaml
apiVersion: crd.k8s.amazonaws.com/v1alpha1
kind: ENIConfig
metadata:
  name: us-west-2a
spec:
  subnet: subnet-REPLACE_WITH_POD_SUBNET_IN_SAME_VPC_AND_AZ
  securityGroups:
  - sg-REPLACE_WITH_APPROVED_POD_GROUP
```

Crea un ENIConfig correspondiente para cada zona de disponibilidad utilizada. Revisa las anulaciones de anotaciones de nodo. Los nodos de sustitución con la etiqueta de zona correcta pueden reutilizar el ENIConfig existente; no es necesario recrearlo cada vez. La red de todos los pods existentes no cambia de inmediato. Valida los nodos de sustitución y migra con comprobaciones de capacidad, PDB y datos.

**Cambios de CIDR/subred:** añade CIDR no solapados aptos y sus subredes asociadas a través del propietario de IaC; después revisa rutas, seguridad, endpoints y etiquetas de descubrimiento. EKS puede tardar hasta una hora en reconocer un CIDR de VPC recién asociado para operaciones del plano de control. Para crear una subred `/16` también se necesita un rango `/16` asociado disponible; elegir un rango «mayor» no evita los límites de VPC.

**CNI alternativo/IPv6:** planifica la ruta completa de plano de control, DNS, servicios/balanceadores de carga, políticas, arranque y reversión. No apliques un manifiesto flotante de overlay de Calico ni desactives aws-node en un clúster activo como cambio genérico. La familia IP de un clúster EKS existente no se puede cambiar sin más a IPv6. La compatibilidad y la integración con AWS dependen del modo específico de cómputo/CNI.

**Fargate:** una etiqueta de namespace no crea un perfil y `eks.amazonaws.com/v1alpha1 kind: FargateProfile` no es una API integrada de Kubernetes. Utiliza la API de EKS o eksctl (o un controlador compatible instalado explícitamente). Este ejemplo de API requiere un nombre de perfil sin utilizar, subredes privadas revisadas y un rol de ejecución:

```bash
# New profile example; this does not create or enlarge subnet address space.
aws eks create-fargate-profile --cluster-name "${EXAMPLE_CLUSTER:?}" \
  --region "${EXAMPLE_REGION:?}" --fargate-profile-name "${NEW_FARGATE_PROFILE:?}" \
  --pod-execution-role-arn "${FARGATE_EXECUTION_ROLE_ARN:?}" \
  --subnets "${PRIVATE_SUBNET_A:?}" "${PRIVATE_SUBNET_B:?}" \
  --selectors '[{"namespace":"ipam-fargate"}]'
```

Crea por separado el namespace y las cargas de trabajo correspondientes, y verifica la activación del perfil. Fargate cambia quién se responsabiliza de las operaciones, no la capacidad finita de direcciones de las subredes elegidas. Compara las soluciones con la demanda medida en lugar de aplicar todas a la vez. En esta revisión no se ejecutó ninguna migración de red ni benchmark de rendimiento.

</details>

## Comprobaciones de la base de VPC

11. ¿Qué par de subredes privadas está alineado y evita las subredes públicas 10.0.0.0/24 y 10.0.1.0/24?
   * A) 10.0.2.0/22 y 10.0.6.0/22
   * B) 10.0.4.0/22 y 10.0.8.0/22
   * C) 10.0.0.0/22 y 10.0.1.0/22
   * D) Cualquier par de cadenas distintas

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) 10.0.4.0/22 y 10.0.8.0/22**

Una subred `/22` empieza en un múltiplo de cuatro en el tercer octeto. La canonicalización de 10.0.2.0/22 produce 10.0.0.0/22, que se solapa con los rangos públicos.

</details>

12. Antes de utilizar recursos, ¿cuántas direcciones se pueden asignar en una subred IPv4 normal de AWS `/24`?
   * A) 256
   * B) 254
   * C) 251
   * D) Siempre 240

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) 251**

AWS reserva las primeras cuatro direcciones y la última de cada subred normal. El total es 256 y se pueden asignar 251; BYOIP tiene excepciones documentadas.

</details>

13. ¿Una etiqueta de rol de subred `elb` crea una ruta a un Internet Gateway?
   * A) Sí
   * B) No; la configuración de rutas y el descubrimiento del controlador son independientes
   * C) Solo en una subred privada
   * D) También abre todos los grupos de seguridad

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) No; la configuración de rutas y el descubrimiento del controlador son independientes**

Las etiquetas pueden afectar al descubrimiento, según el controlador, su versión y las feature gates. No crean rutas ni constituyen un límite de seguridad.

</details>

14. ¿Todos los nodos de EKS necesitan una ruta pública a Internet?
   * A) Sí, siempre a través de una gateway NAT
   * B) Sí, siempre a través de un IGW
   * C) No; el acceso necesario a servicios puede utilizar endpoints privados/mirrors adecuados
   * D) No se necesita acceso de red

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) No; el acceso necesario a servicios puede utilizar endpoints privados/mirrors adecuados**

Planifica las dependencias reales de API, registros de contenedores, DNS y cargas de trabajo. El endpoint del servicio EKS de AWS no es el endpoint de API del clúster de Kubernetes.

</details>

15. ¿Cuál es el puerto de destino habitual de kubelet para el tráfico del plano de control?
   * A) Todos los puertos TCP 1025–65535
   * B) TCP 10250
   * C) Todos los NodePort de forma predeterminada
   * D) Solo UDP 53

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) TCP 10250**

Revisa por separado TCP 443 de la API privada, TCP/UDP 53 de DNS, los puertos reales de webhooks/cargas de trabajo y las asociaciones reales de grupos de seguridad. El tráfico de retorno de SG con estado se comporta de forma distinta a las reglas NACL sin estado.

</details>

## Referencias

- [Requisitos de VPC/subred](https://docs.aws.amazon.com/eks/latest/userguide/network-reqs.html)
- [VPC CNI 1.23.0](https://github.com/aws/amazon-vpc-cni-k8s/blob/v1.23.0/README.md)
- [NetworkPolicy](https://kubernetes.io/docs/concepts/services-networking/network-policies/)
- [Políticas nativas de EKS](https://docs.aws.amazon.com/eks/latest/userguide/cni-network-policy.html)
- [Anotaciones de Service de LBC 3.5](https://github.com/kubernetes-sigs/aws-load-balancer-controller/blob/v3.5.0/docs/guide/service/annotations.md)
- [Descubrimiento de subredes de LBC](https://github.com/kubernetes-sigs/aws-load-balancer-controller/blob/v3.5.0/docs/deploy/subnet_discovery.md)
- [Listeners de NLB](https://docs.aws.amazon.com/elasticloadbalancing/latest/network/load-balancer-listeners.html)
- [Registros de NLB](https://docs.aws.amazon.com/elasticloadbalancing/latest/network/load-balancer-access-logs.html)
- [Caché de CoreDNS](https://coredns.io/plugins/cache/)
- [Implementación de la caché de CoreDNS](https://github.com/coredns/coredns/blob/v1.14.7/plugin/pkg/cache/cache.go)
