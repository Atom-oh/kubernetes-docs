# Guía del laboratorio de creación de clústeres de EKS

> **Dificultad**: Intermedia
> **Tiempo estimado**: 60–90 minutos; los tiempos de aprovisionamiento y eliminación pueden variar
> **Última actualización**: 12 de septiembre de 2026

## Objetivos de aprendizaje

- Crear un clúster de EKS dedicado con eksctl.
- Verificar la cuenta de AWS y la identidad del clúster antes de modificar recursos.
- Inspeccionar los nodos, implementar una aplicación de ejemplo y escalarla.
- Eliminar los recursos del laboratorio y comprobar si la limpieza quedó incompleta.

## Requisitos previos

- [ ] Una cuenta de laboratorio de AWS aprobada y credenciales temporales de un rol, por ejemplo, mediante IAM Identity Center. Pida a un administrador que apruebe los permisos necesarios de EKS, EC2, CloudFormation, IAM/PassRole y otros permisos relacionados con esta configuración; no cree un usuario IAM de larga duración ni conceda AdministratorAccess solo para seguir esta guía.
- [ ] AWS CLI v2, eksctl, kubectl, Bash, Python 3, jq y curl.
- [ ] Un CIDR IPv4 público aprobado para el cliente; normalmente, la dirección de salida actual de su estación de trabajo con prefijo `/32`. El generador rechaza rangos más amplios que `/24`; si su organización exige un rango más restringido, use ese rango.
- [ ] Haber completado [Creación de clústeres de EKS](../../eks/02-eks-cluster-creation-part1.md).

Este laboratorio usa un grupo de nodos administrado de EKS 1.36. En la fecha de revisión, AWS incluye la versión 1.36 en el soporte estándar; el ejemplo anterior con la versión 1.31 ya está en soporte extendido. Consulte el calendario de soporte actual de AWS antes de ejecutar el laboratorio. Use una versión secundaria de kubectl que difiera como máximo en una de la versión del servidor de API; para este ejemplo, se recomienda la 1.36.

Los ejemplos se comprobaron con eksctl 0.229.0 y kubectl 1.36.2 mediante esquemas y simulaciones locales. **En esta auditoría no se aprovisionó un clúster ni se midió el tiempo de implementación.** Aún debe validar los permisos de la cuenta, las cuotas, la disponibilidad de instancias y el acceso a la red en su cuenta de laboratorio.

EKS, EC2, EBS, la puerta de enlace NAT y la transferencia de datos generan cargos. Esta configuración crea nodos privados con una puerta de enlace NAT; es una decisión sobre costos y disponibilidad para un laboratorio, no un diseño de disponibilidad para producción. La política de soporte `STANDARD` evita pasar al soporte extendido al permitir una actualización automática posterior de versión; no detiene el clúster ni sus otros cargos.

Ejecute los comandos en orden, en una terminal Bash dedicada (**Terminal A**). Conserve la ruta privada del laboratorio que se imprime y no confirme en Git su kubeconfig ni los registros de identidad. Los comandos posteriores dependen de las variables y funciones definidas aquí.

## Ejercicio 1: herramientas y cuenta

### 1.1 Comprobar las herramientas

```bash
aws --version
eksctl version
kubectl version --client
python3 --version
jq --version
```

### 1.2 Establecer la cuenta prevista y el rango del cliente

Antes de este bloque, establezca `EXPECTED_ACCOUNT_ID` y `CLIENT_CIDR` con los valores aprobados. No copie un ID de cuenta de ejemplo ni una dirección IP reservada para documentación. El valor predeterminado de `AWS_REGION` es Seúl; las dos variables de región se mantienen coherentes.

```bash
set -euo pipefail
: "${EXPECTED_ACCOUNT_ID:?Set the intended 12-digit lab account ID}"
: "${CLIENT_CIDR:?Set your approved public client IPv4 CIDR, usually a /32}"
export AWS_REGION="${AWS_REGION:-ap-northeast-2}"
export AWS_DEFAULT_REGION="$AWS_REGION"
export EXPECTED_ACCOUNT_ID CLIENT_CIDR
umask 077
export LAB_DIR
LAB_DIR=$(mktemp -d "$PWD/eks-lab.XXXXXXXX")
export LAB_RUN_ID
LAB_RUN_ID=$(python3 -c 'import uuid; print(uuid.uuid4().hex[:12])')
export CLUSTER_NAME="eks-lab-$LAB_RUN_ID"
export KUBECONFIG="$LAB_DIR/kubeconfig"
printf 'Private lab directory: %s\nCluster: %s\nRegion: %s\n' "$LAB_DIR" "$CLUSTER_NAME" "$AWS_REGION"
```

