# Cuestionario sobre Windows en Kubernetes

Este cuestionario evalúa tus conocimientos conceptuales y prácticos sobre la administración de nodos Windows y workloads en Kubernetes. Cubre temas como los conceptos básicos de Windows containers, la configuración de nodos Windows en Kubernetes, redes, almacenamiento, seguridad y monitoreo.

## Preguntas de opción múltiple

1. ¿Qué container runtimes son compatibles con nodos Windows en Kubernetes?
   - A) Docker y containerd
   - B) CRI-O y Docker
   - C) containerd y CRI-O
   - D) Docker, containerd y gVisor

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A) Docker y containerd**

**Explicación:**
Los container runtimes compatibles oficialmente con nodos Windows en Kubernetes son Docker y containerd.

- **Docker**: Docker era la opción tradicional para ejecutar Windows containers en Windows. Sin embargo, el soporte de Docker en Kubernetes está disminuyendo gradualmente y se recomienda migrar a containerd.

- **containerd**: Este es el container runtime recomendado actualmente para nodos Windows. containerd es un runtime ligero y estable que cuenta con soporte oficial para nodos Windows en Kubernetes 1.20 y versiones posteriores.

CRI-O no es compatible oficialmente con nodos Windows. CRI-O es principalmente una implementación de Container Runtime Interface (CRI) para Linux containers.

gVisor es un sandbox runtime para aislamiento de containers, pero actualmente no es compatible con nodos Windows.

Al configurar container runtimes en nodos Windows, es importante verificar la compatibilidad con la versión de Kubernetes.
</details>

2. ¿Qué solución de red se requiere al configurar un cluster con nodos Windows y Linux mixtos en Kubernetes?
   - A) Todos los CNI plugins admiten nodos Windows y Linux
   - B) CNI plugins que admitan Windows, como Flannel, Calico y Antrea
   - C) Los nodos Windows deben usar únicamente kubenet sin CNI plugins
   - D) Los nodos Windows siempre deben usar solo el modo de red del host

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) CNI plugins que admitan Windows, como Flannel, Calico y Antrea**

**Explicación:**
Al configurar un cluster con nodos Windows y Linux mixtos en Kubernetes, debes usar CNI (Container Network Interface) plugins específicos que admitan Windows. No todos los CNI plugins admiten Windows.

Los principales CNI plugins que admiten nodos Windows son:

- **Flannel**: Admite nodos Windows en modo de red overlay (vxlan).
- **Calico**: Proporciona soporte para nodos Windows, compatible tanto con el modo BGP como con el modo VXLAN.
- **Antrea**: Proporciona soporte para nodos Windows usando OVS (Open vSwitch).

Además, Azure CNI, OVN-Kubernetes y otros admiten nodos Windows.

Consideraciones al configurar CNI plugins en nodos Windows:
- Los nodos Windows tienen una pila de red diferente a la de los nodos Linux.
- Algunas funciones de red pueden estar limitadas en Windows.
- Debes verificar la versión de soporte para Windows y los requisitos de configuración del CNI plugin.

kubenet no es compatible con nodos Windows, y los nodos Windows no pueden usar el modo de red del host (HostNetwork=true no es compatible con pods Windows).
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
El modo de aislamiento predeterminado para Windows containers es Process Isolation. En este modo, los Windows containers comparten el kernel del sistema operativo del host y cada container se ejecuta como un grupo de procesos aislado.

Características del modo de aislamiento de procesos:
- Debe usar la misma versión de kernel que el OS del host.
- Menor uso de recursos y tiempo de inicio más rápido.
- Similar al modelo típico de aislamiento de Linux containers.

Windows también proporciona un modo de aislamiento alternativo llamado Hyper-V Isolation:
- Cada container se ejecuta en una máquina virtual ligera.
- Puede usar versiones de kernel diferentes a las del OS del host.
- Proporciona un mayor nivel de aislamiento, pero tiene más overhead.

Para usar aislamiento Hyper-V en Kubernetes, agrega la siguiente anotación a la especificación del pod:
```yaml
annotations:
  io.kubernetes.cri-containerd.isolation: hyperv
```

El aislamiento de máquina virtual no es un modo de aislamiento oficial para Windows containers, y aislamiento sandbox no es un término usado para Windows containers.
</details>

4. ¿Cuál de las siguientes NO es una limitación correcta al usar nodos Windows en Kubernetes?
   - A) No se pueden usar containers privilegiados
   - B) No se pueden usar volúmenes HostPath
   - C) Solo algunas funciones de SecurityContext son compatibles para pods
   - D) No se puede compartir el namespace de red del pod

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) No se pueden usar volúmenes HostPath**

**Explicación:**
Los volúmenes HostPath pueden usarse en nodos Windows. Por lo tanto, la afirmación "No se pueden usar volúmenes HostPath" es incorrecta.

Al usar volúmenes HostPath en nodos Windows, debes seguir el formato de ruta de Windows:
```yaml
volumes:
- name: data
  hostPath:
    path: C:\\data
```

Las limitaciones reales al usar nodos Windows en Kubernetes son:

- **Containers privilegiados**: Los containers privilegiados no pueden usarse en nodos Windows. Esto se debe a que no existe un concepto equivalente al modo privilegiado de Linux en Windows.

- **Limitaciones de SecurityContext**: Solo algunas funciones de SecurityContext son compatibles en nodos Windows. Por ejemplo, runAsUser, runAsGroup, fsGroup, seccomp, SELinux, etc. no son compatibles.

- **Uso compartido del namespace de red del Pod**: Los namespaces de red no pueden compartirse entre pods en nodos Windows. Esto afecta a hostNetwork: true, dnsPolicy: ClusterFirstWithHostNet, la comunicación localhost entre containers en un pod, etc.

Otras limitaciones de los nodos Windows:
- Si quieres que los DaemonSets se ejecuten en todos los nodos (Linux y Windows), debes usar nodeSelector.
- Algunos drivers de almacenamiento y tipos de volúmenes pueden estar limitados.
- Es posible que las funciones alpha/beta específicas de Linux no funcionen en nodos Windows.
</details>

5. ¿Qué etiqueta de nodo se usa para identificar nodos Windows en Kubernetes?
   - A) kubernetes.io/os=windows
   - B) beta.kubernetes.io/os=windows
   - C) node.kubernetes.io/windows=true
   - D) kubernetes.io/windows=enabled

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A) kubernetes.io/os=windows**

**Explicación:**
La etiqueta de nodo estándar utilizada para identificar nodos Windows en Kubernetes es `kubernetes.io/os=windows`. Esta etiqueta indica el tipo de sistema operativo del nodo y el scheduler de Kubernetes la usa para ubicar pods en los nodos adecuados.

