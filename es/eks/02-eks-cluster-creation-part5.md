# Parte 5: Acceso, validación, actualización y eliminación del cluster

## Configuración del acceso al cluster

Después de crear un cluster de EKS, se requiere configuración para acceder al cluster. En esta sección, aprenderemos a configurar el acceso al cluster.

### Proceso de configuración del acceso al cluster

![Diagrama del flujo de configuración de acceso: kubeconfig, principal de IAM, entrada de acceso, reglas y binding de RBAC, y luego una prueba de acceso.](../.gitbook/assets/en-eks-02-eks-cluster-creation-part5-0.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-02-eks-cluster-creation-part5-0.html)

### Configuración de kubeconfig

Debes configurar el archivo kubeconfig para acceder a un cluster de EKS. Puedes configurar kubeconfig mediante AWS CLI:

```bash
aws eks update-kubeconfig \
  --name my-cluster \
  --region us-west-2
```

Este comando actualiza el archivo `~/.kube/config` para habilitar el acceso al cluster de EKS.

### Configuración del acceso de usuarios y roles de IAM

De forma predeterminada, solo la entidad de IAM (usuario o rol) que creó el cluster de EKS puede acceder a este. Hay dos métodos para conceder acceso al cluster a otros usuarios o roles de IAM: el método tradicional aws-auth ConfigMap y el nuevo método EKS Access Entry.

![Diagrama que compara las dos formas en que un principal de IAM se asigna a la API de Kubernetes: las entradas de acceso de EKS y el aws-auth ConfigMap.](../.gitbook/assets/en-eks-02-eks-cluster-creation-part5-1.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-02-eks-cluster-creation-part5-1.html)

#### Método 1: EKS Access Entry (recomendado)

EKS Access Entry es un método nuevo que reemplaza el aws-auth ConfigMap y ofrece un enfoque más estable y fácil de administrar.

1. Habilita Access Entry para el cluster:

```bash
aws eks update-cluster-config \
  --name my-cluster \
  --region us-west-2 \
  --access-config authenticationMode=API_AND_CONFIG_MAP
```

2. Crea una Access Entry para un rol de IAM:

```bash
aws eks create-access-entry \
  --cluster-name my-cluster \
  --principal-arn arn:aws:iam::123456789012:role/MyRole \
  --username my-role \
  --kubernetes-groups system:masters
```

3. Crea una Access Entry para un usuario de IAM:

```bash
aws eks create-access-entry \
  --cluster-name my-cluster \
  --principal-arn arn:aws:iam::123456789012:user/my-user \
  --username my-user \
  --kubernetes-groups system:masters
```

4. Lista las Access Entries:

```bash
aws eks list-access-entries --cluster-name my-cluster
```

5. Describe los detalles de la Access Entry:

```bash
aws eks describe-access-entry \
  --cluster-name my-cluster \
  --principal-arn arn:aws:iam::123456789012:user/my-user
```

#### Método 2: aws-auth ConfigMap (heredado)

El aws-auth ConfigMap es el método tradicional y sigue siendo compatible, pero se recomienda usar Access Entry para los nuevos clusters.

1. Obtén el ConfigMap `aws-auth` actual:

```bash
kubectl get configmap aws-auth -n kube-system -o yaml > aws-auth.yaml
```

2. Edita el archivo `aws-auth.yaml` para agregar usuarios o roles:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: aws-auth
  namespace: kube-system
data:
  mapRoles: |
    - rolearn: arn:aws:iam::123456789012:role/EKSNodeRole
      username: system:node:{{EC2PrivateDNSName}}
      groups:
        - system:bootstrappers
        - system:nodes
    # Additional role
    - rolearn: arn:aws:iam::123456789012:role/MyRole
      username: my-role
      groups:
        - system:masters
  mapUsers: |
    # IAM user
    - userarn: arn:aws:iam::123456789012:user/my-user
      username: my-user
      groups:
        - system:masters
