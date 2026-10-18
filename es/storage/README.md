# Descripción general del almacenamiento

> **Última actualización**: 11 de septiembre de 2026

Cuando se ejecutan cargas de trabajo con estado en Kubernetes, el almacenamiento deja de ser «algo que se conecta» y se convierte en un ámbito que determina el rendimiento, el costo y la disponibilidad. Esta sección aborda el almacenamiento en la nube en el orden que importa en la práctica: **cómo elegir → qué mide realmente → cómo operarlo**.

## Qué incluye esta sección

| Documento | Contenido |
|----------|----------------|
| [Benchmark medido de EBS gp2 frente a gp3](./01-ebs-gp2-gp3-benchmark.md) | Por qué dos volúmenes idénticos de 100 GiB difieren 10 veces en rendimiento: IOPS, latencia y throughput medidos con fio, y el límite abrupto de los créditos de ráfaga de gp2 |

Los fundamentos del almacenamiento de Kubernetes y la configuración práctica de EKS se explican en profundidad en otras partes de este libro. Consulte esta sección junto con:

- [Almacenamiento de Kubernetes](../core/04-storage.md): PV/PVC, StorageClass, aprovisionamiento dinámico y modos de acceso
- [Almacenamiento de EKS, parte 1: EBS y EFS](../eks/04-eks-storage-part1.md): instalación del controlador CSI y uso básico
- [Almacenamiento de EKS, parte 2: FSx for Lustre, S3, instantáneas y rendimiento](../eks/04-eks-storage-part2.md)
- [Almacenamiento de EKS, parte 3: monitoreo, solución de problemas y costos](../eks/04-eks-storage-part3.md)

## Pila de almacenamiento de un vistazo

Comprender la ruta desde una escritura de la aplicación hasta el volumen físico permite identificar qué capa investigar cuando el rendimiento no cumple las expectativas:

```text
application write()
  → mounted volume filesystem (ext4/xfs)
    → guest kernel and block device
      → EC2 EBS path (IOPS/bandwidth shared by all volumes)
        → EBS service and volume (per-volume IOPS/throughput limits)
```

Los límites propios del volumen y los **límites de ancho de banda/IOPS de EBS a nivel de instancia** son presupuestos independientes. Una m5.xlarge tiene una base de aproximadamente 6.000 IOPS; si se usan simultáneamente tres volúmenes gp3 a 3.000 IOPS cada uno, se solicitan 9.000 IOPS, por encima de esa base sostenida. Compruebe también la capacidad de ráfaga de la instancia y el tráfico de los demás volúmenes.

## Cómo elegir almacenamiento de AWS

| Servicio | Modo de acceso | Características | Uso más adecuado |
|---------|-------------|-----------------|----------|
| **EBS (gp3/io2)** | RWO (un solo nodo) | Bloques; la latencia depende del tipo, la carga y la profundidad de cola | Bases de datos, estado de un solo Pod |
| **EFS** | RWX (varios nodos) | NFS, latencia de milisegundos, capacidad elástica | Configuración y contenido compartidos, datos de entrenamiento de ML compartidos |
| **FSx for Lustre** | RWX | Sistema de archivos paralelo, alto throughput | HPC, entrenamiento de ML a gran escala |
| **S3 (Mountpoint CSI)** | RWX (principalmente lectura) | Almacenamiento de objetos; semántica de operaciones distinta de POSIX/NFS | Lagos de datos, modelos y artefactos |
| **Instance store** | Local al nodo | NVMe, latencia mínima, **efímero** | Cachés, datos de shuffle, espacio de trabajo temporal |

RWO permite que varios Pods se ejecuten en un mismo nodo; no garantiza que haya un solo Pod. Excepciones como Multi-Attach de io2 requieren compatibilidad específica y un diseño de concurrencia para el sistema de archivos y la aplicación. Mountpoint para S3 no es un sistema de archivos compartido POSIX de propósito general: compruebe que admita las operaciones de modificación, cambio de nombre y bloqueo que necesita la carga de trabajo. Los datos de Instance store pueden sobrevivir a un reinicio, pero se pueden perder al detener o terminar la instancia.

## Por qué medir en lugar de leer hojas de especificaciones

El almacenamiento es el ámbito donde más se nota la diferencia entre la hoja de datos y la experiencia real. Estas son las trampas habituales:

1. **Créditos de ráfaga limitados de gp2**: los volúmenes con una base inferior a 3.000 IOPS pueden usar los créditos disponibles para alcanzar una tasa de ráfaga. La duración depende del saldo inicial, la capacidad y la carga. Un volumen gp2 de 100 GiB que funciona a 3.000 IOPS alcanza ese límite en unos 33 minutos según el cálculo; una prueba breve puede no detectar el rendimiento posterior al agotamiento.
2. **Límites del volumen frente a los de la instancia**: consulte el diagrama de la pila anterior.
3. **Las conclusiones cambian con iodepth**: una prueba de latencia con profundidad de cola 1 y una prueba de IOPS con profundidad de cola 32 describen propiedades completamente distintas del mismo volumen.

[El benchmark medido de EBS gp2 frente a gp3](./01-ebs-gp2-gp3-benchmark.md) demuestra cada una de estas trampas con fio.

## Referencias

- [Rendimiento de EBS](https://docs.aws.amazon.com/ebs/latest/userguide/general-purpose.html)
- [Límites de EBS en EC2](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ebs-optimized.html)
- [Semántica de Mountpoint para S3](https://github.com/awslabs/mountpoint-s3/blob/main/doc/SEMANTICS.md)
