# Cuestionario sobre la creación de clústeres de EKS - Parte 2

> **Última actualización**: 11 de septiembre de 2026

> Los ejemplos de preguntas son alternativas independientes. Usa los requisitos previos de la Parte 1 y una cuenta/clúster de entrenamiento seleccionado explícitamente. Dentro de un ejercicio, ejecuta sus pasos en orden en la misma sesión de Bash. Los comandos de nube/host que aparecen a continuación se revisaron, pero no se ejecutaron contra AWS ni contra nodos durante esta auditoría.

Este cuestionario evalúa tu comprensión de conceptos avanzados, opciones de seguridad y configuraciones de red relacionadas con la creación de clústeres de Amazon EKS. Abarca temas como la seguridad del clúster, las políticas de red y las cuentas de servicio.

## Preguntas sobre conceptos básicos

1. ¿Cuál es el propósito principal de IRSA en un clúster de EKS?
   * A) Conceder acceso de administrador de Kubernetes
   * B) Asignar el rol de IAM del nodo EC2
   * C) Dar a las cargas de trabajo permisos temporales de AWS a través de su cuenta de servicio de Kubernetes
   * D) Modificar el rol del plano de control de EKS

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Dar a las cargas de trabajo permisos temporales de AWS a través de su cuenta de servicio de Kubernetes**

IRSA permite que una carga de trabajo obtenga credenciales temporales de AWS mediante la identidad de su cuenta de servicio de Kubernetes. La política de permisos del rol de IAM determina qué operaciones de AWS puede realizar. Esto es independiente de RBAC de Kubernetes y de los roles de IAM utilizados por el plano de control de EKS o los nodos EC2.

**Flujo de confianza:** EKS emite un token proyectado de cuenta de servicio. Registra como proveedor OIDC de IAM el emisor OIDC real del clúster y, luego, confía en la audiencia y el sujeto de espacio de nombres/cuenta de servicio previstos. La cadena de credenciales predeterminada de un SDK de AWS compatible intercambia ese token mediante STS `AssumeRoleWithWebIdentity`. Usa el ARN/proveedor real y la identidad exacta de la cuenta de servicio en este ejemplo:

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

Anota la cuenta de servicio con el ARN del rol y haz referencia a ella en el Pod. Crea primero un espacio de nombres `irsa-lab` sin usar. Estos dos manifiestos son una alternativa a la creación de cuentas de servicio administrada por eksctl que se muestra a continuación; no sobrescribas la cuenta de servicio de otra aplicación:

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

El Pod usa una etiqueta de imagen verificada de AWS CLI v2 e imprime la identidad del llamante, no claves de acceso secretas ni el token de identidad web. Confirma que el rol devuelto sea el rol previsto para la carga de trabajo. Que STS confirme la identidad no demuestra por sí solo que se tenga acceso a S3 ni a ningún otro recurso de destino; prueba la operación necesaria por separado, como en el ejercicio 1.

**Alternativa con eksctl:** usa una política limitada a los recursos/acciones previstos, no una política amplia de S3 administrada por AWS para una tarea que afecta a un solo bucket. Revisa primero las cuentas de servicio existentes y la titularidad de los roles; no agregues `--override-existing-serviceaccounts` como solución genérica.

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

- Usa un SDK compatible y su cadena de credenciales. Las credenciales codificadas directamente o los proveedores anteriores en la cadena pueden prevalecer sobre IRSA. El webhook inyecta la configuración del rol/archivo de token; el SDK renueva las credenciales temporales. No imprimas ni copies los valores del token/las credenciales.
- IRSA no bloquea por sí solo el acceso al IMDS del nodo, y los contenedores que comparten un nodo no constituyen un límite de seguridad estricto. Restringe por separado el IMDS y los permisos de los nodos; los Pods con `hostNetwork` aún pueden acceder al IMDS.
- Las condiciones de IAM limitan la asunción del rol, pero cualquiera que pueda crear un Pod con esa cuenta de servicio podría obtener sus permisos de AWS. Controla también la administración de cargas de trabajo/cuentas de servicio de Kubernetes.
- EKS Pod Identity es otra opción de identidad de carga de trabajo, con sus propios requisitos de compatibilidad. Su flujo de credenciales mediante EKS Auth/agente es distinto del flujo OIDC/STS de IRSA.
- Los usuarios del clúster utilizan las políticas/entradas de acceso de EKS o la asignación heredada `aws-auth`, cuando esté configurada. Estas autorizan el acceso a Kubernetes; no sustituyen las políticas de permisos de IAM para cargas de trabajo.

Referencias: [IRSA](https://docs.aws.amazon.com/eks/latest/userguide/iam-roles-for-service-accounts.html), [asignación de un rol a una cuenta de servicio](https://docs.aws.amazon.com/eks/latest/userguide/associate-service-account-role.html), [requisitos de los SDK](https://docs.aws.amazon.com/eks/latest/userguide/iam-roles-for-service-accounts-minimum-sdk.html), [Pod Identity](https://docs.aws.amazon.com/eks/latest/userguide/pod-identities.html).

</details>

2. ¿Qué controlan los grupos de seguridad de AWS en un diseño de EKS?
   * A) La autorización de recursos de Kubernetes
   * B) El tráfico de red permitido en las interfaces asociadas, incluidas las interfaces de Pod compatibles
   * C) Las audiencias de los tokens de cuentas de servicio
   * D) El número de réplicas de un Deployment

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) El tráfico de red permitido en las interfaces asociadas, incluidas las interfaces de Pod compatibles**

Los grupos de seguridad son filtros de red con estado asociados a interfaces de red. En EKS ayudan a controlar el tráfico entre interfaces del clúster, nodos y, con la función compatible Security Groups for Pods, Pods seleccionados. No implementan RBAC de Kubernetes ni autentican usuarios.

**Las reglas predeterminadas y las necesarias no son lo mismo.** EKS crea `eks-cluster-sg-<cluster>-<id>` con reglas de entrada autorreferenciales, acceso de salida amplio y una regla de salida autorreferencial que se usa para EFA. Son valores predeterminados que deben revisarse, no una receta de privilegio mínimo. EKS asocia el grupo del clúster con las interfaces de red del clúster y, normalmente, con las interfaces de los nodos administrados; los grupos de seguridad personalizados especificados en una plantilla de lanzamiento modifican ese comportamiento.

Si restringes las reglas de salida predeterminadas, conserva el tráfico mínimo documentado y las dependencias adicionales de tus cargas de trabajo reales:

| Tráfico de salida requerido del grupo del clúster | Destino |
| --- | --- |
| TCP 443 | Grupo de seguridad del clúster |
| TCP 10250 | Grupo de seguridad del clúster |
| TCP y UDP 53 | Grupo de seguridad del clúster |

Esta tabla por sí sola no constituye un diseño de red completo. Revisa los puertos entre nodos/de las aplicaciones, el acceso a la API y al registro, S3, las rutas DNS y las reglas de IPv4/IPv6. Los puntos de conexión privados pueden proporcionar conectividad con AWS sin salida general a Internet. EKS puede volver a crear reglas autorreferenciales durante las actualizaciones del clúster, así que no describas su eliminación como una restricción permanente.

**Grupos adicionales:** los grupos especificados en `resourcesVpcConfig.securityGroupIds` de un clúster se asocian a las interfaces de red del clúster; no se asocian automáticamente a los grupos de nodos. Si una plantilla de lanzamiento de nodo proporciona grupos de seguridad personalizados, EKS no agrega también el grupo de seguridad del clúster, y los grupos personalizados deben permitir el tráfico necesario entre los nodos y la API.

El siguiente ejemplo de AWS CLI muestra cómo seleccionar un grupo adicional para un plano de control nuevo. No crea capacidad de nodos ni entradas de acceso para operadores. La identidad que aprovisiona necesita permiso para crear la entrada de acceso necesaria para el operador porque el acceso de administrador automático del creador está desactivado:

```bash
# Cluster creation fragment: use reviewed roles/subnets/groups and a new name.
aws eks create-cluster --name "${NEW_CLUSTER_NAME:?}" \
  --region "${EXAMPLE_REGION:?}" --kubernetes-version 1.36 \
  --role-arn "${CLUSTER_ROLE_ARN:?}" \
  --access-config authenticationMode=API,bootstrapClusterCreatorAdminPermissions=false \
  --resources-vpc-config "subnetIds=${PRIVATE_SUBNET_A:?},${PRIVATE_SUBNET_B:?},securityGroupIds=${ADDITIONAL_CONTROL_PLANE_SG:?},endpointPrivateAccess=true,endpointPublicAccess=true,publicAccessCidrs=${APPROVED_API_CIDR:?}"
```

Los campos de red equivalentes de eksctl pertenecen a la configuración completa revisada de la [Parte 2](../../eks/02-eks-cluster-creation-part2.md). Sustituye el CIDR de documentación y todos los ID:

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

**API pública frente a privada:** el punto de conexión público de Kubernetes se restringe con `publicAccessCidrs`, no con el grupo de seguridad del clúster. Las reglas del grupo de seguridad del clúster rigen el tráfico al punto de conexión privado. Ni una lista de CIDR permitidos ni una regla de grupo de seguridad concede autorización de IAM/RBAC.

**Security Groups for Pods:** en el cómputo compatible, configura la función y los ajustes necesarios de IAM/VPC CNI antes de crear un `SecurityGroupPolicy`. Comprueba la compatibilidad con el uso de interfaces troncales de instancias, la versión de CNI, el modo de aplicación, DNS y las reglas reales de los grupos de seguridad. Windows y EKS Auto Mode no admiten esta función; las familias de instancias EC2 `t` no son compatibles. Fargate tiene su propia configuración compatible.

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

La política selecciona Pods en un espacio de nombres `sg-lab` creado por separado; un objeto CRD por sí solo no demuestra que se haya asociado un grupo de seguridad. Los modos de grupo de seguridad de Pod estándar/estricto y SNAT afectan a qué grupo filtra el tráfico fuera de la VPC. Verifica el comportamiento documentado para el modo de tu configuración.

Kubernetes NetworkPolicy es un mecanismo aparte, aplicado por un complemento de red configurado. El tráfico de los Pods no se deniega de forma predeterminada automáticamente solo porque el clúster admita NetworkPolicy. Consulta la pregunta 3 para ver una configuración deliberada de políticas.

```bash
aws eks describe-cluster --name "${EXAMPLE_CLUSTER:?}" \
  --region "${EXAMPLE_REGION:?}" \
  --query 'cluster.resourcesVpcConfig.{clusterSG:clusterSecurityGroupId,additionalSGs:securityGroupIds,publicAccess:endpointPublicAccess,privateAccess:endpointPrivateAccess,cidrs:publicAccessCidrs}'
aws ec2 describe-security-groups --region "$EXAMPLE_REGION" \
  --group-ids "${REVIEWED_SECURITY_GROUP_ID:?}"
```

Referencias: [grupos de seguridad del clúster](https://docs.aws.amazon.com/eks/latest/userguide/sec-group-reqs.html), [acceso al punto de conexión de la API](https://docs.aws.amazon.com/eks/latest/userguide/cluster-endpoint.html), [grupos de seguridad para Pods](https://docs.aws.amazon.com/eks/latest/userguide/security-groups-for-pods.html).

</details>

3. ¿Qué se necesita para aplicar Kubernetes NetworkPolicy en EKS?
   * A) Solo una regla de grupo de seguridad
   * B) Una implementación de políticas compatible y habilitada, como Amazon VPC CNI, Calico o Cilium
   * C) Solo VPC Flow Logs
   * D) Un objeto NetworkPolicy sin una implementación que lo aplique

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Una implementación de políticas compatible y habilitada, como Amazon VPC CNI, Calico o Cilium**

