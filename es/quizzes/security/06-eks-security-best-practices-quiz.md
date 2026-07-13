# Cuestionario sobre mejores prácticas de seguridad de EKS

Pon a prueba tu comprensión de las mejores prácticas de seguridad de Amazon EKS con las siguientes preguntas.

***

## Preguntas

### 1. ¿Qué método de autenticación usa un Pod cuando llama a las AWS APIs con IRSA (IAM Roles for Service Accounts)?

* A) Clave de acceso de IAM User
* B) EC2 Instance Profile
* C) AssumeRoleWithWebIdentity basado en token OIDC
* D) Credenciales almacenadas en Kubernetes Secret

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: C) AssumeRoleWithWebIdentity basado en token OIDC**

**Explicación:** Cómo funciona IRSA:

1. El OIDC Provider del cluster de EKS emite un token de ServiceAccount
2. El Pod llama a la AWS STS `AssumeRoleWithWebIdentity` API
3. El token OIDC se valida y se emiten credenciales temporales
4. El Pod llama a las AWS APIs con credenciales temporales

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: s3-reader
  annotations:
    eks.amazonaws.com/role-arn: arn:aws:iam::123456789012:role/S3ReaderRole
```

IRSA permite una gestión de permisos detallada a nivel de Pod en lugar de a nivel de node.

</details>

***

### 2. ¿Cuál es la principal ventaja de EKS Pod Identity en comparación con IRSA?

* A) Cifrado más fuerte
* B) Rendimiento más rápido
* C) No requiere configuración de OIDC Provider, gestión simplificada
* D) Compatibilidad con más servicios de AWS

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: C) No requiere configuración de OIDC Provider, gestión simplificada**

**Explicación:** Beneficios de EKS Pod Identity:

* No requiere configuración de OIDC Provider
* IAM Role Trust Policy simplificada
* Gestión automática de credenciales mediante Pod Identity Agent
* Acceso entre cuentas simplificado

```bash
# Pod Identity association (simple CLI setup)
aws eks create-pod-identity-association \
  --cluster-name my-cluster \
  --namespace production \
  --service-account myapp-sa \
  --role-arn arn:aws:iam::123456789012:role/MyAppRole
```

IRSA requiere configuración de OIDC Provider y una Trust Policy compleja para cada cluster.

</details>

***

### 3. ¿Cuál NO es un requisito para usar Security Groups for Pods?

* A) Tipos de instancia basados en Nitro
* B) Plugin Amazon VPC CNI
* C) Fargate profile
* D) ENIConfig o SecurityGroupPolicy CRD

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: C) Fargate profile**

**Explicación:** Requisitos de Security Groups for Pods:

* **Requerido**: instancias EC2 basadas en Nitro (m5, c5, r5, etc.)
* **Requerido**: plugin Amazon VPC CNI v1.7.7+
* **Requerido**: configuración de SecurityGroupPolicy CRD
* **Opcional**: Fargate (método de configuración independiente)

```yaml
apiVersion: vpcresources.k8s.aws/v1beta1
kind: SecurityGroupPolicy
metadata:
  name: db-access-policy
spec:
  podSelector:
    matchLabels:
      app: backend
  securityGroups:
    groupIds:
      - sg-0123456789abcdef0
```

Fargate asigna una ENI a cada Pod automáticamente, lo que requiere una configuración independiente.

</details>

***

### 4. ¿Cuál es el impacto de configurar el endpoint del Kubernetes API server del cluster de EKS como solo privado?

* A) No se puede usar kubectl en absoluto
* B) Accesible solo desde dentro de la VPC o redes conectadas
* C) No se puede administrar el cluster desde AWS Console
* D) Los worker nodes no pueden conectarse al API server

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Accesible solo desde dentro de la VPC o redes conectadas**

**Explicación:** Cuando se configura un endpoint privado:

* Accesible desde dentro de la VPC
* Accesible desde redes conectadas mediante VPN, Direct Connect, VPC Peering
* No accesible desde Internet público

```bash
# Endpoint configuration
aws eks update-cluster-config \
  --name my-cluster \
  --resources-vpc-config \
    endpointPublicAccess=false,endpointPrivateAccess=true
