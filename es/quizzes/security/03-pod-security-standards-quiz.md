# Cuestionario sobre Pod Security Standards

> **Última actualización**: September 13, 2026
> **Documento relacionado**: [Pod Security Standards](../../security/03-pod-security-standards.md)

Responde para Pods Linux comunes; consulta la guía para conocer las excepciones específicas de versión para Windows y los espacios de nombres de usuario.

## Preguntas del cuestionario

### 1. ¿Cuál NO es uno de los tres niveles de seguridad de Pod Security Standards (PSS)?

- A) Privileged
- B) Baseline
- C) Hardened
- D) Restricted

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Hardened**

**Explicación:**
Pod Security Standards define tres niveles de seguridad:
- **Privileged**: Sin restricciones, permite los máximos privilegios
- **Baseline**: Evita la escalada de privilegios conocida, con restricciones mínimas
- **Restricted**: Seguridad reforzada, aplica las prácticas recomendadas de fortalecimiento de Pods

Hardened no es un nivel de seguridad oficial de PSS.

</details>

### 2. ¿Qué modo de Pod Security Admission (PSA) bloquea la creación de Pods cuando se producen infracciones de políticas?

- A) audit
- B) warn
- C) enforce
- D) deny

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) enforce**

**Explicación:**
PSA proporciona tres modos:
- **enforce**: Rechaza la creación de Pods ante una infracción de políticas
- **audit**: Registra las infracciones en los registros de auditoría, pero las permite
- **warn**: Muestra un mensaje de advertencia al usuario, pero las permite

deny no es un modo de PSA válido. audit/warn no rechazan por sí mismos; enforce u otras comprobaciones aún pueden rechazar la misma solicitud. La retención de auditorías requiere una configuración de registros adecuada.

</details>

### 3. ¿Qué formato de etiqueta se utiliza para aplicar PSS a un namespace?

- A) security.kubernetes.io/enforce: restricted
- B) pod-security.kubernetes.io/enforce: restricted
- C) pss.kubernetes.io/level: restricted
- D) admission.kubernetes.io/policy: restricted

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) pod-security.kubernetes.io/enforce: restricted**

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

Formato de la etiqueta: `pod-security.kubernetes.io/<MODE>: <LEVEL>`

</details>

### 4. ¿Cuál NO está permitido en el nivel de seguridad Baseline?

- A) hostNetwork: true
- B) runAsNonRoot: false
- C) allowPrivilegeEscalation: true
- D) readOnlyRootFilesystem: false

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A) hostNetwork: true**

**Explicación:**
El nivel Baseline evita la escalada de privilegios conocida. Se prohíbe lo siguiente:
- hostNetwork, hostPID, hostIPC
- contenedores privilegiados
- Adiciones explícitas de capacidades fuera de la lista permitida de Baseline, incluida NET_RAW
- Todos los volúmenes hostPath; PSA integrado no proporciona ninguna lista de rutas permitidas

Baseline no requiere runAsNonRoot ni allowPrivilegeEscalation: false. Restricted añade esos controles para el tipo de Pod asumido. readOnlyRootFilesystem es un fortalecimiento recomendado, no un requisito de ninguno de los perfiles. La comprobación de capacidades se refiere a adiciones explícitas; no elimina el conjunto predeterminado del runtime.

</details>

### 5. ¿Cuál NO es un requisito del nivel de seguridad Restricted?

- A) runAsNonRoot: true
- B) allowPrivilegeEscalation: false
- C) readOnlyRootFilesystem: true
- D) capabilities.drop: ["ALL"]

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) readOnlyRootFilesystem: true**

**Explicación:**
El nivel Restricted requiere:
- runAsNonRoot: true (obligatorio)
- allowPrivilegeEscalation: false (obligatorio)
- capabilities.drop: ["ALL"] (obligatorio)
- seccompProfile.type: RuntimeDefault o Localhost (obligatorio)

readOnlyRootFilesystem es una práctica recomendada de seguridad, pero no es un requisito obligatorio del nivel Restricted.

</details>

### 6. ¿En qué versión de Kubernetes se eliminó PodSecurityPolicy (PSP)?

- A) 1.21
- B) 1.23
- C) 1.25
- D) 1.27

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) 1.25**

**Explicación:**
Cronología de PSP:
- Kubernetes 1.21: Se anunció la obsolescencia de PSP
- Kubernetes 1.22: Se introdujo PSA alpha
- Kubernetes 1.23: PSA beta
- Kubernetes 1.25: PSP se eliminó por completo, PSA GA

</details>

### 7. ¿Qué etiqueta aplica una versión específica de PSS en PSA?

