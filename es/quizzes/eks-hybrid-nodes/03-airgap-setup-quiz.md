# Cuestionario sobre la configuración de acceso restringido a Internet en EKS Hybrid Nodes

> **Documento relacionado**: [Configuración de acceso restringido a Internet](../../eks-hybrid-nodes/03-airgap-setup.md)
> **Última actualización**: 12 de septiembre de 2026

### 1. ¿Qué afirmación sobre la conectividad de EKS Hybrid Nodes es correcta?

A. Transferir físicamente la imagen elimina la necesidad de conectividad con AWS

B. Los nodos siguen necesitando conectividad con el plano de control de EKS y los servicios de credenciales

C. Un bucket privado de S3 aloja el plano de control de EKS

D. La conectividad VPN equivale al aislamiento físico

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Los nodos siguen necesitando conectividad con el plano de control de EKS y los servicios de credenciales**

**Explicación:** El acceso público restringido a Internet puede coexistir con la conectividad privada con AWS. Una red físicamente desconectada no puede proporcionar las rutas activas al plano de control y a los servicios de credenciales que requieren los nodos híbridos.

</details>

### 2. ¿Por qué no basta con un alias de PHZ de hybrid-assets.eks.amazonaws.com a S3?

A. S3 nunca admite DNS privado

B. ECR debe instalarse antes que DNS

C. DNS no proporciona el nombre de host TLS original, el enrutamiento del objeto ni la autorización

D. Todas las solicitudes HTTPS usan automáticamente un rol de IAM

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C. DNS no proporciona el nombre de host TLS original, el enrutamiento del objeto ni la autorización**

**Explicación:** Los endpoints de interfaz de S3 sí admiten DNS privado. Sin embargo, un alias no reescribe SNI de TLS, el encabezado HTTP Host, las rutas de objetos ni la autenticación. Use la preparación de imágenes aprobada o URL reales de manifiestos personalizados; no deshabilite la verificación de certificados.

</details>

### 3. ¿Qué hace el modo de instalación privada de nodeadm v1.0.20?

A. Instala todas las dependencias del SO a partir de un manifiesto local

B. Omite la instalación de paquetes del SO, pero instala los artefactos de credenciales y EKS

C. Hace que todas las llamadas a las API de AWS sean opcionales

D. Firma automáticamente todas las descargas de artefactos de S3

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Omite la instalación de paquetes del SO, pero instala los artefactos de credenciales y EKS**

**Explicación:** El código fuente publicado requiere `--manifest-override` junto con `--private-mode`. Prepare por separado el runtime y las dependencias del SO. El origen del instalador/firma de SSM se construye por separado; que el manifiesto use `file://` no implica que los artefactos admitan `file://`.

</details>

### 4. ¿Qué debe hacer un script de preparación de artefactos si falta una suma de comprobación o no coincide?

A. Mostrar una advertencia y publicar los archivos restantes

B. Aceptar la ejecución si al menos un archivo pasó la verificación

C. Generar una nueva suma esperada a partir del archivo descargado

D. Detenerse y conservar el candidato fallido para investigarlo

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: D. Detenerse y conservar el candidato fallido para investigarlo**

**Explicación:** Todos los archivos obligatorios deben coincidir con un registro de sumas de comprobación confiable y revisado. Generar un nuevo valor esperado anula el propósito de esa verificación. Que los hashes coincidan no constituye una autenticación independiente del publicador.

</details>

### 5. ¿Cuál es el alcance correcto del servicio de actualización de IAM Roles Anywhere?

A. Existe en todas las instalaciones, incluso con SSM

B. Se usa cuando `enableCredentialsFile` está habilitado; el uso normal de credential-process es una ruta separada

C. El servicio es ficticio y siempre debe eliminarse

D. Elimina la necesidad de renovar los certificados

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Se usa cuando `enableCredentialsFile` está habilitado; el uso normal de credential-process es una ruta separada**

**Explicación:** `aws_signing_helper_update.service` es real en el modo de archivo de credenciales. Configure el servicio y los entornos del proceso que lo invoca según corresponda, incluida la detección de proxy o el comportamiento `--with-proxy` de nodeadm. Siguen siendo necesarios el ciclo de vida de los certificados y la conectividad con AWS.

</details>

