# Kubernetes 기본 개념

Kubernetes를 효과적으로 사용하기 위해서는 핵심 개념과 리소스를 이해하는 것이 중요합니다. 이 장에서는 Kubernetes의 기본 구성 요소와 리소스에 대해 알아보겠습니다.

## 목차

1. [포드(Pod)](#포드pod)
2. [레플리카셋(ReplicaSet)](#레플리카셋replicaset)
3. [디플로이먼트(Deployment)](#디플로이먼트deployment)
4. [서비스(Service)](#서비스service)
5. [네임스페이스(Namespace)](#네임스페이스namespace)
6. [레이블과 셀렉터(Labels and Selectors)](#레이블과-셀렉터labels-and-selectors)
7. [어노테이션(Annotations)](#어노테이션annotations)
8. [컨피그맵과 시크릿(ConfigMap and Secret)](#컨피그맵과-시크릿configmap-and-secret)

## 포드(Pod)

포드는 Kubernetes에서 생성하고 관리할 수 있는 배포 가능한 가장 작은 컴퓨팅 단위입니다. 포드는 하나 이상의 컨테이너 그룹으로, 스토리지 및 네트워크 리소스와 컨테이너 실행 방법에 대한 명세를 포함합니다.

### 포드의 특징

- **공유 컨텍스트**: 포드 내의 컨테이너는 네트워크 네임스페이스, IPC 네임스페이스, UTS 네임스페이스를 공유합니다.
- **통신**: 포드 내의 컨테이너는 localhost를 통해 서로 통신할 수 있습니다.
- **스토리지**: 포드는 공유 볼륨을 통해 데이터를 공유할 수 있습니다.
- **생명주기**: 포드는 일시적인(ephemeral) 엔티티로, 장애 발생 시 자동으로 다시 생성되지 않습니다.

### 포드 생성 예제

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

### 포드 관리 명령어

```bash
# 포드 생성
kubectl apply -f pod.yaml

# 포드 목록 조회
kubectl get pods

# 포드 상세 정보 조회
kubectl describe pod nginx-pod

# 포드 로그 조회
kubectl logs nginx-pod

# 포드 내 컨테이너에 명령 실행
kubectl exec -it nginx-pod -- /bin/bash

# 포드 삭제
kubectl delete pod nginx-pod
```

### 멀티 컨테이너 포드

포드는 여러 컨테이너를 포함할 수 있으며, 이는 밀접하게 결합된 애플리케이션 구성 요소를 함께 실행하는 데 유용합니다.

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: multi-container-pod
spec:
  containers:
  - name: nginx
    image: nginx:1.14.2
    ports:
    - containerPort: 80
  - name: sidecar
    image: busybox
    command: ["sh", "-c", "while true; do echo Syncing data; sleep 30; done"]
```

## 레플리카셋(ReplicaSet)

레플리카셋은 지정된 수의 포드 복제본이 항상 실행되도록 보장합니다. 포드가 실패하거나 삭제되면 레플리카셋은 자동으로 새 포드를 생성하여 지정된 복제본 수를 유지합니다.

### 레플리카셋의 특징

- **자가 치유**: 노드 장애 또는 포드 종료 시 자동으로 새 포드 생성
- **스케일링**: 복제본 수를 늘리거나 줄여 애플리케이션 확장 가능
- **선언적 관리**: 원하는 상태를 선언하면 레플리카셋이 현재 상태를 원하는 상태로 조정

### 레플리카셋 생성 예제

```yaml
apiVersion: apps/v1
kind: ReplicaSet
metadata:
  name: nginx-replicaset
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

### 레플리카셋 관리 명령어

```bash
# 레플리카셋 생성
kubectl apply -f replicaset.yaml

# 레플리카셋 목록 조회
kubectl get replicasets

# 레플리카셋 상세 정보 조회
kubectl describe replicaset nginx-replicaset

# 레플리카셋 스케일링
kubectl scale replicaset nginx-replicaset --replicas=5

# 레플리카셋 삭제
kubectl delete replicaset nginx-replicaset
```

## 디플로이먼트(Deployment)

디플로이먼트는 레플리카셋의 상위 개념으로, 애플리케이션의 선언적 업데이트를 제공합니다. 디플로이먼트는 포드와 레플리카셋의 업데이트를 관리하고, 롤백 기능을 제공합니다.

### 디플로이먼트의 특징

- **롤링 업데이트**: 다운타임 없이 애플리케이션 업데이트 가능
- **롤백**: 이전 버전으로 쉽게 되돌릴 수 있음
- **배포 기록**: 이전 배포 버전 기록 유지
- **일시 중지 및 재개**: 배포 프로세스 제어 가능

### 디플로이먼트 생성 예제

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

### 디플로이먼트 관리 명령어

```bash
# 디플로이먼트 생성
kubectl apply -f deployment.yaml

# 디플로이먼트 목록 조회
kubectl get deployments

# 디플로이먼트 상세 정보 조회
kubectl describe deployment nginx-deployment

# 디플로이먼트 스케일링
kubectl scale deployment nginx-deployment --replicas=5

# 디플로이먼트 이미지 업데이트
kubectl set image deployment/nginx-deployment nginx=nginx:1.16.1

# 디플로이먼트 롤아웃 상태 확인
kubectl rollout status deployment/nginx-deployment

# 디플로이먼트 롤백
kubectl rollout undo deployment/nginx-deployment

# 디플로이먼트 롤아웃 기록 조회
kubectl rollout history deployment/nginx-deployment

# 디플로이먼트 삭제
kubectl delete deployment nginx-deployment
```

### 디플로이먼트 업데이트 전략

디플로이먼트는 두 가지 업데이트 전략을 지원합니다:

1. **RollingUpdate (기본값)**: 점진적으로 포드를 업데이트하여 다운타임 없이 애플리케이션 업데이트
2. **Recreate**: 기존 포드를 모두 삭제한 후 새 포드 생성 (일시적인 다운타임 발생)

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: nginx-deployment
spec:
  replicas: 3
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1        # 원하는 포드 수보다 최대 1개 더 생성 가능
      maxUnavailable: 1  # 원하는 포드 수에서 최대 1개 적게 실행 가능
  # ... 나머지 명세
```

## 서비스(Service)

서비스는 포드 집합에 대한 단일 접점을 제공하는 추상화 계층입니다. 포드는 일시적이며 IP 주소가 변경될 수 있으므로, 서비스는 안정적인 엔드포인트를 제공합니다.

### 서비스의 특징

- **안정적인 IP 주소**: 포드가 재생성되더라도 서비스 IP는 변경되지 않음
- **로드 밸런싱**: 여러 포드에 트래픽 분산
- **서비스 디스커버리**: DNS를 통한 서비스 검색
- **외부 액세스**: 클러스터 외부에서 포드에 접근 가능

### 서비스 유형

1. **ClusterIP (기본값)**: 클러스터 내부에서만 접근 가능한 서비스
2. **NodePort**: 각 노드의 IP에서 특정 포트를 통해 서비스에 접근 가능
3. **LoadBalancer**: 클라우드 제공업체의 로드 밸런서를 사용하여 서비스 노출
4. **ExternalName**: 외부 서비스에 대한 DNS 별칭 제공

### 서비스 생성 예제

```yaml
apiVersion: v1
kind: Service
metadata:
  name: nginx-service
spec:
  selector:
    app: nginx
  ports:
  - port: 80        # 서비스가 노출되는 포트
    targetPort: 80  # 포드의 대상 포트
  type: ClusterIP   # 서비스 유형
```

### NodePort 서비스 예제

```yaml
apiVersion: v1
kind: Service
metadata:
  name: nginx-nodeport
spec:
  selector:
    app: nginx
  ports:
  - port: 80
    targetPort: 80
    nodePort: 30080  # 노드에서 노출되는 포트 (30000-32767)
  type: NodePort
```

### LoadBalancer 서비스 예제

```yaml
apiVersion: v1
kind: Service
metadata:
  name: nginx-loadbalancer
spec:
  selector:
    app: nginx
  ports:
  - port: 80
    targetPort: 80
  type: LoadBalancer
```

### 서비스 관리 명령어

```bash
# 서비스 생성
kubectl apply -f service.yaml

# 서비스 목록 조회
kubectl get services

# 서비스 상세 정보 조회
kubectl describe service nginx-service

# 서비스 삭제
kubectl delete service nginx-service
```

## 네임스페이스(Namespace)

네임스페이스는 Kubernetes 클러스터 내에서 리소스를 논리적으로 분리하는 방법을 제공합니다. 이를 통해 여러 팀이나 프로젝트가 동일한 클러스터를 공유할 수 있습니다.

### 네임스페이스의 특징

- **리소스 격리**: 동일한 이름의 리소스를 다른 네임스페이스에 생성 가능
- **리소스 쿼터**: 네임스페이스별로 리소스 사용량 제한 가능
- **액세스 제어**: 네임스페이스별로 권한 부여 가능
- **기본 네임스페이스**: default, kube-system, kube-public, kube-node-lease

### 네임스페이스 생성 예제

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: development
```

### 특정 네임스페이스에 리소스 생성

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: nginx-pod
  namespace: development
spec:
  containers:
  - name: nginx
    image: nginx:1.14.2
```

### 네임스페이스 관리 명령어

```bash
# 네임스페이스 생성
kubectl create namespace development

# 네임스페이스 목록 조회
kubectl get namespaces

# 특정 네임스페이스의 포드 조회
kubectl get pods -n development

# 모든 네임스페이스의 포드 조회
kubectl get pods --all-namespaces

# 네임스페이스 삭제
kubectl delete namespace development
```

## 레이블과 셀렉터(Labels and Selectors)

레이블은 Kubernetes 리소스에 첨부하는 키-값 쌍입니다. 레이블을 사용하여 리소스를 구성하고 선택할 수 있습니다.

### 레이블의 특징

- **식별**: 리소스에 의미 있는 속성 부여
- **그룹화**: 유사한 리소스 그룹화
- **선택**: 레이블 셀렉터를 사용하여 리소스 선택
- **유연성**: 언제든지 추가, 수정, 삭제 가능

### 레이블 예제

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: nginx-pod
  labels:
    app: nginx
    environment: production
    tier: frontend
spec:
  containers:
  - name: nginx
    image: nginx:1.14.2
```

### 레이블 셀렉터

레이블 셀렉터는 레이블을 기반으로 리소스를 선택하는 방법을 제공합니다.

#### 평등 기반 셀렉터

- `=`, `==`: 같음
- `!=`: 같지 않음

```bash
# app=nginx 레이블이 있는 포드 선택
kubectl get pods -l app=nginx

# environment!=development 레이블이 있는 포드 선택
kubectl get pods -l environment!=development
```

#### 집합 기반 셀렉터

- `in`: 지정된 값 중 하나와 일치
- `notin`: 지정된 값과 일치하지 않음
- `exists`: 키가 존재함
- `!`: 키가 존재하지 않음

```bash
# environment가 production 또는 staging인 포드 선택
kubectl get pods -l 'environment in (production,staging)'

# tier 키가 있는 포드 선택
kubectl get pods -l 'tier'

# tier 키가 없는 포드 선택
kubectl get pods -l '!tier'
```

### 레이블 관리 명령어

```bash
# 레이블 추가
kubectl label pods nginx-pod version=1.0

# 레이블 업데이트
kubectl label --overwrite pods nginx-pod version=2.0

# 레이블 삭제
kubectl label pods nginx-pod version-
```

## 어노테이션(Annotations)

어노테이션은 레이블과 유사하게 키-값 쌍이지만, 식별이 아닌 비식별 메타데이터를 저장하는 데 사용됩니다.

### 어노테이션의 특징

- **메타데이터 저장**: 도구나 라이브러리를 위한 정보 저장
- **대용량 데이터**: 레이블보다 더 큰 데이터 저장 가능
- **비식별성**: 리소스 선택에 사용되지 않음
- **확장성**: 시스템 구성 요소나 타사 도구를 위한 정보 제공

### 어노테이션 예제

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: nginx-pod
  annotations:
    description: "Web server for serving static content"
    owner: "team-frontend"
    email: "frontend@example.com"
    version: "1.0"
spec:
  containers:
  - name: nginx
    image: nginx:1.14.2
```

### 어노테이션 관리 명령어

```bash
# 어노테이션 추가
kubectl annotate pods nginx-pod description="Web server"

# 어노테이션 업데이트
kubectl annotate --overwrite pods nginx-pod description="Updated description"

# 어노테이션 삭제
kubectl annotate pods nginx-pod description-
```

## 컨피그맵과 시크릿(ConfigMap and Secret)

컨피그맵과 시크릿은 구성 데이터를 포드와 분리하여 저장하는 방법을 제공합니다.

### 컨피그맵(ConfigMap)

컨피그맵은 키-값 쌍 형태의 비기밀 데이터를 저장하는 데 사용됩니다.

#### 컨피그맵 생성 예제

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: app-config
data:
  database_host: "mysql"
  database_port: "3306"
  app_mode: "production"
```

#### 명령줄에서 컨피그맵 생성

```bash
# 리터럴 값으로 생성
kubectl create configmap app-config --from-literal=database_host=mysql --from-literal=database_port=3306

# 파일에서 생성
kubectl create configmap app-config --from-file=config.properties

# 디렉토리에서 생성
kubectl create configmap app-config --from-file=config-dir/
```

### 시크릿(Secret)

시크릿은 암호, OAuth 토큰, SSH 키와 같은 민감한 정보를 저장하는 데 사용됩니다.

#### 시크릿 생성 예제

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: db-credentials
type: Opaque
data:
  username: YWRtaW4=  # base64로 인코딩된 "admin"
  password: cGFzc3dvcmQ=  # base64로 인코딩된 "password"
```

#### 명령줄에서 시크릿 생성

```bash
# 리터럴 값으로 생성
kubectl create secret generic db-credentials --from-literal=username=admin --from-literal=password=password

# 파일에서 생성
kubectl create secret generic tls-certs --from-file=cert.pem --from-file=key.pem

# Docker 레지스트리 인증 시크릿 생성
kubectl create secret docker-registry regcred --docker-server=<your-registry-server> --docker-username=<your-name> --docker-password=<your-password>
```

### 컨피그맵과 시크릿 사용

#### 환경 변수로 사용

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: config-pod
spec:
  containers:
  - name: app
    image: busybox
    command: ["sh", "-c", "echo $(DB_HOST):$(DB_PORT)"]
    env:
    - name: DB_HOST
      valueFrom:
        configMapKeyRef:
          name: app-config
          key: database_host
    - name: DB_PORT
      valueFrom:
        configMapKeyRef:
          name: app-config
          key: database_port
```

#### 볼륨으로 사용

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: config-pod
spec:
  containers:
  - name: app
    image: busybox
    command: ["sh", "-c", "cat /etc/config/database_host"]
    volumeMounts:
    - name: config-volume
      mountPath: /etc/config
  volumes:
  - name: config-volume
    configMap:
      name: app-config
```

## 결론

이 장에서는 Kubernetes의 기본 개념과 리소스에 대해 알아보았습니다. 포드, 레플리카셋, 디플로이먼트, 서비스, 네임스페이스, 레이블, 어노테이션, 컨피그맵, 시크릿은 Kubernetes 애플리케이션을 구성하는 핵심 구성 요소입니다. 이러한 개념을 이해하면 Kubernetes에서 애플리케이션을 효과적으로 배포하고 관리할 수 있습니다.

다음 장에서는 Kubernetes 리소스 관리에 대해 더 자세히 알아보겠습니다.

## 참고 자료

- [Kubernetes 공식 문서 - 개념](https://kubernetes.io/docs/concepts/)
- [Kubernetes 공식 문서 - 포드](https://kubernetes.io/docs/concepts/workloads/pods/)
- [Kubernetes 공식 문서 - 디플로이먼트](https://kubernetes.io/docs/concepts/workloads/controllers/deployment/)
- [Kubernetes 공식 문서 - 서비스](https://kubernetes.io/docs/concepts/services-networking/service/)
- [Kubernetes 공식 문서 - 네임스페이스](https://kubernetes.io/docs/concepts/overview/working-with-objects/namespaces/)
- [Kubernetes 공식 문서 - 레이블과 셀렉터](https://kubernetes.io/docs/concepts/overview/working-with-objects/labels/)
