# Validación de la conectividad de los Pods sin SNAT y PrivateLink

> **Versiones compatibles**: EKS 1.36, Cilium 1.18.13 (compilación de AWS), complemento CoreDNS v1.14.7-eksbuild.10, configuración predeterminada de VPC CNI
> **Última actualización**: 19 de octubre de 2026

Algunos firewalls deben identificar los Pods locales mediante la **IP del Pod**, no mediante la IP del nodo. Esta página documenta una prueba de ese requisito: se cambió Cilium al enrutamiento nativo con el enmascaramiento deshabilitado y se ejecutaron 38 comprobaciones de conectividad dentro y fuera del clúster. También cubre la ruta de PrivateLink que permite a los Pods locales llamar a las API de AWS (STS, S3) sin pasar por internet, y el comportamiento de DNS cuando se interrumpe el enlace.

El entorno de prueba **simula una instalación local**. Una segunda VPC se conecta mediante un Transit Gateway (TGW), y sus instancias EC2 se registran como nodos híbridos. No se admite ejecutar nodos híbridos en EC2 y se factura con la tarifa de nodo híbrido. Las cifras corresponden a una sola ejecución, el 19 de octubre de 2026. Vuelva a validarlas en una red local real mediante Direct Connect o VPN.

## Primero, el alcance de la compatibilidad

En la tabla «Capacidades compatibles» de [Configurar CNI para nodos híbridos](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-cni.html), el único **modo de red compatible con AWS para Cilium es «encapsulación VXLAN»**. La misma página explica que se puede deshabilitar el enmascaramiento; en ese caso, los CIDR de los Pods deben ser enrutables en la red local, y recomienda usar Cilium BGP Control Plane para hacerlos enrutables.

| Configuración | Dónde son visibles las IP de los Pods | Compatibilidad con AWS | Hybrid Nodes Gateway |
|---|---|---|---|
| VXLAN + enmascaramiento (predeterminado) | En ningún lugar fuera del clúster: IP del nodo | Compatible | Utilizable |
| VXLAN + enmascaramiento desactivado + BGP | De la nube a las instalaciones locales, servidores locales | Compatible | Utilizable |
| **Enrutamiento nativo + enmascaramiento desactivado** (esta página) | Lo anterior, **más el segmento entre nodos híbridos** | **Fuera del alcance compatible** | No utilizable (necesita VTEP, es decir, VXLAN) |

Con VXLAN, el tráfico entre nodos híbridos lleva la IP del nodo en el encabezado externo, por lo que un firewall en ese segmento no puede ver las IP de los Pods. La elección depende de si también se necesitan las IP de los Pods en ese segmento. La segunda fila, que se mantiene dentro del alcance compatible, basta en la mayoría de los casos. Considere la tercera fila solo si cuenta con soporte comercial de Cilium o experiencia interna en lugar de soporte de AWS.

## Configuración

### Rangos de direcciones

| Rango | Valor | Notas |
|---|---|---|
| VPC de la nube | `10.0.0.0/16` | Nodos y Pods de la nube (VPC CNI) |
| Red de nodos remotos | `172.18.0.0/16` | VPC local simulada (hosts de nodos híbridos) |
| Red de Pods remotos | `172.17.0.0/16` | Grupo de clúster de Cilium, `/25` por nodo |
| Servicio | `172.16.0.0/16` | |

### Valores de Cilium (superposición sobre los valores base)

```yaml
routingMode: native
ipv4NativeRoutingCIDR: "172.17.0.0/16"   # remote pod network
autoDirectNodeRoutes: false              # hosts are in different subnets; the on-prem router forwards
enableIPv4Masquerade: false              # no SNAT
vtep:
  enabled: false                         # no gateway
```

El chart de Cilium no reinicia los agentes cuando cambia el ConfigMap (`rollOutCiliumPods` tiene `false` como valor predeterminado), así que ejecute `kubectl -n kube-system rollout restart ds/cilium` después de cambiar los valores. A continuación, compruebe que `cilium-dbg status` muestre `Routing: Network: Native`. El ConfigMap sigue conteniendo `tunnel-protocol: vxlan`, pero no tuvo efecto: una captura en la NIC del host mostró cero paquetes VXLAN (UDP 8472 y 4789).

### Excepciones de enrutamiento y SNAT

