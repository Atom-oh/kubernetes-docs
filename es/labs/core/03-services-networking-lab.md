# Guía de laboratorio de servicios y redes

> **Dificultad**: Intermedio
> **Tiempo estimado**: 45 minutos
> **Última actualización**: 11 de septiembre de 2026

## Objetivos de aprendizaje
- Crear recursos Service de tipo ClusterIP y NodePort
- Practicar el acceso a Pods mediante Services
- Verificar el descubrimiento de Services mediante DNS

## Requisitos previos
- [ ] kubectl y un clúster de Kubernetes (minikube/kind)
- [ ] Haber completado el material de aprendizaje [Servicios y redes](../../core/03-services-networking.md)

Usa un clúster desechable de kind/minikube, un contexto de kubectl que corresponda a ese clúster, permisos para crear namespaces y acceso funcional al DNS, CNI y registro de imágenes del clúster. Las políticas de red deben permitir estos flujos de prueba. NodePort puede exponer las interfaces de los nodos, así que usa la red de prueba prevista. Ejecuta todos los pasos en una misma sesión de Bash; en esta auditoría no se ejecutaron pruebas contra un clúster ni de tráfico.

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

## Ejercicio 1: Service ClusterIP

### Pasos

**Paso 1.1: Crear un Deployment de backend**
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
        image: nginx:1.30.6
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

**Paso 1.2: Crear un Service ClusterIP**
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

**Paso 1.3: Probar el acceso desde dentro del clúster**
```bash
service_kubectl run http-check --image=busybox:1.38.0 \
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
<summary>¿Necesitas una pista?</summary>

- ClusterIP proporciona una dirección virtual interna; no constituye un límite de seguridad y la alcanzabilidad enrutada depende de la red.
- El nombre DNS completo tiene el formato `<service>.<namespace>.svc.<cluster-domain>`; `cluster.local` es solo el dominio predeterminado más habitual.
- Con la configuración DNS habitual de los Pods, en el mismo namespace basta con `<service>` y, desde otro namespace, se puede usar `<service>.<namespace>`.
</details>

### Verificación
EndpointSlices reemplazaron la vista obsoleta Endpoints. Confirma que las direcciones de los backends estén listas; las actualizaciones son asíncronas, y los slices y las familias de direcciones pueden dividir los resultados. Tres réplicas listas no implican que todos los formatos de salida muestren exactamente tres filas.

```bash
service_kubectl get endpointslices -l kubernetes.io/service-name=web-clusterip -o wide
service_kubectl get endpointslices -l kubernetes.io/service-name=web-clusterip \
  -o jsonpath='{range .items[*].endpoints[*]}{.addresses}{" ready="}{.conditions.ready}{"\n"}{end}'
```

---

## Ejercicio 2: Service NodePort

### Pasos

**Paso 2.1: Crear un Service NodePort**
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

**Paso 2.2: Acceder desde fuera**
NodePort se asigna automáticamente; no supongas que el puerto 30080 está libre. Una lista de tipo/puerto de Service demuestra la configuración, no que los clientes puedan alcanzarlo. Ejecuta el comando que usa directamente la dirección del nodo solo cuando lo permitan el enrutamiento, nodePortAddresses y la política del firewall.

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

En minikube, selecciona el perfil correspondiente. En algunas plataformas con controlador Docker, el comando de servicio debe mantener abierto un túnel en otra terminal; usa la URL que muestre. No ocultes errores ni los reemplaces por un puerto fijo. Para acceder desde el host con kind, los extraPortMappings deben estar configurados de antemano y coincidir con el nodePort del Service. Si no se puede acceder a las IP de los nodos, un `service_kubectl port-forward --address=127.0.0.1 service/web-nodeport 18080:80` elegido por separado permite probar la aplicación, pero **no** valida la ruta de datos de NodePort.

```bash
# Only for minikube: the profile must correspond to SERVICE_LAB_CONTEXT.
: "${SERVICE_LAB_MINIKUBE_PROFILE:?Set the matching minikube profile}"
minikube --profile "$SERVICE_LAB_MINIKUBE_PROFILE" \
  service web-nodeport --namespace "${SERVICE_LAB_NAMESPACE:?}" --url
