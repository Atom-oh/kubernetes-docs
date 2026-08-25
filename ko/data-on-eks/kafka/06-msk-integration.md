# Part 6: MSK 통합

> **지원 버전**: Amazon MSK (Provisioned & Serverless), MSK Connect\
> **마지막 업데이트**: 2026년 7월 9일

## 실습 환경 설정

이 문서의 예제를 따라하기 위해서는 다음과 같은 도구와 환경이 필요합니다:

### 필수 도구

* AWS CLI v2 (MSK 클러스터 및 IAM 정책 관리)
* kubectl v1.28 이상, 작동하는 EKS 클러스터
* `aws-msk-iam-auth` 클라이언트 라이브러리 (IAM 인증을 사용하는 Kafka 클라이언트용)
* External Secrets Operator 또는 IRSA가 구성된 EKS 클러스터 (자격 증명 주입용)

앞선 Part들에서는 EKS 위에 Strimzi로 Kafka를 직접 운영하는 방법을 다뤘습니다. 이번 Part에서는 AWS의 완전관리형 Kafka 서비스인 Amazon MSK를 EKS 워크로드와 통합하는 방법과, Strimzi 셀프 매니지드 대안 사이의 트레이드오프를 다룹니다. 또한 완전히 다른 스트리밍 서비스인 Kinesis Data Streams와 Kafka의 관계도 명확히 정리합니다.

## Amazon MSK vs Strimzi 셀프 매니지드 비교

두 방식 모두 "EKS 워크로드가 Kafka를 사용한다"는 목표는 같지만, 브로커가 실제로 어디서 실행되고 누가 그것을 운영하느냐가 다릅니다. MSK는 브로커를 AWS가 관리하는 별도의 인프라에서 실행하고, Strimzi는 브로커를 EKS 클러스터 내부의 Pod로 실행합니다.

| 항목 | Amazon MSK (Provisioned) | Amazon MSK Serverless | Strimzi (EKS 셀프 매니지드) |
| --- | --- | --- | --- |
| **운영 부담** | AWS가 브로커 패치, 하드웨어 교체, 스토리지 확장을 관리 | AWS가 브로커 사이징 자체를 없앰 (완전 자동 확장) | Operator가 롤링 업그레이드/재조정을 수행하지만, 업그레이드 시점·용량 계획·장애 대응은 사용자 책임 |
| **비용 모델** | 브로커 시간당 요금 + 스토리지(GB-월) + 데이터 전송 | 처리량 기반 과금(파티션당, GB 인입/유출당) | EC2/EBS 직접 비용. 대규모에서는 보통 더 저렴하지만 운영 인력 비용이 별도로 필요 |
| **오토스케일링** | 스토리지 자동 확장은 지원, 브로커 스케일은 수동/API 호출 | 파티션 단위로 완전 자동 스케일, 브로커 개념이 사용자에게 노출되지 않음 | Cruise Control 등으로 반자동화 가능하나 기본적으로 사용자가 트리거 |
| **커스텀 설정** | 브로커 설정(`server.properties`) 커스터마이징 가능 | 커스텀 브로커 설정 불가, 일부 API/기능 제한 (예: 특정 ACL, 커넥터 유형) | 리스너, 인터셉터, KRaft 컨트롤러 튜닝 등 거의 모든 설정을 자유롭게 변경 가능 |
| **버전 지원** | AWS가 큐레이션한 Kafka 버전 목록만 지원, 업스트림보다 지연될 수 있음 | 특정 고정 버전 사용, 버전 선택권 없음 | Strimzi가 지원하는 범위 내에서 최신 Kafka 버전을 원하는 시점에 채택 가능 |
| **멀티테넌시** | 클러스터/리소스 정책으로 격리, 세밀한 커스터마이징은 제한적 | 서버리스 특성상 테넌트 격리는 AWS 내부 구현에 위임 | 네임스페이스, `KafkaUser` ACL, 커스텀 리스너로 세밀한 테넌시 설계 가능 |
| **관측/GitOps 통합** | CloudWatch/Prometheus 익스포터 별도 연동, AWS 콘솔이 주 관리 화면 | 동일 | 나머지 플랫폼(Argo CD, Prometheus Operator 등)과 동일한 GitOps/관측 파이프라인에 자연스럽게 편입 |

