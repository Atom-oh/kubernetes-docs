# Cuestionario sobre DNS y conectividad

> **Última actualización**: 15 de septiembre de 2026

Usa la [lección](../../../networking/beginner/04-dns-connectivity.md) para distinguir una observación de una inferencia. El laboratorio interno tiene un cliente `192.0.2.10/24` y un servidor `192.0.2.20/24`; el servidor no ejecuta ningún servicio DNS.

## Preguntas

1. `/etc/hosts` asigna `server.netlab.test` a `.20`. `getent ahostsv4` funciona, pero `dig @192.0.2.20` expira. ¿Qué interpretación corresponde?
   - A) Toda resolución de nombres está rota
   - B) Funciona la búsqueda local de NSS, mientras que el servidor consultado no proporciona el servicio DNS esperado
   - C) Hay que eliminar la ruta predeterminada de administración
   - D) Una entrada hosts crea automáticamente un listener DNS en el servidor

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Funciona la búsqueda local de NSS, mientras que el servidor consultado no proporciona el servicio DNS esperado**

**Explicación:** getent sigue las fuentes de servicio de nombres del sistema; dig envía una consulta DNS al servidor seleccionado. El laboratorio no incluye deliberadamente un listener DNS en `.20`. Un timeout significa que no hubo una respuesta utilizable dentro del límite, no que se recibiera una respuesta NXDOMAIN. Conserva la asignación hosts que funciona en vez de apuntar el DNS del sistema a `.20`.

</details>

2. En Ubuntu, `dig @127.0.0.53 server.netlab.test. A` devuelve la dirección de `/etc/hosts`. ¿Qué ocurrió?
   - A) Dig leyó directamente el nombre consultado de NSS
   - B) Un servidor autoritativo público aprendió la entrada hosts local
   - C) El cliente se convirtió en router
   - D) Dig consultó el stub de resolved, que puede responder con datos hosts locales

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: D) Dig consultó el stub de resolved, que puede responder con datos hosts locales**

**Explicación:** Dig por sí mismo no resuelve el nombre consultado mediante NSS. Sin embargo, systemd-resolved normalmente lee los datos de hosts y puede exponer el resultado mediante su stub DNS. Consultar un stub local y consultar un servidor upstream sin relación son experimentos distintos; inspecciona la configuración si ese comportamiento local está deshabilitado.

</details>

3. Una respuesta DNS contiene `status: NXDOMAIN`, mientras que otra consulta expira. ¿Cuál es la diferencia?
   - A) NXDOMAIN es una respuesta DNS negativa; un timeout significa que no llegó ninguna respuesta utilizable dentro del límite
   - B) Ambos demuestran que el nombre consultado no existe
   - C) NXDOMAIN demuestra que faltan todas las rutas IP
   - D) Un timeout demuestra que el servidor autoritativo eliminó el registro

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A) NXDOMAIN es una respuesta DNS negativa; un timeout significa que no llegó ninguna respuesta utilizable dentro del límite**

**Explicación:** Para NXDOMAIN, investiga la ortografía, la vista del resolver y los datos negativos en caché. Para un timeout, investiga la ruta, la accesibilidad del resolver y las políticas. Dig puede salir con código 0 tras recibir NXDOMAIN, así que lee el estado DNS y el contenido de la respuesta en vez de basarte solo en el código de salida del shell.

</details>

4. Un registro tiene TTL 300. Reduces su TTL autoritativo y borras la caché local de resolved. ¿Qué puedes concluir?
   - A) Todos los clientes ven el registro nuevo al instante
   - B) El registro puede atravesar exactamente 300 routers
   - C) El TTL de DNS es el tiempo de vida en caché; otras cachés pueden conservar datos anteriores y el TTL de IP no está relacionado
   - D) También se borró `/etc/hosts`

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) El TTL de DNS es el tiempo de vida en caché; otras cachés pueden conservar datos anteriores y el TTL de IP no está relacionado**

