# 파드와 워크로드 퀴즈

이 퀴즈는 Kubernetes의 기본 실행 단위인 파드(Pod)와 이를 관리하는 다양한 워크로드 리소스에 대한 이해도를 테스트합니다.

## 객관식 문제

1. Kubernetes에서 가장 작은 배포 가능한 컴퓨팅 단위는 무엇인가요?
   - A) 컨테이너
   - B) 파드(Pod)
   - C) 디플로이먼트(Deployment)
   - D) 노드(Node)
   
<details>

<summary>정답 보기</summary>

**정답: B) 파드(Pod)**

**설명:**
파드(Pod)는 Kubernetes의 가장 작은 배포 가능한 컴퓨팅 단위입니다. 파드는 하나 이상의 컨테이너 그룹으로, 스토리지와 네트워크를 공유하며 함께 스케줄링됩니다. 컨테이너는 파드 내에 포함되는 더 작은 단위이지만, Kubernetes에서 직접 관리하는 배포 단위는 아닙니다.
</details>

2. 다음 중 파드(Pod)의 특징이 아닌 것은 무엇인가요?
   - A) 파드 내의 모든 컨테이너는 동일한 IP 주소를 공유한다
   - B) 파드 내의 모든 컨테이너는 항상 같은 노드에서 실행된다
   - C) 파드는 여러 노드에 걸쳐 실행될 수 있다
   - D) 파드는 고유한 IP 주소를 가진다
   
<details>

<summary>정답 보기</summary>

**정답: C) 파드는 여러 노드에 걸쳐 실행될 수 있다**

**설명:**
파드의 모든 컨테이너는 항상 같은 노드에서 실행됩니다. 파드는 여러 노드에 걸쳐 실행될 수 없습니다. 이는 파드의 기본 특성 중 하나로, 파드 내의 컨테이너들이 로컬 통신을 하고 볼륨을 공유할 수 있도록 합니다. 파드 내의 모든 컨테이너는 동일한 네트워크 네임스페이스를 공유하므로 동일한 IP 주소를 가지며, 각 파드는 클러스터 내에서 고유한 IP 주소를 가집니다.
</details>

3. 다중 컨테이너 파드에서 주 컨테이너의 기능을 확장하는 보조 컨테이너 패턴은 무엇인가요?
   - A) 앰배서더(Ambassador) 패턴
   - B) 사이드카(Sidecar) 패턴
   - C) 어댑터(Adapter) 패턴
   - D) 초기화(Init) 패턴
   
<details>

<summary>정답 보기</summary>

**정답: B) 사이드카(Sidecar) 패턴**

**설명:**
사이드카 패턴은 주 컨테이너의 기능을 확장하는 보조 컨테이너를 추가하는 패턴입니다. 예를 들어, 로그 수집기, 파일 동기화, 프록시 등이 사이드카 컨테이너로 구현될 수 있습니다. 앰배서더 패턴은 외부 서비스에 대한 프록시 역할을 하는 컨테이너를 추가하는 패턴이고, 어댑터 패턴은 주 컨테이너의 출력을 표준화하는 컨테이너를 추가하는 패턴입니다. 초기화 패턴은 주 컨테이너 시작 전에 실행되는 컨테이너를 추가하는 패턴입니다.
</details>

4. 파드의 컨테이너가 요청을 처리할 준비가 되었는지 확인하고, 실패 시 서비스 트래픽에서 제외하는 프로브는 무엇인가요?
   - A) livenessProbe
   - B) readinessProbe
   - C) startupProbe
   - D) healthProbe
   
<details>

<summary>정답 보기</summary>

**정답: B) readinessProbe**

**설명:**
readinessProbe는 컨테이너가 요청을 처리할 준비가 되었는지 확인하고, 실패 시 서비스 트래픽에서 제외합니다. livenessProbe는 컨테이너가 살아있는지 확인하고, 실패 시 컨테이너를 재시작합니다. startupProbe는 컨테이너 내의 애플리케이션이 시작되었는지 확인하고, 성공할 때까지 다른 프로브를 비활성화합니다. healthProbe는 Kubernetes에 존재하지 않는 프로브입니다.
</details>

