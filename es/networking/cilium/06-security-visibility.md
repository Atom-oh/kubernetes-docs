# Seguridad y visibilidad

> **Base de revisión**: Cilium 1.20.3; CLI de Cilium 0.20.1; CLI de Hubble 1.20.2.
> **Última revisión**: 16 de octubre de 2026. Kubernetes 1.33–1.36 es el intervalo de compatibilidad de Cilium 1.20; elige una versión de kubectl dentro de la desviación admitida por el servidor de API.

## Preparación del entorno de laboratorio

Usa un clúster de pruebas existente con Cilium 1.20.3, al menos dos nodos Linux aptos para la programación, DNS operativo y la aplicación de políticas habilitada. Sigue los [requisitos previos de instalación y plataforma](README.md), incluidas las restricciones de EKS y las descargas verificadas de las CLI. Estos ejemplos no instalan ni reemplazan una CNI. Necesitas Helm, kubectl, las CLI de Cilium y Hubble, y jq.

El laboratorio presupone que los Pods de CoreDNS tienen la etiqueta `k8s-app=kube-dns` en `kube-system`. Comprueba la ruta real del resolver; NodeLocal DNS u otra distribución requiere destinos y puertos distintos. Las políticas, la configuración del proxy y los controles de la plataforma que ya estén presentes en el clúster pueden afectar los resultados.

### Instalación y configuración de Hubble

Guarda `hubble-values.yaml`. Este fragmento habilita los servidores locales, Relay, la interfaz de usuario y los complementos de métricas seleccionados. Aplícalo a una **versión existente del chart y con la misma versión**; primero revisa los valores de la instalación actual. Para actualizar la versión, sigue el procedimiento de actualización en lugar de reutilizar valores antiguos sin revisarlos.

```yaml
# hubble-values.yaml
hubble:
  enabled: true
  relay:
    enabled: true
  ui:
    enabled: true
  metrics:
    enabled:
    - dns
    - drop
    - tcp
    - flow
    - httpV2
    serviceMonitor:
      enabled: false
```
```bash
helm upgrade cilium cilium/cilium --namespace kube-system \
  --version 1.20.3 --reuse-values --values hubble-values.yaml --wait
cilium status --wait
# Terminal 1: keep this process running; stop it with Ctrl-C.
cilium hubble port-forward
```

En otra terminal, verifica la conectividad de la API. El reenvío de puertos se mantiene en el entorno local; no publica Relay ni la interfaz de usuario a través de un LoadBalancer público.

```bash
# Terminal 2
hubble status
hubble observe --last 20
# Optional UI; keep its local forwarding process running while using it.
cilium hubble ui
```

## Características de seguridad de Cilium

Cilium combina políticas de red con identidades de extremos y cifrado opcional. Hubble permite observar los eventos de red resultantes. Es importante tener en cuenta los límites de cada función al evaluar un requisito de seguridad.

### Arquitectura de seguridad de Cilium

| Responsabilidad | Componente y alcance |
| --- | --- |
| Microsegmentación de red | La política L3/L4 de Cilium selecciona identidades, direcciones IP, puertos y sentido del tráfico. Un CiliumNetworkPolicy con ámbito de espacio de nombres selecciona los extremos de ese espacio. |
| Política HTTP | La integración de Envoy de Cilium filtra métodos, rutas y encabezados cuando el proxy puede ver el tráfico HTTP. La política DNS usa el proxy de DNS. |
| Control de DNS/FQDN | Las reglas de DNS controlan las consultas; `toFQDNs` permite las direcciones IP de destino que se obtienen de las respuestas DNS observadas. Esto no equivale a un flujo automático de reputación de dominios maliciosos. |
| Cifrado del tráfico entre nodos | IPsec o WireGuard protegen el tráfico admitido entre nodos. La cobertura depende del modo y de la configuración. |
| Investigación de red | Hubble registra metadatos de flujos y veredictos de políticas; Relay, la CLI y la interfaz de usuario los exponen. |
| Seguridad de procesos y llamadas al sistema | **Tetragon** es un proyecto independiente para eventos de ejecución y aplicación de controles configurados. Habilitar Hubble no lo instala. |
| Detección y respuesta ante amenazas | Para la detección y las acciones previstas, hay que configurar reglas de alertas externas, SIEM/WAF y controladores de respuesta. |

### Seguridad de red y de aplicaciones

Aplica políticas de mínimo privilegio para limitar el movimiento lateral y define explícitamente la salida para limitar las dependencias. Las identidades de seguridad se derivan de etiquetas relevantes para la seguridad; no son necesariamente únicas por Pod y no autentican a un usuario final.

