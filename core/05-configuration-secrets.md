# 구성 및 시크릿

> **지원 버전**: Kubernetes 1.26, 1.27, 1.28  
> **마지막 업데이트**: 2023년 7월 20일

Kubernetes에서 구성 관리는 애플리케이션의 설정을 코드와 분리하여 관리하는 중요한 부분입니다. 이 장에서는 컨피그맵(ConfigMap), 시크릿(Secret), 환경 변수, 볼륨을 통한 구성 마운트 등 Kubernetes의 구성 관리 방법에 대해 자세히 알아보겠습니다.

## 한 눈에 보는 구성 관리

```mermaid
graph TD
    Admin[클러스터 관리자] -->|생성| CM[컨피그맵]
    Admin -->|생성| Secret[시크릿]
    CM -->|환경 변수로 제공| Pod1[파드]
    Secret -->|환경 변수로 제공| Pod1
    CM -->|볼륨으로 마운트| Pod2[파드]
    Secret -->|볼륨으로 마운트| Pod2
    Secret -->|이미지 풀 시크릿| Pod3[파드]
    
    %% 스타일 정의
    classDef k8sComponent fill:#326CE5,stroke:#333,stroke-width:1px,color:white;
    classDef userApp fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;
    classDef dataStore fill:#3B48CC,stroke:#333,stroke-width:1px,color:white;
    classDef user fill:#f9f9f9,stroke:#333,stroke-width:1px,color:black;
    
    %% 클래스 적용
    class Admin user;
    class CM,Secret k8sComponent;
    class Pod1,Pod2,Pod3 userApp;
```

## 목차

