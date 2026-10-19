# Configuración y optimización de NodePool

> **Versiones compatibles**: EKS Auto Mode GA; versión base del ejemplo: EKS 1.36
> **Última actualización**: 12 de septiembre de 2026

Este capítulo distingue entre los valores predeterminados administrados por AWS, las restricciones de NodePool personalizadas y la API NodeClass específica de AWS. Completa primero [Introducción](./01-getting-started.md), usa la cuenta y el contexto previstos, y revisa todos los nombres de perfiles/IAM y las etiquetas de red antes de aplicar una plantilla. Los límites de capacidad que se muestran son ilustrativos y aun así pueden permitir costos considerables.

Los ejemplos de NodePool se contrastaron con el esquema estructural de la CRD de Karpenter 1.14.1 publicada; los campos de NodeClass específicos de AWS se compararon con la documentación de AWS. Esto no permite identificar la versión interna del controlador de Auto Mode ni demuestra la admisión o la disponibilidad en un clúster activo. No se aprovisionaron nodos durante esta auditoría.

## Comprender los NodePools integrados

Cuando está habilitado, Auto Mode proporciona los siguientes pools. Son administrados por AWS; crea pools personalizados en lugar de editar su configuración administrada.

| Pool | Arquitectura | Capacidad y selección de instancias | Propósito |
|------|--------------|----------------------------------|---------|
| `general-purpose` | `amd64` | On-Demand, familias C/M/R, generación 5 o posterior | Cargas de trabajo generales |
| `system` | `amd64` y `arm64` | On-Demand, familias C/M/R, generación 5 o posterior | Cargas de trabajo críticas para el clúster que toleran `CriticalAddonsOnly` |

El pool integrado general-purpose **no** habilita Spot. Usa un pool personalizado cuando necesites Spot o restricciones distintas de arquitectura/instancia. Auto Mode proporciona DNS local en los nodos y funciones de red para los Services; un clúster solo de Auto Mode no necesita Pods ordinarios de CoreDNS/kube-proxy únicamente para poblar el pool system. Los clústeres mixtos siguen necesitando el Deployment tradicional de CoreDNS para los nodos que no son de Auto Mode.

Inspecciona los objetos administrados reales para comprobar la configuración de interrupciones y los detalles de los taints, en lugar de aplicar un YAML predeterminado supuesto:

```bash
kubectl --context "$CLUSTER_NAME" get nodepool general-purpose system -o yaml
kubectl --context "$CLUSTER_NAME" get nodeclass default -o yaml
```

Debe haber al menos un pool integrado habilitado para que AWS proporcione el NodeClass `default`. Si ambos están deshabilitados, crea tu propio NodeClass y actualiza las referencias siguientes. Quitar un nombre integrado de `computeConfig.nodePools` elimina ese pool y drena/termina sus nodos; no equivale simplemente a ocultarlo para cargas de trabajo nuevas.

## Crear NodePools personalizados

Estos ejemplos hacen referencia al NodeClass `default` existente para centrarse en las restricciones de programación. Para usar el NodeClass personalizado más adelante en este capítulo, créalo primero y cambia `nodeClassRef.name` en el pool previsto. Todas las etiquetas y los taints de `template` se aplican a los nodos nuevos; una etiqueta solo en los metadatos de NodePool no etiqueta los nodos.

### Cargas de trabajo optimizadas para cómputo

La condición de generación `Gt ["6"]` permite la generación 7 y posteriores. No selecciona únicamente la generación más reciente. El ejemplo permite instancias On-Demand de la familia C x86 y da a este pool una preferencia de aprovisionamiento superior a la del ejemplo de memoria.

```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: compute-optimized
  labels:
    workload-type: compute-intensive
spec:
  template:
    metadata:
      labels:
        workload-type: compute-intensive
    spec:
      requirements:
      - key: eks.amazonaws.com/instance-category
        operator: In
        values:
        - c
      - key: eks.amazonaws.com/instance-generation
        operator: Gt
        values:
        - '6'
      - key: eks.amazonaws.com/instance-size
        operator: In
        values:
        - xlarge
        - 2xlarge
        - 4xlarge
      - key: kubernetes.io/arch
        operator: In
        values:
        - amd64
      - key: karpenter.sh/capacity-type
        operator: In
        values:
        - on-demand
      nodeClassRef:
        group: eks.amazonaws.com
        kind: NodeClass
        name: default
  limits:
    cpu: '1000'
    memory: 4000Gi
  disruption:
    consolidationPolicy: WhenEmptyOrUnderutilized
    consolidateAfter: 5m
  weight: 10
```

