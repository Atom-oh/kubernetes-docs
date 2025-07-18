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

6. 다음 중 디플로이먼트(Deployment)의 업데이트 전략이 아닌 것은 무엇인가요?
   - A) RollingUpdate
   - B) Recreate
   - C) BlueGreen
   - D) Canary
   
   <details>

   <summary>정답 보기</summary>
   
   **정답: C) BlueGreen**
   
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

12. 파드가 종료될 때 컨테이너에 처음으로 전송되는 신호는 무엇인가요?

    <details>

    <summary>정답 보기</summary>
    
    **정답: SIGTERM**
    
    **설명:**
    파드가 종료될 때 kubelet은 컨테이너에 먼저 SIGTERM 신호를 전송합니다. 이는 애플리케이션이 그레이스풀하게 종료될 시간을 제공합니다. 기본 종료 기간(30초) 후에도 컨테이너가 종료되지 않으면 SIGKILL 신호가 전송됩니다. 애플리케이션은 SIGTERM 신호를 받으면 진행 중인 작업을 완료하고, 연결을 닫고, 리소스를 정리하는 등의 작업을 수행할 수 있습니다.
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
    - 첫 번째 컨테이너: nginx 웹 서버 (이미지: nginx:1.21)
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
        image: nginx:1.21
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
    이 YAML 파일은 nginx 웹 서버와 fluentd 로그 수집기를 포함하는 다중 컨테이너 파드를 정의합니다. `log-volume`이라는 emptyDir 볼륨을 생성하고, nginx 컨테이너에서는 `/var/log/nginx`에, fluentd 컨테이너에서는 `/fluentd/log`에 마운트합니다. 이를 통해 nginx가 생성한 로그를 fluentd가 수집할 수 있습니다. nginx 컨테이너는 포트 80을 노출합니다. 이는 사이드카 패턴의 예시입니다.
    </details>

17. 다음 요구사항을 충족하는 디플로이먼트(Deployment) YAML 파일을 작성하세요:
    - 이름: nginx-deployment
    - 레이블: app=nginx, tier=frontend
    - 복제본 수: 3
    - 롤링 업데이트 전략: 최대 서지 1, 최대 불가용 0
    - 컨테이너 이미지: nginx:1.21
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
            image: nginx:1.21
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
    이 YAML 파일은 nginx:1.21 이미지를 사용하는 3개의 복제본을 가진 디플로이먼트를 정의합니다. 롤링 업데이트 전략은 최대 서지 1(원하는 파드 수 이상으로 생성할 수 있는 최대 파드 수)과 최대 불가용 0(업데이트 중 사용할 수 없는 최대 파드 수)으로 설정되어 있어, 다운타임 없이 업데이트가 가능합니다. 각 컨테이너는 포트 80을 노출하고, CPU 요청 100m, 메모리 요청 128Mi, CPU 제한 200m, 메모리 제한 256Mi의 리소스 제약을 가집니다. 활성 프로브와 준비성 프로브는 HTTP GET 요청을 통해 컨테이너의 상태를 확인합니다.
    </details>

18. 다음 요구사항을 충족하는 크론잡(CronJob) YAML 파일을 작성하세요:
    - 이름: database-backup
    - 일정: 매일 오전 2시 실행 (cron 표현식 사용)
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