Las políticas actuales de Cilium admiten reglas L7 para HTTP y DNS. gRPC puede usar reglas HTTP de método/ruta/encabezado cuando el tráfico HTTP/2 está visible. Las políticas de temas de Kafka ya no son compatibles. Las entradas `headers` de una regla HTTP que tienen valores son coincidencias literales, no autenticación mediante expresiones regulares. La presencia o el formato de un encabezado `Authorization` no valida el JWT, su emisor, su firma ni sus declaraciones de autorización. Para ello, usa la capa de autenticación de la aplicación o una pasarela configurada.

Una regla HTTP en el puerto 8443 no descifra HTTPS. Antes de evaluar la política HTTP, es necesario terminar TLS o configurar otro mecanismo de inspección admitido. No eludas el cifrado de una malla de servicios para que funcione la inspección L7.

### Identidad, autenticación y cifrado

La **autenticación mutua basada en SPIRE de Cilium es Beta, pero está obsoleta en la versión 1.20** (se eliminó en la versión preliminar 1.21; las notas de actualización de 1.20 indican que está obsoleta y señalan el cifrado transparente de ztunnel como alternativa, por lo que no debe elegirse para diseños nuevos): realiza un intercambio de autenticación fuera de banda para identidades de seguridad. Ese intercambio, por sí solo, no cifra el tráfico de la aplicación. Entre sus limitaciones documentadas están la falta de compatibilidad con ClusterMesh y con sistemas mTLS externos arbitrarios. La función independiente de mTLS para cargas de trabajo de ztunnel también está en Beta; tiene sus propios requisitos de registro y certificados. Ninguna de las dos funciones debe presentarse como una consecuencia automática de seleccionar una identidad.

### Configuración del cifrado

Los siguientes son **fragmentos alternativos de Helm**, no dos opciones que deban habilitarse a la vez. Elige una para una instalación o cambio planificado y valida los requisitos previos del kernel, el enrutamiento y la plataforma.

```yaml
# wireguard-values.yaml
encryption:
  enabled: true
  type: wireguard
  nodeEncryption: false
```
```yaml
# ipsec-values.yaml
encryption:
  enabled: true
  type: ipsec
  nodeEncryption: false
  ipsec:
    secretName: cilium-ipsec-keys
```

WireGuard requiere compatibilidad del kernel y una ruta UDP entre nodos por el puerto 51871. IPsec requiere que exista en el espacio de nombres de Cilium un Secret `cilium-ipsec-keys` con el formato correcto y gestionado de forma segura antes de habilitarse; sigue el procedimiento oficial para crear y rotar las claves. Nombrar un archivo de claves en un ConfigMap no crea esa clave ni aprovisiona su volumen.

De forma predeterminada, estos modos protegen el tráfico de Pods gestionado por Cilium que cruza entre nodos compatibles; los túneles entre nodos no cifran el tráfico dentro de un mismo nodo. Tampoco cubren automáticamente el tráfico hacia destinos externos arbitrarios. El cifrado WireGuard entre nodos (`encryption.nodeEncryption`) es una opción Beta independiente, obsoleta en la versión preliminar 1.21 y cuya eliminación está prevista para la 1.22; los nodos del plano de control quedan excluidos de esa ampliación de forma predeterminada, aunque sí se puede cifrar el tráfico entre nodos de Pods gestionado por Cilium. Verifica la ruta real de los paquetes y usa TLS de aplicación cuando sea necesario. La compatibilidad del cortafuegos del host también depende del modo de cifrado: las políticas de host no funcionan junto con IPsec (así se documenta en los problemas conocidos de políticas de host de la versión preliminar 1.21).

## Visibilidad de red con Hubble

Hubble recibe eventos del plano de datos, del proxy y de los agentes, y los enriquece con metadatos de Kubernetes. No es simplemente un lector que consulta periódicamente todos los mapas de eBPF.

```text
Kernel/datapath events + proxy/agent events
                  |
                  v
       Hubble server in each Cilium agent
          |             |                |
   bounded flow      metric endpoint   optional file exporter
      buffer          TCP 9965            |
          |             ^             log collector/storage
     Relay query        | scrape
          ^          Prometheus <--- Grafana queries
          |
       CLI / UI
```

