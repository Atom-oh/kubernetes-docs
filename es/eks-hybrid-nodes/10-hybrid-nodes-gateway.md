# Gateway de EKS Hybrid Nodes

< [Anterior: Configuración del sistema operativo en bare metal](./09-bare-metal-os-setup.md) | [Tabla de contenido](./README.md) >

> **Base de validación**: Gateway/chart 1.0.2; use una versión de Kubernetes compatible con EKS y una versión de Cilium mantenida por AWS que cumpla los requisitos previos del gateway.
> **Última actualización**: 18 de octubre de 2026

---

## Descripción general

EKS Hybrid Nodes Gateway es un componente de red de código abierto que automatiza la conectividad entre la VPC de Amazon y los Pods de Kubernetes que se ejecutan en Hybrid Nodes en entornos locales o perimetrales. Se anunció como disponible de forma general el 21 de abril de 2026. El gateway automatiza las rutas de Pods que administra y el estado de reenvío VXLAN. La conectividad de la red subyacente, la propiedad del enrutamiento, la planificación del firewall/MTU, el despliegue progresivo y la limpieza aún requieren configuración explícita.

El gateway establece túneles VXLAN entre instancias dedicadas de EC2 en la VPC y los Hybrid Nodes administrados por Cilium en las instalaciones. Programa automáticamente las tablas de rutas de la VPC, administra las entradas de la base de datos de reenvío (FDB) y configura la integración de Cilium VTEP (VXLAN Tunnel Endpoint) para que los Pods de la VPC puedan comunicarse directamente con los Pods de Hybrid Nodes. El reenvío satisfactorio sigue dependiendo de la configuración revisada de la red subyacente, CNI, IAM, reglas de seguridad y rutas de las aplicaciones.

**Características principales:**