Se necesita una implementación de políticas de red configurada; crear solo un objeto `NetworkPolicy` no aplica reglas de tráfico. **Amazon VPC CNI admite NetworkPolicy**, por lo que Calico o Cilium no son obligatorios para disponer de esta función.

**Ruta de Amazon VPC CNI:** verifica la compatibilidad de la plataforma/clúster, el kernel de Linux y la versión de CNI; luego habilita la función de políticas de red mediante la configuración que administra el complemento. La guía actual de AWS usa VPC CNI 1.21.0 o posterior para las políticas estándar y administrativas, y kernel de Linux 5.10 o posterior. Las versiones mínimas históricas anteriores no son objetivos de actualización para un clúster actual.

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

Para el complemento administrado por EKS, el valor de configuración pertinente es:

```json
{
  "enableNetworkPolicy": "true"
}
```

Combínalo con la **configuración completa revisada**, conservando los ajustes existentes necesarios; proporcionar un nuevo documento `configurationValues` no es un parche JSON. No reduzcas la versión del complemento ni sobrescribas un DaemonSet administrado por EKS con un manifiesto antiguo de upstream. Para una instalación autoadministrada/de Helm, usa en cambio la configuración documentada de esa instalación.

En el modo de inicio estándar, un Pod nuevo puede permitir inicialmente el tráfico hasta que se programe su política. El modo estricto comienza con denegación predeterminada, pero requiere preparar todas las políticas de conectividad necesarias, incluidas las dependencias de CoreDNS. No cambies a ciegas un clúster existente al modo estricto.

**Implementaciones alternativas:**

- **Calico con redes de Amazon VPC:** conserva AWS IPAM/CNI y configura la `Installation` del operador para `AmazonVPC`. Sigue las instrucciones del operador/CRD fijadas a una versión y los requisitos previos de anotación de IP de Pod/RBAC de AWS de la guía oficial de EKS. Desactiva la aplicación de políticas propia de AWS para esa ruta de Calico; instalar solo el operador o un manifiesto VXLAN arbitrario no equivale a este diseño.

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

- **Cilium con Amazon VPC CNI:** se necesita la configuración de encadenamiento documentada; desactivar simplemente los túneles/la mascarada no configura el encadenamiento. Los siguientes valores son una referencia de la guía publicada de la versión 1.20.1. Comprueba la compatibilidad de versión/clúster y completa los requisitos previos de la guía. Los Pods existentes deben volver a crearse mediante un despliegue gradual controlado para que surta efecto la nueva ruta de encadenamiento.

```yaml
# Relevant Helm values from the Cilium 1.20.1 AWS-CNI chaining guide.
# This is not a complete install or migration command.
cni:
  chainingMode: aws-cni
  exclusive: false
enableIPv4Masquerade: false
routingMode: native
```

Elige y valida la implementación de aplicación prevista en lugar de apilar instalaciones de CNI/políticas no revisadas. Sustituir una implementación puede dejar reglas a nivel de nodo y requiere una migración planificada.

**Ejemplo de política:** en un espacio de nombres `policy-lab` recién creado, permite TCP 8080 del frontend al backend y DNS, y deniega el resto del tráfico. El backend debe escuchar realmente en el puerto 8080. Para la implementación de AWS, usa el mismo Service y puerto de contenedor. Los selectores DNS que aparecen a continuación presuponen Pods CoreDNS convencionales en `kube-system`; NodeLocal DNSCache o un DNS personalizado requieren otras reglas revisadas.

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

Se permiten tanto la salida del frontend como la entrada al backend porque ambos extremos están aislados por lo demás. Las distintas NetworkPolicies estándar suman el tráfico permitido; el objeto de denegación predeterminada no anula una regla de permiso. Se permite DNS para el espacio de nombres de prueba, para no confundir una conexión de aplicación denegada con un fallo de DNS.

**Verificación significativa:** usa Pods frontend, backend y cliente no relacionado administrados por Deployments. AWS documenta que la aplicación de políticas puede no ser fiable en Pods independientes sin `metadata.ownerReferences`, así que no uses un Pod creado directamente con `kubectl run` como única prueba. Establece la conectividad de referencia, aplica las políticas y luego verifica que el frontend tenga éxito y el cliente no relacionado falle, mientras DNS siga funcionando. Prueba conexiones nuevas después de que converjan las políticas. Encontrar Pods de CNI o aplicar YAML correctamente no es suficiente.

La aplicación de políticas de AWS VPC CNI se aplica a nodos EC2 Linux compatibles, no a Windows ni a Fargate. Se aplica a la interfaz principal del Pod y a la familia de IP del clúster; las interfaces adicionales y la salida IPv4 de Pods IPv6 tienen limitaciones. Los grupos de seguridad, Network Firewall y los registros de flujo tienen propósitos distintos y no sustituyen esta configuración de políticas de Kubernetes.

Referencias: [configuración de políticas de VPC CNI](https://docs.aws.amazon.com/eks/latest/userguide/cni-network-policy-configure.html), [limitaciones de políticas de AWS](https://docs.aws.amazon.com/eks/latest/userguide/cni-network-policy.html), [Calico en EKS](https://docs.tigera.io/calico/latest/getting-started/kubernetes/managed-public-cloud/eks), [fuente del encadenamiento de Cilium 1.20.1](https://github.com/cilium/cilium/blob/v1.20.1/Documentation/installation/cni-chaining-aws-cni.rst), [Kubernetes NetworkPolicy](https://kubernetes.io/docs/concepts/services-networking/network-policies/).

</details>

4. ¿Qué afirmación describe correctamente el cifrado en reposo de los datos de la API de Kubernetes en EKS 1.28 o posterior?
   * A) El cifrado de sobres está habilitado de forma predeterminada; una clave de KMS administrada por el cliente es opcional
   * B) Todos los clústeres deben volver a crearse antes de poder cifrar los Secrets
   * C) La codificación Base64 proporciona cifrado en reposo
   * D) Un sidecar de aplicación debe cifrar la base de datos del plano de control de EKS

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A) El cifrado de sobres está habilitado de forma predeterminada; una clave de KMS administrada por el cliente es opcional**

Los clústeres de EKS que ejecutan Kubernetes **1.28 o posterior** tienen cifrado de sobres KMS v2 para **todos los datos de la API de Kubernetes** de forma predeterminada, con una clave de AWS de propiedad de AWS, salvo que se asocie una clave de KMS administrada por el cliente. Esto incluye Secrets, ConfigMaps y otros recursos de API almacenados. Es adicional al cifrado de disco de etcd y no cifra los datos de aplicaciones en los nodos ni los volúmenes EBS.

**Inspecciona antes de cambiar nada.** La ausencia del ARN de una clave administrada por el cliente en `encryptionConfig` no significa que los Secrets no estén cifrados. La consola identifica el modo de clave de propiedad de AWS sin revelar el ARN de esa clave.

```bash
aws eks describe-cluster --name "${EXAMPLE_CLUSTER:?}" \
  --region "${EXAMPLE_REGION:?}" \
  --query 'cluster.{version:version,status:status,encryption:encryptionConfig}'

# Optional CMK inspection, only when a customer-managed key is required.
aws kms describe-key --key-id "${KMS_KEY_ARN:?Reviewed customer-managed key ARN}" \
  --region "$EXAMPLE_REGION" \
  --query 'KeyMetadata.{arn:Arn,state:KeyState,spec:KeySpec,usage:KeyUsage}'
```

**Clave opcional administrada por el cliente (CMK).** Usa una clave de cifrado simétrica en la región del clúster cuando tus requisitos exijan controlar la clave como cliente. Verifica la disponibilidad de la clave, los permisos de IAM de quien realiza la llamada, la política de clave/las concesiones y los permisos entre cuentas, si corresponde. Una política genérica que concede solo varias acciones de KMS a `eks.amazonaws.com` no constituye una configuración completa: la identidad que aprovisiona/asocia la clave necesita los permisos documentados `kms:DescribeKey` y `kms:CreateGrant`. La condición `kms:GrantIsForAWSResource` no se admite para controlar `CreateGrant` durante `CreateCluster`.

Puedes proporcionar un proveedor en `CreateCluster` o asociar una CMK a un clúster existente apto mediante `AssociateEncryptionConfig`; no es necesario crear otro clúster por principio. No uses esto como operación general para reemplazar claves o desactivar el cifrado. Los clústeres que ya tienen una CMK asociada necesitan seguir el procedimiento compatible de administración de claves.

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

Registra el ID de actualización y comprueba el estado hasta que indique `Successful` o un fallo; la aceptación de la solicitud no significa que haya terminado. El campo `resources: ["secrets"]` conservado se acepta por compatibilidad. En EKS 1.28 o posterior, **no** limita el cifrado a Secrets: el campo está obsoleto y todos los datos de la API de Kubernetes se cifran mediante cifrado de sobres. Las API actuales también aceptan una lista `resources` omitida, nula o vacía, mientras que las respuestas conservan el valor heredado `["secrets"]`. La antigua guía paso a paso `enable-kms` para Kubernetes 1.27 y versiones anteriores es orientación histórica, no un objetivo de migración para versiones compatibles.

No desactives ni elimines una clave asociada como limpieza de laboratorio mientras exista el clúster. La indisponibilidad de la clave puede degradar el plano de control, y su pérdida permanente puede hacer que el clúster sea irrecuperable. Revisa la recuperación, el acceso y la supervisión de la clave antes de elegir una CMK. El cifrado predeterminado con una clave de propiedad de AWS no requiere configurar claves de cliente; una CMK tiene cargos de KMS independientes.

**El uso de Secrets no cambia.** Los clientes de API y los Pods autorizados reciben valores utilizables; el cifrado en reposo no sustituye RBAC, la identidad de cargas de trabajo ni la protección de registros/copias de seguridad. El siguiente manifiesto contiene intencionadamente datos ficticios públicos y no es un secreto de producción:

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

Para credenciales reales, evita confirmar manifiestos con valores en texto sin formato o codificados en Base64, literales en el historial de la shell y diagnósticos que vuelquen valores. Base64 es una codificación reversible. AWS Secrets Manager puede integrarse mediante archivos montados con CSI o un controlador que sincronice Kubernetes Secrets; no todas las aplicaciones necesitan necesariamente cambios en el SDK. Un Secret sincronizado sigue sujeto a los controles de acceso de Kubernetes. Un sidecar no puede configurar el cifrado en reposo del servidor de API administrado.

Referencias: [cifrado de sobres predeterminado](https://docs.aws.amazon.com/eks/latest/userguide/envelope-encryption.html), [AssociateEncryptionConfig](https://docs.aws.amazon.com/eks/latest/APIReference/API_AssociateEncryptionConfig.html), [procedimiento y permisos heredados de KMS](https://docs.aws.amazon.com/eks/latest/userguide/enable-kms.html), [Secrets Manager en EKS](https://docs.aws.amazon.com/secretsmanager/latest/userguide/integrating_csi_driver.html).

</details>

5. ¿Cómo se deben personalizar los ajustes de kubelet para nodos administrados EC2 con AL2023?
   * A) Editar el kubelet del plano de control de EKS en la consola
   * B) Usar un NodeConfig de nodeadm compatible mediante eksctl o los datos de usuario de una plantilla de lanzamiento
   * C) Cambiar status.capacity con kubectl edit node
   * D) Ejecutar el script bootstrap.sh de AL2 en cada arranque de AL2023

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Usar un NodeConfig de nodeadm compatible mediante eksctl o los datos de usuario de una plantilla de lanzamiento**

