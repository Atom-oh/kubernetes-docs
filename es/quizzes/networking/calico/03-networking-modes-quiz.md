# Cuestionario sobre los modos de red de Calico

> **Documento relacionado**: [Modos de red de Calico](../../../networking/calico/03-networking-modes.md)
> **Última actualización**: 12 de septiembre de 2026

## Cuestionario

1. En IPIP de Calico, con una cabecera IPv4 externa sin opciones, ¿cuánta sobrecarga de cabecera se añade?
   - A) 8 bytes
   - B) 20 bytes
   - C) 50 bytes
   - D) 100 bytes

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) 20 bytes**

**Explicación:**
La cabecera IPv4 añadida ocupa 20 bytes cuando no incluye opciones. IPIP de Calico solo funciona con IPv4. Una cabecera menor deja más espacio para la carga útil, pero por sí sola no demuestra que la latencia vaya a ser menor ni que el rendimiento vaya a ser mayor con cualquier NIC, kernel o carga de trabajo.

</details>

2. Con VXLAN sobre IPv4 externo y sin etiquetas VLAN internas adicionales, ¿qué sobrecarga se añade por encima del paquete IP del Pod?
   - A) 20 bytes
   - B) 30 bytes
   - C) 50 bytes
   - D) 64 bytes

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) 50 bytes**

**Explicación:**
Los 50 bytes corresponden a IPv4 externo (20) + UDP (8) + VXLAN (8) + Ethernet interno (14). La cabecera Ethernet externa queda fuera de la MTU IP de la red subyacente. Con IPv6 externo, la sobrecarga pasa a 70 bytes. TCP y UDP también tienen tamaños distintos para la cabecera de transporte interna.

</details>

3. ¿Qué hace el modo CrossSubnet en Calico?
   - A) Siempre usa encapsulación
   - B) Nunca usa encapsulación
   - C) Usa encapsulación solo para el tráfico que cruza subredes
   - D) Usa encapsulación solo para el tráfico dentro de una misma subred

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Usa encapsulación solo para el tráfico que cruza subredes**

**Explicación:**
CrossSubnet compara las direcciones de nodo pertinentes y las máscaras de subred configuradas. El tráfico entre nodos de una misma subred puede evitar la encapsulación; el tráfico entre subredes distintas usa la encapsulación IPIP o VXLAN seleccionada. Este modo no detecta zonas de disponibilidad ni regiones, ni crea conectividad entre sitios.

</details>

4. ¿Qué requisitos tiene el modo de enrutamiento Direct (sin encapsulación)?
   - A) NIC de hardware especiales
   - B) La red subyacente debe poder enrutar el tráfico destinado a los CIDR de Pod
   - C) Versión de kernel 5.0 o posterior
   - D) Debe estar habilitado el modo eBPF

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) La red subyacente debe poder enrutar el tráfico destinado a los CIDR de Pod**

**Explicación:**
La red subyacente y la ruta de retorno deben poder enrutar las direcciones de Pod. BGP es una opción, pero también se pueden usar rutas estáticas y la programación de rutas de clúster mediante Felix, cuando sea compatible. En Calico 3.32, el campo clusterRoutingMode del operador puede seleccionar Felix para las rutas de clúster que no sean VXLAN; los anuncios BGP externos siguen requiriendo BGP.

</details>

5. ¿Qué comparación de rendimiento entre IPIP y VXLAN está justificada?
   - A) VXLAN siempre es más rápido
   - B) El rendimiento depende de la NIC y sus descargas, el kernel y el plano de datos, el tamaño de los paquetes, las rutas y la carga de trabajo
   - C) Ambos tienen el mismo rendimiento
   - D) El rendimiento depende únicamente de la versión de Kubernetes

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) El rendimiento depende de la NIC y sus descargas, el kernel y el plano de datos, el tamaño de los paquetes, las rutas y la carga de trabajo**

**Explicación:**
IPIP tiene una cabecera de encapsulación IPv4 más pequeña, mientras que las descargas de hardware y los detalles de implementación pueden cambiar el rendimiento. Ninguno de los dos modos es siempre más rápido. Los registros de pruebas comparativas bilingües anteriores discrepan y no cuentan con procedencia completa; por eso se conservan como informes, no como garantías de rendimiento.

</details>

6. ¿Qué valores son válidos para ipipMode en un IPPool?
   - A) On, Off
   - B) True, False
   - C) Always, CrossSubnet, Never
   - D) Enabled, Disabled, Auto

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Always, CrossSubnet, Never**

**Explicación:**
ipipMode y vxlanMode aceptan Always, CrossSubnet y Never. Always se aplica al tráfico entre nodos que puede usar el túnel; no crea un túnel físico para el tráfico que permanece en un mismo nodo. El campo de encapsulación separado del pool del operador usa valores como IPIPCrossSubnet o VXLANCrossSubnet; no confunda las dos API.

