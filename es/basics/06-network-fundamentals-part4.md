# Fundamentos de redes, parte 4: el recorrido de una solicitud y su correspondencia en la nube

> **Última actualización**: October 12, 2026

::: tip Esta es una serie de cuatro partes
[Parte 1: El modelo por capas, las capas de enlace y enrutamiento](./06-network-fundamentals-part1.md) ·
[Parte 2: La capa de transporte y TLS](./06-network-fundamentals-part2.md) ·
[Parte 3: Protocolos de aplicación](./06-network-fundamentals-part3.md) ·
**Parte 4: El recorrido de una solicitud y la nube** *(este documento)*
:::

Esta parte conecta los 25 protocolos y mecanismos de la serie mediante una solicitud ilustrativa y, a continuación, relaciona las responsabilidades correspondientes en AWS y Kubernetes. Se trata de comparaciones funcionales, no de sustituciones equivalentes uno a uno.

![Ruta ilustrativa de una solicitud: configuración de direcciones y DNS, entrega local y enrutamiento, NAT opcional y, después, TCP más TLS para HTTP/1.1 o HTTP/2, o QUIC con TLS integrado para HTTP/3. La reutilización de la caché y la configuración de red pueden omitir algunos pasos.](../.gitbook/assets/en-basics-06-network-fundamentals-part4-0.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-basics-06-network-fundamentals-part4-0.html)

---

## 6. Seguir una solicitud de principio a fin

Para una conexión nueva a `https://example.com`, lo siguiente es una guía conceptual de dependencias. No es un rastreo de paquetes: las consultas DNS y los propios paquetes del protocolo de enlace utilizan las capas de enlace y enrutamiento, y el estado almacenado en caché o una conexión existente pueden evitar ciertos pasos.

1. **Configuración de direcciones**: el host ya tiene direcciones, rutas y parámetros del resolvedor, obtenidos mediante DHCP, configuración estática, SLAAC/Router Advertisements de IPv6 u otro mecanismo administrado.
2. **DNS (o DoH)**: resuelve el destino cuando sea necesario. Un resolvedor recursivo puede usar su caché, seguir delegaciones o reenviar consultas; la aplicación no necesita contactar al servidor raíz. Los registros HTTPS también pueden anunciar parámetros de conexión.
3. **Resolución de vecinos**: para IPv4 sobre Ethernet, resuelve la MAC del siguiente salto seleccionado mediante ARP si no está en caché; IPv6 usa Neighbor Discovery. El siguiente salto puede ser un destino local o un router.
4. **Ethernet / Wi-Fi**: envía tramas a ese siguiente salto. Solo se usa una puerta de enlace predeterminada cuando la ruta seleccionada lo requiere.
5. **Enrutamiento IP**: los routers reenvían paquetes mediante sus tablas de reenvío. Las rutas pueden ser estáticas, conectadas o aprendidas mediante BGP, OSPF u otro plano de control; los protocolos de enrutamiento no realizan una negociación nueva para cada solicitud.
6. **NAT opcional**: una ruta de salida a Internet mediante IPv4 puede traducir una dirección privada a una dirección pública. Muchas rutas internas y de IPv6 no usan NAT; también existe NAT de direcciones privadas a privadas.
7. **TCP o QUIC**: establece o reutiliza el transporte. HTTP/1.1 y HTTP/2 suelen usar TCP; HTTP/3 usa QUIC sobre UDP.
8. **TLS**: autentica al par y establece claves de tráfico según el modo del protocolo de enlace. En QUIC, TLS 1.3 está integrado en el paso 7; la reanudación difiere de un protocolo de enlace nuevo basado en certificados.
9. **HTTP**: intercambia la solicitud y la respuesta mediante la versión negociada. HTTP/3 requiere la rama de QUIC; no funciona sobre la rama de TCP.
10. **Funciones de aplicación opcionales**: WebSocket, gRPC compatible con navegadores o WebRTC pueden crear conexiones adicionales o reutilizar/multiplexar transportes existentes, según la implementación.

