# Ejercicios de validación de red de Cilium

Este capítulo presenta ocho ejercicios guiados con resultados esperados. La base es Cilium 1.20.3, CLI 0.20.1 y una versión compatible de Kubernetes (1.33–1.36), revisados el 16 de octubre de 2026. No se afirma que sea compatible con todas las versiones «1.30 o posteriores».

## Requisitos previos

Use un clúster desechable preparado siguiendo la [guía de redes](../../../networking/cilium/03-networking.md) y los [perfiles de instalación](../../../networking/cilium/README.md), con dos nodos Linux en los que se puedan programar cargas. Use herramientas e imágenes adecuadas para la arquitectura. Mantenga kubectl dentro del desfase de versiones admitido por la documentación. Estos ejercicios no migran un CNI existente ni cambian la red administrada por el proveedor.

El laboratorio manual de políticas requiere permiso para crear un espacio de nombres nuevo, Pods, un Deployment, un Service y una CiliumNetworkPolicy con ámbito de espacio de nombres. Revise las políticas de ámbito de clúster y las restricciones de admisión existentes: un espacio de nombres separado no las anula. Ejecute los bloques de shell en la misma sesión para que se conserven las variables.

## 1. Instalación y pruebas básicas

Siga el procedimiento de descarga de CLI verificado en la guía de instalación y elija un perfil de Cilium. No ejecute los instaladores de Helm y CLI sobre la misma instalación de Cilium ni use, sin verificarlo, un archivo AMD64 obtenido de la versión `latest`.

```bash
set -euo pipefail
kubectl config current-context
kubectl version -o yaml
cilium version
cilium status --wait
kubectl -n kube-system get pods -l k8s-app=cilium -o wide
```

Si lo desea, ejecute el conjunto de pruebas de conectividad mantenido en el clúster desechable. Este crea cargas y políticas, y puede comunicarse con destinos externos; revise las pruebas seleccionadas y sus requisitos previos.

```bash
cilium connectivity test --test-namespace cilium-net-smoke \
  --namespace-labels docs-audit-lab=cilium-networking-03
```

La CLI 0.20.1 añade un sufijo de secuencia: la suite individual predeterminada usa `cilium-net-smoke-1`. Revise los fallos y los casos omitidos; que el comando termine no demuestra que funcionen combinaciones de nube o funciones que no se hayan probado.

<details>
<summary>Resultado esperado y autoevaluación</summary>

Las versiones instaladas se ajustan a la matriz documentada, los agentes quedan listos y los casos de conectividad seleccionados pasan. Explique por qué un DaemonSet listo no demuestra por sí solo el enrutamiento entre nodos y por qué «kubectl 1.31 o posterior» no basta para un servidor de API más reciente.

</details>

## 2. Pruebas de políticas de red

### Crear un espacio de nombres de prueba aislado y las cargas de trabajo

```bash
kubectl create namespace cilium-net-lab
kubectl label namespace cilium-net-lab docs-audit-lab=cilium-networking-03
```

Si al crear el espacio de nombres se indica que ya existe, deténgase y elija un nombre nuevo que use de forma coherente en todos los archivos y comandos. No cambie las etiquetas ni reutilice el espacio de nombres de otra persona.

Los digests de las imágenes siguientes proceden de los valores predeterminados de pruebas de la CLI oficial 0.20.1. El código fuente de la implementación usa `/usr/bin/pause` para la imagen curl y un servidor simulado JSON que escucha en TCP 8080 y tiene una comprobación de disponibilidad en `/`. Son imágenes de prueba, no recomendaciones para aplicaciones de producción. La antiafinidad del backend lo separa del frontend entre nodos.

**`lab-app.yaml`**

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: frontend
  namespace: cilium-net-lab
  labels:
    app: frontend
spec:
  automountServiceAccountToken: false
  containers:
  - name: client
    image: quay.io/cilium/alpine-curl:v1.10.0@sha256:913e8c9f3d960dde03882defa0edd3a919d529c2eb167caa7f54194528bde364
    command:
    - /usr/bin/pause
