# Kubernetes における Windows クイズ

このクイズでは、Kubernetes で Windows node（ノード）と workload を管理するための概念的および実践的な知識を確認します。Windows container の基本、Kubernetes における Windows node 構成、networking、storage、security、monitoring などのトピックを扱います。

## 選択問題

1. Kubernetes の Windows node でサポートされている container runtime はどれですか？
   - A) Windows CRI に対応した containerd
   - B) CRI-O と Docker
   - C) containerd と CRI-O
   - D) Docker、containerd、gVisor

<details>
<summary>回答を表示</summary>

**回答: A) Windows CRI に対応した containerd**

**解説:**
Kubernetes の Windows node で公式にサポートされる container runtime は、Windows CRI 対応の containerd です。

- containerd は Windows node で現在推奨される軽量で安定した runtime であり、Kubernetes 1.20 以降で公式サポートされています。
- CRI-O は Windows node では公式サポートされていません。主に Linux container 向けの CRI 実装です。
- gVisor は container 分離用の sandbox runtime ですが、現在 Windows node ではサポートされていません。

runtime を設定する際は、使用する Kubernetes version との互換性を確認してください。
</details>

2. Kubernetes で Windows node と Linux node が混在する cluster を構成する場合、どの network solution が必要ですか？
   - A) すべての CNI plugin が Windows node と Linux node の両方をサポートする
   - B) Flannel、Calico、Antrea など、Windows をサポートする CNI plugin
   - C) Windows node は CNI plugin なしで kubenet のみを使用する必要がある
   - D) Windows node は常に host network mode のみを使用する必要がある

<details>
<summary>回答を表示</summary>

**回答: B) Flannel、Calico、Antrea など Windows をサポートする CNI plugin**

**解説:**
Windows と Linux が混在する cluster では、Windows node に対応した CNI plugin が必要です。すべての CNI plugin が Windows に対応しているわけではありません。

- Flannel は VXLAN overlay mode、Calico は BGP または VXLAN mode、Antrea は OVS (Open vSwitch) を使う構成で Windows node をサポートします。
- Azure CNI と AWS VPC CNI も、それぞれの環境で Windows をサポートします。
- Windows の networking stack は Linux と異なり、利用できる機能や version ごとの要件は plugin によって異なります。導入前に対応 version と構成条件を確認してください。

kubenet は Windows ではサポートされません。通常の Windows Pod は `hostNetwork` を使えません。HostProcess Pod は例外で、`hostNetwork: true` が必要です。
</details>

3. Kubernetes は Windows application container でどの isolation mode をサポートしますか？
   - A) Hyper-V isolation
   - B) Process isolation
   - C) Virtual machine isolation
   - D) Sandbox isolation

<details>
<summary>回答を表示</summary>

**回答: B) Process isolation**

**解説:**
Kubernetes が Windows application container でサポートするのは process isolation です。container は host OS の kernel を共有し、独立した process group として動作します。

- host OS と同じ kernel version が必要です。
- resource 使用量が少なく、起動も速い方式です。Linux container の一般的な isolation model とも似ています。
- Windows OS 自体には Hyper-V isolation もあります。各 container を軽量 VM 内で動かし、異なる kernel version を利用できますが、resource overhead が増えます。

ただし Kubernetes は Hyper-V isolation をサポートしていません。これを有効にする Pod annotation もありません。Virtual machine isolation は Windows container の公式な isolation mode ではなく、sandbox isolation も Windows container の用語ではありません。
</details>

4. Kubernetes で Windows node を使用する際の制限として正しくないものはどれですか？
   - A) privileged container を使用できない
   - B) HostPath volume を使用できない
   - C) Pod の SecurityContext 機能は一部のみサポートされる
   - D) Windows container 間で process namespace を共有できない

<details>
<summary>回答を表示</summary>

**回答: B) HostPath volume を使用できない**

**解説:**
HostPath volume は Windows node でも利用できます。「使用できない」という B の記述が、正しくない制限です。HostPath では Windows path format を使います。

Windows node では、privileged flag はサポートされません。host access を要する信頼済み node agent には HostProcess を使えます。SecurityContext も一部のみがサポートされ、たとえば `runAsUser`、`runAsGroup`、`fsGroup`、seccomp、SELinux などは利用できません。

同じ Pod 内の container は networking と `localhost` を共有しますが、process namespace や root filesystem は共有しません。Linux と Windows の node すべてに DaemonSet を配置する場合は、OS ごとの `nodeSelector` などで対象 node を分けてください。storage driver や volume type にも制約があり、Linux 固有の alpha/beta feature が Windows で動かないことがあります。

HostPath の Windows path 形式の例:
```yaml
volumes:
- name: data
  hostPath:
    path: 'C:\data'
```
</details>

