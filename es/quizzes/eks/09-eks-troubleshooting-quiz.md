# Cuestionario de solución de problemas de Amazon EKS

Este cuestionario evalúa tu capacidad para diagnosticar y resolver diversos problemas que pueden ocurrir en clusters de Amazon EKS.

## Descripción general del cuestionario
- Problemas de creación y configuración de clusters
- Problemas de redes
- Problemas de Node y Pod
- Problemas de almacenamiento
- Problemas de seguridad y acceso
- Problemas de rendimiento y escalabilidad

## Preguntas de opción múltiple

### 1. ¿Qué deberías comprobar primero cuando falla la creación de un cluster de Amazon EKS?

A. Comprobar si el nombre del cluster es único
B. Comprobar los permisos de IAM, la configuración de VPC y las cuotas de servicio
C. Intentarlo de nuevo en una región diferente
D. Seleccionar un tipo de instancia más grande

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Comprobar los permisos de IAM, la configuración de VPC y las cuotas de servicio**

**Explicación:**
Cuando falla la creación de un cluster de Amazon EKS, lo primero que debes comprobar son los permisos de IAM, la configuración de VPC y las cuotas de servicio. Estos factores son las causas más comunes de fallos en la creación de clusters, y revisarlos sistemáticamente puede ayudar a identificar y resolver problemas con rapidez.

**Elementos clave para comprobar:**

1. **Comprobar permisos de IAM**:
   - Si tienes los permisos de IAM necesarios para crear el cluster
   - Permiso para crear service-linked roles
   - Configuración del rol y las políticas del cluster

2. **Comprobar configuración de VPC**:
   - Configuración de subnets (subnets distribuidas en al menos 2 availability zones)
   - Tamaño de CIDR de subnet (mínimo /28, recomendado /24)
   - Conectividad a Internet (NAT gateway o internet gateway)
   - Configuración de security group y network ACL

3. **Comprobar cuotas de servicio**:
   - Cuota de cantidad de clusters de EKS
   - Cuota de instancias EC2
   - Cuotas de VPC y subnet
   - Otras cuotas de servicios relacionados

**Métodos de solución de problemas:**

1. **Resolver problemas de permisos de IAM**:
   ```bash
   # Check IAM permissions
   aws sts get-caller-identity

   # Attach required policy
   aws iam attach-user-policy \
     --user-name myuser \
     --policy-arn arn:aws:iam::aws:policy/AmazonEKSClusterPolicy

   # Create service-linked role
   aws iam create-service-linked-role --aws-service-name eks.amazonaws.com
   ```

2. **Resolver problemas de configuración de VPC**:
   ```bash
   # Check VPC and subnets
   aws ec2 describe-vpcs --vpc-ids vpc-12345678
   aws ec2 describe-subnets --filters "Name=vpc-id,Values=vpc-12345678"

   # Check subnet tags
   aws ec2 describe-tags --filters "Name=resource-id,Values=subnet-12345678"

   # Add subnet tags
   aws ec2 create-tags \
     --resources subnet-12345678 subnet-87654321 \
     --tags Key=kubernetes.io/cluster/my-cluster,Value=shared
   ```

3. **Resolver problemas de cuotas de servicio**:
   ```bash
   # Check service quotas
   aws service-quotas list-service-quotas --service-code eks

   # Request quota increase
   aws service-quotas request-service-quota-increase \
     --service-code eks \
     --quota-code L-1194D53C \
     --desired-value 10
   ```

**Mensajes de error comunes y soluciones:**

1. **Permisos de IAM insuficientes**:
   - Error: "User: arn:aws:iam::123456789012:user/myuser is not authorized to perform: eks:CreateCluster"
   - Solución: Añadir los permisos de IAM necesarios

2. **Problemas de VPC subnet**:
   - Error: "Cannot create cluster 'my-cluster' because us-west-2a, the targeted availability zone, does not have sufficient capacity to support the cluster. Retry after some time or try other availability zones."
   - Solución: Usar subnets en availability zones diferentes o crear subnets nuevas

3. **Cuota de servicio excedida**:
   - Error: "Account cannot create more EKS clusters in region us-west-2. Current limit is 5"
   - Solución: Solicitar un aumento de cuota de servicio o eliminar clusters innecesarios

**Buenas prácticas:**

1. **Preparación previa a la creación del cluster**:
   - Verificar los permisos de IAM requeridos
   - Configurar una VPC y subnets adecuadas
   - Comprobar las cuotas de servicio

2. **Enfoque sistemático de solución de problemas**:
   - Analizar los mensajes de error
   - Comprobar los logs de AWS CloudTrail
   - Verificación paso a paso de los componentes

3. **Configuración automatizada de infraestructura**:
   - Usar AWS CloudFormation o Terraform
   - Utilizar herramientas como eksctl
   - Controlar versiones de la configuración de infraestructura

**Ejemplos prácticos de implementación:**

1. **Solución de problemas de creación de cluster con eksctl**:
   ```bash
   # Create cluster in debug mode
   eksctl create cluster --name my-cluster --region us-west-2 --verbose 4

   # Check cluster creation status
   eksctl get cluster --name my-cluster --region us-west-2
   ```

2. **Solución de problemas de creación de cluster con AWS CLI**:
   ```bash
   # Attempt cluster creation
   aws eks create-cluster \
     --name my-cluster \
     --role-arn arn:aws:iam::123456789012:role/eks-cluster-role \
     --resources-vpc-config subnetIds=subnet-12345678,subnet-87654321,securityGroupIds=sg-12345678

   # Check cluster status
   aws eks describe-cluster --name my-cluster
   ```

3. **Solución de problemas de creación de cluster con Terraform**:
   ```hcl
   # EKS cluster definition
   resource "aws_eks_cluster" "main" {
     name     = "my-cluster"
     role_arn = aws_iam_role.eks_cluster.arn

     vpc_config {
       subnet_ids         = var.subnet_ids
       security_group_ids = [aws_security_group.eks_cluster.id]
     }

     # Explicit dependencies
     depends_on = [
       aws_iam_role_policy_attachment.eks_cluster_policy,
       aws_iam_role_policy_attachment.eks_service_policy
     ]
   }

   # Debug output on error
   output "cluster_status" {
     value = aws_eks_cluster.main.status
   }
   ```

Problemas con las otras opciones:
- **A. Comprobar si el nombre del cluster es único**: Aunque un nombre de cluster no único puede causar errores, no es la causa más común de fallo.
- **C. Intentarlo de nuevo en una región diferente**: Esto es una solución temporal que no resuelve la causa raíz, y el mismo problema puede ocurrir en otras regiones.
- **D. Seleccionar un tipo de instancia más grande**: El tipo de instancia aplica a node groups y no afecta a la creación del cluster en sí.
</details>
### 2. ¿Cuál es el enfoque de solución de problemas más efectivo cuando un Node está en estado NotReady en un cluster de Amazon EKS?

A. Terminar y reemplazar inmediatamente el Node
B. Comprobar los logs del Node, el uso de recursos y la conectividad de red
C. Reiniciar el cluster API server
D. Eliminar y volver a desplegar todos los Pods

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Comprobar los logs del Node, el uso de recursos y la conectividad de red**

**Explicación:**
Cuando un Node está en estado NotReady en un cluster de Amazon EKS, el enfoque de solución de problemas más efectivo es comprobar los logs del Node, el uso de recursos y la conectividad de red. Este enfoque sistemático ayuda a identificar la causa raíz del problema y aplicar las soluciones adecuadas.

**Elementos clave para comprobar:**

1. **Comprobar el estado y los eventos del Node**:
   - Detalles del estado del Node
   - Eventos relacionados con el Node
   - Condiciones del Node

2. **Analizar logs del Node**:
   - Logs de kubelet
   - Logs del sistema
   - Logs del container runtime

3. **Comprobar uso de recursos**:
   - Uso de CPU, memoria y disco
   - Límites de recursos y presión
   - Estado de procesos del sistema

4. **Comprobar conectividad de red**:
   - Conexión con el control plane
   - Resolución DNS
   - Configuración de VPC y subnet

**Métodos de solución de problemas:**

1. **Comprobar estado y eventos del Node**:
   ```bash
   # Check node status
   kubectl get nodes
   kubectl describe node <node-name>

   # Check node events
   kubectl get events --field-selector involvedObject.name=<node-name>
   ```

2. **Analizar logs del Node**:
   ```bash
   # SSH access to node (for self-managed nodes)
   ssh ec2-user@<node-ip>

   # Check kubelet logs
   sudo journalctl -u kubelet

   # Check system logs
   sudo tail -f /var/log/syslog

   # Check container runtime logs
   sudo journalctl -u docker  # When using Docker
   sudo journalctl -u containerd  # When using containerd
   ```

3. **Comprobar uso de recursos**:
   ```bash
   # Check node resource usage
   kubectl top node <node-name>

   # Check resources via SSH
   ssh ec2-user@<node-ip>

   # Check disk usage
   df -h

   # Check memory usage
   free -m

   # Check CPU usage
   top
   ```

