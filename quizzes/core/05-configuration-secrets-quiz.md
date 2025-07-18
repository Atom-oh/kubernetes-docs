# 구성 퀴즈

이 퀴즈는 Kubernetes의 구성 관련 개념인 ConfigMap, Secret, 환경 변수, 리소스 요청 및 제한 등에 대한 이해도를 테스트합니다.

## 객관식 문제

1. Kubernetes에서 민감한 정보를 저장하기 위해 사용하는 리소스는 무엇인가요?
   - A) ConfigMap
   - B) Secret
   - C) Volume
   - D) Deployment
   
<details>

<summary>정답 보기</summary>

**정답: B) Secret**

**설명:**
Secret은 비밀번호, OAuth 토큰, SSH 키와 같은 민감한 정보를 저장하기 위한 Kubernetes 리소스입니다. Secret은 기본적으로 base64로 인코딩되어 저장되며, 포드에 파일이나 환경 변수로 마운트할 수 있습니다. ConfigMap은 민감하지 않은 구성 데이터를 저장하는 데 사용됩니다.
</details>

2. Kubernetes에서 ConfigMap의 주요 목적은 무엇인가요?
   - A) 컨테이너 이미지 저장
   - B) 애플리케이션 구성 데이터 저장
   - C) 네트워크 정책 정의
   - D) 포드 스케줄링 제어
   
<details>

<summary>정답 보기</summary>

**정답: B) 애플리케이션 구성 데이터 저장**

**설명:**
ConfigMap은 키-값 쌍 형태로 구성 데이터를 저장하는 Kubernetes 리소스입니다. 이를 통해 애플리케이션 코드와 구성을 분리할 수 있으며, 환경별로 다른 구성을 사용할 수 있습니다. ConfigMap은 환경 변수, 명령줄 인수 또는 구성 파일로 컨테이너에 마운트할 수 있습니다.
</details>

3. Kubernetes에서 포드의 리소스 요청(requests)과 제한(limits)의 차이점은 무엇인가요?
   - A) 요청은 포드가 사용할 수 있는 최소 리소스, 제한은 최대 리소스
   - B) 요청은 포드가 사용할 수 있는 최대 리소스, 제한은 최소 리소스
   - C) 요청은 스케줄링에만 사용되고, 제한은 런타임에만 적용됨
   - D) 요청은 CPU에만 적용되고, 제한은 메모리에만 적용됨
   
<details>

<summary>정답 보기</summary>

**정답: A) 요청은 포드가 사용할 수 있는 최소 리소스, 제한은 최대 리소스**

**설명:**
리소스 요청(requests)은 포드가 보장받을 수 있는 최소 리소스 양을 지정하며, 스케줄러가 포드를 노드에 배치할 때 이 값을 사용합니다. 리소스 제한(limits)은 포드가 사용할 수 있는 최대 리소스 양을 지정하며, 이 값을 초과하면 포드가 제한되거나(CPU의 경우) 종료될 수 있습니다(메모리의 경우).
</details>

4. Kubernetes에서 Secret 데이터를 포드에 제공하는 방법이 아닌 것은 무엇인가요?
   - A) 환경 변수로 제공
   - B) 볼륨으로 마운트
   - C) 이미지 레지스트리 자격 증명으로 사용
   - D) 네트워크 인터페이스로 제공
   
<details>

<summary>정답 보기</summary>

**정답: D) 네트워크 인터페이스로 제공**

**설명:**
Kubernetes에서 Secret 데이터를 포드에 제공하는 방법은 환경 변수로 제공, 볼륨으로 마운트, 이미지 레지스트리 자격 증명으로 사용하는 방법이 있습니다. 네트워크 인터페이스를 통해 Secret을 제공하는 방법은 Kubernetes에서 지원하지 않습니다.
</details>

5. Kubernetes에서 ConfigMap을 생성하는 방법이 아닌 것은 무엇인가요?
   - A) 리터럴 값에서 생성
   - B) 파일에서 생성
   - C) 디렉토리에서 생성
   - D) 네트워크 요청에서 생성
   
<details>

<summary>정답 보기</summary>

**정답: D) 네트워크 요청에서 생성**

**설명:**
Kubernetes에서 ConfigMap을 생성하는 방법은 리터럴 값에서 생성(`--from-literal`), 파일에서 생성(`--from-file`), 디렉토리에서 생성(`--from-file=<디렉토리>`)이 있습니다. 네트워크 요청에서 직접 ConfigMap을 생성하는 방법은 Kubernetes에서 기본적으로 제공하지 않습니다.
</details>