19. 고가용성 스테이트풀 애플리케이션을 위한 스테이트풀셋(StatefulSet) 설계에 대해 설명하고, 다음 요구사항을 충족하는 MySQL 복제 클러스터를 위한 스테이트풀셋 YAML을 작성하세요:
    - 1개의 마스터와 2개의 슬레이브로 구성
    - 안정적인 네트워크 식별자 제공
    - 각 인스턴스에 영구 스토리지 제공
    - 순차적인 배포 및 스케일링
    - 마스터 노드 장애 시 자동 복구 메커니즘

    <details>

    <summary>정답 보기</summary>
    
    **정답:**
    
    **고가용성 스테이트풀 애플리케이션 설계 원칙**
    
    스테이트풀 애플리케이션의 고가용성 설계에는 다음과 같은 원칙이 적용됩니다:
    
    1. **안정적인 네트워크 식별자**: 각 인스턴스가 재시작 후에도 동일한 네트워크 식별자를 유지
    2. **영구 스토리지**: 인스턴스가 재스케줄링되더라도 동일한 데이터에 접근 가능
    3. **순차적인 배포 및 스케일링**: 데이터 일관성을 위해 인스턴스를 순서대로 생성 및 삭제
    4. **자동 복구 메커니즘**: 장애 발생 시 자동으로 복구하는 메커니즘
    5. **백업 및 복원**: 정기적인 백업 및 필요 시 복원 절차
    
    **MySQL 복제 클러스터를 위한 스테이트풀셋 YAML**
    
    ```yaml
    # 헤드리스 서비스 정의
    apiVersion: v1
    kind: Service
    metadata:
      name: mysql
      labels:
        app: mysql
    spec:
      ports:
      - port: 3306
        name: mysql
      clusterIP: None
      selector:
        app: mysql
    ---
    # 구성을 위한 ConfigMap
    apiVersion: v1
    kind: ConfigMap
    metadata:
      name: mysql-config
    data:
      master.cnf: |
        [mysqld]
        log-bin=mysql-bin
        binlog-format=ROW
        server-id=1
      slave.cnf: |
        [mysqld]
        server-id=100
        log_bin=mysql-bin
        relay_log=mysql-relay-bin
        read_only=1
      init.sql: |
        CREATE DATABASE IF NOT EXISTS mydb;
        GRANT REPLICATION SLAVE ON *.* TO 'repl'@'%' IDENTIFIED BY 'replpass';
        FLUSH PRIVILEGES;
    ---
    # MySQL 스테이트풀셋
    apiVersion: apps/v1
    kind: StatefulSet
    metadata:
      name: mysql
    spec:
      selector:
        matchLabels:
          app: mysql
      serviceName: mysql
      replicas: 3
      updateStrategy:
        type: RollingUpdate
      podManagementPolicy: OrderedReady
      template:
        metadata:
          labels:
            app: mysql
        spec:
          initContainers:
          - name: init-mysql
            image: mysql:8.0
            command:
            - bash
            - "-c"
            - |
              set -ex
              # 파드 인덱스에 따라 마스터 또는 슬레이브 구성
              [[ `hostname` =~ -([0-9]+)$ ]] || exit 1
              ordinal=${BASH_REMATCH[1]}
              if [[ $ordinal -eq 0 ]]; then
                # 마스터 구성
                cp /mnt/config-map/master.cnf /etc/mysql/conf.d/
                # 초기화 SQL 스크립트 복사
                cp /mnt/config-map/init.sql /docker-entrypoint-initdb.d/
              else
                # 슬레이브 구성
                cp /mnt/config-map/slave.cnf /etc/mysql/conf.d/
              fi
            volumeMounts:
            - name: conf
              mountPath: /etc/mysql/conf.d
            - name: config-map
              mountPath: /mnt/config-map
            - name: initdb
              mountPath: /docker-entrypoint-initdb.d
          - name: clone-mysql
            image: mysql:8.0
            command:
            - bash
            - "-c"
            - |
              set -ex
              # 슬레이브만 복제 설정
              [[ `hostname` =~ -([0-9]+)$ ]] || exit 1
              ordinal=${BASH_REMATCH[1]}
              if [[ $ordinal -eq 0 ]]; then
                # 마스터는 아무것도 하지 않음
                exit 0
              fi
              
              # 마스터가 준비될 때까지 대기
              until mysql -h mysql-0.mysql -u root -p${MYSQL_ROOT_PASSWORD} -e "SELECT 1"; do
                echo "Waiting for mysql-0.mysql to be ready..."
                sleep 2
              done
              
              # 마스터 상태 확인
              master_status=$(mysql -h mysql-0.mysql -u root -p${MYSQL_ROOT_PASSWORD} -e "SHOW MASTER STATUS\G")
              file=$(echo "$master_status" | grep File | awk '{print $2}')
              position=$(echo "$master_status" | grep Position | awk '{print $2}')
              
              # 슬레이브 설정
              mysql -u root -p${MYSQL_ROOT_PASSWORD} -e "CHANGE MASTER TO MASTER_HOST='mysql-0.mysql', MASTER_USER='repl', MASTER_PASSWORD='replpass', MASTER_LOG_FILE='$file', MASTER_LOG_POS=$position; START SLAVE;"
            env:
            - name: MYSQL_ROOT_PASSWORD
              valueFrom:
                secretKeyRef:
                  name: mysql-secret
                  key: password
          containers:
          - name: mysql
            image: mysql:8.0
            env:
            - name: MYSQL_ROOT_PASSWORD
              valueFrom:
                secretKeyRef:
                  name: mysql-secret
                  key: password
            ports:
            - name: mysql
              containerPort: 3306
            volumeMounts:
            - name: data
              mountPath: /var/lib/mysql
            - name: conf
              mountPath: /etc/mysql/conf.d
            - name: initdb
              mountPath: /docker-entrypoint-initdb.d
            resources:
              requests:
                cpu: 500m
                memory: 1Gi
              limits:
                cpu: 1
                memory: 2Gi
            livenessProbe:
              exec:
                command: ["mysqladmin", "ping", "-u", "root", "-p${MYSQL_ROOT_PASSWORD}"]
              initialDelaySeconds: 30
              periodSeconds: 10
              timeoutSeconds: 5
            readinessProbe:
              exec:
                command: ["mysql", "-u", "root", "-p${MYSQL_ROOT_PASSWORD}", "-e", "SELECT 1"]
              initialDelaySeconds: 5
              periodSeconds: 2
              timeoutSeconds: 1
          volumes:
          - name: conf
            emptyDir: {}
          - name: config-map
            configMap:
              name: mysql-config
          - name: initdb
            emptyDir: {}
      volumeClaimTemplates:
      - metadata:
          name: data
        spec:
          accessModes: ["ReadWriteOnce"]
          storageClassName: "standard"
          resources:
            requests:
              storage: 10Gi
    ```
    
    **설명:**
    
    이 YAML 파일은 1개의 마스터와 2개의 슬레이브로 구성된 MySQL 복제 클러스터를 위한 스테이트풀셋을 정의합니다.
    
    1. **헤드리스 서비스**: `mysql` 서비스는 `clusterIP: None`으로 설정되어 있어, 각 파드에 대한 DNS 레코드가 생성됩니다. 이를 통해 `mysql-0.mysql`, `mysql-1.mysql`, `mysql-2.mysql`과 같은 안정적인 네트워크 식별자를 제공합니다.
    
    2. **ConfigMap**: MySQL 구성을 위한 ConfigMap을 정의합니다. 마스터 노드와 슬레이브 노드에 대한 별도의 구성과 초기화 SQL 스크립트를 포함합니다.
    
    3. **스테이트풀셋**: 3개의 복제본을 가진 MySQL 스테이트풀셋을 정의합니다.
       - `podManagementPolicy: OrderedReady`: 파드를 순서대로 생성 및 삭제합니다.
       - `updateStrategy: RollingUpdate`: 롤링 업데이트 전략을 사용합니다.
       - 초기화 컨테이너: 파드 인덱스에 따라 마스터 또는 슬레이브 구성을 적용하고, 슬레이브 노드는 마스터 노드에서 복제를 설정합니다.
       - 영구 스토리지: `volumeClaimTemplates`를 통해 각 파드에 대한 영구 볼륨 클레임을 생성합니다.
       - 리소스 요청 및 제한: 각 MySQL 인스턴스에 대한 리소스 요청 및 제한을 설정합니다.
       - 활성 프로브 및 준비성 프로브: MySQL 인스턴스의 상태를 확인합니다.
    
    4. **자동 복구 메커니즘**:
       - 파드가 실패하면 스테이트풀셋이 자동으로 새 파드를 생성합니다.
       - 새 파드는 동일한 네트워크 식별자와 영구 스토리지를 사용합니다.
       - 슬레이브 노드는 마스터 노드에서 복제를 설정하여 데이터 일관성을 유지합니다.
    
    이 설계는 고가용성 MySQL 클러스터를 제공하며, 마스터 노드 장애 시에도 슬레이브 노드 중 하나를 새로운 마스터로 승격시키는 메커니즘을 구현할 수 있습니다(이 예시에서는 자동 승격 메커니즘은 포함되어 있지 않으며, 일반적으로 MySQL 운영자 또는 추가 컨트롤러를 통해 구현됩니다).
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
    | **잡(Job)** | - 일회성 작업<br>- 완료 보장<br>- 병렬 실행 가능<br>- 실패 시 재시도 | - 배치 처리<br>- 데이터 마이그레이션<br>- 계산 작업<br>- 일회성 관리 작업 |
    | **크론잡(CronJob)** | - 일정에 따른 실행<br>- 주기적인 작업<br>- 동시성 정책<br>- 이력 제한 | - 정기 백업<br>- 데이터 동기화<br>- 보고서 생성<br>- 정리 작업 |
    
    **시나리오별 적합한 워크로드 리소스**
    
    1. **웹 애플리케이션 프론트엔드**
       - **적합한 리소스: 디플로이먼트(Deployment)**
       - **이유**: 웹 애플리케이션 프론트엔드는 일반적으로 상태가 없는(stateless) 애플리케이션입니다. 디플로이먼트는 롤링 업데이트를 통해 다운타임 없이 새 버전을 배포할 수 있고, 수평적 확장이 용이하며, 자동 복구 기능을 제공합니다. 또한 HorizontalPodAutoscaler와 함께 사용하여 트래픽에 따라 자동으로 스케일링할 수 있습니다.
    
    2. **분산 데이터베이스 클러스터**
       - **적합한 리소스: 스테이트풀셋(StatefulSet)**
       - **이유**: 분산 데이터베이스는 상태 유지가 필요하고, 각 인스턴스가 고유한 식별자와 영구 스토리지를 필요로 합니다. 스테이트풀셋은 안정적인 네트워크 식별자(`<파드 이름>-<순서 인덱스>`)와 영구 스토리지를 제공하며, 순차적인 배포 및 스케일링을 통해 데이터 일관성을 유지할 수 있습니다. 예를 들어, MySQL, PostgreSQL, MongoDB, Cassandra 등의 분산 데이터베이스 클러스터에 적합합니다.
    
    3. **로그 수집 에이전트**
       - **적합한 리소스: 데몬셋(DaemonSet)**
       - **이유**: 로그 수집 에이전트는 클러스터의 모든 노드에서 실행되어야 합니다. 데몬셋은 모든 노드(또는 특정 노드)에서 파드의 복사본을 실행하도록 보장하며, 새 노드가 클러스터에 추가되면 자동으로 로그 수집 에이전트를 배포합니다. Fluentd, Logstash, Filebeat 등의 로그 수집 에이전트를 배포하는 데 적합합니다.
    
    4. **일일 데이터 백업**
       - **적합한 리소스: 크론잡(CronJob)**
       - **이유**: 일일 데이터 백업은 정해진 일정에 따라 주기적으로 실행되어야 하는 작업입니다. 크론잡은 cron 표현식을 사용하여 실행 일정을 지정할 수 있으며, 매일 특정 시간에 백업 작업을 실행하도록 설정할 수 있습니다. 또한 `concurrencyPolicy`를 통해 이전 백업이 아직 실행 중일 때의 동작을 정의할 수 있고, 백업 이력을 제한할 수 있습니다.
    
    5. **일회성 데이터 마이그레이션**
       - **적합한 리소스: 잡(Job)**
       - **이유**: 데이터 마이그레이션은 일회성 작업으로, 성공적으로 완료되어야 합니다. 잡은 지정된 수의 파드가 성공적으로 종료될 때까지 실행을 계속하며, 실패 시 재시도 메커니즘을 제공합니다. 또한 `parallelism` 설정을 통해 여러 파드를 병렬로 실행하여 대규모 데이터 마이그레이션을 더 빠르게 처리할 수 있습니다.
    
    **결론**
    
    각 워크로드 리소스는 특정 사용 사례에 맞게 설계되었으며, 애플리케이션의 요구사항에 따라 적절한 리소스를 선택하는 것이 중요합니다. 디플로이먼트는 상태가 없는 애플리케이션에, 스테이트풀셋은 상태 유지가 필요한 애플리케이션에, 데몬셋은 모든 노드에서 실행해야 하는 서비스에, 잡은 일회성 작업에, 크론잡은 주기적인 작업에 적합합니다. 이러한 특성을 이해하고 적절한 워크로드 리소스를 선택하면 Kubernetes에서 애플리케이션을 효율적으로 관리할 수 있습니다.
    </details>

---

[학습 자료로 돌아가기](../../core/02-pods-and-workloads.md) | [다음 퀴즈: 서비스와 네트워킹](../core/03-services-networking-quiz.md)
