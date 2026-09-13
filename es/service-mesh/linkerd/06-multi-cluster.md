# Linkerd multiclúster

> **Última actualización**: September 11, 2026 · Linkerd edge-26.9.1 / charts 2026.9.1 · Gateway API 1.5.1

Linkerd refleja información de servicios seleccionados entre clústeres. Esto requiere tanto una ruta de descubrimiento funcional del plano de control como la ruta de red adecuada del plano de datos. No fusiona clústeres, replica datos de aplicaciones ni duplica cada solicitud para pruebas con tráfico reflejado.

## Modos de comunicación

| Modo | Descubrimiento/selección de servicios | Ruta de datos e identidad |
|---|---|---|
| Jerárquico | De forma predeterminada, `mirror.linkerd.io/exported=true` | Proxy cliente de origen → gateway del clúster de destino → servidor; la identidad original del cliente se pierde en el gateway |
| Plano / descubrimiento remoto | `mirror.linkerd.io/exported=remote-discovery` | Conexiones directas entre Pods de distintos clústeres; se conserva la identidad original de la carga de trabajo |
| Service federado | `mirror.linkerd.io/federated=member` | Unión de servicios con el mismo nombre/espacio de nombres sobre una red plana; requiere clientes incorporados a la malla |

El controlador de reflejo del clúster de origen observa la **API de Kubernetes de destino**, no otro controlador de reflejo. Un Service reflejado es un objeto de descubrimiento de Kubernetes, no un proceso que realiza TLS. Su nombre habitual es `<service>-<Link cluster name>` en el espacio de nombres correspondiente.

![Ruta jerárquica: el proxy cliente de origen se conecta al gateway remoto, que abre una conexión separada al servidor de la malla. No se requiere un salto por un gateway de origen y el servidor final no recibe la identidad original del cliente a través de este gateway.](../../.gitbook/assets/en-service-mesh-linkerd-06-multi-cluster-2.png)

[Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-service-mesh-linkerd-06-multi-cluster-2.html)

El modo jerárquico necesita que los clientes de origen puedan acceder al gateway de destino. El modo plano/federado necesita además enrutamiento directo e inequívoco de IP de Pods entre clústeres y el mismo espacio de nombres del plano de control de Linkerd. Un equilibrador de carga interno o un endpoint de VPC por sí solos no establecen esa red plana.

## Requisitos previos y confianza compartida

Utilice dos clústeres preparados con contextos kubeconfig explícitos `west` y `east`. Son alias locales, no pruebas de su cuenta o región de AWS. Utilice versiones compatibles de Kubernetes/Gateway API, la configuración de nodos de trabajo Linux/CNI y la CLI fijada de la [guía de instalación](01-installation.md); no equipare la versión más reciente de Kubernetes con la compatibilidad de Linkerd.

Ambas instalaciones de Linkerd deben confiar en las cadenas de emisores pertinentes. Una raíz pública común es la disposición más sencilla; también es compatible un paquete compartido que contenga varias raíces apropiadas. Los clústeres no necesitan compartir una clave privada de emisor ni certificados de cargas de trabajo.

![Una disposición habitual de PKI: una raíz pública compartida con emisores separados por clúster y certificados finales por proxy. Las claves privadas de raíz no se distribuyen a todos los proxies; los emisores separados no hacen intrínsecamente que ServiceAccounts con el mismo nombre tengan identidades distintas de clúster.](../../.gitbook/assets/en-service-mesh-linkerd-06-multi-cluster-3.png)

[Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-service-mesh-linkerd-06-multi-cluster-3.html)

**Solo para un laboratorio nuevo y aislado**, lo siguiente crea una raíz común y emisores ECDSA P-256 separados. La duración de diez años de la raíz es un ejemplo, no el valor predeterminado de la CLI ni una recomendación universal:

