# Cuestionario sobre la instalación y migración de SO para servidores bare metal

> **Última actualización**: 13 de septiembre de 2026

> **Documento relacionado**: [Guía](../../eks-hybrid-nodes/09-bare-metal-os-setup.md)

## Preguntas de opción múltiple

<span id="_1-what-is-a-key-benefit-of-running-eks-hybrid-nodes-on-bare-metal-servers"></span>

### 1. ¿Qué motivo puede justificar evaluar servidores bare metal para Hybrid Nodes?

- A) Convertir automáticamente todas las VM en contenedores
- B) Posible eliminación de la capa de hipervisor, evaluada frente al costo total y los requisitos de las cargas de trabajo
- C) Operar sin conectividad con AWS
- D) Cancelar automáticamente todas las licencias de software

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Posible eliminación de la capa de hipervisor, evaluada frente al costo total y los requisitos de las cargas de trabajo**

**Explicación:**

Eliminar un hipervisor puede cambiar los costos de licencias y la sobrecarga de ejecución, pero no garantiza un costo total menor ni un mejor rendimiento. La contenerización, la migración de datos, la disponibilidad, el soporte y las obligaciones contractuales requieren trabajo independiente. No deduzca ahorros de las antiguas estimaciones históricas de precios no verificadas que conserva la guía.

</details>

<span id="_2-what-are-the-essential-components-required-for-pxe-boot-infrastructure"></span>

### 2. ¿Qué componentes suelen ofrecer una configuración PXE heredada?

- A) Solo DNS y NFS
- B) Información de arranque DHCP/ProxyDHCP y un servidor de arranque TFTP
- C) FTP y SMTP
- D) Solo LDAP y Kerberos

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Información de arranque DHCP/ProxyDHCP y un servidor de arranque TFTP**

**Explicación:**

PXE heredado suele usar información de arranque DHCP y TFTP. HTTP puede entregar el contenido del instalador; UEFI HTTP y los diseños iPXE pueden usar otras rutas. `pxelinux.0` no es un cargador de arranque UEFI universal. Verifique la cadena de firmware/cargador y aísle el aprovisionamiento; no exponga códigos de activación ni claves privadas en un servidor compartido sin autenticación.

</details>

<span id="_3-which-correctly-pairs-ubuntu-s-automated-installation-method-with-rhel-s-automated-installation-method"></span>

### 3. ¿Qué combinación describe correctamente la instalación automatizada del SO?

- A) Ubuntu: Kickstart; RHEL: Autoinstall
- B) Ubuntu Server: YAML de Subiquity Autoinstall; RHEL: Kickstart
- C) Ubuntu: govc; RHEL: TOML
- D) Ambos requieren descargar nodeadm `latest` sin verificar dentro del instalador

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Ubuntu Server: YAML de Subiquity Autoinstall; RHEL: Kickstart**

**Explicación:**

Cloud-init puede entregar la configuración Autoinstall de Ubuntu. RHEL usa Kickstart. Valide la versión del instalador elegida y los ajustes de almacenamiento/red específicos del host. Un analizador YAML o `ksvalidator` no demuestra que sea seguro borrar el disco previsto ni que el host instalado pueda autenticarse.

</details>

<span id="_4-according-to-the-os-infrastructure-support-matrix-what-is-bottlerocket-s-supported-environment"></span>

### 4. Según la guía de AWS revisada, ¿qué implementación de Bottlerocket es compatible con EKS Hybrid Nodes?

- A) Cualquier variante bare metal
- B) Todos los hipervisores y arquitecturas
- C) Variantes compatibles de VMware >=1.37.0 en x86_64
- D) Solo EC2

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Variantes compatibles de VMware >=1.37.0 en x86_64**

**Explicación:**

Este es el límite de compatibilidad de EKS Hybrid, no una afirmación sobre todas las variantes de productos Bottlerocket. Para Hybrid en bare metal, evalúe hosts Ubuntu/RHEL compatibles. AL2023 también es una opción de invitado virtualizado local, no la ruta genérica compatible con bare metal. Compruebe por separado la disponibilidad de la variante de Kubernetes y los requisitos actuales del ciclo de vida.

</details>

<span id="_5-what-configuration-tool-and-format-does-bottlerocket-use-differently-from-other-operating-systems"></span>

### 5. ¿Cómo deben distinguirse los ajustes de Bottlerocket de govc?

