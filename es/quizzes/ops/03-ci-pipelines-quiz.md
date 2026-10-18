# Cuestionario sobre pipelines de CI

> **Documento relacionado**: [Pipelines de CI](../../ops/03-ci-pipelines.md)

## Preguntas de opción múltiple

### 1. ¿Por qué se usan repositorios de ECR distintos para las imágenes de publicación y la caché de BuildKit?

- A) Las imágenes de caché no requieren autenticación de IAM
- B) Los tags inmutables de publicación y las referencias mutables de caché necesitan políticas distintas
- C) ECR solo admite un tag
- D) El almacenamiento en caché elimina la necesidad de escanear

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Los tags inmutables de publicación y las referencias mutables de caché necesitan políticas distintas**

**Explicación:** En el ejemplo, el repositorio de la aplicación es INMUTABLE y el de la caché de compilación, MUTABLE. Un tag con forma de SHA de commit por sí solo no impide que se sobrescriba; los despliegues consumen el digest verificado.

</details>

### 2. ¿Qué ofrece un Pod independiente para cada trabajo del executor de Kubernetes de GitLab?

- A) Aislamiento completo incluso para los trabajos privilegiados
- B) La eliminación de todos los riesgos de acceso a los nodos
- C) Ciclos de vida y recursos separados por trabajo, sin garantizar una frontera de seguridad completa
- D) Acceso de publicación de AWS heredado y seguro para solicitudes de extracción no confiables

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Ciclos de vida y recursos separados por trabajo, sin garantizar una frontera de seguridad completa**

**Explicación:** La configuración privilegiada de Docker-in-Docker de esta guía es para trabajos protegidos y confiables. La separación de Pods, los nodos dedicados a CI y los roles con privilegios mínimos son controles distintos; ninguno demuestra por sí solo que sea seguro ejecutar código arbitrario no confiable.

</details>

### 3. ¿En qué se diferencian `poll_interval` y `check_interval`?

- A) `poll_interval` comprueba el estado del Pod de Kubernetes; `check_interval` se refiere a la consulta de trabajos por parte del coordinador
- B) Son dos nombres para el mismo ajuste
- C) Ambos caducan las cachés de imágenes de Docker
- D) `poll_interval` reinicia los Pods

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A) `poll_interval` comprueba el estado del Pod de Kubernetes; `check_interval` se refiere a la consulta de trabajos por parte del coordinador**

**Explicación:** El executor de Kubernetes usa `poll_interval` mientras espera a que el Pod de un trabajo esté listo. El `check_interval` de Runner controla otra ruta de consulta; cambiar uno no sustituye el cambio del otro.

</details>

### 4. ¿Por qué se separan los roles de AWS del administrador de GitLab y de los Pods de compilación?

- A) Para otorgar al administrador todos los permisos de AWS
- B) Porque Pod Identity crea automáticamente las ServiceAccounts
- C) Porque los Pods de compilación deben almacenar claves de larga duración
- D) Para delimitar por separado el acceso a la caché S3 del administrador y el acceso de publicación en ECR de los Pods de compilación

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: D) Para delimitar por separado el acceso a la caché S3 del administrador y el acceso de publicación en ECR de los Pods de compilación**

**Explicación:** Sin `RoleARN`, la caché S3 del ejemplo usa la cadena de credenciales del administrador. Los Pods de compilación reciben un rol ECR distinto. Las ServiceAccounts se deben crear por separado; el token de AWS Pod Identity es distinto del token normal de la API de Kubernetes.

</details>

### 5. ¿Cómo recibe y asigna trabajos el ejemplo actual de ARC?

- A) Instala únicamente `RunnerDeployment` y `HorizontalRunnerAutoscaler`
- B) Usa los charts y listeners oficiales de conjuntos de escalado, y hace coincidir `runs-on` con el nombre real del conjunto
- C) El nombre de un grupo de runners de la organización siempre es una etiqueta del trabajo
- D) `minRunners=0` elimina todos los costos del clúster

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Usa los charts y listeners oficiales de conjuntos de escalado, y hace coincidir `runs-on` con el nombre real del conjunto**

**Explicación:** No mezcles el modelo heredado de CRD con los charts actuales de conjuntos de escalado. ARC 0.15.0 también admite `scaleSetLabels`. `minRunners` se refiere a los runners inactivos; no elimina los costos del controlador ni del listener, ni garantiza que no haya latencia de arranque.