```bash
set -euo pipefail
umask 077
# New lab PKI only. The chosen root lifetime is an example, not a default.
step certificate create root.linkerd.cluster.local ca.crt ca.key \
  --profile root-ca --kty EC --curve P-256 \
  --not-after 87600h --no-password --insecure
step certificate create identity.linkerd.cluster.local issuer-west.crt issuer-west.key \
  --profile intermediate-ca --kty EC --curve P-256 \
  --ca ca.crt --ca-key ca.key --not-after 8760h --no-password --insecure
step certificate create identity.linkerd.cluster.local issuer-east.crt issuer-east.key \
  --profile intermediate-ca --kty EC --curve P-256 \
  --ca ca.crt --ca-key ca.key --not-after 8760h --no-password --insecure
cp ca.crt shared-roots.pem
```

`--no-password --insecure` produce archivos de claves privadas sin cifrar. Consérvelos en una ubicación de trabajo protegida y distribuya únicamente el paquete público de confianza más el material de emisor requerido por cada clúster. Para mallas existentes, utilice el [procedimiento gradual de rotación de confianza](04-security.md); no sustituya raíces solo para seguir un ejemplo de instalación nueva.

### Instalar el núcleo con contextos explícitos

Lo siguiente es la ruta de instalación del núcleo gestionada por la CLI, después de completar los requisitos de Gateway API/CNI de la guía de instalación en ambos clústeres. Para núcleos gestionados por Helm, conserve ese responsable y pase las credenciales correspondientes de cada clúster mediante sus valores revisados.

Los comandos muestran la ruta predeterminada de proxy-init en nodos de trabajo Linux compatibles. Una instalación de Linkerd CNI también debe pasar `cniEnabled:true` mediante su configuración de instalación seleccionada.

```bash
set -euo pipefail
# New CLI-owned installations only; complete Gateway API/CNI prerequisites first.
linkerd --context west install --crds | kubectl --context west apply -f -
linkerd --context west install \
  --identity-trust-anchors-file shared-roots.pem \
  --identity-issuer-certificate-file issuer-west.crt \
  --identity-issuer-key-file issuer-west.key | kubectl --context west apply -f -

linkerd --context east install --crds | kubectl --context east apply -f -
linkerd --context east install \
  --identity-trust-anchors-file shared-roots.pem \
  --identity-issuer-certificate-file issuer-east.crt \
  --identity-issuer-key-file issuer-east.key | kubectl --context east apply -f -
linkerd --context west check
linkerd --context east check
```

Instale Viz por separado si necesita sus estadísticas de tráfico. Las comprobaciones propias de la extensión multiclúster no son una validación de aplicación/negocio.

## Extensión y enlaces direccionales

Este ejercicio utiliza Helm para gestionar la extensión multiclúster y sus controladores de pares. El antiguo `multicluster link` de la CLI seleccionada está obsoleto; utilice `link-gen` para el Link y los Secrets de credenciales, junto con la lista `controllers` del chart.

### Instalación base

Para **EKS con AWS Load Balancer Controller instalado**, guarde esto como `mc-base-values.yaml`. Solicita un NLB TCP interno; asegúrese de que las rutas de pares, DNS, grupos de seguridad y puertos requeridos ya estén diseñados. Otras plataformas necesitan su propia configuración compatible de equilibrador de carga.

```yaml
gateway:
  enabled: true
  serviceType: LoadBalancer
  loadBalancerClass: service.k8s.aws/nlb
  serviceAnnotations:
    service.beta.kubernetes.io/aws-load-balancer-scheme: internal
    service.beta.kubernetes.io/aws-load-balancer-nlb-target-type: ip
    service.beta.kubernetes.io/aws-load-balancer-attributes: load_balancing.cross_zone.enabled=true
```

```bash
helm repo add linkerd-edge https://helm.linkerd.io/edge
helm repo update linkerd-edge
# Initially install gateway/remote-access prerequisites, without peer controllers.
helm --kube-context west upgrade --install linkerd-multicluster \
  linkerd-edge/linkerd-multicluster --version 2026.9.1 \
  -n linkerd-multicluster --create-namespace -f mc-base-values.yaml \
  --wait --timeout 10m
helm --kube-context east upgrade --install linkerd-multicluster \
  linkerd-edge/linkerd-multicluster --version 2026.9.1 \
  -n linkerd-multicluster --create-namespace -f mc-base-values.yaml \
  --wait --timeout 10m
kubectl --context west -n linkerd-multicluster get svc linkerd-gateway -o yaml
kubectl --context east -n linkerd-multicluster get svc linkerd-gateway -o yaml
```

