# Duplicación de tráfico

Traffic Mirroring (o Shadow Traffic) es una técnica que replica en tiempo real el tráfico de producción para probar nuevas versiones.

## Tabla de contenido

1. [Descripción general de Traffic Mirroring](#traffic-mirroring-overview)
2. [Configuración básica](#basic-configuration)
3. [Duplicación parcial](#partial-mirroring)
4. [Buenas prácticas](#best-practices)

## Descripción general de Traffic Mirroring {#traffic-mirroring-overview}

![Un cliente envía una solicitud que responde la Versión 1 en la ruta activa; la misma solicitud se replica a la Versión 2 como copia sombra, cuya respuesta se descarta y nunca llega al cliente.](../../../.gitbook/assets/en-service-mesh-istio-traffic-management-09-traffic-mirror-0.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-service-mesh-istio-traffic-management-09-traffic-mirror-0.html)

## Configuración básica {#basic-configuration}

Estos ejemplos de sidecar requieren un Service `reviews` y subconjuntos `v1`/`v2` de DestinationRule que coincidan con las etiquetas de los Pods. Aplique una sola configuración alternativa de VirtualService para este host a la vez. El espejo no recibe una parte del peso de la ruta principal: recibe una copia adicional.

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

## Duplicación parcial {#partial-mirroring}

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

## Buenas prácticas {#best-practices}

- Las respuestas duplicadas se descartan; esto no es una conmutación por error ni una comparación automática de respuestas.
- Las escrituras también se ejecutan en el destino sombra. Aísle sus bases de datos, colas y efectos secundarios externos antes de duplicar solicitudes de producción.
- Comience con un porcentaje pequeño y supervise tanto la latencia principal como la capacidad del destino sombra. La duplicación agrega tráfico y costo de procesamiento.
- De forma predeterminada, el Host/Authority duplicado recibe el sufijo `-shadow`; configure el servicio sombra para que lo acepte. Evalúe la API de enrutamiento de la versión seleccionada para los waypoints ambient.

## Referencias

- [Traffic Mirroring de Istio](https://istio.io/latest/docs/tasks/traffic-management/mirroring/)
