# Parte 10: Cuestionario de análisis profundo de IPAM

> **Cilium 1.20.2 (estable, 2026-09-16) · 2026-10-15**. Los elementos marcados [versión preliminar 1.21] provienen de v1.21.0-pre.3.

1. **Una operación CNI ADD asigna una IP al Pod mediante `POST /ipam`, pero el plugin CNI falla antes de crear el endpoint. ¿Cuándo libera el agente esa IP, si no hay ningún reinicio?**
   - A) Cuando vence el temporizador de expiración de 10 minutos establecido durante la asignación
   - B) Solo cuando el agente se reinicia y restaura los endpoints
   - C) Inmediatamente, porque se cerró la conexión REST
   - D) Después de 180 segundos, el valor predeterminado de `--excess-ip-release-delay`

   <details>
   <summary>Mostrar respuesta</summary>

   **Respuesta: A) Cuando vence el temporizador de expiración de 10 minutos establecido durante la asignación**

   **Explicación:**
   El plugin CNI solicita la asignación con la marca de expiración activada, así que el agente inicia un temporizador de 10 minutos (`defaults.IPAMExpiration`). La creación del endpoint detiene el temporizador; si nunca sucede, el temporizador libera la IP. El valor de 180 segundos corresponde a la liberación de IP excedentes de ENI en el operador.

   </details>

2. **Con los valores predeterminados de Helm 1.20.2 para cluster-pool (`10.0.0.0/8`, tamaño de máscara IPv4 24), ¿cuántos nodos pueden recibir un PodCIDR de ese CIDR y cuántas direcciones contiene el bloque de cada nodo?**
   - A) 16,384 nodos, 1,024 direcciones cada uno
   - B) 256 nodos, 65,536 direcciones cada uno
   - C) 65,536 nodos, 256 direcciones cada uno
   - D) 65,536 nodos, 254 direcciones utilizables según la definición de la máscara

   <details>
   <summary>Mostrar respuesta</summary>

   **Respuesta: C) 65,536 nodos, 256 direcciones cada uno**

   **Explicación:**
   La cantidad de nodos por CIDR del pool es `2^(nodeMask - poolMask) = 2^(24 - 8) = 65,536`, y cada bloque contiene `2^(32 - 24) = 256` direcciones. Las IP utilizables para Pods son menos porque se apartan las direcciones de red/difusión y las direcciones de router, health e ingress.

   </details>

3. **En el asignador cluster-pool IPv6 de 1.20.2, ¿qué limita la diferencia entre la longitud del prefijo del pool y la máscara del nodo?**
   - A) La diferencia debe ser de al menos 64 bits para que cada nodo reciba un /64, independientemente del tamaño del pool
   - B) La diferencia no puede superar 16 bits (`clusterSubnetMaxDiff`), porque el asignador usa un mapa de bits sin comprimir
   - C) No hay límite, solo la máscara del nodo no puede superar /128, ya que el mapa de bits está comprimido
   - D) La diferencia debe ser exactamente 8 bits, como el valor predeterminado de IPv4

   <details>
   <summary>Mostrar respuesta</summary>

   **Respuesta: B) La diferencia no puede superar 16 bits (`clusterSubnetMaxDiff`), porque el asignador usa un mapa de bits sin comprimir**

   **Explicación:**
   `pkg/ipam/cidrset` rechaza una máscara IPv6 de nodo que supere en más de 16 bits el prefijo del pool (`ErrCIDRSetSubNetTooBig`). IPv4 solo requiere que la máscara del nodo no supere 32. Los valores predeterminados de Helm `fd00::/104` con `/120` quedan justo en el límite de 16 bits.

   </details>