| Ubicación | Configuración | Motivo |
|---|---|---|
| Enrutador local | El bloque de Pods de cada nodo (`/25`) hacia ese nodo | En producción, anuncie las rutas con Cilium BGP Control Plane. La prueba usó rutas estáticas en la tabla de rutas de la VPC local; quedan obsoletas cuando un nodo vuelve a unirse y recibe un bloque de Pods diferente. |
| Tablas de rutas de la nube, TGW | `172.17.0.0/16` hacia las instalaciones locales | El tráfico de retorno llega directamente a las IP de los Pods |
| VPC CNI | `AWS_VPC_K8S_CNI_EXCLUDE_SNAT_CIDRS=172.17.0.0/16,172.18.0.0/16` | Los Pods de la nube también conservan su IP hacia las instalaciones locales. **Sin el rango de nodos (172.18), los servidores locales ven la IP del nodo de la nube.** |
| Grupo de seguridad del clúster | Todo `172.17.0.0/16`, UDP/TCP 53 desde `172.18.0.0/16` | Tráfico de los Pods y DNS de los Pods hostNetwork (que llaman a CoreDNS desde la IP del nodo) |

## Resultados de la matriz de conectividad

Cada comprobación verificó no solo la respuesta HTTP, sino también **la dirección de origen registrada por el servidor**: el registro de acceso de nginx (`$remote_addr`) o, para el servidor fuera de Kubernetes, un receptor `socat` que devuelve la dirección del par. Resultado: 38 PASS, 0 FAIL.

| Segmento | Comprobaciones | Qué se comprobó | Resultado |
|---|---|---|---|
| De Pod a Pod, directo | 7 | Mismo nodo híbrido, entre nodos híbridos, híbrido y nube en ambas direcciones, de nube a nube | El servidor ve como origen la IP del Pod cliente |
| Servicio ClusterIP | 3 | Nodo híbrido a backend híbrido, nodo híbrido a backend de la nube, nube a backend híbrido | kube-proxy reescribe solo el destino; se conserva la IP del Pod de origen |
| DNS | 4 | Nombres de servicio desde dos Pods híbridos y un Pod hostNetwork, un nombre público | Resueltos mediante CoreDNS (nodos de la nube) y el solucionador de VPC |
| API de Kubernetes | 2 | `kubernetes.default.svc/livez`, token de ServiceAccount | 200 y 403 (autenticado, sin concesión de RBAC) |
| Plano de control a nodo híbrido | 3 | Proxy del servidor de API (ruta de webhook), `exec` y `logs`, metrics-server | Las solicitudes del proxy provienen de una ENI administrada por EKS en la VPC de la nube |
| Servidor local fuera de Kubernetes | 2 | Pod híbrido y Pod de la nube a `socat` en un host híbrido | El servidor recibió las IP de los Pods 172.17.x y 10.0.x |
| Internet | 3 | Dos Pods híbridos, un Pod de la nube | Todo sale por la única puerta de enlace NAT de la nube, la única traducción de direcciones en la ruta |
| Política de Cilium | 3 | `fromCIDR: 10.0.0.0/16` en un Pod híbrido | Pod híbrido bloqueado, Pod de la nube permitido, acceso restaurado tras eliminar la política |
| MTU, transferencia masiva | 2 | 32 MiB en ambas direcciones, comparación de sha256 | Coinciden. La MTU del Pod es 9001; el ping DF con paquetes de 8500 bytes funciona |
| Destinos IP de ALB | 1 | Dos Pods híbridos | En buen estado |
| PrivateLink | 8 | Véase más abajo | Todos PASS |

La política `fromCIDR` que funcionó también demuestra que no hay SNAT. Los Pods de la nube usan VPC CNI y no tienen identidad de Cilium, por lo que las políticas solo pueden seleccionarlos mediante un rango de IP, lo cual solo funciona si la IP del Pod llega sin cambios.

La MTU del Pod es 9001 y el límite del TGW es 8500. TCP funcionó porque el TGW limita el MSS. Compruebe por separado la MTU de la ruta para los protocolos sin limitación de MSS, como UDP, y para las rutas de DX o VPN.

### Tres fallos en la primera ejecución

| Síntoma | Causa | Solución |
|---|---|---|
| El Pod hostNetwork no puede resolver nombres de servicio | Los Pods hostNetwork llaman a CoreDNS desde la IP del nodo (172.18.x), y el grupo de seguridad del clúster no tenía una regla para el puerto 53 para ese rango | Permita UDP y TCP 53 desde `172.18.0.0/16` en el grupo de seguridad del clúster |
| El servidor local ve la IP de un nodo de la nube en vez de la de un Pod de la nube | La lista de exclusión de SNAT de VPC CNI incluía el rango de Pods, pero no el rango de nodos locales | Añada `172.18.0.0/16` a `AWS_VPC_K8S_CNI_EXCLUDE_SNAT_CIDRS` |
| `GET /version` anónimo devuelve 401 | EKS 1.36 permite solicitudes anónimas solo a los puntos de conexión de estado | Use `/livez` o `/readyz` para comprobar la conectividad |

