# トラブルシューティング・プレイブック・クイズ

> **関連ドキュメント**: [Kubernetes/EKS トラブルシューティング・プレイブック](../../ops/16-troubleshooting-playbook.md)

## 多肢選択問題

### 1. `Pending` Pod に次の `FailedScheduling` event が表示されています。このメッセージの正しい読み方はどれですか？

```
0/15 nodes are available: 1 Insufficient cpu, 1 Insufficient memory,
6 node(s) didn't match Pod's node affinity/selector, 8 node(s) had untolerated taint(s).
```

- A) 15 個すべての Node で CPU とメモリが不足している
- B) この Pod の対象となる Node は 1 個だけであり、その Node では CPU とメモリが不足している
- C) scheduler が壊れており、どの Node も評価できなかった
- D) 8 個の Node に Pod が多すぎるため（`Too many pods`）スケジューリングに失敗した

<details>
<summary>回答を表示</summary>

**回答: B) この Pod の対象となる Node は 1 個だけであり、その Node では CPU とメモリが不足している**

**解説:**
scheduler は Node ごとに拒否理由を集計します。8 個の Node は一致する toleration がない taint により、6 個は nodeSelector/affinity の label 不一致により拒否され、残り 1 個の Node では CPU とメモリが不足しています。つまり、スケジューリング制約を満たす Node はちょうど 1 個ですが、その Node は容量がいっぱいです。このため、toleration/label の対象を広げるか、それらを満たす Node を追加します（Karpenter では、label key が NodePool requirements に含まれている必要があります）。

</details>

### 2. プライベート ECR image を使用する Pod が `ImagePullBackOff` であり、`describe` event に `Failed to pull image "...dkr.ecr...": ... 401 Unauthorized` と表示されています。最初に何を疑うべきですか？

- A) image tag のタイプミス
- B) Node IAM role に ECR pull 権限（`AmazonEC2ContainerRegistryPullOnly` または `ReadOnly`）がない
- C) Docker Hub の rate limit（`toomanyrequests`）
- D) NAT/VPC endpoint のないプライベート subnet

<details>
<summary>回答を表示</summary>

**回答: B) Node IAM role に ECR pull 権限（`AmazonEC2ContainerRegistryPullOnly` または `ReadOnly`）がない**

**解説:**
診断の手掛かりは `Failed to pull image` の後に続く内容です。`401 Unauthorized` / `no basic auth credentials` は registry authentication の失敗を意味します。ECR では kubelet が Node IAM role で authentication するため、その role の ECR pull 権限を確認してください。tag のタイプミスは `not found` / `manifest unknown`、network path の問題は `dial tcp ... i/o timeout`、Docker Hub の制限は `toomanyrequests` として現れます。

</details>

### 3. `CrashLoopBackOff` Pod の `lastState.terminated` に `Reason: OOMKilled`、`Exit Code: 137` と表示されています。正しい説明はどれですか？

- A) app 自身が error を検出し、code 1 で終了した
- B) memory limit を超過したため kernel が SIGKILL を送信した。limit を引き上げるか memory leak を修正する
- C) SIGTERM を受け取って正常に shutdown したため、対処は不要である
- D) image architecture（arm64/amd64）が Node と一致していない

<details>
<summary>回答を表示</summary>

**回答: B) memory limit を超過したため kernel が SIGKILL を送信した。limit を引き上げるか memory leak を修正する**

**解説:**
exit code 137 は SIGKILL（128+9）です。Reason が `OOMKilled` の場合、memory limit を超過したため kernel OOM killer が container を終了させています。同じ 137 でも Reason が `Error` であれば、container が `terminationGracePeriodSeconds` 内に終了しなかった liveness failure など、別の理由による SIGKILL です。正常な SIGTERM による終了は 143 であり、architecture の不一致は shell entrypoint では 126（`cannot execute binary file: Exec format error`）、image が binary を直接 exec する場合は Reason `StartError` として現れます。crash の直前の log は `kubectl logs <pod> -c <container> --previous` で確認してください。

</details>

### 4. すべての Pod が `1/1 Running` ですが、request が Service に到達しません。`kubectl get endpointslices -l kubernetes.io/service-name=<svc>` の ENDPOINTS column は空です。最も可能性が高い原因は何ですか？

- A) CoreDNS Pod が停止しており、name resolution が失敗している
- B) Service の `selector` が Pod label と一致していない
- C) `targetPort` が container の listen port と異なっている
- D) NetworkPolicy が ingress を block している

<details>
<summary>回答を表示</summary>

**回答: B) Service の `selector` が Pod label と一致していない**

