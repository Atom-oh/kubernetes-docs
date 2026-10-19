# VPC Lattice

Amazon VPC Lattice conecta aplicaciones entre VPC y cuentas de AWS. Este capítulo explica el modelo de recursos, una integración con EKS, el enrutamiento, la autorización IAM, la monitorización y la solución de problemas.

> **Última actualización**: 11 de septiembre de 2026, con AWS Gateway API Controller **v2.1.3** y Gateway API **v1.5.0**. Los ejemplos describen pasos de configuración y validación; no se han desplegado en una cuenta de AWS como parte de esta revisión.

## Tabla de contenidos

- [Descripción general](#overview)
- [Arquitectura](#architecture)
- [Integración de EKS y VPC Lattice](#eks-and-vpc-lattice-integration)
- [Instalación y configuración](#installation-and-configuration)
- [Gestión de servicios](#service-management)
- [Enrutamiento y gestión del tráfico](#routing-and-traffic-management)
- [Seguridad y autenticación](#security-and-authentication)
- [Monitorización y registro](#monitoring-and-logging)
- [Prácticas recomendadas](#best-practices)
- [Solución de problemas](#troubleshooting)
- [Referencias](#references)

## Descripción general {#overview}

### ¿Qué es VPC Lattice?

VPC Lattice proporciona conectividad para aplicaciones sin exigir un proxy junto a cada una. Una **red de servicios (service network)** agrupa servicios y configuraciones de recursos, y permite que los consumidores autorizados accedan a ellos. Cada servicio ofrece listeners, reglas de enrutamiento, grupos de destinos (target groups) y un nombre DNS propio.

La versión actual de VPC Lattice también permite acceder a **configuraciones de recursos** mediante puertas de enlace de recursos, incluidas bases de datos RDS que usan TCP. Este modelo es distinto del de un servicio HTTP con un grupo de destinos: las políticas de autenticación IAM de la red de servicios o del servicio no autorizan el tráfico hacia configuraciones de recursos. Un **endpoint de VPC de la red de servicios**, basado en PrivateLink, puede dar acceso a clientes que llegan mediante emparejamiento de VPC, Transit Gateway, Direct Connect o VPN. Una asociación directa de VPC, por sí sola, no extiende el acceso a clientes que están detrás de una puerta de enlace de tránsito o una conexión de emparejamiento.

Los usos habituales incluyen API de aplicaciones entre cuentas, comunicación entre EKS y otros servicios de computación, y acceso compartido a recursos de datos. La asociación, el enrutamiento, los security groups, la autenticación y la autorización de la aplicación aún requieren configuración.

### Comparación con otros servicios

| Servicio | Responsabilidad principal | Distinción importante |
|---|---|---|
| VPC Lattice | Conectividad privada de aplicaciones y recursos | Enrutamiento de servicios HTTP/HTTPS/gRPC y capacidades separadas de recursos TLS/TCP; no es una puerta de entrada de API de Internet |
| API Gateway | Endpoints de API administrados y gestión de API | Las API REST, HTTP o WebSocket tienen características diferentes; GraphQL no es un tipo de API de API Gateway independiente |
| AWS App Mesh | Service mesh basado en Envoy | El soporte de AWS finalizó el **2026-09-30**; la consola y los recursos ya no son accesibles. Migre los despliegues existentes; no es para instalaciones nuevas |
| Transit Gateway | Conectividad de red mediante enrutamiento IP | Conecta redes; no sustituye el enrutamiento y la autorización HTTP por servicio |
| Istio / Linkerd / Cilium | Capacidades de mesh implementadas con sus respectivos planos de datos | Las características y los costes operativos difieren. Los sidecars no son obligatorios en todas las arquitecturas de mesh |

VPC Lattice elimina la necesidad de operar su plano de datos gestionado, pero no garantiza un coste total menor ni ofrece las mismas funciones que una malla de servicios. Compare los cargos por solicitudes, datos y recursos, las operaciones del controlador, los requisitos de identidad, los reintentos, las funciones de enrutamiento y la observabilidad para la carga de trabajo real. Consulte la [comparación de Istio y Lattice](../service-mesh/istio/comparison/02-istio-vs-lattice.md).

## Arquitectura {#architecture}

### Componentes y flujo de tráfico

| Componente | Responsabilidad |
|---|---|
| Red de servicios (service network) | Agrupación lógica y asociaciones; límite opcional de autorización IAM |
| Servicio | Punto de acceso de la aplicación con su propio nombre DNS |
| Listener y reglas | Pertenecen a un **servicio**; seleccionan acciones y grupos de destinos |
| Grupo de destinos (target group) | Instancias, direcciones IP, funciones Lambda o destinos ALB registrados, con comportamiento propio de cada tipo |
| Asociación de VPC | Permite que los clientes de una VPC asociada accedan a la red, sujetos a los controles de seguridad |
| Endpoint de VPC de la red de servicios | Acceso basado en PrivateLink, incluidas las rutas compatibles desde redes de tránsito o locales |
| Configuración de recursos / puerta de enlace de recursos | Modelo de acceso independiente, incluidos recursos TCP y bases de datos |

![Tres VPC de dos cuentas de AWS se asocian con una red de servicios, cuyos servicios usan grupos de destinos para cargas de trabajo de EC2, EKS y Lambda.](../.gitbook/assets/en-networking-02-vpc-lattice-1.png)

[Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-networking-02-vpc-lattice-1.html)

La figura muestra asociaciones lógicas, no un único proceso de enrutamiento. El acceso también depende de la conectividad de red y de las políticas aplicables. Una solicitud resuelve el nombre DNS **del servicio**, llega a su listener, supera las comprobaciones de autorización aplicables y se enruta a un destino según las reglas del listener. Un grupo de destinos describe los destinos finales; no representa otro salto de aplicación.

Use `get-service --query dnsEntry` o la anotación de ruta del controlador para descubrir el dominio real. No lo construya a partir del nombre del servicio y del ID de la red de servicios. El nombre asignado contiene identificadores propios del servicio y puede cambiar si se vuelve a crear el servicio.

### Modelo de seguridad

El acceso de red, la autorización IAM y el cifrado son controles independientes. `AWS_IAM` requiere una solicitud firmada compatible y políticas apropiadas. `NONE` deshabilita la autenticación IAM en esa capa concreta; no omite la política IAM de otra capa, los grupos de seguridad ni la autorización de la aplicación. HTTPS protege el tráfico del cliente a Lattice. El HTTP del backend sigue en texto sin cifrar salvo que TLS del backend se configure explícitamente.

## Integración de EKS y VPC Lattice {#eks-and-vpc-lattice-integration}

AWS Gateway API Controller reconcilia recursos de Kubernetes en recursos de VPC Lattice:

| Recurso de Kubernetes | Interpretación de Lattice |
|---|---|
| GatewayClass | Selecciona `application-networking.k8s.aws/gateway-api-controller` |
| Gateway | Hace referencia a una red de servicios mediante el **nombre del recurso Gateway**, sin incluir su espacio de nombres |
| HTTPRoute / GRPCRoute | Crea un servicio con su propio dominio y configuración de listener/enrutamiento |
| Servicio backend y sus endpoints | Definen grupos de destinos y los endpoints de Pod registrados |
| TargetGroupPolicy | Configura el protocolo y las comprobaciones de estado del grupo de destinos |
| IAMAuthPolicy | Adjunta una política de autenticación a la red de un Gateway o al servicio de una Route |
| AccessLogPolicy | Configura el destino de los registros de acceso de un recurso de destino |

Dos Gateways con el mismo nombre pueden hacer referencia a la misma red de servicios aunque estén en espacios de nombres de Kubernetes distintos. Un Gateway por sí solo **no** crea la red ni una IP de entrada compartida. La red puede gestionarse externamente, mediante la opción `defaultServiceNetwork` del controlador para casos sencillos o mediante el CRD ServiceNetwork del controlador. Elija un único responsable para cada recurso en la nube.

Los ejemplos siguientes usan una red y una asociación de VPC gestionadas externamente. Dejan `defaultServiceNetwork` sin configurar y no adjuntan una VpcAssociationPolicy a esa asociación. Si adopta el modelo basado en CRD, gestione la red, la asociación de VPC y la autorización como recursos independientes; no gestione esos mismos recursos también con CloudFormation.

## Instalación y configuración {#installation-and-configuration}

### Requisitos previos

La guía de actualización v2.1 del controlador requiere **Kubernetes 1.31 o posterior** y Gateway API **1.5 o posterior**. Este ejemplo fija la versión con la que se compiló v2.1: **1.5.0**. Este mínimo no constituye una matriz de versiones compatibles de EKS ni demuestra compatibilidad con todas las versiones posteriores de Gateway API. Antes de cambiar los CRD de Gateway API, compruebe el ciclo de vida de las versiones de EKS y de todos los controladores que los comparten. En particular, un controlador v2.0 puede fallar tras el cambio de almacenamiento/API de TLSRoute introducido en Gateway API 1.5.

Use un clúster de EKS compatible, las versiones correspondientes de `kubectl`, Helm y AWS CLI v2, y un rol de operador autorizado para configurar los recursos previstos. El backend de ejemplo presupone Pods Linux con direcciones IP accesibles desde VPC Lattice. Compruebe la CNI del clúster, la capacidad de las subredes, la disponibilidad de los endpoints, el DNS y la configuración de las políticas de red.

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

Sustituya el ID de ejemplo del grupo de seguridad. El grupo de seguridad de la asociación de VPC debe permitir el acceso de **clientes autorizados** por TCP 443. Los grupos de seguridad de los Pods o nodos de backend deben permitir la lista de prefijos administrada por Lattice que corresponda, en el puerto real del backend y de la comprobación de estado (TCP 8080 en este ejemplo). Inspeccione los grupos asociados a la ENI real del Pod o del nodo; no suponga que todos los nodos usan el grupo de seguridad del clúster de EKS. Permita también que el plano de control de EKS alcance el webhook del controlador por el puerto requerido. No abra todos los puertos a todo Internet.

### Configuración del rol IAM

El **rol del controlador** administra los recursos en la nube. El **rol del llamador** firma las solicitudes de la aplicación y necesita `vpc-lattice-svcs:Invoke`; son roles distintos.

Use EKS Pod Identity en los nodos compatibles o IRSA. El ejemplo de IRSA presupone que ya existe el proveedor IAM OIDC del clúster y crea una cuenta de servicio dedicada. Para Pod Identity, use el complemento actual de EKS y una asociación para ese mismo espacio de nombres y cuenta de servicio, con la política de confianza adecuada. No combine ambos métodos ni dependa de una anotación IRSA en este ejemplo.

La política recomendada para el controlador en esta versión incluye permisos amplios de `vpc-lattice:*` y de registro y etiquetado. Tómela como punto de partida del proyecto, **no como una política de mínimo privilegio**. Revise el alcance de los recursos y las funciones habilitadas, conserve las condiciones restrictivas del rol vinculado al servicio y guarde la política revisada antes de crearla. En ejecuciones posteriores, reutilice el ARN de una política ya revisada en vez de crear duplicados.

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

Una cuenta de servicio existente requiere una migración deliberada de propiedad o de rol; el ejemplo no la sobrescribe automáticamente.

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

Si ya existe una instalación de Helm, prepare un plan revisado de `helm upgrade` con los valores guardados. Helm no actualiza automáticamente los CRD de `crds/`; revise esos cambios por separado. No elimine CRD compartidos de Gateway API ni políticas de admisión para que la actualización funcione.

Para entregar la instalación mediante manifiestos, genere **este mismo chart** con `helm template --include-crds`, los mismos valores y la misma elección de cuenta de servicio; después revise y aplique el manifiesto resultante. Así se conservan el RBAC publicado, la observación de EndpointSlice, los permisos de elección de líder y la configuración del webhook. No use el obsoleto despliegue v1.0 escrito a mano. El chart genera certificados para el webhook, salvo que se proporcionen explícitamente o se administren con la opción cert-manager; durante las actualizaciones, mantenga coherentes el Secret del webhook y el paquete de certificados CA en vez de regenerarlos por separado.

### Crear la red de servicios

Elija **CLI o CloudFormation**, no ambas opciones para la misma red. El ejemplo de CLI crea una red con `AWS_IAM`. Las solicitudes se deniegan hasta que se instale y propague una política aplicable con efecto `Allow`.

Guarde lo siguiente como `api-auth-policy.json` y sustituya la cuenta y el rol del llamador. Para esta demostración, la política de red permite deliberadamente solo el endpoint `/api` y sus subrutas. Una red de producción requiere una política revisada que cubra los servicios y llamadores previstos.

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

Verifique que la asociación esté `ACTIVE`, que la red aún tenga `authType: AWS_IAM` y que `get-auth-policy` devuelva la política prevista antes de exponer una ruta. La propagación de políticas puede tardar unos minutos.

La plantilla de CloudFormation equivalente de **red y asociación** es:

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

Esta plantilla no adjunta una política de autenticación. Añada un recurso de política de autenticación bajo el mismo modelo de propiedad o aplique explícitamente la política de red revisada antes de probar las solicitudes. Obtenga el ID o ARN de la red en las salidas de la pila. Valide la plantilla e inspeccione un conjunto de cambios antes del despliegue; el ejemplo no crea la VPC ni sus grupos de seguridad.

### Gateway y aplicación

Guarde esto como `gateway.yaml` y aplíquelo. El nombre del recurso Gateway debe coincidir con `my-network`, creado anteriormente.

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

`certificateRefs: [{name: unused}]` sigue la configuración documentada de este controlador: satisface la configuración TLS de Gateway API, pero este controlador no lee allí ningún Secret TLS de Kubernetes. Si no se configura un nombre de host personalizado, Lattice proporciona un certificado para el dominio generado. Este comportamiento es **específico del controlador** y no constituye una receta de gestión de certificados portable a otros controladores.

Guarde lo siguiente como `stable.yaml`. Configura NGINX para que escuche en el puerto 8080 y sirva `/health`; declarar solo `containerPort` no consigue ninguna de esas dos cosas.

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

Cree `canary.yaml` a partir de los mismos tres objetos. Cambie cada nombre `service-stable` a `service-canary`, las etiquetas `version: stable` tanto del selector como de la plantilla por `version: canary`, y el valor JSON de respuesta `"stable"` por `"canary"`. Mantenga sin cambios `app: lattice-demo`, el puerto y el endpoint de comprobación de estado. Aplique ambos archivos en `lattice-demo`. La imagen fijada tiene variantes para Linux AMD64 y ARM64. Las solicitudes de recursos y el número de réplicas son valores de demostración, no un dimensionamiento de producción medido.

Guarde y aplique la siguiente `TargetGroupPolicy`; cree una política `canary-health` equivalente destinada a `service-canary`.

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

El CRD usa `intervalSeconds`, `timeoutSeconds` y `statusMatch`. La CLI de AWS usa otros nombres de campo, que se muestran más adelante. Cambiar el protocolo o la versión puede sustituir un grupo de destinos; al eliminar la política se revierten sus ajustes, incluido el comportamiento HTTP/HTTP1 predeterminado.

## Gestión de servicios {#service-management}

### Crear un servicio mediante HTTPRoute

Guarde esto como `api-route.yaml` y la IAMAuthPolicy siguiente como `api-iam.yaml`. Aplique las políticas de la aplicación y de comprobación de estado; después, aplique la ruta y la política de autenticación. Mantenga activa la política de red `AWS_IAM` mientras la reconciliación crea y protege el servicio de la ruta.

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

`spec.policy` es una **cadena** JSON. Este CRD habilita `AWS_IAM` en el servicio de destino; una anotación de tipo de autenticación o un ConfigMap que contiene una política no lo sustituye. Una política destinada a `Gateway` gestionaría en cambio la política de la red, por lo que no debe competir con la política de red gestionada externamente en este ejemplo.

Inspeccione `Accepted` / `ResolvedRefs`, el estado de la política y del recurso de AWS correspondiente, y la disponibilidad del backend. Que `kubectl apply` termine correctamente no demuestra que la reconciliación en la nube ni la entrega de registros hayan funcionado.

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

Configure el cliente firmado de la sección siguiente antes de ejecutar el último comando. Ejecútelo desde una ubicación con acceso de red autorizado y credenciales del **rol del llamador**. La estación de trabajo necesita una ruta de red adecuada y credenciales de AWS.

### Cliente HTTPS firmado

Guarde este archivo como `lattice_get.py`. Usa la cadena predeterminada de proveedores de credenciales de AWS, obtiene una copia fija de las credenciales para cada solicitud y firma para **`vpc-lattice-svcs`** con **`UNSIGNED-PAYLOAD`**, tal como requiere VPC Lattice. Valida TLS, no sigue redirecciones que dejarían una firma obsoleta y no reintenta las solicitudes automáticamente.

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

Este ejemplo, que solo realiza solicitudes GET, se verificó con Python 3.12 y botocore 1.43.93. Las cargas de trabajo deben usar las credenciales configuradas de Pod Identity o IRSA. No copie credenciales estáticas ni encabezados firmados en manifiestos, registros o tickets de soporte. VPC Lattice también admite SigV4A; este ejemplo usa SigV4 regional.

### Gestión directa mediante AWS API

Lo siguiente es una **alternativa** para administrar recursos por separado. Use una dirección IP estable y accesible para el backend, que atienda HTTP en el puerto 8080 y `/health`; si usa la IP temporal de un Pod, un controlador debe seguir sus reemplazos. No modifique manualmente un servicio gestionado por HTTPRoute y espere que el controlador conserve el cambio.

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

Antes de llamar al dominio HTTPS descubierto, espere a que los destinos estén en buen estado y las asociaciones, activas. Este ejemplo usa un certificado gestionado por AWS para el dominio generado, no para un dominio personalizado.

### Actualizar y eliminar servicios

Para recursos gestionados por Kubernetes, cambie el manifiesto de Route, la carga de trabajo del backend o la política, y compruebe la reconciliación. Para recursos gestionados mediante la API, use la operación de actualización correspondiente y compruebe el estado resultante. Anote los ID de recursos devueltos en las respuestas; no seleccione el primer servicio de la cuenta.

Antes de eliminar recursos, identifique todos los consumidores, las asociaciones de red, los listeners y sus reglas, las referencias a grupos de destinos y quién es responsable de cada recurso. Elimine las asociaciones específicas de ruta y servicio, y después los recursos de servicio según sus dependencias; por último, elimine los grupos de destinos que ya no se usen. Un Gateway o una red compartidos pueden afectar a otros espacios de nombres o cuentas. Mantenga el controlador hasta que terminen los finalizers y la limpieza en la nube; no use eliminaciones indiscriminadas.

**Al eliminar IAMAuthPolicy, se deshabilita la autenticación IAM (`NONE`) en el recurso al que se aplica antes de desvincular la política.** No sirve para denegar el acceso ni para revertir la autorización de forma segura. Mantenga una política restrictiva mientras elimina el servicio y compruebe los controles restantes de red y servicio.

## Enrutamiento y gestión del tráfico {#routing-and-traffic-management}

### Coincidencia de ruta y encabezado

La ruta anterior coincide con `/api` y con las rutas incluidas en su subárbol. Para añadir una regla explícita de canario basada en encabezados, sustituya la **misma** HTTPRoute por:

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

El controlador admite, según su documentación, coincidencias de ruta que no distinguen mayúsculas de minúsculas, una coincidencia de método por regla y hasta cinco coincidencias de encabezado; no admite coincidencias de parámetros de consulta. No dé por hecho que implementa todos los filtros y tipos de coincidencia de Gateway API. Una HTTPRoute independiente crea otro servicio y dominio de Lattice; no añade automáticamente una regla al primer servicio.

### Enrutamiento ponderado

`backendRefs.weight: 90` y `10` son parámetros nativos de Gateway API; no hace falta una anotación de enrutamiento ponderado. Indican una proporción relativa, no un resultado exacto para cada grupo de diez solicitudes. Antes de aumentar el peso del canario, compruebe los endpoints, el estado, los errores y la latencia de ambas versiones con una muestra adecuada.

Para recursos AWS administrados independientemente:

```bash
# TG_STABLE and TG_CANARY are existing target groups managed by this API workflow.
aws vpc-lattice create-rule --service-identifier "$SERVICE_ID" \
  --listener-identifier "$LISTENER_ID" --name api-canary --priority 10 \
  --match '{"httpMatch":{"pathMatch":{"match":{"prefix":"/api"},"caseSensitive":false}}}' \
  --action "{\"forward\":{\"targetGroups\":[{\"targetGroupIdentifier\":\"${TG_STABLE}\",\"weight\":90},{\"targetGroupIdentifier\":\"${TG_CANARY}\",\"weight\":10}]}}"
```

La coincidencia de prefijo de la CLI comprueba el inicio literal de la ruta; analice por separado sus límites y la semántica `PathPrefix` de Kubernetes. Las reglas de enrutamiento no son un límite de autorización. Una prueba de enrutamiento por ruta no demuestra que la política IAM cubra todas las variantes normalizadas o codificadas de esa ruta.

### Comprobaciones de estado

El ejemplo de Kubernetes usa `TargetGroupPolicy`. La actualización de API equivalente es:

```bash
aws vpc-lattice update-target-group --target-group-identifier "$TARGET_GROUP_ID" \
  --health-check '{"enabled":true,"protocol":"HTTP","protocolVersion":"HTTP1","port":8080,"path":"/health","healthCheckIntervalSeconds":30,"healthCheckTimeoutSeconds":5,"healthyThresholdCount":2,"unhealthyThresholdCount":2,"matcher":{"httpCode":"200"}}'
```

Las comprobaciones de estado evalúan la disponibilidad según umbrales, pero no garantizan disponibilidad ni tiempo de inactividad cero. Los grupos de destinos HTTP/1 las habilitan de forma predeterminada; en HTTP/2 hay que evaluarlas expresamente. Los destinos gRPC usan comprobaciones HTTP/1 o HTTP/2, mientras que los destinos Lambda y ALB tienen otros comportamientos. Consulte la documentación vigente para cada tipo de destino; no aplique el ejemplo de Pod a todos ellos.

## Seguridad y autenticación {#security-and-authentication}

### Políticas de autenticación y permisos de llamador

`put-auth-policy` y `get-auth-policy` gestionan la autorización de invocación. `put-resource-policy` pertenece a otra API, destinada a la gestión y el uso compartido de recursos. Para autorizar a los llamadores, use la acción **`vpc-lattice-svcs:Invoke`**.

Cuando tanto la red como el servicio usan `AWS_IAM`, la política de identidad del llamador y **ambas** políticas de autenticación aplicables deben permitir el acceso. Un Deny explícito prevalece. `NONE` en un recurso no cancela el requisito IAM de otro recurso. El tráfico directo a una ClusterIP/IP de Pod de Kubernetes omite la autenticación de Lattice; proteja esas rutas con controles de red y aplicación apropiados.

`StringEquals` no interpreta `/api/*` como un comodín. El ejemplo usa `StringLike` e incluye `/api` además de `/api/*`. La coincidencia de condiciones IAM y la normalización de rutas de la aplicación pueden diferir del enrutamiento del controlador. Para funciones administrativas, prefiera un servicio dedicado, restringido a roles administrativos, y mantenga la autorización de la aplicación; no añada un permiso general `Allow` de gran alcance suponiendo que un comodín de ruta protege todas las variantes.

### Acceso entre cuentas

El uso compartido mediante RAM permite asociarse a la entidad compartida, pero no autoriza por sí mismo las llamadas a la aplicación. La solicitud también debe estar permitida por las políticas de autenticación de red y servicio, los permisos del llamador, los grupos de seguridad de la asociación y la ruta de red.

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

Cuando se habilita el uso compartido mediante Organizations, los consumidores de la organización obtienen acceso sin invitación. Otros mecanismos de uso compartido admitidos requieren aceptar una invitación. Para compartir con una organización o una unidad organizativa (OU), use el **ARN real de Organizations**, incluido el ID de la cuenta de administración; no lo construya a partir del ID de una cuenta miembro.

Los propietarios pueden compartir servicios, redes y configuraciones de recursos, pero no añadir roles IAM individuales como consumidores de RAM. Detener el uso compartido impide nuevas asociaciones, pero **no elimina las asociaciones existentes**. Al revocar el acceso, revíselas y elimínelas expresamente.

### TLS y dominios personalizados

El Gateway de ejemplo solo expone HTTPS. Para usar un nombre de host personalizado, cree el servicio con ese nombre, obtenga un certificado ACM que coincida y configure DNS para resolverlo al dominio asignado por Lattice. Cada servicio admite un solo dominio personalizado, que no puede cambiarse después de crear el servicio.

En el controlador, configure `spec.hostnames` de HTTPRoute y `tls.options["application-networking.k8s.aws/certificate-arn"]` del listener de Gateway, o use el mecanismo documentado de descubrimiento de ACM. No incluya claves privadas en una anotación. ExternalDNS requiere además su propio controlador, permisos y el CRD DNSEndpoint; configurar un nombre de host no demuestra que ya existan registros DNS.

```bash
# For an API-managed service created with the required custom domain name:
aws vpc-lattice update-service --service-identifier "$SERVICE_ID" \
  --certificate-arn "$ACM_CERTIFICATE_ARN"
# Create an HTTPS listener separately if the service does not already have one.
# create-listener uses --protocol HTTPS; there is no --tls mode=STRICT option.
```

El HTTPS del cliente y el TLS del backend son independientes. Una `TargetGroupPolicy` con `protocol: HTTPS` requiere que el backend realmente use TLS y que la comprobación de estado también sea compatible con HTTPS. VPC Lattice **no valida los certificados del backend**: cifra la conexión, pero no autentica la identidad del certificado. Si ese es el diseño previsto, use el modelo independiente de TLSRoute con paso directo de TLS y revise sus limitaciones.

## Monitorización y registro {#monitoring-and-logging}

### Métricas de CloudWatch, panel y alarma

Las métricas del servicio usan el espacio de nombres **`AWS/VpcLattice`**:

| Métrica | Significado / estadístico |
|---|---|
| `TotalRequestCount` | Recuento de solicitudes; `Sum` |
| `HTTPCode_4XX_Count` | Respuestas 4xx; `Sum` |
| `HTTPCode_5XX_Count` | Respuestas 5xx; `Sum` |
| `RequestTime` | Duración de solicitud en **milisegundos**; promedio o un percentil adecuado |

Las métricas del servicio usan la dimensión `Service`, opcionalmente junto con `AvailabilityZone`; las de los grupos de destinos usan `TargetGroup`. Un nombre como `ServiceName=my-service` no identifica estas métricas. Consulte los valores y las combinaciones de dimensiones reales:

```bash
aws cloudwatch list-metrics --namespace AWS/VpcLattice \
  --metric-name HTTPCode_5XX_Count --dimensions Name=Service > metrics.json
python3 - <<'PY'
import json
for metric in json.load(open("metrics.json"))["Metrics"]:
    print(json.dumps(metric["Dimensions"]))
PY
```

Cuando ya haya tráfico y se hayan publicado métricas, seleccione el conjunto de dimensiones **de ámbito de servicio** que corresponda y guárdelo como `service-dimensions.json`. No elija el primer resultado sin comprobarlo ni mezcle una métrica de zona de disponibilidad con una agregada. Confirme que el identificador corresponde al servicio observado. Cree `dashboard.json` con:

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

La alarma indica **más de cinco respuestas 5xx por minuto en dos de tres períodos**; no representa una tasa de error del 5 %. Si necesita notificaciones, configure y revise por separado las acciones de alarma. La política para cuando faltan datos se especifica expresamente: las métricas se publican cuando comienza el tráfico, y `NoData` no debe interpretarse como prueba de buen estado. El panel y la alarma son ejemplos, no SLO definidos para una carga de trabajo concreta.

### Registros de acceso

Para CloudWatch Logs, use un destino existente o cree un grupo de registros dedicado con una política de retención:

```bash
export LOG_GROUP=/aws/vendedlogs/vpc-lattice/api
aws logs create-log-group --log-group-name "$LOG_GROUP"
aws logs put-retention-policy --log-group-name "$LOG_GROUP" --retention-in-days 30
export LOG_DESTINATION_ARN="arn:aws:logs:${AWS_REGION}:${AWS_ACCOUNT_ID}:log-group:${LOG_GROUP}:*"

# API-managed service only; for an HTTPRoute use AccessLogPolicy below instead.
aws vpc-lattice create-access-log-subscription \
  --resource-identifier "$SERVICE_ID" --destination-arn "$LOG_DESTINATION_ARN"
```

La identidad que realiza la configuración también necesita los permisos documentados para entregar registros. AWS puede crear o actualizar la política de recursos de CloudWatch Logs si esa identidad tiene los permisos necesarios; de lo contrario, configúrela de antemano. Compruebe los permisos de `delivery.logs.amazonaws.com` y las condiciones de cuenta y ARN de origen.

Para la ruta gestionada por Kubernetes, use esta opción **en lugar de** crear con la CLI una suscripción de registros que compita con ella:

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

Sustituya el ARN y compruebe tanto el estado de la política como la entrega efectiva de eventos. La política puede aplicarse a un Gateway para los registros de red o a una Route para los registros del servicio. Cada recurso de destino admite un destino por cada tipo compatible.

Para S3, use un bucket de destino cuya configuración se haya revisado: Block Public Access, cifrado, reglas de retención y ciclo de vida, y permisos de entrega adecuados:

```bash
# Existing reviewed destination bucket; no policy is overwritten by this snippet.
aws vpc-lattice create-access-log-subscription \
  --resource-identifier "$SERVICE_ID" --destination-arn "$LOG_BUCKET_ARN"
```

La entrega a S3 requiere los permisos documentados `s3:GetBucketAcl` y `s3:PutObject` para `delivery.logs.amazonaws.com`, el prefijo de entrega y las condiciones `aws:SourceAccount` y `aws:SourceArn`. Las políticas existentes deben combinarse, no sobrescribirse. SSE-KMS requiere una clave administrada por el cliente compatible y su política de clave de entrega. `--destination-name` no es un parámetro de access-log-subscription.

### Análisis de logs y trazas

Los registros de acceso de los servicios HTTP incluyen campos como `sourceIpPort`, `requestMethod`, `requestPath`, `responseCode`, `durationMS`, `callerPrincipal` y `authDeniedReason`. Los registros de recursos y de TCP usan otro esquema.

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

VPC Lattice no ofrece la opción `update-service --tracing-config` ni una anotación del controlador que instrumente automáticamente las aplicaciones para X-Ray. Instrumente las aplicaciones con OpenTelemetry/ADOT o con el SDK de trazas apropiado; propague el contexto de traza y configure la exportación y el muestreo. Correlacione las trazas de la aplicación con los registros de acceso y los ID de solicitud. Un ID de solicitud proporcionado por el cliente no constituye una identidad autenticada.

## Prácticas recomendadas {#best-practices}

- **Diseño y propiedad:** Use nombres claros de red y servicio, y defina límites entre entornos. Tenga en cuenta que puede haber Gateways con el mismo nombre en distintos espacios de nombres, además de consumidores de una red compartida, cuotas y responsables de cada política y asociación.
- **Despliegue:** Mantenga los backends estable y de canario seleccionables por separado. Compruebe los endpoints, el estado de los destinos y la autorización antes de cambiar los pesos. Registre los criterios de reversión y conserve la última configuración conocida.
- **Rendimiento:** Use tiempos de espera acotados y reutilice las conexiones cuando corresponda. Mantenga ligeros y útiles los endpoints de comprobación de estado. Use caché o procesamiento por lotes solo cuando la semántica de la aplicación lo permita. Habilitar la caché no convierte los servicios privados de Lattice en orígenes de CDN.
- **Seguridad:** Separe los roles de administración y de llamador; no incluya credenciales en los manifiestos. Pruebe los roles autorizados y denegados, las rutas raíz y sus subrutas, el acceso directo al backend y el comportamiento de TLS. No elimine un CRD de política IAM para denegar el tráfico.
- **Observabilidad:** Supervise por separado el número de solicitudes, el número y la tasa de errores, la latencia, el estado de los destinos y la falta de telemetría. Conserve los registros de acceso durante el período requerido e instrumente expresamente las trazas de la aplicación.
- **Coste:** Revise los cargos regionales vigentes por servicios y recursos, solicitudes, procesamiento de datos, endpoints y registros para el modelo elegido. Use etiquetas, elimine únicamente recursos que haya confirmado que no se usan y dimensione el autoescalado del backend por separado del plano de datos gestionado por Lattice.

## Solución de problemas {#troubleshooting}

Use los identificadores de las anotaciones y del estado del controlador, junto con el inventario de AWS. No suponga que `$SERVICE_ID` del ejemplo de API directa identifica el servicio de la ruta de Kubernetes.

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

| Síntoma | Comprobar |
|---|---|
| Error de DNS o conectividad | Nombre DNS realmente asignado, asociación de VPC del cliente o ruta del endpoint, estado de la asociación, grupos de seguridad, NACL y conectividad con los Pods |
| Error 403 o de autenticación | Rol del llamador, expiración de las credenciales, región y servicio de firma, `UNSIGNED-PAYLOAD`, ambas capas de autenticación, propagación y campos de registro con el motivo de denegación |
| Ruta o versión incorrecta | Condiciones de la ruta, prioridad y coincidencias del listener y sus reglas, pertenencia al grupo de destinos, pesos y dominios distintos de cada Route |
| Destinos no saludables | Puerto en el que realmente escucha el servicio, `/health`, HTTP o HTTPS, disponibilidad, grupos de seguridad, tipo de destino y umbrales de comprobación de estado |
| No aparecen registros o métricas | Permisos del destino y estado de entrega, dimensiones correctas de las métricas, tráfico inicial, retención y estado de la consulta |
| Error de reconciliación del controlador | Registros de `manager`, rol IAM, EndpointSlices, compatibilidad de las versiones de CRD, estado del webhook y elección de líder |

Use un intervalo de métricas acotado sin depender de `date -d` exclusivo de GNU:

```bash
export METRIC_END="$(python3 -c 'from datetime import datetime,timezone; print(datetime.now(timezone.utc).isoformat())')"
export METRIC_START="$(python3 -c 'from datetime import datetime,timedelta,timezone; print((datetime.now(timezone.utc)-timedelta(hours=1)).isoformat())')"
aws cloudwatch get-metric-statistics --namespace AWS/VpcLattice \
  --metric-name HTTPCode_5XX_Count --dimensions file://service-dimensions.json \
  --start-time "$METRIC_START" --end-time "$METRIC_END" \
  --period 60 --statistics Sum
```

Ante un incidente de un servicio de AWS, consulte AWS Health y los eventos pertinentes de la cuenta. El acceso a la API de la cuenta y las operaciones de soporte dependen del plan y de los endpoints aplicables. Incluya en el caso de soporte los ID de los recursos revisados, el intervalo de tiempo, los síntomas del fallo y registros con los datos sensibles ocultos. Seleccione las opciones vigentes de servicio, categoría y gravedad para la cuenta; no pegue un comando con la gravedad `urgent` fijada de antemano.

## Referencias {#references}

- [Descripción general de VPC Lattice](https://docs.aws.amazon.com/vpc-lattice/latest/ug/what-is-vpc-lattice.html)
- [Asociaciones de redes de servicios](https://docs.aws.amazon.com/vpc-lattice/latest/ug/service-network-associations.html)
- [Instalación de AWS Gateway API Controller v2.1.3](https://github.com/aws/aws-application-networking-k8s/blob/v2.1.3/docs/guides/deploy.md)
- [Requisitos de actualización del controlador v2.1](https://github.com/aws/aws-application-networking-k8s/blob/v2.1.3/docs/guides/upgrading-v2-0-x-to-v2-1-y.md)
- [Referencia de la API del controlador](https://github.com/aws/aws-application-networking-k8s/tree/v2.1.3/docs/api-types)
- [HTTPS del controlador y TLS de backend](https://github.com/aws/aws-application-networking-k8s/blob/v2.1.3/docs/guides/https.md)
- [Políticas de autenticación de VPC Lattice](https://docs.aws.amazon.com/vpc-lattice/latest/ug/auth-policies.html)
- [Firmar solicitudes](https://docs.aws.amazon.com/vpc-lattice/latest/ug/sigv4-authenticated-requests.html)
- [Compartir entidades](https://docs.aws.amazon.com/vpc-lattice/latest/ug/sharing.html)
- [Métricas de CloudWatch](https://docs.aws.amazon.com/vpc-lattice/latest/ug/monitoring-cloudwatch.html)
- [Logs de acceso](https://docs.aws.amazon.com/vpc-lattice/latest/ug/monitoring-access-logs.html)
- [Permisos de entrega de CloudWatch Logs](https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/AWS-logs-infrastructure-CWL.html)
- [Permisos de entrega de S3](https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/AWS-logs-infrastructure-S3.html)

## Cuestionario

Compruebe sus conocimientos con el [cuestionario de VPC Lattice](../quizzes/networking/02-vpc-lattice-quiz.md).
