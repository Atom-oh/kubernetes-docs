# Cuestionario de VPC Lattice

Revisa la guía y explica los requisitos previos, no solo el YAML.

## 1. ¿Cuál es el propósito principal de Amazon VPC Lattice?

- A) Balanceo de carga global basado en DNS de Internet
- B) Conectividad privada de aplicaciones y recursos entre VPC y cuentas
- C) Replicación de bases de datos entre regiones
- D) Reemplazar todo el enrutamiento IP

<details>
<summary>Mostrar respuesta</summary>

B. Lattice conecta servicios y configuraciones de recursos. El enrutamiento de servicios HTTP y el modelo de acceso a recursos son distintos; la asociación, los controles de red y la autorización siguen aplicándose.

</details>

## 2. ¿Qué representa una service network?

- A) Un dispositivo físico de red
- B) Una agrupación lógica con asociaciones de servicio/recurso y de red de clientes
- C) Una tabla de rutas de subred
- D) Un listener HTTP compartido para cada servicio

<details>
<summary>Mostrar respuesta</summary>

B. Los listeners y las reglas pertenecen a servicios individuales. Una asociación habilita una ruta sujeta a security groups y políticas aplicables; no autoriza incondicionalmente cada solicitud.

</details>

## 3. ¿Qué afirmación sobre App Mesh y Lattice es correcta?

- A) Lattice requiere un sidecar Envoy por Pod
- B) App Mesh usa proxies Envoy, mientras que Lattice proporciona un plano de datos administrado sin requerir sidecars de aplicación
- C) Todas las demás mallas requieren sidecars
- D) App Mesh sigue disponible para nuevas implementaciones

<details>
<summary>Mostrar respuesta</summary>

B. App Mesh usaba proxies sidecar Envoy, mientras que Lattice proporciona un plano de datos administrado sin sidecars de aplicación. D es falsa: el soporte de AWS App Mesh terminó el 2026-09-30, y su consola y recursos ya no son accesibles, así que migra las implementaciones existentes en lugar de crear una nueva. Los requisitos de sidecar difieren entre otros modos de malla.

</details>

## 4. ¿Cómo asigna recursos AWS Gateway API Controller?

- A) Cada Service de Kubernetes crea una service network
- B) Gateway selecciona una red por nombre; cada HTTPRoute crea su propio servicio/dominio Lattice
- C) Gateway siempre crea una IP de ingreso compartida por todas las Routes
- D) El controlador usa únicamente la API Ingress

<details>
<summary>Mostrar respuesta</summary>

B. GatewayClass selecciona el controlador. Un Gateway se refiere a una service network existente por su nombre sin el namespace; los Services/endpoints de backend proporcionan target groups. Un Gateway por sí solo no crea la red.

</details>

## 5. ¿Cómo debería obtener un cliente el nombre DNS de servicio Lattice asignado?

- A) Añadir la región al nombre de Service de Kubernetes
- B) Colocar el ID de la service network en un hostname adivinado
- C) Leer get-service dnsEntry o la anotación lattice-assigned-domain-name de la Route
- D) Reutilizar Gateway.status.addresses como la dirección de cada Route

<details>
<summary>Mostrar respuesta</summary>

C. Cada Route tiene su propio servicio/dominio. Usa el valor devuelto real; recrear un servicio puede cambiar su nombre asignado. Los dominios personalizados requieren su propia configuración de DNS y certificados.

</details>

## 6. ¿Qué afirmación sobre autenticación es correcta?

- A) NONE en el servicio deshabilita cada política de red
- B) AWS_IAM acepta una solicitud curl sin firmar si el cliente tiene un rol IAM
- C) AWS_IAM usa solicitudes firmadas compatibles; cada capa de autorización IAM aplicable debe permitir el acceso
- D) Compartir mediante RAM otorga Invoke automáticamente

<details>
<summary>Mostrar respuesta</summary>

C. VPC Lattice admite SigV4 y SigV4A. Usa vpc-lattice-svcs y UNSIGNED-PAYLOAD al firmar. Los permisos de identidad del llamador y las políticas de autenticación de red/servicio aplicables deben permitir el acceso; un Deny explícito prevalece. NONE solo afecta a su propia capa.

