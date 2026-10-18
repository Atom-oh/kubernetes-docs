# Cuestionario sobre conectividad entre VPC de distintas organizaciones

Distinga las mediciones reportadas de los requisitos de la plataforma de AWS.

## 1. ¿Qué se necesita para compartir un TGW con una cuenta que pertenece a una Organization distinta de la propietaria?

- A. Fusionar ambas Organizations
- B. Permitir principales externos en el recurso compartido y aceptar la invitación de RAM en la cuenta receptora
- C. Conectar las cuentas de administración mediante una VPN
- D. Obtener la aprobación mediante un ticket de soporte

<details>
<summary>Mostrar respuesta</summary>

B. El recurso compartido debe permitir la cuenta externa y el destinatario debe aceptar la invitación antes de usar los recursos compartidos. `CreateResourceShare` permite principales externos de forma predeterminada, por lo que no siempre se requiere la opción literal `--allow-external-principals`. Compruebe la configuración efectiva y las restricciones de IAM/uso compartido.

</details>

## 2. Si `AutoAcceptSharedAttachments` está deshabilitado, ¿qué se necesita para que un adjunto de VPC entre cuentas a un TGW compartido sea válido?

- A. No hace falta aceptación
- B. El propietario del TGW debe aceptar el adjunto compartido pendiente
- C. No se pueden crear adjuntos entre Organizations
- D. Siempre se activa después de 24 horas

<details>
<summary>Mostrar respuesta</summary>

B. La aceptación automática de adjuntos compartidos está deshabilitada de forma predeterminada. Aceptar el recurso compartido de RAM y aceptar el adjunto de VPC son pasos distintos. Si se habilita la aceptación automática, cambia el segundo flujo. El propietario del TGW controla sus tablas de rutas; la cuenta receptora sigue controlando sus propias rutas de VPC y ajustes de seguridad.

</details>

## 3. ¿Qué demuestra la comparación TCP_RR M3−M2 del informe?

- A. Cada salto de TGW siempre agrega la misma latencia unidireccional
- B. Las medianas de las rutas reportadas difieren en 0,619−0,048 = 0,571 ms
- C. Un SLA de latencia garantizado por AWS
- D. El throughput del entrenamiento de GPU

<details>
<summary>Mostrar respuesta</summary>

B. Es una diferencia observada entre medianas de ida y vuelta reportadas, no una medición pura de un componente ni una constante por salto. En esa campaña, la mediana de TCP_RR de la ruta con dos TGW fue menor que la de la ruta con un solo TGW. Para sacar conclusiones más amplias se necesitan muestras originales, incertidumbre y mediciones de la carga; esta revisión no reprodujo el benchmark.

</details>

## 4. ¿Qué se debe comprobar en el SG de destino para la ruta probada de un servicio HTTP de Lattice con asociación de VPC?

- A. Abrir todos los puertos de entrada y salida
- B. Permitir las listas de prefijos administradas correctas para la región y la familia de IP en los puertos reales del destino y de comprobación de estado
- C. Sustituir los grupos de seguridad por NACL
- D. Permitir solo TCP 443, sin importar el backend

<details>
<summary>Mostrar respuesta</summary>

B. El tráfico de Lattice puede llegar desde direcciones de sus listas de prefijos administradas, por lo que no basta con permitir solo el CIDR de la VPC cliente. El ejemplo histórico `169.254.171.0/24` no define universalmente todo el rango de direcciones. Use las listas documentadas y los puertos configurados; las rutas de endpoint/gateway de recursos tienen controles propios.

</details>

## 5. ¿Cuáles de los patrones comparados pueden exponer servicios entre VPC con CIDR superpuestos sin enrutar directamente entre esos rangos superpuestos?

- A. Peering directo de VPC
- B. Enrutamiento directo de TGW sin modificar
- C. Acceso a servicios de PrivateLink o VPC Lattice
- D. Ninguna arquitectura puede gestionar nunca la superposición

<details>
<summary>Mostrar respuesta</summary>

C. Estos mecanismos proporcionan acceso a servicios, no enrutamiento VPC bidireccional sin restricciones. El peering directo de VPC no puede conectar CIDR superpuestos, y los diseños enrutados requieren un plan de direcciones inequívoco. NAT y el rediseño de direcciones son otras opciones; por lo tanto, PrivateLink y Lattice no son las únicas arquitecturas posibles.

</details>

## 6. ¿Qué afirmación de enrutamiento es correcta para el peering directo entre TGW?

- A. El peering propaga automáticamente todas las rutas mediante BGP
- B. Configure explícitamente las rutas estáticas de peering y las rutas de VPC necesarias
- C. Solo importan las tablas de VPC
- D. La aceptación crea automáticamente todas las rutas necesarias

<details>
<summary>Mostrar respuesta</summary>

B. El adjunto de peering usa rutas estáticas, que se pueden administrar mediante automatización. El enrutamiento de TGW selecciona primero el prefijo más específico, y las rutas estáticas tienen prioridad sobre las propagadas para el mismo prefijo. Acepte la solicitud de peering pendiente desde la región aceptante mediante el ID de su adjunto; `NotFound` por sí solo no demuestra que los ID del solicitante y del aceptante tengan que ser diferentes.

</details>

[Volver a la guía](../../networking/05-cross-org-vpc-connectivity.md)