- A) pod-security.kubernetes.io/enforce-version: v1.28
- B) pod-security.kubernetes.io/version: v1.28
- C) pod-security.kubernetes.io/enforce-version: 1.28
- D) pod-security.kubernetes.io/policy-version: 1.28

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A) pod-security.kubernetes.io/enforce-version: v1.28**

**Explicación:**
Formato de la etiqueta de versión:
```yaml
pod-security.kubernetes.io/<MODE>-version: <VERSION>
```

Los valores utilizan `v1.XX` o `latest`. La fijación selecciona la definición de la política, no una actualización de Kubernetes. La opción v1.28 ilustra la sintaxis; omite los controles introducidos posteriormente. latest sigue la versión del servidor de la API y puede cambiar durante una actualización.

</details>

### 8. ¿Cómo se habilita PSA en EKS?

- A) Es necesario instalar un complemento de EKS
- B) Habilitado de forma predeterminada
- C) Habilitar con el comando eksctl
- D) Configurar en la consola de AWS

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Habilitado de forma predeterminada**

**Explicación:**
PSA alcanzó GA y está habilitado de forma predeterminada en Kubernetes upstream 1.25+. AWS documenta la habilitación predeterminada de EKS desde la versión 1.23, con valores predeterminados permisivos privileged/latest y sin exenciones estáticas. Revisa las etiquetas reales de los namespaces; añade una política adecuada en lugar de asumir que la habilitación por sí sola proporciona la aplicación de Baseline/Restricted.

</details>

### 9. ¿Cuál NO es un método para configurar exenciones de PSA?

- A) Exención de RuntimeClass
- B) Exención de usuario
- C) Exención de namespace
- D) Exención de etiqueta de Pod

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: D) Exención de etiqueta de Pod**

**Explicación:**
PSA admite los siguientes tipos de exención:
- **usernames**: Exenciones para usuarios específicos
- **runtimeClasses**: Exenciones para RuntimeClasses específicas
- **namespaces**: Exenciones para namespaces específicos

Las etiquetas de Pods no crean exenciones. Las entradas de exención estáticas son nombres exactos, no selectores de comodines ni de grupos. Las exenciones de usuario coinciden con la identidad de la solicitud, no con spec.serviceAccountName. EKS no permite editar esta configuración del control plane; elegir la aplicación de namespace privileged es diferente de una exención estática.

</details>

### 10. ¿Qué tipo de seccompProfile está permitido en el nivel Restricted?

- A) Unconfined
- B) RuntimeDefault
- C) Custom
- D) Disabled

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) RuntimeDefault**

**Explicación:**
Tipos de seccompProfile permitidos en el nivel Restricted:
- **RuntimeDefault**: Perfil predeterminado del runtime de contenedores
- **Localhost**: Perfil personalizado definido en el nodo

Unconfined no está permitido en el nivel Restricted. Desactiva el filtrado de seccomp y plantea riesgos de seguridad.

</details>

### 11. ¿Cuál es el primer paso recomendado al migrar de PSP a PSA?

- A) Eliminar PSP inmediatamente
- B) Aplicar el modo enforce a todos los namespaces
- C) Empezar con el modo audit/warn para identificar infracciones
- D) Crear un nuevo clúster

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Empezar con el modo audit/warn para identificar infracciones**

**Explicación:**
Pasos recomendados para la migración de PSA:
1. **Empezar con el modo audit/warn**: Identificar infracciones
2. **Corregir las cargas de trabajo**: Resolver infracciones
3. **Cambiar al modo enforce**: Aplicar gradualmente
4. **Eliminar PSP**: Después de completar la migración

Los Pods existentes en ejecución no se expulsan simplemente al volver a etiquetar. Se pueden denegar sus reemplazos o actualizaciones relevantes, por lo que una implementación posterior puede bloquearse. Esta secuencia de eliminación de PSP es histórica para los clústeres que aún servían PSP antes de la versión 1.25.

</details>

<span id="_12-what-is-restricted-even-in-the-privileged-level"></span>

### 12. ¿Cuál de estos elementos prohíbe el propio perfil PSS Privileged?

- A) Uso de hostNetwork
- B) contenedores privilegiados
- C) Ninguno de estos por PSS mismo
- D) volúmenes hostPath

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Ninguno de estos por PSS mismo**

**Explicación:**
Privileged no añade restricciones de PSS sobre estos campos válidos de Pod:
- Se permiten todos los ajustes de contexto de seguridad
- Se permiten hostNetwork, hostPID, hostIPC
- Se permiten contenedores privilegiados
- Se permiten todas las capacidades
- Se permiten todos los tipos de volumen

Esto no concede permisos de IAM/RBAC, omite la validación de esquemas ni otras políticas de admisión, ni fuerza privileged: true. Limita estos namespaces a componentes de acceso al host revisados.

</details>
