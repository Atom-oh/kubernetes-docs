# Cuestionario de configuración

Este cuestionario evalúa tu comprensión de los conceptos de configuración de Kubernetes, incluidos ConfigMap, Secret, variables de entorno, requests y limits de recursos.

## Preguntas de opción múltiple

1. ¿Qué recurso se utiliza para almacenar información confidencial en Kubernetes?
   - A) ConfigMap
   - B) Secret
   - C) Volume
   - D) Deployment
   
<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Secret**

**Explicación:**
Secret es un recurso de Kubernetes para almacenar información confidencial, como contraseñas, tokens OAuth y claves SSH. Los Secrets se almacenan codificados en base64 de forma predeterminada y se pueden montar en pods como archivos o variables de entorno. ConfigMap se utiliza para almacenar datos de configuración no confidenciales.
</details>

2. ¿Cuál es el propósito principal de ConfigMap en Kubernetes?
   - A) Almacenar imágenes de contenedor
   - B) Almacenar datos de configuración de la aplicación
   - C) Definir políticas de red
   - D) Controlar la programación de pods
   
<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Almacenar datos de configuración de la aplicación**

**Explicación:**
ConfigMap es un recurso de Kubernetes que almacena datos de configuración en pares clave-valor. Esto te permite separar el código de la aplicación de la configuración, lo que habilita diferentes configuraciones para distintos entornos. Los ConfigMaps se pueden montar en contenedores como variables de entorno, argumentos de línea de comandos o archivos de configuración.
</details>

3. ¿Cuál es la diferencia entre requests y limits de recursos en pods de Kubernetes?
   - A) Los requests orientan la planificación y la asignación de recursos; los limits restringen el uso durante la ejecución
   - B) Los requests son los recursos máximos que un pod puede usar; los limits son el mínimo
   - C) Los requests solo se usan para la programación; los limits solo se aplican en tiempo de ejecución
   - D) Los requests solo se aplican a CPU; los limits solo se aplican a memoria
   
<details>

<summary>Mostrar respuesta</summary>

**Respuesta: A) Los requests orientan la planificación y la asignación de recursos; los limits restringen el uso durante la ejecución**

**Explicación:**
Los requests reservan capacidad para la planificación y afectan a la asignación de recursos durante la ejecución; un proceso puede usar menos de lo solicitado. Los límites de CPU se aplican mediante estrangulamiento (throttling); los límites de memoria se aplican de forma reactiva al terminar el proceso por OOM. Los requests no garantizan protección frente a la presión del nodo.
</details>

4. ¿Cuál NO es un método para proporcionar datos de Secret a pods en Kubernetes?
   - A) Como variables de entorno
   - B) Como un volumen montado
   - C) Como credenciales de registro de imágenes
   - D) Como una interfaz de red
   
<details>

<summary>Mostrar respuesta</summary>

**Respuesta: D) Como una interfaz de red**

**Explicación:**
Los métodos para proporcionar datos de Secret a pods en Kubernetes incluyen hacerlo como variables de entorno, como un volumen montado y como credenciales de registro de imágenes. Kubernetes no admite proporcionar Secrets a través de una interfaz de red.
</details>

5. ¿Cuál de estas opciones NO es compatible con el comando `kubectl create configmap`?
   - A) A partir de valores literales
   - B) A partir de un archivo
   - C) A partir de un directorio
   - D) `--from-url`
   
<details>

<summary>Mostrar respuesta</summary>

**Respuesta: D) `--from-url`**

**Explicación:**
Los métodos para crear ConfigMaps con este comando incluyen valores literales (`--from-literal`), archivos (`--from-file`) y directorios (`--from-file=<directory>`). El comando no tiene la opción `--from-url`. Por supuesto, también se pueden crear ConfigMaps mediante solicitudes a la API REST de Kubernetes o aplicando un manifiesto obtenido desde una URL.
</details>

