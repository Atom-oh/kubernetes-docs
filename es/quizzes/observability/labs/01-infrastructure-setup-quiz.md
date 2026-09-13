# Cuestionario del Lab 01 de Observabilidad

<span id="observability-lab-part-1-infrastructure-setup-quiz"></span>

> **Última actualización**: September 13, 2026

1. ¿Cómo se debe usar el estado revisado de la versión de EKS?
   - A) La 1.31 necesariamente ya no tiene soporte.
   - B) Usar la línea base de soporte estándar revisada1.36 y volver a comprobar el estado actual de la Región y del soporte.
   - C) Las versiones menores tienen soporte para siempre.
   - D) El desfase de versión de kubectl nunca importa.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Usar la línea base de soporte estándar revisada1.36 y volver a comprobar el estado actual de la Región y del soporte.**

Distinga el soporte extendido del fin de soporte y verifique la compatibilidad entre cliente y servidor.

</details>

---

2. ¿Qué se debe comprobar al reutilizar una VPC?
   - A) Solo la cadena del ID de la VPC.
   - B) Las AZ de las subredes, la capacidad de direcciones, las rutas, DNS/SGs y CIDRs de servicio que no se solapen.
   - C) Hacer que ambos CIDRs de servicio sean idénticos.
   - D) NAT y los endpoints nunca son necesarios.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Las AZ de las subredes, la capacidad de direcciones, las rutas, DNS/SGs y CIDRs de servicio que no se solapen.**

El generador no crea recursos de red, por lo que siguen vigentes los requisitos reales de conectividad.

</details>

---

3. ¿Cómo se debe configurar el CIDR del cliente de la API pública?
   - A) Siempre0.0.0.0/0.
   - B) Un rango aprobado y reducido que coincida con el origen real.
   - C) Usar en producción una IP arbitraria de la documentación.
   - D) El CIDR por sí solo sustituye a la autenticación.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Un rango aprobado y reducido que coincida con el origen real.**

Verifique conjuntamente los endpoints privados y públicos, las direcciones de origen y la autenticación.

</details>

---

4. ¿Cuáles son las restricciones de confianza esenciales de IRSA?
   - A) Permitir todos los ServiceAccount.
   - B) El proveedor OIDC correcto y el subject exacto de audience/namespace/ServiceAccount.
   - C) Poner todos los permisos en el rol del nodo.
   - D) Codificar de forma fija una clave de acceso en el Pod.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) El proveedor OIDC correcto y el subject exacto de audience/namespace/ServiceAccount.**

El ARN del proveedor y el host/ruta del issuer deben identificar al mismo proveedor.

</details>

---

5. ¿Cuál es el límite de acceso de Aurora?
   - A) Un writer público abierto a Internet.
   - B) Subredes privadas y acceso a PostgreSQL5432 desde el SG real del cliente del servicio.
   - C) Basta con que los nombres de los SG sean parecidos.
   - D) Un writer multi-AZ aparece automáticamente.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Subredes privadas y acceso a PostgreSQL5432 desde el SG real del cliente del servicio.**

Un único writer es una decisión del laboratorio, no una garantía de alta disponibilidad (HA).

</details>

---

6. ¿Qué cuenta de base de datos debe usar la aplicación?
   - A) La cuenta maestra en todos los Pods.
   - B) Una cuenta de ejecución independiente con acceso DML a las tablas del laboratorio.
   - C) Una conexión pública sin contraseña.
   - D) Sobrescribir la contraseña existente en cada ejecución.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Una cuenta de ejecución independiente con acceso DML a las tablas del laboratorio.**

El bootstrap no sobrescribe los roles; verifique las credenciales candidatas después de un fallo.

</details>

---

7. ¿Cómo se deben proporcionar las contraseñas que contienen caracteres especiales?
   - A) Concatenarlas directamente en un DSN.
   - B) Pasar el valor JSON sin procesar como argumento de contraseña de URL.create.
   - C) Codificarlas en URL repetidamente.
   - D) Imprimirlas en los logs para copiarlas.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Pasar el valor JSON sin procesar como argumento de contraseña de URL.create.**

Verifique también TLS verify-full y la ruta real de la CA.

</details>

---

8. ¿Qué se debe hacer tras un fallo en la creación del cluster?
   - A) Seguir creando nombres nuevos.
   - B) Inspeccionar los recursos parciales, el estado y la propiedad bajo el mismo nombre.
   - C) Suponer que no hay cargos después de un fallo.
   - D) Eliminar todas las VPC.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Inspeccionar los recursos parciales, el estado y la propiedad bajo el mismo nombre.**

Un fallo de la CLI no prueba que no se hayan creado recursos.

</details>

---

9. ¿Qué implica comprobar la StorageClass gp3?
   - A) Un nombre que coincide siempre funciona.
   - B) Comprobar EBS CSI, los permisos, la clase real y la limpieza de volúmenes.
   - C) Sobrescribir siempre la clase compartida.
   - D) Eliminar un PVC y eliminar un snapshot son lo mismo.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Comprobar EBS CSI, los permisos, la clase real y la limpieza de volúmenes.**

Distinga los cambios en objetos compartidos de las responsabilidades de eliminación de recursos.

</details>

---

10. ¿Cómo se deben estimar los costes del laboratorio?
   - A) Siempre2,5USDporhora.
   - B) Incluir la Región real, el uso, la retención, NAT/LBs/almacenamiento/snapshots.
   - C) Tratar el precio mensual por usuario de AMG como una tarifa por hora del workspace.
   - D) Un límite de NodePool es un presupuesto absoluto.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Incluir la Región real, el uso, la retención, NAT/LBs/almacenamiento/snapshots.**

No afirme totales fijos ni ahorros no medidos.

</details>

---

[Volver a la guía](../../../labs/observability/01-infrastructure-setup-lab.md)