# Marco de decisión y diseño de PoC

> **Última actualización**: 12 de octubre de 2026

Los límites de Landing Zone, cuentas/IAM, EKS, VPC y datos/seguridad tratados hasta ahora deben evaluarse de forma independiente, pero en la práctica todos deben poder reproducirse a partir de una única matriz de decisión. Este documento explica cómo diseñar esa matriz y validar mediante PoC las partes que requieren mediciones reales.

## 1. Factores de decisión que se suelen pasar por alto

Por muy cuidadosamente que diseñe los límites, las cuentas y la estructura de red, no puede determinar si el diseño es realmente correcto sin lo siguiente.

### Objetivos de RTO/RPO por CUJ: la brecha más grande

Sin objetivos de RTO (objetivo de tiempo de recuperación)/RPO (objetivo de punto de recuperación) definidos para cada CUJ (recorrido crítico del usuario), sencillamente no se puede determinar:

- Si la conmutación por error de un runtime EKS A/B es suficientemente rápida (la suma del TTL de DNS + propagación de borde + propagación de Route 53 + retraso de detección del estado)
- Qué modelo de titularidad de datos, centralizado o propiedad de las cargas de trabajo, permite realmente recuperarse (si el tiempo de copia de instantáneas cuenta para el RTO)
- Si importa la diferencia entre 2 AZ y 3 AZ (si se mantienen los SLO en un estado N-1)
- Si se justifica el costo adicional del aislamiento a nivel de celda

**Defina primero una tabla de objetivos de RTO/RPO/tasa de errores aceptable por CUJ.**

### Titularidad de la respuesta durante incidentes

Aunque las decisiones sobre límites tengan en cuenta la seguridad, las cuotas, los costos, el ciclo de vida y el radio de impacto, no especificar «quién responde primero» hace perder tiempo durante un incidente a las 2 de la mañana en un clúster compartido cuando no está claro si el problema es del CNI o de la aplicación. Añada columnas de «responsable principal de respuesta» y «ruta de escalamiento» a la matriz de decisión, y adopte la regla de que **un límite con más de un responsable principal es candidato a dividirse.**

### Versión de Kubernetes de destino y estrategia de actualización

Los valores del campo `trafficDistribution`, la integración de cambio zonal de ARC de Karpenter (1.12+) y la adopción de EKS Auto Mode (quién es propietario del ciclo de vida de los nodos), así como la matriz de compatibilidad de complementos, dependen de la versión de EKS. Si se usa el runtime EKS A/B para aislar las actualizaciones, hay que formalizar la desviación de versiones permitida, la regla de actualizar siempre primero un lado y si se usa soporte extendido.

<span id="alb-weighted-target-group-s-fail-open-behavior"></span>

### Separar el reenvío ponderado del comportamiento de fail-open del grupo de destino

Una acción de reenvío ponderado no conmuta automáticamente a otro grupo de destino porque un grupo ponderado esté vacío o en mal estado. **El fail-open dentro del grupo seleccionado** es algo aparte: por debajo de su umbral de destinos en buen estado, un nodo del balanceador de carga puede enrutar a destinos accesibles en mal estado. Revise la conmutación por error de DNS y de enrutamiento mediante estos atributos:

- `target_group_health.unhealthy_state_routing.minimum_healthy_targets.count` (o `.percentage`)
- `target_group_health.dns_failover.minimum_healthy_targets.count` (o `.percentage`)

La configuración unificada aplica el mismo umbral a ambas acciones. Los umbrales de conmutación de DNS deben ser iguales o superiores a los de conmutación de enrutamiento; si se establecen ambos, cualquiera de los valores, recuento o porcentaje, puede activar una acción. Los porcentajes usan el recuento de destinos registrados, no el rendimiento CUJ demostrado ni la capacidad SLO en estado N-1. Condicione también los cambios de peso a la carga real, la tasa de errores y la latencia.

### Controlar las regiones no utilizadas

Además de la decisión sobre una única región, también debe abordar lo siguiente:

- **Prevención**: denegación SCP `aws:RequestedRegion` (con una lista de excepciones para servicios globales)
- **Detección**: revise la cobertura de CloudTrail, GuardDuty y Security Hub CSPM en las regiones permitidas/utilizables. Deshabilitar un producto no vuelve indetectable toda la actividad.
- **Regiones de activación opcional**: se pueden deshabilitar las regiones opcionales que no se usan; las regiones habilitadas de forma predeterminada no. Deshabilitar una región no elimina los recursos existentes ni detiene sus cargos. Combine limpieza, SCP y detección.

### Observabilidad de costos y momento de aplicación de etiquetas

Valide la atribución entre AZ uniendo Flow Logs, asignaciones ENI/IP, identidad de las cargas de trabajo de Kubernetes y categorías de facturación CUR. No todas las ENI admiten etiquetas de usuario ni condiciones RequestTag al crearse. Aplique políticas de etiquetas, IaC y condiciones SCP compatibles según la cobertura específica de cada servicio.

## 2. Diseñar la matriz de decisión

