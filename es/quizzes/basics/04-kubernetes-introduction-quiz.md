# Kubernetes Introduction Quiz

Este cuestionario evalúa tu comprensión de los conceptos básicos, la arquitectura y las características de Kubernetes.

## Multiple Choice Questions

1. ¿Qué significa el nombre Kubernetes en griego?
   - A) Capitán
   - B) Timonel o piloto
   - C) Contenedor
   - D) Administrador

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Timonel o piloto**

**Explicación:**
Kubernetes significa 'timonel' o 'piloto' en griego, lo que simboliza su papel al guiar aplicaciones en contenedores.

</details>

2. ¿Cuál de los siguientes NO es un componente del control plane de Kubernetes?
   - A) kube-apiserver
   - B) etcd
   - C) kubelet
   - D) kube-scheduler

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) kubelet**

**Explicación:**
kubelet es un agente que se ejecuta en cada node y no es un componente del control plane.

</details>

3. ¿Cuál es la unidad desplegable más pequeña en Kubernetes?
   - A) Container
   - B) Pod
   - C) Deployment
   - D) Service

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Pod**

**Explicación:**
Un Pod es la unidad desplegable más pequeña en Kubernetes.

</details>

4. ¿Cuál de los siguientes NO es un tipo de Service de Kubernetes?
   - A) ClusterIP
   - B) NodePort
   - C) LoadBalancer
   - D) ExternalProxy

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: D) ExternalProxy**

**Explicación:**
Los tipos de Service incluyen ClusterIP, NodePort, LoadBalancer y ExternalName.

</details>

5. ¿Qué recurso administra el número de réplicas de Pod?
   - A) Service
   - B) ConfigMap
   - C) ReplicaSet
   - D) Namespace

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) ReplicaSet**

**Explicación:**
ReplicaSet garantiza que siempre se ejecute un número especificado de réplicas de Pod.

</details>

6. ¿Qué recurso de workload está diseñado para aplicaciones con estado?
   - A) Deployment
   - B) StatefulSet
   - C) DaemonSet
   - D) Job

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) StatefulSet**

**Explicación:**
StatefulSet proporciona identificadores únicos y almacenamiento persistente para aplicaciones con estado.

</details>

7. ¿Qué recurso garantiza que un Pod se ejecute en todos los nodes?
   - A) Deployment
   - B) StatefulSet
   - C) DaemonSet
   - D) CronJob

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) DaemonSet**

**Explicación:**
DaemonSet garantiza que una copia de un Pod se ejecute en todos los nodes (o en nodes específicos).

</details>

8. ¿Qué recurso ejecuta tareas periódicamente según una programación?
   - A) Job
   - B) CronJob
   - C) Deployment
   - D) ReplicaSet

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) CronJob**

**Explicación:**
CronJob ejecuta Jobs periódicamente según una programación especificada.

</details>

9. ¿Qué proporciona aislamiento de recursos dentro de un cluster?
   - A) Label
   - B) Annotation
   - C) Namespace
   - D) ConfigMap

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Namespace**

**Explicación:**
Namespace proporciona una forma de aislar grupos de recursos dentro de un único cluster.

</details>

10. ¿Cuál NO es una diferencia clave entre EKS y Kubernetes autogestionado?
    - A) Administración del control plane
    - B) Core Kubernetes API
    - C) Configuración de alta disponibilidad
    - D) Aplicación de parches de seguridad

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Core Kubernetes API**

**Explicación:**
Ambos usan la misma Kubernetes API estándar.

</details>

## Short Answer Questions

11. ¿Qué almacén key-value guarda todos los datos del cluster?

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: etcd**

</details>

12. ¿Qué componente selecciona un node para Pods recién creados?

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: kube-scheduler**

</details>

13. ¿Qué tipo de volumen temporal se elimina cuando se elimina el Pod?

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: emptyDir**

</details>

14. ¿Qué objeto almacena datos de configuración en formato key-value?

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: ConfigMap**

</details>

15. ¿Qué objeto almacena información confidencial como contraseñas?

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: Secret**

</details>

## Practical Questions

16. Escribe un YAML de Deployment para nginx con 3 réplicas.

<details>
<summary>Mostrar respuesta</summary>

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: nginx-deployment
spec:
  replicas: 3
  selector:
    matchLabels:
      app: nginx
  template:
    metadata:
      labels:
        app: nginx
    spec:
      containers:
      - name: nginx
        image: nginx:1.21
        ports:
        - containerPort: 80
```

</details>

17. Escribe un YAML de Service LoadBalancer.

<details>
<summary>Mostrar respuesta</summary>

```yaml
apiVersion: v1
kind: Service
metadata:
  name: nginx-service
spec:
  type: LoadBalancer
  ports:
  - port: 80
    targetPort: 80
  selector:
    app: nginx
```

</details>

18. Escribe un YAML de ConfigMap con DATABASE_URL y LOG_LEVEL.

<details>
<summary>Mostrar respuesta</summary>

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: app-config
data:
  DATABASE_URL: "mysql://localhost:3306/db"
  LOG_LEVEL: "INFO"
```

</details>

## Advanced Questions

19. Escribe un Role/RoleBinding de RBAC para otorgar acceso de lectura a Pod.

<details>
<summary>Mostrar respuesta</summary>

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  namespace: development
  name: pod-reader
rules:
- apiGroups: [""]
  resources: ["pods", "pods/log"]
  verbs: ["get", "watch", "list"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: read-pods
  namespace: development
subjects:
- kind: User
  name: jane
roleRef:
  kind: Role
  name: pod-reader
  apiGroup: rbac.authorization.k8s.io
```

</details>

20. Escribe una NetworkPolicy que permita solo el tráfico de backend a database en el puerto 3306.

<details>
<summary>Mostrar respuesta</summary>

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: db-network-policy
spec:
  podSelector:
    matchLabels:
      role: database
  policyTypes:
  - Ingress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          role: backend
    ports:
    - protocol: TCP
      port: 3306
```

</details>

---

[Volver a los materiales de estudio](../../basics/04-kubernetes-introduction.md) | [Siguiente cuestionario: Arquitectura del cluster](../core/01-cluster-architecture-quiz.md)
