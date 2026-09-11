# Windows in Kubernetes Quiz

This quiz tests your conceptual and practical knowledge about managing Windows nodes and workloads in Kubernetes. It covers topics such as Windows container basics, Windows node configuration in Kubernetes, networking, storage, security, and monitoring.

## Multiple Choice Questions

1. What container runtimes are supported for Windows nodes in Kubernetes?
   - A) containerd with Windows CRI support
   - B) CRI-O and Docker
   - C) containerd and CRI-O
   - D) Docker, containerd, and gVisor

<details>
<summary>Show Answer</summary>

**Answer: A) containerd with Windows CRI support**

**Explanation:**
The officially supported container runtimes for Windows nodes in Kubernetes are containerd with Windows CRI support.


- **containerd**: This is the currently recommended container runtime for Windows nodes. containerd is a lightweight and stable runtime that has official support for Windows nodes in Kubernetes 1.20 and later.

CRI-O is not officially supported on Windows nodes. CRI-O is primarily a Container Runtime Interface (CRI) implementation for Linux containers.

gVisor is a sandbox runtime for container isolation but is not currently supported on Windows nodes.

When setting up container runtimes on Windows nodes, it's important to verify compatibility with the Kubernetes version.
</details>

2. What network solution is required when configuring a cluster with mixed Windows and Linux nodes in Kubernetes?
   - A) All CNI plugins support both Windows and Linux nodes
   - B) CNI plugins that support Windows, such as Flannel, Calico, and Antrea
   - C) Windows nodes must use only kubenet without CNI plugins
   - D) Windows nodes must always use host network mode only

<details>
<summary>Show Answer</summary>

**Answer: B) CNI plugins that support Windows, such as Flannel, Calico, and Antrea**

**Explanation:**
When configuring a cluster with mixed Windows and Linux nodes in Kubernetes, you must use specific CNI (Container Network Interface) plugins that support Windows. Not all CNI plugins support Windows.

The main CNI plugins that support Windows nodes are:

- **Flannel**: Supports Windows nodes in overlay network mode (vxlan).
- **Calico**: Provides support for Windows nodes, supporting both BGP mode and VXLAN mode.
- **Antrea**: Provides support for Windows nodes, using OVS (Open vSwitch).

Azure CNI and AWS VPC CNI support Windows in their respective environments.

Considerations when setting up CNI plugins on Windows nodes:
- Windows nodes have a different networking stack than Linux nodes.
- Some networking features may be limited on Windows.
- You should verify the Windows support version and configuration requirements of the CNI plugin.

kubenet is unsupported. Regular Windows Pods cannot use hostNetwork; HostProcess Pods require hostNetwork: true.
</details>

3. Which isolation mode does Kubernetes support for Windows application containers?
   - A) Hyper-V isolation
   - B) Process isolation
   - C) Virtual machine isolation
   - D) Sandbox isolation

<details>
<summary>Show Answer</summary>

**Answer: B) Process isolation**

**Explanation:**
Kubernetes supports process isolation for Windows application containers. In this mode, Windows containers share the host operating system's kernel, and each container runs as an isolated process group.

Characteristics of process isolation mode:
- Must use the same kernel version as the host OS.
- Lower resource usage and faster startup time.
- Similar to the typical isolation model of Linux containers.

Windows also provides an alternative isolation mode called Hyper-V Isolation:
- Each container runs in a lightweight virtual machine.
- Can use different kernel versions than the host OS.
- Provides a higher level of isolation but has more overhead.

**Kubernetes does not support Hyper-V isolation, and no Pod annotation enables it.** This discussion is Windows OS background knowledge.

Virtual machine isolation is not an official isolation mode for Windows containers, and sandbox isolation is not a term used for Windows containers.
</details>

4. Which of the following is NOT a correct limitation when using Windows nodes in Kubernetes?
   - A) Cannot use privileged containers
   - B) Cannot use HostPath volumes
   - C) Only some SecurityContext features are supported for pods
   - D) Cannot share process namespaces between Windows containers

<details>
<summary>Show Answer</summary>

**Answer: B) Cannot use HostPath volumes**

**Explanation:**
HostPath volumes can be used on Windows nodes. Therefore, the statement "Cannot use HostPath volumes" is incorrect.

When using HostPath volumes on Windows nodes, you must follow the Windows path format:
```yaml
volumes:
- name: data
  hostPath:
    path: 'C:\data'
```

The actual limitations when using Windows nodes in Kubernetes are:

- **Privileged mode**: The privileged flag is unsupported. Trusted node agents that need host access can use HostProcess.

- **SecurityContext limitations**: Only some SecurityContext features are supported on Windows nodes. For example, runAsUser, runAsGroup, fsGroup, seccomp, SELinux, etc. are not supported.

- **Namespace sharing**: Containers in one Pod share networking and localhost, but not process namespaces or root filesystems.

Other limitations of Windows nodes:
- If you want DaemonSets to run on all nodes (Linux and Windows), you must use nodeSelector.
- Some storage drivers and volume types may be limited.
- Linux-specific alpha/beta features may not work on Windows nodes.
</details>

5. What node label is used to identify Windows nodes in Kubernetes?
   - A) kubernetes.io/os=windows
   - B) beta.kubernetes.io/os=windows
   - C) node.kubernetes.io/windows=true
   - D) kubernetes.io/windows=enabled

<details>
<summary>Show Answer</summary>

**Answer: A) kubernetes.io/os=windows**

**Explanation:**
The standard node label used to identify Windows nodes in Kubernetes is `kubernetes.io/os=windows`. This label indicates the node's operating system type and is used by the Kubernetes scheduler to place pods on appropriate nodes.

To schedule Windows pods to Windows nodes, use nodeSelector as follows:
```yaml
nodeSelector:
  kubernetes.io/os: windows
```

Or you can use node affinity:
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

`beta.kubernetes.io/os=windows` was used in previous versions of Kubernetes but is now deprecated.

`node.kubernetes.io/windows=true` and `kubernetes.io/windows=enabled` are not standard Kubernetes labels.

Note: Linux nodes have the `kubernetes.io/os=linux` label.
</details>