### Cargas de trabajo optimizadas para memoria

Este ejemplo permite instancias de la familia R de generación 6 y posteriores en cualquiera de las dos arquitecturas. La imagen de contenedor y las dependencias de la aplicación deben admitir la arquitectura que seleccione el planificador.

```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: memory-optimized
  labels:
    workload-type: memory-intensive
spec:
  template:
    metadata:
      labels:
        workload-type: memory-intensive
    spec:
      requirements:
      - key: eks.amazonaws.com/instance-category
        operator: In
        values:
        - r
      - key: eks.amazonaws.com/instance-generation
        operator: Gt
        values:
        - '5'
      - key: eks.amazonaws.com/instance-size
        operator: In
        values:
        - 2xlarge
        - 4xlarge
        - 8xlarge
        - 12xlarge
      - key: kubernetes.io/arch
        operator: In
        values:
        - amd64
        - arm64
      - key: karpenter.sh/capacity-type
        operator: In
        values:
        - on-demand
      nodeClassRef:
        group: eks.amazonaws.com
        kind: NodeClass
        name: default
  limits:
    cpu: '500'
    memory: 8000Gi
  disruption:
    consolidationPolicy: WhenEmptyOrUnderutilized
    consolidateAfter: 10m
  weight: 5
```

## Configurar el NodeClass de AWS

Auto Mode usa `eks.amazonaws.com/v1`, tipo `NodeClass`. Sus campos difieren de `EC2NodeClass` de AWS Karpenter autoadministrado: no copies `amiFamily`, `blockDeviceMappings`, `userData` con scripts arbitrarios de shell ni `metadataOptions` a esta API. AWS selecciona su variante administrada de Bottlerocket.

Guarda lo siguiente como `custom-nodeclass.yaml` y reemplaza los valores ilustrativos de perfil y selector por recursos revisados. Se admite `instanceProfile`; su nombre debe comenzar por `eks`. Como alternativa, establece `role` con el nombre del rol IAM del nodo. **Especifica exactamente uno de `role` o `instanceProfile`.** El rol incluido en el perfil necesita la entrada de acceso de EKS y los permisos apropiados para Auto Mode; reutilizar un rol configurado no requiere una entrada duplicada. Para un rol nuevo, sigue el procedimiento de entrada de acceso de la referencia de NodeClass de AWS.

Las etiquetas de subred seleccionan recursos, pero no establecen el enrutamiento ni el aislamiento. Verifica la VPC, la disponibilidad de AZ, las tablas de rutas y las reglas de los grupos de seguridad. `associatePublicIPAddress: false` impide la asignación de direcciones IP públicas; los nodos siguen necesitando conectividad saliente apropiada.

```yaml
apiVersion: eks.amazonaws.com/v1
kind: NodeClass
metadata:
  name: custom-nodeclass
spec:
  instanceProfile: eks-node-instance-profile
  subnetSelectorTerms:
  - tags:
      kubernetes.io/role/internal-elb: '1'
      Environment: production
  securityGroupSelectorTerms:
  - tags:
      kubernetes.io/cluster/my-cluster: owned
      Type: worker-node
  ephemeralStorage:
    size: 100Gi
    iops: 3000
    throughput: 125
  advancedNetworking:
    associatePublicIPAddress: false
  advancedCompute:
    kernel:
      sysctl:
        vm.max_map_count: 262144
  tags:
    Environment: production
    ManagedBy: eks-auto-mode
```

Verifica que el rol del clúster pueda crear y etiquetar recursos con cualquier clave personalizada de `spec.tags`; un NodeClass no concede permisos de IAM por sí mismo.