```

Se recomienda usar solo un endpoint privado por seguridad.

</details>

***

### 5. ¿Qué tipo de amenaza NO detecta AWS GuardDuty EKS Protection?

* A) Comunicación con IPs maliciosas
* B) Actividad de minería de criptomonedas
* C) Uso de recursos del Pod que supera los límites
* D) Conexiones a la red Tor

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: C) Uso de recursos del Pod que supera los límites**

**Explicación:** Amenazas detectadas por GuardDuty EKS Protection:

* Comunicación con direcciones IP maliciosas
* Minería de criptomonedas (abuso de Kubernetes API)
* Conexiones a la red Tor
* Ataques de DNS Rebinding
* Intentos de escalada de privilegios
* Patrones anormales de llamadas a la API

La supervisión del uso de recursos la realizan:

* Kubernetes Metrics Server
* Prometheus/Grafana
* CloudWatch Container Insights

</details>

***

### 6. ¿Qué servicio de AWS NO requiere VPC endpoints en un cluster de EKS?

* A) ECR (dkr, api)
* B) S3
* C) STS
* D) Route 53

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: D) Route 53**

**Explicación:** VPC endpoints recomendados para EKS:

* **ECR (dkr, api)**: descargas de imágenes de contenedor
* **S3**: almacenamiento de capas de imágenes
* **STS**: autenticación de IRSA/Pod Identity
* **CloudWatch Logs**: transmisión de logs
* **EC2, ELB, Auto Scaling**: gestión de nodes

Route 53 es un servicio DNS global que utiliza la resolución DNS estándar, no VPC endpoints.

```bash
# Create required VPC endpoint
aws ec2 create-vpc-endpoint \
  --vpc-id vpc-xxx \
  --service-name com.amazonaws.region.ecr.dkr \
  --vpc-endpoint-type Interface
```

</details>

***

### 7. ¿Qué benchmark se usa al comprobar la seguridad de un cluster de EKS con kube-bench?

* A) PCI-DSS
* B) CIS Kubernetes Benchmark
* C) NIST Cybersecurity Framework
* D) SOC 2

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) CIS Kubernetes Benchmark**

**Explicación:** kube-bench comprueba la seguridad del cluster frente al CIS (Center for Internet Security) Kubernetes Benchmark:

```bash
# Run kube-bench on EKS node
kubectl apply -f https://raw.githubusercontent.com/aquasecurity/kube-bench/main/job-eks.yaml

# Check results
kubectl logs job/kube-bench
```

Elementos de inspección:

* Configuración de Control Plane (algunos N/A porque EKS los administra)
* Configuración de Worker Node
* Políticas y seguridad de Pod
* Network policies
* Logging y auditoría

</details>

***

### 8. ¿Qué beneficio de seguridad proporciona Service Account Token Volume Projection en EKS?

* A) Tamaño reducido del token
* B) Tokens vinculados y configuración de tiempo de expiración
* C) Cifrado del token
* D) Copia de seguridad automática del token

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Tokens vinculados y configuración de tiempo de expiración**

**Explicación:** Beneficios de seguridad de Service Account Token Volume Projection:

* **Tokens vinculados**: válidos solo para un Pod específico
* **Tiempo de expiración**: expiración automática del token (1 hora por defecto)
* **Especificación de audiencia**: válido solo para una audiencia específica

```yaml
spec:
  containers:
    - name: app
      volumeMounts:
        - name: token
          mountPath: /var/run/secrets/tokens
  volumes:
    - name: token
      projected:
        sources:
          - serviceAccountToken:
              path: token
              expirationSeconds: 3600
              audience: sts.amazonaws.com
```

Los tokens heredados nunca expiraban, lo que suponía riesgos si se filtraban.

</details>

***

### 9. ¿Qué escanea Amazon Inspector en un entorno EKS?

* A) Kubernetes manifests
* B) Vulnerabilidades de imágenes de contenedor
* C) IAM policies
* D) Tráfico de red

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Vulnerabilidades de imágenes de contenedor**

**Explicación:** Integración de Amazon Inspector con EKS:

* Escanea imágenes de contenedor almacenadas en ECR
* Escanea imágenes de workloads en ejecución
* Detecta vulnerabilidades de paquetes del sistema operativo
* Detecta vulnerabilidades de paquetes de aplicaciones (npm, pip, etc.)

```bash
# Enable Inspector
aws inspector2 enable \
  --resource-types ECR

