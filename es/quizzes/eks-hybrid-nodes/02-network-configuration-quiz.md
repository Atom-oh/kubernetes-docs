# Cuestionario de configuración de red de EKS Hybrid Nodes

> **Documento relacionado**: [Configuración de red](../../eks-hybrid-nodes/02-network-configuration.md)

## Preguntas de opción múltiple

### 1. ¿Cuál es el método recomendado para la conectividad de red entre on-premises y la nube para EKS Hybrid Nodes?

A. Conexión a Internet pública
B. AWS Direct Connect o Site-to-Site VPN
C. Túnel SSH
D. Proxy HTTP

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. AWS Direct Connect o Site-to-Site VPN**

**Explicación:**
EKS Hybrid Nodes requiere una conectividad de red estable y segura con el EKS control plane. Se recomienda AWS Direct Connect (línea dedicada) o Site-to-Site VPN.

**Requisitos de red:**
- Acceso al endpoint del servidor EKS API (443/TCP)
- Acceso a endpoints de servicios de AWS (ECR, S3, STS, etc.)
- Conexión estable de baja latencia

```bash
# Check Site-to-Site VPN configuration
aws ec2 describe-vpn-connections \
  --filters Name=state,Values=available

# Monitor VPN connection status
aws cloudwatch get-metric-statistics \
  --namespace AWS/VPN \
  --metric-name TunnelState \
  --dimensions Name=VpnId,Value=vpn-xxxxxx
```

</details>

### 2. ¿Qué puerto de firewall debe abrirse para que Hybrid Nodes se comunique con el EKS control plane?

A. 22/TCP (SSH)
B. 443/TCP (HTTPS)
C. 8080/TCP (HTTP Proxy)
D. 3306/TCP (MySQL)

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. 443/TCP (HTTPS)**

**Explicación:**
Hybrid Nodes se comunica con el servidor EKS API mediante HTTPS (443/TCP). Reglas de firewall requeridas:

| Port | Protocol | Purpose | Direction |
|------|----------|---------|-----------|
| 443 | TCP | EKS API server, AWS services | Outbound |
| 10250 | TCP | kubelet API | Inbound |
| 10255 | TCP | kubelet read-only | Inbound (optional) |

```bash
# Check firewall rules (iptables)
sudo iptables -L -n

# Test connectivity
curl -v https://<eks-api-endpoint>:443/healthz
```

</details>

### 3. ¿Cuáles son 3 VPC endpoints necesarios para el acceso a servicios de AWS en EKS Hybrid Nodes?

A. ec2, ecr.api, sts
B. lambda, dynamodb, sns
C. rds, elasticache, sqs
D. cloudfront, route53, waf

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A. ec2, ecr.api, sts**

**Explicación:**
VPC endpoints clave necesarios para que Hybrid Nodes acceda a servicios de AWS:

1. **ec2.region.amazonaws.com** (EC2 API)
2. **ecr.api.region.amazonaws.com** (ECR API)
3. **sts.region.amazonaws.com** (STS - autenticación de IAM)

**Endpoints adicionales recomendados:**
- `ecr.dkr.region.amazonaws.com` (ECR Docker Registry)
- `s3.region.amazonaws.com` (S3 - almacenamiento de imágenes de ECR)
- `logs.region.amazonaws.com` (CloudWatch Logs)
- `ssm.region.amazonaws.com` (Systems Manager)

```bash
# Create VPC Endpoint
aws ec2 create-vpc-endpoint \
  --vpc-id vpc-xxx \
  --service-name com.amazonaws.us-west-2.sts \
  --vpc-endpoint-type Interface \
  --subnet-ids subnet-xxx \
  --security-group-ids sg-xxx
```

</details>

### 4. ¿Cuál NO es una consideración al configurar la red de Pod (CIDR) en un entorno de Hybrid Nodes?

A. Evitar conflictos de CIDR con la red on-premises
B. Separar el CIDR de VPC y el CIDR de Pod
C. El CIDR de Pod debe ser un rango /8
D. Evitar la superposición de CIDR de Pod entre clusters

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C. El CIDR de Pod debe ser un rango /8**

**Explicación:**
El CIDR de Pod no necesita ser un rango /8. Normalmente se usan rangos de /16 a /24. Consideraciones clave:

- **Prevención de conflictos de CIDR**: Sin superposición entre redes on-premises, VPC y Pod
- **Tamaño adecuado**: Determinar el tamaño del CIDR según el número esperado de Pods
- **Enrutabilidad**: El CIDR de Pod debe ser enrutable desde on-premises

```yaml
# Configure Pod CIDR in nodeadm settings
apiVersion: node.eks.aws/v1alpha1
kind: NodeConfig
spec:
  kubelet:
    config:
      podCIDR: "10.244.0.0/16"
```

| Network Type | Recommended CIDR Example |
|--------------|-------------------------|
| VPC | 10.0.0.0/16 |
| Pod | 10.244.0.0/16 |
| Service | 10.100.0.0/16 |
| On-premises | 192.168.0.0/16 |

</details>

### 5. ¿Qué dirección IP se usa comúnmente como dirección del servidor DNS del cluster al configurar DNS para Hybrid Nodes?

A. 8.8.8.8
B. 10.100.0.10
C. 192.168.1.1
D. 169.254.169.254

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. 10.100.0.10**

**Explicación:**
En clusters de EKS, el Service de CoreDNS normalmente usa una IP fija dentro del rango de Service CIDR. El valor predeterminado es `10.100.0.10`.

```yaml
# Configure cluster DNS in nodeadm settings
apiVersion: node.eks.aws/v1alpha1
kind: NodeConfig
spec:
  kubelet:
    config:
      clusterDNS:
        - 10.100.0.10
      clusterDomain: cluster.local
```

```bash
# Check CoreDNS service IP
kubectl get svc -n kube-system kube-dns

# Test DNS resolution
kubectl run test --image=busybox --rm -it -- nslookup kubernetes.default
```

</details>

### 6. ¿Cuál es la latencia de red recomendada para la comunicación entre Hybrid Nodes y nodes en la nube?

A. 500 ms o menos
B. 200 ms o menos
C. 100 ms o menos
D. 50 ms o menos

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C. 100 ms o menos**

**Explicación:**
Se recomienda una latencia de red de 100 ms o menos para una comunicación estable con el servidor Kubernetes API.

| Latency | Impact |
|---------|--------|
| < 50ms | Optimal (Direct Connect recommended) |
| 50-100ms | Good (VPN usable) |
| 100-200ms | Warning (some timeouts possible) |
| > 200ms | Unsuitable (frequent disconnections) |

```bash
# Measure latency
ping -c 10 <eks-api-endpoint>

# Measure TCP connection time
curl -w "Connect: %{time_connect}s\n" -o /dev/null -s https://<eks-api-endpoint>
```

El uso de Direct Connect puede lograr una latencia constante inferior a 10 ms.

</details>
