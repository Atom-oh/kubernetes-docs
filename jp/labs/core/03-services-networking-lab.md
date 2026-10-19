# Services とネットワーキングのラボガイド

> **難易度**: 中級
> **目安時間**: 45分
> **最終更新日**: 2026年9月11日

## 学習目標
- ClusterIP と NodePort の Service を作成する
- Service 経由で Pod にアクセスする
- DNS による Service ディスカバリーを検証する

## 前提条件
- [ ] kubectl と Kubernetes クラスター（minikube／kind）
- [ ] [Services and Networking](../../core/03-services-networking.md) の学習を完了している

使い捨ての kind／minikube クラスター、対応する kubectl context、namespace を作成する権限、正常に動作するクラスター DNS／CNI／レジストリへの接続を用意してください。ネットワークポリシーで、この演習の通信が許可されている必要があります。NodePort はノードのネットワークインターフェイスで公開されることがあるため、意図したテスト用ネットワークで実行してください。1 つの Bash セッションで作業します。この監査ではクラスターやトラフィックのテストを実行していません。

```bash
SERVICE_LAB_DIR=$(mktemp -d /tmp/k8s-docs-services.XXXXXX)
: "${SERVICE_LAB_DIR:?mktemp failed}"
SERVICE_LAB_CONTEXT=$(kubectl config current-context)
: "${SERVICE_LAB_CONTEXT:?No context selected}"
printf 'Selected context: %s\n' "$SERVICE_LAB_CONTEXT"
SERVICE_LAB_CANDIDATE=$(basename "$SERVICE_LAB_DIR" | tr '[:upper:].' '[:lower:]-')
unset SERVICE_LAB_NAMESPACE SERVICE_LAB_CLIENT_NAMESPACE SERVICE_LAB_CLIENT_UID
if SERVICE_LAB_UID=$(kubectl --context "$SERVICE_LAB_CONTEXT" create namespace "$SERVICE_LAB_CANDIDATE" -o jsonpath='{.metadata.uid}'); then
  SERVICE_LAB_NAMESPACE=$SERVICE_LAB_CANDIDATE
else
  printf 'Namespace creation failed; stop before resource operations\n' >&2
fi
service_kubectl() {
  kubectl --context "${SERVICE_LAB_CONTEXT:?}" --namespace "${SERVICE_LAB_NAMESPACE:?}" "$@"
}
```

---

## 演習 1: ClusterIP Service

### 手順

**ステップ 1.1: バックエンド Deployment を作成する**
```bash
cat > "${SERVICE_LAB_DIR:?}/web-deployment.yaml" << 'EOF'
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web
spec:
  replicas: 3
  selector:
    matchLabels:
      app: web
  template:
    metadata:
      labels:
        app: web
    spec:
      automountServiceAccountToken: false
      containers:
      - name: nginx
        image: nginx:1.30.6
        ports:
        - name: http
          containerPort: 80
        resources:
          requests:
            cpu: 100m
            memory: 64Mi
          limits:
            memory: 128Mi
        readinessProbe:
          httpGet:
            path: /
            port: http
EOF
service_kubectl apply -f "$SERVICE_LAB_DIR/web-deployment.yaml"
service_kubectl rollout status deployment/web --timeout=120s
```

**ステップ 1.2: ClusterIP Service を作成する**
```bash
cat > "${SERVICE_LAB_DIR:?}/clusterip-svc.yaml" << 'EOF'
apiVersion: v1
kind: Service
metadata:
  name: web-clusterip
spec:
  type: ClusterIP
  selector:
    app: web
  ports:
  - name: http
    port: 80
    targetPort: http
EOF
service_kubectl apply -f "$SERVICE_LAB_DIR/clusterip-svc.yaml"
service_kubectl get service web-clusterip
```

**ステップ 1.3: クラスター内からのアクセスをテストする**
```bash
service_kubectl run http-check --image=busybox:1.38.0 \
  --overrides='{"spec":{"automountServiceAccountToken":false}}' \
  --rm -i --restart=Never --pod-running-timeout=120s --command -- sh -c '
for attempt in 1 2 3 4 5; do
  wget -T 5 -qO- "$1" && exit 0
  sleep 1
done
exit 1
' sh http://web-clusterip/
```
<details>
<summary>ヒントを見る</summary>

