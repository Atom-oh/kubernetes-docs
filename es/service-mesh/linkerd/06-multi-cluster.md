# Linkerd multiclúster

> **Última actualización**: 16 de octubre de 2026 · Linkerd edge-26.10.1 / charts 2026.10.1 · Gateway API 1.5.1

Linkerd refleja información de servicios seleccionados entre clústeres. Para ello, necesita una ruta de descubrimiento funcional en el plano de control y la conectividad adecuada en el plano de datos. No fusiona los clústeres, no replica los datos de las aplicaciones ni duplica cada solicitud para probar con una copia del tráfico.

## Modos de comunicación

| Modo | Descubrimiento y selección de servicios | Ruta de datos e identidad |
|---|---|---|
| Jerárquico | De forma predeterminada, `mirror.linkerd.io/exported=true` | Proxy cliente de origen → gateway del clúster de destino → servidor; la identidad original del cliente se pierde en el gateway |
| Plano / descubrimiento remoto | `mirror.linkerd.io/exported=remote-discovery` | Conexiones directas entre Pods de distintos clústeres; se conserva la identidad original de la carga de trabajo |
| Service federado | `mirror.linkerd.io/federated=member` | Agrupación de servicios con el mismo nombre y namespace sobre una red plana; requiere clientes incorporados a la malla |

El controlador de reflejo del clúster de origen observa la **API de Kubernetes del clúster de destino**, no otro controlador de reflejo. Un Service reflejado es un objeto de descubrimiento de Kubernetes, no un proceso que establece conexiones TLS. Su nombre habitual es `<service>-<Link cluster name>` en el namespace correspondiente.

![Ruta jerárquica: el proxy cliente de origen se conecta al gateway remoto, que abre una conexión separada al servidor de la malla. No se requiere un salto por un gateway de origen y el servidor final no recibe la identidad original del cliente a través de este gateway.](../../.gitbook/assets/en-service-mesh-linkerd-06-multi-cluster-2.png)

[Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-service-mesh-linkerd-06-multi-cluster-2.html)

En modo jerárquico, los clientes de origen deben poder acceder al gateway de destino. Los modos plano y federado requieren, además, enrutamiento directo y sin ambigüedades entre las IP de Pods de los clústeres, y el mismo namespace para el plano de control de Linkerd. Un balanceador de carga interno o un endpoint de VPC no bastan por sí solos para establecer esa red plana.

## Requisitos previos y confianza compartida

Utilice dos clústeres preparados con contextos kubeconfig explícitos `west` y `east`. Estos nombres son alias locales; no identifican por sí solos la cuenta ni la región de AWS. Siga la [guía de instalación](01-installation.md) para seleccionar versiones compatibles de Kubernetes y Gateway API, configurar los nodos Linux y la CNI, y fijar la CLI. Que una versión de Kubernetes sea la más reciente no significa que sea compatible con Linkerd.

Ambas instalaciones de Linkerd deben confiar en las cadenas de certificados de los emisores correspondientes. Compartir un certificado raíz público es la opción más sencilla; también se admite un paquete de confianza que incluya varias raíces adecuadas. Los clústeres no necesitan compartir la clave privada del emisor ni los certificados de las cargas de trabajo.

![Una configuración habitual de PKI: un certificado raíz público compartido, emisores independientes por clúster y certificados de cada proxy. Las claves privadas de la raíz no se distribuyen a todos los proxies; utilizar emisores distintos no hace que los ServiceAccounts con el mismo nombre tengan automáticamente identidades de clúster diferentes.](../../.gitbook/assets/en-service-mesh-linkerd-06-multi-cluster-3.png)

[Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-service-mesh-linkerd-06-multi-cluster-3.html)

**Solo para un laboratorio nuevo y aislado**, el siguiente ejemplo crea una raíz común y emisores ECDSA P-256 independientes. La vigencia de diez años de la raíz es un ejemplo, no el valor predeterminado de la CLI ni una recomendación universal:

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

`--no-password --insecure` genera archivos de claves privadas sin cifrar. Consérvelos en una ubicación de trabajo protegida y distribuya únicamente el paquete público de confianza y el material del emisor que necesite cada clúster. Para las mallas existentes, siga el [procedimiento gradual de rotación de confianza](04-security.md); no sustituya las raíces simplemente para seguir un ejemplo de instalación nueva.

### Instalar el núcleo con contextos explícitos