5. 다음 중 레플리카셋(ReplicaSet)의 주요 기능이 아닌 것은 무엇인가요?
   - A) 지정된 수의 파드 복제본을 유지
   - B) 파드가 실패하거나 삭제되면 자동으로 대체 파드 생성
   - C) 롤링 업데이트 수행
   - D) 레이블 셀렉터를 통해 관리할 파드 식별
   
<details>

<summary>정답 보기</summary>

**정답: C) 롤링 업데이트 수행**

**설명:**
롤링 업데이트는 디플로이먼트(Deployment)의 주요 기능이며, 레플리카셋은 이를 직접 지원하지 않습니다. 레플리카셋의 주요 기능은 지정된 수의 파드 복제본을 유지하고, 파드가 실패하거나 삭제되면 자동으로 대체 파드를 생성하며, 레이블 셀렉터를 통해 관리할 파드를 식별하는 것입니다. 디플로이먼트는 레플리카셋을 관리하여 롤링 업데이트, 롤백 등의 기능을 제공합니다.
</details>

6. 기본 Deployment 업데이트 전략이 아닌 것은 무엇인가요? (두 개 선택)
   - A) RollingUpdate
   - B) Recreate
   - C) BlueGreen
   - D) Canary
   
<details>

<summary>정답 보기</summary>

**정답: C) BlueGreen, D) Canary**

**설명:**
Kubernetes 디플로이먼트는 기본적으로 RollingUpdate와 Recreate 두 가지 업데이트 전략을 제공합니다. BlueGreen과 Canary는 배포 패턴이지만, Kubernetes 디플로이먼트의 기본 업데이트 전략으로 직접 제공되지는 않습니다. 이러한 패턴은 서비스, 인그레스 등 다른 Kubernetes 리소스와 함께 구현하거나, Argo Rollouts와 같은 추가 도구를 사용하여 구현할 수 있습니다.
</details>

7. 상태 유지가 필요한 애플리케이션을 위한 워크로드 리소스는 무엇인가요?
   - A) 디플로이먼트(Deployment)
   - B) 레플리카셋(ReplicaSet)
   - C) 스테이트풀셋(StatefulSet)
   - D) 데몬셋(DaemonSet)
   
<details>

<summary>정답 보기</summary>

**정답: C) 스테이트풀셋(StatefulSet)**

**설명:**
스테이트풀셋(StatefulSet)은 상태 유지가 필요한 애플리케이션을 위한 워크로드 리소스입니다. 각 파드에 고유한 식별자를 부여하고, 안정적인 네트워크 식별자와 영구 스토리지를 제공합니다. 데이터베이스, 분산 시스템, 메시지 큐 등 상태를 유지해야 하는 애플리케이션에 적합합니다. 디플로이먼트와 레플리카셋은 상태가 없는 애플리케이션을 위한 것이고, 데몬셋은 모든 노드에서 파드의 복사본을 실행하도록 보장합니다.
</details>

8. 모든 노드(또는 특정 노드)에서 파드의 복사본을 실행하도록 보장하는 워크로드 리소스는 무엇인가요?
   - A) 디플로이먼트(Deployment)
   - B) 레플리카셋(ReplicaSet)
   - C) 스테이트풀셋(StatefulSet)
   - D) 데몬셋(DaemonSet)
   
<details>

<summary>정답 보기</summary>

**정답: D) 데몬셋(DaemonSet)**

**설명:**
데몬셋(DaemonSet)은 모든 노드(또는 특정 노드)에서 파드의 복사본을 실행하도록 보장합니다. 노드가 클러스터에 추가되면 파드가 자동으로 추가되고, 노드가 제거되면 파드도 제거됩니다. 로그 수집기, 모니터링 에이전트, 네트워크 플러그인과 같은 백그라운드 서비스를 실행하는 데 주로 사용됩니다. 디플로이먼트와 레플리카셋은 지정된 수의 파드 복제본을 유지하고, 스테이트풀셋은 상태 유지가 필요한 애플리케이션을 위한 것입니다.
</details>

9. 일회성 작업을 실행하기 위한 워크로드 리소스는 무엇인가요?
   - A) 디플로이먼트(Deployment)
   - B) 잡(Job)
   - C) 크론잡(CronJob)
   - D) 데몬셋(DaemonSet)
   