# Check scan results
aws inspector2 list-findings \
  --filter-criteria resourceType=AWS_ECR_CONTAINER_IMAGE
```

El escaneo continuo proporciona alertas cuando se descubren nuevos CVEs.

</details>

***

### 10. ¿Qué tipo de log NO se puede habilitar al enviar logs del Control Plane del cluster de EKS a CloudWatch?

* A) api
* B) audit
* C) controllerManager
* D) kubelet

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: D) kubelet**

**Explicación:** Tipos de logs del Control Plane de EKS:

* **api**: logs del API server
* **audit**: logs de auditoría (quién hizo qué)
* **authenticator**: logs de autenticación IAM
* **controllerManager**: logs del controller manager
* **scheduler**: logs del scheduler

Los logs de kubelet se generan en los worker nodes y no son logs del Control Plane.

```bash
# Enable Control Plane logging
aws eks update-cluster-config \
  --name my-cluster \
  --logging '{"clusterLogging":[{"types":["api","audit","authenticator","controllerManager","scheduler"],"enabled":true}]}'
```

</details>

***

### 11. ¿Por qué deben separarse el Node IAM Role y el Pod IAM Role (IRSA) en EKS?

* A) Ahorro de costos
* B) Aplicación del principio de menor privilegio
* C) Mejora del rendimiento
* D) Reducción de la latencia de red

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Aplicación del principio de menor privilegio**

**Explicación:** Importancia de la separación de permisos:

**Node IAM Role (alcance amplio):**

* Accesible por todos los Pods (Instance Metadata)
* Solo permisos básicos como descarga de ECR y logs de CloudWatch

**IRSA (alcance estrecho):**

* Conectado solo a un ServiceAccount específico
* Otorga solo los permisos necesarios por aplicación

```yaml
# Wrong example: S3 full access on Node Role
# -> All Pods can access S3

# Correct example: Grant permissions only to specific Pod via IRSA
apiVersion: v1
kind: ServiceAccount
metadata:
  name: s3-processor
  annotations:
    eks.amazonaws.com/role-arn: arn:aws:iam::xxx:role/S3ProcessorRole
```

</details>

***

### 12. ¿Qué componente es responsable de integrar Kubernetes RBAC con AWS IAM en EKS?

* A) kube-apiserver
* B) aws-auth ConfigMap
* C) aws-iam-authenticator
* D) kube-proxy

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: C) aws-iam-authenticator**

**Explicación:** Flujo de autenticación de EKS:

1. kubectl obtiene un token de AWS STS
2. aws-iam-authenticator valida las credenciales IAM
3. aws-auth ConfigMap mapea IAM -> usuario/grupo de Kubernetes
4. Kubernetes RBAC determina los permisos

```yaml
# aws-auth ConfigMap
apiVersion: v1
kind: ConfigMap
metadata:
  name: aws-auth
  namespace: kube-system
data:
  mapRoles: |
    - rolearn: arn:aws:iam::123456789012:role/DevTeamRole
      username: dev-user
      groups:
        - dev-team
  mapUsers: |
    - userarn: arn:aws:iam::123456789012:user/admin
      username: admin
      groups:
        - system:masters
```

</details>

***

## Cálculo de la puntuación

Calcula 1 punto por pregunta.

| Puntuación | Calificación                                                        |
| ---------- | ------------------------------------------------------------------- |
| 11-12      | Excelente - Nivel de experto en seguridad de EKS                    |
| 8-10       | Bueno - Conceptos básicos comprendidos, revisa funciones avanzadas  |
| 5-7        | Promedio - Se recomienda estudio adicional                          |
| 0-4        | Se necesita aprendizaje básico                                      |

***

## Documentación relacionada

* [Mejores prácticas de seguridad de EKS](https://github.com/Atom-oh/kubernetes-docs/blob/main/en/quizzes/security/06-eks-security-best-practices.md)
* [Pod Security Standards](https://github.com/Atom-oh/kubernetes-docs/blob/main/en/quizzes/security/03-pod-security-standards.md)
* [Gestión de Secrets](https://github.com/Atom-oh/kubernetes-docs/blob/main/en/quizzes/security/05-secrets-management.md)
