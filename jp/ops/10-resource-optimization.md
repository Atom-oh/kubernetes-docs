# リソース最適化: requests、limits、言語ランタイム

> **最終更新**: September 11, 2026。例はKubernetes 1.36スキーマ、
> Java 21 / Spring Boot 4.1.1、Python 3.12 / Gunicorn 26.2.0、
> Node.js 24.21、Go 1.27.1、Rust 1.98 / Tokio 1.53.1で確認しました。

言語名や固定割合だけでワークロードのサイズを決めないでください。代表的な負荷、起動、再起動、GC、
障害条件でスループットとレイテンシーSLOを測定します。requests、limits、レプリカ、ランタイム同時実行数を
一緒に調整します。例の割合やしきい値はテストの出発点であり、性能保証ではありません。

## 1. Requests、limits、QoS

| リソース | Requests | Limits |
|---|---|---|
| CPU | スケジューリング上の計算と競合時の相対重み | Linux cgroup CPUクォータが実行を制限し得る |
| メモリ | スケジューリング上の計算 | 回収で割り当て圧力を満たせないとcgroup OOMを引き起こし得る |
| 未指定 | アドミッションのデフォルトと上位ポリシーが引き続き影響 | コンテナ上限がない場合もノード/祖先cgroup上限は適用 |

requestは物理CPU固定や事前メモリ割り当てではなく、アプリケーション性能を保証しません。
limitだけを指定し、他のアドミッションデフォルトがrequestを設定しなければ、Kubernetesはlimitをrequestへ
コピーします。LimitRangeと他ポリシー適用後の受け入れ済みPodを確認してください。

例はPodレベルでなくコンテナレベルのリソースを使います。
先に`resource-demo`を作成し、LimitRangeがリソースデフォルトを注入しない状態でQoSを比較します。
GuaranteedにはCPUとメモリの正の同一requests/limits、および通常/initコンテナに該当する条件が必要です。

```yaml
# qos-pods.yaml
apiVersion: v1
kind: Pod
metadata:
  name: guaranteed
  namespace: resource-demo
spec:
  containers:
  - name: app
    image: ghcr.io/stefanprodan/podinfo:6.15.0@sha256:ec73780a8425f59ea49f5bc8cdff0d598805a224fbaa1f86c67a244f250fa9da
    resources:
      requests:
        cpu: 500m
        memory: 256Mi
      limits:
        cpu: 500m
        memory: 256Mi
---
apiVersion: v1
kind: Pod
metadata:
  name: burstable
  namespace: resource-demo
spec:
  containers:
  - name: app
    image: ghcr.io/stefanprodan/podinfo:6.15.0@sha256:ec73780a8425f59ea49f5bc8cdff0d598805a224fbaa1f86c67a244f250fa9da
    resources:
      requests:
        cpu: 100m
        memory: 128Mi
      limits:
        memory: 256Mi
---
apiVersion: v1
kind: Pod
metadata:
  name: besteffort
  namespace: resource-demo
spec:
  containers:
  - name: app
    image: ghcr.io/stefanprodan/podinfo:6.15.0@sha256:ec73780a8425f59ea49f5bc8cdff0d598805a224fbaa1f86c67a244f250fa9da
    resources: {}
```

BestEffortはCPU/メモリのrequestsもlimitsも持たず、他の構成はBurstableになる場合があります。
Podレベルリソースやサイドカー/initリソース計算ではバージョン固有ルールを確認します。

QoSは絶対的な退避順序ではありません。メモリ圧力下ではkubeletは使用量がrequestを超えるか、
Pod Priority、requestに対する使用量を考慮します。Guaranteedとrequest内のBurstable Podは
後に検討される傾向がありますが、Guaranteedが常に最後の対象ではありません。
DiskPressureによる退避とコンテナ上限OOMを区別してください。OOMKilledは通常コンテナ終了理由で、
Podフェーズではありません。個々のプロセスがkillされる場合があります。PID 1が終了すると、
再起動ポリシーがコンテナの再起動動作を決定します。

### CPUクォータとメモリ境界

cgroup v1は`cpu.cfs_quota_us` / `cpu.cfs_period_us`、v2は`cpu.max`を使います。
100msは一般的なクォータ期間で、普遍的な定数ではありません。500mと100ms期間の場合、全スレッドが
合計50msの実行予算を共有します。スロットリングはレイテンシーとスループットの両方に影響し得ます。
スロットリング期間率は、スロットリングを含む期間の割合で、失われたCPU時間ではありません。

メモリ上限はヒープ上限ではありません。cgroup v1の`memory.limit_in_bytes`とv2の
`memory.max`を区別します。RSS、ネイティブ割り当て、スレッドスタック、ページキャッシュ、メモリを使う
emptyDirを考慮します。メモリがしきい値に近づくと再起動するlivenessプローブは、原因を隠し、
再起動ループを作る場合があり、一般的なOOM解決策ではありません。

CPU limit削除はそのコンテナのクォータスロットリングを減らせますが、競合、祖先クォータ、ノード制限を
なくしません。requests、優先順位、分離、ポリシー、SLOを一緒に評価します。

### 名前空間のデフォルトと予算