4. **Comprobar conectividad de red**:
   ```bash
   # Check API server connection from node
   curl -k https://<api-server-endpoint>

   # Check DNS resolution
   nslookup kubernetes.default.svc.cluster.local

   # Check network interfaces
   ip addr show

   # Check routing table
   ip route
   ```

**Causas comunes de NotReady y soluciones:**

1. **Problemas de kubelet**:
   - **Síntoma**: El servicio kubelet no está en ejecución o no puede conectarse al API server
   - **Solución**:
     ```bash
     # Check kubelet service status
     sudo systemctl status kubelet

     # Restart kubelet service
     sudo systemctl restart kubelet

     # Check kubelet configuration
     sudo cat /etc/kubernetes/kubelet/kubelet-config.json
     ```

2. **Problemas de red**:
   - **Síntoma**: El Node no puede comunicarse con el control plane
   - **Solución**:
     ```bash
     # Check security groups
     aws ec2 describe-security-groups --group-ids sg-12345678

     # Check routing tables
     aws ec2 describe-route-tables --route-table-ids rtb-12345678

     # Check VPC CNI pod status
     kubectl get pods -n kube-system -l k8s-app=aws-node
     kubectl logs -n kube-system -l k8s-app=aws-node
     ```

3. **Escasez de recursos**:
   - **Síntoma**: CPU, memoria o espacio en disco insuficientes en el Node
   - **Solución**:
     ```bash
     # Free up disk space
     sudo du -sh /var/log/*
     sudo journalctl --vacuum-time=1d

     # Clean up unnecessary containers and images
     docker system prune -af  # When using Docker
     ```

4. **Problemas de certificados**:
   - **Síntoma**: Certificado expirado o discrepancia de certificado
   - **Solución**:
     ```bash
     # Check certificates
     sudo ls -la /etc/kubernetes/pki/

     # Renew certificates (for self-managed nodes)
     sudo kubeadm alpha certs renew all

     # For managed node groups, replace nodes
     eksctl replace nodegroup --cluster=my-cluster --name=my-nodegroup
     ```

**Buenas prácticas:**

1. **Enfoque sistemático de solución de problemas**:
   - Identificar y documentar síntomas
   - Recopilar logs y eventos relevantes
   - Verificar sistemáticamente las posibles causas

2. **Implementar monitorización del estado del Node**:
   - Configurar alarmas de CloudWatch
   - Configurar dashboards de estado de Node
   - Sistema de alertas automatizado

3. **Implementar mecanismos de recuperación automática**:
   - Configurar node groups con self-healing
   - Health checks y reemplazo automático
   - Draining automático de Nodes fallidos

**Ejemplos prácticos de implementación:**

1. **Script de solución de problemas de Node**:
   ```bash
   #!/bin/bash
   # EKS node troubleshooting script

   NODE_NAME=$1

   if [ -z "$NODE_NAME" ]; then
     echo "Please specify a node name."
     exit 1
   fi

   echo "=== Troubleshooting node $NODE_NAME ==="

   # Check node status
   echo "=== Check node status ==="
   kubectl get node $NODE_NAME -o wide
   kubectl describe node $NODE_NAME

   # Check node events
   echo
   echo "=== Check node events ==="
   kubectl get events --field-selector involvedObject.name=$NODE_NAME --sort-by='.lastTimestamp'

   # Check node pods
   echo
   echo "=== Check node pods ==="
   kubectl get pods --all-namespaces -o wide --field-selector spec.nodeName=$NODE_NAME

   # Check system pod logs
   echo
   echo "=== Check system pod logs ==="
   NODE_IP=$(kubectl get node $NODE_NAME -o jsonpath='{.status.addresses[?(@.type=="InternalIP")].address}')
   KUBE_PROXY_POD=$(kubectl get pods -n kube-system -l k8s-app=kube-proxy -o wide | grep $NODE_IP | awk '{print $1}')
   AWS_NODE_POD=$(kubectl get pods -n kube-system -l k8s-app=aws-node -o wide | grep $NODE_IP | awk '{print $1}')

   if [ -n "$KUBE_PROXY_POD" ]; then
     echo "kube-proxy logs:"
     kubectl logs -n kube-system $KUBE_PROXY_POD --tail=50
   fi

   if [ -n "$AWS_NODE_POD" ]; then
     echo
     echo "aws-node (VPC CNI) logs:"
     kubectl logs -n kube-system $AWS_NODE_POD --tail=50
   fi

   # Node access instructions
   echo
   echo "=== Node access instructions ==="
   echo "To access the node directly, use the following command:"
   echo "aws ssm start-session --target <instance-id>"
   echo "or"
   echo "ssh ec2-user@$NODE_IP  # SSH key and security group configuration required"

   echo
   echo "=== Troubleshooting complete ==="
   ```

2. **Configuración de node group con self-healing usando Terraform**:
   ```hcl
   # Self-healing node group
   resource "aws_eks_node_group" "self_healing" {
     cluster_name    = aws_eks_cluster.main.name
     node_group_name = "self-healing"
     node_role_arn   = aws_iam_role.node_role.arn
     subnet_ids      = var.private_subnet_ids

     scaling_config {
       desired_size = 3
       min_size     = 3
       max_size     = 6
     }

     # Self-healing settings
     update_config {
       max_unavailable = 1
     }

     # Health check settings
     health_check {
       type = "EKS"
     }

     # Auto scaling group tags
     tags = {
       "k8s.io/cluster-autoscaler/enabled" = "true"
       "k8s.io/cluster-autoscaler/${aws_eks_cluster.main.name}" = "owned"
     }
   }
   ```

3. **Alarmas de CloudWatch y configuración de recuperación automatizada**:
   ```bash
   # Create CloudWatch alarm
   aws cloudwatch put-metric-alarm \
     --alarm-name EKS-Node-NotReady \
     --metric-name NodeNotReady \
     --namespace AWS/EKS \
     --statistic Maximum \
     --period 60 \
     --threshold 0 \
     --comparison-operator GreaterThanThreshold \
     --dimensions Name=ClusterName,Value=my-cluster \
     --evaluation-periods 3 \
     --alarm-actions arn:aws:sns:us-west-2:123456789012:eks-alerts

   # Automated recovery using AWS Lambda function
   aws lambda create-function \
     --function-name EKS-Node-Recovery \
     --runtime python3.9 \
     --role arn:aws:iam::123456789012:role/EKS-Node-Recovery-Role \
     --handler index.handler \
     --zip-file fileb://node-recovery.zip
   ```

Problemas con las otras opciones:
- **A. Terminar y reemplazar inmediatamente el Node**: Reemplazar el Node sin identificar la causa raíz puede provocar el mismo problema en el nuevo Node, y se pierde información diagnóstica.
- **C. Reiniciar el cluster API server**: El API server no está directamente relacionado con el estado del Node, y reiniciarlo puede afectar a todo el cluster.
- **D. Eliminar y volver a desplegar todos los Pods**: Eliminar Pods no solucionará problemas del Node en sí y puede causar una interrupción innecesaria del servicio.
</details>
### 3. ¿Cuál es la causa y la solución más probables cuando un Pod está en estado "ImagePullBackOff" en un cluster de Amazon EKS?

A. Límite de recursos del Pod excedido / Aumentar los límites de recursos
B. Error en el nombre de la imagen o problema de autenticación / Verificar el nombre de la imagen y configurar image pull secrets
C. Escasez de espacio en disco del Node / Liberar espacio en disco
D. Restricciones de network policy / Modificar network policies

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Error en el nombre de la imagen o problema de autenticación / Verificar el nombre de la imagen y configurar image pull secrets**

**Explicación:**
Cuando un Pod está en estado "ImagePullBackOff" en un cluster de Amazon EKS, la causa más probable es un error en el nombre de la imagen o un problema de autenticación. Para resolverlo, debes verificar el nombre de la imagen y configurar image pull secrets si es necesario.

**Causas principales y soluciones:**

1. **Error en el nombre de la imagen**:
   - Nombre de imagen o tag incorrecto
   - Imagen inexistente
   - Error en la URL del registry

   **Solución**:
   ```bash
   # Check pod definition
   kubectl describe pod <pod-name>

   # Fix image name and tag
   kubectl edit deployment <deployment-name>
   # or
   kubectl set image deployment/<deployment-name> container-name=image:tag
   ```

2. **Problemas de autenticación en registry privado**:
   - Credenciales de autenticación faltantes
   - Credenciales expiradas
   - Permisos insuficientes

   **Solución**:
   ```bash
   # Create Docker registry secret
   kubectl create secret docker-registry regcred \
     --docker-server=<registry-server> \
     --docker-username=<username> \
     --docker-password=<password> \
     --docker-email=<email>

   # Link secret to pod or service account
   kubectl patch serviceaccount default -p '{"imagePullSecrets": [{"name": "regcred"}]}'
   # or
   kubectl patch pod <pod-name> -p '{"spec":{"imagePullSecrets":[{"name":"regcred"}]}}'
   ```

