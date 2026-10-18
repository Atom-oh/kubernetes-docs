# Cuestionario sobre infraestructura de IA en EKS

15 preguntas sobre las APIs actuales y los límites operativos.

## 1. ¿Qué es JARK y está completo automáticamente?

<details>
<summary>Respuesta y explicación</summary>

Es un patrón de integración de JupyterHub/Argo Workflows/Ray/Karpenter. Debes conectar explícitamente las identidades, el envío de trabajos, su ejecución, la ubicación de los Pods, el aprovisionamiento de nodos, el almacenamiento y la autorización.
</details>

## 2. ¿Qué se debe configurar para usar JupyterHub con Cognito?

<details>
<summary>Respuesta y explicación</summary>

Las URL de callback, de token y de userInfo; los scopes; las claims estables del nombre de usuario; y las políticas que autorizan el acceso. Lee el secreto del cliente desde un archivo preparado y configura MFA y la federación por separado en el proveedor. Autenticarse correctamente no concede acceso universal.
</details>

## 3. ¿Qué funciones cumplen el nodo head de Ray y Karpenter?

<details>
<summary>Respuesta y explicación</summary>

GCS significa Global Control Service; el planificador interactúa con los raylets. Un nodo head que anuncia CPU también puede ejecutar trabajo. Karpenter aprovisiona nodos según la demanda de los Pods de los workers y el estado de planificación de Kubernetes.
</details>

## 4. ¿Cómo se deben comparar DRA y los device plugins?

<details>
<summary>Respuesta y explicación</summary>

DRA ofrece solicitudes estructuradas, atributos y asignación mediante DeviceClass/ResourceSlice/ResourceClaim. Los complementos de dispositivos también admiten MIG y time-slicing; no se limitan siempre a la asignación exclusiva. Las funciones dependen de los controladores, el hardware y los feature gates.
</details>

## 5. ¿Qué es importante sobre los perfiles MIG y el aislamiento?

<details>
<summary>Respuesta y explicación</summary>

3g.20gb describe un perfil, no tres dispositivos de 20 GB. MIG particiona el hardware, pero no sustituye el aislamiento del host, los controladores ni la autorización. MPS y time-slicing no son límites de seguridad.
</details>

## 6. ¿Puede una sola versión del GPU Operator establecer todo el soporte de DRA?

<details>
<summary>Respuesta y explicación</summary>

No. Revisa las API de Kubernetes, los controladores, el hardware, CDI y cada feature gate por separado. GPUCluster de GPU Operator 26.7 es mutuamente excluyente con ClusterPolicy; la versión standalone 0.5 tiene una protección opt-in contra conflictos con el complemento de dispositivos.
</details>

## 7. ¿Qué se debe verificar al integrar Langfuse?

<details>
<summary>Respuesta y explicación</summary>

Verifica las dependencias actuales del SDK y el backend, la base de datos, ClickHouse y el almacenamiento de objetos, las credenciales en archivos, el trazado y la retención de datos sensibles. Los Deployments antiguos de la versión 2.x o las llamadas a trace() no corresponden a las API actuales de la versión 4.x.
</details>

## 8. ¿Cómo se deben elegir EFS, FSx y Mountpoint?

<details>
<summary>Respuesta y explicación</summary>

Compara la entrada/salida, la autorización, el alcance del espacio de nombres/PVC, la capacidad y la semántica del sistema de archivos. Las solicitudes de almacenamiento de EFS no son cuotas; Mountpoint CSI 2.8 usa PV estáticos para buckets existentes y no ofrece compatibilidad POSIX completa.
</details>

## 9. ¿Cómo se deben interpretar el ancho de banda de EFA y el número de interfaces?

<details>
<summary>Respuesta y explicación</summary>

Distingue el ancho de banda total de la instancia de los valores por interfaz; no multipliques una cifra que ya sea total. Verifica que las instancias estén en la misma AZ, así como las interfaces, los controladores, libfabric, NCCL, los grupos de seguridad y los recursos del Pod. RAID0 no habilita EFA.
</details>

## 10. ¿Cómo se deben interpretar las métricas de memoria de GPU y XID?

<details>
<summary>Respuesta y explicación</summary>

FB_USED/FREE son indicadores tipo gauge en MiB; una proporción alta no implica necesariamente un error de memoria agotada (OOM). XID_ERRORS es el indicador tipo gauge del último código, no un contador para increase(). Investiga los errores reales, las cachés, los fallos de asignación y los límites específicos del dispositivo.
</details>

## 11. ¿La consolidación de Karpenter usa directamente métricas de utilización de GPU?

<details>
<summary>Respuesta y explicación</summary>

Usa las solicitudes de recursos de las cargas de trabajo, la posibilidad de programarlas, los precios y las restricciones de interrupción, no un umbral de DCGM del 20 %. Los límites y presupuestos no garantizan un coste máximo ni que no haya fallos; verifica la terminación y la recuperación.
</details>

## 12. ¿Quién publica los ResourceSlices y qué representan?

<details>
<summary>Respuesta y explicación</summary>

Los controladores publican el inventario real de dispositivos con atributos tipados y su capacidad. Crear un slice arbitrario no crea GPU. CEL y matchAttribute deben ajustarse al esquema publicado.
</details>

## 13. ¿Solicitar una GPU para Milvus completa el RAG?

<details>
<summary>Respuesta y explicación</summary>

No. Asegúrate de que coincidan las imágenes e índices admitidos, las dimensiones y revisiones de las incrustaciones, las métricas y los parámetros, el filtrado por inquilino y el ciclo de vida de actualización y eliminación. Valida la autorización de los resultados y gestiona la ausencia de evidencia.
</details>

## 14. ¿Cómo se deben investigar los Pods de GPU pendientes y los fallos de nodo?

<details>
<summary>Respuesta y explicación</summary>

No basta con contar los Pods pendientes que solicitan GPU para diagnosticar la causa. Revisa los eventos, los PVC, la afinidad, las taints, las cuotas, los claims y las imágenes, y prueba los puntos de control y la reanudación. Si varios contenedores de un Pod solicitan GPU, el Pod se cuenta una sola vez.
</details>

## 15. ¿MCP proporciona un gateway estándar de autodescubrimiento para Kubernetes?

<details>
<summary>Respuesta y explicación</summary>

No. Define operaciones como listar y llamar herramientas. Elige una versión publicada del servidor o la pasarela, el transporte y el diseño de autorización. Inventar imágenes, etiquetas, configuración o una variable de entorno con una URL no implementa el autodescubrimiento ni la ejecución.
</details>

[Volver a la guía](../../ai-ml/06-ai-infrastructure.md)
