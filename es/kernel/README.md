# Introducción al kernel de Linux

> **Versiones admitidas**: Linux 6.1 / 6.12 / 6.18 (Amazon Linux 2023), Kubernetes 1.33 o posterior (Amazon EKS)
> **Última actualización**: 12 de septiembre de 2026

## Contenido de esta sección

- Qué ejecutan realmente los contenedores y Kubernetes: las funciones del kernel que hay detrás de los espacios de nombres, cgroups, netfilter y conntrack
- La ruta que sigue un paquete dentro del kernel desde un pod hasta la NIC, y qué puedes observar y ajustar en cada punto
- Cómo afectan los parámetros del kernel al rendimiento y la estabilidad de las cargas de trabajo en los nodos de EKS, y qué conviene cambiar y qué dejar como está

## Por qué existe esta sección

La mayoría de la documentación de Kubernetes explica lo que ocurre **por encima de
una API declarativa**. Creas un pod y se inician los contenedores; creas un Service y
se distribuye el tráfico; estableces un límite de recursos y el contenedor no lo
supera.

Pero el conocimiento que necesitas para diagnosticar un incidente está una capa más
abajo.

| Síntoma en producción | Lo que ocurre en la capa del kernel |
|---|---|
| «El pod terminó con `OOMKilled`, pero la memoria del contenedor estaba por debajo del límite» | `memory.current` de cgroup v2 incluye la caché de páginas. Mirar solo el RSS no basta |
| «Las conexiones nuevas del nodo se descartan sin aviso» | Investiga el recuento y el máximo de conntrack, los contadores de inserción/descarte y los registros del kernel, junto con otras posibles causas de descarte de paquetes |
| «Establecí un límite de CPU y p99 empezó a tener picos» | Limitación de CFS/EEVDF. La utilización es baja, pero la tarea se detiene a la fuerza en cada período |
| «La comunicación entre pods del mismo nodo es inusualmente rápida» | El tráfico solo atraviesa el par veth y nunca llega a la NIC |
| «Tenemos miles de reglas de Service y aumentó la latencia» | Evaluación lineal de reglas en kube-proxy con el modo iptables |

**Ninguna de estas causas se ve en la capa de la API de Kubernetes.** El objetivo
de esta sección es cubrir esa brecha.

## Público y supuestos

- Ingenieros de infraestructura con experiencia operando EKS/Kubernetes que necesiten diagnosticar directamente las restricciones de recursos y los fallos de red
- Suponemos que conoces los comandos básicos de Linux y los conceptos de procesos
- Leer el código fuente del kernel o escribir módulos está fuera del alcance. Nos centramos en **lo que un operador puede observar y ajustar**

## Estructura de los documentos

| # | Documento | Pregunta que responde |
|---|----------|---------------------|
| 1 | [Funciones del kernel que sustentan los contenedores](./01-container-primitives.md) | ¿De qué se compone un contenedor? ¿Por qué es importante desde el punto de vista operativo el cambio de cgroup v1 a v2? |
| 2 | [Pila de red del kernel](./02-network-stack.md) | ¿Qué ruta sigue un paquete desde el socket hasta la NIC? ¿Dónde se pueden conectar hooks? |
| 3 | [Ajustes del kernel en nodos de EKS](./03-eks-node-tuning.md) | ¿Qué parámetros conviene cambiar y cuándo? ¿Cuándo es mejor dejar el valor predeterminado? |

## Cómo leer esta sección

El documento 1 es un requisito previo para los documentos 2 y 3. Sin conocer
cgroups y espacios de nombres, los ajustes del documento 3 no tendrán sentido en
los contextos descritos.

Si llegaste para diagnosticar un problema de red, bastan el **documento 2 y la
sección de red del documento 3**. Para los problemas de recursos (OOM, limitación
de CPU), sigue esta ruta: **la sección sobre cgroups del documento 1 → las
secciones sobre memoria y CPU del documento 3**.

## Documentos relacionados

- [Fundamentos de Linux](../basics/01-linux-basics.md) / [Operaciones avanzadas de Linux](../basics/02-linux-advanced.md): comandos y operaciones básicas
- [Tecnología de contenedores](../basics/03-container-technology.md): runtimes de contenedores y capas de imágenes
- [Fundamentos de eBPF](../basics/05-ebpf-fundamentals.md): tipos y usos de programas eBPF
- [Fundamentos de redes, parte 1](../basics/06-network-fundamentals-part1.md): desde los modelos por capas hasta la nube
- [Prueba comparativa de redes de pods](../networking/06-pod-network-benchmark.md): mediciones relacionadas con la teoría de esta sección
- [Optimización de recursos](../ops/10-resource-optimization.md): diseño de solicitudes y límites
- [Plano de datos del kernel de VPC Lattice](../service-mesh/vpc-lattice/07-kernel-datapath.md): capa del kernel para la interceptación local del enlace

## Nota sobre la precisión

El comportamiento del kernel cambia entre versiones. En particular, **los
parámetros ajustables cambian de ubicación y de nombre entre versiones del kernel**
(por ejemplo, de sysctl a debugfs). Esta sección se basa en las series del kernel
que incluye AL2023 (6.1 / 6.12 / 6.18), y señala la versión a la que se aplica cada
elemento dependiente de la versión.

Lo que no se haya confirmado con documentación oficial se marca con un bloque `Needs verification` en lugar de presentarse como un hecho. **Antes de aplicar cualquier parámetro a un clúster de producción, comprueba directamente su valor en la versión del kernel de ese nodo.**