4. **En IPAM de varios pools, ¿qué orden usa Cilium para elegir el pool de un Pod nuevo?**
   - A) Selectores CiliumPodIPPool, luego anotación del Pod, luego anotación del espacio de nombres y después el pool `default`, salvo que se configure `require-pool-match`
   - B) Siempre el pool `default`; las anotaciones y los selectores solo afectan masquerading y LB IPAM
   - C) Anotación del espacio de nombres, luego anotación del Pod y después `default`; los selectores CiliumPodIPPool solo se usan para LB IPAM
   - D) Anotación del Pod (`ipv4-pool`/`ipv6-pool` antes de `ip-pool`), luego anotación del espacio de nombres, después selectores CiliumPodIPPool y, por último, `default`, salvo que se configure `require-pool-match`

   <details>
   <summary>Mostrar respuesta</summary>

   **Respuesta: D) Anotación del Pod (`ipv4-pool`/`ipv6-pool` antes de `ip-pool`), luego anotación del espacio de nombres, después selectores CiliumPodIPPool y, por último, `default`, salvo que se configure `require-pool-match`**

   **Explicación:**
   Las anotaciones del Pod tienen prioridad sobre las del espacio de nombres, que a su vez tienen prioridad sobre las coincidencias de `podSelector`/`namespaceSelector`. Si no hay coincidencias, se usa el pool cuyo nombre indica `ipam-default-ip-pool` (valor predeterminado `default`), a menos que el Pod o su espacio de nombres tenga `ipam.cilium.io/require-pool-match: "true"`, lo que bloquea la asignación. La selección ocurre una sola vez, al crear el Pod.

   </details>

5. **Un Pod coincide con los selectores de dos recursos CiliumPodIPPool diferentes para la misma familia de direcciones y no tiene anotación de pool. ¿Qué sucede?**
   - A) La asignación falla con un error y un evento porque debe coincidir exactamente un pool por familia
   - B) Se usa el pool cuyo nombre aparece primero alfabéticamente y se registra un evento
   - C) El Pod recibe una dirección de cada pool coincidente y ambas se enrutan
   - D) Se usa el pool `default` para desempatar y se ignoran los selectores

   <details>
   <summary>Mostrar respuesta</summary>

   **Respuesta: A) La asignación falla con un error y un evento porque debe coincidir exactamente un pool por familia**

   **Explicación:**
   La selección por selectores requiere exactamente un pool coincidente por familia. Varias coincidencias producen un error (`multiple CiliumPodIPPools match pod ...`) y el Pod queda en `ContainerCreating`. Corrija el problema ajustando los selectores o anotando explícitamente el Pod o el espacio de nombres.

   </details>

6. **¿Qué afirmación sobre la delegación de prefijos ENI en Cilium 1.20.2 es correcta?**
   - A) Funciona con cualquier tipo de instancia EC2 y asigna prefijos /24, con fallback a /28 cuando la subred se llena
   - B) Funciona con cualquier tipo de instancia y combina libremente asignaciones /32 y /28 en el mismo nodo, cambiando según la subred para cada Pod
   - C) Requiere `ipam.mode=multi-pool` y un `CiliumPodIPPool` cuyos CIDR enumeren los prefijos que se delegarán
   - D) Solo funciona en instancias Nitro o bare metal, asigna prefijos /28, se omite si el nodo ya tiene IP secundarias /32 y recurre a /32 si la subred no tiene prefijos

   <details>
   <summary>Mostrar respuesta</summary>

   **Respuesta: D) Solo funciona en instancias Nitro o bare metal, asigna prefijos /28, se omite si el nodo ya tiene IP secundarias /32 y recurre a /32 si la subred no tiene prefijos**

   **Explicación:**
   El operador comprueba si hay un hipervisor Nitro o bare metal, omite el modo de prefijos en nodos que ya tienen IP secundarias (no hay modo mixto) y, ante `InsufficientPrefixesInSubnet`, deja de asignar prefijos a ese nodo y usa `AssignPrivateIpAddresses`. La unidad es /28 (16 direcciones, /80 para IPv6). El modo ENI no usa CiliumPodIPPool.

   </details>

7. **¿Cómo transfiere el asignador ENI de 1.20 al agente el estado de las interfaces EC2?**
   - A) El operador escribe IP individuales en `spec.ipam.pool` y el agente informa el uso en `status.ipam.used`, igual que en 1.19, sin escribir el estado ENI
   - B) El agente llama directamente a la API de EC2 con sus propias credenciales y el operador solo limpia los ENI no utilizados
   - C) El operador escribe ENI en `status.eni.enis`; el agente los convierte en CIDR /32 y /28 en `spec.ipam.pools.allocated` (pool `default`) e informa la demanda en `spec.ipam.pools.requested`
   - D) Cada ENI se convierte en su propio CiliumPodIPPool, seleccionado con la anotación `ip-pool` y creado por el operador

   <details>
   <summary>Mostrar respuesta</summary>

   **Respuesta: C) El operador escribe ENI en `status.eni.enis`; el agente los convierte en CIDR /32 y /28 en `spec.ipam.pools.allocated` (pool `default`) e informa la demanda en `spec.ipam.pools.requested`**

   **Explicación:**
   En 1.20, ENI pasó al asignador de varios pools: solo el operador llama a EC2; el agente calcula los CIDR asignados a partir del inventario de ENI y actualiza el campo de capacidad solicitada. El modelo `spec.ipam.pool` / `status.ipam.used` corresponde al asignador CRD de 1.19 y 1.18. El modo ENI no usa CiliumPodIPPool ni la anotación `ip-pool`.

   </details>

