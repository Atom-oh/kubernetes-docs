# VPC Lattice

Amazon VPC Lattice conecta aplicaciones entre VPC y cuentas de AWS. Este capítulo explica el modelo de recursos, una integración con EKS, el enrutamiento, la autorización IAM, la monitorización y la resolución de problemas.

> **Última actualización**: 11 de septiembre de 2026, con AWS Gateway API Controller **v2.1.3** y Gateway API **v1.5.0**. Los ejemplos describen pasos de configuración y validación; no se desplegaron en una cuenta de AWS durante esta revisión.

## Índice

- [Descripción general](#overview)
- [Arquitectura](#architecture)
- [Integración de EKS y VPC Lattice](#eks-and-vpc-lattice-integration)
- [Instalación y configuración](#installation-and-configuration)
- [Gestión de servicios](#service-management)
- [Enrutamiento y gestión del tráfico](#routing-and-traffic-management)
- [Seguridad y autenticación](#security-and-authentication)
- [Monitorización y registros](#monitoring-and-logging)
- [Buenas prácticas](#best-practices)
- [Resolución de problemas](#troubleshooting)
- [Referencias](#references)

## Descripción general {#overview}

### ¿Qué es VPC Lattice?

VPC Lattice proporciona redes de aplicaciones sin exigir un proxy junto a cada aplicación. Una **red de servicios** agrupa servicios y configuraciones de recursos y los conecta con consumidores autorizados. Los servicios proporcionan listeners, reglas de enrutamiento, grupos de destino y nombres DNS de servicio.

El producto actual también conecta **configuraciones de recursos** mediante gateways de recursos, incluidos recursos como bases de datos RDS que usan TCP. Este modelo de acceso difiere de un servicio HTTP respaldado por un grupo de destino; las políticas de autenticación IAM de la red de servicios/servicio no autorizan el tráfico de configuraciones de recursos. Un **endpoint de VPC de red de servicios**, basado en PrivateLink, puede dar acceso a clientes alcanzados mediante peering, Transit Gateway, Direct Connect o VPN. Una asociación directa de VPC por sí sola no extiende el acceso a clientes detrás de un transit gateway o una conexión de peering.

Los usos habituales incluyen API de aplicaciones entre cuentas, comunicación entre EKS y otros servicios de cómputo y acceso compartido a recursos de datos. La asociación, el enrutamiento, los grupos de seguridad, la autenticación y la autorización de la aplicación siguen necesitando configuración.

### Comparación con otros servicios

| Servicio | Responsabilidad principal | Distinción importante |
|---|---|---|
| VPC Lattice | Conectividad privada de aplicaciones y recursos | Enrutamiento de servicios HTTP/HTTPS/gRPC y capacidades separadas de recursos TLS/TCP; no es una entrada de API para Internet |
| API Gateway | Endpoints de API gestionados y gestión de API | Las API REST, HTTP o WebSocket tienen funciones diferentes; GraphQL no es un tipo de API independiente de API Gateway |
| AWS App Mesh | Malla de servicios basada en Envoy | AWS finalizará el soporte el **2026-09-30**; en esta revisión la fecha aún es futura. Planifique una migración en vez de una instalación nueva |
| Transit Gateway | Conectividad de red mediante enrutamiento IP | Conecta redes; no sustituye el enrutamiento HTTP y la autorización por servicio |
| Istio / Linkerd / Cilium | Capacidades de malla implementadas con sus respectivos planos de datos | Las funciones y costes operativos difieren. Los sidecars no son obligatorios en todas las arquitecturas de malla |

VPC Lattice elimina la necesidad de operar su plano de datos gestionado, pero no promete un coste total menor ni funciones de malla idénticas. Compare los cargos por solicitudes/datos/recursos, la operación del controlador, los requisitos de identidad, los reintentos, las funciones de enrutamiento y la observabilidad para la carga real. Consulte la [comparación Istio–Lattice](../service-mesh/istio/comparison/02-istio-vs-lattice.md).

## Arquitectura {#architecture}

### Componentes y flujo de tráfico

| Componente | Responsabilidad |
|---|---|
| Red de servicios | Agrupación lógica y asociaciones; límite opcional de autorización IAM |
| Servicio | Endpoint de aplicación con su propio nombre DNS |
| Listener y reglas | Pertenecen a un **servicio**; seleccionan acciones y grupos de destino |
| Grupo de destino | Destinos registrados de instancia, IP, Lambda o ALB, con comportamiento específico de cada tipo |
| Asociación de VPC | Permite que clientes de una VPC asociada accedan a la red, sujetos a controles de seguridad |
| Endpoint de VPC de red de servicios | Acceso basado en PrivateLink, incluidas rutas de tránsito/locales admitidas |
| Configuración de recurso / gateway de recursos | Modelo independiente de acceso a recursos, incluidos TCP/bases de datos |

![Tres VPC de dos cuentas de AWS se asocian con una red de servicios cuyos servicios usan grupos de destino para cargas EC2, EKS y Lambda.](../.gitbook/assets/en-networking-02-vpc-lattice-1.png)

[Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-networking-02-vpc-lattice-1.html)

La figura muestra asociaciones lógicas, no un único proceso de router. El acceso también depende de la conectividad de red y las políticas aplicables. Una solicitud resuelve el nombre DNS **del servicio**, llega a su listener, supera las comprobaciones de autorización y se enruta a un destino según las reglas. Un grupo de destino describe destinos; no es otro salto de aplicación.

Use `get-service --query dnsEntry` o la anotación de ruta del controlador para descubrir el dominio real. No lo construya a partir del nombre del servicio y el ID de la red de servicios. El nombre asignado contiene identificadores específicos del servicio; recrearlo puede cambiarlo.

### Modelo de seguridad

El acceso de red, la autorización IAM y el cifrado son controles separados. `AWS_IAM` requiere una solicitud firmada admitida y políticas adecuadas. `NONE` desactiva la autenticación IAM en esa capa concreta; no evita la política IAM de otra capa, los grupos de seguridad ni la autorización de la aplicación. HTTPS protege el tráfico del cliente a Lattice. El HTTP del backend sigue en texto plano salvo que se configure explícitamente TLS para el backend.

## Integración de EKS y VPC Lattice {#eks-and-vpc-lattice-integration}

AWS Gateway API Controller reconcilia recursos de Kubernetes con recursos de VPC Lattice:

| Recurso de Kubernetes | Interpretación en Lattice |
|---|---|
| GatewayClass | Selecciona `application-networking.k8s.aws/gateway-api-controller` |
| Gateway | Hace referencia a una red de servicios mediante el **nombre del Gateway**, sin su namespace |
| HTTPRoute / GRPCRoute | Crea un servicio con dominio propio y configuración de listener/enrutamiento |
| Service de backend y sus endpoints | Definen grupos de destino y endpoints de Pods registrados |
| TargetGroupPolicy | Configura el protocolo y las comprobaciones de estado del grupo de destino |
| IAMAuthPolicy | Adjunta una política de autenticación a la red de un Gateway o al servicio de una Route |
| AccessLogPolicy | Configura el destino de registros de acceso de un recurso objetivo |

Dos Gateways con el mismo nombre pueden referirse a la misma red de servicios aunque sus namespaces sean distintos. Un Gateway por sí solo **no** crea la red ni una IP de entrada compartida. La red puede gestionarse externamente, mediante `defaultServiceNetwork` del controlador en casos sencillos o mediante su CRD ServiceNetwork. Elija un propietario por recurso de nube.

Los ejemplos siguientes usan una red y una asociación de VPC gestionadas externamente. Dejan `defaultServiceNetwork` sin establecer y no adjuntan VpcAssociationPolicy a esa asociación. Si adopta el modelo basado en CRD, gestione la red, la asociación de VPC y la autorización como recursos separados; no gestione simultáneamente esos mismos recursos con CloudFormation.

## Instalación y configuración {#installation-and-configuration}

### Requisitos previos

La guía de actualización v2.1 del controlador requiere **Kubernetes 1.31 o posterior** y Gateway API **1.5 o posterior**. Este ejemplo fija la versión con la que se compiló v2.1, **1.5.0**. Este mínimo no es una matriz de soporte de EKS ni demuestra compatibilidad con todas las versiones posteriores de Gateway API. Antes de cambiar los CRD, revise el ciclo de vida de EKS y todos los controladores que los comparten. En particular, un controlador v2.0 puede fallar tras la transición de almacenamiento/API de TLSRoute introducida en Gateway API 1.5.

Use un clúster EKS admitido, un `kubectl` compatible, Helm, AWS CLI v2 y un rol de operador autorizado para configurar los recursos previstos. El backend de ejemplo supone Pods Linux con IP accesibles desde VPC Lattice. Confirme el CNI, la capacidad de subred, la disponibilidad de endpoints, DNS y la configuración de políticas de red.

```bash
export AWS_REGION=us-west-2
export CLUSTER_NAME=my-cluster
export AWS_ACCOUNT_ID="$(aws sts get-caller-identity --query Account --output text)"
export VPC_ID="$(aws eks describe-cluster --name "$CLUSTER_NAME" \
  --query 'cluster.resourcesVpcConfig.vpcId' --output text)"
export NETWORK_NAME=my-network
export ASSOCIATION_SG_ID=sg-0123456789abcdef0
kubectl config current-context
kubectl version
```

Sustituya el ID de grupo de seguridad de ejemplo. El grupo de la asociación de VPC debe permitir **clientes aprobados** por TCP 443. Los grupos de Pods/nodos del backend deben permitir la lista de prefijos gestionada de Lattice aplicable en el puerto real del backend/comprobación de estado, aquí TCP 8080. Inspeccione los grupos de la ENI real del Pod o nodo, sin asumir que todos los nodos usan el grupo del clúster EKS. Permita también que el plano de control EKS alcance el webhook del controlador en su puerto requerido. No abra todos los puertos a todo Internet.

### Configuración de roles IAM

El **rol del controlador** gestiona recursos de nube. El **rol del llamante** firma solicitudes de aplicación y necesita `vpc-lattice-svcs:Invoke`; son roles distintos.

Use EKS Pod Identity en nodos compatibles, o IRSA. El ejemplo IRSA supone que el proveedor IAM OIDC del clúster ya existe y crea una cuenta de servicio dedicada. Para Pod Identity, use el complemento EKS actual y una asociación para ese mismo namespace/cuenta de servicio, con la política de confianza adecuada; no dependa también de una anotación IRSA en el mismo ejemplo.

La política recomendada del controlador incluye permisos amplios `vpc-lattice:*` y de registros/etiquetado. Trátela como punto de partida de upstream, **no como una política de mínimo privilegio**. Revise el alcance de recursos y las funciones habilitadas, conserve las condiciones restringidas del rol vinculado al servicio y guarde la política revisada antes de crearla. Reutilice un ARN de política existente revisada en vez de crear duplicados en ejecuciones posteriores.

```bash
curl --fail --location --output controller-policy-upstream.json \
  https://raw.githubusercontent.com/aws/aws-application-networking-k8s/v2.1.3/files/controller-installation/recommended-inline-policy.json

# Use the policy reviewed for this account and the enabled controller features.
export REVIEWED_POLICY_FILE=controller-policy-reviewed.json
test -s "$REVIEWED_POLICY_FILE"
export CONTROLLER_POLICY_ARN="$(aws iam create-policy \
  --policy-name VPCLatticeControllerPolicy \
  --policy-document "file://$REVIEWED_POLICY_FILE" \
  --query Policy.Arn --output text)"

# Prerequisite: this cluster's IAM OIDC provider already exists.
eksctl create iamserviceaccount \
  --cluster "$CLUSTER_NAME" --region "$AWS_REGION" \
  --namespace aws-application-networking-system \
  --name gateway-api-controller \
  --attach-policy-arn "$CONTROLLER_POLICY_ARN" \
  --approve
```

Una cuenta de servicio existente requiere una migración deliberada de propietario/rol; el ejemplo no la sobrescribe automáticamente.

### Instalar el controlador publicado

```bash
curl --fail --location --output gateway-api-v1.5.0.yaml \
  https://github.com/kubernetes-sigs/gateway-api/releases/download/v1.5.0/standard-install.yaml
# Inspect changes first if any Gateway API controller is already installed.
kubectl apply --server-side -f gateway-api-v1.5.0.yaml

helm pull oci://public.ecr.aws/aws-application-networking-k8s/aws-gateway-controller-chart \
  --version v2.1.3
helm show crds ./aws-gateway-controller-chart-v2.1.3.tgz > lattice-crds.yaml
kubectl apply --server-side -f lattice-crds.yaml

helm install gateway-api-controller ./aws-gateway-controller-chart-v2.1.3.tgz \
  --namespace aws-application-networking-system --create-namespace \
  --set serviceAccount.create=false \
  --set serviceAccount.name=gateway-api-controller \
  --set-string awsRegion="$AWS_REGION" \
  --set-string awsAccountId="$AWS_ACCOUNT_ID" \
  --set-string clusterVpcId="$VPC_ID" \
  --set-string clusterName="$CLUSTER_NAME" \
  --wait --timeout 5m

kubectl -n aws-application-networking-system get pods
kubectl -n aws-application-networking-system logs \
  -l control-plane=gateway-api-controller -c manager --tail=100
```

Para una release Helm existente, use un plan revisado de `helm upgrade` con sus valores guardados. Helm no actualiza automáticamente los CRD de `crds/`; revise sus cambios por separado. No elimine CRD compartidos de Gateway API ni políticas de admisión para que una actualización pase.

Para entrega mediante manifiestos, renderice este **mismo chart** con `helm template --include-crds`, los mismos valores y elección de cuenta de servicio, y revise y aplique el resultado. Así conserva el RBAC publicado, las observaciones de EndpointSlice, los permisos de elección de líder y la configuración de webhook. No use el antiguo Deployment v1.0 escrito a mano. El chart genera certificados del webhook salvo que se proporcionen explícitamente o se gestionen con su opción cert-manager; mantenga coherentes el Secret del webhook y el paquete CA durante las actualizaciones, sin regenerar uno por separado.

### Crear la red de servicios

Elija **CLI o CloudFormation**, no ambos para la misma red. El ejemplo CLI crea una red `AWS_IAM`. Las solicitudes se rechazan hasta instalar y propagar una política Allow aplicable.

Guarde lo siguiente como `api-auth-policy.json`, sustituyendo la cuenta y el rol del llamante. La política de red permite deliberadamente solo el endpoint `/api` y sus subrutas de esta demostración. Una red de producción necesita una política revisada que cubra los servicios y llamantes previstos.

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "AWS": "arn:aws:iam::123456789012:role/MyAppRole"
      },
      "Action": "vpc-lattice-svcs:Invoke",
      "Resource": "*",
      "Condition": {
        "StringLike": {
          "vpc-lattice-svcs:RequestPath": [
            "/api",
            "/api/*"
          ]
        }
      }
    }
  ]
}
```

```bash
aws vpc-lattice create-service-network --name "$NETWORK_NAME" \
  --auth-type AWS_IAM > service-network.json
export SERVICE_NETWORK_ID="$(python3 -c \
  'import json; print(json.load(open("service-network.json"))["id"])')"
export SERVICE_NETWORK_ARN="$(python3 -c \
  'import json; print(json.load(open("service-network.json"))["arn"])')"

aws vpc-lattice create-service-network-vpc-association \
  --service-network-identifier "$SERVICE_NETWORK_ID" \
  --vpc-identifier "$VPC_ID" --security-group-ids "$ASSOCIATION_SG_ID"

# Save the reviewed policy below as api-auth-policy.json, then compact it.
python3 -c 'import json; print(json.dumps(json.load(open("api-auth-policy.json")),separators=(",",":")))' \
  > api-auth-policy.compact.json
aws vpc-lattice put-auth-policy --resource-identifier "$SERVICE_NETWORK_ID" \
  --policy file://api-auth-policy.compact.json
aws vpc-lattice get-service-network --service-network-identifier "$SERVICE_NETWORK_ID"
aws vpc-lattice get-auth-policy --resource-identifier "$SERVICE_NETWORK_ID"
aws vpc-lattice list-service-network-vpc-associations \
  --service-network-identifier "$SERVICE_NETWORK_ID"
```

Antes de exponer una ruta, verifique que la asociación sea `ACTIVE`, la red conserve `authType: AWS_IAM` y `get-auth-policy` devuelva la política prevista. La propagación puede tardar unos minutos.

La plantilla CloudFormation equivalente de **red y asociación** es:

```yaml
AWSTemplateFormatVersion: '2010-09-09'
Description: VPC Lattice service network and client VPC association
Parameters:
  NetworkName:
    Type: String
    Default: my-network
    MinLength: 3
    MaxLength: 63
    AllowedPattern: '^[a-z0-9]+(-[a-z0-9]+)*$'
    Description: Must match the Kubernetes Gateway name
  VpcId:
    Type: AWS::EC2::VPC::Id
    Description: VPC containing the intended clients
  AssociationSecurityGroupIds:
    Type: List<AWS::EC2::SecurityGroup::Id>
    Description: Existing security groups allowing approved clients on listener ports
Resources:
  ServiceNetwork:
    Type: AWS::VpcLattice::ServiceNetwork
    Properties:
      Name: {Ref: NetworkName}
      AuthType: AWS_IAM
  ClientAssociation:
    Type: AWS::VpcLattice::ServiceNetworkVpcAssociation
    Properties:
      ServiceNetworkIdentifier: {Ref: ServiceNetwork}
      VpcIdentifier: {Ref: VpcId}
      SecurityGroupIds: {Ref: AssociationSecurityGroupIds}
Outputs:
  ServiceNetworkArn:
    Description: ARN used for authorization and sharing
    Value: {Fn::GetAtt: [ServiceNetwork, Arn]}
  ServiceNetworkId:
    Description: ID used with VPC Lattice API operations
    Value: {Fn::GetAtt: [ServiceNetwork, Id]}
```

Esta plantilla no adjunta una política de autenticación. Añada ese recurso con el mismo modelo de propiedad o aplique explícitamente la política revisada antes de probar solicitudes. Obtenga el ID/ARN de la red desde las salidas de la pila. Valide la plantilla e inspeccione un conjunto de cambios antes del despliegue; el ejemplo no crea la VPC ni sus grupos de seguridad.

### Gateway y aplicación

Guarde y aplique esto como `gateway.yaml`. El nombre del Gateway debe coincidir con `my-network` creado antes.

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: lattice-demo
---
apiVersion: gateway.networking.k8s.io/v1
kind: GatewayClass
metadata:
  name: amazon-vpc-lattice
spec:
  controllerName: application-networking.k8s.aws/gateway-api-controller
---
apiVersion: gateway.networking.k8s.io/v1
kind: Gateway
metadata:
  name: my-network
  namespace: lattice-demo
spec:
  gatewayClassName: amazon-vpc-lattice
  listeners:
  - name: https
    protocol: HTTPS
    port: 443
    tls:
      mode: Terminate
      certificateRefs:
      - name: unused
```

`certificateRefs: [{name: unused}]` sigue la configuración documentada de este controlador: satisface la configuración TLS de Gateway API, pero el controlador no lee allí un Secret TLS de Kubernetes. Sin hostname personalizado, Lattice proporciona un certificado para su dominio generado. Esto es **específico del controlador**, no una receta portable de gestión de certificados.

Guarde lo siguiente como `stable.yaml`. Configura NGINX para escuchar realmente en 8080 y servir `/health`; declarar solo `containerPort` no haría ninguna de las dos cosas.

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: service-stable
  namespace: lattice-demo
data:
  nginx.conf: |
    worker_processes 1;
    pid /tmp/nginx.pid;
    error_log stderr notice;
    events { worker_connections 1024; }
    http {
        access_log /dev/stdout;
        default_type application/json;
        client_body_temp_path /tmp/client_temp;
        proxy_temp_path /tmp/proxy_temp;
        fastcgi_temp_path /tmp/fastcgi_temp;
        uwsgi_temp_path /tmp/uwsgi_temp;
        scgi_temp_path /tmp/scgi_temp;
        server {
            listen 8080;
            location = /health { return 200 '{"status":"ok"}\n'; }
            location = /api { return 200 '{"version":"stable"}\n'; }
            location /api/ { return 200 '{"version":"stable"}\n'; }
            location / { return 404 '{"error":"not found"}\n'; }
        }
    }
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: service-stable
  namespace: lattice-demo
spec:
  replicas: 2
  selector:
    matchLabels: &id001
      app: lattice-demo
      version: stable
  template:
    metadata:
      labels: *id001
    spec:
      automountServiceAccountToken: false
      securityContext:
        runAsNonRoot: true
        runAsUser: 101
        runAsGroup: 101
        fsGroup: 101
        seccompProfile:
          type: RuntimeDefault
      containers:
      - name: app
        image: nginx:1.30.4-alpine@sha256:dc5069ad14f19660b141b21236140b91656bf89bbc3e2417c70ae650cd66104c
        command:
        - nginx
        args:
        - -c
        - /etc/lattice/nginx.conf
        - -g
        - daemon off;
        ports:
        - name: http
          containerPort: 8080
        readinessProbe:
          httpGet:
            path: /health
            port: http
          periodSeconds: 5
        resources:
          requests:
            cpu: 50m
            memory: 32Mi
          limits:
            cpu: 250m
            memory: 64Mi
        securityContext:
          allowPrivilegeEscalation: false
          readOnlyRootFilesystem: true
          capabilities:
            drop:
            - ALL
        volumeMounts:
        - name: config
          mountPath: /etc/lattice
          readOnly: true
        - name: tmp
          mountPath: /tmp
      volumes:
      - name: config
        configMap:
          name: service-stable
      - name: tmp
        emptyDir: {}
---
apiVersion: v1
kind: Service
metadata:
  name: service-stable
  namespace: lattice-demo
spec:
  selector:
    app: lattice-demo
    version: stable
  ports:
  - name: http
    port: 8080
    targetPort: http
```

Cree `canary.yaml` con los mismos tres objetos, cambiando cada nombre `service-stable` por `service-canary`, ambas etiquetas `version: stable` del selector/plantilla por `version: canary` y el valor de respuesta JSON `"stable"` por `"canary"`. Mantenga `app: lattice-demo`, el puerto y el endpoint de estado. Aplique ambos archivos en `lattice-demo`. La imagen fijada tiene variantes Linux AMD64 y ARM64. Los requests y números de réplicas son ajustes de demostración, no un dimensionamiento de producción medido.

Guarde y aplique la siguiente `TargetGroupPolicy`; cree una política equivalente `canary-health` dirigida a `service-canary`.

```yaml
apiVersion: application-networking.k8s.aws/v1alpha1
kind: TargetGroupPolicy
metadata:
  name: stable-health
  namespace: lattice-demo
spec:
  targetRef:
    group: ''
    kind: Service
    name: service-stable
  protocol: HTTP
  protocolVersion: HTTP1
  healthCheck:
    enabled: true
    protocol: HTTP
    protocolVersion: HTTP1
    port: 8080
    path: /health
    intervalSeconds: 30
    timeoutSeconds: 5
    healthyThresholdCount: 2
    unhealthyThresholdCount: 2
    statusMatch: '200'
```

El CRD usa `intervalSeconds`, `timeoutSeconds` y `statusMatch`. AWS CLI usa otros nombres de campos, mostrados más adelante. Cambiar el protocolo/versión puede sustituir un grupo de destino; eliminar la política revierte sus ajustes, incluido el comportamiento predeterminado HTTP/HTTP1.

## Gestión de servicios {#service-management}

### Crear un servicio mediante HTTPRoute

Guárdelo como `api-route.yaml`. Guarde también la IAMAuthPolicy siguiente como `api-iam.yaml`. Aplique la aplicación y las políticas de estado, después la ruta y la política de autenticación. Mantenga activa la política `AWS_IAM` de la red mientras la reconciliación crea y protege el servicio de la ruta.

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: api
  namespace: lattice-demo
spec:
  parentRefs:
  - name: my-network
    sectionName: https
  rules:
  - matches:
    - path:
        type: PathPrefix
        value: /api
    backendRefs:
    - name: service-stable
      port: 8080
      weight: 90
    - name: service-canary
      port: 8080
      weight: 10
```

```yaml
apiVersion: application-networking.k8s.aws/v1alpha1
kind: IAMAuthPolicy
metadata:
  name: api-caller
  namespace: lattice-demo
spec:
  targetRef:
    group: gateway.networking.k8s.io
    kind: HTTPRoute
    name: api
  policy: '{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"AWS":"arn:aws:iam::123456789012:role/MyAppRole"},"Action":"vpc-lattice-svcs:Invoke","Resource":"*","Condition":{"StringLike":{"vpc-lattice-svcs:RequestPath":["/api","/api/*"]}}}]}'
```

`spec.policy` es una **cadena** JSON. Este CRD habilita `AWS_IAM` en el servicio objetivo; una anotación de tipo de autenticación o un ConfigMap con una política no lo sustituyen. Una política dirigida a `Gateway` gestionaría la política de la red, por lo que no debe competir con la política externa de este ejemplo.

Inspeccione `Accepted` / `ResolvedRefs`, el estado de la política, el estado de los recursos AWS pertinentes y la disponibilidad del backend. Un `kubectl apply` correcto no demuestra que la reconciliación en la nube o la entrega de registros hayan funcionado.

```bash
kubectl -n lattice-demo get gateway my-network -o yaml
kubectl -n lattice-demo get httproute api -o yaml
kubectl -n lattice-demo get iamauthpolicy api-caller -o yaml
kubectl -n lattice-demo get endpointslices \
  -l kubernetes.io/service-name=service-stable
kubectl -n lattice-demo rollout status deployment/service-stable --timeout=120s
kubectl -n lattice-demo rollout status deployment/service-canary --timeout=120s

export SERVICE_DNS="$(kubectl -n lattice-demo get httproute api \
  -o jsonpath='{.metadata.annotations.application-networking\.k8s\.aws/lattice-assigned-domain-name}')"
test -n "$SERVICE_DNS"
# A caller inside the associated VPC, with MyAppRole credentials, runs:
lattice-client/bin/python lattice_get.py --region "$AWS_REGION" "https://${SERVICE_DNS}/api"
```

Configure el cliente firmado de la siguiente sección antes del último comando. Ejecútelo desde una ubicación de red autorizada con credenciales del **rol del llamante**. La estación de trabajo necesita una ruta de red adecuada además de credenciales AWS.

### Cliente HTTPS firmado

Guárdelo como `lattice_get.py`. Usa la cadena predeterminada de proveedores de credenciales AWS, congela las credenciales para cada solicitud, firma para **`vpc-lattice-svcs`** y establece **`UNSIGNED-PAYLOAD`** según exige VPC Lattice. Valida TLS, no sigue redirecciones con una firma obsoleta y no reintenta automáticamente.

```python
import argparse
import ssl
import sys
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, HTTPSHandler, Request, build_opener

from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest
from botocore.exceptions import BotoCoreError
from botocore.session import Session


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def signed_request(url: str, region: str, credentials) -> Request:
    parts = urlsplit(url)
    if (parts.scheme != "https" or not parts.hostname or parts.username
            or parts.password or parts.fragment):
        raise ValueError("Use an HTTPS URL without user info or a fragment")
    request = AWSRequest(method="GET", url=url, headers={
        "x-amz-content-sha256": "UNSIGNED-PAYLOAD",
    })
    request.context["payload_signing_enabled"] = False
    SigV4Auth(credentials, "vpc-lattice-svcs", region).add_auth(request)
    return Request(url, method="GET", headers=dict(request.headers.items()))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--region", required=True)
    parser.add_argument("url")
    args = parser.parse_args()
    try:
        provider = Session().get_credentials()
        if provider is None:
            raise ValueError("No AWS credentials available")
        request = signed_request(args.url, args.region, provider.get_frozen_credentials())
        opener = build_opener(NoRedirect(), HTTPSHandler(context=ssl.create_default_context()))
        with opener.open(request, timeout=10) as response:
            print(response.status)
            print(response.read(1048576).decode("utf-8", errors="replace"))
        return 0
    except HTTPError as exc:
        print(f"HTTP {exc.code}; check the policy and access logs", file=sys.stderr)
    except (URLError, BotoCoreError, ValueError) as exc:
        print(f"Request failed: {type(exc).__name__}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
```

```bash
python3.12 -m venv lattice-client
lattice-client/bin/python -m pip install 'botocore==1.43.93'
lattice-client/bin/python lattice_get.py --region "$AWS_REGION" "https://${SERVICE_DNS}/api"
```

Este ejemplo exclusivo de GET se comprobó con Python 3.12 y botocore 1.43.93. Las cargas deben usar sus credenciales configuradas de Pod Identity o IRSA. No copie credenciales estáticas ni cabeceras firmadas en manifiestos, registros o tickets de soporte. VPC Lattice también admite SigV4A; este ejemplo usa SigV4 regional.

### Gestión directa mediante la API AWS

Lo siguiente es una **alternativa** para recursos gestionados independientemente. Use una IP de backend accesible y estable que sirva HTTP en 8080 y `/health`; una IP temporal de Pod requiere un controlador que siga sus sustituciones. No cambie manualmente un servicio gestionado por HTTPRoute esperando que el controlador conserve el cambio.

```bash
# Separate API-managed example; do not use for controller-managed resources.
export TARGET_IP=10.0.1.25
export TARGET_GROUP_ID="$(aws vpc-lattice create-target-group \
  --name api-manual --type IP \
  --config "{\"port\":8080,\"protocol\":\"HTTP\",\"protocolVersion\":\"HTTP1\",\"vpcIdentifier\":\"${VPC_ID}\"}" \
  --query id --output text)"
aws vpc-lattice register-targets --target-group-identifier "$TARGET_GROUP_ID" \
  --targets "id=$TARGET_IP,port=8080"
export SERVICE_ID="$(aws vpc-lattice create-service \
  --name api-manual --auth-type AWS_IAM --query id --output text)"
aws vpc-lattice put-auth-policy --resource-identifier "$SERVICE_ID" \
  --policy file://api-auth-policy.compact.json
export LISTENER_ID="$(aws vpc-lattice create-listener \
  --service-identifier "$SERVICE_ID" --name https --protocol HTTPS --port 443 \
  --default-action "{\"forward\":{\"targetGroups\":[{\"targetGroupIdentifier\":\"${TARGET_GROUP_ID}\",\"weight\":1}]}}" \
  --query id --output text)"
aws vpc-lattice create-service-network-service-association \
  --service-identifier "$SERVICE_ID" --service-network-identifier "$SERVICE_NETWORK_ID"
aws vpc-lattice list-targets --target-group-identifier "$TARGET_GROUP_ID"
aws vpc-lattice get-service --service-identifier "$SERVICE_ID" --query dnsEntry
```

Espere a tener destinos saludables y asociaciones activas antes de llamar al dominio HTTPS descubierto. El ejemplo usa un certificado gestionado por AWS para el dominio generado, no un dominio personalizado.

### Actualizar y eliminar servicios

Para recursos gestionados por Kubernetes, cambie la Route, la carga backend o el manifiesto de política y verifique la reconciliación. Para recursos gestionados por API, use la API de actualización correspondiente y compruebe su estado resultante. Capture los IDs de las respuestas en vez de seleccionar el primer servicio de la cuenta.

Antes de eliminar, identifique todos los consumidores, asociaciones de red, listeners/reglas, referencias a grupos de destino y propietarios. Elimine las asociaciones específicas de ruta/servicio y los recursos de servicio respetando las dependencias, y después los grupos de destino sin uso. Un Gateway/red compartido puede afectar a otros namespaces o cuentas. Conserve el controlador hasta completar los finalizers y la limpieza en la nube; no use eliminaciones indiscriminadas.

**Eliminar IAMAuthPolicy desactiva la autenticación IAM de su objetivo (`NONE`) antes de separar la política.** No es una forma de denegar acceso ni de revertir la autorización con seguridad. Mantenga una política restrictiva al eliminar un servicio y verifique los controles restantes de red/servicio.

## Enrutamiento y gestión del tráfico {#routing-and-traffic-management}

### Coincidencia de rutas y cabeceras

La ruta anterior coincide con `/api` y su subárbol. Para añadir una regla canary explícita basada en cabeceras, sustituya la **misma** HTTPRoute por:

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: api
  namespace: lattice-demo
spec:
  parentRefs:
  - name: my-network
    sectionName: https
  rules:
  - matches:
    - path:
        type: PathPrefix
        value: /api
      headers:
      - name: x-version
        value: canary
    backendRefs:
    - name: service-canary
      port: 8080
      weight: 1
  - matches:
    - path:
        type: PathPrefix
        value: /api
    backendRefs:
    - name: service-stable
      port: 8080
      weight: 90
    - name: service-canary
      port: 8080
      weight: 10
```

El controlador documenta coincidencia de rutas sin distinguir mayúsculas, una coincidencia de método por regla, hasta cinco cabeceras y ninguna coincidencia de parámetros de consulta. No asuma que implementa todos los filtros o coincidencias de Gateway API. Una HTTPRoute independiente crea otro servicio/dominio Lattice, no añade automáticamente una regla al primero.

### Enrutamiento ponderado

`backendRefs.weight: 90` y `10` son configuración nativa de Gateway API; no se necesita anotación de enrutamiento ponderado. Expresan una distribución relativa, no un resultado exacto para diez solicitudes. Verifique endpoints, estado, errores y latencia de ambas versiones con una muestra adecuada antes de aumentar el peso canary.

Para recursos AWS gestionados independientemente:

```bash
# TG_STABLE and TG_CANARY are existing target groups managed by this API workflow.
aws vpc-lattice create-rule --service-identifier "$SERVICE_ID" \
  --listener-identifier "$LISTENER_ID" --name api-canary --priority 10 \
  --match '{"httpMatch":{"pathMatch":{"match":{"prefix":"/api"},"caseSensitive":false}}}' \
  --action "{\"forward\":{\"targetGroups\":[{\"targetGroupIdentifier\":\"${TG_STABLE}\",\"weight\":90},{\"targetGroupIdentifier\":\"${TG_CANARY}\",\"weight\":10}]}}"
```

La coincidencia de prefijo de la CLI es léxica; revise sus límites por separado de la semántica `PathPrefix` de Kubernetes. Las coincidencias de enrutamiento no son un límite de autorización. No use una prueba de rutas como demostración de que una política IAM cubre todas las variantes normalizadas o codificadas.

### Comprobaciones de estado

El ejemplo Kubernetes usa `TargetGroupPolicy`. La actualización API equivalente es:

```bash
aws vpc-lattice update-target-group --target-group-identifier "$TARGET_GROUP_ID" \
  --health-check '{"enabled":true,"protocol":"HTTP","protocolVersion":"HTTP1","port":8080,"path":"/health","healthCheckIntervalSeconds":30,"healthCheckTimeoutSeconds":5,"healthyThresholdCount":2,"unhealthyThresholdCount":2,"matcher":{"httpCode":"200"}}'
```

Las comprobaciones evalúan disponibilidad según umbrales; no garantizan disponibilidad ni cero interrupciones. Los grupos HTTP1 las habilitan por defecto, mientras HTTP2 requiere consideración explícita. Los destinos gRPC usan comprobaciones HTTP1/HTTP2, y los tipos Lambda/ALB tienen comportamientos diferentes. Consulte la documentación actual del tipo de destino en vez de aplicar el ejemplo de Pods a todos.

## Seguridad y autenticación {#security-and-authentication}

### Políticas de autenticación y permisos del llamante

`put-auth-policy` / `get-auth-policy` gestionan la autorización de invocación. `put-resource-policy` es otra API de gestión/compartición. Use la acción **`vpc-lattice-svcs:Invoke`** para los llamantes.

Cuando red y servicio usan `AWS_IAM`, la política de identidad del llamante y **ambas** políticas de autenticación aplicables deben permitir el acceso. Un Deny explícito prevalece. `NONE` en un recurso no cancela el requisito IAM de otro. El tráfico directo a ClusterIP/IP de Pod evita la autenticación Lattice; proteja esas rutas con controles adecuados de red y aplicación.

`StringEquals` no interpreta `/api/*` como comodín. El ejemplo usa `StringLike` e incluye `/api` y `/api/*`. La coincidencia de condiciones IAM y la normalización de rutas de la aplicación pueden diferir del enrutamiento del controlador. Para funciones administrativas, prefiera un servicio dedicado restringido a roles administrativos y conserve la autorización de aplicación; no añada un Allow general amplio suponiendo que un comodín protege todos los alias.

### Acceso entre cuentas

La compartición RAM permite asociarse con la entidad compartida; no concede por sí misma invocación de aplicación. Las políticas de red/servicio, los permisos del llamante, los grupos de seguridad de asociación y la ruta de red aún deben permitir la solicitud.

```bash
# Owner account: choose a verified account ID or the actual Organizations ARN.
export CONSUMER_ACCOUNT_ID=111122223333
aws ram create-resource-share --name lattice-network-share \
  --resource-arns "$SERVICE_NETWORK_ARN" --principals "$CONSUMER_ACCOUNT_ID"

# Consumer account: inspect invitations only when the sharing mode requires one.
aws ram get-resource-share-invitations
# After verifying the owner, resources, and intended permissions:
aws ram accept-resource-share-invitation \
  --resource-share-invitation-arn "$VERIFIED_INVITATION_ARN"

# Run with consumer credentials and that account's VPC/security group values.
aws vpc-lattice create-service-network-vpc-association \
  --service-network-identifier "$SERVICE_NETWORK_ARN" \
  --vpc-identifier "$CONSUMER_VPC_ID" \
  --security-group-ids "$CONSUMER_ASSOCIATION_SG_ID"
```

Con la compartición de Organizations habilitada, los consumidores de la organización reciben acceso sin invitación. Otros acuerdos admitidos requieren aceptarla. Para compartir con una organización u OU, use su **ARN real de Organizations**, incluido el identificador de la cuenta de administración, en vez de componerlo con el ID de una cuenta miembro.

Los propietarios pueden compartir servicios, redes y configuraciones de recursos, no roles IAM individuales como consumidores RAM. Dejar de compartir impide asociaciones nuevas, pero **no elimina las existentes**. Revíselas explícitamente al revocar acceso.

### TLS y dominios personalizados

El Gateway de ejemplo solo expone HTTPS. Para un hostname personalizado, cree el servicio con ese nombre, obtenga un certificado ACM coincidente y configure DNS hacia el dominio realmente asignado. Solo se admite un dominio personalizado por servicio y no puede cambiarse después de crearlo.

En el controlador, establezca `spec.hostnames` de HTTPRoute y `tls.options["application-networking.k8s.aws/certificate-arn"]` del listener Gateway, o use el descubrimiento ACM documentado. No ponga claves privadas en anotaciones. La automatización ExternalDNS requiere además su controlador, permisos y el CRD DNSEndpoint; establecer un hostname no demuestra que existan registros DNS.

```bash
# For an API-managed service created with the required custom domain name:
aws vpc-lattice update-service --service-identifier "$SERVICE_ID" \
  --certificate-arn "$ACM_CERTIFICATE_ARN"
# Create an HTTPS listener separately if the service does not already have one.
# create-listener uses --protocol HTTPS; there is no --tls mode=STRICT option.
```

HTTPS orientado al cliente y TLS del backend son independientes. Una `TargetGroupPolicy` de backend con `protocol: HTTPS` también necesita un backend que realmente use TLS y una comprobación HTTPS compatible. VPC Lattice **no valida los certificados del backend**; cifra la conexión sin autenticar la identidad de su certificado. Use el modelo separado TLSRoute/TLS passthrough cuando ese sea el diseño previsto y revise sus limitaciones.

## Monitorización y registros {#monitoring-and-logging}

### Métricas, dashboard y alarma de CloudWatch

Las métricas de servicio usan el namespace **`AWS/VpcLattice`**:

| Métrica | Significado / estadística |
|---|---|
| `TotalRequestCount` | Número de solicitudes; `Sum` |
| `HTTPCode_4XX_Count` | Respuestas 4xx; `Sum` |
| `HTTPCode_5XX_Count` | Respuestas 5xx; `Sum` |
| `RequestTime` | Duración de solicitud en **milisegundos**; media o percentil adecuado |

Las métricas de servicio usan la dimensión `Service`, opcionalmente con `AvailabilityZone`; las de grupos de destino usan `TargetGroup`. Un nombre como `ServiceName=my-service` no identifica estas métricas. Descubra los valores/conjunto reales de dimensiones:

```bash
aws cloudwatch list-metrics --namespace AWS/VpcLattice \
  --metric-name HTTPCode_5XX_Count --dimensions Name=Service > metrics.json
python3 - <<'PY'
import json
for metric in json.load(open("metrics.json"))["Metrics"]:
    print(json.dumps(metric["Dimensions"]))
PY
```

Tras generar métricas con tráfico, seleccione el array de dimensiones **de todo el servicio** previsto y guárdelo como `service-dimensions.json`. No seleccione arbitrariamente el primer resultado ni mezcle una métrica zonal con un agregado. Verifique el identificador frente al servicio observado. Construya `dashboard.json` con:

```python
import json
import os

dimensions = json.load(open("service-dimensions.json"))
if {d["Name"] for d in dimensions} != {"Service"}:
    raise ValueError("Select the service-wide metric, without AvailabilityZone")
pairs = [item for d in dimensions for item in (d["Name"], d["Value"])]
dashboard = {"widgets": [{
    "type": "metric", "width": 12, "height": 6,
    "properties": {
        "title": "VPC Lattice requests and errors",
        "region": os.environ["AWS_REGION"], "period": 60, "stat": "Sum",
        "metrics": [["AWS/VpcLattice", name, *pairs] for name in
                    ("TotalRequestCount", "HTTPCode_4XX_Count", "HTTPCode_5XX_Count")],
    },
}]}
with open("dashboard.json", "w") as output:
    json.dump(dashboard, output)
```

```bash
aws cloudwatch put-dashboard --dashboard-name VPCLattice \
  --dashboard-body file://dashboard.json
aws cloudwatch put-metric-alarm --alarm-name LatticeApi5xx \
  --namespace AWS/VpcLattice --metric-name HTTPCode_5XX_Count \
  --dimensions file://service-dimensions.json \
  --statistic Sum --period 60 --evaluation-periods 3 --datapoints-to-alarm 2 \
  --threshold 5 --comparison-operator GreaterThanThreshold \
  --treat-missing-data missing
```

La alarma significa **más de cinco respuestas 5xx por minuto en dos de tres períodos**, no una tasa de error del 5%. Configure por separado acciones revisadas si necesita notificaciones. La elección para datos ausentes es explícita: las métricas se publican después de empezar el tráfico y NoData no debe tratarse silenciosamente como prueba de salud. Los ajustes son ejemplos, no SLO específicos de la carga.

### Registros de acceso

Para CloudWatch Logs, use un destino existente o cree un grupo dedicado con política de retención:

```bash
export LOG_GROUP=/aws/vendedlogs/vpc-lattice/api
aws logs create-log-group --log-group-name "$LOG_GROUP"
aws logs put-retention-policy --log-group-name "$LOG_GROUP" --retention-in-days 30
export LOG_DESTINATION_ARN="arn:aws:logs:${AWS_REGION}:${AWS_ACCOUNT_ID}:log-group:${LOG_GROUP}:*"

# API-managed service only; for an HTTPRoute use AccessLogPolicy below instead.
aws vpc-lattice create-access-log-subscription \
  --resource-identifier "$SERVICE_ID" --destination-arn "$LOG_DESTINATION_ARN"
```

El principal que realiza la configuración también necesita los permisos documentados de entrega. AWS puede crear/actualizar la política del recurso de registros si ese principal tiene los permisos necesarios; en caso contrario, prepárela previamente. Verifique los permisos de `delivery.logs.amazonaws.com` y las condiciones de cuenta/ARN de origen.

Para la ruta gestionada por Kubernetes, use esto **en lugar de** una suscripción creada por CLI que compita con ella:

```yaml
apiVersion: application-networking.k8s.aws/v1alpha1
kind: AccessLogPolicy
metadata:
  name: api-logs
  namespace: lattice-demo
spec:
  targetRef:
    group: gateway.networking.k8s.io
    kind: HTTPRoute
    name: api
  destinationArn: arn:aws:logs:us-west-2:123456789012:log-group:/aws/vendedlogs/vpc-lattice/api:*
```

Sustituya el ARN y confirme el estado de la política y los eventos realmente entregados. Una política puede dirigirse a un Gateway para registros de red o a una Route para registros del servicio. Cada objetivo puede tener un destino de cada tipo admitido.

Para S3, use un bucket de destino revisado con Block Public Access, cifrado, reglas de retención/ciclo de vida y permisos de entrega adecuados:

```bash
# Existing reviewed destination bucket; no policy is overwritten by this snippet.
aws vpc-lattice create-access-log-subscription \
  --resource-identifier "$SERVICE_ID" --destination-arn "$LOG_BUCKET_ARN"
```

La entrega a S3 exige los permisos documentados `s3:GetBucketAcl` y `s3:PutObject` para `delivery.logs.amazonaws.com`, el prefijo de entrega y las condiciones `aws:SourceAccount` y `aws:SourceArn`. Las políticas existentes deben combinarse, no sobrescribirse. SSE-KMS requiere una clave gestionada por el cliente compatible y su política de entrega. `--destination-name` no es un parámetro de suscripción de registros de acceso.

### Análisis de registros y trazas

Los registros de acceso de servicios HTTP contienen campos como `sourceIpPort`, `requestMethod`, `requestPath`, `responseCode`, `durationMS`, `callerPrincipal` y `authDeniedReason`. Los registros de recursos/TCP tienen otro esquema.

```bash
END_TIME="$(python3 -c 'import time; print(int(time.time()))')"
START_TIME="$((END_TIME - 3600))"
QUERY_ID="$(aws logs start-query --log-group-name "$LOG_GROUP" \
  --start-time "$START_TIME" --end-time "$END_TIME" \
  --query-string 'fields @timestamp, sourceIpPort, requestMethod, requestPath, responseCode, durationMS, callerPrincipal, authDeniedReason | filter responseCode >= 400 | sort @timestamp desc | limit 100' \
  --query queryId --output text)"
aws logs get-query-results --query-id "$QUERY_ID"
# Repeat get-query-results until Complete; Failed/Cancelled/Timeout are errors.
```

VPC Lattice no tiene una opción `update-service --tracing-config` ni una anotación del controlador que instrumente automáticamente aplicaciones para X-Ray. Instrumente con OpenTelemetry/ADOT o el SDK de trazas adecuado, propague contexto y configure exportación/muestreo. Correlacione trazas con registros e IDs de solicitud; un ID suministrado por el cliente no es una identidad autenticada.

## Buenas prácticas {#best-practices}

- **Diseño y propiedad:** Use nombres claros de red/servicio y límites de entorno. Considere Gateways homónimos entre namespaces, consumidores compartidos, cuotas y el propietario de cada política y asociación.
- **Despliegue:** Mantenga seleccionables de forma independiente los backends estable y canary. Compruebe endpoints, estado y autorización antes de cambiar pesos. Registre criterios de reversión y conserve la última configuración conocida.
- **Rendimiento:** Use tiempos de espera acotados y reutilización adecuada de conexiones. Haga que los endpoints de estado sean ligeros y útiles. Use caché o lotes solo donde lo permita la semántica de la aplicación. Los servicios privados Lattice no se convierten en orígenes CDN por habilitar caché.
- **Seguridad:** Separe roles de gestión y de llamada; mantenga las credenciales fuera de manifiestos. Pruebe roles permitidos y rechazados, rutas raíz y subrutas, acceso directo al backend y TLS. No elimine un CRD de política IAM para denegar tráfico.
- **Observabilidad:** Monitorice por separado solicitudes, errores/tasa, latencia, estado de destinos y telemetría ausente. Conserve registros durante el período requerido e instrumente trazas explícitamente.
- **Coste:** Revise los cargos regionales actuales de servicio/recurso, solicitudes, procesamiento de datos, endpoints y registros del modelo elegido. Use etiquetas, elimine solo recursos confirmados sin uso y dimensione el autoscaling del backend separadamente del plano de datos gestionado de Lattice.

## Resolución de problemas {#troubleshooting}

Use identificadores de anotaciones/estado del controlador y del inventario AWS. No asuma que `$SERVICE_ID` del ejemplo API directo sea el servicio de la ruta Kubernetes.

```bash
aws vpc-lattice list-service-network-vpc-associations \
  --service-network-identifier "$SERVICE_NETWORK_ID"
aws vpc-lattice list-service-network-service-associations \
  --service-network-identifier "$SERVICE_NETWORK_ID"
aws vpc-lattice get-service --service-identifier "$SERVICE_ID"
aws vpc-lattice get-auth-policy --resource-identifier "$SERVICE_NETWORK_ID"
aws vpc-lattice get-auth-policy --resource-identifier "$SERVICE_ID"
aws vpc-lattice list-listeners --service-identifier "$SERVICE_ID"
aws vpc-lattice list-rules --service-identifier "$SERVICE_ID" \
  --listener-identifier "$LISTENER_ID"
aws vpc-lattice get-target-group --target-group-identifier "$TARGET_GROUP_ID"
aws vpc-lattice list-targets --target-group-identifier "$TARGET_GROUP_ID"
```

| Síntoma | Comprobación |
|---|---|
| Fallo DNS/conectividad | DNS realmente asignado, asociación VPC o ruta de endpoint del cliente, estado de asociación, grupos de seguridad, NACL y accesibilidad de Pods |
| 403/fallo de autenticación | Rol del llamante, caducidad de credenciales y región/servicio de firma, `UNSIGNED-PAYLOAD`, ambas capas, propagación y campos del motivo de rechazo |
| Ruta o versión incorrecta | Condiciones Route, prioridad/coincidencias de listener/regla, miembros del grupo de destino, pesos y dominios distintos de Route |
| Destinos no saludables | Puerto real, `/health`, HTTP frente a HTTPS, readiness, grupos de seguridad, tipo de destino y umbrales |
| Sin registros/métricas | Permisos y estado de entrega, dimensiones correctas, tráfico inicial, retención y estado de consulta |
| Fallo de reconciliación | Registros de `manager`, rol IAM, EndpointSlices, compatibilidad de CRD, estado de webhook y elección de líder |

Use un intervalo de métricas acotado sin depender de `date -d`, exclusivo de GNU:

```bash
export METRIC_END="$(python3 -c 'from datetime import datetime,timezone; print(datetime.now(timezone.utc).isoformat())')"
export METRIC_START="$(python3 -c 'from datetime import datetime,timedelta,timezone; print((datetime.now(timezone.utc)-timedelta(hours=1)).isoformat())')"
aws cloudwatch get-metric-statistics --namespace AWS/VpcLattice \
  --metric-name HTTPCode_5XX_Count --dimensions file://service-dimensions.json \
  --start-time "$METRIC_START" --end-time "$METRIC_END" \
  --period 60 --statistics Sum
```

Para un incidente de servicio AWS, consulte AWS Health y los eventos de cuenta pertinentes. El acceso API específico de la cuenta y las operaciones de soporte dependen del plan y los endpoints aplicables. Un caso debe incluir IDs revisados, intervalo temporal, síntomas y registros con datos sensibles ocultados. Seleccione las opciones actuales de servicio/categoría/gravedad de la cuenta; no pegue un comando de creación de casos con `urgent` fijado.

## Referencias {#references}

- [Descripción general de VPC Lattice](https://docs.aws.amazon.com/vpc-lattice/latest/ug/what-is-vpc-lattice.html)
- [Asociaciones de redes de servicios](https://docs.aws.amazon.com/vpc-lattice/latest/ug/service-network-associations.html)
- [Instalación del controlador v2.1.3](https://github.com/aws/aws-application-networking-k8s/blob/v2.1.3/docs/guides/deploy.md)
- [Requisitos de actualización del controlador v2.1](https://github.com/aws/aws-application-networking-k8s/blob/v2.1.3/docs/guides/upgrading-v2-0-x-to-v2-1-y.md)
- [Referencia API del controlador](https://github.com/aws/aws-application-networking-k8s/tree/v2.1.3/docs/api-types)
- [HTTPS y TLS de backend del controlador](https://github.com/aws/aws-application-networking-k8s/blob/v2.1.3/docs/guides/https.md)
- [Políticas de autenticación de VPC Lattice](https://docs.aws.amazon.com/vpc-lattice/latest/ug/auth-policies.html)
- [Firma de solicitudes](https://docs.aws.amazon.com/vpc-lattice/latest/ug/sigv4-authenticated-requests.html)
- [Compartición de entidades](https://docs.aws.amazon.com/vpc-lattice/latest/ug/sharing.html)
- [Métricas de CloudWatch](https://docs.aws.amazon.com/vpc-lattice/latest/ug/monitoring-cloudwatch.html)
- [Registros de acceso](https://docs.aws.amazon.com/vpc-lattice/latest/ug/monitoring-access-logs.html)
- [Permisos de entrega de CloudWatch Logs](https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/AWS-logs-infrastructure-CWL.html)
- [Permisos de entrega de S3](https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/AWS-logs-infrastructure-S3.html)

## Cuestionario

Compruebe sus conocimientos con el [cuestionario de VPC Lattice](../quizzes/networking/02-vpc-lattice-quiz.md).
