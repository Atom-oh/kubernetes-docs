# Parte 8: integración con EKS

> **Versiones de referencia revisadas**: Calico 3.32.2 / Tigera Operator 1.42.6 / Kubernetes 1.34–1.36, probado por Calico. **Última actualización**: 12 de octubre de 2026

## Descripción general

Esta guía utiliza Calico para aplicar políticas en **nodos de trabajo Linux en EC2 con Amazon VPC CNI**. VPC CNI asigna las IP de los Pods y configura la conectividad de VPC; Calico establece las reglas de política en el plano de datos del nodo. La instalación siguiente mantiene el plano de datos Iptables y kube-proxy. Utilizar la red de Calico o su plano de datos eBPF son opciones de despliegue independientes, con requisitos adicionales.

En la fecha de esta revisión, EKS ofrece soporte estándar para 1.34–1.37 y soporte extendido para 1.31–1.33 ([ciclo de vida de versiones de Kubernetes de EKS](https://docs.aws.amazon.com/eks/latest/userguide/kubernetes-versions.html)). El rango de versiones de Kubernetes que Calico 3.32 declara haber probado es 1.34–1.36. Compruebe por separado la disponibilidad de EKS, las versiones publicadas de Kubernetes y la compatibilidad de Calico: que EKS ofrezca 1.37 no significa que Calico 3.32 la haya probado. Antes de instalar, confirme las versiones de EKS y de sus complementos en la región de destino.

## Arquitectura de VPC CNI + Calico

![VPC CNI gestiona las interfaces de los Pods y la asignación de IP de VPC, mientras que Felix configura las reglas de política del plano de datos del nodo. Las flechas muestran relaciones de control y configuración, no el recorrido de los paquetes a través de esos procesos.](../../.gitbook/assets/en-networking-calico-08-eks-integration-0.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-networking-calico-08-eks-integration-0.html)

La figura resume las responsabilidades de los componentes. Los paquetes no pasan por el contenedor pause ni por el proceso Felix como si fueran proxies de reenvío. Felix configura reglas que evalúa el kernel de Linux. La etiqueta `iptables / eBPF` representa planos de datos alternativos; esta guía instala Iptables. Typha y kube-controllers se ejecutan en los nodos de trabajo del cliente, no en el plano de control de EKS gestionado por AWS.

| Componente | Responsabilidad en esta configuración |
| --- | --- |
| `aws-node` / IPAMD y plugin VPC CNI | Gestionar las ENI y la asignación de IP, y configurar la conectividad de los Pods |
| Felix en `calico-node` | Configurar las reglas de política de los endpoints locales |
| Typha | Distribuir a Felix las actualizaciones del almacén de datos; el operador gestiona su escalado |
| kube-controllers | Sincronizar los datos de Calico con los recursos de Kubernetes |
| kube-proxy | Proporcionar el reenvío de tráfico de los Services de Kubernetes en esta configuración de referencia |

Para el tráfico entre nodos, el kernel evalúa la política aplicable y utiliza la ruta de VPC. El tráfico entre Pods del mismo nodo puede permanecer en ese host. Un paquete descartado se elimina; una denegación por política no lo devuelve al remitente. Tanto las reglas de salida del origen como las de entrada del destino deben permitir la conexión.

## Elegir un motor de políticas y método de instalación

| Opción | Qué instala | Ciclo de vida y alcance |
| --- | --- | --- |
| Política de red de Amazon VPC CNI | La implementación de políticas de AWS | Configure el complemento `vpc-cni` compatible; no instala Calico |
| Manifiestos de Tigera Operator | El operador y los recursos personalizados de Calico | Fije la versión, gestione los CRDs y después deje que el operador aplique la Installation |
| Chart de Helm de Tigera Operator | El mismo operador, con configuración gestionada por Helm | Genere y revise los manifiestos; para actualizar, utilice la instalación existente de Helm |
| Manifiestos directos de Calico | Los componentes de Calico sin el operador | Conserve las adaptaciones de la plataforma y gestione el procedimiento de actualización |

Los complementos de EKS no se actualizan automáticamente al publicarse una versión nueva ni al cambiar la versión menor del clúster. Los complementos de AWS, Marketplace y la comunidad tienen, además, distintos responsables de soporte. Compruebe el catálogo real, el editor, la versión, la licencia y la compatibilidad con el tipo de cómputo: no dé por hecho que existe un complemento llamado `calico` ni que un producto de Marketplace equivale a esta instalación OSS.

**Utilice un único motor de políticas de red para los mismos endpoints.** La guía de Calico para EKS exige deshabilitar la política de red de AWS VPC CNI. La migración requiere planificar y revisar la transición de las políticas, el estado de los nodos y la disponibilidad; cambiar un indicador mientras ambos motores siguen ejecutándose no constituye un procedimiento de migración. AWS advierte que pueden quedar reglas después de retirar un agente de políticas y recomienda reemplazar los nodos afectados al migrar desde un motor de terceros. Consulte las [consideraciones sobre políticas de AWS](https://docs.aws.amazon.com/eks/latest/userguide/cni-network-policy.html) y el [procedimiento para deshabilitarlas](https://docs.aws.amazon.com/eks/latest/userguide/network-policy-disable.html).

## Preparar la instalación existente de VPC CNI

Los comandos siguientes inspeccionan un complemento gestionado `vpc-cni` existente. Utilice la región y el nombre reales del clúster. Si VPC CNI se gestiona de forma independiente, modifíquelo mediante los manifiestos o la instalación de Helm que ya lo gestionan.

```bash
EKS_CLUSTER=my-cluster
EKS_REGION=us-east-1
EKS_VERSION=$(aws eks describe-cluster --name "$EKS_CLUSTER" \
  --region "$EKS_REGION" --query cluster.version --output text)

aws eks describe-addon-versions --addon-name vpc-cni \
  --kubernetes-version "$EKS_VERSION" --region "$EKS_REGION" \
  --query 'addons[0].addonVersions[].{version:addonVersion,compatibility:compatibilities,compute:computeTypes}'

aws eks describe-addon --cluster-name "$EKS_CLUSTER" \
  --addon-name vpc-cni --region "$EKS_REGION" > vpc-cni-current.json

VPC_CNI_VERSION=$(jq -r '.addon.addonVersion' vpc-cni-current.json)
aws eks describe-addon-configuration --addon-name vpc-cni \
  --addon-version "$VPC_CNI_VERSION" --region "$EKS_REGION" \
  --query configurationSchema --output text > vpc-cni-schema.json
```

Calico requiere `ANNOTATE_POD_IP=true` para que VPC CNI publique sin demora `vpc.amazonaws.com/pod-ips`. El ServiceAccount `aws-node` necesita permiso para modificar los Pods mediante patch. La documentación actual de VPC CNI indica que el complemento de EKS actualiza este permiso automáticamente; compruébelo sin sobrescribir el ClusterRole existente:

```bash
kubectl auth can-i patch pods --all-namespaces \
  --as=system:serviceaccount:kube-system:aws-node
```

Esta comprobación exige permiso para actuar como ese ServiceAccount. Si falta el permiso necesario para modificar los Pods, un binding adicional puede concederlo sin sustituir las reglas existentes. En una instalación no estándar, utilice el nombre real de su ServiceAccount.

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: calico-vpc-pod-annotations
rules:
  - apiGroups: [""]
    resources: ["pods"]
    verbs: ["patch"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: calico-vpc-pod-annotations
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: calico-vpc-pod-annotations
subjects:
  - kind: ServiceAccount
    name: aws-node
    namespace: kube-system
```

Para la **configuración nueva o ya limitada a políticas** que se revisó, prepare la siguiente propuesta conservando los ajustes actuales del complemento:

```bash
jq '(.addon.configurationValues // "") as $current
  | (if $current == "" then {} else ($current | fromjson) end)
  | .enableNetworkPolicy = "false"
  | .env.ANNOTATE_POD_IP = "true"
  | del(.env.NETWORK_POLICY_ENFORCING_MODE)' \
  vpc-cni-current.json > vpc-cni-calico.json
```

Este comando espera valores de configuración en JSON. Si los existentes están en YAML, conviértalos antes de preparar la propuesta, conservando todos los campos, y deténgase si falla el análisis. Valide la propuesta con el esquema obtenido para esa versión del complemento de EKS y revise los cambios. `NETWORK_POLICY_ENFORCING_MODE` pertenece al agente de políticas de AWS; mantenerla configurada cuando el agente no está presente puede impedir la creación de Pods. Si la política de AWS está activa, complete el plan de migración antes de utilizar esta propuesta. Aplique la configuración aprobada mediante el mecanismo que ya gestiona el complemento:

```bash
aws eks update-addon --cluster-name "$EKS_CLUSTER" \
  --addon-name vpc-cni --region "$EKS_REGION" \
  --configuration-values file://vpc-cni-calico.json \
  --resolve-conflicts PRESERVE
```

Revise el estado de la actualización y el DaemonSet resultante. Conservar un conflicto puede impedir que se aplique el campo deseado. Analizar correctamente el JSON o aceptar una solicitud de actualización no demuestra que las políticas se estén aplicando.

## Instalar Calico con el operador

Para una instalación nueva, elija **una** de las opciones siguientes: manifiestos o Helm. No instale un segundo operador sobre una instalación existente. Los ejemplos requieren nodos de trabajo Linux en EC2, acceso a la API y al DNS de Kubernetes, una versión compatible de VPC CNI y la ausencia de otro motor de políticas.

### Instalación mediante manifiestos del operador

Calico 3.32 separa los CRD de Calico del manifiesto del operador:

```bash
kubectl create -f https://raw.githubusercontent.com/projectcalico/calico/v3.32.2/manifests/v1_crd_projectcalico_org.yaml
kubectl create -f https://raw.githubusercontent.com/projectcalico/calico/v3.32.2/manifests/tigera-operator.yaml
```

Guarde lo siguiente como `calico-eks-installation.yaml`:

```yaml
apiVersion: operator.tigera.io/v1
kind: Installation
metadata:
  name: default
spec:
  kubernetesProvider: EKS
  cni:
    type: AmazonVPC
  calicoNetwork:
    bgp: Disabled
    linuxDataplane: Iptables
  nodeUpdateStrategy:
    type: RollingUpdate
    rollingUpdate:
      maxUnavailable: 1
---
apiVersion: operator.tigera.io/v1
kind: APIServer
metadata:
  name: default
spec: {}
---
apiVersion: operator.tigera.io/v1
kind: Goldmane
metadata:
  name: default
spec: {}
---
apiVersion: operator.tigera.io/v1
kind: Whisker
metadata:
  name: default
spec: {}
```

```bash
kubectl apply -f calico-eks-installation.yaml
kubectl get tigerastatus
kubectl get pods -n calico-system
```

El servidor de API, el agregador de flujos Goldmane y la interfaz Whisker están disponibles en OSS. Configure el acceso y la capacidad de recursos para su entorno. `cni.type: AmazonVPC` delega IPAM y la conectividad en VPC CNI; `bgp: Disabled` por sí solo no selecciona la CNI. Deje que el operador gestione las réplicas de Typha: `typhaDeployment.spec.replicas` no es un ajuste admitido de Installation. Consulte los [detalles de escalado](07-advanced-topics.md).

### Instalación mediante Helm

Guarde lo siguiente como `calico-eks-values.yaml`. `installation` corresponde a la API Installation. El `nodeSelector` del nivel superior controla el Pod del operador, no todos los componentes de Calico. Helm puede ignorar los valores no admitidos sin avisar; revise los manifiestos generados.

```yaml
installation:
  enabled: true
  kubernetesProvider: EKS
  cni:
    type: AmazonVPC
  calicoNetwork:
    bgp: Disabled
    linuxDataplane: Iptables
  nodeUpdateStrategy:
    type: RollingUpdate
    rollingUpdate:
      maxUnavailable: 1
apiServer:
  enabled: true
goldmane:
  enabled: true
whisker:
  enabled: true
manageCRDs: true
```

```bash
helm repo add projectcalico https://docs.tigera.io/calico/charts
helm repo update projectcalico
helm template calico projectcalico/tigera-operator \
  --version v3.32.2 --namespace tigera-operator \
  -f calico-eks-values.yaml > calico-rendered.yaml

# After reviewing the rendered configuration for the prepared cluster:
helm install calico projectcalico/tigera-operator \
  --version v3.32.2 --namespace tigera-operator --create-namespace \
  -f calico-eks-values.yaml
```

Con `manageCRDs: true`, el operador gestiona los CRDs necesarios una vez iniciado. Si una actualización utiliza campos nuevos de inmediato, aplique primero los CRDs de la versión correspondiente mediante el mecanismo que ya los gestiona, siguiendo el [procedimiento de actualización de Calico](https://docs.tigera.io/calico/latest/operations/upgrading/kubernetes-upgrade). Una reversión de Helm no garantiza por sí sola que se reviertan las migraciones de CRDs o de datos almacenados.

## Política de red nativa de AWS como alternativa

El soporte de NetworkPolicy estándar en AWS VPC CNI comenzó con **VPC CNI 1.14**, no con EKS 1.14. La guía actual de AWS requiere **VPC CNI 1.21 o posterior para las políticas estándar y de administración**, versiones compatibles de EKS y de su plataforma, y kernel de Linux 5.10 o posterior. Siga la guía de compatibilidad actual, en lugar de los ejemplos de la versión de lanzamiento.

AWS documenta **ClusterNetworkPolicy** de `networking.k8s.aws/v1alpha1`, con los niveles Admin y Baseline, junto con NetworkPolicy de `networking.k8s.io/v1`, cuyo alcance es el namespace. Es una API distinta de GlobalNetworkPolicy y de los niveles configurables de Calico. Las políticas nativas de AWS ya no se limitan necesariamente a reglas de namespace.

| Capacidad | Implementación nativa de AWS | Calico OSS en esta guía |
| --- | --- | --- |
| Kubernetes NetworkPolicy | Compatible en nodos Linux EC2 que cumplan los requisitos | Compatible en los endpoints gestionados |
| Política de clúster | ClusterNetworkPolicy de AWS, con sus propias reglas y requisitos | GlobalNetworkPolicy y Tier de Calico |
| Observabilidad de políticas | Métricas y registros de eventos del agente; la entrega a CloudWatch se configura por separado | Métricas de Felix/Typha y observabilidad de flujos mediante Goldmane y Whisker |
| Políticas de la capa de aplicación | No se deducen de una política de red L3/L4 | Integración independiente con Dikastes/Istio; esta instalación no la habilita |
| Políticas DNS/FQDN de Calico | No implementa la API de Calico | La función documentada de políticas basadas en dominios requiere una edición comercial de Calico |

Para la alternativa nativa, configure `enableNetworkPolicy` mediante los ajustes compatibles del complemento de VPC CNI o de Helm. Establecer la variable de entorno inventada `ENABLE_NETWORK_POLICY` en `aws-node` no basta. El modo de inicio nativo `standard` permite tráfico mientras se establecen las reglas; `strict` empieza denegándolo y requiere permisos para las rutas necesarias, incluido DNS. Estos ajustes de AWS no configuran el comportamiento de inicio de Calico.

La aplicación de políticas nativas tiene límites documentados: nodos Linux EC2, interfaz principal del Pod, restricciones de familias de IP y funcionamiento fiable con Pods gestionados por controladores. Revise las limitaciones de puertos y protocolos y los requisitos de puertos de los Services. Mantenga los recursos PolicyEndpoint de AWS bajo la gestión de su controlador. Consulte la [guía de VPC CNI](../01-vpc-cni.md) para la configuración completa y los detalles de migración.

## Tipos de nodos y perfiles de red

| Perfil | Aplicabilidad |
| --- | --- |
| Nodos Linux EC2 gestionados o autogestionados con VPC CNI | Instalación de referencia limitada a políticas descrita anteriormente; el modelo de gestión del nodo no determina por sí solo las capacidades de Calico |
| Nodos EC2 con la CNI completa de Calico | Diseño independiente documentado por Tigera; cambian el direccionamiento de Pods, el acceso al plano de control, la gestión de la CNI y los límites de soporte |
| EKS Fargate | El agente de nodo de Calico y la política nativa de VPC CNI no se ejecutan en estos Pods; los grupos de seguridad para Pods ofrecen otro control compatible |
| EKS Auto Mode | Red y políticas de AWS integradas; no admite plugins alternativos de CNI o de políticas de red |
| EKS Hybrid Nodes | No es compatible con VPC CNI; la guía especializada de CNI enumera distribuciones de Cilium 1.17/1.18 mantenidas por AWS; consulte la aclaración de soporte siguiente |
| Nodos Windows | Requieren el procedimiento específico de Windows/VPC CNI y Calico HNS; no disponen del plano de datos eBPF de Calico; consulte las [limitaciones de Windows](07-advanced-topics.md) |

La guía especializada de CNI para Hybrid Nodes enumera distribuciones de Cilium mantenidas por AWS y remite a ejemplos de Calico en otras páginas. La [página general de CNI alternativos](https://docs.aws.amazon.com/eks/latest/userguide/alternate-cni-plugins.html) sigue describiendo el soporte básico de Cilium y Calico para Hybrid Nodes. Que se haya trasladado un ejemplo no implica el fin del soporte de Calico, ni que cualquier versión del proyecto original tenga soporte de AWS. Confirme el alcance de soporte de la distribución y de las capacidades concretas.

Una política de Calico aplicada a un endpoint EC2 puede restringir sus conexiones con un Pod de Fargate. Eso no significa que la política se aplique dentro de Fargate. En clústeres con distintos tipos de cómputo, defina explícitamente dónde se programan los Pods y dónde se aplican las políticas; no atribuya «soporte completo de Calico» a todos los nodos.

Establecer `enableNetworkPolicy` de VPC CNI en false no habilita la CNI completa de Calico. El procedimiento de Tigera para un clúster nuevo retira la CNI existente antes de incorporar los nodos de trabajo. Eliminar `aws-node` de un clúster de producción no es un atajo válido para convertirlo. El diseño overlay documentado también requiere considerar el tráfico desde el servidor de API hacia los Pods, como el de los webhooks de admisión; utilizar componentes confiables con `hostNetwork` es una de las soluciones documentadas. Antes de adoptar este perfil, revise los CIDR de Pods, las rutas de retorno, la MTU, los permisos IAM de los nodos, las comprobaciones de origen y destino cuando correspondan, y el alcance de soporte de AWS y Tigera.

En Auto Mode, las variables de entorno de VPC CNI y ENIConfig no configuran el servicio de red gestionado; utilice NodeClass. Auto Mode ejecuta CoreDNS como servicio de sistema del nodo. Un clúster formado únicamente por nodos Auto Mode no necesita el Deployment tradicional de CoreDNS, pero los nodos que no utilizan Auto Mode en un clúster mixto sí lo necesitan. La consulta DNS inicial puede resolverse localmente mientras el reenvío a otros servidores sigue saliendo del nodo.

## IAM, IRSA y Pod Identity

La instalación básica de Calico limitada a políticas utiliza RBAC de Kubernetes. No requiere un rol IAM amplio para consultar EC2 o acceder a CloudWatch en `calico-node`. VPC CNI necesita sus propios permisos de AWS documentados. Un exportador de registros independiente o una integración comercial con la nube pueden requerir permisos adicionales en el ServiceAccount **de ese componente**.

IRSA utiliza el proveedor OIDC del clúster y una política de confianza con alcance adecuado para obtener credenciales de AWS para un ServiceAccount. EKS Pod Identity es otra opción cuando el componente, el SDK y el tipo de cómputo la admiten. Una política IAM o un valor inventado de `Installation.spec.nodeMetadata` no configuran por sí solos las credenciales de una carga de trabajo. Siga la configuración del componente correspondiente y conserve la gestión de los ServiceAccounts por el operador. Consulte la [configuración de IAM de VPC CNI](https://docs.aws.amazon.com/eks/latest/userguide/cni-iam-role.html).

## Grupos de seguridad y política de Calico

![Los grupos de seguridad, la política de Calico y la autenticación de aplicaciones proporcionan capas distintas de control de acceso.](../../.gitbook/assets/en-networking-calico-08-eks-integration-3.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-networking-calico-08-eks-integration-3.html)

La figura representa capas conceptuales, no un orden fijo de evaluación. Calico evalúa las políticas según el nivel, el orden y el comportamiento de las reglas; NetworkPolicy no siempre se evalúa antes que GlobalNetworkPolicy. CloudTrail registra actividad de la API de AWS, no decisiones sobre paquetes. VPC Flow Logs y las herramientas de registro de políticas configuradas aportan distintos tipos de datos de tráfico. mTLS y la autorización de la aplicación deben desplegarse por separado.

Los grupos de seguridad se asocian a ENI. **Los grupos de seguridad para Pods** pueden seleccionar cargas de trabajo mediante SecurityGroupPolicy, por lo que es incorrecto afirmar que solo seleccionan instancias. Para combinarlos con políticas de Calico, AWS exige VPC CNI 1.11 o posterior y `POD_SECURITY_GROUP_ENFORCING_MODE=standard`. En modo strict, Calico no aplica políticas al tráfico de esos Pods. Compruebe la compatibilidad de las ENI de rama y de las instancias, y vuelva a crear los Pods afectados tras cambiar el modo. Los grupos de seguridad para Pods no son compatibles con Windows ni con Auto Mode.

En modo standard, con el SNAT externo habitual de VPC CNI habilitado (`AWS_VPC_K8S_CNI_EXTERNALSNAT=false`), el tráfico que sale de la VPC utiliza la IP de la ENI principal y los grupos de seguridad del nodo. Las reglas de salida del grupo de seguridad del Pod no cubren necesariamente todas las rutas. Consulte las [condiciones exactas de AWS](https://docs.aws.amazon.com/eks/latest/userguide/security-groups-for-pods.html).

### Una política de aplicación con ámbito de namespace

Este ejemplo selecciona únicamente Pods `app=frontend` de un namespace `calico-eks-demo` preparado. Permite que un **Pod de gateway dentro del clúster**, en el mismo namespace, acceda a TCP 8080 y que los Pods frontend se conecten con los Pods backend del mismo namespace en TCP 8080. Supone que se utilizan Pods CoreDNS habituales con `k8s-app=kube-dns`; NodeLocal DNS u otro resolvedor requieren destinos distintos. Otras políticas o niveles pueden modificar el resultado: revise el conjunto completo de políticas efectivas.

```yaml
apiVersion: projectcalico.org/v3
kind: NetworkPolicy
metadata:
  name: frontend-policy
  namespace: calico-eks-demo
spec:
  selector: app == 'frontend'
  types: [Ingress, Egress]
  ingress:
    - action: Allow
      protocol: TCP
      source:
        selector: app == 'gateway'
      destination:
        ports: [8080]
  egress:
    - action: Allow
      protocol: TCP
      destination:
        selector: app == 'backend'
        ports: [8080]
    - action: Allow
      protocol: UDP
      destination:
        namespaceSelector: projectcalico.org/name == 'kube-system'
        selector: k8s-app == 'kube-dns'
        ports: [53]
    - action: Allow
      protocol: TCP
      destination:
        namespaceSelector: projectcalico.org/name == 'kube-system'
        selector: k8s-app == 'kube-dns'
        ports: [53]
```

Mantenga el selector de destino y el puerto dentro del **mismo** bloque `destination`. Las claves YAML duplicadas pueden eliminar el selector sin avisar y permitir TCP 8080 hacia endpoints no previstos. Un ALB o NLB no es un Pod de Kubernetes con `app=load-balancer`. Evalúe por separado el modo de destino, las comprobaciones de salud y las direcciones de origen observadas, siguiendo la [guía del balanceador de carga](../03-aws-lb-controller.md).

Una GlobalNetworkPolicy vacía para todo el clúster con selector `all()` puede interrumpir DNS, la API, la monitorización y el tráfico de las aplicaciones. Empiece aplicando la denegación predeterminada en un namespace de prueba elegido, con permisos explícitos para sus dependencias. Consulte las [políticas de red](05-network-policy.md).

## Actualización y recuperación

1. Inventaríe las versiones del plano de control de EKS, del sistema operativo y kubelet de los nodos, de VPC CNI, kube-proxy, Calico, el operador, los CRDs y calicoctl. Exporte la configuración y las políticas que gestione.
2. Elija una versión de Calico compatible con **las versiones de origen y destino de la transición prevista**. No existe una regla universal que obligue a actualizar Calico siempre primero o siempre al final. Siga el procedimiento de su instalación y las notas de migración de CRDs.
3. Revise las recomendaciones de actualización de EKS, las API retiradas y la compatibilidad de todos los complementos. Actualice el plano de control de EKS una versión menor cada vez; después, lleve los nodos y los complementos correspondientes a versiones compatibles.
4. Compruebe las políticas y el comportamiento de los Services durante la transición gradual, incluidos los casos de tráfico denegado y los Pods recién creados. Defina quién gestiona la configuración y los requisitos para revertir los cambios.

```bash
aws eks describe-cluster --name "$EKS_CLUSTER" --region "$EKS_REGION" \
  --query 'cluster.{version:version,platform:platformVersion,status:status}'
kubectl get nodes -o wide
kubectl get daemonset calico-node -n calico-system -o wide
kubectl get tigerastatus
helm get values calico -n tigera-operator -o yaml
```

EKS admite actualmente la **reversión condicional a la versión menor anterior durante los siete días posteriores a una actualización del clúster existente**. El clúster debe cumplir los requisitos documentados de elegibilidad y preparación; ese plazo no permite cualquier reducción de versión. Prepare los nodos gestionados, autogestionados o híbridos y los complementos incompatibles antes de revertir el plano de control. Auto Mode gestiona la reversión de sus nodos; las cargas de trabajo de Fargate requieren su propio procedimiento. Calico y los complementos de EKS no se revierten automáticamente, y conservar los datos de etcd no hace compatibles los recursos incompatibles. Siga el [procedimiento de reversión actual](https://docs.aws.amazon.com/eks/latest/userguide/rollback-cluster.html) sin utilizar `--force` para ocultar problemas de compatibilidad pendientes. Fuera del plazo permitido, planifique una migración a otro clúster compatible.

Aplicar un manifiesto antiguo del operador o ejecutar `helm rollback` no demuestra que sea seguro reducir la versión de Calico. Revise el soporte de esa versión y sus cambios de esquema y datos antes de elegir cómo recuperar el servicio. `calicoctl node status` muestra el estado BGP local del nodo; no es una prueba de aceptación para una instalación de EKS limitada a políticas.

## Coste y rendimiento

| Factor | Qué evaluar |
| --- | --- |
| Recursos de los nodos de trabajo | Mida Felix, Typha, los controladores y la agregación de flujos con los cambios reales de políticas y endpoints; las solicitudes de CPU no tienen una tarifa independiente de AWS |
| Capacidad de IP de VPC | La delegación de prefijos modifica la asignación y la densidad de direcciones; no reduce automáticamente el coste de asociar ENI |
| Registros y métricas | La retención, la ingesta, las consultas y la entrega del exportador tienen costes distintos; las métricas no son registros de flujo |
| Tráfico entre zonas de disponibilidad | Evalúe las rutas reales de origen y destino y los precios del servicio; la localización del tráfico también afecta a la disponibilidad |
| Ciclo de vida de EKS | El soporte extendido puede añadir un cargo por clúster; consulte el calendario de soporte actual |

Las estimaciones anteriores de coste por componente no indicaban región, precios de instancias ni supuestos de asignación, por lo que no constituyen un modelo de costes utilizable. Estime el coste con el consumo de recursos observado y los precios aplicables de AWS, sin deducir ahorros mensuales fijos de límites de recursos arbitrarios.

### Delegación de prefijos

En nodos habituales con VPC CNI, configure `ENABLE_PREFIX_DELEGATION`, `WARM_PREFIX_TARGET`, `MINIMUM_IP_TARGET` y `WARM_IP_TARGET` dentro de **`env`** en el complemento, o mediante la configuración de DaemonSet o Helm que lo gestiona. Las entradas `enable-prefix-delegation` en minúsculas de un ConfigMap no configuran IPAMD.

Empiece con una estrategia de asignación documentada. `WARM_IP_TARGET` y `MINIMUM_IP_TARGET` tienen prioridad sobre `WARM_PREFIX_TARGET`; configurar todas las variables no suma sus efectos. Los prefijos IPv4 requieren bloques `/28` contiguos en la subred e instancias compatibles. Revise la fragmentación de la subred, las reservas, la configuración de max-Pods y kubelet, y el plan de despliegue. Consulte el [procedimiento de prefijos de AWS](https://docs.aws.amazon.com/eks/latest/userguide/cni-increase-ip-addresses-procedure.html).

### Calico eBPF en EKS

Calico documenta el uso de su plano de datos eBPF en EKS con redes compatibles de VPC CNI, pero modifica el tratamiento de los Services y requiere una migración independiente. Siga la [Parte 6](06-ebpf-dataplane.md): revise el kernel y la plataforma, el acceso directo al FQDN del servidor de API y el DNS de arranque, la gestión de kube-proxy, los puertos de salud y el estado necesario para la reversión.

VPC CNI **no** exige en todos los casos que kube-proxy siga ejecutándose. Si debe coexistir con Calico, configure tanto `bpfKubeProxyIptablesCleanupEnabled: false` como `bpfKubeProxyHealthzPort: 0` para evitar los conflictos documentados. El controlador que gestiona un DaemonSet puede revertir un parche genérico de su selector; el cambio tampoco debe sobrescribir selectores ajenos. DSR no es una optimización predeterminada de EKS: valide por separado las comprobaciones de subred y dirección de origen de AWS y las limitaciones de los balanceadores externos. Esta configuración de referencia mantiene Iptables y kube-proxy.

Aplicar valores genéricos de sysctl, reducir la memoria a un mínimo arbitrario o acortar los tiempos de conntrack no demuestra una mejora de rendimiento. Mida la carga de trabajo real y preserve las rutas de retorno, las conexiones establecidas y la recuperación ante fallos.

## Ejemplo de planificación de clúster con eksctl

Este es un **ejemplo de planificación para nodos Linux gestionados habituales**; no se ha probado como receta de producción ni convierte un clúster Auto Mode. Confirme las versiones compatibles de los complementos mediante `describe-addon-versions` y fije las versiones aprobadas en la configuración antes de crear el clúster. Omitir la versión de un complemento selecciona una opción predeterminada compatible, pero no aprueba todas las versiones futuras. El acceso privado a la API requiere una ruta de administración hacia la VPC. Diseñe NAT, los registros, la capacidad de los nodos y los rangos de direcciones para su entorno.

```yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: calico-eks-demo
  region: us-east-1
  version: "1.36"
iam:
  withOIDC: true
vpc:
  cidr: 10.0.0.0/16
  clusterEndpoints:
    publicAccess: false
    privateAccess: true
managedNodeGroups:
  - name: linux-workers
    instanceType: m5.large
    amiFamily: AmazonLinux2023
    desiredCapacity: 3
    minSize: 3
    maxSize: 6
    privateNetworking: true
    volumeType: gp3
    volumeSize: 100
addons:
  - name: vpc-cni
    attachPolicyARNs:
      - arn:aws:iam::aws:policy/AmazonEKS_CNI_Policy
    configurationValues: |
      enableNetworkPolicy: "false"
      env:
        ANNOTATE_POD_IP: "true"
  - name: coredns
  - name: kube-proxy
cloudWatch:
  clusterLogging:
    enableTypes: [api, audit, authenticator, controllerManager, scheduler]
```

La política CNI para IPv4 corresponde a la identidad de VPC CNI, no a Calico. Revise IAM si utiliza otras familias de IP o métodos de identidad. Cuando exista el clúster aprobado, compruebe las anotaciones y RBAC y siga **una** de las opciones de instalación de Calico descritas anteriormente.

## Validar el resultado

```bash
kubectl get tigerastatus
kubectl rollout status daemonset/calico-node -n calico-system --timeout=300s
kubectl get pods -n calico-system -o wide
kubectl get pods -n calico-eks-demo -o json \
  | jq '.items[] | {name: .metadata.name, ip: .status.podIP,
      annotatedIPs: .metadata.annotations["vpc.amazonaws.com/pod-ips"]}'
kubectl get networkpolicies.projectcalico.org -n calico-eks-demo
```

Utilice cargas de trabajo de prueba gestionadas por controladores. Compruebe las conexiones permitidas y denegadas en el mismo nodo, entre nodos y zonas de disponibilidad, después de recrear los Pods y durante las actualizaciones. Incluya DNS, los endpoints de API e identidad necesarios para la aplicación, el tráfico de los Services y las comprobaciones de salud de los balanceadores. Que un Pod esté Running o un nodo Ready no demuestra que se aplique la denegación prevista ni que no haya un intervalo sin políticas al arrancar. Pruebe IPv6 por separado: la guía actual de Calico para EKS excluye la aplicación de políticas a Pods IPv6 con `ENABLE_V4_EGRESS=true`.

Los ejemplos de este documento se contrastaron con esquemas publicados y manifiestos generados mediante los charts. No se crearon clústeres EKS, recursos IAM ni tráfico de producción para validarlos.

## Referencias

- [Calico en EKS](https://docs.tigera.io/calico/latest/getting-started/kubernetes/managed-public-cloud/eks)
- [Requisitos de Calico](https://docs.tigera.io/calico/latest/getting-started/kubernetes/requirements)
- [Instalación de Calico con Helm](https://docs.tigera.io/calico/latest/getting-started/kubernetes/helm)
- [Actualizaciones de Calico](https://docs.tigera.io/calico/latest/operations/upgrading/kubernetes-upgrade)
- [Referencia de configuración de VPC CNI 1.23](https://github.com/aws/amazon-vpc-cni-k8s/blob/v1.23.0/README.md)
- [Política de red nativa de EKS](https://docs.aws.amazon.com/eks/latest/userguide/cni-network-policy.html)
- [Actualizaciones de complementos de EKS](https://docs.aws.amazon.com/eks/latest/userguide/updating-an-add-on.html)
- [Ciclo de vida de versiones de EKS](https://docs.aws.amazon.com/eks/latest/userguide/kubernetes-versions.html)
- [Redes de EKS Auto Mode](https://docs.aws.amazon.com/eks/latest/userguide/auto-networking.html)
- [CNI de EKS Hybrid Nodes](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-cni.html)

## Siguientes pasos y cuestionario

Continúe con [operaciones](09-operations.md), revise [temas avanzados](07-advanced-topics.md) o el [glosario](glossary.md), y pruebe sus conocimientos con el [cuestionario de integración de EKS](../../quizzes/networking/calico/08-eks-integration-quiz.md).
