# Cuestionario de Pod Security Standards

Este cuestionario evalúa tu comprensión de Pod Security Standards (PSS), Pod Security Admission (PSA) y los perfiles de seguridad.

## Preguntas del cuestionario

### 1. ¿Cuál NO es uno de los tres niveles de seguridad en Pod Security Standards (PSS)?

A. Privileged
B. Baseline
C. Hardened
D. Restricted

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C. Hardened**

**Explicación:**
Pod Security Standards define tres niveles de seguridad:
- **Privileged**: Sin restricciones, permite privilegios máximos
- **Baseline**: Evita la escalada de privilegios conocida, restricciones mínimas
- **Restricted**: Seguridad reforzada, aplica las mejores prácticas de endurecimiento de Pod

Hardened no es un nivel de seguridad oficial de PSS.

</details>

### 2. ¿Qué modo de Pod Security Admission (PSA) bloquea la creación de Pod cuando ocurren infracciones de política?

A. audit
B. warn
C. enforce
D. deny

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C. enforce**

**Explicación:**
PSA proporciona tres modos:
- **enforce**: Rechaza la creación de Pod ante una infracción de política
- **audit**: Registra las infracciones en los registros de auditoría, pero las permite
- **warn**: Muestra un mensaje de advertencia al usuario, pero lo permite

deny no es un modo válido de PSA.

</details>

### 3. ¿Qué formato de etiqueta se usa para aplicar PSS a un namespace?

A. security.kubernetes.io/enforce: restricted
B. pod-security.kubernetes.io/enforce: restricted
C. pss.kubernetes.io/level: restricted
D. admission.kubernetes.io/policy: restricted

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. pod-security.kubernetes.io/enforce: restricted**

**Explicación:**
PSA se configura mediante etiquetas de namespace:
```yaml
metadata:
  labels:
    pod-security.kubernetes.io/enforce: restricted
    pod-security.kubernetes.io/enforce-version: latest
    pod-security.kubernetes.io/audit: restricted
    pod-security.kubernetes.io/warn: restricted
```

Formato de etiqueta: `pod-security.kubernetes.io/<MODE>: <LEVEL>`

</details>

### 4. ¿Qué NO está permitido en el nivel de seguridad Baseline?

A. hostNetwork: true
B. runAsNonRoot: false
C. allowPrivilegeEscalation: true
D. readOnlyRootFilesystem: false

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A. hostNetwork: true**

**Explicación:**
El nivel Baseline evita la escalada de privilegios conocida. Lo siguiente está prohibido:
- hostNetwork, hostPID, hostIPC
- containers privilegiados
- Capabilities peligrosas (no se pueden agregar excepto NET_RAW)
- volúmenes hostPath (excepto ciertas rutas)

runAsNonRoot, allowPrivilegeEscalation y readOnlyRootFilesystem no están restringidos en Baseline; se aplican en el nivel Restricted.

</details>

### 5. ¿Cuál NO es un requisito del nivel de seguridad Restricted?

A. runAsNonRoot: true
B. allowPrivilegeEscalation: false
C. readOnlyRootFilesystem: true
D. capabilities.drop: ["ALL"]

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C. readOnlyRootFilesystem: true**

**Explicación:**
El nivel Restricted requiere:
- runAsNonRoot: true (obligatorio)
- allowPrivilegeEscalation: false (obligatorio)
- capabilities.drop: ["ALL"] (obligatorio)
- seccompProfile.type: RuntimeDefault o Localhost (obligatorio)

readOnlyRootFilesystem es una mejor práctica de seguridad, pero no es un requisito obligatorio del nivel Restricted.

</details>

### 6. ¿En qué versión de Kubernetes se eliminó PodSecurityPolicy (PSP)?

A. 1.21
B. 1.23
C. 1.25
D. 1.27

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C. 1.25**

**Explicación:**
Cronología de PSP:
- Kubernetes 1.21: se anunció la obsolescencia de PSP
- Kubernetes 1.22: se introdujo PSA alpha
- Kubernetes 1.23: PSA beta
- Kubernetes 1.25: PSP se eliminó por completo, PSA GA