6. ¿Qué campo se usa para especificar la service account de un pod en Kubernetes?
   - A) spec.serviceAccount
   - B) spec.serviceAccountName
   - C) metadata.serviceAccount
   - D) spec.account
   
<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) spec.serviceAccountName**

**Explicación:**
En Kubernetes, la service account de un pod se especifica mediante el campo `spec.serviceAccountName`. Este campo te permite especificar qué service account debe usar el pod. Si no se especifica, se usa la service account predeterminada del namespace.
</details>

7. ¿Cuál es el método de codificación predeterminado para los datos de Secret en Kubernetes?
   - A) AES-256
   - B) Base64
   - C) SHA-256
   - D) Sin codificación
   
<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Base64**

**Explicación:**
Los datos de Secret en Kubernetes se almacenan codificados en Base64 de forma predeterminada. Esto es simplemente codificación, no cifrado, por lo que se necesitan medidas de seguridad adicionales. Desde Kubernetes 1.13, está disponible el cifrado de datos de Secret almacenados en etcd.
</details>

8. ¿Qué forma de incluir una contraseña real en el manifiesto de un Pod se debe evitar?
   - A) Referenciar una clave de un Secret
   - B) Usar un volumen protegido de Secret
   - C) Escribirla directamente en la especificación del Pod
   - D) Obtenerla de un gestor externo de secretos mediante identidad de carga de trabajo
   
<details>

<summary>Mostrar respuesta</summary>

**Respuesta: C) Escribirla directamente en la especificación del Pod**

**Explicación:**
Evita incluir contraseñas literales en manifiestos y registros. Usar directamente `env.value` es válido para constantes no confidenciales; para valores confidenciales, usa Secrets o un almacén externo. ConfigMaps y Downward API no son almacenes de contraseñas.
</details>

9. Cuando todos los contenedores tienen requests y limits de CPU y memoria iguales (y no hay ajustes de recursos a nivel del Pod), ¿qué clase QoS (Quality of Service) se asigna?
   - A) Guaranteed
   - B) Burstable
   - C) BestEffort
   - D) Critical
   
<details>

<summary>Mostrar respuesta</summary>

**Respuesta: A) Guaranteed**

**Explicación:**
La clase QoS Guaranteed se asigna cuando todos los contenedores tienen requests y limits de CPU y memoria, y cada request coincide con su limit, sin ajustes de recursos a nivel del Pod. El desalojo también tiene en cuenta la prioridad del Pod y el uso respecto de los requests; Guaranteed no garantiza sobrevivir en cualquier circunstancia. Burstable se asigna cuando solo algunos contenedores tienen requests y limits, o cuando los requests y limits difieren. BestEffort se asigna cuando no se establece ningún request ni limit.
</details>

10. ¿Cuándo se reflejan automáticamente en los pods los cambios en ConfigMaps o Secrets?
    - A) Siempre se reflejan automáticamente
    - B) Eventualmente, en montajes de volumen completos (excepto `subPath`)
    - C) Solo cuando se usan como volúmenes montados
    - D) Nunca se reflejan automáticamente; se requiere reiniciar el pod
    
<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Eventualmente, en montajes de volumen completos (excepto `subPath`)**

**Explicación:**
Las proyecciones mutables en volúmenes completos se actualizan eventualmente; el retraso depende de la sincronización del kubelet y de la configuración de caché/detección de cambios. Los montajes `subPath` no se actualizan. Las aplicaciones deben volver a leer los archivos; para actualizar las variables de entorno, hay que reemplazar o reiniciar el contenedor de la aplicación, o desplegar Pods nuevos.
</details>

## Preguntas prácticas

1. Explica cómo crear ConfigMaps y Secrets, y montarlos en pods como variables de entorno y volumes.

<details>

<summary>Mostrar respuesta</summary>

**Respuesta:**

1. Crear ConfigMap:
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

2. Crear Secret:
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

