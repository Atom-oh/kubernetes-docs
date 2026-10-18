# Cuestionario sobre Feature Flags y OpenFeature

1. ¿Cuál es la principal ventaja del modelo Provider de OpenFeature?
   - A) El bloqueo con un proveedor ofrece un rendimiento óptimo
   - B) Una API de evaluación independiente del proveedor reduce los cambios de código al cambiar de backend
   - C) Requiere ejecutar tu propio servidor de Feature Flags
   - D) Solo admite la API REST

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Una API de evaluación independiente del proveedor reduce los cambios de código al cambiar de backend**

**Explicación:**
La API SDK independiente del proveedor de OpenFeature reduce los cambios en el código de evaluación al cambiar de backend. Las claves de flags, las variantes, las reglas de segmentación, la semántica del contexto, las credenciales, el almacenamiento en caché y el comportamiento de los eventos siguen requiriendo migración y pruebas.

</details>

---

2. ¿Cuál es la diferencia entre los modos de despliegue Sidecar y Standalone de flagd en Kubernetes?
   - A) Sidecar tiene mejor rendimiento y Standalone es más fácil de administrar
   - B) Sidecar se ejecuta dentro del Pod de una aplicación, mientras que Standalone ofrece evaluaciones mediante un Service compartido
   - C) Sidecar solo admite TCP y Standalone solo admite HTTP
   - D) Sidecar usa CRDs y Standalone solo usa ConfigMaps

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Sidecar se ejecuta dentro del Pod de una aplicación, mientras que Standalone ofrece evaluaciones mediante un Service compartido**

**Explicación:**
Las llamadas RPC pueden dirigirse a un sidecar local o a un Deployment compartido a través de un Service. Mide la latencia y el uso de recursos reales. Sidecar/deployment compartido describe dónde se ejecuta flagd; RPC/en proceso describe dónde se evalúan los flags. Un provider en proceso puede sincronizar las reglas y evaluarlas dentro de la aplicación.

</details>

---

3. ¿Qué función tiene la información incluida en el Evaluation Context de un Feature Flag?
   - A) Pasar información de compilación para determinar flags en tiempo de compilación
   - B) Evaluar reglas de segmentación con datos contextuales, como ID de usuario, región y entorno
   - C) Pasar información de conexión a la base de datos
   - D) Pasar información de nodos de Kubernetes

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Evaluar reglas de segmentación con datos contextuales, como ID de usuario, región y entorno**

**Explicación:**
Evaluation Context son metadatos que se pasan dinámicamente durante la evaluación de un flag. Incluyen información como ID de usuario, región, entorno (dev/staging/prod) y grupos de usuarios. Las reglas de segmentación usan esta información para habilitar funciones para usuarios o grupos específicos. Para decisiones relacionadas con derechos de acceso, usa atributos verificados en el servidor; los feature flags no sustituyen la autenticación ni la autorización.

</details>

---

4. ¿Qué función tienen los Feature Flags en el patrón Dark Launch?
   - A) Ocultar por completo un servicio y bloquear el acceso
   - B) Devolver el resultado existente mientras se prueba la lógica nueva mediante una ejecución en sombra sin efectos secundarios
   - C) Cambiar los servidores al modo oscuro
   - D) Ejecutar despliegues únicamente de noche

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Devolver el resultado existente mientras se prueba la lógica nueva mediante una ejecución en sombra sin efectos secundarios**

**Explicación:**
La validación en sombra devuelve el resultado existente y compara cálculos de solo lectura o reproducciones aisladas. No debe cobrar, escribir registros de negocio ni enviar notificaciones dos veces. Limita la concurrencia asíncrona y asigna su propio tiempo de espera al trabajo en segundo plano. Esto difiere de una publicación gradual que sí expone el resultado nuevo a usuarios seleccionados.

</details>

---

5. ¿Qué ventaja ofrece Feature Flag as Code (GitOps)?
   - A) Los flags solo se pueden administrar mediante una interfaz gráfica
   - B) Gestionar los cambios de flags mediante PR de Git permite revisarlos, auditarlos y revertirlos
   - C) La evaluación de flags es más rápida
   - D) Se ahorran recursos del servidor

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Gestionar los cambios de flags mediante PR de Git permite revisarlos, auditarlos y revertirlos**

**Explicación:**
Gestionar los recursos CR de FeatureFlag en Git proporciona revisión mediante PR, historial de cambios y la posibilidad de revertirlos con Git. Los consumidores aún requieren la reconciliación de ArgoCD/Flux, la sincronización de la fuente y la actualización del estado del SDK. La autorreparación puede deshacer una corrección manual urgente; por eso, hay que considerar conjuntamente la propiedad y el comportamiento de reconciliación.

</details>

---

6. ¿Cuál es la mejor práctica para evitar la deuda técnica de los Feature Flags?
   - A) Mantener todos los flags para siempre
   - B) Definir fechas de vencimiento para los flags y limpiar su código al terminar el lanzamiento
   - C) Crear flags sin límite de cantidad
   - D) No incluir fechas en los nombres de los flags

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Definir fechas de vencimiento para los flags y limpiar su código al terminar el lanzamiento**

**Explicación:**
Registra a los responsables y las fechas de revisión, y comprueba si las versiones anteriores de la aplicación u otros consumidores siguen usando el código y la configuración antes de eliminarlos. Los metadatos de vencimiento no borran un flag por sí solos. Los flags operativos permanentes pueden requerir revisiones periódicas en vez de eliminación.

</details>

---

7. ¿Qué funcionalidad principal ofrece el OpenFeature Operator en Kubernetes?
   - A) Inyectar automáticamente sidecars de flagd en los Pods y administrar recursos CRD de FeatureFlag
   - B) Auditar la seguridad del clúster de Kubernetes
   - C) Crear automáticamente imágenes de contenedor
   - D) Configurar automáticamente HPA

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A) Inyectar automáticamente sidecars de flagd en los Pods y administrar recursos CRD de FeatureFlag**

**Explicación:**
El Operator administra recursos como FeatureFlag y FeatureFlagSource. La inyección en Pods usa las anotaciones openfeature.dev/enabled y openfeature.dev/featureflagsource. Los volúmenes ConfigMap de origen de archivos, el acceso directo a Kubernetes y los orígenes de proxy siguen rutas de sincronización distintas. La aplicación aún requiere integración con el SDK.

</details>

---

8. ¿Cómo funciona el despliegue automático basado en métricas al combinar Flagger y Feature Flags?
   - A) Feature Flags controlan directamente el tráfico
   - B) Flagger gestiona el cambio del tráfico Canary, mientras que los Feature Flags controlan la exposición gradual de funciones en la aplicación
   - C) Feature Flags sustituyen por completo a Flagger
   - D) Ambas herramientas usan métricas idénticas

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Flagger gestiona el cambio del tráfico Canary, mientras que los Feature Flags controlan la exposición gradual de funciones en la aplicación**

**Explicación:**
Flagger controla la entrega de cargas de trabajo y el tráfico; los feature flags controlan el comportamiento de la aplicación. No forman automáticamente una única transacción. Para coordinar los cambios de flags y las reversiones hacen falta webhooks reales o automatización con Git, autorización y manejo de fallos. Los porcentajes de tráfico de Canary y los porcentajes de cohortes de usuarios describen poblaciones distintas.

</details>
