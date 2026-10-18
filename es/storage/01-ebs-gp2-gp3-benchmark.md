# EBS gp2 vs gp3: benchmark medido

> **Entorno de prueba registrado**: Kubernetes 1.36 (Amazon EKS), controlador EBS CSI, fio 3.36
> **Última actualización**: 16 de octubre de 2026

La conocida frase de AWS —«mueva gp2 a gp3, ahorre un 20 % y obtenga un rendimiento igual o mejor»— es famosa, pero es difícil encontrar un gráfico que muestre **cuándo y de qué forma** se manifiesta esa diferencia en una PVC de Kubernetes. Este artículo conecta **una PVC gp2 de 100 GiB y una PVC gp3 de 100 GiB** a un único nodo de EKS y somete ambas a una carga intensa de fio durante 45 minutos. El objetivo no es afirmar que «gp2 es lento», sino mostrar que **gp2 ofrece un rendimiento indistinguible de gp3 durante 33 minutos y luego cae a una décima parte en un segundo**. Los valores que se muestran corresponden a la ejecución original; no son resultados garantizados de una repetición. Al comparar ejecuciones, registre los créditos iniciales, las versiones del controlador y de la imagen, y las condiciones del nodo.

![Diagrama de arquitectura: un Pod de fio envía E/S aleatoria de 4k a través de un dispositivo de bloques adjunto mediante EBS CSI hacia gp3 (3.000 IOPS fijos) y gp2 (referencia de 300 IOPS más un depósito de créditos de E/S), cuyo saldo se informa a CloudWatch BurstBalance.](../.gitbook/assets/en-storage-01-ebs-gp2-gp3-benchmark-0.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-storage-01-ebs-gp2-gp3-benchmark-0.html)

## TL;DR — Lo que medimos

| Métrica (100 GiB, m5.xlarge) | gp3 | gp2 |
|-----------------------------|-----|-----|
| IOPS de lectura aleatoria de 4k (qd32) | **3.001** de promedio, plano durante 600 s (mín. 2.991) | **3.001 → 300**, precipicio en 1.999 s |
| Latencia p99 de lectura aleatoria de 4k (qd32) | 12,9 ms | 109,6 ms (dominada por el período posterior al precipicio) |
| IOPS de escritura aleatoria de 4k (qd32, tras el agotamiento de créditos) | **3.025** | 601 (incluye un depósito parcialmente recargado) |
| Latencia de lectura aleatoria de 4k (qd1) | prom. **0,56 ms** / p99 0,87 ms | prom. 1,65 ms — bimodal: p50 0,60 / p95 3,39 ms |
| Lectura / escritura secuencial de 1 MiB | 127 / 126 MiB/s (referencia de 125 MiB/s) | 130 / 129 MiB/s (límite de 128 MiB/s para ≤170 GiB) |
| Costo mensual (región de Seúl, 100 GiB) | **$9.12** | $11.40 |

En una frase: **para la misma capacidad, gp2 le vende 33 minutos de 3.000 IOPS a un precio un 25 % mayor.**

## Entorno de prueba

| Elemento | Valor |
|------|-------|
| Clúster | Amazon EKS, Kubernetes 1.36, ap-northeast-2 |
| Nodo | **m5.xlarge** (4 vCPU, 16 GiB), aprovisionado por Karpenter; límites de EBS de la instancia: referencia de 6.000 IOPS / 1.150 Mbps (143,75 MB/s ≈ 137 MiB/s), ráfaga de 18.750 IOPS / 4.750 Mbps |
| Volúmenes | un EBS **gp2 de 100 GiB** y un **gp3 de 100 GiB**, configuración predeterminada (`StorageClass` `gp2` / `gp3`, controlador EBS CSI) |
| Pod | `alpine:3.20` + `fio 3.36`, `direct=1` (omite la caché de páginas), motor `libaio`, archivo de prueba de 8 GiB |
| Ejecución | **Los dos volúmenes nunca se midieron simultáneamente**; varios volúmenes comparten el presupuesto sostenido y de ráfaga de E/S de la instancia, por lo que las pruebas concurrentes introducirían interferencias |
| Precios | gp2 $0.114/GB-mes, gp3 $0.0912/GB-mes + IOPS adicionales $0.0057/IOPS-mes + rendimiento adicional $0.0456/MiB/s-mes (región de Seúl, Pricing API, septiembre de 2026) |