## Llamadas a las API de AWS desde Pods locales mediante PrivateLink

Para evitar que los Pods locales accedan a internet cuando llaman a las API de AWS, coloque puntos de conexión de interfaz en la VPC de la nube y acceda a ellos mediante DX o VPN.

```
hybrid Pod (172.17.x)
  -> CoreDNS -> VPC resolver: sts.<region>.amazonaws.com and s3.<region>.amazonaws.com resolve to endpoint ENIs (10.0.x)
  -> TGW (DX/VPN in production), source Pod IP preserved
  -> STS and S3 interface endpoints (2 AZs, private DNS)
```

Los Pods híbridos resuelven los nombres mediante el DNS del clúster (CoreDNS) y, después, mediante el solucionador de VPC, por lo que se aplica directamente el DNS privado de los puntos de conexión. Los servidores locales fuera de Kubernetes necesitan un [punto de conexión entrante de Route 53 Resolver](https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/resolver-forwarding-inbound-queries.html) para obtener las mismas respuestas.

### Componentes

| Componente | Configuración |
|---|---|
| Punto de conexión de interfaz de STS | DNS privado habilitado |
| Punto de conexión de interfaz de S3 | DNS privado habilitado. **En una VPC sin un punto de conexión de puerta de enlace de S3, establezca `DnsOptions.PrivateDnsOnlyForInboundResolverEndpoint: AllResolvers`.** El primer intento sin esta opción falló con «To set PrivateDnsOnlyForInboundResolverEndpoint to true, the VPC must have a Gateway endpoint». |
| Grupo de seguridad del punto de conexión | Solo TCP 443 desde `10.0.0.0/16` (VPC) y `172.17.0.0/16` (Pods híbridos). Se excluye deliberadamente el rango de nodos `172.18.0.0/16` |
| IAM | Proveedor OIDC del clúster, un rol asociado al ServiceAccount (IRSA) |
| Política del bucket | El rol de prueba solo está permitido cuando `aws:SourceVpce` es el punto de conexión de S3 |

