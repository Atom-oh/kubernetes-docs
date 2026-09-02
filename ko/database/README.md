# Database on Kubernetes 개요

> **마지막 업데이트**: 2026년 9월 1일

"데이터베이스를 Kubernetes에서 돌려도 되는가"는 더 이상 예/아니오 질문이 아닙니다. 질문은 **어떤 데이터베이스를, 어떤 운영 체계(Operator)로, 어떤 스토리지 위에서** 돌릴 것인가로 바뀌었습니다. 이 섹션은 그 판단 기준과, 스펙 시트가 아닌 실측 데이터를 다룹니다.

## 이 섹션의 구성

| 문서 | 다루는 내용 |
|------|-------------|
| [ClickHouse on EKS 실측 벤치마크](./01-clickhouse-on-eks.md) | EKS 위 단일 노드 ClickHouse에 1억 행 로그를 넣고 직접 측정한 ingest 처리량, 압축률, 쿼리 레이턴시, skip index 효과 |

## 관리형 vs Kubernetes self-hosted 판단 기준

| 기준 | 관리형(RDS/Aurora/ElastiCache)이 유리 | K8s self-hosted가 유리 |
|------|--------------------------------------|------------------------|
| 운영 인력 | DBA/플랫폼 인력이 부족할 때 | 전담 플랫폼 팀이 있을 때 |
| 데이터베이스 종류 | PostgreSQL/MySQL/Redis 등 관리형이 존재할 때 | ClickHouse, 특수 확장(pgvector 특정 버전 등) 등 관리형이 없거나 제약이 클 때 |
| 비용 구조 | 소수의 대형 인스턴스 | 다수의 중소형 클러스터 (관리형 요금 배수가 누적) |
| 배포 밀도 | 테넌트가 적을 때 | 테넌트별 DB 수십 개 (IaC/GitOps로 찍어내는 구조) |
| 컴플라이언스 | 표준 규제 대응은 관리형 인증 활용 | 데이터 위치/암호화 방식을 직접 통제해야 할 때 |

핵심 원칙: **StatefulSet을 직접 운영하는 것은 선택지가 아닙니다.** 프로덕션 데이터베이스를 K8s에서 돌리는 유일한 현실적 경로는 성숙한 Operator입니다. Operator가 페일오버, 백업, 마이너 버전 업그레이드, 복제 토폴로지를 대신 운영해 줍니다.

## Operator 지형 (2026)

| 데이터베이스 | 대표 Operator | 성숙도 메모 |
|--------------|---------------|-------------|
| PostgreSQL | CloudNativePG, Crunchy PGO, Zalando | CloudNativePG가 CNCF 생태계에서 사실상 표준으로 수렴 중 |
| MySQL | Percona Operator, Vitess(샤딩), MySQL Operator(Oracle) | 수평 샤딩이 필요하면 Vitess, 아니면 Percona |
| Redis/Valkey | OT-CONTAINER-KIT redis-operator, Valkey Operator | 캐시 용도는 ElastiCache와의 비용 비교 필수 |
| ClickHouse | Altinity clickhouse-operator | Apache-2.0 DB에 성숙한 커뮤니티 오퍼레이터가 있고, 관리형 대안은 ClickHouse Cloud |
| MongoDB | MongoDB Community Operator, Percona | 라이선스(SSPL) 고려 |
| Kafka | Strimzi | 메시징/스트리밍은 [Data Pipeline 섹션](../data-on-eks/kafka/README.md) 참고 |

## K8s에서 데이터베이스를 돌릴 때의 4대 운영 포인트

1. **스토리지** — 볼륨 타입 선택이 곧 성능 예산입니다. [EBS gp2 vs gp3 실측](../storage/01-ebs-gp2-gp3-benchmark.md)에서 보듯 같은 용량에서도 IOPS가 10배 차이 납니다. DB 워크로드는 gp3 이상 + 프로비저닝 IOPS 검토가 기본입니다.
2. **토폴로지** — `topologySpreadConstraints`로 복제본을 AZ에 분산하고, AZ 간 데이터 전송 비용과 복제 지연을 함께 계산해야 합니다.
3. **리소스 격리** — DB 파드는 Guaranteed QoS(요청=제한)로 두고, 메모리 제한은 DB 엔진의 자체 캐시 설정과 맞물려야 OOMKill을 피할 수 있습니다.
4. **백업과 복구 리허설** — Operator의 백업 기능(예: CloudNativePG의 barman-cloud → S3)을 켜는 것만으로는 부족하고, 복구를 정기적으로 리허설해야 합니다.

## 함께 읽기

- [ClickHouse — 로그 백엔드 관점](../observability/logging/04-clickhouse.md) — Observability 파이프라인에서의 ClickHouse
- [Kubernetes 스토리지 기본](../core/04-storage.md) / [Storage 섹션](../storage/README.md)
- [EKS 스토리지 Part 1](../eks/04-eks-storage-part1.md)
