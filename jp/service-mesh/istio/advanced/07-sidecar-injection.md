# Sidecar injection

> **検証基準**: Istio 1.31.0、Kubernetes 1.32～1.37
> **最終確認日**: 2026年10月16日

自動 injection は、新しく作成される Pod を変更する admission webhook です。稼働中の Pod に後から sidecar を追加したり、Deployment template 自体を編集したりするものではありません。手動の `istioctl kube-inject` は、proxy 設定を含む application manifest を生成します。

## 自動 injection の設定

### Namespace レベル

既存の application namespace では、いずれか 1 つの injection mode を使ってください。label を変更する前に、現在の label とインストール済み revision を記録してください。一致する injector のない revision/tag の label は使用しないでください。

```bash
# Existing, reviewed application namespace; inspect before choosing one mode.
INJECTION_NAMESPACE=injection-demo
kubectl get namespace "$INJECTION_NAMESPACE" -L istio-injection,istio.io/rev,istio.io/dataplane-mode

# Legacy/default injection alternative, only when no revision/ambient mode is selected.
kubectl label namespace "$INJECTION_NAMESPACE" istio-injection=enabled --overwrite
```

```bash
# Alternative: choose an already installed revision or existing revision tag.
istioctl tag list
kubectl get mutatingwebhookconfigurations -l istio.io/rev
kubectl label namespace "$INJECTION_NAMESPACE" istio-injection-
kubectl label namespace "$INJECTION_NAMESPACE" istio.io/rev=<installed-revision-or-tag> --overwrite
```

namespace に `istio-injection` と `istio.io/rev` の両方がある場合は、従来の `istio-injection` label が優先されます。namespace の `istio-injection=disabled` または Pod の `sidecar.istio.io/inject="false"` は、ほかの injection label が有効化を要求していても injection を無効にします。明示的な label がない場合、installer が `enableNamespacesByDefault` を有効にしていなければ、通常は injection されません。

availability、PDB、capacity を確認したうえで、選択した injector を適用する対象 workload だけを再作成してください。namespace label を変更しただけでは、既存 Pod は変わりません。ambient への参加は別に管理し、dataplane mode を混在させずに[ambient 移行ガイド](01-ambient-mode.md)を使ってください。

### Pod レベル

injection の **label** は Pod 自体、または Deployment の `spec.template.metadata` に設定します。同じ名前の以前の annotation は非推奨です。

```yaml
# Existing Deployment: spec.template fragment
metadata:
  labels:
    sidecar.istio.io/inject: "true"
```

この設定は対象 Pod を injection 対象にしますが、namespace 側の無効化を上書きしたり、application を deploy したりするものではありません。既存の app label、revision、workload 設定を維持してください。これは fragment であり、`myapp:latest` のような未確認 image を含む実行可能 Pod ではありません。

## 手動 injection

意図した control plane に一致する `istioctl` version と完全な設定を使ってください。既定では kube-inject は選択した cluster の設定を読み取ることがあります。ローカルで再現可能な生成を行う場合は、対象 revision の実際の injector/mesh ConfigMap を export し、先に内容を確認してください。

```bash
# Obtain all three files from the same installed revision/configuration.
kubectl -n istio-system get configmap <injector-configmap> -o jsonpath='{.data.config}' > inject-config.yaml
kubectl -n istio-system get configmap <injector-configmap> -o jsonpath='{.data.values}' > inject-values.yaml
kubectl -n istio-system get configmap <mesh-configmap> -o jsonpath='{.data.mesh}' > mesh-config.yaml

# Render from the reviewed original application manifest with matching istioctl.
istioctl kube-inject --revision <actual-revision-or-default> --injectConfigFile inject-config.yaml --meshConfigFile mesh-config.yaml --valuesFile inject-values.yaml --filename deployment.yaml --output deployment-injected.yaml

# Review the generated file and deployment diff before the planned rollout.
kubectl diff -f deployment-injected.yaml
kubectl apply -f deployment-injected.yaml
```

Istio 1.31 では、`--revision` を省略すると、ローカルファイルを指定していても default-revision cluster watcher が起動し、command が待ち続ける場合があります。export した設定に一致する実際の revision、または revision を使わない構成では `default` を指定してください。明示的な revision と 3 つすべてのローカル設定ファイルを使う生成については、cluster discovery を行わないことを確認済みです。

