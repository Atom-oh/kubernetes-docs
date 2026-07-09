# MSK 통합 퀴즈

이 퀴즈는 Amazon MSK와 Strimzi 셀프 매니지드의 트레이드오프, EKS-MSK 연결 방식, MSK Connect, Kinesis Data Streams와의 차이점에 대한 이해도를 테스트합니다.

## 객관식 문제

1. Amazon MSK와 EKS 위의 Strimzi 셀프 매니지드 사이의 가장 근본적인 차이는 무엇인가요?
   - A) MSK는 Kafka 프로토콜을 사용하지 않는다
   - B) 브로커가 실제로 실행되는 위치와 이를 운영하는 책임 주체가 다르다
   - C) Strimzi는 Kubernetes에서 실행할 수 없다
   - D) MSK는 파티션 개념을 지원하지 않는다

<details>

<summary>정답 보기</summary>

**정답: B) 브로커가 실제로 실행되는 위치와 이를 운영하는 책임 주체가 다르다**

**설명:**
MSK는 브로커를 AWS가 관리하는 인프라에서 실행하며 패치, 하드웨어 교체, 스토리지 확장 등을 AWS가 대신 수행합니다. Strimzi는 브로커를 EKS 클러스터 내부의 Pod로 실행하며, Operator가 롤링 업그레이드나 조정을 자동화하더라도 업그레이드 시점 결정, 용량 계획, 장애 대응의 최종 책임은 사용자에게 있습니다. 두 방식 모두 Apache Kafka 프로토콜을 그대로 구현하므로 프로토콜 자체의 차이는 없습니다.
</details>

2. MSK Serverless의 특징으로 옳은 것은 무엇인가요?
   - A) 브로커 설정(`server.properties`)을 자유롭게 커스터마이징할 수 있다
   - B) 브로커 사이징 개념이 사용자에게 노출되지 않고 처리량 기반으로 과금된다
   - C) ZooKeeper 기반으로만 동작한다
   - D) MSK Provisioned보다 항상 더 저렴하다

<details>

<summary>정답 보기</summary>

**정답: B) 브로커 사이징 개념이 사용자에게 노출되지 않고 처리량 기반으로 과금된다**

**설명:**
MSK Serverless는 파티션 단위로 완전 자동 확장되며, 사용자는 브로커 개수나 인스턴스 타입을 신경 쓸 필요가 없습니다. 대신 파티션당, 인입/유출 GB당 처리량 기반으로 과금됩니다. 커스텀 브로커 설정은 지원되지 않으며 일부 API/기능(특정 ACL, 커넥터 유형 등)에 제한이 있습니다. 트래픽 패턴에 따라 Provisioned보다 비쌀 수도 저렴할 수도 있으므로 항상 더 저렴하다고 단정할 수 없습니다.
</details>

3. EKS 파드가 MSK 브로커에 IAM 자격 증명을 별도로 배포하지 않고 인증하려면 어떤 조합이 필요한가요?
   - A) SASL/SCRAM과 Secrets Manager
   - B) IRSA와 `AWS_MSK_IAM` SASL 메커니즘
   - C) mTLS와 AWS Private CA
   - D) 플레인텍스트 리스너와 보안 그룹만

<details>

<summary>정답 보기</summary>

**정답: B) IRSA와 `AWS_MSK_IAM` SASL 메커니즘**

**설명:**
IRSA(IAM Roles for Service Accounts)로 파드에 IAM 역할을 부여하고, Kafka 클라이언트에서 `sasl.mechanism=AWS_MSK_IAM`을 설정하면 클라이언트가 SigV4 서명된 요청으로 인증합니다. 이 방식은 비밀번호나 인증서 같은 별도의 자격 증명을 배포·로테이션할 필요가 없다는 점이 핵심 장점입니다. SASL/SCRAM과 mTLS도 유효한 인증 방식이지만 각각 Secrets Manager의 자격 증명 동기화나 인증서 발급·마운트가 추가로 필요합니다.
</details>

