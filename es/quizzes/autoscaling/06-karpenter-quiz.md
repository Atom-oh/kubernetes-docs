# Cuestionario de Karpenter

> **Última actualización**: 11 de septiembre de 2026

Este cuestionario evalúa tu comprensión de los conceptos del autoscaler de nodos Karpenter, la configuración de NodePool y EC2NodeClass, la optimización de costos, Consolidation, Drift, el manejo de interrupciones y la integración con Amazon EKS.

## Preguntas de opción múltiple

1. En este ejemplo de AWS, ¿qué diferencia arquitectónica distingue a Karpenter de Cluster Autoscaler?
   - A) Requisitos de versión de Kubernetes más altos
   - B) Aprovisionamiento directo de instancias EC2 sin Auto Scaling Groups
   - C) Solo admite AWS y ninguna otra nube
   - D) Solo admite el escalado basado en CPU

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Aprovisionamiento directo de instancias EC2 sin Auto Scaling Groups**

**Explicación:**
Con el proveedor de AWS, Karpenter solicita capacidad de EC2 (incluida EC2 Fleet) mediante NodeClaims, en lugar de escalar un Auto Scaling Group. Cluster Autoscaler suele ajustar grupos de nodos configurados. Las opciones de instancia siguen dependiendo de las restricciones de Pod, NodePool y NodeClass, las cuotas y la disponibilidad. El tiempo de lanzamiento de la API, el tiempo hasta que el nodo esté Ready y el tiempo hasta que la aplicación esté lista son etapas distintas; no se garantiza que todo ocurra en unos segundos.
</details>

2. ¿Qué CRD define las políticas de aprovisionamiento de nodos (tipos de instancia, tipos de capacidad y configuración de interrupciones) en la API v1 de Karpenter?
   - A) NodeClaim
   - B) NodePool
   - C) NodeTemplate
   - D) EC2NodeClass

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) NodePool**

**Explicación:**
NodePool (`karpenter.sh/v1`) define los requisitos de la plantilla y la política del ciclo de vida. `expireAfter` se configura en `spec.template.spec`, mientras que la consolidación y los presupuestos se configuran en `spec.disruption`. EC2NodeClass (`karpenter.k8s.aws/v1`) proporciona la configuración de AWS mediante `nodeClassRef`. NodeClaim registra la capacidad solicitada y el ciclo de vida de un nodo individual.
</details>

3. ¿Cómo se configura Karpenter para usar instancias Spot y optimizar costos?
   - A) `disruption.capacityType: spot`
   - B) Especificar `karpenter.sh/capacity-type: spot` en los requisitos
   - C) Establecer `spotEnabled: true` en `nodeClassRef`
   - D) Establecer `spot: true` en `limits`

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Especificar `karpenter.sh/capacity-type: spot` en los requisitos**

**Explicación:**
Los requisitos de NodePool pueden permitir capacidad Spot, On-Demand y, cuando esté configurada, Reserved. Los valores de un requisito `In` forman un conjunto: su orden no expresa preferencia. Entre los tipos de capacidad permitidos, Karpenter prioriza Reserved, luego Spot y después On-Demand, sujeto a las ofertas disponibles y a las demás restricciones. El precio y la exposición a interrupciones de Spot varían; el ahorro no está garantizado.
</details>

4. ¿Qué hace la función Consolidation de Karpenter?
   - A) Consolida los registros de varios nodos
   - B) Evalúa la eliminación viable de nodos o su reemplazo por otros de menor costo, respetando las restricciones de las cargas de trabajo
   - C) Consolida varios clústeres en uno
   - D) Consolida varios NodePools en uno

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Evalúa la eliminación viable de nodos o su reemplazo por otros de menor costo, respetando las restricciones de las cargas de trabajo**

**Explicación:**
Consolidation busca eliminar nodos cuando sea viable o reemplazarlos por otros de menor costo, respetando las restricciones de las cargas de trabajo y los controles de interrupción aplicables. Puede eliminar un nodo, reemplazarlo por uno más barato o consolidar varios; por lo tanto, el número de nodos no siempre disminuye. `WhenEmpty` limita la consolidación a los nodos vacíos que cumplan los requisitos. `consolidateAfter` es un período de espera para que el nodo sea elegible después de cambios pertinentes en los Pods; no es un plazo de terminación garantizado ni un umbral de utilización de CPU.
</details>

5. ¿Para qué sirve el parámetro `expireAfter` de Karpenter?
   - A) Tiempo máximo que un Pod puede ejecutarse en un nodo
   - B) Antigüedad del nodo a partir de la cual comienza el drenaje por expiración
   - C) Tiempo de expiración de la caché del controlador de Karpenter
   - D) Período de validez de las políticas de NodePool

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Antigüedad del nodo a partir de la cual comienza el drenaje por expiración**

