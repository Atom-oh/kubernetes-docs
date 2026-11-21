# 07. Cuestionario de diseño de WAN y conectividad híbrida

> **Última actualización**: 19 de noviembre de 2026

Vuelve al [libro de trabajo](../../../networking/expert/07-wan-hybrid-connectivity.md).
Elige una respuesta por pregunta y explica qué regla del libro de trabajo la respalda.
Estos son ejercicios de razonamiento de diseño, no afirmaciones de que se haya establecido una conexión.

1. Un Transit Gateway recibe `10.10.0.0/16` tanto desde una conexión de puerta de enlace de Direct Connect como desde una conexión VPN BGP. En las rutas anunciadas por DX, las instalaciones locales anteponen AS_PATH tres veces. ¿Por dónde se dirige el tráfico de VPC a las instalaciones locales?
   - A) Por la VPN, porque su AS_PATH es más corto.
   - B) Por DX, porque para el mismo CIDR el orden de los tipos de conexión se aplica antes de cualquier comparación de AS_PATH, y las rutas propagadas por la puerta de enlace de DX tienen prioridad sobre las rutas propagadas por VPN.
   - C) Por ECMP entre ambas rutas.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Por DX, porque para el mismo CIDR el orden de los tipos de conexión se aplica antes de cualquier comparación de AS_PATH, y las rutas propagadas por la puerta de enlace de DX tienen prioridad sobre las rutas propagadas por VPN.**

**Explicación:** El TGW elige primero el prefijo más largo; si el CIDR es el mismo y las rutas provienen de tipos distintos, prefiere, en este orden: rutas estáticas, del sistema, de listas de prefijos, propagadas por VPC, propagadas por la puerta de enlace de DX, de Connect y de VPN. AS_PATH y MED se comparan solo dentro de un mismo tipo, y no se admite ECMP entre tipos de conexión distintos.

</details>

2. Mientras configuras una VPN de respaldo, añades una **ruta estática** `10.10.0.0/16` → conexión VPN a la tabla de rutas del TGW. La puerta de enlace de DX propaga la misma ruta. ¿Qué sucede en condiciones normales?
   - A) DX sigue siendo la ruta principal, porque DX siempre tiene prioridad sobre VPN.
   - B) El TGW alterna entre las dos rutas.
   - C) La ruta estática tiene prioridad sobre la ruta propagada, así que la VPN pasa a ser la ruta principal sin aviso.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) La ruta estática tiene prioridad sobre la ruta propagada, así que la VPN pasa a ser la ruta principal sin aviso.**

**Explicación:** Las rutas estáticas ocupan el primer lugar en el orden de evaluación del TGW, y una ruta propagada con el mismo destino ni siquiera aparece en la tabla. Configura la VPN de respaldo con BGP para que quede por debajo de la ruta propagada por la puerta de enlace de DX.

</details>

3. El prefijo permitido de la puerta de enlace de DX se resume como `10.0.0.0/8`, mientras que la VPN anuncia `10.20.0.0/16` desde la tabla de rutas del TGW. El router de las instalaciones locales asigna LOCAL_PREF 200 a las rutas aprendidas de DX y 100 a las rutas de VPN. ¿Por dónde se dirige el tráfico hacia `10.20.1.10`?
   - A) Por la VPN: primero coincide el prefijo más largo, `10.20.0.0/16`, y LOCAL_PREF solo compara rutas para el mismo prefijo.
   - B) Por DX, porque su LOCAL_PREF es más alto.
   - C) Ambas rutas descartan el tráfico.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A) Por la VPN: primero coincide el prefijo más largo, `10.20.0.0/16`, y LOCAL_PREF solo compara rutas para el mismo prefijo.**

**Explicación:** En una asociación de Transit Gateway, los prefijos permitidos se anuncian exactamente como se introdujeron, de modo que el router aprende `10.0.0.0/8` (DX) y `10.20.0.0/16` (VPN) como rutas distintas. El reenvío sigue la coincidencia con el prefijo más largo, y el tráfico se desvía hacia la VPN. Haz coincidir la longitud del prefijo permitido con la del lado de la VPN o resume las rutas aprendidas de la VPN de la misma manera.

</details>

4. Quieres que dos VIF de DX funcionen en modo activo/pasivo para el tráfico que vuelve de AWS a las instalaciones locales. ¿Cuál es la configuración correcta?
   - A) Un MED más bajo solo en la VIF principal.
   - B) `7224:7300` en los prefijos de la VIF principal y `7224:7100` en los prefijos de la VIF de respaldo, como comunidades estándar.
   - C) Comunidades extendidas de destino de ruta que indiquen la prioridad.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) `7224:7300` en los prefijos de la VIF principal y `7224:7100` en los prefijos de la VIF de respaldo, como comunidades estándar.**

