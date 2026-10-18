# Creación de clústeres EKS: conclusión y mejores prácticas

> **Última actualización**: 11 de septiembre de 2026

## Comparación de métodos para crear clústeres EKS

Hemos explorado varios métodos para crear clústeres EKS. Comparemos las ventajas y desventajas de cada uno.

Elija una herramienta según su reproducibilidad, facilidad de revisión, competencias del equipo y responsabilidad del ciclo de vida. Con cualquiera de las opciones puede crear un clúster que aún requiere validar las cargas de trabajo, la red y la seguridad. Mantenga cada recurso bajo un responsable designado y revise los planes y conjuntos de cambios; no combine cambios manuales con IaC sin reconciliar el estado.

### eksctl

**Ventajas:**
- Flujos de trabajo concisos y orientados a EKS; la velocidad depende de los recursos solicitados
- Creación del clúster con un solo comando
- Compatibilidad con configuración declarativa mediante archivos YAML
- Compatibilidad con distintas funciones, como grupos de nodos y perfiles de Fargate

**Desventajas:**
- Puede quedarse corto para requisitos de infraestructura complejos
- La integración con la infraestructura existente puede ser difícil

**Casos de uso adecuados:**
- Prototipado rápido
- Entornos de desarrollo y prueba
- Entornos de producción con configuración, propiedad y controles del ciclo de vida revisados

### Consola de administración de AWS

**Ventajas:**
- Interfaz visual fácil de entender
- Creación guiada del clúster paso a paso
- Confirmación visual de distintas opciones

**Desventajas:**
- El proceso manual dificulta la automatización
- Las tareas repetitivas requieren mucho tiempo
- La gestión de la configuración y el control de versiones son difíciles

**Casos de uso adecuados:**
- Aprendizaje y exploración
- Creación de un clúster por única vez
- Equipos o proyectos pequeños

### AWS CLI

**Ventajas:**
- Posibilidad de automatizar mediante scripts
- Control detallado
- Integración sencilla con los servicios de AWS

**Desventajas:**
- Estructura de comandos compleja
- Requiere ejecutar varios comandos
- El manejo de errores puede ser difícil

**Casos de uso adecuados:**
- Como parte de scripts de automatización
- Integración con pipelines de CI/CD
- Entornos que requieren control detallado

### Terraform

**Ventajas:**
- Infraestructura como código (IaC)
- Gestión del estado y seguimiento de cambios
- Integración con varios servicios de AWS
- Modularización y reutilización

**Desventajas:**
- Tiene una curva de aprendizaje
- La configuración inicial requiere tiempo
- El estado necesita almacenamiento protegido, bloqueo y recuperación; un backend local, por sí solo, no requiere infraestructura adicional

**Casos de uso adecuados:**
- Entornos de producción a gran escala
- Gestión de varios entornos (desarrollo, preproducción y producción)
- Requisitos de infraestructura complejos

### AWS CDK

**Ventajas:**
- Uso de lenguajes de programación conocidos (TypeScript, Python, etc.)
- Alto nivel de abstracción
- Reutilización y modularización del código
- Integración estrecha con los servicios de AWS

**Desventajas:**
- Tiene una curva de aprendizaje
- La depuración puede ser compleja
- La cobertura de constructos y versiones varía; revise CloudFormation sintetizado y el comportamiento de los recursos personalizados

**Casos de uso adecuados:**
- Entornos centrados en desarrolladores
- Infraestructura de aplicaciones complejas
- Integración con el código de aplicaciones existentes

## Mejores prácticas para crear clústeres EKS

### Redes

1. **Diseño de VPC**
   - Despliegue subredes en al menos 2 zonas de disponibilidad
   - Elija subredes públicas o privadas según los requisitos reales de ingreso y salida; los diseños solo privados pueden utilizar endpoints de servicio y conectividad privada
   - Planifique las direcciones utilizables, los pools de calentamiento/prefijos del CNI y el margen para actualizaciones; distinga el espacio de subred de los límites de ENI por nodo y de maxPods
   - Use las etiquetas y la configuración de descubrimiento de subredes del controlador elegido; las etiquetas no establecen rutas ni límites de seguridad

