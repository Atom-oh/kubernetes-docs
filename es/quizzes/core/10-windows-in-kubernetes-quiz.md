# Cuestionario sobre Windows en Kubernetes

Este cuestionario evalúa tu conocimiento conceptual y práctico sobre la administración de nodes de Windows y workloads en Kubernetes. Cubre temas como los conceptos básicos de Windows containers, la configuración de Windows nodes en Kubernetes, networking, almacenamiento, seguridad y monitoreo.

## Preguntas de opción múltiple

1. ¿Qué container runtimes son compatibles con Windows nodes en Kubernetes?
   - A) Docker y containerd
   - B) CRI-O y Docker
   - C) containerd y CRI-O
   - D) Docker, containerd y gVisor

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A) Docker y containerd**

**Explicación:**
Los container runtimes oficialmente compatibles para Windows nodes en Kubernetes son Docker y containerd.

- **Docker**: Docker era la opción tradicional para ejecutar Windows containers en Windows. Sin embargo, el soporte de Docker en Kubernetes está disminuyendo gradualmente, y se recomienda migrar a containerd.

- **containerd**: Este es el container runtime recomendado actualmente para Windows nodes. containerd es un runtime ligero y estable que tiene soporte oficial para Windows nodes en Kubernetes 1.20 y versiones posteriores.

CRI-O no es oficialmente compatible con Windows nodes. CRI-O es principalmente una implementación de Container Runtime Interface (CRI) para Linux containers.

gVisor es un sandbox runtime para aislamiento de containers, pero actualmente no es compatible con Windows nodes.

Al configurar container runtimes en Windows nodes, es importante verificar la compatibilidad con la versión de Kubernetes.
</details>

2. ¿Qué solución de red se requiere al configurar un cluster con Windows y Linux nodes mezclados en Kubernetes?
   - A) Todos los plugins CNI admiten tanto Windows como Linux nodes
   - B) Plugins CNI que admitan Windows, como Flannel, Calico y Antrea
   - C) Windows nodes deben usar solo kubenet sin plugins CNI
   - D) Windows nodes siempre deben usar únicamente el modo de red del host

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Plugins CNI que admitan Windows, como Flannel, Calico y Antrea**

**Explicación:**
Al configurar un cluster con Windows y Linux nodes mezclados en Kubernetes, debes usar plugins CNI (Container Network Interface) específicos que admitan Windows. No todos los plugins CNI admiten Windows.

Los principales plugins CNI que admiten Windows nodes son:

- **Flannel**: Admite Windows nodes en modo de red overlay (vxlan).
- **Calico**: Proporciona soporte para Windows nodes, con compatibilidad tanto para el modo BGP como para el modo VXLAN.
- **Antrea**: Proporciona soporte para Windows nodes, usando OVS (Open vSwitch).

Además, Azure CNI, OVN-Kubernetes y otros admiten Windows nodes.

Consideraciones al configurar plugins CNI en Windows nodes:
- Windows nodes tienen una stack de networking diferente a la de Linux nodes.
- Algunas funciones de networking pueden estar limitadas en Windows.
- Debes verificar la versión de soporte de Windows y los requisitos de configuración del plugin CNI.

kubenet no es compatible con Windows nodes, y Windows nodes no pueden usar el modo de red del host (HostNetwork=true no es compatible con Windows pods).
</details>

3. ¿Cuál es el modo de aislamiento predeterminado para Windows containers?
   - A) Aislamiento Hyper-V
   - B) Aislamiento de procesos
   - C) Aislamiento de máquina virtual
   - D) Aislamiento sandbox

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Aislamiento de procesos**

**Explicación:**
El modo de aislamiento predeterminado para Windows containers es Process Isolation. En este modo, Windows containers comparten el kernel del sistema operativo del host, y cada container se ejecuta como un grupo de procesos aislado.

Características del modo de aislamiento de procesos:
- Debe usar la misma versión de kernel que el host OS.
- Menor uso de recursos y tiempo de inicio más rápido.
- Similar al modelo de aislamiento típico de Linux containers.

Windows también proporciona un modo de aislamiento alternativo llamado Hyper-V Isolation:
- Cada container se ejecuta en una máquina virtual ligera.
- Puede usar versiones de kernel diferentes a las del host OS.
- Proporciona un nivel de aislamiento mayor, pero tiene más sobrecarga.

Para usar aislamiento Hyper-V en Kubernetes, agrega la siguiente annotation a la especificación del pod:
```yaml
annotations:
  io.kubernetes.cri-containerd.isolation: hyperv
```

El aislamiento de máquina virtual no es un modo de aislamiento oficial para Windows containers, y aislamiento sandbox no es un término usado para Windows containers.
</details>

4. ¿Cuál de las siguientes NO es una limitación correcta al usar Windows nodes en Kubernetes?
   - A) No se pueden usar privileged containers
   - B) No se pueden usar volúmenes HostPath
   - C) Solo algunas funciones de SecurityContext son compatibles para pods
   - D) No se puede compartir el namespace de red del pod

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) No se pueden usar volúmenes HostPath**

**Explicación:**
Los volúmenes HostPath se pueden usar en Windows nodes. Por lo tanto, la afirmación "No se pueden usar volúmenes HostPath" es incorrecta.

Al usar volúmenes HostPath en Windows nodes, debes seguir el formato de rutas de Windows:
```yaml
volumes:
- name: data
  hostPath:
    path: C:\\data
```

Las limitaciones reales al usar Windows nodes en Kubernetes son:

- **Privileged containers**: Privileged containers no se pueden usar en Windows nodes. Esto se debe a que no existe un concepto equivalente al modo privilegiado de Linux en Windows.

- **Limitaciones de SecurityContext**: Solo algunas funciones de SecurityContext son compatibles en Windows nodes. Por ejemplo, runAsUser, runAsGroup, fsGroup, seccomp, SELinux, etc. no son compatibles.

- **Uso compartido del namespace de red del Pod**: Los namespaces de red no se pueden compartir entre pods en Windows nodes. Esto afecta a hostNetwork: true, dnsPolicy: ClusterFirstWithHostNet, comunicación localhost entre containers en un pod, etc.

Otras limitaciones de Windows nodes:
- Si quieres que DaemonSets se ejecuten en todos los nodes (Linux y Windows), debes usar nodeSelector.
- Algunos storage drivers y tipos de volúmenes pueden estar limitados.
- Las funciones alpha/beta específicas de Linux pueden no funcionar en Windows nodes.
</details>

5. ¿Qué label de node se usa para identificar Windows nodes en Kubernetes?
   - A) kubernetes.io/os=windows
   - B) beta.kubernetes.io/os=windows
   - C) node.kubernetes.io/windows=true
   - D) kubernetes.io/windows=enabled

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A) kubernetes.io/os=windows**

**Explicación:**
El label estándar de node usado para identificar Windows nodes en Kubernetes es `kubernetes.io/os=windows`. Este label indica el tipo de sistema operativo del node y lo usa el scheduler de Kubernetes para colocar pods en los nodes adecuados.

Para programar Windows pods en Windows nodes, usa nodeSelector de la siguiente manera:
```yaml
nodeSelector:
  kubernetes.io/os: windows
```

O puedes usar node affinity:
```yaml
affinity:
  nodeAffinity:
    requiredDuringSchedulingIgnoredDuringExecution:
      nodeSelectorTerms:
      - matchExpressions:
        - key: kubernetes.io/os
          operator: In
          values:
          - windows
```

`beta.kubernetes.io/os=windows` se usaba en versiones anteriores de Kubernetes, pero ahora está obsoleto.

`node.kubernetes.io/windows=true` y `kubernetes.io/windows=enabled` no son labels estándar de Kubernetes.

Nota: Linux nodes tienen el label `kubernetes.io/os=linux`.
</details>

6. ¿Cuál es la imagen base predeterminada que se usa al descargar imágenes de containers en Windows nodes?
   - A) mcr.microsoft.com/windows/servercore
   - B) mcr.microsoft.com/windows/nanoserver
   - C) mcr.microsoft.com/dotnet/framework/runtime
   - D) mcr.microsoft.com/powershell

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A) mcr.microsoft.com/windows/servercore**

**Explicación:**
La imagen base más común para Windows containers es `mcr.microsoft.com/windows/servercore`. Esta imagen se basa en una instalación de Windows Server Core e incluye los componentes principales necesarios para ejecutar la mayoría de las aplicaciones de Windows.

Las principales imágenes base disponibles para Windows containers son:

1. **Windows Server Core** (`mcr.microsoft.com/windows/servercore`):
   - Imagen de tamaño medio (aproximadamente 2-4GB)
   - Admite la mayoría de las aplicaciones de Windows
   - Incluye .NET Framework, PowerShell, etc.
   - Imagen base de Windows más utilizada

2. **Nano Server** (`mcr.microsoft.com/windows/nanoserver`):
   - Imagen muy pequeña (aproximadamente 100-200MB)
   - Soporte limitado para API de Windows
   - Adecuada para aplicaciones .NET Core
   - Superficie de ataque mínima

3. **.NET Framework** (`mcr.microsoft.com/dotnet/framework/runtime`):
   - Imagen para aplicaciones .NET Framework
   - Basada en Server Core
   - Incluye versiones específicas de .NET Framework

4. **PowerShell** (`mcr.microsoft.com/powershell`):
   - Imagen para ejecutar scripts de PowerShell
   - Disponible en versiones basadas en Nano Server o Server Core

Al seleccionar una imagen de Windows container, considera:
- Requisitos de la aplicación (API de Windows requeridas)
- Tamaño de la imagen y tiempo de inicio
- Requisitos de seguridad
- Compatibilidad de versión de Windows (verifica el número de versión en el tag de la imagen)

Las imágenes de Windows containers deben ser de la misma versión que el host OS o compatibles con él.
</details>

7. ¿Cuál es el método recomendado para desplegar DaemonSets en un cluster con Windows y Linux nodes mezclados en Kubernetes?
   - A) Usar un único DaemonSet y desplegarlo en todos los nodes
   - B) Crear DaemonSets separados para cada OS y usar nodeSelector
   - C) Usar StatefulSet en lugar de DaemonSet para Windows nodes
   - D) Agregar tolerations a todos los DaemonSets

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Crear DaemonSets separados para cada OS y usar nodeSelector**

