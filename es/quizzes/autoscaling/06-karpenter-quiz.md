# Karpenter Quiz

Este cuestionario evalúa tu comprensión de los conceptos del node autoscaler Karpenter, la configuración de NodePool/EC2NodeClass, la optimización de costos, Consolidation, Drift, el manejo de interrupciones y la integración con Amazon EKS.

## Multiple Choice Questions

1. ¿Cuál es la mayor diferencia de Karpenter en comparación con el Cluster Autoscaler existente?
   - A) Requisitos de versión de Kubernetes más altos
   - B) Aprovisionamiento directo de instancias EC2 sin Auto Scaling Groups
   - C) Solo admite AWS y ninguna otra nube
   - D) Solo admite escalado basado en CPU

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Aprovisionamiento directo de instancias EC2 sin Auto Scaling Groups**

**Explicación:**
El mayor diferenciador de Karpenter es que evita Auto Scaling Groups (ASG) y usa directamente la EC2 Fleet API para aprovisionar nodes. Cluster Autoscaler escala mediante node groups/ASGs, por lo que los tipos de instancia están limitados por la configuración del node group. Karpenter selecciona dinámicamente el tipo de instancia óptimo entre varias opciones según los requisitos del pod y puede aprovisionar nodes en segundos.
</details>

2. ¿Qué CRD define las políticas de aprovisionamiento de nodes en la API v1beta1 de Karpenter?
   - A) Provisioner
   - B) NodePool
   - C) NodeTemplate
   - D) EC2NodeClass

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) NodePool**

**Explicación:**
En la API v1beta1 de Karpenter, el CRD Provisioner anterior fue reemplazado por NodePool. NodePool define las políticas de aprovisionamiento de nodes (tipos de instancia, tipos de capacidad, arquitecturas, zonas de disponibilidad, etc.) y la configuración de disruption (consolidation, expireAfter, etc.). EC2NodeClass define configuraciones específicas de AWS (subnets, security groups, AMIs, block devices, etc.), y NodePool referencia EC2NodeClass mediante nodeClassRef.
</details>

3. ¿Cómo configuras Karpenter para usar instancias Spot para optimización de costos?
   - A) disruption.capacityType: spot
   - B) Especificar karpenter.sh/capacity-type: spot en requirements
   - C) Establecer spotEnabled: true en nodeClassRef
   - D) Establecer spot: true en limits

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Especificar karpenter.sh/capacity-type: spot en requirements**

**Explicación:**
Usa la clave `karpenter.sh/capacity-type` en `spec.template.spec.requirements` de NodePool para especificar el tipo de capacidad. Usa `values: ["spot"]` solo para instancias Spot, o `values: ["spot", "on-demand"]` para permitir ambas. Karpenter selecciona instancias óptimas considerando precio y disponibilidad. Las instancias Spot pueden ahorrar hasta un 90% en comparación con On-Demand.
</details>

4. ¿Qué hace la característica Consolidation de Karpenter?
   - A) Consolida logs de múltiples nodes
   - B) Consolida workloads de múltiples nodes en menos nodes para ahorrar costos
   - C) Consolida múltiples clusters en uno
   - D) Consolida múltiples NodePools en uno

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Consolida workloads de múltiples nodes en menos nodes para ahorrar costos**

**Explicación:**
Consolidation es la característica central de optimización de costos de Karpenter. Consolida (bin-packs) workloads de nodes infrautilizados en menos nodes para aumentar la utilización de recursos y reducir costos. `consolidationPolicy: WhenEmpty` solo elimina nodes vacíos, mientras que `consolidationPolicy: WhenUnderutilized` también consolida cuando la utilización es baja. `consolidateAfter` establece el tiempo de espera antes de la consolidación.
</details>

5. ¿Cuál es el propósito de la configuración expireAfter de Karpenter?
   - A) Tiempo máximo que un pod puede ejecutarse en un node
   - B) Tiempo máximo antes de que un node se reemplace automáticamente después de su creación
   - C) Tiempo de expiración de la caché para el controller de Karpenter
   - D) Período de validez de las políticas de NodePool

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Tiempo máximo antes de que un node se reemplace automáticamente después de su creación**

**Explicación:**
La configuración `expireAfter` define la vida útil máxima de un node. Por ejemplo, establecer `expireAfter: 720h` (30 días) reemplaza automáticamente los nodes después de 30 días. Esto es útil para actualizar periódicamente los nodes con parches de seguridad, actualizaciones de AMI y para utilizar tipos de instancia más recientes. Karpenter respeta los PDBs para mover workloads de forma segura a otros nodes antes de terminar los nodes existentes.
</details>

6. ¿Qué campo establece límites de recursos para un NodePool en Karpenter?
   - A) spec.template.limits
   - B) spec.limits
   - C) spec.maxResources
   - D) spec.resourceQuota

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) spec.limits**

