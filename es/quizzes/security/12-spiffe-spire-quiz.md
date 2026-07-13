# SPIFFE/SPIRE Quiz

Pon a prueba tu comprensión de la identidad de workloads con SPIFFE/SPIRE con las siguientes preguntas.

---

## Questions

### 1. What is the correct format for a SPIFFE ID?

- A) spiffe://workload/trust-domain/path
- B) spiffe://trust-domain/path
- C) trust-domain://spiffe/path
- D) https://spiffe/trust-domain/path

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) spiffe://trust-domain/path**

**Explicación:**
El formato de SPIFFE ID es un URI con la siguiente estructura:

```
spiffe://trust-domain/path
```

Ejemplos:
```
spiffe://example.org/ns/production/sa/frontend
spiffe://cluster.local/k8s/ns/default/pod/nginx-abc123
spiffe://acme.com/region/us-east-1/service/payment
```

Componentes:
- **spiffe://**: Esquema requerido
- **trust-domain**: Espacio de nombres de identidad de la organización (por ejemplo, example.org)
- **path**: Identificador jerárquico para el workload

</details>

---

### 2. What is the key difference between X.509-SVID and JWT-SVID?

- A) X.509-SVID es para autenticación, JWT-SVID es para autorización
- B) X.509-SVID es para conexiones mTLS, JWT-SVID es para autenticación de API
- C) Son idénticos en función
- D) X.509-SVID caduca más rápido que JWT-SVID

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) X.509-SVID es para conexiones mTLS, JWT-SVID es para autenticación de API**

**Explicación:**
SPIFFE admite dos tipos de SVID (SPIFFE Verifiable Identity Document):

**X.509-SVID:**
- Se usa para conexiones mTLS (mutual TLS)
- Contiene el SPIFFE ID en el URI SAN (Subject Alternative Name)
- De larga duración (horas a días)
- Ideal para: mTLS de Service a Service

**JWT-SVID:**
- Se usa para autenticación de API (encabezados HTTP)
- Contiene el SPIFFE ID en la claim `sub`
- De corta duración (minutos)
- Ideal para: API REST, serverless, llamadas entre redes

```yaml
# X.509-SVID use case
service-a --mTLS--> service-b

# JWT-SVID use case
service-a --HTTP + JWT Bearer--> API Gateway
```

</details>

---

### 3. What is the primary role of the SPIRE Server?

- A) Ejecutar workloads
- B) Emitir SVIDs y gestionar el registro de workloads
- C) Balancear el tráfico
- D) Almacenar secretos de aplicaciones

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Emitir SVIDs y gestionar el registro de workloads**

**Explicación:**
Responsabilidades del SPIRE Server:

```
┌─────────────────────────────────────────────┐
│              SPIRE Server                    │
├─────────────────────────────────────────────┤
│  - Manages trust domain CA                   │
│  - Issues X.509 and JWT SVIDs               │
│  - Stores workload registration entries     │
│  - Performs node attestation                │
│  - Maintains federation relationships       │
└─────────────────────────────────────────────┘
                    │
         ┌─────────┴─────────┐
         ▼                   ▼
   SPIRE Agent          SPIRE Agent
     (Node 1)             (Node 2)
```

Funciones clave:
- Certificate Authority para el trust domain
- API de registro para entradas de workloads
- Verificación de attestation de Node y workload
- Firma y rotación de SVID

</details>

---

### 4. What is the primary role of the SPIRE Agent?

- A) Gestionar la red del cluster
- B) Ejecutarse en Nodes para dar attestation a workloads y entregar SVIDs localmente
- C) Almacenar secretos del cluster
- D) Programar Pods

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Ejecutarse en Nodes para dar attestation a workloads y entregar SVIDs localmente**

**Explicación:**
SPIRE Agent se ejecuta como un DaemonSet en cada Node:

```yaml
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: spire-agent
  namespace: spire
spec:
  template:
    spec:
      containers:
      - name: spire-agent
        image: ghcr.io/spiffe/spire-agent:1.8
        volumeMounts:
        - name: spire-agent-socket
          mountPath: /run/spire/sockets
```

