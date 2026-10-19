# Cuestionario de creación de clústeres de EKS - Parte 2

> **Última actualización**: 11 de septiembre de 2026

> Los ejemplos de las preguntas son alternativas independientes. Usa los requisitos previos de la Parte 1 y selecciona explícitamente una cuenta/clúster de formación. Dentro de cada ejercicio, ejecuta los pasos en orden y en la misma sesión de Bash. Los comandos de nube/host que aparecen a continuación se revisaron, pero no se ejecutaron en AWS ni en nodos durante esta auditoría.

Este cuestionario evalúa tus conocimientos sobre conceptos avanzados, ajustes de seguridad y configuraciones de red relacionados con la creación de clústeres de Amazon EKS. Trata temas como la seguridad del clúster, las políticas de red y las cuentas de servicio.

## Preguntas de conceptos básicos

1. ¿Cuál es el propósito principal de IRSA en un clúster de EKS?
   * A) Conceder acceso de administrador de Kubernetes
   * B) Asignar el rol de IAM del nodo EC2
   * C) Conceder permisos temporales de AWS a las cargas de trabajo mediante su cuenta de servicio de Kubernetes
   * D) Modificar el rol del plano de control de EKS

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Conceder permisos temporales de AWS a las cargas de trabajo mediante su cuenta de servicio de Kubernetes**

IRSA permite que una carga de trabajo obtenga credenciales temporales de AWS mediante la identidad de su cuenta de servicio de Kubernetes. La política de permisos del rol de IAM determina qué operaciones de AWS puede realizar. Esto es independiente de RBAC de Kubernetes y de los roles de IAM usados por el plano de control de EKS o los nodos EC2.

**Flujo de confianza:** EKS emite un token proyectado de cuenta de servicio. Registra como proveedor OIDC de IAM el emisor OIDC real del clúster y, después, establece la confianza para la audiencia y el sujeto namespace/cuenta de servicio previstos. La cadena de credenciales predeterminada de un SDK de AWS compatible intercambia ese token mediante STS `AssumeRoleWithWebIdentity`. En este ejemplo usa el ARN/proveedor y emisor reales, así como la identidad exacta de la cuenta de servicio:

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {
      "Federated": "arn:aws:iam::123456789012:oidc-provider/oidc.eks.us-west-2.amazonaws.com/id/EXAMPLE"
    },
    "Action": "sts:AssumeRoleWithWebIdentity",
    "Condition": {
      "StringEquals": {
        "oidc.eks.us-west-2.amazonaws.com/id/EXAMPLE:aud": "sts.amazonaws.com",
        "oidc.eks.us-west-2.amazonaws.com/id/EXAMPLE:sub": "system:serviceaccount:irsa-lab:my-service-account"
      }
    }
  }]
}
```

Anota la cuenta de servicio con el ARN del rol y haz que el Pod la use. Primero crea un namespace `irsa-lab` que no esté en uso. Estos dos manifiestos son una alternativa a la creación de cuentas de servicio administrada por eksctl que aparece más abajo; no sobrescribas la cuenta de servicio de otra aplicación:

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: my-service-account
  namespace: irsa-lab
  annotations:
    eks.amazonaws.com/role-arn: arn:aws:iam::123456789012:role/ReviewedIrsaRole
```

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: irsa-identity-check
  namespace: irsa-lab
spec:
  serviceAccountName: my-service-account
  restartPolicy: Never
  containers:
    - name: aws-cli
      image: public.ecr.aws/aws-cli/aws-cli:2.36.43
      command: ["aws"]
      args: ["sts", "get-caller-identity"]
```

El Pod usa una etiqueta verificada de imagen de AWS CLI v2 e imprime la identidad del llamador, no claves de acceso secretas ni el token de identidad web. Confirma que el rol devuelto sea el rol de carga de trabajo previsto. Que la identidad STS se resuelva correctamente no demuestra acceso a S3 ni a otro recurso de destino; prueba por separado la operación requerida, como en el ejercicio 1.

**Alternativa con eksctl:** limita la política a los recursos/acciones previstos; no uses una política amplia de S3 administrada por AWS para una tarea limitada a un único bucket. Revisa primero las cuentas de servicio y la titularidad de los roles existentes; no agregues `--override-existingserviceaccounts` como solución genérica.

```bash
# For a new service account and dedicated role, with a reviewed scoped policy.
eksctl utils associate-iam-oidc-provider \
  --cluster "${EXAMPLE_CLUSTER:?}" --region "${EXAMPLE_REGION:?}" --approve
KUBECONFIG="${EXAMPLE_KUBECONFIG:?}" eksctl create iamserviceaccount \
  --name "${IRSA_SERVICE_ACCOUNT:?}" --namespace "${IRSA_NAMESPACE:?}" \
  --cluster "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION" \
  --attach-policy-arn "${SCOPED_POLICY_ARN:?}" --approve
kubectl --kubeconfig "$EXAMPLE_KUBECONFIG" -n "$IRSA_NAMESPACE" \
  get serviceaccount "$IRSA_SERVICE_ACCOUNT" -o yaml
```

**Límites y responsabilidades:**

- Usa un SDK compatible y su cadena de credenciales. Las credenciales codificadas en el programa o proveedores anteriores en la cadena pueden prevalecer sobre IRSA. El webhook inyecta la configuración del rol/archivo de token y el SDK renueva las credenciales temporales. No imprimas ni copies valores de tokens o credenciales.
- IRSA por sí solo no bloquea el acceso a IMDS del nodo, y los contenedores que comparten nodo no forman una frontera de seguridad estricta. Restringe IMDS y los permisos del nodo por separado; los Pods con `hostNetwork` aún pueden llegar a IMDS.
- Las condiciones de IAM limitan la asunción del rol, pero cualquier persona autorizada a crear un Pod que use esa cuenta de servicio podría obtener sus permisos de AWS. Controla también la administración de cargas de trabajo/cuentas de servicio de Kubernetes.
- EKS Pod Identity es otra opción de identidad de carga de trabajo y tiene sus propios requisitos de compatibilidad. Su flujo de credenciales mediante EKS Auth/agente es distinto del flujo OIDC/STS de IRSA.
- Los usuarios del clúster usan entradas/políticas de acceso de EKS o, cuando esté configurado, el mapeo heredado `aws-auth`. Estos mecanismos autorizan el acceso a Kubernetes; no sustituyen las políticas de permisos de IAM de las cargas de trabajo.

Referencias: [IRSA](https://docs.aws.amazon.com/eks/latest/userguide/iam-roles-for-service-accounts.html), [asignación de un rol a una cuenta de servicio](https://docs.aws.amazon.com/eks/latest/userguide/associate-service-account-role.html), [requisitos del SDK](https://docs.aws.amazon.com/eks/latest/userguide/iam-roles-for-service-accounts-minimum-sdk.html), [Pod Identity](https://docs.aws.amazon.com/eks/latest/userguide/pod-identities.html).

</details>

2. ¿Qué controlan los grupos de seguridad de AWS en un diseño de EKS?
   * A) La autorización de recursos de Kubernetes
   * B) El tráfico de red permitido en las interfaces asociadas, incluidas las interfaces compatibles de Pods
   * C) Las audiencias de los tokens de cuentas de servicio
   * D) La cantidad de réplicas de un Deployment

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) El tráfico de red permitido en las interfaces asociadas, incluidas las interfaces compatibles de Pods**

Los grupos de seguridad son filtros de red con estado asociados a interfaces de red. En EKS ayudan a controlar el tráfico entre interfaces del clúster y nodos y, con la función compatible Security Groups for Pods, de determinados Pods. No implementan RBAC de Kubernetes ni autentican usuarios.

**Las reglas predeterminadas y las necesarias son distintas.** EKS crea `eks-cluster-sg-<cluster>-<id>` con reglas de entrada autorreferenciadas, acceso de salida amplio y una regla de salida autorreferenciada usada por EFA. Son valores predeterminados que debes inspeccionar, no una receta de privilegio mínimo. EKS asocia el grupo del clúster a sus interfaces y normalmente a las interfaces de nodos administrados; los grupos de seguridad personalizados en una plantilla de lanzamiento cambian ese comportamiento.

Si restringes las reglas de salida predeterminadas, conserva el tráfico mínimo documentado y las dependencias adicionales de tus cargas de trabajo reales:

| Tráfico de salida necesario del grupo del clúster | Destino |
| --- | --- |
| TCP 443 | Grupo de seguridad del clúster |
| TCP 10250 | Grupo de seguridad del clúster |
| TCP y UDP 53 | Grupo de seguridad del clúster |

Esta tabla no es por sí sola un diseño de red completo. Revisa los puertos entre nodos y de aplicaciones, el acceso a la API y a registros, S3, las rutas DNS y las reglas IPv4/IPv6. Los endpoints privados pueden proporcionar conectividad con AWS sin salida general a Internet. EKS puede volver a crear reglas autorreferenciadas durante las actualizaciones del clúster; por eso, no describas su eliminación como una restricción permanente.

**Grupos adicionales:** los grupos indicados en `resourcesVpcConfig.securityGroupIds` del clúster se adjuntan a las interfaces de red del plano de control; no se adjuntan automáticamente a los grupos de nodos. Si la plantilla de lanzamiento de un nodo proporciona grupos de seguridad personalizados, EKS no agrega también el grupo del clúster y esos grupos personalizados deben permitir el tráfico necesario entre nodos y API.

El siguiente ejemplo de AWS CLI muestra cómo seleccionar un grupo adicional para un nuevo plano de control. No crea capacidad de nodos ni entradas de acceso para operadores. La identidad que aprovisiona el clúster necesita permiso para crear la entrada de acceso del operador porque el acceso de administrador automático del creador está desactivado:

```bash
# Cluster creation fragment: use reviewed roles/subnets/groups and a new name.
aws eks create-cluster --name "${NEW_CLUSTER_NAME:?}" \
  --region "${EXAMPLE_REGION:?}" --kubernetes-version 1.36 \
  --role-arn "${CLUSTER_ROLE_ARN:?}" \
  --access-config authenticationMode=API,bootstrapClusterCreatorAdminPermissions=false \
  --resources-vpc-config "subnetIds=${PRIVATE_SUBNET_A:?},${PRIVATE_SUBNET_B:?},securityGroupIds=${ADDITIONAL_CONTROL_PLANE_SG:?},endpointPrivateAccess=true,endpointPublicAccess=true,publicAccessCidrs=${APPROVED_API_CIDR:?}"
```

Los campos de red equivalentes de eksctl forman parte de la configuración completa revisada de la [Parte 2](../../eks/02-eks-cluster-creation-part2.md). Sustituye el CIDR de documentación y todos los ID:

```yaml
# Networking example; merge into a reviewed full ClusterConfig.
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: my-cluster
  region: us-west-2
  version: "1.36"
vpc:
  id: vpc-0123456789abcdef0
  controlPlaneSecurityGroupIDs:
    - sg-0123456789abcdef0
  clusterEndpoints:
    publicAccess: true
    privateAccess: true
  publicAccessCIDRs:
    - 203.0.113.10/32
  subnets:
    private:
      us-west-2a:
        id: subnet-0123456789abcdef0
      us-west-2b:
        id: subnet-0123456789abcdef1
```

**API pública y privada:** el endpoint público de Kubernetes se restringe con `publicAccessCidrs`, no mediante el grupo de seguridad del clúster. Las reglas del grupo de seguridad del clúster rigen el tráfico del endpoint privado. Ni una lista de CIDR permitidos ni una regla de grupo de seguridad conceden autorización de IAM/RBAC.

**Grupos de seguridad para Pods:** en capacidad compatible, configura la función y los ajustes necesarios de IAM/VPC CNI antes de crear una `SecurityGroupPolicy`. Comprueba la compatibilidad de trunking de instancias, la versión de CNI, el modo de aplicación, DNS y las reglas reales del grupo de seguridad. Windows y EKS Auto Mode no admiten esta función; las familias de instancias EC2 `t` tampoco. Fargate tiene su propia configuración compatible.

```yaml
apiVersion: vpcresources.k8s.aws/v1beta1
kind: SecurityGroupPolicy
metadata:
  name: application-sg
  namespace: sg-lab
spec:
  podSelector:
    matchLabels:
      app: my-app
  securityGroups:
    groupIds:
      - sg-0123456789abcdef0
```

La política selecciona Pods de un namespace `sg-lab` creado aparte; la existencia de un objeto CRD no demuestra que se haya adjuntado el grupo de seguridad. Los modos estándar/estricto de los grupos de seguridad de Pods y SNAT influyen en qué grupo filtra el tráfico fuera de la VPC. Comprueba el comportamiento documentado para el modo de tu configuración.

Kubernetes NetworkPolicy es un mecanismo distinto, aplicado por un complemento de red configurado. El tráfico de Pods no se deniega de forma predeterminada solo porque el clúster admita NetworkPolicy. Consulta la pregunta 3 para ver una configuración intencional de políticas.

```bash
aws eks describe-cluster --name "${EXAMPLE_CLUSTER:?}" \
  --region "${EXAMPLE_REGION:?}" \
  --query 'cluster.resourcesVpcConfig.{clusterSG:clusterSecurityGroupId,additionalSGs:securityGroupIds,publicAccess:endpointPublicAccess,privateAccess:endpointPrivateAccess,cidrs:publicAccessCidrs}'
aws ec2 describe-security-groups --region "$EXAMPLE_REGION" \
  --group-ids "${REVIEWED_SECURITY_GROUP_ID:?}"
```

Referencias: [grupos de seguridad del clúster](https://docs.aws.amazon.com/eks/latest/userguide/sec-group-reqs.html), [acceso al endpoint de la API](https://docs.aws.amazon.com/eks/latest/userguide/cluster-endpoint.html), [grupos de seguridad para Pods](https://docs.aws.amazon.com/eks/latest/userguide/security-groups-for-pods.html).

</details>

3. ¿Qué se necesita para aplicar Kubernetes NetworkPolicy en EKS?
   * A) Solo una regla de grupo de seguridad
   * B) Una implementación de políticas compatible y habilitada, como Amazon VPC CNI, Calico o Cilium
   * C) Solo VPC Flow Logs
   * D) Un objeto NetworkPolicy sin implementación que lo aplique

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Una implementación de políticas compatible y habilitada, como Amazon VPC CNI, Calico o Cilium**

Se necesita una implementación de políticas de red configurada; crear solamente un objeto `NetworkPolicy` no hace que se apliquen las reglas de tráfico. **Amazon VPC CNI admite NetworkPolicy**, así que Calico o Cilium no son obligatorios para habilitar esta función.

**Opción Amazon VPC CNI:** comprueba que sean compatibles el clúster/plataforma, el kernel Linux y la versión de CNI; después habilita la función de políticas de red mediante la configuración que administra el complemento. La guía actual de AWS usa VPC CNI 1.21.0+ para políticas estándar y de administración, y Linux kernel 5.10+. Las versiones mínimas históricas anteriores no son objetivos de actualización para un clúster actual.

```bash
aws eks describe-addon --cluster-name "${EXAMPLE_CLUSTER:?}" \
  --region "${EXAMPLE_REGION:?}" --addon-name vpc-cni \
  --query 'addon.{version:addonVersion,status:status,configuration:configurationValues}'
aws eks describe-addon-configuration --region "$EXAMPLE_REGION" \
  --addon-name vpc-cni --addon-version "${REVIEWED_CNI_VERSION:?}" \
  --query configurationSchema --output text
kubectl --kubeconfig "${EXAMPLE_KUBECONFIG:?}" -n kube-system \
  get daemonset aws-node -o jsonpath='{.spec.template.spec.containers[*].name}{"\n"}'
```

Para el complemento administrado por EKS, el valor de configuración relevante es:

```json
{
  "enableNetworkPolicy": "true"
}
```

Combina esto con la **configuración completa revisada**, conservando los ajustes existentes necesarios; proporcionar un nuevo documento `configurationValues` no es un parche JSON. No degrades el complemento ni sobrescribas un DaemonSet administrado por EKS con un manifiesto upstream antiguo. Si usas una instalación de Helm/autoadministrada, sigue su configuración documentada.

En el modo de inicio estándar, un Pod nuevo puede permitir tráfico al principio, antes de que se programe su política. El modo estricto comienza con denegación predeterminada, pero requiere preparar todas las conexiones necesarias, incluidas las dependencias de CoreDNS. No cambies un clúster existente al modo estricto sin revisar antes sus requisitos.

**Implementaciones alternativas:**

- **Calico con redes de Amazon VPC:** conserva AWS IPAM/CNI y configura `Installation` del operador para `AmazonVPC`. Sigue las instrucciones de operador/CRD fijadas y los requisitos previos oficiales de EKS para la anotación de IP del Pod de AWS y RBAC. Desactiva la aplicación de políticas propia de AWS para esta vía Calico; instalar solo el operador o un manifiesto VXLAN arbitrario no equivale a este diseño.

```yaml
# Installation resource for the Amazon VPC networking path, after operator/CRDs.
apiVersion: operator.tigera.io/v1
kind: Installation
metadata:
  name: default