**Explicación:**
Cuando el nodo alcanza esa antigüedad, `expireAfter` inicia el drenaje por expiración. Un PDB que lo bloquee o un Pod con `do-not-disrupt` puede retrasar la finalización si no se ha configurado `terminationGracePeriod`. Si se configura ese período de gracia, al vencer se pueden eliminar por la fuerza los Pods restantes; las fechas límite de interrupciones externas también pueden retirar capacidad. El reemplazo utiliza AMI y tipos elegibles según la configuración actual, que no necesariamente son más recientes. La expiración no garantiza que el reemplazo esté `Ready` primero.
</details>

6. ¿Qué campo establece los límites de recursos de un NodePool en Karpenter?
   - A) `spec.template.limits`
   - B) `spec.limits`
   - C) `spec.maxResources`
   - D) `spec.resourceQuota`

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) `spec.limits`**

**Explicación:**
`spec.limits` limita los recursos totales de un NodePool dinámico. Las cantidades en forma de cadena, como `cpu: "1000"`, evitan diferencias de tipo en la API o en GitOps. Como la comprobación de límites es eventualmente consistente durante el aprovisionamiento en paralelo, un escalado rápido puede superar temporalmente el límite. No es un tope estricto de costos o facturación.
</details>

7. ¿Qué detecta y gestiona la función Drift de Karpenter?
   - A) Cambios en el tráfico de red
   - B) El estado en que los nodos existentes no coinciden con la configuración actual debido a cambios en NodePool o EC2NodeClass
   - C) Drift en la programación de Pods
   - D) Cambios en la versión de Kubernetes

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) El estado en que los nodos existentes no coinciden con la configuración actual debido a cambios en NodePool o EC2NodeClass**

**Explicación:**
Drift compara los NodeClaims existentes con la configuración deseada o resuelta que corresponda. Algunos cambios no causan drift (por ejemplo, los cambios en el peso o en los presupuestos), y un selector de AMI mutable puede resolver una AMI distinta aunque no se haya editado el manifiesto. La gestión de drift está sujeta a los controles de interrupción y no garantiza que todos los nodos converjan de inmediato. Drift es estable en v1; la antigua puerta de funcionalidad para drift ya no existe.
</details>

8. ¿Qué campo de EC2NodeClass configura el tamaño y tipo del volumen raíz del nodo?
   - A) `spec.rootVolume`
   - B) `spec.blockDeviceMappings`
   - C) `spec.storage`
   - D) `spec.ebsConfig`

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) `spec.blockDeviceMappings`**

**Explicación:**
`spec.blockDeviceMappings` configura los dispositivos EBS. En el ejemplo de AL2023, el mapeo raíz es `/dev/xvda`; para otras imágenes, incluidas las que usan un dispositivo de datos separado como Bottlerocket, utiliza el esquema propio de la familia de AMI. El tamaño, el tipo, el cifrado y los permisos de KMS deben corresponder a los volúmenes previstos. Un mapeo EBS adicional no formatea ni monta automáticamente un sistema de archivos.
</details>

## Preguntas de respuesta breve

9. ¿Qué etapas se deben medir para evaluar la latencia del escalado horizontal de Karpenter?

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: Mide las etapas del aprovisionamiento y de la puesta en servicio; no existe una duración fija universal.**

**Explicación:**
Mide la detección y agrupación de la demanda, la solicitud a EC2 y la obtención de capacidad, el arranque y la configuración inicial, el registro del nodo y su transición a `Ready`, y después la descarga de imágenes y la disponibilidad de la aplicación. Los reintentos de IAM o de la API, la capacidad de direcciones IP, el almacenamiento y la inicialización de la aplicación afectan etapas distintas. El documento no contiene mediciones históricas que demuestren una comparación universal de duración con Cluster Autoscaler.
</details>

10. ¿Cómo se determina la prioridad cuando hay varios NodePools en Karpenter?

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: Mediante la preferencia relativa definida por el campo `weight`.**

**Explicación:**
Para los NodePools dinámicos que sean elegibles, un valor más alto en `spec.weight` expresa una preferencia de aprovisionamiento. La agrupación de las solicitudes de programación, los requisitos de las cargas de trabajo, la capacidad existente, los límites de NodePool y la falta de ofertas disponibles pueden llevar a seleccionar otro pool. No es una garantía absoluta por Pod ni una proporción fija entre Spot y On-Demand; los NodePools estáticos tienen restricciones propias. La preferencia de tipo de capacidad dentro de un mismo pool es independiente del orden del arreglo.
</details>

11. ¿Qué recurso de Kubernetes limita la expulsión voluntaria de Pods durante la retirada de un nodo?

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: PDB (`PodDisruptionBudget`)**

**Explicación:**
Un PDB restringe las expulsiones voluntarias según la cantidad de réplicas coincidentes que estén sanas. No crea esas réplicas ni impide la pérdida involuntaria de una instancia, una reparación forzada o la eliminación al vencer un `terminationGracePeriod` configurado. `minAvailable: 2` es una restricción para la expulsión, no una promesa de que siempre haya dos Pods en ejecución o atendiendo tráfico.
</details>

12. ¿Cómo selecciona Karpenter las subnets y los grupos de seguridad que se usarán en EC2NodeClass?

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: Mediante `subnetSelectorTerms` y `securityGroupSelectorTerms`, que admiten tags o ID y otros selectores documentados.**

