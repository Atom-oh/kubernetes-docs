# Configuración y optimización de NodePool

> **Versiones compatibles**: EKS Auto Mode GA; versión de referencia del ejemplo: EKS 1.36
> **Última actualización**: 21 de octubre de 2026

Este capítulo distingue entre los valores predeterminados administrados por AWS, las restricciones de NodePool personalizadas y la API de NodeClass específica de AWS. Completa primero [Introducción](./01-getting-started.md), usa la cuenta y el contexto previstos, y revisa todos los nombres de IAM/perfiles y las etiquetas de red antes de aplicar una plantilla. Los límites de capacidad que se muestran son ilustrativos y aun así pueden permitir costos considerables.

Los ejemplos de NodePool se verificaron con el esquema estructural de la CRD Karpenter 1.14.1 publicada; los campos específicos de AWS de NodeClass se compararon con la documentación de AWS. Esto no permite identificar la versión interna del controlador de Auto Mode ni demuestra que se acepten los recursos o que estén listos en un clúster activo. Durante esta auditoría no se aprovisionaron nodos.

## Comprender los NodePools integrados

Cuando está habilitado, Auto Mode proporciona los siguientes pools. AWS los administra; crea pools personalizados en lugar de editar su configuración administrada.

| Pool | Arquitectura | Capacidad y selección de instancias | Propósito |
|------|--------------|------------------------------------|-----------|
| `general-purpose` | `amd64` | On-Demand, familias C/M/R, generación 5 o posterior | Cargas de trabajo generales |
| `system` | `amd64` y `arm64` | On-Demand, familias C/M/R, generación 5 o posterior | Cargas de trabajo críticas para el clúster que toleran `CriticalAddonsOnly` |

El pool integrado `general-purpose` **no** habilita Spot. Usa un pool personalizado si necesitas Spot o restricciones diferentes de arquitectura o instancia. Auto Mode proporciona funciones de DNS local al nodo y de redes de servicios; un clúster exclusivamente de Auto Mode no necesita Pods normales de CoreDNS/kube-proxy solo para poblar el pool del sistema. Los clústeres mixtos siguen necesitando el Deployment tradicional de CoreDNS para los nodos que no son de Auto Mode.

Inspecciona los objetos administrados reales para conocer los ajustes de interrupción y los detalles de las taints, en lugar de aplicar un YAML predeterminado supuesto:

```bash
kubectl --context "$CLUSTER_NAME" get nodepool general-purpose system -o yaml
kubectl --context "$CLUSTER_NAME" get nodeclass default -o yaml
```

Debe haber habilitado al menos un pool integrado para que AWS proporcione el NodeClass `default`. Si ambos están deshabilitados, crea tu propio NodeClass y actualiza las referencias de abajo. Todas las etiquetas y taints en `template` se aplican a los nodos nuevos; una etiqueta que solo esté en los metadatos de NodePool no etiqueta los nodos.

## Crear NodePools personalizados

Estos ejemplos hacen referencia al NodeClass `default` existente para centrarse en las restricciones de programación. Para usar más adelante en este capítulo el NodeClass personalizado, créalo primero y cambia `nodeClassRef.name` en el pool correspondiente. Todas las etiquetas y taints en `template` se aplican a los nodos nuevos; una etiqueta que solo esté en los metadatos de NodePool no etiqueta los nodos.

### Cargas de trabajo optimizadas para cómputo

La condición de generación `Gt ["6"]` permite la generación 7 y posteriores. No selecciona únicamente la generación más reciente. El ejemplo permite instancias On-Demand de la familia C con arquitectura x86 y asigna a este pool una preferencia de aprovisionamiento superior a la del ejemplo de memoria.

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

Este ejemplo permite instancias de la familia R de generación 6 o posterior en cualquiera de las dos arquitecturas. La imagen de tu contenedor y las dependencias de la aplicación deben ser compatibles con la arquitectura que seleccione el programador.

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

Auto Mode usa `eks.amazonaws.com/v1`, tipo `NodeClass`. Sus campos difieren de los de `EC2NodeClass` de AWS Karpenter autoadministrado: no copies `amiFamily`, `blockDeviceMappings`, `userData` arbitrario de shell ni `metadataOptions` a esta API. AWS selecciona su variante administrada de Bottlerocket.

Guarda lo siguiente como `custom-nodeclass.yaml` y reemplaza los valores ilustrativos del perfil y los selectores por recursos revisados. Se admite `instanceProfile`; su nombre debe comenzar por `eks`. Como alternativa, define `role` con el nombre del rol de IAM del nodo. **Especifica exactamente uno de `role` o `instanceProfile`.** El rol incluido en el perfil necesita la entrada de acceso de EKS y los permisos adecuados para Auto Mode; reutilizar un rol configurado no requiere una entrada duplicada. Para un rol nuevo, sigue el procedimiento de entrada de acceso de la referencia de NodeClass de AWS.

