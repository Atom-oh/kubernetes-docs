# Cuestionario sobre EKS Hybrid Nodes Gateway

1. ¿Qué problema resuelve EKS Hybrid Nodes Gateway?
   - A) Reemplaza VPN/Direct Connect para la conectividad del control plane
   - B) Automatiza el networking a nivel de pod entre VPC y hybrid nodes mediante VXLAN tunnels, eliminando el pod routing manual
   - C) Proporciona un NAT gateway administrado para hybrid nodes
   - D) Cifra todo el tráfico entre cloud y on-premises

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Automatiza el networking a nivel de pod entre VPC y hybrid nodes mediante VXLAN tunnels, eliminando el pod routing manual**

**Explicación:**
EKS Hybrid Nodes Gateway automatiza el networking entre la VPC del cluster de EKS y Kubernetes Pods en Hybrid Nodes. Crea VXLAN tunnels entre gateway nodes basados en EC2 y hybrid nodes administrados por Cilium, y mantiene automáticamente las entradas de las VPC route tables. Esto elimina la necesidad de configuración manual de BGP, rutas estáticas o hacer que las redes de pod on-premises sean ruteables desde la VPC. Ten en cuenta que VPN/Direct Connect sigue siendo necesario para la conectividad base de los node.

</details>

---

2. ¿Cómo mantiene el gateway la alta disponibilidad?
   - A) Active-active con load balancing en varios gateways
   - B) Dos gateway pods como un Deployment con elección de líder basada en Kubernetes Lease
   - C) Redundancia administrada por AWS con failover automático
   - D) Ejecutándose en múltiples Availability Zones con comprobaciones de estado de Route 53

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Dos gateway pods como un Deployment con elección de líder basada en Kubernetes Lease**

**Explicación:**
El gateway se ejecuta como un Deployment de 2 pods en EC2 nodes etiquetados. Una elección de líder basada en Kubernetes Lease determina qué pod está activo. Solo el líder realiza acciones específicas del líder: administrar entradas de VPC route table y el CRD CiliumVTEPConfig. Cuando el líder falla, el liderazgo se transfiere al pod en espera, que luego actualiza las VPC routes para apuntar a su propia ENI.

</details>

---

3. ¿Cuál es el rol de CiliumVTEPConfig en la arquitectura del gateway?
   - A) Configura Cilium network policies para hybrid nodes
   - B) Registra la IP del gateway como un VTEP remoto para que los Cilium agents en hybrid nodes reenvíen el tráfico destinado a la VPC a través del VXLAN tunnel del gateway
   - C) Administra las actualizaciones de versión de Cilium en todo el cluster
   - D) Proporciona claves de cifrado para VXLAN tunnels

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Registra la IP del gateway como un VTEP remoto para que los Cilium agents en hybrid nodes reenvíen el tráfico destinado a la VPC a través del VXLAN tunnel del gateway**

**Explicación:**
El líder del gateway crea el recurso CiliumVTEPConfig. El Cilium agent de cada hybrid node on-premises lee esta configuración y registra la IP del gateway como un VTEP (VXLAN Tunnel Endpoint) remoto. Esto permite que Cilium sepa dónde enviar el tráfico destinado a la VPC: a través del VXLAN tunnel del gateway en lugar de intentar rutearlo directamente, lo cual fallaría sin pod CIDRs ruteables.

</details>

---

4. ¿Cuáles son los requisitos previos de CNI para usar Hybrid Nodes Gateway?
   - A) Cualquier CNI tanto en cloud nodes como en hybrid nodes
   - B) Cilium en cloud nodes y VPC CNI en hybrid nodes
   - C) Cilium (con VTEP habilitado) en hybrid nodes y VPC CNI en cloud nodes
   - D) VPC CNI tanto en cloud nodes como en hybrid nodes

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Cilium (con VTEP habilitado) en hybrid nodes y VPC CNI en cloud nodes**

**Explicación:**
El gateway requiere: (1) La versión de EKS de Cilium como CNI en hybrid nodes con soporte de VTEP habilitado, para que los hybrid nodes puedan participar en VXLAN tunneling. (2) AWS VPC CNI en cloud nodes, ya que el gateway depende del routing nativo de VPC para reenviar tráfico entre la VPC y el VXLAN tunnel. Ambos CNI trabajan juntos a través del gateway para habilitar una comunicación pod-to-pod fluida.