LimitRangeはアドミッションのデフォルトとリソースごとの制約を制御します。ResourceQuotaは名前空間の
requests、limits、オブジェクト数のアドミッション予算を制御します。実際のCPU使用量や費用を直接計測したり
制限したりはしません。適用前に`production`名前空間を作成してください。

```yaml
# namespace-policy.yaml
apiVersion: v1
kind: LimitRange
metadata:
  name: defaults
  namespace: production
spec:
  limits:
  - type: Container
    default:
      memory: 512Mi
    defaultRequest:
      cpu: 100m
      memory: 128Mi
    min:
      memory: 16Mi
    max:
      memory: 4Gi
---
apiVersion: v1
kind: ResourceQuota
metadata:
  name: budget
  namespace: production
spec:
  hard:
    requests.cpu: '8'
    requests.memory: 16Gi
    limits.memory: 32Gi
    pods: '20'
```

## 2. 測定とVPA

代表的な期間で分布、ピーク、起動コスト、メモリ増加を観察します。
P70のrequestsとP99のlimitsは検証する仮説で、普遍的デフォルトではありません。
GC、モデル読み込み、JIT、暗号処理、サイドカー、バッチ入力サイズは同じ言語でも異なります。
上限を上げるだけでリークを隠したり、待機/災害復旧Podをアイドルだから無駄と自動分類したりしないでください。

バージョン固定のVPAとGoldilocksインストールは[スケーリングの章](./06-scaling-strategies.md)を使います。
Goldilocksは選択した名前空間/ワークロードのVPAを作成・表示します。インストールだけで全体が自動最適化される
わけではありません。このVPAは後述の`resource-java` Deploymentを観測します。

```yaml
# vpa.yaml
apiVersion: autoscaling.k8s.io/v1
kind: VerticalPodAutoscaler
metadata:
  name: resource-java
  namespace: production
spec:
  targetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: resource-java
  updatePolicy:
    updateMode: 'Off'
  resourcePolicy:
    containerPolicies:
    - containerName: app
      controlledValues: RequestsOnly
      minAllowed:
        cpu: 100m
        memory: 256Mi
      maxAllowed:
        cpu: '4'
        memory: 4Gi
```

`Off`は推奨のみです。`target`はrequestの推奨値、上下限は推奨範囲です。
upperBoundをそのままメモリlimit、uncappedTargetを適用値と見なさないでください。
`RequestsAndLimits`は既存比率を維持してlimitsを調整でき、upperBoundをlimitsにコピーしません。

VPA 1.7.1では非推奨の`Auto`は`Recreate`として動作します。
`InPlaceOrRecreate`/`InPlace`の前提条件とKubernetesのインプレース対応を確認します。
`Initial`も新Podのrequestsを変更するため、requestベースHPA使用率の分母を変えます。
HPAと自動的に競合しないわけではありません。

1 Podが必要SLOで200 RPSを維持できるなら、1,000 RPSには定常状態で5 Podが必要です。
1 Pod喪失後も維持するには最低6 Podです。AZ全体の喪失に耐えられる保証ではありません。
20%容量を追加することと、利用可能容量の20%を未使用に保つことも区別します。
後者には`ceil(1000 / (200 × 0.8)) = 7`が必要です。

## 3. JVM: ヒープとコンテナメモリ

`MaxRAMPercentage`は検出メモリに基づくJVMヒープ自動調整への入力です。
75%が普遍的に最適ではなく、Pod limit変更を即時に追従する実行中リサイズ機能でもありません。
`-Xmx`、`-XX:MaxRAM`、小ヒープの自動調整も関係します。
Metaspace、コードキャッシュ、スタック、ダイレクトバッファ、JNI、アロケーターはヒープ外メモリを消費します。
固定25%で十分な非ヒープ容量が保証されるわけではありません。

JVMは`JAVA_OPTS`を自動で読みません。イメージのエントリーポイントがコマンドに渡す必要があります。
例はJVMが認識する`JAVA_TOOL_OPTIONS`と明示的な`java -jar`コマンドを使います。
60%はプロファイリングの出発点です。

以下の完全なSpring Boot例はJava 21とBoot 4.1.1でビルドしました。
指定プロジェクトパスにファイルを保存します。

```xml
<!-- java/pom.xml -->
<project xmlns="http://maven.apache.org/POM/4.0.0"
         xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
         xsi:schemaLocation="http://maven.apache.org/POM/4.0.0 https://maven.apache.org/xsd/maven-4.0.0.xsd">
  <modelVersion>4.0.0</modelVersion>
  <parent>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-parent</artifactId>
    <version>4.1.1</version>
    <relativePath/>
  </parent>
  <groupId>example</groupId>
  <artifactId>resource-api</artifactId>
  <version>1.0.0</version>
  <properties>
    <java.version>21</java.version>
  </properties>
  <dependencies>
    <dependency>
      <groupId>org.springframework.boot</groupId>
      <artifactId>spring-boot-starter-webmvc</artifactId>
    </dependency>
    <dependency>
      <groupId>org.springframework.boot</groupId>
      <artifactId>spring-boot-starter-actuator</artifactId>
    </dependency>
    <dependency>
      <groupId>io.micrometer</groupId>
      <artifactId>micrometer-registry-prometheus</artifactId>
    </dependency>
  </dependencies>
  <build>
    <plugins>
      <plugin>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-maven-plugin</artifactId>
      </plugin>
    </plugins>
  </build>
</project>
```