El servidor mantiene un historial acotado en memoria. Relay consulta varios servidores; no es una base de datos duradera. La interfaz de usuario ofrece exploración de flujos y mapas de dependencias de servicios, mientras que la CLI admite filtros explícitos. Que no haya registros coincidentes puede deberse a que no hubo tráfico, al filtro equivocado, a pares no disponibles, a falta de visibilidad L7 o a que los eventos se sobrescribieron o se perdieron.

### Ejemplos de uso de la CLI de Hubble

```bash
hubble observe --namespace cilium-security-demo --last 100
hubble observe --from-pod cilium-security-demo/frontend \
  --to-service cilium-security-demo/backend --last 100
hubble observe --namespace cilium-security-demo --protocol http \
  --http-status '4+' --http-status '5+' --last 100
hubble observe --namespace cilium-deny-demo --verdict DROPPED \
  --drop-reason-desc POLICY_DENIED --last 100
hubble observe --pod cilium-security-demo/frontend --follow
```

`--pod namespace/name` coincide con cualquiera de los dos extremos; usa `--from-pod`/`--to-pod` para indicar la dirección. Los nombres de Pods no son selectores de etiquetas: usa `--from-label` o `--to-label` cuando necesites seleccionar etiquetas. No combines `--namespace` con `--from-pod`/`--to-pod`; la CLI rechaza esa combinación.

`DROPPED` es un veredicto. `POLICY_DENIED` es un motivo de descarte que se selecciona con `--drop-reason-desc`. Los prefijos de estado HTTP usan `4+` y `5+`, no `4..` ni `5..`. Los filtros HTTP requieren eventos L7 derivados del proxy; una conexión TCP descartada no tiene por qué incluir un estado HTTP.

## Visibilidad y supervisión de red

### Métricas de Hubble

Los complementos habilitados exponen observaciones distintas:

| Complemento | Ejemplo de métrica | Significado y límite |
| --- | --- | --- |
| `flow` | `hubble_flows_processed_total` | Eventos de flujo procesados por protocolo/tipo/veredicto; no son solicitudes únicas ni paquetes de todas las rutas. |
| `drop` | `hubble_drop_total{reason="POLICY_DENIED"}` | Descartes observados; la etiqueta del motivo es el nombre de la enumeración. |
| `tcp` | `hubble_tcp_flags_total` | Banderas TCP observadas; no es una métrica general de RTT, retransmisiones o conexiones simultáneas. |
| `dns` | `hubble_dns_queries_total`, `hubble_dns_responses_total` | Consultas/respuestas DNS observadas y códigos de respuesta; no es un histograma genérico de latencia DNS. |
| `httpV2` | `hubble_http_requests_total`, `hubble_http_request_duration_seconds` | Recuentos/estados y duración en segundos derivados de flujos de respuestas HTTP. Requiere visibilidad HTTP. |

No habilites `http` y `httpV2` a la vez. Elige cuidadosamente las etiquetas de origen/destino para controlar la cardinalidad y no añadas encabezados de solicitudes o identidades sensibles sin motivo. Comprueba `hubble_lost_events_total` y la disponibilidad de los pares antes de interpretar un evento ausente como prueba de que no hubo tráfico.

### Integración con Prometheus

El chart crea el Service headless `hubble-metrics` en el espacio de nombres de Cilium y, de forma predeterminada, expone el puerto **9965**. Para el descubrimiento se usa la etiqueta `k8s-app=hubble` del Service; el Service selecciona los Pods de agente con la etiqueta `k8s-app=cilium`. Prometheus debe descubrir los extremos individuales en lugar de depender de un único destino DNS estático.

Si ya tienes Prometheus Operator y la CRD ServiceMonitor, combina este fragmento con los valores de la versión desplegada. `release: monitoring` es un ejemplo: debe coincidir con `serviceMonitorSelector` de Prometheus, y su selector de espacios de nombres debe incluir el espacio donde reside el ServiceMonitor. Prometheus no recopilará un recurso que no seleccione.

```yaml
# hubble-servicemonitor-values.yaml
hubble:
  metrics:
    serviceMonitor:
      enabled: true
      labels:
        release: monitoring
```

El ServiceMonitor del chart usa el puerto con nombre `hubble-metrics` y los extremos del espacio de nombres de Cilium. Sin Operator, configura un descubrimiento de servicios de Kubernetes equivalente en la configuración real de Prometheus. Crear un ConfigMap no relacionado no configura Prometheus. `*.hubble-metrics.cilium.io` se usa en la configuración de identidad TLS de métricas; no es un destino público de recopilación en el puerto 9091.