El Service de destino debe tener una IP de ingreso **o un nombre de host** antes de que pueda generarse un Link basado en gateway. Los NLB de AWS suelen exponer un nombre de host, que `link-gen` acepta. El puerto predeterminado de datos del gateway es 4143; el de las sondas de disponibilidad del gateway es 4191. La accesibilidad de ninguno de esos puertos demuestra que la API remota de Kubernetes o todas las aplicaciones estén sanas.

### East consume West

Guarde esta lista deseada de controladores como `mc-east-links.yaml`:

```yaml
controllers:
- link:
    ref:
      name: west
```

```bash
set -euo pipefail
umask 077
# Read West's configuration; install the generated credentials/Link into East.
linkerd --context west multicluster link-gen --cluster-name west > west-link.yaml
# Review public metadata and target endpoint without printing credential values.
kubectl --context east apply -f west-link.yaml
helm --kube-context east upgrade linkerd-multicluster \
  linkerd-edge/linkerd-multicluster --version 2026.9.1 \
  -n linkerd-multicluster -f mc-base-values.yaml -f mc-east-links.yaml \
  --wait --timeout 10m
kubectl --context east -n linkerd-multicluster get links.multicluster.linkerd.io
linkerd --context east multicluster check
linkerd --context east multicluster gateways
```

`link-gen` lee la ubicación/CA de la API de West y el token del ServiceAccount de acceso remoto seleccionado. Emite un Link y dos Secrets de credenciales, para `linkerd-multicluster` y el espacio de nombres del plano de control `linkerd`. No instala por sí mismo una ruta de red ni el controlador de reflejo de origen.

Trate el archivo generado como una credencial: restrinja el acceso, no lo incluya en commits ni imprima su contenido en registros. El kubeconfig generado debe poder utilizarse desde los controladores, incluidos datos autocontenidos de CA de la API y una dirección de servidor accesible y con certificado válido. Si el endpoint de la estación de trabajo no es apropiado, utilice la anulación compatible `--api-server-address` con el endpoint real de API accesible desde los controladores.

El Link es direccional: generarlo en West y aplicarlo a East permite que **East descubra West**. Conserve todos los pares existentes en la lista deseada de controladores de Helm al actualizar una instalación establecida; sustituir un arreglo por este ejemplo de una sola entrada puede eliminar otros controladores.

### Dirección inversa opcional

Guarde `mc-west-links.yaml`:

```yaml
controllers:
- link:
    ref:
      name: east
```

```bash
set -euo pipefail
umask 077
linkerd --context east multicluster link-gen --cluster-name east > east-link.yaml
kubectl --context west apply -f east-link.yaml
helm --kube-context west upgrade linkerd-multicluster \
  linkerd-edge/linkerd-multicluster --version 2026.9.1 \
  -n linkerd-multicluster -f mc-base-values.yaml -f mc-west-links.yaml \
  --wait --timeout 10m
linkerd --context west multicluster check
```

ServiceAccounts de acceso remoto distintos por par pueden hacer más selectiva la revocación. Coordine su RBAC y la renovación de credenciales; son credenciales de API de Kubernetes, separadas de los certificados de cargas de trabajo de la malla.

## Exportar y consumir un servicio

Prepare el espacio de nombres de la aplicación en ambos clústeres. El chart no crea por defecto los espacios de nombres de reflejo que falten.

Guarde como `mc-namespace.yaml`:

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: mc-demo
  annotations:
    linkerd.io/inject: enabled
```

Utilice cargas de trabajo `web` probadas e incorporadas a la malla, que escuchen en 8080 con etiqueta `app:web`, y una carga de trabajo `client` existente de la malla para comprobar las solicitudes. Esta página no despliega una imagen `client:latest` sin especificar ni afirma que un Deployment parcial sea válido.

Guarde este Service de **West** como `west-web-service.yaml`:

```yaml
apiVersion: v1
kind: Service
metadata:
  name: web
  namespace: mc-demo
  labels:
    mirror.linkerd.io/exported: 'true'
