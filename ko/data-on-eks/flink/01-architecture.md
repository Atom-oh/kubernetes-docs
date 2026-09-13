# Part 1: Kubernetes에서의 Flink 아키텍처

> 검토: 2026-09-12. 연동 예제 기준: Flink 2.2.1 / Java 17 / Operator 1.15.0.

이 장은 cluster 역할과 자원 계산을 설명합니다. 현재 지원되는 EKS/Kubernetes,
호환 kubectl, Flink 배포판과 client 접근을 준비합니다. 설치·ServiceAccount·RBAC와
Operator CR은 Part 2에서 다룹니다. 오래된 Kubernetes 최소값을 현재 지원 표로
사용하지 않습니다.

## 1. JobManager, TaskManager와 client

| 역할 | 책임 |
| --- | --- |
| Client | 제출 경로에 따라 application main()을 실행해 graph를 만들거나 cluster에 application 실행을 요청 |
| JobManager | Dispatcher·ResourceManager·job별 JobMaster 등으로 제출·slot 할당·실행·checkpoint·복구를 조정 |
| TaskManager | Task를 thread에서 실행하고 데이터 교환·buffering·상태 처리를 수행 |
| Kubernetes ResourceManager | Native 모드에서 Kubernetes API를 통해 TaskManager Pod를 요청·해제 |

JobManager가 모든 배포 모드에서 항상 최초 job graph를 만든다는 설명은 정확하지
않습니다. Application 모드에서는 main()이 JobManager에서 실행되며, 일반적인
2.2 Session CLI 제출에서는 client 측에서 graph를 구성합니다.
일반적인 operator record 처리는 TaskManager에 있지만 application의 main()은
임의의 사용자 코드이므로 JobManager를 무조건 가벼운 프로세스로 가정하지 않습니다.

### Slot·operator chaining·slot sharing

Task slot은 TaskManager의 자원 할당 단위입니다. 고전적인 fixed-slot 설정은 managed
memory를 나누지만 **slot만으로 CPU isolation을 제공하지 않습니다**.
각 TaskManager는 JVM 프로세스이며 여러 task thread가 이를 공유할 수 있습니다.

Flink는 여러 operator subtask를 하나의 task/thread로 **chain**할 수 있고, 같은 job의
서로 다른 task도 **slot sharing group**을 통해 slot을 공유할 수 있습니다.
따라서 “4 slots = 최대 4 operator subtasks”는 틀립니다.

| 예제 조건 | 필요한 slot의 단순 계산 |
| --- | --- |
| 같은 sharing group의 source(4) → map(4) → sink(2) | 최대 parallelism인 4 slots에 배치 가능 |
| source/map은 group A, sink는 group B | 두 group을 동시에 실행하면 4 + 2 = 6 slots 필요 |

이는 group/resource 조건이 맞는 단순한 stream 예시입니다. Batch scheduling,
fine-grained resource profile, 다른 job과의 경쟁, chaining 설정은 별도로 고려합니다.
2 slots/TM라면 4 slots는 최소 2 TMs, 6 slots는 최소 3 TMs라는 slot 용량 계산이
나오지만 실제 CPU·network·state 크기와 여유 용량까지 충족해야 합니다.

![Native Flink roles, checkpoint coordination and task slots that can share operator tasks.](../../.gitbook/assets/ko-data-on-eks-flink-01-architecture-0.png)

[Interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/ko-data-on-eks-flink-01-architecture-0.html)

## 2. Application/Session은 cluster 수명과 공유의 선택

| 모드 | main()과 cluster 수명 | 운영상 경계 |
| --- | --- | --- |
| Application | 한 application을 위한 cluster에서 main() 실행; application 수명에 연결 | 한 main()에서 여러 job을 만들 수도 있어 “job마다 무조건 별도 cluster”와 다름 |
| Session | 기존 cluster에 application/job을 제출; 일반적인 2.2 CLI는 client에서 main() 실행 | 여러 job이 JM/TM 용량을 공유하며 한 TM 장애가 여러 job에 영향을 줄 수 있음 |

Application은 application 사이의 JVM·lifecycle 분리에 유리하지만 공유 EKS node,
network·storage·API quota까지 완전히 격리하지 않습니다. 한 application 안의 여러
job도 같은 cluster를 공유합니다. 이 기준선의 2.2 문서는 Application HA를
single-execute application으로 제한하므로 multi-job을 사용할 때 버전별 조건을
확인합니다. 2.3의 개선을 2.2 예제에 소급하지 않습니다.

Session은 이미 확보된 자원을 이용해 cluster 시작 비용을 줄일 수 있지만, 남는
slot이 없으면 즉시 실행되지 않으며 공유 장애·경합을 고려해야 합니다.

Per-Job은 과거 client-side graph 제출 후 job 전용 cluster를 만드는 모델입니다.
Native Kubernetes의 선택지로 제공되지 않으며, 이 장의 현재 Kubernetes 모드는
Application/Session입니다. 이를 현재 지원되는 세 가지 모드로 세지 않습니다.

