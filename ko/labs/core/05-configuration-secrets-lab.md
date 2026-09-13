# ConfigMap과 Secret 실습 가이드

> **난이도**: 초급
> **예상 소요 시간**: 35분
> **마지막 업데이트**: 2026년 9월 11일

## 학습 목표
- ConfigMap을 생성하고 Pod에서 활용합니다
- Secret을 생성하고 안전하게 주입합니다
- 환경변수와 볼륨 마운트 방식을 비교합니다

## 사전 요구 사항
- [ ] kubectl, Kubernetes 클러스터
- [ ] [구성](../../core/05-configuration-secrets.md) 학습 완료

Bash와 기존의 폐기 가능한 kind/minikube 클러스터를 사용합니다. 같은 셸에서 순서대로 실행하고 선행 명령이 실패하면 중단합니다. 네임스페이스를 만들기 전에 선택된 컨텍스트가 실습 클러스터인지 확인합니다. 아래 자격증명은 모두 공개된 더미 데이터이며 실제 데이터베이스에는 연결하지 않습니다.

```bash
CONFIG_LAB_DIR=$(mktemp -d /tmp/k8s-docs-config.XXXXXX)
: "${CONFIG_LAB_DIR:?mktemp failed}"
CONFIG_LAB_CONTEXT=$(kubectl config current-context)
: "${CONFIG_LAB_CONTEXT:?No context selected}"
printf 'Selected context: %s\n' "$CONFIG_LAB_CONTEXT"
unset CONFIG_LAB_NAMESPACE CONFIG_LAB_UID
CONFIG_LAB_CANDIDATE=$(basename "$CONFIG_LAB_DIR" | tr '[:upper:].' '[:lower:]-')
if CONFIG_LAB_UID=$(kubectl --context "$CONFIG_LAB_CONTEXT" create namespace "$CONFIG_LAB_CANDIDATE" -o jsonpath='{.metadata.uid}'); then
  CONFIG_LAB_NAMESPACE=$CONFIG_LAB_CANDIDATE
fi
: "${CONFIG_LAB_NAMESPACE:?Namespace creation failed}"
: "${CONFIG_LAB_UID:?Namespace UID missing}"
config_kubectl() {
  kubectl --context "${CONFIG_LAB_CONTEXT:?}" --namespace "${CONFIG_LAB_NAMESPACE:?}" "$@"
}
```

---

## 실습 1: ConfigMap 생성과 활용

### 단계

**Step 1.1: ConfigMap 생성**
```bash
# 리터럴 값으로 생성
config_kubectl create configmap app-config \
  --from-literal=APP_ENV=production \
  --from-literal=LOG_LEVEL=info \
  --from-literal=MAX_CONNECTIONS=100

config_kubectl get configmap app-config -o yaml
```

**Step 1.2: 파일에서 ConfigMap 생성**
```bash
cat > "${CONFIG_LAB_DIR:?}/app.properties" << 'EOF'
database.host=mysql
database.port=3306
database.name=myapp
EOF

config_kubectl create configmap app-properties --from-file="${CONFIG_LAB_DIR:?}/app.properties"
config_kubectl describe configmap app-properties
```

이 속성들은 구성 형식을 보여 주는 문자열입니다. MySQL Service, 데이터베이스, 인증 흐름을 생성하거나 검증하지 않습니다.

**Step 1.3: 환경변수로 ConfigMap 주입**
```bash
cat > "${CONFIG_LAB_DIR:?}/configmap-env-pod.yaml" << 'EOF'
apiVersion: v1
kind: Pod
metadata:
  name: config-env-demo
spec:
  automountServiceAccountToken: false
  containers:
  - name: app
    image: busybox:1.37.0
    command: ["sh", "-ec", "echo APP_ENV=$APP_ENV LOG_LEVEL=$LOG_LEVEL; exec sleep 3600"]
    envFrom:
    - configMapRef:
        name: app-config
EOF

config_kubectl apply -f "${CONFIG_LAB_DIR:?}/configmap-env-pod.yaml"
config_kubectl wait --for=condition=ready pod/config-env-demo --timeout=120s
config_kubectl logs config-env-demo
```

예상 결과:
```
APP_ENV=production LOG_LEVEL=info
```

**Step 1.4: 볼륨으로 ConfigMap 마운트**
```bash
cat > "${CONFIG_LAB_DIR:?}/configmap-vol-pod.yaml" << 'EOF'
apiVersion: v1
kind: Pod
metadata:
  name: config-vol-demo
spec:
  automountServiceAccountToken: false
  containers:
  - name: app
    image: busybox:1.37.0
    command: ["sh", "-ec", "cat /config/app.properties; exec sleep 3600"]
    volumeMounts:
    - name: config-volume
      mountPath: /config
      readOnly: true
  volumes:
  - name: config-volume
    configMap:
      name: app-properties
EOF

config_kubectl apply -f "${CONFIG_LAB_DIR:?}/configmap-vol-pod.yaml"
config_kubectl wait --for=condition=ready pod/config-vol-demo --timeout=120s
config_kubectl logs config-vol-demo
```