Los paneles de Grafana consultan las métricas de Prometheus; el mapa de servicios de la interfaz de Hubble consulta Relay. Importa paneles que correspondan a los complementos y etiquetas habilitados. Los paneles HTTP estarán vacíos para el tráfico cuya carga HTTP no sea observable.

### Exportación de flujos y retención

Para generar archivos locales rotados en cada nodo, combina opcionalmente el fragmento `hubble-export-values.yaml` con los valores de la versión instalada. La máscara de campos conserva deliberadamente los metadatos de red; no exporta todos los encabezados HTTP.

```yaml
# hubble-export-values.yaml
hubble:
  export:
    static:
      enabled: true
      filePath: /var/run/cilium/hubble/events.log
      fileMaxSizeMb: 10
      fileMaxBackups: 5
      fieldMask:
      - time
      - source.namespace
      - source.pod_name
      - destination.namespace
      - destination.pod_name
      - l4
      - IP
      - node_name
      - is_reply
      - verdict
      - drop_reason_desc
```

El exportador estático escribe en cada nodo y rota los archivos según su configuración. Si los eventos deben sobrevivir a la pérdida de un nodo, configura por separado un recopilador, controles de acceso y retención del almacenamiento. Los cambios de configuración estática requieren desplegar de nuevo los agentes; el exportador dinámico admite un comportamiento de actualización distinto. Los filtros y las máscaras de campos del exportador pueden omitir eventos/campos deliberadamente, y los búferes finitos también pueden perder observaciones.

## Detección de amenazas en tiempo real

Hubble proporciona evidencia para las investigaciones; no incluye un interruptor que lo convierta en un IDS, WAF o sistema de cuarentena automática completo. No existen opciones compatibles de Cilium llamadas `enable-threat-detection`, `enable-anomaly-detection` o `alert-to-slack`.

La repetición de destinos denegados puede sugerir un escaneo; un pico de tráfico puede justificar una investigación. Estas observaciones no demuestran que haya un ataque. Correlaciónalas con los registros de autenticación de la aplicación, los cambios de cargas de trabajo, los eventos de auditoría de la API y, cuando esté desplegado, los eventos de ejecución de Tetragon. La inyección SQL, XSS y la inyección de comandos requieren reglas adecuadas de aplicación/WAF/detección; un registro de flujo HTTP normal, por sí solo, no las clasifica.

Para generar alertas, define y prueba reglas externas de Prometheus/SIEM frente a tráfico normal, datos ausentes y pérdida de eventos. Los límites de tasa, el aislamiento del cortafuegos y la automatización de respuestas son controles configurados por separado. Limita el alcance de la respuesta y proporciona una vía de recuperación; no aísles automáticamente cada Pod que registre un paquete descartado.

## Laboratorio: instalación y uso de Hubble

Este laboratorio usa dos espacios de nombres **nuevos e independientes** para que una regla amplia de autorización no invalide el ejercicio de denegación predeterminada. No crea bases de datos ni usa API externas. Los comandos son ejemplos para tu clúster de pruebas; la auditoría de documentación comprobó esquemas y pruebas locales, no un despliegue activo.

### 1. Crear y comprobar las cargas de trabajo

Guarda `visibility-app.yaml`. Las imágenes de cliente y servidor coinciden con los valores de prueba versionados de la CLI de Cilium. La antiafinidad del backend requiere un segundo nodo apto para la programación, de modo que la ruta del frontend al backend cruce entre nodos.

```yaml
# visibility-app.yaml
apiVersion: v1
kind: Pod
metadata:
  name: frontend
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
set -eu
for ns in cilium-security-demo cilium-deny-demo; do
  kubectl create namespace "$ns"
  kubectl label namespace "$ns" audit-lab=security-visibility
  kubectl --namespace "$ns" apply -f visibility-app.yaml
  kubectl --namespace "$ns" wait --for=condition=Ready pod/frontend pod/outsider --timeout=120s
  kubectl --namespace "$ns" rollout status deployment/backend --timeout=120s
  for client in frontend outsider; do
    kubectl --namespace "$ns" exec "$client" -- \
      curl --fail --silent --show-error --max-time 5 http://backend:8080/
  done
done
```

Antes de aplicar la política, los dos clientes de ambos espacios de nombres deben poder acceder al backend. Si no pueden, resuelve primero los problemas de disponibilidad, programación, DNS y red. No deduzcas que la política denegó el tráfico a partir de cualquier error arbitrario de curl.

### 2. Aplicar y observar una política HTTP

