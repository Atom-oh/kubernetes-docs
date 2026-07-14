# Observability Lab パート2: Observability Stack クイズ

> **最終更新**: February 22, 2026

Observability End-to-End Lab Part 2で扱ったobservability stackの概念について、理解度を確認しましょう。

---

1. OpenTelemetry CollectorのDaemonSetおよびGatewayデプロイパターンの主な違いは何ですか？
   - A) DaemonSetパターンは非推奨であり、Gatewayのみが推奨されるアプローチである
   - B) DaemonSetはローカル収集のために各Node上でCollectorを実行し、GatewayはNode間処理のために収集を一元化する
   - C) Gatewayパターンはmetricsを処理できず、tracesのみを処理できる
   - D) DaemonSetパターンはcluster間でより多くのnetwork bandwidthを必要とする

<details>
<summary>回答を表示</summary>

**回答: B) DaemonSetはローカル収集のために各Node上でCollectorを実行し、GatewayはNode間処理のために収集を一元化する**

**解説:**
DaemonSetパターンでは、すべてのNodeにOTel Collector Podをデプロイし、低レイテンシでtelemetryをローカル収集するとともに、network hopを削減します。Gatewayパターンでは、すべてのsourceからtelemetryを受信する中央集約型のDeploymentまたはStatefulSetを使用するため、tail-based samplingのようなNode間処理が可能になります。多くの場合、両方のパターンを組み合わせます。DaemonSet Collectorがローカルデータを収集してGatewayに転送し、Gatewayが集約してbackendにexportします。

</details>

---

2. OpenTelemetry Collectorのpipeline architectureは、データフローをどのように構成しますか？
   - A) Exporter → Processor → Receiver
   - B) Receiver → Processor → Exporter
   - C) Processor → Receiver → Exporter
   - D) すべてのcomponentは順序付けされずに並列で実行される

<details>
<summary>回答を表示</summary>

**回答: B) Receiver → Processor → Exporter**

**解説:**
OTel Collector pipelineは明確なデータフローに従います。Receiverはさまざまなsource（OTLP、Prometheus、Jaegerなど）からtelemetryデータを取り込み、Processorはデータの変換、filtering、enrichmentを行います（batching、attribute manipulation、sampling）。Exporterは処理済みのデータをbackend（Prometheus、Jaeger、cloud services）へ送信します。異なるsignal type（metrics、traces、logs）向けに複数のpipelineを定義でき、それらのpipelineでcomponentを共有できます。

</details>

---

3. Prometheus remote writeをAmazon Managed Prometheus（AMP）に設定する際、authenticationはどのように機能しますか？
   - A) Kubernetes secretsに保存されたusernameとpassword
   - B) IRSAがIAM credentialsを提供し、SigV4 extensionがAWS Signature Version 4でrequestに署名する
   - C) AMP consoleで生成されたAPI keys
   - D) AWS Certificate Managerが発行したmTLS certificates

<details>
<summary>回答を表示</summary>

**回答: B) IRSAがIAM credentialsを提供し、SigV4 extensionがAWS Signature Version 4でrequestに署名する**

**解説:**
AMPはauthenticationにAWS IAMを使用します。remote write component（Prometheus、OTel Collector、またはGrafana Agent）は、IRSAを使用して一時的なIAM credentialsを取得します。SigV4（AWS Signature Version 4）extensionまたはproxyは、これらのcredentialsで各requestに署名します。このアプローチではAWSのidentity infrastructureを活用するため、長期間有効なcredentialsを管理する必要がなく、CloudTrailを通じたaudit trailを提供できます。

</details>

---

4. VictoriaMetricsはPrometheusとどのように互換性がありますか？
   - A) Prometheusデータをimportするためにdata migration toolsが必要である
   - B) Prometheus remote write/read APIを実装し、queryにはPromQLをサポートする
   - C) Prometheus sidecarとしてのみ機能する
   - D) 互換性には有償enterprise licenseが必要である

<details>
<summary>回答を表示</summary>

**回答: B) Prometheus remote write/read APIを実装し、queryにはPromQLをサポートする**

**解説:**
VictoriaMetricsは、Prometheus storageのdrop-in replacementとして設計されています。Prometheus remote writeおよびremote read APIを実装しているため、Prometheus互換clientはmetricsを送信でき、PromQL互換toolはそれらをqueryできます。追加機能のためにPromQLをMetricsQLで拡張しています。この互換性により、既存のGrafana dashboards、alerting rules、recording rulesは変更せずに動作します。

</details>

---

5. Grafana Mimirのsingle binary modeの特徴は何ですか？
   - A) single-tenant deploymentsのみをサポートする
   - B) デプロイを簡素化するため、すべてのMimir components（ingester、querier、compactorなど）が単一のprocessで実行される
   - C) 水平方向にscaleできない
   - D) single binary modeではlong-term storageが無効になる

<details>
<summary>回答を表示</summary>

**回答: B) デプロイを簡素化するため、すべてのMimir components（ingester、querier、compactorなど）が単一のprocessで実行される**

**解説:**
Mimirのsingle binary mode（monolithic mode）では、distributor、ingester、querier、query-frontend、compactor、store-gateway、rulerのすべてのcomponentを単一のprocessで実行します。これにより、小規模なenvironmentにおけるdeploymentとoperationsが簡素化されます。1つのprocessで実行されますが、複数のreplicaを実行することで水平方向にscaleできます。より大規模なdeploymentでは、componentをmicroservices modeに分離して独立してscaleできます。

</details>

---