**Explicación:**
`spec.limits` de NodePool define los recursos máximos que el NodePool puede aprovisionar. Por ejemplo, `limits: { cpu: 1000, memory: 1000Gi }` limita el aprovisionamiento a un total de 1000 núcleos de CPU y 1000Gi de memoria. Esto permite el control de costos y la gestión de capacidad del cluster. Cuando se alcanzan los límites, Karpenter no aprovisionará nodes adicionales.
</details>

7. ¿Qué detecta y maneja la característica Drift de Karpenter?
   - A) Cambios en el tráfico de red
   - B) Estado en el que los nodes existentes no coinciden con la configuración actual debido a cambios en NodePool/EC2NodeClass
   - C) Drift de scheduling de pods
   - D) Cambios de versión de Kubernetes

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Estado en el que los nodes existentes no coinciden con la configuración actual debido a cambios en NodePool/EC2NodeClass**

**Explicación:**
La característica Drift detecta cuándo cambian las configuraciones de NodePool o EC2NodeClass y los nodes existentes no coinciden con la nueva configuración. Por ejemplo, cuando actualizas una AMI o cambias security groups, los nodes existentes quedan en "drift". Karpenter reemplaza gradualmente estos nodes para que todos los nodes del cluster usen la configuración más reciente. Habilítalo con `featureGates.drift=true`.
</details>

8. ¿Qué campo en EC2NodeClass establece el tamaño y tipo del volumen raíz del node?
   - A) spec.rootVolume
   - B) spec.blockDeviceMappings
   - C) spec.storage
   - D) spec.ebsConfig

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) spec.blockDeviceMappings**

**Explicación:**
`spec.blockDeviceMappings` de EC2NodeClass define la configuración del volumen EBS. Especifica el volumen raíz con `deviceName: /dev/xvda` y configura `volumeSize`, `volumeType`, `iops`, `throughput`, `encrypted`, `kmsKeyID`, etc. en el subcampo `ebs`. Por ejemplo, configura estos atributos adecuadamente para usar un volumen gp3 de 100Gi cifrado.
</details>

## Short Answer Questions

9. ¿Cuál es el tiempo típico para que Karpenter detecte un pod que no se puede programar y aprovisione un node adecuado?

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: En segundos**

**Explicación:**
Karpenter aprovisiona nodes en segundos después de detectar pods que no se pueden programar. Esto contrasta con Cluster Autoscaler, que tarda minutos en escalar mediante ASGs. El escalado rápido de Karpenter proviene de usar directamente la EC2 Fleet API y analizar los requisitos de los pods para seleccionar inmediatamente instancias óptimas. Esta es una gran ventaja para workloads que requieren tráfico por ráfagas o scale-out rápido.
</details>

10. ¿Cómo se determina la prioridad cuando existen múltiples NodePools en Karpenter?

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: Prioridad basada en peso usando el campo weight**

**Explicación:**
Cuando múltiples NodePools pueden satisfacer los requisitos de un pod, usa el campo `spec.weight` para especificar la prioridad. Los NodePools con valores de peso más altos se seleccionan primero. Por ejemplo, establece un peso alto en un NodePool de instancias Spot y un peso bajo en un NodePool On-Demand, y Karpenter intentará usar Spot primero y usará On-Demand si no está disponible.
</details>

11. ¿Qué recurso de Kubernetes respeta Karpenter para garantizar la disponibilidad de workloads al eliminar nodes?

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: PDB (PodDisruptionBudget)**

**Explicación:**
Karpenter respeta PodDisruptionBudget (PDB) al eliminar nodes (consolidation, expiration, drift, etc.). PDB define la disponibilidad mínima de la aplicación, y Karpenter solo drena nodes dentro de límites que no infrinjan el PDB. Por ejemplo, con una configuración de PDB `minAvailable: 2`, Karpenter garantiza que al menos 2 pods estén siempre en ejecución mientras elimina nodes.
</details>

12. ¿Cómo selecciona Karpenter las subnets y security groups que se usarán en EC2NodeClass?

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: Selección basada en tags mediante subnetSelectorTerms y securityGroupSelectorTerms**

**Explicación:**
EC2NodeClass usa `subnetSelectorTerms` y `securityGroupSelectorTerms` para la selección basada en tags de subnets y security groups. Por ejemplo, `tags: { karpenter.sh/discovery: "my-cluster" }` selecciona recursos con ese tag. Los recursos de AWS deben etiquetarse previamente y, cuando se seleccionan múltiples subnets, Karpenter las distribuye adecuadamente para la distribución entre zonas de disponibilidad.
</details>

## Hands-on Questions

13. Escribe un NodePool que priorice instancias Spot, permita varios tipos de instancia (familias m5, c5, r5) y elimine nodes vacíos después de 30 minutos.

<details>

<summary>Mostrar respuesta</summary>