<details>

<summary>정답 보기</summary>

**정답: B) 잡(Job)**

**설명:**
잡(Job)은 하나 이상의 파드를 생성하고 지정된 수의 파드가 성공적으로 종료될 때까지 실행을 계속하는 워크로드 리소스입니다. 일회성 작업을 실행하기 위해 사용됩니다. 디플로이먼트는 지속적으로 실행되는 애플리케이션을 위한 것이고, 크론잡은 일정에 따라 잡을 주기적으로 실행하며, 데몬셋은 모든 노드에서 파드의 복사본을 실행합니다.
</details>

10. 일정에 따라 작업을 주기적으로 실행하는 워크로드 리소스는 무엇인가요?
    - A) 디플로이먼트(Deployment)
    - B) 잡(Job)
    - C) 크론잡(CronJob)
    - D) 스테이트풀셋(StatefulSet)
    
<details>

<summary>정답 보기</summary>

**정답: C) 크론잡(CronJob)**

**설명:**
크론잡(CronJob)은 지정된 일정에 따라 잡을 주기적으로 실행하는 워크로드 리소스입니다. 리눅스 크론 작업과 유사한 방식으로 작동하며, 백업, 보고서 생성, 이메일 전송 등의 정기적인 작업에 사용됩니다. 디플로이먼트는 지속적으로 실행되는 애플리케이션을 위한 것이고, 잡은 일회성 작업을 실행하며, 스테이트풀셋은 상태 유지가 필요한 애플리케이션을 위한 것입니다.
</details>
## 단답형 문제

11. 파드 내의 컨테이너가 시작되기 전에 실행되는 특수한 컨테이너의 이름은 무엇인가요?

<details>

<summary>정답 보기</summary>

**정답: 초기화 컨테이너(Init Container)**

**설명:**
초기화 컨테이너(Init Container)는 파드의 앱 컨테이너가 시작되기 전에 실행되는 특수한 컨테이너입니다. 초기화 컨테이너는 정의된 순서대로 하나씩 실행되며, 각 초기화 컨테이너는 이전 컨테이너가 성공적으로 완료된 후에만 시작됩니다. 초기화 컨테이너가 실패하면 파드의 재시작 정책에 따라 재시작됩니다. 주로 앱 컨테이너 시작 전 설정, 의존성 확인, 권한 설정 등에 사용됩니다.
</details>

12. 이미지·컨테이너에서 변경하지 않은 경우 파드 종료 시 기본 종료 신호는 무엇인가요?

<details>

<summary>정답 보기</summary>

**정답: SIGTERM**

**설명:**
파드가 종료될 때 kubelet은 preStop 훅이 있으면 먼저 실행한 뒤 런타임에 기본 SIGTERM 전송을 요청합니다. 훅 실행 시간도 유예 시간에 포함되며 이미지 STOPSIGNAL 또는 지원되는 컨테이너 설정으로 신호를 변경할 수 있습니다. 이는 애플리케이션이 그레이스풀하게 종료될 시간을 제공합니다. 기본 종료 기간(30초) 후에도 컨테이너가 종료되지 않으면 SIGKILL 신호가 전송됩니다. 애플리케이션은 SIGTERM 신호를 받으면 진행 중인 작업을 완료하고, 연결을 닫고, 리소스를 정리하는 등의 작업을 수행할 수 있습니다.
</details>

13. 디플로이먼트(Deployment)가 관리하는 리소스의 이름은 무엇인가요?

<details>

<summary>정답 보기</summary>

**정답: 레플리카셋(ReplicaSet)**

**설명:**
디플로이먼트(Deployment)는 레플리카셋(ReplicaSet)을 관리합니다. 디플로이먼트는 레플리카셋을 생성하고, 레플리카셋은 파드를 생성하고 관리합니다. 디플로이먼트는 레플리카셋을 통해 롤링 업데이트, 롤백, 스케일링 등의 기능을 제공합니다. 새로운 버전의 애플리케이션을 배포할 때, 디플로이먼트는 새로운 레플리카셋을 생성하고 이전 레플리카셋을 점진적으로 축소합니다.
</details>