Responsabilidades del Agent:
- Da attestation al SPIRE Server (node attestation)
- Verifica la identidad del workload local (workload attestation)
- Obtiene y almacena en caché SVIDs desde el Server
- Expone la Workload API (Unix domain socket) a workloads locales
- Gestiona la rotación de SVID

</details>

---

### 5. Which node attestation method is recommended for Amazon EKS?

- A) aws_iid
- B) k8s_sat
- C) k8s_psat
- D) join_token

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) k8s_psat**

**Explicación:**
Métodos de node attestation para Kubernetes:

**k8s_psat (Projected Service Account Token)** - Recomendado para EKS:
```yaml
# SPIRE Server configuration
nodeAttestor "k8s_psat" {
    plugin_data {
        clusters = {
            "eks-cluster" = {
                service_account_allow_list = ["spire:spire-agent"]
                kube_config_file = ""
                allowed_node_label_keys = ["topology.kubernetes.io/zone"]
            }
        }
    }
}
```

Por qué k8s_psat para EKS:
- Usa projected service account tokens (más seguros)
- Los tokens están vinculados a una audience y tienen límite de tiempo
- Funciona con el proveedor OIDC de EKS
- No se necesitan credenciales del cloud provider en los agents

Alternativas:
- **k8s_sat**: Tokens de service account heredados (menos seguros)
- **aws_iid**: Identidad de instancia EC2 (para entornos no EKS)

</details>

---

### 6. What selector types does k8s workload attestation support?

- A) Solo imagen del container
- B) Namespace, service account, etiquetas de Pod e imagen del container
- C) Solo dirección IP
- D) Solo nombre de Node

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Namespace, service account, etiquetas de Pod e imagen del container**

**Explicación:**
Selectors de Kubernetes workload attestation:

```bash
# Create registration entry with selectors
spire-server entry create \
    -spiffeID spiffe://example.org/ns/production/sa/frontend \
    -parentID spiffe://example.org/agent/node1 \
    -selector k8s:ns:production \
    -selector k8s:sa:frontend \
    -selector k8s:pod-label:app:frontend \
    -selector k8s:container-image:nginx:1.25
```

Selectors disponibles:
| Selector | Example | Description |
|----------|---------|-------------|
| k8s:ns | k8s:ns:production | Namespace |
| k8s:sa | k8s:sa:frontend | ServiceAccount |
| k8s:pod-label | k8s:pod-label:app:web | Pod labels |
| k8s:container-image | k8s:container-image:nginx | Container image |
| k8s:pod-name | k8s:pod-name:nginx-xyz | Specific pod |
| k8s:pod-uid | k8s:pod-uid:abc-123 | Pod UID |

</details>

---

### 7. What is the purpose of the SPIFFE CSI Driver?

- A) Gestionar persistent volumes
- B) Montar SVIDs directamente en Pods sin sidecars
- C) Cifrar el almacenamiento de Node
- D) Aplicar políticas de red

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Montar SVIDs directamente en Pods sin sidecars**

**Explicación:**
El SPIFFE CSI Driver proporciona un enfoque sin sidecar para la entrega de SVID:

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: my-workload
spec:
  containers:
  - name: app
    image: my-app:latest
    volumeMounts:
    - name: spiffe
      mountPath: /run/spiffe/certs
      readOnly: true
  volumes:
  - name: spiffe
    csi:
      driver: "csi.spiffe.io"
      readOnly: true