El `nodeSelector` fija m5.xlarge por un único motivo: su límite de EBS a nivel de instancia (6.000 IOPS) supera holgadamente el límite del volumen (3.000), lo que deja margen para observar el comportamiento del volumen. Confirme también el cuello de botella con la E/S total del nodo y las métricas de límites excedidos de la instancia y del volumen. En una instancia más pequeña (m5.large tiene una referencia de 3.600 IOPS), ambos límites se solapan y los resultados son difíciles de interpretar.

### Manifiesto de Deployment

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: bench-storage
---
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: bench-gp2
provisioner: ebs.csi.aws.com
parameters:
  type: gp2
  encrypted: "true"
volumeBindingMode: WaitForFirstConsumer
reclaimPolicy: Delete
---
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: bench-gp3
provisioner: ebs.csi.aws.com
parameters:
  type: gp3
  encrypted: "true"
  iops: "3000"
  throughput: "125"
volumeBindingMode: WaitForFirstConsumer
reclaimPolicy: Delete
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: bench-gp2
  namespace: bench-storage
spec:
  accessModes: ["ReadWriteOnce"]
  storageClassName: bench-gp2
  resources:
    requests:
      storage: 100Gi
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: bench-gp3
  namespace: bench-storage
spec:
  accessModes: ["ReadWriteOnce"]
  storageClassName: bench-gp3
  resources:
    requests:
      storage: 100Gi
---
apiVersion: v1
kind: Pod
metadata:
  name: fio
  namespace: bench-storage
  annotations:
    karpenter.sh/do-not-disrupt: "true"   # keep consolidation from evicting a 45-minute measurement
spec:
  nodeSelector:
    node.kubernetes.io/instance-type: m5.xlarge
  containers:
    - name: fio
      image: alpine:3.24.2
      command: ["sh", "-c", "apk add --no-cache fio && fio --version && sleep infinity"]
      resources:
        requests: { cpu: "1", memory: 1Gi }
        limits: { cpu: "2", memory: 2Gi }
      volumeMounts:
        - { name: gp2, mountPath: /mnt/gp2 }
        - { name: gp3, mountPath: /mnt/gp3 }
  volumes:
    - name: gp2
      persistentVolumeClaim: { claimName: bench-gp2 }
    - name: gp3
      persistentVolumeClaim: { claimName: bench-gp3 }
  restartPolicy: Never
```

> La anotación `karpenter.sh/do-not-disrupt` se añadió porque el primer intento del benchmark falló sin ella. Cuando terminó la otra carga de trabajo del nodo, Karpenter consideró que el nodo estaba «infrautilizado», inició la consolidación y desalojó el Pod de fio (salida 137) en mitad de la ejecución de 45 minutos. La anotación bloquea algunas interrupciones voluntarias, pero no protege frente a fallos del nodo, interrupciones de instancias Spot, terminaciones forzadas ni al vencimiento de `terminationGracePeriod`; un PDB tampoco evita fallos involuntarios. Persista los resultados y haga que la ejecución se pueda reanudar.

### Comandos de fio

Cada fase usa las opciones comunes siguientes y se ejecutó de una en una, en este orden.

```bash
COMMON="--ioengine=libaio --direct=1 --group_reporting --output-format=json"

# 0. lay out the test files (8 GiB, sequential write)
fio --name=layout --filename=/mnt/gp3/testfile --size=8G --rw=write --bs=1M $COMMON
fio --name=layout --filename=/mnt/gp2/testfile --size=8G --rw=write --bs=1M $COMMON

# 1. 4k random read, qd32: gp3 for 600 s, gp2 for 2,700 s (45 minutes, to catch the credit cliff)
fio --name=gp3-randread --filename=/mnt/gp3/testfile --size=8G --rw=randread --bs=4k \
    --iodepth=32 --runtime=600  --time_based --write_iops_log=gp3_rr --log_avg_msec=1000 $COMMON
