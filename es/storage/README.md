# Descripción general de Storage

> **Última actualización**: September 2, 2026

En el momento en que ejecutas cargas de trabajo con estado en Kubernetes, el almacenamiento deja de ser «algo que adjuntas» y se convierte en un dominio que determina el rendimiento, el costo y la disponibilidad. Esta sección cubre el almacenamiento en la nube en el orden que importa en la práctica: **cómo elegir → qué mide realmente → cómo operarlo**.

## Qué incluye esta sección

| Documento | Qué cubre |
|----------|----------------|
| [Benchmark medido de EBS gp2 vs gp3](./01-ebs-gp2-gp3-benchmark.md) | Por qué dos volúmenes idénticos de 100GiB difieren 10x en rendimiento — IOPS/latencia/throughput medidos con fio y el precipicio de créditos de ráfaga de gp2 |

Los fundamentos de Storage de Kubernetes y la configuración práctica de EKS se cubren en profundidad en otras partes de este libro. Lee esta sección junto con:

- [Storage de Kubernetes](../core/04-storage.md) — PV/PVC, StorageClass, aprovisionamiento dinámico, modos de acceso
- [Storage de EKS Parte 1: EBS, EFS](../eks/04-eks-storage-part1.md) — instalación del driver CSI y uso básico
- [Storage de EKS Parte 2: FSx for Lustre, S3, snapshots, rendimiento](../eks/04-eks-storage-part2.md)
- [Storage de EKS Parte 3: monitoreo, resolución de problemas, costo](../eks/04-eks-storage-part3.md)

## La pila de almacenamiento de un vistazo

Comprender la ruta desde una escritura de la aplicación hasta el volumen físico te indica qué capa responsabilizar cuando el rendimiento no cumple las expectativas:

```text
application write()
  → container filesystem (ext4/xfs)
    → kernel block layer (io scheduler, page cache or O_DIRECT)
      → EBS volume (per-volume-type IOPS/throughput limits)
        → EC2 instance EBS bandwidth limit  ← the one everyone forgets
```

Los propios límites del volumen y los **límites de ancho de banda/IOPS de EBS a nivel de instancia** son presupuestos independientes. Una m5.xlarge tiene una base de aproximadamente 6,000 IOPS; adjunta tres volúmenes gp3 de 3,000 IOPS cada uno y la instancia se convierte en el cuello de botella independientemente de para qué estén clasificados los volúmenes.

## Cómo elegir Storage de AWS

| Servicio | Modo de acceso | Características | Mejor opción |
|---------|-------------|-----------------|----------|
| **EBS (gp3/io2)** | RWO (nodo único) | Bloque, latencia de sub-ms | Bases de datos, estado de un solo Pod |
| **EFS** | RWX (varios nodos) | NFS, latencia de nivel ms, capacidad elástica | Configuración/contenido compartido, datos compartidos de entrenamiento de ML |
| **FSx for Lustre** | RWX | Sistema de archivos paralelo, alto throughput | HPC, entrenamiento de ML a gran escala |
| **S3 (Mountpoint CSI)** | RWX (con muchas lecturas) | Objetos, alto throughput / alta latencia | Data lakes, modelos y artefactos |
| **Instance store** | Local al nodo | NVMe, la menor latencia, **efímero** | Cachés, datos de shuffle, espacio temporal |

## Por qué medir en lugar de leer hojas de especificaciones

El almacenamiento es donde la brecha entre la hoja de datos y la experiencia real es mayor. Las trampas clásicas:

1. **Créditos de ráfaga de gp2** — un volumen nuevo funciona a 3,000 IOPS hasta que se agota el depósito de créditos y luego cae a su valor base (3 IOPS/GiB). Si tu prueba de carga terminó en menos de 30 minutos, pasaste de largo el precipicio sin verlo.
2. **Límites de volumen frente a límites de instancia** — consulta el diagrama de la pila anterior.
3. **Las conclusiones cambian con iodepth** — una prueba de latencia con profundidad de cola 1 y una prueba de IOPS con profundidad de cola 32 describen propiedades completamente diferentes del mismo volumen.

[El benchmark medido de EBS gp2 vs gp3](./01-ebs-gp2-gp3-benchmark.md) demuestra cada una de estas trampas con fio.