14. 스테이트풀셋(StatefulSet)에서 파드에 부여되는 고유한 식별자의 형식은 무엇인가요? (예: 스테이트풀셋 이름이 'web'인 경우)

<details>

<summary>정답 보기</summary>

**정답: \<스테이트풀셋 이름\>-\<순서 인덱스\> (예: web-0, web-1, web-2)**

**설명:**
스테이트풀셋(StatefulSet)은 파드에 `<스테이트풀셋 이름>-<순서 인덱스>` 형식의 고유한 식별자를 부여합니다. 예를 들어, `web` 스테이트풀셋은 `web-0`, `web-1`, `web-2`와 같은 파드를 생성합니다. 이 식별자는 파드가 재스케줄링되더라도 유지되며, 안정적인 네트워크 식별자와 영구 스토리지를 제공하는 데 사용됩니다.
</details>

15. 크론잡(CronJob)에서 이전 잡이 아직 실행 중일 때 새 잡을 건너뛰는 동시성 정책은 무엇인가요?

<details>

<summary>정답 보기</summary>

**정답: Forbid**

**설명:**
크론잡(CronJob)의 `Forbid` 동시성 정책은 이전 잡이 아직 실행 중이면 새 잡을 건너뜁니다. 크론잡은 세 가지 동시성 정책을 제공합니다: `Allow`(여러 잡이 동시에 실행될 수 있음, 기본값), `Forbid`(이전 잡이 아직 실행 중이면 새 잡을 건너뜀), `Replace`(이전 잡이 아직 실행 중이면 새 잡으로 대체). 이러한 정책은 `concurrencyPolicy` 필드를 통해 설정할 수 있습니다.
</details>
## 실습 문제

16. 다음 요구사항을 충족하는 다중 컨테이너 파드 YAML 파일을 작성하세요:
    - 파드 이름: web-app
    - 첫 번째 컨테이너: nginx 웹 서버 (이미지: nginx:1.30.4)
    - 두 번째 컨테이너: 로그 수집기 (이미지: fluentd:v1.14)
    - 두 컨테이너 간에 로그 디렉토리를 공유하는 emptyDir 볼륨
    - nginx 컨테이너는 포트 80 노출
    - 로그 볼륨은 nginx 컨테이너에서는 /var/log/nginx에, fluentd 컨테이너에서는 /fluentd/log에 마운트

<details>

<summary>정답 보기</summary>

**정답:**
```yaml
apiVersion: v1
kind: Pod
metadata:
  name: web-app
spec:
  containers:
    - name: nginx
      image: nginx:1.30.4
      ports:
        - containerPort: 80
      volumeMounts:
        - name: log-volume
          mountPath: /var/log/nginx
    - name: log-collector
      image: fluentd:v1.14
      volumeMounts:
        - name: log-volume
          mountPath: /fluentd/log
  volumes:
    - name: log-volume
      emptyDir: {}
```

**설명:**
이 YAML 파일은 nginx 웹 서버와 fluentd 로그 수집기를 포함하는 다중 컨테이너 파드를 정의합니다. `log-volume`이라는 emptyDir 볼륨을 생성하고, nginx 컨테이너에서는 `/var/log/nginx`에, fluentd 컨테이너에서는 `/fluentd/log`에 마운트합니다. 이렇게 파일을 공유하지만 실제 수집에는 `/fluentd/log/*.log`용 Fluentd tail 입력과 출력 설정이 추가로 필요합니다. nginx 컨테이너는 포트 80을 노출합니다. 이는 사이드카 패턴의 예시입니다.
</details>

17. 다음 요구사항을 충족하는 디플로이먼트(Deployment) YAML 파일을 작성하세요:
    - 이름: nginx-deployment
    - 레이블: app=nginx, tier=frontend
    - 복제본 수: 3
    - 롤링 업데이트 전략: 최대 서지 1, 최대 불가용 0
    - 컨테이너 이미지: nginx:1.30.4
    - 컨테이너 포트: 80
    - 리소스 요청: CPU 100m, 메모리 128Mi
    - 리소스 제한: CPU 200m, 메모리 256Mi
    - 활성 프로브: HTTP GET /, 초기 지연 30초, 주기 10초
    - 준비성 프로브: HTTP GET /, 초기 지연 5초, 주기 5초