<details>
<summary>힌트가 필요하신가요?</summary>

- `envFrom`은 여기서 사용하는 ConfigMap 키를 환경변수로 주입합니다.
- 마운트된 키는 각각 파일이 됩니다. 갱신은 kubelet의 동기화/캐시를 통해 점진적으로 반영되며 즉시 반영을 보장하지 않습니다.
- `subPath` 마운트에는 갱신이 반영되지 않습니다. 환경변수는 컨테이너 시작 시 정해지므로 새 값을 읽으려면 Pod를 교체합니다. 파일을 한 번만 읽는 프로세스도 명시적인 재읽기나 재시작이 필요합니다.
</details>

---

## 실습 2: Secret 관리

### 단계

**Step 2.1: Secret 생성**
```bash
# Public dummy values only. Do not substitute real credentials in shell history.
(
  umask 077
  printf '%s' 'lab-user' > "${CONFIG_LAB_DIR:?}/DB_USER"
  printf '%s' 'not-a-real-password' > "${CONFIG_LAB_DIR:?}/DB_PASSWORD"
)
config_kubectl create secret generic db-secret \
  --from-file=DB_USER="${CONFIG_LAB_DIR:?}/DB_USER" \
  --from-file=DB_PASSWORD="${CONFIG_LAB_DIR:?}/DB_PASSWORD"
# Show key names only, never their values or encoded contents.
config_kubectl get secret db-secret \
  -o go-template='{{range $key, $value := .data}}{{printf "%s\n" $key}}{{end}}'
```

키 이름만 출력되어야 합니다. 파일 입력은 실제 자격증명을 명령 인자에 넣는 일을 피하지만, 이 비공개 로컬 파일에도 평문이 있으므로 실습 후 삭제합니다. Secret API 응답의 base64는 인코딩이며 암호화가 아닙니다. 저장 시 암호화, 최소 권한 RBAC, 회전은 별도 설정이 필요합니다. 이 네임스페이스에서 Pod를 생성할 수 있는 권한도 Secret 노출로 이어질 수 있습니다.

**Step 2.2: Secret을 Pod에 주입**
비루트 컨테이너가 사용자명·비밀번호·길이를 출력하지 않고 값의 존재만 확인합니다. Secret 볼륨은 읽기 전용입니다. `0440`은 YAML의 8진수 모드(JSON에서는 10진수 `288`)이며, `fsGroup`으로 컨테이너 그룹에 읽기 권한을 줍니다. 두 주입 방식은 비교를 위해 함께 보여 주며 앱에 중복 사본이 필요하다는 뜻은 아닙니다.

```bash
cat > "${CONFIG_LAB_DIR:?}/secret-pod.yaml" << 'EOF'
apiVersion: v1
kind: Pod
metadata:
  name: secret-demo
spec:
  automountServiceAccountToken: false
  securityContext:
    runAsNonRoot: true
    runAsUser: 1000
    runAsGroup: 2000
    fsGroup: 2000
    seccompProfile:
      type: RuntimeDefault
  containers:
  - name: app
    image: busybox:1.37.0
    command:
    - sh
    - -ec
    - |
      test -n "$DB_USER"
      test -n "$DB_PASSWORD"
      test -s /run/credentials/DB_USER
      test -s /run/credentials/DB_PASSWORD
      printf 'Dummy credentials available through environment and files\n'
      exec sleep 3600
    securityContext:
      allowPrivilegeEscalation: false
      capabilities:
        drop: [ALL]
    env:
    - name: DB_USER
      valueFrom:
        secretKeyRef:
          name: db-secret
          key: DB_USER
    - name: DB_PASSWORD
      valueFrom:
        secretKeyRef:
          name: db-secret
          key: DB_PASSWORD
    volumeMounts:
    - name: credentials
      mountPath: /run/credentials
      readOnly: true
  volumes:
  - name: credentials
    secret:
      secretName: db-secret
      defaultMode: 0440
EOF
config_kubectl apply -f "${CONFIG_LAB_DIR:?}/secret-pod.yaml"
config_kubectl wait --for=condition=Ready pod/secret-demo --timeout=120s
config_kubectl logs secret-demo
```

예상 결과:
```
Dummy credentials available through environment and files
```

**Step 2.3: 오프라인 더미 문자열로 base64 확인**
```bash
printf '%s' 'lab-only' | base64 | base64 -d
printf '\n'
```

<details>
<summary>힌트가 필요하신가요?</summary>