6. Which Microsoft base image offers broader Windows API support than Nano Server for traditional Windows applications?
   - A) mcr.microsoft.com/windows/servercore
   - B) mcr.microsoft.com/windows/nanoserver
   - C) mcr.microsoft.com/dotnet/framework/runtime
   - D) mcr.microsoft.com/powershell

<details>
<summary>Show Answer</summary>

**Answer: A) mcr.microsoft.com/windows/servercore**

**Explanation:**
Kubernetes does not choose a default base image. A suitable choice for traditional Windows applications is `mcr.microsoft.com/windows/servercore`. This image is based on a Windows Server Core installation and includes the core components needed to run most Windows applications.

The main base images available for Windows containers are:

1. **Windows Server Core** (`mcr.microsoft.com/windows/servercore`):
   - Image size varies with release, layers and compression.
   - Supports most Windows applications
   - Includes Windows PowerShell; select the required .NET Framework runtime image separately.
   - Most widely used Windows base image

2. **Nano Server** (`mcr.microsoft.com/windows/nanoserver`):
   - Image size varies with release, layers and compression.
   - Limited Windows API support
   - Suitable for .NET Core applications
   - Minimal attack surface

3. **.NET Framework** (`mcr.microsoft.com/dotnet/framework/runtime`):
   - Image for .NET Framework applications
   - Based on Server Core
   - Includes specific versions of .NET Framework

4. **PowerShell** (`mcr.microsoft.com/powershell`):
   - Image for running PowerShell scripts
   - Available in Nano Server or Server Core based versions

When selecting a Windows container image, consider:
- Application requirements (required Windows APIs)
- Image size and startup time
- Security requirements
- Windows version compatibility (check version number in image tag)

Windows container images must be the same version as or compatible with the host OS.
</details>

7. What is the recommended method for deploying DaemonSets in a cluster with mixed Windows and Linux nodes in Kubernetes?
   - A) Use a single DaemonSet and deploy to all nodes
   - B) Create separate DaemonSets for each OS and use nodeSelector
   - C) Use StatefulSet instead of DaemonSet for Windows nodes
   - D) Add tolerations to all DaemonSets

<details>
<summary>Show Answer</summary>

**Answer: B) Create separate DaemonSets for each OS and use nodeSelector**

**Explanation:**
The recommended method for deploying DaemonSets in a cluster with mixed Windows and Linux nodes in Kubernetes is to create separate DaemonSets for each OS and use nodeSelector.

Reasons why this approach is necessary:
- Windows containers and Linux containers use different image formats.
- The same application may require different configurations for each OS.
- Some features may only be available on specific OSes.

Windows DaemonSet example:
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

Linux DaemonSet example:
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

Using a single DaemonSet may cause pods to fail to start on some nodes due to container image compatibility issues.

DaemonSets can be used on Windows nodes, so there is no need to replace them with StatefulSets.

Adding tolerations to all DaemonSets can help schedule pods on tainted nodes, but it does not solve OS compatibility issues.
</details>

8. Which statement about DNS configuration for pods on Windows nodes is correct?
   - A) DNS configuration is not supported on Windows nodes
   - B) Windows nodes must use Windows DNS Server instead of CoreDNS
   - C) Windows Pods can use CoreDNS with Windows DNS suffix limitations
   - D) Windows nodes require separate DNS server configuration for each pod

<details>
<summary>Show Answer</summary>

**Answer: C) Windows Pods can use CoreDNS with Windows DNS suffix limitations**

**Explanation:**
Windows Pods can use CoreDNS with Windows DNS suffix limitations. Use a bare Service name in the same namespace or its full FQDN; dotted partial names do not use the Linux search list.

DNS configuration for Windows pods:
- Windows uses HNS/DNS settings and a single namespace suffix, not /etc/resolv.conf.
- Pods can use the cluster's DNS service (CoreDNS) to resolve service names.
- The `dnsPolicy` and `dnsConfig` fields can be used to configure DNS settings.

Example:
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

Considerations when using DNS on Windows nodes:
- DNS client behavior inside Windows containers may be slightly different from Linux.
- Some DNS-related tools (e.g., nslookup, Resolve-DnsName) are available by default in Windows containers.
- You should verify that the network plugin correctly supports DNS resolution.

There is no need to configure a separate DNS server or use Windows DNS Server on Windows nodes. Kubernetes' standard DNS mechanism works for Windows pods.
</details>

9. Which statement about pod-to-pod communication on Windows nodes is correct?
   - A) Pod-to-pod communication is not supported on Windows nodes
   - B) Pods on Windows nodes can only communicate with pods on the same node
   - C) Pods on Windows nodes cannot communicate with pods on Linux nodes
   - D) Pods on Windows nodes can communicate with all other pods through CNI plugins

<details>
<summary>Show Answer</summary>

**Answer: D) Pods on Windows nodes can communicate with all other pods through CNI plugins**

**Explanation:**
Pods on Windows nodes can communicate with all other pods in the cluster through appropriate CNI (Container Network Interface) plugins. This includes pods on the same Windows node, pods on other Windows nodes, and pods on Linux nodes.

Key characteristics of pod-to-pod communication on Windows nodes:
- Pods on Windows nodes can discover and access services in the cluster by name.
- Pods on Windows nodes are assigned unique IP addresses within the cluster IP address range.
- Pod-to-pod communication occurs according to the implementation of the selected CNI plugin.

CNI plugins that support pod-to-pod communication on Windows nodes:
- Flannel (VXLAN mode)
- Calico
- Antrea
- Azure CNI
- AWS VPC CNI

For example, when using Flannel:
- Pods on Windows nodes communicate with pods on other nodes through VXLAN encapsulation.
- Each pod is assigned an IP address within the cluster CIDR range.
- Routing tables are configured to route pod IP addresses to the appropriate nodes.

Considerations for pod-to-pod communication on Windows nodes:
- Some advanced networking features may be limited on Windows.
- NetworkPolicy support may vary depending on the CNI plugin.
- Windows firewall rules should not interfere with pod communication.

Pods on Windows nodes can communicate perfectly with pods on Linux nodes, which is one of Kubernetes' core features.
</details>

10. Which statement about resource limits for Windows containers in Kubernetes is correct?
    - A) Windows containers do not support resource limits
    - B) CPU limits are supported but memory limits are not
    - C) Memory limits are supported but CPU limits are not
    - D) Both CPU and memory limits are supported