<details>

<summary>정답 보기</summary>

**정답:**
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: nginx-deployment
  labels:
    app: nginx
    tier: frontend
spec:
  replicas: 3
  selector:
    matchLabels:
      app: nginx
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0
  template:
    metadata:
      labels:
        app: nginx
        tier: frontend
    spec:
      containers:
        - name: nginx
          image: nginx:1.30.4
          ports:
            - containerPort: 80
          resources:
            requests:
              cpu: 100m
              memory: 128Mi
            limits:
              cpu: 200m
              memory: 256Mi
          livenessProbe:
            httpGet:
              path: /
              port: 80
            initialDelaySeconds: 30
            periodSeconds: 10
          readinessProbe:
            httpGet:
              path: /
              port: 80
            initialDelaySeconds: 5
            periodSeconds: 5
```

**설명:**
이 YAML 파일은 nginx:1.30.4 이미지를 사용하는 3개의 복제본을 가진 디플로이먼트를 정의합니다. 롤링 업데이트 전략은 최대 서지 1(원하는 파드 수 이상으로 생성할 수 있는 최대 파드 수)과 최대 불가용 0(업데이트 중 사용할 수 없는 최대 파드 수)으로 설정되어 있어, 다운타임 없이 업데이트가 가능합니다. 각 컨테이너는 포트 80을 노출하고, CPU 요청 100m, 메모리 요청 128Mi, CPU 제한 200m, 메모리 제한 256Mi의 리소스 제약을 가집니다. 활성 프로브와 준비성 프로브는 HTTP GET 요청을 통해 컨테이너의 상태를 확인합니다.
</details>

18. 다음 요구사항을 충족하는 크론잡(CronJob) YAML 파일을 작성하세요:
    - 이름: database-backup
    - 일정: 매일 UTC 오전 2시 실행 (cron 표현식과 timeZone 사용)
    - 동시성 정책: Forbid
    - 성공한 작업 이력 제한: 3
    - 실패한 작업 이력 제한: 1
    - 컨테이너 이미지: postgres:14
    - 명령어: pg_dump -Fc > /backup/db-$(date +%Y%m%d-%H%M%S).dump
    - 환경 변수: PGHOST=postgres-service, PGUSER와 PGPASSWORD는 postgres-secret에서 가져옴
    - 볼륨: backup-pvc를 /backup에 마운트
    - 재시작 정책: OnFailure

<details>

<summary>정답 보기</summary>

**정답:**
```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: database-backup
spec:
  schedule: "0 2 * * *"
  timeZone: "Etc/UTC"
  concurrencyPolicy: Forbid
  successfulJobsHistoryLimit: 3
  failedJobsHistoryLimit: 1
  jobTemplate:
    spec:
      template:
        spec:
          containers:
            - name: backup
              image: postgres:14
              env:
                - name: PGHOST
                  value: postgres-service
                - name: PGUSER
                  valueFrom:
                    secretKeyRef:
                      name: postgres-secret
                      key: username
                - name: PGPASSWORD
                  valueFrom:
                    secretKeyRef:
                      name: postgres-secret
                      key: password
              command:
                - /bin/sh
                - -c
                - pg_dump -Fc > /backup/db-$(date +%Y%m%d-%H%M%S).dump
              volumeMounts:
                - name: backup-volume
                  mountPath: /backup
          restartPolicy: OnFailure
          volumes:
            - name: backup-volume
              persistentVolumeClaim:
                claimName: backup-pvc