`ephemeralStorage` configura el almacenamiento efímero del nodo, no asignaciones arbitrarias de dispositivos de bloques. El tamaño `100Gi` y los valores de 3000 IOPS/125 MiB/s son ejemplos; comprueba los límites actuales de los campos de Auto Mode, el comportamiento del almacenamiento de la instancia y el costo. La configuración de KMS del cliente corresponde a `ephemeralStorage.kmsKeyID` y se aplica a los volúmenes **EBS** raíz y de datos del nodo. No selecciona la clave para el cifrado del almacenamiento local NVMe de la instancia ni establece el cifrado de los PVC de las aplicaciones.

El ejemplo de bootstrap anterior modificaba `vm.max_map_count`. El reemplazo compatible es `advancedCompute.kernel.sysctl`, que se aplica durante el arranque del nodo. Cambiar la configuración compatible del kernel marca los nodos existentes para su reemplazo por deriva; no modifica los nodos de inmediato mediante shell. Usa este ajuste solo en las cargas de trabajo que lo necesiten y revisa el comportamiento de las interrupciones.

### Configuración de seguridad fija de IMDS

Auto Mode impone IMDSv2 y un límite de saltos de 1; esos valores predeterminados no se pueden cambiar mediante NodeClass. Los Pods normales que no usan la red del host no pueden acceder a IMDS por esa vía, pero esto no garantiza el aislamiento universal de los Pods: `hostNetwork` modifica la accesibilidad. Prefiere la identidad de carga de trabajo para el acceso de las aplicaciones a AWS y proporciona explícitamente la región u otra configuración, en lugar de depender de los metadatos del nodo.

### KMS del cliente, paquetes de CA y redes independientes para Pods

No pegues un certificado truncado en un manifiesto. Este generador opcional lee la plantilla básica revisada, comprueba un paquete PEM público aprobado, lo codifica en base64 en `certificateBundles[].data` y genera un segundo NodeClass completo. Requiere Python 3 con PyYAML. Configura `NODE_KMS_KEY_ARN` y `CA_BUNDLE_FILE`, y conserva los valores revisados de `AWS_REGION`/`EXPECTED_ACCOUNT_ID` del capítulo anterior.

Aprueba por separado el emisor de CA, las huellas digitales y la validez. La comprobación de sintaxis siguiente no demuestra la confiabilidad, los permisos de KMS ni la existencia de recursos en la nube. Revisa la política de clave y las concesiones de IAM, así como las selecciones de etiquetas de red de Pods, antes de aplicar el resultado.

```bash
set -euo pipefail
: "${AWS_REGION:?Set the reviewed cluster region}"
: "${EXPECTED_ACCOUNT_ID:?Set the intended AWS account}"
: "${NODE_KMS_KEY_ARN:?Set the approved same-region customer-managed KMS key ARN}"
: "${CA_BUNDLE_FILE:?Set the path to an approved public CA PEM bundle}"
export AWS_REGION EXPECTED_ACCOUNT_ID NODE_KMS_KEY_ARN CA_BUNDLE_FILE
umask 077
python3 - <<'PY'
import base64, json, os, re, ssl
from pathlib import Path
import yaml

doc = yaml.safe_load(Path("custom-nodeclass.yaml").read_text())
if doc.get("kind") != "NodeClass" or doc.get("apiVersion") != "eks.amazonaws.com/v1":
    raise SystemExit("Expected the reviewed Auto Mode NodeClass template")
spec = doc["spec"]
if ("role" in spec) == ("instanceProfile" in spec):
    raise SystemExit("Set exactly one reviewed role or instanceProfile")
key = os.environ["NODE_KMS_KEY_ARN"]
prefix = "arn:aws:kms:" + os.environ["AWS_REGION"] + ":" + os.environ["EXPECTED_ACCOUNT_ID"] + ":key/"
if not key.startswith(prefix) or not re.fullmatch(r"(?:[a-f0-9-]{36}|mrk-[a-f0-9]{32})", key[len(prefix):]):
    raise SystemExit("KMS key ARN must match the reviewed account and region")
pem = Path(os.environ["CA_BUNDLE_FILE"]).read_bytes()
if b"PRIVATE KEY" in pem:
    raise SystemExit("Use public CA certificates only, never a private key")
ssl.create_default_context().load_verify_locations(cadata=pem.decode("ascii"))
doc["metadata"]["name"] = "secure-network-nodeclass"
spec["ephemeralStorage"]["kmsKeyID"] = key
spec["certificateBundles"] = [{"name": "corporate-ca",
                               "data": base64.b64encode(pem).decode("ascii")}]
spec["podSubnetSelectorTerms"] = [{"tags": {"Purpose": "pod-network"}}]
spec["podSecurityGroupSelectorTerms"] = [{"tags": {"Purpose": "pod-network"}}]
Path("secure-network-nodeclass.json").write_text(json.dumps(doc, indent=2) + "\n")
PY
```

