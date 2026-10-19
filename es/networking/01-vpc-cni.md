# Amazon VPC CNI

> **Base revisada**: VPC CNI / Helm chart 1.23.2; agente de políticas de red 1.4.3.
> **Última revisión**: 16 de octubre de 2026.
>
> **Listado actual de complementos de EKS**: AWS incluye `v1.23.1-eksbuild.1` para Kubernetes 1.31–1.37.
>
> **Ejemplo de versión fijada**: Los ejemplos de configuración siguientes usan upstream/Helm 1.23.2. Las versiones de upstream, Helm y EKS `eksbuild` son identificadores independientes. Compruebe la disponibilidad para la versión de Kubernetes y la región reales del clúster.

## Tabla de contenido

- [Descripción general de VPC CNI](#vpc-cni-overview)
- [Modelo de red](#networking-model)
- [Instalación y configuración](#installation-and-configuration)
- [Administración de direcciones IP](#ip-address-management)
- [Compatibilidad con NetworkPolicy](#network-policy-support)
- [Características avanzadas](#advanced-features)
- [Solución de problemas](#troubleshooting)
- [Prácticas recomendadas](#best-practices)

## Descripción general de VPC CNI {#vpc-cni-overview}

Amazon VPC CNI proporciona redes de Pod nativas de VPC en nodos EC2 estándar de EKS. Los comandos de DaemonSet `aws-node` de esta guía se dirigen a esa instalación. Auto Mode ejecuta los componentes de red administrados como servicios de nodo; Fargate y Windows usan rutas de administración distintas. Consulte la [descripción general](README.md) antes de aplicar instrucciones de EC2/Linux a otro modo de cómputo.

Los Pods usan direcciones enrutables de VPC sin requerir encapsulación de overlay. El enrutamiento, los grupos de seguridad, las políticas de red, los límites de ENI/IP y el comportamiento de la aplicación aún determinan la conectividad y el rendimiento. EKS admite **direccionamiento IPv4 o IPv6 de Pod/Service**, seleccionado al crear el clúster; no admite Pods ni Services de doble pila. Una VPC de doble pila o el asistente de salida IPv4 de un Pod IPv6 es un concepto diferente.

### Arquitectura

| Componente | Responsabilidad |
|---|---|
| Entorno de ejecución de contenedores / binario de CNI | El entorno de ejecución invoca CNI para el sandbox de Pod; el plugin de AWS solicita una dirección y configura su espacio de nombres de red. |
| IPAMD | Mantiene pools de direcciones y administra los ENI/IP ordinarios requeridos en nodos EC2 Linux. |
| Controlador de política de red de EKS / agente de nodo | El controlador administrado resuelve puntos de conexión de las políticas; `aws-eks-nodeagent` aplica las políticas admitidas con eBPF cuando está habilitado. |
| Controlador de recursos de VPC | Administra características como interfaces branch/trunk y asignación de direcciones de Windows según sus propios requisitos previos. |

El diagrama anterior etiquetaba el binario de CNI como llamado directamente por kubelet. Kubernetes actual delega la administración de CNI al entorno de ejecución de contenedores.

### Modos de asignación de IP

| Propiedad | Direcciones IPv4 secundarias | Delegación de prefijo |
|---|---|---|
| Asignación | Direcciones secundarias individuales en un ENI | Prefijos IPv4 `/28` con 16 direcciones; IPv6 usa prefijos `/80` |
| Capacidad | Limitada por las ranuras de interfaz/dirección y la configuración de kubelet | Más direcciones por ranura, sujetas al hardware compatible, prefijos libres y límites de kubelet/recursos |
| Contrapartida de asignación | Asignación de direcciones detallada | Asigna un bloque de una vez; los objetivos de reserva pueden reservar direcciones no utilizadas |
| Selección | Úselo según la compatibilidad y la demanda medida | Verifique compatibilidad con Nitro, fragmentación de subred, rotación de cargas de trabajo y combinaciones de características |

La delegación de prefijo no es un requisito universal para un clúster grande y no crea espacio de direcciones en una subred agotada.

## Modelo de red {#networking-model}

### Arquitectura de ENI

Para el modo ordinario de IPv4 secundaria, cada ENI tiene una dirección primaria y direcciones adicionales disponibles para CNI. El ENI primario también transporta la dirección primaria del nodo. Los ENI adicionales pueden proporcionar más direcciones secundarias de Pod. Las redes personalizadas cambian qué interfaces/subredes proporcionan direcciones de Pod; los modos de prefijo y ENI branch tienen reglas de asignación distintas.

```text
Linux EC2 node (ordinary secondary-IPv4 illustration)
├── Primary ENI: node primary IP + secondary IPs for Pods
├── Additional ENI: its primary IP + secondary IPs for Pods
└── Additional ENI: its primary IP + secondary IPs for Pods
```

### Límites de ENI/IP por tipo de instancia

| Tipo de instancia | Cantidad máx. de ENI | Ranuras IPv4 por ENI | maxPods histórico de arranque para el modo de IP secundaria |
|---|---|---|---|
| t3.medium | 3 | 6 | 17 |
| t3.large | 3 | 12 | 35 |
| m5.large | 3 | 10 | 29 |
| m5.xlarge | 4 | 15 | 58 |
| m5.2xlarge | 4 | 15 | 58 |
| c5.4xlarge | 8 | 30 | 234 |
| m5.8xlarge | 8 | 30 | 234 |

El cálculo histórico es **`ENIs × (IPv4 slots per ENI − 1) + 2`**. El `+2` representa los dos Pods de sistema con red de host en ese cálculo de arranque; para m5.large, `3 × 9 + 2 = 29`. No significa que todos los despliegues actuales siempre tengan exactamente dos Pods con red de host.

Estos son valores de arranque históricos, no recomendaciones universales actuales de densidad de Pod. La delegación de prefijo, las redes personalizadas, las interfaces branch, varias tarjetas de red, CPU/memoria y `maxPods` de kubelet son relevantes. Los grupos de nodos administrados de EKS limitan `maxPods` a 110 para instancias con menos de 30 vCPU y a 250 en caso contrario. Inspeccione la capacidad asignable del nodo real.

### Delegación de prefijo

Un fragmento de configuración de complemento administrado de EKS para el modo de prefijo IPv4 de Linux es:

```json
{
  "env": {
    "ENABLE_PREFIX_DELEGATION": "true",
    "WARM_PREFIX_TARGET": "1"
  }
}
```

Fusione esto con la configuración prevista del complemento mediante el procedimiento de administración siguiente. Para una instalación administrada por Helm, el mapeo `env` equivalente pertenece a los valores de Helm. Las ediciones directas de `kubectl set env` pueden ser reconciliadas por el administrador elegido.

La asignación IPv4 necesita bloques `/28` contiguos adecuados, no solo un `AvailableIpAddressCount` positivo. Verifique las reservas/fragmentación de subred y las instancias Nitro admitidas. Habilitar prefijos no aumenta automáticamente el límite de Pods de cada kubelet existente ni el límite de Pods con ENI branch.

## Instalación y configuración {#installation-and-configuration}

### Establezca propiedad y compatibilidad

Use credenciales configuradas de AWS CLI y un contexto de Kubernetes para el clúster previsto. Comience con lecturas:

```bash
EKS_REGION=ap-northeast-2
CLUSTER_NAME=my-cluster
KUBERNETES_MINOR="$(aws eks describe-cluster --region "$EKS_REGION" \
  --name "$CLUSTER_NAME" --query cluster.version --output text)"
aws eks describe-addon-versions --region "$EKS_REGION" \
  --addon-name vpc-cni --kubernetes-version "$KUBERNETES_MINOR"
aws eks describe-addon --region "$EKS_REGION" \
  --cluster-name "$CLUSTER_NAME" --addon-name vpc-cni
kubectl -n kube-system get daemonset aws-node -o yaml
```

Una `ResourceNotFoundException` de EKS para `describe-addon` no demuestra que no haya CNI instalado: puede estar autoadministrado. Inspeccione el DaemonSet, ServiceAccount, releases de Helm, configuración y modelo de IAM existentes antes de elegir **un** administrador. Las redes de Auto Mode no se instalan mediante este flujo de trabajo.

### Complemento administrado de EKS existente

Exporte la configuración existente e inspeccione el esquema de la compilación compatible seleccionada:

```bash
umask 077
aws eks describe-addon --region "$EKS_REGION" \
  --cluster-name "$CLUSTER_NAME" --addon-name vpc-cni > vpc-cni-before.json
jq -r '.addon.configurationValues // "{}"' vpc-cni-before.json > vpc-cni-config.json
: "${VPC_CNI_ADDON_VERSION:?Select a compatible EKS add-on build from the metadata}"
aws eks describe-addon-configuration --region "$EKS_REGION" \
  --addon-name vpc-cni --addon-version "$VPC_CNI_ADDON_VERSION"
```

Revise las versiones intermedias de actualización requeridas y los cambios de release. Edite `vpc-cni-config.json` para conservar la configuración existente prevista e incorporar solo los cambios seleccionados. No suponga que una carga parcial o una marca de conflictos conserve automáticamente cada ajuste. Confirme los permisos de IAM de CNI y su rol configurado de IRSA/Pod Identity; IPv6 necesita los permisos correspondientes.

Para un complemento ya administrado, una actualización revisada puede usar:

```bash
set -eu
VPC_CNI_UPDATE_ID="$(aws eks update-addon --region "$EKS_REGION" \
  --cluster-name "$CLUSTER_NAME" --addon-name vpc-cni \
  --addon-version "$VPC_CNI_ADDON_VERSION" \
  --configuration-values file://vpc-cni-config.json --resolve-conflicts PRESERVE \
  --query update.id --output text)"
aws eks describe-update --region "$EKS_REGION" --name "$CLUSTER_NAME" \
  --addon-name vpc-cni --update-id "$VPC_CNI_UPDATE_ID"
```

`PRESERVE` es una elección explícita de manejo de conflictos; verifique el entorno, las imágenes y el comportamiento resultantes. Vuelva a comprobar el ID de actualización capturado hasta que su estado sea `Successful`; si es `Failed` o `Cancelled`, inspeccione sus errores antes de continuar. Solo entonces compruebe el complemento y DaemonSet resultantes:

```bash
aws eks describe-addon --region "$EKS_REGION" \
  --cluster-name "$CLUSTER_NAME" --addon-name vpc-cni
kubectl -n kube-system rollout status daemonset/aws-node --timeout=10m
```

Una solicitud de API aceptada o el estado listo de un DaemonSet anterior no demuestra que esta actualización y la validación de red hayan terminado.

Para un complemento administrado ausente tras la preparación de instalación/propiedad, la operación de creación es independiente:

```bash
aws eks create-addon --region "$EKS_REGION" \
  --cluster-name "$CLUSTER_NAME" --addon-name vpc-cni \
  --addon-version "$VPC_CNI_ADDON_VERSION" \
  --configuration-values file://vpc-cni-config.json
```

No llame repetidamente a `create-addon` para activar características individuales y no fuerce `OVERWRITE` sobre una instalación personalizada existente sin un plan de migración.

### Instalación administrada por Helm

Fije el chart completo, que también selecciona los componentes init y agente de políticas correspondientes. Sobrescribir solo dos etiquetas de imagen no actualiza el resto del chart:

```bash
helm repo add eks https://aws.github.io/eks-charts
helm repo update eks
helm show values eks/aws-vpc-cni --version 1.23.2 > chart-defaults.yaml
helm template aws-vpc-cni eks/aws-vpc-cni --namespace kube-system \
  --version 1.23.2 -f helm-values.yaml > rendered-cni.yaml
```

Prepare `helm-values.yaml` para la familia de IP real, ServiceAccount/IAM de CNI y las características seleccionadas. Los ejemplos básicos de Linux de esta guía usan IPv4. Revise los recursos renderizados antes de aplicarlos:

```bash
helm upgrade --install aws-vpc-cni eks/aws-vpc-cni --namespace kube-system \
  --version 1.23.2 -f helm-values.yaml --wait --timeout 10m
```

Estos comandos suponen una instalación limpia o administrada por Helm. Los recursos existentes administrados por EKS o propiedad del arranque necesitan una migración de propiedad planificada. Los requisitos previos de acceso a partición/registro de EKS y extracción de imágenes también deben coincidir con el entorno.

### Valores de configuración importantes

| Ajuste | Significado | Distinción de referencia/predeterminado |
|---|---|---|
| `WARM_IP_TARGET` | Direcciones libres deseadas para nuevas asignaciones ordinarias de Pod | No establecido de forma predeterminada; no es un máximo estricto |
| `MINIMUM_IP_TARGET` | Límite inferior para el total de direcciones asignadas | No establecido de forma predeterminada; combínelo con un objetivo positivo de IP libre cuando se use |
| `WARM_ENI_TARGET` | Capacidad de reserva de ENI deseada | Valor predeterminado de la versión publicada: 1; los objetivos de IP lo reemplazan |
| `WARM_PREFIX_TARGET` | Prefijos IPv4 libres deseados | El chart/manifiesto de la versión publicada establece 1; la documentación del daemon sin configuración indica que no está establecido |
| `ENABLE_PREFIX_DELEGATION` | Selecciona la asignación de prefijo | Valor predeterminado del chart de Linux: `"false"` |
| `AWS_VPC_K8S_CNI_CUSTOM_NETWORK_CFG` | Selecciona el comportamiento de redes personalizadas | Predeterminado: `"false"` |
| `ENI_CONFIG_LABEL_DEF` | Clave de etiqueta de nodo que selecciona ENIConfig | Predeterminado del daemon: `k8s.amazonaws.com/eniConfig`; los ejemplos basados en zona lo reemplazan |
| `ENABLE_POD_ENI` | Habilita la integración EC2 Pod-ENI | Predeterminado: `"false"`; aún se aplican otros requisitos previos de SGPP |
| `POD_SECURITY_GROUP_ENFORCING_MODE` | Comportamiento de enrutamiento/SNAT y grupos de seguridad de SGPP | Predeterminado: `strict` |
| `NETWORK_POLICY_ENFORCING_MODE` | Comportamiento de política de red mientras se configuran las reglas de un nuevo Pod | Predeterminado: `standard` |

Los dos ajustes del modo de aplicación de políticas regulan sistemas distintos. Los valores de entorno de las cargas útiles de configuración de EKS son cadenas.

### Redes personalizadas (ENIConfig)

Cree subredes de Pod y grupos de seguridad reales en la VPC/AZ prevista y, a continuación, haga referencia a sus ID:

```yaml
apiVersion: crd.k8s.amazonaws.com/v1alpha1
kind: ENIConfig
metadata:
  name: ap-northeast-2a
spec:
  subnet: subnet-0123456789abcdef0
  securityGroups:
  - sg-0123456789abcdef0
---
apiVersion: crd.k8s.amazonaws.com/v1alpha1
kind: ENIConfig
metadata:
  name: ap-northeast-2b
spec:
  subnet: subnet-0abcdef0123456789
  securityGroups:
  - sg-0123456789abcdef0
```

Habilite las redes personalizadas y use la etiqueta de zona real del nodo:

```json
{
  "env": {
    "AWS_VPC_K8S_CNI_CUSTOM_NETWORK_CFG": "true",
    "ENI_CONFIG_LABEL_DEF": "topology.kubernetes.io/zone"
  }
}
```

Una anotación explícita de nodo ENIConfig tiene precedencia sobre la etiqueta. Los objetos ENIConfig por sí solos no habilitan redes personalizadas. Planifique el enrutamiento, las reglas de DNS/seguridad, la capacidad de direcciones y la transición de cargas de trabajo/nodos; los Pods actuales no se mueven a una nueva subred simplemente porque exista un CIDR o ENIConfig nuevo.

## Administración de direcciones IP {#ip-address-management}

### Ajuste del pool de reserva

Use la demanda y rotación de Pods medidas, el espacio de direcciones disponible y los límites de API de EC2. Estos son objetivos de ejemplo alternativos, no prescripciones basadas solo en el tamaño del clúster:

```json
{
  "env": {
    "WARM_IP_TARGET": "2",
    "MINIMUM_IP_TARGET": "4"
  }
}
```

```json
{
  "env": {
    "WARM_IP_TARGET": "5",
    "MINIMUM_IP_TARGET": "10"
  }
}
```

`MINIMUM_IP_TARGET` es un límite inferior de asignación total; `WARM_IP_TARGET` se dirige a direcciones libres. Tienen precedencia sobre la estrategia de objetivos de reserva de ENI/prefijo. Con delegación de prefijo, las asignaciones aún ocurren en unidades de tamaño de prefijo. Más capacidad de reserva puede reducir las esperas de asignación, pero consume direcciones, y los cambios agresivos pueden aumentar las llamadas a API.

### Adición de un CIDR secundario

Primero revise las asociaciones existentes, la superposición con redes conectadas, las restricciones de CIDR de VPC y los requisitos de subred/enrutamiento:

```bash
VPC_ID=vpc-0123456789abcdef0
aws ec2 describe-vpcs --region "$EKS_REGION" --vpc-ids "$VPC_ID" \
  --query 'Vpcs[0].CidrBlockAssociationSet'
```

Lo siguiente usa ID y espacio de direcciones ilustrativos; realícelo únicamente como parte del plan de VPC revisado:

```bash
aws ec2 associate-vpc-cidr-block --region "$EKS_REGION" \
  --vpc-id "$VPC_ID" --cidr-block 100.64.0.0/16
aws ec2 describe-vpcs --region "$EKS_REGION" --vpc-ids "$VPC_ID" \
  --query 'Vpcs[0].CidrBlockAssociationSet'
```

Confirme que la nueva asociación CIDR esté **associated**, en vez de aún asociándose, antes de crear una subred en ella:

```bash
aws ec2 create-subnet --region "$EKS_REGION" --vpc-id "$VPC_ID" \
  --cidr-block 100.64.0.0/19 --availability-zone ap-northeast-2a
```

La subred también necesita su tabla de rutas prevista, reglas de seguridad y selección de CNI. Los Pods existentes conservan sus redes actuales hasta la transición planificada. RFC 6598 `100.64.0.0/10` es espacio de direcciones compartido, no capacidad privada única globalmente; compruebe superposiciones con todos los entornos conectados.

### Configuración del clúster IPv6

La familia de IP se selecciona al crear el clúster y no puede cambiarse después. La interfaz oficial de `eksctl` usa un **archivo de configuración**, no una marca `--ip-family`. Un ejemplo de esquema es:

```yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: ipv6-example
  region: ap-northeast-2
  version: '1.35'
kubernetesNetworkConfig:
  ipFamily: IPv6
iam:
  withOIDC: true
addons:
- name: vpc-cni
- name: coredns
- name: kube-proxy
managedNodeGroups:
- name: linux-nitro
  amiFamily: AmazonLinux2023
  instanceType: m5.large
  desiredCapacity: 2
  privateNetworking: true
```

Sustituya la versión/región de ejemplo, elija imágenes de nodo compatibles y revise la configuración de endpoint/acceso de VPC e IAM antes de la creación. Las versiones de complementos omitidas aquí se resuelven mediante la ruta compatible de EKS/eksctl; inspeccione y fije las compilaciones compatibles requeridas para un despliegue controlado. `iam.withOIDC` y los complementos/grupo de nodos administrados reflejan los requisitos previos de IPv6 de eksctl documentados.

```bash
eksctl create cluster --config-file ipv6-cluster.yaml
```

Esta auditoría no creó un clúster. Las comprobaciones locales de ayuda/esquema de CLI usaron eksctl 0.229.0; no son una validación en vivo de las redes, IAM ni de las compilaciones disponibles en la región.

IPv6 requiere rutas Linux Nitro/Fargate compatibles y asignación de prefijo; Windows no es compatible. Los Pods IPv6 pueden tener una interfaz auxiliar de salida IPv4. El agente de políticas documenta que la política IPv6 en la interfaz primaria no protege el tráfico IPv4 de ese asistente. Si el diseño requiere eliminar esa ruta, revise `ENABLE_V4_EGRESS`, las dependencias y el despliegue gradual de Pods en lugar de suponer que la política IPv6 por sí sola la bloquea.

## Compatibilidad con NetworkPolicy {#network-policy-support}

### Aplicación nativa

La compatibilidad nativa estándar con políticas eBPF se introdujo en VPC CNI 1.14. La documentación actual de EKS incluye VPC CNI 1.21.0 o posterior tanto para `NetworkPolicy` estándar como para `ClusterNetworkPolicy` de administración ([requisitos de política de red de EKS](https://docs.aws.amazon.com/eks/latest/userguide/cni-network-policy.html)); la referencia 1.23 revisada aún debe coincidir con el clúster y la plataforma.

```json
{
  "enableNetworkPolicy": "true"
}
```

`"enableNetworkPolicy": "true"` es la configuración documentada con valores de cadena. Los nodos EC2 Linux compatibles pueden usar esta implementación; Fargate y Windows no usan su aplicación. Auto Mode tiene su propia implementación administrada. Los controles Admin/Baseline de EKS `ClusterNetworkPolicy` y `ApplicationNetworkPolicy` de DNS de Auto Mode son extensiones, no alias de `NetworkPolicy` estándar.

En modo estándar, los Pods nuevos permiten inicialmente el tráfico mientras se resuelven las reglas de política. Se puede seleccionar deliberadamente un comportamiento de inicio más estricto:

```json
{
  "enableNetworkPolicy": "true",
  "env": {
    "NETWORK_POLICY_ENFORCING_MODE": "strict"
  }
}
```

El modo estricto requiere cobertura de política correcta para DNS y otro tráfico necesario antes de iniciar las cargas de trabajo. No configura el `POD_SECURITY_GROUP_ENFORCING_MODE` independiente de SGPP.

### Ejemplo de NetworkPolicy

Requisitos previos: el espacio de nombres `app` contiene cargas de trabajo frontend/backend administradas por un controlador; los Pods backend escuchan en TCP 8080. AWS documenta actualmente que `metadata.ownerReferences` es importante para una aplicación confiable y requiere números de puerto de Service/contenedor coincidentes (y nombres coincidentes para puertos con nombre).

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-frontend-to-backend
  namespace: app
spec:
  podSelector:
    matchLabels:
      app: backend
  policyTypes:
  - Ingress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: frontend
    ports:
    - protocol: TCP
      port: 8080
```

El selector de Pod de origen se limita al mismo espacio de nombres. Esta regla aísla el tráfico de entrada al backend seleccionado y permite tráfico frontend coincidente hacia 8080; no deniega el tráfico de salida del backend ni autentica a un usuario de aplicación. Considere otras políticas coincidentes y el comportamiento del nivel Admin. Valide tanto los flujos permitidos como los denegados con Pods administrados por Deployment/Job en lugar de depender de Pods de diagnóstico independientes.

### Verificación y diagnóstico

```bash
kubectl -n kube-system logs -l k8s-app=aws-node -c aws-eks-nodeagent --tail=200
kubectl get networkpolicy -A
kubectl get policyendpoints.networking.k8s.aws -A
```

Estos son logs de **node-agent**; el controlador de política se ejecuta en el plano de control administrado por EKS. Los objetos PolicyEndpoint son estado generado, no objetos para editar/eliminar sin cuidado.

En un nodo Linux autorizado con la CLI de política instalada:

```bash
sudo /opt/cni/bin/aws-eks-na-cli ebpf progs
sudo /opt/cni/bin/aws-eks-na-cli ebpf maps
```

La herramienta es `aws-eks-na-cli`, no `ebpf-sdk list-maps`. Inspeccione el nodo afectado y distinga los logs de proceso de los logs de eventos de política configurados y la entrega a CloudWatch. Habilitar la entrega de logs externa también requiere la IAM/configuración adecuada.

## Características avanzadas {#advanced-features}

### Security Groups for Pods

Los grupos de seguridad seleccionados ya deben existir con reglas adecuadas de DNS, API, aplicación y ruta de retorno:

```yaml
apiVersion: vpcresources.k8s.aws/v1beta1
kind: SecurityGroupPolicy
metadata:
  name: my-security-group-policy
  namespace: app
spec:
  podSelector:
    matchLabels:
      app: database
  securityGroups:
    groupIds:
    - sg-0123456789abcdef0
    - sg-0abcdef0123456789
```

Una configuración de ejemplo de **EC2** que selecciona el comportamiento SGPP estándar es:

```json
{
  "env": {
    "ENABLE_POD_ENI": "true",
    "POD_SECURITY_GROUP_ENFORCING_MODE": "standard"
  }
}
```

Esta no es una instalación SGPP completa. Verifique tipos de instancia compatibles con trunking, permisos de VPC resource-controller del rol de clúster, permisos de CNI, capacidad de subred y los requisitos previos pertinentes de EKS. Las instancias de familia T no son compatibles con trunking solo por estar basadas en Nitro. Los Pods seleccionados recién creados/recreados reciben la configuración prevista.

El controlador de recursos administrado adjunta una **ENI troncal adicional** y le asocia ENI branch. La interfaz troncal no es la ENI `eth0` primaria del nodo. Un Pod seleccionado usa una interfaz branch con sus grupos de seguridad; la delegación de prefijo no aumenta el límite de Pods branch. Los grupos de seguridad de Fargate usan su ruta administrada independiente.

| Modo / característica | Consecuencia que se debe verificar |
|---|---|
| SGPP `strict` | Comportamiento de los grupos de seguridad de la interfaz branch y ausencia de NAT de origen del Pod; NodeLocal DNSCache y LoadBalancer/NodePort con destino de instancia y `externalTrafficPolicy: Local` tienen restricciones documentadas |
| SGPP `standard` | Admite las rutas combinadas de política/DNS documentadas; con el comportamiento de SNAT externo predeterminado, el tráfico fuera de la VPC usa la dirección IP primaria y los grupos de seguridad del nodo |
| Redes personalizadas más SGPP | Los grupos de seguridad de los Pods tienen precedencia sobre los grupos de seguridad de ENIConfig |
| IPv6 | Compatible con la guía de servicio de EKS según sus condiciones de versión/plataforma, incluido EC2 CNI 1.16+; la celda «No» de la tabla de características de README anterior no debe reemplazar esa guía detallada |
| Windows / Auto Mode | Este mecanismo SGPP no es compatible; Auto Mode tiene controles de red de node class independientes |

Los cambios de modo afectan a los Pods recién lanzados; planifique su recreación y verifique la ruta de tráfico. No suponga que los mismos grupos de seguridad controlan cada paquete después de SNAT.

### Interfaces múltiples y Multus

VPC CNI 1.20+ tiene compatibilidad nativa multi-NIC para instancias adecuadas con varias tarjetas de red. Su `ENABLE_MULTI_NIC` y la configuración de NIC de Pod son distintos de Multus, y las aplicaciones deben usar las interfaces adicionales para obtener sus ventajas.

Multus es un meta-plugin. La disposición Multus admitida por AWS usa VPC CNI como el **delegado primario**; usar VPC CNI para interfaces de orden superior no es compatible. Las interfaces adicionales necesitan su propio plugin compatible, asignación de direcciones y administración de ciclo de vida.

| Requisito de interfaz adicional | Por qué es importante |
|---|---|
| Interfaz dedicada e identificada | Un `eth1` codificado de forma fija puede referirse a una interfaz administrada por IPAMD |
| `node.k8s.amazonaws.com/no_manage=true` en el ENI adicional | Impide que VPC CNI administre la interfaz Multus |
| Direcciones asignadas/enrutables por AWS y subred/SG/rutas correctas | Una asignación arbitraria `192.168.1.0/24` no es automáticamente válida en un ENI EC2 |
| IPAM coordinado | Un rango compartido de `host-local` puede asignar duplicados en nodos diferentes |
| Pruebas de política específicas de interfaz | Las interfaces adicionales y las rutas auxiliares IPv4 no están cubiertas automáticamente por toda política de la interfaz primaria |

El `spec.config` de NetworkAttachmentDefinition contiene el JSON de CNI elegido, incluida su versión compatible, plugin, interfaz principal real y configuración de IPAM. El manifiesto genérico anterior de `ipvlan`/`eth1`/`host-local` omitía los requisitos previos anteriores y se ha reemplazado por estos requisitos de implementación. Esta guía no afirma una solución Multus/IPAM desplegada.

### Windows

Windows usa la ruta IPAM de VPC resource-controller. Prepare los permisos del rol de clúster, la autenticación/entrada de acceso del rol de nodo Windows (`EC2_WINDOWS` cuando corresponda), y capacidad Linux/Fargate para CoreDNS. Windows Fargate, Auto Mode, Hybrid Nodes, IPv6, redes personalizadas, SGPP y la política de red nativa de VPC-CNI tienen restricciones documentadas.

El ConfigMap resultante del controlador debe incluir la siguiente entrada IPAM de Windows. Esto muestra los datos requeridos, no una instrucción para sobrescribir un ConfigMap propiedad de un administrador:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: amazon-vpc-cni
  namespace: kube-system
data:
  enable-windows-ipam: 'true'
```

Para una instalación **administrada por Helm**, los objetivos de prefijo de Windows usan claves distintas de Linux:

```yaml
enableWindowsIpam: 'true'
enableWindowsPrefixDelegation: 'true'
warmWindowsPrefixTarget: 1
warmWindowsIPTarget: 0
minimumWindowsIPTarget: 0
```

Revise el esquema de la compilación correspondiente, la propiedad de los campos y el ConfigMap resultante. No suponga que un valor de Helm se acepta sin cambios como propiedad de configuración de complemento de EKS. Las marcas de chart de Windows se asignan a `enable-windows-ipam` y `enable-windows-prefix-delegation`; los campos de objetivos de reserva también son específicos de Windows aquí.

Tras esos requisitos previos y las comprobaciones de AMI/versión, un comando de grupo de nodos puede usar:

```bash
eksctl create nodegroup --region "$EKS_REGION" --cluster "$CLUSTER_NAME" \
  --name windows-example --managed --node-type m5.large --nodes 2 \
  --node-ami-family WindowsServer2022FullContainer
```

El modo de IP secundaria de Windows normalmente usa un ENI y su límite de ranuras de dirección, no la fórmula Linux de múltiples ENI. La delegación de prefijo y los límites reales de kubelet necesitan un dimensionamiento independiente.

## Solución de problemas {#troubleshooting}

### Asignación de IP y programación

Compruebe los eventos de Pod para distinguir un fallo de programación de un fallo de asignación de sandbox/CNI:

```bash
kubectl -n kube-system logs -l k8s-app=aws-node -c aws-node --tail=300
kubectl get nodes -o json | jq '.items[] | {name: .metadata.name, allocatablePods: .status.allocatable.pods}'
SUBNET_ID=subnet-0123456789abcdef0
aws ec2 describe-subnets --region "$EKS_REGION" --subnet-ids "$SUBNET_ID" \
  --query 'Subnets[].{SubnetId:SubnetId,AvailableIPs:AvailableIpAddressCount}'
```

`allocatablePods` es capacidad de programación de kubelet, no utilización actual de IP. El recuento de direcciones disponibles de subred no muestra si hay un `/28` contiguo disponible. Compruebe los logs de IPAMD, el modo de asignación, los objetivos de reserva, los límites de ENI, los errores de API y el nodo afectado antes de elegir una solución.

### Recuento de ENI

```bash
INSTANCE_ID=i-0123456789abcdef0
aws ec2 describe-instances --region "$EKS_REGION" --instance-ids "$INSTANCE_ID" \
  --query 'Reservations[].Instances[].{InstanceId:InstanceId,AttachedENIs:length(NetworkInterfaces)}'
aws ec2 describe-instance-types --region "$EKS_REGION" --instance-types m5.large \
  --query 'InstanceTypes[].NetworkInfo.{MaxENI:MaximumNetworkInterfaces,IPv4PerENI:Ipv4AddressesPerInterface}'
```

La proyección original contaba una lista anidada de interfaces en lugar de las interfaces mismas. La consulta corregida informa un recuento por instancia. Varias tarjetas, interfaces no administradas/trunk y límites específicos de instancia aún necesitan interpretación.

### Introspección y métricas

Seleccione el Pod `aws-node` real del nodo afectado y mantenga abierta esta sesión de reenvío:

```bash
kubectl -n kube-system get pods -l k8s-app=aws-node -o wide
AWS_NODE_POD=aws-node-example
kubectl -n kube-system port-forward "pod/$AWS_NODE_POD" 61678:61678 61679:61679
```

Desde otra terminal local:

```bash
curl --fail http://127.0.0.1:61679/v1/enis
curl --fail http://127.0.0.1:61678/metrics
```

La introspección de IPAMD usa de forma predeterminada la interfaz de loopback **61679**; las métricas de Prometheus usan **61678**. `/v1/enis` no es un endpoint de métricas. Estos comandos usan curl local a través de la ruta de reenvío de Kubernetes; no requieren un binario curl dentro de la imagen de CNI.

### Clasifique los errores antes de cambiar el clúster

| Observación | Investigue antes de actuar |
|---|---|
| `InsufficientFreeAddressesInSubnet` | Direcciones libres reales, asignación de reserva, subredes seleccionadas y expansión de capacidad planificada |
| `InsufficientCidrBlocks` | Disponibilidad/fragmentación de prefijo contiguo y reservas de subred |
| Error de límite de ENI/SG | La cuota específica, tipo de instancia/interfaz y objetos en uso; evite eliminar grupos de seguridad no relacionados |
| Fallo de creación de ENI | Error detallado de AWS, rol de credenciales de CNI, permisos/condiciones, cuota y conectividad de API |
| Esperando una IP de Pod | Estado de IPAMD, retrasos de controlador/API, limitación, eventos de sandbox y disponibilidad de direcciones |

Reiniciar IPAMD, aumentar una instancia o conceder más permisos de rol de nodo no es una solución universal. Capture primero la evidencia y aplique un cambio revisado al componente que realmente posee la operación fallida.

## Prácticas recomendadas {#best-practices}

Planifique la capacidad de subred según los Pods esperados, pools de reserva, crecimiento y solapamiento de fallo/reemplazo. Un rango `/19` o RFC 6598 es una elección de diseño de ejemplo, no un requisito universal. Asocie CIDR nuevos, cree las subredes/rutas necesarias y planifique conjuntamente la adopción de CNI/cargas de trabajo.

Elija una estrategia de pool de reserva. Un ejemplo IPv4 de prefijo que usa objetivos de IP libres e IP totales es:

```json
{
  "env": {
    "ENABLE_PREFIX_DELEGATION": "true",
    "WARM_IP_TARGET": "5",
    "MINIMUM_IP_TARGET": "10"
  }
}
```

No interprete un `WARM_PREFIX_TARGET` adicional como un objetivo efectivo independiente cuando se establecen esos objetivos de IP. Supervise los fallos de asignación y las restricciones reales de recursos en vez de inferir seguridad únicamente a partir del tamaño del clúster.

### Métricas y alertas

El código IPAMD publicado exporta `awscni_total_ip_addresses`, `awscni_assigned_ip_addresses` y el contador `awscni_no_available_ip_addresses`. Las métricas tipo gauge de total/asignado describen el **pool de direcciones asignadas por IPAMD**, no el espacio total de direcciones de las subredes de la VPC. Objetivos de reserva pequeños pueden producir legítimamente una proporción asignado/total alta; el período de enfriamiento, las interfaces branch, la familia de IP y la capacidad de kubelet necesitan contexto adicional.

Los CRD y selectores de Prometheus Operator ya deben estar configurados. En una instalación de CNI administrada por Helm, el chart puede crear un PodMonitor con este **ejemplo de clúster IPv4**:

```yaml
podMonitor:
  create: true
  labels:
    release: prometheus
  interval: 30s
  relabelings:
  - sourceLabels:
    - __meta_kubernetes_pod_node_name
    targetLabel: node
  - targetLabel: cluster
    replacement: example-cluster
  - targetLabel: ip_family
    replacement: ipv4
  - targetLabel: job
    replacement: aws-vpc-cni
```

Sustituya la etiqueta de clúster de ejemplo, adapte el selector `release` y establezca las etiquetas de familia de IP de forma veraz; las etiquetas no detectan la familia del clúster. El chart recopila el puerto nombrado `metrics` del agente y el puerto `agentmetrics` del agente de políticas habilitado. Un complemento administrado de EKS necesita un scraper/PodMonitor configurado de forma independiente en lugar de instalar un segundo release Helm de CNI.

```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: vpc-cni-signals
  namespace: monitoring
  labels:
    release: prometheus
spec:
  groups:
  - name: vpc-cni
    rules:
    - record: vpc_cni:allocated_ipv4_pool_utilization:ratio
      expr: (awscni_assigned_ip_addresses{job="aws-vpc-cni",ip_family="ipv4"} / awscni_total_ip_addresses{job="aws-vpc-cni",ip_family="ipv4"})
        and (awscni_total_ip_addresses{job="aws-vpc-cni",ip_family="ipv4"} > 0)
    - alert: CniHighAllocatedIPv4PoolUtilization
      expr: vpc_cni:allocated_ipv4_pool_utilization:ratio > 0.9
      for: 5m
      labels:
        severity: info
      annotations:
        summary: Most currently allocated IPAMD IPv4 addresses are assigned
        description: This is allocated-pool utilization, not subnet exhaustion. Check
          warm targets, assignment failures and available subnet space.
    - alert: CniIPAssignmentFailures
      expr: increase(awscni_no_available_ip_addresses{job="aws-vpc-cni"}[5m]) > 0
      for: 1m
      labels:
        severity: warning
      annotations:
        summary: IPAMD could not assign an available IP address
    - alert: CniMetricsScrapeFailed
      expr: up{job="aws-vpc-cni"} == 0
      for: 5m
      labels:
        severity: warning
      annotations:
        summary: A known CNI metrics endpoint cannot be scraped
```

La proporción de pool se limita a IPv4 y a un denominador positivo observado. Es una señal informativa de ajuste, no una prueba de agotamiento de subred. El contador de fallos de asignación señala una asignación fallida real. Una recopilación fallida es distinta de un objetivo desaparecido; compare por separado el inventario esperado de nodos/componentes. La ausencia de datos no equivale a un estado saludable con valor cero. Ajuste los umbrales, etiquetas y el enrutamiento de notificaciones en el entorno de monitorización real.

## Referencias

- [Documentación de VPC CNI 1.23.2](https://raw.githubusercontent.com/aws/amazon-vpc-cni-k8s/v1.23.2/README.md)
- [Valores de Helm de VPC CNI](https://raw.githubusercontent.com/aws/amazon-vpc-cni-k8s/v1.23.2/charts/aws-vpc-cni/values.yaml)
- [Metadatos de versión de chart](https://raw.githubusercontent.com/aws/amazon-vpc-cni-k8s/v1.23.2/charts/aws-vpc-cni/Chart.yaml)
- [Manifiesto de CNI publicado](https://raw.githubusercontent.com/aws/amazon-vpc-cni-k8s/v1.23.2/config/master/aws-k8s-cni.yaml)
- [Implementación de IPAMD](https://raw.githubusercontent.com/aws/amazon-vpc-cni-k8s/v1.23.2/pkg/ipamd/ipamd.go)
- [Servidor de introspección de IPAMD](https://raw.githubusercontent.com/aws/amazon-vpc-cni-k8s/v1.23.2/pkg/ipamd/introspect.go)
- [Datastore IPAM](https://raw.githubusercontent.com/aws/amazon-vpc-cni-k8s/v1.23.2/pkg/ipamd/datastore/data_store.go)
- [Definiciones de métricas de IPAMD](https://raw.githubusercontent.com/aws/amazon-vpc-cni-k8s/v1.23.2/utils/prometheusmetrics/prometheusmetrics.go)
- [Agente de políticas de red 1.4.3](https://github.com/aws/aws-network-policy-agent/blob/v1.4.3/README.md)
- [Índice de chart de AWS Helm](https://aws.github.io/eks-charts/index.yaml)
- [Grupos de seguridad de EKS para Pods](https://docs.aws.amazon.com/eks/latest/userguide/security-groups-for-pods.html)
- [Consideraciones operativas de SGPP](https://docs.aws.amazon.com/eks/latest/best-practices/sgpp.html)
- [Límites de compatibilidad de EKS Multus](https://docs.aws.amazon.com/eks/latest/userguide/pod-multus.html)
- [Redes de EKS Windows](https://docs.aws.amazon.com/eks/latest/userguide/windows-support.html)
- [Compatibilidad IPv6 de EKS](https://docs.aws.amazon.com/eks/latest/userguide/cni-ipv6.html)
- [Configuración IPv6 de eksctl](https://docs.aws.amazon.com/eks/latest/eksctl/vpc-ip-family.html)
- [Configuración IAM de CNI](https://docs.aws.amazon.com/eks/latest/userguide/cni-iam-role.html)
- [Administración de EKS VPC CNI](https://docs.aws.amazon.com/eks/latest/userguide/managing-vpc-cni.html)
- [Condiciones de política de red de EKS](https://docs.aws.amazon.com/eks/latest/userguide/cni-network-policy.html)
- [Habilitar política de red de EKS](https://docs.aws.amazon.com/eks/latest/userguide/cni-network-policy-configure.html)
- [Asignación de prefijo y límites de capacidad de Pod](https://docs.aws.amazon.com/eks/latest/userguide/cni-increase-ip-addresses-procedure.html)

## Cuestionario

Compruebe sus conocimientos con el [Cuestionario de VPC CNI](../quizzes/networking/01-vpc-cni-quiz.md).