```

3. Aplica el ConfigMap actualizado:

```bash
kubectl apply -f aws-auth.yaml
```

> **Nota**: EKS Access Entry se introdujo en 2023, y se recomienda usar Access Entry para los nuevos clusters. Los clusters existentes se pueden migrar a un modo híbrido que admite ambos métodos.

### Configuración de RBAC

Puedes controlar el acceso a los recursos dentro del cluster mediante Kubernetes Role-Based Access Control (RBAC).

1. Crea un namespace:

```bash
kubectl create namespace dev
```

2. Crea un rol:

```yaml
# role.yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  namespace: dev
  name: developer
rules:
- apiGroups: [""]
  resources: ["pods", "services", "configmaps", "secrets"]
  verbs: ["get", "list", "watch", "create", "update", "patch", "delete"]
- apiGroups: ["apps"]
  resources: ["deployments", "statefulsets", "daemonsets"]
  verbs: ["get", "list", "watch", "create", "update", "patch", "delete"]
```

```bash
kubectl apply -f role.yaml
```

3. Crea un role binding:

```yaml
# rolebinding.yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: developer-binding
  namespace: dev
subjects:
- kind: User
  name: my-user
  apiGroup: rbac.authorization.k8s.io
roleRef:
  kind: Role
  name: developer
  apiGroup: rbac.authorization.k8s.io
```

```bash
kubectl apply -f rolebinding.yaml
```

## Validación del cluster

Después de crear un cluster de EKS, debes verificar que funcione correctamente. En esta sección, aprenderemos a validar el cluster.

### Proceso de validación del cluster

![Diagrama de validación del cluster que comprueba los nodes y los Pods del sistema, implementa y expone una aplicación de prueba, y luego revisa los logs.](../.gitbook/assets/en-eks-02-eks-cluster-creation-part5-2.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-02-eks-cluster-creation-part5-2.html)

### Verificar los nodes

Verifica los nodes en el cluster:

```bash
kubectl get nodes
```

Verifica que todos los nodes estén en estado `Ready`.

### Verificar los Pods del sistema

Verifica los Pods en el namespace kube-system:

```bash
kubectl get pods -n kube-system
```

Verifica que todos los Pods del sistema estén en estado `Running`.

### Implementar una aplicación de prueba

Implementa una aplicación de prueba sencilla para verificar que el cluster funcione correctamente:

```yaml
# nginx.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: nginx
spec:
  replicas: 3
  selector:
    matchLabels:
      app: nginx
  template:
    metadata:
      labels:
        app: nginx
    spec:
      containers:
      - name: nginx
        image: nginx:latest
        ports:
        - containerPort: 80
---
apiVersion: v1
kind: Service
metadata:
  name: nginx
spec:
  type: LoadBalancer
  ports:
  - port: 80
    targetPort: 80
  selector:
    app: nginx
```

```bash
kubectl apply -f nginx.yaml
```

Verifica el estado del Deployment y el Service:

```bash
kubectl get deployments
kubectl get pods
kubectl get services
```

Verifica que puedas acceder a la aplicación mediante la IP externa del Service LoadBalancer:

```bash
curl http://<EXTERNAL-IP>
```

### Verificar los logs del cluster

Verifica los logs del cluster en CloudWatch Logs:

```bash
aws logs describe-log-groups \
  --log-group-name-prefix /aws/eks/my-cluster
```

## Actualización del cluster

Para mantener actualizado un cluster de EKS, se requieren actualizaciones periódicas. En esta sección, aprenderemos a actualizar un cluster.

### Proceso de actualización del cluster

![Diagrama del proceso de actualización, desde la planificación y las comprobaciones de versión hasta el control plane, los node groups, los add-ons y las pruebas de funciones.](../.gitbook/assets/en-eks-02-eks-cluster-creation-part5-3.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-02-eks-cluster-creation-part5-3.html)

### Actualización del control plane

Para actualizar el control plane de EKS, sigue estos pasos:

1. Comprueba las versiones de Kubernetes disponibles:

```bash
aws eks describe-addon-versions \
  --kubernetes-version 1.27 \
  --query "addons[].addonVersions[].compatibilities[].clusterVersion"
```

2. Actualiza el cluster:

```bash
aws eks update-cluster-version \
  --name my-cluster \
  --kubernetes-version 1.27
```

3. Comprueba el estado de la actualización:

```bash
aws eks describe-update \
  --name my-cluster \
  --update-id <UPDATE-ID>