El siguiente ejemplo instala el núcleo mediante la CLI, después de completar los requisitos de Gateway API y CNI de la guía de instalación en ambos clústeres. Si Helm ya gestiona el núcleo, mantenga esa forma de gestión y proporcione las credenciales de cada clúster mediante los valores de Helm revisados.

Los comandos utilizan la opción predeterminada proxy-init en nodos Linux compatibles. Si utiliza Linkerd CNI, también debe incluir `cniEnabled:true` en la configuración de instalación elegida.

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

Instale Viz por separado si necesita sus estadísticas de tráfico. Las comprobaciones de la extensión multiclúster no validan el funcionamiento de la aplicación ni sus operaciones de negocio.

## Extensión y enlaces direccionales

Este ejercicio utiliza Helm para gestionar la extensión multiclúster y los controladores de los clústeres remotos. El antiguo comando `multicluster link` de la CLI seleccionada está obsoleto. Utilice `link-gen` para generar el Link y los Secrets de credenciales, junto con la lista `controllers` del chart.

### Instalación base

Para **EKS con AWS Load Balancer Controller instalado**, guarde lo siguiente como `mc-base-values.yaml`. Esta configuración solicita un NLB TCP interno; antes de aplicarla, prepare las rutas entre clústeres, DNS, los grupos de seguridad y los puertos necesarios. En otras plataformas, utilice una configuración de balanceador de carga compatible con ellas.

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
  linkerd-edge/linkerd-multicluster --version 2026.10.1 \
  -n linkerd-multicluster --create-namespace -f mc-base-values.yaml \
  --wait --timeout 10m
helm --kube-context east upgrade --install linkerd-multicluster \
  linkerd-edge/linkerd-multicluster --version 2026.10.1 \
  -n linkerd-multicluster --create-namespace -f mc-base-values.yaml \
  --wait --timeout 10m
kubectl --context west -n linkerd-multicluster get svc linkerd-gateway -o yaml
kubectl --context east -n linkerd-multicluster get svc linkerd-gateway -o yaml
```

El Service de destino debe disponer de una IP de ingreso **o un nombre de host** para que pueda generarse un Link basado en gateway. Los NLB de AWS suelen proporcionar un nombre de host, que `link-gen` admite. El puerto predeterminado para el tráfico de datos del gateway es 4143, y el de las sondas de disponibilidad es 4191. Poder acceder a cualquiera de esos puertos no demuestra que la API remota de Kubernetes ni todas las aplicaciones funcionen correctamente.

### East utiliza servicios de West

Guarde la lista de controladores que desea mantener como `mc-east-links.yaml`:

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
  linkerd-edge/linkerd-multicluster --version 2026.10.1 \
  -n linkerd-multicluster -f mc-base-values.yaml -f mc-east-links.yaml \
  --wait --timeout 10m
kubectl --context east -n linkerd-multicluster get links.multicluster.linkerd.io
linkerd --context east multicluster check
linkerd --context east multicluster gateways
```

`link-gen` lee la dirección de la API de West, su CA y el token del ServiceAccount seleccionado para el acceso remoto. Genera un Link y dos Secrets de credenciales: uno para `linkerd-multicluster` y otro para el namespace del plano de control, `linkerd`. El comando no instala una ruta de red ni el controlador de reflejo del clúster de origen.

El archivo generado contiene credenciales: restrinja su acceso, no lo incluya en commits ni imprima su contenido en los registros. Los controladores deben poder utilizar el kubeconfig generado. Este debe incluir los datos de la CA de la API sin depender de archivos externos, y una dirección de servidor accesible cuyo certificado sea válido. Si el endpoint de la estación de trabajo no sirve para los controladores, utilice la opción compatible `--api-server-address` para indicar el endpoint real de la API al que puedan acceder.

El Link es direccional: generarlo en West y aplicarlo en East permite que **East descubra West**. Al actualizar una instalación existente, mantenga todos los clústeres remotos en la lista de controladores de Helm. Sustituir la lista por este ejemplo de una sola entrada puede eliminar otros controladores.

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
  linkerd-edge/linkerd-multicluster --version 2026.10.1 \
  -n linkerd-multicluster -f mc-base-values.yaml -f mc-west-links.yaml \
  --wait --timeout 10m