spec:
  selector:
    app: web
  ports:
  - name: http
    port: 80
    targetPort: 8080
    appProtocol: http
```

```bash
# Apply the Namespace manifest to both contexts before creating workloads/mirrors.
kubectl --context west apply -f mc-namespace.yaml
kubectl --context east apply -f mc-namespace.yaml
kubectl --context west apply -f west-web-service.yaml
# Alternative for an existing West Service:
kubectl --context west -n mc-demo label service/web mirror.linkerd.io/exported=true --overwrite
kubectl --context east -n mc-demo get service web-west
# Hierarchical mode: current service-mirror still manages legacy Endpoints.
kubectl --context east -n mc-demo get endpoints web-west -o yaml
kubectl --context east -n mc-demo get endpointslices.discovery.k8s.io \
  -l kubernetes.io/service-name=web-west -o yaml
# Existing meshed client with curl installed and the expected app endpoint.
kubectl --context east -n mc-demo exec deployment/client -c client -- \
  curl --fail --show-error --retry 0 --max-time 10 http://web-west.mc-demo.svc.cluster.local/
```

Para un Service recién creado, aplique su manifiesto después de crear el espacio de nombres y preparar las cargas de trabajo. El comando de etiqueta es la alternativa para un Service existente. Las etiquetas de exportación seleccionan el descubrimiento; no son un límite de control de acceso y solo afectan a pares cuyos selectores/RBAC de Link coincidan.

La implementación seleccionada de service-mirror sigue manteniendo `Endpoints` heredados para reflejos jerárquicos. Inspeccione también EndpointSlices cuando existan, pero no finja que cambiar un comando de diagnóstico migra el controlador. En modo de descubrimiento remoto, los Endpoints locales pueden faltar intencionadamente: el componente destination consulta en su lugar los endpoints remotos.

## Enrutamiento local/remoto explícito

Para las cargas de trabajo web locales de **East**, guarde estos Services principal/de backend local como `east-web-services.yaml`:

```yaml
apiVersion: v1
kind: Service
metadata:
  name: web
  namespace: mc-demo
spec:
  selector:
    app: web
  ports:
  - name: http
    port: 80
    targetPort: 8080
    appProtocol: http
---
apiVersion: v1
kind: Service
metadata:
  name: web-local
  namespace: mc-demo
spec:
  selector:
    app: web
  ports:
  - name: http
    port: 80
    targetPort: 8080
    appProtocol: http
```

Guarde `east-web-route.yaml` para dividir el tráfico de clientes de la malla aptos entre ese backend local y el Service importado:

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: web-cluster-route
  namespace: mc-demo
spec:
  parentRefs:
  - group: ''
    kind: Service
    name: web
    port: 80
  rules:
  - backendRefs:
    - name: web-local
      port: 80
      weight: 80
    - name: web-west
      port: 80
      weight: 20
```

```bash
kubectl --context east apply -f east-web-services.yaml
kubectl --context east apply -f east-web-route.yaml
kubectl --context east -n mc-demo get httproute web-cluster-route -o yaml
linkerd --context east diagnostics policy -n mc-demo service/web 80 -o json
```

Utilice el grupo principal de Service `""` y el puerto 80 del Service. Confirme que las rutas local y remota estén listas, la aceptación de la ruta y la política efectiva del cliente. Un ServiceProfile en conflicto puede tener prioridad sobre la política saliente actual; consulte la [gestión del tráfico](03-traffic-management.md).

### Transición manual frente a conmutación automática

Una configuración 100/0 no convierte automáticamente un backend de peso cero en una reserva activa. Para esta ruta gestionada manualmente, un estado exclusivamente remoto revisado explícitamente es:

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: web-cluster-route
  namespace: mc-demo
spec:
  parentRefs:
  - group: ''
    kind: Service
    name: web
    port: 80
  rules:
  - backendRefs:
    - name: web-local
      port: 80
      weight: 0
    - name: web-west
      port: 80
      weight: 100