Las opciones tratadas en estos documentos (evaluación independiente de límites, carteras híbridas de cuentas, EKS compartido + dedicado, VPC de zonas de confianza mixtas, datos híbridos y titularidad híbrida de claves) establecen todas la **«reproducibilidad mediante una matriz de decisión»** como condición de validez. Sin una matriz de decisión, ningún resultado de PoC se puede convertir en un estándar.

Columnas recomendadas para la matriz de decisión:

| Columna | Propósito |
|---|---|
| ¿Necesita EKS? | Determina si el límite de EKS está subordinado al límite de VPC |
| Acceso a recursos entre cuentas | Elegir según corresponda entre encadenamiento de roles de destino, política de recursos o IRSA |
| ¿Usa un servicio no compatible con subredes compartidas? | Determina si se excluye de la estrategia de ubicación de VPC compartida |
| Grupos por par de permission set/cuenta | Comprobar el límite real de 100 y el crecimiento; 50 es un aviso local opcional |
| Responsable principal / ruta de escalamiento | Un límite con más de un responsable principal es candidato a dividirse |
| RTO/RPO del CUJ | Base para evaluar el diseño de datos y disponibilidad |

## 3. Patrones de diseño de PoC

Algunos puntos no se pueden cerrar sobre el papel y requieren mediciones reales. Las PoC siguientes se enumeran por orden de prioridad.

### PoC-0: Prueba de la matriz de decisión (ejecutar antes que todas las demás PoC)

- **Entradas**: 10–15 cargas de trabajo representativas (incluidos CUJ, al menos una carga de trabajo con PII, una carga de un dominio común, al menos dos herramientas internas pequeñas y al menos una integración con un socio externo)
- **Procedimiento**: pedir a dos personas que apliquen la matriz de decisión de forma independiente y comparar los resultados
- **Ejemplos de criterios de éxito**: desacuerdo inferior al 20 %, excepciones por debajo del 15 %; ajuste estas hipótesis locales
- **Producto derivado**: los resultados evaluados proporcionan estimaciones del número de cuentas/VPC/clústeres, que determinan los objetivos de medición de cuotas para el resto de las PoC

### PoC-1: Clúster compartido + cuenta de cargas de trabajo

| Medición | Criterios de éxito |
|---|---|
| Rutas de permisos de Pod Identity/política de recursos/IRSA | Validar la reutilización de origen/destino, el alcance, la revocación, KMS y la política de recursos; no usar una fórmula fija de 2 roles |
| Detección automática de subredes del controlador ALB en una subred compartida | Comprobar si falla la detección automática basada en etiquetas → si es así, normalizar el uso de anotaciones explícitas |
| Tasa de crecimiento de las entradas de acceso | (Aumento por carga de trabajo añadida) × número de cargas de trabajo objetivo < 3,000 |
| Número de grupos de nodos administrados | Margen frente al valor predeterminado de 30 y la cuota aplicada; distinguir ubicación de aislamiento de seguridad |
| Tiempo hasta la primera respuesta entre la cuenta del clúster y la cuenta de cargas de trabajo | Tiempo para determinar «problema de CNI frente a problema de aplicación» |
| Tiempo de detección/bloqueo de reglas Allow demasiado amplias de grupos de seguridad de participantes | Tiempo desde la detección hasta el bloqueo mediante una política de auditoría de Firewall Manager |

### PoC-2: Runtime EKS A/B y configuración de AZ (requisito previo: definir RTO/RPO por CUJ)

| Medición | Criterios de éxito |
|---|---|
| Inyectar 3 o más fallos de la lista del [capítulo 3](./03-eks-multi-account-multi-cluster.md) | Confirmar que cada fallo queda realmente contenido en un solo clúster |
| Simulación de cambio zonal automático de ARC | Confirmar que cada clúster A/B puede gestionar de forma independiente la carga máxima N-1 de AZ |
| Rendimiento/latencia de CoreDNS en N-1 | Tasa de aumento de latencia y si se alcanza el límite de 1,024 paquetes/s por ENI |
| Cobertura de AZ del grafo de servicios del CUJ | Validar la accesibilidad, la capacidad y la alternativa desde las AZ supervivientes |
| Recuperación con estado | Validar las restricciones de AZ de EBS, el almacenamiento/replicación alternativo, el tiempo de recuperación y la pérdida de datos |
| Tiempo integral de conmutación por error de A→B | Medir por separado la conmutación del borde y el cambio de registro de Route 53 |
| Tiempo de reversión | Medirlo por separado del tiempo de conmutación por error |
| Bytes entre AZ | Basarse en Flow Logs y comparar antes/después de la optimización |
| Multiplicador de capacidad aprovisionada previamente | Comparar valores medidos con las hipótesis 2x/1.5x |

### PoC-3: VPC compartida mínima / grupo de VPC compartidas