- 이 오프라인 예제는 공개된 문자열 `lab-only`만 출력합니다. 실제 Secret을 공유 터미널이나 로그로 디코딩하지 않습니다.
- Secret을 갱신해도 기존 컨테이너의 환경변수는 바뀌지 않습니다. 일반 Secret 볼륨은 점진적으로 갱신되지만 앱이 파일을 다시 읽어야 하며, `subPath`는 갱신되지 않습니다.
- 외부 Secret 저장소/컨트롤러도 별도의 신원·권한·회전 설정이 필요합니다. 도구 설치만으로 이러한 보장이 성립하지 않습니다.
</details>

---

## 실습 3: 환경변수 vs 볼륨 마운트 비교

### 단계

**Step 3.1: ConfigMap을 갱신하고 실행 중인 Pod 비교**
```bash
config_kubectl patch configmap app-config --type=merge \
  -p '{"data":{"LOG_LEVEL":"debug"}}'
config_kubectl patch configmap app-properties --type=merge \
  -p '{"data":{"app.properties":"database.host=mysql\ndatabase.port=3306\ndatabase.name=myapp_v2\n"}}'

# The existing container still has LOG_LEVEL=info.
config_kubectl exec config-env-demo -- sh -c 'printf "LOG_LEVEL=%s\n" "$LOG_LEVEL"'

# Reopen the file up to 60 times, with five seconds between attempts.
CONFIG_LAB_PROJECTED=false
for ((attempt=1; attempt<=60; attempt++)); do
  if config_kubectl exec config-vol-demo -- sh -c 'grep -qx "database.name=myapp_v2" /config/app.properties'; then
    CONFIG_LAB_PROJECTED=true
    break
  fi
  sleep 5
done
if [ "$CONFIG_LAB_PROJECTED" = true ]; then
  config_kubectl exec config-vol-demo -- cat /config/app.properties
else
  printf 'Update not observed: inspect Pod events, kubelet connectivity and sync/cache settings\n' >&2
fi

# Replace this bare Pod to read the current environment values.
config_kubectl delete pod config-env-demo --wait=true --timeout=120s &&
  config_kubectl apply -f "${CONFIG_LAB_DIR:?}/configmap-env-pod.yaml" &&
  config_kubectl wait --for=condition=Ready pod/config-env-demo --timeout=120s &&
  config_kubectl logs config-env-demo
```

원래 `config-vol-demo` 로그는 시작 시 한 번 읽은 내용입니다. 마운트된 파일을 다시 확인하면 볼륨 갱신을 관찰할 수 있지만, 앱의 자동 재읽기를 증명하는 것은 아닙니다. 재시도 횟수와 간격은 실습을 위한 관찰 조건입니다. 명령 실행 시간도 더해지며 Kubernetes가 이 시간 안의 반영을 보장하지 않습니다. 교체한 Pod가 정상 시작하면 로그에 `LOG_LEVEL=debug`가 표시되어야 합니다.

---

## 정리
```bash
if [[ -n ${CONFIG_LAB_NAMESPACE:-} && -n ${CONFIG_LAB_UID:-} ]]; then
  current_uid=$(kubectl --context "${CONFIG_LAB_CONTEXT:?}" get namespace "$CONFIG_LAB_NAMESPACE" -o jsonpath='{.metadata.uid}') || current_uid=""
  if [ "$current_uid" = "$CONFIG_LAB_UID" ]; then
    kubectl --context "$CONFIG_LAB_CONTEXT" delete namespace "$CONFIG_LAB_NAMESPACE" --timeout=120s
  fi
fi
if [[ -n ${CONFIG_LAB_DIR:-} ]]; then
  rm -f -- "$CONFIG_LAB_DIR/app.properties" "$CONFIG_LAB_DIR/configmap-env-pod.yaml" \
    "$CONFIG_LAB_DIR/configmap-vol-pod.yaml" "$CONFIG_LAB_DIR/secret-pod.yaml" \
    "$CONFIG_LAB_DIR/DB_USER" "$CONFIG_LAB_DIR/DB_PASSWORD"
  rmdir -- "$CONFIG_LAB_DIR"
fi
unset -f config_kubectl
```

## 참고 자료와 검증 범위

- [ConfigMap projection and updates](https://kubernetes.io/docs/concepts/configuration/configmap/)
- [Secret security and updates](https://kubernetes.io/docs/concepts/configuration/secret/)
- [Secret file permissions and environment variables](https://kubernetes.io/docs/tasks/inject-data-application/distribute-credentials-secure/)

셸 구문, 매니페스트, 로컬 fixture를 검증했습니다. 감사 중 Kubernetes Secret, Pod, 네임스페이스, 외부 Secret 저장소를 생성하거나 접근하지 않았습니다.

## 다음 단계
- [구성 퀴즈](../../quizzes/core/05-configuration-secrets-quiz.md)
- [EKS 클러스터 생성 실습](../eks/01-eks-cluster-creation-lab.md)
