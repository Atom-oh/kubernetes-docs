# Cuestionario de seguridad de imágenes de contenedor

Este cuestionario evalúa tu comprensión del escaneo de imágenes, la firma de imágenes, la seguridad de la cadena de suministro y la selección de imágenes base.

## Preguntas del cuestionario

### 1. ¿Cuál es el comando correcto para escanear una imagen de contenedor con Trivy?

A. trivy scan nginx:latest
B. trivy image nginx:latest
C. trivy container nginx:latest
D. trivy check nginx:latest

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. trivy image nginx:latest**

**Explicación:**
Comando de escaneo de imágenes de Trivy:
```bash
trivy image nginx:latest
trivy image --severity HIGH,CRITICAL nginx:latest
trivy image --format json nginx:latest
```

`trivy image` escanea imágenes de contenedor en busca de vulnerabilidades.

</details>

### 2. ¿Qué herramienta se usa para la firma y verificación de imágenes?

A. Trivy
B. Cosign/Sigstore
C. Clair
D. Anchore

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Cosign/Sigstore**

**Explicación:**
Cosign forma parte del proyecto Sigstore, una herramienta para firmar y verificar imágenes de contenedor:
```bash
# Sign image
cosign sign --key cosign.key myregistry/myimage:tag

# Verify signature
cosign verify --key cosign.pub myregistry/myimage:tag
```

Trivy, Clair y Anchore son escáneres de vulnerabilidades.

</details>

### 3. ¿Qué significa el enfoque de seguridad "Shift-Left"?

A. Aplazar la seguridad a la fase de operaciones
B. Mover la seguridad a las etapas tempranas del desarrollo
C. Solo el equipo de seguridad es responsable
D. Eliminar la automatización

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Mover la seguridad a las etapas tempranas del desarrollo**

**Explicación:**
La seguridad Shift-Left mueve las comprobaciones de seguridad a la etapa más temprana posible del ciclo de desarrollo:
- Escaneo en la etapa de IDE
- Controles de compilación en el pipeline de CI/CD
- Comprobaciones de seguridad durante la revisión de PR

Cuanto antes se encuentren los problemas, menor será el costo de corregirlos.

</details>

### 4. ¿Cuál es la característica principal de las imágenes Distroless?

A. Incluyen todas las utilidades de Linux
B. Incluyen solo los componentes mínimos necesarios para ejecutar aplicaciones
C. Incluyen herramientas de depuración
D. Incluyen gestores de paquetes

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Incluyen solo los componentes mínimos necesarios para ejecutar aplicaciones**

**Explicación:**
Las imágenes Distroless tienen:
- Sin shell (bash, sh, etc.)
- Sin gestor de paquetes
- Sin utilidades innecesarias
- Superficie de ataque mínima
- Solo el runtime de la aplicación

Beneficios en seguridad y tamaño de imagen.

</details>

### 5. ¿Cuáles son los dos tipos de escaneo de imágenes de Amazon ECR?

A. Basic scanning, Enhanced scanning
B. Automatic scanning, Manual scanning
C. Quick scanning, Deep scanning
D. Free scanning, Paid scanning

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A. Basic scanning, Enhanced scanning**

**Explicación:**
Tipos de escaneo de Amazon ECR:
- **Basic scanning**: basado en Clair, escaneo de vulnerabilidades de paquetes del OS
- **Enhanced scanning**: basado en Amazon Inspector, paquetes del OS + paquetes de lenguajes de programación, escaneo continuo

Enhanced scanning tiene un costo adicional, pero es más completo.

</details>

### 6. ¿Qué es SBOM (Software Bill of Materials)?

A. Lista de licencias de software
B. Lista de componentes de software
C. Lista de vulnerabilidades de seguridad
D. Lista de comandos de compilación

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Lista de componentes de software**

**Explicación:**
SBOM es una lista de todos los componentes (bibliotecas, dependencias, versiones, etc.) incluidos en el software. Es esencial para la seguridad de la cadena de suministro y la gestión de vulnerabilidades:
```bash
# Generate SBOM with Trivy
trivy image --format spdx-json -o sbom.json nginx:latest
```

