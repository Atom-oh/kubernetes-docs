# Cuestionario de temas avanzados

> **Documento relacionado**: [Temas avanzados](../../../networking/calico/07-advanced-topics.md)
> **Última actualización**: 12 de septiembre de 2026

## Cuestionario

1. En el IPAM de Calico basado en bloques, ¿cuántas direcciones IP proporciona un bloque CIDR /26?
   - A) 32 direcciones IP
   - B) 64 direcciones IP
   - C) 128 direcciones IP
   - D) 256 direcciones IP

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) 64 direcciones IP**

**Explicación:**
Un bloque IPv4 /26 contiene 64 direcciones. Esto no significa siempre que haya 64 direcciones utilizables para Pods: Calico para Windows reserva cuatro por cada bloque que posee. El valor predeterminado para IPv6 es /122, que también contiene 64 direcciones. Define `blockSize` al crear un pool; no es un ajuste que se pueda cambiar directamente después.

</details>

2. ¿Qué es la afinidad de bloques IP en el IPAM de Calico?
   - A) Los Pods con la misma etiqueta siempre reciben direcciones IP del mismo bloque
   - B) Los nodos reclaman bloques IP específicos y los usan de forma preferente
   - C) Los Services reciben direcciones IP cercanas a sus endpoints
   - D) Las direcciones IP se agrupan por zona de disponibilidad

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Los nodos reclaman bloques IP específicos y los usan de forma preferente**

**Explicación:**
Los nodos asignan direcciones preferentemente desde sus bloques afiliados, según la selección y los límites del pool. Un nodo puede tener varios bloques, y el préstamo permitido puede crear rutas más específicas. La afinidad de bloques no equivale a `Node.spec.podCIDR` ni garantiza que todos los Pods de un nodo compartan el mismo prefijo.

</details>

3. ¿Cómo se activa el cifrado WireGuard en Calico?
   - A) Instalando un operador WireGuard independiente
   - B) Estableciendo `wireguardEnabled: true` en FelixConfiguration
   - C) Aplicando una NetworkPolicy de WireGuard
   - D) Habilitándolo en los flags del servidor de la API de Kubernetes

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Estableciendo `wireguardEnabled: true` en FelixConfiguration**

**Explicación:**
`wireguardEnabled` habilita la ruta IPv4 compatible; `wireguardEnabledV6` se configura por separado. Ambos peers necesitan compatibilidad con la red y el kernel. Calico administra las claves de los nodos y publica las claves públicas. El tráfico entre Pods del mismo nodo y el tráfico de peers no compatibles no se cifra automáticamente mediante el túnel entre nodos.

</details>

4. ¿Qué afirmación describe el diseño de WireGuard sin atribuirle un resultado de rendimiento universal?
   - A) WireGuard admite más algoritmos de cifrado
   - B) WireGuard usa un diseño criptográfico y una configuración de claves deliberadamente limitados
   - C) Calico WireGuard no requiere requisitos previos del nodo ni del entorno de ejecución
   - D) WireGuard ofrece mejor compresión

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) WireGuard usa un diseño criptográfico y una configuración de claves deliberadamente limitados**

**Explicación:**
WireGuard limita deliberadamente las opciones criptográficas. El costo de CPU y las comparaciones de caudal, roaming y descarga de trabajo dependen de la implementación y la carga. Los recuentos de líneas de código sin una versión definida y los intervalos de rendimiento no verificados del capítulo no constituyen una clasificación universal de seguridad o velocidad.

</details>

5. ¿Cuál es el caso de uso principal de la función Egress Gateway documentada de Calico Enterprise?
   - A) Balancear el tráfico de entrada hacia los Services
   - B) Proporcionar direcciones IP de origen coherentes para los Pods que acceden a servicios externos
   - C) Almacenar en caché respuestas DNS para acelerar la resolución
   - D) Limitar la tasa de llamadas API salientes

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Proporcionar direcciones IP de origen coherentes para los Pods que acceden a servicios externos**

**Explicación:**
Un Pod que actúa como gateway de tránsito realiza SNAT para los clientes seleccionados y expone un conjunto controlado de direcciones de origen. Las direcciones observadas dependen del pool, del NAT ascendente y de la disponibilidad. NetworkPolicy Allow y BGP `serviceExternalIPs` no crean ese comportamiento de enrutamiento/SNAT. Permitir direcciones de origen en una lista de IP no demuestra por completo el cumplimiento normativo ni la autorización de la aplicación.

</details>

6. ¿Qué ofrece la función actual de federación de Calico Enterprise?
   - A) Replicación y conmutación por error automáticas de bases de datos de aplicaciones
   - B) Identidad de endpoints remotos y descubrimiento de Services seleccionados, mientras las políticas se aplican localmente
   - C) Registro centralizado para todos los clústeres
   - D) Facturación unificada entre clústeres

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Identidad de endpoints remotos y descubrimiento de Services seleccionados, mientras las políticas se aplican localmente**

