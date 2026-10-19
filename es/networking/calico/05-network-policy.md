# Parte 5: Políticas de red

> **Base de revisión**: Calico 3.32.2; Kubernetes 1.34–1.36 es el rango probado con Calico 3.32. **Última actualización**: 12 de septiembre de 2026.
>
> Los ejemplos presuponen el servidor de API estándar de Calico (`projectcalico.org/v3`), el almacén de datos de Kubernetes y un plano de datos compatible que aplique las políticas. Utilice un namespace dedicado, `calico-demo`, con etiquetas de cargas de trabajo conocidas, endpoints listos y una configuración básica que funcione antes de aplicar políticas. Las secciones presentan patrones independientes, no un único conjunto de manifiestos. Las políticas existentes de mayor prioridad, la implementación de DNS, el NAT de los Service, las políticas de host y el comportamiento de las aplicaciones afectan a los resultados. Esta revisión no incluyó pruebas en un clúster de producción, un servidor de admisión ni el reenvío de paquetes.

## Introducción

Las políticas de red controlan las conexiones permitidas entre cargas de trabajo y otros endpoints. Calico añade políticas ordenadas, acciones explícitas, ámbito global y controles de endpoints de host a la API estándar de Kubernetes. La disponibilidad de las funciones depende del producto y del mecanismo de aplicación: las políticas basadas en dominios DNS son una extensión comercial, mientras que las políticas HTTP de Open Source requieren la integración documentada con Istio/Dikastes.

Este análisis detallado abarca las políticas estándar de Kubernetes y las funciones ampliadas de Calico, con patrones y ejemplos para requisitos de seguridad empresariales.

***

## NetworkPolicy estándar de Kubernetes

### Fundamentos de NetworkPolicy

NetworkPolicy de Kubernetes es un recurso con ámbito de namespace que selecciona Pods. El aislamiento de entrada y de salida es independiente; el tráfico permitido en cada dirección aislada es la unión del tráfico permitido por las políticas de Kubernetes coincidentes. Si ambos extremos están aislados, tanto la política de salida del origen como la de entrada del destino deben permitir una conexión nueva. Las respuestas a una conexión permitida no necesitan una regla adicional de autorización en sentido inverso.

Las entradas de una lista `from`/`to` son alternativas **OR**. Un `namespaceSelector` y un `podSelector` dentro de la misma entrada son condiciones **AND**. Un selector de Pods sin selector de namespace se refiere al namespace de la política.

Si ninguna política de Kubernetes se aplica a una dirección, esta API no la aísla; eso no anula los firewalls de host, las políticas de Calico ni otros controles. Los efectos de los cambios de política sobre las conexiones existentes dependen de la implementación, por lo que debe validar con conexiones nuevas. La dirección que observa `ipBlock` antes o después del NAT de un Service o balanceador también depende de la implementación.

![Comparación entre una red sin NetworkPolicy, donde todos los Pods pueden comunicarse entre sí, y otra donde una NetworkPolicy deja una única ruta explícitamente permitida y bloquea las demás.](../../.gitbook/assets/en-networking-calico-05-network-policy-0.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-networking-calico-05-network-policy-0.html)

> Las flechas representan conexiones nuevas bajo las políticas ilustradas, no los paquetes de respuesta de una conexión permitida. El ejemplo presupone que no hay otras políticas, firewalls ni restricciones de ruta; la mera existencia de una NetworkPolicy no aísla todos los Pods ni todas las direcciones.

### Estructura básica de NetworkPolicy

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: example-policy
  namespace: calico-demo
spec:
  # Which pods this policy applies to
  podSelector:
    matchLabels:
      app: web

  # Policy types: Ingress, Egress, or both
  policyTypes:
    - Ingress
    - Egress

  # Ingress rules (who can connect TO these pods)
  ingress:
    - from:
        - podSelector:
            matchLabels:
              app: frontend
        - namespaceSelector:
            matchLabels:
              purpose: monitoring
        - ipBlock:
            cidr: 10.0.0.0/8
            except:
              - 10.0.1.0/24
      ports:
        - protocol: TCP
          port: 8080

  # Egress rules (where these pods can connect TO)
  egress:
    - to:
        - podSelector:
            matchLabels:
              app: database
      ports:
        - protocol: TCP
          port: 5432
```

### Limitaciones de NetworkPolicy de Kubernetes

| Función | NetworkPolicy de Kubernetes | Extensión de Calico / requisito previo |
| --- | --- | --- |
| Ámbito | Política de Pods con ámbito de namespace | GlobalNetworkPolicy puede seleccionar cargas de trabajo en varios namespaces y HostEndpoints |
| Orden y acciones | Reglas de autorización aditivas; sin orden de políticas definido por el usuario | Nivel/orden y Allow, Deny, Log, Pass |
| Puertos | TCP/UDP/SCTP, puertos con nombre y rangos numéricos mediante `endPort` (estable desde 1.25; requiere soporte del plugin) | Sintaxis de rangos de puertos de Calico y coincidencias adicionales de protocolos IP/ICMP |
| Métodos y rutas HTTP | No forman parte de esta API | Las reglas `http` de Open Source requieren una integración configurada de Istio/Dikastes que aplique las restricciones en la capa de aplicación |
| Nombres de dominio DNS | No forman parte de esta API | Por ejemplo, las políticas de dominio de Calico Enterprise; `domains` no existe en el CRD de Open Source 3.32 |
| Interfaces de host | No es un firewall general de nodos | Políticas de HostEndpoint con comportamientos distintos para tráfico local, reenviado y reglas failsafe |

El ámbito del objeto NetworkPolicy estándar es distinto del de las API más recientes de políticas de clúster de Kubernetes; no suponga que todas las API de seguridad de red de Kubernetes están limitadas a un namespace. Compruebe el soporte de protocolos y registros del plano de datos elegido, en lugar de equiparar la aceptación del esquema con la aplicación efectiva de la política.

***

## Extensiones de NetworkPolicy de Calico

### Soporte de protocolos adicionales

Los ejemplos SCTP requieren un plano de datos clásico compatible: el plano eBPF de Calico 3.32 no admite políticas ni Service SCTP.

Calico admite otros protocolos además de TCP y UDP:

```yaml
apiVersion: projectcalico.org/v3
kind: NetworkPolicy
metadata:
  name: extended-protocols
  namespace: calico-demo
spec:
  selector: app == 'network-tools'

  ingress:
    # ICMP ping
    - action: Allow
      protocol: ICMP
      icmp:
        type: 8  # Echo Request
        code: 0

    # ICMPv6
    - action: Allow
      protocol: ICMPv6
      icmp:
        type: 128  # Echo Request

    # SCTP
    - action: Allow
      protocol: SCTP
      destination:
        ports:
          - 3868  # Diameter

    # UDP with port range
    - action: Allow
      protocol: UDP
      destination:
        ports:
          - "5000:6000"  # Port range