**Respuesta:**
```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: cost-optimized
spec:
  template:
    metadata:
      labels:
        nodepool: cost-optimized
    spec:
      requirements:
        - key: karpenter.sh/capacity-type
          operator: In
          values: ["spot", "on-demand"]
        - key: kubernetes.io/arch
          operator: In
          values: ["amd64"]
        - key: node.kubernetes.io/instance-type
          operator: In
          values:
            - m5.large
            - m5.xlarge
            - m5.2xlarge
            - c5.large
            - c5.xlarge
            - c5.2xlarge
            - r5.large
            - r5.xlarge
            - r5.2xlarge
      nodeClassRef:
        apiVersion: karpenter.k8s.aws/v1
        kind: EC2NodeClass
        name: default
  limits:
    cpu: 1000
    memory: 1000Gi
  disruption:
    consolidationPolicy: WhenEmpty
    consolidateAfter: 30m
  weight: 100
```

**Explicación:**
Este NodePool prioriza las instancias Spot para la optimización de costos (listando spot primero en `capacity-type`). Permitir varios tipos de instancia mejora la disponibilidad de Spot y la optimización de precios. `consolidationPolicy: WhenEmpty` con `consolidateAfter: 30m` elimina nodes que están vacíos durante 30 minutos. `weight: 100` establece una prioridad más alta que otros NodePools, por lo que este NodePool se selecciona primero.
</details>

14. Escribe un EC2NodeClass con un volumen raíz gp3 de 100Gi cifrado, selección de subnet/security group basada en tags y configuraciones que requieran IMDSv2.

<details>

<summary>Mostrar respuesta</summary>

**Respuesta:**
```yaml
apiVersion: karpenter.k8s.aws/v1
kind: EC2NodeClass
metadata:
  name: secure-nodeclass
spec:
  amiFamily: AL2

  subnetSelectorTerms:
    - tags:
        karpenter.sh/discovery: "my-cluster"
        kubernetes.io/role: "private"

  securityGroupSelectorTerms:
    - tags:
        karpenter.sh/discovery: "my-cluster"

  instanceProfile: KarpenterNodeInstanceProfile-my-cluster

  blockDeviceMappings:
    - deviceName: /dev/xvda
      ebs:
        volumeSize: 100Gi
        volumeType: gp3
        iops: 3000
        throughput: 125
        encrypted: true
        deleteOnTermination: true

  metadataOptions:
    httpEndpoint: enabled
    httpProtocolIPv6: disabled
    httpPutResponseHopLimit: 2
    httpTokens: required  # IMDSv2 required

  tags:
    Environment: production
    ManagedBy: karpenter
```

**Explicación:**
Este EC2NodeClass sigue las mejores prácticas de seguridad. `blockDeviceMappings` configura un volumen gp3 de 100Gi con cifrado. `metadataOptions.httpTokens: required` hace que IMDSv2 sea obligatorio para prevenir ataques SSRF. Los selectores basados en tags configuran el uso únicamente de subnets privadas. `instanceProfile` referencia un IAM instance profile creado previamente.
</details>

15. Escribe comandos para verificar el estado de instalación de Karpenter y depurar problemas de aprovisionamiento.

<details>

<summary>Mostrar respuesta</summary>

**Respuesta:**
```bash
# 1. Check Karpenter pod status
kubectl get pods -n karpenter

# 2. Check Karpenter controller logs
kubectl logs -n karpenter -l app.kubernetes.io/name=karpenter -c controller

# 3. Check NodePool status
kubectl get nodepool
kubectl describe nodepool default

# 4. Check EC2NodeClass status
kubectl get ec2nodeclass
kubectl describe ec2nodeclass default

# 5. Check pods waiting to be scheduled
kubectl get pods --all-namespaces --field-selector status.phase=Pending

# 6. Check nodes created by Karpenter
kubectl get nodes -l karpenter.sh/nodepool

# 7. Check node details and labels/taints
kubectl describe node <node-name>

# 8. Check Karpenter events
kubectl get events --field-selector source=karpenter --sort-by='.lastTimestamp'

# 9. Check detailed provisioning logs
kubectl logs -n karpenter -l app.kubernetes.io/name=karpenter -c controller | grep -i "provisioning\|creating\|launching"

# 10. Check Karpenter metrics (if Prometheus is configured)
kubectl port-forward -n karpenter svc/karpenter 8080:8080 &
curl localhost:8080/metrics | grep karpenter_
```

**Explicación:**
Al solucionar problemas de Karpenter, revisa varios aspectos. Primero verifica que los pods del controller se estén ejecutando normalmente y que los logs no tengan errores. Revisa el estado y la configuración de NodePool y EC2NodeClass. Comprueba los pods en Pending y sus razones. Los problemas comunes incluyen permisos IAM insuficientes, problemas con tags de subnet/security group y límites de instancia. Los eventos y métricas de Karpenter también son útiles para el diagnóstico.
</details>

---

**Puntuación:**
- 13-15 correctas: Excelente (nivel experto en Karpenter)
- 10-12 correctas: Bueno (capaz de aplicación práctica)
- 7-9 correctas: Promedio (se recomienda aprendizaje adicional)
- 0-6 correctas: Insuficiente (se necesita revisar los conceptos básicos)

[Volver a los materiales de aprendizaje](../../autoscaling/02-karpenter.md)
