# Part 6: MSK 통합

> **검토 기준**: MSK Standard/Express Provisioned, MSK Serverless, MSK Connect; Java IAM helper 2.3.8\
> **최종 검토**: 2026년 9월 12일

## 책임과 준비사항

Amazon MSK의 브로커는 EKS 밖의 AWS 관리 인프라에서 실행됩니다. Strimzi는 팀이
운영하는 Kubernetes 워크로드로 브로커를 실행합니다. 어느 쪽이든 애플리케이션,
토픽, 접근 제어, 보존과 복구 설계가 필요합니다. 관리형 브로커가 Kafka 동작에 대한
이해까지 대신하지는 않습니다.

AWS CLI v2와 EKS 버전에 호환되는 kubectl을 사용합니다. IAM 클라이언트에는 지원되는
인증 helper와 정상적인 워크로드 자격증명 체인이 필요합니다. EKS Pod Identity나
IRSA로 임시 자격증명을 제공할 수 있습니다. External Secrets Operator는 다른 비밀
관리 흐름에서 선택하는 도구이며 IAM 인증의 필수 구성요소가 아닙니다.

## 실제 MSK 유형 비교

| 선택지 | 용량과 설정 | 비교할 비용 |
| --- | --- | --- |
| MSK Provisioned Standard | 브로커·스토리지를 선택하고 필요 시 저장소 자동 확장을 구성; 지원되는 브로커 설정만 변경 가능 | 브로커 시간, 프로비저닝한 저장소, 선택한 처리량·계층형 저장소, 네트워크 |
| MSK Provisioned Express | 브로커 컴퓨팅을 선택하며 저장소는 자동 확장·사용량 과금; 설정·처리량 제한 적용 | 브로커 시간, 데이터 입력, 사용 저장소, 해당 네트워크 비용 |
| MSK Serverless | AWS가 브로커 용량 관리; 사용자도 토픽·파티션·보존·할당량 계획 필요 | **클러스터 시간**, 파티션 시간, 데이터 입력·출력, 사용 저장소, 해당 네트워크 비용 |
| EKS의 Strimzi | 노드·디스크·브로커/컨트롤러 배치와 Operator 지원 설정 운영 | EKS/EC2/EBS, 네트워크, 여유 용량, 관측과 운영 노력 |

Express는 Serverless가 아닌 **Provisioned 브로커 유형**입니다. 현재 공식 문서는
3개 AZ를 요구하며 KStreams의 불완전한 지원, KIP-932 미지원 등의 제약을 명시합니다.
모든 Kafka 기능이 동일하게 동작한다고 가정하지 말고 브로커 유형·버전 조합을 확인합니다.

Serverless는 IAM 인증·인가를 요구하며 Kafka ACL을 지원하지 않습니다. 목록에
명시된 토픽 설정만 변경할 수 있습니다. 예를 들어 보존 설정은 바꿀 수 있지만
`cleanup.policy`는 토픽 생성 때만 선택합니다. 기본 보존에는 7일뿐 아니라
**파티션당 250 GiB 크기 제한**도 있어 시간보다 크기 제한에 먼저 도달할 수 있습니다.
용량 자동 확장이 임의의 파티션 수나 급증 트래픽을 무제한 처리한다는 뜻은 아닙니다.

각 서비스는 CloudWatch 지표를 제공하지만 Serverless의 관측 기능은 Provisioned의
브로커 단위 Prometheus/open monitoring과 같지 않습니다. Serverless의 테넌트별
IAM 토픽·그룹 정책도 사용자 책임입니다. Strimzi에서도 Kubernetes 네임스페이스만으로
Kafka 토픽 접근이 인가되는 것은 아닙니다.

MSK도 API와 IaC로 관리할 수 있으므로 GitOps는 Strimzi만의 기능이 아닙니다.
Strimzi 이식성도 스토리지·네트워크·인증과 Operator 버전에 영향을 받습니다.
총비용과 복구 요구를 측정해 비교하며 “대규모에서는 항상 자체 운영이 저렴함”,
“급증 트래픽에는 Serverless가 가장 저렴함”으로 단정하지 않습니다.

## EKS에서의 네트워크 연결

클라이언트는 bootstrap 주소뿐 아니라 **metadata에 광고된 모든 브로커 주소**에
도달해야 합니다. DNS, 라우트, 보안 그룹, NACL, 실제 Pod·노드 소스와 egress를
확인합니다. 같은 VPC라는 사실만으로 연결이 완성되지는 않습니다.

