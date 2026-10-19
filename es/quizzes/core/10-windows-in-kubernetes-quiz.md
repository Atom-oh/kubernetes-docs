# Cuestionario sobre Windows en Kubernetes

Este cuestionario evalúa tus conocimientos conceptuales y prácticos para administrar nodos y cargas de trabajo Windows en Kubernetes. Abarca los conceptos básicos de los contenedores Windows, la configuración de nodos Windows, la red, el almacenamiento, la seguridad y la supervisión.

## Preguntas de opción múltiple

1. ¿Qué runtimes de contenedores admite Kubernetes en los nodos Windows?
   - A) containerd con compatibilidad con CRI para Windows
   - B) CRI-O y Docker
   - C) containerd y CRI-O
   - D) Docker, containerd y gVisor

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A) containerd con compatibilidad con CRI para Windows**

**Explicación:**
El runtime de contenedores admitido oficialmente para nodos Windows en Kubernetes es containerd con compatibilidad con CRI para Windows.

- **containerd:** es el runtime recomendado actualmente para nodos Windows. Es ligero y estable, y Kubernetes lo admite oficialmente en nodos Windows desde la versión 1.20.

CRI-O no se admite oficialmente en nodos Windows; es principalmente una implementación de CRI para contenedores Linux.

gVisor es un runtime de aislamiento para contenedores, pero actualmente no se admite en nodos Windows.

Al configurar los runtimes de contenedores en nodos Windows, verifica que sean compatibles con la versión de Kubernetes.
</details>

2. ¿Qué solución de red se necesita en un clúster Kubernetes mixto con nodos Windows y Linux?
   - A) Todos los complementos CNI admiten nodos Windows y Linux
   - B) Complementos CNI compatibles con Windows, como Flannel, Calico y Antrea
   - C) Los nodos Windows deben usar kubenet sin complementos CNI
   - D) Los nodos Windows siempre deben usar solo el modo de red del host

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Complementos CNI compatibles con Windows, como Flannel, Calico y Antrea**

**Explicación:**
En un clúster mixto con nodos Windows y Linux, debes usar complementos CNI (Container Network Interface) que admitan Windows. No todos son compatibles.

Entre los principales complementos CNI compatibles con nodos Windows se encuentran:

- **Flannel:** admite nodos Windows en modo de red overlay (VXLAN).
- **Calico:** admite nodos Windows en los modos BGP y VXLAN.
- **Antrea:** admite nodos Windows mediante OVS (Open vSwitch).

Azure CNI y AWS VPC CNI también admiten Windows en sus respectivos entornos.

Al configurar complementos CNI en nodos Windows, ten en cuenta lo siguiente:
- Windows usa una pila de red distinta de la de Linux.
- Algunas funciones de red pueden estar limitadas en Windows.
- Comprueba qué versiones de Windows admite el complemento y sus requisitos de configuración.

kubenet no se admite. Los Pods Windows normales no pueden usar hostNetwork; los Pods HostProcess requieren `hostNetwork: true`.
</details>

3. ¿Qué modo de aislamiento admite Kubernetes para los contenedores de aplicaciones Windows?
   - A) Aislamiento Hyper-V
   - B) Aislamiento de procesos
   - C) Aislamiento de máquina virtual
   - D) Aislamiento sandbox

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Aislamiento de procesos**

**Explicación:**
Kubernetes admite el aislamiento de procesos para contenedores de aplicaciones Windows. En este modo, los contenedores comparten el kernel del sistema operativo anfitrión y cada contenedor se ejecuta en un grupo de procesos aislado.

Características del aislamiento de procesos:
- Debe usarse la misma versión del kernel que en el sistema operativo anfitrión.
- Consume menos recursos y se inicia más rápido.
- Es parecido al modelo habitual de aislamiento de los contenedores Linux.

Windows también ofrece el aislamiento Hyper-V:
- Cada contenedor se ejecuta en una máquina virtual ligera.
- Puede usar una versión de kernel distinta de la del sistema anfitrión.
- Aísla más, pero consume más recursos.

**Kubernetes no admite el aislamiento Hyper-V y ninguna anotación de Pod lo habilita.** Esta explicación aporta contexto sobre Windows.

El aislamiento de máquina virtual no es un modo oficial de aislamiento de contenedores Windows, y «aislamiento sandbox» no es un término usado para ellos.
</details>

4. ¿Cuál de estas afirmaciones NO describe correctamente una limitación de los nodos Windows en Kubernetes?
   - A) No se pueden usar contenedores privilegiados
   - B) No se pueden usar volúmenes HostPath
   - C) Solo se admiten algunas funciones de SecurityContext para los Pods
   - D) Los contenedores Windows no pueden compartir namespaces de procesos

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) No se pueden usar volúmenes HostPath**

**Explicación:**
Los nodos Windows sí pueden usar volúmenes HostPath, por lo que esa afirmación es incorrecta.

Al usar HostPath en nodos Windows, debes seguir el formato de ruta de Windows:
```yaml
volumes:
- name: data
  hostPath:
    path: 'C:\data'
```

Las limitaciones reales de los nodos Windows en Kubernetes incluyen:

- **Modo privilegiado:** no se admite el indicador privileged. Los agentes de nodo de confianza que necesiten acceso al host pueden usar HostProcess.
- **SecurityContext:** solo se admiten algunas funciones en nodos Windows. Por ejemplo, no se admiten runAsUser, runAsGroup, fsGroup, seccomp ni SELinux.
- **Namespaces:** los contenedores de un mismo Pod comparten la red y localhost, pero no comparten namespaces de procesos ni sistemas de archivos raíz.

Otras limitaciones de los nodos Windows:
- Para ejecutar DaemonSets en todos los nodos Linux y Windows debes usar nodeSelector.
- Algunos controladores y tipos de almacenamiento pueden estar limitados.
- Es posible que las funciones alfa/beta específicas de Linux no funcionen en nodos Windows.
</details>

5. ¿Qué etiqueta identifica los nodos Windows en Kubernetes?
   - A) kubernetes.io/os=windows
   - B) beta.kubernetes.io/os=windows
   - C) node.kubernetes.io/windows=true
   - D) kubernetes.io/windows=enabled

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A) kubernetes.io/os=windows**

**Explicación:**
La etiqueta estándar para identificar nodos Windows es `kubernetes.io/os=windows`. Indica el sistema operativo del nodo y el scheduler la usa para ubicar los Pods en nodos apropiados.

Para programar Pods Windows en nodos Windows, usa nodeSelector:
```yaml
nodeSelector:
  kubernetes.io/os: windows
```

También puedes usar afinidad de nodos:
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

`beta.kubernetes.io/os=windows` se usó en versiones anteriores, pero está obsoleta.

`node.kubernetes.io/windows=true` y `kubernetes.io/windows=enabled` no son etiquetas estándar de Kubernetes.

Nota: los nodos Linux llevan la etiqueta `kubernetes.io/os=linux`.
</details>

6. ¿Qué imagen base de Microsoft ofrece una compatibilidad con las API de Windows más amplia que Nano Server para aplicaciones Windows tradicionales?
   - A) mcr.microsoft.com/windows/servercore
   - B) mcr.microsoft.com/windows/nanoserver
   - C) mcr.microsoft.com/dotnet/framework/runtime
   - D) mcr.microsoft.com/powershell

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A) mcr.microsoft.com/windows/servercore**

**Explicación:**
Kubernetes no elige una imagen base predeterminada. Para muchas aplicaciones Windows tradicionales, una opción adecuada es `mcr.microsoft.com/windows/servercore`. Esta imagen parte de Windows Server Core e incluye los componentes necesarios para ejecutar la mayoría de las aplicaciones Windows.

Principales imágenes base para contenedores Windows:

1. **Windows Server Core** (`mcr.microsoft.com/windows/servercore`):
   - El tamaño depende de la versión, las capas y la compresión.
   - Admite la mayoría de las aplicaciones Windows.
   - Incluye Windows PowerShell; si necesitas .NET Framework, selecciona aparte la imagen de runtime requerida.
   - Es la imagen base Windows más usada.

2. **Nano Server** (`mcr.microsoft.com/windows/nanoserver`):
   - El tamaño depende de la versión, las capas y la compresión.
   - Tiene compatibilidad limitada con las API de Windows.
   - Es adecuado para aplicaciones .NET Core.
   - Tiene una superficie de ataque pequeña.

3. **.NET Framework** (`mcr.microsoft.com/dotnet/framework/runtime`):
   - Imagen para aplicaciones .NET Framework.
   - Está basada en Server Core.
   - Incluye versiones específicas de .NET Framework.

4. **PowerShell** (`mcr.microsoft.com/powershell`):
   - Imagen para ejecutar scripts de PowerShell.
   - Hay variantes basadas en Nano Server y Server Core.

Al elegir una imagen de contenedor Windows, ten en cuenta los requisitos de la aplicación y las API de Windows necesarias, el tamaño y el tiempo de inicio, la seguridad y la compatibilidad de versiones (comprueba la etiqueta de la imagen).

