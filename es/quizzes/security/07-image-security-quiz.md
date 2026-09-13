<span id="quiz-questions"></span>

# Cuestionario de seguridad de imágenes de contenedores
> **Última actualización**: September 13, 2026

<span id="_1-what-is-the-correct-command-to-scan-a-container-image-with-trivy"></span>

### 1. ¿Qué comando analiza una referencia de imagen determinada con Trivy?

- A. trivy scan "$IMAGE_REF"
- B. trivy image "$IMAGE_REF"
- C. trivy container "$IMAGE_REF"
- D. trivy check "$IMAGE_REF"

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. trivy image "$IMAGE_REF"**

trivy image es el comando de análisis de imágenes. Establezca IMAGE_REF en una referencia real por digest. Una sintaxis válida por sí sola no demuestra acceso al registro, una base de datos actualizada ni cobertura en la detección de paquetes.

</details>

<span id="_2-which-tool-is-used-for-image-signing-and-verification"></span>

### 2. ¿Qué herramienta verifica la relación entre el digest de una imagen y un firmante aprobado?

- A. La base de datos de CVE de Trivy
- B. Cosign/Sigstore
- C. El analizador de paquetes de Clair
- D. Docker imagePullPolicy

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Cosign/Sigstore**

Cosign verifica una clave o una identidad y un emisor OIDC, el digest y las pruebas de transparencia exigidas. Las firmas no garantizan la ausencia de vulnerabilidades conocidas.

</details>

<span id="_3-what-does-the-shift-left-security-approach-mean"></span>

### 3. ¿Qué significa el enfoque de seguridad shift-left?

- A. Posponer las comprobaciones hasta producción
- B. Comprobar antes, durante el desarrollo, las PR y las compilaciones
- C. Restringir el acceso al código fuente al equipo de seguridad
- D. Eliminar los nuevos análisis en producción

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Comprobar antes, durante el desarrollo, las PR y las compilaciones**

Las comprobaciones tempranas acortan los ciclos de retroalimentación. Las nuevas CVE y el comportamiento en ejecución siguen exigiendo nuevos análisis del registro y detección en tiempo de ejecución después de la publicación.

</details>

<span id="_4-what-is-the-main-characteristic-of-distroless-images"></span>

### 4. ¿Qué caracteriza a una imagen estándar de ejecución distroless?

- A. Incluye todas las utilidades de Linux
- B. Incluye un conjunto mínimo de componentes para ejecutar la aplicación
- C. Siempre incluye un shell y un depurador
- D. Es obligatorio incluir un gestor de paquetes

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Incluye un conjunto mínimo de componentes para ejecutar la aplicación**

Las imágenes estándar de ejecución omiten los shells y los gestores de paquetes; las variantes de depuración son diferentes. Los binarios y las bibliotecas de la aplicación aún pueden contener vulnerabilidades.

</details>

<span id="_5-what-are-the-two-types-of-amazon-ecr-image-scanning"></span>

### 5. ¿En qué se diferencian actualmente los análisis Basic y Enhanced de ECR?

- A. Basic utiliza el análisis nativo de AWS para paquetes del sistema operativo; Enhanced utiliza Inspector para paquetes del sistema operativo y de lenguajes
- B. Basic siempre utiliza Clair; Enhanced solo analiza paquetes del sistema operativo
- C. Ambos rechazan automáticamente las cargas de imágenes
- D. Enhanced analiza todas las imágenes para siempre

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A. Basic utiliza el análisis nativo de AWS para paquetes del sistema operativo; Enhanced utiliza Inspector para paquetes del sistema operativo y de lenguajes**

Basic admite análisis manuales y al cargar imágenes; Enhanced admite análisis al cargar imágenes y continuos. Distinga findings de enhancedFindings, y los eventos de ECR de los de Inspector.

</details>

<span id="_6-what-is-sbom-software-bill-of-materials"></span>

### 6. ¿Qué proporciona una SBOM?

- A. Una certificación de que no existen vulnerabilidades
- B. Un inventario de los componentes de software detectados por una herramienta
- C. Una prueba automática de un firmante aprobado
- D. Autorización para desplegar

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Un inventario de los componentes de software detectados por una herramienta**