3. **Problemas de autenticación de Amazon ECR**:
   - Permisos de ECR insuficientes
   - Token expirado
   - Problemas de acceso entre cuentas

   **Solución**:
   ```bash
   # Get ECR authentication token
   aws ecr get-login-password --region us-west-2 | docker login --username AWS --password-stdin 123456789012.dkr.ecr.us-west-2.amazonaws.com

   # Create ECR pull secret
   TOKEN=$(aws ecr get-authorization-token --output text --query 'authorizationData[].authorizationToken')
   echo $TOKEN | base64 -d | cut -d: -f2 > password.txt

   kubectl create secret docker-registry ecr-secret \
     --docker-server=123456789012.dkr.ecr.us-west-2.amazonaws.com \
     --docker-username=AWS \
     --docker-password="$(cat password.txt)" \
     --docker-email=no-reply@example.com

   rm password.txt
   ```

4. **Problemas de conectividad de red**:
   - Acceso de red restringido al registry
   - Problemas de resolución DNS
   - Problemas de configuración de proxy

   **Solución**:
   ```bash
   # Check registry connection from node
   ssh ec2-user@<node-ip>
   curl -v https://<registry-url>

   # Check DNS resolution
   nslookup <registry-url>

   # Configure VPC endpoint for private registry
   aws ec2 create-vpc-endpoint \
     --vpc-id vpc-12345678 \
     --service-name com.amazonaws.us-west-2.ecr.dkr \
     --vpc-endpoint-type Interface \
     --subnet-ids subnet-12345678 \
     --security-group-ids sg-12345678
   ```

**Pasos de solución de problemas:**

1. **Comprobar estado y eventos del Pod**:
   ```bash
   # Check pod status
   kubectl get pod <pod-name>

   # Check pod details and events
   kubectl describe pod <pod-name>
   ```

2. **Verificar nombre de imagen y registry**:
   ```bash
   # Check image name
   kubectl get pod <pod-name> -o jsonpath='{.spec.containers[0].image}'

   # Verify image exists
   docker pull <image-name>  # In local environment
   # or
   aws ecr describe-images \
     --repository-name <repository-name> \
     --image-ids imageTag=<tag>  # For ECR
   ```

3. **Comprobar configuración de autenticación**:
   ```bash
   # Check service account and image pull secrets
   kubectl get serviceaccount default -o yaml

   # Check secret contents
   kubectl get secret <secret-name> -o yaml
   ```

4. **Aplicar solución temporal**:
   ```bash
   # Pull image locally and transfer to node (for emergencies)
   docker pull <image-name>
   docker save <image-name> -o image.tar
   scp image.tar ec2-user@<node-ip>:~/
   ssh ec2-user@<node-ip> "docker load -i image.tar"
   ```

**Buenas prácticas:**

1. **Gestión de tags de imagen**:
   - Usar digests en lugar de tags específicos
   - Evitar usar el tag `latest`
   - Implementar una estrategia de gestión de versiones

2. **Gestión de image pull secrets**:
   - Vincular secrets a service accounts
   - Renovación periódica de secrets
   - Automatizar la gestión de secrets

3. **Garantizar accesibilidad del registry de imágenes**:
   - Configurar VPC endpoints para registries privados
   - Configurar network policies y security groups
   - Considerar el caching de imágenes

4. **Buenas prácticas al usar ECR**:
   - Usar autenticación basada en IAM roles
   - Implementar renovación automática de tokens
   - Configurar image scanning y lifecycle policies

Problemas con las otras opciones:
- **A. Límite de recursos del Pod excedido / Aumentar los límites de recursos**: Los problemas de límites de recursos suelen causar estados "OOMKilled" o "Pending", no "ImagePullBackOff".
- **C. Escasez de espacio en disco del Node / Liberar espacio en disco**: Aunque la escasez de espacio en disco puede causar "ImagePullBackOff", los errores relacionados con el espacio en disco suelen aparecer en los eventos del Node y no son la causa más común.
- **D. Restricciones de network policy / Modificar network policies**: Las network policies afectan la comunicación entre Pods, pero normalmente no son la causa principal de problemas al hacer pull de imágenes.
</details>
### 4. ¿Cuál es el paso de solución de problemas más efectivo cuando un Service no enruta tráfico a Pods en un cluster de Amazon EKS?

A. Crear inmediatamente un Service nuevo
B. Comprobar labels de Service y Pod, endpoints y network policies
C. Reiniciar todos los Pods
D. Reiniciar el cluster API server

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Comprobar labels de Service y Pod, endpoints y network policies**

**Explicación:**
Cuando un Service no enruta tráfico a Pods en un cluster de Amazon EKS, el paso de solución de problemas más efectivo es comprobar los labels de Service y Pod, los endpoints y las network policies. Este enfoque sistemático ayuda a identificar la causa raíz de los problemas de service discovery y enrutamiento de tráfico.

**Elementos clave para comprobar:**

1. **Comprobar labels de Service y Pod**:
   - Coincidencia entre selector del Service y label del Pod
   - Sintaxis de labels y errores tipográficos
   - Verificación de namespace

2. **Comprobar endpoints**:
   - Creación de endpoints del Service
   - Coincidencia entre IP de endpoint e IP de Pod
   - Número de Pods Ready

3. **Comprobar network policies**:
   - Network policies que restringen el tráfico
   - Reglas de ingress y egress
   - Restricciones de comunicación entre namespaces

4. **Comprobar estado de Service y Pod**:
   - Estado running y ready del Pod
   - Tipo de Service y configuración de puertos
   - Configuración de health check

**Métodos de solución de problemas:**

1. **Comprobar labels de Service y Pod**:
   ```bash
   # Check service selector
   kubectl get service <service-name> -o yaml | grep -A 5 selector

   # Check pod labels
   kubectl get pods --show-labels

   # Check pods matching selector
   kubectl get pods -l key=value
   ```

2. **Comprobar endpoints**:
   ```bash
   # Check service endpoints
   kubectl get endpoints <service-name>

   # Check endpoint details
   kubectl describe endpoints <service-name>

   # Compare endpoint and pod IPs
   kubectl get pods -o wide
   ```

3. **Comprobar network policies**:
   ```bash
   # Check network policies
   kubectl get networkpolicy

   # Check network policy details
   kubectl describe networkpolicy <policy-name>

   # Temporarily disable network policy
   kubectl delete networkpolicy <policy-name>
   ```

4. **Probar conectividad del Service**:
   ```bash
   # Create temporary debug pod
   kubectl run -it --rm debug --image=nicolaka/netshoot -- bash

   # Test service DNS resolution
   nslookup <service-name>.<namespace>.svc.cluster.local

   # Test service connectivity
   curl <service-ip>:<port>

   # Test direct pod connectivity
   curl <pod-ip>:<container-port>
   ```

**Problemas comunes de Service y soluciones:**

1. **Discrepancia de labels**:
   - **Síntoma**: Los endpoints del Service están vacíos
   - **Solución**:
     ```bash
     # Modify service selector
     kubectl edit service <service-name>
     # or
     kubectl patch service <service-name> -p '{"spec":{"selector":{"app":"correct-label"}}}'

     # Modify pod labels
     kubectl label pods <pod-name> app=correct-label --overwrite
     ```

2. **Error de configuración de puertos**:
   - **Síntoma**: El Service conecta, pero no hay respuesta de la aplicación
   - **Solución**:
     ```bash
     # Check service port configuration
     kubectl describe service <service-name>

     # Check pod container port
     kubectl describe pod <pod-name>

     # Modify service port
     kubectl edit service <service-name>
     ```

3. **Restricciones de network policy**:
   - **Síntoma**: El Service es inaccesible solo desde orígenes específicos
   - **Solución**:
     ```bash
     # Modify network policy
     kubectl edit networkpolicy <policy-name>

     # Add allow rule
     kubectl apply -f - <<EOF
     apiVersion: networking.k8s.io/v1
     kind: NetworkPolicy
     metadata:
       name: allow-service-access
       namespace: <namespace>
     spec:
       podSelector:
         matchLabels:
           app: <app-label>
       ingress:
       - from:
         - namespaceSelector: {}
       policyTypes:
       - Ingress
     EOF
     ```

4. **Problemas de CoreDNS**:
   - **Síntoma**: Falla la resolución de nombres de Service
   - **Solución**:
     ```bash
     # Check CoreDNS pods
     kubectl get pods -n kube-system -l k8s-app=kube-dns

     # Check CoreDNS logs
     kubectl logs -n kube-system -l k8s-app=kube-dns

     # Check CoreDNS configuration
     kubectl get configmap -n kube-system coredns -o yaml
     ```

**Buenas prácticas:**