### 6. ¿Qué imágenes se deben incluir en el inventario de entrega de Hybrid Nodes?

A. Una lista fija de imágenes de VPC CNI para todos los nodos

B. Solo kubelet, porque es la imagen de CNI

C. Las imágenes reales y compatibles de CNI, DNS, plano de datos, entorno aislado y cargas de trabajo, incluidos los init containers y las plataformas

D. Cualquier etiqueta que se construya añadiendo `-eksbuild.1` a un parche de Kubernetes

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C. Las imágenes reales y compatibles de CNI, DNS, plano de datos, entorno aislado y cargas de trabajo, incluidos los init containers y las plataformas**

**Explicación:** VPC CNI no es el CNI de Hybrid Nodes. Use los manifiestos desplegados y los digest aprobados. Las descargas desde ECR privado también necesitan la ruta de capas de S3 y las credenciales de extracción de imágenes de la carga de trabajo; enumerar repositorios no basta.

</details>

### 7. ¿Qué comprobación válida de la configuración de nodeadm se puede realizar antes del arranque?

A. `nodeadm init --dry-run`

B. `nodeadm config check --config-source file:///etc/eks/nodeconfig.yaml`

C. Ejecutar `curl -k` y después informar que el nodo está listo

D. Omitir un archivo de configuración faltante y devolver éxito

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. `nodeadm config check --config-source file:///etc/eks/nodeconfig.yaml`**

**Explicación:** Use un archivo de configuración protegido y con los datos necesarios. `config check` valida la configuración; no demuestra que la red privada funcione ni registra el nodo. El comando `init` inspeccionado no tiene la opción `--dry-run`.

</details>

### 8. ¿Qué cambio de proxy conserva mejor un DaemonSet de kube-proxy existente?

A. Reemplazar `/containers/0/env` por una nueva matriz JSON Patch

B. Eliminar `NODE_NAME` porque los proxies no lo necesitan

C. Usar una fusión estratégica revisada por nombre de contenedor/variable de entorno y conservar los argumentos y `NODE_NAME` existentes

D. Excluir siempre `.eks.amazonaws.com` del proxy

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C. Usar una fusión estratégica revisada por nombre de contenedor/variable de entorno y conservar los argumentos y `NODE_NAME` existentes**

**Explicación:** Una operación JSON Patch `add` sobre un elemento `env` existente puede reemplazar toda la matriz. Limite el parche a kube-proxy y conserve los demás valores. La exclusión amplia de `.eks.amazonaws.com` también coincide con el host público de descarga hybrid-assets.

</details>

### 9. ¿Qué se necesita antes de usar un archivo de imagen OCI transferido?

A. Solo que la importación de tar termine correctamente

B. Verificar el hash aprobado, el contenido del digest/plataforma, las referencias de destino y el comportamiento final de extracción del runtime

C. Deshabilitar TLS en el registro de origen para evitar errores de certificado

D. Suponer que solo se necesita la arquitectura de la máquina de compilación

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Verificar el hash aprobado, el contenido del digest/plataforma, las referencias de destino y el comportamiento final de extracción del runtime**

**Explicación:** `skopeo --all` conserva la lista de plataformas y `--preserve-digests` falla si no se puede conservar un digest. Los nombres de importación, el espacio de nombres `k8s.io` de containerd, `imagePullPolicy` y la recolección de basura siguen afectando si el Pod real puede iniciarse.

</details>

### 10. ¿Qué práctica de actualización es adecuada para el repositorio privado de artefactos?

A. Sobrescribir automáticamente cada semana las claves `latest` de producción

B. Tratar un error AccessDenied de `head-object` como si el objeto no existiera

C. Aprobar un nuevo candidato inmutable después de validar procedencia, compatibilidad y nodos representativos

D. Prometer un ahorro de ancho de banda del 50–80 % en todos los entornos

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C. Aprobar un nuevo candidato inmutable después de validar procedencia, compatibilidad y nodos representativos**

**Explicación:** Use un bucket propio, especifique el propietario esperado y separe los permisos de publicador y lector; deténgase ante errores desconocidos. Las escrituras condicionales de objetos no hacen atómica una carga completa. Los porcentajes de ancho de banda anteriores son ejemplos históricos no verificados, no mediciones garantizadas.

</details>