</details>

### 7. ¿Qué etiqueta aplica una versión específica de PSS en PSA?

A. pod-security.kubernetes.io/enforce-version: v1.28
B. pod-security.kubernetes.io/version: v1.28
C. pod-security.kubernetes.io/enforce-version: 1.28
D. pod-security.kubernetes.io/policy-version: 1.28

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A. pod-security.kubernetes.io/enforce-version: v1.28**

**Explicación:**
Formato de etiqueta de versión:
```yaml
pod-security.kubernetes.io/<MODE>-version: <VERSION>
```

Los valores de versión usan el formato `v1.XX` o `latest`. Especificar una versión usa la definición de PSS de esa versión de Kubernetes.

</details>

### 8. ¿Cómo se habilita PSA en EKS?

A. Es necesario instalar el add-on de EKS
B. Habilitado de forma predeterminada
C. Habilitar con el comando eksctl
D. Configurar en la consola de AWS

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Habilitado de forma predeterminada**

**Explicación:**
Pod Security Admission está habilitado de forma predeterminada en Kubernetes 1.25+. En EKS 1.25 y versiones posteriores, PSA se puede usar sin configuración adicional. Solo necesitas agregar las etiquetas adecuadas a los namespaces.

</details>

### 9. ¿Cuál NO es un método para configurar exenciones de PSA?

A. Exención de RuntimeClass
B. Exención de usuario
C. Exención de namespace
D. Exención de etiqueta de Pod

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: D. Exención de etiqueta de Pod**

**Explicación:**
PSA admite los siguientes tipos de exención:
- **usernames**: Exenciones para usuarios específicos
- **runtimeClassNames**: Exenciones para RuntimeClasses específicos
- **namespaces**: Exenciones para namespaces específicos

PSA no admite exenciones basadas en etiquetas de Pod. Las exenciones se configuran mediante AdmissionConfiguration.

</details>

### 10. ¿Qué tipo de seccompProfile está permitido en el nivel Restricted?

A. Unconfined
B. RuntimeDefault
C. Custom
D. Disabled

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. RuntimeDefault**

**Explicación:**
Tipos de seccompProfile permitidos en el nivel Restricted:
- **RuntimeDefault**: Perfil predeterminado del runtime del container
- **Localhost**: Perfil personalizado definido en el node

Unconfined no está permitido en el nivel Restricted. Deshabilita el filtrado seccomp y plantea riesgos de seguridad.

</details>

### 11. ¿Cuál es el primer paso recomendado al migrar de PSP a PSA?

A. Eliminar PSP inmediatamente
B. Aplicar el modo enforce a todos los namespaces
C. Comenzar con el modo audit/warn para identificar infracciones
D. Crear un cluster nuevo

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C. Comenzar con el modo audit/warn para identificar infracciones**

**Explicación:**
Pasos recomendados para la migración a PSA:
1. **Comenzar con el modo audit/warn**: Identificar infracciones
2. **Corregir workloads**: Resolver infracciones
3. **Cambiar al modo enforce**: Aplicar gradualmente
4. **Eliminar PSP**: Después de completar la migración

Aplicar inmediatamente el modo enforce puede interrumpir workloads existentes.

</details>

### 12. ¿Qué está restringido incluso en el nivel Privileged?

A. uso de hostNetwork
B. containers privilegiados
C. Nada (todo está permitido)
D. volúmenes hostPath

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C. Nada (todo está permitido)**

**Explicación:**
El nivel Privileged no tiene restricciones:
- Se permiten todas las configuraciones de contexto de seguridad
- Se permiten hostNetwork, hostPID, hostIPC
- Se permiten containers privilegiados
- Se permiten todas las capabilities
- Se permiten todos los tipos de volúmenes

Este nivel se usa para workloads de sistema e infraestructura (por ejemplo, CNI, drivers de almacenamiento).

</details>
