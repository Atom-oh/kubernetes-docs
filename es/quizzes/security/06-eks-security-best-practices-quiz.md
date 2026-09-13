# Cuestionario de mejores prácticas de seguridad de EKS

> **Última actualización**: September 13, 2026

Pon a prueba tu comprensión de las mejores prácticas de seguridad de Amazon EKS con las siguientes preguntas.

***

## Preguntas

<span id="_1-what-authentication-method-does-a-pod-use-when-calling-aws-apis-with-irsa-iam-roles-for-service-accounts"></span>

### 1. ¿Cómo obtiene un Pod credenciales temporales de AWS mediante IRSA?

* A) Clave de acceso de usuario de IAM
* B) Perfil de instancia de EC2
* C) AssumeRoleWithWebIdentity basado en token OIDC
* D) Credenciales almacenadas en Kubernetes Secret

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: C) AssumeRoleWithWebIdentity basado en token OIDC**

**Explicación:** El servidor de API de Kubernetes emite el JWT de ServiceAccount proyectado. Un SDK compatible lo intercambia con STS AssumeRoleWithWebIdentity; STS comprueba el emisor/JWKS de confianza, la audiencia y el sujeto, y devuelve credenciales temporales de AWS. El objeto de proveedor OIDC de IAM no es el emisor del token, y el JWT no se sustituye directamente por credenciales para la API de AWS.

</details>

***

### 2. ¿Cuál es la principal ventaja de EKS Pod Identity en comparación con IRSA?

* A) Cifrado más sólido
* B) Rendimiento más rápido
* C) No se requiere configuración de OIDC Provider, gestión simplificada
* D) Compatibilidad con más servicios de AWS

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: C) No se requiere configuración de OIDC Provider, gestión simplificada**

**Explicación:** Pod Identity evita la configuración de un proveedor OIDC de IAM por clúster y utiliza una asociación, un agente/SDK compatible y EKS Auth. Los roles aún requieren permisos de confianza y de privilegio mínimo. Auto Mode incluye el agente; otras plataformas y los roles entre cuentas/en cadena tienen requisitos específicos. No reemplaza IRSA ni refuerza automáticamente la seguridad de todas las aplicaciones.

</details>

***

<span id="_3-which-is-not-a-requirement-for-using-security-groups-for-pods"></span>

### 3. ¿Qué NO se requiere para la ruta de Security Groups for Pods respaldada por EC2?

* A) Tipos de instancia EC2 compatibles con trunking
* B) Plugin Amazon VPC CNI
* C) Perfil de Fargate
* D) Configuración de SecurityGroupPolicy

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: C) Perfil de Fargate**

**Explicación:** Para la ruta respaldada por EC2, utiliza un tipo de instancia compatible con trunking, Amazon VPC CNI compatible y SecurityGroupPolicy. No todas las instancias Nitro cumplen los requisitos. La política de VPC Resource Controller pertenece al rol del clúster. Fargate tiene un modelo compatible independiente; Windows y Auto Mode están excluidos por la documentación actual de Pod-SG. ENIConfig no sustituye a SecurityGroupPolicy.

</details>

***

### 4. ¿Cuál es el impacto de configurar el endpoint del servidor de API de Kubernetes del clúster EKS como privado únicamente?

* A) No se puede usar kubectl en absoluto
* B) Solo es accesible desde la VPC o redes conectadas
* C) No se puede administrar el clúster desde AWS Console
* D) Los nodos de trabajo no pueden conectarse al servidor de API

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Solo es accesible desde la VPC o redes conectadas**

**Explicación:** La accesibilidad a la API privada necesita una red conectada, DNS, rutas y security groups, además de autenticación de IAM y autorización de Kubernetes. Prueba el acceso de operadores, CI y recuperación antes de eliminar el acceso público. Un endpoint de administración PrivateLink de EKS no sustituye al endpoint privado de la API de Kubernetes.

</details>

***

### 5. ¿Qué tipo de amenaza NO detecta AWS GuardDuty EKS Protection?

* A) Comunicación con IP maliciosas
* B) Actividad de minería de criptomonedas
* C) Uso de recursos de Pod que supera los límites
* D) Conexiones a la red Tor

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: C) Uso de recursos de Pod que supera los límites**

**Explicación:** Distingue el análisis de auditoría de EKS, Runtime Monitoring basado en agentes y las fuentes fundamentales de GuardDuty. La cobertura varía según el plan y la plataforma habilitados; la compatibilidad con ECS Fargate no equivale a la compatibilidad con EKS Fargate. La monitorización de límites de CPU/memoria corresponde a las herramientas de métricas operativas, y un detector sin alertas no demuestra la ausencia de una vulneración.

</details>

***

<span id="_6-which-aws-service-does-not-require-vpc-endpoints-in-an-eks-cluster"></span>

### 6. ¿Cuál es la forma correcta de razonar sobre DNS y el acceso privado a la API de AWS?

* A) Un endpoint de administración de EKS sustituye a la API de Kubernetes
* B) Pod Identity siempre utiliza el endpoint global de STS
* C) Todas las regiones de AWS admiten los mismos nombres de endpoint
* D) Distinguir la resolución DNS de Route 53 management API PrivateLink

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: D) Distinguir la resolución DNS de Route 53 management API PrivateLink**

**Explicación:** La resolución DNS habitual utiliza el resolvedor/la ruta de red configurados. Las llamadas a Route 53 management API son diferentes; la documentación actual de clústeres privados de EKS enumera un servicio Route 53 PrivateLink. EKS Auth, STS regional, detección de OIDC y ECR/S3 también tienen rutas distintas, por lo que debes verificar los requisitos reales del servicio/la región.

