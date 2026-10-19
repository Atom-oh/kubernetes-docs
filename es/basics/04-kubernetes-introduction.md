# Introducción a Kubernetes

> **Versiones compatibles**: Kubernetes upstream 1.35–1.37; soporte estándar de EKS 1.34–1.37 (al 12 de octubre de 2026)
> **Última actualización**: 16 de octubre de 2026

El proyecto Kubernetes mantiene ramas de publicación para las tres versiones menores más recientes (1.35–1.37). Kubernetes 1.34, en su distribución original, está en fase de mantenimiento y recibe parches hasta el **27 de octubre de 2026**. Esa fecha difiere del fin de soporte de la versión en Amazon EKS. Consulte el [ciclo de vida de AWS EKS](https://docs.aws.amazon.com/eks/latest/userguide/kubernetes-versions.html) para comprobar las versiones cubiertas y sus fechas.

Kubernetes (K8s) es una plataforma de código abierto para orquestar contenedores. Automatiza el despliegue, el escalado y la administración de aplicaciones en contenedores. Esta guía explica sus conceptos básicos, arquitectura, componentes principales y funciones.

Los ejemplos independientes de esta guía se revisaron mediante análisis estático de los esquemas y la documentación oficial; no se validaron con despliegues de producción. Antes de aplicarlos, compruebe en el entorno de destino las imágenes personalizadas, los nombres y las etiquetas, TLS, IAM/RBAC, CNI y los requisitos de almacenamiento. Sustituya también los marcadores de posición.

## Configuración del entorno de laboratorio

Para practicar con los ejemplos de esta guía, prepare las herramientas y el entorno siguientes:

### Herramientas necesarias

* **kubectl**: herramienta de línea de comandos para interactuar con clústeres de Kubernetes
* **Controlador para el clúster local**: motor de contenedores o controlador de máquina virtual compatible con minikube/kind. Los nodos de Kubernetes utilizan un entorno de ejecución compatible con CRI v1.
* **minikube** o **kind**: herramientas para crear un clúster local de Kubernetes y practicar durante el desarrollo o el aprendizaje

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

Siga la guía oficial de inicio de minikube para elegir el binario, su suma de comprobación y el controlador adecuado para su sistema operativo y arquitectura. Ejecute las instrucciones de Linux y Windows en el shell correspondiente y añada el binario verificado a PATH. En macOS:

```bash
brew install minikube
minikube version
```

### Iniciar un clúster local

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

## ¿Qué es Kubernetes? {#what-is-kubernetes}

Kubernetes significa «timonel» o «piloto» en griego. Este sistema de código abierto automatiza el despliegue, el escalado y la operación de aplicaciones en contenedores. Se inspiró en Borg, el sistema interno de Google, y se publicó como código abierto en 2014.

### Características principales de Kubernetes

1. **Descubrimiento de servicios y balanceo de carga**: exponer contenedores al exterior y distribuir el tráfico
2. **Orquestación del almacenamiento**: montar automáticamente sistemas de almacenamiento locales o en la nube
3. **Despliegues y reversiones**: actualizar aplicaciones gradualmente y permitir que un operador o una herramienta revierta los cambios; un Deployment fallido no se revierte automáticamente.
4. **Asignación eficiente de recursos**: distribuir contenedores entre nodos según sus requisitos de recursos
5. **Autorreparación**: reiniciar contenedores fallidos y reemplazar los que no responden
6. **Administración de Secrets y configuración**: almacenar información confidencial y actualizar la configuración
7. **Escalado horizontal**: ajustar el tamaño de las aplicaciones mediante comandos sencillos o una interfaz de usuario
8. **Ejecución por lotes**: administrar cargas de trabajo por lotes y de integración continua

### Problemas que resuelve Kubernetes

* **Orquestación de contenedores**: administrar cientos o miles de contenedores de forma eficiente
* **Alta disponibilidad**: facilitar aplicaciones resilientes mediante réplicas, distribución, comprobaciones de estado y capacidad suficiente
* **Escalabilidad**: ampliar la capacidad automáticamente cuando aumenta el tráfico
* **Recuperación**: restablecer las cargas de trabajo fallidas mediante reconciliación; la recuperación ante desastres también requiere copias de seguridad probadas y planes de restauración
* **Eficiencia de recursos**: aprovechar los recursos de hardware de forma eficiente
* **Configuración declarativa**: administrar la infraestructura como código
* **Multinube y nube híbrida**: mantener un despliegue y una administración coherentes en distintos entornos

## Historia de Kubernetes {#history-of-kubernetes}

### Antecedentes

* **2003-2013**: Google utilizó internamente un sistema de orquestación de contenedores llamado Borg
* **Junio de 2014**: Google publicó Kubernetes como código abierto
* **Julio de 2015**: se publicó Kubernetes 1.0 y se donó a la Cloud Native Computing Foundation (CNCF)
* **2016-2017**: los principales proveedores de nube lanzaron servicios de Kubernetes administrados
* **2018 en adelante**: se consolidó como el estándar de facto para la orquestación de contenedores

### Origen del nombre

Kubernetes (κυβερνήτης) significa «timonel» o «piloto» en griego y alude a su papel de dirigir aplicaciones en contenedores. La abreviatura K8s sustituye por un 8 las ocho letras entre «K» y «s».

### Significado del logotipo

El logotipo de Kubernetes representa un timón de barco con siete radios. Simboliza su función de dirigir el rumbo de las aplicaciones en contenedores.

## Arquitectura de Kubernetes {#kubernetes-architecture}

Kubernetes organiza el clúster en un plano de control y nodos de trabajo. Los nodos maestros, que forman el plano de control, administran el clúster; los nodos de trabajo ejecutan las cargas de las aplicaciones.

### Componentes del plano de control (maestro)

![Plano de control de Kubernetes: las solicitudes de kubectl pasan por kube-apiserver hasta etcd, mientras que kube-scheduler, kube-controller-manager y cloud-controller-manager observan y reconcilian a través del servidor de API.](../.gitbook/assets/en-basics-04-kubernetes-introduction-0.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-basics-04-kubernetes-introduction-0.html)

1. **kube-apiserver**: interfaz del plano de control que expone la API de Kubernetes
2. **etcd**: almacén de pares clave-valor coherente y de alta disponibilidad para los objetos de la API de Kubernetes y el estado del clúster (no el contenido de los volúmenes de aplicaciones)
3. **kube-scheduler**: componente que asigna pods a los nodos
4. **kube-controller-manager**: componente que ejecuta procesos de controladores
   * Controlador de nodos: notificación y respuesta cuando los nodos dejan de funcionar
   * Controlador de replicación: mantiene el número correcto de réplicas de pods
   * Controlador de EndpointSlice: mantiene los registros de endpoints de Service (Endpoints, la opción heredada, está obsoleto)
   * El controlador de ServiceAccount crea cuentas predeterminadas; los tokens proyectados de Pod usan TokenRequest y la rotación de kubelet
5. **cloud-controller-manager**: componente que contiene lógica de control específica de la nube
   * Controlador de nodos: comprueba con el proveedor de nube si se ha eliminado un nodo
   * Controlador de rutas: configura rutas en la infraestructura de la nube
   * Controlador de Service: crea, actualiza y elimina balanceadores de carga del proveedor de nube

### Componentes de los nodos

![Nodo de trabajo de Kubernetes: kubelet recibe instrucciones del plano de control y dirige el entorno de ejecución CRI (containerd/CRI-O, o Docker Engine mediante un adaptador externo), que ejecuta los contenedores del Pod. kube-proxy mantiene las reglas de red.](../.gitbook/assets/en-basics-04-kubernetes-introduction-1.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-basics-04-kubernetes-introduction-1.html)

1. **kubelet**: agente que se ejecuta en cada nodo y garantiza que los contenedores de los pods estén en ejecución
2. **kube-proxy**: proxy de red que se ejecuta en cada nodo e implementa el concepto de Service de Kubernetes
3. **Entorno de ejecución de contenedores**: software que implementa CRI v1, como containerd o CRI-O; Docker Engine requiere un adaptador CRI independiente

### Arquitectura completa

![Clúster completo de Kubernetes: los clientes kubectl se conectan a kube-apiserver, que coordina etcd, kube-scheduler, kube-controller-manager y cloud-controller-manager, y dirige kubelet, el entorno de ejecución de contenedores y kube-proxy en dos nodos de trabajo.](../.gitbook/assets/en-basics-04-kubernetes-introduction-2.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-basics-04-kubernetes-introduction-2.html)

## Componentes principales de Kubernetes {#kubernetes-main-components}

### Servidor de API (kube-apiserver)

El servidor de API es la interfaz del plano de control que expone la API de Kubernetes. Las solicitudes a la API de Kubernetes pasan por él; el tráfico de aplicaciones y las operaciones de E/S de almacenamiento no pasan por el servidor de API.

**Funciones principales**:

* Proporciona una API REST
* Autenticación y autorización
* Validación de solicitudes
* Comunicación con etcd
* Escalabilidad horizontal

### etcd

etcd es un almacén de pares clave-valor coherente y de alta disponibilidad que almacena los objetos de la API de Kubernetes y el estado del clúster (no el contenido de los volúmenes de aplicaciones).

**Características principales**:

* Sistema distribuido
* Coherencia sólida
* Alta disponibilidad
* Almacenamiento seguro de datos
* Función de observación para supervisar los cambios

### Planificador (kube-scheduler)

El planificador es el componente del plano de control que elige los nodos donde se ejecutarán los Pod recién creados.

**Proceso de planificación**:

1. **Filtrado**: identificar los nodos que pueden ejecutar el pod
2. **Puntuación**: asignar puntuaciones a los nodos adecuados
3. **Vinculación**: asignar el pod al nodo óptimo

**Consideraciones**:

* Requisitos de recursos (CPU y memoria)
* Restricciones de hardware, software y políticas
* Reglas de afinidad y antiafinidad
* Ubicación de los datos
* Interferencia entre cargas de trabajo

### Administrador de controladores (kube-controller-manager)

El administrador de controladores es el componente del plano de control que ejecuta los distintos procesos de control.

**Controladores principales**:

* **Controlador de nodos**: supervisa y responde al estado de los nodos
* **Controlador de replicación**: mantiene el número de réplicas de pods
* **Controlador de EndpointSlice**: mantiene los registros de endpoints de Service (Endpoints, la opción heredada, está obsoleto)
* **Controlador de ServiceAccount**: crea cuentas predeterminadas; los tokens modernos de Pod se solicitan mediante TokenRequest y kubelet los rota
* **Controlador de Job**: administra tareas puntuales
* **Controlador de CronJob**: administra tareas programadas
* **Controlador de DaemonSet**: reconcilia un Pod en cada nodo apto
* **Controlador de StatefulSet**: administra aplicaciones con estado
* **Controlador de PV**: administra volúmenes persistentes

### Administrador de controladores de nube (cloud-controller-manager)

El administrador de controladores de nube contiene la lógica específica del proveedor de nube. Los sidecars y controladores CSI, junto con kubelet y los complementos de nodo, gestionan el aprovisionamiento, la conexión y el montaje del almacenamiento. Esas funciones no corresponden a un controlador de volúmenes de CCM.

**Controladores principales**:

* **Controlador de nodos**: comprueba el estado de los nodos mediante la API del proveedor de nube
* **Controlador de rutas**: configura rutas en el entorno de nube
* **Controlador de Service**: crea, actualiza y elimina balanceadores de carga en la nube

### kubelet

kubelet es un agente que se ejecuta en cada nodo y garantiza que los contenedores de los pods estén en ejecución.

**Funciones principales**:

* Ejecutar contenedores según PodSpec
* Informar el estado de los contenedores
* Realizar comprobaciones de estado de los contenedores
* Administrar el ciclo de vida de los contenedores
* Informar el estado de los nodos

### kube-proxy

kube-proxy es un proxy de red que se ejecuta en cada nodo e implementa el concepto de Service de Kubernetes.

**Funciones principales**:

* Mantener reglas de red para las IP y los puertos de los servicios
* Reenviar conexiones
* Implementar el balanceo de carga

**Modos de funcionamiento**:

* **Modo nftables**: estable desde 1.33; compruebe la compatibilidad del kernel y del complemento de red
* **Modo iptables**: implementación de NAT mediante iptables de Linux; es el modo predeterminado
* **Modo IPVS**: obsoleto desde 1.35; planifique la migración. El antiguo modo userspace se eliminó.

## Objetos básicos de Kubernetes {#kubernetes-basic-objects}

Los objetos de Kubernetes son entidades persistentes que representan el estado del clúster: las aplicaciones en ejecución, los recursos disponibles y las políticas, entre otros elementos.

### Pod

Un Pod es la unidad desplegable más pequeña de Kubernetes y representa un grupo de uno o más contenedores. Los contenedores de un Pod comparten la red y pueden compartir volúmenes montados explícitamente; se ejecutan en el mismo nodo. No comparten automáticamente sus sistemas de archivos raíz.

**Características principales**:

* Dirección IP única
* Espacio de nombres de red compartido, con la misma IP y el mismo espacio de puertos
* Espacio de nombres IPC compartido
* Nombre de host compartido
* Comunicación entre contenedores mediante localhost

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

Los Namespace permiten separar grupos de recursos dentro de un mismo clúster y organizar equipos o proyectos. Por sí solos, no imponen aislamiento de red ni restricciones de autorización.

**Namespace predeterminados**:

* **default**: Namespace predeterminado
* **kube-system**: Namespace para los objetos creados por el sistema Kubernetes
* **kube-public**: Namespace utilizado convencionalmente para información pública; el acceso real a los objetos sigue dependiendo de RBAC
* **kube-node-lease**: Namespace para los latidos de los nodos

**Ejemplo de Namespace**:

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: development
```

### Etiquetas y selectores

Las etiquetas son pares clave-valor asociados a objetos, que se usan para identificar y seleccionar objetos. Los selectores permiten filtrar objetos según sus etiquetas.

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

Las anotaciones son pares clave-valor que almacenan metadatos no identificativos sobre los objetos. Son útiles para guardar información utilizada por herramientas o bibliotecas.

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

Un nodo es una máquina de trabajo de un clúster de Kubernetes que ejecuta Pod. Puede ser física o virtual.

**Estado del nodo**:

* **Direcciones**: nombre de host, IP interna, IP externa
* **Condiciones**: Ready, DiskPressure, MemoryPressure, PIDPressure, NetworkUnavailable
* **Capacidad**: CPU, memoria, cantidad máxima de pods
* **Información**: versión del kernel, versión del entorno de ejecución de contenedores, versión de kubelet

**Ejemplo de estado de un nodo (lo comunican el nodo y los controladores; no es un manifiesto de aprovisionamiento)**:

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

## Recursos de cargas de trabajo de Kubernetes {#kubernetes-workload-resources}

Los recursos de cargas de trabajo son objetos que se utilizan para administrar y ejecutar pods. Administran su creación, escalado, actualización y terminación.

### ReplicaSet

Un ReplicaSet reconcilia el número de objetos Pod con la cantidad deseada. Que esos Pod estén listos también depende de la capacidad, de una configuración válida y de la aplicación. Si los Pod fallan o se eliminan, ReplicaSet crea reemplazos automáticamente.

**Funciones principales**:

* Mantener la cantidad especificada de réplicas de pods
* Definir una plantilla de pod
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

Un Deployment añade un nivel de abstracción sobre ReplicaSet y permite actualizar aplicaciones de forma declarativa. Ofrece actualizaciones graduales, reversiones y escalado.

**Funciones principales**:

* Actualizaciones declarativas de aplicaciones
* Actualizaciones graduales y reversiones
* Administración del historial de implementaciones
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

El ejemplo de MySQL utiliza una sola instancia con almacenamiento persistente. StatefulSet no configura la replicación de la base de datos, la conmutación por error ni las copias de seguridad. Prepare primero mysql-secret/password y sustituya el marcador de posición de StorageClass. Aumentar únicamente las réplicas crea bases de datos independientes; para obtener alta disponibilidad, necesita un operador de bases de datos o una configuración de replicación que haya probado.

### StatefulSet

StatefulSet es un recurso de carga de trabajo para aplicaciones que requieren conservar el estado. Asigna identificadores únicos a cada pod y proporciona identificadores de red estables y almacenamiento persistente.

**Funciones principales**:

* Identificadores de red estables y únicos
* Almacenamiento estable y persistente
* Implementación y escalado secuenciales
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

El ejemplo de Fluent Bit para Linux envía los registros CRI a stdout con fines demostrativos. Excluye sus propios registros para evitar un bucle y guarda por separado la base de datos que registra la posición de lectura. No lo despliegue junto con otro recopilador que vuelva a publicar esos mismos registros en stdout. En producción, configure un destino externo y revise las rutas del host, los permisos y las excepciones de PSS.

### DaemonSet

Un DaemonSet crea un Pod en cada nodo apto, sujeto a los selectores de nodo, las taints, la capacidad y las políticas de admisión. Añade Pod cuando se incorporan nodos al clúster y los retira cuando se eliminan esos nodos.

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

Job crea uno o más pods y continúa la ejecución hasta que finaliza correctamente la cantidad especificada de pods. Es adecuado para tareas de procesamiento por lotes.

**Funciones principales**:

* Ejecución de tareas puntuales
* Ejecución paralela de tareas
* Seguimiento de ejecuciones completadas correctamente; el Job puede fallar si supera los límites de reintentos o de tiempo
* Reintentos tras un fallo

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

Los Job pueden fallar al superar sus límites de reintentos o de tiempo, y pueden repetir el mismo trabajo. Por ello, las tareas deben ser idempotentes. CronJob no garantiza que cada tarea se ejecute exactamente una vez; Forbid solo evita que se solapen los Job del mismo CronJob.

### CronJob

CronJob ejecuta Job periódicamente según una programación especificada. Funciona de forma similar a los trabajos cron de Linux.

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

## Servicios y redes de Kubernetes {#kubernetes-services-and-networking}

En Kubernetes, un CNI compatible proporciona la red de los Pod. La conectividad depende de NetworkPolicy, los firewalls y la topología. Los Service ofrecen puntos de acceso estables a conjuntos de Pod.

### Service

Un Service proporciona un único endpoint y balanceo de carga para un conjunto de pods. Como los pods se crean y eliminan dinámicamente, los servicios proporcionan direcciones de red estables pese a esos cambios.

**Tipos de Service**:

* **ClusterIP**: Service accesible solo dentro del clúster (predeterminado)
* **NodePort**: accesible externamente mediante la IP de cada nodo y un puerto específico
* **LoadBalancer**: accesible externamente mediante el balanceador de carga del proveedor de nube
* **ExternalName**: crea un registro CNAME para un servicio externo

![Acceso externo mediante Service NodePort y LoadBalancer, con otros puntos de entrada posibles como Ingress/Gateway. ClusterIP ofrece acceso interno. Los tres tipos de Service distribuyen las solicitudes al puerto 80 entre los mismos Pod (Pod 1, 2, 3).](../.gitbook/assets/en-basics-04-kubernetes-introduction-3.png)

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

Este ejemplo de AWS requiere instalar AWS Load Balancer Controller y configurar sus requisitos de IAM y red. EKS Auto Mode utiliza otro loadBalancerClass. Los clústeres locales necesitan su propia implementación de LoadBalancer.

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

Para este ejemplo, instale Traefik y prepare su IngressClass traefik, los Service app1/app2 y el Secret TLS. Las rutas /app1 y /app2 se conservan al enviar las solicitudes, por lo que los servicios de destino deben atenderlas. Crear un recurso Ingress no instala el controlador.

### Ingress

Ingress es un objeto de API que administra el enrutamiento HTTP y HTTPS desde fuera del clúster hacia los servicios internos. Ingress proporciona balanceo de carga, terminación SSL, alojamiento virtual basado en nombres, etc.

**Controladores Ingress**:

* **ingress-nginx (retirado en marzo de 2026)**: antiguo controlador comunitario; elija un controlador con mantenimiento activo para instalaciones nuevas. F5 NGINX Ingress Controller es un proyecto independiente.
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

NetworkPolicy permite controlar la comunicación entre pods. De forma predeterminada, todos los pods pueden comunicarse entre sí, pero puede restringirlo mediante políticas de red.&#x20;

![Las solicitudes externas pasan por los pods de frontend, API y base de datos en el Namespace predeterminado; una NetworkPolicy db-network-policy protege los pods role=db, y Prometheus en el Namespace monitoring recopila métricas de los tres niveles.](../.gitbook/assets/en-basics-04-kubernetes-introduction-4.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-basics-04-kubernetes-introduction-4.html)

**Funciones principales**:

* Controlar la comunicación entre Pod
* Controlar la comunicación entre Namespace
* Controlar el tráfico entrante y saliente
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

Los permisos de NetworkPolicy se suman. La política permite el acceso desde role=api al puerto 3306 de la base de datos, y desde app=prometheus en monitoring al puerto 9104 de un exportador de base de datos instalado por separado. No permite que la base de datos se conecte a Prometheus en el puerto 9090. Adapte los selectores de salida DNS a la configuración real de DNS del clúster o de NodeLocal DNS.

### DNS

Las distribuciones de Kubernetes suelen incluir CoreDNS para el descubrimiento de servicios. Al editar su ConfigMap, conserve los ajustes que gestiona la distribución. El modo pods insecure del ejemplo genera registros heredados basados en IP sin verificar que el Pod exista. Use disabled si no necesita esos registros, o verified si acepta el consumo adicional de memoria y la observación de los Pod.

**Formato de nombres DNS**:

* **Service**: `<service-name>.<namespace>.svc.cluster.local`
* **Pod**: `<pod-ip-with-dashes>.<namespace>.pod.cluster.local` (registro IPv4; depende del modo pods de CoreDNS)

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

Una malla de servicios es una capa de infraestructura que administra la comunicación entre microservicios. Las mallas de servicios proporcionan administración del tráfico, seguridad y observabilidad.

**Principales mallas de servicios**:

* **Istio**: la malla de servicios más utilizada
* **Linkerd**: malla de servicios ligera
* **AWS App Mesh**: el soporte finalizó el 2026-09-30; AWS indica que su consola y sus recursos ya no son accesibles.

**Ejemplo de VirtualService de Istio**:

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

## Almacenamiento de Kubernetes {#kubernetes-storage}

Kubernetes ofrece varias opciones de almacenamiento para aplicaciones contenerizadas. Proporciona formas de conservar los datos aunque los pods se reinicien o se reprogramen.

![Almacenamiento de Kubernetes: Pod 1 y Pod 2 se vinculan a PersistentVolumes (pv-1, pv-3) mediante PersistentVolumeClaims (pvc-1, pvc-2); el StorageClass estándar aprovisiona los PV dinámicamente, y cada PV se asigna a un volumen de AWS EBS.](../.gitbook/assets/en-basics-04-kubernetes-introduction-5.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-basics-04-kubernetes-introduction-5.html)

### Volume

Un volumen es un directorio que puede montarse en los contenedores de un Pod para conservar datos durante su ciclo de vida. También permite compartir datos entre los contenedores del mismo Pod.

**Tipos principales de volumen**:

* **emptyDir**: comienza como un directorio vacío y se elimina al eliminar el Pod
* **hostPath**: monta en el Pod un directorio del sistema de archivos del nodo host
* **configMap**: monta ConfigMap como volumen
* **secret**: monta Secret como volumen
* **persistentVolumeClaim**: monta un volumen persistente en el Pod

**Ejemplo de volumen emptyDir**:

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

PersistentVolume es un objeto de API que representa un recurso de almacenamiento en el clúster. Existe independientemente de los pods y lo aprovisionan estáticamente los administradores o dinámicamente un aprovisionador de almacenamiento.

**Modos de acceso**:

* **ReadWriteOnce (RWO)**: puede montarse con acceso de lectura/escritura desde un único nodo
* **ReadOnlyMany (ROX)**: puede montarse en modo de solo lectura desde varios nodos
* **ReadWriteMany (RWX)**: puede montarse con acceso de lectura/escritura desde varios nodos
* **ReadWriteOncePod (RWOP)**: acceso de un único Pod para volúmenes CSI compatibles; RWO por sí solo sigue permitiendo varios Pod en el mismo nodo

Instale previamente el controlador CSI de EBS y configure los permisos de IAM. Utilice un ID de volumen existente y su zona de disponibilidad real; no reutilice un volumen que siga en uso en otro lugar. Estos ejemplos de almacenamiento son específicos de AWS. Para un clúster local, prepare su propio aprovisionador.

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

PersistentVolumeClaim es un objeto de API que representa una solicitud de almacenamiento de un usuario. Los pods acceden a los PV mediante los PVC.

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

**Ejemplo de Pod que usa PVC**:

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

StorageClass describe las «clases» de almacenamiento que ofrecen los administradores del clúster. Cada clase puede tener distintos niveles de servicio, políticas de copia de seguridad u otras políticas que los administradores definan.

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

El aprovisionamiento dinámico es una función que crea automáticamente PV cuando se solicitan PVC mediante clases de almacenamiento.

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

CSI proporciona una interfaz estándar entre Kubernetes y los sistemas de almacenamiento. Esto permite que los proveedores de almacenamiento desarrollen sus propios controladores de almacenamiento sin modificar el código de Kubernetes.

**Principales controladores CSI**:

* **Controlador CSI de AWS EBS**: administración de volúmenes de Amazon EBS
* **Controlador CSI de AWS EFS**: administración de sistemas de archivos de Amazon EFS
* **Controlador CSI de AWS FSx for Lustre**: administración de sistemas de archivos de FSx for Lustre
* **Controlador CSI de GCE PD**: administración de discos persistentes de Google Compute Engine
* **Controlador CSI de Azure Disk**: administración de discos de Azure

**StorageClass que usa un controlador CSI instalado**:

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

## Configuración y seguridad de Kubernetes {#kubernetes-configuration-and-security}

Kubernetes proporciona varios objetos y mecanismos para administrar la configuración y la seguridad de las aplicaciones.

### ConfigMap

ConfigMap es un objeto de API que almacena datos de configuración como pares clave-valor. Los pods pueden usar los datos de ConfigMap como variables de entorno, argumentos de línea de comandos o archivos de configuración.

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

Los valores de las variables de entorno no se actualizan automáticamente; vuelva a crear los Pod después de cambiarlos. Los cambios en volúmenes se propagan con cierto retraso y requieren que la aplicación recargue la configuración. Los montajes subPath no reciben esas actualizaciones.

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

Secret es un objeto de API que almacena información confidencial, como contraseñas, tokens y claves. Es similar a ConfigMap, pero está diseñado para datos confidenciales.

**Tipos de Secret**:

* **Opaque**: datos arbitrarios definidos por el usuario (predeterminado)
* **kubernetes.io/service-account-token**: Secret de token heredado de larga duración solicitado manualmente; se recomienda usar TokenRequest/tokens proyectados
* **kubernetes.io/dockercfg**: archivo \~/.dockercfg serializado
* **kubernetes.io/dockerconfigjson**: archivo \~/.docker/config.json serializado
* **kubernetes.io/basic-auth**: credenciales para autenticación básica
* **kubernetes.io/ssh-auth**: credenciales para autenticación SSH
* **kubernetes.io/tls**: datos para TLS de cliente o servidor

El campo data utiliza codificación base64, no cifrado. Proteja los Secret con RBAC y el cifrado en reposo adecuado para el clúster. EKS cifra de forma predeterminada todos los datos de la API de Kubernetes en las versiones 1.28 y posteriores. Sustituya los valores de demostración del ejemplo.

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

RBAC es un mecanismo para controlar el acceso a la API de Kubernetes. Otorga permisos específicos a usuarios o cuentas de servicio mediante Role y RoleBinding.

**Objetos principales de RBAC**:

* **Role**: define un conjunto de permisos dentro de un Namespace
* **ClusterRole**: define reglas reutilizables para recursos de ámbito de clúster o de Namespace; la vinculación determina dónde se aplican
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

ServiceAccount proporciona una identidad para los procesos que se ejecutan dentro de un pod. Los pods usan cuentas de servicio para comunicarse con la API de Kubernetes.

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

NetworkPolicy permite controlar la comunicación entre pods. De forma predeterminada, todos los pods pueden comunicarse entre sí, pero puede restringirlo mediante políticas de red.

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

PodSecurityPolicy se eliminó en la versión 1.25. Pod Security Admission aplica los estándares de seguridad de Pod mediante etiquetas de Namespace. SecurityContext configura la propia carga de trabajo; no reemplaza la aplicación de políticas de admisión.

**Ejemplo de SecurityContext de Pod**:

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

### Estándares de seguridad de Pod

Los estándares de seguridad de Pod proporcionan tres niveles de políticas que definen los requisitos de seguridad para los pods:

1. **Privileged**: sin restricciones; se permiten todas las funciones
2. **Baseline**: impide escaladas de privilegios conocidas
3. **Restricted**: restricciones estrictas que aplican las prácticas recomendadas

**Ejemplo de aplicación de los estándares de seguridad de Pod**:

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

## Kubernetes frente a Amazon EKS {#kubernetes-vs-amazon-eks}

Amazon EKS (Elastic Kubernetes Service) es el servicio de Kubernetes administrado de AWS. Expone la API estándar de Kubernetes y ofrece integraciones con AWS. Esta comparación se refiere a grupos de nodos EC2 convencionales. Las responsabilidades y las funciones admitidas difieren en Auto Mode, Fargate y Hybrid Nodes.

### Diferencias principales

| Característica            | Kubernetes autoadministrado                   | Amazon EKS                                                        |
| ------------------------ | ----------------------------------------------- | ----------------------------------------------------------------- |
| Administración del plano de control | El usuario lo administra directamente          | AWS lo administra                                                 |
| Alta disponibilidad     | El usuario debe configurarla                    | Proporcionada de forma predeterminada (implementada en varias zonas de disponibilidad) |
| Actualizaciones             | El usuario las realiza directamente             | AWS administra las actualizaciones del plano de control; coordina las actualizaciones de nodos/add-ons |
| Parches de seguridad         | El usuario los aplica directamente              | AWS aplica parches al plano de control; el despliegue gradual de AMI de nodos administrados sigue siendo responsabilidad del usuario (Auto Mode es distinto) |
| Autenticación           | Es necesario configurar distintas opciones      | Integrada con AWS IAM                                            |
| Redes               | Se requiere seleccionar y configurar un complemento CNI | Amazon VPC CNI se proporciona de forma predeterminada             |
| Balanceo de carga           | Se requiere configuración manual                | Integración con AWS Load Balancer Controller                      |
| Almacenamiento                  | Se requiere configurar un controlador de almacenamiento | Integración con controladores CSI de EBS, EFS y FSx                |
| Supervisión               | Se requiere configuración manual                | Integración con CloudWatch Container Insights                     |
| Costo                     | Infraestructura más esfuerzo operativo          | Costo del plano de control + costos de infraestructura            |

### Funciones adicionales de EKS

1. **Integración con AWS IAM**: integración de Kubernetes RBAC y AWS IAM
2. **AWS Load Balancer Controller**: integración de ALB y NLB con los servicios y el Ingress de Kubernetes
3. **Grupos de nodos administrados de EKS**: automatización de la administración del ciclo de vida de los nodos
4. **Perfiles de Fargate**: ejecución serverless de pods de Kubernetes
5. **Complemento VPC CNI**: integración con las redes de AWS VPC
6. **CloudWatch Container Insights**: supervisión y registro de contenedores
7. **AWS App Mesh**: el soporte finalizó el 2026-09-30; AWS indica que su consola y sus recursos ya no son accesibles
8. **AWS Distro for OpenTelemetry**: rastreo distribuido y supervisión
9. **Consola y CLI de EKS**: interfaces de administración
10. **EKS Blueprints**: configuración de clúster basada en prácticas recomendadas

### Componentes específicos de EKS

1. **Plano de control de EKS**: alta disponibilidad en varias zonas de disponibilidad
2. **AMI de nodo de EKS**: opciones AL2023/Bottlerocket/Windows proporcionadas por AWS y AMI compatibles suministradas por separado, como Ubuntu
3. **Grupos de nodos administrados de EKS**: flujos de trabajo de actualización de grupos de nodos; el escalado de nodos impulsado por las cargas de trabajo requiere un autoscaler
4. **EKS Fargate**: entorno de ejecución de contenedores serverless
5. **EKS Connector**: conecta clústeres externos de Kubernetes a la consola de AWS
6. **EKS Anywhere**: ejecuta clústeres compatibles con EKS en entornos locales
7. **EKS Distro**: distribución de Kubernetes administrada por AWS

### Integración con servicios de AWS

EKS se integra con los siguientes servicios de AWS:

1. **Amazon VPC**: infraestructura de red
2. **AWS IAM**: autenticación y autorización
3. **Amazon ECR**: repositorio de imágenes de contenedores
4. **AWS Load Balancer**: distribución del tráfico de aplicaciones
5. **Amazon EBS/EFS/FSx**: almacenamiento persistente
6. **AWS CloudWatch**: supervisión y registro
7. **AWS CloudTrail**: auditoría de la API de AWS; la auditoría de la API de Kubernetes requiere el registro de auditoría de EKS
8. **AWS KMS**: administración de claves de cifrado
9. **AWS WAF**: se puede asociar a puntos de entrada de aplicaciones compatibles, como ALB; no directamente al endpoint de la API de EKS
10. **AWS Shield**: protección frente a DDoS
11. **AWS X-Ray**: rastreo distribuido
12. **AWS App Mesh**: el soporte finalizó el 2026-09-30; las cargas de trabajo existentes necesitan migrarse
13. **AWS SageMaker**: cargas de trabajo de aprendizaje automático
14. **AWS Bedrock**: cargas de trabajo de IA generativa

## Primeros pasos con Kubernetes {#getting-started-with-kubernetes}

Hay varias formas de empezar a usar Kubernetes. A continuación, presentamos brevemente cómo iniciar Kubernetes en un entorno de desarrollo local y en AWS EKS.

### Entorno de desarrollo local

#### Minikube

Minikube ejecuta clústeres locales de Kubernetes y admite configuraciones de un solo nodo y de varios nodos.

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

Kind ejecuta clústeres locales mediante contenedores como nodos, con proveedores Docker/Podman/nerdctl compatibles.

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

1. Instale Docker Desktop
2. En Settings > Kubernetes, marque "Enable Kubernetes"
3. Haga clic en "Apply & Restart"

### AWS EKS

#### Crear un clúster de EKS con eksctl

eksctl es una sencilla herramienta CLI para crear y administrar clústeres de EKS.

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

#### Crear un clúster de EKS con la consola de administración de AWS

También puede crear clústeres de EKS mediante la consola de administración de AWS.

**Pasos**:

1. Inicie sesión en la consola de administración de AWS
2. Abra el servicio EKS
3. Haga clic en "Create cluster"
4. Configure el nombre del clúster, el rol de IAM, la VPC y las subredes
5. Configure los grupos de seguridad
6. Configure las opciones de registro
7. Cree el clúster
8. Añada los grupos de nodos

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

### Uso de la interfaz de Headlamp

Kubernetes Dashboard está archivado y carece de mantenimiento. Utilice Headlamp con una identidad cuyos permisos estén limitados por el RBAC existente. El ejemplo de Helm desactiva la vinculación automática de cluster-admin y el modo inseguro que utiliza un token compartido de ServiceAccount. Un administrador puede conceder por separado los permisos limitados que hagan falta.

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

Abra `http://localhost:8080` desde su equipo y siga el procedimiento de inicio de sesión de la versión instalada de Headlamp. Si expone la interfaz mediante Ingress público, configure TLS y autenticación por separado.

## Conclusión

Kubernetes automatiza el despliegue, el escalado y la administración de aplicaciones en contenedores. Esta guía ha presentado los conceptos siguientes:

### Arquitectura básica

* **Plano de control**: coordina el clúster mediante API Server, etcd, Scheduler y Controller Manager
* **Nodos de trabajo**: ejecutan las aplicaciones mediante kubelet, kube-proxy y el entorno de ejecución de contenedores
* **Configuración declarativa**: define el estado deseado para que Kubernetes ajuste el estado actual

### Objetos y recursos principales

* **Objetos básicos**: Pod, Service, Volume, Namespace
* **Recursos de cargas de trabajo**: Deployment, StatefulSet, DaemonSet, Job, CronJob
* **Configuración y seguridad**: ConfigMap, Secret, RBAC, ServiceAccount
* **Redes**: Service, Ingress, NetworkPolicy
* **Almacenamiento**: PersistentVolume, PersistentVolumeClaim, StorageClass

### Ruta de aprendizaje recomendada

**Paso 1: crear un entorno local**

* Cree un clúster local con minikube o kind
* Aprenda los comandos de kubectl
* Practique con objetos básicos: Pod, Deployment y Service

**Paso 2: dominar los conceptos básicos**

* Comprenda los recursos de cargas de trabajo y practique con ellos
* Administre la configuración con ConfigMap y Secret
* Configure las redes con Service e Ingress
* Administre el almacenamiento con PV y PVC

**Paso 3: aprender funciones avanzadas**

* RBAC y políticas de seguridad
* Escalado automático (HPA, VPA, Cluster Autoscaler)
* Supervisión y registro (Prometheus, Grafana)
* Malla de servicios (Istio, Linkerd)

**Paso 4: operaciones de producción**

* Utilice Amazon EKS u otro servicio de Kubernetes administrado
* Integre una canalización de CI/CD
* Prepare estrategias de recuperación ante desastres y copias de seguridad
* Optimice los costos y administre los recursos

### Próximos pasos

* **Análisis detallado de EKS**: funciones específicas de EKS (Fargate, VPC CNI, ALB Controller)
* **Redes avanzadas**: complementos CNI (Calico, Cilium)
* **Observabilidad**: métricas, registros, rastreo
* **GitOps**: ArgoCD, Flux
* **Refuerzo de la seguridad**: estándares de seguridad de Pod, políticas de red, OPA/Gatekeeper

Kubernetes sigue evolucionando y es una parte fundamental del desarrollo y la operación de aplicaciones nativas de la nube. Esta guía ofrece una base para empezar a trabajar con él.

### Recursos de aprendizaje adicionales

* **Documentación oficial**: la [documentación oficial de Kubernetes](https://kubernetes.io/docs/) proporciona la información más precisa y actualizada
* **Tutoriales interactivos**: hay prácticas disponibles en [Tutoriales de Kubernetes](https://kubernetes.io/docs/tutorials/)
* **Comunidad**: [Kubernetes Slack](https://slack.k8s.io/), [Reddit r/kubernetes](https://reddit.com/r/kubernetes)
* **Certificaciones**: CKA (Certified Kubernetes Administrator), CKAD (Certified Kubernetes Application Developer)
* **Comunidad coreana**: Kubernetes Korea User Group, AWS Korea User Group

## Cuestionario

Para comprobar lo que ha aprendido en este capítulo, responda el [cuestionario de introducción a Kubernetes](../quizzes/basics/04-kubernetes-introduction-quiz.md).

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
