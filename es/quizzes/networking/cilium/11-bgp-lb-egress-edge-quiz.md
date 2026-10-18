# Cuestionario sobre el plano de control BGP, las IP de los balanceadores de carga y el egreso: parte 11

> **Cilium 1.20.2 · 2026-10-15**

1. **En un clúster de EKS que usa ENI IPAM, ¿qué consigue un `CiliumBGPAdvertisement` de tipo `PodCIDR`?**
   - A) Anuncia cada IP secundaria de ENI al peer como una ruta `/32`
   - B) Programa las rutas en la tabla de enrutamiento de la VPC
   - C) Anuncia el CIDR de la VPC desde cada nodo
   - D) Nada útil: ENI IPAM no asigna a los nodos un PodCIDR propio de Cilium, así que no hay ningún prefijo por nodo que anunciar

   <details>
   <summary>Mostrar respuesta</summary>

   **Respuesta: D) Nada útil: ENI IPAM no asigna a los nodos un PodCIDR propio de Cilium, así que no hay ningún prefijo por nodo que anunciar**

   El anuncio `PodCIDR` solo funciona con modos de IPAM que asignan un PodCIDR por nodo (cluster-pool, ámbito de host de Kubernetes). Con ENI, las IP de los pods ya son direcciones de la VPC que esta enruta, y BGP Control Plane nunca programa tablas de rutas de la nube.

   </details>

2. **¿Cómo elige un `CiliumBGPPeerConfig` qué anuncios enviar a un peer?**
   - A) Mediante `families[].advertisements`, un selector de etiquetas que coincide con `metadata.labels` de los objetos `CiliumBGPAdvertisement`
   - B) Mediante una coincidencia de `advertisementType` en la entrada `families` del peer
   - C) Enumerando nombres de anuncios en `peerConfigRef`
   - D) Mediante una anotación en el nodo

   <details>
   <summary>Mostrar respuesta</summary>

   **Respuesta: A) Mediante `families[].advertisements`, un selector de etiquetas que coincide con `metadata.labels` de los objetos `CiliumBGPAdvertisement`**

   ClusterConfig hace referencia a PeerConfig por nombre, pero PeerConfig selecciona anuncios mediante etiquetas del objeto de anuncio. Si no coincide ningún anuncio, la sesión se establece pero no se anuncia nada.

   </details>

3. **Un Service `LoadBalancer` se anuncia mediante BGP con `externalTrafficPolicy: Local`. ¿Desde qué nodos se anuncia su VIP?**
   - A) Solo desde el nodo que tiene el lease del Service
   - B) Desde todos los nodos seleccionados por la configuración del clúster
   - C) Solo desde nodos que tengan al menos un backend local Ready; la ruta sigue a los pods
   - D) Solo desde nodos del plano de control

   <details>
   <summary>Mostrar respuesta</summary>

   **Respuesta: C) Solo desde nodos que tengan al menos un backend local Ready; la ruta sigue a los pods**

   Con `Cluster`, el VIP se anuncia desde todos los nodos seleccionados. Con `Local`, se retira de los nodos que no tengan un endpoint local Ready. Los leases pertenecen a los anuncios L2, no a BGP.

   </details>

4. **Después de actualizar Cilium 1.19 a 1.20, los paneles de Grafana de sesiones BGP aparecen vacíos. ¿Cuál es la causa probable?**
   - A) Las métricas BGP se trasladaron al operador
   - B) La etiqueta por instancia `vrouter` ahora es `instance_name`, y las notas de actualización de 1.20 no lo mencionan
   - C) Las métricas BGP están deshabilitadas a menos que se establezca `bgpControlPlane.metrics.enabled`
   - D) El prefijo de las métricas cambió de `cilium_` a `bgp_`

   <details>
   <summary>Mostrar respuesta</summary>

   **Respuesta: B) La etiqueta por instancia `vrouter` ahora es `instance_name`, y las notas de actualización de 1.20 no lo mencionan**

   La documentación de métricas de 1.19.8 usa `vrouter`; la de 1.20.2 usa `instance_name`. Las consultas y alertas que filtran por la etiqueta anterior dejan de coincidir silenciosamente.

   </details>

5. **Dos objetos `CiliumBGPAdvertisement` coinciden con el mismo Service, pero tienen comunidades y valores `localPreference` distintos (Cilium 1.18 y posterior). ¿Qué se anuncia?**
   - A) La unión de las comunidades y el valor máximo de `localPreference`
   - B) Los atributos del último anuncio aplicado
   - C) Solo el primer anuncio en orden alfabético
   - D) Se retira la ruta debido al conflicto

   <details>
   <summary>Mostrar respuesta</summary>

   **Respuesta: A) La unión de las comunidades y el valor máximo de `localPreference`**

   «Gana la última coincidencia» era el comportamiento anterior a 1.18. Recuerda además que `localPreference` solo se envía a peers iBGP.

   </details>

