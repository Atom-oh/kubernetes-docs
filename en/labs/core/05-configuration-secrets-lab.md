# ConfigMap and Secret Lab Guide

> **Difficulty**: Beginner
> **Estimated Time**: 35 minutes
> **Last Updated**: September 11, 2026

## Learning Objectives
- Create ConfigMaps and use them in Pods
- Create Secrets and inject them securely
- Compare environment variable and volume mount methods

## Prerequisites
- [ ] kubectl, Kubernetes cluster
- [ ] Completed [Configuration](../../core/05-configuration-secrets.md) learning

Use Bash and an existing disposable kind/minikube cluster. Run the steps in the same shell and stop if a prerequisite command fails. Confirm the selected context is the intended lab cluster before creating the namespace. All credentials below are public dummy data; this lab does not connect to a database.

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

## Exercise 1: ConfigMap Creation and Usage

### Steps

**Step 1.1: Create ConfigMap**
```bash
# Create from literal values
config_kubectl create configmap app-config \
  --from-literal=APP_ENV=production \
  --from-literal=LOG_LEVEL=info \
  --from-literal=MAX_CONNECTIONS=100

config_kubectl get configmap app-config -o yaml
```

**Step 1.2: Create ConfigMap from file**
```bash
cat > "${CONFIG_LAB_DIR:?}/app.properties" << 'EOF'
database.host=mysql
database.port=3306
database.name=myapp
EOF

config_kubectl create configmap app-properties --from-file="${CONFIG_LAB_DIR:?}/app.properties"
config_kubectl describe configmap app-properties
```

These properties are sample configuration text. No MySQL Service, database or authentication flow is created or validated.

**Step 1.3: Inject ConfigMap as environment variables**
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

Expected output:
```
APP_ENV=production LOG_LEVEL=info
```

**Step 1.4: Mount ConfigMap as volume**
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
<summary>Need a hint?</summary>

- `envFrom` imports the ConfigMap keys used here as environment variables.
- Each mounted key becomes a file. Updates propagate eventually through the kubelet sync/cache mechanism; they are not immediate.
- A `subPath` mount does not receive updates. Environment variables are fixed when a container starts; replace the Pod to load new values. A process that reads a file only once also needs an explicit reload/restart.
</details>

---

## Exercise 2: Secret Management

### Steps

**Step 2.1: Create Secret**
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

Only key names should appear. File input avoids embedding real credentials in command arguments; these private local files still contain plaintext and must be removed after the lab. Base64 in a Secret API response is an encoding, not encryption. At-rest encryption, least-privilege RBAC and rotation need separate configuration. Permission to create Pods in this namespace can also expose its Secrets.

**Step 2.2: Inject Secret into Pod**
The non-root container checks that values exist without printing usernames, passwords or lengths. The Secret volume is read-only; `0440` is an octal YAML mode (decimal `288` in JSON), with `fsGroup` granting this container group read access. Both injection methods are shown for comparison, not because an application needs duplicate copies.

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

Expected output:
```
Dummy credentials available through environment and files
```

**Step 2.3: Demonstrate base64 using offline dummy text**
```bash
printf '%s' 'lab-only' | base64 | base64 -d
printf '\n'
```

<details>
<summary>Need a hint?</summary>

- This offline example prints only the public string `lab-only`; never decode a live Secret into shared terminals or logs.
- Updating a Secret does not change environment variables in an existing container. Regular Secret volume projections update eventually, but applications must reread the files; `subPath` does not update.
- External secret stores/controllers require their own identity, authorization and rotation setup. Installing a tool does not itself establish those guarantees.
</details>

---

## Exercise 3: Environment Variables vs Volume Mount Comparison

### Steps

**Step 3.1: Update the ConfigMaps and compare the running Pods**
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

The original `config-vol-demo` log contains a startup-only read. Inspecting the mounted file again demonstrates projection, not automatic application reload. The retry count and delay are observation choices for this exercise; command duration adds to the elapsed time and Kubernetes does not guarantee delivery within this window. After the replacement Pod starts successfully, its log should show `LOG_LEVEL=debug`.

---

## Cleanup
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

## References and validation scope

- [ConfigMap projection and updates](https://kubernetes.io/docs/concepts/configuration/configmap/)
- [Secret security and updates](https://kubernetes.io/docs/concepts/configuration/secret/)
- [Secret file permissions and environment variables](https://kubernetes.io/docs/tasks/inject-data-application/distribute-credentials-secure/)

Validation covers shell syntax, manifests and local fixtures. No Kubernetes Secret, Pod, namespace or external secret store was created or accessed during this audit.

## Next Steps
- [Configuration Quiz](../../quizzes/core/05-configuration-secrets-quiz.md)
- [EKS Cluster Creation Lab](../eks/01-eks-cluster-creation-lab.md)