1. **Enfoque sistemático de solución de problemas**:
   - Empezar con la configuración del Service y luego comprobar Pods, network policies y DNS en orden
   - Recopilar evidencia clara en cada paso
   - Cambiar solo una variable a la vez

2. **Utilizar herramientas de depuración de Service**:
   ```bash
   # Check kube-proxy logs
   kubectl logs -n kube-system -l k8s-app=kube-proxy

   # Check iptables rules (for self-managed nodes)
   ssh ec2-user@<node-ip>
   sudo iptables-save | grep <service-ip>

   # DNS debugging
   kubectl run -it --rm dnsutils --image=tutum/dnsutils -- bash
   ```

3. **Implementar monitorización de Service**:
   - Monitorizar el estado de endpoints del Service
   - Verificar el estado de conectividad del Service
   - Visualizar el flujo de tráfico

4. **Gestión de configuración de Service**:
   - Estrategia de labeling consistente
   - Nombres de puertos explícitos
   - Documentar Services

Problemas con las otras opciones:
- **A. Crear inmediatamente un Service nuevo**: Crear un Service nuevo sin identificar la causa raíz puede resultar en el mismo problema, y se pierde información diagnóstica.
- **C. Reiniciar todos los Pods**: Reiniciar Pods no solucionará problemas de configuración del Service y puede causar una interrupción innecesaria del servicio.
- **D. Reiniciar el cluster API server**: Reiniciar el API server es una medida extrema y no está directamente relacionada con problemas de enrutamiento del Service. También puede afectar a todo el cluster.
</details>
### 5. ¿Cuál es la causa y la solución más probables cuando un PersistentVolumeClaim permanece en estado "Pending" en un cluster de Amazon EKS?

A. Escasez de recursos del Node / Añadir Nodes más grandes
B. Problema de storage class o permisos insuficientes de aprovisionamiento de volúmenes / Comprobar la storage class y configurar permisos de IAM
C. Baja prioridad del Pod / Aumentar la prioridad del Pod
D. Cluster autoscaler deshabilitado / Habilitar autoscaler

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Problema de storage class o permisos insuficientes de aprovisionamiento de volúmenes / Comprobar la storage class y configurar permisos de IAM**

**Explicación:**
Cuando un PersistentVolumeClaim (PVC) permanece en estado "Pending" en un cluster de Amazon EKS, la causa más probable es un problema de storage class o permisos insuficientes de aprovisionamiento de volúmenes. Para resolverlo, debes comprobar la storage class y configurar los permisos de IAM necesarios.

**Causas principales y soluciones:**

1. **Problemas de storage class**:
   - Se especificó una storage class inexistente
   - Errores en parámetros de la storage class
   - Problemas de configuración del provisioner

   **Solución**:
   ```bash
   # Check storage classes
   kubectl get storageclass

   # Check storage class details
   kubectl describe storageclass <storage-class-name>

   # Set default storage class
   kubectl patch storageclass <storage-class-name> -p '{"metadata": {"annotations":{"storageclass.kubernetes.io/is-default-class":"true"}}}'
   ```

2. **Permisos de IAM insuficientes**:
   - La service account del EBS CSI driver no tiene permisos
   - El IAM role del Node no tiene permisos
   - Problemas de acceso entre cuentas

   **Solución**:
   ```bash
   # Check EBS CSI driver service account
   kubectl get serviceaccount -n kube-system ebs-csi-controller-sa

   # Check IAM role attachment
   kubectl describe serviceaccount -n kube-system ebs-csi-controller-sa

   # Attach required IAM policy
   aws iam attach-role-policy \
     --role-name <role-name> \
     --policy-arn arn:aws:iam::aws:policy/service-role/AmazonEBSCSIDriverPolicy
   ```

3. **Problemas de volume binding mode**:
   - Discrepancia de availability zone
   - Problemas con la configuración WaitForFirstConsumer
   - Restricciones de topología

   **Solución**:
   ```bash
   # Check volume binding mode
   kubectl get storageclass <storage-class-name> -o jsonpath='{.volumeBindingMode}'

   # Modify storage class
   kubectl patch storageclass <storage-class-name> -p '{"volumeBindingMode":"WaitForFirstConsumer"}'

   # Create new storage class
   kubectl apply -f - <<EOF
   apiVersion: storage.k8s.io/v1
   kind: StorageClass
   metadata:
     name: ebs-sc-waitforfirstconsumer
   provisioner: ebs.csi.aws.com
   volumeBindingMode: WaitForFirstConsumer
   parameters:
     type: gp3
   EOF
   ```

4. **Problemas del CSI driver**:
   - CSI driver no instalado o con errores
   - Problemas de compatibilidad de versiones
   - Errores en Pods del controller

   **Solución**:
   ```bash
   # Check CSI driver pods
   kubectl get pods -n kube-system -l app=ebs-csi-controller

   # Check CSI driver logs
   kubectl logs -n kube-system -l app=ebs-csi-controller -c ebs-plugin

   # Reinstall CSI driver
   eksctl create addon --name aws-ebs-csi-driver --cluster <cluster-name> --force
   ```

**Buenas prácticas:**

1. **Configuración adecuada de storage class**:
   ```yaml
   # gp3 storage class example
   apiVersion: storage.k8s.io/v1
   kind: StorageClass
   metadata:
     name: ebs-gp3
     annotations:
       storageclass.kubernetes.io/is-default-class: "true"
   provisioner: ebs.csi.aws.com
   volumeBindingMode: WaitForFirstConsumer
   parameters:
     type: gp3
     encrypted: "true"
   allowVolumeExpansion: true
   ```

2. **Configuración de IRSA (IAM Roles for Service Accounts)**:
   ```bash
   # Create IRSA for EBS CSI driver
   eksctl create iamserviceaccount \
     --name ebs-csi-controller-sa \
     --namespace kube-system \
     --cluster <cluster-name> \
     --attach-policy-arn arn:aws:iam::aws:policy/service-role/AmazonEBSCSIDriverPolicy \
     --approve \
     --override-existing-serviceaccounts
   ```

3. **Solicitud PVC optimizada**:
   ```yaml
   # Optimized PVC example
   apiVersion: v1
   kind: PersistentVolumeClaim
   metadata:
     name: my-pvc
   spec:
     accessModes:
       - ReadWriteOnce
     storageClassName: ebs-gp3
     resources:
       requests:
         storage: 10Gi
   ```

4. **Optimización de volume binding mode**:
   - Usar WaitForFirstConsumer
   - Asegurar que coincidan las availability zones del Pod y el PV
   - Utilizar aprovisionamiento consciente de la topología

Problemas con las otras opciones:
- **A. Escasez de recursos del Node / Añadir Nodes más grandes**: La escasez de recursos del Node normalmente hace que los Pods queden en estado "Pending", pero no está directamente relacionada con PVCs en estado "Pending".
- **C. Baja prioridad del Pod / Aumentar la prioridad del Pod**: La prioridad del Pod afecta las decisiones de scheduling, pero no afecta el aprovisionamiento de PVC.
- **D. Cluster autoscaler deshabilitado / Habilitar autoscaler**: Autoscaler ayuda a ajustar la cantidad de Nodes, pero no está directamente relacionado con problemas de aprovisionamiento de PVC.
</details>
### 6. ¿Cuál es el enfoque de solución de problemas más efectivo cuando autoscaling no funciona como se esperaba en un cluster de Amazon EKS?

A. Asignar más recursos a todos los Pods
B. Añadir Nodes manualmente
C. Comprobar configuración, métricas, permisos y eventos de HPA, CA y VPA
D. Recrear el cluster

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C. Comprobar configuración, métricas, permisos y eventos de HPA, CA y VPA**

**Explicación:**
Cuando autoscaling no funciona como se esperaba en un cluster de Amazon EKS, el enfoque de solución de problemas más efectivo es comprobar la configuración, las métricas, los permisos y los eventos de HPA (Horizontal Pod Autoscaler), CA (Cluster Autoscaler) y VPA (Vertical Pod Autoscaler). Este enfoque sistemático ayuda a identificar y resolver la causa raíz de los problemas de autoscaling.

**Elementos clave para comprobar:**

1. **Comprobar HPA (Horizontal Pod Autoscaler)**:
   - Configuración y estado de HPA
   - Disponibilidad y valores de métricas
   - Límites y comportamiento de scaling

2. **Comprobar CA (Cluster Autoscaler)**:
   - Deployment y configuración de CA
   - Permisos y roles de IAM
   - Tags y configuración de node group

3. **Comprobar VPA (Vertical Pod Autoscaler)**:
   - Configuración y modo de VPA
   - Recomendaciones de recursos
   - Políticas de actualización

4. **Comprobar métricas y eventos**:
   - Estado de metrics server
   - Disponibilidad de métricas de CloudWatch
   - Eventos y logs de autoscaling

**Métodos de solución de problemas:**

