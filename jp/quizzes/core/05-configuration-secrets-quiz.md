# 設定クイズ

このクイズでは、ConfigMap、Secret、環境変数、resource requests と limits を含む Kubernetes の設定概念についての理解を確認します。

## 選択式問題

1. Kubernetes で機密情報を保存するために使用される resource は何ですか？
   - A) ConfigMap
   - B) Secret
   - C) Volume
   - D) Deployment
   
<details>

<summary>回答を表示</summary>

**回答: B) Secret**

**解説:**
Secret は、password、OAuth token、SSH key などの機密情報を保存するための Kubernetes resource です。Secret はデフォルトで base64 にエンコードされて保存され、ファイルまたは環境変数として Pod にマウントできます。ConfigMap は機密性のない設定データを保存するために使用されます。
</details>

2. Kubernetes における ConfigMap の主な目的は何ですか？
   - A) container image を保存する
   - B) アプリケーション設定データを保存する
   - C) network policy を定義する
   - D) Pod のスケジューリングを制御する
   
<details>

<summary>回答を表示</summary>

**回答: B) アプリケーション設定データを保存する**

**解説:**
ConfigMap は、key-value pair で設定データを保存する Kubernetes resource です。これにより、アプリケーションコードと設定を分離でき、環境ごとに異なる設定を使用できます。ConfigMap は、環境変数、command-line arguments、または設定ファイルとして container にマウントできます。
</details>

3. Kubernetes Pod の resource requests と limits は、それぞれどのような役割を果たしますか？
   - A) requests はスケジューリングと resource 割り当ての基準となり、limits は実行時の使用量を制限する
   - B) requests は Pod が使用できる最大 resource、limits は最小 resource
   - C) requests はスケジューリングにのみ使われ、limits は実行時にのみ適用される
   - D) requests は CPU にのみ適用され、limits は memory にのみ適用される
   
<details>

<summary>回答を表示</summary>

**回答: A) requests はスケジューリングと resource 割り当ての基準となり、limits は実行時の使用量を制限する**

**解説:**
Requests はスケジューリング容量の確保に使われ、実行時のリソース割り当てにも影響します。プロセスの使用量は request を下回ることがあります。CPU limit は throttling によって適用され、memory limit は OOM kill によって事後的に適用されます。request が設定されていても、Node のリソース圧迫から Pod が保護されるわけではありません。
</details>

4. Kubernetes で Secret data を Pod に提供する方法ではないものはどれですか？
   - A) 環境変数として
   - B) マウントされた volume として
   - C) image registry credentials として
   - D) network interface として
   
<details>

<summary>回答を表示</summary>

**回答: D) network interface として**

**解説:**
Kubernetes で Secret data を Pod に提供する方法には、環境変数として、マウントされた volume として、image registry credentials として提供する方法があります。network interface を通じて Secret を提供することは Kubernetes ではサポートされていません。
</details>

5. `kubectl create configmap` がサポートしていない入力方法はどれですか？
   - A) literal value から
   - B) ファイルから
   - C) ディレクトリから
   - D) `--from-url`
   
<details>

<summary>回答を表示</summary>

**回答: D) `--from-url`**

**解説:**
ConfigMap は literal value（`--from-literal`）、ファイル（`--from-file`）、ディレクトリ（`--from-file=<directory>`）から作成できます。このコマンドに `--from-url` flag はありません。ただし、Kubernetes REST API request で ConfigMap を作成したり、URL から取得した manifest を適用したりすることはできます。
</details>

6. Kubernetes で Pod の service account を指定するために使用される field は何ですか？
   - A) spec.serviceAccount
   - B) spec.serviceAccountName
   - C) metadata.serviceAccount
   - D) spec.account
   
<details>

<summary>回答を表示</summary>

**回答: B) spec.serviceAccountName**

**解説:**
Kubernetes では、Pod の service account は `spec.serviceAccountName` field を通じて指定されます。この field により、Pod が使用する service account を指定できます。指定しない場合、namespace の default service account が使用されます。
</details>

