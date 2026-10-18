# Cuestionario de EKS Hybrid Nodes Gateway

> **Última actualización**: 13 de septiembre de 2026

1. ¿Qué problema resuelve EKS Hybrid Nodes Gateway?
   - A) Reemplaza VPN/Direct Connect para conectar el plano de control
   - B) Automatiza las rutas de pods que administra el gateway y el reenvío VXLAN entre la VPC y los Hybrid Nodes
   - C) Proporciona un NAT gateway administrado para los Hybrid Nodes
   - D) Cifra todo el tráfico entre la nube y las instalaciones locales

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Automatiza las rutas de pods que administra el gateway y el reenvío VXLAN entre la VPC y los Hybrid Nodes**

**Explicación:**
El gateway programa rutas agregadas para los CIDR de pods de la VPC y el estado local de reenvío VXLAN. La red subyacente todavía debe enrutar el tráfico entre las direcciones IP del gateway y de los Hybrid Nodes a través de la conexión privada aprobada. Revisa quién administra las tablas de rutas, las rutas de retorno y las reglas de seguridad. La instalación no elimina todas las tareas de red manuales y la desinstalación no borra las rutas de AWS.

</details>

---

2. ¿Cómo mantiene el gateway la alta disponibilidad?
   - A) Activo-activo, con balanceo de carga entre varios gateways
   - B) Dos pods del gateway en un Deployment con elección de líder basada en Kubernetes Lease
   - C) Redundancia administrada por AWS con conmutación por error automática
   - D) Ejecución en varias zonas de disponibilidad con comprobaciones de estado de Route 53

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Dos pods del gateway en un Deployment con elección de líder basada en Kubernetes Lease**

**Explicación:**
El chart configura de forma predeterminada dos réplicas, con anti-afinidad obligatoria entre hosts y anti-afinidad preferida entre zonas de disponibilidad. Ambas mantienen entradas locales de túnel; solo el líder actualiza las rutas de la VPC y `CiliumVTEPConfig`. La expiración del Lease, el reemplazo de rutas, la convergencia de Cilium y la recuperación de las aplicaciones pueden interrumpir el tráfico. Más réplicas en espera no distribuyen el caudal, y un PDB no garantiza que se reemplace primero al líder o al pod en espera.

</details>

---

3. ¿Qué función cumple `CiliumVTEPConfig` en la arquitectura del gateway?
   - A) Configura las políticas de red de Cilium para los Hybrid Nodes
   - B) Registra la IP del gateway como VTEP remoto para que los agentes de Cilium en los Hybrid Nodes envíen el tráfico destinado a la VPC por el túnel VXLAN del gateway
   - C) Administra las actualizaciones de versión de Cilium en todo el clúster
   - D) Proporciona claves de cifrado para los túneles VXLAN

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Registra la IP del gateway como VTEP remoto para que los agentes de Cilium en los Hybrid Nodes envíen el tráfico destinado a la VPC por el túnel VXLAN del gateway**

**Explicación:**
La versión 1.0.2 del gateway administra el objeto `cilium.io/v2` llamado `hybrid-gateway`. Las entradas de `spec.endpoints` contienen `name`, `tunnelEndpoint`, `cidr` y `mac`. El endpoint usa la IP del nodo que es líder en ese momento y la dirección MAC real de la interfaz VXLAN. Este recurso no contiene claves de cifrado, y VNI no es uno de sus campos CRD.

</details>

---

4. ¿Qué requisitos de CNI hay para usar EKS Hybrid Nodes Gateway?
   - A) Cualquier CNI tanto en los nodos de la nube como en los Hybrid Nodes
   - B) Cilium en los nodos de la nube y VPC CNI en los Hybrid Nodes
   - C) Cilium mantenido por AWS, con VTEP habilitado y L7 deshabilitado, además de la configuración de red correcta en los nodos de la nube
   - D) VPC CNI tanto en los nodos de la nube como en los Hybrid Nodes

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Cilium mantenido por AWS, con VTEP habilitado y L7 deshabilitado, además de la configuración de red correcta en los nodos de la nube**

**Explicación:**
Usa una rama y versión de Cilium mantenido por AWS que cumpla el requisito mínimo de VTEP del gateway, con `vtep.enabled=true` y `l7Proxy=false`. Las funciones L7 de Cilium Ingress y Gateway API no pueden compartir esa configuración. En los nodos de la nube administrados o autoadministrados que usen `aws-node`, excluye los CIDR de pods híbridos del SNAT para el tráfico de ClusterIP hacia endpoints Hybrid. Auto Mode proporciona la red integrada; no instales ni configures un DaemonSet `aws-node` para Auto Mode. Una prueba directa a la IP del pod, por sí sola, no verifica el comportamiento de ClusterIP.