Para **nodos EC2 con AL2023**, usa `NodeConfig` de `nodeadm` y la integración compatible con eksctl/plantillas de lanzamiento. No uses el procedimiento AL2 `/etc/eks/bootstrap.sh` ni supongas que existe la opción `eksctl create nodegroup --kubelet-extra-args`. El mapa antiguo `kubeletExtraArgs` no es el campo compatible para grupos de nodos administrados en este ejemplo.

**eksctl:** para AL2023, `overrideBootstrapCommand` contiene un `NodeConfig` YAML, a pesar de su nombre. eksctl lo antepone a los datos de usuario para que nodeadm lo combine con la configuración de nodo generada. Con una AMI nativa seleccionada por EKS, EKS proporciona la configuración predeterminada necesaria del clúster. Revisa la configuración combinada efectiva en un nodo de prueba antes de ampliar el despliegue:

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

Las reservas de recursos y el umbral de desalojo de 500 MiB que aparecen arriba son **ilustrativos**, no recomendaciones basadas en mediciones. Reducen la capacidad asignable a Pods y pueden causar desalojos si no son adecuados. `mergeDefaultEvictionSettings: true` es compatible con Kubernetes 1.36 y conserva las señales de desalojo predeterminadas que no se especifican cuando kubelet procesa un mapa parcial de desalojo. Sin una combinación apropiada, especificar una sola señal puede poner accidentalmente en cero otros umbrales predeterminados.

**Ruta de AMI personalizada/plantilla de lanzamiento:** si proporcionas tu propio ID de AMI fuera de la configuración generada por eksctl, proporciona metadatos completos del clúster: nombre, punto de conexión de la API, CA en Base64 y CIDR de Service. Reutiliza el procedimiento de generación de metadatos de la [pregunta avanzada 5 del cuestionario de la Parte 1](02-eks-cluster-creation-part1-quiz.md#advanced-topics) y agrega a ese NodeConfig los ajustes revisados de `spec.kubelet.config`. Un objeto parcial que solo contiene kubelet no es una configuración de arranque independiente completa.

AL2023 ejecuta `nodeadm-config` antes de los datos de usuario y `nodeadm-run` después. No vuelvas a ejecutar `nodeadm init` ni inicies/reconfigures kubelet manualmente de una forma que entre en conflicto con esos servicios. Otras familias de sistemas operativos, como Bottlerocket y Windows, usan mecanismos de configuración distintos; estos ejemplos no se aplican a los nodos de EKS Auto Mode.

| Ajuste | Qué verificar |
| --- | --- |
| `maxPods` / `maxPodsExpression` de nodeadm | Límites de ENI/IP de la instancia, modo CNI, delegación de prefijos y densidad compatible; no fuerces un valor universal de 110 |
| Etiquetas y taints de nodos | Prefiere los campos de grupos de nodos administrados; usa tu propio prefijo de etiquetas en lugar de sobrescribir etiquetas de EKS/AZ |
| `kubeReserved`, `systemReserved` | Requisitos reales de las cargas de trabajo del host/sistema y Node Allocatable |
| `evictionHard`, umbrales soft | Señales de memoria/disco/inodos y comportamiento de combinación predeterminada; no desactives protecciones no relacionadas |
| Controlador cgroup | Compatibilidad con el sistema operativo y el entorno de ejecución de contenedores seleccionados; conserva los valores predeterminados probados de la AMI salvo que se necesite un cambio revisado |

**Validación:** inspecciona la capacidad/asignación de nodos y la configuración/los registros efectivos del servicio. Que el nodo esté listo no demuestra que se haya aplicado cada valor personalizado. Esta auditoría comprobó la sintaxis de configuración y las definiciones oficiales de los campos; no arrancó un nodo con estos ajustes.

```bash
# Kubernetes-side checks through the intended cluster context.
kubectl --kubeconfig "${EXAMPLE_KUBECONFIG:?}" describe node "${EXAMPLE_NODE_NAME:?}"

# Run separately on a specifically authorized AL2023 test node.
sudo systemctl status nodeadm-config nodeadm-run kubelet --no-pager
sudo systemctl cat kubelet
sudo journalctl -u nodeadm-config -u nodeadm-run -u kubelet --since '-15 min' --no-pager
```

Usa la ruta de configuración real del servicio configurado, en lugar de suponer que todas las AMI tienen `/etc/systemd/system/kubelet.service.d/10-kubelet-args.conf`. Limita y protege los registros de diagnóstico según corresponda.

`kubectl edit node` puede cambiar los metadatos del Node, pero no establece la configuración de inicio de kubelet. SSM puede ejecutar comandos en el host, pero una modificación improvisada del host no es una configuración duradera para reemplazar nodos administrados y puede requerir reinicios disruptivos. Incluye los ajustes revisados en la configuración de aprovisionamiento y reemplaza/prueba los nodos deliberadamente.

Referencias: [arranque de AL2023 con eksctl](https://docs.aws.amazon.com/eks/latest/eksctl/node-bootstrapping.html), [servicios de AL2023](https://docs.aws.amazon.com/eks/latest/userguide/al2023.html), [API de nodeadm](https://awslabs.github.io/amazon-eks-ami/nodeadm/doc/api/), [KubeletConfiguration](https://kubernetes.io/docs/reference/config-api/kubelet-config.v1beta1/), [definiciones de campos de Kubernetes 1.36](https://github.com/kubernetes/kubelet/blob/v0.36.0/config/v1beta1/types.go).

</details>

6. ¿Qué mecanismos pueden sustituir los controles eliminados de PodSecurityPolicy en EKS?
   * A) Solo los grupos de seguridad de EC2
   * B) Pod Security Admission y, cuando sea necesario, un motor de políticas compatible
   * C) Solo la retención de registros de CloudWatch
   * D) Una clave de acceso de usuario de IAM almacenada en cada Pod

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Pod Security Admission y, cuando sea necesario, un motor de políticas compatible**

PodSecurityPolicy quedó obsoleto en Kubernetes 1.21 y se eliminó en 1.25. Usa **Pod Security Admission (PSA)** integrado para aplicar los **Pod Security Standards (PSS)** y un motor de políticas adecuado para los requisitos que excedan esos controles.

**PSA:** Privileged, Baseline y Restricted son los tres niveles de PSS; `enforce`, `audit` y `warn` son modos independientes. Para un espacio de nombres de laboratorio recién creado, este ejemplo aplica Baseline e informa de las infracciones de Restricted. La versión de política está fijada al ejemplo de EKS 1.36; elige una versión compatible con el clúster real.

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

No vuelvas a etiquetar a ciegas un espacio de nombres compartido existente. Primero audita/avisa, corrige los manifiestos de las cargas de trabajo y después endurece la aplicación. PSA no modifica los Pods para que cumplan los requisitos ni desalojará Pods que ya estén en ejecución. Evalúa la admisión de Pods; las advertencias/auditorías de las plantillas de cargas de trabajo ayudan a detectar infracciones antes de que sus controladores intenten crear Pods.

**Kyverno:** en este ejemplo auditado, el chart 3.9.1 incluye el controlador 1.19.1. Kyverno 1.19 declara obsoletos los tipos heredados `ClusterPolicy`/`Policy` y su guía de migración prevé eliminarlos en 1.20. Los ejemplos nuevos deben usar las API de políticas actuales basadas en CEL. Migra las políticas existentes antes de una actualización incompatible, en lugar de cambiar solo la versión del controlador.

```bash
# Optional new installation; review existing controllers and release compatibility.
helm repo add kyverno https://kyverno.github.io/kyverno/
helm repo update kyverno
helm install kyverno kyverno/kyverno --version 3.9.1 \
  --namespace kyverno --create-namespace \
  --kubeconfig "${EXAMPLE_KUBECONFIG:?}" --wait --timeout 5m
```

El siguiente **ValidatingPolicy** `policies.kyverno.io/v1` rechaza `privileged: true` en contenedores normales, init y efímeros, y solo se aplica al espacio de nombres del laboratorio. Permite que el campo no esté presente o sea falso:

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

Esto demuestra un control, no todo el estándar Baseline o Restricted. El motor de políticas/las CRD deben estar listos antes de aplicar la política, y hay que verificar el comportamiento real de admisión/subrecursos en el clúster previsto. La evaluación en segundo plano informa de infracciones existentes; no desaloja cargas de trabajo en ejecución.

**Alternativa OPA Gatekeeper:** instala una versión de Gatekeeper revisada si su modelo de políticas se ajusta a tus requisitos. Este ejemplo fija el chart/controlador en 3.23.1:

```bash
# Alternative policy-engine example, not a prerequisite for the Kyverno example.
helm repo add gatekeeper https://open-policy-agent.github.io/gatekeeper/charts
helm repo update gatekeeper
helm install gatekeeper gatekeeper/gatekeeper --version 3.23.1 \
  --namespace gatekeeper-system --create-namespace \
  --kubeconfig "${EXAMPLE_KUBECONFIG:?}" --wait --timeout 5m
```

Gatekeeper necesita primero una ConstraintTemplate `templates.gatekeeper.sh/v1`. Espera a que se establezcan la plantilla y la CRD de Constraint generada antes de aplicar la Constraint correspondiente. El ejemplo de Rego que aparece a continuación comprueba las mismas tres listas de contenedores y limita la Constraint al espacio de nombres del laboratorio:

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

Gatekeeper `enforcementAction: deny` rechaza las infracciones coincidentes; `dryrun` o `warn` pueden facilitar un despliegue gradual. Una plantilla sin su Constraint no es una política aplicada. Usa la API/el esquema y el modo Rego compatibles con la versión instalada.

**Validación y límites:** la CLI de Kyverno 1.19.1 (con las advertencias tratadas como errores) y Gator de Gatekeeper 3.23.1 se ejecutaron localmente en seis casos cada uno: valor explícito false, campo omitido, contenedores normales/init/efímeros con privilegios y un espacio de nombres fuera del ámbito. Ambas implementaciones de políticas dieron los resultados locales previstos. No se instaló nada en un clúster ni se realizó una prueba de admisión en vivo.

```bash
# Offline policy logic checks using locally reviewed fixture files.
kyverno apply kyverno-policy.yaml --resource test-pod.yaml --warnings-as-errors
gator test --filename gatekeeper-policy.yaml --filename test-pod.yaml --output=json
```

No infieras que un rechazo en vivo procede de un motor específico si PSA u otro webhook también lo rechazaría. Verifica el estado del controlador/la política, el ámbito de destino, las respuestas reales de admisión y los informes. Usa el conjunto completo de controles para espacios de nombres del host, hostPath, capacidades, escalada de privilegios y otros requisitos de PSS.

AWS Security Hub, AWS Config y los grupos de seguridad de EC2 tienen funciones distintas; habilitarlos no sustituye la aplicación de admisión de Pods de Kubernetes.

Referencias: [PSA](https://kubernetes.io/docs/concepts/security/pod-security-admission/), [PSS](https://kubernetes.io/docs/concepts/security/pod-security-standards/), [migración de Kyverno a CEL](https://kyverno.io/docs/guides/migration-to-cel/), [Kyverno 1.19.1](https://github.com/kyverno/kyverno/releases/tag/v1.19.1), [guía de Gatekeeper 3.23.1](https://github.com/open-policy-agent/gatekeeper/blob/v3.23.1/website/docs/howto.md).

</details>

7. ¿Qué requisito previo del proveedor de identidad de IAM se necesita para la confianza de identidad web de IRSA?
   * A) Una clave de acceso de usuario de IAM almacenada en cada Pod
   * B) Un RoleBinding de administrador del clúster
   * C) Un proveedor OIDC de IAM que coincida con el emisor del clúster
   * D) Una IP pública en cada nodo de trabajo

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Un proveedor OIDC de IAM que coincida con el emisor del clúster**