```

### Actualización de nodes

Después de actualizar el control plane, también se deben actualizar los nodes:

#### Actualización de Managed Node Group

```bash
aws eks update-nodegroup-version \
  --cluster-name my-cluster \
  --nodegroup-name my-nodegroup
```

#### Actualización de Self-Managed Node

Para los nodes autogestionados, debes crear un nuevo node group, migrar las cargas de trabajo y luego eliminar el node group anterior.

### Actualización de add-ons

Para actualizar los add-ons de EKS, sigue estos pasos:

1. Comprueba las versiones de add-ons disponibles:

```bash
aws eks describe-addon-versions \
  --addon-name vpc-cni \
  --kubernetes-version 1.27
```

2. Actualiza el add-on:

```bash
aws eks update-addon \
  --cluster-name my-cluster \
  --addon-name vpc-cni \
  --addon-version <VERSION>
```

## Eliminación del cluster

Cuando ya no se necesita un cluster de EKS, puedes eliminarlo para ahorrar costos. En esta sección, aprenderemos a eliminar un cluster.

### Proceso de eliminación del cluster

![Diagrama del proceso de eliminación que borra los load balancers y los PVC, elimina los node groups y los perfiles de Fargate, luego el cluster y finalmente comprueba los recursos restantes.](../.gitbook/assets/en-eks-02-eks-cluster-creation-part5-4.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-02-eks-cluster-creation-part5-4.html)

### Limpieza de recursos

Antes de eliminar un cluster, debes limpiar todos los recursos creados en él:

1. Elimina los Services de LoadBalancer:

```bash
kubectl get services --all-namespaces -o json | jq -r '.items[] | select(.spec.type == "LoadBalancer") | .metadata.name + " " + .metadata.namespace' | while read name namespace; do
  kubectl delete service $name -n $namespace
done
```

2. Elimina PersistentVolumeClaims:

```bash
kubectl delete pvc --all --all-namespaces
```

### Eliminar el cluster mediante eksctl

Si creaste el cluster mediante eksctl, puedes eliminarlo con el siguiente comando:

```bash
eksctl delete cluster --name my-cluster --region us-west-2
```

### Eliminar el cluster mediante AWS CLI

Para eliminar un cluster mediante AWS CLI, sigue estos pasos:

1. Elimina el node group:

```bash
aws eks delete-nodegroup \
  --cluster-name my-cluster \
  --nodegroup-name my-nodegroup
```

2. Elimina el perfil de Fargate:

```bash
aws eks delete-fargate-profile \
  --cluster-name my-cluster \
  --fargate-profile-name my-fargate-profile
```

3. Elimina el cluster:

```bash
aws eks delete-cluster \
  --name my-cluster
```

### Limpiar los recursos relacionados

Después de eliminar el cluster de EKS, pueden permanecer los siguientes recursos relacionados:

1. VPC y recursos relacionados:

```bash
aws ec2 delete-vpc --vpc-id vpc-xxxxxxxxxxxxxxxxx
```

2. Roles y políticas de IAM:

```bash
aws iam detach-role-policy \
  --role-name EKSClusterRole \
  --policy-arn arn:aws:iam::aws:policy/AmazonEKSClusterPolicy

aws iam delete-role --role-name EKSClusterRole

aws iam detach-role-policy \
  --role-name EKSNodeRole \
  --policy-arn arn:aws:iam::aws:policy/AmazonEKSWorkerNodePolicy

aws iam detach-role-policy \
  --role-name EKSNodeRole \
  --policy-arn arn:aws:iam::aws:policy/AmazonEKS_CNI_Policy

aws iam detach-role-policy \
  --role-name EKSNodeRole \
  --policy-arn arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly

aws iam delete-role --role-name EKSNodeRole
```

3. Grupos de logs de CloudWatch:

```bash
aws logs delete-log-group \
  --log-group-name /aws/eks/my-cluster/cluster
```

## Cuestionario

Para poner a prueba lo que aprendiste en este capítulo, intenta el [Cuestionario sobre la creación de clusters de EKS - Parte 5](../quizzes/eks/02-eks-cluster-creation-part5-quiz.md).