</details>

### 7. ¿Qué tipo de política verifica las firmas de imágenes en Kyverno?

A. validate
B. mutate
C. verifyImages
D. generate

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C. verifyImages**

**Explicación:**
La regla `verifyImages` de Kyverno verifica las firmas de imágenes de contenedor:
```yaml
spec:
  rules:
  - name: verify-signature
    verifyImages:
    - imageReferences:
      - "myregistry/*"
      attestors:
      - entries:
        - keys:
            publicKeys: |-
              -----BEGIN PUBLIC KEY-----
              ...
              -----END PUBLIC KEY-----
```

</details>

### 8. ¿Por qué deberías usar digests en lugar de tags de imagen?

A. Nombres más cortos
B. Inmutabilidad garantizada
C. Pulling más rápido
D. Ahorrar espacio de almacenamiento

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Inmutabilidad garantizada**

**Explicación:**
Los tags (por ejemplo, `nginx:latest`) pueden cambiarse para apuntar a imágenes diferentes. Los digests (por ejemplo, `nginx@sha256:abc123...`) son hashes del contenido específico de una imagen y son inmutables:
```yaml
image: nginx@sha256:abc123def456...
```

Esto garantiza reproducibilidad y seguridad.

</details>

### 9. ¿Qué NO escanea Trivy?

A. Vulnerabilidades de paquetes del OS
B. Dependencias específicas del lenguaje
C. Comportamiento en runtime
D. Detección de secretos

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C. Comportamiento en runtime**

**Explicación:**
Trivy es una herramienta de análisis estático que escanea:
- Vulnerabilidades de paquetes del OS
- Dependencias específicas del lenguaje (npm, pip, go, etc.)
- Configuraciones incorrectas de IaC
- Secretos hardcodeados
- Licencias

El análisis del comportamiento en runtime es el dominio de herramientas de seguridad en runtime como Falco.

</details>

### 10. ¿Cuál NO es una buena práctica de seguridad para un registro de imágenes de contenedor?

A. Usar un registro privado
B. Habilitar el escaneo de imágenes
C. Permitir pulling anónimo
D. Bloquear el push de imágenes vulnerables

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C. Permitir pulling anónimo**

**Explicación:**
Buenas prácticas de seguridad para registros:
- Usar un registro privado
- Autenticación basada en IAM
- Habilitar el escaneo de imágenes
- Bloquear el push/pull de imágenes vulnerables
- Verificación de firmas de imágenes
- Usar tags o digests inmutables

El pulling anónimo es un riesgo de seguridad y debe deshabilitarse en entornos de producción.

</details>

### 11. ¿Cuál es la acción recomendada cuando falla el escaneo de imágenes en un pipeline de CI/CD?

A. Registrar solo una advertencia
B. Detener la compilación
C. Auto-corregir
D. Ignorar y continuar

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Detener la compilación**

**Explicación:**
En pipelines de CI/CD, las compilaciones deben detenerse cuando se encuentran vulnerabilidades Critical/High:
```bash
trivy image --exit-code 1 --severity HIGH,CRITICAL myimage:tag
```

`--exit-code 1` devuelve un código de salida distinto de cero cuando se encuentran vulnerabilidades, lo que hace fallar el pipeline.

</details>

### 12. ¿Qué NO es una ventaja de las imágenes base Alpine?

A. Tamaño pequeño
B. Menos vulnerabilidades
C. Compatibilidad con glibc
D. Compilaciones rápidas

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C. Compatibilidad con glibc**

**Explicación:**
Características de Alpine Linux:
- Tamaño pequeño (~5MB)
- Paquetes mínimos
- Usa musl libc (no glibc)

Alpine usa musl libc en lugar de glibc, por lo que algunas aplicaciones que dependen de glibc pueden tener problemas de compatibilidad.

</details>
