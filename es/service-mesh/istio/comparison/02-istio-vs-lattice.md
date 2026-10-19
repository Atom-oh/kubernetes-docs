# Istio frente a VPC Lattice

> **Última actualización**: 11 de septiembre de 2026
> **Línea base de API de Istio**: 1.31.0; la compatibilidad con Kubernetes debe comprobarse por separado

Compare los requisitos de comunicación, identidad, protocolo y operación de la aplicación. Istio y VPC Lattice tienen límites distintos de implementación y seguridad; una tabla de características o una afirmación infundada de «sobrecarga cero» no basta para elegir la arquitectura correcta.

Los ejemplos de configuración presuponen recursos existentes y autorizados, así como endpoints de aplicación reales. Son alternativas para el entorno adecuado, no una única implementación de producción. Los identificadores, roles, namespaces y URL de los proveedores de identidad deben sustituirse de forma deliberada. La revisión validó localmente la sintaxis de las configuraciones y entradas, además de los cálculos, sin implementar recursos de AWS ni del clúster.

## Contenido

1. [Arquitectura y plataformas](#architecture-and-platforms)
2. [Gestión del tráfico](#traffic-management)
3. [Seguridad e identidad](#security-and-identity)
4. [Observabilidad](#observability)
5. [Instalación y operaciones](#installation-and-operations)
6. [Costos y evidencia histórica](#cost-and-historical-evidence)
7. [Diseño híbrido y multicloud](#hybrid-and-multicloud-design)
8. [Criterios de selección](#selection-criteria)

## Arquitectura y plataformas {#architecture-and-platforms}

### Istio

Istio proporciona un plano de control/datos implementable con Kubernetes e integración documentada para VM. El modo sidecar usa un proxy Envoy en los Pods de cargas de trabajo inscritos; ambient usa ztunnel por nodo más waypoints inscritos por separado para el procesamiento L7 compatible. Agregar un sidecar añade un **contenedor**, no otro Pod de aplicación.

![Un esquema de modo sidecar: Istiod configura Envoy, los proxies intercambian tráfico de mesh y los backends de observabilidad configurados recopilan/consultan telemetría.](../../../.gitbook/assets/en-service-mesh-istio-comparison-02-istio-vs-lattice-0.png)

[Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-service-mesh-istio-comparison-02-istio-vs-lattice-0.html)

El diagrama conservado describe el modo sidecar. Sus anotaciones de recursos son estimaciones ilustrativas antiguas, no valores predeterminados medidos ni una recomendación actual de capacidad. Kiali consulta telemetría/backends; no es en sí un recopilador de trazas.

La captura ambient usa el mecanismo documentado de Linux de namespace de red/iptables, no una capa de captura eBPF. La funcionalidad principal de ambient alcanzó la disponibilidad general (GA) en la versión 1.24, mientras que las características individuales y las topologías multicluster tienen estados independientes. Eliminar un sidecar, inscribir una carga de trabajo y exigir el recorrido por un waypoint son operaciones distintas; una etiqueta de namespace por sí sola no migra de forma segura todas las cargas de trabajo ni garantiza ahorros del 97–98%.

### VPC Lattice

VPC Lattice es una red de aplicaciones administrada por AWS para **servicios y recursos**. Su modelo de servicio incluye listeners, reglas y grupos de destino para destinos IP/instancia, Lambda y ALB compatibles; la integración con ECS/EKS administra los destinos aplicables. Las configuraciones de recursos y sus resource gateways ofrecen un modelo distinto para acceder a recursos privados, incluida la conectividad TCP.

Una red de servicios es un límite lógico de asociación/acceso, no un sidecar ni una identidad a nivel de Pod. Un cliente puede usar una asociación de VPC a la red de servicios o un endpoint de VPC de esa red. La conexión a través del endpoint se apoya en PrivateLink; es inexacto describir cada ruta de datos de Lattice o todo el plano de datos simplemente como «AWS PrivateLink».

Las asociaciones de VPC y las asociaciones de endpoints se comportan de forma distinta en cuanto a direccionamiento y conectividad. Los endpoints de red de servicios pueden aceptar tráfico compatible que llegue mediante peering, Transit Gateway, Direct Connect o VPN, incluidos clientes fuera de AWS. El servicio de AWS sigue operándose en AWS; esto no es una implementación de Lattice en otra nube.

| Dimensión | Istio | VPC Lattice |
|---|---|---|
| Plano de datos | Sidecars o componentes ambient, además de las puertas de enlace elegidas | Red de servicios/recursos administrada y destinos/endpoints configurados |
| Identidad | Identidad de mesh de carga de trabajo y políticas de aplicación/JWT configuradas | Autorización de servicio IAM/SigV4 cuando está habilitada; el acceso a recursos tiene controles separados |
| Operaciones | Ciclo de vida de control/proxy, certificados, capacidad, políticas y telemetría | AWS opera el servicio; los usuarios siguen administrando IAM, DNS, asociaciones, destinos, controladores, cuotas y aplicaciones |
| Plataforma | Implementaciones Kubernetes/VM compatibles, requisitos específicos por modo | Tipos de destino AWS compatibles y rutas documentadas de cliente/red |
| Costo | Infraestructura, telemetría, soporte e ingeniería reales | Cargos aplicables de servicio/recurso/tráfico, más infraestructura de aplicación, registros e ingeniería |

«No requerir un sidecar» es una propiedad de implementación; no demuestra que la latencia, el uso de CPU, el trabajo de firma/controlador o el costo total de infraestructura sean cero.

## Gestión del tráfico {#traffic-management}

### Enrutamiento ponderado y condicional

Istio puede hacer coincidir propiedades de solicitudes HTTP y enrutar a subconjuntos etiquetados. El backend Service y las cargas de trabajo v1/v2 coincidentes ya deben existir en `mesh-demo`:

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: backend-canary
  namespace: mesh-demo
spec:
  hosts:
  - backend
  http:
  - match:
    - headers:
        x-release:
          exact: canary
    route:
    - destination:
        host: backend
        port:
          number: 8080
        subset: v2
      weight: 100
    retries:
      attempts: 0
  - route:
    - destination:
        host: backend
        port:
          number: 8080
        subset: v1
      weight: 90
    - destination:
        host: backend
        port:
          number: 8080
        subset: v2
      weight: 10
    retries:
      attempts: 0
---
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: backend
  namespace: mesh-demo
spec:
  host: backend
  trafficPolicy:
    loadBalancer:
      simple: LEAST_REQUEST
    connectionPool:
      tcp:
        maxConnections: 100
      http:
        http1MaxPendingRequests: 50
        http2MaxRequests: 100
        maxRequestsPerConnection: 2
    outlierDetection:
      consecutive5xxErrors: 5
      interval: 30s
      baseEjectionTime: 60s
      maxEjectionPercent: 50
      minHealthPercent: 50
  subsets:
  - name: v1
    labels:
      version: v1
  - name: v2
    labels:
      version: v2
```

Las rutas deshabilitan explícitamente los reintentos de mesh. Los límites de recursos son ilustrativos; `maxRequestsPerConnection: 2` limita intencionadamente la reutilización y no es una recomendación general de rendimiento. Un proxy evalúa la detección de valores atípicos para sus endpoints upstream. `minHealthPercent` es el umbral de pánico/fail-open, no una garantía de que al menos ese porcentaje se mantenga saludable.

Las reglas de listener HTTP/HTTPS de Lattice admiten coincidencias por método, encabezado y ruta. Esta entrada completa de **CreateRule** reemplaza el ejemplo anterior, que carecía de los campos service/name y tenía pathMatch mal formado:

```json
{
  "serviceIdentifier": "svc-0123456789abcdef0",
  "listenerIdentifier": "listener-0123456789abcdef0",
  "name": "api-canary",
  "priority": 10,
  "match": {
    "httpMatch": {
      "method": "GET",
      "pathMatch": {
        "caseSensitive": true,
        "match": {
          "prefix": "/api/v1/"
        }
      }
    }
  },
  "action": {
    "forward": {
      "targetGroups": [
        {
          "targetGroupIdentifier": "tg-0123456789abcdef0",
          "weight": 90
        },
        {
          "targetGroupIdentifier": "tg-0123456789abcdef1",
          "weight": 10
        }
      ]
    }
  }
}
```

Guarde como `rule.json`, sustituya los identificadores por un servicio/listener existente y dos grupos de destino elegibles, y verifique que el nombre y la prioridad de la regla no estén en uso antes de crearla:

```bash
AWS_REGION=us-east-1
aws vpc-lattice create-rule --region "$AWS_REGION" --cli-input-json file://rule.json
```

La prioridad numérica más baja se evalúa primero. Se requiere la forma anidada `pathMatch.match.prefix`. La regla mostrada coincide con GET bajo `/api/v1/`; no es un equivalente completo de cada coincidencia de Istio ni una política de autenticación. Los pesos no implementan ni escalan las versiones. Evite que un controlador de AWS y este ejemplo de CLI compitan por la propiedad de la misma regla y los mismos destinos.

Lattice documenta la selección de destinos round-robin; esto es independiente de los pesos entre grupos de destino. La API no ofrece la opción «least connections» que antes se atribuía a este ejemplo.

### Duplicación y fallos

Para un experimento de duplicación aislado y de solo lectura, use un VirtualService alternativo independiente:

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: backend-mirror
  namespace: mesh-demo
spec:
  hosts:
  - backend
  http:
  - match:
    - method:
        exact: GET
      uri:
        prefix: /api/v1/
    route:
    - destination:
        host: backend
        port:
          number: 8080
        subset: v1
      weight: 100
    mirror:
      host: backend
      port:
        number: 8080
      subset: v2
    mirrorPercentage:
      value: 10
    retries:
      attempts: 0
  - route:
    - destination:
        host: backend
        port:
          number: 8080
        subset: v1
      weight: 100
    retries:
      attempts: 0
```

Solo se duplican las solicitudes GET coincidentes; las demás solicitudes van a v1 sin duplicación. Las respuestas de sombra no son la respuesta que recibe el cliente, y las solicitudes duplicadas aún pueden crear efectos secundarios si un endpoint no es verdaderamente de solo lectura. Las versiones de destino y la capacidad deben existir.

Un experimento de fallos aislado puede usar un marcador de solicitud deliberado:

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: backend-fault-lab
  namespace: mesh-demo
spec:
  hosts:
  - backend
  http:
  - match:
    - method:
        exact: GET
      headers:
        x-fault-lab:
          exact: enabled
    fault:
      delay:
        percentage:
          value: 10
        fixedDelay: 5s
      abort:
        percentage:
          value: 5
        httpStatus: 503
    route:
    - destination:
        host: backend
        port:
          number: 8080
        subset: v1
      weight: 100
  - route:
    - destination:
        host: backend
        port:
          number: 8080
        subset: v1
      weight: 100
    retries:
      attempts: 0
```

El marcador no es un mecanismo de autorización; limite el alcance de la prueba y quién puede invocarla. La inyección de fallos y el comportamiento de reintento/timeout en la misma ruta no son pruebas intercambiables. Observe qué proxy genera el error y mida por separado los resultados sin procesar frente a los reintentados.

La API RuleAction documentada de Lattice ofrece reenvío o una respuesta fija, no una acción equivalente de Istio para duplicar o retrasar/abortar por porcentaje. Una regla de respuesta fija no equivale a la inyección de fallos por porcentaje. Los mecanismos de prueba de aplicación/proxy o las acciones AWS FIS compatibles requieren su propio diseño explícito. «ALB + Lambda@Edge» no es una característica integrada válida de duplicación: Lambda@Edge se ejecuta en eventos de CloudFront.

### Health checks y manejo de fallos

Esta entrada de **CreateTargetGroup** presupone un backend HTTP existente sin mesh y un endpoint `/health` real en la VPC especificada. No es el backend Istio STRICT del ejemplo de seguridad:

```json
{
  "name": "backend-v1",
  "type": "IP",
  "config": {
    "port": 8080,
    "protocol": "HTTP",
    "protocolVersion": "HTTP1",
    "vpcIdentifier": "vpc-0123456789abcdef0",
    "ipAddressType": "IPV4",
    "healthCheck": {
      "enabled": true,
      "protocol": "HTTP",
      "protocolVersion": "HTTP1",
      "port": 8080,
      "path": "/health",
      "healthCheckIntervalSeconds": 30,
      "healthCheckTimeoutSeconds": 5,
      "healthyThresholdCount": 2,
      "unhealthyThresholdCount": 3,
      "matcher": {
        "httpCode": "200"
      }
    }
  }
}
```

```bash
aws vpc-lattice create-target-group --region "$AWS_REGION"   --cli-input-json file://target-group.json
```

La configuración debe contener la entrada completa mostrada y usar valores reales. Incluya las comprobaciones de estado dentro de config, con healthCheckIntervalSeconds y healthCheckTimeoutSeconds; esta operación no tiene una bandera `--health-check` de nivel superior. Después de crear el grupo, registre destinos compatibles reales. En EKS, gestione normalmente el ciclo de vida de las IP de Pods mediante el AWS Gateway API Controller apropiado, en lugar de mantener direcciones de Pod añadidas manualmente de forma permanente.

Lattice usa automáticamente los destinos saludables. Si ningún destino del grupo está saludable, **se activa el modo fail-open** y Lattice sigue enviándoles tráfico; no se limita a esperar que alguien los retire manualmente. Las comprobaciones de estado no reparan la aplicación. El enrutamiento de salud de Lattice es diferente de los controles de grupo de conexiones y valores atípicos por proxy de Istio.

El valor idleTimeoutSeconds del servicio puede configurarse entre 60 y 600 segundos. No controla lo mismo que el timeout de una solicitud por ruta ni que el presupuesto de reintentos. Pruebe los límites de conexión y solicitud y el comportamiento ante fallos de la ruta HTTP, gRPC o TLS elegida, en lugar de declarar una opción genéricamente superior.

## Seguridad e identidad {#security-and-identity}

### Istio: exigir juntas las condiciones previstas

```yaml
apiVersion: security.istio.io/v1
kind: PeerAuthentication
metadata:
  name: backend-strict
  namespace: mesh-demo
spec:
  selector:
    matchLabels:
      app: backend
  mtls:
    mode: STRICT
---
apiVersion: security.istio.io/v1
kind: RequestAuthentication
metadata:
  name: backend-jwt
  namespace: mesh-demo
spec:
  selector:
    matchLabels:
      app: backend
  jwtRules:
  - issuer: https://issuer.example.com
    jwksUri: https://issuer.example.com/.well-known/jwks.json
    audiences:
    - api.example.com
---
apiVersion: security.istio.io/v1
kind: AuthorizationPolicy
metadata:
  name: backend-access
  namespace: mesh-demo
spec:
  selector:
    matchLabels:
      app: backend
  action: ALLOW
  rules:
  - from:
    - source:
        principals:
        - cluster.local/ns/mesh-demo/sa/frontend
        requestPrincipals:
        - https://issuer.example.com/*
    to:
    - operation:
        methods:
        - GET
        - POST
        paths:
        - /api/v1/*
        ports:
        - '8080'
    when:
    - key: request.auth.claims[role]
      values:
      - admin
```

El issuer/JWKS/audience son marcadores de posición explícitos del proveedor de identidad, y quien llama debe usar la identidad real de la ServiceAccount frontend. La **misma regla ALLOW** exige el principal de mesh, el principal JWT de ese issuer, el método/ruta/puerto permitido y la reclamación admin. Las políticas ALLOW separadas se combinan con OR y no exigirían ambas comprobaciones juntas. RequestAuthentication por sí sola no exige un JWT, y un encabezado de rol de usuario sin procesar no es identidad autenticada. Revise otras políticas ALLOW que apunten a la carga de trabajo, porque una concesión coincidente separada aún puede añadir acceso.

La rotación de certificados depende de la vigencia del emisor y de la configuración de proxy/CA; no existe un intervalo universal de renovación de 15 minutos. La integración de CA externa necesita su ruta de issuer realmente compatible. Los ajustes mTLS a nivel de puerto se refieren a puertos de carga de trabajo y difieren según el modo de proxy; etiquetar el puerto principal de aplicación 8080 como una «excepción de métricas» de texto plano puede romper este contrato de seguridad.

### Lattice: límite TLS y autorización de servicio

Esta entrada de **CreateListener** configura la terminación HTTPS para un servicio existente y listo, junto con su grupo de destino:

```json
{
  "serviceIdentifier": "svc-0123456789abcdef0",
  "name": "https-main",
  "protocol": "HTTPS",
  "port": 443,
  "defaultAction": {
    "forward": {
      "targetGroups": [
        {
          "targetGroupIdentifier": "tg-0123456789abcdef0",
          "weight": 100
        }
      ]
    }
  }
}
```

```bash
aws vpc-lattice create-listener --region "$AWS_REGION" --cli-input-json file://listener.json
```

El nombre DNS de servicio generado tiene un certificado administrado por AWS; los dominios personalizados requieren la configuración documentada de certificado/dominio. HTTPS de front-end no implica HTTPS de backend ni mTLS SPIFFE de Istio. El protocolo de grupo de destino es una elección independiente. Cuando Lattice establece HTTPS con los destinos, el comportamiento documentado **no valida los certificados de destino**; no describa esto como autenticación de certificados de pares a nivel de aplicación.

TLS_PASSTHROUGH puede en cambio transportar el propio TLS/mTLS de la aplicación sin terminarlo en Lattice. Requiere la configuración de dominio personalizado/SNI y destino TCP, permite solo la regla de reenvío predeterminada, limita las conexiones a diez minutos y admite solo principales de política de autenticación anónimos. Los destinos Lambda no son compatibles en esa ruta. No permite inspeccionar políticas IAM de HTTP ni encabezados dentro del flujo cifrado.

### Políticas de autenticación IAM correctas

Use `vpc-lattice-svcs:Invoke`, el ARN de servicio más la ruta y un rol seleccionado explícitamente. Un ejemplo de política de autenticación de servicio/red es:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "AWS": "arn:aws:iam::123456789012:role/LatticeClient"
      },
      "Action": "vpc-lattice-svcs:Invoke",
      "Resource": "arn:aws:vpc-lattice:us-east-1:123456789012:service/svc-0123456789abcdef0/api/v1/*",
      "Condition": {
        "StringEquals": {
          "vpc-lattice-svcs:RequestMethod": [
            "GET",
            "POST"
          ]
        }
      }
    }
  ]
}
```

Guarde la política de autenticación como auth-policy.json después de sustituir los ARN de ejemplo. El rol del llamador necesita por separado un permiso basado en identidad correspondiente:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": "vpc-lattice-svcs:Invoke",
      "Resource": "arn:aws:vpc-lattice:us-east-1:123456789012:service/svc-0123456789abcdef0/api/v1/*",
      "Condition": {
        "StringEquals": {
          "vpc-lattice-svcs:RequestMethod": [
            "GET",
            "POST"
          ]
        }
      }
    }
  ]
}
```

Sustituya los ARN de ejemplo y asegúrese de que cada política habilitada de autenticación de red de servicios y servicio permita la solicitud. Una denegación explícita en cualquier lugar prevalece. AWS_IAM activa la evaluación; una política adjunta mientras authType es NONE está inactiva. Un Principal comodín combinado únicamente con SourceVpc puede permitir tráfico anónimo, por lo que no demuestra que haya autenticación IAM.

La operación de API es **PutAuthPolicy**. Para conservar una cadena de política compacta dentro de una entrada CLI completa sin saltos de línea incrustados:

```bash
: "${SERVICE_ID:?Set the actual service ID}"
jq -n --arg resource "$SERVICE_ID" --slurpfile policy auth-policy.json   '{resourceIdentifier:$resource, policy:($policy[0] | tojson)}' > put-auth-policy.json
aws vpc-lattice put-auth-policy --region "$AWS_REGION"   --cli-input-json file://put-auth-policy.json
```

Esto sustituye la sintaxis inexistente create-auth-policy/allowedPrincipals. El rol de administración que aplica la configuración es distinto del rol de carga de trabajo que invoca el servicio. La aplicación o un componente de firma compatible debe firmar la solicitud real mediante la ruta SigV4 documentada y las credenciales de carga de trabajo; los ajustes TLS por sí solos no producen la firma. Los cambios en los componentes reenviados de una solicitud firmada pueden invalidar la firma; consérvelos o firme la solicitud después de aplicar las transformaciones previstas.

La autorización de Lattice no se limita a L4/nombres de servicio. Las condiciones documentadas incluyen método, ruta, encabezados y cadenas de consulta, además del contexto de principal/VPC/servicio. La disponibilidad de estas condiciones depende del protocolo y de si se admite un llamador anónimo. Estas políticas de servicio no cubren configuraciones de recursos en una red de servicios.

La lista actual de recursos admitidos por la API AssociateWebACL de WAF no incluye un servicio ni una red de Lattice. Un componente WAF compatible puede formar parte de una ruta diseñada por separado, pero no se justifica la anterior afirmación del diagrama de «integración directa de Lattice WAF». IAM, WAF, aislamiento de red y autorización de aplicación siguen siendo controles distintos.


## Observabilidad {#observability}

### Métricas y trazas de Istio

Use la familia de métricas, etiquetas y un reporter reales. Para el backend de ejemplo, pueden consultarse por separado el RPS total, la proporción de respuestas 5xx o con estado cero y la latencia p95 en milisegundos:

```promql
sum(rate(istio_requests_total{reporter="source",destination_service_name="backend",destination_service_namespace="mesh-demo"}[5m]))

(sum(rate(istio_requests_total{reporter="source",destination_service_name="backend",destination_service_namespace="mesh-demo",response_code=~"5..|0"}[5m])) or vector(0))
/
sum(rate(istio_requests_total{reporter="source",destination_service_name="backend",destination_service_namespace="mesh-demo"}[5m]))

histogram_quantile(0.95, sum by (le) (rate(istio_request_duration_milliseconds_bucket{reporter="source",destination_service_name="backend",destination_service_namespace="mesh-demo"}[5m])))
```

La expresión alternativa del numerador contempla que falte una serie 5xx cuando existe tráfico real; si falta el denominador, debe seguir ausente, y el tráfico inactivo no demuestra que el servicio esté saludable. Confirme las etiquetas de métricas y el alcance de scraping. Los gauges y contadores de conexión/valores atípicos de proxy son familias Envoy separadas; no invente recuentos fijos de «50 métricas predeterminadas» ni una interpretación universal de caché/reintento.

La configuración actual de Telemetry usa anulaciones de métricas/tagOverrides y un proveedor de trazado declarado:

```yaml
apiVersion: install.istio.io/v1alpha1
kind: IstioOperator
spec:
  meshConfig:
    enableTracing: true
    extensionProviders:
    - name: otel-tracing
      opentelemetry:
        service: otel-collector.observability.svc.cluster.local
        port: 4317
---
apiVersion: telemetry.istio.io/v1
kind: Telemetry
metadata:
  name: backend-observability
  namespace: mesh-demo
spec:
  selector:
    matchLabels:
      app: backend
  metrics:
  - providers:
    - name: prometheus
    overrides:
    - match:
        metric: REQUEST_COUNT
      tagOverrides:
        request_method:
          value: request.method
  tracing:
  - providers:
    - name: otel-tracing
    randomSamplingPercentage: 10
    customTags:
      environment:
        literal:
          value: lab
```

El objeto IstioOperator es **una entrada para istioctl** y debe combinarse con la configuración de instalación existente que ya se revisó. No sobrescriba el ConfigMap de Istio activo ni descarte otros proveedores de extensión. El Service del Collector debe aceptar OTLP gRPC en el puerto 4317 y contar con una canalización funcional de exportación al backend; estos objetos no lo instalan. El nombre de proveedor en Telemetry debe coincidir con MeshConfig.

Añadir una dimensión de métrica no es lo mismo que producir una métrica de negocio arbitraria. Limite la cardinalidad, recopile métricas de aplicación cuando sea necesario y configure compatibilidad con exemplars y trazas. Las trazas de extremo a extremo requieren propagación de contexto de la aplicación, muestreo y entrega de collector/backend; ni «todos los backends» ni la propagación automática de baggage están garantizados al instalar Istio.

### Métricas de VPC Lattice

El namespace documentado de CloudWatch es **AWS/VpcLattice**, con mayúsculas y minúsculas exactas. Las dimensiones de servicio incluyen Service y AvailabilityZone; las dimensiones de grupo de destino incluyen TargetGroup y AvailabilityZone. Compruebe qué combinación de métrica y dimensiones se emite realmente:

```bash
aws cloudwatch list-metrics --region "$AWS_REGION"   --namespace AWS/VpcLattice --metric-name TotalRequestCount
```

| Señal documentada | Interpretación |
|---|---|
| TotalRequestCount | Recuento de solicitudes; Sum es útil |
| RequestTime | Milisegundos; Average o un percentil, con el límite de medición documentado de servicio/grupo de destino |
| HTTPCode_2XX_Count a HTTPCode_5XX_Count | Respuestas HTTP agregadas |
| HTTPCode_VpcLattice_403_Count y otros códigos granulares documentados | Respuestas generadas por Lattice, útiles junto con los motivos registrados en los logs de acceso |
| Métricas de conexión de grupos de destino | Recuentos/errores/bytes de conexión específicos por protocolo; distintos de las métricas de solicitudes de aplicación |

Estas métricas se publican una vez por minuto después de que el recurso recibe tráfico. Un período de consulta de cinco minutos es una elección de agregación. Consulte list-targets y los resultados de las comprobaciones de estado para conocer la salud de los destinos, en lugar de suponer que en este namespace existen métricas de ALB como HealthyTargetCount o TargetResponseTime.

Para una consulta actual de una hora, genere una vez las marcas de tiempo UTC. Este fragmento de Bash/Python no llama a AWS:

```bash
read -r START_TIME END_TIME START_EPOCH END_EPOCH < <(python3 - <<'PYTIME'
from datetime import datetime, timedelta, timezone
end = datetime.now(timezone.utc).replace(microsecond=0)
start = end - timedelta(hours=1)
print(start.strftime('%Y-%m-%dT%H:%M:%SZ'),
      end.strftime('%Y-%m-%dT%H:%M:%SZ'),
      int(start.timestamp()), int(end.timestamp()))
PYTIME
)
```

En list-metrics, elija la métrica que solo tenga la dimensión Service y copie exactamente el valor de esa dimensión. Si selecciona una métrica específica de AZ, incluya su conjunto completo de dimensiones tal como se devuelve en vez de omitir la AZ:

```bash
: "${SERVICE_DIMENSION:?Copy the exact Service dimension value from list-metrics}"
aws cloudwatch get-metric-statistics --region "$AWS_REGION"   --namespace AWS/VpcLattice --metric-name TotalRequestCount   --dimensions "Name=Service,Value=$SERVICE_DIMENSION"   --start-time "$START_TIME" --end-time "$END_TIME"   --period 60 --statistics Sum
```

Las métricas ausentes no equivalen automáticamente a tráfico cero ni a un servicio saludable. El espacio de nombres de AWS para Lattice contiene sus métricas de servicio publicadas; las aplicaciones pueden publicar por separado métricas personalizadas o derivar métricas de logs. Por tanto, «las métricas personalizadas son imposibles» no es una afirmación general útil.

### Logs de acceso y correlación de solicitudes

Lattice puede entregar logs de acceso a CloudWatch Logs, S3 o Data Firehose. Deben configurarse permisos de entrega, políticas de destino, retención y cargos; la entrega se ofrece con carácter de mejor esfuerzo. Esta es una **ilustración** de campos documentados, no un log de producción capturado:

```json
{
  "startTime": "2025-01-15T12:34:56Z",
  "serviceArn": "arn:aws:vpc-lattice:us-east-1:123456789012:service/svc-0123456789abcdef0",
  "requestMethod": "GET",
  "requestPath": "/api/v1/items",
  "protocol": "HTTP/1.1",
  "responseCode": 200,
  "duration": 12,
  "requestId": "example-request-001"
}
```

Los campos documentados adicionales incluyen authDeniedReason, failureReason, callerPrincipal/resolvedUser e información de destino/origen. Use el tipo de log real: los logs de acceso a recursos describen una ruta TCP/recurso diferente. No suponga campos genéricos timestamp/requestProtocol/responseCodeDetails/requestHeaders/traceparent.

El requestId se correlaciona con x-amzn-requestid, que puede proporcionar un cliente; no es identidad autenticada. Un encabezado de trazas W3C propagado por una aplicación es distinto de un campo de log nativo garantizado o una traza distribuida generada automáticamente. La instrumentación de aplicación puede usar backends de trazado adecuados y no está restringida a X-Ray.

Para un grupo de registros ya configurado, indique ambos límites de tiempo e inspeccione el estado y los resultados de la consulta:

```bash
: "${LATTICE_LOG_GROUP:?Set the configured CloudWatch log group}"
QUERY_ID=$(aws logs start-query --region "$AWS_REGION"   --log-group-name "$LATTICE_LOG_GROUP"   --start-time "$START_EPOCH" --end-time "$END_EPOCH"   --query-string 'fields @timestamp, requestId, requestMethod, requestPath, responseCode, authDeniedReason, failureReason | filter responseCode >= 500 | sort @timestamp desc | limit 20'   --query queryId --output text)
aws logs get-query-results --region "$AWS_REGION" --query-id "$QUERY_ID"
```

Una consulta aún puede estar Scheduled o Running; un resultado vacío inmediato no prueba que no se produjeron errores. Limite el acceso y el intervalo de tiempo a la investigación. Los paneles de Kiali/Grafana o CloudWatch requieren sus fuentes de datos reales y una configuración de acceso; el nombre de un panel no demuestra que ofrezca la misma visibilidad.

## Instalación y operaciones {#installation-and-operations}

### Elegir y verificar la plataforma

Istio 1.31 admite Kubernetes 1.32–1.37; use la intersección entre las versiones compatibles de Kubernetes, la plataforma administrada real y el modo de proxy requerido. No existe un perfil de producción integrado, y la etiqueta obsoleta istio.io/injection no habilita la inyección de sidecars. Siga la [guía de instalación](../01-installation.md) para los artefactos actuales, etiquetas de revisión y requisitos previos. Los complementos de demostración no constituyen una pila de monitorización y alta disponibilidad de producción.

Para Lattice, defina el modelo de servicio o recurso, la asociación real del cliente o el endpoint por el que se conectará, el ciclo de vida de los destinos, el protocolo del listener y los límites de autenticación. Un servicio no tiene que ser una función Lambda, y una aplicación EKS con mesh puede llamar a Lambda mediante una integración compatible separada. Lambda no puede alojar un sidecar de Istio; esto es diferente de declarar incompatible con Istio toda arquitectura EKS más Lambda.

Una configuración completa del servicio requiere estos pasos, en el orden que acuerden sus responsables:

1. Conectividad de red, DNS, grupos de seguridad y roles autorizados de administración y cliente ya configurados.
2. La red de servicios y la asociación VPC de cliente prevista o el endpoint de red de servicios.
3. El servicio y la asociación de red/servicio, con el modo de autenticación previsto.
4. Grupo de destino, registro de destino compatible y comportamiento de salud verificado.
5. Listener/reglas y configuración de dominio/certificado.
6. Todas las políticas de autenticación y los permisos de identidad necesarios para quien llama, además de un componente que firme las solicitudes autenticadas.
7. Registros y métricas, pruebas reales de solicitudes y denegaciones, y un plan para el ciclo de vida y la limpieza de los recursos.

Las entradas anteriores cubren solo partes de ese flujo de trabajo: no crean los requisitos previos ni demuestran que el entorno esté listo. Antes de continuar, compruebe el estado de aprovisionamiento de cada recurso y quién lo administra. En Kubernetes, use el controlador apropiado en lugar de mantener registros obsoletos de direcciones IP de Pods. Las actualizaciones de servicios administrados no eliminan la responsabilidad de controladores, SDK, IAM, DNS o compatibilidad de aplicaciones.

### Actualizaciones de Istio e inscripción ambient

Use la ruta de actualización compatible desde la versión instalada y conserve todos los valores de configuración, certificados de confianza y políticas, después de revisarlos. El antiguo diagrama 1.23→1.24 es histórico, no un objetivo actual. La transferencia de revisión no justifica saltar versiones menores arbitrarias.

Haga una copia de seguridad de la configuración autoritativa de instalación/GitOps y los recursos personalizados pertinentes. `kubectl get all` no incluye todos los objetos y no es una copia de seguridad recuperable completa. Inspeccione las sobrescrituras reales de namespace/revisión/Pod, prepare un grupo de cargas de trabajo y compruebe su estado, el tráfico, los certificados y la telemetría. Mantenga capacidad para revertir el cambio hasta que se acepte la transición.

No fuerce el reinicio de todas las cargas de trabajo, vuelva a emitir una CA para cada error de certificado ni elimine manualmente, como parte de una limpieza rutinaria, nombres de webhooks compartidos fijados en el código. Siga el procedimiento de retirada compatible con la versión solo después de confirmar que todos los proxies y gateways dependientes se han migrado. Eliminar un plano de control cambia las opciones de recuperación; no es una prueba universal de que el rollback sea imposible para siempre.

La inscripción ambient puede añadir cargas de trabajo sin sidecar sin reiniciar la aplicación, mientras que eliminar sidecars existentes requiere reemplazar la carga de trabajo. Aún se aplican los requisitos previos de ambient/CNI/ztunnel y los controles de inscripción/seguridad de waypoint. Los recuentos de Pod Ready no son universalmente 2/2, y los sidecars nativos pueden representarse bajo initContainers.

### Diagnosticar el límite real del fallo

| Capa | Comprobaciones relevantes para el diseño seleccionado |
|---|---|
| Aplicación/destino | Protocolo/puerto en escucha, preparación, réplicas/endpoints, dependencias y errores |
| Enrutamiento de mesh o Lattice | Rutas efectivas, subconjuntos/grupos de destino, salud/fail-open, timeouts y estado de recursos |
| Identidad y política | Duración/confianza de certificado, JWT o SigV4, cada política de autenticación aplicable y denegación IAM |
| Red/DNS | Asociación/endpoint correcto, rutas, security groups/NetworkPolicy y ruta de resolvedor real |
| Control/telemetría | Estado de revisión/controlador, propagación de API/configuración, métricas reales y logs entregados |

Para Istio, son útiles los comandos de estado/configuración de proxy y los logs reales de la carga de trabajo. No suponga que la imagen de proxy contiene curl, tcpdump o un shell; use métodos de depuración compatibles con los permisos necesarios. Proteja los archivos de diagnóstico y restaure los ajustes temporales de depuración. Un backend con cero réplicas es una condición del Deployment o de sus endpoints, no un campo Service.spec.replicas.

Para Lattice, estas operaciones de lectura inspeccionan recursos reales:

```bash
: "${SERVICE_NETWORK_ID:?Set the actual service-network ID}"
: "${TG_ID:?Set the actual target-group ID}"
aws vpc-lattice get-service --region "$AWS_REGION" --service-identifier "$SERVICE_ID"
aws vpc-lattice list-service-network-service-associations --region "$AWS_REGION"   --service-network-identifier "$SERVICE_NETWORK_ID"
aws vpc-lattice get-target-group --region "$AWS_REGION" --target-group-identifier "$TG_ID"
aws vpc-lattice list-targets --region "$AWS_REGION" --target-group-identifier "$TG_ID"
```

list-services no acepta un filtro de red de servicios. Las herramientas de análisis de red inspeccionan sus recursos de red compatibles; pasar un ID de servicio Lattice como destino de network-insights de EC2 no es un diagnóstico completo de aplicación/IAM. De estos comandos no se deduce ningún proceso fijo de tres capas, tiempo de reparación de cinco minutos ni garantía de «auto healing» administrado.


## Costos y evidencia histórica {#cost-and-historical-evidence}

### Comparar el mismo límite de costos

Incluya las mismas aplicaciones, requisitos de disponibilidad, tráfico de red, retención de logs/métricas y alcance de ingeniería en ambos lados. Lattice no paga ni elimina el cómputo EC2/EKS/ECS/Lambda de la aplicación. No es válido comparar solo una factura de red administrada con el costo total de una flota de aplicaciones con Istio y su equipo de operación.

El ejemplo anterior contenía varios problemas distintos:

- Modelaba 24.5 vCPU en total: aplicación 10 + sidecars 10 + Istiod 1 + Prometheus 2 + Jaeger 1 + Kiali 0.5. Cinco nodos m5.xlarge de cuatro vCPU proporcionan solo 20 vCPU antes de las reservas. Incluso el límite inferior ideal de CPU es siete nodos, antes de otras restricciones.
- Las partidas en inglés sumaban $850 de cómputo + $15 de almacenamiento = **$865**, mientras que el texto coreano añadió un cargo no respaldado de $10 por «latencia/red» para llegar a $875. La latencia no es en sí una unidad de facturación de AWS.
- La aritmética original de Lattice era $209 ×12 + $300 ×12 + $1,000 = **$7,108**, no $7,608. Su importe de configuración más operaciones era $4,600, no $5,100.
- Usando solo esas suposiciones antiguas, cinco años de infraestructura de $209/mes y operaciones de $300/mes más una configuración única serían **$31,540**, no cinco copias de una cifra anual que contiene la configuración.
- La cifra coreana de Istio a cinco años añadió una contingencia de $50,000 solo en ese lado y contó repetidamente la configuración inicial. Este es un límite de comparación inconsistente, no evidencia de una diferencia intrínseca de precio de producto.

Los antiguos $140/nodo-mes, cantidades de recursos y estimaciones de personal eran entradas hipotéticas sin una cotización fundamentada ni medición de carga de trabajo. También se mezclaron Mi y MB: 100 × 128 Mi son 12,800 Mi = 12.5 Gi, no 12.8 GB decimales. Un sidecar no duplica el recuento de Pods, y el margen de recursos liberado no elimina automáticamente nodos facturados.

### Ejemplo actual de precios de servicio con fecha

Los ejemplos oficiales de precios de servicio de US East (N. Virginia) comprobados el 11 de septiembre de 2026 usan $0.025 por hora de servicio, $0.025 por GB procesado y cargos por solicitudes y conexiones una vez superada la asignación horaria documentada para cada servicio. Las asociaciones de VPC y los endpoints de la red de servicios figuran sin costo adicional. Las configuraciones de recursos/endpoints de recursos tienen un modelo de precios **diferente**; su nivel de $0.01/GB no es la tarifa de procesamiento de datos de servicio. No añada el antiguo cargo separado de hora de red de servicios a este modelo de precios de servicio.

Para una carga de trabajo de servicio HTTP/HTTPS explícitamente hipotética:

| Entrada | Cálculo | Cargo mensual de red |
|---|---|---:|
| Cinco servicios, 730 horas cada uno |5 ×730 ×$0.025|$91.25|
|10,000 GB facturables entre esos servicios, incluidas solicitudes y respuestas |10,000 ×$0.025|$250.00|
| Cada servicio permanece dentro de 300,000 solicitudes en cada hora |Sin solicitudes por encima de la asignación horaria|$0.00|
| Total para estas entradas indicadas |$91.25 +$250.00|**$341.25**|

Una vez superada esa asignación, calcule los cargos por solicitudes para cada servicio y hora con la tarifa publicada de $0.10 por millón; no use un RPS mensual promedio para ocultar los cargos de las horas con picos de tráfico. Las conexiones TLS passthrough se facturan con un contador distinto. Incluya cada salto facturable entre servicios, la región real, la infraestructura de la aplicación, los registros y los demás cargos pertinentes. Estas son entradas ilustrativas con fecha, no una cotización, garantía de precio futuro ni un ahorro afirmado frente a una flota Istio no medida.

Modele la configuración/migración única por separado de las operaciones recurrentes. Los descuentos, compromisos de compra, crecimiento esperado, la incertidumbre y los requisitos equivalentes de alta disponibilidad y soporte importan para una comparación multianual. No se establece ningún ahorro genérico de $42,000/año o $260,000/cinco años mediante la tabla anterior.

### Preservar honestamente las mediciones históricas

La sección anterior sobre rendimiento afirmaba que se había probado con **dos nodos EKS, m5.xlarge y 1,000 RPS** en el contexto de Istio 1.24, pero no proporcionaba el banco de pruebas, las muestras sin procesar, las versiones exactas de EKS, los parches y el proxy, ni una configuración equivalente:

| Resultado original no verificado | Línea base | Total Istio | Total Lattice |
|---|---:|---:|---:|
| p50 |1.0 ms|2.0 ms|1.5 ms|
| p95 |2.5 ms|5.0 ms|3.7 ms|
| p99 |5.0 ms|8.5 ms|7.0 ms|
| RPS máximo |10,000|8,500|9,200|
| Afirmación de CPU |100%|115%|102%|
| Afirmación de memoria |1 GB|1.5 GB|1.05 GB|

Estos valores siguen siendo afirmaciones históricas sin verificar, no mediciones nuevas de Istio 1.31. No demuestran que eliminar un sidecar explique toda la diferencia de latencia y rendimiento. Una prueba significativa iguala el protocolo, la carga útil, TLS y la autorización, la ubicación, la carga, la telemetría y el comportamiento ante fallos; además, distingue los fallos originales de los resultados que los reintentos ocultan.

Las historias originales anónimas de clientes y la presunta encuesta de satisfacción de re:Invent no tenían publicación ni metodología rastreables. Pueden sugerir preguntas sobre migración, personal y propiedad híbrida, pero no tasas de éxito medidas. La encuesta identificada, **CNCF 2024 Annual Survey**, pregunta sobre los desafíos de los contenedores, el uso de proyectos y el uso de service mesh; no respalda la afirmación de que «el 40 % no logra adoptar Istio» ni los porcentajes atribuidos a distintas causas de fallo. Al citar una encuesta, indique la pregunta real, la muestra y qué significa el resultado.

## Diseño híbrido y multicloud {#hybrid-and-multicloud-design}

![Un posible diseño híbrido usa Istio dentro del clúster y una ruta de servicio Lattice configurada por separado fuera de él. Deben definirse quién firma las solicitudes y los requisitos de red, TLS y del gateway de salida opcional.](../../../.gitbook/assets/en-service-mesh-istio-comparison-02-istio-vs-lattice-17.png)

[Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-service-mesh-istio-comparison-02-istio-vs-lattice-17.html)

El diagrama muestra una opción de alto nivel, no una configuración de salida completa. Decida si el tráfico seguirá una ruta directa desde el sidecar o pasará por un gateway de salida configurado explícitamente, y defina cada límite de TLS e identidad. Lattice no establece automáticamente mTLS de Istio con identidad SPIFFE hacia un backend en modo STRICT. Un límite de ingreso definido deliberadamente puede autenticar la ruta externa prevista y usar mTLS en el tramo posterior del mesh; en ese caso, el backend puede ver la identidad del gateway en lugar de la identidad IAM del llamador original.

Para una aplicación que firma e inicia HTTPS, descubra el nombre DNS de servicio Lattice **real** en vez de inventar payment.vpclattice.aws:

```bash
aws vpc-lattice get-service --region "$AWS_REGION"   --service-identifier "$SERVICE_ID" > lattice-service.json
LATTICE_HOST=$(jq -er '.dnsEntry.domainName | select(type == "string" and length > 0)' lattice-service.json) || exit 1
jq -n --arg host "$LATTICE_HOST" '{
  apiVersion:"networking.istio.io/v1",kind:"ServiceEntry",
  metadata:{name:"payment-lattice",namespace:"mesh-demo"},
  spec:{hosts:[$host],location:"MESH_EXTERNAL",resolution:"DNS",
        ports:[{number:443,name:"https",protocol:"HTTPS"}]}
}' > lattice-service-entry.json
```

Esto solo crea una entrada de configuración que el responsable habitual de la configuración de la carga de trabajo debe revisar y aplicar. No aprovisiona Lattice, no obliga al tráfico a pasar por el gateway de salida, no firma solicitudes ni omite IAM. El sidecar no puede inspeccionar el HTTPS de la aplicación; por eso, un VirtualService HTTP no puede examinar la ruta como lo sugería el ejemplo de salida incompleto anterior. No añada otra capa SIMPLE de TLS alrededor de un flujo de aplicación que ya está cifrado.

Los endpoints de la red de servicios pueden ofrecer una ruta de entrada compatible desde redes locales u otras redes conectadas. Esto requiere enrutamiento, DNS, grupos de seguridad y la autorización de servicio correspondiente. Que AWS opere el servicio no significa que sea imposible conectarse desde redes externas a AWS. Tampoco crea una red de servicios global ni replica los datos de la aplicación entre regiones o nubes.

Para una migración, identifique las API, las identidades, la confianza en los certificados, las rutas, la telemetría y quién es responsable de la recuperación. Cambiar una etiqueta de espacio de nombres no completa la transición de IAM de Lattice a la identidad del mesh. Consulte la [guía de VPC Lattice](../../../networking/02-vpc-lattice.md), la [integración de AWS](../04-aws-integration.md) y la [guía multicluster](../advanced/02-multi-cluster.md) para sus contratos específicos.

## Criterios de selección {#selection-criteria}

| Requisito | Evidencia de decisión |
|---|---|
| Mesh de cargas de trabajo Kubernetes/VM | Características sidecar/ambient necesarias, compatibilidad de la plataforma, ciclo de vida de la identidad y capacidad operativa medida |
| Conectividad de servicio/recurso AWS | Tipos de destino/recurso compatibles, ruta real del cliente, modelo de autenticación/TLS y responsabilidades del propietario |
| Comportamiento detallado de tráfico | API exactas de regla/filtro, límites de protocolo, reintentos, salud y comportamiento ante fallos en vez de una puntuación de características |
| Seguridad sólida | Identidad, cifrado de extremo a extremo y autorización de aplicación en cada punto de terminación, incluidos los caminos que eluden los controles |
| Equipo pequeño o entrega rápida | Flujo de trabajo repetible y plan de soporte del equipo real, sin inventar dotación mínima ni umbrales fijos de tiempo de instalación |
| Costo y rendimiento | Facturas de alcance igual, mediciones reproducibles de carga/fallos y suposiciones fechadas explícitamente |
| Híbrido/multicloud | Límites de red e identidad probados, además de procedimientos de recuperación de aplicaciones y datos; no basta con los nombres de los productos |

Evalúe una prueba de concepto limitada con cargas de trabajo reales y conserve la evidencia. Ni «Istio siempre es caro/complejo» ni «Lattice siempre es más barato/seguro» se deduce únicamente de la arquitectura.

## Referencias oficiales

- [Versiones compatibles de Istio](https://istio.io/latest/docs/releases/supported-releases/), [ambient](https://istio.io/latest/docs/ambient/overview/), [seguridad](https://istio.io/latest/docs/concepts/security/) y [API de Telemetry](https://istio.io/latest/docs/reference/config/telemetry/)
- [Componentes y responsabilidades de VPC Lattice](https://docs.aws.amazon.com/vpc-lattice/latest/ug/what-is-vpc-lattice.html) y [asociaciones/endpoints de red](https://docs.aws.amazon.com/vpc-lattice/latest/ug/service-network-associations.html)
- [CreateRule](https://docs.aws.amazon.com/vpc-lattice/latest/APIReference/API_CreateRule.html), [RuleAction](https://docs.aws.amazon.com/vpc-lattice/latest/APIReference/API_RuleAction.html), [CreateListener](https://docs.aws.amazon.com/vpc-lattice/latest/APIReference/API_CreateListener.html) y [CreateTargetGroup](https://docs.aws.amazon.com/vpc-lattice/latest/APIReference/API_CreateTargetGroup.html)
- [Grupos de destino](https://docs.aws.amazon.com/vpc-lattice/latest/ug/target-groups.html) y [health checks](https://docs.aws.amazon.com/vpc-lattice/latest/ug/target-group-health-checks.html)
- [Listeners HTTPS](https://docs.aws.amazon.com/vpc-lattice/latest/ug/https-listeners.html) y [TLS passthrough](https://docs.aws.amazon.com/vpc-lattice/latest/ug/tls-listeners.html)
- [Políticas de autenticación](https://docs.aws.amazon.com/vpc-lattice/latest/ug/auth-policies.html), [PutAuthPolicy](https://docs.aws.amazon.com/vpc-lattice/latest/APIReference/API_PutAuthPolicy.html) y [solicitudes SigV4](https://docs.aws.amazon.com/vpc-lattice/latest/ug/sigv4-authenticated-requests.html)
- [Métricas de Lattice](https://docs.aws.amazon.com/vpc-lattice/latest/ug/monitoring-cloudwatch.html) y [logs de acceso](https://docs.aws.amazon.com/vpc-lattice/latest/ug/monitoring-access-logs.html)
- [Precios de Lattice](https://aws.amazon.com/vpc/lattice/pricing/), [API de asociación de WAF](https://docs.aws.amazon.com/waf/latest/APIReference/API_AssociateWebACL.html) y [Lambda@Edge](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/lambda-at-the-edge.html)
- [Encuesta CNCF 2024](https://www.cncf.io/reports/cncf-annual-survey-2024/) e [informe original](https://www.cncf.io/wp-content/uploads/2025/04/cncf_annual_survey24_031225a.pdf), especialmente las preguntas 22, 32, 47 (páginas 12, 16, 22)
- [Comparación de service mesh](01-service-mesh-comparison.md), [arquitectura de Istio](../03-architecture.md) y [guía ambient](../advanced/01-ambient-mode.md)