spec:
  kubernetesProvider: EKS
  cni:
    type: AmazonVPC
  calicoNetwork:
    bgp: Disabled
```

- **Cilium con Amazon VPC CNI:** se necesita la configuración documentada de encadenamiento; desactivar túneles/masquerading por sí solo no lo configura. Los siguientes valores son una referencia de la guía publicada 1.20.1. Comprueba la compatibilidad con la versión y el clúster y completa sus requisitos previos. Para aplicar la nueva ruta de encadenamiento, los Pods existentes deben recrearse mediante un despliegue controlado.

```yaml
# Relevant Helm values from the Cilium 1.20.1 AWS-CNI chaining guide.
# This is not a complete install or migration command.
cni:
  chainingMode: aws-cni
  exclusive: false
enableIPv4Masquerade: false
routingMode: native
```

Elige y valida la implementación prevista en lugar de apilar instalaciones de CNI/políticas no revisadas. Sustituir una implementación puede dejar reglas a nivel de nodo y requiere una migración planificada.

**Ejemplo de política:** en un namespace `policy-lab` recién creado, permite TCP 8080 desde frontend a backend y el tráfico DNS, y deniega el resto. El backend debe escuchar realmente en el puerto 8080. Para la implementación de AWS, usa el mismo Service y puerto de contenedor. Los selectores DNS siguientes presuponen Pods de CoreDNS convencionales en `kube-system`; NodeLocal DNSCache o un DNS personalizado requiere reglas revisadas distintas.

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny
  namespace: policy-lab
spec:
  podSelector: {}
  policyTypes: [Ingress, Egress]
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: backend-ingress
  namespace: policy-lab
spec:
  podSelector:
    matchLabels:
      app: backend
  policyTypes: [Ingress]
  ingress:
    - from:
        - podSelector:
            matchLabels:
              app: frontend
      ports:
        - protocol: TCP
          port: 8080
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: frontend-egress
  namespace: policy-lab
spec:
  podSelector:
    matchLabels:
      app: frontend
  policyTypes: [Egress]
  egress:
    - to:
        - podSelector:
            matchLabels:
              app: backend
      ports:
        - protocol: TCP
          port: 8080
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: dns-egress
  namespace: policy-lab
spec:
  podSelector: {}
  policyTypes: [Egress]
  egress:
    - to:
        - namespaceSelector:
            matchLabels:
              kubernetes.io/metadata.name: kube-system
          podSelector:
            matchLabels:
              k8s-app: kube-dns
      ports:
        - protocol: UDP
          port: 53
        - protocol: TCP
          port: 53
```

Se permite la salida de frontend y la entrada de backend porque ambos extremos quedan aislados de lo contrario. Varias NetworkPolicy estándar suman el tráfico permitido; el objeto de denegación predeterminada no anula una regla de autorización. Se permite DNS para el namespace de prueba, para que no se confunda una conexión de aplicación denegada con un fallo de DNS.

**Verificación significativa:** usa Pods frontend, backend y cliente no relacionado administrados por Deployments. AWS advierte que la aplicación puede ser poco fiable para Pods independientes sin `metadata.ownerReferences`; no uses un Pod creado únicamente con `kubectl run` como prueba. Comprueba la conectividad inicial, aplica las políticas y luego confirma que frontend funciona y el cliente no relacionado falla mientras DNS sigue funcionando. Prueba conexiones nuevas una vez convergidas las políticas. Encontrar Pods de CNI o aplicar YAML correctamente no basta.

La aplicación de políticas de AWS VPC CNI se limita a nodos EC2 Linux compatibles, no a Windows ni Fargate. Se aplica a la interfaz principal del Pod y a la familia de IP del clúster; hay limitaciones para interfaces adicionales y salida IPv4 desde Pods IPv6. Los grupos de seguridad, Network Firewall y los registros de flujo cumplen otras funciones y no sustituyen esta configuración de políticas de Kubernetes.

Referencias: [configuración de políticas VPC CNI](https://docs.aws.amazon.com/eks/latest/userguide/cni-network-policy-configure.html), [limitaciones de políticas de AWS](https://docs.aws.amazon.com/eks/latest/userguide/cni-network-policy.html), [Calico en EKS](https://docs.tigera.io/calico/latest/getting-started/kubernetes/managed-public-cloud/eks), [encadenamiento de Cilium 1.20.1](https://github.com/cilium/cilium/blob/v1.20.1/Documentation/installation/cni-chaining-aws-cni.rst), [Kubernetes NetworkPolicy](https://kubernetes.io/docs/concepts/services-networking/network-policies/).

</details>

4. ¿Qué afirmación describe correctamente el cifrado en reposo de los datos de la API de Kubernetes en EKS 1.28 o posterior?
   * A) El cifrado de sobre está habilitado de forma predeterminada; una clave KMS administrada por el cliente es opcional
   * B) Siempre hay que volver a crear el clúster antes de cifrar Secrets
   * C) La codificación Base64 proporciona cifrado en reposo
   * D) Un sidecar de aplicación debe cifrar la base de datos del plano de control de EKS

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A) El cifrado de sobre está habilitado de forma predeterminada; una clave KMS administrada por el cliente es opcional**

Los clústeres EKS con Kubernetes **1.28 o posterior** tienen habilitado de forma predeterminada el cifrado de sobre KMS v2 para **todos los datos de la API de Kubernetes**, con una clave propiedad de AWS, salvo que se asocie una clave KMS administrada por el cliente. Esto incluye Secrets, ConfigMaps y otros recursos almacenados de la API. Se suma al cifrado de disco de etcd y no cifra datos de aplicaciones en nodos ni volúmenes EBS.

**Inspecciona antes de cambiar nada.** Que no aparezca el ARN de una clave administrada por el cliente en `encryptionConfig` no significa que Secrets no esté cifrado. La consola identifica el modo de clave propiedad de AWS sin revelar el ARN de esa clave.

```bash
aws eks describe-cluster --name "${EXAMPLE_CLUSTER:?}" \
  --region "${EXAMPLE_REGION:?}" \
  --query 'cluster.{version:version,status:status,encryption:encryptionConfig}'

# Optional CMK inspection, only when a customer-managed key is required.
aws kms describe-key --key-id "${KMS_KEY_ARN:?Reviewed customer-managed key ARN}" \
  --region "$EXAMPLE_REGION" \
  --query 'KeyMetadata.{arn:Arn,state:KeyState,spec:KeySpec,usage:KeyUsage}'
```

**Clave administrada por el cliente (CMK) opcional.** Si tus requisitos necesitan control del cliente sobre las claves, usa una clave de cifrado simétrica en la región del clúster. Comprueba la disponibilidad de la clave, los permisos IAM del llamador, la política/concesiones de la clave y, si corresponde, los permisos entre cuentas. Una política genérica que concede varias acciones KMS solo a `eks.amazonaws.com` no configura todo: la identidad que aprovisiona/asocia el clúster necesita los permisos documentados `kms:DescribeKey` y `kms:CreateGrant`. La condición `kms:GrantIsForAWSResource` no se admite para controlar `CreateGrant` durante `CreateCluster`.

Puedes proporcionar un proveedor en `CreateCluster` o asociar una CMK a un clúster existente apto mediante `AssociateEncryptionConfig`; no es obligatorio crear otro clúster. No uses esto como mecanismo genérico para reemplazar claves o desactivar el cifrado. Los clústeres que ya tienen una CMK asociada deben seguir el procedimiento de administración de claves compatible.

```bash
# Optional CMK association for an eligible existing cluster.
# Review current configuration, key policy/grants and recovery procedures first.
KMS_CONFIG_DIR=$(mktemp -d /tmp/eks-kms-config.XXXXXX)
: "${KMS_CONFIG_DIR:?}"
jq -n --arg arn "${KMS_KEY_ARN:?}" \
  '[{resources:["secrets"],provider:{keyArn:$arn}}]' \
  > "$KMS_CONFIG_DIR/encryption.json" || exit 1
if ENCRYPTION_UPDATE_ID=$(aws eks associate-encryption-config \
  --cluster-name "${EXAMPLE_CLUSTER:?}" --region "${EXAMPLE_REGION:?}" \
  --encryption-config "file://$KMS_CONFIG_DIR/encryption.json" \
  --query update.id --output text); then
  aws eks describe-update --name "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION" \
    --update-id "$ENCRYPTION_UPDATE_ID" --query 'update.{status:status,errors:errors}'
fi
```

Registra el ID de actualización y comprueba hasta que indique `Successful` o un error; aceptar la solicitud no significa que haya finalizado. El campo `resources: ["secrets"]` conservado se acepta por compatibilidad. En EKS 1.28+, **no** limita el cifrado a Secrets: está obsoleto y se cifran todos los datos de la API de Kubernetes. Las API actuales también aceptan una lista `resources` omitida, nula o vacía, mientras que las respuestas conservan el valor heredado `['secrets']`. El antiguo procedimiento `enable-kms` para Kubernetes 1.27 y anteriores es una referencia histórica, no un objetivo de migración con versiones admitidas.

No desactives ni elimines una clave asociada como limpieza del laboratorio mientras exista el clúster. La indisponibilidad de la clave puede degradar el plano de control y su pérdida permanente puede hacer que el clúster sea irrecuperable. Revisa recuperación, acceso y monitoreo antes de elegir una CMK. El cifrado predeterminado con clave propiedad de AWS no requiere configurar una clave del cliente; una CMK sí tiene cargos KMS propios.

**El uso de Secrets no cambia.** Los clientes autorizados de la API y los Pods reciben valores utilizables; el cifrado en reposo no sustituye RBAC, identidad de carga de trabajo ni la protección de registros/copias de seguridad. El siguiente manifiesto contiene deliberadamente datos ficticios públicos y no representa un secreto de producción:

```yaml
# Public dummy data for a newly created secrets-lab namespace only.
apiVersion: v1
kind: Secret
metadata:
  name: example-credentials
  namespace: secrets-lab
type: Opaque
stringData:
  username: example-user
  password: public-training-placeholder
```

```bash
# Inspect keys and metadata without printing values.
kubectl --kubeconfig "${EXAMPLE_KUBECONFIG:?}" \
  -n secrets-lab get secret example-credentials -o json |
  jq '{name:.metadata.name,type:.type,keys:(.data|keys)}'
```

Para credenciales reales, evita confirmar manifiestos con valores en texto plano o Base64, literales en el historial del shell y diagnósticos que impriman valores. Base64 es codificación reversible. AWS Secrets Manager puede integrarse con archivos montados mediante CSI o con un controlador que sincronice Kubernetes Secrets; no necesariamente hay que modificar todas las aplicaciones para que usen el SDK. Un Secret sincronizado sigue sujeto a los controles de acceso de Kubernetes. Un sidecar no puede configurar el cifrado en reposo del servidor de API administrado.

Referencias: [cifrado de sobre predeterminado](https://docs.aws.amazon.com/eks/latest/userguide/envelope-encryption.html), [AssociateEncryptionConfig](https://docs.aws.amazon.com/eks/latest/APIReference/API_AssociateEncryptionConfig.html), [procedimiento KMS heredado y permisos](https://docs.aws.amazon.com/eks/latest/userguide/enable-kms.html), [Secrets Manager en EKS](https://docs.aws.amazon.com/secretsmanager/latest/userguide/integrating_csi_driver.html).

</details>

5. ¿Cómo se deben personalizar los ajustes de kubelet para nodos administrados EC2 con AL2023?
   * A) Editar kubelet del plano de control de EKS en la consola
   * B) Usar un NodeConfig compatible de nodeadm mediante eksctl o datos de usuario de una plantilla de lanzamiento
   * C) Cambiar `status.capacity` con `kubectl edit node`
   * D) Ejecutar el script AL2 `bootstrap.sh` en cada arranque de AL2023

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Usar un NodeConfig compatible de nodeadm mediante eksctl o datos de usuario de una plantilla de lanzamiento**

Para **nodos EC2 con AL2023**, usa `NodeConfig` de `nodeadm` y la integración compatible de eksctl/plantilla de lanzamiento. No uses el procedimiento AL2 `/etc/eks/bootstrap.sh` ni des por supuesto que existe la opción `eksctl create nodegroup --kubelet-extra-args`. El mapa heredado `kubeletExtraArgs` no es el campo compatible de grupo de nodos administrado que se muestra aquí.

**eksctl:** en AL2023, `overrideBootstrapCommand` contiene YAML `NodeConfig`, pese a su nombre. eksctl antepone esa configuración a los datos de usuario para que nodeadm la combine con la configuración de nodo generada. Con una AMI nativa seleccionada por EKS, EKS proporciona la configuración predeterminada del clúster necesaria. Revisa los ajustes combinados efectivos en un nodo de prueba antes de ampliar el despliegue:

```yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: my-cluster
  region: us-west-2
managedNodeGroups:
  - name: custom-kubelet
    amiFamily: AmazonLinux2023
    instanceType: m5.large
    privateNetworking: true
    desiredCapacity: 2
    minSize: 2
    maxSize: 5
    labels:
      example.com/environment: test
    overrideBootstrapCommand: |
      apiVersion: node.eks.aws/v1alpha1
      kind: NodeConfig
      spec:
        kubelet:
          config:
            kubeReserved:
              cpu: 100m
              memory: 300Mi
            systemReserved:
              cpu: 200m
              memory: 512Mi
            evictionHard:
              memory.available: 500Mi
            mergeDefaultEvictionSettings: true
```

Las reservas de recursos y el umbral de desalojo de 500 MiB anteriores son **ilustrativos**, no recomendaciones medidas. Reducen los recursos asignables a Pods y pueden provocar desalojos si no son adecuados. `mergeDefaultEvictionSettings: true` se admite en Kubernetes 1.36 y conserva las señales de desalojo predeterminadas no especificadas cuando kubelet procesa un mapa parcial. Sin la combinación apropiada, especificar una sola señal puede poner accidentalmente a cero otros umbrales predeterminados.

**Vía de AMI/plantilla de lanzamiento personalizada:** si proporcionas tu propio ID de AMI fuera de la configuración generada por eksctl, incluye metadatos completos del clúster: nombre, endpoint de API, CA en base64 y CIDR de servicios. Reutiliza el procedimiento para generar metadatos de la [pregunta avanzada 5 del cuestionario de la Parte 1](02-eks-cluster-creation-part1-quiz.md#advanced-topics) y añade los ajustes revisados `spec.kubelet.config` a ese NodeConfig. Un objeto parcial que solo contenga kubelet no es una configuración de arranque independiente completa.

En AL2023, `nodeadm-config` se ejecuta antes de los datos de usuario y `nodeadm-run` después. No vuelvas a ejecutar `nodeadm init` ni inicies/reconfigures kubelet manualmente de forma que entre en conflicto con esos servicios. Otras familias de sistemas operativos, incluidas Bottlerocket y Windows, usan mecanismos distintos; estos ejemplos no se aplican a los nodos EKS Auto Mode.

| Ajuste | Qué verificar |
| --- | --- |
| `maxPods` / `maxPodsExpression` de nodeadm | Límites de ENI/IP de la instancia, modo de CNI, delegación de prefijos y densidad compatible; no impongas el valor universal 110 |
| Etiquetas y taints de nodos | Prefiere los campos del grupo de nodos administrado; usa tu propio prefijo de etiquetas en vez de sobrescribir etiquetas de EKS/AZ |
| `kubeReserved`, `systemReserved` | Requisitos reales del host/cargas del sistema y Node Allocatable |
| `evictionHard`, umbrales soft | Señales de memoria/disco/inodos y combinación con valores predeterminados; no desactives otras protecciones |
| Controlador cgroup | Compatibilidad con el sistema operativo y el entorno de ejecución elegidos; conserva los valores probados de la AMI salvo que haga falta un cambio revisado |

**Validación:** inspecciona `capacity`/`allocatable` del nodo y la configuración/registros efectivos del servicio. Que el nodo esté listo no demuestra que se haya aplicado cada valor personalizado. Esta auditoría comprobó la sintaxis de configuración y las definiciones oficiales de los campos; no arrancó un nodo con estos ajustes.

```bash
# Kubernetes-side checks through the intended cluster context.
kubectl --kubeconfig "${EXAMPLE_KUBECONFIG:?}" describe node "${EXAMPLE_NODE_NAME:?}"

# Run separately on a specifically authorized AL2023 test node.
sudo systemctl status nodeadm-config nodeadm-run kubelet --no-pager
sudo systemctl cat kubelet
sudo journalctl -u nodeadm-config -u nodeadm-run -u kubelet --since '-15 min' --no-pager
```

Usa la ruta de configuración real del servicio configurado, en lugar de suponer que cada AMI tiene `/etc/systemd/system/kubelet.service.d/10-kubelet-args.conf`. Limita y protege los registros de diagnóstico según corresponda.

`kubectl edit node` puede cambiar metadatos del objeto Node, pero no define la configuración de inicio de kubelet. SSM puede ejecutar comandos en el host, pero una modificación puntual no es una configuración duradera para sustituir nodos administrados y puede exigir reinicios disruptivos. Incluye los ajustes revisados en la configuración de aprovisionamiento y sustituye/prueba los nodos de forma planificada.

Referencias: [arranque de AL2023 en eksctl](https://docs.aws.amazon.com/eks/latest/eksctl/node-bootstrapping.html), [servicios de AL2023](https://docs.aws.amazon.com/eks/latest/userguide/al2023.html), [API de nodeadm](https://awslabs.github.io/amazon-eks-ami/nodeadm/doc/api/), [KubeletConfiguration](https://kubernetes.io/docs/reference/config-api/kubelet-config.v1beta1/), [definiciones de campos de Kubernetes 1.36](https://github.com/kubernetes/kubelet/blob/v0.36.0/config/v1beta1/types.go).

</details>

6. ¿Qué mecanismos pueden sustituir los controles eliminados de PodSecurityPolicy en EKS?
   * A) Solo grupos de seguridad de EC2
   * B) Pod Security Admission y, cuando haga falta, un motor de políticas compatible
   * C) Solo la retención de registros de CloudWatch
   * D) Una clave de acceso de un usuario de IAM guardada en cada Pod

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Pod Security Admission y, cuando haga falta, un motor de políticas compatible**

