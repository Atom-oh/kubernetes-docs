# Cuestionario sobre modos de red de Calico

> **Documento relacionado**: [Modos de red de Calico](../../../networking/calico/03-networking-modes.md)
> **Última actualización**: February 22, 2026

## Cuestionario

1. ¿Cuál es la sobrecarga en bytes añadida por la encapsulación IPIP?
   - A) 8 bytes
   - B) 20 bytes
   - C) 50 bytes
   - D) 100 bytes

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) 20 bytes**

**Explicación:**
La encapsulación IPIP (IP-in-IP) añade 20 bytes de sobrecarga a cada paquete. Este es el tamaño de una cabecera IP adicional que envuelve el paquete original. Es más eficiente que VXLAN, que añade 50 bytes de sobrecarga, por lo que IPIP ofrece un mejor rendimiento cuando se requiere encapsulación.

</details>

2. ¿Cuál es la sobrecarga en bytes añadida por la encapsulación VXLAN?
   - A) 20 bytes
   - B) 30 bytes
   - C) 50 bytes
   - D) 64 bytes

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) 50 bytes**

**Explicación:**
La encapsulación VXLAN añade aproximadamente 50 bytes de sobrecarga a cada paquete. Esto incluye la cabecera Ethernet externa (14 bytes), la cabecera IP externa (20 bytes), la cabecera UDP (8 bytes) y la cabecera VXLAN (8 bytes). Aunque esto es más que los 20 bytes de IPIP, VXLAN tiene mejor compatibilidad con diversos entornos de red.

</details>

3. ¿Qué hace el modo CrossSubnet en Calico?
   - A) Siempre usa encapsulación
   - B) Nunca usa encapsulación
   - C) Usa encapsulación solo para el tráfico entre subredes
   - D) Usa encapsulación solo para el tráfico dentro de la misma subred

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Usa encapsulación solo para el tráfico entre subredes**

**Explicación:**
El modo CrossSubnet es una optimización que aplica encapsulación (IPIP o VXLAN) solo cuando el tráfico cruza límites de subred. El tráfico entre nodos de la misma subred usa enrutamiento directo sin encapsulación. Esto ofrece lo mejor de ambos mundos: enrutamiento directo donde es posible y encapsulación solo cuando es necesaria.

</details>

4. ¿Cuáles son los requisitos para el modo de enrutamiento Direct (sin encapsulación)?
   - A) NIC de hardware especiales
   - B) La red subyacente debe poder enrutar el tráfico CIDR de Pod
   - C) Versión de kernel 5.0 o superior
   - D) El modo eBPF debe estar habilitado

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) La red subyacente debe poder enrutar el tráfico CIDR de Pod**

**Explicación:**
El modo de enrutamiento directo requiere que la infraestructura de red subyacente pueda enrutar el tráfico CIDR de Pod entre nodos. Esto normalmente significa usar BGP para anunciar rutas de Pod a la infraestructura de red o tener configuradas rutas estáticas. Sin esto, la red descartaría los paquetes destinados a las IP de Pod en otros nodos.

</details>

5. ¿Qué modo de red ofrece generalmente un mejor rendimiento: IPIP o VXLAN?
   - A) VXLAN siempre es más rápido
   - B) IPIP es generalmente más rápido debido a una menor sobrecarga
   - C) Tienen un rendimiento idéntico
   - D) El rendimiento depende de la versión de Kubernetes

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) IPIP es generalmente más rápido debido a una menor sobrecarga**

**Explicación:**
IPIP generalmente ofrece mejor rendimiento que VXLAN porque tiene una menor sobrecarga de encapsulación (20 bytes frente a 50 bytes). Menos sobrecarga significa más espacio para los datos reales de carga útil y menos procesamiento requerido para la encapsulación y desencapsulación. Sin embargo, VXLAN tiene compatibilidad más amplia y mejor soporte para descarga de hardware.

</details>

6. ¿Cuáles son las opciones válidas para ipipMode en un IPPool?
   - A) On, Off
   - B) True, False
   - C) Always, CrossSubnet, Never
   - D) Enabled, Disabled, Auto

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Always, CrossSubnet, Never**

**Explicación:**
El campo ipipMode en un IPPool acepta tres valores: `Always` (usar siempre encapsulación IPIP), `CrossSubnet` (usar IPIP solo para el tráfico entre subredes) y `Never` (deshabilitar IPIP). Estas mismas opciones también están disponibles para vxlanMode a fin de configurar el comportamiento de encapsulación VXLAN.

</details>

