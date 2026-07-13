# Cuestionario sobre la configuración de un entorno air-gap para EKS Hybrid Nodes

> **Documento relacionado**: [Configuración de entorno air-gap](../../eks-hybrid-nodes/03-airgap-setup.md)

## Preguntas de opción múltiple

### 1. ¿Cuál NO es un tipo válido de política de replicación en Harbor?

A. Push-based
B. Pull-based
C. Event-based
D. Sync-based

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: D. Sync-based**

**Explicación:**
Harbor admite políticas de replicación Push-based, Pull-based y Event-based. "Sync-based" no es un término oficial de Harbor.

**Tipos de políticas de replicación de Harbor:**
1. **Push-based**: Push desde el Harbor de origen hacia el registro de destino
2. **Pull-based**: El Harbor de destino hace pull de las imágenes desde el origen
3. **Event-based**: Replicación automática ante eventos de push de imágenes

```yaml
# Harbor Replication Policy API Example
POST /api/v2.0/replication/policies
{
  "name": "ecr-replication",
  "trigger": {
    "type": "event_based"
  },
  "filters": [
    {"type": "name", "value": "myapp/**"},
    {"type": "tag", "value": "v*"}
  ]
}
```

</details>

### 2. ¿Qué tipo de Secret se usa al integrar un registro privado de Harbor con Kubernetes?

A. Opaque
B. kubernetes.io/dockerconfigjson
C. kubernetes.io/tls
D. kubernetes.io/service-account-token

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. kubernetes.io/dockerconfigjson**

**Explicación:**
La información de autenticación del registro Docker/Container se almacena como un Secret de tipo `kubernetes.io/dockerconfigjson`.

```bash
# Create Harbor Registry Secret
kubectl create secret docker-registry harbor-secret \
  --docker-server=harbor.example.com \
  --docker-username=admin \
  --docker-password=Harbor12345 \
  --docker-email=admin@example.com
```

```yaml
# Use imagePullSecrets in Pod
apiVersion: v1
kind: Pod
metadata:
  name: my-app
spec:
  containers:
  - name: app
    image: harbor.example.com/project/my-app:v1
  imagePullSecrets:
  - name: harbor-secret
```

</details>

### 3. ¿Cuál es el escáner de vulnerabilidades predeterminado que proporciona Harbor para el escaneo de imágenes?

A. Clair
B. Trivy
C. Anchore
D. Snyk

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Trivy**

**Explicación:**
Desde Harbor 2.0, Trivy se incluye como el escáner de vulnerabilidades predeterminado. Clair también se puede usar opcionalmente.

```bash
# Harbor Vulnerability Scan API
POST /api/v2.0/projects/{project_name}/repositories/{repository_name}/artifacts/{reference}/scan

# Get Scan Results
GET /api/v2.0/projects/{project_name}/repositories/{repository_name}/artifacts/{reference}/additions/vulnerabilities
```

**Configuración de la política de escaneo de Harbor:**
- Projects > Configuration > Vulnerability scanning
- Escanear automáticamente las imágenes al hacer push: habilitado
- Impedir que se ejecuten imágenes vulnerables: habilitado (umbral de severidad de CVE)

</details>

### 4. ¿Cuál es la definición más precisa de un entorno air-gap?

A. Un entorno con conexión a internet lenta
B. Un entorno físicamente aislado de redes externas
C. Un entorno conectado solo mediante VPN
D. Un entorno con firewalls instalados

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Un entorno físicamente aislado de redes externas**

**Explicación:**
Un entorno air-gap está separado físicamente de internet o de redes externas por razones de seguridad. Se usa habitualmente en:

- Instalaciones militares/de defensa
- Sistemas centrales de instituciones financieras
- Sistemas de control de plantas nucleares
- Sistemas de procesamiento de datos sensibles de instituciones sanitarias

```
Air-gap environment characteristics:
+------------------+     Physical isolation     +------------------+
|   External       | <---- No connection ---->  |   Air-gap        |
|   Network        |                            |   Environment    |
| (Internet, Cloud)|                            | (On-premises DC) |
+------------------+                            +------------------+
```

En entornos air-gap, todo el software y todas las imágenes deben transferirse sin conexión.

</details>

### 5. ¿Cuál es la secuencia correcta para replicar imágenes de contenedor en Harbor en un entorno air-gap?

