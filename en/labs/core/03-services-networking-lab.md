# Services and Networking Lab Guide

> **Difficulty**: Intermediate
> **Estimated Time**: 45 minutes
> **Last Updated**: September 11, 2026

## Learning Objectives
- Create ClusterIP and NodePort Services
- Practice accessing Pods through Services
- Verify DNS-based service discovery

## Prerequisites
- [ ] kubectl, Kubernetes cluster (minikube/kind)
- [ ] Completed [Services and Networking](../../core/03-services-networking.md) learning

Use a disposable kind/minikube cluster, a matching kubectl context, permission to create namespaces, and working cluster DNS/CNI/registry access. Network policies must allow these test flows. NodePort can expose node interfaces, so use the intended test network. Run in one Bash session; no cluster/traffic tests were executed in this audit.

```bash
SERVICE_LAB_DIR=$(mktemp -d /tmp/k8s-docs-services.XXXXXX)
: "${SERVICE_LAB_DIR:?mktemp failed}"
SERVICE_LAB_CONTEXT=$(kubectl config current-context)
: "${SERVICE_LAB_CONTEXT:?No context selected}"
printf 'Selected context: %s\n' "$SERVICE_LAB_CONTEXT"
SERVICE_LAB_CANDIDATE=$(basename "$SERVICE_LAB_DIR" | tr '[:upper:].' '[:lower:]-')
unset SERVICE_LAB_NAMESPACE SERVICE_LAB_CLIENT_NAMESPACE SERVICE_LAB_CLIENT_UID
if SERVICE_LAB_UID=$(kubectl --context "$SERVICE_LAB_CONTEXT" create namespace "$SERVICE_LAB_CANDIDATE" -o jsonpath='{.metadata.uid}'); then
  SERVICE_LAB_NAMESPACE=$SERVICE_LAB_CANDIDATE
else
  printf 'Namespace creation failed; stop before resource operations\n' >&2
fi
service_kubectl() {
  kubectl --context "${SERVICE_LAB_CONTEXT:?}" --namespace "${SERVICE_LAB_NAMESPACE:?}" "$@"
}
```

---

## Exercise 1: ClusterIP Service

### Steps

**Step 1.1: Create backend Deployment**
```bash
cat > "${SERVICE_LAB_DIR:?}/web-deployment.yaml" << 'EOF'
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web
spec:
  replicas: 3
  selector:
    matchLabels:
      app: web
  template:
    metadata:
      labels:
        app: web
    spec:
      automountServiceAccountToken: false
      containers:
      - name: nginx
        image: nginx:1.30.4
        ports:
        - name: http
          containerPort: 80
        resources:
          requests:
            cpu: 100m
            memory: 64Mi
          limits:
            memory: 128Mi
        readinessProbe:
          httpGet:
            path: /
            port: http
EOF
service_kubectl apply -f "$SERVICE_LAB_DIR/web-deployment.yaml"
service_kubectl rollout status deployment/web --timeout=120s
```

**Step 1.2: Create ClusterIP Service**
```bash
cat > "${SERVICE_LAB_DIR:?}/clusterip-svc.yaml" << 'EOF'
apiVersion: v1
kind: Service
metadata:
  name: web-clusterip
spec:
  type: ClusterIP
  selector:
    app: web
  ports:
  - name: http
    port: 80
    targetPort: http
EOF
service_kubectl apply -f "$SERVICE_LAB_DIR/clusterip-svc.yaml"
service_kubectl get service web-clusterip
```

**Step 1.3: Test access from inside the cluster**
```bash
service_kubectl run http-check --image=busybox:1.37.0 \
  --overrides='{"spec":{"automountServiceAccountToken":false}}' \
  --rm -i --restart=Never --pod-running-timeout=120s --command -- sh -c '
for attempt in 1 2 3 4 5; do
  wget -T 5 -qO- "$1" && exit 0
  sleep 1
done
exit 1
' sh http://web-clusterip/
```
<details>
<summary>Need a hint?</summary>