Las imágenes de contenedor Windows deben tener la misma versión que el sistema anfitrión o ser compatibles con ella.
</details>

7. ¿Cuál es el método recomendado para desplegar DaemonSets en un clúster Kubernetes mixto con nodos Windows y Linux?
   - A) Usar un único DaemonSet en todos los nodos
   - B) Crear DaemonSets separados por sistema operativo y usar nodeSelector
   - C) Usar StatefulSet en lugar de DaemonSet para los nodos Windows
   - D) Añadir tolerations a todos los DaemonSets

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Crear DaemonSets separados por sistema operativo y usar nodeSelector**

**Explicación:**
En clústeres mixtos se recomienda crear DaemonSets separados para cada sistema operativo y usar nodeSelector.

Este enfoque es necesario porque:
- Los contenedores Windows y Linux usan formatos de imagen distintos.
- Una misma aplicación puede requerir una configuración diferente según el sistema operativo.
- Algunas funciones solo están disponibles en un sistema operativo.

Ejemplo de DaemonSet Windows:
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
      os:
        name: windows
      nodeSelector:
        kubernetes.io/os: windows
      containers:
      - name: agent
        image: contoso/windows-monitoring-agent:v1
```

Ejemplo de DaemonSet Linux:
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

Un solo DaemonSet puede hacer que los Pods no se inicien en ciertos nodos por incompatibilidad de imágenes.

Los DaemonSets sí pueden ejecutarse en nodos Windows; no hace falta sustituirlos por StatefulSets.

Las tolerations pueden permitir la programación en nodos con taints, pero no resuelven la compatibilidad entre sistemas operativos.
</details>

8. ¿Qué afirmación sobre la configuración DNS de los Pods en nodos Windows es correcta?
   - A) La configuración DNS no se admite en nodos Windows
   - B) Los nodos Windows deben usar Windows DNS Server en vez de CoreDNS
   - C) Los Pods Windows pueden usar CoreDNS con limitaciones en los sufijos DNS
   - D) Cada Pod requiere una configuración independiente de servidor DNS

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Los Pods Windows pueden usar CoreDNS con limitaciones en los sufijos DNS**

**Explicación:**
Los Pods Windows pueden usar CoreDNS, aunque Windows tiene limitaciones en los sufijos DNS. Usa el nombre simple del Service dentro del mismo namespace o el FQDN completo; los nombres parciales con puntos no usan la lista de búsqueda de Linux.

Configuración DNS en Pods Windows:
- Windows usa la configuración HNS/DNS y un único sufijo de namespace; no usa `/etc/resolv.conf`.
- Los Pods pueden consultar el servicio DNS del clúster (CoreDNS) para resolver los nombres de Services.
- Los campos `dnsPolicy` y `dnsConfig` permiten configurar DNS.

Ejemplo:
```yaml
apiVersion: v1
kind: Pod
metadata:
  name: windows-pod
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
    - "Start-Sleep -Seconds 3600"
  dnsPolicy: ClusterFirst
```

Consideraciones:
- El comportamiento del cliente DNS en contenedores Windows puede diferir ligeramente de Linux.
- Algunos comandos DNS, como nslookup y Resolve-DnsName, están disponibles de forma predeterminada.
- Comprueba que el complemento de red resuelva correctamente los nombres DNS.

No hace falta configurar un servidor DNS independiente ni usar Windows DNS Server en los nodos Windows. Kubernetes usa el mecanismo DNS estándar también para los Pods Windows.
</details>

9. ¿Qué afirmación sobre la comunicación entre Pods en nodos Windows es correcta?
   - A) No se admite la comunicación entre Pods en nodos Windows
   - B) Los Pods Windows solo se comunican con Pods del mismo nodo
   - C) Los Pods Windows no pueden comunicarse con Pods Linux
   - D) Los Pods Windows pueden comunicarse con los demás Pods mediante complementos CNI

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: D) Los Pods Windows pueden comunicarse con los demás Pods mediante complementos CNI**

**Explicación:**
Con los complementos CNI (Container Network Interface) adecuados, los Pods Windows pueden comunicarse con todos los demás Pods del clúster: en el mismo nodo Windows, en otros nodos Windows y en nodos Linux.

Características de la comunicación entre Pods en nodos Windows:
- Los Pods Windows pueden descubrir Services del clúster y acceder a ellos por nombre.
- Cada Pod recibe una dirección IP única dentro del rango de direcciones del clúster.
- La comunicación entre Pods depende de la implementación del complemento CNI elegido.

Los complementos CNI que admiten comunicación entre Pods en nodos Windows incluyen:
- Flannel (modo VXLAN)
- Calico
- Antrea
- Azure CNI
- AWS VPC CNI

Por ejemplo, con Flannel:
- Los Pods Windows se comunican con Pods de otros nodos mediante encapsulación VXLAN.
- Cada Pod recibe una IP dentro del CIDR del clúster.
- Las tablas de rutas dirigen las IP de los Pods a los nodos apropiados.

Ten en cuenta que algunas funciones avanzadas de red pueden estar limitadas en Windows, que la compatibilidad con NetworkPolicy depende del complemento CNI y que las reglas de Windows Firewall no deben bloquear el tráfico.

Los Pods Windows pueden comunicarse con Pods Linux; esto forma parte de las capacidades principales de Kubernetes.
</details>

10. ¿Qué afirmación sobre los límites de recursos de contenedores Windows en Kubernetes es correcta?
   - A) Los contenedores Windows no admiten límites de recursos
   - B) Admiten límites de CPU, pero no de memoria
   - C) Admiten límites de memoria, pero no de CPU
   - D) Admiten límites de CPU y memoria

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: D) Se admiten tanto los límites de CPU como los de memoria**

**Explicación:**
Los contenedores Windows en Kubernetes admiten límites de recursos de CPU y memoria. Los nodos Windows pueden solicitar y limitar recursos de los contenedores de forma similar a los nodos Linux.

Ejemplo de límites de recursos para contenedores Windows:
```yaml
apiVersion: v1
kind: Pod
metadata:
  name: windows-resource-demo
spec:
  os:
    name: windows
  nodeSelector:
    kubernetes.io/os: windows
  containers:
  - name: windows-container
    image: mcr.microsoft.com/windows/servercore:ltsc2022
    resources:
      requests:
        memory: "128Mi"
        cpu: "100m"
      limits:
        memory: "256Mi"
        cpu: "500m"
