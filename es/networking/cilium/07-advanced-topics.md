# Temas avanzados y casos reales

> **Línea base de revisión**: Cilium 1.20.2, Cilium CLI 0.20.1 y Hubble CLI 1.20.2.
> **Última actualización**: October 15, 2026. El rango de compatibilidad de Kubernetes de Cilium 1.20 es 1.33–1.36; las mediciones históricas siguientes conservan su entorno original.

## Configuración del entorno de laboratorio

Use [los requisitos previos de instalación](README.md) y un clúster de prueba desechable con al menos dos nodos Linux planificables. Mantenga el SO, kernel, configuración de Cilium, topología, MTU, policies, encryption y carga de trabajo de prueba en el registro de resultados. Use kubectl dentro de su desfase de versión de API server compatible. Helm, jq y las CLI de Cilium/Hubble son necesarios para los comandos siguientes; `kubectl top` requiere además una API de métricas.

### Configuración del entorno de pruebas de rendimiento

Registre el Deployment existente antes de modificarlo:

```bash
cilium version
cilium status --verbose
kubectl version
kubectl get nodes -o wide
kubectl -n kube-system get pods -l k8s-app=cilium -o wide
helm get values cilium --namespace kube-system -o yaml > cilium-current-values.yaml
```

La CLI actual puede crear sus propias cargas de trabajo de prueba coincidentes. Ejecute esto solo cuando generar carga de red y crear recursos de prueba sea aceptable:

```bash
cilium connectivity perf --test-namespace cilium-advanced-perf \
  --namespace-labels docs-audit-lab=cilium-advanced-07 \
  --duration 10s --samples 2 --crr --udp \
  --host-net=false --pod-net=true --same-node=true --other-node=true \
  --report-dir ./cilium-advanced-perf-results
```

La ejecución predeterminada de concurrencia única usa **`cilium-advanced-perf-1`**, aunque el argumento no tenga ese sufijo. Asegúrese de que ese namespace no esté en uso antes de la prueba. `--duration` se aplica a cada escenario/muestra, no a la ejecución completa; la planificación, configuración y combinación de casos añaden tiempo. El comando es una prueba activa de carga de trabajo, no un diagnóstico de solo lectura.

Compare resultados en el mismo nodo y entre nodos, request/response TCP y UDP, y el comportamiento real de CPU/memoria/pérdida de paquetes. Repita con un cambio planificado a la vez. Una ejecución satisfactoria no demuestra SLOs de la aplicación, un límite de capacidad de producción ni todas las rutas de policy. La auditoría validó estos contratos de comandos sin ejecutar la prueba ni aprovisionar un clúster.

## Ajuste y solución de problemas de rendimiento

### Arquitectura de ajuste de rendimiento

![Cuatro áreas que investigar para el rendimiento de Cilium: comportamiento del kernel, mapas eBPF, asignación de recursos y la ruta de red seleccionada.](../../.gitbook/assets/en-networking-cilium-07-advanced-topics-0.png)

[Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-networking-cilium-07-advanced-topics-0.html)

La figura agrupa áreas de investigación; no prescribe aumentar cada configuración ni deshabilitar controles de seguridad.

### Áreas de ajuste de rendimiento

