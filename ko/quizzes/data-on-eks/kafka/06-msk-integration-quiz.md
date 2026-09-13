# MSK 통합 퀴즈

MSK 유형, IAM·네트워크, MSK Connect와 Kinesis 비교를 확인합니다.

## 1. MSK와 EKS의 Strimzi는 무엇이 다르며 어떤 책임이 공통으로 남나요?

<details>
<summary>정답 보기</summary>

MSK는 EKS 밖의 AWS 관리 인프라, Strimzi는 팀이 운영하는 Kubernetes에서 브로커를 실행합니다. 어느 쪽이든 애플리케이션, 토픽·보존, 접근 제어와 복구 설계는 필요합니다.

</details>

## 2. MSK Serverless 과금에서 처리량 외에 놓치기 쉬운 항목은 무엇인가요?

<details>
<summary>정답 보기</summary>

클러스터 시간, 파티션 시간과 사용 저장소입니다. 데이터 입력·출력과 해당 네트워크 비용도 포함합니다. 자동 확장에도 서비스 할당량이 있으며 항상 가장 저렴하지는 않습니다.

</details>

## 3. EKS Pod가 MSK IAM 인증을 사용하려면 어떤 인증 경로가 필요한가요?

<details>
<summary>정답 보기</summary>

Pod Identity 또는 IRSA 등의 역할·신뢰 설정, 임시 자격증명 체인·갱신, 지원되는 Kafka helper, 네트워크·TLS와 데이터 영역 권한이 필요합니다. External Secrets Operator나 노드 역할 상속만으로 대신하지 않습니다.

</details>

## 4. 다른 VPC에서 MSK에 연결하는 방법은 피어링과 Transit Gateway뿐인가요?

<details>
<summary>정답 보기</summary>

아닙니다. 지원되는 MSK multi-VPC private connectivity(PrivateLink)도 있습니다. 같은 리전·인증·AZ/서브넷 조건과 실제 엔드포인트를 확인합니다. 공개 접근이 필수는 아닙니다.

</details>

## 5. 같은 VPC이고 IAM 정책이 있으면 바로 연결되나요?

<details>
<summary>정답 보기</summary>

아닙니다. DNS, 라우트, SG, NACL, egress, 실제 소스 ID와 모든 광고된 브로커 주소를 확인해야 합니다. TCP/TLS 연결 전에 IAM 인증은 성공하지 않으며 기존 SG 규칙도 조사합니다.

</details>

## 6. MSK Connect가 네트워크로 보이는 모든 Strimzi 리스너에 바로 연결되나요?

<details>
<summary>정답 보기</summary>

아닙니다. 현재 클러스터 인증 API는 NONE/IAM을 제공하며 브로커 신뢰·인증·워커 설정이 맞아야 합니다. 앞 장의 TLS/SCRAM 리스너에 단순히 주소만 지정하면 된다고 가정하지 않습니다.

</details>

## 7. Kafka의 bootstrap.servers를 Kinesis 주소로 바꾸면 호환되나요?

<details>
<summary>정답 보기</summary>

아닙니다. Kinesis Data Streams는 자체 API를 사용합니다. 커넥터나 스트림 처리 계층에서 키·레코드·재시도·체크포인트를 연결해야 합니다.

</details>

## 8. Kafka는 Connect를 통해서만 Lambda·Firehose와 연동하나요?

<details>
<summary>정답 보기</summary>

아닙니다. MSK에는 네이티브 Lambda·Firehose 연동도 있습니다. Kafka/Kinesis 간 데이터 브리지는 별도 문제이며 런타임·형식·순서·중복 처리를 검증합니다.

</details>

## 9. GitOps를 사용하려면 MSK 대신 Strimzi를 선택해야 하나요?

<details>
<summary>정답 보기</summary>

아닙니다. MSK도 API·IaC를 GitOps 흐름에 통합할 수 있습니다. Strimzi를 선택할 때는 필요한 설정·이식성과 운영 역량을 따지고 스토리지·네트워크·인증의 환경 의존성도 고려합니다.

</details>

## 10. MSK Express는 Serverless와 무엇이 다른가요?

<details>
<summary>정답 보기</summary>

Express는 Provisioned의 브로커 유형으로 브로커 컴퓨팅을 선택하고 자동 확장되는 사용량 기반 저장소를 사용합니다. 현재 3개 AZ와 기능 제한을 확인해야 합니다. 브로커 시간·data-in·저장소 등 비용을 포함해 비교합니다.