```java
// java/src/main/java/example/ResourceApi.java
package example;

import java.util.Map;
import io.micrometer.core.instrument.MeterRegistry;
import io.micrometer.core.instrument.Timer;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

@SpringBootApplication
@RestController
public class ResourceApi {
    private final Timer workTimer;

    public ResourceApi(MeterRegistry registry) {
        workTimer = Timer.builder("demo.work")
                .description("Synthetic work duration")
                .publishPercentileHistogram()
                .register(registry);
    }

    @GetMapping("/work")
    public Map<String, String> work() {
        return workTimer.record(() -> Map.of("status", "ok"));
    }

    public static void main(String[] args) {
        SpringApplication.run(ResourceApi.class, args);
    }
}
```

```yaml
# java/src/main/resources/application.yaml
spring:
  application:
    name: resource-api
management:
  endpoints:
    web:
      exposure:
        include: health,prometheus
  endpoint:
    health:
      show-details: never
      probes:
        enabled: true
  prometheus:
    metrics:
      export:
        enabled: true
  metrics:
    tags:
      application: ${spring.application.name}
    distribution:
      percentiles-histogram:
        http.server.requests: true
        jvm.gc.pause: true
      slo:
        http.server.requests: 10ms,50ms,100ms,500ms,1s
```

```bash
mvn -f java/pom.xml package
java -jar java/target/resource-api-1.0.0.jar
```

最小プロジェクトにラッパーファイルはありません。追加しないなら`mvn package`を使います。
イメージにはビルド済みjarを`/app/resource-api.jar`に置き、Java 21互換ランタイムを含める必要があります。
下の`registry.example.com`イメージは置換するプレースホルダーです。
名前空間作成、イメージビルド、レジストリアクセスは別の前提条件です。
readiness/livenessパスは実際のActuatorエンドポイントに一致します。

```yaml
# java-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: resource-java
  namespace: production
spec:
  replicas: 3
  selector:
    matchLabels:
      app: resource-java
  template:
    metadata:
      labels:
        app: resource-java
    spec:
      terminationGracePeriodSeconds: 30
      containers:
      - name: app
        image: registry.example.com/team/resource-java:1.0.0
        command:
        - java
        - -jar
        - /app/resource-api.jar
        env:
        - name: JAVA_TOOL_OPTIONS
          value: -XX:+UseContainerSupport -XX:MaxRAMPercentage=60.0 -XX:+UseG1GC -XX:+HeapDumpOnOutOfMemoryError
            -XX:HeapDumpPath=/diagnostics
        resources:
          requests:
            cpu: 500m
            memory: 1Gi
          limits:
            cpu: '2'
            memory: 2Gi
        ports:
        - name: http
          containerPort: 8080
        startupProbe:
          httpGet:
            path: /actuator/health/liveness
            port: http
          periodSeconds: 5
          failureThreshold: 30
        livenessProbe:
          httpGet:
            path: /actuator/health/liveness
            port: http
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /actuator/health/readiness
            port: http
          periodSeconds: 5
        volumeMounts:
        - name: diagnostics
          mountPath: /diagnostics
      volumes:
      - name: diagnostics
        emptyDir:
          sizeLimit: 3Gi
      topologySpreadConstraints:
      - maxSkew: 1
        topologyKey: topology.kubernetes.io/zone
        whenUnsatisfiable: ScheduleAnyway
        labelSelector:
          matchLabels:
            app: resource-java
```

Prometheus設定パスは`management.prometheus.metrics.export`です。
メトリクスや詳細ヘルス情報を無差別に公開しないでください。
`_bucket`クエリに対応するのはヒストグラム公開を行うメトリクスだけです。クライアント計算の
パーセンタイルをPod間で平均しても全体パーセンタイルにはなりません。
Micrometer Timerはすでにcount/sumを提供するため、同じ測定に重複Counterは不要です。

HeapDumpOnOutOfMemoryErrorはJVMのJava OOMEを扱います。カーネルSIGKILLではヒープダンプや
終了フックを実行できません。emptyDirの診断ファイルはPod削除で消えます。ファイル名衝突とディスク枯渇を扱ってください。
ヒープダンプは機密アプリケーションデータを含み得るため、アクセスと保持を制限します。
`ScheduleAnyway`は希望を表し、厳格なAZ分散ではありません。

### GCとCPU

| 選択肢 | 検証事項 |
|---|---|
| G1 | 一般的な出発点。停止時間目標は最大レイテンシー保証ではない |
| ZGC | JDK固有の世代別動作とCPU/メモリ予算 |
| Shenandoah | 選択したJDKディストリビューション/バージョンでの提供状況 |
| Parallel / Serial | スループットまたは小ヒープワークロード要件で比較 |

Java 21は`-XX:+UseZGC -XX:+ZGenerational`で世代別ZGCをサポートします。
Java 23では世代別がデフォルトとなり、Java 24は非世代別モードを削除して選択フラグを廃止扱いにしました。
Java 25の廃止警告と将来のフラグ削除を区別してください。Java 17へこのフラグをコピーしないでください。
現在の世代別専用JDKでは`-XX:+UseZGC`を使い、正確なバージョンで起動を確認します。
固定GCレイテンシー/スループット値にはベンチマークが必要です。

