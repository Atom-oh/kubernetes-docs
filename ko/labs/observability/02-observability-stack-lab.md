# Part 2: Observability 스택 배포

<span id="_2-2-1-kube-prometheus-stack-prometheus-alertmanager-grafana"></span>
<span id="_2-2-2-victoriametrics"></span>
<span id="_2-2-3-mimir"></span>
<span id="_2-2-4-cloudwatch-metrics-adot"></span>
<span id="_2-3-1-loki-simplescalable-mode"></span>
<span id="_2-3-2-clickhouse"></span>
<span id="_2-3-3-opensearch-fluentbit"></span>
<span id="_2-3-4-cloudwatch-logs-fluentbit"></span>
<span id="_2-4-1-tempo"></span>
<span id="_2-4-2-x-ray-otel-collector-exporter"></span>
<span id="_2-5-1-grafana-datasource-provisioning"></span>
<span id="_2-5-2-amazon-managed-grafana-설정"></span>
<span id="_2-5-3-exemplar-설정"></span>
<span id="_2-6-1-alertmanager-sns-receiver"></span>
<span id="_2-6-2-grafana-oncall-설치"></span>
<span id="_2-6-3-cloudwatch-alarms"></span>
<span id="grafana-explore-테스트"></span>
<span id="observability-스택-상태-확인"></span>
<span id="otel-collector-아키텍처"></span>
<span id="step-2-1-opentelemetry-collector-배포"></span>
<span id="step-2-2-metrics-스택-배포"></span>
<span id="step-2-3-logging-스택-배포"></span>
<span id="step-2-4-tracing-스택-배포"></span>
<span id="step-2-5-visualization-구성"></span>
<span id="step-2-6-alerting-기본-구성"></span>
<span id="검증-verification"></span>
<span id="다음-단계"></span>
<span id="아키텍처-개요"></span>
<span id="예상-결과"></span>
<span id="참조-문서"></span>
<span id="학습-목표"></span>