- **Código abierto**: Disponible íntegramente en [github.com/aws/eks-hybrid-nodes-gateway](https://github.com/aws/eks-hybrid-nodes-gateway)
- **Sin cargo por el software del gateway**: EC2, almacenamiento, tarifas de Auto Mode (solo si los nodos del gateway se ejecutan en Auto Mode; también funcionan los grupos de nodos administrados o autoadministrados), tráfico entre zonas de disponibilidad, conectividad y observabilidad siguen generando costos
- **Administración automatizada de rutas**: el líder programa las rutas agregadas configuradas para los Pods de la VPC; cada réplica reconcilia por separado el estado local del túnel de cada CiliumNode
- **Alta disponibilidad**: admite un Deployment de 2 réplicas con elección de líder basada en Lease para la conmutación por error
- **Integración con Cilium**: aprovecha la función VTEP de Cilium para permitir el enrutamiento transparente de Pod a Pod a través del túnel VXLAN

### Objetivos de aprendizaje

Al terminar este documento, podrá:

1. **Explicar la arquitectura** de EKS Hybrid Nodes Gateway, incluidos los túneles VXLAN, la elección de líder y la administración de rutas de la VPC.
2. **Implementar y configurar** el gateway con Helm, incluidos los roles de IAM, los grupos de seguridad y la integración con Cilium VTEP.
3. **Seguir los flujos de tráfico** en ambas direcciones entre los Pods de la VPC y los Pods de Hybrid Nodes.
4. **Implementar alta disponibilidad** con despliegues de gateway de varias réplicas y comprender el comportamiento de conmutación por error.
5. **Operar y solucionar problemas** de los despliegues del gateway, incluida la supervisión, el escalado y los escenarios de fallo comunes.
6. **Comparar enfoques** de red para Hybrid Nodes y decidir cuándo usar el gateway frente al enrutamiento manual.
7. **Aplicar prácticas recomendadas** de seguridad, rendimiento y optimización de costos en despliegues de gateway de producción.

### El problema: enrutamiento manual de Pods en entornos Hybrid

Antes de que estuviera disponible el gateway, habilitar la comunicación a nivel de Pod entre la VPC y Hybrid Nodes exigía un esfuerzo manual considerable:

```
Before Gateway (Manual Approach):
=================================

1. Configure BGP peering between on-prem routers and VPC (or use static routes)
2. Manually manage VPC route table entries for every hybrid Pod CIDR
3. Set up and maintain VPN tunnels or Direct Connect with proper route propagation
4. Handle route updates when nodes join/leave the cluster
5. Troubleshoot routing asymmetries and MTU issues across multiple hops
6. Maintain custom scripts or controllers to keep routes in sync

After Gateway (Automated Approach):
====================================

1. Deploy gateway via Helm chart
2. Gateway automatically:
   - Creates VXLAN tunnels to hybrid nodes
   - Programs VPC route table entries
   - Configures Cilium VTEP for transparent routing
   - Handles failover via leader election
   - Updates routes as nodes come and go
```

El gateway convierte un desafío de red complejo, propenso a errores y que involucra a varios equipos en una sola instalación de Helm con unos pocos valores de configuración.

---

## Análisis detallado de la arquitectura

### Arquitectura de alto nivel

EKS Hybrid Nodes Gateway se sitúa en el límite entre la VPC y la red local y actúa como puente VXLAN para el tráfico de Pods. El siguiente diagrama muestra la arquitectura general:

![Los gateways líder y en espera, alojados en instancias EC2 de la nube, mantienen el estado local de los túneles; las rutas configuradas de la VPC dirigen el tráfico al líder activo.](../.gitbook/assets/en-eks-hybrid-nodes-10-hybrid-nodes-gateway-0.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-hybrid-nodes-10-hybrid-nodes-gateway-0.html)

### Mecánica del túnel VXLAN

El gateway usa VXLAN (Virtual Extensible LAN) para encapsular el tráfico de Pods entre la VPC y los entornos locales. Así se establece y mantiene el túnel:

#### Interfaz VXLAN del gateway

Cuando el Pod del gateway se inicia en una instancia EC2, crea una interfaz de red `hybrid_vxlan0` con los siguientes parámetros:

| Parámetro | Valor | Descripción |
|-----------|-------|-------------|
| **Nombre de interfaz** | `hybrid_vxlan0` | Interfaz de túnel VXLAN del gateway |
| **VNI (VXLAN Network Identifier)** | 2 | Valor predeterminado del gateway, compatible con la ruta de Cilium VTEP; no es un campo de CiliumVTEPConfig |
| **Puerto UDP** | 8472 | Puerto VXLAN del gateway/Cilium; el puerto asignado por IANA a VXLAN es 4789 |
| **IP local** | IP privada de la instancia EC2 del gateway | IP de origen de los paquetes encapsulados en VXLAN |
| **Aprendizaje** | Deshabilitado | El gateway programa estáticamente las entradas FDB |

El gateway crea esta interfaz mediante netlink. Lo siguiente es una ilustración conceptual, no un comando que deba ejecutarse junto al controlador. La versión 1.0.2 no asigna una dirección IP a esta interfaz; el túnel externo usa la IP privada del nodo del gateway.

```bash
# Conceptual equivalent of what the gateway does programmatically
ip link add hybrid_vxlan0 type vxlan \
    id 2 \
    local <gateway-private-ip> \
    dstport 8472 \
    nolearning

ip link set hybrid_vxlan0 up
```

#### Programación de FDB, ARP y rutas

El reconciliador de nodos observa los objetos `CiliumNode` etiquetados con `eks.amazonaws.com/compute-type: hybrid`. Se ejecuta en cada réplica del gateway y programa tres tipos de entradas locales a partir de la IP interna del nodo y del CIDR de Pods asignado:

```text
Per Hybrid Node, the gateway programs:
=======================================

1. FDB (Forwarding Database) Entry:
   deterministic node MAC → hybrid node's internal IP
   → Tells the VXLAN interface where to send encapsulated frames for this node

2. ARP Entry:
   hybrid node's internal IP → deterministic node MAC
   → Pre-populates ARP so the gateway can immediately forward packets without ARP discovery

3. Route Entry:
   hybrid node's Pod CIDR via its internal IP, dev hybrid_vxlan0, onlink
   → Directs Pod traffic for this node's CIDR through the VXLAN tunnel
```

El controlador deriva la MAC remota de la dirección IPv4 del nodo en lugar de descubrir la MAC de una interfaz de Cilium. Las entradas estáticas de vecino/FDB evitan depender del aprendizaje dinámico para esta ruta. Los errores de reconciliación, las entradas obsoletas y los fallos de la red subyacente aún pueden interrumpir el reenvío. Estas rutas locales son distintas de las entradas de la tabla de rutas de la VPC.

#### Lado del Hybrid Node (Cilium VTEP)

En el lado del Hybrid Node, la función VTEP (VXLAN Tunnel Endpoint) de Cilium gestiona la terminación del túnel. El gateway se registra como VTEP remoto mediante el recurso personalizado `CiliumVTEPConfig`. Esto indica a cada agente de Cilium en los Hybrid Nodes que:

1. El tráfico destinado a los CIDR de la VPC se debe encapsular con VXLAN.
2. El tráfico encapsulado se debe enviar a la dirección IP del gateway.
3. El túnel VXLAN usa VNI 2 en el puerto UDP 8472.

```yaml
# CiliumVTEPConfig created and managed by the gateway
apiVersion: cilium.io/v2
kind: CiliumVTEPConfig
metadata:
  name: hybrid-gateway
spec:
  endpoints:
    - name: vpc-gateway
      tunnelEndpoint: "10.0.1.5"      # Actual leader node IP
      cidr: "10.0.0.0/16"            # One VPC prefix per endpoint
      mac: "82:36:6c:89:e6:ad"       # Illustrative; read the leader's actual VXLAN MAC
```

Cuando un Pod de un Hybrid Node envía tráfico a una dirección IP de la VPC (por ejemplo, a un Pod del lado de la nube o a un endpoint de servicio de AWS), el agente de Cilium:

1. Compara el destino con un `cidr` de endpoint en CiliumVTEPConfig.
2. Encapsula el paquete con VXLAN y VNI 2.
3. Envía el paquete UDP externo a la IP del gateway por el puerto 8472.
4. El gateway desencapsula el paquete y reenvía el paquete interno a la VPC.

### Elección de líder y alta disponibilidad

El chart configura de forma predeterminada un Deployment de dos réplicas. Ambas réplicas mantienen sus propias rutas, entradas FDB y de vecino VXLAN locales. Solo el líder actualiza las rutas de la VPC de AWS y el recurso `CiliumVTEPConfig` llamado `hybrid-gateway`, que administra el controlador.

#### Elección de líder basada en Lease

La elección de líder usa el recurso Lease estándar de Kubernetes:

```yaml
apiVersion: coordination.k8s.io/v1
kind: Lease
metadata:
  name: hybrid-gateway-leader
  namespace: eks-hybrid-nodes-gateway
spec:
  holderIdentity: "gateway-node-hostname_example-uuid"
  leaseDurationSeconds: 3
  acquireTime: "2026-06-28T10:00:00Z"
  renewTime: "2026-06-28T10:00:10Z"
  leaseTransitions: 3
```

Este Lease es una observación ilustrativa, no un manifiesto que se deba aplicar. La identidad del titular no es necesariamente el nombre de un Pod; antes de realizar cualquier operación, identifique el nodo/Pod correspondiente. Estos indicadores binarios controlan el intervalo de elección; el chart 1.0.2 no expone un objeto de valores `leaderElection`:

| Parámetro | Valor predeterminado | Descripción |
|-----------|---------------|-------------|
| `--leader-election-lease-duration` | 3s | Duración del Lease de elección |
| `--leader-election-renew-deadline` | 2s | Plazo para renovar el Lease del líder |
| `--leader-election-retry-period` | 1s | Intervalo de reintento de la elección |

#### Funciones del líder

El Pod líder se encarga de:

1. **Administración de las tablas de rutas de la VPC**: crea y actualiza rutas en las tablas de rutas de la VPC especificadas para dirigir los CIDR de Pods Hybrid a la ENI de la instancia EC2 del líder.
2. **Administración de CiliumVTEPConfig**: crea y actualiza el recurso CiliumVTEPConfig para dirigir el tráfico VTEP de los nodos Hybrid a la IP de la instancia EC2 del líder.
3. **Programación de FDB/ARP/rutas**: programa la interfaz VXLAN local con entradas de todos los nodos Hybrid.
4. **Observación de nodos**: como la réplica en espera, observa los objetos CiliumNode y actualiza las entradas locales de túnel. No crea ni elimina una ruta de AWS por cada evento de nodo.

#### Funciones de la réplica en espera

El Pod en espera:

1. **Mantiene el túnel VXLAN**: conserva activa su interfaz `hybrid_vxlan0` y la configura con entradas FDB/ARP/rutas.
2. **No programa rutas de la VPC**: solo el líder modifica las tablas de rutas de la VPC.
3. **No actualiza CiliumVTEPConfig**: solo el líder actualiza la configuración de VTEP.
4. **Supervisa el Lease**: intenta adquirir el Lease continuamente en caso de que falle el líder.

### Administración automática de las tablas de rutas de la VPC

Al asumir el liderazgo, el gateway crea o reemplaza rutas para los `podCIDRs` agregados configurados en cada tabla de rutas indicada. Primero actualiza las rutas de AWS y después actualiza CiliumVTEPConfig. La reconciliación de CiliumNode mantiene por separado las entradas locales de túnel de cada nodo en todas las réplicas.

![Los eventos de CiliumNode actualizan las entradas locales del túnel en todas las réplicas. La configuración independiente del líder actualiza las rutas agregadas de AWS y después los endpoints de VTEP; no elimina rutas de AWS cuando se retira cada nodo.](../.gitbook/assets/en-eks-hybrid-nodes-10-hybrid-nodes-gateway-1.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-hybrid-nodes-10-hybrid-nodes-gateway-1.html)

El gateway usa la API de EC2 para administrar rutas:

| Llamada a la API | Cuándo se usa | Propósito |
|----------|-----------|---------|
| `ec2:DescribeRouteTables` | Comprobación de acceso y configuración inicial del líder | Leer las tablas de rutas configuradas explícitamente |
| `ec2:CreateRoute` | Configuración inicial del líder cuando falta una ruta CIDR configurada | Agregar la ruta agregada del CIDR de Pods |
| `ec2:ReplaceRoute` | Configuración inicial del líder cuando su destino es distinto | Dirigir la ruta configurada a la ENI principal del líder actual |
| `ec2:DescribeInstances` | Inicio y conmutación por error | Descubrir los ID de las ENI de las instancias EC2 del gateway |

El runtime del gateway no llama a `DeleteRoute`. La eliminación de Helm no limpia las rutas de AWS. Se pueden reemplazar rutas existentes para el mismo CIDR aunque las haya creado otro sistema: antes de la instalación, revise quién es su propietario y el plan de transición/reversión.

Estos contratos se verificaron con la [implementación 1.0.2](https://github.com/aws/eks-hybrid-nodes-gateway/tree/v1.0.2/internal) y la [guía de operaciones de AWS](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-gateway-operations.html). Las lecturas de la API, el estado de disponibilidad o una métrica del líder por sí solos no demuestran que el reenvío de extremo a extremo funcione.

### Resumen de la interacción entre componentes

El siguiente diagrama muestra cómo interactúan todos los componentes:

![Las réplicas del gateway observan CiliumNode en los nodos de trabajo EC2 de la nube, mientras el líder programa las rutas agregadas de AWS y los endpoints de CiliumVTEPConfig.](../.gitbook/assets/en-eks-hybrid-nodes-10-hybrid-nodes-gateway-2.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-hybrid-nodes-10-hybrid-nodes-gateway-2.html)

---

## Requisitos previos

Antes de desplegar EKS Hybrid Nodes Gateway, asegúrese de cumplir todos los requisitos previos siguientes.

### Configuración del clúster de EKS

| Requisito | Detalles |
|-------------|---------|
| **Versión de EKS** | Una versión compatible actualmente con EKS y los complementos elegidos |
| **Familia de direcciones** | IPv4; redes de VPC, Service, nodo remoto y Pod remoto que no se superpongan |
| **Hybrid Nodes** | Al menos un Hybrid Node configurado e incorporado al clúster |
| **Modo de autenticación** | `API` o `API_AND_CONFIG_MAP` |
| **Acceso al endpoint** | Solo público o solo privado (no «público y privado») |
| **Red de Pods remota** | CIDR de Pods configurados para los nodos Hybrid del clúster |

### Requisitos del CNI

El gateway requiere una configuración específica del CNI:

| Ubicación | CNI | Versión | Compatibilidad con VTEP |
|----------|-----|---------|--------------|
| **Nodos de la nube administrados/autoadministrados** | Amazon VPC CNI | Versión de complemento compatible; configure la exclusión de SNAT de ClusterIP de Hybrid | No se requiere |
| **Nodos de la nube en Auto Mode** | Redes integradas | Use la configuración compatible con Auto Mode | No se requiere |
| **Nodos Hybrid** | Cilium mantenido por AWS | Cumpla el mínimo de rama indicado en [Configuración del CNI](#cni-configuration) | VTEP habilitado; proxy L7 deshabilitado |

> Esta implementación del gateway requiere la integración VTEP de Cilium mantenida por AWS; no es un controlador compatible con Calico. Si los requisitos de CNI/L7 no se ajustan, use un diseño compatible independiente de Pods enrutables. Los [requisitos de creación del clúster Hybrid](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-cluster-create.html) exigen autenticación API/API_AND_CONFIG_MAP, IPv4 y conectividad del endpoint solo pública o solo privada para Hybrid Nodes.

### Conectividad de red

La conectividad privada entre la VPC y el entorno local debe estar establecida previamente:

| Tipo de conectividad | Cuándo se usa | Notas |
|-------------------|-------------|-------|
| **AWS Direct Connect** | Cargas de trabajo de producción que requieren baja latencia constante | Conectividad dedicada; la resiliencia y la latencia dependen del diseño redundante real |
| **AWS Site-to-Site VPN** | Conectividad híbrida estándar | Conectividad IPsec; el rendimiento depende de la oferta de túnel elegida, la combinación de paquetes y el enrutamiento |
| **Transit Gateway + VPN** | Entornos con varias VPC | Terminación centralizada de VPN; admite ECMP para un mayor rendimiento |
| **VPN personalizada (por ejemplo, WireGuard)** | Requisitos especializados | Túnel autoadministrado; útil cuando preocupan las limitaciones de AWS VPN |

> **Nota**: el gateway no establece la conectividad básica entre la VPC y las instalaciones. Agrega una superposición VXLAN sobre la conectividad existente para enrutar Pods.

### Instancias EC2 del gateway

Se necesitan al menos dos instancias EC2 en la VPC para ejecutar los Pods del gateway:

```yaml
# Recommended EC2 instance configuration for gateway nodes
Instance type: c6i.large (2 vCPU, 4 GiB RAM) or larger
AMI: Amazon Linux 2023 (EKS optimized)
Placement: Spread across at least 2 Availability Zones
EBS: 20 GiB gp3 (minimal storage needed)
```

Las instancias del gateway deben:

1. Ser nodos EC2 de la nube registrados; distinga Amazon VPC CNI de los nodos administrados/autoadministrados y las redes integradas de Auto Mode.
2. Tener el rol de nodo apropiado y un rol de carga de trabajo del gateway con alcance independiente (consulte [Configuración de IAM](#iam-configuration)).
3. Tener etiquetas para programar los Pods del gateway (consulte [Instalación](#installation-and-configuration)).

### Configuración de grupos de seguridad

Use los CIDR reales de nodos/Pods y los puertos revisados. El puerto UDP 8472 por sí solo no establece todas las rutas de la aplicación o del plano de control. Revise por separado estos flujos:

| Flujo | Comprobación requerida |
|---|---|
| IP principal del gateway ↔ IP del nodo Hybrid | UDP 8472 de VXLAN externo en ambas direcciones |
| Cargas de trabajo de la nube ↔ Pods Hybrid | Protocolos/puertos internos previstos de la aplicación y su tráfico de retorno |
| Nodos → API de Kubernetes, API/registro de AWS y DNS | Endpoints/resolutores reales, TCP 443 y rutas DNS necesarias |
| Plano de control → kubelet | TCP 10250 hacia los nodos previstos; independiente del tráfico saliente del nodo hacia la API por TCP 443 |
| Prometheus → gateway | Restrinja TCP 10080 al origen de recopilación previsto |

Tenga en cuenta por separado los grupos de seguridad, las NACL sin estado y los firewalls locales. No agregue reglas de entrada generales para toda la VPC como sustituto de los flujos de aplicación necesarios. Proteja las direcciones IP de todos los nodos que puedan ser líderes, incluida la capacidad de reemplazo.

#### Ejemplo de grupo de seguridad con Terraform

Administre la matriz de reglas aprobada en la pila de Terraform existente para los nodos/la red. Una regla UDP exclusiva del gateway es un fragmento, no un grupo de seguridad completo para los nodos. Conserve los requisitos existentes del clúster para el arranque, DNS, API y aplicaciones, e inspeccione el plan final; no cree un grupo de seguridad duplicado sin restricciones suponiendo que una regla VXLAN lo hace seguro.

### Configuración del firewall local

Use las **IP privadas de nodo** del gateway, accesibles por la red subyacente privada, no las IP elásticas. Permita la ruta UDP 8472 necesaria para cada líder/réplica en espera elegible y revise por separado los flujos de API de Kubernetes/kubelet, DNS y aplicaciones. Concilie las actualizaciones del firewall cuando Auto Mode u otro administrador de nodos reemplace instancias del gateway. Ni este capítulo ni una tabla estática de grupos de seguridad demuestran cuál es la ruta real del firewall.

Verifique la comprobación de origen/destino en la ENI principal prevista. Auto Mode usa el ajuste de reenvío de NodeClass; el aprovisionamiento administrado/autoadministrado es responsable de cualquier modificación requerida de la ENI. Lo siguiente solo lee su valor actual:

```bash
: "${AWS_REGION:?Set the reviewed Region}"
: "${GATEWAY_PRIMARY_ENI_ID:?Set the verified gateway primary ENI}"
aws ec2 describe-network-interface-attribute --region "$AWS_REGION" \
  --network-interface-id "$GATEWAY_PRIMARY_ENI_ID" --attribute sourceDestCheck
```

### Consideraciones sobre MTU

VXLAN IPv4 suele agregar 50 bytes, incluido el encabezado Ethernet interno. Use la MTU efectiva de extremo a extremo de la red subyacente, no la MTU máxima de la interfaz EC2. Las siguientes cifras originales de MTU son ilustraciones de planificación, no resultados de medición de la ruta ni ajustes universales de DX/VPN:

| Componente | MTU recomendada | Notas |
|-----------|----------------|-------|
| Instancia EC2 del gateway | 9001 (tramas gigantes) | Valor predeterminado de la mayoría de los tipos de instancia EC2 en una VPC |
| Nodos Hybrid locales | 1500 o superior | Depende de la infraestructura de red |
| Interfaz VXLAN (efectiva) | MTU de la ruta − 50 | Por ejemplo, 1450 si la MTU de la ruta es 1500 |
| Direct Connect | 9001 (tramas gigantes) | Si la conexión DX lo admite |
| Túnel VPN | 1399–1500 | Varía según la configuración de VPN |

Si la ruta de red entre la VPC y las instalaciones usa una MTU estándar de 1500:

```
Effective Pod MTU calculation:
Physical MTU:        1500 bytes
VXLAN overhead:      - 50 bytes (outer IP + outer UDP + VXLAN header)
VPN overhead (IPsec): - 57-73 bytes (if applicable)
Effective Pod MTU:   ~1377-1450 bytes
```

Cilium en los nodos Hybrid se puede configurar con la MTU adecuada:

```yaml
# Cilium Helm values for hybrid nodes
mtu: 1400  # Illustrative only; replace using validated path MTU and chosen Cilium datapath.
```

---

## Configuración de IAM {#iam-configuration}

### Permisos IAM requeridos

Separe el rol de carga de trabajo del gateway del rol de nodo EC2 y de los permisos de aprovisionamiento/limpieza del operador. La [guía de inicio de AWS](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-gateway-getting-started.html) recomienda EKS Pod Identity. Su agente debe estar disponible en los nodos administrados/autoadministrados elegibles; Auto Mode proporciona compatibilidad con Pod Identity. No cree a ciegas un complemento encima de una instalación existente.

Las acciones del runtime del gateway son `ec2:DescribeRouteTables`, `ec2:DescribeInstances`, `ec2:CreateRoute` y `ec2:ReplaceRoute`. Las operaciones Describe requieren `Resource: "*"`; restrinja la región. Para escribir rutas se pueden usar los ARN exactos de las tablas de rutas y una condición de VPC. Eliminar rutas obsoletas es una acción del operador, no un permiso del runtime.

### Política IAM de alcance limitado (recomendada para producción)

Después de reemplazar la cuenta, la región, la VPC y los ID de las tablas de rutas con el inventario revisado, guarde lo siguiente como `gateway-permissions.json`. Son identificadores ilustrativos, no recursos aprovisionados durante esta auditoría. La política no restringe qué CIDR de destino puede modificar el rol dentro de esas tablas de rutas: considérelas un límite de seguridad de enrutamiento y controle quién puede editar los valores del Gateway o usar su ServiceAccount.

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "ReadGatewayRoutingMetadata",
      "Effect": "Allow",
      "Action": [
        "ec2:DescribeRouteTables",
        "ec2:DescribeInstances"
      ],
      "Resource": "*",
      "Condition": {
        "StringEquals": {
          "aws:RequestedRegion": "ap-northeast-2"
        }
      }
    },
    {
      "Sid": "ManageOnlyOwnedRouteTables",
      "Effect": "Allow",
      "Action": [
        "ec2:CreateRoute",
        "ec2:ReplaceRoute"
      ],
      "Resource": [
        "arn:aws:ec2:ap-northeast-2:111122223333:route-table/rtb-0abc123456789def0",
        "arn:aws:ec2:ap-northeast-2:111122223333:route-table/rtb-0def456789abc1230"
      ],
      "Condition": {
        "StringEquals": {
          "ec2:Vpc": "arn:aws:ec2:ap-northeast-2:111122223333:vpc/vpc-0123456789abcdef0"
        }
      }
    }
  ]
}
```

El alcance mediante ARN de tabla de rutas y `ec2:Vpc` sigue el [ejemplo de política de tablas de rutas de EC2](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ExamplePolicies_EC2.html). Una solicitud Describe satisfactoria no demuestra autorización para CreateRoute/ReplaceRoute. Antes de la transición, pruebe la autorización y la propiedad de las rutas en un entorno aprobado.

### Configuración IAM con Terraform

Para Pod Identity, guarde esta política de confianza como `gateway-trust.json` después de reemplazar el ARN exacto del clúster. Las etiquetas de sesión deben permanecer habilitadas porque las condiciones vinculan el clúster, el espacio de nombres y el ServiceAccount. Además de los permisos de IAM, restrinja la creación de Pods/ServiceAccounts y la administración de asociaciones de Pod Identity.

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "pods.eks.amazonaws.com"
      },
      "Action": [
        "sts:AssumeRole",
        "sts:TagSession"
      ],
      "Condition": {
        "StringEquals": {
          "aws:RequestTag/eks-cluster-arn": "arn:aws:eks:ap-northeast-2:111122223333:cluster/hybrid-production",
          "aws:RequestTag/kubernetes-namespace": "eks-hybrid-nodes-gateway",
          "aws:RequestTag/kubernetes-service-account": "eks-hybrid-nodes-gateway"
        }
      }
    }
  ]
}
```

La [política de confianza de Pod Identity](https://docs.aws.amazon.com/eks/latest/userguide/pod-id-role.html) y las [etiquetas de sesión](https://docs.aws.amazon.com/eks/latest/userguide/pod-id-abac.html) definen estas condiciones. El siguiente HCL es un fragmento de integración, no una pila completa de proveedor/clúster; para cada recurso, use la administración de Terraform o la ruta de CLI.

```hcl
# Fragment in the existing reviewed AWS provider/cluster stack.
# Declare and validate these variables; do not create duplicate CLI-managed resources.
resource "aws_iam_role" "gateway" {
  name               = var.gateway_role_name
  assume_role_policy = file("${path.module}/gateway-trust.json")
}
resource "aws_iam_role_policy" "gateway_routes" {
  name   = "GatewayOwnedRoutes"
  role   = aws_iam_role.gateway.id
  policy = file("${path.module}/gateway-permissions.json")
}
resource "aws_eks_pod_identity_association" "gateway" {
  cluster_name    = var.cluster_name
  namespace       = "eks-hybrid-nodes-gateway"
  service_account = "eks-hybrid-nodes-gateway"
  role_arn        = aws_iam_role.gateway.arn
}
```

### Configuración de IAM con AWS CLI

Prepare el rol con el JSON de confianza/permisos revisado junto con el responsable de IAM. El nombre de ServiceAccount de la asociación debe coincidir con el del chart renderizado; los cambios en el nombre/las anulaciones de la versión de Helm pueden modificarlo. La configuración de la asociación es independiente de los valores del chart: la versión 1.0.2 ignora `serviceAccount.annotations`.

```bash
: "${AWS_REGION:?Set the reviewed Region}"
: "${CLUSTER_NAME:?Set the reviewed cluster}"
: "${GATEWAY_ROLE_ARN:?Set the prepared, scoped Pod Identity role ARN}"
# Inspect existing associations; do not create a duplicate or replace another owner.
aws eks list-pod-identity-associations --region "$AWS_REGION" \
  --cluster-name "$CLUSTER_NAME" --namespace eks-hybrid-nodes-gateway \
  --service-account eks-hybrid-nodes-gateway
# Run only for the reviewed new association; keep session tags enabled:
aws eks create-pod-identity-association --region "$AWS_REGION" \
  --cluster-name "$CLUSTER_NAME" --namespace eks-hybrid-nodes-gateway \
  --service-account eks-hybrid-nodes-gateway --role-arn "$GATEWAY_ROLE_ARN" \
  --no-disable-session-tags
```

IRSA sigue siendo una alternativa, pero requiere una política de confianza OIDC real y una anotación en el ServiceAccount renderizado, administradas mediante un parche/superposición revisado; un valor que Helm ignora no puede establecer IRSA. Evite asociar permisos para escribir rutas de forma generalizada a todas las cargas de trabajo de los nodos. Las consultas del binario a los metadatos de EC2 para obtener la identidad del nodo y la cadena de credenciales del SDK son aspectos independientes; no deshabilite los metadatos a ciegas sin proporcionar y verificar los datos de identidad requeridos por el nodo.

El reenvío de Auto Mode usa `NodeClass.spec.advancedNetworking.sourceDestCheck: DisabledPrimaryENI`. El arranque de los nodos administrados/autoadministrados debe deshabilitar la comprobación de origen/destino en la ENI principal prevista mediante permisos independientes y de alcance limitado para nodos/operadores. `ModifyNetworkInterfaceAttribute` y la creación de clúster/rol/complemento no forman parte de la política de carga de trabajo del gateway anterior.

---

## Instalación y configuración {#installation-and-configuration}

### Paso 1: Etiquetar los nodos del gateway

Primero aprovisione nodos EC2 elegibles de la nube. Para los nodos administrados/autoadministrados, use `autoMode.enabled=false`; Auto Mode necesita un NodeClass/NodePool preparado y `autoMode.enabled=true`. Etiquete únicamente los nodos cuyos requisitos de reenvío, grupos de seguridad e IAM se hayan verificado. No invente etiquetas de tipos de instancia ni de zonas de disponibilidad administradas por el proveedor. Se prefieren dos nodos elegibles en distintas zonas de disponibilidad.

```bash
: "${KUBE_CONTEXT:?Set the reviewed Kubernetes context}"
: "${GW_NODE_A:?Set the first eligible gateway node}"
: "${GW_NODE_B:?Set the second eligible gateway node}"
kubectl --context "$KUBE_CONTEXT" get node "$GW_NODE_A" "$GW_NODE_B" \
  -L topology.kubernetes.io/zone,eks.amazonaws.com/compute-type
# Apply only after source/destination check, IAM and network prerequisites are met:
kubectl --context "$KUBE_CONTEXT" label node "$GW_NODE_A" "$GW_NODE_B"   hybrid-gateway-node=true
```

### Paso 2: Recopilar los valores de configuración

Confirme la cuenta de AWS, la VPC del clúster, los CIDR de Pods remotos, las ENI reales del gateway y las tablas de rutas afectadas de las subredes/el plano de control. Seleccione solo las tablas de rutas que pertenezcan a este diseño de enrutamiento; enumerar todas las tablas de una VPC no autoriza a modificarlas todas. `remoteNetworkConfig` va directamente bajo `cluster`, no bajo `kubernetesNetworkConfig`.

```bash
: "${AWS_REGION:?Set the reviewed AWS Region}"
: "${CLUSTER_NAME:?Set the reviewed EKS cluster}"
: "${VPC_ID:?Set the cluster VPC ID}"
aws sts get-caller-identity --query Account --output text
aws eks describe-cluster --region "$AWS_REGION" --name "$CLUSTER_NAME" \
  --query 'cluster.{VpcId:resourcesVpcConfig.vpcId,RemotePodCIDRs:remoteNetworkConfig.remotePodNetworks[].cidrs[]}' \
  --output json
aws ec2 describe-vpcs --region "$AWS_REGION" --vpc-ids "$VPC_ID" \
  --query 'Vpcs[].CidrBlockAssociationSet[].{CIDR:CidrBlock,State:CidrBlockState.State}' \
  --output json
aws ec2 describe-route-tables --region "$AWS_REGION" \
  --filters "Name=vpc-id,Values=$VPC_ID" \
  --query 'RouteTables[].{ID:RouteTableId,Associations:Associations,Routes:Routes}' \
  --output json
```

### Paso 3: Instalar con Helm

Complete los pasos de CNI, nodo e IAM de la carga de trabajo antes de la instalación. Es posible que el líder reemplace inmediatamente las rutas existentes de los CIDR configurados. Después de revisar la propiedad, el enrutamiento de retorno y la reversión, use el archivo de valores de abajo. Este capítulo valida la configuración localmente; no indica que se haya realizado un despliegue activo.

### Referencia completa de valores de Helm

El chart publicado 1.0.2 requiere **cadenas CSV**, no matrices YAML, para `podCIDRs` y `routeTableIDs`. Use un archivo de valores para que el análisis de listas/comas de `helm --set` no cambie sus tipos.

```yaml
# values.yaml: replace CIDRs/table IDs from the reviewed network inventory.
vpcCIDR: "10.0.0.0/16"
podCIDRs: "10.85.0.0/16"
routeTableIDs: "rtb-0abc123456789def0,rtb-0def456789abc1230"
replicas: 2
nodeLabel: hybrid-gateway-node
autoMode:
  enabled: false  # MNG/self-managed. Set true only for prepared Auto Mode nodes.
```

El chart también admite `image.repository`, `image.tag`, `image.pullPolicy` y auxiliares de nomenclatura. Sus plantillas **no usan** los valores `replicaCount`, `nodeSelector`, `resources`, `affinity`, `topologySpreadConstraints`, `serviceAccount.annotations`, `leaderElection`, `logLevel`, `metrics`, `extraEnv` ni los volúmenes personalizados. No interprete que se haya aplicado un ajuste solo porque el YAML lo acepte. Configure la identidad de la carga de trabajo por separado; si hace falta un post-renderer mantenido para otro ajuste, revise expresamente el Deployment resultante y su comportamiento al actualizarlo.

Ambos modos usan red del host, NET_ADMIN, anti-afinidad de host obligatoria y anti-afinidad de zona de disponibilidad preferida. El chart no crea un Service, ServiceMonitor ni PDB. Auto Mode usa maxSurge=1/maxUnavailable=0; los demás nodos usan 0/1. Ninguna estrategia tiene en cuenta al líder ni garantiza que el reenvío no se interrumpa. El despliegue maxSurge de Auto Mode requiere otro nodo elegible debido a la anti-afinidad de host.

```bash
: "${KUBE_CONTEXT:?Set the reviewed Kubernetes context}"
# Local rendering first; it does not prove API admission, IAM or network readiness.
helm template eks-hybrid-nodes-gateway \
  oci://public.ecr.aws/eks/eks-hybrid-nodes-gateway \
  --version 1.0.2 --namespace eks-hybrid-nodes-gateway \
  --values values.yaml > gateway-rendered.yaml
# Creates/changes cluster resources and can redirect existing VPC routes:
helm upgrade --install eks-hybrid-nodes-gateway \
  oci://public.ecr.aws/eks/eks-hybrid-nodes-gateway \
  --version 1.0.2 --namespace eks-hybrid-nodes-gateway --create-namespace \
  --kube-context "$KUBE_CONTEXT" --values values.yaml
```

### Paso 4: Verificar la instalación

Lea el titular real del Lease, el nodo/IP del Pod del gateway, el endpoint/MAC de VTEP y la ENI de la ruta; confirme que todos correspondan al mismo líder. `holderIdentity` puede contener el nombre de host de un nodo más un UUID, así que no lo pase directamente a `kubectl logs` ni a `kubectl delete pod`.

```bash
: "${KUBE_CONTEXT:?Set the reviewed Kubernetes context}"
: "${AWS_REGION:?Set the reviewed AWS Region}"
: "${ROUTE_TABLE_ID:?Set one reviewed route table ID}"
kubectl --context "$KUBE_CONTEXT" -n eks-hybrid-nodes-gateway \
  rollout status deployment/eks-hybrid-nodes-gateway --timeout=180s
kubectl --context "$KUBE_CONTEXT" -n eks-hybrid-nodes-gateway get pods -o wide
kubectl --context "$KUBE_CONTEXT" -n eks-hybrid-nodes-gateway   get lease hybrid-gateway-leader -o yaml
kubectl --context "$KUBE_CONTEXT" get ciliumvtepconfig hybrid-gateway -o yaml
aws ec2 describe-route-tables --region "$AWS_REGION" \
  --route-table-ids "$ROUTE_TABLE_ID" --query 'RouteTables[].Routes' --output json
kubectl --context "$KUBE_CONTEXT" -n eks-hybrid-nodes-gateway logs \
  -l app.kubernetes.io/name=eks-hybrid-nodes-gateway --all-containers=true --tail=50
```

Un Pod en estado Running, una respuesta de disponibilidad y una métrica de líder no demuestran que el reenvío funcione. Pruebe ambas direcciones, IP de Pods directas, Services ClusterIP con endpoints Hybrid, llamadas reales al webhook y tráfico de retorno desde cargas de trabajo seleccionadas explícitamente de la nube y Hybrid. El servidor debe estar escuchando realmente en el puerto probado. Mantenga los registros en privado y oculte los datos sensibles de las cargas de trabajo antes de compartirlos.

---

## Configuración del CNI {#cni-configuration}

### Configuración de Cilium VTEP en Hybrid Nodes

Use la compilación de Cilium mantenida por AWS. Los [requisitos previos del CNI del gateway](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-gateway-cni.html) especifican las versiones mínimas de rama **1.17.13-1, 1.18.8-1 o 1.19.2-1**; son mínimos funcionales, no recomendaciones para degradar ni ignorar la compatibilidad de rama. Conserve los selectores de nodo existentes, los rangos de IPAM y los demás valores revisados de la versión.

El cambio requerido es `vtep.enabled=true` y **`l7Proxy=false`**. El perfil L7 de Cilium Ingress/Gateway API de [Operaciones](./08-operations.md) no se puede habilitar en esa misma instalación de Cilium. Esto no impide que las aplicaciones HTTP comunes usen la ruta enrutada. No deduzca que VXLAN cifra el tráfico ni habilite WireGuard solo porque lo mencione un ejemplo no relacionado; valide la combinación específica de datapath/cifrado que sea compatible.

#### Verificación de Cilium VTEP en Hybrid Nodes

```bash
: "${KUBE_CONTEXT:?Set the reviewed Kubernetes context}"
: "${CILIUM_VERSION:?Choose an AWS-maintained Cilium version meeting the gateway minimum}"
# Apply to the existing reviewed Hybrid Cilium release during a maintenance window.
helm upgrade cilium oci://public.ecr.aws/eks/cilium/cilium \
  --version "$CILIUM_VERSION" --namespace kube-system \
  --kube-context "$KUBE_CONTEXT" --reuse-values \
  --set vtep.enabled=true --set l7Proxy=false
kubectl --context "$KUBE_CONTEXT" -n kube-system rollout restart daemonset/cilium
kubectl --context "$KUBE_CONTEXT" -n kube-system   rollout status daemonset/cilium --timeout=300s
kubectl --context "$KUBE_CONTEXT" -n kube-system get configmap cilium-config \
  -o jsonpath='{.data.enable-vtep}{"\n"}{.data.enable-l7-proxy}{"\n"}'
```

Los dos valores de ConfigMap impresos deben ser `true` y después `false`. Inspeccione también el estado de Cilium en cada nodo Hybrid y el objeto VTEP administrado por el controlador. Use la CLI incluida en la imagen de Cilium seleccionada y revise su ayuda antes de confiar en un comando `bpf vtep` específico; un solo Pod seleccionado por el DaemonSet no abarca todos los nodos.

### Configuración de VPC CNI en nodos de la nube

En los nodos de la nube que ejecutan AWS VPC CNI, se deben excluir del SNAT los CIDR de Pods Hybrid para el **tráfico ClusterIP a endpoints Hybrid**. El tráfico directo a IP de Pod puede funcionar incluso si falta este ajuste, por lo que una prueba solo con IP directa no basta. Conserve las demás exclusiones y coordine el cambio con quien administra la configuración del complemento.

```bash
: "${KUBE_CONTEXT:?Set the reviewed Kubernetes context}"
# MNG/self-managed cloud nodes using the aws-node DaemonSet:
kubectl --context "$KUBE_CONTEXT" -n kube-system get daemonset aws-node
# Preserve existing exclusions; use the complete reviewed CSV union, not just a new CIDR.
: "${SNAT_EXCLUDE_CIDRS:?Set existing exclusions plus all Hybrid Pod CIDRs}"
kubectl --context "$KUBE_CONTEXT" -n kube-system set env daemonset/aws-node \
  AWS_VPC_K8S_CNI_EXCLUDE_SNAT_CIDRS="$SNAT_EXCLUDE_CIDRS"
```

Auto Mode proporciona redes integradas, no un DaemonSet `aws-node` que haya que configurar. No instale ni reemplace sus redes con esta receta de DaemonSet. Valide por separado la ruta de servicios Hybrid compatible; en clústeres mixtos, aplique el ajuste de `aws-node` a los nodos de la nube que realmente administra ese componente. La delegación de prefijos y las opciones de redes personalizadas son decisiones de diseño independientes, no requisitos previos del gateway.

### Detalles de la CRD CiliumVTEPConfig

El código [upsert de la versión 1.0.2](https://github.com/aws/eks-hybrid-nodes-gateway/blob/v1.0.2/internal/cilium/vtep.go) del controlador usa la siguiente forma de API. El gateway administra el objeto denominado `hybrid-gateway`; esto no significa que Kubernetes permita un solo objeto CiliumVTEPConfig en el clúster.

```yaml
# Illustrative controller-owned observation; do not apply over the running controller.
apiVersion: cilium.io/v2
kind: CiliumVTEPConfig
metadata:
  name: hybrid-gateway
spec:
  endpoints:
  - name: vpc-gateway
    tunnelEndpoint: "10.0.1.5"
    cidr: "10.0.0.0/16"
    mac: "82:36:6c:89:e6:ad"  # Read the actual leader VXLAN MAC.
```

Al cambiar el líder, se actualizan `tunnelEndpoint` y `mac`. Cada endpoint tiene un `cidr`; varios prefijos de VPC configurados producen varias entradas. La MAC es la de la interfaz VXLAN real del líder, no una constante ficticia arbitraria. Observe la convergencia de Cilium y la recuperación de la aplicación en lugar de suponer que la propagación siempre tarda de 1 a 5 segundos. Ese intervalo anterior era una ilustración no verificada, no un resultado medido.

---

## Patrones de flujo de tráfico

Comprender cómo fluye el tráfico por el gateway es esencial para solucionar problemas y planificar capacidad. Esta sección sigue los paquetes por el sistema para cada patrón principal de comunicación. Los diagramas históricos usan un rango de Pods ilustrativo independiente, 10.100.0.0/20; no combine ese plan de direcciones con el ejemplo de instalación sin conciliar todos los CIDR reales.

### Patrón 1: de un Pod de la VPC a un Pod Hybrid

Este es el patrón más común: un Pod que se ejecuta en un nodo de la nube dentro de la VPC necesita comunicarse con un Pod que se ejecuta en un nodo Hybrid en las instalaciones.

![Un paquete de la VPC sigue la ruta agregada configurada hasta el líder y después una ruta local por nodo a través de hybrid_vxlan0 hasta el Pod Hybrid.](../.gitbook/assets/en-eks-hybrid-nodes-10-hybrid-nodes-gateway-3.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-hybrid-nodes-10-hybrid-nodes-gateway-3.html)

**Flujo del paquete paso a paso:**

1. El Pod de la nube (`10.0.64.15`) envía un paquete al Pod Hybrid (`10.100.0.42`).
2. El paquete entra en la red de la VPC; la tabla de rutas de la VPC coincide con la ruta agregada configurada `10.100.0.0/20 -> gateway ENI`.
3. El paquete llega a la ENI principal de la instancia EC2 del gateway.
4. La tabla de enrutamiento de Linux del gateway coincide con la ruta: `10.100.0.0/24 via <hybrid-node-internal-ip> dev hybrid_vxlan0 onlink`.
5. El gateway encapsula el paquete con VXLAN (origen externo: IP del gateway; destino externo: IP del nodo Hybrid; VNI: 2; puerto UDP de destino externo: 8472).
6. El paquete encapsulado atraviesa Direct Connect/VPN hasta la red local.
7. El agente de Cilium del nodo Hybrid recibe el paquete UDP en el puerto 8472.
8. Cilium desencapsula el paquete VXLAN y entrega el paquete interno al Pod de destino.

### Patrón 2: de un Pod Hybrid a un Pod de la VPC

Cuando un Pod de un nodo Hybrid necesita acceder a un Pod (o a cualquier IP) de la VPC:

![Cilium coincide con el cidr del endpoint, encapsula hacia el endpoint del túnel líder y el gateway reenvía el paquete desencapsulado por la VPC.](../.gitbook/assets/en-eks-hybrid-nodes-10-hybrid-nodes-gateway-4.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-hybrid-nodes-10-hybrid-nodes-gateway-4.html)

**Flujo del paquete paso a paso:**

1. El Pod Hybrid (`10.100.0.42`) envía un paquete al Pod de la nube (`10.0.64.15`).
2. El agente de Cilium del nodo Hybrid hace una búsqueda BPF y descubre que `10.0.64.15` coincide con el `cidr` de endpoint `10.0.0.0/16` de VTEP.
3. Cilium encapsula el paquete con VXLAN (destino externo: IP del gateway `10.0.1.100`; VNI: 2; puerto UDP de destino externo: 8472).
4. El paquete encapsulado atraviesa Direct Connect/VPN hasta la VPC.
5. La instancia EC2 del gateway recibe el paquete UDP en el puerto 8472.
6. El gateway desencapsula el paquete VXLAN y extrae el paquete interno (destino: `10.0.64.15`).
7. El paquete interno se reenvía a la VPC mediante la ENI de la instancia EC2 del gateway.
8. El enrutamiento estándar de la VPC entrega el paquete al Pod de la nube.

> La comprobación de origen/destino debe estar deshabilitada en la ENI principal real del gateway por quien administra el aprovisionamiento del nodo. Consulte arriba los requisitos de Auto Mode y de nodos administrados/autoadministrados; leer la ruta no verifica este ajuste.

### Patrón 3: del plano de control a un webhook de un nodo Hybrid

Cuando un webhook mutador o validador se ejecuta en un nodo Hybrid, el plano de control de EKS necesita acceder a él.

```text
Webhook invocation → resolved remote Pod endpoint
  → control-plane VPC network path / matching route table
  → gateway primary ENI → VXLAN → Hybrid node → webhook listener
  → verified reverse path for the response
```

La red de Pods remota configurada, las rutas de las subredes del plano de control, el Service/endpoint/TLS del webhook, las reglas de seguridad y la ruta de retorno deben coincidir. No suponga que el plano de control administrado implementa kube-proxy/iptables. Un diseño nativo de Pods enrutables también puede admitir webhooks Hybrid; esta capacidad no es exclusiva del gateway.

### Patrón 4: de los servicios de AWS a Pods Hybrid

| Ruta | Configuración requerida |
|---|---|
| Destinos IP de ALB/NLB | Registre las IP de los Pods elegibles mediante el controlador previsto; verifique las rutas de las subredes del balanceador, las comprobaciones de estado, los puertos de aplicación, la identidad de origen y el tráfico de retorno |
| Recopilador administrado de AMP | El recopilador accede a los endpoints de métricas mediante las rutas de VPC/Pods remotos y los puertos de firewall abiertos; la guía del complemento Hybrid también exige acceso al endpoint privado del clúster |
| Prometheus remote_write | Un recopilador de Prometheus/ADOT envía muestras al endpoint de ingesta del workspace de AMP; el workspace no es un recopilador entrante |
| CloudWatch/exportación de trazas | Un agente/recopilador configurado adecuadamente envía datos al endpoint del servicio; las rutas necesarias de IAM/API/DNS/salida son independientes del enrutamiento entrante de Pods |
| PrivateLink | Endpoint del consumidor → servicio/balanceador del proveedor → destinos, según el diseño de ese servicio; un servicio genérico de AWS no inicia conexiones arbitrarias a Pods Hybrid a través de un endpoint |

La [guía de complementos Hybrid](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-add-ons.html) admite explícitamente la recopilación administrada de AMP cuando se cumplen estos requisitos de endpoint y red. Distinga ese recopilador de `remote_write` autoadministrado; ninguno aparece solo por instalar el gateway.

#### Medición: destinos IP de ALB en Pods Hybrid (18-10-2026)

Medición en un entorno simulado (se sustituyeron las instalaciones por una VPC separada conectada mediante TGW; gateway 1.0.2, chart 3.6.0 de AWS Load Balancer Controller y ALB interno). No es una configuración de producción compatible y las cifras no son garantías.

| Comprobación | Resultado |
|---|---|
| Registro de destinos | LBC registró las IP de los Pods Hybrid (`172.17.0.202`, `172.17.0.48`) como destinos `ip`. Están fuera de la VPC, por lo que `AvailabilityZone` es `all`; las comprobaciones de estado pasaron por la ruta del gateway |
| Solicitud | Cliente de la VPC → ALB interno → ruta de la VPC `172.17.0.0/16` (ENI del líder) → VXLAN → Pod Hybrid, 20/20 |
| Reemplazo del Pod | Reinicio progresivo durante la carga; los destinos convergieron a las nuevas IP de Pod en 54 s, con 0 de 276 solicitudes fallidas (`preStop` 15 s, retraso de baja 10 s) |
| Cambio de líder | Se eliminó el Pod líder durante la carga; transferencia en 4 s, con 1 de 191 solicitudes fallidas (cliente sin reintentos) |

El **AWS Load Balancer Controller**, no el gateway, actualiza los destinos cuando cambian las IP de Pod. El gateway solo proporciona la ruta a las IP de Pods que están fuera de la VPC, por lo que el CIDR de Pods debe ser enrutable desde la VPC. Durante la instalación, el objeto `kind: List` del chart 3.6.0 de LBC (IngressClassParams e IngressClass) no superó la validación OpenAPI del cliente con `the server is currently unable to handle the request`; `--disable-openapi-validation` permitió continuar. Si reduce a 5 s el intervalo de la comprobación de estado, establezca también un timeout inferior a 5 s o fallará la creación del grupo de destinos.

### Patrón 5: de clientes locales a Pods de la región (dirección inversa)

Un cliente local entra mediante un balanceador de carga y llega a Pods en nodos de la región (VPC). En esta dirección, la ruta predeterminada es el propio enrutamiento de la VPC, no el gateway.

| Ruta | Comportamiento | Medición (18-10-2026) |
|---|---|---|
| Instalaciones → ALB interno → Pod de VPC CNI | El DNS local resuelve el nombre del ALB a IP privadas (endpoint entrante de Route 53 Resolver); el tráfico entra en la VPC por DX/VPN/TGW y el ALB lo reenvía a las IP de Pods de VPC CNI. No pasa por el gateway | 20/20 |
| Instalaciones → ALB interno → Pod Hybrid | Misma ruta, con retorno a las instalaciones mediante el gateway; atraviesa DX dos veces, lo que aumenta la latencia y el costo de transferencia | 20/20 |
| Instalaciones → NodePort Hybrid → Pod de VPC CNI | kube-proxy hace SNAT a la IP del nodo y el enrutamiento del host lo envía por la red subyacente, sin usar el gateway (VTEP). Los grupos de seguridad de los nodos de la región deben permitir el puerto de la aplicación desde el CIDR de los nodos remotos | Falló (el grupo de seguridad del clúster solo permitía 443 desde el CIDR de los nodos remotos) |

La [guía de Ingress de AWS](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-ingress.html) recomienda ALB con Load Balancer Controller para el tráfico que se origina en la región, e Ingress local para el tráfico que se origina en las instalaciones. Como el gateway requiere `l7Proxy=false` de Cilium, Cilium Ingress y Gateway API no están disponibles en la misma instalación; para el acceso desde las instalaciones, considere un Service `LoadBalancer` L4 (Cilium LB IPAM/BGP) o un balanceador de hardware existente con NodePort.

### Patrón 6: comparación — con y sin gateway

El enrutamiento nativo/BGP/estático y este gateway son rutas de datos distintas, administradas por componentes diferentes. El gateway agrega un salto VXLAN activo/en espera y automatiza rutas agregadas, pero mantiene las responsabilidades sobre la red subyacente, CIDR, firewall, IAM y aplicaciones. Las secciones siguientes sobre comparación y migración describen sus límites; ninguno de los enfoques garantiza automáticamente la disponibilidad de webhooks/balanceadores.

---

## Alta disponibilidad y conmutación por error

### Arquitectura del Deployment

El despliegue de producción recomendado usa 2 réplicas del gateway distribuidas entre zonas de disponibilidad:

![El líder controla las rutas de AWS y los endpoints de VTEP mientras la réplica en espera ya reconcilia el estado local del túnel; se debe verificar la ubicación entre zonas de disponibilidad.](../.gitbook/assets/en-eks-hybrid-nodes-10-hybrid-nodes-gateway-5.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-hybrid-nodes-10-hybrid-nodes-gateway-5.html)

### Secuencia de conmutación por error

Cuando el Pod líder del gateway deja de estar disponible (fallo del nodo, caída del Pod o partición de red), se produce la siguiente secuencia de conmutación por error:

![Después del cambio de líder, primero se actualizan las rutas agregadas de AWS y luego los endpoints de VTEP. Los ajustes de elección no garantizan un tiempo de recuperación fijo.](../.gitbook/assets/en-eks-hybrid-nodes-10-hybrid-nodes-gateway-6.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-hybrid-nodes-10-hybrid-nodes-gateway-6.html)

### Cronología de conmutación por error

**Ilustración histórica, no evidencia medida**: la tabla original no tiene un registro de prueba reproducible. Conserve sus valores como contexto, no como SLO. La guía actual de AWS calcula aproximadamente 3–5 segundos, mientras que el README etiquetado del proyecto presenta otra estimación; es necesario probar la convergencia real de rutas, API, Cilium y aplicaciones. La configuración del líder actualiza las rutas de la VPC **antes** que el objeto VTEP, no en paralelo. Ninguno de los intervalos garantiza la recuperación ante un fallo de nodo, zona de disponibilidad o plano de control.

| Fase | Duración | Descripción |
|-------|----------|-------------|
| **Detección** | 0–3 s | El líder actual deja de renovar el Lease; este vence después de `leaseDuration` |
| **Elección** | 0–1 s | La réplica en espera adquiere el Lease en el siguiente intervalo de `retryPeriod` |
| **Actualización de rutas** | 1–3 s | El nuevo líder llama a `ec2:ReplaceRoute` para actualizar las rutas de la VPC |
| **Actualización de VTEP** | 1–5 s | El nuevo líder actualiza `CiliumVTEPConfig`; los agentes de Cilium vuelven a cargar los mapas BPF |
| **Total** | **~5–10 s** | Tiempo de conmutación por error de extremo a extremo |

Durante la ventana de conmutación por error:

- **Tráfico de la VPC a Hybrid**: se pierde hasta que se actualizan las rutas de la VPC (los paquetes se envían a la ENI del gateway que falló).
- **Tráfico de Hybrid a la VPC**: se pierde hasta que se actualiza CiliumVTEPConfig (Cilium envía el tráfico a la IP del gateway anterior).
- **Rutas internas de Hybrid y del nodo/plano de control**: las rutas que no atraviesan el gateway pueden seguir funcionando solo si su propia red subyacente, CNI, DNS y dependencias continúan en buen estado; un fallo compartido de zona de disponibilidad/red también puede afectarlas.

### Fallo de un único gateway y varios centros de datos

El gateway (1.0.2) se despliega como un único conjunto por clúster con un solo líder activo. El líder crea una ruta en cada tabla configurada **para cada CIDR** de `podCIDRs` (CSV), y las entradas del túnel se administran por cada `CiliumNode` Hybrid. Un único gateway atiende centros de datos con CIDR de Pods diferentes (por ejemplo, centro A `10.85.0.0/16` y centro B `10.86.0.0/16`), siempre que cada CIDR aparezca tanto en `remotePodNetworks` del clúster como en `podCIDRs` del gateway. Los rangos no necesitan ser contiguos.

| Elemento | Detalles |
|---|---|
| Cantidad de CIDR | Hasta 15 CIDR de red de Pods remotos (límite de EKS). Cada CIDR agrega una ruta por tabla de rutas; compruebe también la cuota de rutas por tabla (50 de forma predeterminada) |
| Rendimiento | El tráfico entre la VPC y Pods Hybrid de todos los centros de datos pasa por un único líder. El modo activo/en espera no permite escalar horizontalmente; dimensione la instancia y el rendimiento de su red |
| Firewall | Los nodos Hybrid de todos los centros de datos deben poder acceder por UDP 8472 a las IP tanto del líder como de la réplica en espera |
| Separación por centro de datos | No está documentado ejecutar un gateway independiente por centro de datos dentro de un clúster. En 1.0.2, los nombres del Lease (`hybrid-gateway-leader`) y de CiliumVTEPConfig (`hybrid-gateway`) son fijos, por lo que es probable que varias versiones entren en conflicto (no verificado) |

Si solo hay un Pod de gateway o fallan ambos, el tráfico entre la VPC y los CIDR de Pods Hybrid de **todos** los centros de datos se detiene a la vez. El runtime nunca llama a `DeleteRoute`, por lo que las rutas de la VPC siguen apuntando a la ENI fallida.

| Rutas que se interrumpen | Rutas que continúan (si su propia red y DNS están en buen estado) |
|---|---|
| Pods de la VPC ↔ Pods Hybrid en ambas direcciones, webhooks en Pods Hybrid, destinos ALB/NLB en Pods Hybrid y recopilador AMP → endpoints Hybrid | Plano de control ↔ kubelet (ruta del CIDR de nodo), tráfico Hybrid a Hybrid dentro de un centro de datos, tráfico Hybrid entre centros de datos enrutado localmente, rutas de IP de nodo (NodePort, hostNetwork) |

Por tanto, en la práctica se requieren dos réplicas en nodos elegibles de zonas de disponibilidad distintas. Si el mismo Service también tiene Pods en la VPC, el grupo de destinos incluye esos nodos de la nube, por lo que el balanceador puede seguir respondiendo desde allí cuando las comprobaciones de estado descarten los destinos Hybrid (esta combinación no se midió).

### Recomendaciones para despliegues multizona

El chart 1.0.2 exige hosts distintos, pero solo prefiere zonas de disponibilidad distintas. Seleccione/aprovisione nodos elegibles en varias zonas e inspeccione su ubicación real; no establezca etiquetas de topología falsas. Los valores `affinity` y `topologySpreadConstraints` de ejemplos antiguos no están conectados en este chart. Si se requieren restricciones estrictas por zona, mantenga una superposición de Deployment revisada y tenga en cuenta que los Pods pueden quedar Pending cuando una zona/la capacidad no esté disponible.

### PodDisruptionBudget

Este PDB opcional limita el desalojo voluntario mediante la API de desalojo. No impide la eliminación directa de Pods, los despliegues del Deployment ni los fallos involuntarios, y no conserva el líder activo por su identidad:

```yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: eks-hybrid-nodes-gateway
  namespace: eks-hybrid-nodes-gateway
spec:
  minAvailable: 1
  selector:
    matchLabels:
      app.kubernetes.io/name: eks-hybrid-nodes-gateway
```

### Recuperación tras el fallo total del gateway

Inspeccione ambos Pods del gateway, los nodos de la nube elegibles, el Lease, los destinos de ruta y el estado de VTEP. Distinga la pérdida del gateway de un fallo más amplio de la red subyacente/API/Cilium. La conectividad existente entre las IP de nodo y el plano de control es una ruta independiente; no suponga que todas las cargas de trabajo conservan el acceso a DNS o a servicios de la nube.

```bash
: "${KUBE_CONTEXT:?Set the reviewed Kubernetes context}"
kubectl --context "$KUBE_CONTEXT" -n eks-hybrid-nodes-gateway get pods -o wide
kubectl --context "$KUBE_CONTEXT" get nodes -l hybrid-gateway-node=true -o wide
kubectl --context "$KUBE_CONTEXT" -n eks-hybrid-nodes-gateway   get lease hybrid-gateway-leader -o yaml
kubectl --context "$KUBE_CONTEXT" get ciliumvtepconfig hybrid-gateway -o yaml
```

Antes de etiquetarlo, el nodo de reemplazo debe cumplir los requisitos de IAM, reenvío de la ENI principal, red y ubicación del chart. Una vez restaurado el liderazgo, vuelva a comprobar las ENI de las rutas de la VPC y las pruebas bidireccionales de las aplicaciones. El estado de disponibilidad y las métricas del líder por sí solos no son criterios de aceptación. Un ejercicio destructivo de conmutación por error debe realizarse en una ventana aprobada, con identidades verificadas de Pod/nodo, pruebas de tráfico y una persona responsable de la recuperación; no deduzca a ciegas el Pod que debe eliminar a partir de `holderIdentity`.

---

## Operaciones

### Supervisión

#### Métricas clave que se deben observar

La versión 1.0.2 expone `/metrics` en el puerto **10080**, con `/healthz` y `/readyz` en el puerto 8088. Las [definiciones de métricas etiquetadas](https://github.com/aws/eks-hybrid-nodes-gateway/blob/v1.0.2/internal/metrics/metrics.go) y el [recopilador](https://github.com/aws/eks-hybrid-nodes-gateway/blob/v1.0.2/internal/metrics/collector.go) definen estos nombres/tipos:

| Métrica | Tipo | Interpretación |
|---|---|---|
| `hybrid_gateway_leader_is_active` | Gauge | Estado de liderazgo de esta réplica; no demuestra que las rutas se hayan configurado correctamente |
| `hybrid_gateway_hybrid_nodes_configured` | Gauge | Cantidad de nodos configurados localmente por esta réplica |
| `hybrid_gateway_vxlan_tx_bytes_total`, `hybrid_gateway_vxlan_rx_bytes_total` | Counter | Contadores de bytes de la interfaz del kernel; use la tasa y tenga en cuenta los reinicios |
| `hybrid_gateway_vxlan_tx_packets_total`, `hybrid_gateway_vxlan_rx_packets_total` | Counter | Contadores de paquetes, no de solicitudes de aplicación satisfactorias |
| `hybrid_gateway_vxlan_interface_up` | Gauge | Estado de la interfaz, no accesibilidad de extremo a extremo |
| `hybrid_gateway_vxlan_fdb_entries`, `hybrid_gateway_vxlan_route_count` | Gauge | Recuentos de tablas observados localmente |
| `hybrid_gateway_aws_route_table_update_total`, `hybrid_gateway_aws_route_table_update_errors_total` | Counter | Eventos satisfactorios o fallidos de operaciones de ruta |
| `hybrid_gateway_aws_route_table_update_duration_seconds`, `hybrid_gateway_leader_setup_duration_seconds` | Histogram | Observaciones de duración; sin eventos no se obtiene una estimación útil de latencia |

El código emite las métricas de red con sufijo `_total` como contadores, incluso cuando una tabla en prosa las denomina gauges. `LeaderIsActive` se activa antes de completar la configuración de rutas/VTEP, y la disponibilidad no es una prueba de aplicación. Investigue la ausencia/proliferación sostenida de líderes junto con el estado de recopilación y los errores de API; una sola muestra transitoria no demuestra una división de cerebro.

#### ServiceMonitor de Prometheus

El chart no crea un Service. Este ejemplo independiente crea uno y vincula un ServiceMonitor con el **puerto nombrado del Service**. Prometheus Operator/CRD, la selección de espacios de nombres y el `serviceMonitorSelector` real ya deben estar configurados. Cambie la etiqueta de ejemplo `release` para que coincida con esa pila. Restrinja el acceso al puerto de métricas de red del host mediante controles del nodo/la red.

```yaml
apiVersion: v1
kind: Service
metadata:
  name: hybrid-gateway-metrics
  namespace: eks-hybrid-nodes-gateway
  labels:
    app.kubernetes.io/name: eks-hybrid-nodes-gateway
    app.kubernetes.io/instance: eks-hybrid-nodes-gateway
spec:
  selector:
    app.kubernetes.io/name: eks-hybrid-nodes-gateway
    app.kubernetes.io/instance: eks-hybrid-nodes-gateway
  ports:
  - name: metrics
    port: 10080
    targetPort: metrics
---
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: hybrid-gateway-metrics
  namespace: eks-hybrid-nodes-gateway
  labels:
    release: kube-prom  # Must match the existing Prometheus serviceMonitorSelector.
spec:
  namespaceSelector:
    matchNames: [eks-hybrid-nodes-gateway]
  selector:
    matchLabels:
      app.kubernetes.io/name: eks-hybrid-nodes-gateway
      app.kubernetes.io/instance: eks-hybrid-nodes-gateway
  endpoints:
  - port: metrics
    interval: 30s
    scrapeTimeout: 10s
    path: /metrics
```

#### Consultas de ejemplo para el panel de Grafana

```promql
# Expected steady-state leader count, scoped to this one Service scrape job.
sum(hybrid_gateway_leader_is_active{namespace="eks-hybrid-nodes-gateway",service="hybrid-gateway-metrics"})

# Per-target VXLAN TX/RX byte rates; do not sum duplicate scrape jobs.
rate(hybrid_gateway_vxlan_tx_bytes_total{namespace="eks-hybrid-nodes-gateway",service="hybrid-gateway-metrics"}[5m])
rate(hybrid_gateway_vxlan_rx_bytes_total{namespace="eks-hybrid-nodes-gateway",service="hybrid-gateway-metrics"}[5m])

# Failures in the observation window, not a cumulative nonzero counter alert.
increase(hybrid_gateway_aws_route_table_update_errors_total{namespace="eks-hybrid-nodes-gateway",service="hybrid-gateway-metrics"}[5m])

# Per-replica local configuration counts; summing leader and standby double-counts nodes.
hybrid_gateway_hybrid_nodes_configured{namespace="eks-hybrid-nodes-gateway",service="hybrid-gateway-metrics"}

# Target scrape health is separate from leader/traffic metrics.
up{namespace="eks-hybrid-nodes-gateway",service="hybrid-gateway-metrics"}
```

La ausencia de series temporales requiere una alerta por destino/recopilación ausente; una suma sin series no equivale automáticamente a cero. Derive los períodos de alerta y las cantidades esperadas de nodos del despliegue real. Menos tráfico puede significar que las aplicaciones están inactivas, no que haya un fallo, y los errores acumulados siguen siendo distintos de cero tras un incidente anterior.

#### Integración con CloudWatch

`NetworkIn`/`NetworkOut` de EC2 son contadores a nivel de instancia, no métricas exclusivas de VXLAN/ENI. Para usar métricas personalizadas del gateway en CloudWatch, primero configure un recopilador con espacio de nombres, dimensiones, unidades y tratamiento de contadores acumulativos explícitos; después, verifique las muestras publicadas. Un comando `put-metric-alarm` no crea su métrica ni demuestra que el tráfico haya fallado. Incluya en el diseño de alarmas los huecos del exportador, los períodos de inactividad y los reinicios de contadores.

### Registro de eventos

Recopile registros acotados en privado y mantenga los fallos de API/permisos como fallos. Un selector de etiquetas selecciona ambas réplicas, no solo el líder. `holderIdentity` no es necesariamente el nombre de un Pod. Algunos mensajes útiles de 1.0.2 son `Processing CiliumNode`, `Adding hybrid node to gateway`, `Remote VTEP added` y `Reconciling CiliumVTEPConfig`; use los registros estructurados reales, no texto supuesto sobre una operación AWS DeleteRoute que el runtime nunca realiza.

#### Habilitar el registro de depuración

El chart 1.0.2 no conecta `logLevel=debug`; ese valor de Helm no habilita el modo de depuración. Inspeccione las marcas de registro compatibles con el binario seleccionado y mantenga explícitamente cualquier superposición de Deployment que se requiera. Al aumentar el nivel de detalle, evite exponer credenciales o contenido de las cargas de trabajo.

### Solución de problemas

#### Problema: los Pods no pueden comunicarse a través del gateway

Este script de recopilación se detiene si falla una consulta a la API o a los registros. No interpreta los errores de autenticación/transporte como ausencia del recurso. Antes de compartir artefactos privados, revíselos y oculte la información sensible.

```bash
#!/usr/bin/env bash
set -euo pipefail
umask 077
: "${KUBE_CONTEXT:?Set the reviewed Kubernetes context}"
: "${AWS_REGION:?Set the reviewed AWS Region}"
: "${ROUTE_TABLE_ID:?Set one reviewed route table ID}"
OUT_DIR=$(mktemp -d "${TMPDIR:-/tmp}/gateway-diagnose.XXXXXX")
kubectl --context "$KUBE_CONTEXT" -n eks-hybrid-nodes-gateway get pods -o json > "$OUT_DIR/pods.json"
kubectl --context "$KUBE_CONTEXT" -n eks-hybrid-nodes-gateway \
  get lease hybrid-gateway-leader -o json > "$OUT_DIR/lease.json"
kubectl --context "$KUBE_CONTEXT" get ciliumvtepconfig hybrid-gateway -o json > "$OUT_DIR/vtep.json"
kubectl --context "$KUBE_CONTEXT" get ciliumnodes -o json > "$OUT_DIR/ciliumnodes.json"
aws ec2 describe-route-tables --region "$AWS_REGION" \
  --route-table-ids "$ROUTE_TABLE_ID" --output json > "$OUT_DIR/routes.json"
kubectl --context "$KUBE_CONTEXT" -n eks-hybrid-nodes-gateway logs \
  -l app.kubernetes.io/name=eks-hybrid-nodes-gateway \
  --all-containers=true --prefix=true --tail=100 > "$OUT_DIR/gateway.log"
printf 'Private diagnostic files: %s\n' "$OUT_DIR"
```

Compare el nodo/IP del Pod del líder real, la IP/MAC de VTEP, la ruta de la ENI principal y los CIDR de CiliumNode. Compruebe toda la ruta de retorno y la configuración requerida `VTEP=true`/`L7=false`. No reinicie Cilium a ciegas porque falte un mapa; primero inspeccione la versión, la configuración y los errores de reconciliación.

#### Problema: configuración incorrecta del grupo de seguridad

UDP no tiene un protocolo de enlace de conexión. Que `nc -uz` indique éxito no demuestra que el tráfico VXLAN haya llegado ni se haya desencapsulado. Compruebe los grupos de seguridad, las NACL sin estado, los firewalls locales y ambas direcciones de la red subyacente mediante capturas/contadores aprobados y acotados. Un filtro de captura en la interfaz física ve el UDP 8472 externo; una captura en `hybrid_vxlan0` ve el tráfico interno, así que filtrar esa interfaz por el UDP 8472 externo puede ocultar el tráfico que se intenta diagnosticar.

#### Problema: faltan rutas de la VPC

Confirme los ID de las tablas configuradas, los prefijos exactos de Pods, la ENI principal del gateway y la identidad IAM de la carga de trabajo. El comando `sts get-caller-identity` del operador no demuestra qué rol usa el SDK del gateway. Una prueba DryRun distingue los resultados `DryRunOperation` y `UnauthorizedOperation` y debe usar el principal/parámetros previstos; no modifica rutas satisfactoriamente. Inspeccione la comprobación de origen/destino de la ENI principal real, no solo un atributo supuesto del nodo.

#### Problema: cambios frecuentes de líder

Inspeccione el Lease indicado, la latencia/accesibilidad de la API, el estado del nodo del gateway y la presión de recursos. La pérdida del liderazgo no demuestra que otra réplica haya terminado de configurar las rutas. El controlador de disponibilidad hace una comprobación booleana local. Un `wget` sin autenticación al servidor de API puede fallar por TLS/autenticación sin demostrar que la red esté caída.

#### Problema: problemas de MTU

Use una imagen/entorno de diagnóstico que realmente incluya iproute2/iputils. `ping` de BusyBox no siempre admite la opción `-M do` de iputils. Limite la cantidad de paquetes y el timeout, elija ambos endpoints deliberadamente y recuerde que la carga útil ICMP de IPv4 también necesita 28 bytes para los encabezados IP/ICMP antes de la encapsulación. Una respuesta ICMP bloqueada no permite medir la MTU de forma concluyente. Importa más la MTU mínima de extremo a extremo de la red subyacente, incluida la encapsulación VPN/DX, que restar 50 a la NIC de EC2 por sí sola.

#### Árbol de decisión para solucionar problemas

1. Confirme los dos objetos del plano de control y las identidades reales de los nodos de la nube/Hybrid; conserve los errores de API.
2. Verifique por separado la propiedad/destino de la ruta agregada y las rutas/FDB/vecinos locales de cada nodo.
3. Verifique la accesibilidad del UDP externo y la comprobación de origen/destino de la ENI principal.
4. Verifique la versión de Cilium mantenida por AWS, los ajustes de VTEP/L7 y el endpoint VTEP actual.
5. Pruebe por separado la IP directa de Pod y ClusterIP; después, la ruta real del webhook/balanceador.
6. Investigue la MTU, la pérdida de paquetes, el listener/TLS de la aplicación y el enrutamiento de retorno mediante diagnósticos acotados.

### Escalado

#### Agregar más Hybrid Nodes

Cada réplica del gateway reconcilia objetos CiliumNode etiquetados y crea entradas locales de túnel. Cuando asume el liderazgo, el líder administra las rutas agregadas configuradas de CIDR de Pods; no agrega una ruta de AWS por cada nodo nuevo. Verifique las nuevas direcciones/CIDR de nodo y los recuentos locales en ambas réplicas. Una cantidad mayor de nodos por sí sola no determina el rendimiento; las réplicas adicionales proporcionan capacidad en espera, no distribución activa-activa de la carga.

#### Dimensionamiento de instancias del gateway

Dimensione según la tasa máxima de bytes, los paquetes por segundo, las conexiones/túneles concurrentes, la CPU, la memoria y la capacidad de reserva ante fallos. Solo una réplica reenvía el tráfico administrado por el gateway a la vez.

**Ilustración histórica de dimensionamiento:** la tabla siguiente conserva estimaciones originales, no límites probados de cantidad de nodos ni rendimiento validado. Consulte las especificaciones actuales de EC2; en particular, la entrada de 50 Gbps para c6in.2xlarge no es una especificación sostenida verificada.

| Tipo de instancia | vCPU | Memoria | Ancho de banda de red | Uso recomendado |
|---------------|------|--------|-------------------|-----------------|
| c6i.large | 2 | 4 GiB | Hasta 12.5 Gbps | Desarrollo/pruebas, menos de 10 nodos Hybrid |
| c6i.xlarge | 4 | 8 GiB | Hasta 12.5 Gbps | Producción pequeña, 10–50 nodos |
| c6i.2xlarge | 8 | 16 GiB | Hasta 12.5 Gbps | Producción mediana, 50–100 nodos |
| c6i.4xlarge | 16 | 32 GiB | Hasta 12.5 Gbps | Producción grande, más de 100 nodos |
| c6in.2xlarge | 8 | 16 GiB | Hasta 50 Gbps | Cargas de trabajo de alto rendimiento |
| c6in.4xlarge | 16 | 32 GiB | Hasta 50 Gbps | Rendimiento muy alto |

> La tabla no garantiza capacidad. El procesamiento de VXLAN consume CPU y memoria; también se aplican los límites de ancho de banda en ráfaga/base de EC2, PPS y ruta de tráfico. Valide la combinación real de instancia/paquetes en lugar de elegir solo por el ancho de banda de red máximo anunciado.

#### Planificación de capacidad del gateway

El cálculo original de abajo se conserva como un **ejemplo de planificación no medido**. El cálculo de 800 Mbps usa KB/MB decimales y presupone 10 KB por solicitud en cada dirección. Si los 10 KB ya incluyen la solicitud y la respuesta, multiplicarlos por dos los cuenta dos veces. El tamaño de paquete, los encabezados, la concurrencia máxima y los reintentos requieren cálculos independientes. No demuestra que la instancia indicada tenga suficiente capacidad de reserva sostenida:

```
Throughput estimation:
======================
Number of hybrid Pods with cross-boundary traffic:   100
Average request/response size:                        10 KB
Average requests per second per Pod:                  50
VXLAN overhead per packet:                            ~3% (50 bytes / ~1500 bytes)

Required throughput:
  100 Pods × 50 req/s × 10 KB × 2 (bidirectional) = ~100 MB/s = ~800 Mbps

Recommendation: c6i.xlarge (12.5 Gbps) with comfortable headroom
```

### Actualización del gateway

Revise una versión realmente publicada y sus contratos de chart/aplicación. Esta auditoría validó la versión 1.0.2; el comando anterior para 1.1.0 era un ejemplo sin verificar, no una actualización ejecutada. Haga una copia privada de los valores/manifiestos propios y del inventario de rutas, inspeccione el historial de Helm y elija la revisión exacta a la que volver, en vez de suponer que la revisión 1 es adecuada.

```bash
: "${KUBE_CONTEXT:?Set the reviewed Kubernetes context}"
: "${GATEWAY_VERSION:?Set an existing, reviewed release version}"
helm history eks-hybrid-nodes-gateway -n eks-hybrid-nodes-gateway   --kube-context "$KUBE_CONTEXT"
# OCI charts are inspected/pulled by an explicit version, not helm search repo.
helm show chart oci://public.ecr.aws/eks/eks-hybrid-nodes-gateway   --version "$GATEWAY_VERSION"
helm template eks-hybrid-nodes-gateway \
  oci://public.ecr.aws/eks/eks-hybrid-nodes-gateway \
  --version "$GATEWAY_VERSION" --namespace eks-hybrid-nodes-gateway \
  --values values.yaml > gateway-upgrade-rendered.yaml
# Run only after reviewing the rendered diff, IAM, routes and rollback plan:
helm upgrade eks-hybrid-nodes-gateway \
  oci://public.ecr.aws/eks/eks-hybrid-nodes-gateway \
  --version "$GATEWAY_VERSION" --namespace eks-hybrid-nodes-gateway \
  --kube-context "$KUBE_CONTEXT" --values values.yaml
kubectl --context "$KUBE_CONTEXT" -n eks-hybrid-nodes-gateway \
  rollout status deployment/eks-hybrid-nodes-gateway --timeout=300s
```

Las actualizaciones progresivas de Deployment no tienen en cuenta al líder: no garantizan reemplazar primero la réplica en espera. El chart 1.0.2 no conecta un valor `strategy` personalizado. La anti-afinidad/capacidad de hosts, los cambios de Lease y la convergencia de rutas/VTEP pueden interrumpir el tráfico. Los ejemplos históricos de 5–10 s y 40–55 s no son SLO de actualización. Una reversión de Helm también requiere CRD/configuración compatibles y verificación de aplicaciones/rutas; no restaura automáticamente todas las rutas externas de AWS.

### Limpieza

**La desinstalación de Helm deja rutas de AWS.** Antes de instalar y antes de quitar el gateway, registre las tablas, los CIDR, los destinos anteriores y las ENI actuales del gateway. Primero migre/desagende el tráfico que depende del gateway. Detenga el controlador antes de modificar el objeto VTEP que administra para que no lo vuelva a crear.

```bash
: "${KUBE_CONTEXT:?Set the reviewed Kubernetes context}"
: "${AWS_REGION:?Set the reviewed AWS Region}"
: "${ROUTE_TABLE_ID:?Set one route table whose ownership was confirmed}"
# Snapshot/read current targets before deciding which routes to restore or delete.
aws ec2 describe-route-tables --region "$AWS_REGION"   --route-table-ids "$ROUTE_TABLE_ID" --output json
kubectl --context "$KUBE_CONTEXT" get ciliumvtepconfig hybrid-gateway -o yaml
# Disruptive: retire/migrate traffic and record the current leader/ENI before running.
helm uninstall eks-hybrid-nodes-gateway -n eks-hybrid-nodes-gateway   --kube-context "$KUBE_CONTEXT" --wait --timeout=180s
```

Después de eliminar los Pods del gateway, restaure el destino de ruta anterior cuando así lo exija el plan de migración; elimine una ruta solo si su tabla/CIDR/destino actual y propiedad coinciden con el plan de retiro. Nunca elimine a ciegas todos los CIDR configurados: otro propietario podría haber cambiado el destino. Vuelva a consultar el estado de AWS después de cada cambio aprobado y distinga los errores de acceso/transporte de la ausencia del recurso.

Elimine `ciliumvtepconfig/hybrid-gateway`, administrado por el controlador, solo después de confirmar que ningún consumidor/controlador lo siga usando. Quite la asociación/rol de Pod Identity de esta versión, los recursos de métricas y la capacidad dedicada mediante su responsable de infraestructura registrado; que se haya desinstalado el release de Helm no demuestra que hayan desaparecido esos recursos facturables. Elimine un espacio de nombres o una etiqueta de nodo solo si es de uso exclusivo y no quedan cargas de trabajo ajenas. Verifique las rutas resultantes de las aplicaciones, las rutas de red, las asociaciones y la capacidad.

---

## Comparación: con y sin gateway

### Comparación de funciones

| Aspecto | Pods enrutables sin este gateway | EKS Hybrid Nodes Gateway |
|---|---|---|
| Enrutamiento | BGP/enrutamiento estático u otra ruta de automatización propia | Rutas agregadas de la VPC más VTEP de Cilium/reconciliación local de túneles |
| Configuración | Planificación de red subyacente/enrutadores/CNI/direcciones | La misma planificación de red subyacente más nodos de gateway elegibles, IAM, perfil VTEP/L7 de Cilium de AWS y propiedad de rutas |
| Webhooks y destinos IP de ALB/NLB | Posibles con rutas válidas, redes de Pods remotos, rutas de retorno y reglas de seguridad | También requieren esos requisitos de aplicación/plano de control; instalar Helm no los establece |
| CNI | Elija un diseño compatible de Pods enrutables | Requiere la integración VTEP de Cilium mantenida por AWS con el proxy L7 deshabilitado |
| Capacidad | Límites reales de enrutadores/enlaces/CNI/hosts | Capacidad de un gateway activo más los límites de todos los enlaces/rutas subyacentes |
| Alta disponibilidad | Diseño de convergencia/red administrado por el cliente | Lease activo/en espera y convergencia de rutas/VTEP; pueden producirse interrupciones temporales |
| Costos | Clúster/Hybrid Nodes, conectividad, infraestructura y operaciones | Esos costos más EC2/almacenamiento del gateway, tarifas de Auto Mode cuando sus nodos lo usan y posible tráfico adicional entre zonas |
| Retiro | Conciliar rutas/recursos propios | Helm no elimina rutas externas de AWS, asociaciones de IAM ni capacidad dedicada |

### Cuándo usar el gateway

Úselo cuando su perfil VTEP de Cilium de AWS y el salto activo/en espera se ajusten a la carga de trabajo y simplifiquen la propiedad de las rutas de Pods. No elimina la responsabilidad del equipo de red sobre la accesibilidad privada de los nodos, la MTU, los CIDR, las reglas de seguridad ni la recuperación ante fallos. El enrutamiento nativo existente, los requisitos incompatibles de CNI/L7 u otras necesidades de capacidad/dominios de fallo pueden favorecer otro diseño. Ninguna opción ofrece una ventaja universal de latencia, disponibilidad o costo.

### Características de rendimiento

**Las estimaciones originales siguientes son ilustraciones no medidas, no resultados actuales de pruebas de rendimiento.** El enrutamiento nativo también tiene retrasos de procesamiento/cola, y el costo de VXLAN depende del tamaño de paquete, CPU, límites del enlace y descarga de procesamiento. Un salto adicional puede ser relevante incluso con tramas gigantes.

| Métrica | Ilustración original de enrutamiento nativo/BGP | Ilustración original de VXLAN |
|---|---|---|
| Sobrecarga de latencia | ~0 ms | ~0,1–0,5 ms |
| Rendimiento | Ancho de banda DX/VPN completo | Mínimo entre el ancho de banda del gateway y el de DX/VPN |
| Sobrecarga por paquete | 0 bytes para esta superposición | ~50 bytes con VXLAN IPv4 |
| Jitter | Depende de DX/VPN | Depende de DX/VPN y del procesamiento VXLAN |
| PPS | Limitado por la red | Puede limitarlo la CPU del gateway |

Las expresiones de rendimiento omiten ráfagas/base, PPS, CPU y restricciones de la aplicación; no las considere garantías. Las afirmaciones anteriores de conmutación por error en 5–10 s y de «baja complejidad/instalación única» también requieren las salvedades operativas ya indicadas.

### Migración del enrutamiento manual al gateway

1. Registre en privado la propiedad exacta de las tablas/CIDR/destinos actuales y el estado existente de BGP/enrutamiento estático/NAT/CNI. Planifique la reversión y valide la red subyacente, el firewall y los rangos de red.
2. Prepare los nodos de gateway elegibles, IAM de la carga de trabajo y el perfil VTEP/L7 de Cilium de AWS revisado. El cambio de CNI en sí puede interrumpir el tráfico.
3. Trate la instalación del controlador como un **cambio de rutas**: su líder puede reemplazar una ruta existente para el mismo CIDR. No suponga que CreateRoute fallará sin modificar el destino anterior.
4. Verifique las IP directas de la nube/Hybrid, ClusterIP, el tráfico real de webhooks/balanceadores y ambas rutas de retorno. Coordine otros controladores de rutas para evitar que se sobrescriban continuamente.
5. Retire solo los recursos obsoletos cuya propiedad esté confirmada. No elimine todas las rutas manuales/BGP después de que el gateway ya haya reutilizado la misma tabla/CIDR.

La reversión requiere detener el controlador del gateway, restaurar los destinos anteriores registrados y la configuración compatible de Cilium/red, y volver a verificar el tráfico. La reversión/desinstalación de Helm por sí sola no revierte cambios de rutas externas. Las rutas más específicas son un diseño deliberado con efectos de prefijo más largo, no una solución genérica a conflictos.

---

## Prácticas recomendadas

### Seguridad

#### IAM con privilegios mínimos

Use las cuatro acciones del runtime y la política exacta para tablas de rutas propias descrita arriba; reserve DeleteRoute para el responsable de limpieza aprobado. Controle el acceso a los valores de Gateway, el ServiceAccount, las etiquetas de nodo y las asociaciones de Pod Identity. NET_ADMIN con red del host proporciona acceso privilegiado a la infraestructura, aunque el contenedor no tenga marcado `privileged: true`.

#### Prácticas recomendadas para grupos de seguridad

Use los CIDR privados reales de nodos Hybrid, los puertos previstos de las aplicaciones y las rutas específicas de API/DNS/métricas. Las NACL no tienen estado: permitir solo UDP 8472 entrante no define una política bidireccional funcional. Revise las direcciones de los nodos de reemplazo y todo el tráfico de retorno necesario.

#### Segmentación de red

El Gateway usa la red del host. El tratamiento del tráfico `hostNetwork` por la política de red habitual de Pods depende de la implementación; no sustituye los controles de nodo/ENI/firewall. Aplique políticas L3/L4 compatibles a los endpoints reales de las cargas de trabajo y verifique la identidad de origen después de NAT/encapsulación. Un selector CIDR no identifica un espacio de nombres de Kubernetes. Las reglas L7 de Cilium entran en conflicto con el perfil `l7Proxy=false` requerido por este gateway.

### Rendimiento

#### Dimensionamiento de instancias del gateway

Use el ancho de banda sostenido/por ráfagas permitido, PPS, tamaños de paquete, CPU/memoria y capacidad de reserva ante fallos. Las reglas originales de «actualizar por encima del 60 %, reducir por debajo del 20 %, elegir c6in por encima de 25 Gbps/hasta 100 Gbps» son heurísticas no medidas, no garantías de capacidad ni especificaciones actuales de familias de instancia. La tabla actual de operaciones de gateway de AWS enumera c6in.2xlarge con **hasta 40 Gbps**; la entrada anterior de 50 Gbps se conserva solo como cifra histórica no verificada.

La suma de NetworkIn/NetworkOut de EC2 durante un intervalo da bytes; divídala por el intervalo para obtener bytes/s. Estas métricas de instancia incluyen otro tráfico y por sí solas no miden el rendimiento de VXLAN/de la aplicación. No trate los puntos de datos Average/Maximum como una garantía de tasa de bits sostenida.

#### Supervisión de latencia

Prepare cargas de trabajo cliente existentes y aprobadas que tengan curl instalado; no instale paquetes al iniciar la prueba ni suponga que `compute-type=ec2` selecciona nodos de la nube. El destino debe estar realmente escuchando. Ejecute esta comprobación acotada desde cada ubicación seleccionada explícitamente, una vez para la IP directa del Pod y otra para ClusterIP/el endpoint real de la aplicación. `time_total` incluye DNS, conexión/TLS y procesamiento del servidor; no es el RTT de red aislado ni una prueba de sobrecarga.

```bash
#!/usr/bin/env bash
set -euo pipefail
: "${KUBE_CONTEXT:?Set the reviewed Kubernetes context}"
: "${PROBE_NAMESPACE:?Set the approved probe namespace}"
: "${PROBE_CLIENT_POD:?Set an existing client Pod with curl installed}"
: "${PROBE_URL:?Set the actual listening application URL}"
# Select and inspect the client node first; run separately from cloud and Hybrid clients.
kubectl --context "$KUBE_CONTEXT" -n "$PROBE_NAMESPACE" get pod "$PROBE_CLIENT_POD" -o wide
for attempt in 1 2 3; do
  kubectl --context "$KUBE_CONTEXT" -n "$PROBE_NAMESPACE" exec "$PROBE_CLIENT_POD" -- \
  curl --fail --show-error --silent --connect-timeout 3 --max-time 10 \
  --output /dev/null --write-out 'http_code=%{http_code} total_seconds=%{time_total}\n' \
  "$PROBE_URL"
done
```

### Costos

#### Costos del gateway

El software del gateway no tiene costo. Cuente EC2, almacenamiento, tarifas de administración de Auto Mode (solo para nodos del gateway que se ejecutan en Auto Mode), transferencia de datos entre zonas, conectividad privada y observabilidad, además de los costos normales del clúster/Hybrid Nodes. Que algo esté «dentro de la misma VPC» no significa que la transferencia entre zonas sea gratuita. Enrutar por otra zona puede agregar cargos de tráfico. Solo hay un líder activo; por eso, aunque haya nodos de gateway en varias zonas, el tráfico Hybrid de Pods, ALB o recopiladores en otras zonas pasa a la zona del líder ([guía de operaciones de AWS](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-gateway-operations.html)). En rutas de gran volumen, enrute directamente los CIDR de Pods mediante Cilium BGP para que el tráfico salga por TGW/VGW en la zona del propio Pod, y conserve el gateway para webhooks y tráfico de bajo volumen entre Pods.

**Estimaciones históricas, no cotizaciones actuales ni ahorros medidos:** no se puede recuperar la fuente de verificación de los siguientes precios/descuentos originales. Se conservan como contexto; antes de comprometerse, vuelva a calcular una estimación regional y fechada según el uso real y la [página de precios de EKS](https://aws.amazon.com/eks/pricing/), las condiciones de EC2 y las rutas de transferencia de datos.

| Componente | Estimación mensual original sin verificar (us-west-2) | Notas |
|-----------|-------------------------|-------|
| 2 × c6i.large (instancias del gateway) | ~$124 ($0,085/h cada una) | Precio bajo demanda |
| 2 × c6i.large (reservadas, 1 año) | ~$78 | RI sin pago inicial |
| 2 × c6i.large (Savings Plan, 1 año) | ~$81 | Compute Savings Plan |
| EBS (2 × gp3 de 20 GiB) | ~$3,20 | Almacenamiento mínimo |
| Transferencia de datos (supuesto original) | $0 | No es una regla universal; pueden aplicarse cargos entre zonas |
| **Total (bajo demanda)** | **~$127/mes** | Para 2 instancias del gateway |

#### Consejos para optimizar costos

Dimensione según las mediciones y el requisito de réplica en espera/fallo. Evalúe descuentos por compromiso según el uso estable y las condiciones reales en vez de suponer un ahorro fijo. Elija los tipos de capacidad conforme a un presupuesto de interrupciones explícito; no deduzca que Spot sea seguro porque existan dos réplicas ni que todos los despliegues del gateway toleren las interrupciones por igual.

### Integración con funciones existentes de Hybrid Nodes

| Función | Límite que se debe tener en cuenta |
|---|---|
| Cargas de trabajo de GPU | La accesibilidad de red es independiente de los controladores, complementos de dispositivos y compatibilidad con cargas GPU |
| Ubicación | Aplique etiquetas/taints a los nodos elegibles; un selector no aprovisiona capacidad |
| Redes restringidas | Proporcione las rutas privadas/API/registro/DNS necesarias; los nodos Hybrid no están completamente desconectados de AWS ni de las dependencias del plano de control |
| SSM / IAM Roles Anywhere | Las credenciales del nodo Hybrid son independientes del rol de carga de trabajo del Gateway en la nube |
| Ciclo de vida de nodeadm | La incorporación de nodos y la reconciliación del túnel del Gateway son responsabilidades distintas |
| Políticas de red | Valide el comportamiento L3/L4 compatible y las excepciones de red del host; no hay compatibilidad L7 general |
| Services y webhooks | Verifique SNAT de ClusterIP, rutas, accesibilidad de endpoints y la ruta real de solicitudes |
| DNS | Los distintos tipos de nodos necesitan la configuración DNS adecuada; la instalación del Gateway no establece la disponibilidad de DNS |

Cada despliegue de Gateway pertenece a un clúster de EKS. El acceso desde VPC adicionales requiere un diseño independiente y compatible de rutas/seguridad/direcciones; no deduzca que un solo release de Helm crea enrutamiento multiclúster o de Transit Gateway. Los prefijos de VPC configurados determinan la coincidencia de VTEP, no una ruta predeterminada automática a Internet. Los ajustes existentes de DX/VPN pueden requerir cambios de MTU, rutas y firewall aunque el gateway no cree la conexión subyacente.

---

## Referencias

### Documentación de AWS

- [Descripción general de EKS Hybrid Nodes](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-overview.html)
- [Redes de EKS Hybrid Nodes](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-networking.html)
- [Configuración de CNI para EKS Hybrid Nodes](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-cni.html)
- [Solución de problemas de EKS Hybrid Nodes](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-troubleshooting.html)
- [Tablas de rutas de VPC](https://docs.aws.amazon.com/vpc/latest/userguide/VPC_Route_Tables.html)
- [Requisitos del CNI de Gateway](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-gateway-cni.html)

### Código abierto

- [Repositorio de EKS Hybrid Nodes Gateway en GitHub](https://github.com/aws/eks-hybrid-nodes-gateway)
- [Documentación de Cilium VTEP](https://docs.cilium.io/en/stable/network/vtep/)
- [Documentación de VXLAN en Linux](https://www.kernel.org/doc/html/latest/networking/vxlan.html)

### Documentos internos relacionados

- [Requisitos previos y requisitos del sistema](./01-prerequisites.md)
- [Configuración de red](./02-network-configuration.md)
- [Arranque de nodos](./04-node-bootstrap.md)
- [Operaciones y mantenimiento](./08-operations.md)
- [Configuración del sistema operativo en bare metal](./09-bare-metal-os-setup.md)
- [Análisis detallado de Cilium](../networking/cilium/README.md)
- [VPC CNI](../networking/01-vpc-cni.md)

---

< [Anterior: Configuración del sistema operativo en bare metal](./09-bare-metal-os-setup.md) | [Tabla de contenido](./README.md) >
