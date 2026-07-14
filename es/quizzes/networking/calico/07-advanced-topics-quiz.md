# Cuestionario de temas avanzados

> **Documento relacionado**: [Temas avanzados](../../../networking/calico/07-advanced-topics.md)
> **Última actualización**: February 22, 2026

## Cuestionario

1. En el IPAM basado en bloques de Calico, ¿cuántas direcciones IP proporciona un bloque CIDR /26?
   - A) 32 IPs
   - B) 64 IPs
   - C) 128 IPs
   - D) 256 IPs

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) 64 IPs**

**Explicación:**
Un bloque CIDR /26 proporciona 64 direcciones IP (2^(32-26) = 2^6 = 64). Calico asigna bloques de IP de tamaño configurable a los Nodes y, después, asigna IPs individuales desde estos bloques a los Pods. El tamaño de bloque predeterminado es /26, que equilibra la eficiencia con la utilización de IP.

</details>

2. ¿Qué es la afinidad de bloques IP en el IPAM de Calico?
   - A) Los Pods con la misma etiqueta siempre obtienen IPs del mismo bloque
   - B) Los Nodes reclaman y usan preferentemente bloques IP específicos
   - C) A los Services se les asignan IPs cercanas a sus endpoints
   - D) Las direcciones IP se agrupan por zona de disponibilidad

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Los Nodes reclaman y usan preferentemente bloques IP específicos**

**Explicación:**
La afinidad de bloques IP significa que, cuando un Node necesita asignar IPs de Pod, reclama uno o más bloques IP y asigna preferentemente desde esos bloques. Esto mejora la eficiencia de enrutamiento porque todos los Pods de un Node normalmente comparten el mismo prefijo IP, lo que permite la agregación de rutas.

</details>

3. ¿Cómo se activa el cifrado WireGuard en Calico?
   - A) Instalando un operador WireGuard independiente
   - B) Estableciendo wireguardEnabled: true en FelixConfiguration
   - C) Aplicando una WireGuard NetworkPolicy
   - D) Habilitándolo en los flags del servidor de la API de Kubernetes

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Estableciendo wireguardEnabled: true en FelixConfiguration**

**Explicación:**
El cifrado WireGuard se habilita estableciendo `wireguardEnabled: true` en el recurso FelixConfiguration. Calico administra automáticamente la generación y distribución de claves de WireGuard entre los Nodes, creando túneles cifrados para el tráfico de Pod a Pod entre Nodes.

</details>

4. ¿Cuál es una ventaja clave de WireGuard sobre IPsec para cifrar el tráfico de Pod?
   - A) WireGuard admite más algoritmos de cifrado
   - B) WireGuard tiene una configuración más sencilla y menor sobrecarga de CPU
   - C) WireGuard funciona sin soporte del kernel
   - D) WireGuard proporciona mejor compresión

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) WireGuard tiene una configuración más sencilla y menor sobrecarga de CPU**

**Explicación:**
WireGuard ofrece una configuración más sencilla con menos opciones (lo que reduce el riesgo de configuración incorrecta) y, normalmente, menor sobrecarga de CPU en comparación con IPsec. Utiliza primitivas criptográficas modernas y tiene una base de código más pequeña, lo que facilita su auditoría y mantenimiento.

</details>

5. ¿Cuál es el caso de uso principal de la funcionalidad Egress Gateway de Calico?
   - A) Equilibrar la carga del tráfico de ingress hacia los Services
   - B) Proporcionar IPs de origen coherentes para Pods que acceden a Services externos
   - C) Almacenar en caché respuestas DNS para una resolución más rápida
   - D) Limitar la tasa de llamadas API salientes

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Proporcionar IPs de origen coherentes para Pods que acceden a Services externos**

**Explicación:**
Egress Gateway permite que los Pods accedan a Services externos usando una dirección IP de origen coherente y predecible. Esto es esencial cuando los Services externos usan listas de permitidos basadas en IP, ya que garantiza que el tráfico de Pods específicos siempre parezca provenir de IPs de gateway conocidas.

</details>

6. ¿Qué capacidad proporciona la federación multi-cluster de Calico?
   - A) Failover automático entre clusters
   - B) NetworkPolicies compartidas y descubrimiento de Services entre clusters
   - C) Logging centralizado para todos los clusters
   - D) Facturación unificada entre clusters

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) NetworkPolicies compartidas y descubrimiento de Services entre clusters**

**Explicación:**
La federación multi-cluster permite a Calico compartir NetworkPolicies, habilitar el descubrimiento de Services entre clusters y proporcionar redes coherentes en múltiples clusters de Kubernetes. Esto permite que las cargas de trabajo en diferentes clusters se comuniquen de forma segura mediante políticas unificadas.

</details>

