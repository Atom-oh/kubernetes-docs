# Zone Aware Routing

> **마지막 업데이트**: 2026년 9월 11일 · Istio1.31. 이 장은 locality 가중치·우선순위 장애조치를 위한 `localityLbSetting`을 사용합니다. 별도 `zoneAwareLbSetting` API는 전제·의미가 다르므로 필드를 섞지 않습니다. 사이드카 메시를 가정하며 같은 host 정책들은 독립적인 대안입니다. 배포·부하 검증된 예제가 아닙니다.

Zone Aware Routing은 Kubernetes 가용 영역(Availability Zone)을 인식하여 트래픽을 최적화하는 기능입니다. 같은 AZ 내 통신을 우선하여 지연시간을 줄이고 크로스 AZ 데이터 전송 비용을 절감합니다.

## 목차

1. [개요](#개요)
2. [작동 원리](#작동-원리)
3. [기본 설정](#기본-설정)
4. [고급 설정](#고급-설정)
5. [AWS EKS에서 설정](#aws-eks에서-설정)
6. [실전 예제](#실전-예제)
7. [모니터링](#모니터링)
8. [문제 해결](#문제-해결)

## 개요

Zone Aware Routing은 다음과 같은 이점을 제공합니다:


### 이점

1. **지연시간 감소**: 같은 AZ 내 통신으로 네트워크 지연 최소화
2. **비용 절감**: 크로스 AZ 데이터 전송 비용 절감
   - 실제 과금 byte·방향·리전·AWS 서비스 경로로 산정합니다. 모든 EKS 요청에 공통인 GB 단가는 없습니다.
3. **가용성 지원**: 다른 AZ의 정상·접근 가능한 endpoint와 여유 용량이 필요합니다.
4. **성능 최적화**: 네트워크 대역폭 최적화

## 작동 원리

### Locality Load Balancing 알고리즘

80/10/10 `distribute` 정책은 세 정상 AZ에 평상시 트래픽을 보냅니다. 10% 부분은 대기 failover가 아닙니다. Locality priority 장애조치는 별도 모드이며 건강·용량 가중치 때문에 모든 local host가 실패하기 전에도 spillover할 수 있습니다. AZ 문자는 물리적 인접성·지연 순서가 아닙니다.



### Locality 계층 구조

Istio는 다음과 같은 계층적 Locality를 사용합니다:

```
Region/Zone/SubZone

예시:
us-east-1/us-east-1a/*
us-east-1/us-east-1b/*
us-west-2/us-west-2a/*
```

**기본 locality 우선순위** (priority failover가 활성화된 경우):

1. Region·zone·subzone 모두 같음.
2. Region·zone은 같고 subzone은 다름.
3. Region은 같고 zone은 다름.
4. 다른 region이며 지정한 regional failover 정책이 있으면 그 순서를 반영.

### Pod에 AZ 레이블이 없어도 동작하는 원리

**중요**: Pod 자체에는 AZ 레이블이 필요하지 않습니다. Istio는 **노드의 Topology 레이블**을 읽어서 Pod의 Locality를 자동으로 파악합니다.

#### 동작 방식

![파드 자체에는 Zone 레이블이 없어도, Istiod의 Service Discovery가 Pod가 실행 중인 Node의 topology 레이블을 조회해 Locality를 파악하고 이를 EDS로 만들어 Envoy Proxy에 xDS로 전달하는 과정을 보여준다.](../../../.gitbook/assets/ko-service-mesh-istio-resilience-03-zone-aware-routing-2.png)

[🔍 인터랙티브 다이어그램 보기](https://www.atomai.click/kubernetes-docs/archmaps/ko-service-mesh-istio-resilience-03-zone-aware-routing-2.html)

#### 단계별 프로세스

**1단계: Istiod가 Pod 정보 수집**

```bash
# Istiod는 Kubernetes API를 통해 Pod 정보 조회
kubectl get pod <pod-name> -o json | jq '.spec.nodeName'
# 출력: "ip-10-0-1-10.ec2.internal"
```

**2단계: Pod가 실행 중인 Node의 Topology 레이블 조회**

```bash
# Pod의 nodeName으로 Node 정보 조회
kubectl get node ip-10-0-1-10.ec2.internal -o json | \
  jq '.metadata.labels."topology.kubernetes.io/zone"'
# 출력: "us-east-1a"
```

**3단계: EDS (Endpoint Discovery Service) 생성**

다음은 수집한 CLI 출력이 아닌 ClusterLoadAssignment 개념 예시입니다. 실제 EDS에는 생성된 가중치·priority·건강 상태도 포함됩니다:

```json
{
  "cluster_name": "outbound|8080||myapp.default.svc.cluster.local",
  "endpoints": [
    {
      "locality": {
        "region": "us-east-1",
        "zone": "us-east-1a"
      },
      "lb_endpoints": [
        {
          "endpoint": {
            "address": {
              "socket_address": {
                "address": "10.0.1.10",
                "port_value": 8080
              }
            }
          }
        }
      ]
    },
    {
      "locality": {
        "region": "us-east-1",
        "zone": "us-east-1b"
      },
      "lb_endpoints": [
        {
          "endpoint": {
            "address": {
              "socket_address": {
                "address": "10.0.2.20",
                "port_value": 8080
              }
            }
          }
        }
      ]
    }
  ]
}
```

**4단계: Envoy가 Locality 기반 라우팅**

Envoy는 받은 EDS 정보를 바탕으로 자신의 Locality와 비교하여 라우팅:

```bash
# Envoy의 Locality 확인 (자신이 실행 중인 노드 기준)
istioctl proxy-config bootstrap <pod-name> -n default -o json | \
  jq '.bootstrap.node.locality'

# 출력:
# {
#   "region": "us-east-1",
#   "zone": "us-east-1a"
# }
```

#### 실제 확인 방법

```bash
# 1. Pod가 어느 Node에서 실행 중인지 확인
kubectl get pod <pod-name> -o wide
# NAME        READY   STATUS    NODE
# myapp-abc   2/2     Running   ip-10-0-1-10.ec2.internal

# 2. 해당 Node의 Zone 레이블 확인
kubectl get node ip-10-0-1-10.ec2.internal \
  -o jsonpath='{.metadata.labels.topology\.kubernetes\.io/zone}'
# 출력: us-east-1a

# 3. Envoy가 인식한 Endpoint Locality 확인
istioctl proxy-config all <pod-name> -n default -o json | \
  jq '.configs[] | select(.["@type"] | endswith("EndpointsConfigDump")) |
      ((.dynamic_endpoint_configs // .dynamicEndpointConfigs // [])[] |
       (.endpoint_config // .endpointConfig)) |
      select((.cluster_name // .clusterName) == "outbound|8080||myapp.default.svc.cluster.local") |
      .endpoints[] | {locality, priority}'
```

#### 왜 Pod 레이블이 필요 없는가?

스케줄된 Pod는 해당 UID의 수명 동안 같은 Node에 있고 controller가 다른 Node의 새 Pod로 교체할 수 있습니다. Istiod는 Kubernetes discovery로 endpoint를 Node topology와 연결합니다. 일반 locality routing에 추가 Pod zone 레이블은 필요하지 않습니다. API watch/cache·프록시 설정은 비동기적으로 반영되므로 즉시 갱신을 가정하지 말고 실제 설정을 확인합니다. 사용자 telemetry enrichment는 별도 요구입니다.

```yaml
# Relevant existing Node metadata; do not overwrite actual cloud topology
metadata:
  labels:
    topology.kubernetes.io/zone: us-east-1a
    topology.kubernetes.io/region: us-east-1
```

#### AWS EKS의 자동 설정

AWS EKS는 노드 생성 시 자동으로 Topology 레이블을 추가합니다:

```bash
# EKS 노드 확인
kubectl get nodes -L topology.kubernetes.io/zone,topology.kubernetes.io/region

# 출력 예시:
# NAME                           ZONE         REGION
# ip-10-0-1-10.ec2.internal      us-east-1a   us-east-1
# ip-10-0-2-20.ec2.internal      us-east-1b   us-east-1
# ip-10-0-3-30.ec2.internal      us-east-1c   us-east-1
```

EC2 기반 Node는 cloud/bootstrap 통합이 AWS 인스턴스 배치 정보를 사용합니다. `spec.providerID`는 provider 인스턴스 식별자이며 EC2 instance ID 자체가 아닙니다. Workload의 IMDS 접근은 제한될 수 있고 IMDSv2에는 token이 필요합니다. 필요하면 뒤의 읽기 전용 EC2 진단을 사용합니다. Fargate Node는 해당 platform 진단이 필요합니다.

## 기본 설정

### 1. Kubernetes 노드에 Topology 레이블 설정

AWS EKS는 자동으로 다음 레이블을 추가합니다:

```yaml
topology.kubernetes.io/region: us-east-1
topology.kubernetes.io/zone: us-east-1a
```

**확인 방법**:
```bash
kubectl get nodes -L topology.kubernetes.io/zone -L topology.kubernetes.io/region

# 출력 예시:
# NAME                          ZONE         REGION
# ip-10-0-1-10.ec2.internal     us-east-1a   us-east-1
# ip-10-0-2-20.ec2.internal     us-east-1b   us-east-1
# ip-10-0-3-30.ec2.internal     us-east-1c   us-east-1
```

### 2. DestinationRule에서 Zone Aware Routing 활성화

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: myapp
  namespace: default
spec:
  host: myapp
  trafficPolicy:
    loadBalancer:
      localityLbSetting:
        enabled: true
    outlierDetection:
      consecutive5xxErrors: 5
      interval: 10s
      baseEjectionTime: 30s
      maxEjectionPercent: 100
      minHealthPercent: 0
```

기본 예제는 locality priority와 outlier detection을 사용합니다. 100% 제외 cap은 모든 비정상 endpoint 제외를 허용하므로 남은 용량이 없으면 “no healthy upstream”이 될 수 있습니다. 일반적인 안전 한도가 아닌 장애조치 예시입니다.

### 3. 분산 비율 설정

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: myapp
  namespace: default
spec:
  host: myapp
  trafficPolicy:
    loadBalancer:
      localityLbSetting:
        enabled: true
        distribute:
        - from: us-east-1/us-east-1a/*
          to:
            us-east-1/us-east-1a/*: 80
            us-east-1/us-east-1b/*: 10
            us-east-1/us-east-1c/*: 10
        - from: us-east-1/us-east-1b/*
          to:
            us-east-1/us-east-1b/*: 80
            us-east-1/us-east-1a/*: 10
            us-east-1/us-east-1c/*: 10
        - from: us-east-1/us-east-1c/*
          to:
            us-east-1/us-east-1c/*: 80
            us-east-1/us-east-1a/*: 10
            us-east-1/us-east-1b/*: 10
    outlierDetection:
      consecutive5xxErrors: 5
      interval: 10s
      baseEjectionTime: 30s
      maxEjectionPercent: 100
      minHealthPercent: 0
```

## 고급 설정

### 장애조치 설정

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: myapp-failover
  namespace: default
spec:
  host: myapp
  trafficPolicy:
    loadBalancer:
      localityLbSetting:
        enabled: true
        failoverPriority:
        - topology.kubernetes.io/region
        - topology.kubernetes.io/zone
    outlierDetection:
      consecutive5xxErrors: 5
      interval: 10s
      baseEjectionTime: 30s
      maxEjectionPercent: 100
      minHealthPercent: 0
```

`localityLbSetting`의 `failoverPriority`는 위와 같이 region/zone metadata를 비교할 수 있습니다. `failover`는 `region/zone` 경로가 아닌 **리전 이름**을 받으며 AZ A→B→C 순서를 표현하지 않습니다. 여기서는 `distribute`·`failover`·`failoverPriority` 중 하나를 사용합니다. 별도 `zoneAwareLbSetting` API와 규칙이 다릅니다.

### Outlier Detection과 함께 사용

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: myapp-resilient
  namespace: default
spec:
  host: myapp
  trafficPolicy:
    loadBalancer:
      localityLbSetting:
        enabled: true
        distribute:
        - from: us-east-1/us-east-1a/*
          to:
            us-east-1/us-east-1a/*: 80
            us-east-1/us-east-1b/*: 20
    outlierDetection:
      consecutive5xxErrors: 5
      interval: 30s
      baseEjectionTime: 30s
      maxEjectionPercent: 50
      minHealthPercent: 0
```

`minHealthPercent`는 pool의 panic/fail-open 임계치이며 AZ별 최소 정상 용량이 아닙니다. 0은 그 임계치를 끕니다. 가중치80/20은 두 정상 AZ를 계속 사용하며 대기 failover가 아닙니다.

### 다중 리전 설정

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: myapp-multi-region
  namespace: default
spec:
  host: myapp.default.svc.cluster.local
  trafficPolicy:
    loadBalancer:
      localityLbSetting:
        enabled: true
        distribute:
        - from: us-east-1/*
          to:
            us-east-1/*: 90
            us-west-2/*: 10
        - from: us-west-2/*
          to:
            us-west-2/*: 90
            us-east-1/*: 10
    outlierDetection:
      consecutive5xxErrors: 5
      interval: 10s
      baseEjectionTime: 30s
      maxEjectionPercent: 100
      minHealthPercent: 0
```

90/10 예제는 분배 전용입니다. 두 리전에서 해당 서비스를 노출하는 실제 multi-cluster/network 구성이 필요하며 `myapp.global`은 자동 생성되는 서비스가 아닙니다. 우선순위 장애조치가 필요하면 다음 별도 정책과 실제 endpoint·연결을 검증합니다:

```yaml
# Alternative to distribute: region-name priority failover
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: myapp-regional-failover
  namespace: default
spec:
  host: myapp.default.svc.cluster.local
  trafficPolicy:
    loadBalancer:
      localityLbSetting:
        enabled: true
        failover:
        - from: us-east-1
          to: us-west-2
        - from: us-west-2
          to: us-east-1
    outlierDetection:
      consecutive5xxErrors: 5
      interval: 10s
      baseEjectionTime: 30s
      maxEjectionPercent: 100
      minHealthPercent: 0
```

## AWS EKS에서 설정

### 1. 다중 AZ 노드 그룹 생성

```yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: my-cluster
  region: us-east-1
  version: '1.36'
nodeGroups:
- name: ng-zone-a
  instanceType: t3.medium
  desiredCapacity: 2
  availabilityZones:
  - us-east-1a
  amiFamily: AmazonLinux2023
- name: ng-zone-b
  instanceType: t3.medium
  desiredCapacity: 2
  availabilityZones:
  - us-east-1b
  amiFamily: AmazonLinux2023
- name: ng-zone-c
  instanceType: t3.medium
  desiredCapacity: 2
  availabilityZones:
  - us-east-1c
  amiFamily: AmazonLinux2023
```

eksctl 파일은 과금되는 클러스터/node-group 설계 예제이며 이 감사에서 실행하지 않았습니다. 문서의 Istio/EKS 호환 범위에 맞춰 Kubernetes1.36·AL2023을 지정했습니다. 실제 subnet/AZ·인스턴스 용량·접근 설정을 선택하고 기존 클러스터에는 적절한 node-group 변경 계획이 필요합니다.

### 2. Zone별로 파드 분산

의도적으로 해석되지 않는 image 참조를 HTTP8080을 제공하는 검증된 앱 이미지로 바꾸고 readiness 동작을 구성합니다. 아래 Service가 정책의 `myapp` 목적지를 제공합니다. `maxSkew: 1`은 eligible domain 사이의 제한이며 무조건3개 AZ 보장이 아닙니다. Node affinity·taint·자원·`minDomains`가 scheduling에 영향을 줍니다.


```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: myapp
  namespace: default
spec:
  replicas: 9
  selector:
    matchLabels:
      app: myapp
  template:
    metadata:
      labels:
        app: myapp
    spec:
      topologySpreadConstraints:
      - maxSkew: 1
        topologyKey: topology.kubernetes.io/zone
        whenUnsatisfiable: DoNotSchedule
        labelSelector:
          matchLabels:
            app: myapp
      containers:
      - name: myapp
        image: example.invalid/myapp:replace-with-tested-tag
        ports:
        - containerPort: 8080
        resources:
          requests:
            memory: 64Mi
            cpu: 100m
          limits:
            memory: 128Mi
            cpu: 200m
---
apiVersion: v1
kind: Service
metadata:
  name: myapp
  namespace: default
spec:
  selector:
    app: myapp
  ports:
  - name: http
    port: 8080
    targetPort: 8080
```

### 3. Istio에서 Zone Aware Routing 활성화

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: myapp
  namespace: default
spec:
  host: myapp
  trafficPolicy:
    loadBalancer:
      localityLbSetting:
        enabled: true
        distribute:
        - from: us-east-1/us-east-1a/*
          to:
            us-east-1/us-east-1a/*: 80
            us-east-1/us-east-1b/*: 10
            us-east-1/us-east-1c/*: 10
    outlierDetection:
      consecutive5xxErrors: 5
      interval: 10s
      baseEjectionTime: 30s
      maxEjectionPercent: 100
      minHealthPercent: 0
```

## 실전 예제

### 예제 1: 마이크로서비스 체인

처음 세 문서는 기존 frontend/backend Deployment·DB workload용 **Pod-template patch**이며 완전한 Kubernetes 리소스가 아닙니다. 실제 container·selector·Service·스토리지가 있는 workload에 병합합니다. DB affinity는 이미 AZ에 종속된 한 volume/instance 예시이며 모든 DB replica를 한 AZ에 두라는 HA 권장이 아닙니다. 마지막 DestinationRule은 실제 `backend` Service를 전제합니다.


```yaml
spec:
  template:
    metadata:
      labels:
        app: frontend
    spec:
      topologySpreadConstraints:
      - maxSkew: 1
        topologyKey: topology.kubernetes.io/zone
        whenUnsatisfiable: DoNotSchedule
        labelSelector:
          matchLabels:
            app: frontend
---
spec:
  template:
    metadata:
      labels:
        app: backend
    spec:
      topologySpreadConstraints:
      - maxSkew: 1
        topologyKey: topology.kubernetes.io/zone
        whenUnsatisfiable: DoNotSchedule
        labelSelector:
          matchLabels:
            app: backend
---
spec:
  template:
    metadata:
      labels:
        app: database
    spec:
      affinity:
        nodeAffinity:
          requiredDuringSchedulingIgnoredDuringExecution:
            nodeSelectorTerms:
            - matchExpressions:
              - key: topology.kubernetes.io/zone
                operator: In
                values:
                - us-east-1a
---
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: backend
  namespace: default
spec:
  host: backend
  trafficPolicy:
    loadBalancer:
      localityLbSetting:
        enabled: true
        distribute:
        - from: us-east-1/us-east-1a/*
          to:
            us-east-1/us-east-1a/*: 90
            us-east-1/us-east-1b/*: 5
            us-east-1/us-east-1c/*: 5
    outlierDetection:
      consecutive5xxErrors: 5
      interval: 10s
      baseEjectionTime: 30s
      maxEjectionPercent: 100
      minHealthPercent: 0
```

### 예제 2: 비용 최적화

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: cost-optimized
  namespace: default
spec:
  host: myapp
  trafficPolicy:
    loadBalancer:
      localityLbSetting:
        enabled: true
        distribute:
        - from: us-east-1/us-east-1a/*
          to:
            us-east-1/us-east-1a/*: 95
            us-east-1/us-east-1b/*: 3
            us-east-1/us-east-1c/*: 2
    outlierDetection:
      consecutive5xxErrors: 5
      interval: 10s
      baseEjectionTime: 30s
      maxEjectionPercent: 100
      minHealthPercent: 0
```

95/3/2 정책은 zoneA 호출자만 다루므로 필요하면 다른 source locality도 정의합니다. 집중 때문에 local endpoint가 과부하될 수 있습니다. [EKS 네트워크 비용 가이드](https://docs.aws.amazon.com/eks/latest/best-practices/cost-opt-networking.html)와 실측 과금 byte·서비스별 가격을 대조하며 요청 수·가중치만으로 비용을 계산하지 않습니다.

### 예제 3: 고가용성

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: high-availability
  namespace: default
spec:
  host: myapp
  trafficPolicy:
    loadBalancer:
      localityLbSetting:
        enabled: true
        distribute:
        - from: us-east-1/us-east-1a/*
          to:
            us-east-1/us-east-1a/*: 34
            us-east-1/us-east-1b/*: 33
            us-east-1/us-east-1c/*: 33
    outlierDetection:
      consecutive5xxErrors: 5
      interval: 10s
      baseEjectionTime: 30s
      maxEjectionPercent: 100
      minHealthPercent: 0
```

## 모니터링

### Prometheus 메트릭

`source_zone`·`destination_zone`은 **Istio 표준 메트릭 레이블이 아닙니다**. 다음 선택적 쿼리에는 두 endpoint를 실제 AZ와 연결하면서 표준 서비스 레이블을 보존하는 별도의 검증된 enrichment pipeline이 필요합니다. 이 장에서는 pipeline을 배포하지 않습니다. Node 레이블·locality routing·Grafana panel만으로 메트릭이 생기지는 않습니다. 필요하면 cluster/account 문맥도 유지합니다. AWS AZ 이름은 계정별 매핑이 다를 수 있고 AZ ID가 같은 물리적 AZ를 식별합니다.

예제는 한 클러스터/계정의 us-east-1a/b/c 사이 트래픽만 다루며 미확인 AZ·다른 리전·다른 목적지는 분자·분모에서 모두 제외합니다. PromQL selector에서 `{source_zone=destination_zone}`처럼 레이블 값을 서로 비교할 수 없으므로 다음처럼 명시적 쌍을 사용합니다. Rate는 초당 값이고 same-zone 결과는0–100%입니다.

```promql
sum by (source_zone, destination_zone) (rate(istio_requests_total{reporter="source",source_workload_namespace="default",destination_service="myapp.default.svc.cluster.local",source_zone=~"us-east-1[abc]",destination_zone=~"us-east-1[abc]"}[5m]))

100 * sum(rate(istio_requests_total{reporter="source",source_workload_namespace="default",destination_service="myapp.default.svc.cluster.local",source_zone="us-east-1a",destination_zone="us-east-1a"}[5m]) or rate(istio_requests_total{reporter="source",source_workload_namespace="default",destination_service="myapp.default.svc.cluster.local",source_zone="us-east-1b",destination_zone="us-east-1b"}[5m]) or rate(istio_requests_total{reporter="source",source_workload_namespace="default",destination_service="myapp.default.svc.cluster.local",source_zone="us-east-1c",destination_zone="us-east-1c"}[5m])) / sum(rate(istio_requests_total{reporter="source",source_workload_namespace="default",destination_service="myapp.default.svc.cluster.local",source_zone=~"us-east-1[abc]",destination_zone=~"us-east-1[abc]"}[5m]))

sum by (destination_zone) (rate(istio_requests_total{reporter="source",source_workload_namespace="default",destination_service="myapp.default.svc.cluster.local",source_zone=~"us-east-1[abc]",destination_zone=~"us-east-1[abc]",response_code=~"5.."}[5m])) / sum by (destination_zone) (rate(istio_requests_total{reporter="source",source_workload_namespace="default",destination_service="myapp.default.svc.cluster.local",source_zone=~"us-east-1[abc]",destination_zone=~"us-east-1[abc]"}[5m]))
```

무트래픽·enrichment 누락·scrape 실패는 별도로 처리합니다. 송신 메트릭은 과금 byte가 아닌 요청 수이고 수신 메트릭에는 도착하지 못한 실패가 없습니다. Cluster의 활성 연결 수만으로 목적지 AZ나 locality 효과를 알 수는 없습니다.

### Grafana 대시보드

앞의 enrichment·datasource UID `prometheus`가 필요한 dashboard입니다. [대시보드 장](../observability/04-dashboards.md)에 따라 완전한 객체를 provisioning합니다. Enrichment 없이는 AZ 트래픽 측정 panel이 작동하지 않습니다.

```json
{
  "uid": "istio-enriched-zone-traffic",
  "title": "Istio Enriched Zone Traffic",
  "panels": [
    {
      "id": 1,
      "title": "Enriched Request Rate by Zone",
      "type": "timeseries",
      "datasource": {
        "type": "prometheus",
        "uid": "prometheus"
      },
      "targets": [
        {
          "expr": "sum by (source_zone, destination_zone) (rate(istio_requests_total{reporter=\"source\",source_workload_namespace=\"default\",destination_service=\"myapp.default.svc.cluster.local\",source_zone=~\"us-east-1[abc]\",destination_zone=~\"us-east-1[abc]\"}[5m]))",
          "legendFormat": "{{source_zone}} → {{destination_zone}}",
          "refId": "A"
        }
      ],
      "gridPos": {
        "x": 0,
        "y": 0,
        "w": 24,
        "h": 8
      },
      "fieldConfig": {
        "defaults": {
          "unit": "reqps"
        }
      }
    },
    {
      "id": 2,
      "title": "Same-Zone Percentage (Known a/b/c Traffic)",
      "type": "timeseries",
      "datasource": {
        "type": "prometheus",
        "uid": "prometheus"
      },
      "targets": [
        {
          "expr": "100 * sum(rate(istio_requests_total{reporter=\"source\",source_workload_namespace=\"default\",destination_service=\"myapp.default.svc.cluster.local\",source_zone=\"us-east-1a\",destination_zone=\"us-east-1a\"}[5m]) or rate(istio_requests_total{reporter=\"source\",source_workload_namespace=\"default\",destination_service=\"myapp.default.svc.cluster.local\",source_zone=\"us-east-1b\",destination_zone=\"us-east-1b\"}[5m]) or rate(istio_requests_total{reporter=\"source\",source_workload_namespace=\"default\",destination_service=\"myapp.default.svc.cluster.local\",source_zone=\"us-east-1c\",destination_zone=\"us-east-1c\"}[5m])) / sum(rate(istio_requests_total{reporter=\"source\",source_workload_namespace=\"default\",destination_service=\"myapp.default.svc.cluster.local\",source_zone=~\"us-east-1[abc]\",destination_zone=~\"us-east-1[abc]\"}[5m]))",
          "legendFormat": "Same-zone %",
          "refId": "A"
        }
      ],
      "gridPos": {
        "x": 0,
        "y": 8,
        "w": 24,
        "h": 8
      },
      "fieldConfig": {
        "defaults": {
          "unit": "percent"
        }
      }
    }
  ],
  "time": {
    "from": "now-1h",
    "to": "now"
  },
  "refresh": "30s"
}
```

### 실시간 확인

`proxy-config endpoints`로 host 건강을 확인할 수 있지만 EDS locality 할당과 출력 형식이 다릅니다. `proxy-config all -o json`에는 EDS가 포함되므로 해당 ClusterLoadAssignment를 확인합니다. 쿼리는 원본 snake_case·정규화된 camelCase 필드 모두를 받습니다. 이는 설정 증거이며 실제 트래픽 비율 측정은 아닙니다.

```bash
istioctl proxy-config endpoints <pod-name> -n <namespace>

istioctl proxy-config all <pod-name> -n <namespace> -o json | \
  jq '.configs[] | select(.["@type"] | endswith("EndpointsConfigDump")) |
      ((.dynamic_endpoint_configs // .dynamicEndpointConfigs // [])[] |
       (.endpoint_config // .endpointConfig)) |
      select((.cluster_name // .clusterName) == "outbound|8080||myapp.default.svc.cluster.local") |
      .endpoints[] | {locality, priority}'
```

## 문제 해결

### Zone Aware Routing이 작동하지 않음

레이블 복구 전에 실제 cloud topology를 확인합니다. 모든 Node에 임의의 같은 zone을 지정하면 scheduler/storage/routing 결정이 바뀌고 거짓 metadata가 됩니다. 의도한 정책이 호출 프록시에 전달되고 목적지 endpoint가 검색되는지 확인합니다.

```bash
kubectl get nodes -L topology.kubernetes.io/region,topology.kubernetes.io/zone
kubectl get destinationrule -n <namespace>
kubectl describe destinationrule <name> -n <namespace>
istioctl analyze -n <namespace>
istioctl proxy-config clusters <pod-name> -n <namespace> --fqdn myapp.default.svc.cluster.local -o json
kubectl get pods -n <namespace> -l app=myapp -o wide
```

앞의 명령으로 EDS를 읽습니다. Kubernetes EDS cluster의 endpoint 원천은 cluster 설정의 `.loadAssignment`가 아닙니다. Pod zone 레이블은 Node에서 자동 복사되지 않으므로 `.spec.nodeName`으로 연결합니다.

### 트래픽이 다른 Zone으로 가는 비율이 높음

구조화된 필드로 Pod→Node 배치·readiness를 확인합니다. Running Pod도 unready일 수 있고 Node별 개수는 AZ별 개수가 아닙니다. Rollout 중에는 두 snapshot의 시점 차이를 고려합니다.

```bash
kubectl get nodes -o json > /tmp/zone-nodes.json
kubectl get pods -n default -l app=myapp -o json > /tmp/zone-pods.json
jq -r --slurpfile nodes /tmp/zone-nodes.json '
  ($nodes[0].items | map({key: .metadata.name,
    value: .metadata.labels["topology.kubernetes.io/zone"]}) | from_entries) as $zones |
  .items[] | [.metadata.name, (.spec.nodeName // "unscheduled"),
    ($zones[(.spec.nodeName // "")] // "unknown"),
    ([.status.conditions[]? | select(.type == "Ready") | .status][0] // "Unknown")] | @tsv
' /tmp/zone-pods.json

istioctl x envoy-stats <pod-name> -n <namespace> --output prom | grep outlier_detection
```

Endpoint/ejection·source-locality `from` 매칭·연결 재사용·트래픽량·AZ별 여유 용량도 확인합니다. 가중치 분배는 정상 트래픽 일부를 다른 AZ로 보내며 replica 수 차이만으로 설정 가중치가 다시 정의되지는 않습니다.

### EKS에서 Topology 레이블 누락

AWS Node Termination Handler는 interruption/termination event를 처리하며 설치해도 topology 레이블을 복구하지 않습니다. EKS node bootstrap/cloud 통합·실제 instance 배치를 확인합니다. 다음은 **EC2 Node 전용 읽기 진단**으로 providerID에서 instance ID를 추출하고 cluster region을 명시합니다. Node 레이블을 바꾸지 않으며 Fargate·다른 provider에는 해당 플랫폼 진단을 사용합니다.

```bash
CLUSTER_REGION=us-east-1
NODE_NAME=<node-name>
PROVIDER_ID=$(kubectl get node "$NODE_NAME" -o jsonpath='{.spec.providerID}')
INSTANCE_ID=${PROVIDER_ID##*/}
if [[ ! "$INSTANCE_ID" =~ ^i-([0-9a-f]{8}|[0-9a-f]{17})$ ]]; then
  echo "Expected an EC2 instance ID in providerID; inspect the node platform." >&2
  exit 1
fi
aws ec2 describe-instances --region "$CLUSTER_REGION" \
  --instance-ids "$INSTANCE_ID" \
  --query 'Reservations[].Instances[].{InstanceId:InstanceId,AZ:Placement.AvailabilityZone,State:State.Name}' \
  --output table
```

검토한 bootstrap·레이블 복구를 적용하기 전에 계정/리전·실제 Node 신원을 확인합니다. `aws:///zone/i-...` 전체를 `--instance-ids`로 넘기거나 인증 없는 IMDSv1 접근을 가정하지 않습니다.

## 모범 사례

### 1. Zone별 균등 파드 배포

Pod template의 `spec` 아래에 넣고 selector가 Pod 레이블과 일치하게 합니다. 제약은 eligible domain을 세므로 AZ가 없을 때 엄격한 scheduling으로 Pod를 Pending 상태에 둘지 결정합니다.


```yaml
# ✅ topologySpreadConstraints 사용
topologySpreadConstraints:
- maxSkew: 1
  topologyKey: topology.kubernetes.io/zone
  whenUnsatisfiable: DoNotSchedule
  labelSelector:
    matchLabels:
      app: myapp
```

### 2. 비용 최적화

```yaml
# ✅ 같은 Zone 우선 (80% 이상)
distribute:
- from: us-east-1/us-east-1a/*
  to:
    "us-east-1/us-east-1a/*": 80
    "us-east-1/us-east-1b/*": 10
    "us-east-1/us-east-1c/*": 10
```

### 3. 고가용성 보장

검증한 여유 용량과 locality priority·outlier detection을 함께 사용합니다. 다음 조각은 `trafficPolicy.loadBalancer.localityLbSetting` 아래에 들어가며 `failover`는 AZ가 아닌 리전 순서이고 `distribute`의 대안입니다.

```yaml
failover:
- from: us-east-1
  to: us-west-2
```

### 4. Stateful Workload의 스토리지·가용성

EBS volume과 연결할 EC2 instance는 같은 AZ여야 합니다. 개별 volume/replica 제약이지 StatefulSet의 모든 replica를 같은 AZ에 두라는 뜻은 아닙니다. 호환 스토리지·scheduling과 장애 도메인별 DB 복제·failover를 설계하며 locality routing이 안전한 writable primary를 선출하지는 않습니다. 다음 affinity는 의도적으로 기존 zoneA volume에 종속된 workload용이며 모든 stateful replica를 한 AZ에 두라는 권장이 아닙니다.


```yaml
# 기존 zonal volume/replica 하나에 대한 Pod-spec 조각
affinity:
  nodeAffinity:
    requiredDuringSchedulingIgnoredDuringExecution:
      nodeSelectorTerms:
      - matchExpressions:
        - key: topology.kubernetes.io/zone
          operator: In
          values:
          - us-east-1a
```

Kubernetes Service topology hint/traffic distribution과 Istio Envoy 부하 분산은 별도 메커니즘입니다. Service annotation을 켜면 호출 sidecar locality 정책도 설정된다고 가정하지 않습니다.

## 참고 자료

- [Istio Locality Load Balancing](https://istio.io/latest/docs/tasks/traffic-management/locality-load-balancing/)
- [Kubernetes Topology Aware Routing](https://kubernetes.io/docs/concepts/services-networking/topology-aware-routing/)
- [AWS EKS Resilience](https://docs.aws.amazon.com/eks/latest/userguide/disaster-recovery-resiliency.html)
- [EKS Network Cost Optimization](https://docs.aws.amazon.com/eks/latest/best-practices/cost-opt-networking.html)
- [EBS Volume Availability Zones](https://docs.aws.amazon.com/ebs/latest/userguide/ebs-volumes.html)
- [AWS Availability Zone IDs](https://docs.aws.amazon.com/global-infrastructure/latest/regions/az-ids.html)
