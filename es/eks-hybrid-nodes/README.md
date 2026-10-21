# EKS Hybrid Nodes

> **Versiones compatibles**: Versiones compatibles actuales de EKS; los ejemplos se revisaron para EKS 1.36 / nodeadm 1.0.20
> **Última actualización**: 12 de octubre de 2026

Amazon EKS Hybrid Nodes conecta nodos locales o perimetrales operados por el cliente con un plano de control de EKS administrado por AWS. Usted sigue operando los hosts, los sistemas operativos, la conectividad y las cargas de trabajo. Esta guía distingue las interfaces compatibles de las configuraciones de ejemplo; no demuestra que se haya probado una implementación de producción local concreta.

EKS 1.37 estuvo disponible el 1 de octubre de 2026. Los ejemplos de esta guía siguen revisados para EKS 1.36 y nodeadm 1.0.20.

Antes de elegir una versión, consulte el [calendario de versiones de EKS](https://docs.aws.amazon.com/eks/latest/userguide/kubernetes-versions.html), la documentación de Hybrid Nodes y la información de compatibilidad de hosts/CNI.

## Tabla de contenido

1. [Requisitos previos y requisitos del sistema](01-prerequisites.md)
2. [Configuración de red](02-network-configuration.md)
3. [Configuración con acceso a Internet restringido (S3 + puntos de conexión de VPC)](03-airgap-setup.md)
4. [Inicialización de nodos](04-node-bootstrap.md)
5. [Integración de servidores GPU](05-gpu-integration.md)
6. [Estrategias de ubicación de cargas de trabajo](06-workload-placement.md)
7. [Administración del ciclo de vida de los nodos](07-node-lifecycle.md)
8. [Operaciones y mantenimiento](08-operations.md)
9. [Guía de instalación y migración del sistema operativo de servidores bare metal](09-bare-metal-os-setup.md)
10. [Gateway de Hybrid Nodes](10-hybrid-nodes-gateway.md)
11. [Revisión de seguridad de la separación de redes](11-network-separation-security.md)
12. [Conectividad de Pod sin SNAT y PrivateLink](12-connectivity-validation.md)

## ¿Qué son Hybrid Nodes?

Hybrid Nodes pueden compartir un clúster con nodos de cómputo comunes de AWS. Registrar una máquina en la nube como nodo **híbrido** es otra cosa: AWS no admite infraestructura de nodos híbridos en las regiones de AWS, Local Zones, Outposts ni otras nubes, y el uso de EC2 sigue generando cargos de Hybrid Nodes.

![Diagrama general de red de EKS Hybrid Nodes, desde el router y el gateway locales hasta la ENI del plano de control en la VPC del clúster de AWS.](../.gitbook/assets/en-eks-hybrid-nodes-highlevel-0.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-hybrid-nodes-highlevel-0.html)

El siguiente diagrama muestra los requisitos previos de red, incluidos la VPC, las subredes, Transit Gateway/Virtual Private Gateway y la conectividad de los CIDR de nodos/Pod remotos.

![Diagrama de requisitos previos de Hybrid Nodes que relaciona los ajustes RemoteNodeNetwork y RemotePodNetwork del clúster con las tablas de rutas tanto del lado de la VPC como del entorno local.](../.gitbook/assets/en-eks-hybrid-nodes-prereq-0.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-hybrid-nodes-prereq-0.html)

Los diagramas ilustran la conectividad privada y el enrutamiento, no la creación automática de todas las rutas locales, reglas de firewall o puntos de conexión de servicios de AWS.

Para las revisiones del equipo de seguridad, consulte la [guía de revisión de separación de redes](11-network-separation-security.md). Distingue los puntos de conexión privados del clúster, las ENI de EKS y los puntos de conexión AWS PrivateLink para servicios, e identifica las pruebas de las conexiones de administración y los límites de datos a través de DX.

## Casos de uso y límites de datos

Las GPU locales, los grandes conjuntos de datos locales, el procesamiento perimetral y el hardware existente pueden ser motivos para usar Hybrid Nodes. Los requisitos de localidad de los datos siguen necesitando controles de aplicación, almacenamiento, salida y registro. Los objetos de la API de Kubernetes y los metadatos del plano de control se administran en AWS; un selector de nodos por sí solo no garantiza la soberanía de los datos ni el cumplimiento normativo.

Para la ubicación, use la etiqueta de cómputo híbrido real y una etiqueta de organización mantenida explícitamente, en lugar de suponer que existe una zona de AWS llamada `on-premises`:

```yaml
# Pod spec fragment; set organization labels through the node owner.
nodeSelector:
  eks.amazonaws.com/compute-type: hybrid
  example.com/data-location: on-premises
```

Este fragmento no crea una etiqueta, una aplicación completa, un límite de seguridad ni una política de retención de datos. Valide la compatibilidad de las imágenes y el entorno de ejecución, así como las rutas reales de los datos.

## Arquitectura y responsabilidades

| Componente | Ubicación | Responsabilidad |
|-----------|----------|----------------|
| Servidor de API de EKS, etcd, controladores, programador | AWS | Plano de control administrado por AWS |
| nodeadm | Host Linux compatible local | CLI de instalación/inicialización/actualización; no es el agente de nodo de larga duración |
| kubelet / containerd | Local | Agente de nodo / entorno de ejecución CRI, operado por el propietario del host |
| Cilium o Calico | Local y clúster | Configuración de CNI compatible; VPC CNI no administra los nodos híbridos |
| SSM Agent o ayudante de firma de Roles Anywhere | Local | Obtiene credenciales temporales del servicio de AWS correspondiente |
| Servicio SSM / IAM Roles Anywhere | AWS | Servicio de credenciales, no un sustituto local de una CA sin conexión |
| VPN / Direct Connect y enrutamiento | Ambos entornos | Conectividad bidireccional; Direct Connect por sí solo no implica cifrado |

Las variantes VMware compatibles de Bottlerocket usan su propia ruta de inicialización y no utilizan nodeadm. Para otros hosts compatibles, `nodeadm install` instala las dependencias y `nodeadm init` configura e incorpora el nodo. Las nuevas instalaciones y actualizaciones basadas en SSM requieren **nodeadm 1.0.19 o posterior** debido a cambios en las claves de firma de SSM; la versión actual revisada es **1.0.20**.

## Restricciones que debe tener en cuenta

- **Entorno conectado:** Se requiere conectividad privada bidireccional y confiable con AWS. Hybrid Nodes no está pensado para operar en modo DDIL desconectado o intermitente. En esta guía, «aislamiento de red» significa acceso a Internet restringido con la conectividad necesaria con AWS, no aislamiento de AWS.
- **Direcciones:** Rangos IPv4 RFC1918 o CGNAT, sin superposición entre los CIDR de nodos/Pod remotos, la VPC y los servicios. Se admiten hasta **15 CIDR de nodos y 15 CIDR de Pod por clúster**.
- **Autenticación:** Use `API` o `API_AND_CONFIG_MAP` y prepare el rol de IAM de Hybrid Nodes y las entradas de acceso.
- **Punto de conexión de API:** AWS recomienda usar solo el público o solo el privado. Si ambos están habilitados, los nodos fuera de la VPC resuelven las direcciones del punto de conexión público; esto **puede** impedir su incorporación si la ruta/reglas de acceso esperadas son privadas. No es una prohibición universal de la API. Incluso un punto de conexión de API público no elimina el requisito de conectividad privada desde el plano de control hasta el nodo.
- **Regiones:** Está disponible en todas las regiones salvo AWS GovCloud (US) y las regiones de AWS China, según la descripción general actual.
- **Compatibilidad con hosts:** Revise conjuntamente el sistema operativo, la arquitectura, el CNI y el kernel. AL2023 está destinado a entornos virtualizados locales, no es una recomendación genérica para bare metal.
- **Cargos:** Los cargos de Hybrid Nodes se calculan según las horas de vCPU notificadas mientras los nodos están conectados. Los núcleos bare metal con hyperthreading pueden notificar dos vCPU. Las cargas de trabajo inactivas no detienen automáticamente los cargos de los nodos; los cargos del clúster y de otros servicios se cobran por separado.

## Proveedores de credenciales

Ambos proveedores necesitan acceso a los puntos de conexión de servicios de AWS para renovar las credenciales. Una CA local no permite que IAM Roles Anywhere emita credenciales de AWS sin conexión. A menos que exista una razón revisada para combinarlos, es preferible usar un solo proveedor de manera uniforme en toda la flota.

| Tema | Activaciones híbridas de SSM | IAM Roles Anywhere |
|-------|------------------------|--------------------|
| Inicialización | ID/código de activación y rol preparado para confiar en SSM | PKI, certificado/clave por nodo, ancla de confianza, perfil y rol |
| Nomenclatura | Nombre `mi-...` generado por SSM | Nombre de nodo personalizado vinculado a la identidad del certificado |
| Duración de la sesión | Una hora fija, renovada por SSM | Una hora de forma predeterminada; las duraciones admitidas para solicitudes/perfiles son de 15 minutos a 12 horas, sujetas a la duración efectiva y al máximo del rol |
| Desconexión | No se pueden renovar las credenciales; el retroceso entre reintentos puede retrasar la reconexión después de recuperar la red | No se pueden obtener credenciales nuevas sin conexión; credential-process las obtiene a petición cuando se restablece la conectividad |
| Escala / costo | Sin cargos por registro de nodos de SSM ni por administración por nodo; el precio por uso de características se cobra por separado | Revise las cuotas de IAM Roles Anywhere y los requisitos operativos de PKI |
| Opción habitual | No hay una PKI existente; registro más sencillo | PKI existente y ciclo de vida de certificados administrado |

**Precios consultados el 16 de septiembre de 2026:** SSM eliminó el nivel Advanced Instances a partir del 30 de junio de 2026. Consulte los [precios actuales de SSM](https://aws.amazon.com/systems-manager/pricing/) para conocer las condiciones de uso de Session Manager y Run Command; los [cargos por vCPU de EKS Hybrid Nodes](https://aws.amazon.com/eks/pricing/) se cobran por separado.

El perfil de Roles Anywhere debe aceptar un nombre de sesión de rol personalizado, y la política de confianza debe vincularlo al atributo de certificado elegido. La duración efectiva de la sesión **no debe superar** el máximo del rol de IAM; la API CreateSession permite que ambos valores sean iguales. Los [requisitos previos](01-prerequisites.md) detallan estos contratos y la preparación segura.

## Ejemplos de cargas de trabajo

1. Entrenamiento o inferencia local con GPU, con un entorno de ejecución verificado y un plan de recuperación.
2. Procesamiento de datos local con rutas de metadatos/telemetría/salida de AWS revisadas por separado.
3. Aplicaciones de fábrica/perimetrales con conectividad confiable y comportamiento de desconexión probado.
4. Procesamiento de medios cerca de grandes conjuntos de datos existentes.

## Próximos pasos

Empiece por [Requisitos previos y requisitos del sistema](01-prerequisites.md) para asegurarse de que su entorno esté listo para EKS Hybrid Nodes.

## Cuestionario

Para comprobar su comprensión de EKS Hybrid Nodes, responda el siguiente cuestionario:

* [Cuestionario sobre los requisitos previos de EKS Hybrid Nodes](../quizzes/eks-hybrid-nodes/01-prerequisites-quiz.md)
* [Cuestionario sobre la configuración de red de EKS Hybrid Nodes](../quizzes/eks-hybrid-nodes/02-network-configuration-quiz.md)
* [Cuestionario sobre la configuración de EKS Hybrid Nodes con acceso a Internet restringido](../quizzes/eks-hybrid-nodes/03-airgap-setup-quiz.md)
* [Cuestionario sobre la inicialización de nodos de EKS Hybrid Nodes](../quizzes/eks-hybrid-nodes/04-node-bootstrap-quiz.md)
* [Cuestionario sobre la integración de GPU de EKS Hybrid Nodes](../quizzes/eks-hybrid-nodes/05-gpu-integration-quiz.md)
* [Cuestionario sobre la ubicación de cargas de trabajo de EKS Hybrid Nodes](../quizzes/eks-hybrid-nodes/06-workload-placement-quiz.md)
* [Cuestionario sobre la administración del ciclo de vida de los nodos](../quizzes/eks-hybrid-nodes/07-node-lifecycle-quiz.md)
* [Cuestionario sobre operaciones de EKS Hybrid Nodes](../quizzes/eks-hybrid-nodes/08-operations-quiz.md)
* [Cuestionario sobre la instalación y migración del sistema operativo de servidores bare metal](../quizzes/eks-hybrid-nodes/09-bare-metal-os-setup-quiz.md)
* [Cuestionario sobre el gateway de EKS Hybrid Nodes](../quizzes/eks-hybrid-nodes/10-hybrid-nodes-gateway-quiz.md)
* [Cuestionario sobre la revisión de seguridad de la separación de redes](../quizzes/eks-hybrid-nodes/11-network-separation-security-quiz.md)
* [Cuestionario sobre la conectividad de Pod sin SNAT y PrivateLink](../quizzes/eks-hybrid-nodes/12-connectivity-validation-quiz.md)

## Documentos relacionados

* [Guía de resiliencia de EKS](../eks/10-eks-resiliency.md) - Configuración de alta disponibilidad en entornos híbridos
* [Optimización de costos de EKS](../eks/07-eks-cost-optimization.md) - Estrategias de administración de costos
* [Supervisión y registro de EKS](../eks/06-eks-monitoring-logging.md) - Configuración de supervisión integrada

## Documentación oficial

* [Documentación oficial de AWS EKS Hybrid Nodes](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-overview.html)
* [Calendario de versiones de EKS Kubernetes](https://docs.aws.amazon.com/eks/latest/userguide/kubernetes-versions.html)
* [Guía del usuario de nodeadm](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-nodeadm.html)
* [Documentación oficial de Harbor](https://goharbor.io/docs/)
* [Documentación de NVIDIA GPU Operator](https://docs.nvidia.com/datacenter/cloud-native/gpu-operator/overview.html)
* [Guía de redes de Hybrid Nodes](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-networking.html)
* [Configuración de CNI de Hybrid Nodes](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-cni.html)
* [Solución de problemas de Hybrid Nodes](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-troubleshooting.html)

* [Compatibilidad de sistemas operativos para Hybrid Nodes](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-os.html)
* [Credenciales y rol de IAM de Hybrid Nodes](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-creds.html)
* [Credenciales del host durante la desconexión de la red](https://docs.aws.amazon.com/eks/latest/best-practices/hybrid-nodes-host-creds.html)
* [Semántica de CreateSession de IAM Roles Anywhere](https://docs.aws.amazon.com/rolesanywhere/latest/userguide/authentication-create-session.html)
* [Precios de EKS](https://aws.amazon.com/eks/pricing/)