```

Características de la gestión de recursos para contenedores Windows:
- **Límites de CPU**: Windows aplica el uso compartido y los límites de CPU para administrar la asignación entre contenedores.
- Windows no tiene el OOM killer de Linux; si se agota la memoria disponible, pueden producirse errores de asignación o paginación y degradarse el rendimiento.
- **Monitoreo de recursos**: kubelet supervisa el uso de recursos de los contenedores Windows e informa a la API de Kubernetes.

Consideraciones sobre la gestión de recursos para contenedores Windows:
- La sobrecarga de recursos predeterminada de los contenedores Windows puede ser mayor que la de los contenedores Linux.
- La implementación exacta de los límites puede variar según la versión de Windows.
- Si el límite de memoria es demasiado bajo, los contenedores Windows quizá no funcionen correctamente.
- Kubernetes no admite el aislamiento Hyper-V.

Puedes supervisar el uso de recursos de los nodos Windows con `kubectl top pods` y `kubectl top nodes`.
</details>

## Preguntas de respuesta corta

1. Explica los principales pasos y requisitos para agregar nodos Windows a un clúster de Kubernetes.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:**

**Pasos para agregar nodos Windows a un clúster de Kubernetes:**

1. **Verificar los requisitos previos:**
   - Una combinación compatible de Kubernetes y Windows; en upstream, la versión 1.37 admite Windows Server 2022/2025.
   - El plano de control debe ejecutarse en nodos Linux.
   - Usa Windows Server 2022 para los ejemplos `ltsc2022` de esta respuesta.
   - Un complemento CNI compatible, como Flannel, Calico o Antrea.

2. **Configurar la red:**
   - Instala un complemento CNI compatible con nodos Windows.
   - Configura los CIDR del clúster y de los Services.
   - Ejemplo de configuración de Flannel en Linux; instala por separado el CNI para Windows:
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
   - Instala y actualiza Windows Server.
   - Habilita las funciones de Windows necesarias:
     ```powershell
     Install-WindowsFeature -Name Containers
     Restart-Computer -Force
     ```
   - Instala el runtime de contenedores; se recomienda containerd:
     ```powershell
     # Use the reviewed sig-windows-tools installation procedure in the chapter.
     # Install-Containerd.ps1: supported runtime; PrepareNode.ps1: matching kubeadm/kubelet.
     # Do not start kubelet with an empty configuration.
     ```

4. **Instalar kubelet y kube-proxy:**
   - Descarga los binarios de Kubernetes:
     ```powershell
     # Use the reviewed sig-windows-tools installation procedure in the chapter.
     # Install-Containerd.ps1: supported runtime; PrepareNode.ps1: matching kubeadm/kubelet.
     # Do not start kubelet with an empty configuration.
     ```
   - Crea el archivo de configuración de kubelet:
     ```powershell
     # Use the reviewed sig-windows-tools installation procedure in the chapter.
     # Install-Containerd.ps1: supported runtime; PrepareNode.ps1: matching kubeadm/kubelet.
     # Do not start kubelet with an empty configuration.
     ```
   - Registra e inicia el servicio kubelet:
     ```powershell
     # Use the reviewed sig-windows-tools installation procedure in the chapter.
     # Install-Containerd.ps1: supported runtime; PrepareNode.ps1: matching kubeadm/kubelet.
     # Do not start kubelet with an empty configuration.
     ```
   - Configura e inicia kube-proxy, que normalmente se implementa como DaemonSet.

5. **Unir el nodo al clúster:**
   - Ejecuta `kubeadm join` o configura manualmente los certificados TLS y kubeconfig.
   - Verifica que el nodo se haya registrado en el clúster:
     ```bash
     kubectl get nodes
     ```

6. **Agregar etiquetas al nodo:**
   - Si la etiqueta no se agregó automáticamente, asigna al nodo Windows la etiqueta del sistema operativo:
     ```bash
     kubectl label node <windows-node-name> kubernetes.io/os=windows
     ```

7. **Implementar una carga de prueba:**
   - Implementa un Pod sencillo que ejecute un contenedor Windows:
     ```yaml
     apiVersion: v1
     kind: Pod
     metadata:
       name: windows-test-pod
     spec:
       os:
         name: windows
       nodeSelector:
         kubernetes.io/os: windows
       containers:
       - name: windows-server
         image: mcr.microsoft.com/windows/servercore:ltsc2022
         command:
         - powershell.exe
         - -Command
         - "Start-Sleep -Seconds 3600"
     ```

**Consideraciones clave:**

1. **Compatibilidad de versiones:**
   - La versión de Windows Server debe ser compatible con la versión de la imagen del contenedor.
   - Comprueba la versión de Kubernetes y las funciones admitidas para Windows.

2. **Red:**
   - Usa complementos CNI compatibles con nodos Windows.
   - Comprueba la compatibilidad con NetworkPolicy.
   - Verifica los requisitos de puertos de kubelet, containerd, CNI, etc.

3. **Almacenamiento:**
   - Comprueba qué controladores y tipos de volúmenes admiten los nodos Windows.
   - Verifica la compatibilidad del controlador CSI.

4. **Monitoreo y registros:**
   - Implementa agentes de monitoreo adecuados para nodos Windows.
   - Configura la recopilación de registros de eventos de Windows.

5. **Seguridad:**
   - Configura las reglas del firewall de Windows.
   - Si es necesario, configura cuentas de servicio administradas de grupo (gMSA).
   - Configura los grupos de seguridad de red.

6. **Automatización:**
   - Automatiza el aprovisionamiento de nodos Windows con Ansible, PowerShell DSC u otras herramientas.
   - Define una estrategia para actualizar los nodos.
</details>

2. Explica las principales diferencias entre los contenedores Windows y Linux, y cómo gestionar esas diferencias en Kubernetes.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:**

**Principales diferencias entre los contenedores Windows y Linux:**

1. **Tecnología subyacente:**
   - **Contenedores Linux**: utilizan namespaces, cgroups y funciones del kernel de Linux para aislar procesos.
   - **Contenedores Windows**: utilizan tecnologías de aislamiento de Windows, como Job Objects y aislamiento Hyper-V.

2. **Estructura de las imágenes:**
   - **Contenedores Linux**: suelen ser relativamente pequeños, de decenas a cientos de MB.
   - **Contenedores Windows**: suelen ocupar varios GB y sus imágenes base son más grandes.

3. **Modos de aislamiento:**
   - **Contenedores Linux**: normalmente usan namespaces; también existen runtimes alternativos de aislamiento.
   - **Contenedores Windows**: Kubernetes admite el aislamiento de procesos; Hyper-V queda fuera de lo que admite Kubernetes.

4. **Sistema de archivos:**
   - **Contenedores Linux**: sistema de archivos por capas, como OverlayFS.
   - **Contenedores Windows**: controlador de filtros basado en NTFS.

5. **Red:**
   - **Contenedores Linux**: admiten diversos modos de red y controladores.
   - **Contenedores Windows**: tienen modos de red más limitados y solo admiten ciertos complementos CNI.

6. **Gestión de recursos:**
   - **Contenedores Linux**: control granular de recursos mediante cgroups.
   - **Contenedores Windows**: control mediante Job Objects, con algunas limitaciones.

7. **Contexto de seguridad:**
   - **Contenedores Linux**: ofrecen varias opciones de contexto de seguridad, como SELinux y AppArmor.
   - **Contenedores Windows**: ofrecen menos opciones; no admiten contenedores privilegiados.

8. **Dependencia del sistema operativo del host:**
   - **Contenedores Linux**: pueden ejecutarse en distintas distribuciones Linux.
   - **Contenedores Windows**: requieren una versión igual o compatible con la del sistema operativo del host.

**Cómo gestionar estas diferencias en Kubernetes:**

1. **Selección y programación de nodos:**
   - **Usar etiquetas de nodo**: `kubernetes.io/os=windows` o `kubernetes.io/os=linux`.
   - **Usar `nodeSelector`**:
     ```yaml
     os:
       name: windows
     nodeSelector:
       kubernetes.io/os: windows
     ```
   - **Usar afinidad de nodo**:
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

2. **Separación de cargas de trabajo:**
   - **Crear Deployments específicos para cada sistema operativo**:
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
           os:
             name: windows
           nodeSelector:
             kubernetes.io/os: windows
           containers:
           - name: windows-app
             image: myregistry/windows-app:latest

     ---
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

3. **Gestión de DaemonSets:**
   - **Crear DaemonSets específicos para cada sistema operativo**:
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
           os:
             name: windows
           nodeSelector:
             kubernetes.io/os: windows
           containers:
           - name: agent
             image: myregistry/windows-agent:latest
     ```

4. **Gestión de imágenes:**
   - **Usar imágenes multiarquitectura**: admite varios sistemas operativos y arquitecturas con la misma etiqueta.
   - **Usar etiquetas de imagen específicas del sistema operativo**: `myapp:linux` y `myapp:windows`.
   - **Definir la política de extracción de imágenes**: `imagePullPolicy: Always`.

5. **Solicitudes y límites de recursos:**
   - **Definir recursos adecuados para cada sistema operativo**:
     ```yaml
     resources:
       requests:
         memory: "2Gi"  # Windows containers typically need more memory
         cpu: "500m"
       limits:
         memory: "4Gi"
         cpu: "1"
     ```

6. **Red:**
   - **Elegir un complemento CNI compatible**: por ejemplo, Flannel, Calico o Antrea.
   - **Tener en cuenta el sistema operativo al aplicar NetworkPolicy**:
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
   - **Usar clases de almacenamiento compatibles con el sistema operativo**:
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

8. **Contexto de seguridad:**
   - **Aplicar una configuración de seguridad adecuada para cada sistema operativo**:
     ```yaml
     # Security context for Linux pods
     securityContext:
       runAsUser: 1000
       runAsGroup: 3000
       fsGroup: 2000

     # These Linux-only fields are rejected with spec.os.name: windows.
     ```

9. **Monitoreo y registros:**
   - **Implementar agentes de monitoreo específicos para cada sistema operativo.**
   - **Ajustar las rutas de recopilación de registros**: Windows (`C:\k\logs`) frente a Linux (`/var/log`).

10. **Pipelines de CI/CD:**
    - **Configurar pipelines de compilación y pruebas específicos para cada sistema operativo.**
    - **Definir una estrategia de implementación para varios sistemas operativos.**
</details>


3. Explica cómo se usan las cuentas de servicio administradas de grupo (gMSA) en contenedores Windows y qué ventajas ofrecen.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:**

**Descripción general de gMSA:**

Las cuentas de servicio administradas de grupo (gMSA) son cuentas de Active Directory especiales para autenticar servicios en dominios Windows. En Kubernetes, permiten ejecutar contenedores Windows con aplicaciones que necesitan autenticación de dominio. Son útiles, por ejemplo, para:

- Aplicaciones .NET que necesitan integrarse con Active Directory.
- Conexiones con SQL Server que usan autenticación de Windows.
- Servicios que requieren autenticación Kerberos.
- Aplicaciones que necesitan acceder a recursos del dominio.

**Cómo usar gMSA en contenedores Windows:**