```

### Rangos de puertos y puertos con nombre

```yaml
apiVersion: projectcalico.org/v3
kind: NetworkPolicy
metadata:
  name: port-examples
  namespace: calico-demo
spec:
  selector: app == 'multi-port-app'

  ingress:
    # Port range
    - action: Allow
      protocol: TCP
      destination:
        ports:
          - "8080:8090"

    # Named ports (from pod spec)
    - action: Allow
      protocol: TCP
      destination:
        ports:
          - http      # References containerPort name
          - metrics   # References containerPort name

    # Mix of specific ports and ranges
    - action: Allow
      protocol: TCP
      destination:
        ports:
          - 22
          - 80
          - 443
          - "3000:3100"
```

### Sintaxis de selectores ampliada

Calico utiliza selectores basados en expresiones. Las reglas siguientes ilustran alternativas: reunir todas las reglas Allow amplias en una sola política aumenta el conjunto de conexiones permitidas. `app != 'untrusted'` también coincide con recursos que carecen de la etiqueta; no demuestra que sean de confianza.

`selector: !has(x)` coincide con recursos conocidos dentro del ámbito que carecen de la etiqueta. `notSelector: has(x)` niega la coincidencia del paquete y también puede coincidir con direcciones externas que no figuran en ese selector. El `selector: all()` de una regla no coincide con todos los paquetes; para ello, omita las condiciones de selección de endpoints.

```yaml
apiVersion: projectcalico.org/v3
kind: NetworkPolicy
metadata:
  name: selector-examples
  namespace: calico-demo
spec:
  # Label equality
  selector: app == 'web'

  ingress:
    # Set membership
    - action: Allow
      source:
        selector: app in {'frontend', 'api-gateway', 'monitoring'}

    # Negation
    - action: Allow
      source:
        selector: app != 'untrusted'

    # Label existence
    - action: Allow
      source:
        selector: has(security-cleared)

    # Combining conditions (AND)
    - action: Allow
      source:
        selector: app == 'backend' && tier == 'internal'

    # OR inside one selector expression
    - action: Allow
      source:
        selector: (app == 'frontend') || (app == 'api')

    # Namespace selector
    - action: Allow
      source:
        namespaceSelector: environment == 'production'
        selector: app == 'authorized-client'
```

***

## GlobalNetworkPolicy

GlobalNetworkPolicy no pertenece a un namespace y puede seleccionar endpoints de cargas de trabajo de varios namespaces o HostEndpoints. `selector: all()` por sí solo no significa «solo todos los Pods de aplicaciones». Estos ejemplos limitan explícitamente las cargas seleccionadas al namespace de demostración, conservando el tráfico del sistema y de los hosts.

### Denegación predeterminada con excepciones explícitas

La política vacía selecciona ambas direcciones. Al omitir `order`, se evalúa después de las políticas con un orden explícito; 10.000 no es un valor especial de «prioridad más baja». Las reglas vacías no anulan una acción Allow anterior que haya finalizado la evaluación. Utilice un nivel anterior administrado por separado para las restricciones que las políticas de aplicaciones no deban anular.

```yaml
apiVersion: projectcalico.org/v3
kind: GlobalNetworkPolicy
metadata:
  name: default.demo-default-deny
spec:
  tier: default
  namespaceSelector: kubernetes.io/metadata.name == 'calico-demo'
  types: [Ingress, Egress]
  ingress: []
  egress: []
---
apiVersion: projectcalico.org/v3
kind: GlobalNetworkPolicy
metadata:
  name: default.demo-essential-egress
spec:
  tier: default
  order: 100
  namespaceSelector: kubernetes.io/metadata.name == 'calico-demo'
  selector: needs-platform == 'true'
  types: [Egress]
  egress:
    - action: Allow
      protocol: UDP
      destination:
        namespaceSelector: kubernetes.io/metadata.name == 'kube-system'
        selector: k8s-app == 'kube-dns'
        ports: [53]
    - action: Allow
      protocol: TCP
      destination:
        namespaceSelector: kubernetes.io/metadata.name == 'kube-system'
        selector: k8s-app == 'kube-dns'
        ports: [53]
    - action: Allow
      destination:
        services:
          name: kubernetes
          namespace: default
```

Este ejemplo permite la salida hacia servicios de plataforma solo a las cargas etiquetadas con `needs-platform=true`. La coincidencia de Service sigue los endpoints y puertos reales de `kubernetes/default` en el **almacén de datos de Kubernetes**; se ignora con un almacén etcd. Evite combinar esa coincidencia de Service con puertos, CIDR o selectores de destino. El acceso de red a la API es distinto de su autenticación y del RBAC.

Confirme la implementación real de DNS. Combinar selectores de namespace y de Pods evita que un Pod ajeno etiquetado como `kube-dns` se convierta en un resolvedor de confianza. El DNS local de nodo necesita una coincidencia distinta para la ruta real. Crear una política vacía en `kube-system` antes de identificar las dependencias del sistema puede interrumpir el clúster; demuestre ese patrón en un namespace de pruebas separado.

### Restricción de salida en un nivel anterior

Este ejemplo independiente bloquea la dirección IPv4 de metadatos para las cargas de demostración seleccionadas y delega el resto del tráfico al finalizar su nivel. No ofrece protección completa frente a SSRF, protección de procesos privilegiados o que comparten la red del host, ni cobertura de todos los endpoints de metadatos de la plataforma.

```yaml
apiVersion: projectcalico.org/v3
kind: Tier
metadata:
  name: egress-guardrail
spec:
  order: 50
  defaultAction: Pass
---
apiVersion: projectcalico.org/v3
kind: GlobalNetworkPolicy
metadata:
  name: egress-guardrail.block-imds-v4
spec:
  tier: egress-guardrail
  order: 10
  namespaceSelector: kubernetes.io/metadata.name == 'calico-demo'
  types: [Egress]
  egress:
    - action: Deny
      destination:
        nets: [169.254.169.254/32]
