# Cuestionario sobre redes L2–L7 y balanceo de carga de Cilium

> **Cilium 1.20.3 · CLI 0.20.1 · 2026-10-16**

## Preguntas de opción múltiple

1. **¿Qué capa conceptual del modelo OSI contiene el comportamiento de aplicación de HTTP, DNS y gRPC?**
   - A) L1
   - B) L2
   - C) L3
   - D) L7

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: D) L7**

Los protocolos de aplicación se asignan conceptualmente a L7. Esto no significa que Cilium tenga un analizador nativo de políticas para todos los protocolos de aplicación; las reglas L7 de Kafka se han eliminado.

</details>

2. **¿Qué característica ofrece el retorno directo (DSR)?**
   - A) Cifra todas las respuestas
   - B) Un backend remoto puede responder sin volver a pasar por el nodo de entrada que realiza el balanceo de carga
   - C) Autentica las IP de los clientes
   - D) Restaura las IP de cliente que ya haya reescrito un proxy anterior

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Un backend remoto puede responder sin volver a pasar por el nodo de entrada que realiza el balanceo de carga**

La red debe admitir la ruta de retorno asimétrica. DSR puede reducir un salto en la ruta de respuesta; el rendimiento y la conservación de la IP del cliente dependen de la topología real.

</details>

3. **¿Qué componente gestiona las políticas HTTP/gRPC de Cilium compatibles?**
   - A) kube-proxy
   - B) Hubble Relay
   - C) Envoy
   - D) CoreDNS

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Envoy**

La implementación de Envoy depende de los valores de instalación. Las políticas DNS usan el proxy DNS de Cilium; declarar una regla Kafka que ya no se admite no instala un analizador Kafka.

</details>

4. **¿Qué par corresponde a los algoritmos documentados de Cilium para seleccionar backends de servicios BPF?**
   - A) Round Robin y Least Connection
   - B) Random y Maglev
   - C) Hash de IP de origen y tiempo de respuesta ponderado
   - D) Todos los algoritmos de Envoy

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Random y Maglev**

La selección BPF y el balanceo de carga L7 de Envoy son componentes distintos. Maglev está disponible en ciertas rutas externas; el tráfico este-oeste habitual con socket-LB no utiliza Maglev.

</details>

5. **¿Qué afirmación sobre las implementaciones de masquerading es correcta?**
   - A) BPF siempre ofrece más velocidad con cualquier carga de trabajo
   - B) Todas las versiones del kernel de Linux son compatibles con Cilium actual
   - C) Ambas implementaciones se ejecutan en el kernel y tienen requisitos de configuración o plataforma
   - D) Elegir BPF elimina los requisitos de enrutamiento

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Ambas implementaciones se ejecutan en el kernel y tienen requisitos de configuración o plataforma**

Ni el nombre del producto ni su ejecución en el kernel demuestran por sí solos un resultado de rendimiento. El masquerading BPF de esta versión depende de funciones y dispositivos específicos, y la compatibilidad con IPv6 está en fase beta.

</details>

6. **¿Qué valor actual habilita el reemplazo de kube-proxy?**
   - A) kubeProxyReplacement: partial
   - B) kubeProxyReplacement: true
   - C) kubeProxyReplacement: strict
   - D) kubeProxyReplacement: hybrid

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) kubeProxyReplacement: true**

Use el valor booleano actual true y cumpla todos los requisitos previos del reemplazo, incluida la conectividad con la API. El vocabulario anterior de strict/partial ya no describe el contrato vigente.

</details>

7. **¿Cuál de las siguientes opciones no es un predicado integrado de las políticas HTTP de Cilium?**
   - A) Método
   - B) Ruta
   - C) Condiciones admitidas para encabezados
   - D) Contenido arbitrario del cuerpo de la solicitud

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: D) Contenido arbitrario del cuerpo de la solicitud**

Las expresiones de método y ruta son distintas de las condiciones admitidas para encabezados. Una cadena con valor para un encabezado es literal, no una expresión regular general para el valor. La inspección de cargas útiles requiere diseñar por separado una solución de aplicación o proxy.

</details>