</details>

---

5. ¿Qué configuración VXLAN usa el gateway?
   - A) VNI 1 en el puerto UDP 4789 (VXLAN estándar)
   - B) VNI 2 en el puerto UDP 8472 (valor predeterminado de Cilium)
   - C) VNI 100 en el puerto UDP 6081 (Geneve)
   - D) VNI 0 en el puerto UDP 443 (encapsulación HTTPS)

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) VNI 2 en el puerto UDP 8472 (valor predeterminado de Cilium)**

**Explicación:**
La interfaz predeterminada es `hybrid_vxlan0`, con VNI 2 y UDP 8472. La versión 1.0.2 no asigna una IP a esa interfaz. Deriva direcciones MAC deterministas e instala entradas FDB y de vecinos, además de rutas `onlink`, usando la IP interna y el CIDR de pods de cada Hybrid Node. Permite el tráfico UDP subyacente requerido en ambas direcciones. La encapsulación VXLAN no cifra el tráfico.

</details>

---

6. ¿Cómo administra el gateway las rutas de la VPC?
   - A) Usa BGP para anunciar las rutas de pods al router de la VPC
   - B) Crea y mantiene automáticamente entradas en las tablas de rutas de la VPC que apuntan los CIDR de pods híbridos a la ENI principal del gateway activo
   - C) Modifica la tabla de rutas principal de la VPC para agregar reglas NAT
   - D) Configura las tablas de rutas de Transit Gateway

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Crea y mantiene automáticamente entradas en las tablas de rutas de la VPC que apuntan los CIDR de pods híbridos a la ENI principal del gateway activo**

**Explicación:**
La configuración del líder crea o reemplaza rutas para los `podCIDRs` agregados que estén configurados y luego actualiza `CiliumVTEPConfig`. Por separado, los eventos de `CiliumNode` actualizan las entradas locales de túnel por nodo en cada réplica del gateway. Los permisos de ejecución son `DescribeRouteTables`, `DescribeInstances`, `CreateRoute` y `ReplaceRoute`. El gateway no llama a `DeleteRoute`; al retirar el gateway, los operadores deben revisar y eliminar o restaurar solo las rutas que les pertenecen.

</details>

---

7. ¿Cuál es el modelo de precios de EKS Hybrid Nodes Gateway?
   - A) Un cargo por hora basado en los datos procesados
   - B) Está incluido en el precio de EKS Hybrid Nodes, a 0,10 USD por nodo híbrido y hora
   - C) El software del gateway no tiene cargo; se siguen aplicando los cargos de EC2 y de otra infraestructura o tráfico pertinente
   - D) Es gratis durante los primeros tres meses y luego se aplican los cargos estándar de redes de AWS

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) El software del gateway no tiene cargo; se siguen aplicando los cargos de EC2 y de otra infraestructura o tráfico pertinente**

**Explicación:**
El software del gateway no tiene un cargo adicional. Aun así, pueden cobrarse EC2, las tarifas de administración aplicables de Auto Mode, el almacenamiento, la transferencia de datos entre zonas, la conectividad privada y la observabilidad, además de los cargos del clúster y de Hybrid Nodes. El costo total depende del despliegue y del tráfico; no hay una garantía de ahorro universal.

</details>

---

8. ¿Cuándo conviene elegir el gateway en lugar del enrutamiento manual de pods con BGP o rutas estáticas?
   - A) Cuando se necesita la latencia más baja posible entre los pods de la nube y los de las instalaciones locales
   - B) Cuando el perfil de Cilium/VTEP de AWS y el salto adicional del gateway se ajustan al diseño y simplifican la administración de rutas de pods
   - C) Cuando hay más de 1000 Hybrid Nodes
   - D) Cuando se usa un CNI distinto de Cilium en los Hybrid Nodes

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Cuando el perfil de Cilium/VTEP de AWS y el salto adicional del gateway se ajustan al diseño y simplifican la administración de rutas de pods**

**Explicación:**
El gateway puede simplificar la administración de rutas de pods si el diseño admite el perfil requerido de Cilium/VTEP de AWS y un salto adicional activo-en espera. Los webhooks y los destinos de ALB/NLB siguen necesitando sus propias rutas, rutas de retorno, configuración de pods remotos, comprobaciones de estado y reglas de seguridad. Las redes de pods enrutables manualmente también pueden admitir estas rutas. Una infraestructura BGP/rutas estáticas existente u otras necesidades de CNI/L7 pueden favorecer otro diseño.

</details>
