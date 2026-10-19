# Registro de contenedores

> **Última actualización**: 11 de septiembre de 2026

## Introducción

Los registros de contenedores son componentes fundamentales de la infraestructura del ecosistema Kubernetes. Funcionan como repositorios centralizados para almacenar, administrar y distribuir imágenes de contenedor. Actúan como puente entre los pipelines de CI/CD y los clústeres de Kubernetes, lo que permite entregar imágenes de forma fiable y segura a las cargas de trabajo.

Un registro de contenedores proporciona:

- **Almacenamiento de imágenes**: almacenamiento persistente de imágenes de contenedor con control de versiones mediante etiquetas
- **Control de acceso**: mecanismos de autenticación y autorización para controlar quién puede enviar y descargar imágenes
- **Análisis de seguridad**: detección de vulnerabilidades en imágenes de contenedor antes del despliegue
- **Distribución**: almacenamiento en caché y distribución eficientes de capas de imágenes a los entornos de ejecución de contenedores
- **Administración del ciclo de vida**: políticas automatizadas de limpieza y retención para optimizar el almacenamiento

![Diagrama de flujo que muestra cómo una imagen de contenedor pasa del pipeline de CI/CD (compilar, probar, enviar) a un registro de contenedores (almacenar, versionar, analizar) y luego a un clúster de Kubernetes (descargar, ejecutar, escalar).](../.gitbook/assets/en-container-registry-readme-0.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-container-registry-readme-0.html)

## Comparación de registros

| Característica | Docker Hub | Amazon ECR | Harbor |
|---------|------------|------------|--------|
| **Tipo** | SaaS (nube pública) | Servicio administrado de AWS | Autohospedado (CNCF) |
| **Modelo de precios** | Suscripciones personales y de pago | Según el uso | Infraestructura, operaciones y copias de seguridad |
| **Repositorios privados** | Personal: 1; límites según el plan de pago | Se aplican cuotas del servicio | Cuotas configuradas por el operador |
| **Repositorios públicos** | Disponibles según las políticas del plan | ECR Public con límites gratuitos y cargos por uso | Compatible |
| **Precio del almacenamiento** | Depende del plan | Depende de la región y la clase de almacenamiento | Autoadministrado |
| **Transferencia de datos** | Políticas de uso y uso razonable | Cargos según el destino y la región | Autoadministrada |
| **Análisis de vulnerabilidades** | Límites de los planes de Docker Scout | Básico / Mejorado (Inspector) | Integración con Trivy |
| **Firma de imágenes** | DCT o herramientas OCI de firma independientes | Firma administrada o manual con AWS Signer | Cosign/Notation |
| **Replicación** | No disponible | Replicación entre regiones | Replicación mediante descarga/envío |
| **RBAC** | A nivel de organización | Políticas de IAM | Roles a nivel de proyecto |
| **Operación completamente desconectada** | Requiere acceso a Hub | Requiere conectividad con AWS; los VPC endpoints proporcionan acceso privado | Importación de imágenes, bases de datos de escáneres y dependencias de instalación |
| **Límites de solicitudes** | Límites de descarga y políticas de uso razonable específicos de cada cuenta | Cuotas del servicio por API | Límites del operador y capacidad de la infraestructura |
| **Integración** | Universal | Nativa de AWS (EKS, IAM) | Nativa de Kubernetes |
| **Cumplimiento** | Consulta las certificaciones y el alcance actuales del servicio | Comprueba la elegibilidad del servicio y la región de AWS, así como tus controles | El operador es responsable de los controles y las pruebas |

