# Cuestionario de IPAM y políticas de red de Cilium

> **Cilium 1.20.3 · 2026-10-16**

## IPAM

1. **Sin una configuración específica de la plataforma, ¿cuál es el modo IPAM genérico predeterminado y cómo se asignan las direcciones?**
   - A) `kubernetes`; cada Pod solicita una IP a la API de Kubernetes
   - B) `cluster-pool`; el Cilium Operator asigna prefijos CIDR a los nodos y los agentes asignan localmente las IP de los Pods
   - C) `crd`; cada Pod crea un CiliumPodIPPool
   - D) `eni` en todas las plataformas

   <details>
   <summary>Mostrar respuesta</summary>

   **Respuesta: B) `cluster-pool`; el Cilium Operator asigna prefijos CIDR a los nodos y los agentes asignan localmente las IP de los Pods**

   `cluster-pool` asigna prefijos de nodo mediante CiliumNode. No solicita centralmente una dirección por cada Pod, y los perfiles de plataforma pueden elegir otro backend.

   </details>

2. **¿Qué modo obtiene los prefijos de nodo del estado Node de Kubernetes en lugar de usar la asignación `cluster-pool` del Cilium Operator?**
   - A) `cluster-pool`
   - B) `kubernetes` (ámbito del host)
   - C) Solo `multi-pool`
   - D) Solo `eni`

   <details>
   <summary>Mostrar respuesta</summary>

   **Respuesta: B) `kubernetes` (ámbito del host)**

   Kubernetes proporciona los CIDR necesarios para los nodos y el agente asigna direcciones dentro de ellos. Tanto el ámbito del host como `cluster-pool` asignan localmente direcciones individuales; ninguno elimina la coordinación de prefijos.

   </details>

3. **¿Qué backend se aplica cuando Cilium administra las ENI de AWS y las direcciones de VPC en una instalación preparada sobre nodos EC2?**
   - A) `kubernetes`
   - B) `cluster-pool`
   - C) `eni`
   - D) `delegated-plugin` para todos los nodos de AWS

   <details>
   <summary>Mostrar respuesta</summary>

   **Respuesta: C) `eni`**

   Es IPAM de ENI. Si AWS VPC CNI se encadena con Cilium, la asignación de IP sigue a cargo de AWS VPC CNI; Hybrid Nodes usan una ruta distinta, y Fargate y Auto Mode no admiten esta configuración de reemplazo.

   </details>

4. **¿Qué campos de Kubernetes son pertinentes para el modo IPAM con ámbito del host?**
   - A) `Node.spec.podCIDRs` y el campo `Node.spec.podCIDR`, heredado y limitado a una sola familia
   - B) `Node.spec.subnet`
   - C) `Service.spec.podCIDR`
   - D) `CiliumPodIPPool.spec.selector`

   <details>
   <summary>Mostrar respuesta</summary>

   **Respuesta: A) `Node.spec.podCIDRs` y el campo `Node.spec.podCIDR`, heredado y limitado a una sola familia**

   Estos son campos del recurso Node de Kubernetes. En cambio, `cluster-pool` usa `CiliumNode.spec.ipam.podCIDRs`; cuál es el estado autoritativo depende del modo seleccionado.

   </details>

5. **¿Cómo se debe investigar la configuración IPAM efectiva?**
   - A) Considerar completa cualquier línea de `grep` que contenga `ipam`
   - B) Usar solo la disponibilidad del Pod
   - C) Usar siempre la primera dirección y el primer CIDR de CiliumNode
   - D) Comparar los valores deseados y las anulaciones por nodo con el estado real del agente y del Operator, y con el recurso del asignador seleccionado

   <details>
   <summary>Mostrar respuesta</summary>

   **Respuesta: D) Comparar los valores deseados y las anulaciones por nodo con el estado real del agente y del Operator, y con el recurso del asignador seleccionado**

   Los valores de Helm/ConfigMap, las anulaciones por nodo y el estado de asignación se complementan. CiliumNode no es la fuente autoritativa universal para todos los modos IPAM, y la posición de una dirección en una lista no determina el siguiente salto.

   </details>

## Conceptos básicos de políticas

6. **¿Qué versión de API del recurso CiliumNetworkPolicy se usa en esta guía?**
   - A) `networking.k8s.io/v1`
   - B) `cilium.io/v1`
   - C) `cilium.io/v2`
   - D) `policy.cilium.io/v1`

   <details>
   <summary>Mostrar respuesta</summary>

   **Respuesta: C) `cilium.io/v2`**

   CiliumNetworkPolicy usa `cilium.io/v2`. No la confundas con la API `v2alpha1` de CiliumPodIPPool ni con el recurso NetworkPolicy estándar de Kubernetes.

   </details>

