# Cuestionario de integración de GPU en EKS Hybrid Nodes

> **Documento relacionado**: [GPU Integration](../../eks-hybrid-nodes/05-gpu-integration.md)
> **Última actualización**: October 12, 2026

### 1. ¿Qué afirmación describe correctamente MIG?

A. Combina varias GPU físicas en una

B. Crea instancias de cómputo/memoria respaldadas por hardware compatibles, mientras persisten las consideraciones de SLO de host/driver y aplicación

C. Garantiza aislamiento completo para cada tenant y cada fallo

D. Es idéntico al time-slicing de software

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Crea instancias de cómputo/memoria respaldadas por hardware compatibles, mientras persisten las consideraciones de SLO de host/driver y aplicación**

**Explicación:** MIG proporciona aislamiento de memoria/fallos y recursos en la capa de hardware de la GPU. Los perfiles/límites compatibles dependen de la SKU de GPU y del driver. Esto no establece seguridad completa del host compartido ni una garantía de latencia de la aplicación.

</details>

### 2. ¿Qué perfil pertenece a la tabla común A10040GB?

A. 4g.40gb

B. 4g.20gb

C. 4g.80gb

D. 1g significa una GPU física completa

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. 4g.20gb**

**Explicación:** Los ejemplos de A10040GB incluyen1g.5gb,2g.10gb,3g.20gb,4g.20gb y7g.40gb.4g.40gb pertenece al conjunto A10080GB. El componente g cuenta los segmentos de cómputo del perfil; las etiquetas nominales de memoria no son garantías exactas de memoria utilizable.

</details>

### 3. ¿Qué proporciona time-slicing replicas:4?

A. Cuatro GPU físicas y cuatro regiones de memoria privadas

B. Cuatro espacios de acceso lógicos por GPU configurada, que comparten su dominio de memoria/fallos

C. Un cuarto de cómputo garantizado para cada Pod

D. Expansión automática de memoria de GPU

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Cuatro espacios de acceso lógicos por GPU configurada, que comparten su dominio de memoria/fallos**

**Explicación:** La contención y el comportamiento de la carga de trabajo pueden cambiar la latencia/el rendimiento. Solicitar más réplicas no garantiza un cómputo proporcional. renameByDefault:true anuncia nvidia.com/gpu.shared; conecte la configuración al plugin real en lugar de crear un ConfigMap sin usar.

</details>

### 4. ¿Qué añade DRA actual a la asignación de GPU?

A. Compatibilidad con GPU sin ningún driver de proveedor

B. Solo solicitudes estáticas de CPU y memoria

C. Selección/asignación estructurada de dispositivos mediante DeviceClasses y ResourceClaims

D. Validación automática de producción de todas las aplicaciones de GPU

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C. Selección/asignación estructurada de dispositivos mediante DeviceClasses y ResourceClaims**

**Explicación:** Aún se requieren un driver de proveedor, ResourceSlices, kubelets/runtime compatibles y API habilitadas. Los claims v1 actuales usan requests[].exactly, y los resourceClaims de Pod hacen referencia directamente a resourceClaimTemplateName.

</details>

### 5. ¿Cómo se debe evaluar un ResourceClaim actual?

A. Esperar un enum universal status.phase:Bound

B. La creación del claim por sí sola demuestra que la GPU se puede usar

C. Inspeccionar allocation.devices.results, las reservas, los eventos de Pod y la preparación del driver

D. Inspeccionar únicamente el campo antiguo resourceHandles

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C. Inspeccionar allocation.devices.results, las reservas, los eventos de Pod y la preparación del driver**

**Explicación:** No existe una secuencia de fase Pending→Allocated→Bound universal almacenada para los ResourceClaims actuales. Una asignación/reserva no demuestra la inyección correcta del dispositivo ni la ejecución de la aplicación.

</details>

### 6. ¿Qué afirmación sobre la propiedad de GPU Operator26.7 es correcta?

A. GPUCluster y ClusterPolicy siempre deben ejecutarse juntos

B. Elija ClusterPolicy para la administración de device-plugin o un nuevo flujo de trabajo GPUCluster para DRA administrado; no pueden coexistir

