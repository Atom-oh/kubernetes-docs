# Cuestionario de glosario

> **Base de revisión**: Cilium 1.20.3.
> **Última revisión**: 16 de octubre de 2026.

Este cuestionario evalúa tu comprensión de términos y conceptos clave relacionados con Cilium, eBPF, Kubernetes y redes.

## Preguntas de opción múltiple

1. ¿Cuál es el nombre completo de eBPF?

   - A) Enhanced Berkeley Packet Filter
   - B) Extended Berkeley Packet Filter
   - C) Embedded BPF Filter
   - D) External Berkeley Protocol Filter

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Extended Berkeley Packet Filter**

**Explicación:** eBPF amplía el BPF clásico y se utiliza para redes, trazado y otros puntos de enganche del kernel. El verificador comprueba propiedades de los programas; esto no hace que el kernel ni el verificador sean inmunes a errores de implementación.

</details>

2. ¿Cuál es la unidad básica a la que se aplican las políticas de red en Cilium?

   - A) Pod
   - B) Node
   - C) Endpoint
   - D) Service

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: C) Endpoint**

**Explicación:** Un endpoint de Cilium suele corresponder a un Pod administrado. El ID del endpoint es local a su agente; las identidades de seguridad pueden compartirse. Ejecuta `cilium-dbg endpoint list` dentro del agente propietario.

</details>

3. ¿Dónde se ejecuta XDP nativo en un dispositivo de red compatible?

   - A) Análisis de protocolos L7
   - B) Procesamiento de paquetes en la capa del controlador de red
   - C) Cifrado TLS
   - D) Resolución DNS

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Procesamiento de paquetes en la capa del controlador de red**

**Explicación:** XDP nativo se ejecuta en la ruta de recepción de un controlador compatible. `PASS` continúa por la pila; `DROP`, `TX` y `REDIRECT` realizan otras acciones. Los modos genérico y descargado al hardware son distintos. La aceleración de servicios de Cilium depende de las condiciones; no garantiza una tasa de paquetes universal ni protección DDoS integrada.

</details>

4. ¿Cómo se llama la plataforma de observabilidad de red de Cilium?

   - A) Prometheus
   - B) Grafana
   - C) Hubble
   - D) Jaeger

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: C) Hubble**

**Explicación:** Hubble expone registros de flujo, veredictos y métricas de protocolos compatibles mediante la CLI, la interfaz web y las integraciones configuradas. Relay no es almacenamiento duradero; las alertas y la retención externas requieren configuración, y se pueden perder eventos.

</details>

5. ¿Cuál es el nombre completo y el propósito principal de VXLAN?

   - A) Virtual Extended LAN - Creación de una red virtual
   - B) Virtual Extensible LAN - Red superpuesta L2
   - C) Very Extended LAN - Expansión de red a gran escala
   - D) Variable Extensible LAN - Configuración dinámica de red

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Virtual Extensible LAN - Red superpuesta L2**

**Explicación:** VXLAN transporta una red superpuesta L2 sobre una red subyacente IP mediante UDP y un VNI de 24 bits. El campo admite unos 16 millones de valores posibles; esto no es una promesa de capacidad de Cilium. Cilium también transporta información de identidad en los metadatos de la superposición.

</details>

6. ¿Cuál es la función principal de los mapas BPF?

   - A) Administración de tablas de enrutamiento de red
   - B) Intercambio y almacenamiento de datos entre programas eBPF
   - C) Almacenamiento en caché de registros DNS
   - D) Almacenamiento de certificados TLS

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Intercambio y almacenamiento de datos entre programas eBPF**

**Explicación:** Los mapas BPF comparten estado y eventos administrados por el kernel con los programas y el espacio de usuario. Los mapas hash y de matriz usan claves; los búferes circulares y algunos otros tipos de mapa no admiten las operaciones habituales de búsqueda, actualización y eliminación.

</details>