---
apiVersion: v1
kind: Pod
metadata:
  name: outsider
  namespace: cilium-net-lab
  labels:
    app: outsider
spec:
  automountServiceAccountToken: false
  containers:
  - name: client
    image: quay.io/cilium/alpine-curl:v1.10.0@sha256:913e8c9f3d960dde03882defa0edd3a919d529c2eb167caa7f54194528bde364
    command:
    - /usr/bin/pause
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: backend
  namespace: cilium-net-lab
spec:
  replicas: 1
  selector:
    matchLabels:
      app: backend
  template:
    metadata:
      labels:
        app: backend
    spec:
      automountServiceAccountToken: false
      affinity:
        podAntiAffinity:
          requiredDuringSchedulingIgnoredDuringExecution:
          - labelSelector:
              matchLabels:
                app: frontend
            topologyKey: kubernetes.io/hostname
      containers:
      - name: http
        image: quay.io/cilium/json-mock:v1.4.1@sha256:6a66df90808a39c02e7a9d58af7bf0e54d8f8b7d4bc528f48c891969a7049195
        ports:
        - containerPort: 8080
          name: http
        readinessProbe:
          httpGet:
            path: /
            port: http
---
apiVersion: v1
kind: Service
metadata:
  name: backend
  namespace: cilium-net-lab
spec:
  selector:
    app: backend
  ports:
  - name: http
    port: 8080
    targetPort: http
    protocol: TCP
```


```bash
kubectl apply -f lab-app.yaml
kubectl -n cilium-net-lab wait --for=condition=Ready pod/frontend pod/outsider --timeout=120s
kubectl -n cilium-net-lab rollout status deployment/backend --timeout=120s
kubectl -n cilium-net-lab get pods -o wide
kubectl -n cilium-net-lab get endpointslices -l kubernetes.io/service-name=backend
BACKEND_IP=$(kubectl -n cilium-net-lab get service backend -o jsonpath='{.spec.clusterIP}')
test -n "$BACKEND_IP"
```

Un backend en estado Pending puede indicar que no hay suficientes nodos aptos para cumplir la antiafinidad. No lo interprete como un fallo de la política de red. Primero compruebe que **ambos** clientes pueden llegar al backend en buen estado antes de añadir la política. Use la IP del Service para excluir los fallos de DNS de esta prueba de tráfico entrante.

```bash
kubectl -n cilium-net-lab exec frontend -- \
  curl --fail --silent --show-error --connect-timeout 3 --max-time 5 "http://$BACKEND_IP:8080/"
kubectl -n cilium-net-lab exec outsider -- \
  curl --fail --silent --show-error --connect-timeout 3 --max-time 5 "http://$BACKEND_IP:8080/"
```

### Aplicar y comprobar la política

**`allow-frontend.yaml`**

```yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: allow-frontend-to-backend
  namespace: cilium-net-lab
spec:
  endpointSelector:
    matchLabels:
      app: backend
  ingress:
  - fromEndpoints:
    - matchLabels:
        k8s:io.kubernetes.pod.namespace: cilium-net-lab
        k8s:app: frontend
    toPorts:
    - ports:
      - port: '8080'
        protocol: TCP
```


```bash
kubectl apply -f allow-frontend.yaml
kubectl -n cilium-net-lab get ciliumnetworkpolicy allow-frontend-to-backend -o yaml
kubectl -n cilium-net-lab exec frontend -- \
  curl --fail --silent --show-error --connect-timeout 3 --max-time 5 "http://$BACKEND_IP:8080/"
```

Espere a que la política se aplique a los endpoints pertinentes y vuelva a comprobar la solicitud permitida. Que una conexión anterior haya pasado no demuestra que una política nueva ya esté lista; cada comando de esta sección inicia un proceso curl nuevo.

```bash
if kubectl -n cilium-net-lab exec outsider -- \
  curl --fail --silent --show-error --connect-timeout 3 --max-time 5 "http://$BACKEND_IP:8080/"; then
  echo "Unexpected allowed request: inspect combined policy and realization" >&2
  exit 1
