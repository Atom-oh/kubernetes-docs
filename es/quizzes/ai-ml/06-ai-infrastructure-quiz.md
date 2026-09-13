# Cuestionario sobre infraestructura de IA en EKS

15preguntas sobre las APIs actuales y los límites operativos.

## 1. ¿Qué es JARK y está completo automáticamente?

<details>
<summary>Respuesta y explicación</summary>

Un patrón de integración de JupyterHub/Argo Workflows/Ray/Karpenter. Conecta explícitamente identidades, envíos, ejecución, ubicación de Pods, aprovisionamiento de nodos, almacenamiento y autorización.
</details>

## 2. ¿Qué se debe configurar para usar JupyterHub con Cognito?

<details>
<summary>Respuesta y explicación</summary>

URLs de callback/token/userInfo, scopes, claims de nombre de usuario estables y políticas de permiso. Lee el client secret desde un archivo preparado; configura MFA/federación por separado en el proveedor. Una autenticación correcta no implica acceso universal.
</details>

## 3. ¿Cuáles son los roles del head de Ray y de Karpenter?

<details>
<summary>Respuesta y explicación</summary>

GCS es Global Control Service; la planificación interactúa con los raylets. Un head que anuncia CPUs puede ejecutar trabajo. Karpenter aprovisiona nodos según la demanda de los Pods worker y el estado de planificación de Kubernetes.
</details>

## 4. ¿Cómo se deben comparar DRA y los device plugins?

<details>
<summary>Respuesta y explicación</summary>

DRA ofrece solicitudes estructuradas, atributos y asignación mediante DeviceClass/ResourceSlice/ResourceClaim. Los device plugins también admiten MIG/time-slicing; no son universalmente de uso exclusivo. Las funcionalidades dependen de los drivers, el hardware y los gates.
</details>

## 5. ¿Qué es importante sobre los perfiles MIG y el aislamiento?

<details>
<summary>Respuesta y explicación</summary>

3g.20gb describe un perfil, no tres dispositivos de20GB. MIG particiona el hardware pero no sustituye el aislamiento de host/driver/autorización. MPS y time-slicing no son límites de seguridad.
</details>

## 6. ¿Puede una sola versión del GPU Operator establecer todo el soporte de DRA?

<details>
<summary>Respuesta y explicación</summary>

No. Revisa las APIs de Kubernetes, los drivers/hardware/CDI y cada gate individual. GPUCluster del Operator26.7 es mutuamente excluyente con ClusterPolicy; standalone0.5 tiene una protección opt-in frente a colisiones con el device plugin.
</details>

## 7. ¿Qué se debe verificar al integrar Langfuse?

<details>
<summary>Respuesta y explicación</summary>

Verifica las dependencias actuales de SDK/backend, la BD/ClickHouse/almacenamiento de objetos, las credenciales en archivos, el tracing y la retención de datos sensibles. Los Deployments antiguos2.x o las llamadas a trace() no son las APIs actuales4.x.
</details>

## 8. ¿Cómo se deben elegir EFS, FSx y Mountpoint?

<details>
<summary>Respuesta y explicación</summary>

Compara E/S, autorización, alcance de namespace/PVC, capacidad y semántica del sistema de archivos. Las requests de EFS no son cuotas; Mountpoint CSI2.8 usa PVs estáticos para buckets existentes y no es totalmente POSIX.
</details>

## 9. ¿Cómo se deben interpretar el ancho de banda de EFA y el número de interfaces?

<details>
<summary>Respuesta y explicación</summary>

Distingue el ancho de banda agregado de la instancia de los valores por interfaz; no multipliques una cifra que ya es agregada. Verifica la ubicación en la misma AZ, las interfaces, los drivers/libfabric/NCCL, los security groups y los recursos del Pod. RAID0 no habilita EFA.
</details>

## 10. ¿Cómo se deben interpretar las métricas de memoria de GPU y XID?

<details>
<summary>Respuesta y explicación</summary>

FB_USED/FREE son gauges en MiB; una proporción alta no implica necesariamente OOM. XID_ERRORS es un gauge con el último código, no un contador para increase(). Investiga los errores reales, las cachés, los fallos de asignación y los límites propios del dispositivo.
</details>

## 11. ¿La consolidación de Karpenter usa directamente métricas de utilización de GPU?

<details>
<summary>Respuesta y explicación</summary>

Usa las requests de las cargas de trabajo, la viabilidad de planificación, los precios y las restricciones de disrupción, en lugar de un umbral del20% de DCGM. Los limits/budgets no son garantías absolutas de coste o de ausencia de fallos; verifica la terminación y la recuperación.
</details>

## 12. ¿Quién publica los ResourceSlices y qué representan?

<details>
<summary>Respuesta y explicación</summary>

Los drivers publican el inventario real de dispositivos con atributos y capacidad tipados. Crear un slice arbitrario no crea GPUs. CEL y matchAttribute deben seguir el esquema realmente publicado.
</details>

## 13. ¿Solicitar una GPU para Milvus completa el RAG?

<details>
<summary>Respuesta y explicación</summary>

No. Haz coincidir las imágenes e índices admitidos, las dimensiones/revisiones de embeddings, las métricas y parámetros, el filtrado por tenant y el ciclo de vida de actualización/eliminación. Valida la autorización de los resultados y gestiona la ausencia de evidencia.
</details>

## 14. ¿Cómo se deben investigar los Pods de GPU pendientes y los fallos de nodo?

<details>
<summary>Respuesta y explicación</summary>

Contar los Pods pendientes que solicitan GPU no diagnostica la causa. Revisa los eventos, PVCs, afinidad, taints, cuotas, claims e imágenes, y prueba el checkpoint/reanudación. Varios contenedores solicitantes cuentan una sola vez por Pod.
</details>

## 15. ¿MCP proporciona un gateway estándar de autodescubrimiento para Kubernetes?

<details>
<summary>Respuesta y explicación</summary>

No. Define operaciones como el listado y la invocación de herramientas. Elige una release real de servidor/gateway, el transporte y el diseño de autorización. Inventar imágenes/labels/configuración o una variable de entorno con una URL no implementa el descubrimiento ni la ejecución.
</details>

[Volver a la guía](../../ai-ml/06-ai-infrastructure.md)
