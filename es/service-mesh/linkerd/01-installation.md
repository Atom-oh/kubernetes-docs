# Instalación y configuración de Linkerd

> **Última actualización**: 11 de septiembre de 2026 · CLI pública: edge-26.9.1 · Charts correspondientes: 2026.9.1

La guía cubre instalación controlada, propiedad Helm/CLI, HA, extensiones opcionales, EKS, actualizaciones y retirada. Upstream publica artefactos edge; las distribuciones estables tienen instrucciones de instalación/soporte del proveedor. Un hito como 2.20 no es una descarga upstream stable-2.20.0.

Los comandos usan Bash salvo indicación PowerShell. Use kubeconfig/contexto y propietario previstos. CLI y Helm son **alternativas**: no aplique recursos CLI sobre una release Helm. Las comprobaciones offline no establecen dimensionamiento productivo, almacenamiento, enforcement de red ni compatibilidad de aplicación.

## Requisitos

### Kubernetes y Gateway API

| Rama/versión | Evidencia Kubernetes | Evidencia Gateway API |
|---|---|---|
| Hito/distribución Linkerd 2.20 | Matriz 1.31–1.35; confirme soporte del proveedor | Matriz 1.2.1–1.5.1 |
| edge-26.9.1 público usado aquí | Mínimo CLI 1.31.0; edge-26.8.2 elevó máximo probado a 1.36 | Soporte publicado 1.5.1; se usa su paquete estándar |
| Histórico 2.16 | Matriz 1.22–1.29 | No recomendado para instalación actual |
| Históricos 2.15 / 2.14 | Intervalos 1.22–1.29 / 1.21–1.28 | Revise la release; no deduzca «y todo Kubernetes posterior» |

Comprobar el mínimo CLI no comprueba soporte máximo. check --pre correcto no prueba compatibilidad con Kubernetes/Gateway API recién publicados. Para EKS revise también versiones y períodos disponibles. La validación Helm de esta auditoría usó capacidades Kubernetes 1.35.

### Capacidad y plataforma

No dimensione todo el control plane con una cifra universal 100m CPU/200Mi. Inspeccione requests/limits renderizados de controladores, contenedores policy, proxies, init y extensiones; mida tráfico y conexiones. HA espera al menos tres nodos elegibles para anti-afinidad obligatoria y capacidad durante rollout. Separar por zona es preferencia, no garantía de tres zonas distintas.

El tutorial apunta a nodos Linux. Descargar CLI Windows no establece soporte de cargas Windows; compruébelo por separado. Para Cilium kube-proxy replacement revise socketLB.hostNamespaceOnly; al encadenar Linkerd CNI con Cilium, cni.exclusive debe permitir otros plugins.

### Rutas de red y preflight

Verifique origen/destino, no solo puertos para abrir en todas partes:

| Ruta | Ejemplos predeterminados del render fijado |
|---|---|
| API server a admisión | Service 443 a injector/SP-validator 8443 y policy-validator 9443 |
| Proxy a control plane | Identity 8080, destination 8086, policy 8090 |
| Tráfico de aplicación mallada | Proxy entrante 4143 y rutas reales de aplicación/servicio |
| Viz instalado | Tap API 8089, tap gRPC 8088, metrics API 8085, Prometheus 9090 |
| Diagnóstico | Métricas proxy 4191; UI 8084 y admin/readiness separado 9994 |

Son puertos de componentes, no reglas de seguridad sin restricciones. Incluya DNS, Kubernetes API y comportamiento CNI/políticas elegido. Inspeccione targetPorts y webhooks reales.

```bash
LINKERD_CHART_VERSION=2026.9.1
CNI_ENABLED=false  # Set true only after installing/verifying Linkerd CNI.
kubectl config current-context
kubectl version
kubectl get nodes -L kubernetes.io/os,kubernetes.io/arch,topology.kubernetes.io/zone
kubectl get crd httproutes.gateway.networking.k8s.io \
  -o 'jsonpath={.metadata.annotations.gateway\.networking\.k8s\.io/bundle-version}'
# For a new lab without a conflicting installed bundle, after ownership review:
kubectl apply --server-side -f https://github.com/kubernetes-sigs/gateway-api/releases/download/v1.5.1/standard-install.yaml
linkerd check --pre --linkerd-cni-enabled="$CNI_ENABLED"
```

Aplique Gateway API solo si hace falta tras revisar propiedad CRD y todos los controladores consumidores. Si elige Linkerd CNI, instálelo/verifíquelo antes del control plane y use la comprobación CNI posterior. Lea salida y código reales; el antiguo transcript «todo verde» no era un resultado de su clúster.

## Instalación de CLI Linkerd

