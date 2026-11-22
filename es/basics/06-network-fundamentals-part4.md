# Fundamentos de redes, parte 4: el recorrido de una solicitud y su correspondencia con la nube

> **Última actualización**: 12 de octubre de 2026

::: tip Esta es una serie de cinco partes
[Parte 1: El modelo por capas, las capas de enlace y de enrutamiento](./06-network-fundamentals-part1.md) ·
[Parte 2: La capa de transporte y TLS](./06-network-fundamentals-part2.md) ·
[Parte 3: Protocolos de aplicación](./06-network-fundamentals-part3.md) ·
**Parte 4: El recorrido de una solicitud y la nube** *(este documento)* ·
[Parte 5: Dispositivos de red, LAN y WAN](./06-network-fundamentals-part5.md)
:::

Esta parte relaciona los 25 protocolos y mecanismos de la serie mediante el ejemplo de una solicitud y, después, establece correspondencias entre las responsabilidades relacionadas en AWS y Kubernetes. Son comparaciones funcionales, no sustituciones directas.

![Ruta ilustrativa de una solicitud: configuración de direcciones y DNS, entrega local y enrutamiento, NAT opcional y, luego, TCP más TLS para HTTP/1.1 o HTTP/2, o QUIC con TLS integrado para HTTP/3. La reutilización de la caché y la configuración de red pueden omitir pasos.](../.gitbook/assets/en-basics-06-network-fundamentals-part4-0.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-basics-06-network-fundamentals-part4-0.html)

---

## 6. Seguir una solicitud de principio a fin

Para una conexión nueva a `https://example.com`, lo siguiente es una guía conceptual de dependencias. No es un rastreo de paquetes: las consultas DNS y los paquetes del protocolo de enlace también usan las capas de enlace y de enrutamiento, y la información almacenada en caché o una conexión existente pueden evitar algunos pasos.

1. **Configuración de direcciones**: el host ya tiene direcciones, rutas y parámetros del solucionador, obtenidos mediante DHCP, configuración estática, SLAAC/Router Advertisements de IPv6 u otro mecanismo administrado.
2. **DNS (o DoH)**: resolver el destino cuando sea necesario. Un solucionador recursivo puede usar su caché, seguir delegaciones o reenviar consultas; la aplicación no tiene por qué contactar con el servidor raíz. Los registros HTTPS también pueden anunciar parámetros de conexión.
3. **Resolución de vecinos**: para IPv4 sobre Ethernet, si la dirección no está en caché, resolver con ARP la dirección MAC del siguiente salto seleccionado; IPv6 usa Neighbor Discovery. El siguiente salto puede ser un destino local o un enrutador.
4. **Ethernet / Wi-Fi**: enviar tramas a ese siguiente salto. Solo se usa una puerta de enlace predeterminada cuando la ruta seleccionada lo requiere.
5. **Enrutamiento IP**: los enrutadores reenvían paquetes mediante sus tablas de reenvío. Las rutas pueden ser estáticas, conectadas o aprendidas mediante BGP, OSPF u otro plano de control; los protocolos de enrutamiento no realizan una nueva negociación para cada solicitud.
6. **NAT opcional**: una ruta de salida a Internet con IPv4 puede traducir una dirección privada a una pública. Muchas rutas internas y de IPv6 no usan NAT; también existe NAT de privado a privado.
7. **TCP o QUIC**: establecer o reutilizar el transporte. HTTP/1.1 y HTTP/2 suelen usar TCP; HTTP/3 usa QUIC sobre UDP.
8. **TLS**: autenticar al par y establecer claves de tráfico según el modo del protocolo de enlace. En QUIC, TLS 1.3 está integrado en el paso 7; la reanudación difiere de un protocolo de enlace nuevo basado en certificados.
9. **HTTP**: intercambiar la solicitud y la respuesta mediante la versión negociada. HTTP/3 requiere la rama de QUIC; no funciona sobre la rama de TCP.
10. **Funciones opcionales de la aplicación**: WebSocket, gRPC compatible con navegadores o WebRTC pueden crear conexiones adicionales o reutilizar/multiplexar transportes existentes, según la implementación.

**ICMP** puede informar de ciertos errores de la capa IP, como un destino inalcanzable o un paquete demasiado grande para una ruta. No informa de todos los fallos: los paquetes o los errores ICMP pueden filtrarse, y los fallos de TLS y de la aplicación usan sus propios mecanismos. Combine ICMP pertinente y permitido con registros y mediciones de transporte y de la aplicación; la ausencia de un error ICMP no demuestra que la operación haya tenido éxito.