다른 VPC 연결에는 피어링·Transit Gateway와 지원되는 MSK **multi-VPC private
connectivity**(PrivateLink) 등이 있습니다. 관리형 multi-VPC 기능은 같은 리전에서
사용하며 클러스터·인증·AZ/서브넷 조건이 있습니다. 공개 엔드포인트는 지원되는
클러스터에서 명시적으로 선택하는 기능이지 VPC 간 연결의 필수 조건이 아닙니다.

| 직접 연결 엔드포인트 예시 | 포트 |
| --- | --- |
| 프라이빗 IPv4 TLS | 9094 |
| 프라이빗 IPv4 SASL/SCRAM | 9096 |
| 프라이빗 IPv4 IAM | 9098 |
| 지원·활성화된 공개 TLS / SCRAM / IAM | 9194 / 9196 / 9198 |

IPv6와 관리형 multi-VPC 엔드포인트는 다른 포트를 사용할 수 있습니다. 실제
bootstrap 응답에서 네트워크·인증 방식에 맞는 필드를 선택하며 모든 주소의 포트를
9098로 바꾸지 않습니다.

```bash
: "${DOCS_AWS_REGION:?Set the MSK region}"
: "${DOCS_MSK_CLUSTER_ARN:?Set the exact existing cluster ARN}"
aws kafka get-bootstrap-brokers \
  --region "$DOCS_AWS_REGION" \
  --cluster-arn "$DOCS_MSK_CLUSTER_ARN"
```

같은 VPC에서 프라이빗 IPv4 IAM 주소로 직접 연결한다면 네트워크 관리자가 기존
규칙을 확인한 뒤 다음과 같이 필요한 소스만 허용할 수 있습니다.

```bash
: "${DOCS_AWS_REGION:?Set the MSK region}"
: "${DOCS_MSK_SG_ID:?Set the existing MSK security group ID}"
: "${DOCS_EKS_SOURCE_SG_ID:?Set the actual EKS source security group ID}"
# Example: same-VPC, direct private IPv4 IAM endpoint on port 9098.
aws ec2 authorize-security-group-ingress \
  --region "$DOCS_AWS_REGION" \
  --group-id "$DOCS_MSK_SG_ID" \
  --protocol tcp --port 9098 \
  --source-group "$DOCS_EKS_SOURCE_SG_ID"
```

이 명령은 보안 그룹을 **변경**합니다. 실제 경로의 노드·Pod 소스 SG를 사용하며
다른 VPC의 SG 참조에는 별도 지원 조건이 있습니다. 기존 SG에는 자기 참조 규칙 등
이미 설정된 규칙이 있을 수 있습니다. TCP/TLS 연결 전에 IAM 인증이 성공할 수는 없습니다.

## IAM 인증과 워크로드 ID

| 클라이언트 | 지원되는 IAM 메커니즘 |
| --- | --- |
| Java | AWS Java helper로 `AWS_MSK_IAM` 또는 `OAUTHBEARER` |
| Python, JavaScript, Go, .NET | 해당 언어의 AWS 공식 signer/helper와 `OAUTHBEARER` |

`AWS_MSK_IAM`이 모든 언어의 Kafka 클라이언트에 기본 제공되는 것은 아닙니다.
비 Java helper도 단순한 커뮤니티 대체재가 아닌 AWS 공식 프로젝트입니다.
Provisioned에서는 지원 조건에 따라 SCRAM·상호 TLS도 사용할 수 있으며 비밀·인증서와
Kafka ACL을 구성합니다. Serverless에서는 IAM을 대신하는 선택지가 아닙니다.

Kafka 연결 전에 워크로드 역할 연결·신뢰 관계와 임시 자격증명 갱신을 준비합니다.
상속받은 노드 역할이 의도한 Pod 역할이라고 가정하지 않습니다. 프라이빗 환경에서는
선택한 provider가 필요한 인증 서비스에도 접근해야 합니다. 자격증명 갱신 후
재인증을 시험합니다. Java helper는 Pod Identity 등 일부 provider의 session name
변경 문제를 설명하므로 해당 문제가 발생하면 문서화된 우회 설정을 적용합니다.

### 생산자와 소비자 정책 분리

다음 스크립트는 실제 클러스터 ARN에서 정확한 리소스 ARN을 만듭니다.
`policies.py`로 저장하면 정책 파일만 생성하며 역할에 연결하지 않습니다.
기존의 과도한 `AlterCluster`, `*Topic*` 관리 권한을 빼고 컨슈머 그룹 권한을
넣었습니다. 클러스터 범위 idempotent write와 토픽 범위 쓰기도 구분합니다.