### Binarios Linux/macOS fijados

Lo siguiente selecciona el artefacto exacto y compara SHA256 con metadatos oficiales. Solo cambia PATH en el shell actual:

```bash
set -euo pipefail
LINKERD_VERSION=edge-26.9.1
case "$(uname -s)/$(uname -m)" in
  Linux/x86_64) suffix=linux-amd64; expected=094e1de06215fbe76fc011cf62c96214f8dae0cd5a58135fb40307be88b6b176 ;;
  Linux/aarch64|Linux/arm64) suffix=linux-arm64; expected=f92eddc52dc1f3089b65fd16014cdb1bc6b07c3fd177091c365cf3d8c0ea1a8b ;;
  Darwin/x86_64) suffix=darwin; expected=acff9471f26552dd0ebb9560925a98d5ca1213a13dfc81464a2b815c9201664d ;;
  Darwin/arm64) suffix=darwin-arm64; expected=5050da9d974e0c2f548a2e9f145540ec035582cfd67f47c58c37411ae3008913 ;;
  *) echo "No verified asset for this OS/architecture in this example" >&2; exit 1 ;;
esac
CLI_DIR="$PWD/linkerd-cli/$LINKERD_VERSION"
mkdir -p "$CLI_DIR"
curl --proto '=https' --tlsv1.2 -fsSL \
  "https://github.com/linkerd/linkerd2/releases/download/$LINKERD_VERSION/linkerd2-cli-$LINKERD_VERSION-$suffix" \
  -o "$CLI_DIR/linkerd.download"
if command -v sha256sum >/dev/null; then
  actual=$(sha256sum "$CLI_DIR/linkerd.download" | awk '{print $1}')
else
  actual=$(shasum -a 256 "$CLI_DIR/linkerd.download" | awk '{print $1}')
fi
test "$actual" = "$expected"
chmod 755 "$CLI_DIR/linkerd.download"
mv "$CLI_DIR/linkerd.download" "$CLI_DIR/linkerd"
export PATH="$CLI_DIR:$PATH"
linkerd version --client
```

Los artefactos cubren Linux amd64/arm64 y macOS Intel/Apple Silicon. La rama ARM genérica del instalador no implica un binario ARM de 32 bits en esta release. La auditoría ejecutó la CLI Linux arm64 nativa; identificó las demás en metadatos oficiales.

### Alternativa del instalador oficial

run.linkerd.io/install antiguo está obsoleto e instala edge, no stable. El instalador actual acepta LINKERD2_VERSION como variable; sh --version stable-2.16.0 antiguo no selecciona un artefacto estable upstream admitido.

```bash
curl --proto '=https' --tlsv1.2 -fsSL https://run.linkerd.io/install-edge -o install-linkerd.sh
# Inspect the downloaded script before execution.
LINKERD2_VERSION=edge-26.9.1 INSTALLROOT="$PWD/linkerd-installer" sh ./install-linkerd.sh
export PATH="$PWD/linkerd-installer/bin:$PATH"
linkerd version --client
```

Seleccione Gateway API desde la matriz de la release. El mensaje final del instalador incluye su propia versión de ejemplo; aquí se fija 1.5.1 tras verificar compatibilidad. Gestores de paquetes/proveedores pueden elegir otras versiones; verifique procedencia y versión, sin asumir que Homebrew/Chocolatey proporcionan esta. No hace falta editar perfiles del shell.

### Binario Windows

El artefacto se llama windows.exe, no windows-amd64.exe:

```powershell
$ErrorActionPreference = "Stop"
$LinkerdVersion = "edge-26.9.1"
$ExpectedSha256 = "d50119c635a0052bfcc7e0b96dcc985676b237ebc87464380677c413344d99a9"
$Download = Join-Path (Get-Location) "linkerd.download.exe"
$Url = "https://github.com/linkerd/linkerd2/releases/download/$LinkerdVersion/linkerd2-cli-$LinkerdVersion-windows.exe"
Invoke-WebRequest -Uri $Url -OutFile $Download
if ((Get-FileHash -Algorithm SHA256 $Download).Hash.ToLowerInvariant() -ne $ExpectedSha256) {
    throw "Linkerd release checksum mismatch"
}
Move-Item $Download (Join-Path (Get-Location) "linkerd.exe") -Force
.\linkerd.exe version --client
```

Los demás ejemplos Bash necesitan shell apropiado, como WSL configurado, o traducción a comandos PowerShell. Esta auditoría no ejecutó PowerShell ni probó cargas Windows.

## Instalación del plano de control

### Instalación CLI

Para instalación nueva gestionada por CLI, aplique CRD antes de generar/instalar control plane:

```bash
linkerd install --crds > linkerd-crds.yaml
kubectl apply -f linkerd-crds.yaml
linkerd install --linkerd-cni-enabled="$CNI_ENABLED" > linkerd-control-plane.yaml
# Review the generated resources and trust credentials before applying.
kubectl apply -f linkerd-control-plane.yaml
linkerd check
```

Los comandos generan manifiestos; kubectl instala. Ancla de confianza e issuer generados por CLI tienen vida finita y requieren rotación planificada. Multiclúster con confianza compartida necesita credenciales proporcionadas deliberadamente, no raíces independientes por clúster.

### Instalación Helm

Helm ofrece flujo repetible de releases/values. Fije versión chart separada del tag CLI:

```bash
helm repo add linkerd-edge https://helm.linkerd.io/edge
helm repo update linkerd-edge
helm show chart linkerd-edge/linkerd-control-plane --version "$LINKERD_CHART_VERSION"
```

Los charts públicos correspondientes son linkerd-crds, linkerd-control-plane, linkerd-viz, linkerd-multicluster y linkerd2-cni 2026.9.1. El appVersion core actual es edge-26.9.1. No instale un chart antiguo sin fijar del repositorio stable suponiendo coincidencia con esta CLI.

#### Ancla de confianza e issuer

Helm necesita certificado de confianza más certificado/clave privada del issuer, o una integración externa de Secret admitida y deliberadamente configurada. No exige subir la clave privada de la CA raíz.