**Explicación:**
El método recomendado para desplegar DaemonSets en un cluster con Windows y Linux nodes mezclados en Kubernetes es crear DaemonSets separados para cada OS y usar nodeSelector.

Razones por las que este enfoque es necesario:
- Windows containers y Linux containers usan formatos de imagen diferentes.
- La misma aplicación puede requerir configuraciones diferentes para cada OS.
- Algunas funciones pueden estar disponibles solo en OSes específicos.

Ejemplo de Windows DaemonSet:
```yaml
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: windows-agent
spec:
  selector:
    matchLabels:
      app: monitoring-agent
  template:
    metadata:
      labels:
        app: monitoring-agent
    spec:
      nodeSelector:
        kubernetes.io/os: windows
      containers:
      - name: agent
        image: contoso/windows-monitoring-agent:v1
```

Ejemplo de Linux DaemonSet:
```yaml
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: linux-agent
spec:
  selector:
    matchLabels:
      app: monitoring-agent
  template:
    metadata:
      labels:
        app: monitoring-agent
    spec:
      nodeSelector:
        kubernetes.io/os: linux
      containers:
      - name: agent
        image: contoso/linux-monitoring-agent:v1
```

Usar un único DaemonSet puede hacer que los pods no se inicien en algunos nodes debido a problemas de compatibilidad de imágenes de containers.

DaemonSets se pueden usar en Windows nodes, por lo que no es necesario reemplazarlos con StatefulSets.

Agregar tolerations a todos los DaemonSets puede ayudar a programar pods en nodes con taints, pero no resuelve problemas de compatibilidad de OS.
</details>

8. ¿Qué afirmación sobre la configuración DNS para pods en Windows nodes es correcta?
   - A) La configuración DNS no es compatible con Windows nodes
   - B) Windows nodes deben usar Windows DNS Server en lugar de CoreDNS
   - C) Windows nodes pueden usar la misma configuración DNS que Linux nodes
   - D) Windows nodes requieren una configuración de servidor DNS separada para cada pod

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Windows nodes pueden usar la misma configuración DNS que Linux nodes**

**Explicación:**
Windows nodes pueden usar la misma configuración DNS que Linux nodes. El Service DNS de Kubernetes (normalmente CoreDNS) funciona de la misma manera para Windows pods.

Configuración DNS para Windows pods:
- La configuración equivalente a `/etc/resolv.conf` se crea automáticamente dentro de Windows pods.
- Pods pueden usar el Service DNS del cluster (CoreDNS) para resolver nombres de services.
- Los campos `dnsPolicy` y `dnsConfig` se pueden usar para configurar ajustes de DNS.

Ejemplo:
```yaml
apiVersion: v1
kind: Pod
metadata:
  name: windows-pod
spec:
  nodeSelector:
    kubernetes.io/os: windows
  containers:
  - name: windows-container
    image: mcr.microsoft.com/windows/servercore:ltsc2019
    command:
    - powershell.exe
    - -Command
    - "Start-Sleep -Seconds 3600"
  dnsPolicy: ClusterFirst
  dnsConfig:
    nameservers:
    - 8.8.8.8
    searches:
    - example.com
    options:
    - name: ndots
      value: "5"
```

Consideraciones al usar DNS en Windows nodes:
- El comportamiento del cliente DNS dentro de Windows containers puede ser ligeramente diferente al de Linux.
- Algunas herramientas relacionadas con DNS (por ejemplo, nslookup, Resolve-DnsName) están disponibles de forma predeterminada en Windows containers.
- Debes verificar que el plugin de red admita correctamente la resolución DNS.

No es necesario configurar un servidor DNS separado ni usar Windows DNS Server en Windows nodes. El mecanismo DNS estándar de Kubernetes funciona para Windows pods.
</details>

9. ¿Qué afirmación sobre la comunicación pod a pod en Windows nodes es correcta?
   - A) La comunicación pod a pod no es compatible con Windows nodes
   - B) Pods en Windows nodes solo pueden comunicarse con pods en el mismo node
   - C) Pods en Windows nodes no pueden comunicarse con pods en Linux nodes
   - D) Pods en Windows nodes pueden comunicarse con todos los demás pods mediante plugins CNI

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: D) Pods en Windows nodes pueden comunicarse con todos los demás pods mediante plugins CNI**

**Explicación:**
Pods en Windows nodes pueden comunicarse con todos los demás pods del cluster mediante plugins CNI (Container Network Interface) adecuados. Esto incluye pods en el mismo Windows node, pods en otros Windows nodes y pods en Linux nodes.

Características clave de la comunicación pod a pod en Windows nodes:
- Pods en Windows nodes pueden descubrir y acceder a services en el cluster por nombre.
- A Pods en Windows nodes se les asignan direcciones IP únicas dentro del rango de direcciones IP del cluster.
- La comunicación pod a pod ocurre según la implementación del plugin CNI seleccionado.

Plugins CNI que admiten comunicación pod a pod en Windows nodes:
- Flannel (modo VXLAN)
- Calico
- Antrea
- Azure CNI
- OVN-Kubernetes

Por ejemplo, al usar Flannel:
- Pods en Windows nodes se comunican con pods en otros nodes mediante encapsulación VXLAN.
- A cada pod se le asigna una dirección IP dentro del rango CIDR del cluster.
- Las tablas de routing se configuran para enrutar direcciones IP de pods a los nodes adecuados.

Consideraciones para la comunicación pod a pod en Windows nodes:
- Algunas funciones avanzadas de networking pueden estar limitadas en Windows.
- El soporte de NetworkPolicy puede variar según el plugin CNI.
- Las reglas del firewall de Windows no deben interferir con la comunicación de pods.

Pods en Windows nodes pueden comunicarse perfectamente con pods en Linux nodes, lo cual es una de las funciones principales de Kubernetes.
</details>

10. ¿Qué afirmación sobre los límites de recursos para Windows containers en Kubernetes es correcta?
    - A) Windows containers no admiten límites de recursos
    - B) Los límites de CPU son compatibles, pero los límites de memoria no
    - C) Los límites de memoria son compatibles, pero los límites de CPU no
    - D) Tanto los límites de CPU como los de memoria son compatibles

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: D) Tanto los límites de CPU como los de memoria son compatibles**

**Explicación:**
Windows containers en Kubernetes admiten límites de recursos tanto de CPU como de memoria. Windows nodes pueden limitar y solicitar recursos de containers de forma similar a Linux nodes.

Ejemplo de límites de recursos para Windows containers:
```yaml
apiVersion: v1
kind: Pod
metadata:
  name: windows-resource-demo
spec:
  nodeSelector:
    kubernetes.io/os: windows
  containers:
  - name: windows-container
    image: mcr.microsoft.com/windows/servercore:ltsc2019
    resources:
      requests:
        memory: "128Mi"
        cpu: "100m"
      limits:
        memory: "256Mi"
        cpu: "500m"
```

Características de la administración de recursos para Windows containers:
- **Límites de CPU**: Windows implementa CPU sharing y límites para administrar la asignación de recursos de CPU entre containers.
- **Límites de memoria**: Windows limita el uso de memoria de los containers y realiza terminación OOM (Out of Memory) cuando se excede.
- **Monitoreo de recursos**: kubelet monitorea el uso de recursos de Windows containers e informa a la API de Kubernetes.

Consideraciones para la administración de recursos de Windows containers:
- La sobrecarga de recursos predeterminada para Windows containers puede ser mayor que para Linux containers.
- La implementación exacta de los límites de recursos puede variar según la versión de Windows.
- Establecer límites de memoria demasiado bajos puede impedir que Windows containers funcionen correctamente.
- Se produce sobrecarga adicional de recursos al usar el modo de aislamiento Hyper-V.

Puedes monitorear el uso de recursos en Windows nodes usando los comandos `kubectl top pods` y `kubectl top nodes`.
</details>
## Preguntas de respuesta corta

1. Explica los pasos y requisitos principales para agregar Windows nodes a un cluster de Kubernetes.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:**

**Pasos para agregar Windows nodes a un cluster de Kubernetes:**

1. **Verificar requisitos previos:**
   - Kubernetes versión 1.14 o posterior (se recomienda la versión más reciente)
   - El control plane debe ejecutarse en Linux nodes
   - Windows Server 2019 o posterior (se recomienda Windows Server 2022)
   - Plugin CNI compatible (Flannel, Calico, Antrea, etc.)

2. **Configurar networking:**
   - Instalar plugin CNI que admita Windows nodes
   - Configurar cluster CIDR y service CIDR
   - Ejemplo (configuración de Flannel):
     ```yaml
     kind: ConfigMap
     apiVersion: v1
     metadata:
       name: kube-flannel-cfg
       namespace: kube-system
     data:
       cni-conf.json: |
         {
           "name": "cbr0",
           "plugins": [
             {
               "type": "flannel",
               "delegate": {
                 "hairpinMode": true,
                 "isDefaultGateway": true
               }
             },
             {
               "type": "portmap",
               "capabilities": {
                 "portMappings": true
               }
             }
           ]
         }
       net-conf.json: |
         {
           "Network": "10.244.0.0/16",
           "Backend": {
             "Type": "vxlan",
             "VNI": 4096,
             "Port": 4789
           }
         }
     ```

3. **Preparar Windows node:**
   - Instalar y actualizar Windows Server
   - Habilitar las características de Windows requeridas:
     ```powershell
     Install-WindowsFeature -Name Containers
     Restart-Computer -Force
     ```
   - Instalar container runtime (se recomienda containerd):
     ```powershell
     # Download and install containerd
     curl.exe -L https://github.com/containerd/containerd/releases/download/v1.6.8/containerd-1.6.8-windows-amd64.tar.gz -o containerd.tar.gz
     tar.exe xvf containerd.tar.gz
     mkdir -p $env:ProgramFiles\containerd
     Copy-Item -Path ".\bin\*" -Destination "$env:ProgramFiles\containerd" -Recurse -Force

     # Register containerd service
     & $env:ProgramFiles\containerd\containerd.exe config default | Out-File $env:ProgramFiles\containerd\config.toml -Encoding ascii
     # Edit configuration file (add Windows-related settings)

     # Register and start service
     & $env:ProgramFiles\containerd\containerd.exe --register-service
     Start-Service containerd
     ```