- A) govc es el analizador TOML de Bottlerocket
- B) Bottlerocket usa el mismo YAML de nodeadm que Ubuntu
- C) Bottlerocket usa entradas de ajustes/arranque; govc administra el ciclo de vida de VM de VMware y la entrega de user-data
- D) `settings.hybrid.ssm` es un espacio de nombres de ajustes estándar compatible

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Bottlerocket usa entradas de ajustes/arranque; govc administra el ciclo de vida de VM de VMware y la entrega de user-data**

**Explicación:**

Use el proceso de ajustes/arranque de Bottlerocket correspondiente a la versión y descrito en la guía. Los antiguos ejemplos `settings.hybrid.*` no eran válidos. govc puede clonar/configurar/encender VM, pero no analiza los ajustes del SO. Proteja guestinfo y user-data; la codificación base64 no cifra las credenciales.

</details>

<span id="_6-when-selecting-a-credential-provider-for-an-environment-without-pki-infrastructure-and-with-internet-connectivity-which-option-is-recommended"></span>

### 6. ¿Qué afirmación sobre los proveedores de credenciales y la conectividad de Hybrid es correcta?

- A) IAM Roles Anywhere funciona indefinidamente sin conexión con AWS
- B) Ambos proveedores necesitan las API de AWS requeridas; la conectividad privada puede evitar el acceso a Internet público
- C) SSM siempre requiere acceso directo a Internet público
- D) Una cuenta de servicio de Kubernetes reemplaza al proveedor de credenciales de host de Hybrid

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Ambos proveedores necesitan las API de AWS requeridas; la conectividad privada puede evitar el acceso a Internet público**

**Explicación:**

SSM puede reducir el trabajo de administración de certificados si no hay una PKI administrada. IAM Roles Anywhere usa identidad X.509, pero aun así llama a AWS CreateSession para obtener credenciales temporales. Ambos diseños necesitan las rutas compatibles a las API/endpoints privados, el ciclo de vida de identidad y la autorización de EKS. Un entorno completamente desconectado/DDIL no es un modelo operativo compatible con EKS Hybrid.

</details>

<span id="_7-what-option-must-be-used-when-installing-containerd-with-nodeadm-on-rhel"></span>

### 7. ¿Qué opciones documentadas ofrece nodeadm para el origen de containerd en RHEL?

- A) `distro` es la única opción compatible
- B) `docker`, o `none` si containerd se instala y administra por separado
- C) `eks`, independientemente del SO
- D) `latest`, sin comprobar la compatibilidad

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) `docker`, o `none` si containerd se instala y administra por separado**

**Explicación:**

RHEL no admite el origen `distro` de nodeadm. `docker` selecciona el paquete de containerd distribuido con Docker que sea compatible; `none` omite la instalación y requiere un runtime administrado por separado antes de ejecutar `init`. Afirmar que toda instalación RHEL debe usar `docker` omite esta alternativa compatible. AL2023 tiene una restricción de origen distinta.

</details>

<span id="_8-what-is-the-correct-order-of-phases-when-migrating-from-vmware-to-bare-metal-eks-hybrid-nodes"></span>

### 8. ¿Qué secuencia de migración conserva una ruta de recuperación?

- A) Desmantelar primero el origen
- B) Cancelar las licencias antes del piloto
- C) Preparar un destino paralelo, migrar y probar las cargas de trabajo y la red, aceptar los datos y la operación, y desmantelar el origen después del período de reversión
- D) Copiar los discos de VM a contenedores y borrar inmediatamente el origen

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Preparar un destino paralelo, migrar y probar las cargas de trabajo y la red, aceptar los datos y la operación, y desmantelar el origen después del período de reversión**

**Explicación:**

Inventaríe las dependencias, planifique copias de seguridad y restauraciones, y conserve capacidad para revertir. Pruebe la coherencia de los datos, TLS/DNS, las políticas de acceso y el comportamiento real de las cargas de trabajo antes de cambiar el tráfico. Ni contenerizar las VM ni instalar únicamente un controlador CSI migra el estado. El desmantelamiento y los cambios de licencia requieren las decisiones acordadas de aceptación/retención.

</details>

<span id="_9-what-does-openshift-s-route-concept-map-to-in-eks-hybrid-nodes"></span>

### 9. ¿Cómo se debe migrar una Route de OpenShift?

