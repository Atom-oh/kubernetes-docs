# Cuestionario de integración de EKS

> **Documento relacionado**: [Integración de EKS](../../../networking/calico/08-eks-integration.md)
> **Última actualización**: February 22, 2026

## Cuestionario

1. ¿Cuál es la separación de funciones habitual al usar VPC CNI con Calico en EKS?
   - A) VPC CNI gestiona las políticas, Calico gestiona el networking
   - B) VPC CNI gestiona el networking (asignación de IP), Calico gestiona las políticas de red
   - C) VPC CNI y Calico gestionan el networking de forma redundante
   - D) Calico reemplaza completamente a VPC CNI

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) VPC CNI gestiona el networking (asignación de IP), Calico gestiona las políticas de red**

**Explicación:**
En la configuración de EKS más habitual, AWS VPC CNI gestiona el networking de los Pod mediante la asignación de IP desde la VPC, mientras que Calico se instala en modo «solo políticas» para proporcionar la aplicación de políticas de red. Esto combina la integración nativa de VPC con las potentes capacidades de políticas de Calico.

</details>

2. ¿Cuáles son los tres métodos principales para instalar Calico en EKS?
   - A) kubectl apply, Docker, AWS CLI
   - B) Complemento de EKS, Tigera Operator, Helm chart
   - C) CloudFormation, Terraform, Pulumi
   - D) eksctl, Consola de AWS, SDK

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Complemento de EKS, Tigera Operator, Helm chart**

**Explicación:**
Calico se puede instalar en EKS mediante: 1) el complemento administrado de EKS (el método más sencillo para el modo de solo políticas), 2) Tigera Operator (recomendado para las funciones completas de Calico) o 3) Helm charts (configuración flexible). Cada método presenta diferentes ventajas y desventajas en cuanto a simplicidad frente a personalización.

</details>

3. ¿A partir de qué versión de EKS está disponible el Network Policy Controller nativo?
   - A) EKS 1.12
   - B) EKS 1.14
   - C) EKS 1.18
   - D) EKS 1.24

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) EKS 1.14**

**Explicación:**
EKS introdujo su Network Policy Controller nativo a partir de la versión 1.14. Este controlador proporciona compatibilidad básica con Kubernetes NetworkPolicy. Sin embargo, Calico ofrece funciones de políticas adicionales, como GlobalNetworkPolicy y niveles de políticas, que van más allá de las capacidades del controlador nativo.

</details>

4. ¿Cuál es una limitación clave de ejecutar Calico con EKS Fargate?
   - A) Fargate no admite ningún tipo de networking
   - B) Calico no puede aplicar políticas de red en los Pod de Fargate
   - C) Fargate solo admite IPv6
   - D) Calico requiere acceso root, que Fargate proporciona

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Calico no puede aplicar políticas de red en los Pod de Fargate**

**Explicación:**
Los Pod de Fargate se ejecutan en microVM aisladas administradas por AWS, y los usuarios no pueden instalar DaemonSets ni modificar el host subyacente. Dado que el agente Felix de Calico se ejecuta como un DaemonSet, no se puede desplegar en nodos de Fargate, lo que significa que la aplicación de políticas de red no está disponible para los Pod de Fargate.

</details>

5. ¿Qué es IRSA en el contexto de Calico en EKS?
   - A) Asignación de servicio de rutas internas
   - B) IAM Roles for Service Accounts: permite que los Pod asuman roles de AWS IAM
   - C) Asociación de seguridad de recursos de Ingress
   - D) Asignación de subred de rango de IP

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) IAM Roles for Service Accounts: permite que los Pod asuman roles de AWS IAM**

**Explicación:**
IRSA (IAM Roles for Service Accounts) permite que las cuentas de servicio de Kubernetes asuman roles de AWS IAM. Cuando los componentes de Calico necesitan acceder a las API de AWS (por ejemplo, para la integración con el proveedor cloud), IRSA proporciona acceso seguro y detallado sin incrustar credenciales en los Pod.