</details>

## 7. ¿Cuál no corresponde a uno de los tipos de grupo de destino de un servicio Lattice?

- A) INSTANCE
- B) IP
- C) LAMBDA
- D) RDS

<details>
<summary>Mostrar respuesta</summary>

D. Los tipos de grupo de destino de servicios incluyen INSTANCE, IP, LAMBDA y ALB. Esto no significa que Lattice no pueda conectar una base de datos RDS: las configuraciones de recursos y los resource gateways proporcionan un modelo separado de acceso a recursos TCP. Las políticas de autenticación de servicio no rigen ese tráfico de recursos.

</details>

## 8. ¿Qué significa una proporción de peso backendRefs de 90:10?

- A) Exactamente una de cada diez solicitudes consecutivas llega a canary
- B) Distribución relativa de tráfico entre los dos backends
- C) Un requisito de cantidad de réplicas de Pod
- D) Una anotación no compatible con Gateway API

<details>
<summary>Mostrar respuesta</summary>

B. La propiedad nativa backendRefs.weight configura una distribución relativa; una muestra pequeña de solicitudes no tiene por qué coincidir exactamente. Ambos backends deben existir y estar en buen estado. Observa errores y latencia antes de aumentar la proporción de canary.

</details>

## 9. Explica el uso compartido entre cuentas de una service network.

<details>
<summary>Mostrar respuesta</summary>

El propietario crea un recurso compartido de RAM para el ARN de la red y una cuenta, organización u OU prevista. Los consumidores dentro de una organización con el uso compartido habilitado no necesitan invitaciones; otros acuerdos aplicables requieren aceptación. El consumidor asocia su propia VPC o crea un service-network endpoint adecuado. El uso compartido no otorga Invoke: las políticas del llamador, las políticas de autenticación, las rutas de red y los security groups también deben permitir el acceso. Detener un recurso compartido deja las asociaciones existentes en su lugar.

</details>

## 10. Escribe una política de comprobación de estado de Kubernetes para el backend de demostración.

<details>
<summary>Mostrar respuesta</summary>

Usa TargetGroupPolicy en el mismo namespace que su Service objetivo. El CRD del controlador usa intervalSeconds/timeoutSeconds/statusMatch, mientras que la API de AWS usa healthCheckIntervalSeconds/healthCheckTimeoutSeconds/matcher.

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

El backend realmente debe escuchar en 8080 y devolver 200 en /health. Los umbrales ayudan a determinar la preparación; no garantizan disponibilidad ni cero tiempo de inactividad. Revisa el comportamiento según el tipo de destino y el protocolo.

</details>

## 11. ¿En qué se diferencian Transit Gateway y VPC Lattice?

<details>
<summary>Mostrar respuesta</summary>

Transit Gateway enruta tráfico IP entre redes. Lattice expone servicios y configuraciones de recursos: las rutas de servicio HTTP pueden usar enrutamiento L7, mientras que las capacidades de TLS/TCP/recursos tienen características diferentes. Se pueden usar juntos. Un endpoint VPC de service network admite clientes aplicables que llegan mediante tránsito/peering; una asociación VPC directa por sí sola no otorga ese acceso de tránsito.

</details>

## 12. ¿En qué niveles puede aplicarse una política de autenticación y cómo restringes la ruta de la API de demostración?

<details>
<summary>Mostrar respuesta</summary>

Las políticas de autenticación se aplican a service networks y servicios individuales configurados con AWS_IAM. Ambas capas aplicables y la política de identidad del llamador deben permitir la solicitud. Usa StringLike para la coincidencia con comodines e incluye explícitamente la ruta raíz:

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