Para programar pods Windows en nodos Windows, usa nodeSelector de la siguiente manera:
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

`beta.kubernetes.io/os=windows` se usaba en versiones anteriores de Kubernetes, pero ahora está obsoleta.

`node.kubernetes.io/windows=true` y `kubernetes.io/windows=enabled` no son etiquetas estándar de Kubernetes.

Nota: Los nodos Linux tienen la etiqueta `kubernetes.io/os=linux`.
</details>

6. ¿Cuál es la imagen base predeterminada usada al extraer imágenes de containers en nodos Windows?
   - A) mcr.microsoft.com/windows/servercore
   - B) mcr.microsoft.com/windows/nanoserver
   - C) mcr.microsoft.com/dotnet/framework/runtime
   - D) mcr.microsoft.com/powershell

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A) mcr.microsoft.com/windows/servercore**

**Explicación:**
La imagen base más común para Windows containers es `mcr.microsoft.com/windows/servercore`. Esta imagen se basa en una instalación de Windows Server Core e incluye los componentes principales necesarios para ejecutar la mayoría de las aplicaciones Windows.

Las principales imágenes base disponibles para Windows containers son:

1. **Windows Server Core** (`mcr.microsoft.com/windows/servercore`):
   - Imagen de tamaño medio (aproximadamente 2-4GB)
   - Admite la mayoría de las aplicaciones Windows
   - Incluye .NET Framework, PowerShell, etc.
   - Imagen base de Windows más utilizada

2. **Nano Server** (`mcr.microsoft.com/windows/nanoserver`):
   - Imagen muy pequeña (aproximadamente 100-200MB)
   - Soporte limitado para Windows API
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
- Requisitos de la aplicación (Windows APIs requeridas)
- Tamaño de la imagen y tiempo de inicio
- Requisitos de seguridad
- Compatibilidad de versión de Windows (verifica el número de versión en la etiqueta de la imagen)

Las imágenes de Windows containers deben ser de la misma versión que el OS del host o compatibles con él.
</details>

7. ¿Cuál es el método recomendado para desplegar DaemonSets en un cluster con nodos Windows y Linux mixtos en Kubernetes?
   - A) Usar un único DaemonSet y desplegarlo en todos los nodos
   - B) Crear DaemonSets separados para cada OS y usar nodeSelector
   - C) Usar StatefulSet en lugar de DaemonSet para nodos Windows
   - D) Agregar tolerations a todos los DaemonSets

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Crear DaemonSets separados para cada OS y usar nodeSelector**

**Explicación:**
El método recomendado para desplegar DaemonSets en un cluster con nodos Windows y Linux mixtos en Kubernetes es crear DaemonSets separados para cada OS y usar nodeSelector.

Razones por las que este enfoque es necesario:
- Los Windows containers y Linux containers usan formatos de imagen diferentes.
- La misma aplicación puede requerir configuraciones diferentes para cada OS.
- Algunas funciones pueden estar disponibles solo en OS específicos.

Ejemplo de DaemonSet para Windows:
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

Ejemplo de DaemonSet para Linux:
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

Usar un único DaemonSet puede hacer que los pods no se inicien en algunos nodos debido a problemas de compatibilidad de la imagen del container.

Los DaemonSets pueden usarse en nodos Windows, por lo que no es necesario reemplazarlos por StatefulSets.

Agregar tolerations a todos los DaemonSets puede ayudar a programar pods en nodos con taints, pero no resuelve los problemas de compatibilidad de OS.
</details>

8. ¿Qué afirmación sobre la configuración de DNS para pods en nodos Windows es correcta?
   - A) La configuración de DNS no es compatible en nodos Windows
   - B) Los nodos Windows deben usar Windows DNS Server en lugar de CoreDNS
   - C) Los nodos Windows pueden usar la misma configuración de DNS que los nodos Linux
   - D) Los nodos Windows requieren una configuración de servidor DNS separada para cada pod

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Los nodos Windows pueden usar la misma configuración de DNS que los nodos Linux**

**Explicación:**
Los nodos Windows pueden usar la misma configuración de DNS que los nodos Linux. El servicio DNS de Kubernetes (normalmente CoreDNS) funciona de la misma manera para pods Windows.

Configuración de DNS para pods Windows:
- Se crea automáticamente dentro de los pods Windows una configuración equivalente a `/etc/resolv.conf`.
- Los pods pueden usar el servicio DNS del cluster (CoreDNS) para resolver nombres de servicios.
- Los campos `dnsPolicy` y `dnsConfig` pueden usarse para configurar opciones de DNS.

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

Consideraciones al usar DNS en nodos Windows:
- El comportamiento del cliente DNS dentro de Windows containers puede ser ligeramente diferente al de Linux.
- Algunas herramientas relacionadas con DNS (por ejemplo, nslookup, Resolve-DnsName) están disponibles de forma predeterminada en Windows containers.
- Debes verificar que el plugin de red admita correctamente la resolución DNS.

No es necesario configurar un servidor DNS separado ni usar Windows DNS Server en nodos Windows. El mecanismo DNS estándar de Kubernetes funciona para pods Windows.
</details>

9. ¿Qué afirmación sobre la comunicación pod a pod en nodos Windows es correcta?
   - A) La comunicación pod a pod no es compatible en nodos Windows
   - B) Los pods en nodos Windows solo pueden comunicarse con pods del mismo nodo
   - C) Los pods en nodos Windows no pueden comunicarse con pods en nodos Linux
   - D) Los pods en nodos Windows pueden comunicarse con todos los demás pods mediante CNI plugins

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: D) Los pods en nodos Windows pueden comunicarse con todos los demás pods mediante CNI plugins**

**Explicación:**
Los pods en nodos Windows pueden comunicarse con todos los demás pods del cluster mediante CNI (Container Network Interface) plugins adecuados. Esto incluye pods en el mismo nodo Windows, pods en otros nodos Windows y pods en nodos Linux.

Características clave de la comunicación pod a pod en nodos Windows:
- Los pods en nodos Windows pueden descubrir y acceder a servicios del cluster por nombre.
- A los pods en nodos Windows se les asignan direcciones IP únicas dentro del rango de direcciones IP del cluster.
- La comunicación pod a pod ocurre según la implementación del CNI plugin seleccionado.

CNI plugins que admiten comunicación pod a pod en nodos Windows:
- Flannel (modo VXLAN)
- Calico
- Antrea
- Azure CNI
- OVN-Kubernetes

