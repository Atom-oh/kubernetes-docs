# トラフィックミラーリング

Traffic Mirroring（shadow traffic とも呼ばれます）は、新しい version をテストするため、本番トラフィックをリアルタイムに複製する手法です。

## 目次

1. [トラフィックミラーリングの概要](#traffic-mirroring-overview)
2. [基本設定](#basic-configuration)
3. [部分ミラーリング](#partial-mirroring)
4. [ベストプラクティス](#best-practices)

## トラフィックミラーリングの概要 {#traffic-mirroring-overview}

![client からの request に Version 1 が本番経路で応答する一方、同じ request が shadow copy の Version 2 に複製されます。shadow 側の response は破棄され、client には返りません。](../../../.gitbook/assets/en-service-mesh-istio-traffic-management-09-traffic-mirror-0.png)

[🔍 インタラクティブ図を表示](https://www.atomai.click/kubernetes-docs/archmaps/en-service-mesh-istio-traffic-management-09-traffic-mirror-0.html)

## 基本設定 {#basic-configuration}

以下の sidecar の例には、`reviews` Service と、Pod label に一致する `v1`／`v2` subset を持つ DestinationRule が必要です。同じ host に対して、VirtualService の代替設定は一度に 1 つだけ適用してください。mirror は主経路の route weight を分け合うのではなく、request の追加 copy を受け取ります。

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
      value: 100  # 100% mirroring
```

## 部分ミラーリング {#partial-mirroring}

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
      value: 10  # Mirror only 10%
```

## ベストプラクティス {#best-practices}

- mirror された response は破棄されます。これは failover でも、自動的な response 比較でもありません。
- write は shadow 側の宛先でも実行されます。本番 request を mirror する前に、shadow 側の database、queue、外部への副作用を分離してください。
- 小さな割合から始め、主経路の latency と shadow 側の容量を監視してください。mirroring により traffic と処理コストが増えます。
- 既定では mirror された Host／Authority に `-shadow` suffix が付与されます。shadow Service がこれを受け入れるよう設定してください。ambient waypoint では、選択した release の routing API が対応するかも評価してください。

## 参考資料

- [Istio Traffic Mirroring](https://istio.io/latest/docs/tasks/traffic-management/mirroring/)