| Área | Qué medir y qué controla la configuración |
| --- | --- |
| Backlogs de socket | `net.core.somaxconn` limita el backlog de escucha del socket; `net.ipv4.tcp_max_syn_backlog` se refiere a solicitudes SYN_RECV pendientes por listener. Compruebe el comportamiento de aceptación del servidor y el namespace de red pertinente. |
| Entradas de vecinos | `net.ipv4.neigh.default.gc_thresh1`, `gc_thresh2` y `gc_thresh3` son umbrales distintos de recolección de basura. No existe una única configuración `gc_thresh`. |
| Seguimiento de conexiones | `nf_conntrack_max` de Netfilter y los mapas BPF CT de Cilium son mecanismos independientes. Aumentar el primero no redimensiona el segundo. |
| Mapas BPF | Inspeccione la presión de los mapas, fallos de inserción, rotación y memoria. Los mapas CT, NAT, LB y de policy por endpoint tienen distintos ámbitos y reglas de dimensionamiento. |
| CPU y memoria | Mida agent, operator, Envoy y Hubble por separado. Las requests afectan la planificación; los límites de CPU pueden limitar y los límites de memoria pueden provocar terminación OOM. Aumentar todos los límites no es un diagnóstico. |
| Ruta de red | Identifique routing nativo/en túnel, MTU, masquerading, encryption y reenvío de Service. La aceleración XDP se aplica a rutas y drivers compatibles; no es necesaria para el reemplazo de kube-proxy. |

Mantenga constantes los requisitos de seguridad y routing al comparar el rendimiento. Un resultado más rápido obtenido al eliminar encryption o policy necesarias no es una configuración equivalente.

### Dimensionamiento de mapas

Guarde lo siguiente solo como un **cambio candidato** después de medir la presión. Intégrelo en los valores completos y versionados de la versión; no reemplace todo el ConfigMap de Cilium con un fragmento pequeño.

```yaml
# map-sizing-values.yaml
bpf:
  mapDynamicSizeRatio: 0.005
```

`0.005` es una entrada nominal de **0.5% de la memoria del nodo** para el dimensionamiento dinámico, no 5% ni un límite estricto para toda la memoria de Cilium. Por ejemplo, 32 GiB × 0.005 son 163.84 MiB antes de los límites de mapas, redondeo y otras asignaciones. Los mapas grandes afectados incluyen los mapas CT, NAT, neighbor y socket reverse-NAT; otros mapas y la memoria de userspace permanecen separados.

Los valores explícitos `bpf.ctTcpMax`, `bpf.ctAnyMax` o `bpf.natMax` anulan el dimensionamiento dinámico para esos mapas. Mantenga la capacidad NAT compatible con la capacidad CT y verifique los tamaños resueltos al inicio. Aumentar los mapas puede consumir más memoria; reemplazar mapas puede interrumpir conexiones existentes.

LRU distribuido (`bpf.distributedLRU.enabled`) usa pools por CPU para reducir la contención, con compensaciones de memoria/expulsión. Requiere dimensionamiento dinámico y recrea mapas al habilitarse. El perfil oficial de alto rendimiento no es una opción universal para activar en vivo: introduzca dichos cambios de datapath en nodos nuevos preparados o use el procedimiento de migración documentado.

Los antiguos ejemplos `proxy-max-memory-percentage`, `proxy-max-threads`, `enable-xdp`, `tunnel: disabled` y `kube-proxy-replacement: strict` no son recetas actuales de configuración. Use configuraciones de chart compatibles, como `envoy.resources`, `routingMode`, el booleano `kubeProxyReplacement` y `loadBalancer.acceleration`, junto con sus requisitos previos.

### Coste de Hubble y pérdida de eventos

Una cola de eventos más grande puede absorber una ráfaga, pero usa memoria y no resuelve un déficit sostenido de procesamiento ni reduce el consumo de CPU:

```yaml
# hubble-queue-values.yaml
hubble:
  eventQueueSize: 32768
```

Si los eventos de trace repetidos dominan el procesamiento, evalúe por separado un intervalo de agregación más largo:

```yaml
# hubble-aggregation-values.yaml
bpf:
  monitorAggregation: medium
  monitorInterval: 10s
```

El campo real de chart es **`bpf.monitorInterval`**, no `bpf.events.monitorInterval`. Inspeccione el `monitor-aggregation-interval` renderizado antes del Deployment. El aumento de la agregación, los límites de tasa de eventos y las clases de eventos deshabilitadas reducen las observaciones disponibles para monitor, métricas de Hubble y exportación. Un evento de Hubble perdido no es en sí un paquete de aplicación descartado; compruebe tanto la pérdida de observabilidad como los descartes de datapath.

