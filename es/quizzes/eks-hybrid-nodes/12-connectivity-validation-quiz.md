# Cuestionario sobre conectividad de Pods sin SNAT y PrivateLink

> **Última actualización**: 19 de octubre de 2026

[Guía de estudio: Validación de la conectividad de Pods sin SNAT y PrivateLink](../../eks-hybrid-nodes/12-connectivity-validation.md)

1. ¿Qué modo de red de Cilium admite AWS para EKS Hybrid Nodes?
   - A) Solo enrutamiento nativo
   - B) Solo encapsulación VXLAN
   - C) Tanto VXLAN como enrutamiento nativo

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Solo encapsulación VXLAN**

**Explicación:**
La tabla de capacidades admitidas de Configure CNI for hybrid nodes indica la encapsulación VXLAN como modo de red. El enrutamiento nativo queda fuera del alcance de lo admitido, y Hybrid Nodes Gateway necesita VTEP (VXLAN), por lo que no se puede usar con el enrutamiento nativo.

</details>

2. Mantienes VXLAN, deshabilitas el enmascaramiento y anuncias los CIDR de los Pods con Cilium BGP. ¿En qué segmento sigue sin poder ver un firewall las IP de los Pods?
   - A) Entre los Pods de la nube y los Pods locales
   - B) Hacia los servidores locales fuera de Kubernetes
   - C) Entre los nodos híbridos

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Entre los nodos híbridos**

**Explicación:**
El tráfico entre nodos híbridos se encapsula en VXLAN y la cabecera externa lleva la IP del nodo. El tráfico que sale del clúster conserva la IP del Pod cuando el enmascaramiento está desactivado.

</details>

3. Después de cambiar al enrutamiento nativo, un servidor local ve la IP de un nodo de la nube cuando un Pod de la nube se conecta a él. ¿Qué compruebas primero?
   - A) Si `AWS_VPC_K8S_CNI_EXCLUDE_SNAT_CIDRS` de VPC CNI incluye el rango de nodos locales
   - B) El valor de `enableIPv4Masquerade` de Cilium
   - C) La ruta predeterminada de la tabla de rutas de TGW

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A) Si `AWS_VPC_K8S_CNI_EXCLUDE_SNAT_CIDRS` de VPC CNI incluye el rango de nodos locales**

**Explicación:**
VPC CNI, no Cilium, realiza el SNAT de los Pods de la nube. Si la lista de exclusión contiene únicamente el rango de Pods (172.17.0.0/16) y no el rango de nodos locales (172.18.0.0/16), el tráfico dirigido a los servidores locales se traduce a la IP del nodo.

</details>

4. Solo los Pods hostNetwork no pueden resolver los nombres de Service del clúster; los Pods híbridos normales sí. ¿Cuál es la causa más probable?
   - A) CoreDNS no está en los nodos híbridos
   - B) Los Pods hostNetwork llaman a CoreDNS desde la IP del nodo, y el SG del clúster no permite el puerto 53 desde el rango de nodos
   - C) Los Pods hostNetwork no pueden usar DNS

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Los Pods hostNetwork llaman a CoreDNS desde la IP del nodo, y el SG del clúster no permite el puerto 53 desde el rango de nodos**

**Explicación:**
Los Pods normales salen con su IP de Pod (172.17.x); los Pods hostNetwork salen con la IP del nodo (172.18.x). Permite UDP y TCP 53 desde `172.18.0.0/16` en el SG del clúster. También se necesita `dnsPolicy: ClusterFirstWithHostNet`.

</details>

5. Los Pods locales deben poder llegar a S3 por una ruta privada. ¿Qué afirmación es correcta?
   - A) Un endpoint de gateway de S3 también funciona desde las instalaciones locales.
   - B) Se necesita un endpoint de interfaz de S3; sin un endpoint de gateway, la prueba tuvo que establecer `DnsOptions` en `AllResolvers`.
   - C) S3 no admite PrivateLink.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Se necesita un endpoint de interfaz de S3; sin un endpoint de gateway, la prueba tuvo que establecer `DnsOptions` en `AllResolvers`.**

**Explicación:**
Los endpoints de gateway no se pueden usar desde las instalaciones locales. En la prueba, la primera creación falló sin `PrivateDnsOnlyForInboundResolverEndpoint` y mostró un error que indicaba que la VPC debía tener un endpoint de gateway.

</details>

6. El SG del endpoint permite TCP 443 únicamente desde `172.17.0.0/16` (el rango de Pods). ¿Qué ocurre cuando un Pod normal y un Pod hostNetwork del mismo nodo híbrido se conectan al endpoint de STS?
   - A) Ambos se conectan correctamente.
   - B) Ambos fallan.
   - C) El Pod normal se conecta correctamente y el Pod hostNetwork agota el tiempo de espera.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) El Pod normal se conecta correctamente y el Pod hostNetwork agota el tiempo de espera.**

**Explicación:**
Sin SNAT, el origen del Pod normal es su IP de Pod y el del Pod hostNetwork es la IP del nodo (172.18.x). Por lo tanto, los grupos de seguridad del lado de AWS pueden distinguir los Pods locales por el rango de Pods.

</details>

7. En la prueba con un clúster de modo mixto Kubernetes 1.36 y Cilium 1.18, ¿qué ajuste del Service kube-dns mantuvo a los Pods híbridos en el CoreDNS local durante una interrupción del enlace?
   - A) `trafficDistribution: PreferClose`
   - B) `externalTrafficPolicy: Local`
   - C) `sessionAffinity: ClientIP`

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A) `trafficDistribution: PreferClose`**

**Explicación:**
Cilium BPF realiza el balanceo de carga de ClusterIP en los nodos híbridos, y la versión probada, Cilium 1.18.13, ignoraba `PreferSameZone`. El ejemplo de la documentación de AWS también usa `PreferClose`. Es un alias obsoleto desde Kubernetes 1.35, pero fue el único valor que funcionó en este caso. También se requieren una etiqueta de zona establecida al unirse, CoreDNS en cada zona y `loadBalancer.serviceTopology: true` de Cilium.

</details>
