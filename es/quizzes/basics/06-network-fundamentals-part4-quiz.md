# Cuestionario sobre fundamentos de redes, parte 4: el recorrido y la nube

> **Última actualización**: 11 de septiembre de 2026

Compruebe su comprensión del recorrido completo de una solicitud y de su correspondencia con la nube y Kubernetes.

## Preguntas de opción múltiple

1. Para una conexión HTTPS nueva, ¿cuál es el orden conceptual correcto de dependencias (sin considerar cachés ni conexiones existentes)?
   - A) TLS → DNS → ARP → TCP → HTTP
   - B) Resolver la dirección del servidor → usar conectividad de enlace/IP → handshake de TCP+TLS o QUIC → solicitud HTTP
   - C) ARP → TLS → DNS → NAT → HTTP
   - D) Conexión TCP → consulta DNS → TLS → enrutamiento → HTTP

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Resolver la dirección del servidor → usar conectividad de enlace/IP → handshake de TCP+TLS o QUIC → solicitud HTTP**

**Explicación:**
Este es un resumen de dependencias, no un seguimiento de paquetes. Los mensajes DNS ya usan conectividad de enlace/IP, y ARP o IPv6 Neighbor Discovery pueden ocurrir durante DNS o el tráfico posterior. NAT es opcional y el enrutamiento se aplica a todos los paquetes pertinentes. HTTP/3 usa QUIC con TLS 1.3 integrado; HTTP/1.1 y HTTP/2 suelen usar TCP con un handshake de TLS separado para HTTPS.

</details>

2. En un clúster que utiliza kube-proxy, ¿qué combinación describe el reenvío habitual de un Service ClusterIP?
   - A) CoreDNS: DHCP
   - B) kube-proxy: NAT y balanceo de carga L4
   - C) El plugin de CNI: terminación de TLS
   - D) NetworkPolicy: enrutamiento BGP

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) kube-proxy: NAT y balanceo de carga L4**

**Explicación:**
En Linux, kube-proxy programa iptables o nftables; su modo IPVS está obsoleto desde Kubernetes 1.35. Una implementación de Service basada en eBPF puede reemplazar kube-proxy, pero no es un modo eBPF de kube-proxy. El estado de Service/EndpointSlice proporciona los endpoints aptos. Los Services headless no usan ClusterIP y NetworkPolicy requiere una implementación compatible.

</details>

3. ¿Qué opción puede reducir el procesamiento de NAT Gateway para el tráfico compatible con servicios de AWS, tras comprobar las dependencias de endpoints y el costo total?
   - A) Consolidar en un NAT Gateway por Region
   - B) Usar VPC endpoints adecuados para el tráfico de servicios compatible, con el DNS, las rutas y las políticas de acceso requeridos
   - C) Asignar una IP pública a cada Pod
   - D) Desactivar IPv6

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Usar VPC endpoints adecuados para el tráfico de servicios compatible, con el DNS, las rutas y las políticas de acceso requeridos**

**Explicación:**
Los endpoints pueden quitar del recorrido de NAT el tráfico de servicios que coincida, pero los interface endpoints tienen cargos por hora y por datos, y la topología importa. Los gateway endpoints de S3/DynamoDB no tienen cargos adicionales por endpoint. La descarga privada de imágenes de ECR suele requerir los interface endpoints ecr.api y ecr.dkr, además de una ruta a S3, DNS privado y acceso adecuado. Las primeras descargas mediante pull-through cache o las capas externas de Windows pueden seguir necesitando acceso a Internet. Calcule el costo total y conserve la salida a Internet necesaria; el ahorro y la eliminación del agotamiento de puertos no están garantizados en todos los casos.

</details>

---

[Volver al material de estudio](../../basics/06-network-fundamentals-part4.md) | [Siguiente cuestionario: arquitectura de clúster](../core/01-cluster-architecture-quiz.md)
