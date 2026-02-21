# 비용 최적화

< [이전: 워크로드 배치 전략](./06-workload-placement.md) | [목차](./README.md) | [다음: 운영 및 유지보수](./08-operations.md) >

> **지원 버전**: EKS 1.31+, nodeadm 0.1+
> **마지막 업데이트**: 2025년 2월

이 문서에서는 EKS Hybrid Nodes 환경에서의 비용 최적화 전략을 다룹니다.

## 온프레미스 GPU vs 클라우드 GPU 비용 비교

### 비교 대상

동일 스펙(8x NVIDIA H200 141GB HBM3e)을 기준으로 온프레미스 서버와 AWS 클라우드 인스턴스를 비교합니다. H200은 H100 대비 HBM3e 메모리가 80GB → 141GB로 76% 증가하고, 메모리 대역폭이 3.35TB/s → 4.8TB/s로 향상되어 LLM 추론 성능이 최대 2배 빨라집니다.

| 항목 | 온프레미스 (예: DGX H200) | AWS p5en.48xlarge |
|------|--------------------------|-------------------|
| GPU | 8x H200 141GB HBM3e | 8x H200 141GB HBM3e |
| GPU 메모리 합계 | 1,128 GB | 1,128 GB |
| vCPU / RAM | 112 cores / 2TB | 192 vCPUs / 2,048 GB |
| 네트워크 | NVLink + InfiniBand 400Gb/s | EFA 3200 Gbps (Gen5 PCIe) |

### 서버 컴포넌트별 원가 (8x H200 SXM 서버)

| 구성요소 | 세부 사항 | 예상 비용 |
|---------|----------|----------|
| **GPU** | 8x NVIDIA H200 141GB SXM (~$27K-$30K/개, HBM3e 탑재로 H100 대비 프리미엄) | ~$220,000 |
| **시스템 메모리** | 2TB DDR5 RDIMM (32x 64GB, DDR5 가격 급등 반영) | ~$20,000 |
| **CPU** | 2x Intel Xeon Platinum 8480C (56C) | ~$10,000 |
| **NVSwitch + 인터커넥트** | NVSwitch 4개 + NVLink 연결 (7.2TB/s 양방향) | ~$35,000 |
| **스토리지** | NVMe SSD (OS 2x 1.9TB + 데이터 8x 3.84TB) | ~$15,000 |
| **섀시 + 전원 + 냉각** | 서버 섀시, PSU, 팬/히트싱크 (TDP 700W/GPU) | ~$15,000 |
| **네트워킹** | ConnectX-7 400Gb/s NIC × 10 | ~$10,000 |
| **OEM 마진 + 조립** | 제조사 마진 및 통합 테스트 | ~$75,000 |
| **합계** | | **~$400,000** |

> **가격 근거**:
> - GPU: H200 SXM은 HBM3e 141GB 탑재로 H100($20-$23K) 대비 프리미엄 가격. 2025-2026년 시장가 $27K-$30K 수준 (업계 추정)
> - DDR5 메모리: DRAMeXchange(2026.02) 기준 DDR5 RDIMM 가격 상승세 지속. 64GB RDIMM 모듈 ~$400-$600 (2024년 $200-$300 대비 ~60-100% 상승)
> - 전체 서버 참조 가격: NVIDIA DGX H200 공급가 ~$350K-$450K (DGX H100 $270K 대비 상승), OEM 서버 시장가 $380K-$500K
> - H200 TDP는 H100과 동일한 700W/GPU (SXM 폼팩터)

### 온프레미스 월간 TCO 산출

3년 상각 기준으로 월간 총 소유 비용(TCO)을 산출합니다.

| 비용 항목 | 산출 근거 | 월간 비용 |
|-----------|----------|-----------|
| **하드웨어 상각** | ~$400,000 서버 가격 ÷ 36개월 | $11,111 |
| **전력** | ~10kW 소비 × 730h × $0.10/kWh | $730 |
| **냉각 (PUE 1.3)** | 전력비 × 0.3 (PUE 오버헤드) | $219 |
| **데이터센터 공간** | 랙 공간 할당 비용 (42U 랙 기준 비례) | $1,500 |
| **네트워크 회선** | 전용선/인터넷 할당 비용 | $500 |
| **운영 인력** | 인프라 엔지니어 partial FTE 배분 | $3,000 |
| **유지보수/보증** | 하드웨어 가격의 ~15%/년 ÷ 12 | $5,000 |
| **합계** | | **~$22,060** |

> **핵심 가정**:
> - 서버 가격 ~$400,000은 2025-2026년 기준 8x H200 SXM 서버 시장가 추정치. HBM3e 및 DDR5 메모리 가격 상승분 반영
> - 전력 단가 $0.10/kWh는 미국 상업용 전기 평균 (EIA 2024 기준 $0.08-$0.13)
> - PUE 1.3은 Uptime Institute 2024 글로벌 평균 (1.55)보다 효율적인 최신 데이터센터 기준
> - 운영 인력은 10대 서버 기준 전담 인프라 엔지니어 1명($150K/년)의 배분치
> - **이 수치는 예시이며, 실제 비용은 지역, 전력 단가, 데이터센터 계약 조건에 따라 크게 달라질 수 있습니다**