1. **Solución de problemas de HPA**:
   ```bash
   # Check HPA status
   kubectl get hpa

   # Check HPA details
   kubectl describe hpa <hpa-name>

   # Check metrics
   kubectl get --raw "/apis/metrics.k8s.io/v1beta1/namespaces/<namespace>/pods"

   # Check metrics server status
   kubectl get pods -n kube-system -l k8s-app=metrics-server
   kubectl logs -n kube-system -l k8s-app=metrics-server
   ```

2. **Solución de problemas de CA**:
   ```bash
   # Check CA pod status
   kubectl get pods -n kube-system -l app=cluster-autoscaler

   # Check CA logs
   kubectl logs -n kube-system -l app=cluster-autoscaler

   # Check node group tags
   aws autoscaling describe-auto-scaling-groups \
     --auto-scaling-group-names <asg-name> \
     --query "AutoScalingGroups[].Tags"

   # Check CA events
   kubectl get events --sort-by='.lastTimestamp' | grep -i "cluster-autoscaler"
   ```

3. **Solución de problemas de VPA**:
   ```bash
   # Check VPA status
   kubectl get vpa

   # Check VPA details
   kubectl describe vpa <vpa-name>

   # Check VPA recommendations
   kubectl get vpa <vpa-name> -o jsonpath='{.status.recommendation}'

   # Check VPA component status
   kubectl get pods -n kube-system -l app=vpa-recommender
   ```

4. **Solución de problemas de métricas y permisos**:
   ```bash
   # Check metrics server status
   kubectl get apiservices v1beta1.metrics.k8s.io

   # Check IAM roles and policies
   aws iam get-role --role-name <role-name>
   aws iam list-attached-role-policies --role-name <role-name>

   # Check CloudWatch metrics
   aws cloudwatch list-metrics \
     --namespace AWS/EC2 \
     --metric-name CPUUtilization \
     --dimensions Name=AutoScalingGroupName,Value=<asg-name>
   ```

**Problemas comunes de autoscaling y soluciones:**

1. **Problemas de métricas de HPA**:
   - **Síntoma**: HPA no toma decisiones de scaling
   - **Causa**: Error del metrics server o problema de disponibilidad de métricas
   - **Solución**:
     ```bash
     # Reinstall metrics server
     kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml

     # Verify metrics
     kubectl top pods
     kubectl top nodes
     ```

2. **Problemas de permisos de CA**:
   - **Síntoma**: CA no añade Nodes
   - **Causa**: Permisos de IAM insuficientes o tags de ASG faltantes
   - **Solución**:
     ```bash
     # Attach CA IAM policy
     aws iam attach-role-policy \
       --role-name <role-name> \
       --policy-arn arn:aws:iam::aws:policy/AutoScalingFullAccess

     # Add ASG tags
     aws autoscaling create-or-update-tags \
       --tags "ResourceId=<asg-name>,ResourceType=auto-scaling-group,Key=k8s.io/cluster-autoscaler/enabled,Value=true,PropagateAtLaunch=true" \
       "ResourceId=<asg-name>,ResourceType=auto-scaling-group,Key=k8s.io/cluster-autoscaler/<cluster-name>,Value=owned,PropagateAtLaunch=true"
     ```

3. **Problemas de límites de scaling**:
   - **Síntoma**: Scaling no supera cierto valor
   - **Causa**: Configuración de límites de HPA o CA
   - **Solución**:
     ```bash
     # Modify HPA max replicas
     kubectl patch hpa <hpa-name> -p '{"spec":{"maxReplicas":20}}'

     # Modify ASG max size
     aws autoscaling update-auto-scaling-group \
       --auto-scaling-group-name <asg-name> \
       --max-size 10
     ```

4. **Problemas de modo de actualización de VPA**:
   - **Síntoma**: VPA no actualiza recursos
   - **Causa**: Modo de actualización configurado como "Off" o "Initial"
   - **Solución**:
     ```bash
     # Modify VPA update mode
     kubectl patch vpa <vpa-name> -p '{"spec":{"updatePolicy":{"updateMode":"Auto"}}}'
     ```

**Buenas prácticas:**

1. **Enfoque sistemático de solución de problemas**:
   - Comprobar cada componente de autoscaling de forma individual
   - Analizar logs y eventos
   - Solución de problemas paso a paso

2. **Implementar monitorización de autoscaling**:
   - Monitorizar actividad de autoscaling
   - Configurar notificaciones de eventos de scaling
   - Configurar dashboard de métricas de scaling

3. **Optimizar la configuración de autoscaling**:
   - Establecer umbrales de scaling adecuados para las características de la workload
   - Ajustar el comportamiento de scaling y los períodos de cooldown
   - Equilibrar costo y rendimiento

4. **Integrar varios componentes de autoscaling**:
   - Usar una combinación de HPA, CA y VPA
   - Evitar conflictos entre componentes
   - Implementar una estrategia de scaling consistente

Problemas con las otras opciones:
- **A. Asignar más recursos a todos los Pods**: Esto no resuelve la causa raíz y puede desperdiciar recursos, además de no identificar la causa real de los problemas de autoscaling.
- **B. Añadir Nodes manualmente**: Esto es solo una solución temporal y no resuelve los problemas fundamentales del sistema de autoscaling.
- **D. Recrear el cluster**: Esta es una medida extrema que no identifica la causa raíz y provoca downtime y trabajo innecesarios.
</details>
### 7. ¿Cuál es el enfoque de solución de problemas más efectivo cuando las network policies no funcionan como se esperaba en un cluster de Amazon EKS?

A. Eliminar todas las network policies y usar los valores predeterminados
B. Comprobar el plugin CNI del cluster, la configuración de network policy, logs y eventos
C. Establecer hostNetwork: true para todos los Pods
D. Reconfigurar la VPC del cluster

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Comprobar el plugin CNI del cluster, la configuración de network policy, logs y eventos**

**Explicación:**
Cuando las network policies no funcionan como se esperaba en un cluster de Amazon EKS, el enfoque de solución de problemas más efectivo es comprobar sistemáticamente el plugin CNI del cluster, la configuración de network policy, los logs y los eventos. Este enfoque ayuda a identificar y resolver la causa raíz de los problemas de network policy.

**Elementos clave para comprobar:**

1. **Comprobar plugin CNI**:
   - Tipo de plugin CNI en uso (AWS VPC CNI, Calico, Cilium, etc.)
   - Versión y compatibilidad del plugin CNI
   - Soporte de network policy

2. **Comprobar configuración de network policy**:
   - Sintaxis y selectors de network policy
   - Prioridad y conflictos de policies
   - Namespace selectors y label selectors

3. **Comprobar logs y eventos**:
   - Logs del plugin CNI
   - Logs del network policy controller
   - Eventos relacionados y mensajes de error

4. **Probar conectividad de red**:
   - Prueba de conectividad Pod a Pod
   - Prueba de conectividad de Service
   - Prueba de conectividad externa

**Métodos de solución de problemas:**

1. **Comprobar plugin CNI**:
   ```bash
   # Check CNI plugin pods
   kubectl get pods -n kube-system -l k8s-app=aws-node  # AWS VPC CNI
   kubectl get pods -n kube-system -l k8s-app=calico-node  # Calico
   kubectl get pods -n kube-system -l k8s-app=cilium  # Cilium

   # Check CNI plugin logs
   kubectl logs -n kube-system -l k8s-app=aws-node
   kubectl logs -n kube-system -l k8s-app=calico-node
   kubectl logs -n kube-system -l k8s-app=cilium

   # Check CNI configuration
   kubectl describe daemonset -n kube-system aws-node
   kubectl describe daemonset -n kube-system calico-node
   kubectl describe daemonset -n kube-system cilium
   ```

2. **Comprobar network policies**:
   ```bash
   # List network policies
   kubectl get networkpolicies --all-namespaces

   # Check specific network policy details
   kubectl describe networkpolicy <policy-name> -n <namespace>

   # Check network policy YAML
   kubectl get networkpolicy <policy-name> -n <namespace> -o yaml
   ```

3. **Comprobar información de red del Pod**:
   ```bash
   # Check pod IP and node information
   kubectl get pods -o wide

   # Check pod network interface
   kubectl exec -it <pod-name> -- ip addr

   # Check pod routing table
   kubectl exec -it <pod-name> -- ip route
   ```

4. **Probar conectividad de red**:
   ```bash
   # Create debug pod
   kubectl run network-debug --rm -it --image=nicolaka/netshoot -- /bin/bash

   # Test pod-to-pod connectivity
   ping <target-pod-ip>
   nc -zv <target-pod-ip> <port>

   # Test DNS resolution
   nslookup <service-name>.<namespace>.svc.cluster.local

   # Packet capture
   tcpdump -i eth0 -n
   ```

**Problemas comunes de network policy y soluciones:**

