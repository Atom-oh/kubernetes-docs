# 워크로드 리소스

Kubernetes에서 워크로드 리소스는 컨테이너화된 애플리케이션을 실행하고 관리하는 다양한 방법을 제공합니다. 이 장에서는 디플로이먼트, 스테이트풀셋, 데몬셋, 잡, 크론잡 등의 워크로드 리소스와 관련된 개념을 자세히 살펴보겠습니다.

## 목차

1. [디플로이먼트 전략](#디플로이먼트-전략)
2. [스테이트풀셋(StatefulSet)](#스테이트풀셋statefulset)
3. [데몬셋(DaemonSet)](#데몬셋daemonset)
4. [잡(Job)과 크론잡(CronJob)](#잡job과-크론잡cronjob)
5. [롤링 업데이트와 롤백](#롤링-업데이트와-롤백)

## 디플로이먼트 전략

디플로이먼트(Deployment)는 포드와 레플리카셋에 대한 선언적 업데이트를 제공합니다. 디플로이먼트는 애플리케이션의 배포와 업데이트를 관리하는 가장 일반적인 방법입니다.

### 디플로이먼트 기본 개념

디플로이먼트는 다음과 같은 기능을 제공합니다:

- 포드의 원하는 상태 선언
- 롤링 업데이트 및 롤백
- 스케일링
- 일시 중지 및 재개

### 디플로이먼트 생성

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

이 예제는 3개의 레플리카를 가진 Nginx 디플로이먼트를 생성합니다.

### 디플로이먼트 전략 유형

Kubernetes는 두 가지 주요 디플로이먼트 전략을 제공합니다:

1. **롤링 업데이트(RollingUpdate)**: 기본 전략으로, 이전 버전의 포드를 점진적으로 새 버전으로 교체합니다.
2. **재생성(Recreate)**: 모든 기존 포드를 삭제한 후 새 포드를 생성합니다.

#### 롤링 업데이트 전략

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
      maxSurge: 1
      maxUnavailable: 1
  # ... 나머지 사양
```

- **maxSurge**: 원하는 포드 수를 초과하여 생성할 수 있는 최대 포드 수 (절대값 또는 백분율)
- **maxUnavailable**: 업데이트 중에 사용할 수 없는 최대 포드 수 (절대값 또는 백분율)

#### 재생성 전략

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: nginx-deployment
spec:
  replicas: 3
  strategy:
    type: Recreate
  # ... 나머지 사양
```

### 블루/그린 배포

블루/그린 배포는 Kubernetes의 기본 기능은 아니지만, 서비스와 레이블을 사용하여 구현할 수 있습니다.

1. 현재 버전(블루)이 실행 중입니다.
2. 새 버전(그린)을 별도의 디플로이먼트로 배포합니다.
3. 새 버전이 준비되면 서비스의 셀렉터를 업데이트하여 트래픽을 새 버전으로 전환합니다.
4. 문제가 없으면 이전 버전을 삭제합니다.

```yaml
# 블루 디플로이먼트
apiVersion: apps/v1
kind: Deployment
metadata:
  name: app-blue
spec:
  replicas: 3
  selector:
    matchLabels:
      app: my-app
      version: blue
  template:
    metadata:
      labels:
        app: my-app
        version: blue
    spec:
      containers:
      - name: app
        image: my-app:1.0
---
# 그린 디플로이먼트
apiVersion: apps/v1
kind: Deployment
metadata:
  name: app-green
spec:
  replicas: 3
  selector:
    matchLabels:
      app: my-app
      version: green
  template:
    metadata:
      labels:
        app: my-app
        version: green
    spec:
      containers:
      - name: app
        image: my-app:2.0
---
# 서비스
apiVersion: v1
kind: Service
metadata:
  name: my-app
spec:
  selector:
    app: my-app
    version: blue  # 트래픽을 블루 버전으로 라우팅
  ports:
  - port: 80
    targetPort: 8080
```

트래픽을 그린 버전으로 전환하려면 서비스의 셀렉터를 업데이트합니다:

```bash
kubectl patch service my-app -p '{"spec":{"selector":{"version":"green"}}}'
```

### 카나리 배포

카나리 배포는 새 버전을 점진적으로 출시하는 방법입니다. 일부 트래픽만 새 버전으로 라우팅하여 위험을 최소화합니다.

```yaml
# 기존 디플로이먼트
apiVersion: apps/v1
kind: Deployment
metadata:
  name: app-stable
spec:
  replicas: 9  # 90%의 트래픽
  selector:
    matchLabels:
      app: my-app
      version: stable
  template:
    metadata:
      labels:
        app: my-app
        version: stable
    spec:
      containers:
      - name: app
        image: my-app:1.0
---
# 카나리 디플로이먼트
apiVersion: apps/v1
kind: Deployment
metadata:
  name: app-canary
spec:
  replicas: 1  # 10%의 트래픽
  selector:
    matchLabels:
      app: my-app
      version: canary
  template:
    metadata:
      labels:
        app: my-app
        version: canary
    spec:
      containers:
      - name: app
        image: my-app:2.0
---
# 서비스
apiVersion: v1
kind: Service
metadata:
  name: my-app
spec:
  selector:
    app: my-app  # 버전을 지정하지 않아 두 디플로이먼트 모두에 트래픽 분산
  ports:
  - port: 80
    targetPort: 8080
```

카나리 배포가 성공적이면 점진적으로 카나리 디플로이먼트의 레플리카 수를 늘리고 기존 디플로이먼트의 레플리카 수를 줄입니다.

## 스테이트풀셋(StatefulSet)

스테이트풀셋은 상태를 유지해야 하는 애플리케이션을 위한 워크로드 리소스입니다. 디플로이먼트와 달리, 스테이트풀셋은 각 포드에 고유한 식별자를 제공하고, 순서대로 배포 및 스케일링됩니다.

### 스테이트풀셋의 특징

- 안정적이고 고유한 네트워크 식별자
- 안정적이고 지속적인 스토리지
- 순서대로 배포 및 스케일링
- 순서대로 자동 롤링 업데이트

### 스테이트풀셋 생성

```yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: web
spec:
  serviceName: "nginx"
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
          name: web
        volumeMounts:
        - name: www
          mountPath: /usr/share/nginx/html
  volumeClaimTemplates:
  - metadata:
      name: www
    spec:
      accessModes: [ "ReadWriteOnce" ]
      resources:
        requests:
          storage: 1Gi
```

이 예제는 3개의 레플리카를 가진 Nginx 스테이트풀셋을 생성합니다. 각 포드는 고유한 PVC를 가집니다.

### 헤드리스 서비스

스테이트풀셋은 일반적으로 헤드리스 서비스와 함께 사용됩니다. 헤드리스 서비스는 클러스터 IP가 없고 각 포드에 대한 DNS 레코드를 생성합니다.

```yaml
apiVersion: v1
kind: Service
metadata:
  name: nginx
spec:
  clusterIP: None  # 헤드리스 서비스
  selector:
    app: nginx
  ports:
  - port: 80
    name: web
```

### 포드 식별자

스테이트풀셋의 각 포드는 안정적인 호스트 이름을 가집니다. 호스트 이름은 `<스테이트풀셋 이름>-<순서 인덱스>`의 형식입니다. 예를 들어, `web-0`, `web-1`, `web-2` 등입니다.

### 스테이트풀셋 업데이트 전략

스테이트풀셋은 두 가지 업데이트 전략을 제공합니다:

1. **RollingUpdate**: 포드를 순서대로 업데이트합니다(기본값).
2. **OnDelete**: 포드가 삭제될 때만 업데이트합니다.

```yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: web
spec:
  updateStrategy:
    type: RollingUpdate
    rollingUpdate:
      partition: 2  # 인덱스가 2 이상인 포드만 업데이트
  # ... 나머지 사양
```

`partition` 필드를 사용하면 인덱스가 지정된 값 이상인 포드만 업데이트됩니다. 이를 통해 카나리 배포와 유사한 점진적 업데이트를 구현할 수 있습니다.

## 데몬셋(DaemonSet)

데몬셋은 모든 노드(또는 특정 노드)에서 포드의 복사본을 실행하는 워크로드 리소스입니다. 노드가 클러스터에 추가되면 포드가 자동으로 추가되고, 노드가 제거되면 포드도 제거됩니다.

### 데몬셋 사용 사례

- 로깅 에이전트(예: Fluentd, Logstash)
- 모니터링 에이전트(예: Prometheus Node Exporter)
- 네트워크 플러그인(예: Calico, Cilium)
- 스토리지 데몬(예: Ceph)

### 데몬셋 생성

```yaml
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: fluentd
  namespace: kube-system
spec:
  selector:
    matchLabels:
      name: fluentd
  template:
    metadata:
      labels:
        name: fluentd
    spec:
      containers:
      - name: fluentd
        image: fluentd:v1.7
        resources:
          limits:
            memory: 200Mi
          requests:
            cpu: 100m
            memory: 200Mi
        volumeMounts:
        - name: varlog
          mountPath: /var/log
      volumes:
      - name: varlog
        hostPath:
          path: /var/log
```

이 예제는 모든 노드에서 Fluentd 로깅 에이전트를 실행하는 데몬셋을 생성합니다.

### 특정 노드에서만 실행

노드 셀렉터, 어피니티, 테인트와 톨러레이션을 사용하여 데몬셋이 특정 노드에서만 실행되도록 제한할 수 있습니다.

```yaml
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: fluentd
spec:
  selector:
    matchLabels:
      name: fluentd
  template:
    metadata:
      labels:
        name: fluentd
    spec:
      nodeSelector:
        role: logging
      # ... 나머지 사양
```

이 예제에서는 `role=logging` 레이블이 있는 노드에서만 데몬셋이 실행됩니다.

### 데몬셋 업데이트 전략

데몬셋은 두 가지 업데이트 전략을 제공합니다:

1. **RollingUpdate**: 포드를 점진적으로 업데이트합니다(기본값).
2. **OnDelete**: 포드가 삭제될 때만 업데이트합니다.

```yaml
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: fluentd
spec:
  updateStrategy:
    type: RollingUpdate
    rollingUpdate:
      maxUnavailable: 1  # 한 번에 최대 1개의 포드가 사용 불가능
  # ... 나머지 사양
```

## 잡(Job)과 크론잡(CronJob)

잡과 크론잡은 일회성 또는 예약된 작업을 실행하는 워크로드 리소스입니다.

### 잡(Job)

잡은 하나 이상의 포드를 생성하고 지정된 수의 포드가 성공적으로 종료될 때까지 실행을 계속합니다.

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: pi
spec:
  completions: 5  # 5개의 성공적인 포드 완료가 필요
  parallelism: 2  # 최대 2개의 포드를 병렬로 실행
  backoffLimit: 4  # 최대 4번의 재시도
  activeDeadlineSeconds: 100  # 최대 100초 동안 실행
  template:
    spec:
      containers:
      - name: pi
        image: perl
        command: ["perl",  "-Mbignum=bpi", "-wle", "print bpi(2000)"]
      restartPolicy: Never
```

이 예제는 원주율(π)을 계산하는 잡을 생성합니다. 잡은 5개의 성공적인 포드 완료가 필요하며, 최대 2개의 포드를 병렬로 실행합니다.

### 잡 완료 모드

잡은 두 가지 완료 모드를 제공합니다:

1. **NonIndexed**: 기본 모드로, 모든 포드가 동일한 작업을 수행합니다.
2. **Indexed**: 각 포드에 고유한 인덱스가 할당되어 다른 작업을 수행할 수 있습니다.

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: indexed-job
spec:
  completions: 5
  parallelism: 3
  completionMode: Indexed
  template:
    spec:
      containers:
      - name: worker
        image: busybox
        command: ["sh", "-c", "echo Job completion index: ${JOB_COMPLETION_INDEX}"]
      restartPolicy: Never
```

이 예제에서는 각 포드가 자신의 인덱스를 출력합니다. 인덱스는 환경 변수 `JOB_COMPLETION_INDEX`를 통해 제공됩니다.

### 크론잡(CronJob)

크론잡은 지정된 일정에 따라 잡을 주기적으로 생성합니다. 크론 표현식을 사용하여 일정을 정의합니다.

```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: hello
spec:
  schedule: "*/1 * * * *"  # 매분마다 실행
  timeZone: "Asia/Seoul"   # 타임존 지정 (Kubernetes 1.24+)
  concurrencyPolicy: Forbid  # 동시 실행 금지
  startingDeadlineSeconds: 120  # 최대 120초 지연 허용
  successfulJobsHistoryLimit: 3  # 최근 성공한 잡 3개 유지
  failedJobsHistoryLimit: 1  # 최근 실패한 잡 1개 유지
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: hello
            image: busybox
            command: ["sh", "-c", "echo Hello from the Kubernetes cluster; date"]
          restartPolicy: OnFailure
```

이 예제는 매분마다 "Hello from the Kubernetes cluster"와 현재 날짜를 출력하는 크론잡을 생성합니다.

### 크론 표현식

크론 표현식은 다음과 같은 형식을 가집니다:

```
┌───────────── 분 (0 - 59)
│ ┌───────────── 시 (0 - 23)
│ │ ┌───────────── 일 (1 - 31)
│ │ │ ┌───────────── 월 (1 - 12)
│ │ │ │ ┌───────────── 요일 (0 - 6) (일요일부터 토요일까지)
│ │ │ │ │
│ │ │ │ │
* * * * *
```

일반적인 크론 표현식 예:

- `*/1 * * * *`: 매분마다
- `0 * * * *`: 매시간 정각마다
- `0 0 * * *`: 매일 자정마다
- `0 0 * * 0`: 매주 일요일 자정마다
- `0 0 1 * *`: 매월 1일 자정마다
- `0 0 1 1 *`: 매년 1월 1일 자정마다

### 동시성 정책

크론잡은 세 가지 동시성 정책을 제공합니다:

1. **Allow**: 여러 잡이 동시에 실행될 수 있습니다(기본값).
2. **Forbid**: 이전 잡이 아직 실행 중이면 새 잡을 건너뜁니다.
3. **Replace**: 이전 잡이 아직 실행 중이면 새 잡으로 대체합니다.

## 롤링 업데이트와 롤백

Kubernetes는 애플리케이션을 중단 없이 업데이트하고 문제가 발생할 경우 이전 버전으로 롤백하는 기능을 제공합니다.

### 롤링 업데이트

롤링 업데이트는 애플리케이션을 점진적으로 업데이트하는 프로세스입니다. 이전 버전의 포드를 하나씩 새 버전으로 교체하여 다운타임을 최소화합니다.

디플로이먼트 이미지 업데이트:

```bash
kubectl set image deployment/nginx-deployment nginx=nginx:1.16.1
```

또는 디플로이먼트 매니페스트를 직접 편집:

```bash
kubectl edit deployment/nginx-deployment
```

롤링 업데이트 상태 확인:

```bash
kubectl rollout status deployment/nginx-deployment
```

### 롤백

문제가 발생하면 이전 버전으로 롤백할 수 있습니다.

롤아웃 기록 확인:

```bash
kubectl rollout history deployment/nginx-deployment
```

특정 버전의 세부 정보 확인:

```bash
kubectl rollout history deployment/nginx-deployment --revision=2
```

이전 버전으로 롤백:

```bash
kubectl rollout undo deployment/nginx-deployment
```

특정 버전으로 롤백:

```bash
kubectl rollout undo deployment/nginx-deployment --to-revision=2
```

### 롤아웃 일시 중지 및 재개

롤아웃을 일시 중지하여 점진적으로 업데이트를 제어할 수 있습니다.

롤아웃 일시 중지:

```bash
kubectl rollout pause deployment/nginx-deployment
```

롤아웃 재개:

```bash
kubectl rollout resume deployment/nginx-deployment
```

## 결론

이 장에서는 Kubernetes의 다양한 워크로드 리소스에 대해 알아보았습니다. 디플로이먼트는 상태가 없는 애플리케이션을 관리하는 데 적합하고, 스테이트풀셋은 상태를 유지해야 하는 애플리케이션에 적합합니다. 데몬셋은 모든 노드에서 실행해야 하는 백그라운드 서비스에 유용하며, 잡과 크론잡은 일회성 또는 예약된 작업을 실행하는 데 사용됩니다.

각 워크로드 리소스는 고유한 특성과 사용 사례를 가지고 있으므로, 애플리케이션의 요구 사항에 맞는 적절한 리소스를 선택하는 것이 중요합니다. 또한, 롤링 업데이트와 롤백 기능을 활용하여 애플리케이션을 안전하게 업데이트하고 문제가 발생할 경우 빠르게 복구할 수 있습니다.

다음 장에서는 서비스와 네트워킹에 대해 알아보겠습니다.

## 참고 자료

- [Kubernetes 공식 문서 - 디플로이먼트](https://kubernetes.io/docs/concepts/workloads/controllers/deployment/)
- [Kubernetes 공식 문서 - 스테이트풀셋](https://kubernetes.io/docs/concepts/workloads/controllers/statefulset/)
- [Kubernetes 공식 문서 - 데몬셋](https://kubernetes.io/docs/concepts/workloads/controllers/daemonset/)
- [Kubernetes 공식 문서 - 잡](https://kubernetes.io/docs/concepts/workloads/controllers/job/)
- [Kubernetes 공식 문서 - 크론잡](https://kubernetes.io/docs/concepts/workloads/controllers/cron-jobs/)
- [Kubernetes 공식 문서 - 롤링 업데이트](https://kubernetes.io/docs/tutorials/kubernetes-basics/update/update-intro/)