**Explicación:** Borrar la caché DNS de un servicio local no borra las cachés de aplicaciones ni upstream. Cambiar el TTL autoritativo no reescribe el tiempo de vida ya almacenado en caché. El TTL de IP limita los saltos de reenvío; sus unidades y mecanismo difieren del TTL de DNS, que se mide en segundos.

</details>

5. `ip route get 192.0.2.20` del cliente muestra `dev LAB_NIC src 192.0.2.10` y ningún `via`. ¿Qué se ha demostrado?
   - A) La aplicación HTTP del servidor está sana
   - B) El enrutamiento local selecciona la interfaz del laboratorio y el origen para un par conectado directamente; aún no se probó la accesibilidad
   - C) No existe ninguna ruta predeterminada en la máquina virtual
   - D) DNS seleccionó la MAC del par

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) El enrutamiento local selecciona la interfaz del laboratorio y el origen para un par conectado directamente; aún no se probó la accesibilidad**

**Explicación:** La búsqueda de ruta es local y no envía sondas. Un par `/24` conectado directamente no requiere un router de siguiente salto. Se puede conservar la ruta predeterminada de administración independiente. Comprueba por separado Neighbor Discovery, el comportamiento del par/ruta de retorno y las pruebas de aplicación.

</details>

6. El ping a la propia dirección del cliente `192.0.2.10` funciona, pero su entrada de vecino para `.20` pasa a `FAILED`. ¿Qué debes comprobar primero?
   - A) Instalar DNS público en la NIC del laboratorio
   - B) Tratar el ping a la propia máquina como prueba del cable virtual
   - C) Vaciar la tabla de rutas de administración
   - D) Las dos conexiones a la red interna, la dirección del par, la portadora y posibles conflictos de direcciones

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: D) Las dos conexiones a la red interna, la dirección del par, la portadora y posibles conflictos de direcciones**

**Explicación:** Una solicitud dirigida a una dirección local normalmente se gestiona localmente. No prueba el enlace virtual. Una entrada de vecino fallida sugiere que no se pudo resolver la MAC del siguiente salto, así que inspecciona las pruebas de enlace/dirección antes de investigar el DNS de la aplicación. En cambio, `STALE` no es por sí solo una asociación fallida.

</details>

7. Traceroute imprime `*`, pero una solicitud HTTP del cliente al mismo servidor funciona. ¿Qué afirmación está justificada?
   - A) La sonda no recibió una respuesta coincidente a tiempo; el reenvío normal de la aplicación aún puede funcionar
   - B) El salto con asterisco descarta todos los paquetes
   - C) Traceroute almacenó en caché el resultado HTTP
   - D) Todos los conmutadores virtuales deben aparecer como saltos IP

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A) La sonda no recibió una respuesta coincidente a tiempo; el reenvío normal de la aplicación aún puede funcionar**

**Explicación:** Los protocolos de sondeo y las políticas de respuestas de control difieren del tráfico de aplicaciones. El filtrado, los límites de frecuencia de respuesta y las rutas de retorno pueden ocultar respuestas. Un conmutador Ethernet no decrementa el TTL de IP como lo hace un router. Un asterisco por sí solo no mide la pérdida de paquetes de la aplicación.

</details>

8. `nc -z` o `ncat -z` se conecta al puerto 18080, pero no se ha enviado ninguna solicitud HTTP. ¿Qué se completó?
   - A) La verificación de la autoridad DNS
   - B) La autenticación HTTP y la representación de la página
   - C) El establecimiento de una conexión TCP a ese endpoint
   - D) La validación completa del certificado HTTPS

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) El establecimiento de una conexión TCP a ese endpoint**

**Explicación:** La sonda de conexión sin E/S no envía la solicitud HTTP prevista ni valida su respuesta. Continúa con curl para inspeccionar el estado, los encabezados y el cuerpo. Incluso una conexión TCP correcta no demuestra que el servicio use el protocolo esperado.

</details>