### MSK를 선택하는 이유

* 브로커 운영 지식이 있는 인력이 부족하거나, Kafka 운영을 핵심 역량으로 두고 싶지 않은 조직
* AWS 콘솔/IAM/CloudWatch 등 기존 AWS 네이티브 운영 체계에 이미 깊게 투자된 환경
* MSK Serverless처럼 트래픽 예측이 어려운 워크로드에서 브로커 용량 계획 자체를 없애고 싶은 경우

### EKS에서 Strimzi로 Kafka를 직접 운영하는 이유 (MSK가 있어도)

* 나머지 플랫폼(다른 워크로드, GitOps, Prometheus/Grafana 관측 스택)과 **동일한 도구·동일한 배포 파이프라인**으로 Kafka를 관리하고 싶은 경우 — 별도의 AWS 콘솔/IAM 표면을 늘리지 않음
* 특정 클라우드에 종속되지 않는 **이식성**이 필요한 경우 (온프레미스, 멀티클라우드로 이전 가능성)
* 초대규모 트래픽에서 EC2/EBS를 직접 관리하는 것이 브로커 시간당 과금보다 비용 효율적인 경우
* MSK가 아직 지원하지 않는 최신 Kafka 기능(신규 KIP, 커스텀 인터셉터, 특정 KRaft 튜닝 옵션)이 필요한 경우

## EKS에서 MSK에 연결하기

EKS의 워크로드가 MSK 브로커에 도달하려면 네트워크 경로와 인증 두 가지를 모두 갖춰야 합니다.

### 네트워크 경로

* **같은 VPC**: EKS 클러스터와 MSK 클러스터가 동일 VPC에 있다면 서브넷 라우팅만으로 연결 가능합니다. 가장 단순하고 지연 시간도 가장 낮습니다.
* **다른 VPC**: VPC 피어링 또는 AWS Transit Gateway로 두 VPC를 연결해야 합니다. MSK는 퍼블릭 액세스를 지원하지만(공용 브로커 엔드포인트), 프로덕션에서는 보통 프라이빗 연결을 권장합니다.
* **보안 그룹**: MSK 클러스터의 보안 그룹은 EKS 워커 노드(또는 파드가 자체 보안 그룹을 갖는 경우 파드) 보안 그룹으로부터 브로커 포트(플레인텍스트 9092, TLS 9094, SASL/SCRAM 9096, IAM 9098)에 대한 인바운드를 명시적으로 허용해야 합니다. 기본적으로는 아무 트래픽도 허용되지 않습니다.

```bash
# MSK 클러스터 보안 그룹에 EKS 노드 보안 그룹으로부터의 IAM 인증 포트 허용
aws ec2 authorize-security-group-ingress \
  --group-id sg-0abcd1234msk \
  --protocol tcp --port 9098 \
  --source-group sg-0efgh5678eksnode
```

### 인증 방식 비교

| 방식 | 동작 방식 | EKS 통합 포인트 |
| --- | --- | --- |
| **IAM 인증 (`AWS_MSK_IAM`)** | 클라이언트가 `AWS_MSK_IAM`이라는 전용 SASL 메커니즘을 통해 SigV4 서명된 요청으로 인증, IAM 정책으로 토픽별 권한 제어 | IRSA로 파드에 IAM 역할 부여, 별도 자격 증명 배포 불필요 |
| **SASL/SCRAM** | 사용자명/패스워드 기반, 자격 증명은 AWS Secrets Manager에 저장 | External Secrets Operator로 Secrets Manager의 SCRAM 자격 증명을 K8s Secret으로 동기화 |
| **상호 TLS(mTLS)** | 클라이언트 인증서를 AWS Private CA로 발급, 인증서 기반 신원 확인 | cert-manager 또는 External Secrets Operator로 인증서/키를 파드에 마운트 |