4. **Instalar kubelet y kube-proxy:**
   - Descargar binarios de Kubernetes:
     ```powershell
     curl.exe -L https://dl.k8s.io/v1.26.0/kubernetes-node-windows-amd64.tar.gz -o kubernetes-node-windows-amd64.tar.gz
     tar.exe xvf kubernetes-node-windows-amd64.tar.gz
     mkdir -p $env:ProgramFiles\Kubernetes\bin
     Copy-Item -Path "kubernetes\node\bin\*" -Destination "$env:ProgramFiles\Kubernetes\bin" -Recurse -Force
     ```
   - Crear archivo de configuración de kubelet:
     ```powershell
     New-Item -Path "$env:ProgramFiles\Kubernetes\kubelet-config.yaml" -ItemType File -Force
     # Add configuration file contents
     ```
   - Registrar e iniciar el service kubelet:
     ```powershell
     & $env:ProgramFiles\Kubernetes\bin\kubelet.exe --windows-service --config=$env:ProgramFiles\Kubernetes\kubelet-config.yaml
     Start-Service kubelet
     ```
   - Configurar e iniciar kube-proxy (normalmente desplegado como DaemonSet)

5. **Unir el node:**
   - Ejecutar el comando kubeadm join o configurar manualmente certificados TLS y kubeconfig
   - Verificar que el node se haya registrado con el cluster:
     ```bash
     kubectl get nodes
     ```

6. **Agregar labels de node:**
   - Agregar el label de OS al Windows node (si no se agregó automáticamente):
     ```bash
     kubectl label node <windows-node-name> kubernetes.io/os=windows
     ```

7. **Desplegar workload de prueba:**
   - Desplegar un pod simple que ejecute un Windows container:
     ```yaml
     apiVersion: v1
     kind: Pod
     metadata:
       name: windows-test-pod
     spec:
       nodeSelector:
         kubernetes.io/os: windows
       containers:
       - name: windows-server
         image: mcr.microsoft.com/windows/servercore:ltsc2019
         command:
         - powershell.exe
         - -Command
         - "Start-Sleep -Seconds 3600"
     ```

**Consideraciones clave:**

1. **Compatibilidad de versiones:**
   - La versión de Windows Server y la versión de la imagen del container deben ser compatibles
   - Verificar la versión de Kubernetes y las funciones de soporte de Windows

2. **Networking:**
   - Usar plugins CNI compatibles con Windows nodes
   - Verificar soporte de network policy
   - Verificar requisitos de puertos (kubelet, containerd, CNI, etc.)

3. **Almacenamiento:**
   - Verificar storage drivers y tipos de volúmenes compatibles con Windows nodes
   - Verificar compatibilidad de CSI driver

4. **Monitoreo y logging:**
   - Desplegar agentes de monitoreo adecuados para Windows nodes
   - Configurar la recolección de logs de eventos de Windows

5. **Seguridad:**
   - Configurar reglas del firewall de Windows
   - Configurar Group Managed Service Accounts (gMSA) si es necesario
   - Configurar grupos de seguridad de red

6. **Automatización:**
   - Automatizar el aprovisionamiento de Windows nodes (Ansible, PowerShell DSC, etc.)
   - Establecer una estrategia de actualización de nodes
</details>

2. Explica las principales diferencias entre Windows containers y Linux containers, y cómo administrar estas diferencias en Kubernetes.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:**

**Principales diferencias entre Windows containers y Linux containers:**

1. **Tecnología subyacente:**
   - **Linux containers**: Usan namespaces de Linux, cgroups y características del kernel para el aislamiento
   - **Windows containers**: Usan tecnologías de aislamiento de Windows (job objects, aislamiento Hyper-V, etc.)

2. **Estructura de imagen:**
   - **Linux containers**: Tamaño relativamente pequeño (decenas a cientos de MB)
   - **Windows containers**: Generalmente de mayor tamaño (varios GB), las imágenes base son más grandes

3. **Modos de aislamiento:**
   - **Linux containers**: Un solo modo de aislamiento (basado en namespaces)
   - **Windows containers**: Dos modos compatibles: aislamiento de procesos y aislamiento Hyper-V

4. **Sistema de archivos:**
   - **Linux containers**: Sistema de archivos por capas (OverlayFS, etc.)
   - **Windows containers**: Filter driver basado en NTFS

5. **Networking:**
   - **Linux containers**: Varios modos de networking y soporte de drivers
   - **Windows containers**: Modos de networking limitados, solo plugins CNI específicos compatibles

6. **Administración de recursos:**
   - **Linux containers**: Control de recursos detallado mediante cgroups
   - **Windows containers**: Control de recursos mediante Job Objects, con algunas limitaciones

7. **Security Context:**
   - **Linux containers**: Varias opciones de security context (SELinux, AppArmor, etc.)
   - **Windows containers**: Opciones limitadas de security context, privileged containers no compatibles

8. **Dependencia del host OS:**
   - **Linux containers**: Pueden ejecutarse en varias distribuciones de Linux
   - **Windows containers**: Requieren la misma versión o una versión compatible con el host OS

**Cómo administrar estas diferencias en Kubernetes:**

1. **Selección de nodes y scheduling:**
   - **Usar labels de node**: `kubernetes.io/os=windows` o `kubernetes.io/os=linux`
   - **Usar nodeSelector**:
     ```yaml
     nodeSelector:
       kubernetes.io/os: windows
     ```
   - **Usar node affinity**:
     ```yaml
     affinity:
       nodeAffinity:
         requiredDuringSchedulingIgnoredDuringExecution:
           nodeSelectorTerms:
           - matchExpressions:
             - key: kubernetes.io/os
               operator: In
               values:
               - windows
     ```

2. **Separación de workloads:**
   - **Crear Deployments específicos por OS**:
     ```yaml
     # Deployment for Windows workloads
     apiVersion: apps/v1
     kind: Deployment
     metadata:
       name: windows-app
     spec:
       selector:
         matchLabels:
           app: myapp
           os: windows
       template:
         metadata:
           labels:
             app: myapp
             os: windows
         spec:
           nodeSelector:
             kubernetes.io/os: windows
           containers:
           - name: windows-app
             image: myregistry/windows-app:latest

     # Deployment for Linux workloads
     apiVersion: apps/v1
     kind: Deployment
     metadata:
       name: linux-app
     spec:
       selector:
         matchLabels:
           app: myapp
           os: linux
       template:
         metadata:
           labels:
             app: myapp
             os: linux
         spec:
           nodeSelector:
             kubernetes.io/os: linux
           containers:
           - name: linux-app
             image: myregistry/linux-app:latest
     ```

3. **Administración de DaemonSet:**
   - **Crear DaemonSets específicos por OS**:
     ```yaml
     # DaemonSet for Windows nodes
     apiVersion: apps/v1
     kind: DaemonSet
     metadata:
       name: windows-agent
     spec:
       selector:
         matchLabels:
           app: monitoring-agent
       template:
         metadata:
           labels:
             app: monitoring-agent
         spec:
           nodeSelector:
             kubernetes.io/os: windows
           containers:
           - name: agent
             image: myregistry/windows-agent:latest
     ```

4. **Administración de imágenes:**
   - **Usar imágenes multi-arquitectura**: Admitir varios OS/arquitecturas con el mismo tag
   - **Usar tags de imagen específicos por OS**: `myapp:linux` y `myapp:windows`
   - **Establecer image pull policy**: `imagePullPolicy: Always`

5. **Resource Requests and Limits:**
   - **Establecer recursos adecuados para cada OS**:
     ```yaml
     resources:
       requests:
         memory: "2Gi"  # Windows containers typically need more memory
         cpu: "500m"
       limits:
         memory: "4Gi"
         cpu: "1"
     ```

6. **Networking:**
   - **Seleccionar plugin CNI compatible**: Flannel, Calico, Antrea, etc.
   - **Considerar el OS al aplicar network policies**:
     ```yaml
     apiVersion: networking.k8s.io/v1
     kind: NetworkPolicy
     metadata:
       name: allow-specific-traffic
     spec:
       podSelector:
         matchLabels:
           app: myapp
       ingress:
       - from:
         - podSelector:
             matchLabels:
               app: frontend
     ```

7. **Almacenamiento:**
   - **Usar storage classes compatibles con OS**:
     ```yaml
     apiVersion: v1
     kind: PersistentVolumeClaim
     metadata:
       name: windows-pvc
     spec:
       storageClassName: windows-storage  # Windows node compatible storage class
       accessModes:
         - ReadWriteOnce
       resources:
         requests:
           storage: 10Gi
     ```

8. **Security Context:**
   - **Aplicar ajustes de seguridad adecuados para cada OS**:
     ```yaml
     # Security context for Linux pods
     securityContext:
       runAsUser: 1000
       runAsGroup: 3000
       fsGroup: 2000

     # Windows pods ignore the above settings and use different security mechanisms
     ```

9. **Monitoreo y logging:**
   - **Desplegar agentes de monitoreo específicos por OS**
   - **Ajustar rutas de recolección de logs**: Windows (`C:\k\logs`) vs Linux (`/var/log`)

10. **Pipelines CI/CD:**
    - **Configurar pipelines de build y pruebas específicos por OS**
    - **Establecer estrategia de deployment multi-OS**
</details>

3. Explica cómo usar Group Managed Service Accounts (gMSA) en Windows containers y sus beneficios.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:**

**Descripción general de Group Managed Service Accounts (gMSA):**

Group Managed Service Accounts (gMSA) son un tipo especial de cuenta de Active Directory para autenticación de services en entornos de dominio de Windows. Usar gMSA en Windows containers en Kubernetes permite ejecutar aplicaciones que requieren autenticación de dominio, y es particularmente útil en los siguientes escenarios:

- Aplicaciones .NET que requieren integración con Active Directory
- Conexiones a SQL Server usando autenticación de Windows
- Services que requieren autenticación Kerberos
- Aplicaciones que necesitan acceder a recursos de dominio

**Cómo usar gMSA en Windows containers:**

1. **Requisitos previos:**
   - Controlador de dominio de Active Directory
   - Windows nodes deben estar unidos al dominio
   - Kubernetes versión 1.14 o posterior
   - Container runtime containerd o Docker