**Explicación:** Para las VIF privadas y de tránsito, AWS compara el prefijo más largo, la comunidad de preferencia local, AS_PATH y, por último, MED; las comunidades se evalúan antes que AS_PATH. MED tiene la prioridad más baja y AWS no lo recomienda. Las comunidades extendidas no se evalúan para determinar la preferencia y pueden eliminarse.

</details>

5. ¿Qué afirmación sobre BFD en Direct Connect es correcta?
   - A) Se habilita automáticamente en el lado de AWS, así que funciona sin configurar el router.
   - B) Direct Connect no admite BFD, así que solo se aplica el tiempo de espera de BGP.
   - C) BFD asíncrono se habilita automáticamente en el lado de AWS, pero solo surte efecto cuando se configura en el router; el intervalo mínimo predeterminado es de 300 ms, con un multiplicador de 3.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) BFD asíncrono se habilita automáticamente en el lado de AWS, pero solo surte efecto cuando se configura en el router; el intervalo mínimo predeterminado es de 300 ms, con un multiplicador de 3.**

**Explicación:** Sin BFD, BGP solo interrumpe la sesión después de 90 segundos sin mensajes de mantenimiento. Por eso, en el escenario del ejercicio en el que «BFD no está configurado» no se cumple el objetivo de 5 segundos.

</details>

6. BFD con 300 ms × 3 detecta un fallo en unos 0,9 segundos. ¿Qué frase está justificada en un documento de diseño?
   - A) La detección tarda unos 0,9 segundos; la retirada y propagación de rutas, la programación de la FIB en ambos routers y el cambio en la dirección inversa son supuestos hasta que se midan.
   - B) La conmutación por error tarda 0,9 segundos.
   - C) Incluso con BFD, la ruta solo cambia después del tiempo de espera de BGP de 90 segundos.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A) La detección tarda unos 0,9 segundos; la retirada y propagación de rutas, la programación de la FIB en ambos routers y el cambio en la dirección inversa son supuestos hasta que se midan.**

**Explicación:** En RFC 5880, el tiempo de detección es el multiplicador por el intervalo negociado. La detección es solo una parte de la recuperación, y AWS no publica valores fijos para los pasos restantes. Cuando BFD interrumpe la sesión, BGP no espera a que venza el tiempo de espera.

</details>

7. ¿Qué afirmación sobre un LAG de Direct Connect es correcta?
   - A) Agrupar conexiones de dos ubicaciones de DX distintas en un LAG protege ante el fallo de una ubicación.
   - B) Agrupa conexiones dedicadas de igual ancho de banda en un mismo punto de conexión (hasta 4 por debajo de 100 Gbps y hasta 2 a 100 o 400 Gbps) y no admite MLAG; por tanto, añade capacidad, pero no redundancia de ubicación.
   - C) Las conexiones alojadas pueden formar parte de un LAG.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Agrupa conexiones dedicadas de igual ancho de banda en un mismo punto de conexión (hasta 4 por debajo de 100 Gbps y hasta 2 a 100 o 400 Gbps) y no admite MLAG; por tanto, añade capacidad, pero no redundancia de ubicación.**

**Explicación:** Todos los miembros de un LAG deben ser conexiones dedicadas que terminen en el mismo punto de conexión de Direct Connect. La redundancia de ubicación se consigue distribuyendo las conexiones entre distintas ubicaciones, como en los modelos de resiliencia Alta y Máxima del Resiliency Toolkit. Configurar el atributo de enlaces mínimos (0 de forma predeterminada) evita sobrecargar los miembros que sigan activos.

</details>

8. ¿Qué tiene de incorrecto un informe que dice «una conexión Site-to-Site VPN tiene dos túneles, así que ya hay redundancia»?
   - A) Nada; los dos túneles hacen redundante todo lo que llega hasta la puerta de enlace del cliente.
   - B) AWS envía tráfico por ambos túneles mediante ECMP, así que no hace falta configurar el enrutamiento asimétrico.
   - C) Los dos túneles solo hacen redundante el punto de conexión del lado de AWS entre zonas de disponibilidad; si se comparte una única puerta de enlace del cliente y un único circuito, siguen siendo puntos únicos de fallo.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Los dos túneles solo hacen redundante el punto de conexión del lado de AWS entre zonas de disponibilidad; si se comparte una única puerta de enlace del cliente y un único circuito, siguen siendo puntos únicos de fallo.**