C. Establecer driver.enabled:false instala un driver de host ausente

D. El nodeSelector del controlador restringe automáticamente cada operando

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Elija ClusterPolicy para la administración de device-plugin o un nuevo flujo de trabajo GPUCluster para DRA administrado; no pueden coexistir**

**Explicación:** GPUCluster es un singleton de ámbito de clúster llamado gpu-cluster. El flujo de trabajo de DRA administrado no es una migración in situ desde ClusterPolicy/DRA independiente. Prepare los componentes adecuados de driver/CDI/detección y revise las etiquetas de los operandos por separado.

</details>

### 7. ¿Qué establece la comparación H100SXM/H200SXM?

A. Cada variante de H100 tiene memoria idéntica

B. NVIDIA enumera80GB/3.35TB/s para H100SXM y141GB/4.8TB/s para H200SXM; los resultados de la aplicación aún requieren medición

C. H200 no admite MIG

D. H200 siempre duplica el rendimiento de cada aplicación

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. NVIDIA enumera80GB/3.35TB/s para H100SXM y141GB/4.8TB/s para H200SXM; los resultados de la aplicación aún requieren medición**

**Explicación:** Estas son especificaciones de SKU del proveedor, no benchmarks de auditoría. Las variantes H100NVL/PCIe difieren. El tamaño del modelo, la precisión, el batching, el software, la interconexión y la contención también afectan al rendimiento real.

</details>

### 8. ¿Qué límite de implementación de GPU en EKS es correcto?

A. Instale un NVIDIA device plugin adicional en cada nodo de Auto Mode

B. DRA no es compatible con ningún tipo de nodo de EKS

C. Use una cohorte de asignación Hybrid con ámbito definido; el Auto Mode de EKS actual no admite el driver NVIDIA DRA y ya administra su device plugin

D. Publique cada GPU física a través de tantos administradores como sea posible

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C. Use una cohorte de asignación Hybrid con ámbito definido; el Auto Mode de EKS actual no admite el driver NVIDIA DRA y ya administra su device plugin**

**Explicación:** AWS recomienda DRA para implementaciones nuevas compatibles de capacidad estática de EKS 1.34+. Use los prerrequisitos de driver documentados y evite la propiedad duplicada de dispositivos. La madurez de la API de Kubernetes es independiente de los feature gates de cada proveedor.

</details>

### 9. Un contenedor solicita una GPU DRA. ¿Cómo debe establecer CUDA_VISIBLE_DEVICES?

A. Establezca siempre0,1,2,3

B. Establezca cada índice físico detectado en el host

C. Use la variable para solicitar tres GPU adicionales

D. Deje que el administrador de dispositivos/runtime exponga los dispositivos asignados; no lo sobrescriba con índices físicos no relacionados

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: D. Deje que el administrador de dispositivos/runtime exponga los dispositivos asignados; no lo sobrescriba con índices físicos no relacionados**

**Explicación:** Los índices de CUDA visibles para el proceso pueden diferir de los índices físicos de GPU. Una sobrescritura manual puede ocultar o identificar erróneamente dispositivos y no concede GPU adicionales. Varios contenedores que hacen referencia a un claim todavía comparten esa única asignación.

</details>

### 10. ¿Qué demuestran los smoke Jobs suspendidos y las comprobaciones de esquema locales?

A. El driver y el modelo de GPU se han ejecutado correctamente

B. Todas las cargas de trabajo de GPU cumplen sus SLO de latencia

C. Los manifests/la configuración revisados superan comprobaciones locales acotadas; la validación de GPU real requiere aprobación y ejecución del propietario

D. No se necesitará verificación de limpieza

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C. Los manifests/la configuración revisados superan comprobaciones locales acotadas; la validación de GPU real requiere aprobación y ejecución del propietario**

**Explicación:** Reemplace la imagen deliberadamente inutilizable con un digest aprobado y verifique runtime/ubicación/seguridad antes de reanudar un Job. Capture los resultados y verifique la despreparación/liberación del claim durante la limpieza. La visibilidad de nvidia-smi por sí sola no es un benchmark de CUDA/LLM.

</details>