```

Aplique deliberadamente un estado elegido y verifique el resultado de la aplicación, la capacidad remota y la coherencia de datos antes de tratarlo como recuperación. Las solicitudes y escrituras existentes pueden tener resultados inciertos; los cambios de enrutamiento no replican bases de datos ni deshacen operaciones confirmadas.

El antiguo webhook de reversión de Flagger referenciaba un servicio `/failover` no desplegado/no verificado y modificaba un TrafficSplit con otro nombre. No establecía una conmutación regional fiable. La entrega progresiva con Flagger se cubre por separado en la guía de tráfico.

SMI TrafficSplit y la extensión Linkerd Failover están obsoletos. La dirección oficial de migración son los servicios federados cuando hay red plana; la federación no sustituye automáticamente todos los requisitos de red jerárquica o de primario local estricto.


## Redes planas y servicios federados

Para una **configuración solo plana** independiente, los valores base omiten el gateway. Guarde como `flat-base-values.yaml`:

```yaml
gateway:
  enabled: false
```

Los valores del controlador de pares de East, `flat-east-links.yaml`, también omiten las sondas de gateway:

```yaml
controllers:
- link:
    ref:
      name: west
  gateway:
    enabled: false
```

Siga la misma secuencia instalación base → Link/Secrets → controlador de Helm, utilizando estos archivos y `--gateway=false` en la generación del Link. Prepare primero el enrutamiento de Pods, los espacios de nombres y la confianza de ambos clústeres. Al migrar una instalación existente, conserve los gateways hasta que se haya trasladado su último consumidor jerárquico.

```bash
set -euo pipefail
umask 077
# Separate flat-network setup: both base installs omit the gateway.
# Use flat-base-values.yaml plus the corresponding flat controller values.
linkerd --context west multicluster link-gen --cluster-name west \
  --gateway=false > west-flat-link.yaml
kubectl --context east apply -f west-flat-link.yaml
helm --kube-context east upgrade linkerd-multicluster \
  linkerd-edge/linkerd-multicluster --version 2026.9.1 \
  -n linkerd-multicluster -f flat-base-values.yaml -f flat-east-links.yaml \
  --wait --timeout 10m
kubectl --context west -n mc-demo label service/web \
  mirror.linkerd.io/exported=remote-discovery --overwrite
linkerd --context east diagnostics endpoints web-west.mc-demo.svc.cluster.local:80
```

El descubrimiento remoto cambia dónde se consultan los endpoints; no crea rutas de Pods, reglas de grupos de seguridad ni acceso remoto a la API. Las credenciales correspondientes del plano de control también deben funcionar desde el componente destination.

### Pertenencia a un servicio federado

Los servicios con el mismo nombre y espacio de nombres pueden unirse a un Service federado, normalmente llamado `web-federated` en este ejemplo:

```bash
# Flat connectivity, matching namespaces and the required directional Links first.
kubectl --context west -n mc-demo label service/web mirror.linkerd.io/federated=member --overwrite
kubectl --context east -n mc-demo label service/web mirror.linkerd.io/federated=member --overwrite
kubectl --context east -n mc-demo get service web-federated
kubectl --context east -n linkerd-multicluster get link west -o yaml
linkerd --context east diagnostics endpoints web-federated.mc-demo.svc.cluster.local:80
```

El Service federado existe donde están configurados los Links/controladores direccionales pertinentes. Los clientes de la malla equilibran directamente entre los endpoints de miembros descubiertos, sin gateway. Esto proporciona una base para la resiliencia, pero no garantiza recuperación inmediata, orden local primero estricto ni disponibilidad de aplicaciones/datos.

Revise la disponibilidad de endpoints, los ajustes de acumulación de fallos, las particiones de red, la actualidad del descubrimiento y la semántica de reintentos del cliente. La selección de metadatos/puertos de la federación también importa cuando los Services miembros difieren; no suponga que todas las anotaciones contradictorias se combinen como se pretende.

El reflejo de servicios sin IP de clúster es una capacidad opcional independiente del controlador (`enableHeadlessServices` en los ajustes correspondientes del controlador). Requiere hosts con nombre adecuados y tiene un comportamiento de endpoints distinto; los Services sin IP de clúster no pueden unirse a Services federados.

## Autorización entre clústeres

Los gateways jerárquicos autentican la conexión de malla entrante y crean una conexión saliente separada. El servidor final no puede utilizar la identidad original del cliente remoto para distinguir clientes a través de ese gateway.

Para **tráfico plano/federado**, esta política en West permite la identidad conservada `client.mc-demo.serviceaccount.identity.linkerd.cluster.local`:

```yaml
apiVersion: policy.linkerd.io/v1beta3
kind: Server
metadata:
  name: web-http
  namespace: mc-demo