1. Prepara la conectividad con Active Directory y DNS, y un método de recuperación de credenciales compatible: hosts unidos al dominio o un proveedor de identidad portátil configurado por separado. Los contenedores no pueden unirse al dominio.
2. Comprueba `Get-KdsRootKey`. Un administrador de Active Directory crea una clave solo si hace falta y deja tiempo para su replicación, que puede tardar hasta 10 horas. Retroceder diez horas la fecha efectiva solo corresponde a un entorno de prueba con un único controlador de dominio.
3. Autoriza la recuperación de contraseñas a un grupo específico de hosts autorizados, no a todos los equipos del dominio. Genera los valores reales de SID, GUID, DNS y NetBIOS con el módulo CredentialSpec y `New-CredentialSpec`.
4. Instala la CRD `GMSACredentialSpec` y los webhooks de mutación y validación. Incluye el JSON generado en `GMSACredentialSpec.credspec` con `windows.k8s.io/v1`. No es un Secret y no contiene la contraseña de gMSA.
5. Concede al ServiceAccount permiso `use` sobre el recurso con nombre y configura `serviceAccountName` y `windowsOptions.gmsaCredentialSpecName` en el Pod.
6. Valida la autenticación Kerberos de la aplicación y usa `klist`. `whoami` muestra el usuario local del proceso, no la identidad de red gMSA.

Consulta el [procedimiento de gMSA del capítulo](../../core/10-windows-in-kubernetes.md) para ver el ejemplo completo del recurso generado y RBAC.

**Ventajas de usar gMSA:**

1. **Mayor seguridad:**
   - Evita incluir credenciales codificadas directamente en los contenedores.
   - Automatiza la administración y rotación de contraseñas.
   - Permite aplicar el principio de privilegio mínimo.

2. **Integración con Active Directory:**
   - Permite contenerizar aplicaciones existentes que usan autenticación de Windows.
   - Admite autenticación Kerberos y NTLM.
   - Facilita el acceso a recursos del dominio.

3. **Administración centralizada de identidades:**
   - Unifica la administración de identidades mediante Active Directory.
   - Permite aplicar directivas de grupo.
   - Mejora la auditoría y el cumplimiento.

4. **Compatibilidad de aplicaciones:**
   - Admite aplicaciones .NET heredadas que requieren autenticación de dominio.
   - Admite conexiones con SQL Server mediante autenticación integrada de Windows.
   - Admite autenticación de Windows para aplicaciones web de IIS.

5. **Operaciones simplificadas:**
   - Automatiza la administración de credenciales.
   - Las credenciales se mantienen al reiniciar los contenedores.
   - Se puede compartir la misma identidad entre varios contenedores.

**Consideraciones al usar gMSA:**

1. **Requisitos de red:**
   - Los nodos Windows necesitan conectividad de red con los controladores de dominio.
   - Se requiere una configuración DNS correcta.
   - Deben estar abiertos los puertos necesarios, como los de Kerberos y LDAP.

2. **Administración de permisos:**
   - Concede a gMSA solo los permisos mínimos necesarios.
   - Configura las pertenencias a grupos adecuadas.
   - Revisa periódicamente los permisos.

3. **Escalabilidad:**
   - En clústeres grandes, ten en cuenta la carga de los controladores de dominio.
   - Usa varias cuentas gMSA para separar permisos.

4. **Solución de problemas:**
   - Diagnostica los problemas de conectividad con el dominio.
   - Verifica la configuración de Credential Spec.
   - Revisa los registros del runtime de contenedores.
</details>

4. Explica cómo configurar el registro y el monitoreo de nodos Windows en Kubernetes y en qué se diferencian de los nodos Linux.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:**

**Configuración del registro y monitoreo de nodos Windows:**

**1. Configuración del registro:**

**Principales fuentes de registros de nodos Windows:**
- Registros de eventos de Windows (System, Application y Security).
- Eventos ETW (Event Tracing for Windows).
- Archivos de registro de aplicaciones, normalmente en la unidad `C:\`.
- Registros de kubelet y del runtime de contenedores, normalmente en `C:\k\logs` o rutas similares.

**Métodos para configurar el registro de nodos Windows:**

1. **Configurar Fluent Bit o Fluentd:**
   Lee los registros de eventos del host con el servicio Fluent Bit para Windows descrito en el capítulo o con un recopilador HostProcess revisado. Montar archivos `.evtx` en un contenedor normal no le da acceso a la API del host que usa `winlog`. La entrada siguiente necesita permiso para leer Security y un directorio persistente para sus puntos de control.

2. **Configurar la recopilación del registro de eventos de Windows:**
   ```ini
   # Fluent Bit Windows configuration
   [INPUT]
       Name            winlog
       Channels        System,Application,Security
       Interval_Sec    1
       DB              C:\fluent-bit\winlog.db

   [OUTPUT]
       Name            es
       Match           *
       Host            elasticsearch-master
       Port            9200
       Index           windows_logs
       Suppress_Type_Name On
       tls             On
       tls.verify      On
   ```

3. **Recopilar los registros de los contenedores:**
   - Ruta de registros de containerd: `C:\var\log\containers`.
   - Ruta de registros de kubelet: `C:\k\logs` o el registro de eventos de Windows.

**2. Configuración del monitoreo:**

**Métricas principales para monitorear los nodos Windows:**
- Uso de CPU, memoria y disco.
- Tráfico de red.
- Cantidad de procesos.
- Uso del archivo de paginación.
- Uso de recursos de los contenedores.

**Métodos para configurar el monitoreo de nodos Windows:**

1. **Configurar Windows Exporter de Prometheus:**
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
         os:
           name: windows
         nodeSelector:
           kubernetes.io/os: windows
         containers:
         - name: windows-exporter
           image: ghcr.io/prometheus-community/windows-exporter:REPLACE_WITH_TESTED_RELEASE
           args:
           - --collectors.enabled=cpu,memory,logical_disk,net,service,os,system,container
           ports:
           - containerPort: 9182
             name: metrics
             protocol: TCP
         hostNetwork: true
         securityContext:
           windowsOptions:
             hostProcess: true
             runAsUserName: NT AUTHORITY\SYSTEM
   ```

2. **Configurar el scraping de Prometheus:**
   ```yaml
   apiVersion: v1
   kind: Service
   metadata:
     name: windows-exporter
     namespace: monitoring
     labels:
       app: windows-exporter
   spec:
     selector:
       app: windows-exporter
     ports:
     - name: metrics
       port: 9182
       targetPort: metrics
   ---
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

3. **Configurar un dashboard de Grafana:**
   - Crea dashboards específicos para las métricas de nodos Windows.
   - Agrega paneles propios de Windows, por ejemplo, sobre el uso del archivo de paginación y el estado de los servicios.

**3. Herramientas de diagnóstico:**

**Herramientas para diagnosticar nodos Windows:**
- Comandos de PowerShell (`Get-Process`, `Get-Service`, `Get-EventLog`).
- Windows Performance Monitor (PerfMon).
- Event Viewer.
- El comando `kubectl debug`, con compatibilidad limitada en nodos Windows.

**Ejemplos de diagnóstico de nodos Windows:**
```powershell
# Check kubelet logs
Get-EventLog -LogName Application -Source kubelet -Newest 50

# Check containerd status
Get-Service containerd

