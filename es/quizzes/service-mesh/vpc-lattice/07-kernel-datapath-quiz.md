# Cuestionario sobre el plano de datos del kernel

Este cuestionario evalúa tu comprensión de la capa del kernel que interviene en la interceptación de enlace local, las colisiones de iptables y el comportamiento de conntrack.

## Preguntas de opción múltiple

1. ¿Por qué se dice que el uso del rango de enlace local de Lattice «no sigue estrictamente la semántica de enlace local»?
   - A) Las direcciones son en realidad IP públicas
   - B) `169.254.0.0/16` es nominalmente no enrutable, pero el tráfico de Lattice debe llegar a un endpoint de ingreso dentro de la VPC, así que la infraestructura lo dirige allí
   - C) Solo se admite IPv4
   - D) DNS no resuelve ese rango

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) `169.254.0.0/16` es nominalmente no enrutable, pero el tráfico de Lattice debe llegar a un endpoint de ingreso dentro de la VPC, así que la infraestructura lo dirige allí**

**Explicación:**
Lattice no usa el rango de enlace local en su sentido original de «direcciones no enrutables»; **reutiliza el rango como una señal que significa «la infraestructura intercepta esto»**. El paquete realmente debe llegar a un endpoint de ingreso dentro de la VPC. Por la misma razón, IPv6 usa una ULA enrutable (`fd00:ec2:80::/64`) en lugar de una dirección de enlace local (`fe80::/10`); el alcance de enlace sería insuficiente.
</details>

2. ¿En qué punto exacto del kernel ocurre la colisión entre una malla sidecar y el tráfico de Lattice?
   - A) `POSTROUTING` en el espacio de nombres de red del nodo
   - B) El hook `OUTPUT` del espacio de nombres de red del pod: el tráfico de Lattice también es saliente, así que coincide con la regla REDIRECT
   - C) El búfer de anillo del controlador de la NIC
   - D) La tabla de enrutamiento del nodo

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) El hook `OUTPUT` del espacio de nombres de red del pod: el tráfico de Lattice también es saliente, así que coincide con la regla REDIRECT**

**Explicación:**
El contenedor init de la malla instala reglas de iptables dentro del espacio de nombres de red del pod que REDIRECT todo el tráfico saliente al puerto de Envoy. El tráfico dirigido a Lattice también es saliente, así que coincide con la regla; Envoy no encuentra `169.254.171.x` en su configuración de clúster y falla. La colisión ocurre dentro del pod porque las reglas de netfilter son específicas de cada espacio de nombres de red.
</details>

3. ¿Cómo se debe diagnosticar una solicitud interceptada?
   - A) Provoca un kernel panic
   - B) Inspecciona la política real de salida de Envoy, la ruta y el error; los destinos desconocidos pueden reenviarse o rechazarse
   - C) El pod entra inmediatamente en CrashLoopBackOff
   - D) kube-proxy registra una advertencia

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Inspecciona la política real de salida de Envoy, la ruta y el error; los destinos desconocidos pueden reenviarse o rechazarse**

**Explicación:**
Ver una solicitud en el registro del proxy demuestra que pasó por él, no que haya una única causa de fallo. Verifica el comportamiento elegido para omitir la interceptación o firmar, en lugar de suponer que fallará de inmediato.
</details>

4. Se registró el CIDR de excepción, pero el fallo sigue ocurriendo «a veces». ¿Cuál es la causa más probable?
   - A) Orden incorrecto de las reglas
   - B) Falta el rango IPv6 (`fd00:ec2:80::/64`): en una red de doble pila, el cliente que se conecta por IPv6 sigue siendo interceptado
   - C) No se reiniciaron los pods
   - D) Falta una regla de grupo de seguridad

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Falta el rango IPv6 (`fd00:ec2:80::/64`): en una red de doble pila, el cliente que se conecta por IPv6 sigue siendo interceptado**

**Explicación:**
Excluir solo IPv4 en un clúster de doble pila significa que el cliente que recibe un registro AAAA y se conecta por IPv6 sigue siendo interceptado. **El síntoma de «fallo ocasional» es característico**, porque depende del orden de las respuestas DNS y de la selección de direcciones del cliente. C también puede ser una causa real, pero entonces ese pod falla sistemáticamente y no «a veces».
</details>