```

Evite situar una acción Pass incondicional antes de restricciones posteriores del mismo nivel. Conserve las rutas de identidad y DNS que necesita la plataforma y revise cómo se aplican realmente las políticas al tráfico de las cargas hacia el host.

***

## NetworkSet y GlobalNetworkSet

Los NetworkSet etiquetan grupos reutilizables de IP/CIDR; los selectores de las políticas se refieren a sus etiquetas, no al nombre de los objetos. Las direcciones siguientes son ilustrativas y no proceden de una fuente real de geolocalización o amenazas. Un selector de etiquetas también puede coincidir con endpoints que tengan las mismas etiquetas; por eso, controle esas etiquetas y el ámbito de namespace o global previsto.

Use `namespaceSelector: global()` en la coincidencia de entidad de una política con ámbito de namespace para seleccionar un GlobalNetworkSet. Los NetworkSet con ámbito de namespace permanecen en el namespace seleccionado. Si se solapan los rangos de confianza y los bloqueados, evalúe primero la denegación; una acción Allow anterior finaliza la evaluación.

### NetworkSet (ámbito de namespace)

```yaml
apiVersion: projectcalico.org/v3
kind: NetworkSet
metadata:
  name: corporate-networks
  namespace: calico-demo
  labels:
    network-type: corporate
spec:
  nets:
    - 10.0.0.0/8
    - 172.16.0.0/12
    - 192.168.0.0/16

---
# Reference in policy
apiVersion: projectcalico.org/v3
kind: NetworkPolicy
metadata:
  name: allow-corporate
  namespace: calico-demo
spec:
  selector: app == 'internal-app'

  ingress:
    - action: Allow
      source:
        selector: network-type == 'corporate'  # References NetworkSet by label
```

### GlobalNetworkSet (ámbito de clúster)

```yaml
apiVersion: projectcalico.org/v3
kind: GlobalNetworkSet
metadata:
  name: external-trusted-ips
  labels:
    network-group: external-trusted
spec:
  nets:
    - 203.0.113.0/24     # Partner network
    - 198.51.100.0/24    # CDN network
    - 192.0.2.50/32      # Specific trusted IP

---
apiVersion: projectcalico.org/v3
kind: GlobalNetworkSet
metadata:
  name: demo-blocked-networks
  labels:
    network-group: blocked
spec:
  nets:
    # Illustrative test ranges, not geolocation or threat intelligence
    - 192.0.2.128/25
    - 203.0.113.128/25

---
# Reference in GlobalNetworkPolicy
apiVersion: projectcalico.org/v3
kind: GlobalNetworkPolicy
metadata:
  name: external-access-control
spec:
  namespaceSelector: kubernetes.io/metadata.name == 'calico-demo'
  selector: has(external-facing)
  order: 200
  types:
    - Ingress

  ingress:
    # Deny overlaps before considering trusted ranges.
    - action: Deny
      source:
        namespaceSelector: global()
        selector: network-group == 'blocked'
    - action: Allow
      source:
        namespaceSelector: global()
        selector: network-group == 'external-trusted'
```

***

## Políticas por niveles

Los niveles están disponibles en Calico Open Source 3.32. Agrupan políticas de Calico con ámbito de namespace y globales; no representan una progresión desde NetworkPolicy de Kubernetes hasta GlobalNetworkPolicy.

### Evaluación y valores predeterminados

En las políticas normales de endpoints, los niveles se evalúan en orden creciente de `order`, y las políticas de cada nivel también en orden creciente de `order`. Las políticas sin orden definido se evalúan después de las que tienen un orden explícito. Tenga en cuenta el endpoint seleccionado **y la dirección del tráfico**.

| Situación | Resultado |
| --- | --- |
| Ninguna política del nivel selecciona ese endpoint y esa dirección | Se omite el nivel |
| Una regla permite o deniega | Finaliza la decisión de política para ese endpoint y esa dirección |
| Una regla registra | Continúa con la siguiente regla |
| Una regla ejecuta Pass | Omite las políticas restantes de este nivel y pasa al siguiente nivel aplicable |
| Un nivel aplicable no tiene una regla coincidente que finalice la evaluación | Aplica su `defaultAction`, cuyo valor predeterminado es Deny |
| El último nivel aplicable ejecuta Pass | Evalúa los Profiles del endpoint; si ningún perfil permite el tráfico, lo deniega |

Esto no equivale a «si ninguna regla coincide, siempre se pasa al siguiente nivel». Además, una acción Allow en un endpoint no omite la política del otro extremo. Las políticas de host previas a DNAT y sin seguimiento de conexiones tienen un comportamiento distinto al continuar la evaluación, como se explica más adelante.

El nivel integrado `default` tiene un orden fijo de **1.000.000**, no 1.000 ni infinito. Las NetworkPolicy de Kubernetes y las políticas de Calico sin nivel explícito pertenecen a él. Los niveles actuales `kube-admin` y `kube-baseline` utilizan 1.000 y 10.000.000, con Pass como acción predeterminada, para la integración correspondiente con políticas de clúster de Kubernetes; por tanto, `default` no es siempre el último nivel posible.

### Decisiones separadas de seguridad, plataforma y aplicaciones

Estos niveles de ejemplo utilizan Pass al finalizar los niveles de seguridad y plataforma, de modo que se evalúen todas sus reglas aplicables antes de delegar. La creación y el cambio de orden de los niveles requieren permisos administrados de forma centralizada.

```yaml
apiVersion: projectcalico.org/v3
kind: Tier
metadata:
  name: security
spec:
  order: 100
  defaultAction: Pass
---
apiVersion: projectcalico.org/v3
kind: Tier
metadata:
  name: platform
spec:
  order: 200
  defaultAction: Pass
---
apiVersion: projectcalico.org/v3
kind: Tier
metadata:
  name: application
spec:
  order: 500
  defaultAction: Deny
```

El siguiente ejemplo utiliza una dirección de amenaza reservada para documentación y, después, una regla separada para datos restringidos. Una acción Pass al final de la primera política de seguridad omitiría la segunda. Delegar al **final del nivel** evita esa omisión. Las etiquetas de datos restringidos ilustran la segmentación, no el cumplimiento completo de PCI DSS.

```yaml
apiVersion: projectcalico.org/v3
kind: GlobalNetworkSet
metadata:
  name: demo-threats
  labels:
    network-group: demo-threat
spec:
  nets:
    - 192.0.2.100/32
---
apiVersion: projectcalico.org/v3
kind: GlobalNetworkPolicy
metadata:
  name: security.block-threats
spec:
  tier: security
  order: 10
  namespaceSelector: kubernetes.io/metadata.name == 'calico-demo'
  types: [Ingress, Egress]
  ingress:
    - action: Deny
      source:
        namespaceSelector: global()
        selector: network-group == 'demo-threat'
  egress:
    - action: Deny
      destination:
        namespaceSelector: global()
        selector: network-group == 'demo-threat'
---
apiVersion: projectcalico.org/v3
kind: GlobalNetworkPolicy
metadata:
  name: security.restricted-data
spec:
  tier: security
  order: 20
  namespaceSelector: kubernetes.io/metadata.name == 'calico-demo'
  selector: data-scope == 'restricted'
  types: [Ingress]
  ingress:
    - action: Deny
      source:
        notSelector: data-scope == 'restricted'