| Medición | Criterios de éxito |
|---|---|
| **Rutas TGW/VPC (actuales/proyección a 3 años)** | Separar el total de 10,000 de tablas TGW del límite VPC no propagado de 500/ajustable a 1,000; distinguir VGW 100 |
| Tasa de crecimiento de cuentas participantes | Frente al límite de 100, según el número objetivo de equipos |
| Subredes compartidas por cuenta | Combinaciones AZ × zona de confianza × propósito frente a 100 |
| Uso de NAU | Reflejar la densidad de Pods y cuándo resulta necesario el ajuste de 64,000 → 256,000 |
| Tiempo desde una solicitud de cambio de ruta/DNS hasta que el propietario la atiende | Cuantificar el cuello de botella |
| Integridad de la evidencia de Flow Logs | Determinar si los registros del propietario y el participante juntos pueden reconstruir el flujo completo |
| Tiempo de detección/recuperación de un cambio de ruta central incorrecto en las configuraciones mínima y dedicada | Medir ambas opciones (este es el verdadero factor de decisión) |
| Rendimiento de las conexiones TGW | Margen frente a 100 Gbps/7.5M PPS por AZ |

## 4. Relación con las operaciones basadas en IA

Este marco no se limita a decisiones de topología como cuenta/VPC/EKS; se puede ampliar hasta convertirlo en un principio operativo aplicado a cada ADR (registro de decisión de arquitectura). Las vías de ejecución para automatizar cambios de infraestructura suelen ser:

- **Solo IaC**: cambios únicamente mediante IaC escrito y revisado por personas. Ofrece la mayor reproducibilidad, pero es lento para el trabajo urgente o exploratorio.
- **IaC asistido por IA**: un agente genera propuestas de cambios de IaC que se ejecutan mediante el proceso existente de revisión → plan → aplicación. Reduce el costo de autoría, pero conlleva el riesgo de diferencias generadas extensas y desviación con respecto al estado real.
- **Política/intención + plan generado**: un agente lee el estado actual y genera un plan de ejecución. Separa la intención del backend, pero los esquemas de intención poco definidos y la conciliación deficiente del estado producen resultados incoherentes.
- **MCP/CLI/API directa del agente**: un agente aprobado realiza los cambios directamente y luego los verifica. Es la opción más rápida, pero conlleva riesgos de permisos demasiado amplios, fallos parciales e inyección de prompts.
- **Híbrida por nivel de riesgo**: IaC para cambios de configuración persistentes y de alto riesgo; ejecución directa limitada del agente para tareas de bajo riesgo y reversibles. Esta es la dirección realista para la mayoría de las organizaciones.

Para cada vía de ejecución, defina controles adecuados a su riesgo: intención legible por máquinas, instantánea previa a la ejecución, plan, comprobaciones deterministas de políticas, aprobación, identidad temporal de alcance limitado, comprobación posterior, registros de CloudTrail, conciliación del estado real y un contrato de recuperación.

> **Alcance de AWS MCP Server**: según la comprobación del 12 de octubre de 2026, la tabla de endpoints enumera ocho regiones (us-east-1, us-west-2, ap-northeast-1, ap-southeast-1/2, eu-central-1 y eu-west-1/2) y ningún endpoint de Seúl (ap-northeast-2). La ubicación del endpoint difiere de la región de un recurso administrado. La ejecución de API usa IAM y los permisos de los servicios posteriores, y los registros de CloudTrail están disponibles para revisión. Evalúe el endpoint, la autenticación, los registros y las rutas de datos según los requisitos de la organización; la mera ausencia de un endpoint de Seúl no demuestra una infracción normativa.

## Documentos relacionados

- [Resumen de gobernanza de la nube empresarial](./00-governance-overview.md)
- [Landing Zone, OU y control organizativo](./01-landing-zone-and-ou.md)
- [Estructura de cuentas y límites de IAM](./02-account-and-iam.md)
- [Arquitectura EKS multicuenta y multiclúster](./03-eks-multi-account-multi-cluster.md)
- [VPC compartida y conectividad](./04-shared-vpc-and-connectivity.md)
- [Límites de datos y seguridad](./05-data-security-boundaries.md)

## Referencias

- [Atributos de grupos de destino de ALB](https://docs.aws.amazon.com/elasticloadbalancing/latest/application/edit-target-group-attributes.html)
- [Estado de grupos de destino de ALB](https://docs.aws.amazon.com/elasticloadbalancing/latest/application/load-balancer-target-groups.html#target-group-health)
- [Tipos de acciones de reglas ALB (ponderadas)](https://docs.aws.amazon.com/elasticloadbalancing/latest/application/rule-action-types.html)
- [Enrutamiento ponderado de Route 53](https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/routing-policy-weighted.html)
- [Enrutamiento de conmutación por error de Route 53](https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/routing-policy-failover.html)
- [AWS MCP Server](https://docs.aws.amazon.com/agent-toolkit/latest/userguide/mcp-server.html)
- [IAM de AWS MCP Server](https://docs.aws.amazon.com/agent-toolkit/latest/userguide/security_iam_service-with-iam.html)
- [Endpoints regionales de AWS MCP](https://docs.aws.amazon.com/general/latest/gr/aws-mcp.html)
- [Cargos en regiones deshabilitadas](https://docs.aws.amazon.com/awsaccountbilling/latest/aboutv2/checklistforunwantedcharges.html)
