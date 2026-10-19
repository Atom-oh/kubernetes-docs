# VPC Lattice

Amazon VPC Lattice conecta aplicaciones entre VPC y cuentas de AWS. Este capítulo explica el modelo de recursos, una integración con EKS, el enrutamiento, la autorización de IAM, la supervisión y la resolución de problemas.

> **Última actualización**: 11 de septiembre de 2026, con AWS Gateway API Controller **v2.1.3** y Gateway API **v1.5.0**. Los ejemplos describen pasos de configuración y validación; no se han implementado en una cuenta de AWS como parte de esta revisión.

## Tabla de contenido

- [Descripción general](#overview)
- [Arquitectura](#architecture)
- [Integración de EKS y VPC Lattice](#eks-and-vpc-lattice-integration)
- [Instalación y configuración](#installation-and-configuration)
- [Administración de servicios](#service-management)
- [Enrutamiento y administración del tráfico](#routing-and-traffic-management)
- [Seguridad y autenticación](#security-and-authentication)
- [Supervisión y registro](#monitoring-and-logging)
- [Prácticas recomendadas](#best-practices)
- [Resolución de problemas](#troubleshooting)
- [Referencias](#references)

## Descripción general

### ¿Qué es VPC Lattice?

VPC Lattice proporciona redes de aplicaciones sin que sea necesario colocar un proxy junto a cada aplicación. Una **red de servicios** agrupa servicios y configuraciones de recursos, y los conecta con consumidores autorizados. Los servicios proporcionan listeners, reglas de enrutamiento, grupos de destino y nombres DNS de servicio.

El producto actual también conecta **configuraciones de recursos** mediante puertas de enlace de recursos, incluidos recursos como bases de datos RDS que usan TCP. Este modelo de acceso a recursos es distinto de un servicio HTTP respaldado por un grupo de destino; las políticas de autenticación de IAM de la red de servicios/servicio no autorizan el tráfico de configuraciones de recursos. Un **endpoint de VPC de la red de servicios**, basado en PrivateLink, puede proporcionar acceso desde clientes a los que se llega a través de peering, Transit Gateway, Direct Connect o VPN. Una asociación directa de VPC, por sí sola, no extiende el acceso a clientes detrás de una puerta de enlace de tránsito o una conexión de peering.

Entre los usos habituales se incluyen las API de aplicaciones entre cuentas, la comunicación entre EKS y otros servicios de cómputo, y el acceso compartido a recursos de datos. La asociación, el enrutamiento, los grupos de seguridad, la autenticación y la autorización de aplicaciones siguen requiriendo configuración.

### Comparación con otros servicios

| Servicio | Responsabilidad principal | Diferencia importante |
|---|---|---|
| VPC Lattice | Conectividad privada de aplicaciones y recursos | Enrutamiento de servicios HTTP/HTTPS/gRPC y capacidades independientes de recursos TLS/TCP; no es una puerta de entrada de API a Internet |
| API Gateway | Endpoints de API administrados y administración de API | Las API REST, HTTP o WebSocket tienen distintas funciones; GraphQL no es un tipo de API independiente de API Gateway |
| AWS App Mesh | Malla de servicios basada en Envoy | El soporte de AWS finalizó el **2026-09-30**; la consola y los recursos ya no están accesibles. Migra las implementaciones existentes; no lo uses para instalaciones nuevas |
| Transit Gateway | Conectividad de red mediante enrutamiento IP | Conecta redes; no reemplaza el enrutamiento HTTP ni la autorización por servicio |
| Istio / Linkerd / Cilium | Capacidades de malla implementadas con sus respectivos planos de datos | Las funciones y los costos operativos varían. Los sidecars no son obligatorios en todas las arquitecturas de malla |

VPC Lattice elimina la necesidad de operar su plano de datos administrado, pero no garantiza un menor costo total ni una funcionalidad de malla idéntica. Compara los cargos por solicitudes/datos/recursos, las operaciones del controlador, los requisitos de identidad, los reintentos, las funciones de enrutamiento y la observabilidad para la carga de trabajo real. Consulta la [comparación entre Istio y Lattice](../service-mesh/istio/comparison/02-istio-vs-lattice.md).

## Arquitectura

### Componentes y flujo del tráfico

| Componente | Responsabilidad |
|---|---|
| Red de servicios | Agrupación lógica y asociaciones; límite opcional de autorización de IAM |
| Servicio | Endpoint de aplicación con su propio nombre DNS |
| Listener y reglas | Pertenecen a un **servicio**; seleccionan acciones y grupos de destino |
| Grupo de destino | Destinos registrados de tipo instancia, IP, Lambda o ALB, con comportamiento específico según el tipo de destino |
| Asociación de VPC | Permite que los clientes de una VPC asociada accedan a la red, sujeto a los controles de seguridad |
| Endpoint de VPC de la red de servicios | Acceso basado en PrivateLink, incluidas las rutas de tránsito o locales compatibles |
| Configuración de recursos / puerta de enlace de recursos | Modelo independiente de acceso a recursos, incluidos recursos TCP/bases de datos |

![Tres VPC de dos cuentas de AWS se asocian a una red de servicios, cuyos servicios usan grupos de destino para cargas de trabajo de EC2, EKS y Lambda.](../.gitbook/assets/en-networking-02-vpc-lattice-1.png)

[Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-networking-02-vpc-lattice-1.html)

La figura muestra asociaciones lógicas, no un único proceso de enrutador. El acceso también depende de la conectividad de red y de las políticas aplicables. Una solicitud resuelve el nombre DNS del **servicio**, llega a su listener, supera las comprobaciones de autorización aplicables y se enruta a un destino según las reglas del listener. Un grupo de destino describe destinos; no es otro salto de aplicación.

Usa `get-service --query dnsEntry` o la anotación de ruta del controlador para descubrir el dominio real. No lo construyas a partir del nombre del servicio y del ID de la red de servicios. El nombre asignado contiene identificadores específicos del servicio; si se vuelve a crear un servicio, su nombre puede cambiar.

### Modelo de seguridad

El acceso a la red, la autorización de IAM y el cifrado son controles independientes. `AWS_IAM` requiere una solicitud firmada compatible y las políticas correspondientes. `NONE` desactiva la autenticación de IAM en esa capa en particular; no omite las políticas de IAM de otras capas, los grupos de seguridad ni la autorización de la aplicación. HTTPS protege el tráfico entre el cliente y Lattice. El HTTP del backend permanece sin cifrar, salvo que se configure explícitamente TLS en el backend.

## Integración de EKS y VPC Lattice

AWS Gateway API Controller reconcilia los recursos de Kubernetes con los recursos de VPC Lattice:

| Recurso de Kubernetes | Interpretación en Lattice |
|---|---|
| GatewayClass | Selecciona `application-networking.k8s.aws/gateway-api-controller` |
| Gateway | Hace referencia a una red de servicios por el **nombre del Gateway**, sin su espacio de nombres |
| HTTPRoute / GRPCRoute | Crea un servicio con su propio dominio y configuración de listener/enrutamiento |
| Service de backend y sus endpoints | Definen grupos de destino y endpoints de Pod registrados |
| TargetGroupPolicy | Configura el protocolo y las comprobaciones de estado del grupo de destino |
| IAMAuthPolicy | Asocia una política de autenticación a la red de un Gateway o al servicio de una Route |
| AccessLogPolicy | Configura el destino del registro de acceso de un recurso de destino |

Dos Gateways con el mismo nombre pueden hacer referencia a la misma red de servicios, aunque sus espacios de nombres de Kubernetes sean distintos. Un Gateway por sí solo **no** crea la red ni una IP de entrada compartida. La red puede administrarse externamente, con la opción `defaultServiceNetwork` del controlador para casos sencillos, o con el CRD ServiceNetwork del controlador. Elige un único responsable para cada recurso de la nube.

Los ejemplos siguientes usan una red y una asociación de VPC administradas externamente. Dejan `defaultServiceNetwork` sin configurar y no asocian una VpcAssociationPolicy a esa asociación. Si adoptas el modelo basado en CRD, administra la red, la asociación de VPC y la autorización como recursos independientes; no administres también los mismos recursos con CloudFormation.

## Instalación y configuración

### Requisitos previos

La guía de actualización a v2.1 del controlador requiere **Kubernetes 1.31 o posterior** y Gateway API **1.5 o posterior**. Este ejemplo fija la versión con la que se creó v2.1: **1.5.0**. Este mínimo no es una matriz de compatibilidad de EKS ni una prueba de compatibilidad con todas las versiones posteriores de Gateway API. Comprueba el ciclo de vida de las versiones de EKS y todos los controladores que comparten los CRD de Gateway API antes de cambiarlos. En particular, un controlador v2.0 puede fallar tras la transición de almacenamiento/API de TLSRoute introducida con Gateway API 1.5.

Usa un clúster de EKS compatible, versiones coincidentes de `kubectl`, Helm y AWS CLI v2, y un rol de operador con permisos para configurar los recursos previstos. El backend de ejemplo presupone Pods Linux con IP a las que VPC Lattice pueda acceder. Confirma la configuración de CNI del clúster, la capacidad de las subredes, la disponibilidad de los endpoints, DNS y las políticas de red.

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

Sustituye el ID del grupo de seguridad de ejemplo. El grupo de seguridad de la asociación de VPC debe permitir el acceso de **clientes aprobados** por TCP 443. Los grupos de seguridad de los Pods/nodos del backend deben permitir la lista de prefijos administrada de Lattice aplicable en el puerto real del backend/de comprobación de estado, que aquí es TCP 8080. Inspecciona los grupos asociados a la ENI real del Pod o del nodo en vez de dar por hecho que todos los nodos usan el grupo de seguridad del clúster de EKS. Permite también que el plano de control de EKS acceda al webhook del controlador en el puerto requerido. No abras todos los puertos a toda Internet.

### Configuración del rol de IAM

El **rol del controlador** administra los recursos de la nube. El **rol del llamador** firma las solicitudes de la aplicación y necesita `vpc-lattice-svcs:Invoke`; son roles distintos.

Usa EKS Pod Identity en los nodos compatibles o IRSA. El ejemplo de IRSA siguiente presupone que el proveedor de OIDC de IAM del clúster ya existe y crea una cuenta de servicio dedicada. Para Pod Identity, usa el complemento actual de EKS y una asociación para este mismo espacio de nombres/cuenta de servicio, con la política de confianza correspondiente; no dependas también de una anotación de IRSA para el mismo ejemplo.

La política recomendada para el controlador en esta versión incluye permisos amplios `vpc-lattice:*` y permisos de registro/etiquetado. Considérala un punto de partida del proyecto upstream, **no una política de privilegio mínimo**. Revisa su ámbito de recursos y las funciones habilitadas, conserva las condiciones restringidas del rol vinculado al servicio y guarda la política revisada antes de crearla. En ejecuciones posteriores, reutiliza el ARN de una política existente y revisada en vez de crear políticas duplicadas.

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

Una cuenta de servicio existente requiere una migración intencional de propiedad/rol; el ejemplo no la sobrescribe automáticamente.

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

Para una versión existente de Helm, usa un plan revisado de `helm upgrade` con los valores guardados. Helm no actualiza automáticamente los CRD de `crds/`; revisa sus cambios por separado. No elimines CRD de Gateway API compartidos ni políticas de admisión para conseguir que se complete una actualización.

Para implementar mediante manifiestos, renderiza este **mismo chart** con `helm template --include-crds`, usando los mismos valores y la misma elección de cuenta de servicio; luego revisa y aplica el manifiesto resultante. Así se conservan los permisos RBAC publicados, las observaciones de EndpointSlice, los permisos de elección de líder y la configuración del webhook. No uses la implementación manual obsoleta de v1.0. El chart genera certificados del webhook, salvo que se proporcionen explícitamente o se administren mediante su opción cert-manager; durante las actualizaciones, mantén coherentes el Secret del webhook y el paquete de CA en lugar de volver a generar uno por separado.

### Crear la red de servicios

Elige **CLI o CloudFormation**, no ambas, para la misma red. El ejemplo de CLI crea una red `AWS_IAM`. Hasta que se instale y propague una política Allow aplicable, las solicitudes se deniegan.

Guarda lo siguiente como `api-auth-policy.json` y sustituye la cuenta y el rol del llamador. La política de red permite deliberadamente solo el endpoint `/api` de esta demostración y sus subrutas. Una red de producción necesita una política revisada que incluya los servicios y llamadores previstos.

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

Comprueba que la asociación esté `ACTIVE`, que la red siga teniendo `authType: AWS_IAM` y que `get-auth-policy` devuelva la política prevista antes de exponer una ruta. La propagación de políticas puede tardar unos minutos.

La plantilla equivalente de CloudFormation para la **red y la asociación** es:

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

Esta plantilla no asocia una política de autenticación. Añade un recurso de política de autenticación dentro del mismo modelo de propiedad o aplica explícitamente la política de red revisada antes de probar las solicitudes. Obtén el ID/ARN de la red de las salidas de la pila. Valida la plantilla y revisa un conjunto de cambios antes de implementarla; el ejemplo no crea la VPC ni sus grupos de seguridad.

### Gateway y aplicación

Guarda y aplica esto como `gateway.yaml`. El nombre del Gateway debe coincidir con `my-network`, creado anteriormente.

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

`certificateRefs: [{name: unused}]` sigue la configuración documentada de este controlador: cumple la configuración TLS de Gateway API, pero este controlador no lee ningún Secret TLS de Kubernetes allí. Si no hay un nombre de host personalizado, Lattice proporciona un certificado para su dominio generado. Esto es **específico del controlador**, no una receta portátil para administrar certificados.

Guarda lo siguiente como `stable.yaml`. Configura NGINX para que realmente escuche en 8080 y sirva `/health`; declarar solo `containerPort` no haría ninguna de las dos cosas.

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
        image: nginx:1.30.6-alpine@sha256:970364228b1e4f932abc22d321932816782cca8a20b85a77552a7cfe9acfb3b5
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

Crea `canary.yaml` a partir de los mismos tres objetos; cambia todos los nombres `service-stable` por `service-canary`, cambia las etiquetas `version: stable` de los selectores y las plantillas por `version: canary`, y cambia el valor de respuesta JSON `"stable"` por `"canary"`. Mantén sin cambios `app: lattice-demo`, el puerto y el endpoint de comprobación de estado. Aplica ambos archivos en `lattice-demo`. La imagen fijada tiene variantes Linux AMD64 y ARM64. Las solicitudes de recursos y el número de réplicas son valores de demostración, no un dimensionamiento de producción medido.

Guarda y aplica la siguiente `TargetGroupPolicy`; crea una política `canary-health` equivalente para `service-canary`.

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

El CRD usa `intervalSeconds`, `timeoutSeconds` y `statusMatch`. AWS CLI usa nombres de campos distintos, que se muestran más adelante. Cambiar el protocolo/la versión puede sustituir un grupo de destino; eliminar la política revierte su configuración, incluido el comportamiento HTTP/HTTP1 predeterminado.

## Administración de servicios

### Crear un servicio mediante HTTPRoute

Guarda esto como `api-route.yaml`. Guarda también la IAMAuthPolicy siguiente como `api-iam.yaml`. Aplica la aplicación y las políticas de comprobación de estado, y luego la ruta y la política de autenticación. Mantén activa la política de nivel de red `AWS_IAM` mientras la reconciliación crea y protege el servicio de la ruta.

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

`spec.policy` es una **cadena** JSON. Este CRD habilita `AWS_IAM` en el servicio de destino; una anotación de tipo de autenticación o un ConfigMap que contenga una política no lo sustituye. Una política que tenga como destino `Gateway` administraría en cambio la política de la red, por lo que no debe competir con la política de red administrada externamente en este ejemplo.

Inspecciona los estados `Accepted` / `ResolvedRefs` y el estado de las políticas, el estado del recurso de AWS correspondiente y la disponibilidad del backend. Un `kubectl apply` correcto no demuestra que la reconciliación de la nube o la entrega de registros se hayan realizado correctamente.

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

Configura el cliente firmado de la sección siguiente antes de ejecutar el último comando. Ejecútalo desde una ubicación de red autorizada con credenciales del **rol del llamador**. Tu estación de trabajo necesita una ruta de red adecuada además de credenciales de AWS.

### Cliente HTTPS firmado

Guarda esto como `lattice_get.py`. Usa la cadena de proveedores de credenciales predeterminada de AWS, fija las credenciales para cada solicitud, firma para **`vpc-lattice-svcs`** y establece **`UNSIGNED-PAYLOAD`**, tal como requiere VPC Lattice. Valida TLS, no sigue redirecciones con una firma obsoleta y no vuelve a intentar las solicitudes automáticamente.

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

Este ejemplo, que solo admite GET, se comprobó con Python 3.12 y botocore 1.43.93. Las cargas de trabajo deben usar las credenciales de Pod Identity o IRSA que tengan configuradas. No copies credenciales estáticas ni encabezados firmados en manifiestos, registros ni solicitudes de soporte. VPC Lattice también admite SigV4A; este ejemplo usa SigV4 regional.

### Administración directa de la API de AWS

Lo siguiente es una **alternativa** para recursos administrados de forma independiente. Usa una IP de backend estable y accesible que sirva HTTP en 8080 y `/health`; una IP temporal de Pod requiere un controlador que siga sus reemplazos. No cambies manualmente un servicio propiedad de HTTPRoute esperando que el controlador conserve el cambio.

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

Espera a que haya destinos en buen estado y asociaciones activas antes de llamar al dominio HTTPS detectado. Este ejemplo usa un certificado administrado por AWS para el dominio generado, no un dominio personalizado.

### Actualización y eliminación de servicios

Para recursos propiedad de Kubernetes, cambia la Route, la carga de trabajo del backend o el manifiesto de la política y verifica la reconciliación. Para recursos propiedad de la API, usa la API de actualización correspondiente y comprueba el estado resultante. Captura los ID de los recursos de las respuestas en lugar de seleccionar el primer servicio de la cuenta.

Antes de eliminar recursos, identifica a todos los consumidores, las asociaciones de red, los listeners/reglas, las referencias a grupos de destino y la propiedad. Elimina las asociaciones de Route/servicio específicas y los recursos de servicio en el orden de sus dependencias; después, elimina los grupos de destino que ya no se usen. Un Gateway/red compartido puede afectar a otros espacios de nombres o cuentas. Conserva el controlador hasta que se completen los finalizadores y la limpieza de la nube; no uses eliminaciones masivas.

**Al eliminar IAMAuthPolicy, se desactiva la autenticación de IAM en su destino (`NONE`) antes de separar la política.** No sirve para denegar el acceso ni para revertir la autorización de forma segura. Mantén una política restrictiva mientras eliminas un servicio y verifica los controles restantes de red/servicio.

## Enrutamiento y administración del tráfico

### Coincidencia de rutas y encabezados

La ruta anterior coincide con `/api` y su subárbol. Para añadir una regla canary explícita basada en encabezados, sustituye la misma HTTPRoute por esta:

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

El controlador documenta la coincidencia de rutas sin distinguir mayúsculas de minúsculas, una coincidencia de método por regla, hasta cinco coincidencias de encabezado y ninguna coincidencia de parámetros de consulta. No des por hecho que se implementan todos los filtros o coincidencias de Gateway API. Una HTTPRoute independiente crea otro servicio/dominio de Lattice, en lugar de añadir automáticamente una regla al primer servicio.

### Enrutamiento ponderado

`backendRefs.weight: 90` y `10` son configuración nativa de Gateway API; no se necesita ninguna anotación de enrutamiento ponderado. Expresan una distribución relativa, no un resultado exacto para diez solicitudes. Comprueba los endpoints, el estado, los errores y la latencia de ambas versiones en una muestra adecuada antes de aumentar el peso de canary.

Para recursos de AWS administrados de forma independiente:

```bash
# TG_STABLE and TG_CANARY are existing target groups managed by this API workflow.
aws vpc-lattice create-rule --service-identifier "$SERVICE_ID" \
  --listener-identifier "$LISTENER_ID" --name api-canary --priority 10 \
  --match '{"httpMatch":{"pathMatch":{"match":{"prefix":"/api"},"caseSensitive":false}}}' \
  --action "{\"forward\":{\"targetGroups\":[{\"targetGroupIdentifier\":\"${TG_STABLE}\",\"weight\":90},{\"targetGroupIdentifier\":\"${TG_CANARY}\",\"weight\":10}]}}"
```

La coincidencia de prefijo de CLI es un prefijo léxico; revisa por separado el comportamiento en los límites y la semántica de `PathPrefix` de Kubernetes. Las coincidencias de enrutamiento no son un límite de autorización. No uses una prueba de enrutamiento de rutas como demostración de que una política de IAM cubre todas las variantes de rutas normalizadas o codificadas.

### Comprobaciones de estado

El ejemplo de Kubernetes usa `TargetGroupPolicy`. La actualización de API equivalente es:

```bash
aws vpc-lattice update-target-group --target-group-identifier "$TARGET_GROUP_ID" \
  --health-check '{"enabled":true,"protocol":"HTTP","protocolVersion":"HTTP1","port":8080,"path":"/health","healthCheckIntervalSeconds":30,"healthCheckTimeoutSeconds":5,"healthyThresholdCount":2,"unhealthyThresholdCount":2,"matcher":{"httpCode":"200"}}'
```

Las comprobaciones de estado evalúan la disponibilidad según los umbrales; no garantizan disponibilidad ni cero tiempo de inactividad. Los grupos de destino HTTP1 las habilitan de forma predeterminada, mientras que HTTP2 requiere una consideración explícita. Los destinos gRPC usan comprobaciones de estado HTTP1/HTTP2, y los tipos de destino Lambda/ALB tienen un comportamiento de comprobación de estado distinto. Consulta la documentación actual del tipo de destino en lugar de aplicar el ejemplo de Pod a todos los destinos.

## Seguridad y autenticación

### Políticas de autenticación y permisos del llamador

`put-auth-policy` / `get-auth-policy` administran la autorización de invocación. `put-resource-policy` es una API distinta de administración/uso compartido. Usa la acción **`vpc-lattice-svcs:Invoke`** para los llamadores.

Cuando tanto la red como el servicio usan `AWS_IAM`, la política de identidad del llamador y **ambas** políticas de autenticación aplicables deben permitir el acceso. Un Deny explícito prevalece. `NONE` en un recurso no cancela el requisito de IAM de otro recurso. El tráfico directo a un ClusterIP/Pod IP de Kubernetes omite la autenticación de Lattice; protege esas rutas con controles de red y de aplicación adecuados.

`StringEquals` no interpreta `/api/*` como comodín. El ejemplo usa `StringLike` e incluye tanto `/api` como `/api/*`. La coincidencia de condiciones de IAM y la normalización de rutas de la aplicación pueden diferir del enrutamiento del controlador. Para las funciones administrativas, prefiere un servicio dedicado y restringido a roles administrativos, y conserva la autorización de la aplicación; no añadas un Allow general amplio suponiendo que un comodín de ruta protege todos los alias.

### Acceso entre cuentas

El uso compartido mediante RAM permite asociarse a la entidad compartida; por sí solo, no concede la invocación de la aplicación. Las políticas de autenticación de red/servicio, los permisos del llamador, los grupos de seguridad de la asociación y la ruta de red también deben permitir la solicitud.

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

Si el uso compartido con Organizations está habilitado, los consumidores que pertenecen a la organización obtienen acceso sin invitación. Otros acuerdos de uso compartido compatibles requieren aceptar una invitación. Para compartir con una organización o unidad organizativa (OU), usa su **ARN real de Organizations**, incluido el identificador de la cuenta de administración, en lugar de construir uno a partir del ID de una cuenta miembro.

Los propietarios pueden compartir servicios, redes y configuraciones de recursos, pero no roles de IAM individuales como consumidores de RAM. Dejar de compartir impide nuevas asociaciones, pero **no elimina las asociaciones existentes**. Revísalas explícitamente al revocar el acceso.

### TLS y dominios personalizados

El Gateway de ejemplo solo expone HTTPS. Para usar un nombre de host personalizado, crea el servicio con ese nombre, obtén un certificado de ACM coincidente y configura DNS para que apunte al dominio asignado real. Solo se admite un dominio personalizado por servicio y no se puede cambiar después de crear el servicio.

Para el controlador, configura `spec.hostnames` de HTTPRoute y `tls.options["application-networking.k8s.aws/certificate-arn"]` del listener de Gateway, o usa la detección de ACM documentada. No pongas claves privadas en una anotación. La automatización de ExternalDNS requiere además su controlador, permisos y el CRD DNSEndpoint; configurar un nombre de host no demuestra por sí solo que existan registros DNS.

```bash
# For an API-managed service created with the required custom domain name:
aws vpc-lattice update-service --service-identifier "$SERVICE_ID" \
  --certificate-arn "$ACM_CERTIFICATE_ARN"
# Create an HTTPS listener separately if the service does not already have one.
# create-listener uses --protocol HTTPS; there is no --tls mode=STRICT option.
```

HTTPS hacia el cliente y TLS del backend son independientes. Una `TargetGroupPolicy` de backend con `protocol: HTTPS` también requiere un backend que realmente use TLS y una comprobación de estado HTTPS compatible. VPC Lattice **no valida los certificados del backend**; esto cifra la conexión sin autenticar la identidad del certificado del backend. Usa el modelo independiente de paso transparente TLSRoute cuando ese sea el diseño previsto y revisa sus limitaciones funcionales.

## Supervisión y registro

### Métricas de CloudWatch, panel y alarma

Las métricas de servicio usan el espacio de nombres **`AWS/VpcLattice`**:

| Métrica | Significado / estadística |
|---|---|
| `TotalRequestCount` | Recuento de solicitudes; `Sum` |
| `HTTPCode_4XX_Count` | Respuestas 4xx; `Sum` |
| `HTTPCode_5XX_Count` | Respuestas 5xx; `Sum` |
| `RequestTime` | Duración de la solicitud en **milisegundos**; promedio o un percentil adecuado |

Las métricas de servicio usan la dimensión `Service`, opcionalmente con `AvailabilityZone`; las métricas de grupos de destino usan `TargetGroup`. Un nombre como `ServiceName=my-service` no identifica estas métricas. Descubre los valores/conjuntos de dimensiones reales:

```bash
aws cloudwatch list-metrics --namespace AWS/VpcLattice \
  --metric-name HTTPCode_5XX_Count --dimensions Name=Service > metrics.json
python3 - <<'PY'
import json
for metric in json.load(open("metrics.json"))["Metrics"]:
    print(json.dumps(metric["Dimensions"]))
PY
```

Después de que el tráfico haya generado métricas, selecciona la matriz de dimensiones **de todo el servicio** previsto y guárdala como `service-dimensions.json`. No selecciones arbitrariamente el primer resultado ni mezcles una métrica de zona de disponibilidad con un agregado. Verifica el identificador con el servicio que se está observando. Crea `dashboard.json` con lo siguiente:

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

La alarma significa **más de cinco respuestas 5xx por minuto en dos de tres períodos**, no una tasa de error del 5 %. Configura por separado las acciones de alarma revisadas si se necesitan notificaciones. La opción de datos faltantes es explícita: las métricas se publican después de que empieza el tráfico y NoData no debe tratarse silenciosamente como prueba de buen estado. La configuración del panel y de la alarma son ejemplos, no SLO específicos de una carga de trabajo.

### Registro de acceso

Para CloudWatch Logs, usa un destino existente o crea un grupo de registros dedicado con una política de retención:

```bash
export LOG_GROUP=/aws/vendedlogs/vpc-lattice/api
aws logs create-log-group --log-group-name "$LOG_GROUP"
aws logs put-retention-policy --log-group-name "$LOG_GROUP" --retention-in-days 30
export LOG_DESTINATION_ARN="arn:aws:logs:${AWS_REGION}:${AWS_ACCOUNT_ID}:log-group:${LOG_GROUP}:*"

# API-managed service only; for an HTTPRoute use AccessLogPolicy below instead.
aws vpc-lattice create-access-log-subscription \
  --resource-identifier "$SERVICE_ID" --destination-arn "$LOG_DESTINATION_ARN"
```

La entidad principal de configuración también necesita los permisos de entrega de registros documentados. AWS puede crear/actualizar la política de recursos de registro si la entidad principal de configuración tiene los permisos necesarios; de lo contrario, configúrala previamente. Verifica los permisos de `delivery.logs.amazonaws.com` y las condiciones de cuenta de origen/ARN de origen.

Para la ruta administrada por Kubernetes, usa esto **en lugar de** una suscripción creada por CLI que compita con ella:

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

Sustituye el ARN y confirma el estado de la política y la entrega real de eventos. Una política puede tener como destino un Gateway para los registros de red o una Route para los registros del servicio. Puede haber un destino de cada tipo compatible por destino.

Para S3, usa un bucket de destino revisado con bloqueo de acceso público, cifrado, reglas de retención/ciclo de vida y permisos de entrega adecuados:

```bash
# Existing reviewed destination bucket; no policy is overwritten by this snippet.
aws vpc-lattice create-access-log-subscription \
  --resource-identifier "$SERVICE_ID" --destination-arn "$LOG_BUCKET_ARN"
```

La entrega a S3 requiere los permisos documentados `s3:GetBucketAcl` y `s3:PutObject` para `delivery.logs.amazonaws.com`, el prefijo de entrega y las condiciones `aws:SourceAccount` y `aws:SourceArn`. Las políticas existentes deben combinarse, no sobrescribirse. SSE-KMS requiere una clave administrada por el cliente compatible y su política de clave de entrega. `--destination-name` no es un parámetro de suscripción al registro de acceso.

### Análisis de registros y rastreo

Los registros de acceso de servicios HTTP contienen campos como `sourceIpPort`, `requestMethod`, `requestPath`, `responseCode`, `durationMS`, `callerPrincipal` y `authDeniedReason`. Los registros de recursos/TCP tienen un esquema distinto.

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

VPC Lattice no tiene una opción `update-service --tracing-config` ni una anotación del controlador que instrumente automáticamente las aplicaciones para X-Ray. Instrumenta las aplicaciones con OpenTelemetry/ADOT o el SDK de rastreo adecuado, propaga el contexto de rastreo y configura la exportación/el muestreo. Correlaciona los seguimientos de la aplicación con los registros de acceso y los ID de solicitud; un ID de solicitud proporcionado por el cliente no es una identidad autenticada.

## Prácticas recomendadas

- **Diseño y propiedad:** Usa nombres claros para redes/servicios y límites de entorno. Ten en cuenta los Gateways con el mismo nombre en distintos espacios de nombres, los consumidores de redes compartidas, las cuotas y la propiedad de cada política y asociación.
- **Implementación:** Mantén los backends estable y canary seleccionables de forma independiente. Comprueba los endpoints, el estado de los destinos y la autorización antes de cambiar los pesos. Define criterios de reversión y conserva la última configuración conocida.
- **Rendimiento:** Usa tiempos de espera acotados y reutilización de conexiones adecuada. Mantén los endpoints de comprobación de estado ligeros y significativos. Usa caché o procesamiento por lotes solo cuando la semántica de la aplicación lo permita. Los servicios privados de Lattice no se convierten en orígenes de CDN simplemente por habilitar el almacenamiento en caché.
- **Seguridad:** Separa los roles de administración y de llamador; mantén las credenciales fuera de los manifiestos. Prueba los roles permitidos y denegados, las rutas raíz y subrutas, el acceso directo al backend y el comportamiento de TLS. No elimines un CRD de política de IAM para denegar el tráfico.
- **Observabilidad:** Supervisa por separado el recuento de solicitudes, el recuento/la tasa de errores, la latencia, el estado de los destinos y la telemetría faltante. Conserva los registros de acceso durante el período requerido e instrumenta explícitamente los seguimientos de la aplicación.
- **Costo:** Revisa los cargos regionales actuales por servicio/recurso, solicitudes, procesamiento de datos, endpoints y registro para el modelo elegido. Usa etiquetas, elimina solo los recursos cuya falta de uso se haya confirmado y dimensiona el escalado automático del backend por separado del plano de datos administrado de Lattice.

## Resolución de problemas

Usa los identificadores de las anotaciones/estados del controlador y del inventario de AWS. No des por hecho que el `$SERVICE_ID` del ejemplo de API directa es el servicio de la ruta de Kubernetes.

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
| Error de DNS/conectividad | DNS asignado real, asociación de VPC del cliente o ruta del endpoint, estado de asociación, grupos de seguridad, NACL, conectividad de los Pods |
| Error 403/de autenticación | Rol del llamador, caducidad de credenciales y región/servicio de firma, `UNSIGNED-PAYLOAD`, ambas capas de autenticación, propagación, campos de registro del motivo de denegación |
| Ruta o versión incorrecta | Condiciones de Route, prioridad y coincidencias del listener/regla, miembros del grupo de destino, pesos, dominios distintos de Route |
| Destinos en mal estado | Puerto de escucha real, `/health`, HTTP frente a HTTPS, disponibilidad, grupos de seguridad, tipo de destino y umbrales de comprobación de estado |
| Sin registros/métricas | Permisos de destino y estado de entrega, dimensiones de métrica correctas, tráfico inicial, retención, estado de consulta |
| Error de reconciliación del controlador | Registros de `manager`, rol de IAM, EndpointSlices, compatibilidad de versiones de CRD, estado del webhook y de la elección de líder |

Usa un intervalo acotado de métricas sin depender de `date -d`, que solo está disponible en GNU:

```bash
export METRIC_END="$(python3 -c 'from datetime import datetime,timezone; print(datetime.now(timezone.utc).isoformat())')"
export METRIC_START="$(python3 -c 'from datetime import datetime,timedelta,timezone; print((datetime.now(timezone.utc)-timedelta(hours=1)).isoformat())')"
aws cloudwatch get-metric-statistics --namespace AWS/VpcLattice \
  --metric-name HTTPCode_5XX_Count --dimensions file://service-dimensions.json \
  --start-time "$METRIC_START" --end-time "$METRIC_END" \
  --period 60 --statistics Sum
```

Si se produce un incidente de servicio de AWS, consulta AWS Health y los eventos pertinentes de la cuenta. El acceso a la API y las operaciones de soporte específicas de la cuenta dependen del plan y los endpoints aplicables. Un caso de soporte debe incluir los ID de recursos revisados, el intervalo de tiempo, los síntomas del fallo y registros con datos sensibles enmascarados. Selecciona las opciones actuales de servicio/categoría/severidad para la cuenta; no pegues un comando codificado de creación de caso con `urgent`.

## Referencias

- [Descripción general de VPC Lattice](https://docs.aws.amazon.com/vpc-lattice/latest/ug/what-is-vpc-lattice.html)
- [Asociaciones de redes de servicios](https://docs.aws.amazon.com/vpc-lattice/latest/ug/service-network-associations.html)
- [Instalación de Controller v2.1.3](https://github.com/aws/aws-application-networking-k8s/blob/v2.1.3/docs/guides/deploy.md)
- [Requisitos de actualización de Controller v2.1](https://github.com/aws/aws-application-networking-k8s/blob/v2.1.3/docs/guides/upgrading-v2-0-x-to-v2-1-y.md)
- [Referencia de la API de Controller](https://github.com/aws/aws-application-networking-k8s/tree/v2.1.3/docs/api-types)
- [HTTPS y TLS del backend de Controller](https://github.com/aws/aws-application-networking-k8s/blob/v2.1.3/docs/guides/https.md)
- [Políticas de autenticación de VPC Lattice](https://docs.aws.amazon.com/vpc-lattice/latest/ug/auth-policies.html)
- [Firma de solicitudes](https://docs.aws.amazon.com/vpc-lattice/latest/ug/sigv4-authenticated-requests.html)
- [Uso compartido de entidades](https://docs.aws.amazon.com/vpc-lattice/latest/ug/sharing.html)
- [Métricas de CloudWatch](https://docs.aws.amazon.com/vpc-lattice/latest/ug/monitoring-cloudwatch.html)
- [Registros de acceso](https://docs.aws.amazon.com/vpc-lattice/latest/ug/monitoring-access-logs.html)
- [Permisos de entrega de CloudWatch Logs](https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/AWS-logs-infrastructure-CWL.html)
- [Permisos de entrega de S3](https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/AWS-logs-infrastructure-S3.html)

## Cuestionario

Comprueba lo que sabes con el [cuestionario de VPC Lattice](../quizzes/networking/02-vpc-lattice-quiz.md).