7. ¿Cómo se llama el identificador numérico que representa la identidad de seguridad de un Pod en Cilium?

   - A) Pod ID
   - B) Security Context
   - C) Identity
   - D) Endpoint ID

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: C) Identity**

**Explicación:** Las etiquetas pertinentes para la seguridad determinan la identidad; no participan todas las etiquetas de metadatos. Los endpoints pueden compartir una identidad dentro de su ámbito de asignación. El ID numérico del endpoint es local al agente y constituye un identificador distinto.

</details>

8. ¿Cuál es el nombre completo de IPAM y qué función cumple en Cilium?

   - A) IP Address Management - Asignación y administración de direcciones IP
   - B) Internet Protocol Access Manager - Administración del acceso a Internet
   - C) IP Assignment Module - Módulo de asignación de IP
   - D) Internal Protocol Address Mapper - Asignación interna de direcciones de protocolo

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: A) IP Address Management - Asignación y administración de direcciones IP**

**Explicación:** IPAM asigna y registra direcciones. Según el modo, Cilium admite distintos responsables de la asignación, como cluster-pool, multi-pool, host-scope de Kubernetes y ENI. GKE es una plataforma, no un valor universal e independiente para `ipam.mode`; comprueba la integración con la plataforma administrada.

</details>

9. ¿Cuál es la característica principal de WireGuard y para qué se utiliza en Cilium?

   - A) Herramienta de captura de paquetes - Análisis de red
   - B) Protocolo VPN moderno - Cifrado del tráfico entre nodos
   - C) Algoritmo de balanceo de carga - Distribución del tráfico
   - D) Proxy DNS - Resolución de nombres

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Protocolo VPN moderno - Cifrado del tráfico entre nodos**

**Explicación:** WireGuard de Cilium protege el tráfico compatible entre nodos. El tráfico entre Pods del mismo nodo no atraviesa su túnel; el tráfico externo o dirigido al nodo tiene condiciones distintas. No siempre es más rápido que IPsec; compara cargas de trabajo y ajustes de protección equivalentes.

</details>

10. ¿Cuál es el nombre completo y la función de CNI?

    - A) Container Network Interface - Interfaz estándar para complementos de red de contenedores
    - B) Cloud Native Infrastructure - Infraestructura nativa de la nube
    - C) Cluster Network Integration - Integración de red del clúster
    - D) Container Node Interconnect - Conexión de nodos de contenedores

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: A) Container Network Interface - Interfaz estándar para complementos de red de contenedores**

**Explicación:** CNI especifica la interfaz entre el runtime y los complementos de red. En las versiones actuales de Kubernetes, kubelet usa CRI y el runtime de contenedores administra la invocación de CNI. Las opciones de kubelet para administrar CNI directamente se eliminaron en Kubernetes 1.24.

</details>

## Preguntas de respuesta breve

11. ¿Cómo se llama el componente de código abierto que proporciona funciones de proxy L7 y de service mesh en Cilium?

<details>

<summary>Mostrar respuesta</summary>

**Respuesta:** Envoy

**Explicación:** Envoy proporciona funciones configuradas de proxy HTTP/gRPC. Las políticas DNS usan el proxy DNS de Cilium y se eliminaron las reglas Kafka L7. El despliegue y el ciclo de vida del proxy dependen de la configuración de instalación; no se despliega automáticamente un proxy por cada regla L7 arbitraria.

</details>

12. ¿Cómo se llama el componente de Cilium que se ejecuta en cada nodo y carga programas eBPF, implementa políticas de red y administra endpoints?

<details>

<summary>Mostrar respuesta</summary>

**Respuesta:** Cilium Agent

**Explicación:** El agente administra endpoints locales del nodo, programas BPF y el estado de políticas y del plano de datos en los nodos aptos que administra Cilium. Según el modo, las responsabilidades de IPAM se reparten entre el agente, el operador o la plataforma.

</details>

13. ¿Cuál es el nombre y el número de la capa del modelo OSI responsable del enrutamiento de paquetes mediante direcciones IP?

<details>

<summary>Mostrar respuesta</summary>

