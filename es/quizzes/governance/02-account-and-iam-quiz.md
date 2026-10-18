# Cuestionario sobre la estructura de Account y los límites de IAM

> Este cuestionario evalúa su comprensión de [la estructura de Account y los límites de IAM](../../governance/02-account-and-iam.md).

---

1. ¿Cuál es el alcance del límite de 100 grupos de Identity Center?
   - A) Todos los grupos de la Organization
   - B) Todos los grupos de una Account
   - C) Los grupos asignados a un conjunto de permisos en una Account, o a una aplicación
   - D) Los usuarios con sesión iniciada al mismo tiempo

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Los grupos asignados a un conjunto de permisos en una Account, o a una aplicación**

**Explicación:**
Se aplica por combinación de conjunto de permisos y Account, no al total de toda la Account entre conjuntos de permisos. Tampoco exige ABAC en todos los casos.

</details>

---

2. ¿Qué se debe tener en cuenta al planificar la separación de una Account que usa Shared VPC?
   - A) Todos los recursos se eliminan de inmediato
   - B) Planificar la migración considerando el requisito de pertenecer a la misma Organization y los límites de creación/reemplazo tras dejar de compartir
   - C) Las subredes de RAM siguen compartiéndose con organizaciones externas
   - D) EKS mueve las VPC automáticamente

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Planificar la migración considerando el requisito de pertenecer a la misma Organization y los límites de creación/reemplazo tras dejar de compartir**

**Explicación:**
Los recursos existentes pueden seguir funcionando después de dejar de compartir, mientras que la creación de recursos nuevos y el escalado o reemplazo de servicios administrados podrían verse afectados. Prepare una ruta operativa independiente antes de salir.

</details>

---

3. ¿Cómo puede un Shared Cluster acceder a los recursos de AWS de otra Account?
   - A) Emitir siempre claves de IAM user
   - B) Elegir según corresponda entre el encadenamiento de roles objetivo, las políticas de recursos compatibles o IRSA
   - C) Crear exactamente dos roles para cada carga de trabajo
   - D) Editar aws-auth concede permisos de AWS

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Elegir según corresponda entre el encadenamiento de roles objetivo, las políticas de recursos compatibles o IRSA**

**Explicación:**
El requisito de que el rol principal de Pod Identity esté en la misma Account no exige un rol objetivo para cada solicitud. Distinga la Account del clúster de la Account que solo posee una base de datos.

</details>

---

4. ¿Qué ocurre al combinar Access Policies con Kubernetes RBAC?
   - A) Solo se aplica la más reciente
   - B) Los permisos concedidos se combinan y ninguno restringe al otro
   - C) No se pueden combinar
   - D) RBAC siempre prevalece

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Los permisos concedidos se combinan y ninguno restringe al otro**

**Explicación:**
Revise las concesiones previstas y las superposiciones. La automatización ayuda, pero no es un requisito previo de la API.

</details>