El generador de configuración valida esos valores y registra el clúster previsto antes de crearlo:

```bash
python3 - <<'PY'
import ipaddress, json, os, re
from pathlib import Path
account = os.environ["EXPECTED_ACCOUNT_ID"]
region = os.environ["AWS_REGION"]
name = os.environ["CLUSTER_NAME"]
run_id = os.environ["LAB_RUN_ID"]
network = ipaddress.ip_network(os.environ["CLIENT_CIDR"], strict=True)
if not re.fullmatch(r"\d{12}", account):
    raise SystemExit("Expected a 12-digit account ID")
if not re.fullmatch(r"[a-z]{2}(?:-[a-z]+)+-\d", region):
    raise SystemExit("Invalid Region")
if not re.fullmatch(r"eks-lab-[0-9a-f]{12}", name) or name != "eks-lab-" + run_id:
    raise SystemExit("Unexpected lab name")
if network.version != 4 or network.prefixlen < 24:
    raise SystemExit("Use a reviewed narrow IPv4 CIDR (/24 or narrower); never 0.0.0.0/0")
config = {
    "apiVersion": "eksctl.io/v1alpha5", "kind": "ClusterConfig",
    "metadata": {"name": name, "region": region, "version": "1.36",
                 "tags": {"content-lab-id": run_id}},
    "accessConfig": {"authenticationMode": "API"},
    "upgradePolicy": {"supportType": "STANDARD"},
    "vpc": {"clusterEndpoints": {"publicAccess": True, "privateAccess": True},
            "publicAccessCIDRs": [str(network)], "nat": {"gateway": "Single"}},
    "managedNodeGroups": [{
        "name": "workers", "instanceType": "t3.medium", "amiFamily": "AmazonLinux2023",
        "desiredCapacity": 2, "minSize": 1, "maxSize": 3,
        "privateNetworking": True, "volumeSize": 20, "volumeType": "gp3",
        "volumeEncrypted": True
    }]
}
directory = Path(os.environ["LAB_DIR"])
(directory / "cluster.json").write_text(json.dumps(config, indent=2) + "\n")
(directory / "lab-state.json").write_text(json.dumps({
    "account": account, "region": region, "cluster": name, "labId": run_id
}, indent=2) + "\n")
PY
```

```bash
check_account() {
  local actual
  actual=$(aws sts get-caller-identity --region "$AWS_REGION" --query Account --output text)
  test "$actual" = "$EXPECTED_ACCOUNT_ID" || { printf '%s\n' 'Account mismatch; stop.' >&2; return 1; }
}
check_account
aws sts get-caller-identity --region "$AWS_REGION"
```

La cuenta que devuelve el comando debe coincidir con `EXPECTED_ACCOUNT_ID`; es normal que las credenciales temporales muestren el ARN de un rol asumido. Si no coincide o falla la autenticación, deténgase.

## Ejercicio 2: crear e identificar el clúster

### 2.1 Revisar la configuración

```bash
cat "$LAB_DIR/cluster.json"
```

La configuración selecciona EKS 1.36, entradas de acceso basadas en API, dos nodos administrados `t3.medium`, AL2023, discos de nodo gp3 cifrados de 20 GiB y una etiqueta única `content-lab-id`. Ambos endpoints de API están habilitados: los nodos usan el acceso privado y el endpoint público solo permite el CIDR de cliente aprobado. Los nodos siguen necesitando acceso saliente a los endpoints de imágenes y paquetes.

### 2.2 Crear el clúster

El comando siguiente crea recursos facturables. Reserve tiempo suficiente tanto para la creación como para la limpieza; el tiempo de espera de 45 minutos es un límite de espera, no una garantía de finalización.

```bash
# MUTATION: creates billed CloudFormation/EKS/VPC/NAT/EC2/EBS resources.
check_account
eksctl create cluster --config-file "$LAB_DIR/cluster.json" \
  --write-kubeconfig=false --timeout=45m
```