`availableProcessors()`が常にGCワーカー数ではありません。クォータ、アフィニティ、JDKバージョン、
コレクターの自動調整が関係します。GCスレッドを増やすと小さなCPUクォータをより早く使い切る場合があります。
起動が遅い場合はstartupProbeを使い、JIT/GC/CPU動作を測定します。

### JMXとJFR

JMX exporter 1.6.0 jarをイメージに含めるか公式成果物を取得し、チェックサムを確認します。
以下の設定は実際のメモリ、スレッド、GC MBeanでテストしました。
JMXとMicrometerはメトリクス名が異なるため、ダッシュボードで暗黙に混在させないでください。
GC CollectionTimeはミリ秒から秒へ変換します。

```yaml
# jmx-config.yaml
startDelaySeconds: 0
lowercaseOutputName: true
lowercaseOutputLabelNames: true
includeObjectNames:
  - "java.lang:type=Memory"
  - "java.lang:type=Threading"
  - "java.lang:type=GarbageCollector,name=*"
rules:
  - pattern: 'java.lang<type=Memory><HeapMemoryUsage>(used|committed|max)'
    name: demo_jmx_heap_$1_bytes
    type: GAUGE
  - pattern: 'java.lang<type=Threading><>ThreadCount'
    name: demo_jmx_threads
    type: GAUGE
  - pattern: 'java.lang<name=(.+), type=GarbageCollector><>CollectionCount'
    name: demo_jmx_gc_collections_total
    labels:
      gc: "$1"
    type: COUNTER
  - pattern: 'java.lang<name=(.+), type=GarbageCollector><>CollectionTime'
    name: demo_jmx_gc_collection_seconds_total
    valueFactor: 0.001
    labels:
      gc: "$1"
    type: COUNTER
```

```bash
java -javaagent:jmx_prometheus_javaagent-1.6.0.jar=127.0.0.1:9404:jmx-config.yaml   -jar java/target/resource-api-1.0.0.jar
```

このローカル診断コマンドはループバックにバインドします。他Podからの収集には明示的なメトリクスポート、
ServiceMonitor、アクセス制御が必要です。エージェントjarがなければJVMは起動できません。
NMTには起動時の`-XX:NativeMemoryTracking=summary`が必要です。すべての外部ネイティブライブラリ割り当てを
網羅する完全なRSS計測システムではありません。

実行中JFR収集にはJDKツール、適切な同一ユーザー権限、attach対応、書き込み可能な保存先が必要です。
PID 1と決めつけず、`PID`をJavaプロセスIDに置き換えます。

```bash
jcmd PID VM.native_memory summary
jcmd PID JFR.start name=profile settings=profile duration=60s filename=/diagnostics/profile.jfr
jfr summary /diagnostics/profile.jfr
```

コンテナからのコピーでは、選択コンテナと`kubectl cp`に必要な`tar`の有無を考慮します。
記録終了後にコピーしてください。プロセス/Pod置換後もヒープやJFRファイルが残る保証はありません。

## 4. Python: ワーカーとプロファイリング

ホストの`multiprocessing.cpu_count()`に`2 × CPU + 1`を適用すると、コンテナクォータを超過して
ワーカーを割り当てる場合があります。CPU/IO動作、GIL/ネイティブ拡張、ワーカーごとのRSS、同時リクエスト数を
テストします。CPUあたりワーカー数に普遍的な正解はありません。
このWSGI Flask例は実際に`WEB_CONCURRENCY`を読み、1ワーカーと2スレッドで開始します。

```text
# python/requirements.txt
Flask==3.1.3
gunicorn==26.2.0
```

```python
# python/app.py
from flask import Flask


def create_app():
    app = Flask(__name__)

    @app.get("/health/live")
    @app.get("/health/ready")
    def health():
        # Process-only health for this minimal example.
        return {"status": "ok"}

    return app
```

```python
# python/gunicorn.conf.py
import os


def positive_int(name, default):
    value = os.environ.get(name, str(default))
    if not value.isdecimal() or int(value) < 1:
        raise ValueError(f"{name} must be a positive integer")
    return int(value)


bind = os.environ.get("HTTP_BIND", "0.0.0.0:8000")
workers = positive_int("WEB_CONCURRENCY", 1)
threads = positive_int("GUNICORN_THREADS", 2)
worker_class = "gthread"  # WSGI Flask, not an ASGI worker.
control_socket_disable = True  # No local administration socket in this example.
preload_app = False
timeout = 30
graceful_timeout = 25
keepalive = 5
max_requests = 1000
max_requests_jitter = 100
accesslog = "-"
errorlog = "-"
loglevel = "info"
```

```bash
python -m venv .venv
.venv/bin/python -m pip install -r python/requirements.txt
WEB_CONCURRENCY=2 GUNICORN_THREADS=2   .venv/bin/python -m gunicorn --chdir python   --config python/gunicorn.conf.py 'app:create_app()'
```

これらのヘルスエンドポイントは例のプロセスだけを確認します。アプリケーションの依存関係の準備状態を実装してください。
削除されたFlaskの`before_first_request`フックを使わないでください。
Gunicorn 26のローカル管理制御ソケットは、この最小例では無効です。

