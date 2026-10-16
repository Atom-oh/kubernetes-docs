# Seguridad y visibilidad

> **Referencia de revisión**: Cilium 1.20.2; Cilium CLI 0.20.1; Hubble CLI 1.20.2.
> **Última revisión**: October 15, 2026. Kubernetes 1.33–1.36 es el rango de compatibilidad de Cilium 1.20; elija kubectl dentro de la desviación de versiones compatible del servidor de API.

## Configuración del entorno de laboratorio

Use un clúster de prueba existente de Cilium 1.20.2 con al menos dos nodos Linux programables, DNS funcional y aplicación de políticas habilitada. Siga [los requisitos previos de instalación y plataforma](README.md), incluidas las restricciones de EKS y las descargas verificadas de CLI. Estos ejemplos no instalan ni reemplazan un CNI. Requieren Helm, kubectl, las CLI de Cilium y Hubble, y jq.

El laboratorio presupone Pods de CoreDNS con la etiqueta `k8s-app=kube-dns` en `kube-system`. Verifique la ruta real del resolvedor; NodeLocal DNS o una distribución distinta requiere destinos/puertos diferentes. Las políticas, la configuración de proxy y los controles de plataforma ya presentes en el clúster pueden afectar los resultados.

### Instalación y configuración de Hubble

Guarde `hubble-values.yaml`. Este fragmento habilita los servidores locales, Relay, UI y plugins de métricas seleccionados. Aplíquelo a una **release existente con la misma versión de chart**; primero revise los valores de instalación conservados. Para una actualización de versión, use el procedimiento de actualización en lugar de reutilizar a ciegas valores antiguos.

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
  --version 1.20.2 --reuse-values --values hubble-values.yaml --wait
