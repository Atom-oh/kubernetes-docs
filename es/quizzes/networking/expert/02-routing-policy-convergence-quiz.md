# 02. Cuestionario sobre políticas de enrutamiento y convergencia medida

> **Última actualización**: 15 de septiembre de 2026

Vuelve al [cuaderno de trabajo](../../../networking/expert/02-routing-policy-convergence.md).
Elige una respuesta por pregunta y explica qué observación la respaldaría.
Son ejercicios de razonamiento, no afirmaciones de que se haya ejecutado un laboratorio.

1. ¿Por qué el laboratorio BGP seleccionado también ejecuta OSPF dentro de AS65000?
   - A) OSPF reemplaza todas las decisiones de políticas de BGP.
   - B) OSPF proporciona conectividad interna, incluidos los loopbacks que usa iBGP.
   - C) OSPF distribuye LOCAL_PREF a los proveedores externos.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B**

**Explicación:** BGP distribuye información de destinos que contiene políticas; OSPF proporciona rutas internas en este diseño. Comprueba la ruta al next hop BGP real, además de la adyacencia OSPF. La adyacencia por sí sola no demuestra que exista el prefijo necesario.

</details>

2. Una ruta aprendida por iBGP aparece en la tabla BGP, pero no se puede resolver su NEXT_HOP. ¿Cuál es el mejor paso siguiente?
   - A) Comprueba la ruta a ese next hop, la política de next hop y la búsqueda del kernel.
   - B) Declara que el reenvío funciona porque la sesión está establecida.
   - C) Aumenta LOCAL_PREF hasta que se pueda alcanzar un next hop inaccesible.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A**

**Explicación:** La preferencia no crea conectividad. Identifica el NEXT_HOP real y resuélvelo mediante la tabla de enrutamiento hasta una interfaz o vecino. Después, compara la elegibilidad, la ruta seleccionada, FIB y las pruebas de tráfico específicas del origen.

</details>

3. c2 aprende una ruta elegible con LOCAL_PREF 200 a través de c1 y otra con 100 a través de x2. ¿Por qué c2 podría preferir c1 a pesar de un salto interno adicional?
   - A) BGP siempre elige la dirección IP más pequeña.
   - B) c1 propagó automáticamente Weight 200.
   - C) LOCAL_PREF expresa la política interna del AS y en este proceso de selección de FRR se considera antes que la longitud de AS_PATH.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C**

**Explicación:** La selección BGP no es simplemente un cálculo del número de saltos IGP. LOCAL_PREF se comunica internamente; Weight es local a una implementación o router. Verifica que ambas rutas sean elegibles y que ningún criterio o política anterior cambie la premisa.

</details>

4. ¿Qué resuelve un route reflector y qué se debe comprobar igualmente?
   - A) Crea todas las rutas que faltan de la red subyacente (underlay), así que los clientes no necesitan un IGP.
   - B) Reduce los requisitos de sesiones iBGP; los clientes siguen necesitando next hops utilizables y pruebas de reenvío.
   - C) Garantiza que todos los clientes vean todas las rutas alternativas.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B**

**Explicación:** La reflexión modifica las reglas de anuncio y usa ORIGINATOR_ID/CLUSTER_LIST para prevenir bucles. No repara la conectividad de next hops ni garantiza la visibilidad completa de rutas alternativas. Además, un reflector no tiene que transportar el tráfico de datos del inquilino.

</details>

5. El filtro de exportación propuesto permite exactamente `192.168.42.0/24`. ¿Qué ruta se debe rechazar según ese contrato?
   - A) `192.168.42.0/25`, porque la coincidencia exacta de prefijo/longitud no incluye automáticamente prefijos más específicos.
   - B) Ninguna; una lista de permitidos permite todas las rutas si no se deniegan explícitamente.
   - C) Solo las rutas con un MED elevado.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A**

