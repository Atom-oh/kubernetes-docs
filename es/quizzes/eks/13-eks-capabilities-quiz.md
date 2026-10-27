# Cuestionario sobre las capacidades de Amazon EKS

> **Última actualización**: 23 de octubre de 2026

Usa el [capítulo fuente](../../eks/13-eks-capabilities.md) para distinguir los resultados medidos de las afirmaciones basadas únicamente en la documentación.

1. ¿Dónde se ejecutan los controladores de Argo CD, kro y ACK de EKS Capabilities?

   - A) Como DaemonSet en cada nodo de trabajo
   - B) Como Deployments en el espacio de nombres `kube-system`
   - C) En infraestructura propiedad de AWS, sin Pods en los nodos de trabajo
   - D) En un perfil de Fargate creado automáticamente en tu VPC

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) En infraestructura propiedad de AWS, sin Pods en los nodos de trabajo**

Las tres capacidades crearon cero Pods en los nodos de trabajo. Los controladores llaman al servidor de API mediante el rol de la capacidad y una entrada de acceso de EKS, por lo que funcionan incluso con un punto de conexión de API exclusivamente privado. Por el mismo motivo, los registros no están disponibles mediante `kubectl logs`; usa Vended Logs.

</details>

---

2. ¿Qué se necesita para sincronizar una Application con el clúster local justo después de crear Argo CD administrado?

   - A) Nada; el clúster local se registra automáticamente
   - B) Un Secret de clúster que use el ARN de EKS, además de permisos de implementación en la entrada de acceso del rol de la capacidad
   - C) Ejecutar `argocd cluster add`
   - D) Siempre se requiere `system:masters`

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Un Secret de clúster que use el ARN de EKS, además de permisos de implementación en la entrada de acceso del rol de la capacidad**

La entrada de acceso creada automáticamente, por sí sola, produjo el error `podtemplates is forbidden`. Argo CD enumera todos los tipos de recursos para crear su caché, así que `AmazonEKSEditPolicy` no bastó; al añadir `AmazonEKSAdminViewPolicy`, la sincronización funcionó. No se necesitó cluster-admin.

</details>

---

3. ¿Cómo se elimina la demora de varios minutos entre la confirmación y el estado Synced en Argo CD administrado?

   - A) Reduce `timeout.reconciliation` en `argocd-cm` a 30 segundos
   - B) Vuelve a crear la capacidad cada vez
   - C) Registra un webhook de GitHub en `/api/webhook` en la URL del servidor de la capacidad
   - D) Añade más nodos

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Registra un webhook de GitHub en `/api/webhook` en la URL del servidor de la capacidad**

La consulta periódica predeterminada midió entre 342 y 697 segundos, y el intervalo de consulta no es una clave configurable en la capacidad administrada. Con un webhook, las sincronizaciones tardaron entre 7,0 y 7,3 segundos. La URL del servidor está alojada en AWS, así que no hace falta un punto de conexión público independiente.

</details>

---

4. Después de aplicar un RGD a kro administrado, ves `ControllerReady=False` con el mensaje "cache sync timeout". ¿Cuál es la causa más probable?

   - A) Una interrupción del controlador del lado de AWS
   - B) A `AmazonEKSKROPolicy` le faltan permisos para la API generada por el RGD y sus recursos secundarios
   - C) Un error de sintaxis de CEL en el RGD
   - D) Presión de memoria en los nodos

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) A `AmazonEKSKROPolicy` le faltan permisos para la API generada por el RGD y sus recursos secundarios**

La política predeterminada solo cubre el grupo `kro.run` y los CRD. Como el mensaje no dice "forbidden", es fácil confundirlo con un fallo del controlador. Añade un grupo de Kubernetes a la entrada de acceso, vincula un ClusterRole por cada RGD y aplícalo antes que el RGD; de este modo se evitó la espera (se midieron 228 segundos, que presumiblemente corresponden al intervalo de reintento del controlador).

</details>

---

5. En las pruebas, ¿qué ocurrió cuando ya existía un CR de ACK Table con el mismo nombre que un recurso secundario de una instancia de kro?

   - A) kro se negó a crear la instancia
   - B) kro se hizo cargo del CR existente y cambió `spec.tableName`, dejando sin administrar la tabla original
   - C) Solo ocurre en kro administrado y no se reproduce en OSS
   - D) ACK fusionó automáticamente los dos CR

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) kro se hizo cargo del CR existente y cambió `spec.tableName`, dejando sin administrar la tabla original**

kro sobrescribió el CR mediante una aplicación del lado del servidor y le asignó la etiqueta `kro.run/owned=true`. Al eliminar la instancia, también se eliminó el CR del que se había hecho cargo. OSS 0.9.4 se comportó igual, así que este es el comportamiento del proyecto original. Mitiga el problema con sufijos de nombre específicos para cada RGD y espacios de nombres separados.