spec:
  podSelector:
    matchLabels:
      app: web
  port: 8080
  proxyProtocol: HTTP/1
  accessPolicy: deny
---
apiVersion: policy.linkerd.io/v1alpha1
kind: AuthorizationPolicy
metadata:
  name: web-from-client
  namespace: mc-demo
spec:
  targetRef:
    group: policy.linkerd.io
    kind: Server
    name: web-http
  requiredAuthenticationRefs:
  - kind: ServiceAccount
    name: client
    namespace: mc-demo
```

La API es AuthorizationPolicy de Linkerd con Server `v1beta3`, no el inexistente ServerAuthorization `v1beta2`. La identidad estándar de Kubernetes tiene formato DNS, no la URI SPIFFE de estilo Istio mostrada anteriormente.

La misma combinación de ServiceAccount/espacio de nombres/dominio de confianza puede tener la misma identidad en varios clústeres. Las claves separadas de emisor no introducen un ID criptográfico implícito de clúster. Esta política permite esa identidad de carga de trabajo; no demuestra «solo East». Diseñe identidades y límites de confianza distintos cuando sea necesario y evalúe la identidad realmente visible en cada punto de aplicación.

Para despliegues en modo gateway, tenga en cuenta la identidad del gateway en el servidor final y los controles en el límite del gateway/red. Las etiquetas de exportación y un equilibrador de carga interno no sustituyen la autorización.

## Conectividad y gestión de EKS

Los valores base anteriores presuponen **AWS Load Balancer Controller**, `service.k8s.aws/nlb`, destinos IP y un NLB interno. Utilizan la anotación actual de atributos del equilibrador de carga en vez de la anotación entre zonas obsoleta. EKS Auto Mode utiliza otro responsable/clase, `eks.amazonaws.com/nlb`, y sus anotaciones compatibles deben comprobarse por separado.

Mantenga intacta la ruta TCP/mTLS de Linkerd; el enrutamiento HTTP o la terminación TLS de un ALB no son un transporte de gateway intercambiable. Tenga en cuenta por separado el puerto de datos 4143 de origen a gateway, el puerto de sonda 4191 del controlador de reflejo al gateway y el acceso del plano de control de origen a la API de Kubernetes de destino. Restrinja los orígenes permitidos según el diseño real de enrutamiento/SNAT/grupos de seguridad.

| Conectividad | Qué proporciona |
|---|---|
| Emparejamiento de VPC / enrutamiento apropiado de Transit Gateway | Conectividad privada de red cuando se configuran rutas, direcciones, DNS y controles de seguridad |
| AWS PrivateLink | Acceso a servicios/recursos seleccionados mediante endpoints; no es emparejamiento de VPC ni enrutamiento arbitrario automático entre Pods |
| Endpoint privado de API de Kubernetes de EKS | Acceso a la API de Kubernetes de ese clúster desde su VPC/red conectada apropiadamente |
| Endpoint de interfaz de VPC de EKS | Acceso privado a la API de gestión de AWS EKS; no es el endpoint de la API de Kubernetes |

Para modo plano, asegure direcciones de Pods sin conflictos y directamente accesibles; una conexión solo mediante gateway no basta. Para modo jerárquico, diseñe la accesibilidad del gateway y la API remota aunque no exista enrutamiento arbitrario a Pods remotos.

Aprovisione los clústeres y las conexiones de red mediante su flujo de infraestructura revisado, seleccionando la cuenta/perfil AWS previstos y versiones compatibles. Dar nombres diferentes a dos comandos `eksctl create cluster` no los coloca en cuentas diferentes. La creación de clústeres, el aprovisionamiento de gateways y el tráfico real entre regiones no se ejecutaron en esta auditoría.

Los operadores/controladores que gestionan recursos de AWS necesitan permisos IAM de AWS. Las credenciales de reflejo generadas por Linkerd se autentican con tokens de ServiceAccount de Kubernetes y RBAC; un rol IAM general entre cuentas no es un requisito de todos los Links durante la ejecución. Mantenga separadas estas relaciones de confianza.

## Observabilidad y federación

`multicluster gateways` informa de la sonda del gateway de destino, no del estado de extremo a extremo de todas las aplicaciones exportadas. Las métricas de sonda pertenecen al controlador de reflejo de origen: incluyen, por ejemplo, `gateway_alive` y `gateway_probe_latency_ms`, etiquetadas con `target_cluster_name`. No son métricas ordinarias del proxy del gateway local.

Para Prometheus central, lo siguiente es un **ejemplo de configuración de cliente para endpoints HTTPS privados ya desplegados con autenticación Basic**. Proporcione DNS reales, archivos de CA/contraseña, autenticación del servidor, accesibilidad y autorización de recopilación. Viz predeterminado no expone automáticamente estos endpoints.

```yaml
scrape_configs:
- job_name: federate-west
  scheme: https
  honor_labels: true
  metrics_path: /federate
  params:
    match[]:
    - '{job=~"linkerd-proxy|linkerd-controller"}'
  static_configs:
  - targets:
    - prometheus-west.internal.example.com:443
  tls_config:
    ca_file: /etc/prometheus/federation/ca.crt
  basic_auth:
    username: federation-reader
    password_file: /etc/prometheus/federation/west/password
  metric_relabel_configs:
  - target_label: origin_cluster
    replacement: west