`deployment.yaml` には元の application resource が含まれていなければなりません。これを生成出力と分離し、設定や version が変わった場合は元のファイルから再生成してください。自動 injection と手動 injection のどちらを管理元とするか決め、admission 結果を確認してください。生成された proxy container に場当たり的な変更を重ねないでください。`kubectl diff` の終了コード 1 は通常、差分が見つかったことを示します。適用が承認または検証されたという意味ではありません。

## Sidecar resource の設定

次は元の例で使われている request/limit です。本番環境の sizing 値ではなく、個別 workload の tuning 入力として扱ってください。

```yaml
# Existing Deployment: spec.template fragment
metadata:
  annotations:
    sidecar.istio.io/proxyCPU: "100m"
    sidecar.istio.io/proxyMemory: "128Mi"
    sidecar.istio.io/proxyCPULimit: "200m"
    sidecar.istio.io/proxyMemoryLimit: "256Mi"
```

request と対応する limit は意図して設定してください。対応する limit を指定せず `proxyCPU`/`proxyMemory` だけを指定すると、その limit がなくなる場合があります。生成後の proxy resource、namespace の LimitRange/ResourceQuota、CPU throttling、メモリ使用量を確認してください。Pod template の変更は、新しく作成される Pod に反映されます。

## injection 対象からの除外

```yaml
# Existing Deployment: spec.template fragment
metadata:
  labels:
    sidecar.istio.io/inject: "false"
```

この label は今後の sidecar injection を防ぎます。すでに injection 済みの proxy を削除したり、Pod を ambient capture の対象外にしたりするものではありません。既存の label/annotation を整合させ、通常の rollout 経路で選択した workload だけを再作成してください。

## トラブルシューティング

```bash
kubectl get namespace "$INJECTION_NAMESPACE" -L istio-injection,istio.io/rev,istio.io/dataplane-mode
kubectl get mutatingwebhookconfigurations
kubectl get events -n "$INJECTION_NAMESPACE" --sort-by=.lastTimestamp

kubectl get pods -n "$INJECTION_NAMESPACE" -o json |
  jq '.items[] | {
    pod:.metadata.name,
    revision:.metadata.annotations["istio.io/rev"],
    proxies: ([.spec.containers[]?, .spec.initContainers[]?] |
      map(select(.name == "istio-proxy") | {name,image,restartPolicy}))
  }'
istioctl proxy-status
```

native sidecar は `restartPolicy: Always` を持つ `spec.initContainers` に配置され、従来型 sidecar は `spec.containers` に配置されます。Kubernetes の native sidecar は 1.33 で stable となり、1.32 では既定で有効です。一方、Istio の `sidecar.istio.io/nativeSidecar` annotation は引き続き Alpha として記載されています。2/2 READY 表示がどの環境でも一律に使えると仮定せず、インストール済み injector の動作を確認してください。

Pod が作成されない場合は、controller event、webhook の到達性と証明書、namespace/object selector、revision の有無、resource admission limit を調査します。proxy が存在する場合は、readiness、log、xDS 同期を個別に確認してください。proxy 名があるだけでは、mesh への登録が正しい証拠にはなりません。

## 参考資料

- [Istio sidecar injection](https://istio.io/latest/docs/setup/additional-setup/sidecar-injection/)
- [Istio injection annotations](https://istio.io/latest/docs/reference/config/annotations/)
- [Istio revision upgrades](https://istio.io/latest/docs/setup/upgrade/canary/)
- [Kubernetes native sidecar containers](https://kubernetes.io/docs/concepts/workloads/pods/sidecar-containers/)
- [Istio 1.31 injection template](https://raw.githubusercontent.com/istio/istio/1.31.0/manifests/charts/istio-control/istio-discovery/files/injection-template.yaml)
- [Istio 1.31 local injection command](https://raw.githubusercontent.com/istio/istio/1.31.0/istioctl/pkg/kubeinject/kubeinject.go)
- [Istio 1.31 default revision resolution](https://raw.githubusercontent.com/istio/istio/1.31.0/istioctl/pkg/cli/context.go)