---
apiVersion: projectcalico.org/v3
kind: GlobalNetworkPolicy
metadata:
  name: platform.dns
spec:
  tier: platform
  order: 10
  namespaceSelector: kubernetes.io/metadata.name == 'calico-demo'
  types: [Egress]
  egress:
    - action: Allow
      protocol: UDP
      destination:
        namespaceSelector: kubernetes.io/metadata.name == 'kube-system'
        selector: k8s-app == 'kube-dns'
        ports: [53]
    - action: Allow
      protocol: TCP
      destination:
        namespaceSelector: kubernetes.io/metadata.name == 'kube-system'
        selector: k8s-app == 'kube-dns'
        ports: [53]
---
apiVersion: projectcalico.org/v3
kind: NetworkPolicy
metadata:
  name: application.frontend
  namespace: calico-demo
spec:
  tier: application
  order: 10
  selector: app == 'frontend'
  types: [Ingress, Egress]
  ingress:
    - action: Allow
      protocol: TCP
      source:
        selector: app == 'gateway'
      destination:
        ports: [8080]
  egress:
    - action: Allow
      protocol: TCP
      destination:
        selector: app == 'backend'
        ports: [8080]
```

`namespaceSelector: global()` junto con un selector de etiquetas separado selecciona el GlobalNetworkSet. `global(label == 'value')` no es una sintaxis válida. La acción Allow de DNS en la plataforma es una excepción deliberada que finaliza la evaluación de salida de la carga seleccionada; las reglas del nivel de aplicaciones no pueden restringir después esa excepción. La política de aplicaciones regula únicamente el frontend seleccionado, no todas las cargas del namespace.

El ejemplo de DNS presupone Pods CoreDNS convencionales con namespace y etiquetas verificados. NodeLocal DNSCache o el DNS local de nodo de EKS Auto Mode necesitan reglas para la ruta real del resolvedor, no un selector de Pods copiado sin cambios. Conserve el acceso al resolvedor necesario y valide las consultas tanto UDP como TCP.

### Integración de RBAC de niveles

El RBAC de niveles de Calico utiliza los pseudorrecursos `tier.networkpolicies` y `tier.globalnetworkpolicies`, además de `get` sobre el Tier de destino. El autorizador de Calico comprueba explícitamente nombres sintéticos como `application.*`. Esto no es un comodín general de Kubernetes en `resourceNames` para los recursos ordinarios `networkpolicies`.

El siguiente ejemplo completo de vinculación permite que una cuenta de servicio edite políticas con ámbito de namespace en el nivel de aplicaciones. No concede permisos para crear o reordenar niveles ni para administrar políticas globales.

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: policy-editor
  namespace: calico-demo
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: demo-get-application-tier
rules:
  - apiGroups: ["projectcalico.org"]
    resources: ["tiers"]
    resourceNames: ["application"]
    verbs: ["get"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: demo-get-application-tier
subjects:
  - kind: ServiceAccount
    name: policy-editor
    namespace: calico-demo
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: demo-get-application-tier
---
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: demo-edit-application-policies
  namespace: calico-demo
rules:
  - apiGroups: ["projectcalico.org"]
    resources: ["tier.networkpolicies"]
    resourceNames: ["application.*"]
    verbs: ["get", "list", "watch", "create", "update", "patch", "delete"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: demo-edit-application-policies
  namespace: calico-demo
subjects:
  - kind: ServiceAccount
    name: policy-editor
    namespace: calico-demo
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: Role
  name: demo-edit-application-policies
```

La edición de políticas globales utiliza `tier.globalnetworkpolicies` en un ClusterRole y un ClusterRoleBinding con ámbito deliberadamente restringido. Mantenga separado el permiso `get` sobre el Tier previsto de los permisos para cambiar el orden de los niveles.

El ejemplo presupone el servidor de API agregado estándar de Calico. Los CRD v3 nativos utilizan un webhook de admisión para autorizar la creación, actualización y eliminación según el nivel; ese webhook no puede restringir GET/LIST/WATCH. Evite afirmar que ambos modos ofrecen el mismo aislamiento de lectura. Un simple `kubectl auth can-i` no valida las comprobaciones de nivel combinadas de Calico: pruebe solicitudes reales permitidas y prohibidas en un entorno aislado, con un principal sin otras vinculaciones más amplias. El RBAC de Kubernetes es aditivo, por lo que un permiso amplio existente puede anular la restricción prevista.

***

## Política de salida basada en FQDN

El CRD de Open Source 3.32 no tiene el campo `destination.domains` ni el campo `dnsTrustedServers` de Felix. Configurar `policySyncPathPrefix` habilita la ruta de sincronización de políticas que utilizan las integraciones de capa de aplicación; no añade políticas basadas en dominios DNS a Open Source.

Calico Enterprise 3.23 documenta las coincidencias de dominios DNS en reglas **Allow de salida**. El controlador aprende las respuestas A/AAAA/CNAME de servidores DNS de confianza y permite las IP de destino coincidentes. La aplicación de la política se basa en IP, no en la autenticación del nombre de host HTTPS, por lo que las IP de destino compartidas y la identidad de la aplicación siguen siendo relevantes. Utilice selectores de cargas o de Service para los servicios internos del clúster.

El siguiente ejemplo comercial presupone que la función está habilitada, el resolvedor de confianza se ha verificado y ninguna acción Allow anterior que finalice la evaluación la omite. Cada regla tiene un único mapa `destination`; repetir esa clave YAML podría descartar silenciosamente la restricción de dominio.

```yaml
# Calico Enterprise 3.23 example; NOT an Open Source 3.32 resource.
apiVersion: projectcalico.org/v3
kind: NetworkPolicy
metadata:
  name: allow-approved-domains
  namespace: calico-demo
spec:
  selector: app == 'external-api-client'
  types: [Egress]
  egress:
    - action: Allow
      protocol: UDP
      destination:
        namespaceSelector: kubernetes.io/metadata.name == 'kube-system'
        selector: k8s-app == 'kube-dns'
        ports: [53]
    - action: Allow
      protocol: TCP
      destination:
        namespaceSelector: kubernetes.io/metadata.name == 'kube-system'
        selector: k8s-app == 'kube-dns'
        ports: [53]
    - action: Allow
      protocol: TCP
      destination:
        domains:
          - api.github.com
          - "*.example.com"
        ports: [443]
```

