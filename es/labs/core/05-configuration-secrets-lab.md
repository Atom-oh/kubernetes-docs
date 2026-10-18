# Guía del laboratorio de ConfigMap y Secret

> **Dificultad**: Principiante
> **Tiempo estimado**: 35 minutos
> **Última actualización**: 11 de septiembre de 2026

## Objetivos de aprendizaje
- Crear ConfigMaps y usarlos en Pods
- Crear Secrets e inyectarlos de forma segura
- Comparar los métodos de inyección mediante variables de entorno y montaje de volúmenes

## Requisitos previos
- [ ] kubectl y un clúster de Kubernetes
- [ ] Haber completado el módulo de [Configuración](../../core/05-configuration-secrets.md)

Usa Bash y un clúster desechable existente de kind o minikube. Ejecuta los pasos en la misma shell y detente si falla algún comando de requisito previo. Antes de crear el espacio de nombres, confirma que el contexto seleccionado corresponde al clúster previsto para el laboratorio. Todas las credenciales siguientes son datos ficticios públicos; este laboratorio no se conecta a ninguna base de datos.

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

## Ejercicio 1: Crear y usar un ConfigMap

### Pasos

**Paso 1.1: Crear un ConfigMap**
```bash
# Create from literal values
config_kubectl create configmap app-config \
  --from-literal=APP_ENV=production \
  --from-literal=LOG_LEVEL=info \
  --from-literal=MAX_CONNECTIONS=100

config_kubectl get configmap app-config -o yaml
```

**Paso 1.2: Crear un ConfigMap a partir de un archivo**
```bash
cat > "${CONFIG_LAB_DIR:?}/app.properties" << 'EOF'
database.host=mysql
database.port=3306
database.name=myapp
EOF

config_kubectl create configmap app-properties --from-file="${CONFIG_LAB_DIR:?}/app.properties"
config_kubectl describe configmap app-properties
```

Estas propiedades son texto de configuración de ejemplo. No se crea ni se valida ningún Service de MySQL, base de datos o flujo de autenticación.

**Paso 1.3: Inyectar el ConfigMap como variables de entorno**
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
    image: busybox:1.38.0
    command: ["sh", "-ec", "echo APP_ENV=$APP_ENV LOG_LEVEL=$LOG_LEVEL; exec sleep 3600"]
    envFrom:
    - configMapRef:
        name: app-config
EOF

config_kubectl apply -f "${CONFIG_LAB_DIR:?}/configmap-env-pod.yaml"
config_kubectl wait --for=condition=ready pod/config-env-demo --timeout=120s
config_kubectl logs config-env-demo
```

Salida esperada:
```
APP_ENV=production LOG_LEVEL=info
```

**Paso 1.4: Montar el ConfigMap como volumen**
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
    image: busybox:1.38.0
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
<summary>¿Necesitas una pista?</summary>

- `envFrom` importa las claves del ConfigMap usadas en este ejemplo como variables de entorno.
- Cada clave montada se convierte en un archivo. Las actualizaciones se propagan eventualmente mediante el mecanismo de sincronización y caché de kubelet; no son inmediatas.
- Un montaje con `subPath` no recibe actualizaciones. Las variables de entorno quedan fijadas cuando se inicia el contenedor; reemplaza el Pod para cargar valores nuevos. Si un proceso lee el archivo una sola vez, también necesitará una recarga o un reinicio explícitos.
</details>

---

## Ejercicio 2: Administrar Secrets

### Pasos

**Paso 2.1: Crear un Secret**
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

Solo deben mostrarse los nombres de las claves. Usar archivos evita incluir credenciales reales en los argumentos de los comandos; aun así, estos archivos locales privados contienen texto sin cifrar y deben eliminarse al terminar el laboratorio. Base64 en una respuesta de la API de Secret es una codificación, no un cifrado. El cifrado en reposo, RBAC con privilegios mínimos y la rotación requieren configuración aparte. El permiso para crear Pods en este espacio de nombres también puede permitir acceder a sus Secrets.

**Paso 2.2: Inyectar el Secret en un Pod**
El contenedor se ejecuta sin root y comprueba que existan los valores sin imprimir nombres de usuario, contraseñas ni longitudes. El volumen del Secret es de solo lectura; `0440` es un modo octal de YAML (decimal `288` en JSON), y `fsGroup` concede acceso de lectura al grupo de este contenedor. Se muestran ambos métodos de inyección para compararlos, no porque una aplicación necesite copias duplicadas.

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
    image: busybox:1.38.0
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

Salida esperada:
```
Dummy credentials available through environment and files
```

**Paso 2.3: Mostrar base64 con texto ficticio sin conexión**
```bash
printf '%s' 'lab-only' | base64 | base64 -d
printf '\n'
```

<details>
<summary>¿Necesitas una pista?</summary>

- Este ejemplo sin conexión solo imprime la cadena pública `lab-only`; nunca decodifiques un Secret activo en terminales compartidos ni en registros.
- Actualizar un Secret no cambia las variables de entorno de un contenedor existente. Las proyecciones normales de volúmenes Secret se actualizan eventualmente, pero las aplicaciones deben volver a leer los archivos; `subPath` no se actualiza.
- Los almacenes o controladores externos de secretos requieren su propia configuración de identidad, autorización y rotación. Instalar una herramienta no proporciona por sí solo esas garantías.
</details>

---

## Ejercicio 3: Comparar las variables de entorno con el montaje de volúmenes

### Pasos

**Paso 3.1: Actualizar los ConfigMaps y comparar los Pods en ejecución**
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

El registro original de `config-vol-demo` contiene una lectura realizada solo al inicio. Volver a inspeccionar el archivo montado demuestra la proyección, no una recarga automática de la aplicación. El número de reintentos y la demora son parámetros de observación de este ejercicio; la duración de los comandos se suma al tiempo transcurrido y Kubernetes no garantiza que la actualización llegue dentro de este intervalo. Cuando el Pod de reemplazo se inicie correctamente, su registro debería mostrar `LOG_LEVEL=debug`.

---

## Limpieza
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

## Referencias y alcance de la validación

- [Proyección y actualizaciones de ConfigMap](https://kubernetes.io/docs/concepts/configuration/configmap/)
- [Seguridad y actualizaciones de Secret](https://kubernetes.io/docs/concepts/configuration/secret/)
- [Permisos de archivos Secret y variables de entorno](https://kubernetes.io/docs/tasks/inject-data-application/distribute-credentials-secure/)

La validación abarca la sintaxis de shell, los manifiestos y los recursos de prueba locales. Durante esta revisión no se creó ni se accedió a ningún Secret, Pod o espacio de nombres de Kubernetes ni a ningún almacén externo de secretos.

## Próximos pasos
- [Cuestionario de configuración](../../quizzes/core/05-configuration-secrets-quiz.md)
- [Laboratorio de creación de clústeres EKS](../eks/01-eks-cluster-creation-lab.md)