2. **Configurar gMSA en Active Directory:**
   ```powershell
   # 1. Create KDS root key (run on domain controller)
   Add-KdsRootKey -EffectiveTime (Get-Date).AddHours(-10)

   # 2. Create gMSA account
   New-ADServiceAccount -Name "gmsa-k8s" -DnsHostName "gmsa-k8s.example.com" -ServicePrincipalNames "host/gmsa-k8s", "host/gmsa-k8s.example.com" -PrincipalsAllowedToRetrieveManagedPassword "Domain Computers"
   ```

3. **Crear gMSA Credential Spec:**
   ```yaml
   apiVersion: windows.k8s.io/v1
   kind: GMSACredentialSpec
   metadata:
     name: gmsa-k8s-credspec
   credspec:
     ActiveDirectoryConfig:
       GroupManagedServiceAccounts:
       - Name: gmsa-k8s
         Scope: EXAMPLE
     CmsPlugins:
     - ActiveDirectory
     DomainJoinConfig:
       DnsName: example.com
       DnsTreeName: example.com
       Guid: 12345678-1234-1234-1234-123456789012
       MachineAccountName: gmsa-k8s
       NetBiosName: EXAMPLE
   ```

4. **Almacenar Credential Spec como Kubernetes Secret:**
   ```bash
   kubectl create secret generic gmsa-k8s-secret --from-file=credspec.json=/path/to/gmsa-credspec.json
   ```

5. **Agregar configuración gMSA a la definición del Pod:**
   ```yaml
   apiVersion: v1
   kind: Pod
   metadata:
     name: iis-gmsa
     labels:
       app: iis-gmsa
   spec:
     securityContext:
       windowsOptions:
         gmsaCredentialSpecName: gmsa-k8s-credspec
     nodeSelector:
       kubernetes.io/os: windows
     containers:
     - name: iis
       image: mcr.microsoft.com/windows/servercore/iis:windowsservercore-ltsc2019
       ports:
       - containerPort: 80
   ```

6. **Verificar uso de gMSA:**
   ```powershell
   # Run inside container
   whoami
   # Output: EXAMPLE\gmsa-k8s$

   nltest /sc_verify:example.com
   # Output: Trusted DC connections... Passed
   ```

**Beneficios de usar gMSA:**

1. **Seguridad mejorada:**
   - Elimina credenciales hardcodeadas dentro de containers
   - Administración y rotación automática de contraseñas
   - Permite aplicar el principio de mínimo privilegio

2. **Integración con Active Directory:**
   - Permite containerizar aplicaciones existentes que usan autenticación de Windows
   - Admite autenticación Kerberos y NTLM
   - Acceso fluido a recursos de dominio

3. **Administración centralizada de identidad:**
   - Administración unificada de identidad mediante Active Directory
   - Se pueden aplicar políticas de grupo
   - Auditoría y cumplimiento mejorados

4. **Compatibilidad de aplicaciones:**
   - Admite aplicaciones .NET legacy que requieren autenticación de dominio
   - Admite conexiones a SQL Server usando autenticación integrada de Windows
   - Admite autenticación de Windows para aplicaciones web IIS

5. **Operaciones simplificadas:**
   - Administración automatizada de credenciales
   - Las credenciales persisten entre reinicios de containers
   - La misma identidad puede compartirse entre múltiples containers

**Consideraciones al usar gMSA:**

1. **Requisitos de red:**
   - Se requiere conectividad de red desde Windows nodes hacia controladores de dominio
   - Se requiere configuración DNS adecuada
   - Los puertos requeridos deben estar abiertos (Kerberos, LDAP, etc.)

2. **Administración de permisos:**
   - Otorgar solo los permisos mínimos requeridos a gMSA
   - Configurar membresías de grupos adecuadas
   - Revisiones regulares de permisos

3. **Escalabilidad:**
   - Considerar la carga del controlador de dominio en clusters grandes
   - Usar múltiples cuentas gMSA para separación de permisos

4. **Solución de problemas:**
   - Depurar problemas de conectividad de dominio
   - Verificar errores de configuración de credential spec
   - Revisar logs del container runtime
</details>

4. Explica cómo configurar logging y monitoreo para Windows nodes en Kubernetes y las diferencias respecto a Linux nodes.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:**

**Configuración de logging y monitoreo para Windows nodes:**

**1. Configuración de logging:**

