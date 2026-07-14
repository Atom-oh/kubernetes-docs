# Cuestionario del laboratorio de Observability, parte 1: configuración de infraestructura

> **Última actualización**: February 22, 2026

Pon a prueba tu comprensión de los conceptos de configuración de infraestructura tratados en el laboratorio integral de Observability, parte 1.

---

1. ¿Cuál es la diferencia principal de roles entre el Managed Cluster y el Service Cluster en una arquitectura de EKS con varios clusters?
   - A) El Managed Cluster ejecuta workloads de aplicación, mientras que el Service Cluster solo se encarga de la red
   - B) El Managed Cluster aloja herramientas de observabilidad y plataforma, mientras que el Service Cluster ejecuta workloads de aplicación
   - C) El Service Cluster administra todos los clusters, mientras que el Managed Cluster es para pruebas
   - D) No hay diferencia funcional; son intercambiables

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) El Managed Cluster aloja herramientas de observabilidad y plataforma, mientras que el Service Cluster ejecuta workloads de aplicación**

**Explicación:**
En una arquitectura con varios clusters, el Managed Cluster (a menudo llamado cluster de administración o plataforma) aloja servicios compartidos como stacks de observabilidad, herramientas de GitOps (ArgoCD) y componentes de plataforma. El/los Service Cluster ejecutan los workloads de aplicación reales. Esta separación proporciona mejor aislamiento de recursos, límites de seguridad y permite el escalado independiente de los servicios de plataforma frente a los workloads de aplicación.

</details>

---

2. ¿Por qué se prefiere IRSA (IAM Roles for Service Accounts) en lugar de usar perfiles de instancia de IAM para workloads de EKS?
   - A) IRSA se configura más rápido que los perfiles de instancia
   - B) IRSA proporciona permisos de IAM a nivel de Pod siguiendo el principio de mínimo privilegio
   - C) Los perfiles de instancia están obsoletos en AWS
   - D) IRSA permite políticas de IAM ilimitadas por Pod

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) IRSA proporciona permisos de IAM a nivel de Pod siguiendo el principio de mínimo privilegio**

**Explicación:**
IRSA (IAM Roles for Service Accounts) habilita permisos de IAM detallados a nivel de Pod al asociar roles de IAM con Service Accounts de Kubernetes. A diferencia de los perfiles de instancia, que otorgan los mismos permisos a todos los Pods de un Node, IRSA sigue el principio de mínimo privilegio al permitir que cada workload tenga solo los permisos específicos que necesita. Esto mejora la postura de seguridad y facilita la auditoría y administración de permisos.

</details>

---

3. ¿Cuál es una compensación clave al elegir Terraform en lugar de eksctl para el aprovisionamiento de clusters de EKS?
   - A) Terraform no puede crear clusters de EKS en absoluto
   - B) Terraform proporciona mejor administración del estado y prácticas de infrastructure-as-code, pero tiene una curva de aprendizaje más pronunciada
   - C) eksctl es más adecuado para entornos de producción
   - D) Terraform solo funciona con regiones de AWS GovCloud

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Terraform proporciona mejor administración del estado y prácticas de infrastructure-as-code, pero tiene una curva de aprendizaje más pronunciada**

**Explicación:**
Terraform ofrece una sólida administración del estado, detección de drift, grafos de dependencias y funciona con varios proveedores de cloud mediante sintaxis HCL declarativa. Sin embargo, requiere aprender HCL y comprender los conceptos de Terraform. eksctl está diseñado específicamente para EKS, con una configuración YAML más sencilla y una creación de clusters más rápida, pero ofrece menos flexibilidad para la administración de infraestructura compleja. Terraform suele preferirse para entornos de producción donde las prácticas de infrastructure-as-code y la administración del estado son críticas.

</details>

---

4. ¿Por qué Aurora PostgreSQL utiliza una configuración de instancias writer/reader en una configuración de observabilidad de producción?
   - A) Para reducir los costos de licencias
   - B) Para proporcionar alta disponibilidad y separar las consultas de observabilidad con gran carga de lectura de las operaciones de escritura
   - C) Aurora solo admite esta configuración
   - D) Para habilitar exclusivamente la replicación entre regiones

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Para proporcionar alta disponibilidad y separar las consultas de observabilidad con gran carga de lectura de las operaciones de escritura**

**Explicación:**
La configuración writer/reader de Aurora PostgreSQL separa las operaciones de escritura (ingesta de métricas, almacenamiento de logs) de las operaciones de lectura (consultas de dashboards, consultas de alertas). Los workloads de observabilidad suelen tener una gran carga de lectura, con actualizaciones constantes de dashboards y evaluaciones de alertas. Las instancias reader manejan estas consultas sin afectar el rendimiento de escritura. Esta configuración también proporciona alta disponibilidad: si el writer falla, un reader puede promocionarse automáticamente, lo que minimiza el tiempo de inactividad.

</details>

---

5. ¿Cuáles son los componentes esenciales que deben configurarse al crear un workspace de Amazon Managed Service for Prometheus (AMP)?
   - A) Solo se requiere el nombre del workspace
   - B) Workspace, rol de IAM con permisos de remote write y endpoints de VPC para acceso seguro
   - C) Solo configuración de bucket de S3 para almacenamiento
   - D) Workspace e integración obligatoria con CloudWatch

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Workspace, rol de IAM con permisos de remote write y endpoints de VPC para acceso seguro**

**Explicación:**
Al configurar AMP, necesitas crear un workspace (el contenedor lógico para tus datos de Prometheus), configurar un rol de IAM con permisos de `aps:RemoteWrite` para la ingesta de datos y, opcionalmente, configurar endpoints de VPC para acceso a redes privadas. El rol de IAM se usa con IRSA para permitir que tus collectors se autentiquen y escriban métricas. Los endpoints de VPC garantizan que el tráfico no atraviese Internet público, lo que mejora la seguridad y reduce la latencia.