7. **¿Qué selecciona `endpointSelector` en una CiliumNetworkPolicy con ámbito de namespace?**
   - A) Los endpoints de ese namespace a los que se aplica la política
   - B) Un Service de Kubernetes que se debe crear
   - C) Nodos host de cualquier namespace
   - D) Otras políticas que se deben heredar

   <details>
   <summary>Mostrar respuesta</summary>

   **Respuesta: A) Los endpoints de ese namespace a los que se aplica la política**

   Selecciona los endpoints a los que se aplica la política. El ámbito del recurso y sus selectores son distintos de los peers de tráfico descritos en las reglas ingress/egress.

   </details>

8. **¿Qué describe una regla ingress?**
   - A) El tráfico que entra en los endpoints seleccionados
   - B) El tráfico que sale de los endpoints seleccionados
   - C) Un nuevo pool de IP
   - D) Un anuncio de rutas

   <details>
   <summary>Mostrar respuesta</summary>

   **Respuesta: A) El tráfico que entra en los endpoints seleccionados**

   Ingress se define con respecto al endpoint sujeto seleccionado. Aplica las restricciones correspondientes de peer, puerto y protocolo admitido.

   </details>

9. **¿Qué describe una regla egress?**
   - A) El tráfico que entra en los endpoints seleccionados
   - B) El tráfico que sale de los endpoints seleccionados
   - C) Todo el tráfico en todas partes
   - D) Solo el tráfico que viene de fuera de Kubernetes

   <details>
   <summary>Mostrar respuesta</summary>

   **Respuesta: B) El tráfico que sale de los endpoints seleccionados**

   Egress controla el tráfico saliente del endpoint seleccionado. Conserva deliberadamente las dependencias necesarias de DNS y de la aplicación.

   </details>

10. **¿Para qué se usan las etiquetas opcionales `spec.labels` de una regla de Cilium?**
    - A) Para seleccionar los Pods sujetos en lugar de usar `endpointSelector`
    - B) Para identificar la regla y aportar metadatos
    - C) Para heredar cualquier política con las mismas etiquetas
    - D) Para asignar IP a los Pods

    <details>
    <summary>Mostrar respuesta</summary>

    **Respuesta: B) Para identificar la regla y aportar metadatos**

    Las etiquetas de regla pueden servir para identificación y búsquedas, y no tienen que ser únicas. No hacen referencia a otras políticas ni las heredan; `metadata.labels` de Kubernetes etiqueta el propio recurso.

    </details>

## Selección de peers

11. **¿Cuál es el propósito y cuál es el límite predeterminado de `toCIDR`/`toCIDRSet`?**
    - A) Seleccionar prefijos IP, principalmente para peers externos; la coincidencia con Pods/nodos administrados tiene límites predeterminados documentados
    - B) Filtrar URL HTTP
    - C) Crear Services automáticamente
    - D) Asignar direcciones de esos prefijos

    <details>
    <summary>Mostrar respuesta</summary>

    **Respuesta: A) Seleccionar prefijos IP, principalmente para peers externos; la coincidencia con Pods/nodos administrados tiene límites predeterminados documentados**

    Para las políticas habituales sobre Pods administrados, usa selectores de endpoints. La versión documenta una coincidencia beta optativa de CIDR para Pods/nodos, con implicaciones para el consumo de identidades; no describas el comportamiento predeterminado como un comparador IP incondicional.

    </details>

12. **¿Qué autoriza `toFQDNs`?**
    - A) Todas las consultas DNS automáticamente
    - B) Cualquier URL HTTP del dominio
    - C) Tráfico hacia las IP aprendidas para los nombres seleccionados, sujeto a los puertos y demás restricciones de la política
    - D) Solo IP configuradas estáticamente

    <details>
    <summary>Mostrar respuesta</summary>

    **Respuesta: C) Tráfico hacia las IP aprendidas para los nombres seleccionados, sujeto a los puertos y demás restricciones de la política**

    Una regla aparte del proxy DNS permite observar la correspondencia entre nombres e IP. Autorizar el puerto 53 por sí solo no habilita ese aprendizaje, y permitir una IP no equivale a autorizar un hostname HTTP ni a un usuario de la aplicación.

    </details>

13. **¿Qué representa la entidad `world`?**
    - A) Todos los Pods locales y remotos sin distinción
    - B) Una categoría amplia de identidades externas al clúster
    - C) Solo los nodos del plano de control
    - D) Solo las direcciones de Internet públicas

    <details>
    <summary>Mostrar respuesta</summary>

    **Respuesta: B) Una categoría amplia de identidades externas al clúster**

    `world` puede incluir peers externos privados; no equivale a la entidad `all` ni a un selector de un clúster remoto con nombre. Cuando sea necesario, usa peers explícitos y reglas más acotadas.

    </details>

14. **¿Cómo funciona `toServices`?**
    - A) Resuelve los selectores de Service de Kubernetes o las direcciones de EndpointSlice de Services sin selector y los convierte en selectores de políticas
    - B) Crea un Service y configura el enrutamiento automáticamente
    - C) Hace accesibles todos los nombres DNS
    - D) Reemplaza todas las reglas de entidad de kube-apiserver

    <details>
    <summary>Mostrar respuesta</summary>

    **Respuesta: A) Resuelve los selectores de Service de Kubernetes o las direcciones de EndpointSlice de Services sin selector y los convierte en selectores de políticas**

    Los Services sin selector usan selectores derivados de CIDR y heredan sus límites. No des por sentado que el Service especial `default/kubernetes` se comporta como un selector de una carga de trabajo ordinaria.

    </details>