4. EKS 워크로드가 다른 VPC에 있는 MSK 클러스터에 연결해야 할 때 필요한 네트워크 구성은 무엇인가요?
   - A) 항상 MSK를 퍼블릭 액세스로 전환해야 한다
   - B) VPC 피어링 또는 AWS Transit Gateway로 두 VPC를 연결해야 한다
   - C) Kafka 프로토콜은 VPC 경계를 자동으로 넘을 수 있다
   - D) NAT 게이트웨이만 있으면 별도 설정이 필요 없다

<details>

<summary>정답 보기</summary>

**정답: B) VPC 피어링 또는 AWS Transit Gateway로 두 VPC를 연결해야 한다**

**설명:**
EKS 클러스터와 MSK 클러스터가 다른 VPC에 있다면 VPC 피어링 또는 Transit Gateway로 두 VPC 간 라우팅을 구성해야 합니다. MSK는 퍼블릭 액세스를 지원하지만 이는 별도의 선택 사항이며 프로덕션에서는 보안상 프라이빗 연결이 권장됩니다. 네트워크 경로가 확보되어도 MSK 클러스터 보안 그룹이 EKS 노드/파드 보안 그룹으로부터의 인바운드를 허용하지 않으면 여전히 연결이 차단됩니다.
</details>

5. MSK 클러스터의 보안 그룹 설정에 대한 설명 중 옳은 것은 무엇인가요?
   - A) 기본적으로 같은 VPC 내 모든 트래픽을 허용한다
   - B) EKS 노드(또는 파드) 보안 그룹으로부터 브로커 포트에 대한 인바운드를 명시적으로 허용해야 한다
   - C) 보안 그룹은 IAM 인증을 사용할 때는 필요하지 않다
   - D) 보안 그룹 설정은 MSK Serverless에만 적용된다

<details>

<summary>정답 보기</summary>

**정답: B) EKS 노드(또는 파드) 보안 그룹으로부터 브로커 포트에 대한 인바운드를 명시적으로 허용해야 한다**

**설명:**
MSK 클러스터 보안 그룹은 기본적으로 아무 인바운드 트래픽도 허용하지 않습니다. EKS 워커 노드(또는 파드별 보안 그룹을 사용하는 경우 파드) 보안 그룹을 소스로 지정해 필요한 브로커 포트(플레인텍스트 9092, TLS 9094, SASL/SCRAM 9096, IAM 9098)에 대한 인바운드 규칙을 명시적으로 추가해야 합니다. 인증 방식(IAM, SCRAM, mTLS)과 무관하게 네트워크 계층의 보안 그룹 규칙은 별도로 필요합니다.
</details>

6. MSK Connect에 대한 설명으로 옳은 것은 무엇인가요?
   - A) MSK 클러스터에만 연결할 수 있으며 다른 Kafka 클러스터에는 사용할 수 없다
   - B) 부트스트랩 브로커에 네트워크로 도달할 수 있다면 EKS 위의 Strimzi 클러스터에도 커넥터를 연결할 수 있다
   - C) Kafka Connect 워커의 스케일링과 패치를 사용자가 직접 관리해야 한다
   - D) 커넥터 플러그인은 컨테이너 이미지로만 등록할 수 있다

<details>

<summary>정답 보기</summary>

**정답: B) 부트스트랩 브로커에 네트워크로 도달할 수 있다면 EKS 위의 Strimzi 클러스터에도 커넥터를 연결할 수 있다**

**설명:**
MSK Connect는 MSK 전용 서비스가 아닙니다. 커넥터가 부트스트랩 브로커에 네트워크로 도달할 수만 있으면, EKS에서 Strimzi로 셀프 매니지드하는 Kafka 클러스터를 포함해 어떤 Kafka 클러스터에도 연결할 수 있습니다. Connect 워커 인프라의 프로비저닝, 스케일링, 패치는 AWS가 관리하므로 사용자가 직접 관리할 필요가 없습니다. 커스텀 커넥터 플러그인은 JAR을 묶은 ZIP 파일을 S3에 업로드해 등록합니다.
</details>

7. Kafka와 Kinesis Data Streams의 관계에 대해 옳게 설명한 것은 무엇인가요?
   - A) MSK가 "Kafka 호환"이므로 Kinesis 클라이언트로 MSK에 직접 접속할 수 있다
   - B) Kafka와 Kinesis는 서로 다른 프로토콜을 사용하는 별개의 서비스이며 직접 호환되지 않는다
   - C) Kinesis는 내부적으로 Kafka 프로토콜을 그대로 구현한 서비스이다
   - D) Kafka 클라이언트는 설정만 바꾸면 Kinesis 스트림에 바로 연결된다