**Respuesta:** L3 (Network Layer)

**Explicación:** L3 (capa de red) es la tercera capa del modelo OSI; se encarga del direccionamiento lógico mediante direcciones IP y del enrutamiento de paquetes. IP (Internet Protocol) e ICMP (Internet Control Message Protocol) funcionan en esta capa. Las políticas L3 de Cilium pueden filtrar el tráfico según direcciones IP y bloques CIDR. L2 (capa de enlace de datos) usa direcciones MAC, y L4 (capa de transporte) usa números de puerto.

</details>

14. ¿Cómo se llama el recurso de Kubernetes que proporciona endpoints de red estables para un conjunto de Pods?

<details>

<summary>Mostrar respuesta</summary>

**Respuesta:** Service

**Explicación:** Service proporciona una abstracción de acceso a backends lógicos. Los Services ClusterIP normales tienen una IP virtual; los headless no la tienen, y ExternalName usa un alias DNS. Los Services sin selector pueden representar endpoints externos o administrados manualmente.

</details>

15. ¿Cómo se llama el tipo de NAT que modifica la dirección IP de origen de un paquete?

<details>

<summary>Mostrar respuesta</summary>

**Respuesta:** SNAT (Source Network Address Translation)

**Explicación:** SNAT cambia la dirección de origen. Masquerading elige una dirección asociada a la ruta o interfaz de salida; importan las exclusiones y las IP de gateway seleccionadas. No necesariamente se traduce todo paquete saliente de un Pod. DNAT cambia el destino.

</details>

## Preguntas prácticas

16. Relaciona ClusterMesh, CRD, FQDN y mTLS con sus definiciones.

<details>

<summary>Mostrar respuesta</summary>

**Respuesta:**

- **ClusterMesh**: Metadatos y conectividad de red entre clústeres; no replica automáticamente todos los recursos de políticas.
- **CRD**: Una definición que añade un tipo de recurso personalizado a la API de Kubernetes.
- **FQDN**: Un nombre absoluto dentro del árbol DNS. `toFQDNs` permite usar IP aprendidas.
- **mTLS**: TLS con autenticación mutua entre pares. La autenticación es distinta de la autorización de la aplicación.

</details>


17. Consulta las identidades asignadas mediante CRD y filtra las etiquetas de seguridad reales; distingue la vista local del agente.

<details>

<summary>Mostrar respuesta</summary>

**Respuesta:**

```bash
set -euo pipefail
kubectl get ciliumidentities -o json > identities.json
jq '.items[]
| select(.["security-labels"]["k8s:app"] == "frontend")
| {id: .metadata.name, labels: .["security-labels"]}' identities.json
: "${CILIUM_POD:?Select the Cilium agent Pod on the node being inspected}"
kubectl -n kube-system exec "$CILIUM_POD" -c cilium-agent -- cilium-dbg identity list
kubectl -n kube-system exec "$CILIUM_POD" -c cilium-agent -- cilium-dbg endpoint list
```

Esto supone el modo de asignación mediante CRD. CiliumIdentity tiene ámbito de clúster, y `security-labels` es la fuente de verdad, distinta de `metadata.labels`. No todas las identidades reservadas o locales al nodo se representan como CRD. La vista del agente tiene otro ámbito. Define `CILIUM_POD` mediante el [procedimiento para seleccionar el nodo de destino](../../../networking/cilium/07-advanced-topics.md).

</details>


18. Inspecciona los mapas de servicios, CT, NAT, políticas y endpoints del agente seleccionado.

<details>

<summary>Mostrar respuesta</summary>

**Respuesta:**