- A) Cambiarle el nombre a Service sin hacer otros cambios
- B) Diseñar una correspondencia con Ingress/Gateway API y verificar el comportamiento TLS y de enrutamiento del controlador elegido
- C) Reemplazar cada Route por NetworkPolicy
- D) Copiar sus campos sin cambios a un Gateway

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Diseñar una correspondencia con Ingress/Gateway API y verificar el comportamiento TLS y de enrutamiento del controlador elegido**

**Explicación:**

Ingress/Gateway API son interfaces de enrutamiento posibles, no equivalentes automáticos. Preserve, según corresponda, la terminación/reencriptación/paso directo, los pesos y las anotaciones. La misma precaución aplica a SCC frente a PSS/PSA, la entrega OLM, los disparadores de ImageStream y los hooks de DeploymentConfig: ECR/Helm/Deployment no reproducen automáticamente todos los comportamientos de OpenShift.

</details>

<span id="_10-what-is-the-solution-when-pods-won-t-terminate-on-ubuntu-24-04-due-to-containerd-issues"></span>

### 10. ¿Qué respuesta es adecuada ante el problema documentado de terminación de contenedores/AppArmor en Ubuntu 24.04?

- A) Eliminar todos los perfiles AppArmor desconocidos de todos los hosts
- B) Verificar el problema real del paquete/perfil, aplicar la corrección compatible y planificar un reinicio cuando la transición lo requiera
- C) Deshabilitar todos los mecanismos de seguridad
- D) Suponer que todos los Pods atascados se arreglan instalando exactamente containerd 1.7.19

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Verificar el problema real del paquete/perfil, aplicar la corrección compatible y planificar un reinicio cuando la transición lo requiera**

**Explicación:**

El bug 2065423 tiene correcciones publicadas y describe un reinicio para la transición afectada del paquete/perfil. Compruebe el estado del paquete/parche del proveedor y los registros reales de denegación de señal. `aa-remove-unknown` elimina los perfiles cargados que no están en `/etc/apparmor.d`; no es un editor específico. Realice tareas controladas de drenado/reinicio y comprobación de cargas de trabajo; no convierta todo cambio de AppArmor en una regla universal de reinicio.

</details>

<span id="_11-which-cost-model-matches-the-reviewed-eks-hybrid-pricing"></span>

### 11. ¿Qué modelo de costos coincide con los precios revisados de EKS Hybrid?

- A) Una tarifa plana universal de 0,01 USD por vCPU-hora que incluye todos los servicios
- B) Tramos marginales mensuales según las vCPU-horas declaradas, además de los costos del clúster y otros cargos
- C) Se facturan solo las CPU solicitadas por Pods en ejecución
- D) No se cobra por los nodos cuando las cargas de trabajo están inactivas

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Tramos marginales mensuales según las vCPU-horas declaradas, además de los costos del clúster y otros cargos**

**Explicación:**

Las primeras 576 000 vCPU-horas mensuales cuestan 0,020 USD/vCPU-hora; a continuación se aplican los tramos marginales publicados. La agregación es regional dentro de una cuenta o del ámbito de facturación consolidada de Organizations. Incluya las vCPU declaradas, la duración de cada mes, el nivel de soporte del clúster y los demás servicios. El antiguo cálculo de 2803,20 USD por nodo/año se conserva como una suposición obsoleta no verificada, no como TCO actual.

</details>

<span id="_12-what-does-choosing-cilium-bgp-imply-when-replacing-nsx-t-functions"></span>

### 12. ¿Qué implica elegir Cilium BGP al reemplazar funciones de NSX-T?

- A) Todas las funciones de NSX-T se reproducen automáticamente
- B) BGP intercambia rutas; los requisitos de overlay, firewall, balanceo de carga y políticas deben asignarse por separado
- C) No hace falta probar las rutas de retorno
- D) Todas las sesiones existentes se conservan sin cambios

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) BGP intercambia rutas; los requisitos de overlay, firewall, balanceo de carga y políticas deben asignarse por separado**

**Explicación:**

Los anuncios BGP no proporcionan toda la plataforma NSX. Inventaríe por separado el comportamiento de rutas, overlay, seguridad y balanceo de carga; después pruebe las direcciones de destino, las rutas de retorno, TLS/DNS y las conexiones existentes/nuevas. Seleccione un patrón compatible de CNI mixto y conserve la opción de reversión; no se afirma que exista un reemplazo universal uno a uno.

</details>
