# Kubernetes 리소스 관리

Kubernetes에서 리소스를 효과적으로 관리하는 것은 클러스터의 안정성과 효율성을 유지하는 데 중요합니다. 이 장에서는 Kubernetes 리소스를 생성, 조회, 수정, 삭제하는 방법과 리소스 제한 및 요청을 설정하는 방법에 대해 알아보겠습니다.

## 목차

1. [YAML 파일 작성](#yaml-파일-작성)
2. [kubectl 명령어 활용](#kubectl-명령어-활용)
3. [리소스 생성, 조회, 수정, 삭제](#리소스-생성-조회-수정-삭제)
4. [리소스 제한 및 요청 설정](#리소스-제한-및-요청-설정)
5. [네임스페이스 리소스 관리](#네임스페이스-리소스-관리)
6. [리소스 모니터링](#리소스-모니터링)

## YAML 파일 작성

Kubernetes 리소스는 일반적으로 YAML 파일로 정의됩니다. YAML(YAML Ain't Markup Language)은 사람이 읽기 쉬운 데이터 직렬화 형식입니다.

### YAML 기본 구문

```yaml
key: value           # 키-값 쌍
nested:              # 중첩된 맵
  key1: value1
  key2: value2
sequence:            # 시퀀스(배열)
  - item1
  - item2
  - item3
```

### Kubernetes 리소스 YAML 구조

모든 Kubernetes 리소스 YAML 파일은 다음 필드를 포함합니다:

```yaml
apiVersion: v1       # Kubernetes API 버전
kind: Pod            # 리소스 유형
metadata:            # 리소스에 대한 메타데이터
  name: nginx-pod    # 리소스 이름
  labels:            # 레이블(선택 사항)
    app: nginx
spec:                # 리소스 사양
  containers:        # 컨테이너 정의
  - name: nginx      # 컨테이너 이름
    image: nginx:1.14.2  # 컨테이너 이미지
```

### 주요 리소스 YAML 예제

#### 포드(Pod)

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: nginx-pod
  labels:
    app: nginx
spec:
  containers:
  - name: nginx
    image: nginx:1.14.2
    ports:
    - containerPort: 80
```

#### 디플로이먼트(Deployment)

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: nginx-deployment
  labels:
    app: nginx
spec:
  replicas: 3
  selector:
    matchLabels:
      app: nginx
  template:
    metadata:
      labels:
        app: nginx
    spec:
      containers:
      - name: nginx
        image: nginx:1.14.2
        ports:
        - containerPort: 80
```

#### 서비스(Service)

```yaml
apiVersion: v1
kind: Service
metadata:
  name: nginx-service
spec:
  selector:
    app: nginx
  ports:
  - port: 80
    targetPort: 80
  type: ClusterIP
```

### YAML 작성 팁

1. **들여쓰기**: YAML은 들여쓰기에 민감합니다. 일관된 들여쓰기(일반적으로 2칸)를 사용하세요.
2. **주석**: `#` 문자를 사용하여 주석을 추가할 수 있습니다.
3. **멀티라인 문자열**: `|`(파이프) 문자를 사용하여 줄 바꿈을 유지하는 멀티라인 문자열을 정의할 수 있습니다.
4. **참조**: 다른 YAML 파일이나 환경 변수를 참조할 수 있습니다.

```yaml
# 멀티라인 문자열 예제
data:
  config.properties: |
    database.url=jdbc:mysql://localhost:3306/db
    database.username=admin
    database.password=password
```

## kubectl 명령어 활용

kubectl은 Kubernetes 클러스터와 상호 작용하기 위한 명령줄 도구입니다. 다양한 작업을 수행하는 데 사용됩니다.

### 기본 명령어 구조

```bash
kubectl [command] [TYPE] [NAME] [flags]
```

- **command**: 수행할 작업(get, create, delete 등)
- **TYPE**: 리소스 유형(pods, deployments, services 등)
- **NAME**: 리소스 이름
- **flags**: 추가 옵션

### 주요 kubectl 명령어

#### 리소스 조회

```bash
# 모든 포드 조회
kubectl get pods

# 모든 디플로이먼트 조회
kubectl get deployments

# 모든 서비스 조회
kubectl get services

# 여러 리소스 유형 조회
kubectl get pods,services

# 모든 네임스페이스의 리소스 조회
kubectl get pods --all-namespaces

# 특정 네임스페이스의 리소스 조회
kubectl get pods -n kube-system

# 자세한 정보 조회
kubectl get pods -o wide

# YAML 형식으로 조회
kubectl get pod nginx-pod -o yaml

# JSON 형식으로 조회
kubectl get pod nginx-pod -o json

# 특정 레이블을 가진 리소스 조회
kubectl get pods -l app=nginx

# 리소스 감시(실시간 업데이트)
kubectl get pods --watch
```

#### 리소스 상세 정보 조회

```bash
# 포드 상세 정보 조회
kubectl describe pod nginx-pod

# 디플로이먼트 상세 정보 조회
kubectl describe deployment nginx-deployment

# 서비스 상세 정보 조회
kubectl describe service nginx-service
```

#### 리소스 생성 및 적용

```bash
# YAML 파일로부터 리소스 생성
kubectl create -f pod.yaml

# YAML 파일로부터 리소스 적용(생성 또는 업데이트)
kubectl apply -f pod.yaml

# 여러 YAML 파일 적용
kubectl apply -f pod1.yaml -f pod2.yaml

# 디렉토리의 모든 YAML 파일 적용
kubectl apply -f ./configs/

# URL에서 YAML 파일 적용
kubectl apply -f https://example.com/pod.yaml

# 명령줄에서 직접 리소스 생성
kubectl create deployment nginx --image=nginx:1.14.2
```

#### 리소스 편집

```bash
# 리소스 편집
kubectl edit pod nginx-pod

# 특정 필드 설정
kubectl set image deployment/nginx-deployment nginx=nginx:1.16.1

# 리소스 스케일링
kubectl scale deployment nginx-deployment --replicas=5
```

#### 리소스 삭제

```bash
# 이름으로 리소스 삭제
kubectl delete pod nginx-pod

# YAML 파일로 리소스 삭제
kubectl delete -f pod.yaml

# 레이블로 리소스 삭제
kubectl delete pods -l app=nginx

# 모든 포드 삭제
kubectl delete pods --all

# 강제 삭제
kubectl delete pod nginx-pod --grace-period=0 --force
```

#### 로그 및 디버깅

```bash
# 포드 로그 조회
kubectl logs nginx-pod

# 이전 인스턴스의 로그 조회
kubectl logs nginx-pod --previous

# 로그 스트리밍
kubectl logs -f nginx-pod

# 포드 내 컨테이너에 명령 실행
kubectl exec -it nginx-pod -- /bin/bash

# 포드 내 특정 컨테이너에 명령 실행
kubectl exec -it nginx-pod -c nginx -- /bin/bash
```

#### 클러스터 정보

```bash
# 클러스터 정보 조회
kubectl cluster-info

# API 리소스 조회
kubectl api-resources

# API 버전 조회
kubectl api-versions

# 노드 조회
kubectl get nodes

# 컴포넌트 상태 조회
kubectl get componentstatuses
```

### kubectl 출력 형식

kubectl 명령어의 출력 형식을 `-o` 또는 `--output` 플래그로 지정할 수 있습니다:

```bash
# 기본 출력
kubectl get pods

# 자세한 출력
kubectl get pods -o wide

# YAML 형식
kubectl get pod nginx-pod -o yaml

# JSON 형식
kubectl get pod nginx-pod -o json

# 특정 필드만 출력
kubectl get pods -o jsonpath='{.items[0].metadata.name}'

# 사용자 정의 열
kubectl get pods -o custom-columns=NAME:.metadata.name,STATUS:.status.phase

# Go 템플릿
kubectl get pods -o go-template='{{range .items}}{{.metadata.name}}{{"\n"}}{{end}}'
```

### kubectl 컨텍스트 및 구성

kubectl은 `~/.kube/config` 파일에서 클러스터 구성을 찾습니다:

```bash
# 현재 컨텍스트 확인
kubectl config current-context

# 컨텍스트 전환
kubectl config use-context my-cluster-name

# 컨텍스트 목록 조회
kubectl config get-contexts

# 클러스터 정보 조회
kubectl config view
```

## 리소스 생성, 조회, 수정, 삭제

### 리소스 생성

리소스를 생성하는 방법에는 여러 가지가 있습니다:

#### YAML 파일 사용

```bash
# 리소스 생성
kubectl create -f resource.yaml

# 리소스 적용(생성 또는 업데이트)
kubectl apply -f resource.yaml
```

#### 명령줄에서 직접 생성

```bash
# 디플로이먼트 생성
kubectl create deployment nginx --image=nginx:1.14.2

# 서비스 생성
kubectl expose deployment nginx --port=80 --type=ClusterIP

# 컨피그맵 생성
kubectl create configmap app-config --from-literal=key1=value1 --from-literal=key2=value2

# 시크릿 생성
kubectl create secret generic db-secret --from-literal=username=admin --from-literal=password=password
```

#### 드라이런(Dry Run)

실제로 리소스를 생성하지 않고 YAML 파일을 생성할 수 있습니다:

```bash
# 드라이런으로 디플로이먼트 YAML 생성
kubectl create deployment nginx --image=nginx:1.14.2 --dry-run=client -o yaml > deployment.yaml

# 드라이런으로 서비스 YAML 생성
kubectl expose deployment nginx --port=80 --type=ClusterIP --dry-run=client -o yaml > service.yaml
```

### 리소스 조회

리소스를 조회하는 방법에는 여러 가지가 있습니다:

```bash
# 기본 조회
kubectl get pods

# 자세한 정보 조회
kubectl get pods -o wide

# 특정 리소스 조회
kubectl get pod nginx-pod

# 레이블로 필터링
kubectl get pods -l app=nginx

# 네임스페이스 지정
kubectl get pods -n kube-system

# 모든 네임스페이스 조회
kubectl get pods --all-namespaces

# 상세 정보 조회
kubectl describe pod nginx-pod
```

### 리소스 수정

리소스를 수정하는 방법에는 여러 가지가 있습니다:

#### 직접 편집

```bash
# 리소스 편집
kubectl edit pod nginx-pod
```

#### 패치(Patch)

```bash
# JSON 패치 적용
kubectl patch pod nginx-pod -p '{"spec":{"containers":[{"name":"nginx","image":"nginx:1.16.1"}]}}'

# 전략적 병합 패치 적용
kubectl patch deployment nginx-deployment --patch-file patch.yaml
```

#### 특정 필드 설정

```bash
# 이미지 업데이트
kubectl set image deployment/nginx-deployment nginx=nginx:1.16.1

# 리소스 요청 및 제한 설정
kubectl set resources deployment nginx-deployment --limits=cpu=200m,memory=512Mi --requests=cpu=100m,memory=256Mi
```

#### 스케일링

```bash
# 디플로이먼트 스케일링
kubectl scale deployment nginx-deployment --replicas=5
```

#### 롤아웃 관리

```bash
# 롤아웃 상태 확인
kubectl rollout status deployment/nginx-deployment

# 롤아웃 기록 조회
kubectl rollout history deployment/nginx-deployment

# 특정 버전으로 롤백
kubectl rollout undo deployment/nginx-deployment --to-revision=2

# 롤아웃 일시 중지
kubectl rollout pause deployment/nginx-deployment

# 롤아웃 재개
kubectl rollout resume deployment/nginx-deployment
```

### 리소스 삭제

리소스를 삭제하는 방법에는 여러 가지가 있습니다:

```bash
# 이름으로 삭제
kubectl delete pod nginx-pod

# YAML 파일로 삭제
kubectl delete -f resource.yaml

# 레이블로 삭제
kubectl delete pods -l app=nginx

# 모든 리소스 삭제
kubectl delete pods --all

# 네임스페이스의 모든 리소스 삭제
kubectl delete all --all -n my-namespace

# 강제 삭제
kubectl delete pod nginx-pod --grace-period=0 --force
```

## 리소스 제한 및 요청 설정

Kubernetes에서는 컨테이너의 리소스 사용량을 제어하기 위해 리소스 요청(requests)과 제한(limits)을 설정할 수 있습니다.

### 리소스 요청과 제한

- **리소스 요청(requests)**: 컨테이너가 보장받을 최소 리소스 양
- **리소스 제한(limits)**: 컨테이너가 사용할 수 있는 최대 리소스 양

### 리소스 유형

- **CPU**: 코어 단위(예: 0.5, 1, 2) 또는 밀리코어 단위(예: 500m, 1000m)
- **메모리**: 바이트 단위(예: 256Mi, 1Gi)

### 포드에 리소스 요청 및 제한 설정

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: resource-demo
spec:
  containers:
  - name: resource-demo-container
    image: nginx
    resources:
      requests:
        memory: "64Mi"
        cpu: "250m"
      limits:
        memory: "128Mi"
        cpu: "500m"
```

### 디플로이먼트에 리소스 요청 및 제한 설정

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: nginx-deployment
spec:
  replicas: 3
  selector:
    matchLabels:
      app: nginx
  template:
    metadata:
      labels:
        app: nginx
    spec:
      containers:
      - name: nginx
        image: nginx:1.14.2
        resources:
          requests:
            memory: "64Mi"
            cpu: "250m"
          limits:
            memory: "128Mi"
            cpu: "500m"
```

### 명령줄에서 리소스 요청 및 제한 설정

```bash
# 디플로이먼트 생성 시 리소스 설정
kubectl create deployment nginx --image=nginx --requests=cpu=250m,memory=64Mi --limits=cpu=500m,memory=128Mi

# 기존 디플로이먼트에 리소스 설정
kubectl set resources deployment nginx-deployment --requests=cpu=250m,memory=64Mi --limits=cpu=500m,memory=128Mi
```

### QoS(Quality of Service) 클래스

포드의 리소스 요청 및 제한 설정에 따라 Kubernetes는 포드에 QoS 클래스를 할당합니다:

1. **Guaranteed**: 모든 컨테이너에 CPU 및 메모리에 대한 요청과 제한이 설정되어 있고, 요청과 제한이 동일한 경우
2. **Burstable**: 적어도 하나의 컨테이너에 CPU 또는 메모리에 대한 요청이 설정되어 있지만, Guaranteed 조건을 충족하지 않는 경우
3. **BestEffort**: 어떤 컨테이너도 CPU 및 메모리에 대한 요청과 제한이 설정되어 있지 않은 경우

QoS 클래스는 리소스 부족 시 포드 축출(eviction) 우선순위에 영향을 미칩니다:
- BestEffort 포드가 가장 먼저 축출됩니다.
- 그 다음으로 Burstable 포드가 축출됩니다.
- Guaranteed 포드는 마지막에 축출됩니다.

## 네임스페이스 리소스 관리

네임스페이스 수준에서 리소스 사용량을 제한하기 위해 ResourceQuota와 LimitRange를 사용할 수 있습니다.

### ResourceQuota

ResourceQuota는 네임스페이스에서 사용할 수 있는 총 리소스 양을 제한합니다.

```yaml
apiVersion: v1
kind: ResourceQuota
metadata:
  name: compute-quota
  namespace: development
spec:
  hard:
    pods: "10"
    requests.cpu: "4"
    requests.memory: 8Gi
    limits.cpu: "8"
    limits.memory: 16Gi
```

### LimitRange

LimitRange는 네임스페이스 내의 포드 및 컨테이너에 대한 기본 리소스 제한 및 요청을 설정합니다.

```yaml
apiVersion: v1
kind: LimitRange
metadata:
  name: limit-range
  namespace: development
spec:
  limits:
  - default:
      cpu: 500m
      memory: 512Mi
    defaultRequest:
      cpu: 200m
      memory: 256Mi
    max:
      cpu: 1
      memory: 1Gi
    min:
      cpu: 100m
      memory: 128Mi
    type: Container
```

## 리소스 모니터링

Kubernetes 리소스 사용량을 모니터링하는 방법에는 여러 가지가 있습니다:

### kubectl top

```bash
# 노드 리소스 사용량 조회
kubectl top nodes

# 포드 리소스 사용량 조회
kubectl top pods

# 특정 네임스페이스의 포드 리소스 사용량 조회
kubectl top pods -n kube-system
```

### Metrics Server

Metrics Server는 클러스터 전체의 리소스 사용량 데이터를 수집합니다:

```bash
# Metrics Server 설치
kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml

# Metrics Server 확인
kubectl get deployment metrics-server -n kube-system
```

### Prometheus 및 Grafana

더 고급 모니터링을 위해 Prometheus와 Grafana를 사용할 수 있습니다:

```bash
# Prometheus Operator 설치(Helm 사용)
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update
helm install prometheus prometheus-community/kube-prometheus-stack
```

## 결론

이 장에서는 Kubernetes 리소스 관리에 대해 알아보았습니다. YAML 파일 작성, kubectl 명령어 활용, 리소스 생성/조회/수정/삭제, 리소스 제한 및 요청 설정, 네임스페이스 리소스 관리, 리소스 모니터링 등의 주제를 다루었습니다. 이러한 지식을 바탕으로 Kubernetes 클러스터에서 리소스를 효과적으로 관리할 수 있습니다.

다음 장에서는 Kubernetes Core 개념에 대해 더 자세히 알아보겠습니다.

## 참고 자료

- [Kubernetes 공식 문서 - kubectl 치트 시트](https://kubernetes.io/docs/reference/kubectl/cheatsheet/)
- [Kubernetes 공식 문서 - 리소스 관리](https://kubernetes.io/docs/concepts/configuration/manage-resources-containers/)
- [Kubernetes 공식 문서 - ResourceQuota](https://kubernetes.io/docs/concepts/policy/resource-quotas/)
- [Kubernetes 공식 문서 - LimitRange](https://kubernetes.io/docs/concepts/policy/limit-range/)
- [Kubernetes 공식 문서 - 모니터링 아키텍처](https://kubernetes.io/docs/tasks/debug-application-cluster/resource-usage-monitoring/)