**Explicación:**
La identidad federada de endpoints incorpora información de endpoints remotos al cálculo de políticas local; no copia las políticas remotas a los endpoints locales. Un controlador independiente de Services federados consulta las API remotas de Kubernetes. Se necesitan rutas de Pods enrutables que preserven el origen, además de las credenciales y la configuración del controlador; Typha no es un controlador compartido de Federation.

</details>

7. ¿Qué afirmación sobre la compatibilidad de Calico con Windows es correcta?
   - A) Los nodos Windows requieren un plugin CNI diferente
   - B) Calico admite nodos Windows con algunas limitaciones de funciones
   - C) La compatibilidad con Windows solo está disponible en Calico Enterprise
   - D) Los nodos Windows no pueden participar en peering BGP

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Calico admite nodos Windows con algunas limitaciones de funciones**

**Explicación:**
Calico para Windows usa HNS/HostProcess y tiene límites de plataforma y versión. Admite VXLAN IPv4 o BGP sin overlay en los casos compatibles, pero la guía revisada de Windows excluye IPv6/dual stack, eBPF, WireGuard, políticas HostEndpoint y anuncios de Services. Haz coincidir las versiones del sistema operativo y del contenedor con el perfil real del proveedor.

</details>

8. ¿Cuál es una diferencia clave entre Calico Enterprise y Calico Open Source?
   - A) Enterprise usa una tecnología de dataplane diferente
   - B) Enterprise incluye funciones adicionales de seguridad, cumplimiento y observabilidad
   - C) Enterprise solo funciona con distribuciones específicas de Kubernetes
   - D) Enterprise no admite BGP

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Enterprise incluye funciones adicionales de seguridad, cumplimiento y observabilidad**

**Explicación:**
Open Source 3.32 ya incluye niveles de política, visibilidad de flujos mediante Whisker, políticas por etapas y políticas HTTP a través de Istio/Dikastes. Las ediciones comerciales agregan funciones específicas del producto, como políticas de dominio, gateways de salida, identidad y Services remotos, e informes. Las funciones y condiciones de soporte dependen del producto y la versión seleccionados.

</details>

9. ¿Qué cantidad de réplicas de Typha calcula Tigera Operator 1.42.6 para 1.000 nodos contabilizados?
   - A) 5 réplicas
   - B) 3 réplicas
   - C) 7 réplicas
   - D) 10 réplicas

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) 7 réplicas**

**Explicación:**
Para N>4, el operador revisado usa `max(3, floor(N/200)+2)`, lo que da 7 con 1.000 nodos. N<=2 da 1 y N<=4 da 2. Este es un objetivo de implementación sujeto a condiciones de recuento y ubicación de nodos, no una garantía de capacidad medida de «200 nodos por Typha».

</details>

10. ¿Qué requisito de pools se aplica a una implementación dual stack que usa Calico-IPAM?
    - A) Una instalación independiente específica para IPv6
    - B) Configurar IPPools para los rangos de direcciones IPv4 e IPv6
    - C) Usar únicamente el dataplane eBPF
    - D) Deshabilitar la aplicación de políticas de red

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Configurar IPPools para los rangos de direcciones IPv4 e IPv6**

**Explicación:**
Calico-IPAM dual stack usa pools IPv4 e IPv6; Kubernetes, CNI, el direccionamiento de los nodos y la red subyacente también deben admitir ambas familias. El modo solo IPv6 no requiere un pool IPv4. `Felix ipv6Support` es un booleano; añadir ese flag o crear pools, por sí solos, no cambia la configuración de familias IP de un clúster existente.

</details>

11. ¿Cómo se puede detectar el agotamiento de direcciones IP en el IPAM de Calico?
    - A) Revisando los logs de kube-apiserver
    - B) Usando `calicoctl ipam show` para ver el estado de las asignaciones
    - C) Supervisando el uso de memoria de los nodos
    - D) Revisando la cantidad de reinicios de Pods

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Usando `calicoctl ipam show` para ver el estado de las asignaciones**

**Explicación:**
`ipam show` informa el uso de las asignaciones; `--show-blocks` añade detalles de los bloques. Usa BlockAffinity para asociar los bloques a los nodos y considera los pools elegibles, las reservas y los límites de afinidad/host. Que haya direcciones libres en otra parte no garantiza que se pueda asignar una. Limpia únicamente asignaciones obsoletas verificadas con un informe de recuperación reciente; no uses una IP de ejemplo copiada.

</details>

12. ¿Cuál es una razón para considerar el perfil de Calico con etcd directo?
    - A) Para clústeres de menos de 100 nodos
    - B) Al ejecutarlo en servicios de Kubernetes administrados
    - C) Para una implementación compatible que no sea de Kubernetes y que tenga un plan explícito de operación y recuperación de etcd
    - D) Al usar el dataplane eBPF

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Para una implementación compatible que no sea de Kubernetes y que tenga un plan explícito de operación y recuperación de etcd**

**Explicación:**
etcd directo puede ser apropiado para una implementación compatible y diseñada por separado. El datastore de Kubernetes es más sencillo para muchas instalaciones de Kubernetes y es obligatorio para el dataplane eBPF actual. La decisión no se determina por un umbral fijo de 5.000 nodos ni por una comparación universal de velocidad de lectura.

</details>
