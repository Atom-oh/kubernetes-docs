# Traffic Mirroring

Traffic Mirroring(또는 Shadow Traffic)은 프로덕션 트래픽을 실시간으로 복제하여 새 버전을 테스트하는 기법입니다.

## 목차

1. [Traffic Mirroring 개요](#traffic-mirroring-개요)
2. [기본 설정](#기본-설정)
3. [부분 미러링](#부분-미러링)
4. [모범 사례](#모범-사례)

## Traffic Mirroring 개요

![클라이언트의 요청이 프로덕션의 Version 1으로 전달되어 실제 응답을 받는 동시에, 동일한 요청이 Shadow(미러) 영역의 Version 2로 복제되지만 그 응답은 무시됨을 보여준다.](../../../.gitbook/assets/ko-service-mesh-istio-traffic-management-09-traffic-mirror-0.png)

[🔍 인터랙티브 다이어그램 보기](https://www.atomai.click/kubernetes-docs/archmaps/ko-service-mesh-istio-traffic-management-09-traffic-mirror-0.html)

## 기본 설정

Sidecar 예제에는 `reviews` Service와 파드 레이블에 일치하는 DestinationRule subset `v1`/`v2`가 필요합니다. 이 호스트의 VirtualService는 대안 중 하나씩 적용하세요. Mirror는 주 경로 가중치의 일부가 아니라 추가 복사본을 받습니다.

```yaml
apiVersion: networking.istio.io/v1
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
apiVersion: networking.istio.io/v1
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

## 모범 사례

- 미러 응답은 버리므로 장애 조치나 자동 응답 비교 기능이 아닙니다.
- 복사한 쓰기 요청도 대상에서 실행됩니다. 프로덕션 요청을 복제하기 전에 Shadow의 DB·큐·외부 부수 효과를 격리하세요.
- 작은 비율로 시작해 주 요청의 지연 시간과 Shadow 용량을 관찰하세요. 미러링은 트래픽과 처리 비용을 추가합니다.
- 기본적으로 미러 요청의 Host/Authority에는 `-shadow` 접미사가 붙으므로 대상이 이를 수용해야 합니다. Ambient waypoint에는 선택한 릴리스가 지원하는 라우팅 API를 확인하세요.

## 참고 자료

- [Istio Traffic Mirroring](https://istio.io/latest/docs/tasks/traffic-management/mirroring/)