Guarda `backend-http.yaml`. Permite que la identidad `frontend` haga `GET /` al puerto TCP 8080 del backend. Ninguna regla amplia de entrada debe solaparse con este ejemplo: una autorización L4 podría eludir la restricción L7 prevista.

```yaml
# backend-http.yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: backend-http
  namespace: cilium-security-demo
spec:
  endpointSelector:
    matchLabels:
      app: backend
  ingress:
  - fromEndpoints:
    - matchLabels:
        k8s:io.kubernetes.pod.namespace: cilium-security-demo
        k8s:app: frontend
    toPorts:
    - ports:
      - port: '8080'
        protocol: TCP
      rules:
        http:
        - method: GET
          path: /
```
```bash
kubectl apply -f backend-http.yaml
# After the endpoint has realized the policy:
kubectl -n cilium-security-demo exec frontend -- \
  curl --fail --silent --show-error --max-time 5 http://backend:8080/
# Display the HTTP response code; do not use --fail here.
kubectl -n cilium-security-demo exec frontend -- \
  curl --silent --show-error --max-time 5 --output /dev/null \
    --write-out '%{http_code}\n' --request POST http://backend:8080/
# A separate client is not in the allowed identity selector.
kubectl -n cilium-security-demo exec outsider -- \
  curl --silent --show-error --max-time 5 http://backend:8080/
hubble observe --namespace cilium-security-demo --verdict DROPPED --last 100
```

Una vez aplicada la política, se espera que el `GET /` del frontend tenga éxito y que el `POST /` reciba un HTTP 403 del proxy. La nueva conexión del cliente externo debe denegarse en L3/L4. Correlaciona el momento de la solicitud, los extremos y el evento de Hubble; los errores DNS, los contenedores ausentes y otros errores HTTP no constituyen una prueba de denegación correcta. Usa la interfaz de Hubble para inspeccionar la arista de dependencia y los descartes generados.

Para un backend real que necesite una base de datos y una API externa, la siguiente **política opcional de dependencias** ilustra la salida. Este laboratorio no la aplica: sustituye `database` y `api.example.com` por dependencias reales. Primero verifica los extremos de DNS.

```yaml
# backend-dependencies.yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: backend-dependencies
  namespace: cilium-security-demo
spec:
  endpointSelector:
    matchLabels:
      app: backend
  egress:
  - toEndpoints:
    - matchLabels:
        k8s:io.kubernetes.pod.namespace: kube-system
        k8s:k8s-app: kube-dns
    toPorts:
    - ports:
      - port: '53'
        protocol: UDP
      - port: '53'
        protocol: TCP
      rules:
        dns:
        - matchPattern: '*'
  - toEndpoints:
    - matchLabels:
        k8s:io.kubernetes.pod.namespace: cilium-security-demo
        k8s:app: database
    toPorts:
    - ports:
      - port: '3306'
        protocol: TCP
  - toFQDNs:
    - matchName: api.example.com
    toPorts:
    - ports:
      - port: '443'
        protocol: TCP
```

Se permite DNS por TCP y UDP, y las reglas del proxy DNS permiten a Cilium observar las respuestas que usa `toFQDNs`. Permitir consultas DNS no equivale a permitir después conexiones a las direcciones IP resueltas. El comodín DNS `*` de esta política permite todas las consultas; no es una lista de bloqueo de dominios.

### 3. Verificar por separado la denegación predeterminada

Guarda `deny-except-dns.yaml`. El `policyTypes` explícito activa el aislamiento en ambas direcciones; `ingress: []` **no contiene ninguna regla que permita tráfico de entrada**. La única excepción de salida permite DNS únicamente a los Pods del resolver seleccionados.

```yaml
# deny-except-dns.yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: deny-except-dns
  namespace: cilium-deny-demo
spec:
  podSelector: {}
  policyTypes:
  - Ingress
  - Egress
  ingress: []
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
```
```bash
kubectl apply -f deny-except-dns.yaml
kubectl -n cilium-deny-demo exec frontend -- \
  curl --silent --show-error --max-time 5 http://backend:8080/
hubble observe --namespace cilium-deny-demo --verdict DROPPED \
  --drop-reason-desc POLICY_DENIED --last 100
```

No reemplaces la lista de entrada vacía por `ingress: [{}]`: esa forma permite toda la entrada. Las reglas de autorización de NetworkPolicy se suman, así que otra política puede abrir tráfico. Las reglas de denegación de Cilium y las políticas del clúster pueden imponer más restricciones. Este ejercicio de espacio de nombres no afirma aislar el tráfico de la red del host ni todas las rutas originadas por el host.

