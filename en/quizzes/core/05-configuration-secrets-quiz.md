# Configuration Quiz

This quiz tests your understanding of Kubernetes configuration concepts including ConfigMap, Secret, environment variables, resource requests and limits.

## Multiple Choice Questions

1. What resource is used to store sensitive information in Kubernetes?
   - A) ConfigMap
   - B) Secret
   - C) Volume
   - D) Deployment
   
<details>

<summary>Show Answer</summary>

**Answer: B) Secret**

**Explanation:**
Secret is a Kubernetes resource for storing sensitive information such as passwords, OAuth tokens, and SSH keys. Secrets are stored encoded in base64 by default and can be mounted to pods as files or environment variables. ConfigMap is used for storing non-sensitive configuration data.
</details>

2. What is the main purpose of ConfigMap in Kubernetes?
   - A) Storing container images
   - B) Storing application configuration data
   - C) Defining network policies
   - D) Controlling pod scheduling
   
<details>

<summary>Show Answer</summary>

**Answer: B) Storing application configuration data**

**Explanation:**
ConfigMap is a Kubernetes resource that stores configuration data in key-value pairs. This allows you to separate application code from configuration, enabling different configurations for different environments. ConfigMaps can be mounted to containers as environment variables, command-line arguments, or configuration files.
</details>

3. What is the difference between resource requests and limits in Kubernetes pods?
   - A) Requests guide scheduling/resource allocation; limits constrain runtime usage
   - B) Requests are the maximum resources a pod can use, limits are the minimum
   - C) Requests are only used for scheduling, limits are only applied at runtime
   - D) Requests only apply to CPU, limits only apply to memory
   
<details>

<summary>Show Answer</summary>

**Answer: A) Requests guide scheduling/resource allocation; limits constrain runtime usage**

**Explanation:**
Requests reserve scheduling capacity and affect runtime resource allocation; a process can use less than its request. CPU limits are enforced by throttling; memory limits are enforced reactively through OOM killing. Requests do not guarantee immunity from node pressure.
</details>

4. Which is NOT a method for providing Secret data to pods in Kubernetes?
   - A) As environment variables
   - B) As a mounted volume
   - C) As image registry credentials
   - D) As a network interface
   
<details>

<summary>Show Answer</summary>

**Answer: D) As a network interface**

**Explanation:**
Methods for providing Secret data to pods in Kubernetes include as environment variables, as a mounted volume, and as image registry credentials. Providing Secrets through a network interface is not supported in Kubernetes.
</details>

5. Which is NOT a supported input option of `kubectl create configmap`?
   - A) From literal values
   - B) From a file
   - C) From a directory
   - D) `--from-url`
   
<details>

<summary>Show Answer</summary>

**Answer: D) `--from-url`**

**Explanation:**
Methods for creating ConfigMaps in Kubernetes include from literal values (`--from-literal`), from a file (`--from-file`), and from a directory (`--from-file=<directory>`). There is no `--from-url` flag for this command. ConfigMaps can of course be created through Kubernetes REST API requests, or by applying a manifest fetched from a URL.
</details>

6. What field is used to specify a pod's service account in Kubernetes?
   - A) spec.serviceAccount
   - B) spec.serviceAccountName
   - C) metadata.serviceAccount
   - D) spec.account
   
<details>

<summary>Show Answer</summary>

**Answer: B) spec.serviceAccountName**

**Explanation:**
In Kubernetes, a pod's service account is specified through the `spec.serviceAccountName` field. This field allows you to specify which service account the pod should use. If not specified, the namespace's default service account is used.
</details>

7. What is the default encoding method for Secret data in Kubernetes?
   - A) AES-256
   - B) Base64
   - C) SHA-256
   - D) No encoding
   
<details>

<summary>Show Answer</summary>

**Answer: B) Base64**

**Explanation:**
Secret data in Kubernetes is stored encoded in Base64 by default. This is simply encoding, not encryption, so additional security measures are needed. Since Kubernetes 1.13, encryption of Secret data stored in etcd is available.
</details>

8. Which approach should be avoided when putting a real password into a Pod manifest?
   - A) Reference a Secret key
   - B) Use a protected Secret volume
   - C) Hardcoded directly in the pod spec
   - D) Retrieve from an external secret manager with workload identity
   
<details>

<summary>Show Answer</summary>

**Answer: C) Hardcoded directly in the pod spec**

**Explanation:**
Avoid literal passwords in manifests and logs. Direct `env.value` is valid for non-sensitive constants; use Secrets or an external store for confidential values. ConfigMaps and the Downward API are not password stores.
</details>

9. When every container has both CPU and memory requests equal to its limits (with no Pod-level resource settings), what QoS (Quality of Service) class is assigned?
   - A) Guaranteed
   - B) Burstable
   - C) BestEffort
   - D) Critical
   
<details>

<summary>Show Answer</summary>

**Answer: A) Guaranteed**

**Explanation:**
The Guaranteed QoS class is assigned when all containers in a pod have resource requests and limits set, and the requests equal the limits. Eviction also considers Pod priority and usage relative to requests; Guaranteed is not an unconditional survival guarantee. Burstable is assigned when only some containers have requests and limits set, or when requests and limits differ. BestEffort is assigned when no requests or limits are set.
</details>

10. When are changes to ConfigMaps or Secrets automatically reflected in pods?
    - A) Always automatically reflected
    - B) Eventually in full volume mounts (excluding subPath)
    - C) Only when used as environment variables
    - D) Never automatically reflected; pod restart required
    
<details>

<summary>Show Answer</summary>

**Answer: B) Eventually in full volume mounts (excluding subPath)**

**Explanation:**
Mutable full-volume projections update eventually; delay depends on kubelet sync and cache/change-detection settings. `subPath` mounts do not update. Applications must reread files, while environment variables require replacing/restarting the application container or rolling out new Pods.
</details>

