# EKS Hybrid Nodes

> **Versiones compatibles**: Versiones actuales compatibles con EKS; ejemplos revisados para EKS 1.36 / nodeadm 1.0.20
> **Última actualización**: September 16, 2026

Amazon EKS Hybrid Nodes conecta nodos locales o de edge operados por el cliente a un plano de control de EKS administrado por AWS. Usted continúa operando los hosts, sistemas operativos, conectividad y cargas de trabajo. Esta guía distingue las interfaces compatibles de las configuraciones de ejemplo; no constituye evidencia de que se haya probado una implementación de producción local específica.

## Tabla de contenido

1. [Requisitos previos y requisitos del sistema](01-prerequisites.md)
2. [Configuración de red](02-network-configuration.md)
3. [Configuración con acceso restringido a Internet (S3 + VPC Endpoints)](03-airgap-setup.md)
4. [Bootstrap de nodos](04-node-bootstrap.md)
5. [Integración de servidores GPU](05-gpu-integration.md)
6. [Estrategias de ubicación de cargas de trabajo](06-workload-placement.md)
7. [Administración del ciclo de vida de los nodos](07-node-lifecycle.md)
8. [Operaciones y mantenimiento](08-operations.md)
9. [Guía de instalación y migración del SO de servidores Bare Metal](09-bare-metal-os-setup.md)
10. [Gateway de Hybrid Nodes](10-hybrid-nodes-gateway.md)
11. [Revisión de seguridad de la separación de red](11-network-separation-security.md)

## ¿Qué son los Hybrid Nodes?

Hybrid Nodes pueden compartir un clúster con nodos de cómputo de AWS habituales. Registrar una máquina en la nube como nodo **hybrid** es diferente: AWS no admite infraestructura de nodos híbridos en AWS Regions, Local Zones, Outposts u otras nubes, y el uso de EC2 sigue generando tarifas de híbrido.

![Diagrama de descripción general de red de nodos híbridos de EKS que se extiende desde el router y gateway locales hasta la ENI del plano de control en la VPC del clúster de AWS.](../.gitbook/assets/en-eks-hybrid-nodes-highlevel-0.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-hybrid-nodes-highlevel-0.html)

El siguiente diagrama muestra los requisitos previos de red, incluida la conectividad de VPC, subredes, Transit Gateway/Virtual Private Gateway y CIDR de Remote Node/Pod.

![Diagrama de requisitos previos de nodos híbridos que vincula las configuraciones RemoteNodeNetwork y RemotePodNetwork del clúster con las tablas de rutas tanto en el lado de la VPC como en el local.](../.gitbook/assets/en-eks-hybrid-nodes-prereq-0.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-hybrid-nodes-prereq-0.html)

Los diagramas ilustran la conectividad y el enrutamiento privados, no la creación automática de cada ruta local, regla de firewall o endpoint de servicio de AWS.

Para revisiones de equipos de seguridad, use la [guía de revisión de separación de red](11-network-separation-security.md). Distingue los endpoints privados del clúster, las ENI de EKS y los endpoints PrivateLink de servicios de AWS, e identifica evidencia de conexiones de administración y límites de datos a través de DX.

## Casos de uso y límites de datos

Las GPU locales, los conjuntos de datos locales grandes, el procesamiento de edge y el hardware existente pueden ser motivos para usar Hybrid Nodes. Los requisitos de localidad de datos aún necesitan controles de aplicación, almacenamiento, salida y registro. Los objetos de la API de Kubernetes y los metadatos del plano de control se administran en AWS; un selector de nodos por sí solo no establece soberanía de datos ni cumplimiento normativo.

Use la etiqueta real de cómputo híbrido y una etiqueta de organización mantenida explícitamente para la ubicación, en lugar de asumir que existe una zona de AWS llamada `on-premises`:

```yaml
# Pod spec fragment; set organization labels through the node owner.
nodeSelector:
  eks.amazonaws.com/compute-type: hybrid
  example.com/data-location: on-premises
```

Este fragmento no crea una etiqueta, una aplicación completa, un límite de seguridad ni una política de retención de datos. Valide la compatibilidad real de las imágenes y el runtime, así como las rutas de datos reales.

## Arquitectura y propiedad