### AWS 비용 산출 근거

| 항목 | 근거 | 비용 |
|------|------|------|
| **p5en.48xlarge On-Demand** | AWS EC2 Pricing API (us-east-1, 2026.02 조회) | $63.30/시간 |
| **월간 (730시간)** | $63.30 × 730h | **~$46,209** |
| **1-Year RI (No Upfront)** | 약 30% 할인 (GPU 인스턴스 추정치) | ~$32,346/월 |
| **3-Year RI (All Upfront)** | 약 50% 할인 (GPU 인스턴스 추정치) | ~$23,105/월 |

> **참고**:
> - AWS 가격은 us-east-1 리전 기준이며, AWS Pricing API에서 직접 조회한 값입니다 (p5en.48xlarge: $63.2960/hr)
> - 참고로 p5.48xlarge (H100)는 현재 $55.04/hr로, 기존 문서의 $98.32에서 크게 인하되었습니다
> - RI 할인율은 GPU 인스턴스 기준 추정치입니다. 정확한 RI 가격은 [AWS Pricing Calculator](https://calculator.aws/)에서 확인하세요

### 월간 비용 요약

| 시나리오 | 온프레미스 | AWS On-Demand | AWS 1Y RI | AWS 3Y RI |
|---------|-----------|---------------|-----------|-----------|
| 월간 비용 (24/7) | ~$22,060 | ~$46,209 | ~$32,346 | ~$23,105 |
| 시간당 환산 | ~$30.22 | $63.30 | ~$44.31 | ~$31.65 |
| 3년 총비용 | ~$794,160 | ~$1,663,524 | ~$1,164,456 | ~$831,780 |

### 비용 계산 스크립트

```bash
#!/bin/bash
# cost-calculator.sh - Hybrid 환경 비용 계산기

# 온프레미스 H200 서버 월간 비용 (TCO 기반)
ONPREM_H200_MONTHLY=22060

# AWS p5en.48xlarge 가격 시나리오
AWS_P5EN_ON_DEMAND=63.30
AWS_P5EN_1Y_RI=44.31
AWS_P5EN_3Y_RI=31.65

# 사용 시간 입력
read -p "월간 GPU 사용 시간 (시간): " HOURS

# 비용 계산
AWS_OD=$(echo "$AWS_P5EN_ON_DEMAND * $HOURS" | bc)
AWS_1Y=$(echo "$AWS_P5EN_1Y_RI * $HOURS" | bc)
AWS_3Y=$(echo "$AWS_P5EN_3Y_RI * $HOURS" | bc)

echo ""
echo "=== 월간 비용 비교 (${HOURS}시간 사용 기준) ==="
echo "온프레미스 H200 (TCO):        \$${ONPREM_H200_MONTHLY}"
echo "AWS p5en.48xlarge On-Demand:  \$${AWS_OD}"
echo "AWS p5en.48xlarge 1Y RI:      \$${AWS_1Y}"
echo "AWS p5en.48xlarge 3Y RI:      \$${AWS_3Y}"
echo ""

# 손익분기점 계산
BE_OD=$(echo "$ONPREM_H200_MONTHLY / $AWS_P5EN_ON_DEMAND" | bc)
BE_1Y=$(echo "$ONPREM_H200_MONTHLY / $AWS_P5EN_1Y_RI" | bc)
BE_3Y=$(echo "$ONPREM_H200_MONTHLY / $AWS_P5EN_3Y_RI" | bc)
echo "=== 손익분기점 ==="
echo "vs On-Demand: 월 ${BE_OD}시간 ($(echo "scale=0; $BE_OD * 100 / 730" | bc)% 가동률)"
echo "vs 1Y RI:     월 ${BE_1Y}시간 ($(echo "scale=0; $BE_1Y * 100 / 730" | bc)% 가동률)"
echo "vs 3Y RI:     월 ${BE_3Y}시간 ($(echo "scale=0; $BE_3Y * 100 / 730" | bc)% 가동률)"
```

## 손익분기점 분석

AWS 가격 시나리오별 온프레미스와의 손익분기점:

| AWS 시나리오 | 시간당 비용 | 손익분기점 | 최소 가동률 |
|-------------|-----------|-----------|-----------|
| On-Demand | $63.30 | ~349시간/월 | ~48% |
| 1-Year RI | ~$44.31 | ~498시간/월 | ~68% |
| 3-Year RI | ~$31.65 | ~697시간/월 | ~95% |

> **해석**: H200 기준으로 온프레미스는 On-Demand 대비 월 48% 가동률부터 유리하지만, 3-Year RI 대비로는 95% 이상 가동해야 온프레미스가 유리합니다. H100 대비 AWS 클라우드 가격이 크게 인하되면서 **RI/Savings Plan 적용 시 클라우드의 비용 경쟁력이 크게 향상**되었습니다.

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
