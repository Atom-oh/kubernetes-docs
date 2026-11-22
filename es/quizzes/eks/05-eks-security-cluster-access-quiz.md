# Cuestionario sobre la autenticación para el acceso a clústeres de EKS

> **Última actualización**: 21 de noviembre de 2026

Este cuestionario comprueba tu comprensión de [Autenticación para el acceso a clústeres de EKS: IAM y entradas de acceso](../../eks/05-eks-security-cluster-access.md).

## Resumen del cuestionario
- Autenticación de IAM y autorización de Kubernetes
- Rol del clúster de EKS y entidad que realiza el aprovisionamiento
- Modo de autenticación y entradas de acceso
- Alcance de las políticas de acceso y verificación

## Preguntas de opción múltiple

### 1. Para un usuario o rol de IAM, ¿qué configuración de EKS combina correctamente la autenticación de identidad y la autorización de Kubernetes?

- A) Usar únicamente permisos de administración de IAM
- B) Crear reglas de RBAC sin configurar la ruta de autenticación de la identidad
- C) Configurar el acceso al clúster de IAM junto con las reglas de RBAC y/o las políticas de acceso de EKS adecuadas
- D) Usar únicamente restricciones de red del punto de conexión de la API

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Configurar el acceso al clúster de IAM junto con las reglas de RBAC y/o las políticas de acceso de EKS adecuadas**

**Explicación:**

IAM autentica la identidad humana o de automatización prevista mediante la ruta de acceso a EKS configurada. RBAC de Kubernetes y las políticas de acceso de EKS autorizan las operaciones de Kubernetes; los permisos que otorgan son aditivos. Las restricciones de red son otra capa y no sustituyen a la autorización. La autenticación de Pod a Kubernetes normalmente usa su token de ServiceAccount; IRSA/Pod Identity proporciona, en cambio, credenciales de AWS a las cargas de trabajo.

El rol de servicio del clúster de EKS y el rol de un desarrollador humano tienen propósitos distintos. Asociar AmazonEKSClusterPolicy al desarrollador no concede acceso a Kubernetes, y los permisos DescribeCluster/ListClusters o un archivo kubeconfig no conceden permisos sobre las cargas de trabajo.

**Implementación con alcance limitado:** un operador autorizado de la plataforma prepara el espacio de nombres y las reglas de RBAC siguientes para un rol de IAM de desarrollador aprobado que ya existe. El clúster ya debe admitir entradas de acceso. Conserva las asignaciones existentes de administradores y nodos, y revisa la migración del modo de autenticación; no sobrescribas aws-auth con un ConfigMap de ejemplo.

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: security-demo
  labels:
    pod-security.kubernetes.io/enforce: restricted
    pod-security.kubernetes.io/enforce-version: v1.36
```



```bash
set -euo pipefail
: "${CLUSTER_NAME:?Set the verified cluster name}"
: "${AWS_REGION:?Set its Region}"
: "${DEVELOPER_ROLE_ARN:?Set a prepared IAM role ARN, not an STS session ARN}"
MODE=$(aws eks describe-cluster --name "$CLUSTER_NAME" --region "$AWS_REGION" \
  --query cluster.accessConfig.authenticationMode --output text)
case "$MODE" in
  API|API_AND_CONFIG_MAP) ;;
  *) echo "Access entries are not enabled; review the migration first"; exit 1 ;;
esac
aws eks list-access-entries --cluster-name "$CLUSTER_NAME" --region "$AWS_REGION" \
  --output json > security-access-entries.json
python3 - "$DEVELOPER_ROLE_ARN" <<'PY'
import json, sys
with open("security-access-entries.json") as stream:
    existing = json.load(stream)["accessEntries"]
if sys.argv[1] in existing:
    raise SystemExit("Entry already exists; inspect its groups/policies instead of overwriting")
PY
aws eks create-access-entry --cluster-name "$CLUSTER_NAME" --region "$AWS_REGION" \
  --principal-arn "$DEVELOPER_ROLE_ARN" --type STANDARD \
  --kubernetes-groups security-demo-developers
```



```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: developer
  namespace: security-demo
rules:
- apiGroups:
  - ''
  resources:
  - pods
  verbs:
  - get
  - list
  - watch
