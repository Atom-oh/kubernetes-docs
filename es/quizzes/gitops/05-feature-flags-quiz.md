# Cuestionario sobre Feature Flags y OpenFeature

1. ¿Cuál es la ventaja clave del modelo de Provider de OpenFeature?
   - A) El vendor lock-in proporciona un rendimiento óptimo
   - B) Una API independiente del proveedor permite cambiar libremente los backends de Feature Flag
   - C) Requiere ejecutar tu propio servidor de Feature Flag
   - D) Solo admite API REST

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Una API independiente del proveedor permite cambiar libremente los backends de Feature Flag**

**Explicación:**
OpenFeature es un estándar de CNCF que proporciona una API de SDK independiente del proveedor. Mediante la interfaz Provider, puedes cambiar entre backends como flagd, LaunchDarkly, Flagsmith y otros modificando únicamente la configuración de Provider, sin necesidad de cambios en el código de la aplicación.

</details>

---

2. ¿Cuál es la diferencia entre los modos de despliegue Sidecar y Standalone para flagd en Kubernetes?
   - A) Sidecar tiene mejor rendimiento y Standalone es más fácil de administrar
   - B) Sidecar se inyecta en cada Pod y minimiza la latencia; Standalone se ejecuta como un servicio central
   - C) Sidecar solo admite TCP y Standalone solo admite HTTP
   - D) Sidecar usa CRDs y Standalone solo usa ConfigMaps

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Sidecar se inyecta en cada Pod y minimiza la latencia; Standalone se ejecuta como un servicio central**

**Explicación:**
En el modo Sidecar, el OpenFeature Operator inyecta un contenedor flagd en cada Pod, lo que permite comunicación local con una latencia mínima. En el modo Standalone, flagd se ejecuta como un Deployment independiente administrado de forma centralizada, lo que resulta más eficiente en recursos, pero requiere llamadas de red.

</details>

---

3. ¿Cuál es la función de la información incluida en el Evaluation Context de un Feature Flag?
   - A) Transmitir información de compilación para determinar los Flags en tiempo de compilación
   - B) Evaluar reglas de targeting mediante contexto como ID de usuario, región y entorno
   - C) Transmitir información de conexión a la base de datos
   - D) Transmitir información de nodos de Kubernetes

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Evaluar reglas de targeting mediante contexto como ID de usuario, región y entorno**

**Explicación:**
El Evaluation Context son metadatos que se transmiten dinámicamente durante la evaluación de un Flag. Incluye información como ID de usuario, región, entorno (dev/staging/prod) y grupos de usuarios. Las reglas de targeting utilizan esta información para habilitar funcionalidades para usuarios o grupos específicos.

</details>

---

4. ¿Cuál es la función de los Feature Flags en el patrón Dark Launch?
   - A) Ocultar completamente un servicio y bloquear el acceso
   - B) Desplegar código de una nueva funcionalidad, pero deshabilitarlo mediante un Flag para que los usuarios no lo vean
   - C) Cambiar los servidores al modo oscuro
   - D) Ejecutar despliegues únicamente por la noche

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Desplegar código de una nueva funcionalidad, pero deshabilitarlo mediante un Flag para que los usuarios no lo vean**

**Explicación:**
Dark Launch despliega código de una nueva funcionalidad en producción, pero lo mantiene invisible para los usuarios mediante Feature Flags. Después, el Flag se habilita gradualmente para un subconjunto de usuarios con fines de prueba y, si no surgen problemas, se habilita para todos los usuarios. Este es un patrón clave para separar el despliegue del lanzamiento.

</details>

---

5. ¿Cuál es la ventaja de Feature Flag as Code (GitOps)?
   - A) Los Flags solo se pueden administrar mediante GUI
   - B) Los cambios de Flags administrados mediante Git PRs permiten revisión, auditoría y rollback
   - C) La evaluación de Flags se vuelve más rápida
   - D) Se ahorran recursos del servidor

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Los cambios de Flags administrados mediante Git PRs permiten revisión, auditoría y rollback**

**Explicación:**
Feature Flag as Code administra FeatureFlag CRs en un repositorio Git, aplicando procesos de revisión y aprobación basados en PR. El historial de cambios se registra en Git para auditoría, y los problemas se pueden revertir rápidamente mediante Git revert. ArgoCD o Flux sincronizan automáticamente los cambios.

</details>

---

6. ¿Cuál es la práctica recomendada para prevenir deuda técnica derivada de Feature Flags?
   - A) Mantener todos los Flags de forma permanente
   - B) Establecer fechas de expiración en los Flags y limpiar el código de Flag después de completar el lanzamiento
   - C) Crear Flags libremente sin limitar la cantidad
   - D) No incluir fechas en los nombres de los Flags

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Establecer fechas de expiración en los Flags y limpiar el código de Flag después de completar el lanzamiento**

**Explicación:**
Los Feature Flags suelen utilizarse como herramientas temporales de lanzamiento. Después de completar un lanzamiento, el Flag y el código condicional relacionado deben limpiarse para evitar la acumulación de deuda técnica. Etiqueta los Flags con fechas de expiración y propietarios, y establece un proceso para detectar y eliminar periódicamente los Flags sin uso.

</details>

---

7. ¿Cuál es la funcionalidad principal que proporciona el OpenFeature Operator en Kubernetes?
   - A) Inyectar automáticamente sidecars flagd en Pods y administrar FeatureFlag CRDs
   - B) Auditar la seguridad del clúster de Kubernetes
   - C) Compilar automáticamente imágenes de contenedores
   - D) Configurar automáticamente HPA

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A) Inyectar automáticamente sidecars flagd en Pods y administrar FeatureFlag CRDs**

**Explicación:**
El OpenFeature Operator es un Operator para administrar Feature Flags de forma nativa en Kubernetes. Administra Flags de forma declarativa mediante FeatureFlag CRDs, define fuentes de Flags mediante FeatureFlagSource CRDs e inyecta automáticamente contenedores sidecar flagd en Pods con las anotaciones adecuadas.

</details>

---

8. ¿Cómo funciona el auto-rollout basado en métricas en la combinación de Flagger + Feature Flag?
   - A) Feature Flag controla directamente el tráfico
   - B) Flagger gestiona el cambio de tráfico Canary, mientras que Feature Flag controla la exposición gradual de funcionalidades en el nivel de la aplicación
   - C) Feature Flag reemplaza completamente a Flagger
   - D) Ambas herramientas usan métricas idénticas

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Flagger gestiona el cambio de tráfico Canary, mientras que Feature Flag controla la exposición gradual de funcionalidades en el nivel de la aplicación**

**Explicación:**
Flagger y Feature Flags operan en niveles diferentes. Flagger divide el tráfico en el nivel de infraestructura y analiza métricas para controlar el despliegue. Los Feature Flags controlan la activación o desactivación de funcionalidades individuales en el nivel de la aplicación. Utilizarlos juntos separa completamente el despliegue (Flagger) del lanzamiento (Feature Flags).

</details>