</details>

7. ¿Qué controla natOutgoing en un IPPool?
   - A) Si los Pods pueden recibir tráfico NAT entrante
   - B) Si se aplica SNAT al tráfico apto de este pool cuyo destino está fuera de todos los IPPool de Calico
   - C) Si se aplica NAT entre Pods
   - D) Si el nodo aplica NAT a servicios externos

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Si se aplica SNAT al tráfico apto de este pool cuyo destino está fuera de todos los IPPool de Calico**

**Explicación:**
La condición habitual es que el destino esté fuera de todos los IPPool de Calico, no simplemente fuera del clúster. Un pool deshabilitado aún puede definir un rango de destinos sin NAT, y las exclusiones adicionales de Felix pueden incluir direcciones IP de host. NAT no autoriza el tráfico ni garantiza que haya una ruta de retorno desde el exterior.

</details>

8. ¿Cuál es el puerto UDP VXLAN predeterminado de Calico?
   - A) 4789
   - B) 8472
   - C) 8080
   - D) 5473

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A) 4789**

**Explicación:**
El valor predeterminado de Calico es UDP 4789, y se puede configurar. Otras implementaciones actuales de VXLAN pueden usar 8472; este no es un puerto reservado solo a implementaciones obsoletas. IPIP usa el protocolo IP 4, que no es un puerto TCP ni UDP.

</details>

9. ¿Por qué la guía de overlays de Calico recomienda una configuración VXLAN adecuada en lugar de IPIP para las redes administradas por Calico en Azure?
   - A) Azure proporciona aceleración de hardware para VXLAN
   - B) La guía de overlays de Calico indica que VXLAN es compatible en Azure y que IPIP no lo es
   - C) La directiva de Azure exige VXLAN
   - D) Azure configura VXLAN automáticamente

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) La guía de overlays de Calico indica que VXLAN es compatible en Azure y que IPIP no lo es**

**Explicación:**
Este es un límite de compatibilidad de redes de Calico; no demuestra que todos los despliegues de AKS deban instalar un overlay de Calico. Seleccione la integración real de CNI y políticas del proveedor. Añadir una UDR no vuelve compatible un patrón de encapsulación IPIP que no lo es.

</details>

10. Si la MTU IP real de la red subyacente es de 1500 bytes, se usa IPv4 externa y no hay otra encapsulación, ¿cuál es el presupuesto de MTU IP del Pod para VXLAN?
   - A) Establecer la MTU del Pod en 1500
   - B) 1450 bytes: 1500 menos 50
   - C) 1500, porque la detección automática elimina la sobrecarga de encapsulación
   - D) Establecer la MTU del Pod en 1400

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) 1450 bytes: 1500 menos 50**

**Explicación:**
En estos supuestos, la sobrecarga de VXLAN sobre IPv4 es de 50 bytes, por lo que quedan 1450 bytes para el paquete IP del Pod. IPv6 externo, el cifrado, una ruta física con MTU menor o una ruta de servicio eBPF pueden cambiar el presupuesto. La detección automática de MTU puede elegir un valor, pero debe reflejar los modos y las rutas reales.

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
tunl0 suele ser la interfaz de túnel IPIP de Linux en esta configuración. Solo corresponde cuando IPIP está habilitado y es compatible. No cifra el tráfico y no es la interfaz que se usa para todos los modos de red de Calico.

</details>

12. Al migrar direcciones a otro IPPool de Calico, ¿qué principio es adecuado?
   - A) Cambiar directamente la configuración del IPPool
   - B) Verificar que el nuevo pool sea compatible y no se superponga, controlar las nuevas asignaciones, migrar las cargas de trabajo y sus dependencias, y retirar el pool antiguo solo después de comprobarlo todo
   - C) Reiniciar todos los nodos al mismo tiempo
   - D) La migración no es compatible; hay que reconstruir el clúster

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Verificar que el nuevo pool sea compatible y no se superponga, controlar las nuevas asignaciones, migrar las cargas de trabajo y sus dependencias, y retirar el pool antiguo solo después de comprobarlo todo**

**Explicación:**
La migración de CIDR/IPPool es distinta de un cambio solo de encapsulación. Planifique la propiedad del pool, la compatibilidad con el CIDR del clúster, la MTU, las solicitudes explícitas al pool antiguo, las asignaciones restantes y el despliegue de la aplicación. nodeSelector !all del operador no bloquea las solicitudes explícitas a un pool. No elimine un pool solo porque algunos Pods de reemplazo hayan recibido direcciones nuevas: pueden quedar asignaciones de túneles u otras, además de efectos de NAT y enrutamiento.

</details>

---

[Material de aprendizaje](../../../networking/calico/03-networking-modes.md) | [Cuestionario anterior](02-architecture-quiz.md) | [Siguiente cuestionario](04-bgp-deep-dive-quiz.md)
