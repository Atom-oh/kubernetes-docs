# 종료된 검토 세션의 로컬 기록

2026-09-13에 종료된 문서 검토 세션의 미커밋 작업 기록 8개를 원본 바이트 그대로 보존합니다. 보존 작업은 2026-09-14에 수행했습니다. 각 파일의 원래 경로, SHA-256, 크기는 [manifest.json](manifest.json)에 있습니다.

현재 문서의 검토·배포 상태는 [최종 검토 안내](../../README.md)와 [전체 검증 보고서](../../full-audit-verification.json)를 기준으로 확인합니다. 이 폴더의 기록은 과거 작업 상태이며, 새로운 내용 검토나 실행 검증의 결과가 아닙니다.

| 기록 | 원래 역할 |
| --- | --- |
| [service-mesh-worker-checkpoint.json](service-mesh-worker-checkpoint.json) | 검토 작업자의 진행·인계 상태 |
| [worker-domain-queue.json](worker-domain-queue.json) | 작업 범위와 담당 구분 |
| [worker-render-compilation.json](worker-render-compilation.json) | 당시의 Markdown 컴파일 결과 |
| [batches/observability-metrics.json](batches/observability-metrics.json) | 메트릭 문서별 검토 기록 |
| [batches/observability-tracing.json](batches/observability-tracing.json) | 트레이싱 문서별 검토 기록 |
| [observability-domain-progress.json](observability-domain-progress.json) | 관측성 작업자의 완료 상태 |
| [observability-ready-cohorts.json](observability-ready-cohorts.json) | 통합 담당자에게 전달한 묶음과 당시 파일 해시 |
| [security-03-pss-validation.json](security-03-pss-validation.json) | 다이어그램 후속 작업이 남아 있던 Pod Security 검토의 중간 기록 |

원본 기록에는 오래된 진행 문구, 임시 파일 경로, 당시 로컬 문서의 해시가 남아 있습니다. 특히 Pod Security 기록의 `semantic-review-complete-assets-pending` 상태는 최종 완료 판정이 아닙니다. 기록에 있는 로컬 경로나 후속 작업 메모를 현재 실행 지시로 해석하지 않습니다.

수집 당시 원본 작업 폴더에는 미커밋 변경이 있었습니다. manifest의 `sourceCheckoutHead`는 그 폴더의 기준 커밋이며, 기록 내용이 해당 커밋에 들어 있었다는 뜻이 아닙니다. 실제 보존한 내용은 파일별 SHA-256으로 식별합니다. `comparisonMainCommit`은 정리 시 비교한 `main` 커밋입니다.