<details>
<summary>Show Answer</summary>

**Answer: D) Both CPU and memory limits are supported**

**Explanation:**
Windows containers in Kubernetes support both CPU and memory resource limits. Windows nodes can limit and request container resources in a similar way to Linux nodes.

Example of resource limits for Windows containers:
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

Characteristics of resource management for Windows containers:
- **CPU limits**: Windows implements CPU sharing and limits to manage CPU resource allocation between containers.
- Windows has no Linux OOM killer; exceeding available memory can cause allocation failures or paging and degraded performance.
- **Resource monitoring**: kubelet monitors resource usage of Windows containers and reports to the Kubernetes API.

Considerations for resource management of Windows containers:
- Default resource overhead for Windows containers may be greater than Linux containers.
- The exact implementation of resource limits may vary depending on the Windows version.
- Setting memory limits too low may prevent Windows containers from working properly.
- Hyper-V isolation is unsupported by Kubernetes.

You can monitor resource usage on Windows nodes using `kubectl top pods` and `kubectl top nodes` commands.
</details>
## Short Answer Questions

1. Explain the main steps and requirements for adding Windows nodes to a Kubernetes cluster.

<details>
<summary>Show Answer</summary>

**Answer:**

**Steps for Adding Windows Nodes to a Kubernetes Cluster:**

1. **Verify Prerequisites:**
   - A supported Kubernetes/Windows combination; upstream v1.37 supports Windows Server 2022/2025
   - Control plane must run on Linux nodes
   - Windows Server 2022 for these ltsc2022 examples
   - Compatible CNI plugin (Flannel, Calico, Antrea, etc.)

2. **Configure Networking:**
   - Install CNI plugin that supports Windows nodes
   - Configure cluster CIDR and service CIDR
   - Example (Linux-side Flannel configuration; install the Windows CNI separately):
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

3. **Prepare Windows Node:**
   - Install and update Windows Server
   - Enable required Windows features:
     ```powershell
     Install-WindowsFeature -Name Containers
     Restart-Computer -Force
     ```
   - Install container runtime (containerd recommended):
     ```powershell
     # Use the reviewed sig-windows-tools installation procedure in the chapter.
     # Install-Containerd.ps1: supported runtime; PrepareNode.ps1: matching kubeadm/kubelet.
     # Do not start kubelet with an empty configuration.
     ```

4. **Install kubelet and kube-proxy:**
   - Download Kubernetes binaries:
     ```powershell
     # Use the reviewed sig-windows-tools installation procedure in the chapter.
     # Install-Containerd.ps1: supported runtime; PrepareNode.ps1: matching kubeadm/kubelet.
     # Do not start kubelet with an empty configuration.
     ```
   - Create kubelet configuration file:
     ```powershell
     # Use the reviewed sig-windows-tools installation procedure in the chapter.
     # Install-Containerd.ps1: supported runtime; PrepareNode.ps1: matching kubeadm/kubelet.
     # Do not start kubelet with an empty configuration.
     ```
   - Register and start kubelet service:
     ```powershell
     # Use the reviewed sig-windows-tools installation procedure in the chapter.
     # Install-Containerd.ps1: supported runtime; PrepareNode.ps1: matching kubeadm/kubelet.
     # Do not start kubelet with an empty configuration.
     ```
   - Configure and start kube-proxy (typically deployed as DaemonSet)

5. **Join Node:**
   - Run kubeadm join command or manually configure TLS certificates and kubeconfig
   - Verify that the node has registered with the cluster:
     ```bash
     kubectl get nodes
     ```

6. **Add Node Labels:**
   - Add OS label to Windows node (if not automatically added):
     ```bash
     kubectl label node <windows-node-name> kubernetes.io/os=windows
     ```

7. **Deploy Test Workload:**
   - Deploy a simple pod running a Windows container:
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

**Key Considerations:**

1. **Version Compatibility:**
   - Windows Server version and container image version must be compatible
   - Verify Kubernetes version and Windows support features

2. **Networking:**
   - Use CNI plugins supported on Windows nodes
   - Verify network policy support
   - Verify port requirements (kubelet, containerd, CNI, etc.)

3. **Storage:**
   - Verify storage drivers and volume types supported on Windows nodes
   - Verify CSI driver compatibility

4. **Monitoring and Logging:**
   - Deploy monitoring agents suitable for Windows nodes
   - Configure Windows event log collection

5. **Security:**
   - Configure Windows firewall rules
   - Set up Group Managed Service Accounts (gMSA) if needed
   - Configure network security groups

6. **Automation:**
   - Automate Windows node provisioning (Ansible, PowerShell DSC, etc.)
   - Establish node upgrade strategy
</details>

2. Explain the main differences between Windows containers and Linux containers, and how to manage these differences in Kubernetes.

<details>
<summary>Show Answer</summary>

**Answer:**

**Main Differences Between Windows Containers and Linux Containers:**

1. **Underlying Technology:**
   - **Linux containers**: Use Linux namespaces, cgroups, and kernel features for isolation
   - **Windows containers**: Use Windows isolation technologies (job objects, Hyper-V isolation, etc.)

2. **Image Structure:**
   - **Linux containers**: Relatively small size (tens to hundreds of MB)
   - **Windows containers**: Generally larger size (several GB), base images are larger

3. **Isolation Modes:**
   - **Linux containers**: Typically namespace-based; alternative sandbox runtimes also exist
   - **Windows containers**: Kubernetes supports process isolation; Hyper-V is outside Kubernetes support

4. **File System:**
   - **Linux containers**: Layered file system (OverlayFS, etc.)
   - **Windows containers**: NTFS-based filter driver

5. **Networking:**
   - **Linux containers**: Various networking modes and driver support
   - **Windows containers**: Limited networking modes, only specific CNI plugins supported

6. **Resource Management:**
   - **Linux containers**: Fine-grained resource control through cgroups
   - **Windows containers**: Resource control through Job Objects, with some limitations

7. **Security Context:**
   - **Linux containers**: Various security context options (SELinux, AppArmor, etc.)
   - **Windows containers**: Limited security context options, privileged containers not supported

8. **Host OS Dependency:**
   - **Linux containers**: Can run on various Linux distributions
   - **Windows containers**: Require same or compatible version as host OS