```python
import json
import re
import sys
from pathlib import Path

def policies(cluster_arn, topic="orders", group="orders-consumer"):
    match = re.fullmatch(
        r"arn:(aws(?:-[a-z-]+)?):kafka:([a-z0-9-]+):(\d{12}):cluster/([A-Za-z0-9_-]+)/([A-Za-z0-9-]+)",
        cluster_arn,
    )
    if not match:
        raise ValueError("Supply an exact MSK cluster ARN, including its cluster UUID.")
    for name in [topic, group]:
        if not re.fullmatch(r"[A-Za-z0-9._-]{1,249}", name) or name in [".", ".."]:
            raise ValueError("Use an explicit topic/group name without wildcards.")
    partition, region, account, cluster_name, uuid = match.groups()
    prefix = f"arn:{partition}:kafka:{region}:{account}:"
    identity = f"{cluster_name}/{uuid}"
    topic_arn = prefix + f"topic/{identity}/{topic}"
    group_arn = prefix + f"group/{identity}/{group}"
    def statement(actions, resource):
        return {"Effect": "Allow", "Action": ["kafka-cluster:" + a for a in actions], "Resource": resource}
    return {
        "producer": {"Version": "2012-10-17", "Statement": [
            statement(["Connect", "WriteDataIdempotently"], cluster_arn),
            statement(["DescribeTopic", "WriteData"], topic_arn),
        ]},
        "consumer": {"Version": "2012-10-17", "Statement": [
            statement(["Connect"], cluster_arn),
            statement(["DescribeTopic", "ReadData"], topic_arn),
            statement(["DescribeGroup", "AlterGroup"], group_arn),
        ]},
    }

if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python3 policies.py EXACT_MSK_CLUSTER_ARN")
    for name, policy in policies(sys.argv[1]).items():
        Path(f"msk-{name}-policy.json").write_text(json.dumps(policy, indent=2) + "\n")
```

```bash
: "${DOCS_MSK_CLUSTER_ARN:?Set the exact existing MSK cluster ARN}"
python3 policies.py "$DOCS_MSK_CLUSTER_ARN"
# Review msk-producer-policy.json and msk-consumer-policy.json,
# then attach each to the appropriate workload role through your IAM workflow.
```

기존 토픽은 `orders`이며 소비자는 `orders-consumer` 그룹을 사용해야 합니다.
토픽 생성은 별도 관리자 ID에 맡깁니다. 생산자 정책은 공식 IAM 작업 집합에 따른
**비트랜잭션 idempotent 쓰기**용입니다. 트랜잭션 생산자는 범위를 제한한
transactional-ID 작업과 호환되는 브로커 지원이 추가로 필요합니다. MSK Kafka 3.8
이상은 IAM으로 `WriteTxnMarkers`를 지원합니다. 권한 오류를 숨기기 위해 모든
transactional ID를 허용하거나 idempotence를 끄지 않습니다.

실제 접근은 다른 정책, 명시적 거부, SCP, permissions boundary와 교차 계정 리소스
정책에도 영향을 받습니다. 이 파일만으로 전체 권한 경계가 완성되지는 않습니다.
`kafka:GetBootstrapBrokers` 등의 제어 영역 작업은 `kafka-cluster:*` 데이터 영역
작업과 다르며 배포·운영 ID에 따로 부여할 수 있습니다.

### Java 클라이언트 설정

`software.amazon.msk:aws-msk-iam-auth:2.3.8`과 의존성을 추가하거나 검증한 릴리스의
all-in-one JAR를 사용합니다. 다음을 `iam.properties`로 저장합니다.

```properties
security.protocol=SASL_SSL
sasl.mechanism=AWS_MSK_IAM
sasl.jaas.config=software.amazon.msk.auth.iam.IAMLoginModule required;
sasl.client.callback.handler.class=software.amazon.msk.auth.iam.IAMClientCallbackHandler
ssl.endpoint.identification.algorithm=https
```

Java에서 OAuth 방식을 선택하면 두 설정을 섞지 말고 다음 대안을 사용합니다.

```properties
security.protocol=SASL_SSL
sasl.mechanism=OAUTHBEARER
sasl.jaas.config=org.apache.kafka.common.security.oauthbearer.OAuthBearerLoginModule required;
sasl.login.callback.handler.class=software.amazon.msk.auth.iam.IAMOAuthBearerLoginCallbackHandler
sasl.client.callback.handler.class=software.amazon.msk.auth.iam.IAMOAuthBearerLoginCallbackHandler
ssl.endpoint.identification.algorithm=https
```

애플리케이션에는 선택한 `bootstrap.servers`, 키·값 직렬화기/역직렬화기와
컨슈머 `group.id`도 필요합니다. JVM이 브로커 TLS 인증서 체인을 신뢰해야 하며
호스트 이름 검증을 유지합니다. 위 속성은 인증 방식을 구성하며 없는 워크로드
자격증명이나 IAM 권한을 만들어 주지는 않습니다.

