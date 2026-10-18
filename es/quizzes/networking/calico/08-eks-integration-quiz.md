# Cuestionario de integración de EKS

> **Documento relacionado**: [Integración de EKS](../../../networking/calico/08-eks-integration.md)
> **Última actualización**: 12 de septiembre de 2026

## Cuestionario

1. ¿Qué funciones corresponden a cada componente en la configuración habitual de esta guía, con VPC CNI + Calico en Linux sobre EC2?
   - A) VPC CNI aplica las políticas y Calico asigna las IP de VPC
   - B) VPC CNI gestiona la red de los Pods y Calico aplica las políticas
   - C) Ambos CNI configuran por separado todas las interfaces de cada Pod
   - D) Calico sustituye el plano de control de EKS administrado por AWS

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) VPC CNI gestiona la red de los Pods y Calico aplica las políticas**

**Explicación:**
VPC CNI gestiona las ENI, la asignación de direcciones IP de los Pods y su conectividad. Calico programa las reglas de políticas. Esta guía conserva iptables y kube-proxy; elegir un plano de datos alternativo requiere un plan independiente.

</details>

2. ¿Cuál de estas afirmaciones describe correctamente la instalación de Calico en EKS?
   - A) Habilitar la política de red de VPC CNI instala Calico
   - B) El Tigera Operator con versión fijada puede instalarse mediante manifiestos o su chart de Helm
   - C) Todos los clústeres de EKS tienen un complemento de AWS compatible llamado calico
   - D) Una reversión de Helm siempre revierte las migraciones de CRD y de datos de Calico

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) El Tigera Operator con versión fijada puede instalarse mediante manifiestos o su chart de Helm**

**Explicación:**
El chart de Helm instala Tigera Operator. La política de AWS VPC CNI es una implementación distinta. Comprueba el catálogo y el responsable de soporte actuales para los productos de Marketplace o de la comunidad, y utiliza un único responsable de la instalación.

</details>

3. ¿Qué afirmación coincide con las recomendaciones actuales de AWS para la política de red nativa?
   - A) EKS 1.14 introdujo todas las funciones actuales de políticas
   - B) VPC CNI 1.21 o posterior admite políticas estándar y administrativas con los requisitos documentados de plataforma y kernel
   - C) La política nativa solo admite políticas con alcance de espacio de nombres de forma permanente
   - D) La política nativa y Calico deben aplicar políticas a los mismos endpoints

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) VPC CNI 1.21 o posterior admite políticas estándar y administrativas con los requisitos documentados de plataforma y kernel**

**Explicación:**
La compatibilidad estándar comenzó con VPC CNI 1.14, no con EKS 1.14. Las recomendaciones actuales de AWS cubren NetworkPolicy y AWS ClusterNetworkPolicy con VPC CNI 1.21 o posterior, versiones compatibles de EKS y de la plataforma, y Linux kernel 5.10 o posterior. Estas API son distintas de las de Calico.

</details>

4. ¿Qué limitación tiene la política de red en EKS Fargate?
   - A) Fargate no tiene red
   - B) Ni la política del agente de nodo de Calico ni la política de red nativa de VPC CNI se aplican dentro de los Pods de Fargate
   - C) Todas las funciones de Calico funcionan si kubernetesProvider está configurado como EKS
   - D) Fargate solo admite IPv6

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Ni la política del agente de nodo de Calico ni la política de red nativa de VPC CNI se aplican dentro de los Pods de Fargate**

**Explicación:**
Fargate no ejecuta estos agentes de nodo. Los grupos de seguridad para Pods son un control independiente. Calico aún puede restringir el endpoint EC2 de una conexión con un endpoint de Fargate; eso no equivale a aplicar políticas dentro de Fargate.

</details>

5. ¿Cuándo se deben asignar permisos de IAM de AWS en esta configuración?
   - A) Cada calico-node necesita permisos amplios de EC2 Describe y CloudWatch
   - B) Asigna permisos al componente que realmente llama a las API de AWS; las políticas básicas de Calico usan RBAC de Kubernetes
   - C) El campo nodeMetadata de Installation crea un rol de IRSA
   - D) Crear una política de IAM la asocia automáticamente a todas las cuentas de servicio

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Asigna permisos al componente que realmente llama a las API de AWS; las políticas básicas de Calico usan RBAC de Kubernetes**