5. Kubernetes で Windows node を識別するために使用される node label は何ですか？
   - A) kubernetes.io/os=windows
   - B) beta.kubernetes.io/os=windows
   - C) node.kubernetes.io/windows=true
   - D) kubernetes.io/windows=enabled

<details>
<summary>回答を表示</summary>

**回答: A) kubernetes.io/os=windows**

**解説:**
Kubernetes で Windows node を識別するために使用される標準の node label は `kubernetes.io/os=windows` です。この label は node の operating system type を示し、Kubernetes scheduler が Pod を適切な node に配置するために使用されます。

Windows Pod を Windows node に schedule するには、次のように nodeSelector を使用します。
```yaml
nodeSelector:
  kubernetes.io/os: windows
```

または node affinity を使用できます。
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

`beta.kubernetes.io/os=windows` は以前の Kubernetes バージョンで使用されていましたが、現在は非推奨です。

`node.kubernetes.io/windows=true` と `kubernetes.io/windows=enabled` は標準の Kubernetes label ではありません。

注: Linux node には `kubernetes.io/os=linux` label があります。
</details>

6. 従来型の Windows application 向けに、Nano Server より広い Windows API を提供する Microsoft base image はどれですか？
   - A) mcr.microsoft.com/windows/servercore
   - B) mcr.microsoft.com/windows/nanoserver
   - C) mcr.microsoft.com/dotnet/framework/runtime
   - D) mcr.microsoft.com/powershell

<details>
<summary>回答を表示</summary>

**回答: A) `mcr.microsoft.com/windows/servercore`**

**解説:**
Kubernetes が既定の base image を選ぶわけではありません。従来型の Windows application には、ほとんどの Windows application の実行に必要な component を含む Windows Server Core が有力な選択肢です。

1. **Windows Server Core** (`mcr.microsoft.com/windows/servercore`): image size は release、layer、圧縮方式によって変わり、多くの Windows application をサポートします。Windows PowerShell を含みますが、必要な .NET Framework runtime image は別途選択してください。広く使われる Windows base image です。
2. **Nano Server** (`mcr.microsoft.com/windows/nanoserver`): Windows API の範囲が限られ、.NET Core application などに適します。attack surface を小さくできます。image size は version と layer によって異なります。
3. **.NET Framework** (`mcr.microsoft.com/dotnet/framework/runtime`): .NET Framework application 向けで、Server Core をベースに特定の .NET Framework version を含みます。
4. **PowerShell** (`mcr.microsoft.com/powershell`): PowerShell script を実行する image で、Nano Server または Server Core ベースがあります。

選択時には必要な Windows API、size と起動時間、security、image tag と host OS の version compatibility を確認してください。Windows image は host OS と同一または互換性のある version が必要です。
</details>

7. Kubernetes で Windows node と Linux node が混在する cluster に DaemonSets を deploy する推奨方法は何ですか？
   - A) 単一の DaemonSet を使用してすべての node に deploy する
   - B) OS ごとに個別の DaemonSets を作成し、nodeSelector を使用する
   - C) Windows node には DaemonSet の代わりに StatefulSet を使用する
   - D) すべての DaemonSets に tolerations を追加する

<details>
<summary>回答を表示</summary>

**回答: B) OS ごとに個別の DaemonSets を作成し、nodeSelector を使用する**

**解説:**
Kubernetes で Windows node と Linux node が混在する cluster に DaemonSets を deploy する推奨方法は、OS ごとに個別の DaemonSets を作成し、nodeSelector を使用することです。

この approach が必要な理由:
- Windows container と Linux container は異なる image format を使用します。
- 同じ application でも OS ごとに異なる configuration が必要になる場合があります。
- 一部の機能は特定の OS でのみ利用できる場合があります。

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

単一の DaemonSet を使用すると、container image の互換性問題により、一部の node で Pod の起動に失敗する可能性があります。

DaemonSets は Windows node で使用できるため、StatefulSets に置き換える必要はありません。

すべての DaemonSets に tolerations を追加すると、taint された node に Pod を schedule するのに役立ちますが、OS の互換性問題は解決しません。
</details>

8. Windows node 上の Pod の DNS configuration について正しい記述はどれですか？
   - A) DNS configuration は Windows node でサポートされていない
   - B) Windows node は CoreDNS の代わりに Windows DNS Server を使用する必要がある
   - C) Windows Pod は Windows DNS suffix の制約のもとで CoreDNS を利用できる
   - D) Windows node では Pod ごとに個別の DNS server configuration が必要である

<details>
<summary>回答を表示</summary>

**回答: C) Windows Pod は Windows DNS suffix の制約のもとで CoreDNS を利用できる**

**解説:**
Windows Pod も CoreDNS など cluster DNS を利用できますが、Windows の DNS suffix の動作は Linux と異なります。同じ namespace の Service なら短い Service 名を使えます。別 namespace などでは完全修飾名 (FQDN) を使ってください。ドットを含む部分名には Linux の search list と同じ補完動作が適用されません。

