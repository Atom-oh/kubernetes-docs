# Cuestionario de conectividad de VPC entre organizaciones

Este cuestionario evalúa tu comprensión de las cinco opciones para conectar VPC entre diferentes AWS Organizations.

## Preguntas de opción múltiple

1. ¿Qué se requiere para compartir un Transit Gateway con una cuenta en una Organization diferente?
   - A) Fusionar las dos Organizations en una sola
   - B) La opción `--allow-external-principals` y la aceptación de la invitación por parte del destinatario
   - C) Una conexión VPN entre las cuentas de administración de ambas Organizations
   - D) Aprobación manual mediante un ticket de AWS Support

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) La opción `--allow-external-principals` y la aceptación de la invitación por parte del destinatario**

**Explicación:**
Compartir recursos con una cuenta fuera de tu Organization mediante AWS RAM requiere `--allow-external-principals` en el recurso compartido, y el recurso permanece invisible hasta que la cuenta destinataria ejecute `accept-resource-share-invitation`. A diferencia del uso compartido automático basado en OU dentro de una Organization, el uso compartido entre organizaciones impone una selección explícita por ID de cuenta y una aceptación explícita.
</details>

2. ¿Qué ocurre cuando una cuenta de otra Organization crea un adjunto de VPC a un TGW compartido?
   - A) Se vuelve disponible de inmediato
   - B) Permanece en pendingAcceptance hasta que la cuenta propietaria del TGW lo acepta
   - C) La solicitud se rechaza y no se puede crear ningún adjunto
   - D) Se activa automáticamente después de 24 horas

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Permanece en pendingAcceptance hasta que la cuenta propietaria del TGW lo acepta**

**Explicación:**
Con la aceptación automática deshabilitada (el valor predeterminado), el adjunto de una cuenta externa permanece en `pendingAcceptance` hasta que el propietario del TGW ejecute `accept-transit-gateway-vpc-attachment`. Aquí es donde el modelo de que «el propietario del TGW controla centralmente la red» se aplica en el nivel de API. La cuenta que recibe el recurso compartido solo puede crear adjuntos; no puede modificar las tablas de rutas.
</details>

3. Según mediciones en vivo dentro de la misma AZ, ¿cuánta latencia agrega cada salto de Transit Gateway (p50)?
   - A) Aproximadamente 0.02 ms; efectivamente cero
   - B) Aproximadamente 0.4–0.6 ms; menos de un milisegundo
   - C) Aproximadamente 3–5 ms
   - D) 10 ms o más

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Aproximadamente 0.4–0.6 ms; menos de un milisegundo**

**Explicación:**
Medido con c7g.large, un respondedor EC2 simple y TCP_RR persistente (1,500 muestras/ruta), un salto de TGW tuvo un coste de +0.571 ms (TCP_RR) / +0.410 ms (ICMP). Como referencia, el coste de VPC Peering fue cero dentro de los límites de medición (igual que la línea base de la misma VPC), y un salto de NLB (+0.79 ms) en realidad cuesta más que un salto de TGW. Las mediciones que usan instancias ampliables o cadenas de proxy de varias etapas ocultan esta señal de menos de un milisegundo en el ruido, por lo que el diseño de la medición es importante.
</details>

4. ¿Cuál es el error común en la configuración del Security Group de una instancia de destino de VPC Lattice?
   - A) Deben abrirse todas las reglas de salida
   - B) El plano de datos de Lattice llega desde link-local (169.254.171.0/24), por lo que se debe permitir la lista de prefijos administrada
   - C) Se deben usar NACL en lugar de SG
   - D) Solo se debe permitir el puerto 443

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) El plano de datos de Lattice llega desde link-local (169.254.171.0/24), por lo que se debe permitir la lista de prefijos administrada**

**Explicación:**
El tráfico de VPC Lattice (incluidas las comprobaciones de estado) llega desde el rango link-local 169.254.171.0/24, no desde el CIDR de la VPC. Si el SG de destino solo permite el CIDR de la VPC, cada comprobación de estado informa UNHEALTHY. La solución es agregar la lista de prefijos administrada `com.amazonaws.<region>.vpc-lattice` a las reglas de entrada del SG.
</details>

5. ¿Qué opciones pueden conectar VPC en dos Organizations cuyos CIDR de IP se superponen?
   - A) VPC Peering y TGW Peering
   - B) TGW RAM Sharing
   - C) PrivateLink y VPC Lattice
   - D) Ninguna de las opciones puede hacerlo

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: C) PrivateLink y VPC Lattice**

**Explicación:**
VPC Peering, el uso compartido de TGW RAM y TGW Peering se basan todos en enrutamiento L3, por lo que los CIDR superpuestos los descartan. PrivateLink funciona mediante una ENI dentro de la VPC del consumidor, y VPC Lattice usa direccionamiento link-local, por lo que ambos funcionan independientemente de la superposición de CIDR. En situaciones como fusiones y adquisiciones o migraciones de MSP en las que es imposible rediseñar las IP, estas dos son las únicas opciones.
</details>

6. ¿Qué afirmación sobre el enrutamiento en una configuración de TGW Peering es correcta?
   - A) Las rutas se propagan automáticamente mediante BGP
   - B) BGP no es compatible, por lo que se deben agregar rutas estáticas manualmente a ambas tablas de rutas de TGW
   - C) Solo las tablas de rutas de VPC necesitan modificaciones
   - D) No se necesita ninguna configuración de enrutamiento

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) BGP no es compatible, por lo que se deben agregar rutas estáticas manualmente a ambas tablas de rutas de TGW**

**Explicación:**
Los adjuntos de peering de TGW no admiten BGP, por lo que no hay propagación automática de rutas. Se deben agregar rutas estáticas hacia los CIDR del par a ambas tablas de rutas de TGW; en las pruebas en vivo, no fluyó tráfico hasta que las rutas estáticas estuvieron establecidas. También ten en cuenta, desde el punto de vista operativo, que las rutas estáticas de TGW tienen prioridad sobre las rutas propagadas y que el ID del adjunto de peering difiere entre los lados solicitante y aceptante.
</details>
