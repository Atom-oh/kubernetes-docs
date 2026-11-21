# Laboratorio de migración de IAM para cargas de trabajo de EKS: del rol del nodo a IRSA y Pod Identity

> **Dificultad**: Avanzado
> **Tiempo estimado**: 40–60 minutos (unos 30 minutos más con `harden`)
> **Versiones compatibles**: Verificado en Amazon EKS 1.36 y AWS CLI 2.35.11 (dentro de los Pods)
> **Última actualización**: 21 de noviembre de 2026

## Objetivos de aprendizaje

- Empieza con tres copias de la misma aplicación de pedidos, todas con el rol de IAM del nodo; luego migra una copia a IRSA y otra a EKS Pod Identity.
- Comprueba por ti mismo en qué se diferencian las variables de entorno inyectadas, los tokens y las políticas de confianza de roles entre ambos métodos.
- Revoca el permiso de S3 del rol del nodo, observa cómo se deniega el acceso solo al Pod que aún no se ha migrado y comprueba la coherencia eventual de IAM y de las asociaciones.
- (Opcional) Reduce a 1 el límite de saltos de IMDS para cerrar la ruta de credenciales del nodo a los Pods normales.
- Usa una simulación en el servidor para comprobar qué recibe un Pod nuevo cuando una ServiceAccount tiene tanto una anotación de IRSA como una asociación de Pod Identity.