</details>

---

6. ¿Cómo se conceden permisos de IAM distintos a los equipos con ACK administrado?

   - A) Asocia IRSA a la ServiceAccount de cada controlador de servicio
   - B) Concede al rol de la capacidad solo permiso para asumir roles y asigna roles de equipo a los espacios de nombres con `IAMRoleSelector`
   - C) Habilita CARM y establece la cuenta con una anotación del espacio de nombres
   - D) La separación por equipos es imposible con la capacidad administrada

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Concede al rol de la capacidad solo permiso para asumir roles y asigna roles de equipo a los espacios de nombres con `IAMRoleSelector`**

Un Bucket en team-b, cuyo rol solo permitía SQS, falló con `AccessDenied`, y el mensaje indicaba qué rol se había usado. La misma configuración en controladores OSS requiere tanto `featureGates.IAMRoleSelector=true` como `enableCARM=false`; si se deja CARM activado, se produce CrashLoopBackOff.

</details>

---

7. ¿Qué mostraron las pruebas sobre un atributo de SQS cambiado fuera de ACK (con la CLI)?

   - A) ACK administrado siempre lo revierte en menos de un minuto
   - B) Ni ACK administrado ni OSS lo revirtieron periódicamente en 25 minutos; las reversiones en la versión administrada solo se observaron en lo que parecen ser reinicios del controlador
   - C) OSS lo revierte inmediatamente mediante eventos en tiempo real
   - D) El intervalo de resincronización de la versión administrada se configura con `disabledServices`

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Ni ACK administrado ni OSS lo revirtieron periódicamente en 25 minutos; las reversiones en la versión administrada solo se observaron en lo que parecen ser reinicios del controlador**

ACK no observa en tiempo real los cambios realizados en el lado de AWS. La resincronización predeterminada de OSS es de 10 horas y se puede ajustar; el intervalo de la versión administrada no está publicado y es fijo. Si es importante recuperarse rápidamente, bloquea los cambios fuera de banda con SCP o condiciones de IAM.

</details>

---

8. ¿Qué afirmación sobre las versiones de los controladores de la capacidad administrada es correcta?

   - A) Puedes fijar una con `create-capability --version`
   - B) Revertir la versión del clúster también revierte la versión de la capacidad
   - C) AWS elige y actualiza la versión, que puede cambiar independientemente de las actualizaciones del clúster; puedes consultarla en `version` dentro de `describe-capability`
   - D) Solo cambia cuando actualizas la versión de Kubernetes del clúster

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) AWS elige y actualiza la versión, que puede cambiar independientemente de las actualizaciones del clúster; puedes consultarla en `version` dentro de `describe-capability`**

Las API de creación y actualización no tienen un argumento para la versión, y las capacidades de Argo CD creadas con un día de diferencia indicaron `3.4.6-eks-2` y `3.4.7-eks-1`. Registra los cambios de versión, mantén un clúster de validación y prepárate para una alternativa temporal autogestionada basada en RETAIN. Si fijar las versiones es un requisito estricto, elige la opción autogestionada.

</details>

---

9. ¿Qué necesitaba un clúster spoke exclusivamente privado para que la capacidad de Argo CD del hub pudiera implementar una aplicación con `CreateNamespace=true`?

   - A) Un Transit Gateway y reglas de entrada para el grupo de seguridad
   - B) Una entrada de acceso para el rol de la capacidad del hub con Edit, AdminView y `AmazonEKSArgoCDClusterPolicy`
   - C) Su propia capacidad de Argo CD
   - D) Un punto de conexión de API público

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Una entrada de acceso para el rol de la capacidad del hub con Edit, AdminView y `AmazonEKSArgoCDClusterPolicy`**

La conexión y la autenticación funcionaron sin configurar la red, pero Edit y AdminView por sí solos produjeron el error `namespaces is forbidden`. El hub recibe esta política automáticamente; es necesario asociarla manualmente a los clústeres remotos. Una vez agotados los reintentos automáticos, fue necesaria una sincronización manual.

</details>

---

10. ¿En qué caso es más conveniente la opción autogestionada que la capacidad administrada?

   - A) Crear un hub que implemente en varios clústeres privados de EKS
   - B) El inicio de sesión de la organización ya está centralizado en Identity Center
   - C) Dependes de Argo CD Notifications o CMP, o de ACK FieldExport, y también implementas en clústeres que no son de EKS
   - D) Administras varios servicios de AWS, pero ejecutar controladores por servicio supone una carga

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Dependes de Argo CD Notifications o CMP, o de ACK FieldExport, y también implementas en clústeres que no son de EKS**

La capacidad administrada no incluye Notifications, CMP, `argocd admin`, las bibliotecas estándar de Lua ni FieldExport, y los Secrets de clúster solo aceptan ARN de EKS. Las demás opciones son casos en los que la capacidad administrada encaja bien.

</details>

---