# Verify network connectivity
Test-NetConnection -ComputerName api.kubernetes.cluster -Port 443
```

**Diferencias clave respecto de los nodos Linux:**

1. **Ubicación de almacenamiento de registros:**
   - **Linux**: se guardan como archivos de texto en `/var/log/`.
   - **Windows**: se usan registros de eventos de Windows (formato binario) y archivos de texto en varias ubicaciones.

2. **Mecanismo de recopilación de registros:**
   - **Linux**: lo habitual es recopilar registros basados en archivos (tail, read).
   - **Windows**: se necesita la API de Windows Event Log.

3. **Recopilación de métricas:**
   - **Linux**: se recopilan métricas de los sistemas de archivos `/proc` y `/sys`.
   - **Windows**: se usan WMI (Windows Management Instrumentation) o la API Performance Counter.

4. **Registros de contenedores:**
   - **Linux**: la salida estándar y de error se redirige a archivos.
   - **Windows**: stdout y stderr también usan registros CRI; los registros ETW o de archivos requieren un recopilador de la aplicación o del host.

5. **Monitoreo de recursos:**
   - **Linux**: el uso de recursos de los contenedores se monitorea mediante cgroups.
   - **Windows**: se monitorea mediante Job Objects; algunas métricas se calculan de forma distinta.

6. **Agentes de monitoreo:**
   - **Linux**: hay diversos agentes, como node-exporter y cAdvisor.
   - **Windows**: hay menos agentes y se necesitan agentes específicos para Windows.

7. **Herramientas de diagnóstico:**
   - **Linux**: dispone de diversas herramientas de CLI, como ps, top, netstat y strace.
   - **Windows**: se usan comandos de PowerShell y herramientas gráficas; las herramientas de CLI son más limitadas.

**Prácticas recomendadas:**

1. **Solución integrada de registro:**
   - Usa EFK (Elasticsearch, Fluent Bit, Kibana) o la pila ELK.
   - Configura por separado los nodos Windows y Linux.

2. **Solución integrada de monitoreo:**
   - Monitorea todos los nodos con Prometheus y Grafana.
   - Crea dashboards específicos para cada sistema operativo.

3. **Configuración de alertas:**
   - Configura reglas de alerta para eventos específicos de Windows.
   - Monitorea el estado de los servicios críticos de Windows.

4. **Política de retención de registros:**
   - Configura el tamaño y el período de retención de los registros de eventos de Windows.
   - Configura la rotación de registros.

5. **Monitoreo de seguridad:**
   - Recopila y analiza los registros de eventos de seguridad de Windows.
   - Monitorea los cambios de permisos y los intentos de inicio de sesión.

Crea el namespace de monitoreo y sustituye la etiqueta del exporter por una versión publicada y probada. HostProcess se ejecuta con privilegios del host: limita la excepción de PSS y el acceso de firewall al puerto 9182 a los orígenes de Prometheus. Comprueba las rutas y canales de registros del host según la distribución; en EKS, los registros de kubelet y kube-proxy se registran en EKS Windows. El ejemplo de Elasticsearch también requiere una CA de confianza y la configuración de autenticación.
</details>

5. Explica las opciones de almacenamiento y cómo configurar los montajes de volumen para contenedores Windows en Kubernetes.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:**

**Opciones de almacenamiento para contenedores Windows:**

**1. Tipos básicos de volumen:**

1. **emptyDir:**
   - Almacena datos temporales durante la vida del Pod.
   - Se crea en el volumen NTFS local del nodo Windows.
   - Los datos se eliminan cuando se elimina el Pod.

   ```yaml
   volumes:
   - name: temp-data
     emptyDir: {}
   ```

2. **hostPath:**
   - Da acceso directo al sistema de archivos del nodo Windows.
   - Escapa las barras invertidas solo en cadenas YAML entre comillas dobles; en rutas sin comillas o entre comillas simples, usa una sola barra invertida.
   - Los datos no se pueden compartir entre nodos.

   ```yaml
   volumes:
   - name: logs
     hostPath:
       path: 'C:\Logs'
       type: DirectoryOrCreate
   ```

3. **configMap y Secret:**
   - Almacenan datos de configuración e información confidencial.
   - Funcionan de la misma forma para los contenedores Windows.
   - En Windows, los permisos de los archivos se aplican de forma distinta.

   ```yaml
   volumes:
   - name: config
     configMap:
       name: app-config
   ```

4. **PersistentVolumeClaim (PVC):**
   - Solicita almacenamiento persistente.
   - Requiere una StorageClass compatible con Windows.
   - Hay que verificar la compatibilidad del controlador CSI.

   ```yaml
   volumes:
   - name: data
     persistentVolumeClaim:
       claimName: windows-pvc
   ```

**2. Soluciones de almacenamiento compatibles con contenedores Windows:**

1. **Azure Disk/Files (AKS):**
   - Azure Kubernetes Service admite nodos Windows.
   - Se puede usar Azure Files basado en el protocolo SMB.
   - El controlador CSI de Azure Disk es compatible.

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
   - Amazon EKS admite nodos Windows.
   - Está disponible el controlador CSI de EBS.
   - El acceso está limitado a una sola zona de disponibilidad (AZ).

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
   - Sistema de archivos de red adecuado para entornos Windows.
   - Requiere un controlador CSI para SMB compatible con Windows.
   - Admite acceso ReadWriteMany desde varios Pods.

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
   - Que Windows admita iSCSI no implica que se admita el complemento de volumen integrado `iscsi` de Kubernetes. Usa un controlador CSI del proveedor de almacenamiento que indique expresamente que admite volúmenes con sistema de archivos Windows. Los Pods Windows no admiten `volumeDevices` de bloques sin formato.

**3. Configuración de montajes de volumen para contenedores Windows:**

1. **Rutas de montaje de volumen:**
   - Los contenedores Windows usan el formato de rutas de Windows.
   - Normalmente usan rutas dentro de la unidad `C:\`.
   - Escapa las barras invertidas solo en cadenas YAML entre comillas dobles; en rutas sin comillas o entre comillas simples, usa una sola barra invertida.

   ```yaml
   volumeMounts:
   - name: data
     mountPath: 'C:\data'
   ```

2. **Montajes de solo lectura:**
   - Son compatibles con contenedores Windows.
   - Se aplican mediante permisos NTFS.

   ```yaml
   volumeMounts:
   - name: config
     mountPath: 'C:\config'
     readOnly: true
   ```

3. **Montajes de subPath:**
   - Permiten montar solo subrutas específicas de los volúmenes.
   - Ten en cuenta los separadores de rutas de Windows.

   ```yaml
   volumeMounts:
   - name: shared-data
     mountPath: 'C:\app\logs'
     subPath: logs
   ```

**4. Ejemplos de configuración de almacenamiento para contenedores Windows:**

1. **Configuración de una aplicación web:**
   ```yaml
   apiVersion: v1
   kind: Pod
   metadata:
     name: windows-web-app
   spec:
     os:
       name: windows
     nodeSelector:
       kubernetes.io/os: windows
     containers:
     - name: web
       image: mcr.microsoft.com/windows/servercore/iis:windowsservercore-ltsc2022
       volumeMounts:
       - name: website
         mountPath: 'C:\inetpub\wwwroot'
       - name: logs
         mountPath: 'C:\inetpub\logs'
       - name: config
         mountPath: 'C:\config'
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

2. **Configuración de una base de datos:**
   ```yaml
   apiVersion: v1
   kind: Pod
   metadata:
     name: linux-sql-for-windows-apps
   spec:
     nodeSelector:
       kubernetes.io/os: linux
       kubernetes.io/arch: amd64
     containers:
     - name: sql
       image: mcr.microsoft.com/mssql/server:2022-latest
       env:
       - name: ACCEPT_EULA
         value: "Y"
       - name: MSSQL_SA_PASSWORD
         valueFrom:
           secretKeyRef:
             name: sql-credentials
             key: sa-password
       volumeMounts:
       - name: data
         mountPath: /var/opt/mssql/data
       - name: backup
         mountPath: /var/opt/mssql/backup
     volumes:
     - name: data
       persistentVolumeClaim:
         claimName: sql-data-pvc
     - name: backup
       persistentVolumeClaim:
         claimName: sql-backup-pvc
     os:
       name: linux
   ```

**5. Consideraciones sobre el almacenamiento de contenedores Windows:**

1. **Separadores de rutas:**
   - Escapa las barras invertidas solo en cadenas YAML entre comillas dobles; en rutas sin comillas o entre comillas simples, usa una sola barra invertida.
   - También se pueden usar barras diagonales (`/`), pero hay que comprobar que la aplicación sea compatible.

2. **Permisos de archivos:**
   - Windows usa el modelo de permisos NTFS.
   - No se pueden definir permisos como `chmod` o `chown` en Linux.
   - Los permisos dentro de los contenedores dependen del contexto de usuario del contenedor.

3. **Rendimiento:**
   - El almacenamiento de red SMB/CIFS puede añadir latencia.
   - Para requisitos de alto rendimiento se recomienda almacenamiento local o almacenamiento de bloques conectado directamente.

4. **Compatibilidad de StorageClass:**
   - Comprueba qué StorageClasses son compatibles con nodos Windows.
   - Verifica que los controladores CSI admitan Windows.

5. **Copia de seguridad y recuperación:**
   - Considera la integración con Windows Volume Shadow Copy Service (VSS).
   - Implementa mecanismos de copia de seguridad coherentes con la aplicación.

La imagen de contenedor de SQL Server se ejecuta en Linux; las aplicaciones Windows se conectan a ella por la red. Prepara PVC compatibles con Linux, permisos de escritura para el proceso de SQL y el Secret existente `sql-credentials`.

Primero crea las StorageClasses del ejemplo. Una StorageClass de EBS para Windows necesita NTFS y `WaitForFirstConsumer`; el nombre por sí solo no instala un controlador ni crea la clase.
</details>

## Preguntas prácticas

1. Escribe un manifiesto de Deployment que cumpla estos requisitos en un clúster de Kubernetes con nodos Windows y Linux:
   - Nombre de la aplicación: `web-app`.
   - Imagen del contenedor Windows: `mcr.microsoft.com/windows/servercore/iis:windowsservercore-ltsc2022`.
   - Réplicas: 2.
   - Puerto: 80.
   - Variable de entorno: `WEBSITE_NAME=MyWindowsApp`.
   - Volumen: monta el ConfigMap `web-config` en `C:\inetpub\wwwroot\web.config`.

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
      os:
        name: windows
      nodeSelector:
        kubernetes.io/os: windows
      containers:
      - name: iis
        image: mcr.microsoft.com/windows/servercore/iis:windowsservercore-ltsc2022
        ports:
        - containerPort: 80
        env:
        - name: WEBSITE_NAME
          value: "MyWindowsApp"
        volumeMounts:
        - name: config-volume
          mountPath: 'C:\inetpub\wwwroot\web.config'
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