| Componente | Ubicación | Responsabilidad |
|-----------|----------|----------------|
| Servidor de API de EKS, etcd, controllers, scheduler | AWS | Plano de control administrado por AWS |
| nodeadm | Host Linux local compatible | CLI de instalación/bootstrap/actualización; no es el agente de nodos de ejecución prolongada |
| kubelet / containerd | Local | Agente de nodos / runtime CRI, operado por el propietario del host |
| Cilium o Calico | Local y clúster | Configuración de CNI compatible; VPC CNI no administra nodos híbridos |
| SSM Agent o asistente de firma de Roles Anywhere | Local | Obtiene credenciales temporales del servicio de AWS correspondiente |
| Servicio SSM / IAM Roles Anywhere | AWS | Servicio de credenciales, no un sustituto local de CA sin conexión |
| VPN / Direct Connect y enrutamiento | Ambos entornos | Conectividad bidireccional; Direct Connect por sí solo no implica cifrado |

Las variantes de VMware compatibles de Bottlerocket usan su propia ruta de bootstrap y no usan nodeadm. Para otros hosts compatibles, `nodeadm install` instala las dependencias y `nodeadm init` configura e incorpora el nodo. Las nuevas instalaciones y actualizaciones basadas en SSM requieren **nodeadm 1.0.19 o posterior** debido a cambios en la clave de firma de SSM; la versión actual revisada es **1.0.20**.

## Restricciones que se deben tener en cuenta

- **Entorno conectado:** Se requiere conectividad privada bidireccional y confiable con AWS. Hybrid Nodes no está diseñado para operaciones DDIL desconectadas o intermitentes. «Air-gap» en esta guía significa acceso restringido a Internet con la conectividad de AWS requerida, no aislamiento de AWS.
- **Direcciones:** Rangos IPv4 RFC1918 o CGNAT, sin superposición entre los CIDR de nodos/Pod remotos, VPC y servicios. Se admiten hasta **15 CIDR de nodos y 15 CIDR de Pod por clúster**.
- **Autenticación:** Use `API` o `API_AND_CONFIG_MAP` y prepare el rol de IAM y las entradas de acceso de Hybrid Nodes.
- **Endpoint de API:** AWS recomienda solo público o solo privado. Con ambos habilitados, los nodos fuera de la VPC resuelven direcciones de endpoint públicas; eso **puede** impedir la incorporación si la ruta o las reglas de acceso esperadas son privadas. No es una prohibición universal de la API. Incluso un endpoint de API público no elimina el requisito de conectividad privada entre el plano de control y el nodo.
- **Regiones:** Disponible excepto en AWS GovCloud (US) y AWS China Regions, según la descripción general actual.
- **Compatibilidad de hosts:** Revise conjuntamente el SO, la arquitectura, CNI y el kernel. AL2023 es para entornos virtualizados locales, no una recomendación genérica para Bare Metal.
- **Cargos:** Las tarifas de híbrido usan las horas de vCPU informadas mientras los nodos están conectados. Los núcleos de Bare Metal con hyperthreading pueden informar dos vCPU. Las cargas de trabajo inactivas no detienen automáticamente los cargos de los nodos; las tarifas del clúster y de otros servicios son independientes.

## Proveedores de credenciales

Ambos proveedores necesitan acceso a los endpoints de servicios de AWS para renovar las credenciales. Una CA local no permite que IAM Roles Anywhere emita credenciales de AWS sin conexión. Prefiera un proveedor de forma coherente en toda la flota, salvo que exista un motivo revisado para combinarlos.

| Tema | Activaciones híbridas de SSM | IAM Roles Anywhere |
|-------|------------------------|--------------------|
| Bootstrap | ID/código de activación y rol preparado que confía en SSM | PKI, certificado/clave por nodo, trust anchor, profile y rol |
| Nomenclatura | Nombre `mi-...` generado por SSM | Nombre de nodo personalizado vinculado a la identidad del certificado |
| Duración de la sesión | Una hora fija, renovada por SSM | Una hora de forma predeterminada; duraciones de solicitud/profile compatibles de 15 minutos a 12 horas, sujetas a la duración efectiva y al máximo del rol |
| Desconexión | No puede renovar; el backoff de reintentos puede retrasar la reconexión después de recuperar la red | No puede obtener credenciales nuevas sin conexión; credential-process las obtiene bajo demanda cuando regresa la conectividad |
| Escala / costo | Sin cargo de registro de nodos ni administración por nodo de SSM; el precio de uso de la característica es independiente | Revise las cuotas de IAM Roles Anywhere y los requisitos operativos de PKI |
| Elección habitual | Sin PKI existente; registro más sencillo | PKI existente y ciclo de vida de certificados administrado |

