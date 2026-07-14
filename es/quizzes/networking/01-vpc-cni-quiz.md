# Cuestionario de Amazon VPC CNI

Las siguientes preguntas evalúan tu comprensión de Amazon VPC CNI.

---

1. ¿Cuál es la función principal de IPAMD (L-IPAM Daemon) en VPC CNI?
   - A) Gestionar la configuración de DNS de los Pod
   - B) Preasignar y gestionar ENIs y direcciones IP
   - C) Aplicar Network Policies
   - D) Cifrar el tráfico entre nodos

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Preasignar y gestionar ENIs y direcciones IP**

**Explicación:**
IPAMD (L-IPAM Daemon) es un daemon que se ejecuta en cada nodo y gestiona ENIs (Elastic Network Interfaces), además de preasignar direcciones IP para que estas puedan asignarse rápidamente cuando se crean Pods. kubelet llama al CNI Binary, que recibe IPs de IPAMD y configura los espacios de nombres de red de los Pod.

</details>

---

2. ¿Cuál es la diferencia clave entre el modo Secondary IP y el modo Prefix Delegation?
   - A) Secondary IP admite solo IPv6; Prefix Delegation admite solo IPv4
   - B) Secondary IP asigna IPs individuales; Prefix Delegation asigna prefijos /28 (16 IPs)
   - C) Secondary IP es solo para EKS; Prefix Delegation es solo para clústeres autogestionados
   - D) Secondary IP usa redes overlay; Prefix Delegation usa enrutamiento directo

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Secondary IP asigna IPs individuales; Prefix Delegation asigna prefijos /28 (16 IPs)**

**Explicación:**
El modo Secondary IP asigna direcciones IP individuales, una a la vez, a cada ENI, mientras que el modo Prefix Delegation asigna prefijos IPv4 /28 (16 IPs) de una vez. Esto permite ejecutar más Pods por nodo y también mejora la velocidad de asignación de IPs.

</details>

---

3. ¿Por qué el número máximo de Pods para una instancia m5.large es 29 con VPC CNI?
   - A) Porque Kubernetes tiene un límite predeterminado de 29
   - B) Máximo de 3 ENIs × 10 IPs por ENI = 30, menos el número de ENIs (3) para IPs primarias
   - C) Está limitado por un límite flexible de AWS
   - D) Está limitado por el tamaño de la subred VPC

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Máximo de 3 ENIs × 10 IPs por ENI = 30, menos el número de ENIs (3) para IPs primarias**

**Explicación:**
El número máximo de Pods en VPC CNI se calcula como (número de ENIs × IPs por ENI) - número de ENIs. La m5.large admite hasta 3 ENIs con 10 direcciones IPv4 por ENI. Dado que la Primary IP de cada ENI la utiliza el nodo, (3 × 10) - 3 = 27. El número real puede variar ligeramente debido a los Pods con redes de host y otros factores adicionales.

</details>

---

4. ¿Cuál es el propósito de la variable de entorno WARM_IP_TARGET?
   - A) Establecer el número máximo de IPs que se pueden asignar a los Pods
   - B) Establecer el número de IPs de reserva que se deben preasignar en cada nodo
   - C) Limitar el número total de IPs en todo el clúster
   - D) Establecer el TTL (Time To Live) de las direcciones IP

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Establecer el número de IPs de reserva que se deben preasignar en cada nodo**

**Explicación:**
WARM_IP_TARGET controla el número de IPs de reserva que IPAMD preasigna en cada nodo. Esto garantiza que las IPs estén disponibles de inmediato cuando se crean nuevos Pods. Un valor mayor acelera el inicio de los Pods, pero utiliza más IPs, mientras que un valor menor mejora la eficiencia de IPs, pero puede ralentizar el inicio de los Pods.

</details>

---

5. ¿Qué afirmación sobre la compatibilidad nativa de VPC CNI con Network Policy es correcta?
   - A) Usa Calico internamente para aplicar Network Policies
   - B) Admite Network Policy nativa basada en eBPF a partir de v1.14
   - C) Network Policy no es compatible con EKS
   - D) Usa iptables para aplicar Network Policies

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Admite Network Policy nativa basada en eBPF a partir de v1.14**

**Explicación:**
A partir de VPC CNI v1.14, se admite Network Policy nativa de Kubernetes basada en eBPF. Antes era necesario un motor de Network Policy independiente como Calico, pero ahora VPC CNI puede procesar recursos estándar de Kubernetes NetworkPolicy por sí mismo.

</details>

---

6. ¿Cuál es el propósito principal de usar Custom Networking (ENIConfig)?
   - A) Personalizar la configuración del servidor DNS de los Pod
   - B) Asignar IPs de Pod desde una subred diferente a la del nodo
   - C) Instalar plugins de CNI personalizados
   - D) Cambiar el nombre de la interfaz de red del nodo

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Asignar IPs de Pod desde una subred diferente a la del nodo**

**Explicación:**
Custom Networking usa CRDs de ENIConfig para asignar IPs de Pod desde una subred diferente a la del nodo. Esto resulta útil cuando las IPs de la subred de los nodos son insuficientes, cuando se deben aplicar diferentes Security Groups a los Pods o cuando las redes de nodos y Pods necesitan estar separadas. Normalmente se usa con Secondary CIDRs (por ejemplo, 100.64.0.0/16).

</details>

---

7. ¿Cuáles son las funciones de Trunk ENI y Branch ENI en la característica de Security Group por Pod?
   - A) Trunk ENI gestiona el tráfico externo; Branch ENI gestiona el tráfico interno
   - B) Trunk ENI es la ENI principal del nodo que aloja Branch ENIs; Branch ENIs son ENIs virtuales asignadas a cada Pod
   - C) Trunk ENI es para IPv4; Branch ENI es para IPv6
   - D) Trunk ENI y Branch ENI desempeñan funciones idénticas

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Trunk ENI es la ENI principal del nodo que aloja Branch ENIs; Branch ENIs son ENIs virtuales asignadas a cada Pod**

**Explicación:**
Los Security Groups por Pod usan una arquitectura Trunk/Branch ENI. Trunk ENI es la ENI principal conectada al nodo que aloja varias Branch ENIs. Las Branch ENIs son interfaces de red virtuales asignadas a cada Pod, lo que permite aplicar AWS Security Groups de forma independiente. Esto permite un control de seguridad de red granular en el nivel de Pod.

</details>

---

8. ¿Cuál NO es una solución eficaz para los problemas de agotamiento de IPs?
   - A) Habilitar Prefix Delegation
   - B) Agregar Secondary CIDR
   - C) Cambiar todos los Pods al modo de red de host
   - D) Usar Custom Networking con subredes dedicadas para Pods

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Cambiar todos los Pods al modo de red de host**

**Explicación:**
Ejecutar todos los Pods en el modo de red de host (`hostNetwork: true`) resolvería técnicamente los problemas de asignación de IPs, pero elimina el aislamiento de red entre Pods y puede provocar conflictos de puertos, lo que lo convierte en una solución poco práctica. Las soluciones adecuadas para el agotamiento de IPs incluyen habilitar Prefix Delegation, agregar Secondary CIDRs, usar Custom Networking y ajustar WARM_IP_TARGET.

</details>
