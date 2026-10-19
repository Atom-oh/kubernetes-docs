# Kubernetes/EKS トラブルシューティング・プレイブック: 症状 → 診断 → 原因 → 修正

> **元の例に記録されたバージョン**: Amazon EKS 1.36 の元の出力例（コントロールプレーン v1.36.2-eks-bca9cf6、platform version eks.9、Karpenter 1.4、VPC CNI v1.21、CoreDNS v1.14）
> **最終確認日**: 2026年9月11日

< [前へ: Zonal Cluster Operations](15-zonal-operations-guide.md) | [目次](./README.md) >

***

午前3時にページャーが鳴ってターミナルを開いたときに必要なのは、概念の解説ではなく「**今見えている状況で次に入力するコマンド**」です。このドキュメントは概念ではなく**症状**から始めます。各症状について、「見えているもの → 実行するもの → 出力例 → 最も一般的な原因と修正方法」を1つのまとまりにしています。

以下の出力例は、元の2026年9月2日の文書に記録された環境を示すもので、公式資料の記述も含みます。このレビューでは、そのクラスターを再実行しておらず、元の取得ログも独立に検証していません。特に[Karpenter互換性表](https://karpenter.sh/docs/upgrading/compatibility/)によると、Kubernetes 1.36にはKarpenter 1.13以降が必要です。記録された1.4.0の組み合わせを、サポート対象のデプロイとして再利用しないでください。

根本原因の詳細分析（コントロールプレーンログ、CloudWatch Logs Insightsクエリ、ノード参加失敗の8つの原因など）は、[EKSトラブルシューティング](../eks/09-eks-troubleshooting.md)と[EKS高度なデバッグ](../eks/11-eks-advanced-debugging.md)にあります。このページはその手前に位置し、**30秒以内に次に開くページを決める**ことを目的としています。内容を重複させず、関連ページへ案内します。

## 目次

1. [30秒サマリー: 症状 → 最初のコマンド → 最も一般的な原因](#30-second-summary-symptom--first-command--most-common-cause)
2. [診断判断ツリー](#diagnostic-decision-tree)
3. [症状別プレイブック](#playbook-by-symptom)
4. [kubectl診断チートシート](#kubectl-diagnostic-cheat-sheet)
5. [さらに調べる: 関連ドキュメント](#going-deeper-related-documents)
6. [参考資料](#references)

***

<span id="30-second-summary-symptom--first-command--most-common-cause"></span>

## 30秒サマリー: 症状 → 最初のコマンド → 最も一般的な原因

各症状のセルから、下にある対応するプレイブック節へ移動できます。

| 症状（`kubectl get pods`/`nodes` の表示） | 最初のコマンド | 最も一般的な原因 |
|---|---|---|
| [`Pending`](#1-pod-stuck-in-pending) | `kubectl describe pod <pod>` → Events内の`FailedScheduling`メッセージ | リソース不足（`Insufficient cpu/memory`）、toleration不足、nodeSelectorの不一致、未バインドのPVC |
| [`ImagePullBackOff` / `ErrImagePull`](#2-imagepullbackoff--errimagepull) | `kubectl describe pod <pod>` → `Failed to pull image`の行 | tagの誤記、private registry認証（imagePullSecrets/node IAM）、ECRのregion/account不一致 |
| [`CrashLoopBackOff`](#3-crashloopbackoff-exit-137-oomkilled-probe-failures-config-errors) | `kubectl logs <pod> --previous` + `lastState.terminated`を確認 | アプリの起動時失敗（exit 1）、`OOMKilled`（exit 137）、liveness probe失敗、ConfigMap/Secretの不足 |
| [`Running`だがREADY `0/1`](#4-running-but-not-ready--empty-endpoints) | `kubectl describe pod <pod>` → `Readiness probe failed` | readinessのpath/port誤り、依存先待ち、sidecarがReadyでない |
| [Serviceにリクエストが届かない](#5-service-is-unreachable) | `kubectl get endpointslices -l kubernetes.io/service-name=<svc>` | selector label不一致、誤った`targetPort`、NetworkPolicyによる遮断、CoreDNS障害 |
| [Nodeが`NotReady`](#6-node-notready--kubelet-pressure-diskpressure-memorypressure-pidpressure) | `kubectl describe node <node>` → Conditions | kubelet停止/network partition、`DiskPressure`、`MemoryPressure`、`PIDPressure` |
| [PVCが`Pending`](#7-pvc-stuck-in-pending) | `kubectl describe pvc <pvc>` → Events | `WaitForFirstConsumer`（正常な待機）、StorageClassの欠落/誤記、AZ不一致 |
| [アプリログのAWS API `AccessDenied`](#8-eks-irsa--pod-identity-accessdenied) | `kubectl get sa <sa> -o yaml` + 注入されたcredential-providerフィールド | IRSA（IAM Roles for Service Accounts）のannotation/trust policy誤り、Pod Identity association不足、Pod未再起動 |
| [`ContainerCreating`で停止 + `failed to assign an IP address`](#9-eks-enivpc-cni-ip-exhaustion) | `kubectl describe pod <pod>` → `FailedCreatePodSandBox` | SubnetのIP枯渇、node max-pods到達、`aws-node`の不健全 |
| [Karpenterがnodeを起動しない](#10-eks-karpenter-does-not-launch-a-node) | `kubectl get events -A --field-selector reason=FailedScheduling` | NodePoolの`limits`到達、requirements/taint不一致、instance type制限 |
| [Service作成が`failed calling webhook`で拒否される](#11-no-service-can-be-created-failed-calling-webhook) | `kubectl -n kube-system get endpointslices -l kubernetes.io/service-name=aws-load-balancer-webhook-service` | すべてのnamespaceに一致する`failurePolicy: Fail` webhookの背後でWebhook Deploymentが不健全（CrashLoop） |

***

## 診断判断ツリー {#diagnostic-decision-tree}

![ノード割り当て、イメージ取得とセットアップ待ち、繰り返し終了、Pod Ready条件、EndpointSliceとネットワークの診断を区別する判断ツリー。](../.gitbook/assets/en-ops-16-troubleshooting-playbook-0.png)

[🔍 インタラクティブ図を表示](https://www.atomai.click/kubernetes-docs/archmaps/en-ops-16-troubleshooting-playbook-0.html)

まずcontextとnamespaceを確認します。`<pod>`や`<ns>`などのplaceholderは実際の値に置き換えてください。Pod phaseとcontainer stateは異なります。`Running`のPodをすべて除外すると、一部のCrashLoopやreadiness失敗を見落とします。このクエリは完了済みPodを除外し、異常なphase、またはReady条件が欠落／falseのPodを含めます。

```bash
# Inspect phase and Ready condition together
kubectl get pods -A -o json | jq -r '
  .items[]
  | select(.status.phase != "Succeeded")
  | select(.status.phase != "Running" or
      ([.status.conditions[]? | select(.type == "Ready" and .status == "True")] | length == 0))
  | [.metadata.namespace, .metadata.name, .status.phase,
     ([.status.initContainerStatuses[]?, .status.containerStatuses[]?
       | .state.waiting.reason // empty] | join(","))] | @tsv
'

# Recent Warning events (cluster-wide, sorted by lastTimestamp)
kubectl get events -A --field-selector type=Warning --sort-by=.lastTimestamp | tail -30
```

***

<span id="playbook-by-symptom"></span>

## 症状別プレイブック

<span id="1-pod-stuck-in-pending"></span>

### 1. `Pending`で停止したPod

**症状**: `Pending`には、スケジューリング待ちだけでなくイメージ取得やcontainer setup待ちも含まれます。まず`.spec.nodeName`と`PodScheduled` conditionを確認してください。未バインドPodではスケジューリングイベントを、バインド済みPodではcontainer、mount、CNIの状態を調べます。

**診断**: 未スケジュールPodでは`FailedScheduling`を調べます。このメッセージは失敗理由ごとのnode数を集計しており、各理由のグループは重複することがあります。

```bash
kubectl describe pod <pod> -n <ns> | sed -n '/^Events:/,$p'
```

```
Warning  FailedScheduling  default-scheduler  0/15 nodes are available: 1 Insufficient cpu, 1 Insufficient memory,
  6 node(s) didn't match Pod's node affinity/selector, 8 node(s) had untolerated taint(s).
  no new claims to deallocate, preemption: 0/15 nodes are available:
  1 No preemption victims found for incoming pod, 14 Preemption is not helpful for scheduling.
```

この概要だけから、CPU不足とmemory不足が同じnodeで起きた、あるいは他のすべての制約を満たすnodeが正確に1台ある、と推定しないでください。[schedulerの集計コード](https://github.com/kubernetes/kubernetes/blob/v1.36.2/pkg/scheduler/framework/types.go)は、1つのnodeに複数の失敗理由を数えることがあります。実際のnode label、taint、割り当て状況を確認し、DRAメッセージはResourceClaimの利用状況に照らして解釈してください。

**原因と修正**:

| メッセージ断片 | 原因 | 修正 |
|---|---|---|
| `Insufficient cpu` / `Insufficient memory` | requestsがnodeの残りcapacityを超過 | requestsを適正化してautoscalerを確認（→ [10. Karpenter](#10-eks-karpenter-does-not-launch-a-node)）。`kubectl describe node`の`Allocated resources`も確認 |
| `Too many pods` | 設定済みnode max-podsに到達。CNIのIP capacityは別に確認 | → [9. ENI/IP枯渇](#9-eks-enivpc-cni-ip-exhaustion) |
| `node(s) had untolerated taint(s)` | node taintに対するtolerationがない | `kubectl get nodes -o custom-columns=NAME:.metadata.name,TAINTS:.spec.taints[*].key`でtaintを列挙し、tolerationを追加するかNodePoolを調整 |
| `node(s) didn't match Pod's node affinity/selector` | nodeSelector/affinityのlabelを持つnodeがない | `kubectl get nodes --show-labels`を確認。KarpenterではNodePool template labelまたはrequirementsで供給されるwell-known keyと値を確認 |
| `pod has unbound immediate PersistentVolumeClaims` | PVCが`Pending` | → [7. PVC Pending](#7-pvc-stuck-in-pending) |
| `node(s) had volume node affinity conflict` | PV（EBS）が存在するAZにスケジュール可能なnodeがない | PVの`nodeAffinity` zoneを読み、そのAZにcapacityを用意 |
| `node(s) didn't match pod topology spread constraints` / `pod anti-affinity rules` | spread制約を満たすnodeがない | 適切なnodeを追加。topology spreadでは可用性目標を検討した後に限りScheduleAnywayを検討。pod anti-affinityには別個のrequired/preferred規則がある |
| eventがまったくない | scheduler障害、または`schedulerName`の誤記 | `kubectl get pod <pod> -o jsonpath='{.spec.schedulerName}'`を確認 |

<span id="2-imagepullbackoff--errimagepull"></span>

### 2. `ImagePullBackOff` / `ErrImagePull`

**症状**: STATUSは最初`ErrImagePull`となり、数回のretry後に`ImagePullBackOff`へ変わります。kubeletのpull back-offは最大5分まで増加します。

**診断**:

```bash
kubectl describe pod <pod> -n <ns> | grep -A2 -E "Failed to pull|Back-off pulling"
kubectl get pod <pod> -n <ns> -o jsonpath='{range .spec.containers[*]}{.name}{"\t"}{.image}{"\n"}{end}'
kubectl get pod <pod> -n <ns> -o jsonpath='{.spec.imagePullSecrets}'
```

```
Warning  Failed   kubelet  Failed to pull image "123456789012.dkr.ecr.ap-northeast-2.amazonaws.com/app:v1.2.3": ... not found
Warning  Failed   kubelet  Error: ErrImagePull
Normal   BackOff  kubelet  Back-off pulling image "123456789012.dkr.ecr.ap-northeast-2.amazonaws.com/app:v1.2.3"
Warning  Failed   kubelet  Error: ImagePullBackOff
```

正常なpullでは`Pulling image "..."` → `Successfully pulled image "..." in 4.501s ...`の組が残り、すでにcache済みのimageでは`Container image "..." already present on machine`と記録されます。pull成功はダウンロード成功を示しますが、image内容、architecture、entrypointの問題を否定するものではありません。

**原因と修正**:

| `Failed to pull image`に続く内容 | 原因 | 修正 |
|---|---|---|
| `not found` / `manifest unknown` | tagの誤記、未pushのtag、repository誤り | `aws ecr describe-images --repository-name <repo> --image-ids imageTag=<tag>`で確認 |
| `401 Unauthorized` / `no basic auth credentials` | private registryの認証失敗 | ECRではnode IAM roleに`AmazonEC2ContainerRegistryPullOnly`（または`ReadOnly`）が必要。外部registryでは`imagePullSecrets`を確認 |
| 別のECR Region/accountからpullできない | 異なるaddress自体は誤りとは限らない。cross-account policyとregional endpoint accessを確認 | pullするprincipalをECR repository policyに追加 |
| `dial tcp ... i/o timeout` | NAT/VPC endpointのないprivate subnet | `com.amazonaws.<region>.ecr.api`、`ecr.dkr`、S3 gateway endpointを確認 |
| `toomanyrequests` | Docker Hubのrate limit | ECR pull-through cache経由でmirror |

nodeの診断では、まずkubelet event/logと、image pullに使われるcredential providerを確認してください。`crictl pull`はkubeletのECR credential providerやPodのimagePullSecretsを自動的に再利用しないため、同じ認証経路の再現にはなりません。Fargateのimage pullにはpod execution roleを使い、アプリケーションのIRSA roleとは分けます。

<span id="3-crashloopbackoff-exit-137-oomkilled-probe-failures-config-errors"></span>

### 3. `CrashLoopBackOff`（exit 137 `OOMKilled`、probe失敗、config誤り）

**症状**: containerが繰り返し終了し、RESTARTSが増えます。通常のback-offは10秒から300秒まで倍増しますが、feature gateやkubelet設定により変わることがあります。restart policyは[Pod lifecycle](https://kubernetes.io/docs/concepts/workloads/pods/pod-lifecycle/)を確認してください。

**診断**: 次の3点を順に確認します: **termination reasonとexit code**、**直前のcontainerのlogs**、**Events**。

```bash
# (1) Why did it die: lastState.terminated
kubectl get pod <pod> -n <ns> -o jsonpath='{range .status.containerStatuses[*]}{.name}{"\t"}restarts={.restartCount}{"\t"}reason={.lastState.terminated.reason}{"\t"}exit={.lastState.terminated.exitCode}{"\n"}{end}'

# (2) Logs right before death (the previous container, not the current one)
kubectl logs <pod> -n <ns> -c <container> --previous --tail=100

# (3) Probe/kill events
kubectl describe pod <pod> -n <ns> | sed -n '/^Events:/,$p'
```

元の文書に記録された、memory limit 128Miのcontainer出力例:

```
    Last State:     Terminated
      Reason:       OOMKilled
      Exit Code:    137
      Started:      Mon, 31 Aug 2026 08:55:27 +0000
      Finished:     Tue, 01 Sep 2026 21:13:37 +0000
    Restart Count:  3
```

約36時間稼働したことは、即時の起動失敗と区別する手掛かりですが、memory leakの証明ではありません。memory時系列とkernel/cgroup eventを使い、traffic急増、batch job、node OOM、limit変更も調べてください。

**exit codeの読み方**:

| Exit Code | Reason | 意味 | 修正 |
|---|---|---|---|
| `0` | `Completed` | processは正常終了。Deploymentではアプリがforegroundで動作し続けていないことを意味する | 長時間動作するentrypointをforegroundで実行するか、Jobに切り替える |
| `1` | `Error` | アプリ自身が終了（config誤り、依存先への接続失敗） | stack traceを`logs --previous`で確認 |
| `126` | `Error` | shell entrypointでcommandは見つかったが実行不可。execute bit不足、またはshellが`cannot execute binary file: Exec format error`（architecture不一致）を報告 | Dockerfileで`chmod +x`。`kubectl get nodes -L kubernetes.io/arch`でarm64/amd64を確認し、multi-arch imageを使う |
| `127` | `Error` | shell entrypointでcommandが見つからない。pathの誤記、またはbinaryが最終image stageにcopyされていない | `command`/`args`をimage内の実ファイル（`kubectl debug ... -- ls <path>`）と照合 |
| `137` | `OOMKilled` | OOMによる終了。container limit超過とnode memory pressureを区別 | limitを上げるかleakを修正。JVMでは`-XX:MaxRAMPercentage`を確認 → [Resource Optimization](10-resource-optimization.md) |
| `137` | `Error` | 別の理由によるSIGKILL: liveness失敗後、containerが`terminationGracePeriodSeconds`内に終了しなかった | preStop/graceful shutdownを見直す |
| `143` | `Error` | SIGTERMで終了（通常のrollout/evictionの可能性もある） | 繰り返す場合、Eventsから終了させた主体を調べる |

- imageがbinaryを直接execする（間にshellがない）場合、architecture不一致でもexit 126にはなりません。containerは起動せず、`lastState.terminated`のReasonは`StartError`、messageは`exec format error`になります。対処は同じくmulti-arch image、または`kubernetes.io/arch`のnodeSelectorです。

**Probe失敗**: 次のeventはliveness失敗によるrestartを示します。原因はpath/port誤りだけでなく、実際のアプリ障害、過負荷、deadlockの場合もあります。probeを緩める前にresponseとアプリケーションを調べてください。

```
Warning  Unhealthy  kubelet  Liveness probe failed: HTTP probe failed with statuscode: 503
Normal   Killing    kubelet  Container app failed liveness probe, will be restarted
```

- アプリの起動が遅い場合、livenessの`initialDelaySeconds`**を増やすのではなく`startupProbe`を追加します**（startup probeが成功するまでlivenessは開始されません）。
- `Readiness probe failed: dial tcp 10.0.2.45:8080: connect: connection refused`のようなTCP拒否では、まずcontainer portとprobe portが異ならないか確認してください。

**Configuration referenceの誤り**: 厳密にはcrash loopではありません。Podは`CreateContainerConfigError`で停止します。

```
Warning  Failed  kubelet  Error: configmap "app-config" not found
Warning  Failed  kubelet  Error: secret "db-credentials" not found
```

`kubectl get cm,secret -n <ns>`でnameとnamespaceを照合します。referenceがvolume mountの場合は、代わりに`FailedMount` event（`MountVolume.SetUp failed for volume "cfg" : configmap "app-config" not found`）として表示されます。

<span id="4-running-but-not-ready--empty-endpoints"></span>

### 4. `Running`だがReadyでない / Endpointsが空

**症状**: STATUSは`Running`でもREADYは`0/1`（sidecarがあると`1/2`）です。通常のService routingではnot-ready endpointを除外します。`publishNotReadyAddresses`、terminating endpoint、LB fail-openなどの例外は別途確認してください。proxyに応じて、clientにはerrorやtimeoutが見える場合があります。

**診断**:

```bash
kubectl describe pod <pod> -n <ns> | grep -E "Ready|Readiness probe"
kubectl get endpointslices -n <ns> -l kubernetes.io/service-name=<svc>
```

**EndpointSliceのaddressとreadinessは別です。** 一致するnot-ready Podもaddressと`ready: false`を持って表示されることがあります。ENDPOINTS欄だけからreadinessを推測せず、`ready`、`serving`、`terminating`を調べてください。

```bash
kubectl get endpointslices -n <ns> -l kubernetes.io/service-name=<svc> -o json | jq -r '
  .items[] as $slice | $slice.endpoints[]?
  | [$slice.metadata.name, (.addresses | join(",")), (.conditions | tojson)] | @tsv
'
```

`ready`が未設定なら状態はunknownであり、consumer側ではreadyとして扱う必要があります。`publishNotReadyAddresses: true`はreadinessによるfilteringを変更します。proxyはtermination中のserving endpointも処理できます。selectorのないServiceでは手動管理のEndpointSliceを確認します。v1 Endpoints APIはKubernetes 1.33以降deprecatedです。新しい診断にはEndpointSliceを使ってください。

**原因と修正**:

| 観測結果 | 原因 | 修正 |
|---|---|---|
| Eventsに`Readiness probe failed`が繰り返し出る | probe path/port誤り、またはアプリが依存先（DBなど）を待っている | probeをアプリの実health endpointに向ける。依存先待ちはlivenessではなくreadinessで扱う |
| `ReadinessGatesNotReady` reasonでCondition `Ready False` | Pod readiness gateを待機中。通常はAWS Load Balancer Controllerの`target-health.elbv2.k8s.aws/*` gate | Target Group health checkが失敗する理由を調べる → [AWS Load Balancer Controller](../networking/03-aws-lb-controller.md) |
| `1/2` RunningでアプリcontainerだけReady | sidecar（istio-proxyなど）がReadyでない、またはアプリ後にsidecarが起動して初期connectionに失敗 | sidecar logsを確認し、injector/versionがサポートする起動順序とreadinessを確認。native-sidecar化だけではreadinessは解決しない |
| ReadyなのにEndpointSliceが空 | Service selectorがPod labelに一致しない | → [5. Service unreachable](#5-service-is-unreachable) |

<span id="5-service-is-unreachable"></span>

### 5. Serviceに到達できない

**症状**: containerは`1/1 Running`ですが、`curl http://<svc>.<ns>.svc.cluster.local`がtimeoutまたはconnection refusedになる、あるいはname resolutionに失敗します。

**診断は3層に分けます**: (a) Service → Podのmapping、(b) network policy、(c) DNS。

```bash
# (a) Compare the selector with actual labels
kubectl get svc <svc> -n <ns> -o jsonpath='{.spec.selector}{"\n"}{.spec.ports}{"\n"}'
kubectl get pods -n <ns> -l <key>=<value> -o wide
kubectl get endpointslices -n <ns> -l kubernetes.io/service-name=<svc>

# (b) NetworkPolicies applied to the namespace
kubectl get networkpolicies -n <ns>
kubectl describe networkpolicy <policy> -n <ns>

# (c) CoreDNS status and logs
kubectl get pods -n kube-system -l k8s-app=kube-dns
kubectl logs -n kube-system -l k8s-app=kube-dns --tail=50
kubectl get cm -n kube-system coredns -o jsonpath='{.data.Corefile}'
```

**原因と修正**:

| 観測結果 | 原因 | 修正 |
|---|---|---|
| selectorが`{"app":"api"}`だがPod labelが`app=api-server` | label不一致でEndpointSliceが空 | labelとselectorを統一。Helm chartでは`selectorLabels`と`podLabels`がずれることがよくある |
| EndpointSliceにIPがあるのに`connection refused` | `targetPort`がcontainerの実待受portと異なる | `kubectl get pod <pod> -n <ns> -o jsonpath='{.spec.containers[*].ports}'`と照合。アプリが`127.0.0.1`だけにbindする場合も同じ症状 |
| 特定namespaceからだけ失敗 | `default-deny` NetworkPolicyがありingress allow ruleがない | `podSelector`/`namespaceSelector`を確認。VPC CNI network policyでは`kubectl get policyendpoints -n <ns>`で実際のenforcementを確認 → [Network Policies](../security/04-network-policies.md) |
| `nslookup <svc>`が`NXDOMAIN`を返す | 別namespaceからshort nameを使った、またはCoreDNS障害 | FQDN（`<svc>.<ns>.svc.cluster.local`）を使う。CoreDNS Podが`Running`で、`/etc/resolv.conf`の`nameserver`がkube-dns ClusterIP（このclusterでは`172.20.0.10`）か確認 |
| 外部domainの解決が遅い | defaultの`ndots:5`では、dotが5個未満のnameはabsolute nameとしてqueryする前に各search domain（`<ns>.svc.cluster.local`、`svc.cluster.local`、`cluster.local`、nodeのVPC domain）で試される | 外部nameの末尾に`.`を付けるか、nameが`ndots`、string値が`"2"`のdnsConfig.options entryを検討 |
| NodePort/LBが一部node経由だけで動作 | そのnodeにPodがない`externalTrafficPolicy: Local` | 意図された動作。client IP保持とnode間trafficを確認した後でのみClusterを検討 |

Pod視点のDNSを再現するには、使い捨てPodを起動します: `kubectl run -it --rm dns-test --image=busybox:1.36 --restart=Never -- nslookup kubernetes.default.svc.cluster.local`。CoreDNSの概念とCorefileは[Services and Networking](../core/03-services-networking.md#coredns)を参照してください。

宛先側ingressと送信元側egressのNetworkPolicyを両方確認します。containerPortを宣言しても待受socketは作られません。アプリlogsまたはsocket状態を調べてください。NodeLocal DNSCacheを使う場合、resolv.confのnameserverがkube-dns ClusterIP以外でも正常なことがあります。

**Auto ModeのDNS**: [現在のAuto Mode](https://docs.aws.amazon.com/eks/latest/userguide/auto-networking.html)ではCoreDNSはnode system serviceとして動作します。Auto Modeのみのclusterでkube-dns Pod/Serviceがないことだけでは障害を意味しません。混在clusterでは通常node用のCoreDNS Deploymentが必要です。上記Pod/ConfigMapコマンドはDeployment型DNSを調べます。Auto Modeでは実際のPod name resolution、node DNS logs、upstream resolverへの到達性を確認してください。

<span id="6-node-notready--kubelet-pressure-diskpressure-memorypressure-pidpressure"></span>

### 6. Node `NotReady` / kubelet pressure（`DiskPressure`、`MemoryPressure`、`PIDPressure`）

**症状**: `kubectl get nodes`で`NotReady`になるか、nodeが`Ready`でもPodが`Evicted`になる、または新しいPodが`node(s) had untolerated taint(s)`で避けられます。

**診断**:

```bash
# One-line summary of node conditions
kubectl get nodes -o custom-columns='NAME:.metadata.name,READY:.status.conditions[?(@.type=="Ready")].status,MEM:.status.conditions[?(@.type=="MemoryPressure")].status,DISK:.status.conditions[?(@.type=="DiskPressure")].status,PID:.status.conditions[?(@.type=="PIDPressure")].status'

# Conditions with their reason
kubectl get node <node> -o jsonpath='{range .status.conditions[*]}{.type}{"="}{.status}{" ("}{.reason}{")\n"}{end}'

# Taints the node picked up automatically
kubectl get node <node> -o jsonpath='{.spec.taints}'
```

健全なnodeの出力です（EKS Node Monitoring Agentが入っていれば`ContainerRuntimeReady`/`NetworkingReady`/`KernelReady`/`StorageReady` conditionsも表示されます）。

```
MemoryPressure=False (KubeletHasSufficientMemory)
DiskPressure=False (KubeletHasNoDiskPressure)
PIDPressure=False (KubeletHasSufficientPID)
Ready=True (KubeletReady)
ContainerRuntimeReady=True (ContainerRuntimeIsReady)
NetworkingReady=True (NetworkingIsReady)
KernelReady=True (KernelIsReady)
StorageReady=True (DiskIsReady)
```

**原因と修正**:

| Condition / reason | 自動taint | 原因 | 修正 |
|---|---|---|---|
| `Ready=Unknown`（`NodeStatusUnknown`、「Kubelet stopped posting node status.」） | `node.kubernetes.io/unreachable` | kubelet process停止、instance停止/network partition、API server認証失敗 | EC2 instance stateを確認。nodeが応答するならサポートされたlog取得方法を使う。kubelet停止中はdebug Podを起動できない場合がある |
| `Ready=False` | `node.kubernetes.io/not-ready` | container runtime停止、CNI未初期化（`aws-node`不健全） | 該当nodeのaws-nodeは`kubectl get pods -n kube-system -l k8s-app=aws-node -o wide`で確認 |
| `DiskPressure=True`（`KubeletHasDiskPressure`） | `node.kubernetes.io/disk-pressure` | image cache/container logがroot volumeを満たした | `crictl rmi --prune`、log rotation、root EBS拡張。Podは`The node was low on resource: ephemeral-storage`で`Evicted`される |
| `MemoryPressure=True`（`KubeletHasInsufficientMemory`） | `node.kubernetes.io/memory-pressure` | 実使用量がreservationを超過、またはsystem reservation不足。requestのないlimitは、そのlimitをrequestのdefaultにする場合がある | requestsを強制（LimitRange）し、`kube-reserved`/`system-reserved`を確認 |
| `PIDPressure=True`（`KubeletHasInsufficientPID`） | `node.kubernetes.io/pid-pressure` | fork storm（thread leak） | 問題のPodを特定してrestartし、`podPidsLimit`を設定 |

以下は特権debug Podを作成し、host shell、journalctl、crictlを使える一般的なLinux workerを前提とします。immutableなBottlerocket/EKS Auto Mode hostで同じchroot手順が使えるとは限りません。[Auto Mode troubleshooting](https://docs.aws.amazon.com/eks/latest/userguide/auto-troubleshoot.html)にあるdebug-containerとconsole-logの手順を使ってください。

```bash
kubectl debug node/<node> -it --image=busybox --profile=sysadmin -- chroot /host
# once inside
journalctl -u kubelet --since "10 min ago" | tail -50
df -h /var/lib/containerd
crictl ps -a | head
```

`kubectl get nodes`に**一度も表示されない**node（join failure: IAM role/access entry、subnet routing、security group、AMI mismatch）は別の問題です → [EKS高度なデバッグ: Node Join Failure Diagnosis](../eks/11-eks-advanced-debugging.md#node-join-diagnosis)、[EKSトラブルシューティング: Node and Pod Issues](../eks/09-eks-troubleshooting.md#node-and-pod-issues)。Karpenter nodeでは[section 10](#10-eks-karpenter-does-not-launch-a-node)のNodeClaim確認から始めます。

<span id="7-pvc-stuck-in-pending"></span>

### 7. PVCが`Pending`で停止

**症状**: `kubectl get pvc`は`Pending`を示し、それを使うPodも`pod has unbound immediate PersistentVolumeClaims`で`Pending`です。

**診断**:

```bash
kubectl get pvc -n <ns>
kubectl describe pvc <pvc> -n <ns> | sed -n '/^Events:/,$p'
kubectl get storageclass
kubectl get pods -n kube-system -l app=ebs-csi-node -o wide     # is the CSI node plugin on that node?
```

```
NAME   PROVISIONER             RECLAIMPOLICY   VOLUMEBINDINGMODE      ALLOWVOLUMEEXPANSION   AGE
gp2    kubernetes.io/aws-ebs   Delete          WaitForFirstConsumer   false                  145d
gp3    ebs.csi.aws.com         Delete          WaitForFirstConsumer   true                   76d
```

StorageClass一覧は環境例です。Auto Modeの`ebs.csi.eks.amazonaws.com`と、別途導入する`ebs.csi.aws.com` driverを区別してください。Auto Modeで通常のebs-csi-node DaemonSetがないことだけでは障害と判断できません。明示的な`storageClassName: ""`はdefault classを使わない指定であり、field自体を省略する場合とは異なります。

**原因と修正**: `describe pvc`のEvents messageが診断になります。

| Events message | 原因 | 修正 |
|---|---|---|
| `WaitForFirstConsumer: waiting for first consumer to be created before binding` | **正常。** `volumeBindingMode: WaitForFirstConsumer`はPodがscheduleされるまでvolume作成を遅らせる | 使用PodがまだなくPendingならそのまま待つ。PodもPendingならPodの`FailedScheduling`を読む |
| `FailedBinding: no persistent volumes available for this claim and no storage class is set` | `storageClassName`がなくdefault StorageClassもない | PVCに`storageClassName: gp3`を設定するか、SCに`storageclass.kubernetes.io/is-default-class: "true"`をannotation |
| `ProvisioningFailed: storageclass.storage.k8s.io "<name>" not found` | StorageClassの誤記、別clusterからmanifestをcopy | `kubectl get sc`で実際のnameを確認 |
| `ProvisioningFailed: error generating accessibility requirements: no topology key found for node <node>` | Podが配置されたnodeにEBS CSI node pluginが登録されていない（`CSINode`にdriverがない） | `kubectl get csinode <node>`のDRIVERS列を確認し、`ebs-csi-node` DaemonSetがそのnodeで実行中か確認 |
| `ProvisioningFailed` + `UnauthorizedOperation`/`AccessDenied` | EBS CSI controllerのIRSA/Pod Identityにpermission不足 | → [8. IRSA/Pod Identity](#8-eks-irsa--pod-identity-accessdenied)（subjectは`ebs-csi-controller-sa`） |
| Pod側の`node(s) had volume node affinity conflict` | 既存PV（EBS）がAZ `ap-northeast-2a`にあり、schedule可能なnodeは別AZ | EBSはAZをまたげません。`kubectl get pv <pv> -o jsonpath='{.spec.nodeAffinity}'`でzoneを調べ、そこにcapacityを用意（NodePool zone requirementまたはnodeSelector） |
| Pod側の`FailedAttachVolume: Multi-Attach error for volume` | RWO volumeが前のnodeにattachされたまま（node障害後にStatefulSetが再schedule） | `kubectl get volumeattachments`でstale attachmentを調べる。nodeを失った場合はcleanupを数分待つ |

`WaitForFirstConsumer`、StorageClass、dynamic provisioningは[Storage](../core/04-storage.md#storage-classes)、EBS/EFS CSIのerror patternは[EKS高度なデバッグ: Storage Troubleshooting](../eks/11-eks-advanced-debugging.md#6-storage-troubleshooting)を参照してください。

<span id="8-eks-irsa--pod-identity-accessdenied"></span>

### 8. EKS: IRSA / Pod Identityの`AccessDenied`

**症状**: Podは`Running`ですが、アプリlogsにAWS SDK errorが出ます。

```
An error occurred (AccessDenied) when calling the AssumeRoleWithWebIdentity operation:
  Not authorized to perform sts:AssumeRoleWithWebIdentity
```

またはS3/DynamoDB callが`... is not authorized to perform: s3:GetObject`で拒否され、拒否principalがservice account roleではなく**node IAM role**（`assumed-role/<node-role>/i-0abc...`）になっています。これはSDKがnode credentialsを選んだことを示します。IMDS accessが遮断されている場合、node roleへのfallbackは利用できません。credential injection、SDK version、provider precedence、明示credentialsを確認してください。

**診断**: まず使用中のmechanismを特定します。Podのenvironment variableから確認できます。

```bash
# Service account annotation (IRSA)
kubectl get sa <sa> -n <ns> -o jsonpath='{.metadata.annotations.eks\.amazonaws\.com/role-arn}{"\n"}'

# Credential-related env injected into the pod
kubectl get pod <pod> -n <ns> -o json | jq -r '
  (.spec.initContainers[]?, .spec.containers[]?) as $container
  | $container.env[]?
  | select(.name == "AWS_ROLE_ARN" or .name == "AWS_WEB_IDENTITY_TOKEN_FILE"
        or .name == "AWS_CONTAINER_CREDENTIALS_FULL_URI"
        or .name == "AWS_CONTAINER_AUTHORIZATION_TOKEN_FILE")
  | [$container.name, .name, (.value // "valueFrom")] | @tsv
'
```

| 注入されたenv | Mechanism | 意味 |
|---|---|---|
| `AWS_ROLE_ARN=arn:aws:iam::...:role/<role>` + `AWS_WEB_IDENTITY_TOKEN_FILE=/var/run/secrets/eks.amazonaws.com/serviceaccount/token` | **IRSA** | pod-identity-webhookが注入。なければSA annotationがPod作成**後**に追加されたか、SA nameが異なる |
| `AWS_CONTAINER_CREDENTIALS_FULL_URI` + `AWS_CONTAINER_AUTHORIZATION_TOKEN_FILE` | **EKS Pod Identity** | `eks-pod-identity-agent`が`169.254.170.23`でcredentialsを提供。associationがある場合だけ注入 |
| どちらもない | 別providerまたはcredentialsなし | 下の表を参照 |

```bash
# Pod Identity: agent and association
kubectl get pods -n kube-system -l app.kubernetes.io/name=eks-pod-identity-agent
aws eks list-pod-identity-associations --cluster-name <cluster> --namespace <ns> --service-account <sa>

# IRSA: OIDC condition in the trust policy
aws eks describe-cluster --name <cluster> --query 'cluster.identity.oidc.issuer' --output text
aws iam get-role --role-name <role> --query 'Role.AssumeRolePolicyDocument'
```

**原因と修正**:

| 観測結果 | 原因 | 修正 |
|---|---|---|
| envがないがSA annotationはある | 作成順序、実際のserviceAccountName、またはwebhook injection設定 | 設定を確認・修正し、影響を考慮して正しいnamespaceでPodを作り直す |
| envもassociationもない | Pod Identity associationがない、または別のSA/namespace用に作成された | `aws eks create-pod-identity-association ...`を実行し、その後Podを再起動 |
| `Not authorized to perform sts:AssumeRoleWithWebIdentity` | IRSA trust policy: `Federated` OIDC provider ARN誤り、または`sub`（`system:serviceaccount:<ns>:<sa>`）/`aud`（`sts.amazonaws.com`）condition不一致 | trust policyを修正。clusterを再作成してOIDC issuerが変わった場合はproviderも再作成 |
| Pod Identityだが`AssumeRole`が拒否 | trust policy principalが`pods.eks.amazonaws.com`ではない、または`sts:TagSession`不足 | trust policyで`sts:AssumeRole`と`sts:TagSession`の両方を許可 |
| envは正常だが特定APIだけ`AccessDenied` | identity/resource policy、SCP、boundary、sessionまたはVPC endpoint policyによる拒否 | 呼び出し元とresource、明示的Denyを確認。関連するCloudTrail data eventにはlogging設定が必要な場合がある |
| Pod Identity envはあるがSDKが`Unable to locate credentials`と表示 | SDKが古くcontainer credential provider（`FULL_URI`）をサポートしない | SDKをupgrade。最低対応versionはEKS docsを参照 |

IRSAとPod Identityの仕組み・設定は[EKS Security Best Practices](../security/06-eks-security-best-practices.md#irsa-iam-roles-for-service-accounts)および[EKS Security](../eks/05-eks-security.md#eks-pod-identity)、token expiryとwebhook問題は[EKS高度なデバッグ: Control Plane Debugging](../eks/11-eks-advanced-debugging.md#2-control-plane-debugging)を参照してください。

<span id="9-eks-enivpc-cni-ip-exhaustion"></span>

### 9. EKS: ENI/VPC CNIのIP枯渇

**症状**: PodがEventsの`FailedCreatePodSandBox`とともに`ContainerCreating`で停止します:

```
Warning  FailedCreatePodSandBox  kubelet  Failed to create pod sandbox: rpc error: code = Unknown desc =
  failed to setup network for sandbox "...": plugin type="aws-cni" name="aws-cni" failed (add):
  add cmd: failed to assign an IP address to container
```

スケジューリング時の`Too many pods`はkubeletのPod数上限に達したことを示します。IP capacityに関係する場合はありますが、IP枯渇の証明ではありません。CNIの`FailedCreatePodSandBox`はnode割り当て後に発生します。

**診断**:

```bash
# Read the actual pod ceiling; distinguish secondary-IP defaults from prefix/custom networking configuration
kubectl get node <node> -o jsonpath='{.status.allocatable.pods}{"\n"}'
kubectl get pods -A --field-selector spec.nodeName=<node>,status.phase!=Succeeded,status.phase!=Failed --no-headers | wc -l

# aws-node status and IPAM settings
kubectl get pods -n kube-system -l k8s-app=aws-node -o wide
kubectl get ds -n kube-system aws-node -o jsonpath='{range .spec.template.spec.containers[?(@.name=="aws-node")].env[*]}{.name}={.value}{"\n"}{end}' | grep -E "PREFIX|WARM|MINIMUM|CUSTOM_NETWORK"

# Free IPs in the subnet
aws ec2 describe-subnets --subnet-ids <subnet-id> --query 'Subnets[].{id:SubnetId,az:AvailabilityZone,free:AvailableIpAddressCount}' --output table
```

IPv4 secondary-IP modeでは、未使用ENI capacityのdefault targetは`WARM_ENI_TARGET=1`です。各ENIはprimary IPも1つ消費します。m5.xlargeではENIごとにIPv4 addressが15個あり、そのうち通常のPod用secondary addressは14個です。正の`WARM_IP_TARGET`/`MINIMUM_IP_TARGET`値はwarm-ENI規則に優先します。warm=3、minimum=6の場合、使用IPが1個なら合計6個を目標にして5個を余分に確保し、使用IPが5個なら合計8個を目標にして3個を余分に確保します。余剰capacityが常にちょうど3個とは限りません。IPAM reconciliation、ENI上限、prefix割当粒度が実数に影響します。

**原因と修正**:

| 観測結果 | 原因 | 修正 |
|---|---|---|
| Subnetの`AvailableIpAddressCount`が一桁 | warm poolがIPを事前確保し、subnet自体が枯渇 | 上記設定のように`WARM_IP_TARGET`/`MINIMUM_IP_TARGET`でwarm poolを縮小し、**custom networking**（`ENIConfig`）でsecondary CIDR（例: 100.64.0.0/16）を追加。長期的にはIPv6も検討 |
| node上のPod数 = allocatable Pod数 | 設定済みPod数上限。IP capacityは別途確認 | 対応version/instanceと連続した/28 block、subnet capacityを確認してから**prefix delegation**（`ENABLE_PREFIX_DELEGATION=true`）を検討し、max-podsを再計算。または大きいinstanceを使う |
| 該当nodeの`aws-node`が`CrashLoopBackOff` | CNI自体の障害（`AmazonEKS_CNI_Policy`不足、version不一致） | `kubectl logs -n kube-system <aws-node-pod> -c aws-node`とnode上の`/var/log/aws-routed-eni/ipamd.log`を確認 |
| Security Groups for Podsを使い`vpc.amazonaws.com/pod-eni`が不足 | Branch ENI上限 | trunk ENI対応instanceへ移行し、`ENABLE_POD_ENI=true`を確認 |

IPAM動作（warm pool、prefix delegation、custom networking）は[VPC CNI: IP Address Management](../networking/01-vpc-cni.md#ip-address-management)、段階的なIP枯渇対処は[EKS高度なデバッグ: Networking Diagnostics](../eks/11-eks-advanced-debugging.md#5-networking-diagnostics)と[EKSトラブルシューティング: VPC CNI Issues](../eks/09-eks-troubleshooting.md#networking-issues)を参照してください。

<span id="10-eks-karpenter-does-not-launch-a-node"></span>

### 10. EKS: Karpenterがnodeを起動しない

**症状**: Podが`Pending`で、新しいNodeClaimが`kubectl get nodeclaims`に現れません。default schedulerの`FailedScheduling`とは**別に**、Karpenterも同じPodに自身の理由をeventとして記録します。

**診断**:

```bash
# Events emitted by Karpenter (source is karpenter)
kubectl get events -n <ns> --field-selector involvedObject.name=<pod> -o custom-columns=REASON:.reason,SRC:.source.component,MSG:.message

# NodePool limits vs current usage
kubectl get nodepool -o custom-columns='NAME:.metadata.name,CPU_LIMIT:.spec.limits.cpu,CPU_USED:.status.resources.cpu,MEM_LIMIT:.spec.limits.memory,MEM_USED:.status.resources.memory,READY:.status.conditions[?(@.type=="Ready")].status'

# NodeClaim progress
kubectl get nodeclaims -o custom-columns='NAME:.metadata.name,TYPE:.metadata.labels.node\.kubernetes\.io/instance-type,LAUNCHED:.status.conditions[?(@.type=="Launched")].status,REGISTERED:.status.conditions[?(@.type=="Registered")].status,READY:.status.conditions[?(@.type=="Ready")].status'

kubectl logs -n kube-system -l app.kubernetes.io/name=karpenter --tail=100
```

元の文書に記録された、拒否されたNodePoolを列挙するKarpenter event:

```
FailedScheduling  karpenter  Failed to schedule pod, incompatible with nodepool "system",
  daemonset overhead={"cpu":"821m","memory":"1350Mi","pods":"10"}, incompatible requirements,
  label "nvidia.com/device-plugin.config" does not have known values;
  incompatible with nodepool "runner-arm", ..., did not tolerate workload-type=ci-runner:NoSchedule;
  all available instance types exceed limits for nodepool "graviton";
  incompatible with nodepool "gpu-ner", ..., incompatible requirements, key node.kubernetes.io/instance-type,
  node.kubernetes.io/instance-type In [g6e.4xlarge] not in node.kubernetes.io/instance-type In [g6.2xlarge g6.4xlarge g6.xlarge]
```

記録例ではCPU_LIMITが8、CPU_USEDが8ですが、`exceed limits`は現使用量が上限と同じ場合に限りません。候補instanceのすべてが残りheadroomを超えれば、上限未満でも発生します。`Nominated`はscheduler上のnominationであり、完了を意味しません。NodeClaimのLaunched、Registered、Initialized、Readyと、実際のPod割り当てを確認してください。

**原因と修正**:

| メッセージ断片 | 原因 | 修正 |
|---|---|---|
| `all available instance types exceed limits for nodepool "<np>"` | 候補instanceを追加するとNodePool limitsを超える | limitを上げるか、consolidationがidle nodeを回収できているか確認 |
| `label "<key>" does not have known values` | 要求されたcustom labelの値がNodePool template label/requirementsで供給されない | NodePoolの`spec.template.spec.requirements`に値の一覧とともにkeyを追加 |
| `did not tolerate <key>=<value>:NoSchedule` | NodePool `taints`に対するtolerationがない | isolationが意図的なら別NodePoolを使い、それ以外はtolerationを追加 |
| `key node.kubernetes.io/instance-type, ... In [X] not in ... In [Y Z]` | PodがNodePoolで許可されていないinstance typeを要求 | どちらかを揃える。通常、Pod側のrequirementが狭すぎる |
| 大きな`daemonset overhead={...}`と`Insufficient` | DaemonSet reservationを差し引いた後のcapacity不足 | requirementsに大きいinstanceを含める |
| NodeClaim `LAUNCHED=True, REGISTERED=False`が数分続く | EC2は起動したがnodeが参加できない（EC2NodeClassのsubnet/SG selector、node IAM role access entry、AMI） | `kubectl describe nodeclaim <name>`のConditions/EventsとEC2 console system logを確認 |
| Karpenter logに`InsufficientInstanceCapacity` | そのAZ/instance typeでEC2 capacity不足（ICE: Insufficient Capacity Error） | instance type、AZ、capacity-type（spot/on-demand）を広げる |
| eventがなくKarpenter logも静か | PodがKarpenter候補でない（`nodeSelector`がMNG labelを指定、またはKarpenterと無関係なschedule制約） | Pod specのnode関連制約をすべて再確認 |

NodePool/EC2NodeClassの構造と詳細なtroubleshootingは[Karpenter: Troubleshooting](../autoscaling/02-karpenter.md#troubleshooting)と[EKS高度なデバッグ: Karpenter Provisioning Issues](../eks/11-eks-advanced-debugging.md#karpenter-provisioning-issues)を参照してください。

<span id="11-no-service-can-be-created-failed-calling-webhook"></span>

### 11. Serviceを作成できない: failed calling webhook

**症状**: load balancerと無関係なnamespaceも含め、どのnamespaceからのService `kubectl apply`/`create`もAPI serverに拒否されます。Serviceを含むDeployment、Helm install、ArgoCD syncはその箇所で止まります。一方で**既存Serviceは動作し続ける**ため、Pod側には異常が見えません。

```
Internal error occurred: failed calling webhook "mservice.elbv2.k8s.aws": failed to call webhook:
  ... no endpoints available for service "aws-load-balancer-webhook-service"
```

**診断**: error messageはwebhookと、その背後にあるServiceを示しています。webhook configuration → webhook Serviceのendpoint → その背後のDeploymentの順に追ってください。

```bash
# (1) Which webhooks are registered, and what each does on failure (rules, namespaceSelector, objectSelector, failurePolicy)
kubectl get mutatingwebhookconfigurations,validatingwebhookconfigurations
kubectl get mutatingwebhookconfiguration aws-load-balancer-webhook -o jsonpath='{range .webhooks[*]}{.name}{"\t"}failurePolicy={.failurePolicy}{"\t"}ns={.namespaceSelector}{"\t"}obj={.objectSelector}{"\t"}{.rules[*].operations}{" "}{.rules[*].resources}{"\n"}{end}'

# (2) Is there a Ready pod behind the webhook Service?
kubectl -n kube-system get endpointslices -l kubernetes.io/service-name=aws-load-balancer-webhook-service

# (3) Why does that Deployment keep dying?
kubectl -n kube-system get pods -l app.kubernetes.io/name=aws-load-balancer-controller
kubectl -n kube-system logs deploy/aws-load-balancer-controller --previous
```

元の文書には2026年9月2日のLBC v3.2.1の繰り返しrestartと下記logが記録されています。このレビューでは、過去のrestart回数や継続時間を独立検証していません。実行可能な根拠は、導入済みCRDとcontrollerが要求するAPI versionの不一致です。

```
{"ts":"2026-09-02T07:54:42Z","logger":"setup","msg":"Disabling NLBGatewayAPI: missing required Gateway API CRDs","missing":["TLSRoute","TCPRoute","UDPRoute"]}
{"level":"error","logger":"controller-runtime.source.Kind","msg":"if kind is a CRD, it should be installed before calling Start","kind":"ListenerSet.gateway.networking.k8s.io","error":"no matches for kind \"ListenerSet\" in version \"gateway.networking.k8s.io/v1\""}
{"ts":"2026-09-02T07:57:00Z","level":"error","logger":"setup","msg":"problem running manager","error":"failed to wait for gateway.k8s.aws/alb caches to sync kind source: *v1.ListenerSet: timed out waiting for cache to be synced for Kind *v1.ListenerSet"}
```

このlogは`ListenerSet.gateway.networking.k8s.io/v1`が見つからず、cache同期が失敗していることを示します。**Gateway API 1.5.0のstandard channelにはListenerSetが含まれます。** version要件、standard CRD、LBC固有CRDを[LBC v3.2.1 guide](https://github.com/kubernetes-sigs/aws-load-balancer-controller/blob/v3.2.1/docs/guide/gateway/gateway.md)で確認してください。TCPRoute/UDPRouteなど追加APIが必要ならexperimental導入要件を確認します。影響は実際のwebhook rule、selector、failurePolicyによって異なります。target更新や新規resourceのreconcileが損なわれても、既存LBのdata pathは継続する場合があります。

**原因と修正**:

| 観測結果 | 原因 | 修正 |
|---|---|---|
| `no endpoints available for service "aws-load-balancer-webhook-service"` | webhook DeploymentにReady Podがない（CrashLoop、schedule不可、replica 0） | **まずcontrollerを正常化**（次の行）。EndpointSliceのaddressとready conditionを確認し、実際のwebhook requestを試す |
| logに`no matches for kind "ListenerSet"` → `timed out waiting for cache to be synced` | controller versionが必要とするGateway API CRDがない | (a) controller versionが必要とするGateway API CRDを導入（ListenerSetはGateway API 1.5.0のstandard channelに含まれる）、(b) CRD導入までHelm feature-gate valueでGateway API機能を無効化（正確なgate名はそのversionの`values.yaml`で確認）、(c) 導入済みCRDに合うcontroller versionをpin |
| endpointはあるが`connection refused` / `context deadline exceeded` / `x509` | webhook portへの経路が遮断（NetworkPolicy/security group）、証明書期限切れまたは不一致 | API server → Pod webhook portの経路、`clientConfig.caBundle`、証明書更新を確認 |
| 今すぐServiceを作る必要がある | — | **影響範囲を理解した緊急措置としてのみ**: `mservice.elbv2.k8s.aws`の`failurePolicy`を`Ignore`へpatch。この間に作成したServiceにはcontrollerのmutation（default `loadBalancerClass`の注入）が行われません。**復旧後に`Fail`へ戻し**、その間に作成されたServiceをレビューしてください |

やってはいけないこと: `objectSelector`を回避するためServiceに`app.kubernetes.io/name=aws-load-balancer-controller` labelを付けないでください。webhookは通過しますが、そのServiceにはmutationが適用されず、labelも実態と異なります。このselectorはcontroller自身のServiceを作成できるようにするためだけのものです。

未使用のGateway API機能を一時停止する場合、既存設定とマージしたv3.2.1 chart valueを用意してHelm diffをレビューしてください。まず既存Gateway resourceがそれらのcontrollerに依存するか確認します。

```yaml
controllerConfig:
  featureGates:
    ALBGatewayAPI: false
    NLBGatewayAPI: false
```

**予防**: webhook Deploymentのavailable replica数とCrashLoop状態を監視してください。例として、kube-state-metricsの次のexpressionに5分のholdを設定します。

```promql
kube_deployment_status_replicas_available{
  namespace="kube-system", deployment="aws-load-balancer-controller"
} < 1
```

metricがない場合、このexpressionもseriesを返しません。別途`absent_over_time(...[5m])`またはscrape失敗を監視します。DeploymentのavailableはService selector、証明書、network pathの正常性を保証しません。EndpointSlice conditionとwebhook経路も確認してください。replicaをAZに分散しPDBを使うとnode障害には役立ちますが、全replica共通の設定誤りは防げません。

元の[Pod Network Benchmark](../networking/06-pod-network-benchmark.md)ではClusterIP測定を除外しています。これは記録済みbenchmarkの制約のままです。このレビューではincidentを再現していません。

***

<span id="kubectl-diagnostic-cheat-sheet"></span>

## kubectl診断チートシート

resourceの確認とdebug actionを分けてください。get/describe/logs/topはresourceを調べますが、kubectl debugとkubectl runはcontainerまたはPodを作成します。debug Podのlabelが誤ってService selectorに一致しないようにし、使用後はdebug Podを削除してください。ephemeral containerは元のPodに記録されたままです。

```bash
# ── Status scan ────────────────────────────────────────────────────────
# Unhealthy pods only
kubectl get pods -A -o json | jq -r '
  .items[]
  | select(.status.phase != "Succeeded")
  | select(.status.phase != "Running" or
      ([.status.conditions[]? | select(.type == "Ready" and .status == "True")] | length == 0))
  | [.metadata.namespace, .metadata.name, .status.phase,
     ([.status.initContainerStatuses[]?, .status.containerStatuses[]?
       | .state.waiting.reason // empty] | join(","))] | @tsv
'
# Restart counts ascending, so the 15 worst pods come LAST (after tail) + last termination reason.
# Reads the first container only ([0]); for multi-container pods check the others separately.
kubectl get pods -A --sort-by='.status.containerStatuses[0].restartCount' \
  -o custom-columns='NS:.metadata.namespace,NAME:.metadata.name,RESTARTS:.status.containerStatuses[0].restartCount,REASON:.status.containerStatuses[0].lastState.terminated.reason' | tail -15
# Pods on a given node
kubectl get pods -A --field-selector spec.nodeName=<node> -o wide
# Node conditions + zone + instance type
kubectl get nodes -o custom-columns='NAME:.metadata.name,READY:.status.conditions[?(@.type=="Ready")].status,DISK:.status.conditions[?(@.type=="DiskPressure")].status,MEM:.status.conditions[?(@.type=="MemoryPressure")].status,ZONE:.metadata.labels.topology\.kubernetes\.io/zone,TYPE:.metadata.labels.node\.kubernetes\.io/instance-type'

# ── Events ─────────────────────────────────────────────────────────────
kubectl get events -A --field-selector type=Warning --sort-by=.lastTimestamp | tail -30
kubectl get events -n <ns> --field-selector involvedObject.name=<pod>,reason=FailedScheduling
kubectl events -n <ns> --for pod/<pod> --watch          # follow one object live
kubectl events -A --types=Warning                       # kubectl events subcommand (1.26+)

# ── jsonpath for exactly the fields you need ──────────────────────────
kubectl get pod <pod> -o jsonpath='{.status.containerStatuses[*].lastState.terminated}'
kubectl get pod <pod> -o jsonpath='{range .spec.containers[*]}{.name}{": "}{.resources}{"\n"}{end}'
kubectl get svc <svc> -o jsonpath='{.spec.selector}'
kubectl get sa <sa> -o jsonpath='{.metadata.annotations.eks\.amazonaws\.com/role-arn}'
kubectl get pv <pv> -o jsonpath='{.spec.nodeAffinity.required.nodeSelectorTerms[0].matchExpressions}'

# ── Logs ───────────────────────────────────────────────────────────────
kubectl logs <pod> -c <container> --previous --tail=100   # logs of the dead container
kubectl logs -n kube-system -l k8s-app=kube-dns --tail=50  # several pods by label
kubectl logs deploy/<name> --all-containers --since=10m

# ── Debug containers ───────────────────────────────────────────────────
# Attach an ephemeral container (target process namespace requires runtime support)
kubectl debug -it <pod> --image=nicolaka/netshoot --target=<container>
# Copy with an approved shell-capable debug-image; review copied labels and volume access
kubectl debug <pod> -it --copy-to=<pod>-debug --container=<container> --set-image=<container>=<debug-image> -- sh
# Node shell without SSH. --profile=sysadmin is a privileged container
kubectl debug node/<node> -it --image=busybox --profile=sysadmin -- chroot /host

# ── Resource usage (requires metrics-server) ───────────────────────────
kubectl top nodes
kubectl top pods -n <ns> --sort-by=memory
# Without metrics-server: "error: Metrics API not available"

# ── Schema lookup ──────────────────────────────────────────────────────
kubectl explain pod.status.containerStatuses.lastState.terminated
kubectl explain nodepool.spec.limits        # works for CRDs too
kubectl api-resources | grep -E "karpenter|k8s.aws"

# ── Rollouts ───────────────────────────────────────────────────────────
kubectl rollout status deploy/<name> -n <ns>
kubectl rollout history deploy/<name> -n <ns>
```

`kubectl debug`で有効な`--profile`値は`legacy`、`general`、`baseline`、`restricted`、`netadmin`、`sysadmin`です（defaultはkubectl versionにより`legacy`または`general`。`kubectl debug --help`を確認）。restricted policy下では互換性のあるimage/security contextと`--profile=restricted`を使いますが、他のadmission policyで拒否される場合もあります。特権node debugには別途認可が必要です。

***

<span id="going-deeper-related-documents"></span>

## さらに調べる: 関連ドキュメント

このプレイブックは「次にどこへ進むか」を決める入口です。原因を絞り込んだら、以下のドキュメントへ進んでください。

| 絞り込んだ領域 | 概念ドキュメント | 詳細なtroubleshooting |
|---|---|---|
| Pod lifecycle、probe、restart policy | [Pods and Workloads](../core/02-pods-and-workloads.md#pod-lifecycle) | [EKS高度なデバッグ: Workload Debugging](../eks/11-eks-advanced-debugging.md#4-workload-debugging) |
| Service、EndpointSlice、CoreDNS、NetworkPolicy | [Services and Networking](../core/03-services-networking.md)、[Network Policies](../security/04-network-policies.md) | [EKSトラブルシューティング: Networking Issues](../eks/09-eks-troubleshooting.md#networking-issues) |
| PV/PVC/StorageClass、EBS CSI | [Storage](../core/04-storage.md) | [EKSトラブルシューティング: Storage Issues](../eks/09-eks-troubleshooting.md#storage-issues) |
| Node参加、kubelet、resource pressure | [Cluster Architecture](../core/01-cluster-architecture.md) | [EKSトラブルシューティング: Node and Pod Issues](../eks/09-eks-troubleshooting.md#node-and-pod-issues) |
| Karpenter NodePool/NodeClaim | [Karpenter](../autoscaling/02-karpenter.md) | [Scaling Strategies](06-scaling-strategies.md) |
| VPC CNI IPAM、prefix delegation、custom networking | [VPC CNI](../networking/01-vpc-cni.md) | [EKS Networking Part 3: Troubleshooting](../eks/03-eks-networking-part3.md) |
| IRSA、Pod Identity、RBAC | [EKS Security Best Practices](../security/06-eks-security-best-practices.md)、[Kubernetes Authentication and Authorization](../security/02-kubernetes-auth-authz.md) | [EKSトラブルシューティング: IAM and Authentication Issues](../eks/09-eks-troubleshooting.md#iam-and-authentication-issues) |
| logの場所と調べ方 | [Logging Overview](../observability/logging/README.md) | [Observability Analysis](08-observability-analysis.md) |
| requests/limits、OOM、JVM memory | [Resource Optimization](10-resource-optimization.md) | [EKSトラブルシューティング: Performance Issues](../eks/09-eks-troubleshooting.md#performance-issues) |
| Incident responseの流れ、severity、最初の5分のchecklist | — | [EKS高度なデバッグ: Incident Response Framework](../eks/11-eks-advanced-debugging.md#1-incident-response-framework) |

***

<span id="references"></span>

## 参考資料

このページの引用文字列と経験則を裏付ける公式資料です。

**Kubernetes**

- [Taints and Tolerations](https://kubernetes.io/docs/concepts/scheduling-eviction/taint-and-toleration/): node controllerが自動追加する`node.kubernetes.io/*` taint（section 6）
- [Debugging Kubernetes Nodes with kubectl](https://kubernetes.io/docs/tasks/debug/debug-cluster/kubectl-node-debug/)と[`kubectl debug` reference](https://kubernetes.io/docs/reference/kubectl/generated/kubectl_debug/): node debug Podと`--profile`値（sections 2、6、cheat sheet）
- [Debug Running Pods](https://kubernetes.io/docs/tasks/debug/debug-application/debug-running-pod/): ephemeral container、`--copy-to`、`--target`（cheat sheet）
- [EndpointSlices](https://kubernetes.io/docs/concepts/services-networking/endpoint-slices/): `v1 Endpoints`が1.33以降deprecatedである理由（section 4）
- [Debug Services](https://kubernetes.io/docs/tasks/debug/debug-application/debug-service/)と[Debugging DNS Resolution](https://kubernetes.io/docs/tasks/administer-cluster/dns-debugging-resolution/): selector/port/DNSの確認と`ndots`（section 5）

**Amazon EKS / AWS**

- [Amazon VPC CNI plugin README](https://github.com/aws/amazon-vpc-cni-k8s/blob/master/README.md): `WARM_ENI_TARGET`、`WARM_IP_TARGET`、`MINIMUM_IP_TARGET`、`ENABLE_PREFIX_DELEGATION`の意味と優先順位（section 9）
- [Assign more IP addresses to Amazon EKS nodes with prefixes](https://docs.aws.amazon.com/eks/latest/userguide/cni-increase-ip-addresses.html): prefix delegationとmax-pods再計算（section 9）
- [EKS Pod Identity](https://docs.aws.amazon.com/eks/latest/userguide/pod-identities.html)と[IAM roles for service accounts](https://docs.aws.amazon.com/eks/latest/userguide/iam-roles-for-service-accounts.html): trust policyの形式と注入される環境変数（section 8）
- [Detect node health issues and enable automatic node repair](https://docs.aws.amazon.com/eks/latest/userguide/node-health.html): section 6に示すNode Monitoring Agent condition
- [Troubleshoot problems with Amazon EKS clusters and nodes](https://docs.aws.amazon.com/eks/latest/userguide/troubleshooting.html): node参加失敗、`AccessDenied`、CNI error
- [Karpenter: Troubleshooting](https://karpenter.sh/docs/troubleshooting/): NodePool limit、requirement不一致、NodeClaimの起動／登録失敗（section 10）

***

< [前へ: Zonal Cluster Operations](15-zonal-operations-guide.md) | [目次](./README.md) >
