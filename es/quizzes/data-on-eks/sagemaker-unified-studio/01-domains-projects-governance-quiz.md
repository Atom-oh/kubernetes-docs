# Cuestionario sobre la gobernanza de dominios y proyectos de Unified Studio

## Preguntas de opción múltiple

1. ¿Qué afirmación describe correctamente un perfil de proyecto?

   - A) Solo selecciona controladores de GPU
   - B) Combina blueprints y configura herramientas para su creación o para usarlas bajo demanda
   - C) Todas sus capacidades garantizan que todas las herramientas estén listas de inmediato
   - D) Reemplaza todos los permisos de IAM

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B**

Verifique el ID del perfil previsto, el tipo de dominio y los blueprints, las cuentas y las regiones requeridos.

</details>

2. ¿Los permisos de IAM DeleteProject y la pertenencia ordinaria como colaborador garantizan la eliminación?

   - A) Siempre
   - B) No; verifique la autoridad del propietario o administrador para la ruta de eliminación y el resto de las políticas de IAM y del servicio
   - C) Sí, si coincide el espacio de nombres de EKS
   - D) Sí, si el nombre del proyecto es único

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B**

La propiedad del proyecto, la autorización de la API y los permisos reales sobre datos y recursos son límites distintos.

</details>

3. ¿Cómo se debe interpretar projectStatus=ACTIVE?

   - A) Todos los entornos y las herramientas de GPU están listos
   - B) Es el estado del proyecto; compruebe aparte los detalles obligatorios de environmentDeploymentDetails y el acceso a las herramientas
   - C) Todas las capacidades bajo demanda ya están aprovisionadas
   - D) El entrenamiento se completó correctamente

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B**

Distinga las herramientas bajo demanda que no se aprovisionaron intencionalmente de los fallos reales.

</details>

4. ¿Qué debe contener un miembro de membershipAssignments de CreateProject?

   - A) Siempre tanto userIdentifier como groupIdentifier
   - B) Exactamente un userIdentifier o groupIdentifier que coincida con el perfil previsto
   - C) Una clave de acceso secreta de IAM
   - D) Cualquier ARN de rol de IAM en lugar de un ID de perfil de grupo

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B**

Es una unión discriminada. Las asignaciones enviadas en la misma solicitud no garantizan una reversión atómica de todo el aprovisionamiento de entornos; verifique los resultados.

</details>

5. ¿Cómo se debe verificar la eliminación de un proyecto pendiente?

   - A) Interpretar AccessDenied como ausencia
   - B) Comprobar el alcance autorizado de get/list, el dominio, los filtros y la paginación, y el inventario de recursos de la ejecución
   - C) Un registro de principios de septiembre demuestra el estado actual
   - D) Eliminar todos los buckets y roles compartidos con el mismo prefijo si falla una etiqueta

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B**

Los registros históricos no reemplazan la verificación actual. La limpieza debe respetar la propiedad de la ejecución y la política de retención.

</details>

---

[Volver a los materiales de aprendizaje](../../../data-on-eks/sagemaker-unified-studio/01-domains-projects-governance.md)