> **난이도**: 고급
> **마지막 업데이트**: 2026년 9월 13일
서비스 클러스터의 애플리케이션에서 관리 클러스터의 조회 화면까지 metrics·logs·traces를 연결합니다. [stack 실행 예제](https://github.com/Atom-oh/kubernetes-docs/tree/main/examples/labs/observability/stack)의 고정 차트·TLS·identity 파일을 사용합니다. [Part 1](./01-infrastructure-setup-lab.md)의 cluster context, gp3/EBS CSI, LBC, DNS/route, IRSA 및 `helm-inputs/collector-identity.yaml`이 선행 조건입니다.

![실제로 연결된 metrics·logs·traces 경로](../../.gitbook/assets/ko-labs-observability-02-observability-stack-lab-0.png)

[🔍 인터랙티브 다이어그램 보기](https://www.atomai.click/kubernetes-docs/archmaps/ko-labs-observability-02-observability-stack-lab-0.html)

## 1. 고정 버전과 기본 경로 {#baseline}

| Component | Chart | Application |
|---|---|---|
| kube-prometheus-stack | 90.0.0 | Operator0.93.1; inspect component images |
| Tempo | 3.0.0 | 3.0.3 |
| Loki | 18.13.0 | 3.7.7 |
| OTel Collector | 0.173.1 | contrib0.160.0 |

metrics는 서비스 Prometheus가 scrape한 뒤 mTLS remote-write로 관리 Prometheus에 보냅니다. Collector는 CRI/JSON 로그와 OTLP trace를 받아 인증된 관리 endpoint로 전달합니다. 관리 Collector는 Loki/Tempo에 전달하며, CloudWatch addon은 AIOps가 읽는 구조화 로그를 보냅니다. Grafana UID는 `prometheus`, `loki`, `tempo`로 일치시킵니다.

각 backend는 실습용 단일 durable instance입니다. 이를 HA나 측정된 수용량이라고 설명하지 않습니다. Prometheus 2일, Loki/Tempo 24시간 보존은 30일 SLO 증거가 아닙니다.

## 2. 비공개 TLS·네트워크 입력 {#tls-network}

```bash
cd examples/labs/observability/stack
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python prepare_tls.py   --collector-dns "$COLLECTOR_DNS" --prometheus-dns "$PROMETHEUS_DNS"   --output-directory "$LAB_STATE/tls"
.venv/bin/python render_network.py --service-source-cidr "$SERVICE_SOURCE_CIDR"   --nlb-security-group "$NLB_SECURITY_GROUP"   --nlb-source-cidr "$NLB_SUBNET_CIDR_A" --nlb-source-cidr "$NLB_SUBNET_CIDR_B"   --output-directory "$LAB_STATE/network"
```
7일 실습용 CA와 server/client 용도를 구분한 인증서를 생성합니다. CA 개인키는 cluster Secret에 들어가지 않습니다. 기존 조직 PKI를 사용한다면 동일한 Secret key·SAN·EKU를 제공해야 합니다. helper는 실제 DNS·route·SG를 만들지 않습니다. source CIDR과 NLB health-check subnet CIDR을 실제 값으로 입력합니다.

```bash
kubectl --context managed create namespace monitoring --dry-run=client -o yaml | kubectl --context managed apply -f -
kubectl --context service create namespace monitoring --dry-run=client -o yaml | kubectl --context service apply -f -
kubectl --context service create namespace observability --dry-run=client -o yaml | kubectl --context service apply -f -
kubectl --context managed apply -f "$LAB_STATE/tls/management-secrets.yaml"
kubectl --context service apply -f "$LAB_STATE/tls/service-monitoring-secrets.yaml"
kubectl --context service apply -f "$LAB_STATE/tls/service-observability-secrets.yaml"
```

## 3. 관리 backend 설치 {#management}

```bash
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo add grafana-community https://grafana-community.github.io/helm-charts
helm repo add open-telemetry https://open-telemetry.github.io/opentelemetry-helm-charts
kubectl --context managed apply -f prometheus-probe.yaml
helm upgrade --install lab-monitoring prometheus-community/kube-prometheus-stack   --version 90.0.0 --kube-context managed -n monitoring -f monitoring-management-values.yaml
helm upgrade --install lab-loki grafana-community/loki --version 18.13.0   --kube-context managed -n monitoring -f loki-values.yaml
helm upgrade --install lab-tempo grafana-community/tempo --version 3.0.0   --kube-context managed -n monitoring -f tempo-values.yaml
```
Prometheus web가 mTLS를 요구하므로 기본 kubelet HTTPS probe는 인증서를 제공하지 못합니다. `promtool check ready/healthy --http.config.file=...` exec probe와 client Secret을 사용하며 Operator의 probe merge도 검증했습니다. Grafana와 Tempo metrics-generator 역시 mTLS client 인증서를 사용합니다.

Loki는 Monolithic·TSDB/v13·filesystem PVC입니다. Tempo3는 live-store/backend scheduler/worker를 사용합니다. Tempo2의 ingester/compactor 설정을 섞지 않습니다. Grafana replicas1·PVC·private admin Secret을 사용하며 알려진 공통 비밀번호를 배포하지 않습니다. Grafana는 사용하지 않는 dashboard sidecar·API token·RBAC를 비활성화하고, 데이터 소스 파일은 지정된 Secret에서 마운트합니다.

## 4. Collector·endpoint·서비스 수집 {#collectors}

```bash
helm upgrade --install lab-collector open-telemetry/opentelemetry-collector   --version 0.173.1 --kube-context managed -n monitoring   -f collector-management-values.yaml -f collector-cloudwatch-values.yaml   -f "$LAB_STATE/helm-inputs/collector-identity.yaml"
kubectl --context managed apply -f backend-network-policies.yaml
kubectl --context managed apply -f "$LAB_STATE/network/endpoints.yaml"
kubectl --context managed -n monitoring get svc lab-collector-ingest lab-prometheus-ingest
```
실제 internal NLB hostname으로 private DNS를 연결하고 서비스 Pod에서 route·SG/NACL·client IP 처리를 확인한 뒤 진행합니다. 다른 클러스터의 `.svc.cluster.local` 이름을 사용하지 않습니다. TLS는 NLB가 아니라 Collector/Prometheus에서 종료해 client 인증을 유지합니다.

```bash
helm upgrade --install lab-service-monitoring prometheus-community/kube-prometheus-stack   --version 90.0.0 --kube-context service -n monitoring   -f monitoring-service-values.yaml -f "$LAB_STATE/tls/prometheus-endpoint-values.yaml"
helm upgrade --install lab-agent open-telemetry/opentelemetry-collector   --version 0.173.1 --kube-context service -n observability   -f collector-service-values.yaml -f "$LAB_STATE/tls/collector-endpoint-values.yaml"
```
서비스 DaemonSet은 msa Pod 로그를 읽기 전용 mount로 읽습니다. node log 접근을 위한 root UID·capability drop·no privilege escalation을 명시했으므로 해당 namespace admission 정책에서 이 수집기만 허용해야 합니다. CRI parser 다음 JSON parser를 적용하고, 원래 cluster에서 k8s metadata를 붙입니다. 관리 Collector가 다른 cluster의 Pod를 조회할 수 있다고 가정하지 않습니다.

이 실습은 file offset/exporter queue를 영속화하지 않습니다. 재시작/장애 중 유실·중복 가능성을 기록하고 운영용 durable buffering은 별도로 설계합니다. CloudWatch `raw_log: true`로 service/level/trace_id를 유지하며 실제 IRSA 교환·Logs 권한을 확인합니다.

## 5. 실제 데이터 확인과 확장 {#verify-extend}

```bash
kubectl --context managed -n monitoring get pods,pvc
kubectl --context service -n observability get pods
kubectl --context managed -n monitoring port-forward svc/lab-grafana 3000:80
```
private admin Secret으로 로그인합니다. Part3 앱 배포 후 실제 target scrape, exporter 오류, CloudWatch JSON 필드, Tempo trace ID, Loki trace_id, exemplar를 대조합니다. datasource가 존재하거나 Grafana 옵션이 켜진 것만으로 데이터 도착을 증명하지 않습니다.

VictoriaMetrics/Mimir/AMP, ClickHouse/OpenSearch, X-Ray, AMG, MWAA는 선택 확장입니다. 각각의 [metrics](../../observability/metrics/README.md)·[logging](../../observability/logging/README.md)·[tracing](../../observability/tracing/README.md) 가이드에서 인증·저장·전송·비용을 검증하고 추가합니다. 기본 실습이 이들 모두를 동시에 배포했다고 표시하지 않습니다. [Part3](./03-msa-deployment-lab.md)로 진행합니다.

## 검증 범위

차트/CRD/native config, 실제 local Collector mTLS·CRI/JSON forwarding, Prometheus mTLS probe, synthetic PKI, NetworkPolicy schema를 검증했습니다. 실제 EKS/LBC/DNS·NetworkPolicy enforcement·IRSA·Grafana live datasource는 실행하지 않았습니다.

DaemonSet 프로필은 `lab-agent.observability.svc.cluster.local:4318` Service를 명시적으로 생성합니다. 기본 `internalTrafficPolicy: Local`에서는 앱이 있는 노드에 준비된 Collector Pod가 있어야 하므로 taint·toleration과 DaemonSet ready 상태를 확인합니다.