No se puede usar un punto de conexión de puerta de enlace de S3 [desde las instalaciones locales](https://docs.aws.amazon.com/AmazonS3/latest/userguide/privatelink-interface-endpoints.html); los Pods locales necesitan el punto de conexión de interfaz.

La política del bucket de abajo bloquea solo al rol de prueba cuando está fuera del punto de conexión. No afecta a otras entidades principales, como los operadores.

```json
{
  "Sid": "TestRoleOnlyThroughEndpoint",
  "Effect": "Deny",
  "Principal": "*",
  "Action": "s3:*",
  "Resource": ["arn:aws:s3:::<bucket>", "arn:aws:s3:::<bucket>/*"],
  "Condition": {
    "StringNotEquals": {"aws:SourceVpce": "<s3-endpoint-id>"},
    "ArnEquals": {"aws:PrincipalArn": "<test-role-arn>"}
  }
}
```

### IRSA y Pod Identity

Con IRSA, el propio Pod llama a STS `AssumeRoleWithWebIdentity` con su token proyectado, por lo que el intercambio del token ya pasa por el punto de conexión de STS. Cree primero el proveedor OIDC del clúster si aún no existe. Al establecer `AWS_STS_REGIONAL_ENDPOINTS=regional` en el `env` del Pod, se hace que el SDK use el nombre regional de STS, que está cubierto por el DNS privado.

EKS Pod Identity necesita [configuración adicional](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-add-ons.html) en los nodos híbridos: `enableCredentialsFile` en la configuración de nodeadm y la configuración del complemento Pod Identity Agent `{"daemonsets":{"hybrid":{"create":true}}}`. El DaemonSet predeterminado del agente en el clúster de prueba excluía los nodos híbridos, así que esta prueba usó IRSA.

### Resultados (los 8 PASS)

| Comprobación | Resultado |
|---|---|
| Resolver `sts`, `s3` y el nombre de host del bucket desde un Pod híbrido | Todos devuelven direcciones ENI de los puntos de conexión (10.0.x) |
| Pod híbrido: `sts get-caller-identity` (IRSA) | Se devuelve el ARN del rol asumido; el intercambio del token usó el punto de conexión de STS |
| Pod híbrido: `PutObject` | Funciona. La política del bucket bloquea este rol fuera del punto de conexión, por lo que la solicitud pasó por él |
| Pod de la nube: `GetObject` del mismo objeto | El mismo contenido |
| ENI de STS:443 desde un Pod y un Pod hostNetwork en el mismo nodo | El Pod (172.17.x) recibe HTTP 302; el Pod hostNetwork (172.18.x) agota el tiempo de espera |
| Mismo rol desde fuera del punto de conexión (estación de trabajo) | Denegado por la condición `aws:SourceVpce` |

El Pod pudo acceder, mientras que el Pod hostNetwork quedó bloqueado, aunque ambos salieron por el mismo nodo. **Los grupos de seguridad del lado de AWS también pueden distinguir los Pods locales mediante el rango de Pods**, lo que constituye la prueba más directa de que no hay SNAT.

## Qué ocurre con DNS cuando se interrumpe el enlace

Se reprodujo una interrupción de DX o VPN durante unos 95 segundos añadiendo rutas de descarte (`/17` para los rangos de nodos y Pods locales) a la tabla de rutas del TGW. El cambio de ruta tardó unos 17 segundos en surtir efecto. En cada nodo híbrido, un Pod de sondeo resolvía cada segundo el nombre de un servicio local y el de un servicio de la nube, y después llamaba al servicio local por nombre y por ClusterIP. Durante la interrupción, los nodos híbridos pasaron a estar `NotReady` mientras sus Pods seguían ejecutándose (los registros del sondeo no tienen interrupciones); en la primera ejecución volvieron a estar `Ready` unos 23 segundos después de que se restableciera el enlace.

| Configuración | Resolución de nombres en los Pods híbridos durante la interrupción | Llamadas al servicio local | Notas |
|---|---|---|---|
| Predeterminada: ambas réplicas de CoreDNS en nodos de la nube | **Todas las consultas fallan** (fallaron de 26 de 43 a 44 muestras) | ClusterIP devuelve 200; por nombre falla | El tráfico dentro de las instalaciones locales sigue funcionando, pero los nombres no |
| Etiqueta de zona + 3 réplicas + `PreferSameZone` (difiere del ejemplo de la documentación) | Falla aproximadamente la mitad (de 38 de 44 en 76 a 80 muestras) | Las llamadas por nombre fallan de forma intermitente | Cilium ignora las sugerencias y sigue balanceando al CoreDNS inaccesible de la nube |
| Etiqueta de zona + 4 réplicas + **`PreferClose`** + distribución por zona obligatoria + reinicio de Cilium | **0 fallos** (todas las muestras, entre 96 y 97) | Tanto por nombre como por ClusterIP, 200 | Los Pods de la nube resuelven correctamente; solo fallan sus llamadas a las instalaciones locales, como se esperaba |

Las causas encontradas en cada paso:

1. **Use el valor de la documentación de AWS, `PreferClose`. Cilium no actuó según `PreferSameZone`.** El ejemplo de AWS usa `trafficDistribution: PreferClose`. La prueba usó el nombre más reciente, `PreferSameZone`, porque `PreferClose` pasó a ser un alias obsoleto en Kubernetes 1.35, lo que provocó que fallara la mitad de las consultas. En los nodos híbridos, el balanceo de carga de ClusterIP lo realiza Cilium BPF, no kube-proxy, incluso con `kubeProxyReplacement: false`. EndpointSlice tenía sugerencias de zona, pero `cilium-dbg bpf lb list` seguía mostrando los tres backends de CoreDNS. Con `trafficDistribution: PreferClose`, solo quedaban los dos backends locales. Las sugerencias de EndpointSlice parecen iguales para ambos valores, así que compruebe la lista de backends de Cilium en un nodo híbrido.
2. **Establezca la etiqueta de zona al unirse.** La prueba añadió la etiqueta más tarde y después reinició Cilium con `kubectl -n kube-system rollout restart ds/cilium`; no se comprobó si surte efecto sin reiniciar. Unirse con kubelet `--node-labels=topology.kubernetes.io/zone=<name>` en la configuración de nodeadm evita la duda.
3. **Las zonas de disponibilidad de la nube sin CoreDNS también son un problema.** Un Pod de la nube cuya zona no tiene CoreDNS se balancea entre todos los backends, y las consultas que llegan al CoreDNS local fallan durante una interrupción. Ejecute una réplica por zona de disponibilidad de la nube y al menos una en las instalaciones locales.
4. **La anti-afinidad preferida no garantizó la ubicación.** Después de reiniciar CoreDNS, las réplicas locales se redujeron una vez a una. `topologySpreadConstraints` con `whenUnsatisfiable: DoNotSchedule` garantiza al menos una réplica por zona.
5. **CoreDNS en nodos híbridos omite PrivateLink.** Reenvía las consultas al solucionador del nodo (DNS local), por lo que `sts` y `s3` se resolvieron en direcciones públicas. Las llamadas siguen funcionando a través de NAT y parecen estar en buen estado, pero las solicitudes de S3 fueron denegadas por la política del bucket `aws:SourceVpce` y fallaron cuatro comprobaciones de la matriz. La solución fue un punto de conexión entrante de Route 53 Resolver en la VPC de la nube, además de un bloque `amazonaws.com` en CoreDNS. En una red real, un reenviador condicional en los servidores DNS locales hace lo mismo.

Valores finales de configuración del complemento CoreDNS (`aws eks update-addon --configuration-values`):

```json
{
  "replicaCount": 4,
  "trafficDistribution": "PreferClose",
  "topologySpreadConstraints": [{
    "maxSkew": 1, "topologyKey": "topology.kubernetes.io/zone", "whenUnsatisfiable": "DoNotSchedule",
    "labelSelector": {"matchLabels": {"k8s-app": "kube-dns"}}
  }],
  "corefile": "...default .:53 block...\namazonaws.com:53 {\n    errors\n    cache 30\n    forward . <inbound endpoint IP 1> <inbound endpoint IP 2>\n}"
}
```

El valor `corefile` reemplaza todo el Corefile, así que debe incluir el bloque predeterminado `.:53`. Después del cambio de Corefile, una réplica de CoreDNS en un nodo híbrido tardó en recoger el ConfigMap y durante un tiempo respondió con la configuración anterior; `rollout restart deploy/coredns` lo solucionó. El grupo de seguridad del punto de conexión entrante abre el puerto 53 solo al rango de la VPC y al rango de los Pods híbridos. Durante una interrupción, el punto de conexión entrante también es inaccesible, por lo que no se resuelven los nombres de las API de AWS, aunque en ese momento los propios puntos de conexión tampoco son accesibles.

## Aspectos que deben vigilarse en las operaciones

- **Ubicación de CoreDNS**: AWS recomienda al menos una réplica de CoreDNS en nodos híbridos y otra en nodos de la nube en un clúster de modo mixto ([Configurar las réplicas de CoreDNS](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-webhooks.html)). Como se midió anteriormente, para que esto ayude durante una interrupción, la etiqueta de zona, la distribución por zona, `trafficDistribution` y `loadBalancer.serviceTopology: true` de Cilium deben estar configurados correctamente. Interrumpa el enlace de verdad para verificarlo después de hacer cambios.
- **Webhooks y rutas del plano de control**: Las solicitudes del proxy del servidor de API provenían de una ENI administrada por EKS en la VPC de la nube. Para ejecutar webhooks en nodos híbridos, los CIDR de los Pods deben ser enrutables y el firewall local debe permitir el rango de la VPC que contiene esas ENI.
- **Desfase de rutas estáticas**: Un nodo que vuelve a unirse puede recibir un bloque de Pods diferente. Sin BGP, se necesita un paso que reconcilie las rutas después de cada incorporación.
- **Salida a internet**: Esta configuración enviaba la ruta predeterminada local a la nube, así que todo salía por una única puerta de enlace NAT. Si las instalaciones locales usan su propia ruta a internet, la traducción NAT y la política del firewall de esa ruta deben conocer el rango de Pods.
- **Costo**: Los puntos de conexión de interfaz se facturan por hora y por zona de disponibilidad, y también por GB procesado.

## Cuestionario

* [Cuestionario sobre conectividad de Pods sin SNAT y PrivateLink](../quizzes/eks-hybrid-nodes/12-connectivity-validation-quiz.md)

## Referencias

* [Configurar CNI para nodos híbridos](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-cni.html): modo de red compatible, enmascaramiento, recomendación de BGP
* [Preparar la red para nodos híbridos](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-networking.html)
* [Configurar webhooks para nodos híbridos](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-webhooks.html): ubicación de las réplicas de CoreDNS
* [Configurar complementos para nodos híbridos](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-add-ons.html): Pod Identity Agent
* [Prácticas recomendadas para mantener la estabilidad durante las desconexiones de red](https://docs.aws.amazon.com/eks/latest/best-practices/hybrid-nodes-network-disconnection-best-practices.html)
* [AWS PrivateLink para Amazon S3](https://docs.aws.amazon.com/AmazonS3/latest/userguide/privatelink-interface-endpoints.html)
* [Acceder a servicios de AWS mediante AWS PrivateLink](https://docs.aws.amazon.com/vpc/latest/privatelink/privatelink-access-aws-services.html)
* [Hybrid Nodes Gateway](10-hybrid-nodes-gateway.md), [Configuración de red](02-network-configuration.md), [Revisión de seguridad de la separación de red](11-network-separation-security.md)