8. **[Versión preliminar 1.21] Actualmente, se pasa `--aws-use-primary-address` directamente al operador de Cilium. ¿Qué debe hacerse antes de migrar a 1.21?**
   - A) Nada; la marca solo está obsoleta y sigue funcionando como marca del operador en 1.21
   - B) Eliminarla y establecer `eni.nodeSpec.usePrimaryAddress=true` (marca del agente `--eni-use-primary-address`)
   - C) Configurarla en `CiliumPodIPPool` para el pool predeterminado bajo `spec.ipv4.pool[]`
   - D) Pasarla al agente como `--aws-use-primary-address`, conservando el mismo nombre

   <details>
   <summary>Mostrar respuesta</summary>

   **Respuesta: B) Eliminarla y establecer `eni.nodeSpec.usePrimaryAddress=true` (marca del agente `--eni-use-primary-address`)**

   **Explicación:**
   La marca del operador se elimina en 1.21 para que `CiliumNode.spec.eni.use-primary-address` sea la única fuente de verdad por nodo. Los usuarios de Helm no se ven afectados porque el chart siempre conectó únicamente el valor del lado del agente. Este cambio corresponde a una versión preliminar (v1.21.0-pre.3).

   </details>

9. **[Versión preliminar 1.21] ¿Para qué se usa `spec.ipv4.pool[].reservedRanges` en `CiliumPodIPPool` de `cilium.io/v2`?**
   - A) Para excluir direcciones de todos los bloques de nodo y entregarlas como IP estáticas de Service mediante pools de LB IPAM
   - B) Para permitir cambiar `maskSize` en un pool activo sin volver a crear los bloques de nodo existentes
   - C) Para reservar direcciones para los endpoints de router, health e ingress en cada bloque de nodo
   - D) Para conservar un CIDR antiguo en `cidrs` de modo que los bloques de nodo existentes sigan funcionando mientras no se creen bloques nuevos allí, lo que permite migrar gradualmente a otro CIDR

   <details>
   <summary>Mostrar respuesta</summary>

   **Respuesta: D) Para conservar un CIDR antiguo en `cidrs` de modo que los bloques de nodo existentes sigan funcionando mientras no se creen bloques nuevos allí, lo que permite migrar gradualmente a otro CIDR**

   **Explicación:**
   Reservar todo el CIDR antiguo significa que Cilium conserva las asignaciones existentes, pero asigna nuevos bloques PodCIDR solo desde los otros CIDR. Después de que todos los grupos de nodos migren, se elimina el CIDR antiguo y su entrada `pool`. Cada `pool[].cidr` debe ser uno de los valores de `cidrs`; `maskSize` permanece inmutable.

   </details>

10. **Dos recursos `CiliumLoadBalancerIPPool` contienen bloques superpuestos. ¿Qué hace LB IPAM?**
    - A) Marca el pool posterior como Conflicting (`cilium.io/PoolConflict`) y no asigna nada desde él
    - B) Rechaza el segundo pool durante la admisión mediante un webhook de validación
    - C) Los combina en un solo pool y asigna direcciones de la unión de sus bloques
    - D) Divide el rango superpuesto equitativamente entre los dos pools según la cantidad de Service

    <details>
    <summary>Mostrar respuesta</summary>

    **Respuesta: A) Marca el pool posterior como Conflicting (`cilium.io/PoolConflict`) y no asigna nada desde él**

    **Explicación:**
    LB IPAM no combina ni rechaza pools superpuestos. El pool posterior se marca como Conflicting, se muestra en la columna de salida `Conflicting` y en la métrica `lbipam_conflicting_pools` (el prefijo exacto en tiempo de ejecución, `cilium_` o `cilium_operator_`, no está verificado), y no se asigna ninguna IP desde él. Editar un pool activo también puede reasignar IP de Service existentes, así que es preferible agregar un pool o establecer `disabled: true`.

    </details>