linkerd --context west multicluster check
```

Utilizar un ServiceAccount de acceso remoto distinto para cada clúster permite revocar el acceso de forma más selectiva. Coordine sus permisos RBAC y la renovación de sus credenciales. Estas credenciales permiten acceder a la API de Kubernetes y son independientes de los certificados de las cargas de trabajo de la malla.

## Exportar y consumir un servicio

Prepare el namespace de la aplicación en ambos clústeres. De forma predeterminada, el chart no crea los namespaces que falten para los servicios reflejados.

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

Para crear un Service, aplique su manifiesto después de crear el namespace y preparar las cargas de trabajo. Si el Service ya existe, utilice como alternativa el comando que añade la etiqueta. Las etiquetas de exportación seleccionan los servicios que se descubren; no son un mecanismo de control de acceso. Solo afectan a los clústeres remotos cuyos selectores y permisos RBAC del Link coincidan.

La implementación seleccionada de service-mirror sigue gestionando `Endpoints` heredados para los servicios reflejados en modo jerárquico. Inspeccione también los EndpointSlices cuando existan; cambiar el comando de diagnóstico no migra el controlador. En modo de descubrimiento remoto, puede ser intencionado que no haya Endpoints locales: el componente destination consulta directamente los endpoints remotos.

## Enrutamiento explícito entre servicios locales y remotos

Para las cargas de trabajo web locales de **East**, guarde el Service principal y el Service del backend local como `east-web-services.yaml`:

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

Guarde `east-web-route.yaml` para repartir el tráfico de los clientes de la malla a los que se aplique la ruta entre el backend local y el Service importado:

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

Utilice el grupo de API principal de Service, `""`, y su puerto 80. Confirme que las rutas local y remota estén disponibles, que la ruta se acepte y que la política efectiva del cliente sea la prevista. Un ServiceProfile en conflicto puede prevalecer sobre la política de salida actual; consulte la [gestión del tráfico](03-traffic-management.md).

### Transición manual frente a conmutación automática

Una configuración 100/0 no convierte automáticamente un backend con peso cero en un destino de reserva activo. En esta ruta gestionada manualmente, el siguiente ejemplo define de forma explícita y revisada un estado que solo envía tráfico al backend remoto:

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

Aplique deliberadamente el estado elegido y compruebe el resultado de la aplicación, la capacidad remota y la coherencia de los datos antes de dar por recuperado el servicio. El resultado de las solicitudes y escrituras que ya estaban en curso puede ser incierto. Cambiar las rutas no replica las bases de datos ni deshace operaciones confirmadas.

El anterior webhook de reversión de Flagger apuntaba a un servicio `/failover` que no se había desplegado ni verificado, y modificaba un TrafficSplit con otro nombre. Ese ejemplo no demostraba una conmutación regional fiable. La guía de tráfico trata por separado la entrega progresiva con Flagger.

SMI TrafficSplit y la extensión Linkerd Failover están obsoletos. La migración oficial recomienda servicios federados cuando existe una red plana. La federación no sustituye automáticamente cualquier configuración jerárquica ni satisface por sí sola los requisitos de mantener estrictamente un destino local como primario.


## Redes planas y servicios federados

Para una **configuración independiente que utilice únicamente una red plana**, los valores base deshabilitan el gateway. Guárdelos como `flat-base-values.yaml`:

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

Siga la misma secuencia: instalación base → Link/Secrets → controlador de Helm. Utilice estos archivos y la opción `--gateway=false` al generar el Link. Prepare primero el enrutamiento de Pods, los namespaces y la confianza de ambos clústeres. Al migrar una instalación existente, conserve los gateways hasta que el último cliente que utilice el modo jerárquico haya migrado.

```bash
set -euo pipefail
umask 077
# Separate flat-network setup: both base installs omit the gateway.
# Use flat-base-values.yaml plus the corresponding flat controller values.
linkerd --context west multicluster link-gen --cluster-name west \
  --gateway=false > west-flat-link.yaml
kubectl --context east apply -f west-flat-link.yaml
helm --kube-context east upgrade linkerd-multicluster \
  linkerd-edge/linkerd-multicluster --version 2026.10.1 \
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

El Service federado existe allí donde se hayan configurado los Links direccionales y sus controladores. Los clientes de la malla reparten el tráfico directamente entre los endpoints descubiertos de los miembros, sin pasar por un gateway. Esto ayuda a diseñar la resiliencia, pero no garantiza una recuperación inmediata, la prioridad estricta de los destinos locales ni la disponibilidad de las aplicaciones y sus datos.