IRSA necesita un proveedor OIDC de IAM que coincida con el emisor del clúster de destino. Comprueba si ya existe; no crees proveedores duplicados ni reutilices el emisor de otro clúster. Este requisito previo debe cumplirse antes de que la carga de trabajo pueda asumir su rol de IAM, pero la cuenta de servicio puede crearse antes que el rol y anotarse después. No existe un requisito universal de crear todos los recursos exactamente en el mismo orden.

```bash
aws eks describe-cluster --name "${EXAMPLE_CLUSTER:?}" \
  --region "${EXAMPLE_REGION:?}" --query cluster.identity.oidc.issuer --output text
eksctl utils associate-iam-oidc-provider \
  --cluster "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION" --approve
```

Usa eksctl o el procedimiento actual para proveedores OIDC de IAM en lugar de copiar una huella digital de certificado fija y antigua. Configura `sts.amazonaws.com` como el ID de cliente/la audiencia prevista. En una VPC sin salida a Internet, configurar el proveedor desde dentro de la VPC puede requerir el punto de conexión de interfaz independiente `oidc-eks`/DNS privado u otra ruta de administración accesible. El intercambio de tokens de IRSA requiere por separado conectividad regional con STS.

Luego crea la política de rol limitada y la política de confianza de la pregunta 1 con `aud` y `sub`; anota la cuenta de servicio correcta y crea un Pod nuevo que haga referencia a ella. Los Pods existentes no obtienen la configuración inyectada nueva simplemente porque cambie una anotación de la cuenta de servicio; vuelve a crearlos mediante el despliegue gradual normal de su controlador.

Para comprobar la identidad, usa el manifiesto explícito del Pod de la pregunta 1. `kubectl run --serviceaccount` no es una opción compatible actual:

```bash
# After deploying the identity-check Pod from question 1.
kubectl --kubeconfig "${EXAMPLE_KUBECONFIG:?}" -n irsa-lab \
  get pod irsa-identity-check -o jsonpath='{.status.phase}{"\n"}'
kubectl --kubeconfig "$EXAMPLE_KUBECONFIG" -n irsa-lab logs irsa-identity-check
```

Comprueba el estado de salida del Pod y compara la cuenta/la identidad de rol asumido devuelta con el rol esperado. Una identidad del rol del nodo no demuestra que IRSA funcione. A continuación, prueba solo la operación de la aplicación que esté dentro del ámbito; `aws s3 ls` sin un bucket requeriría enumerar todos los buckets y no es apropiado para una política de un solo bucket.

EKS Pod Identity usa un mecanismo distinto y no requiere crear un proveedor OIDC de IAM para cada clúster. Mantén sus requisitos de asociación de cuenta de servicio, agente y confianza de IAM separados de los de IRSA.

Referencias: [crear un proveedor OIDC de IAM](https://docs.aws.amazon.com/eks/latest/userguide/enable-iam-roles-for-service-accounts.html), [conectividad privada de IRSA](https://docs.aws.amazon.com/eks/latest/userguide/private-clusters.html), [configuración de Pods](https://docs.aws.amazon.com/eks/latest/userguide/pod-configuration.html).

</details>

8. ¿Cómo se habilita la exportación de registros del plano de control de EKS?
   * A) Instalar un agente en los hosts del plano de control administrado
   * B) Configurar los registros del clúster mediante las API de EKS, la consola o eksctl
   * C) Instalar Fluentd solo en los nodos de trabajo
   * D) Conectarse por SSH al servidor de API administrado y editar su configuración

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Configurar los registros del clúster mediante las API de EKS, la consola o eksctl**

Habilita la exportación de registros del plano de control de EKS mediante la API de EKS, la consola o eksctl. AWS opera los hosts del plano de control; instalar agentes de CloudWatch/Fluentd en los nodos de trabajo no habilita esos registros del plano de control. Los operadores no pueden conectarse por SSH a los hosts del plano de control administrado.

**AWS CLI:** inspecciona los ajustes actuales y elige los tipos necesarios. Esta actualización es asíncrona: registra su ID y repite `describe-update` hasta que tenga éxito o informe de un fallo. EKS puede necesitar hasta cinco direcciones IP libres en cada subred del clúster para actualizar los registros.

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

Para habilitar solo API/audit y deshabilitar explícitamente los otros tres tipos, usa el siguiente contenido **alternativo** para `logging` tras revisar los requisitos de auditoría/retención. No ejecutes ambas configuraciones en secuencia ni deshabilites registros necesarios solo para reducir costes:

```json
{
  "clusterLogging": [
    {"types": ["api", "audit"], "enabled": true},
    {"types": ["authenticator", "controllerManager", "scheduler"], "enabled": false}
  ]
}
```

**Alternativa con eksctl:** las operaciones de vista previa y aplicación son distintas; se necesita `--approve` para aplicar el cambio revisado. `--disable-types` puede deshabilitar tipos seleccionados explícitamente cuando esa sea la intención.

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

**Consola:** selecciona el clúster, abre **Observabilidad** y usa **Registro del plano de control → Administrar registros**. Elige cada tipo de registro y guarda la configuración revisada.

| Tipo | Propósito | Prefijo del flujo |
| --- | --- | --- |
| `api` | Diagnósticos de los componentes del servidor de API; las marcas iniciales solo están disponibles si se capturan antes de la rotación de registros | `kube-apiserver-` |
| `audit` | Actividad de la API de Kubernetes registrada según la política de auditoría administrada | `kube-apiserver-audit-` |
| `authenticator` | Diagnósticos de autenticación de IAM | `authenticator-` |
| `controllerManager` | Diagnósticos del bucle de control integrado de Kubernetes | `kube-controller-manager-` |
| `scheduler` | Diagnósticos de programación de Pods | `kube-scheduler-` |

Los registros de auditoría no son un registro de cada solicitud de aplicación ni de cada acción de proceso/red en un nodo. CloudTrail registra por separado la actividad pertinente de la API de AWS. La entrega de registros del plano de control es de mejor esfuerzo, normalmente en unos minutos; habilitarla no recupera los registros que ya rotaron.

**Verificar la exportación:** los registros están en `/aws/eks/<cluster-name>/cluster` en la cuenta/región del clúster. Los sufijos de los flujos rotan, así que inspecciona las horas recientes de los eventos en lugar de suponer que existe un único nombre de flujo permanente.

```bash
aws eks describe-cluster --name "${EXAMPLE_CLUSTER:?}" \
  --region "${EXAMPLE_REGION:?}" --query cluster.logging
aws logs describe-log-streams --region "$EXAMPLE_REGION" \
  --log-group-name "/aws/eks/$EXAMPLE_CLUSTER/cluster" \
  --order-by LastEventTime --descending --max-items 10
```

La ingesta, el almacenamiento y las consultas de CloudWatch tienen costes. Configura la retención y los controles de acceso según tus requisitos y verifica que los tipos de registro necesarios estén llegando. Una actualización de configuración correcta no demuestra que estén presentes todos los eventos históricos esperados. Los recopiladores de registros de los nodos/de las aplicaciones siguen siendo una cuestión independiente del plano de datos.

Referencia: [registro del plano de control de EKS](https://docs.aws.amazon.com/eks/latest/userguide/control-plane-logs.html).

</details>

9. ¿Cómo se cambian los tipos de instancia especificados en la solicitud del grupo de nodos administrado de EKS, cuando no se especificó un tipo de instancia en una plantilla personalizada?
   * A) Editar directamente el campo instanceTypes en la consola
   * B) Crear un grupo de nodos de reemplazo y validar la migración de cargas de trabajo
   * C) Usar kubectl edit node para cambiar el hardware EC2
   * D) Pasar nuevos tipos de instancia a update-nodegroup-config

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Crear un grupo de nodos de reemplazo y validar la migración de cargas de trabajo**

Esta pregunta se refiere a los tipos de instancia especificados en la **solicitud del grupo de nodos administrado**, no a los de una plantilla de lanzamiento personalizada. Esos tipos no se pueden cambiar con `update-nodegroup-config`; crea un grupo nuevo y migra las cargas de trabajo.

Existe una ruta distinta cuando el grupo se creó con una plantilla de lanzamiento personalizada y el tipo de instancia está definido en ella: revisa una nueva versión de la **misma** plantilla y aplícala con `update-nodegroup-version`. Aun así, se reemplazan las instancias. No modifiques las plantillas generadas por EKS, especifiques tipos en ambos lugares ni supongas que una arquitectura de CPU diferente funcionará con la misma AMI/las mismas imágenes.

**1. Crea capacidad de reemplazo.** Comprueba la disponibilidad de instancias, las cuotas, la arquitectura, la capacidad de IP/CNI, las zonas de disponibilidad, el almacenamiento y los permisos del rol de nodo. Los dos comandos son alternativas para un clúster de prueba existente:

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

**2. Verifica el grupo nuevo.** Espera a que esté `ACTIVE`, a que los nodos estén sanos y `Ready`, y a que CNI/DNS funcionen. Enumerar las etiquetas no demuestra que la aplicación esté lista:

```bash
aws eks describe-nodegroup --cluster-name "${EXAMPLE_CLUSTER:?}" \
  --region "${EXAMPLE_REGION:?}" --nodegroup-name "${NEW_NODEGROUP_NAME:?}" \
  --query 'nodegroup.{status:status,health:health,types:instanceTypes,subnets:subnets}'
kubectl --kubeconfig "${EXAMPLE_KUBECONFIG:?}" get nodes \
  -l example.com/migration-target=true -o wide
```

**3. Migra y prueba.** Elige un plan gradual o blue/green específico de la aplicación. Un Service envía tráfico a los puntos de conexión de Pod listos seleccionados, no directamente a un nombre de grupo de nodos. Conserva la capacidad antigua hasta comprender las necesidades de reversión y la compatibilidad de los datos.

Para el vaciado manual, selecciona un nodo antiguo, confirma su etiqueta de grupo de nodos y comprueba primero los PDB, la capacidad sobrante y el almacenamiento local. Este ejemplo no omite deliberadamente la expulsión ni descarta datos de `emptyDir`. Si falla el vaciado, investiga el motivo antes de continuar; el nodo puede permanecer aislado para impedir la programación.

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

Como alternativa, actualiza la plantilla de Pod de la aplicación real para que seleccione el grupo de reemplazo. El ejemplo completo que sigue es una demostración aparte para un espacio de nombres `migration-lab` recién creado, no un manifiesto de reemplazo para una aplicación existente:

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

El PDB exige dos Pods coincidentes sanos durante una expulsión voluntaria. Con tres réplicas, normalmente se puede desalojar una a la vez si las demás condiciones lo permiten. No garantiza la disponibilidad, no protege contra eliminaciones directas ni conserva datos locales al nodo. Comprueba la ubicación, la disponibilidad, el enrutamiento del servicio, la afinidad de zona de los volúmenes persistentes y las copias de seguridad mediante pruebas representativas de la carga de trabajo.

**4. Retira el grupo antiguo solo tras la validación.** No ejecutes los comandos de eliminación de eksctl y AWS ni eludas los PDB para completar la migración. Revisa el clúster/grupo de destino y elimina solo el grupo que pertenece a esta migración:

```bash
# Separate final step, after application/data validation and ownership review.
if [ "${MIGRATION_VERIFIED:?Set yes only after workload and data checks}" = yes ]; then
  eksctl delete nodegroup --cluster "${EXAMPLE_CLUSTER:?}" \
    --region "${EXAMPLE_REGION:?}" --name "${OLD_NODEGROUP_NAME:?}" --approve --wait
fi
```

Conserva el grupo antiguo si falla la validación de la aplicación. Blue/green agrega temporalmente capacidad y costes; no garantiza una reversión sencilla de los cambios con estado. `kubectl edit node` cambia los metadatos de Kubernetes, no el tipo de instancia EC2 subyacente.

Referencias: [actualizaciones de plantillas de lanzamiento](https://docs.aws.amazon.com/eks/latest/userguide/launch-templates.html), [UpdateNodegroupConfig](https://docs.aws.amazon.com/eks/latest/APIReference/API_UpdateNodegroupConfig.html), [drain](https://kubernetes.io/docs/tasks/administer-cluster/safely-drain-node/).

</details>

10. ¿Qué afirmación sobre los taints de grupos de nodos administrados de EKS es correcta?
   * A) Solo kubectl puede configurar taints
   * B) Usa la configuración del grupo de nodos mediante la consola/API o eksctl; verifica por separado el estado de Node existente
   * C) La consola de EKS no puede configurar taints
   * D) Una toleration garantiza que el Pod se programe en el grupo con el taint coincidente

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Usa la configuración del grupo de nodos mediante la consola/API o eksctl; verifica por separado el estado de Node existente**

Los taints de grupos de nodos administrados se pueden configurar mediante la consola/API de EKS o un archivo de configuración de eksctl. La consola es un método válido, así que un cuestionario no debe marcarlo como incorrecto solo porque exista también un método de CLI. `kubectl taint` modifica directamente un objeto Node individual y no es la configuración persistente de los nodos de reemplazo de un grupo administrado.

**Configuración de eksctl:** guarda esto como configuración de grupo de nodos revisada para un clúster existente y un nombre de grupo sin usar; luego ejecuta `eksctl create nodegroup -f nodegroup.yaml`. Usa el campo compatible `taints` en lugar de suponer que existe una opción de CLI.

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

**Alternativa con AWS CLI:** los nombres de efectos de Kubernetes/eksctl usan CamelCase, pero la API de EKS usa nombres en mayúsculas:

| Kubernetes / eksctl | API de EKS | Efecto |
| --- | --- | --- |
| `NoSchedule` | `NO_SCHEDULE` | El planificador rechaza Pods nuevos sin una toleration coincidente; los Pods existentes permanecen |
| `PreferNoSchedule` | `PREFER_NO_SCHEDULE` | Preferencia de programación flexible, no una garantía |
| `NoExecute` | `NO_EXECUTE` | También desaloja los Pods existentes sin una toleration coincidente; `tolerationSeconds` puede retrasar el desalojo |

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

La actualización es asíncrona; espera a que se complete correctamente e inspecciona los taints reales de Node. EKS **no** vuelve a agregar automáticamente un taint de grupo administrado si alguien lo elimina manualmente de un Node existente, aunque la configuración del grupo todavía lo incluya. Restringe quién puede modificar nodos y verifica su estado después de los cambios.

**Ubicación de cargas de trabajo dedicadas:** una toleration permite la programación, pero no obliga a que un Pod se ubique en el grupo con el taint. Combínala con un selector/afinidad de nodos adecuado. Esta demostración completa usa un espacio de nombres `taint-lab` nuevo:

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

Para grupos de GPU, selecciona también instancias/AMI de GPU compatibles e instala un complemento de dispositivos compatible; las cargas de trabajo deben solicitar un recurso extendido como `nvidia.com/gpu`. Un taint `dedicated=gpu` por sí solo no instala controladores ni asigna una GPU. Los taints son controles de programación, no límites de seguridad entre inquilinos.

**Mantenimiento:** un taint temporal de nodo puede impedir la programación normal de Pods nuevos, pero no vacía los Pods en ejecución. Los dos comandos siguientes corresponden al inicio y al final de una ventana de mantenimiento revisada:

```bash
# Individual-node maintenance example; does not evict existing Pods.
kubectl --kubeconfig "${EXAMPLE_KUBECONFIG:?}" taint node \
  "${EXAMPLE_NODE_NAME:?}" maintenance=planned:NoSchedule

# After the maintenance window, remove only this exact example taint.
kubectl --kubeconfig "$EXAMPLE_KUBECONFIG" taint node \
  "$EXAMPLE_NODE_NAME" maintenance=planned:NoSchedule-
```

Usa un procedimiento de vaciado independiente que tenga en cuenta los PDB si se requieren expulsiones. Evita agregar `NoExecute` a un grupo con cargas de trabajo sin revisar el efecto de los desalojos inmediatos. Las marcas de registro de arranque de nodos son otro mecanismo, pero la configuración del grupo administrado es más clara para este caso.

Referencia: [taints de nodos administrados de EKS](https://docs.aws.amazon.com/eks/latest/userguide/node-taints-managed-node-groups.html).

</details>

## Ejercicios prácticos

### Ejercicio 1: Configuración de IRSA (IAM Roles for Service Accounts)

**Escenario:** una carga de trabajo de Linux en un clúster de EKS existente necesita leer un prefijo `training/` aprobado de un bucket de S3. Asígnale un rol dedicado para la carga de trabajo en lugar de una política amplia de S3 en cada nodo.

**Requisitos previos:** usa un clúster de entrenamiento autorizado en la partición comercial de AWS, AWS CLI v2, eksctl y jq. El operador necesita los permisos de IAM y Kubernetes necesarios para este ejercicio. Prepara un objeto existente y no sensible bajo `training/` en un bucket aprobado y establece `S3_BUCKET`/`S3_TEST_KEY`. La política del bucket y cualquier clave de cifrado administrada por el cliente deben permitir el acceso al rol previsto; agrega permisos de KMS con ámbito independiente solo cuando el cifrado del objeto los requiera. Este ejemplo no crea ningún bucket ni objeto.

<details>
<summary>Mostrar solución</summary>

**1. Prepara un espacio de nombres único, un kubeconfig privado y el proveedor OIDC del clúster.** Conserva el directorio generado y el registro de titularidad hasta completar la limpieza. Ejecuta los pasos en la misma sesión de Bash; si un paso falla, inspecciona los recursos registrados antes de volver a intentarlo.

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

IRSA necesita conectividad con STS y acceso a S3 desde la carga de trabajo. Los entornos solo privados necesitan las rutas regionales adecuadas para STS/ECR/S3; crear el proveedor OIDC de IAM desde dentro de la VPC también puede requerir conectividad `oidc-eks`. Restringe de forma independiente el IMDS y el uso de cuentas de servicio; IRSA no constituye por sí sola un límite de aislamiento de Pods.

**2. Crea el rol dedicado y la política de ámbito limitado.** La política de confianza exige tanto la audiencia prevista como el sujeto exacto de espacio de nombres/cuenta de servicio. La política permite enumerar solo el prefijo `training/` del bucket y leer objetos solo bajo ese prefijo. No concede `ListAllMyBuckets`.

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

El rol debe ser de nueva creación. Si falla la creación, el script se detiene antes de adjuntar la política, y el `RoleId` inmutable de IAM se registra para la limpieza. Esto evita adjuntar una política de laboratorio a un rol existente que casualmente tenga el mismo nombre.

**3. Crea la cuenta de servicio y un Pod de prueba de corta duración.** Tres contenedores comprueban la identidad del llamante, enumeran como máximo un objeto del prefijo permitido y leen los metadatos del objeto seleccionado. El ejemplo solo genera recuentos/longitudes y registra metadatos de identidad; no imprime tokens, claves secretas ni contenido de objetos.

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

Los tres contenedores deben tener éxito, y la comprobación de identidad debe coincidir con la cuenta y el rol esperados. Una identidad de rol de nodo es un fallo. Si falla el Pod, inspecciona el estado/los registros de cada contenedor, la confianza de IAM, el prefijo, la política del bucket/la clave y la conectividad; no resuelvas un fallo de autorización adjuntando `AmazonS3ReadOnlyAccess`.

Los cambios de IAM pueden tardar en propagarse. Tras resolver la causa, vuelve a crear el Pod de prueba deliberadamente en el espacio de nombres del que eres titular, en lugar de suponer que la ejecución fallida original demostró el éxito. Que una operación permitida tenga éxito no demuestra que se denieguen todas las demás; revisa todas las políticas de IAM/recursos aplicables y realiza pruebas negativas autorizadas si es necesario.

**4. Limpia el espacio de nombres y el rol de los que eres titular.** El UID del espacio de nombres y el RoleId de IAM protegen contra la reutilización de nombres. Si el espacio de nombres ya no existe, la limpieza puede continuar con el rol registrado. Las políticas en línea inesperadas o las consultas fallidas detienen el resto de la limpieza; investiga los fallos parciales en lugar de eliminar recursos no relacionados.

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

Se conservan el clúster, su proveedor OIDC compartido, el bucket y sus objetos. Verifica que se hayan eliminado el espacio de nombres/el rol y conserva el registro de titularidad si falla algún paso. Detener los Pods no significa que todas las credenciales STS emitidas anteriormente queden invalidadas al instante.

Esta auditoría no aprovisionó el rol ni ejecutó el Pod contra AWS. Las comprobaciones locales validan los manifiestos/políticas generados y las protecciones ante fallos; la propagación real de IAM, la accesibilidad de red y el acceso a S3 siguen siendo pruebas específicas del entorno.

Referencias: [configuración de roles de IRSA](https://docs.aws.amazon.com/eks/latest/userguide/associate-service-account-role.html), [conectividad privada de IRSA](https://docs.aws.amazon.com/eks/latest/userguide/private-clusters.html), [condiciones de políticas de S3](https://docs.aws.amazon.com/AmazonS3/latest/userguide/amazon-s3-policy-keys.html).

</details>

### Ejercicio 2: Refuerzo de la seguridad del clúster de EKS

**Escenario:** evalúa controles de seguridad específicos en un clúster de entrenamiento dedicado de EKS 1.36. Este es un ejercicio de integración, no una configuración de producción probada y lista para usarse.

**Requisitos previos:** administración autorizada del clúster, AWS CLI v2, kubectl y jq; nodos EC2 Linux compatibles; un VPC CNI administrado por EKS compatible con la política de red habilitada; y Pods CoreDNS convencionales en `kube-system`. Usa los requisitos actuales de CNI/kernel de la pregunta básica 3. El ejemplo requiere que la comunicación de referencia entre Pods funcione; las políticas existentes de toda la organización pueden requerir un diseño de prueba aprobado distinto. No instales un segundo CNI solo para realizar este ejercicio.

<details>
<summary>Mostrar solución</summary>

**1. Inspecciona el destino y guarda su configuración actual.** Establece un CIDR real aprobado para la salida de administración, no los rangos de documentación que se muestran en otros lugares. Este ejemplo comprueba que EKS sea 1.36 y que esté habilitada una configuración de políticas de CNI administrado antes de continuar.

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

**2. Aplica en serie los ajustes revisados de punto de conexión/registros.** Lo siguiente mantiene ambas rutas de API y restringe la ruta pública al CIDR aprobado. Antes de elegir una alternativa solo privada, verifica por separado el enrutamiento/DNS/acceso a la API privados, como se describe en la Parte 1. Un tiempo de espera de la función de sondeo no cancela la actualización de AWS; inspecciónala antes de enviar otro cambio.

EKS 1.36 ya cifra con cifrado de sobres los datos de la API de Kubernetes, incluidos los Secrets. Una configuración vacía de clave administrada por el cliente no demuestra que los datos se almacenen en texto sin formato. No crees un segundo clúster ni claves KMS duplicadas para este paso. Si se necesita una CMK, usa el procedimiento revisado y las precauciones sobre el ciclo de vida de la clave de la pregunta básica 4.

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

Los registros del plano de control tienen costes de CloudWatch y su entrega es de mejor esfuerzo. Confirma que los tipos previstos llegan realmente a `/aws/eks/<cluster-name>/cluster` y establece los controles de retención/acceso. Las restricciones del punto de conexión complementan la autorización de IAM/Kubernetes, pero no la sustituyen.

**3. Crea un espacio de nombres Restricted aislado y cargas de trabajo de prueba.** Los tres Deployments proporcionan Pods administrados por controladores para probar de forma fiable las políticas de VPC CNI. Usan un usuario no raíz, seccomp RuntimeDefault, capacidades descartadas, un sistema de archivos raíz de solo lectura y un `emptyDir` para los archivos temporales del backend. No se necesita un token de API de ServiceAccount.

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

Ambos clientes deben llegar al backend antes de aplicar las políticas. Si falla la conectividad de referencia, resuelve primero ese problema en lugar de interpretar el fallo como prueba de aplicación de políticas de red.

**4. Aplica la denegación predeterminada más las reglas de permiso necesarias.** Este es el mismo diseño de políticas que en la pregunta básica 3, limitado al espacio de nombres generado. Permite TCP 8080 del frontend al backend y el tráfico CoreDNS convencional por UDP y TCP. Los puertos de Service y de contenedor coinciden.

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

**5. Verifica conexiones nuevas y controles positivos.** Observa la solicitud denegada del cliente no relacionado cuando converjan las políticas y, después, confirma que la solicitud permitida del frontend y DNS sigan funcionando. Estas observaciones corresponden a esta topología de prueba; inspecciona el estado de las políticas/agentes y sus registros al interpretar resultados inesperados.

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

PSA aplica el estándar Restricted del espacio de nombres. Kyverno o Gatekeeper son opcionales para requisitos que excedan PSA; usa las API actuales de la pregunta básica 6 y adapta la coincidencia del espacio de nombres si vas a probarlos aquí. Una política creada correctamente fuera de este espacio de nombres no aplicaría sus reglas a las cargas de trabajo de este laboratorio.

**6. Revisa controles relacionados sin sustituirlos por recetas incompletas.** Una política IAM de solo lectura `Describe*` no puede operar AWS Load Balancer Controller; usa su política oficial correspondiente a la versión y las condiciones revisadas de recursos/etiquetas. Inspecciona IAM de nodos, IMDS, grupos de seguridad e identidades de complementos. `maxUnavailable` controla la interrupción de una actualización iniciada de nodos administrados; no programa reemplazos periódicos. Usa un plan de mantenimiento/actualización revisado por separado.

**7. Limpia el espacio de nombres de laboratorio.** Usa el UID registrado; conserva los archivos privados de titularidad/configuración si falla la limpieza.

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

Si conservas el clúster, revisa el estado resultante de los puntos de conexión/registros y la retención/el coste continuos de los registros. Si eliminas el clúster de entrenamiento, sigue la guía del ciclo de vida del clúster e inspecciona los registros de CloudWatch conservados y los recursos administrados de forma independiente. No elimines una clave KMS asociada como parte de la limpieza del espacio de nombres.

Esta auditoría no realizó las actualizaciones de AWS ni ejecutó la red de Pods. Las comprobaciones locales abarcan los manifiestos generados, la lógica de políticas y las protecciones ante fallos/de limpieza. IAM, enrutamiento, admisión, disponibilidad y recuperación en producción aún requieren verificación específica del entorno.

Referencias: [requisitos de políticas de red](https://docs.aws.amazon.com/eks/latest/userguide/cni-network-policy.html), [cifrado de sobres predeterminado](https://docs.aws.amazon.com/eks/latest/userguide/envelope-encryption.html), [acceso al punto de conexión de la API](https://docs.aws.amazon.com/eks/latest/userguide/cluster-endpoint.html), [registros del plano de control](https://docs.aws.amazon.com/eks/latest/userguide/control-plane-logs.html), [Pod Security Standards](https://kubernetes.io/docs/concepts/security/pod-security-standards/).

</details>

## Temas avanzados

Las siguientes son preguntas sobre temas avanzados de la creación de clústeres de Amazon EKS. Esta sección evalúa tu comprensión de los conceptos avanzados y las prácticas recomendadas para crear clústeres de EKS.

1. ¿Cuál de estas opciones NO es un requisito para un clúster IPv6 de EKS?
   * A) VPC/subredes con direccionamiento IPv4 e IPv6
   * B) Una configuración de CNI compatible y permisos de IAM para IPv6
   * C) Nodos EC2 Nitro compatibles o Fargate
   * D) Una familia de instancias EC2 solo IPv6 independiente

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: D) Una familia de instancias EC2 solo IPv6 independiente**