</details>

### 6. ¿Qué trabajos de GitHub obtienen las credenciales de AWS OIDC del ejemplo?

- A) Todas las pruebas de solicitudes de extracción externas
- B) Un trabajo `pull_request_target` que ejecuta código arbitrario de una solicitud de extracción
- C) Los trabajos confiables de publicación tras una inserción, después de que pasen las pruebas
- D) Todos los runners autohospedados al arrancar

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Los trabajos confiables de publicación tras una inserción, después de que pasen las pruebas**

**Explicación:** Las pruebas de solicitudes de extracción se ejecutan en runners alojados por GitHub y no solicitan credenciales de publicación. La relación de confianza del rol restringe el repositorio exacto y la rama principal o los tags protegidos; los Pods de ARC no heredan un rol de publicación de AWS.

</details>

### 7. ¿Qué secuencia mantiene el contrato entre el escaneo y la publicación?

- A) Compilar → escanear correctamente la misma imagen → publicar → crear un índice con los digests aprobados
- B) Publicar → ignorar el fallo del escaneo → desplegar `latest`
- C) Escanear el código fuente → compilar otra imagen → publicarla siempre
- D) Considerar que la existencia de cualquier archivo JSON significa que el escaneo tuvo éxito

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A) Compilar → escanear correctamente la misma imagen → publicar → crear un índice con los digests aprobados**

**Explicación:** GitLab pasa archivos de imagen mediante dependencias 1:1 específicas de cada arquitectura. GitHub escanea su imagen compilada localmente antes de subirla. Los errores de Trivy o los fallos de la barrera de vulnerabilidades impiden publicar; el JSON nativo de Trivy no se etiqueta incorrectamente como el esquema de informes de GitLab.

</details>

### 8. ¿Qué afirmación compara correctamente los runners nativos con QEMU?

- A) Una opción de plataforma por sí sola permite ejecutar cualquier instrucción de otra arquitectura
- B) QEMU es el compilador cruzado de la aplicación
- C) Una imagen AMD64 se convierte en ARM64 al cambiarle el tag
- D) Los runners nativos compilan en la CPU de destino; QEMU emula las instrucciones de otra CPU

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: D) Los runners nativos compilan en la CPU de destino; QEMU emula las instrucciones de otra CPU**

**Explicación:** Haz coincidir los selectores de nodo del administrador y del trabajo, los tags del runner y la arquitectura auxiliar. El índice final debe apuntar a digests de plataformas verificados de forma independiente. La compilación cruzada requiere una cadena de herramientas y un Dockerfile configurados deliberadamente.

</details>

### 9. ¿Qué requiere el ejemplo de salida independiente de Next.js?

- A) `npm ci --omit=dev` es suficiente para todas las compilaciones
- B) Salida standalone, dependencias de compilación, recursos estáticos copiados y la ruta correcta del servidor
- C) `public` y `.next/static` siempre se copian automáticamente en la salida standalone
- D) Todos los monorepos comienzan en `root/server.js`

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Salida standalone, dependencias de compilación, recursos estáticos copiados y la ruta correcta del servidor**

**Explicación:** El ejemplo presupone una sola raíz de aplicación y un archivo de bloqueo de npm. Copia `public` y `.next/static` al diseño de ejecución y enlaza con `0.0.0.0`. Los monorepos necesitan sus propias comprobaciones de la raíz de seguimiento y de la ruta de salida anidada.

</details>

### 10. ¿Qué afirmación sobre Kaniko y BuildKit sin privilegios de root es correcta?

- A) No tener daemon garantiza que cada compilación se ejecute sin root y con aislamiento completo
- B) Renombrar la imagen privilegiada de Docker-in-Docker completa una configuración sin root
- C) Comprueba el estado de mantenimiento y la compatibilidad del nodo con espacios de nombres de usuario, montajes y políticas de seguridad
- D) `no-process-sandbox` refuerza el aislamiento de procesos

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Comprueba el estado de mantenimiento y la compatibilidad del nodo con espacios de nombres de usuario, montajes y políticas de seguridad**

**Explicación:** El repositorio de Google Kaniko está archivado. El fragmento opcional de BuildKit sin root requiere un runner validado por separado. `no-process-sandbox` debilita el aislamiento de procesos y la limpieza del contenedor daemon; además, la caché del registro no conserva automáticamente todos los montajes de caché.

</details>