Por ejemplo, al usar Flannel:
- Los pods en nodos Windows se comunican con pods en otros nodos mediante encapsulación VXLAN.
- A cada pod se le asigna una dirección IP dentro del rango CIDR del cluster.
- Las tablas de enrutamiento se configuran para dirigir direcciones IP de pods a los nodos adecuados.

Consideraciones para la comunicación pod a pod en nodos Windows:
- Algunas funciones avanzadas de red pueden estar limitadas en Windows.
- El soporte de NetworkPolicy puede variar según el CNI plugin.
- Las reglas de Windows firewall no deben interferir con la comunicación de los pods.

Los pods en nodos Windows pueden comunicarse perfectamente con pods en nodos Linux, lo cual es una de las funciones centrales de Kubernetes.
</details>

10. ¿Qué afirmación sobre los límites de recursos para Windows containers en Kubernetes es correcta?
    - A) Los Windows containers no admiten límites de recursos
    - B) Los límites de CPU son compatibles, pero los límites de memoria no
    - C) Los límites de memoria son compatibles, pero los límites de CPU no
    - D) Tanto los límites de CPU como los de memoria son compatibles

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: D) Tanto los límites de CPU como los de memoria son compatibles**

**Explicación:**
Los Windows containers en Kubernetes admiten límites de recursos tanto de CPU como de memoria. Los nodos Windows pueden limitar y solicitar recursos de containers de forma similar a los nodos Linux.

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

Características de la gestión de recursos para Windows containers:
- **Límites de CPU**: Windows implementa CPU sharing y límites para gestionar la asignación de recursos de CPU entre containers.
- **Límites de memoria**: Windows limita el uso de memoria de los containers y realiza terminación OOM (Out of Memory) cuando se supera el límite.
- **Monitoreo de recursos**: kubelet monitorea el uso de recursos de Windows containers e informa a la Kubernetes API.

Consideraciones para la gestión de recursos de Windows containers:
- El overhead de recursos predeterminado para Windows containers puede ser mayor que el de Linux containers.
- La implementación exacta de los límites de recursos puede variar según la versión de Windows.
- Establecer límites de memoria demasiado bajos puede impedir que los Windows containers funcionen correctamente.
- Se produce overhead adicional de recursos al usar el modo de aislamiento Hyper-V.

Puedes monitorear el uso de recursos en nodos Windows usando los comandos `kubectl top pods` y `kubectl top nodes`.
</details>
## Preguntas de respuesta corta

1. Explica los pasos y requisitos principales para agregar nodos Windows a un cluster de Kubernetes.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:**

**Pasos para agregar nodos Windows a un cluster de Kubernetes:**

1. **Verificar prerrequisitos:**
   - Kubernetes versión 1.14 o posterior (se recomienda la versión más reciente)
   - El control plane debe ejecutarse en nodos Linux
   - Windows Server 2019 o posterior (se recomienda Windows Server 2022)
   - CNI plugin compatible (Flannel, Calico, Antrea, etc.)

2. **Configurar redes:**
   - Instalar un CNI plugin que admita nodos Windows
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

3. **Preparar el nodo Windows:**
   - Instalar y actualizar Windows Server
   - Habilitar las funciones de Windows requeridas:
     ```powershell
     Install-WindowsFeature -Name Containers
     Restart-Computer -Force
     ```
   - Instalar el container runtime (se recomienda containerd):
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
   - Descargar los binarios de Kubernetes:
     ```powershell
     curl.exe -L https://dl.k8s.io/v1.26.0/kubernetes-node-windows-amd64.tar.gz -o kubernetes-node-windows-amd64.tar.gz
     tar.exe xvf kubernetes-node-windows-amd64.tar.gz
     mkdir -p $env:ProgramFiles\Kubernetes\bin
     Copy-Item -Path "kubernetes\node\bin\*" -Destination "$env:ProgramFiles\Kubernetes\bin" -Recurse -Force
     ```
   - Crear el archivo de configuración de kubelet:
     ```powershell
     New-Item -Path "$env:ProgramFiles\Kubernetes\kubelet-config.yaml" -ItemType File -Force
     # Add configuration file contents
     ```
   - Registrar e iniciar el servicio kubelet:
     ```powershell
     & $env:ProgramFiles\Kubernetes\bin\kubelet.exe --windows-service --config=$env:ProgramFiles\Kubernetes\kubelet-config.yaml
     Start-Service kubelet
     ```
   - Configurar e iniciar kube-proxy (normalmente desplegado como DaemonSet)

5. **Unir el nodo:**
   - Ejecutar el comando kubeadm join o configurar manualmente certificados TLS y kubeconfig
   - Verificar que el nodo se haya registrado en el cluster:
     ```bash
     kubectl get nodes
     ```

6. **Agregar etiquetas de nodo:**
   - Agregar la etiqueta de OS al nodo Windows (si no se agregó automáticamente):
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
   - Verificar la versión de Kubernetes y las funciones de soporte para Windows

2. **Redes:**
   - Usar CNI plugins compatibles con nodos Windows
   - Verificar el soporte de network policy
   - Verificar requisitos de puertos (kubelet, containerd, CNI, etc.)

3. **Almacenamiento:**
   - Verificar los drivers de almacenamiento y tipos de volumen compatibles con nodos Windows
   - Verificar compatibilidad del CSI driver

4. **Monitoreo y logging:**
   - Desplegar agentes de monitoreo adecuados para nodos Windows
   - Configurar la recopilación de Windows event logs

5. **Seguridad:**
   - Configurar reglas de Windows firewall
   - Configurar Group Managed Service Accounts (gMSA) si es necesario
   - Configurar network security groups

6. **Automatización:**
   - Automatizar el aprovisionamiento de nodos Windows (Ansible, PowerShell DSC, etc.)
   - Establecer una estrategia de actualización de nodos
</details>

2. Explica las principales diferencias entre Windows containers y Linux containers, y cómo gestionar estas diferencias en Kubernetes.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:**

**Principales diferencias entre Windows containers y Linux containers:**

1. **Tecnología subyacente:**
   - **Linux containers**: Usan namespaces de Linux, cgroups y funciones del kernel para el aislamiento
   - **Windows containers**: Usan tecnologías de aislamiento de Windows (job objects, aislamiento Hyper-V, etc.)

2. **Estructura de imagen:**
   - **Linux containers**: Tamaño relativamente pequeño (decenas a cientos de MB)
   - **Windows containers**: Generalmente mayor tamaño (varios GB), las imágenes base son más grandes

3. **Modos de aislamiento:**
   - **Linux containers**: Un único modo de aislamiento (basado en namespaces)
   - **Windows containers**: Dos modos compatibles: aislamiento de procesos y aislamiento Hyper-V