7. ¿Qué afirmación sobre el soporte de Windows de Calico es correcta?
   - A) Los Nodes de Windows requieren un plugin CNI diferente
   - B) Calico admite Nodes de Windows con algunas limitaciones de funcionalidades
   - C) El soporte de Windows solo está disponible en Calico Enterprise
   - D) Los Nodes de Windows no pueden participar en el peering BGP

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Calico admite Nodes de Windows con algunas limitaciones de funcionalidades**

**Explicación:**
Calico admite Nodes de Windows en clusters de Kubernetes, lo que habilita entornos mixtos de Linux/Windows. Sin embargo, algunas funcionalidades como el dataplane eBPF no están disponibles en Windows debido a diferencias del sistema operativo. El soporte de Windows cubre las funciones básicas de red y la aplicación de NetworkPolicy.

</details>

8. ¿Cuál es una diferencia clave entre Calico Enterprise y Calico Open Source?
   - A) Enterprise usa una tecnología de dataplane diferente
   - B) Enterprise incluye funcionalidades adicionales de seguridad, cumplimiento y observabilidad
   - C) Enterprise solo funciona con distribuciones específicas de Kubernetes
   - D) Enterprise no admite BGP

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Enterprise incluye funcionalidades adicionales de seguridad, cumplimiento y observabilidad**

**Explicación:**
Calico Enterprise se basa en el proyecto open source y agrega funcionalidades como niveles jerárquicos de políticas, visualización de flujos, informes de cumplimiento, defensa contra amenazas y soporte empresarial. El dataplane de red central es el mismo en ambas versiones.

</details>

9. ¿Cuál es la fórmula de dimensionamiento de Typha para grandes deployments de Calico?
   - A) 1 Typha por cada 100 Nodes
   - B) 1 Typha por cada 500 Nodes, mínimo 3 para HA
   - C) Réplicas de Typha = Nodes / 200, recomendado para clusters de más de 1000 Nodes
   - D) Fijo en 5 réplicas independientemente del tamaño del cluster

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Réplicas de Typha = Nodes / 200, recomendado para clusters de más de 1000 Nodes**

**Explicación:**
Para clusters con más de 1000 Nodes, Typha se vuelve esencial para la escalabilidad. La fórmula general de dimensionamiento es aproximadamente 1 réplica de Typha por cada 200 Nodes, con un mínimo de 3 réplicas para alta disponibilidad. Typha distribuye las actualizaciones del datastore a las instancias de Felix, lo que reduce la carga del servidor de la API.

</details>

10. ¿Qué se requiere para que Calico admita redes IPv6 y dual-stack?
    - A) Una instalación independiente específica para IPv6
    - B) Configurar IPPools para los rangos de direcciones IPv4 e IPv6
    - C) Usar solo el dataplane eBPF
    - D) Deshabilitar la aplicación de NetworkPolicy

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Configurar IPPools para los rangos de direcciones IPv4 e IPv6**

**Explicación:**
El soporte dual-stack en Calico requiere configurar IPPools para los rangos CIDR de IPv4 e IPv6. Los Pods pueden entonces recibir direcciones de ambos pools. El cluster también debe tener dual-stack habilitado a nivel de Kubernetes, y la infraestructura subyacente debe admitir IPv6.

</details>

11. ¿Cómo puedes detectar el agotamiento de direcciones IP en el IPAM de Calico?
    - A) Revisando los logs de kube-apiserver
    - B) Usando calicoctl ipam show para ver el estado de asignación
    - C) Monitorizando el uso de memoria de los Nodes
    - D) Revisando los conteos de reinicios de Pods

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Usando calicoctl ipam show para ver el estado de asignación**

**Explicación:**
El comando `calicoctl ipam show` muestra el estado de asignación de IPAM, incluidos los IPs totales, los IPs asignados y los IPs disponibles en todos los pools y bloques. El flag `--show-blocks` proporciona información detallada de asignación de bloques por Node, lo que ayuda a identificar problemas de agotamiento.

</details>

12. ¿Cuándo deberías elegir etcd como datastore de Calico en lugar de la API de Kubernetes?
    - A) Para clusters de menos de 100 Nodes
    - B) Al ejecutarlo en Services de Kubernetes administrados
    - C) Para clusters muy grandes o deployments que no son de Kubernetes
    - D) Al usar el dataplane eBPF

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Para clusters muy grandes o deployments que no son de Kubernetes**

**Explicación:**
El datastore etcd se recomienda para clusters muy grandes donde la carga del servidor de la API de Kubernetes es un problema, o para deployments que no son de Kubernetes (bare metal, VMs). Para la mayoría de los deployments de Kubernetes, el datastore de Kubernetes es más sencillo, ya que no requiere administrar un cluster etcd independiente.

</details>