1. **Recurso Deployment:**
   - Usa `nodeSelector` para programar el Pod solo en nodos Windows.
   - Define las 2 réplicas solicitadas.
   - Usa la imagen del servidor web IIS.

2. **Configuración del contenedor:**
   - Expone el puerto 80.
   - Define la variable de entorno `WEBSITE_NAME`.
   - Monta el ConfigMap en una ruta de archivo específica usando el formato de rutas de Windows.

3. **Configuración del volumen:**
   - Monta el ConfigMap como volumen.
   - Usa `subPath` para montar una clave específica del ConfigMap como archivo.

4. **Definición del Service:**
   - Crea un Service ClusterIP para acceder a la aplicación por el puerto 80.

**Notas:**
- Escapa las barras invertidas solo en cadenas YAML entre comillas dobles; en rutas sin comillas o entre comillas simples, usa una sola barra invertida.
- Los contenedores Windows pueden requerir más recursos que los Linux. En producción, conviene definir solicitudes y límites de recursos adecuados.
- Definir `WEBSITE_NAME` no cambia por sí solo el nombre del sitio de IIS. Agrega la clave correspondiente a `web.config` en el ConfigMap existente `web-config`; los montajes `subPath` no se actualizan automáticamente.
</details>

2. Escribe manifiestos de DaemonSet para implementar agentes de monitoreo en nodos Windows y Linux. Cada sistema operativo debe usar imágenes y configuración adecuadas.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:**

```yaml
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
      hostNetwork: true
      hostPID: true
      dnsPolicy: ClusterFirstWithHostNet
---
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
      os:
        name: windows
      nodeSelector:
        kubernetes.io/os: windows
      containers:
      - name: agent
        image: ghcr.io/prometheus-community/windows-exporter:REPLACE_WITH_TESTED_RELEASE
        ports:
        - containerPort: 9182
          name: metrics
        args:
        - --collectors.enabled=cpu,memory,logical_disk,net,service,os,system,container
      hostNetwork: true
      securityContext:
        windowsOptions:
          hostProcess: true
          runAsUserName: NT AUTHORITY\SYSTEM
---
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
  - name: metrics
    port: 9100
    targetPort: metrics
    protocol: TCP
  selector:
    app: monitoring-agent
```

**Explicación:**

1. **DaemonSet para nodos Linux:**
   - Usa `nodeSelector` para programar Pods solo en nodos Linux.
   - Usa la imagen de Prometheus Node Exporter.
   - Monta los directorios `/proc`, `/sys` y `/` del host para recopilar métricas del sistema.
   - Configura el contexto de seguridad para ejecutarse como usuario no root.

2. **DaemonSet para nodos Windows:**
   - Usa `nodeSelector` para programar Pods solo en nodos Windows.
   - Usa la imagen de Windows Exporter.
   - Indica los recopiladores de métricas que se van a activar.
   - Aplica configuración específica de Windows.

3. **Service común:**
   - Crea un Service que selecciona los Pods de ambos DaemonSets.
   - Usa el `targetPort` con nombre para resolver, según el endpoint, el puerto 9100 de Linux o el 9182 de Windows.
   - Prometheus puede recopilar las métricas a través de este Service.

**Notas:**
- Es importante usar imágenes y configuración adecuadas para cada sistema operativo.
- Como la recopilación de métricas difiere entre nodos Linux y Windows, se usan DaemonSets separados.
- Las etiquetas de sistema operativo ayudan a filtrar y visualizar métricas en el sistema de monitoreo.
- En producción se necesita configuración adicional de solicitudes y límites de recursos, contextos de seguridad y cuentas de servicio.
- Crea el namespace de monitoreo y sustituye la etiqueta del exporter por una versión publicada y probada. HostProcess se ejecuta con privilegios del host: limita la excepción de PSS y el acceso de firewall al puerto 9182 a los orígenes de Prometheus. Prometheus debe descubrir y recopilar métricas de cada endpoint del Service.
</details>

3. Escribe un manifiesto de Pod para implementar una aplicación .NET que use autenticación de Active Directory en un contenedor Windows. Debe usar cuentas de servicio administradas de grupo (gMSA).

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:**

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: ad-auth-app
  labels:
    app: ad-auth-app
spec:
  os:
    name: windows
  nodeSelector:
    kubernetes.io/os: windows
  securityContext:
    windowsOptions:
      gmsaCredentialSpecName: gmsa-cred-spec
  containers:
  - name: dotnet-app
    image: myregistry/ad-auth-app:latest
    ports:
    - containerPort: 80
    env:
    - name: ASPNETCORE_ENVIRONMENT
      value: Production
    volumeMounts:
    - name: app-config
      mountPath: C:\app\appsettings.json
      subPath: appsettings.json
    resources:
      requests:
        memory: 2Gi
        cpu: 500m
      limits:
        memory: 4Gi
        cpu: 1000m
  volumes:
  - name: app-config
    configMap:
      name: ad-auth-app-config
  serviceAccountName: windows-app
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: ad-auth-app-config
data:
  appsettings.json: "{\n  \"Logging\": {\n    \"LogLevel\": {\n      \"Default\":\
    \ \"Information\",\n      \"Microsoft\": \"Warning\"\n    }\n  },\n  \"ConnectionStrings\"\
    : {\n    \"DefaultConnection\": \"Server=sql-server;Database=AppDB;Integrated\
    \ Security=True;\"\n  },\n  \"ActiveDirectory\": {\n    \"Domain\": \"example.com\"\
    ,\n    \"UseWindowsAuthentication\": true\n  }\n}\n"
---
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

1. **GMSACredentialSpec y autorización:**
   - El recurso previo `GMSACredentialSpec` contiene metadatos de credenciales generados, no la contraseña.
   - El webhook amplía la especificación con nombre después de comprobar el permiso `use` del ServiceAccount.

2. **Configuración del Pod Windows:**
   - Usa `nodeSelector` para programar el Pod en nodos Windows.
   - Hace referencia a la especificación de credenciales gMSA mediante `securityContext.windowsOptions.gmsaCredentialSpecName`.
   - Usa una imagen de la aplicación .NET.
   - Define solicitudes y límites de recursos adecuados.

3. **Volúmenes y configuración:**
   - Proporciona la configuración de la aplicación mediante un ConfigMap.
   - Monta el archivo de configuración con el formato de rutas de Windows.
   - Incluye una cadena de conexión a SQL Server con autenticación integrada de Windows.

4. **Definición del Service:**
   - Crea un Service ClusterIP para acceder a la aplicación.

**Requisitos previos para configurar gMSA:**

Primero crea el recurso `gmsa-cred-spec` del capítulo, el ServiceAccount `windows-app` y la concesión RBAC `use` limitada al nombre del recurso. Se requieren la CRD y ambos webhooks. Compila y valida la imagen y configuración personalizadas para Windows Server 2022. gMSA proporciona credenciales de red; la aplicación también debe usar autenticación de Windows. Los montajes `subPath` de ConfigMap no se actualizan automáticamente; vuelve a crear el Pod después de cambiar la configuración.
</details>

4. Escribe manifiestos de NetworkPolicy que cumplan estos requisitos en un clúster con nodos Windows y Linux:
   - Los Pods de la aplicación web Windows (etiqueta `app=windows-web`) solo pueden acceder a los Pods de la base de datos Linux (etiqueta `app=linux-db`).
   - Los Pods de la base de datos solo permiten acceso por el puerto 3306.
   - Se puede acceder a los Pods de la aplicación web desde el exterior por el puerto 80.

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

1. **NetworkPolicy de la aplicación web Windows:**
   - Se aplica a los Pods con la etiqueta `app=windows-web`.
   - **Regla de entrada**: permite conexiones de cualquier origen por el puerto 80.
   - **Regla de salida**: permite conexiones solo al puerto 3306 de Pods con la etiqueta `app=linux-db`.

2. **NetworkPolicy de la base de datos Linux:**
   - Se aplica a los Pods con la etiqueta `app=linux-db`.
   - **Regla de entrada**: permite conexiones por el puerto 3306 solo desde Pods con la etiqueta `app=windows-web`.

**Notas:**
- Para que funcionen, las políticas requieren un complemento CNI compatible con NetworkPolicy, como Calico o Antrea.
- La compatibilidad con NetworkPolicy en nodos Windows puede variar según el complemento CNI.
- El ejemplo supone que todos los recursos están en el namespace `default`; en entornos reales se deben indicar los namespaces adecuados.
- En producción pueden hacer falta reglas de salida adicionales para DNS y el acceso a servicios externos, entre otros.

**Ejemplos de Deployment:**

Pods de la aplicación web Windows:
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
      os:
        name: windows
      nodeSelector:
        kubernetes.io/os: windows
      containers:
      - name: web
        image: mcr.microsoft.com/windows/servercore/iis:windowsservercore-ltsc2022
        ports:
        - containerPort: 80
