# Cuestionario sobre el arranque de nodos de EKS Hybrid Nodes

> **Documento relacionado**: [Arranque de nodos](../../eks-hybrid-nodes/04-node-bootstrap.md)
> **Última actualización**: 12 de septiembre de 2026

### 1. ¿Qué función cumple Hybrid nodeadm?

A. Crear el plano de control de EKS

B. Instalar e inicializar componentes de nodos Hybrid mediante la implementación aws/eks-hybrid

C. Programar Pods de aplicaciones

D. Sustituir al controlador CNI

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Instalar e inicializar componentes de nodos Hybrid mediante la implementación aws/eks-hybrid**

**Explicación:** Usa el instalador Hybrid, no nodeadm de EC2 amazon-eks-ami. Instala las dependencias antes de `init`, elige el origen correcto para el sistema operativo y el entorno de ejecución, y verifica el binario aprobado. Las instalaciones y actualizaciones nuevas de SSM requieren actualmente nodeadm 1.0.19 o posterior.

</details>

### 2. ¿Qué datos del clúster se usan en la configuración normal de NodeConfig para Hybrid?

A. Nombre y región del clúster, junto con un proveedor de credenciales admitido

B. Solo el ID de VPC y el ID de subred

C. Tres campos escritos manualmente obligatorios: nombre, endpoint y CA

D. Una clave de acceso de usuario de IAM y una contraseña

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A. Nombre y región del clúster, junto con un proveedor de credenciales admitido**

**Explicación:** La configuración Hybrid documentada usa `spec.cluster.name` y `spec.cluster.region`, además de `spec.hybrid.ssm` o `spec.hybrid.iamRolesAnywhere`. El rol Hybrid preparado proporciona los permisos de descubrimiento del clúster. No es correcto exigir que se copie manualmente un certificado CA PEM sin procesar para cada inicialización Hybrid habitual.

</details>

### 3. ¿Qué par de proveedores de credenciales admite nodeadm?

A. Claves de usuario de IAM y LDAP

B. Tokens estáticos de Kubernetes y contraseñas locales

C. Activaciones híbridas de SSM e IAM Roles Anywhere

D. Perfiles de instancia EC2 y contraseñas de kubeconfig

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C. Activaciones híbridas de SSM e IAM Roles Anywhere**

**Explicación:** Elige exactamente una opción: `ssm` o `iam-ra`. La configuración de SSM incluye `activationCode` y `activationId` dentro de `spec.hybrid.ssm`; IAM Roles Anywhere usa `spec.hybrid.iamRolesAnywhere`. Ambas necesitan el rol Hybrid preparado y acceso al clúster.

</details>

### 4. ¿Cuál no es un campo de configuración de kubelet?

A. `maxPods`

B. `clusterDNS`

C. `clusterDomain`

D. `podScheduler`

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: D. `podScheduler`**

**Explicación:** `podScheduler` no es un campo de configuración de kubelet; el scheduler se ejecuta en el plano de control. `clusterCIDR`, opción usada anteriormente, tampoco es un campo válido de configuración de kubelet, por lo que la pregunta anterior era ambigua. Los ajustes de kubelet de NodeConfig no sustituyen la planificación de IPAM de CNI.

</details>

### 5. ¿Qué demuestra un registro de automatización que indica que terminó el comando de inicialización?

A. Que el nodo estará siempre en estado Ready

B. Que el comando `init` terminó y las comprobaciones locales pasaron en ese momento; aún hay que verificar la disponibilidad en el clúster

C. Que se probaron todas las descargas de imágenes y renovaciones de credenciales

D. Que se puede clonar el host sin riesgos, incluida su identidad

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Que el comando `init` terminó y las comprobaciones locales pasaron en ese momento; aún hay que verificar la disponibilidad en el clúster**

**Explicación:** Asocia los registros de automatización con el host, la configuración y el binario; conserva el estado iniciado si hay una interrupción y rechaza volver a ejecutar automáticamente un estado desconocido. `network-online.target` y `RemainAfterExit` no demuestran que haya conectividad con AWS ni que el nodo esté listo.

</details>

### 6. ¿Cómo se debe entender la CA del servidor de la API de Kubernetes?

A. Emite automáticamente el certificado de cliente de kubelet durante cada handshake TLS

B. Es la credencial para iniciar sesión en el registro de contenedores