6. Kubernetes에서 포드의 서비스 계정을 지정하는 필드는 무엇인가요?
   - A) spec.serviceAccount
   - B) spec.serviceAccountName
   - C) metadata.serviceAccount
   - D) spec.account
   
<details>

<summary>정답 보기</summary>

**정답: B) spec.serviceAccountName**

**설명:**
Kubernetes에서 포드의 서비스 계정은 `spec.serviceAccountName` 필드를 통해 지정합니다. 이 필드를 통해 포드가 사용할 서비스 계정을 지정할 수 있으며, 지정하지 않으면 네임스페이스의 기본 서비스 계정이 사용됩니다.
</details>

7. Kubernetes에서 Secret 데이터의 기본 인코딩 방식은 무엇인가요?
   - A) AES-256
   - B) Base64
   - C) SHA-256
   - D) 인코딩하지 않음
   
<details>

<summary>정답 보기</summary>

**정답: B) Base64**

**설명:**
Kubernetes에서 Secret 데이터는 기본적으로 Base64로 인코딩되어 저장됩니다. 이는 단순한 인코딩일 뿐 암호화가 아니므로, 추가적인 보안 조치가 필요합니다. Kubernetes 1.13부터는 etcd에 저장된 Secret 데이터를 암호화하는 기능을 제공합니다.
</details>

8. Kubernetes에서 환경 변수를 설정하는 방법 중 가장 권장되지 않는 것은 무엇인가요?
   - A) ConfigMap에서 가져오기
   - B) Secret에서 가져오기
   - C) 포드 스펙에 직접 하드코딩
   - D) Downward API를 통해 가져오기
   
<details>

<summary>정답 보기</summary>

**정답: C) 포드 스펙에 직접 하드코딩**

**설명:**
환경 변수를 포드 스펙에 직접 하드코딩하는 것은 구성과 코드를 분리하는 원칙에 위배되므로 권장되지 않습니다. ConfigMap이나 Secret을 사용하여 환경 변수를 관리하면 애플리케이션 코드를 변경하지 않고도 구성을 변경할 수 있으며, Downward API를 사용하면 포드의 메타데이터나 리소스 정보를 환경 변수로 제공할 수 있습니다.
</details>

9. Kubernetes에서 포드의 QoS(Quality of Service) 클래스 중, 모든 컨테이너에 리소스 요청과 제한이 설정되어 있고, 요청과 제한이 동일한 경우의 QoS 클래스는 무엇인가요?
   - A) Guaranteed
   - B) Burstable
   - C) BestEffort
   - D) Critical
   
<details>

<summary>정답 보기</summary>

**정답: A) Guaranteed**

**설명:**
Guaranteed QoS 클래스는 포드의 모든 컨테이너에 리소스 요청과 제한이 설정되어 있고, 요청과 제한이 동일한 경우에 할당됩니다. 이 클래스의 포드는 리소스 부족 시 가장 마지막에 종료됩니다. Burstable은 일부 컨테이너에만 요청과 제한이 설정되어 있거나, 요청과 제한이 다른 경우에 할당되며, BestEffort는 요청과 제한이 모두 설정되지 않은 경우에 할당됩니다.
</details>

10. Kubernetes에서 ConfigMap이나 Secret의 변경 사항이 포드에 자동으로 반영되는 경우는 언제인가요?
    - A) 항상 자동으로 반영됨
    - B) 볼륨으로 마운트된 경우에만 자동으로 반영됨
    - C) 환경 변수로 사용된 경우에만 자동으로 반영됨
    - D) 자동으로 반영되지 않고 포드를 재시작해야 함
    
<details>

<summary>정답 보기</summary>

**정답: B) 볼륨으로 마운트된 경우에만 자동으로 반영됨**

**설명:**
ConfigMap이나 Secret이 볼륨으로 마운트된 경우, Kubernetes는 주기적으로(기본값은 약 1분) 마운트된 파일을 업데이트합니다. 그러나 환경 변수로 사용된 경우에는 포드가 생성될 때 한 번만 설정되므로, 변경 사항을 반영하려면 포드를 재시작해야 합니다. 이는 환경 변수가 프로세스의 시작 시점에 설정되기 때문입니다.
</details>

