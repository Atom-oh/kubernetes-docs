# Cuestionario sobre la estructura de cuentas y los límites de IAM

> Este cuestionario evalúa su comprensión de [la estructura de cuentas y los límites de IAM](../../governance/02-account-and-iam.md).

---

1. ¿Cuál es el alcance del límite de 100 grupos de Identity Center?
   - A) Todos los grupos de la organización
   - B) Todos los grupos de una cuenta
   - C) Los grupos asignados a un conjunto de permisos en una cuenta, o a una aplicación
   - D) Los usuarios con sesión iniciada al mismo tiempo

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Los grupos asignados a un conjunto de permisos en una cuenta, o a una aplicación**

**Explicación:**
Se aplica a cada combinación de conjunto de permisos y cuenta, no a la suma de todos los conjuntos de permisos de la cuenta. Tampoco exige ABAC en todos los casos.

</details>

---

2. ¿Qué se debe tener en cuenta al planificar la separación de una cuenta que usa una VPC compartida (Shared VPC)?
   - A) Todos los recursos se eliminan de inmediato
   - B) Planificar la migración considerando el requisito de pertenecer a la misma organización y los límites de creación/reemplazo tras dejar de compartirla
   - C) Las subredes de RAM siguen compartiéndose con organizaciones externas
   - D) EKS mueve las VPC automáticamente

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Planificar la migración considerando el requisito de pertenecer a la misma organización y los límites de creación/reemplazo tras dejar de compartirla**

**Explicación:**
Los recursos existentes pueden seguir funcionando después de dejar de compartir la VPC, mientras que la creación de recursos nuevos y el escalado o reemplazo de servicios administrados podrían verse afectados. Prepare una ruta operativa independiente antes de completar la separación.

</details>

---

3. ¿Cómo puede un clúster compartido (Shared Cluster) acceder a los recursos de AWS de otra cuenta?
   - A) Emitir siempre claves de un usuario de IAM
   - B) Elegir según corresponda entre el encadenamiento con un rol de destino, las políticas de recursos compatibles o IRSA
   - C) Crear exactamente dos roles para cada carga de trabajo
   - D) Editar aws-auth concede permisos de AWS

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Elegir según corresponda entre el encadenamiento con un rol de destino, las políticas de recursos compatibles o IRSA**

**Explicación:**
El requisito de que el rol principal de Pod Identity esté en la misma cuenta no exige un rol de destino para cada solicitud. Distinga la cuenta del clúster de la cuenta que solo posee una base de datos.

</details>

---

4. ¿Qué ocurre al combinar las políticas de acceso (Access Policies) con Kubernetes RBAC?
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