6. Grafana LokiのSimpleScalable deployment modeに含まれるcomponentは何ですか？
   - A) 単一のread-write Podのみ
   - B) 独立してscaleできる、分離されたread、write、backend component
   - C) ingesterとquerierのみで、外部compactorを使用する
   - D) automatic shardingを備えたmonolithic mode

<details>
<summary>回答を表示</summary>

**回答: B) 独立してscaleできる、分離されたread、write、backend component**

**解説:**
LokiのSimpleScalable mode（Simple Scalable DeploymentまたはSSDとも呼ばれる）は、componentを3つのtarget、すなわちWrite（distributor、ingester）、Read（query-frontend、querier）、Backend（compactor、index-gateway、ruler）に分割します。これにより、独立したscalingが可能になります。write pathはingestion volumeに応じてscaleし、read pathはquery loadに応じてscaleします。これはmonolithic（single binary）modeとmicroservices（fully distributed）modeの中間に位置し、operational simplicityとscalabilityのバランスを取るものです。

</details>

---

7. 従来のsolutionと比べて、log storeとしてClickHouseを使用する利点は何ですか？
   - A) ClickHouseはstructured JSON logsのみをサポートする
   - B) column-oriented storage、高いcompression、そして大量のlog volumeに対する高速なanalytical queries
   - C) 必要なstorageは少ないが、query performanceは遅い
   - D) ClickHouseはlogsではなく、主にmetrics向けに設計されている

<details>
<summary>回答を表示</summary>

**回答: B) column-oriented storage、高いcompression、そして大量のlog volumeに対する高速なanalytical queries**

**解説:**
ClickHouseは、analytical queriesに最適化されたcolumn-oriented OLAP databaseです。log storageにおいては、次のことを意味します。column内の類似データがよく圧縮されることによる優れたcompression ratio（多くの場合、row-based storesより10x高い）、数十億件のlog entryを横断する非常に高速なaggregation queries、そして行全体を読み取らずに特定のcolumnを効率的にfilteringできることです。これらの特性により、interactive query performanceを備えたhigh-volume log storageにおいてcost-effectiveになります。

</details>

---

8. log collectionにおけるFluentBitとGrafana Alloyの主な違いは何ですか？
   - A) FluentBitはGoで書かれ、AlloyはCで書かれている
   - B) FluentBitはlightweightでlog forwardingに重点を置く一方、Alloyはmetrics、logs、traces、profilesをサポートする統合telemetry collectorである
   - C) AlloyはGrafana backendsのみをサポートする一方、FluentBitはvendor-agnosticである
   - D) 同等のworkloadでは、FluentBitはAlloyより多くのmemoryを必要とする

<details>
<summary>回答を表示</summary>

**回答: B) FluentBitはlightweightでlog forwardingに重点を置く一方、Alloyはmetrics、logs、traces、profilesをサポートする統合telemetry collectorである**

**解説:**
FluentBitはCで書かれたlightweightでhigh-performanceなlog processorおよびforwarderであり、resource-constrained environments向けに設計されています。Grafana Alloy（Grafana Agentのevolution）は、metrics、logs、traces、profilesというすべてのtelemetry signalsを処理する統合observability collectorです。Alloyはcomponent-based configuration modelを使用し、Grafana ecosystemと緊密に統合されます。最小限のfootprintでlog forwardingを行う場合はFluentBitを、すべてのsignal typeにわたる統合collectionを行う場合はAlloyを選択します。

</details>

---

9. Tempo-Loki TraceID derived field correlationをどのように設定しますか？
   - A) correlationは自動的に行われ、設定は不要である
   - B) Loki data sourceに、logsからTraceIDを抽出しtrace IDを使用してTempoへlinkするderived fieldを設定する
   - C) TempoとLokiの間に別個のcorrelation serviceをinstallする
   - D) TraceID correlationはJaegerでのみ機能し、Tempoでは機能しない

<details>
<summary>回答を表示</summary>

**回答: B) Loki data sourceに、logsからTraceIDを抽出しtrace IDを使用してTempoへlinkするderived fieldを設定する**

**解説:**
GrafanaのLoki data source settingsで、regexを使用してlog linesからtrace IDsを抽出するderived fieldsを設定します。derived fieldは、抽出したtrace IDをvariableとして使用するTempo data sourceへのinternal linkを指定します。logsを表示すると、trace IDsを含むlog linesの横にclickable linksが表示され、log entryからTempo内の対応するdistributed traceへ直接navigationできます。

</details>

---

10. Alertmanagerを設定してAWS SNSへnotificationsを送信するにはどうすればよいですか？
    - A) Alertmanagerはnative SNS supportを備えており、topic ARNのみが必要である
    - B) topic ARN、region、IRSAまたはaccess keysを介したIAM authenticationを使用してSNS receiverを設定する
    - C) SNS integrationにはwebhook proxy serviceが必要である
    - D) AlertmanagerはSNSへ送信できない。代わりにCloudWatch Alarmsを使用する

<details>
<summary>回答を表示</summary>

**回答: B) topic ARN、region、IRSAまたはaccess keysを介したIAM authenticationを使用してSNS receiverを設定する**

**解説:**
AlertmanagerはSNSをnative receiver typeとしてサポートしています。設定にはSNS topic ARN、AWS region、authentication credentialsが必要です。EKS deploymentsでは、`sns:Publish` permissionを持つIAM roleでservice accountを設定してIRSAを使用します。receiver configurationには、AWS authentication用の`sigv4` settingsが含まれます。これによりSNSへ直接alert deliveryでき、SNSはその後email、SMS、Lambda、SQS、またはその他のSNS subscribersへfan outできます。

</details>
