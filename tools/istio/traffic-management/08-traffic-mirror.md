# Traffic Mirroring

Traffic Mirroring(또는 Shadow Traffic)은 프로덕션 트래픽을 실시간으로 복제하여 새 버전을 테스트하는 기법입니다.

## 목차

1. [Traffic Mirroring 개요](#traffic-mirroring-개요)
2. [기본 설정](#기본-설정)
3. [부분 미러링](#부분-미러링)
4. [실전 예제](#실전-예제)
5. [모범 사례](#모범-사례)

## Traffic Mirroring 개요

```mermaid
flowchart LR
    Client[클라이언트]
    
    subgraph Production["프로덕션"]
        V1[Version 1<br/>실제 응답]
    end
    
    subgraph Shadow["Shadow (미러)"]
        V2[Version 2<br/>응답 무시]
    end
    
    Client -->|요청| V1
    V1 -->|응답| Client
    Client -.->|복제| V2
    V2 -.->|무시| Client
    
    %% 스타일 정의
    classDef client fill:#f9f9f9,stroke:#333,stroke-width:1px,color:black;
    classDef production fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;
    classDef shadow fill:#95A5A6,stroke:#333,stroke-width:1px,color:white;
    
    %% 클래스 적용
    class Client client;
    class V1 production;
    class V2 shadow;
```

## 기본 설정

```yaml
apiVersion: networking.istio.io/v1beta1
kind: VirtualService
metadata:
  name: reviews-mirror
spec:
  hosts:
  - reviews
  http:
  - route:
    - destination:
        host: reviews
        subset: v1
      weight: 100
    mirror:
      host: reviews
      subset: v2
    mirrorPercentage:
      value: 100  # 100% 미러링
```

## 부분 미러링

```yaml
apiVersion: networking.istio.io/v1beta1
kind: VirtualService
metadata:
  name: reviews-partial-mirror
spec:
  hosts:
  - reviews
  http:
  - route:
    - destination:
        host: reviews
        subset: v1
    mirror:
      host: reviews
      subset: v2
    mirrorPercentage:
      value: 10  # 10%만 미러링
```

## 참고 자료

- [Istio Traffic Mirroring](https://istio.io/latest/docs/tasks/traffic-management/mirroring/)