### Requisitos previos de datapath avanzado

| Funcionalidad | Requisitos previos y límites que comprobar |
| --- | --- |
| netkit | Beta en esta línea base; Linux 6.8+ y BPF host routing. Los Pods veth existentes no pueden simplemente cambiar de tipo de dispositivo al reiniciar el agent. |
| BIG TCP | Requisitos de kernel/NIC específicos de la familia; el perfil de ajuste combinado requiere Linux 6.8+ y NIC compatibles. No es un aumento genérico de MTU. |
| BPF host routing | Requiere reemplazo de kube-proxy compatible y BPF masquerading. Omite los hooks de Netfilter del host; compruebe Istio y otras integraciones que dependen de esos hooks. |
| Aceleración de Service XDP | Dispositivos compatibles con XDP nativo y una ruta de reenvío de Service externa compatible. Use la guía de driver/plataforma y verifique el estado en ejecución. |
| Bandwidth Manager | El egress por Pod usa EDT; el ingress usa un token bucket eBPF. `10M` en la anotación de ancho de banda significa 10 Mbit/s, no 10 MB/s. |
| BBR para Pods | Bandwidth Manager, Linux 5.18+ y BPF host routing; los Pods creados recientemente adoptan la configuración. BBR solo para host es una opción independiente. |

La aplicación de ancho de banda tiene limitaciones documentadas con policies L7 de Cilium de egress y namespaces de red anidados como kind. Estas condiciones difieren de los requisitos ordinarios de instalación de Cilium. No use un perfil de ajuste como evidencia de que todas las combinaciones de service mesh, nube o kernel funcionan.

### Comandos de solución de problemas dirigidos

Use la CLI independiente `cilium` para operaciones de clúster y **`cilium-dbg` dentro del agent pertinente** para endpoints, policies y mapas locales. Seleccione el nodo investigado en lugar de consultar arbitrariamente el primer agent:

```bash
set -euo pipefail
: "${NODE_NAME:?Set NODE_NAME to the node being investigated}"
CILIUM_POD=$(kubectl -n kube-system get pods -l k8s-app=cilium \
  --field-selector "spec.nodeName=$NODE_NAME,status.phase=Running" -o json |
  jq -er 'if (.items | length) == 1
then .items[0].metadata.name
else error("expected exactly one running Cilium Pod on the selected node")
end')
kubectl -n kube-system exec "$CILIUM_POD" -c cilium-agent -- cilium-dbg status --verbose
kubectl -n kube-system exec "$CILIUM_POD" -c cilium-agent -- cilium-dbg endpoint list
kubectl -n kube-system exec "$CILIUM_POD" -c cilium-agent -- cilium-dbg policy get
kubectl -n kube-system exec "$CILIUM_POD" -c cilium-agent -- cilium-dbg policy selectors
kubectl -n kube-system exec "$CILIUM_POD" -c cilium-agent -- cilium-dbg map list
kubectl -n kube-system exec "$CILIUM_POD" -c cilium-agent -- cilium-dbg bpf metrics list
kubectl -n kube-system logs "$CILIUM_POD" -c cilium-agent --since=10m --tail=200
```

Los ID de endpoint son locales a ese agent. Use un ID de su lista de endpoints:

```bash
: "${CILIUM_POD:?Select the owning Cilium Pod first}"
: "${ENDPOINT_ID:?Read the endpoint ID from the selected agent endpoint list}"
kubectl -n kube-system exec "$CILIUM_POD" -c cilium-agent -- \
  cilium-dbg endpoint get "$ENDPOINT_ID"
# Stream local BPF drop events; stop with Ctrl-C.
kubectl -n kube-system exec "$CILIUM_POD" -c cilium-agent -- \
  cilium-dbg monitor --type drop
```