Si la creación falla o se interrumpe, **no inicie otro clúster con un nombre aleatorio ni ejecute a ciegas el bloque de limpieza normal**. Conserve `lab-state.json` y `cluster.json`, inspeccione las pilas de CloudFormation identificadas por nombre y, antes de continuar, compruebe sus etiquetas, cuenta y recursos. Una respuesta de error de la CLI no demuestra que no se hayan creado recursos; los recursos pendientes pueden seguir generando cargos.

### 2.3 Guardar la identidad y un kubeconfig privado

Ejecute este paso solo si la creación finalizó correctamente. `--write-kubeconfig=false` arriba deja intacto su kubeconfig habitual; el comando siguiente escribe únicamente en la ruta dedicada del laboratorio.

```bash
check_account
aws eks describe-cluster --region "$AWS_REGION" --name "$CLUSTER_NAME" \
  --query 'cluster.{arn:arn,createdAt:createdAt,endpoint:endpoint,tags:tags}' \
  --output json > "$LAB_DIR/cluster-identity.json"
jq -e --arg id "$LAB_RUN_ID" '.tags["content-lab-id"] == $id' "$LAB_DIR/cluster-identity.json"
aws eks update-kubeconfig --region "$AWS_REGION" --name "$CLUSTER_NAME" \
  --kubeconfig "$KUBECONFIG" --alias "$CLUSTER_NAME"
```

Defina una protección que compruebe la cuenta, el ARN del clúster, la hora de creación, la etiqueta de propiedad y el endpoint del kubeconfig antes de hacer cambios posteriores:

```bash
check_lab() {
  check_account || return
  local current endpoint
  current=$(aws eks describe-cluster --region "$AWS_REGION" --name "$CLUSTER_NAME" --output json) || return
  jq -e --arg id "$LAB_RUN_ID" --slurpfile saved "$LAB_DIR/cluster-identity.json" '
    .cluster.arn == $saved[0].arn and
    .cluster.createdAt == $saved[0].createdAt and
    .cluster.tags["content-lab-id"] == $id and
    .cluster.endpoint == $saved[0].endpoint
  ' <<<"$current" >/dev/null || { printf '%s\n' 'Cluster identity mismatch; stop.' >&2; return 1; }
  endpoint=$(kubectl --kubeconfig "$KUBECONFIG" --context "$CLUSTER_NAME" config view --minify \
    -o jsonpath='{.clusters[0].cluster.server}') || return
  jq -e --arg endpoint "$endpoint" '.endpoint == $endpoint' "$LAB_DIR/cluster-identity.json" >/dev/null ||
    { printf '%s\n' 'Kubeconfig endpoint mismatch; stop.' >&2; return 1; }
}
check_lab
```

### Verificación

```bash
check_lab
kubectl --context "$CLUSTER_NAME" --request-timeout=15s get nodes -o wide
kubectl --context "$CLUSTER_NAME" wait node --selector=eks.amazonaws.com/nodegroup=workers \
  --for=condition=Ready --timeout=300s
kubectl --context "$CLUSTER_NAME" --request-timeout=15s get nodes \
  -l eks.amazonaws.com/nodegroup=workers -o json |
  jq -e '(.items | length) == 2 and all(.items[];
    any(.status.conditions[]; .type == "Ready" and .status == "True"))'
```

Ambos nodos deberían estar en estado Ready. Si se registra menos de dos nodos, inspeccione el grupo de nodos y los eventos de CloudFormation; la creación satisfactoria del plano de control no demuestra que los nodos de trabajo estén sanos.

## Ejercicio 3: explorar el clúster

Elija un `NODE_NAME` de la lista verificada de nodos y establézcalo antes de ejecutar este bloque. Este laboratorio usa nodos administrados convencionales, por lo que la vista de sus componentes del sistema difiere de la de un clúster que usa únicamente Auto Mode.

```bash
check_lab
: "${NODE_NAME:?Choose a node name from the preceding list}"
kubectl --context "$CLUSTER_NAME" --request-timeout=15s describe node "$NODE_NAME"
kubectl --context "$CLUSTER_NAME" --request-timeout=15s -n kube-system get pods
kubectl --context "$CLUSTER_NAME" --request-timeout=15s -n kube-system get services
# Run separately; preserve the actual error if the metrics API is unavailable.
if ! kubectl --context "$CLUSTER_NAME" --request-timeout=15s top nodes; then
  printf 'Metrics query failed; inspect the error and metrics API status.\n' >&2
fi
```