PodSecurityPolicy quedó obsoleto en Kubernetes 1.21 y se eliminó en 1.25. Usa **Pod Security Admission (PSA)**, integrado, para aplicar **Pod Security Standards (PSS)**; para requisitos que excedan esos controles, usa un motor de políticas adecuado.

**PSA:** Privileged, Baseline y Restricted son los tres niveles de PSS; `enforce`, `audit` y `warn` son modos separados. Para un namespace de laboratorio nuevo, este ejemplo aplica Baseline e informa de las infracciones de Restricted. La versión de política se fija para el ejemplo de EKS 1.36; elige una versión compatible con el clúster real.

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: policy-engine-lab
  labels:
    pod-security.kubernetes.io/enforce: baseline
    pod-security.kubernetes.io/enforce-version: v1.36
    pod-security.kubernetes.io/audit: restricted
    pod-security.kubernetes.io/audit-version: v1.36
    pod-security.kubernetes.io/warn: restricted
    pod-security.kubernetes.io/warn-version: v1.36
```

No cambies etiquetas a ciegas en un namespace compartido existente. Primero usa audit/warn, corrige manifiestos de cargas de trabajo y, después, endurece la aplicación. PSA no modifica Pods para que cumplan ni expulsa Pods que ya se están ejecutando. Evalúa la admisión de Pods; las advertencias/auditorías de plantillas de carga de trabajo ayudan a detectar infracciones antes de que sus controladores intenten crear Pods.

**Kyverno:** el chart 3.9.1 incluye el controlador 1.19.1 en este ejemplo auditado. Kyverno 1.19 declara obsoletos los tipos heredados `ClusterPolicy`/`Policy` y su guía de migración programa su eliminación en 1.20. Los ejemplos nuevos deben usar las API de políticas actuales basadas en CEL. Migra las políticas existentes antes de una actualización incompatible, en vez de cambiar solo la versión del controlador.

```bash
# Optional new installation; review existing controllers and release compatibility.
helm repo add kyverno https://kyverno.github.io/kyverno/
helm repo update kyverno
helm install kyverno kyverno/kyverno --version 3.9.1 \
  --namespace kyverno --create-namespace \
  --kubeconfig "${EXAMPLE_KUBECONFIG:?}" --wait --timeout 5m
```

La siguiente **ValidatingPolicy** de `policies.kyverno.io/v1` rechaza `privileged: true` en contenedores normales, de inicialización y efímeros y solo coincide con el namespace de laboratorio. Permite que el campo esté ausente o sea falso:

```yaml
apiVersion: policies.kyverno.io/v1
kind: ValidatingPolicy
metadata:
  name: disallow-privileged-lab
spec:
  validationActions:
  - Deny
  evaluation:
    background:
      enabled: true
  matchConstraints:
    resourceRules:
    - apiGroups:
      - ''
      apiVersions:
      - v1
      operations:
      - CREATE
      - UPDATE
      resources:
      - pods
      - pods/ephemeralcontainers
  matchConditions:
  - name: lab-only
    expression: object.metadata.namespace == 'policy-engine-lab'
  validations:
  - expression: object.spec.containers.all(c, !has(c.securityContext) || !has(c.securityContext.privileged) || !c.securityContext.privileged)
    message: Privileged containers are not allowed.
  - expression: '!has(object.spec.initContainers) || object.spec.initContainers.all(c, !has(c.securityContext) ||
      !has(c.securityContext.privileged) || !c.securityContext.privileged)'
    message: Privileged initContainers are not allowed.
  - expression: '!has(object.spec.ephemeralContainers) || object.spec.ephemeralContainers.all(c, !has(c.securityContext)
      || !has(c.securityContext.privileged) || !c.securityContext.privileged)'
    message: Privileged ephemeralContainers are not allowed.
```

Esto demuestra un control, no todo el estándar Baseline o Restricted. El motor/CRD de políticas debe estar listo antes de aplicar la política, y hay que verificar la admisión activa y el comportamiento de subrecursos en el clúster previsto. La evaluación en segundo plano informa de infracciones existentes, pero no expulsa cargas en ejecución.

**Alternativa OPA Gatekeeper:** instala una versión revisada de Gatekeeper si su modelo de políticas satisface tus requisitos. Este ejemplo fija el chart/controlador 3.23.1:

```bash
# Alternative policy-engine example, not a prerequisite for the Kyverno example.
helm repo add gatekeeper https://open-policy-agent.github.io/gatekeeper/charts
helm repo update gatekeeper
helm install gatekeeper gatekeeper/gatekeeper --version 3.23.1 \
  --namespace gatekeeper-system --create-namespace \
  --kubeconfig "${EXAMPLE_KUBECONFIG:?}" --wait --timeout 5m
```

Gatekeeper necesita primero una ConstraintTemplate `templates.gatekeeper.sh/v1`. Espera a que la plantilla y el CRD de restricción generado estén establecidos antes de aplicar la Constraint correspondiente. El ejemplo Rego siguiente comprueba las mismas tres listas de contenedores y limita la Constraint al namespace del laboratorio:

```yaml
apiVersion: templates.gatekeeper.sh/v1
kind: ConstraintTemplate
metadata:
  name: k8snoprivilegedlab
spec:
  crd:
    spec:
      names:
        kind: K8sNoPrivilegedLab
      validation:
        openAPIV3Schema:
          type: object
  targets:
  - target: admission.k8s.gatekeeper.sh
    rego: "package k8snoprivilegedlab\n\ncontainers[c] {\n  c := input.review.object.spec.containers[_]\n\
      }\ncontainers[c] {\n  c := input.review.object.spec.initContainers[_]\n}\ncontainers[c]\
      \ {\n  c := input.review.object.spec.ephemeralContainers[_]\n}\nviolation[{\"\
      msg\": msg}] {\n  c := containers[_]\n  c.securityContext.privileged == true\n\
      \  msg := sprintf(\"Privileged container is not allowed: %v\", [c.name])\n}\n"
---
apiVersion: constraints.gatekeeper.sh/v1beta1
kind: K8sNoPrivilegedLab
metadata:
  name: no-privileged-lab
spec:
  enforcementAction: deny
  match:
    scope: Namespaced
    namespaces:
    - policy-engine-lab
    kinds:
    - apiGroups:
      - ''
      kinds:
      - Pod
```

`enforcementAction: deny` de Gatekeeper rechaza infracciones coincidentes; `dryrun` o `warn` permiten una implementación gradual. Una plantilla sin su Constraint no aplica ninguna política. Usa el esquema de API y modo Rego compatibles con la versión instalada.

**Validación y límites:** la CLI Kyverno 1.19.1 (con advertencias tratadas como errores) y Gator de Gatekeeper 3.23.1 se ejecutaron localmente con seis casos cada uno: valor explícitamente falso, campo omitido, contenedores normales/de inicialización/efímeros privilegiados y un namespace fuera de alcance. Ambas implementaciones dieron los resultados locales previstos. No se instaló ningún clúster ni se probó admisión activa.

```bash
# Offline policy logic checks using locally reviewed fixture files.
kyverno apply kyverno-policy.yaml --resource test-pod.yaml --warnings-as-errors
gator test --filename gatekeeper-policy.yaml --filename test-pod.yaml --output=json
```

No deduzcas que un rechazo activo provino de un motor específico si PSA u otro webhook también lo habría rechazado. Verifica el estado del controlador/política, el alcance, las respuestas de admisión reales y los informes. Usa el conjunto completo de controles para namespaces del host, hostPath, capacidades, escalada de privilegios y otros requisitos PSS.

AWS Security Hub, AWS Config y los grupos de seguridad de EC2 tienen funciones distintas; habilitarlos no sustituye la aplicación de políticas de admisión de Pods de Kubernetes.

Referencias: [PSA](https://kubernetes.io/docs/concepts/security/pod-security-admission/), [PSS](https://kubernetes.io/docs/concepts/security/pod-security-standards/), [migración de Kyverno CEL](https://kyverno.io/docs/guides/migration-to-cel/), [Kyverno 1.19.1](https://github.com/kyverno/kyverno/releases/tag/v1.19.1), [guía de Gatekeeper 3.23.1](https://github.com/open-policy-agent/gatekeeper/blob/v3.23.1/website/docs/howto.md).

</details>

7. ¿Qué requisito de proveedor de identidad de IAM necesita la relación de confianza de identidad web de IRSA?
   * A) Una clave de acceso de usuario IAM almacenada en cada Pod
   * B) Un RoleBinding de administrador del clúster
   * C) Un proveedor OIDC de IAM que coincida con el emisor del clúster
   * D) Una IP pública en cada nodo de trabajo

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Un proveedor OIDC de IAM que coincida con el emisor del clúster**

IRSA necesita un proveedor OIDC de IAM que coincida con el emisor del clúster de destino. Comprueba si ya existe; no crees proveedores duplicados ni reutilices el emisor de otro clúster. Este requisito debe cumplirse antes de que la carga de trabajo asuma el rol de IAM, aunque la cuenta de servicio puede crearse antes que el rol y anotarse después. No hay un orden universal obligatorio para crear todos los recursos.

```bash
aws eks describe-cluster --name "${EXAMPLE_CLUSTER:?}" \
  --region "${EXAMPLE_REGION:?}" --query cluster.identity.oidc.issuer --output text
eksctl utils associate-iam-oidc-provider \
  --cluster "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION" --approve
```

Usa eksctl o el procedimiento actual para proveedores OIDC de IAM, en vez de copiar una huella digital de certificado fija y antigua. Configura `sts.amazonaws.com` como ID de cliente/audiencia previsto. En una VPC sin salida a Internet, configurar el proveedor desde dentro de la VPC puede requerir el endpoint de interfaz `oidc-eks`/DNS privado independiente u otra ruta de administración accesible. El intercambio de tokens de IRSA también necesita conectividad regional con STS.

Después crea la política de rol con alcance limitado y la política de confianza de la pregunta 1 con `aud` y `sub`; anota la cuenta de servicio correcta y crea un Pod nuevo que la use. Los Pods existentes no reciben la configuración inyectada recién modificada solo porque cambie la anotación de la cuenta; recréalos mediante el despliegue habitual de su controlador.

Para comprobar la identidad, usa el manifiesto explícito de Pod de la pregunta 1. `kubectl run --serviceaccount` no es una opción compatible actual:

```bash
# After deploying the identity-check Pod from question 1.
kubectl --kubeconfig "${EXAMPLE_KUBECONFIG:?}" -n irsa-lab \
  get pod irsa-identity-check -o jsonpath='{.status.phase}{"\n"}'
kubectl --kubeconfig "$EXAMPLE_KUBECONFIG" -n irsa-lab logs irsa-identity-check
```

Comprueba el estado de salida del Pod y compara la cuenta/identidad del rol asumido devuelto con el rol esperado. La identidad del rol del nodo no demuestra que IRSA funcione. Prueba después únicamente la operación acotada de la aplicación; `aws s3 ls` sin bucket intentaría enumerar todos los buckets y no corresponde a una política limitada a uno solo.

EKS Pod Identity usa otro mecanismo y no requiere crear un proveedor OIDC de IAM por cada clúster. Mantén separados sus requisitos de asociación de cuenta de servicio, agente y confianza IAM de los de IRSA.

Referencias: [crear un proveedor OIDC de IAM](https://docs.aws.amazon.com/eks/latest/userguide/enable-iam-roles-for-service-accounts.html), [conectividad privada de IRSA](https://docs.aws.amazon.com/eks/latest/userguide/private-clusters.html), [configuración de Pods](https://docs.aws.amazon.com/eks/latest/userguide/pod-configuration.html).

</details>

8. ¿Cómo se habilita la exportación de registros del plano de control de EKS?
   * A) Instalar un agente en los hosts del plano de control administrado
   * B) Configurar los registros del clúster mediante las API de EKS, la consola o eksctl
   * C) Instalar Fluentd únicamente en los nodos de trabajo
   * D) Conectarse por SSH al servidor API administrado y editar su configuración

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Configurar los registros del clúster mediante las API de EKS, la consola o eksctl**

Habilita la exportación de registros del plano de control de EKS mediante la API de EKS, la consola o eksctl. AWS opera los hosts del plano de control; instalar agentes de CloudWatch/Fluentd en nodos de trabajo no habilita esos registros. Los operadores no pueden conectarse por SSH a los hosts administrados del plano de control.

**AWS CLI:** inspecciona la configuración actual y elige los tipos necesarios. Es una actualización asíncrona: registra su ID y vuelve a ejecutar `describe-update` hasta que tenga éxito o indique un error. EKS puede necesitar hasta cinco direcciones IP libres en cada subred del clúster para actualizar los registros.

```bash
# Enable the reviewed set of log types; this example enables all five.
if LOG_UPDATE_ID=$(aws eks update-cluster-config \
  --name "${EXAMPLE_CLUSTER:?}" --region "${EXAMPLE_REGION:?}" \
  --logging '{"clusterLogging":[{"types":["api","audit","authenticator","controllerManager","scheduler"],"enabled":true}]}' \
  --query update.id --output text); then
  aws eks describe-update --name "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION" \
    --update-id "$LOG_UPDATE_ID" --query 'update.{status:status,errors:errors}'
fi
```

Para habilitar solo API/audit y desactivar explícitamente los otros tres tipos, usa la siguiente carga de registro **alternativa** después de revisar los requisitos de auditoría/retención. No ejecutes ambas configuraciones en secuencia ni desactives registros requeridos solo para reducir costes:

```json
{
  "clusterLogging": [
    {"types": ["api", "audit"], "enabled": true},
    {"types": ["authenticator", "controllerManager", "scheduler"], "enabled": false}
  ]
}
```

**Alternativa eksctl:** las operaciones de vista previa y aplicación son distintas; `--approve` es obligatorio para aplicar el cambio revisado. `--disable-types` puede desactivar expresamente tipos seleccionados cuando esa sea la intención.

```bash
# Alternative interface; do not submit a second update while one is running.
# Without --approve this previews the logging change.
eksctl utils update-cluster-logging \
  --cluster "${EXAMPLE_CLUSTER:?}" --region "${EXAMPLE_REGION:?}" \
  --enable-types api,audit,authenticator,controllerManager,scheduler

# Apply the reviewed change.
eksctl utils update-cluster-logging \
  --cluster "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION" \
  --enable-types api,audit,authenticator,controllerManager,scheduler --approve
```

**Consola:** selecciona el clúster, abre **Observabilidad** y ve a **Control plane logging → Manage logging**. Elige cada tipo de registro y guarda la configuración revisada.

| Tipo | Propósito | Prefijo del flujo |
| --- | --- | --- |
| `api` | Diagnóstico de componentes del servidor API; los parámetros de inicio solo están disponibles si se capturan antes de rotar el registro | `kube-apiserver-` |
| `audit` | Actividad de la API de Kubernetes registrada conforme a la política de auditoría administrada | `kube-apiserver-audit-` |
| `authenticator` | Diagnóstico de autenticación IAM | `authenticator-` |
| `controllerManager` | Diagnóstico del bucle de control integrado de Kubernetes | `kube-controller-manager-` |
| `scheduler` | Diagnóstico de planificación de Pods | `kube-scheduler-` |

Los registros de auditoría no documentan cada solicitud de aplicación ni cada proceso/acción de red en un nodo. CloudTrail registra por separado la actividad pertinente de la API de AWS. La entrega de registros del plano de control es de mejor esfuerzo, normalmente en unos minutos; habilitarla no recupera registros ya rotados.

**Verifica la exportación:** los registros están en `/aws/eks/<cluster-name>/cluster` de la cuenta/región del clúster. Los sufijos de los flujos rotan; inspecciona las horas de eventos recientes en vez de suponer un único nombre permanente.

```bash
aws eks describe-cluster --name "${EXAMPLE_CLUSTER:?}" \
  --region "${EXAMPLE_REGION:?}" --query cluster.logging