StringEquals coincidiría literalmente con /api/*. Esta política se refiere a rutas canónicas; la normalización de la aplicación y el enrutamiento de rutas del controlador son comportamientos independientes. PutAuthPolicy, no PutResourcePolicy, gestiona la autorización de invocación.

</details>

## 13. Describe una instalación IRSA de AWS Gateway API Controller v2.1.3.

<details>
<summary>Mostrar respuesta</summary>

Verifica la versión de Kubernetes compatible con el clúster, la compatibilidad con Gateway API, el proveedor IAM OIDC y la conectividad de red/webhook. Revisa la política recomendada de la versión para la cuenta y las características previstas; sus amplios permisos upstream no son una garantía de privilegio mínimo. Usa una cuenta de servicio dedicada para el controlador y el chart OCI publicado:

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

El rol del controlador administra recursos; no es el rol del llamador de la aplicación. Las cuentas de servicio y las versiones existentes requieren una actualización que tenga en cuenta quién las administra. Helm no actualiza automáticamente sus CRD. Consulta la guía para la configuración independiente de service network/política de autenticación.

</details>

## 14. Escribe una HTTPRoute para una división stable/canary de 90:10.

<details>
<summary>Mostrar respuesta</summary>

Requisitos previos: el Gateway HTTPS my-network de la guía en lattice-demo, su service network existente y su política de autenticación activa, ambas implementaciones y ambos Services de backend en el puerto 8080 y las políticas de comprobación de estado de los grupos de destino. Luego aplica:

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

Aplica también IAMAuthPolicy de la guía a esta Route e inspecciona la reconciliación. No se necesita ninguna anotación de peso. Usa el dominio asignado de la Route y solicitudes HTTPS firmadas; que el comando `kubectl apply` termine correctamente no demuestra que los backends estén en buen estado.

</details>

## 15. Permite que solo AdminRole y DevOpsRole invoquen un servicio administrativo dedicado en /admin y sus subrutas.

<details>
<summary>Mostrar respuesta</summary>

Usa lo siguiente como la política de autenticación de servicio completa, con ARN reales de cuenta/rol. Configura ese servicio dedicado en AWS_IAM y asegúrate de que la política de identidad del llamador y la política de autenticación de red también permitan estos roles y rutas. La política de red exclusiva para API de la guía necesitaría un cambio revisado para este servicio administrativo independiente.

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "AWS": [
          "arn:aws:iam::123456789012:role/AdminRole",
          "arn:aws:iam::123456789012:role/DevOpsRole"
        ]
      },
      "Action": "vpc-lattice-svcs:Invoke",
      "Resource": "*",
      "Condition": {
        "StringLike": {
          "vpc-lattice-svcs:RequestPath": [
            "/admin",
            "/admin/*"
          ]
        }
      }
    }
  ]
}
```

Para una HTTPRoute administrada por el controlador llamada admin en lattice-demo, adjúntala mediante el CRD real:

```yaml
apiVersion: application-networking.k8s.aws/v1alpha1
kind: IAMAuthPolicy
metadata:
  name: admin-caller
  namespace: lattice-demo
spec:
  targetRef:
    group: gateway.networking.k8s.io
    kind: HTTPRoute
    name: admin
  policy: '{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"AWS":["arn:aws:iam::123456789012:role/AdminRole","arn:aws:iam::123456789012:role/DevOpsRole"]},"Action":"vpc-lattice-svcs:Invoke","Resource":"*","Condition":{"StringLike":{"vpc-lattice-svcs:RequestPath":["/admin","/admin/*"]}}}]}'
```

No hay una declaración amplia AllowGeneralAccess. En esta política, los demás roles y rutas no tienen Allow, y /admin se incluye explícitamente en lugar de solo /admin/*. Trata la normalización/codificación de rutas como un requisito de seguridad de la aplicación; un servicio dedicado restringido por rol y la autorización de la aplicación reducen la dependencia de alias de rutas. El acceso directo al backend también debe protegerse. Eliminar IAMAuthPolicy cambia el tipo de autenticación de destino a NONE y no es un mecanismo de denegación ni de reversión segura.

</details>

Puntuación: 13–15 indica una sólida comprensión de este capítulo, 10–12 sugiere revisar los temas no acertados, y 0–9 sugiere releer la guía. La puntuación de un cuestionario no acredita experiencia operativa en producción.

[Volver a la guía](../../networking/02-vpc-lattice.md)