- apiGroups:
  - apps
  resources:
  - deployments
  verbs:
  - get
  - list
  - watch
  - create
  - update
  - patch
- apiGroups:
  - batch
  resources:
  - jobs
  verbs:
  - get
  - list
  - watch
  - create
  - update
  - patch
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: developer
  namespace: security-demo
subjects:
- kind: Group
  name: security-demo-developers
  apiGroup: rbac.authorization.k8s.io
roleRef:
  kind: Role
  name: developer
  apiGroup: rbac.authorization.k8s.io
```

El nombre del grupo de la entrada de acceso debe coincidir con el sujeto del RoleBinding. Este rol permite únicamente las operaciones indicadas en security-demo; otros permisos existentes pueden ampliar el acceso. Crear Deployments/Jobs puede permitir indirectamente el uso de Secrets, PVC y ServiceAccounts de ese espacio de nombres, por lo que la ausencia de una regla directa de lectura de Secret no constituye un límite de seguridad entre inquilinos. Separa a los inquilinos y restringe la identidad y el uso de recursos de las cargas de trabajo mediante controles de admisión y de propiedad.

Un visor, revisado por separado, puede usar en su lugar una asociación de AmazonEKSViewPolicy con alcance limitado a un espacio de nombres. Inspecciona las políticas de acceso existentes antes de añadirla; no revoca permisos más amplios de RBAC ni los concedidos por otras políticas de acceso. `eks:namespaces` filtra las solicitudes de asociación de políticas de acceso, no las solicitudes generales de kubectl.

**Valida el inicio de sesión real:** la entidad que realiza la llamada debe poder descubrir el clúster y asumir el rol aprobado. Esto crea un kubeconfig temporal en lugar de reemplazar el contexto predeterminado:

```bash
set -euo pipefail
umask 077
: "${CLUSTER_NAME:?Set the reviewed cluster name}"
: "${AWS_REGION:?Set the cluster Region}"
: "${DEVELOPER_ROLE_ARN:?Set the intended IAM role ARN}"
review_dir=$(mktemp -d "${TMPDIR:-/tmp}/eks-login-check.XXXXXXXX")
trap 'rm -rf -- "$review_dir"' EXIT
aws eks update-kubeconfig --name "$CLUSTER_NAME" --region "$AWS_REGION" \
  --role-arn "$DEVELOPER_ROLE_ARN" --kubeconfig "$review_dir/config"