1. **Problemas de compatibilidad del plugin CNI**:
   - **Síntoma**: Las network policies no se aplican
   - **Causa**: El plugin CNI en uso no soporta network policies
   - **Solución**:
     ```bash
     # Add Calico policy engine to AWS VPC CNI
     kubectl apply -f https://raw.githubusercontent.com/aws/amazon-vpc-cni-k8s/master/config/master/calico-operator.yaml
     kubectl apply -f https://raw.githubusercontent.com/aws/amazon-vpc-cni-k8s/master/config/master/calico-crs.yaml

     # Or switch to Cilium
     helm repo add cilium https://helm.cilium.io/
     helm install cilium cilium/cilium --namespace kube-system
     ```

2. **Problemas de selector en network policy**:
   - **Síntoma**: Las policies no se aplican a los Pods esperados
   - **Causa**: Label selector o namespace selector incorrecto
   - **Solución**:
     ```bash
     # Check pod labels
     kubectl get pods --show-labels

     # Modify network policy
     kubectl edit networkpolicy <policy-name> -n <namespace>
     ```

3. **Problemas de conflicto de policies**:
   - **Síntoma**: Bloqueo o permiso de conexiones inesperado
   - **Causa**: Conflictos o problemas de prioridad entre múltiples policies
   - **Solución**:
     ```bash
     # Review all network policies
     kubectl get networkpolicies --all-namespaces -o yaml

     # Simplify or reconfigure policies
     kubectl apply -f updated-network-policy.yaml
     ```

4. **Bugs o errores de configuración del plugin CNI**:
   - **Síntoma**: Problemas de conexión intermitentes o comportamiento inconsistente
   - **Causa**: Bugs del plugin CNI o configuración incorrecta
   - **Solución**:
     ```bash
     # Update CNI plugin
     kubectl set image daemonset/aws-node -n kube-system aws-node=<new-image-version>

     # Check and modify CNI configuration
     kubectl edit configmap -n kube-system aws-node
     ```

**Buenas prácticas:**

1. **Diseño sistemático de network policies**:
   - Empezar con una default deny policy
   - Permitir explícitamente solo las conexiones necesarias
   - Usar policies basadas en namespace y labels

2. **Probar y validar network policies**:
   - Probar antes de aplicar policies
   - Automatizar pruebas de conectividad
   - Despliegue gradual de policies

3. **Monitorización y logging de red**:
   - Monitorizar el tráfico de red
   - Registrar denegaciones de conexión
   - Monitorizar el rendimiento de red

4. **Selección y configuración del plugin CNI**:
   - Elegir un CNI adecuado para los requisitos de la workload
   - Mantenerlo actualizado
   - Asignar recursos adecuados

Problemas con las otras opciones:
- **A. Eliminar todas las network policies y usar los valores predeterminados**: Esto crea riesgos de seguridad, elimina el aislamiento de red necesario y no resuelve la causa raíz.
- **C. Establecer hostNetwork: true para todos los Pods**: Esto omite las network policies, crea riesgos de seguridad y elimina el aislamiento entre Pods.
- **D. Reconfigurar la VPC del cluster**: Esta es una medida extrema, y la mayoría de los problemas de network policy están relacionados con la configuración de CNI y policies dentro del cluster, no a nivel de VPC.
</details>
### 8. ¿Cuál es el enfoque más efectivo para solucionar problemas de despliegue de Helm chart en un cluster de Amazon EKS?

A. Eliminar todos los Helm charts y reinstalarlos
B. Recrear el cluster
C. Comprobar sistemáticamente la versión de Helm, la configuración del chart, dependencias, permisos y logs
D. Desplegar manualmente todos los recursos

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C. Comprobar sistemáticamente la versión de Helm, la configuración del chart, dependencias, permisos y logs**

**Explicación:**
El enfoque más efectivo para solucionar problemas de despliegue de Helm chart en un cluster de Amazon EKS es comprobar sistemáticamente la versión de Helm, la configuración del chart, las dependencias, los permisos y los logs. Este enfoque ayuda a identificar y resolver la causa raíz de los problemas de despliegue de Helm.

**Elementos clave para comprobar:**

1. **Comprobar versión y compatibilidad de Helm**:
   - Versión del cliente Helm y Tiller (Helm 2)
   - Compatibilidad de versión de Kubernetes API
   - Compatibilidad de versión de EKS

2. **Comprobar configuración y values del chart**:
   - Errores de sintaxis del chart
   - Configuración del archivo values
   - Problemas de renderizado de templates

3. **Comprobar dependencias y repositorios**:
   - Disponibilidad de dependencias del chart
   - Accesibilidad del repositorio
   - Compatibilidad de versión del chart

4. **Comprobar permisos y RBAC**:
   - Permisos de service account
   - Reglas RBAC
   - Acceso a namespace

5. **Comprobar logs y eventos**:
   - Logs de debug de Helm
   - Eventos de Kubernetes
   - Logs de Pods relacionados

**Métodos de solución de problemas:**

1. **Comprobar versión y configuración de Helm**:
   ```bash
   # Check Helm version
   helm version

   # Check Helm environment variables
   env | grep HELM

   # Check Helm plugins
   helm plugin list

   # Check Helm repositories
   helm repo list
   helm repo update
   ```

2. **Validar y depurar charts**:
   ```bash
   # Validate chart syntax
   helm lint ./my-chart

   # Check template rendering
   helm template ./my-chart --debug

   # Update chart dependencies
   helm dependency update ./my-chart

   # Install with debug mode
   helm install my-release ./my-chart --debug
   ```

3. **Comprobar estado e historial de releases**:
   ```bash
   # List releases
   helm list -A

   # Include failed releases
   helm list -A --failed

   # Check release status
   helm status my-release

   # Check release history
   helm history my-release

   # Check release details
   helm get all my-release
   ```

4. **Comprobar recursos y eventos**:
   ```bash
   # Check deployed resources
   kubectl get all -n <namespace> -l app.kubernetes.io/instance=my-release

   # Check events
   kubectl get events -n <namespace> --sort-by='.lastTimestamp'

   # Check pod logs
   kubectl logs -n <namespace> -l app.kubernetes.io/instance=my-release

   # Check pod status
   kubectl describe pods -n <namespace> -l app.kubernetes.io/instance=my-release
   ```

5. **Comprobar permisos y RBAC**:
   ```bash
   # Check service accounts
   kubectl get serviceaccount -n <namespace>

   # Check roles and role bindings
   kubectl get roles,rolebindings -n <namespace>

   # Check cluster roles and bindings
   kubectl get clusterroles,clusterrolebindings -l app.kubernetes.io/instance=my-release

   # Check service account permissions
   kubectl auth can-i --list --as=system:serviceaccount:<namespace>:<serviceaccount>
   ```

**Problemas comunes de despliegue de Helm y soluciones:**

1. **Errores de sintaxis del chart**:
   - **Síntoma**: Falla el comando `helm install` o `helm template`
   - **Causa**: Errores de sintaxis YAML, funciones o variables de template inválidas
   - **Solución**:
     ```bash
     # Validate chart syntax
     helm lint ./my-chart

     # Check template rendering
     helm template ./my-chart --debug

     # Render template with specific values
     helm template ./my-chart --set key=value --debug
     ```

2. **Problemas de dependencias**:
   - **Síntoma**: Errores de dependencias durante la instalación del chart
   - **Causa**: Dependencias faltantes, discrepancias de versión o problemas de acceso al repositorio
   - **Solución**:
     ```bash
     # Update dependencies
     helm dependency update ./my-chart

     # Add and update repository
     helm repo add bitnami https://charts.bitnami.com/bitnami
     helm repo update

     # Build dependencies
     helm dependency build ./my-chart
     ```

3. **Problemas de permisos**:
   - **Síntoma**: Errores de permiso denegado
   - **Causa**: Permisos RBAC insuficientes o configuración incorrecta de service account
   - **Solución**:
     ```bash
     # Create required RBAC resources
     kubectl apply -f rbac.yaml

     # Specify service account
     helm install my-release ./my-chart --service-account=my-service-account

     # Check permissions
     kubectl auth can-i create deployments --as=system:serviceaccount:<namespace>:<serviceaccount>
     ```

4. **Conflictos de recursos**:
   - **Síntoma**: Error de recurso ya existente
   - **Causa**: Quedan recursos de una instalación anterior o hay conflictos de nombres
   - **Solución**:
     ```bash
     # Remove existing release
     helm uninstall my-release

     # Check and delete remaining resources
     kubectl get all -n <namespace> -l app.kubernetes.io/instance=my-release
     kubectl delete <resource-type> <resource-name> -n <namespace>

     # Install with different release name
     helm install new-release ./my-chart
     ```

5. **Problemas de configuración de values**:
   - **Síntoma**: La aplicación desplegada no funciona como se esperaba
   - **Causa**: Valores de configuración incorrectos o valores requeridos faltantes
   - **Solución**:
     ```bash
     # Check current values
     helm get values my-release

     # Check default values
     helm show values ./my-chart

     # Upgrade with values file
     helm upgrade my-release ./my-chart -f values.yaml

     # Set specific values
     helm upgrade my-release ./my-chart --set key=value
     ```

