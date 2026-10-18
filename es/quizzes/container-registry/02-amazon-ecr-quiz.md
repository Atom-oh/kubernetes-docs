# Cuestionario sobre Amazon ECR
> **Última actualización**: 11 de septiembre de 2026

1. ¿Cuál es la diferencia principal entre Amazon ECR Private y Amazon ECR Public?
   - A) ECR Private es gratuito y ECR Public es de pago
   - B) ECR Private requiere autenticación para todas las operaciones y ECR Public permite descargas anónimas
   - C) ECR Private solo admite imágenes de Docker y ECR Public admite todos los formatos
   - D) ECR Private es regional y ECR Public solo está disponible en us-east-1

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) ECR Private requiere autenticación para todas las operaciones y ECR Public permite descargas anónimas**

**Explicación:**
Las operaciones de publicación y descarga privadas requieren autenticación. Las imágenes públicas se pueden descargar anónimamente, pero la publicación y la administración requieren autenticación. Los endpoints de API públicos aparecen en us-east-1 y us-west-2, y las imágenes se distribuyen mediante URL globales.

</details>

2. ¿Qué comando de la CLI emite directamente la contraseña de ECR para usar con `docker login --password-stdin`?
   - A) `aws ecr get-authorization-token`
   - B) `aws ecr get-login-password`
   - C) `aws ecr login`
   - D) `aws ecr authenticate`

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) `aws ecr get-login-password`**

**Explicación:**
`get-login-password` imprime la contraseña que se puede pasar mediante stdin. `get-authorization-token` también es una operación válida de API/CLI, pero devuelve un token de autorización codificado que se debe decodificar.

</details>

3. En las políticas de ciclo de vida de ECR, ¿qué determina qué regla se aplica cuando varias coinciden con la misma imagen?
   - A) Gana la regla con el número `rulePriority` más bajo
   - B) Gana la regla con el número `rulePriority` más alto
   - C) Las reglas se aplican en orden alfabético
   - D) Todas las reglas coincidentes se aplican simultáneamente

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A) Gana la regla con el número `rulePriority` más bajo**

**Explicación:**
Primero se evalúan todas las reglas y luego se aplican sus resultados según la prioridad. Los números más bajos tienen mayor prioridad; una imagen que coincida con los requisitos de etiquetado de una regla de mayor prioridad no puede expirar debido a una regla de menor prioridad. Las reglas no se evalúan con una secuencia ordenada que se interrumpe al encontrar la primera coincidencia.

</details>

4. ¿Qué sintaxis de patrones usa `tagPatternList` de las políticas de ciclo de vida de ECR?
   - A) Expresiones regulares (regex)
   - B) El patrón documentado con comodín `*`
   - C) Patrones SQL LIKE
   - D) Solo coincidencia de cadena exacta

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) El patrón documentado con comodín `*`**

**Explicación:**
Usa el comodín documentado `*`, con un máximo de cuatro asteriscos por cadena. No supongas que admite regex, clases de caracteres ni todo el comportamiento de los patrones glob de Unix. `v*` selecciona un prefijo; CI debe validar el formato de la versión de lanzamiento.

</details>

5. ¿Cuál es una limitación importante de la lógica de las políticas de ciclo de vida de ECR?
   - A) No puede haber más de 5 reglas
   - B) No se puede expresar lógica OR/unión entre patrones de etiquetas en una sola regla
   - C) No se pueden eliminar imágenes sin etiqueta
   - D) No se puede usar `countType` con `imageCountMoreThan`

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) No se puede expresar lógica OR/unión entre patrones de etiquetas en una sola regla**

**Explicación:**
Una regla de ciclo de vida de ECR con varios patrones en `tagPatternList` aplica lógica AND (una imagen debe coincidir con todos los patrones). Para conseguir lógica OR (coincidencia con cualquier patrón), hay que crear reglas separadas para cada patrón. Esta limitación requiere diseñar cuidadosamente las reglas si se quiere aplicar la misma política de retención a imágenes que coinciden con distintos patrones de etiquetas.

</details>