## Hands-on Questions

1. Explain how to create ConfigMaps and Secrets and mount them to pods as environment variables and volumes.

<details>

<summary>Show Answer</summary>

**Answer:**

1. Create ConfigMap:
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
   name: app-config
data:
  app.name: MyApp
  app.properties: |
    app.name=MyApp
    app.version=1.0.0
  database.properties: |
    db.host=mysql
    db.port=3306
    db.name=mydb
```

2. Create Secret:
```yaml
apiVersion: v1
kind: Secret
metadata:
  name: app-secrets
type: Opaque
data:
  db.user: YWRtaW4=  # admin (base64 encoded)
  db.password: cGFzc3dvcmQxMjM=  # password123 (base64 encoded)
```

3. Create a pod that mounts as environment variables and volumes:
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
        # Get environment variable from ConfigMap
        - name: APP_NAME
          valueFrom:
            configMapKeyRef:
              name: app-config
              key: app.name
        # Get environment variables from Secret
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
        # Mount ConfigMap as volume
        - name: config-volume
          mountPath: /etc/config
        # Mount Secret as volume
        - name: secret-volume
          mountPath: /etc/secrets
          readOnly: true
  volumes:
    # Define ConfigMap volume
    - name: config-volume
      configMap:
        name: app-config
    # Define Secret volume
    - name: secret-volume
      secret:
        secretName: app-secrets
```

4. Apply resources:
```bash
kubectl apply -f configmap.yaml
kubectl apply -f secret.yaml
kubectl apply -f pod.yaml
```

5. Verify environment variables:
```bash
kubectl exec app-pod -- sh -c 'test -n "$APP_NAME" && test -n "$DB_PASSWORD" && echo "Configuration available"'
```

6. Verify mounted volumes:
```bash
kubectl exec app-pod -- ls -la /etc/config
kubectl exec app-pod -- ls -la /etc/secrets
```

7. Verify file contents:
```bash
kubectl exec app-pod -- cat /etc/config/app.properties
kubectl exec app-pod -- test -s /etc/secrets/db.user
```
</details>

2. Explain how to set resource requests and limits for pods and verify the QoS class.

<details>

<summary>Show Answer</summary>

**Answer:**

1. Create pods with different QoS classes:

**Guaranteed QoS Pod**:
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

**Burstable QoS Pod**:
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

**BestEffort QoS Pod**:
```yaml
apiVersion: v1
kind: Pod
metadata:
  name: besteffort-pod
spec:
  containers:
    - name: nginx
      image: nginx
# No resource requests or limits
```

2. Create pods:
```bash
kubectl apply -f guaranteed-pod.yaml
kubectl apply -f burstable-pod.yaml
kubectl apply -f besteffort-pod.yaml
```

3. Check QoS class:
```bash
kubectl get pods guaranteed-pod -o jsonpath='{.status.qosClass}'
# Output: Guaranteed

kubectl get pods burstable-pod -o jsonpath='{.status.qosClass}'
# Output: Burstable

kubectl get pods besteffort-pod -o jsonpath='{.status.qosClass}'
# Output: BestEffort
```

4. Check pod details:
```bash
kubectl describe pod guaranteed-pod | grep QoS
kubectl describe pod burstable-pod | grep QoS
kubectl describe pod besteffort-pod | grep QoS
```

5. Monitor resource usage:
```bash
kubectl top pod guaranteed-pod
kubectl top pod burstable-pod
kubectl top pod besteffort-pod
```

**QoS Class Decision Rules**:
  - **Guaranteed**: All containers have resource requests and limits set, and requests equal limits
  - **Burstable**: At least one container has resource requests set, but does not meet Guaranteed conditions
  - **BestEffort**: No resource requests or limits are set for any container
</details>

3. Explain how to use the Downward API to provide pod metadata and resource information to containers.

<details>

<summary>Show Answer</summary>

**Answer:**

1. Create a pod using the Downward API:
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
        # Provide pod metadata as environment variables
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
        # Provide container resource information as environment variables
        - name: CPU_REQUEST
          valueFrom:
            resourceFieldRef:
              containerName: main
              resource: requests.cpu
              divisor: "1m"
        - name: CPU_LIMIT
          valueFrom:
            resourceFieldRef:
              containerName: main
              resource: limits.cpu
              divisor: "1m"
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
    # Provide Downward API as volume
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
              divisor: "1m"
          - path: "cpu-limit"
            resourceFieldRef:
              containerName: main
              resource: limits.cpu
              divisor: "1m"
```

2. Create pod:
```bash
kubectl apply -f downward-api-pod.yaml
```

3. Verify environment variables:
```bash
kubectl exec downward-api-pod -- env | sort
```

4. Verify volume files:
```bash
kubectl exec downward-api-pod -- ls -la /etc/podinfo
kubectl exec downward-api-pod -- cat /etc/podinfo/labels
kubectl exec downward-api-pod -- cat /etc/podinfo/cpu-request
```

**Fields Available via Downward API**:

**Fields available as environment variables**:
  - `metadata.name` - Pod name
  - `metadata.namespace` - Pod namespace
  - `metadata.uid` - Pod UID
  - `metadata.labels['<KEY>']` - Pod label value
  - `metadata.annotations['<KEY>']` - Pod annotation value
  - `status.podIP` - Pod IP address
  - `spec.nodeName` - Name of node where pod is running
  - `spec.serviceAccountName` - Pod's service account name
  - `status.hostIP` - IP address of node where pod is running

**Resource fields**:
  - `requests.cpu` - CPU request
  - `limits.cpu` - CPU limit
  - `requests.memory` - Memory request
  - `limits.memory` - Memory limit
</details>
