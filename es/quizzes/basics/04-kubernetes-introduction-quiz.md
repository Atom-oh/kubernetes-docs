# Cuestionario de introducción a Kubernetes

Este cuestionario evalúa su comprensión de los conceptos básicos, la arquitectura y las funciones de Kubernetes.

## Preguntas de opción múltiple

1. ¿Qué significa la palabra Kubernetes en griego?
   - A) Capitán
   - B) Timonel o piloto
   - C) Contenedor
   - D) Administrador

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Timonel o piloto**

**Explicación:**
En griego, Kubernetes significa «timonel» o «piloto», en alusión a su función de guiar aplicaciones en contenedores.

</details>

2. ¿Cuál de los siguientes no es un componente del plano de control de Kubernetes?
   - A) kube-apiserver
   - B) etcd
   - C) kubelet
   - D) kube-scheduler

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) kubelet**

**Explicación:**
kubelet es un agente que se ejecuta en cada nodo y no es un componente del plano de control.

</details>

3. ¿Cuál es la unidad desplegable más pequeña de Kubernetes?
   - A) Contenedor
   - B) Pod
   - C) Deployment
   - D) Service

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Pod**

**Explicación:**
Un Pod es la unidad desplegable más pequeña de Kubernetes.

</details>

4. ¿Cuál de los siguientes no es un tipo de Service de Kubernetes?
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

5. ¿Qué recurso administra el número de réplicas de un Pod?
   - A) Service
   - B) ConfigMap
   - C) ReplicaSet
   - D) Namespace

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) ReplicaSet**

**Explicación:**
ReplicaSet reconcilia el número deseado de Pods; no garantiza que todos estén en estado Ready si fallan las imágenes, la programación o las aplicaciones.

</details>

6. ¿Qué recurso de carga de trabajo está diseñado para aplicaciones con estado?
   - A) Deployment
   - B) StatefulSet
   - C) DaemonSet
   - D) Job

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) StatefulSet**

**Explicación:**
StatefulSet proporciona identificadores únicos y almacenamiento persistente para las aplicaciones con estado.

El almacenamiento de StatefulSet requiere PVC/controladores y no configura automáticamente la replicación ni las copias de seguridad de la base de datos.

</details>

7. ¿Qué recurso garantiza que un Pod se ejecute en todos los nodos?
   - A) Deployment
   - B) StatefulSet
   - C) DaemonSet
   - D) CronJob

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) DaemonSet**

**Explicación:**
DaemonSet reconcilia un Pod por cada nodo apto, sujeto a las restricciones de programación y admisión.

</details>

8. ¿Qué recurso ejecuta tareas periódicamente según un horario?
   - A) Job
   - B) CronJob
   - C) Deployment
   - D) ReplicaSet

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) CronJob**

**Explicación:**
CronJob ejecuta Jobs periódicamente según un horario especificado.

</details>

9. ¿Qué proporciona aislamiento de recursos dentro de un clúster?
   - A) Label
   - B) Annotation
   - C) Namespace
   - D) ConfigMap

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Namespace**

**Explicación:**
Namespace delimita los nombres y la organización de los recursos; RBAC, las cuotas y NetworkPolicy ofrecen controles adicionales de acceso, recursos y red.

</details>

10. ¿Cuál de las siguientes no es una diferencia clave entre EKS y Kubernetes autoadministrado?
    - A) Administración del plano de control
    - B) API central de Kubernetes
    - C) Configuración de alta disponibilidad
    - D) Aplicación de parches de seguridad

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) API central de Kubernetes**

**Explicación:**
Ambos usan la misma API estándar de Kubernetes.

</details>

## Preguntas de respuesta corta

11. ¿Qué almacén de clave-valor guarda los objetos de la API de Kubernetes y el estado del clúster, excluido el contenido de los volúmenes de las aplicaciones?

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: etcd**

</details>

12. ¿Qué componente selecciona un nodo para los Pods recién creados?

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: kube-scheduler**

</details>

13. ¿Qué tipo de volumen temporal se elimina al eliminar el Pod?

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: emptyDir**

</details>

14. ¿Qué objeto almacena datos de configuración en formato clave-valor?

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: ConfigMap**

</details>

15. ¿Qué objeto almacena información confidencial, como contraseñas?

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: Secret**

</details>

## Preguntas prácticas

16. Escriba un Deployment de nginx con 3 réplicas, puerto 80, solicitudes de CPU 100m/memoria 128Mi y límites de CPU 200m/memoria 256Mi.

<details>
<summary>Mostrar respuesta</summary>

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: nginx-deployment
  labels:
    app: nginx
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
        image: nginx:1.30.6
        ports:
        - containerPort: 80
        resources:
          requests:
            cpu: 100m
            memory: 128Mi
          limits:
            cpu: 200m
            memory: 256Mi