EKS no requiere una «familia de instancias solo IPv6» independiente. Sí requiere **nodos EC2 Nitro compatibles o Fargate**, así que es incorrecta la afirmación de que funcionará cualquier tipo de instancia EC2 ordinario.

**Requisitos previos:**

1. Selecciona la familia de direcciones IP IPv6 al crear un clúster **nuevo**. Es inmutable; aplicar `ENABLE_IPV6` a un clúster IPv4 existente no lo convierte.
2. Asocia CIDR IPv4 e IPv6 a la VPC/las subredes y habilita la asignación automática de IPv6 en las subredes de nodos. Revisa las rutas IPv6, los grupos de seguridad, DNS y la conectividad de administración. Los ID de subred deben corresponder a la VPC/las zonas de disponibilidad previstas.
3. Usa una versión de VPC CNI compatible configurada para IPv6 y delegación de prefijos. La versión 1.10.1 es el mínimo histórico, no una instalación recomendada actual. No apliques un manifiesto antiguo de la versión 1.10 sobre un complemento administrado actual.
4. Proporciona los permisos de IAM para IPv6 de CNI, preferiblemente en su propio rol de carga de trabajo. La política IPv4 `AmazonEKS_CNI_Policy` no es la política de IPv6. Revisa el rol/las políticas que genera el flujo de trabajo de IPv6/complementos de eksctl.

```bash
aws ec2 describe-subnets --region "${EXAMPLE_REGION:?}" \
  --subnet-ids "${PRIVATE_SUBNET_A:?}" "${PRIVATE_SUBNET_B:?}" \
  --query 'Subnets[].{id:SubnetId,az:AvailabilityZone,ipv4:CidrBlock,ipv6:Ipv6CidrBlockAssociationSet,autoIPv6:AssignIpv6AddressOnCreation}'
aws eks describe-addon-versions --region "$EXAMPLE_REGION" \
  --addon-name vpc-cni --kubernetes-version 1.36
```

**Ejemplo:** usa subredes privadas de doble pila existentes y ya preparadas, y un grupo de nodos AL2023 basado en Nitro. Sustituye los ID de ejemplo y el CIDR de acceso público. La forma `kubernetesNetworkConfig.ipFamily: IPv6` es correcta para eksctl; la API de EKS usa `ipv6` en minúsculas.

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

Guarda la configuración revisada como `ipv6-cluster.yaml`. Selecciona y registra las versiones exactas compatibles de los complementos para tu entorno; las versiones omitidas arriba permiten que la herramienta elija sus valores predeterminados compatibles. Esto no significa que deba instalarse una compilación específica de CNI histórica.

```bash
# After reviewing real IDs, routing, IAM, access and compatible addon versions.
eksctl create cluster -f ipv6-cluster.yaml --kubeconfig "${EXAMPLE_KUBECONFIG:?}"
```

La configuración no prepara por sí sola las rutas/los atributos IPv6 de la subred existente. Confirma también las entradas de acceso creadas y los permisos de CNI, así como la disponibilidad de los nodos/complementos. Esta auditoría no creó un clúster IPv6.

**Direccionamiento y tráfico:**

- EKS expone direcciones IPv6 de Pod y asigna ClusterIP IPv6. Una VPC de doble pila no convierte los Pods/Services de EKS en recursos de doble pila.
- Las direcciones IPv6 de Pod proceden del direccionamiento de subred; las direcciones IPv6 de Service usan un rango local único asignado por EKS dentro de `fc00::/7`. No supongas que el CIDR fijo de Service es `fd00::/108`.
- Los nodos EC2 tienen direcciones IPv4 e IPv6. Un Pod también puede recibir una dirección IPv4 local al host no informada para llegar a destinos IPv4 externos, con NAT de origen a través del nodo. El acceso a Internet IPv4 desde nodos privados aún puede necesitar NAT; IPv6 no elimina todas las dependencias de NAT.
- El tráfico IPv6 nativo a Internet puede usar una puerta de enlace de Internet o una puerta de enlace de Internet de salida únicamente, según el sentido previsto y el diseño de seguridad. No es obligatorio usar una puerta de enlace de salida únicamente para todos los clústeres IPv6.
- El balanceo de carga hacia Pods IPv6 requiere un controlador/configuración de balanceador compatible con destinos IP. El acceso de clientes IPv4 puede seguir ofreciéndose mediante una interfaz frontal de doble pila adecuada; no confundas el direccionamiento de Pods con la familia de IP del cliente.
- Windows y las redes personalizadas de VPC CNI no son compatibles con clústeres IPv6 de EKS. Comprueba la compatibilidad de controladores de almacenamiento, complementos y dependencias externas antes de elegir la familia.

```bash
aws eks describe-cluster --name "${IPV6_CLUSTER_NAME:?}" \
  --region "${EXAMPLE_REGION:?}" --query cluster.kubernetesNetworkConfig
kubectl --kubeconfig "${EXAMPLE_KUBECONFIG:?}" -n kube-system get pods -o wide
kubectl --kubeconfig "$EXAMPLE_KUBECONFIG" -n kube-system get services -o wide
kubectl --kubeconfig "$EXAMPLE_KUBECONFIG" get nodes -o wide
```

Inspecciona las direcciones reales y prueba DNS, además de los destinos IPv6/IPv4 necesarios. Enumerar direcciones IPv6 por sí solo no es una prueba de conectividad o disponibilidad. Limpia solo los recursos de laboratorio registrados siguiendo el procedimiento del ciclo de vida del clúster.

Referencias: [comportamiento IPv6 de EKS](https://docs.aws.amazon.com/eks/latest/userguide/cni-ipv6.html), [tutorial IPv6 de eksctl](https://docs.aws.amazon.com/eks/latest/userguide/deploy-ipv6-cluster.html), [rol IAM de CNI](https://docs.aws.amazon.com/eks/latest/userguide/cni-iam-role.html), [respuesta de configuración de red](https://docs.aws.amazon.com/eks/latest/APIReference/API_KubernetesNetworkConfigResponse.html).

</details>

2. ¿Qué habilita principalmente la red personalizada de VPC CNI?
   * A) Subredes/grupos de seguridad de Pod distintos de la interfaz principal del nodo, dentro de la misma VPC
   * B) La prevención automática de todo solapamiento de CIDR
   * C) El cifrado de todas las conexiones entre nodos
   * D) Una reconciliación más rápida del plano de control

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A) Subredes/grupos de seguridad de Pod distintos de la interfaz principal del nodo, dentro de la misma VPC**

La red personalizada de VPC CNI permite que **los Pods EC2 Linux IPv4 usen subredes/grupos de seguridad alternativos dentro de la misma VPC que sus nodos**. El rango de Pods no queda fuera de los CIDR asociados a la VPC. Un CIDR secundario de VPC puede proporcionar espacio de direcciones adicional, pero usar uno no evita automáticamente los solapamientos con otras redes.

