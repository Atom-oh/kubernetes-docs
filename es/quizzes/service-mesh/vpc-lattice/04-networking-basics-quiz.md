# Cuestionario sobre fundamentos: enlace local y SNI

Este cuestionario evalúa tu comprensión del direccionamiento de enlace local/ULA, el funcionamiento de SNI y la compatibilidad de protocolos de Lattice.

## Preguntas de opción múltiple

1. ¿Qué afirmación sobre los rangos de direcciones a los que resuelve el nombre DNS de un servicio de VPC Lattice es correcta?
   - A) Tanto IPv4 `169.254.171.0/24` como IPv6 `fe80::/10` son de enlace local
   - B) IPv4 `169.254.171.0/24` es de enlace local, mientras que IPv6 `fd00:ec2:80::/64` no es de enlace local, sino una dirección local única (ULA)
   - C) Ambos rangos son direcciones públicas globales únicas
   - D) No se admite IPv6

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) IPv4 `169.254.171.0/24` es de enlace local, mientras que IPv6 `fd00:ec2:80::/64` no es de enlace local, sino una dirección local única (ULA)**

**Explicación:**
El rango IPv4 forma parte de `169.254.0.0/16` (RFC 3927, enlace local), pero el rango IPv6 no es `fe80::/10` (enlace local); es `fd00:ec2:80::/64`, dentro del rango ULA `fc00::/7` (RFC 4193). Las direcciones de enlace local tienen alcance de enlace. Las ULA tienen alcance de dirección global según RFC 6724, pero están pensadas para el enrutamiento privado, no para el acceso global a Internet; no son la clase de direcciones locales de sitio obsoleta. Estas clasificaciones de direcciones no describen por sí solas la implementación especial de ingreso de Lattice de AWS.
</details>

2. ¿Cómo se deben interpretar los rangos de direcciones de Lattice?
   - A) Para conservar direcciones IP
   - B) Usa el direccionamiento específico del servicio documentado por AWS; no conviertas el prefijo en una definición general de interceptación de enlace local
   - C) Para afrontar el agotamiento de direcciones IPv4
   - D) Para que el cliente conozca explícitamente el destino

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Usa el direccionamiento específico del servicio documentado por AWS; no conviertas el prefijo en una definición general de interceptación de enlace local**

**Explicación:**
La ruta y la asociación específicas del servicio determinan la accesibilidad. ULA no es de enlace local ni pertenece a la clase obsoleta de direcciones locales de sitio; el alcance de una dirección y su accesibilidad mediante enrutamiento son distintos.
</details>

3. Durante la coexistencia, las solicitudes dirigidas a Lattice aparecen en los registros de Envoy. ¿Qué se debe comprobar después?
   - A) Si se superaron las cuotas de Lattice
   - B) Comprueba si la interceptación de la malla y la ruta de salida o la política de firma configuradas explican el fallo
   - C) Si las versiones de las CRD de Gateway API no coinciden
   - D) Si la configuración del protocolo del Target Group es incorrecta

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Comprueba si la interceptación de la malla y la ruta de salida o la política de firma configuradas explican el fallo**

**Explicación:**
Algunas políticas de Envoy rechazan destinos desconocidos y otras los reenvían. Inspecciona las reglas y los registros, y luego prueba el diseño elegido para omitir la interceptación o reenviar el tráfico; la coexistencia no implica que el fallo sea inevitable.
</details>

4. ¿Por qué la IP de destino por sí sola no basta para establecer una identidad de servicio y una autorización estables?
   - A) Las IP de destino se cifran y no hay alternativa
   - B) Usa una identidad que reconozca el servicio, correlación de DNS/solicitudes y reglas de red revisadas, en lugar de depender solo de la IP
   - C) Los registros de flujo se deshabilitan; habilitarlos lo resuelve
   - D) VPC CNI reutiliza IP; cambiar la política de asignación de IP lo resuelve

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Usa una identidad que reconozca el servicio, correlación de DNS/solicitudes y reglas de red revisadas, en lugar de depender solo de la IP**

**Explicación:**
La identidad del servicio no corresponde a un límite de seguridad CIDR estable y exclusivo del servicio. Las pruebas de red siguen siendo útiles cuando se combinan con políticas de autenticación, registros del servicio e ID de solicitud. Los cambios de grupos de seguridad deben hacerse con IaC revisada.
</details>

5. ¿Cuál es la distinción correcta entre SNI y ECH?
   - A) Es una vulnerabilidad residual del diseño inicial de TLS
   - B) TLS normal expone SNI para seleccionar un certificado; ECH es otro diseño, pero TLS Passthrough de Lattice no lo admite
   - C) El cifrado de SNI se omitió por razones de rendimiento
   - D) Se expuso deliberadamente para permitir que el tráfico atravesara firewalls

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) TLS normal expone SNI para seleccionar un certificado; ECH es otro diseño, pero TLS Passthrough de Lattice no lo admite**

**Explicación:**
TLS Passthrough requiere un dominio personalizado que coincida con SNI. AWS excluye explícitamente ECH/ESNI en ese modo, así que no afirmes que SNI en texto sin cifrar sea inevitable en todos los casos ni que la compatibilidad de Lattice sea simplemente desconocida.
</details>

6. ¿Qué afirmación sobre TCP sin formato en VPC Lattice es correcta?
   - A) TCP no es un protocolo admitido en la red de AWS
   - B) Los listeners de servicio no ofrecen TCP sin formato, pero las configuraciones de recursos TCP y los gateways de recursos son un modelo compatible independiente
   - C) Un NLB ya lo hace, por lo que sería redundante
   - D) Las normas de seguridad prohíben las comunicaciones sin cifrar

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Los listeners de servicio no ofrecen TCP sin formato, pero las configuraciones de recursos TCP y los gateways de recursos son un modelo compatible independiente**

**Explicación:**
No lo describas como una imposibilidad matemática en todo el producto. Compara el modelo independiente de acceso a la conectividad de recursos, la compatibilidad del controlador y los requisitos de enrutamiento; no clasifiques h2c gRPC como TCP sin formato arbitrario.
</details>

7. ¿Qué afirmación describe correctamente el compromiso entre un listener HTTPS y TLS Passthrough?
   - A) TLS Passthrough es superior en todos los sentidos
   - B) Passthrough conserva TLS del endpoint, pero no puede inspeccionar la identidad HTTP SigV4; las políticas de contexto de red anónimo son un control distinto
   - C) Ambos tipos de listener autentican los encabezados HTTP SigV4 cifrados sin descifrarlos
   - D) Un listener HTTPS no puede ver SNI

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Passthrough conserva TLS del endpoint, pero no puede inspeccionar la identidad HTTP SigV4; las políticas de contexto de red anónimo son un control distinto**

**Explicación:**
Lo que se pierde es la identidad HTTP autenticada y la inspección de capa 7, no toda forma de política de autenticación. Selecciona explícitamente los controles del listener y del endpoint; el cifrado HTTPS del backend no significa que Lattice valide los certificados de los destinos.
</details>