WSGI FlaskとFastAPIなどのASGIアプリケーションを区別します。Gunicorn 26にもASGIワーカーがあります。
Uvicornを選ぶなら非推奨`uvicorn.workers`と別パッケージ`uvicorn-worker`を区別してください。
gthread設定をそのままASGIアプリに適用しないでください。
preloadのcopy-on-write効果は、fork前に初期化したスレッド/接続/クライアントと併せて評価します。
ワーカーの再生成はリークの根本修正ではありません。

tracemallocは追跡対象のPython割り当てを観測し、全ネイティブ/RSS使用量は観測しません。
以下は明示的なローカル診断であり、公開HTTPデバッグエンドポイントではありません。

```python
# python/profile_allocations.py
import tracemalloc


def profile_allocation_delta(workload):
    """Run an explicit local diagnostic; this is not an HTTP debug endpoint."""
    tracemalloc.start(10)
    try:
        before = tracemalloc.take_snapshot()
        result = workload()
        after = tracemalloc.take_snapshot()
        for statistic in after.compare_to(before, "lineno")[:10]:
            print(statistic)
        return result
    finally:
        tracemalloc.stop()


if __name__ == "__main__":
    profile_allocation_delta(lambda: [bytearray(1024) for _ in range(100)])
```

## 5. Node.js: old spaceとプロセスメモリ

`--max-old-space-size`の単位はMiBで、V8のold spaceを制御します。
RSS上限ではありません。若い世代、外部/Buffer、ネイティブメモリにも容量が必要です。
複数ワーカープロセスでは各プロセスのヒープを予算化します。
Node.js 20は2026年4月にEOLとなったため、新しい例は対応中のNode.js 24系列を使います。

この単一プロセス例はヘルスエンドポイント、メモリ観測、SIGTERM処理を実装します。
割合だけに基づく`global.gc()`の繰り返しは一般的な最適化ではありません。
テストしたNode 24はNODE_OPTIONS内の`--expose-gc`を受け入れますが、強制GCによる本番上の利点を示すものではありません。

```javascript
// node/server.cjs
const http = require('node:http');

const port = Number(process.env.PORT || 3000);
if (!Number.isInteger(port) || port < 1 || port > 65535) {
  throw new Error('PORT must be an integer between 1 and 65535');
}
let draining = false;
const server = http.createServer((req, res) => {
  if (!['/health/live', '/health/ready'].includes(req.url)) {
    res.writeHead(404).end();
    return;
  }
  const status = draining && req.url === '/health/ready' ? 503 : 200;
  res.writeHead(status, { 'Content-Type': 'application/json' });
  res.end(JSON.stringify({ status: status === 200 ? 'ok' : 'draining' }));
});
server.listen(port, process.env.HTTP_HOST || '0.0.0.0');

const monitor = setInterval(() => {
  const { rss, heapUsed, heapTotal, external, arrayBuffers } = process.memoryUsage();
  console.log(JSON.stringify({ rss, heapUsed, heapTotal, external, arrayBuffers }));
}, 30000);
monitor.unref();

function shutdown() {
  if (draining) return;
  draining = true;
  clearInterval(monitor);
  server.close(() => process.exit(0));
  setTimeout(() => {
    server.closeAllConnections();
    process.exit(1);
  }, 10000).unref();
}
process.on('SIGTERM', shutdown);
process.on('SIGINT', shutdown);
```

```bash
NODE_OPTIONS="--max-old-space-size=512" node node/server.cjs
```

`UV_THREADPOOL_SIZE`はファイルシステムI/O、一部DNS処理、暗号処理などlibuvスレッドプールを使う
操作に影響します。全ネットワークI/Oを対象にするわけではありません。
スレッド追加はスタックと同時操作のメモリを増やす場合があります。起動前に設定し、実ワークロードでテストします。

Node clusterを使う場合は`isPrimary`を優先し、ワーカー数を明示的に制限します。
`os.cpus().length`、PM2の`instances: max`、`availableParallelism()`を、全cgroupクォータの
正確な計算式と想定しないでください。再起動ループにはバックオフが必要で、終了中にワーカーを再作成してはいけません。
Podレプリカとプロセスレプリカを組み合わせると、ワーカー数とメモリ予算は掛け算になります。

## 6. GoとRust

### Go

Go 1.25はLinuxでcgroup対応のデフォルトGOMAXPROCSを導入しました。
`go.mod`の言語バージョンとGODEBUG互換デフォルトが関係します。このデフォルトには`go 1.25.0`以降を使います。
例はGo 1.27.1でテストしました。
環境でGOMAXPROCSを明示設定するか、正の`runtime.GOMAXPROCS(n)`を呼ぶと自動更新は無効になります。
`runtime.GOMAXPROCS(0)`での照会は変更しません。

現ランタイムはクォータを切り上げ、論理CPUとアフィニティも考慮します。
論理CPU/アフィニティ数が2を許す場合、通常2未満を選ばないため、`500m always means 1`は誤りです。
automaxprocsのバージョン/丸め動作をGo組み込みデフォルトと同一視したり、両方を無条件に有効にしたりしないでください。
CPU requestはクォータではありません。

```text
// go/go.mod
module example.com/resource-probe

go 1.25.0
```