### 4. Inspeccionar JSON y exportar un resumen local

Guarda lo siguiente como `flow-summary.jq`. `--output jsonpb` entrega la envoltura de respuesta protobuf con `.flow`; así no dependes de la antigua opción de compatibilidad `json` de la CLI.

```text
[.[] | select(.flow != null) | .flow] as $flows
| {
    flow_records: ($flows | length),
    other_records: (length - ($flows | length)),
    policy_denied_records: (
      [$flows[] | select(.verdict == "DROPPED"
                        and .drop_reason_desc == "POLICY_DENIED")] | length
    ),
    dropped_by_reason: (
      [$flows[] | select(.verdict == "DROPPED")]
      | group_by(.drop_reason_desc // "UNKNOWN")
      | map({reason: (.[0].drop_reason_desc // "UNKNOWN"), records: length})
    )
  }
```
```bash
set -eu
hubble observe --namespace cilium-deny-demo --last 100 --output jsonpb > flows.jsonl
jq --slurp --from-file flow-summary.jq flows.jsonl
```

El resultado cuenta **registros de flujos de esta muestra finita**, no ataques, conexiones únicas ni todos los paquetes del clúster. Cuenta por separado los registros que no son flujos; revísalos para detectar pérdida o información de estado. Para un filtro local en tiempo real:

```bash
hubble observe --namespace cilium-deny-demo --follow --output jsonpb |
  jq --unbuffered -c 'select(.flow.verdict == "DROPPED"
    and .flow.drop_reason_desc == "POLICY_DENIED")'
```

Esta canalización solo imprime resultados localmente. Las notificaciones requieren una integración, credenciales, una política de reintentos/eliminación de duplicados y tratamiento de fallos del flujo, todo configurado por separado.

### 5. Limpiar los espacios de nombres de prueba

Después de revisar los nombres de espacios de nombres, elimina solo las cargas de trabajo y políticas de este laboratorio. La comprobación de propiedad se detiene si falla la consulta o si encuentra una etiqueta distinta.

```bash
set -eu
for ns in cilium-security-demo cilium-deny-demo; do
  LAB_OWNER=$(kubectl get namespace "$ns" -o jsonpath='{.metadata.labels.audit-lab}')
  test "$LAB_OWNER" = security-visibility
  kubectl delete namespace "$ns"
done
```

## Referencias principales

- [Aplicación de políticas de Cilium](https://raw.githubusercontent.com/cilium/cilium/v1.20.3/Documentation/security/policy/intro.rst)
- [NetworkPolicy de Kubernetes](https://kubernetes.io/docs/concepts/services-networking/network-policies/)
- [Políticas HTTP](https://raw.githubusercontent.com/cilium/cilium/v1.20.3/Documentation/security/policy/layer7.rst)
- [Políticas DNS](https://raw.githubusercontent.com/cilium/cilium/v1.20.3/Documentation/security/dns.rst)
- [Configuración de Hubble](https://raw.githubusercontent.com/cilium/cilium/v1.20.3/Documentation/observability/hubble/setup.rst)
- [Métricas](https://raw.githubusercontent.com/cilium/cilium/v1.20.3/Documentation/observability/metrics.rst)
- [Exportador de flujos](https://raw.githubusercontent.com/cilium/cilium/v1.20.3/Documentation/observability/hubble/configuration/export.rst)
- [WireGuard](https://raw.githubusercontent.com/cilium/cilium/v1.20.3/Documentation/security/network/encryption-wireguard.rst)
- [IPsec](https://raw.githubusercontent.com/cilium/cilium/v1.20.3/Documentation/security/network/encryption-ipsec.rst)
- [Autenticación mutua](https://raw.githubusercontent.com/cilium/cilium/v1.20.3/Documentation/network/servicemesh/mutual-authentication/mutual-authentication.rst)
- [ztunnel](https://raw.githubusercontent.com/cilium/cilium/v1.20.3/Documentation/security/network/encryption-ztunnel.rst)
- [Tetragon](https://raw.githubusercontent.com/cilium/tetragon/main/README.md)
- [Filtros de la CLI de Hubble](https://raw.githubusercontent.com/cilium/hubble/v1.20.2/vendor/github.com/cilium/cilium/hubble/cmd/observe/flows.go)

[Volver a la página principal](README.md)

## Cuestionario

Evalúa las diferencias entre políticas, cifrado y observabilidad con el [cuestionario del tema](../../quizzes/networking/cilium/06-security-visibility-quiz.md).