IAM 인증은 EKS와 조합했을 때 가장 자연스럽습니다. IRSA(IAM Roles for Service Accounts)로 파드에 세분화된 IAM 역할을 부여하면, 별도의 비밀번호나 인증서를 배포/로테이션할 필요 없이 Kafka 토픽 단위의 접근 제어를 IAM 정책만으로 표현할 수 있습니다.

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "kafka-cluster:Connect",
        "kafka-cluster:AlterCluster",
        "kafka-cluster:DescribeCluster"
      ],
      "Resource": "arn:aws:kafka:ap-northeast-2:111122223333:cluster/my-msk-cluster/*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "kafka-cluster:*Topic*",
        "kafka-cluster:WriteData",
        "kafka-cluster:ReadData"
      ],
      "Resource": "arn:aws:kafka:ap-northeast-2:111122223333:topic/my-msk-cluster/*/orders"
    }
  ]
}
```

클라이언트 측에서는 `aws-msk-iam-auth` 라이브러리를 클래스패스(또는 언어별 동등한 패키지)에 추가하고, Kafka 클라이언트 설정에 다음을 지정합니다.

```properties
security.protocol=SASL_SSL
sasl.mechanism=AWS_MSK_IAM
sasl.jaas.config=software.amazon.msk.auth.iam.IAMLoginModule required;
sasl.client.callback.handler.class=software.amazon.msk.auth.iam.IAMClientCallbackHandler
```

## MSK Connect

MSK Connect는 AWS의 완전관리형 Kafka Connect 서비스입니다. Kafka Connect 워커의 프로비저닝, 스케일링, 패치를 AWS가 대신 처리하며, 커넥터 플러그인(JAR 묶음)을 S3에 업로드해 등록하는 방식으로 동작합니다.

중요한 점은 MSK Connect가 **MSK 클러스터에만 연결되는 것이 아니라는 것**입니다. 부트스트랩 브로커에 네트워크로 도달할 수 있는 한, MSK Connect는 EKS 위에서 Strimzi로 셀프 매니지드 중인 Kafka 클러스터에도 커넥터를 연결할 수 있습니다.

```bash
# 커스텀 커넥터 플러그인을 S3에 업로드 후 MSK Connect 커스텀 플러그인으로 등록
aws kafkaconnect create-custom-plugin \
  --name debezium-postgres-plugin \
  --content-type ZIP \
  --location s3Location='{bucketArn=arn:aws:s3:::my-connect-plugins,fileKey=debezium-postgres-2.7.zip}'