</details>

***

### 7. ¿Qué benchmark se utiliza al comprobar la seguridad de un clúster EKS con kube-bench?

* A) PCI-DSS
* B) El perfil de benchmark CIS Amazon EKS aplicable
* C) NIST Cybersecurity Framework
* D) SOC 2

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) El perfil de benchmark CIS Amazon EKS aplicable**

**Explicación:** Elige la edición del benchmark CIS Amazon EKS y el perfil de kube-bench adecuados para el entorno. kube-bench0.16.0 incluye varios perfiles de EKS; un único Job ascendente mutable no demuestra la cobertura de toda la flota. Las comprobaciones manuales/no aplicables y las limitaciones del plano de control administrado se mantienen, y la puntuación de un cuestionario/herramienta no es una certificación.

</details>

***

### 8. ¿Qué beneficio de seguridad proporciona Service Account Token Volume Projection en EKS?

* A) Tamaño de token reducido
* B) Tokens vinculados y configuración del tiempo de expiración
* C) Cifrado de token
* D) Copia de seguridad automática de token

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Tokens vinculados y configuración del tiempo de expiración**

**Explicación:** La proyección permite una audiencia y una duración solicitada con vinculación de objetos. Comprueba la expiración real del token y la validación del receptor; no supongas que todos los tokens expiran exactamente una hora después. Un token de portador robado aún puede reutilizarse mientras sea aceptado, por lo que la proyección no elimina los requisitos de protección de tokens. La proyección por sí sola no es una configuración completa de IRSA.

</details>

***

### 9. ¿Qué analiza Amazon Inspector en un entorno EKS?

* A) Manifiestos de Kubernetes
* B) Vulnerabilidades de imágenes de contenedor
* C) Políticas de IAM
* D) Tráfico de red

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Vulnerabilidades de imágenes de contenedor**

**Explicación:** El análisis mejorado de ECR utiliza Inspector para detectar vulnerabilidades de paquetes de imágenes compatibles. La información sobre el uso de imágenes en ejecución difiere de la detección del comportamiento en tiempo de ejecución. Restringe el digest exacto solo después de un estado correcto, una marca de tiempo de finalización y un mapa explícito de recuento de hallazgos; los resultados pendientes/faltantes/con errores no deben convertirse en cero vulnerabilidades.

</details>

***

### 10. ¿Qué tipo de log NO se puede habilitar al enviar logs del Control Plane del clúster EKS a CloudWatch?

* A) api
* B) audit
* C) controllerManager
* D) kubelet

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: D) kubelet**

**Explicación:** Las cinco categorías del plano de control de EKS son api, audit, authenticator, controllerManager y scheduler. Los logs de Kubelet/contenedor requieren una ruta de recopilación de nodos/tiempo de ejecución independiente. Habilita las exportaciones mediante el propietario del clúster, inspecciona la actualización asíncrona y la llegada real, y configura la retención y el acceso.

</details>

***

### 11. ¿Por qué se deben separar el Node IAM Role y el Pod IAM Role (IRSA) en EKS?

* A) Ahorro de costes
* B) Aplicar el principio de privilegio mínimo
* C) Mejora del rendimiento
* D) Reducción de la latencia de red

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Aplicar el principio de privilegio mínimo**

**Explicación:** Los roles de workload limitan los permisos de la aplicación independientemente de las responsabilidades del nodo. La exposición del rol de nodo depende de la accesibilidad a metadatos y de los privilegios; no todos los Pod tienen acceso siempre. IRSA por sí solo no bloquea IMDS. Revisa IMDSv2, los controles de red, los workloads hostNetwork/con privilegios, la precedencia de credenciales del SDK y el compromiso de nodos.

</details>

***

<span id="_12-which-component-is-responsible-for-integrating-kubernetes-rbac-with-aws-iam-in-eks"></span>

### 12. ¿Qué enfoque otorga a un desarrollador de EKS únicamente el acceso de namespace requerido?

* A) Agregar a todos los desarrolladores a system:masters
* B) Compartir el rol de nodo con todos los desarrolladores
* C) Usar una entrada de acceso con una política de acceso con ámbito o mapeo de grupo/RBAC
* D) Deshabilitar la autenticación de la API

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: C) Usar una entrada de acceso con una política de acceso con ámbito o mapeo de grupo/RBAC**

**Explicación:** Utiliza una entrada de acceso con la política de acceso de EKS con ámbito requerida o el mapeo de grupo/RBAC de Kubernetes. La autenticación y la autorización son independientes. El ConfigMap aws-auth es una ruta heredada, y la migración del modo de autenticación tiene restricciones unidireccionales. Evita system:masters para desarrolladores habituales; las políticas de acceso de EKS o RBAC pueden permitir una operación de forma independiente.

</details>

***

## Cálculo de puntuación

Calcula 1 punto por pregunta.

| Puntuación | Calificación                                                     |
| ----- | ---------------------------------------------------------- |
| 11-12 | Repaso completo; valida los escenarios operativos a continuación                      |
| 8-10  | Bien - Conceptos básicos comprendidos, repasa las características avanzadas |
| 5-7   | Regular - Se recomienda estudio adicional                     |
| 0-4   | Se requiere aprendizaje básico                                      |

***

## Documentación relacionada

* [Mejores prácticas de seguridad de EKS](../../security/06-eks-security-best-practices.md)
* [Estándares de seguridad de Pod](../../security/03-pod-security-standards.md)
* [Gestión de Secrets](../../security/05-secrets-management.md)
