# Cuestionario sobre la arquitectura de EKS con varias Accounts y varios clústeres

> Este cuestionario evalúa su comprensión de la [arquitectura de EKS con varias Accounts y varios clústeres](../../governance/03-eks-multi-account-multi-cluster.md).

---

1. ¿Cuál es un objetivo válido de validación para EKS con dos clústeres A/B?
   - A) Corregir un plano de control de EKS de una sola AZ
   - B) Probar que los fallos de actualización, complementos y webhooks quedan limitados a un clúster
   - C) Cubrir automáticamente las interrupciones de todas las Regions
   - D) Garantizar un costo menor

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Probar que los fallos de actualización, complementos y webhooks quedan limitados a un clúster**

**Explicación:**
La contención de fallos específica del clúster puede justificar el diseño. Las dependencias compartidas de VPC, DNS, Account y datos requieren un análisis independiente.

</details>

---

2. ¿Qué afirmación describe correctamente el comportamiento de seguridad ante fallos de ARC zonal shift?
   - A) El tráfico se bloquea de inmediato para cualquier carga de trabajo cuando ocurre una zonal shift
   - B) Si los endpoints de una carga de trabajo solo existen en la AZ afectada, EKS sigue enviando tráfico a esa AZ
   - C) Todas las cargas de trabajo se reubican automáticamente en otra AZ
   - D) Este comportamiento solo ocurre en EKS Fargate

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Si los endpoints de una carga de trabajo solo existen en la AZ afectada, EKS sigue enviando tráfico a esa AZ**

**Explicación:**
Este es el comportamiento de seguridad ante fallos: una carga de trabajo implementada en una sola AZ no queda protegida por zonal shift. Pruebe la carga N-1 y las excepciones de una sola AZ; esto no significa que una prueba práctica siempre detenga esa carga de trabajo.

</details>

---

3. ¿Qué implica la asignación de 1,024 paquetes/s de EC2 para tráfico link-local?
   - A) Revisar el tráfico combinado de DNS/IMDS/NTP y las métricas reales de DNS
   - B) Capacidad ilimitada reservada exclusivamente para DNS
   - C) Un límite de 100 Gbps por AZ
   - D) Prueba de que CoreDNS es la causa de fallos más frecuente

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A) Revisar el tráfico combinado de DNS/IMDS/NTP y las métricas reales de DNS**

**Explicación:**
Revise el límite compartido de link-local y el límite de la ENI de DNS de VPC. Compruebe linklocal_allowance_exceeded y la latencia de DNS en lugar de inferir la causa únicamente a partir de la densidad de Pods.

</details>

---

4. ¿Qué se debe comprobar al desactivar el balanceo entre zonas del target group de ALB?
   - A) Ahorros garantizados en la transferencia entre zonas de ALB
   - B) La capacidad por AZ, distinguiendo un 503 por una AZ vacía de la conmutación por error de un target en mal estado
   - C) Reinicios automáticos del clúster
   - D) Todos los targets pasan a estar en buen estado

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) La capacidad por AZ, distinguiendo un 503 por una AZ vacía de la conmutación por error de un target en mal estado**

**Explicación:**
La persistencia de target y los targets de Lambda tienen restricciones; un target vacío y uno en mal estado son situaciones distintas. La transferencia de datos regional entre zonas de ALB no tiene cargos adicionales por transferencia.

</details>