```

Pods de la base de datos Linux:
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

Las reglas de permiso de NetworkPolicy son aditivas; otra política puede conceder acceso adicional. Una política no crea un LoadBalancer o Ingress externo. Si la aplicación usa DNS, también necesita salida UDP/TCP por el puerto 53 hacia el DNS del clúster. El ejemplo de base de datos es material didáctico no persistente; un servicio real necesita almacenamiento persistente y copias de seguridad.
</details>

5. Escribe un manifiesto de Deployment para una aplicación .NET Framework que se ejecute en nodos Windows. La aplicación necesita una cadena de conexión como variable de entorno para acceder a Azure Blob Storage. Configura también un volumen persistente para los registros.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:**

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: windows-logs-pvc
spec:
  accessModes:
  - ReadWriteMany
  storageClassName: azurefile-csi
  resources:
    requests:
      storage: 10Gi
---
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
      os:
        name: windows
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
          value: Information
        - name: ASPNET_ENVIRONMENT
          value: Production
        volumeMounts:
        - name: logs-volume
          mountPath: C:\app\logs
        - name: config-volume
          mountPath: C:\app\web.config
          subPath: web.config
        resources:
          requests:
            memory: 2Gi
            cpu: 500m
          limits:
            memory: 4Gi
            cpu: 1000m
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
apiVersion: v1
kind: ConfigMap
metadata:
  name: dotnet-app-config
data:
  web.config: "<?xml version=\"1.0\" encoding=\"utf-8\"?>\n<configuration>\n  <system.web>\n\
    \    <compilation debug=\"false\" targetFramework=\"4.8\" />\n    <httpRuntime\
    \ targetFramework=\"4.8\" />\n  </system.web>\n  <system.webServer>\n    <handlers>\n\
    \      <remove name=\"ExtensionlessUrlHandler-Integrated-4.0\" />\n      <add\
    \ name=\"ExtensionlessUrlHandler-Integrated-4.0\" path=\"*.\" verb=\"*\" type=\"\
    System.Web.Handlers.TransferRequestHandler\" preCondition=\"integratedMode,runtimeVersionv4.0\"\
    \ />\n    </handlers>\n  </system.webServer>\n  <appSettings>\n    <add key=\"\
    BlobContainerName\" value=\"appdata\" />\n    <add key=\"LogDirectory\" value=\"\
    C:\\app\\logs\" />\n  </appSettings>\n</configuration>\n"
---
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

1. **Configuración del Secret:**
   - Crea `azure-storage-secret` a partir de una fuente protegida o de un administrador externo de secretos; no se proporciona ninguna clave de cuenta de ejemplo.
   - La aplicación puede acceder al valor de forma segura mediante una variable de entorno.

2. **PersistentVolumeClaim:**
   - Solicita 10 GB de almacenamiento persistente para los archivos de registro.
   - Usa una StorageClass de Azure Files con SMB y compatible con Windows.
   - Usa ReadWriteMany para que las réplicas de distintos nodos puedan montar el recurso compartido.

3. **Configuración del Deployment:**
   - Usa `nodeSelector` para programar el Pod solo en nodos Windows.
   - Usa una imagen de la aplicación .NET Framework.
   - Proporciona la cadena de conexión de Azure Storage mediante variables de entorno.
   - Monta el volumen persistente en el directorio de registros.
   - Monta el archivo `web.config` desde un ConfigMap.
   - Define solicitudes y límites de recursos adecuados.
   - Configura probes de disponibilidad y actividad para las comprobaciones de estado.

4. **Configuración del ConfigMap:**
   - Proporciona el archivo `web.config` de la aplicación .NET Framework.
   - Incluye las opciones y la configuración de la aplicación.

5. **Definición del Service:**
   - Crea un Service ClusterIP para acceder a la aplicación.

**Notas:**
- En entornos reales, ajusta al entorno las direcciones del registro de imágenes, las StorageClasses y los requisitos de recursos.
- Las aplicaciones .NET Framework deben usar imágenes basadas en Windows Server Core.
- En producción, se puede configurar el acceso externo mediante controladores Ingress o balanceadores de carga.
- Los datos confidenciales, como las cadenas de conexión de Azure Storage, deben integrarse con administradores externos de secretos, como Azure Key Vault.

Configura las réplicas para que escriban nombres de archivo distintos o subdirectorios específicos de cada Pod. La aplicación debe consumir las variables de entorno e implementar `/health`. Los montajes `subPath` de ConfigMap no se actualizan automáticamente.
</details>

## Temas avanzados

1. ¿Qué opción de containerd 1.x selecciona la imagen sandbox de los Pods Windows?
   - A) El ajuste `sandbox_image`.
   - B) El nivel y la ruta de los registros.
   - C) Los límites de memoria y el uso compartido de CPU.
   - D) La política de descarga de imágenes y la configuración del registro.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A) El ajuste `sandbox_image`**

**Explicación:**

En containerd 1.x se usa `plugins."io.containerd.grpc.v1.cri".sandbox_image`. En la configuración v3 de containerd 2.x, el ajuste es `plugins."io.containerd.cri.v1.images".pinned_images.sandbox`. Parte de `containerd config default` del runtime instalado y sigue el procedimiento de instalación de Windows correspondiente; no mezcles tablas de versiones de configuración.

La imagen sandbox debe ser compatible con la compilación de Windows del host. Una imagen pause solo para Linux no se puede ejecutar en Windows. CNI/HNS configura la red y el sandbox mantiene activa la red del Pod. La configuración del registro y de descarga de imágenes, el runtime runhcs, las rutas CNI y el registro de eventos también son importantes para las operaciones. Usa la imagen sandbox de Windows probada por la distribución en lugar de copiar una etiqueta antigua 3.6.
</details>

2. ¿Cuál es la principal ventaja del modo de aislamiento Hyper-V en contenedores Windows?
   - A) Mejor rendimiento y menor consumo de recursos.
   - B) Posibilidad de ejecutar contenedores con una versión de Windows distinta de la del sistema operativo del host.
   - C) Mayor velocidad de comunicación de red entre contenedores.
   - D) Compatibilidad con más API y funciones de Windows.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Posibilidad de ejecutar contenedores con una versión de Windows distinta de la del sistema operativo del host**

**Explicación:**
La principal ventaja del modo de aislamiento Hyper-V para contenedores Windows es poder ejecutar contenedores con una versión de Windows distinta de la del sistema operativo del host. Esta característica resulta útil, en particular, para ejecutar aplicaciones heredadas en infraestructura moderna.

Ventajas principales del modo de aislamiento Hyper-V:

1. **Compatibilidad de versiones:**
   - Resuelve incompatibilidades entre las versiones del sistema operativo del host y del contenedor.
   - Por ejemplo, se pueden ejecutar contenedores basados en Windows Server 2019 en un host Windows Server 2022.
   - Esto no es posible con el aislamiento de procesos, que requiere la misma versión del kernel en el host y en el contenedor.

2. **Mayor aislamiento de seguridad:**
   - Cada contenedor se ejecuta en una máquina virtual ligera, lo que proporciona un aislamiento más fuerte.
   - Refuerza los límites de seguridad entre contenedores y entre estos y el host.
   - Puede ser útil en entornos multiinquilino o al ejecutar código no confiable.

3. **Aislamiento a nivel del kernel:**
   - Cada contenedor tiene su propia instancia del kernel de Windows.
   - Así, los problemas del kernel de un contenedor no afectan a los demás contenedores ni al host.

**Kubernetes no admite el aislamiento Hyper-V y no hay ninguna anotación de Pod que lo habilite.** Esta explicación sirve como contexto sobre el sistema operativo Windows.

Desventajas del aislamiento Hyper-V:
- Consume más recursos de memoria y CPU.
- El inicio es más lento.
- Requiere que la función Hyper-V esté habilitada en el host.

Por qué las otras opciones son incorrectas:
- Hyper-V ofrece menor rendimiento y consume más recursos (A).
- La comunicación de red entre contenedores es más rápida con el aislamiento de procesos (C).
- Las API y funciones de Windows dependen de la versión del sistema operativo del contenedor; el aislamiento Hyper-V no agrega API (D).
</details>

3. ¿Qué afirmación sobre la red de Pods en nodos Windows de Kubernetes es correcta?
   - A) Los nodos Windows no usan complementos CNI y tienen su propia pila de red.
   - B) Los nodos Windows usan los mismos complementos CNI que los nodos Linux, pero con una configuración diferente.
   - C) Los nodos Windows siempre deben usar el modo de red del host.
   - D) Los nodos Windows no admiten redes overlay.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Los nodos Windows usan los mismos complementos CNI que los nodos Linux, pero con una configuración diferente**

**Explicación:**
Los nodos Windows de Kubernetes pueden usar los mismos complementos CNI (Container Network Interface) que los nodos Linux, pero la configuración cambia porque Windows tiene una pila de red distinta. Esto permite mantener un modelo de red coherente en clústeres con varios sistemas operativos y tener en cuenta las características de cada uno.

Características de la red de Pods en nodos Windows:

1. **Compatibilidad con complementos CNI:**
   - Los nodos Windows admiten varios complementos CNI, como Flannel, Calico y Antrea.
   - Estos complementos están diseñados para funcionar en nodos Linux y Windows.
   - Cada uno proporciona componentes o ajustes específicos para Windows.

2. **Modos de red:**
   - En general, los nodos Windows admiten redes overlay, como VXLAN y GENEVE.
   - Admiten varios modos de red, como L2bridge, L2tunnel y overlay.
   - El modo VXLAN de Flannel se usa ampliamente en nodos Windows.

3. **Diferencias de configuración:**
   - Los nodos Windows usan HNS (Host Network Service) para administrar la configuración de red.
   - La creación y administración de endpoints de red difiere de Linux.
   - Algunas funciones de red avanzadas pueden estar limitadas en Windows.

Ejemplo de configuración de Flannel CNI:
```yaml
# Linux-side Flannel ConfigMap; Windows uses separate HNS/CNI configuration.
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