8. **¿Qué modelo de integración entre Cilium e Istio plantea la guía?**
   - A) Omitir automáticamente la interceptación de los sidecars de Istio
   - B) Mantener la interceptación de Istio y combinar los controles de red de Cilium con la responsabilidad de Istio sobre L7 y mTLS
   - C) Deshabilitar mTLS automáticamente
   - D) Hacer que todas las reglas HTTP de Cilium inspeccionen tráfico de Istio cifrado

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Mantener la interceptación de Istio y combinar los controles de red de Cilium con la responsabilidad de Istio sobre L7 y mTLS**

Configure la interoperabilidad de CNI/socket-LB y pruebe la topología. El ejemplo conserva mTLS de Istio y usa políticas L3/L4 de Cilium, en vez de aplicar inspección HTTP en texto claro al tráfico cifrado.

</details>

9. **¿Qué puede hacer el balanceo de carga a nivel de socket?**
   - A) Elegir un backend antes de construir los paquetes mediante los hooks de socket compatibles
   - B) Autenticar automáticamente los encabezados HTTP
   - C) Descifrar todo el tráfico
   - D) Crear un balanceador de carga externo

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A) Elegir un backend antes de construir los paquetes mediante los hooks de socket compatibles**

Las conexiones TCP y las rutas de socket UDP compatibles pueden traducir un Service a un backend antes de construir los paquetes. Esto no garantiza menor latencia en todos los casos y puede requerir tratamiento especial cuando interviene la interceptación de un sidecar.

</details>

10. **¿Qué principio es adecuado para tratar la fragmentación?**
   - A) El seguimiento garantiza protección contra todos los ataques de fragmentación
   - B) Planificar la MTU efectiva de la ruta y verificar la señalización de errores necesaria
   - C) Siempre hay que descartar todos los fragmentos
   - D) La MTU de Cilium siempre equivale al tamaño final de la carga útil del Pod

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Planificar la MTU efectiva de la ruta y verificar la señalización de errores necesaria**

La MTU de Cilium sustituye el valor de la red subyacente. El seguimiento de fragmentos conserva el contexto L4, pero no reensambla la carga útil ni garantiza la prevención de ataques; PMTUD puede fallar si se interrumpen la señalización o el comportamiento requeridos en la ruta.

</details>

## Preguntas de respuesta corta

11. **Indique los grupos de políticas L7 integrados actuales y explique dónde encaja gRPC.**

<details>
<summary>Mostrar respuesta</summary>

HTTP y DNS. Las restricciones compatibles de gRPC usan la coincidencia de rutas y encabezados HTTP/2 mediante Envoy. DNS usa el proxy DNS de Cilium; las reglas L7 de Kafka se han eliminado. La visibilidad TLS debe configurarse, no darse por sentada.

</details>

12. **Distinga entre la disponibilidad de backends de un Service y un motor genérico de comprobaciones de estado activas.**

<details>
<summary>Mostrar respuesta</summary>

El estado de los endpoints de Kubernetes y el estado de readiness influyen en la elegibilidad de los backends, con sujeción a la semántica de Service y terminación, y al retraso de propagación. Esto no significa que cada Service BPF realice sondeos TCP/HTTP independientes. La comprobación de conectividad de Cilium, los sondeos de la aplicación y las comprobaciones de estado del proxy son mecanismos distintos.

</details>

13. **¿Qué operación cambia la dirección de origen de un Pod al salir por una ruta externa?**

<details>
<summary>Mostrar respuesta</summary>

SNAT/masquerading. Es distinto de la traducción del destino a un backend de Service. La interfaz seleccionada, los CIDR excluidos, las excepciones de nodo y una NAT posterior en la nube pueden afectar a la dirección de origen observada; una solicitud HTTP externa satisfactoria no demuestra por sí sola qué implementación se usó.

</details>

14. **Explique por qué Maglev y sessionAffinity: ClientIP no son intercambiables.**

<details>
<summary>Mostrar respuesta</summary>

Maglev ofrece selección de backend coherente en las rutas compatibles, usando tablas, estado y una semilla compatibles. La afinidad ClientIP mantiene una afinidad de Service por cliente y el comportamiento de timeout correspondiente, mediante una IP o la cookie del espacio de nombres de socket-LB aplicable. Ninguna de las dos conserva una sesión en un backend que ha fallado o se ha eliminado.