</details>

---

6. ¿Qué métodos se pueden utilizar para conectar Amazon Managed Grafana (AMG) a fuentes de datos?
   - A) Solo configuración manual mediante la UI de Grafana
   - B) Configuración de fuentes de datos de AWS, aprovisionamiento mediante la API de Grafana o Terraform/CloudFormation
   - C) Solo mediante comandos de AWS CLI
   - D) Las fuentes de datos se detectan automáticamente sin configuración

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Configuración de fuentes de datos de AWS, aprovisionamiento mediante la API de Grafana o Terraform/CloudFormation**

**Explicación:**
AMG admite varios métodos para la configuración de fuentes de datos: configuración de fuentes de datos nativas de AWS (que maneja la autenticación automáticamente para servicios de AWS como AMP, CloudWatch y X-Ray), aprovisionamiento basado en la API de Grafana para una configuración programática y herramientas de Infrastructure-as-Code como Terraform o CloudFormation. Esta flexibilidad permite a los equipos elegir el enfoque que mejor se adapte a su workflow, ya sea automatización basada en GitOps o configuración manual durante la configuración inicial.

</details>

---

7. ¿Qué configuraciones se requieren al registrar un Service Cluster con ArgoCD en una configuración con varios clusters?
   - A) Solo la URL del endpoint del cluster
   - B) Endpoint del cluster, credenciales de autenticación (token de Service Account o IAM) y nombre/etiqueta del cluster
   - C) Solo la ruta del archivo kubeconfig
   - D) El registro del cluster es automático una vez que ambos clusters están en la misma VPC

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Endpoint del cluster, credenciales de autenticación (token de Service Account o IAM) y nombre/etiqueta del cluster**

**Explicación:**
Registrar un cluster externo con ArgoCD requiere el endpoint del servidor de API del cluster, credenciales de autenticación (ya sea un token de Service Account con los permisos de RBAC adecuados o autenticación basada en IAM para EKS) y metadatos como el nombre y las etiquetas del cluster. El nombre y las etiquetas del cluster se utilizan en ApplicationSets para dirigir Deployments. Para EKS, se recomienda la autenticación basada en IAM mediante IRSA, ya que evita administrar tokens de larga duración.

</details>

---

8. ¿Cómo deberían integrarse los dominios de Amazon OpenSearch Service con EKS para el almacenamiento de logs?
   - A) OpenSearch no puede utilizarse con EKS
   - B) Mediante endpoints de VPC, control de acceso detallado y autenticación basada en IRSA para los transportadores de logs
   - C) Solo mediante endpoints públicos con listas blancas de IP
   - D) La integración de OpenSearch requiere CloudWatch como intermediario

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Mediante endpoints de VPC, control de acceso detallado y autenticación basada en IRSA para los transportadores de logs**

**Explicación:**
Para una integración segura de OpenSearch con EKS, implementa OpenSearch en modo VPC con endpoints de VPC para acceso privado. Habilita el control de acceso detallado para administrar permisos a nivel de índice. Configura los transportadores de logs (como FluentBit o Grafana Alloy) con IRSA para autenticarse mediante roles de IAM. Esta configuración garantiza que los logs se transmitan de forma segura dentro de la VPC, que el acceso se controle a nivel de índice y que la autenticación siga las mejores prácticas de seguridad de AWS.

</details>

---

9. ¿Cuál es el rol del bucket de DAG de S3 en un entorno de Amazon MWAA (Managed Workflows for Apache Airflow)?
   - A) Almacena únicamente logs de ejecución de Airflow
   - B) Almacena archivos DAG, plugins y requisitos que MWAA carga para definir y ejecutar workflows
   - C) Sirve como copia de seguridad para la base de datos de MWAA
   - D) Proporciona almacenamiento temporal para las salidas de tareas

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Almacena archivos DAG, plugins y requisitos que MWAA carga para definir y ejecutar workflows**

**Explicación:**
El bucket de DAG de S3 es la fuente de verdad para las definiciones de workflows de MWAA. Almacena archivos Python de DAG (Directed Acyclic Graph) que definen workflows, plugins personalizados para ampliar la funcionalidad de Airflow y requirements.txt para dependencias adicionales de Python. MWAA sincroniza continuamente este bucket, detectando y cargando automáticamente DAG nuevos o actualizados. Este enfoque basado en S3 habilita workflows de GitOps donde los cambios de DAG se implementan mediante pipelines de CI/CD.

</details>

---

10. ¿Por qué se instala Argo Rollouts en el Service Cluster en lugar del Managed Cluster?
    - A) Argo Rollouts no puede comunicarse entre clusters
    - B) Los controllers de Rollouts necesitan acceso directo a los workloads que administran para Deployments canary/blue-green
    - C) Instalarlo en menos clusters reduce los costos de licencias
    - D) El Managed Cluster no admite la instalación de CRD

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Los controllers de Rollouts necesitan acceso directo a los workloads que administran para Deployments canary/blue-green**

**Explicación:**
Los controllers de Argo Rollouts administran la entrega progresiva de aplicaciones mediante estrategias de Deployment canary, blue-green u otras. Necesitan acceso directo para modificar ReplicaSets, Services y otros recursos en el cluster donde se ejecutan los workloads. Aunque ArgoCD puede realizar Deployments desde una ubicación central, los controllers de Rollouts administran activamente el desplazamiento de tráfico y el escalado de Pods durante los Deployments, lo que requiere que se ejecuten junto a los workloads que controlan. Por ello, Rollouts se instala en cada Service Cluster.

</details>