Windows は `/etc/resolv.conf` ではなく HNS/DNS 設定と単一の namespace suffix を使います。`dnsPolicy` と `dnsConfig` field で Pod の DNS を構成できます。

例:
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

Windows container では `nslookup` や `Resolve-DnsName` などを利用できます。network plugin の DNS 対応を確認してください。Windows node に別の DNS server を設置する必要はなく、Kubernetes の標準 DNS 機構を利用できます。
</details>

9. Windows node 上の pod-to-pod communication について正しい記述はどれですか？
   - A) pod-to-pod communication は Windows node でサポートされていない
   - B) Windows node 上の Pod は同じ node 上の Pod としか通信できない
   - C) Windows node 上の Pod は Linux node 上の Pod と通信できない
   - D) Windows node 上の Pod は CNI plugin を通じて他のすべての Pod と通信できる

<details>
<summary>回答を表示</summary>

**回答: D) Windows node 上の Pod は、対応する CNI plugin を通じて他の Pod と通信できる**

**解説:**
適切な CNI plugin が構成されていれば、Windows Pod は同じ node、別の Windows node、Linux node 上の Pod と cluster 内で通信できます。各 Pod には cluster CIDR 内の IP address が割り当てられ、Service は名前で参照できます。

Windows の Pod 間通信をサポートする CNI には Flannel、Calico、Antrea、Azure CNI、AWS VPC CNI があります。Flannel VXLAN mode では、Pod 間 traffic は node 間で VXLAN encapsulation されます。高度な networking 機能や NetworkPolicy の対応範囲は CNI ごとに異なります。Windows firewall rule が通信を妨げないよう確認してください。
</details>

10. Kubernetes における Windows container の resource limits について正しい記述はどれですか？
    - A) Windows container は resource limits をサポートしていない
    - B) CPU limits はサポートされるが memory limits はサポートされない
    - C) Memory limits はサポートされるが CPU limits はサポートされない
    - D) CPU と memory limits の両方がサポートされる

<details>
<summary>回答を表示</summary>

**回答: D) CPU と memory の両方の limit がサポートされる**

**解説:**
Kubernetes の Windows container は CPU と memory の request と limit を設定できます。次の例のように指定します。

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

Windows は CPU limit と CPU sharing を実装します。memory を超過した場合、Linux の OOM killer のように container を終了させるのではなく、allocation failure や paging、性能低下につながることがあります。kubelet は resource usage を監視し、Kubernetes API に報告します。

Windows container は Linux container より既定の resource overhead が大きい場合があり、limit の挙動は Windows version によって異なることがあります。`kubectl top pods` と `kubectl top nodes` で使用状況を確認できます。Kubernetes は Hyper-V isolation をサポートしません。
</details>

## 短答問題

1. Kubernetes cluster に Windows node を追加するための主な手順と要件を説明してください。

<details>
<summary>回答を表示</summary>

**回答:**

**Kubernetes cluster に Windows node を追加する手順:**

1. **前提条件を確認:** 対応する Kubernetes/Windows の組み合わせを使います。upstream v1.37 は Windows Server 2022/2025 をサポートします。control plane は Linux node 上で稼働させ、この章の `ltsc2022` の例では Windows Server 2022 を使います。Windows 対応 CNI plugin も必要です。
2. **Networking を構成:** Windows 対応 CNI を install し、cluster CIDR と service CIDR を設定します。次は Linux 側の Flannel 設定例です。Windows CNI は別途 install してください。
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
3. **Windows node を準備:** Windows Server を install/update し、必要な feature を有効にします。
     ```powershell
     Install-WindowsFeature -Name Containers
     Restart-Computer -Force
     ```
container runtime は containerd を推奨します。
     ```powershell
     # Use the reviewed sig-windows-tools installation procedure in the chapter.
     # Install-Containerd.ps1: supported runtime; PrepareNode.ps1: matching kubeadm/kubelet.
     # Do not start kubelet with an empty configuration.
     ```
4. **kubelet と kube-proxy を install:** Kubernetes binary を取得します。
     ```powershell
     # Use the reviewed sig-windows-tools installation procedure in the chapter.
     # Install-Containerd.ps1: supported runtime; PrepareNode.ps1: matching kubeadm/kubelet.
     # Do not start kubelet with an empty configuration.
     ```
kubelet configuration file を作成します。
     ```powershell
     # Use the reviewed sig-windows-tools installation procedure in the chapter.
     # Install-Containerd.ps1: supported runtime; PrepareNode.ps1: matching kubeadm/kubelet.
     # Do not start kubelet with an empty configuration.
     ```
kubelet service を登録して起動します。
     ```powershell
     # Use the reviewed sig-windows-tools installation procedure in the chapter.
     # Install-Containerd.ps1: supported runtime; PrepareNode.ps1: matching kubeadm/kubelet.
     # Do not start kubelet with an empty configuration.
     ```