4. **Sistema de archivos:**
   - **Linux containers**: Sistema de archivos por capas (OverlayFS, etc.)
   - **Windows containers**: Filter driver basado en NTFS

5. **Redes:**
   - **Linux containers**: Diversos modos de red y soporte de drivers
   - **Windows containers**: Modos de red limitados, solo CNI plugins específicos compatibles

6. **Gestión de recursos:**
   - **Linux containers**: Control de recursos granular mediante cgroups
   - **Windows containers**: Control de recursos mediante Job Objects, con algunas limitaciones

7. **Security Context:**
   - **Linux containers**: Varias opciones de security context (SELinux, AppArmor, etc.)
   - **Windows containers**: Opciones de security context limitadas, containers privilegiados no compatibles

8. **Dependencia del OS del host:**
   - **Linux containers**: Pueden ejecutarse en varias distribuciones Linux
   - **Windows containers**: Requieren la misma versión que el OS del host o una compatible

**Cómo gestionar estas diferencias en Kubernetes:**

1. **Selección de nodos y scheduling:**
   - **Usar etiquetas de nodo**: `kubernetes.io/os=windows` o `kubernetes.io/os=linux`
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

3. **Gestión de DaemonSet:**
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

4. **Gestión de imágenes:**
   - **Usar imágenes multi-arquitectura**: Admitir varios OS/arquitecturas con la misma etiqueta
   - **Usar etiquetas de imagen específicas por OS**: `myapp:linux` y `myapp:windows`
   - **Establecer image pull policy**: `imagePullPolicy: Always`

5. **Resource Requests y Limits:**
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

6. **Redes:**
   - **Seleccionar CNI plugin compatible**: Flannel, Calico, Antrea, etc.
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
   - **Usar storage classes compatibles con el OS**:
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
   - **Aplicar configuraciones de seguridad adecuadas para cada OS**:
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
   - **Ajustar rutas de recopilación de logs**: Windows (`C:\k\logs`) vs Linux (`/var/log`)

10. **CI/CD Pipelines:**
    - **Configurar pipelines de build y test específicos por OS**
    - **Establecer una estrategia de Deployment multi-OS**
</details>

3. Explica cómo usar Group Managed Service Accounts (gMSA) en Windows containers y sus beneficios.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:**

**Descripción general de Group Managed Service Accounts (gMSA):**

Group Managed Service Accounts (gMSA) son un tipo especial de cuenta de Active Directory para autenticación de servicios en entornos de dominio Windows. Usar gMSA en Windows containers en Kubernetes permite ejecutar aplicaciones que requieren autenticación de dominio y es especialmente útil en los siguientes escenarios:

- Aplicaciones .NET que requieren integración con Active Directory
- Conexiones a SQL Server usando autenticación Windows
- Servicios que requieren autenticación Kerberos
- Aplicaciones que necesitan acceder a recursos de dominio

**Cómo usar gMSA en Windows containers:**

1. **Prerrequisitos:**
   - Controlador de dominio de Active Directory
   - Los nodos Windows deben estar unidos al dominio
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

5. **Agregar configuración de gMSA a la definición del Pod:**
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

6. **Verificar el uso de gMSA:**
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
   - Gestión y rotación automática de contraseñas
   - Permite aplicar el principio de menor privilegio

2. **Integración con Active Directory:**
   - Permite containerizar aplicaciones existentes que usan autenticación Windows
   - Admite autenticación Kerberos y NTLM
   - Acceso fluido a recursos de dominio

3. **Gestión de identidades centralizada:**
   - Gestión unificada de identidades mediante Active Directory
   - Se pueden aplicar políticas de grupo
   - Auditoría y cumplimiento mejorados

4. **Compatibilidad de aplicaciones:**
   - Admite aplicaciones .NET legacy que requieren autenticación de dominio
   - Admite conexiones a SQL Server usando autenticación integrada de Windows
   - Admite autenticación Windows para aplicaciones web IIS

5. **Operaciones simplificadas:**
   - Gestión automatizada de credenciales
   - Las credenciales persisten entre reinicios de containers
   - La misma identidad puede compartirse entre múltiples containers

**Consideraciones al usar gMSA:**

1. **Requisitos de red:**
   - Se requiere conectividad de red desde los nodos Windows a los controladores de dominio
   - Se requiere configuración DNS adecuada
   - Los puertos requeridos deben estar abiertos (Kerberos, LDAP, etc.)

2. **Gestión de permisos:**
   - Otorgar solo los permisos mínimos requeridos a gMSA
   - Configurar membresías de grupo adecuadas
   - Revisiones periódicas de permisos

3. **Escalabilidad:**
   - Considerar la carga del controlador de dominio en clusters grandes
   - Usar múltiples cuentas gMSA para separar permisos

4. **Solución de problemas:**
   - Depurar problemas de conectividad de dominio
   - Verificar errores de configuración de credential spec
   - Revisar logs del container runtime
</details>

4. Explica cómo configurar logging y monitoreo para nodos Windows en Kubernetes y las diferencias con los nodos Linux.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:**

**Configuración de logging y monitoreo para nodos Windows:**

**1. Configuración de logging:**