```go
// go/main.go
package main

import (
	"encoding/json"
	"os"
	"runtime"
	"runtime/debug"
)

func main() {
	var memory runtime.MemStats
	runtime.ReadMemStats(&memory)
	// A negative value queries the current setting without changing it.
	limit := debug.SetMemoryLimit(-1)
	result := map[string]any{
		"gomaxprocs":           runtime.GOMAXPROCS(0),
		"goroutines":           runtime.NumGoroutine(),
		"go_managed_bytes":     memory.Sys - memory.HeapReleased,
		"go_soft_memory_limit": limit,
		"runtime_version":      runtime.Version(),
	}
	if err := json.NewEncoder(os.Stdout).Encode(result); err != nil {
		panic(err)
	}
}
```

```bash
go -C go build -o resource-probe .
GOMEMLIMIT=450MiB ./go/resource-probe
```

GOMEMLIMITはGoランタイム管理メモリ、おおよそ`MemStats.Sys - HeapReleased`のソフト上限です。
cgo、mmap、外部ライブラリを含むプロセス全体のRSS上限ではありません。
ランタイムはGC負荷を抑えるため上限を超える場合があります。
コンテナメモリの80–90%に設定してもOOM防止は保証されず、生存ヒープより大幅に下げると過剰GCを起こし得ます。
このプログラムは設定を報告するだけで、cgroupを読み取ったり変更したりしません。

### Rust

GCがないことは、メモリ使用量やレイテンシーが決定的であることを意味しません。
アロケーター動作、断片化、同時処理、バッファ、ブロッキング処理、OSスケジューリングを観察します。
jemallocなどへの変更は普遍的性能向上を想定せず、プロファイルとプラットフォーム対応から評価します。

この小さなTokioプログラムはランタイム設定を検証し、HTTPサーバーではありません。
明示的な`worker_threads()`は環境設定を上書きするため例では省略します。
ワーカースレッド数は`spawn_blocking`や外部ライブラリのスレッド上限ではありません。

```toml
# rust/Cargo.toml
[package]
name = "resource-probe"
version = "0.1.0"
edition = "2024"

[dependencies]
tokio = { version = "=1.53.1", features = ["rt-multi-thread", "time"] }
```

```rust
// rust/src/main.rs
use std::time::Duration;
use tokio::runtime::Builder;

fn main() -> Result<(), Box<dyn std::error::Error>> {
    // Without worker_threads(), Tokio can honor TOKIO_WORKER_THREADS.
    // This example rejects invalid values before building the runtime.
    if let Ok(value) = std::env::var("TOKIO_WORKER_THREADS") {
        let workers: usize = value.parse()?;
        if workers == 0 {
            return Err("TOKIO_WORKER_THREADS must be positive".into());
        }
    }
    let runtime = Builder::new_multi_thread()
        .enable_time()
        .build()?;
    println!("worker_threads={}", runtime.metrics().num_workers());
    runtime.block_on(async {
        tokio::time::sleep(Duration::from_millis(10)).await;
    });
    Ok(())
}
```

```bash
cargo build --manifest-path rust/Cargo.toml
TOKIO_WORKER_THREADS=2 ./rust/target/debug/resource-probe
```

lockfileがない新規プロジェクトでは`cargo build`を実行し、lockfileを確認してコミットします。
以後の再現可能ビルドは`--locked`を使えます。
CPU負荷の高いasyncタスクを無制限に作らず、上限付きキュー/同時実行数を使います。
比較可能なベンチマークなしに言語全体のメモリ/起動/速度ランキングを公開しないでください。

## 7. PromQLとアラート

ルールはkube-prometheus-stackの`job="kubelet"`、`metrics_path="/metrics/cadvisor"`、
集約`cpu="total"`系列とkube-state-metricsを前提とします。
CPUごとの収集に集約を合わせ、セレクターを実際のラベル契約に合わせます。

例は重複スクレイプ観測を合計しないよう、コンテナごとのmax集約を使います。
同じPod/コンテナ名で複数ランタイムIDが重なる再起動期間を調べてください。
これらの観測は正確なCPU課金データではありません。
複数クラスターには収集/remote-write経路に実際の`cluster`ラベルが必要で、
PromQLは欠けたクラスターIDを生成しません。

順序付きルールはrequest/limitの分母を合わせ、ゼロを除外します。
ワーキングセットは正確なOOM予測値ではありません。ページキャッシュとメモリ回収動作を調査します。
最終終了理由はゲージなので、`increase(reason)`はOOM数ではありません。
OOMアラートは最近の再起動と最後に記録されたOOM理由を組み合わせ、期間内の全OOMを数えるものではありません。