`cilium-dbg map list` enumera los mapas abiertos que el gestor de mapas del agent conoce; no es un inventario de todos los mapas BPF del kernel. `cilium-dbg monitor` muestra eventos BPF emitidos y traces capturados opcionales, no un tcpdump sin pérdidas de cada paquete. Los volcados de mapas CT grandes pueden ser costosos; inspeccione las métricas y el nodo afectado antes de ejecutar `cilium-dbg bpf ct list global`.

Para Hubble, establezca primero la conexión local de Relay descrita en [Seguridad y visibilidad](06-security-visibility.md):

```bash
hubble status
hubble observe --protocol tcp --verdict DROPPED --since 1h
hubble observe --protocol dns --from-label k8s:app=frontend --last 100
hubble observe --http-status '5+' --from-namespace production --last 100
```

`--type` selecciona tipos de eventos, no el tipo A de registro DNS. Use los campos de flujo DNS si necesita distinguir tipos de consulta. Los filtros de estado HTTP usan `5+`, no `5xx`. El historial retenido y la disponibilidad de eventos limitan `--since 1h`; no puede recuperar una hora de eventos sobrescritos.

### Escenarios comunes de solución de problemas

| Síntoma | Evidencia que recopilar | Próxima decisión |
| --- | --- | --- |
| Presión CT/NAT | Presión de mapas, motivos de inserción/descarte, rotación de conexiones, tamaños configurados reales | Investigue la rotación/los timeouts y el margen de memoria antes de redimensionar. |
| Saturación de OOM o CPU | Motivo de terminación del contenedor, historial de memoria/CPU, throttling, carga de proxy y Hubble | Identifique el componente responsable y cambie su presupuesto o carga de trabajo. |
| Resultado inesperado de policy | Namespace/labels correctos, revisión de policy del endpoint, errores de proxy y veredicto de Hubble | Compruebe dirección, reglas allow aditivas y precedencia de deny; los allow ordinarios no son una lista de firewall ordenada por prioridad. |
| Fallo entre nodos | DNS, rutas de nodo/Pod, MTU, puertos de túnel/encryption y firewall de plataforma | Verifique rutas de ida y vuelta; una sesión BGP por sí sola no demuestra la accesibilidad del datapath. |
| Regresión de actualización | Valores antiguos/nuevos, notas de versión, versiones de todos los componentes, reconexiones de proxy | Use la ruta de rollback compatible preparada e investigue la compatibilidad de funcionalidades. |

## Estrategias de despliegue a gran escala

La planificación de capacidad debe incluir densidad de nodo/Pod, Services y backends, identidades, expansión de policies, tráfico de observación de API, asignación de IPAM y volumen de flujos. El número de objetos de una policy por sí solo no determina su coste de mapas por endpoint.

### Arquitectura de despliegue a gran escala

```text
Management / GitOps / shared monitoring
          | config and collected telemetry
          +-----------------------+
          v                       v
  Workload cluster A       Workload cluster B
  - Cilium Operator        - Cilium Operator
  - agent on each node     - agent on each node
  - local Hubble servers   - local Hubble servers
  - Relay/export setup     - Relay/export setup
          |                       |
          +--- optional ClusterMesh metadata/data paths
```

Un clúster central de management no reemplaza al operator en cada clúster administrado. Dimensione el operator y los agents de cada clúster; las réplicas del operator y la anti-affinity del chart necesitan suficientes nodos elegibles. Agregue métricas/logs mediante collectors configurados. ClusterMesh requiere su propio diseño de direccionamiento, identidad, trust y accesibilidad; no replica automáticamente todos los recursos de policy.

`ciliumEndpointSlice.enabled` es una funcionalidad Cilium opt-in, distinta de Kubernetes EndpointSlice. No es el antiguo flag de ConfigMap `enable-endpoint-slice`. Evalúe la compatibilidad de la versión y la funcionalidad antes de habilitarla; Egress Gateway actualmente no se puede combinar con CiliumEndpointSlice ni ClusterMesh.

