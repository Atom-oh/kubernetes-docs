# 비용 최적화

< [이전: 워크로드 배치 전략](./06-workload-placement.md) | [목차](./README.md) | [다음: 운영 및 유지보수](./08-operations.md) >

> **지원 버전**: EKS 1.31+, nodeadm 0.1+, Harbor 2.13+
> **마지막 업데이트**: 2025년 2월

이 문서에서는 EKS Hybrid Nodes 환경에서의 비용 최적화 전략을 다룹니다.

## 온프레미스 GPU vs 클라우드 GPU 비용 비교

### 월간 비용 비교 (예시)

| 항목 | 온프레미스 H100 서버 | AWS p5.48xlarge |
|------|---------------------|-----------------|
| GPU | 8x H100 80GB | 8x H100 80GB |
| 시간당 비용 | ~$24.96 (TCO 기반) | ~$98.32 |
| 월간 비용 (24/7) | ~$17,971 | ~$70,790 |
| 3년 TCO | ~$647,000 | ~$2,548,440 |

> **계산 기준**: 온프레미스는 하드웨어, 전력, 냉각, 공간, 관리 인력 포함. 클라우드는 On-Demand 가격 기준.

### 비용 계산 스크립트

```bash
#!/bin/bash
# cost-calculator.sh - Hybrid 환경 비용 계산기

# 온프레미스 H100 서버 월간 비용 (TCO 기반)
ONPREM_H100_MONTHLY=17971

# AWS p5.48xlarge 시간당 비용
AWS_P5_HOURLY=98.32

# 사용 시간 입력
read -p "월간 GPU 사용 시간 (시간): " HOURS

# 비용 계산
AWS_COST=$(echo "$AWS_P5_HOURLY * $HOURS" | bc)
ONPREM_COST=$ONPREM_H100_MONTHLY

echo ""
echo "=== 월간 비용 비교 ==="
echo "온프레미스 H100: \$${ONPREM_COST}"
echo "AWS p5.48xlarge: \$${AWS_COST}"
echo ""

# 손익분기점 계산
BREAKEVEN=$(echo "$ONPREM_COST / $AWS_P5_HOURLY" | bc)
echo "손익분기점: 월 ${BREAKEVEN}시간"
echo "현재 사용량이 ${BREAKEVEN}시간 이상이면 온프레미스가 유리합니다."
```

## 손익분기점 분석

```
월간 사용 시간에 따른 비용 비교:

  $80,000 |                                        ___
          |                                   ____/
  $60,000 |                              ____/
          |                         ____/
  $40,000 |                    ____/
          |               ____/
  $20,000 |----------____/------------------------ 온프레미스 (고정비)
          |     ____/
        0 |____/
          +----+----+----+----+----+----+----+----+
            100  200  300  400  500  600  700  730
                     월간 GPU 사용 시간

손익분기점: 약 183시간/월 (25% 가동률)
- 183시간 미만: AWS가 유리
- 183시간 이상: 온프레미스가 유리
```

## AWS Cost Explorer 통합

```bash
# 하이브리드 환경 비용 태그 설정
aws ce get-cost-and-usage \
  --time-period Start=2025-01-01,End=2025-01-31 \
  --granularity MONTHLY \
  --metrics "BlendedCost" \
  --group-by Type=TAG,Key=Environment Type=TAG,Key=NodeType \
  --filter '{
    "Tags": {
      "Key": "kubernetes.io/cluster/my-hybrid-cluster",
      "Values": ["owned"]
    }
  }'

# EKS 클러스터별 비용 분석
aws ce get-cost-and-usage \
  --time-period Start=2025-01-01,End=2025-01-31 \
  --granularity DAILY \
  --metrics "UnblendedCost" \
  --group-by Type=DIMENSION,Key=SERVICE \
  --filter '{
    "Tags": {
      "Key": "eks:cluster-name",
      "Values": ["my-hybrid-cluster"]
    }
  }'
```

## 선택적 워크로드 분배 권장사항

| 워크로드 유형 | 권장 위치 | 이유 |
|--------------|----------|------|
| 대규모 모델 학습 | 온프레미스 GPU | 장시간 사용, 비용 효율 |
| 실시간 추론 (고부하) | 온프레미스 GPU | 일관된 지연시간 |
| 실시간 추론 (변동) | AWS (Karpenter) | 탄력적 확장 |
| 데이터 전처리 | 온프레미스 CPU | 데이터 이동 최소화 |
| API 서빙 | AWS | 글로벌 배포, Auto Scaling |
| 배치 처리 | AWS Spot | 비용 최적화 |

---

< [이전: 워크로드 배치 전략](./06-workload-placement.md) | [목차](./README.md) | [다음: 운영 및 유지보수](./08-operations.md) >
