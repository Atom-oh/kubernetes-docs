### 6. Amazon EKS에서 스토리지 모니터링 및 관리를 위한 가장 효과적인 도구 조합은 무엇인가요?

A. CloudWatch와 AWS Console만 사용  
B. CloudWatch, Prometheus, Grafana 및 자동화된 관리 도구  
C. 수동 검사 및 로그 분석  
D. 타사 모니터링 도구만 사용  

<details>
<summary>정답 및 설명</summary>

**정답: B. CloudWatch, Prometheus, Grafana 및 자동화된 관리 도구**

**설명:**
Amazon EKS에서 스토리지 모니터링 및 관리를 위한 가장 효과적인 도구 조합은 CloudWatch, Prometheus, Grafana 및 자동화된 관리 도구를 함께 사용하는 것입니다. 이 통합 접근 방식은 AWS 네이티브 메트릭과 Kubernetes 수준의 상세 메트릭을 모두 수집하고, 시각화하며, 자동화된 관리를 통해 운영 효율성을 높입니다.

**통합 모니터링 및 관리 아키텍처:**

1. **CloudWatch**:
   - AWS 인프라 수준 메트릭 수집
   - EBS, EFS, FSx 스토리지 성능 메트릭
   - 알람 및 이벤트 관리

2. **Prometheus**:
   - Kubernetes 수준의 상세 메트릭 수집
   - 사용자 정의 스토리지 메트릭 수집
   - 장기 데이터 보존 및 쿼리

3. **Grafana**:
   - 통합 대시보드 및 시각화
   - CloudWatch 및 Prometheus 데이터 소스 통합
   - 커스텀 알림 및 보고서

4. **자동화된 관리 도구**:
   - 스토리지 프로비저닝 자동화
   - 용량 계획 및 확장
   - 문제 감지 및 해결

**구현 예시:**

1. **CloudWatch Container Insights 설정**:
   ```yaml
   apiVersion: v1
   kind: ConfigMap
   metadata:
     name: cwagent-config
     namespace: amazon-cloudwatch
   data:
     cwagentconfig.json: |
       {
         "logs": {
           "metrics_collected": {
             "kubernetes": {
               "cluster_name": "my-cluster",
               "metrics_collection_interval": 60
             }
           },
           "force_flush_interval": 5
         },
         "metrics": {
           "namespace": "EKS/Storage",
           "metrics_collected": {
             "statsd": {
               "service_address": ":8125"
             }
           }
         }
       }
   ```

2. **Prometheus 및 스토리지 익스포터 설정**:
   ```yaml
   apiVersion: monitoring.coreos.com/v1
   kind: ServiceMonitor
   metadata:
     name: storage-monitor
     namespace: monitoring
   spec:
     selector:
       matchLabels:
         app: storage-exporter
     endpoints:
     - port: metrics
       interval: 30s
       path: /metrics
   ```

3. **Grafana 대시보드 구성**:
   ```yaml
   apiVersion: v1
   kind: ConfigMap
   metadata:
     name: storage-dashboard
     namespace: monitoring
   data:
     storage-dashboard.json: |
       {
         "title": "EKS Storage Dashboard",
         "panels": [
           {
             "title": "EBS Volume IOPS",
             "datasource": "Prometheus",
             "targets": [
               {
                 "expr": "aws_ebs_volume_read_ops + aws_ebs_volume_write_ops",
                 "legendFormat": "{{volume_id}}"
               }
             ]
           },
           {
             "title": "EFS Throughput",
             "datasource": "CloudWatch",
             "targets": [
               {
                 "namespace": "AWS/EFS",
                 "metricName": "TotalIOBytes",
                 "dimensions": {
                   "FileSystemId": "*"
                 },
                 "statistic": "Sum"
               }
             ]
           }
         ]
       }
   ```

4. **자동화된 스토리지 관리 CronJob**:
   ```yaml
   apiVersion: batch/v1
   kind: CronJob
   metadata:
     name: storage-manager
   spec:
     schedule: "0 1 * * *"
     jobTemplate:
       spec:
         template:
           spec:
             containers:
             - name: storage-manager
               image: storage-tools:latest
               command:
               - /bin/bash
               - -c
               - |
                 # 사용하지 않는 PVC 식별
                 UNUSED_PVCS=$(kubectl get pvc -A -o json | jq -r '.items[] | select(.status.phase == "Bound") | select(.metadata.annotations.lastUsed < "'$(date -d "30 days ago" +%Y-%m-%d)'") | .metadata.name')
                 
                 # 스냅샷 생성
                 for PVC in $UNUSED_PVCS; do
                   kubectl create snapshot ...
                 done
                 
                 # 볼륨 사용량 분석 및 보고서 생성
                 ...
             restartPolicy: OnFailure
   ```

**주요 모니터링 메트릭:**

1. **EBS 볼륨 메트릭**:
   - VolumeReadOps/VolumeWriteOps
   - VolumeReadBytes/VolumeWriteBytes
   - VolumeQueueLength
   - BurstBalance (gp2 볼륨)

2. **EFS 메트릭**:
   - TotalIOBytes
   - DataReadIOBytes/DataWriteIOBytes
   - MetadataIOBytes
   - ClientConnections
   - StorageBytes (표준/IA)

3. **FSx for Lustre 메트릭**:
   - DataReadBytes/DataWriteBytes
   - DataReadOperations/DataWriteOperations
   - FreeDataStorageCapacity
   - LogicalDiskUsage

4. **Kubernetes 스토리지 메트릭**:
   - PVC 사용량 및 용량
   - 볼륨 마운트 상태
   - 스토리지 클래스 사용량

**고급 모니터링 및 관리 기능:**

1. **예측 분석**:
   - 용량 예측 및 계획
   - 성능 추세 분석
   - 비용 예측

2. **이상 탐지**:
   - 비정상적인 I/O 패턴 감지
   - 성능 저하 조기 경고
   - 용량 부족 예측

3. **자동화된 최적화**:
   - 사용 패턴에 따른 볼륨 유형 추천
   - 자동 확장 및 축소
   - 비용 최적화 권장 사항

4. **통합 보고**:
   - 스토리지 사용량 및 성능 보고서
   - 비용 할당 및 분석
   - 규정 준수 및 감사 보고서

**구현 모범 사례:**

1. **다중 수준 모니터링**:
   - 인프라 수준 (CloudWatch)
   - Kubernetes 수준 (Prometheus)
   - 애플리케이션 수준 (커스텀 메트릭)

2. **알림 전략**:
   - 중요도 기반 알림 설정
   - 알림 그룹화 및 중복 제거
   - 에스컬레이션 경로 정의

3. **데이터 보존 정책**:
   - 고해상도 데이터: 단기 보존
   - 집계된 데이터: 장기 보존
   - 비용과 유용성 균형

4. **자동화 단계적 도입**:
   - 모니터링 및 알림 먼저 구현
   - 보고 및 분석 기능 추가
   - 자동화된 관리 점진적 도입

다른 옵션들의 문제점:
- **A. CloudWatch와 AWS Console만 사용**: AWS 네이티브 메트릭은 제공하지만, Kubernetes 수준의 상세 메트릭이 부족하며 자동화 기능이 제한적입니다.
- **C. 수동 검사 및 로그 분석**: 확장성이 떨어지고, 실시간 모니터링이 어려우며, 선제적 문제 감지가 불가능합니다.
- **D. 타사 모니터링 도구만 사용**: AWS 네이티브 메트릭과의 통합이 제한적일 수 있으며, 추가 비용이 발생할 수 있습니다.
</details>