- job_name: federate-east
  scheme: https
  honor_labels: true
  metrics_path: /federate
  params:
    match[]:
    - '{job=~"linkerd-proxy|linkerd-controller"}'
  static_configs:
  - targets:
    - prometheus-east.internal.example.com:443
  tls_config:
    ca_file: /etc/prometheus/federation/ca.crt
  basic_auth:
    username: federation-reader
    password_file: /etc/prometheus/federation/east/password
  metric_relabel_configs:
  - target_label: origin_cluster
    replacement: east
```

`honor_labels:true` conserva las etiquetas de métricas de origen; un reetiquetado de destino por sí solo no sobrescribe de forma fiable una etiqueta exportada en conflicto. Aquí el reetiquetado de métricas asigna el `origin_cluster` controlado por el recopilador después de la recopilación. Conserve esa etiqueta de origen al agregar y evite rutas de recopilación duplicadas.

Proporción de éxito del backend por origen de métricas:

```promql
(sum by (origin_cluster) (rate(response_total{namespace="mc-demo",deployment="web",direction="inbound",classification="success"}[5m]))
 or on(origin_cluster) (0 * sum by (origin_cluster) (rate(response_total{namespace="mc-demo",deployment="web",direction="inbound"}[5m])))) / sum by (origin_cluster) (rate(response_total{namespace="mc-demo",deployment="web",direction="inbound"}[5m]))