**Precios verificados el 16 de septiembre de 2026:** SSM eliminó el nivel Advanced Instances Tier con vigencia a partir del 30 de junio de 2026. Consulte los [precios actuales de SSM](https://aws.amazon.com/systems-manager/pricing/) para los términos de uso de Session Manager y Run Command; los [cargos de vCPU de EKS Hybrid Nodes](https://aws.amazon.com/eks/pricing/) siguen siendo independientes.

El profile de Roles Anywhere debe aceptar un nombre de sesión de rol personalizado y la política de confianza debe vincularlo al atributo de certificado elegido. Su duración de sesión efectiva **no debe superar** el máximo del rol de IAM; CreateSession API permite la igualdad. Los [requisitos previos](01-prerequisites.md) detallan estos contratos y la preparación segura.

## Cargas de trabajo de ejemplo

1. Entrenamiento o inferencia de GPU local con un runtime verificado y un plan de recuperación.
2. Procesamiento de datos local con rutas de metadatos, telemetría y salida de AWS revisadas por separado.
3. Aplicaciones de fábrica/edge con conectividad confiable y comportamiento de desconexión probado.
4. Procesamiento de medios cerca de grandes conjuntos de datos existentes.

## Próximos pasos

Comience con los [Requisitos previos y requisitos del sistema](01-prerequisites.md) para asegurarse de que su entorno esté listo para EKS Hybrid Nodes.

## Cuestionario

Para comprobar su comprensión de EKS Hybrid Nodes, pruebe el siguiente cuestionario:

* [Cuestionario de requisitos previos de EKS Hybrid Nodes](../quizzes/eks-hybrid-nodes/01-prerequisites-quiz.md)
* [Cuestionario de configuración de red de EKS Hybrid Nodes](../quizzes/eks-hybrid-nodes/02-network-configuration-quiz.md)
* [Cuestionario de configuración con acceso restringido a Internet de EKS Hybrid Nodes](../quizzes/eks-hybrid-nodes/03-airgap-setup-quiz.md)
* [Cuestionario de bootstrap de nodos de EKS Hybrid Nodes](../quizzes/eks-hybrid-nodes/04-node-bootstrap-quiz.md)
* [Cuestionario de integración de GPU de EKS Hybrid Nodes](../quizzes/eks-hybrid-nodes/05-gpu-integration-quiz.md)
* [Cuestionario de ubicación de cargas de trabajo de EKS Hybrid Nodes](../quizzes/eks-hybrid-nodes/06-workload-placement-quiz.md)
* [Cuestionario de administración del ciclo de vida de nodos](../quizzes/eks-hybrid-nodes/07-node-lifecycle-quiz.md)
* [Cuestionario de operaciones de EKS Hybrid Nodes](../quizzes/eks-hybrid-nodes/08-operations-quiz.md)
* [Cuestionario de instalación y migración del SO de servidores Bare Metal](../quizzes/eks-hybrid-nodes/09-bare-metal-os-setup-quiz.md)
* [Cuestionario de Gateway de EKS Hybrid Nodes](../quizzes/eks-hybrid-nodes/10-hybrid-nodes-gateway-quiz.md)
* [Cuestionario de revisión de seguridad de la separación de red](../quizzes/eks-hybrid-nodes/11-network-separation-security-quiz.md)

## Documentos relacionados

* [Guía de resiliencia de EKS](../eks/10-eks-resiliency.md) - Configuración de alta disponibilidad en entornos híbridos
* [Optimización de costos de EKS](../eks/07-eks-cost-optimization.md) - Estrategias de administración de costos
* [Monitoreo y registro de EKS](../eks/06-eks-monitoring-logging.md) - Configuración de monitoreo integrado

## Documentación oficial

* [Documentación oficial de AWS EKS Hybrid Nodes](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-overview.html)
* [Guía del usuario de nodeadm](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-nodeadm.html)
* [Documentación oficial de Harbor](https://goharbor.io/docs/)
* [Documentación de NVIDIA GPU Operator](https://docs.nvidia.com/datacenter/cloud-native/gpu-operator/overview.html)
* [Guía de redes de Hybrid Nodes](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-networking.html)
* [Configuración de CNI de Hybrid Nodes](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-cni.html)
* [Solución de problemas de Hybrid Nodes](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-troubleshooting.html)

* [Compatibilidad de sistemas operativos híbridos](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-os.html)
* [Credenciales híbridas y rol de IAM](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-creds.html)
* [Credenciales de host durante la desconexión de red](https://docs.aws.amazon.com/eks/latest/best-practices/hybrid-nodes-host-creds.html)
* [Semántica de CreateSession de IAM Roles Anywhere](https://docs.aws.amazon.com/rolesanywhere/latest/userguide/authentication-create-session.html)
* [Precios de EKS](https://aws.amazon.com/eks/pricing/)