De forma predeterminada, VPC CNI crea ENI secundarias en la subred principal del nodo y usa direcciones de esas ENI, así como direcciones aptas de la ENI principal. Con redes personalizadas, las IP habituales de los Pods proceden de ENI secundarias configuradas mediante `ENIConfig`; la ENI principal no se usa para asignar esas IP de Pod. Los Pods con red de host siguen usando la red del host.

**Secuencia de configuración:**

1. Planifica el espacio IPv4 disponible, el enrutamiento y los permisos. Si agregas un CIDR secundario, comprueba las restricciones de asociación de VPC y los solapamientos con redes conectadas. Los ejemplos de AWS que usan espacio compartido `100.64.0.0/10` no garantizan que el rango esté libre en tu entorno.
2. Prepara subredes de Pod alternativas en la **misma VPC y la zona de disponibilidad correspondiente** a la subred principal de cada nodo. Revisa las rutas de las subredes y las reglas de los grupos de seguridad, incluidas las dependencias de API/DNS/cargas de trabajo.
3. Crea un `ENIConfig` por cada subred de Pod prevista. El siguiente ejemplo usa una subred por zona de disponibilidad; sustituye todos los ID. No sobrescribas configuraciones de ámbito de clúster existentes que pertenezcan a otro despliegue.

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

4. Configura las redes personalizadas y la selección de ENIConfig mediante el responsable de la instalación de CNI. Para un complemento administrado por EKS, combina estos ajustes de entorno con su configuración completa revisada después de comprobar el esquema de la versión instalada:

```yaml
# Merge with existing managed-addon configuration; do not discard other env values.
env:
  AWS_VPC_K8S_CNI_CUSTOM_NETWORK_CFG: "true"
  ENI_CONFIG_LABEL_DEF: topology.kubernetes.io/zone
```

Para un DaemonSet autoadministrado, la actualización equivalente aparece a continuación. Afecta el comportamiento de CNI en todo el clúster y debe formar parte de una migración planificada, no de un despliegue de aplicación improvisado:

```bash
# Self-managed CNI alternative, after preparing ENIConfig/subnets and a rollout plan.
# For an EKS-managed addon, use its supported configuration-values workflow instead.
kubectl --kubeconfig "${EXAMPLE_KUBECONFIG:?}" -n kube-system \
  set env daemonset/aws-node AWS_VPC_K8S_CNI_CUSTOM_NETWORK_CFG=true \
  ENI_CONFIG_LABEL_DEF=topology.kubernetes.io/zone
kubectl --kubeconfig "$EXAMPLE_KUBECONFIG" -n kube-system \
  rollout status daemonset/aws-node --timeout=5m
```

5. Aprovisiona y valida nodos de reemplazo con la configuración necesaria y luego migra las cargas de trabajo usando vaciado que tenga en cuenta los PDB y pruebas de aplicaciones. Cambiar las variables de entorno no reasigna las direcciones de los Pods existentes. AWS recomienda usar nodos nuevos para la configuración de redes personalizadas. Conserva la capacidad antigua hasta verificar la migración.

Cuando `ENI_CONFIG_LABEL_DEF=topology.kubernetes.io/zone`, asigna a cada `ENIConfig` el nombre de la zona de disponibilidad correspondiente. Si se necesitan varias subredes de Pod en una misma zona de disponibilidad, utiliza nombres únicos y una asignación revisada de etiquetas/anotaciones de nodo personalizadas. La selección existente de ENIConfig mediante anotación puede prevalecer sobre la selección basada en etiquetas. No cambies la etiqueta de topología real de un nodo para forzarlo a usar una subred de otra zona de disponibilidad.

**Límites de capacidad y seguridad:**

- Excluir la ENI principal reduce la capacidad de Pods en modo de IP secundaria. La delegación de prefijos puede aumentar la capacidad de direcciones, pero siguen importando la disponibilidad de prefijos de subred, los límites de instancia compatibles y `maxPods` de kubelet. Calcula y prueba la densidad en lugar de copiar un valor universal.
- Con el valor predeterminado `AWS_VPC_K8S_CNI_EXTERNALSNAT=false`, el tráfico fuera de los CIDR asociados a la VPC recibe NAT de origen a través de la interfaz principal del nodo y usa sus subredes/grupos de seguridad. No supongas que el grupo de seguridad de ENIConfig filtra todo el tráfico externo.
- Si se combina con Security Groups for Pods, el grupo `SecurityGroupPolicy` del Pod prevalece sobre el grupo de ENIConfig para ese Pod. Comprueba los modos de aplicación/SNAT compatibles.
- Las redes personalizadas no constituyen por sí solas cifrado ni un límite de aislamiento entre inquilinos, y no resuelven el enrutamiento con CIDR superpuestos sin un diseño de red adecuado.
- No son compatibles con EKS IPv6 ni con nodos Windows. Fargate selecciona subredes mediante sus perfiles, en lugar de usar asignaciones ENIConfig de nodos EC2.

```bash
kubectl --kubeconfig "${EXAMPLE_KUBECONFIG:?}" get eniconfigs
kubectl --kubeconfig "$EXAMPLE_KUBECONFIG" get nodes -L topology.kubernetes.io/zone
kubectl --kubeconfig "$EXAMPLE_KUBECONFIG" -n "${APPLICATION_NAMESPACE:?}" get pods -o wide
aws ec2 describe-subnets --region "${EXAMPLE_REGION:?}" \
  --subnet-ids "${POD_SUBNET_A:?}" "${POD_SUBNET_B:?}" \
  --query 'Subnets[].{id:SubnetId,vpc:VpcId,az:AvailabilityZone,cidr:CidrBlock,free:AvailableIpAddressCount}'
```

Verifica las IP de los Pods frente a las subredes previstas, las zonas de disponibilidad de los nodos, la conectividad DNS/API y los flujos necesarios de las aplicaciones. Una lista de `ENIConfig` no demuestra por sí sola la migración ni el aislamiento. Este ejemplo se revisó de forma estática; no se ejecutó ningún cambio de CNI, migración de nodos ni evaluación comparativa de red.

Referencias: [redes personalizadas](https://docs.aws.amazon.com/eks/latest/userguide/cni-custom-network.html), [configuración y migración](https://docs.aws.amazon.com/eks/latest/userguide/cni-custom-network-tutorial.html), [consideraciones sobre redes personalizadas](https://docs.aws.amazon.com/eks/latest/best-practices/custom-networking.html).

</details>

3. ¿Cuál de estas opciones NO es un requisito para cargas de trabajo Windows en EKS?
   * A) Al menos dos grupos de nodos administrados de Amazon Linux
   * B) Capacidad Linux o Fargate para Pods del sistema que solo funcionan en Linux
   * C) Una AMI de Windows y una imagen de contenedor compatibles
   * D) IPAM de Windows y autenticación IAM/de nodo correcta

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A) Al menos dos grupos de nodos administrados de Amazon Linux**

No se requieren dos grupos de nodos administrados de Amazon Linux. EKS necesita **capacidad Linux o Fargate para Pods del sistema que solo funcionan en Linux, como CoreDNS**; esto no exige una distribución Linux específica ni dos grupos separados. Planifica las réplicas y la ubicación entre dominios de fallo para lograr disponibilidad, en lugar de tratar el mínimo como un diseño de alta disponibilidad.

**Requisitos previos de Windows:**

1. Usa un clúster EKS **IPv4** actualmente compatible y una AMI de Windows optimizada para EKS compatible. AWS publica variantes de Windows Server 2019, 2022 y 2025; este ejemplo usa deliberadamente 2022, no una base de compatibilidad obsoleta de Kubernetes 1.14/1.23.
2. Confirma que los permisos `AmazonEKSVPCResourceController` estén en el rol IAM del clúster y habilita IPAM de Windows en la configuración `kube-system/amazon-vpc-cni`.
3. Deja que el controlador de recursos VPC administrado realice IPAM de Windows. No instales los antiguos manifiestos del controlador de recursos del plano de datos/webhook de admisión desde una URL `master` cambiante.
4. Usa un rol IAM de nodo Windows dedicado y la autenticación correcta del nodo. La autenticación de API usa una entrada de acceso `EC2_WINDOWS`; los grupos de nodos administrados gestionan sus entradas de acceso de nodo. Con el `aws-auth` heredado, conserva el grupo obligatorio `eks:kube-proxy-windows`, además de los grupos de arranque/nodo.

```bash
aws iam list-attached-role-policies --role-name "${EKS_CLUSTER_ROLE_NAME:?}"

# If missing, attach to the reviewed cluster role, not to every worker role.
aws iam attach-role-policy --role-name "$EKS_CLUSTER_ROLE_NAME" \
  --policy-arn arn:aws:iam::aws:policy/AmazonEKSVPCResourceController
```

El ajuste de IPAM de Windows pertenece a la configuración de VPC CNI existente. Si EKS o Helm administra esa configuración, usa los ajustes compatibles de su responsable en lugar de reemplazar todo el ConfigMap:

```yaml
# Relevant ConfigMap data; merge through the owning addon/Helm configuration.
data:
  enable-windows-ipam: "true"
```

**Ejemplo de grupo de nodos:** guarda esto como `windows-nodegroup.yaml` después de revisar el clúster existente, las subredes, la disponibilidad de la AMI y IAM. El taint evita que las cargas de trabajo Linux normales se ubiquen accidentalmente en estos nodos; las plantillas de cargas de trabajo Linux también deberían seleccionar Linux explícitamente.

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

**Ejemplo de carga de trabajo:** crea un espacio de nombres `windows-lab` sin usar y despliega una imagen compatible con la compilación de Windows del nodo. Las AMI de Windows optimizadas para EKS incluyen kubelet, **Windows kube-proxy**, containerd y componentes de host relacionados; kube-proxy no es exclusivo de Linux.

Usa la imagen oficial de IIS con su punto de entrada ServiceMonitor existente. La antigua ubicación de descarga de ServiceMonitor `dotnetbinaries.blob.core.windows.net` se retiró; instalar IIS y descargar un binario cada vez que se inicia un Pod no es necesario aquí.

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

La etiqueta de imagen se verificó en el README de imágenes de Microsoft y en los metadatos del registro. Durante esta auditoría no se descargaron sus capas ni se ejecutó la carga de trabajo de Windows. Los valores de recursos son ilustrativos. Comprueba el despliegue/la disponibilidad real, DNS, el tráfico de la aplicación y la compatibilidad de compilación del host/contenedor antes de usarla en producción.

**Límites de las funciones compatibles:**

- Windows no puede ejecutarse como Pods de EKS Fargate, nodos de EKS Auto Mode ni EKS Hybrid Nodes. No es compatible con EKS IPv6, redes personalizadas de VPC CNI ni Security Groups for Pods.
- Los Pods Windows normales difieren de los contenedores Linux privilegiados. Los Pods **HostProcess** de Windows pueden usar la red del host, así que es incorrecto afirmar que «Windows nunca admite hostNetwork». HostProcess requiere una revisión de seguridad elevada aparte.
- La capacidad de red/IP de Windows difiere de la de Linux. Revisa los límites de una sola ENI y la delegación de prefijos compatible en lugar de suponer que se aplican los cálculos de densidad de Pods de Linux.
- Elige controladores de almacenamiento compatibles con Windows y valida la semántica de volúmenes/rutas. No supongas que los permisos hostPath de Linux ni todas las funciones de CSI son portátiles.
- Los nodos Windows optimizados para EKS usan containerd; las imágenes de aplicaciones Linux deben ejecutarse en nodos Linux. Verifica la ubicación de complementos del sistema y aplicaciones en clústeres con sistemas operativos mixtos.