**Explicación:**
VPC CNI necesita sus propios permisos de AWS. Un exportador o una integración con servicios en la nube puede necesitar un rol aparte. Usa la configuración de IRSA o Pod Identity admitida por el componente responsable; Calico, cuando solo aplica políticas básicas, no necesita un rol amplio de AWS.

</details>

6. ¿Qué exige AWS para combinar grupos de seguridad para Pods con las políticas de Calico?
   - A) Solo POD_SECURITY_GROUP_ENFORCING_MODE=strict
   - B) VPC CNI 1.11 o posterior y POD_SECURITY_GROUP_ENFORCING_MODE=standard, además de los otros requisitos previos de la función
   - C) Basta con añadir una etiqueta a la instancia EC2
   - D) Los grupos de seguridad para Pods también funcionan en EKS Auto Mode

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) VPC CNI 1.11 o posterior y POD_SECURITY_GROUP_ENFORCING_MODE=standard, además de los otros requisitos previos de la función**

**Explicación:**
En modo strict, esos Pods no están sujetos a la aplicación de políticas de Calico. Comprueba qué instancias y branch ENI son compatibles y reemplaza los Pods afectados después de cambiar el modo. En modo standard, con SNAT externo normal, el tráfico que sale de la VPC usa los grupos de seguridad de los nodos.

</details>

7. ¿Cuál es el enfoque correcto para actualizar EKS y Calico?
   - A) Actualiza siempre Calico después de EKS, sin importar la compatibilidad
   - B) Elige una versión de Calico compatible durante la transición y revisa los requisitos de EKS, los nodos, los complementos y las CRD
   - C) EKS actualiza y revierte automáticamente todos los componentes de terceros
   - D) Aplicar una versión anterior del operador garantiza una reversión segura

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Elige una versión de Calico compatible durante la transición y revisa los requisitos de EKS, los nodos, los complementos y las CRD**

**Explicación:**
Comprueba la compatibilidad en ambos lados de la transición. EKS ofrece actualmente una ventana condicional de siete días para revertir a la versión menor anterior, pero Calico y los complementos de EKS no se revierten automáticamente. La recuperación aún requiere comprobar la compatibilidad y el estado de preparación.

</details>

8. ¿Qué valor de proveedor se usa en la Installation revisada?
   - A) AWS
   - B) EKS
   - C) AmazonEKS
   - D) Ninguno

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) EKS**

**Explicación:**
Usa `spec.kubernetesProvider: EKS`, o `installation.kubernetesProvider: EKS` en los valores de Helm. Esto selecciona la configuración del proveedor; no demuestra que todos los tipos de nodo, CNI, planos de datos o versiones sean compatibles.

</details>

9. ¿Qué tipo de CNI delega la red en Amazon VPC CNI?
   - A) Calico
   - B) AmazonVPC
   - C) AWSCNI
   - D) VPC

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) AmazonVPC**

**Explicación:**
Configura `spec.cni.type: AmazonVPC` en Installation. El modo de Calico que solo aplica políticas también requiere la anotación documentada de IP del Pod, RBAC y un único motor de políticas; `bgp: Disabled` por sí solo no selecciona este CNI.

</details>

10. ¿Por qué deben permanecer juntos el selector del backend y el puerto TCP en una misma asignación de destino?
   - A) YAML exige repetir todos los campos
   - B) Una clave de destino duplicada puede descartar el selector y permitir endpoints no previstos
   - C) El puerto implica automáticamente la etiqueta del Pod backend
   - D) Las claves duplicadas siempre producen un error de validación de Kubernetes

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Una clave de destino duplicada puede descartar el selector y permitir endpoints no previstos**

**Explicación:**
Algunos analizadores YAML conservan solo la última clave duplicada. Mantén juntos el selector y los puertos, rechaza las claves duplicadas durante la validación y prueba tanto el tráfico permitido como el denegado. Que un nodo esté Ready no demuestra que las políticas se apliquen correctamente.

</details>