```

Beneficios:
- No se necesita un container sidecar
- Los SVIDs se montan automáticamente como archivos
- Rotación transparente de certificados
- Menor complejidad del Pod
- Funciona con cualquier aplicación que espere certificados basados en archivos

El CSI driver se comunica con el SPIRE Agent para obtener y montar SVIDs.

</details>

---

### 8. What does SPIFFE Federation enable?

- A) Replicación de base de datos
- B) Comunicación entre trust domains de deployments SPIFFE separados
- C) Programación de Pods entre clusters
- D) Sincronización de secretos

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Comunicación entre trust domains de deployments SPIFFE separados**

**Explicación:**
SPIFFE Federation permite que workloads en distintos trust domains se autentiquen:

```
┌─────────────────────┐      Federation      ┌─────────────────────┐
│  Trust Domain A     │◄──────────────────►│  Trust Domain B      │
│  example.org        │     Bundle Exchange │  partner.com         │
├─────────────────────┤                      ├─────────────────────┤
│  spiffe://example.  │                      │  spiffe://partner.   │
│  org/service/api    │   ─── mTLS ───►     │  com/service/db      │
└─────────────────────┘                      └─────────────────────┘
```

Configuración:
```yaml
# SPIRE Server federation config
federatesWith "partner.com" {
    bundleEndpointURL = "https://spire.partner.com:8443"
    bundleEndpointProfile "https_spiffe" {
        endpointSPIFFEID = "spiffe://partner.com/spire/server"
    }
}
```

Casos de uso:
- Deployments multi-cloud
- Integraciones con partners
- Fusiones y adquisiciones
- Comunicación zero-trust entre organizaciones

</details>

---

### 9. How does SPIFFE/SPIRE compare to IAM Roles for Service Accounts (IRSA)?

- A) IRSA es independiente de la plataforma, SPIFFE es solo para AWS
- B) SPIFFE proporciona identidad independiente de la plataforma, IRSA es específico de AWS
- C) Son tecnologías idénticas
- D) SPIFFE solo funciona con Azure

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) SPIFFE proporciona identidad independiente de la plataforma, IRSA es específico de AWS**

**Explicación:**
Comparación de SPIFFE/SPIRE vs IRSA:

| Feature | SPIFFE/SPIRE | IRSA |
|---------|--------------|------|
| Platform | Any (multi-cloud) | AWS only |
| Identity Format | SPIFFE ID (URI) | IAM Role ARN |
| Credential Type | X.509/JWT SVID | AWS STS token |
| Service-to-Service | Native mTLS | Not supported |
| AWS Service Access | Via JWT exchange | Direct |
| Setup Complexity | Higher | Lower (EKS native) |

Cuándo usar cada uno:
- **IRSA**: Workloads nativos de AWS que acceden a servicios de AWS
- **SPIFFE/SPIRE**: Multi-cloud, service mesh, requisitos de mTLS

Puedes usar ambos juntos:
```
Pod --SPIFFE--> Service Mesh (mTLS)
Pod --IRSA--> AWS Services (S3, DynamoDB)
```

</details>

---

### 10. What are best practices for naming trust domains in SPIFFE?

- A) Usar cadenas aleatorias
- B) Usar direcciones IP
- C) Usar nombres con estilo DNS que controle tu organización
- D) Usar números secuenciales

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Usar nombres con estilo DNS que controle tu organización**

**Explicación:**
Mejores prácticas para nombrar trust domains:

**Patrones recomendados:**
```
# Organization domain
spiffe://example.com/...

# Environment-specific
spiffe://prod.example.com/...
spiffe://staging.example.com/...

# Region-specific
spiffe://us-east.example.com/...
```

**Mejores prácticas:**
1. Usa dominios que poseas (evita colisiones)
2. Mantén estables los trust domains (cambiarlos es disruptivo)
3. Considera la separación por entorno
4. Planifica la federation desde el inicio

**Antipatrones que debes evitar:**
```
# Bad: Generic names
spiffe://cluster/...
spiffe://kubernetes/...

# Bad: Temporary names
spiffe://test123/...

# Bad: IP addresses
spiffe://10.0.0.1/...
```

Los nombres de trust domain aparecen en todos los SVIDs y logs, así que elige identificadores significativos y estables.

</details>

---

## Score Calculation

- **9-10 correctas**: Excelente - Tienes una comprensión profunda de SPIFFE/SPIRE.
- **7-8 correctas**: Bien - Tienes un dominio sólido de los conceptos clave.
- **5-6 correctas**: Regular - Hay áreas que necesitan estudio adicional.
- **4 o menos**: Revisa la documentación nuevamente.

## Related Documentation

- [Identidad de workloads con SPIFFE/SPIRE](../../security/12-spiffe-spire.md)