cilium status --wait
# Terminal 1: keep this process running; stop it with Ctrl-C.
cilium hubble port-forward
```

En otra terminal, verifique la conectividad de API. El reenvío de puertos permanece local; no publica Relay ni UI mediante un LoadBalancer público.

```bash
# Terminal 2
hubble status
hubble observe --last 20
# Optional UI; keep its local forwarding process running while using it.
cilium hubble ui
```

## Funciones de seguridad de Cilium

Cilium combina la política de red con identidades de endpoint y cifrado opcional. Hubble hace observables los eventos de red resultantes. Sus límites son importantes al evaluar un requisito de seguridad.

### Arquitectura de seguridad de Cilium

| Responsabilidad | Componente y alcance |
| --- | --- |
| Microsegmentación de red | La política L3/L4 de Cilium selecciona identidades, direcciones, puertos y direcciones de tráfico. Una CiliumNetworkPolicy con namespace selecciona endpoints en su namespace. |
| Política HTTP | La integración Envoy de Cilium filtra métodos, rutas y encabezados cuando el proxy puede ver HTTP. La política DNS usa el proxy DNS. |
| Control DNS/FQDN | Las reglas DNS controlan las consultas; `toFQDNs` permite direcciones IP de destino aprendidas de respuestas DNS observadas. Esto no es una fuente automática de reputación de dominios maliciosos. |
| Cifrado de transporte entre nodos | IPsec o WireGuard protege el tráfico compatible entre nodos. La cobertura depende del modo y la configuración. |
| Investigación de red | Hubble registra metadatos de flujos y veredictos de política; Relay, CLI y UI los exponen. |
| Seguridad de procesos y llamadas al sistema | **Tetragon** es un proyecto independiente para eventos de runtime y aplicación configurada. Habilitar Hubble no lo instala. |
| Detección y respuesta ante amenazas | Deben configurarse reglas de alerta externas, SIEM/WAF y controladores de respuesta para la detección y acción previstas. |

### Seguridad de red y aplicación

Use una política de mínimo privilegio para limitar el movimiento lateral y egress explícito para limitar las dependencias. Las identidades de seguridad derivan de etiquetas relevantes para la seguridad; no son necesariamente únicas por Pod ni autentican a un usuario final.

La política actual de Cilium admite reglas L7 HTTP y DNS. gRPC puede usar reglas de método/ruta/encabezado HTTP cuando su tráfico HTTP/2 es visible. Las políticas de temas de Kafka ya no son compatibles. Las entradas HTTP `headers` con valores son coincidencias literales, no autenticación mediante expresiones regulares. La presencia o forma de un encabezado `Authorization` no valida un JWT, su emisor, firma ni reclamaciones de autorización. Use para ello la capa de autenticación de la aplicación o un gateway configurado.

Una regla HTTP en el puerto 8443 no descifra HTTPS. Se requiere terminación TLS o una disposición de inspección compatible independiente antes de que la política HTTP pueda evaluar datos de aplicación cifrados. No omita el cifrado de un service mesh solo para hacer funcionar la inspección L7.

### Identidad, autenticación y cifrado

La **autenticación mutua basada en SPIRE** de Cilium es Beta, pero está obsoleta en 1.20 (se eliminó en la pre-release 1.21; las notas de actualización señalan ztunnel como alternativa, por lo que no debe elegirla para diseños nuevos): realiza un handshake fuera de banda para identidades de seguridad. Ese handshake por sí solo no cifra el tráfico de aplicación. Sus limitaciones documentadas incluyen la ausencia de soporte para ClusterMesh y la falta de interoperabilidad con sistemas mTLS externos arbitrarios. La función independiente de **mTLS de workload ztunnel también es Beta**; tiene sus propios requisitos de inscripción y certificados. Ninguna función debe presentarse como la consecuencia automática de un selector de identidad.

### Configuración de cifrado

Los siguientes son **fragmentos Helm alternativos**, no dos ajustes para habilitar juntos. Seleccione uno para una instalación/cambio planificado y valide los requisitos previos de kernel, routing y plataforma.

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

WireGuard requiere soporte del kernel y la ruta UDP de nodo a nodo en el puerto 51871. IPsec requiere un Secret `cilium-ipsec-keys` con el formato correcto y gestionado de forma segura en el namespace de Cilium antes de habilitarlo; siga el procedimiento oficial de creación y rotación de claves. Simplemente nombrar un archivo de clave en un ConfigMap no aprovisiona esa clave ni su volumen.

De forma predeterminada, estos modos protegen el tráfico de Pod gestionado por Cilium compatible que cruza nodos; el tráfico en el mismo nodo no se cifra mediante estos túneles de nodo. El tráfico hacia destinos externos arbitrarios no queda cubierto automáticamente. El cifrado WireGuard de nodo a nodo (`encryption.nodeEncryption`) es una opción Beta independiente, obsoleta en la pre-release 1.21 y cuya eliminación está prevista para 1.22; los nodos de plano de control quedan excluidos de esta extensión de forma predeterminada, mientras que su tráfico de Pod entre nodos gestionado por Cilium aún puede cifrarse. Verifique la ruta real de los paquetes y use TLS de aplicación donde sea necesario. La compatibilidad con firewall de host también depende del modo de cifrado: las políticas de host no funcionan junto con IPsec (documentado en los problemas conocidos de políticas de host de la pre-release 1.21).

## Visibilidad de red con Hubble

Hubble recibe eventos de datapath, proxy y agente, y los enriquece con metadatos de Kubernetes. No es simplemente un lector que sondea periódicamente todos los mapas eBPF.

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

El servidor mantiene un historial limitado en memoria. Relay consulta varios servidores; no es una base de datos duradera. UI ofrece exploración de flujos y mapas de dependencias de servicios, mientras que la CLI admite filtros explícitos. La ausencia de registros coincidentes puede significar que no hubo tráfico, que el filtro es incorrecto, que los peers no están disponibles, que falta visibilidad L7 o que se sobrescribieron/perdieron eventos.

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

`--pod namespace/name` coincide con cualquiera de los endpoints; use `--from-pod`/`--to-pod` para la dirección. Los nombres de Pod no son selectores de etiquetas: use `--from-label` o `--to-label` al seleccionar etiquetas. No combine `--namespace` con `--from-pod`/`--to-pod`; la CLI rechaza esa combinación.

`DROPPED` es un veredicto. `POLICY_DENIED` es un motivo de descarte, seleccionado con `--drop-reason-desc`. Los prefijos de estado HTTP usan `4+` y `5+`, no `4..` y `5..`. Los filtros HTTP requieren eventos L7 derivados del proxy; una conexión TCP descartada no tiene por qué tener un estado HTTP.

## Visibilidad y monitorización de red

### Métricas de Hubble

Los plugins habilitados exponen observaciones distintas:

| Plugin | Métrica de ejemplo | Significado y límite |
| --- | --- | --- |
| `flow` | `hubble_flows_processed_total` | Eventos de flujo procesados por protocolo/tipo/veredicto; no solicitudes únicas ni paquetes en todas las rutas. |
| `drop` | `hubble_drop_total{reason="POLICY_DENIED"}` | Descartes observados; la etiqueta de motivo es el nombre de enum. |
| `tcp` | `hubble_tcp_flags_total` | Flags TCP observados; no es una métrica general de RTT, retransmisión o conexiones simultáneas. |
| `dns` | `hubble_dns_queries_total`, `hubble_dns_responses_total` | Consultas/respuestas DNS y códigos de respuesta observados; no es un histograma genérico de latencia DNS. |
| `httpV2` | `hubble_http_requests_total`, `hubble_http_request_duration_seconds` | Recuentos/estado de solicitudes y duración en segundos derivados de flujos de respuesta HTTP. Requiere visibilidad HTTP. |

No habilite `http` y `httpV2` juntos. Elija cuidadosamente las etiquetas de origen/destino para controlar la cardinalidad, y evite añadir encabezados de solicitud o identidades sensibles sin motivo. Compruebe `hubble_lost_events_total` y la disponibilidad de peers antes de tratar la ausencia de un evento como prueba de que no ocurrió tráfico.

### Integración con Prometheus

El chart crea el Service headless `hubble-metrics` en el namespace de Cilium, que expone de forma predeterminada el puerto **9965**. Su etiqueta de Service `k8s-app=hubble` se usa para el descubrimiento; el Service selecciona Pods de agente con la etiqueta `k8s-app=cilium`. Prometheus debe descubrir los endpoints individuales en lugar de depender de un único destino DNS estático.

Con un Prometheus Operator existente y una CRD ServiceMonitor, fusione este fragmento en los valores de la release. `release: monitoring` es un ejemplo: debe coincidir con su `serviceMonitorSelector` de Prometheus, y su selector de namespace debe incluir el namespace de ServiceMonitor. Un recurso que Prometheus no seleccione no será recolectado.

```yaml
# hubble-servicemonitor-values.yaml
hubble:
  metrics:
    serviceMonitor:
      enabled: true
      labels:
        release: monitoring