7. Kubernetes における Secret data のデフォルトのエンコード方式は何ですか？
   - A) AES-256
   - B) Base64
   - C) SHA-256
   - D) エンコードなし
   
<details>

<summary>回答を表示</summary>

**回答: B) Base64**

**解説:**
Kubernetes の Secret data はデフォルトで Base64 にエンコードされて保存されます。これは単なるエンコードであり、暗号化ではないため、追加のセキュリティ対策が必要です。Kubernetes 1.13 以降、etcd に保存される Secret data の暗号化が利用可能です。
</details>

8. Pod manifest に実際の password を記述する場合、避けるべき方法はどれですか？
   - A) Secret key を参照する
   - B) 保護された Secret volume を使う
   - C) Pod spec に直接ハードコードする
   - D) workload identity を使って外部の Secret manager から取得する
   
<details>

<summary>回答を表示</summary>

**回答: C) Pod spec に直接ハードコードする**

**解説:**
manifest や log に password を文字列のまま記述しないでください。機密情報でない定数なら `env.value` を直接使えますが、機密値には Secret または外部の Secret store を使用します。ConfigMap と Downward API は password の保存先ではありません。
</details>

9. Pod レベルの resource 設定がない場合、すべての container で CPU と memory の requests が limits と等しいとき、割り当てられる QoS (Quality of Service) class はどれですか？
   - A) Guaranteed
   - B) Burstable
   - C) BestEffort
   - D) Critical
   
<details>

<summary>回答を表示</summary>

**回答: A) Guaranteed**

**解説:**
Guaranteed QoS class は、すべての container に resource requests と limits が設定され、各 resource の request と limit が等しい場合に割り当てられます。ただし、Eviction の判断では Pod priority と request に対する使用量も考慮されるため、Guaranteed は無条件に保護されることを意味しません。Burstable は、一部の container にのみ requests／limits が設定されている場合や、requests と limits が異なる場合に割り当てられます。requests と limits がどの container にも設定されていない場合は BestEffort です。
</details>

10. ConfigMap または Secret への変更が Pod に自動的に反映されるのはいつですか？
    - A) 常に自動的に反映される
    - B) subPath を除く完全な volume mount では、いずれ反映される
    - C) 環境変数として使用された場合のみ
    - D) 自動的には反映されない。Pod の restart が必要
    
<details>

<summary>回答を表示</summary>

**回答: B) subPath を除く完全な volume mount では、いずれ反映される**

**解説:**
変更可能な ConfigMap／Secret を通常の volume 全体として投影した場合、内容は最終的に更新されます（反映の遅延は kubelet の sync と cache／change-detection 設定によります）。`subPath` mount は更新されません。アプリケーションはファイルを再読み込みする必要があります。環境変数の場合は、アプリケーション container を置き換える／再起動するか、新しい Pod を展開する必要があります。
</details>

## 実践問題

1. ConfigMap と Secret を作成し、それらを環境変数および volume として Pod にマウントする方法を説明してください。

<details>

<summary>回答を表示</summary>

**回答:**

1. ConfigMap を作成する:
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
   name: app-config
data:
  app.name: MyApp
  app.properties: |
    app.name=MyApp
    app.version=1.0.0
  database.properties: |
    db.host=mysql
    db.port=3306
    db.name=mydb
```

2. Secret を作成する:
```yaml
apiVersion: v1
kind: Secret
metadata:
  name: app-secrets
type: Opaque
data:
  db.user: YWRtaW4=  # admin (base64 encoded)
  db.password: cGFzc3dvcmQxMjM=  # password123 (base64 encoded)
```

3. 環境変数および volume としてマウントする Pod を作成する:
```yaml
apiVersion: v1
kind: Pod
metadata:
  name: app-pod
