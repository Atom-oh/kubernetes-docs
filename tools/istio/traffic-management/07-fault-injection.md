# Fault Injection

Fault Injection은 시스템의 복원력을 테스트하기 위해 의도적으로 장애를 주입하는 기법입니다.

## 목차

1. [Fault Injection 개요](#fault-injection-개요)
2. [Delay 주입](#delay-주입)
3. [Abort 주입](#abort-주입)
4. [실전 예제](#실전-예제)
5. [모범 사례](#모범-사례)

## Fault Injection 개요

```mermaid
flowchart LR
    Client[클라이언트]
    
    subgraph FaultInjection["Fault Injection"]
        Delay[지연<br/>3초]
        Abort[중단<br/>HTTP 503]
    end
    
    Service[서비스]
    
    Client --> Delay
    Client --> Abort
    Delay -.->|느린 응답| Service
    Abort -->|에러| Client
    
    %% 스타일 정의
    classDef client fill:#f9f9f9,stroke:#333,stroke-width:1px,color:black;
    classDef fault fill:#FF6B6B,stroke:#333,stroke-width:1px,color:white;
    classDef service fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;
    
    %% 클래스 적용
    class Client client;
    class Delay,Abort fault;
    class Service service;
```

## Delay 주입

```yaml
apiVersion: networking.istio.io/v1beta1
kind: VirtualService
metadata:
  name: reviews-delay
spec:
  hosts:
  - reviews
  http:
  - fault:
      delay:
        percentage:
          value: 10.0  # 10%의 요청에 지연 주입
        fixedDelay: 5s  # 5초 지연
    route:
    - destination:
        host: reviews
```

## Abort 주입

```yaml
apiVersion: networking.istio.io/v1beta1
kind: VirtualService
metadata:
  name: reviews-abort
spec:
  hosts:
  - reviews
  http:
  - fault:
      abort:
        percentage:
          value: 10.0  # 10%의 요청 중단
        httpStatus: 503  # HTTP 503 에러 반환
    route:
    - destination:
        host: reviews
```

## 참고 자료

- [Istio Fault Injection](https://istio.io/latest/docs/tasks/traffic-management/fault-injection/)
