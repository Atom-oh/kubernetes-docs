# Cuestionario de Amazon VPC CNI

Revisado el 11 de septiembre de 2026 según la [guía de VPC CNI](../../networking/01-vpc-cni.md) y sus referencias primarias.

## 1. ¿Qué hace IPAMD en los nodos Linux EC2 estándar de EKS?

- A. Administra todos los ajustes DNS de las aplicaciones de los Pods
- B. Mantiene los grupos normales de asignación de ENI e IP para la red de los Pods
- C. Sustituye al controlador de políticas de red
- D. Cifra todo el tráfico entre nodos

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Mantiene los grupos normales de asignación de ENI e IP para la red de los Pods**

El entorno de ejecución del contenedor invoca el binario CNI, que solicita direcciones y configura el entorno de red del Pod. IPAMD mantiene los grupos de direcciones pertinentes. Las rutas administradas para Windows, Fargate y Auto Mode son diferentes.

</details>

## 2. ¿Cuál es la diferencia de asignación IPv4 entre los modos de IP secundaria y de prefijos?

- A. Solo el modo de IP secundaria admite IPv6
- B. El modo de IP secundaria asigna direcciones individuales; el modo de prefijos IPv4 asigna bloques /28 con 16 direcciones
- C. El modo de prefijos elimina los límites de Pods de kubelet
- D. El modo de prefijos crea espacio libre en una subred agotada

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. El modo de IP secundaria asigna direcciones individuales; el modo de prefijos IPv4 asigna bloques /28 con 16 direcciones**

El modo de prefijos requiere hardware compatible y bloques contiguos. La asignación sigue consumiendo espacio de subred, y los objetivos de reserva pueden dejar direcciones sin usar. IPv6 usa prefijos /80; EKS no ofrece Pods y Services de doble pila.

</details>

## 3. ¿Cómo llega a 29 el cálculo heredado de arranque de IPv4 secundaria para m5.large?

- A. Kubernetes siempre limita todos los nodos a 29
- B. 3 × (10 − 1) + 2 = 29
- C. 3 × 10 − 3 = 29
- D. 29 es el tamaño de todas las subredes

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. 3 × (10 − 1) + 2 = 29**

Hay tres ENI con diez espacios IPv4 cada una. Al quitar el espacio primario de cada ENI quedan 27 direcciones secundarias ordinarias; la fórmula histórica suma dos Pods de sistema que usan la red del host. No es un límite universal de capacidad vigente: los prefijos, SGPP, los límites de kubelet y los recursos cambian la interpretación.

</details>

## 4. ¿Qué especifica `WARM_IP_TARGET`?

- A. La cantidad máxima de Pods
- B. La cantidad objetivo de direcciones libres disponibles para asignaciones ordinarias
- C. La cuota de direcciones de todo el clúster
- D. El TTL de una dirección

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. La cantidad objetivo de direcciones libres disponibles para asignaciones ordinarias**

`MINIMUM_IP_TARGET` establece el mínimo de direcciones asignadas en total. Estos objetivos IP prevalecen sobre la estrategia de reserva de ENI o prefijos; la asignación de tamaño de prefijo sigue aplicándose. Elige los valores según la demanda y rotación medidas, el espacio de direcciones y el comportamiento de la API.

</details>

## 5. ¿Qué afirmación sobre la política de red nativa de EKS es correcta?

- A. VPC CNI ejecuta Calico internamente
- B. La política estándar basada en eBPF se introdujo en 1.14, pero siguen aplicándose las condiciones actuales de plataforma, versión y habilitación
- C. Se aplica automáticamente a Windows y Fargate
- D. Habilitarla garantiza la aplicación fiable a todos los Pods independientes

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. La política estándar basada en eBPF se introdujo en 1.14, pero siguen aplicándose las condiciones actuales de plataforma, versión y habilitación**

La configuración 1.23 revisada usa el controlador de políticas configurado y `aws-eks-nodeagent`. La guía actual de EKS incluye Linux EC2, Pods administrados por el controlador y condiciones de Service y puerto de contenedor. El modo estándar de inicio permite el tráfico mientras se resuelven las reglas; el inicio estricto es una decisión aparte e intencional.

</details>

## 6. ¿Qué ofrece la red personalizada con ENIConfig?

- A. Sustituir el servidor DNS
- B. Asignar direcciones de Pods desde subredes o grupos de seguridad seleccionados, distintos de la configuración predeterminada del nodo
- C. Migrar automáticamente los Pods existentes después de agregar un CIDR
- D. Eliminar automáticamente las rutas que se superponen

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Asignar direcciones de Pods desde subredes o grupos de seguridad seleccionados, distintos de la configuración predeterminada del nodo**

Configura recursos reales de la misma zona de disponibilidad, habilita la red personalizada y selecciona ENIConfig mediante la etiqueta o anotación prevista del nodo. Una anotación explícita prevalece sobre la etiqueta. Crear una subred o un CIDR nuevo no mueve los Pods existentes ni proporciona por sí mismo todas las rutas y permisos necesarios.

</details>

## 7. ¿Cómo funcionan las interfaces trunk y branch para SGPP en los nodos EC2 compatibles?

- A. La trunk siempre es la interfaz eth0 principal
- B. El controlador adjunta una ENI trunk adicional y asocia interfaces branch usadas por los Pods seleccionados
- C. Los dos nombres representan IPv4 e IPv6, respectivamente
- D. La delegación de prefijos multiplica por 16 el límite de Pods branch

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. El controlador adjunta una ENI trunk adicional y asocia interfaces branch usadas por los Pods seleccionados**

La trunk es una interfaz adicional, no la ENI principal. Se requieren tipos de instancia compatibles, el controlador y sus permisos de IAM, y reglas reales de grupos de seguridad. Fargate sigue una ruta administrada distinta. SGPP no se admite en Windows ni Auto Mode; la guía del servicio de EKS documenta compatibilidad con IPv6 bajo sus condiciones.

</details>

## 8. ¿Cuál es una respuesta predeterminada inadecuada ante el agotamiento de direcciones IP?

- A. Revisar que haya espacio contiguo para prefijos y hardware compatible antes de considerar la delegación de prefijos
- B. Planificar CIDR o subredes adicionales y la migración de las cargas de trabajo si falta capacidad
- C. Cambiar todas las cargas de trabajo a `hostNetwork` para evitar la asignación ordinaria de direcciones de Pods
- D. Considerar la red personalizada y ajustar los objetivos de reserva según mediciones

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C. Cambiar todas las cargas de trabajo a `hostNetwork` para evitar la asignación ordinaria de direcciones de Pods**

Cambiar todas las cargas de trabajo a `hostNetwork` modifica el aislamiento y el comportamiento de los puertos; no es una solución general de capacidad. Diagnostica por separado el agotamiento de direcciones, la fragmentación de prefijos, los límites de ENI, la capacidad de kubelet y los errores de API. La delegación de prefijos no puede crear direcciones de subred que no existen.

</details>