1. [컨피그맵(ConfigMap)](#컨피그맵configmap)
2. [시크릿(Secret)](#시크릿secret)
3. [환경 변수](#환경-변수)
4. [볼륨을 통한 구성 마운트](#볼륨을-통한-구성-마운트)
5. [구성 모범 사례](#구성-모범-사례)
6. [외부 구성 관리 도구](#외부-구성-관리-도구)

## 컨피그맵(ConfigMap)

> **핵심 개념**: 컨피그맵은 키-값 쌍 형태로 구성 데이터를 저장하는 객체로, 애플리케이션 코드와 구성을 분리합니다.

컨피그맵은 키-값 쌍의 형태로 구성 데이터를 저장하는 API 객체입니다. 컨피그맵을 사용하면 컨테이너 이미지에서 구성 데이터를 분리하여 애플리케이션을 더 쉽게 이식할 수 있습니다.

### 컨피그맵 사용 방법

```mermaid
graph TD
    CM[컨피그맵] -->|환경 변수| Pod1[파드]
    CM -->|볼륨 마운트| Pod2[파드]
    CM -->|명령줄 인수| Pod3[파드]
    
    subgraph "컨피그맵 데이터"
        CMData1["key1: value1"]
        CMData2["key2: value2"]
        CMData3["config.properties: 파일 내용"]
    end
    
    subgraph "환경 변수 사용"
        Env1["env.key1 = value1"]
        Env2["env.key2 = value2"]
    end
    
    subgraph "볼륨 마운트 사용"
        Vol1["/etc/config/key1"]
        Vol2["/etc/config/key2"]
        Vol3["/etc/config/config.properties"]
    end
    
    CM --- CMData1
    CM --- CMData2
    CM --- CMData3
    
    Pod1 --- Env1
    Pod1 --- Env2
    
    Pod2 --- Vol1
    Pod2 --- Vol2
    Pod2 --- Vol3
    
    %% 스타일 정의
    classDef k8sComponent fill:#326CE5,stroke:#333,stroke-width:1px,color:white;
    classDef userApp fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;
    
    %% 클래스 적용
    class CM k8sComponent;
    class Pod1,Pod2,Pod3 userApp;
```

### 컨피그맵 생성

컨피그맵은 여러 가지 방법으로 생성할 수 있습니다:

#### 명령형 방식

```bash
# 리터럴 값으로 생성
kubectl create configmap my-config --from-literal=key1=value1 --from-literal=key2=value2

# 파일에서 생성
kubectl create configmap my-config --from-file=config.properties

# 디렉토리에서 생성
kubectl create configmap my-config --from-file=config-dir/
```

#### 선언형 방식

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: my-config
data:
  # 단순 키-값 쌍
  key1: value1
  key2: value2
  # 파일과 같은 구성
  config.properties: |
    property1=value1
    property2=value2
  # JSON 구성
  config.json: |
    {
      "property1": "value1",
      "property2": "value2"
    }
```

### 컨피그맵 사용

컨피그맵은 다음과 같은 방법으로 포드에서 사용할 수 있습니다:

#### 환경 변수로 사용

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: configmap-pod
spec:
  containers:
  - name: test-container
    image: busybox
    command: [ "/bin/sh", "-c", "env" ]
    env:
    # 단일 키-값 쌍 사용
    - name: SPECIAL_KEY
      valueFrom:
        configMapKeyRef:
          name: my-config
          key: key1
    # 모든 키-값 쌍을 환경 변수로 사용
    envFrom:
    - configMapRef:
        name: my-config
  restartPolicy: Never
```

#### 볼륨으로 마운트

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: configmap-pod
spec:
  containers:
  - name: test-container
    image: busybox
    command: [ "/bin/sh", "-c", "ls /etc/config/" ]
    volumeMounts:
    - name: config-volume
      mountPath: /etc/config
  volumes:
  - name: config-volume
    configMap:
      name: my-config
  restartPolicy: Never
```

#### 특정 키만 마운트

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: configmap-pod
spec:
  containers:
  - name: test-container
    image: busybox
    command: [ "/bin/sh", "-c", "cat /etc/config/key1" ]
    volumeMounts:
    - name: config-volume
      mountPath: /etc/config
  volumes:
  - name: config-volume
    configMap:
      name: my-config
      items:
      - key: key1
        path: key1
  restartPolicy: Never
```

### 컨피그맵 업데이트

컨피그맵을 업데이트하면 볼륨으로 마운트된 컨피그맵의 내용이 자동으로 업데이트됩니다. 그러나 환경 변수로 사용된 컨피그맵은 포드가 재시작되어야 업데이트됩니다.

```bash
kubectl edit configmap my-config
```

또는

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: my-config
data:
  key1: updated-value1
  key2: value2
```

```bash
kubectl apply -f updated-configmap.yaml
```

## 시크릿(Secret)

시크릿은 암호, OAuth 토큰, SSH 키와 같은 민감한 정보를 저장하는 API 객체입니다. 시크릿은 컨피그맵과 유사하지만, 민감한 데이터를 저장하기 위한 추가적인 보안 기능을 제공합니다.

```mermaid
graph LR
    Secret[시크릿] -->|환경 변수| Pod1[파드]
    Secret -->|볼륨 마운트| Pod2[파드]
    Secret -->|이미지 풀 시크릿| Pod3[파드]
    
    subgraph "시크릿 유형"
        ST1["Opaque (기본)"]
        ST2["kubernetes.io/tls"]
        ST3["kubernetes.io/dockerconfigjson"]
        ST4["kubernetes.io/basic-auth"]
    end
    
    subgraph "저장 방식"
        Store1["base64 인코딩"]
        Store2["etcd 암호화 (선택)"]
    end
    
    Secret --- ST1
    Secret --- ST2
    Secret --- ST3
    Secret --- ST4
    
    Secret --- Store1
    Secret --- Store2
    
    %% 스타일 정의
    classDef k8sComponent fill:#326CE5,stroke:#333,stroke-width:1px,color:white;
    classDef userApp fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;
    classDef dataStore fill:#3B48CC,stroke:#333,stroke-width:1px,color:white;
    
    %% 클래스 적용
    class Secret k8sComponent;
    class Pod1,Pod2,Pod3 userApp;
    class Store1,Store2 dataStore;
```

### 시크릿 유형

Kubernetes는 다양한 유형의 시크릿을 제공합니다:

- **Opaque**: 기본 유형으로, 임의의 사용자 정의 데이터를 저장합니다.
- **kubernetes.io/service-account-token**: 서비스 계정 토큰을 저장합니다.
- **kubernetes.io/dockercfg**: `.dockercfg` 파일의 직렬화된 형태를 저장합니다.
- **kubernetes.io/dockerconfigjson**: `.docker/config.json` 파일의 직렬화된 형태를 저장합니다.
- **kubernetes.io/basic-auth**: 기본 인증을 위한 자격 증명을 저장합니다.
- **kubernetes.io/ssh-auth**: SSH 인증을 위한 자격 증명을 저장합니다.
- **kubernetes.io/tls**: TLS 인증서와 키를 저장합니다.
- **bootstrap.kubernetes.io/token**: 부트스트랩 토큰 데이터를 저장합니다.

### 시크릿 생성

시크릿은 여러 가지 방법으로 생성할 수 있습니다:

#### 명령형 방식

```bash
# 리터럴 값으로 생성
kubectl create secret generic my-secret --from-literal=username=admin --from-literal=password=secret

# 파일에서 생성
kubectl create secret generic my-secret --from-file=username.txt --from-file=password.txt

# TLS 시크릿 생성
kubectl create secret tls my-tls-secret --cert=path/to/cert.crt --key=path/to/key.key

# Docker 레지스트리 시크릿 생성
kubectl create secret docker-registry my-registry-secret \
  --docker-server=DOCKER_REGISTRY_SERVER \
  --docker-username=DOCKER_USER \
  --docker-password=DOCKER_PASSWORD \
  --docker-email=DOCKER_EMAIL
```

#### 선언형 방식

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: my-secret
type: Opaque
data:
  # base64로 인코딩된 값
  username: YWRtaW4=  # admin
  password: c2VjcmV0  # secret
```

또는 `stringData` 필드를 사용하여 인코딩되지 않은 값을 제공할 수 있습니다:

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: my-secret
type: Opaque
stringData:
  # 인코딩되지 않은 값
  username: admin
  password: secret
```

### 시크릿 사용

시크릿은 다음과 같은 방법으로 포드에서 사용할 수 있습니다:

#### 환경 변수로 사용

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: secret-pod
spec:
  containers:
  - name: test-container
    image: busybox
    command: [ "/bin/sh", "-c", "env" ]
    env:
    # 단일 키-값 쌍 사용
    - name: USERNAME
      valueFrom:
        secretKeyRef:
          name: my-secret
          key: username
    # 모든 키-값 쌍을 환경 변수로 사용
    envFrom:
    - secretRef:
        name: my-secret
  restartPolicy: Never
```

#### 볼륨으로 마운트

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: secret-pod
spec:
  containers:
  - name: test-container
    image: busybox
    command: [ "/bin/sh", "-c", "ls /etc/secret/" ]
    volumeMounts:
    - name: secret-volume
      mountPath: /etc/secret
  volumes:
  - name: secret-volume
    secret:
      secretName: my-secret
  restartPolicy: Never
```

#### 이미지 풀 시크릿

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: private-image-pod
spec:
  containers:
  - name: private-image-container
    image: private-registry.example.com/my-app:v1
  imagePullSecrets:
  - name: my-registry-secret
```

### 시크릿 보안 고려 사항

시크릿은 기본적으로 base64로 인코딩되어 있지만, 이는 암호화가 아닙니다. 시크릿의 보안을 강화하기 위해 다음과 같은 방법을 고려할 수 있습니다:

1. **etcd 암호화**: etcd에 저장된 시크릿을 암호화합니다.
2. **RBAC**: 시크릿에 대한 접근을 제한합니다.
3. **네트워크 정책**: 시크릿에 접근할 수 있는 포드를 제한합니다.
4. **외부 시크릿 관리 도구**: AWS Secrets Manager, HashiCorp Vault 등의 외부 시크릿 관리 도구를 사용합니다.

#### etcd 암호화 구성

```yaml
apiVersion: apiserver.config.k8s.io/v1
kind: EncryptionConfiguration
resources:
  - resources:
    - secrets
    providers:
    - aescbc:
        keys:
        - name: key1
          secret: <base64 encoded key>
    - identity: {}
```

## 환경 변수

환경 변수는 컨테이너에 구성 정보를 전달하는 간단한 방법입니다. Kubernetes는 여러 가지 방법으로 환경 변수를 설정할 수 있습니다.

```mermaid
graph TD
    Pod[파드] -->|포함| Container[컨테이너]
    
    subgraph "환경 변수 소스"
        Direct["직접 설정"]
        CM["컨피그맵"]
        Secret["시크릿"]
        DownAPI["다운워드 API"]
    end
    
    Direct -->|env| Container
    CM -->|valueFrom.configMapKeyRef| Container
    CM -->|envFrom.configMapRef| Container
    Secret -->|valueFrom.secretKeyRef| Container
    Secret -->|envFrom.secretRef| Container
    DownAPI -->|valueFrom.fieldRef| Container
    DownAPI -->|valueFrom.resourceFieldRef| Container
    
    %% 스타일 정의
    classDef k8sComponent fill:#326CE5,stroke:#333,stroke-width:1px,color:white;
    classDef userApp fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;
    
    %% 클래스 적용
    class Pod,Container userApp;
    class CM,Secret,DownAPI k8sComponent;
    class Direct k8sComponent;
```

### 직접 설정

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: env-pod
spec:
  containers:
  - name: test-container
    image: busybox
    command: [ "/bin/sh", "-c", "env" ]
    env:
    - name: ENVIRONMENT
      value: "production"
    - name: LOG_LEVEL
      value: "INFO"
  restartPolicy: Never
```

### 컨피그맵에서 설정

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: env-pod
spec:
  containers:
  - name: test-container
    image: busybox
    command: [ "/bin/sh", "-c", "env" ]
    env:
    - name: ENVIRONMENT
      valueFrom:
        configMapKeyRef:
          name: my-config
          key: environment
  restartPolicy: Never
```

### 시크릿에서 설정

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: env-pod
spec:
  containers:
  - name: test-container
    image: busybox
    command: [ "/bin/sh", "-c", "env" ]
    env:
    - name: DATABASE_PASSWORD
      valueFrom:
        secretKeyRef:
          name: my-secret
          key: password
  restartPolicy: Never
```

### 다운워드 API를 통한 설정

다운워드 API를 사용하면 포드 및 컨테이너 정보를 환경 변수로 노출할 수 있습니다.

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: downward-api-pod
  labels:
    app: myapp
spec:
  containers:
  - name: test-container
    image: busybox
    command: [ "/bin/sh", "-c", "env" ]
    env:
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
    - name: CONTAINER_CPU_REQUEST
      valueFrom:
        resourceFieldRef:
          containerName: test-container
          resource: requests.cpu
  restartPolicy: Never
```

## 볼륨을 통한 구성 마운트

볼륨을 통해 구성 파일을 컨테이너에 마운트하는 방법은 환경 변수보다 더 유연한 구성 관리 방법을 제공합니다.

```mermaid
graph TD
    Pod[파드] -->|포함| Container[컨테이너]
    Pod -->|정의| Volumes[볼륨]
    Container -->|마운트| VolumeMounts[볼륨 마운트]
    VolumeMounts -->|참조| Volumes
    
    subgraph "볼륨 소스"
        CM["컨피그맵"]
        Secret["시크릿"]
    end
    
    Volumes -->|configMap| CM
    Volumes -->|secret| Secret
    
    subgraph "마운트 옵션"
        MO1["전체 볼륨 마운트"]
        MO2["특정 키만 마운트"]
        MO3["읽기 전용 마운트"]
        MO4["서브패스 마운트"]
    end
    
    VolumeMounts --- MO1
    VolumeMounts --- MO2
    VolumeMounts --- MO3
    VolumeMounts --- MO4
    
    %% 스타일 정의
    classDef k8sComponent fill:#326CE5,stroke:#333,stroke-width:1px,color:white;
    classDef userApp fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;
    
    %% 클래스 적용
    class Pod,Container userApp;
    class Volumes,VolumeMounts,CM,Secret k8sComponent;
```

### 컨피그맵 볼륨

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: configmap-volume-pod
spec:
  containers:
  - name: test-container
    image: busybox
    command: [ "/bin/sh", "-c", "ls -la /etc/config" ]
    volumeMounts:
    - name: config-volume
      mountPath: /etc/config
  volumes:
  - name: config-volume
    configMap:
      name: my-config
  restartPolicy: Never
```

### 시크릿 볼륨

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: secret-volume-pod
spec:
  containers:
  - name: test-container
    image: busybox
    command: [ "/bin/sh", "-c", "ls -la /etc/secret" ]
    volumeMounts:
    - name: secret-volume
      mountPath: /etc/secret
  volumes:
  - name: secret-volume
    secret:
      secretName: my-secret
  restartPolicy: Never
```

### 특정 파일 마운트

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: specific-file-pod
spec:
  containers:
  - name: test-container
    image: busybox
    command: [ "/bin/sh", "-c", "cat /etc/config/config.properties" ]
    volumeMounts:
    - name: config-volume
      mountPath: /etc/config
  volumes:
  - name: config-volume
    configMap:
      name: my-config
      items:
      - key: config.properties
        path: config.properties
  restartPolicy: Never
```

### 읽기 전용 마운트

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: readonly-mount-pod
spec:
  containers:
  - name: test-container
    image: busybox
    command: [ "/bin/sh", "-c", "ls -la /etc/config" ]
    volumeMounts:
    - name: config-volume
      mountPath: /etc/config
      readOnly: true
  volumes:
  - name: config-volume
    configMap:
      name: my-config
  restartPolicy: Never
```

### 서브패스 마운트

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: subpath-mount-pod
spec:
  containers:
  - name: test-container
    image: busybox
    command: [ "/bin/sh", "-c", "cat /etc/nginx/nginx.conf" ]
    volumeMounts:
    - name: config-volume
      mountPath: /etc/nginx/nginx.conf
      subPath: nginx.conf
  volumes:
  - name: config-volume
    configMap:
      name: my-config
  restartPolicy: Never
```

## 구성 모범 사례

Kubernetes에서 구성을 관리할 때 다음과 같은 모범 사례를 고려하세요:

### 1. 구성과 코드 분리

애플리케이션 코드와 구성을 분리하여 관리하세요. 이렇게 하면 구성을 변경할 때 애플리케이션을 다시 빌드하지 않아도 됩니다.

### 2. 환경별 구성 관리

개발, 테스트, 프로덕션 등 다양한 환경에 대한 구성을 별도로 관리하세요. 네임스페이스를 사용하여 환경을 분리하고, 환경별로 다른 컨피그맵과 시크릿을 사용할 수 있습니다.

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: my-config
  namespace: development
data:
  environment: development
  log_level: DEBUG
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: my-config
  namespace: production
data:
  environment: production
  log_level: INFO
```

### 3. 민감한 정보는 시크릿 사용

암호, API 키, 인증서 등의 민감한 정보는 항상 시크릿을 사용하여 저장하세요. 컨피그맵은 민감하지 않은 구성 데이터에만 사용하세요.

### 4. 불변성 유지

구성을 변경할 때는 새 버전을 생성하고, 기존 버전을 수정하지 마세요. 이렇게 하면 롤백이 쉬워지고, 구성 변경 이력을 추적할 수 있습니다.

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: my-config-v1
data:
  # 구성 데이터
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: my-config-v2
data:
  # 업데이트된 구성 데이터
```

### 5. 구성 변경 시 포드 재시작

환경 변수로 사용된 구성은 포드가 재시작되어야 업데이트됩니다. 디플로이먼트를 사용하여 포드를 롤링 업데이트하세요.

```bash
kubectl rollout restart deployment/my-deployment
```

### 6. 구성 검증

구성을 적용하기 전에 유효성을 검증하세요. 잘못된 구성은 애플리케이션 장애를 일으킬 수 있습니다.

### 7. 구성 문서화

구성 옵션과 그 영향을 문서화하세요. 이는 팀원들이 구성을 이해하고 관리하는 데 도움이 됩니다.

## Amazon EKS에서의 구성 관리

Amazon EKS에서는 Kubernetes의 기본 구성 관리 기능 외에도 AWS의 다양한 서비스를 활용하여 구성과 시크릿을 관리할 수 있습니다. 이 섹션에서는 EKS에서 구성을 관리하는 다양한 방법과 AWS 서비스와의 통합에 대해 알아보겠습니다.

```mermaid
graph TD
    EKS[Amazon EKS] -->|사용| K8s[Kubernetes 구성]
    EKS -->|통합| AWS[AWS 서비스]
    
    subgraph "Kubernetes 구성"
        CM["컨피그맵"]
        Secret["시크릿"]
    end
    
    subgraph "AWS 서비스"
        SM["AWS Secrets Manager"]
        PS["AWS Parameter Store"]
        AC["AWS AppConfig"]
        KMS["AWS KMS"]
        IAM["AWS IAM"]
    end
    
    subgraph "통합 도구"
        ESO["External Secrets Operator"]
        ASCP["AWS Secrets and Configuration Provider"]
        IRSA["IAM Roles for Service Accounts"]
        ACK["AWS Controllers for Kubernetes"]
    end
    
    K8s --- CM
    K8s --- Secret
    
    AWS --- SM
    AWS --- PS
    AWS --- AC
    AWS --- KMS
    AWS --- IAM
    
    SM -->|통합| ESO
    PS -->|통합| ASCP
    IAM -->|통합| IRSA
    AWS -->|통합| ACK
    
    ESO -->|생성| Secret
    ASCP -->|마운트| Secret
    IRSA -->|권한 부여| Pod[파드]
    ACK -->|관리| AWS
    
    KMS -->|암호화| Secret
    
    %% 스타일 정의
    classDef k8sComponent fill:#326CE5,stroke:#333,stroke-width:1px,color:white;
    classDef userApp fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;
    classDef awsService fill:#FF9900,stroke:#333,stroke-width:1px,color:black;
    classDef integrationTool fill:#3B48CC,stroke:#333,stroke-width:1px,color:white;
    
    %% 클래스 적용
    class EKS,K8s,CM,Secret k8sComponent;
    class Pod userApp;
    class AWS,SM,PS,AC,KMS,IAM awsService;
    class ESO,ASCP,IRSA,ACK integrationTool;
```

### AWS Secrets Manager 통합

AWS Secrets Manager는 데이터베이스 자격 증명, API 키 및 기타 시크릿 정보를 안전하게 저장하고 관리할 수 있는 서비스입니다. EKS에서는 External Secrets Operator나 AWS Secrets and Configuration Provider(ASCP)를 사용하여 AWS Secrets Manager의 시크릿을 Kubernetes 시크릿으로 동기화할 수 있습니다.

#### External Secrets Operator 설치

```bash
# Helm을 사용하여 External Secrets Operator 설치
helm repo add external-secrets https://charts.external-secrets.io
helm install external-secrets external-secrets/external-secrets \
  --namespace external-secrets \
  --create-namespace
```

#### SecretStore 생성

```yaml
apiVersion: external-secrets.io/v1beta1
kind: SecretStore
metadata:
  name: aws-secretsmanager
  namespace: my-namespace
spec:
  provider:
    aws:
      service: SecretsManager
      region: us-west-2
      auth:
        jwt:
          serviceAccountRef:
            name: my-serviceaccount
```

#### ExternalSecret 생성

```yaml
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: database-credentials
  namespace: my-namespace
spec:
  refreshInterval: 1h
  secretStoreRef:
    name: aws-secretsmanager
    kind: SecretStore
  target:
    name: db-credentials
  data:
  - secretKey: username
    remoteRef:
      key: prod/db/credentials
      property: username
  - secretKey: password
    remoteRef:
      key: prod/db/credentials
      property: password
```

#### IRSA(IAM Roles for Service Accounts) 설정

External Secrets Operator가 AWS Secrets Manager에 접근하려면 적절한 IAM 권한이 필요합니다. IRSA를 사용하여 Kubernetes 서비스 계정에 IAM 역할을 연결할 수 있습니다.

```bash
# OIDC 제공자 생성
eksctl utils associate-iam-oidc-provider \
  --cluster my-cluster \
  --approve

# IAM 역할 및 서비스 계정 생성
eksctl create iamserviceaccount \
  --cluster my-cluster \
  --namespace my-namespace \
  --name my-serviceaccount \
  --attach-policy-arn arn:aws:iam::aws:policy/SecretsManagerReadWrite \
  --approve
```

### AWS Parameter Store 활용

AWS Systems Manager Parameter Store는 구성 데이터와 시크릿 값을 계층적으로 저장하고 관리할 수 있는 서비스입니다. Parameter Store는 Secrets Manager보다 비용이 저렴하며, 간단한 구성 값을 저장하는 데 적합합니다.

#### ASCP(AWS Secrets and Configuration Provider) 설치

```bash
# ASCP 설치
helm repo add secrets-store-csi-driver https://kubernetes-sigs.github.io/secrets-store-csi-driver/charts
helm install csi-secrets-store secrets-store-csi-driver/secrets-store-csi-driver \
  --namespace kube-system

# AWS 제공자 설치
kubectl apply -f https://raw.githubusercontent.com/aws/secrets-store-csi-driver-provider-aws/main/deployment/aws-provider-installer.yaml
```

#### SecretProviderClass 생성

```yaml
apiVersion: secrets-store.csi.x-k8s.io/v1
kind: SecretProviderClass
metadata:
  name: aws-parameters
  namespace: my-namespace
spec:
  provider: aws
  parameters:
    objects: |
      - objectName: /my-app/config/log-level
        objectType: ssmparameter
      - objectName: /my-app/config/environment
        objectType: ssmparameter
```

#### 포드에서 Parameter Store 값 사용

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: parameter-store-pod
  namespace: my-namespace
spec:
  containers:
  - name: app
    image: my-app:latest
    volumeMounts:
    - name: parameters-store-volume
      mountPath: "/mnt/parameters"
      readOnly: true
  volumes:
  - name: parameters-store-volume
    csi:
      driver: secrets-store.csi.k8s.io
      readOnly: true
      volumeAttributes:
        secretProviderClass: aws-parameters
```

### AWS AppConfig를 사용한 동적 구성

AWS AppConfig는 애플리케이션 구성을 관리하고 배포하는 서비스입니다. AppConfig를 사용하면 애플리케이션을 재배포하지 않고도 구성을 동적으로 업데이트할 수 있습니다.

#### AppConfig Agent 사이드카 패턴

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: my-app
  namespace: my-namespace
spec:
  replicas: 3
  selector:
    matchLabels:
      app: my-app
  template:
    metadata:
      labels:
        app: my-app
    spec:
      containers:
      - name: app
        image: my-app:latest
        env:
        - name: CONFIG_PATH
          value: /config/config.json
        volumeMounts:
        - name: config-volume
          mountPath: /config
      - name: appconfig-agent
        image: public.ecr.aws/aws-appconfig/aws-appconfig-agent:2.0
        env:
        - name: AWS_APPCONFIG_EXTENSION_POLL_INTERVAL_SECONDS
          value: "45"
        - name: AWS_APPCONFIG_EXTENSION_POLL_TIMEOUT_SECONDS
          value: "15"
        - name: AWS_APPCONFIG_EXTENSION_HTTP_PORT
          value: "2772"
        - name: AWS_APPCONFIG_EXTENSION_PREFETCH_LIST
          value: '{"Applications":[{"ApplicationId":"MyApp","Environments":[{"EnvironmentId":"Production","Configurations":[{"ConfigurationProfileId":"MyConfig","VersionNumber":null}]}]}]}'
        volumeMounts:
        - name: config-volume
          mountPath: /config
      volumes:
      - name: config-volume
        emptyDir: {}
```

### EKS Fargate 프로파일을 사용한 구성

EKS Fargate를 사용하면 노드를 관리할 필요 없이 Kubernetes 포드를 실행할 수 있습니다. Fargate 프로파일을 사용하여 포드의 실행 환경을 구성할 수 있습니다.

```yaml
apiVersion: eks.amazonaws.com/v1beta1
kind: FargateProfile
metadata:
  name: my-profile
  namespace: my-namespace
spec:
  clusterName: my-cluster
  podExecutionRoleArn: arn:aws:iam::123456789012:role/my-pod-execution-role
  selectors:
  - namespace: my-namespace
    labels:
      environment: production
  subnets:
  - subnet-1234567890abcdef0
  - subnet-0abcdef1234567890
```

### AWS KMS를 사용한 시크릿 암호화

Kubernetes 시크릿은 기본적으로 base64로 인코딩되어 있지만, 이는 암호화가 아닙니다. AWS KMS(Key Management Service)를 사용하여 EKS 클러스터의 시크릿을 암호화할 수 있습니다.

#### KMS 키 생성

```bash
# KMS 키 생성
aws kms create-key --description "EKS Secret Encryption Key"

# 키 ID 저장
KEY_ID=$(aws kms create-key --query KeyMetadata.KeyId --output text)

# 키 별칭 생성
aws kms create-alias --alias-name alias/eks-secrets --target-key-id $KEY_ID
```

#### EKS 클러스터에 암호화 구성 적용

```bash
# 암호화 구성 적용
aws eks update-cluster-config \
  --name my-cluster \
  --encryption-config '[{"resources":["secrets"],"provider":{"keyArn":"arn:aws:kms:us-west-2:123456789012:key/'$KEY_ID'"}}]'
```

### AWS IAM을 사용한 시크릿 접근 제어

IRSA(IAM Roles for Service Accounts)를 사용하여 Kubernetes 서비스 계정에 IAM 역할을 연결하면, 포드가 AWS 서비스에 안전하게 접근할 수 있습니다.

#### 서비스 계정 생성

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: my-service-account
  namespace: my-namespace
  annotations:
    eks.amazonaws.com/role-arn: arn:aws:iam::123456789012:role/my-iam-role
```

#### 포드에서 서비스 계정 사용

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: my-pod
  namespace: my-namespace
spec:
  serviceAccountName: my-service-account
  containers:
  - name: app
    image: my-app:latest
```

### EKS 구성 모범 사례

EKS에서 구성을 관리할 때 다음과 같은 모범 사례를 고려하세요:

1. **IRSA 사용**: AWS 서비스에 접근할 때는 항상 IRSA를 사용하여 포드에 최소 권한을 부여하세요.

2. **시크릿 암호화**: KMS를 사용하여 EKS 클러스터의 시크릿을 암호화하세요.

3. **외부 시크릿 관리**: 민감한 정보는 AWS Secrets Manager나 Parameter Store와 같은 외부 시크릿 관리 서비스를 사용하여 관리하세요.

4. **구성 버전 관리**: AWS AppConfig나 Parameter Store를 사용하여 구성 버전을 관리하세요.

5. **환경별 구성 분리**: 개발, 테스트, 프로덕션 환경에 대한 구성을 분리하여 관리하세요. Kubernetes 네임스페이스와 AWS 리소스 태그를 활용하세요.

6. **IAM 정책 최소화**: AWS 서비스에 접근할 때는 최소 권한 원칙을 따르세요.

7. **구성 자동화**: AWS CloudFormation, AWS CDK, Terraform 등의 도구를 사용하여 구성 관리를 자동화하세요.

### EKS 구성 관리 도구

EKS에서 구성을 관리하는 데 도움이 되는 도구들을 살펴보겠습니다:

#### AWS Controllers for Kubernetes(ACK)

ACK는 Kubernetes에서 AWS 리소스를 관리할 수 있는 도구입니다. ACK를 사용하면 Kubernetes 매니페스트를 통해 AWS 리소스를 생성하고 관리할 수 있습니다.

```yaml
apiVersion: secretsmanager.services.k8s.aws/v1alpha1
kind: Secret
metadata:
  name: my-secret
spec:
  name: my-secret
  description: "My secret created via ACK"
  forceDeleteWithoutRecovery: true
  generateSecretString:
    excludeCharacters: "\"@/\\"
    excludePunctuation: true
    includeSpace: false
    passwordLength: 16
```

#### eksctl

eksctl은 EKS 클러스터를 생성하고 관리하는 명령줄 도구입니다. eksctl을 사용하여 클러스터 구성을 관리할 수 있습니다.

```yaml
# cluster.yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: my-cluster
  region: us-west-2
secretsEncryption:
  keyARN: arn:aws:kms:us-west-2:123456789012:key/1234abcd-12ab-34cd-56ef-1234567890ab
```

```bash
eksctl create cluster -f cluster.yaml
```

#### AWS CDK

AWS CDK(Cloud Development Kit)는 프로그래밍 언어를 사용하여 AWS 리소스를 정의하는 도구입니다. CDK를 사용하여 EKS 클러스터와 관련 리소스를 정의할 수 있습니다.

```typescript
import * as cdk from 'aws-cdk-lib';
import * as eks from 'aws-cdk-lib/aws-eks';
import * as iam from 'aws-cdk-lib/aws-iam';

const app = new cdk.App();
const stack = new cdk.Stack(app, 'EksStack');

// EKS 클러스터 생성
const cluster = new eks.Cluster(stack, 'Cluster', {
  version: eks.KubernetesVersion.V1_21,
  secretsEncryptionKey: new kms.Key(stack, 'Key'),
});

// 서비스 계정 생성
const serviceAccount = cluster.addServiceAccount('ServiceAccount', {
  name: 'my-service-account',
  namespace: 'my-namespace',
});

// IAM 정책 연결
serviceAccount.role.addManagedPolicy(
  iam.ManagedPolicy.fromAwsManagedPolicyName('SecretsManagerReadWrite')
);
```

## 결론

이 장에서는 Kubernetes의 구성 관리 방법에 대해 알아보았습니다. 컨피그맵과 시크릿은 애플리케이션 구성을 관리하는 기본적인 방법을 제공하며, 환경 변수와 볼륨을 통해 이러한 구성을 컨테이너에 전달할 수 있습니다. 또한, 구성 관리의 모범 사례와 외부 구성 관리 도구에 대해서도 살펴보았습니다.

Amazon EKS 환경에서는 Kubernetes의 기본 구성 관리 기능과 함께 AWS의 다양한 서비스를 활용하여 더욱 강력하고 안전한 구성 관리가 가능합니다. AWS Secrets Manager, Parameter Store, KMS, IAM 등의 서비스를 통합하여 시크릿을 안전하게 관리하고, IRSA를 통해 포드에 최소 권한을 부여할 수 있습니다. 또한, AWS AppConfig를 사용하여 애플리케이션을 재배포하지 않고도 구성을 동적으로 업데이트할 수 있습니다.

효과적인 구성 관리는 Kubernetes 애플리케이션의 유지 관리성, 확장성 및 보안을 향상시키는 데 중요합니다. 애플리케이션의 요구 사항에 맞는 적절한 구성 관리 전략을 선택하고, 모범 사례를 따르는 것이 중요합니다. 특히 EKS 환경에서는 AWS 서비스와의 통합을 통해 더욱 강력한 구성 관리 솔루션을 구축할 수 있습니다.

다음 장에서는 Kubernetes의 보안에 대해 알아보겠습니다.

## 참고 자료

- [Kubernetes 공식 문서 - ConfigMaps](https://kubernetes.io/docs/concepts/configuration/configmap/)
- [Kubernetes 공식 문서 - Secrets](https://kubernetes.io/docs/concepts/configuration/secret/)
- [Kubernetes 공식 문서 - Environment Variables](https://kubernetes.io/docs/tasks/inject-data-application/define-environment-variable-container/)
- [Kubernetes 공식 문서 - Configure a Pod to Use a ConfigMap](https://kubernetes.io/docs/tasks/configure-pod-container/configure-pod-configmap/)
- [Kubernetes 공식 문서 - Distribute Credentials Securely Using Secrets](https://kubernetes.io/docs/tasks/inject-data-application/distribute-credentials-secure/)
- [Helm 공식 문서](https://helm.sh/docs/)
- [Kustomize 공식 문서](https://kustomize.io/)
- [External Secrets Operator 공식 문서](https://external-secrets.io/latest/)
- [AWS Secrets Manager 공식 문서](https://docs.aws.amazon.com/secretsmanager/latest/userguide/intro.html)
- [AWS Systems Manager Parameter Store 공식 문서](https://docs.aws.amazon.com/systems-manager/latest/userguide/systems-manager-parameter-store.html)
- [AWS AppConfig 공식 문서](https://docs.aws.amazon.com/appconfig/latest/userguide/what-is-appconfig.html)
- [EKS 공식 문서 - IRSA](https://docs.aws.amazon.com/eks/latest/userguide/iam-roles-for-service-accounts.html)
- [EKS 공식 문서 - Secrets Encryption](https://docs.aws.amazon.com/eks/latest/userguide/enable-kms.html)
- [AWS Controllers for Kubernetes(ACK) 공식 문서](https://aws-controllers-k8s.github.io/community/)