```

El ServiceMonitor del chart usa el puerto con nombre `hubble-metrics` y los endpoints del namespace de Cilium. Sin el Operator, configure un descubrimiento de servicios Kubernetes equivalente en su configuración real de Prometheus. Crear un ConfigMap no relacionado no configura Prometheus. `*.hubble-metrics.cilium.io` se usa en la configuración de identidad TLS de métricas; no es un destino de scraping público en el puerto 9091.

Los dashboards de Grafana consultan métricas de Prometheus; el mapa de servicios de Hubble UI consulta Relay. Importe dashboards que coincidan con los plugins y etiquetas habilitados. Los dashboards HTTP estarán vacíos para tráfico cuya carga útil HTTP no sea observable.

### Exportación y retención de flujos

Para archivos rotados locales al nodo, fusione opcionalmente `hubble-export-values.yaml`. La máscara de campos conserva deliberadamente metadatos de red; no exporta encabezados HTTP completos.

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

El exportador estático escribe en cada nodo y rota según sus ajustes de archivo. Organice un colector independiente, controles de acceso y retención de almacenamiento si los eventos deben sobrevivir a la pérdida del nodo. Los cambios de configuración estática requieren el rollout del agente; el exportador dinámico admite un comportamiento de actualización diferente. Los filtros del exportador y las máscaras de campos pueden omitir intencionadamente eventos/campos, y los buffers finitos aún pueden perder observaciones.

## Detección de amenazas en tiempo real

Hubble proporciona evidencia para investigaciones; no incluye un interruptor que lo convierta en un IDS, WAF o sistema de cuarentena automática completo. No hay ajustes de Cilium compatibles llamados `enable-threat-detection`, `enable-anomaly-detection` ni `alert-to-slack`.

Los destinos denegados repetidos pueden sugerir escaneo; un pico de tráfico puede justificar una investigación. Estas observaciones no son prueba de un ataque. Correlaciónelas con registros de autenticación de la aplicación, cambios de workload, eventos de auditoría de API y, donde esté desplegado, eventos de runtime de Tetragon. La inyección SQL, XSS y la inyección de comandos requieren reglas adecuadas de aplicación/WAF/detección; un registro de flujo HTTP normal por sí solo no las clasifica.

Para las alertas, defina y pruebe reglas externas de Prometheus/SIEM frente a tráfico normal, datos ausentes y pérdida de eventos. Los límites de velocidad, el aislamiento mediante firewall y la automatización de respuesta son controles configurados por separado. Limite el alcance de la respuesta y proporcione una ruta de recuperación; no aísle automáticamente cada Pod que registre un paquete descartado.

## Laboratorio: instalación y uso de Hubble

Este laboratorio usa dos **namespaces nuevos e independientes** para que una regla amplia de permiso no pueda invalidar el ejercicio de denegación predeterminada. No crea ninguna base de datos ni API externa. Los comandos son ejemplos para su clúster de prueba; la auditoría de documentación comprobó esquemas y fixtures locales, no un despliegue en vivo.

### 1. Crear y comprobar los workloads

Guarde `visibility-app.yaml`. Las imágenes de cliente y servidor coinciden con los valores predeterminados de prueba versionados de Cilium CLI. La anti-affinity de Backend requiere un segundo nodo programable, lo que hace que la ruta frontend a backend cruce nodos.

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

Ambos clientes de ambos namespaces deben alcanzar el backend antes de aplicar la política. De lo contrario, resuelva primero los problemas de disponibilidad, programación, DNS y red. No infiera una denegación de política a partir de un error curl arbitrario.

### 2. Aplicar y observar la política HTTP

Guarde `backend-http.yaml`. Permite que la identidad `frontend` emita `GET /` a backend TCP 8080. Ninguna regla de ingress amplia debe solaparse con este ejemplo: un permiso L4 puede omitir la restricción L7 prevista.

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

Después de que se materialice la política, espere que `GET /` de frontend tenga éxito y que su `POST /` reciba el HTTP 403 del proxy. La nueva conexión de outsider debe denegarse en L3/L4. Correlacione el momento de la solicitud, los endpoints y el evento de Hubble; errores DNS, contenedores ausentes y errores HTTP no relacionados no constituyen una prueba de denegación correcta. Use Hubble UI para inspeccionar la arista de dependencia generada y los descartes.

Para un backend real que necesita una base de datos y una API externa, la siguiente **política de dependencias opcional** ilustra egress. Este laboratorio no la aplica: `database` y `api.example.com` deben sustituirse por dependencias reales. Primero verifique los endpoints DNS.

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

DNS TCP y UDP están permitidos, y las reglas de proxy DNS permiten a Cilium observar las respuestas usadas por `toFQDNs`. Permitir consultas DNS es distinto de permitir conexiones posteriores a sus IP resueltas. El `*` DNS de esta política permite todos los nombres de consulta; no es una lista de bloqueo de dominios.

### 3. Verificar la denegación predeterminada por separado

Guarde `deny-except-dns.yaml`. Los `policyTypes` explícitos activan el aislamiento en ambas direcciones; `ingress: []` no contiene **ninguna regla de permiso de ingress**. La única excepción de egress permite DNS solamente a los Pods de resolvedor coincidentes.

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

No sustituya la lista de ingress vacía por `ingress: [{}]`: eso es una regla de permiso de ingress total. Los permisos de NetworkPolicy estándar son aditivos, por lo que otra política puede abrir tráfico. Las reglas de denegación de Cilium y las políticas de clúster pueden imponer restricciones adicionales. Este ejercicio de namespace no pretende aislar el tráfico host-network ni todas las rutas originadas por el host.

### 4. Inspeccionar JSON y exportar un resumen local

Guarde lo siguiente como `flow-summary.jq`. `--output jsonpb` proporciona el sobre de respuesta protobuf con `.flow`; esto evita depender del ajuste de compatibilidad `json` heredado de la CLI.

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

El resultado cuenta **registros de flujo en esta muestra finita**, no ataques, conexiones ni todos los paquetes del clúster únicos. Cuenta por separado los registros que no son de flujo; inspecciónelos para obtener información de pérdida/estado. Para un filtro local en vivo:

```bash
hubble observe --namespace cilium-deny-demo --follow --output jsonpb |
  jq --unbuffered -c 'select(.flow.verdict == "DROPPED"
    and .flow.drop_reason_desc == "POLICY_DENIED")'