<details>

<summary>정답 보기</summary>

**정답: B) Kafka와 Kinesis는 서로 다른 프로토콜을 사용하는 별개의 서비스이며 직접 호환되지 않는다**

**설명:**
Kinesis Data Streams는 AWS 전용 API/SDK를 사용하는 완전히 별개의 서비스로, Kafka 프로듀서/컨슈머 프로토콜을 이해하지 못합니다. MSK가 "Kafka 호환"이라는 표현을 쓰는 것은 MSK가 Apache Kafka 프로토콜을 구현했다는 의미일 뿐, Kinesis와의 상호 운용성을 뜻하지 않습니다. 두 시스템을 연동하려면 Kafka Connect(또는 MSK Connect)의 Kinesis 싱크/소스 커넥터 같은 별도의 브리징 계층이 필요합니다.
</details>

8. Kafka와 Kinesis Data Streams를 실질적으로 연동하는 올바른 방법은 무엇인가요?
   - A) Kafka 클라이언트의 `bootstrap.servers`를 Kinesis 엔드포인트로 변경한다
   - B) Kafka Connect 또는 MSK Connect의 Kinesis 싱크/소스 커넥터를 사용한다
   - C) MSK 클러스터를 Kinesis 모드로 전환하는 설정 플래그를 사용한다
   - D) 둘 다 같은 파티션 모델을 쓰므로 별도 연동 없이 상호 참조 가능하다

<details>

<summary>정답 보기</summary>

**정답: B) Kafka Connect 또는 MSK Connect의 Kinesis 싱크/소스 커넥터를 사용한다**

**설명:**
Kafka와 Kinesis는 프로토콜이 호환되지 않으므로, 둘을 연동하려면 브리징 역할을 하는 커넥터가 필요합니다. Kinesis 싱크 커넥터는 Kafka 토픽의 메시지를 Kinesis 스트림에 기록하고, Kinesis 소스 커넥터는 Kinesis 스트림의 레코드를 Kafka 토픽에 기록합니다. 이 커넥터는 MSK Connect에 배포하거나 Strimzi `KafkaConnect`/`KafkaConnector` CR로 EKS 위에서 직접 운영할 수 있습니다.
</details>

9. 다음 중 EKS에서 Strimzi로 Kafka를 직접 운영하는 것이 여전히 타당한 이유가 아닌 것은 무엇인가요?
   - A) 나머지 플랫폼과 동일한 GitOps/관측 파이프라인에 Kafka를 통합하고 싶다
   - B) 온프레미스나 멀티클라우드로 이전 가능한 이식성이 필요하다
   - C) MSK가 아직 지원하지 않는 최신 Kafka 기능이 필요하다
   - D) 브로커 운영 인력을 전혀 두고 싶지 않다

<details>

<summary>정답 보기</summary>

**정답: D) 브로커 운영 인력을 전혀 두고 싶지 않다**

**설명:**
Strimzi 셀프 매니지드는 Operator가 많은 작업을 자동화하지만 업그레이드 시점 결정, 용량 계획, 장애 대응 등은 여전히 사용자의 책임입니다. 브로커 운영 부담을 완전히 없애고 싶다면 오히려 MSK(특히 MSK Serverless)가 더 적합한 선택입니다. GitOps 통합, 이식성, 최신 기능 채택은 실제로 Strimzi를 EKS에서 직접 운영하는 타당한 이유들입니다.
</details>

10. 다음 중 MSK Provisioned와 Strimzi 셀프 매니지드의 비용 모델 차이를 가장 정확하게 설명한 것은 무엇인가요?
    - A) MSK는 항상 Strimzi보다 저렴하다
    - B) MSK는 브로커 시간당 요금과 스토리지 비용으로 과금되고, Strimzi는 EC2/EBS 직접 비용에 운영 인력 비용이 별도로 필요하다
    - C) Strimzi는 과금 방식이 없고 완전히 무료다
    - D) 두 방식의 비용 모델은 동일하다

<details>

