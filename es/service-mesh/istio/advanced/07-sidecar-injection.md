# Inyección de sidecars

> **Base de verificación**: Istio 1.31.0, Kubernetes 1.32–1.37
> **Última revisión**: 16 de octubre de 2026

La inyección automática es un webhook de admisión que modifica los Pods recién creados. No añade un sidecar en ejecución a los Pods existentes ni edita la plantilla del Deployment. La inyección manual con `istioctl kube-inject` genera un manifiesto de aplicación con la configuración del proxy incluida.

## Configuración de la inyección automática

### Nivel de namespace

Use un único modo de inyección para el namespace de la aplicación existente. Antes de cambiar las etiquetas, registre las actuales y la revisión instalada; no use una etiqueta de revisión para una revisión/etiqueta que no tenga un inyector correspondiente.

```bash
# Existing, reviewed application namespace; inspect before choosing one mode.
INJECTION_NAMESPACE=injection-demo
kubectl get namespace "$INJECTION_NAMESPACE" -L istio-injection,istio.io/rev,istio.io/dataplane-mode

# Legacy/default injection alternative, only when no revision/ambient mode is selected.
kubectl label namespace "$INJECTION_NAMESPACE" istio-injection=enabled --overwrite
```

```bash
# Alternative: choose an already installed revision or existing revision tag.
istioctl tag list
kubectl get mutatingwebhookconfigurations -l istio.io/rev
kubectl label namespace "$INJECTION_NAMESPACE" istio-injection-
kubectl label namespace "$INJECTION_NAMESPACE" istio.io/rev=<installed-revision-or-tag> --overwrite
```

Cuando un namespace tenga ambas etiquetas `istio-injection` y `istio.io/rev`, prevalece la etiqueta heredada `istio-injection`. La etiqueta de namespace `istio-injection=disabled` o la etiqueta de Pod `sidecar.istio.io/inject="false"` deshabilita la inyección aunque otra etiqueta de inyección la solicite. Si no hay etiquetas explícitas, normalmente la inyección está desactivada, salvo que el instalador habilite `enableNamespacesByDefault`.

Después de revisar la disponibilidad, el PDB y la capacidad, vuelva a crear solo las cargas de trabajo previstas para que adopten el inyector seleccionado. Cambiar una etiqueta de namespace no modifica los Pods existentes. Mantenga por separado la inscripción en modo ambient; siga la [guía de migración a ambient](01-ambient-mode.md) en lugar de mezclar modos de plano de datos.

### Nivel de Pod

La **etiqueta** de inyección va en el Pod o en `spec.template.metadata` de un Deployment. La anotación anterior con el mismo nombre está obsoleta.

```yaml
# Existing Deployment: spec.template fragment
metadata:
  labels:
    sidecar.istio.io/inject: "true"
```

Esto selecciona los Pods aptos para inyección, pero no anula una desactivación a nivel de namespace ni despliega una aplicación. Conserve las etiquetas, revisión y configuración de carga de trabajo existentes; son fragmentos, no Pods ejecutables con una imagen `myapp:latest` inventada.

## Inyección manual

Use la versión de `istioctl` y la configuración completa que coincidan con el plano de control previsto. De forma predeterminada, kube-inject puede leer la configuración del clúster seleccionado; para generar contenido local reproducible, exporte los ConfigMaps reales de inyector/malla para esa revisión e inspecciónelos primero.

```bash
# Obtain all three files from the same installed revision/configuration.
kubectl -n istio-system get configmap <injector-configmap> -o jsonpath='{.data.config}' > inject-config.yaml
kubectl -n istio-system get configmap <injector-configmap> -o jsonpath='{.data.values}' > inject-values.yaml
kubectl -n istio-system get configmap <mesh-configmap> -o jsonpath='{.data.mesh}' > mesh-config.yaml

# Render from the reviewed original application manifest with matching istioctl.
istioctl kube-inject --revision <actual-revision-or-default> --injectConfigFile inject-config.yaml --meshConfigFile mesh-config.yaml --valuesFile inject-values.yaml --filename deployment.yaml --output deployment-injected.yaml

# Review the generated file and deployment diff before the planned rollout.
kubectl diff -f deployment-injected.yaml
kubectl apply -f deployment-injected.yaml
```

En Istio 1.31, omitir `--revision` puede activar un observador de clúster de la revisión predeterminada aunque se usen archivos locales, y dejar el comando esperando. Especifique la revisión real que coincida con la configuración exportada, o `default` para una instalación sin revisiones. Se verificó la generación con una revisión explícita y los tres archivos de configuración locales sin descubrir el clúster.

