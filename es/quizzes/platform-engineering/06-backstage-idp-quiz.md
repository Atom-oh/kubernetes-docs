# Cuestionario de Backstage IDP

[Backstage](../../platform-engineering/06-backstage-idp.md)

Los ocho temas originales se han actualizado a la revisión de Backstage 1.54.7.

## 1. ¿Qué kind del catálogo representa un microservicio?

<details>
<summary>Mostrar respuesta</summary>

Component, con un spec.type como service. Un Resource del catálogo describe infraestructura; no es un controlador que aprovisione recursos de AWS.

</details>

## 2. ¿Qué crea realmente una Software Template?

<details>
<summary>Mostrar respuesta</summary>

Solo los archivos y las operaciones externas implementadas por las actions registradas y los skeletons suministrados. El pequeño ejemplo de la guía crea tres archivos de catálogo/TechDocs, no un runtime de aplicación ni una base de datos. Los golden paths no reemplazan la autorización ni las políticas obligatorias.

</details>

## 3. ¿Cómo se asocian las cargas de trabajo de Kubernetes con las entidades del catálogo?

<details>
<summary>Mostrar respuesta</summary>

Haga coincidir backstage.io/kubernetes-id o las anotaciones de selector de etiquetas admitidas con las etiquetas reales de la carga de trabajo. También se requieren la selección de namespace/cluster, las credenciales y RBAC. La coincidencia de metadatos no es una autorización por usuario.

</details>

## 4. ¿Cómo se deben preparar PostgreSQL y los secrets en EKS?

<details>
<summary>Mostrar respuesta</summary>

Al seleccionar un PostgreSQL externo como RDS, deshabilite la base de datos incluida y configure TLS, redes, esquemas, migraciones y copias de seguridad. Utilice montajes de archivos de secrets aprobados con rutas $file coincidentes. Una base de datos administrada por sí sola no completa la verificación de HA/recuperación.

</details>

## 5. ¿Cómo se compila y se sirve TechDocs?

<details>
<summary>Mostrar respuesta</summary>

Utilice MkDocs y techdocs-core. Con builders externos, CI publica en un almacenamiento como S3 y el backend de Backstage lo lee para la UI. Alinee las claves de entidad y las rutas raíz, y separe los permisos de publisher/reader; no es necesario el acceso público al bucket.

</details>

## 6. ¿Qué se debe establecer durante una adopción incremental?

<details>
<summary>Mostrar respuesta</summary>

Comience con un catálogo pequeño y preciso y con propiedad/fuentes confiables, y luego amplíe las templates y TechDocs. Establezca la autenticación, la autorización y los límites de confianza desde el principio.

</details>

## 7. ¿Qué conecta la publicación en GitHub con las actions de ArgoCD?

<details>
<summary>Mostrar respuesta</summary>

Registre los módulos de actions y configure las credenciales, los permisos y los esquemas reales de entrada/salida. El argocd:create-resources de Roadie 1.8.1 toma el namespace de despliegue y no tiene una entrada de revision. No registre un archivo de catálogo de la rama main inmediatamente después de abrir su PR sin fusionar.

</details>

## 8. ¿Cómo se puede restringir la eliminación del catálogo según la propiedad?

<details>
<summary>Mostrar respuesta</summary>

Registre un módulo PermissionPolicy real, devuelva una condición IS_ENTITY_OWNER para la eliminación del catálogo y deje que el backend del catálogo la evalúe. El ejemplo deniega las acciones sin concesiones explícitas. La propiedad del catálogo, las escrituras en GitHub y los permisos de despliegue de ArgoCD son distintos; proteja también las fuentes de Group/User.

</details>