```

| 항목 | MSK Connect | Strimzi `KafkaConnect` (EKS 자체 운영) |
| --- | --- | --- |
| **운영 부담** | 워커 인프라를 AWS가 관리, 사용자는 커넥터 설정만 관리 | 워커 Pod의 스케일링, 모니터링, 리소스 튜닝을 직접 관리 |
| **유연성** | AWS가 지원하는 커넥터 프레임워크 범위 내로 제한 | 임의의 커넥터, 커스텀 SMT(Single Message Transform), 사이드카 추가 등 자유도 높음 |
| **이식성** | AWS 전용 서비스, 다른 환경으로 이전 어려움 | 다른 Kubernetes 클러스터로 그대로 이식 가능 |
| **관측** | CloudWatch Logs/Metrics로 커넥터 상태 확인 | 나머지 EKS 워크로드와 동일한 Prometheus/Grafana 파이프라인으로 통합 |

## Kinesis Data Streams와의 비교/연동

Kinesis Data Streams와 Kafka는 자주 같이 언급되지만 **호환 가능한 프로토콜이 아닙니다**. Kinesis는 AWS 네이티브 스트리밍 서비스로 자체 API/SDK를 사용하며, Kafka의 프로듀서/컨슈머 프로토콜을 이해하지 못합니다. MSK가 "Kafka 호환"이라는 표현을 쓴다고 해서 이것이 Kinesis와 상호 운용된다는 의미는 아닙니다 — MSK는 Apache Kafka 프로토콜을 구현한 서비스이고, Kinesis는 완전히 별개의 서비스입니다.

| 항목 | Apache Kafka (MSK/Strimzi) | Kinesis Data Streams |
| --- | --- | --- |
| **프로토콜** | 오픈 소스 Kafka 프로토콜, 다양한 클라이언트/생태계와 호환 | AWS 전용 API, Kafka 클라이언트와 호환 불가 |
| **확장 단위** | 파티션 (토픽 생성 시 정의, 재파티셔닝 가능) | 샤드 (읽기/쓰기 용량 단위, 분할/병합으로 조정) |
| **운영 복잡도** | 브로커/컨트롤러 운영 필요 (MSK 사용 시 AWS가 대신 관리) | 완전관리형, 서버 개념 자체가 없음 |
| **AWS 서비스 통합** | 커넥터를 통한 간접 통합 (Kafka Connect, MSK Connect) | Lambda 트리거, Firehose, Kinesis Data Analytics와 네이티브로 직결 |
| **생태계** | Kafka Streams, ksqlDB, Flink, Debezium 등 광범위한 오픈소스 생태계 | AWS 서비스 중심의 제한적이지만 통합이 간단한 생태계 |
| **보존 기간** | 사실상 무제한(스토리지 비용만 지불, 기본은 7일) | 기본 24시간, 최대 365일까지 연장 가능(과금 증가) |

### 두 시스템을 연동하는 실질적인 방법

Kafka와 Kinesis를 "직접 연동"할 필요가 있다면(마이그레이션, 레거시 Kinesis 컨슈머와의 브리징 등), 실제 패턴은 **Kafka Connect(또는 MSK Connect)의 Kinesis 커넥터**를 사용하는 것입니다.

* **Kinesis Sink 커넥터**: Kafka 토픽의 메시지를 읽어 Kinesis 스트림에 기록 — Kafka 기반 파이프라인의 출력을 Kinesis 소비 생태계(Lambda, Firehose)로 넘길 때 사용
* **Kinesis Source 커넥터**: Kinesis 스트림의 레코드를 읽어 Kafka 토픽에 기록 — 기존 Kinesis 프로듀서를 유지하면서 점진적으로 Kafka 기반 소비자로 전환할 때 사용

이 커넥터들은 MSK Connect에 배포하거나, Strimzi `KafkaConnect`/`KafkaConnector` CR로 EKS 위에서 직접 운영할 수 있습니다 — 앞서 다룬 MSK Connect vs Strimzi 트레이드오프가 그대로 적용됩니다.

## 의사결정 가이드

아래 체크리스트로 자체 관리 Strimzi, MSK Provisioned, MSK Serverless, Kinesis 중 무엇을 선택할지 좁혀갑니다.

* **팀에 Kafka 운영 전문성이 있고, 세밀한 튜닝/커스텀 설정이 필요한가?** → 예: Strimzi (EKS 셀프 매니지드) / 아니오: MSK로 이동
* **멀티 클라우드/온프레미스 이식성이 핵심 요구사항인가?** → 예: Strimzi / 아니오: MSK 계열 검토 가능
* **트래픽이 예측 불가능하거나 스파이크가 크고, 브로커 용량 계획 자체를 없애고 싶은가?** → 예: MSK Serverless / 아니오: MSK Provisioned 또는 Strimzi
* **이미 Lambda, Firehose 등 AWS 네이티브 이벤트 처리에 깊게 투자되어 있고 Kafka 생태계(Kafka Streams, ksqlDB 등)가 필요 없는가?** → 예: Kinesis Data Streams 검토 / 아니오: Kafka(MSK/Strimzi) 유지
* **AWS 콘솔/IAM 운영 표면을 늘리지 않고 나머지 EKS 플랫폼과 동일한 GitOps로 관리하고 싶은가?** → 예: Strimzi / 아니오: MSK

정답은 대부분 "혼합"입니다 — 예를 들어 신규 서비스는 MSK Serverless로 빠르게 시작하고, 커스텀 튜닝이 필요해지는 시점에 Strimzi로 이전하는 것도 흔한 경로입니다.

## 다음 단계

MSK든 Strimzi든 클러스터가 안정적으로 동작하는지 확인하려면 브로커 메트릭과 컨슈머 랙을 지속적으로 관측해야 합니다. 이는 [Part 7: 모니터링](./07-monitoring.md)에서 다룹니다.

[메인 페이지로 돌아가기](./README.md)

## 퀴즈

이 장에서 배운 내용을 테스트하려면 [주제 퀴즈](../../quizzes/data-on-eks/kafka/06-msk-integration-quiz.md)를 풀어보세요.