6. En la estrategia A (repositorios separados por entorno) para ECR, ¿cuál es una ventaja principal?
   - A) Las políticas de ciclo de vida son más sencillas porque cada repositorio tiene requisitos de retención uniformes
   - B) El almacenamiento cuesta menos
   - C) Las imágenes se descargan más rápido
   - D) La replicación entre regiones es automática

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A) Las políticas de ciclo de vida son más sencillas porque cada repositorio tiene requisitos de retención uniformes**

**Explicación:**
La estrategia A usa repositorios separados por entorno (por ejemplo, `myapp-dev`, `myapp-prod`). Así se simplifican las políticas de ciclo de vida porque cada repositorio contiene imágenes con requisitos de retención uniformes. A cambio, hay que administrar varios repositorios y posiblemente duplicar imágenes entre ellos.

</details>

7. ¿Qué recurso de Terraform se usa para definir políticas de ciclo de vida de ECR?
   - A) `aws_ecr_repository`
   - B) `aws_ecr_lifecycle_policy`
   - C) `aws_ecr_repository_policy`
   - D) `aws_ecr_retention_policy`

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) `aws_ecr_lifecycle_policy`**

**Explicación:**
El recurso de Terraform `aws_ecr_lifecycle_policy` adjunta una política de ciclo de vida a un repositorio de ECR. Requiere el nombre `repository` y un documento JSON `policy` que defina las reglas de ciclo de vida. Ten en cuenta que `aws_ecr_repository_policy` es distinto y se usa para políticas de recursos de IAM que controlan el acceso al repositorio.

</details>

8. ¿Qué identidad suele proporcionar los permisos iniciales para descargar imágenes de ECR en nodos de EKS respaldados por EC2?
   - A) Una clave de acceso estática guardada en un Secret
   - B) Kubelet usa directamente el rol de IAM del nodo
   - C) Los pods asumen un rol de IAM mediante federación OIDC y usan credenciales temporales
   - D) Los tokens de ECR están aprovisionados previamente en ConfigMaps

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Kubelet usa directamente el rol de IAM del nodo**

**Explicación:**
Kubelet descarga la imagen antes de que se inicie la aplicación, usando las credenciales de descarga del nodo. Fargate usa el rol de ejecución del pod. IRSA/Pod Identity proporcionan credenciales SDK de la carga de trabajo después del inicio del pod; no reemplazan la identidad de bootstrap para descargar imágenes.

</details>

9. ¿Qué se evita al habilitar etiquetas inmutables en un repositorio de ECR?
   - A) Eliminar cualquier imagen del repositorio
   - B) Publicar imágenes nuevas con la misma etiqueta que una imagen existente
   - C) Descargar imágenes sin autenticación
   - D) Crear políticas de ciclo de vida

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Publicar imágenes nuevas con la misma etiqueta que una imagen existente**

**Explicación:**
Las etiquetas inmutables impiden sobrescribir las etiquetas de imágenes existentes. Una vez que se publica una imagen con una etiqueta concreta, esa etiqueta no se puede reutilizar para un digest de imagen distinto. Esto garantiza la estabilidad de etiquetas para las implementaciones y evita el reemplazo accidental o malicioso de imágenes. Aun así, se pueden eliminar imágenes y publicar etiquetas nuevas y únicas.

</details>

10. ¿Qué descripción de la replicación entre regiones de ECR es correcta?
    - A) Solo se replican los manifiestos de imagen
    - B) Las imágenes y etiquetas elegibles se replican de forma asíncrona; los ajustes del destino se administran por separado
    - C) Se replica todo, incluidas las políticas de ciclo de vida y los permisos
    - D) Todas las imágenes preexistentes se rellenan automáticamente

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Las imágenes y etiquetas elegibles se replican de forma asíncrona; los ajustes del destino se administran por separado**

**Explicación:**
Las imágenes que se publiquen o restauren después de configurar la replicación pueden incluirse. El contenido existente no se replica retroactivamente de forma automática. La configuración, los permisos y las políticas de ciclo de vida del repositorio de destino se definen de manera independiente, por ejemplo, mediante plantillas de creación. Verifica el digest requerido en el destino antes de depender de la replicación para la recuperación.

</details>