## MSK Connect: 배포 전 호환성 확인

MSK Connect는 관리형 Kafka Connect 워커를 실행하며 독립적으로 운영하는 Kafka도
대상으로 삼을 수 있습니다. 하지만 **네트워크 접근만으로 충분하지 않습니다**.
현재 `KafkaClusterClientAuthentication` API는 `NONE`과 `IAM`을 허용합니다.
브로커 신뢰·인증과 지원되는 워커 설정이 맞아야 합니다. Part 2의 TLS/SCRAM
Strimzi 리스너는 이름이 조회된다는 이유만으로 바로 연결 가능한 대상이 아닙니다.
연동을 강제하려고 기존 인증을 제거하지 않습니다.

문서화된 Connect 런타임은 **2.7.1 / Java 11**, **3.7.x / Java 17**입니다.
이는 Kafka 브로커 버전이나 Part 5의 Kafka 4.3.1 Connect 런타임과 다릅니다.
플러그인 bytecode·의존성·Connect API와 공급자 지원 표를 확인합니다. Java 17에서
클래스가 로드되어도 선택한 관리형 런타임의 연동 테스트가 필요합니다.

Part 5 아티팩트에는 Java 17을 넘는 기본 클래스가 없지만 **MSK Connect 호환 인증은
아닙니다**. 다음은 이러한 검토를 마친 Aiven 3.4.3 ZIP을 등록하는 예제입니다.
대상 리전의 기존 비공개 S3 버킷과 업로드·플러그인 등록 권한을 전제로 합니다.

```bash
: "${DOCS_AWS_REGION:?Set the target region}"
: "${DOCS_PLUGIN_BUCKET:?Set an existing private S3 bucket in that region}"
DOCS_PLUGIN_ZIP="s3-sink-connector-for-apache-kafka-3.4.3.zip"
DOCS_PLUGIN_KEY="plugins/aiven-s3/3.4.3/${DOCS_PLUGIN_ZIP}"
# Download the reviewed release artifact and verify its published digest first.
aws s3 cp "$DOCS_PLUGIN_ZIP" "s3://${DOCS_PLUGIN_BUCKET}/${DOCS_PLUGIN_KEY}" \
  --region "$DOCS_AWS_REGION"
export DOCS_PLUGIN_BUCKET DOCS_PLUGIN_KEY
python3 - <<'PY'
import json
import os
from pathlib import Path
Path("custom-plugin.json").write_text(json.dumps({
    "name": "aiven-s3-3-4-3-reviewed",
    "contentType": "ZIP",
    "location": {"s3Location": {
        "bucketArn": "arn:aws:s3:::" + os.environ["DOCS_PLUGIN_BUCKET"],
        "fileKey": os.environ["DOCS_PLUGIN_KEY"]
    }}
}, indent=2) + "\n")
PY
aws kafkaconnect create-custom-plugin \
  --region "$DOCS_AWS_REGION" \
  --cli-input-json file://custom-plugin.json
```

이 명령은 **플러그인**을 업로드·등록하며 커넥터를 실행하지 않습니다. 커넥터 생성에는
서비스 실행 역할, Kafka·네트워크 설정, 소스·목적지 권한, 용량과 converter 설정이
필요합니다. MSK Connect의 기본 키·값 converter는 StringConverter이므로 앞의 CDC
예제에 필요한 JSON schema envelope 설정도 명시해야 합니다.

MSK Connect는 플러그인을 만들 때 S3 객체를 복사합니다. 이후 객체를 덮어써도
플러그인이 갱신되지 않으며 custom plugin은 제자리 수정이 불가능합니다. 버전을
구분한 새 플러그인 리소스와 검증한 커넥터 전환 절차를 사용하고 활성 파이프라인을
교체하기 전에 오프셋을 보존·검증합니다. 자동 확장에도 설정된 한계가 있으며
단일 태스크 소스를 자동으로 병렬화하지 않습니다.

## Kafka와 Kinesis Data Streams

Kinesis Data Streams는 자체 API를 사용합니다. `bootstrap.servers`를 Kinesis
주소로 바꿔도 Kafka 클라이언트가 변환되지 않습니다. 커넥터나 명시적인 스트림 처리
계층이 레코드·키·재시도·체크포인트를 연결해야 합니다.