<summary>정답 보기</summary>

**정답: B) MSK는 브로커 시간당 요금과 스토리지 비용으로 과금되고, Strimzi는 EC2/EBS 직접 비용에 운영 인력 비용이 별도로 필요하다**

**설명:**
MSK Provisioned는 브로커 시간당 요금, 스토리지(GB-월), 데이터 전송 비용으로 과금됩니다. Strimzi는 EC2/EBS 인프라 비용을 직접 지불하며, 대규모에서는 보통 더 저렴하지만 이를 운영할 인력 비용이 별도로 발생합니다. 어느 쪽이 총소유비용(TCO) 측면에서 더 유리한지는 트래픽 규모, 조직의 운영 역량, 인건비 등에 따라 달라집니다.
</details>

## 단답형 문제

11. EKS 파드가 IAM 역할을 사용해 MSK에 SASL로 인증할 때 사용하는 SASL 메커니즘의 정확한 이름은 무엇인가요?

<details>

<summary>정답 보기</summary>

**정답: `AWS_MSK_IAM`**

**설명:**
`AWS_MSK_IAM`은 MSK가 제공하는 SASL 메커니즘으로, 클라이언트가 SigV4 서명 기반의 자격 증명(IAM 역할 또는 사용자)으로 인증할 수 있게 합니다. 클라이언트 설정에서 `security.protocol=SASL_SSL`, `sasl.mechanism=AWS_MSK_IAM`을 지정하고, `aws-msk-iam-auth` 라이브러리가 제공하는 `IAMLoginModule`과 `IAMClientCallbackHandler`를 JAAS 설정과 콜백 핸들러로 등록합니다.
</details>

12. MSK 클라이언트가 IAM 인증을 사용하기 위해 클래스패스(또는 해당 언어의 패키지 관리자)에 추가해야 하는 라이브러리의 이름은 무엇인가요?

<details>

<summary>정답 보기</summary>

**정답: `aws-msk-iam-auth`**

**설명:**
`aws-msk-iam-auth`는 AWS가 제공하는 클라이언트 라이브러리로, Kafka 클라이언트가 SigV4 서명 요청을 생성해 IAM 자격 증명으로 MSK 브로커에 인증할 수 있도록 `AWS_MSK_IAM`이라는 전용 커스텀 SASL 메커니즘(OAUTHBEARER 확장이 아님)을 구현합니다. Java 클라이언트는 Maven 아티팩트로 제공되며, 다른 언어(Python, Go 등)에도 동등한 커뮤니티 구현체가 존재합니다.
</details>

13. AWS의 완전관리형 Kafka Connect 서비스로, 커넥터 워커의 프로비저닝과 스케일링을 AWS가 대신 처리하는 서비스의 이름은 무엇인가요?

<details>

<summary>정답 보기</summary>

**정답: MSK Connect**

**설명:**
MSK Connect는 Kafka Connect 워커 클러스터의 프로비저닝, 스케일링, 패치를 AWS가 관리하는 서비스입니다. 사용자는 커넥터 플러그인(JAR을 묶은 ZIP)을 S3에 업로드하고 커넥터 설정을 등록하기만 하면 됩니다. MSK 클러스터뿐 아니라 네트워크로 도달 가능한 어떤 Kafka 클러스터(EKS의 Strimzi 클러스터 포함)에도 연결할 수 있습니다.
</details>

14. Kafka의 확장 단위인 "파티션"에 대응하는 Kinesis Data Streams의 확장 단위는 무엇인가요?

<details>

<summary>정답 보기</summary>

**정답: 샤드(Shard)**

**설명:**
Kafka는 토픽을 여러 파티션으로 나누어 병렬 처리와 확장성을 확보하며, 파티션 수는 토픽 생성 시 정의되고 이후 재파티셔닝으로 조정할 수 있습니다. Kinesis는 대신 샤드 단위로 읽기/쓰기 용량을 나누며, 샤드 분할(split)과 병합(merge)을 통해 처리 용량을 조정합니다. 두 개념은 유사한 목적을 갖지만 API와 운영 방식이 서로 다릅니다.
</details>

15. Kafka 토픽의 메시지를 읽어 Kinesis 스트림에 기록하는 역할을 하는 Kafka Connect 커넥터의 종류를 무엇이라고 부르나요?