C. Permite validar la confianza en el certificado del servidor; la aprobación o emisión del certificado de cliente es independiente

D. Sustituye el rol IAM Hybrid

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C. Permite validar la confianza en el certificado del servidor; la aprobación o emisión del certificado de cliente es independiente**

**Explicación:** Valida el nombre de host del servidor y la cadena de la CA. No uses `curl -k` para comprobar la confianza. La CA del clúster, la CA del registro privado y la identidad del host de IAM Roles Anywhere sirven para usos de confianza distintos.

</details>

### 7. ¿Qué respuesta es adecuada ante una unión fallida o una inicialización parcial?

A. Ejecutar `nodeadm status` y luego `uninstall --force` inmediatamente

B. Revisar en privado los registros acotados de kubelet y la depuración de nodeadm, verificar identidad y red, y después reconciliar el estado registrado

C. Eliminar todas las CRD de Cilium del clúster compartido

D. Eliminar el objeto Node y suponer que se dio de baja SSM

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Revisar en privado los registros acotados de kubelet y la depuración de nodeadm, verificar identidad y red, y después reconciliar el estado registrado**

**Explicación:** La CLI inspeccionada tiene `nodeadm debug`, no `nodeadm status`. La depuración contacta servicios de AWS y del clúster; conserva su salida en privado. Eliminar un objeto Node no detiene kubelet ni da de baja SSM. `uninstall` es una operación controlada de eliminación, no una solución genérica para errores de autenticación.

</details>

### 8. ¿Qué afirmación sobre la identidad de Pods de Bottlerocket es correcta?

A. Usa NodeConfig y nodeadm exactamente igual que Ubuntu

B. `settings.hybrid.ssm` es el contrato de arranque documentado completo

C. Bottlerocket 1.39.0 o posterior usa compatibilidad del proveedor con el archivo de credenciales de arranque y el DaemonSet del agente hybrid-bottlerocket

D. Codificar los datos de usuario en Base64 cifra la clave privada

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C. Bottlerocket 1.39.0 o posterior usa compatibilidad del proveedor con el archivo de credenciales de arranque y el DaemonSet del agente hybrid-bottlerocket**

**Explicación:** Bottlerocket usa ajustes y entradas de bootstrap container independientes. La versión mínima compatible del agente es v1.3.7-eksbuild.2, y la ruta de credenciales temporales es `/var/eks-hybrid/.aws/credentials`. Elige un complemento actual compatible y protege los datos de usuario; codificar no es cifrar.

</details>

### 9. ¿Qué acción del ciclo de vida de Cilium tiene el alcance correcto?

A. Cambiar en el sitio un CIDR de cluster-pool existente

B. Ejecutar una comprobación previa acotada a Hybrid y verificar la cobertura del DaemonSet y que el Deployment de validación esté listo antes de actualizar

C. Reutilizar siempre todos los valores Helm antiguos sin revisarlos

D. Desinstalar todas las CRD que contengan cilium para reparar un nodo

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Ejecutar una comprobación previa acotada a Hybrid y verificar la cobertura del DaemonSet y que el Deployment de validación esté listo antes de actualizar**

**Explicación:** La comprobación previa tiene un selector de nodos independiente. No cambies los elementos ni el tamaño de máscara de los pools existentes; para ampliar, puedes agregar una entrada nueva revisada al pool junto con los cambios correspondientes de EKS y enrutamiento. Quitar CNI o CRD es una operación disruptiva controlada por su propietario.

</details>

### 10. ¿Qué significa `nodeadm uninstall --force` en la versión inspeccionada?

A. Garantiza que se eliminen todas las rutas montadas, incluida `/var/lib/kubelet`

B. Omite una confirmación genérica y sustituye el vaciado de nodos

C. Elimina rutas predeterminadas adicionales, pero mantiene la protección de `/var/lib/kubelet` de la versión 1.0.9 o posterior

D. Verifica automáticamente que exista un nodo de reemplazo

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C. Elimina rutas predeterminadas adicionales, pero mantiene la protección de `/var/lib/kubelet` de la versión 1.0.9 o posterior**

**Explicación:** No elimines rutas montadas de kubelet a ciegas. Desaloja las cargas de trabajo, revisa los datos y la limpieza del proveedor y CNI, y conserva las pruebas de recuperación. Una reinstalación aprobada requiere `install` → comprobar la configuración → `init`; no basta con ejecutar `init` después de desinstalar.

</details>