**Explicación:** Cada túnel tiene una dirección IP pública única y termina en una zona de disponibilidad distinta. El tráfico de AWS a las instalaciones locales prefiere un solo túnel, por lo que la puerta de enlace del cliente debe permitir el enrutamiento asimétrico. Para obtener redundancia del lado del cliente, añade otra puerta de enlace del cliente y otra conexión VPN.

</details>

9. Una conexión TCP que funciona sobre DX con una MTU de VIF de tránsito de 8500 conmuta por error a una VPN (AES-GCM, NAT-T deshabilitado). ¿Qué diseño evita que desaparezcan los paquetes grandes?
   - A) Limita el MSS en el router al valor de la ruta de respaldo (1406 para esta combinación) o mantén la VIF en 1500 mientras la VPN sea la ruta de respaldo.
   - B) Déjalo como está; el TGW admite PMTUD en todas las conexiones.
   - C) Habilita tramas gigantes en la VPN.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A) Limita el MSS en el router al valor de la ruta de respaldo (1406 para esta combinación) o mantén la VIF en 1500 mientras la VPN sea la ruta de respaldo.**

**Explicación:** Site-to-Site VPN admite una MTU de hasta 1446 y un MSS de 1406, no admite tramas gigantes ni PMTUD. PMTUD del TGW se aplica únicamente al tráfico que entra por conexiones de VPC y Connect. En un diseño de conmutación por error, importa la MTU de la ruta de respaldo.

</details>

10. Un router de las instalaciones locales anuncia 150 prefijos IPv4 a través de una sesión BGP de una VIF de tránsito con la asignación de prefijos predeterminada. ¿Qué sucede?
   - A) AWS acepta los primeros 100 e ignora el resto.
   - B) Se supera la asignación (100 de forma predeterminada), así que la sesión BGP pasa al estado inactivo y se informa como DOWN.
   - C) AWS los resume automáticamente.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Se supera la asignación (100 de forma predeterminada), así que la sesión BGP pasa al estado inactivo y se informa como DOWN.**

**Explicación:** Una sesión BGP de una VIF privada o de tránsito acepta de forma predeterminada 100 rutas IPv4 y 100 rutas IPv6; los controles de prefijos permiten aumentar cada cantidad a 1.000. Superar el límite provoca una interrupción de la sesión; por eso, el ejercicio comienza comprobando la tabla de anuncios frente a las cuotas.

</details>

11. ¿Cómo debería aparecer la puerta de enlace de Direct Connect en un diagrama de topología?
   - A) Como un salto que reenvía paquetes entre la VIF y el Transit Gateway.
   - B) Como parte de la tabla de rutas del Transit Gateway.
   - C) Como un reflector de rutas BGP distribuido fuera de la ruta de datos, conectado únicamente mediante líneas de sesión.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Como un reflector de rutas BGP distribuido fuera de la ruta de datos, conectado únicamente mediante líneas de sesión.**

**Explicación:** AWS describe la puerta de enlace de DX como un conjunto distribuido de reflectores de rutas que opera fuera de la ruta del tráfico de datos, por lo que no es un punto único de fallo. Además, en la animación, el paquete solo permanece en la ubicación de DX y en el Transit Gateway.

</details>

12. ¿Cómo expresar con precisión «SD-WAN detecta los fallos rápidamente» en términos del plano de control y del plano de datos?
   - A) BFD detecta fallos de conexión en las conexiones de datos IPsec entre routers; la redundancia de los controladores es un aspecto de diseño independiente.
   - B) Las sesiones OMP de los controladores miden directamente la pérdida de paquetes en los túneles de datos.
   - C) MEF 70.2 establece los valores de los temporizadores BFD.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A) BFD detecta fallos de conexión en las conexiones de datos IPsec entre routers; la redundancia de los controladores es un aspecto de diseño independiente.**

**Explicación:** En Cisco Catalyst SD-WAN, los controladores orquestan el plano de control y el Validator gestiona la autenticación de dispositivos y las conexiones de control. Los datos fluyen a través de conexiones IPsec entre routers, y BFD se ejecuta automáticamente en ellas. MEF 70.2 define atributos de servicio como los túneles y las políticas.

</details>

Finalización: explica cada respuesta con una regla del libro de trabajo y adjunta la tabla de escenarios del ejercicio o etiqueta el trabajo como **revisión de diseño**.