<details>

<summary>정답 보기</summary>

**정답: Kinesis Sink 커넥터**

**설명:**
Kinesis Sink 커넥터는 Kafka 토픽을 소스로 하여 메시지를 읽고 Kinesis 스트림에 기록합니다. 반대로 Kinesis Source 커넥터는 Kinesis 스트림의 레코드를 읽어 Kafka 토픽에 기록합니다. 이 두 커넥터는 Kafka와 Kinesis 사이에 프로토콜 호환성이 없다는 것을 전제로, 실제 데이터 브리징을 담당하는 계층입니다.
</details>

## 실습 문제

16. EKS 워커 노드 보안 그룹(`sg-0efgh5678eksnode`)에서 MSK 클러스터 보안 그룹(`sg-0abcd1234msk`)의 IAM 인증 포트로 인바운드를 허용하는 AWS CLI 명령어를 작성하세요.

<details>

<summary>정답 보기</summary>

**정답:**
```bash
aws ec2 authorize-security-group-ingress \
  --group-id sg-0abcd1234msk \
  --protocol tcp --port 9098 \
  --source-group sg-0efgh5678eksnode
```

**설명:**
MSK의 IAM 인증 포트는 9098입니다. `authorize-security-group-ingress` 명령어의 `--group-id`에는 규칙을 추가할 대상(MSK 보안 그룹)을, `--source-group`에는 트래픽을 허용할 소스(EKS 노드 보안 그룹)를 지정합니다. 이 규칙이 없으면 IAM 인증 자체가 성공하더라도 TCP 연결 단계에서 차단됩니다. 다른 인증 방식을 쓴다면 포트도 그에 맞게 변경해야 합니다(TLS: 9094, SASL/SCRAM: 9096).
</details>

17. IAM 인증을 사용하는 Kafka 클라이언트가 특정 MSK 클러스터의 `orders` 토픽에 대해서만 읽기/쓰기를 허용받도록 하는 IAM 정책 JSON을 작성하세요.

<details>

<summary>정답 보기</summary>

**정답:**
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "kafka-cluster:Connect",
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

**설명:**
첫 번째 Statement는 클러스터에 연결하고 상태를 조회할 수 있는 최소 권한(`Connect`, `DescribeCluster`)을 부여합니다. 두 번째 Statement는 리소스 ARN을 `topic/my-msk-cluster/*/orders`로 한정해 `orders` 토픽에 대해서만 토픽 관련 작업, 쓰기(`WriteData`), 읽기(`ReadData`) 권한을 부여합니다. 이렇게 리소스 ARN을 토픽 단위로 좁히면 동일한 클러스터의 다른 토픽에는 접근할 수 없습니다.
</details>

18. `AWS_MSK_IAM` 메커니즘을 사용하도록 Kafka 클라이언트를 설정하는 클라이언트 설정 파일(properties)을 작성하세요.

<details>

<summary>정답 보기</summary>

**정답:**
```properties
security.protocol=SASL_SSL
sasl.mechanism=AWS_MSK_IAM
sasl.jaas.config=software.amazon.msk.auth.iam.IAMLoginModule required;
sasl.client.callback.handler.class=software.amazon.msk.auth.iam.IAMClientCallbackHandler
```

**설명:**
`security.protocol=SASL_SSL`은 SASL 인증과 TLS 암호화를 함께 사용하도록 지정합니다. `sasl.mechanism=AWS_MSK_IAM`은 IAM 기반 SASL 메커니즘을 선택합니다. `sasl.jaas.config`는 `aws-msk-iam-auth` 라이브러리의 `IAMLoginModule`을 JAAS 로그인 모듈로 등록하며, `sasl.client.callback.handler.class`는 SigV4 서명 요청을 생성하는 콜백 핸들러를 지정합니다. 이 설정만으로 클라이언트는 로컬 자격 증명 체인(IRSA로 주입된 IAM 역할 포함)을 사용해 자동으로 인증합니다.
</details>

---

[학습 자료로 돌아가기](../../../data-on-eks/kafka/06-msk-integration.md) | [다음 퀴즈: 모니터링](./07-monitoring-quiz.md)