7. ¿Qué controla la configuración natOutgoing en un IPPool?
   - A) Si los pods pueden recibir tráfico NAT entrante
   - B) Si el tráfico de Pod que sale del cluster se enmascara
   - C) Si NAT se aplica entre pods
   - D) Si el nodo realiza NAT para servicios externos

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Si el tráfico de Pod que sale del cluster se enmascara**

**Explicación:**
La configuración `natOutgoing` controla si el tráfico de los pods en este pool de IP se enmascara (SNAT) al salir del cluster. Cuando se establece en true, la IP de origen del tráfico saliente cambia a la IP del nodo, lo que permite a los pods comunicarse con recursos externos incluso cuando las IP de Pod no se pueden enrutar fuera del cluster.

</details>

8. ¿Qué puerto UDP usa VXLAN de forma predeterminada?
   - A) 4789
   - B) 8472
   - C) 8080
   - D) 5473

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A) 4789**

**Explicación:**
VXLAN usa el puerto UDP 4789 de forma predeterminada, según lo especificado por IANA. Este es el puerto estándar utilizado en diferentes implementaciones de VXLAN. Algunas implementaciones antiguas (como las primeras versiones de Flannel) usaban el puerto 8472, pero Calico sigue el puerto estándar 4789.

</details>

9. ¿Por qué podría preferirse VXLAN a IPIP en entornos de Azure?
   - A) Azure proporciona aceleración de hardware para VXLAN
   - B) IPIP (protocolo IP 4) no tiene buen soporte en Azure
   - C) VXLAN es requerido por la política de Azure
   - D) Azure configura VXLAN automáticamente

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) IPIP (protocolo IP 4) no tiene buen soporte en Azure**

**Explicación:**
Azure tiene soporte limitado para la encapsulación IPIP porque el protocolo IP 4 puede estar bloqueado o presentar problemas en la red de Azure. VXLAN, al estar basado en UDP, funciona de manera más confiable en entornos de Azure. Esta es una recomendación habitual al desplegar Calico en Azure Kubernetes Service (AKS) o en VM de Azure.

</details>

10. ¿Cómo se debe optimizar MTU al usar encapsulación VXLAN con una MTU de red estándar de 1500 bytes?
    - A) Establecer MTU de Pod en 1500
    - B) Establecer MTU de Pod en 1450 (1500 - 50 bytes de sobrecarga)
    - C) El ajuste de MTU es automático
    - D) Establecer MTU de Pod en 1400

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Establecer MTU de Pod en 1450 (1500 - 50 bytes de sobrecarga)**

**Explicación:**
Al usar VXLAN con una MTU de red de 1500 bytes, la MTU de Pod debe establecerse en aproximadamente 1450 bytes (1500 - 50 bytes de sobrecarga de VXLAN) para evitar la fragmentación. Para IPIP, la MTU de Pod sería de 1480 bytes (1500 - 20 bytes de sobrecarga). Una configuración correcta de MTU evita problemas de rendimiento causados por la fragmentación de paquetes.

</details>

11. ¿Qué interfaz se crea en los nodos cuando se habilita el modo IPIP?
    - A) vxlan.calico
    - B) tunl0
    - C) cali0
    - D) ipip0

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) tunl0**

**Explicación:**
Cuando se habilita el modo IPIP, Calico crea una interfaz de túnel `tunl0` en cada nodo. Esta interfaz se usa para la encapsulación IPIP del tráfico entre nodos. La interfaz tunl0 gestiona la encapsulación y desencapsulación de paquetes cuando entran y salen del túnel IPIP.

</details>

12. ¿Cuál es la práctica recomendada para migrar del modo IPIP al modo VXLAN en un cluster en funcionamiento?
    - A) Cambiar directamente la configuración de IPPool
    - B) Crear un nuevo IPPool con VXLAN, migrar las cargas de trabajo y después eliminar el pool anterior
    - C) Reiniciar todos los nodos simultáneamente
    - D) La migración no es compatible; reconstruir el cluster

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Crear un nuevo IPPool con VXLAN, migrar las cargas de trabajo y después eliminar el pool anterior**

**Explicación:**
El enfoque recomendado para migrar entre modos de encapsulación es crear un nuevo IPPool con la configuración deseada, migrar gradualmente los Workloads para que usen el nuevo pool (mediante la recreación de pods o el uso de node selectors) y, después, eliminar el pool anterior una vez que la migración esté completa. Este enfoque minimiza las interrupciones y permite revertir los cambios si ocurren problemas.

</details>

---

[Volver a los materiales de aprendizaje](../../../networking/calico/03-networking-modes.md) | [Cuestionario anterior: Arquitectura](./02-architecture-quiz.md) | [Siguiente cuestionario: Análisis detallado de BGP](./04-bgp-deep-dive-quiz.md)
