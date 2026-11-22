# Cuestionario de fundamentos de redes, parte 4: El recorrido y la nube

> **Última actualización**: 11 de septiembre de 2026

Evalúa tu comprensión del recorrido completo de una solicitud y de su correspondencia con la nube/Kubernetes.

## Preguntas de opción múltiple

1. Para una nueva conexión HTTPS, ¿cuál es el orden conceptual correcto de dependencias (sin tener en cuenta las cachés ni las conexiones existentes)?
   - A) TLS → DNS → ARP → TCP → HTTP
   - B) Resolver la dirección del servidor → usar la conectividad de enlace/IP → negociación de TCP+TLS o QUIC → solicitud HTTP
   - C) ARP → TLS → DNS → NAT → HTTP
   - D) Conexión TCP → búsqueda DNS → TLS → enrutamiento → HTTP

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Resolver la dirección del servidor → usar la conectividad de enlace/IP → negociación de TCP+TLS o QUIC → solicitud HTTP**

**Explicación:**
Esto es un resumen de dependencias, no una traza de paquetes. Los mensajes DNS ya utilizan la conectividad de enlace/IP, y ARP o el descubrimiento de vecinos IPv6 pueden producirse durante el tráfico DNS o el tráfico posterior. NAT es opcional y el enrutamiento se aplica a todos los paquetes pertinentes. HTTP/3 usa QUIC con TLS 1.3 integrado; HTTP/1.1 y HTTP/2 suelen usar TCP con una negociación TLS independiente para HTTPS.

</details>

2. En un clúster que usa kube-proxy, ¿qué combinación describe el reenvío habitual de un Service ClusterIP?
   - A) CoreDNS: DHCP
   - B) kube-proxy: NAT + balanceo de carga L4
   - C) Complemento CNI: terminación TLS
   - D) NetworkPolicy: enrutamiento BGP

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) kube-proxy: NAT + balanceo de carga L4**

**Explicación:**
En Linux, kube-proxy programa iptables o nftables; su modo IPVS está obsoleto desde Kubernetes 1.35. Una implementación de Service basada en eBPF puede sustituir a kube-proxy, pero no es un modo eBPF de kube-proxy. El estado de Service/EndpointSlice proporciona los endpoints aptos. Los Services Headless no usan un ClusterIP, y NetworkPolicy necesita una implementación que la admita.

</details>

3. ¿Qué opción puede reducir el procesamiento de NAT Gateway para el tráfico de servicios de AWS compatibles, después de comprobar las dependencias de los endpoints y el costo total?
   - A) Consolidar en un solo NAT Gateway por región
   - B) Usar VPC endpoints adecuados para el tráfico de servicios compatibles, con el DNS, las rutas y las políticas de acceso necesarios
   - C) Asignar una IP pública a cada pod
   - D) Desactivar IPv6

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Usar VPC endpoints adecuados para el tráfico de servicios compatibles, con el DNS, las rutas y las políticas de acceso necesarios**

**Explicación:**
Los endpoints pueden excluir del recorrido por NAT el tráfico correspondiente, pero los endpoints de interfaz tienen cargos por hora y por datos, y la topología es importante. Los endpoints de gateway de S3/DynamoDB no tienen cargos adicionales por endpoint. Para extraer imágenes privadas de ECR, normalmente se necesitan los endpoints de interfaz ecr.api y ecr.dkr, además de una ruta a S3, DNS privado y los permisos de acceso adecuados. Las primeras extracciones mediante una caché de paso y las capas externas de Windows aún pueden requerir acceso a Internet. Calcula el costo total y conserva la salida necesaria; el ahorro y la eliminación del agotamiento de puertos no están garantizados en todos los casos.

</details>

---

[Volver al material de estudio](../../basics/06-network-fundamentals-part4.md) | [Siguiente cuestionario: Parte 5](./06-network-fundamentals-part5-quiz.md)
