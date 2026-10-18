# Cuestionario sobre diseño de nube y CNI

[Cuaderno de trabajo](../../../networking/expert/05-cloud-cni-design.md)

1. DNS responde, pero falla la conexión TCP. ¿Cuál es el siguiente paso adecuado?

   - A) Declarar que el backend está en buen estado basándose solo en DNS
   - B) Inspeccionar el destino real, el puerto, las rutas, los controles y el listener
   - C) Abrir todos los grupos de seguridad
   - D) Concluir que no existe ningún recurso

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B**

**Explicación:** DNS aporta evidencia de resolución de nombres. TCP y HTTP requieren evidencia independiente de ruta, política y aplicación.

</details>

2. ¿Qué es AWS Load Balancer Controller?

   - A) El plano de datos por el que pasa cada solicitud HTTP
   - B) La puerta de enlace predeterminada de todos los Pods
   - C) Un reconciliador del plano de control que usa las API de AWS para administrar recursos de balanceadores de carga
   - D) La propia caché DNS

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C**

**Explicación:** Las solicitudes pasan por los balanceadores de carga y sus destinos reales. Investigue por separado el estado del controlador y la comunicación del plano de datos.

</details>

3. EndpointSlice figura como listo, pero el destino del balanceador de carga está en mal estado. ¿Cómo se debe interpretar?

   - A) Correlacionar el registro, el puerto, las condiciones de comprobación de estado y la ruta, porque los estados pueden diferir
   - B) La observación es imposible porque significan lo mismo
   - C) Cambiar el TTL de DNS siempre lo resuelve
   - D) Eliminar EndpointSlice

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A**

**Explicación:** El estado de disponibilidad y las comprobaciones de estado del balanceador tienen observadores y condiciones distintos. Correlacione cada dirección de endpoint con sus condiciones y el destino real.

</details>

4. ¿Qué más se necesita cuando existe un objeto NetworkPolicy?

   - A) Nada; su existencia demuestra que se aplica
   - B) Mover todos los Pods a hostNetwork
   - C) Derechos de administrador en todas las cuentas de AWS
   - D) Los Pods seleccionados, la dirección, una API compatible, la activación del motor y evidencia del flujo real

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: D**

**Explicación:** Una lista de objetos no garantiza la selección ni la aplicación de políticas. También pueden regir otras políticas administradas o CRD.

</details>

5. ¿Qué distinción sobre TGW es correcta?

   - A) Ambos son la misma regla de firewall
   - B) La asociación elige la tabla de búsqueda del attachment; la propagación identifica las tablas que aprenden rutas
   - C) La propagación siempre hace que el attachment use esa tabla
   - D) Un attachment se asocia con todas las tablas

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B**

**Explicación:** Un attachment se asocia con una tabla y puede propagarse a varias. Compruebe por separado la búsqueda y la ruta de retorno.

</details>

6. Una consulta devuelve AccessDenied y no se pueden obtener los endpoints. ¿Cuál es el resultado?

   - A) El tráfico denegado quedó validado correctamente
   - B) Asociar automáticamente una política de administrador
   - C) Evidencia no disponible; obtener acceso mínimo aprobado o evidencia proporcionada
   - D) No existe ningún backend

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C**

**Explicación:** Un fallo de permisos no indica el estado del recurso ni de la red. No convierta lo desconocido en permitido, denegado o ausente.

</details>

7. ¿Cómo se debe representar un Service ClusterIP en la ruta de paquetes?

   - A) Distinguir la selección lógica del reenvío real del proxy y sus destinos
   - B) Siempre como otro salto físico detrás del nodo
   - C) Como requisito para toda solicitud dirigida a un destino IP
   - D) Omitir la ruta de retorno

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A**

**Explicación:** El reenvío depende del tipo de destino, la implementación del proxy y la política. Convertir relaciones entre objetos en saltos obligatorios por la red distorsiona el diagnóstico.

</details>

8. Solo se revisó el diseño de enrutamiento híbrido, sin usar una cuenta. ¿Qué etiqueta de finalización corresponde?

   - A) Conmutación por error en vivo validada
   - B) Rendimiento garantizado
   - C) Todas las políticas se aplican
   - D) Revisión de diseño completada; observaciones en vivo sin verificar

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: D**

**Explicación:** El diseño, el análisis de evidencia proporcionada y los experimentos reales son niveles de evidencia distintos. Limite las conclusiones a lo que se hizo.

</details>