```

Añada a este Deployment comprobaciones de disponibilidad de la aplicación cuando corresponda.
</details>

17. Escriba un YAML de Service LoadBalancer.

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

Requiere una implementación de LoadBalancer y la configuración de red local o en la nube. Si la dirección externa permanece en Pending, normalmente necesita esa implementación; para aprender localmente, puede usar port-forward.
</details>

18. Guarde `DATABASE_URL` sin credenciales y `LOG_LEVEL` en un ConfigMap, y coloque las credenciales de la base de datos y `API_KEY` en un Secret independiente.

<details>
<summary>Mostrar respuesta</summary>

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: app-config
data:
  DATABASE_URL: mysql://mysql.default.svc.cluster.local:3306/db
  LOG_LEVEL: INFO
---
apiVersion: v1
kind: Secret
metadata:
  name: app-secrets
type: Opaque
stringData:
  DB_USERNAME: replace-from-protected-source
  DB_PASSWORD: replace-from-protected-source
  API_KEY: replace-from-protected-source
```

Los valores de Secret son marcadores de posición ilustrativos. Proporcione los valores reales mediante una entrada protegida o un administrador de secretos; no los confirme en el repositorio. `stringData` no sustituye al cifrado en reposo.
</details>

## Preguntas avanzadas

19. Escriba un Role y un RoleBinding de RBAC para conceder acceso de lectura a Pods.

<details>
<summary>Mostrar respuesta</summary>

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: pod-reader
  namespace: development
rules:
- apiGroups:
  - ''
  resources:
  - pods
  verbs:
  - get
  - watch
  - list
- apiGroups:
  - ''
  resources:
  - pods/log
  verbs:
  - get
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: read-pods
  namespace: development
subjects:
- kind: User
  name: jane
  apiGroup: rbac.authorization.k8s.io
roleRef:
  kind: Role
  name: pod-reader
  apiGroup: rbac.authorization.k8s.io
```

El namespace `development` y la identidad `jane`, autenticada externamente, deben existir. RoleBinding no crea una cuenta de usuario.
</details>

20. Escriba una NetworkPolicy que permita solo el tráfico de backend a la base de datos por el puerto 3306.

<details>
<summary>Mostrar respuesta</summary>

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: db-network-policy
  namespace: production
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

Requiere el namespace `production` y un plugin de red que aplique NetworkPolicy. Las reglas de permiso se acumulan, así que otras políticas pueden conceder accesos adicionales. Esta política no aísla el tráfico de salida.
</details>

---

[Volver a los materiales de estudio](../../basics/04-kubernetes-introduction.md) | [Siguiente cuestionario: arquitectura del clúster](../core/01-cluster-architecture-quiz.md)

## Referencias de verificación

- https://kubernetes.io/releases/version-skew-policy/
- https://kubernetes.io/docs/tasks/tools/install-kubectl-windows/
- https://kubernetes.io/docs/setup/production-environment/container-runtimes/
- https://kubernetes.io/docs/concepts/workloads/controllers/deployment/
- https://kubernetes.io/docs/concepts/workloads/controllers/statefulset/
- https://kubernetes.io/docs/concepts/storage/persistent-volumes/
- https://kubernetes.io/docs/reference/networking/virtual-ips/
- https://kubernetes.io/docs/concepts/services-networking/network-policies/
- https://kubernetes.io/blog/2025/11/11/ingress-nginx-retirement/
- https://coredns.io/plugins/kubernetes/
- https://github.com/fluent/fluent-bit/releases/tag/v5.1.3
- https://github.com/fluent/fluent-bit/blob/v5.1.3/conf/parsers.conf
- https://docs.aws.amazon.com/app-mesh/latest/userguide/what-is-app-mesh.html
- https://docs.aws.amazon.com/eks/latest/userguide/managed-node-groups.html
- https://docs.aws.amazon.com/eks/latest/userguide/kubernetes-versions-standard.html
- https://docs.aws.amazon.com/eks/latest/userguide/envelope-encryption.html
- https://docs.aws.amazon.com/eks/latest/userguide/lbc-helm.html
- https://eksctl.io/installation/
- https://minikube.sigs.k8s.io/docs/tutorials/multi_node/
- https://kind.sigs.k8s.io/docs/user/quick-start/
- https://github.com/kubernetes/dashboard/blob/master/README.md
- https://headlamp.dev/docs/latest/installation/in-cluster/
- https://github.com/kubernetes-sigs/headlamp/blob/main/charts/headlamp/values.yaml