and on(origin_cluster) (sum by (origin_cluster) (rate(response_total{namespace="mc-demo",deployment="web",direction="inbound"}[5m])) > 0)
```

TTFB observado por el cliente por origen de métricas:

```promql
histogram_quantile(0.99,
  sum by (le, origin_cluster) (rate(response_latency_ms_bucket{namespace="mc-demo",deployment="client",direction="outbound"}[5m]))
)
```

El cliente de demostración debe enviar el tráfico remoto previsto para que la segunda consulta represente esa ruta. Incluye tiempo de aplicación/proxy/red y no es RTT puro entre regiones. `src_cluster` y `dst_cluster` no son etiquetas que esta configuración garantice añadir. Inspeccione las series reales antes de construir dimensiones entre clústeres más específicas.

Las series de éxito ausentes se alinean con el total de cada clúster; los totales inactivos/ausentes no se informan como 100% de éxito. Consulte la [guía de observabilidad](05-observability.md) para clasificación, unidades, estado de recopilación y requisitos de paneles.

## Solución de problemas

```bash
linkerd --context east multicluster check
linkerd --context east multicluster gateways
kubectl --context east -n linkerd-multicluster get link west -o yaml
kubectl --context east -n linkerd-multicluster logs deployment/controller-west -c controller --tail=100
kubectl --context west -n linkerd-multicluster logs deployment/linkerd-gateway -c linkerd-proxy --tail=100
linkerd --context east viz stat deployment/client -n mc-demo --to service/web-west
linkerd --context west check --proxy
linkerd --context east check --proxy
```

Compruebe el estado del Link y los registros del controlador para problemas de API remota/RBAC/espacio de nombres. Para problemas de gateway, inspeccione la dirección de ingreso del Service de **destino**, la ruta/puerto de sonda y la ruta de red. Una sonda sana no verifica el puerto de datos ni la lógica de negocio. Para modo plano, utilice diagnósticos de endpoints de destination y conectividad directa de Pods en vez de esperar estadísticas de gateway.

Lea el paquete público de confianza real:

```bash
set -euo pipefail
# Public bundle data, not private keys or the generated Link kubeconfig.
kubectl --context west -n linkerd get configmap linkerd-identity-trust-roots -o json \
  | jq -er '.data["ca-bundle.crt"] | select(length > 0)' > west-trust.pem
kubectl --context east -n linkerd get configmap linkerd-identity-trust-roots -o json \
  | jq -er '.data["ca-bundle.crt"] | select(length > 0)' > east-trust.pem
openssl crl2pkcs7 -nocrl -certfile west-trust.pem | openssl pkcs7 -print_certs -text -noout
openssl crl2pkcs7 -nocrl -certfile east-trust.pem | openssl pkcs7 -print_certs -text -noout
```

Inspeccione todos los certificados y su validez/cadena de emisores. El orden/formato PEM por sí solo no prueba equivalencia de confianza y un grep corto del antiguo campo de configuración no es una verificación completa. Utilice el proceso gradual de rotación de la guía de seguridad para los cambios.

## Referencias y siguientes pasos

- [Buenas prácticas](07-best-practices.md), [cuestionario multiclúster](../../quizzes/service-mesh/linkerd/multi-cluster.md)
- [Referencia multiclúster](https://linkerd.io/docs/reference/multicluster/) e [instalación](https://linkerd.io/docs/tasks/installing-multicluster/)
- [Modo entre Pods](https://linkerd.io/docs/tasks/pod-to-pod-multicluster/) y [servicios federados](https://linkerd.io/docs/tasks/federated-services/)
- [Extensión de conmutación por error obsoleta](https://linkerd.io/docs/tasks/automatic-failover/)
- [Implementación publicada de link-gen](https://github.com/linkerd/linkerd2/blob/edge-26.9.1/multicluster/cmd/link-gen.go)
- [Tratamiento de endpoints de service-mirror publicado](https://github.com/linkerd/linkerd2/blob/edge-26.9.1/multicluster/service-mirror/cluster_watcher.go)
- [Anotaciones de AWS Load Balancer Controller](https://kubernetes-sigs.github.io/aws-load-balancer-controller/latest/guide/service/annotations/)
- [NLB de EKS Auto Mode](https://docs.aws.amazon.com/eks/latest/userguide/auto-configure-nlb.html)
- [Emparejamiento de VPC](https://docs.aws.amazon.com/vpc/latest/peering/what-is-vpc-peering.html) y [AWS PrivateLink](https://docs.aws.amazon.com/vpc/latest/privatelink/what-is-privatelink.html)
- [Endpoint de API de Kubernetes de EKS](https://docs.aws.amazon.com/eks/latest/userguide/cluster-endpoint.html) y [endpoints de interfaz de EKS](https://docs.aws.amazon.com/eks/latest/userguide/vpc-interface-endpoints.html)