15. **¿Dónde se usa `nodeSelector` para seleccionar sujetos del firewall de host?**
    - A) En cualquier CiliumNetworkPolicy con ámbito de namespace, sin requisitos previos
    - B) En CiliumClusterwideNetworkPolicy cuando el firewall de host está configurado
    - C) En CiliumPodIPPool para asignar la IP de cada Pod
    - D) En anotaciones de Service

    <details>
    <summary>Mostrar respuesta</summary>

    **Respuesta: B) En CiliumClusterwideNetworkPolicy cuando el firewall de host está configurado**

    La API Rule restringe `nodeSelector` a CiliumClusterwideNetworkPolicy. Es distinto de `endpointSelector` y de la selección de peers mediante `fromNodes`/`toNodes`.

    </details>

## Política L7

16. **¿Qué atributos de las solicitudes HTTP pueden restringir las reglas L7 admitidas por Cilium?**
    - A) La ruta
    - B) El método
    - C) Los encabezados
    - D) Todos los anteriores

    <details>
    <summary>Mostrar respuesta</summary>

    **Respuesta: D) Todos los anteriores**

    Envoy aplica las reglas al tráfico HTTP visible. Una regla L4 independiente y sin restricciones puede eludir restricciones L7 que se superpongan; además, que la política permita el tráfico no garantiza que la aplicación funcione correctamente.

    </details>

17. **¿Qué es cierto sobre `rules.kafka` en Cilium 1.20.3?**
    - A) Autoriza temas de Kafka de forma predeterminada
    - B) Se habilita cambiando `apiVersion` a `v2alpha1`
    - C) Cifra automáticamente la conexión con el broker
    - D) Se eliminó la API L7 de Kafka integrada; usa controles de red adecuados y la autorización del broker

    <details>
    <summary>Mostrar respuesta</summary>

    **Respuesta: D) Se eliminó la API L7 de Kafka integrada; usa controles de red adecuados y la autorización del broker**

    No apliques la política obsoleta de temas/API keys/ID de cliente. Para la conectividad L4, usa el puerto real del listener del broker y sus mecanismos nativos de autenticación y autorización.

    </details>

18. **¿Qué afirmación sobre los comodines coincide con la implementación de esta versión?**
    - A) `*.example.com` también coincide con `example.com` y `a.b.example.com`
    - B) `*.example.com` coincide con una etiqueta de subdominio; `**.example.com` coincide con uno o más niveles, y ambos excluyen el dominio raíz
    - C) Todos los asteriscos siempre coinciden con puntos
    - D) `matchName` y `matchPattern` asignan direcciones DNS

    <details>
    <summary>Mostrar respuesta</summary>

    **Respuesta: B) `*.example.com` coincide con una etiqueta de subdominio; `**.example.com` coincide con uno o más niveles, y ambos excluyen el dominio raíz**

    La implementación compara el nombre DNS normalizado anclándolo por completo. Los nombres exactos, los comodines de una etiqueta y el prefijo de varios niveles tienen significados distintos; un `matchName` separado puede incluir el dominio raíz.

    </details>

19. **¿Cómo se expresan las restricciones admitidas para servicios/métodos gRPC y metadatos?**
    - A) Con un filtro de campos protobuf `rules.grpc`
    - B) Solo con una coincidencia CIDR L3
    - C) Con coincidencias de ruta y encabezados HTTP/2 mediante la ruta admitida de Envoy
    - D) Reemplazando el CNI por kube-proxy

    <details>
    <summary>Mostrar respuesta</summary>

    **Respuesta: C) Con coincidencias de ruta y encabezados HTTP/2 mediante la ruta admitida de Envoy**

    Los nombres de servicio/método gRPC aparecen en la ruta HTTP/2 y los metadatos, en los encabezados. Esto no inspecciona arbitrariamente el payload protobuf; también importa si TLS permite ver ese tráfico.

    </details>

20. **¿Qué distinción entre componentes es correcta?**
    - A) kube-proxy aplica todas las reglas L7
    - B) Envoy gestiona las reglas HTTP/gRPC admitidas; el proxy DNS de Cilium gestiona la política DNS
    - C) NGINX Ingress es obligatorio para la política DNS
    - D) Todos los analizadores L7 se ejecutan solo en BPF del kernel

    <details>
    <summary>Mostrar respuesta</summary>

    **Respuesta: B) Envoy gestiona las reglas HTTP/gRPC admitidas; el proxy DNS de Cilium gestiona la política DNS**

    De forma predeterminada, el proxy DNS se ejecuta dentro del agente; existe un modo independiente alfa documentado por separado. No exijas Envoy para todas las reglas DNS ni des por sentado que el cifrado deja visible el payload.

    </details>

[Revisa la guía](../../../networking/cilium/04-ipam-policy.md).
