# Cuestionario de pipelines de CI

> **Documento relacionado**: [Pipelines de CI](../../ops/03-ci-pipelines.md)

## Preguntas de opción múltiple

### 1. ¿Cuál es el propósito principal de las políticas de ciclo de vida de ECR?

- A) Construir automáticamente imágenes de container
- B) Gestionar la retención de imágenes y reducir los costos de almacenamiento
- C) Escanear imágenes en busca de vulnerabilidades
- D) Replicar imágenes entre regiones

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Gestionar la retención de imágenes y reducir los costos de almacenamiento**

**Explicación:**
Las políticas de ciclo de vida de ECR expiran y eliminan automáticamente imágenes antiguas según reglas como antigüedad o cantidad. Esto evita el crecimiento ilimitado del almacenamiento y reduce costos, mientras conserva indefinidamente las imágenes importantes (como tags de producción).

</details>

### 2. Al ejecutar GitLab Runner en EKS, ¿qué tipo de executor se recomienda para el aislamiento?

- A) Shell executor
- B) Docker executor
- C) Kubernetes executor
- D) SSH executor

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Kubernetes executor**

**Explicación:**
El Kubernetes executor ejecuta cada trabajo de CI en un pod separado, lo que proporciona un fuerte aislamiento entre trabajos. Limpia automáticamente los recursos después de que los trabajos finalizan y puede aprovechar características de Kubernetes como node selectors y tolerations.

</details>

### 3. ¿Qué es GitHub Actions Runner Controller (ARC)?

- A) Un servicio de runners alojado por GitHub
- B) Un operador de Kubernetes para runners de GitHub autohospedados
- C) Una biblioteca cliente de la API de GitHub
- D) Un controlador de container registry

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Un operador de Kubernetes para runners de GitHub autohospedados**

**Explicación:**
ARC es un operador de Kubernetes que escala automáticamente runners de GitHub Actions autohospedados según la demanda del workflow. Crea pods de runners cuando los trabajos se ponen en cola y los limpia después de completarlos.

</details>

### 4. ¿Cuál es el beneficio de las compilaciones de container multiplataforma (linux/amd64, linux/arm64)?

- A) Tamaños de imagen más pequeños
- B) Tiempos de compilación más rápidos
- C) Compatibilidad con diferentes arquitecturas de CPU (x86 y Graviton)
- D) Mejor escaneo de seguridad

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Compatibilidad con diferentes arquitecturas de CPU (x86 y Graviton)**

**Explicación:**
Las compilaciones multiplataforma crean imágenes que funcionan tanto en procesadores x86 (amd64) como ARM (arm64/Graviton). Esto habilita la optimización de costos mediante el uso de instancias Graviton y admite entornos de despliegue diversos.

</details>

### 5. ¿Cómo mejora la caché de BuildKit el rendimiento de compilación de containers?

- A) Omitiendo todos los pasos de compilación
- B) Almacenando en caché artefactos de capas y reutilizando capas sin cambios
- C) Comprimiendo las imágenes para hacerlas más pequeñas
- D) Paralelizando todas las operaciones

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Almacenando en caché artefactos de capas y reutilizando capas sin cambios**

**Explicación:**
BuildKit almacena inteligentemente en caché los artefactos de compilación y las salidas de capas. Cuando los archivos fuente no han cambiado, reutiliza capas en caché en lugar de reconstruirlas. La caché puede almacenarse en registries, S3 o almacenamiento local para compartirla entre compilaciones.

</details>

### 6. ¿Para qué se usa principalmente Kaniko?

- A) Orquestación de containers
- B) Construir imágenes de container sin Docker daemon
- C) Seguridad del runtime de containers
- D) Escaneo de vulnerabilidades de imágenes

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Construir imágenes de container sin Docker daemon**

**Explicación:**
Kaniko construye imágenes de container a partir de Dockerfiles sin requerir un Docker daemon ni modo privilegiado. Esto lo hace ideal para entornos de CI/CD donde ejecutar Docker-in-Docker plantea preocupaciones de seguridad o no está disponible.

</details>

### 7. En GitLab CI, ¿cuál es el propósito de la palabra clave `services`?

- A) Definir destinos de despliegue
- B) Levantar containers auxiliares (como bases de datos) para pruebas
- C) Configurar GitLab Pages
- D) Configurar monitoreo

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Levantar containers auxiliares (como bases de datos) para pruebas**

**Explicación:**
La palabra clave `services` define containers que se ejecutan junto al container principal del trabajo. Se usan comúnmente para dependencias de prueba como bases de datos (PostgreSQL, MySQL) o cachés (Redis) con las que las pruebas necesitan interactuar.

</details>

### 8. ¿Cuál es el enfoque recomendado para almacenar la caché de compilación de containers en CI/CD?

- A) Solo disco local
- B) Caché basada en registry con las flags --cache-to y --cache-from
- C) Nunca usar caché en CI/CD
- D) Almacenar la caché en el repositorio git

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Caché basada en registry con las flags --cache-to y --cache-from**

**Explicación:**
El almacenamiento en caché basado en registry guarda las capas de caché de compilación en un container registry, lo que las hace accesibles entre distintos runners de CI. Las flags `--cache-to` y `--cache-from` de BuildKit habilitan este patrón para una aceleración de compilación consistente.

</details>

### 9. Al configurar GitHub ARC, ¿qué controla la configuración `minRunners`?

- A) Trabajos concurrentes máximos
- B) Cantidad mínima de runners inactivos mantenidos
- C) Asignación de memoria del runner
- D) Duración del timeout del trabajo

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Cantidad mínima de runners inactivos mantenidos**

**Explicación:**
`minRunners` garantiza que siempre haya disponible una línea base de runners preparados, lo que reduce la latencia de inicio de trabajos. Configurarlo por encima de cero evita demoras por arranque en frío para workflows sensibles al tiempo, pero aumenta los costos de recursos inactivos.

</details>

### 10. ¿Cuál es el beneficio de seguridad de usar roles de IAM para runners de CI/CD en lugar de credenciales de larga duración?

- A) Autenticación más rápida
- B) Rotación automática de credenciales y menor riesgo de exposición
- C) Configuración más simple
- D) Acceso entre cuentas

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Rotación automática de credenciales y menor riesgo de exposición**

**Explicación:**
Los roles de IAM proporcionan credenciales temporales que rotan automáticamente, lo que elimina el riesgo de que claves de acceso de larga duración se filtren o se vean comprometidas. Combinados con Pod Identity o IRSA, los runners obtienen permisos delimitados sin almacenar secretos.

</details>