| 항목 | Kafka / MSK / Strimzi | Kinesis Data Streams |
| --- | --- | --- |
| 병렬 처리 | 토픽 파티션; 수를 늘려도 옛 레코드를 재분배하지 않으며 기존 토픽에서 수를 줄이지 못함 | 샤드; Provisioned는 직접 용량 계획, on-demand는 서비스가 용량 관리 |
| 용량 선택 | Standard·Express·Serverless·자체 운영에 따라 다름 | Provisioned, On-demand Standard, On-demand Advantage |
| 보존 | 토픽·서비스 설정, 저장소와 cleanup policy; 시간·크기 제한 모두 확인 | 기본 24시간, 최대 365일까지 설정 |
| AWS 연동 | MSK의 네이티브 Lambda·Firehose 연동과 커넥터 등 | Lambda·Firehose·Managed Service for Apache Flink 네이티브 연동 |

“Kafka는 Connect를 통해서만 AWS와 연동한다”는 설명은 틀립니다. 기존
Kinesis Data Analytics 대신 현재 명칭인 **Amazon Managed Service for Apache Flink**를
사용합니다. Kinesis sink는 Kafka 레코드를 Kinesis에 쓰고 source는 반대로 이동합니다.
유지보수되고 선택한 런타임과 호환되는 플러그인을 고른 뒤 순서, partition key,
레코드 크기 제한과 중복 처리를 검증합니다. 프로토콜 차이가 특정 브리지 제품
하나만 사용해야 한다는 뜻은 아닙니다.

## 선택 기준

필요한 Kafka API, 데이터량·편중, 파티션·보존 한계, 지연, 복구 목표, 규정, 운영 역량과
총비용부터 비교합니다. 현재 리전·브로커 버전 지원을 확인합니다. MSK와 Strimzi 모두
IaC/GitOps로 관리할 수 있습니다. 나중에 서비스를 바꾸려면 데이터·스키마·인증·
컨슈머 오프셋 이전이 필요하며 자동으로 간단하거나 흔한 다음 단계라고 단정하지 않습니다.

## 참고 자료와 검증 범위

정책 생성, Java 클래스·JAAS 설정, 플러그인 bytecode와 CLI 요청 형식은 로컬에서
검사할 수 있습니다. 이 검사는 실제 IAM 허용, 워크로드 자격증명 갱신, 브로커 접속,
관리형 커넥터 배포나 데이터 전달의 성공을 의미하지 않습니다.

- [MSK Express brokers](https://docs.aws.amazon.com/msk/latest/developerguide/msk-broker-types-express.html)
- [MSK Serverless](https://docs.aws.amazon.com/msk/latest/developerguide/serverless.html)
- [Serverless configuration](https://docs.aws.amazon.com/msk/latest/developerguide/serverless-config.html)
- [MSK pricing dimensions](https://aws.amazon.com/msk/pricing/)
- [MSK multi-VPC private connectivity](https://docs.aws.amazon.com/msk/latest/developerguide/aws-access-mult-vpc.html)
- [MSK port information](https://docs.aws.amazon.com/msk/latest/developerguide/port-info.html)
- [IAM client mechanisms and official language helpers](https://docs.aws.amazon.com/msk/latest/developerguide/configure-clients-for-iam-access-control.html)
- [MSK IAM action/resource dependencies](https://docs.aws.amazon.com/msk/latest/developerguide/kafka-actions.html)
- [IAM use cases](https://docs.aws.amazon.com/msk/latest/developerguide/iam-access-control-use-cases.html)
- [aws-msk-iam-auth 2.3.8](https://github.com/aws/aws-msk-iam-auth/tree/v2.3.8)
- [MSK Connect](https://docs.aws.amazon.com/msk/latest/developerguide/msk-connect.html)
- [MSK Connect plugin packaging and Java versions](https://docs.aws.amazon.com/msk/latest/developerguide/msk-connect-plugins.html)
- [MSK Connect client authentication API](https://docs.aws.amazon.com/MSKC/latest/mskc/API_KafkaClusterClientAuthentication.html)
- [Lambda with MSK](https://docs.aws.amazon.com/lambda/latest/dg/with-msk.html)
- [Firehose with MSK](https://docs.aws.amazon.com/msk/latest/developerguide/integrations-kinesis-data-firehose.html)
- [Kinesis capacity modes](https://docs.aws.amazon.com/streams/latest/dev/how-do-i-size-a-stream.html)
- [Kinesis retention](https://docs.aws.amazon.com/streams/latest/dev/kinesis-extended-retention.html)

## 다음 단계

[Part 7: 모니터링](./07-monitoring.md)

[메인 페이지로 돌아가기](./README.md)

## 퀴즈

[주제 퀴즈](../../quizzes/data-on-eks/kafka/06-msk-integration-quiz.md)