6. **¿En qué versión se eliminaron v1 `CiliumBGPPeeringPolicy` y su plano de control?**
   - A) 1.18
   - B) 1.20
   - C) 1.21
   - D) 1.19

   <details>
   <summary>Mostrar respuesta</summary>

   **Respuesta: D) 1.19**

   Quedó obsoleta en 1.18 y se eliminó junto con `pkg/bgpv1` en 1.19, por lo que los clústeres deben migrar a las CRD `cilium.io/v2` antes de actualizar a 1.19. Las copias v2alpha1 de las CRD v2 siguen expuestas a través de la API, pero están obsoletas en 1.20 y 1.21-pre.

   </details>

7. **¿Cómo se debe gestionar la detección rápida de fallos en una sesión BGP multisalto en Cilium 1.20?**
   - A) Habilitar BFD en `CiliumBGPPeerConfig.spec.bfd`
   - B) BFD no es compatible; reduce los temporizadores hold y keepalive (mínimos de la CRD: 3 y 1) y usa Graceful Restart para reinicios del agente
   - C) Establecer `ebgpMultihop` en 255, lo que habilita la conmutación rápida por error
   - D) Usar `connectRetryTimeSeconds: 1`

   <details>
   <summary>Mostrar respuesta</summary>

   **Respuesta: B) BFD no es compatible; reduce los temporizadores hold y keepalive (mínimos de la CRD: 3 y 1) y usa Graceful Restart para reinicios del agente**

   Ninguna CRD de las versiones 1.18 a 1.21-pre tiene un campo BFD. Los temporizadores 9/3 que se suelen citar son un ajuste agresivo recomendado, no los mínimos de la CRD. `ebgpMultihop` solo establece el TTL; connect-retry afecta a la reconexión, no a la detección de fallos.

   </details>

8. **Ya existen objetos `TLSRoute` con `v1alpha2` y se planea actualizar a Cilium 1.20 (Gateway API v1.6.1). ¿Qué hay que hacer?**
   - A) Nada; las CRD del canal estándar convierten los objetos automáticamente
   - B) Eliminar TLSRoute y volver a crearlos después de la actualización
   - C) Hacer una copia de seguridad de TLSRoute e instalar la CRD TLSRoute v1.6.1 del canal experimental (que aún incluye `v1alpha2`) antes de actualizar Cilium
   - D) Instalar solo la CRD TLSRoute v1.6 del canal estándar, que conserva todas las versiones

   <details>
   <summary>Mostrar respuesta</summary>

   **Respuesta: C) Hacer una copia de seguridad de TLSRoute e instalar la CRD TLSRoute v1.6.1 del canal experimental (que aún incluye `v1alpha2`) antes de actualizar Cilium**

   Instalar la CRD TLSRoute v1.6 del canal estándar hace que los objetos `v1alpha2` almacenados no se puedan leer, por lo que parece que desaparecen.

   </details>

9. **Con la configuración predeterminada del lease de anuncios L2 (duración de 15 s, plazo de renovación de 5 s, reintento de 2 s), ¿cuál es la ventana aproximada de conmutación por error?**
   - A) De 2 a 4 segundos
   - B) Exactamente 15 segundos
   - C) De 30 a 60 segundos
   - D) De 10 a 20 segundos

   <details>
   <summary>Mostrar respuesta</summary>

   **Respuesta: D) De 10 a 20 segundos**

   La conmutación por error ocurre entre `leaseDuration - leaseRenewDeadline` y `leaseDuration + leaseRenewDeadline`. Ajustar los valores a 3 s/1 s/200 ms da de 2 a 4 segundos, pero aumenta la cantidad de consultas por segundo (QPS) a la API; por tanto, eleva el límite de QPS del cliente.

   </details>

10. **Una `CiliumEgressGatewayPolicy` tiene un `egressGateway.nodeSelector` que no coincide con ningún nodo. ¿Qué ocurre con el tráfico de los pods seleccionados a los CIDR de destino?**
    - A) Se descarta
    - B) Se envía por un nodo aleatorio
    - C) Vuelve al masquerade normal del nodo
    - D) Se pone en cola hasta que aparezca un gateway

    <details>
    <summary>Mostrar respuesta</summary>

    **Respuesta: A) Se descarta**

    Egress Gateway no tiene conmutación por error basada en estado de salud ni fallback en 1.20.2 ni 1.21.0-pre.3. Si no hay ningún gateway coincidente, se descarta el tráfico a los CIDR de destino.

    </details>