aws logs describe-log-streams --region "$EXAMPLE_REGION" \
  --log-group-name "/aws/eks/$EXAMPLE_CLUSTER/cluster" \
  --order-by LastEventTime --descending --max-items 10
```

La ingesta, el almacenamiento y las consultas de CloudWatch tienen coste. Configura la retención y los controles de acceso según tus requisitos y verifica que lleguen los tipos de registro requeridos. Que la actualización de configuración tenga éxito no demuestra que estén presentes todos los eventos históricos esperados. Los recolectores de registros de nodos/aplicaciones son una preocupación distinta del plano de datos.

Referencia: [registros del plano de control de EKS](https://docs.aws.amazon.com/eks/latest/userguide/control-plane-logs.html).

</details>

9. ¿Cómo se cambian los tipos de instancia especificados en la solicitud del grupo de nodos administrado de EKS, cuando no se usa un tipo de instancia de una plantilla personalizada?
   * A) Editar el campo `instanceTypes` directamente en la consola
   * B) Crear un grupo de nodos de sustitución y validar la migración de cargas de trabajo
   * C) Usar `kubectl edit node` para cambiar el hardware EC2
   * D) Pasar nuevos tipos de instancia a `update-nodegroup-config`

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Crear un grupo de nodos de sustitución y validar la migración de cargas de trabajo**

Esta pregunta trata los tipos de instancia especificados en la **solicitud del grupo de nodos administrado**, no en una plantilla de lanzamiento personalizada. Esos tipos no se pueden cambiar con `update-nodegroup-config`; crea un grupo nuevo y migra las cargas de trabajo.

Hay otra vía si el grupo se creó con una plantilla de lanzamiento personalizada y el tipo de instancia está definido allí: revisa una versión nueva de **la misma** plantilla y aplícala mediante `update-nodegroup-version`. Aun así, se sustituyen instancias. No modifiques plantillas generadas por EKS, no especifiques tipos en ambos lugares ni supongas que una arquitectura de CPU distinta funcionará con la misma AMI/imágenes.

**1. Crear capacidad de sustitución.** Comprueba ofertas de instancias, cuotas, arquitectura, capacidad de CNI/IP, AZ, almacenamiento y permisos del rol de nodo. Los dos comandos son alternativas para un clúster de pruebas existente:

```bash
# Alternative 1: eksctl, for an unused managed node-group name.
eksctl create nodegroup --cluster "${EXAMPLE_CLUSTER:?}" \
  --region "${EXAMPLE_REGION:?}" --name "${NEW_NODEGROUP_NAME:?}" \
  --managed --node-ami-family AmazonLinux2023 --node-private-networking \
  --node-type m5.large --nodes 3 --nodes-min 1 --nodes-max 5 \
  --node-labels "example.com/migration-target=true"

# Alternative 2: AWS CLI; do not run both for the same node group.
aws eks create-nodegroup --cluster-name "${EXAMPLE_CLUSTER:?}" \
  --region "${EXAMPLE_REGION:?}" --nodegroup-name "${NEW_NODEGROUP_NAME:?}" \
  --subnets "${PRIVATE_SUBNET_A:?}" "${PRIVATE_SUBNET_B:?}" \
  --instance-types m5.large --ami-type AL2023_x86_64_STANDARD \
  --scaling-config minSize=1,maxSize=5,desiredSize=3 \
  --node-role "${NODE_ROLE_ARN:?}" \
  --labels '{"example.com/migration-target":"true"}'
```

**2. Verificar el grupo nuevo.** Espera a que esté `ACTIVE`, haya nodos `Ready` sanos y funcionen CNI/DNS. Enumerar etiquetas no demuestra que la aplicación esté lista:

```bash
aws eks describe-nodegroup --cluster-name "${EXAMPLE_CLUSTER:?}" \
  --region "${EXAMPLE_REGION:?}" --nodegroup-name "${NEW_NODEGROUP_NAME:?}" \
  --query 'nodegroup.{status:status,health:health,types:instanceTypes,subnets:subnets}'
kubectl --kubeconfig "${EXAMPLE_KUBECONFIG:?}" get nodes \
  -l example.com/migration-target=true -o wide
```

**3. Migrar y probar.** Elige un plan de actualización gradual o blue/green específico de la aplicación. Un Service envía tráfico a endpoints de Pods listos seleccionados, no directamente al nombre de un grupo de nodos. Conserva la capacidad antigua hasta entender las necesidades de reversión y la compatibilidad de datos.

Para vaciar nodos manualmente, selecciona uno antiguo, confirma su etiqueta de grupo de nodos y comprueba antes los PDB, la capacidad libre y el almacenamiento local. Este ejemplo no omite el desalojo ni descarta datos `emptyDir` intencionadamente. Si falla el vaciado, investiga la causa antes de continuar; el nodo puede quedarse acordonado.

```bash
# One reviewed node at a time, after validating replacement capacity.
OLD_NODE_JSON=$(kubectl --kubeconfig "${EXAMPLE_KUBECONFIG:?}" \
  get node "${OLD_NODE_NAME:?}" -o json) || exit 1
OLD_NODE_GROUP=$(printf '%s' "$OLD_NODE_JSON" |
  jq -er '.metadata.labels["eks.amazonaws.com/nodegroup"]') || exit 1
if [ "$OLD_NODE_GROUP" != "${OLD_NODEGROUP_NAME:?}" ]; then
  printf '%s\n' 'Node is not in the intended old managed node group.' >&2
  exit 1
fi
kubectl --kubeconfig "$EXAMPLE_KUBECONFIG" cordon "$OLD_NODE_NAME" &&
kubectl --kubeconfig "$EXAMPLE_KUBECONFIG" drain "$OLD_NODE_NAME" \
  --ignore-daemonsets --timeout=15m
```

Como alternativa, actualiza la plantilla Pod de la aplicación real para que seleccione el grupo de sustitución. El ejemplo completo siguiente es una demostración independiente para un namespace `migration-lab` recién creado, no un manifiesto de sustitución para una aplicación existente:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: migration-demo
  namespace: migration-lab
spec:
  replicas: 3
  selector:
    matchLabels:
      app: migration-demo
  template:
    metadata:
      labels:
        app: migration-demo
    spec:
      nodeSelector:
        example.com/migration-target: "true"
      containers:
        - name: nginx
          image: nginx:1.30.6
          ports:
            - containerPort: 80
          readinessProbe:
            httpGet:
              path: /
              port: 80
          resources:
            requests:
              cpu: 100m
              memory: 128Mi
            limits:
              memory: 256Mi
---
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: migration-demo
  namespace: migration-lab
spec:
  minAvailable: 2
  selector:
    matchLabels:
      app: migration-demo
```

El PDB exige dos Pods coincidentes sanos durante un desalojo voluntario. Con tres réplicas, normalmente se puede desalojar una por vez si se cumplen las demás condiciones. No garantiza disponibilidad, no protege ante eliminaciones directas ni conserva datos locales del nodo. Comprueba ubicación, disponibilidad, enrutamiento del servicio, afinidad de zona del volumen persistente y copias de seguridad con pruebas representativas de las cargas.

**4. Retirar el grupo antiguo solo después de validar.** No ejecutes comandos de eksctl y AWS para borrar el grupo ni eludas los PDB para completar la migración. Revisa el clúster/grupo de destino y elimina únicamente el grupo propiedad de esta migración:

```bash
# Separate final step, after application/data validation and ownership review.
if [ "${MIGRATION_VERIFIED:?Set yes only after workload and data checks}" = yes ]; then
  eksctl delete nodegroup --cluster "${EXAMPLE_CLUSTER:?}" \
    --region "${EXAMPLE_REGION:?}" --name "${OLD_NODEGROUP_NAME:?}" --approve --wait
fi
```

Conserva el grupo antiguo si falla la validación de la aplicación. Blue/green añade capacidad y coste temporalmente; no garantiza que sea sencillo revertir cambios con estado. `kubectl edit node` modifica metadatos de Kubernetes, no el tipo de instancia EC2 subyacente.

Referencias: [actualizaciones de plantillas de lanzamiento](https://docs.aws.amazon.com/eks/latest/userguide/launch-templates.html), [UpdateNodegroupConfig](https://docs.aws.amazon.com/eks/latest/APIReference/API_UpdateNodegroupConfig.html), [vaciado de nodos](https://kubernetes.io/docs/tasks/administer-cluster/safely-drain-node/).

</details>

10. ¿Qué afirmación sobre los taints de grupos de nodos administrados de EKS es correcta?
   * A) Solo `kubectl` puede configurarlos
   * B) Usa la configuración del grupo de nodos mediante consola/API o eksctl; comprueba por separado el estado real de los objetos Node
   * C) La consola de EKS no permite configurarlos
   * D) Una toleration garantiza la ubicación en el grupo con el taint correspondiente

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Usa la configuración del grupo de nodos mediante consola/API o eksctl; comprueba por separado el estado real de los objetos Node**

Los taints de grupos de nodos administrados se configuran con la consola/API de EKS o un archivo de configuración de eksctl. La consola es válida; no marques esa opción como incorrecta porque también exista un método de CLI. `kubectl taint` directo modifica un objeto Node individual y no es la configuración persistente de nodos de sustitución de un grupo administrado.

**Configuración con eksctl:** guarda esto como configuración de grupo de nodos revisada para un clúster existente y un nombre de grupo no utilizado; después usa `eksctl create nodegroup -f nodegroup.yaml`. Utiliza el campo compatible `taints`, no una opción de CLI supuesta.

```yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: my-cluster
  region: us-west-2
managedNodeGroups:
  - name: tainted-ng
    amiFamily: AmazonLinux2023
    instanceType: m5.large
    privateNetworking: true
    desiredCapacity: 3
    minSize: 2
    maxSize: 5
    labels:
      example.com/pool: batch
    taints:
      - key: dedicated
        value: batch
        effect: NoSchedule
      - key: special
        value: "true"
        effect: PreferNoSchedule
```

**Alternativa AWS CLI:** Kubernetes/eksctl usan nombres de efecto en CamelCase, mientras que la API de EKS usa nombres en mayúsculas:

| Kubernetes / eksctl | API de EKS | Efecto |
| --- | --- | --- |
| `NoSchedule` | `NO_SCHEDULE` | El planificador rechaza Pods nuevos sin toleration coincidente; los existentes permanecen |
| `PreferNoSchedule` | `PREFER_NO_SCHEDULE` | Preferencia de planificación flexible, no garantía |
| `NoExecute` | `NO_EXECUTE` | También expulsa Pods existentes sin toleration coincidente; `tolerationSeconds` puede retrasar la expulsión |

```bash
# Alternative to the eksctl file: create a new group through the EKS API.
aws eks create-nodegroup --cluster-name "${EXAMPLE_CLUSTER:?}" \
  --region "${EXAMPLE_REGION:?}" --nodegroup-name "${NEW_NODEGROUP_NAME:?}" \
  --subnets "${PRIVATE_SUBNET_A:?}" "${PRIVATE_SUBNET_B:?}" \
  --instance-types m5.large --ami-type AL2023_x86_64_STANDARD \
  --scaling-config minSize=2,maxSize=5,desiredSize=3 \
  --node-role "${NODE_ROLE_ARN:?}" \
  --labels '{"example.com/pool":"batch"}' \
  --taints '[{"key":"dedicated","value":"batch","effect":"NO_SCHEDULE"},{"key":"special","value":"true","effect":"PREFER_NO_SCHEDULE"}]'
```

```bash
# Separate update example for the intended existing group.
if TAINT_UPDATE_ID=$(aws eks update-nodegroup-config \
  --cluster-name "${EXAMPLE_CLUSTER:?}" --region "${EXAMPLE_REGION:?}" \
  --nodegroup-name "${EXAMPLE_NODEGROUP:?}" \
  --taints '{"addOrUpdateTaints":[{"key":"dedicated","value":"batch","effect":"NO_SCHEDULE"}],"removeTaints":[{"key":"special","value":"true","effect":"PREFER_NO_SCHEDULE"}]}' \
  --query update.id --output text); then
  aws eks describe-update --name "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION" \
    --nodegroup-name "$EXAMPLE_NODEGROUP" --update-id "$TAINT_UPDATE_ID" \
    --query 'update.{status:status,errors:errors}'
fi
```

La actualización es asíncrona: espera a que termine correctamente e inspecciona los taints reales del objeto Node. EKS **no** vuelve a añadir automáticamente a un Node existente el taint de un grupo administrado si alguien lo elimina manualmente, aunque la configuración del grupo aún lo incluya. Limita quién puede modificar nodos y verifica el estado después de los cambios.

**Ubicación de cargas de trabajo dedicadas:** una toleration permite la planificación, pero no obliga a ubicar un Pod en el grupo con taint. Combínala con un selector/afinidad de nodo apropiados. Esta demostración completa usa un namespace `taint-lab` nuevo:

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: batch-example
  namespace: taint-lab
spec:
  nodeSelector:
    example.com/pool: batch
  tolerations:
    - key: dedicated
      operator: Equal
      value: batch
      effect: NoSchedule
  restartPolicy: Never
  containers:
    - name: task
      image: busybox:1.37
      command: ["sh", "-c", "echo batch-example-complete"]
      resources:
        requests:
          cpu: 100m
          memory: 32Mi
        limits:
          memory: 64Mi
```

Para grupos GPU, selecciona también instancias/AMI compatibles e instala un complemento de dispositivo admitido; las cargas deben solicitar un recurso extendido como `nvidia.com/gpu`. Un taint `dedicated=gpu` por sí solo no instala controladores ni asigna una GPU. Los taints son controles de planificación, no fronteras de seguridad entre tenants.

**Mantenimiento:** un taint temporal de nodo puede impedir la planificación ordinaria nueva, pero no vacía Pods en ejecución. Los dos comandos siguientes corresponden al inicio y final de una ventana de mantenimiento revisada:

```bash
# Individual-node maintenance example; does not evict existing Pods.
kubectl --kubeconfig "${EXAMPLE_KUBECONFIG:?}" taint node \
  "${EXAMPLE_NODE_NAME:?}" maintenance=planned:NoSchedule

# After the maintenance window, remove only this exact example taint.
kubectl --kubeconfig "$EXAMPLE_KUBECONFIG" taint node \
  "$EXAMPLE_NODE_NAME" maintenance=planned:NoSchedule-