5. ¿Por qué es obligatoria una regla de excepción basada en UID en el enfoque de proxy de egreso?
   - A) La política de seguridad exige que el proxy se ejecute con un UID sin privilegios
   - B) El paquete firmado que envía el proxy también se dirige al rango de Lattice; sin una excepción de UID, se redirige a sí mismo y entra en un bucle
   - C) Las firmas SigV4 incluyen información de UID
   - D) conntrack distingue las entradas por UID

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) El paquete firmado que envía el proxy también se dirige al rango de Lattice; sin una excepción de UID, se redirige a sí mismo y entra en un bucle**

**Explicación:**
El paquete firmado que emite el proxy también se dirige a `169.254.171.x`. Sin la excepción de UID, vuelve a coincidir con la regla REDIRECT y entra en un bucle. Por lo tanto, el proxy se ejecuta con un UID dedicado (101 en la implementación de referencia) y el tráfico que proviene de él hace `RETURN` mediante la coincidencia `owner` de netfilter (`-m owner --uid-owner`). **El `runAsUser` del contenedor del proxy y el UID de iptables deben coincidir** (es el eslabón más frágil al personalizar manifiestos).
</details>

6. ¿Por qué el enfoque de proxy de egreso carga más conntrack que el enfoque de biblioteca compartida?
   - A) El proxy mantiene las conexiones abiertas durante más tiempo
   - B) REDIRECT en el espacio de nombres de red del pod es DNAT y debe recordarse para deshacerlo; además, la conexión del proxy a Lattice añade entradas
   - C) El proxy también usa UDP
   - D) El proxy aumenta los tiempos de espera de conntrack

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) REDIRECT en el espacio de nombres de red del pod es DNAT y debe recordarse para deshacerlo; además, la conexión del proxy a Lattice añade entradas**

**Explicación:**
Un proxy de firma crea segmentos de conexión locales y upstream, mientras que el pool de conexiones y las opciones de espacio de nombres/NAT cambian el costo de seguimiento. Inspecciona las tablas del pod y del nodo, y los mapas eBPF, en vez de suponer un incremento fijo en la tabla del nodo.
</details>

7. ¿Qué demuestra la visibilidad de una captura de paquetes?
   - A) Agotamiento de conntrack
   - B) Interpreta la captura según emisor/receptor, dirección, interfaz y espacio de nombres; después, correlaciónala con otras pruebas
   - C) Descartes de qdisc
   - D) Fallo de autenticación de Lattice

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Interpreta la captura según emisor/receptor, dirección, interfaz y espacio de nombres; después, correlaciónala con otras pruebas**

**Explicación:**
Un paquete entrante rechazado antes de entregarse no aparece en el receptor. Un paquete saliente puede ser visible en el emisor antes de que un grupo de seguridad externo lo descarte. La falta de respuestas por sí sola no demuestra un fallo del grupo de seguridad.
</details>

8. ¿Qué indica el patrón «las llamadas a Lattice solo fallan en algunos nodos»?
   - A) Una configuración incorrecta del servicio de Lattice
   - B) Divergencia del estado de los nodos: diferencias de grupos de seguridad, versiones mixtas del kernel, distintos ajustes de conntrack, sincronización del reloj y si se reiniciaron los pods
   - C) Una configuración incorrecta de la política de autenticación
   - D) Retraso en la propagación de DNS

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Divergencia del estado de los nodos: diferencias de grupos de seguridad, versiones mixtas del kernel, distintos ajustes de conntrack, sincronización del reloj y si se reiniciaron los pods**

**Explicación:**
Un fallo total apunta a la configuración o la autenticación; **un fallo limitado a ciertos nodos apunta a una divergencia del estado de los nodos**. Entre las causas posibles están las diferencias de grupos de seguridad por grupo de nodos; kernels mixtos 6.1/6.18 debido a AMI `kernel-default`; distintas configuraciones de conntrack según el momento de inicio; la sincronización del reloj, que puede provocar una desviación de cinco minutos en `x-amz-date`; y cambios de anotaciones que no se aplicaron a los pods existentes. El patrón de «algunos nodos» reduce el alcance de la búsqueda.
</details>
