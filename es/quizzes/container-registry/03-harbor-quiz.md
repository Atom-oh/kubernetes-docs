# Cuestionario sobre Harbor
> **Última actualización**: 11 de septiembre de 2026

1. ¿Cuál es el estado de Harbor dentro de Cloud Native Computing Foundation (CNCF)?
   - A) Proyecto Sandbox
   - B) Proyecto Incubating
   - C) Proyecto Graduated
   - D) Proyecto archivado

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Proyecto Graduated**

**Explicación:**
Harbor es un proyecto Graduated de CNCF, el nivel de madurez más alto de CNCF. Este estado indica que Harbor ha demostrado una adopción sólida, un proceso de gobernanza abierto y un firme compromiso con la sostenibilidad y la seguridad de la comunidad. Harbor se graduó en 2020.

</details>

2. ¿Cuál es el escáner de vulnerabilidades predeterminado de Harbor?
   - A) Clair
   - B) Trivy
   - C) Anchore
   - D) Snyk

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Trivy**

**Explicación:**
A partir de Harbor 2.2, Trivy reemplazó a Clair como escáner de vulnerabilidades predeterminado. Trivy es un escáner de código abierto de Aqua Security que detecta vulnerabilidades en imágenes de contenedor, incluidos paquetes del sistema operativo y dependencias de aplicaciones. Harbor sigue admitiendo escáneres conectables si se prefieren otras alternativas.

</details>

3. ¿Cuál es el método recomendado para instalar Harbor en un entorno de Kubernetes?
   - A) Docker Compose
   - B) Manifiestos YAML manuales
   - C) Chart de Helm
   - D) Patrón de operador

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Chart de Helm**

**Explicación:**
El chart oficial de Helm de Harbor es el método de instalación recomendado para entornos de Kubernetes. Gestiona todas las dependencias complejas (base de datos, Redis y almacenamiento) y ofrece amplias opciones de configuración. Docker Compose es adecuado para implementaciones que no usan Kubernetes o para pruebas rápidas, pero no se recomienda para implementaciones de Kubernetes en producción.

</details>

4. En el modelo RBAC de Harbor, ¿qué permisos tiene un Project Maintainer frente a un Developer?
   - A) Maintainer puede publicar imágenes; Developer no puede
   - B) Maintainer puede analizar/eliminar imágenes; Developer puede publicarlas/descargarlas, pero no administrar miembros del proyecto
   - C) Maintainer y Developer tienen permisos idénticos
   - D) Developer tiene más permisos que Maintainer

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Maintainer puede analizar/eliminar imágenes; Developer puede publicarlas/descargarlas, pero no administrar miembros del proyecto**

**Explicación:**
El RBAC a nivel de proyecto de Harbor define varios roles: Project Admin, Maintainer, Developer y Guest. Maintainer puede analizar y eliminar imágenes, y administrar etiquetas, pero no puede editar la configuración del proyecto ni administrar miembros. Developer puede publicar y descargar imágenes, pero no tiene esos privilegios administrativos. Project Admin tiene control completo, incluida la administración de miembros.

</details>

5. ¿Para qué se usan las cuentas robot de Harbor?
   - A) Tareas administrativas automatizadas
   - B) Cuentas de servicio no humanas con credenciales limitadas y acotadas para sistemas CI/CD
   - C) Administración de los componentes internos de Harbor
   - D) Replicación de imágenes entre instancias de Harbor

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Cuentas de servicio no humanas con credenciales limitadas y acotadas para sistemas CI/CD**

**Explicación:**
Las cuentas robot proporcionan autenticación entre sistemas para flujos de trabajo automatizados, como las canalizaciones CI/CD. Se pueden configurar para que caduquen, y tienen permisos de alcance de proyecto, como publicar/descargar repositorios, sin necesitar credenciales de usuarios humanos. Así se siguen las prácticas de seguridad recomendadas: se evitan credenciales compartidas y se permite rotarlas.