---

## 7. Dónde se aplican estos conceptos en la nube

Las redes en la nube mantienen las responsabilidades de direccionamiento, enrutamiento, filtrado y transporte, pero sus límites son distintos de los de los dispositivos tradicionales. En AWS:

| Concepto tradicional | Equivalente en AWS |
|---|---|
| Segmentación y filtrado | VPC/subredes para límites lógicos de red; grupos de seguridad y NACL para el filtrado, no equivalentes de VLAN |
| Tablas de enrutamiento | Tablas de rutas de VPC, Transit Gateway |
| Emparejamiento BGP | Interfaces virtuales de Direct Connect; VPN de sitio a sitio con enrutamiento dinámico (también es posible el enrutamiento estático de VPN) |
| NAT / acceso a servicios privados | NAT Gateway traduce direcciones; los puntos de enlace de VPC ofrecen rutas privadas a los servicios compatibles |
| Servidores DNS | Route 53, puntos de enlace de Resolver |
| DHCP | Conjuntos de opciones DHCP de VPC |
| Terminación de TLS / certificados | Receptores HTTPS de ALB, receptores TLS de NLB o CloudFront; ACM administra los certificados compatibles, pero no reenvía tráfico |
| Balanceo de carga de capa 7 | ALB; proxies de aplicación como Istio/Envoy en una malla de servicios administrada por separado |
| Acceso SSH | Systems Manager Session Manager |
| Cifrado de segmentos internos | TLS/mTLS en aplicaciones o proxies; el cifrado de capa de red es una opción de diseño independiente |

La compatibilidad con AWS App Mesh **finalizó el 30 de septiembre de 2026**. AWS indica que, después de esa fecha, ya no se puede acceder a la consola ni a los recursos de App Mesh. Las implementaciones existentes han perdido su vía de control y administración; consulte el aviso oficial de fin de compatibilidad y las instrucciones de migración.

**Tres decisiones que conviene tomar primero** al diseñar:

1. **Plan de direcciones IP**: planifique CIDR para las redes que deban interconectarse, incluidas las redes locales, los rangos de Pod y de Service. La superposición puede requerir traducción o un rediseño; cambiar la numeración tiene un costo operativo, pero no hay un orden de costos universal.
2. **Ruta de salida**: haga corresponder cada destino con una ruta a Internet o a servicios privados. Compare los cargos por hora y por datos de NAT, los cargos por hora y por datos de los puntos de enlace de interfaz, la transferencia entre zonas de disponibilidad y los requisitos de disponibilidad. Los puntos de enlace de gateway de S3/DynamoDB no tienen cargos adicionales por punto de enlace, pero no sustituyen todas las rutas a Internet.
3. **Punto de terminación del cifrado**: documente el cifrado y la autenticación en cada salto, incluida la conexión al backend después de un balanceador de carga. Verifique los requisitos de la carga de trabajo y las políticas aplicables; la terminación de TLS por sí sola no protege el siguiente salto.

---

## 8. Quién realiza estas tareas en Kubernetes

Dentro de un clúster se repiten los mismos conceptos, pero con nombres de componentes nuevos. Esta tabla sirve de puente entre esta serie y los documentos de análisis detallado que siguen.

| Concepto tradicional | Equivalente en Kubernetes |
|---|---|
| Asignación de IP a Pod | Integración de CNI/IPAM (VPC CNI, Cilium, …); esto no necesariamente usa DHCP para cada Pod |
| Entrega local / reenvío | Interfaces del host, gestión de vecinos y plano de datos de CNI; la implementación puede usar veth, rutas, túneles o eBPF |
| DNS | DNS del clúster, a menudo CoreDNS; `service.namespace.svc.<cluster-domain>` (`cluster.local` es un dominio configurado comúnmente) |
| IP virtual de Service / balanceo de capa 4 | kube-proxy en Linux: iptables o nftables; IPVS está obsoleto desde la versión 1.35. Una implementación de eBPF puede reemplazar kube-proxy; no es un modo de kube-proxy |
| Política de tráfico de Pod | NetworkPolicy, aplicada únicamente por un controlador/complemento de red que la admita |
| Enrutamiento de capa 7 / terminación de TLS | Recursos de Ingress/Gateway API junto con un controlador implementador y un plano de datos |
| mTLS entre Services | TLS de aplicación o una malla configurada, como Istio/Linkerd; no se habilita simplemente instalando cualquier CNI |
| Enrutamiento / anuncio BGP | Por ejemplo, rutas BGP de Calico o anuncio BGP de direcciones de Service por MetalLB; sus funciones son distintas |