</details>

15. **¿Qué es L4 y qué diferencia de fiabilidad importa entre TCP y UDP?**

<details>
<summary>Mostrar respuesta</summary>

L4 es la capa de transporte. TCP proporciona un flujo de bytes fiable y ordenado; UDP proporciona datagramas sin garantías de entrega ni de orden. UDP no es automáticamente más rápido para todas las aplicaciones, y una política de protocolo y puerto no proporciona autenticación de aplicación.

</details>

## Preguntas prácticas

16. **Escriba una política para una API que escucha en TCP8080 en l7-exercise: permita frontend GET /api/v1/users y POST /api/v1/data solo cuando esté presente X-Auth-Token.**

<details>
<summary>Mostrar respuesta</summary>

```yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: api-http
  namespace: l7-exercise
spec:
  endpointSelector:
    matchLabels:
      app: backend-api
  ingress:
  - fromEndpoints:
    - matchLabels:
        k8s:io.kubernetes.pod.namespace: l7-exercise
        k8s:app: frontend
    toPorts:
    - ports:
      - port: '8080'
        protocol: TCP
      rules:
        http:
        - method: ^GET$
          path: ^/api/v1/users$
        - method: ^POST$
          path: ^/api/v1/data$
          headerMatches:
          - name: x-auth-token
```

Las etiquetas de la carga de trabajo y el espacio de nombres, así como el listener, son requisitos previos. Una entrada de headerMatches que solo indique un nombre comprueba su presencia; no valida un token. La cadena antigua `X-Auth-Token: .*` significa una coincidencia literal con valor, no cualquier valor. Revise las otras políticas aplicables y el estado efectivo del proxy.

</details>

17. **Instale el perfil DSR/Maglev documentado en un clúster de prueba IPv4 nuevo, preparado y sin kube-proxy.**

<details>
<summary>Mostrar respuesta</summary>

**lb-values.yaml**

```yaml
kubeProxyReplacement: true
routingMode: tunnel
tunnelProtocol: geneve
ipv4:
  enabled: true
ipv6:
  enabled: false
ipam:
  mode: cluster-pool
  operator:
    clusterPoolIPv4PodCIDRList:
    - 10.244.0.0/16
    clusterPoolIPv4MaskSize: 24
loadBalancer:
  mode: dsr
  dsrDispatch: geneve
  algorithm: maglev
  acceleration: disabled
maglev:
  tableSize: 65521
bpf:
  masquerade: true
enableIPv4Masquerade: true
enableIPv6Masquerade: false
l7Proxy: true
envoy:
  enabled: true
hubble:
  enabled: true
  relay:
    enabled: true
```

```bash
: "${API_SERVER_HOST:?Set the real reachable API server host}"
: "${API_SERVER_PORT:?Set its actual port}"
: "${MAGLEV_SEED:?Set the persisted base64 encoding of 12 random bytes}"
helm repo add cilium https://helm.cilium.io/
helm repo update cilium
helm install cilium cilium/cilium --version 1.20.3 --namespace kube-system \
  --values lb-values.yaml \
  --set-string k8sServiceHost="$API_SERVER_HOST" \
  --set k8sServicePort="$API_SERVER_PORT" \
  --set-string maglev.hashSeed="$MAGLEV_SEED"
cilium status --wait
```

El perfil usa una superposición Geneve con despacho DSR Geneve. Antes deben estar preparados el endpoint de API, la ruta de retorno de red y una semilla Maglev común persistida. 65521 es un tamaño de tabla permitido, no un requisito universal. No elimine kube-proxy después de una instalación arbitraria ni cambie el modo de reenvío de un clúster en ejecución como atajo de prueba.

</details>

18. **El requisito es orders-produce para order-service y payments-consume para payment-processor. ¿Qué puede aplicar la política actual de Cilium y qué debe aplicar el broker?**

<details>
<summary>Mostrar respuesta</summary>

```yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: broker-connectivity
  namespace: messaging
spec:
  endpointSelector:
    matchLabels:
      app: kafka-broker
  ingress:
  - fromEndpoints:
    - matchLabels:
        k8s:io.kubernetes.pod.namespace: messaging
        k8s:app: order-service
    - matchLabels:
        k8s:io.kubernetes.pod.namespace: messaging
        k8s:app: payment-processor
    toPorts:
    - ports:
      - port: '9092'
        protocol: TCP
```

Esto solo permite tráfico de las dos cargas de trabajo de origen al listener supuesto del broker en TCP9092; sustituya el puerto por el del listener configurado realmente. No aplica las operaciones sobre los topics. Autentique principales distintos en el broker y configure en Kafka la autorización requerida para producir, consumir y usar grupos de consumidores. Se ha eliminado `rules.kafka`, por lo que presentar el YAML antiguo como autorización completa sería incorrecto.

</details>

19. **Proporcione un fragmento de masquerading BPF que excluya los destinos dentro de un rango 10.0.0.0/8 que tenga rutas válidas.**

<details>
<summary>Mostrar respuesta</summary>

```yaml
bpf:
  masquerade: true
enableIPv4Masquerade: true
enableIPv6Masquerade: false
ipv4NativeRoutingCIDR: 10.0.0.0/8
```

Combine esto con la configuración preparada adecuada. Siguen siendo necesarios los requisitos previos de dispositivo para BPF NodePort y las rutas de retorno. ipv4NativeRoutingCIDR controla la exclusión pertinente del masquerading; no crea rutas ni cambia routingMode. Verifique el estado de `cilium-dbg status --verbose` en los nodos seleccionados y `cilium-dbg bpf nat list`, además de realizar una observación externa controlada.

</details>

20. **Describa una secuencia no disruptiva para investigar un comportamiento inesperado de las políticas L7.**

<details>
<summary>Mostrar respuesta</summary>

```bash
cilium status --verbose
kubectl -n kube-system get pods -l k8s-app=cilium -o wide
kubectl -n kube-system get pods -l k8s-app=cilium-envoy -o wide
kubectl -n cilium-l2l7-demo get pods -o wide
export APP_POD=REPLACE-WITH-APP1-POD
export CILIUM_POD=REPLACE-WITH-AGENT-ON-APP-NODE
kubectl -n kube-system exec "$CILIUM_POD" -c cilium-agent -- cilium-dbg status --verbose
kubectl -n kube-system exec "$CILIUM_POD" -c cilium-agent -- \
  cilium-dbg endpoint get "pod-name:cilium-l2l7-demo:$APP_POD"
kubectl -n cilium-l2l7-demo get cnp -o yaml
kubectl get ccnp -o yaml
kubectl -n kube-system logs "$CILIUM_POD" -c cilium-agent --tail=100
```

Para el DaemonSet de Envoy habilitado explícitamente:

```bash
export ENVOY_POD=REPLACE-WITH-ENVOY-POD-ON-APP-NODE
kubectl -n kube-system logs "$ENVOY_POD" --all-containers=true --tail=100
```

```bash
cilium hubble port-forward
```

```bash
hubble observe --namespace cilium-l2l7-demo --protocol http --last 20
hubble observe --namespace cilium-l2l7-demo --verdict DROPPED --last 20
```

Elija los Pods de agente y Envoy del nodo de la carga de trabajo, no un Pod cualquiera del DaemonSet. Para un DaemonSet de Envoy explícito, revise los registros acotados de ese Pod; para Envoy integrado, revise los registros configurados del agente. Mantenga el reenvío de Relay en una terminal separada. Compare las reglas deseadas y aplicadas, la visibilidad de texto claro/TLS, las respuestas de la aplicación y los flujos. Un HTTP403 no equivale a un descarte de paquetes, y la falta de observaciones puede deberse a filtros o pérdida. El antiguo trace de políticas, que ya se eliminó, y la regeneración forzada de endpoints no son pasos iniciales necesarios.

</details>

---

[Volver a los materiales de aprendizaje](../../../networking/cilium/05-l2-l7-networking.md) | [Siguiente cuestionario: seguridad y visibilidad](./06-security-visibility-quiz.md)