Sustituya el dominio de documentación por un dominio real aprobado. `*.example.com` coincide con `api.example.com` y `deep.api.example.com`, pero no con el dominio raíz `example.com`. El comodín debe ocupar un componente completo y solo se admite uno. El modo de políticas DNS inline admite comodines al principio; los patrones con el comodín en otra posición requieren un modo documentado adecuado. Un sufijo amplio como `*.amazonaws.com` no es un límite de cuenta de AWS ni de IAM.

Mantenga el resolvedor real accesible por UDP y TCP y haga coincidir sus IP con la configuración de DNS de confianza. Los resolvedores locales de nodo necesitan un tratamiento específico del despliegue. La guía comercial excluye las políticas de dominio en el punto de aplicación de salida de los Pods de pasarela de salida, porque su caché DNS compartida por todo el nodo puede producir coincidencias ausentes o intermitentes.

En Open Source, utilice un proxy o una pasarela de salida explícitos con autorización propia de la aplicación, o NetworkSet de IP/CIDR mantenidos cuando sea adecuado. Una consulta DNS puntual no sustituye una política de dominio aplicada de forma continua.

***

## Filtrado de métodos HTTP (capa 7)

Calico Open Source 3.32 admite políticas HTTP mediante la integración documentada **Istio + Dikastes**. Instalar un proxy Envoy cualquiera o añadir un campo `http` a una política CNI normal no habilita la aplicación de políticas de capa 7.

Los requisitos incluyen la API Policy Sync de Felix, el montaje del socket CSI de Calico, la inyección de Dikastes y la autorización externa de Envoy en la ruta de tráfico correspondiente. La guía actual de integración describe la inyección de Istio mediante sidecars nativos de Kubernetes y recomienda Istio 1.28.1; eso no garantiza la compatibilidad de todas las versiones posteriores de Istio. Consulte la [guía de instalación de Istio](../../service-mesh/istio/01-installation.md), los periodos de soporte de ambos proyectos y la integración real antes de elegir una combinación de producción. Aquí no se desplegó esa integración.

Estos son ejemplos de **Allow de entrada** sobre una carga que ya tiene la integración configurada. Para filtrar métodos o rutas HTTPS, el proxy que aplica la política debe ver la solicitud HTTP después de terminar TLS. Las etiquetas de los Pods de origen identifican cargas, no usuarios finales autenticados; configure la identidad de cargas de confianza y la ruta mTLS de la integración, y conserve el acceso de red que necesitan DNS y el plano de control de Istio. Valide las solicitudes permitidas y denegadas, incluido el comportamiento ante fallos del proxy o del servicio de autorización, antes de confiar en la política.

### Reglas de coincidencia HTTP

```yaml
apiVersion: projectcalico.org/v3
kind: GlobalNetworkPolicy
metadata:
  name: l7-http-policy
spec:
  namespaceSelector: kubernetes.io/metadata.name == 'calico-demo'
  selector: app == 'api-server'
  order: 300
  types:
    - Ingress

  ingress:
    # Allow only GET and HEAD for read-only clients
    - action: Allow
      source:
        selector: role == 'reader'
      http:
        methods:
          - GET
          - HEAD
        paths:
          - prefix: /api/v1/

    # Allow the listed methods for admin-labeled workloads
    - action: Allow
      source:
        selector: role == 'admin'
      http:
        methods:
          - GET
          - POST
          - PUT
          - DELETE
          - PATCH

    # Allow health checks
    - action: Allow
      http:
        methods:
          - GET
        paths:
          - exact: /health
          - exact: /ready
```

### Filtrado basado en rutas

```yaml
apiVersion: projectcalico.org/v3
kind: NetworkPolicy
metadata:
  name: path-based-policy
  namespace: calico-demo
spec:
  selector: app == 'web-app'

  ingress:
    # Public endpoints
    - action: Allow
      http:
        paths:
          - prefix: /public/
          - exact: /

    # Admin endpoints - restricted
    - action: Allow
      source:
        selector: role == 'admin'
      http:
        paths:
          - prefix: /admin/

    # API endpoints - authenticated only
    - action: Allow
      source:
        selector: has(api-access)
      http:
        paths:
          - prefix: /api/
```

***

## Protección de endpoints de host

Un HostEndpoint representa una interfaz de un nodo administrado por Calico. Crearlo puede cambiar inmediatamente la conectividad del host. `defaultEndpointToHostAction` controla el tráfico de las cargas hacia su host local; no crea HostEndpoints. `Installation.calicoNetwork.hostPorts` controla el soporte de hostPort, no la protección automática del host.

### Endpoint de host y política manuales

El siguiente **ejemplo parcial no es un firewall completo de host**. Presupone un nodo de prueba autogestionado, `demo-worker`, con dirección `10.0.1.10`, un bastión `10.0.0.100`, un origen del plano de control `10.0.1.5` y la interfaz `eth0`. Sustituya esos valores por identidades y direcciones verificadas, y prepare todas las reglas necesarias de administración, DNS, DHCP, BGP, API, comprobaciones de estado y salida antes de crear el HostEndpoint. El ejemplo no representa un nodo del plano de control administrado por EKS.

```yaml
apiVersion: projectcalico.org/v3
kind: GlobalNetworkPolicy
metadata:
  name: default.demo-worker-ingress
spec:
  order: 100
  selector: host-demo == 'true' && !has(projectcalico.org/namespace)
  types: [Ingress]
  ingress:
    - action: Allow
      protocol: TCP
      source:
        nets: [10.0.0.100/32]
      destination:
        ports: [22]
    - action: Allow
      protocol: TCP
      source:
        nets: [10.0.1.5/32]
      destination:
        ports: [10250]
---
apiVersion: projectcalico.org/v3
kind: HostEndpoint
metadata:
  name: demo-worker-eth0
  labels:
    host-demo: "true"
spec:
  node: demo-worker
  interfaceName: eth0
  expectedIPs: [10.0.1.10]
```

La regla de kubelet se dirige al endpoint autenticado 10250 del nodo. Evite abrir el antiguo puerto de solo lectura 10255 sin autenticación como requisito predeterminado. El ejemplo solo define entrada; un HostEndpoint creado manualmente sin política o perfil de salida puede denegar el tráfico originado en el host. Complete primero la configuración básica real.

Las reglas failsafe predeterminadas de Calico incluyen TCP 22 de entrada y otros puertos de conectividad. Esas excepciones eluden la restricción pretendida por la regla SSH anterior, de modo que esta por sí sola **no** limita SSH al bastión. Revise la lista failsafe y una vía de recuperación probada antes de modificarla; evite vaciar las listas sin comprobar las consecuencias.

### Endpoints de host automáticos

El campo `KubeControllersConfiguration.spec.controllers.node.hostEndpoint.autoCreate` del controlador de nodos regula la creación automática. Utilice un parche de fusión para conservar los demás ajustes del controlador:

```bash
kubectl get kubecontrollersconfiguration.projectcalico.org default -o yaml
# Apply only after reviewing existing host endpoints and global policies.
kubectl patch kubecontrollersconfiguration.projectcalico.org default --type=merge \
  -p '{"spec":{"controllers":{"node":{"hostEndpoint":{"autoCreate":"Enabled"}}}}}'
```

Esto puede afectar a todos los nodos aptos. Los endpoints automáticos suelen incluir un perfil que permite el tráfico de forma predeterminada; ese perfil no anula una acción Deny de una política coincidente. Las plantillas personalizadas y `createDefaultHostEndpoint` pueden reducir el conjunto de endpoints generado, pero cambiarlos en un despliegue existente exige revisar primero los endpoints y las políticas actuales.

### Tráfico local y reenviado

Las políticas normales de host utilizan false como valor predeterminado de `applyOnForward`. Si se establece en true, la política también se aplica al tráfico reenviado, que aún debe superar las políticas de carga correspondientes. Si ninguna política de reenvío selecciona el endpoint y la dirección, el tráfico reenviado se permite de forma predeterminada; si una política seleccionada no lo permite, se deniega. El tráfico que termina localmente en el host tiene un comportamiento distinto de denegación predeterminada, sujeto a perfiles y reglas failsafe.

## Políticas DoNotTrack y PreDNAT

Estos patrones de políticas de host se aplican en Linux. Regulan HostEndpoints; no permiten deshabilitar el seguimiento de conexiones de Pods ordinarios seleccionados. Confirme el soporte en el plano de datos elegido. `doNotTrack` y `preDNAT` no pueden ser true a la vez, y cualquiera de los dos requiere `applyOnForward: true`.

### DoNotTrack

Una acción Allow sin seguimiento omite el seguimiento de conexiones del tráfico coincidente. No mejora siempre el rendimiento y puede entrar en conflicto con una ruta de Service/NAT que necesite conntrack. Las solicitudes y las respuestas requieren reglas explícitas; este ejemplo presupone un proceso DNS en el host de prueba que atiende directamente a la subred de clientes de confianza.

```yaml
apiVersion: projectcalico.org/v3
kind: GlobalNetworkPolicy
metadata:
  name: default.demo-untracked-dns
spec:
  selector: host-demo == 'true' && !has(projectcalico.org/namespace)
  order: 10
  types: [Ingress, Egress]
  doNotTrack: true
  applyOnForward: true
  ingress:
    - action: Allow
      protocol: UDP
      source:
        nets: [10.0.0.0/24]
      destination:
        ports: [53]
    - action: Allow
      protocol: TCP
      source:
        nets: [10.0.0.0/24]
      destination:
        ports: [53]
  egress:
    - action: Allow
      protocol: UDP
      source:
        ports: [53]
      destination:
        nets: [10.0.0.0/24]
    - action: Allow
      protocol: TCP
      source:
        ports: [53]
      destination:
        nets: [10.0.0.0/24]
```

A diferencia de las políticas normales de endpoints, una falta de coincidencia en la etapa sin seguimiento no provoca una denegación predeterminada al finalizar el nivel; las políticas posteriores con seguimiento aún pueden aplicarse. Esto no constituye un firewall de host con denegación implícita de todo el tráfico.

### PreDNAT

Las políticas previas a DNAT observan la IP y el puerto de destino originales antes de la traducción. Solo se aplican a la entrada y utilizan el seguimiento normal de conexiones para el tráfico de retorno permitido. Este ejemplo protege el NodePort TCP 30080 concreto en la ruta de host seleccionada:

```yaml
apiVersion: projectcalico.org/v3
kind: GlobalNetworkPolicy
metadata:
  name: default.demo-nodeport
spec:
  selector: host-demo == 'true' && !has(projectcalico.org/namespace)
  order: 20
  types: [Ingress]
  preDNAT: true
  applyOnForward: true
  ingress:
    - action: Allow
      protocol: TCP
      source:
        nets: [10.0.0.0/24]
      destination:
        ports: [30080]
    - action: Deny
      protocol: TCP
      destination:
        ports: [30080]
```

La etapa previa a DNAT no tiene una denegación predeterminada. El tráfico sin coincidencia continúa hacia las políticas posteriores de host o de cargas. La segunda regla explícita rechaza el tráfico no confiable hacia este NodePort; los demás puertos quedan fuera del ejemplo. Una ruta que llega directamente a un Pod sin atravesar este NodePort del host no queda cubierta por la regla.

***

## Depuración de políticas

Inspeccione las etiquetas, los namespaces, los endpoints de Service, todos los niveles aplicables y ambas direcciones reales. En el servidor de API estándar de Calico, una lista sin selector de nivel puede limitarse al nivel `default`; `-A` significa todos los namespaces, no necesariamente todos los niveles.

```bash
kubectl get networkpolicies.networking.k8s.io -n calico-demo -o yaml
kubectl get tiers.projectcalico.org -o yaml
for CALICO_TIER in $(kubectl get tiers.projectcalico.org -o jsonpath='{.items[*].metadata.name}'); do
  kubectl get networkpolicies.projectcalico.org -n calico-demo \
    -l "projectcalico.org/tier=$CALICO_TIER" -o yaml
  kubectl get globalnetworkpolicies.projectcalico.org \
    -l "projectcalico.org/tier=$CALICO_TIER" -o yaml
done
calicoctl get workloadendpoint -n calico-demo \
  --selector="app == 'frontend'" -o yaml
```

```bash
CALICO_NAMESPACE=calico-system
CALICO_NODE=demo-worker
CALICO_POD="$(kubectl -n "$CALICO_NAMESPACE" get pods -l k8s-app=calico-node \
  --field-selector "spec.nodeName=$CALICO_NODE" -o jsonpath='{.items[0].metadata.name}')"
test -n "$CALICO_POD"
kubectl -n "$CALICO_NAMESPACE" logs "$CALICO_POD" -c calico-node --tail=200
kubectl -n "$CALICO_NAMESPACE" exec "$CALICO_POD" -c calico-node -- \
  calico-node -felix-ready
```

```bash
# Assumes named, ready test Pods and an nc binary in the client image.
TARGET_POD=backend-test
TARGET_IP="$(kubectl -n calico-demo get pod "$TARGET_POD" -o jsonpath='{.status.podIP}')"
test -n "$TARGET_IP"
kubectl -n calico-demo exec frontend-client -- nc -z -w 3 "$TARGET_IP" 8080
```

El comando `calico-node -felix-ready` comprueba la disponibilidad del componente. No realiza un seguimiento de la evaluación de políticas ni mide el tiempo por paquete. La versión publicada de Open Source de `calicoctl` no ofrece el antiguo comando `policy-trace`. Listar un endpoint o buscar texto en las políticas tampoco calcula la política efectiva completa.

