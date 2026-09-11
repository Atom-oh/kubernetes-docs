# ClickHouse on EKS 실측 벤치마크

> **기존 측정 환경**: ClickHouse 24.8 (측정 당시 버전 — 24.x 계열은 현재 지원 종료, 테스트 환경의 버전 안내 참고), Kubernetes 1.36 (Amazon EKS)
> **마지막 업데이트**: 2026년 9월 11일

"ClickHouse는 빠르다"는 말은 벤치마크 보고서마다 나오지만, **EKS의 평범한 노드 하나와 기본 gp3 볼륨**에서 어느 정도인지 직접 잰 숫자는 찾기 어렵습니다. 이 문서는 4 vCPU 노드 + 기본 설정 gp3 100 GiB라는 의도적으로 소박한 환경에 Kubernetes 로그 1억 행을 넣고 측정한 결과입니다. 수치는 기존 실행의 보고값입니다. 원시 query_log와 당시의 모든 쿼리·캐시 상태가 이 문서에 포함된 것은 아니므로 동일한 숫자의 재현을 보장하지 않습니다. 아래 새 실행 예제에서는 실제 SQL·설정·버전·원시 결과를 함께 보관합니다.

![numbers_mt 생성기에서 MergeTree 테이블로의 ingest 경로와, 쿼리가 primary index 프루닝 → bloom filter skip index → 컬럼 읽기(페이지 캐시 or gp3 직행)를 거치는 조회 경로를 함께 보여주는 아키텍처 다이어그램.](../.gitbook/assets/ko-database-01-clickhouse-on-eks-0.png)