Las etiquetas de subred seleccionan recursos, pero no establecen el enrutamiento ni el aislamiento. Verifica la VPC, la disponibilidad de las AZ, las tablas de rutas y las reglas de los grupos de seguridad. `associatePublicIPAddress: false` impide la asignación de direcciones IP públicas; los nodos siguen necesitando una conectividad saliente adecuada.

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

Verifica que el rol del clúster pueda crear recursos y asignarles etiquetas con las claves personalizadas que haya en `spec.tags`; un NodeClass no concede permisos de IAM por sí mismo.

`ephemeralStorage` configura el almacenamiento efímero del nodo, no asignaciones arbitrarias de dispositivos de bloques. El tamaño `100Gi` y los valores de 3000 IOPS/125 MiB/s son ejemplos; comprueba los límites actuales de los campos de Auto Mode, el comportamiento del almacenamiento de las instancias y el costo. La configuración de KMS del cliente se establece en `ephemeralStorage.kmsKeyID` y se aplica a los volúmenes **EBS** raíz/de datos del nodo. No selecciona la clave para el cifrado del almacenamiento local NVMe de las instancias ni establece el cifrado de los PVC de las aplicaciones.

El ejemplo antiguo de bootstrap cambiaba `vm.max_map_count`. El reemplazo compatible es `advancedCompute.kernel.sysctl`, que se aplica durante el arranque del nodo. Cambiar la configuración compatible del kernel marca los nodos existentes para su reemplazo por divergencia; no es una actualización inmediata de shell en el mismo nodo. Configúrala solo para las cargas de trabajo que necesiten ese ajuste y revisa el comportamiento ante interrupciones.

### Configuración de Kubelet

Auto Mode aplica sus propios valores predeterminados de kubelet. Anúlalos solo mediante `spec.advancedCompute.kubelet` cuando una carga de trabajo necesite una densidad de Pods, un comportamiento de desalojo, una rotación de registros o un comportamiento de OOM diferentes. Las anulaciones documentadas por AWS que aparecen abajo constituyen el conjunto completo; los campos de `spec.kubelet` de `EC2NodeClass` de Karpenter autoadministrado que no se enumeran (por ejemplo, `kubeReserved`, `systemReserved`, `clusterDNS`, `podsPerCore` y los umbrales de recolección de imágenes) no están expuestos por el NodeClass de Auto Mode.

Guarda lo siguiente como `kubelet-nodeclass.yaml`. Los valores son ilustrativos, no recomendaciones; reemplaza los valores de identidad y selectores por recursos revisados, como en el ejemplo anterior.

```yaml
apiVersion: eks.amazonaws.com/v1
kind: NodeClass
metadata:
  name: kubelet-nodeclass
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
  advancedCompute:
    kernel:
      sysctl:
        user.max_user_namespaces: 65536   # required because idsPerPod is set below
    kubelet:
      maxPods: 60
      podPidsLimit: 4096
      idsPerPod: 65536
      singleProcessOOMKill: false
      eviction:
        hard:
          memory.available: 100Mi
          nodefs.available: 10%
        soft:
          memory.available: 500Mi
          nodefs.available: 15%
        softGracePeriod:                  # required for every soft signal
          memory.available: 1m30s
          nodefs.available: 2m
        maxPodGracePeriod: 60
      logging:
        containerLogMaxSize: 10Mi
        containerLogMaxFiles: 5
      allowedUnsafeSysctls:
      - net.core.somaxconn
```

| Campo | Significado | Restricción |
|-------|-------------|-------------|
| `maxPods` | Límite superior de Pods por nodo | De 1 a 110; el valor efectivo es el menor entre este ajuste, las direcciones IP que puede proporcionar el tipo de instancia y el límite de 110 de Auto Mode |
| `podPidsLimit` | Número máximo de identificadores de proceso por Pod | `-1` deshabilita el límite; de lo contrario, el valor debe ser 100 o superior (se rechazan los valores de 0 a 99) |
| `idsPerPod` | UID y GID que kubelet asigna al espacio de nombres de usuario de cada Pod | Un múltiplo de 65536 entre 65536 y 4294967295; requiere que `advancedCompute.kernel.sysctl.user.max_user_namespaces` sea mayor que 0 en el mismo NodeClass |
| `singleProcessOOMKill` | En caso de OOM, termina los procesos de un contenedor uno a uno en lugar de hacerlo como grupo | Requiere Kubernetes 1.32 o posterior; en versiones anteriores no tiene efecto y EKS emite un evento de advertencia en el NodeClass |
| `eviction.hard` / `eviction.soft` | Umbrales de desalojo por señal, expresados como cantidad (`500Mi`) o porcentaje (`10%`) | Señales: `memory.available`, `nodefs.available`, `nodefs.inodesFree`, `imagefs.available`, `imagefs.inodesFree`, `pid.available` |
| `eviction.softGracePeriod` | Cuánto tiempo debe mantenerse un umbral flexible antes de que empiece el desalojo | Obligatorio para cada señal que tenga un umbral flexible |
| `eviction.maxPodGracePeriod` | Período de gracia máximo de terminación, en segundos, para los Pods desalojados al alcanzarse un umbral flexible | `0` usa el valor `terminationGracePeriodSeconds` de cada Pod |
| `logging.containerLogMaxSize` / `logging.containerLogMaxFiles` | Tamaño de rotación de los registros de contenedor y cantidad de archivos conservados | `containerLogMaxFiles` debe ser al menos 2 |
| `allowedUnsafeSysctls` | Sysctl no seguros, o patrones terminados en `*`, que los Pods del nodo pueden establecer | Hasta 64 entradas; los patrones permitidos son `kernel.shm*`, `kernel.msg*`, `kernel.sem`, `fs.mqueue.*` y `net.*` |