```
### Verificación
```bash
service_kubectl get service web-nodeport -o jsonpath='{.spec.type}{"\n"}{.spec.ports[0].nodePort}{"\n"}'
```

---

## Ejercicio 3: Descubrimiento de Services mediante DNS

### Pasos

**Paso 3.1: Probar la resolución DNS**
```bash
service_kubectl run dns-check --image=busybox:1.38.0 \
  --overrides='{"spec":{"automountServiceAccountToken":false}}' \
  --rm -i --restart=Never --pod-running-timeout=120s --command -- nslookup web-clusterip
service_kubectl get service web-clusterip -o jsonpath='{.spec.clusterIP}{"\n"}'
```

La IP del resolver, la IP de respuesta y el dominio del clúster dependen del clúster. Para este Service ClusterIP normal, DNS debería resolver la IP virtual del Service que se muestra arriba, no las IP de cada Pod backend. El nombre completo debe incluir el namespace de este laboratorio, no un namespace predeterminado fijado de antemano.

**Paso 3.2: Acceder desde otro namespace**
```bash
SERVICE_LAB_CLIENT_CANDIDATE="${SERVICE_LAB_NAMESPACE:?}-client"
unset SERVICE_LAB_CLIENT_NAMESPACE
if SERVICE_LAB_CLIENT_UID=$(kubectl --context "${SERVICE_LAB_CONTEXT:?}" create namespace "$SERVICE_LAB_CLIENT_CANDIDATE" -o jsonpath='{.metadata.uid}'); then
  SERVICE_LAB_CLIENT_NAMESPACE=$SERVICE_LAB_CLIENT_CANDIDATE
  kubectl --context "$SERVICE_LAB_CONTEXT" --namespace "$SERVICE_LAB_CLIENT_NAMESPACE" \
    run cross-ns-check --image=busybox:1.38.0 \
    --overrides='{"spec":{"automountServiceAccountToken":false}}' \
    --rm -i --restart=Never --pod-running-timeout=120s --command -- \
    wget -T 5 -qO- "http://web-clusterip.$SERVICE_LAB_NAMESPACE/"
else
  printf 'Client namespace was not created; no cross-namespace test was run\n' >&2
fi
```

<details>
<summary>¿Necesitas una pista?</summary>

- Con la ruta de búsqueda DNS estándar, `service.namespace` basta para acceder desde otro namespace; también se puede usar el dominio completo del clúster.
- CoreDNS o la implementación de DNS configurada en el clúster publica los registros de Services.
- Comprueba los Pods de DNS con `kubectl get pods -n kube-system -l k8s-app=kube-dns`
</details>

---

## Limpieza
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

## Referencias y alcance de la validación

* [Service](https://kubernetes.io/docs/concepts/services-networking/service/)
* [EndpointSlice](https://kubernetes.io/docs/concepts/services-networking/endpoint-slices/)
* [DNS para Services y Pods](https://kubernetes.io/docs/concepts/services-networking/dns-pod-service/)
* [Acceso desde minikube](https://minikube.sigs.k8s.io/docs/handbook/accessing/)
* [Asignación de puertos en kind](https://kind.sigs.k8s.io/docs/user/configuration/#extra-port-mappings)

La validación consiste en comprobar manifiestos y comandos localmente; no se registraron pruebas de CNI, DNS ni NodePort. Los clientes temporales usan comandos explícitos y no necesitan tokens de ServiceAccount.

## Siguientes pasos
- [Cuestionario de servicios y redes](../../quizzes/core/03-services-networking-quiz.md)
- [Laboratorio de almacenamiento](./04-storage-lab.md)