## 실습 문제

1. ConfigMap과 Secret을 생성하고, 이를 포드에 환경 변수와 볼륨으로 마운트하는 방법을 설명하세요.

<details>

<summary>정답 보기</summary>

**정답:**

1. ConfigMap 생성:
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
name: app-config
data:
app.properties: |
app.name=MyApp
app.version=1.0.0
database.properties: |
db.host=mysql
db.port=3306
db.name=mydb
```

2. Secret 생성:
```yaml
apiVersion: v1
kind: Secret
metadata:
name: app-secrets
type: Opaque
data:
db.user: YWRtaW4=  # admin (base64 인코딩)
db.password: cGFzc3dvcmQxMjM=  # password123 (base64 인코딩)
```

3. 환경 변수와 볼륨으로 마운트하는 포드 생성:
```yaml
apiVersion: v1
kind: Pod
metadata:
name: app-pod
spec:
containers:
- name: app
image: myapp:1.0
env:
# ConfigMap에서 환경 변수 가져오기
- name: APP_NAME
valueFrom:
configMapKeyRef:
name: app-config
key: app.properties
subPath: app.name
# Secret에서 환경 변수 가져오기
- name: DB_USER
valueFrom:
secretKeyRef:
name: app-secrets
key: db.user
- name: DB_PASSWORD
valueFrom:
secretKeyRef:
name: app-secrets
key: db.password
volumeMounts:
# ConfigMap을 볼륨으로 마운트
- name: config-volume
mountPath: /etc/config
# Secret을 볼륨으로 마운트
- name: secret-volume
mountPath: /etc/secrets
readOnly: true
volumes:
# ConfigMap 볼륨 정의
- name: config-volume
configMap:
name: app-config
# Secret 볼륨 정의
- name: secret-volume
secret:
secretName: app-secrets
```

4. 리소스 적용:
```bash
kubectl apply -f configmap.yaml
kubectl apply -f secret.yaml
kubectl apply -f pod.yaml
```

5. 환경 변수 확인:
```bash
kubectl exec app-pod -- env | grep -E 'APP_NAME|DB_'
```

6. 마운트된 볼륨 확인:
```bash
kubectl exec app-pod -- ls -la /etc/config
kubectl exec app-pod -- ls -la /etc/secrets
```

7. 파일 내용 확인:
```bash
kubectl exec app-pod -- cat /etc/config/app.properties
kubectl exec app-pod -- cat /etc/secrets/db.user
```
</details>

2. 포드에 리소스 요청과 제한을 설정하고, QoS 클래스를 확인하는 방법을 설명하세요.

<details>

<summary>정답 보기</summary>

**정답:**

1. 다양한 QoS 클래스를 가진 포드 생성:

**Guaranteed QoS 포드**:
```yaml
apiVersion: v1
kind: Pod
metadata:
name: guaranteed-pod
spec:
containers:
- name: nginx
image: nginx
resources:
requests:
memory: "100Mi"
cpu: "100m"
limits:
memory: "100Mi"
cpu: "100m"
```

**Burstable QoS 포드**:
```yaml
apiVersion: v1
kind: Pod
metadata:
name: burstable-pod
spec:
containers:
- name: nginx
image: nginx
resources:
requests:
memory: "100Mi"
cpu: "100m"
limits:
memory: "200Mi"
cpu: "200m"
```

**BestEffort QoS 포드**:
```yaml
apiVersion: v1
kind: Pod
metadata:
name: besteffort-pod
spec:
containers:
- name: nginx
image: nginx
# 리소스 요청과 제한이 없음
```

2. 포드 생성:
```bash
kubectl apply -f guaranteed-pod.yaml
kubectl apply -f burstable-pod.yaml
kubectl apply -f besteffort-pod.yaml
```

3. QoS 클래스 확인:
```bash
kubectl get pods guaranteed-pod -o jsonpath='{.status.qosClass}'
# 출력: Guaranteed

kubectl get pods burstable-pod -o jsonpath='{.status.qosClass}'
# 출력: Burstable