Revise la disponibilidad de los endpoints, la configuración de detección de fallos acumulados, las particiones de red, la actualización de la información de descubrimiento y la semántica de los reintentos del cliente. Si los Services miembros difieren, también debe revisar cómo la federación selecciona sus metadatos y puertos. No dé por supuesto que las anotaciones en conflicto se combinan de la forma deseada.

El reflejo de servicios headless, sin IP de clúster, es una función opcional e independiente del controlador (`enableHeadlessServices` en su configuración correspondiente). Requiere hosts con nombres adecuados y gestiona los endpoints de forma distinta. Los Services headless no pueden pertenecer a Services federados.

## Autorización entre clústeres

Los gateways del modo jerárquico autentican la conexión entrante de la malla y establecen otra conexión de salida. El servidor final no recibe la identidad original del cliente remoto, por lo que no puede utilizarla para distinguir a los clientes que llegan a través de ese gateway.

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

La misma combinación de ServiceAccount, namespace y dominio de confianza puede producir la misma identidad en varios clústeres. Utilizar claves de emisor diferentes no añade un identificador criptográfico implícito del clúster. Esta política permite la identidad de esa carga de trabajo; no demuestra que proceda «solo de East». Cuando sea necesario, diseñe identidades y límites de confianza diferenciados, y compruebe qué identidad se ve realmente en cada punto donde se aplica la política.

En modo gateway, tenga en cuenta la identidad que el gateway presenta al servidor final y los controles que se aplican en el gateway y en la red. Las etiquetas de exportación y un balanceador de carga interno no sustituyen los controles de autorización.

## Conectividad y gestión de EKS

Los valores base anteriores presuponen **AWS Load Balancer Controller**, la clase `service.k8s.aws/nlb`, destinos IP y un NLB interno. Utilizan la anotación actual de atributos del balanceador de carga en lugar de la antigua anotación para tráfico entre zonas. EKS Auto Mode utiliza otro controlador y otra clase, `eks.amazonaws.com/nlb`; compruebe por separado las anotaciones que admite.

Mantenga la ruta TCP/mTLS de Linkerd. El enrutamiento HTTP o la terminación TLS de un ALB no pueden sustituir sin más el transporte del gateway. Prepare por separado el acceso del origen al puerto de datos 4143 del gateway, el acceso del controlador de reflejo al puerto de sonda 4191 y el acceso del plano de control de origen a la API de Kubernetes de destino. Restrinja los orígenes permitidos según el diseño real de enrutamiento, SNAT y grupos de seguridad.

| Conectividad | Qué proporciona |
|---|---|
| Emparejamiento de VPC / enrutamiento apropiado de Transit Gateway | Conectividad privada de red cuando se configuran rutas, direcciones, DNS y controles de seguridad |
| AWS PrivateLink | Acceso a servicios/recursos seleccionados mediante endpoints; no es emparejamiento de VPC ni enrutamiento arbitrario automático entre Pods |
| Endpoint privado de API de Kubernetes de EKS | Acceso a la API de Kubernetes de ese clúster desde su VPC/red conectada apropiadamente |
| Endpoint de interfaz de VPC de EKS | Acceso privado a la API de gestión de AWS EKS; no es el endpoint de la API de Kubernetes |

El modo plano requiere direcciones de Pods que no se solapen y que sean directamente accesibles; una conexión únicamente mediante gateway no basta. En modo jerárquico, prepare el acceso al gateway y a la API remota, aunque no exista enrutamiento directo a cualquier Pod remoto.

Aprovisione los clústeres y las conexiones de red mediante el flujo de infraestructura revisado, seleccionando la cuenta y el perfil de AWS previstos y versiones compatibles. Asignar nombres distintos a dos comandos `eksctl create cluster` no hace que creen clústeres en cuentas diferentes. En la auditoría descrita en el original no se crearon clústeres, no se aprovisionaron gateways ni se probó tráfico real entre regiones.

Los operadores y controladores que gestionan recursos de AWS necesitan permisos IAM. En cambio, las credenciales de reflejo generadas por Linkerd utilizan tokens de ServiceAccount de Kubernetes y permisos RBAC. No todos los Links necesitan un rol IAM general entre cuentas durante su ejecución. Gestione estas relaciones de confianza por separado.

## Observabilidad y federación