```yaml
# resource-rules.yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: resource-review
  namespace: observability
  labels:
    release: prometheus
spec:
  groups:
  - name: resource-review
    interval: 1m
    rules:
    - record: resource:cpu_cores:rate5m
      expr: max by (cluster, namespace, pod, container) (rate(container_cpu_usage_seconds_total{job="kubelet",metrics_path="/metrics/cadvisor",container!="",container!="POD",pod!="",cpu="total"}[5m]))
    - record: resource:cpu_requests:cores
      expr: max by (cluster, namespace, pod, container) (kube_pod_container_resource_requests{resource="cpu",unit="core"})
    - record: resource:memory_working_set:bytes
      expr: max by (cluster, namespace, pod, container) (container_memory_working_set_bytes{job="kubelet",metrics_path="/metrics/cadvisor",container!="",container!="POD",pod!=""})
    - record: resource:memory_limit:bytes
      expr: max by (cluster, namespace, pod, container) (kube_pod_container_resource_limits{resource="memory",unit="byte"})
    - record: resource:cpu_request_ratio
      expr: resource:cpu_cores:rate5m / (resource:cpu_requests:cores > 0)
    - record: resource:memory_limit_ratio
      expr: resource:memory_working_set:bytes / (resource:memory_limit:bytes > 0)
    - record: resource:cfs_throttled:rate5m
      expr: max by (cluster, namespace, pod, container) (rate(container_cpu_cfs_throttled_periods_total{job="kubelet",metrics_path="/metrics/cadvisor",container!="",container!="POD",pod!=""}[5m]))
    - record: resource:cfs_periods:rate5m
      expr: max by (cluster, namespace, pod, container) (rate(container_cpu_cfs_periods_total{job="kubelet",metrics_path="/metrics/cadvisor",container!="",container!="POD",pod!=""}[5m]))
    - record: resource:cfs_throttled_period_ratio
      expr: resource:cfs_throttled:rate5m / (resource:cfs_periods:rate5m > 0)
    - record: resource:recent_restart_last_oom
      expr: (max by (cluster, namespace, pod, container) (increase(kube_pod_container_status_restarts_total[5m]))
        > 0) and on (cluster, namespace, pod, container) (max by (cluster, namespace,
        pod, container) (kube_pod_container_status_last_terminated_reason{reason="OOMKilled"})
        == 1)
    - record: cluster:pending_pods:count
      expr: sum by (cluster) (max by (cluster, namespace, pod) (kube_pod_status_phase{phase="Pending"}))
    - record: node:pods:count
      expr: count by (cluster, node) (max by (cluster, node, namespace, pod) (kube_pod_info{node!=""}))
    - alert: HighCPUThrottledPeriodRatio
      expr: resource:cfs_throttled_period_ratio > 0.25
      for: 10m
      labels:
        severity: warning
      annotations:
        summary: HighCPUThrottledPeriodRatio
        description: A high fraction of quota periods were throttled; correlate with
          latency and throughput.
    - alert: MemoryWorkingSetNearLimit
      expr: resource:memory_limit_ratio > 0.9
      for: 5m
      labels:
        severity: warning
      annotations:
        summary: MemoryWorkingSetNearLimit
        description: Working set is near the configured limit; this is not an exact
          OOM prediction.
    - alert: RecentRestartWithLastReasonOOM
      expr: resource:recent_restart_last_oom > 0
      for: 0m
      labels:
        severity: warning
      annotations:
        summary: RecentRestartWithLastReasonOOM
        description: A recent restart has OOMKilled as its last recorded reason; inspect
          termination state.
```

`release: prometheus`と`observability`名前空間をPrometheusのルールセレクターに合わせます。
しきい値は例です。スロットリング期間率が高くても、直ちにlimitを増やすべきとは限りません。
レイテンシー、スループット、同時実行数、ノード競合と関連付けます。

`cluster:pending_pods:count`は0/1フェーズゲージを合計します。
`count(kube_pod_status_phase{phase="Pending"})`はゼロ値サンプルも数えます。
Pendingにはスケジュール済みでイメージ/ストレージ待ちのPodも含まれるため、リソース不足と同義ではありません。
`node:pods:count`はすでにノードごとの数なので、クラスターのノード数で割らないでください。

Deployment集約は、Pod名の正規表現から所有権を推測せず、kube-state-metricsの
Pod→ReplicaSet→Deployment所有関係か検証済み記録ルールを使います。
長期サイジングではロールアウト、休日、待機容量、SLOを評価します。観測使用量の低さは自動退避ポリシーではありません。

### JVMクエリとダッシュボード

クエリは上のMicrometer設定を使うJVMが対象です。
Prometheusのinstanceラベルでプロセスを区別し、実スクレイプのメトリクス名を確認します。

```promql
sum by (instance, application) (jvm_memory_used_bytes{area="heap"})
/
sum by (instance, application) (jvm_memory_max_bytes{area="heap"} > 0)
```

```promql
histogram_quantile(0.99,
  sum by (le, instance, application) (rate(jvm_gc_pause_seconds_bucket[5m]))
)
```

```promql
sum by (instance, application) (rate(jvm_gc_pause_seconds_sum[5m]))
```

```promql
rate(jvm_classes_loaded_count_classes_total[5m])
```

`jvm_gc_pause_seconds_sum`のrateは、実経過時間1秒あたりの観測停止秒数です。
プロセスCPUで割っても有効なGC CPU割合にはならず、並行GC処理のすべても捉えません。
`jvm_classes_loaded_classes`は現在ロードされたクラスのゲージで、テストしたMicrometerの累積カウンターは
`jvm_classes_loaded_count_classes_total`です。JDK/ライブラリ変更時は実際の公開データを確認します。

[前章](./09-observability-stack.md)の明示的データソースUIDとダッシュボードプロビジョニングを使います。
比率はpercentunitで表示するか、100倍してpercentを使います。
生の使用率ゲージをヒートマップのヒストグラムバケットとして扱わないでください。
部分パネルJSON断片を完全なインポート可能ダッシュボードと説明しないでください。

