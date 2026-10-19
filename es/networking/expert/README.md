# Ruta de estudio avanzada de redes

> **Recursos comprobados**: 15 de septiembre de 2026
>
> **Entorno**: máquinas virtuales desechables Ubuntu Server 24.04 LTS o Rocky Linux 9 para ejercicios de host. Las herramientas de enrutamiento/EVPN y los entornos de nube tienen requisitos previos propios por capítulo.

Estos cuadernos avanzados continúan el [curso para principiantes](../beginner/README.md). Relaciona los principios de los protocolos con el código y los paquetes; después, evalúa políticas de enrutamiento, rendimiento de Linux y diseños de nube usando pruebas.

El objetivo del nivel avanzado es **definir qué debería ser cierto, probar hipótesis mediante observaciones y explicar el impacto y la recuperación de un cambio**. Un periodo fijo de estudio o una certificación por sí solos no garantizan esa capacidad.

## Comprobación inicial {#entry-check}

Pasa al capítulo 1 cuando puedas explicar y reproducir lo siguiente:

- Distinguir las funciones de IP, subred, gateway y DNS de las de MAC/ARP.
- Leer `ip route get`, `ss` y una captura limitada de `tcpdump`, e identificar el punto de observación.
- Verificar el acceso SSH con clave y la política del firewall del laboratorio, y restaurar el estado anterior.
- Distinguir un error HTTP, un fallo de conexión y un fallo de resolución de nombres.
- Separar las rutas de administración y de experimentación, e identificar tus propios archivos, máquinas virtuales y contenedores.