**Explicación:** El contrato permite un prefijo y una longitud. `/25`, el `192.168.100.0/24` del proveedor y una ruta predeterminada quedan fuera. Inspecciona los anuncios reales por separado: un diseño de filtro por escrito no equivale a tener el filtro instalado.

</details>

6. ¿Qué afirmación sobre los atributos de política BGP se puede sostener?
   - A) Una comunidad adjunta siempre aplica el comportamiento previsto.
   - B) MED siempre se compara entre todos los AS vecinos.
   - C) Las comunidades necesitan una política que las interprete, y la comparación de MED depende de las reglas del receptor.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C**

**Explicación:** Las comunidades transportan etiquetas; la política receptora les da significado operativo. MED y el prepend de AS_PATH influyen en la selección solo dentro del proceso de decisión del receptor. No son instrucciones incondicionales para otro AS.

</details>

7. En este laboratorio de FRR/clab, ¿qué secuencia permite entrar correctamente en la CLI de enrutamiento?
   - A) Ejecuta `show ip route` directamente en el shell de la VM.
   - B) Ejecuta `netlab connect c1` desde el directorio del laboratorio y, luego, `vtysh` en el shell de Linux de c1.
   - C) Ejecuta `ip route get` en el prompt `c1(config-router)#`.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B**

**Explicación:** La conexión abre el shell de Linux del contenedor FRR. `vtysh` proporciona la CLI de FRR; `ip` y `ping` de Linux siguen siendo comandos del shell. La alternativa `netlab connect c1 --show ip route` desde la VM es válida y está verificada para un solo comando show de FRR.

</details>

8. Antes de aplicar el cambio de política del cuaderno de trabajo, c1 ya tiene una preferencia local explícita de 150. ¿Qué se debe hacer?
   - A) Detente y define el estado base previsto en vez de eliminar una política existente.
   - B) Supón 100 de todos modos porque es un valor predeterminado común.
   - C) Aplica 200, luego elimina el ajuste y considera que eso restaura exactamente la configuración.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A**

**Explicación:** La configuración inversa proporcionada supone que no hay ningún ajuste explícito y que la preferencia efectiva es 100. Eliminar un valor 150 preexistente no restauraría el estado original. El estado previo conocido forma parte de la autorización y la reproducibilidad, no es una anotación opcional.

</details>

9. Las sondas con marcas de tiempo no muestran pérdida con intervalos de 200 ms durante el apagado del peer. ¿Qué conclusión está justificada?
   - A) La convergencia tardó exactamente cero milisegundos.
   - B) No se vieron afectadas todas las aplicaciones ni todos los tamaños de paquete.
   - C) Este muestreo no detectó una interrupción; conserva las observaciones de ruta/FIB e informa el límite de la medición.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C**

**Explicación:** El muestreo puede pasar por alto una interrupción breve. El apagado administrativo también es distinto de un fallo silencioso y del vencimiento de temporizadores. Informa la intervención, los cambios de ruta/FIB observados, el intervalo de las sondas y el criterio de recuperación sostenida, en lugar de deducir un temporizador universal.

</details>

10. ¿Qué conjunto de resultados permite completar el experimento de fallo?
    - A) BGP vuelve a estar establecido, aunque no se guardó la salida de las sondas.
    - B) Se revierten los cambios exactos de peer y política, se recuperan las rutas/FIB/sondas de referencia y se registran los límites de medición.
    - C) Un borrado comodín y una limpieza de rutas para todo el host hacen que la salida parezca normal.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B**

**Explicación:** Primero restaura el peer nombrado de c1; luego, el ajuste introducido de preferencia local; finalmente, verifica el comportamiento original. La falta de telemetría no equivale al éxito. Conserva el clon y las revisiones bajo tu control e informa los fallos sin limpieza de alcance indiscriminado ni afirmar que se superó el validador upstream `c2=50`.

</details>

Finalización: explica cada respuesta y adjunta al cuaderno de trabajo una matriz de línea base/cambio/fallo/restauración, o marca el trabajo práctico como **no ejecutado**.