```bash
set -eu
: "${CILIUM_POD:?Select the Cilium agent Pod on the node being inspected}"
kubectl -n kube-system exec "$CILIUM_POD" -c cilium-agent -- cilium-dbg bpf lb list
kubectl -n kube-system exec "$CILIUM_POD" -c cilium-agent -- cilium-dbg bpf lb list --backends
kubectl -n kube-system exec "$CILIUM_POD" -c cilium-agent -- cilium-dbg bpf ct list global
kubectl -n kube-system exec "$CILIUM_POD" -c cilium-agent -- cilium-dbg bpf nat list
kubectl -n kube-system exec "$CILIUM_POD" -c cilium-agent -- cilium-dbg bpf policy get --all
kubectl -n kube-system exec "$CILIUM_POD" -c cilium-agent -- cilium-dbg bpf endpoint list
kubectl -n kube-system exec "$CILIUM_POD" -c cilium-agent -- cilium-dbg map list
```

Selecciona primero el agente del nodo propietario. Las opciones `--backends` y `--all` para el mapa de políticas son válidas. Los volcados completos de CT/políticas pueden ser grandes; úsalos de forma deliberada en el nodo afectado. `map list` muestra los mapas abiertos del agente; no es un inventario exhaustivo de mapas del kernel ni demuestra todas las conexiones activas de aplicaciones.

</details>


19. Escribe una política que permita TCP 443 hacia las IP aprendidas para `api.example.com` y nombres `*.googleapis.com` de un nivel, e incluye una excepción DNS. Indica sus límites.

<details>

<summary>Mostrar respuesta</summary>

**Respuesta:**

```yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: fqdn-egress-policy
  namespace: cilium-glossary-demo
spec:
  endpointSelector:
    matchLabels:
      app: external-client
  egress:
  - toEndpoints:
    - matchLabels:
        k8s:io.kubernetes.pod.namespace: kube-system
        k8s:k8s-app: kube-dns
    toPorts:
    - ports:
      - port: '53'
        protocol: UDP
      - port: '53'
        protocol: TCP
      rules:
        dns:
        - matchPattern: '*'
  - toFQDNs:
    - matchName: api.example.com
    - matchPattern: '*.googleapis.com'
    toPorts:
    - ports:
      - port: '443'
        protocol: TCP
```

Este ejercicio solo trata la política. Prepara por separado el namespace, el cliente etiquetado y la ruta real a CoreDNS. Permite DNS por TCP/UDP y la observación del proxy DNS. `*.googleapis.com` coincide con un nivel de subdominio, no con el dominio raíz ni con `a.b.googleapis.com`. DNS `*` permite todos los nombres consultados. `toFQDNs` crea permisos para IP, no una restricción del encabezado HTTPS Host en IP compartidas ni autenticación del servidor remoto. Comprueba las políticas de permiso superpuestas y la validación TLS.

</details>


20. Compara las responsabilidades del operador y del agente, e inspecciona el estado del operador.

<details>

<summary>Mostrar respuesta</summary>

**Respuesta:**

```bash
kubectl -n kube-system get deployment cilium-operator
kubectl -n kube-system get pods -l name=cilium-operator
kubectl -n kube-system logs -l name=cilium-operator -c cilium-operator --prefix --since=10m --tail=100
cilium status --verbose
kubectl get ciliumidentities
kubectl get ciliumendpoints --all-namespaces
```

| Componente | Ámbito y responsabilidades |
| --- | --- |
| Agent | Endpoints de nodos administrados, programas BPF, estado de políticas y del plano de datos, y tareas de IPAM local según el modo. |
| Operator | Registro de CRD a nivel de clúster, IPAM y asignación de IP para balanceadores de carga según el modo, recolección de recursos huérfanos e identidades, y traducción de Ingress/Gateway cuando está habilitada. |

`name=cilium-operator` es válido en el chart actual. `operator.replicas` se puede configurar por encima de una o dos instancias. Por defecto, los agentes crean identidades; la administración de identidades por el operador es un modo Beta independiente. Las funciones habilitadas también pueden añadir sincronización de EndpointSlice/MCS de ClusterMesh, por lo que las responsabilidades no deben tratarse como una lista incondicional.

</details>


***

[Volver al material de aprendizaje](../../../networking/cilium/glossary.md) | [Lista de cuestionarios de Cilium](../../README.md#cilium)