Puede que los nodos Windows requieran configuración adicional:
```powershell
# Script running on Windows nodes
$env:KUBE_NETWORK = "cbr0"
$networkName = "vxlan0"
$networkMode = "overlay"
```

Por qué las otras opciones son incorrectas:
- Los nodos Windows usan complementos CNI; no dependen exclusivamente de su propia pila de red (A).
- Los Pods Windows normales no pueden usar `hostNetwork`; HostProcess es la excepción (C).
- Los nodos Windows admiten redes overlay, como VXLAN (D).
</details>

4. ¿Qué afirmación sobre la gestión de recursos en nodos Windows de Kubernetes es correcta?
   - A) Los nodos Windows no admiten límites de recursos.
   - B) Los nodos Windows ofrecen límites de recursos más precisos que los nodos Linux.
   - C) Los nodos Windows implementan límites de recursos mediante Job Objects.
   - D) Los nodos Windows implementan límites de recursos mediante cgroups.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Los nodos Windows implementan límites de recursos mediante Job Objects**

**Explicación:**
Los nodos Windows de Kubernetes usan Job Objects, una función del sistema operativo Windows, para aplicar límites de recursos a los contenedores. En cambio, los nodos Linux usan cgroups.

Características de la gestión de recursos en nodos Windows:

1. **Job Objects:**
   - Windows usa Job Objects para limitar el uso de recursos de grupos de procesos.
   - Los runtimes de contenedores compatibles con Windows, como containerd, usan la API de Job Objects para aplicar límites de CPU y memoria.
   - Job Objects puede limitar el tiempo de CPU, el uso de memoria, el tiempo de actividad y otros recursos de grupos de procesos.

2. **Límites de CPU:**
   - Los límites de CPU restringen el tiempo de CPU; no hay que confundirlos con los pesos relativos de uso compartido de CPU.
   - El concepto es similar al uso compartido de CPU en Linux, pero se implementa de otra forma.
   - Windows ajusta el uso compartido de CPU según la cantidad de núcleos.

3. **Límites de memoria:**
   - Los límites de memoria de los contenedores Windows se implementan con Job Objects.
   - Windows no tiene el OOM killer de Linux; si se agota la memoria disponible, pueden producirse errores de asignación o paginación y degradarse el rendimiento.
   - La gestión de memoria de Windows difiere de Linux, por lo que el comportamiento real puede variar aunque el límite sea el mismo.

4. **Configuración de solicitudes y límites de recursos:**
   - Los Pods Windows especifican las solicitudes y los límites de recursos del mismo modo que los Pods Linux:
     ```yaml
     resources:
       requests:
         memory: "2Gi"
         cpu: "500m"
       limits:
         memory: "4Gi"
         cpu: "1"
     ```
   - kubelet entrega estos valores al runtime de contenedores Windows, que usa Job Objects para aplicar los límites.

5. **Monitoreo e informes:**
   - kubelet monitorea el uso de recursos de los contenedores mediante contadores de rendimiento de Windows.
   - Esta información se puede consultar con `kubectl top pods` y `kubectl top nodes`.
   - Metrics Server recopila esta información y la proporciona mediante la API de Kubernetes.

Consideraciones para la gestión de recursos en nodos Windows:
- En general, los contenedores Windows usan más recursos de base que los contenedores Linux.
- La sobrecarga de memoria puede ser mayor; asegúrate de reservar suficiente margen.
- El comportamiento exacto de los límites puede variar según la versión de Windows.

Por qué las otras opciones son incorrectas:
- Los nodos Windows sí admiten límites de recursos (A).
- Ninguno de los dos sistemas operativos ofrece límites universalmente más precisos; sus mecanismos son diferentes (B).
- Los nodos Windows usan Job Objects, no cgroups (D).
</details>

5. ¿Cuál de las siguientes opciones NO es una práctica de seguridad adecuada para nodos Windows en Kubernetes?
   - A) Analizar y actualizar periódicamente las imágenes de contenedor para corregir vulnerabilidades.
   - B) Habilitar el modo privilegiado para todos los Pods Windows.
   - C) Usar gMSA (cuentas de servicio administradas de grupo) para integrarse con Active Directory.
   - D) Usar NetworkPolicy para restringir la comunicación entre Pods.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Habilitar el modo privilegiado para todos los Pods Windows**

**Explicación:**
Habilitar el modo privilegiado para todos los Pods Windows NO es una práctica de seguridad adecuada. Los contenedores Windows no admiten el modo privilegiado y, si se intenta configurarlo, la creación del Pod falla.

Por qué esta opción no es adecuada:

1. **El modo privilegiado no es compatible:**
   - A diferencia de los contenedores Linux, los contenedores Windows no admiten el concepto de modo privilegiado.
   - Windows tiene un modelo de seguridad distinto y no ofrece un mecanismo equivalente para otorgar privilegios de host a los contenedores.
   - Windows usa HostProcess para agentes de host confiables; es distinto de la opción privileged.

2. **Incumple el principio de privilegio mínimo:**
   - Aunque se admitiera, habilitar el modo privilegiado para todos los Pods incumpliría el principio de privilegio mínimo.
   - Cada carga de trabajo debe recibir solo los permisos que necesita.

3. **Aumenta el riesgo de seguridad:**
   - El modo privilegiado permite que los contenedores accedan al sistema host, lo que aumenta mucho el riesgo.
   - Si se explota una vulnerabilidad de escape del contenedor, el host entero podría quedar expuesto.

Las demás opciones sí son prácticas de seguridad adecuadas:

A) **Analizar y actualizar periódicamente las imágenes de contenedor para corregir vulnerabilidades:**
   - El análisis de imágenes ayuda a detectar y corregir vulnerabilidades conocidas.
   - Las imágenes Windows deben recibir actualizaciones de seguridad periódicas.
   - Conviene integrar las herramientas de análisis de imágenes en los pipelines de CI/CD.

C) **Usar gMSA para integrarse con Active Directory:**
   - gMSA permite que los contenedores Windows se autentiquen de forma segura ante los servicios de Active Directory.
   - Usar gMSA en lugar de credenciales codificadas directamente mejora la seguridad.
   - gMSA automatiza la administración y rotación de contraseñas.

D) **Usar NetworkPolicy para restringir la comunicación entre Pods:**
   - NetworkPolicy aplica el principio de privilegio mínimo a las comunicaciones de red.
   - Limitar la comunicación entre Pods a los casos necesarios reduce la superficie de ataque.
   - La segmentación de red ayuda a impedir el movimiento lateral.

Prácticas adicionales para reforzar la seguridad de nodos Windows:
- Mantén los nodos Windows actualizados con los parches de seguridad más recientes.
- Deshabilita funciones y roles de Windows innecesarios.
- Configura correctamente las reglas del firewall de Windows.
- Usa mecanismos de autenticación sólidos.
- Elimina herramientas y componentes innecesarios de las imágenes de contenedor.
- Implementa monitoreo de seguridad en tiempo de ejecución.
</details>

## Referencias de verificación

- https://kubernetes.io/docs/concepts/windows/intro/
- https://kubernetes.io/docs/concepts/configuration/windows-resource-management/
- https://kubernetes.io/docs/concepts/services-networking/dns-pod-service/#dns-windows
- https://kubernetes.io/docs/tasks/configure-pod-container/configure-gmsa/
- https://kubernetes.io/docs/tasks/configure-pod-container/create-hostprocess-pod/
- https://learn.microsoft.com/en-us/virtualization/windowscontainers/manage-containers/manage-serviceaccounts
- https://learn.microsoft.com/en-us/virtualization/windowscontainers/manage-containers/gmsa-run-container
- https://github.com/prometheus-community/windows_exporter/blob/master/kubernetes/windows-exporter-daemonset.yaml
- https://github.com/fluent/fluent-bit-docs/blob/master/installation/downloads/windows.md
- https://github.com/containerd/containerd/blob/main/docs/cri/config.md
- https://learn.microsoft.com/en-us/sql/linux/quickstart-install-connect-docker?view=sql-server-ver17&tabs=cli
