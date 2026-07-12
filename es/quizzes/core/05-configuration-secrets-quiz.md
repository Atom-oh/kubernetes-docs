# Cuestionario sobre Configuration

Este cuestionario evalúa tu comprensión de los conceptos de configuración de Kubernetes, incluidos ConfigMap, Secret, variables de entorno, resource requests y limits.

## Preguntas de opción múltiple

1. ¿Qué recurso se utiliza para almacenar información sensible en Kubernetes?
   - A) ConfigMap
   - B) Secret
   - C) Volume
   - D) Deployment
   
<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Secret**

**Explicación:**
Secret es un recurso de Kubernetes para almacenar información sensible, como contraseñas, tokens OAuth y claves SSH. Los Secrets se almacenan codificados en base64 de forma predeterminada y se pueden montar en Pods como archivos o variables de entorno. ConfigMap se utiliza para almacenar datos de configuración no sensibles.
</details>

2. ¿Cuál es el propósito principal de ConfigMap en Kubernetes?
   - A) Almacenar imágenes de containers
   - B) Almacenar datos de configuración de la aplicación
   - C) Definir políticas de red
   - D) Controlar la programación de Pods
   
<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Almacenar datos de configuración de la aplicación**

**Explicación:**
ConfigMap es un recurso de Kubernetes que almacena datos de configuración en pares clave-valor. Esto te permite separar el código de la aplicación de la configuración, habilitando diferentes configuraciones para diferentes entornos. Los ConfigMaps se pueden montar en containers como variables de entorno, argumentos de línea de comandos o archivos de configuración.
</details>

3. ¿Cuál es la diferencia entre resource requests y limits en Pods de Kubernetes?
   - A) Las requests son los recursos mínimos que un Pod puede usar, los limits son los máximos
   - B) Las requests son los recursos máximos que un Pod puede usar, los limits son los mínimos
   - C) Las requests solo se utilizan para la programación, los limits solo se aplican en tiempo de ejecución
   - D) Las requests solo se aplican a CPU, los limits solo se aplican a memoria
   
<details>

<summary>Mostrar respuesta</summary>

**Respuesta: A) Las requests son los recursos mínimos que un Pod puede usar, los limits son los máximos**

**Explicación:**
Los resource requests especifican la cantidad mínima de recursos garantizada a un Pod, y el scheduler usa estos valores al colocar Pods en nodes. Los resource limits especifican la cantidad máxima de recursos que un Pod puede usar. Cuando se superan estos valores, el Pod puede ser limitado (para CPU) o terminado (para memoria).
</details>

4. ¿Cuál NO es un método para proporcionar datos de Secret a Pods en Kubernetes?
   - A) Como variables de entorno
   - B) Como un volume montado
   - C) Como credenciales de image registry
   - D) Como una interfaz de red
   
<details>

<summary>Mostrar respuesta</summary>

**Respuesta: D) Como una interfaz de red**

**Explicación:**
Los métodos para proporcionar datos de Secret a Pods en Kubernetes incluyen como variables de entorno, como un volume montado y como credenciales de image registry. Proporcionar Secrets a través de una interfaz de red no está soportado en Kubernetes.
</details>

5. ¿Cuál NO es un método para crear un ConfigMap en Kubernetes?
   - A) A partir de valores literales
   - B) A partir de un archivo
   - C) A partir de un directorio
   - D) A partir de una solicitud de red
   
<details>

<summary>Mostrar respuesta</summary>

**Respuesta: D) A partir de una solicitud de red**

**Explicación:**
Los métodos para crear ConfigMaps en Kubernetes incluyen a partir de valores literales (`--from-literal`), a partir de un archivo (`--from-file`) y a partir de un directorio (`--from-file=<directory>`). Crear un ConfigMap directamente a partir de una solicitud de red no está soportado de forma nativa en Kubernetes.
</details>

6. ¿Qué campo se utiliza para especificar la service account de un Pod en Kubernetes?
   - A) spec.serviceAccount
   - B) spec.serviceAccountName
   - C) metadata.serviceAccount
   - D) spec.account
   
<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) spec.serviceAccountName**

**Explicación:**
En Kubernetes, la service account de un Pod se especifica mediante el campo `spec.serviceAccountName`. Este campo permite especificar qué service account debe usar el Pod. Si no se especifica, se utiliza la service account predeterminada del namespace.
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
Los datos de Secret en Kubernetes se almacenan codificados en Base64 de forma predeterminada. Esto es simplemente codificación, no cifrado, por lo que se necesitan medidas de seguridad adicionales. Desde Kubernetes 1.13, está disponible el cifrado de los datos de Secret almacenados en etcd.
</details>

8. ¿Qué método para configurar variables de entorno es el menos recomendado en Kubernetes?
   - A) Desde un ConfigMap
   - B) Desde un Secret
   - C) Codificadas directamente en la especificación del Pod
   - D) Desde la Downward API
   
<details>

<summary>Mostrar respuesta</summary>

**Respuesta: C) Codificadas directamente en la especificación del Pod**