2. **Configuración de grupos de seguridad**
   - Aplique el principio de privilegio mínimo
   - Permita las rutas reales de API, kubelet, DNS, webhooks y aplicaciones; kubelet usa TCP 10250, no un rango efímero amplio arbitrario
   - Restrinja las direcciones IP de origen
   - Utilice referencias a grupos de seguridad

3. **Políticas de red**
   - Elija un motor de políticas compatible: políticas nativas de VPC CNI o un diseño apropiado de Calico/Cilium; no habilite motores en conflicto
   - Restrinja la comunicación entre Pods
   - Verifique con pruebas positivas y negativas las restricciones de ingreso/salida de namespaces y DNS; las reglas de autorización coincidentes de Kubernetes NetworkPolicy se suman

### Seguridad

1. **Roles y políticas de IAM**
   - Aplique el principio de privilegio mínimo
   - Use EKS Pod Identity o IRSA según los requisitos de cómputo, agente/SDK y confianza; limite los permisos de las aplicaciones
   - Configure políticas de permisos detalladas

2. **Cifrado**
   - Habilite el cifrado de volúmenes EBS
   - Verifique el cifrado de sobre de los datos de la API de EKS predeterminado (KMSv2 para 1.28 o posterior) y si se necesita una clave de KMS administrada por el cliente; base64 no es cifrado
   - Cifre los datos en tránsito mediante TLS

3. **Autenticación y autorización**
   - Use la autenticación IAM de EKS y las entradas/políticas de acceso según corresponda; al usar tokens de AWS CLI, no se requiere necesariamente un binario independiente de cliente aws-iam-authenticator
   - Revise en conjunto las concesiones de RBAC de Kubernetes y las políticas de acceso de EKS; los permisos efectivos se acumulan
   - Separe identidades y namespaces mediante RBAC, Pod Security y controles de red; los namespaces por sí solos no proporcionan aislamiento completo entre tenants

### Escalabilidad y disponibilidad

1. **Configuración del grupo de nodos**
   - Despliegue nodos en varias zonas de disponibilidad
   - Identifique quién administra el cómputo: grupos de nodos administrados o autoadministrados, Karpenter, Auto Mode o Fargate; no suponga que todos los modos usan un ASG administrado por un operador
   - Utilice distintos tipos de instancia, incluidas instancias Spot

2. **Cluster Autoscaler**
   - Cuando sea necesario, use una versión compatible de Cluster Autoscaler/Karpenter; Auto Mode administra su propia capacidad. Evite varios responsables para el mismo pool
   - Distinga el escalado de réplicas de cargas de trabajo del aprovisionamiento de nodos; valide las solicitudes, los Pods no programables y las restricciones de capacidad
   - Ajuste los presupuestos y la temporización de interrupción/consolidación mediante el controlador elegido; pruebe el drenaje y la recuperación de aplicaciones

3. **Configuración de alta disponibilidad**
   - Utilice varias zonas de disponibilidad
   - Use PodDisruptionBudget para los desalojos voluntarios que corresponda; no evita fallos de nodos ni todas las interrupciones forzadas
   - Establezca réplicas, distribución topológica, preparación y capacidad según los escenarios de fallo previstos

### Supervisión y registros

1. **Registros del plano de control**
   - Considere los cinco tipos de registro del plano de control (api, audit, authenticator, controllerManager y scheduler), con controles de retención, acceso y costo
   - Intégrelos con CloudWatch Logs

2. **Supervisión de nodos y Pods**
   - Elija las señales necesarias de CloudWatch Container Insights y sus complementos, así como una configuración de cómputo compatible
   - Use Prometheus/Grafana o la plataforma de supervisión existente de forma deliberada; evite la recopilación duplicada y la instrumentación automática no revisada
   - Configure métricas personalizadas

3. **Alertas y notificaciones**
   - Configure alarmas de CloudWatch
   - Configure destinos de notificación autorizados y confirme la entrega y la responsabilidad; no suponga que una suscripción ya está confirmada
   - Configure notificaciones para eventos críticos

### Optimización de costos

1. **Selección del tipo de instancia**
   - Elija tipos de instancia adecuados para las cargas de trabajo
   - Use Spot en cargas tolerantes a interrupciones, con capacidad y manejo de fallos probados
   - Considere Graviton tras validar la compatibilidad de arquitectura de la aplicación, las imágenes, los agentes y los complementos