Egress Gateway aplica **SNAT** al tráfico seleccionado hacia una dirección de gateway predecible; no conserva la dirección de origen del Pod original. Las interfaces/IP de gateway y el routing ya deben estar aprovisionados, incluidos los requisitos específicos de plataforma en AWS. Requiere BPF masquerading, reemplazo de kube-proxy y asignación de identidad CRD. Los Pods recién iniciados pueden enviar tráfico brevemente antes de que la policy de egress tenga efecto; no lo trate como una garantía inmediata de IP de origen fail-closed.

### Despliegue y recuperación

Mantenga los valores deseados, policies, definiciones de address-pool y el material de trust/key necesario bajo controles adecuados de versionado y backup. Ensaye la recuperación; un backup de ConfigMap no es un plan completo de recuperación de IPAM o criptografía.

Para actualizaciones minor, primero alcance el último patch de la minor actual, ejecute el preflight requerido y, luego, avance **una minor a la vez**. Preserve `upgradeCompatibility` inicial según las instrucciones de la guía de actualización y migre valores renombrados/eliminados. No use `--reuse-values` entre versiones minor. Los agents, operator y otros componentes de Cilium deben converger en la misma versión.

El tráfico a través de proxies de userspace puede reconectarse durante las actualizaciones; los eventos de monitoring almacenados en búfer pueden perderse. Las nuevas funcionalidades/recursos pueden necesitar eliminación o migración antes de que un rollback sea válido. Un Deployment blue/green de aplicación genérico o un rollback de Helm no es garantía de una migración de CNI reversible y sin tiempo de inactividad.

## Estudios de casos de uso reales

### Un experimento histórico de escalabilidad documentado

El informe oficial de escalabilidad describe **1,000 nodos worker**, tres nodos controller y kernel **5.4.0-1009-gcp** en Google Cloud. Su configuración no identifica una versión de Cilium, por lo que estos resultados no deben volver a etiquetarse como un benchmark de Cilium 1.20.2. El informe analiza el consumo de recursos y la convergencia bajo su propia carga de trabajo; no es una matriz de compatibilidad actual ni una promesa de capacidad.

Sus cambios de health-check y alta concurrencia de despliegue fueron elecciones experimentales. Preserve las condiciones reales de prueba al citarlo y valide por separado una configuración operativa.

### Escenario de diseño 1: comercio electrónico a gran escala

Para muchos Services y un volumen alto de solicitudes, evalúe el reenvío de Service eBPF, policy de identidad/L7, Hubble y ClusterMesh opcional. Mida latencia p95/p99, throughput, errores, CPU por solicitud y convergencia de policy bajo la misma topología y requisitos de protección. Ninguna implementación nombrada o mediciones reproducibles respaldan aquí una mejora porcentual universal.

### Escenario de diseño 2: servicios financieros

Combine policy de mínimo privilegio, encryption de transporte/aplicación con ámbito adecuado y exportación de flujos controlada con registros de auditoría de aplicación/API. Pruebe la rotación de keys, pérdida de eventos, retención y trust entre clústeres. Los flujos de Hubble por sí solos no constituyen evidencia de auditoría regulatoria completa ni garantizan una auditoría más corta.

### Escenario de diseño 3: telecomunicaciones y edge

Evalúe la compatibilidad de NIC/driver, planificación de CPU, rutas de reenvío de Service, tamaños de paquete, pérdida y latencia bajo tráfico realista. XDP puede beneficiar a una ruta de reenvío que cumpla los requisitos. Por sí solo no implementa una función de plano de usuario 5G ni demuestra una tasa fija de paquetes por segundo en hardware arbitrario. Los sitios remotos aún requieren un underlay y pruebas explícitas de fallo/recuperación.

## Hoja de ruta futura y dirección de desarrollo

La hoja de ruta de la comunidad no asume explícitamente **ningún compromiso de fechas**. Siga las notas de versión, diseños aceptados y issues para una capacidad específica en vez de tratar una lista de integraciones deseadas como una promesa de entrega.