**Explicación:**
Codificar variables de entorno directamente en la especificación del Pod viola el principio de separar la configuración del código y no se recomienda. Usar ConfigMaps o Secrets para gestionar variables de entorno permite cambiar la configuración sin modificar el código de la aplicación, y usar la Downward API permite proporcionar metadata del Pod o información de recursos como variables de entorno.
</details>

9. Cuando todos los containers de un Pod tienen resource requests y limits configurados, y las requests son iguales a los limits, ¿qué clase QoS (Quality of Service) se asigna?
   - A) Guaranteed
   - B) Burstable
   - C) BestEffort
   - D) Critical
   
<details>

<summary>Mostrar respuesta</summary>

**Respuesta: A) Guaranteed**

**Explicación:**
La clase QoS Guaranteed se asigna cuando todos los containers de un Pod tienen resource requests y limits configurados, y las requests son iguales a los limits. Los Pods de esta clase se terminan al final cuando los recursos son escasos. Burstable se asigna cuando solo algunos containers tienen requests y limits configurados, o cuando las requests y los limits difieren. BestEffort se asigna cuando no hay requests ni limits configurados.
</details>

10. ¿Cuándo se reflejan automáticamente en Pods los cambios en ConfigMaps o Secrets?
    - A) Siempre se reflejan automáticamente
    - B) Solo cuando se montan como un volume
    - C) Solo cuando se usan como variables de entorno
    - D) Nunca se reflejan automáticamente; se requiere reiniciar el Pod
    
<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Solo cuando se montan como un volume**

**Explicación:**
Cuando ConfigMaps o Secrets se montan como volumes, Kubernetes actualiza periódicamente los archivos montados (el valor predeterminado es aproximadamente 1 minuto). Sin embargo, cuando se usan como variables de entorno, se establecen solo una vez cuando se crea el Pod, por lo que el Pod debe reiniciarse para reflejar los cambios. Esto se debe a que las variables de entorno se establecen al iniciar el proceso.
</details>

## Preguntas prácticas

1. Explica cómo crear ConfigMaps y Secrets y montarlos en Pods como variables de entorno y volumes.

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

3. Crear un Pod que monte como variables de entorno y volumes:
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
              key: app.properties
              subPath: app.name
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
kubectl exec app-pod -- env | grep -E 'APP_NAME|DB_'
```

6. Verificar volumes montados:
```bash
kubectl exec app-pod -- ls -la /etc/config
kubectl exec app-pod -- ls -la /etc/secrets
```

7. Verificar el contenido de los archivos:
```bash
kubectl exec app-pod -- cat /etc/config/app.properties
kubectl exec app-pod -- cat /etc/secrets/db.user
```
</details>

2. Explica cómo configurar resource requests y limits para Pods y verificar la clase QoS.

<details>

<summary>Mostrar respuesta</summary>

**Respuesta:**

1. Crear Pods con diferentes clases QoS:

**Pod QoS Guaranteed**:
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

**Pod QoS Burstable**:
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

**Pod QoS BestEffort**:
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

2. Crear Pods:
```bash
kubectl apply -f guaranteed-pod.yaml
kubectl apply -f burstable-pod.yaml
kubectl apply -f besteffort-pod.yaml
```

3. Comprobar la clase QoS:
```bash
kubectl get pods guaranteed-pod -o jsonpath='{.status.qosClass}'
# Output: Guaranteed

kubectl get pods burstable-pod -o jsonpath='{.status.qosClass}'
# Output: Burstable

kubectl get pods besteffort-pod -o jsonpath='{.status.qosClass}'
# Output: BestEffort
```

4. Comprobar detalles del Pod:
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
  - **Guaranteed**: Todos los containers tienen resource requests y limits configurados, y las requests son iguales a los limits
  - **Burstable**: Al menos un container tiene resource requests configurados, pero no cumple las condiciones de Guaranteed
  - **BestEffort**: No hay resource requests ni limits configurados para ningún container
</details>

3. Explica cómo usar la Downward API para proporcionar metadata del Pod e información de recursos a los containers.

<details>

<summary>Mostrar respuesta</summary>

**Respuesta:**

1. Crear un Pod usando la Downward API:
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
          - path: "cpu-limit"
            resourceFieldRef:
              containerName: main
              resource: limits.cpu
```

2. Crear Pod:
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

**Campos disponibles mediante Downward API**:

**Campos disponibles como variables de entorno**:
  - `metadata.name` - Nombre del Pod
  - `metadata.namespace` - Namespace del Pod
  - `metadata.uid` - UID del Pod
  - `metadata.labels['<KEY>']` - Valor de label del Pod
  - `metadata.annotations['<KEY>']` - Valor de annotation del Pod
  - `status.podIP` - Dirección IP del Pod
  - `spec.nodeName` - Nombre del node donde se ejecuta el Pod
  - `spec.serviceAccountName` - Nombre de la service account del Pod
  - `status.hostIP` - Dirección IP del node donde se ejecuta el Pod

**Campos de recursos**:
  - `requests.cpu` - CPU request
  - `limits.cpu` - CPU limit
  - `requests.memory` - Memory request
  - `limits.memory` - Memory limit
</details>