[🔍 인터랙티브 다이어그램 보기](https://www.atomai.click/kubernetes-docs/archmaps/ko-database-01-clickhouse-on-eks-0.html)

## TL;DR — 측정 결과 요약

| 측정 항목 | 결과 |
|-----------|------|
| Ingest (서버 내부 생성·삽입) | 1억 행 / 106.7초 = **약 94만 행/초** |
| 저장 크기 (LZ4 기본) | 15.37 GiB → **7.82 GiB (1.97×)** |
| 저장 크기 (ZSTD(3)) | 15.37 GiB → **4.16 GiB (3.7×)**, LZ4 대비 47% 절감 |
| ORDER BY 키 범위 카운트 (1시간 창) | **4 ms** — 59,916행을 세면서 실제로 읽은 행은 1억 중 16,385행 |
| 파드별 ERROR 건수 GROUP BY (2일 창) | **0.36 초** (2,800만 행 스캔) |
| `LIKE '%timeout%'` 풀스캔 | 캐시 warm **2.63 초** / Direct I/O 요청 **31.5 초** (12배) |
| trace_id 점 조회 | 풀스캔 1.13초 → **bloom filter index 후 0.036초 (31배)** |

## 테스트 환경

| 항목 | 값 |
|------|-----|
| 클러스터 | Amazon EKS, Kubernetes 1.36, ap-northeast-2 |
| 노드 | **m5.xlarge** (4 vCPU, 16 GiB) — Karpenter가 프로비저닝한 전용 노드 1대 (벤치마크 파드 단독 배치) |
| 파드 리소스 | requests 2.5 vCPU / 9 Gi, limits 3.5 vCPU / 12 Gi |
| 스토리지 | EBS **gp3 100 GiB 기본 설정** (3,000 IOPS / 125 MiB/s 베이스라인), EBS CSI 드라이버 |
| ClickHouse | 공식 이미지 `clickhouse/clickhouse-server:24.8` (24.8.14.39), 설정 기본값 |
| 시간당 비용 | m5.xlarge 온디맨드 $0.236/h + gp3 100 GiB $0.0912/GB-월 (서울 리전, 2026-09 Pricing API 조회) |

> **버전 안내.** 측정은 당시 LTS였던 24.8에서 했지만, ClickHouse [보안 정책](https://github.com/ClickHouse/ClickHouse/blob/master/SECURITY.md)의 지원 버전 목록에는 이제 24.x가 없습니다(2026년 9월 기준 지원 라인은 26.8 LTS, 26.7, 26.6, 26.3 LTS). 새로 배포한다면 현행 LTS 태그를 쓰세요. 아래에서 측정한 메커니즘 — primary key 프루닝, LZ4/ZSTD 코덱, bloom filter skip index — 은 현행 릴리스에도 모두 있지만, 용량 산정에 쓰려면 실제 배포할 버전에서 다시 재보는 것이 맞습니다.

일부러 "화려하지 않은" 환경입니다. 전용 i-계열 NVMe 인스턴스가 아니라, 여러분 클러스터에 이미 있을 법한 범용 노드와 기본 gp3에서 어디까지 되는지가 이 벤치마크의 질문입니다.

### 배포 매니페스트

아래는 **재실행용** 예제이며 검토 시점 지원 LTS인 26.3.33.24를 사용합니다. 원래 24.8 측정값은 유지합니다. 일반 EC2 노드의 EBS CSI 드라이버·IAM 권한과 PVC 프로비저닝이 필요합니다. 기본 사용자의 외부 접근 제한을 유지하고 `kubectl exec` 안의 localhost 클라이언트로 측정합니다. 이미지 digest·fio/EBS 설정·실제 CPU/메모리 사용도 기록합니다.

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: bench-database
---
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: bench-clickhouse-gp3
provisioner: ebs.csi.aws.com
parameters:
  type: gp3
  encrypted: "true"
  iops: "3000"
  throughput: "125"
volumeBindingMode: WaitForFirstConsumer
reclaimPolicy: Delete
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: clickhouse-data
  namespace: bench-database
spec:
  accessModes: ["ReadWriteOnce"]
  storageClassName: bench-clickhouse-gp3
  resources:
    requests:
      storage: 100Gi
---
apiVersion: v1
kind: Pod
metadata:
  name: clickhouse
  namespace: bench-database
  annotations:
    karpenter.sh/do-not-disrupt: "true"
spec:
  nodeSelector:
    node.kubernetes.io/instance-type: m5.xlarge
  containers:
    - name: clickhouse
      image: clickhouse/clickhouse-server:26.3.33.24
      resources:
        requests: { cpu: "2500m", memory: 9Gi }
        limits: { cpu: "3500m", memory: 12Gi }
      readinessProbe:
        exec:
          command: ["clickhouse-client", "--host", "127.0.0.1", "--query", "SELECT 1"]
        initialDelaySeconds: 5
        periodSeconds: 5
      volumeMounts:
        - name: data
          mountPath: /var/lib/clickhouse
  volumes:
    - name: data
      persistentVolumeClaim:
        claimName: clickhouse-data
```

> 프로덕션에서는 수명주기·복구 자동화가 필요하며, 예를 들어 [Altinity clickhouse-operator](https://github.com/Altinity/clickhouse-operator)의 `ClickHouseInstallation`을 사용할 수 있습니다. 여기서는 측정 대상을 단순하게 유지하기 위해 Pod를 직접 사용했습니다.

## 데이터셋 — 현실적인 Kubernetes 로그 1억 행

균등 난수(generateRandom)는 압축률을 왜곡하므로, 실제 로그처럼 **반복되는 템플릿 + 가변 필드** 구조로 생성했습니다. 10개 네임스페이스, 네임스페이스당 파드 이름 1개(파드 접미사를 네임스페이스를 고르는 것과 같은 해시 버킷에서 만들기 때문에 파드 값은 총 10종뿐입니다 — 압축 수치에 영향을 주는 단순화이며, 측정 2에서 다시 다룹니다), 0.8% ERROR 비율, 7일치 타임스탬프입니다.

```sql
CREATE TABLE logs
(
  timestamp   DateTime64(3),
  namespace   LowCardinality(String),
  pod         String,
  container   LowCardinality(String),
  level       LowCardinality(String),
  message     String,
  trace_id    String,
  duration_ms Float32
)
ENGINE = MergeTree
PARTITION BY toDate(timestamp)
ORDER BY (namespace, timestamp);
```

```sql
INSERT INTO logs (timestamp, namespace, pod, container, level, trace_id, duration_ms, message)
WITH
  ['payment','order','user','search','catalog','cart','shipping','auth','gateway','recommend'] AS nss,
  ['GET /api/v1/orders','POST /api/v1/payments','GET /api/v1/users','GET /api/v1/search',
   'POST /api/v1/cart/items','GET /api/v1/products','POST /api/v1/shipments','POST /oauth/token',
   'GET /healthz','GET /api/v1/recommendations'] AS eps
SELECT
  toDateTime64('2026-08-25 00:00:00', 3) + toIntervalMillisecond(number * 6) AS timestamp,
  nss[(cityHash64(number) % 10) + 1] AS namespace,
  concat(namespace, '-7c7dd4f9c-', substring(lower(hex(sipHash64(cityHash64(number) % 10))), 1, 5)) AS pod,
  if(cityHash64(number + 2) % 10 < 8, 'app', 'istio-proxy') AS container,
  multiIf(cityHash64(number + 3) % 1000 < 8, 'ERROR',
          cityHash64(number + 3) % 1000 < 50, 'WARN',
          cityHash64(number + 3) % 1000 < 300, 'DEBUG', 'INFO') AS level,
  lower(hex(sipHash128(number))) AS trace_id,
  round(if(level = 'ERROR', 2000 + (cityHash64(number + 4) % 30000) / 10,
           (cityHash64(number + 4) % 20000) / 100), 1) AS duration_ms,
  multiIf(
    level = 'ERROR', concat('upstream request timeout after ', toString(round(duration_ms)),
                            'ms endpoint=', eps[(cityHash64(number + 5) % 10) + 1],
                            ' status=503 trace_id=', trace_id),
    concat(eps[(cityHash64(number + 5) % 10) + 1], ' completed status=200 in ',
           toString(duration_ms), 'ms trace_id=', trace_id)
  ) AS message
FROM numbers_mt(100000000)
SETTINGS max_threads = 3, max_insert_threads = 2, max_memory_usage = 9000000000;
```

## 측정 1 — Ingest: 1억 행 / 106.7초

```text
Elapsed: 106.747 sec  →  약 936,800 행/초, 파티션 7개(일 단위), active parts 36개
```

**이 수치의 의미를 정확히 읽어야 합니다.** 서버 내부에서 생성해 바로 삽입(INSERT…SELECT)한 값이므로 네트워크 전송과 텍스트 파싱 비용이 빠진 **서버 내부 경로의 측정값**입니다. 데이터 생성 CPU 비용도 포함하므로 외부 ingest의 수학적 상한은 아닙니다. 외부 성능은 클라이언트·포맷·네트워크·배치·동시성에 따라 달라집니다. 그럼에도 3.5 vCPU 제한 안에서 초당 약 94만 행을 정렬·압축·기록했다는 점, 그것도 125 MiB/s짜리 기본 gp3에서 해냈다는 점이 핵심입니다 — 최종 압축 크기/경과 시간은 약 75 MiB/s지만, 이는 실제 EBS 쓰기 처리량의 계측값이 아닙니다. 페이지 캐시·writeback·merge 비용과 durable flush 조건을 별도로 확인해야 합니다.

## 측정 2 — 압축: 어떤 컬럼이 돈을 쓰는가

전체: 15.37 GiB → 7.82 GiB (**1.97×**, LZ4 기본). 컬럼별 내역이 훨씬 흥미롭습니다:

| 컬럼 | 압축 후 | 압축 전 | 비율 |
|------|---------|---------|------|
| message | 3.97 GiB | 8.75 GiB | 2.2× |
| **trace_id** | **3.08 GiB** | 3.07 GiB | **1.0× (압축 불가)** |
| timestamp | 404.07 MiB | 762.94 MiB | 1.89× |
| duration_ms | 289.17 MiB | 381.47 MiB | 1.32× |
| level | 45.88 MiB | 95.72 MiB | 2.09× |
| container | 39.27 MiB | 95.72 MiB | 2.44× |
| pod | 9.32 MiB | 2.15 GiB | **236×** |
| namespace | 488.63 KiB | 95.72 MiB | **201×** |

크기와 비율은 `system.parts_columns`가 보고한 값 그대로입니다(압축 전/후 바이트 합계의 `formatReadableSize`). 비율은 반올림된 크기가 아니라 원래 바이트 수로 계산된 값입니다.

두 가지 교훈이 바로 보입니다:

1. **LowCardinality + ORDER BY 정렬의 위력** — namespace는 ORDER BY 첫 키라서 같은 값이 길게 이어지고, 95.7 MiB가 489 KiB로 사라집니다. pod가 236×인 것도 같은 이유인데, 한 가지 주의가 필요합니다. 이 생성기는 네임스페이스당 파드 이름을 정확히 1개(총 10종)만 만들기 때문에 pod 컬럼이 namespace의 복사본처럼 동작합니다. 네임스페이스당 파드가 수십 개이고 재시작마다 이름이 바뀌는 실제 클러스터에서는 pod 압축률이 눈에 띄게 낮아집니다.
2. **고엔트로피 ID가 스토리지의 약 40%를 먹습니다** — 이 실행의 LZ4에서는 32자 hex trace_id가 거의 줄지 않아(1.0×) 전체 7.82 GiB 중 3.08 GiB(39.4%)를 차지합니다. 로그 스키마를 설계할 때 "ID를 문자열로 넣을 것인가"가 저장 비용의 최대 변수라는 뜻입니다. hex 문자열에는 4비트 정보가 1바이트 문자로 표현되므로 다른 코덱으로도 압축 여지가 있습니다. UUID/FixedString(16) 바이너리 표현은 원시 표현 폭을 줄이지만 최종 저장 절감은 코덱·인덱스·쿼리 호환성을 포함해 측정합니다.

### LZ4 vs ZSTD(3) — 저장 47% vs 스캔 1.9×

같은 데이터를 `CODEC(ZSTD(3))` 테이블에 다시 삽입해 비교했습니다:

| | LZ4 (기본) | ZSTD(3) |
|---|-----------|---------|
| 압축 후 크기 | 7.82 GiB (1.97×) | **4.16 GiB (3.7×)** |
| 재압축 삽입 (1억 행) | — | 120.0초 |
| `LIKE '%timeout%'` 풀스캔 (warm) | **2.63초** | 4.9초 |

저장은 47% 줄지만 CPU-bound 풀스캔은 1.9배 느려집니다. **최근 데이터 LZ4 + 오래된 파티션 TTL ZSTD 재압축**은 검토할 수 있는 조합입니다. 최적 코덱은 실제 데이터·CPU·I/O 비중에 따라 달라집니다.

## 측정 3 — 쿼리: 어떤 쿼리가 왜 빠른가/느린가

각 쿼리는 mark/uncompressed 캐시를 비운 뒤 ① `min_bytes_to_use_direct_io=1`로 페이지 캐시를 우회한 Direct I/O 요청 1회, ② warm 3회(최솟값 기록)를 측정했습니다.

| # | 쿼리 패턴 | Direct I/O 요청 | warm | 읽은 행 수 (`read_rows`) |
|---|-----------|-----------|------|-----------|
| Q1 | `WHERE namespace='payment' AND timestamp BETWEEN …` (1시간 창 count) | 13 ms | **4 ms** | 16,385 (0.016%) — 결과 59,916 |
| Q2 | 파드별 ERROR 건수, 2일 창 GROUP BY (데이터셋에 파드가 10개뿐이라 `LIMIT 10`은 사실상 전체 반환) | 0.57 s | **0.36 s** | 2,800만 |
| Q3 | `message LIKE '%timeout%'` 전 기간 풀스캔 | **31.5 s** | 2.63 s | 1억 |
| Q4 | namespace별 duration p50/p99 전 기간 | 1.34 s | **1.03 s** | 1억 (필터 없음) |
| Q5 | `trace_id = '…'` 점 조회 (인덱스 없음) | 24.3 s | 1.13 s | 1억 |

읽는 법:

- **Q1이 4ms인 이유**: PARTITION BY(일)와 ORDER BY(namespace, timestamp)가 겹치면서 `payment`의 1시간 창이 하나의 연속된 키 범위가 됩니다. 결과는 59,916행인데 `system.query_log`의 read_rows는 16,385행뿐입니다. 24.6부터 ClickHouse는 primary key 범위 안에 완전히 들어가는 granule은 인덱스만으로 개수를 세고, 범위 양끝에 걸친 granule(약 두 개, 8,192행씩)만 실제로 압축을 풀어 읽기 때문입니다. 이는 해당 조건에서 읽을 데이터를 줄이는 최적화입니다. 적용 여부는 `EXPLAIN indexes = 1`과 실제 read_rows로 확인합니다.
- **Q3의 31.5초(Direct I/O 요청) vs 2.63초(warm)**: message 컬럼 압축본 약 4 GiB를 디스크에서 읽으면 4 GiB ÷ 31.5초 ≈ **130 MiB/s — gp3 볼륨 상한(125 MiB/s)과 이 m5.xlarge의 인스턴스 EBS 베이스라인(1,150 Mbps ≈ 137 MiB/s)이 겹쳐 있는 좁은 구간에 막힌 수치**입니다. 두 한계가 너무 가까워 이 측정만으로는 어느 쪽이 먼저 걸렸는지 가릴 수 없습니다. 같은 쿼리가 페이지 캐시에서는 CPU-bound(초당 3,800만 행)로 바뀝니다. 풀스캔 성능은 데이터베이스가 아니라 **볼륨 처리량 설정**의 문제일 수 있다는 실측 증거입니다. ([EBS gp2 vs gp3 실측](../storage/01-ebs-gp2-gp3-benchmark.md) 참고) 인덱스 없는 Q5도 같은 이야기입니다: trace_id 3.08 GiB를 24.3초에 읽어 ≈ 130 MiB/s.
- **Q4가 풀스캔인데 1초인 이유**: 컬럼 지향의 본질입니다. 컬럼 크기로 보면 duration_ms(289 MiB)와 namespace(0.5 MiB)만 건드리고 7.8 GiB를 읽지 않으며, warm 실행은 Float32 1억 개의 분위수 계산에 CPU-bound입니다.
- **짧은 Direct I/O 요청 수치(Q2, Q4)만으로 물리 디스크 처리량을 계산할 수 없습니다.** 최종 압축 크기와 쿼리 시간의 비율이 125 MiB/s를 넘는다는 이유만으로 페이지 캐시 사용을 증명하지는 못합니다. mark/uncompressed cache 삭제는 OS 페이지 캐시 삭제와도 다릅니다. 원래 실행은 추가 추적 전에 종료되었으므로 캐시·read method·짧은 구간의 서비스 동작을 분리하지 못했습니다. 새 실행에서는 query_log의 ProfileEvents와 노드/EBS I/O 지표를 함께 저장합니다.

## 측정 4 — bloom filter skip index: 1.13초 → 0.036초

trace_id 점 조회는 ORDER BY 키가 아니므로 기본적으로 풀스캔(1.13초)입니다. skip index를 추가하면:

```sql
ALTER TABLE logs ADD INDEX trace_bf trace_id TYPE bloom_filter(0.01) GRANULARITY 4;
ALTER TABLE logs MATERIALIZE INDEX trace_bf;  -- asynchronous; wait for system.mutations.is_done
```

| | 인덱스 없음 | bloom_filter(0.01) |
|---|-----------|-------------------|
| warm 조회 시간 | 1.13 s | **0.036 s (31×)** |
| 읽은 행 수 | 1억 | **108만 (98.9% 스킵)** |
| 읽은 데이터 | 3.82 GiB | 42.6 MiB |
| 인덱스 크기 | — | 119.7 MiB (테이블의 1.5%) |

관측용 로그 저장소에서 "trace ID로 점프"는 가장 흔한 쿼리인데, 인덱스 크기 1.5%와 materialize 20초로 31배를 얻습니다. Grafana + ClickHouse 로그 백엔드를 구성한다면 후보 인덱스입니다. 실제 선택도·false positive·쓰기/merge 비용과 인덱스 사용 여부를 확인해야 합니다.

## 비용으로 환산하면

2026-09-11 Pricing API에서 서울 리전 m5.xlarge Linux 온디맨드 `$0.236/h`, gp3 `$0.0912/GB-month`를 확인했습니다. EBS는 **프로비저닝한 용량**으로 과금됩니다. 데이터가 7.82 GiB 또는 4.16 GiB여도 이 예제의 100 GiB 볼륨은 월 **$9.12**이며, 사용 바이트에 단가를 곱한 `$0.71/$0.38`을 실제 청구액으로 보면 안 됩니다.

하루 1억 행을 30일 보관하면 이 합성 데이터의 LZ4 비율상 데이터만 약 235 GiB입니다. 기존 100 GiB 볼륨에는 들어가지 않으며, merge 작업 공간·인덱스·복제·백업·여유 용량을 더해 프로비저닝해야 합니다. 235 GiB만 잡아도 약 `$21.43/월`이고 노드·EKS·네트워크·운영 비용은 별도입니다. CloudWatch Logs의 ingest 요금과 EBS 저장 비용 한 항목만 비교해 전체 비용 우위를 결론 내리지 않습니다.

## 재현 방법

아래는 패턴을 비교하기 위한 새 실행 예제입니다. Q1/Q2의 원래 정확한 시간 창과 Q5의 원래 ID는 보존되지 않았으므로 기존 결과 행 수·밀리초와 일치한다고 주장하지 않습니다. 재실행에는 각각의 SQL, 버전, timezone, read settings, 원시 결과를 함께 저장합니다.

```sql
-- Q1: explicit example window for a new run, not recovered historical SQL.
SELECT count() FROM logs
WHERE namespace = 'payment'
  AND timestamp >= toDateTime64('2026-08-26 00:00:00', 3)
  AND timestamp < toDateTime64('2026-08-26 01:00:00', 3);

-- Q2: a two-day example window.
SELECT namespace, pod, count() AS errors FROM logs
WHERE level = 'ERROR'
  AND timestamp >= toDateTime64('2026-08-26 00:00:00', 3)
  AND timestamp < toDateTime64('2026-08-28 00:00:00', 3)
GROUP BY namespace, pod ORDER BY errors DESC LIMIT 10;

-- Q3: full-range message scan.
SELECT count() FROM logs WHERE message LIKE '%timeout%';

-- Q4: approximate quantiles; all candidate rows are still processed.
SELECT namespace, quantiles(0.5, 0.99)(duration_ms) AS p50_p99
FROM logs GROUP BY namespace;

-- Q5: a trace ID that the generator creates for number=42.
SELECT * FROM logs
WHERE trace_id = lower(hex(sipHash128(toUInt64(42))));
```

```bash
kubectl apply -f clickhouse.yaml
kubectl wait -n bench-database pod/clickhouse --for=condition=Ready --timeout=300s
kubectl exec -n bench-database clickhouse -- \
  clickhouse-client --host 127.0.0.1 --query 'SELECT version(), timezone()'
# Save the CREATE TABLE block as schema.sql and INSERT block as insert.sql.
kubectl exec -i -n bench-database clickhouse -- \
  clickhouse-client --host 127.0.0.1 --multiquery < schema.sql
kubectl exec -i -n bench-database clickhouse -- \
  clickhouse-client --host 127.0.0.1 --time --multiquery < insert.sql
# Run the selected query with a unique ID; store its exact SQL with the results.
kubectl exec -i -n bench-database clickhouse -- \
  clickhouse-client --host 127.0.0.1 --query_id benchmark-q3-run1 \
  --time --multiquery < q3.sql
```

각 쿼리의 Direct I/O 요청은 해당 SELECT 끝에 `SETTINGS min_bytes_to_use_direct_io=1`을 넣어 별도로 실행합니다. 이후 기본 read 설정으로 반복하고 최솟값뿐 아니라 전체 표본과 중앙값을 저장합니다. `SYSTEM FLUSH LOGS` 후 해당 query_id의 query_log를 보관하고, 인덱스 적용은 `system.mutations` 완료를 확인한 뒤 비교합니다. 쿼리 캐시·filesystem cache·OS 캐시와 background merge도 기록합니다.

모든 결과를 클러스터 밖으로 복사한 뒤 전용 `bench-database` namespace와 `bench-clickhouse-gp3` StorageClass를 정리합니다. 이 예제의 Delete reclaimPolicy는 PVC 삭제 시 측정 데이터도 삭제합니다.

## 해석 시 주의사항

- **단일 노드, 단일 실행 환경**입니다. 복제/샤딩 구성이나 다른 인스턴스 타입에서는 절대값이 달라집니다. 상대적 패턴(프루닝, 컬럼 지향, 캐시, 인덱스 효과)이 이 문서의 본론입니다.
- ingest 수치는 서버 내부 생성·삽입 경로의 측정값이며 외부 수집 처리량은 아닙니다(측정 1 참고).
- 합성 데이터의 압축률은 필드 구성에 민감합니다. 고엔트로피 trace_id를 message에도 포함시켜 보수적으로 만들었지만, pod 컬럼(이름이 10종뿐, 측정 2 참고)은 반대로 낙관적입니다. 실제 로그의 압축률은 스키마에 따라 이보다 좋을 수도 나쁠 수도 있습니다.
- warm 첫 회는 캐시 적재 때문에 느립니다(Q3 첫 회 8.7초 → 이후 2.6초). 표의 warm 값은 3회 중 최솟값입니다.

## 함께 읽기

- [ClickHouse — 로그 백엔드 관점](../observability/logging/04-clickhouse.md) — 수집 파이프라인(Fluent Bit/Vector)과의 통합
- [EBS gp2 vs gp3 실측 벤치마크](../storage/01-ebs-gp2-gp3-benchmark.md) — Q3에서 확인한 볼륨 처리량 병목의 근거
- [Database on Kubernetes 개요](./README.md) — Operator 지형과 관리형 vs self-hosted 판단 기준

## 검토 근거

- [ClickHouse support policy](https://github.com/ClickHouse/ClickHouse/blob/master/SECURITY.md)
- [Official Docker image behavior](https://github.com/ClickHouse/ClickHouse/blob/master/docker/server/README.md)
- [Quantile sampling](https://clickhouse.com/docs/sql-reference/aggregate-functions/reference/quantile)
- [Data skipping indexes](https://clickhouse.com/docs/optimize/skipping-indexes)
- [Partial count optimization](https://github.com/ClickHouse/ClickHouse/pull/60463)
- [EBS pricing](https://aws.amazon.com/ebs/pricing/)