kube-proxy も構成して起動します (通常は DaemonSet として deploy)。
5. **node を join:** kubeadm join を実行するか、TLS certificate と kubeconfig を手動で構成します。node の登録を確認します。
     ```bash
     kubectl get nodes
     ```
6. **node label を追加:** 自動で付かない場合は `kubernetes.io/os=windows` を設定します。
     ```bash
     kubectl label node <windows-node-name> kubernetes.io/os=windows
     ```
7. **test workload を deploy:** Windows container を使う簡単な Pod を起動します。
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

**重要な考慮事項:** Windows と image の version compatibility、Windows 対応 CNI と network policy、必要な port、storage driver/CSI 対応、Windows 用 monitoring と event log 収集、firewall/security group、必要な場合の gMSA、provisioning と node upgrade の自動化を確認します。provisioning は Ansible や PowerShell DSC などで自動化できます。
</details>

2. Windows container と Linux container の主な違い、および Kubernetes でこれらの違いを管理する方法を説明してください。

<details>
<summary>回答を表示</summary>

**回答:**

**Windows container と Linux container の主な違い:**

1. **基盤技術:** Linux は namespace、cgroup、kernel feature を使います。Windows は Job Objects など Windows の isolation 技術を使います。
2. **image:** Linux image は数十〜数百 MB のものがあり、さまざまな Linux distribution 上で実行できます。Windows image は通常より大きく、数 GB になる場合があります。
3. **isolation:** Linux は通常 namespace-based isolation を使い、他の sandbox runtime もあります。Kubernetes の Windows container では process isolation がサポートされます。Hyper-V isolation は Windows の機能ですが Kubernetes のサポート対象外です。
4. **filesystem:** Linux は OverlayFS などの layered filesystem、Windows は NTFS-based filter driver を使います。
5. **networking:** OS ごとに利用できる mode や driver が異なり、Windows node では Windows 対応 CNI が必要です。
6. **resource management:** Linux は cgroup、Windows は Job Objects を使い、制約にも差があります。
7. **security context:** Windows で使える option は限られ、privileged container はサポートされません。
8. **host OS 依存性:** Windows container image は host OS と同一または互換性のある version が必要です。

**Kubernetes で差異を扱う方法:**

1. **node selection:** `kubernetes.io/os` label と nodeSelector を使います。
     ```yaml
     os:
       name: windows
     nodeSelector:
       kubernetes.io/os: windows
     ```
必要に応じて node affinity も指定します。
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
2. **workload separation:** OS ごとに Deployment を分けます。
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
3. **DaemonSet:** OS ごとに DaemonSet を分けます。
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
4. **image:** multi-architecture tag または OS ごとの image tag (例: `myapp:linux`、`myapp:windows`) を使い、必要に応じて `imagePullPolicy: Always` を設定します。
5. **resource request/limit:** 各 OS に合わせて設定します。
     ```yaml
     resources:
       requests:
         memory: "2Gi"  # Windows containers typically need more memory
         cpu: "500m"
       limits:
         memory: "4Gi"
         cpu: "1"
     ```
6. **networking:** Windows 対応 CNI を選び、NetworkPolicy の対応範囲を確認します。
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
7. **storage:** OS 対応 storage class を使います。
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
8. **security context:** 各 OS でサポートされる security setting を使います。
     ```yaml
     # Security context for Linux pods
     securityContext:
       runAsUser: 1000
       runAsGroup: 3000
       fsGroup: 2000

     # These Linux-only fields are rejected with spec.os.name: windows.
     ```
9. **monitoring/logging:** OS ごとの agent と log path を構成します。
10. **CI/CD:** OS ごとの build/test と multi-OS deploy strategy を用意します。
</details>

3. Windows container で Group Managed Service Accounts (gMSA) を使用する方法とその benefits を説明してください。

<details>
<summary>回答を表示</summary>

**回答:**

**Group Managed Service Account (gMSA) の概要:**
gMSA は Windows domain で service authentication に使う Active Directory account です。Windows container 内の application が AD、Kerberos、SQL Server integrated authentication などを必要とするときに利用します。container 自体を domain に join するものではありません。

**Windows container で gMSA を使う手順:**

1. AD/DNS connectivity と対応する credential retrieval method を準備します。domain-joined host を使う方法、または別途構成した portable identity provider を使う方法があります。container 自体は domain join できません。
2. `Get-KdsRootKey` で KDS root key を確認します。必要な場合のみ AD administrator が作成し、最大 10 時間の replication time を見込みます。10 時間遡らせる手順は single-DC の test environment に限ります。
3. password retrieval 権限は専用の authorized-host group に付与し、すべての Domain Computers には付与しません。CredentialSpec module の `New-CredentialSpec` で実際の SID、GUID、DNS/NetBIOS 値を含む spec を生成します。
4. GMSACredentialSpec CRD と mutating/validating webhook を install します。生成した JSON は `windows.k8s.io/v1` の `GMSACredentialSpec.credspec` に保存します。これは Kubernetes Secret ではなく、gMSA password も含みません。
5. 対象 resource に対する `use` 権限を ServiceAccount に与え、Pod の `serviceAccountName` と `windowsOptions.gmsaCredentialSpecName` を設定します。
6. 実際の application で Kerberos authentication を検証し、`klist` を確認します。`whoami` が示すのは local process user であり、network identity の gMSA ではありません。