**Explicación:**
Los selectores admiten tags o ID de recursos explícitos (y nombres de grupos de seguridad cuando corresponda). Las condiciones dentro de un término se combinan con AND; los términos se combinan con OR. Dentro de una zona de disponibilidad seleccionada, Karpenter suele elegir la subnet coincidente que tenga más direcciones IP disponibles. Esto por sí solo no garantiza una distribución uniforme entre zonas ni rutas privadas; verifica la topología, las rutas y los grupos de seguridad reales.
</details>

## Preguntas prácticas

13. Escribe un NodePool dinámico que permita Spot con On-Demand como alternativa, admita tipos m5/c5/r5 y haga que los nodos vacíos sean elegibles para consolidación después de 30 minutos.

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
        values:
        - spot
        - on-demand
      - key: kubernetes.io/arch
        operator: In
        values:
        - amd64
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
        group: karpenter.k8s.aws
        kind: EC2NodeClass
        name: default
  limits:
    cpu: '1000'
    memory: 1000Gi
  disruption:
    consolidationPolicy: WhenEmpty
    consolidateAfter: 30m
  weight: 100
```

**Explicación:**
La preferencia por Spot procede de la política de tipos de capacidad de Karpenter, no de poner `spot` primero en la lista. Una gama más amplia de tipos elegibles puede ofrecer más opciones, pero no garantiza que haya capacidad. `WhenEmpty` con `consolidateAfter: 30m` hace que los nodos vacíos elegibles puedan consolidarse después de esa espera; los presupuestos, los PDB y la reconciliación pueden aplazar su eliminación. `weight: 100` expresa solo una preferencia relativa. El EC2NodeClass `default` y la identidad del nodo referenciados ya deben ser válidos.
</details>

14. Escribe un EC2NodeClass con un volumen raíz gp3 cifrado de 100 GiB, selección de subnet y grupo de seguridad basada en tags, y opciones que exijan IMDSv2.

<details>

<summary>Mostrar respuesta</summary>

**Respuesta:**
```yaml
apiVersion: karpenter.k8s.aws/v1
kind: EC2NodeClass
metadata:
  name: secure-nodeclass
spec:
  amiSelectorTerms:
  - alias: al2023@latest
  subnetSelectorTerms:
  - tags:
      karpenter.sh/discovery: my-cluster
      example.com/network-role: private
  securityGroupSelectorTerms:
  - tags:
      karpenter.sh/discovery: my-cluster
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
    httpPutResponseHopLimit: 1
    httpTokens: required
  tags:
    Environment: production
    ManagedBy: karpenter
```

**Explicación:**
Este es un ejemplo didáctico de AL2023. `@latest` puede resolver una AMI distinta y provocar drift; antes de implementarlo en producción, fija y prueba una versión aprobada o una AMI específica. La etiqueta privada es personalizada y debe existir en las subnets cuyas rutas hayas verificado. IMDSv2 reduce varias vías de ataque a los metadatos, pero no impide universalmente SSRF; el límite de salto 1 restringe muchas rutas desde contenedores sin `hostNetwork` y debe probarse con la configuración de CNI e identidad de las cargas de trabajo. El perfil de instancia indicado, el acceso del nodo, la configuración de KMS y volúmenes y las rutas de red son requisitos previos.
</details>

15. Escribe comandos para verificar el estado de la instalación de Karpenter y depurar problemas de aprovisionamiento.

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
kubectl get events --all-namespaces --sort-by='.metadata.creationTimestamp'
kubectl get nodeclaims -o wide

# 9. Check detailed provisioning logs
kubectl logs -n karpenter -l app.kubernetes.io/name=karpenter -c controller | grep -i "provisioning\|creating\|launching"

# 10. Forward the metrics endpoint; keep this terminal open until done.
kubectl port-forward -n karpenter svc/karpenter 8080:8080
```

En otra terminal, después de que aparezca el mensaje que confirma que el reenvío está listo:

```bash
curl --fail --show-error http://127.0.0.1:8080/metrics | grep karpenter_
```

**Explicación:**
Revisa conjuntamente la disponibilidad del controlador, las condiciones de NodePool, EC2NodeClass y NodeClaim, los eventos de programación de Pods y los requisitos previos del lado de AWS. Un Pod en `Pending` no implica necesariamente que falte capacidad de cómputo, y no encontrar una línea de registro filtrada no demuestra que todo funcione. Ejecuta `port-forward` en una terminal aparte, espera el mensaje de disponibilidad, consulta las métricas desde otra terminal y luego detenlo con Ctrl+C. No se requiere un servidor Prometheus para leer directamente estas métricas; ninguno de estos comandos se ejecutó contra un clúster.
</details>

---

**Puntuación:**
- 13-15 correctas: Excelente (nivel experto en Karpenter)
- 10-12 correctas: Bueno (capacidad de aplicación práctica)
- 7-9 correctas: Promedio (se recomienda seguir aprendiendo)
- 0-6 correctas: Insuficiente (se recomienda repasar los conceptos básicos)

[Volver a los materiales de aprendizaje](../../autoscaling/02-karpenter.md)