2. **Escalado automático**
   - Configure el escalado automático según la demanda
   - Optimice las políticas de reducción de escala
   - Considere el escalado programado

3. **Solicitudes y límites de recursos**
   - Establezca solicitudes de CPU y memoria adecuadas
   - Defina límites según el comportamiento de las cargas de trabajo; tenga en cuenta los OOM de memoria y la limitación de CPU en lugar de tratar todos los límites como protección gratuita
   - Establezca cuotas de recursos y rangos de límites

4. **Uso de Fargate**
   - Use Fargate solo si sus restricciones de programación, red, almacenamiento y privilegios se ajustan a la carga de trabajo
   - Optimice los perfiles de Fargate
   - Evalúe el costo frente al rendimiento

## Próximos pasos

Después de crear correctamente un clúster EKS, considere estos pasos:

1. **Establecer una estrategia de actualización del clúster**
   - Planifique según el catálogo de compatibilidad de EKS y la compatibilidad exacta de complementos, clientes y nodos, no solo según las versiones upstream de Kubernetes
   - Compare las estrategias de actualización in situ y de clúster de reemplazo; la reversión actual del plano de control de EKS es condicional y no restaura los datos de las aplicaciones
   - Automatice las pruebas de actualización

2. **Planificación de recuperación ante desastres**
   - Defina RPO/RTO y respalde los datos de aplicaciones, la configuración y las claves necesarias; pruebe la coherencia y la restauración, no solo la creación de instantáneas
   - Elija recuperación multirregión solo con supuestos explícitos de replicación, DNS/conmutación por error, IAM/KMS y costos
   - Pruebe escenarios de fallo

3. **Integración con pipelines de CI/CD**
   - Implemente flujos de trabajo de GitOps
   - Construya pipelines automatizados de despliegue
   - Automatice las pruebas y la validación

4. **Integración de servicios adicionales**
   - Use AWS Load Balancer Controller cuando lo requiera la ruta de cómputo/ingreso elegida; evite duplicar controladores administrados por Auto Mode
   - Configure ExternalDNS con propiedad de DNS y permisos IAM de alcance definido
   - Use cert-manager cuando Kubernetes deba emitir certificados; la gestión de certificados ACM para ALB es una ruta distinta
   - Elija almacenamiento EBS/EFS según la compatibilidad del cómputo y quién lo aprovisiona; las rutas de EBS de Auto Mode y de almacenamiento de Fargate difieren de los complementos EC2 normales

5. **Refuerzo de la seguridad**
   - Implemente análisis de vulnerabilidades
   - Supervise el cumplimiento
   - Automatice las políticas de seguridad

La creación de un clúster EKS es solo el comienzo del recorrido con Kubernetes. Para mantener un entorno de Kubernetes estable y eficiente, es importante gestionarlo, supervisarlo y optimizarlo continuamente.

## Referencias de verificación

- [Requisitos de red de EKS](https://docs.aws.amazon.com/eks/latest/userguide/network-reqs.html)
- [Clústeres EKS privados](https://docs.aws.amazon.com/eks/latest/userguide/private-clusters.html)
- [Pod Identity](https://docs.aws.amazon.com/eks/latest/userguide/pod-identities.html)
- [Cifrado de sobre de los datos de API](https://docs.aws.amazon.com/eks/latest/userguide/envelope-encryption.html)
- [Permisos de políticas de acceso](https://docs.aws.amazon.com/eks/latest/userguide/access-policies.html)
- [EKS Auto Mode](https://docs.aws.amazon.com/eks/latest/userguide/automode.html)
- [Reversión condicional de clúster](https://docs.aws.amazon.com/eks/latest/userguide/rollback-cluster.html)

Los detalles de implementación y los ejemplos comprobados localmente están en [la parte 4 de creación](02-eks-cluster-creation-part4.md), [la parte 5](02-eks-cluster-creation-part5.md) y [la parte 2 de redes](03-eks-networking-part2.md). La preparación para producción requiere las pruebas correspondientes en el entorno y pruebas de fallo/restauración.