詳しい生成 resource と RBAC の例は、[章の gMSA 手順](../../core/10-windows-in-kubernetes.md)を参照してください。

**gMSA の利点:** hardcoded credential を container に埋め込まずに済み、password の管理・rotation は AD が行います。最小権限を適用しやすく、既存の Windows authentication application、Kerberos/NTLM、domain resource access に使えます。AD に identity 管理を集約し、group policy と audit/compliance に活用できます。legacy .NET application、SQL Server integrated authentication、IIS web application と互換性があり、credential は container restart 後も利用でき、複数 container で同じ identity を共有できます。

**考慮事項:** Windows node から domain controller への network/DNS と Kerberos/LDAP 等の port、gMSA の最小権限と group membership、定期的な permission review、cluster 規模に応じた domain controller load と権限分離用の複数 gMSA、domain connectivity・credential spec・container runtime log を使った troubleshooting を確認してください。
</details>

4. Kubernetes の Windows node に対する logging と monitoring の構成方法、および Linux node との違いを説明してください。

<details>
<summary>回答を表示</summary>

**回答:**

**Windows node の logging と monitoring:**

**1. Logging**
主な source は Windows Event Log (System/Application/Security)、ETW event、`C:\` 内の application log file、kubelet と container runtime log (`C:\k\logs` など) です。

- **Fluent Bit/Fluentd:** 章の Windows service または確認済み HostProcess collector で host event log を読み取ります。`.evtx` file を通常 container に mount するだけでは host の Event Log API は利用できません。下の input は Security log の read 権限と永続 checkpoint directory を必要とします。
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
- **Windows Event Log collection:**
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
- **container log:** containerd の CRI log は `C:\var\log\containers`、kubelet log は `C:\k\logs` または Windows Event Log を確認します。

**2. Monitoring**
CPU、memory、disk、network、process count、page file、container resource を監視します。

- **Windows Exporter:**
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
- **Prometheus scrape:**
```powershell
# Check kubelet logs
Get-EventLog -LogName Application -Source kubelet -Newest 50

# Check containerd status
Get-Service containerd