Usa el [proyecto integrador para principiantes](../beginner/08-container-cloud-capstone.md) para repasar las habilidades que te falten. Completa la [preparación de herramientas del sistema invitado](../beginner/README.md#guest-tools) cuando no haya un comando de host disponible.

## Seis cuadernos {#course-map}

Cada fila sigue el flujo **lectura → experimento o validación de diseño → pruebas → cuestionario explicado**. Los cursos externos proporcionan el ámbito de lectura; estos cuadernos ofrecen una forma de evaluar tus propios resultados.

| Orden | Cuaderno | Entregable |
|---|---|---|
| 1 | [Proyectos de protocolos e implementación](01-protocol-projects.md) · [Cuestionario](../../quizzes/networking/expert/01-protocol-projects-quiz.md) | Ruta de solicitud, correlación de sondas/respuestas, límites de protocolos y casos extremos |
| 2 | [Política de enrutamiento y convergencia](02-routing-policy-convergence.md) · [Cuestionario](../../quizzes/networking/expert/02-routing-policy-convergence-quiz.md) | Anuncios/selección previstos, pruebas de RIB/FIB y reenvío, cronología de fallo/recuperación |
| 3 | [EVPN/VXLAN de centro de datos](03-datacenter-evpn.md) · [Cuestionario](../../quizzes/networking/expert/03-datacenter-evpn-quiz.md) | Correspondencia entre underlay/overlay, flujos de VRF permitidos/prohibidos, rutas y pruebas de encapsulación |
| 4 | [Rutas de paquetes y rendimiento de Linux](04-linux-performance.md) · [Cuestionario](../../quizzes/networking/expert/04-linux-performance-quiz.md) | Colas, contadores y paquetes correlacionados temporalmente; límites de medición y recuperación |
| 5 | [Diseño de nube y CNI](05-cloud-cni-design.md) · [Cuestionario](../../quizzes/networking/expert/05-cloud-cni-design-quiz.md) | Diseño y pruebas desde DNS hasta el backend y la ruta de retorno |
| 6 | [Automatización y evaluación final](06-automation-capstone.md) · [Cuestionario](../../quizzes/networking/expert/06-automation-capstone-quiz.md) | Pruebas y revisión de cambios que abarcan estados normales, prohibidos, fallidos y recuperados |

Siguen siendo útiles estas referencias: [fundamentos de protocolos](../../basics/06-network-fundamentals-part1.md), [redes del kernel](../../kernel/02-network-stack.md), [BGP de Calico](../calico/04-bgp-deep-dive.md), [Cilium](../cilium/README.md) y [VPC CNI](../01-vpc-cni.md).

## Elige una especialización {#tracks}

| Orientación | Orden prioritario | Profundización |
|---|---|---|
| Redes de nube/SRE | 1 → 2 → 4 → 5 → 6 | Rendimiento y fallos entre CNI, DNS, balanceadores de carga y límites híbridos |
| Empresa/centro de datos | 1 → 2 → 4 → 3 → 6 | Compara los temas restantes de L2/L3, seguridad, virtualización y automatización con el programa oficial de Cisco |
| Protocolos/software de red | 1 → 2 → 4 → 6 | Proyectos de implementación de transporte y kernel tras establecer fundamentos de C/C++ |

Los capítulos 1, 2 y 4 son requisitos previos comunes. Añade el capítulo 3 para la ruta de centro de datos o el capítulo 5 para la nube. La ruta de protocolos/Linux puede usar el experimento de host del capítulo 4 para la evaluación correspondiente del capítulo 6. Completa la evaluación dentro del ámbito elegido y luego añade otra especialización. Reserva tiempo para preparar el entorno, lidiar con intentos fallidos, reproducirlos y redactar los resultados, además de leer.

## Límites y propiedad del laboratorio {#lab-contract}

No ejecutes todos los capítulos secuencialmente en un mismo entorno.

| Entorno | Preparación y límites | Comprobación antes de finalizar |
|---|---|---|
| Observación del host | Máquina virtual desechable del curso para principiantes, herramientas instaladas y tráfico propio | Alcance de la interfaz/proceso/captura, duración y limpieza de tus archivos |
| Enrutamiento/EVPN | Máquina virtual Linux de laboratorio independiente y requisitos de la instalación/imagen de netlab o proveedor seleccionado | Revisión upstream, versiones de herramientas/imágenes, ID/recursos de laboratorio propios y comandos de recuperación |
| Nube | Cuenta/clúster de laboratorio existente y aprobado, con permisos de lectura | Cuenta, región, contexto, espacio de nombres, propietario de recursos y ámbito de costo/permisos/validación |
| Diseño/pruebas proporcionadas | Supuestos y datos de entrada indicados, incluso si no se dispone del equipo | Distinguir la revisión del diseño de la validación del tráfico en vivo y marcar lo que no se observó |

No copies las direcciones ni los nombres de dispositivos de netlab/containerlab a la NIC de una máquina virtual para principiantes. Algunos ejercicios requieren imágenes comerciales de NOS, soporte de virtualización o placas adicionales: **comprueba primero cada capítulo y sus requisitos upstream**. La eliminación global de recursos de Docker, el desmantelamiento de otros laboratorios y la inyección de fallos en producción no son pasos predeterminados de este curso.

Crea este registro antes de cada experimento. Registrar versiones y revisiones significa capturar las entradas reales; no garantiza compatibilidad entre combinaciones arbitrarias.

| Registro | Ejemplo |
|---|---|
| ID y propietario del experimento | Un ID que puedas distinguir y la función responsable |
| Entorno/permisos | Máquina virtual local, contenedor de laboratorio o acceso de solo lectura aprobado a la nube |
| Topología | Nodos, interfaces, direcciones, VRF, puntos de observación y rutas de administración |
| Herramientas/entradas | Sistema operativo, kernel, versiones de herramienta e imagen; commit upstream; hashes de archivos de entrada |
| Alcance del tráfico | Origen, destino, protocolo, puertos y duración máxima |
| Línea base | Rutas, políticas, estado de servicios y configuración de recuperación |
| Hipótesis/cambio | Resultado esperado y el único elemento que se cambiará |
| Criterios de detención/recuperación | Fallo de administración, recursos inesperados, restauración y comprobación posterior |

## Selección de recursos oficiales {#resources}

Estas orientaciones de aprendizaje se comprobaron el 15 de septiembre de 2026. Verifica aparte el acceso a los materiales semestrales, la matrícula, el personal de evaluación y la formación programada.

| Recurso | Función en este curso | Antes de usarlo |
|---|---|---|
| [Berkeley CS168](https://www.cs168.io/) | Estructura para arquitectura de Internet, enrutamiento, transporte, centros de datos y proyectos | Elige un semestre público con contenido y comprueba por separado el acceso a las descripciones, el código y la calificación |
| [Laboratorios BGP](https://bgplabs.net/) | Práctica progresiva de configuración BGP, políticas y fallos | Comprueba la [instalación](https://bgplabs.net/install/), la revisión del laboratorio y los requisitos de proveedor/imagen |
| [netlab EVPN](https://netlab.tools/module/evpn/) | Diseño EVPN/VRF/IRB y validación de compatibilidad de funciones | Verifica que los dispositivos seleccionados admitan la función necesaria y la configuración del plano de datos |
| [Redes Linux de Bootlin](https://bootlin.com/training/networking/) | Profundización en kernel, controladores, espacio de usuario y rendimiento | Distingue el material público de la formación de pago y comprueba los requisitos de C/kernel y placa |
| [Infraestructura empresarial de Cisco](https://www.cisco.com/site/us/en/learn/training-certifications/certifications/enterprise/ccie-enterprise-infrastructure/index.html) | Comprobar la cobertura de diseño, operaciones y automatización empresarial | Selecciona el programa oficial vigente; FRR no reproduce el comportamiento de todos los dispositivos comerciales ni de todos los ASIC |
| [AWS Advanced Networking](https://docs.aws.amazon.com/aws-certification/latest/advanced-networking-specialty-01/advanced-networking-specialty-01.html) | Ámbito de diseño, implementación, operaciones y seguridad de nube/híbrido | Distingue la preparación del examen de la implementación; define condiciones de cuenta, acceso, costo y limpieza |
| [Stanford CS144](https://online.stanford.edu/courses/cs144-introduction-computer-networking) | Ruta opcional de C/C++ para implementación de protocolos | Verifica la matrícula actual, las tareas públicas y la disponibilidad del repositorio |

Este repositorio no proporciona materiales privados de cursos ni soluciones. Lee los requisitos del proyecto y produce tu propia implementación, pruebas y justificación de diseño.

## Interpretación de pruebas {#evidence-rules}

- **Medidas:** observadas en el entorno, intervalo temporal y tráfico indicados.
- **Proporcionadas:** recopiladas por otra persona; registra su procedencia, ámbito y relación con el original.
- **Ilustrativas/sintéticas:** entradas para explicar un cálculo o validador. No las informes como tráfico real satisfactorio.
- **Supuesto de diseño:** una condición de diseño no probada. Déjala marcada como no verificada.

Las observaciones ausentes son `unknown`. Una salida de enrutamiento vacía, paquetes faltantes y un timeout de `ping` por sí solos no demuestran una denegación de política ni una causa raíz de extremo a extremo. Una sesión BGP establecida no demuestra los prefijos ni el comportamiento de reenvío previstos.

## Portafolio final {#portfolio}

Relaciona estos entregables en tu propio entorno:

1. Rutas de ida y vuelta de una solicitud, incluidos los puntos de observación.
2. Pruebas del tráfico normal y del **tráfico que se debe prohibir**.
3. Registros de antes, durante y después de un fallo o cambio de política.
4. Condiciones de medición, pruebas faltantes e hipótesis descartadas.
5. Un cambio acotado y la verificación después de la recuperación.
6. Resultados de automatización de la [evaluación final](06-automation-capstone.md) y sus límites de revisión humana.

Conserva las pruebas originales en una ubicación aprobada y usa alias coherentes en las notas públicas. No publiques indiscriminadamente paquetes sin procesar, registros, cuentas ni inventarios de topología.

**Siguiente:** [Capítulo 1: Proyectos de protocolos e implementación](01-protocol-projects.md)