</details>

6. ¿Cuál es la diferencia entre los modos de replicación push y pull de Harbor?
   - A) Push es más rápido y pull más confiable
   - B) Push envía imágenes a registros remotos; pull las obtiene de registros remotos
   - C) Push requiere activadores manuales; pull es automático
   - D) No hay diferencia; son alias

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Push envía imágenes a registros remotos; pull las obtiene de registros remotos**

**Explicación:**
La replicación push envía proactivamente imágenes de Harbor a registros remotos (útil para distribuirlas en ubicaciones periféricas). La replicación pull obtiene imágenes de registros remotos y las introduce en Harbor (útil para reflejar registros externos o para la recuperación ante desastres). La replicación manual y la programada admiten flujos pull. La replicación basada en eventos sigue eventos de artefactos en el Harbor local; no se suscribe a cambios arbitrarios de registros externos.

</details>

7. ¿Con qué herramienta se integra Harbor para firmar y verificar imágenes?
   - A) GPG
   - B) Cosign y Notation
   - C) OpenSSL
   - D) HashiCorp Vault

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Cosign y Notation**

**Explicación:**
Harbor almacena las firmas creadas por Cosign y Notation. Notary v1 se eliminó en Harbor 2.9. Las políticas del registro que comprueban la presencia de firmas no reemplazan la verificación con claves o identidades de firma confiables durante la admisión.

</details>

8. ¿Para qué sirve la función de caché proxy de Harbor?
   - A) Almacenar en caché consultas DNS
   - B) Actuar como caché pull-through para registros remotos, como Docker Hub
   - C) Almacenar en caché dependencias de charts de Helm
   - D) Acelerar las operaciones internas de Harbor

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Actuar como caché pull-through para registros remotos, como Docker Hub**

**Explicación:**
La caché proxy de Harbor crea un proxy en caché para registros externos. Cuando los usuarios descargan imágenes a través de Harbor, estas se almacenan en la caché local. Las descargas posteriores de la misma imagen se sirven desde esa caché, lo que reduce el uso de ancho de banda externo, mejora el rendimiento de descarga y reduce las solicitudes upstream. Aun así, se aplican las reglas de fallos de caché, comprobaciones de vigencia y límites de cuenta upstream.

</details>

9. Al implementar Harbor en un entorno aislado de la red, ¿qué componente requiere una atención especial para las actualizaciones de la base de datos de vulnerabilidades?
   - A) El servicio principal de Harbor
   - B) La base de datos (PostgreSQL)
   - C) El escáner de vulnerabilidades (Trivy)
   - D) La caché de Redis

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) El escáner de vulnerabilidades (Trivy)**

**Explicación:**
En entornos aislados de la red, Trivy no puede descargar actualizaciones de la base de datos de vulnerabilidades desde Internet. Hay que descargar manualmente la base de datos de Trivy en una máquina conectada, transferirla al entorno aislado y configurar Trivy para que use la base de datos sin conexión. Si no se hace, el análisis de vulnerabilidades usará datos obsoletos o fallará por completo.

</details>

10. ¿Qué activa el proceso de recolección de basura de Harbor?
    - A) Se ejecuta automáticamente cada hora
    - B) Se debe activar manualmente o programar mediante la interfaz o la API de Harbor
    - C) Se ejecuta después de cada eliminación de imagen
    - D) Se ejecuta cuando el almacenamiento llega al 80 % de capacidad

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Se debe activar manualmente o programar mediante la interfaz o la API de Harbor**

**Explicación:**
La recolección de basura (GC) de Harbor no es automática. Se debe activar manualmente desde la interfaz de administración o la API de Harbor, o configurarse como trabajo programado. GC elimina las capas de imagen (blobs) a las que ya no hace referencia ningún manifiesto. Recupera almacenamiento, pero se debería programar en períodos de baja actividad porque puede afectar el rendimiento del registro.

</details>