fio --name=gp2-randread --filename=/mnt/gp2/testfile --size=8G --rw=randread --bs=4k \
    --iodepth=32 --runtime=2700 --time_based --write_iops_log=gp2_rr --log_avg_msec=1000 $COMMON

# 2. 4k random write, qd32, 120 s (gp2 has exhausted its credits by now)
fio --name=gp3-randwrite --filename=/mnt/gp3/testfile --size=8G --rw=randwrite --bs=4k --iodepth=32 --runtime=120 --time_based $COMMON
fio --name=gp2-randwrite --filename=/mnt/gp2/testfile --size=8G --rw=randwrite --bs=4k --iodepth=32 --runtime=120 --time_based $COMMON

# 3. 4k random read, qd1, 60 s: end-to-end completion latency at low concurrency
fio --name=gp3-lat --filename=/mnt/gp3/testfile --size=8G --rw=randread --bs=4k --iodepth=1 --runtime=60 --time_based $COMMON
fio --name=gp2-lat --filename=/mnt/gp2/testfile --size=8G --rw=randread --bs=4k --iodepth=1 --runtime=60 --time_based $COMMON

# 4. 1 MiB sequential read/write, qd8, 60 s: throughput ceiling
fio --name=gp3-seqread  --filename=/mnt/gp3/testfile --size=8G --rw=read  --bs=1M --iodepth=8 --runtime=60 --time_based $COMMON
fio --name=gp3-seqwrite --filename=/mnt/gp3/testfile --size=8G --rw=write --bs=1M --iodepth=8 --runtime=60 --time_based $COMMON
fio --name=gp2-seqread  --filename=/mnt/gp2/testfile --size=8G --rw=read  --bs=1M --iodepth=8 --runtime=60 --time_based $COMMON
fio --name=gp2-seqwrite --filename=/mnt/gp2/testfile --size=8G --rw=write --bs=1M --iodepth=8 --runtime=60 --time_based $COMMON
```

## Medición 1 — 45 minutos de lecturas aleatorias de 4k: el precipicio de créditos

![Serie temporal de IOPS: gp3 mantiene 3.000 IOPS constantes durante 10 minutos; gp2 mantiene 3.000 IOPS y luego cae verticalmente a 300 IOPS a los 1.999 segundos.](../.gitbook/assets/en-storage-01-ebs-gp2-gp3-iops-timeline.svg)

Este es el registro de IOPS por segundo que fio guardó (2.699 muestras para gp2 y 600 para gp3), representado tal cual. La tabla siguiente excluye la primera muestra de un segundo de cada registro (5.997 en ambos volúmenes), un transitorio inicial cuya causa requiere un análisis aparte; incluirla puede cambiar el promedio resumido.

| | gp3 (600 s) | gp2 antes del precipicio (0–1.999 s) | gp2 después del precipicio (2.000–2.700 s) |
|---|---|---|---|
| IOPS promedio | **3.001** | **3.001** | **300** |
| Mín. / máx. | 2.991 / 3.004 | 2.997 / 3.005 | 297 / 304 |
| Latencia promedio (qd32) | 10,4 ms | ≈10,4 ms | ≈106 ms |

Cómo interpretarlo:

- **Antes del precipicio, gp2 es indistinguible de gp3.** Ambos entregan 3.001 IOPS, ambos se sitúan en un p50 de 10,0–10,2 ms. «gp2 es lento» simplemente es falso aquí: un volumen gp2 con créditos es un volumen de 3.000 IOPS.
- **El precipicio tomó un segundo.** 3.001 IOPS a los 1.998 s, 2.659 a los 1.999 s, 300 a los 2.000 s. No se degrada gradualmente; el 90 % de la capacidad desaparece como si se accionara un interruptor. Desde el punto de vista de la aplicación, este es el patrón de incidente «las consultas a la base de datos de repente son 10 veces más lentas y nadie desplegó nada».
- **Las cifras coinciden con la documentación de AWS con una precisión de un segundo.** Un volumen gp2 de 100 GiB tiene una referencia de 3 IOPS/GiB × 100 = **300 IOPS**, un depósito de 5,4 M de créditos y una duración de ráfaga de `5,400,000 ÷ (3,000 − 300) = 2,000 s`. La tabla de AWS indica «100 GiB → 2.000 segundos»; nosotros medimos 1.999.
- **Los 106 ms de latencia no significan que el volumen sea lento.** La ley de Little (latencia promedio = E/S pendientes ÷ rendimiento) da 32 ÷ 300 = 106,7 ms. Mantenemos 32 E/S en curso mientras solo se completan 300 por segundo, así que la cola crece. Los 10,4 ms a 3.000 IOPS se explican por la misma aritmética (32 ÷ 3.000 = 10,7 ms). **Esto aproxima el tiempo total de respuesta cuando hay unas 32 E/S en curso en promedio, pero no separa el tiempo en cola del tiempo de servicio. Compare la misma métrica fio (`slat`, `clat` o `lat`) entre ejecuciones.**

> **Divulgación de las condiciones de prueba**: unos 13 minutos antes de la ejecución registrada, el primer intento —interrumpido por la expulsión de Karpenter— ya había sometido este mismo volumen gp2 a 3.000 IOPS durante unos 8 minutos (14:55–15:03 UTC). Un modelo simple de créditos predeciría que ese consumo previo adelantara el precipicio respecto de los 2.000 s; sin embargo, lo observamos a los 2.000 s. No pudimos determinar la causa porque se desconoce la duración exacta de la E/S antes de la expulsión. Considere **la caída del 90 % en un segundo y el mínimo de 300 IOPS como resultados observados en esta ejecución**, y **use la fórmula de AWS (2.000 s) para planificar la duración exacta**.

## Medición 2 — Escrituras aleatorias tras el agotamiento de créditos: 3.025 frente a 601 IOPS

| Escritura aleatoria de 4k, qd32, 120 s | gp3 | gp2 (justo después del agotamiento) |
|---|---|---|
| IOPS | **3.025** | **601** |
| Latencia promedio | 10,3 ms | 52,0 ms |
| p50 / p95 / p99 | 10,2 / 11,2 / 12,0 ms | 11,1 / 109,6 / 133,7 ms |

La verdadera lección aquí es por qué gp2 produjo 601 IOPS en lugar de su referencia de 300. Durante los 120 segundos inmediatamente anteriores a la prueba de escritura de gp2 (mientras se ejecutaba la prueba de escritura de gp3), gp2 estuvo inactivo y acumuló **300 créditos/s × 120 s = 36.000 créditos**. Gastar esos 36.000 durante una prueba de 120 segundos agrega 300 IOPS sobre la referencia de 300: exactamente **600 IOPS**. Medido: 601.

Por tanto, el depósito de créditos de gp2 no está «vacío para siempre una vez agotado»; es **una cuenta bancaria que se recarga lentamente cuando el volumen descansa**. Por eso gp2 con tráfico intermitente a veces es rápido y a veces lento, un patrón doloroso de depurar porque rara vez se reproduce bajo demanda. La distribución bimodal — p50 en 11 ms, p95 en 110 ms — es la huella: los segundos en que quedan créditos son rápidos; los segundos sin ellos permanecen en la cola.

## Medición 3 — Latencia qd1: distribución a baja concurrencia

Una profundidad de cola de 1 reduce la concurrencia generada por la aplicación. El kernel, la virtualización, el servicio EBS y la limitación de rendimiento también pueden contribuir a la latencia; esta prueba no mide únicamente la SSD física.

| Lectura aleatoria de 4k, qd1, 60 s | gp3 | gp2 (limitado) |
|---|---|---|
| Latencia promedio | **0,564 ms** | 1,651 ms |
| p50 | 0,569 ms | **0,602 ms** |
| p95 | 0,627 ms | 3,391 ms |
| p99 | 0,872 ms | 3,555 ms |
| IOPS alcanzados | 1.759 | 603 |

- **Los 0,56 ms de gp3 (p99 0,87 ms) son el tiempo real de ida y vuelta del SSD de uso general de EBS en este entorno.** En qd1, 1.759 IOPS se mantiene por debajo del límite de 3.000, por lo que no hubo limitación y la latencia por sí sola determinó el rendimiento (1 ÷ 0,564 ms ≈ 1.773).
- **Observe el p50 de gp2: 0,602 ms.** La mitad de sus E/S son tan rápidas como las de gp3. Un p50 similar no demuestra que los dispositivos físicos o el funcionamiento interno del servicio sean idénticos. La otra mitad llegó a 3,4–3,6 ms porque las E/S que excedían la asignación por segundo (603 IOPS; el mismo cálculo de la Medición 2: 18.000 créditos acumulados durante los 60 segundos de reposo, más la referencia de 300) quedaron retenidas en la cola de limitación.
- Conclusión práctica: **la limitación aparece en la forma de la distribución, no en el promedio.** Un panel que muestra solo la latencia media registra 1,6 ms — «un poco más lento» — mientras que p95 se ha multiplicado por 6. Por eso los paneles de almacenamiento necesitan p50 junto a p95/p99.

## Medición 4 — 1 MiB secuencial: ambos tienen un límite de 125–128 MiB/s

| Secuencial de 1 MiB, qd8, 60 s | lectura gp3 | escritura gp3 | lectura gp2 | escritura gp2 |
|---|---|---|---|---|
| Rendimiento | 127,3 MiB/s | 126,0 MiB/s | 130,3 MiB/s | 128,9 MiB/s |
| Latencia promedio | 58,0 ms | 58,5 ms | 56,7 ms | 57,3 ms |

Aquí gp2 y gp3 son efectivamente idénticos. gp3 se detiene en su referencia de 125 MiB/s; gp2 se detiene en 128 MiB/s, el límite para volúmenes de 170 GiB o menos. La aritmética también explica por qué la prueba secuencial de gp2 no se ralentizó debido a su depósito de créditos vacío: EBS cuenta una E/S de 1 MiB como cuatro operaciones de 256 KiB, así que 130 MiB/s ≈ 520 IOPS, dentro de los 36.000 créditos acumulados durante los 120 segundos de descanso anteriores. El límite de rendimiento se activó antes que el límite de IOPS.

Un aspecto adicional: la referencia de ancho de banda EBS de esta instancia m5.xlarge es 1.150 Mbps ≈ **137 MiB/s**. Un volumen gp3 configurado para 250 MiB/s puede superar los 137 MiB/s mientras la instancia tenga capacidad de ráfaga disponible. **Planifique la demanda sostenida a largo plazo según la referencia de aproximadamente 137 MiB/s.** AWS especifica el rendimiento máximo durante 30 minutos al menos una vez cada 24 horas; no garantiza una asignación invariable de exactamente 30 minutos. Revise la columna de ancho de banda EBS de la ficha de la instancia antes de actualizar un volumen. El análisis completo del [benchmark de ClickHouse](../database/01-clickhouse-on-eks.md) se detuvo en esta misma franja de 125–137 MiB/s por el mismo motivo.

## En dólares

Con precios de la región de Seúl (Pricing API, septiembre de 2026), «¿cómo obtengo 3.000 IOPS?» no deja ningún motivo para permanecer en gp2.

| Configuración | Costo mensual | IOPS sostenibles | Rendimiento |
|---------------|--------------|------------------|------------|
| gp2 100 GiB | $11.40 | **300** (ráfaga de 3.000 durante como máximo 33 minutos) | 128 MiB/s |
| gp3 100 GiB (predeterminado) | **$9.12** | **3.000**, ilimitados | 125 MiB/s |
| gp3 100 GiB + 6.000 IOPS | $26.22 ($9.12 + 3.000 × $0.0057) | 6.000 | 125 MiB/s |
| gp3 100 GiB + 250 MiB/s | $14.82 ($9.12 + 125 × $0.0456) | 3.000 | 250 MiB/s |
| gp2 1.000 GiB (un volumen «dimensionado para IOPS») | $114.00 | 3.000 | 250 MiB/s |

La última fila es el desperdicio más común en la práctica. En la era de gp2, la práctica estándar para un conjunto de datos de 100 GiB que necesitaba IOPS era asignar 1 TiB. gp3 de 100 GiB proporciona los mismos 3.000 IOPS por **$9.12**: 12,5 veces más barato ($114.00 ÷ $9.12). Desacoplar los IOPS de la capacidad es la esencia de gp3, y esta tabla es la consecuencia.

## Migrar a gp3 en Kubernetes

### Volúmenes nuevos: hacer de gp3 el StorageClass predeterminado

Los valores predeterminados de StorageClass varían según la versión del clúster y el método de aprovisionamiento. Inspeccione el provisioner, el tipo y las anotaciones de valor predeterminado con `kubectl get storageclass -o yaml`. El ejemplo siguiente usa EBS CSI estándar; ajuste explícitamente cualquier clase predeterminada existente.

```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: gp3
  annotations:
    storageclass.kubernetes.io/is-default-class: "true"
