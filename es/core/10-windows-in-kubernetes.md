# Windows en Kubernetes

> **Versiones compatibles**: Kubernetes 1.32, 1.33, 1.34
> **Última actualización**: February 11, 2026

Kubernetes se diseñó originalmente para contenedores Linux, pero la compatibilidad de producción con contenedores Windows se añadió a partir de la versión 1.14. En este capítulo, exploraremos cómo ejecutar cargas de trabajo Windows en Kubernetes, la arquitectura, las limitaciones y la compatibilidad con Windows en Amazon EKS.

## Tabla de contenido
1. [Descripción general de los contenedores Windows](#windows-container-overview)
2. [Arquitectura de compatibilidad con Windows en Kubernetes](#kubernetes-windows-support-architecture)
3. [Limitaciones de los nodos Windows](#windows-node-limitations)
4. [Configuración de nodos Windows](#windows-node-setup)
5. [Implementación de contenedores Windows](#deploying-windows-containers)
6. [Redes](#networking)
7. [Almacenamiento](#storage)
8. [Monitoreo y registro](#monitoring-and-logging)
9. [Seguridad](#security)
10. [Compatibilidad con Windows en Amazon EKS](#windows-support-in-amazon-eks)
11. [Prácticas recomendadas](#best-practices)
12. [Conclusión](#conclusion)

## Descripción general de los contenedores Windows

Los contenedores Windows son contenedores que se ejecutan en el sistema operativo Windows, lo que permite contenerizar e implementar aplicaciones Windows.

### Tipos de contenedores Windows

Hay dos tipos de contenedores Windows:

1. **Windows Server Containers**: Al igual que los contenedores Linux, comparten el kernel del sistema operativo host. Son ligeros y se inician rápidamente, pero requieren la misma versión de Windows que el host.

2. **Hyper-V Isolation Containers**: Cada contenedor se ejecuta en una VM ligera, lo que proporciona un mayor nivel de aislamiento. Pueden ejecutar versiones de Windows diferentes de la del host, pero usan más recursos.

El siguiente diagrama muestra las diferencias arquitectónicas entre los dos tipos de contenedores Windows:

![Comparación entre Windows Server Containers, donde varias aplicaciones Windows comparten un runtime de contenedor y el kernel del sistema operativo host, y Hyper-V Isolation Containers, donde cada aplicación se ejecuta en su propia VM ligera con un kernel de Windows dedicado bajo el hipervisor Hyper-V antes de llegar al mismo sistema operativo Windows Server y al hardware físico.](../.gitbook/assets/en-core-10-windows-in-kubernetes-0.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-core-10-windows-in-kubernetes-0.html)

### Imágenes de contenedor Windows

Las imágenes de contenedor Windows se basan en imágenes base proporcionadas por Microsoft:

1. **Windows Server Core**: Una imagen ligera que proporciona un entorno mínimo de Windows Server
2. **Nano Server**: Una imagen ultraligera con una huella menor
3. **Windows**: Una imagen que proporciona un entorno completo de Windows Server

Dockerfile de ejemplo:

```dockerfile
FROM mcr.microsoft.com/windows/servercore:ltsc2019
WORKDIR /app
COPY . .
RUN powershell -Command "Install-WindowsFeature Web-Server"
EXPOSE 80
CMD ["powershell", "-Command", "Start-Service W3SVC; Get-Content -Path 'C:\\inetpub\\logs\\LogFiles\\W3SVC1\\u_ex*' -Wait"]
```

## Arquitectura de compatibilidad con Windows en Kubernetes

La compatibilidad con Windows en Kubernetes se basa en un entorno mixto. Los componentes del control plane siempre se ejecutan en Linux, mientras que los nodos worker pueden ser Linux o Windows.

### Descripción general de la arquitectura

La arquitectura de compatibilidad con Windows en Kubernetes es la siguiente:

1. **Linux Control Plane**: kube-apiserver, kube-controller-manager, kube-scheduler y etcd siempre se ejecutan en Linux.
2. **Linux Worker Nodes**: Ejecutan componentes del sistema (CoreDNS, metrics-server, etc.).
3. **Windows Worker Nodes**: Ejecutan cargas de trabajo de aplicaciones Windows.

![Un control plane exclusivamente Linux (kube-apiserver, kube-controller-manager, kube-scheduler, etcd) administra un clúster mixto, que llega a un nodo worker Linux que ejecuta Pods del sistema como CoreDNS y metrics-server, y a dos nodos worker Windows que ejecutan cada uno kubelet, kube-proxy y contenedores Windows.](../.gitbook/assets/en-core-10-windows-in-kubernetes-1.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-core-10-windows-in-kubernetes-1.html)

### Componentes de nodos Windows

Componentes de Kubernetes que se ejecutan en nodos Windows:

1. **kubelet**: Administra Pods y contenedores en el nodo
2. **kube-proxy**: Administra reglas de red
3. **CNI Plugin**: Configuración de red
4. **CSI Plugin**: Administración del almacenamiento

## Limitaciones de los nodos Windows

Hay varias limitaciones que se deben tener en cuenta al usar nodos Windows en Kubernetes.

### Limitaciones de funcionalidades

1. **Privileged Containers**: Windows no admite contenedores privilegiados.
2. **Host Network Mode**: Los Pods Windows no pueden usar el modo de red del host.
3. **Pod Security Context**: Algunas funcionalidades del contexto de seguridad (runAsUser, fsGroup, etc.) no son compatibles.
4. **DaemonSet**: Los DaemonSets que se ejecutan en nodos Windows requieren consideraciones especiales.
5. **emptyDir Volumes**: Los volúmenes emptyDir basados en memoria no son compatibles con Windows.
6. **Resource Limits**: Los límites de CPU se aplican de manera diferente en Windows.

### Limitaciones de red

1. **Network Mode**: Windows solo admite redes L3.
2. **Service Types**: Los nodos Windows tienen limitaciones en algunos tipos de Service.
3. **Load Balancing**: Algunas funcionalidades de balanceo de carga pueden estar limitadas.

### Compatibilidad de versiones del sistema operativo

Los contenedores Windows tienen consideraciones importantes de compatibilidad con la versión del sistema operativo host:

| Imagen base del contenedor | Versiones compatibles del sistema operativo host |
|---------------------|---------------------------|
| Windows Server 2019 | Windows Server 2019 |
| Windows Server 2022 | Windows Server 2022 |

El aislamiento de Hyper-V puede relajar estas limitaciones, pero requiere recursos adicionales.
## Configuración de nodos Windows

Exploremos el proceso de agregar nodos Windows a un clúster de Kubernetes.

### Requisitos previos

Antes de configurar nodos Windows, verifique lo siguiente:

1. **Kubernetes Version**: 1.14 o posterior
2. **Windows Version**: Windows Server 2019 o posterior
3. **Network Plugin**: Plugin CNI compatible con Windows (Calico, Flannel, etc.)
4. **Container Runtime**: Docker, containerd, etc.

### Preparación de nodos Windows

Pasos para preparar un nodo Windows:

1. **Install Windows Server**: Instale Windows Server 2019 o posterior
2. **Enable Container Feature**:

```powershell
Install-WindowsFeature -Name Containers
Restart-Computer -Force
```

3. **Install Docker**:

```powershell
Install-Module -Name DockerMsftProvider -Repository PSGallery -Force
Install-Package -Name Docker -ProviderName DockerMsftProvider -Force
Restart-Computer -Force
```

4. **Install Kubernetes Components**:

```powershell
# Create directory
mkdir -p c:\k

# Download kubelet, kubeadm, kubectl
curl.exe -LO https://dl.k8s.io/v1.22.0/bin/windows/amd64/kubelet.exe
curl.exe -LO https://dl.k8s.io/v1.22.0/bin/windows/amd64/kubectl.exe
curl.exe -LO https://dl.k8s.io/v1.22.0/bin/windows/amd64/kube-proxy.exe
curl.exe -LO https://github.com/kubernetes-sigs/sig-windows-tools/releases/latest/download/wins.exe

# Move files to C:\k
mv kubelet.exe C:\k
mv kubectl.exe C:\k
mv kube-proxy.exe C:\k
mv wins.exe C:\k
```

5. **Configure Network**:

```powershell
# Set firewall rules
New-NetFirewallRule -Name kubelet -DisplayName 'kubelet' -Enabled True -Direction Inbound -Protocol TCP -Action Allow -LocalPort 10250
New-NetFirewallRule -Name https -DisplayName 'https' -Enabled True -Direction Inbound -Protocol TCP -Action Allow -LocalPort 443
New-NetFirewallRule -Name http -DisplayName 'http' -Enabled True -Direction Inbound -Protocol TCP -Action Allow -LocalPort 80
```

### Unión de un nodo Windows mediante kubeadm

Genere un token de unión en el control plane Linux:

```bash
kubeadm token create --print-join-command
```

Ejecute el comando de unión en el nodo Windows:

```powershell
# Run kubeadm join command
kubeadm join <control-plane-host>:<control-plane-port> --token <token> --discovery-token-ca-cert-hash sha256:<hash>

# Register and start kubelet service
sc.exe create kubelet binPath= "C:\k\kubelet.exe --windows-service --kubeconfig=C:\k\config"
Start-Service kubelet
```

### Configuración de etiquetas de nodos Windows

Establezca las etiquetas adecuadas en los nodos Windows para controlar la programación de cargas de trabajo:

```bash
kubectl label node <windows-node-name> kubernetes.io/os=windows
kubectl label node <windows-node-name> kubernetes.io/arch=amd64
```

## Implementación de contenedores Windows

Exploremos cómo implementar contenedores Windows en Kubernetes.

### Uso de Node Selector

Al implementar cargas de trabajo Windows, use un node selector para asegurarse de que se programen en nodos Windows:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: iis-deployment
spec:
  replicas: 2
  selector:
    matchLabels:
      app: iis
  template:
    metadata:
      labels:
        app: iis
    spec:
      nodeSelector:
        kubernetes.io/os: windows
      containers:
      - name: iis
        image: mcr.microsoft.com/windows/servercore/iis:windowsservercore-ltsc2019
        resources:
          limits:
            cpu: 1
            memory: 800Mi
          requests:
            cpu: .1
            memory: 300Mi
        ports:
        - containerPort: 80
```

### Solicitudes y límites de recursos

Las solicitudes y los límites de recursos para los contenedores Windows se manejan de manera diferente que para los contenedores Linux:

1. **CPU Limits**: Los límites de CPU se aplican de manera diferente en Windows. Por ejemplo, un límite de CPU de 1 significa que se puede usar el 100 % de un único núcleo de CPU.
2. **Memory Limits**: Los contenedores Windows respetan los límites de memoria, pero algunos procesos del sistema pueden generar una sobrecarga adicional.

### Personalización de contenedores

Ejecución de scripts personalizados en contenedores Windows:

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: windows-custom-script
spec:
  nodeSelector:
    kubernetes.io/os: windows
  containers:
  - name: windows-container
    image: mcr.microsoft.com/windows/servercore:ltsc2019
    command:
    - powershell.exe
    - -Command
    - |
      while ($true) {
        Write-Host "Hello from Windows container"
        Start-Sleep -Seconds 10
      }
```

### Pods con varios contenedores

Windows también admite Pods con varios contenedores, pero con algunas limitaciones:

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: windows-multi-container
spec:
  nodeSelector:
    kubernetes.io/os: windows
  containers:
  - name: web
    image: mcr.microsoft.com/windows/servercore/iis:windowsservercore-ltsc2019
    ports:
    - containerPort: 80
  - name: logger
    image: mcr.microsoft.com/windows/servercore:ltsc2019
    command:
    - powershell.exe
    - -Command
    - |
      while ($true) {
        Get-Content -Path 'C:\inetpub\logs\LogFiles\W3SVC1\u_ex*' -Wait
      }
```

## Redes

Las redes en nodos Windows tienen características diferentes de las de los nodos Linux.

El siguiente diagrama muestra la arquitectura de red de un clúster de Kubernetes con nodos Windows y Linux mixtos:

![Una solicitud de cliente llega a un Kubernetes Service, que balancea la carga entre Pods Linux y Windows por igual, mientras que los Pods forman una red de malla plana independientemente del sistema operativo del nodo.](../.gitbook/assets/en-core-10-windows-in-kubernetes-2.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-core-10-windows-in-kubernetes-2.html)

### Plugins de red compatibles

Plugins de red compatibles con nodos Windows:

1. **Flannel**: Modo VXLAN o host-gw
2. **Calico**: Modo VXLAN
3. **Antrea**: Redes basadas en OVS
4. **Azure CNI**: Se usa en entornos Azure
5. **AWS VPC CNI**: Se usa en entornos AWS

### Ejemplo de configuración de Flannel

Configuración de red Windows mediante Flannel:

```yaml
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: kube-flannel-ds-windows
  namespace: kube-system
  labels:
    tier: node
    app: flannel
spec:
  selector:
    matchLabels:
      app: flannel
  template:
    metadata:
      labels:
        tier: node
        app: flannel
    spec:
      affinity:
        nodeAffinity:
          requiredDuringSchedulingIgnoredDuringExecution:
            nodeSelectorTerms:
            - matchExpressions:
              - key: kubernetes.io/os
                operator: In
                values:
                - windows
      hostNetwork: true
      containers:
      - name: kube-flannel
        image: sigwindowstools/flannel:v0.13.0
        command:
        - powershell
        args:
        - -file
        - /opt/bin/flannel-host.ps1
        env:
        - name: POD_NAME
          valueFrom:
            fieldRef:
              fieldPath: metadata.name
        - name: POD_NAMESPACE
          valueFrom:
            fieldRef:
              fieldPath: metadata.namespace
        volumeMounts:
        - name: host-run
          mountPath: /run
        - name: cni
          mountPath: /etc/cni/net.d
        - name: flannel-cfg
          mountPath: /etc/kube-flannel/
      volumes:
      - name: host-run
        hostPath:
          path: /run
      - name: cni
        hostPath:
          path: /etc/cni/net.d
      - name: flannel-cfg
        configMap:
          name: kube-flannel-cfg
```

### Exposición de Services

Cómo exponer Services en nodos Windows:

```yaml
apiVersion: v1
kind: Service
metadata:
  name: iis-service
spec:
  selector:
    app: iis
  ports:
  - port: 80
    targetPort: 80
  type: LoadBalancer
```

### Políticas de red

Para usar políticas de red en nodos Windows, necesita un plugin CNI compatible con políticas de red (por ejemplo, Calico):

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-frontend-to-backend
  namespace: default
spec:
  podSelector:
    matchLabels:
      app: backend
      os: windows
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: frontend
    ports:
    - protocol: TCP
      port: 80
```

## Almacenamiento

Exploremos las opciones de almacenamiento disponibles en nodos Windows.

El siguiente diagrama muestra varias opciones de almacenamiento disponibles en nodos Windows:

![Un contenedor Windows en un Pod Windows monta volúmenes emptyDir y hostPath en el nodo Windows (hostPath respaldado por el disco del nodo), volúmenes ConfigMap y Secret entregados por la API de Kubernetes, y un PersistentVolume que llega a Azure Disk/File, AWS EBS o un recurso compartido SMB mediante un driver CSI.](../.gitbook/assets/en-core-10-windows-in-kubernetes-3.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-core-10-windows-in-kubernetes-3.html)

### Tipos de volumen compatibles

Tipos de volumen compatibles con nodos Windows:

1. **emptyDir**: Almacenamiento temporal (emptyDir basado en memoria no compatible)
2. **hostPath**: Sistema de archivos del nodo host
3. **configMap**: Datos de configuración
4. **secret**: Datos confidenciales
5. **azureFile**: Almacenamiento Azure File
6. **awsElasticBlockStore**: Volúmenes AWS EBS
7. **azureDisk**: Almacenamiento Azure Disk
8. **CSI**: Drivers de Container Storage Interface

### Ejemplo de volumen emptyDir

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: windows-emptydir
spec:
  nodeSelector:
    kubernetes.io/os: windows
  containers:
  - name: windows-container
    image: mcr.microsoft.com/windows/servercore:ltsc2019
    volumeMounts:
    - name: temp-volume
      mountPath: C:\temp
    command:
    - powershell.exe
    - -Command
    - |
      Set-Content -Path C:\temp\test.txt -Value "Hello from Windows"
      while ($true) {
        Get-Content -Path C:\temp\test.txt
        Start-Sleep -Seconds 10
      }
  volumes:
  - name: temp-volume
    emptyDir: {}
```

### Ejemplo de volumen hostPath

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: windows-hostpath
spec:
  nodeSelector:
    kubernetes.io/os: windows
  containers:
  - name: windows-container
    image: mcr.microsoft.com/windows/servercore:ltsc2019
    volumeMounts:
    - name: logs-volume
      mountPath: C:\logs
    command:
    - powershell.exe
    - -Command
    - |
      Set-Content -Path C:\logs\app.log -Value "Application log"
      while ($true) {
        Add-Content -Path C:\logs\app.log -Value "Log entry at $(Get-Date)"
        Start-Sleep -Seconds 10
      }
  volumes:
  - name: logs-volume
    hostPath:
      path: C:\k\logs
      type: DirectoryOrCreate
```

### Ejemplo de volúmenes ConfigMap y Secret

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: windows-config
data:
  config.json: |
    {
      "setting1": "value1",
      "setting2": "value2"
    }
---
apiVersion: v1
kind: Secret
metadata:
  name: windows-secret
type: Opaque
data:
  username: YWRtaW4=  # admin
  password: cGFzc3dvcmQ=  # password
---
apiVersion: v1
kind: Pod
metadata:
  name: windows-config-secret
spec:
  nodeSelector:
    kubernetes.io/os: windows
  containers:
  - name: windows-container
    image: mcr.microsoft.com/windows/servercore:ltsc2019
    volumeMounts:
    - name: config-volume
      mountPath: C:\config
    - name: secret-volume
      mountPath: C:\secret
    command:
    - powershell.exe
    - -Command
    - |
      Get-Content -Path C:\config\config.json
      Get-Content -Path C:\secret\username
      Get-Content -Path C:\secret\password
      while ($true) { Start-Sleep -Seconds 10 }
  volumes:
  - name: config-volume
    configMap:
      name: windows-config
  - name: secret-volume
    secret:
      secretName: windows-secret
```

### Uso de drivers CSI

Ejemplo de uso de drivers CSI en Windows:

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: windows-pvc
spec:
  accessModes:
  - ReadWriteOnce
  resources:
    requests:
      storage: 10Gi
  storageClassName: windows-csi
---
apiVersion: v1
kind: Pod
metadata:
  name: windows-csi-pod
spec:
  nodeSelector:
    kubernetes.io/os: windows
  containers:
  - name: windows-container
    image: mcr.microsoft.com/windows/servercore:ltsc2019
    volumeMounts:
    - name: data-volume
      mountPath: C:\data
    command:
    - powershell.exe
    - -Command
    - |
      Set-Content -Path C:\data\file.txt -Value "Persistent data"
      while ($true) { Start-Sleep -Seconds 10 }
  volumes:
  - name: data-volume
    persistentVolumeClaim:
      claimName: windows-pvc
```
## Monitoreo y registro

Exploremos los métodos de monitoreo y registro para nodos y contenedores Windows.

### Monitoreo

Herramientas para monitorear nodos Windows:

1. **Prometheus Windows Exporter**: Recopila métricas de nodos Windows
2. **metrics-server**: Proporciona métricas básicas de uso de recursos
3. **Datadog, Dynatrace, New Relic**: Soluciones comerciales de monitoreo

Instalación de Prometheus Windows Exporter en nodos Windows:

```powershell
# Download Windows Exporter
Invoke-WebRequest -Uri https://github.com/prometheus-community/windows_exporter/releases/download/v0.16.0/windows_exporter-0.16.0-amd64.msi -OutFile windows_exporter.msi

# Install Windows Exporter
Start-Process msiexec.exe -ArgumentList '/i', 'windows_exporter.msi', 'ENABLED_COLLECTORS=cpu,memory,disk,net,service,os,system', '/quiet' -Wait
```

Configuración de Prometheus:

```yaml
scrape_configs:
  - job_name: 'windows-nodes'
    static_configs:
      - targets: ['windows-node-1:9182', 'windows-node-2:9182']
```

### Registro

Herramientas para recopilar logs de contenedores Windows:

1. **Fluent Bit**: Recopilador de logs ligero
2. **Fluentd**: Recopilación y reenvío de logs
3. **Elasticsearch**: Almacenamiento y búsqueda de logs
4. **Azure Monitor**: Se usa en entornos Azure
5. **CloudWatch Logs**: Se usa en entornos AWS

Instalación de Fluent Bit en nodos Windows:

```powershell
# Download Fluent Bit
Invoke-WebRequest -Uri https://fluentbit.io/releases/1.8/fluent-bit-1.8.11-win64.zip -OutFile fluent-bit.zip

# Extract
Expand-Archive -Path fluent-bit.zip -DestinationPath C:\fluent-bit

# Create configuration file
@"
[SERVICE]
    Flush        5
    Daemon       Off
    Log_Level    info

[INPUT]
    Name         winlog
    Channels     Application,System,Security

[OUTPUT]
    Name         es
    Match        *
    Host         elasticsearch-host
    Port         9200
    Index        windows_logs
"@ | Out-File -FilePath C:\fluent-bit\conf\fluent-bit.conf -Encoding ascii

# Register service
sc.exe create fluent-bit binPath= "C:\fluent-bit\bin\fluent-bit.exe -c C:\fluent-bit\conf\fluent-bit.conf"
Start-Service fluent-bit
```

### Recopilación de logs de aplicaciones

Recopilación de logs de aplicaciones de contenedores Windows:

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: windows-logging
spec:
  nodeSelector:
    kubernetes.io/os: windows
  containers:
  - name: iis
    image: mcr.microsoft.com/windows/servercore/iis:windowsservercore-ltsc2019
    volumeMounts:
    - name: logs
      mountPath: C:\inetpub\logs\LogFiles
  - name: log-collector
    image: mcr.microsoft.com/windows/servercore:ltsc2019
    command:
    - powershell.exe
    - -Command
    - |
      while ($true) {
        Get-Content -Path 'C:\inetpub\logs\LogFiles\W3SVC1\u_ex*' -Wait
      }
    volumeMounts:
    - name: logs
      mountPath: C:\inetpub\logs\LogFiles
  volumes:
  - name: logs
    emptyDir: {}
```

## Seguridad

Exploremos las consideraciones de seguridad para nodos y contenedores Windows.

### Seguridad de los nodos Windows

Recomendaciones para la seguridad de nodos Windows:

1. **Apply Latest Updates**: Aplique regularmente las actualizaciones de seguridad de Windows
2. **Firewall Configuration**: Configure correctamente Windows Defender Firewall
3. **Least Privilege Principle**: Conceda solo los permisos mínimos necesarios
4. **Antivirus Software**: Instale un software antivirus adecuado
5. **Group Policy**: Aplique políticas de grupo para el refuerzo de seguridad

### Seguridad de los contenedores Windows

Recomendaciones para la seguridad de contenedores Windows:

1. **Minimal Base Image**: Use la imagen base más pequeña posible (Nano Server, etc.)
2. **Image Scanning**: Analice las imágenes de contenedor en busca de vulnerabilidades
3. **ReadOnlyRootFilesystem**: Use un sistema de archivos raíz de solo lectura cuando sea posible
4. **Non-Privileged User**: Ejecute las aplicaciones como usuarios no privilegiados
5. **Network Policies**: Aplique las políticas de red adecuadas

### RunAsUsername

En los contenedores Windows, puede usar `runAsUsername` en lugar de `runAsUser` para especificar el usuario que se ejecutará dentro del contenedor:

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: windows-runasusername
spec:
  nodeSelector:
    kubernetes.io/os: windows
  securityContext:
    windowsOptions:
      runAsUserName: "ContainerUser"
  containers:
  - name: windows-container
    image: mcr.microsoft.com/windows/servercore:ltsc2019
    command:
    - powershell.exe
    - -Command
    - |
      whoami
      while ($true) { Start-Sleep -Seconds 10 }
```

### Group Managed Service Accounts (gMSA)

La configuración de gMSA para autenticación de Active Directory en contenedores Windows:

1. **Create gMSA in Active Directory**:

```powershell
# Create gMSA
New-ADServiceAccount -Name WebApp1 -DNSHostName WebApp1.contoso.com -ServicePrincipalNames http/WebApp1.contoso.com -PrincipalsAllowedToRetrieveManagedPassword "Domain Controllers", "Domain Computers"
```

2. **Store gMSA Credentials in Kubernetes**:

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: gmsa-cred-spec
type: microsoft.com/gmsa-credential-spec
data:
  credspec.json: <base64-encoded-credential-spec>
```

3. **Apply gMSA Configuration to Pod**:

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: windows-gmsa
spec:
  nodeSelector:
    kubernetes.io/os: windows
  securityContext:
    windowsOptions:
      gmsaCredentialSpecName: gmsa-cred-spec
  containers:
  - name: windows-container
    image: mcr.microsoft.com/windows/servercore:ltsc2019
    command:
    - powershell.exe
    - -Command
    - |
      whoami
      while ($true) { Start-Sleep -Seconds 10 }
```

## Compatibilidad con Windows en Amazon EKS

Exploremos cómo ejecutar cargas de trabajo Windows en Amazon EKS.

El siguiente diagrama muestra la arquitectura de compatibilidad con Windows en Amazon EKS:

![El control plane administrado de EKS gestiona tanto un grupo de nodos Linux (que ejecuta Pods del sistema CoreDNS, VPC CNI y kube-proxy) como un grupo de nodos Windows (que ejecuta Pods de aplicaciones Windows), se integra con AWS IAM, Amazon VPC y CloudWatch, y los Pods de aplicaciones Windows llegan a los usuarios finales mediante un Elastic Load Balancer.](../.gitbook/assets/en-core-10-windows-in-kubernetes-4.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-core-10-windows-in-kubernetes-4.html)

### Habilitación de la compatibilidad con Windows en EKS

Pasos para habilitar la compatibilidad con Windows en Amazon EKS:

1. **Update VPC CNI Plugin**:

```bash
kubectl apply -f https://raw.githubusercontent.com/aws/amazon-vpc-cni-k8s/release-1.11/config/master/vpc-resource-controller.yaml
```

2. **Install Windows VPC Admission Webhook**:

```bash
kubectl apply -f https://raw.githubusercontent.com/aws/amazon-vpc-cni-k8s/release-1.11/config/master/vpc-admission-webhook.yaml
```

### Creación de grupos de nodos Windows

Cree un grupo de nodos Windows mediante eksctl:

```bash
eksctl create nodegroup \
  --cluster my-cluster \
  --region us-west-2 \
  --name windows-ng \
  --node-type t3.large \
  --nodes 2 \
  --nodes-min 1 \
  --nodes-max 4 \
  --managed \
  --node-ami-family WindowsServer2019FullContainer
```

Creación de un grupo de nodos Windows mediante AWS Management Console:

1. Seleccione el clúster en la consola de EKS
2. Seleccione la pestaña "Compute"
3. Haga clic en "Add node group"
4. Introduzca los detalles del grupo de nodos
5. Seleccione "Windows" como tipo de AMI
6. Configure los ajustes restantes y cree el grupo

### Implementación de aplicaciones Windows en EKS

Ejemplo de implementación de aplicaciones Windows en EKS:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: windows-server-iis
spec:
  selector:
    matchLabels:
      app: windows-server-iis
      tier: backend
      track: stable
  replicas: 2
  template:
    metadata:
      labels:
        app: windows-server-iis
        tier: backend
        track: stable
    spec:
      nodeSelector:
        kubernetes.io/os: windows
      containers:
      - name: windows-server-iis
        image: mcr.microsoft.com/windows/servercore/iis:windowsservercore-ltsc2019
        ports:
        - name: http
          containerPort: 80
        resources:
          limits:
            cpu: 1
            memory: 800Mi
          requests:
            cpu: .1
            memory: 300Mi
---
apiVersion: v1
kind: Service
metadata:
  name: windows-server-iis-service
  labels:
    app: windows-server-iis
spec:
  ports:
  - port: 80
    protocol: TCP
  selector:
    app: windows-server-iis
  type: LoadBalancer
```

### Registro de contenedores Windows en EKS

Recopilación de logs de contenedores Windows mediante CloudWatch Logs:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: fluent-bit-config
  namespace: amazon-cloudwatch
data:
  fluent-bit.conf: |
    [SERVICE]
        Flush         5
        Log_Level     info
        Daemon        off

    [INPUT]
        Name          tail
        Tag           kube.*
        Path          /var/log/containers/*.log
        Parser        docker
        DB            /var/fluent-bit/state/flb_container.db
        Mem_Buf_Limit 50MB

    [FILTER]
        Name          kubernetes
        Match         kube.*
        Kube_URL      https://kubernetes.default.svc:443
        Merge_Log     On

    [OUTPUT]
        Name          cloudwatch_logs
        Match         kube.*
        region        us-west-2
        log_group_name /aws/eks/my-cluster/windows-logs
        log_stream_prefix windows-
        auto_create_group true
```

## Prácticas recomendadas

Exploremos las prácticas recomendadas para ejecutar cargas de trabajo Windows en Kubernetes.

### Prácticas recomendadas para el diseño del clúster

1. **Mixed Node Pools**: Use una combinación adecuada de nodos Linux y Windows
2. **Node Labels and Taints**: Use etiquetas y taints de nodo adecuados para separar las cargas de trabajo
3. **Version Compatibility**: Verifique la compatibilidad entre la versión de Kubernetes y la versión de Windows
4. **Network Plugin Selection**: Seleccione un plugin de red adecuado compatible con Windows
5. **High Availability**: Configure alta disponibilidad para las cargas de trabajo críticas

### Prácticas recomendadas para el diseño de aplicaciones

1. **Container Image Optimization**: Use imágenes de contenedor pequeñas y eficientes
2. **Resource Requests and Limits**: Establezca solicitudes y límites de recursos adecuados
3. **Stateless Design**: Diseñe aplicaciones sin estado cuando sea posible
4. **Logging and Monitoring**: Configure un registro y monitoreo eficaces
5. **Security Hardening**: Aplique contextos de seguridad y políticas de red adecuados

### Prácticas recomendadas de operaciones

1. **Regular Updates**: Actualice regularmente los nodos Windows y las imágenes de contenedor
2. **Automation**: Automatice las tareas de implementación y administración
3. **Backup and Recovery**: Realice copias de seguridad de los datos importantes regularmente
4. **Troubleshooting Tools**: Desarrolle herramientas y procesos adecuados de solución de problemas
5. **Documentation**: Documente las configuraciones y los procedimientos

### Prácticas recomendadas específicas de EKS

1. **Managed Node Groups**: Use grupos de nodos administrados cuando sea posible
2. **IAM Roles for Service Accounts (IRSA)**: Administre los permisos de IAM por Pod
3. **VPC CNI Configuration**: Configure VPC CNI según los requisitos de red
4. **Security Groups**: Configure grupos de seguridad adecuados
5. **Cost Optimization**: Seleccione tipos y tamaños de instancia adecuados

## Conclusión

La compatibilidad con Windows en Kubernetes continúa evolucionando, y ahora puede ejecutar cargas de trabajo Windows en entornos de producción. Los nodos Windows pueden ejecutarse junto a nodos Linux en el mismo clúster, lo que le permite administrar cargas de trabajo diversas en un único clúster de Kubernetes.

Los contenedores Windows permiten contenerizar aplicaciones .NET Framework, servicios Windows y otras cargas de trabajo específicas de Windows para aprovechar las capacidades de orquestación de Kubernetes. Sin embargo, existen algunas limitaciones en comparación con los contenedores Linux, por lo que es importante comprender y abordar estas limitaciones adecuadamente.

Amazon EKS proporciona servicios administrados para nodos Windows, lo que facilita la implementación y administración de cargas de trabajo Windows. Aprovechar la compatibilidad con Windows de EKS puede simplificar el proceso de migración de aplicaciones Windows a entornos de contenedores modernos.

Para implementar Windows en Kubernetes correctamente, es importante seguir prácticas recomendadas adecuadas de planificación, diseño y operaciones. Esto permite administrar eficientemente las cargas de trabajo Windows y Linux y aprovechar todos los beneficios de Kubernetes.

## Cuestionario

Para poner a prueba lo que aprendió en este capítulo, intente el [Cuestionario de Windows en Kubernetes](../quizzes/core/10-windows-in-kubernetes-quiz.md).