else
  denied_rc=$?
  printf 'Outsider request failed with exit %s; correlate the flow before declaring a policy pass.\n' "$denied_rc"
fi
```

Un código de salida distinto de cero **no** demuestra automáticamente que se haya denegado el tráfico. También puede deberse a exec/RBAC, a la ausencia de curl, al enrutamiento, al backend u otros fallos. El timeout de curl suele producir el código de salida 28, pero correlacione el origen, el destino, el puerto y el flujo denegado por la política con la prueba inicial satisfactoria y con el frontend que sigue funcionando. La regla limitada al espacio de nombres no impide que otras políticas permitan el tráfico de forma independiente.

<details>
<summary>Resultado esperado y autoevaluación</summary>

Antes de aplicar la política, ambos clientes llegan al backend. Una vez aplicada, el frontend sigue funcionando y al Pod outsider se le deniega el acceso, con evidencia de la política que lo corrobore. Explique por qué la falta de EndpointSlices, los errores de DNS o cualquier código de salida no nulo no demuestran aislamiento. Esta política L3/L4 no analiza HTTP.

</details>

## 3. Pruebas de visibilidad de Hubble

Use Hubble Relay/UI habilitados por el perfil y una CLI de Hubble compatible. Mantenga este reenvío de puertos en un terminal aparte y ejecute el observador en otro:

```bash
cilium hubble port-forward
```

```bash
hubble status
hubble observe --namespace cilium-net-lab --last 50
hubble observe --from-pod cilium-net-lab/outsider --verdict DROPPED --last 20
cilium hubble ui
```

Genere solicitudes nuevas mientras observa. La pérdida o agregación de eventos y los filtros afectan lo que se ve. Los flujos HTTP requieren un proxy L7 o una configuración de visibilidad compatible; la regla L4 anterior no los crea. Un rechazo L7 configurado puede devolver HTTP 403 en lugar de un evento de paquete DROPPED.

<details>
<summary>Resultado esperado y autoevaluación</summary>

Se puede acceder a Relay, los flujos identifican los endpoints previstos y la evidencia de la prueba negativa corresponde a su solicitud. Explique por qué la ausencia de registros HTTP en este laboratorio solo L4 no demuestra que Hubble esté averiado.

</details>

## 4. Pruebas de rendimiento

Ejecute el ejemplo mantenido de [`cilium connectivity perf` en la guía](../../../networking/cilium/03-networking.md), que crea cargas de cliente y servidor coincidentes. Mantenga separados los resultados del mismo nodo y entre nodos, y registre la ubicación de los nodos, las versiones, las MTU de las rutas y la configuración de políticas y cifrado.

La prueba anterior combinaba nombres de Pods `netperf-*` que no correspondían con una imagen iperf3 y un Service que solo admitía TCP. En una configuración iperf3 independiente, una prueba UDP requiere **control TCP y datos UDP** en los puertos configurados. Solicitar simplemente `-b 1G` no demuestra que se esté transmitiendo a 1 Gbit/s.

<details>
<summary>Resultado esperado y autoevaluación</summary>

Todas las cargas de prueba seleccionadas están listas y los resultados están etiquetados por escenario. Explique la diferencia entre solicitud/respuesta TCP, creación de conexiones, caudal de un flujo y tasa ofrecida y pérdida de paquetes en UDP. Un resultado de benchmark solo corresponde a la configuración registrada, no a todos los modos de Cilium o de la nube.

</details>

## 5. Comprobaciones opcionales de funciones avanzadas

Configure cada función mediante un perfil documentado preparado por separado. **No desinstale el CNI del clúster entre comprobaciones.** Un indicador de Helm no aporta por sí solo claves, rutas, acceso a la API ni peers BGP que falten.

| Función | Preparación | Qué observar |
|---|---|---|
| Reemplazo de kube-proxy | `kubeProxyReplacement: true`, valores accesibles para `k8sServiceHost`/`k8sServicePort`, datapath compatible y plan de migración | Estado real del agente y tráfico de Service; `strict` ya no es un valor vigente |
| IPsec/WireGuard | Modo de cifrado correcto, gestión de claves, puertos/MTU y alcance de tráfico compatible | Estado de cifrado del agente y ruta real entre nodos |
| BGP Control Plane | `bgpControlPlane.enabled: true`, recursos BGP versionados y peers configurados accesibles | Sesiones y rutas anunciadas; no dé por hecho que se programan rutas en la tabla de reenvío local |

Elija el agente del nodo pertinente:

```bash
kubectl -n kube-system get pods -l k8s-app=cilium -o wide
export CILIUM_POD=cilium-REPLACE-WITH-AGENT-ON-TARGET-NODE
kubectl -n kube-system exec "$CILIUM_POD" -c cilium-agent -- cilium-dbg status --verbose
kubectl -n kube-system exec "$CILIUM_POD" -c cilium-agent -- cilium-dbg encrypt status
cilium bgp peers
kubectl get ciliumbgpclusterconfigs,ciliumbgppeerconfigs,ciliumbgpadvertisements
```

Interprete los comandos opcionales de una función solo si esta está configurada. En el perfil base, el estado deshabilitado/no configurado es lo esperado. El comando independiente `cilium bgp peers` informa sobre los estados de los nodos del clúster; los comandos BGP antiguos, ejecutados dentro de un agente, están obsoletos. BGP requiere los recursos de configuración aplicables de `cilium.io/v2`; los ajustes eliminados `bgp.enabled` y `bgp.announce.loadbalancerIP` no establecen una sesión.

<details>
<summary>Resultado esperado y autoevaluación</summary>

El estado observado coincide con el perfil elegido y la evidencia pertinente de tráfico/rutas respalda el resultado. Explique por qué «BGP establecido» no demuestra el enrutamiento interno de Pods o por qué el estado del cifrado por sí solo no demuestra que se cifran todas las rutas del tráfico.

</details>

## 6. Comprobaciones de compatibilidad

```bash
kubectl version -o yaml
cilium version
kubectl get nodes -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.status.nodeInfo.kernelVersion}{"\n"}{end}'
kubectl -n kube-system get configmap cilium-config -o yaml
kubectl -n kube-system get daemonset cilium -o yaml
```

Compare las versiones y funciones con la matriz de compatibilidad, incluidos los backports de kernel documentados. Inspeccione la configuración CNI real y los montajes de volúmenes antes de leer un archivo de configuración del host: `/etc/cni/net.d/05-cilium.conf` no es una ruta ni un nombre de archivo universal dentro de los contenedores. Las configuraciones encadenadas o personalizadas son distintas. Que exista un archivo no demuestra compatibilidad en tiempo de ejecución.

<details>
<summary>Resultado esperado y autoevaluación</summary>

Los requisitos de versión y kernel coinciden con la plataforma, los Pods reciben direcciones mediante el CNI previsto y las pruebas de tráfico pasan. Explique la diferencia entre instalar el CNI, asignar IPAM y reenviar tráfico de extremo a extremo.

</details>

## 7. Solución de problemas

```bash
cilium status --verbose
kubectl -n kube-system logs "$CILIUM_POD" -c cilium-agent --tail=100
kubectl -n kube-system logs deployment/cilium-operator --tail=100
kubectl -n kube-system logs deployment/hubble-relay --tail=100
```

Para un endpoint frontend, seleccione el agente del nodo del frontend antes de inspeccionarlo:

```bash
kubectl -n cilium-net-lab get pod frontend -o wide
kubectl -n kube-system exec "$CILIUM_POD" -c cilium-agent -- \
  cilium-dbg endpoint get pod-name:cilium-net-lab:frontend
