# Cilium 도구 퀴즈

이 퀴즈는 Cilium 도구 및 운영에 대한 이해도를 테스트합니다.

## 문제 1: Cilium CLI

<details>
<summary>Cilium CLI의 주요 명령어들은?</summary>

**답변:**
- **cilium install**: Cilium 설치
- **cilium status**: Cilium 상태 확인
- **cilium connectivity test**: 연결성 테스트 실행
- **cilium hubble enable**: Hubble 활성화
- **cilium config**: 구성 확인 및 변경
- **cilium endpoint list**: 엔드포인트 목록 조회
- **cilium policy get**: 네트워크 정책 조회
- **cilium monitor**: 실시간 이벤트 모니터링
</details>

## 문제 2: Hubble 관찰성

<details>
<summary>Hubble을 사용한 네트워크 플로우 관찰 방법은?</summary>

**답변:**
```bash
# Hubble 활성화
cilium hubble enable --ui

# 실시간 플로우 관찰
hubble observe

# 특정 네임스페이스 플로우 관찰
hubble observe --namespace kube-system

# 특정 포드 플로우 관찰
hubble observe --pod app=frontend

# 거부된 트래픽만 관찰
hubble observe --verdict DROPPED

# HTTP 트래픽만 관찰
hubble observe --protocol http
```
</details>

## 문제 3: 네트워크 정책 테스트

<details>
<summary>Cilium에서 네트워크 정책을 테스트하는 방법은?</summary>

**답변:**
```bash
# 연결성 테스트 실행
cilium connectivity test

# 특정 시나리오 테스트
cilium connectivity test --test pod-to-pod
cilium connectivity test --test pod-to-service

# 네트워크 정책 적용 후 테스트
kubectl apply -f network-policy.yaml
cilium connectivity test --test deny-all

# 정책 위반 모니터링
hubble observe --verdict DROPPED
```
</details>

## 문제 4: 성능 모니터링

<details>
<summary>Cilium의 성능을 모니터링하는 방법은?</summary>

**답변:**
- **Prometheus 메트릭**: Cilium이 노출하는 메트릭 수집
- **Grafana 대시보드**: 시각화된 성능 지표
- **Hubble 메트릭**: 네트워크 플로우 통계
- **eBPF 맵 통계**: 메모리 사용량 및 성능 지표

```bash
# Cilium 메트릭 확인
curl http://localhost:9090/metrics

# eBPF 맵 상태 확인
cilium bpf map list
cilium bpf map get cilium_policy
```
</details>

## 문제 5: 문제 해결

<details>
<summary>Cilium 관련 문제를 해결하는 단계는?</summary>

**답변:**
1. **상태 확인**:
   ```bash
   cilium status --verbose
   kubectl get pods -n kube-system -l k8s-app=cilium
   ```

2. **로그 분석**:
   ```bash
   kubectl logs -n kube-system -l k8s-app=cilium
   cilium monitor --type drop
   ```

3. **연결성 테스트**:
   ```bash
   cilium connectivity test
   ```

4. **구성 검증**:
   ```bash
   cilium config
   kubectl get ciliumnetworkpolicies
   ```

5. **엔드포인트 확인**:
   ```bash
   cilium endpoint list
   cilium endpoint get <endpoint-id>
   ```
</details>

## 문제 6: 업그레이드

<details>
<summary>Cilium을 안전하게 업그레이드하는 방법은?</summary>

**답변:**
```bash
# 현재 버전 확인
cilium version

# 업그레이드 전 상태 백업
kubectl get ciliumnetworkpolicies -o yaml > policies-backup.yaml

# 업그레이드 실행
cilium upgrade --version 1.14.0

# 업그레이드 상태 확인
cilium status

# 연결성 테스트
cilium connectivity test

# 롤백 (필요시)
cilium upgrade --version 1.13.0
```
</details>

---

**점수 계산:**
- 5-6개 정답: 우수 (Cilium 운영 전문가 수준)
- 3-4개 정답: 양호 (추가 학습 권장)
- 1-2개 정답: 보통 (기본 개념 복습 필요)
- 0개 정답: 미흡 (전체 내용 재학습 필요)