**ICMP** puede informar de ciertos errores de la capa IP, como un destino inalcanzable o un paquete demasiado grande para una ruta. No informa de todos los fallos: los paquetes o errores ICMP pueden filtrarse, y los fallos de TLS/aplicación utilizan sus propios mecanismos. Combina ICMP permitido y pertinente con registros y mediciones de transporte/aplicación; la ausencia de un error ICMP no demuestra que la operación haya tenido éxito.

---

## 7. Dónde encajan estos conceptos en la nube

Las redes en la nube mantienen las responsabilidades de direccionamiento, enrutamiento, filtrado y transporte, pero los límites difieren de los de los dispositivos tradicionales. En AWS:

| Concepto tradicional | Equivalente en AWS |
|---|---|
| Segmentación y filtrado | VPC/subredes para límites lógicos de red; grupos de seguridad y NACL para filtrar, no como equivalentes de VLAN |
| Tablas de enrutamiento | Tablas de rutas de VPC, Transit Gateway |
| Emparejamiento BGP | Interfaces virtuales de Direct Connect; VPN de sitio a sitio con enrutamiento dinámico (también es posible el enrutamiento estático de VPN) |
| NAT / acceso privado a servicios | NAT Gateway traduce direcciones; los endpoints de VPC proporcionan rutas privadas a los servicios compatibles |
| Servidores DNS | Route 53, endpoints de Resolver |
| DHCP | Conjuntos de opciones DHCP de VPC |
| Terminación de TLS / certificados | Listeners HTTPS de ALB, listeners TLS de NLB o CloudFront; ACM administra los certificados compatibles en lugar de reenviar tráfico |
| Balanceo de carga de capa 7 | ALB; proxies de aplicación como Istio/Envoy en una malla de servicios administrada por separado |
| Acceso SSH | Systems Manager Session Manager |
| Cifrado entre segmentos internos | TLS/mTLS en aplicaciones o proxies; el cifrado de capa de red es una opción de diseño independiente |

El soporte de AWS App Mesh **finalizó el 30 de septiembre de 2026**. AWS indica que, después de esa fecha, ya no se podrá acceder a la consola ni a los recursos de App Mesh. Las implementaciones existentes han perdido su ruta de control y administración; consulta el aviso oficial de fin de soporte y las instrucciones de migración.

**Tres decisiones que conviene tomar primero** al diseñar:

1. **Plan de direcciones IP**: planifica los CIDR de las redes que deben interconectarse, incluidas las redes locales, los rangos de Pod y de Service. Los rangos superpuestos pueden requerir traducción o un rediseño; renumerar tiene un coste operativo, pero no existe un orden de costes universal aplicable a todos los casos.
2. **Ruta de salida**: asigna a cada destino una ruta de Internet o una ruta a servicios privados. Compara los cargos por hora y datos de NAT, los cargos por hora y datos de los endpoints de interfaz, la transferencia entre zonas de disponibilidad y los requisitos de disponibilidad. Los endpoints de gateway de S3/DynamoDB no tienen cargos adicionales por endpoint, pero no sustituyen todas las rutas a destinos de Internet.
3. **Punto de terminación del cifrado**: documenta el cifrado y la autenticación en cada salto, incluida la conexión al backend después de un balanceador de carga. Comprueba los requisitos de la carga de trabajo y las políticas aplicables; la terminación de TLS, por sí sola, no protege el siguiente salto.

---

## 8. Quién realiza estas tareas en Kubernetes

Dentro de un clúster se repiten los mismos conceptos con nombres de componentes nuevos. Esta tabla conecta esta serie con los documentos de análisis en profundidad que siguen.

| Concepto tradicional | Equivalente en Kubernetes |
|---|---|
| Asignación de IP de Pod | Integración de CNI/IPAM (VPC CNI, Cilium, …); no necesariamente usa DHCP para cada Pod |
| Entrega / reenvío local | Interfaces del host, gestión de vecinos y plano de datos de CNI; la implementación puede usar veth, rutas, túneles o eBPF |
| DNS | DNS del clúster, a menudo CoreDNS; `service.namespace.svc.<cluster-domain>` (`cluster.local` es un dominio configurado habitual) |
| IP virtual de Service / balanceo de carga de capa 4 | kube-proxy en Linux: iptables o nftables; IPVS está obsoleto desde la versión 1.35. Una implementación de eBPF puede reemplazar kube-proxy; no es un modo de kube-proxy |
| Política del tráfico de Pod | NetworkPolicy, aplicada únicamente por un controlador/plugin de red que la admita |
| Enrutamiento de capa 7 / terminación de TLS | Recursos de Ingress/Gateway API junto con un controlador implementador y un plano de datos |
| mTLS entre servicios | TLS en la aplicación o una malla configurada como Istio/Linkerd; no se habilita simplemente al instalar cualquier CNI |
| Enrutamiento / anuncio BGP | Por ejemplo, rutas BGP de Calico o anuncio BGP de direcciones de Service por MetalLB; sus funciones son distintas |