**How to Manage These Differences in Kubernetes:**

1. **Node Selection and Scheduling:**
   - **Use node labels**: `kubernetes.io/os=windows` or `kubernetes.io/os=linux`
   - **Use nodeSelector**:
     ```yaml
     os:
       name: windows
     nodeSelector:
       kubernetes.io/os: windows
     ```
   - **Use node affinity**:
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

2. **Workload Separation:**
   - **Create OS-specific Deployments**:
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

3. **DaemonSet Management:**
   - **Create OS-specific DaemonSets**:
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

4. **Image Management:**
   - **Use multi-architecture images**: Support various OS/architectures with the same tag
   - **Use OS-specific image tags**: `myapp:linux` and `myapp:windows`
   - **Set image pull policy**: `imagePullPolicy: Always`

5. **Resource Requests and Limits:**
   - **Set appropriate resources for each OS**:
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
   - **Select compatible CNI plugin**: Flannel, Calico, Antrea, etc.
   - **Consider OS when applying network policies**:
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

7. **Storage:**
   - **Use OS-compatible storage classes**:
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
   - **Apply appropriate security settings for each OS**:
     ```yaml
     # Security context for Linux pods
     securityContext:
       runAsUser: 1000
       runAsGroup: 3000
       fsGroup: 2000

     # These Linux-only fields are rejected with spec.os.name: windows.
     ```

9. **Monitoring and Logging:**
   - **Deploy OS-specific monitoring agents**
   - **Adjust log collection paths**: Windows (`C:\k\logs`) vs Linux (`/var/log`)

10. **CI/CD Pipelines:**
    - **Configure OS-specific build and test pipelines**
    - **Establish multi-OS deployment strategy**
</details>

3. Explain how to use Group Managed Service Accounts (gMSA) in Windows containers and their benefits.

<details>
<summary>Show Answer</summary>

**Answer:**

**Group Managed Service Accounts (gMSA) Overview:**

Group Managed Service Accounts (gMSA) are a special type of Active Directory account for service authentication in Windows domain environments. Using gMSA in Windows containers in Kubernetes allows running applications that require domain authentication, and is particularly useful in the following scenarios:

- .NET applications requiring Active Directory integration
- SQL Server connections using Windows authentication
- Services requiring Kerberos authentication
- Applications that need to access domain resources

**How to Use gMSA in Windows Containers:**

1. Prepare AD/DNS connectivity and a supported credential retrieval method: domain-joined hosts or a separately configured portable identity provider. Containers themselves cannot join the domain.
2. Check `Get-KdsRootKey`. An AD administrator creates a key only when needed and allows replication time (up to 10 hours). Backdating ten hours is only for a single-DC test environment.
3. Grant password retrieval to a dedicated authorized-host group, not all Domain Computers. Generate real SID/GUID/DNS/NetBIOS values with the CredentialSpec module’s `New-CredentialSpec`.
4. Install the GMSACredentialSpec CRD and mutating/validating webhooks. Put generated JSON into `GMSACredentialSpec.credspec` using `windows.k8s.io/v1`. It is not a Secret and contains no gMSA password.
5. Grant the ServiceAccount `use` on the named resource and set the Pod’s `serviceAccountName` and `windowsOptions.gmsaCredentialSpecName`.
6. Validate real application Kerberos authentication and `klist`. `whoami` reports the local process user, not the gMSA network identity.

See the [chapter’s gMSA procedure](../../core/10-windows-in-kubernetes.md) for the complete generated-resource and RBAC example.

**Benefits of Using gMSA:**

1. **Enhanced Security:**
   - Eliminates hardcoded credentials inside containers
   - Automatic password management and rotation
   - Enables applying principle of least privilege

2. **Active Directory Integration:**
   - Enables containerizing existing applications using Windows authentication
   - Supports Kerberos and NTLM authentication
   - Seamless access to domain resources

3. **Centralized Identity Management:**
   - Unified identity management through Active Directory
   - Group policies can be applied
   - Improved auditing and compliance

4. **Application Compatibility:**
   - Supports legacy .NET applications requiring domain authentication
   - Supports SQL Server connections using Windows integrated authentication
   - Supports Windows authentication for IIS web applications

5. **Simplified Operations:**
   - Automated credential management
   - Credentials persist across container restarts
   - Same identity can be shared across multiple containers

**Considerations When Using gMSA:**

1. **Network Requirements:**
   - Network connectivity from Windows nodes to domain controllers required
   - Proper DNS configuration required
   - Required ports must be open (Kerberos, LDAP, etc.)

2. **Permission Management:**
   - Grant only minimum required permissions to gMSA
   - Configure appropriate group memberships
   - Regular permission reviews

3. **Scalability:**
   - Consider domain controller load in large clusters
   - Use multiple gMSA accounts for permission separation

4. **Troubleshooting:**
   - Debug domain connectivity issues
   - Verify credential spec configuration errors
   - Review container runtime logs
</details>

4. Explain how to configure logging and monitoring for Windows nodes in Kubernetes and the differences from Linux nodes.

<details>
<summary>Show Answer</summary>

**Answer:**

**Configuring Logging and Monitoring for Windows Nodes:**

**1. Logging Configuration:**