- ClusterIP provides an internal virtual address; it is not a security boundary and routed reachability depends on the network.
- The full DNS form is `<service>.<namespace>.svc.<cluster-domain>`; `cluster.local` is only the common default.
- With normal Pod DNS search settings, the same namespace can use `<service>`, and another namespace can use `<service>.<namespace>`.
</details>

### Verification
EndpointSlices replace the deprecated Endpoints view. Confirm ready backend addresses; updates are asynchronous and slices/address families can split the result. Three ready replicas do not imply exactly three rows in every output format.

```bash
service_kubectl get endpointslices -l kubernetes.io/service-name=web-clusterip -o wide
service_kubectl get endpointslices -l kubernetes.io/service-name=web-clusterip \
  -o jsonpath='{range .items[*].endpoints[*]}{.addresses}{" ready="}{.conditions.ready}{"\n"}{end}'
```

---

## Exercise 2: NodePort Service

### Steps

**Step 2.1: Create NodePort Service**
```bash
cat > "${SERVICE_LAB_DIR:?}/nodeport-svc.yaml" << 'EOF'
apiVersion: v1
kind: Service
metadata:
  name: web-nodeport
spec:
  type: NodePort
  selector:
    app: web
  ports:
  - name: http
    port: 80
    targetPort: http
EOF
service_kubectl apply -f "$SERVICE_LAB_DIR/nodeport-svc.yaml"
SERVICE_LAB_NODE_PORT=$(service_kubectl get service web-nodeport -o jsonpath='{.spec.ports[0].nodePort}')
: "${SERVICE_LAB_NODE_PORT:?No allocated NodePort}"
service_kubectl get service web-nodeport
```

**Step 2.2: Access from outside**
NodePort is allocated rather than assuming30080 is free. A Service type/port listing proves configuration, not client reachability. Use the direct node-address command only where routing, nodePortAddresses and firewall policy permit it.

```bash
printf 'Allocated NodePort: %s\n' "${SERVICE_LAB_NODE_PORT:?}"
kubectl --context "${SERVICE_LAB_CONTEXT:?}" get nodes -o wide

# Use only an address reachable from this client and permitted by node/firewall policy.
: "${SERVICE_LAB_NODE_ADDRESS:?Set a reachable node address}"
case "$SERVICE_LAB_NODE_ADDRESS" in
  *:*) SERVICE_LAB_NODE_URL_HOST="[$SERVICE_LAB_NODE_ADDRESS]" ;;
  *) SERVICE_LAB_NODE_URL_HOST=$SERVICE_LAB_NODE_ADDRESS ;;
esac
curl --disable --noproxy '*' --fail --show-error --silent --max-time 5 \
  "http://$SERVICE_LAB_NODE_URL_HOST:$SERVICE_LAB_NODE_PORT/"
```

On minikube, select the matching profile. Some Docker-driver platforms require the service command to keep a tunnel open in a separate terminal; use its printed URL. Do not suppress errors or replace them with a hardcoded port. For kind host access, preconfigured extraPortMappings must match the Service nodePort. If node IPs are not reachable, a separately chosen `service_kubectl port-forward --address=127.0.0.1 service/web-nodeport 18080:80` can test the application, but it does **not** validate the NodePort data path.

```bash
# Only for minikube: the profile must correspond to SERVICE_LAB_CONTEXT.
: "${SERVICE_LAB_MINIKUBE_PROFILE:?Set the matching minikube profile}"
minikube --profile "$SERVICE_LAB_MINIKUBE_PROFILE" \
  service web-nodeport --namespace "${SERVICE_LAB_NAMESPACE:?}" --url
```
### Verification
```bash
service_kubectl get service web-nodeport -o jsonpath='{.spec.type}{"\n"}{.spec.ports[0].nodePort}{"\n"}'
```

---

## Exercise 3: DNS Service Discovery

### Steps

**Step 3.1: DNS lookup test**
```bash
service_kubectl run dns-check --image=busybox:1.37.0 \
  --overrides='{"spec":{"automountServiceAccountToken":false}}' \
  --rm -i --restart=Never --pod-running-timeout=120s --command -- nslookup web-clusterip
service_kubectl get service web-clusterip -o jsonpath='{.spec.clusterIP}{"\n"}'
```