`deployment.yaml` debe contener los recursos originales de la aplicación. Manténgalo separado de la salida generada y vuelva a generarla a partir de esa fuente cuando cambie la configuración o la versión. Decida deliberadamente si la inyección automática o la manual administra la inyección e inspeccione los resultados de admisión; no acumule ediciones improvisadas en los contenedores de proxy generados. Un código de salida 1 de `kubectl diff` normalmente indica que encontró diferencias, no que aplicar los cambios esté aprobado o validado.

## Configuración de recursos del sidecar

Estas son las solicitudes/límites originales del ejemplo; consérvelos como parámetros de ajuste específicos de la carga de trabajo, no como dimensionamiento para producción:

```yaml
# Existing Deployment: spec.template fragment
metadata:
  annotations:
    sidecar.istio.io/proxyCPU: "100m"
    sidecar.istio.io/proxyMemory: "128Mi"
    sidecar.istio.io/proxyCPULimit: "200m"
    sidecar.istio.io/proxyMemoryLimit: "256Mi"
```

Establezca deliberadamente la solicitud y el límite correspondiente: indicar `proxyCPU`/`proxyMemory` sin el límite correspondiente puede eliminarlo. Verifique los recursos del proxy renderizado, LimitRange/ResourceQuota del namespace, el throttling de CPU y el uso de memoria. Los cambios en la plantilla del Pod afectan a los Pods que se creen en adelante.

## Exclusión de la inyección

```yaml
# Existing Deployment: spec.template fragment
metadata:
  labels:
    sidecar.istio.io/inject: "false"
```

La etiqueta impide la futura inyección de sidecar; no elimina un proxy inyectado que ya exista ni excluye un Pod de la captura de ambient. Reconcilie las etiquetas/anotaciones existentes y vuelva a crear solo la carga de trabajo seleccionada mediante su proceso normal de despliegue gradual.

## Solución de problemas

```bash
kubectl get namespace "$INJECTION_NAMESPACE" -L istio-injection,istio.io/rev,istio.io/dataplane-mode
kubectl get mutatingwebhookconfigurations
kubectl get events -n "$INJECTION_NAMESPACE" --sort-by=.lastTimestamp

kubectl get pods -n "$INJECTION_NAMESPACE" -o json |
  jq '.items[] | {
    pod:.metadata.name,
    revision:.metadata.annotations["istio.io/rev"],
    proxies: ([.spec.containers[]?, .spec.initContainers[]?] |
      map(select(.name == "istio-proxy") | {name,image,restartPolicy}))
  }'
istioctl proxy-status
```

Los sidecars nativos usan `spec.initContainers` con `restartPolicy: Always`; los sidecars clásicos usan `spec.containers`. Los sidecars nativos de Kubernetes son estables desde la versión 1.33 y están habilitados de forma predeterminada en la 1.32, mientras que la anotación de Istio `sidecar.istio.io/nativeSidecar` sigue documentada como Alpha. Confirme el comportamiento del inyector instalado en lugar de presuponer que siempre aparecerá una visualización READY de 2/2.

Si no se crean los Pods, inspeccione por separado los eventos del controlador, la accesibilidad/certificados del webhook, los selectores de namespace/objeto, la disponibilidad de la revisión y los límites de admisión de recursos. Si hay un proxy, inspeccione por separado su estado de disponibilidad, registros y sincronización xDS. La presencia de un nombre de proxy no demuestra una inscripción correcta en la malla.

## Referencias

- [Inyección de sidecar de Istio](https://istio.io/latest/docs/setup/additional-setup/sidecar-injection/)
- [Anotaciones de inyección de Istio](https://istio.io/latest/docs/reference/config/annotations/)
- [Actualizaciones de revisión de Istio](https://istio.io/latest/docs/setup/upgrade/canary/)
- [Contenedores sidecar nativos de Kubernetes](https://kubernetes.io/docs/concepts/workloads/pods/sidecar-containers/)
- [Plantilla de inyección de Istio 1.31](https://raw.githubusercontent.com/istio/istio/1.31.0/manifests/charts/istio-control/istio-discovery/files/injection-template.yaml)
- [Comando de inyección local de Istio 1.31](https://raw.githubusercontent.com/istio/istio/1.31.0/istioctl/pkg/kubeinject/kubeinject.go)
- [Resolución de la revisión predeterminada en Istio 1.31](https://raw.githubusercontent.com/istio/istio/1.31.0/istioctl/pkg/cli/context.go)