Para un Service ClusterIP común respaldado por Pods, el DNS del clúster suele resolver la IP del Service y, después, kube-proxy o su sustituto selecciona un endpoint apto mediante el estado de Service/EndpointSlice. El plano de datos reenvía el tráfico a ese endpoint, que puede estar en el mismo nodo o en otro. En cambio, los Services headless exponen las direcciones de los endpoints a través de DNS, y los Services ExternalName devuelven un CNAME. mTLS solo se aplica cuando los pares y las políticas pertinentes están configurados. Estas variaciones explican por qué no es válido asumir que «siempre se ejecutan todas las capas» al analizar el flujo de paquetes.

---

## Conclusión

Después de recorrer estos 25 protocolos y mecanismos, examina las compensaciones y el alcance de cada garantía.

TCP proporciona una entrega ordenada y fiable, con los costes de recuperación y ordenamiento correspondientes. UDP deja estas funciones a las capas superiores. QUIC proporciona flujos fiables y seguridad integrada sobre UDP. NAT conserva las direcciones IPv4 públicas, pero dificulta la accesibilidad a conexiones no solicitadas; ICE/STUN/TURN ayudan a resolver este problema. DoH protege un salto hacia el resolvedor; la visibilidad organizativa depende del resolvedor y de las políticas de los endpoints.

Al investigar un fallo, utiliza las garantías reales de cada capa y las pruebas observables para acotar el dominio del fallo. Una explicación plausible a nivel de protocolo es una hipótesis hasta que los registros, los rastreos o las mediciones permitan distinguirla de otras posibilidades.

---

## Próximos documentos

Relaciona primero estos fundamentos de protocolos con las observaciones de Linux y, a continuación, sigue la [ruta de aprendizaje de redes](../networking/README.md#learning-path) a través de contenedores y Services hasta las implementaciones de CNI:

- [Pila de red del kernel](../kernel/02-network-stack.md): rutas de entrada de socket/VFS, búferes y procesamiento de paquetes
- [Práctica de diagnóstico de redes en Linux](../networking/07-linux-network-diagnostics.md): interpreta observaciones y comprueba hipótesis | [Cuestionario](../quizzes/networking/07-linux-network-diagnostics-quiz.md)
- [Fundamentos de eBPF](./05-ebpf-fundamentals.md): cómo se procesan los paquetes en el kernel
- [Redes con Cilium](../networking/cilium/03-networking.md): el CNI basado en eBPF
- [Análisis en profundidad de Calico BGP](../networking/calico/04-bgp-deep-dive.md): enrutamiento BGP dentro del clúster
- [Amazon VPC CNI](../networking/01-vpc-cni.md): el VPC CNI y la asignación de IP

## Referencias

La lista de protocolos se inspiró en la infografía de ByteByteGo «What Keeps the Internet Running?»; las explicaciones y los comentarios prácticos se escribieron de forma independiente.

Referencias principales: [Modos de proxy de Service de Kubernetes](https://kubernetes.io/docs/reference/networking/virtual-ips/), [DNS de Service](https://kubernetes.io/docs/concepts/services-networking/dns-pod-service/), [NetworkPolicy](https://kubernetes.io/docs/concepts/services-networking/network-policies/), [Guía de costes de NAT Gateway](https://docs.aws.amazon.com/vpc/latest/userguide/nat-gateway-pricing.html), [Endpoints de VPC de ECR](https://docs.aws.amazon.com/AmazonECR/latest/userguide/vpc-endpoints.html), [Ciclo de vida de App Mesh](https://docs.aws.amazon.com/app-mesh/latest/userguide/what-is-app-mesh.html).
