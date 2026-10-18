# 03. Cuestionario sobre EVPN de centros de datos

> **Última actualización**: 15 de septiembre de 2026

Vuelve al [cuaderno de trabajo](../../../networking/expert/03-datacenter-evpn.md).
Elige una respuesta y menciona el control positivo que permitiría distinguir una
prueba negativa válida de un laboratorio averiado.

1. La estructura de la red presenta una ruta de acceso bloqueada de forma inesperada. ¿Qué requisito previo se debería investigar antes de suponer que EVPN tiene la culpa?
   - A) Pertenencia a VLAN, estado real de STP y estado de los miembros de LAG cuando esas funciones estén implementadas.
   - B) Solo los temporizadores hold de BGP.
   - C) Si un único flujo usa todos los miembros de LACP a la vez.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A**

**Explicación:** La conexión del tenant y el reenvío local son requisitos previos para un overlay. El hashing de LACP no garantiza que un flujo use todos los miembros. Los pequeños laboratorios seleccionados no implementan LACP ni una topología STP redundante, por lo que no pueden demostrar que esas funciones se hayan probado.

</details>

2. En un paquete VXLAN que transporta tráfico de h1 a h2, ¿qué identifica normalmente el endpoint de encapsulación remoto?
   - A) La IP de destino externa debe ser la IP del tenant de h2.
   - B) La IP del VTEP remoto es el destino externo, mientras que el VNI identifica el segmento virtual.
   - C) El RD se coloca en el campo de destino IP externo.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B**

**Explicación:** Distingue el transporte externo del tráfico interno del tenant. Captura el par de VTEP, el VNI y las direcciones internas, y compáralos con la tabla de asignación. Un ping de administración nunca reemplaza estas pruebas de la ruta del tenant.

</details>

3. Dos anuncios tienen RDs distintos, pero incluyen un RT que importa la misma VRF. ¿Qué afirmación es correcta?
   - A) Los RDs distintos los obligan a pertenecer a VPN diferentes.
   - B) Se necesita el mismo RD para que la VRF los importe.
   - C) Los RD distinguen identidades de ruta; una política de importación/exportación RT coincidente puede ubicarlas en la misma VPN.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C**

**Explicación:** La identidad de la ruta y su pertenencia cumplen funciones distintas. La política RT controla la importación, mientras que el RD distingue rutas que, de otro modo, se solaparían. Aun así, verifica la ruta importada, FIB y el tráfico; un RT no es un firewall de paquetes ni una garantía de reenvío.

</details>

4. ¿Qué correspondencia entre tipo de ruta y función es correcta?
   - A) El tipo 2 transporta una dirección MAC y, opcionalmente, una IP; el tipo 3 proporciona información de participación en IMET; el tipo 5 transporta un prefijo IP.
   - B) Tipo 2 transporta solo una ruta OSPF de underlay; tipo 3 garantiza un servicio enrutado del tenant.
   - C) El tipo 5 debe aparecer en todos los laboratorios que solo usan bridging.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A**

**Explicación:** Relaciona cada tipo de ruta con el modelo de servicio. Genera tráfico desde los hosts antes de esperar que se aprendan sus direcciones; inspecciona el estado de replicación/FDB para L2 y sigue la importación de Type-5 para la etapa B. Un tipo que no requiera el modelo elegido se puede justificar como N/A, no marcarlo falsamente como aprobado.

</details>

5. ¿Qué distingue IRB simétrico de la mera presencia de BGP EVPN?
   - A) Cualquier sesión EVPN habilita automáticamente un gateway anycast.
   - B) IRB simétrico requiere enrutamiento del tenant en ambos extremos con un L3VNI entre ellos.
   - C) IRB simétrico significa que los dos VTEP usan RDs idénticos.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B**

**Explicación:** IRB se relaciona con el reenvío en los límites de bridging/enrutamiento, no solo con la familia de direcciones BGP. Verifica las asociaciones pertinentes de SVI/VRF/VNI. La etapa B solo usa L3 con enlaces de host enrutados; por sí sola no prueba IRB anycast de VLAN de acceso ni movilidad.