</details>

---

5. ¿Qué configuración de VXLAN usa el gateway?
   - A) VNI 1 en el puerto UDP 4789 (VXLAN estándar)
   - B) VNI 2 en el puerto UDP 8472 (valor predeterminado de Cilium)
   - C) VNI 100 en el puerto UDP 6081 (Geneve)
   - D) VNI 0 en el puerto UDP 443 (encapsulación HTTPS)

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) VNI 2 en el puerto UDP 8472 (valor predeterminado de Cilium)**

**Explicación:**
El gateway crea una VXLAN interface llamada `hybrid_vxlan0` con VNI (VXLAN Network Identifier) 2 en el puerto UDP 8472, que es el puerto VXLAN predeterminado de Cilium. Establece un tunnel hacia cada hybrid node programando entradas FDB (Forwarding Database), entradas ARP y rutas en la VXLAN interface. Los security groups y los firewalls on-premises deben permitir UDP 8472 de forma bidireccional.

</details>

---

6. ¿Cómo administra el gateway el routing de VPC?
   - A) Usa BGP para anunciar pod routes al VPC router
   - B) Crea y mantiene automáticamente entradas de VPC route table que apuntan los hybrid pod CIDRs a la ENI primaria del gateway activo
   - C) Modifica la main route table de la VPC para agregar reglas NAT
   - D) Configura Transit Gateway route tables

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Crea y mantiene automáticamente entradas de VPC route table que apuntan los hybrid pod CIDRs a la ENI primaria del gateway activo**

**Explicación:**
El node controller del gateway observa objetos CiliumNode y agrega o elimina automáticamente VXLAN tunnels a medida que los hybrid nodes se unen o salen. El leader pod mantiene las entradas de VPC route table, ruteando cada hybrid pod CIDR a la ENI primaria de la instancia de gateway activa. Por eso el IAM role del gateway necesita permisos ec2:DescribeRouteTables, ec2:CreateRoute y ec2:ReplaceRoute.

</details>

---

7. ¿Cuál es el modelo de precios de EKS Hybrid Nodes Gateway?
   - A) Cargo por hora basado en los datos procesados
   - B) Incluido en los precios de EKS Hybrid Nodes a $0.10 por hybrid node por hora
   - C) Sin cargo adicional por el gateway en sí, pero aplican los costos de instancias EC2 para gateway nodes
   - D) Gratis durante los primeros 3 meses, luego cargos estándar de networking de AWS

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Sin cargo adicional por el gateway en sí, pero aplican los costos de instancias EC2 para gateway nodes**

**Explicación:**
EKS Hybrid Nodes Gateway se ofrece sin cargo adicional y es open source (disponible en GitHub). Sin embargo, dado que el gateway se ejecuta en instancias EC2 en tu VPC, pagas los costos estándar de instancias EC2 para los gateway nodes. Esto lo convierte en una solución rentable en comparación con administrar manualmente infraestructura compleja de BGP o routing estático.

</details>

---

8. ¿Cuándo deberías elegir el enfoque del gateway en lugar del pod routing manual (BGP/rutas estáticas)?
   - A) Cuando necesitas la latencia más baja posible entre pods en cloud y on-premises
   - B) Cuando quieres simplificar las operaciones y evitar hacer ruteables las redes de pod on-premises, mientras habilitas comunicación con webhooks e integración con servicios de AWS
   - C) Cuando tienes más de 1000 hybrid nodes
   - D) Cuando usas un CNI distinto de Cilium en hybrid nodes

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Cuando quieres simplificar las operaciones y evitar hacer ruteables las redes de pod on-premises, mientras habilitas comunicación con webhooks e integración con servicios de AWS**

**Explicación:**
El gateway es ideal cuando quieres evitar cambios complejos en la infraestructura de red (configuración de BGP, administración de rutas estáticas). Habilita automáticamente: (1) comunicación de control plane a webhook en hybrid nodes, (2) tráfico pod-to-pod entre cloud y on-premises, (3) conectividad de servicios de AWS (ALB, NLB, Prometheus) a hybrid pods. El enfoque manual con BGP puede seguir siendo preferible cuando ya tienes infraestructura BGP o necesitas minimizar el salto adicional a través del gateway.

</details>