Este laboratorio recorre paso a paso la [demostración en directo](../../security/17-eks-workload-identity-migration.md#live-demo) de [Migrar los permisos de IAM del nodo de EKS a IRSA y Pod Identity](../../security/17-eks-workload-identity-migration.md). Lee primero las secciones del cuaderno de trabajo sobre el [flujo de IRSA](../../security/17-eks-workload-identity-migration.md#irsa-flow) y el [flujo de Pod Identity](../../security/17-eks-workload-identity-migration.md#pod-identity-flow).

## Tiempo y costo

| Paso | Tiempo medido | Notas |
| --- | --- | --- |
| `up` | 174 s (ejecución `t1121`) | Principalmente la creación del grupo de nodos; de 3 a 5 min según el entorno |
| `migrate-irsa` | 6 s | |
| `migrate-podid` | 11 s | Incluye 5 s hasta que la asociación llegó a la admisión |
| `diff` | 8 s | Solo lectura |
| `revoke` | 13 s hasta el primer `denied` | El comando termina después de 17–18 s |
| `harden` (opcional) | 878 s | Sustitución gradual del grupo de nodos |
| `restore` | 15 s; 578 s después de `harden` | Para repetir la práctica |
| `down` | 323 s (ejecución `t1121`) | Principalmente la eliminación del grupo de nodos |

El costo corresponde principalmente a una instancia t3.medium bajo demanda (0,052 USD por hora en Seúl) y un volumen gp3 de 20 GiB. Una hora de laboratorio cuesta unos 0,06 USD; las solicitudes a S3 y las llamadas a la API son insignificantes. La página de demostración pública opcional añade unos 0,55 USD al día por el ALB. Limpia siempre los recursos con `down` cuando termines.

## Requisitos previos

- [ ] **Un clúster de EKS existente** (verificado en la versión 1.36). La demostración principal no crea ningún clúster, VPC, subred ni grupo de seguridad (solo el `page-up` opcional crea un grupo de seguridad para el ALB interno y registros DNS para `PAGE_DOMAIN`). Da por supuesto el entorno habitual, en el que vpc-cni del clúster se ejecuta con el rol del nodo.
- [ ] Está instalado el complemento **`eks-pod-identity-agent`**. El script solo comprueba que exista; no lo instala.
- [ ] El emisor del clúster está registrado como **proveedor de OIDC de IAM**. El script tampoco lo crea.
- [ ] **Subredes privadas** en la VPC del clúster y sus etiquetas Name. Solo se aceptan las subredes con `MapPublicIpOnLaunch=false`; los nodos obtienen `public.ecr.aws/aws-cli/aws-cli` a través de la ruta NAT existente de la VPC.
- [ ] Herramientas: AWS CLI v2, kubectl, jq, bash y git.
- [ ] Permisos: credenciales con permisos de EKS, EC2 (plantillas de lanzamiento), IAM y S3, además de acceso de administrador del clúster. Usa credenciales temporales en lugar de claves de acceso de larga duración.

### Comandos de comprobación previa

```bash
export AWS_REGION=ap-northeast-2
export CLUSTER=<CLUSTER> VPC_NAME=<Name tag of the cluster VPC> \
  SUBNET_NAMES=<private subnet Name tag 1>,<private subnet Name tag 2>

aws sts get-caller-identity --query Arn --output text
aws eks describe-addon --cluster-name "$CLUSTER" --addon-name eks-pod-identity-agent \
  --query addon.status --output text                       # ACTIVE
ISSUER=$(aws eks describe-cluster --name "$CLUSTER" \
  --query cluster.identity.oidc.issuer --output text | sed 's#^https://##')
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
aws iam get-open-id-connect-provider --open-id-connect-provider-arn \
  "arn:aws:iam::${ACCOUNT_ID}:oidc-provider/${ISSUER}" --query ClientIDList   # ["sts.amazonaws.com"]
VPC_ID=$(aws ec2 describe-vpcs --filters "Name=tag:Name,Values=$VPC_NAME" \
  --query 'Vpcs[0].VpcId' --output text)
aws eks describe-cluster --name "$CLUSTER" --query cluster.resourcesVpcConfig.vpcId --output text  # must equal $VPC_ID
aws ec2 describe-subnets --filters "Name=vpc-id,Values=$VPC_ID" "Name=tag:Name,Values=$SUBNET_NAMES" \
  --query 'Subnets[].[Tags[?Key==`Name`]|[0].Value,SubnetId,MapPublicIpOnLaunch]' --output table
```

Comprueba que el complemento esté en estado `ACTIVE`, que la consulta al proveedor de OIDC funcione, que el ID de la VPC del clúster coincida con la VPC encontrada mediante `VPC_NAME` y que todas las subredes muestren `MapPublicIpOnLaunch` como `False`. Si alguna de estas comprobaciones falla, `up` se detiene antes de crear nada.

### Código y archivo de entorno

```bash
git clone https://github.com/Atom-oh/kubernetes-docs.git
cd kubernetes-docs/examples/security/eks-workload-identity

STATE_DIR="${XDG_STATE_HOME:-$HOME/.local/state}/eks-workload-identity-demo"
mkdir -p "$STATE_DIR"
cat > "$STATE_DIR/env" <<'EOF'
export AWS_REGION=ap-northeast-2
export CLUSTER=<CLUSTER>
export VPC_NAME=<Name tag of the cluster VPC>
export SUBNET_NAMES=<private subnet Name tag 1>,<private subnet Name tag 2>
EOF

export RUN_ID=lab01     # 4–12 lowercase letters or digits; goes into resource names wid-<RUN_ID>-*
export NS="wid-$RUN_ID"
export KUBECONFIG="$STATE_DIR/kubeconfig-$RUN_ID"   # the dedicated kubeconfig demo.sh writes
```

`demo.sh` carga este archivo de entorno en cada ejecución, así que `watch`, en el segundo terminal, usa los mismos valores. El archivo se carga después de las variables del shell, por lo que el valor del archivo prevalece sobre el de una variable del shell con el mismo nombre. Cuando ejecutes `kubectl` directamente más abajo, usa el `KUBECONFIG` anterior para asegurarte de que los comandos no puedan acceder al contexto de otro clúster. El archivo aparece la primera vez que ejecutas `up`.

Los comandos y resultados que imprime el script enmascaran el ID de cuenta, el ID del emisor de OIDC, el nombre del clúster y los ID de las plantillas de lanzamiento como `<ACCOUNT_ID>`, `<OIDC_ID>`, `<CLUSTER>` y `<LAUNCH_TEMPLATE_ID>`. Los resultados esperados que aparecen a continuación están enmascarados del mismo modo. Provienen de ensayos realizados en la región de Seúl el 21 de noviembre de 2026; cada bloque indica el ID de ejecución (`d1124` o `t1121`). En tu pantalla aparecerán tu propio `RUN_ID` y tus propias marcas de tiempo.

## Paso 0: Implementar el entorno del laboratorio (`up`)

**Comando** (terminal A)

```bash
./demo.sh up "$RUN_ID"
```

**Resultado esperado** (medido, ejecución `t1121`, 174 s)

```text
==> bucket and test object
==> node role (with the app's S3 permission, the legacy pattern)
==> IRSA and Pod Identity roles
==> creating node group wid-t1121 (3–5 min)
==> namespace, ServiceAccounts and three copies of the orders app
Waiting for deployment "orders-legacy" rollout to finish: 0 of 1 updated replicas are available...
deployment "orders-legacy" successfully rolled out
deployment "orders-irsa" successfully rolled out
deployment "orders-podid" successfully rolled out
==> ready. In a second terminal run: ./demo.sh watch t1121
```

**Qué debes comprobar**

```bash
./demo.sh status "$RUN_ID"
aws ec2 describe-launch-template-versions --launch-template-name "wid-$RUN_ID-node" --versions '$Latest' \
  --query 'LaunchTemplateVersions[0].LaunchTemplateData.MetadataOptions'
```

- `status` debería mostrar el grupo de nodos como `ACTIVE t3.medium lt-version=1`, la política insertada `OrdersReadInvoices` en los tres roles (`wid-<RUN_ID>-node`, `-irsa`, `-podid`), el bucket como `present`, `pod-id 0 association(s)`, `irsa SA (not annotated)` y los tres Pods como `Running`.
- `MetadataOptions` de la plantilla de lanzamiento son `HttpTokens: required`, `HttpPutResponseHopLimit: 2` y `HttpEndpoint: enabled`.

**Por qué.** `up` crea el mismo punto de partida que un grupo de nodos de producción. IMDSv2 es obligatorio, pero con un límite de saltos de 2 un Pod normal sin red del host aún puede obtener un token de IMDS y las credenciales del rol del nodo; ese rol tiene el permiso `s3:GetObject` de la aplicación. Los roles de IRSA y Pod Identity se crean de antemano, pero todavía no están vinculados a ninguna ServiceAccount.

## Paso 1: Comprobar el estado inicial (`watch`)

**Comando** (terminal B, mismo directorio)

```bash
export RUN_ID=lab01
./demo.sh watch "$RUN_ID"     # refreshes every 2 s; Ctrl-C to stop
```

**Pantalla esperada** (medida, ejecución `d1124`)

```text
04:11:37 EKS workload identity — <CLUSTER>/wid-d1124  (Ctrl-C to stop)

COPY            CREDENTIALS    ROLE                           S3        AT
orders-legacy   node (IMDS)    wid-d1124-node  ← node       allowed   04:11:36
orders-irsa     node (IMDS)    wid-d1124-node  ← node       allowed   04:11:35
orders-podid    node (IMDS)    wid-d1124-node  ← node       allowed   04:11:36

node role: wid-d1124-node   bucket object: invoices/2026-11.txt
```

**Qué debes comprobar.** Las tres filas muestran `node (IMDS)`, `wid-<RUN_ID>-node ← node` y `allowed`; la hora de `AT` cambia cada 3 segundos. La pantalla se genera a partir de la línea de registro más reciente del Pod más reciente de cada copia. Puedes leer el JSON sin procesar desde el terminal A:

```bash
kubectl -n "$NS" logs deploy/orders-legacy --tail=3
# format: {"t":"HH:MM:SS","src":"imds","role":"wid-<RUN_ID>-node","s3":"allowed"}
```

**Por qué.** Ninguno de los tres Pods tiene variables de credenciales inyectadas, así que la cadena de proveedores predeterminada de AWS CLI llega hasta el último paso, IMDS, y obtiene el rol del nodo. `app.sh` establece `src` según si está presente `AWS_WEB_IDENTITY_TOKEN_FILE` o `AWS_CONTAINER_CREDENTIALS_FULL_URI`, y obtiene el nombre del rol del ARN de `sts get-caller-identity`. No imprime tokens ni claves.

## Paso 2: Migrar a IRSA (`migrate-irsa`)

**Comando** (terminal A)

```bash
./demo.sh migrate-irsa "$RUN_ID"
```

**Resultado esperado** (medido, ejecución `t1121`, 6 s)

```text
==> IRSA: point the ServiceAccount at its own role, then restart the copy
$ kubectl -n wid-t1121 annotate serviceaccount orders-irsa --overwrite eks.amazonaws.com/role-arn=arn:aws:iam::<ACCOUNT_ID>:role/wid-t1121-irsa
$ kubectl -n wid-t1121 rollout restart deployment/orders-irsa
$ kubectl -n wid-t1121 rollout status deployment/orders-irsa --timeout=180s
Waiting for deployment "orders-irsa" rollout to finish: 1 old replicas are pending termination...
deployment "orders-irsa" successfully rolled out
```

En el terminal B, la fila `orders-irsa` cambia a `IRSA (STS)`, `wid-<RUN_ID>-irsa` y `allowed`; las otras dos filas no cambian (medido, ejecución `d1124`).

```text
orders-legacy   node (IMDS)    wid-d1124-node  ← node       allowed   04:11:59
orders-irsa     IRSA (STS)     wid-d1124-irsa                 allowed   04:12:01
orders-podid    node (IMDS)    wid-d1124-node  ← node       allowed   04:12:00
```

**Compruébalo tú mismo.** Observa qué ha cambiado en los objetos de Kubernetes.

```bash
# 1) The ServiceAccount annotation
kubectl -n "$NS" get sa orders-irsa \
  -o jsonpath='{.metadata.annotations.eks\.amazonaws\.com/role-arn}{"\n"}'

# 2) Names of the environment variables the webhook added to the new Pod (no values)
POD=$(kubectl -n "$NS" get pod -l app=orders,track=irsa \
  --sort-by=.metadata.creationTimestamp -o jsonpath='{.items[-1:].metadata.name}')
kubectl -n "$NS" get pod "$POD" \
  -o jsonpath='{range .spec.containers[0].env[*]}{.name}{"\n"}{end}'

# 3) The projected token mount path
kubectl -n "$NS" get pod "$POD" \
  -o jsonpath='{range .spec.containers[0].volumeMounts[*]}{.mountPath}{"\n"}{end}'
```

**Qué debes comprobar**

- La anotación es `arn:aws:iam::<ACCOUNT_ID>:role/wid-<RUN_ID>-irsa`.
- Junto a las variables propias del manifiesto, como `BUCKET`, `KEY`, `AWS_REGION` y otras, la lista de variables muestra `AWS_STS_REGIONAL_ENDPOINTS`, `AWS_ROLE_ARN` y `AWS_WEB_IDENTITY_TOKEN_FILE`, añadidas por el webhook.
- Las rutas de montaje ahora incluyen `/var/run/secrets/eks.amazonaws.com/serviceaccount`.
- Los Pods `orders-legacy` y `orders-podid` no tienen estas variables.

**Por qué.** El webhook de mutación de EKS lee la anotación `eks.amazonaws.com/role-arn` de la ServiceAccount **cuando se crea un Pod** y añade las variables y el volumen del token. Los Pods en ejecución no cambian, así que el script ejecuta `rollout restart` justo después de añadir la anotación. En el Pod nuevo, AWS CLI encuentra el proveedor de tokens de identidad web, que aparece antes que IMDS en la cadena, y obtiene el rol de IRSA a través de STS `AssumeRoleWithWebIdentity`.

## Paso 3: Migrar a Pod Identity (`migrate-podid`)

**Comando** (terminal A)

```bash
./demo.sh migrate-podid "$RUN_ID"
```

**Resultado esperado** (medido, ejecución `t1121`, 11 s)

```text
==> Pod Identity: associate the ServiceAccount with its role in the EKS API, then restart
$ aws eks create-pod-identity-association --cluster-name <CLUSTER> --namespace wid-t1121 --service-account orders-podid --role-arn arn:aws:iam::<ACCOUNT_ID>:role/wid-t1121-podid --tags Lab=eks-workload-identity-demo\,LabRun=t1121 --query association.associationId --output text
==> waiting for the association change to reach Pod admission (eventually consistent)
    2s  not yet   injected after 5s
$ kubectl -n wid-t1121 rollout restart deployment/orders-podid
$ kubectl -n wid-t1121 rollout status deployment/orders-podid --timeout=180s
Waiting for deployment "orders-podid" rollout to finish: 1 old replicas are pending termination...
deployment "orders-podid" successfully rolled out
```

En el terminal B, la fila `orders-podid` cambia a `Pod Identity`, `wid-<RUN_ID>-podid` y `allowed` (medido, ejecución `d1124`).

```text
orders-legacy   node (IMDS)    wid-d1124-node  ← node       allowed   04:12:27
orders-irsa     IRSA (STS)     wid-d1124-irsa                 allowed   04:12:29
orders-podid    Pod Identity   wid-d1124-podid                allowed   04:12:27
```

**Compruébalo tú mismo**

```bash
# The association lives in the EKS API; the ServiceAccount has no annotation
aws eks list-pod-identity-associations --cluster-name "$CLUSTER" --namespace "$NS" \
  --query 'associations[].[serviceAccount,associationId]' --output text
kubectl -n "$NS" get sa orders-podid -o jsonpath='{.metadata.annotations}{"\n"}'

POD=$(kubectl -n "$NS" get pod -l app=orders,track=podid \
  --sort-by=.metadata.creationTimestamp -o jsonpath='{.items[-1:].metadata.name}')
kubectl -n "$NS" get pod "$POD" \
  -o jsonpath='{range .spec.containers[0].env[*]}{.name}{"\n"}{end}'
```

**Qué debes comprobar**

- Hay una asociación para `orders-podid` y las anotaciones de la ServiceAccount están vacías.
- El Pod nuevo tiene `AWS_STS_REGIONAL_ENDPOINTS`, `AWS_CONTAINER_CREDENTIALS_FULL_URI` y `AWS_CONTAINER_AUTHORIZATION_TOKEN_FILE`.
- `injected after Ns` en el resultado es el tiempo transcurrido desde la creación de la asociación hasta que la admisión la inyectó. En ambos ensayos fueron 5 s.

**Por qué hay que esperar a que se inyecte.** Las asociaciones tienen coherencia eventual. En el primer ensayo, un rollout justo después de crear la asociación produjo un Pod sin las variables de Pod Identity, y ese Pod siguió usando el rol del nodo. Por eso el script envía la plantilla de Pod del Deployment a través de `kubectl create --dry-run=server` y solo inicia el rollout cuando el webhook de mutación inyecta realmente las variables. Una simulación en el servidor no guarda nada, pero pasa por los mismos pasos de admisión que un Pod real, que es justo lo que necesita esta comprobación.

## Paso 4: Comparar los dos métodos (`diff`)

**Comando**

```bash
./demo.sh diff "$RUN_ID"
```

**Resultado esperado** (medido, ejecución `t1121`)

```text
1. What EKS injected into each new Pod (env var names)
  irsa   AWS_STS_REGIONAL_ENDPOINTS, AWS_ROLE_ARN, AWS_WEB_IDENTITY_TOKEN_FILE
  podid  AWS_STS_REGIONAL_ENDPOINTS, AWS_CONTAINER_CREDENTIALS_FULL_URI, AWS_CONTAINER_AUTHORIZATION_TOKEN_FILE

2. The projected ServiceAccount token (claims only)
  irsa   {"iss":"https://oidc.eks.ap-northeast-2.amazonaws.com/id/<OIDC_ID>","aud":["sts.amazonaws.com"],"sub":"system:serviceaccount:wid-t1121:orders-irsa","lifetime_s":86400}
  podid  {"iss":"https://oidc.eks.ap-northeast-2.amazonaws.com/id/<OIDC_ID>","aud":["pods.eks.amazonaws.com"],"sub":"system:serviceaccount:wid-t1121:orders-podid","lifetime_s":79636}

3. Who each role trusts
  irsa             {"principal":{"Federated":"arn:aws:iam::<ACCOUNT_ID>:oidc-provider/oidc.eks.ap-northeast-2.amazonaws.com/id/<OIDC_ID>"},"action":"sts:AssumeRoleWithWebIdentity","conditions":["<issuer>:aud","<issuer>:sub"]}
  podid            {"principal":{"Service":"pods.eks.amazonaws.com"},"action":["sts:AssumeRole","sts:TagSession"],"conditions":["aws:RequestTag/eks-cluster-arn","aws:RequestTag/kubernetes-namespace","aws:RequestTag/kubernetes-service-account"]}

4. Where the SDK goes for credentials
  irsa   Pod → STS AssumeRoleWithWebIdentity (regional endpoint) → temporary credentials
  podid  Pod → Pod Identity Agent 169.254.170.23 on the node → EKS Auth AssumeRoleForPodIdentity → credentials
  legacy Pod → IMDSv2 169.254.169.254 → node role credentials

5. Wiring lives in
  irsa   ServiceAccount annotation + IAM OIDC provider + per-role trust on issuer/sub
  podid  EKS association (1 found) + one service principal trust, reusable across clusters
```

**Cómo interpretar el resultado**

- **1**: Ambos métodos añaden variables al Pod nuevo, pero con nombres distintos. IRSA pasa el ARN del rol y un archivo de token, y el SDK llama a STS directamente. Pod Identity no pasa ningún ARN de rol: solo una URI de credenciales y un archivo de token de autorización; la asociación determina qué rol recibe el Pod.
- **2**: Ambos tokens son tokens de ServiceAccount firmados por el mismo emisor del clúster, con `sub` en el mismo formato. La diferencia está en `aud`: STS solo acepta un token `sts.amazonaws.com` y EKS Auth solo acepta uno `pods.eks.amazonaws.com`. La duración del token de Pod Identity varía entre ejecuciones porque el webhook añade una fluctuación aleatoria (se midieron 79.636 s y 86.171 s).
- **3**: El rol de IRSA confía en un proveedor de OIDC por clúster con condiciones `aud` y `sub`, por lo que su política de confianza crece con cada clúster. El rol de Pod Identity confía en una entidad de servicio con condiciones de etiquetas de sesión, así que no requiere cambios en la política de confianza al usarlo en otro clúster.
- **4–5** son texto de resumen fijo que imprime el script. Solo `1 found` en el punto 5 es un recuento real de asociaciones.

**Por qué.** La diferencia entre los dos métodos es quién toma el token y lo convierte en un rol. Con IRSA, el Pod va directamente a STS y STS verifica la firma a través del proveedor de OIDC. Con Pod Identity, el Agent del mismo nodo consulta a EKS Auth, que encuentra la asociación y devuelve credenciales con etiquetas de sesión.

## Paso 5: Revocar el permiso del rol del nodo (`revoke`)

**Comando**

```bash
./demo.sh revoke "$RUN_ID"
```

**Resultado esperado** (medido, ejecución `t1121`, 13 s hasta el primer `denied`)

```text
==> remove the app's S3 permission from the node role
$ aws iam delete-role-policy --role-name wid-t1121-node --policy-name OrdersReadInvoices
==> waiting for IAM to propagate: legacy copy should flip to denied
    1s  legacy still: allowed     5s  legacy still: allowed     9s  legacy still: allowed   legacy denied after 13s
  orders-irsa   allowed via wid-t1121-irsa
  orders-podid  allowed via wid-t1121-podid
```

Terminal B (medido, ejecución `d1124`; inmediatamente después de `revoke` y 60 s más tarde):

```text
orders-legacy   node (IMDS)    wid-d1124-node  ← node       denied    04:12:56
orders-irsa     IRSA (STS)     wid-d1124-irsa                 allowed   04:12:58
orders-podid    Pod Identity   wid-d1124-podid                allowed   04:12:58
```

**Qué debes comprobar**

- Solo `orders-legacy` pasa a `denied`, y su rol sigue siendo el rol del nodo: aún obtiene credenciales, pero ese rol ya no tiene el permiso.
- Las copias IRSA y Pod Identity siguen en `allowed`, lo que demuestra que ya no dependen del permiso de la aplicación del rol del nodo.
- Comprueba si aparecen lecturas `allowed` tardías durante los siguientes minutos.

```bash
kubectl -n "$NS" logs deploy/orders-legacy --since=10m | jq -r 'select(.s3=="allowed") | .t' | tail -n 3
```

**Por qué.** Los cambios en las políticas de IAM se propagan con coherencia eventual. En ambos ensayos, la primera denegación apareció después de 13 s, pero en el primero aparecieron dos lecturas `allowed` más unos 4,5 minutos después. `revoke` termina con el primer `denied`, así que en producción sigue observando durante varios minutos después de quitar una política del nodo antes de tomar una decisión.

## Paso 6 (opcional): Cerrar la ruta de IMDS (`harden`)

Esto tarda unos 15 minutos (878 s medidos), así que puedes iniciarlo justo después de `revoke` y continuar con el paso 7.

**Comando**

```bash
./demo.sh harden "$RUN_ID"
./demo.sh status "$RUN_ID"      # in another terminal: nodegroup UPDATING → ACTIVE
```

**Resultado esperado** (medido, ejecución `d1124`, 878 s). El script actualiza el grupo de nodos a una nueva versión de la plantilla de lanzamiento e imprime un punto cada 15 s hasta que termina.

```text
==> block Pod access to IMDS on the demo node group (hop limit 1)
$ aws eks update-nodegroup-version --cluster-name <CLUSTER> --nodegroup-name wid-d1124 --launch-template id=<LAUNCH_TEMPLATE_ID>\,version=2 --query update.id --output text
...
deployment "orders-legacy" successfully rolled out
==> legacy copy now has no credentials at all; IRSA and Pod Identity are unaffected
```

La última línea de registro de cada copia tras la sustitución (medida, ejecución `d1124`):

```text
legacy: {"t":"04:00:27","src":"imds","role":"no-credentials","s3":"no-creds"}
irsa: {"t":"04:00:26","src":"irsa","role":"wid-d1124-irsa","s3":"allowed"}
podid: {"t":"04:00:27","src":"pod-identity","role":"wid-d1124-podid","s3":"allowed"}
```

**Qué debes comprobar**

```bash
aws ec2 describe-launch-template-versions --launch-template-name "wid-$RUN_ID-node" --versions '$Latest' \
  --query 'LaunchTemplateVersions[0].LaunchTemplateData.MetadataOptions'
```

- `HttpPutResponseHopLimit` es `1` y `HttpEndpoint` sigue siendo `enabled`.
- `orders-legacy` no obtiene ninguna credencial (`no-credentials` / `no-creds`); las otras dos copias siguen en `allowed` en el nodo nuevo.

**Por qué.** Con un límite de saltos de 1, la respuesta del token IMDSv2 no puede atravesar el espacio de nombres de red del nodo hasta el Pod, por lo que un Pod normal no puede obtener las credenciales del rol del nodo. **No desactives IMDS (`HttpEndpoint=disabled`).** El Pod Identity Agent se ejecuta en la red del host y obtiene las credenciales del rol del nodo desde IMDS para llamar a EKS Auth; si IMDS está desactivado, `orders-podid` también perdería sus credenciales. Los Pods con `hostNetwork` pueden acceder a IMDS independientemente del límite de saltos, así que contrólalos por separado.

Antes de ejecutar `restore` o `down` después de `harden`, espera a que el grupo de nodos vuelva a estar en estado `ACTIVE`. `restore`, después de `harden`, revierte el límite de saltos a 2 y tarda unos 10 minutos (578 s medidos).

## Paso 7: Experimentar: anotación de IRSA y asociación a la vez

El cuaderno de trabajo indica que, cuando una ServiceAccount tiene tanto una anotación de IRSA como una asociación, el webhook de EKS solo inyecta las variables de Pod Identity en los Pods nuevos. Compruébalo tú mismo después del paso 3. No crees una asociación para `orders-irsa`: los comandos `restore` y `down` del script solo eliminan la asociación de `orders-podid`, así que la otra quedaría sin eliminar. En su lugar, añade brevemente una anotación de IRSA a `orders-podid`, que ya tiene la asociación.

**7.1 Una función que muestra el resultado de la inyección** — envía la plantilla de Pod del Deployment a una simulación en el servidor, igual que `podid_injected()` en `demo.sh`.

```bash
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

injected() { # deployment name
  kubectl -n "$NS" get deployment "$1" -o json |
    jq --arg n "probe-$RUN_ID" '{apiVersion:"v1",kind:"Pod",metadata:{name:$n},spec:.spec.template.spec}' |
    kubectl -n "$NS" create --dry-run=server -o json -f - |
    jq -r '[.spec.containers[0].env[]?.name
            | select(test("^AWS_(ROLE_ARN|WEB_IDENTITY_TOKEN_FILE|CONTAINER_)"))] | join(", ")'
}
```

**7.2 Referencia: una ServiceAccount solo con la anotación y otra solo con la asociación**

```bash
injected orders-irsa     # expected (from diff output and coexistence.log): AWS_ROLE_ARN, AWS_WEB_IDENTITY_TOKEN_FILE
injected orders-podid    # expected (from diff output and coexistence.log): AWS_CONTAINER_CREDENTIALS_FULL_URI, AWS_CONTAINER_AUTHORIZATION_TOKEN_FILE
```

**7.3 Añadir una anotación de IRSA a `orders-podid`, que tiene la asociación, y volver a hacer la simulación**

```bash
kubectl -n "$NS" annotate sa orders-podid \
  "eks.amazonaws.com/role-arn=arn:aws:iam::${ACCOUNT_ID}:role/wid-${RUN_ID}-irsa"
injected orders-podid    # expected (from diff output and coexistence.log): AWS_CONTAINER_CREDENTIALS_FULL_URI, AWS_CONTAINER_AUTHORIZATION_TOKEN_FILE
```

**7.4 Limpiar: eliminar la anotación y no iniciar un rollout**

```bash
kubectl -n "$NS" annotate sa orders-podid eks.amazonaws.com/role-arn-
kubectl -n "$NS" get sa orders-podid -o jsonpath='{.metadata.annotations}{"\n"}'   # should be empty
```

**Qué debes comprobar.** Si 7.3 muestra solo las variables de Pod Identity y no muestra `AWS_ROLE_ARN`, el resultado coincide con el cuaderno de trabajo. Medición de la ejecución `d1124` del 21 de noviembre de 2026: solo con la anotación, `AWS_ROLE_ARN` y `AWS_WEB_IDENTITY_TOKEN_FILE`; 5 segundos después de añadir la asociación, solo `AWS_CONTAINER_CREDENTIALS_FULL_URI` y `AWS_CONTAINER_AUTHORIZATION_TOKEN_FILE`; 2 segundos después de eliminar ambas, no aparece nada. Una simulación no crea ningún Pod, así que no afecta al `orders-podid` en ejecución.

**Por qué.** Para una ServiceAccount que tiene una asociación, el webhook de EKS da preferencia a las variables de Pod Identity incluso cuando hay una anotación de IRSA, y no inyecta variables de IRSA. Por el contrario, si añades una asociación más adelante, los Pods **que ya están en ejecución** conservan las variables de IRSA hasta que se vuelvan a crear. Por eso, al cambiar de método, vuelve a crear los Pods con un rollout y elimina la anotación que ya no se usa para que las dos configuraciones no se mezclen.

## Página de demostración pública (opcional)

Esto inicia una página en directo de solo lectura que el público puede abrir en sus propios navegadores. Tres tarjetas muestran el origen de las credenciales, el rol y el resultado de S3 de cada copia, los nombres de las variables `AWS_*` que inyectó EKS y las lecturas recientes; nada de lo que se haga en la página cambia nada. **Cualquiera que tenga la URL puede verla**, así que solo muestra nombres de roles, nombres de Pods, nombres de variables inyectadas y resultados de lectura; nunca muestra credenciales, tokens, ID de cuenta ni ARN.

La ruta es CloudFront (solo HTTPS y GET/HEAD; HTTP se redirige a HTTPS) → origen VPC de CloudFront → ALB **interno** (HTTP 80) → Pod del panel. El grupo de seguridad del ALB solo permite el grupo `CloudFront-VPCOrigins-Service-SG` de la VPC o la lista de prefijos administrada de CloudFront (`com.amazonaws.global.cloudfront.origin-facing`) si ese grupo aún no existe. No se crea ningún balanceador de carga de cara a Internet, IP pública ni regla para CIDR público. El Pod del panel no tiene ningún rol de IAM, y su Role solo enumera Pods y lee sus registros en este espacio de nombres. Como el nodo de demostración usa un límite de saltos de 2, una NetworkPolicy limita el tráfico de salida del Pod a DNS y TCP 443 (API de Kubernetes), para que no pueda acceder a IMDS ni al Pod Identity Agent.

**Requisitos previos adicionales**: AWS Load Balancer Controller, política de red habilitada en VPC CNI (`enableNetworkPolicy`), una versión actual de AWS CLI v2 compatible con los orígenes VPC de CloudFront y permisos para crear y eliminar orígenes VPC y distribuciones de CloudFront, ELB, grupos de seguridad de EC2 y registros de Route 53, además de acceso de lectura al certificado de ACM. Añade tres valores al archivo de entorno:

```bash
export PAGE_DOMAIN=<page host name>
export PAGE_CERT_ARN=<ACM certificate ARN in us-east-1 covering PAGE_DOMAIN>
export PAGE_ZONE_ID=<public hosted zone ID for PAGE_DOMAIN>
```

**Comandos**

```bash
./demo.sh page-up "$RUN_ID"     # measured 446 s (mostly the VPC origin and distribution deployments)
./demo.sh status "$RUN_ID"      # page https://<PAGE_DOMAIN>/ (Deployed)
```

Si `PAGE_DOMAIN` ya tiene registros que no apuntan a la distribución de esta ejecución, el script se detiene sin tocar DNS. Después de ejecutar `page-down` y luego `page-up`, los resolutores que hayan buscado el nombre mientras tanto pueden almacenar en caché durante un máximo de 15 minutos la respuesta «no existe ese nombre» (el TTL negativo SOA de la zona alojada). Justo después de recrearla, observamos que solo el resolutor VPC del host de trabajo devolvía NXDOMAIN (los servidores autoritativos y un resolutor público respondían correctamente); unos 10 minutos más tarde, el nombre se resolvía con normalidad. No recrees la página justo antes de una charla.

**Pantalla esperada** (medida, ejecución `d1124`, verificada con una captura de pantalla en cada paso): el paso de la línea del título sigue el estado de la demostración. Al principio dice «0 · Inicio: las tres copias usan el rol del nodo» y muestra tres tarjetas con node (IMDS); después de `migrate-irsa`, la tarjeta de orders-irsa cambia a IRSA; después de `migrate-podid`, la tarjeta de orders-podid cambia a Pod Identity y muestra los nombres de las variables inyectadas; después de `revoke`, solo la tarjeta de orders-legacy se pone roja y muestra `denied`.

**Qué debes comprobar.** Las tarjetas deberían coincidir con el `watch` del terminal, y la hora UTC de la parte superior debería cambiar cada 2 segundos. Para confirmar que IMDS está bloqueado desde el Pod del panel:

```bash
P=$(kubectl -n "wid-$RUN_ID" get pod -l app=wid-dashboard -o name | head -1)
kubectl -n "wid-$RUN_ID" exec "$P" -- python3 -c "import urllib.request as u; u.urlopen(u.Request('http://169.254.169.254/latest/api/token', method='PUT', headers={'X-aws-ec2-metadata-token-ttl-seconds':'60'}), timeout=3)"
# measured: urllib.error.URLError (timed out) — blocked
```

**Por qué.** El panel recopila el estado de la API de Kubernetes cada 2 segundos y lo mantiene en memoria; responde con `Cache-Control: max-age=1`. CloudFront almacena el contenido en caché según esa cabecera, así que una audiencia numerosa no añade llamadas a la API del clúster.

**Costo y limpieza.** Mientras está en funcionamiento, el ALB añade unos 0,55 USD al día. Elimínalo con `./demo.sh page-down "$RUN_ID"` (546 s medidos); `down` lo ejecuta primero. Para comprobar que no queda nada:

```bash
aws cloudfront list-distributions --query "DistributionList.Items[?Comment=='wid-$RUN_ID-page'].Id" --output text   # empty
aws cloudfront list-vpc-origins --query "VpcOriginList.Items[?Name=='wid-$RUN_ID-page'].Id" --output text         # empty
aws elbv2 describe-load-balancers --names "wid-$RUN_ID-page" 2>&1 | grep -c LoadBalancerNotFound                   # 1
aws route53 list-resource-record-sets --hosted-zone-id "$PAGE_ZONE_ID" \
  --query "ResourceRecordSets[?Name=='$PAGE_DOMAIN.'].Type" --output text                                          # empty
```

## Limpieza (`down`)

Si ejecutaste `harden`, asegúrate primero de que el grupo de nodos esté en estado `ACTIVE`. Para repetir la práctica con el mismo RUN_ID, puedes ejecutar `./demo.sh restore "$RUN_ID"` en lugar de `down` y volver al estado inicial.

**Comando**

```bash
./demo.sh down "$RUN_ID"
```

**Resultado esperado** (medido, ejecución `t1121`, 323 s)

```text
==> deleted namespace
==> deleting node group (3–5 min)
==> deleted launch template
==> deleted role wid-t1121-node
==> deleted role wid-t1121-irsa
==> deleted role wid-t1121-podid
==> deleted bucket
==> done
```

**Comprueba que no queden recursos.** `down` elimina el kubeconfig dedicado, así que usa AWS CLI.

```bash
aws eks describe-nodegroup --cluster-name "$CLUSTER" --nodegroup-name "wid-$RUN_ID" 2>&1 | grep -c ResourceNotFound   # 1
aws eks list-pod-identity-associations --cluster-name "$CLUSTER" --namespace "wid-$RUN_ID" \
  --query 'length(associations)'                                                             # 0
for r in node irsa podid; do
  aws iam get-role --role-name "wid-$RUN_ID-$r" >/dev/null 2>&1 && echo "left: wid-$RUN_ID-$r"
done                                                                                          # no output
aws ec2 describe-launch-templates --filters "Name=tag:LabRun,Values=$RUN_ID" \
  --query 'LaunchTemplates[].LaunchTemplateName' --output text                               # empty
aws ec2 describe-instances --filters "Name=tag:LabRun,Values=$RUN_ID" \
  "Name=instance-state-name,Values=pending,running,stopping,stopped" \
  --query 'Reservations[].Instances[].InstanceId' --output text                              # empty
aws s3api head-bucket --bucket "wid-$RUN_ID-$(aws sts get-caller-identity --query Account --output text)-$AWS_REGION" \
  2>&1 | grep -c 404                                                                         # 1
```

Comprueba también con tu kubeconfig habitual que `kubectl get namespace wid-$RUN_ID` devuelva `NotFound`. Si iniciaste la página de demostración pública, comprueba que no quede ninguna distribución de CloudFront ni ningún ALB interno. Puedes conservar el archivo de entorno para el próximo laboratorio; elimina `$STATE_DIR` si ya no lo necesitas.

## Solución de problemas

| Síntoma | Causa y solución |
| --- | --- |
| Solo aparece el texto de uso (`Usage: ./demo.sh <command> RUN_ID`) | RUN_ID debe tener entre 4 y 12 letras minúsculas o dígitos; no puede contener guiones ni mayúsculas. |
| Aparece `set CLUSTER to an existing EKS cluster name` o un mensaje parecido | `CLUSTER`, `VPC_NAME` o `SUBNET_NAMES` está vacío. Comprueba la ruta y el contenido del archivo de entorno; sus valores prevalecen sobre las variables del shell. |
| `cluster VPC is not <VPC_NAME>` | La VPC encontrada mediante `VPC_NAME` no es la VPC del clúster. Vuelve a comprobar la etiqueta Name de la VPC del clúster. |
| `private subnet '<name>' not found in <VPC_NAME>` | La subred no está en la VPC del clúster o es una subred pública con `MapPublicIpOnLaunch=true`. Usa las etiquetas Name de las subredes privadas. |
| `eks-pod-identity-agent add-on is required` | Instálalo con `aws eks create-addon --cluster-name "$CLUSTER" --addon-name eks-pod-identity-agent` y espera a que esté en estado `ACTIVE`. Coordínalo con el administrador del clúster. |
| `IAM OIDC provider for the cluster is required` | Registra el emisor del clúster como proveedor de OIDC de IAM (por ejemplo, `eksctl utils associate-iam-oidc-provider --cluster "$CLUSTER" --approve`). |
| `role ... is not tagged for run ...; refusing to modify it` | Ya existe un rol con el mismo nombre, pero sin las etiquetas de este laboratorio. Usa otro RUN_ID. |
| `up` se queda bloqueado al crear el grupo de nodos | Comprueba `aws eks describe-nodegroup --cluster-name "$CLUSTER" --nodegroup-name "wid-$RUN_ID" --query nodegroup.health`. Si no hay una ruta NAT desde las subredes privadas, el nodo no puede unirse al clúster ni descargar la imagen. |
| `watch` sigue mostrando `starting` | El Pod aún no está en estado `Running` o no tiene registros. Compruébalo con `kubectl -n "$NS" get pods` y `kubectl -n "$NS" describe pod`. |
| `association change not visible to admission within 120s` | Comprueba que la asociación exista con `aws eks list-pod-identity-associations` y vuelve a ejecutar `migrate-podid`. Si la asociación existe, se omite su creación y se pasa directamente a comprobar la inyección. |
| `orders-podid` sigue usando el rol del nodo después de `migrate-podid` | El Pod se creó antes de la inyección. Comprueba sus variables con el comando del paso 3; si faltan, vuelve a ejecutar `kubectl -n "$NS" rollout restart deploy/orders-podid`. |
| `legacy copy did not flip within 180s` | La propagación de IAM va lenta. Sigue observando `watch`. Si vuelves a ejecutar `revoke`, indicará que la política ya se ha eliminado y solo volverá a esperar. |
| El resultado de S3 es `error` | Se produjo un error distinto de `AccessDenied` o de la falta de credenciales. Comprueba la ruta del Pod a los puntos de conexión de STS y S3 (NAT, puntos de conexión de VPC, DNS). |
| El rol es el esperado, pero aparece `denied` | La identidad del rol y el acceso a los recursos son cosas distintas. Comprueba la política del bucket, las SCP, los límites de permisos y las políticas de los puntos de conexión de VPC. |

## Referencias

- [Migrar los permisos de IAM del nodo de EKS a IRSA y Pod Identity](../../security/17-eks-workload-identity-migration.md) — el cuaderno de trabajo de este laboratorio
- [Código de la demostración y guía de ejecución para quien la presenta](https://github.com/Atom-oh/kubernetes-docs/tree/main/examples/security/eks-workload-identity)
- [Roles de IAM para cuentas de servicio](https://docs.aws.amazon.com/eks/latest/userguide/iam-roles-for-service-accounts.html)
- [Cómo funciona EKS Pod Identity](https://docs.aws.amazon.com/eks/latest/userguide/pod-id-how-it-works.html)
- [Plantillas de lanzamiento de grupos de nodos administrados](https://docs.aws.amazon.com/eks/latest/userguide/launch-templates.html)

## Pasos siguientes

- Comprueba lo que has aprendido con el [cuestionario sobre la migración de IAM de cargas de trabajo de EKS](../../quizzes/security/17-eks-workload-identity-migration-quiz.md).
- Usa el [orden de migración a producción](../../security/17-eks-workload-identity-migration.md) del cuaderno de trabajo para planificar la identificación de dependencias y la migración canaria de tus cargas de trabajo reales.