Use [Smallstep CLI](https://smallstep.com/docs/step-cli/installation/) instalado con la interfaz certificate-create publicada. El ejemplo ECDSA P-256 conserva las vidas de demostración originales y corrige la continuación rota tras --not-after:

```bash
umask 077
mkdir linkerd-pki
(
  cd linkerd-pki
  # Demonstration lifetimes, not a universal certificate policy.
  step certificate create root.linkerd.cluster.local ca.crt ca.key \
    --profile root-ca --kty EC --curve P-256 \
    --not-after 87600h --no-password --insecure
  step certificate create identity.linkerd.cluster.local issuer.crt issuer.key \
    --profile intermediate-ca --kty EC --curve P-256 \
    --not-after 8760h --no-password --insecure \
    --ca ca.crt --ca-key ca.key
  openssl verify -CAfile ca.crt issuer.crt
  openssl x509 -in issuer.crt -noout -text
)
```

Inspeccione cadena, algoritmo y validez. La clave raíz queda fuera de Kubernetes; solo se proporciona ancla pública y credencial de firma del issuer. --no-password/--insecure genera claves locales sin cifrar, por lo que se usa directorio/umask restringido. PKI productiva necesita almacenamiento y rotación aprobados. La auditoría comprobó flags en documentación, no generó certificados Smallstep.

#### Values personalizados

Guarde como linkerd-values.yaml. Son ejemplos de dimensionamiento, no garantías:

```yaml
proxy:
  resources:
    cpu:
      request: 100m
      limit: 1000m
    memory:
      request: 64Mi
      limit: 250Mi
  logLevel: warn,linkerd=info
  logFormat: plain
identity:
  issuer:
    clockSkewAllowance: 20s
    issuanceLifetime: 24h0m0s
controllerResources: &id001
  cpu:
    request: 100m
    limit: 1000m
  memory:
    request: 50Mi
    limit: 250Mi
destinationResources: *id001
identityResources: *id001
proxyInjectorResources: *id001
```

proxy.logLevel y proxy.logFormat son las claves anidadas reales. destinationResources, identityResources y proxyInjectorResources se admiten aunque no aparezcan todas en values base; las usan el perfil HA y plantillas. namespace.labels y proxyLogLevel/proxyLogFormat raíz antiguos no se consumían. El chart añade por defecto supresiones de logging de cabeceras/solicitudes al selector; inspeccione el entorno final.

```bash
helm install linkerd-crds linkerd-edge/linkerd-crds \
  --version "$LINKERD_CHART_VERSION" -n linkerd --create-namespace --wait

helm template linkerd-control-plane linkerd-edge/linkerd-control-plane \
  --version "$LINKERD_CHART_VERSION" -n linkerd -f linkerd-values.yaml \
  --set "cniEnabled=$CNI_ENABLED" \
  --set-file identityTrustAnchorsPEM=linkerd-pki/ca.crt \
  --set-file identity.issuer.tls.crtPEM=linkerd-pki/issuer.crt \
  --set-file identity.issuer.tls.keyPEM=linkerd-pki/issuer.key \
  > linkerd-rendered.yaml
# Review the render, then install through Helm (do not apply the render as another owner).
helm install linkerd-control-plane linkerd-edge/linkerd-control-plane \
  --version "$LINKERD_CHART_VERSION" -n linkerd -f linkerd-values.yaml \
  --set "cniEnabled=$CNI_ENABLED" \
  --set-file identityTrustAnchorsPEM=linkerd-pki/ca.crt \
  --set-file identity.issuer.tls.crtPEM=linkerd-pki/issuer.crt \
  --set-file identity.issuer.tls.keyPEM=linkerd-pki/issuer.key \
  --wait --timeout 10m
linkerd check
```

Manifiestos y backups de values pueden incluir claves privadas del issuer. Restrinja acceso y no pegue contenido en informes. Mantenga el mismo propietario de release/credenciales al actualizar.

## Instalación de alta disponibilidad

Use values-ha.yaml incluido en el chart fijado:

```bash
helm pull linkerd-edge/linkerd-control-plane --version "$LINKERD_CHART_VERSION"
tar -xOf "linkerd-control-plane-$LINKERD_CHART_VERSION.tgz" \
  linkerd-control-plane/values-ha.yaml > linkerd-ha.yaml
# For the Helm render/install above, use:
# -f linkerd-ha.yaml -f linkerd-values.yaml
# For a new CLI-owned installation, render with:
linkerd install --ha --linkerd-cni-enabled="$CNI_ENABLED" > linkerd-ha-rendered.yaml
```

En Helm, coloque el archivo HA **antes** de sus values personalizados tanto al renderizar como instalar. Compruebe que sobrescrituras posteriores no desactiven requisitos HA.

El perfil habilita tres réplicas críticas, separación obligatoria por nodo, preferida por zona, PDB y política Fail de webhook. Son instancias redundantes, no quórum de consenso de tres miembros. La disponibilidad depende también de API/red, credenciales, capacidad y aplicación.

Los campos manuales anteriores destination.replicas/identity.resources/proxyInjector.resources no configuraban los contenedores previstos. Un podDisruptionBudget raíz no creaba PDB y topologySpreadConstraints raíz no se consumía. El render antiguo mostraba tres réplicas, pero faltaban recursos de controladores y PDB. Use el perfil real e inspeccione.

```bash
kubectl -n linkerd get pods -o wide
kubectl -n linkerd get pdb
kubectl -n linkerd get deployments -o yaml
```

Con menos de tres nodos elegibles, la anti-afinidad puede dejar réplicas Pending. Revise admisión Fail e interrupciones antes de confiar en HA; no debilite webhooks como remedio genérico.


## Instalación de extensiones

### Viz: dashboard y métricas

Para extensión gestionada por CLI:

```bash
linkerd viz install > linkerd-viz.yaml
# Review the optional extension and its metrics backend.
kubectl apply -f linkerd-viz.yaml
linkerd viz check
linkerd viz dashboard
```

En Helm, guarde viz-values.yaml e inspeccione PVC, Deployment y recursos:

```yaml
prometheus:
  enabled: true
  resources:
    cpu:
      request: 300m
      limit: 1000m
    memory:
      request: 300Mi
      limit: 1Gi
  persistence:
    storageClass: gp3
    size: 10Gi
    accessMode: ReadWriteOnce
dashboard:
  replicas: 1
  resources:
    cpu:
      request: 100m
      limit: 500m
    memory:
      request: 50Mi
      limit: 250Mi
tap:
  replicas: 1
  resources:
    cpu:
      request: 100m
      limit: 1000m
    memory:
      request: 50Mi
      limit: 250Mi
metricsAPI:
  replicas: 1
  resources:
    cpu:
      request: 100m
      limit: 500m
    memory:
      request: 50Mi
      limit: 250Mi
```

```bash
helm install linkerd-viz linkerd-edge/linkerd-viz \
  --version "$LINKERD_CHART_VERSION" -n linkerd-viz --create-namespace \
  -f viz-values.yaml --wait --timeout 10m
linkerd viz check
```

El chart admite persistencia cuando **existe el mapa** persistence. No usa persistence.enabled como interruptor. accessMode es obligatorio; el ejemplo anterior lo omitía y renderizaba null. Omitir el mapa usa emptyDir. StorageClass gp3 es requisito de ejemplo, no algo que cree Viz; verifique CSI EBS, permisos y topología en EKS.

Prometheus incluido tiene una réplica; persistencia selecciona Recreate. Un PVC conserva datos en reemplazos adecuados, pero no hace HA ni garantiza disponibilidad continua. Chart 2026.9.1 usa Prometheus v2.55.1 y seis horas de retención por defecto. Elija explícitamente mantenimiento, retención y disponibilidad.

Para Prometheus externo ya configurado, este archivo es una **alternativa**:

```yaml
prometheus:
  enabled: false
prometheusUrl: http://prometheus.monitoring.svc.cluster.local:9090
```

Configure scrapes/relabeling Linkerd y acceso antes de cambiar. Verifique consultas y métricas Viz reales, no solo readiness HTTP. Se admiten recursos dashboard, tap y metricsAPI. grafana.enabled no despliega: el chart ofrece enlaces para Grafana gestionado aparte.

Use dashboard localhost inicialmente. dashboard.enforcedHostRegexp valida Host; no autentica usuarios, y vacío elige la restricción predeterminada. Un ingress organizativo necesita autenticación/autorización, exposición aprobada y host permitido.

### Trazado distribuido

edge-26.9.1 no tiene subcomando linkerd jaeger. El chart público linkerd-jaeger termina en 2025.9.4, no corresponde a 2026.9.1. Sustituya instrucciones obsoletas de instalar/comprobar/actualizar/desinstalar por collector/backend independiente y configuración de tracing del proxy.

Tracing requiere contexto entrante, propagación de aplicación y protocolos compatibles. Una topología Viz o gráfico métrico no es una traza. Consulte [observabilidad](05-observability.md) y [documentación oficial](https://linkerd.io/docs/features/distributed-tracing/) para la ruta completa. Esta auditoría no afirma que un despliegue Collector/Jaeger no probado funcione extremo a extremo. Si existe una release antigua linkerd-jaeger, inventaríe/migre datos y retírela mediante su propietario; la CLI actual no gestiona esa extensión eliminada.

### Multiclúster

La CLI puede renderizar una extensión base:

```bash
linkerd multicluster install > linkerd-multicluster.yaml
# Review network exposure, shared trust and actual gateway configuration first.
kubectl apply -f linkerd-multicluster.yaml
linkerd multicluster check
```

Antes de aplicar, elija exposición gateway adecuada. La extensión sola no enlaza clústeres, no crea confianza compartida ni concede acceso a API Kubernetes remota.

En EKS con **AWS Load Balancer Controller**, el ejemplo elige NLB interno y conserva TCP al gateway Linkerd:

```yaml
gateway:
  replicas: 1
  serviceType: LoadBalancer
  loadBalancerClass: service.k8s.aws/nlb
  serviceAnnotations:
    service.beta.kubernetes.io/aws-load-balancer-scheme: internal
    service.beta.kubernetes.io/aws-load-balancer-nlb-target-type: ip
    service.beta.kubernetes.io/aws-load-balancer-attributes: load_balancing.cross_zone.enabled=true
remoteMirrorServiceAccountName: linkerd-service-mirror-remote-access-default
```

Guarde multicluster-values.yaml y use la alternativa Helm:

```bash
helm install linkerd-multicluster linkerd-edge/linkerd-multicluster \
  --version "$LINKERD_CHART_VERSION" -n linkerd-multicluster --create-namespace \
  -f multicluster-values.yaml --wait --timeout 10m
```

loadBalancerClass selecciona controlador. Auto Mode tiene contrato de clase/configuración diferente; no mezcle supuestos ni cambie casualmente propiedad Service existente. Asegure resolución/acceso desde redes remotas al gateway y probes. No termine mTLS Linkerd en un listener ACM ajeno.

gateway.resources no se consume. Recursos del proxy gateway vienen de la inyección; inspeccione el Pod, no asuma que un bloque ignorado cambió límites. El override HA del chart usa gateway.replicas y anti-afinidad.

Las credenciales remotas edge actuales rechazan proveedores exec. Use el flujo de [multiclúster](06-multi-cluster.md) y verifique controlador/versión service-mirror y acceso API mínimo.

## CNI y configuración Amazon EKS

### Linkerd CNI opcional

Linkerd CNI se encadena con el principal; no sustituye VPC CNI o Cilium. Debe estar listo en los nodos **antes** de que control plane y cargas usen configuración CNI:

```bash
# Optional branch, before control-plane installation.
helm install linkerd-cni linkerd-edge/linkerd2-cni \
  --version "$LINKERD_CHART_VERSION" -n linkerd-cni --create-namespace --wait
kubectl -n linkerd-cni rollout status daemonset/linkerd-cni --timeout=180s
CNI_ENABLED=true
linkerd check --pre --linkerd-cni-enabled
# Use --linkerd-cni-enabled=true for CLI control-plane installation,
# or --set cniEnabled=true for the control-plane Helm chart.
```

Verifique directorios CNI de configuración/binarios y comportamiento del plugin. Los valores /etc/cni/net.d y /opt/cni/bin no son universales. El chart consume cniEnabled; el render debe omitir linkerd-init como se espera.

Sin Linkerd CNI, la redirección init normal necesita NET_ADMIN. Con CNI pasa al plugin de nodo. Esta release habilita sidecars nativos por defecto: inspeccione containers e initContainers. Identity Deployment usa deliberadamente proxy regular sin espera inicial; no es inyección fallida. Desactivar sidecars nativos cambia orden de red/arranque init; un UID de bypass no es solución genérica de seguridad.

Para reemplazo kube-proxy Cilium, la configuración Linkerd documentada usa socketLB.hostNamespaceOnly=true para conservar direcciones Service en tráfico Pod. Encadenar CNI requiere también cni.exclusive=false. Revise con el propietario del CNI principal, no reemplace configuración a ciegas.

### Clúster EKS existente

Use clúster soportado y verifique versión frente a rama Linkerd y EKS. La antigua creación EKS 1.28 es orientación obsoleta. El procedimiento Linux supone nodos EC2 compatibles; Fargate no ejecuta este DaemonSet CNI y no es destino intercambiable.

Si prepara kubeconfig dedicado:

```bash
: "${EKS_CLUSTER_NAME:?Set the intended existing cluster}"
: "${EKS_REGION:?Set its region}"
aws eks describe-cluster --name "$EKS_CLUSTER_NAME" --region "$EKS_REGION"   --query 'cluster.{version:version,endpoint:endpoint}' --output json
aws eks update-kubeconfig --name "$EKS_CLUSTER_NAME" --region "$EKS_REGION"   --kubeconfig "$PWD/linkerd.kubeconfig" --alias linkerd-lab
export KUBECONFIG="$PWD/linkerd.kubeconfig"
kubectl config current-context
kubectl -n kube-system get daemonset aws-node   -o jsonpath='{.spec.template.spec.containers[*].image}'
```

Verifique endpoint/contexto antes de modificar. Los controladores Linkerd usan credenciales API Kubernetes; linkerd-destination no necesita IAM solo para descubrir Services. Los permisos AWS corresponden al llamante real, como LB Controller, CSI EBS o collector, con IRSA/Pod Identity admitidos.

### Dashboard y red EKS

El antiguo ALB público exponía administración sin autenticación diseñada. Use localhost hasta configurar y probar ingress organizativo autenticado.

El puerto web Service 8084 es válido. Admin/readiness separado usa 9994 y probe /ready. No asuma la misma semántica en la UI. ALB debe alinear salud de targets, grupos de seguridad, validación Host, certificados y autenticación; un certificado TLS no autentica usuarios.

Limite grupos de seguridad y NetworkPolicy a origen/destino reales. La tabla de puertos es información diagnóstica, no solicitud de exponer métricas/webhooks a cualquiera. Valide arranque CNI, DNS, admisión, identidad y rutas entre nodos.

## Verificación de instalación

```bash
linkerd check
linkerd check --proxy -n my-app
linkerd viz check
linkerd multicluster check
kubectl -n linkerd get pods,services,pdb -o wide
kubectl -n linkerd-viz get pods,services -o wide
```

Compruebe extensiones solo si están instaladas. check --proxy comprueba plano de datos, no «todas las extensiones». No valida lógica de negocio.

Para una aplicación de muestra, revise manifiesto fijado antes de aplicarlo, anote solo el namespace elegido y recree cargas previstas. Una URL emojivoto mutable y exportar/reaplicar todos los Deployments vivos no son entrada reproducible. Confirme imágenes/arquitectura, puertos, readiness y HTTP/TCP real.

```bash
kubectl annotate namespace my-app linkerd.io/inject=enabled
kubectl -n my-app rollout restart deployment/my-app
kubectl -n my-app rollout status deployment/my-app
linkerd check --proxy -n my-app
linkerd viz stat deploy/my-app -n my-app
linkerd viz top deploy/my-app -n my-app
```

Sustituya my-app por namespace y Deployment reales. Métricas/tap/top dependen de extensión y protocolo; no prueban cifrado de todo tráfico ni éxito de todas las operaciones.

## Actualización Linkerd

### Planificación

Elija CLI/chart exactos y revise release notes, compatibilidad, skew y salud. El objetivo no promete actualización directa desde toda instalación histórica 2.14/2.16; siga pasos intermedios y proveedor. Tags edge no garantizan versionado semántico. Actualice CLI, CRD/control plane, extensiones y finalmente proxies mediante sus propietarios.

Use check y check --proxy en instalaciones existentes. check --pre es preflight de nueva instalación con supuestos de namespace/configuración, no reemplaza planificación. Conserve confianza y revise versiones CRD eliminadas antes de actualizar.

### Instalación gestionada por CLI

```bash
# First install/verify the selected target CLI and review the supported upgrade path.
linkerd version --client
linkerd check
linkerd check --proxy
linkerd upgrade --crds > linkerd-crds-upgrade.yaml
kubectl apply -f linkerd-crds-upgrade.yaml
linkerd upgrade > linkerd-upgrade.yaml
# Review retained configuration and credentials before applying.
kubectl apply -f linkerd-upgrade.yaml
linkerd check
linkerd viz install > linkerd-viz-upgrade.yaml
kubectl apply -f linkerd-viz-upgrade.yaml
linkerd viz check
# Likewise review/install the selected multicluster extension if present.
linkerd prune > linkerd-obsolete.yaml
# Review ownership and contents before any kubectl delete -f linkerd-obsolete.yaml.
```

Las extensiones tienen install para renderizar actualizaciones, no subcomando viz upgrade. Un help que devuelve 0 puede ser ayuda del padre; revise comandos disponibles y contenido generado. Revise prune antes de borrar. Actualizaciones multiclúster pueden exigir volver a enlazar según el flujo admitido.

### Instalación gestionada por Helm

```bash
umask 077
helm get values linkerd-control-plane -n linkerd > current-values.yaml
helm get manifest linkerd-control-plane -n linkerd > current-manifest.yaml
# Migrate intentional overrides to reviewed-values.yaml; preserve current trust credentials.
helm upgrade linkerd-crds linkerd-edge/linkerd-crds \
  --version "$LINKERD_CHART_VERSION" -n linkerd --wait
helm upgrade linkerd-control-plane linkerd-edge/linkerd-control-plane \
  --version "$LINKERD_CHART_VERSION" -n linkerd \
  --reset-values -f reviewed-values.yaml --wait --timeout 10m
# Upgrade each installed extension with its own reviewed values and pinned chart.
linkerd check
```

Los values revisados deben incluir HA/CNI deliberados y confianza/issuer **existentes** o referencias Secret externas admitidas. --reset-values sin conservar entradas puede cambiar comportamiento o fallar; --reuse-values puede mantener ajustes obsoletos. Compare defaults y overrides; nunca regenere CA solo por una actualización rutinaria.

### Actualizar plano de datos

Actualice una carga prevista cada vez según su política de disponibilidad:

```bash
kubectl -n my-app rollout restart deployment/my-app
kubectl -n my-app rollout status deployment/my-app
linkerd check --proxy -n my-app
kubectl -n my-app get pods -o json |
  jq '.items[] | {pod: .metadata.name, proxies: ([.spec.containers[]?, .spec.initContainers[]?] | map(select(.name == "linkerd-proxy") | {image, restartPolicy}))}'
```

stat informa tráfico, no inventario de versiones de imagen proxy. Arriba se revisan ubicaciones regulares y nativas. Compruebe skew aplicable y readiness/tráfico reales tras recrear.

## Resolución de problemas

### Admisión y recursos

```bash
kubectl -n linkerd get service linkerd-proxy-injector
kubectl get mutatingwebhookconfiguration linkerd-proxy-injector-webhook-config -o yaml
kubectl -n linkerd get networkpolicy
kubectl -n linkerd get events --sort-by='.lastTimestamp'
: "${LINKERD_POD:?Set a control-plane Pod name}"
kubectl -n linkerd describe pod "$LINKERD_POD"
```

La inyección puede fallar por CA bundles, selección/red webhook, configuración rechazada o seguridad Pod; no siempre es conectividad Service. Pending puede indicar anti-afinidad, taints, volúmenes, cuota o recursos. Lea el evento real antes de cambiar límites o seguridad.

### Certificados

Por defecto, las raíces están en un **ConfigMap** y certificado/clave del issuer en un Secret:

```bash
set -euo pipefail
kubectl -n linkerd get configmap linkerd-identity-trust-roots \
  -o jsonpath='{.data.ca-bundle\.crt}' > trust-bundle.pem
openssl crl2pkcs7 -nocrl -certfile trust-bundle.pem |
  openssl pkcs7 -print_certs -text -noout
kubectl -n linkerd get secret linkerd-identity-issuer -o json |
  jq -er '.data["crt.pem"] // .data["tls.crt"]' |
  base64 -d | openssl x509 -noout -dates
```

El formato issuer predeterminado usa crt.pem; kubernetes.io/tls usa tls.crt. Compruebe esquema, no asuma campos iguales. Integraciones de confianza pueden cambiar propietario. Inspeccione todos los certificados, reloj/validez, issuer e identidad; evite reemplazar raíz sin plan.

### Logs de componentes y proxies

```bash
kubectl -n linkerd logs deployment/linkerd-destination -c destination
kubectl -n linkerd logs deployment/linkerd-destination -c policy
kubectl -n linkerd logs deployment/linkerd-identity -c identity
kubectl -n linkerd logs deployment/linkerd-proxy-injector -c proxy-injector
: "${APP_POD:?Set an application Pod name}"
kubectl -n my-app logs "$APP_POD" -c linkerd-proxy
linkerd diagnostics proxy-metrics "$APP_POD" -n my-app
```

Use nombres reales de componentes/contenedores de la versión. Conserve logs antes de borrar o reemplazar Pods.

## Desinstalación

### Retirar primero proxies de aplicación

Planifique pérdida de políticas, routing y observabilidad. Retire fuentes de inyección y configuración manual mediante el propietario, recree cargas y verifique ambas ubicaciones de contenedor antes de quitar control plane:

```bash
# Choose the actual application namespace/Deployment and review all injection sources.
kubectl annotate namespace my-app linkerd.io/inject-
# Also remove any Pod-template injection override/manual proxy using its manifest owner.
kubectl -n my-app rollout restart deployment/my-app
kubectl -n my-app rollout status deployment/my-app
kubectl -n my-app get pods -o json |
  jq '.items[] | {pod: .metadata.name, containers: ([.spec.containers[]?, .spec.initContainers[]?] | map(.name))}'
```

Eliminar solo una anotación namespace no anula la de plantilla Pod ni retira un proxy manual. Valide conexión/seguridad sin malla. No use force para omitir cargas aún inyectadas.

### Retirada gestionada por CLI

```bash
# Only after applications are unmeshed and extension dependencies are removed.
linkerd viz uninstall > remove-viz.yaml
linkerd multicluster uninstall > remove-multicluster.yaml
# Inspect each manifest and remove only the extensions actually installed via CLI.
kubectl delete -f remove-viz.yaml
kubectl delete -f remove-multicluster.yaml
linkerd uninstall > remove-linkerd.yaml
# This includes namespace-scoped resources and cluster-wide CRDs.
kubectl delete -f remove-linkerd.yaml
```

Quite solo extensiones instaladas. La eliminación generada del control plane incluye CRD; borrarlos elimina sus instancias. Inventaríe y respalde lo necesario. No es solo borrar un Deployment.

### Retirada gestionada por Helm

```bash
# Only the releases actually installed through Helm, after unmeshing applications.
helm uninstall linkerd-viz -n linkerd-viz
helm uninstall linkerd-multicluster -n linkerd-multicluster
helm uninstall linkerd-control-plane -n linkerd
# Inventory/back up CR instances before removing the CRDs.
helm uninstall linkerd-crds -n linkerd
```

Si se instaló Linkerd CNI, limpie su plugin de nodo aparte cuando ninguna carga dependa de él y verifique que el principal siga intacto. Borre namespaces solo tras comprobar propiedad y contenido restante, no como limpieza incondicional de cuatro namespaces.

## Siguientes pasos

- [Arquitectura](02-architecture.md)
- [Gestión de tráfico](03-traffic-management.md)
- [Seguridad y ciclo de certificados](04-security.md)
- [Observabilidad](05-observability.md)
- [Multiclúster](06-multi-cluster.md)
- [Cuestionario de instalación](../../quizzes/service-mesh/linkerd/installation.md)

## Referencias

- [Modelo de releases](https://linkerd.io/releases/) y [artefactos edge-26.9.1](https://github.com/linkerd/linkerd2/releases/tag/edge-26.9.1)
- [Matriz Kubernetes](https://linkerd.io/docs/reference/k8s-versions/) y [compatibilidad Gateway API](https://linkerd.io/docs/features/gateway-api/)
- [Instalación Helm](https://linkerd.io/docs/tasks/install-helm/) e [índice oficial edge](https://helm.linkerd.io/edge/index.yaml)
- [Comportamiento HA](https://linkerd.io/docs/features/ha/) y [configuración clúster/Cilium](https://linkerd.io/docs/reference/cluster-configuration/)
- [Generación de certificados](https://linkerd.io/docs/tasks/generate-certificates/) y [referencia Smallstep create](https://smallstep.com/docs/step-cli/reference/certificate/create/)
- [CNI](https://linkerd.io/docs/features/cni/), [actualización](https://linkerd.io/docs/tasks/upgrade/) y [desinstalación](https://linkerd.io/docs/tasks/uninstall/)
- [Ajustes Service de AWS Load Balancer Controller](https://kubernetes-sigs.github.io/aws-load-balancer-controller/latest/guide/service/annotations/) y [restricciones EKS Fargate](https://docs.aws.amazon.com/eks/latest/userguide/fargate.html)
