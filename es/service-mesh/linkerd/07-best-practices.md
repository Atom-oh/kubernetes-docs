# Buenas prácticas de Linkerd

> **Última actualización**: 11 de septiembre de 2026 · Linkerd edge-26.9.1 / charts 2026.9.1

Utilice las guías de [instalación](01-installation.md), [seguridad](04-security.md), [observabilidad](05-observability.md) y [múltiples clústeres](06-multi-cluster.md) para las versiones y los requisitos previos seleccionados. Este capítulo conecta esos procedimientos en una revisión operativa; no certifica que un entorno esté listo para producción.

Seleccione y verifique el contexto de Kubernetes, el endpoint de la API y el responsable de gestión de los recursos previstos antes de realizar cualquier cambio. Los comandos siguientes utilizan el contexto actual y nombres de ejemplo de namespaces y cargas de trabajo. En esta auditoría no se realizó ninguna actualización, reversión, migración ni prueba de carga en un entorno activo.

## Revisión de preparación

- [ ] Verifique la compatibilidad de Kubernetes/Linkerd/Gateway API y las notas de versión de la distribución elegida.
- [ ] Confirme las réplicas reales, su ubicación, la capacidad, el comportamiento ante interrupciones y la política de admisión.
- [ ] Distinga las vidas útiles de los certificados raíz, del emisor y de las cargas de trabajo; verifique sus procedimientos de renovación y recuperación.
- [ ] Pruebe el comportamiento de identidad y autorización requerido, incluidos los clientes denegados y las vías ajenas a la malla.
- [ ] Confirme los requisitos de métricas, registros y trazas, la entrega de alertas y la detección de datos ausentes.
- [ ] Registre la responsabilidad de gestión de los recursos, las copias de seguridad protegidas, los pasos de actualización y recuperación específicos de cada versión y la responsabilidad operativa.

Se requiere confianza compartida para las relaciones previstas entre mallas vinculadas, no para todos los clústeres no relacionados. Los ServiceProfiles no son un requisito universal de preparación: las políticas actuales de Gateway API y los perfiles de compatibilidad tienen funciones y precedencia diferentes.

```bash
linkerd version
linkerd check
linkerd check --proxy
kubectl -n linkerd get deployments,pods,poddisruptionbudgets
kubectl -n my-app get pods -o wide
```

Conserve la salida completa de la comprobación y su estado de salida. Un grep de «valid» puede coincidir con «invalid» y ocultar un comando fallido detrás del estado de salida exitoso de grep:

```bash
#!/usr/bin/env bash
set -euo pipefail
umask 077
if linkerd check --proxy > linkerd-check.log 2>&1; then
  cat linkerd-check.log
else
  check_status=$?
  cat linkerd-check.log >&2
  exit "$check_status"
fi
```

Revise las advertencias incluso cuando el comando termine correctamente. Una comprobación del plano de control con resultado sano no demuestra el cumplimiento del SLO de la aplicación ni su comportamiento de conmutación por error regional.

## Asignación de recursos

Dimensione a partir del comportamiento medido de la carga de trabajo: concurrencia de solicitudes y conexiones, protocolo, tamaño de cargas útiles y flujos, tamaño del conjunto de descubrimiento, cardinalidad de la telemetría, presión de memoria y limitación de CPU. Las RPS por sí solas no determinan los recursos del proxy.

Esta es una **configuración inicial ilustrativa**, no una garantía de capacidad:

```yaml
proxy:
  resources:
    cpu:
      request: 100m
      limit: 1000m
    memory:
      request: 64Mi
      limit: 250Mi
```

Use un único mapa YAML coherente. Repetir `proxy:` tres veces en el mismo mapa no es válido; los cargadores permisivos pueden conservar silenciosamente solo el último perfil.

Para una carga de trabajo existente, guarde este **parche de combinación** como `proxy-resources-patch.yaml`:

```yaml
spec:
  template:
    metadata:
      annotations:
        config.linkerd.io/proxy-cpu-request: 500m
        config.linkerd.io/proxy-cpu-limit: 2000m
        config.linkerd.io/proxy-memory-request: 128Mi
        config.linkerd.io/proxy-memory-limit: 500Mi
```

```bash
# A merge patch for one existing, reviewed workload; this starts a rollout.
kubectl -n my-app patch deployment/api --type merge --patch-file proxy-resources-patch.yaml
kubectl -n my-app rollout status deployment/api --timeout=5m
kubectl -n my-app top pod --containers
```

`kubectl top pod --containers` solicita datos por contenedor; no existe un filtro `-c linkerd-proxy` para ese comando. Confirme que la canalización de métricas informa sobre el sidecar nativo de inicialización según lo esperado. Utilice conjuntamente spec/status del Pod y las métricas de recursos en lugar de inferir su ausencia a partir de una sola vista.

### Hilos de ejecución frente a cuota de CPU

Las solicitudes y los límites de CPU configuran la planificación y la asignación de CPU. Un límite de 4 no solicita directamente cuatro hilos de trabajo del proxy. El chart seleccionado tiene límites independientes para los hilos de ejecución:

```yaml
proxy:
  runtime:
    workers:
      minimum: 1
      maximum: 4
      maximumCPURatio: 1
```

Este es un extracto independiente de valores; combine sus campos anidados en lugar de duplicar una clave YAML de nivel superior. El chart publicado emite ajustes de mínimo, máximo y proporción de CPU de los hilos por separado de los límites de CPU de Kubernetes. El comportamiento en ejecución también depende de la CPU disponible y de la demanda; aumentar un límite por sí solo no mejora el rendimiento. La antigua configuración fija `proxy.cores` está obsoleta en la plantilla.

## Alta disponibilidad

### Plano de control principal

Empiece con el **perfil de alta disponibilidad de la misma versión del chart** y combínelo con los valores revisados de la instalación, incluida su configuración de certificados:

```bash
set -euo pipefail
umask 077
# Use the same reviewed chart version for the profile and render.
curl --fail --show-error --location \
  https://raw.githubusercontent.com/linkerd/linkerd2/edge-26.9.1/charts/linkerd-control-plane/values-ha.yaml \
  -o values-ha.yaml
helm template linkerd-control-plane linkerd-edge/linkerd-control-plane \
  --version 2026.9.1 -n linkerd \
  -f reviewed-core-values.yaml -f values-ha.yaml > reviewed-ha.yaml
```

El perfil incluido configura tres réplicas de controlador, tres PDBs del plano de control, antiafinidad obligatoria entre nodos por componente, separación preferida entre zonas e inyección que deniega en caso de fallo. También proporciona recursos y ajustes de despliegue. Confirme los objetos Deployment/PDB/webhook renderizados y los nodos aptos reales. Los archivos de valores se combinan en orden, por lo que el perfil de alta disponibilidad puede anular ajustes de recursos anteriores; inspeccione el resultado final y conserve los controles esenciales de alta disponibilidad al añadir modificaciones adicionales.

Este chart ignoraba los anteriores ejemplos anidados `destination.replicas/resources`, `identity.replicas/resources` y `proxyInjector.replicas/resources`. Los valores compatibles para recursos de controladores incluyen `destinationResources`, `identityResources`, `proxyInjectorResources` y los demás campos del perfil incluido. Las claves arbitrarias `podAntiAffinity`, `topologySpreadConstraints` o `podDisruptionBudget` no se convierten automáticamente en campos de Pod.

Tres réplicas no garantizan un cuórum. Los requisitos de ubicación pueden dejar réplicas en estado Pending si hay demasiado pocos nodos adecuados; las reglas de preferencia de zona no garantizan una réplica por zona. Los PDBs limitan los desalojos voluntarios compatibles, no todas las interrupciones ni todos los despliegues dirigidos por controladores.

### Disponibilidad de Viz y de las métricas

Para un endpoint de Prometheus y consultas preparado por separado con la retención, la autenticación y el comportamiento de alta disponibilidad previstos, estos valores escalan los componentes sin estado de Viz:

```yaml
prometheus:
  enabled: false
prometheusUrl: http://prometheus.monitoring.svc.cluster.local:9090
tap:
  replicas: 2
metricsAPI:
  replicas: 2
tapInjector:
  replicas: 2
dashboard:
  replicas: 2
```

Los recuentos de réplicas por sí solos no establecen separación entre dominios de fallo, protección ante interrupciones ni disponibilidad de métricas. Verifique la ubicación real y la arquitectura externa de consultas, incluida cualquier deduplicación de réplicas.

Como alternativa, un **único Prometheus local** puede persistir sus datos:

```yaml
prometheus:
  enabled: true
  persistence:
    accessMode: ReadWriteOnce
    size: 50Gi
```

Esto necesita una StorageClass predeterminada operativa o el ajuste explícito adecuado de clase de almacenamiento del chart. El chart de Viz seleccionado mantiene Prometheus en una réplica y utiliza una estrategia Recreate con su PVC. El antiguo `prometheus.replicas:2` se ignoraba, y `persistence.enabled:true` sin un accessMode producía un PVC no válido. La persistencia ayuda a que los datos sobrevivan a los reinicios; no proporciona alta disponibilidad de Prometheus.

## Actualización y recuperación

### Seleccionar la vía antes de cambiar de versión

Los artefactos públicos de Linkerd utilizan el canal edge; la distribución estable de un proveedor puede tener instrucciones de actualización compatibles diferentes. El instalador público no es un instalador genérico de versiones estables ni de degradaciones de versión. Obtenga y verifique la CLI seleccionada como se describe en la guía de instalación.

Los números de versión edge no garantizan la compatibilidad propia del versionado semántico. Revise los cambios específicos de la versión y el desfase permitido entre los planos de control y de datos, utilizando versiones intermedias cuando sea necesario. `check --pre` es una comprobación previa a la instalación, no una prueba de aptitud para actualizar una malla existente.

Haga copias de seguridad de los valores deseados y de las credenciales necesarias a través de sus responsables de gestión, proteja el material de claves almacenado y pruebe la restauración. `helm get values` puede exponer material del emisor; no publique su salida. Prepare valores de destino revisados en lugar de aplicar ciegamente a un nuevo chart antiguos valores predeterminados calculados.

### Instalación gestionada por la CLI

Después de aprobar una vía compatible y conservar la configuración y las credenciales actuales:

```bash
set -euo pipefail
# The selected, verified target CLI must already be on PATH.
linkerd version --client
linkerd check
linkerd check --proxy
linkerd upgrade --crds | kubectl apply -f -
linkerd upgrade | kubectl apply -f -
linkerd check
# CLI-owned Viz only; preserve its complete reviewed configuration.
linkerd viz install -f reviewed-viz-values.yaml | kubectl apply -f -
linkerd viz check
```

Actualice los CRDs antes del núcleo, luego las extensiones compatibles y después los proxies de las cargas de trabajo. La CLI actual de extensiones utiliza `install` con la configuración completa; `linkerd viz upgrade` no existe. Revise las instrucciones de eliminación de recursos obsoletos y migración específicas de la versión e inspeccione los recursos candidatos a estar obsoletos antes de eliminar nada.

Para múltiples clústeres, conserve la lista deseada de Helm `controllers` y la responsabilidad de gestión actual de Link y credenciales de la guía de múltiples clústeres. No vuelva a crear los controladores heredados obsoletos gestionados por vínculos como paso automático de actualización.

### Instalación gestionada por Helm

La versión de destino del ejemplo siguiente es 2026.9.1; solo puede utilizarse después de verificar la vía desde la versión realmente instalada:

```bash
set -euo pipefail
umask 077
helm get values linkerd-control-plane -n linkerd > current-core-values.yaml
helm get values linkerd-viz -n linkerd-viz > current-viz-values.yaml
# Prepare reviewed target values and approved migration steps before these changes.
helm upgrade linkerd-crds linkerd-edge/linkerd-crds \
  --version 2026.9.1 -n linkerd --wait --timeout 10m
helm upgrade linkerd-control-plane linkerd-edge/linkerd-control-plane \
  --version 2026.9.1 -n linkerd -f reviewed-core-values.yaml \
  --wait --timeout 10m
linkerd check
helm upgrade linkerd-viz linkerd-edge/linkerd-viz \
  --version 2026.9.1 -n linkerd-viz -f reviewed-viz-values.yaml \
  --wait --timeout 10m
linkerd viz check
```

Mantenga los CRDs, el núcleo, CNI y las extensiones bajo sus responsables de gestión establecidos. No mezcle un flujo de aplicación mediante CLI con una instalación gestionada por Helm solo porque los manifiestos parezcan similares.

### Despliegue de cargas de trabajo

Seleccione los controladores reales de las cargas de trabajo de la malla, incluidos los StatefulSets, DaemonSets y trabajos pertinentes, y coordine su comportamiento de despliegue específico de la aplicación. Un bucle que abarque todo el namespace reinicia cargas de trabajo no relacionadas, y una espera fija de 30 segundos no es una prueba de estabilización.

```bash
# One explicitly selected meshed Deployment, after checking disruption/capacity.
kubectl -n my-app rollout restart deployment/api
kubectl -n my-app rollout status deployment/api --timeout=5m
linkerd check --proxy -n my-app
linkerd viz stat deployment/api -n my-app
```

Verifique la disponibilidad, la identidad y las políticas, y tráfico representativo de la aplicación antes de continuar con otra carga de trabajo. Las anotaciones del namespace afectan a los Pods nuevos; no actualizan los sidecars en ejecución en el sitio.

### Recuperación y múltiples planos de control

Defina un plan de recuperación probado para las versiones y los CRDs específicos. Revertir únicamente una instalación principal de Helm no revierte también los CRDs gestionados por separado, todos los cambios de credenciales ni los proxies de cargas de trabajo que ya estén en ejecución. Descargar una CLI antigua arbitraria y ejecutar upgrade no es un procedimiento universal para volver a una versión anterior.

El antiguo ejemplo «azul-verde» instalaba un segundo namespace y cambiaba `proxy-version`. Esa anotación selecciona una imagen del proxy, no un plano de control. Los renderizados predeterminados del chart para ambos namespaces también comparten nombres con alcance de clúster, incluidos los webhooks de admisión. Por tanto, un segundo namespace no establece coexistencia aislada ni migración segura de cargas de trabajo. Use un diseño compatible con la distribución, con responsabilidad explícita de gestión de recursos y selección de tráfico e identidad, y conserve la capacidad de recuperación hasta que se verifique.


## Incorporación y tratamiento de protocolos

Incorporación por namespace para Pods nuevos:

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: my-app
  annotations:
    linkerd.io/inject: enabled
```

La exclusión de una carga de trabajo existente es un parche de combinación de la plantilla del Pod, no un Deployment completo:

```yaml
spec:
  template:
    metadata:
      annotations:
        linkerd.io/inject: disabled
```

Cambiar únicamente las anotaciones no elimina un proxy en ejecución ni uno incrustado manualmente. Reconcilie los manifiestos reales de la carga de trabajo y vuelva a crearla mediante su responsable de gestión cuando corresponda. Inspeccione tanto `containers` como `initContainers`; los sidecars nativos no están ausentes solo porque la lista de contenedores normales no los muestre.

Los puertos opacos omiten la detección del protocolo HTTP conservando la vía pertinente del proxy TCP, mTLS y las políticas. Para una carga de trabajo MySQL preparada, utilice el parche de la plantilla del Pod y una anotación coherente del Service:

```yaml
spec:
  template:
    metadata:
      annotations:
        config.linkerd.io/opaque-ports: '3306'
---
apiVersion: v1
kind: Service
metadata:
  name: mysql
  namespace: my-app
  annotations:
    config.linkerd.io/opaque-ports: '3306'
