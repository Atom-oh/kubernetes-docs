# Cuestionario de revisión de seguridad para la separación de redes en Hybrid Nodes

> **Última actualización**: 16 de septiembre de 2026

[Guía de estudio: revisión de la separación de redes de Hybrid Nodes con los equipos de seguridad](../../eks-hybrid-nodes/11-network-separation-security.md)

1. ¿Cómo se debería corregir la afirmación «DX y los endpoints privados hacen que esto cumpla con la separación de redes»?
   - A) Basta con asociar el ID de la conexión DX.
   - B) Identifica la política aplicable, las conexiones, los permisos y los datos permitidos, las pruebas de implementación y las condiciones de aprobación.
   - C) Sin acceso a Internet, no existe ninguna conexión de administración externa.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B**

El enrutamiento privado reduce la exposición. No determina si la política del cliente permite la conexión de administración.

</details>

2. ¿Qué proporciona el endpoint de interfaz `com.amazonaws.<region>.eks`?
   - A) Un relay para todas las conexiones TCP 10250 desde el plano de control hasta el kubelet.
   - B) Una política de endpoint que reemplaza el RBAC de la API de Kubernetes.
   - C) Acceso privado a las API de administración de AWS EKS, como `DescribeCluster`.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C**

El endpoint privado de la API de Kubernetes y el endpoint de PrivateLink de la API de administración de AWS EKS son distintos.

</details>

3. Un firewall solo permite respuestas a las sesiones TCP 443 que inician los nodos híbridos. ¿Eso también permite la conexión del kubelet que utiliza `kubectl logs` en una implementación convencional con rutas?
   - A) No. Revisa la sesión independiente que inicia el servidor API hacia TCP 10250 del nodo.
   - B) Sí. Todos los paquetes del mismo clúster forman parte de la respuesta a una sesión existente.
   - C) Sí. DX omite automáticamente las reglas del firewall.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A**

Permitir el tráfico de retorno con seguimiento de estado no permite una conexión entrante nueva para otra sesión TCP.

</details>

4. ¿Qué comprobaciones demuestran el supuesto de este artículo de que solo se usa acceso privado?
   - A) Comprueba solo `endpointPrivateAccess=true`.
   - B) Confirma que el acceso privado esté habilitado y el acceso público deshabilitado; después verifica DNS, enrutamiento y los flujos reales.
   - C) Restringe `publicAccessCidrs`; limita el endpoint privado de la misma manera.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B**

Si el acceso público y el privado están habilitados, los nodos híbridos pueden usar direcciones públicas. Los CIDR de acceso público no controlan el acceso al endpoint privado.

</details>

5. ¿Qué afirmación sobre el cifrado es correcta en una implementación de DX?
   - A) DX cifra de forma predeterminada todos los flujos de pods.
   - B) Una IP privada permite omitir la validación de certificados TLS.
   - C) Conserva TLS y comprueba la compatibilidad y cobertura de IPsec/MACsec si se necesita cifrado adicional del enlace.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C**

DX no cifra el tráfico en tránsito de forma predeterminada. La protección de enlace MACsec tampoco tiene el mismo alcance que TLS de extremo a extremo de la aplicación.

</details>

6. Los pods de una aplicación empresarial se ejecutan en instalaciones locales. ¿Qué afirmación sobre el límite de los datos es correcta?
   - A) Todos los datos empresariales se copian automáticamente en AWS.
   - B) Todos los datos necesariamente permanecen en las instalaciones locales.
   - C) Revisa por separado los objetos de API, los Secrets, `logs`, los flujos de administración y el egreso de la aplicación, aparte del almacén de datos empresarial.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C**

La ubicación de los nodos no determina dónde se almacena o transfiere cada dato. Las operaciones de administración de Kubernetes pueden manejar datos confidenciales.

</details>

7. ¿Qué proceso se necesita si se usan direcciones ENI de EKS en listas de permitidos del firewall?
   - A) Conserva para siempre las direcciones `/32` observadas inicialmente.
   - B) Verifica la propiedad del clúster y el alcance de las direcciones, actualiza y vuelve a probar después de cambios de ENI, y registra los riesgos de subredes compartidas.
   - C) Permite todo el espacio de direcciones de AWS.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B**

Las IP de ENI pueden cambiar. Permitir una subred compartida amplia puede incluir otros recursos dentro del rango de origen permitido.

</details>

8. ¿Qué falta en la afirmación «quitamos `exec`, así que está bloqueado todo acceso a los datos mediado por administradores»?
   - A) Revisa también la creación o modificación de cargas de trabajo, el acceso privilegiado o mediante `hostPath`, otros subrecursos y los permisos de administración del host.
   - B) Los administradores del clúster no pueden cruzar los límites de espacios de nombres.
   - C) NetworkPolicy invalida todos los permisos administrativos.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A**

Restringir un comando no elimina otras rutas de acceso. Revisa todos los permisos de la identidad junto con los controles de admisión y de host.

</details>

9. ¿Qué afirmación sobre las pruebas para la revisión de seguridad es correcta?
   - A) VPC Flow Logs pueden reconstruir cada carga útil TLS y toda entrada o salida de `exec`.
   - B) CloudTrail hace innecesarios los registros de auditoría de Kubernetes.
   - C) Distingue los registros de red, la auditoría de Kubernetes y CloudTrail, y prueba los comportamientos permitidos y denegados con datos sintéticos.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C**

Los registros tienen alcances distintos. La auditoría de Kubernetes no registra todas las cargas útiles transmitidas y no reemplaza las pruebas de denegación ni la clasificación de datos.

</details>

10. Una política prohíbe toda conexión nueva iniciada desde la nube. ¿Mover los webhooks a nodos de la nube o usar Hybrid Nodes Gateway cumple automáticamente con esa política?
    - A) Cualquiera de los dos cambios basta.
    - B) No. Reevalúa el diseño, incluida la conexión independiente del kubelet y las rutas bidireccionales reales del gateway.
    - C) Basta con describir la arquitectura como PrivateLink.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B**

Mover los webhooks no elimina el requisito del kubelet. Hybrid Nodes Gateway no es una puerta de enlace de seguridad unidireccional. Si la política entra en conflicto con los requisitos de conectividad admitidos, reconsidera el diseño o las condiciones de aprobación formal.

</details>
