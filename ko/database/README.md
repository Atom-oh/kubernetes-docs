# Database on Kubernetes 개요

> **마지막 업데이트**: 2026년 9월 11일

"데이터베이스를 Kubernetes에서 돌려도 되는가"는 더 이상 예/아니오 질문이 아닙니다. 질문은 **어떤 데이터베이스를, 어떤 운영 체계(Operator)로, 어떤 스토리지 위에서** 돌릴 것인가로 바뀌었습니다. 이 섹션은 그 판단 기준과, 스펙 시트가 아닌 실측 데이터를 다룹니다.

## 이 섹션의 구성

| 문서 | 다루는 내용 |
|------|-------------|
| [ClickHouse on EKS 실측 벤치마크](./01-clickhouse-on-eks.md) | EKS 위 단일 노드 ClickHouse에 1억 행 로그를 넣고 직접 측정한 ingest 처리량, 압축률, 쿼리 레이턴시, skip index 효과 |

## 관리형 vs Kubernetes self-hosted 판단 기준

| 기준 | 관리형(RDS/Aurora/ElastiCache)이 유리 | K8s self-hosted가 유리 |
|------|--------------------------------------|------------------------|
| 운영 인력 | DBA/플랫폼 인력이 부족할 때 | 전담 플랫폼 팀이 있을 때 |
| 데이터베이스 종류 | PostgreSQL/MySQL/Redis 등 관리형이 존재할 때 | 관리형 서비스의 리전·확장·버전·운영 제약이 요구사항과 맞지 않을 때 (ClickHouse Cloud 등도 비교) |
| 비용 구조 | 서비스 요금과 운영 인력 절감을 합산 | 인프라·백업·HA·업그레이드·인력 비용을 모두 합산 |
| 배포 밀도 | 테넌트가 적을 때 | 테넌트별 DB 수십 개 (IaC/GitOps로 찍어내는 구조) |
| 통제 요구사항 | 제공되는 리전·암호화·감사 기능이 충족하는지 확인 | 직접 통제 범위와 운영 책임을 감당할 수 있는지 확인 |

핵심은 **데이터베이스 수명주기와 복구 책임을 누가 맡는가**입니다. 검증된 Operator는 이 자동화의 한 방법이지만 설치만으로 백업·HA가 완성되지는 않습니다. 엔진과 Operator의 지원 조합·기능·복구 절차를 확인합니다. StatefulSet을 직접 관리하는 경우 팀이 그 책임과 자동화를 직접 구현해야 합니다.

## Operator 지형 (2026)

| 데이터베이스 | 대표 Operator | 성숙도 메모 |
|--------------|---------------|-------------|
| PostgreSQL | CloudNativePG, Crunchy PGO, Zalando | 각 Operator의 지원 PostgreSQL/Kubernetes 버전과 복구 방식 비교 |
| MySQL | Percona Operator, Vitess(샤딩), MySQL Operator(Oracle) | Vitess는 샤딩 플랫폼; Percona/Oracle Operator는 지원 엔진·기능 비교 |
| Redis/Valkey | OT-CONTAINER-KIT redis-operator 등 (엔진별 지원 확인) | 캐시 용도는 ElastiCache와의 비용 비교 필수 |
| ClickHouse | Altinity clickhouse-operator | Apache-2.0 DB에 성숙한 커뮤니티 오퍼레이터가 있고, 관리형 대안은 ClickHouse Cloud |
| MongoDB | MongoDB Controllers for Kubernetes, Percona | 구 Community Operator는 폐기 경로이므로 새 저장소·마이그레이션 가이드 확인 |
| Kafka | Strimzi | 메시징/스트리밍은 [Data Pipeline 섹션](../data-on-eks/kafka/README.md) 참고 |

## K8s에서 데이터베이스를 돌릴 때의 4대 운영 포인트

1. **스토리지** — 볼륨 타입 선택이 곧 성능 예산입니다. [EBS gp2 vs gp3 실측](../storage/01-ebs-gp2-gp3-benchmark.md)에서 보듯 같은 용량에서도 IOPS가 10배 차이 납니다. DB 워크로드는 gp3 이상 + 프로비저닝 IOPS 검토가 기본입니다.
2. **토폴로지** — `topologySpreadConstraints`로 복제본을 AZ에 분산하고, AZ 간 데이터 전송 비용과 복제 지연을 함께 계산해야 합니다.
3. **리소스 격리** — Guaranteed QoS가 필요한 경우 모든 컨테이너의 CPU·메모리 request/limit을 일치시킵니다. 다만 이는 OOM·CPU throttling·노드 장애를 없애지 않습니다. CPU limit 정책과 캐시·백그라운드 작업·쿼리 메모리 여유를 실제 부하에 맞춰 정합니다.
4. **백업과 복구 리허설** — Operator의 백업 기능(예: CloudNativePG의 지원되는 Barman Cloud 플러그인 → S3)을 켜는 것만으로는 부족하고, 복구를 정기적으로 리허설해야 합니다.

## 함께 읽기

- [ClickHouse — 로그 백엔드 관점](../observability/logging/04-clickhouse.md) — Observability 파이프라인에서의 ClickHouse
- [Kubernetes 스토리지 기본](../core/04-storage.md) / [Storage 섹션](../storage/README.md)
- [EKS 스토리지 Part 1](../eks/04-eks-storage-part1.md)

## 참고 자료

- [MongoDB operator migration](https://github.com/mongodb/mongodb-kubernetes/blob/master/docs/migration/community-operator-migration.md)
- [CloudNativePG](https://cloudnative-pg.io/docs/)
- [ClickHouse Cloud](https://clickhouse.com/cloud)
- [Altinity ClickHouse Operator](https://github.com/Altinity/clickhouse-operator)