spec:
  containers:
    - name: app
      image: myapp:1.0
      env:
        # Get environment variable from ConfigMap
        - name: APP_NAME
          valueFrom:
            configMapKeyRef:
              name: app-config
              key: app.name
        # Get environment variables from Secret
        - name: DB_USER
          valueFrom:
            secretKeyRef:
              name: app-secrets
              key: db.user
        - name: DB_PASSWORD
          valueFrom:
            secretKeyRef:
              name: app-secrets
              key: db.password
      volumeMounts:
        # Mount ConfigMap as volume
        - name: config-volume
          mountPath: /etc/config
        # Mount Secret as volume
        - name: secret-volume
          mountPath: /etc/secrets
          readOnly: true
  volumes:
    # Define ConfigMap volume
    - name: config-volume
      configMap:
        name: app-config
    # Define Secret volume
    - name: secret-volume
      secret:
        secretName: app-secrets
```

4. resource を適用する:
```bash
kubectl apply -f configmap.yaml
kubectl apply -f secret.yaml
kubectl apply -f pod.yaml
```

5. 環境変数を確認する:
```bash
kubectl exec app-pod -- sh -c 'test -n "$APP_NAME" && test -n "$DB_PASSWORD" && echo "Configuration available"'
```

6. マウントされた volume を確認する:
```bash
kubectl exec app-pod -- ls -la /etc/config
kubectl exec app-pod -- ls -la /etc/secrets
```

7. ファイル内容を確認する:
```bash
kubectl exec app-pod -- cat /etc/config/app.properties
kubectl exec app-pod -- test -s /etc/secrets/db.user
```
</details>

2. Pod に resource requests と limits を設定し、QoS class を確認する方法を説明してください。

<details>

<summary>回答を表示</summary>

**回答:**

1. 異なる QoS class の Pod を作成する:

**Guaranteed QoS の Pod**:
```yaml
apiVersion: v1
kind: Pod
metadata:
  name: guaranteed-pod
spec:
  containers:
    - name: nginx
      image: nginx
      resources:
        requests:
          memory: "100Mi"
          cpu: "100m"
        limits:
          memory: "100Mi"
          cpu: "100m"
```

**Burstable QoS の Pod**:
```yaml
apiVersion: v1
kind: Pod
metadata:
  name: burstable-pod
spec:
  containers:
    - name: nginx
      image: nginx
      resources:
        requests:
          memory: "100Mi"
          cpu: "100m"
        limits:
          memory: "200Mi"
          cpu: "200m"
```

**BestEffort QoS の Pod**:
```yaml
apiVersion: v1
kind: Pod
metadata:
  name: besteffort-pod
spec:
  containers:
    - name: nginx
      image: nginx
# No resource requests or limits
```

2. Pod を作成する:
```bash
kubectl apply -f guaranteed-pod.yaml
kubectl apply -f burstable-pod.yaml
kubectl apply -f besteffort-pod.yaml
```

3. QoS class を確認する:
```bash
kubectl get pods guaranteed-pod -o jsonpath='{.status.qosClass}'
# Output: Guaranteed

kubectl get pods burstable-pod -o jsonpath='{.status.qosClass}'
# Output: Burstable

kubectl get pods besteffort-pod -o jsonpath='{.status.qosClass}'
# Output: BestEffort
```

4. Pod の詳細を確認する:
```bash
kubectl describe pod guaranteed-pod | grep QoS
kubectl describe pod burstable-pod | grep QoS
kubectl describe pod besteffort-pod | grep QoS
```

5. resource 使用量を監視する:
```bash
kubectl top pod guaranteed-pod
kubectl top pod burstable-pod
kubectl top pod besteffort-pod
```

**QoS class の判定規則**:
  - **Guaranteed**: すべての container に resource requests と limits が設定され、requests が limits と等しい
  - **Burstable**: 少なくとも 1 つの container に resource requests が設定されているが、Guaranteed の条件を満たしていない
  - **BestEffort**: どの container にも resource requests または limits が設定されていない
</details>

3. Downward API を使用して Pod metadata と resource 情報を container に提供する方法を説明してください。

<details>

<summary>回答を表示</summary>

**回答:**

1. Downward API を使用する Pod を作成する:
```yaml
apiVersion: v1
kind: Pod
metadata:
  name: downward-api-pod
  labels:
    app: myapp
    environment: production