A. Instalar Harbor -> Etiquetar la imagen -> Hacer push de la imagen -> Hacer pull de la imagen
B. Hacer pull de la imagen -> Guardar la imagen -> Transferencia offline -> Cargar y hacer push a Harbor
C. Instalar Harbor -> Conexión directa a ECR -> Sincronización automática
D. Crear la imagen -> Despliegue directo -> Omitir Harbor

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Hacer pull de la imagen -> Guardar la imagen -> Transferencia offline -> Cargar y hacer push a Harbor**

**Explicación:**
En entornos air-gap no hay conexión a internet, por lo que las imágenes deben transferirse manualmente:

```bash
# 1. Pull image on internet-connected system
docker pull nginx:1.25

# 2. Save image to tar file
docker save nginx:1.25 -o nginx-1.25.tar

# 3. Offline transfer (USB, external hard drive, etc.)
# Physically move media to air-gap environment

# 4. Load image in air-gap environment
docker load -i nginx-1.25.tar

# 5. Tag and push to Harbor
docker tag nginx:1.25 harbor.airgap.local/library/nginx:1.25
docker push harbor.airgap.local/library/nginx:1.25
```

Para gestionar grandes cantidades de imágenes, herramientas como `skopeo` o `crane` son más eficientes.

</details>

### 6. ¿Cuál es el método correcto para la instalación offline de nodeadm en un entorno air-gap?

A. Descargar directamente desde GitHub usando curl
B. apt-get install nodeadm
C. Descargar previamente los binarios y las dependencias para la instalación offline
D. pip install nodeadm

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C. Descargar previamente los binarios y las dependencias para la instalación offline**

**Explicación:**
En entornos air-gap, el acceso a internet no es posible, por lo que todos los archivos necesarios deben prepararse con antelación:

```bash
# Prepare on internet-connected system
# 1. Download nodeadm binary
curl -L -o nodeadm https://github.com/awslabs/amazon-eks-ami/releases/download/nodeadm-v0.1.0/nodeadm-linux-amd64

# 2. Download required dependency packages (e.g., Ubuntu)
apt-get download containerd.io kubelet kubectl

# 3. Transfer all files to air-gap environment

# Install in air-gap environment
# 4. Install nodeadm
chmod +x nodeadm
sudo mv nodeadm /usr/local/bin/

# 5. Install dependency packages
sudo dpkg -i containerd.io_*.deb kubelet_*.deb kubectl_*.deb

# 6. Run nodeadm
sudo nodeadm init --config-source file://nodeadm-config.yaml
```

</details>

### 7. ¿Cuál NO es una variable de entorno que deba configurarse al configurar un servidor proxy en un entorno air-gap?

A. HTTP_PROXY
B. HTTPS_PROXY
C. NO_PROXY
D. FTP_PROXY

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: D. FTP_PROXY**

**Explicación:**
Las variables de entorno de proxy que se usan habitualmente en entornos de contenedores y Kubernetes son HTTP_PROXY, HTTPS_PROXY y NO_PROXY. FTP_PROXY rara vez se usa.

```bash
# Set proxy environment variables
export HTTP_PROXY=http://proxy.company.local:8080
export HTTPS_PROXY=http://proxy.company.local:8080
export NO_PROXY=localhost,127.0.0.1,.cluster.local,10.0.0.0/8

# containerd proxy configuration
sudo mkdir -p /etc/systemd/system/containerd.service.d
cat <<EOF | sudo tee /etc/systemd/system/containerd.service.d/proxy.conf
[Service]
Environment="HTTP_PROXY=http://proxy.company.local:8080"
Environment="HTTPS_PROXY=http://proxy.company.local:8080"
Environment="NO_PROXY=localhost,127.0.0.1,.cluster.local"
EOF

sudo systemctl daemon-reload
sudo systemctl restart containerd
```

**Direcciones que se deben incluir en NO_PROXY:**
- Servicios internos del cluster (*.cluster.local)
- CIDR de Pod/Service
- Rango de IP de Node
- Dirección del registro Harbor

</details>

### 8. ¿Cuál NO es un elemento válido de la lista de verificación para comprobar que un entorno air-gap está listo?

A. Accesibilidad del registro Harbor
B. Presencia de las imágenes de contenedor requeridas
C. Prueba de velocidad de conexión a internet
D. Capacidad de resolución DNS

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C. Prueba de velocidad de conexión a internet**

**Explicación:**
Por definición, un entorno air-gap no tiene conexión a internet, por lo que una prueba de velocidad de internet no tiene sentido. Lista de verificación para comprobar la preparación de air-gap:

```bash
# 1. Verify Harbor registry access
curl -k https://harbor.airgap.local/api/v2.0/health

# 2. Verify required images exist
docker pull harbor.airgap.local/library/pause:3.9

# 3. Verify DNS resolution
nslookup harbor.airgap.local

# 4. Verify nodeadm binary
nodeadm version

# 5. Verify dependency packages
dpkg -l | grep -E "containerd|kubelet"

# 6. Verify TLS certificates
openssl s_client -connect harbor.airgap.local:443 -showcerts
```

**Ejemplo de script de verificación:**
```bash
#!/bin/bash
echo "=== Air-gap Environment Verification ==="

# Harbor connection
if curl -sk https://harbor.airgap.local/api/v2.0/health | grep -q "healthy"; then
  echo "[OK] Harbor is healthy"
else
  echo "[FAIL] Harbor connection failed"
fi

# Required images check
REQUIRED_IMAGES="pause:3.9 coredns:v1.10.1"
for img in $REQUIRED_IMAGES; do
  if docker manifest inspect harbor.airgap.local/library/$img > /dev/null 2>&1; then
    echo "[OK] $img exists"
  else
    echo "[FAIL] $img missing"
  fi
done
```

</details>

### 9. ¿Cuál es el método recomendado para actualizar imágenes de contenedor al operar EKS Hybrid Nodes en un entorno air-gap?

A. Ejecutar docker pull directamente en los Nodes
B. Establecer un proceso periódico de replicación de imágenes y transferencia offline
C. Usar solo versiones fijas sin actualizaciones de imágenes
D. Permitir temporalmente la conexión a internet

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Establecer un proceso periódico de replicación de imágenes y transferencia offline**

**Explicación:**
Los entornos air-gap requieren un proceso sistemático de gestión de imágenes:

```
Image Update Workflow:

[Internet-connected Environment]    [Air-gap Environment]
+-----------------------+           +-----------------------+
| 1. Check/download     |           | 4. Load images        |
|    image list         |           |                       |
| 2. Vulnerability scan | --------> | 5. Push to Harbor     |
| 3. Package as tar     | Offline   | 6. Update deployments |
+-----------------------+ Transfer  +-----------------------+
```

```bash
# Image list management (images.txt)
public.ecr.aws/eks-distro/kubernetes/pause:3.9
public.ecr.aws/eks-distro/coredns/coredns:v1.10.1
docker.io/library/nginx:1.25

# Batch download script
#!/bin/bash
while read -r image; do
  echo "Pulling $image..."
  docker pull "$image"
  name=$(echo "$image" | tr '/:' '_')
  docker save "$image" -o "${name}.tar"
done < images.txt

# Batch upload script (air-gap environment)
#!/bin/bash
for tarfile in *.tar; do
  docker load -i "$tarfile"
  # Retag and push to Harbor
done
```

**Recomendaciones:**
- Establecer ciclos mensuales o trimestrales de actualización de imágenes
- Establecer procedimientos de actualización de emergencia para parches de vulnerabilidades de seguridad
- Firma de imágenes y verificación de integridad

</details>

### 10. ¿Cuál es el método correcto para optimizar el ancho de banda al replicar imágenes en Harbor?

A. Transferir de nuevo imágenes completas cada vez
B. Usar transferencia incremental basada en capas y compresión
C. Procesar de la misma manera independientemente del tamaño de la imagen
D. Reconstruir cada vez en lugar de replicar

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Usar transferencia incremental basada en capas y compresión**

**Explicación:**
Las imágenes de contenedor están compuestas por capas, y transferir solo las capas modificadas puede ahorrar ancho de banda de forma significativa:

```bash
# Efficient image copy using skopeo
skopeo copy \
  --src-tls-verify=false \
  docker://source-registry.com/myapp:v1 \
  docker://harbor.airgap.local/myapp:v1

# Layer-based copy using crane
crane copy source-registry.com/myapp:v1 harbor.airgap.local/myapp:v1
```

**Estrategias de optimización:**

| Método | Descripción | Ahorro |
|--------|-------------|--------|
| Caché de capas | Transferir solo las capas modificadas | 50-80% |
| Compresión | Aplicar compresión gzip/zstd | 30-50% |
| Multi-arquitectura | Replicar solo las arquitecturas requeridas | 50% |
| Filtrado de tags | Replicar solo los tags requeridos | Variable |

```yaml
# Filtering in Harbor replication policy
{
  "filters": [
    {"type": "tag", "value": "v*"},
    {"type": "label", "value": "production=true"}
  ]
}
```

</details>