## 8. EKS Auto Modeと予備容量

requests、実際のNode allocatable、DaemonSet/システム負荷、Podオーバーヘッド、ポート、ボリューム、
トポロジー、Taintを考慮します。4 vCPUインスタンスがアプリケーションrequest用に4 CPUを割り当て可能とは限りません。
大きいインスタンスが常に効率的でも、小さいものが常に安価でもありません。
障害影響、可用性、料金、断片化を評価します。

Auto Mode NodePoolは`karpenter.sh/v1`、NodeClassグループは`eks.amazonaws.com`です。
例は既存Auto Modeの`default` NodeClassを参照します。
NodeClass、サブネット、IAMロール、リージョンでのインスタンス提供状況を別途検証します。

```yaml
# auto-nodepool.yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: resource-demo
spec:
  template:
    spec:
      nodeClassRef:
        group: eks.amazonaws.com
        kind: NodeClass
        name: default
      requirements:
      - key: node.kubernetes.io/instance-type
        operator: In
        values:
        - m7i.large
        - m7i.xlarge
        - m7i.2xlarge
      - key: karpenter.sh/capacity-type
        operator: In
        values:
        - on-demand
  disruption:
    consolidationPolicy: WhenEmptyOrUnderutilized
    consolidateAfter: 5m
```

統合はrequests、スケジューリング可能性、価格、中断制約を考慮します。
CPU観測値30%未満でもノード統合は保証されません。
PDBは全終了を防がず、強制終了時の無中断も保証しません。
requestが変わらなければ、通常スケジューラーが大きすぎるlimitを自動予約するわけではありません。

プレースホルダーPodは高優先度作業向けの予備容量確保を促せます。
優先度-1はデフォルト0より低いだけで、最小の優先度ではありません。
`preemptionPolicy: Never`はプレースホルダーが他をプリエンプトするのを止め、プレースホルダー自身が
プリエンプトされることは防ぎません。EC2 Capacity Reservationでも可用性保証でもなく、
トポロジー、Taint、リソース構成が実ワークロードに合う必要があります。

```yaml
# capacity-buffer.yaml
apiVersion: scheduling.k8s.io/v1
kind: PriorityClass
metadata:
  name: capacity-buffer
value: -1
preemptionPolicy: Never
globalDefault: false
description: Lower priority placeholder capacity; not a reservation guarantee.
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: capacity-buffer
  namespace: production
spec:
  replicas: 2
  selector:
    matchLabels:
      app: capacity-buffer
  template:
    metadata:
      labels:
        app: capacity-buffer
    spec:
      priorityClassName: capacity-buffer
      containers:
      - name: pause
        image: registry.k8s.io/pause:3.10.2
        resources:
          requests:
            cpu: '2'
            memory: 4Gi
```

## ロールアウト順序と検証の限界

1. 代表的負荷でレイテンシー、スループット、クォータ動作、総メモリ、再起動原因を測定します。
2. HPAとランタイム同時実行数を併せて考え、VPAと観測からrequestsを提案します。
3. limitsと余裕容量を調整する前に、本番外で起動、ピーク負荷、障害、再起動をテストします。
4. カナリア中にSLO、費用、配置、中断を観察し、ロールバックに必要な設定を保持します。

検証ではJava/Spring/JMXメトリクスとJFR/NMT、Gunicorn/NodeのヘルスとSIGTERM動作、
Goランタイム報告とTokioワーカー設定をローカルで実行しました。
PromQL計算ケースは重複スクレイプ、複数クラスター、ゼロ分母、過去OOM状態、Pendingの0/1ゲージを扱いました。
EKSデプロイ、cgroupクォータ変更、強制OOM、性能ベンチマークは行っていません。

## 公式参考資料

- [Kubernetesリソース](https://kubernetes.io/docs/concepts/configuration/manage-resources-containers/)
- [ノード圧力による退避](https://kubernetes.io/docs/concepts/scheduling-eviction/node-pressure-eviction/)
- [Goのコンテナ対応GOMAXPROCS](https://go.dev/blog/container-aware-gomaxprocs)
- [Go GCガイド](https://go.dev/doc/gc-guide)
- [Java 21オプション](https://docs.oracle.com/en/java/javase/21/docs/specs/man/java.html)
- [JEP 474](https://openjdk.org/jeps/474)
- [JEP 490](https://openjdk.org/jeps/490)
- [Spring Bootプロパティ](https://docs.spring.io/spring-boot/appendix/application-properties/index.html)
- [JMX exporter 1.6.0](https://github.com/prometheus/jmx_exporter/releases/tag/1.6.0)
- [Gunicorn設定](https://gunicorn.org/reference/settings/)
- [Flask変更履歴](https://flask.palletsprojects.com/en/stable/changes/)
- [Node.js 24 CLI](https://nodejs.org/download/release/v24.21.0/docs/api/cli.html)
- [Tokioランタイムビルダー](https://docs.rs/tokio/1.53.1/tokio/runtime/struct.Builder.html)

---

< [前: 可観測性スタック](./09-observability-stack.md) | [目次](./README.md) | [次: EKSアップグレード](./11-upgrade-operations.md) >
