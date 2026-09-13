# Parte 2: Creación de clústeres con eksctl

## Creación de un clúster con eksctl

eksctl es la forma más sencilla de crear y administrar clústeres de EKS. eksctl utiliza CloudFormation para crear clústeres de EKS y recursos relacionados.

El siguiente diagrama muestra el proceso de creación de un clúster de EKS con eksctl:

![Diagrama del proceso de creación de clústeres con eksctl, que crea VPC, IAM, el control plane y el node group en orden mediante pilas de CloudFormation.](../.gitbook/assets/en-eks-02-eks-cluster-creation-part2-0.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-02-eks-cluster-creation-part2-0.html)

### Creación básica de clústeres

Para crear la forma más básica de un clúster de EKS, ejecute el siguiente comando:

```bash
eksctl create cluster --name my-cluster --region us-west-2
```

Este comando crea un clúster con la siguiente configuración predeterminada:

* 2 nodos m5.large
* VPC y subredes nuevas
* AMI predeterminada de Amazon Linux 2
* Última versión de Kubernetes

### Creación de un clúster mediante un archivo de configuración

Para configuraciones más complejas, puede definir el clúster mediante un archivo YAML:

```yaml
# cluster.yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig

metadata:
  name: my-eks-cluster
  region: us-west-2
  version: "1.26"

vpc:
  id: vpc-12345678
  subnets:
    private:
      us-west-2a:
        id: subnet-12345678
      us-west-2b:
        id: subnet-87654321
    public:
      us-west-2a:
        id: subnet-23456789
      us-west-2b:
        id: subnet-98765432

managedNodeGroups:
  - name: ng-1
    instanceType: m5.large
    desiredCapacity: 2
    minSize: 1
    maxSize: 3
    privateNetworking: true
    volumeSize: 80
    volumeType: gp3
    iam:
      withAddonPolicies:
        imageBuilder: true
        autoScaler: true
        externalDNS: true
        certManager: true
        appMesh: true
        ebs: true
        fsx: true
        efs: true
        albIngress: true
        xRay: true
        cloudWatch: true

  - name: ng-2
    instanceType: c5.xlarge
    desiredCapacity: 2
    privateNetworking: true
    spot: true

fargate:
  profiles:
    - name: fp-default
      selectors:
        - namespace: default
          labels:
            env: fargate
    - name: fp-kube-system
      selectors:
        - namespace: kube-system
          labels:
            k8s-app: kube-dns

cloudWatch:
  clusterLogging:
    enableTypes: ["api", "audit", "authenticator", "controllerManager", "scheduler"]
```

Para crear un clúster con este archivo de configuración, ejecute el siguiente comando:

```bash
eksctl create cluster -f cluster.yaml
```

### Creación de Managed Node Groups

El siguiente diagrama muestra la arquitectura de Managed Node Group para un clúster de EKS:

![Diagrama de arquitectura del control plane que administra un node group cuyo grupo de Auto Scaling inicia instancias de EC2 que ejecutan Pods.](../.gitbook/assets/en-eks-02-eks-cluster-creation-part2-1.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-02-eks-cluster-creation-part2-1.html)

Para agregar un Managed Node Group a un clúster existente, ejecute el siguiente comando:

```bash
eksctl create nodegroup \
  --cluster my-cluster \
  --region us-west-2 \
  --name my-nodegroup \
  --node-type m5.large \
  --nodes 3 \
  --nodes-min 1 \
  --nodes-max 5 \
  --ssh-access \
  --ssh-public-key my-key
```

O puede utilizar un archivo de configuración:

```yaml
# nodegroup.yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig

metadata:
  name: my-cluster
  region: us-west-2

managedNodeGroups:
  - name: my-nodegroup
    instanceType: m5.large
    desiredCapacity: 3
    minSize: 1
    maxSize: 5
    volumeSize: 80
    volumeType: gp3
    ssh:
      allow: true
      publicKeyName: my-key
```

```bash
eksctl create nodegroup -f nodegroup.yaml
```

### Creación de perfiles de Fargate

El siguiente diagrama muestra la arquitectura del perfil de Fargate de EKS:

![Diagrama de arquitectura que muestra Pods que coinciden con los selectores de namespace y etiquetas de un perfil de Fargate ubicados en microVM dedicadas.](../.gitbook/assets/en-eks-02-eks-cluster-creation-part2-2.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-02-eks-cluster-creation-part2-2.html)

Para crear un perfil de Fargate, ejecute el siguiente comando:

```bash
eksctl create fargateprofile \
  --cluster my-cluster \
  --region us-west-2 \
  --name my-fargate-profile \
  --namespace default \
  --labels env=fargate
```

O puede utilizar un archivo de configuración:

```yaml
# fargate.yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig

metadata:
  name: my-cluster
  region: us-west-2

fargate:
  profiles:
    - name: my-fargate-profile
      selectors:
        - namespace: default
          labels:
            env: fargate
```

```bash
eksctl create fargateprofile -f fargate.yaml
```

### Actualización de un clúster

Puede actualizar un clúster existente con eksctl:

```bash
# Upgrade cluster version
eksctl upgrade cluster --name=my-cluster --version=1.27

# Upgrade node group
eksctl upgrade nodegroup --cluster=my-cluster --name=my-nodegroup
```

### Eliminación de un clúster

Puede eliminar un clúster con eksctl:

```bash
eksctl delete cluster --name=my-cluster --region=us-west-2
```

## Administración del ciclo de vida del clúster de EKS

El siguiente diagrama muestra el proceso general de administración del ciclo de vida de un clúster de EKS:

![Diagrama del ciclo de vida de un clúster de EKS, desde la creación y configuración, pasando por las actualizaciones de versión, hasta la eliminación.](../.gitbook/assets/en-eks-02-eks-cluster-creation-part2-3.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-02-eks-cluster-creation-part2-3.html)

## Cuestionario

Para comprobar lo que aprendió en este capítulo, pruebe el [Cuestionario de creación de clústeres de EKS - Parte 2](../quizzes/eks/02-eks-cluster-creation-part2-quiz.md).