`kubectl top` requiere la API de métricas. Si falla, puede deberse a que falta metrics-server, a que las métricas no están disponibles, a RBAC o a problemas de conectividad. Conserve el error real y diagnostíquelo; no concluya sin comprobarlo que metrics-server está ausente.

## Ejercicio 4: implementar y escalar una aplicación

### 4.1 Implementar nginx

El Deployment tiene solicitudes y límites explícitos de recursos, además de una sonda de disponibilidad. El Service es de tipo `ClusterIP`; este ejercicio no instala un controlador de balanceadores de carga ni asigna un balanceador público.

```bash
cat > "$LAB_DIR/app.yaml" <<'YAML'
apiVersion: apps/v1
kind: Deployment
metadata:
  name: nginx
  namespace: eks-lab
spec:
  replicas: 2
  selector:
    matchLabels:
      app: nginx
  template:
    metadata:
      labels:
        app: nginx
    spec:
      automountServiceAccountToken: false
      containers:
      - name: nginx
        image: nginx:1.30.6
        ports:
        - containerPort: 80
        resources:
          requests:
            cpu: 100m
            memory: 64Mi
          limits:
            cpu: 500m
            memory: 128Mi
        readinessProbe:
          httpGet:
            path: /
            port: 80
          initialDelaySeconds: 2
          periodSeconds: 5
---
apiVersion: v1
kind: Service
metadata:
  name: nginx
  namespace: eks-lab
spec:
  type: ClusterIP
  selector:
    app: nginx
  ports:
  - port: 80
    targetPort: 80
YAML
```

```bash
# MUTATION in the verified dedicated lab cluster.
check_lab
kubectl --context "$CLUSTER_NAME" create namespace eks-lab
kubectl --context "$CLUSTER_NAME" label namespace eks-lab "content-lab-id=$LAB_RUN_ID"
kubectl --context "$CLUSTER_NAME" apply -f "$LAB_DIR/app.yaml"
kubectl --context "$CLUSTER_NAME" -n eks-lab rollout status deployment/nginx --timeout=180s
```

### 4.2 Verificar el acceso local

Inicie el reenvío de puertos en la Terminal A y, después, ejecute el comando curl en la **Terminal B** de la misma estación de trabajo. El listener solo se enlaza a la interfaz loopback. La conexión reenviada prueba un Pod seleccionado; no prueba el balanceo de carga externo ni todas las réplicas.

```bash
# Keep this in Terminal A; it binds only loopback. Stop with Ctrl+C before continuing.
check_lab
kubectl --context "$CLUSTER_NAME" -n eks-lab port-forward service/nginx 8080:80 --address=127.0.0.1 || test "$?" -eq 130
```

```bash
# Terminal B on the same workstation; no AWS credentials are needed for this local URL.
curl --fail --silent --show-error --connect-timeout 5 --max-time 10 \
  http://127.0.0.1:8080/ --output /dev/null --write-out 'HTTP %{http_code}\n'
```

Una comprobación correcta imprime `HTTP 200`. Detenga el reenvío de puertos en primer plano con Ctrl+C en la Terminal A antes de continuar. El comando permite esa interrupción prevista y conserva las comprobaciones de otros errores.

### 4.3 Escalar a cuatro réplicas

```bash
# MUTATION: after stopping port-forward in Terminal A.
check_lab
kubectl --context "$CLUSTER_NAME" -n eks-lab scale deployment/nginx --replicas=4
kubectl --context "$CLUSTER_NAME" -n eks-lab rollout status deployment/nginx --timeout=180s
kubectl --context "$CLUSTER_NAME" --request-timeout=15s -n eks-lab get deployment nginx -o json |
  jq -e '.spec.replicas == 4 and .status.observedGeneration >= .metadata.generation and
         .status.readyReplicas == 4 and .status.availableReplicas == 4'
```

Si también desea practicar con un LoadBalancer público, siga primero [Redes de EKS](../../eks/03-eks-networking-part1.md) para configurar el controlador previsto, los permisos IAM y los ajustes de exposición. Lleve un registro y elimine por separado sus recursos y costos; que se asigne un nombre de host o que el Deployment esté Ready no demuestra que el balanceador funcione de extremo a extremo.

## Limpieza

Detenga primero el reenvío de puertos. Este bloque elimina el namespace etiquetado del laboratorio y el clúster dedicado. Se permite que el namespace no exista; si no puede leerlo o sus etiquetas no coinciden, no se considera seguro eliminarlo.