```

**설명:**
이 YAML 파일은 매일 오전 2시에 실행되는 데이터베이스 백업 크론잡을 정의합니다. `concurrencyPolicy: Forbid`는 이전 작업이 아직 실행 중이면 새 작업을 건너뛰도록 설정합니다. `successfulJobsHistoryLimit: 3`과 `failedJobsHistoryLimit: 1`은 성공한 작업과 실패한 작업의 이력을 각각 3개와 1개로 제한합니다. 컨테이너는 postgres:14 이미지를 사용하고, pg_dump 명령어를 실행하여 데이터베이스를 백업합니다. 환경 변수 PGHOST는 직접 값을 설정하고, PGUSER와 PGPASSWORD는 postgres-secret에서 가져옵니다. backup-pvc 볼륨을 /backup 디렉토리에 마운트하여 백업 파일을 저장합니다. 재시작 정책은 OnFailure로 설정되어 있어, 작업이 실패하면 컨테이너를 재시작합니다.
</details>
## 심화 문제

19. 기본(primary) 1개와 복제본 2개인 MySQL 클러스터에서 StatefulSet이 제공하는 기능과 DB 오퍼레이터·복제 컨트롤러가 담당해야 하는 기능을 구분하세요. 일반 init 컨테이너에서 로컬 MySQL 서버를 설정하려는 방식이 잘못된 이유는 무엇인가요?

<details>
<summary>정답 보기</summary>

**정답:**

- StatefulSet은 안정적인 파드 이름, 헤드리스 Service, 파드별 PVC, 기본적으로 순서가 있는 스케일링을 제공합니다. 스토리지 사용이 가능하면 실패한 파드를 같은 ordinal과 볼륨으로 대체합니다.
- DB 데이터 복사, 복제 설정, primary 선출·승격, 이전 primary 차단, 클라이언트 연결 전환은 제공하지 않습니다. 검증된 DB 오퍼레이터·운영 절차가 복제 자격 증명, 백업, 복원 확인과 함께 이를 구현해야 합니다.
- 일반 init 컨테이너는 로컬 앱 컨테이너 시작 전에 완료되어야 합니다. 아직 시작하지 않은 MySQL 서버에 init 컨테이너가 SQL 연결을 시도해서는 설정할 수 없습니다. 복제 설정은 적절한 DB 수명 주기 단계에서 수행해야 합니다.
- 독립 MySQL 파드 3개는 복제된 HA 데이터베이스가 아닙니다. 복제본의 server ID를 중복 사용하거나 ConfigMap에 복제 비밀번호를 넣는 방식도 잘못되었습니다.
- 본문의 단일 인스턴스 StatefulSet은 Kubernetes 식별자·스토리지 연결 예시입니다. 복제본 수를 3으로 늘리는 것만으로 복제·자동 장애 조치가 구성되지는 않습니다.

</details>

20. 다양한 워크로드 리소스(디플로이먼트, 스테이트풀셋, 데몬셋, 잡, 크론잡)의 특성과 사용 사례를 비교하고, 다음 시나리오에 가장 적합한 워크로드 리소스를 선택하고 그 이유를 설명하세요:
    - 웹 애플리케이션 프론트엔드
    - 분산 데이터베이스 클러스터
    - 로그 수집 에이전트
    - 일일 데이터 백업
    - 일회성 데이터 마이그레이션

<details>

<summary>정답 보기</summary>

**정답:**

**워크로드 리소스 비교**

| 워크로드 리소스 | 주요 특성 | 사용 사례 |
|--------------|---------|---------|
| **디플로이먼트(Deployment)** | - 상태가 없는 애플리케이션<br>- 롤링 업데이트 지원<br>- 자동 스케일링<br>- 레플리카셋 관리 | - 웹 서버<br>- API 서버<br>- 상태가 없는 마이크로서비스<br>- 프론트엔드 애플리케이션 |
| **스테이트풀셋(StatefulSet)** | - 안정적인 네트워크 식별자<br>- 영구 스토리지<br>- 순차적인 배포 및 스케일링<br>- 순서가 보장된 파드 생성 | - 데이터베이스<br>- 분산 시스템<br>- 메시지 큐<br>- 상태 유지 애플리케이션 |
| **데몬셋(DaemonSet)** | - 모든 노드에서 실행<br>- 노드 추가 시 자동 배포<br>- 노드 제거 시 자동 정리<br>- 노드 선택 가능 | - 로그 수집기<br>- 모니터링 에이전트<br>- 네트워크 플러그인<br>- 스토리지 데몬 |
| **잡(Job)** | - 일회성 작업<br>- 완료 추적 (실패 가능)<br>- 병렬 실행 가능<br>- 실패 시 재시도 | - 배치 처리<br>- 데이터 마이그레이션<br>- 계산 작업<br>- 일회성 관리 작업 |
| **크론잡(CronJob)** | - 일정에 따른 실행<br>- 주기적인 작업<br>- 동시성 정책<br>- 이력 제한 | - 정기 백업<br>- 데이터 동기화<br>- 보고서 생성<br>- 정리 작업 |

**시나리오별 적합한 워크로드 리소스**

1. **웹 애플리케이션 프론트엔드**
  - **적합한 리소스: 디플로이먼트(Deployment)**
  - **이유**: 웹 애플리케이션 프론트엔드는 일반적으로 상태가 없는(stateless) 애플리케이션입니다. 디플로이먼트는 롤링 업데이트를 통해 다운타임 없이 새 버전을 배포할 수 있고, 수평적 확장이 용이하며, 자동 복구 기능을 제공합니다. 또한 HorizontalPodAutoscaler와 함께 사용하여 트래픽에 따라 자동으로 스케일링할 수 있습니다.

2. **분산 데이터베이스 클러스터**
  - **적합한 리소스: 스테이트풀셋(StatefulSet)**
  - **이유**: 분산 데이터베이스는 상태 유지가 필요하고, 각 인스턴스가 고유한 식별자와 영구 스토리지를 필요로 합니다. 스테이트풀셋은 안정적인 네트워크 식별자(`<StatefulSet 이름>-<순서 인덱스>`)와 영구 스토리지를 제공하며, 순차적인 배포·스케일링을 지원하지만 데이터 복제와 일관성은 DB가 구현해야 합니다. 예를 들어, MySQL, PostgreSQL, MongoDB, Cassandra 등의 분산 데이터베이스 클러스터에 적합합니다.

3. **로그 수집 에이전트**
  - **적합한 리소스: 데몬셋(DaemonSet)**
  - **이유**: 로그 수집 에이전트는 클러스터의 모든 노드에서 실행되어야 합니다. 데몬셋은 모든 노드(또는 특정 노드)에서 파드의 복사본을 실행하도록 보장하며, 새 노드가 클러스터에 추가되면 자동으로 로그 수집 에이전트를 배포합니다. Fluentd, Logstash, Filebeat 등의 로그 수집 에이전트를 배포하는 데 적합합니다.

4. **일일 데이터 백업**
  - **적합한 리소스: 크론잡(CronJob)**
  - **이유**: 일일 데이터 백업은 정해진 일정에 따라 주기적으로 실행되어야 하는 작업입니다. 크론잡은 cron 표현식을 사용하여 실행 일정을 지정할 수 있으며, 매일 특정 시간에 백업 작업을 실행하도록 설정할 수 있습니다. 또한 `concurrencyPolicy`를 통해 이전 백업이 아직 실행 중일 때의 동작을 정의할 수 있고, Job 이력을 제한할 수 있으며 백업 파일 보존에는 별도 정책이 필요합니다.

5. **일회성 데이터 마이그레이션**
  - **적합한 리소스: 잡(Job)**
  - **이유**: 데이터 마이그레이션은 일회성 작업으로, 성공적으로 완료되어야 합니다. 잡은 지정된 수의 파드가 성공적으로 종료될 때까지 실행을 계속하며, 실패 시 재시도 메커니즘을 제공합니다. 또한 `parallelism` 설정을 통해 여러 파드를 병렬로 실행하여 대규모 데이터 마이그레이션을 더 빠르게 처리할 수 있습니다.

**결론**

각 워크로드 리소스는 특정 사용 사례에 맞게 설계되었으며, 애플리케이션의 요구사항에 따라 적절한 리소스를 선택하는 것이 중요합니다. 디플로이먼트는 상태가 없는 애플리케이션에, 스테이트풀셋은 상태 유지가 필요한 애플리케이션에, 데몬셋은 모든 노드에서 실행해야 하는 서비스에, 잡은 일회성 작업에, 크론잡은 주기적인 작업에 적합합니다. 이러한 특성을 이해하고 적절한 워크로드 리소스를 선택하면 Kubernetes에서 애플리케이션을 효율적으로 관리할 수 있습니다.
</details>

---

[학습 자료로 돌아가기](../../core/02-pods-and-workloads.md) | [다음 퀴즈: 서비스와 네트워킹](../core/03-services-networking-quiz.md)