spec:
  selector:
    app: mysql
  ports:
  - name: mysql
    port: 3306
    targetPort: 3306
```

Las correspondencias de puertos de Pod y Service deben coincidir. El `proxyProtocol` de un Server seleccionado también afecta al tratamiento del protocolo. El modo opaco no proporciona métricas de rutas HTTP para ese flujo.

En cambio, skip-inbound/outbound-ports eluden la vía del proxy y pueden eliminar el cifrado, las políticas y la telemetría de la malla. No prescriba omitir puertos de Redis, Memcached o bases de datos como optimización genérica de latencia.

Un tiempo de espera de ruta de ServiceProfile es un plazo, no una configuración del conjunto de conexiones. Del mismo modo, el tratamiento del protocolo no garantiza que todas las conexiones HTTP/1 de una aplicación se conviertan en HTTP/2 de extremo a extremo. Mida la reutilización real de conexiones, el almacenamiento en búfer y el comportamiento del protocolo antes de ajustar.

## Operación de certificados

Trate los certificados raíz públicos, las credenciales del emisor, los certificados finales del proxy y los certificados de webhooks como ciclos de vida independientes con sus propios responsables de gestión. Los certificados finales de corta duración predeterminados del proxy no pueden satisfacer una lista genérica de comprobación de 60 días de vigencia restante. Elija los umbrales a partir de las vidas útiles configuradas y la antelación de renovación.

Utilice los ejemplos validados de inspección de credenciales, recarga y eventos del emisor y responsabilidad de gestión de cert-manager de la guía de seguridad. Establecer únicamente `isCA:true` no instala un Issuer, no distribuye raíces de confianza, no rota todos los consumidores ni configura la entrega de alertas.

El antiguo CronJob de certificados utilizaba una imagen antigua no verificada de la CLI, carecía del RBAC necesario y ocultaba los fallos de las comprobaciones detrás de grep. Una comprobación programada necesita un entorno de ejecución compatible, credenciales de alcance limitado, tratamiento explícito de fallos y una vía de entrega probada. El ejemplo anterior de comprobación y registro conserva el estado de salida; la guía de seguridad proporciona alertas basadas en métricas. Ninguno es un servicio completo de notificaciones sin esa integración.

## Resolución de problemas basada en pruebas

Para problemas de inyección, inspeccione el namespace y los metadatos reales de la plantilla del Pod y del Pod, ambos tipos de contenedores, la configuración del webhook y los registros del inyector:

```bash
kubectl get namespace my-app -o yaml
kubectl -n my-app get deployment api -o yaml
# Set this to an actual API Pod.
api_pod=api-example-pod
kubectl -n my-app get pod "$api_pod" -o json | jq '{
  annotations: .metadata.annotations,
  containers: [.spec.containers[]? | {name,image,resources}],
  initContainers: [.spec.initContainers[]? | {name,image,restartPolicy,resources}],
  status: .status
}'
kubectl get mutatingwebhookconfiguration linkerd-proxy-injector-webhook-config
kubectl -n linkerd logs deployment/linkerd-proxy-injector -c proxy-injector --tail=100
```

Para problemas de latencia o inestabilidad, compare el comportamiento de la aplicación, la presión de recursos, los Pods pendientes, los endpoints, DNS, la detección de protocolos y los errores de certificados y políticas. Aumentar los tiempos de espera o reiniciar todo el plano de control no es un diagnóstico.

```bash
linkerd check
linkerd check --proxy
linkerd viz stat deploy -n my-app
linkerd viz tap deployment/api -n my-app --max-rps 20
linkerd viz edges deploy -n my-app
linkerd identity -n my-app -l app=api
kubectl -n my-app top pod --containers
kubectl -n my-app logs deployment/api -c linkerd-proxy --tail=100
kubectl -n linkerd logs deployment/linkerd-destination -c destination --tail=100
kubectl -n linkerd logs deployment/linkerd-identity -c identity --tail=100
kubectl -n linkerd get events --sort-by=.lastTimestamp
```

`linkerd identity` recupera certificados finales públicos; no suponga que existe un archivo fijo `end-entity.crt` en la imagen del proxy. Use `viz routes` de ServiceProfile o los diagnósticos actuales de políticas solo para los recursos realmente configurados. Especifique explícitamente el contenedor del controlador pertinente al leer registros.

Después de una corrección específica, verifique la vía que fallaba originalmente, no solo que un comando termine correctamente.

## Migración desde Istio

Inventaríe las funciones y las propiedades de seguridad utilizadas por cada carga de trabajo antes de diseñar una transición. Estas son **comparaciones parciales de capacidades**, no una conversión mecánica de manifiestos:

| Concepto de Istio | Consideración de Linkerd |
|---|---|
| VirtualService | Funciones de enrutamiento compatibles de Gateway API; ServiceProfile es una interfaz de compatibilidad, no un equivalente completo |
| DestinationRule | Reevalúe individualmente el balanceo de carga, la acumulación de fallos, el comportamiento de las conexiones y los requisitos de TLS |
| PeerAuthentication STRICT | mTLS automático por sí solo es insuficiente porque la política predeterminada de Linkerd puede aceptar texto sin cifrar ajeno a la malla; exija la autorización adecuada |
| AuthorizationPolicy | Modelo diferente de destino y autenticación en Linkerd; JWT, declaraciones de usuario y otras condiciones requieren un diseño independiente |
| Alcance del tráfico de Sidecar | Sin equivalencia general con las anotaciones de inyección ni con un firewall de red |
| Gateway | Elija y configure una implementación adecuada de ingress/gateway y su integración con Linkerd |

Las etiquetas de inyección clásica, las etiquetas y los tags de revisión, las anotaciones de Pods, los manifiestos inyectados manualmente y la incorporación en modo ambient son distintos. Eliminar solo `istio-injection` no los contempla todos. Inspeccione la incorporación real de CNI y proxies de Istio/Linkerd antes de cambiar las cargas de trabajo.

No suponga que el mTLS de las mallas de Istio y Linkerd interopera automáticamente. Las etapas mixtas de migración necesitan límites explícitos de tráfico y seguridad y un comportamiento de aplicación verificado; evite incorporar accidentalmente la misma carga de trabajo en ambas vías de interceptación. Los namespaces por sí solos no son una unidad segura de migración si las dependencias atraviesan esos límites.

Una secuencia práctica de revisión consiste en inventariar dependencias y políticas, reproducirlas en un entorno aislado, probar los flujos permitidos y denegados además de la recuperación, y después trasladar un grupo de cargas de trabajo seleccionado deliberadamente. Reconcilie los controles correctos de incorporación, verifique exactamente la vía prevista del proxy y mida tráfico representativo antes de ampliar la transición. Elimine el plano de control y los recursos antiguos solo cuando ya no quede ningún consumidor que los necesite y el plan de recuperación elegido sea viable.

Esto sustituye la receta incondicional de etiquetar namespaces, reiniciar y desinstalar, y las correspondencias incorrectas de funciones uno a uno del diagrama. La compatibilidad de las aplicaciones y la migración de producción siguen siendo trabajo específico del entorno que debe verificarse.

## Referencias

- [Perfil de alta disponibilidad seleccionado](https://github.com/linkerd/linkerd2/blob/edge-26.9.1/charts/linkerd-control-plane/values-ha.yaml)
- [Configuración del proxy](https://linkerd.io/docs/reference/proxy-configuration/)
- [Plantilla publicada del entorno de ejecución del proxy](https://github.com/linkerd/linkerd2/blob/edge-26.9.1/charts/partials/templates/_proxy.tpl)
- [Guía de actualización](https://linkerd.io/docs/tasks/upgrade/)
- [Política de autorización](https://linkerd.io/docs/reference/authorization-policy/)
- [Inyección de Istio](../istio/advanced/07-sidecar-injection.md) y [modo ambient](../istio/advanced/01-ambient-mode.md)