```

Este pipeline imprime localmente. Las notificaciones requieren una integración configurada por separado, credenciales, política de reintento/deduplicación y gestión de fallos de stream.

### 5. Limpiar los namespaces de prueba

Después de revisar los nombres de namespace, elimine únicamente los workloads y políticas de este laboratorio. La comprobación de propiedad se detiene si falla la búsqueda o hay una etiqueta distinta.

```bash
set -eu
for ns in cilium-security-demo cilium-deny-demo; do
  LAB_OWNER=$(kubectl get namespace "$ns" -o jsonpath='{.metadata.labels.audit-lab}')
  test "$LAB_OWNER" = security-visibility
  kubectl delete namespace "$ns"
done
```

## Referencias principales

- [Aplicación de políticas de Cilium](https://raw.githubusercontent.com/cilium/cilium/v1.20.2/Documentation/security/policy/intro.rst)
- [Kubernetes NetworkPolicy](https://kubernetes.io/docs/concepts/services-networking/network-policies/)
- [Política HTTP](https://raw.githubusercontent.com/cilium/cilium/v1.20.2/Documentation/security/policy/layer7.rst)
- [Política DNS](https://raw.githubusercontent.com/cilium/cilium/v1.20.2/Documentation/security/dns.rst)
- [Configuración de Hubble](https://raw.githubusercontent.com/cilium/cilium/v1.20.2/Documentation/observability/hubble/setup.rst)
- [Métricas](https://raw.githubusercontent.com/cilium/cilium/v1.20.2/Documentation/observability/metrics.rst)
- [Exportador de flujos](https://raw.githubusercontent.com/cilium/cilium/v1.20.2/Documentation/observability/hubble/configuration/export.rst)
- [WireGuard](https://raw.githubusercontent.com/cilium/cilium/v1.20.2/Documentation/security/network/encryption-wireguard.rst)
- [IPsec](https://raw.githubusercontent.com/cilium/cilium/v1.20.2/Documentation/security/network/encryption-ipsec.rst)
- [Autenticación mutua](https://raw.githubusercontent.com/cilium/cilium/v1.20.2/Documentation/network/servicemesh/mutual-authentication/mutual-authentication.rst)
- [ztunnel](https://raw.githubusercontent.com/cilium/cilium/v1.20.2/Documentation/security/network/encryption-ztunnel.rst)
- [Tetragon](https://raw.githubusercontent.com/cilium/tetragon/main/README.md)
- [Filtros de Hubble CLI](https://raw.githubusercontent.com/cilium/hubble/v1.20.2/vendor/github.com/cilium/cilium/hubble/cmd/observe/flows.go)

[Volver a la página principal](README.md)

## Cuestionario

Pruebe los límites de política, cifrado y observabilidad en el [cuestionario del tema](../../quizzes/networking/cilium/06-security-visibility-quiz.md).