Resolver IP, answer IP and cluster domain depend on the cluster. For this normal ClusterIP Service, DNS should resolve the Service virtual IP shown above, not each backend Pod IP. The full name contains this lab namespace, not a hardcoded default namespace.

**Step 3.2: Access from different namespace**
```bash
SERVICE_LAB_CLIENT_CANDIDATE="${SERVICE_LAB_NAMESPACE:?}-client"
unset SERVICE_LAB_CLIENT_NAMESPACE
if SERVICE_LAB_CLIENT_UID=$(kubectl --context "${SERVICE_LAB_CONTEXT:?}" create namespace "$SERVICE_LAB_CLIENT_CANDIDATE" -o jsonpath='{.metadata.uid}'); then
  SERVICE_LAB_CLIENT_NAMESPACE=$SERVICE_LAB_CLIENT_CANDIDATE
  kubectl --context "$SERVICE_LAB_CONTEXT" --namespace "$SERVICE_LAB_CLIENT_NAMESPACE" \
    run cross-ns-check --image=busybox:1.37.0 \
    --overrides='{"spec":{"automountServiceAccountToken":false}}' \
    --rm -i --restart=Never --pod-running-timeout=120s --command -- \
    wget -T 5 -qO- "http://web-clusterip.$SERVICE_LAB_NAMESPACE/"
else
  printf 'Client namespace was not created; no cross-namespace test was run\n' >&2
fi
```

<details>
<summary>Need a hint?</summary>

- With the standard DNS search path, `service.namespace` is sufficient across namespaces; the full cluster domain is another option.
- CoreDNS or the configured cluster DNS implementation publishes Service records.
- Check DNS Pods with `kubectl get pods -n kube-system -l k8s-app=kube-dns`
</details>

---

## Cleanup
```bash
delete_service_lab_namespace() {
  local name="$1" expected_uid="$2" current_uid
  [[ -n "$name" && -n "$expected_uid" ]] || return 0
  current_uid=$(kubectl --context "${SERVICE_LAB_CONTEXT:?}" get namespace "$name" -o jsonpath='{.metadata.uid}') || return 0
  if [ "$current_uid" = "$expected_uid" ]; then
    kubectl --context "$SERVICE_LAB_CONTEXT" delete namespace "$name" --timeout=120s
  else
    printf 'Namespace identity changed; deletion skipped: %s\n' "$name"
  fi
}
delete_service_lab_namespace "${SERVICE_LAB_CLIENT_NAMESPACE:-}" "${SERVICE_LAB_CLIENT_UID:-}"
delete_service_lab_namespace "${SERVICE_LAB_NAMESPACE:-}" "${SERVICE_LAB_UID:-}"
if [[ -n ${SERVICE_LAB_DIR:-} ]]; then
  rm -f -- "$SERVICE_LAB_DIR/web-deployment.yaml" "$SERVICE_LAB_DIR/clusterip-svc.yaml" "$SERVICE_LAB_DIR/nodeport-svc.yaml"
  rmdir -- "$SERVICE_LAB_DIR"
fi
unset -f service_kubectl delete_service_lab_namespace
```


## References and validation scope

* [Service](https://kubernetes.io/docs/concepts/services-networking/service/)
* [EndpointSlice](https://kubernetes.io/docs/concepts/services-networking/endpoint-slices/)
* [DNS for Services and Pods](https://kubernetes.io/docs/concepts/services-networking/dns-pod-service/)
* [minikube access](https://minikube.sigs.k8s.io/docs/handbook/accessing/)
* [kind port mappings](https://kind.sigs.k8s.io/docs/user/configuration/#extra-port-mappings)

Validation is local manifest/command checking, not a recorded CNI, DNS or NodePort test. Temporary clients use explicit commands and do not need service-account tokens.

## Next Steps
- [Services and Networking Quiz](../../quizzes/core/03-services-networking-quiz.md)
- [Storage Lab](./04-storage-lab.md)
