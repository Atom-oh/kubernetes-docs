# Guía de laboratorio de creación de cluster EKS

> **Dificultad**: Intermedio
> **Tiempo estimado**: 60 minutos
> **Última actualización**: February 11, 2026

## Objetivos de aprendizaje
- Crear un cluster EKS usando eksctl
- Acceder al cluster con kubectl y comprobar su estado
- Desplegar una aplicación de ejemplo
- Eliminar el cluster de forma segura

## Requisitos previos
- [ ] Cuenta de AWS y AWS CLI configurada (verificar con `aws sts get-caller-identity`)
- [ ] eksctl instalado (verificar con `eksctl version`)
- [ ] kubectl instalado
- [ ] Haber completado el aprendizaje de [Creación de cluster EKS](../../eks/02-eks-cluster-creation-part1.md)

> **Advertencia de coste**: Operar un cluster EKS genera costes de AWS. Asegúrate de eliminar el cluster después de completar el laboratorio.

---

## Ejercicio 1: Verificación de la configuración de eksctl

### Pasos

**Paso 1.1: Comprobar versiones de herramientas**
```bash
aws --version
eksctl version
kubectl version --client
```

**Paso 1.2: Verificar credenciales de AWS**
```bash
aws sts get-caller-identity
```

Salida esperada:
```json
{
    "UserId": "AIDACKCEVSQ6C2EXAMPLE",
    "Account": "123456789012",
    "Arn": "arn:aws:iam::123456789012:user/your-user"
}
```

**Paso 1.3: Establecer la región predeterminada**
```bash
export AWS_DEFAULT_REGION=ap-northeast-2
echo "Region: $AWS_DEFAULT_REGION"
```

<details>
<summary>¿Necesitas una pista?</summary>

- Usa `aws configure list` para comprobar la configuración actual
- eksctl usa CloudFormation internamente
- El usuario de IAM necesita permisos de EKS, EC2, CloudFormation e IAM
</details>

---

## Ejercicio 2: Creación de cluster EKS

### Pasos

**Paso 2.1: Escribir archivo de configuración del cluster**
```bash
cat > /tmp/eks-cluster.yaml << 'EOF'
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: lab-cluster
  region: ap-northeast-2
  version: "1.31"
managedNodeGroups:
  - name: workers
    instanceType: t3.medium
    desiredCapacity: 2
    minSize: 1
    maxSize: 3
    volumeSize: 20
EOF
```

**Paso 2.2: Crear cluster**
```bash
eksctl create cluster -f /tmp/eks-cluster.yaml
```

> La creación del cluster tarda 15-20 minutos.

**Paso 2.3: Verificar kubeconfig**
```bash
kubectl config current-context
kubectl cluster-info
```

### Verificación
```bash
kubectl get nodes
# Should display 2 Ready nodes
```

---

## Ejercicio 3: Exploración del cluster

### Pasos

**Paso 3.1: Comprobar información de los nodes**
```bash
kubectl get nodes -o wide
kubectl describe node $(kubectl get nodes -o jsonpath='{.items[0].metadata.name}')
```

**Paso 3.2: Comprobar componentes del sistema**
```bash
kubectl get pods -n kube-system
kubectl get svc -n kube-system
```

**Paso 3.3: Comprobar uso de recursos**
```bash
kubectl top nodes 2>/dev/null || echo "Metrics Server is not installed"
```

---

## Ejercicio 4: Despliegue de aplicación de ejemplo

### Pasos

**Paso 4.1: Desplegar Nginx**
```bash
kubectl create deployment nginx --image=nginx:1.25 --replicas=2
kubectl expose deployment nginx --port=80 --type=LoadBalancer
kubectl wait --for=condition=available deployment/nginx --timeout=120s
```

**Paso 4.2: Verificar acceso**
```bash
# Check LoadBalancer External IP (ELB creation takes a few minutes)
kubectl get svc nginx -w
# Press Ctrl+C once EXTERNAL-IP is assigned

# Test access
ELB_URL=$(kubectl get svc nginx -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')
echo "ELB URL: $ELB_URL"
curl -s "$ELB_URL" | head -5
```

**Paso 4.3: Prueba de escalado**
```bash
kubectl scale deployment nginx --replicas=4
kubectl get pods -l app=nginx -o wide
```

<details>
<summary>¿Necesitas una pista?</summary>

- La URL del ELB puede tardar unos minutos en propagarse a través de DNS
- Usa `kubectl get svc -w` para monitorizar la asignación de EXTERNAL-IP en tiempo real
- También puedes verificarlo en AWS Console en EC2 > Load Balancers
</details>

### Verificación
```bash
kubectl get deployment nginx -o jsonpath='{.status.readyReplicas}'
# Output: 4
```

---

## Limpieza

> **Importante**: Asegúrate de eliminar el cluster para evitar costes continuos.

```bash
# 1. Clean up application (so LoadBalancer deletes the ELB)
kubectl delete svc nginx
kubectl delete deployment nginx

# 2. Wait for ELB deletion (about 1 minute)
sleep 60

# 3. Delete cluster
eksctl delete cluster -f /tmp/eks-cluster.yaml --wait

# 4. Clean up configuration file
rm -f /tmp/eks-cluster.yaml
```

## Solución de problemas

<details>
<summary>La creación del cluster falla</summary>

- Comprueba los permisos de IAM (se requiere AdministratorAccess o políticas relacionadas con EKS)
- Comprueba los límites de VPC/subnet (límites de recuento de VPC predeterminadas por región)
- Obtén detalles con `eksctl utils describe-stacks --region=ap-northeast-2 --cluster=lab-cluster`
</details>

<details>
<summary>kubectl no puede conectarse al cluster</summary>

Actualiza kubeconfig manualmente:
```bash
aws eks update-kubeconfig --name lab-cluster --region ap-northeast-2
```
</details>

## Siguientes pasos
- [Cuestionario de creación de cluster EKS](../../quizzes/eks/02-eks-cluster-creation-part1-quiz.md)
- Temas avanzados: [Networking de EKS](../../eks/03-eks-networking-part1.md)