| Área | Preguntas que investigar |
| --- | --- |
| eBPF y kernels | ¿Qué funcionalidad de kernel, backport, NIC y arquitectura requiere la ruta propuesta? CO-RE no proporciona capacidades de kernel ausentes. |
| Networking e IPv6 | ¿Qué combinaciones de IPAM, routing, policy e integración externa son compatibles con la versión seleccionada? |
| Seguridad y observabilidad | ¿Es esta una network policy de Cilium, autenticación/encryption de carga de trabajo Beta, enforcement de runtime de Tetragon, o un sistema externo de detector/almacenamiento? |
| Nube, mesh y serverless | ¿Permite la plataforma administrada los hooks CNI/host previstos? ¿Se preservan la interceptación y autenticación de mesh? |
| Edge, IoT, 5G y AI/ML | ¿Qué integración adicional de dispositivo, transporte, runtime o acelerador se requiere? Un CNI de Kubernetes no establece todas las capacidades específicas de la aplicación. |

Participe mediante issues del proyecto, propuestas de diseño, documentación y discusiones de la comunidad. El soporte comercial y las distribuciones administradas tienen sus propios contratos de funcionalidad/soporte.

## Configuración BGP actual

El ejemplo anterior de `CiliumBGPPeeringPolicy` es obsoleto para esta línea base. La configuración actual separa la selección de clúster/nodo, configuración de peer y prefijos anunciados en tres recursos **`cilium.io/v2`**. Para BGP Control Plane, anuncio de IP de LoadBalancer, Egress Gateway y patrones edge en profundidad, consulte [BGP, LB, egress y edge](11-bgp-lb-egress-edge.md); para multiclúster, consulte [Instalación y actualización de ClusterMesh](13-clustermesh-install-upgrade.md).

Este es un modelo de configuración para un laboratorio de routing aislado, no una configuración completa de router en la nube. Supone IPAM de ámbito host de cluster-pool o Kubernetes para anuncios `PodCIDR`, un router peer accesible, la configuración de router correspondiente y nodos etiquetados intencionalmente con `cilium-bgp=lab`. `192.0.2.1` es una dirección de documentación; sustitúyala por la IP real del peer, sin `/32`. IPAM multi-pool usa un tipo de anuncio y selección de pool diferentes.

```yaml
# bgp-values.yaml
bgpControlPlane:
  enabled: true
```
```yaml
# bgp-lab.yaml
apiVersion: cilium.io/v2
kind: CiliumBGPClusterConfig
metadata:
  name: lab-bgp
spec:
  nodeSelector:
    matchLabels:
      cilium-bgp: lab
  bgpInstances:
  - name: asn-64512
    localASN: 64512
    peers:
    - name: router-64513
      peerASN: 64513
      peerAddress: 192.0.2.1
      peerConfigRef:
        name: lab-peer
---
apiVersion: cilium.io/v2
kind: CiliumBGPPeerConfig
metadata:
  name: lab-peer
spec:
  timers:
    connectRetryTimeSeconds: 120
    holdTimeSeconds: 90
    keepAliveTimeSeconds: 30
  gracefulRestart:
    enabled: true
    restartTimeSeconds: 120
  families:
  - afi: ipv4
    safi: unicast
    advertisements:
      matchLabels:
        advertise: lab
---
apiVersion: cilium.io/v2
kind: CiliumBGPAdvertisement
metadata:
  name: lab-pod-cidrs
  labels:
    advertise: lab
spec:
  advertisements:
  - advertisementType: PodCIDR
```

El selector de anuncio del peer coincide con `advertise: lab`, y `peerConfigRef` se resuelve en `lab-peer`. Graceful Restart requiere comportamiento de peer compatible y timers apropiados; no puede conservar un datapath fallido ni garantizar la disponibilidad de la aplicación. BGP anuncia accesibilidad, pero **no instala las rutas de datapath locales** ni crea registros DNS.