Referencias: [compatibilidad de Windows en EKS](https://docs.aws.amazon.com/eks/latest/userguide/windows-support.html), [AMI optimizadas para Windows](https://docs.aws.amazon.com/eks/latest/userguide/eks-optimized-windows-ami.html), [imagen de IIS de Microsoft](https://github.com/microsoft/iis-docker), [Windows HostProcess](https://kubernetes.io/docs/tasks/configure-pod-container/create-hostprocess-pod/).

</details>



4. ¿Qué ajuste exige un token de sesión para las solicitudes de metadatos de instancias EC2?
   * A) HttpTokens=required (solo IMDSv2)
   * B) Una regla de grupo de seguridad para 169.254.169.254
   * C) Una etiqueta Node de Kubernetes
   * D) Solo el nombre de una ServiceAccount de aplicación

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A) HttpTokens=required (solo IMDSv2)**

Exigir IMDSv2 (`HttpTokens: required`) deshabilita las llamadas IMDSv1 sin token y añade defensa en profundidad. **No** hace imposibles todas las SSRF ni proporciona un límite de seguridad entre contenedores que comparten un host.

**Ajustes de la plantilla de lanzamiento:** lo siguiente es un fragmento de `LaunchTemplateData` de EC2, no un campo `managedNodeGroups.metadataOptions`. El límite de saltos 1 presupone que los Pods normales usan IRSA/Pod Identity en lugar de obtener credenciales del nodo:

```json
{
  "MetadataOptions": {
    "HttpTokens": "required",
    "HttpPutResponseHopLimit": 1,
    "HttpEndpoint": "enabled"
  }
}
```

El límite de saltos se aplica a la **respuesta PUT** del token IMDS, no a todas las solicitudes de metadatos. Un contenedor que necesite legítimamente IMDSv2 puede requerir un límite de saltos 2. Comprueba la compatibilidad y traslada los permisos de las aplicaciones a roles de carga de trabajo; no aumentes el límite solo para ocultar un fallo inexplicado.

Usa una versión existente y revisada de la plantilla mediante los campos compatibles `launchTemplate.id/version` de eksctl. Se debe sustituir el ID de ejemplo; `--launch-template-name` no es la interfaz documentada de `eksctl create nodegroup`:

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

**Alternativa con eksctl:** se pueden usar los campos compatibles `disableIMDSv1` y `disablePodIMDS` para un grupo de nodos nuevo. Prepara primero las identidades de carga de trabajo necesarias. `disablePodIMDS` se aplica a Pods que no usan la red del host y no se puede combinar con `withAddonPolicies`.

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

Estas dos configuraciones son alternativas; revisa la plantilla generada real y los ajustes de metadatos de los nodos. Los valores predeterminados dependen de los ajustes de lanzamiento de la instancia, de los valores predeterminados de cuenta/región y de la compatibilidad con metadatos de la AMI; los ajustes de lanzamiento tienen prioridad. No supongas que todas las AMI/grupos de nodos tienen un límite de saltos predeterminado de 1.

**Nodos existentes:** se puede desplegar una versión nueva de la misma plantilla de lanzamiento personalizada mediante una actualización del grupo de nodos administrado. También se pueden cambiar los ajustes de metadatos de instancias EC2 individuales en ejecución/detenidas, sujetos a restricciones de IAM/SCP, pero eso por sí solo no actualiza la configuración de los futuros nodos de reemplazo:

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

Verifica que las opciones hayan llegado al estado `applied` y que los agentes del nodo, la extracción de imágenes y las credenciales de carga de trabajo sigan funcionando. No deshabilites todo el punto de conexión de metadatos solo porque una aplicación use IRSA: los componentes del host pueden seguir dependiendo del perfil de instancia del nodo y de sus metadatos.

**Controles adicionales:**

- Limita el alcance del rol del nodo y asigna a las aplicaciones sus propios roles. IRSA/Pod Identity no impide por sí solo otras vías de acceso al IMDS del nodo.
- Los Pods `hostNetwork` pueden acceder al IMDS, y una carga de trabajo del host con suficientes privilegios puede eludir el aislamiento de red de Pods. Controla por separado los privilegios de Pods y el acceso al host.
- Los grupos de seguridad no filtran el servicio de metadatos de enlace local de la instancia. Si aplicas restricciones adicionales de host/red, ten en cuenta la ruta real del Pod y también el punto de conexión IMDS IPv6 opcional (`fd00:ec2::254`), además de IPv4. La antigua regla DNAT improvisada `PREROUTING -i eth0` no es una restricción general fiable de IMDS para Pods.
- Usa SDK compatibles y prueba el acceso a metadatos sin imprimir tokens de sesión ni valores de credenciales de IAM. Observa los ajustes reales de metadatos de la instancia en lugar de suponer que las etiquetas de Kubernetes del nodo demuestran su aplicación.

Referencias: [opciones y precedencia de IMDS](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/configuring-instance-metadata-options.html), [comportamiento de IMDSv2](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/configuring-instance-metadata-service.html), [opciones de seguridad de eksctl](https://docs.aws.amazon.com/eks/latest/eksctl/security.html), [límites de aislamiento de IRSA](https://docs.aws.amazon.com/eks/latest/userguide/iam-roles-for-service-accounts.html).

</details>

5. ¿Qué tarea queda fuera del propósito de una configuración de arranque de nodo EC2?
   * A) Modificar los procesos del plano de control administrado por EKS
   * B) Configurar software revisado que ya está instalado en una AMI personalizada
   * C) Aplicar ajustes del host validados para la carga de trabajo
   * D) Establecer etiquetas y taints compatibles para grupos de nodos

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A) Modificar los procesos del plano de control administrado por EKS**

La configuración de arranque de nodo configura **hosts de nodo**, no el servidor de API, el planificador, el administrador de controladores ni etcd administrados por EKS. Para AL2023, usa `nodeadm` y las rutas compatibles de eksctl/plantillas de lanzamiento; los ejemplos antiguos de AL2 `bootstrap.sh`/`kubeletExtraArgs` no se aplican.

**Instala y configura el software deliberadamente.** Usa un paquete verificado para el sistema operativo/la arquitectura de destino, preferiblemente integrado en una AMI revisada. Un RPM `latest` no verificado descargado en cada arranque no constituye una instalación reproducible. Un agente del host también necesita los permisos de IAM y la conectividad privada/pública adecuadas con los servicios.

El siguiente ejemplo opcional de host AL2023 presupone que el agente de CloudWatch ya está instalado. Configura métricas de memoria/swap del host e inicia el agente; si se ejecuta con acceso funcional a AWS, envía telemetría facturable. No es una instrucción para ejecutarlo en la estación de trabajo de administración, Bottlerocket o Auto Mode:

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

**Ajuste del kernel:** usa evidencia de la carga de trabajo y los requisitos reales del kernel/CNI. Los valores del ejemplo original se conservan aquí como referencias de ajuste no validadas, no como recomendaciones universales de rendimiento:

| Ajuste de ejemplo | Valor del ejemplo original | Requisito de revisión |
| --- | --- | --- |
| `net.ipv4.ip_forward` | `1` | Requisitos de enrutamiento del nodo/CNI |
| `net.bridge.bridge-nf-call-iptables` | `1` | Si el módulo bridge y el plano de datos de CNI lo requieren |
| `net.ipv4.tcp_keepalive_time` | `600` | Comportamiento de los tiempos de espera de aplicaciones/conexiones |
| `net.ipv4.tcp_max_syn_backlog`, `net.core.somaxconn`, `net.core.netdev_max_backlog` | `40000` | Presión real de colas, memoria y mediciones de cargas de trabajo |
| `vm.max_map_count` | `262144` | Requisitos de asignación de memoria de la aplicación específica |

No apliques esta tabla como un script general de nodos. Registra la referencia, valida los cambios en un grupo de prueba y conserva una ruta de reversión.

**Discos:** no ejecutes nunca `mkfs` en un `/dev/nvme1n1` supuesto. La enumeración NVMe no es un identificador estable de titularidad y el dispositivo puede contener datos necesarios. Identifica el volumen EBS previsto mediante el ID/serial del volumen, confirma que sea un dispositivo recién aprovisionado y descartable o preparado expresamente de otro modo, e inspecciona particiones/sistemas de archivos/montajes antes de formatear. Usa identificadores estables, como los UUID del sistema de archivos, para la configuración de montajes persistentes.

```bash
# Read-only inspection on the specifically authorized test node.
lsblk --output NAME,PATH,TYPE,SIZE,FSTYPE,UUID,MOUNTPOINTS,SERIAL
findmnt
sysctl net.ipv4.ip_forward vm.max_map_count
```

Para datos persistentes de aplicaciones, prefiere el ciclo de vida de CSI/PV adecuado en vez de vincularlos a los discos desechables de un nodo. Los comandos de inspección anteriores no formatean ni montan nada.

**Etiquetas, taints y seguridad:** usa los campos de etiquetas/taints de grupos de nodos administrados y un dominio que controles; no sobrescribas etiquetas de topología/grupo de nodos administradas por el proveedor. Usa una AMI revisada y un diseño de grupo de seguridad/CNI para reforzar la seguridad del host. Los cambios improvisados de SSH/firewall durante el arranque pueden entrar en conflicto con las reglas existentes o cortar el acceso, y no constituyen un procedimiento de refuerzo completo.

**Datos de usuario de la plantilla de lanzamiento:** con una AMI AL2023 seleccionada por EKS y sin `ImageId` personalizado, EKS proporciona el NodeConfig predeterminado necesario. Una personalización MIME mínima puede tener este aspecto:

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

Usa el ID/la versión de plantilla devueltos mediante `managedNodeGroups[].launchTemplate`, como en la pregunta avanzada 4. Si especificas un ID de AMI personalizado fuera de una configuración generada por eksctl, proporciona también el NodeConfig completo del clúster descrito en la pregunta básica 5. No inicies kubelet manualmente ni vuelvas a llamar a `nodeadm init`.

**Alternativa con eksctl:** la configuración siguiente usa campos compatibles de grupos de nodos y un comando inocuo previo al arranque que crea un directorio. Agrega solo personalizaciones de host revisadas. `preBootstrapCommands` contiene comandos de shell; `overrideBootstrapCommand` de AL2023, cuando se necesita para personalizar NodeConfig, contiene YAML de NodeConfig.

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

Los ejemplos no se han arrancado como receta de nodo de producción. Valida la procedencia de los paquetes, la configuración efectiva de nodeadm/kubelet, los fallos de inicio, la red y el estado de las cargas de trabajo en tu entorno.

**CoreDNS es una carga de trabajo/complemento del plano de datos**, normalmente un Deployment en EC2 Linux o en capacidad Fargate compatible, no un proceso del plano de control administrado por EKS. Configúralo mediante el flujo de trabajo del complemento/Kubernetes. Los ajustes del plano de control de EKS expuestos por la API, como el registro, son independientes de los datos de usuario de los nodos.

Referencias: [inicialización de AL2023](https://docs.aws.amazon.com/eks/latest/userguide/al2023.html), [arranque con eksctl](https://docs.aws.amazon.com/eks/latest/eksctl/node-bootstrapping.html), [restricciones de plantillas de lanzamiento](https://docs.aws.amazon.com/eks/latest/userguide/launch-templates.html), [configuración del agente de CloudWatch](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch-Agent-Configuration-File-Details.html).

</details>