kubectl get pods besteffort-pod -o jsonpath='{.status.qosClass}'
# 출력: BestEffort
```

4. 포드 상세 정보 확인:
```bash
kubectl describe pod guaranteed-pod | grep QoS
kubectl describe pod burstable-pod | grep QoS
kubectl describe pod besteffort-pod | grep QoS
```

5. 리소스 사용량 모니터링:
```bash
kubectl top pod guaranteed-pod
kubectl top pod burstable-pod
kubectl top pod besteffort-pod
```

**QoS 클래스 결정 규칙**:
- **Guaranteed**: 모든 컨테이너에 리소스 요청과 제한이 설정되어 있고, 요청과 제한이 동일한 경우
- **Burstable**: 적어도 하나의 컨테이너에 리소스 요청이 설정되어 있지만, Guaranteed 조건을 충족하지 않는 경우
- **BestEffort**: 모든 컨테이너에 리소스 요청과 제한이 설정되지 않은 경우
</details>

3. Downward API를 사용하여 포드의 메타데이터와 리소스 정보를 컨테이너에 제공하는 방법을 설명하세요.

<details>

<summary>정답 보기</summary>

**정답:**

1. Downward API를 사용하는 포드 생성:
```yaml
apiVersion: v1
kind: Pod
metadata:
name: downward-api-pod
labels:
app: myapp
environment: production
spec:
containers:
- name: main
image: busybox
command: ["sh", "-c", "while true; do echo Downward API Demo; sleep 10; done"]
resources:
requests:
memory: "64Mi"
cpu: "250m"
limits:
memory: "128Mi"
cpu: "500m"
env:
# 포드 메타데이터를 환경 변수로 제공
- name: POD_NAME
valueFrom:
fieldRef:
fieldPath: metadata.name
- name: POD_NAMESPACE
valueFrom:
fieldRef:
fieldPath: metadata.namespace
- name: POD_IP
valueFrom:
fieldRef:
fieldPath: status.podIP
- name: NODE_NAME
valueFrom:
fieldRef:
fieldPath: spec.nodeName
- name: POD_SERVICE_ACCOUNT
valueFrom:
fieldRef:
fieldPath: spec.serviceAccountName
- name: POD_LABEL_APP
valueFrom:
fieldRef:
fieldPath: metadata.labels['app']
# 컨테이너 리소스 정보를 환경 변수로 제공
- name: CPU_REQUEST
valueFrom:
resourceFieldRef:
containerName: main
resource: requests.cpu
- name: CPU_LIMIT
valueFrom:
resourceFieldRef:
containerName: main
resource: limits.cpu
- name: MEM_REQUEST
valueFrom:
resourceFieldRef:
containerName: main
resource: requests.memory
divisor: "1Mi"
- name: MEM_LIMIT
valueFrom:
resourceFieldRef:
containerName: main
resource: limits.memory
divisor: "1Mi"
volumeMounts:
- name: podinfo
mountPath: /etc/podinfo
volumes:
# Downward API를 볼륨으로 제공
- name: podinfo
downwardAPI:
items:
- path: "labels"
fieldRef:
fieldPath: metadata.labels
- path: "annotations"
fieldRef:
fieldPath: metadata.annotations
- path: "cpu-request"
resourceFieldRef:
containerName: main
resource: requests.cpu
- path: "cpu-limit"
resourceFieldRef:
containerName: main
resource: limits.cpu
```

2. 포드 생성:
```bash
kubectl apply -f downward-api-pod.yaml
```

3. 환경 변수 확인:
```bash
kubectl exec downward-api-pod -- env | sort
```

4. 볼륨 파일 확인:
```bash
kubectl exec downward-api-pod -- ls -la /etc/podinfo
kubectl exec downward-api-pod -- cat /etc/podinfo/labels
kubectl exec downward-api-pod -- cat /etc/podinfo/cpu-request
```

**Downward API 사용 가능한 필드**:

**환경 변수로 사용 가능한 필드**:
- `metadata.name` - 포드 이름
- `metadata.namespace` - 포드 네임스페이스
- `metadata.uid` - 포드 UID
- `metadata.labels['<KEY>']` - 포드 레이블 값
- `metadata.annotations['<KEY>']` - 포드 어노테이션 값
- `status.podIP` - 포드 IP 주소
- `spec.nodeName` - 포드가 실행 중인 노드 이름
- `spec.serviceAccountName` - 포드의 서비스 계정 이름
- `status.hostIP` - 포드가 실행 중인 노드 IP 주소

**리소스 필드**:
- `requests.cpu` - CPU 요청
- `limits.cpu` - CPU 제한
- `requests.memory` - 메모리 요청
- `limits.memory` - 메모리 제한
</details>