- ClusterIP はクラスター内の仮想アドレスを提供します。セキュリティ境界ではなく、ルーティングされた通信の到達性はネットワークに依存します。
- DNS の完全修飾名は `<service>.<namespace>.svc.<cluster-domain>` です。`cluster.local` は一般的な既定値にすぎません。
- 通常の Pod DNS 検索設定では、同じ namespace 内なら `<service>`、別の namespace からなら `<service>.<namespace>` でアクセスできます。
</details>

### 検証
EndpointSlice は非推奨の Endpoints 表示に代わるリソースです。Ready 状態のバックエンドアドレスを確認してください。更新は非同期であり、スライスやアドレスファミリーごとに結果が分かれる場合があります。Ready なレプリカが 3 つあっても、すべての出力形式で必ず 3 行になるとは限りません。

```bash
service_kubectl get endpointslices -l kubernetes.io/service-name=web-clusterip -o wide
service_kubectl get endpointslices -l kubernetes.io/service-name=web-clusterip \
  -o jsonpath='{range .items[*].endpoints[*]}{.addresses}{" ready="}{.conditions.ready}{"\n"}{end}'
```

---

## 演習 2: NodePort Service

### 手順

**ステップ 2.1: NodePort Service を作成する**
```bash
cat > "${SERVICE_LAB_DIR:?}/nodeport-svc.yaml" << 'EOF'
apiVersion: v1
kind: Service
metadata:
  name: web-nodeport
spec:
  type: NodePort
  selector:
    app: web
  ports:
  - name: http
    port: 80
    targetPort: http
EOF
service_kubectl apply -f "$SERVICE_LAB_DIR/nodeport-svc.yaml"
SERVICE_LAB_NODE_PORT=$(service_kubectl get service web-nodeport -o jsonpath='{.spec.ports[0].nodePort}')
: "${SERVICE_LAB_NODE_PORT:?No allocated NodePort}"
service_kubectl get service web-nodeport
```

**ステップ 2.2: クラスター外からアクセスする**
NodePort は割り当てられるポートです。30080 が空いていると決めつけて指定しないでください。Service の type／port 一覧で確認できるのは設定であり、クライアントから到達できることではありません。ノードアドレスを直接使うコマンドは、ルーティング、nodePortAddresses、ファイアウォールポリシーが許可する環境でのみ実行してください。

```bash
printf 'Allocated NodePort: %s\n' "${SERVICE_LAB_NODE_PORT:?}"
kubectl --context "${SERVICE_LAB_CONTEXT:?}" get nodes -o wide

# Use only an address reachable from this client and permitted by node/firewall policy.
: "${SERVICE_LAB_NODE_ADDRESS:?Set a reachable node address}"
case "$SERVICE_LAB_NODE_ADDRESS" in
  *:*) SERVICE_LAB_NODE_URL_HOST="[$SERVICE_LAB_NODE_ADDRESS]" ;;
  *) SERVICE_LAB_NODE_URL_HOST=$SERVICE_LAB_NODE_ADDRESS ;;
esac
curl --disable --noproxy '*' --fail --show-error --silent --max-time 5 \
  "http://$SERVICE_LAB_NODE_URL_HOST:$SERVICE_LAB_NODE_PORT/"
```

minikube では、対象とするプロファイルを選択してください。Docker driver を使う一部の環境では、トンネルを開いたままにするため、別のターミナルで service コマンドを実行する必要があります。そのコマンドが表示する URL を使ってください。エラーを抑制したり、固定ポートに置き換えたりしないでください。kind からホスト経由でアクセスするには、あらかじめ設定した extraPortMappings が Service の nodePort と一致している必要があります。ノード IP に到達できない場合は、別途選んだ `service_kubectl port-forward --address=127.0.0.1 service/web-nodeport 18080:80` でアプリケーションをテストできますが、これは NodePort のデータ経路を検証するものではありません。

```bash
# Only for minikube: the profile must correspond to SERVICE_LAB_CONTEXT.
: "${SERVICE_LAB_MINIKUBE_PROFILE:?Set the matching minikube profile}"
minikube --profile "$SERVICE_LAB_MINIKUBE_PROFILE" \
  service web-nodeport --namespace "${SERVICE_LAB_NAMESPACE:?}" --url
```
### 検証
```bash
service_kubectl get service web-nodeport -o jsonpath='{.spec.type}{"\n"}{.spec.ports[0].nodePort}{"\n"}'
```

---

## 演習 3: DNS Service ディスカバリー

### 手順