9. La solicitud del propio servidor devuelve 200, su listener está enlazado a `.20:18080` y la solicitud TCP del cliente expira. ¿Cuál es el mejor informe?
   - A) HTTP funciona completamente de extremo a extremo
   - B) El servicio local funciona; aún hay que investigar el enrutamiento remoto, las pruebas de vecino/ruta de retorno y la política del host
   - C) DNS debe estar roto aunque el cliente haya usado una dirección numérica
   - D) Deshabilitar globalmente el firewall del servidor

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) El servicio local funciona; aún hay que investigar el enrutamiento remoto, las pruebas de vecino/ruta de retorno y la política del host**

**Explicación:** Una solicitud del servidor a sí mismo no demuestra el acceso del cliente. El firewall es una posible causa, no una conclusión derivada únicamente de un timeout. Conserva las pruebas para el trabajo de políticas con ámbito definido del capítulo 06. No sustituyas una prueba remota bloqueada por un éxito local ni eludas el firewall para forzar el resultado.

</details>

10. Curl devuelve HTTP 404 para `/missing-page` y sale con código 0. ¿Qué significa?
   - A) No existía una conexión TCP
   - B) El nombre del servidor no tiene un registro DNS
   - C) Curl necesariamente ignoró la respuesta del servidor
   - D) HTTP devolvió una respuesta de recurso no encontrado; sin `--fail`, curl puede salir de todos modos correctamente

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: D) HTTP devolvió una respuesta de recurso no encontrado; sin `--fail`, curl puede salir de todos modos correctamente**

**Explicación:** El transporte funcionó lo suficiente para intercambiar HTTP, pero el recurso solicitado no estaba. Lee la línea de estado HTTP e investiga la ruta/aplicación. No cambies DNS para corregir este fallo deliberado a nivel de aplicación.

</details>

11. HTTP numérico funciona, HTTP con nombre falla y agregar `--resolve server.netlab.test:18080:192.0.2.20` hace que funcione la solicitud con nombre. ¿Cuál es el siguiente paso?
   - A) Inspeccionar la búsqueda normal de nombres con getent/NSS; la anulación solo afectó esa invocación de curl
   - B) Eliminar la ruta persistente a `.20`
   - C) Suponer que curl actualizó la zona DNS pública
   - D) Deshabilitar en todas partes la verificación TLS

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A) Inspeccionar la búsqueda normal de nombres con getent/NSS; la anulación solo afectó esa invocación de curl**

**Explicación:** La anulación conserva el nombre de host en la solicitud y proporciona a curl la dirección conocida. No modifica ningún archivo hosts ni registro DNS y no requiere reversión. Para HTTPS también importan el nombre de host, SNI y el comportamiento del certificado; este ejercicio HTTP no justifica omitir la validación del certificado.

</details>

12. ¿Qué afirmación sobre finalización/limpieza es correcta?
   - A) El DNS público debe funcionar para que se apruebe el laboratorio aislado
   - B) Eliminar todos los archivos en `/tmp` y restablecer por completo el archivo hosts
   - C) Detener el servidor propio, eliminar su archivo/directorio exactos y las entradas hosts marcadas, conservar las direcciones estáticas del laboratorio y tratar el DNS público como opcional
   - D) Cambiar la NIC de administración para usar DNS público, de modo que todas las observaciones coincidan

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Detener el servidor propio, eliminar su archivo/directorio exactos y las entradas hosts marcadas, conservar las direcciones estáticas del laboratorio y tratar el DNS público como opcional**

**Explicación:** La limpieza sigue la propiedad: el servidor en primer plano tiene un límite de cinco minutos, se registró su directorio temporal y se marcó el bloque hosts. Conserva las modificaciones no relacionadas y las direcciones del capítulo 03 para SSH. Las consultas públicas dependen del acceso y las políticas externas existentes, y no aportan pruebas sobre la ruta del par aislado.

</details>

---

[Volver a la lección](../../../networking/beginner/04-dns-connectivity.md) · [Siguiente lección: Acceso SSH](../../../networking/beginner/05-ssh-access.md)