| Campo | Significado |
|-------|---------|
| `ephemeralStorage.kmsKeyID` | Clave administrada por el cliente para los volúmenes EBS raíz y de datos del nodo; usa una clave de la región del clúster |
| `certificateBundles[].data` | Paquete de certificados codificado en base64 para la confianza del nodo; no modifica automáticamente el almacén de confianza de contenedores de todas las aplicaciones |
| `podSubnetSelectorTerms` | Subredes separadas para Pods seleccionadas para este NodeClass |
| `podSecurityGroupSelectorTerms` | Grupos de seguridad de red de Pods; configúralos junto con los selectores de subredes de Pods |

Los selectores de subredes y grupos de seguridad de Pods deben configurarse juntos y tener una cobertura compatible de VPC/AZ. La configuración se aplica por NodeClass, no por espacio de nombres ni por ServiceAccount. El tráfico que usa la red del host utiliza la red del nodo; SNAT de salida también puede cambiar la dirección de origen y los grupos de seguridad aplicables. Revisa los efectos del enrutamiento, SNAT y la densidad de Pods antes de afirmar que todo el tráfico está aislado.

## Separar cargas de trabajo y entornos

### Pools de frontend y backend

Los taints impiden que los Pods sin tolerancias coincidentes se ejecuten en estos nodos. Las tolerancias solo permiten la programación; añade un selector o una afinidad requerida cuando una carga de trabajo deba usar sus nodos designados.

```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: frontend
spec:
  template:
    metadata:
      labels:
        workload-tier: frontend
    spec:
      requirements:
      - key: eks.amazonaws.com/instance-category
        operator: In
        values:
        - m
        - c
      - key: karpenter.sh/capacity-type
        operator: In
        values:
        - spot
        - on-demand
      taints:
      - key: workload-tier
        value: frontend
        effect: NoSchedule
      nodeClassRef:
        group: eks.amazonaws.com
        kind: NodeClass
        name: default
  weight: 10
  limits:
    cpu: '100'
    memory: 400Gi
---
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: backend
spec:
  template:
    metadata:
      labels:
        workload-tier: backend
    spec:
      requirements:
      - key: eks.amazonaws.com/instance-category
        operator: In
        values:
        - m
        - r
      - key: karpenter.sh/capacity-type
        operator: In
        values:
        - on-demand
      taints:
      - key: workload-tier
        value: backend
        effect: NoSchedule
      nodeClassRef:
        group: eks.amazonaws.com
        kind: NodeClass
        name: default
  weight: 10
  limits:
    cpu: '100'
    memory: 800Gi
```

Por ejemplo, crea un espacio de nombres `nodepool-lab` de tu propiedad y usa tanto un selector como una tolerancia para comprobar la ubicación en frontend:

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: frontend-placement-check
  namespace: nodepool-lab
spec:
  automountServiceAccountToken: false
  nodeSelector:
    workload-tier: frontend
  tolerations:
  - key: workload-tier
    operator: Equal
    value: frontend
    effect: NoSchedule
  containers:
  - name: nginx
    image: nginx:1.30.6
    resources:
      requests:
        cpu: 100m
        memory: 64Mi
      limits:
        cpu: 500m
        memory: 128Mi
    readinessProbe:
      httpGet:
        path: /
        port: 80
      periodSeconds: 5