Revisa estos comportamientos antes de cambiar un NodeClass de producción:

- **Los nodos se reemplazan, no se parchean.** Cambiar la configuración de kubelet en un NodeClass existente marca sus nodos como divergentes y EKS los reemplaza por nodos que usan la nueva configuración. Los ajustes nunca se aplican en el mismo nodo en ejecución, así que revisa primero los presupuestos de interrupción y los PDB.
- **`maxPods` es un límite máximo.** Confirma el resultado en un nodo de reemplazo con `kubectl get node <node> -o jsonpath='{.status.capacity.pods}'` en lugar de dar por sentado que se usará el valor configurado.
- **Los umbrales flexibles deben activarse antes que los estrictos.** Para una misma señal, el umbral flexible debe ser menos agresivo que el umbral estricto. Se pueden combinar una cantidad y un porcentaje; EKS resuelve ambos para cada tipo de instancia y marca como incompatibles con el NodeClass los tipos de instancia que incumplen la regla.
- **`allowedUnsafeSysctls` solo los permite.** Permite que los Pods del nodo soliciten el sysctl; cada Pod debe seguir incluyéndolo en `securityContext.sysctls`. Los valores del kernel a nivel de nodo se establecen por separado mediante `advancedCompute.kernel.sysctl`.

### Configuración de seguridad fija de IMDS

Auto Mode impone IMDSv2 y un límite de saltos de 1; estos valores predeterminados no se pueden cambiar mediante NodeClass. Los Pods normales que no usan la red del host no pueden acceder a IMDS por esa vía, pero esto no garantiza de forma universal el aislamiento de los Pods: `hostNetwork` cambia la accesibilidad. Da preferencia a la identidad de carga de trabajo para el acceso de las aplicaciones a AWS y proporciona explícitamente la región u otra configuración, en vez de depender de los metadatos del nodo.

### KMS del cliente, paquetes de CA y redes independientes para Pods

No pegues un certificado truncado en un manifiesto. Este generador opcional lee la plantilla básica revisada, verifica un paquete PEM público aprobado, lo codifica en base64 en `certificateBundles[].data` y genera un segundo NodeClass completo. Requiere Python 3 con PyYAML. Define `NODE_KMS_KEY_ARN` y `CA_BUNDLE_FILE`, y conserva los valores revisados de `AWS_REGION`/`EXPECTED_ACCOUNT_ID` del capítulo anterior.

Aprueba por separado la entidad emisora de la CA, las huellas digitales y la validez. La comprobación de sintaxis que aparece abajo no demuestra que el paquete sea confiable, que haya permisos de KMS ni que existan los recursos en la nube. Revisa la política de la clave y las concesiones de IAM, así como las selecciones de etiquetas de la red de Pods, antes de aplicar el resultado.

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
|-------|-------------|
| `ephemeralStorage.kmsKeyID` | Clave administrada por el cliente para los volúmenes EBS raíz/de datos del nodo; usa una clave de la región del clúster |
| `certificateBundles[].data` | Paquete de certificados codificado en base64 para la confianza del nodo; no modifica automáticamente el almacén de confianza de contenedores de todas las aplicaciones |
| `podSubnetSelectorTerms` | Subredes independientes para Pods seleccionadas para este NodeClass |
| `podSecurityGroupSelectorTerms` | Grupos de seguridad de la red de Pods; configúralos junto con los selectores de subredes de Pods |

Los selectores de subredes y grupos de seguridad de Pods deben configurarse juntos y tener una cobertura compatible de VPC/AZ. La configuración se aplica por NodeClass, no por espacio de nombres ni por ServiceAccount. El tráfico de la red del host utiliza la red del nodo; el SNAT de salida también puede cambiar la dirección de origen y los grupos de seguridad aplicables. Revisa el enrutamiento, el SNAT y los efectos sobre la densidad de Pods antes de afirmar que todo el tráfico está aislado.