**Principales fuentes de logs para nodos Windows:**
- Windows Event Logs (System, Application, Security)
- Eventos ETW (Event Tracing for Windows)
- Archivos de logs de aplicaciones (normalmente dentro de la unidad `C:\`)
- Logs de kubelet y container runtime (normalmente `C:\k\logs` o rutas similares)

**Métodos para configurar logging en nodos Windows:**

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

2. **Configuración de recopilación de Windows Event Log:**
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

3. **Recopilación de logs de containers:**
   - Ruta de logs de containerd: `C:\ProgramData\containerd\root\containers`
   - Ruta de logs de kubelet: `C:\k\logs` o Windows Event Log

**2. Configuración de monitoreo:**

**Métricas principales para el monitoreo de nodos Windows:**
- Uso de CPU, memoria y disco
- Tráfico de red
- Conteo de procesos
- Uso de page file
- Uso de recursos de containers

**Métodos para configurar el monitoreo de nodos Windows:**

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
   - Crear dashboards dedicados para métricas de nodos Windows
   - Agregar panels específicos de Windows (por ejemplo, uso de page file, estado de servicios, etc.)

**3. Herramientas de solución de problemas:**

**Herramientas para solucionar problemas en nodos Windows:**
- Comandos de PowerShell (`Get-Process`, `Get-Service`, `Get-EventLog`)
- Windows Performance Monitor (PerfMon)
- Event Viewer
- Comando `kubectl debug` (soporte limitado en nodos Windows)

**Ejemplos de solución de problemas en nodos Windows:**
```powershell
# Check kubelet logs
Get-EventLog -LogName Application -Source kubelet -Newest 50

# Check containerd status
Get-Service containerd

# Verify network connectivity
Test-NetConnection -ComputerName api.kubernetes.cluster -Port 443
```

**Diferencias clave con los nodos Linux:**

1. **Ubicación de almacenamiento de logs:**
   - **Linux**: Se almacenan como archivos de texto en el directorio `/var/log/`
   - **Windows**: Windows Event Logs (formato binario) y archivos de texto en varias ubicaciones

2. **Mecanismo de recopilación de logs:**
   - **Linux**: La recopilación de logs basada en archivos es típica (tail, read)
   - **Windows**: Requiere recopilación mediante Windows Event Log API

3. **Recopilación de métricas:**
   - **Linux**: Recopila métricas desde los sistemas de archivos `/proc`, `/sys`
   - **Windows**: Usa WMI (Windows Management Instrumentation) o Performance Counter API

4. **Logs de containers:**
   - **Linux**: La salida estándar/error se redirige a archivos
   - **Windows**: ETW o logging basado en archivos, estructura de rutas diferente

5. **Monitoreo de recursos:**
   - **Linux**: Monitoreo del uso de recursos de containers mediante cgroups
   - **Windows**: Monitoreo de recursos mediante Job Objects; algunas métricas se calculan de forma diferente

6. **Agentes de monitoreo:**
   - **Linux**: Soporte para varios agentes (node-exporter, cAdvisor, etc.)
   - **Windows**: Soporte de agentes limitado; se requieren agentes específicos de Windows

7. **Herramientas de depuración:**
   - **Linux**: Varias herramientas CLI (ps, top, netstat, strace, etc.)
   - **Windows**: Comandos de PowerShell, herramientas GUI, herramientas CLI limitadas

**Buenas prácticas:**

1. **Solución integrada de logging:**
   - Usar EFK (Elasticsearch, Fluent Bit, Kibana) o ELK stack
   - Configuraciones separadas para nodos Windows y Linux

2. **Solución integrada de monitoreo:**
   - Monitorear todos los nodos con Prometheus + Grafana
   - Crear dashboards específicos por OS

3. **Configuración de alertas:**
   - Configurar reglas de alerta para eventos específicos de Windows
   - Monitorear el estado de servicios críticos de Windows

4. **Política de retención de logs:**
   - Configurar el tamaño y periodo de retención de Windows event logs
   - Configurar la política de rotación de logs

5. **Monitoreo de seguridad:**
   - Recopilar y analizar Windows security event logs
   - Monitorear cambios de permisos e intentos de inicio de sesión
</details>

5. Explica las opciones de almacenamiento y los métodos de configuración de montajes de volúmenes para Windows containers en Kubernetes.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:**

**Opciones de almacenamiento para Windows containers:**

**1. Tipos de volumen básicos:**

1. **emptyDir:**
   - Almacena datos temporales durante la vida del pod
   - Se crea en el volumen NTFS local del nodo Windows
   - Los datos se eliminan cuando se elimina el pod

   ```yaml
   volumes:
   - name: temp-data
     emptyDir: {}
   ```

2. **hostPath:**
   - Acceso directo al sistema de archivos del nodo Windows
   - Debe usar el formato de ruta de Windows (escapar barras invertidas)
   - Los datos no pueden compartirse entre nodos

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
   - Azure Kubernetes Service admite nodos Windows
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
   - Soporte de nodos Windows en Amazon EKS
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
   - Admite acceso ReadWriteMany entre múltiples pods

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
   - Requiere configuración del iniciador iSCSI en el nodo Windows
   - Proporciona acceso a almacenamiento de bloque
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

**3. Configuración de montajes de volumen para Windows containers:**

1. **Rutas de montaje de volúmenes:**
   - Los Windows containers usan el formato de ruta de Windows
   - Normalmente usan rutas dentro de la unidad `C:\`
   - Las barras invertidas en las rutas necesitan escaparse en YAML

   ```yaml
   volumeMounts:
   - name: data
     mountPath: C:\\data
   ```

2. **Montajes de solo lectura:**
   - Compatibles con Windows containers
   - Se aplican mediante permisos NTFS

   ```yaml
   volumeMounts:
   - name: config
     mountPath: C:\\config
     readOnly: true
   ```

3. **Montajes Subpath:**
   - Pueden montar solo subpaths específicos de volúmenes
   - Ten en cuenta los separadores de ruta de Windows

   ```yaml
   volumeMounts:
   - name: shared-data
     mountPath: C:\\app\\logs
     subPath: logs
   ```

**4. Ejemplos de configuración de almacenamiento para Windows containers:**

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
   - Windows usa barras invertidas (`\`) pero es necesario escaparlas en YAML
   - Alternativamente, se pueden usar barras diagonales (`/`), pero verifica la compatibilidad de la aplicación

2. **Permisos de archivo:**
   - Windows usa el modelo de permisos NTFS
   - No se pueden establecer permisos como chmod/chown en Linux
   - Los permisos dentro de los containers se determinan por el contexto de usuario del container

3. **Consideraciones de rendimiento:**
   - El almacenamiento de red (SMB/CIFS) puede tener latencia
   - Se recomienda almacenamiento local o almacenamiento de bloque adjunto directamente para requisitos de alto rendimiento

4. **Compatibilidad de Storage Class:**
   - Verificar storage classes compatibles con nodos Windows
   - Verificar el soporte de Windows de los CSI drivers

5. **Backup y recuperación:**
   - Considerar la integración con Windows Volume Shadow Copy Service (VSS)
   - Implementar mecanismos de backup consistentes con la aplicación
</details>

## Preguntas prácticas

1. Escribe un manifiesto Deployment que cumpla los siguientes requisitos para un cluster de Kubernetes con nodos Windows y Linux mixtos:
   - Nombre de la aplicación: web-app
   - Imagen de Windows container: mcr.microsoft.com/windows/servercore/iis:windowsservercore-ltsc2019
   - Replicas: 2
   - Puerto: 80
   - Variable de entorno: WEBSITE_NAME=MyWindowsApp
   - Volumen: Montar ConfigMap "web-config" en C:\inetpub\wwwroot\web.config

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

1. **Deployment Resource**:
   - Usa `nodeSelector` para especificar scheduling solo en nodos Windows
   - Establece 2 replicas como se requiere
   - Usa la imagen del servidor web IIS

2. **Configuración del container**:
   - Expone el puerto 80
   - Establece la variable de entorno `WEBSITE_NAME`
   - Monta ConfigMap en una ruta de archivo específica (usando formato de ruta de Windows)

3. **Configuración de volumen**:
   - Monta ConfigMap como volumen
   - Usa `subPath` para montar una clave específica de ConfigMap como archivo

4. **Definición de Service**:
   - Crea un Service ClusterIP para acceder a la aplicación
   - Accesible a través del puerto 80

**Notas**:
- En rutas de Windows, las barras invertidas (`\`) se tratan como caracteres de escape en YAML, así que ten cuidado. Este ejemplo usa barras invertidas normales, pero para rutas más complejas se pueden usar barras invertidas dobles (`\\`) o barras diagonales (`/`).
- Los Windows containers pueden tener requisitos de recursos más altos que los Linux containers, por lo que es buena práctica establecer resource requests y limits adecuados en entornos de producción.
</details>

2. Escribe manifiestos DaemonSet para desplegar agentes de monitoreo que se ejecuten en nodos Windows y Linux. Cada OS debe usar imágenes y configuraciones adecuadas.

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

1. **DaemonSet para nodos Linux**:
   - Usa `nodeSelector` para programar solo en nodos Linux
   - Usa la imagen Prometheus Node Exporter
   - Monta los directorios `/proc`, `/sys`, `/` del host para recopilar métricas del sistema
   - Security context configurado para ejecutarse como usuario no root

2. **DaemonSet para nodos Windows**:
   - Usa `nodeSelector` para programar solo en nodos Windows
   - Usa la imagen Windows Exporter
   - Especifica los metric collectors que se recopilarán
   - Se aplica configuración específica de Windows

3. **Service común**:
   - Crea un Service que selecciona pods de ambos DaemonSets
   - Expone los puertos de métricas tanto de Linux como de Windows
   - Prometheus puede hacer scrape de métricas mediante este Service

**Notas**:
- Es importante usar imágenes y configuraciones adecuadas para cada OS.
- Como los métodos de recopilación de métricas difieren entre nodos Linux y Windows, se separan en DaemonSets diferentes.
- Usar etiquetas para distinguir tipos de OS es útil para filtrar y visualizar métricas en el sistema de monitoreo.
- En entornos de producción, se necesita configuración adicional de resource requests y limits, security contexts, service accounts, etc.
</details>

3. Escribe un manifiesto pod para desplegar una aplicación .NET que use autenticación Active Directory en un Windows container. Se deben usar Group Managed Service Accounts (gMSA).

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

1. **gMSA Credential Spec Secret**:
   - La credential spec de gMSA de Active Directory se codifica en Base64 y se almacena como secret
   - Este secret es usado por los pods para autenticación de dominio

2. **Configuración del Pod Windows**:
   - Usa `nodeSelector` para programar en nodos Windows
   - Referencia la credential spec de gMSA usando `securityContext.windowsOptions.gmsaCredentialSpecName`
   - Usa una imagen de aplicación .NET
   - Se establecen resource requests y limits adecuados

3. **Volúmenes y configuración**:
   - Proporciona configuración de aplicación mediante ConfigMap
   - Archivo de configuración montado usando formato de ruta de Windows
   - Incluye connection string de SQL Server usando autenticación integrada de Windows

4. **Definición de Service**:
   - Crea un Service ClusterIP para acceder a la aplicación

**Prerrequisitos para configurar gMSA:**

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
- Los nodos Windows deben estar unidos al dominio de Active Directory.
- containerd o Docker deben estar configurados para admitir gMSA.
- En entornos reales, el contenido de la credential spec debe gestionarse de forma segura.
- La aplicación debe estar configurada para usar correctamente la autenticación Windows.
</details>

4. Escribe manifiestos NetworkPolicy que cumplan los siguientes requisitos en un cluster con nodos Windows y Linux mixtos:
   - Los pods de aplicación web Windows (label: app=windows-web) solo pueden acceder a pods de base de datos Linux (label: app=linux-db)
   - Los pods de base de datos permiten acceso solo en el puerto 3306
   - Los pods de aplicación web son accesibles desde el exterior en el puerto 80

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
   - Se aplica a pods con la etiqueta `app=windows-web`
   - **Regla de Ingress**: Permite acceso desde todos los orígenes en el puerto 80
   - **Regla de Egress**: Permite acceso solo al puerto 3306 en pods con la etiqueta `app=linux-db`

2. **NetworkPolicy de la base de datos Linux**:
   - Se aplica a pods con la etiqueta `app=linux-db`
   - **Regla de Ingress**: Permite acceso solo desde pods con la etiqueta `app=windows-web` en el puerto 3306

**Notas**:
- Las network policies requieren un CNI plugin que admita NetworkPolicy (por ejemplo, Calico, Antrea) para funcionar.
- El soporte de NetworkPolicy en nodos Windows puede variar según el CNI plugin.
- Este ejemplo asume el namespace default, pero en entornos reales deben especificarse namespaces adecuados.
- En entornos de producción, pueden necesitarse reglas de egress adicionales para búsquedas DNS, acceso a servicios externos, etc.

**Ejemplos de Deployment:**

Pods de aplicación web Windows:
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

Pods de base de datos Linux:
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

5. Escribe un manifiesto Deployment para una aplicación .NET Framework que se ejecuta en nodos Windows. La aplicación requiere una connection string como variable de entorno para acceder a Azure Blob Storage. Configura también un volumen persistente para logs.

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
   - La connection string de Azure Storage se codifica en Base64 y se almacena como secret
   - La aplicación puede acceder a ella de forma segura como variable de entorno

2. **PersistentVolumeClaim**:
   - Solicita 10GB de almacenamiento persistente para archivos de logs
   - Usa Azure Disk storage class (ajustar para tu entorno)
   - Usa el access mode ReadWriteOnce

3. **Configuración de Deployment**:
   - Usa `nodeSelector` para programar solo en nodos Windows
   - Usa una imagen de aplicación .NET Framework
   - Proporciona la connection string de Azure Storage mediante variables de entorno
   - Monta el volumen persistente para el directorio de logs
   - Monta el archivo web.config desde ConfigMap
   - Se establecen resource requests y limits adecuados
   - Readiness y liveness probes configuradas para health checking

4. **Configuración de ConfigMap**:
   - Proporciona el archivo web.config para la aplicación .NET Framework
   - Incluye ajustes y configuración de la aplicación

5. **Definición de Service**:
   - Crea un Service ClusterIP para acceder a la aplicación

**Notas**:
- En entornos reales, las direcciones de image registry, storage classes, requisitos de recursos, etc. deben ajustarse a tu entorno.
- Las aplicaciones .NET Framework deben usar imágenes basadas en Windows Server Core.
- En entornos de producción, el acceso externo puede configurarse mediante ingress controllers o load balancers.
- La información sensible, como las connection strings de Azure Storage, debe integrarse con sistemas externos de gestión de secrets como Azure Key Vault.
</details>

## Temas avanzados

1. ¿Cuál es la configuración más importante al configurar containerd como container runtime para nodos Windows en Kubernetes?
   - A) Configuración sandbox_image
   - B) Nivel y ruta de logs
   - C) Límites de memoria y CPU sharing
   - D) Image pull policy y configuración de registry

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A) Configuración sandbox_image**

**Explicación:**
La configuración más importante al configurar containerd como container runtime para nodos Windows en Kubernetes es la configuración `sandbox_image`. Esta configuración especifica la imagen que se usará como container de infraestructura del pod (pause container) en nodos Windows.

Por qué la configuración `sandbox_image` es importante para nodos Windows en la configuración de containerd:

1. **Redes de Pod**: El pause container configura y mantiene el namespace de red de los pods. Como Windows usa una pila de red diferente a Linux, se requiere una imagen pause específica para Windows.

2. **Compatibilidad de OS**: Las imágenes pause de Linux no funcionan en nodos Windows, y las imágenes pause de Windows no funcionan en nodos Linux.

3. **Compatibilidad de versiones**: Debes seleccionar una imagen pause adecuada compatible con la versión de Windows (por ejemplo, Windows Server 2019, Windows Server 2022).

Ejemplo de configuración de containerd para nodos Windows:
```toml
[plugins."io.containerd.grpc.v1.cri".containerd]
  default_runtime_name = "microsoft/windows"

[plugins."io.containerd.grpc.v1.cri".containerd.runtimes."microsoft/windows"]
  runtime_type = "io.containerd.runhcs.v1"

[plugins."io.containerd.grpc.v1.cri"]
  sandbox_image = "mcr.microsoft.com/oss/kubernetes/pause:3.6-windows-ltsc2019"
```

Imágenes pause de Windows usadas comúnmente:
- Windows Server 2019 LTSC: `mcr.microsoft.com/oss/kubernetes/pause:3.6-windows-ltsc2019`
- Windows Server 2022: `mcr.microsoft.com/oss/kubernetes/pause:3.6-windows-ltsc2022`

Otras opciones también son importantes, pero `sandbox_image` es la más crítica:
- El nivel y la ruta de logs son útiles para depuración, pero no son funcionalmente esenciales.
- Los límites de memoria y CPU sharing son importantes para tuning de rendimiento, pero no afectan la funcionalidad básica.
- Image pull policy y configuración de registry son importantes para la gestión de imágenes, pero no afectan el funcionamiento básico del container runtime.
</details>

2. ¿Cuál es el principal beneficio de usar el modo de aislamiento Hyper-V en Windows containers?
   - A) Mejor rendimiento y menor uso de recursos
   - B) Capacidad de ejecutar containers con versiones de Windows diferentes a la del OS del host
   - C) Mejor velocidad de comunicación de red entre containers
   - D) Soporte para más Windows APIs y funciones

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Capacidad de ejecutar containers con versiones de Windows diferentes a la del OS del host**

**Explicación:**
El principal beneficio de usar el modo de aislamiento Hyper-V en Windows containers es la capacidad de ejecutar containers con versiones de Windows diferentes a la del OS del host. Esta es una de las características importantes de Windows containers y es especialmente útil al ejecutar aplicaciones legacy en infraestructura moderna.

Beneficios principales del modo de aislamiento Hyper-V:

1. **Compatibilidad de versiones**:
   - Resuelve problemas de incompatibilidad de versión entre el OS del host y el OS del container.
   - Por ejemplo, puedes ejecutar containers basados en Windows Server 2019 en un host Windows Server 2022.
   - Esto no es posible en el modo de aislamiento de procesos (el aislamiento de procesos requiere que el host y el container usen la misma versión de kernel).

2. **Aislamiento de seguridad mejorado**:
   - Cada container se ejecuta en una máquina virtual ligera que proporciona un aislamiento más fuerte.
   - Se refuerzan los límites de seguridad entre containers y entre containers y el host.
   - Útil en entornos multi-tenant o al ejecutar código no confiable.

3. **Aislamiento a nivel de kernel**:
   - Cada container tiene su propia instancia del kernel de Windows.
   - Esto proporciona aislamiento a nivel de kernel, de modo que problemas del kernel en un container no afecten a otros containers ni al host.

Para usar el modo de aislamiento Hyper-V en Kubernetes, agrega la siguiente anotación a la especificación del pod:
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
- Requiere que la función Hyper-V esté habilitada en el host.

Problemas con las otras opciones:
- El aislamiento Hyper-V en realidad tiene menor rendimiento y mayor uso de recursos (A es incorrecta).
- La comunicación de red entre containers es en realidad más rápida en el modo de aislamiento de procesos (C es incorrecta).
- El soporte de Windows API y funciones depende de la versión del OS del container; el aislamiento Hyper-V en sí no proporciona más APIs (D es incorrecta).
</details>

3. ¿Qué afirmación sobre redes de pods al usar nodos Windows en Kubernetes es correcta?
   - A) Los nodos Windows no usan CNI plugins y usan su propia pila de red
   - B) Los nodos Windows usan los mismos CNI plugins que los nodos Linux, pero con configuración diferente
   - C) Los nodos Windows siempre deben usar el modo de red del host
   - D) Los nodos Windows no admiten redes overlay

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Los nodos Windows usan los mismos CNI plugins que los nodos Linux, pero con configuración diferente**

**Explicación:**
Los nodos Windows en Kubernetes pueden usar los mismos CNI (Container Network Interface) plugins que los nodos Linux, pero la configuración es diferente porque Windows tiene una pila de red distinta. Esto permite un modelo de red consistente en clusters de OS mixtos, considerando al mismo tiempo las características de cada OS.

Características de redes de pods en nodos Windows:

1. **Soporte de CNI Plugin**:
   - Los nodos Windows admiten varios CNI plugins, incluidos Flannel, Calico y Antrea.
   - Estos plugins están diseñados para funcionar en nodos Linux y Windows.
   - Cada plugin proporciona componentes o configuraciones específicas de Windows.

2. **Modos de red**:
   - Los nodos Windows generalmente admiten redes overlay (VXLAN, GENEVE, etc.).
   - Admiten varios modos de red, incluidos L2bridge, L2tunnel, overlay, etc.
   - El modo VXLAN de Flannel se usa ampliamente en nodos Windows.

3. **Diferencias de configuración**:
   - Los nodos Windows usan HNS (Host Network Service) para gestionar la configuración de red.
   - Los métodos de creación y gestión de endpoints de red difieren de Linux.
   - Algunas funciones avanzadas de red pueden estar limitadas en Windows.

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

Puede necesitarse configuración adicional en nodos Windows:
```powershell
# Script running on Windows nodes
$env:KUBE_NETWORK = "cbr0"
$networkName = "vxlan0"
$networkMode = "overlay"
```

Problemas con las otras opciones:
- Los nodos Windows usan CNI plugins y no usan únicamente su propia pila de red (A es incorrecta).
- Los nodos Windows no admiten el modo de red del host. `hostNetwork: true` no funciona para pods Windows (C es incorrecta).
- Los nodos Windows admiten redes overlay (VXLAN, etc.) (D es incorrecta).
</details>

4. ¿Qué afirmación sobre la gestión de recursos en nodos Windows en Kubernetes es correcta?
   - A) Los nodos Windows no admiten límites de recursos
   - B) Los nodos Windows proporcionan límites de recursos más precisos que los nodos Linux
   - C) Los nodos Windows implementan límites de recursos usando Job Objects
   - D) Los nodos Windows implementan límites de recursos usando cgroups

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Los nodos Windows implementan límites de recursos usando Job Objects**

**Explicación:**
Los nodos Windows en Kubernetes usan Job Objects, una función del sistema operativo Windows, para implementar límites de recursos para containers. Esto contrasta con los nodos Linux, que usan cgroups.

Características de la gestión de recursos en nodos Windows:

1. **Job Objects**:
   - Windows usa Job Objects para limitar el uso de recursos de grupos de procesos.
   - Los container runtimes (containerd o Docker) usan la Job Objects API para aplicar límites de CPU y memoria.
   - Job Objects puede limitar tiempo de CPU, uso de memoria, tiempo de trabajo, etc. para grupos de procesos.

2. **Límites de CPU**:
   - Los límites de CPU en Windows se implementan mediante un mecanismo de CPU sharing (weights).
   - Esto es similar al CPU sharing de Linux, pero se implementa de forma diferente.
   - Windows ajusta el CPU sharing en función de la cantidad de cores de CPU.

3. **Límites de memoria**:
   - Los límites de memoria para Windows containers se implementan mediante la función de límite de memoria de Job Objects.
   - Cuando los containers superan los límites de memoria, se produce terminación OOM (Out of Memory).
   - La gestión de memoria de Windows funciona de forma diferente a Linux, por lo que el comportamiento real puede diferir incluso con el mismo valor de límite de memoria.

4. **Configuración de Resource Request y Limit**:
   - Los pods Windows especifican resource requests y limits de la misma manera que los pods Linux:
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

5. **Monitoreo y reporte**:
   - kubelet monitorea el uso de recursos de containers mediante Windows performance counters.
   - Esta información puede verse mediante los comandos `kubectl top pods` y `kubectl top nodes`.
   - Metrics server recopila esta información y la proporciona mediante la Kubernetes API.

Consideraciones para la gestión de recursos en nodos Windows:
- Los Windows containers generalmente usan más recursos predeterminados que los Linux containers.
- El overhead de memoria de Windows containers puede ser mayor, así que asegúrate de tener suficiente margen de memoria.
- El comportamiento exacto de los límites de recursos puede variar según la versión de Windows.

Problemas con las otras opciones:
- Los nodos Windows admiten límites de recursos (A es incorrecta).
- Los nodos Windows generalmente proporcionan límites de recursos menos precisos que los nodos Linux (B es incorrecta).
- Los nodos Windows usan Job Objects, no cgroups (D es incorrecta).
</details>

5. ¿Cuál de las siguientes NO es una buena práctica de seguridad adecuada al usar nodos Windows en Kubernetes?
   - A) Escanear y actualizar regularmente las imágenes de containers para resolver vulnerabilidades de seguridad
   - B) Habilitar el modo privilegiado para todos los pods Windows
   - C) Usar gMSA (Group Managed Service Accounts) para integración con Active Directory
   - D) Usar network policies para restringir la comunicación pod a pod

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Habilitar el modo privilegiado para todos los pods Windows**

**Explicación:**
"Habilitar el modo privilegiado para todos los pods Windows" NO es una buena práctica de seguridad adecuada al usar nodos Windows en Kubernetes. De hecho, los Windows containers no admiten el modo privilegiado, e intentar establecerlo hará que falle la creación del pod.

Razones por las que esta opción no es adecuada:

1. **Modo privilegiado no compatible**:
   - Los Windows containers no admiten el concepto de modo privilegiado como los Linux containers.
   - Windows tiene un modelo de seguridad diferente al de Linux y no tiene un mecanismo para otorgar privilegios a nivel de host a containers.

2. **Viola el principio de menor privilegio**:
   - Incluso si fuera compatible, habilitar el modo privilegiado para todos los pods viola el principio de menor privilegio.
   - Cada workload debe tener solo los permisos mínimos necesarios.

3. **Mayor riesgo de seguridad**:
   - El modo privilegiado permite a los containers acceder al sistema host, aumentando considerablemente los riesgos de seguridad.
   - Si ocurre una vulnerabilidad de escape de container, todo el sistema host podría quedar expuesto al riesgo.

Todas las demás opciones son buenas prácticas de seguridad adecuadas:

A) **Escanear y actualizar regularmente las imágenes de containers para resolver vulnerabilidades de seguridad**:
   - El escaneo de imágenes es importante para identificar y resolver vulnerabilidades conocidas.
   - Las imágenes de Windows deben recibir actualizaciones de seguridad periódicas.
   - Es buena práctica integrar herramientas de escaneo de imágenes en CI/CD pipelines.

C) **Usar gMSA (Group Managed Service Accounts) para integración con Active Directory**:
   - gMSA permite que los Windows containers se autentiquen de forma segura ante servicios de Active Directory.
   - Usar gMSA en lugar de credenciales hardcodeadas mejora la seguridad.
   - Proporciona funcionalidad de gestión y rotación automática de contraseñas.

D) **Usar network policies para restringir la comunicación pod a pod**:
   - Las network policies aplican el principio de menor privilegio a la comunicación de red.
   - Restringir la comunicación pod a pod solo a los casos necesarios reduce la superficie de ataque.
   - La segmentación de red ayuda a prevenir ataques de movimiento lateral.

Buenas prácticas adicionales para reforzar la seguridad de nodos Windows:
- Mantener los nodos Windows actualizados con los últimos parches de seguridad
- Deshabilitar funciones y roles de Windows innecesarios
- Configurar adecuadamente las reglas de Windows firewall
- Usar mecanismos de autenticación fuertes
- Eliminar herramientas y componentes innecesarios de las imágenes de containers
- Implementar monitoreo de seguridad en runtime
</details>