**ステップ 3.1: DNS lookup をテストする**
```bash
service_kubectl run dns-check --image=busybox:1.38.0 \
  --overrides='{"spec":{"automountServiceAccountToken":false}}' \
  --rm -i --restart=Never --pod-running-timeout=120s --command -- nslookup web-clusterip
service_kubectl get service web-clusterip -o jsonpath='{.spec.clusterIP}{"\n"}'
```

リゾルバー IP、応答 IP、クラスターのドメインは、クラスターによって異なります。この通常の ClusterIP Service では、DNS は上記の Service 仮想 IP に解決されるはずです。各バックエンド Pod の IP には解決されません。完全修飾名にはこのラボの namespace が含まれ、既定の namespace を固定で指定するものではありません。

**ステップ 3.2: 別の namespace からアクセスする**
```bash
SERVICE_LAB_CLIENT_CANDIDATE="${SERVICE_LAB_NAMESPACE:?}-client"
unset SERVICE_LAB_CLIENT_NAMESPACE
if SERVICE_LAB_CLIENT_UID=$(kubectl --context "${SERVICE_LAB_CONTEXT:?}" create namespace "$SERVICE_LAB_CLIENT_CANDIDATE" -o jsonpath='{.metadata.uid}'); then
  SERVICE_LAB_CLIENT_NAMESPACE=$SERVICE_LAB_CLIENT_CANDIDATE
  kubectl --context "$SERVICE_LAB_CONTEXT" --namespace "$SERVICE_LAB_CLIENT_NAMESPACE" \
    run cross-ns-check --image=busybox:1.38.0 \
    --overrides='{"spec":{"automountServiceAccountToken":false}}' \
    --rm -i --restart=Never --pod-running-timeout=120s --command -- \
    wget -T 5 -qO- "http://web-clusterip.$SERVICE_LAB_NAMESPACE/"
else
  printf 'Client namespace was not created; no cross-namespace test was run\n' >&2
fi
```

<details>
<summary>ヒントを見る</summary>

- 標準の DNS 検索パスでは、namespace をまたいでも `service.namespace` で指定できます。クラスターの完全修飾ドメインを使う方法もあります。
- Service の DNS レコードは CoreDNS または設定済みのクラスター DNS 実装が公開します。
- DNS Pod は `kubectl get pods -n kube-system -l k8s-app=kube-dns` で確認してください。
</details>

---

## クリーンアップ
```bash
delete_service_lab_namespace() {
  local name="$1" expected_uid="$2" current_uid
  [[ -n "$name" && -n "$expected_uid" ]] || return 0
  current_uid=$(kubectl --context "${SERVICE_LAB_CONTEXT:?}" get namespace "$name" -o jsonpath='{.metadata.uid}') || return 0
  if [ "$current_uid" = "$expected_uid" ]; then
    kubectl --context "$SERVICE_LAB_CONTEXT" delete namespace "$name" --timeout=120s
  else
    printf 'Namespace identity changed; deletion skipped: %s\n' "$name"
  fi
}
delete_service_lab_namespace "${SERVICE_LAB_CLIENT_NAMESPACE:-}" "${SERVICE_LAB_CLIENT_UID:-}"
delete_service_lab_namespace "${SERVICE_LAB_NAMESPACE:-}" "${SERVICE_LAB_UID:-}"
if [[ -n ${SERVICE_LAB_DIR:-} ]]; then
  rm -f -- "$SERVICE_LAB_DIR/web-deployment.yaml" "$SERVICE_LAB_DIR/clusterip-svc.yaml" "$SERVICE_LAB_DIR/nodeport-svc.yaml"
  rmdir -- "$SERVICE_LAB_DIR"
fi
unset -f service_kubectl delete_service_lab_namespace
```

## 参考資料と検証範囲

* [Service](https://kubernetes.io/docs/concepts/services-networking/service/)
* [EndpointSlice](https://kubernetes.io/docs/concepts/services-networking/endpoint-slices/)
* [Service と Pod の DNS](https://kubernetes.io/docs/concepts/services-networking/dns-pod-service/)
* [minikube のアクセス](https://minikube.sigs.k8s.io/docs/handbook/accessing/)
* [kind のポートマッピング](https://kind.sigs.k8s.io/docs/user/configuration/#extra-port-mappings)

検証はローカルのマニフェスト／コマンド確認であり、CNI、DNS、NodePort の実測テストを記録したものではありません。一時的なクライアントは明示したコマンドで実行し、ServiceAccount token を必要としません。

## 次のステップ
- [Services and Networking クイズ](../../quizzes/core/03-services-networking-quiz.md)
- [ストレージラボ](./04-storage-lab.md)
