# Parte 1: Requisitos previos

Hay varias formas de crear un clúster de Amazon EKS. En este capítulo, aprenderemos a crear un clúster de EKS utilizando diversas herramientas y métodos.

## Tabla de contenido

1. [Requisitos previos](02-eks-cluster-creation-part1.md#prerequisites)
2. [Creación de un clúster con eksctl](02-eks-cluster-creation-part1.md#creating-a-cluster-using-eksctl)
3. [Creación de un clúster con AWS Management Console](02-eks-cluster-creation-part1.md#creating-a-cluster-using-aws-management-console)
4. [Creación de un clúster con AWS CLI](02-eks-cluster-creation-part1.md#creating-a-cluster-using-aws-cli)
5. [Creación de un clúster con Terraform](02-eks-cluster-creation-part1.md#creating-a-cluster-using-terraform)

## Requisitos previos

Antes de crear un clúster de EKS, se requieren los siguientes requisitos previos:

### 1. Cuenta de AWS

Se requiere una cuenta válida de AWS. Si no tiene una cuenta de AWS, puede registrarse en el [sitio web de AWS](https://aws.amazon.com/).

### 2. Permisos de IAM

Se requieren los siguientes permisos de IAM para crear y administrar un clúster de EKS:

* `eks:*`
* `ec2:*`
* `iam:*`
* `cloudformation:*`

Si tiene permisos de administrador, no se requieren configuraciones de permisos adicionales. De lo contrario, debe adjuntar la siguiente política de IAM al usuario o rol:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "eks:*",
        "ec2:*",
        "iam:*",
        "cloudformation:*"
      ],
      "Resource": "*"
    }
  ]
}
```

### 3. Instalación de herramientas

Se deben instalar las siguientes herramientas para crear y administrar un clúster de EKS:

#### AWS CLI

AWS CLI es una herramienta unificada para controlar los servicios de AWS desde la línea de comandos.

**macOS**:

```bash
curl "https://awscli.amazonaws.com/AWSCLIV2.pkg" -o "AWSCLIV2.pkg"
sudo installer -pkg AWSCLIV2.pkg -target /
```

**Linux**:

```bash
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install
```

**Windows**:

```
https://awscli.amazonaws.com/AWSCLIV2.msi
```

Después de instalar AWS CLI, ejecute el siguiente comando para configurar las credenciales:

```bash
aws configure
```

#### kubectl

kubectl es una herramienta de línea de comandos para comunicarse con clústeres de Kubernetes.

**macOS**:

```bash
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/darwin/amd64/kubectl"
chmod +x ./kubectl
sudo mv ./kubectl /usr/local/bin/kubectl
```

**Linux**:

```bash
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
chmod +x ./kubectl
sudo mv ./kubectl /usr/local/bin/kubectl
```

**Windows**:

```bash
curl -LO "https://dl.k8s.io/release/v1.26.0/bin/windows/amd64/kubectl.exe"
```

#### eksctl

eksctl es una herramienta CLI sencilla para crear y administrar clústeres de EKS.

**macOS**:

```bash
brew tap weaveworks/tap
brew install weaveworks/tap/eksctl
```

O:

```bash
curl --silent --location "https://github.com/weaveworks/eksctl/releases/latest/download/eksctl_$(uname -s)_amd64.tar.gz" | tar xz -C /tmp
sudo mv /tmp/eksctl /usr/local/bin
```

**Linux**:

```bash
curl --silent --location "https://github.com/weaveworks/eksctl/releases/latest/download/eksctl_$(uname -s)_amd64.tar.gz" | tar xz -C /tmp
sudo mv /tmp/eksctl /usr/local/bin
```

**Windows**:

```bash
# PowerShell
$version = (Invoke-WebRequest -Uri "https://api.github.com/repos/weaveworks/eksctl/releases/latest" | ConvertFrom-Json).tag_name
Invoke-WebRequest -Uri "https://github.com/weaveworks/eksctl/releases/download/$version/eksctl_Windows_amd64.zip" -OutFile eksctl.zip
Expand-Archive -Path eksctl.zip -DestinationPath $env:USERPROFILE\.eksctl\bin
$env:PATH += ";$env:USERPROFILE\.eksctl\bin"
```

### 4. VPC y subredes

Un clúster de EKS requiere una VPC y subredes. Puede utilizar una VPC existente o crear una nueva. La VPC para un clúster de EKS debe cumplir los siguientes requisitos:

![Diagrama de arquitectura de VPC de EKS que ubica los balanceadores de carga en subredes públicas, las NAT Gateways y los nodos de trabajo en subredes privadas distribuidas en dos zonas de disponibilidad.](../.gitbook/assets/en-eks-02-eks-cluster-creation-part1-0.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-02-eks-cluster-creation-part1-0.html)

* Al menos 2 subredes deben estar en diferentes zonas de disponibilidad.
* Las subredes deben tener acceso a Internet (a través de una NAT gateway o Internet gateway).
* Las subredes deben tener suficientes direcciones IP.
* Las subredes deben tener las etiquetas adecuadas.

#### Etiquetas de VPC para el clúster de EKS

Se deben aplicar las siguientes etiquetas para que el clúster de EKS pueda utilizar correctamente la VPC y las subredes:

**Etiquetas de VPC**:

* `kubernetes.io/cluster/<cluster-name>`: `shared` or `owned`

**Etiquetas de subred pública**:

* `kubernetes.io/cluster/<cluster-name>`: `shared` or `owned`
* `kubernetes.io/role/elb`: `1`

**Etiquetas de subred privada**:

* `kubernetes.io/cluster/<cluster-name>`: `shared` or `owned`
* `kubernetes.io/role/internal-elb`: `1`

## Cuestionario

Para comprobar lo que aprendió en este capítulo, pruebe el [Cuestionario de creación de clúster de EKS - Parte 1](../quizzes/eks/02-eks-cluster-creation-part1-quiz.md).