ECR tiene [cuotas de servicio](https://docs.aws.amazon.com/AmazonECR/latest/userguide/service-quotas.html), incluidos límites para la tasa de solicitudes y los repositorios. Se admite la [integración con AWS Signer](https://docs.aws.amazon.com/AmazonECR/latest/userguide/image-signing.html); el almacenamiento de firmas y la aplicación de la verificación durante el despliegue son configuraciones independientes. Consulta la [política de uso actual](https://docs.docker.com/docker-hub/usage/) y los encabezados de respuesta de Docker Hub, en lugar de considerar universal un límite histórico de descargas.

## Comparación detallada

### Docker Hub

**Ideal para**: proyectos de código abierto, entornos de desarrollo y equipos que necesitan una configuración rápida

**Ventajas**:
- La biblioteca pública de imágenes más grande (imágenes oficiales, publicadores verificados)
- No requiere administrar infraestructura
- Integración sencilla con Docker CLI
- Automatización de compilación y envío mediante CI externo, como GitHub Actions/GitLab CI; Automated Builds nativo de Hub está obsoleto

**Desventajas**:
- Límites de descarga y controles de uso razonable y abuso específicos de cada cuenta
- Almacenamiento limitado para repositorios privados en los planes gratuitos
- Sin integración nativa con AWS/Kubernetes
- Posibles riesgos de seguridad de la cadena de suministro con imágenes públicas

**Precios**: Compara los usuarios, la facturación mensual o anual y el uso incluido de Scout y compilaciones en la [página de precios actual](https://www.docker.com/pricing/). Los precios históricos de $5 para Pro y $9 para Team, así como los límites diarios de descargas, no son una referencia válida para los precios actuales.

### Amazon ECR

**Ideal para**: cargas de trabajo nativas de AWS, clústeres de EKS y empresas que requieren cumplimiento normativo

**Ventajas**:
- Integración con los roles de ejecución de los nodos de EKS y Fargate; los permisos de IRSA/Pod Identity de las cargas de trabajo son independientes de las credenciales para descargar imágenes
- Acceso basado en IAM y cuotas de servicio de API ajustables
- Replicación entre regiones
- Análisis mejorado con Amazon Inspector
- VPC endpoints para conectividad privada con AWS, que no equivale a un entorno completamente desconectado
- Precios según el uso (sin compromiso inicial)

**Desventajas**:
- Dependencia del proveedor AWS
- Los costos pueden acumularse con bibliotecas de imágenes grandes
- Sintaxis compleja para las políticas del ciclo de vida
- El acceso entre cuentas requiere una configuración cuidadosa de IAM

**Precios**: Multiplica los datos almacenados por la tarifa regional y de clase de almacenamiento aplicable; luego, ten en cuenta los cargos por transferencia, Inspector, AWS Signer y VPC endpoints. Con la tarifa de ejemplo oficial de $0.10/GB al mes, 100 GB cuestan $10 al mes **solo por almacenamiento**. Las transferencias dentro de la misma región a servicios de cómputo de AWS compatibles tienen tarifas distintas de las del tráfico por Internet o entre regiones; consulta los [precios de ECR](https://aws.amazon.com/ecr/pricing/) para conocer el costo de la ruta correspondiente.

### Harbor

**Ideal para**: entornos locales, entornos aislados, entornos multinube e industrias con requisitos de cumplimiento estrictos

**Ventajas**:
- Control total sobre los datos y la infraestructura
- Sin dependencia de proveedores
- Conjunto completo de funciones (replicación, análisis, firma y RBAC)
- Proyecto graduado de CNCF con una comunidad sólida
- Ideal para industrias reguladas (finanzas, atención sanitaria y gobierno)

**Desventajas**:
- Sobrecarga operativa (despliegue, actualizaciones y copias de seguridad)
- Requiere inversión en infraestructura
- Curva de aprendizaje para la administración
- Complejidad de la configuración de alta disponibilidad

**Precios**: Sin costo de licencia. Los costos de infraestructura dependen del despliegue:
- Recursos del clúster de Kubernetes (CPU, memoria y almacenamiento)
- Almacenamiento persistente (bases de datos y almacenamiento del registro)
- Costos de red y balanceadores de carga

## Criterios de selección

Elige el registro de contenedores según estos factores:

### 1. Entorno de infraestructura

| Entorno | Registro recomendado |
|-------------|---------------------|
| Nativo de AWS (EKS) | Amazon ECR |
| Multinube / híbrido | Harbor |
| Desarrollo / código abierto | Docker Hub |
| Aislado / desconectado | Harbor |
| Edge / IoT | Harbor (con replicación) |

### 2. Requisitos de seguridad y cumplimiento

Compara el control de acceso, la duración de las credenciales, el análisis de vulnerabilidades, la fijación por digest, la verificación de firmas, los límites de red y los procedimientos de recuperación. Un producto no es automáticamente más seguro por ser autohospedado o pertenecer a un nivel de suscripción superior. La elegibilidad de un servicio para cumplir determinadas normas tampoco hace que una carga de trabajo cumpla esas normas si carece de los controles requeridos.

- **Requisitos de AWS**: Comprueba la elegibilidad de ECR para la región y el alcance de cumplimiento específicos.
- **Soberanía de datos u operación desconectada**: Harbor proporciona control sobre el despliegue; el operador es responsable de las actualizaciones, las copias de seguridad y la recopilación de pruebas.
- **Colaboración administrada**: Compara las funciones reales del plan de Docker Hub con los controles que necesita el equipo.

### 3. Tamaño del equipo y presupuesto

- **Equipo pequeño, presupuesto limitado**: Docker Hub Free/Pro
- **Equipo en crecimiento que usa AWS**: Amazon ECR (pago por uso)
- **Empresa con un equipo de plataforma dedicado**: Harbor

### 4. Preferencias operativas

- **Totalmente administrado, sin operaciones**: Docker Hub o Amazon ECR
- **Control total y personalización**: Harbor

## Contenido de la sección

Esta sección aborda en profundidad los conceptos y la implementación de los registros de contenedores:

1. [Docker Hub](01-docker-hub.md) - Uso de registros públicos, límites de solicitudes e integración con Kubernetes
2. [Amazon ECR](02-amazon-ecr.md) - Registro nativo de AWS con políticas del ciclo de vida e integración con EKS
3. [Harbor](03-harbor.md) - Registro empresarial autohospedado y graduación de CNCF
4. [Prácticas recomendadas](04-best-practices.md) - Estrategias para distintos registros en materia de seguridad, costos y operaciones

## Árbol de decisión para comenzar rápidamente

![Árbol de decisión para elegir un registro de contenedores: los entornos aislados conducen a Harbor autohospedado; las cargas de trabajo conectadas de AWS/EKS conducen a Amazon ECR; otras cargas de trabajo de producción con requisitos de cumplimiento conducen a Harbor o Docker Hub Business; el resto usa Docker Hub Free/Pro.](../.gitbook/assets/en-container-registry-readme-1.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-container-registry-readme-1.html)

## Resumen

Los registros de contenedores son infraestructura crítica que afecta directamente a la fiabilidad de los despliegues, la postura de seguridad y los costos operativos. Docker Hub ofrece la forma más sencilla de empezar, Amazon ECR proporciona la integración más estrecha con AWS y Harbor brinda el máximo control y flexibilidad para requisitos empresariales complejos.

Los documentos siguientes de esta sección proporcionan instrucciones detalladas de implementación para cada opción de registro y te ayudarán a sacar el máximo partido a la solución que elijas.