En un Service ClusterIP común respaldado por Pods, el DNS del clúster suele resolver la IP del Service y, luego, kube-proxy o su sustituto selecciona un punto de enlace apto mediante el estado de Service/EndpointSlice. El plano de datos reenvía el tráfico a ese punto de enlace, que puede estar en el mismo nodo o en otro. En cambio, los Services headless exponen las direcciones de los puntos de enlace mediante DNS, y los Services ExternalName devuelven un CNAME. mTLS se aplica solo cuando se configuran los pares y las políticas pertinentes. Estas variaciones explican por qué no es válido suponer que «siempre se ejecutan todas las capas» al analizar el flujo de paquetes.

---

## Conclusión

Después de recorrer estos 25 protocolos y mecanismos, examine las compensaciones y el alcance de cada garantía.

TCP proporciona una entrega ordenada y fiable, con costos de recuperación y ordenamiento. UDP deja estas funciones a las capas superiores. QUIC proporciona flujos fiables y seguridad integrada sobre UDP. NAT conserva las direcciones IPv4 públicas, pero complica la accesibilidad no solicitada, algo que ICE/STUN/TURN ayudan a resolver. DoH protege un salto hasta el solucionador; la visibilidad de la organización depende del solucionador y de la política del punto de conexión.

Al investigar un fallo, use las garantías reales de cada capa y las pruebas observables para acotar el dominio del problema. Una explicación plausible a nivel de protocolo es una hipótesis hasta que los registros, los rastreos o las mediciones permitan distinguirla de otras posibilidades.

---

## Documentos siguientes

Relacione primero estos fundamentos de protocolos con las observaciones de Linux y, después, siga la [ruta de aprendizaje de redes](../networking/README.md#learning-path) a través de los contenedores y los Services hasta las implementaciones de CNI:

- [Parte 5: Dispositivos de red y fundamentos de LAN y WAN](./06-network-fundamentals-part5.md): decisiones de reenvío por dispositivo, VLAN/STP/FHRP, NAT y CGNAT, tipos de WAN | [Cuestionario](../quizzes/basics/06-network-fundamentals-part5-quiz.md)
- [Pila de redes del kernel](../kernel/02-network-stack.md): rutas de entrada de socket/VFS, búferes y procesamiento de paquetes
- [Práctica de diagnóstico de redes en Linux](../networking/07-linux-network-diagnostics.md): interpretar observaciones y poner a prueba hipótesis | [Cuestionario](../quizzes/networking/07-linux-network-diagnostics-quiz.md)
- [Fundamentos de eBPF](./05-ebpf-fundamentals.md): cómo se procesan los paquetes en el kernel
- [Redes con Cilium](../networking/cilium/03-networking.md): el CNI basado en eBPF
- [Análisis detallado de BGP con Calico](../networking/calico/04-bgp-deep-dive.md): enrutamiento BGP dentro del clúster
- [Amazon VPC CNI](../networking/01-vpc-cni.md): el VPC CNI y la asignación de IP

## Referencias

La lista de protocolos se inspiró inicialmente en la infografía «What Keeps the Internet Running?» de ByteByteGo; las explicaciones y los comentarios prácticos se redactaron de forma independiente.

Referencias principales: [Modos de proxy de Service en Kubernetes](https://kubernetes.io/docs/reference/networking/virtual-ips/), [DNS de Service](https://kubernetes.io/docs/concepts/services-networking/dns-pod-service/), [NetworkPolicy](https://kubernetes.io/docs/concepts/services-networking/network-policies/), [Guía de costos de NAT Gateway](https://docs.aws.amazon.com/vpc/latest/userguide/nat-gateway-pricing.html), [Puntos de enlace de VPC para ECR](https://docs.aws.amazon.com/AmazonECR/latest/userguide/vpc-endpoints.html), [Ciclo de vida de App Mesh](https://docs.aws.amazon.com/app-mesh/latest/userguide/what-is-app-mesh.html).