**Buenas prácticas:**

1. **Enfoque sistemático de solución de problemas**:
   - Verificación y validación paso a paso
   - Análisis de logs y eventos
   - Rastrear desde el síntoma hasta la causa

2. **Probar y validar Helm charts**:
   - Validar charts antes del despliegue
   - Probar primero en un entorno de pruebas
   - Incluir pasos de validación en el pipeline de CI/CD

3. **Gestión de versiones y compatibilidad**:
   - Usar versiones compatibles de Helm y Kubernetes
   - Especificar explícitamente las versiones de chart
   - Fijar versiones de dependencias

4. **Documentación y gestión de values**:
   - Documentar los values del chart
   - Gestionar archivos values específicos por entorno
   - Aplicar prácticas de seguridad para values sensibles

Problemas con las otras opciones:
- **A. Eliminar todos los Helm charts y reinstalarlos**: Esta es una medida extrema que puede causar pérdida de datos y no resuelve la causa raíz.
- **B. Recrear el cluster**: Esta es una medida muy extrema, y la mayoría de los problemas de despliegue de Helm están relacionados con la configuración del chart o permisos, no con problemas a nivel de cluster.
- **D. Desplegar manualmente todos los recursos**: Esto abandona los beneficios de Helm y es propenso a errores y difícil de gestionar para aplicaciones complejas.
</details>
### 9. ¿Cuál es el enfoque más efectivo para solucionar problemas de memory leak en un cluster de Amazon EKS?

A. Reiniciar todos los Pods
B. Aumentar el tamaño de los Nodes del cluster
C. Perfilar el uso de memoria, revisar límites de contenedores, analizar el código de la aplicación
D. Añadir más Nodes

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C. Perfilar el uso de memoria, revisar límites de contenedores, analizar el código de la aplicación**

**Explicación:**
El enfoque más efectivo para solucionar problemas de memory leak en un cluster de Amazon EKS es un enfoque sistemático que incluye profiling del uso de memoria, revisión de límites de contenedores y análisis del código de la aplicación. Este método ayuda a identificar y resolver la causa raíz de los memory leaks.

**Elementos clave para comprobar:**

1. **Profiling del uso de memoria**:
   - Monitorizar el uso de memoria a nivel de Pod y Node
   - Analizar patrones de uso de memoria a lo largo del tiempo
   - Identificar señales de memory leaks

2. **Revisar límites de contenedores**:
   - Comprobar configuración de memory request y limit
   - Analizar eventos OOM (Out of Memory) del contenedor
   - Optimizar la asignación de recursos

3. **Análisis del código de la aplicación**:
   - Revisar patrones internos de uso de memoria de la aplicación
   - Identificar código con posibles memory leaks
   - Usar herramientas de profiling de aplicaciones

4. **Revisar componentes del sistema**:
   - Configuración de gestión de memoria de kubelet
   - Uso de recursos del sistema del Node
   - Estado de componentes del cluster

**Métodos de solución de problemas:**

1. **Monitorizar y analizar el uso de memoria**:
   ```bash
   # Check node memory usage
   kubectl top nodes

   # Check pod memory usage
   kubectl top pods -A

   # Check pod memory usage in specific namespace
   kubectl top pods -n <namespace>

   # Check memory usage per container
   kubectl top pods -n <namespace> --containers

   # Identify pods with high memory usage
   kubectl top pods -A --sort-by=memory
   ```

2. **Comprobar límites de contenedores y eventos OOM**:
   ```bash
   # Check pod memory limits
   kubectl get pods -n <namespace> -o jsonpath='{.items[*].spec.containers[*].resources}'

   # Check pod details
   kubectl describe pod <pod-name> -n <namespace>

   # Check OOM events
   kubectl get events -n <namespace> --sort-by='.lastTimestamp' | grep -i "OOMKilled"

   # Check node OOM events
   kubectl get events --field-selector involvedObject.kind=Node --sort-by='.lastTimestamp' | grep -i "memory"
   ```

3. **Logs y profiling de la aplicación**:
   ```bash
   # Check application logs
   kubectl logs <pod-name> -n <namespace>

   # Check previous pod logs
   kubectl logs <pod-name> -n <namespace> --previous

   # Run application profiling tool
   kubectl exec -it <pod-name> -n <namespace> -- <profiling-command>

   # Generate memory dump
   kubectl exec -it <pod-name> -n <namespace> -- <memory-dump-command>
   ```

4. **Comprobar recursos de Node y sistema**:
   ```bash
   # Check node details
   kubectl describe node <node-name>

   # Check node memory pressure
   kubectl get nodes -o jsonpath='{.items[*].status.conditions[?(@.type=="MemoryPressure")]}'

   # Check kubelet logs
   kubectl logs -n kube-system <kubelet-pod-name>

   # Check system memory statistics
   kubectl debug node/<node-name> -it --image=busybox -- sh -c "cat /proc/meminfo"
   ```

**Problemas comunes de memory leak y soluciones:**

1. **Memory leaks de aplicación**:
   - **Síntoma**: El uso de memoria aumenta continuamente con el tiempo
   - **Causa**: Memory leaks en el código de la aplicación, falta de gestión de caché
   - **Solución**:
     - Revisar y corregir el código de la aplicación
     - Usar herramientas de profiling de memoria
     - Configurar garbage collection periódica
     - Implementar límites de tamaño de caché y políticas de expiración

2. **Problemas de límites de memoria del contenedor**:
   - **Síntoma**: Terminaciones OOM frecuentes, reinicios de Pod
   - **Causa**: Configuración inadecuada de límites de memoria, gran diferencia entre resource requests y limits
   - **Solución**:
     ```yaml
     # Set appropriate memory requests and limits
     apiVersion: v1
     kind: Pod
     metadata:
       name: memory-optimized-pod
     spec:
       containers:
       - name: app
         image: app-image
         resources:
           requests:
             memory: "256Mi"
           limits:
             memory: "512Mi"
     ```

3. **Problemas de memoria en componentes del sistema**:
   - **Síntoma**: Inestabilidad del Node, alto uso de memoria por kubelet u otros componentes del sistema
   - **Causa**: Problemas de configuración de kubelet, bugs de componentes del sistema
   - **Solución**:
     - Optimizar la configuración de kubelet
     - Actualizar componentes del sistema
     - Ajustar reservas de recursos del Node

4. **Problemas de fragmentación de memoria**:
   - **Síntoma**: OOM ocurre a pesar de que hay suficiente memoria total disponible
   - **Causa**: Fragmentación de memoria, fallos de asignación de páginas grandes
   - **Solución**:
     - Programar reinicios periódicos de Nodes
     - Distribuir workloads con alta presión de memoria
     - Reducir el memory overcommit del Node

**Buenas prácticas:**

1. **Monitorización sistemática de memoria**:
   - Monitorizar memoria a nivel de cluster, Node y Pod
   - Seguir patrones de uso de memoria a lo largo del tiempo
   - Configurar alertas para anomalías

2. **Establecer límites de recursos adecuados**:
   - Establecer memory requests y limits adecuados para las características de la workload
   - Mantener una proporción adecuada entre memory requests y limits
   - Revisión y ajuste periódicos del uso de recursos

3. **Optimización de aplicaciones**:
   - Escribir código eficiente en memoria
   - Profiling y optimización de memoria periódicos
   - Implementar estrategias de caching adecuadas

4. **Optimización de configuración del cluster**:
   - Optimizar las reservas de memoria del Node
   - Configuración adecuada de gestión de memoria de kubelet
   - Distribución y aislamiento de workloads

Problemas con las otras opciones:
- **A. Reiniciar todos los Pods**: Esto es solo una solución temporal y no resuelve la causa raíz de los memory leaks. El problema volverá a ocurrir una vez que los Pods se reinicien.
- **B. Aumentar el tamaño de los Nodes del cluster**: Esto no resuelve la causa raíz y solo oculta los síntomas. Los Nodes más grandes eventualmente se quedarán sin memoria si los memory leaks continúan.
- **D. Añadir más Nodes**: Similar a B, esto solo oculta los síntomas sin resolver la causa raíz. Los problemas de memory leak continuarán independientemente de la cantidad de Nodes.
</details>
### 10. ¿Cuál es el enfoque más efectivo para solucionar problemas de resolución DNS en un cluster de Amazon EKS?

A. Asignar IPs estáticas a todos los Pods
B. Comprobar sistemáticamente la configuración de CoreDNS, network policies, DNS policies y conectividad
C. Usar ExternalName para todos los Services
D. Reconfigurar la VPC del cluster

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Comprobar sistemáticamente la configuración de CoreDNS, network policies, DNS policies y conectividad**

**Explicación:**
El enfoque más efectivo para solucionar problemas de resolución DNS en un cluster de Amazon EKS es comprobar sistemáticamente la configuración de CoreDNS, network policies, DNS policies y conectividad. Este enfoque ayuda a identificar y resolver la causa raíz de los problemas DNS.