</details>

## 11. Java와 비 Java 클라이언트가 사용할 수 있는 MSK IAM SASL 메커니즘은 무엇인가요?

<details>
<summary>정답 보기</summary>

Java는 AWS_MSK_IAM 또는 OAUTHBEARER를 사용할 수 있습니다. Python·JavaScript·Go·.NET은 공식 AWS signer/helper와 OAUTHBEARER를 사용합니다. AWS_MSK_IAM을 모든 언어에 공통으로 설정하지 않습니다.

</details>

## 12. aws-msk-iam-auth 라이브러리만 추가하면 IAM 인증이 완성되나요?

<details>
<summary>정답 보기</summary>

아닙니다. Java helper는 설정된 인증 방식을 구현합니다. 실제 역할 자격증명·갱신, 신뢰 관계, 데이터 권한, 네트워크와 TLS가 필요합니다. 비 Java는 언어별 공식 helper를 선택합니다.

</details>

## 13. MSK Connect의 런타임 버전과 플러그인 갱신에서 주의할 점은 무엇인가요?

<details>
<summary>정답 보기</summary>

문서화된 조합은 Connect 2.7.1/Java 11, 3.7.x/Java 17입니다. 브로커 버전과 다르며 bytecode뿐 아니라 의존성과 API도 검증합니다. 플러그인은 생성 시 S3 객체를 복사하므로 객체 덮어쓰기로 갱신되지 않습니다.

</details>

## 14. Kafka 파티션 수 증가와 Kinesis 용량 모드를 비교하세요.

<details>
<summary>정답 보기</summary>

Kafka 파티션을 늘려도 옛 레코드가 자동 재분배되지 않고 기존 토픽의 파티션 수를 줄이지 못합니다. Kinesis는 샤드를 사용하며 Provisioned, On-demand Standard, On-demand Advantage 모드를 구분합니다.

</details>

## 15. Serverless의 기본 보존을 7일만으로 해석하면 안 되는 이유는 무엇인가요?

<details>
<summary>정답 보기</summary>

기본 retention.bytes가 파티션당 250 GiB이므로 크기 제한에 먼저 도달할 수 있습니다. 시간·크기·cleanup policy와 서비스 제약을 함께 확인합니다. Kinesis Data Streams의 보존은 기본 24시간, 최대 365일입니다.

</details>

## 16. 같은 VPC의 프라이빗 IPv4 IAM 연결을 위한 SG 명령을 작성하고 적용 범위를 설명하세요.

<details>
<summary>정답 보기</summary>

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

실제 노드·Pod 소스 SG를 사용하며 기존 규칙을 먼저 확인합니다. IPv6·공개·multi-VPC 주소는 포트가 다를 수 있으므로 bootstrap 응답을 확인합니다. 명령은 SG를 변경합니다.

</details>

## 17. orders 토픽과 orders-consumer 그룹용 생산자·소비자 IAM 정책에는 어떤 권한이 필요한가요?

<details>
<summary>정답 보기</summary>

본문의 policies.py로 정확한 클러스터 ARN·UUID에서 정책을 생성합니다. 생산자는 cluster의 Connect/WriteDataIdempotently와 orders의 DescribeTopic/WriteData, 소비자는 cluster Connect와 orders의 DescribeTopic/ReadData 및 해당 group의 DescribeGroup/AlterGroup을 사용합니다. AlterCluster나 *Topic*은 필요하지 않습니다. 트랜잭션은 별도 범위의 transactional-ID 권한을 설계합니다.

</details>

## 18. Java AWS_MSK_IAM 설정을 작성하고 아직 필요한 구성을 설명하세요.

<details>
<summary>정답 보기</summary>

```properties
security.protocol=SASL_SSL
sasl.mechanism=AWS_MSK_IAM
sasl.jaas.config=software.amazon.msk.auth.iam.IAMLoginModule required;
sasl.client.callback.handler.class=software.amazon.msk.auth.iam.IAMClientCallbackHandler
ssl.endpoint.identification.algorithm=https
```

선택한 bootstrap.servers, serializer/deserializer와 소비자 group.id를 추가합니다. JVM의 CA 신뢰, 워크로드 자격증명, IAM 권한과 네트워크가 필요합니다. 호스트 이름 검증을 끄지 않습니다.

</details>

---

[학습 자료로 돌아가기](../../../data-on-eks/kafka/06-msk-integration.md) | [다음 퀴즈](./07-monitoring-quiz.md)