## Separar las cargas de trabajo y los entornos

### Pools de frontend y backend

Las taints impiden que los Pods sin tolerancias coincidentes se ejecuten en estos nodos. Las tolerancias solo permiten la programación; añade un selector o una afinidad obligatoria cuando una carga de trabajo deba usar los nodos designados.

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

Por ejemplo, crea un espacio de nombres `nodepool-lab` bajo tu administración y usa un selector y una tolerancia para comprobar la ubicación en el frontend:

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

Antes de aplicar, ten en cuenta que este Pod puede provocar el aprovisionamiento de nodos facturables. Comprueba el nodo que se le asignó, su disponibilidad y las etiquetas del nodo; luego elimina el Pod de prueba de ese espacio de nombres. `NoSchedule` no expulsa un Pod que ya esté en ejecución, y las etiquetas y taints por sí solas no constituyen un límite de seguridad entre inquilinos no confiables.

### Pool de desarrollo

La lista actual de tipos de instancia compatibles de AWS incluye tipos T de ráfaga además de tipos M. No elimines los tipos T únicamente por suposiciones antiguas sobre Auto Mode. Auto Mode requiere más de una CPU y excluye los tamaños nano/micro/pequeño; aun así, verifica la disponibilidad regional de los tipos, el comportamiento de los créditos de CPU y la idoneidad para la carga de trabajo.

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

`limits.cpu` y `limits.memory` establecen límites a los recursos agregados del pool; no son un número máximo de nodos ni un presupuesto monetario. Pon entre comillas las cantidades de CPU para evitar divergencias de GitOps entre enteros y cadenas. Por ejemplo, `memory: 4000Gi` equivale a 4000 GiB (aproximadamente 3,91 TiB), no exactamente a 4 TB.

La documentación de Karpenter upstream indica que la coherencia eventual y los aprovisionamientos rápidos pueden provocar que se excedan los límites. No prometas un tope instantáneo de facturación basándote en estos campos. Deja margen para los reemplazos, supervisa el uso y prueba el comportamiento del entorno administrado.

`weight` influye en la preferencia de aprovisionamiento entre los pools que cumplan los requisitos. No otorga prioridad del programador de Kubernetes a un nodo, no expulsa las cargas de trabajo existentes ni obliga a un Pod a usar un pool específico. Usa restricciones explícitas para las cargas de trabajo y evita los solapamientos no deseados.

```bash
# Validate against the target cluster's actual schemas; no object is persisted.
kubectl --context "$CLUSTER_NAME" apply --dry-run=server -f custom-nodeclass.yaml
kubectl --context "$CLUSTER_NAME" apply --dry-run=server -f secure-network-nodeclass.json
# After an approved apply, inspect conditions rather than assuming readiness.
kubectl --context "$CLUSTER_NAME" get nodeclasses,nodepools
kubectl --context "$CLUSTER_NAME" describe nodeclass secure-network-nodeclass
kubectl --context "$CLUSTER_NAME" get nodeclaims
```

La simulación del servidor puede comprobar la admisión, pero no demuestra que IAM, la conectividad de red, el aprovisionamiento, el almacenamiento o el comportamiento de la aplicación funcionen correctamente. Resuelve las condiciones de disponibilidad falsas o desconocidas y valida las cargas de trabajo controladas antes de usarlo en producción.

## Referencias

- [NodePools integrados](https://docs.aws.amazon.com/eks/latest/userguide/set-builtin-node-pools.html)
- [Campos y etiquetas de NodePool de Auto Mode](https://docs.aws.amazon.com/eks/latest/userguide/create-node-pool.html)
- [Especificación de NodeClass de Auto Mode](https://docs.aws.amazon.com/eks/latest/userguide/create-node-class.html)
- [Tipos de instancia administrados y restricciones de IMDS](https://docs.aws.amazon.com/eks/latest/userguide/automode-learn-instances.html)
- [Seguridad de los nodos de Auto Mode](https://docs.aws.amazon.com/whitepapers/latest/security-overview-amazon-eks-auto-mode/eks-auto-mode-data-plane.html)
- [Límites de NodePool de Karpenter upstream](https://karpenter.sh/docs/concepts/nodepools/)
- [Aprovisionamiento ponderado de Karpenter](https://karpenter.sh/docs/concepts/scheduling/#weighted-nodepools)
- [Funciones de CA de nodos, KMS y redes](https://aws.amazon.com/blogs/containers/new-amazon-eks-auto-mode-features-for-enhanced-security-network-control-and-performance/)

< [Anterior: Introducción](./01-getting-started.md) | [Índice](./README.md) | [Siguiente: Comportamiento del escalado](./03-scaling-behavior.md) >