</details>

6. ¿En qué se diferencian los Security Groups y las políticas de red de Calico en cuanto al alcance?
   - A) Son funcionalmente idénticos
   - B) Los Security Groups operan en el nivel de VPC/ENI y las políticas de Calico en el nivel de Pod/container
   - C) Los Security Groups son solo para ingress y Calico solo para egress
   - D) Los Security Groups están obsoletos en favor de Calico

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Los Security Groups operan en el nivel de VPC/ENI y las políticas de Calico en el nivel de Pod/container**

**Explicación:**
Los AWS Security Groups operan en la capa de networking de VPC y controlan el tráfico hacia y desde las ENI (Elastic Network Interfaces). Las políticas de red de Calico operan en el nivel de Pod de Kubernetes con selectores basados en labels. Ambos se pueden usar conjuntamente para una defensa en profundidad: los SG proporcionan controles en el nivel de VPC y Calico proporciona políticas en el nivel de aplicación.

</details>

7. ¿Qué se debe tener en cuenta al actualizar clústeres de EKS que ejecutan Calico?
   - A) Calico debe desinstalarse antes de actualizar
   - B) Verificar la compatibilidad de la versión de Calico con la versión de EKS objetivo
   - C) Las actualizaciones de EKS actualizan Calico automáticamente
   - D) Calico solo admite versiones específicas de EKS que terminan en números pares

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Verificar la compatibilidad de la versión de Calico con la versión de EKS objetivo**

**Explicación:**
Al actualizar EKS, debes verificar que tu versión de Calico sea compatible con la versión de Kubernetes/EKS objetivo. Revisa la matriz de compatibilidad de Calico y actualiza Calico si es necesario antes o después de la actualización de EKS, siguiendo los procedimientos de actualización documentados.

</details>

8. ¿A qué debe configurarse el ajuste kubernetesProvider para las instalaciones de EKS?
   - A) kubernetesProvider: AWS
   - B) kubernetesProvider: EKS
   - C) kubernetesProvider: Amazon
   - D) kubernetesProvider: None (detectado automáticamente)

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) kubernetesProvider: EKS**

**Explicación:**
Al instalar Calico en EKS, `kubernetesProvider` debe establecerse en `EKS` en el recurso Installation. Esto indica a Calico que use configuraciones y optimizaciones específicas de EKS, lo que garantiza una integración adecuada con el servicio administrado de Kubernetes.

</details>

9. ¿Qué controla el ajuste cni.type en el recurso Installation de Calico para EKS?
   - A) La versión de la especificación de CNI que se debe usar
   - B) Si Calico gestiona CNI o delega en otro plugin de CNI
   - C) El tipo de cifrado de red
   - D) El modo de integración del runtime de container

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Si Calico gestiona CNI o delega en otro plugin de CNI**

**Explicación:**
El ajuste `cni.type` determina el comportamiento de CNI de Calico. Establecer `cni.type: AmazonVPC` indica a Calico que delegue el networking en VPC CNI mientras Calico gestiona únicamente las políticas. Establecer `cni.type: Calico` hace que Calico gestione tanto el networking como las políticas.

</details>

10. ¿Qué es el «modo solo políticas» en Calico en EKS?
    - A) Un modo en el que solo se aplican GlobalNetworkPolicies
    - B) Un modo en el que Calico gestiona las políticas de red, pero no el networking de los Pod
    - C) Un modo que deshabilita todas las políticas de egress
    - D) Un modo para la evaluación de políticas solo de auditoría

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Un modo en el que Calico gestiona las políticas de red, pero no el networking de los Pod**

**Explicación:**
El modo solo políticas es una configuración de despliegue de Calico en la que VPC CNI sigue gestionando la asignación y el enrutamiento de IP de los Pod, mientras que Calico es responsable únicamente de la aplicación de políticas de red. Este es el patrón de despliegue de Calico más habitual en EKS, ya que conserva las ventajas del networking nativo de VPC.

</details>