**解説:**
EndpointSlice には Service selector に一致する **Ready Pod** の IP が一覧表示されます。すべての Pod が Ready であるにもかかわらず slice が空の場合、selector と Pod label が異なっています（Helm chart では `selectorLabels` と `podLabels` のずれがよくある原因です）。`targetPort` が誤っている場合は IP と `connection refused`、NetworkPolicy による block は IP と timeout、CoreDNS の停止は `NXDOMAIN`/resolution failure として現れます。Kubernetes 1.33+ では `kubectl get endpoints` に deprecation warning が表示されるため、代わりに EndpointSlice を確認してください。

</details>

### 5. Node の condition に `DiskPressure=True (KubeletHasDiskPressure)` と表示されています。node controller（kube-controller-manager）はどの taint を Node に自動追加しますか？

- A) `node.kubernetes.io/unreachable`
- B) `node.kubernetes.io/not-ready`
- C) `node.kubernetes.io/disk-pressure`
- D) `node.kubernetes.io/memory-pressure`

<details>
<summary>回答を表示</summary>

**回答: C) `node.kubernetes.io/disk-pressure`**

**解説:**
各 Node condition には対応する自動 taint があります。`DiskPressure` → `node.kubernetes.io/disk-pressure`、`MemoryPressure` → `node.kubernetes.io/memory-pressure`、`PIDPressure` → `node.kubernetes.io/pid-pressure`、`Ready=False` → `node.kubernetes.io/not-ready`、および `Ready=Unknown`（kubelet が status の送信を停止し、reason が `NodeStatusUnknown`）→ `node.kubernetes.io/unreachable` です。このため、Node が `Ready` であっても、新しい Pod は `node(s) had untolerated taint(s)` によりその Node を回避することがあります。DiskPressure は一般に image cache と container log が root volume を埋めることで発生し、Pod は `The node was low on resource: ephemeral-storage` とともに `Evicted` されます。

</details>

### 6. PVC が `Pending` であり、`describe pvc` に `WaitForFirstConsumer: waiting for first consumer to be created before binding` だけが表示されています。この PVC を使用する Pod はまだ deploy されていません。適切な判断はどれですか？

- A) StorageClass 名のスペルが間違っている。`kubectl get sc` で確認する
- B) EBS CSI controller に IAM permission がない
- C) これは正常である。`volumeBindingMode: WaitForFirstConsumer` は Pod がスケジュールされるまで volume 作成を保留する
- D) PV が別の AZ にあり、`volume node affinity conflict` が発生している

<details>
<summary>回答を表示</summary>

**回答: C) これは正常である。`volumeBindingMode: WaitForFirstConsumer` は Pod がスケジュールされるまで volume 作成を保留する**

**解説:**
EKS が default で作成する `gp2` StorageClass は `WaitForFirstConsumer` binding mode を使用します。EBS CSI driver 用に作成する `gp3` StorageClass でも、`volumeBindingMode: WaitForFirstConsumer` を明示的に設定した場合にのみ同様となります。API default は `Immediate` です。playbook の `kubectl get storageclass` output が示すように、verification cluster の `gp3` class にはこの設定があります。この遅延は意図的なものです。Pod がスケジュールされる AZ で EBS volume が作成されるため、使用する Pod がない間に PVC が `Pending` のままでも問題ではありません。StorageClass のタイプミスは `storageclass.storage.k8s.io "<name>" not found`、IAM permission の不足は `ProvisioningFailed` + `UnauthorizedOperation`/`AccessDenied`、AZ の不一致は Pod の `FailedScheduling` event に `volume node affinity conflict` として現れます。

</details>

### 7. Pod 内からの AWS API call が `AccessDenied` となり、拒否された principal が service account role ではなく Node IAM role です。`kubectl get sa` には `eks.amazonaws.com/role-arn` annotation が表示されますが、Pod env には `AWS_ROLE_ARN`/`AWS_WEB_IDENTITY_TOKEN_FILE` がありません。原因と修正方法は何ですか？

- A) IAM role の permission policy が不十分である → policy に action を追加する
- B) Pod 作成**後**に annotation が追加されたため、webhook が credentials を inject しなかった → `kubectl rollout restart`
- C) OIDC provider がない → cluster を再作成する
- D) EKS Pod Identity agent が停止している → agent を再起動する

<details>
<summary>回答を表示</summary>

**回答: B) Pod 作成後に annotation が追加されたため、webhook が credentials を inject しなかった → `kubectl rollout restart`**