Después de preparar y aplicar una configuración adecuada en su laboratorio de routing, inspeccione tanto el estado de Cilium como las rutas recibidas por el router externo:

```bash
kubectl get ciliumbgpclusterconfigs,ciliumbgppeerconfigs,ciliumbgpadvertisements
cilium bgp peers
cilium bgp routes advertised ipv4 unicast
```

Pruebe el tráfico real de ida/vuelta por separado. No describa policy HTTP existente desde hace tiempo o ganancias porcentuales arbitrarias como funcionalidades nuevas de una versión antigua. Consulte las notas de versión exactas al migrar desde Cilium 1.18 u otra minor anterior.

## Próximos pasos

Use los capítulos [IPAM y policy](04-ipam-policy.md), [networking L2–L7](05-l2-l7-networking.md) y [seguridad/visibilidad](06-security-visibility.md) para validar rutas individuales. Mantenga las condiciones y limitaciones del benchmark junto con cada resultado; después, ensaye un despliegue y recuperación por etapas.

Después de revisar el namespace exacto creado por la prueba de rendimiento, elimine sus recursos:

```bash
set -eu
PERF_NS=cilium-advanced-perf-1
LAB_OWNER=$(kubectl get namespace "$PERF_NS" -o jsonpath='{.metadata.labels.docs-audit-lab}')
test "$LAB_OWNER" = cilium-advanced-07
kubectl delete namespace "$PERF_NS"
```

## Referencias principales

- [Guía de ajuste](https://raw.githubusercontent.com/cilium/cilium/v1.20.2/Documentation/operations/performance/tuning.rst)
- [Valores de chart](https://raw.githubusercontent.com/cilium/cilium/v1.20.2/install/kubernetes/cilium/values.yaml)
- [Plantilla de ConfigMap de chart](https://raw.githubusercontent.com/cilium/cilium/v1.20.2/install/kubernetes/cilium/templates/cilium-configmap.yaml)
- [Dimensionamiento de mapas](https://raw.githubusercontent.com/cilium/cilium/v1.20.2/Documentation/network/ebpf/maps.rst)
- [Implementación de dimensionamiento de mapas](https://raw.githubusercontent.com/cilium/cilium/v1.20.2/pkg/option/config.go)
- [Guía de actualización](https://raw.githubusercontent.com/cilium/cilium/v1.20.2/Documentation/operations/upgrade.rst)
- [Limitaciones de actualización](https://raw.githubusercontent.com/cilium/cilium/v1.20.2/Documentation/operations/upgrade-warning.rst)
- [Configuración BGP](https://raw.githubusercontent.com/cilium/cilium/v1.20.2/Documentation/network/bgp-control-plane/bgp-control-plane-configuration.rst)
- [Operación BGP](https://raw.githubusercontent.com/cilium/cilium/v1.20.2/Documentation/network/bgp-control-plane/bgp-control-plane-operation.rst)
- [Bandwidth Manager](https://raw.githubusercontent.com/cilium/cilium/v1.20.2/Documentation/network/kubernetes/bandwidth-manager.rst)
- [Egress Gateway](https://raw.githubusercontent.com/cilium/cilium/v1.20.2/Documentation/network/egress-gateway/egress-gateway.rst)
- [Informe histórico de escalabilidad](https://raw.githubusercontent.com/cilium/cilium/v1.20.2/Documentation/operations/performance/scalability/report.rst)
- [Hoja de ruta de la comunidad](https://raw.githubusercontent.com/cilium/cilium/v1.20.2/Documentation/community/roadmap.rst)
- [sysctls IP de Linux](https://www.kernel.org/doc/html/latest/networking/ip-sysctl.html)

[Volver a la página principal](README.md)

## Cuestionario

Revise los límites operativos y comandos de diagnóstico en el [cuestionario del tema](../../quizzes/networking/cilium/07-advanced-topics-quiz.md).