```

Revisa antes de aplicar: este Pod puede provocar el aprovisionamiento de nodos facturables. Comprueba el nodo asignado, la disponibilidad y las etiquetas del nodo; luego elimina el Pod de prueba de ese espacio de nombres. `NoSchedule` no expulsa un Pod que ya está en ejecución, y las etiquetas/taints por sí solas no constituyen un límite de seguridad entre inquilinos no confiables.

### Pool de desarrollo

La lista actual de tipos de instancia compatibles con AWS incluye tipos T con capacidad de ráfaga, además de tipos M. No elimines T únicamente por suposiciones antiguas sobre Auto Mode. Auto Mode requiere más de una CPU y excluye los tamaños nano/micro/small; aun así, verifica la disponibilidad regional de los tipos, el comportamiento de los créditos de CPU y la idoneidad para la carga de trabajo.

```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: dev-pool
spec:
  template:
    metadata:
      labels:
        environment: development
    spec:
      requirements:
      - key: eks.amazonaws.com/instance-category
        operator: In
        values:
        - t
        - m
      - key: eks.amazonaws.com/instance-size
        operator: In
        values:
        - medium
        - large
      - key: karpenter.sh/capacity-type
        operator: In
        values:
        - spot
      taints:
      - key: environment
        value: development
        effect: NoSchedule
      nodeClassRef:
        group: eks.amazonaws.com
        kind: NodeClass
        name: default
  limits:
    cpu: '100'
    memory: 400Gi
  weight: 1
```

## Límites de recursos, pesos y validación

`limits.cpu` y `limits.memory` limitan los recursos agregados del pool; no son un número máximo de nodos ni un presupuesto monetario. Escribe entre comillas las cantidades de CPU para evitar divergencias de GitOps entre enteros y cadenas. Por ejemplo, `memory: 4000Gi` son 4000 GiB (aproximadamente 3,91 TiB), no exactamente 4 TB.

La documentación de Karpenter (proyecto upstream) describe una consistencia eventual y posibles excesos de los límites durante un aprovisionamiento rápido. No prometas un límite de facturación instantáneo basándote en estos campos. Deja margen para los reemplazos, supervisa el uso y prueba el comportamiento del entorno administrado.

`weight` influye en la preferencia de aprovisionamiento entre los pools aptos. No otorga a un nodo prioridad en el planificador de Kubernetes, no expulsa cargas de trabajo existentes ni obliga a un Pod a usar un pool determinado. Usa restricciones explícitas para las cargas de trabajo y evita superposiciones no deseadas.

```bash
# Validate against the target cluster's actual schemas; no object is persisted.
kubectl --context "$CLUSTER_NAME" apply --dry-run=server -f custom-nodeclass.yaml
kubectl --context "$CLUSTER_NAME" apply --dry-run=server -f secure-network-nodeclass.json
# After an approved apply, inspect conditions rather than assuming readiness.
kubectl --context "$CLUSTER_NAME" get nodeclasses,nodepools
kubectl --context "$CLUSTER_NAME" describe nodeclass secure-network-nodeclass
kubectl --context "$CLUSTER_NAME" get nodeclaims
```

La simulación del lado del servidor puede comprobar la admisión, pero no demuestra IAM, conectividad de red, aprovisionamiento, almacenamiento ni el comportamiento de la aplicación. Resuelve las condiciones de disponibilidad con estado false o unknown y valida las cargas de trabajo controladas antes de usarlo en producción.

## Referencias

- [NodePool integrados](https://docs.aws.amazon.com/eks/latest/userguide/set-builtin-node-pools.html)
- [Campos y etiquetas de NodePool de Auto Mode](https://docs.aws.amazon.com/eks/latest/userguide/create-node-pool.html)
- [Especificación de NodeClass de Auto Mode](https://docs.aws.amazon.com/eks/latest/userguide/create-node-class.html)
- [Tipos de instancia administrados y restricciones de IMDS](https://docs.aws.amazon.com/eks/latest/userguide/automode-learn-instances.html)
- [Seguridad de nodos de Auto Mode](https://docs.aws.amazon.com/whitepapers/latest/security-overview-amazon-eks-auto-mode/eks-auto-mode-data-plane.html)
- [Límites de NodePool de Karpenter upstream](https://karpenter.sh/docs/concepts/nodepools/)
- [Aprovisionamiento ponderado de Karpenter](https://karpenter.sh/docs/concepts/scheduling/#weighted-nodepools)
- [Funciones de CA de nodo, KMS y redes](https://aws.amazon.com/blogs/containers/new-amazon-eks-auto-mode-features-for-enhanced-security-network-control-and-performance/)

< [Anterior: Introducción](./01-getting-started.md) | [Tabla de contenido](./README.md) | [Siguiente: Comportamiento de escalado](./03-scaling-behavior.md) >
