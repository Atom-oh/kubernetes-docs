# Itinerario de estudio de redes para expertos

> **Recursos verificados**: 15 de septiembre de 2026
>
> **Entorno**: máquinas virtuales desechables con Ubuntu Server 24.04 LTS o Rocky Linux 9 para los ejercicios en el host. Las herramientas de enrutamiento/EVPN y los entornos en la nube tienen requisitos previos específicos en sus respectivos capítulos.

Estos cuadernos de trabajo avanzados continúan el [curso para principiantes](../beginner/README.md). Relaciona los principios de los protocolos con el código y los paquetes, y luego evalúa las políticas de enrutamiento, el rendimiento de Linux y los diseños en la nube mediante evidencias.

El objetivo de nivel experto es **definir qué condiciones deberían cumplirse, poner a prueba hipótesis mediante observaciones y explicar el impacto de un cambio y cómo recuperarse de él**. Un período de estudio fijo o una certificación, por sí solos, no garantizan esa capacidad.

## Comprobación inicial {#entry-check}

Pasa al capítulo 1 cuando puedas explicar y reproducir lo siguiente:

- Distinguir las funciones de IP, la subred, la puerta de enlace y DNS de las de MAC/ARP.
- Leer `ip route get`, `ss` y una captura acotada de `tcpdump`, e identificar el punto de observación.
- Verificar el acceso con clave SSH y la política del cortafuegos del laboratorio, y luego restaurar el estado anterior.
- Distinguir un error HTTP, un fallo de conexión y un fallo de resolución de nombres.
- Explicar las funciones de los switches, routers, cortafuegos y balanceadores de carga, las VLAN y el límite entre la LAN y la WAN. Antes del capítulo 7, contrasta estos conocimientos con [Conceptos básicos de redes, parte 5](../../basics/06-network-fundamentals-part5.md).
- Separar las rutas de administración y de experimentación, e identificar tus propios archivos, máquinas virtuales y contenedores.