## 3. Native/Standalone은 자원 관리 주체의 별도 축

Application/Session과 Native/Standalone은 같은 분류가 아닙니다.
Operator 1.15.0은 Application/Session cluster와 **Native/Standalone 배포**를 지원합니다.

| 항목 | Native | Standalone |
| --- | --- | --- |
| TM Pod 관리 | JM의 Kubernetes ResourceManager가 API로 요청·해제 | Operator 등 외부 관리자가 Kubernetes 자원을 조정 |
| Flink runtime의 권한 | Native 자원 관리에 필요한 Kubernetes API 권한 필요 | 외부 자원 관리가 가능하지만 HA 등 추가 기능의 API 권한은 별도 검토 |
| Replica 변경 | Flink의 slot 요청·idle 정책·상한에 따름 | Operator/외부 controller로 변경 가능; 수동 YAML 수정만 가능한 방식이 아님 |

Native가 기본 권장 경로이지만 Standalone을 단순히 폐기된 모드로 부르지 않습니다.
Operator CR의 spec.mode로 선택하며, Kubernetes 자원 생성 권한을 어디에 둘지와
필요 기능의 제한을 검토합니다. 이 차이가 모든 Kubernetes API 접근을 자동 제거하거나
신뢰하지 않는 코드를 완전히 격리하는 것은 아닙니다.

Native에서도 TaskManager는 필요 slot뿐 아니라 resource profile·상한·idle timeout에
따라 관리됩니다. 2.2.1의 resourcemanager.taskmanager-timeout 기본값은 30초입니다.
Job 완료·parallelism 감소와 동시에 Pod/node가 정확히 비례해 사라지는 것은 아닙니다.
Node 용량 확보·반환은 Karpenter/Cluster Autoscaler 등의 별도 계층입니다.

### 현재 CLI 제출 형태

다음은 Part 2에서 namespace와 flink ServiceAccount/RBAC를 준비한 뒤 참고할
**Operator를 사용하지 않는 Native Application 제출 예시**입니다.
동일 cluster ID를 Operator CR과 CLI가 동시에 관리하지 않도록 합니다.
기본 제공되는 state-machine 예제는 장시간 실행되므로 완료되는 batch smoke test가 아닙니다.

```bash
# Illustration after namespace/ServiceAccount/RBAC preparation from Part 2.
# Use the Flink 2.2.1 distribution and a cluster ID not owned by an Operator CR.
./bin/flink run \
  --target kubernetes-application \
  -Dkubernetes.cluster-id=flink-cli-example \
  -Dkubernetes.container.image.ref=flink:2.2.1-java17 \
  -Dkubernetes.namespace=data-processing \
  -Dkubernetes.jobmanager.service-account=flink \
  -Dtaskmanager.numberOfTaskSlots=2 \
  -p 2 \
  local:///opt/flink/examples/streaming/StateMachineExample.jar
```

2.2.1 CLI는 run --target kubernetes-application을 사용합니다. 예전 run-application
명령을 그대로 복사하지 않습니다. image.ref는 현재 key이며 container.image는
deprecated alias입니다. local URI는 이 예제 image 안의 JAR을 가리킵니다.
CLI/JM의 권한, 이미지 pull, DNS·자원 여유와 실제 REST/로그 결과를 확인합니다.

## 4. Runtime과 검증 범위

Java 17은 이 기준선의 권장/default image 선택입니다. 공식 image 목록에는 Java 11
변형도 있으므로 2.x에서 전부 제거되었다고 단정하지 않습니다.
2.2 문서의 Java 21 지원은 experimental이며 “17 이상이면 어떤 JDK나 동일 지원”으로
표현하지 않습니다. JAR target bytecode·connector·reflection 설정까지 맞춥니다.

Architecture·CLI dispatch/config key·Operator source와 image tag 목록을 확인했습니다.
여기서 실제 cluster 생성, CLI job 제출이나 HA/throughput 시험을 수행하지는 않았습니다.

## 참고 자료

- [Flink releases and connector compatibility](https://flink.apache.org/downloads/)
- [Flink 2.2 architecture](https://nightlies.apache.org/flink/flink-docs-release-2.2/docs/concepts/flink-architecture/)
- [Flink 2.2 deployment modes](https://nightlies.apache.org/flink/flink-docs-release-2.2/docs/deployment/overview/)
- [Native Kubernetes deployment](https://nightlies.apache.org/flink/flink-docs-release-2.2/docs/deployment/resource-providers/native_kubernetes/)
- [Java compatibility](https://nightlies.apache.org/flink/flink-docs-release-2.2/docs/deployment/java_compatibility/)
- [Operator 1.15.0 deployment modes](https://github.com/apache/flink-kubernetes-operator/blob/release-1.15.0/docs/content/docs/custom-resource/overview.md)

[Part 2: Operator](02-flink-kubernetes-operator.md)

[README](README.md)

[Quiz](../../quizzes/data-on-eks/flink/01-architecture-quiz.md)