Pruebe un cliente autorizado, uno no confiable, un puerto incorrecto, un cliente de otro namespace y el acceso al resolvedor mediante conexiones **nuevas**. Compruebe el puerto de destino del servidor, no el puerto efímero de origen del cliente. Pruebe por separado las direcciones directas de Pod y las de Service para distinguir los problemas de políticas de los de endpoints, NAT o reenvío; kube-proxy o su sustituto también pueden ser relevantes.

En el plano de datos iptables, inspeccione las cadenas `cali-` reales en el nodo y namespace de red correctos; un hash de ejemplo no es un nombre real de cadena. Las acciones Log de iptables escriben en el registro del kernel del host, mientras que la salida estándar de Felix contiene principalmente diagnósticos de componentes y controladores. Ni la ausencia de un mensaje en esa salida ni un contador a cero demuestran que una política no se utiliza en ninguna ruta. eBPF/nftables necesitan sus propios diagnósticos; `tc filter show` por sí solo no explica la decisión efectiva de una política.

### Preparar políticas antes de aplicarlas

Open Source 3.32 proporciona `StagedNetworkPolicy`, `StagedGlobalNetworkPolicy` y `StagedKubernetesNetworkPolicy`. Estos recursos de preparación no aplican decisiones sobre paquetes. Una vez configurado el flujo de registros de tráfico y Whisker, inspeccione `policies.pending` para anticipar los efectos observados.

```yaml
apiVersion: projectcalico.org/v3
kind: StagedNetworkPolicy
metadata:
  name: default.preview-backend-egress
  namespace: calico-demo
spec:
  tier: default
  order: 100
  selector: app == 'frontend'
  types: [Egress]
  egress:
    - action: Allow
      protocol: TCP
      destination:
        selector: app == 'backend'
        ports: [8080]
```

Esta vista previa contiene deliberadamente solo la conexión con el backend. Compruebe si el DNS necesario u otros flujos quedarían denegados antes de crear una política equivalente que se aplique efectivamente. La ausencia de tráfico observado no demuestra que una dependencia sea innecesaria. `action: Log` por sí sola no constituye un modo universal de auditoría sin aplicación: la evaluación continúa y aún puede terminar en una denegación.

***

## Biblioteca de patrones de políticas habituales

### Frontend → Backend → Base de datos

La demostración presupone cargas listas con las etiquetas y los procesos de escucha indicados. Cada puerto de servidor es un puerto de **destino**; una coincidencia con `source.ports: [8080]` normalmente rechazaría a clientes que utilizan puertos efímeros de origen. Todas las reglas con puertos numéricos especifican TCP. La pasarela de demostración es una aplicación de prueba, no una etiqueta que se presuponga en un controlador Ingress concreto.

```yaml
apiVersion: projectcalico.org/v3
kind: NetworkPolicy
metadata:
  name: default.frontend
  namespace: calico-demo
spec:
  order: 100
  selector: app == 'frontend'
  types: [Ingress, Egress]
  ingress:
    - action: Allow
      protocol: TCP
      source:
        selector: app == 'gateway'
      destination:
        ports: [8080]
  egress:
    - action: Allow
      protocol: TCP
      destination:
        selector: app == 'backend'
        ports: [8080]
---
apiVersion: projectcalico.org/v3
kind: NetworkPolicy
metadata:
  name: default.backend
  namespace: calico-demo
spec:
  order: 100
  selector: app == 'backend'
  types: [Ingress, Egress]
  ingress:
    - action: Allow
      protocol: TCP
      source:
        selector: app == 'frontend'
      destination:
        ports: [8080]
  egress:
    - action: Allow
      protocol: TCP
      destination:
        selector: app == 'database'
        ports: [5432]
---
apiVersion: projectcalico.org/v3
kind: NetworkPolicy
metadata:
  name: default.database
  namespace: calico-demo
spec:
  order: 100
  selector: app == 'database'
  types: [Ingress, Egress]
  ingress:
    - action: Allow
      protocol: TCP
      source:
        selector: app == 'backend'
      destination:
        ports: [5432]
  egress: []
```

Permita DNS por separado para los clientes que lo necesiten, mediante el patrón de salida esencial con ámbito restringido y su etiqueta requerida. La base de datos no inicia conexiones nuevas de salida en este patrón simplificado; las respuestas de conexiones existentes siguen funcionando. Las copias de seguridad, la replicación y las dependencias externas requieren sus propias reglas revisadas.

### Aislamiento entre inquilinos

Calico no interpola `$(namespace.tenant)`, `${namespace.labels.tenant}` ni `${namespace.name}` dentro de los selectores. Genere una política para cada valor explícito de inquilino, o utilice una política con ámbito de namespace para aislar el tráfico dentro de un mismo namespace.

```yaml
apiVersion: projectcalico.org/v3
kind: GlobalNetworkPolicy
metadata:
  name: default.team-a-isolation
spec:
  order: 500
  namespaceSelector: tenant == 'team-a'
  types: [Ingress, Egress]
  ingress:
    - action: Allow
      source:
        namespaceSelector: tenant == 'team-a'
  egress:
    - action: Allow
      destination:
        namespaceSelector: tenant == 'team-a'
    - action: Allow
      protocol: UDP
      destination:
        namespaceSelector: kubernetes.io/metadata.name == 'kube-system'
        selector: k8s-app == 'kube-dns'
        ports: [53]
    - action: Allow
      protocol: TCP
      destination:
        namespaceSelector: kubernetes.io/metadata.name == 'kube-system'
        selector: k8s-app == 'kube-dns'
        ports: [53]
```

Esto permite todo el tráfico interno de team-a, incluso entre namespaces con esa etiqueta. Deben controlarse la administración de etiquetas de namespace y los permisos para editar políticas; las acciones Allow anteriores pueden anular el aislamiento previsto. Pruebe los casos de tráfico entre inquilinos y de namespaces sin etiqueta.

### Mismo namespace y servicios compartidos

En esta política con ámbito de namespace, los selectores de entidades que no incluyen un selector de namespace permanecen dentro de `calico-demo`. Es una alternativa al patrón restrictivo de microservicios, no una política adicional que deba superponerse a él.

```yaml
apiVersion: projectcalico.org/v3
kind: NetworkPolicy
metadata:
  name: default.namespace-and-shared
  namespace: calico-demo
spec:
  order: 200
  selector: all()
  types: [Ingress, Egress]
  ingress:
    - action: Allow
      source:
        selector: all()
  egress:
    - action: Allow
      destination:
        selector: all()
    - action: Allow
      protocol: TCP
      destination:
        namespaceSelector: kubernetes.io/metadata.name == 'logging'
        selector: app == 'log-receiver'
        ports: [24224]
    - action: Allow
      protocol: TCP
      destination:
        namespaceSelector: kubernetes.io/metadata.name == 'auth'
        selector: app == 'identity-provider'
        ports: [8080]
```