**Main Logging Sources for Windows Nodes:**
- Windows Event Logs (System, Application, Security)
- ETW (Event Tracing for Windows) events
- Application log files (typically within the `C:\` drive)
- kubelet and container runtime logs (typically `C:\k\logs` or similar paths)

**Methods for Configuring Windows Node Logging:**

1. **Fluent Bit or Fluentd Setup:**
   Read host event logs using the chapter’s Fluent Bit Windows service or a reviewed HostProcess collector. Mounting .evtx files into a regular container does not make winlog read the host API. The input below requires permission to read Security and a persistent checkpoint directory.

2. **Windows Event Log Collection Configuration:**
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

3. **Container Log Collection:**
   - containerd log path: `C:\var\log\containers`
   - kubelet log path: `C:\k\logs` or Windows Event Log

**2. Monitoring Configuration:**

**Main Metrics for Windows Node Monitoring:**
- CPU, memory, disk usage
- Network traffic
- Process count
- Page file usage
- Container resource usage

**Methods for Configuring Windows Node Monitoring:**

1. **Prometheus Windows Exporter Setup:**
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

2. **Prometheus Scraping Configuration:**
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

3. **Grafana Dashboard Setup:**
   - Create dedicated dashboards for Windows node metrics
   - Add Windows-specific panels (e.g., page file usage, service status, etc.)

**3. Troubleshooting Tools:**

**Tools for Windows Node Troubleshooting:**
- PowerShell commands (`Get-Process`, `Get-Service`, `Get-EventLog`)
- Windows Performance Monitor (PerfMon)
- Event Viewer
- `kubectl debug` command (limited support on Windows nodes)

**Windows Node Troubleshooting Examples:**
```powershell
# Check kubelet logs
Get-EventLog -LogName Application -Source kubelet -Newest 50

# Check containerd status
Get-Service containerd

# Verify network connectivity
Test-NetConnection -ComputerName api.kubernetes.cluster -Port 443
```

**Key Differences from Linux Nodes:**

1. **Log Storage Location:**
   - **Linux**: Stored as text files in `/var/log/` directory
   - **Windows**: Windows Event Logs (binary format) and text files in various locations

2. **Log Collection Mechanism:**
   - **Linux**: File-based log collection is typical (tail, read)
   - **Windows**: Requires collection through Windows Event Log API

3. **Metric Collection:**
   - **Linux**: Collect metrics from `/proc`, `/sys` file systems
   - **Windows**: Use WMI (Windows Management Instrumentation) or Performance Counter API

4. **Container Logs:**
   - **Linux**: Standard output/error redirected to files
   - **Windows**: stdout/stderr use CRI logs too; ETW/file logs require an application/host collector

5. **Resource Monitoring:**
   - **Linux**: Container resource usage monitoring through cgroups
   - **Windows**: Resource monitoring through Job Objects, some metrics calculated differently

6. **Monitoring Agents:**
   - **Linux**: Various agent support (node-exporter, cAdvisor, etc.)
   - **Windows**: Limited agent support, Windows-specific agents required

7. **Debugging Tools:**
   - **Linux**: Various CLI tools (ps, top, netstat, strace, etc.)
   - **Windows**: PowerShell commands, GUI tools, limited CLI tools

**Best Practices:**

1. **Integrated Logging Solution:**
   - Use EFK (Elasticsearch, Fluent Bit, Kibana) or ELK stack
   - Separate configurations for both Windows and Linux nodes

2. **Integrated Monitoring Solution:**
   - Monitor all nodes with Prometheus + Grafana
   - Create OS-specific dashboards

3. **Alert Configuration:**
   - Set up alert rules for Windows-specific events
   - Monitor critical Windows service status

4. **Log Retention Policy:**
   - Configure Windows event log size and retention period
   - Configure log rotation policy

5. **Security Monitoring:**
   - Collect and analyze Windows security event logs
   - Monitor permission changes and login attempts
Provide the monitoring namespace, Prometheus Operator/ServiceMonitor discovery configuration and a tested release tag. Restrict HostProcess PSS exceptions and port 9182 firewall sources. Confirm host log paths/channels per distribution; EKS records kubelet/kube-proxy in EKS Windows. The Elasticsearch example also requires trusted CA and authentication configuration.
</details>

5. Explain the storage options and volume mount configuration methods for Windows containers in Kubernetes.

<details>
<summary>Show Answer</summary>

**Answer:**

**Storage Options for Windows Containers:**

**1. Basic Volume Types:**

1. **emptyDir:**
   - Stores temporary data during pod lifetime
   - Created on local NTFS volume of Windows node
   - Data is deleted when pod is deleted

   ```yaml
   volumes:
   - name: temp-data
     emptyDir: {}
   ```

2. **hostPath:**
   - Direct access to Windows node's file system
   - Escape backslashes only in double-quoted YAML strings; plain/single-quoted paths use single backslashes.
   - Data cannot be shared across nodes

   ```yaml
   volumes:
   - name: logs
     hostPath:
       path: 'C:\Logs'
       type: DirectoryOrCreate
   ```

3. **configMap and secret:**
   - Store configuration data and sensitive information
   - Works the same way for Windows containers
   - File permission settings are applied differently on Windows

   ```yaml
   volumes:
   - name: config
     configMap:
       name: app-config
   ```

4. **persistentVolumeClaim (PVC):**
   - Request persistent storage
   - Requires Windows-compatible storage class
   - Need to verify CSI driver support

   ```yaml
   volumes:
   - name: data
     persistentVolumeClaim:
       claimName: windows-pvc
   ```

**2. Storage Solutions Supporting Windows Containers:**

1. **Azure Disk/File (AKS):**
   - Azure Kubernetes Service supports Windows nodes
   - Can use SMB protocol-based Azure Files
   - Azure Disk CSI driver supported

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
   - Amazon EKS Windows node support
   - EBS CSI driver available
   - Access limited within single AZ

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

3. **SMB/CIFS Volumes:**
   - Network file system suitable for Windows environments
   - Requires a Windows-compatible SMB CSI driver
   - Supports ReadWriteMany access across multiple pods

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
   - Windows iSCSI capability does not imply support for the Kubernetes in-tree iscsi volume plugin. Use a storage vendor CSI driver that explicitly supports Windows filesystem volumes. Windows Pods do not support raw block volumeDevices.

**3. Volume Mount Configuration for Windows Containers:**

1. **Volume Mount Paths:**
   - Windows containers use Windows path format
   - Typically use paths within the `C:\` drive
   - Escape backslashes only in double-quoted YAML strings; plain/single-quoted paths use single backslashes.

   ```yaml
   volumeMounts:
   - name: data
     mountPath: 'C:\data'
   ```

2. **Read-Only Mounts:**
   - Supported for Windows containers
   - Applied through NTFS permissions

   ```yaml
   volumeMounts:
   - name: config
     mountPath: 'C:\config'
     readOnly: true
   ```

3. **Subpath Mounts:**
   - Can mount only specific subpaths of volumes
   - Note Windows path separators

   ```yaml
   volumeMounts:
   - name: shared-data
     mountPath: 'C:\app\logs'
     subPath: logs
   ```

**4. Windows Container Storage Configuration Examples:**

1. **Web Application Configuration:**
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

2. **Database Configuration:**
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
         value: Y
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

**5. Considerations When Using Windows Container Storage:**

1. **Path Separators:**
   - Escape backslashes only in double-quoted YAML strings; plain/single-quoted paths use single backslashes.
   - Alternatively, forward slashes (`/`) can be used but verify application compatibility

2. **File Permissions:**
   - Windows uses NTFS permission model
   - Cannot set permissions like chmod/chown in Linux
   - Permissions inside containers are determined by container user context

3. **Performance Considerations:**
   - Network storage (SMB/CIFS) may have latency
   - Local storage or direct-attached block storage recommended for high-performance requirements

4. **Storage Class Compatibility:**
   - Verify storage classes compatible with Windows nodes
   - Verify Windows support of CSI drivers

5. **Backup and Recovery:**
   - Consider Windows Volume Shadow Copy Service (VSS) integration
   - Implement application-consistent backup mechanisms
The SQL Server container image runs on Linux; Windows applications connect over the network. Prepare Linux-compatible PVCs, SQL process write permissions and the existing sql-credentials Secret.
Create the example StorageClasses first. A Windows EBS class needs NTFS and WaitForFirstConsumer; the name alone does not install a driver or class.
</details>

## Hands-on Questions

1. Write a Deployment manifest that meets the following requirements for a mixed Windows and Linux node Kubernetes cluster:
   - Application name: web-app
   - Windows container image: mcr.microsoft.com/windows/servercore/iis:windowsservercore-ltsc2022
   - Replicas: 2
   - Port: 80
   - Environment variable: WEBSITE_NAME=MyWindowsApp
   - Volume: Mount ConfigMap "web-config" to C:\inetpub\wwwroot\web.config

<details>
<summary>Show Answer</summary>

**Answer:**

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

**Explanation:**

1. **Deployment Resource**:
   - Uses `nodeSelector` to specify scheduling only to Windows nodes
   - Sets 2 replicas as required
   - Uses IIS web server image

2. **Container Configuration**:
   - Exposes port 80
   - Sets environment variable `WEBSITE_NAME`
   - Mounts ConfigMap to specific file path (using Windows path format)

3. **Volume Configuration**:
   - Mounts ConfigMap as volume
   - Uses `subPath` to mount specific key from ConfigMap as file

4. **Service Definition**:
   - Creates ClusterIP service for accessing the application
   - Accessible through port 80

**Notes**:
- Escape backslashes only in double-quoted YAML strings; plain/single-quoted paths use single backslashes.
- Windows containers may have higher resource requirements than Linux containers, so it's good practice to set appropriate resource requests and limits in production environments.
Setting WEBSITE_NAME alone does not rename an IIS site. Provide the web.config key in the existing web-config ConfigMap; subPath mounts do not update automatically.
</details>

2. Write DaemonSet manifests for deploying monitoring agents that run on both Windows and Linux nodes. Each OS should use appropriate images and configurations.

<details>
<summary>Show Answer</summary>

**Answer:**

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

**Explanation:**

1. **DaemonSet for Linux Nodes**:
   - Uses `nodeSelector` to schedule only to Linux nodes
   - Uses Prometheus Node Exporter image
   - Mounts host's `/proc`, `/sys`, `/` directories to collect system metrics
   - Security context configured to run as non-root user

2. **DaemonSet for Windows Nodes**:
   - Uses `nodeSelector` to schedule only to Windows nodes
   - Uses Windows Exporter image
   - Specifies metric collectors to collect
   - Windows-specific configuration applied

3. **Common Service**:
   - Creates service selecting pods from both DaemonSets
   - Uses named targetPort metrics to resolve Linux port 9100 and Windows port 9182 per endpoint
   - Prometheus can scrape metrics through this service

**Notes**:
- It's important to use appropriate images and configurations for each OS.
- Since metric collection methods differ between Linux and Windows nodes, they are separated into different DaemonSets.
- Using labels to distinguish OS types is useful for filtering and visualizing metrics in the monitoring system.
- In production environments, additional configuration of resource requests and limits, security contexts, service accounts, etc. is needed.
Create the monitoring namespace and replace the exporter tag with a tested release. HostProcess runs with host privileges; scope its PSS exception and port 9182 firewall access to Prometheus sources. Prometheus must discover/scrape each Service endpoint to collect every node.
</details>

3. Write a pod manifest for deploying a .NET application that uses Active Directory authentication in a Windows container. Group Managed Service Accounts (gMSA) must be used.

<details>
<summary>Show Answer</summary>

**Answer:**

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

**Explanation:**

1. **gMSACredentialSpec and authorization**:
   - The prerequisite GMSACredentialSpec contains generated credential metadata, not the password
   - The webhook expands the named spec after checking the ServiceAccount use permission

2. **Windows Pod Configuration**:
   - Uses `nodeSelector` to schedule to Windows nodes
   - References gMSA credential spec using `securityContext.windowsOptions.gmsaCredentialSpecName`
   - Uses .NET application image
   - Appropriate resource requests and limits set

3. **Volumes and Configuration**:
   - Provides application settings using ConfigMap
   - Configuration file mounted using Windows path format
   - Includes SQL Server connection string using Windows integrated authentication

4. **Service Definition**:
   - Creates ClusterIP service for accessing the application

**Prerequisites for gMSA Setup:**

First create the chapter’s `gmsa-cred-spec` resource, `windows-app` ServiceAccount and resource-name-scoped use RBAC grant. The CRD and both webhooks are required. Build and validate the custom application image and configuration for Windows Server 2022. gMSA supplies network credentials; the application must also use Windows authentication. ConfigMap subPath mounts do not update automatically; recreate the Pod after configuration changes.
</details>

4. Write NetworkPolicy manifests that meet the following requirements in a cluster with mixed Windows and Linux nodes:
   - Windows web application pods (label: app=windows-web) can only access Linux database pods (label: app=linux-db)
   - Database pods allow access only on port 3306
   - Web application pods are accessible from external on port 80

<details>
<summary>Show Answer</summary>

**Answer:**

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

**Explanation:**

1. **Windows Web Application NetworkPolicy**:
   - Applies to pods with label `app=windows-web`
   - **Ingress rule**: Allows access from all sources on port 80
   - **Egress rule**: Allows access only to port 3306 on pods with label `app=linux-db`

2. **Linux Database NetworkPolicy**:
   - Applies to pods with label `app=linux-db`
   - **Ingress rule**: Allows access only from pods with label `app=windows-web` on port 3306

**Notes**:
- Network policies require a CNI plugin that supports NetworkPolicy (e.g., Calico, Antrea) to function.
- NetworkPolicy support on Windows nodes may vary depending on the CNI plugin.
- This example assumes the default namespace, but appropriate namespaces should be specified in real environments.
- In production environments, additional egress rules may be needed for DNS lookups, external service access, etc.

**Deployment Examples:**

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
NetworkPolicy allows are additive; another policy can grant additional access. A policy does not create an external LoadBalancer/Ingress. Applications using DNS also need UDP/TCP 53 egress to cluster DNS. The database example below is nonpersistent teaching material; a real service needs persistent storage and backups.
</details>

5. Write a Deployment manifest for a .NET Framework application running on Windows nodes. The application requires a connection string as an environment variable to access Azure Blob Storage. Also configure a persistent volume for logs.

<details>
<summary>Show Answer</summary>

**Answer:**

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

**Explanation:**

1. **Secret Configuration**:
   - Create azure-storage-secret from a protected source or external secret manager before deployment; no sample account key is provided
   - Accessible securely from application as environment variable

2. **PersistentVolumeClaim**:
   - Requests 10GB persistent storage for log files
   - Uses a Windows-compatible Azure Files SMB CSI storage class
   - Uses ReadWriteMany so replicas on different nodes can mount the share

3. **Deployment Configuration**:
   - Uses `nodeSelector` to schedule only to Windows nodes
   - Uses .NET Framework application image
   - Provides Azure Storage connection string through environment variables
   - Mounts persistent volume for log directory
   - Mounts web.config file from ConfigMap
   - Appropriate resource requests and limits set
   - Readiness and liveness probes configured for health checking

4. **ConfigMap Configuration**:
   - Provides web.config file for .NET Framework application
   - Includes application settings and configuration

5. **Service Definition**:
   - Creates ClusterIP service for accessing the application

**Notes**:
- In real environments, image registry addresses, storage classes, resource requirements, etc. should be adjusted for your environment.
- .NET Framework applications must use Windows Server Core based images.
- In production environments, external access can be configured through ingress controllers or load balancers.
- Sensitive information like Azure Storage connection strings should be integrated with external secret management systems like Azure Key Vault.
Configure replicas to write distinct filenames or Pod-specific subdirectories. The application must consume the environment variables and implement /health. ConfigMap subPath mounts do not update automatically.
</details>

## Advanced Topics

1. Which containerd 1.x setting selects the Windows Pod sandbox image?
   - A) sandbox_image setting
   - B) Log level and log path
   - C) Memory limits and CPU sharing
   - D) Image pull policy and registry configuration

<details>
<summary>Show Answer</summary>

**Answer: A) sandbox_image setting**

**Explanation:**

containerd 1.x uses `plugins."io.containerd.grpc.v1.cri".sandbox_image`. In containerd 2.x configuration v3, the setting is `plugins."io.containerd.cri.v1.images".pinned_images.sandbox`. Start from the installed runtime’s `containerd config default` and its Windows installation procedure; do not mix configuration-version tables.

The sandbox image must support the host Windows build. A Linux-only pause image cannot run on Windows. CNI/HNS configures networking, and the sandbox maintains the Pod network lifetime. Registry/image-pull configuration, the runhcs runtime, CNI paths and logging are also operationally important. Use the distribution’s tested Windows sandbox image rather than copying an old 3.6 tag.
</details>

2. What is the main benefit of using Hyper-V isolation mode in Windows containers?
   - A) Better performance and lower resource usage
   - B) Ability to run containers with different Windows versions than the host OS
   - C) Improved network communication speed between containers
   - D) Support for more Windows APIs and features

<details>
<summary>Show Answer</summary>

**Answer: B) Ability to run containers with different Windows versions than the host OS**

**Explanation:**
The main benefit of using Hyper-V isolation mode in Windows containers is the ability to run containers with different Windows versions than the host OS. This is one of the important characteristics of Windows containers and is particularly useful when running legacy applications on modern infrastructure.

Main benefits of Hyper-V isolation mode:

1. **Version Compatibility**:
   - Resolves version mismatch issues between host OS and container OS.
   - For example, you can run Windows Server 2019-based containers on a Windows Server 2022 host.
   - This is not possible in process isolation mode (process isolation requires the host and container to use the same kernel version).

2. **Enhanced Security Isolation**:
   - Each container runs in a lightweight virtual machine providing stronger isolation.
   - Security boundaries between containers and between containers and the host are strengthened.
   - Useful in multi-tenant environments or when running untrusted code.

3. **Kernel-Level Isolation**:
   - Each container has its own Windows kernel instance.
   - This provides kernel-level isolation so that kernel issues in one container do not affect other containers or the host.

**Kubernetes does not support Hyper-V isolation, and no Pod annotation enables it.** This discussion is Windows OS background knowledge.

Disadvantages of Hyper-V isolation mode:
- Uses more resources (memory, CPU).
- Longer startup time.
- Requires Hyper-V feature enabled on the host.

Issues with other options:
- Hyper-V isolation actually has lower performance and higher resource usage (A is incorrect).
- Network communication between containers is actually faster in process isolation mode (C is incorrect).
- Windows API and feature support depends on the container OS version, Hyper-V isolation itself does not provide more APIs (D is incorrect).
</details>

3. Which statement about pod networking when using Windows nodes in Kubernetes is correct?
   - A) Windows nodes do not use CNI plugins and use their own networking stack
   - B) Windows nodes use the same CNI plugins as Linux nodes but with different configuration
   - C) Windows nodes must always use host network mode
   - D) Windows nodes do not support overlay networks

<details>
<summary>Show Answer</summary>

**Answer: B) Windows nodes use the same CNI plugins as Linux nodes but with different configuration**

**Explanation:**
Windows nodes in Kubernetes can use the same CNI (Container Network Interface) plugins as Linux nodes, but the configuration is different because Windows has a different networking stack. This allows for a consistent networking model in mixed OS clusters while considering the characteristics of each OS.

Pod networking characteristics on Windows nodes:

1. **CNI Plugin Support**:
   - Windows nodes support several CNI plugins including Flannel, Calico, and Antrea.
   - These plugins are designed to work on both Linux and Windows nodes.
   - Each plugin provides Windows-specific components or settings.

2. **Networking Modes**:
   - Windows nodes generally support overlay networks (VXLAN, GENEVE, etc.).
   - Support various network modes including L2bridge, L2tunnel, overlay, etc.
   - Flannel's VXLAN mode is widely used on Windows nodes.

3. **Configuration Differences**:
   - Windows nodes use HNS (Host Network Service) to manage network configuration.
   - Network endpoint creation and management methods differ from Linux.
   - Some advanced networking features may be limited on Windows.

Example - Flannel CNI configuration:
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

Additional configuration may be needed on Windows nodes:
```powershell
# Script running on Windows nodes
$env:KUBE_NETWORK = "cbr0"
$networkName = "vxlan0"
$networkMode = "overlay"
```

Issues with other options:
- Windows nodes use CNI plugins and do not use only their own networking stack (A is incorrect).
- Regular Windows Pods cannot use hostNetwork; HostProcess is the exception (C is incorrect).
- Windows nodes support overlay networks (VXLAN, etc.) (D is incorrect).
</details>

4. Which statement about resource management on Windows nodes in Kubernetes is correct?
   - A) Windows nodes do not support resource limits
   - B) Windows nodes provide more accurate resource limits than Linux nodes
   - C) Windows nodes implement resource limits using Job Objects
   - D) Windows nodes implement resource limits using cgroups

<details>
<summary>Show Answer</summary>

**Answer: C) Windows nodes implement resource limits using Job Objects**

**Explanation:**
Windows nodes in Kubernetes use Job Objects, a Windows operating system feature, to implement resource limits for containers. This contrasts with Linux nodes which use cgroups.

Resource management characteristics on Windows nodes:

1. **Job Objects**:
   - Windows uses Job Objects to limit resource usage of process groups.
   - Container runtimes (Windows-compatible containerd) use the Job Objects API to apply CPU and memory limits.
   - Job Objects can limit CPU time, memory usage, work time, etc. for process groups.

2. **CPU Limits**:
   - CPU limits cap CPU time; do not confuse limits with relative CPU sharing weights.
   - This is similar to Linux CPU sharing but implemented differently.
   - Windows adjusts CPU sharing based on the number of CPU cores.

3. **Memory Limits**:
   - Windows container memory limits use Job Objects.
   - Windows has no Linux OOM killer; exceeding available memory can cause allocation failures or paging and degraded performance.
   - Windows memory management works differently from Linux, so the actual behavior may differ even with the same memory limit value.

4. **Resource Request and Limit Configuration**:
   - Windows pods specify resource requests and limits the same way as Linux pods:
     ```yaml
     resources:
       requests:
         memory: "2Gi"
         cpu: "500m"
       limits:
         memory: "4Gi"
         cpu: "1"
     ```
   - kubelet passes these values to the Windows container runtime, and the runtime uses Job Objects to apply the limits.

5. **Monitoring and Reporting**:
   - kubelet monitors container resource usage using Windows performance counters.
   - This information can be viewed through `kubectl top pods` and `kubectl top nodes` commands.
   - Metrics server collects this information and provides it through the Kubernetes API.

Considerations for resource management on Windows nodes:
- Windows containers generally use more default resources than Linux containers.
- Memory overhead for Windows containers may be greater, so ensure sufficient memory headroom.
- Exact behavior of resource limits may vary depending on Windows version.

Issues with other options:
- Windows nodes support resource limits (A is incorrect).
- Neither OS universally provides more accurate resource limits; the mechanisms differ (B is incorrect).
- Windows nodes use Job Objects, not cgroups (D is incorrect).
</details>

5. Which of the following is NOT an appropriate security best practice when using Windows nodes in Kubernetes?
   - A) Regularly scan and update container images to resolve security vulnerabilities
   - B) Enable privileged mode for all Windows pods
   - C) Use gMSA (Group Managed Service Accounts) for Active Directory integration
   - D) Use network policies to restrict pod-to-pod communication

<details>
<summary>Show Answer</summary>

**Answer: B) Enable privileged mode for all Windows pods**

**Explanation:**
"Enable privileged mode for all Windows pods" is NOT an appropriate security best practice when using Windows nodes in Kubernetes. In fact, Windows containers do not support privileged mode, and attempting to set this will cause pod creation to fail.

Reasons why this option is inappropriate:

1. **Privileged Mode Not Supported**:
   - Windows containers do not support the concept of privileged mode like Linux containers.
   - Windows uses HostProcess for trusted host-level agents; it is distinct from the privileged flag.

2. **Violates Principle of Least Privilege**:
   - Even if it were supported, enabling privileged mode for all pods violates the principle of least privilege.
   - Each workload should have only the minimum permissions needed.

3. **Increased Security Risk**:
   - Privileged mode allows containers to access the host system, greatly increasing security risks.
   - If a container escape vulnerability occurs, the entire host system could be exposed to risk.

All other options are appropriate security best practices:

A) **Regularly scan and update container images to resolve security vulnerabilities**:
   - Image scanning is important for identifying and resolving known vulnerabilities.
   - Windows images should receive regular security updates.
   - It's good practice to integrate image scanning tools into CI/CD pipelines.

C) **Use gMSA (Group Managed Service Accounts) for Active Directory integration**:
   - gMSA allows Windows containers to securely authenticate to Active Directory services.
   - Using gMSA instead of hardcoded credentials improves security.
   - Provides automatic password management and rotation functionality.

D) **Use network policies to restrict pod-to-pod communication**:
   - Network policies apply the principle of least privilege to network communication.
   - Restricting pod-to-pod communication to only necessary cases reduces the attack surface.
   - Network segmentation helps prevent lateral movement attacks.

Additional best practices for strengthening Windows node security:
- Keep Windows nodes updated with latest security patches
- Disable unnecessary Windows features and roles
- Configure Windows firewall rules appropriately
- Use strong authentication mechanisms
- Remove unnecessary tools and components from container images
- Implement runtime security monitoring
</details>

## Verification References

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