**Elementos clave para comprobar:**

1. **Comprobar configuración y estado de CoreDNS**:
   - Estado y logs de Pods de CoreDNS
   - Configuración del ConfigMap de CoreDNS
   - Service y endpoints de CoreDNS

2. **Comprobar network policies y conectividad**:
   - Network policies para puertos DNS (53/UDP, 53/TCP)
   - Conectividad de red entre Pods y CoreDNS
   - Configuración DNS de VPC

3. **Comprobar DNS policies y configuración**:
   - Configuración de DNS policy del Pod
   - Opciones de configuración DNS
   - Configuración de host namespace

4. **Comprobar configuración del cluster y VPC**:
   - Configuración DNS del cluster EKS
   - Atributos DNS de VPC
   - DHCP option sets

**Métodos de solución de problemas:**

1. **Comprobar estado y configuración de CoreDNS**:
   ```bash
   # Check CoreDNS pod status
   kubectl get pods -n kube-system -l k8s-app=kube-dns

   # Check CoreDNS logs
   kubectl logs -n kube-system -l k8s-app=kube-dns

   # Check CoreDNS ConfigMap
   kubectl get configmap coredns -n kube-system -o yaml

   # Check CoreDNS service
   kubectl get service kube-dns -n kube-system

   # Check CoreDNS endpoints
   kubectl get endpoints kube-dns -n kube-system
   ```

2. **Probar resolución DNS**:
   ```bash
   # Create debug pod
   kubectl run dns-test --rm -it --image=busybox -- sh

   # Test cluster internal DNS resolution
   nslookup kubernetes.default.svc.cluster.local

   # Test service DNS resolution
   nslookup <service-name>.<namespace>.svc.cluster.local

   # Test external domain resolution
   nslookup google.com

   # Check DNS server
   cat /etc/resolv.conf
   ```

3. **Comprobar network policies y conectividad**:
   ```bash
   # Check DNS-related network policies
   kubectl get networkpolicies --all-namespaces

   # Test connection to CoreDNS
   kubectl run netcat-test --rm -it --image=busybox -- sh -c "nc -zv kube-dns.kube-system.svc.cluster.local 53"

   # Capture DNS packets
   kubectl run tcpdump-test --rm -it --image=nicolaka/netshoot -- tcpdump -i any port 53
   ```

4. **Comprobar configuración DNS del Pod**:
   ```bash
   # Check pod DNS policy
   kubectl get pod <pod-name> -o jsonpath='{.spec.dnsPolicy}'

   # Check pod DNS configuration
   kubectl get pod <pod-name> -o jsonpath='{.spec.dnsConfig}'

   # Check pod internal resolv.conf
   kubectl exec -it <pod-name> -- cat /etc/resolv.conf
   ```

5. **Comprobar configuración DNS de VPC y cluster**:
   ```bash
   # Check VPC DNS attributes
   aws ec2 describe-vpcs --vpc-id <vpc-id> --query 'Vpcs[0].EnableDnsSupport'
   aws ec2 describe-vpcs --vpc-id <vpc-id> --query 'Vpcs[0].EnableDnsHostnames'

   # Check DHCP option set
   aws ec2 describe-vpcs --vpc-id <vpc-id> --query 'Vpcs[0].DhcpOptionsId'
   aws ec2 describe-dhcp-options --dhcp-options-id <dhcp-options-id>

   # Check node DNS configuration
   kubectl debug node/<node-name> -it --image=busybox -- cat /etc/resolv.conf
   ```

**Problemas comunes de DNS y soluciones:**

1. **Problemas de Pods de CoreDNS**:
   - **Síntoma**: Las consultas DNS fallan, Pods de CoreDNS anormales
   - **Causa**: Fallos de Pods de CoreDNS, escasez de recursos, errores de configuración
   - **Solución**:
     ```bash
     # Restart CoreDNS pods
     kubectl rollout restart deployment coredns -n kube-system

     # Increase CoreDNS resources
     kubectl edit deployment coredns -n kube-system
     # Increase requests and limits in resources section

     # Check CoreDNS logs
     kubectl logs -n kube-system -l k8s-app=kube-dns
     ```

2. **Problemas de network policy**:
   - **Síntoma**: La resolución DNS falla solo desde namespaces o Pods específicos
   - **Causa**: Network policies restrictivas que bloquean tráfico DNS
   - **Solución**:
     ```yaml
     # Network policy allowing DNS traffic
     apiVersion: networking.k8s.io/v1
     kind: NetworkPolicy
     metadata:
       name: allow-dns
       namespace: <namespace>
     spec:
       podSelector: {}
       policyTypes:
       - Egress
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

3. **Problemas de DNS policy y configuración**:
   - **Síntoma**: Solo fallan ciertos tipos de consultas DNS
   - **Causa**: DNS policy o configuración inadecuada
   - **Solución**:
     ```yaml
     # Create pod with custom DNS configuration
     apiVersion: v1
     kind: Pod
     metadata:
       name: dns-custom-pod
     spec:
       containers:
       - name: app
         image: busybox
         command: ["sleep", "3600"]
       dnsPolicy: "None"
       dnsConfig:
         nameservers:
         - "169.254.20.10"  # VPC DNS server
         - "8.8.8.8"        # Backup DNS server
         searches:
         - <namespace>.svc.cluster.local
         - svc.cluster.local
         - cluster.local
         options:
         - name: ndots
           value: "5"
     ```

4. **Problemas de configuración DNS de VPC**:
   - **Síntoma**: Falla la resolución de dominios externos
   - **Causa**: Atributos DNS de VPC deshabilitados o problemas con DHCP option set
   - **Solución**:
     ```bash
     # Enable VPC DNS attributes
     aws ec2 modify-vpc-attribute --vpc-id <vpc-id> --enable-dns-support
     aws ec2 modify-vpc-attribute --vpc-id <vpc-id> --enable-dns-hostnames

     # Create custom DHCP option set
     aws ec2 create-dhcp-options \
       --dhcp-configurations \
       "Key=domain-name-servers,Values=AmazonProvidedDNS" \
       "Key=domain-name,Values=<region>.compute.internal"

     # Associate DHCP option set with VPC
     aws ec2 associate-dhcp-options --dhcp-options-id <dhcp-options-id> --vpc-id <vpc-id>
     ```

5. **Problemas de configuración de CoreDNS**:
   - **Síntoma**: Falla la resolución de dominios específicos o la resolución DNS es lenta
   - **Causa**: Errores de configuración de CoreDNS o configuraciones no optimizadas
   - **Solución**:
     ```yaml
     # Optimized CoreDNS ConfigMap
     apiVersion: v1
     kind: ConfigMap
     metadata:
       name: coredns
       namespace: kube-system
     data:
       Corefile: |
         .:53 {
             errors
             health {
                lameduck 5s
             }
             ready
             kubernetes cluster.local in-addr.arpa ip6.arpa {
                pods insecure
                fallthrough in-addr.arpa ip6.arpa
                ttl 30
             }
             prometheus :9153
             forward . /etc/resolv.conf {
                max_concurrent 1000
                health_check 5s
             }
             cache 30
             loop
             reload
             loadbalance
         }
     ```

**Buenas prácticas:**

1. **Monitorización y scaling de CoreDNS**:
   - Monitorizar rendimiento y estado de CoreDNS
   - Escalar réplicas de CoreDNS según el tamaño del cluster
   - Asignar recursos adecuados

2. **Caching y optimización de DNS**:
   - TTL y configuración de caché adecuados
   - Implementar caching DNS a nivel de Node
   - Considerar caching DNS a nivel de aplicación

3. **Diseño de network policy**:
   - Permitir explícitamente tráfico DNS
   - Aplicar el principio de privilegio mínimo
   - Probar y validar network policies

4. **Herramientas y procesos de solución de problemas de DNS**:
   - Preparar herramientas y scripts de solución de problemas de DNS
   - Establecer un proceso sistemático de solución de problemas
   - Monitorizar eventos y logs relacionados con DNS

Problemas con las otras opciones:
- **A. Asignar IPs estáticas a todos los Pods**: Esto no resuelve problemas DNS, y la asignación de IP de Pod y la resolución DNS son problemas separados. Asignar IPs estáticas a Pods también va en contra de la naturaleza dinámica de Kubernetes y aumenta la complejidad de gestión.
- **C. Usar ExternalName para todos los Services**: Esto solo es adecuado para casos de uso específicos y no resuelve la mayoría de problemas DNS. ExternalName se usa para proporcionar alias a servicios externos y no resuelve problemas de resolución DNS interna del cluster.
- **D. Reconfigurar la VPC del cluster**: Esta es una medida extrema, y la mayoría de los problemas DNS están relacionados con la configuración DNS dentro del cluster, no a nivel de VPC. Reconfigurar la VPC puede causar downtime y complejidad innecesarios.
</details>