kubectl --kubeconfig "$review_dir/config" auth can-i list pods -n security-demo
kubectl --kubeconfig "$review_dir/config" auth can-i create jobs -n security-demo
kubectl --kubeconfig "$review_dir/config" auth can-i list pods -n another-team
```

Compara los resultados con los permisos previstos e investiga cualquier permiso inesperado entre espacios de nombres. `--as` comprueba la suplantación de identidad y RBAC, pero no demuestra que funcione la ruta de las políticas de acceso de IAM. Para este cuestionario no se ejecutó ninguna prueba real de inicio de sesión de IAM ni de autorización de Kubernetes; las pruebas de esquema y de shell, junto con los flujos simulados de entradas de acceso, son las comprobaciones locales realizadas.

Referencias: [Entradas de acceso de EKS](https://docs.aws.amazon.com/eks/latest/userguide/access-entries.html), [Políticas de acceso de EKS](https://docs.aws.amazon.com/eks/latest/userguide/access-policies.html), [RBAC de Kubernetes](https://kubernetes.io/docs/reference/access-authn-authz/rbac/).

</details>

### 2. ¿Qué afirmación sobre el cambio del modo de autenticación CONFIG_MAP a API_AND_CONFIG_MAP o API es correcta?

- A) No es totalmente reversible; conserva las asignaciones de administradores y nodos, y planifica una vía de recuperación
- B) Siempre se puede volver al modo anterior más adelante, así que cambia de modo sin revisarlo antes
- C) Primero sobrescribe aws-auth con un ConfigMap breve de ejemplo que omita los roles de nodo
- D) El modo API migra automáticamente todas las asignaciones de aws-auth a entradas de acceso, así que omite todas las comprobaciones

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A) No es totalmente reversible; conserva las asignaciones de administradores y nodos, y planifica una vía de recuperación**

**Explicación:**

Inspecciona el modo de autenticación actual en `accessConfig` de `describe-cluster` y conserva las asignaciones existentes de administradores y nodos antes de la migración. El cambio de CONFIG_MAP a API_AND_CONFIG_MAP/API no es totalmente reversible. No sobrescribas aws-auth con un ejemplo breve que omita los roles de nodo; revisa todas las identidades, políticas y nodos, y prepara una vía de recuperación antes de elegir el modo exclusivo de API.

</details>

### 3. ¿Qué afirmación sobre el rol estándar de IAM del clúster de EKS y los permisos de desarrollador es correcta?

- A) El rol del clúster debe confiar en el usuario de IAM del desarrollador para que kubectl funcione
- B) AmazonEKSClusterPolicy en un rol de desarrollador concede acceso a todos los espacios de nombres
- C) CreateCluster admite la limitación por ARN de recurso, por lo que basta con limitarlo únicamente al ARN del clúster
- D) El rol del clúster confía en el servicio `eks.amazonaws.com`, no en las identidades de desarrolladores

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: D) El rol del clúster confía en el servicio `eks.amazonaws.com`, no en las identidades de desarrolladores**

**Explicación:**

La relación de confianza del rol estándar de IAM del clúster de EKS permite `sts:AssumeRole` al principal de servicio `eks.amazonaws.com`; no es la política de permisos del desarrollador. Por separado, la entidad que realiza el aprovisionamiento necesita las acciones correspondientes a la configuración seleccionada y PassRole para el rol previsto. La referencia de autorización actual indica que CreateCluster no admite la limitación por ARN de recurso, así que usa las condiciones de solicitud admitidas. Asociar AmazonEKSClusterPolicy a un rol de desarrollador no concede acceso a las aplicaciones de Kubernetes.

</details>

### 4. Después de configurar la entrada de acceso y RBAC de un desarrollador, ¿qué indica el resultado de `kubectl auth can-i --as=...`?

- A) Prueba que funcionan tanto el inicio de sesión real de IAM como la ruta de las políticas de acceso
- B) Solo comprueba la suplantación de identidad y RBAC de Kubernetes; no demuestra que funcione la ruta de las políticas de acceso de IAM
- C) No hace falta nada más, porque el propio kubeconfig concede los permisos
- D) Solo comprueba la evaluación de la política de IAM, ya que `--as` omite completamente RBAC

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Solo comprueba la suplantación de identidad y RBAC de Kubernetes; no demuestra que funcione la ruta de las políticas de acceso de IAM**

**Explicación:**

`kubectl --as` comprueba la suplantación de identidad y RBAC de Kubernetes, no demuestra que funcione la ruta de las políticas de acceso de IAM. Las actualizaciones pueden tardar en propagarse, así que realiza la prueba con el inicio de sesión de IAM previsto. Un kubeconfig indica al cliente a qué clúster conectarse y qué mecanismo de credenciales usar; por sí solo no concede permisos.

</details>

### 5. ¿Qué afirmación sobre una asociación de AmazonEKSViewPolicy limitada a un espacio de nombres y la condición `eks:namespaces` es correcta?

- A) Añadir View revoca los permisos más amplios de RBAC que ya tiene el principal
- B) `eks:namespaces` limita todas las llamadas a la API de kubectl a los espacios de nombres indicados
- C) `eks:AccessKubernetesApi` es un permiso general de RBAC para espacios de nombres que permite usar kubectl
- D) Añadir View no revoca nada; `eks:namespaces` filtra las solicitudes de asociación

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: D) Añadir View no revoca nada; `eks:namespaces` filtra las solicitudes de asociación**

**Explicación:**

Inspecciona los grupos actuales de la entrada y las políticas asociadas con `list-associated-access-policies` antes de añadir el permiso. Añadir View no revoca permisos más amplios de RBAC o de políticas de acceso. La condición `eks:namespaces` filtra las solicitudes de asociación de políticas de acceso; no es un filtro general de espacios de nombres para las llamadas a la API de kubectl. `eks:AccessKubernetesApi` es un permiso para ver la consola.

</details>