3. Crear un pod que monte como variables de entorno y volumes:
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

4. Aplicar recursos:
```bash
kubectl apply -f configmap.yaml
kubectl apply -f secret.yaml
kubectl apply -f pod.yaml
```

5. Verificar variables de entorno:
```bash
kubectl exec app-pod -- sh -c 'test -n "$APP_NAME" && test -n "$DB_PASSWORD" && echo "Configuration available"'
```

6. Verificar volumes montados:
```bash
kubectl exec app-pod -- ls -la /etc/config
kubectl exec app-pod -- ls -la /etc/secrets
```

7. Verificar contenido de archivos:
```bash
kubectl exec app-pod -- cat /etc/config/app.properties
kubectl exec app-pod -- test -s /etc/secrets/db.user
```
</details>

2. Explica cómo establecer resource requests y limits para pods, y verificar la clase QoS.

<details>

<summary>Mostrar respuesta</summary>

**Respuesta:**

1. Crear pods con diferentes clases QoS:

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

2. Crear pods:
```bash
kubectl apply -f guaranteed-pod.yaml
kubectl apply -f burstable-pod.yaml
kubectl apply -f besteffort-pod.yaml
```

3. Verificar la clase QoS:
```bash
kubectl get pods guaranteed-pod -o jsonpath='{.status.qosClass}'
# Output: Guaranteed

kubectl get pods burstable-pod -o jsonpath='{.status.qosClass}'
# Output: Burstable

kubectl get pods besteffort-pod -o jsonpath='{.status.qosClass}'
# Output: BestEffort
```

4. Verificar detalles del pod:
```bash
kubectl describe pod guaranteed-pod | grep QoS
kubectl describe pod burstable-pod | grep QoS
kubectl describe pod besteffort-pod | grep QoS
```

5. Monitorear el uso de recursos:
```bash
kubectl top pod guaranteed-pod
kubectl top pod burstable-pod
kubectl top pod besteffort-pod
```

**Reglas de decisión de clase QoS**:
  - **Guaranteed**: Todos los contenedores tienen resource requests y limits establecidos, y los requests son iguales a los limits
  - **Burstable**: Al menos un contenedor tiene resource requests establecidos, pero no cumple las condiciones de Guaranteed
  - **BestEffort**: No se establecen resource requests ni limits para ningún contenedor
</details>

3. Explica cómo usar la Downward API para proporcionar metadatos del pod e información de recursos a los contenedores.

<details>

<summary>Mostrar respuesta</summary>

**Respuesta:**

1. Crear un pod usando la Downward API:
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

2. Crear pod:
```bash
kubectl apply -f downward-api-pod.yaml
```

3. Verificar variables de entorno:
```bash
kubectl exec downward-api-pod -- env | sort
```

4. Verificar archivos del volume:
```bash
kubectl exec downward-api-pod -- ls -la /etc/podinfo
kubectl exec downward-api-pod -- cat /etc/podinfo/labels
kubectl exec downward-api-pod -- cat /etc/podinfo/cpu-request
```

**Campos disponibles mediante la Downward API**:

**Campos disponibles como variables de entorno**:
  - `metadata.name` - Nombre del Pod
  - `metadata.namespace` - Namespace del Pod
  - `metadata.uid` - UID del Pod
  - `metadata.labels['<KEY>']` - Valor de label del Pod
  - `metadata.annotations['<KEY>']` - Valor de annotation del Pod
  - `status.podIP` - Dirección IP del Pod
  - `spec.nodeName` - Nombre del node donde se ejecuta el pod
  - `spec.serviceAccountName` - Nombre de la service account del Pod
  - `status.hostIP` - Dirección IP del node donde se ejecuta el pod

**Campos de recursos**:
  - `requests.cpu` - CPU request
  - `limits.cpu` - CPU limit
  - `requests.memory` - Memory request
  - `limits.memory` - Memory limit
</details>