**解説:**
IRSA は、pod-identity-webhook が `AWS_ROLE_ARN` と `AWS_WEB_IDENTITY_TOKEN_FILE` env（および token volume）を **Pod 作成時**に inject することで機能します。inject の痕跡がない場合、Pod は annotation が存在する前に作成されたか、SA 名が異なっています。そのため SDK は credentials を見つけられず、Node role に fallback します。Pod を再作成すると解決します。permission policy の不足（A）は異なる形で現れます。env は正常ですが、特定の API が拒否されます。Pod Identity（D）は `AWS_CONTAINER_CREDENTIALS_FULL_URI` env により識別できます。

</details>

### 8. Pod が `Pending` で、新しい NodeClaim は作成されず、Karpenter event に `all available instance types exceed limits for nodepool "graviton"` と表示されています。原因は何ですか？

- A) Pod の nodeSelector label key が NodePool requirements に含まれていない
- B) NodePool taint に対する toleration がない
- C) NodePool の `spec.limits`（cpu/memory）にすでに到達している
- D) EC2 にその AZ の capacity がない（`InsufficientInstanceCapacity`）

<details>
<summary>回答を表示</summary>

**回答: C) NodePool の `spec.limits`（cpu/memory）にすでに到達している**

**解説:**
Karpenter は Pod に対してすべての NodePool を確認し、それぞれが拒否された理由を event として記録します。`exceed limits` は、追加可能な instance のいずれも NodePool を `spec.limits` 超過に至らせることを意味します。`kubectl get nodepool -o custom-columns=...spec.limits.cpu,...status.resources.cpu` は limit と usage が等しいことを示します。label key の不足は `label "<key>" does not have known values`、toleration の不足は `did not tolerate <key>=<value>:NoSchedule`、EC2 capacity の不足は Karpenter controller log に `InsufficientInstanceCapacity` として現れます。

</details>

### 9. EKS Node 上の Pod が `ContainerCreating` で停止し、event に `FailedCreatePodSandBox ... plugin type="aws-cni" ... failed to assign an IP address to container` と表示されています。subnet の `AvailableIpAddressCount` は 1 桁であり、`aws-node` は VPC CNI の default（`WARM_ENI_TARGET=1`、`WARM_IP_TARGET`/`MINIMUM_IP_TARGET` は未設定）で稼働しています。正しい説明はどれですか？

- A) `WARM_ENI_TARGET=1` default は、Node ごとに spare ENI 1 個分の IP を保持するため、subnet は Pod 数から想定されるよりずっと早く枯渇する。`WARM_IP_TARGET`/`MINIMUM_IP_TARGET` を設定すると、これらが warm-ENI rule より優先されるため warm pool は縮小する
- B) `WARM_ENI_TARGET=0` を設定するだけで十分である。`WARM_ENI_TARGET` が設定されている間は `WARM_IP_TARGET` が無視されるためである
- C) `ENABLE_PREFIX_DELEGATION=true` はより多くの ENI を attach して IP を追加するため、どの instance family でも機能する
- D) `FailedCreatePodSandBox` は scheduler が Node を見つけられなかったことを意味するため、これは `Too many pods` と同じ failure である

<details>
<summary>回答を表示</summary>

**回答: A) `WARM_ENI_TARGET=1` default は、Node ごとに spare ENI 1 個分の IP を保持するため、subnet は Pod 数から想定されるよりずっと早く枯渇する。`WARM_IP_TARGET`/`MINIMUM_IP_TARGET` を設定すると、これらが warm-ENI rule より優先されるため warm pool は縮小する**

**解説:**
default の `WARM_ENI_TARGET=1` のみでは、ipamd は各 Node に spare ENI 1 個を完全に attach した状態で保持します（m5.xlarge では ENI あたり 15 IP）。そのため、小さな subnet では Pod よりはるかに早く事前確保された IP が枯渇します。`WARM_IP_TARGET`/`MINIMUM_IP_TARGET` を設定すると、これらが warm-ENI rule を上書きします。playbook の verification cluster では `WARM_IP_TARGET=3`、`MINIMUM_IP_TARGET=6` を使用しているため、Node は使用中の Pod 分に加えて spare IP を 3 個だけ保持し、合計で 6 IP 未満になることはありません（`MINIMUM_IP_TARGET` は spare 数ではなく、使用中と spare を合わせた合計を下限とします）。B は優先順位を逆にしています。prefix delegation（C）は ENI を追加するのではなく、既存の ENI slot に /28 prefix を割り当てます。また、Nitro-based instance と max-pods の再計算が必要です。D は 2 つの症状を混同しています。`FailedCreatePodSandBox` はスケジューリング後に発生し、kubelet が IP の残っていない Node 上の CNI に IP を要求したときに発生します。`Too many pods` は `allocatable.pods` にすでに到達しているため scheduler が Node を拒否する際に発生します。両者は根本原因（割り当て可能な IP がない）を共有しますが、発生する段階が異なります。

</details>