Usa el [proyecto final para principiantes](../beginner/08-container-cloud-capstone.md) para repasar las habilidades que te falten. Completa la [preparación de herramientas del invitado](../beginner/README.md#guest-tools) cuando no esté disponible un comando del host.

## Nueve cuadernos de trabajo {#course-map}

Cada fila sigue el orden **lectura → experimento o validación del diseño → evidencias → cuestionario explicado**. Los cursos externos proporcionan el contenido de lectura; estos cuadernos ofrecen una forma de evaluar tus propios resultados.

| Orden | Cuaderno de trabajo | Entregable |
|---|---|---|
| 1 | [Proyectos de protocolos e implementación](01-protocol-projects.md) · [Cuestionario](../../quizzes/networking/expert/01-protocol-projects-quiz.md) | Ruta de la solicitud, correlación de sondeo/respuesta, límites del protocolo y casos extremos |
| 2 | [Políticas de enrutamiento y convergencia](02-routing-policy-convergence.md) · [Cuestionario](../../quizzes/networking/expert/02-routing-policy-convergence-quiz.md) | Anuncios/selección previstos, evidencias de RIB/FIB y reenvío, cronología del fallo y la recuperación |
| 3 | [EVPN/VXLAN en centros de datos](03-datacenter-evpn.md) · [Cuestionario](../../quizzes/networking/expert/03-datacenter-evpn-quiz.md) | Asignación de underlay/overlay, flujos VRF permitidos/prohibidos, rutas y evidencias de encapsulación |
| 4 | [Rutas de paquetes y rendimiento en Linux](04-linux-performance.md) · [Cuestionario](../../quizzes/networking/expert/04-linux-performance-quiz.md) | Colas, contadores y paquetes correlacionados temporalmente; límites de las mediciones y recuperación |
| 5 | [Diseño de la nube y CNI](05-cloud-cni-design.md) · [Cuestionario](../../quizzes/networking/expert/05-cloud-cni-design-quiz.md) | Diseño y evidencias desde DNS hasta el backend y la ruta de retorno |
| 6 | [Automatización y evaluación final](06-automation-capstone.md) · [Cuestionario](../../quizzes/networking/expert/06-automation-capstone-quiz.md) | Evidencias y revisión del cambio que abarquen los estados normal, prohibido, fallido y recuperado |
| 7 | [Diseño de conectividad WAN e híbrida](07-wan-hybrid-connectivity.md) · [Cuestionario](../../quizzes/networking/expert/07-wan-hybrid-connectivity-quiz.md) | Ruta prevista en cada dirección, regla de conmutación por error, tiempo y qué se reduce (ancho de banda, MTU) cuando falla un enlace |
| 8 | [Diseño de CDN y distribución en el edge](08-cdn-edge-delivery.md) · [Cuestionario](../../quizzes/networking/expert/08-cdn-edge-delivery-quiz.md) | Dónde se responde una solicitud, explicado a partir de los encabezados de respuesta, y una ruta del edge al origen accesible únicamente mediante CloudFront |
| 9 | [Seguridad en el edge: WAF y defensa contra DDoS](09-edge-security-waf-ddos.md) · [Cuestionario](../../quizzes/networking/expert/09-edge-security-waf-ddos-quiz.md) | Dónde se detiene cada capa de ataque y un plan de reglas WAF en modo de recuento con un criterio para revertir el cambio |

Las referencias existentes siguen siendo útiles: [fundamentos de protocolos](../../basics/06-network-fundamentals-part1.md), [redes del kernel](../../kernel/02-network-stack.md), [BGP de Calico](../calico/04-bgp-deep-dive.md), [Cilium](../cilium/README.md) y [VPC CNI](../01-vpc-cni.md).

## Elige una especialización {#tracks}

| Orientación | Orden de prioridad | Profundización adicional |
|---|---|---|
| Redes en la nube/SRE | 1 → 2 → 4 → 5 → 6 | Rendimiento y fallos en CNI, DNS, balanceadores de carga y límites híbridos |
| Empresa/centro de datos | 1 → 2 → 4 → 3 → 6 | Contrasta los temas restantes de L2/L3, seguridad, virtualización y automatización con el temario oficial de Cisco |
| Protocolos/software de red | 1 → 2 → 4 → 6 | Proyectos de implementación de transporte y del kernel tras establecer los fundamentos de C/C++ |

Los capítulos 1, 2 y 4 son requisitos previos comunes. Añade el capítulo 3 para la ruta de centros de datos o el capítulo 5 para la nube. La ruta de protocolos/Linux puede usar el experimento en el host del capítulo 4 para la evaluación correspondiente del capítulo 6. Completa la evaluación dentro del ámbito seleccionado y luego añade otra especialización. Reserva tiempo para preparar el entorno, realizar intentos fallidos, reproducir resultados e informar sobre ellos, además de leer.

## Límites y titularidad del laboratorio {#lab-contract}

No ejecutes todos los capítulos secuencialmente en un solo entorno.

| Entorno | Preparación y límites | Qué comprobar antes de terminar |
|---|---|---|
| Observación en el host | Máquina virtual desechable del curso para principiantes, herramientas instaladas y tráfico propio | Alcance de las interfaces/procesos/capturas, duración y eliminación de tus archivos |
| Enrutamiento/EVPN | Máquina virtual Linux de laboratorio independiente y requisitos de instalación/imagen de netlab o del proveedor seleccionado | Revisión de upstream, versiones de herramientas/imágenes, ID/recursos del laboratorio que te pertenecen y comandos de recuperación |
| Nube | Cuenta/clúster de laboratorio existente y aprobado, con permisos de lectura | Cuenta, región, contexto, espacio de nombres, propietario del recurso y alcance del costo/permisos/validación |
| Diseño/evidencias proporcionadas | Supuestos establecidos y evidencias de entrada, sin necesidad de disponer del equipo | Distingue la revisión del diseño de la validación del tráfico en vivo y marca los elementos no observados |

No copies las direcciones ni los nombres de un dispositivo de netlab/containerlab a la NIC de una máquina virtual para principiantes. Algunos ejercicios requieren imágenes comerciales de NOS, compatibilidad con virtualización o placas adicionales: **consulta primero cada capítulo y los requisitos previos de upstream**. La depuración global de Docker, el desmontaje de otros laboratorios y la inyección de fallos en producción no son pasos predeterminados de este curso.

Crea este registro antes de cada experimento. Registrar versiones y revisiones significa capturar las entradas reales; no garantiza la compatibilidad entre combinaciones arbitrarias.

| Registro | Ejemplo |
|---|---|
| ID y responsable del experimento | Un ID que puedas distinguir y el rol responsable |
| Entorno/permisos | Máquina virtual local, contenedor de laboratorio o acceso aprobado de solo lectura a la nube |
| Topología | Nodos, interfaces, direcciones, VRF, rutas de observación y administración |
| Herramientas/entradas | SO, kernel y versiones de herramientas e imágenes; commit de upstream; hashes de los archivos de entrada |
| Alcance del tráfico | Origen, destino, protocolo, puertos y duración máxima |
| Línea de base | Rutas, política, estado del servicio y configuración de recuperación |
| Hipótesis/cambio | Resultado esperado y el único elemento que se cambiará |
| Criterios de detención/recuperación | Fallo de administración, recursos inesperados, restauración y nueva comprobación |

## Selección de recursos oficiales {#resources}

Estas son orientaciones de estudio verificadas el 15 de septiembre de 2026. Comprueba por separado el acceso a los materiales del semestre, la matrícula, los evaluadores y las sesiones de formación programadas.

| Recurso | Función en este curso | Antes de usarlo |
|---|---|---|
| [Berkeley CS168](https://www.cs168.io/) | Estructura para estudiar la arquitectura de Internet, el enrutamiento, el transporte, los centros de datos y los proyectos | Elige un semestre público con contenido y comprueba por separado el acceso a las descripciones, el código y la evaluación |
| [BGP Labs](https://bgplabs.net/) | Práctica progresiva de configuración de BGP, políticas y fallos | Comprueba la [instalación](https://bgplabs.net/install/), la revisión del laboratorio y los requisitos del proveedor/las imágenes |
| [netlab EVPN](https://netlab.tools/module/evpn/) | Diseño de EVPN/VRF/IRB y validación de compatibilidad de funciones | Verifica que los dispositivos seleccionados admitan la función requerida y la configuración del plano de datos |
| [Redes Linux de Bootlin](https://bootlin.com/training/networking/) | Profundización en el kernel, los controladores, el espacio de usuario y el rendimiento | Distingue los materiales públicos de la formación de pago; comprueba los requisitos de C/kernel y de las placas |
| [Infraestructura empresarial de Cisco](https://www.cisco.com/site/us/en/learn/training-certifications/certifications/enterprise/ccie-enterprise-infrastructure/index.html) | Verificación de la cobertura de diseño, operaciones y automatización empresariales | Elige el temario oficial vigente; FRR no reproduce el comportamiento de todos los dispositivos comerciales ni de los ASIC |
| [Redes avanzadas de AWS](https://docs.aws.amazon.com/aws-certification/latest/advanced-networking-specialty-01/advanced-networking-specialty-01.html) | Alcance del diseño, la implementación, las operaciones y la seguridad en la nube/híbridos | Distingue la preparación para el examen del despliegue; establece las condiciones de cuenta, acceso, costos y limpieza |
| [Stanford CS144](https://online.stanford.edu/courses/cs144-introduction-computer-networking) | Orientación opcional en C/C++ para la implementación de protocolos | Verifica la matrícula vigente, las tareas públicas y la disponibilidad del repositorio |

Este repositorio no proporciona materiales privados de los cursos ni soluciones. Lee los requisitos del proyecto y crea tu propia implementación, tus pruebas y la justificación del diseño.

## Interpretación de las evidencias {#evidence-rules}

- **Medidas:** Observadas en el entorno, el intervalo de tiempo y el tráfico que has especificado.
- **Proporcionadas:** Recopiladas por otra persona; registra su procedencia, alcance y relación con el original.
- **Ilustrativas/sintéticas:** Entradas que explican un cálculo o validador. No las presentes como tráfico real satisfactorio.
- **Supuesto de diseño:** Condición de diseño no probada. Mantenla marcada como no verificada.

Las observaciones ausentes son `unknown`. Una salida de enrutamiento vacía, la ausencia de paquetes o un tiempo de espera agotado en `ping`, por sí solos, no demuestran una denegación por política ni una causa raíz de extremo a extremo. Una sesión BGP establecida no demuestra que los prefijos previstos ni el comportamiento de reenvío sean correctos.

## Portafolio final {#portfolio}

Relaciona estos entregables en tu propio entorno:

1. Rutas de ida y retorno para una solicitud, incluidos los puntos de observación.
2. Evidencias tanto del tráfico normal como del **tráfico que debe prohibirse**.
3. Registros de antes/durante/después para un fallo o cambio de política.
4. Condiciones de medición, evidencias ausentes e hipótesis descartadas.
5. Un cambio acotado y una verificación posterior a la recuperación.
6. Resultados de automatización de la [evaluación final](06-automation-capstone.md) y sus límites en cuanto a la revisión humana.

Guarda las evidencias originales en una ubicación aprobada y usa alias coherentes en las notas públicas. No publiques indiscriminadamente paquetes, registros, cuentas ni inventarios de topología sin procesar.

**Siguiente:** [Capítulo 1: Proyectos de protocolos e implementación](01-protocol-projects.md)