spec:
  containers:
    - name: main
      image: busybox
      command: ["sh", "-c", "while true; do echo Downward API Demo; sleep 10; done"]
      resources:
        requests:
          memory: "64Mi"
          cpu: "250m"
        limits:
          memory: "128Mi"
          cpu: "500m"
      env:
        # Provide pod metadata as environment variables
        - name: POD_NAME
          valueFrom:
            fieldRef:
              fieldPath: metadata.name
        - name: POD_NAMESPACE
          valueFrom:
            fieldRef:
              fieldPath: metadata.namespace
        - name: POD_IP
          valueFrom:
            fieldRef:
              fieldPath: status.podIP
        - name: NODE_NAME
          valueFrom:
            fieldRef:
              fieldPath: spec.nodeName
        - name: POD_SERVICE_ACCOUNT
          valueFrom:
            fieldRef:
              fieldPath: spec.serviceAccountName
        - name: POD_LABEL_APP
          valueFrom:
            fieldRef:
              fieldPath: metadata.labels['app']
        # Provide container resource information as environment variables
        - name: CPU_REQUEST
          valueFrom:
            resourceFieldRef:
              containerName: main
              resource: requests.cpu
              divisor: "1m"
        - name: CPU_LIMIT
          valueFrom:
            resourceFieldRef:
              containerName: main
              resource: limits.cpu
              divisor: "1m"
        - name: MEM_REQUEST
          valueFrom:
            resourceFieldRef:
              containerName: main
              resource: requests.memory
              divisor: "1Mi"
        - name: MEM_LIMIT
          valueFrom:
            resourceFieldRef:
              containerName: main
              resource: limits.memory
              divisor: "1Mi"
      volumeMounts:
        - name: podinfo
          mountPath: /etc/podinfo
  volumes:
    # Provide Downward API as volume
    - name: podinfo
      downwardAPI:
        items:
          - path: "labels"
            fieldRef:
              fieldPath: metadata.labels
          - path: "annotations"
            fieldRef:
              fieldPath: metadata.annotations
          - path: "cpu-request"
            resourceFieldRef:
              containerName: main
              resource: requests.cpu
              divisor: "1m"
          - path: "cpu-limit"
            resourceFieldRef:
              containerName: main
              resource: limits.cpu
              divisor: "1m"
```

2. Pod を作成する:
```bash
kubectl apply -f downward-api-pod.yaml
```

3. 環境変数を確認する:
```bash
kubectl exec downward-api-pod -- env | sort
```

4. volume ファイルを確認する:
```bash
kubectl exec downward-api-pod -- ls -la /etc/podinfo
kubectl exec downward-api-pod -- cat /etc/podinfo/labels
kubectl exec downward-api-pod -- cat /etc/podinfo/cpu-request
```

**Downward API で取得できるフィールド**:

**環境変数として取得できるフィールド**:
  - `metadata.name` - Pod 名
  - `metadata.namespace` - Pod namespace
  - `metadata.uid` - Pod UID
  - `metadata.labels['<KEY>']` - Pod label value
  - `metadata.annotations['<KEY>']` - Pod annotation value
  - `status.podIP` - Pod IP address
  - `spec.nodeName` - Pod が実行されている Node の名前
  - `spec.serviceAccountName` - Pod の service account 名
  - `status.hostIP` - Pod が実行されている Node の IP address

**Resource field**:
  - `requests.cpu` - CPU request
  - `limits.cpu` - CPU limit
  - `requests.memory` - Memory request
  - `limits.memory` - Memory limit
</details>
