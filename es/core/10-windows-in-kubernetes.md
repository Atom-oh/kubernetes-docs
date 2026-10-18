# Windows en Kubernetes

> **Versiones de Kubernetes upstream revisadas**: Kubernetes 1.35, 1.36, 1.37
> **Última actualización**: 11 de septiembre de 2026

Kubernetes se diseñó originalmente para contenedores Linux, pero la compatibilidad para producción de contenedores Windows se añadió a partir de la versión 1.14. En este capítulo veremos cómo ejecutar cargas de trabajo Windows en Kubernetes, su arquitectura y limitaciones, y la compatibilidad con Windows en Amazon EKS.

## Tabla de contenido
1. [Descripción general de los contenedores Windows](#windows-container-overview)
2. [Arquitectura de compatibilidad con Windows en Kubernetes](#kubernetes-windows-support-architecture)
3. [Limitaciones de los nodos Windows](#windows-node-limitations)
4. [Configuración de nodos Windows](#windows-node-setup)
5. [Despliegue de contenedores Windows](#deploying-windows-containers)
6. [Redes](#networking)
7. [Almacenamiento](#storage)
8. [Supervisión y registro](#monitoring-and-logging)
9. [Seguridad](#security)
10. [Compatibilidad con Windows en Amazon EKS](#windows-support-in-amazon-eks)
11. [Prácticas recomendadas](#best-practices)
12. [Conclusión](#conclusion)

## Descripción general de los contenedores Windows

Los contenedores Windows se ejecutan en el sistema operativo Windows y permiten empaquetar e implementar aplicaciones Windows.

### Tipos de contenedores Windows

Windows ofrece dos tipos de aislamiento. Kubernetes solo admite **aislamiento de procesos**; la información sobre Hyper-V que aparece a continuación es contextual, no una opción de despliegue de Kubernetes:

1. **Windows Server Containers**: Al igual que los contenedores Linux, comparten el kernel del sistema operativo host. Son ligeros y se inician rápido, pero requieren una combinación de host e imagen compatible con Microsoft.

2. **Contenedores con aislamiento de Hyper-V**: Cada contenedor se ejecuta en una VM ligera, que ofrece mayor aislamiento. Pueden ejecutar versiones de Windows distintas de la del host, pero consumen más recursos.

El diagrama siguiente muestra las diferencias arquitectónicas entre los dos tipos de contenedores Windows:

![Comparación entre Windows Server Containers, donde varias aplicaciones Windows comparten un runtime de contenedores y el kernel del sistema operativo host, y los contenedores con aislamiento de Hyper-V, donde cada aplicación se ejecuta en su propia VM ligera con un kernel de Windows dedicado bajo el hipervisor Hyper-V antes de llegar al mismo sistema operativo Windows Server y al hardware físico.](../.gitbook/assets/en-core-10-windows-in-kubernetes-0.png)

[🔍 Ver el diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-core-10-windows-in-kubernetes-0.html)

### Imágenes de contenedor Windows

Las imágenes de contenedor Windows se basan en imágenes base proporcionadas por Microsoft:

1. **Windows Server Core**: Imagen ligera que proporciona un entorno mínimo de Windows Server
2. **Nano Server**: Imagen ultraligera, con una huella menor
3. **Windows**: Ofrece una superficie de API de Windows más amplia; las imágenes de contenedor no incluyen un servidor de escritorio/GUI completo

Dockerfile de ejemplo:

```dockerfile
FROM mcr.microsoft.com/windows/servercore/iis:windowsservercore-ltsc2022
COPY website/ C:/inetpub/wwwroot/
EXPOSE 80
# Inherit the IIS image entrypoint (ServiceMonitor.exe).
```

## Arquitectura de compatibilidad con Windows en Kubernetes

La compatibilidad con Windows en Kubernetes se basa en un entorno mixto. Los componentes del plano de control siempre se ejecutan en Linux, mientras que los nodos de trabajo pueden ser Linux o Windows.

### Descripción general de la arquitectura

La arquitectura de compatibilidad con Windows en Kubernetes es la siguiente:

1. **Plano de control Linux**: kube-apiserver, kube-controller-manager, kube-scheduler y etcd siempre se ejecutan en Linux.
2. **Nodos de trabajo Linux**: Ejecutan componentes del sistema como CoreDNS y metrics-server.
3. **Nodos de trabajo Windows**: Ejecutan cargas de trabajo de aplicaciones Windows.

![Un plano de control solo Linux (kube-apiserver, kube-controller-manager, kube-scheduler, etcd) administra un clúster mixto y se conecta con un nodo de trabajo Linux que ejecuta Pods del sistema como CoreDNS y metrics-server, y con dos nodos de trabajo Windows que ejecutan kubelet, kube-proxy y contenedores Windows.](../.gitbook/assets/en-core-10-windows-in-kubernetes-1.png)

[🔍 Ver el diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-core-10-windows-in-kubernetes-1.html)

### Componentes de nodos Windows

Los componentes de Kubernetes que se ejecutan en nodos Windows son:

1. **kubelet**: Administra los Pods y contenedores del nodo
2. **kube-proxy**: Administra las reglas de red
3. **Plugin CNI**: Configuración de red
4. **Plugin CSI**: Administración del almacenamiento

## Limitaciones de los nodos Windows

Al usar nodos Windows en Kubernetes, hay varias limitaciones que debe tener en cuenta.

### Limitaciones de funcionalidades

1. `privileged` no es compatible. Los agentes de nodo pueden usar **contenedores HostProcess** con `hostProcess` y `hostNetwork` habilitados; restrinja cuidadosamente sus privilegios en el host.
2. Los Pods Windows normales no pueden usar `hostNetwork`; HostProcess es la excepción.
3. Los Pods con `spec.os.name: windows` no deben definir campos exclusivos de Linux como `runAsUser`, `fsGroup`, `seccomp`, `capabilities` o `readOnlyRootFilesystem`.
4. Use imágenes específicas para cada sistema operativo y `nodeSelector` en DaemonSets separados.
5. No se admiten `emptyDir` respaldado por memoria, `volumeDevices` de bloques sin formato, PIDPressure ni la expulsión OOM al estilo de Linux.
6. Los límites de CPU/memoria usan mecanismos de Windows. Windows no tiene el OOM killer de Linux; agotar la memoria puede provocar fallos de asignación o paginación y degradar el rendimiento.

### Limitaciones de red

Compruebe la matriz de compatibilidad de HNS/CNI de Windows para modos como L2bridge y overlay. Los contenedores de un mismo Pod comparten la red y `localhost`, pero no los espacios de nombres de procesos ni los sistemas de archivos raíz. Verifique la compatibilidad de NetworkPolicy, Service y DSR para la combinación elegida de sistema operativo/CNI/clúster.

### Compatibilidad de versiones del sistema operativo

Kubernetes v1.37 admite nodos de trabajo Windows Server 2022 y 2025. Los ejemplos de este capítulo usan **Windows Server 2022 + ltsc2022**. Consulte tanto la matriz de compatibilidad de Microsoft como la política de soporte de la distribución y aplique las actualizaciones de seguridad mensuales. El aislamiento de Hyper-V no evita los requisitos de compatibilidad de Kubernetes.

## Configuración de nodos Windows

Veamos el proceso para añadir nodos Windows a un clúster de Kubernetes.

### Requisitos previos

Use una combinación compatible de Kubernetes y Windows, un plano de control Linux, un CNI compatible con Windows y containerd compatible con CRI. Docker Engine por sí solo no implementa CRI; dockershim, que estaba integrado, se eliminó en Kubernetes 1.24. Para los nodos de EKS, siga la sección de EKS más abajo.

### Preparación de nodos Windows

Habilite la característica Containers en PowerShell como administrador y complete los reinicios que sean necesarios. Las instrucciones siguientes son para **nodos de trabajo kubeadm autoadministrados**. Descargue `hostprocess/Install-Containerd.ps1` y `hostprocess/PrepareNode.ps1` desde un commit revisado del repositorio oficial sig-windows-tools, inspecciónelos y verifique sus sumas de comprobación antes de ejecutarlos. Seleccione una versión de parche de containerd compatible y una versión de kubelet compatible con el clúster. Revise las reglas de firewall que crea el instalador y restrinja el puerto 10250 a los orígenes necesarios del plano de control.

```powershell
$ErrorActionPreference = "Stop"
$ContainerdVersion = Read-Host "Validated containerd version (without v)"
$KubernetesVersion = Read-Host "Cluster-compatible Kubernetes version (vX.Y.Z)"
if (-not $ContainerdVersion -or -not $KubernetesVersion) { throw "Versions required" }
.\Install-Containerd.ps1 -ContainerDVersion $ContainerdVersion
.\PrepareNode.ps1 -KubernetesVersion $KubernetesVersion
```

### Unión de un nodo Windows mediante kubeadm

Genere un token de unión en el plano de control Linux:

```bash
kubeadm token create --print-join-command
```

Ejecute el comando de unión en el nodo Windows:

```powershell
# Run kubeadm join command
kubeadm join <control-plane-host>:<control-plane-port> --token <token> --discovery-token-ca-cert-hash sha256:<hash>

```

### Configuración de etiquetas del nodo Windows

Inspeccione las etiquetas de sistema operativo, arquitectura y compilación que publica kubelet. No sobrescriba una etiqueta del sistema operativo para forzar la programación. `spec.os.name` declara el sistema operativo del Pod, pero no sustituye los selectores del planificador; use también `nodeSelector`.

```bash
kubectl get nodes -L kubernetes.io/os,kubernetes.io/arch,node.kubernetes.io/windows-build
```

## Despliegue de contenedores Windows

Veamos cómo desplegar contenedores Windows en Kubernetes.

### Uso de nodeSelector

Al desplegar cargas de trabajo Windows, use un selector de nodo para asegurarse de que se programen en nodos Windows:

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
      os:
        name: windows
      nodeSelector:
        kubernetes.io/os: windows
      containers:
      - name: iis
        image: mcr.microsoft.com/windows/servercore/iis:windowsservercore-ltsc2022
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

Las solicitudes y los límites de recursos de los contenedores Windows se gestionan de forma distinta a los de los contenedores Linux:

1. **Límites de CPU**: En Windows, los límites de CPU se aplican de otra manera. Por ejemplo, un límite de CPU de 1 permite usar el 100 % de un único núcleo de CPU.
2. **Límites de memoria**: Los contenedores Windows respetan los límites de memoria, aunque algunos procesos del sistema pueden generar una sobrecarga adicional.

### Personalización de contenedores

Ejecución de scripts personalizados en contenedores Windows:

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: windows-custom-script
spec:
  os:
    name: windows
  nodeSelector:
    kubernetes.io/os: windows
  containers:
  - name: windows-container
    image: mcr.microsoft.com/windows/servercore:ltsc2022
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

Windows también admite Pods con varios contenedores, aunque con algunas limitaciones:

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: windows-multi-container
spec:
  os:
    name: windows
  nodeSelector:
    kubernetes.io/os: windows
  containers:
  - name: writer
    image: mcr.microsoft.com/windows/servercore:ltsc2022
    command: [powershell.exe, -Command, 'while ($true) { Add-Content C:\shared-logs\app.log "Log at $(Get-Date)"; Start-Sleep 10 }']
    volumeMounts:
    - name: logs
      mountPath: C:\shared-logs
  - name: logger
    image: mcr.microsoft.com/windows/servercore:ltsc2022
    command: [powershell.exe, -Command, 'while (-not (Test-Path C:\shared-logs\app.log)) { Start-Sleep 2 }; Get-Content C:\shared-logs\app.log -Wait']
    volumeMounts:
    - name: logs
      mountPath: C:\shared-logs
      readOnly: true
  volumes:
  - name: logs
    emptyDir: {}
```

## Redes

Las redes de los nodos Windows tienen características distintas de las de los nodos Linux.

El diagrama siguiente muestra la arquitectura de red de un clúster de Kubernetes con nodos Windows y Linux:

![Un cliente usa una IP virtual de Service, cuyo plano de datos selecciona endpoints de Pods Linux o Windows. La conectividad entre Pods de sistemas operativos distintos depende de rutas y políticas CNI compatibles; el objeto de API Service no es un salto de procesamiento de paquetes.](../.gitbook/assets/en-core-10-windows-in-kubernetes-2.png)

[🔍 Ver el diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-core-10-windows-in-kubernetes-2.html)

### Plugins de red compatibles

Plugins de red compatibles con nodos Windows:

1. **Flannel**: Modo VXLAN o host-gw
2. **Calico**: Modo VXLAN
3. **Antrea**: Redes basadas en OVS
4. **Azure CNI**: Para entornos de Azure
5. **AWS VPC CNI**: Para entornos de AWS

### Ejemplo de configuración de Flannel

Copiar un manifiesto de Flannel para Linux a un DaemonSet de Windows no funciona. Se necesitan los binarios de Windows, HNS, las rutas de CNI, RBAC y la configuración de HostProcess. Use el procedimiento de instalación de Windows de la distribución y coordine las redes Linux con la configuración `win-overlay`/`win-bridge` de Windows. Compruebe los requisitos de VXLAN de Flannel para Windows: VNI 4096/UDP 4789. Añadir `hostNetwork` a un Pod de aplicación normal no es un método de instalación.

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

Para usar políticas de red en nodos Windows, necesita un plugin CNI compatible con NetworkPolicy, por ejemplo Calico:

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

Veamos las opciones de almacenamiento disponibles en los nodos Windows.

El diagrama siguiente muestra varias opciones de almacenamiento disponibles en nodos Windows:

![Un contenedor Windows en un Pod Windows monta volúmenes emptyDir y hostPath en el nodo Windows (hostPath usa el disco del nodo), recibe volúmenes ConfigMap y Secret mediante la API de Kubernetes y accede a un PersistentVolume de Azure Disk/File, AWS EBS o un recurso compartido SMB mediante un controlador CSI.](../.gitbook/assets/en-core-10-windows-in-kubernetes-3.png)

[🔍 Ver el diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-core-10-windows-in-kubernetes-3.html)

### Tipos de volúmenes compatibles

Tipos de volumen compatibles con nodos Windows:

1. **emptyDir**: Almacenamiento temporal (no se admite `emptyDir` basado en memoria)
2. **hostPath**: Sistema de archivos del nodo host
3. **configMap**: Datos de configuración
4. **secret**: Datos confidenciales
5. **CSI/PVC**: Controladores CSI de Azure Files, Azure Disk, EBS o SMB compatibles con Windows y volúmenes de sistema de archivos; compruebe la compatibilidad de sistema operativo y sistema de archivos de cada controlador.

### Ejemplo de volumen emptyDir

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: windows-emptydir
spec:
  os:
    name: windows
  nodeSelector:
    kubernetes.io/os: windows
  containers:
  - name: windows-container
    image: mcr.microsoft.com/windows/servercore:ltsc2022
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
  os:
    name: windows
  nodeSelector:
    kubernetes.io/os: windows
  containers:
  - name: windows-container
    image: mcr.microsoft.com/windows/servercore:ltsc2022
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

### Ejemplo de volumen ConfigMap y Secret

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
  os:
    name: windows
  nodeSelector:
    kubernetes.io/os: windows
  containers:
  - name: windows-container
    image: mcr.microsoft.com/windows/servercore:ltsc2022
    volumeMounts:
    - name: config-volume
      mountPath: C:\config
    - name: secret-volume
      mountPath: C:\secret
      readOnly: true
    command:
    - powershell.exe
    - -Command
    - |
      Get-Content -Path C:\config\config.json
      if (-not (Test-Path C:\secret\username) -or -not (Test-Path C:\secret\password)) { throw "Secret files missing" }
      while ($true) { Start-Sleep -Seconds 10 }
  volumes:
  - name: config-volume
    configMap:
      name: windows-config
  - name: secret-volume
    secret:
      secretName: windows-secret
```

### Uso de controladores CSI

Requisito previo: cree `windows-csi` con un controlador CSI instalado y compatible con Windows, y con un sistema de archivos (por ejemplo, EBS CSI con NTFS y `WaitForFirstConsumer`). El nombre por sí solo no instala un controlador. Los volúmenes EBS están asociados a una AZ; use el modo de sistema de archivos, no el de bloques sin formato.

Ejemplo:

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
  os:
    name: windows
  nodeSelector:
    kubernetes.io/os: windows
  containers:
  - name: windows-container
    image: mcr.microsoft.com/windows/servercore:ltsc2022
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

## Supervisión y registro

Veamos métodos para supervisar y recopilar registros de nodos y contenedores Windows.

### Supervisión

Herramientas para supervisar nodos Windows:

1. **Prometheus Windows Exporter**: Recopila métricas de nodos Windows
2. **metrics-server**: Proporciona métricas básicas de uso de recursos
3. **Datadog, Dynatrace, New Relic**: Soluciones comerciales de supervisión

Instalación de Prometheus Windows Exporter en nodos Windows:

```powershell
# Download a supported release MSI, verify its checksum, then install locally.
$ExporterMsi = (Resolve-Path .\windows_exporter.msi).Path
Start-Process msiexec.exe -ArgumentList "/i `"$ExporterMsi`" ENABLED_COLLECTORS=cpu,memory,logical_disk,net,service,os,system REMOVE=FirewallException /quiet" -Wait
# Restrict any separately configured port 9182 firewall rule to Prometheus sources.
```

Configuración de Prometheus:

```yaml
scrape_configs:
  - job_name: 'windows-nodes'
    static_configs:
      - targets: ['windows-node-1:9182', 'windows-node-2:9182']
```

### Registro

Herramientas para recopilar registros de contenedores Windows:

1. **Fluent Bit**: Recopilador de registros ligero
2. **Fluentd**: Recopilación y reenvío de registros
3. **Elasticsearch**: Almacenamiento y búsqueda de registros
4. **Azure Monitor**: Para entornos de Azure
5. **CloudWatch Logs**: Para entornos de AWS

Instalación de Fluent Bit en nodos Windows:

Configure el endpoint real de Elasticsearch, la autenticación y la CA de confianza. La cuenta de servicio necesita permiso de lectura del registro de eventos Security y permiso de escritura en la ruta de checkpoints.

```powershell
# Install a supported Windows Fluent Bit release, verify its checksum,
# and arrange bin/ and conf/ under C:\fluent-bit before continuing.

# Create configuration file
@"
[SERVICE]
    Flush        5
    Daemon       Off
    Log_Level    info

[INPUT]
    Name         winlog
    Channels     Application,System,Security
    DB           C:\fluent-bit\winlog.db

[OUTPUT]
    Name         es
    Match        *
    Host         elasticsearch-host
    Port         9200
    Index        windows_logs
    Suppress_Type_Name On
    tls          On
    tls.verify   On
"@ | Out-File -FilePath C:\fluent-bit\conf\fluent-bit.conf -Encoding ascii

# Register service
sc.exe create fluent-bit binPath= "C:\fluent-bit\bin\fluent-bit.exe -c C:\fluent-bit\conf\fluent-bit.conf"
Start-Service fluent-bit
```

### Recopilación de registros de aplicaciones

Integre Microsoft LogMonitor en la imagen de la aplicación y defina los orígenes reales de archivos/ETW/Event Log en `LogMonitorConfig.json` para enviar los registros de IIS a stdout. Pruebe el punto de entrada para que los ciclos de vida de ServiceMonitor e IIS sigan siendo correctos. El sidecar con archivo compartido anterior muestra cómo compartir un volumen; no gestiona la rotación de archivos ni los registros duplicados/perdidos durante un reinicio. Los recopiladores de producción necesitan checkpoints y control de rotación. `kubectl logs` lee stdout/stderr y no recopila automáticamente los archivos de IIS.

## Seguridad

Veamos las consideraciones de seguridad para nodos y contenedores Windows.

### Seguridad de nodos Windows

Recomendaciones para proteger los nodos Windows:

1. **Aplicar las últimas actualizaciones**: Aplique periódicamente las actualizaciones de seguridad de Windows.
2. **Configuración del firewall**: Configure correctamente Windows Defender Firewall.
3. **Principio de privilegio mínimo**: Conceda solo los permisos mínimos necesarios.
4. **Antivirus**: Instale software antivirus adecuado.
5. **Directiva de grupo**: Aplique directivas de grupo para reforzar la seguridad.

### Seguridad de contenedores Windows

Recomendaciones para proteger los contenedores Windows:

1. **Imagen base mínima**: Use la imagen base más pequeña posible, como Nano Server.
2. **Análisis de imágenes**: Analice las imágenes de contenedor en busca de vulnerabilidades.
3. **Permisos del sistema de archivos**: Restrinja las ACL de NTFS y use montajes de datos de solo lectura cuando se admitan; Windows no admite `readOnlyRootFilesystem`.
4. **Usuario sin privilegios**: Ejecute las aplicaciones con usuarios sin privilegios.
5. **Políticas de red**: Aplique políticas de red adecuadas.

### RunAsUsername

En contenedores Windows, puede usar `securityContext.windowsOptions.runAsUserName` en lugar de `runAsUser` para especificar el usuario que se ejecutará dentro del contenedor:

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: windows-runasusername
spec:
  os:
    name: windows
  nodeSelector:
    kubernetes.io/os: windows
  securityContext:
    windowsOptions:
      runAsUserName: "ContainerUser"
  containers:
  - name: windows-container
    image: mcr.microsoft.com/windows/servercore:ltsc2022
    command:
    - powershell.exe
    - -Command
    - |
      whoami
      while ($true) { Start-Sleep -Seconds 10 }
```

### Cuentas de servicio administradas de grupo (gMSA)

`gmsaCredentialSpecName` hace referencia a un **GMSACredentialSpec** con ámbito de clúster, no a un Secret. Instale el CRD, los webhooks de mutación/validación y el permiso RBAC `use` de ServiceAccount. Reemplace los nombres de dominio/host de ejemplo y genere los valores de SID/GUID/NetBIOS/DNS de AD mediante el módulo CredentialSpec. Este ejemplo usa hosts unidos al dominio; una configuración de identidad portátil compatible con hosts que no estén unidos al dominio requiere una configuración aparte.

Compruebe primero `Get-KdsRootKey`. Si necesita una clave nueva, un administrador de AD ejecuta `Add-KdsRootKey -EffectiveImmediately` y espera el tiempo necesario para la replicación (hasta 10 horas). Retroceder la fecha 10 horas es solo para un entorno de prueba con un único controlador de dominio. gMSA proporciona credenciales de red; no une el contenedor al dominio ni hace que `whoami` muestre el nombre de gMSA. Valide la autenticación Kerberos real del servicio e inspeccione `klist`.

```powershell
# On an authorized AD administration host, after KDS readiness is confirmed:
Import-Module ActiveDirectory
New-ADGroup -Name 'WebAppHosts' -SamAccountName 'WebAppHosts' -GroupScope DomainLocal
Add-ADGroupMember -Identity 'WebAppHosts' -Members 'ContainerHost01$'
New-ADServiceAccount -Name WebApp1 -DNSHostName WebApp1.contoso.com -ServicePrincipalNames http/WebApp1.contoso.com -PrincipalsAllowedToRetrieveManagedPassword WebAppHosts
# Install/review the official CredentialSpec PowerShell module first.
Import-Module CredentialSpec
New-CredentialSpec -AccountName WebApp1 -Path C:\gmsa-credspec.json
$spec = Get-Content C:\gmsa-credspec.json -Raw | ConvertFrom-Json
@{ apiVersion='windows.k8s.io/v1'; kind='GMSACredentialSpec'; metadata=@{name='gmsa-cred-spec'}; credspec=$spec } |
    ConvertTo-Json -Depth 20 | Set-Content C:\gmsa-resource.json -Encoding utf8
```

```bash
# Requires the GMSA CRD and mutating/validating webhooks installed by an administrator.
kubectl apply -f gmsa-resource.json
```

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: windows-app
  namespace: default
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: use-webapp-gmsa
rules:
- apiGroups: [windows.k8s.io]
  resources: [gmsacredentialspecs]
  resourceNames: [gmsa-cred-spec]
  verbs: [use]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: use-webapp-gmsa
  namespace: default
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: use-webapp-gmsa
subjects:
- kind: ServiceAccount
  name: windows-app
  namespace: default
---
apiVersion: v1
kind: Pod
metadata:
  name: windows-gmsa
  namespace: default
spec:
  os:
    name: windows
  serviceAccountName: windows-app
  nodeSelector:
    kubernetes.io/os: windows
  securityContext:
    windowsOptions:
      gmsaCredentialSpecName: gmsa-cred-spec
      runAsUserName: 'NT AUTHORITY\NETWORK SERVICE'
  containers:
  - name: windows-container
    image: mcr.microsoft.com/windows/servercore:ltsc2022
    command: [powershell.exe, -Command, 'whoami; Start-Sleep -Seconds 3600']
```

## Compatibilidad con Windows en Amazon EKS

Veamos cómo ejecutar cargas de trabajo Windows en Amazon EKS.

El diagrama siguiente muestra la arquitectura de compatibilidad con Windows en Amazon EKS:

![El plano de control administrado de EKS gestiona tanto un grupo de nodos Linux (con los Pods del sistema CoreDNS, VPC CNI y kube-proxy) como un grupo de nodos Windows (con Pods de aplicaciones Windows), se integra con AWS IAM, Amazon VPC y CloudWatch, y conecta los Pods de aplicaciones Windows con los usuarios finales a través de un Elastic Load Balancer.](../.gitbook/assets/en-core-10-windows-in-kubernetes-4.png)

[🔍 Ver el diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-core-10-windows-in-kubernetes-4.html)

### Habilitación de la compatibilidad con Windows en EKS

EKS administra el controlador de recursos de VPC responsable de IPAM para Windows. No instale los antiguos manifiestos de controlador/webhook de release-1.11. Conceda al rol IAM del clúster los permisos `AmazonEKSVPCResourceController` y siga las instrucciones actuales de AWS para establecer `enable-windows-ipam: "true"` en `kube-system/amazon-vpc-cni`. Conserve las claves existentes y configure este ajuste mediante el flujo de trabajo propietario de Helm/add-on cuando corresponda.

Proporcione nodos Linux o una configuración de Fargate compatible para CoreDNS. Windows no es compatible con EKS Auto Mode, las cargas de trabajo de Fargate, Hybrid Nodes, IPv6, redes personalizadas ni los grupos de seguridad para Pods. El tipo de entrada de acceso del rol de nodo Windows es `EC2_WINDOWS`; las asignaciones antiguas de aws-auth requieren el grupo `eks:kube-proxy-windows`.

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
  --node-ami-family WindowsServer2022FullContainer
```

Creación de un grupo de nodos Windows mediante la consola de administración de AWS:

1. Seleccione el clúster en la consola de EKS.
2. Seleccione la pestaña «Compute».
3. Haga clic en «Add node group».
4. Introduzca los detalles del grupo de nodos.
5. Seleccione «Windows» como tipo de AMI.
6. Configure los demás ajustes y créelo.

### Despliegue de aplicaciones Windows en EKS

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
      os:
        name: windows
      nodeSelector:
        kubernetes.io/os: windows
      containers:
      - name: windows-server-iis
        image: mcr.microsoft.com/windows/servercore/iis:windowsservercore-ltsc2022
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

Windows Container Insights es compatible con la versión 1.5.0 o posterior del add-on CloudWatch Observability para EKS. Seleccione una versión del add-on compatible con el clúster, los permisos de IAM y la configuración del agente Windows. Windows Application Signals no es compatible.

Recopile stdout/stderr de Windows desde las rutas de registros CRI de kubelet (normalmente `C:\var\log\pods` y `C:\var\log\containers`); verifique las rutas de la distribución en lugar de copiar las rutas Linux `/var/log` y la configuración del analizador de Docker. EKS escribe los registros de kubelet/kube-proxy en el registro de eventos **EKS Windows**. Montar archivos .evtx en un contenedor normal no permite a winlog acceder a la API de eventos del host. Use un servicio del host o un recopilador HostProcess revisado.

## Prácticas recomendadas

Veamos las prácticas recomendadas para ejecutar cargas de trabajo Windows en Kubernetes.

### Prácticas recomendadas de diseño del clúster

1. **Grupos mixtos de nodos**: Use una combinación adecuada de nodos Linux y Windows.
2. **Etiquetas y taints de nodos**: Use etiquetas y taints adecuados para separar las cargas de trabajo.
3. **Compatibilidad de versiones**: Verifique la compatibilidad entre las versiones de Kubernetes y Windows.
4. **Selección del plugin de red**: Elija un plugin de red compatible con Windows.
5. **Alta disponibilidad**: Configure alta disponibilidad para las cargas de trabajo críticas.

### Prácticas recomendadas de diseño de aplicaciones

1. **Optimización de imágenes de contenedor**: Use imágenes de contenedor pequeñas y eficientes.
2. **Solicitudes y límites de recursos**: Establezca solicitudes y límites de recursos adecuados.
3. **Diseño sin estado**: Diseñe aplicaciones sin estado cuando sea posible.
4. **Registro y supervisión**: Configure un registro y una supervisión eficaces.
5. **Refuerzo de seguridad**: Aplique contextos de seguridad y políticas de red adecuados.

### Prácticas recomendadas operativas

1. **Actualizaciones periódicas**: Actualice periódicamente los nodos Windows y las imágenes de contenedor.
2. **Automatización**: Automatice las tareas de despliegue y administración.
3. **Copia de seguridad y recuperación**: Haga copias de seguridad periódicas de los datos importantes.
4. **Herramientas de solución de problemas**: Prepare herramientas y procesos adecuados para diagnosticar problemas.
5. **Documentación**: Documente las configuraciones y los procedimientos.

### Prácticas recomendadas específicas de EKS

1. **Grupos de nodos administrados**: Use grupos de nodos administrados cuando sea posible.
2. **Roles IAM para cuentas de servicio (IRSA)**: Administre los permisos IAM por Pod.
3. **Configuración de VPC CNI**: Configure VPC CNI según los requisitos de red.
4. **Grupos de seguridad**: Configure grupos de seguridad adecuados.
5. **Optimización de costos**: Seleccione los tipos y tamaños de instancia adecuados.

## Conclusión

La compatibilidad de Kubernetes con Windows sigue evolucionando y ahora se pueden ejecutar cargas de trabajo Windows en entornos de producción. Los nodos Windows pueden ejecutarse junto a nodos Linux en el mismo clúster, lo que permite administrar diversas cargas de trabajo en un único clúster de Kubernetes.

Los contenedores Windows permiten empaquetar aplicaciones de .NET Framework, servicios Windows y otras cargas de trabajo específicas de Windows para aprovechar la orquestación de Kubernetes. Sin embargo, tienen algunas limitaciones frente a los contenedores Linux, por lo que es importante comprenderlas y abordarlas adecuadamente.

Amazon EKS ofrece servicios administrados para nodos Windows, lo que facilita el despliegue y la administración de estas cargas de trabajo. La compatibilidad de EKS con Windows puede simplificar la migración de aplicaciones Windows a entornos modernos de contenedores.

Para implementar correctamente Windows en Kubernetes, es importante seguir prácticas adecuadas de planificación, diseño y operación. Esto permite administrar de forma eficiente las cargas de trabajo Windows y Linux y aprovechar las ventajas de Kubernetes.

## Cuestionario

Para comprobar lo aprendido en este capítulo, pruebe el [cuestionario sobre Windows en Kubernetes](../quizzes/core/10-windows-in-kubernetes-quiz.md).

## Referencias de verificación

- https://kubernetes.io/docs/concepts/windows/intro/
- https://kubernetes.io/docs/tasks/administer-cluster/kubeadm/adding-windows-nodes/
- https://kubernetes.io/docs/tasks/configure-pod-container/create-hostprocess-pod/
- https://kubernetes.io/docs/tasks/configure-pod-container/configure-gmsa/
- https://learn.microsoft.com/en-us/virtualization/windowscontainers/deploy-containers/version-compatibility
- https://github.com/microsoft/windows-container-tools/tree/main/LogMonitor
- https://docs.aws.amazon.com/eks/latest/userguide/windows-support.html
- https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/install-CloudWatch-Observability-EKS-addon.html