```bash
# DESTRUCTIVE: only the verified dedicated lab resources.
check_lab
namespace_json=$(kubectl --context "$CLUSTER_NAME" --request-timeout=15s \
  get namespace eks-lab --ignore-not-found -o json)
if [ -n "$namespace_json" ]; then
  jq -e --arg id "$LAB_RUN_ID" '.metadata.labels["content-lab-id"] == $id' \
    <<<"$namespace_json" >/dev/null
  kubectl --context "$CLUSTER_NAME" delete namespace eks-lab --wait=true --timeout=180s
fi
check_lab
eksctl delete cluster --name "$CLUSTER_NAME" --region "$AWS_REGION" --wait --timeout=45m
aws eks wait cluster-deleted --name "$CLUSTER_NAME" --region "$AWS_REGION"
# Keep private config/identity records until remaining resources/billing are checked.
```

Se requiere `--wait` para detectar errores de eliminación. El waiter de eliminación de EKS confirma que el objeto del plano de control ya no existe, no que hayan desaparecido todos los recursos dependientes o cargos. Inspeccione el estado de la pila de CloudFormation guardado para el laboratorio y los recursos etiquetados que aún queden de EC2/EBS/NAT/VPC, incluidos los recursos en `DELETE_FAILED` o retenidos. Conserve la evidencia local de identidad y configuración hasta completar esa comprobación. No reemplace la verificación de la eliminación por una espera de duración fija.

Si la creación no llegó a capturar la identidad, use el registro privado de intención y los eventos/etiquetas de CloudFormation para verificar manualmente la propiedad. No invente un archivo `cluster-identity.json` solo para que pase la protección.

## Solución de problemas

<details>
<summary>Falla la creación del clúster</summary>

Compruebe los permisos del rol aprobado, las cuotas de servicio, la capacidad de IP/subredes y la disponibilidad de instancias en la región elegida. eksctl usa CloudFormation; inspeccione el error real en vez de conceder acceso de administrador general como solución predeterminada.

```bash
check_account
eksctl utils describe-stacks --region "$AWS_REGION" --cluster "$CLUSTER_NAME"
```

Durante la recuperación de una creación parcial, conserve el directorio privado del laboratorio. Antes de ejecutar cualquier eliminación propuesta, compárela con la propiedad real de los recursos.

</details>

<details>
<summary>kubectl no puede conectarse</summary>

Compruebe las credenciales del rol, las entradas de acceso, DNS y si la dirección de salida actual de la estación de trabajo sigue dentro del CIDR aprobado. Si necesita reconstruir el kubeconfig privado, primero verifique la identidad del clúster y luego escriba únicamente en la ruta de este laboratorio:

```bash
check_account
aws eks update-kubeconfig --region "$AWS_REGION" --name "$CLUSTER_NAME" \
  --kubeconfig "$KUBECONFIG" --alias "$CLUSTER_NAME"
check_lab
```

No amplíe el acceso al endpoint a todo Internet para compensar un cambio en la dirección del cliente.

</details>

## Referencias

- [Versiones de EKS compatibles](https://docs.aws.amazon.com/eks/latest/userguide/kubernetes-versions.html)
- [Política de actualización de EKS](https://docs.aws.amazon.com/eks/latest/userguide/view-upgrade-policy.html)
- [Acceso al endpoint del clúster](https://docs.aws.amazon.com/eks/latest/userguide/cluster-endpoint.html)
- [Permisos IAM de eksctl](https://docs.aws.amazon.com/eks/latest/eksctl/minimum-iam-policies.html)
- [Creación y eliminación con eksctl](https://docs.aws.amazon.com/eks/latest/eksctl/creating-and-managing-clusters.html)
- [Diferencia de versiones de kubectl](https://kubernetes.io/releases/version-skew-policy/)
- [Reenvío de puertos](https://kubernetes.io/docs/tasks/access-application-cluster/port-forward-access-application-cluster/)
- [Definiciones oficiales de la imagen nginx](https://github.com/docker-library/official-images/blob/master/library/nginx)

## Siguientes pasos

- [Cuestionario sobre la creación de clústeres de EKS](../../quizzes/eks/02-eks-cluster-creation-part1-quiz.md)
- [Redes de EKS](../../eks/03-eks-networking-part1.md)
