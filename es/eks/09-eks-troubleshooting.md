# Solución de problemas de Amazon EKS

> **Última actualización**: 12 de septiembre de 2026

Al operar clústeres de Amazon EKS, pueden surgir diversos problemas. Este documento describe problemas comunes que pueden presentarse en los clústeres de EKS y sus soluciones.

## Tabla de contenido

1. [Fundamentos de la solución de problemas](#troubleshooting-basics)
2. [Problemas de creación y administración de clústeres](#cluster-creation-and-management-issues)
3. [Problemas de redes](#networking-issues)
4. [Problemas de nodos y Pods](#node-and-pod-issues)
5. [Problemas de IAM y autenticación](#iam-and-authentication-issues)
6. [Problemas de almacenamiento](#storage-issues)
7. [Problemas de registro y supervisión](#logging-and-monitoring-issues)
8. [Problemas de rendimiento](#performance-issues)
9. [Problemas de actualización](#upgrade-issues)
10. [Mensajes de error comunes y soluciones](#common-error-messages-and-solutions)

## Fundamentos de la solución de problemas {#troubleshooting-basics}

![Fundamentos de la solución de problemas de EKS: identificar los síntomas, recopilar evidencias, probar hipótesis, corregir, verificar y documentar.](../.gitbook/assets/en-eks-09-eks-troubleshooting-0.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-09-eks-troubleshooting-0.html)

### Enfoque para solucionar problemas

1. Identifique el síntoma, los usuarios o las cargas de trabajo afectados y el período del incidente.
2. Recopile el estado, los registros, los eventos y las métricas pertinentes antes de modificar recursos.
3. Compare las hipótesis alternativas con las evidencias; no considere que un error genérico demuestra una causa.
4. Aplique una corrección específica, con un responsable definido y efectos conocidos en los datos y la disponibilidad.
5. Verifique la recuperación con el comportamiento de la aplicación y las métricas, no solo con el código de salida de un comando.
6. Registre la causa, los cambios, los resultados, las incertidumbres restantes y las medidas preventivas.

Los comandos de este capítulo son plantillas para un entorno revisado, no un único script que se deba ejecutar de principio a fin. Consultar un recurso, crear una carga de trabajo de depuración, reiniciar un componente y eliminar infraestructura tienen efectos distintos. Durante esta revisión no se realizaron operaciones activas en AWS/Kubernetes.

### Herramientas y comandos esenciales

Para un clúster **existente**, configure la cuenta, la región, el clúster y el contexto de kubectl previstos, y luego compruebe que coincidan. No deduzca el nombre de un clúster a partir de un alias de contexto arbitrario. Si la creación falló antes de que hubiera un clúster utilizable, use la evidencia de la cuenta/región y de la solicitud o pila original que se indica en la sección de creación.

```bash
set -euo pipefail
: "${AWS_REGION:?Set the intended Region}"
: "${CLUSTER_NAME:?Set the existing cluster name}"
: "${EXPECTED_ACCOUNT_ID:?Set the intended 12-digit account ID}"
: "${KUBE_CONTEXT:?Set the explicit kubectl context}"
ACTUAL_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
if [ "$ACTUAL_ACCOUNT_ID" != "$EXPECTED_ACCOUNT_ID" ]; then
  echo "Account mismatch" >&2; exit 1
fi
CLUSTER_ENDPOINT=$(aws eks describe-cluster --name "$CLUSTER_NAME" --region "$AWS_REGION" \
  --query cluster.endpoint --output text)
KUBE_ENDPOINT=$(kubectl config view --context "$KUBE_CONTEXT" --minify \
  -o jsonpath='{.clusters[0].cluster.server}')
if [ "$CLUSTER_ENDPOINT" != "$KUBE_ENDPOINT" ]; then
  echo "kubectl context does not match the selected EKS cluster" >&2; exit 1
fi
export AWS_REGION CLUSTER_NAME EXPECTED_ACCOUNT_ID KUBE_CONTEXT
```

#### AWS CLI y eksctl

```bash
aws eks describe-cluster --name "$CLUSTER_NAME" --region "$AWS_REGION" \
  --query 'cluster.{arn:arn,status:status,version:version,health:health,access:accessConfig}'
aws eks list-nodegroups --cluster-name "$CLUSTER_NAME" --region "$AWS_REGION"
aws eks list-addons --cluster-name "$CLUSTER_NAME" --region "$AWS_REGION"
eksctl get nodegroup --cluster "$CLUSTER_NAME" --region "$AWS_REGION"
```

Estos comandos enumeran los grupos de nodos administrados y los complementos de EKS instalados, pero no todos los controladores autoadministrados ni los recursos de cómputo. Antes de elegir un procedimiento, registre el propietario real y el tipo de cómputo.

#### kubectl

```bash
kubectl --context "$KUBE_CONTEXT" get nodes -o wide
kubectl --context "$KUBE_CONTEXT" get pods -A -o wide
kubectl --context "$KUBE_CONTEXT" get services -A
kubectl --context "$KUBE_CONTEXT" get events -A --sort-by='.metadata.creationTimestamp'
: "${NAMESPACE:?}"; : "${POD_NAME:?}"
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" describe pod "$POD_NAME"
```

Especifique explícitamente el espacio de nombres, el Pod, el contenedor y el nodo afectados. La salida de `describe` y los registros de la aplicación pueden incluir información operativa confidencial. `kubectl auth can-i` comprueba la autorización para una acción concreta; `aws sts get-caller-identity` identifica las credenciales de AWS, y ninguno de los dos por sí solo demuestra el acceso a la red ni todos los permisos de Kubernetes.

### Recopilación y análisis de registros

#### Registros del plano de control de EKS

Compruebe la configuración de registro existente y un período acotado del incidente:

```bash
set -euo pipefail
: "${CLUSTER_NAME:?}"; : "${AWS_REGION:?}"
: "${START_TIME_MS:?Set the incident-window start in epoch milliseconds}"
: "${END_TIME_MS:?Set the incident-window end in epoch milliseconds}"
aws eks describe-cluster --name "$CLUSTER_NAME" --region "$AWS_REGION" \
  --query cluster.logging --output json
aws logs filter-log-events --region "$AWS_REGION" \
  --log-group-name "/aws/eks/$CLUSTER_NAME/cluster" \
  --start-time "$START_TIME_MS" --end-time "$END_TIME_MS" \
  --max-items 200 --output json --no-cli-pager
```

Habilitar el registro del plano de control es un cambio independiente de `UpdateClusterConfig`, con su propio ID de actualización, permisos y cargos de CloudWatch. No recupera registros anteriores ni habilita la recopilación de registros de aplicaciones o hosts. Si el grupo no existe, se deniega la solicitud o el período no contiene eventos, se trata de una limitación de visibilidad. Para los registros de aplicaciones o hosts, use `/aws/containerinsights/<cluster>/...` o el destino real del recopilador.

#### Registros de nodos

En un nodo EC2 Linux estándar al que el operador tenga acceso, verifique el `spec.providerID` del nodo, la cuenta/región y los requisitos previos de SSM antes de abrir una sesión:

```bash
: "${INSTANCE_ID:?Verify the node EC2 ProviderID and account/Region first}"
aws ssm start-session --target "$INSTANCE_ID" --region "$AWS_REGION"
```

Ejecute lo siguiente **dentro de la sesión del nodo**, no en la terminal local. Estos ejemplos de systemd/containerd presuponen que la imagen del nodo incluye esas herramientas; Bottlerocket, Fargate y Auto Mode requieren sus métodos de diagnóstico compatibles.

```bash
sudo journalctl -u kubelet --since "15 minutes ago" --no-pager
sudo journalctl -u containerd --since "15 minutes ago" --no-pager
df -h
df -i
free -m
```

Los nodos Linux optimizados para EKS actuales usan containerd. En esos nodos, el registro del daemon de Docker no es el registro del runtime de kubelet. Preserve los registros y las evidencias de espacio en disco e inodos antes de depurar imágenes, compactar los diarios o reiniciar algo. La ausencia de métricas de `kubectl top` en un nodo en mal estado no demuestra por sí sola un agotamiento de CPU o memoria.

#### Registros de Pods

```bash
set -euo pipefail
: "${KUBE_CONTEXT:?}"; : "${NAMESPACE:?}"; : "${POD_NAME:?}"; : "${CONTAINER_NAME:?}"
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" logs "$POD_NAME" \
  -c "$CONTAINER_NAME" --since=15m --tail=200 --timestamps=true
# Run only when a previous container instance exists in this same Pod.
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" logs "$POD_NAME" \
  -c "$CONTAINER_NAME" --previous --tail=200 --timestamps=true
```

`--previous` se refiere a la instancia anterior terminada del contenedor indicado en el **mismo Pod**. No recupera los registros de un Pod predecesor eliminado; para consultar el historial conservado, use el backend de registros. Revise el estado, la disponibilidad y los motivos de salida tanto de los contenedores regulares como de los contenedores de inicialización.

### Recopilación de información de diagnóstico

```bash
set -euo pipefail
: "${EVIDENCE_PARENT:?Set an existing private directory}"
: "${KUBE_CONTEXT:?}"; : "${NAMESPACE:?}"
umask 077
EVIDENCE_DIR=$(mktemp -d "$EVIDENCE_PARENT/eks-diagnosis.XXXXXXXX")
kubectl --context "$KUBE_CONTEXT" get nodes -o wide > "$EVIDENCE_DIR/nodes.txt"
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" get pods -o wide > "$EVIDENCE_DIR/pods.txt"
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" get services -o wide > "$EVIDENCE_DIR/services.txt"
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" get events \
  --sort-by='.metadata.creationTimestamp' > "$EVIDENCE_DIR/events.txt"
printf 'Evidence saved to %s; assess the findings before remediation.\n' "$EVIDENCE_DIR"
```

Si una consulta falla, este ejemplo se detiene; los archivos existentes constituyen evidencia parcial. Evite los volcados generales de `cluster-info dump` o las descripciones de todos los Pods si basta con un inventario acotado, y revise o enmascare las evidencias antes de compartirlas.

Para la presión de recursos, compare las solicitudes y los límites, los recursos asignables del nodo y `kubectl top` cuando Metrics Server esté disponible. En los nodos accesibles, compruebe tanto `df -h` como `df -i`; disponer de bytes libres no descarta el agotamiento de inodos. Un Pod de depuración de nodos tiene su propio sistema de archivos raíz, mientras que la raíz del host se monta en `/host`; ejecutar `df -h` sin la ruta prevista puede mostrar el sistema de archivos equivocado. Crear un Pod de este tipo requiere revisar el espacio de nombres, la imagen, el perfil de depuración, los permisos y la limpieza.

Para diagnosticar la red, identifique el Pod, el espacio de nombres y el nodo de origen, así como el destino, el protocolo y el puerto. Primero inspeccione las políticas aplicables y el resolvedor del origen. Un Pod de depuración recién creado puede tener etiquetas, identidad, DNS o enrutamiento distintos de los de la carga de trabajo afectada. Un ping ICMP no demuestra que una aplicación sea accesible por TCP/UDP. Realice una prueba acotada en la ruta realmente permitida; coordine la preparación de herramientas y la limpieza con el responsable, en lugar de crear repetidamente Pods `dnsutils`/`netshoot` sin versión fijada y con nombres comunes.

Fuentes: [Solución de problemas de EKS](https://docs.aws.amazon.com/eks/latest/userguide/troubleshooting.html), [Registros de Kubernetes](https://kubernetes.io/docs/reference/kubectl/generated/kubectl_logs/), [Depuración de nodos](https://kubernetes.io/docs/tasks/debug/debug-cluster/kubectl-node-debug/).

## Problemas de creación y administración de clústeres {#cluster-creation-and-management-issues}

![Síntomas relacionados con la creación, el acceso al endpoint y la eliminación del clúster, con hipótesis para investigar.](../.gitbook/assets/en-eks-09-eks-troubleshooting-1.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-09-eks-troubleshooting-1.html)

### Error al crear el clúster

#### Causas comunes

Revise la solicitud fallida exacta o el evento de CloudFormation para determinar los permisos del solicitante, la relación de confianza y las políticas del rol de servicio del clúster, las cuotas de servicio, la selección de subredes/AZ compatibles, la capacidad de IP, los conflictos de nombres o la disponibilidad del servicio. Son hipótesis; su probabilidad depende del error real.

#### Pasos para solucionar el problema

```bash
set -euo pipefail
: "${AWS_REGION:?}"; : "${CLUSTER_ROLE_NAME:?}"; : "${VPC_ID:?}"
aws sts get-caller-identity
aws iam get-role --role-name "$CLUSTER_ROLE_NAME" \
  --query 'Role.{Arn:Arn,Trust:AssumeRolePolicyDocument}'
aws iam list-attached-role-policies --role-name "$CLUSTER_ROLE_NAME"
aws iam list-role-policies --role-name "$CLUSTER_ROLE_NAME"
aws ec2 describe-subnets --region "$AWS_REGION" --filters "Name=vpc-id,Values=$VPC_ID" \
  --query 'Subnets[].{Id:SubnetId,AZ:AvailabilityZone,AZId:AvailabilityZoneId,AvailableIPs:AvailableIpAddressCount,CIDR:CidrBlock}'
aws service-quotas list-service-quotas --service-code eks --region "$AWS_REGION"
aws cloudtrail lookup-events --region "$AWS_REGION" \
  --lookup-attributes AttributeKey=EventName,AttributeValue=CreateCluster \
  --max-items 20 --output json
```

Las políticas adjuntas por sí solas no muestran los permisos efectivos del solicitante: incluya las políticas insertadas, los límites de permisos, las políticas de sesión y los controles de Organizations. `AmazonEKSClusterPolicy` corresponde al rol de servicio del clúster de EKS; adjuntarla a un usuario humano no concede los permisos necesarios `eks:CreateCluster`/`iam:PassRole` ni acceso a Kubernetes. La creación del rol vinculado al servicio también tiene sus propios permisos y ciclo de vida.

Para las comprobaciones de red, use las subredes seleccionadas para el clúster y la configuración exacta de rutas, grupos de seguridad y NACL. Los requisitos de las subredes del clúster y la planificación de capacidad de direcciones para nodos/Pods/LB son aspectos distintos. Los clústeres privados pueden usar los endpoints de servicio necesarios sin una gateway NAT ni acceso general a Internet. La etiqueta de subred `kubernetes.io/cluster/...` no es una solución universal para crear el plano de control.

Si hay errores de cuota, identifique el servicio o la cuota a partir del error y consulte el valor aplicado actual antes de solicitar un aumento. Las cuotas de clústeres de EKS, las cuotas de vCPU/familia de instancias EC2 y los límites de VPC son distintas. Los mensajes históricos como “el límite es 5” son ejemplos, no los límites actuales de una cuenta.

#### Soluciones comunes

Corrija el problema específico de permisos, confianza del rol de servicio, selección de subredes, asignación de IP o cuota con el responsable de la infraestructura y, después, revise cualquier reintento. `UnsupportedAvailabilityZoneException` significa que una subred del clúster especificada está en una AZ que no admite EKS para la cuenta; use las AZ compatibles indicadas por la excepción. No se diagnostica únicamente a partir de las ofertas de tipos de instancias EC2.

Compruebe AWS Health para ver si hay algún evento del servicio. Cambiar de región crea un diseño independiente de ubicación, datos y red, y posiblemente otro clúster; no es un reintento predeterminado para solucionar problemas. `eksctl create cluster --verbose ...` y las opciones de depuración de AWS CLI también ejecutan la creación. Antes de enviar una nueva solicitud de aprovisionamiento, use los eventos de la pila existente y el ID de solicitud.

### Problemas de acceso al endpoint del clúster

#### Diagnostique por separado DNS, transporte, TLS, autenticación y autorización

Inspeccione el modo del endpoint, los CIDR públicos permitidos y el grupo de seguridad del clúster; luego haga una prueba con el certificado de CA del clúster y un límite de tiempo:

```bash
set -euo pipefail
: "${CLUSTER_NAME:?}"; : "${AWS_REGION:?}"; : "${EVIDENCE_PARENT:?}"
umask 077
ENDPOINT_DIR=$(mktemp -d "$EVIDENCE_PARENT/eks-endpoint.XXXXXXXX")
aws eks describe-cluster --name "$CLUSTER_NAME" --region "$AWS_REGION" \
  --output json > "$ENDPOINT_DIR/cluster.json"
jq -er '.cluster.certificateAuthority.data' "$ENDPOINT_DIR/cluster.json" \
  | base64 --decode > "$ENDPOINT_DIR/cluster-ca.crt"
ENDPOINT=$(jq -er '.cluster.endpoint' "$ENDPOINT_DIR/cluster.json")
jq '.cluster.resourcesVpcConfig | {endpointPublicAccess,endpointPrivateAccess,publicAccessCidrs,clusterSecurityGroupId,vpcId}' \
  "$ENDPOINT_DIR/cluster.json"
curl --silent --show-error --connect-timeout 5 --max-time 10 \
  --cacert "$ENDPOINT_DIR/cluster-ca.crt" --output /dev/null \
  --write-out 'HTTP status: %{http_code}\n' "$ENDPOINT"
```

Esto no envía ningún token bearer de Kubernetes. Una respuesta 401/403 puede demostrar que DNS/TCP/TLS funcionan, aunque el acceso esté denegado; una respuesta HTTP satisfactoria no demuestra que la aplicación esté en buen estado. `curl -k` ocultaría los errores de validación del certificado. Si necesita una consulta DNS, use el nombre de host de la URL del endpoint en vez de pasar una URL `https://` a `nslookup`.

Para un endpoint público, compruebe que la dirección real de salida/NAT del cliente esté incluida en los CIDR permitidos. Para un endpoint privado, compruebe la ruta desde la VPC o la red conectada, la resolución DNS y el acceso al grupo de seguridad. El endpoint de interfaz `com.amazonaws.<region>.eks` ofrece **API de administración de EKS**, no el servidor de API de Kubernetes. Habilitarlo por sí solo no soluciona el acceso de kubectl. El endpoint privado de Kubernetes del clúster es independiente.

#### kubeconfig y permisos

Inspeccione el nombre del contexto y el servidor sin mostrar las credenciales sin procesar. Para crear un kubeconfig de diagnóstico independiente, use una ruta y un alias explícitos; establezca `NAMESPACE` en el ámbito de autorización previsto:

```bash
set -euo pipefail
: "${CLUSTER_NAME:?}"; : "${AWS_REGION:?}"
: "${NAMESPACE:?Set the namespace for the authorization check}"
: "${DIAGNOSTIC_KUBECONFIG:?Set a separate writable kubeconfig path}"
: "${KUBE_CONTEXT:?Choose an explicit alias for this cluster}"
umask 077
aws eks update-kubeconfig --name "$CLUSTER_NAME" --region "$AWS_REGION" \
  --kubeconfig "$DIAGNOSTIC_KUBECONFIG" --alias "$KUBE_CONTEXT"
export KUBECONFIG="$DIAGNOSTIC_KUBECONFIG"
kubectl --context "$KUBE_CONTEXT" auth can-i get pods --namespace "$NAMESPACE"
```

Crear el kubeconfig requiere `eks:DescribeCluster`; la autenticación y autorización de Kubernetes son requisitos independientes. Si va a asumir un rol, use `--role-arn` después de revisarlo, junto con los permisos de confianza/STS correspondientes. Renueve las credenciales mediante el proveedor de credenciales real (por ejemplo, la sesión SSO configurada), en lugar de mostrar los tokens de sesión.

```bash
set -euo pipefail
: "${CLUSTER_NAME:?}"; : "${AWS_REGION:?}"
aws eks describe-cluster --name "$CLUSTER_NAME" --region "$AWS_REGION" \
  --query 'cluster.accessConfig'
# Use the next command when API or API_AND_CONFIG_MAP authentication is enabled.
aws eks list-access-entries --cluster-name "$CLUSTER_NAME" --region "$AWS_REGION"
```

Si la autenticación mediante access entry está habilitada, inspeccione la entrada correspondiente y el ámbito de las políticas asociadas. Los clústeres heredados `CONFIG_MAP` o de modo mixto también pueden usar `aws-auth`; conserve las asignaciones de nodos existentes y planifique la migración. No conceda `system:masters` ni sobrescriba todo el ConfigMap como solución de acceso genérica. El proveedor IAM OIDC de IRSA sirve para las credenciales de AWS de las cargas de trabajo, no para la asignación que autoriza a un principal IAM humano a acceder a Kubernetes.

#### Corrija la ruta de acceso

Use una ruta administrativa privada conectada o una lista de CIDR públicos permitidos revisada y apropiada para el modo del endpoint. No abra `0.0.0.0/0` solo para que funcione un comando de diagnóstico. Pruebe la ruta privada antes de quitar el acceso público, conserve la configuración de VPC no relacionada y registre el ID de actualización de la configuración. Para un cambio planificado, siga el [procedimiento de endpoints del capítulo de seguridad](./05-eks-security.md).

#### Acceso a CloudShell con un clic

La función de un clic, disponible desde el 30 de abril de 2026, es compatible. Seleccione **Conectar** en la página de detalles del clúster para abrir CloudShell con kubectl configurado. Se admiten endpoints de API públicos y privados; para un endpoint privado, se inicia automáticamente un entorno de CloudShell en una VPC y se solicita su nombre. La función está disponible sin cargos adicionales por la función en las regiones de EKS.

La ruta de la consola sigue requiriendo los permisos pertinentes de IAM/CloudShell/entorno de VPC, acceso a Kubernetes y una configuración de red funcional. Evita la configuración local, no las comprobaciones de autorización. Revise los cargos aplicables por recursos/transferencia de datos y la identidad de la sesión antes de ejecutar comandos.

Fuentes: [kubeconfig y CloudShell](https://docs.aws.amazon.com/eks/latest/userguide/create-kubeconfig.html), [Anuncio del acceso con un clic](https://aws.amazon.com/about-aws/whats-new/2026/04/amazon-eks-one-click-cluster-access/), [Distinción de EKS PrivateLink](https://docs.aws.amazon.com/eks/latest/userguide/vpc-interface-endpoints.html), [Solución de problemas de clústeres](https://docs.aws.amazon.com/eks/latest/userguide/troubleshooting.html).

### Problemas al eliminar un clúster

#### Identifique la dependencia que lo bloquea

Eliminar un clúster es un desmantelamiento deliberado, no una solución general a problemas. Lea el error exacto de EKS/CloudFormation, el ARN de clúster/cuenta/región, el estado de la actualización y la configuración de protección contra eliminación. Además de los grupos de nodos administrados y los perfiles de Fargate, la protección contra eliminación y las Capabilities de EKS instaladas pueden bloquear la eliminación. Mantenga los roles IAM/de servicio del clúster hasta que termine la eliminación.

Inventaríe el clúster seleccionado y compare su endpoint con el contexto explícito de kubectl. Los siguientes comandos son de solo lectura y no seleccionan automáticamente recursos para eliminarlos:

```bash
set -euo pipefail
: "${CLUSTER_NAME:?Set the cluster being deliberately retired}"
: "${AWS_REGION:?}"; : "${KUBE_CONTEXT:?}"; : "${EXPECTED_ACCOUNT_ID:?}"
ACTUAL_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
if [ "$ACTUAL_ACCOUNT_ID" != "$EXPECTED_ACCOUNT_ID" ]; then
  echo "Account mismatch; stop" >&2
  exit 1
fi
aws eks describe-cluster --name "$CLUSTER_NAME" --region "$AWS_REGION" \
  --query 'cluster.{arn:arn,status:status,deletionProtection:deletionProtection,endpoint:endpoint}'
kubectl config view --context "$KUBE_CONTEXT" --minify \
  -o jsonpath='{.clusters[0].cluster.server}{"\n"}'
# Compare the endpoints before inspecting Kubernetes resources.
kubectl --context "$KUBE_CONTEXT" get services -A \
  -o custom-columns='NAMESPACE:.metadata.namespace,NAME:.metadata.name,TYPE:.spec.type,CLASS:.spec.loadBalancerClass,ADDRESS:.status.loadBalancer.ingress'
kubectl --context "$KUBE_CONTEXT" get ingress -A
kubectl --context "$KUBE_CONTEXT" get pvc -A
kubectl --context "$KUBE_CONTEXT" get pv \
  -o custom-columns='NAME:.metadata.name,CLAIM_NS:.spec.claimRef.namespace,CLAIM:.spec.claimRef.name,RECLAIM:.spec.persistentVolumeReclaimPolicy,DRIVER:.spec.csi.driver,HANDLE:.spec.csi.volumeHandle'
aws eks list-nodegroups --cluster-name "$CLUSTER_NAME" --region "$AWS_REGION"
aws eks list-fargate-profiles --cluster-name "$CLUSTER_NAME" --region "$AWS_REGION"
aws eks list-capabilities --cluster-name "$CLUSTER_NAME" --region "$AWS_REGION"
aws eks list-addons --cluster-name "$CLUSTER_NAME" --region "$AWS_REGION"
```

La salida `EXTERNAL-IP` de un Service por sí sola no demuestra quién es su propietario: distinga los Services `LoadBalancer` administrados por controladores, las IP externas configuradas manualmente y otros tipos de Service. Registre el espacio de nombres, nombre y UID, la propiedad del controlador, el ARN del recurso de AWS y las etiquetas pertinentes. Incluya recursos Ingress, Gateway/TargetGroupBinding cuando estén instalados sus controladores, y determine si los destinos o los balanceadores de carga son compartidos.

#### Retire los recursos según la secuencia de su propietario

1. Migre el tráfico y las cargas de trabajo, y verifique que las copias de seguridad y restauraciones sean coherentes con la aplicación y cumplan los requisitos de conservación de datos. Guardar el YAML de un PVC no es una copia de seguridad de los datos. Una política de recuperación `Delete` puede eliminar el almacenamiento subyacente al eliminarse el claim; `Retain` requiere decidir por separado qué hacer con los datos y el almacenamiento.
2. Mientras los controladores de balanceadores de carga necesarios sigan en ejecución, elimine únicamente los recursos de Kubernetes revisados que sean propietarios de balanceadores de carga. Espere a los finalizers y verifique que se hayan liberado los recursos de AWS correspondientes. Resuelva los errores de IAM del controlador o de dependencias antes de eliminar sus nodos. No quite finalizers solo para ocultar una limpieza fallida.
3. Elimine las Capabilities de EKS según sus semánticas documentadas de propiedad y eliminación de recursos. Elimine los grupos de nodos administrados y los perfiles de Fargate en un orden revisado y espere a que terminen. Las pilas o los nodos autoadministrados requieren su propio desmantelamiento. La eliminación de complementos también puede quitar componentes de Kubernetes; conserve los controladores de red/almacenamiento hasta que termine la limpieza de lo que depende de ellos.
4. Desactive la protección contra eliminación solo como decisión explícita de desmantelamiento y elimine el clúster mediante su propietario original de infraestructura. La eliminación de un clúster de Auto Mode también elimina sus nodos y balanceadores de carga administrados; tenga en cuenta ese alcance y el ciclo de vida de los grupos de destino TargetGroupBinding integrados.
5. Revise los recursos restantes según su propietario exacto: pilas/VPC dedicadas, volúmenes/instantáneas, balanceadores de carga, recursos IAM, registros y scrapers de Prometheus. Los recursos compartidos y los datos conservados tienen ciclos de vida independientes y pueden seguir generando cargos.

Por ejemplo, lo siguiente elimina **un** Service seleccionado explícitamente después de la revisión previa del tráfico y los datos. No es un bucle que descubra y elimine recursos:

```bash
set -euo pipefail
: "${KUBE_CONTEXT:?}"; : "${SERVICE_NAMESPACE:?}"; : "${SERVICE_NAME:?}"
# Separate approved teardown step after traffic/data migration and owner review.
kubectl --context "$KUBE_CONTEXT" -n "$SERVICE_NAMESPACE" get service "$SERVICE_NAME" -o yaml
kubectl --context "$KUBE_CONTEXT" -n "$SERVICE_NAMESPACE" delete service "$SERVICE_NAME" \
  --wait=true --timeout=10m
```

Un tiempo de espera agotado no demuestra que el balanceador de carga de AWS se haya conservado o eliminado; inspeccione los finalizers, los eventos del controlador y el ARN exacto de AWS. La limpieza de recursos de Kubernetes y AWS puede completarse en momentos distintos.

#### Errores de eliminación y comportamiento forzado

Use los detalles de actualización de EKS y los eventos de la pila de CloudFormation para identificar fallos de dependencias, autorización u operaciones en curso. En eksctl 0.229, `delete cluster --force` es una opción válida que permite continuar con la eliminación cuando ocurren errores. No demuestra que la limpieza se haya completado ni identifica de forma segura los recursos huérfanos. `--disable-nodegroup-eviction` omite por separado las comprobaciones de PDB mediante la eliminación. Ninguna de las dos opciones es una respuesta predeterminada a un incidente.

No conecte un inventario de ELB/ELBv2 de toda la cuenta/región mediante una tubería a comandos de eliminación ni elimine todos los Services, PVC o espacios de nombres para despejar un error de dependencia. Si hay que quitar manualmente un recurso huérfano, primero establezca con exactitud qué clúster o pila es su propietario y cuál es el impacto en los datos y el tráfico; después siga el procedimiento de desmantelamiento revisado del servicio correspondiente.

Fuentes: [Eliminación de clústeres de EKS](https://docs.aws.amazon.com/eks/latest/userguide/delete-cluster.html), [Solución de problemas de eliminación](https://repost.aws/knowledge-center/eks-delete-cluster-issues), [Ciclo de vida de los volúmenes persistentes](https://kubernetes.io/docs/concepts/storage/persistent-volumes/).

## Problemas de redes {#networking-issues}

![Síntomas de red agrupados en comunicación entre Pods, acceso a Services, balanceo de carga, DNS y asignación de CNI/IP.](../.gitbook/assets/en-eks-09-eks-troubleshooting-2.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-09-eks-troubleshooting-2.html)

Primero identifique el plano de cómputo/datos real. Los nodos EC2 estándar que usan el VPC CNI de código abierto, Fargate y Auto Mode no tienen agentes ni configuraciones idénticos. Para Auto Mode, use los controles de red de su `NodeClass`; cambiar un DaemonSet `aws-node` o `ENIConfig` no configura los nodos de Auto Mode.

### Problemas de comunicación entre Pods

#### Rastree la ruta que falla

Registre el Pod, el espacio de nombres, el nodo/AZ, la familia IP, el protocolo y el puerto de destino del origen y el destino. Compare el comportamiento en el mismo nodo y entre nodos si una prueba aprobada permite aislar la diferencia. Compruebe la política, los grupos de seguridad, las rutas/NACL, el estado del CNI, la asignación de IP y la MTU de la ruta en cuestión.

```bash
set -euo pipefail
: "${KUBE_CONTEXT:?}"; : "${NAMESPACE:?}"; : "${POD_NAME:?}"
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" get pod "$POD_NAME" -o wide
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" get pod "$POD_NAME" \
  -o jsonpath='{.metadata.labels}{"\n"}{.spec.nodeName}{"\n"}{.spec.hostNetwork}{"\n"}'
kubectl --context "$KUBE_CONTEXT" get namespace "$NAMESPACE" --show-labels
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" get networkpolicies
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" get events \
  --sort-by='.metadata.creationTimestamp'
```

Las NetworkPolicies estándar `networking.k8s.io/v1` combinan el tráfico permitido de forma aditiva; no tienen prioridad de reglas ni una política de «la última gana». Cuando ambos pares están aislados, deben permitir el flujo tanto el tráfico de salida del origen como el tráfico de entrada del destino. Las API de políticas de administración/de clúster y los motores de políticas específicos de cada proveedor tienen semánticas distintas. Compruebe las etiquetas del espacio de nombres y si `namespaceSelector` y `podSelector` pertenecen al mismo par (AND) o a pares distintos (OR).

El VPC CNI admite la aplicación nativa de políticas de red; no instale Calico/Cilium solo porque no haya un Pod de políticas de terceros. Verifique que la configuración del agente de políticas esté habilitada y que el CNI, la plataforma y el kernel sean compatibles. En el modo de inicio estándar, un Pod nuevo permite inicialmente el tráfico hasta que se configuran sus políticas; el modo estricto empieza con denegación y necesita las políticas requeridas de DNS/dependencias. El comportamiento de `hostNetwork` y otros límites de cobertura requieren consultar la documentación de la implementación pertinente.

En una instalación estándar del VPC CNI, inspeccione los registros del contenedor `aws-network-policy-agent` del Pod `aws-node` real si está presente. Que `kubectl get pods -l ...` se ejecute correctamente y devuelva una lista vacía no demuestra que haya un complemento instalado. Auto Mode usa en cambio sus controles de políticas integrados.

#### Corrija únicamente el flujo previsto

Revise la matriz completa de flujos permitidos en vez de añadir reglas de entrada/salida que permitan todo el tráfico en todo el espacio de nombres o eliminar políticas. Este ejemplo selecciona Pods API de backend y permite únicamente el tráfico TCP 8080 desde Pods web del frontend:

```yaml
# Example ingress policy only: review both peers and the complete allowed-flow matrix.
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: api-from-web
  namespace: backend
spec:
  podSelector:
    matchLabels:
      app: api
  policyTypes:
    - Ingress
  ingress:
    - from:
        - namespaceSelector:
            matchLabels:
              kubernetes.io/metadata.name: frontend
          podSelector:
            matchLabels:
              app: web
      ports:
        - protocol: TCP
          port: 8080
```

Al aplicarla, se puede aislar otro tráfico de entrada a los Pods de backend seleccionados, salvo que otras políticas lo permitan. No configura el tráfico de salida del cliente, el DNS ni todas las dependencias. Verifíquelos por separado con pruebas positivas y negativas. Use los espacios de nombres y las etiquetas reales de la carga de trabajo en vez de copiar los nombres del ejemplo.

Para los grupos de seguridad, inspeccione los grupos de las ENI de origen y destino, incluidos los grupos de Pods o las subredes personalizadas de Pods cuando corresponda. Permita por medio del responsable el origen/puerto necesario; no añada todos los protocolos ni CIDR amplios como solución genérica. Los valores de MTU como 1500 o 9001 dependen de la ruta; mida el fallo y tenga en cuenta la encapsulación antes de cambiar la configuración del CNI o reemplazar Pods.

### Problemas de acceso a Services

Compruebe en conjunto el selector del Service, la disponibilidad real de los Pods, las condiciones de los endpoints y la asignación de puertos:

```bash
set -euo pipefail
: "${KUBE_CONTEXT:?}"; : "${NAMESPACE:?}"; : "${SERVICE_NAME:?}"
SERVICE_JSON=$(kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" get service "$SERVICE_NAME" -o json)
printf '%s\n' "$SERVICE_JSON" | jq '{metadata: {name: .metadata.name, namespace: .metadata.namespace}, spec: .spec, status: .status}'
SELECTOR=$(printf '%s\n' "$SERVICE_JSON" | jq -r '(.spec.selector // {}) | to_entries | map("\(.key)=\(.value)") | join(",")')
if [ -n "$SELECTOR" ]; then
  kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" get pods -l "$SELECTOR" -o wide
  kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" get pods -l "$SELECTOR" -o json \
    | jq '.items[] | {name:.metadata.name,phase:.status.phase,ready:[.status.conditions[]? | select(.type=="Ready")],containers:.status.containerStatuses}'
else
  printf 'No selector: inspect ExternalName or explicitly managed EndpointSlices as applicable.\n'
fi
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" get endpointslices \
  -l "kubernetes.io/service-name=$SERVICE_NAME" -o yaml
```

Use EndpointSlices en vez de depender de la API obsoleta Endpoints. Inspeccione las condiciones `ready`, `serving` y `terminating`, y opciones del Service como `publishNotReadyAddresses`, `externalTrafficPolicy` e `internalTrafficPolicy`. Un Pod en ejecución no necesariamente está preparado.

En el caso de un Service `ExternalName`, diagnostique el alias DNS en lugar de esperar que seleccione Pods. En un Service headless, `clusterIP: None` es intencional. Los Services sin selector pueden usar EndpointSlices administrados por su propietario. El `port` de un Service puede diferir del `targetPort`; declarar un puerto de contenedor no hace que una aplicación escuche en él.

Si las etiquetas o los puertos son incorrectos, actualice la configuración declarada del Service/plantilla del Pod a través de la configuración de su versión. Cambiar las etiquetas de un Pod controlado por un controlador no es una solución duradera. Revise toda la lista de puertos y los campos inmutables antes de aplicar un parche. Evite eliminar y volver a crear el Service, cambiar ClusterIP o reiniciar todos los Pods kube-proxy sin diagnosticar la causa.

Compare la conectividad directa con el Pod y con el Service desde el mismo origen y con el mismo protocolo, solo cuando la política lo permita. Confirme si el plano de datos es kube-proxy, una implementación alternativa o Auto Mode antes de inspeccionar el comportamiento de iptables/nftables/eBPF. La ausencia de un Pod kube-proxy no siempre es un problema.

### Problemas de balanceadores de carga

Identifique el controlador a partir de la clase del Service/Ingress, las anotaciones y la propiedad. AWS Load Balancer Controller estándar y EKS Auto Mode utilizan clases/API y reglas de ciclo de vida diferentes. Compruebe los eventos del controlador, la selección de subredes, IAM, los grupos de seguridad, el registro de destinos y las comprobaciones de estado correspondientes al propietario.

Use los ARN exactos del balanceador de carga y del grupo de destinos asociados a la carga de trabajo:

```bash
set -euo pipefail
: "${AWS_REGION:?}"; : "${LOAD_BALANCER_ARN:?}"; : "${TARGET_GROUP_ARN:?}"
aws elbv2 describe-load-balancers --region "$AWS_REGION" \
  --load-balancer-arns "$LOAD_BALANCER_ARN"
aws elbv2 describe-tags --region "$AWS_REGION" \
  --resource-arns "$LOAD_BALANCER_ARN" "$TARGET_GROUP_ARN"
aws elbv2 describe-load-balancer-attributes --region "$AWS_REGION" \
  --load-balancer-arn "$LOAD_BALANCER_ARN"
aws elbv2 describe-target-groups --region "$AWS_REGION" \
  --target-group-arns "$TARGET_GROUP_ARN"
aws elbv2 describe-target-health --region "$AWS_REGION" \
  --target-group-arn "$TARGET_GROUP_ARN"
```

`describe-load-balancer-attributes` muestra atributos, no el estado operativo; `describe-load-balancers` incluye el estado. Compruebe los códigos de motivo del estado de los destinos, el protocolo/puerto/ruta de las comprobaciones de estado, el enrutamiento de listener/reglas y la respuesta de la aplicación. Los destinos de tipo instancia suelen llegar a un nodo/NodePort; los destinos IP llegan al puerto de destino del Pod. Las reglas de los grupos de seguridad deben coincidir con la ruta real.

Las etiquetas de función de las subredes afectan la detección automática; compruebe el esquema público/interno, las tablas de rutas, las IP libres y la cobertura de AZ. Añadir etiquetas de función tanto públicas como privadas a las mismas subredes no es una solución. La selección explícita de subredes y las versiones del controlador pueden cambiar los requisitos de etiquetas. No abra los grupos de seguridad de frontend/backend a `0.0.0.0/0` para eludir una comprobación de estado fallida.

Use la configuración de esquema/tipo actual del propietario. Los ejemplos heredados `aws-load-balancer-internal` o `aws-load-balancer-type: nlb` no son intercambiables con las clases actuales del controlador. Cambiar la propiedad del controlador o el esquema del balanceador puede requerir un reemplazo planificado y migración del tráfico; modificar una anotación no garantiza una conversión en el mismo recurso. Auto Mode no adopta los balanceadores de carga que ya administra el controlador autoadministrado.

Eliminar un Service puede eliminar su balanceador de carga; exportar el YAML sin procesar del Service no es un plan completo de reversión del tráfico o los datos. Crear un ALB manualmente no lo conecta automáticamente a un Service de Kubernetes. Antes de un cambio, revise las [guías de redes](./03-eks-networking-part2.md) correspondientes al propietario seleccionado.

### Problemas de DNS

#### Inspeccione el resolvedor que usa el Pod afectado

```bash
set -euo pipefail
: "${KUBE_CONTEXT:?}"; : "${NAMESPACE:?}"; : "${POD_NAME:?}"; : "${CONTAINER_NAME:?}"
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" get pod "$POD_NAME" \
  -o jsonpath='{.spec.dnsPolicy}{"\n"}{.spec.dnsConfig}{"\n"}{.spec.hostNetwork}{"\n"}'
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" exec "$POD_NAME" \
  -c "$CONTAINER_NAME" -- cat /etc/resolv.conf
# Where this container actually includes nslookup, test the intended name.
: "${DNS_TEST_NAME:?Set the intended Service FQDN or reviewed external hostname}"
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" exec "$POD_NAME" \
  -c "$CONTAINER_NAME" -- nslookup "$DNS_TEST_NAME"
```

Si la imagen no incluye un shell o una herramienta DNS, se trata de una limitación de herramientas, no de una consulta DNS fallida. Prepare un método de depuración revisado que conserve el contexto pertinente de red/identidad. Un Pod de depuración nuevo puede usar una configuración de DNS/políticas distinta.

En nodos estándar que no sean de Auto Mode, inspeccione el Deployment/Service de CoreDNS instalado, su configuración y sus EndpointSlices:

```bash
kubectl --context "$KUBE_CONTEXT" -n kube-system get deployment coredns
kubectl --context "$KUBE_CONTEXT" -n kube-system get pods -l k8s-app=kube-dns -o wide
kubectl --context "$KUBE_CONTEXT" -n kube-system get service kube-dns
kubectl --context "$KUBE_CONTEXT" -n kube-system get endpointslices \
  -l kubernetes.io/service-name=kube-dns
kubectl --context "$KUBE_CONTEXT" -n kube-system get configmap coredns -o yaml
kubectl --context "$KUBE_CONTEXT" -n kube-system logs -l k8s-app=kube-dns \
  --all-containers=true --prefix=true --since=15m --tail=100
```

En los **nodos de Auto Mode**, CoreDNS se ejecuta como servicio de sistema del nodo. Un clúster exclusivamente de Auto Mode puede funcionar sin el Deployment tradicional de CoreDNS. Un clúster mixto de Auto Mode y nodos no Auto Mode debe conservar el Deployment para estos últimos. No instale NodeLocal DNSCache ni reinicie un Deployment inexistente como solución para Auto Mode.

Distinga el servidor de nombres del Pod, el upstream de CoreDNS/NodeLocal y el resolvedor de VPC. `169.254.20.10` es una dirección que se suele elegir para NodeLocal DNSCache, no el servidor DNS universal de VPC. Un resolvedor público como `8.8.8.8` no es un sustituto para las zonas de Service de Kubernetes ni el DNS privado de AWS.

```bash
set -euo pipefail
: "${AWS_REGION:?}"; : "${VPC_ID:?}"
aws ec2 describe-vpc-attribute --region "$AWS_REGION" --vpc-id "$VPC_ID" \
  --attribute enableDnsSupport
aws ec2 describe-vpc-attribute --region "$AWS_REGION" --vpc-id "$VPC_ID" \
  --attribute enableDnsHostnames
aws ec2 describe-vpcs --region "$AWS_REGION" --vpc-ids "$VPC_ID" \
  --query 'Vpcs[].{VpcId:VpcId,DhcpOptionsId:DhcpOptionsId}'
```

Use `describe-vpc-attribute` para los atributos de DNS; no son campos que devuelva `describe-vpcs`. Consulte las opciones DHCP usando el ID devuelto. No sustituya la configuración DHCP de una VPC compartida sin revisar las otras cargas de trabajo.

#### Aplique una corrección de DNS específica

Compruebe UDP y TCP 53 cuando sea necesario, el estado/configuración real de CoreDNS, el acceso al upstream, la política de DNS y la configuración de búsqueda personalizada. Los Pods `hostNetwork` suelen necesitar `ClusterFirstWithHostNet` cuando se pretende usar el DNS del clúster; `dnsPolicy: None` requiere una configuración de resolvedor completa y deliberada. Una política de salida que solo permita DNS también aísla el resto del tráfico de salida de los Pods seleccionados, salvo que otras políticas lo permitan.

Conserve las personalizaciones del Corefile que pertenezcan al propietario y use el esquema de configuración compatible con el complemento. Revise las réplicas, los recursos, el PDB, la programación y el propietario de cualquier escalado automático antes de escalar o reiniciar CoreDNS. Registre un ID de actualización y realice comprobaciones de DNS funcionales; no elimine todos los Pods DNS ni instale como primer paso una imagen «latest» elegida a ciegas.

### Problemas del VPC CNI

La siguiente inspección se aplica a los **nodos EC2 estándar que usan el VPC CNI de código abierto**. Seleccione explícitamente el Pod del nodo afectado; `kubectl exec` no acepta un selector de etiquetas.

```bash
set -euo pipefail
: "${KUBE_CONTEXT:?}"; : "${NODE_NAME:?}"
kubectl --context "$KUBE_CONTEXT" get node "$NODE_NAME" \
  -o jsonpath='{.spec.providerID}{"\n"}{.status.nodeInfo}{"\n"}{.status.allocatable.pods}{"\n"}'
kubectl --context "$KUBE_CONTEXT" -n kube-system get daemonset aws-node -o json \
  | jq '.spec.template.spec | {containers:[.containers[] | {name,image,args,env}],initContainers:[.initContainers[]? | {name,image,args,env}]}'
kubectl --context "$KUBE_CONTEXT" -n kube-system get pods \
  -l k8s-app=aws-node --field-selector "spec.nodeName=$NODE_NAME" -o wide
kubectl --context "$KUBE_CONTEXT" get pods -A \
  --field-selector "spec.nodeName=$NODE_NAME" -o wide
: "${AWS_NODE_POD:?Select the aws-node Pod on that exact node}"
kubectl --context "$KUBE_CONTEXT" -n kube-system logs "$AWS_NODE_POD" \
  -c aws-node --since=15m --tail=200
```

Inspeccione `configurationValues` del complemento, el entorno del DaemonSet y los recursos personalizados pertinentes. No presuponga que un ConfigMap `aws-node` contiene todos los ajustes. El `.spec.podCIDR` del nodo no es un inventario fiable de las direcciones IP de los Pods del VPC CNI; inspeccione las IP reales de los Pods, las ENI de EC2, los prefijos y las subredes.

```bash
set -euo pipefail
: "${AWS_REGION:?}"; : "${INSTANCE_ID:?Verify it from the selected node ProviderID}"
aws ec2 describe-instances --region "$AWS_REGION" --instance-ids "$INSTANCE_ID" \
  --query 'Reservations[].Instances[].{Id:InstanceId,Type:InstanceType,Subnet:SubnetId,SGs:SecurityGroups,ENIs:NetworkInterfaces}'
: "${SUBNET_ID:?Set the actual node or custom Pod subnet being investigated}"
aws ec2 describe-subnets --region "$AWS_REGION" --subnet-ids "$SUBNET_ID" \
  --query 'Subnets[].{Id:SubnetId,CIDR:CidrBlock,AvailableIPs:AvailableIpAddressCount}'
: "${INSTANCE_TYPE:?Set the selected instance type}"
aws ec2 describe-instance-types --region "$AWS_REGION" --instance-types "$INSTANCE_TYPE" \
  --query 'InstanceTypes[].{Type:InstanceType,Network:NetworkInfo}'
```

Cuando está habilitada, la introspección de IPAMD se encuentra en el endpoint de introspección configurado para el nodo (normalmente el puerto de loopback 61679). Use un método de diagnóstico del nodo/agente que esté permitido y disponga de la herramienta necesaria; que la imagen del CNI no incluya curl no es un fallo de IPAM.

#### Distinga las restricciones de asignación

- **Agotamiento o fragmentación de subredes:** compare las direcciones y los prefijos libres. La delegación de prefijos requiere instancias y configuración compatibles, además de bloques de prefijos contiguos disponibles; contar IP libres no demuestra por sí solo que se pueda asignar un /28.
- **Límites de ENI/IP de la instancia:** inspeccione `NetworkInfo` y las ENI existentes. Cambiar los valores deseados/mínimos/máximos del grupo de nodos modifica el número de nodos, no el tipo de instancia ni sus límites por instancia. Para cambiar la configuración de la instancia, use un grupo nuevo revisado o la ruta compatible de actualización de la plantilla de lanzamiento original.
- **Redes personalizadas:** prepare los `ENIConfig`, las subredes/los grupos de seguridad de los Pods y la selección de nodos correspondientes antes de habilitarlas. Cambian el origen de las ENI secundarias/IP de Pods; no crean capacidad ilimitada.
- **Objetivos de calentamiento:** `WARM_IP_TARGET` controla el margen de IP libres; `MINIMUM_IP_TARGET` es un piso para el total de IP asignadas. Según la documentación, estos ajustes prevalecen sobre el comportamiento de ENI de reserva, y los objetivos de IP/mínimos afectan el comportamiento de los prefijos de reserva en modo de prefijos. Un mínimo sin margen positivo de IP de reserva puede impedir asignaciones posteriores. Calcule los valores a partir del presupuesto de cargas de trabajo/IP en vez de copiar valores arbitrarios como 1/2/5.
- **Identidad/propiedad:** inspeccione la identidad real IRSA/Pod Identity del CNI o el rol aplicable del nodo y la política IPv4/IPv6. Adjuntar una política CNI IPv4 al rol de cada nodo no es una solución universal.

Auto Mode usa los controles de subred/grupo de seguridad/políticas de `NodeClass` y no admite estos ajustes de IP de reserva/ENI ni `ENIConfig`. Conserve su modelo de redes administrado.

Aplique una versión/configuración del CNI revisada a través de su propietario, siguiendo las versiones intermedias y el esquema de configuración compatibles. Use la [guía de actualización](./08-eks-upgrades.md) para supervisar la actualización exacta del complemento y validar las redes después. No sustituya solo la imagen de un contenedor, sobrescriba la configuración a ciegas ni reinicie todas las cargas de trabajo para ocultar fallos de asignación.

Fuentes: [Configuración de políticas del VPC CNI](https://docs.aws.amazon.com/eks/latest/userguide/cni-network-policy-configure.html), [Redes de Auto Mode](https://docs.aws.amazon.com/eks/latest/userguide/auto-networking.html), [Redes personalizadas](https://docs.aws.amazon.com/eks/latest/best-practices/custom-networking.html), [Configuración del CNI](https://github.com/aws/amazon-vpc-cni-k8s), [NetworkPolicy de Kubernetes](https://kubernetes.io/docs/concepts/services-networking/network-policies/), [EndpointSlices](https://kubernetes.io/docs/concepts/services-networking/endpoint-slices/).

## Problemas de nodos y Pods {#node-and-pod-issues}

![Síntomas de nodos y Pods con hipótesis de recursos, kubelet, redes, cargas de trabajo y escalado para investigar.](../.gitbook/assets/en-eks-09-eks-troubleshooting-3.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-09-eks-troubleshooting-3.html)

### Problemas de nodos NotReady

#### Inspeccione las condiciones y el nodo real

`Ready=False` y `Ready=Unknown` requieren evidencias distintas: un kubelet/runtime en mal estado puede informar de un fallo, mientras que la falta de latidos puede reflejar una pérdida de conectividad o un nodo detenido. La presión de memoria, disco y PID son condiciones independientes y no siempre significan que el nodo esté `NotReady`. Inspeccione los motivos y las horas de las condiciones, y los leases/eventos, en vez de inferir la causa a partir de una sola etiqueta.

```bash
set -euo pipefail
: "${KUBE_CONTEXT:?}"; : "${NODE_NAME:?}"
NODE_JSON=$(kubectl --context "$KUBE_CONTEXT" get node "$NODE_NAME" -o json)
printf '%s\n' "$NODE_JSON" | jq '{name:.metadata.name,uid:.metadata.uid,labels:.metadata.labels,providerID:.spec.providerID,taints:.spec.taints,unschedulable:.spec.unschedulable,nodeInfo:.status.nodeInfo,conditions:.status.conditions,capacity:.status.capacity,allocatable:.status.allocatable}'
NODE_UID=$(printf '%s\n' "$NODE_JSON" | jq -er '.metadata.uid')
kubectl --context "$KUBE_CONTEXT" get events -A --field-selector "involvedObject.uid=$NODE_UID" \
  --sort-by='.metadata.creationTimestamp'
kubectl --context "$KUBE_CONTEXT" get pods -A --field-selector "spec.nodeName=$NODE_NAME" -o wide
```

Para las comprobaciones de EC2, use el ProviderID exacto; buscar una IP de nodo con `grep` puede seleccionar el recurso equivocado. En los grupos de nodos administrados, inspeccione el estado, la imagen/versión y la configuración de reparación:

```bash
set -euo pipefail
: "${CLUSTER_NAME:?}"; : "${AWS_REGION:?}"; : "${NODEGROUP_NAME:?}"
aws eks describe-nodegroup --cluster-name "$CLUSTER_NAME" --nodegroup-name "$NODEGROUP_NAME" \
  --region "$AWS_REGION" \
  --query 'nodegroup.{status:status,health:health,version:version,releaseVersion:releaseVersion,amiType:amiType,nodeRepairConfig:nodeRepairConfig,updateConfig:updateConfig,scalingConfig:scalingConfig}'
```

Cuando se admita el acceso al nodo, use el procedimiento de sesión remota de la sección de fundamentos para inspeccionar los diarios de kubelet/containerd, las redes, los bytes/inodos del disco y la memoria. Inspeccione las rutas reales configuradas de certificados/kubeconfig sin mostrar claves privadas. `kubeadm certs renew` no repara el plano de control administrado de EKS y `eksctl replace nodegroup` no es un comando compatible de eksctl. AL2023 usa la configuración nodeadm; no vuelva a ejecutar en todas las imágenes la receta `/etc/eks/bootstrap.sh` de AL2.

#### Recuperación y reparación automática

Elija una acción de recuperación cuyo responsable esté definido, después de conservar las evidencias. Reiniciar kubelet/containerd, reiniciar el nodo o sustituirlo afecta a las cargas de trabajo y puede no resolver un problema persistente de IAM/redes/inicialización. Una respuesta satisfactoria de la API de reinicio no significa que la instancia o kubelet estén listos; verifique el mismo nodo/instancia y sus cargas de trabajo antes de quitarle el cordón.

Para un reemplazo planificado, compruebe la capacidad, los datos con estado, los PDB y el propietario del reemplazo; luego vacíe un nodo seleccionado con un límite de tiempo:

```bash
set -euo pipefail
: "${KUBE_CONTEXT:?Set the reviewed cluster context}"
: "${NODE_NAME:?Set one reviewed old node}"
kubectl --context "$KUBE_CONTEXT" get node "$NODE_NAME" -o wide
kubectl --context "$KUBE_CONTEXT" get node "$NODE_NAME" \
  -o jsonpath='{.spec.providerID}{"\n"}'
kubectl --context "$KUBE_CONTEXT" get pods --all-namespaces \
  --field-selector "spec.nodeName=$NODE_NAME" -o wide
# Stop on failure. Do not terminate the instance or delete the node group here.
kubectl --context "$KUBE_CONTEXT" drain "$NODE_NAME" --ignore-daemonsets --timeout=10m
```

No continúe con la terminación de EC2 después de un vaciado fallido ni descarte por defecto los datos de `emptyDir`. Un nodo vaciado parcialmente puede permanecer con el cordón aplicado. Los PDB se aplican a la ruta de expulsión, no a todos los fallos de infraestructura, terminaciones o reducciones de escala del controlador. Para un reemplazo administrado, siga el [procedimiento de actualización de nodos](./08-eks-upgrades.md) en vez de cambiar paquetes en el sitio.

La reparación automática de nodos de EKS es un mecanismo real e independiente. Auto Mode la habilita de forma predeterminada; los grupos de nodos administrados pueden habilitar `nodeRepairConfig`, y Karpenter tiene sus propios requisitos de función/configuración. La supervisión de nodos informa de condiciones adicionales, pero la detección por sí sola no habilita la reparación. La tabla predeterminada actual incluye reemplazos por fallos persistentes de `Ready`, runtime, kernel, redes y almacenamiento; `MemoryPressure` y `DiskPressure` **no tienen una acción de reparación predeterminada**. Los umbrales/paralelismo de reparación y los controles ARC/de flota en mal estado pueden detener nuevas acciones mientras las que están en curso continúan. No prometa que una Lambda personalizada, una etiqueta ASG o `maxUnavailable` proporcionan automáticamente este comportamiento.

### Problemas de Pods que no se ejecutan

#### Lea el estado, los eventos y el controlador propietario

```bash
set -euo pipefail
: "${KUBE_CONTEXT:?}"; : "${NAMESPACE:?}"; : "${POD_NAME:?}"
POD_JSON=$(kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" get pod "$POD_NAME" -o json)
printf '%s\n' "$POD_JSON" | jq '{
  name:.metadata.name,uid:.metadata.uid,owners:.metadata.ownerReferences,
  node:.spec.nodeName,serviceAccount:.spec.serviceAccountName,
  imagePullSecrets:.spec.imagePullSecrets,
  containers:[.spec.containers[] | {name,image,imagePullPolicy,resources}],
  initContainers:[.spec.initContainers[]? | {name,image,resources}],
  phase:.status.phase,reason:.status.reason,message:.status.message,
  conditions:.status.conditions,containerStatuses:.status.containerStatuses,
  initContainerStatuses:.status.initContainerStatuses
}'
POD_UID=$(printf '%s\n' "$POD_JSON" | jq -er '.metadata.uid')
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" get events \
  --field-selector "involvedObject.uid=$POD_UID" --sort-by='.metadata.creationTimestamp'
```

Use el procedimiento de registros por contenedor de la sección de fundamentos. `Pending`, `ContainerCreating`, la espera de descarga de imagen, un fallo de contenedor de inicialización, un fallo de preparación, `OOMKilled` y el retroceso de reinicio describen problemas distintos. `CrashLoopBackOff` es el retroceso tras fallos repetidos del contenedor; no es una causa raíz.

| Evidencia | Comprobaciones siguientes |
| --- | --- |
| Error al descargar la imagen | Registro/nombre/etiqueta/digest/arquitectura, DNS/TLS/rutas del lado del nodo, límites de frecuencia e identidad real usada para descargar la imagen |
| FailedScheduling | Solicitudes frente a capacidad asignable, número de Pods, taints/afinidad/topología, cuota y restricciones de consumidores de PVC |
| FailedMount / conexión | PVC/PV/StorageClass, CSI/identidad, AZ y conexión actual; consulte la sección de almacenamiento |
| OOMKilled / Evicted | Estado de terminación del contenedor, límites, presión del nodo e historial de uso; no presuponga una fuga de memoria |
| Forbidden / error de admisión | Actor exacto de la API, RBAC o política de admisión; añadir permisos para listar Pods no soluciona un acceso no relacionado al registro/sistema de archivos |

Cambiar `imagePullPolicy` a `Always` no soluciona la ausencia de una imagen ni las credenciales no válidas. Descargar una imagen con Docker en una laptop no verifica la ruta/identidad del nodo, y cargarla en Docker no la incorpora automáticamente a un runtime containerd.

#### Credenciales del registro y cambios de cargas de trabajo

Para ECR privado, revise la identidad de ejecución real del nodo/Fargate y la política del repositorio. IRSA/Pod Identity de la aplicación no es la identidad que descarga su imagen antes del inicio. Las redes de ECR privado pueden requerir acceso a ECR API/DKR y S3; un endpoint de ECR no proporciona acceso privado a registros arbitrarios.

Para un registro que requiera un Secret de descarga de imagen, use un archivo JSON de autenticación de Docker protegido e independiente con las credenciales correctas del registro. No muestre `.dockerconfigjson` ni contraseñas en registros/argumentos de comandos; las referencias a ayudantes de credenciales del escritorio, por sí solas, no son credenciales que kubelet pueda usar.

```bash
set -euo pipefail
: "${KUBE_CONTEXT:?}"; : "${NAMESPACE:?}"; : "${DEPLOYMENT_NAME:?}"
: "${PULL_SECRET_NAME:?Choose an application-specific secret name}"
: "${DOCKER_CONFIG_JSON:?Provide a protected registry auth JSON file}"
# Separate reviewed change; an existing Secret causes create to fail rather than replacing it.
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" create secret generic "$PULL_SECRET_NAME" \
  --type=kubernetes.io/dockerconfigjson \
  --from-file=".dockerconfigjson=$DOCKER_CONFIG_JSON"
PATCH=$(jq -n --arg name "$PULL_SECRET_NAME" \
  '{spec:{template:{spec:{imagePullSecrets:[{name:$name}]}}}}')
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" patch deployment "$DEPLOYMENT_NAME" \
  --type=strategic --patch "$PATCH"
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" rollout status \
  "deployment/$DEPLOYMENT_NAME" --timeout=5m
```

El Secret debe estar en el espacio de nombres del Pod. El parche estratégico de la plantilla del Pod combina las entradas de los Secrets de descarga por nombre e inicia un despliegue controlado del Deployment; conserve la propiedad de la versión y otros ajustes. Por lo general, `imagePullSecrets` de un Pod existente no es un campo editable. Los valores predeterminados de ServiceAccount afectan a los Pods admitidos posteriormente; cambiar la ServiceAccount predeterminada de todo un espacio de nombres puede afectar a cargas de trabajo no relacionadas. Renueve las credenciales que caducan mediante su propietario en vez de eliminar y volver a crear un Secret compartido según un temporizador.

Para otros cambios de configuración, corrija la plantilla declarada del controlador y observe el despliegue y la disponibilidad. Eliminar un Pod solo lo vuelve a crear si existe un controlador apropiado, y puede eliminar evidencias útiles. Un Pod de depuración `--copy-to` puede duplicar efectos secundarios de la aplicación; use en su lugar un método de diagnóstico y una imagen revisados, con permisos explícitos y limpieza.

### Problemas de restricciones de recursos

```bash
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" get resourcequotas,limitranges
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" get pods -o wide
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" top pods --containers
kubectl --context "$KUBE_CONTEXT" top nodes
```

Los comandos de métricas requieren Metrics Server y acceso funcional a kubelet. La planificación usa las solicitudes de recursos y la capacidad asignable del nodo, no el uso actual de `kubectl top`. Cuando corresponda, incluya los contenedores de inicialización, la sobrecarga de Pods, el almacenamiento efímero, los recursos extendidos y los límites de cantidad de Pods. Las cuotas del espacio de nombres y los LimitRange son restricciones distintas.

Reduzca las solicitudes solo si las necesidades medidas de la carga de trabajo lo justifican; bajar una solicitud de memoria no soluciona `Insufficient pods` ni garantiza que un contenedor quepa dentro de su límite. Aumentar los límites puede trasladar la presión al nodo. Resuelva el uso del disco/inodos y del sistema de archivos/imágenes antes de eliminar registros o cachés, y conserve las evidencias del incidente.

Aumentar el número de nodos no modifica la capacidad por instancia. Para grupos administrados, coordine los valores deseados/mínimos/máximos con su autoscaler; reducir la configuración de escalado no respeta los PDB. Para cambiar el tipo de instancia, use un grupo nuevo apropiado o la ruta admitida de la plantilla/versión de lanzamiento original. No quite taints ni restricciones de afinidad o topología solo para que se pueda programar un Pod.

### Problemas de escalado automático

Separe el escalado de réplicas (HPA), las recomendaciones/actualizaciones de recursos (VPA), el aprovisionamiento de nodos (CA, Karpenter o Auto Mode) y los cuellos de botella de la aplicación. Es normal que no haya un Pod de CA cuando otro aprovisionador de nodos controla la capacidad.

```bash
set -euo pipefail
: "${KUBE_CONTEXT:?}"; : "${NAMESPACE:?}"
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" get hpa -o json \
  | jq '.items[] | {name:.metadata.name,target:.spec.scaleTargetRef,min:.spec.minReplicas,max:.spec.maxReplicas,current:.status.currentReplicas,desired:.status.desiredReplicas,metrics:.status.currentMetrics,conditions:.status.conditions}'
kubectl --context "$KUBE_CONTEXT" get apiservice v1beta1.metrics.k8s.io
kubectl --context "$KUBE_CONTEXT" get --raw "/apis/metrics.k8s.io/v1beta1/namespaces/$NAMESPACE/pods"
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" get events \
  --sort-by='.metadata.creationTimestamp'
```

Inspeccione condiciones del HPA como `AbleToScale`, `ScalingActive` y `ScalingLimited`, además de las métricas y el comportamiento actuales. Una diferencia temporal entre las réplicas deseadas y las actuales no es automáticamente un fallo. Los objetivos de utilización de CPU/memoria requieren solicitudes de recursos; las métricas personalizadas/externas usan su propio adaptador de API o integración con KEDA. Los errores de métricas pueden impedir la reducción de escala.

Para CA, inspeccione la versión instalada, la versión menor de Kubernetes compatible, la identidad, las etiquetas de detección, las restricciones de los Pods no programables y los máximos/cuotas de los grupos de nodos. CA no añade nodos solo porque el promedio de CPU de los nodos sea alto. Para Karpenter/Auto Mode, inspeccione los límites y eventos correspondientes de NodePool/NodeClaim/proveedor; no instale CA como solución general.

Para VPA, distinga el modo de solo recomendación `Off`, el modo `Initial` aplicado al crear y los modos de actualización deliberados. `Auto` está obsoleto y se reemplazó por `Recreate`; cambiar de modo puede interrumpir las cargas de trabajo y entrar en conflicto con un HPA que use las mismas señales de CPU/memoria. Una consulta fallida a la API no demuestra que falte la CRD de VPA.

Este es un ejemplo de HPA con **métricas de recursos**, no una configuración de métricas personalizadas:

```yaml
# Resource metrics example, not a custom/external-metrics adapter configuration.
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: app-hpa
  namespace: applications
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: app
  minReplicas: 2
  maxReplicas: 10
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70
    - type: Resource
      resource:
        name: memory
        target:
          type: Utilization
          averageUtilization: 80
  behavior:
    scaleDown:
      stabilizationWindowSeconds: 300
```

Los porcentajes 70 %/80 %, los límites de réplicas y el período de estabilización son ajustes ilustrativos, no recomendaciones basadas en mediciones. El Deployment de destino debe existir, tener solicitudes adecuadas y disponer de capacidad. El HPA elige la recomendación de réplicas más alta entre las métricas; el comportamiento de la memoria y los fallos de adaptadores requieren pruebas específicas de la carga de trabajo. Mantenga un único propietario del escalado de réplicas y evite que Terraform/GitOps restablezca continuamente `.spec.replicas`.

Consulte los [conceptos de escalado automático](../core/09-cluster-administration.md) y la configuración documentada del controlador instalado. Verifique los valores/identidad reales de Helm y una versión firmada y fijada en vez de aplicar un manifiesto `master` sin revisar o conceder `AutoScalingFullAccess` al rol del nodo.

Fuentes: [Reparación de nodos de EKS](https://docs.aws.amazon.com/eks/latest/userguide/node-repair.html), [Ciclo de vida de Pods](https://kubernetes.io/docs/concepts/workloads/pods/pod-lifecycle/), [Descargas de imágenes privadas](https://kubernetes.io/docs/tasks/configure-pod-container/pull-image-private-registry/), [HPA](https://kubernetes.io/docs/tasks/run-application/horizontal-pod-autoscale/), [VPA](https://github.com/kubernetes/autoscaler/tree/master/vertical-pod-autoscaler).

## Problemas de IAM y autenticación {#iam-and-authentication-issues}

<!-- Audit 2026-09-11: parent diagram repair pending; see core-audit/eks-troubleshooting/diagram-review.json.
![IAM and Kubernetes authorization symptoms; use the cluster authentication mode and actual caller to select the diagnostic path.](../.gitbook/assets/en-eks-09-eks-troubleshooting-4.png)

[🔍 View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-09-eks-troubleshooting-4.html)
-->

### Acceso al clúster denegado

Separe el solicitante de AWS, los permisos de API de EKS, la autenticación kubeconfig/STS, la asignación de identidad del clúster y la autorización de Kubernetes. El rol IAM que usa el plano de control de EKS no es el rol del operador humano. Que `DescribeCluster` de AWS se ejecute correctamente no concede acceso a Kubernetes.

```bash
set -euo pipefail
: "${CLUSTER_NAME:?}"; : "${AWS_REGION:?}"; : "${KUBE_CONTEXT:?}"; : "${NAMESPACE:?}"
aws sts get-caller-identity
aws eks describe-cluster --name "$CLUSTER_NAME" --region "$AWS_REGION" \
  --query 'cluster.{arn:arn,endpoint:endpoint,access:accessConfig}'
kubectl config view --context "$KUBE_CONTEXT" --minify \
  -o jsonpath='{.contexts[0].name}{"\n"}{.clusters[0].cluster.server}{"\n"}'
kubectl --context "$KUBE_CONTEXT" auth can-i get pods -n "$NAMESPACE"
```

Para errores de transporte, use las comprobaciones de endpoint/CA de la sección de acceso. Si las credenciales han caducado, renueve la sesión SSO/federada/de rol asumido configurada y confirme el perfil/rol seleccionado. `sts get-session-token` no es un comando universal para renovar credenciales, y mostrar su salida puede exponerlas.

Inspeccione el modo de autenticación del clúster antes de decidir cómo funciona la asignación de identidades:

```bash
set -euo pipefail
: "${CLUSTER_NAME:?}"; : "${AWS_REGION:?}"; : "${PRINCIPAL_ARN:?Set the exact IAM principal}"
# These APIs apply to clusters with API or API_AND_CONFIG_MAP authentication.
aws eks list-access-entries --cluster-name "$CLUSTER_NAME" --region "$AWS_REGION"
aws eks describe-access-entry --cluster-name "$CLUSTER_NAME" --region "$AWS_REGION" \
  --principal-arn "$PRINCIPAL_ARN"
aws eks list-associated-access-policies --cluster-name "$CLUSTER_NAME" --region "$AWS_REGION" \
  --principal-arn "$PRINCIPAL_ARN"
```

Para el acceso basado en API, inspeccione el principal exacto, el tipo de entrada, los grupos de Kubernetes y el ámbito de espacio de nombres/clúster de la política de acceso asociada. `aws-auth` es pertinente para `CONFIG_MAP` y el modo mixto heredado; no presuponga que su ausencia implica que todo acceso esté interrumpido. Conserve las asignaciones de nodos y siga la ruta de migración documentada antes de cambiar el modo de autenticación.

No sustituya `aws-auth` por un ejemplo breve ni conceda `system:masters` como solución genérica. Las concesiones limitadas a espacios de nombres no revocan las concesiones más amplias que ya existan mediante otra vinculación/política de acceso. Corrija la ruta de acceso prevista a través de su responsable.

### Problemas de RBAC

Un fallo de autenticación, una respuesta `Forbidden` de Kubernetes y una solicitud de suplantación fallida son evidencias distintas. Compruebe el verbo exacto de la API, el recurso/subrecurso, el espacio de nombres y el tipo de sujeto.

```bash
set -euo pipefail
: "${KUBE_CONTEXT:?}"; : "${NAMESPACE:?}"
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" get roles,rolebindings
kubectl --context "$KUBE_CONTEXT" get clusterroles,clusterrolebindings
: "${SUBJECT_NAME:?Set the exact subject name}"
kubectl --context "$KUBE_CONTEXT" get rolebindings -A -o json \
  | jq --arg name "$SUBJECT_NAME" '.items[] | select(any(.subjects[]?; .name == $name)) | {namespace:.metadata.namespace,name:.metadata.name,roleRef,subjects}'
kubectl --context "$KUBE_CONTEXT" get clusterrolebindings -o json \
  | jq --arg name "$SUBJECT_NAME" '.items[] | select(any(.subjects[]?; .name == $name)) | {name:.metadata.name,roleRef,subjects}'
```

Las consultas encuentran candidatos por nombre de sujeto; revise `kind`, el espacio de nombres de la ServiceAccount y `roleRef`, porque una misma cadena puede identificar sujetos distintos. `kubectl auth can-i --as=...` requiere permiso de suplantación. Las comprobaciones RBAC suplantadas y la salida de `--list` no reproducen todas las concesiones de las políticas de acceso de EKS; pruebe también con el principal autenticado previsto.

Por ejemplo, después de asignar deliberadamente una entrada de acceso IAM estándar a `eks-troubleshoot-readers`, el siguiente Role concede únicamente lectura de Pods/Services/eventos/EndpointSlices en el espacio de nombres y de registros de Pods:

```yaml
# Example for a deliberately mapped Kubernetes group in an existing namespace.
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: troubleshooting-reader
  namespace: applications
rules:
  - apiGroups: [""]
    resources: [pods, services, events]
    verbs: [get, list, watch]
  - apiGroups: [""]
    resources: [pods/log]
    verbs: [get]
  - apiGroups: [discovery.k8s.io]
    resources: [endpointslices]
    verbs: [get, list, watch]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: troubleshooting-readers
  namespace: applications
subjects:
  - kind: Group
    name: eks-troubleshoot-readers
    apiGroup: rbac.authorization.k8s.io
roleRef:
  kind: Role
  name: troubleshooting-reader
  apiGroup: rbac.authorization.k8s.io
```

El espacio de nombres debe existir previamente y la asignación del grupo debe revisarse por separado. Para una ServiceAccount de aplicación, use una vinculación distinta con `kind: ServiceAccount`, su nombre exacto y su espacio de nombres. La lectura de nodos/espacios de nombres tiene ámbito de clúster y requiere un ClusterRole revisado explícitamente; no conceda acceso de administrador del clúster a todos los usuarios de diagnóstico. El acceso a los registros puede revelar datos de la aplicación aunque este Role no conceda lectura de Secrets.

### Problemas de IRSA y Pod Identity

IRSA proporciona **credenciales de AWS para cargas de trabajo**; el proveedor IAM OIDC del clúster no es el mecanismo por el que un principal IAM humano obtiene acceso RBAC a Kubernetes. Inspeccione la ServiceAccount real del Pod, la confianza y las políticas de permisos, la cadena de credenciales del SDK y la accesibilidad de los endpoints de servicio:

```bash
set -euo pipefail
: "${CLUSTER_NAME:?}"; : "${AWS_REGION:?}"; : "${KUBE_CONTEXT:?}"
: "${NAMESPACE:?}"; : "${SERVICE_ACCOUNT:?}"; : "${POD_NAME:?}"; : "${ROLE_NAME:?}"
aws eks describe-cluster --name "$CLUSTER_NAME" --region "$AWS_REGION" \
  --query cluster.identity.oidc.issuer --output text
aws iam get-role --role-name "$ROLE_NAME" --query 'Role.{Arn:Arn,Trust:AssumeRolePolicyDocument}'
aws iam list-attached-role-policies --role-name "$ROLE_NAME"
aws iam list-role-policies --role-name "$ROLE_NAME"
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" get serviceaccount "$SERVICE_ACCOUNT" -o json \
  | jq '{name:.metadata.name,namespace:.metadata.namespace,annotations:.metadata.annotations}'
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" get pod "$POD_NAME" -o json \
  | jq '{serviceAccount:.spec.serviceAccountName,containers:[.spec.containers[] | {name,awsEnvironmentNames:[.env[]? | select(.name | startswith("AWS_")) | .name]}]}'
```

Aquí solo se muestran los nombres de las variables de entorno de AWS. No vuelque todos los valores de entorno del Pod ni los tokens proyectados para diagnosticar la identidad. Con IRSA, confirme que se usan el token de identidad web proyectado y el rol configurado mediante un SDK compatible; una fuente anterior de credenciales estáticas o predeterminadas puede tener prioridad.

Esta declaración de confianza ilustrativa vincula el sujeto de una ServiceAccount y la audiencia STS. Sustituya la cuenta, la partición, la región, el ID del emisor y el sujeto por valores verificados; no es una política con la que sobrescribir un rol compartido:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Federated": "arn:aws:iam::123456789012:oidc-provider/oidc.eks.us-west-2.amazonaws.com/id/EXAMPLE"
      },
      "Action": "sts:AssumeRoleWithWebIdentity",
      "Condition": {
        "StringEquals": {
          "oidc.eks.us-west-2.amazonaws.com/id/EXAMPLE:aud": "sts.amazonaws.com",
          "oidc.eks.us-west-2.amazonaws.com/id/EXAMPLE:sub": "system:serviceaccount:applications:app"
        }
      }
    }
  ]
}
```

Conserve las demás declaraciones de confianza legítimas al modificar el rol administrado. Las políticas de permisos de IAM, las políticas de recursos, las concesiones de KMS y los controles de la organización todavía pueden denegar la acción de AWS después de asumir correctamente el rol. Actualizar una anotación de ServiceAccount no incorpora retroactivamente variables de entorno/configuración de volúmenes a un Pod existente; coordine un despliegue con el propietario de la carga de trabajo.

La guía actual de EKS admite un endpoint PrivateLink independiente `com.amazonaws.<region>.oidc-eks` para la detección de OIDC/JWKS. Es distinto del endpoint de administración de EKS, de `eks-auth` para Pod Identity y de STS. El acceso privado a OIDC no crea por sí mismo el proveedor IAM, concede confianza al rol ni permite el acceso a STS.

Para EKS Pod Identity, inspeccione la asociación del espacio de nombres/ServiceAccount exactos:

```bash
set -euo pipefail
: "${CLUSTER_NAME:?}"; : "${AWS_REGION:?}"; : "${NAMESPACE:?}"; : "${SERVICE_ACCOUNT:?}"
aws eks list-pod-identity-associations --cluster-name "$CLUSTER_NAME" --region "$AWS_REGION" \
  --namespace "$NAMESPACE" --service-account "$SERVICE_ACCOUNT"
```

Luego inspeccione el ID de asociación devuelto, la confianza/permisos del rol y los requisitos compatibles del agente/SDK/cómputo. La ausencia de una anotación IRSA no es un fallo de Pod Identity. Importan las actualizaciones de asociaciones, el almacenamiento en caché de credenciales y los proveedores SDK anteriores; no cambie de mecanismo de identidad ni elimine la confianza IRSA existente antes de validar todos los consumidores. Consulte el [capítulo de seguridad](./05-eks-security.md) para conocer las rutas actuales de configuración/migración.

### Error al incorporar nodos

```bash
set -euo pipefail
: "${CLUSTER_NAME:?}"; : "${AWS_REGION:?}"; : "${NODEGROUP_NAME:?}"
aws eks describe-nodegroup --cluster-name "$CLUSTER_NAME" --nodegroup-name "$NODEGROUP_NAME" \
  --region "$AWS_REGION" \
  --query 'nodegroup.{name:nodegroupName,status:status,health:health,nodeRole:nodeRole,subnets:subnets,amiType:amiType,release:releaseVersion,launchTemplate:launchTemplate}'
aws eks describe-cluster --name "$CLUSTER_NAME" --region "$AWS_REGION" \
  --query 'cluster.{endpoint:endpoint,access:accessConfig,vpc:resourcesVpcConfig}'
```

Para un grupo administrado, use `health.issues`, los detalles de la plantilla de lanzamiento/AMI/inicialización y el estado real de la instancia EC2. Para los nodos autoadministrados/híbridos, inspeccione su propio mecanismo de inicialización y registro en vez de presuponer que una API de nodos administrados los describe.

Confirme el **ARN del rol IAM**, no el ARN de un perfil de instancia, y la asignación de autenticación/entrada de acceso apropiada para nodos. Los grupos de nodos administrados y Fargate tienen comportamientos de identidad administrados por el servicio; no sobrescriba sus asignaciones. Los access entries de nodos tienen tipos/semánticas distintos de las entradas estándar para humanos. Las rutas de los roles y las restricciones heredadas de `aws-auth` también requieren consultar las directrices del modo de autenticación correspondiente.

Inspeccione las políticas de nodos requeridas y los permisos para descargar imágenes de ECR, pero mantenga los permisos de CNI/CSI/aplicaciones en sus identidades reales cuando sea compatible. Añadir `AmazonEKSClusterPolicy` o todos los permisos de CNI/almacenamiento al rol de un nodo no es una solución general de registro.

Compruebe HTTPS del nodo al servidor de API, el puerto 10250 del servidor de API a kubelet y las rutas reales de webhook/dependencias, incluidos DNS, rutas/NACL y la dirección de los grupos de seguridad. Las reglas para un webhook de backend no implican que todos los nodos necesiten tráfico entrante 443 desde cualquier origen.

Use el modelo de inicialización de la AMI: AL2023/nodeadm, la configuración de Bottlerocket y las AMI personalizadas tienen requisitos previos diferentes. Volver a ejecutar un script de AL2 o reemplazar solo kubelet no puede reparar todas las imágenes. Conserve las evidencias y siga el procedimiento de reemplazo de nodos del propietario después de solucionar la causa verificada.

Fuentes: [Access entries de EKS](https://docs.aws.amazon.com/eks/latest/userguide/access-entries.html), [RBAC](https://kubernetes.io/docs/reference/access-authn-authz/rbac/), [IRSA](https://docs.aws.amazon.com/eks/latest/userguide/iam-roles-for-service-accounts.html), [PrivateLink de OIDC](https://docs.aws.amazon.com/eks/latest/userguide/irsa-fetch-keys.html), [EKS Pod Identity](https://docs.aws.amazon.com/eks/latest/userguide/pod-identities.html).

## Problemas de almacenamiento {#storage-issues}

### Diagnóstico de PVC, PV y consumidores

Comience por identificar el espacio de nombres, el claim y el UID exactos, el provisionador y el consumidor. Que un PVC esté `Pending` con `WaitForFirstConsumer` puede ser normal hasta que se programe un Pod consumidor adecuado. Inspeccione las restricciones de programación/zona/capacidad de ese Pod, así como el controlador de almacenamiento.

```bash
set -euo pipefail
: "${KUBE_CONTEXT:?}"; : "${NAMESPACE:?}"; : "${PVC_NAME:?}"
PVC_JSON=$(kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" get pvc "$PVC_NAME" -o json)
printf '%s\n' "$PVC_JSON" | jq '{name:.metadata.name,uid:.metadata.uid,status:.status,spec:.spec,storageClassFieldPresent:(.spec | has("storageClassName"))}'
PVC_UID=$(printf '%s\n' "$PVC_JSON" | jq -er '.metadata.uid')
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" get events \
  --field-selector "involvedObject.uid=$PVC_UID" --sort-by='.metadata.creationTimestamp'
SC_NAME=$(printf '%s\n' "$PVC_JSON" | jq -r '.spec.storageClassName // empty')
if [ -n "$SC_NAME" ]; then
  kubectl --context "$KUBE_CONTEXT" get storageclass "$SC_NAME" -o yaml
else
  printf 'Inspect absent versus explicitly empty storageClassName and default/static binding intent.\n'
fi
PV_NAME=$(printf '%s\n' "$PVC_JSON" | jq -r '.spec.volumeName // empty')
if [ -n "$PV_NAME" ]; then
  kubectl --context "$KUBE_CONTEXT" get pv "$PV_NAME" -o yaml
  kubectl --context "$KUBE_CONTEXT" get volumeattachments -o json \
    | jq --arg pv "$PV_NAME" '.items[] | select(.spec.source.persistentVolumeName == $pv) | {name:.metadata.name,spec,status}'
fi
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" get pods -o json \
  | jq --arg pvc "$PVC_NAME" '.items[] | select(any(.spec.volumes[]?; .persistentVolumeClaim.claimName == $pvc)) | {name:.metadata.name,node:.spec.nodeName,phase:.status.phase,conditions:.status.conditions}'
```

No existe un selector de campo de Pod compatible para `spec.volumes.persistentVolumeClaim.claimName`; la consulta JSON anterior selecciona los consumidores sin usar ese filtro de API no válido. La ausencia de `storageClassName` y una cadena explícitamente vacía tienen intenciones distintas respecto a los valores predeterminados y la vinculación estática. No consulte una clase literal `<default>`.

El YAML de un PVC es la configuración de un objeto, no una copia de seguridad de su contenido. Eliminar y volver a crear un claim puede eliminar el almacenamiento subyacente con `Delete` o dejar un PV conservado que deba volver a vincularse deliberadamente. No lo use como solución general para `Pending`/`FailedMount`. Antes de cualquier cambio del ciclo de vida, compruebe la política de recuperación, las instantáneas/copias de seguridad y quién es el responsable de la carga de trabajo/los datos. Que un claim esté Bound no demuestra que una aplicación pueda montarlo o leerlo.

### Problemas de volúmenes EBS

#### Compruebe el controlador y el volumen real

Distinga entre `ebs.csi.aws.com` estándar, `ebs.csi.eks.amazonaws.com` de Auto Mode, los volúmenes heredados/migrados y sus propietarios. Los permisos del controlador EBS CSI estándar suelen proceder de su identidad IAM configurada; inspeccionar solo el rol IAM del nodo no basta. Incluya los permisos KMS para la clave real y el estado de los componentes del controlador/nodo.

El cifrado de volúmenes raíz/de datos de nodos de Auto Mode no demuestra la configuración de cifrado de cada PVC de carga de trabajo. La referencia actual de [StorageClass de Auto Mode](https://docs.aws.amazon.com/eks/latest/userguide/create-storage-class.html) indica que `encrypted` tiene el valor predeterminado `false`; solicite explícitamente `encrypted: "true"` para cualquiera de los dos provisionadores EBS y verifique el volumen/la clave EBS reales. Los valores predeterminados de cifrado de la cuenta y las propiedades de las instantáneas también pueden afectar el resultado.

Auto Mode no necesita un controlador EBS CSI estándar instalado por separado para sus propios volúmenes. Los volúmenes EBS no se pueden montar en Pods de Fargate y el controlador/los volúmenes EBS CSI no son compatibles con EKS Hybrid Nodes. Ejecutar un controlador en Fargate no permite montar EBS en cargas de trabajo de Fargate.

```bash
set -euo pipefail
: "${AWS_REGION:?}"; : "${VOLUME_ID:?Verify it from the selected PV CSI volumeHandle}"
aws ec2 describe-volumes --region "$AWS_REGION" --volume-ids "$VOLUME_ID" \
  --query 'Volumes[].{Id:VolumeId,State:State,AZ:AvailabilityZone,Type:VolumeType,Size:Size,Encrypted:Encrypted,KmsKey:KmsKeyId,Attachments:Attachments}'
aws ec2 describe-volume-status --region "$AWS_REGION" --volume-ids "$VOLUME_ID"
```

Verifique que el Pod/nodo seleccionado y el volumen EBS puedan usar la misma AZ, e inspeccione los límites de conexión, los errores de CSI y el estado actual de VolumeAttachment/EC2. Los nombres de PVC no son únicos entre espacios de nombres ni volúmenes antiguos; identifique el volumen exacto mediante su PV.

#### Recuperación de conexiones y montajes

En caso de Multi-Attach, determine si un consumidor antiguo sigue ejecutándose o escribiendo, si su nodo es accesible o está aislado, y si un despliegue colocó un segundo consumidor en otro nodo. `ReadWriteOnce` es un modo de acceso de un único nodo, no un bloqueo de un único Pod. Coordine la detención de la carga de trabajo y el desmontaje/desacoplamiento de CSI; no se limite a eliminar el objeto Pod suponiendo que el proceso se ha detenido.

La conexión/desconexión manual no sustituye la conciliación de CSI. Si la recuperación requiere intervención manual, confirme que los escritores estén detenidos, proteja los datos y siga el procedimiento de recuperación de EBS; desconectar un volumen montado puede dañar los datos. No eluda errores de conexión reiniciando repetidamente nodos ni forzando la desconexión.

#### StorageClass y aprovisionamiento

Para una clase nueva del controlador estándar, este es un ejemplo con cifrado explícito, vinculación diferida y retención:

```yaml
# New, explicitly selected StorageClass for standard EBS CSI, not an in-place edit.
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: diagnostic-ebs-gp3
provisioner: ebs.csi.aws.com
parameters:
  type: gp3
  encrypted: "true"
  csi.storage.k8s.io/fstype: ext4
volumeBindingMode: WaitForFirstConsumer
allowVolumeExpansion: true
reclaimPolicy: Retain
```

Esto no modifica la clase de un PVC existente. El provisionador, los parámetros y el modo de vinculación no se pueden cambiar libremente en un StorageClass existente, y cambiar la clase predeterminada afecta a otros claims. `Retain` deja intencionalmente el almacenamiento para una decisión de limpieza independiente y puede seguir generando cargos. La expansión requiere compatibilidad con el controlador, la clase y el sistema de archivos; no permite reducir un PVC editando el tamaño solicitado.

Elija y configure un complemento CSI compatible a través de su propietario actual, incluidas su identidad IRSA/Pod Identity real y toda la configuración. `eksctl create iamserviceaccount --role-only` crea un rol; por sí solo no lo asocia con un complemento. Use la identidad del complemento y el procedimiento de actualización que haya inspeccionado en lugar de reinstalarlo con `--force`.

Para migrar a Auto Mode, la [guía de EBS](https://docs.aws.amazon.com/eks/latest/userguide/ebs-csi.html) documenta la migración mediante instantáneas, mientras que la [guía de migración de Auto Mode](https://docs.aws.amazon.com/eks/latest/userguide/migrate-auto.html) también describe una ruta con cargas de trabajo detenidas, Retain y PV estático. Antes de elegir una ruta, valide el controlador aplicable, las etiquetas/IAM, el ciclo de vida del claim/finalizer y el plan de recuperación. Cambiar una cadena de provisionador en un claim vinculado no es una migración. El uso de instantáneas también requiere el controlador/las CRD de instantáneas de CSI y las clases/permisos apropiados.

### Problemas de volúmenes EFS

#### Rastree por separado el aprovisionamiento y el acceso de montaje

Inspeccione el sistema de archivos/punto de acceso a partir del PV, el nodo/AZ consumidor, la disponibilidad del destino de montaje, DNS y la ruta NFS. Los permisos de API del controlador para crear puntos de acceso y los permisos del cliente para montar/acceder a archivos son distintos. Revise las políticas del sistema de archivos, los requisitos de TLS/IAM, la identidad POSIX del punto de acceso, la propiedad del directorio raíz y el UID/GID de la aplicación.

```bash
set -euo pipefail
: "${AWS_REGION:?}"; : "${FILE_SYSTEM_ID:?Verify the filesystem from the PV}"
aws efs describe-file-systems --region "$AWS_REGION" --file-system-id "$FILE_SYSTEM_ID"
aws efs describe-mount-targets --region "$AWS_REGION" --file-system-id "$FILE_SYSTEM_ID"
aws efs describe-access-points --region "$AWS_REGION" --file-system-id "$FILE_SYSTEM_ID"
: "${MOUNT_TARGET_ID:?Choose the mount target on the affected path}"
aws efs describe-mount-target-security-groups --region "$AWS_REGION" \
  --mount-target-id "$MOUNT_TARGET_ID"
```

Compruebe TCP 2049 de NFS entre la identidad de red real del cliente y el destino de montaje, incluidas las rutas/NACL y los grupos de seguridad. No deduzca las subredes de los nodos a partir de las subredes del plano de control. Use un destino de montaje apropiado para la AZ/topología de la carga de trabajo; crear otro destino de montaje es un cambio independiente de infraestructura.

En las configuraciones EC2 compatibles, inspeccione las versiones compatibles actuales del controlador y del complemento de nodo EFS CSI instalados. Fargate tiene montaje EFS integrado y admite la ruta documentada de aprovisionamiento estático; la guía actual de EKS no admite el aprovisionamiento dinámico en nodos de Fargate. El controlador EFS CSI no es compatible con contenedores Windows ni EKS Hybrid Nodes. No instale a ciegas un manifiesto antiguo `release-1.5` ni duplique un complemento administrado.

#### El aprovisionamiento dinámico y el estático son alternativas

El aprovisionamiento dinámico crea puntos de acceso en un sistema de archivos EFS **existente**; no crea ese sistema de archivos ni sus destinos de montaje. Sustituya el ID ilustrativo y revise la propiedad/permisos, la cuota y la retención del punto de acceso:

```yaml
# Dynamic EFS access-point provisioning example for a supported EC2-node setup.
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: diagnostic-efs-ap
provisioner: efs.csi.aws.com
parameters:
  provisioningMode: efs-ap
  fileSystemId: fs-0123456789abcdef0
  directoryPerms: "700"
mountOptions:
  - tls
reclaimPolicy: Retain
```

Como alternativa, un punto de acceso existente y preparado deliberadamente puede referenciarse mediante un PV estático:

```yaml
# Alternative static provisioning: replace the filesystem/access-point IDs.
apiVersion: v1
kind: PersistentVolume
metadata:
  name: diagnostic-efs-static
spec:
  capacity:
    storage: 5Gi
  volumeMode: Filesystem
  accessModes:
    - ReadWriteMany
  persistentVolumeReclaimPolicy: Retain
  storageClassName: ""
  mountOptions:
    - tls
  csi:
    driver: efs.csi.aws.com
    volumeHandle: fs-0123456789abcdef0::fsap-0123456789abcdef0
```

Vincule el PV estático con un claim revisado que especifique `storageClassName: ""` y el `volumeName` previsto; conserve la semántica de vinculación/claimRef. No lo combine con la clase dinámica y vincule involuntariamente un claim nuevo a la raíz del sistema de archivos. La capacidad `5Gi` es metadato de vinculación de Kubernetes, no una cuota de tamaño aplicada al directorio ni al sistema de archivos EFS.

Para diagnosticar un montaje, empiece por los eventos y registros existentes de Pod/CSI. Un Pod de diagnóstico debe usar el espacio de nombres del claim y un nodo/identidad compatibles; montar un PVC de aplicación en lectura/escritura solo para ejecutar `df` puede introducir otro escritor. Si se necesita una prueba, use un montaje explícito de solo lectura, una imagen preparada, una duración acotada y una limpieza que tenga en cuenta al propietario. No cree volúmenes EBS no relacionados ni conecte manualmente un dispositivo como «prueba» de almacenamiento.

Fuentes: [EBS CSI](https://docs.aws.amazon.com/eks/latest/userguide/ebs-csi.html), [EFS CSI](https://docs.aws.amazon.com/eks/latest/userguide/efs-csi.html), [Volúmenes persistentes](https://kubernetes.io/docs/concepts/storage/persistent-volumes/), [StorageClasses](https://kubernetes.io/docs/concepts/storage/storage-classes/).

## Problemas de registro y supervisión {#logging-and-monitoring-issues}

### CloudWatch Logs y Container Insights

Separe la entrega de registros del plano de control de EKS, la recopilación de aplicaciones/hosts mediante Fluent Bit u otro recopilador, las métricas del agente de CloudWatch y la instrumentación de aplicaciones. Habilitar el registro del clúster no instala un recopilador de aplicaciones, y que un recopilador esté en ejecución no demuestra que los datos hayan llegado a la cuenta/región/grupo previsto.

```bash
set -euo pipefail
: "${CLUSTER_NAME:?}"; : "${AWS_REGION:?}"; : "${KUBE_CONTEXT:?}"
aws eks describe-cluster --name "$CLUSTER_NAME" --region "$AWS_REGION" \
  --query cluster.logging
aws logs describe-log-groups --region "$AWS_REGION" \
  --log-group-name-prefix "/aws/eks/$CLUSTER_NAME/"
aws logs describe-log-groups --region "$AWS_REGION" \
  --log-group-name-prefix "/aws/containerinsights/$CLUSTER_NAME/"
: "${COLLECTOR_NAMESPACE:?}"; : "${COLLECTOR_POD:?}"; : "${COLLECTOR_CONTAINER:?}"
kubectl --context "$KUBE_CONTEXT" -n "$COLLECTOR_NAMESPACE" get pod "$COLLECTOR_POD" -o wide
kubectl --context "$KUBE_CONTEXT" -n "$COLLECTOR_NAMESPACE" logs "$COLLECTOR_POD" \
  -c "$COLLECTOR_CONTAINER" --since=15m --tail=200 --timestamps=true
```

Use el espacio de nombres, Pod, contenedor, configuración y destino del recopilador instalado en vez de presuponer convenciones de etiquetas/nombres. Compruebe las rutas de entrada, analizadores, filtros, almacenamiento en búfer/retroceso, capacidad del sistema de archivos, marcas de tiempo, errores de salida, DNS/TLS/endpoints y cuotas. La ausencia de grupos de registros puede indicar que no hay entrega, que el destino es distinto o que faltan permisos de consulta; crear un grupo a ciegas no corrige el productor.

Inspeccione la identidad IRSA/Pod Identity u otra identidad compatible real. Una política de nodo o una anotación de ServiceAccount por sí sola no demuestra qué credenciales usa el recopilador. Si el complemento de EKS CloudWatch Observability está instalado, inspeccione su propia identidad/estado:

```bash
set -euo pipefail
: "${CLUSTER_NAME:?}"; : "${AWS_REGION:?}"
# Only for an installation actually owned by this EKS add-on.
aws eks describe-addon --cluster-name "$CLUSTER_NAME" --region "$AWS_REGION" \
  --addon-name amazon-cloudwatch-observability \
  --query 'addon.{status:status,version:addonVersion,health:health,role:serviceAccountRoleArn,podIdentity:podIdentityAssociations}'
```

Un error de API no demuestra que falte el complemento; compruebe el error y el propietario real de Helm/complemento. Conserve ese propietario y la configuración personalizada al actualizar. No aplique como medida genérica de recuperación un inicio rápido antiguo de Fluentd/Fluent Bit sin renderizar ni sobrescriba una ServiceAccount existente. Las rutas de recopilación de Windows, Fargate, Auto Mode y EC2 son distintas.

Para Container Insights, consulte el espacio de nombres de métricas, las dimensiones y el intervalo real. El listado de métricas es metadato, no un punto de datos actual ni prueba de que una alarma/notificación funcione. Use consultas de datos acotadas y compárelas con los registros del recopilador. Proteja la configuración y las evidencias de registros; aplique cambios de retención/KMS solo a través del propietario del grupo de registros.

### Metrics Server y métricas de recursos

```bash
set -euo pipefail
: "${KUBE_CONTEXT:?}"; : "${NAMESPACE:?}"
kubectl --context "$KUBE_CONTEXT" get apiservice v1beta1.metrics.k8s.io -o yaml
kubectl --context "$KUBE_CONTEXT" get --raw "/apis/metrics.k8s.io/v1beta1/namespaces/$NAMESPACE/pods"
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" top pods --containers
kubectl --context "$KUBE_CONTEXT" top nodes
```

La API de métricas de recursos, las métricas de objetos de kube-state-metrics y las muestras de Prometheus/cAdvisor son fuentes de datos distintas. Inspeccione las condiciones de APIService, el acceso del agregador/RBAC, los registros de Metrics Server y su conexión con cada kubelet.

Para `Unauthorized`, identifique qué solicitante y endpoint rechazaron las credenciales. Para `Forbidden`, examine el verbo/recurso RBAC exactos. Un fallo de scraping puede deberse al enrutamiento, la dirección/puerto de kubelet, la validación de certificados, la autenticación o un kubelet en mal estado. No habilite el antiguo puerto no autenticado 10255 ni use `--kubelet-insecure-tls` como solución general.

Un error de recurso no encontrado para `v1.Pod` no demuestra por sí mismo que la configuración del servidor de API de EKS esté defectuosa. Confirme kubeconfig/URL, la detección de API, la compatibilidad del cliente y las respuestas del proxy. Reinstalar la versión más reciente de Metrics Server o reiniciar todos sus Pods antes de recopilar evidencias puede ocultar el problema.

### Prometheus y Grafana

```bash
set -euo pipefail
: "${KUBE_CONTEXT:?}"; : "${MONITORING_NAMESPACE:?}"; : "${MONITORING_RELEASE:?}"
helm status "$MONITORING_RELEASE" --namespace "$MONITORING_NAMESPACE" --kube-context "$KUBE_CONTEXT"
helm history "$MONITORING_RELEASE" --namespace "$MONITORING_NAMESPACE" --kube-context "$KUBE_CONTEXT"
kubectl --context "$KUBE_CONTEXT" -n "$MONITORING_NAMESPACE" get pods,services,pvc
kubectl --context "$KUBE_CONTEXT" -n "$MONITORING_NAMESPACE" get events \
  --sort-by='.metadata.creationTimestamp'
```

Identifique el chart/operator, el espacio de nombres de la versión, los puertos de Service, el almacenamiento y los selectores reales. `prometheus-community/prometheus` es un chart independiente; instalarlo no proporciona la conciliación de Prometheus Operator para recursos ServiceMonitor. Una pila basada en Operator tiene requisitos adicionales de CRD, recursos personalizados de Prometheus y selectores/RBAC.

Para inspeccionar un endpoint existente de Prometheus, mantenga abierto en una terminal este port-forward limitado al loopback:

```bash
: "${KUBE_CONTEXT:?}"; : "${MONITORING_NAMESPACE:?}"
: "${PROMETHEUS_SERVICE:?Select the actual Prometheus Service}"
: "${PROMETHEUS_SERVICE_PORT:?Select its Service port}"
kubectl --context "$KUBE_CONTEXT" -n "$MONITORING_NAMESPACE" port-forward \
  --address 127.0.0.1 "service/$PROMETHEUS_SERVICE" "9090:$PROMETHEUS_SERVICE_PORT"
```

En una segunda terminal local, para un endpoint que permita este acceso:

```bash
set -euo pipefail
curl --fail --silent --show-error --max-time 10 \
  http://127.0.0.1:9090/api/v1/targets \
  | jq '.data.activeTargets[] | {scrapePool,health,lastError,lastScrape}'
```

Adapte el esquema y la autenticación al endpoint real; no eluda sus controles de acceso. Compruebe los errores de scraping, el etiquetado, la detección de destinos, los intervalos de consulta y la retención. Una consulta vacía puede indicar que faltan etiquetas/datos, no que haya un uso cero y normal.

#### Selección de ServiceMonitor

Este ejemplo conecta el puerto de métricas con nombre de una aplicación existente con un ServiceMonitor de Operator:

```yaml
# Requires an existing application exporting metrics on a named container port "metrics".
apiVersion: v1
kind: Service
metadata:
  name: app-metrics
  namespace: applications
  labels:
    app: metrics-demo
spec:
  selector:
    app: metrics-demo
  ports:
    - name: metrics
      port: 9090
      targetPort: metrics
---
# Requires Prometheus Operator and a Prometheus CR selecting this namespace/label.
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: app-metrics
  namespace: monitoring
  labels:
    release: observability
spec:
  namespaceSelector:
    matchNames:
      - applications
  selector:
    matchLabels:
      app: metrics-demo
  endpoints:
    - port: metrics
      path: /metrics
      interval: 30s
```

Sustituya los espacios de nombres, las etiquetas y el selector de versión por los de la instalación real. Hay tres selecciones importantes: Prometheus selecciona los espacios de nombres de ServiceMonitor; su `serviceMonitorSelector` selecciona las etiquetas del monitor; el `namespaceSelector` y el `selector` del monitor seleccionan Services. `endpoints.port` nombra el **puerto del Service**, no un puerto de contenedor arbitrario. La aplicación debe escuchar y exponer realmente la ruta de métricas esperada. Prometheus también necesita permisos de detección y acceso de red/TLS/autenticación.

#### Conserve la configuración y verifique el cambio

```bash
set -euo pipefail
: "${KUBE_CONTEXT:?}"; : "${MONITORING_NAMESPACE:?}"; : "${MONITORING_RELEASE:?}"
: "${EVIDENCE_PARENT:?Set an existing private directory}"
umask 077
MONITORING_EVIDENCE=$(mktemp -d "$EVIDENCE_PARENT/monitoring-config.XXXXXXXX")
helm get values "$MONITORING_RELEASE" --namespace "$MONITORING_NAMESPACE" \
  --kube-context "$KUBE_CONTEXT" --all > "$MONITORING_EVIDENCE/values.yaml"
printf 'Protected configuration snapshot: %s\n' "$MONITORING_EVIDENCE"
```

Los valores pueden contener datos confidenciales aunque se escriban en un archivo protegido; enmascárelos antes de compartirlos. Revise los valores predeterminados del chart/destino, la migración de CRD, los valores personalizados, los recursos de las cargas de trabajo y la capacidad del PVC. Aplique las actualizaciones a través del propietario existente y valide después el comportamiento de scraping/alertas. Instalar una segunda pila o aplicar parches a ciegas a los límites de recursos no es un diagnóstico.

En Grafana, verifique el UID/URL/autenticación del origen de datos, el acceso a la red, las etiquetas/intervalos de tiempo de las consultas y la selección del aprovisionamiento de dashboards/sidecar. Un ConfigMap sin la etiqueta de sidecar o el espacio de nombres esperados no se convierte automáticamente en dashboard. Use el flujo de inicio de sesión/SSO existente; evite mostrar contraseñas de administrador en los registros de diagnóstico.

Consulte [Supervisión y registro de EKS](./06-eks-monitoring-logging.md) para ver los procedimientos revisados de instalación, consultas y alertas. Los ejemplos anteriores son plantillas de diagnóstico/configuración; no afirman que haya entrega de registros, cobertura de supervisión ni preparación para producción verificadas en un entorno real.

Fuentes: [Complemento de CloudWatch para EKS](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/Container-Insights-setup-EKS-addon.html), [Metrics Server](https://github.com/kubernetes-sigs/metrics-server), [Solución de problemas de Prometheus Operator](https://prometheus-operator.dev/docs/platform/troubleshooting/).

## Problemas de rendimiento {#performance-issues}

### Establezca una referencia comparable

Registre la carga de trabajo afectada, la tasa de solicitudes, la distribución de latencia/errores, las solicitudes/límites de recursos, el nodo/AMI/runtime, la ubicación y el período. El uso actual no equivale a la capacidad reservada ni a la saturación, y un aumento de memoria por sí solo no demuestra una fuga. Distinga entre cuellos de botella de nodo, Pod, almacenamiento, red y aplicación.

```bash
set -euo pipefail
: "${KUBE_CONTEXT:?}"; : "${NAMESPACE:?}"; : "${POD_NAME:?}"; : "${NODE_NAME:?}"
kubectl --context "$KUBE_CONTEXT" top nodes
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" top pods --containers
kubectl --context "$KUBE_CONTEXT" get node "$NODE_NAME" -o json \
  | jq '{nodeInfo:.status.nodeInfo,allocatable:.status.allocatable,conditions:.status.conditions}'
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" get pod "$POD_NAME" -o json \
  | jq '{containers:[.spec.containers[] | {name,resources}],status:.status}'
```

Las métricas requieren que funcione su ruta de recopilación. Incluya la limitación de CPU, el conjunto de trabajo/RSS/comportamiento del heap, el estado de terminación OOM, la latencia/cola del disco y las pérdidas de red según corresponda. Correlaciónelas con la carga de la aplicación; no prescriba los mismos valores de recursos 100m/128Mi para cargas de trabajo distintas.

### Problemas de rendimiento de nodos

En la sesión remota verificada del nodo Linux, recopile observaciones acotadas con las herramientas pertinentes disponibles:

```bash
top -b -n 1
free -m
df -h
df -i
iostat -x 1 5
ip -s link
ss -s
```

No instale herramientas en un contenedor de aplicación de producción solo para ejecutar estos comandos. Use una imagen de diagnóstico preparada o el método compatible de acceso al nodo, y conserve las evidencias antes de cambiar el host.

Añadir nodos ayuda con la capacidad programable, pero no modifica los límites de red/ENI/EBS por nodo. Para cambiar el tipo de instancia, use la ruta de reemplazo/plantilla de lanzamiento compatible con el grupo de nodos; `update-nodegroup-config --launch-template` no es un comando válido. Coordine el cambio con el autoscaler y la ubicación de las cargas de trabajo, en vez de cambiar el tamaño a espaldas del propietario.

#### Ajustes del kernel

Inspeccione los ajustes pertinentes en el espacio de nombres del host o del Pod previsto antes de considerar cambios:

```bash
sysctl net.ipv4.ip_local_port_range net.ipv4.tcp_fin_timeout
sysctl net.core.somaxconn net.ipv4.tcp_max_syn_backlog fs.file-max
```

Muchos sysctl de red tienen ámbito de espacio de nombres. `hostPID: true` por sí solo no coloca un contenedor en el espacio de nombres de red del host; por tanto, un DaemonSet privilegiado puede cambiar un espacio de nombres de red distinto y, al mismo tiempo, modificar ajustes globales del nodo. Use `securityContext.sysctls` de Pod compatibles para los ajustes de espacio de nombres permitidos y la configuración del nodo administrada por su propietario para los ajustes a nivel de nodo. Compruebe la compatibilidad con la política de kernel/Kubernetes, el aislamiento y los efectos antes de modificarlos. Ajustar sysctl arbitrarios con privilegios en todo el clúster no es un diagnóstico de rendimiento.

#### Cambios de rendimiento de EBS

Antes de modificar nada, inspeccione el tipo/IOPS/caudal del volumen real y el ancho de banda EBS de la instancia. Las asignaciones de dispositivos de bloques de EC2 `modify-instance-attribute` no aceptan el tipo de volumen/IOPS/caudal como interfaz de ajuste de EBS; la operación de EBS es `ModifyVolume`. Para el almacenamiento administrado por CSI, use el flujo de trabajo compatible del propietario del almacenamiento y concilie la configuración en lugar de crear discrepancias.

La siguiente **mutación** opcional presupone que el propietario del volumen ha revisado los límites/relaciones compatibles, la capacidad de la instancia, el costo, el estado de la modificación actual y el impacto en la aplicación/los datos:

```bash
set -euo pipefail
: "${AWS_REGION:?}"; : "${VOLUME_ID:?Verify the owned EBS volume}"
: "${TARGET_IOPS:?Set a reviewed supported gp3 IOPS value}"
: "${TARGET_THROUGHPUT:?Set a reviewed supported gp3 MiB/s value}"
: "${EVIDENCE_PARENT:?Set an existing private directory}"
umask 077
EBS_CHANGE_DIR=$(mktemp -d "$EVIDENCE_PARENT/ebs-performance.XXXXXXXX")
aws ec2 describe-volumes --region "$AWS_REGION" --volume-ids "$VOLUME_ID" \
  --output json > "$EBS_CHANGE_DIR/before.json"
# Separate approved volume change; this is not a diagnostic read.
aws ec2 modify-volume --region "$AWS_REGION" --volume-id "$VOLUME_ID" \
  --volume-type gp3 --iops "$TARGET_IOPS" --throughput "$TARGET_THROUGHPUT" \
  --output json > "$EBS_CHANGE_DIR/request.json"
aws ec2 describe-volumes-modifications --region "$AWS_REGION" --volume-ids "$VOLUME_ID" \
  --output json
```

La solicitud es asíncrona. Siga los estados `modifying`, `optimizing`, `completed` o `failed`; la primera respuesta no significa que haya terminado. Tenga en cuenta los límites de frecuencia de modificaciones aplicables y espere a que termine la modificación anterior antes de solicitar otra. Si aumenta la capacidad, la expansión del sistema de archivos debe considerarse por separado. El ejemplo antiguo de 16000 IOPS/1000 MiB/s era ilustrativo de configuración, no un óptimo universal medido; en esta revisión no se ejecutó ningún cambio de EBS.

### Rendimiento de Pods y problemas de memoria

Correlacione el uso/límite por contenedor y los motivos de reinicio/terminación con la carga de solicitudes. `OOMKilled` se encuentra en el estado del contenedor y puede no aparecer como motivo literal de un evento. Un límite de cgroup puede causar OOM aunque el nodo todavía tenga memoria libre. El crecimiento de caché, el comportamiento del asignador de memoria, los picos de carga y los objetos retenidos accesibles requieren investigaciones distintas; la recolección periódica de basura o reiniciar nodos no son soluciones genéricas a una fuga.

Seleccione un perfilador para el runtime/versión reales y conéctelo al proceso previsto mediante un procedimiento revisado. Iniciar `node --inspect` inicia un proceso nuevo, no se conecta automáticamente a la aplicación existente. Los perfiladores de JVM/Python/Go tienen requisitos previos de herramientas, símbolos, código o endpoints. Los volcados de heap pueden pausar las cargas de trabajo, agotar el disco y contener secretos; limite su recopilación y proteja el artefacto. Para este capítulo no se ejecutó ningún perfil ni benchmark.

Ajuste las solicitudes y los límites según los requisitos medidos e incluya la sobrecarga del runtime. Compruebe las cuotas de recursos y quién es el propietario del despliegue y del HPA/VPA. La antiafinidad preferente y la distribución de topología `ScheduleAnyway` son preferencias, no garantías; las reglas estrictas pueden dejar Pods en estado Pending si no hay suficientes nodos elegibles. El escalado de réplicas no necesariamente soluciona un cuello de botella de un solo subproceso, almacenamiento o servicio downstream.

### Problemas de rendimiento de red

Inspeccione las rutas reales de CNI/políticas/SG, el ancho de banda/PPS/límites de conexión de la instancia, la MTU, el comportamiento de DNS y la ubicación del origen/destino. Cambiar la MTU a 9001, habilitar ENA o sustituir una versión de plantilla de lanzamiento no es una solución universal en vivo; siga los requisitos previos de plataforma/estado y un despliegue administrado por su propietario. Auto Mode ya proporciona DNS de nodo y su propia configuración de redes.

Para una prueba programada, prepare imágenes de cliente/servidor compatibles, recursos, ubicación de nodo/AZ y acceso TCP 5201 permitido en un ámbito de prueba aislado. Registre la imagen/versión, la dirección y la topología. Este ejemplo acotado conserva la duración original de 30 segundos y limita la tasa de bits objetivo de un flujo:

```bash
set -euo pipefail
: "${KUBE_CONTEXT:?Set the approved test context}"
: "${TEST_NAMESPACE:?}"; : "${CLIENT_POD:?}"; : "${CLIENT_CONTAINER:?}"
: "${SERVER_IP:?Set the prepared test server IP}"
# Existing prepared test client/server only: one stream, 30 seconds, 10 Mbit/s target.
kubectl --context "$KUBE_CONTEXT" -n "$TEST_NAMESPACE" exec "$CLIENT_POD" \
  -c "$CLIENT_CONTAINER" -- iperf3 -c "$SERVER_IP" -P 1 -t 30 -b 10M -J
```

El objetivo de 10 Mbit/s sirve para regular la prueba; no representa el rendimiento esperado ni demuestra un límite de red. Los flujos múltiples recibirían cada uno ese límite de tasa de bits. Espere a que el servidor/cliente esté listo antes del comando y, después, limpie solo los recursos de prueba preparados. Al medir el tiempo de DNS, distinga entre aciertos de caché, búsqueda upstream y sobrecarga de comandos/exec. No afirme que se midieron el caudal, la latencia ni el éxito de un benchmark de producción sin evidencias reales.

Fuentes: [Sysctl de Kubernetes](https://kubernetes.io/docs/tasks/administer-cluster/sysctl-cluster/), [ModifyVolume de EBS](https://docs.aws.amazon.com/botocore/latest/reference/services/ec2/client/modify_volume.html), [Manual de iperf](https://software.es.net/iperf/invoking.html).

## Problemas de actualización {#upgrade-issues}

### Identifique la operación exacta

Que el estado de un clúster o grupo de nodos sea `ACTIVE` no sustituye el resultado de una solicitud concreta. Registre el ID de actualización, el ámbito de la operación, la versión/configuración prevista, la última etapa satisfactoria y los errores:

```bash
set -euo pipefail
: "${CLUSTER_NAME:?}"; : "${AWS_REGION:?}"; : "${UPDATE_ID:?}"
: "${UPDATE_KIND:?Set control-plane, nodegroup, or addon}"
args=(--name "$CLUSTER_NAME" --region "$AWS_REGION" --update-id "$UPDATE_ID")
case "$UPDATE_KIND" in
  control-plane) ;;
  nodegroup) : "${NODEGROUP_NAME:?}"; args+=(--nodegroup-name "$NODEGROUP_NAME") ;;
  addon) : "${ADDON_NAME:?}"; args+=(--addon-name "$ADDON_NAME") ;;
  *) echo "Invalid UPDATE_KIND" >&2; exit 2 ;;
esac
aws eks describe-update "${args[@]}" --output json --no-cli-pager
```

Para el trabajo en curso, use el sondeo acotado del ID exacto en [Actualizaciones de EKS](./08-eks-upgrades.md). Solo `Successful` indica éxito; los estados de error, cancelación o desconocidos, así como los errores de consulta, requieren investigación. Un tiempo de espera agotado localmente no cancela una operación de AWS.

### Plano de control y compatibilidad de API

```bash
set -euo pipefail
: "${CLUSTER_NAME:?}"; : "${AWS_REGION:?}"; : "${TARGET_VERSION:?}"
FILTER=$(jq -n --arg target "$TARGET_VERSION" \
  '{categories:["UPGRADE_READINESS"],kubernetesVersions:[$target]}')
aws eks list-insights --cluster-name "$CLUSTER_NAME" --region "$AWS_REGION" \
  --filter "$FILTER" --output json
aws eks describe-addon-versions --kubernetes-version "$TARGET_VERSION" --region "$AWS_REGION" \
  --output json
```

El catálogo de complementos no es el catálogo de versiones del clúster. Elija la siguiente versión menor de EKS compatible a partir del catálogo del clúster y de la versión actual real; no deduzca la compatibilidad de EKS a partir de una versión upstream. Como preparación conservadora, alinee los nodos con la versión actual del plano de control y distinga esto del límite de desfase compatible. Algunos complementos requieren versiones intermedias antes del cambio del plano de control.

Inspeccione los manifiestos/metadatos Helm originales, los clientes de API del runtime, los insights de actualización y los webhooks de admisión/conversión. Las listas de imágenes de contenedores o la representación `.apiVersion` de los objetos devueltos actualmente no demuestran que los clientes ya no usen una API retirada. Use la guía de migración y los comandos Pluto verificados del capítulo de actualización de origen; `kubectl convert` es un complemento independiente, no una herramienta integrada universal de migración/prueba.

En la guía actual de EKS, se ha revertido temporalmente la aplicación de `--force` para los insights de actualización normales; esto es distinto de las condiciones bloqueantes de `ROLLBACK_READINESS`. No vuelva a enviar una actualización solo porque un comando anterior agotó el tiempo de espera ni presuponga que se puede cancelar una actualización normal del plano de control una vez iniciada.

### Recuperación de grupos de nodos y complementos

Inspeccione las interrupciones permitidas por los PDB, las réplicas/preparación, la capacidad de IP/EC2 de reemplazo, la AMI/inicialización y los errores reales de actualización de nodos administrados. `kubectl drain --force` permite quitar Pods no administrados; **no** omite las comprobaciones de expulsión de PDB. `--disable-eviction` y una actualización forzada de nodos administrados tienen semánticas disruptivas distintas. No establezca `minAvailable: 0` ni descarte datos de `emptyDir` solo para eliminar un error.

Para una AMI optimizada para EKS, revise tanto la versión de Kubernetes como la versión de la AMI. Un grupo que use una AMI personalizada requiere una nueva versión revisada de su plantilla de lanzamiento original con la API/opciones correctas. Una actualización fallida no garantiza la reversión automática de la flota. Use la sección actual de nodos/Pods y el procedimiento de actualización por etapas en vez de crear y eliminar grupos de inmediato.

Para los complementos, conserve la versión/configuración/esquema, IAM/Pod Identity y propietario. `PRESERVE` no garantiza una combinación completa de configuración ni el funcionamiento; `OVERWRITE` puede descartar personalizaciones. Eliminar y volver a crear un complemento de red/almacenamiento puede interrumpir la limpieza dependiente y el acceso de las cargas de trabajo. Una carga genérica `{"key":"value"}` o un manifiesto de VPC CNI etiquetado erróneamente como CoreDNS no son una reparación válida.

### La reversión es una decisión independiente

Actualmente, EKS admite, bajo ciertas condiciones, volver a la versión menor inmediatamente anterior durante los siete días posteriores a una actualización in situ completada. Siguen aplicándose la elegibilidad, la política de soporte, los requisitos previos de funciones, el orden de tipos de cómputo y `ROLLBACK_READINESS`. La reversión de nodos administrados precede a la del plano de control; Auto Mode coordina primero los nodos. Sus reglas de tiempo de espera/cancelación/interrupción difieren de las de una actualización normal.

`--force` omite los insights de reversión, no la validación de requisitos previos ni los controles de interrupción de Auto Mode. La reversión de versión conserva el estado de las cargas de trabajo/datos en vez de restaurar una copia de seguridad y no revierte automáticamente los complementos. Para Fargate, nodos híbridos/personalizados, la política de soporte y las condiciones de recuperación, use el [procedimiento completo de reversión](./08-eks-upgrades.md); una reversión de Git/CloudFormation no es la operación del servicio.

Fuentes: [Actualizaciones de EKS](https://docs.aws.amazon.com/eks/latest/userguide/update-cluster.html), [Actualizaciones de nodos administrados](https://docs.aws.amazon.com/eks/latest/userguide/update-managed-node-group.html), [Reversión de EKS](https://docs.aws.amazon.com/eks/latest/userguide/rollback-cluster.html), [Reversión de Auto Mode](https://docs.aws.amazon.com/eks/latest/userguide/rollback-automode.html).

## Mensajes de error comunes y soluciones {#common-error-messages-and-solutions}

Son mensajes o patrones ilustrativos; no se afirma que todos los controladores actuales emitan exactamente la misma cadena. Use el código de error, el UID del recurso, el ID de solicitud y las condiciones reales. Una causa propuesta sigue siendo una hipótesis hasta que haya evidencias que la respalden.

| Mensaje / patrón | Evidencia y próximo paso apropiado |
| --- | --- |
| `UnsupportedAvailabilityZoneException` | Una subred/AZ seleccionada para el clúster no es compatible con EKS en la cuenta; compruebe las AZ compatibles en el error en vez de limitarse a las ofertas de instancias EC2 |
| `ResourceLimitExceeded` / error de cuota | Identifique el servicio/cuota específicos y el límite aplicado actual; el mensaje histórico «límite 5» no es un límite actual |
| `InvalidParameterException: Error in role params` | Compruebe que el rol exista, la confianza, `iam:PassRole` del solicitante, los permisos requeridos y la solicitud exacta; no cree a ciegas un nuevo rol compartido |
| `ClusterUnreachable` | Compruebe DNS del endpoint, rutas, SG/NACL y TLS; regenerar kubeconfig por sí solo no repara el transporte |
| `You must be logged in ... (Unauthorized)` / `the server has asked for the client to provide credentials` | Compruebe el proveedor de credenciales, el rol/perfil, la autenticación exec y el modo de autenticación/entrada de acceso del clúster o la asignación heredada |
| `Forbidden` | Compruebe el sujeto autenticado, el verbo/recurso/subrecurso/espacio de nombres y todas las concesiones aplicables; distinga los fallos de suplantación |
| `error loading ... .kube/config ... permission denied` | Compruebe el archivo seleccionado, el propietario y los permisos del directorio principal; el modo 600 solo ayuda si la propiedad/ruta son correctas |
| `dial tcp: lookup ... no such host` | Resuelva el nombre de host del endpoint e inspeccione el resolvedor/ruta privada reales; no pase la URL HTTPS completa a una consulta DNS |
| `FailedScheduling ... Insufficient memory` | Compare las solicitudes/sobrecarga y la capacidad asignable de los nodos elegibles, la ubicación y la cuota; los datos actuales de memoria libre/top por sí solos no representan el cálculo del scheduler |
| `Insufficient pods` | Compruebe las ranuras de Pods asignables del nodo y la asignación actual; reducir las solicitudes de memoria no crea ranuras para Pods |
| `CrashLoopBackOff` | Inspeccione el estado de terminación actual y anterior del contenedor/contenedor de inicialización, los registros de la instancia anterior, la configuración y las sondas |
| `ImagePullBackOff` | Lea el error de descarga relativo a la imagen/digest/plataforma, la ruta/TLS/límite de frecuencia del registro desde el nodo y la identidad real de descarga; nunca exponga credenciales para depurarlo |
| `Evicted` | Lea el motivo/mensaje del Pod y la presión/cronología del nodo; use la ruta de recuperación de datos/disponibilidad correspondiente |
| `FailedCreateServiceEndpoints` / error de actualización de EndpointSlice | Inspeccione el selector/tipo del Service, el estado Ready/las condiciones de endpoint del Pod, los puertos con nombre y los eventos del controlador |
| `EniLimitExceeded` / error de asignación de IPAM | Compruebe las restricciones reales de ENI/IP/subred/prefijos y el contexto de cuota/error; las redes con prefijos/personalizadas no eliminan todos los límites |
| `FailedLoadBalancerCreation` / error de aprovisionamiento del controlador | Inspeccione la propiedad del controlador exacto, la selección de subredes, IAM, el estado de los destinos y la ruta de SG; no etiquete todas las subredes ni abra todo el tráfico |
| `FailedAttachVolume: Multi-Attach ...` | Determine los consumidores reales y el estado de conexión/aislamiento; coordine el desmontaje/desacoplamiento de CSI y la seguridad de los datos en vez de forzar la desconexión |
| `FailedMount ... timeout ...` | Compruebe el controlador/el complemento de nodo CSI, la identidad/KMS, la topología, el sistema de archivos y los eventos de conexión; reiniciar el nodo no es una solución automática |
| `PersistentVolumeClaim is not bound` | Distinga la vinculación diferida esperada de los problemas de clase/provisionador/identidad/programación del consumidor; no elimine el claim |
| `Failed to list *v1.Pod: Unauthorized` | Identifique el endpoint/solicitante que rechaza la solicitud y el token/identidad; reiniciar Metrics Server no restaura las credenciales que faltan |
| `Failed to scrape node` | Inspeccione la ruta de scraping de kubelet autenticada, los certificados, la dirección/puerto, las redes y el estado del nodo |
| `Failed to list *v1.Pod: the server could not find the requested resource` | Verifique la URL/contexto de API, la detección y la respuesta del cliente/proxy antes de atribuirlo a la configuración del plano de control de EKS |

Use la sección pertinente para recopilar evidencias acotadas y elegir una corrección con un responsable definido. Conserve los resultados y las suposiciones pendientes; ninguno de estos mensajes de ejemplo demuestra un diagnóstico ni una recuperación probada.

## Cuestionario

Compruebe lo que sabe con el [cuestionario del tema](../quizzes/eks/09-eks-troubleshooting-quiz.md).