# Verify network connectivity
Test-NetConnection -ComputerName api.kubernetes.cluster -Port 443
```
- Grafana で page file usage や service status など Windows 固有 panel を追加します。

**3. Troubleshooting**
PowerShell (`Get-Process`、`Get-Service`、`Get-EventLog`)、PerfMon、Event Viewer を使います。Windows node の `kubectl debug` は制約があります。

**Linux node との違い:** Linux log は通常 `/var/log/` の text file を tail/read して収集しますが、Windows Event Log は binary format のため Windows Event Log API が必要です。Linux metric collector は `/proc` と `/sys` を読み取る一方、Windows では WMI または Performance Counter API を使います。resource 使用量は Linux では cgroup、Windows では Job Objects を使って観測し、一部の metric の計算方法も異なります。Windows 固有の agent が必要で、対応 agent はより限られます。Linux の `ps`、`top`、`netstat`、`strace` に相当する調査では、PowerShell、GUI tool、限られた CLI tool を使います。container の stdout/stderr も CRI log として収集されます。ETW/file log は application または host collector が必要です。

**Best practice:** EFK (Elasticsearch、Fluent Bit、Kibana) や ELK stack のような統合 logging を使い、Windows/Linux で個別の設定をします。Prometheus と Grafana で全 node を監視し、OS ごとの dashboard を作成します。Windows 固有 event と重要な service 状態に alert を設定し、Event Log の size/retention と log rotation を構成します。Security event log を収集・分析し、permission 変更と login attempt を監視します。Prometheus を利用する場合は monitoring namespace、Prometheus Operator/ServiceMonitor discovery、検証済み release tag を確認してください。HostProcess の PSS exception と port 9182 の firewall source は必要最小限にします。host log path/channel は distribution ごとに確認し、EKS Windows では kubelet/kube-proxy log の収集元も確認してください。Elasticsearch 例には信頼する CA と authentication configuration が必要です。
</details>

5. Kubernetes の Windows container における storage options と volume mount configuration methods を説明してください。

<details>
<summary>回答を表示</summary>

**回答:**

**Windows container の storage:**

**1. 基本 volume type**
1. **emptyDir:** Pod の lifetime 中だけ使う一時データを Windows node の local NTFS volume に保存します。Pod 削除時に失われます。
   ```yaml
   volumes:
   - name: temp-data
     emptyDir: {}
   ```
2. **hostPath:** Windows node の filesystem に直接 access します。YAML の double-quoted path では backslash を escape しますが、plain/single-quoted path では通常の backslash を使います。node 間で共有されません。
   ```yaml
   volumes:
   - name: logs
     hostPath:
       path: 'C:\Logs'
       type: DirectoryOrCreate
   ```
3. **ConfigMap/Secret:** 設定や機密情報を保存します。Windows container でも利用できますが、file permission は Windows の方式で適用されます。
   ```yaml
   volumes:
   - name: config
     configMap:
       name: app-config
   ```
4. **PVC:** 永続 storage を要求します。Windows 対応 StorageClass と CSI driver が必要です。
   ```yaml
   volumes:
   - name: data
     persistentVolumeClaim:
       claimName: windows-pvc
   ```

**2. Windows container 対応 storage**
- **Azure Disk/File (AKS):** Windows node と Azure Disk CSI を使えます。SMB protocol の Azure Files も利用できます。
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
- **AWS EBS (EKS):** EBS CSI driver の Windows 対応を確認します。volume access は単一 AZ 内です。
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
- **SMB/CIFS:** Windows 対応 SMB CSI driver が必要で、複数 Pod 間の ReadWriteMany を提供できます。
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
- **iSCSI:** Windows に iSCSI 機能があることは、Kubernetes の in-tree `iscsi` volume plugin が使えることを意味しません。Windows filesystem volume を明示的にサポートする storage vendor の CSI driver を使います。Windows Pod は raw block `volumeDevices` をサポートしません。

**3. Windows container の mount**
通常 `C:\` drive 配下の Windows path を使います。double-quoted YAML string だけ backslash を escape してください。
   ```yaml
   volumeMounts:
   - name: data
     mountPath: 'C:\data'
   ```
Read-only mount は NTFS permission によって適用されます。
   ```yaml
   volumeMounts:
   - name: config
     mountPath: 'C:\config'
     readOnly: true
   ```
volume の特定 subpath を mount できます。Windows path separator を確認してください。
   ```yaml
   volumeMounts:
   - name: shared-data
     mountPath: 'C:\app\logs'
     subPath: logs
   ```

**4. 構成例**
- **Web application:**
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
- **Database:**
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

この SQL Server container image は Linux 上で動作するため、Windows application から network 経由で接続します。Linux 対応 PVC、SQL process の write permission、および既存の `sql-credentials` Secret を準備してください。例で使う StorageClass は先に作成します。Windows EBS class には NTFS と `WaitForFirstConsumer` が必要で、class 名だけでは driver/class は install されません。

**storage を使う際の考慮事項:** Windows path の backslash は double-quoted YAML string 内だけ escape し、plain または single-quoted string では通常の backslash を使います。forward slash (`/`) も使えますが、application が対応することを確認してください。Windows は NTFS permission model を使い、Linux の `chmod`/`chown` と同じ設定はできません。permission は container 内の user context で決まります。SMB/CIFS など network storage には latency があり、高い性能が必要なら local storage または直接接続された block storage を検討します。storage class と CSI driver の Windows 対応を確認し、Windows Volume Shadow Copy Service (VSS) との連携や application-consistent backup を実装してください。
</details>

## ハンズオン問題

1. Windows node と Linux node が混在する Kubernetes cluster 向けに、次の要件を満たす Deployment manifest を作成してください:
   - Application name: web-app
   - Windows container image: mcr.microsoft.com/windows/servercore/iis:windowsservercore-ltsc2022
   - Replicas: 2
   - Port: 80
   - Environment variable: WEBSITE_NAME=MyWindowsApp
   - Volume: ConfigMap "web-config" を C:\inetpub\wwwroot\web.config にマウント

<details>
<summary>回答を表示</summary>

**回答:**

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

**解説:** Windows Server 2022 (`ltsc2022`) の IIS image を使い、Windows node に 2 replica を配置します。ConfigMap の `web-config` を `subPath` で `C:\inetpub\wwwroot\web.config` に mount します。`WEBSITE_NAME` environment variable を設定するだけでは IIS site 名は変更されません。ConfigMap には `web.config` key を用意してください。`subPath` mount は自動更新されないため、変更後は Pod を再作成します。
</details>

2. Windows node と Linux node の両方で実行される monitoring agent を deploy する DaemonSet manifest を作成してください。各 OS は適切な image と configuration を使用する必要があります。

<details>
<summary>回答を表示</summary>

**回答:**

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

**解説:** Linux と Windows は個別の DaemonSet で管理します。共通 Service は named `targetPort` を使い、endpoint ごとに Linux exporter の 9100 と Windows exporter の 9182 を解決します。両方の port を同時に公開する設定ではありません。monitoring namespace と Prometheus Operator/ServiceMonitor discovery を用意し、image tag は検証済み release に置き換えてください。HostProcess は host privilege を持つため PSS exception を限定し、9182 の firewall access を Prometheus source のみに絞ります。
</details>

3. Windows container で Active Directory authentication を使用する .NET application を deploy する Pod manifest を作成してください。Group Managed Service Accounts (gMSA) を使用する必要があります。

<details>
<summary>回答を表示</summary>

**回答:**

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

**解説:** この例は章の `gmsa-cred-spec`、`windows-app` ServiceAccount、および resource 名を限定した `use` RBAC grant を前提とします。CRD と mutating/validating webhook が必要です。Windows Server 2022 用の custom application image と設定を build/validate し、application が Windows authentication を実際に使用するよう構成してください。gMSA は network credential を提供します。ConfigMap の `subPath` mount は自動更新されないため、変更時は Pod を再作成します。
</details>

4. Windows node と Linux node が混在する cluster で、次の要件を満たす NetworkPolicy manifest を作成してください:
   - Windows web application pods (label: app=windows-web) は Linux database pods (label: app=linux-db) のみに access できる
   - Database pods は port 3306 の access のみを許可する
   - Web application pods は外部から port 80 で access 可能

<details>
<summary>回答を表示</summary>

**回答:**

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

**解説:** NetworkPolicy の rule は加算的です。この policy は外部 LoadBalancer/Ingress を作成しません。外部公開には対応する Service または Ingress を別に構成します。DNS を使う application には cluster DNS 宛て UDP/TCP 53 の egress rule も必要です。この Linux database manifest は学習用で、永続 storage や backup は含みません。実運用では永続化と backup を設計してください。

Windows web application Pod:
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
Linux database Pod:
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

5. Windows node 上で実行される .NET Framework application の Deployment manifest を作成してください。この application は Azure Blob Storage に access するために connection string を environment variable として必要とします。また、logs 用の persistent volume も構成してください。

<details>
<summary>回答を表示</summary>

**回答:**

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

**解説:** connection string の値を manifest に直接書かず、保護された source または external secret manager から既存 Secret を作成してください。application は Secret の environment variable を読み取り、`/health` endpoint を実装します。ConfigMap の `subPath` mount は自動更新されないため、設定変更後に Pod を再作成します。replica ごとに log file 名または subdirectory を分け、複数 Pod が同じ file を競合して書き込まないようにします。
</details>

## 高度なトピック

1. Kubernetes の Windows node で containerd を container runtime として構成する際に最も重要な setting は何ですか？
   - A) sandbox_image setting
   - B) Log level と log path
   - C) Memory limits と CPU sharing
   - D) Image pull policy と registry configuration

<details>
<summary>回答を表示</summary>

**回答: A) sandbox_image setting**

**解説:**
containerd 1.x では `plugins."io.containerd.grpc.v1.cri".sandbox_image` を使います。containerd 2.x の config v3 では `plugins."io.containerd.cri.v1.images".pinned_images.sandbox` に設定します。install 済み runtime の `containerd config default` と Windows install procedure を起点にし、異なる config version の table を混ぜないでください。

sandbox image は host の Windows build に対応する必要があり、Linux 専用 pause image は Windows では動きません。sandbox は Pod network の lifetime を維持し、networking は CNI/HNS が構成します。registry/image pull、runhcs runtime、CNI path、logging も確認します。古い `3.6` tag を流用せず、distribution で検証された Windows sandbox image を使ってください。
</details>

2. Windows container で Hyper-V isolation mode を使用する主な benefit は何ですか？
   - A) より高い performance と低い resource usage
   - B) host OS とは異なる Windows version の container を実行できること
   - C) container 間の network communication speed の向上
   - D) より多くの Windows APIs と features のサポート

<details>
<summary>回答を表示</summary>

**回答: B) host OS と異なる Windows version の container を実行できること**

**解説:**
Windows OS 自体の Hyper-V isolation は、host と異なる Windows version の container を実行できる利点があります。各 container を軽量 VM で分離し、security boundary を強められますが、memory/CPU、起動時間などの overhead が増え、host で Hyper-V が必要です。

host と container の version mismatch を避ける必要があるときに役立ちます。たとえば Windows Server 2022 host 上で Windows Server 2019 base の container を実行できます。process isolation では host と container の kernel version を合わせる必要があります。Hyper-V isolation は軽量 VM ごとの kernel を持つため security boundary を強化し、multi-tenant environment や untrusted code に有用です。

ただし、この機能は Kubernetes ではサポートされません。Pod annotation で Hyper-V isolation を有効化することもできません。Windows OS の一般的な機能説明と Kubernetes が実際にサポートする container isolation を区別してください。Hyper-V isolation は性能が低く resource usage が多く、起動も遅くなり、host で Hyper-V を有効にする必要があります。他の選択肢では、process isolation の方が性能が高く、network communication も速い場合があります。また、利用できる Windows API/feature は container OS version に依存し、Hyper-V 自体が追加 API を提供するわけではありません。
</details>

3. Kubernetes で Windows node を使用する場合の pod networking について正しい記述はどれですか？
   - A) Windows node は CNI plugin を使用せず、独自の networking stack を使用する
   - B) Windows node は Linux node と同じ CNI plugin を使用するが、configuration は異なる
   - C) Windows node は常に host network mode を使用する必要がある
   - D) Windows node は overlay networks をサポートしない

<details>
<summary>回答を表示</summary>

**回答: B) Windows node は Linux node と同じ CNI plugin を異なる構成で利用できる**

**解説:**
Windows node は Flannel、Calico、Antrea など Linux/Windows の両方で動作する Windows 対応 CNI を利用できます。plugin は Windows 固有 component/setting を使い、Windows の HNS が network 構成と endpoint を管理します。VXLAN、GENEVE、L2bridge、L2tunnel などの mode がありますが、利用可否や高度な機能は plugin によって異なります。Flannel の VXLAN は Windows node で広く使われます。

Flannel の Linux 側 ConfigMap 例:
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
Windows node 側では追加構成が必要になる場合があります。
```powershell
# Script running on Windows nodes
$env:KUBE_NETWORK = "cbr0"
$networkName = "vxlan0"
$networkMode = "overlay"
```

通常の Windows Pod は `hostNetwork` を使えず、HostProcess が例外です。Windows は overlay network をサポートします。
</details>

4. Kubernetes の Windows node における resource management について正しい記述はどれですか？
   - A) Windows node は resource limits をサポートしない
   - B) Windows node は Linux node より正確な resource limits を提供する
   - C) Windows node は Job Objects を使用して resource limits を実装する
   - D) Windows node は cgroups を使用して resource limits を実装する

<details>
<summary>回答を表示</summary>

**回答: C) Windows node は Job Objects で resource limit を適用する**

**解説:**
Windows container runtime は Job Objects API を使って process group に CPU、memory、処理時間などの limit を適用します。Linux の cgroup とは実装が異なります。CPU limit は CPU time の上限であり、相対的な CPU sharing weight と混同しないでください。runtime は CPU core 数などに応じて CPU sharing を扱います。

Windows container の memory limit も Job Objects で実装されます。Windows には Linux の OOM killer がありません。memory を超えると allocation failure、paging、性能低下が生じる場合があり、同じ limit 値でも Linux とは挙動が異なることがあります。Kubernetes の request/limit は Linux Pod と同じように指定し、kubelet が値を Windows runtime に渡します。kubelet は Windows performance counter で usage を監視し、Metrics Server 経由で Kubernetes API と `kubectl top pods`/`kubectl top nodes` に報告します。Windows container は既定でより多くの resource を使う場合があるため十分な memory headroom を確保し、version ごとの挙動を確認してください。

A は resource limit が利用できるため誤り、B はどちらの OS が常に正確ということではなく機構が異なるため誤り、D は Windows が cgroup ではなく Job Objects を使うため誤りです。
     ```yaml
     resources:
       requests:
         memory: "2Gi"
         cpu: "500m"
       limits:
         memory: "4Gi"
         cpu: "1"
     ```

</details>

5. Kubernetes で Windows node を使用する際の security best practice として適切でないものはどれですか？
   - A) security vulnerabilities を解決するために container images を定期的に scan して update する
   - B) すべての Windows Pod で privileged mode を有効にする
   - C) Active Directory integration のために gMSA (Group Managed Service Accounts) を使用する
   - D) pod-to-pod communication を制限するために network policies を使用する

<details>
<summary>回答を表示</summary>

**回答: B) すべての Windows Pod で privileged mode を有効にする**

**解説:**
これは適切な security best practice ではありません。Windows container は Linux と同じ privileged mode をサポートせず、設定すると Pod の作成に失敗します。仮に利用できても、全 Pod を privileged にすることは最小権限の原則に反し、host access を増やして security risk を高めます。信頼済みの host-level agent には HostProcess を使う場合がありますが、HostProcess は privileged flag とは別の仕組みであり、PSS exception や権限範囲を限定する必要があります。

他の選択肢は適切です。A の定期的な image scan/update は既知 vulnerability の検出と修正に役立ち、Windows image の security update と CI/CD pipeline での image scan も重要です。C の gMSA は hardcoded credential の代わりに AD authentication を提供し、password を自動管理・rotation します。D の NetworkPolicy は必要な通信だけを許可して lateral movement の可能性を下げます。加えて Windows node に security patch を適用し、不要 feature を無効化し、firewall と強い authentication を設定し、image を最小化して runtime security monitoring を実施してください。
</details>

## 検証用リファレンス

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
