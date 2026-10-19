# Introducción a Kubernetes

> **Versiones compatibles**: Kubernetes upstream 1.35–1.37; soporte estándar de EKS 1.34–1.37 (al 12 de octubre de 2026)
> **Última actualización**: 16 de octubre de 2026

El proyecto Kubernetes mantiene ramas de lanzamiento para las tres versiones menores más recientes (1.35–1.37). Kubernetes upstream 1.34 está en modo de mantenimiento y sigue recibiendo versiones de parches hasta el fin de su ciclo de vida, el **27 de octubre de 2026**; esa fecha es independiente de la fecha en que finaliza el soporte de AWS para EKS. Consulta el [ciclo de vida de AWS EKS](https://docs.aws.amazon.com/eks/latest/userguide/kubernetes-versions.html) para conocer la cobertura y las fechas de EKS.

Kubernetes (K8s) es una plataforma de orquestación de contenedores de código abierto que automatiza el despliegue, el escalado y la administración de aplicaciones en contenedores. Este documento explica los conceptos básicos, la arquitectura, los componentes principales y las funciones de Kubernetes.

Estos ejemplos de aprendizaje independientes se revisaron de forma estática frente a esquemas y documentación oficial. No son configuraciones de producción validadas mediante un despliegue. Verifica las imágenes personalizadas, los nombres y las etiquetas, TLS, IAM/RBAC, CNI y los requisitos previos de almacenamiento en el entorno de destino, y reemplaza los marcadores de posición.

## Configuración del entorno de laboratorio

Para seguir los ejemplos de este documento, necesitarás las siguientes herramientas y el siguiente entorno:

### Herramientas necesarias

* **kubectl**: herramienta de línea de comandos para interactuar con clústeres de Kubernetes
* **Controlador de clúster local**: un motor de contenedores o controlador de máquinas virtuales compatible con minikube/kind; los nodos de Kubernetes usan un entorno de ejecución CRI v1.
* **minikube** o **kind**: clúster local de Kubernetes (para desarrollo y aprendizaje)

### Métodos de instalación

**Instalación de kubectl**:

```bash
# macOS: use a kubectl version within one minor of the API server.
brew install kubectl
```

```bash
# Linux: select an explicit compatible version and architecture.
set -euo pipefail
: "${KUBECTL_VERSION:?Set a cluster-compatible version, e.g. v1.37.1}"
case "$(uname -m)" in
  x86_64) KUBECTL_ARCH=amd64 ;;
  aarch64|arm64) KUBECTL_ARCH=arm64 ;;
  *) echo "Choose a supported kubectl architecture" >&2; exit 1 ;;
esac
curl --fail --location --output kubectl "https://dl.k8s.io/release/$KUBECTL_VERSION/bin/linux/$KUBECTL_ARCH/kubectl"
curl --fail --location --output kubectl.sha256 "https://dl.k8s.io/release/$KUBECTL_VERSION/bin/linux/$KUBECTL_ARCH/kubectl.sha256"
echo "$(cat kubectl.sha256)  kubectl" | sha256sum --check
sudo install -m 0755 kubectl /usr/local/bin/kubectl
```

```powershell
$ErrorActionPreference = "Stop"
$KubectlVersion = Read-Host "Cluster-compatible kubectl version (vX.Y.Z)"
$KubectlArch = Read-Host "Architecture (amd64 or arm64)"
if ($KubectlVersion -notmatch '^v\d+\.\d+\.\d+$' -or $KubectlArch -notin @('amd64','arm64')) { throw "Invalid version/architecture" }
$BaseUrl = "https://dl.k8s.io/release/$KubectlVersion/bin/windows/$KubectlArch"
Invoke-WebRequest "$BaseUrl/kubectl.exe" -OutFile kubectl.exe
Invoke-WebRequest "$BaseUrl/kubectl.exe.sha256" -OutFile kubectl.exe.sha256
if ((Get-FileHash kubectl.exe -Algorithm SHA256).Hash -ne (Get-Content kubectl.exe.sha256).Trim()) { throw "Checksum mismatch" }
# Move the verified binary to a directory included in PATH.
```

**Instalación de minikube**:

Usa la guía oficial de inicio de minikube para seleccionar el binario, la suma de comprobación y el controlador correspondientes a tu sistema operativo y arquitectura. Sigue las instrucciones de Linux y Windows en sus respectivos shells y agrega el binario verificado a PATH. Para macOS:

```bash
brew install minikube
minikube version
```

### Inicio de un clúster local

```bash
minikube start
```

## Tabla de contenido

* [¿Qué es Kubernetes?](04-kubernetes-introduction.md#what-is-kubernetes)
* [Historia de Kubernetes](04-kubernetes-introduction.md#history-of-kubernetes)
* [Arquitectura de Kubernetes](04-kubernetes-introduction.md#kubernetes-architecture)
* [Componentes principales de Kubernetes](04-kubernetes-introduction.md#kubernetes-main-components)
* [Objetos básicos de Kubernetes](04-kubernetes-introduction.md#kubernetes-basic-objects)
* [Recursos de cargas de trabajo de Kubernetes](04-kubernetes-introduction.md#kubernetes-workload-resources)
* [Servicios y redes de Kubernetes](04-kubernetes-introduction.md#kubernetes-services-and-networking)
* [Almacenamiento de Kubernetes](04-kubernetes-introduction.md#kubernetes-storage)
* [Configuración y seguridad de Kubernetes](04-kubernetes-introduction.md#kubernetes-configuration-and-security)
* [Kubernetes frente a Amazon EKS](04-kubernetes-introduction.md#kubernetes-vs-amazon-eks)
* [Primeros pasos con Kubernetes](04-kubernetes-introduction.md#getting-started-with-kubernetes)

## ¿Qué es Kubernetes?

Kubernetes significa «timonel» o «piloto» en griego, y es un sistema de código abierto que automatiza el despliegue, el escalado y el funcionamiento de aplicaciones en contenedores. Se inspiró en el sistema interno Borg de Google y se publicó como código abierto en 2014.

### Funciones principales de Kubernetes

1. **Detección de servicios y balanceo de carga**: exponer contenedores externamente y distribuir el tráfico
2. **Orquestación del almacenamiento**: montar automáticamente sistemas de almacenamiento locales o en la nube
3. **Actualizaciones progresivas y reversiones**: actualizar aplicaciones gradualmente y admitir reversiones iniciadas por un operador o una herramienta; un Deployment fallido no se revierte automáticamente.
4. **Empaquetado automático de cargas**: ubicar contenedores en nodos según sus requisitos de recursos
5. **Autorreparación**: reiniciar contenedores que hayan fallado y reemplazar los que no respondan
6. **Administración de Secrets y configuración**: almacenar información confidencial y actualizar la configuración
7. **Escalado horizontal**: escalar aplicaciones mediante comandos sencillos o una interfaz de usuario
8. **Ejecución por lotes**: administrar cargas de trabajo por lotes y de CI

### Problemas que resuelve Kubernetes

* **Orquestación de contenedores**: administrar de forma eficiente cientos o miles de contenedores
* **Alta disponibilidad**: admite un diseño de aplicaciones resiliente mediante réplicas, ubicación, comprobaciones y capacidad
* **Escalabilidad**: escalado automático en función del aumento del tráfico
* **Recuperación**: reconcilia las cargas de trabajo que hayan fallado; la recuperación ante desastres también requiere copias de seguridad probadas y planes de restauración
* **Eficiencia de los recursos**: utilizar los recursos de hardware de forma eficiente
* **Configuración declarativa**: administrar la infraestructura como código
* **Multinube y nube híbrida**: despliegue y administración uniformes en diversos entornos

## Historia de Kubernetes

### Antecedentes

* **2003-2013**: Google utilizó internamente un sistema de orquestación de contenedores llamado Borg
* **Junio de 2014**: Google publicó Kubernetes como código abierto
* **Julio de 2015**: se publicó Kubernetes 1.0 y se donó a la Cloud Native Computing Foundation (CNCF)
* **2016-2017**: los principales proveedores de nube lanzaron servicios administrados de Kubernetes
* **2018 en adelante**: se consolidó como el estándar de facto para la orquestación de contenedores

### Origen del nombre

Kubernetes (κυβερνήτης) significa «timonel» o «piloto» en griego. Esto simboliza su función de guiar las aplicaciones en contenedores. Se usa la abreviatura K8s porque hay 8 caracteres entre la «K» y la «s».

### Significado del logotipo

El logotipo de Kubernetes representa un timón (la rueda de dirección de un barco) con 7 radios, que simboliza la función de Kubernetes de guiar el rumbo de las aplicaciones en contenedores.

## Arquitectura de Kubernetes

Kubernetes sigue una arquitectura de nodo principal. Los nodos principales (plano de control) administran el clúster, y los nodos de trabajo ejecutan las cargas de trabajo reales de las aplicaciones.

### Componentes del plano de control (principal)

![Plano de control de Kubernetes: las solicitudes de kubectl pasan por kube-apiserver hasta etcd, mientras kube-scheduler, kube-controller-manager y cloud-controller-manager observan y reconcilian mediante el servidor de API.](../.gitbook/assets/en-basics-04-kubernetes-introduction-0.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-basics-04-kubernetes-introduction-0.html)

1. **kube-apiserver**: interfaz del plano de control que expone la API de Kubernetes
2. **etcd**: almacén de clave-valor coherente y de alta disponibilidad para los objetos de la API de Kubernetes y el estado del clúster (no para el contenido de los volúmenes de las aplicaciones)
3. **kube-scheduler**: componente que asigna pods a nodos
4. **kube-controller-manager**: componente que ejecuta procesos de controlador
   * Controlador de nodos: notifica y responde cuando los nodos dejan de funcionar
   * Replication Controller: mantiene la cantidad correcta de réplicas de pods
   * Controlador de EndpointSlice: mantiene los registros de endpoints de Service (Endpoints, el recurso heredado, está obsoleto)
   * El controlador de ServiceAccount crea cuentas predeterminadas; los tokens proyectados de Pod usan TokenRequest y la rotación de kubelet
5. **cloud-controller-manager**: componente que contiene la lógica de control específica de la nube
   * Controlador de nodos: comprueba con el proveedor de nube si se ha eliminado un nodo
   * Controlador de rutas: configura rutas en la infraestructura de la nube
   * Controlador de Service: crea, actualiza y elimina balanceadores de carga del proveedor de nube

### Componentes de los nodos

![Nodo de trabajo de Kubernetes: kubelet recibe instrucciones del plano de control y controla el entorno de ejecución CRI (containerd/CRI-O o Docker Engine mediante un adaptador externo), que ejecuta los contenedores del Pod, mientras kube-proxy mantiene sus reglas de red.](../.gitbook/assets/en-basics-04-kubernetes-introduction-1.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-basics-04-kubernetes-introduction-1.html)

1. **kubelet**: agente que se ejecuta en cada nodo y garantiza que los contenedores de los pods estén en funcionamiento
2. **kube-proxy**: proxy de red que se ejecuta en cada nodo e implementa el concepto de Kubernetes Service
3. **Entorno de ejecución de contenedores**: software que implementa CRI v1, como containerd o CRI-O; Docker Engine requiere un adaptador CRI independiente

### Arquitectura completa

![Clúster completo de Kubernetes: los clientes de kubectl acceden a kube-apiserver, que coordina etcd, kube-scheduler, kube-controller-manager y cloud-controller-manager, y controla kubelet, el entorno de ejecución de contenedores y kube-proxy en dos nodos de trabajo.](../.gitbook/assets/en-basics-04-kubernetes-introduction-2.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-basics-04-kubernetes-introduction-2.html)

## Componentes principales de Kubernetes

### Servidor de API (kube-apiserver)

El servidor de API es la interfaz del plano de control que expone la API de Kubernetes. Las solicitudes a la API de Kubernetes pasan por él; el tráfico de las aplicaciones y la E/S de almacenamiento no pasan por el servidor de API.

**Funciones principales**:

* Proporciona la API REST
* Autenticación y autorización
* Validación de solicitudes
* Comunicación con etcd
* Escalabilidad horizontal

### etcd

etcd es un almacén de clave-valor coherente y de alta disponibilidad que guarda los objetos de la API de Kubernetes y el estado del clúster (no el contenido de los volúmenes de las aplicaciones).

**Funciones principales**:

* Sistema distribuido
* Coherencia sólida
* Alta disponibilidad
* Almacenamiento seguro de datos
* Función de observación para supervisar cambios

### Scheduler (kube-scheduler)

El scheduler es un componente del plano de control que selecciona los nodos donde se ejecutarán los pods recién creados.

**Proceso de planificación**:

1. **Filtrado**: identificar los nodos que pueden ejecutar el pod
2. **Puntuación**: asignar puntuaciones a los nodos adecuados
3. **Vinculación**: asignar el pod al nodo óptimo

**Consideraciones**:

* Requisitos de recursos (CPU, memoria)
* Restricciones de hardware, software y políticas
* Especificaciones de afinidad/anti-afinidad
* Localidad de los datos
* Interferencia entre cargas de trabajo

### Controller Manager (kube-controller-manager)

El controller manager es un componente del plano de control que ejecuta varios procesos de controlador.

**Controladores principales**:

* **Node Controller**: supervisa el estado de los nodos y responde a sus cambios
* **Replication Controller**: mantiene la cantidad de réplicas de pods
* **Controlador de EndpointSlice**: mantiene los registros de endpoints de Service (Endpoints, el recurso heredado, está obsoleto)
* **Controlador de ServiceAccount**: crea cuentas predeterminadas; los tokens modernos de Pod se solicitan mediante TokenRequest y kubelet los rota
* **Job Controller**: administra tareas puntuales
* **CronJob Controller**: administra tareas programadas
* **DaemonSet Controller**: reconcilia un Pod en cada nodo que cumpla los requisitos
* **StatefulSet Controller**: administra aplicaciones con estado
* **PV Controller**: administra los volúmenes persistentes

### Cloud Controller Manager (cloud-controller-manager)

El cloud controller manager contiene la lógica de control específica de la nube. Los controladores complementarios/controladores CSI y los complementos de kubelet/nodo se encargan del aprovisionamiento, la conexión y el montaje del almacenamiento; esto no corresponde a un controlador de volúmenes de CCM.

**Controladores principales**:

* **Node Controller**: comprueba el estado de los nodos mediante la API del proveedor de nube
* **Route Controller**: configura rutas en el entorno de nube
* **Service Controller**: crea, actualiza y elimina balanceadores de carga en la nube

### kubelet

kubelet es un agente que se ejecuta en cada nodo y garantiza que los contenedores de los pods estén en funcionamiento.

**Funciones principales**:

* Ejecutar contenedores según PodSpec
* Informar del estado de los contenedores
* Realizar comprobaciones del estado de los contenedores
* Administrar el ciclo de vida de los contenedores
* Informar del estado del nodo

### kube-proxy

kube-proxy es un proxy de red que se ejecuta en cada nodo e implementa el concepto de Kubernetes Service.

**Funciones principales**:

* Mantener reglas de red para las IP y los puertos de Service
* Reenviar conexiones
* Implementar el balanceo de carga

**Modos de funcionamiento**:

* **Modo nftables**: estable desde la versión 1.33; verifica la compatibilidad del kernel y del complemento de red
* **Modo iptables**: implementación NAT que usa iptables de Linux (predeterminado)
* **Modo IPVS**: obsoleto desde la versión 1.35; planifica la migración. El antiguo modo de espacio de usuario se eliminó.

## Objetos básicos de Kubernetes

Los objetos de Kubernetes son entidades persistentes que representan el estado del clúster. Describen las aplicaciones en ejecución, los recursos disponibles, las políticas, etc., del clúster.

### Pod

Un Pod es la unidad desplegable más pequeña de Kubernetes y representa un grupo de uno o más contenedores. Los contenedores de un Pod comparten la red y pueden compartir volúmenes montados explícitamente; se ejecutan en el mismo nodo. No comparten automáticamente sus sistemas de archivos raíz.

**Funciones principales**:

* Tiene una dirección IP única
* Espacio de nombres de red compartido (misma IP y espacio de puertos)
* Espacio de nombres IPC compartido
* Nombre de host compartido
* Posibilidad de comunicarse entre contenedores mediante localhost

**Ejemplo de Pod**:

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: nginx-pod
  labels:
    app: nginx
spec:
  containers:
  - name: nginx
    image: nginx:1.30.6
    ports:
    - containerPort: 80
    volumeMounts:
    - name: logs
      mountPath: /var/log/nginx
  - name: log-sidecar
    image: busybox:1.38.0
    command:
    - /bin/sh
    - -c
    - until [ -f /var/log/nginx/access.log ]; do sleep 1; done; tail -F /var/log/nginx/access.log
    volumeMounts:
    - name: logs
      mountPath: /var/log/nginx
      readOnly: true
  volumes:
  - name: logs
    emptyDir: {}
```

### Namespace

Los Namespace permiten aislar grupos de recursos dentro de un único clúster. Esto ayuda a organizar equipos y proyectos; por sí solos, los Namespace no imponen el aislamiento de red ni de autorización.

**Namespace predeterminados**:

* **default**: Namespace predeterminado
* **kube-system**: Namespace para los objetos creados por el sistema Kubernetes
* **kube-public**: Namespace usado convencionalmente para información pública; el acceso real a los objetos sigue dependiendo de RBAC
* **kube-node-lease**: Namespace para los latidos de los nodos

**Ejemplo de Namespace**:

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: development
```

### Etiquetas y selectores

Las etiquetas son pares clave-valor asociados a los objetos que se usan para identificarlos y seleccionarlos. Los selectores permiten filtrar objetos según sus etiquetas.

**Ejemplo de etiquetas**:

```yaml
metadata:
  labels:
    app: nginx
    environment: production
    tier: frontend
```

**Tipos de selectores**:

* **Basados en igualdad**: `=`, `!=`
* **Basados en conjuntos**: `in`, `notin`, `exists`

**Ejemplo de selector**:

```yaml
selector:
  matchLabels:
    app: nginx
  matchExpressions:
    - {key: tier, operator: In, values: [frontend, middleware]}
    - {key: environment, operator: NotIn, values: [dev]}
```

### Anotaciones

Las anotaciones son pares clave-valor que almacenan metadatos no identificativos sobre los objetos. Son útiles para guardar información que utilizan herramientas o bibliotecas.

**Ejemplo de anotaciones**:

```yaml
metadata:
  annotations:
    example.com/created-by: "admin"
    example.com/last-modified: "2023-07-01T12:00:00Z"
    prometheus.io/scrape: "true"
    prometheus.io/port: "9090"
```

### Nodo

Un nodo es una máquina de trabajo de un clúster de Kubernetes que ejecuta pods. Puede ser una máquina física o virtual.

**Estado del nodo**:

* **Direcciones**: nombre de host, IP interna, IP externa
* **Condiciones**: Ready, DiskPressure, MemoryPressure, PIDPressure, NetworkUnavailable
* **Capacidad**: CPU, memoria, cantidad máxima de pods
* **Información**: versión del kernel, versión del entorno de ejecución de contenedores, versión de kubelet

**Estado ilustrativo del nodo (informado por el nodo/controladores, no es un manifiesto para aprovisionar nodos)**:

```yaml
apiVersion: v1
kind: Node
metadata:
  name: worker-1
  labels:
    kubernetes.io/hostname: worker-1
    node-role.kubernetes.io/worker: ""
    topology.kubernetes.io/zone: us-east-1a
status:
  capacity:
    cpu: "4"
    memory: 8Gi
    pods: "110"
  conditions:
    - type: Ready
      status: "True"
  # ...
```

## Recursos de cargas de trabajo de Kubernetes

Los recursos de cargas de trabajo son objetos que se usan para administrar y ejecutar pods. Administran la creación, el escalado, las actualizaciones y la terminación de pods.

### ReplicaSet

Un ReplicaSet reconcilia la cantidad deseada de objetos Pod; la disponibilidad también depende de la capacidad, de una configuración válida y de la aplicación. Si los pods fallan o se eliminan, el ReplicaSet crea automáticamente pods de reemplazo.

**Funciones principales**:

* Mantener la cantidad especificada de réplicas de pods
* Definir la plantilla del pod
* Identificar pods mediante selectores

**Ejemplo de ReplicaSet**:

```yaml
apiVersion: apps/v1
kind: ReplicaSet
metadata:
  name: nginx-replicaset
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
```

### Deployment

Un Deployment añade otra capa de abstracción sobre ReplicaSets y ofrece actualizaciones declarativas para las aplicaciones. Los Deployment ofrecen funciones como actualizaciones progresivas, reversiones y escalado.

**Funciones principales**:

* Actualizaciones declarativas de aplicaciones
* Actualizaciones progresivas y reversiones
* Administración del historial de Deployment
* Escalado

**Ejemplo de Deployment**:

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
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0
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
        livenessProbe:
          httpGet:
            path: /
            port: 80
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /
            port: 80
          initialDelaySeconds: 5
          periodSeconds: 5
```

El ejemplo de MySQL es una única instancia persistente. StatefulSet no configura la replicación de la base de datos, la conmutación por error ni las copias de seguridad. Primero proporciona mysql-secret/password y reemplaza el marcador de posición de StorageClass. Aumentar solo el número de réplicas crea bases de datos independientes; la alta disponibilidad requiere una configuración probada de operador de base de datos/replicación.

### StatefulSet

Un StatefulSet es un recurso de carga de trabajo para aplicaciones que necesitan mantener su estado. Asigna identificadores únicos a cada pod y proporciona identificadores de red estables y almacenamiento persistente.

**Funciones principales**:

* Identificadores de red estables y únicos
* Almacenamiento estable y persistente
* Despliegue y escalado secuenciales
* Actualizaciones secuenciales

**Ejemplo de StatefulSet**:

```yaml
apiVersion: v1
kind: Service
metadata:
  name: mysql
spec:
  clusterIP: None
  selector:
    app: mysql
  ports:
  - name: mysql
    port: 3306
    targetPort: 3306
---
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: mysql
spec:
  selector:
    matchLabels:
      app: mysql
  serviceName: mysql
  replicas: 1
  template:
    metadata:
      labels:
        app: mysql
        role: db
    spec:
      containers:
      - name: mysql
        image: mysql:8.4
        env:
        - name: MYSQL_ROOT_PASSWORD
          valueFrom:
            secretKeyRef:
              name: mysql-secret
              key: password
        ports:
        - containerPort: 3306
          name: mysql
        volumeMounts:
        - name: data
          mountPath: /var/lib/mysql
        readinessProbe:
          tcpSocket:
            port: 3306
          initialDelaySeconds: 10
          periodSeconds: 5
  volumeClaimTemplates:
  - metadata:
      name: data
    spec:
      accessModes:
      - ReadWriteOnce
      storageClassName: replace-with-storage-class
      resources:
        requests:
          storage: 10Gi
```

El ejemplo de Fluent Bit para Linux envía los registros CRI a stdout con fines demostrativos. Excluye sus propios registros para evitar un bucle de retroalimentación y persiste su base de datos de posiciones por separado. No lo despliegues junto con otro recopilador que vuelva a publicar en stdout los mismos registros. En producción se necesita un destino externo y hay que revisar las rutas del host, los permisos y las excepciones de PSS.

### DaemonSet

Un DaemonSet crea un Pod en cada nodo que cumpla los requisitos; los selectores de nodos, los taints, la capacidad y las políticas de admisión siguen aplicándose. Al agregar nodos al clúster, se agregan pods automáticamente; al eliminar nodos, también se eliminan los pods.

**Casos de uso principales**:

* Recopiladores de registros (Fluentd, Logstash)
* Agentes de supervisión (Prometheus Node Exporter)
* Complementos de red (Calico, Cilium)
* Daemons de almacenamiento (Ceph)

**Ejemplo de DaemonSet**:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: intro-log-agent-config
  namespace: kube-system
data:
  fluent-bit.conf: |
    [SERVICE]
        Flush 5
        Parsers_File /fluent-bit/etc/parsers.conf
    [INPUT]
        Name tail
        Path /var/log/containers/*.log
        Exclude_Path /var/log/containers/intro-log-agent-*_kube-system_fluent-bit-*.log
        Parser cri
        Tag kube.*
        DB /var/lib/fluent-bit/tail.db
        Mem_Buf_Limit 5MB
        Skip_Long_Lines On
    [OUTPUT]
        Name stdout
        Match *
---
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: intro-log-agent
  namespace: kube-system
spec:
  selector:
    matchLabels:
      app: intro-log-agent
  template:
    metadata:
      labels:
        app: intro-log-agent
    spec:
      automountServiceAccountToken: false
      tolerations:
      - key: node-role.kubernetes.io/control-plane
        operator: Exists
        effect: NoSchedule
      containers:
      - name: fluent-bit
        image: cr.fluentbit.io/fluent/fluent-bit:5.1.3
        securityContext:
          runAsUser: 0
          allowPrivilegeEscalation: false
          readOnlyRootFilesystem: true
          capabilities:
            drop: [ALL]
        args:
        - -c
        - /fluent-bit/custom/fluent-bit.conf
        resources:
          requests:
            cpu: 100m
            memory: 100Mi
          limits:
            memory: 200Mi
        volumeMounts:
        - name: varlog
          mountPath: /var/log
          readOnly: true
        - name: config
          mountPath: /fluent-bit/custom
          readOnly: true
        - name: state
          mountPath: /var/lib/fluent-bit
      volumes:
      - name: varlog
        hostPath:
          path: /var/log
          type: Directory
      - name: config
        configMap:
          name: intro-log-agent-config
      - name: state
        hostPath:
          path: /var/lib/intro-log-agent
          type: DirectoryOrCreate
      nodeSelector:
        kubernetes.io/os: linux
```

### Job

Un Job crea uno o más pods y continúa ejecutándose hasta que termina correctamente la cantidad especificada de pods. Es adecuado para tareas de procesamiento por lotes.

**Funciones principales**:

* Ejecución de tareas puntuales
* Ejecución paralela de tareas
* Seguimiento de las finalizaciones correctas; los límites de fallos y plazos aún pueden hacer que falle el Job
* Reintento en caso de fallo

**Ejemplo de Job**:

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: pi-calculator
spec:
  completions: 5
  parallelism: 2
  backoffLimit: 3
  template:
    spec:
      containers:
      - name: pi
        image: perl
        command: ["perl", "-Mbignum=bpi", "-wle", "print bpi(2000)"]
      restartPolicy: Never
```

Los Job pueden fallar debido a los límites de reintentos o plazos, y es posible que vuelvan a ejecutar el mismo trabajo; por eso, las tareas deben ser idempotentes. La programación de CronJob no ofrece ejecución exactamente una vez; Forbid solo controla la superposición de Job de ese CronJob.

### CronJob

Un CronJob ejecuta Jobs periódicamente según una programación especificada. Funciona de manera similar a los trabajos cron de Linux.

**Funciones principales**:

* Ejecución de tareas según una programación
* Compatibilidad con expresiones cron
* Configuración de políticas de concurrencia
* Límites del historial

**Ejemplo de CronJob**:

```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: database-backup
spec:
  timeZone: Etc/UTC
  schedule: "0 2 * * *"  # Run at 02:00 daily
  concurrencyPolicy: Forbid
  successfulJobsHistoryLimit: 3
  failedJobsHistoryLimit: 1
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: backup
            image: database-backup:v1
            env:
            - name: DB_HOST
              value: "db.example.com"
          restartPolicy: OnFailure
```

## Servicios y redes de Kubernetes

El modelo de red de Kubernetes parte de la premisa de que un CNI compatible proporciona la red de los Pod; la capacidad de enrutar depende de NetworkPolicy, los firewalls y la topología. Los Service proporcionan endpoints estables para conjuntos de pods.

### Service

Un Service proporciona un único endpoint y balanceo de carga para un conjunto de pods. Como los pods se crean y eliminan dinámicamente, los Service proporcionan direcciones de red estables a pesar de estos cambios.

**Tipos de Service**:

* **ClusterIP**: Service accesible solo dentro del clúster (predeterminado)
* **NodePort**: accesible externamente mediante la IP de cada nodo y un puerto específico
* **LoadBalancer**: accesible externamente mediante el balanceador de carga del proveedor de nube
* **ExternalName**: crea un registro CNAME para un servicio externo

![El diagrama muestra el acceso externo mediante los Service NodePort y LoadBalancer; también son posibles otros puntos de entrada, como Ingress/Gateway, ClusterIP permanece interno y los tres tipos de Service balancean las solicitudes al puerto 80 hacia los mismos pods (Pod 1, 2, 3).](../.gitbook/assets/en-basics-04-kubernetes-introduction-3.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-basics-04-kubernetes-introduction-3.html)

**Ejemplo de Service**:

```yaml
apiVersion: v1
kind: Service
metadata:
  name: nginx-service
spec:
  selector:
    app: nginx
  ports:
  - port: 80
    targetPort: 80
  type: ClusterIP
```

**Ejemplo de Service NodePort**:

```yaml
apiVersion: v1
kind: Service
metadata:
  name: nginx-nodeport
spec:
  selector:
    app: nginx
  ports:
  - port: 80
    targetPort: 80
    nodePort: 30080
  type: NodePort
```

Este ejemplo de AWS requiere AWS Load Balancer Controller y sus requisitos previos de IAM y red. EKS Auto Mode utiliza un loadBalancerClass distinto; los clústeres locales necesitan su propia implementación de LoadBalancer.

**Ejemplo de Service LoadBalancer**:

```yaml
apiVersion: v1
kind: Service
metadata:
  name: nginx-lb
  annotations:
    service.beta.kubernetes.io/aws-load-balancer-scheme: internet-facing
    service.beta.kubernetes.io/aws-load-balancer-nlb-target-type: ip
spec:
  selector:
    app: nginx
  ports:
  - port: 80
    targetPort: 80
  type: LoadBalancer
  loadBalancerClass: service.k8s.aws/nlb
```

Este ejemplo requiere que Traefik esté instalado, su traefik IngressClass, los Service app1/app2 y el Secret TLS. Las rutas /app1 y /app2 se conservan y los backends deben servirlas. Un recurso Ingress no instala un controlador.

### Ingress

Un Ingress es un objeto de API que administra el enrutamiento HTTP y HTTPS desde fuera del clúster hacia los servicios internos. Ingress ofrece balanceo de carga, terminación SSL, alojamiento virtual basado en nombres, etc.

**Controladores de Ingress**:

* **ingress-nginx (retirado en marzo de 2026)**: controlador comunitario histórico; para instalaciones nuevas, elige un controlador con mantenimiento activo. F5 NGINX Ingress Controller es un proyecto independiente.
* **AWS Load Balancer Controller**: controlador de Ingress basado en Application Load Balancer de AWS
* **Traefik**: enrutador perimetral nativo de la nube
* **Istio Ingress**: Ingress basado en una malla de servicios

**Ejemplo de Ingress**:

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: example-ingress
spec:
  ingressClassName: traefik
  rules:
  - host: example.com
    http:
      paths:
      - path: /app1
        pathType: Prefix
        backend:
          service:
            name: app1-service
            port:
              number: 80
      - path: /app2
        pathType: Prefix
        backend:
          service:
            name: app2-service
            port:
              number: 80
  tls:
  - hosts:
    - example.com
    secretName: example-tls
```

### NetworkPolicy

NetworkPolicy permite controlar la comunicación entre pods. De forma predeterminada, todos los pods pueden comunicarse entre sí, pero puedes restringirlo mediante políticas de red.&#x20;

![Las solicitudes externas pasan por los pods frontend, API y base de datos del Namespace predeterminado; una NetworkPolicy db-network-policy protege los pods con role=db, y Prometheus, en el Namespace monitoring, recopila métricas de los tres niveles.](../.gitbook/assets/en-basics-04-kubernetes-introduction-4.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-basics-04-kubernetes-introduction-4.html)

**Funciones principales**:

* Controlar la comunicación entre pods
* Controlar la comunicación entre Namespace
* Controlar el tráfico de entrada y de salida
* Filtrar por puerto y protocolo

**Ejemplo de NetworkPolicy**:

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: db-network-policy
  namespace: default
spec:
  podSelector:
    matchLabels:
      role: db
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          role: api
    ports:
    - protocol: TCP
      port: 3306
  - from:
    - namespaceSelector:
        matchLabels:
          kubernetes.io/metadata.name: monitoring
      podSelector:
        matchLabels:
          app: prometheus
    ports:
    - protocol: TCP
      port: 9104
  egress:
  - to:
    - namespaceSelector:
        matchLabels:
          kubernetes.io/metadata.name: kube-system
      podSelector:
        matchLabels:
          k8s-app: kube-dns
    ports:
    - protocol: UDP
      port: 53
    - protocol: TCP
      port: 53
```

Las reglas de autorización de NetworkPolicy son aditivas. La política permite el acceso desde role=api al puerto 3306 de la base de datos y desde app=prometheus en monitoring a un exportador de base de datos instalado por separado en el puerto 9104. No hace que la base de datos se conecte a Prometheus en el puerto 9090. Adapta los selectores de salida de DNS a la configuración real de DNS del clúster/DNS NodeLocal.

### DNS

Las distribuciones de Kubernetes suelen desplegar CoreDNS para la detección de servicios. Conserva la configuración administrada por la distribución al editar su ConfigMap. El modo insecure de pods que aparece a continuación proporciona registros heredados basados en IP sin verificar la existencia del Pod; usa disabled si esos registros no son necesarios o verified si aceptas el costo adicional de observación y memoria.

**Formato de los nombres DNS**:

* **Service**: `<service-name>.<namespace>.svc.cluster.local`
* **Pod**: `<pod-ip-with-dashes>.<namespace>.pod.cluster.local` (registro IPv4; depende del modo de pods de CoreDNS)

**Ejemplo de configuración de DNS**:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: coredns
  namespace: kube-system
data:
  Corefile: |
    .:53 {
        errors
        health
        ready
        kubernetes cluster.local in-addr.arpa ip6.arpa {
          pods insecure
          fallthrough in-addr.arpa ip6.arpa
        }
        prometheus :9153
        forward . /etc/resolv.conf
        cache 30
        loop
        reload
        loadbalance
    }
```

### Malla de servicios

Una malla de servicios es una capa de infraestructura que administra la comunicación entre microservicios. Las mallas de servicios ofrecen administración del tráfico, seguridad y observabilidad.

**Principales mallas de servicios**:

* **Istio**: la malla de servicios más utilizada
* **Linkerd**: malla de servicios ligera
* **AWS App Mesh**: el soporte finalizó el 30 de septiembre de 2026; AWS indica que ya no se puede acceder a su consola ni a sus recursos.

**Ejemplo de Istio VirtualService**:

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: reviews-route
spec:
  hosts:
  - reviews
  http:
  - match:
    - headers:
        end-user:
          exact: jason
    route:
    - destination:
        host: reviews
        subset: v2
  - route:
    - destination:
        host: reviews
        subset: v1
---
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: reviews-subsets
spec:
  host: reviews
  subsets:
  - name: v1
    labels:
      version: v1
  - name: v2
    labels:
      version: v2
```

## Almacenamiento de Kubernetes

Kubernetes ofrece varias opciones de almacenamiento para aplicaciones en contenedores. Permite conservar los datos aunque los pods se reinicien o se reprogramen.

![Almacenamiento de Kubernetes: el Pod 1 y el Pod 2 se vinculan a PersistentVolumes (pv-1, pv-3) mediante PersistentVolumeClaims (pvc-1, pvc-2), el StorageClass estándar aprovisiona los PV de forma dinámica y cada PV se asigna a un volumen AWS EBS.](../.gitbook/assets/en-basics-04-kubernetes-introduction-5.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-basics-04-kubernetes-introduction-5.html)

### Volume

Un Volume es un directorio que se puede montar en los contenedores de un pod para conservar los datos durante el ciclo de vida del pod. Los Volume también se usan para compartir datos entre los contenedores de un pod.

**Tipos principales de Volume**:

* **emptyDir**: empieza como un directorio vacío y se elimina cuando se elimina el pod
* **hostPath**: monta en el pod una ruta del sistema de archivos del nodo host
* **configMap**: monta un ConfigMap como Volume
* **secret**: monta un Secret como Volume
* **persistentVolumeClaim**: monta un volumen persistente en el pod

**Ejemplo de Volume emptyDir**:

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: test-pd
spec:
  containers:
  - name: test-container
    image: nginx:1.30.6
    volumeMounts:
    - mountPath: /cache
      name: cache-volume
  volumes:
  - name: cache-volume
    emptyDir: {}
```

### PersistentVolume (PV)

Un PersistentVolume es un objeto de API que representa un recurso de almacenamiento del clúster. Existe independientemente de los pods y lo aprovisiona un administrador de forma estática o un aprovisionador de almacenamiento de forma dinámica.

**Modos de acceso**:

* **ReadWriteOnce (RWO)**: se puede montar con acceso de lectura y escritura en un único nodo
* **ReadOnlyMany (ROX)**: se puede montar con acceso de solo lectura en varios nodos
* **ReadWriteMany (RWX)**: se puede montar con acceso de lectura y escritura en varios nodos
* **ReadWriteOncePod (RWOP)**: acceso de un único Pod para los volúmenes CSI compatibles; RWO por sí solo todavía permite varios Pod en el mismo nodo

El controlador CSI de EBS debe estar instalado previamente y los permisos de IAM deben estar configurados. Usa un ID de volumen existente y su zona de disponibilidad real; nunca reutilices un volumen que siga en uso en otro lugar. Estos ejemplos de almacenamiento son específicos de AWS; los clústeres locales necesitan su propio aprovisionador.

**Ejemplo de PersistentVolume**:

```yaml
apiVersion: v1
kind: PersistentVolume
metadata:
  name: pv-example
spec:
  capacity:
    storage: 10Gi
  accessModes:
  - ReadWriteOnce
  persistentVolumeReclaimPolicy: Retain
  storageClassName: ebs-gp3
  csi:
    driver: ebs.csi.aws.com
    volumeHandle: vol-0123456789abcdef0
    fsType: ext4
  nodeAffinity:
    required:
      nodeSelectorTerms:
      - matchExpressions:
        - key: topology.kubernetes.io/zone
          operator: In
          values:
          - replace-with-volume-az
```

### PersistentVolumeClaim (PVC)

Un PersistentVolumeClaim es un objeto de API que representa una solicitud de almacenamiento de un usuario. Los pods acceden a los PV mediante los PVC.

**Ejemplo de PersistentVolumeClaim**:

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: pvc-example
spec:
  accessModes:
  - ReadWriteOnce
  resources:
    requests:
      storage: 5Gi
  storageClassName: ebs-gp3
```

**Ejemplo de Pod que usa un PVC**:

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: mypod
spec:
  containers:
    - name: myfrontend
      image: nginx:1.30.6
      volumeMounts:
      - mountPath: "/var/www/html"
        name: mypd
  volumes:
    - name: mypd
      persistentVolumeClaim:
        claimName: pvc-example
```

### StorageClass

Un StorageClass describe las «clases» de almacenamiento que proporcionan los administradores. Puede ofrecer distintos niveles de calidad del servicio, políticas de copias de seguridad o políticas arbitrarias determinadas por los administradores del clúster.

**Ejemplo de StorageClass**:

```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: ebs-gp3
provisioner: ebs.csi.aws.com
parameters:
  type: gp3
  csi.storage.k8s.io/fstype: ext4
  encrypted: 'true'
reclaimPolicy: Delete
allowVolumeExpansion: true
volumeBindingMode: WaitForFirstConsumer
```

### Aprovisionamiento dinámico

El aprovisionamiento dinámico es una función que crea PV automáticamente cuando se solicitan PVC mediante StorageClass.

**Ejemplo de aprovisionamiento dinámico**:

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: dynamic-pvc
spec:
  accessModes:
  - ReadWriteOnce
  resources:
    requests:
      storage: 10Gi
  storageClassName: ebs-gp3
```

### CSI (Container Storage Interface)

CSI proporciona una interfaz estándar entre Kubernetes y los sistemas de almacenamiento. Esto permite que los proveedores de almacenamiento desarrollen sus propios controladores sin modificar el código de Kubernetes.

**Principales controladores CSI**:

* **AWS EBS CSI Driver**: administración de volúmenes de Amazon EBS
* **AWS EFS CSI Driver**: administración de sistemas de archivos de Amazon EFS
* **AWS FSx for Lustre CSI Driver**: administración de sistemas de archivos FSx for Lustre
* **GCE PD CSI Driver**: administración de discos persistentes de Google Compute Engine
* **Azure Disk CSI Driver**: administración de discos de Azure

**StorageClass que utiliza un controlador CSI instalado**:

```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: ebs-sc
provisioner: ebs.csi.aws.com
parameters:
  type: gp3
  encrypted: 'true'
  csi.storage.k8s.io/fstype: ext4
volumeBindingMode: WaitForFirstConsumer
```

## Configuración y seguridad de Kubernetes

Kubernetes proporciona diversos objetos y mecanismos para administrar la configuración y la seguridad de las aplicaciones.

### ConfigMap

Un ConfigMap es un objeto de API que almacena datos de configuración como pares clave-valor. Los pods pueden usar los datos de ConfigMap como variables de entorno, argumentos de línea de comandos o archivos de configuración.

**Ejemplo de ConfigMap**:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: app-config
data:
  app.properties: |
    app.name=MyApp
    app.version=1.0.0
    app.environment=production
  log-level: INFO
  max-connections: "100"
```

Los valores de entorno no se actualizan automáticamente; vuelve a crear los Pod después de los cambios. Las actualizaciones de Volume son graduales y requieren que la aplicación se recargue; los montajes subPath no reciben actualizaciones.

**Ejemplo de Pod que usa ConfigMap**:

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: config-pod
spec:
  containers:
  - name: app
    image: myapp:1.0
    env:
    - name: LOG_LEVEL
      valueFrom:
        configMapKeyRef:
          name: app-config
          key: log-level
    volumeMounts:
    - name: config-volume
      mountPath: /etc/config
  volumes:
  - name: config-volume
    configMap:
      name: app-config
```

### Secret

Un Secret es un objeto de API que almacena información confidencial, como contraseñas, tokens y claves. Es similar a ConfigMap, pero está diseñado para datos confidenciales.

**Tipos de Secret**:

* **Opaque**: datos arbitrarios definidos por el usuario (predeterminado)
* **kubernetes.io/service-account-token**: Secret de token heredado de larga duración solicitado manualmente; se recomienda usar TokenRequest/tokens proyectados
* **kubernetes.io/dockercfg**: archivo \~/.dockercfg serializado
* **kubernetes.io/dockerconfigjson**: archivo \~/.docker/config.json serializado
* **kubernetes.io/basic-auth**: credenciales para autenticación básica
* **kubernetes.io/ssh-auth**: credenciales para autenticación SSH
* **kubernetes.io/tls**: datos para TLS de cliente o servidor

El campo data usa codificación base64, no cifrado. Protege los Secret con RBAC y con un cifrado en reposo adecuado para el clúster; EKS cifra de forma predeterminada todos los datos de la API de Kubernetes en las versiones 1.28 y posteriores. Los valores que aparecen a continuación son solo para demostración y deben reemplazarse.

**Ejemplo de Secret**:

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: db-credentials
type: Opaque
data:
  username: YWRtaW4=  # base64 encoded "admin"
  password: cGFzc3dvcmQxMjM=  # base64 encoded "password123"
```

**Ejemplo de Pod que usa Secret**:

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: secret-pod
spec:
  containers:
  - name: db-client
    image: db-client:1.0
    env:
    - name: DB_USERNAME
      valueFrom:
        secretKeyRef:
          name: db-credentials
          key: username
    - name: DB_PASSWORD
      valueFrom:
        secretKeyRef:
          name: db-credentials
          key: password
```

### RBAC (control de acceso basado en roles)

RBAC es un mecanismo para controlar el acceso a la API de Kubernetes. Concede permisos específicos a usuarios o cuentas de servicio mediante Role y RoleBinding.

**Objetos RBAC principales**:

* **Role**: define un conjunto de permisos dentro de un Namespace
* **ClusterRole**: reglas reutilizables para recursos del clúster o de Namespace; la vinculación determina su ámbito efectivo
* **RoleBinding**: vincula un rol a usuarios, grupos o cuentas de servicio
* **ClusterRoleBinding**: vincula un rol de clúster a usuarios, grupos o cuentas de servicio

**Ejemplo de Role**:

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  namespace: default
  name: pod-reader
rules:
- apiGroups: [""]
  resources: ["pods"]
  verbs: ["get", "watch", "list"]
```

**Ejemplo de RoleBinding**:

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: read-pods
  namespace: default
subjects:
- kind: User
  name: jane
  apiGroup: rbac.authorization.k8s.io
roleRef:
  kind: Role
  name: pod-reader
  apiGroup: rbac.authorization.k8s.io
```

### ServiceAccount

Un ServiceAccount proporciona una identidad para los procesos que se ejecutan dentro de un pod. Los pods usan cuentas de servicio para comunicarse con la API de Kubernetes.

**Ejemplo de ServiceAccount**:

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: app-sa
  namespace: default
```

**Ejemplo de Pod que usa ServiceAccount**:

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: sa-pod
spec:
  serviceAccountName: app-sa
  containers:
  - name: app
    image: myapp:1.0
```

### NetworkPolicy

NetworkPolicy permite controlar la comunicación entre pods. De forma predeterminada, todos los pods pueden comunicarse entre sí, pero puedes restringirlo mediante políticas de red.

**Ejemplo de NetworkPolicy**:

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: db-network-policy
  namespace: default
spec:
  podSelector:
    matchLabels:
      role: db
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          role: api
    ports:
    - protocol: TCP
      port: 3306
  - from:
    - namespaceSelector:
        matchLabels:
          kubernetes.io/metadata.name: monitoring
      podSelector:
        matchLabels:
          app: prometheus
    ports:
    - protocol: TCP
      port: 9104
  egress:
  - to:
    - namespaceSelector:
        matchLabels:
          kubernetes.io/metadata.name: kube-system
      podSelector:
        matchLabels:
          k8s-app: kube-dns
    ports:
    - protocol: UDP
      port: 53
    - protocol: TCP
      port: 53
```

### Pod Security Admission y SecurityContext

PodSecurityPolicy se eliminó en la versión 1.25. Pod Security Admission aplica Pod Security Standards mediante etiquetas de Namespace. SecurityContext configura la propia carga de trabajo; no reemplaza la aplicación de políticas de admisión.

**Ejemplo de Pod SecurityContext**:

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: security-context-pod
spec:
  securityContext:
    runAsUser: 1000
    runAsGroup: 3000
    fsGroup: 2000
    runAsNonRoot: true
    seccompProfile:
      type: RuntimeDefault
  containers:
  - name: app
    image: myapp:1.0
    securityContext:
      allowPrivilegeEscalation: false
      capabilities:
        drop:
        - ALL
```

### Pod Security Standards

Pod Security Standards ofrecen tres niveles de políticas que definen requisitos de seguridad para los pods:

1. **Privileged**: sin restricciones; se permiten todas las funciones
2. **Baseline**: evita escaladas de privilegios conocidas
3. **Restricted**: aplica restricciones estrictas según las prácticas recomendadas

**Ejemplo de aplicación de Pod Security Standards**:

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: my-namespace
  labels:
    pod-security.kubernetes.io/enforce: restricted
    pod-security.kubernetes.io/audit: restricted
    pod-security.kubernetes.io/warn: restricted
```

## Kubernetes frente a Amazon EKS

Amazon EKS (Elastic Kubernetes Service) es un servicio de Kubernetes administrado que ofrece AWS. EKS expone la API estándar de Kubernetes con integraciones de AWS. La comparación siguiente presupone grupos de nodos EC2 convencionales; las responsabilidades y las funciones compatibles difieren en Auto Mode, Fargate y Hybrid Nodes.

### Diferencias principales

| Característica           | Kubernetes autoadministrado                    | Amazon EKS                                                        |
| ------------------------ | ----------------------------------------------- | ----------------------------------------------------------------- |
| Administración del plano de control | El usuario lo administra directamente                           | AWS lo administra                                                    |
| Alta disponibilidad        | El usuario debe configurarla                             | Se proporciona de forma predeterminada (desplegado en varias zonas de disponibilidad) |
| Actualizaciones                 | El usuario las realiza directamente                          | AWS administra las actualizaciones del plano de control; coordina las actualizaciones de nodos y complementos                                |
| Parches de seguridad         | El usuario los aplica directamente                           | AWS aplica parches al plano de control; el despliegue gradual de AMI de nodos administrados sigue siendo responsabilidad del usuario (Auto Mode es distinto)                                      |
| Autenticación           | Es necesario configurar varias opciones              | Integrada con AWS IAM                                           |
| Redes               | Es necesario seleccionar y configurar un complemento CNI | Amazon VPC CNI se proporciona de forma predeterminada                                |
| Balanceo de carga           | Requiere configuración manual                   | Integración con AWS Load Balancer Controller                          |
| Almacenamiento                  | Requiere configurar el controlador de almacenamiento           | Integración con los controladores CSI de EBS, EFS y FSx                              |
| Supervisión               | Requiere configuración manual                           | Integración con CloudWatch Container Insights                         |
| Costo                     | Infraestructura más esfuerzo operativo                       | Costo del plano de control más costos de infraestructura                         |

### Funciones adicionales de EKS

1. **Integración con AWS IAM**: integración de Kubernetes RBAC y AWS IAM
2. **AWS Load Balancer Controller**: integración de ALB y NLB con servicios e Ingress de Kubernetes
3. **Grupos de nodos administrados de EKS**: automatización de la administración del ciclo de vida de los nodos
4. **Perfiles de Fargate**: ejecución de pods de Kubernetes sin servidor
5. **Complemento VPC CNI**: integración con las redes de AWS VPC
6. **CloudWatch Container Insights**: supervisión y registro de contenedores
7. **AWS App Mesh**: el soporte finalizó el 30 de septiembre de 2026; AWS indica que ya no se puede acceder a su consola ni a sus recursos
8. **AWS Distro for OpenTelemetry**: rastreo distribuido y supervisión
9. **Consola y CLI de EKS**: interfaces de administración
10. **EKS Blueprints**: configuración de clúster basada en prácticas recomendadas

### Componentes específicos de EKS

1. **Plano de control de EKS**: alta disponibilidad en varias zonas de disponibilidad
2. **AMI de nodos de EKS**: opciones AL2023/Bottlerocket/Windows proporcionadas por AWS y AMI compatibles suministradas por separado, como Ubuntu
3. **Grupos de nodos administrados de EKS**: flujos de trabajo de actualización de grupos de nodos; el escalado de nodos en función de las cargas de trabajo requiere un autoscaler
4. **EKS Fargate**: entorno de ejecución de contenedores sin servidor
5. **EKS Connector**: conecta clústeres externos de Kubernetes con la consola de AWS
6. **EKS Anywhere**: ejecuta clústeres compatibles con EKS en entornos locales
7. **EKS Distro**: distribución de Kubernetes administrada por AWS

### Integración con servicios de AWS

EKS se integra con los siguientes servicios de AWS:

1. **Amazon VPC**: infraestructura de redes
2. **AWS IAM**: autenticación y autorización
3. **Amazon ECR**: repositorio de imágenes de contenedor
4. **AWS Load Balancer**: distribución del tráfico de aplicaciones
5. **Amazon EBS/EFS/FSx**: almacenamiento persistente
6. **AWS CloudWatch**: supervisión y registro
7. **AWS CloudTrail**: auditoría de la API de AWS; para auditar la API de Kubernetes se requiere habilitar el registro de auditoría de EKS
8. **AWS KMS**: administración de claves de cifrado
9. **AWS WAF**: se puede asociar a puntos de entrada de aplicaciones compatibles, como ALB; no se asocia directamente al endpoint de la API de EKS
10. **AWS Shield**: protección contra DDoS
11. **AWS X-Ray**: rastreo distribuido
12. **AWS App Mesh**: el soporte finalizó el 30 de septiembre de 2026; las cargas de trabajo existentes requieren migración
13. **AWS SageMaker**: cargas de trabajo de aprendizaje automático
14. **AWS Bedrock**: cargas de trabajo de IA generativa

## Primeros pasos con Kubernetes

Hay varias maneras de empezar a usar Kubernetes. Aquí presentamos brevemente cómo iniciar Kubernetes en un entorno de desarrollo local y en AWS EKS.

### Entorno de desarrollo local

#### Minikube

Minikube ejecuta clústeres locales de Kubernetes y admite configuraciones de uno o varios nodos.

**Instalación e inicio**:

```bash
# Install
brew install minikube

# Start
minikube start

# Check status
minikube status

# Inspect workloads; see the maintained Headlamp UI section below.
kubectl get pods -A
```

#### Kind (Kubernetes en Docker)

Kind ejecuta clústeres locales mediante contenedores como nodos, con proveedores compatibles Docker/Podman/nerdctl.

**Instalación e inicio**:

```bash
# Install
brew install kind

# Create cluster
kind create cluster --name my-cluster

# Check cluster
kind get clusters
kubectl cluster-info --context kind-my-cluster
```

#### Docker Desktop

Docker Desktop ofrece una función para ejecutar Kubernetes fácilmente en Mac y Windows.

**Configuración**:

1. Instala Docker Desktop
2. Settings > Kubernetes > marca «Enable Kubernetes»
3. Haz clic en «Apply & Restart»

### AWS EKS

#### Creación de un clúster EKS con eksctl

eksctl es una herramienta CLI sencilla para crear y administrar clústeres de EKS.

**Instalación y creación del clúster**:

```bash
# Install a reviewed eksctl release from the official eksctl-io GitHub releases,
# verify eksctl_checksums.txt, and place the binary in PATH.
eksctl version
# Use an existing short-lived AWS login/SSO profile with required permissions.
aws sts get-caller-identity
# This example provisions real AWS resources. Choose the intended account/Region,
# supported EKS version, networking and IAM configuration before running it.
: "${EKS_VERSION:?Set a version supported by EKS, not upstream latest}"
eksctl create cluster \
  --name my-cluster \
  --region ap-northeast-2 \
  --version "$EKS_VERSION" \
  --nodegroup-name standard-workers \
  --node-type t3.medium \
  --node-ami-family AmazonLinux2023 \
  --node-private-networking \
  --nodes 3 --nodes-min 1 --nodes-max 4 --managed
kubectl get nodes
```

#### Creación de un clúster EKS con la consola de administración de AWS

También puedes crear clústeres de EKS mediante la consola de administración de AWS.

**Pasos**:

1. Inicia sesión en la consola de administración de AWS
2. Ve al servicio EKS
3. Haz clic en «Create cluster»
4. Configura el nombre del clúster, el rol de IAM, la VPC y las subredes
5. Configura los grupos de seguridad
6. Configura las opciones de registro
7. Crea el clúster
8. Agrega grupos de nodos

### Instalación y configuración de kubectl

kubectl es una herramienta de línea de comandos para interactuar con clústeres de Kubernetes.

**Instalación**:

```bash
# macOS: use a kubectl version within one minor of the API server.
brew install kubectl
```

```bash
# Linux: select an explicit compatible version and architecture.
set -euo pipefail
: "${KUBECTL_VERSION:?Set a cluster-compatible version, e.g. v1.37.1}"
case "$(uname -m)" in
  x86_64) KUBECTL_ARCH=amd64 ;;
  aarch64|arm64) KUBECTL_ARCH=arm64 ;;
  *) echo "Choose a supported kubectl architecture" >&2; exit 1 ;;
esac
curl --fail --location --output kubectl "https://dl.k8s.io/release/$KUBECTL_VERSION/bin/linux/$KUBECTL_ARCH/kubectl"
curl --fail --location --output kubectl.sha256 "https://dl.k8s.io/release/$KUBECTL_VERSION/bin/linux/$KUBECTL_ARCH/kubectl.sha256"
echo "$(cat kubectl.sha256)  kubectl" | sha256sum --check
sudo install -m 0755 kubectl /usr/local/bin/kubectl
```

```powershell
$ErrorActionPreference = "Stop"
$KubectlVersion = Read-Host "Cluster-compatible kubectl version (vX.Y.Z)"
$KubectlArch = Read-Host "Architecture (amd64 or arm64)"
if ($KubectlVersion -notmatch '^v\d+\.\d+\.\d+$' -or $KubectlArch -notin @('amd64','arm64')) { throw "Invalid version/architecture" }
$BaseUrl = "https://dl.k8s.io/release/$KubectlVersion/bin/windows/$KubectlArch"
Invoke-WebRequest "$BaseUrl/kubectl.exe" -OutFile kubectl.exe
Invoke-WebRequest "$BaseUrl/kubectl.exe.sha256" -OutFile kubectl.exe.sha256
if ((Get-FileHash kubectl.exe -Algorithm SHA256).Hash -ne (Get-Content kubectl.exe.sha256).Trim()) { throw "Checksum mismatch" }
# Move the verified binary to a directory included in PATH.
```

**Comandos básicos**:

```bash
# Check cluster info
kubectl cluster-info

# List nodes
kubectl get nodes

# Check pods in all namespaces
kubectl get pods --all-namespaces

# Create deployment
kubectl create deployment nginx --image=nginx:1.30.6

# Expose service
kubectl expose deployment nginx --port=80 --type=ClusterIP
# Run port-forward in a separate terminal; stop it when finished.
kubectl port-forward service/nginx 8080:80

# Check logs
kubectl logs <pod-name>

# Execute command in pod container
kubectl exec -it <pod-name> -- /bin/bash
```

### Uso de la interfaz de usuario de Headlamp

Kubernetes Dashboard está archivado y ya no recibe mantenimiento. Usa Headlamp con una identidad limitada por el RBAC existente. El ejemplo de Helm desactiva la vinculación automática de cluster-admin y no habilita el modo inseguro de token compartido de cuenta de servicio. Un administrador puede conceder por separado permisos de alcance reducido.

```bash
helm repo add headlamp https://kubernetes-sigs.github.io/headlamp/
helm repo update headlamp
: "${HEADLAMP_CHART_VERSION:?Set a reviewed chart version}"
helm upgrade --install headlamp headlamp/headlamp \
  --namespace kube-system --version "$HEADLAMP_CHART_VERSION" \
  --set clusterRoleBinding.create=false \
  --set config.unsafeUseServiceAccountToken=false
kubectl -n kube-system port-forward service/headlamp 8080:80
```

Abre `http://localhost:8080` localmente y sigue el flujo de inicio de sesión de la versión de Headlamp instalada. El Ingress público requiere configurar TLS y autenticación por separado.

## Conclusión

Kubernetes es una plataforma potente que automatiza el despliegue, el escalado y la administración de aplicaciones en contenedores. A continuación, se resumen los principales temas tratados en este documento:

### Arquitectura principal

* **Plano de control**: cerebro del clúster (servidor de API, etcd, Scheduler, Controller Manager)
* **Nodos de trabajo**: nodos que ejecutan las aplicaciones reales (kubelet, kube-proxy, entorno de ejecución de contenedores)
* **Configuración declarativa**: define el estado deseado y Kubernetes hace que el estado actual coincida con él

### Objetos y recursos principales

* **Objetos básicos**: Pod, Service, Volume, Namespace
* **Recursos de cargas de trabajo**: Deployment, StatefulSet, DaemonSet, Job, CronJob
* **Configuración y seguridad**: ConfigMap, Secret, RBAC, ServiceAccount
* **Redes**: Service, Ingress, NetworkPolicy
* **Almacenamiento**: PersistentVolume, PersistentVolumeClaim, StorageClass

### Ruta de aprendizaje recomendada

**Paso 1: preparar un entorno local**

* Crea un clúster local con minikube o kind
* Aprende los comandos de kubectl
* Practica con los objetos básicos (Pod, Deployment, Service)

**Paso 2: dominar los conceptos fundamentales**

* Comprende y practica con los recursos de cargas de trabajo
* Administra la configuración con ConfigMap y Secret
* Configura las redes con Service e Ingress
* Administra el almacenamiento con PV y PVC

**Paso 3: aprender las funciones avanzadas**

* RBAC y políticas de seguridad
* Escalado automático (HPA, VPA, Cluster Autoscaler)
* Supervisión y registro (Prometheus, Grafana)
* Malla de servicios (Istio, Linkerd)

**Paso 4: operaciones de producción**

* Usa Amazon EKS u otro servicio administrado de Kubernetes
* Integra el pipeline de CI/CD
* Estrategias de recuperación ante desastres y copias de seguridad
* Optimización de costos y administración de recursos

### Próximos pasos

* **Análisis detallado de EKS**: funciones específicas de EKS (Fargate, VPC CNI, ALB Controller)
* **Redes avanzadas**: complementos CNI (Calico, Cilium)
* **Observabilidad**: métricas, registros y rastreo
* **GitOps**: ArgoCD, Flux
* **Refuerzo de la seguridad**: Pod Security Standards, políticas de red, OPA/Gatekeeper

Kubernetes sigue evolucionando y se ha convertido en un elemento central del desarrollo y las operaciones de aplicaciones nativas de la nube. Esperamos que este documento te ayude a comenzar tu recorrido con Kubernetes.

### Recursos de aprendizaje adicionales

* **Documentación oficial**: la [documentación oficial de Kubernetes](https://kubernetes.io/docs/) ofrece la información más precisa y actualizada
* **Tutoriales interactivos**: práctica guiada disponible en [Tutoriales de Kubernetes](https://kubernetes.io/docs/tutorials/)
* **Comunidad**: [Kubernetes Slack](https://slack.k8s.io/), [Reddit r/kubernetes](https://reddit.com/r/kubernetes)
* **Certificaciones**: CKA (Certified Kubernetes Administrator), CKAD (Certified Kubernetes Application Developer)
* **Comunidad coreana**: Kubernetes Korea User Group, AWS Korea User Group

## Cuestionario

Para comprobar lo que has aprendido en este capítulo, responde el [cuestionario de introducción a Kubernetes](../quizzes/basics/04-kubernetes-introduction-quiz.md).

## Referencias

* [Documentación oficial de Kubernetes](https://kubernetes.io/docs/)
* [Documentación de Amazon EKS](https://docs.aws.amazon.com/eks/)
* [Repositorio de Kubernetes en GitHub](https://github.com/kubernetes/kubernetes)
* [CNCF (Cloud Native Computing Foundation)](https://www.cncf.io/)
* [Kubernetes The Hard Way](https://github.com/kelseyhightower/kubernetes-the-hard-way)
* [Kubernetes Patterns](https://www.oreilly.com/library/view/kubernetes-patterns/9781492050278/)

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