Las SBOM registran componentes y relaciones, pero su cobertura puede ser incompleta. Evalúe por separado las atestaciones firmadas que las vinculan a un digest y la política de verificación.

</details>

<span id="_7-what-policy-type-verifies-image-signatures-in-kyverno"></span>

### 7. ¿Qué regla comprueba las firmas de imágenes en la ClusterPolicy heredada de Kyverno?

- A. Solo validate
- B. Solo mutate
- C. verifyImages
- D. Solo generate

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C. verifyImages**

Distinga la regla heredada verifyImages de la nueva ImageValidatingPolicy. El ejemplo de Kyverno 1.19.1 utiliza políticas CEL junto con restricciones de registro y digest que abarcan contenedores ordinarios, init y efímeros.

</details>

<span id="_8-why-should-you-use-digests-instead-of-image-tags"></span>

### 8. ¿Por qué fijar el digest de una imagen en lugar de una etiqueta?

- A. Siempre es más corto
- B. Identifica un contenido específico de la imagen
- C. Verifica automáticamente las firmas
- D. Elimina las CVE

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Identifica un contenido específico de la imagen**

Las etiquetas pueden cambiar de destino; los digests identifican el contenido. Esto permite seleccionar artefactos de forma reproducible, pero no sustituye la confianza en el firmante, las comprobaciones de vulnerabilidades ni la validación de disponibilidad.

</details>

<span id="_9-what-does-trivy-not-scan"></span>

### 9. ¿Qué ámbito es independiente de las comprobaciones estáticas de Trivy?

- A. La identificación de paquetes del sistema operativo
- B. El análisis de dependencias de lenguajes
- C. La detección del comportamiento de llamadas al sistema y procesos en ejecución
- D. La detección de secretos en el código fuente

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C. La detección del comportamiento de llamadas al sistema y procesos en ejecución**

El análisis de paquetes, configuraciones incorrectas y secretos es distinto de la detección del comportamiento en ejecución. Diseñe por separado el uso de herramientas de ejecución como Falco.

</details>

<span id="_10-which-is-not-a-container-image-registry-security-best-practice"></span>

### 10. ¿Qué práctica de acceso al registro es inapropiada?

- A. Identidades aprobadas para descargar imágenes privadas
- B. Verificación del digest y de la firma de imágenes públicas
- C. Permitir cargas y eliminaciones arbitrarias de imágenes de forma anónima
- D. Separar los permisos del registro, de admisión y del control de análisis

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C. Permitir cargas y eliminaciones arbitrarias de imágenes de forma anónima**

Las lecturas anónimas de imágenes publicadas intencionadamente no son vulnerabilidades por sí mismas. Controle por separado la confidencialidad, los permisos de escritura y eliminación, la procedencia y los límites de frecuencia.

</details>

<span id="_11-what-is-the-recommended-action-when-image-scanning-fails-in-ci-cd-pipeline"></span>

### 11. ¿Qué debe ocurrir cuando no se supera el control de análisis acordado en CI?

- A. Ignorarlo siempre
- B. Detenerse antes de publicar o firmar e investigar la causa
- C. Compilar otra imagen y cargarla sin analizarla
- D. Forzar el código de salida 0

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Detenerse antes de publicar o firmar e investigar la causa**

Distinga los incumplimientos de políticas de los errores del analizador, de la base de datos o de permisos, y conserve los resultados. No despliegue un artefacto diferente recompilado después del análisis. Las excepciones necesitan una justificación, un responsable y una fecha de caducidad.

</details>

<span id="_12-what-is-not-an-advantage-of-alpine-base-images"></span>

### 12. ¿Qué suposición sobre Alpine es incorrecta?

- A. Utiliza musl libc
- B. Utiliza el gestor de paquetes apk
- C. Siempre es totalmente compatible con las aplicaciones que dependen de glibc
- D. Es necesario comprobar el periodo de soporte de la versión seleccionada

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C. Siempre es totalmente compatible con las aplicaciones que dependen de glibc**

Alpine utiliza musl, por lo que los binarios que dependen de glibc pueden presentar problemas de compatibilidad. El tamaño de la imagen por sí solo no garantiza ni una cantidad determinada de vulnerabilidades ni una velocidad de compilación.

</details>