```

Si se deniega el ingreso, inspeccione también el agente/endpoint del backend. Compare la política deseada con su estado aplicado, el estado de la ruta y del backend, y los flujos observados. No use los comandos eliminados `policy trace` ni analice tablas legibles por personas con un marcador `<pod-name>` sin entrecomillar en el shell.

Si hace falta, `cilium sysdump` recopila diagnósticos; revise los registros y la información de recursos del archivo antes de compartirlo. `cilium clustermesh status` solo se aplica a Cluster Mesh configurado. Después de establecer la conexión, consulte el estado de Relay con `hubble status`.

<details>
<summary>Resultado esperado y autoevaluación</summary>

La evidencia identifica el nodo y el endpoint correctos, no cualquier Pod del DaemonSet que kubectl haya seleccionado. Explique qué evidencia permite distinguir entre un backend que no está listo, un fallo de ruta, una denegación de política y la falta de observación.

</details>

## 8. Limpieza

Revise qué espacios de nombres creó esta ejecución y guarde primero los resultados:

```bash
kubectl get namespaces -l docs-audit-lab=cilium-networking-03
LAB_OWNER=$(kubectl get namespace cilium-net-lab -o jsonpath='{.metadata.labels.docs-audit-lab}')
test "$LAB_OWNER" = cilium-networking-03
kubectl delete namespace cilium-net-lab
```

Si ejecutó las suites de CLI, verifique por separado la propiedad antes de eliminar sus espacios de nombres generados `cilium-net-smoke-1` o `cilium-net-perf-1`. No elimine en bloque espacios de nombres ajenos ni desinstale Cilium como parte de la limpieza de la aplicación. Detenga los reenvíos de puertos locales con Ctrl-C.

<details>
<summary>Resultado esperado y autoevaluación</summary>

Solo se eliminan los recursos de prueba de esta ejecución; el CNI instalado y las demás cargas de trabajo siguen funcionando. Explique por qué desinstalar repetidamente el CNI no era una forma válida de comparar funciones.

</details>

## Límites de validación y referencias

Se comprobaron los valores YAML/Helm publicados, la sintaxis de shell y los contratos de CLI/API sin implementar estas cargas. Tras reiniciar el host no se afirma haber usado un clúster activo ni haber ejecutado imágenes, renderizado Helm o medido el caudal. Hay que verificar en el entorno preparado la admisión, la arquitectura de las imágenes y su política de descarga, la capacidad, el plano de datos real y los resultados esperados.

- [Valores predeterminados de imágenes de CLI 0.20.1](https://github.com/cilium/cilium-cli/blob/v0.20.1/vendor/github.com/cilium/cilium/cilium-cli/defaults/defaults.go), [implementaciones de prueba](https://github.com/cilium/cilium-cli/blob/v0.20.1/vendor/github.com/cilium/cilium/cilium-cli/connectivity/check/deployment.go), [indicadores de conectividad/rendimiento](https://github.com/cilium/cilium-cli/blob/v0.20.1/vendor/github.com/cilium/cilium/cilium-cli/cli/connectivity.go)
- [API de políticas de Cilium 1.20.3](https://github.com/cilium/cilium/blob/v1.20.3/pkg/k8s/apis/cilium.io/client/crds/v2/ciliumnetworkpolicies.yaml), [comportamiento L7](https://github.com/cilium/cilium/blob/v1.20.3/Documentation/security/policy/layer7.rst), [configuración BGP](https://github.com/cilium/cilium/blob/v1.20.3/Documentation/network/bgp-control-plane/bgp-control-plane-configuration.rst), [CLI BGP](https://github.com/cilium/cilium-cli/blob/v0.20.1/vendor/github.com/cilium/cilium/cilium-cli/cli/bgp.go), [comandos del agente](https://github.com/cilium/cilium/tree/v1.20.3/Documentation/cmdref)
- [Desviación de versiones de Kubernetes](https://kubernetes.io/releases/version-skew-policy/), [uso de iperf3](https://software.es.net/iperf/invoking.html), [guía de redes](../../../networking/cilium/03-networking.md)