</details>

6. La topología base de la etapa A selecciona EOS/Cumulus, pero quieres usar la ruta de FRR del cuaderno. ¿Qué se requiere?
   - A) Usar cualquier contenedor antiguo de FRR; todos los proveedores tienen el mismo datapath.
   - B) Cambiar la etiqueta de imagen sin preparar interfaces de Linux bridge/VTEP.
   - C) Sobrescribir explícitamente s1 y s2 para FRR, usar la combinación admitida de clab/kernel, registrar versiones/digests y verificar los objetos de datapath generados.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C**

**Explicación:** El proveedor, la imagen, las plantillas de netlab y el kernel de la VM implementan conjuntamente el laboratorio. FRR aprende el estado de las interfaces de Linux en lugar de crear todas las interfaces. Un entorno restringido sin la compatibilidad de kernel necesaria está bloqueado, aunque se inicie el demonio BGP.

</details>

7. h1 no puede llegar a h3 en la etapa A, pero tampoco funciona ningún par de la misma VLAN. ¿Cómo se debe clasificar el resultado?
   - A) No es una prueba de aislamiento correcta; primero investiga los controles positivos fallidos.
   - B) PASS porque cualquier sonda fallida entre VLAN demuestra aislamiento.
   - C) PASS porque la sesión EVPN está establecida.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A**

**Explicación:** Un host inactivo o una estructura de red averiada pueden producir la misma sonda negativa. Exige que ambos pares previstos funcionen, que la conexión sea correcta y que se explique la ruta bloqueada. Las rutas o sondas faltantes no demuestran por sí solas el contrato de servicio/aislamiento solicitado.

</details>

8. ¿Por qué el experimento RT añade un RT de importación manual que no se usa antes de eliminar el RT original?
   - A) Para cambiar el RD sin que se note.
   - B) Para impedir que una lista manual vacía vuelva a un RT automático; aun así, hay que comprobar la lista efectiva.
   - C) Para apagar todos los peers EVPN.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B**

**Explicación:** El comportamiento automático del RT puede invalidar un experimento de eliminación ingenuo. Comprueba que la membresía original ya no sea efectiva y que ninguna ruta exportada coincida con el RT temporal. Para restaurar, añade el RT original y luego elimina solo la entrada temporal de la lista de importación de la VRF `red` en s1.

</details>

9. Después de reducir la MTU del underlay de s1, las sondas pequeñas funcionan y las grandes también funcionan, pero se ve fragmentación externa. ¿Qué debe indicar el informe?
   - A) No hubo impacto de MTU porque no se perdieron paquetes.
   - B) Hubo un agujero negro garantizado porque estaba establecido DF interno.
   - C) La fragmentación fue el efecto observado; DF interno no determina el comportamiento de DF externo.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C**

**Explicación:** Registra el tamaño de encapsulación, la fragmentación externa, los errores y los cambios de adyacencia. El modelo y la implementación determinan el efecto; un cuaderno de trabajo no debe inventar un resultado fijo de pérdida. Restaura el estado previo conocido de interfaz de 1600 bytes y vuelve a probar ambos tamaños y los controles de VRF.

</details>

10. ¿Qué pruebas respaldan la inyección y recuperación correctas de un fallo RT?
   - A) Durante el fallo, la ruta global permanece, fallan la importación y la sonda de `red`, y `blue` y el gateway local de h2 funcionan; después de restaurar, vuelven el conjunto original de RT, la ruta y la sonda de `red`.
   - B) Solo una tabla global vacía.
   - C) La inicialización repetida y la poda global terminan eliminando los errores.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A**

**Explicación:** Los controles funcionales distinguen un fallo de política de importación de una indisponibilidad general. Se requiere la restauración exacta del objeto nombrado. No se supone que la inicialización de VLAN/VRF de FRR sea idempotente, y la telemetría faltante o una limpieza amplia no demuestra que se haya recuperado.

</details>

Finalización: entrega la matriz de pruebas de L2, L3, RT y MTU con revisiones y resultados de restauración, o marca explícitamente el trabajo práctico como **no ejecutado**.