`multicluster gateways` informa de la sonda del gateway de destino, no del estado de extremo a extremo de todas las aplicaciones exportadas. Las métricas de sonda pertenecen al controlador de reflejo de origen: incluyen, por ejemplo, `gateway_alive` y `gateway_probe_latency_ms`, etiquetadas con `target_cluster_name`. No son métricas ordinarias del proxy del gateway local.

Para un Prometheus central, el siguiente es un **ejemplo de configuración de cliente para endpoints HTTPS privados ya desplegados con autenticación Basic**. Proporcione los nombres DNS reales, los archivos de CA y contraseñas, la autenticación del servidor, la conectividad y los permisos para recopilar métricas. La configuración predeterminada de Viz no expone automáticamente estos endpoints.

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

`honor_labels:true` conserva las etiquetas de las métricas de origen. Reetiquetar solo el destino de recopilación no sobrescribe de forma fiable una etiqueta exportada con el mismo nombre. Aquí, el reetiquetado de métricas asigna `origin_cluster`, controlado por el recopilador, después de obtener las métricas. Conserve esta etiqueta al agregarlas y evite recopilar las mismas series por varias rutas.

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

El cliente de demostración debe enviar el tráfico remoto previsto para que la segunda consulta represente esa ruta. El tiempo medido incluye la aplicación, el proxy y la red; no es únicamente el RTT entre regiones. Esta configuración no garantiza que se añadan las etiquetas `src_cluster` y `dst_cluster`. Inspeccione las series reales antes de definir dimensiones más específicas entre clústeres.

Las series de éxito que falten se alinean con el total de su clúster. Si el total es cero o no existe, no se informa de un 100 % de éxito. Consulte la [guía de observabilidad](05-observability.md) para revisar la clasificación, las unidades, el estado de la recopilación y los requisitos de los paneles.

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

Para problemas con la API remota, RBAC o los namespaces, revise el estado del Link y los registros del controlador. Si falla el gateway, inspeccione la dirección de ingreso del Service de **destino**, la ruta y el puerto de la sonda, y la conectividad de red. Una sonda correcta no valida el puerto de datos ni la lógica de negocio. En modo plano, utilice los diagnósticos de endpoints del componente destination y compruebe la conectividad directa entre Pods; no espere estadísticas de gateway.

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

Inspeccione todos los certificados, su vigencia y la cadena de emisores. El orden y el formato PEM no bastan para demostrar que dos configuraciones ofrecen la misma confianza. Tampoco basta un grep breve del antiguo campo de configuración. Para realizar cambios, siga el proceso gradual de rotación de la guía de seguridad.

## Referencias y siguientes pasos

- [Buenas prácticas](07-best-practices.md), [cuestionario multiclúster](../../quizzes/service-mesh/linkerd/multi-cluster.md)
- [Referencia multiclúster](https://linkerd.io/docs/reference/multicluster/) e [instalación](https://linkerd.io/docs/tasks/installing-multicluster/)
- [Modo entre Pods](https://linkerd.io/docs/tasks/pod-to-pod-multicluster/) y [servicios federados](https://linkerd.io/docs/tasks/federated-services/)
- [Extensión de conmutación por error obsoleta](https://linkerd.io/docs/tasks/automatic-failover/)
- [Implementación publicada de link-gen](https://github.com/linkerd/linkerd2/blob/edge-26.10.1/multicluster/cmd/link-gen.go)
- [Gestión de endpoints en la versión publicada de service-mirror](https://github.com/linkerd/linkerd2/blob/edge-26.10.1/multicluster/service-mirror/cluster_watcher.go)
- [Anotaciones de AWS Load Balancer Controller](https://kubernetes-sigs.github.io/aws-load-balancer-controller/latest/guide/service/annotations/)
- [NLB de EKS Auto Mode](https://docs.aws.amazon.com/eks/latest/userguide/auto-configure-nlb.html)
- [Emparejamiento de VPC](https://docs.aws.amazon.com/vpc/latest/peering/what-is-vpc-peering.html) y [AWS PrivateLink](https://docs.aws.amazon.com/vpc/latest/privatelink/what-is-privatelink.html)
- [Endpoint de API de Kubernetes de EKS](https://docs.aws.amazon.com/eks/latest/userguide/cluster-endpoint.html) y [endpoints de interfaz de EKS](https://docs.aws.amazon.com/eks/latest/userguide/vpc-interface-endpoints.html)