```

Si hace falta desalojar, utiliza un procedimiento de vaciado independiente que tenga en cuenta los PDB. Evita añadir `NoExecute` a un grupo poblado sin revisar el efecto de expulsión inmediato. Los indicadores de registro de node bootstrap son otro mecanismo, pero la configuración del grupo administrado resulta más clara para este caso.

Referencia: [taints de nodos administrados por EKS](https://docs.aws.amazon.com/eks/latest/userguide/node-taints-managed-node-groups.html).

</details>

## Ejercicios prácticos

### Ejercicio 1: Configurar IRSA (IAM Roles for Service Accounts)

**Escenario:** una carga de trabajo Linux de un clúster EKS existente necesita leer un prefijo autorizado `training/` de un bucket S3. Asígnale un rol de carga de trabajo dedicado en vez de aplicar una política amplia de S3 a todos los nodos.

**Requisitos previos:** usa un clúster de formación autorizado en la partición comercial de AWS, AWS CLI v2, eksctl y jq. El operador necesita los permisos IAM y Kubernetes para este ejercicio. Prepara un objeto existente y no confidencial bajo `training/` en un bucket aprobado y define `S3_BUCKET`/`S3_TEST_KEY`. La política del bucket y cualquier clave de cifrado administrada por el cliente deben permitir el rol previsto; añade permisos KMS con alcance independiente solo si el cifrado del objeto los requiere. Este ejemplo no crea buckets ni objetos.

<details>
<summary>Mostrar solución</summary>

**1. Preparar un namespace único, kubeconfig privado y el proveedor OIDC del clúster.** Conserva el directorio y el registro de titularidad generados hasta terminar la limpieza. Ejecuta los pasos en la misma sesión de Bash; si falla uno, inspecciona los recursos registrados antes de volver a intentarlo.

```bash
# Commercial AWS partition example; use an existing approved S3 training prefix.
: "${EXAMPLE_CLUSTER:?}"
: "${EXAMPLE_REGION:?}"
: "${S3_BUCKET:?Existing bucket containing the approved training object}"
: "${S3_TEST_KEY:?Existing non-sensitive object key under training/}"
case "$S3_TEST_KEY" in training/*) ;; *) printf '%s\n' 'Use a training/ key.' >&2; exit 1 ;; esac
IRSA_LAB_DIR=$(mktemp -d /tmp/eks-irsa-lab.XXXXXX)
: "${IRSA_LAB_DIR:?}"
IRSA_LAB_ID="irsa-quiz-$(date +%s)-$$"
IRSA_NAMESPACE="$IRSA_LAB_ID"
IRSA_ROLE_NAME="$IRSA_LAB_ID"
IRSA_SERVICE_ACCOUNT=s3-reader
IRSA_KUBECONFIG="$IRSA_LAB_DIR/kubeconfig"

aws sts get-caller-identity --output json > "$IRSA_LAB_DIR/caller.json" || exit 1
IRSA_ACCOUNT_ID=$(jq -er '.Account' "$IRSA_LAB_DIR/caller.json") || exit 1
jq -e '.Arn | startswith("arn:aws:")' "$IRSA_LAB_DIR/caller.json" >/dev/null || exit 1
aws eks describe-cluster --name "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION" \
  --query cluster --output json > "$IRSA_LAB_DIR/cluster.json" || exit 1
IRSA_ISSUER=$(jq -er '.identity.oidc.issuer' "$IRSA_LAB_DIR/cluster.json") || exit 1
case "$IRSA_ISSUER" in https://*) ;; *) printf '%s\n' 'Invalid OIDC issuer.' >&2; exit 1 ;; esac
IRSA_ISSUER_HOST="${IRSA_ISSUER#https://}"
IRSA_PROVIDER_ARN="arn:aws:iam::$IRSA_ACCOUNT_ID:oidc-provider/$IRSA_ISSUER_HOST"

aws eks update-kubeconfig --name "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION" \
  --kubeconfig "$IRSA_KUBECONFIG" --alias "$EXAMPLE_CLUSTER" || exit 1
kubectl --kubeconfig "$IRSA_KUBECONFIG" create namespace "$IRSA_NAMESPACE" || exit 1
IRSA_NAMESPACE_UID=$(kubectl --kubeconfig "$IRSA_KUBECONFIG" \
  get namespace "$IRSA_NAMESPACE" -o jsonpath='{.metadata.uid}') || exit 1
: "${IRSA_NAMESPACE_UID:?}"
jq -n --arg namespace "$IRSA_NAMESPACE" --arg uid "$IRSA_NAMESPACE_UID" \
  '{namespace:$namespace,namespaceUID:$uid}' > "$IRSA_LAB_DIR/ownership.json" || exit 1

# The cluster's provider is shared infrastructure; eksctl checks/associates it.
eksctl utils associate-iam-oidc-provider --cluster "$EXAMPLE_CLUSTER" \
  --region "$EXAMPLE_REGION" --approve || exit 1
aws iam get-open-id-connect-provider --open-id-connect-provider-arn "$IRSA_PROVIDER_ARN" \
  --output json > "$IRSA_LAB_DIR/provider.json" || exit 1
jq -e '.ClientIDList | index("sts.amazonaws.com") != null' \
  "$IRSA_LAB_DIR/provider.json" >/dev/null || exit 1
```

La carga requiere conectividad con STS y acceso a S3. Los entornos solo privados necesitan las rutas regionales adecuadas a STS/ECR/S3; configurar el proveedor OIDC de IAM desde dentro de la VPC también puede requerir conectividad `oidc-eks`. Restringe IMDS y el uso de cuentas de servicio por separado; IRSA por sí sola no aísla Pods.

**2. Crear el rol dedicado y la política con alcance limitado.** La política de confianza requiere la audiencia prevista y el sujeto exacto de namespace/cuenta de servicio. La política permite listar solo el prefijo `training/` del bucket y leer objetos solo bajo ese prefijo. No concede `ListAllMyBuckets`.

```bash
jq -n --arg provider "${IRSA_PROVIDER_ARN:?}" --arg issuer "${IRSA_ISSUER_HOST:?}" \
  --arg subject "system:serviceaccount:${IRSA_NAMESPACE:?}:${IRSA_SERVICE_ACCOUNT:?}" \
  '{
    Version:"2012-10-17",
    Statement:[{
      Effect:"Allow",
      Principal:{Federated:$provider},
      Action:"sts:AssumeRoleWithWebIdentity",
      Condition:{StringEquals:{
        ($issuer+":aud"):"sts.amazonaws.com",
        ($issuer+":sub"):$subject
      }}
    }]
  }' > "${IRSA_LAB_DIR:?}/trust.json" || exit 1

jq -n --arg bucket "${S3_BUCKET:?}" \
  '{
    Version:"2012-10-17",
    Statement:[
      {
        Effect:"Allow",Action:"s3:ListBucket",Resource:("arn:aws:s3:::"+$bucket),
        Condition:{StringLike:{"s3:prefix":["training/","training/*"]}}
      },
      {
        Effect:"Allow",Action:"s3:GetObject",
        Resource:("arn:aws:s3:::"+$bucket+"/training/*")
      }
    ]
  }' > "$IRSA_LAB_DIR/s3-policy.json" || exit 1

# Stop on creation failure; never attach this policy to a pre-existing role.
aws iam create-role --role-name "${IRSA_ROLE_NAME:?}" \
  --assume-role-policy-document "file://$IRSA_LAB_DIR/trust.json" \
  --tags "Key=TrainingLab,Value=${IRSA_LAB_ID:?}" \
  --query Role --output json > "$IRSA_LAB_DIR/created-role.json" || exit 1
IRSA_ROLE_ARN=$(jq -er '.Arn' "$IRSA_LAB_DIR/created-role.json") || exit 1
IRSA_ROLE_ID=$(jq -er '.RoleId' "$IRSA_LAB_DIR/created-role.json") || exit 1
jq -n --arg namespace "$IRSA_NAMESPACE" --arg uid "${IRSA_NAMESPACE_UID:?}" \
  --arg roleName "$IRSA_ROLE_NAME" --arg roleArn "$IRSA_ROLE_ARN" --arg roleId "$IRSA_ROLE_ID" \
  '{namespace:$namespace,namespaceUID:$uid,roleName:$roleName,roleARN:$roleArn,roleID:$roleId}' \
  > "$IRSA_LAB_DIR/ownership.json" || exit 1
aws iam put-role-policy --role-name "$IRSA_ROLE_NAME" \
  --policy-name ScopedTrainingS3Read \
  --policy-document "file://$IRSA_LAB_DIR/s3-policy.json" || exit 1
```

El rol debe ser nuevo. Si falla su creación, el script se detiene antes de adjuntar la política y registra el `RoleId` IAM inmutable para la limpieza. Así se evita adjuntar la política del laboratorio a un rol existente que casualmente tenga el mismo nombre.

**3. Crear la cuenta de servicio y un Pod de prueba de corta duración.** Tres contenedores comprueban la identidad del llamador, enumeran como máximo un objeto del prefijo permitido y leen los metadatos del objeto seleccionado. El ejemplo solo muestra recuentos/longitudes y registra metadatos de identidad; no imprime tokens, claves secretas ni contenido de objetos.

```bash
# JSON construction preserves literal object keys and prevents YAML interpolation errors.
jq -n --arg ns "${IRSA_NAMESPACE:?}" --arg sa "${IRSA_SERVICE_ACCOUNT:?}" \
  --arg role "${IRSA_ROLE_ARN:?}" --arg region "${EXAMPLE_REGION:?}" \
  --arg bucket "${S3_BUCKET:?}" --arg key "${S3_TEST_KEY:?}" '
  {
    apiVersion:"v1",kind:"List",items:[
      {
        apiVersion:"v1",kind:"ServiceAccount",
        metadata:{name:$sa,namespace:$ns,annotations:{
          "eks.amazonaws.com/role-arn":$role,
          "eks.amazonaws.com/sts-regional-endpoints":"true"
        }}
      },
      {
        apiVersion:"v1",kind:"Pod",metadata:{name:"irsa-check",namespace:$ns},
        spec:{
          serviceAccountName:$sa,nodeSelector:{"kubernetes.io/os":"linux"},restartPolicy:"Never",
          containers:[
            {name:"identity",args:["--region",$region,"sts","get-caller-identity"]},
            {name:"list-prefix",args:["--region",$region,"s3api","list-objects-v2","--bucket",$bucket,
              "--prefix","training/","--max-keys","1","--query","KeyCount","--output","json"]},
            {name:"object-metadata",args:["--region",$region,"s3api","head-object","--bucket",$bucket,
              "--key",$key,"--query","ContentLength","--output","json"]}
          ] | map(.+{
            image:"public.ecr.aws/aws-cli/aws-cli:2.36.43",command:["aws"],
            resources:{requests:{cpu:"100m",memory:"128Mi"},limits:{memory:"256Mi"}}
          })
        }
      }
    ]
  }' > "${IRSA_LAB_DIR:?}/workload.json" || exit 1
kubectl --kubeconfig "${IRSA_KUBECONFIG:?}" create -f "$IRSA_LAB_DIR/workload.json" || exit 1
kubectl --kubeconfig "$IRSA_KUBECONFIG" -n "$IRSA_NAMESPACE" \
  wait --for=jsonpath='{.status.phase}'=Succeeded pod/irsa-check --timeout=180s || exit 1
kubectl --kubeconfig "$IRSA_KUBECONFIG" -n "$IRSA_NAMESPACE" \
  logs irsa-check -c identity > "$IRSA_LAB_DIR/pod-identity.json" || exit 1
jq -e --arg account "${IRSA_ACCOUNT_ID:?}" --arg role "${IRSA_ROLE_NAME:?}" \
  '.Account == $account and (.Arn | startswith("arn:aws:sts::"+$account+":assumed-role/"+$role+"/"))' \
  "$IRSA_LAB_DIR/pod-identity.json" >/dev/null || exit 1
kubectl --kubeconfig "$IRSA_KUBECONFIG" -n "$IRSA_NAMESPACE" logs irsa-check -c list-prefix
kubectl --kubeconfig "$IRSA_KUBECONFIG" -n "$IRSA_NAMESPACE" logs irsa-check -c object-metadata
```

Los tres contenedores deben tener éxito y la comprobación de identidad debe coincidir con la cuenta y el rol previstos. La identidad del rol del nodo es un fallo. Si falla el Pod, inspecciona el estado/registros de cada contenedor, la confianza IAM, el prefijo, las políticas del bucket/clave y la conectividad; no soluciones un error de autorización adjuntando `AmazonS3ReadOnlyAccess`.

Los cambios de IAM pueden tardar en propagarse. Tras resolver la causa, recrea deliberadamente el Pod de prueba en el namespace que controlas, en vez de asumir que la ejecución fallida original demostró el éxito. Que una operación permitida funcione no demuestra que todas las demás estén denegadas; revisa todas las políticas IAM/de recursos aplicables y realiza pruebas negativas autorizadas si son necesarias.

**4. Limpiar el namespace y el rol que controlas.** El UID del namespace y el `RoleId` IAM evitan confusiones cuando se reutilizan nombres. Si el namespace ya no existe, la limpieza puede continuar con el rol registrado. Las políticas en línea inesperadas o las búsquedas fallidas detienen la limpieza posterior; inspecciona los fallos parciales en vez de borrar recursos ajenos.

```bash
# Recover the recorded values from ownership.json if this is a later shell.
IRSA_CLEANUP_NAMESPACE_OK=false
if CURRENT_IRSA_UID=$(kubectl --kubeconfig "${IRSA_KUBECONFIG:?}" \
  get namespace "${IRSA_NAMESPACE:?}" --ignore-not-found -o jsonpath='{.metadata.uid}'); then
  if [ -z "$CURRENT_IRSA_UID" ]; then
    IRSA_CLEANUP_NAMESPACE_OK=true
  elif [ "$CURRENT_IRSA_UID" = "${IRSA_NAMESPACE_UID:?Recorded UID required}" ]; then
    if kubectl --kubeconfig "$IRSA_KUBECONFIG" delete namespace "$IRSA_NAMESPACE" --wait=true; then
      IRSA_CLEANUP_NAMESPACE_OK=true
    else
      exit 1
    fi
  else
    printf '%s\n' 'Namespace UID mismatch; stop and inspect.' >&2
    exit 1
  fi
else
  printf '%s\n' 'Namespace lookup failed; stop and inspect.' >&2
  exit 1
fi

if [ "$IRSA_CLEANUP_NAMESPACE_OK" = true ]; then
  CURRENT_IRSA_ROLE_JSON=$(aws iam get-role --role-name "${IRSA_ROLE_NAME:?}" \
    --query Role --output json) || exit 1
  CURRENT_IRSA_ROLE_ID=$(printf '%s' "$CURRENT_IRSA_ROLE_JSON" | jq -er '.RoleId') || exit 1
  if [ "$CURRENT_IRSA_ROLE_ID" = "${IRSA_ROLE_ID:?Recorded IAM RoleId required}" ]; then
    IRSA_INLINE_POLICIES=$(aws iam list-role-policies --role-name "$IRSA_ROLE_NAME" \
      --query PolicyNames --output json) || exit 1
    printf '%s' "$IRSA_INLINE_POLICIES" |
      jq -e 'all(.[]; . == "ScopedTrainingS3Read")' >/dev/null || exit 1
    if printf '%s' "$IRSA_INLINE_POLICIES" | jq -e 'index("ScopedTrainingS3Read") != null' >/dev/null; then
      aws iam delete-role-policy --role-name "$IRSA_ROLE_NAME" \
        --policy-name ScopedTrainingS3Read || exit 1
    fi
    aws iam delete-role --role-name "$IRSA_ROLE_NAME"
  else
    printf '%s\n' 'IAM RoleId mismatch; no IAM deletion attempted.' >&2
    exit 1
  fi
fi
```

Se conservan el clúster, su proveedor OIDC compartido, el bucket y sus objetos. Verifica la eliminación del namespace/rol y guarda el registro de titularidad si falla algún paso. Detener los Pods no implica que todas las credenciales STS emitidas con anterioridad se invaliden instantáneamente.

Esta auditoría no aprovisionó el rol ni ejecutó el Pod contra AWS. Las comprobaciones locales validan los manifiestos/políticas generados y las protecciones ante fallos; la propagación IAM, el alcance de red y el acceso S3 reales dependen del entorno.

Referencias: [configuración de roles IRSA](https://docs.aws.amazon.com/eks/latest/userguide/associate-service-account-role.html), [conectividad privada de IRSA](https://docs.aws.amazon.com/eks/latest/userguide/private-clusters.html), [condiciones de políticas S3](https://docs.aws.amazon.com/AmazonS3/latest/userguide/amazon-s3-policy-keys.html).

</details>

### Ejercicio 2: Reforzar la seguridad del clúster EKS

**Escenario:** evalúa controles de seguridad concretos en un clúster EKS 1.36 de formación dedicado. Es un ejercicio de integración, no una configuración probada y lista para producción.

**Requisitos previos:** administración autorizada del clúster, AWS CLI v2, kubectl y jq; nodos Linux EC2 compatibles; VPC CNI administrado por EKS con políticas de red habilitadas y compatible; y Pods de CoreDNS convencionales en `kube-system`. Usa los requisitos actuales del CNI/kernel indicados en la pregunta básica 3. El ejemplo exige que funcione la comunicación básica entre Pods; las políticas existentes de toda la organización pueden requerir otro diseño de prueba aprobado. No instales un segundo CNI solo para este ejercicio.

<details>
<summary>Mostrar solución</summary>

**1. Inspeccionar el destino y guardar su configuración actual.** Define un CIDR de salida administrativa realmente autorizado, no los rangos reservados para documentación que aparecen en otros lugares. Este ejemplo comprueba EKS 1.36 y que la configuración de políticas del CNI administrado esté habilitada antes de continuar.

```bash
: "${EXAMPLE_CLUSTER:?Use a dedicated EKS 1.36 training cluster}"
: "${EXAMPLE_REGION:?}"
: "${APPROVED_API_CIDR:?Actual approved administration egress CIDR}"
SECURITY_LAB_DIR=$(mktemp -d /tmp/eks-security-lab.XXXXXX)
: "${SECURITY_LAB_DIR:?}"
SECURITY_NAMESPACE="security-quiz-$(date +%s)-$$"
SECURITY_KUBECONFIG="$SECURITY_LAB_DIR/kubeconfig"

aws eks describe-cluster --name "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION" \
  --query cluster --output json > "$SECURITY_LAB_DIR/before-cluster.json" || exit 1
jq -e '.version == "1.36" and .status == "ACTIVE"' \
  "$SECURITY_LAB_DIR/before-cluster.json" >/dev/null || exit 1
aws eks describe-addon --cluster-name "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION" \
  --addon-name vpc-cni --query addon --output json > "$SECURITY_LAB_DIR/cni.json" || exit 1
jq -e '(.configurationValues // "{}" | fromjson | .enableNetworkPolicy) as $enabled |
  .status == "ACTIVE" and ($enabled == true or $enabled == "true")' \
  "$SECURITY_LAB_DIR/cni.json" >/dev/null || exit 1
aws eks update-kubeconfig --name "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION" \
  --kubeconfig "$SECURITY_KUBECONFIG" --alias "$EXAMPLE_CLUSTER" || exit 1

# Serialize cluster configuration updates. A timeout does not cancel an AWS update.
security_wait_update() {
  local update_id="$1" status attempt
  for ((attempt=1; attempt<=60; attempt++)); do
    status=$(aws eks describe-update --name "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION" \
      --update-id "$update_id" --query update.status --output text) || return 1
    case "$status" in
      Successful) return 0 ;;
      Failed|Cancelled)
        printf 'EKS update %s ended as %s\n' "$update_id" "$status" >&2
        return 1 ;;
      InProgress) sleep 10 ;;
      *) printf 'Unexpected EKS update status: %s\n' "$status" >&2; return 1 ;;
    esac
  done
  printf '%s\n' 'Update still pending; inspect it before another configuration change.' >&2
  return 1
}
```

**2. Aplicar en serie los ajustes revisados de endpoint/registros.** Lo siguiente conserva ambas rutas de API y restringe la ruta pública al CIDR aprobado. Antes de elegir la alternativa solo privada, verifica por separado el enrutamiento/DNS/acceso a la API privados, como se describe en la Parte 1. Un timeout del auxiliar de espera no cancela la actualización de AWS; inspecciónala antes de enviar otro cambio.

EKS 1.36 ya cifra mediante cifrado de sobre los datos de la API de Kubernetes, incluidos Secrets. Que la configuración de una clave administrada por el cliente esté vacía no demuestra que los datos se almacenen en texto claro. No crees otro clúster ni dupliques claves KMS para este paso. Si se necesita una CMK, sigue el procedimiento revisado y las precauciones de ciclo de vida de claves de la pregunta básica 4.

```bash
# Keep both API paths; the supplied CIDR must include the intended administration path.
SECURITY_ENDPOINT_UPDATE=$(aws eks update-cluster-config \
  --name "${EXAMPLE_CLUSTER:?}" --region "${EXAMPLE_REGION:?}" \
  --resources-vpc-config "endpointPublicAccess=true,endpointPrivateAccess=true,publicAccessCidrs=${APPROVED_API_CIDR:?}" \
  --query update.id --output text) || exit 1
security_wait_update "$SECURITY_ENDPOINT_UPDATE" || exit 1
kubectl --kubeconfig "${SECURITY_KUBECONFIG:?}" get nodes || exit 1

# EKS 1.36 already has default envelope encryption; inspect rather than create a new cluster.
aws eks describe-cluster --name "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION" \
  --query 'cluster.{version:version,encryption:encryptionConfig}'

SECURITY_LOGGING_UPDATE=$(aws eks update-cluster-config \
  --name "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION" \
  --logging '{"clusterLogging":[{"types":["api","audit","authenticator","controllerManager","scheduler"],"enabled":true}]}' \
  --query update.id --output text) || exit 1
security_wait_update "$SECURITY_LOGGING_UPDATE" || exit 1
aws eks describe-cluster --name "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION" \
  --query cluster.logging
```

Los registros del plano de control tienen costes de CloudWatch y se entregan con esfuerzo razonable, no garantizado. Confirma que los tipos previstos lleguen a `/aws/eks/<cluster-name>/cluster` y configura la retención/controles de acceso. Las restricciones del endpoint complementan la autorización de IAM/Kubernetes, pero no la sustituyen.

**3. Crear un namespace Restricted aislado y probar las cargas.** Los tres Deployments crean Pods administrados por controladores, para probar de manera fiable las políticas del CNI de VPC. Usan un usuario no root, seccomp RuntimeDefault, capacidades descartadas, sistema de archivos raíz de solo lectura y un `emptyDir` para los archivos temporales del backend. No necesitan un token de API de cuenta de servicio.

```bash
jq -n --arg ns "${SECURITY_NAMESPACE:?}" '{
  apiVersion:"v1",kind:"Namespace",metadata:{name:$ns,labels:{
    "pod-security.kubernetes.io/enforce":"restricted",
    "pod-security.kubernetes.io/enforce-version":"v1.36",
    "pod-security.kubernetes.io/audit":"restricted",
    "pod-security.kubernetes.io/audit-version":"v1.36",
    "pod-security.kubernetes.io/warn":"restricted",
    "pod-security.kubernetes.io/warn-version":"v1.36"
  }}
}' > "${SECURITY_LAB_DIR:?}/namespace.json" || exit 1
kubectl --kubeconfig "${SECURITY_KUBECONFIG:?}" \
  create -f "$SECURITY_LAB_DIR/namespace.json" || exit 1
SECURITY_NAMESPACE_UID=$(kubectl --kubeconfig "$SECURITY_KUBECONFIG" \
  get namespace "$SECURITY_NAMESPACE" -o jsonpath='{.metadata.uid}') || exit 1
: "${SECURITY_NAMESPACE_UID:?}"
jq -n --arg ns "$SECURITY_NAMESPACE" --arg uid "$SECURITY_NAMESPACE_UID" \
  '{namespace:$ns,uid:$uid}' > "$SECURITY_LAB_DIR/namespace-owner.json" || exit 1

jq -n --arg ns "$SECURITY_NAMESPACE" '
  def deployment($name;$command):
    {
      apiVersion:"apps/v1",kind:"Deployment",metadata:{name:$name,namespace:$ns},
      spec:{replicas:1,selector:{matchLabels:{app:$name}},template:{
        metadata:{labels:{app:$name}},
        spec:{
          nodeSelector:{"kubernetes.io/os":"linux"},
          automountServiceAccountToken:false,
          securityContext:{
            runAsNonRoot:true,runAsUser:1000,runAsGroup:1000,fsGroup:1000,
            seccompProfile:{type:"RuntimeDefault"}
          },
          volumes:[{name:"tmp",emptyDir:{}}],
          containers:[({
            name:"app",image:"busybox:1.37",command:$command,
            securityContext:{
              allowPrivilegeEscalation:false,readOnlyRootFilesystem:true,
              capabilities:{drop:["ALL"]}
            },
            volumeMounts:[{name:"tmp",mountPath:"/tmp"}],
            resources:{requests:{cpu:"50m",memory:"32Mi"},limits:{memory:"64Mi"}}
          } + if $name == "backend" then {
            ports:[{name:"http",containerPort:8080}],
            readinessProbe:{httpGet:{path:"/",port:8080}}
          } else {} end)]
        }
      }}
    };
  {
    apiVersion:"v1",kind:"List",items:[
      deployment("backend";["sh","-c","mkdir -p /tmp/www && printf \"policy-test-ok\\n\" > /tmp/www/index.html && exec httpd -f -p 8080 -h /tmp/www"]),
      deployment("frontend";["sleep","3600"]),
      deployment("outsider";["sleep","3600"]),
      {
        apiVersion:"v1",kind:"Service",metadata:{name:"backend",namespace:$ns},
        spec:{selector:{app:"backend"},ports:[{name:"http",port:8080,targetPort:8080}]}
      }
    ]
  }' > "$SECURITY_LAB_DIR/workloads.json" || exit 1
kubectl --kubeconfig "$SECURITY_KUBECONFIG" create -f "$SECURITY_LAB_DIR/workloads.json" || exit 1
for app in backend frontend outsider; do
  kubectl --kubeconfig "$SECURITY_KUBECONFIG" -n "$SECURITY_NAMESPACE" \
    rollout status "deployment/$app" --timeout=180s || exit 1
done

# Establish baseline connectivity before applying the policies.
kubectl --kubeconfig "$SECURITY_KUBECONFIG" -n "$SECURITY_NAMESPACE" \
  exec deployment/frontend -- wget -qO- -T 5 http://backend:8080/ || exit 1
kubectl --kubeconfig "$SECURITY_KUBECONFIG" -n "$SECURITY_NAMESPACE" \
  exec deployment/outsider -- wget -qO- -T 5 http://backend:8080/ || exit 1
```

Ambos clientes deben llegar al backend antes de aplicar las políticas. Si falla la conectividad básica, resuélvelo primero; no interpretes ese fallo como prueba de aplicación de NetworkPolicy.

**4. Aplicar denegación predeterminada y reglas de autorización necesarias.** Este es el mismo diseño de política de la pregunta básica 3, con alcance limitado al namespace generado. Permite TCP 8080 desde frontend a backend y DNS convencional por UDP y TCP. Los puertos de servicio y contenedor coinciden.

```bash
cat > "${SECURITY_LAB_DIR:?}/networkpolicies.yaml" << EOF
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny
  namespace: ${SECURITY_NAMESPACE:?}
spec:
  podSelector: {}
  policyTypes: [Ingress, Egress]
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: backend-ingress
  namespace: ${SECURITY_NAMESPACE:?}
spec:
  podSelector:
    matchLabels:
      app: backend
  policyTypes: [Ingress]
  ingress:
    - from:
        - podSelector:
            matchLabels:
              app: frontend
      ports:
        - protocol: TCP
          port: 8080
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: frontend-egress
  namespace: ${SECURITY_NAMESPACE:?}
spec:
  podSelector:
    matchLabels:
      app: frontend
  policyTypes: [Egress]
  egress:
    - to:
        - podSelector:
            matchLabels:
              app: backend
      ports:
        - protocol: TCP
          port: 8080
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: dns-egress
  namespace: ${SECURITY_NAMESPACE:?}
spec:
  podSelector: {}
  policyTypes: [Egress]
  egress:
    - to:
        - namespaceSelector:
            matchLabels:
              kubernetes.io/metadata.name: kube-system
          podSelector:
            matchLabels:
              k8s-app: kube-dns
      ports:
        - protocol: UDP
          port: 53
        - protocol: TCP
          port: 53
EOF
kubectl --kubeconfig "${SECURITY_KUBECONFIG:?}" apply -f "$SECURITY_LAB_DIR/networkpolicies.yaml" || exit 1
```

**5. Verificar conexiones nuevas y controles positivos.** Tras la convergencia de políticas, observa la solicitud denegada del cliente no relacionado y confirma luego que funcione la solicitud autorizada de frontend y siga funcionando DNS. Estas observaciones corresponden a esta topología de prueba; si hay fallos inesperados, inspecciona el estado/registros de las políticas y agentes antes de interpretarlos.

```bash
# Wait briefly for the expected denied fresh connection; do not treat baseline failures as success.
SECURITY_DENY_OBSERVED=false
for ((attempt=1; attempt<=6; attempt++)); do
  if kubectl --kubeconfig "${SECURITY_KUBECONFIG:?}" -n "${SECURITY_NAMESPACE:?}" \
    exec deployment/outsider -- wget -qO- -T 5 http://backend:8080/ >/dev/null 2>&1; then
    sleep 2
  else
    SECURITY_DENY_OBSERVED=true
    break
  fi
done
[ "$SECURITY_DENY_OBSERVED" = true ] || {
  printf '%s\n' 'Expected deny was not observed; inspect policy enforcement.' >&2
  exit 1
}

# Positive controls after the denial: allowed application traffic and DNS must still work.
kubectl --kubeconfig "$SECURITY_KUBECONFIG" -n "$SECURITY_NAMESPACE" \
  exec deployment/frontend -- wget -qO- -T 5 http://backend:8080/ || exit 1
kubectl --kubeconfig "$SECURITY_KUBECONFIG" -n "$SECURITY_NAMESPACE" \
  exec deployment/outsider -- nslookup backend || exit 1
kubectl --kubeconfig "$SECURITY_KUBECONFIG" -n "$SECURITY_NAMESPACE" get networkpolicies
```

PSA aplica el estándar Restricted del namespace. Kyverno o Gatekeeper son opcionales para requisitos que excedan PSA; usa las API actuales de la pregunta básica 6 y adapta aquí su coincidencia de namespace. Una política creada correctamente fuera de este namespace no aplicaría sus reglas a las cargas del laboratorio.

**6. Revisar controles relacionados sin sustituirlos por recetas incompletas.** Una política IAM de solo lectura `Describe*` no permite operar AWS Load Balancer Controller; usa su política oficial correspondiente a la versión y revisa las condiciones de recursos/etiquetas. Inspecciona IAM del nodo, IMDS, grupos de seguridad e identidades de complementos. `maxUnavailable` controla la disrupción de una actualización de nodo administrado ya iniciada; no programa sustituciones periódicas. Usa un plan de mantenimiento/actualización revisado por separado.

**7. Limpiar el namespace del laboratorio.** Usa el UID registrado; si falla la limpieza, conserva los archivos privados de titularidad/ajustes.

```bash
CURRENT_SECURITY_UID=$(kubectl --kubeconfig "${SECURITY_KUBECONFIG:?}" \
  get namespace "${SECURITY_NAMESPACE:?}" --ignore-not-found \
  -o jsonpath='{.metadata.uid}') || exit 1
if [ -z "$CURRENT_SECURITY_UID" ]; then
  printf '%s\n' 'Lab namespace is already absent.'
elif [ "$CURRENT_SECURITY_UID" = "${SECURITY_NAMESPACE_UID:?Recorded UID required}" ]; then
  kubectl --kubeconfig "$SECURITY_KUBECONFIG" delete namespace "$SECURITY_NAMESPACE" --wait=true
else
  printf '%s\n' 'Namespace UID mismatch; no deletion attempted.' >&2
  exit 1
fi
```

Si conservas el clúster, revisa los ajustes de endpoint/registros resultantes y la retención/coste continuos de los registros. Si eliminas el clúster de formación, sigue la guía de ciclo de vida del clúster e inspecciona los registros CloudWatch retenidos y los recursos administrados de manera independiente. No elimines una clave KMS asociada al limpiar el namespace.

Esta auditoría no realizó las actualizaciones de AWS ni ejecutó la red de Pods. Las comprobaciones locales abarcan los manifiestos generados, la lógica de políticas y las protecciones ante fallos/limpieza. IAM, enrutamiento, admisión, disponibilidad y recuperación en producción requieren verificación específica del entorno.

Referencias: [requisitos de NetworkPolicy](https://docs.aws.amazon.com/eks/latest/userguide/cni-network-policy.html), [cifrado de sobre predeterminado](https://docs.aws.amazon.com/eks/latest/userguide/envelope-encryption.html), [acceso al endpoint de la API](https://docs.aws.amazon.com/eks/latest/userguide/cluster-endpoint.html), [registros del plano de control](https://docs.aws.amazon.com/eks/latest/userguide/control-plane-logs.html), [Pod Security Standards](https://kubernetes.io/docs/concepts/security/pod-security-standards/).

</details>

## Temas avanzados

Las siguientes preguntas tratan temas avanzados de la creación de clústeres de Amazon EKS y evalúan tu comprensión de sus conceptos y prácticas recomendadas.

1. ¿Cuál de las siguientes NO es un requisito para un clúster EKS IPv6?
   * A) VPC/subredes con direccionamiento IPv4 e IPv6
   * B) Configuración de CNI compatible y permisos IAM IPv6
   * C) Nodos EC2 compatibles basados en Nitro o Fargate
   * D) Una familia de instancias EC2 independiente y solo IPv6

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: D) Una familia de instancias EC2 independiente y solo IPv6**

EKS no exige una «familia de instancias solo IPv6» independiente. Sí requiere **nodos EC2 compatibles basados en Nitro o Fargate**, por lo que es incorrecto afirmar que funciona cualquier tipo de instancia EC2 ordinario.

**Requisitos previos:**

1. Selecciona la familia IP IPv6 al crear un clúster **nuevo**. Es inmutable; cambiar `ENABLE_IPV6` en un clúster IPv4 existente no lo convierte.
2. Asocia CIDR IPv4 e IPv6 a la VPC/subredes y habilita la asignación automática de IPv6 en las subredes de nodos. Revisa rutas IPv6, grupos de seguridad, DNS y conectividad de administración. Los ID de subred deben corresponder a las VPC/AZ previstas.
3. Usa una versión compatible de VPC CNI configurada para IPv6 y delegación de prefijos. La versión 1.10.1 es el mínimo histórico, no una instalación recomendada actualmente. No apliques un manifiesto antiguo 1.10 encima de un complemento administrado actual.
4. Proporciona los permisos IAM IPv6 del CNI, preferiblemente mediante su propio rol de carga de trabajo. La política IPv4 `AmazonEKS_CNI_Policy` no es la política IPv6. Revisa el rol/políticas generados por el flujo IPv6/complemento de eksctl.

```bash
aws ec2 describe-subnets --region "${EXAMPLE_REGION:?}" \
  --subnet-ids "${PRIVATE_SUBNET_A:?}" "${PRIVATE_SUBNET_B:?}" \
  --query 'Subnets[].{id:SubnetId,az:AvailabilityZone,ipv4:CidrBlock,ipv6:Ipv6CidrBlockAssociationSet,autoIPv6:AssignIpv6AddressOnCreation}'
aws eks describe-addon-versions --region "$EXAMPLE_REGION" \
  --addon-name vpc-cni --kubernetes-version 1.36
```

**Ejemplo:** usa subredes privadas de doble pila ya preparadas y un grupo de nodos AL2023 basado en Nitro. Sustituye los ID de ejemplo y el CIDR de acceso público. La escritura `kubernetesNetworkConfig.ipFamily: IPv6` es correcta para eksctl; la API de EKS usa `ipv6` en minúsculas.

```yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: ipv6-lab
  region: us-west-2
  version: "1.36"
kubernetesNetworkConfig:
  ipFamily: IPv6
vpc:
  id: vpc-0123456789abcdef0
  subnets:
    private:
      us-west-2a:
        id: subnet-0123456789abcdef0
      us-west-2b:
        id: subnet-0123456789abcdef1
  clusterEndpoints:
    publicAccess: true
    privateAccess: true
  publicAccessCIDRs:
    - 203.0.113.10/32
iam:
  withOIDC: true
addons:
  - name: vpc-cni
  - name: coredns
  - name: kube-proxy
managedNodeGroups:
  - name: ipv6-ng
    amiFamily: AmazonLinux2023
    instanceType: m5.large
    privateNetworking: true
    desiredCapacity: 2
    minSize: 2
    maxSize: 4
```

Guarda la configuración revisada como `ipv6-cluster.yaml`. Selecciona y registra las versiones exactas de complementos compatibles con tu entorno; omitir las versiones anteriores permite que la herramienta elija valores predeterminados compatibles. Esto no afirma que se deba instalar una versión histórica específica de CNI.

```bash
# After reviewing real IDs, routing, IAM, access and compatible addon versions.
eksctl create cluster -f ipv6-cluster.yaml --kubeconfig "${EXAMPLE_KUBECONFIG:?}"
```

La configuración no prepara por sí misma los atributos/rutas IPv6 de las subredes existentes. Confirma las entradas de acceso creadas y los permisos del CNI, así como la preparación de nodos/complementos. Esta auditoría no creó un clúster IPv6.

**Direccionamiento y tráfico:**

- EKS expone direcciones IPv6 de Pods y asigna ClusterIP IPv6. Una VPC de doble pila no convierte Pods/Services de EKS en doble pila.
- Las direcciones IPv6 de Pods proceden del direccionamiento de la subred; las direcciones IPv6 de Service usan un rango local único asignado por EKS dentro de `fc00::/7`. No supongas un CIDR de servicio fijo `fd00::/108`.
- Los nodos EC2 tienen direcciones IPv4 e IPv6. Un Pod también puede recibir una dirección IPv4 local del host que no se muestra para llegar a destinos IPv4 externos, con NAT de origen a través del nodo. El acceso IPv4 a Internet de nodos privados aún puede requerir NAT; IPv6 no elimina todas las dependencias de NAT.
- El tráfico IPv6 nativo a Internet puede usar un internet gateway o un egress-only internet gateway, según el sentido previsto y el diseño de seguridad. El gateway de solo salida no es obligatorio en todos los clústeres IPv6.
- El balanceo hacia Pods IPv6 requiere una configuración compatible de controlador/balanceador con destinos IP. Un frontend apropiado de doble pila aún puede atender clientes IPv4; no confundas el direccionamiento del Pod con la familia IP del cliente.
- Windows y el networking personalizado de VPC CNI no son compatibles con clústeres EKS IPv6. Comprueba la compatibilidad de controladores de almacenamiento, complementos y dependencias externas antes de elegir la familia.

```bash
aws eks describe-cluster --name "${IPV6_CLUSTER_NAME:?}" \
  --region "${EXAMPLE_REGION:?}" --query cluster.kubernetesNetworkConfig
kubectl --kubeconfig "${EXAMPLE_KUBECONFIG:?}" -n kube-system get pods -o wide
kubectl --kubeconfig "$EXAMPLE_KUBECONFIG" -n kube-system get services -o wide
kubectl --kubeconfig "$EXAMPLE_KUBECONFIG" get nodes -o wide
```

Inspecciona las direcciones reales y prueba DNS y destinos IPv6/IPv4 necesarios. Enumerar direcciones IPv6 no demuestra conectividad ni disponibilidad. Limpia únicamente los recursos de laboratorio registrados según el procedimiento de ciclo de vida del clúster.

Referencias: [comportamiento IPv6 de EKS](https://docs.aws.amazon.com/eks/latest/userguide/cni-ipv6.html), [tutorial IPv6 de eksctl](https://docs.aws.amazon.com/eks/latest/userguide/deploy-ipv6-cluster.html), [rol IAM del CNI](https://docs.aws.amazon.com/eks/latest/userguide/cni-iam-role.html), [respuesta de configuración de red](https://docs.aws.amazon.com/eks/latest/APIReference/API_KubernetesNetworkConfigResponse.html).

</details>

2. ¿Qué permite principalmente el networking personalizado de VPC CNI?
   * A) Subredes/grupos de seguridad de Pods distintos de la interfaz principal del nodo dentro de la misma VPC
   * B) Evitar automáticamente cualquier solapamiento de CIDR
   * C) Cifrar todas las conexiones entre nodos
   * D) Acelerar la reconciliación del plano de control

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A) Subredes/grupos de seguridad de Pods distintos de la interfaz principal del nodo dentro de la misma VPC**

El networking personalizado de VPC CNI permite que los Pods Linux IPv4 en EC2 utilicen **subredes/grupos de seguridad alternativos dentro de la misma VPC que sus nodos**. El rango de los Pods no queda fuera de los CIDR asociados a la VPC. Un CIDR secundario de VPC puede aportar espacio de direcciones, pero su uso no evita automáticamente el solapamiento con otras redes.

De forma predeterminada, VPC CNI crea ENI secundarias en la subred principal del nodo y utiliza direcciones de esas ENI y de las direcciones aptas de la ENI principal. Con networking personalizado, las IP normales de Pods proceden de ENI secundarias configuradas mediante `ENIConfig`; no se usa la ENI principal para asignarlas. Los Pods `hostNetwork` siguen usando la red del host.

**Secuencia de configuración:**

1. Planifica el espacio IPv4 disponible, el enrutamiento y los permisos. Si agregas un CIDR secundario, comprueba las restricciones de asociación de VPC y el solapamiento con redes conectadas. Los ejemplos de espacio compartido `100.64.0.0/10` de AWS no garantizan que ese rango esté libre en tu entorno.
2. Prepara subredes alternativas de Pods en la **misma VPC y AZ correspondiente** a cada subred principal de nodo. Revisa rutas de subred y reglas de grupos de seguridad, incluidas dependencias de API/DNS/cargas de trabajo.
3. Crea un `ENIConfig` por cada subred de Pod prevista. Lo siguiente usa una subred por AZ; sustituye todos los ID. No sobrescribas configuraciones de alcance de clúster que pertenezcan a otro despliegue.

```yaml
apiVersion: crd.k8s.amazonaws.com/v1alpha1
kind: ENIConfig
metadata:
  name: us-west-2a
spec:
  subnet: subnet-0123456789abcdef0
  securityGroups:
    - sg-0123456789abcdef0
---
apiVersion: crd.k8s.amazonaws.com/v1alpha1
kind: ENIConfig
metadata:
  name: us-west-2b
spec:
  subnet: subnet-0123456789abcdef1
  securityGroups:
    - sg-0123456789abcdef0
```

4. Configura networking personalizado y la selección de ENIConfig usando el responsable de la instalación del CNI. Si es un complemento administrado por EKS, combina estos ajustes de entorno con la configuración completa revisada después de comprobar el esquema de la versión instalada:

```yaml
# Merge with existing managed-addon configuration; do not discard other env values.
env:
  AWS_VPC_K8S_CNI_CUSTOM_NETWORK_CFG: "true"
  ENI_CONFIG_LABEL_DEF: topology.kubernetes.io/zone
```

Para un DaemonSet autoadministrado, la actualización equivalente es la siguiente. Afecta al comportamiento del CNI de todo el clúster y debe formar parte de una migración planificada, no de un despliegue de aplicación informal:

```bash
# Self-managed CNI alternative, after preparing ENIConfig/subnets and a rollout plan.
# For an EKS-managed addon, use its supported configuration-values workflow instead.
kubectl --kubeconfig "${EXAMPLE_KUBECONFIG:?}" -n kube-system \
  set env daemonset/aws-node AWS_VPC_K8S_CNI_CUSTOM_NETWORK_CFG=true \
  ENI_CONFIG_LABEL_DEF=topology.kubernetes.io/zone
kubectl --kubeconfig "$EXAMPLE_KUBECONFIG" -n kube-system \
  rollout status daemonset/aws-node --timeout=5m
```

5. Aprovisiona y valida nodos de sustitución con la configuración necesaria; luego migra las cargas con vaciado que tenga en cuenta los PDB y con pruebas de aplicaciones. Cambiar las variables de entorno no reasigna las direcciones de Pods existentes. AWS recomienda nodos nuevos para configurar networking personalizado. Conserva la capacidad anterior hasta verificar la migración.

Al usar `ENI_CONFIG_LABEL_DEF=topology.kubernetes.io/zone`, asigna a cada `ENIConfig` el nombre de esa AZ. Si necesitas varias subredes de Pod en una AZ, usa nombres únicos y una asignación revisada de etiqueta/anotación de nodo personalizada. La selección mediante anotación `ENIConfig` existente puede prevalecer sobre la selección por etiqueta. No cambies la etiqueta topológica real de un nodo para forzarlo a usar una subred de otra AZ.

**Límites de capacidad y seguridad:**

- Excluir la ENI principal reduce la capacidad de Pods en modo de IP secundaria. La delegación de prefijos puede aumentarla, pero siguen importando la disponibilidad de prefijos en la subred, los límites compatibles de la instancia y `maxPods` de kubelet. Calcula y prueba la densidad; no copies un valor universal.
- Con `AWS_VPC_K8S_CNI_EXTERNALSNAT=false` (valor predeterminado), el tráfico fuera de los CIDR asociados a la VPC recibe NAT de origen mediante la interfaz principal del nodo y usa su subred/grupos de seguridad. No supongas que el grupo de seguridad de ENIConfig filtra todos los flujos externos.
- Al combinarlo con Security Groups for Pods, el grupo de `SecurityGroupPolicy` del Pod tiene prioridad sobre el grupo de ENIConfig para ese Pod. Comprueba los modos de aplicación/SNAT compatibles.
- El networking personalizado no cifra el tráfico ni establece por sí solo una frontera de aislamiento entre tenants, y no resuelve rutas con CIDR solapados sin un diseño de red apropiado.
- No es compatible con EKS IPv6 ni nodos Windows. Fargate selecciona subredes mediante sus perfiles, no con los mapeos ENIConfig de nodos EC2.

```bash
kubectl --kubeconfig "${EXAMPLE_KUBECONFIG:?}" get eniconfigs
kubectl --kubeconfig "$EXAMPLE_KUBECONFIG" get nodes -L topology.kubernetes.io/zone
kubectl --kubeconfig "$EXAMPLE_KUBECONFIG" -n "${APPLICATION_NAMESPACE:?}" get pods -o wide
aws ec2 describe-subnets --region "${EXAMPLE_REGION:?}" \
  --subnet-ids "${POD_SUBNET_A:?}" "${POD_SUBNET_B:?}" \
  --query 'Subnets[].{id:SubnetId,vpc:VpcId,az:AvailabilityZone,cidr:CidrBlock,free:AvailableIpAddressCount}'
```

Verifica las IP de Pods con las subredes previstas, las AZ de nodo, la conectividad DNS/API y los flujos requeridos de aplicaciones. Enumerar `ENIConfig` no demuestra migración ni aislamiento. Este ejemplo se revisó estáticamente; no se cambió CNI, migró ningún nodo ni ejecutó una prueba de rendimiento de red.

Referencias: [networking personalizado](https://docs.aws.amazon.com/eks/latest/userguide/cni-custom-network.html), [configuración y migración](https://docs.aws.amazon.com/eks/latest/userguide/cni-custom-network-tutorial.html), [consideraciones sobre networking personalizado](https://docs.aws.amazon.com/eks/latest/best-practices/custom-networking.html).

</details>

3. ¿Cuál NO es un requisito para ejecutar cargas de trabajo Windows en EKS?
   * A) Al menos dos grupos de nodos administrados de Amazon Linux
   * B) Capacidad Linux o Fargate para Pods del sistema que solo se ejecutan en Linux
   * C) Una AMI Windows e imagen de contenedor compatibles
   * D) IPAM de Windows y autenticación/IAM de nodo correctos

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A) Al menos dos grupos de nodos administrados de Amazon Linux**

No se exigen dos grupos de nodos administrados de Amazon Linux. EKS sí necesita **capacidad Linux o Fargate para Pods del sistema que solo se ejecutan en Linux, como CoreDNS**; esto no requiere una distribución Linux específica ni dos grupos separados. Planifica réplicas y ubicación entre dominios de fallo para la disponibilidad; no confundas el mínimo con un diseño de alta disponibilidad.

**Requisitos previos de Windows:**

1. Usa un clúster IPv4 de EKS actualmente compatible y una AMI de Windows optimizada para EKS compatible. AWS publica variantes Windows Server 2019, 2022 y 2025; este ejemplo usa deliberadamente 2022, no una línea base obsoleta de Kubernetes 1.14/1.23.
2. Confirma los permisos `AmazonEKSVPCResourceController` en el rol IAM del clúster y habilita IPAM de Windows en la configuración `kube-system/amazon-vpc-cni`.
3. Deja que el controlador de recursos VPC administrado por EKS haga IPAM de Windows. No instales manifiestos antiguos del controlador de recursos/admission-webhook del plano de datos desde una URL `master` flotante.
4. Usa un rol IAM de nodo Windows dedicado y la autenticación de nodo correcta. La autenticación API usa una entrada de acceso `EC2_WINDOWS`; los grupos de nodos administrados gestionan sus entradas de acceso de nodo. Con `aws-auth` heredado, conserva el grupo requerido `eks:kube-proxy-windows` además de los grupos de nodo/arranque.

```bash
aws iam list-attached-role-policies --role-name "${EKS_CLUSTER_ROLE_NAME:?}"

# If missing, attach to the reviewed cluster role, not to every worker role.
aws iam attach-role-policy --role-name "$EKS_CLUSTER_ROLE_NAME" \
  --policy-arn arn:aws:iam::aws:policy/AmazonEKSVPCResourceController
```

El ajuste de IPAM de Windows pertenece a la configuración existente de VPC CNI. Si EKS o Helm lo administra, usa los ajustes compatibles de ese responsable en vez de reemplazar todo el ConfigMap:

```yaml
# Relevant ConfigMap data; merge through the owning addon/Helm configuration.
data:
  enable-windows-ipam: "true"
```

**Ejemplo de grupo de nodos:** guarda esto como `windows-nodegroup.yaml` después de revisar el clúster existente, las subredes, disponibilidad de AMI e IAM. El taint impide que cargas Linux normales terminen accidentalmente en esos nodos; las plantillas de cargas Linux también deben seleccionar Linux explícitamente.

```yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: my-cluster
  region: us-west-2
managedNodeGroups:
  - name: windows-ng
    amiFamily: WindowsServer2022FullContainer
    instanceType: m5.large
    desiredCapacity: 2
    minSize: 2
    maxSize: 4
    privateNetworking: true
    taints:
      - key: example.com/os
        value: windows
        effect: NoSchedule
```

```bash
# Existing, supported IPv4 cluster with Windows IPAM and IAM prerequisites ready.
eksctl create nodegroup -f windows-nodegroup.yaml
aws eks describe-nodegroup --cluster-name "${EXAMPLE_CLUSTER:?}" \
  --region "${EXAMPLE_REGION:?}" --nodegroup-name windows-ng \
  --query 'nodegroup.{status:status,ami:amiType,role:nodeRole,health:health}'
kubectl --kubeconfig "${EXAMPLE_KUBECONFIG:?}" get nodes \
  -l kubernetes.io/os=windows -L node.kubernetes.io/windows-build
```

**Ejemplo de carga de trabajo:** crea un namespace `windows-lab` no usado y despliega una imagen compatible con la compilación de Windows del nodo. Las AMI Windows optimizadas para EKS incluyen kubelet, **Windows kube-proxy**, containerd y otros componentes del host; kube-proxy no es exclusivo de Linux.

Usa la imagen oficial IIS con su punto de entrada ServiceMonitor existente. La ubicación retirada de descarga de ServiceMonitor `dotnetbinaries.blob.core.windows.net` ya no está disponible; aquí no hace falta instalar IIS ni descargar un binario cada vez que arranca el Pod.

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: windows-iis
  namespace: windows-lab
spec:
  replicas: 2
  selector:
    matchLabels:
      app: windows-iis
  template:
    metadata:
      labels:
        app: windows-iis
    spec:
      os:
        name: windows
      nodeSelector:
        kubernetes.io/os: windows
        kubernetes.io/arch: amd64
        node.kubernetes.io/windows-build: "10.0.20348"
      tolerations:
        - key: example.com/os
          operator: Equal
          value: windows
          effect: NoSchedule
      containers:
        - name: iis
          image: mcr.microsoft.com/windows/servercore/iis:windowsservercore-ltsc2022
          ports:
            - containerPort: 80
          startupProbe:
            httpGet:
              path: /
              port: 80
            periodSeconds: 10
            failureThreshold: 60
          readinessProbe:
            httpGet:
              path: /
              port: 80
          resources:
            requests:
              cpu: 500m
              memory: 512Mi
            limits:
              memory: 1Gi
```

La etiqueta de imagen se verificó en el README y los metadatos de registro de Microsoft. No se descargaron sus capas ni se ejecutó la carga Windows durante esta auditoría. Los valores de recursos son ilustrativos. Antes de producción, comprueba el rollout/estado, DNS, tráfico de aplicación y compatibilidad de compilación del host/contenedor reales.

**Límites de funciones compatibles:**

- Windows no se puede ejecutar como Pods de EKS Fargate, nodos EKS Auto Mode ni EKS Hybrid Nodes. No admite EKS IPv6, networking personalizado de VPC CNI ni Security Groups for Pods.
- Los Pods Windows normales difieren de los contenedores Linux privilegiados. Los Pods Windows **HostProcess** pueden usar red del host, así que es incorrecto afirmar que Windows nunca admite `hostNetwork`. HostProcess requiere una revisión de seguridad elevada independiente.
- El networking/capacidad IP de Windows difiere de Linux. Revisa límites de ENI única y delegación de prefijos compatible; no des por válidos los cálculos de densidad de Pods de Linux.
- Elige controladores de almacenamiento compatibles con Windows y valida la semántica de volúmenes/rutas. No supongas que funcionan los permisos `hostPath` de Linux ni todas las funciones CSI.
- Los nodos Windows optimizados para EKS usan containerd; las imágenes de aplicaciones Linux deben ir en nodos Linux. Verifica la ubicación de complementos del sistema y aplicaciones en clústeres con distintos sistemas operativos.

Referencias: [compatibilidad Windows en EKS](https://docs.aws.amazon.com/eks/latest/userguide/windows-support.html), [AMI Windows optimizadas](https://docs.aws.amazon.com/eks/latest/userguide/eks-optimized-windows-ami.html), [imagen IIS de Microsoft](https://github.com/microsoft/iis-docker), [Windows HostProcess](https://kubernetes.io/docs/tasks/configure-pod-container/create-hostprocess-pod/).

</details>

4. ¿Qué ajuste hace obligatorio un token de sesión para las solicitudes de metadatos de instancia EC2?
   * A) `HttpTokens=required` (solo IMDSv2)
   * B) Una regla de grupo de seguridad para `169.254.169.254`
   * C) Una etiqueta Node de Kubernetes
   * D) El nombre de una cuenta de servicio de aplicación por sí solo

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A) `HttpTokens=required` (solo IMDSv2)**

Exigir IMDSv2 (`HttpTokens: required`) deshabilita las llamadas IMDSv1 sin token y añade defensa en profundidad. **No** hace imposibles todos los SSRF ni crea una frontera de seguridad entre contenedores que comparten host.

**Ajustes de plantilla de lanzamiento:** lo siguiente es un fragmento EC2 `LaunchTemplateData`, no un campo `managedNodeGroups.metadataOptions`. El límite de saltos 1 presupone que los Pods normales usan IRSA/Pod Identity en vez de obtener credenciales del nodo:

```json
{
  "MetadataOptions": {
    "HttpTokens": "required",
    "HttpPutResponseHopLimit": 1,
    "HttpEndpoint": "enabled"
  }
}
```

El límite de saltos se aplica a la **respuesta PUT** del token IMDS, no a todas las solicitudes de metadatos. Un contenedor que legítimamente necesite IMDSv2 puede requerir límite 2. Inspecciona compatibilidad y traslada permisos de aplicación a roles de carga de trabajo; no aumentes el límite solo para ocultar un fallo sin explicación.

Usa una versión de plantilla revisada existente mediante los campos compatibles `launchTemplate.id/version` de eksctl. Hay que sustituir el ID de ejemplo; `--launch-template-name` no es la interfaz documentada de `eksctl create nodegroup`:

```yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: my-cluster
  region: us-west-2
managedNodeGroups:
  - name: imds-template-ng
    launchTemplate:
      id: lt-0123456789abcdef0
      version: "1"
    privateNetworking: true
```

**Alternativa eksctl:** los campos compatibles `disableIMDSv1` y `disablePodIMDS` se pueden usar para un grupo de nodos nuevo. Prepara primero las identidades de carga de trabajo necesarias. `disablePodIMDS` se aplica a Pods sin red del host y no se puede combinar con `withAddonPolicies`.

```yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: my-cluster
  region: us-west-2
managedNodeGroups:
  - name: imds-restricted-ng
    amiFamily: AmazonLinux2023
    instanceType: m5.large
    privateNetworking: true
    desiredCapacity: 2
    minSize: 2
    maxSize: 4
    disableIMDSv1: true
    disablePodIMDS: true
```

Estas dos configuraciones son alternativas; revisa la plantilla generada real y los ajustes de metadatos del nodo. Los valores predeterminados dependen de la configuración de inicio de instancias, los valores predeterminados de cuenta/región y la compatibilidad de metadatos de la AMI; la configuración de lanzamiento tiene prioridad. No supongas que todas las AMI/grupos de nodos usan límite 1 por defecto.

**Nodos existentes:** una versión nueva de la misma plantilla de lanzamiento personalizada puede implementarse con una actualización de grupo de nodos administrado. También se pueden cambiar las opciones de metadatos de instancias EC2 en ejecución/detenidas, sujeto a restricciones IAM/SCP; esto por sí solo no cambia la configuración de futuras instancias de sustitución:

```bash
# Inspect the explicitly reviewed instance before changing its metadata settings.
aws ec2 describe-instances --region "${EXAMPLE_REGION:?}" \
  --instance-ids "${REVIEWED_INSTANCE_ID:?}" \
  --query 'Reservations[].Instances[].{id:InstanceId,tags:Tags,metadata:MetadataOptions}'

# Separate transition step for a tested instance with compatible host agents.
aws ec2 modify-instance-metadata-options --region "$EXAMPLE_REGION" \
  --instance-id "$REVIEWED_INSTANCE_ID" --http-tokens required \
  --http-put-response-hop-limit 1 --http-endpoint enabled
```

Verifica que las opciones hayan llegado al estado `applied` y que sigan funcionando los agentes del nodo, las descargas de imágenes y las credenciales de cargas de trabajo. No deshabilites por completo el endpoint de metadatos solo porque una aplicación use IRSA: los componentes del host aún pueden depender del perfil de instancia y de los metadatos del nodo.

**Controles adicionales:**

- Limita el rol de nodo y asigna roles propios a las aplicaciones. IRSA/Pod Identity no impide por sí solo el acceso alternativo a IMDS del nodo.
- Los Pods `hostNetwork` pueden acceder a IMDS y una carga privilegiada del host puede eludir el aislamiento de red de Pods. Controla los privilegios y el acceso al host por separado.
- Los grupos de seguridad no filtran el servicio de metadatos de enlace local de la instancia. Si aplicas restricciones adicionales en host/red, ten en cuenta la ruta real de Pods y el endpoint IPv6 IMDS opcional (`fd00:ec2::254`) además de IPv4. La antigua regla DNAT ad hoc `PREROUTING -i eth0` no es una restricción general fiable para IMDS de Pods.
- Usa SDK compatibles y prueba el acceso a metadatos sin imprimir tokens de sesión ni valores de credenciales IAM. Observa las opciones reales de metadatos de la instancia; no supongas que las etiquetas Kubernetes del nodo prueban que se apliquen.

Referencias: [opciones IMDS y precedencia](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/configuring-instance-metadata-options.html), [comportamiento de IMDSv2](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/configuring-instance-metadata-service.html), [opciones de seguridad de eksctl](https://docs.aws.amazon.com/eks/latest/eksctl/security.html), [límites de aislamiento de IRSA](https://docs.aws.amazon.com/eks/latest/userguide/iam-roles-for-service-accounts.html).

</details>

5. ¿Qué tarea queda fuera del propósito de una configuración de arranque de nodos EC2?
   * A) Modificar procesos del plano de control administrado por EKS
   * B) Configurar software revisado que ya está instalado en una AMI personalizada
   * C) Aplicar ajustes del host validados con cargas de trabajo
   * D) Configurar etiquetas y taints compatibles para el grupo de nodos

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A) Modificar procesos del plano de control administrado por EKS**

La configuración de arranque configura **hosts de nodos**, no el servidor API, scheduler, controller manager ni etcd administrados por EKS. Para AL2023 usa `nodeadm` y las vías compatibles de eksctl/plantilla de lanzamiento; los ejemplos AL2 antiguos de `bootstrap.sh`/`kubeletExtraArgs` no sirven.

**Instala y configura el software de forma deliberada.** Usa un paquete verificado para el sistema operativo/arquitectura de destino, preferiblemente incorporado a una AMI revisada. Descargar al inicio de cada nodo un RPM `latest` no verificado no produce una instalación reproducible. Un agente de host también necesita los permisos IAM y la conectividad a servicios privados/públicos correspondientes.

El siguiente ejemplo opcional para host AL2023 presupone que CloudWatch Agent ya está instalado. Configura métricas de memoria/swap del host e inicia el agente; si se ejecuta con acceso AWS, envía telemetría facturable. No es una instrucción para ejecutarlo en una estación de administración, Bottlerocket o Auto Mode:

```bash
#!/bin/bash
# AL2023 host example: the reviewed AMI must already contain the verified agent package.
set -euo pipefail
AGENT_CTL=/opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl
test -x "$AGENT_CTL" || {
  printf '%s\n' 'CloudWatch agent is not installed in this AMI.' >&2
  exit 1
}
cat > /opt/aws/amazon-cloudwatch-agent/etc/cloudwatch-agent.json << 'EOF'
{
  "metrics": {
    "metrics_collected": {
      "mem": {"measurement": ["mem_used_percent"]},
      "swap": {"measurement": ["swap_used_percent"]}
    }
  }
}
EOF
"$AGENT_CTL" -a fetch-config -m ec2 \
  -c file:/opt/aws/amazon-cloudwatch-agent/etc/cloudwatch-agent.json -s
```

**Ajuste del kernel:** usa evidencia de las cargas y los requisitos del kernel/CNI real. Los valores de ejemplo originales se conservan como referencias de ajuste no validadas, no recomendaciones universales de rendimiento:

| Ajuste de ejemplo | Valor original de ejemplo | Requisito de revisión |
| --- | --- | --- |
| `net.ipv4.ip_forward` | `1` | Requisitos de enrutamiento de nodo/CNI |
| `net.bridge.bridge-nf-call-iptables` | `1` | Si el módulo bridge y el datapath de CNI lo requieren |
| `net.ipv4.tcp_keepalive_time` | `600` | Comportamiento de timeouts de aplicación/conexión |
| `net.ipv4.tcp_max_syn_backlog`, `net.core.somaxconn`, `net.core.netdev_max_backlog` | `40000` | Presión real de colas, memoria y mediciones de carga |
| `vm.max_map_count` | `262144` | Requisitos de mapeo de la aplicación concreta |

No apliques esta tabla como script general de nodos. Registra la línea base, valida los cambios en un grupo de prueba y conserva una ruta de reversión.

**Discos:** nunca ejecutes `mkfs` sobre un `/dev/nvme1n1` supuesto. La enumeración NVMe no es un identificador estable de titularidad y el dispositivo puede contener datos necesarios. Identifica el volumen EBS previsto por ID/número de serie, confirma que sea desechable recién aprovisionado o esté preparado expresamente e inspecciona particiones/sistemas de archivos/montajes antes de formatearlo. Usa identificadores estables como UUID del sistema de archivos para configurar montajes persistentes.

```bash
# Read-only inspection on the specifically authorized test node.
lsblk --output NAME,PATH,TYPE,SIZE,FSTYPE,UUID,MOUNTPOINTS,SERIAL
findmnt
sysctl net.ipv4.ip_forward vm.max_map_count
```

Para datos persistentes de aplicaciones, prefiere el ciclo de vida CSI/PV correspondiente en vez de vincularlos a discos desechables de un nodo. Los comandos de inspección anteriores no formatean ni montan nada.

**Etiquetas, taints y seguridad:** usa campos de etiquetas/taints del grupo administrado y un dominio que controles; no sobrescribas etiquetas de topología/grupo de nodos propiedad del proveedor. Usa una AMI revisada y un diseño de grupos de seguridad/CNI para reforzar el host. Los cambios ad hoc de SSH/firewall durante el arranque pueden entrar en conflicto con reglas existentes o cortar el acceso y no constituyen un procedimiento completo de refuerzo.

**Datos de usuario de plantilla de lanzamiento:** con una AMI AL2023 seleccionada por EKS y sin `ImageId` personalizado, EKS proporciona el NodeConfig predeterminado necesario. Una personalización MIME mínima puede verse así:

```text
MIME-Version: 1.0
Content-Type: multipart/mixed; boundary="EKS_BOOTSTRAP_EXAMPLE"

--EKS_BOOTSTRAP_EXAMPLE
Content-Type: text/x-shellscript; charset="us-ascii"

#!/bin/bash
set -euo pipefail
install -d -m 0755 /opt/company

--EKS_BOOTSTRAP_EXAMPLE--
```

```bash
# Prepare real EC2 UserData JSON from the reviewed MIME file; no placeholder base64.
BOOTSTRAP_DIR=$(mktemp -d /tmp/eks-bootstrap-example.XXXXXX)
: "${BOOTSTRAP_DIR:?}"
jq -n --rawfile data "${REVIEWED_MIME_FILE:?}" \
  '{UserData:($data|@base64)}' > "$BOOTSTRAP_DIR/launch-template-data.json" || exit 1
aws ec2 create-launch-template --region "${EXAMPLE_REGION:?}" \
  --launch-template-name "${NEW_LAUNCH_TEMPLATE_NAME:?}" \
  --version-description "Reviewed AL2023 customization" \
  --launch-template-data "file://$BOOTSTRAP_DIR/launch-template-data.json" \
  --query 'LaunchTemplate.{id:LaunchTemplateId,version:LatestVersionNumber}'
```

Usa el ID/versión de plantilla devueltos mediante `managedNodeGroups[].launchTemplate`, como en la pregunta avanzada 4. Si especificas un ID de AMI personalizado fuera de una configuración generada por eksctl, proporciona también el NodeConfig completo del clúster descrito en la pregunta básica 5. No inicies kubelet manualmente ni vuelvas a ejecutar `nodeadm init`.

**Alternativa eksctl:** la configuración siguiente usa campos compatibles del grupo de nodos y un comando inocuo de prearranque que crea un directorio. Añade únicamente personalizaciones de host revisadas. `preBootstrapCommands` contiene comandos shell; cuando haga falta personalizar NodeConfig en AL2023, `overrideBootstrapCommand` contiene YAML de NodeConfig.

```yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: my-cluster
  region: us-west-2
managedNodeGroups:
  - name: custom-ng
    amiFamily: AmazonLinux2023
    instanceType: m5.large
    privateNetworking: true
    desiredCapacity: 2
    minSize: 2
    maxSize: 5
    labels:
      example.com/environment: test
      example.com/node-type: compute
    taints:
      - key: dedicated
        value: compute
        effect: NoSchedule
    preBootstrapCommands:
      - install -d -m 0755 /opt/company
```

Los ejemplos no se han arrancado como receta de nodo lista para producción. Valida en tu entorno la procedencia de paquetes, la configuración efectiva de nodeadm/kubelet, los fallos de inicio, la red y el estado de las cargas de trabajo.

**CoreDNS es una carga del plano de datos/complemento**, normalmente un Deployment en capacidad Linux EC2 o Fargate compatible, no un proceso del plano de control administrado por EKS. Configúralo mediante el flujo del complemento/Kubernetes. Los ajustes expuestos de la API del plano de control de EKS, como los registros, son independientes de los datos de usuario de nodos.

Referencias: [inicialización AL2023](https://docs.aws.amazon.com/eks/latest/userguide/al2023.html), [arranque con eksctl](https://docs.aws.amazon.com/eks/latest/eksctl/node-bootstrapping.html), [restricciones de plantillas de lanzamiento](https://docs.aws.amazon.com/eks/latest/userguide/launch-templates.html), [configuración de CloudWatch Agent](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch-Agent-Configuration-File-Details.html).

</details>
