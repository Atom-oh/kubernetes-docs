# Windows in Kubernetes

> **Versiones compatibles**: Kubernetes 1.32, 1.33, 1.34
> **Última actualización**: February 11, 2026

Kubernetes fue diseñado originalmente para contenedores Linux, pero el soporte de producción para contenedores Windows se agregó a partir de la versión 1.14. En este capítulo, exploraremos cómo ejecutar cargas de trabajo Windows en Kubernetes, la arquitectura, las limitaciones y el soporte de Windows en Amazon EKS.

## Table of Contents
1. [Windows Container Overview](#windows-container-overview)
2. [Kubernetes Windows Support Architecture](#kubernetes-windows-support-architecture)
3. [Windows Node Limitations](#windows-node-limitations)
4. [Windows Node Setup](#windows-node-setup)
5. [Deploying Windows Containers](#deploying-windows-containers)
6. [Networking](#networking)
7. [Storage](#storage)
8. [Monitoring and Logging](#monitoring-and-logging)
9. [Security](#security)
10. [Windows Support in Amazon EKS](#windows-support-in-amazon-eks)
11. [Best Practices](#best-practices)
12. [Conclusion](#conclusion)

## Windows Container Overview

Los contenedores Windows son contenedores que se ejecutan en el sistema operativo Windows, lo que permite contenerizar y desplegar aplicaciones Windows.

### Windows Container Types

Hay dos tipos de contenedores Windows:

1. **Windows Server Containers**: De forma similar a los contenedores Linux, comparten el kernel del sistema operativo del host. Son ligeros y se inician rápidamente, pero requieren la misma versión de Windows que el host.

2. **Hyper-V Isolation Containers**: Cada contenedor se ejecuta en una VM ligera, lo que proporciona un mayor nivel de aislamiento. Pueden ejecutar versiones de Windows diferentes a la del host, pero usan más recursos.

El siguiente diagrama muestra las diferencias arquitectónicas entre los dos tipos de contenedores Windows:

```mermaid
flowchart TD
    subgraph "Windows Server Containers"
        WSC1[Windows App 1] --- WSC2[Windows App 2] --- WSC3[Windows App 3]
        WSC1 --- WSCR[Container Runtime]
        WSC2 --- WSCR
        WSC3 --- WSCR
        WSCR --- WSOS[Windows Server OS]
        WSOS --- WSHW[Physical Hardware]
    end

    subgraph "Hyper-V Isolation Containers"
        HVC1[Windows App 1] --- HVCR1[Container Runtime]
        HVCR1 --- HVOS1[Windows OS Kernel]

        HVC2[Windows App 2] --- HVCR2[Container Runtime]
        HVCR2 --- HVOS2[Windows OS Kernel]

        HVOS1 --- HV[Hyper-V Hypervisor]
        HVOS2 --- HV
        HV --- HVHOS[Windows Server OS]
        HVHOS --- HVHW[Physical Hardware]
    end

    classDef userApp fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;
    classDef k8sComponent fill:#326CE5,stroke:#333,stroke-width:1px,color:white;
    classDef default fill:#f9f9f9,stroke:#333,stroke-width:1px,color:black;

    class WSC1,WSC2,WSC3,HVC1,HVC2 userApp;
    class WSCR,HVCR1,HVCR2,HVOS1,HVOS2,HV k8sComponent;
    class WSOS,WSHW,HVHOS,HVHW default;
```

### Windows Container Images

Las imágenes de contenedor Windows se basan en imágenes base proporcionadas por Microsoft:

1. **Windows Server Core**: Una imagen ligera que proporciona un entorno mínimo de Windows Server
2. **Nano Server**: Una imagen ultraligera con una huella menor
3. **Windows**: Una imagen que proporciona un entorno completo de Windows Server

Ejemplo de Dockerfile:

```dockerfile
FROM mcr.microsoft.com/windows/servercore:ltsc2019
WORKDIR /app
COPY . .
RUN powershell -Command "Install-WindowsFeature Web-Server"
EXPOSE 80
CMD ["powershell", "-Command", "Start-Service W3SVC; Get-Content -Path 'C:\\inetpub\\logs\\LogFiles\\W3SVC1\\u_ex*' -Wait"]
```

## Kubernetes Windows Support Architecture

El soporte de Windows en Kubernetes se basa en un entorno mixto. Los componentes del control plane (plano de control) siempre se ejecutan en Linux, mientras que los nodos worker pueden ser Linux o Windows.

### Architecture Overview

La arquitectura de soporte de Windows en Kubernetes es la siguiente:

1. **Linux Control Plane**: kube-apiserver, kube-controller-manager, kube-scheduler y etcd siempre se ejecutan en Linux.
2. **Linux Worker Nodes**: Ejecutan componentes del sistema (CoreDNS, metrics-server, etc.).
3. **Windows Worker Nodes**: Ejecutan cargas de trabajo de aplicaciones Windows.

```mermaid
flowchart TD
    subgraph "Linux Control Plane"
        API[kube-apiserver] --> CM[kube-controller-manager]
        API --> SCH[kube-scheduler]
        API --> ETCD[(etcd)]
    end

    API --> LN[Linux Node]
    API --> WN1[Windows Node 1]
    API --> WN2[Windows Node 2]

    subgraph "Linux Worker Node"
        LN --> CoreDNS[CoreDNS]
        LN --> Metrics[metrics-server]
        LN --> Other[Other System Pods]
    end

    subgraph "Windows Worker Nodes"
        WN1 --> WK1[kubelet]
        WN1 --> WP1[kube-proxy]
        WN1 --> WC1[Windows Containers]

        WN2 --> WK2[kubelet]
        WN2 --> WP2[kube-proxy]
        WN2 --> WC2[Windows Containers]
    end

    classDef k8sComponent fill:#326CE5,stroke:#333,stroke-width:1px,color:white;
    classDef dataStore fill:#3B48CC,stroke:#333,stroke-width:1px,color:white;
    classDef userApp fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;
    classDef default fill:#f9f9f9,stroke:#333,stroke-width:1px,color:black;

    class API,CM,SCH,LN,WN1,WN2,WK1,WK2,WP1,WP2,CoreDNS,Metrics,Other k8sComponent;
    class ETCD dataStore;
    class WC1,WC2 userApp;
```

### Windows Node Components

Componentes de Kubernetes que se ejecutan en nodos Windows:

1. **kubelet**: Gestiona los pods y contenedores en el nodo
2. **kube-proxy**: Gestiona las reglas de red
3. **CNI Plugin**: Configuración de red
4. **CSI Plugin**: Gestión de almacenamiento

## Windows Node Limitations

Hay varias limitaciones que se deben tener en cuenta al usar nodos Windows en Kubernetes.

### Feature Limitations

1. **Privileged Containers**: Windows no admite contenedores privilegiados.
2. **Host Network Mode**: Los pods de Windows no pueden usar el modo de red del host.
3. **Pod Security Context**: Algunas funcionalidades de security context (runAsUser, fsGroup, etc.) no son compatibles.
4. **DaemonSet**: Los DaemonSets que se ejecutan en nodos Windows requieren consideraciones especiales.
5. **emptyDir Volumes**: Los volúmenes emptyDir basados en memoria no son compatibles con Windows.
6. **Resource Limits**: Los límites de CPU se aplican de forma diferente en Windows.

### Networking Limitations

1. **Network Mode**: Windows solo admite redes L3.
2. **Service Types**: Los nodos Windows tienen limitaciones en algunos tipos de Service.
3. **Load Balancing**: Algunas funcionalidades de balanceo de carga pueden estar limitadas.

### Operating System Version Compatibility

Los contenedores Windows tienen consideraciones importantes de compatibilidad con la versión del sistema operativo del host:

| Container Base Image | Compatible Host OS Versions |
|---------------------|---------------------------|
| Windows Server 2019 | Windows Server 2019 |
| Windows Server 2022 | Windows Server 2022 |

El aislamiento Hyper-V puede relajar estas limitaciones, pero requiere recursos adicionales.
## Windows Node Setup

Exploremos el proceso de agregar nodos Windows a un cluster de Kubernetes.

### Prerequisites

Antes de configurar nodos Windows, verifica lo siguiente:

1. **Versión de Kubernetes**: 1.14 o posterior
2. **Versión de Windows**: Windows Server 2019 o posterior
3. **Network Plugin**: Plugin CNI que admita Windows (Calico, Flannel, etc.)
4. **Container Runtime**: Docker, containerd, etc.

### Preparing Windows Nodes

Pasos para preparar un nodo Windows:

1. **Instalar Windows Server**: Instala Windows Server 2019 o posterior
2. **Habilitar la característica Containers**:

```powershell
Install-WindowsFeature -Name Containers
Restart-Computer -Force
```

3. **Instalar Docker**:

```powershell
Install-Module -Name DockerMsftProvider -Repository PSGallery -Force
Install-Package -Name Docker -ProviderName DockerMsftProvider -Force
Restart-Computer -Force
```

4. **Instalar componentes de Kubernetes**:

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

5. **Configurar la red**:

```powershell
# Set firewall rules
New-NetFirewallRule -Name kubelet -DisplayName 'kubelet' -Enabled True -Direction Inbound -Protocol TCP -Action Allow -LocalPort 10250
New-NetFirewallRule -Name https -DisplayName 'https' -Enabled True -Direction Inbound -Protocol TCP -Action Allow -LocalPort 443
New-NetFirewallRule -Name http -DisplayName 'http' -Enabled True -Direction Inbound -Protocol TCP -Action Allow -LocalPort 80
```

### Joining Windows Node Using kubeadm

Genera el token de unión en el control plane de Linux:

```bash
kubeadm token create --print-join-command
```

Ejecuta el comando de unión en el nodo Windows:

```powershell
# Run kubeadm join command
kubeadm join <control-plane-host>:<control-plane-port> --token <token> --discovery-token-ca-cert-hash sha256:<hash>

# Register and start kubelet service
sc.exe create kubelet binPath= "C:\k\kubelet.exe --windows-service --kubeconfig=C:\k\config"
Start-Service kubelet
```

### Setting Windows Node Labels

Establece labels adecuadas en los nodos Windows para controlar la programación de cargas de trabajo:

```bash
kubectl label node <windows-node-name> kubernetes.io/os=windows
kubectl label node <windows-node-name> kubernetes.io/arch=amd64
```

## Deploying Windows Containers

Exploremos cómo desplegar contenedores Windows en Kubernetes.

### Using Node Selector

Al desplegar cargas de trabajo Windows, usa un node selector para garantizar que se programen en nodos Windows:

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

### Resource Requests and Limits

Las requests y limits de recursos para contenedores Windows se manejan de forma diferente a las de los contenedores Linux:

1. **CPU Limits**: Los límites de CPU se aplican de forma diferente en Windows. Por ejemplo, un límite de CPU de 1 significa que se puede usar el 100% de un único núcleo de CPU.
2. **Memory Limits**: Los contenedores Windows respetan los límites de memoria, pero algunos procesos del sistema pueden generar sobrecarga adicional.

### Container Customization

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

### Multi-Container Pods

Windows también admite pods de múltiples contenedores, pero con algunas limitaciones:

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

## Networking

La red en nodos Windows tiene características diferentes a las de los nodos Linux.

El siguiente diagrama muestra la arquitectura de red de un cluster de Kubernetes con nodos Windows y Linux mixtos:

```mermaid
flowchart TD
    subgraph "External Network"
        Client[Client] --> LB[Load Balancer]
    end

    LB --> SVC[Kubernetes Service]

    subgraph "Kubernetes Cluster"
        SVC --> LP1[Linux Pod]
        SVC --> LP2[Linux Pod]
        SVC --> WP1[Windows Pod]
        SVC --> WP2[Windows Pod]

        subgraph "Linux Node"
            LP1
            LP2
        end

        subgraph "Windows Node"
            WP1
            WP2
        end

        LP1 <--> LP2
        LP1 <--> WP1
        LP2 <--> WP2
        WP1 <--> WP2
    end

    classDef k8sComponent fill:#326CE5,stroke:#333,stroke-width:1px,color:white;
    classDef userApp fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;
    classDef default fill:#f9f9f9,stroke:#333,stroke-width:1px,color:black;

    class SVC k8sComponent;
    class LP1,LP2,WP1,WP2 userApp;
    class Client,LB default;
```

### Supported Network Plugins

Plugins de red compatibles con nodos Windows:

1. **Flannel**: Modo VXLAN o host-gw
2. **Calico**: Modo VXLAN
3. **Antrea**: Redes basadas en OVS
4. **Azure CNI**: Usado en entornos Azure
5. **AWS VPC CNI**: Usado en entornos AWS

### Flannel Setup Example

Configuración de red de Windows usando Flannel:

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

### Exposing Services

Cómo exponer services en nodos Windows:

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

### Network Policies

Para usar network policies en nodos Windows, necesitas un plugin CNI que admita network policies (por ejemplo, Calico):

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

## Storage

Exploremos las opciones de almacenamiento disponibles en nodos Windows.

El siguiente diagrama muestra varias opciones de almacenamiento disponibles en nodos Windows:

```mermaid
flowchart TD
    subgraph "Windows Pod"
        WC[Windows Container]
    end

    WC --> ED[emptyDir Volume]
    WC --> HP[hostPath Volume]
    WC --> CM[ConfigMap Volume]
    WC --> SC[Secret Volume]
    WC --> PV[PersistentVolume]

    subgraph "Windows Node"
        ED
        HP --> ND[Node Disk]
    end

    subgraph "Kubernetes API"
        CM
        SC
    end

    PV --> CSI[CSI Driver]
    CSI --> AZ[Azure Disk/File]
    CSI --> AWS[AWS EBS]
    CSI --> SMB[SMB Share]

    classDef userApp fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;
    classDef k8sComponent fill:#326CE5,stroke:#333,stroke-width:1px,color:white;
    classDef dataStore fill:#3B48CC,stroke:#333,stroke-width:1px,color:white;
    classDef awsService fill:#FF9900,stroke:#333,stroke-width:1px,color:black;
    classDef default fill:#f9f9f9,stroke:#333,stroke-width:1px,color:black;

    class WC userApp;
    class ED,HP,CM,SC,PV,CSI k8sComponent;
    class ND,SMB dataStore;
    class AWS awsService;
    class AZ default;
```

### Supported Volume Types

Tipos de volúmenes compatibles con nodos Windows:

1. **emptyDir**: Almacenamiento temporal (emptyDir basado en memoria no compatible)
2. **hostPath**: Sistema de archivos del nodo host
3. **configMap**: Datos de configuración
4. **secret**: Datos sensibles
5. **azureFile**: Almacenamiento Azure File
6. **awsElasticBlockStore**: Volúmenes AWS EBS
7. **azureDisk**: Almacenamiento Azure Disk
8. **CSI**: Drivers Container Storage Interface

### emptyDir Volume Example

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

### hostPath Volume Example

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

### ConfigMap and Secret Volume Example

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

### Using CSI Drivers

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
## Monitoring and Logging

Exploremos los métodos de monitoreo y logging para nodos y contenedores Windows.

### Monitoring

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

### Logging

Herramientas para recopilar logs de contenedores Windows:

1. **Fluent Bit**: Recopilador de logs ligero
2. **Fluentd**: Recopilación y reenvío de logs
3. **Elasticsearch**: Almacenamiento y búsqueda de logs
4. **Azure Monitor**: Usado en entornos Azure
5. **CloudWatch Logs**: Usado en entornos AWS

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

### Application Log Collection

Recopilación de logs de aplicaciones en contenedores Windows:

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

## Security

Exploremos las consideraciones de seguridad para nodos y contenedores Windows.

### Windows Node Security

Recomendaciones para la seguridad de nodos Windows:

1. **Apply Latest Updates**: Aplica regularmente las actualizaciones de seguridad de Windows
2. **Firewall Configuration**: Configura correctamente Windows Defender Firewall
3. **Least Privilege Principle**: Otorga solo los permisos mínimos necesarios
4. **Antivirus Software**: Instala software antivirus adecuado
5. **Group Policy**: Aplica group policies para el endurecimiento de seguridad

### Windows Container Security

Recomendaciones para la seguridad de contenedores Windows:

1. **Minimal Base Image**: Usa la imagen base más pequeña posible (Nano Server, etc.)
2. **Image Scanning**: Escanea las imágenes de contenedor en busca de vulnerabilidades
3. **ReadOnlyRootFilesystem**: Usa un sistema de archivos raíz de solo lectura cuando sea posible
4. **Non-Privileged User**: Ejecuta aplicaciones como usuarios no privilegiados
5. **Network Policies**: Aplica network policies adecuadas

### RunAsUsername

En contenedores Windows, puedes usar `runAsUsername` en lugar de `runAsUser` para especificar el usuario con el que se ejecutará dentro del contenedor:

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

Configuración de gMSA para autenticación de Active Directory en contenedores Windows:

1. **Crear gMSA en Active Directory**:

```powershell
# Create gMSA
New-ADServiceAccount -Name WebApp1 -DNSHostName WebApp1.contoso.com -ServicePrincipalNames http/WebApp1.contoso.com -PrincipalsAllowedToRetrieveManagedPassword "Domain Controllers", "Domain Computers"
```

2. **Almacenar credenciales de gMSA en Kubernetes**:

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: gmsa-cred-spec
type: microsoft.com/gmsa-credential-spec
data:
  credspec.json: <base64-encoded-credential-spec>
```

3. **Aplicar la configuración de gMSA al Pod**:

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

## Windows Support in Amazon EKS

Exploremos cómo ejecutar cargas de trabajo Windows en Amazon EKS.

El siguiente diagrama muestra la arquitectura de soporte de Windows en Amazon EKS:

```mermaid
flowchart TD
    subgraph "AWS Cloud"
        subgraph "Amazon EKS"
            CP[EKS Control Plane] --> LNG[Linux Node Group]
            CP --> WNG[Windows Node Group]

            subgraph "Linux Node Group"
                LNG --> LN1[Linux Node 1]
                LNG --> LN2[Linux Node 2]

                LN1 --> LP1[CoreDNS]
                LN1 --> LP2[VPC CNI]
                LN2 --> LP3[kube-proxy]
                LN2 --> LP4[Other System Pods]
            end

            subgraph "Windows Node Group"
                WNG --> WN1[Windows Node 1]
                WNG --> WN2[Windows Node 2]

                WN1 --> WP1[Windows Application Pods]
                WN2 --> WP2[Windows Application Pods]
            end
        end

        CP --> IAM[AWS IAM]
        CP --> VPC[Amazon VPC]
        CP --> CW[CloudWatch]

        WP1 --> ELB[Elastic Load Balancer]
        WP2 --> ELB
        ELB --> User[User]
    end

    classDef k8sComponent fill:#326CE5,stroke:#333,stroke-width:1px,color:white;
    classDef userApp fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;
    classDef awsService fill:#FF9900,stroke:#333,stroke-width:1px,color:black;
    classDef default fill:#f9f9f9,stroke:#333,stroke-width:1px,color:black;

    class CP,LNG,WNG,LN1,LN2,WN1,WN2,LP1,LP2,LP3,LP4 k8sComponent;
    class WP1,WP2 userApp;
    class IAM,VPC,CW,ELB awsService;
    class User default;
```

### Enabling Windows Support in EKS

Pasos para habilitar el soporte de Windows en Amazon EKS:

1. **Actualizar el plugin VPC CNI**:

```bash
kubectl apply -f https://raw.githubusercontent.com/aws/amazon-vpc-cni-k8s/release-1.11/config/master/vpc-resource-controller.yaml
```

2. **Instalar Windows VPC Admission Webhook**:

```bash
kubectl apply -f https://raw.githubusercontent.com/aws/amazon-vpc-cni-k8s/release-1.11/config/master/vpc-admission-webhook.yaml
```

### Creating Windows Node Groups

Crea un grupo de nodos Windows usando eksctl:

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

Creación de un grupo de nodos Windows usando AWS Management Console:

1. Selecciona el cluster en la consola de EKS
2. Selecciona la pestaña "Compute"
3. Haz clic en "Add node group"
4. Ingresa los detalles del grupo de nodos
5. Selecciona "Windows" como tipo de AMI
6. Configura los ajustes restantes y crea

### Deploying Windows Applications in EKS

Ejemplo de despliegue de aplicaciones Windows en EKS:

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

### Windows Container Logging in EKS

Recopilación de logs de contenedores Windows usando CloudWatch Logs:

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

## Best Practices

Exploremos las mejores prácticas para ejecutar cargas de trabajo Windows en Kubernetes.

### Cluster Design Best Practices

1. **Mixed Node Pools**: Usa una combinación adecuada de nodos Linux y Windows
2. **Node Labels and Taints**: Usa labels y taints de nodo adecuados para separar las cargas de trabajo
3. **Version Compatibility**: Verifica la compatibilidad entre la versión de Kubernetes y la versión de Windows
4. **Network Plugin Selection**: Selecciona un plugin de red adecuado que admita Windows
5. **High Availability**: Configura alta disponibilidad para cargas de trabajo críticas

### Application Design Best Practices

1. **Container Image Optimization**: Usa imágenes de contenedor pequeñas y eficientes
2. **Resource Requests and Limits**: Establece requests y limits de recursos adecuados
3. **Stateless Design**: Diseña aplicaciones stateless cuando sea posible
4. **Logging and Monitoring**: Configura logging y monitoreo efectivos
5. **Security Hardening**: Aplica security contexts y network policies adecuados

### Operations Best Practices

1. **Regular Updates**: Actualiza regularmente los nodos Windows y las imágenes de contenedor
2. **Automation**: Automatiza las tareas de despliegue y gestión
3. **Backup and Recovery**: Realiza copias de seguridad periódicas de los datos importantes
4. **Troubleshooting Tools**: Crea herramientas y procesos adecuados de troubleshooting
5. **Documentation**: Documenta configuraciones y procedimientos

### EKS-Specific Best Practices

1. **Managed Node Groups**: Usa managed node groups cuando sea posible
2. **IAM Roles for Service Accounts (IRSA)**: Gestiona permisos de IAM por pod
3. **VPC CNI Configuration**: Configura VPC CNI según los requisitos de red
4. **Security Groups**: Configura security groups adecuados
5. **Cost Optimization**: Selecciona tipos y tamaños de instancia adecuados

## Conclusion

El soporte de Windows en Kubernetes continúa evolucionando, y ahora puedes ejecutar cargas de trabajo Windows en entornos de producción. Los nodos Windows pueden ejecutarse junto con nodos Linux en el mismo cluster, lo que te permite gestionar cargas de trabajo diversas en un único cluster de Kubernetes.

Los contenedores Windows permiten contenerizar aplicaciones .NET Framework, servicios Windows y otras cargas de trabajo específicas de Windows para aprovechar las capacidades de orquestación de Kubernetes. Sin embargo, existen algunas limitaciones en comparación con los contenedores Linux, por lo que es importante entender y abordar estas limitaciones adecuadamente.

Amazon EKS proporciona servicios gestionados para nodos Windows, lo que facilita desplegar y gestionar cargas de trabajo Windows. Aprovechar el soporte de Windows de EKS puede simplificar el proceso de migración de aplicaciones Windows a entornos de contenedores modernos.

Para implementar Windows en Kubernetes con éxito, es importante seguir prácticas recomendadas adecuadas de planificación, diseño y operación. Esto te permite gestionar eficientemente cargas de trabajo Windows y Linux y aprovechar todos los beneficios de Kubernetes.

## Quiz

Para comprobar lo que aprendiste en este capítulo, intenta el [Windows in Kubernetes Quiz](../quizzes/core/10-windows-in-kubernetes-quiz.md).
