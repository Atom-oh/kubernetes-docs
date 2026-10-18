# Cuestionario sobre requisitos previos de EKS Hybrid Nodes

> **Documento relacionado**: [Requisitos previos](../../eks-hybrid-nodes/01-prerequisites.md)
> **Última actualización**: 12 de septiembre de 2026

## Preguntas de opción múltiple

### 1. ¿Cuál de estos escenarios no es un motivo compatible para registrar máquinas como EKS Hybrid Nodes?

- A) Usar servidores GPU locales compatibles
- B) Mantener el procesamiento de aplicaciones cerca de los conjuntos de datos locales
- C) Registrar máquinas EC2/nube ordinarias como infraestructura de nodos híbridos
- D) Cargas de trabajo conectadas en el edge con recuperación probada

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Registrar máquinas EC2/nube ordinarias como infraestructura de nodos híbridos**

**Explicación:**
AWS admite infraestructura de nodos híbridos en hosts físicos o virtuales locales/edge operados por el cliente, no en infraestructura de nube. Registrar EC2 como nodo híbrido sigue generando cargos de Hybrid Nodes. Para los nodos en la nube, use los tipos de cómputo ordinarios de AWS. Hybrid Nodes requiere conectividad fiable; una etiqueta de ubicación por sí sola no demuestra cumplimiento normativo ni funcionamiento sin conexión.

</details>

### 2. ¿Qué afirmación sobre el sistema operativo coincide con la matriz actual de integración de AWS para nodos híbridos?

- A) Windows Server es la única opción
- B) Ubuntu 20.04/22.04/24.04, RHEL 8/9, AL2023 virtualizado y variantes de Bottlerocket para VMware compatibles
- C) Cualquier versión de macOS
- D) Cualquier imagen Linux recibe automáticamente soporte del sistema operativo de AWS

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Ubuntu 20.04/22.04/24.04, RHEL 8/9, AL2023 virtualizado y variantes de Bottlerocket para VMware compatibles**

**Explicación:**
Revise el mantenimiento de seguridad del proveedor, la arquitectura y el CNI/kernel elegido. Bottlerocket VMware v1.37.0 o posterior solo admite x86_64 y usa su propio procedimiento de arranque. AL2023 es para entornos virtualizados locales y no está cubierto por el soporte de sistemas operativos de AWS fuera de EC2. EKS kube-proxy para ARM a partir de la versión 1.31 requiere ARMv8.2+crypto; una regla genérica de kernel 5.4 o el nombre del modelo de CPU no bastan para completar la validación.

</details>

### 3. ¿Qué afirmación es incorrecta al evaluar la compatibilidad de una carga de trabajo GPU?

- A) Importa la compatibilidad entre el controlador, CUDA y la imagen del framework
- B) Los requisitos de memoria dependen de la carga de trabajo
- C) Importan el sistema operativo/kernel compatible y el runtime de contenedores
- D) Se puede ignorar la arquitectura de CPU una vez instalada una GPU

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: D) Se puede ignorar la arquitectura de CPU una vez instalada una GPU**

**Explicación:**
La arquitectura de CPU, la variante de GPU, los controladores, el sistema operativo/kernel, el toolkit/runtime de contenedores y la imagen de la aplicación deben ser compatibles entre sí. No existe un mínimo universal de 4 GB de GPU ni un requisito fijo de controlador 525/550 para Hybrid Nodes. No hace falta un compilador host `nvcc` solo para ejecutar un contenedor empaquetado correctamente; `nvidia-smi` y `nvcc` informan de componentes diferentes.

</details>

### 4. ¿Cómo deben interpretarse las recomendaciones básicas de recursos del host?

- A) 1 núcleo y 512 MB garantizan una configuración suficiente
- B) AWS recomienda al menos 1 vCPU y 1 GiB de RAM, sin un mínimo universal estricto
- C) Todas las cargas de trabajo requieren exactamente 4 núcleos y 8 GB
- D) Un disco de 50 GB garantiza que el nodo está listo

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) AWS recomienda al menos 1 vCPU y 1 GiB de RAM, sin un mínimo universal estricto**

**Explicación:**
Dimensione por separado el sistema operativo, kubelet/runtime, CNI/agentes, imágenes/registros y la carga de trabajo real. La respuesta anterior de dos núcleos y 2 GB y las recomendaciones de discos de 20/50/100 GB eran ejemplos de planificación incoherentes, no mínimos validados para una carga de trabajo. Del mismo modo, la recomendación general de AWS de 100 Mbps/200 ms para la red no es un umbral universal de aceptación.

</details>

### 5. ¿Qué componente no es necesario solo porque un host pase a ser un nodo EKS Hybrid?

- A) Un runtime CRI compatible, como containerd
- B) kubelet
- C) Docker Engine
- D) Los ayudantes de credenciales/autenticación elegidos de AWS

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Docker Engine**

**Explicación:**
La fuente del paquete containerd de Docker no es un requisito para ejecutar Docker Engine. En hosts que no sean Bottlerocket, `nodeadm install` instala dependencias, `config check` valida las entradas e `init` configura y une el nodo. La instalación/actualización mediante SSM requiere nodeadm 1.0.19 o posterior tras el cambio de clave de firma; la versión revisada es la 1.0.20. En RHEL, el runtime puede ser `docker` o uno preinstalado; se debe especificar `none` como distribución.

</details>

### 6. ¿Cuál es el enfoque correcto para desplegar H100 en EKS Hybrid Nodes?

- A) Instalar la versión 450.x en todos los hosts
- B) Considerar que un ejemplo antiguo con 525.x siempre es suficiente
- C) Exigir exactamente 535.x sin importar el framework
- D) Elegir un conjunto compatible de GPU/sistema operativo/controlador/CUDA/runtime y validar la aplicación

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: D) Elegir un conjunto compatible de GPU/sistema operativo/controlador/CUDA/runtime y validar la aplicación**

**Explicación:**
La tabla antigua mezclaba versiones mínimas y recomendadas del controlador, y contradecía su propia respuesta. Los valores 450/525/535/545/550 no constituyen un contrato de despliegue universal vigente. Verifique la variante H100 concreta, la rama de controlador compatible, la imagen del framework y los requisitos de funcionalidades; pruebe los cambios primero en un host de pruebas desalojado. En esta auditoría no se ejecutó ninguna GPU ni se hizo ningún benchmark de modelos.

</details>

## Referencias

- [Requisitos previos de Hybrid Nodes](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-prereqs.html)
- [Compatibilidad de sistemas operativos de Hybrid Nodes](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-os.html)
- [Referencia de nodeadm](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-nodeadm.html)