Añada por separado la regla del resolvedor necesario y asegúrese de que la política del destino permite al cliente. Un puerto de registros o una etiqueta de proveedor de identidad son supuestos explícitos de la demostración; verifique el protocolo y puerto reales del receptor y la autenticación de la aplicación.

### Control de salida en Open Source

Mantenga las direcciones aprobadas en un NetworkSet cuando el servicio garantice unas direcciones determinadas. La IP del ejemplo está reservada para documentación; no es un endpoint real de API ni una resolución DNS permanente.

```yaml
apiVersion: projectcalico.org/v3
kind: NetworkSet
metadata:
  name: approved-api-ips
  namespace: calico-demo
  labels:
    destination-group: approved-api
spec:
  nets: [203.0.113.10/32]
---
apiVersion: projectcalico.org/v3
kind: NetworkPolicy
metadata:
  name: default.approved-api-egress
  namespace: calico-demo
spec:
  order: 100
  selector: app == 'external-api-client'
  types: [Egress]
  egress:
    - action: Allow
      protocol: TCP
      destination:
        selector: destination-group == 'approved-api'
        ports: [443]
```

Utilice la regla DNS anterior si la aplicación resuelve nombres. Para servicios externos dinámicos, use un proxy con la autorización adecuada o la política comercial de dominios documentada por separado. Permitir todo el espacio RFC1918 no equivale a «solo este clúster» y puede dar acceso a redes privadas ajenas.

### Denegación predeterminada como parte del diseño de seguridad

Combine una configuración básica de denegación predeterminada con ámbito limitado, conexiones necesarias explícitas, control de los responsables de etiquetas y RBAC, y autenticación de la aplicación. Esto ofrece segmentación de red, no una implementación completa de confianza cero o cumplimiento por sí sola. Prepare las políticas y pruebe las rutas que deben denegarse antes de aplicarlas.

***

## Impacto de las políticas en el rendimiento

El número de políticas por sí solo no constituye una prueba de capacidad. El coste depende del número de endpoints, los cambios en selectores, la estructura de las reglas, los flujos activos, la frecuencia de actualización y el plano de datos elegido. La afirmación de que «1.000 políticas son muy lentas» y la hipótesis de un coste lineal carecen de un entorno medido y de resultados originales que las respalden.

Los selectores de igualdad, pertenencia a conjuntos y existencia de etiquetas pueden beneficiarse de las optimizaciones de Calico. Evite fusionar políticas de forma que amplíen el acceso solo para reducir el número de objetos. Reutilice NetworkSet mantenidos, limite el volumen de registros y mida la convergencia ante cambios representativos.

Las comprobaciones de disponibilidad, la búsqueda de «Policy sync» y el recuento de líneas de `iptables -L` no miden la latencia de evaluación de reglas. Habilite el endpoint documentado de Felix y recopile sus métricas, inspeccione TYPE/HELP y las unidades de cada métrica y correlacione las mediciones de programación y actualización con una carga controlada:

```bash
# After enabling the documented Felix metrics endpoint through its config owner:
kubectl -n "$CALICO_NAMESPACE" port-forward "pod/$CALICO_POD" 9091:9091
```

```bash
# In another terminal while the localhost port-forward remains active:
curl --fail --silent --show-error http://127.0.0.1:9091/metrics
```

Las métricas de Felix están deshabilitadas de forma predeterminada; habilite primero `prometheusMetricsEnabled` a través del responsable de la configuración. El endpoint debe ser accesible en el nodo seleccionado. Esto permite descubrir métricas, no presenta un resultado de rendimiento publicado. Pruebe rutas de tráfico permitidas y denegadas mientras cambia las políticas, y conserve las versiones exactas de Calico, Kubernetes y el kernel, el plano de datos, la topología, la carga y las mediciones.

## Principios operativos

1. Comience en un namespace aislado, identifique las conexiones necesarias y prepare y aplique reglas explícitas.
2. Trate las etiquetas, las etiquetas de namespace y el RBAC de edición de políticas como parte del límite de autorización.
3. Revise los efectos de Allow y Pass que finalizan o delegan la evaluación cuando cambien los niveles o su orden.
4. Mantenga los requisitos de administración del host, failsafe, Service y DNS separados de las reglas de aplicaciones.
5. Combine la segmentación de red con la autenticación de cargas y usuarios finales; evite afirmar que una regla IP por sí sola previene todos los casos de SSRF o fallos de cumplimiento.

***

## Referencias

* [API NetworkPolicy de Calico](https://docs.tigera.io/calico/latest/reference/resources/networkpolicy)
* [API GlobalNetworkPolicy](https://docs.tigera.io/calico/latest/reference/resources/globalnetworkpolicy)
* [Evaluación de niveles](https://docs.tigera.io/calico/latest/reference/resources/tier)
* [RBAC de niveles](https://docs.tigera.io/calico/latest/network-policy/policy-tiers/rbac-tiered-policies)
* [NetworkPolicy de Kubernetes](https://kubernetes.io/docs/concepts/services-networking/network-policies/)
* [RBAC de Kubernetes](https://kubernetes.io/docs/reference/access-authn-authz/rbac/)
* [Políticas de aplicación con Istio/Dikastes en Open Source](https://docs.tigera.io/calico/latest/network-policy/istio/app-layer-policy)
* [Políticas de dominios de Enterprise](https://docs.tigera.io/calico-enterprise/latest/network-policy/domain-based-policy)
* [Políticas preparadas](https://docs.tigera.io/calico/latest/network-policy/staged-network-policies)
* [Reglas failsafe de host](https://docs.tigera.io/calico/latest/reference/host-endpoints/failsafe)
* [Pre-DNAT](https://docs.tigera.io/calico/latest/reference/host-endpoints/pre-dnat)
* [Tráfico reenviado por el host](https://docs.tigera.io/calico/latest/reference/host-endpoints/forwarded)
* [KubeControllersConfiguration](https://docs.tigera.io/calico/latest/reference/resources/kubecontrollersconfig)
* [Registros de políticas](https://docs.tigera.io/calico/latest/network-policy/policy-rules/log-rules)
* [Métricas de componentes](https://docs.tigera.io/calico/latest/operations/monitor/monitor-component-metrics)

* [Soporte de protocolos de Calico eBPF](https://docs.tigera.io/calico/latest/operations/ebpf/install)