**Principales fuentes de logging para Windows nodes:**
- Windows Event Logs (System, Application, Security)
- Eventos ETW (Event Tracing for Windows)
- Archivos de log de aplicaciones (normalmente dentro de la unidad `C:\`)
- Logs de kubelet y container runtime (normalmente `C:\k\logs` o rutas similares)

**Métodos para configurar logging de Windows nodes:**

1. **Configuración de Fluent Bit o Fluentd:**
   ```yaml
   apiVersion: apps/v1
   kind: DaemonSet
   metadata:
     name: fluent-bit-windows
     namespace: logging
   spec:
     selector:
       matchLabels:
         app: fluent-bit-windows
     template:
       metadata:
         labels:
           app: fluent-bit-windows
       spec:
         nodeSelector:
           kubernetes.io/os: windows
         containers:
         - name: fluent-bit
           image: fluent/fluent-bit:windows-latest
           volumeMounts:
           - name: config
             mountPath: C:/fluent-bit/conf/
           - name: windows-logs
             mountPath: C:/Windows/System32/winevt/Logs
             readOnly: true
         volumes:
         - name: config
           configMap:
             name: fluent-bit-windows-config
         - name: windows-logs
           hostPath:
             path: C:/Windows/System32/winevt/Logs
   ```

2. **Configuración de recolección de Windows Event Log:**
   ```ini
   # Fluent Bit Windows configuration
   [INPUT]
       Name            winlog
       Channels        System,Application,Security
       Interval_Sec    1
       DB              C:\\fluent-bit\\winlog.db

   [OUTPUT]
       Name            elasticsearch
       Match           *
       Host            elasticsearch-master
       Port            9200
       Index           windows_logs
       Type            _doc
   ```

3. **Recolección de logs de containers:**
   - Ruta de logs de containerd: `C:\ProgramData\containerd\root\containers`
   - Ruta de logs de kubelet: `C:\k\logs` o Windows Event Log

**2. Configuración de monitoreo:**

**Principales métricas para monitoreo de Windows nodes:**
- Uso de CPU, memoria y disco
- Tráfico de red
- Conteo de procesos
- Uso del page file
- Uso de recursos de containers

**Métodos para configurar monitoreo de Windows nodes:**

1. **Configuración de Prometheus Windows Exporter:**
   ```yaml
   apiVersion: apps/v1
   kind: DaemonSet
   metadata:
     name: windows-exporter
     namespace: monitoring
   spec:
     selector:
       matchLabels:
         app: windows-exporter
     template:
       metadata:
         labels:
           app: windows-exporter
       spec:
         nodeSelector:
           kubernetes.io/os: windows
         containers:
         - name: windows-exporter
           image: prometheuscommunity/windows-exporter:latest
           args:
           - --collectors.enabled=cpu,memory,disk,net,service,os,system,container
           ports:
           - containerPort: 9182
             name: metrics
             protocol: TCP
   ```

2. **Configuración de scraping de Prometheus:**
   ```yaml
   apiVersion: monitoring.coreos.com/v1
   kind: ServiceMonitor
   metadata:
     name: windows-exporter
     namespace: monitoring
   spec:
     selector:
       matchLabels:
         app: windows-exporter
     endpoints:
     - port: metrics
       interval: 30s
   ```

3. **Configuración de dashboard de Grafana:**
   - Crear dashboards dedicados para métricas de Windows nodes
   - Agregar paneles específicos de Windows (por ejemplo, uso de page file, estado de services, etc.)

**3. Herramientas de troubleshooting:**

**Herramientas para troubleshooting de Windows nodes:**
- Comandos de PowerShell (`Get-Process`, `Get-Service`, `Get-EventLog`)
- Windows Performance Monitor (PerfMon)
- Event Viewer
- Comando `kubectl debug` (soporte limitado en Windows nodes)

**Ejemplos de troubleshooting de Windows nodes:**
```powershell
# Check kubelet logs
Get-EventLog -LogName Application -Source kubelet -Newest 50

# Check containerd status
Get-Service containerd

# Verify network connectivity
Test-NetConnection -ComputerName api.kubernetes.cluster -Port 443
```

**Diferencias clave respecto a Linux nodes:**

1. **Ubicación de almacenamiento de logs:**
   - **Linux**: Se almacenan como archivos de texto en el directorio `/var/log/`
   - **Windows**: Windows Event Logs (formato binario) y archivos de texto en varias ubicaciones

2. **Mecanismo de recolección de logs:**
   - **Linux**: La recolección de logs basada en archivos es típica (tail, read)
   - **Windows**: Requiere recolección mediante Windows Event Log API

3. **Recolección de métricas:**
   - **Linux**: Recolecta métricas desde los sistemas de archivos `/proc`, `/sys`
   - **Windows**: Usa WMI (Windows Management Instrumentation) o Performance Counter API

4. **Logs de containers:**
   - **Linux**: La salida estándar/error se redirige a archivos
   - **Windows**: ETW o logging basado en archivos, estructura de rutas diferente

5. **Monitoreo de recursos:**
   - **Linux**: Monitoreo del uso de recursos de containers mediante cgroups
   - **Windows**: Monitoreo de recursos mediante Job Objects, algunas métricas se calculan de forma diferente

6. **Agentes de monitoreo:**
   - **Linux**: Soporte para varios agentes (node-exporter, cAdvisor, etc.)
   - **Windows**: Soporte limitado de agentes, se requieren agentes específicos de Windows

7. **Herramientas de depuración:**
   - **Linux**: Varias herramientas CLI (ps, top, netstat, strace, etc.)
   - **Windows**: Comandos de PowerShell, herramientas GUI, herramientas CLI limitadas

**Mejores prácticas:**

1. **Solución integrada de logging:**
   - Usar stack EFK (Elasticsearch, Fluent Bit, Kibana) o ELK
   - Configuraciones separadas para Windows y Linux nodes

2. **Solución integrada de monitoreo:**
   - Monitorear todos los nodes con Prometheus + Grafana
   - Crear dashboards específicos por OS

3. **Configuración de alertas:**
   - Configurar reglas de alerta para eventos específicos de Windows
   - Monitorear el estado de services críticos de Windows

4. **Política de retención de logs:**
   - Configurar tamaño y período de retención de Windows event logs
   - Configurar política de rotación de logs

5. **Monitoreo de seguridad:**
   - Recolectar y analizar logs de eventos de seguridad de Windows
   - Monitorear cambios de permisos e intentos de inicio de sesión
</details>

5. Explica las opciones de almacenamiento y los métodos de configuración de volume mount para Windows containers en Kubernetes.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:**

**Opciones de almacenamiento para Windows containers:**

**1. Tipos básicos de volúmenes:**

1. **emptyDir:**
   - Almacena datos temporales durante la vida del pod
   - Se crea en el volumen NTFS local del Windows node
   - Los datos se eliminan cuando se elimina el pod

   ```yaml
   volumes:
   - name: temp-data
     emptyDir: {}
   ```

2. **hostPath:**
   - Acceso directo al sistema de archivos del Windows node
   - Debe usar formato de rutas de Windows (escapar barras invertidas)
   - Los datos no se pueden compartir entre nodes

   ```yaml
   volumes:
   - name: logs
     hostPath:
       path: C:\\Logs
       type: DirectoryOrCreate
   ```

3. **configMap y secret:**
   - Almacenan datos de configuración e información sensible
   - Funcionan de la misma manera para Windows containers
   - La configuración de permisos de archivo se aplica de forma diferente en Windows

   ```yaml
   volumes:
   - name: config
     configMap:
       name: app-config
   ```

4. **persistentVolumeClaim (PVC):**
   - Solicita almacenamiento persistente
   - Requiere una storage class compatible con Windows
   - Es necesario verificar el soporte del CSI driver

   ```yaml
   volumes:
   - name: data
     persistentVolumeClaim:
       claimName: windows-pvc
   ```

**2. Soluciones de almacenamiento compatibles con Windows containers:**

1. **Azure Disk/File (AKS):**
   - Azure Kubernetes Service admite Windows nodes
   - Puede usar Azure Files basado en protocolo SMB
   - Azure Disk CSI driver compatible

   ```yaml
   # Azure File PVC
   apiVersion: v1
   kind: PersistentVolumeClaim
   metadata:
     name: azure-file-pvc
   spec:
     accessModes:
     - ReadWriteMany
     storageClassName: azurefile-csi
     resources:
       requests:
         storage: 100Gi
   ```

2. **AWS EBS (EKS):**
   - Amazon EKS admite Windows nodes
   - EBS CSI driver disponible
   - Acceso limitado dentro de una sola AZ

   ```yaml
   # AWS EBS PVC
   apiVersion: v1
   kind: PersistentVolumeClaim
   metadata:
     name: ebs-windows-pvc
   spec:
     accessModes:
     - ReadWriteOnce
     storageClassName: ebs-sc
     resources:
       requests:
         storage: 50Gi
   ```

3. **Volúmenes SMB/CIFS:**
   - Sistema de archivos de red adecuado para entornos Windows
   - Requiere FlexVolume o CSI driver
   - Admite acceso ReadWriteMany en múltiples pods

   ```yaml
   # SMB CSI driver example
   apiVersion: v1
   kind: PersistentVolumeClaim
   metadata:
     name: smb-windows-pvc
   spec:
     accessModes:
     - ReadWriteMany
     storageClassName: smb-csi
     resources:
       requests:
         storage: 100Gi
   ```

4. **iSCSI:**
   - Requiere configuración del iniciador iSCSI en Windows node
   - Proporciona acceso a almacenamiento de bloques
   - Adecuado para requisitos de alto rendimiento

   ```yaml
   # iSCSI PV example
   apiVersion: v1
   kind: PersistentVolume
   metadata:
     name: iscsi-windows-pv
   spec:
     capacity:
       storage: 100Gi
     accessModes:
     - ReadWriteOnce
     persistentVolumeReclaimPolicy: Retain
     iscsi:
       targetPortal: 192.168.1.10:3260
       iqn: iqn.2000-01.com.example:storage.kube.sys1.xyz
       lun: 0
       fsType: ntfs
       readOnly: false
   ```

**3. Configuración de volume mounts para Windows containers:**

1. **Rutas de volume mount:**
   - Windows containers usan formato de rutas de Windows
   - Normalmente se usan rutas dentro de la unidad `C:\`
   - Las barras invertidas en las rutas necesitan escaparse en YAML

   ```yaml
   volumeMounts:
   - name: data
     mountPath: C:\\data
   ```

2. **Mounts de solo lectura:**
   - Compatibles con Windows containers
   - Se aplican mediante permisos NTFS

   ```yaml
   volumeMounts:
   - name: config
     mountPath: C:\\config
     readOnly: true
   ```

3. **Mounts de subpath:**
   - Pueden montar solo subpaths específicos de volúmenes
   - Ten en cuenta los separadores de rutas de Windows

   ```yaml
   volumeMounts:
   - name: shared-data
     mountPath: C:\\app\\logs
     subPath: logs
   ```

**4. Ejemplos de configuración de almacenamiento de Windows containers:**

1. **Configuración de aplicación web:**
   ```yaml
   apiVersion: v1
   kind: Pod
   metadata:
     name: windows-web-app
   spec:
     nodeSelector:
       kubernetes.io/os: windows
     containers:
     - name: web
       image: mcr.microsoft.com/windows/servercore/iis:windowsservercore-ltsc2019
       volumeMounts:
       - name: website
         mountPath: C:\\inetpub\\wwwroot
       - name: logs
         mountPath: C:\\inetpub\\logs
       - name: config
         mountPath: C:\\config
         readOnly: true
     volumes:
     - name: website
       persistentVolumeClaim:
         claimName: website-content-pvc
     - name: logs
       emptyDir: {}
     - name: config
       configMap:
         name: web-config
   ```

2. **Configuración de base de datos:**
   ```yaml
   apiVersion: v1
   kind: Pod
   metadata:
     name: windows-sql
   spec:
     nodeSelector:
       kubernetes.io/os: windows
     containers:
     - name: sql
       image: mcr.microsoft.com/mssql/server:2019-latest
       env:
       - name: ACCEPT_EULA
         value: "Y"
       - name: SA_PASSWORD
         valueFrom:
           secretKeyRef:
             name: sql-credentials
             key: sa-password
       volumeMounts:
       - name: data
         mountPath: C:\\var\\opt\\mssql\\data
       - name: backup
         mountPath: C:\\var\\opt\\mssql\\backup
     volumes:
     - name: data
       persistentVolumeClaim:
         claimName: sql-data-pvc
     - name: backup
       persistentVolumeClaim:
         claimName: sql-backup-pvc
   ```

**5. Consideraciones al usar almacenamiento de Windows containers:**

1. **Separadores de ruta:**
   - Windows usa barras invertidas (`\`) pero se necesita escaparlas en YAML
   - Alternativamente, se pueden usar barras (`/`), pero verifica la compatibilidad de la aplicación

2. **Permisos de archivo:**
   - Windows usa el modelo de permisos NTFS
   - No se pueden establecer permisos como chmod/chown en Linux
   - Los permisos dentro de containers están determinados por el contexto de usuario del container

3. **Consideraciones de rendimiento:**
   - El almacenamiento de red (SMB/CIFS) puede tener latencia
   - Se recomienda almacenamiento local o almacenamiento de bloques conectado directamente para requisitos de alto rendimiento

4. **Compatibilidad de Storage Class:**
   - Verificar storage classes compatibles con Windows nodes
   - Verificar soporte de Windows de CSI drivers

5. **Backup y recuperación:**
   - Considerar la integración con Windows Volume Shadow Copy Service (VSS)
   - Implementar mecanismos de backup consistentes con la aplicación
</details>

## Preguntas prácticas

1. Escribe un manifiesto Deployment que cumpla los siguientes requisitos para un cluster de Kubernetes con Windows y Linux nodes mezclados:
   - Nombre de la aplicación: web-app
   - Imagen de Windows container: mcr.microsoft.com/windows/servercore/iis:windowsservercore-ltsc2019
   - Replicas: 2
   - Puerto: 80
   - Variable de entorno: WEBSITE_NAME=MyWindowsApp
   - Volumen: montar ConfigMap "web-config" en C:\inetpub\wwwroot\web.config

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:**

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-app
  labels:
    app: web-app
spec:
  replicas: 2
  selector:
    matchLabels:
      app: web-app
  template:
    metadata:
      labels:
        app: web-app
    spec:
      nodeSelector:
        kubernetes.io/os: windows
      containers:
      - name: iis
        image: mcr.microsoft.com/windows/servercore/iis:windowsservercore-ltsc2019
        ports:
        - containerPort: 80
        env:
        - name: WEBSITE_NAME
          value: "MyWindowsApp"
        volumeMounts:
        - name: config-volume
          mountPath: C:\inetpub\wwwroot\web.config
          subPath: web.config
      volumes:
      - name: config-volume
        configMap:
          name: web-config
---
apiVersion: v1
kind: Service
metadata:
  name: web-app
spec:
  selector:
    app: web-app
  ports:
  - port: 80
    targetPort: 80
  type: ClusterIP
```

**Explicación:**

1. **Recurso Deployment**:
   - Usa `nodeSelector` para especificar scheduling solo a Windows nodes
   - Establece 2 replicas según lo requerido
   - Usa la imagen del servidor web IIS

2. **Configuración del container**:
   - Expone el puerto 80
   - Establece la variable de entorno `WEBSITE_NAME`
   - Monta ConfigMap en una ruta de archivo específica (usando formato de ruta de Windows)

3. **Configuración de volumen**:
   - Monta ConfigMap como volumen
   - Usa `subPath` para montar una clave específica de ConfigMap como archivo

4. **Definición de Service**:
   - Crea un service ClusterIP para acceder a la aplicación
   - Accesible mediante el puerto 80

**Notas**:
- En rutas de Windows, las barras invertidas (`\`) se tratan como caracteres de escape en YAML, así que ten cuidado. Este ejemplo usa barras invertidas normales, pero para rutas más complejas, se pueden usar barras invertidas dobles (`\\`) o barras (`/`).
- Windows containers pueden tener requisitos de recursos mayores que Linux containers, por lo que es buena práctica establecer resource requests and limits adecuados en entornos de producción.
</details>

2. Escribe manifiestos DaemonSet para desplegar agentes de monitoreo que se ejecuten tanto en Windows como en Linux nodes. Cada OS debe usar imágenes y configuraciones adecuadas.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:**

```yaml
# DaemonSet for Linux nodes
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: monitoring-agent-linux
  namespace: monitoring
  labels:
    app: monitoring-agent
    os: linux
spec:
  selector:
    matchLabels:
      app: monitoring-agent
      os: linux
  template:
    metadata:
      labels:
        app: monitoring-agent
        os: linux
    spec:
      nodeSelector:
        kubernetes.io/os: linux
      containers:
      - name: agent
        image: prom/node-exporter:latest
        ports:
        - containerPort: 9100
          name: metrics
        volumeMounts:
        - name: proc
          mountPath: /host/proc
          readOnly: true
        - name: sys
          mountPath: /host/sys
          readOnly: true
        - name: root
          mountPath: /host/root
          readOnly: true
        args:
        - --path.procfs=/host/proc
        - --path.sysfs=/host/sys
        - --path.rootfs=/host/root
        securityContext:
          runAsNonRoot: true
          runAsUser: 65534
      volumes:
      - name: proc
        hostPath:
          path: /proc
      - name: sys
        hostPath:
          path: /sys
      - name: root
        hostPath:
          path: /
---
# DaemonSet for Windows nodes
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: monitoring-agent-windows
  namespace: monitoring
  labels:
    app: monitoring-agent
    os: windows
spec:
  selector:
    matchLabels:
      app: monitoring-agent
      os: windows
  template:
    metadata:
      labels:
        app: monitoring-agent
        os: windows
    spec:
      nodeSelector:
        kubernetes.io/os: windows
      containers:
      - name: agent
        image: prometheuscommunity/windows-exporter:latest
        ports:
        - containerPort: 9182
          name: metrics
        args:
        - --collectors.enabled=cpu,memory,disk,net,service,os,system,container
---
# Service for monitoring agents
apiVersion: v1
kind: Service
metadata:
  name: monitoring-agent
  namespace: monitoring
  labels:
    app: monitoring-agent
spec:
  type: ClusterIP
  ports:
  - name: linux-metrics
    port: 9100
    targetPort: 9100
    protocol: TCP
  - name: windows-metrics
    port: 9182
    targetPort: 9182
    protocol: TCP
  selector:
    app: monitoring-agent
```

**Explicación:**

1. **DaemonSet para Linux Nodes**:
   - Usa `nodeSelector` para programar solo en Linux nodes
   - Usa la imagen Prometheus Node Exporter
   - Monta los directorios `/proc`, `/sys`, `/` del host para recolectar métricas del sistema
   - Security context configurado para ejecutarse como usuario no root

2. **DaemonSet para Windows Nodes**:
   - Usa `nodeSelector` para programar solo en Windows nodes
   - Usa la imagen Windows Exporter
   - Especifica los colectores de métricas que se deben recolectar
   - Se aplica configuración específica de Windows

3. **Service común**:
   - Crea un service que selecciona pods de ambos DaemonSets
   - Expone tanto los puertos de métricas de Linux como de Windows
   - Prometheus puede hacer scrape de métricas mediante este service

**Notas**:
- Es importante usar imágenes y configuraciones adecuadas para cada OS.
- Como los métodos de recolección de métricas difieren entre Linux y Windows nodes, se separan en DaemonSets diferentes.
- Usar labels para distinguir tipos de OS es útil para filtrar y visualizar métricas en el sistema de monitoreo.
- En entornos de producción, se necesita configuración adicional de resource requests and limits, security contexts, service accounts, etc.
</details>

3. Escribe un manifiesto pod para desplegar una aplicación .NET que usa autenticación de Active Directory en un Windows container. Se deben usar Group Managed Service Accounts (gMSA).

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:**

```yaml
# Secret for gMSA credential spec
apiVersion: v1
kind: Secret
metadata:
  name: gmsa-credential-spec
  namespace: default
type: Opaque
data:
  credspec.json: BASE64_ENCODED_CREDENTIAL_SPEC_HERE
---
# Windows pod using gMSA
apiVersion: v1
kind: Pod
metadata:
  name: ad-auth-app
  labels:
    app: ad-auth-app
spec:
  nodeSelector:
    kubernetes.io/os: windows
  securityContext:
    windowsOptions:
      gmsaCredentialSpecName: gmsa-credential-spec
  containers:
  - name: dotnet-app
    image: myregistry/ad-auth-app:latest
    ports:
    - containerPort: 80
    env:
    - name: ASPNETCORE_ENVIRONMENT
      value: "Production"
    volumeMounts:
    - name: app-config
      mountPath: C:\app\appsettings.json
      subPath: appsettings.json
    resources:
      requests:
        memory: "2Gi"
        cpu: "500m"
      limits:
        memory: "4Gi"
        cpu: "1000m"
  volumes:
  - name: app-config
    configMap:
      name: ad-auth-app-config
---
# ConfigMap for application configuration
apiVersion: v1
kind: ConfigMap
metadata:
  name: ad-auth-app-config
data:
  appsettings.json: |
    {
      "Logging": {
        "LogLevel": {
          "Default": "Information",
          "Microsoft": "Warning"
        }
      },
      "ConnectionStrings": {
        "DefaultConnection": "Server=sql-server;Database=AppDB;Integrated Security=True;"
      },
      "ActiveDirectory": {
        "Domain": "example.com",
        "UseWindowsAuthentication": true
      }
    }
---
# Service definition
apiVersion: v1
kind: Service
metadata:
  name: ad-auth-app
spec:
  selector:
    app: ad-auth-app
  ports:
  - port: 80
    targetPort: 80
  type: ClusterIP
```

**Explicación:**

1. **Secret de gMSA Credential Spec**:
   - Active Directory gMSA credential spec se codifica en Base64 y se almacena como secret
   - Los pods usan este secret para autenticación de dominio

2. **Configuración de Windows Pod**:
   - Usa `nodeSelector` para programar en Windows nodes
   - Referencia gMSA credential spec usando `securityContext.windowsOptions.gmsaCredentialSpecName`
   - Usa imagen de aplicación .NET
   - Se establecen resource requests and limits adecuados

3. **Volúmenes y configuración**:
   - Proporciona ajustes de aplicación usando ConfigMap
   - Archivo de configuración montado usando formato de ruta de Windows
   - Incluye cadena de conexión de SQL Server usando autenticación integrada de Windows

4. **Definición de Service**:
   - Crea un service ClusterIP para acceder a la aplicación

**Requisitos previos para la configuración de gMSA:**

1. **Configuración del controlador de dominio de Active Directory:**
   ```powershell
   # Create KDS root key (run on domain controller)
   Add-KdsRootKey -EffectiveTime (Get-Date).AddHours(-10)

   # Create gMSA account
   New-ADServiceAccount -Name "k8s-gmsa" -DnsHostName "k8s-gmsa.example.com" -ServicePrincipalNames "host/k8s-gmsa", "host/k8s-gmsa.example.com" -PrincipalsAllowedToRetrieveManagedPassword "Domain Computers"
   ```

2. **Crear Credential Spec:**
   ```powershell
   # Run on Windows node
   Import-Module ActiveDirectory
   $CredSpec = New-CimInstance -Namespace root/Microsoft/Windows/CredentialSpecification -ClassName Win32_CredentialSpecification -Property @{Name = "k8s-gmsa"; ActiveDirectoryCredentialSpec = Get-CredentialSpec -Name k8s-gmsa -Json}

   # Verify credential spec contents
   Get-CredentialSpec -Name k8s-gmsa -Json
   ```

3. **Convertir Credential Spec a Kubernetes Secret:**
   ```bash
   # Base64 encode credential spec JSON
   cat credspec.json | base64 -w 0

   # Add encoded value to secret YAML
   ```

**Notas**:
- Windows nodes deben estar unidos al dominio de Active Directory.
- containerd o Docker debe configurarse para admitir gMSA.
- En entornos reales, el contenido de credential spec debe administrarse de forma segura.
- La aplicación debe configurarse para usar correctamente la autenticación de Windows.
</details>

4. Escribe manifiestos NetworkPolicy que cumplan los siguientes requisitos en un cluster con Windows y Linux nodes mezclados:
   - Windows web application pods (label: app=windows-web) solo pueden acceder a Linux database pods (label: app=linux-db)
   - Database pods permiten acceso solo en el puerto 3306
   - Web application pods son accesibles desde el exterior en el puerto 80

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:**

```yaml
# NetworkPolicy for Windows web application
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: windows-web-policy
  namespace: default
spec:
  podSelector:
    matchLabels:
      app: windows-web
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - ports:
    - port: 80
      protocol: TCP
  egress:
  - to:
    - podSelector:
        matchLabels:
          app: linux-db
    ports:
    - port: 3306
      protocol: TCP
---
# NetworkPolicy for Linux database
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: linux-db-policy
  namespace: default
spec:
  podSelector:
    matchLabels:
      app: linux-db
  policyTypes:
  - Ingress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: windows-web
    ports:
    - port: 3306
      protocol: TCP
```

**Explicación:**

1. **NetworkPolicy de la aplicación web Windows**:
   - Se aplica a pods con label `app=windows-web`
   - **Regla Ingress**: Permite acceso desde todas las fuentes en el puerto 80
   - **Regla Egress**: Permite acceso solo al puerto 3306 en pods con label `app=linux-db`

2. **NetworkPolicy de la base de datos Linux**:
   - Se aplica a pods con label `app=linux-db`
   - **Regla Ingress**: Permite acceso solo desde pods con label `app=windows-web` en el puerto 3306

**Notas**:
- Las network policies requieren un plugin CNI que admita NetworkPolicy (por ejemplo, Calico, Antrea) para funcionar.
- El soporte de NetworkPolicy en Windows nodes puede variar según el plugin CNI.
- Este ejemplo asume el namespace default, pero en entornos reales se deben especificar los namespaces adecuados.
- En entornos de producción, pueden ser necesarias reglas egress adicionales para búsquedas DNS, acceso a services externos, etc.

**Ejemplos de Deployment:**

Windows web application pods:
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: windows-web
spec:
  replicas: 2
  selector:
    matchLabels:
      app: windows-web
  template:
    metadata:
      labels:
        app: windows-web
    spec:
      nodeSelector:
        kubernetes.io/os: windows
      containers:
      - name: web
        image: mcr.microsoft.com/windows/servercore/iis:windowsservercore-ltsc2019
        ports:
        - containerPort: 80
```

Linux database pods:
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: linux-db
spec:
  replicas: 1
  selector:
    matchLabels:
      app: linux-db
  template:
    metadata:
      labels:
        app: linux-db
    spec:
      nodeSelector:
        kubernetes.io/os: linux
      containers:
      - name: mysql
        image: mysql:8.0
        ports:
        - containerPort: 3306
        env:
        - name: MYSQL_ROOT_PASSWORD
          valueFrom:
            secretKeyRef:
              name: mysql-secret
              key: password
```
</details>

5. Escribe un manifiesto Deployment para una aplicación .NET Framework que se ejecute en Windows nodes. La aplicación requiere una cadena de conexión como variable de entorno para acceder a Azure Blob Storage. También configura un volumen persistente para logs.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:**

```yaml
# Secret for Azure Storage connection string
apiVersion: v1
kind: Secret
metadata:
  name: azure-storage-secret
type: Opaque
data:
  connection-string: QWNjb3VudE5hbWU9bXlzdG9yYWdlYWNjb3VudDtBY2NvdW50S2V5PW15YWNjb3VudGtleTtFbmRwb2ludFN1ZmZpeD1jb3JlLndpbmRvd3MubmV0
---
# PersistentVolumeClaim for logs
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: windows-logs-pvc
spec:
  accessModes:
    - ReadWriteOnce
  storageClassName: managed-premium  # Azure Disk storage class example
  resources:
    requests:
      storage: 10Gi
---
# .NET Framework application Deployment
apiVersion: apps/v1
kind: Deployment
metadata:
  name: dotnet-framework-app
  labels:
    app: dotnet-framework-app
spec:
  replicas: 2
  selector:
    matchLabels:
      app: dotnet-framework-app
  template:
    metadata:
      labels:
        app: dotnet-framework-app
    spec:
      nodeSelector:
        kubernetes.io/os: windows
      containers:
      - name: dotnet-app
        image: myregistry/dotnet-framework-app:latest
        ports:
        - containerPort: 80
        env:
        - name: AZURE_STORAGE_CONNECTION_STRING
          valueFrom:
            secretKeyRef:
              name: azure-storage-secret
              key: connection-string
        - name: LOG_LEVEL
          value: "Information"
        - name: ASPNET_ENVIRONMENT
          value: "Production"
        volumeMounts:
        - name: logs-volume
          mountPath: C:\app\logs
        - name: config-volume
          mountPath: C:\app\web.config
          subPath: web.config
        resources:
          requests:
            memory: "2Gi"
            cpu: "500m"
          limits:
            memory: "4Gi"
            cpu: "1000m"
        readinessProbe:
          httpGet:
            path: /health
            port: 80
          initialDelaySeconds: 30
          periodSeconds: 10
        livenessProbe:
          httpGet:
            path: /health
            port: 80
          initialDelaySeconds: 60
          periodSeconds: 15
      volumes:
      - name: logs-volume
        persistentVolumeClaim:
          claimName: windows-logs-pvc
      - name: config-volume
        configMap:
          name: dotnet-app-config
---
# ConfigMap for application configuration
apiVersion: v1
kind: ConfigMap
metadata:
  name: dotnet-app-config
data:
  web.config: |
    <?xml version="1.0" encoding="utf-8"?>
    <configuration>
      <system.web>
        <compilation debug="false" targetFramework="4.8" />
        <httpRuntime targetFramework="4.8" />
      </system.web>
      <system.webServer>
        <handlers>
          <remove name="ExtensionlessUrlHandler-Integrated-4.0" />
          <add name="ExtensionlessUrlHandler-Integrated-4.0" path="*." verb="*" type="System.Web.Handlers.TransferRequestHandler" preCondition="integratedMode,runtimeVersionv4.0" />
        </handlers>
      </system.webServer>
      <appSettings>
        <add key="BlobContainerName" value="appdata" />
        <add key="LogDirectory" value="C:\app\logs" />
      </appSettings>
    </configuration>
---
# Service definition
apiVersion: v1
kind: Service
metadata:
  name: dotnet-framework-app
spec:
  selector:
    app: dotnet-framework-app
  ports:
  - port: 80
    targetPort: 80
  type: ClusterIP
```

**Explicación:**

1. **Configuración de Secret**:
   - La cadena de conexión de Azure Storage se codifica en Base64 y se almacena como secret
   - La aplicación puede acceder a ella de forma segura como variable de entorno

2. **PersistentVolumeClaim**:
   - Solicita 10GB de almacenamiento persistente para archivos de log
   - Usa Azure Disk storage class (ajustar para tu entorno)
   - Usa modo de acceso ReadWriteOnce

3. **Configuración de Deployment**:
   - Usa `nodeSelector` para programar solo en Windows nodes
   - Usa imagen de aplicación .NET Framework
   - Proporciona la cadena de conexión de Azure Storage mediante variables de entorno
   - Monta volumen persistente para el directorio de logs
   - Monta el archivo web.config desde ConfigMap
   - Se establecen resource requests and limits adecuados
   - Readiness y liveness probes configurados para health checking

4. **Configuración de ConfigMap**:
   - Proporciona archivo web.config para la aplicación .NET Framework
   - Incluye ajustes y configuración de la aplicación

5. **Definición de Service**:
   - Crea un service ClusterIP para acceder a la aplicación

**Notas**:
- En entornos reales, las direcciones del image registry, storage classes, requisitos de recursos, etc. deben ajustarse para tu entorno.
- Las aplicaciones .NET Framework deben usar imágenes basadas en Windows Server Core.
- En entornos de producción, el acceso externo puede configurarse mediante ingress controllers o load balancers.
- La información sensible, como las cadenas de conexión de Azure Storage, debe integrarse con sistemas externos de administración de secretos como Azure Key Vault.
</details>

## Temas avanzados

1. ¿Cuál es la configuración más importante al configurar containerd como container runtime para Windows nodes en Kubernetes?
   - A) configuración sandbox_image
   - B) Nivel de log y ruta de log
   - C) Límites de memoria y CPU sharing
   - D) Image pull policy y configuración del registry

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A) configuración sandbox_image**

**Explicación:**
La configuración más importante al configurar containerd como container runtime para Windows nodes en Kubernetes es la configuración `sandbox_image`. Esta configuración especifica la imagen que se usará como container de infraestructura del pod (pause container) en Windows nodes.

Por qué la configuración `sandbox_image` es importante para Windows nodes en la configuración de containerd:

1. **Pod Networking**: El pause container configura y mantiene el namespace de red para pods. Dado que Windows usa una stack de networking diferente a Linux, se requiere una imagen pause específica de Windows.

2. **Compatibilidad de OS**: Las imágenes pause de Linux no funcionan en Windows nodes, y las imágenes pause de Windows no funcionan en Linux nodes.

3. **Compatibilidad de versiones**: Debes seleccionar una imagen pause adecuada compatible con la versión de Windows (por ejemplo, Windows Server 2019, Windows Server 2022).

Ejemplo de configuración de containerd para Windows nodes:
```toml
[plugins."io.containerd.grpc.v1.cri".containerd]
  default_runtime_name = "microsoft/windows"

[plugins."io.containerd.grpc.v1.cri".containerd.runtimes."microsoft/windows"]
  runtime_type = "io.containerd.runhcs.v1"

[plugins."io.containerd.grpc.v1.cri"]
  sandbox_image = "mcr.microsoft.com/oss/kubernetes/pause:3.6-windows-ltsc2019"
```

Imágenes pause de Windows comúnmente usadas:
- Windows Server 2019 LTSC: `mcr.microsoft.com/oss/kubernetes/pause:3.6-windows-ltsc2019`
- Windows Server 2022: `mcr.microsoft.com/oss/kubernetes/pause:3.6-windows-ltsc2022`

Otras opciones también son importantes, pero `sandbox_image` es la más crítica:
- El nivel de log y la ruta de log son útiles para debugging, pero no son funcionalmente esenciales.
- Los límites de memoria y CPU sharing son importantes para performance tuning, pero no afectan la funcionalidad básica.
- Image pull policy y la configuración del registry son importantes para la administración de imágenes, pero no afectan la operación básica del container runtime.
</details>

2. ¿Cuál es el beneficio principal de usar el modo de aislamiento Hyper-V en Windows containers?
   - A) Mejor rendimiento y menor uso de recursos
   - B) Capacidad de ejecutar containers con versiones de Windows diferentes a las del host OS
   - C) Mayor velocidad de comunicación de red entre containers
   - D) Soporte para más API y funciones de Windows

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Capacidad de ejecutar containers con versiones de Windows diferentes a las del host OS**

**Explicación:**
El beneficio principal de usar el modo de aislamiento Hyper-V en Windows containers es la capacidad de ejecutar containers con versiones de Windows diferentes a las del host OS. Esta es una de las características importantes de Windows containers y es particularmente útil al ejecutar aplicaciones legacy en infraestructura moderna.

Beneficios principales del modo de aislamiento Hyper-V:

1. **Compatibilidad de versiones**:
   - Resuelve problemas de incompatibilidad de versiones entre host OS y container OS.
   - Por ejemplo, puedes ejecutar containers basados en Windows Server 2019 en un host Windows Server 2022.
   - Esto no es posible en modo de aislamiento de procesos (el aislamiento de procesos requiere que el host y el container usen la misma versión de kernel).

2. **Aislamiento de seguridad mejorado**:
   - Cada container se ejecuta en una máquina virtual ligera que proporciona un aislamiento más fuerte.
   - Se refuerzan los límites de seguridad entre containers y entre containers y el host.
   - Útil en entornos multi-tenant o al ejecutar código no confiable.

3. **Aislamiento a nivel de kernel**:
   - Cada container tiene su propia instancia del kernel de Windows.
   - Esto proporciona aislamiento a nivel de kernel, de modo que los problemas de kernel en un container no afectan a otros containers ni al host.

Para usar el modo de aislamiento Hyper-V en Kubernetes, agrega la siguiente annotation a la especificación del pod:
```yaml
apiVersion: v1
kind: Pod
metadata:
  name: iis-hyper-v
  annotations:
    io.kubernetes.cri-containerd.isolation: "hyperv"
spec:
  nodeSelector:
    kubernetes.io/os: windows
  containers:
  - name: iis
    image: mcr.microsoft.com/windows/servercore/iis:windowsservercore-ltsc2019
```

Desventajas del modo de aislamiento Hyper-V:
- Usa más recursos (memoria, CPU).
- Tiempo de inicio más largo.
- Requiere que la característica Hyper-V esté habilitada en el host.

Problemas con otras opciones:
- El aislamiento Hyper-V en realidad tiene menor rendimiento y mayor uso de recursos (A es incorrecta).
- La comunicación de red entre containers en realidad es más rápida en modo de aislamiento de procesos (C es incorrecta).
- El soporte de API y funciones de Windows depende de la versión del container OS; el aislamiento Hyper-V en sí no proporciona más API (D es incorrecta).
</details>

3. ¿Qué afirmación sobre pod networking al usar Windows nodes en Kubernetes es correcta?
   - A) Windows nodes no usan plugins CNI y usan su propia stack de networking
   - B) Windows nodes usan los mismos plugins CNI que Linux nodes, pero con configuración diferente
   - C) Windows nodes siempre deben usar el modo de red del host
   - D) Windows nodes no admiten redes overlay

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Windows nodes usan los mismos plugins CNI que Linux nodes, pero con configuración diferente**

**Explicación:**
Windows nodes en Kubernetes pueden usar los mismos plugins CNI (Container Network Interface) que Linux nodes, pero la configuración es diferente porque Windows tiene una stack de networking diferente. Esto permite un modelo de networking consistente en clusters de OS mixtos, considerando las características de cada OS.

Características de pod networking en Windows nodes:

1. **Soporte de plugins CNI**:
   - Windows nodes admiten varios plugins CNI, incluidos Flannel, Calico y Antrea.
   - Estos plugins están diseñados para funcionar tanto en Linux como en Windows nodes.
   - Cada plugin proporciona componentes o ajustes específicos de Windows.

2. **Modos de networking**:
   - Windows nodes generalmente admiten redes overlay (VXLAN, GENEVE, etc.).
   - Admiten varios modos de red, incluidos L2bridge, L2tunnel, overlay, etc.
   - El modo VXLAN de Flannel se usa ampliamente en Windows nodes.

3. **Diferencias de configuración**:
   - Windows nodes usan HNS (Host Network Service) para administrar la configuración de red.
   - Los métodos de creación y administración de network endpoints difieren de Linux.
   - Algunas funciones avanzadas de networking pueden estar limitadas en Windows.

Ejemplo - configuración de Flannel CNI:
```yaml
# Flannel ConfigMap for both Linux and Windows nodes
kind: ConfigMap
apiVersion: v1
metadata:
  name: kube-flannel-cfg
  namespace: kube-system
data:
  cni-conf.json: |
    {
      "name": "cbr0",
      "cniVersion": "0.3.1",
      "plugins": [
        {
          "type": "flannel",
          "delegate": {
            "hairpinMode": true,
            "isDefaultGateway": true
          }
        },
        {
          "type": "portmap",
          "capabilities": {
            "portMappings": true
          }
        }
      ]
    }
  net-conf.json: |
    {
      "Network": "10.244.0.0/16",
      "Backend": {
        "Type": "vxlan",
        "VNI": 4096,
        "Port": 4789
      }
    }
```

Puede ser necesaria configuración adicional en Windows nodes:
```powershell
# Script running on Windows nodes
$env:KUBE_NETWORK = "cbr0"
$networkName = "vxlan0"
$networkMode = "overlay"
```

Problemas con otras opciones:
- Windows nodes usan plugins CNI y no usan solo su propia stack de networking (A es incorrecta).
- Windows nodes no admiten el modo de red del host. `hostNetwork: true` no funciona para Windows pods (C es incorrecta).
- Windows nodes admiten redes overlay (VXLAN, etc.) (D es incorrecta).
</details>

4. ¿Qué afirmación sobre la administración de recursos en Windows nodes en Kubernetes es correcta?
   - A) Windows nodes no admiten límites de recursos
   - B) Windows nodes proporcionan límites de recursos más precisos que Linux nodes
   - C) Windows nodes implementan límites de recursos usando Job Objects
   - D) Windows nodes implementan límites de recursos usando cgroups

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Windows nodes implementan límites de recursos usando Job Objects**

**Explicación:**
Windows nodes en Kubernetes usan Job Objects, una característica del sistema operativo Windows, para implementar límites de recursos para containers. Esto contrasta con Linux nodes, que usan cgroups.

Características de la administración de recursos en Windows nodes:

1. **Job Objects**:
   - Windows usa Job Objects para limitar el uso de recursos de grupos de procesos.
   - Los container runtimes (containerd o Docker) usan la API de Job Objects para aplicar límites de CPU y memoria.
   - Job Objects pueden limitar el tiempo de CPU, uso de memoria, tiempo de trabajo, etc. para grupos de procesos.

2. **Límites de CPU**:
   - Los límites de CPU en Windows se implementan mediante un mecanismo de CPU sharing (weights).
   - Esto es similar al CPU sharing de Linux, pero se implementa de forma diferente.
   - Windows ajusta el CPU sharing según la cantidad de núcleos de CPU.

3. **Límites de memoria**:
   - Los límites de memoria para Windows containers se implementan mediante la característica de limitación de memoria de Job Objects.
   - Cuando los containers exceden los límites de memoria, se produce terminación OOM (Out of Memory).
   - La administración de memoria de Windows funciona de forma diferente a Linux, por lo que el comportamiento real puede diferir incluso con el mismo valor de límite de memoria.

4. **Configuración de resource requests and limits**:
   - Windows pods especifican resource requests and limits de la misma manera que Linux pods:
     ```yaml
     resources:
       requests:
         memory: "2Gi"
         cpu: "500m"
       limits:
         memory: "4Gi"
         cpu: "1"
     ```
   - kubelet pasa estos valores al Windows container runtime, y el runtime usa Job Objects para aplicar los límites.

5. **Monitoreo y reportes**:
   - kubelet monitorea el uso de recursos de containers usando contadores de rendimiento de Windows.
   - Esta información se puede ver mediante los comandos `kubectl top pods` y `kubectl top nodes`.
   - Metrics server recolecta esta información y la proporciona mediante la API de Kubernetes.

Consideraciones para la administración de recursos en Windows nodes:
- Windows containers generalmente usan más recursos predeterminados que Linux containers.
- La sobrecarga de memoria para Windows containers puede ser mayor, así que asegúrate de tener suficiente margen de memoria.
- El comportamiento exacto de los límites de recursos puede variar según la versión de Windows.

Problemas con otras opciones:
- Windows nodes admiten límites de recursos (A es incorrecta).
- Windows nodes generalmente proporcionan límites de recursos menos precisos que Linux nodes (B es incorrecta).
- Windows nodes usan Job Objects, no cgroups (D es incorrecta).
</details>

5. ¿Cuál de las siguientes NO es una mejor práctica de seguridad adecuada al usar Windows nodes en Kubernetes?
   - A) Escanear y actualizar regularmente las imágenes de containers para resolver vulnerabilidades de seguridad
   - B) Habilitar modo privilegiado para todos los Windows pods
   - C) Usar gMSA (Group Managed Service Accounts) para integración con Active Directory
   - D) Usar network policies para restringir la comunicación pod a pod

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Habilitar modo privilegiado para todos los Windows pods**

**Explicación:**
"Habilitar modo privilegiado para todos los Windows pods" NO es una mejor práctica de seguridad adecuada al usar Windows nodes en Kubernetes. De hecho, Windows containers no admiten modo privilegiado, e intentar configurarlo hará que falle la creación del pod.

Razones por las que esta opción es inapropiada:

1. **Modo privilegiado no compatible**:
   - Windows containers no admiten el concepto de modo privilegiado como Linux containers.
   - Windows tiene un modelo de seguridad diferente al de Linux y no tiene un mecanismo para otorgar privilegios a nivel de host a containers.

2. **Viola el principio de mínimo privilegio**:
   - Incluso si fuera compatible, habilitar modo privilegiado para todos los pods viola el principio de mínimo privilegio.
   - Cada workload debe tener solo los permisos mínimos necesarios.

3. **Mayor riesgo de seguridad**:
   - El modo privilegiado permite que containers accedan al sistema host, lo que aumenta considerablemente los riesgos de seguridad.
   - Si se produce una vulnerabilidad de escape de container, todo el sistema host podría quedar expuesto a riesgo.

Todas las demás opciones son mejores prácticas de seguridad adecuadas:

A) **Escanear y actualizar regularmente las imágenes de containers para resolver vulnerabilidades de seguridad**:
   - El escaneo de imágenes es importante para identificar y resolver vulnerabilidades conocidas.
   - Las imágenes de Windows deben recibir actualizaciones de seguridad periódicas.
   - Es buena práctica integrar herramientas de escaneo de imágenes en pipelines CI/CD.

C) **Usar gMSA (Group Managed Service Accounts) para integración con Active Directory**:
   - gMSA permite que Windows containers se autentiquen de forma segura contra services de Active Directory.
   - Usar gMSA en lugar de credenciales hardcodeadas mejora la seguridad.
   - Proporciona funcionalidad de administración y rotación automática de contraseñas.

D) **Usar network policies para restringir la comunicación pod a pod**:
   - Network policies aplican el principio de mínimo privilegio a la comunicación de red.
   - Restringir la comunicación pod a pod solo a los casos necesarios reduce la superficie de ataque.
   - La segmentación de red ayuda a prevenir ataques de movimiento lateral.

Mejores prácticas adicionales para reforzar la seguridad de Windows nodes:
- Mantener Windows nodes actualizados con los últimos parches de seguridad
- Deshabilitar características y roles de Windows innecesarios
- Configurar adecuadamente las reglas del firewall de Windows
- Usar mecanismos de autenticación fuertes
- Eliminar herramientas y componentes innecesarios de las imágenes de containers
- Implementar monitoreo de seguridad en runtime
</details>