provisioner: ebs.csi.aws.com
parameters:
  type: gp3
  encrypted: "true"
volumeBindingMode: WaitForFirstConsumer
allowVolumeExpansion: true
```

```bash
# Run only if gp2 actually exists and is the default.
kubectl annotate storageclass gp2 storageclass.kubernetes.io/is-default-class="false" --overwrite
kubectl apply -f gp3-storageclass.yaml
```

### PVC existentes: cambio in situ con VolumeAttributesClass

`VolumeAttributesClass` (`storage.k8s.io/v1`, GA desde Kubernetes 1.34) cambia el tipo de un volumen sin eliminar el PVC. El controlador EBS CSI admite los parámetros `type`, `iops` y `throughput`, y llama internamente a EBS Elastic Volumes (`ModifyVolume`), por lo que el Pod sigue ejecutándose.

```yaml
apiVersion: storage.k8s.io/v1
kind: VolumeAttributesClass
metadata:
  name: gp3-baseline
driverName: ebs.csi.aws.com
parameters:
  type: gp3
```

Guarde la VAC anterior como `gp3-baseline-volumeattributesclass.yaml`. Compruebe las API disponibles con `kubectl api-resources --api-group=storage.k8s.io` e instale versiones compatibles de EBS CSI, external-provisioner y resizer. Seleccione el espacio de nombres de la PVC. Si especifica solo el tipo, puede conservar un rendimiento de gp2 superior al de referencia de gp3 y generar un cargo adicional.

```bash
kubectl apply -f gp3-baseline-volumeattributesclass.yaml
kubectl patch pvc data-postgres-0 --type=merge -p '{"spec":{"volumeAttributesClassName":"gp3-baseline"}}'
kubectl get pvc data-postgres-0 -o jsonpath='{.status.currentVolumeAttributesClassName}'
```

Dos advertencias: EBS exige que una modificación llegue al estado `completed` antes de iniciar la siguiente en el mismo volumen (una modificación de un volumen de 1 TiB suele tardar hasta seis horas, aunque la finalización es de mejor esfuerzo) y permite **como máximo cuatro modificaciones por volumen en cualquier período móvil de 24 horas**. Agrupe los cambios de tipo, IOPS y rendimiento en una sola solicitud. En Kubernetes 1.31–1.33, verifique la API `v1beta1` de la distribución y la configuración de las feature gates del plano de control y de los sidecars. Ni `ModifyVolume` directo ni una VAC cambian automáticamente el `storageClassName` existente. Gestione los atributos deseados mediante PVC/VAC y compruebe tanto el estado de modificación de la PVC como el tipo, las IOPS y el rendimiento reales de EBS.

### Crear una alarma para cualquier gp2 restante

Hasta que termine la migración, cree una alarma sobre la métrica de EBS de CloudWatch **`BurstBalance`** (porcentaje de créditos restantes). Para el volumen gp2 de este artículo, un 15 % equivale a unos cinco minutos con una carga constante de 3.000 IOPS. Tenga en cuenta el consumo real, los períodos de evaluación de la alarma y los datos ausentes. El precipicio llega sin aviso; el saldo de créditos sí avisa.

## Cómo reproducirlo

1. Aplique el manifiesto anterior: `kubectl apply -f bench-storage.yaml`; luego espere a que el Pod esté listo con `kubectl wait -n bench-storage pod/fio --for=condition=Ready --timeout=300s`.
2. Ponga los comandos de fio en un script de shell dentro del Pod y **ejecútelo con `nohup`**, guardando los resultados en un volumen (`/mnt/gp3/results`). No suponga que `kubectl exec` permanecerá activo durante 45 minutos; el contenido de `/tmp` del Pod desaparece cuando se elimina.
3. Grafique directamente la salida de `--write_iops_log` (`*_iops.1.log`, formato `time_ms, iops, ...`) para obtener la serie temporal de IOPS.
4. Antes de eliminar el espacio de nombres dedicado `bench-storage`, exporte fuera del clúster el JSON sin procesar, los registros de IOPS, las series de CloudWatch y la configuración de PVC/EBS. Este ejemplo usa `reclaimPolicy: Delete`, así que también se borran los datos. Elimine por separado las StorageClass de ámbito de clúster `bench-gp2` y `bench-gp3`. Los cargos dependen del uso real de nodos, volúmenes, plano de control de EKS y red, incluido el tiempo que los recursos permanezcan después de la ejecución.

## Advertencias

- **Un solo volumen, una sola ejecución.** AWS diseña tanto gp2 como gp3 para «ofrecer el rendimiento aprovisionado el 99 % del tiempo», por lo que un volumen diferente en otro día puede desviarse unos pocos puntos porcentuales en IOPS. El tema de este artículo es **la forma del modelo de créditos**, no los valores absolutos.
- Consulte la divulgación de la Medición 1 sobre la carga previa en el volumen gp2 antes de medir el precipicio.
- `direct=1` omite la caché de páginas. Una base de datos real, gracias a su buffer pool y a la caché del SO, sobrevive con muchos menos IOPS, que es precisamente la razón por la que el precipicio de gp2 aparece «solo a veces» y tarda tanto en diagnosticarse.
- Los volúmenes gp2 de más de 100 GiB tienen valores de referencia proporcionalmente mayores (334 GiB → 1.002 IOPS); a partir de 1.000 GiB, la referencia es de al menos 3.000 IOPS y no se produce el precipicio. Estas conclusiones se aplican a **volúmenes gp2 cuya referencia sea inferior a 3.000 IOPS**.

## Lecturas relacionadas

- [Descripción general de almacenamiento](./README.md) — cómo elegir el almacenamiento de EKS y dónde encaja este benchmark
- [Almacenamiento de EKS, parte 1](../eks/04-eks-storage-part1.md) — instalación del controlador EBS CSI y conceptos básicos de StorageClass
- [Benchmark medido de ClickHouse en EKS](../database/01-clickhouse-on-eks.md) — cómo aparece en un análisis completo de una base de datos real el límite de rendimiento de 125 MiB/s descrito en este artículo

## Fuentes de referencia

- [Rendimiento de EBS gp2/gp3](https://docs.aws.amazon.com/ebs/latest/userguide/general-purpose.html)
- [Ancho de banda EBS optimizado para EC2](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ebs-optimized.html)
- [Consideraciones sobre la modificación de volúmenes EBS](https://docs.aws.amazon.com/ebs/latest/userguide/ebs-modify-volume.html)
- [VolumeAttributesClass](https://kubernetes.io/docs/concepts/storage/volume-attributes-classes/)
- [Modificación de volúmenes con el controlador EBS CSI](https://github.com/kubernetes-sigs/aws-ebs-csi-driver/blob/master/docs/modify-volume.md)
- [Interrupciones de Karpenter](https://karpenter.sh/docs/concepts/disruption/)
- [Definiciones de latencia de fio](https://github.com/axboe/fio/blob/master/HOWTO.rst)
- [Soporte de versiones de Alpine](https://alpinelinux.org/releases/)
