# Cuestionario sobre Shared VPC y conectividad

> Este cuestionario evalúa su comprensión de [Shared VPC y conectividad](../../governance/04-shared-vpc-and-connectivity.md).

---

1. ¿Cómo se relaciona la propagación de TGW con las tablas de enrutamiento de VPC?
   - A) El límite de 100 prefijos de TGW es un límite fijo de Shared VPC
   - B) Las rutas de TGW no se propagan automáticamente; el propietario agrega rutas estáticas de VPC cuyo destino es TGW
   - C) Todas las tablas comparten una cuota
   - D) Nunca se alcanza primero la cuota de CIDR

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Las rutas de TGW no se propagan automáticamente; el propietario agrega rutas estáticas de VPC cuyo destino es TGW**

**Explicación:**
Las tablas de TGW tienen un límite predeterminado combinado de 10,000 rutas; las rutas de VPC no propagadas tienen un valor predeterminado de 500. No confunda el límite de 100 rutas propagadas de VGW con los totales de TGW.

</details>

---

2. ¿Qué recurso del propietario no puede describir un participante de Shared VPC?
   - A) Una subred
   - B) Su propio security group
   - C) NAT Gateway
   - D) Una tabla de enrutamiento

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) NAT Gateway**

**Explicación:**
Los participantes no pueden describir los NAT gateways del propietario. Los inventarios centralizados, los registros y las rutas de lectura delegada aún pueden aportar evidencia de auditoría.

</details>

---

3. ¿Cómo se debe diseñar el descubrimiento de subredes de LBC para Shared VPC?
   - A) Suponer que todas las versiones funcionan correctamente
   - B) Validar el modo del controller, los permisos y la visibilidad de etiquetas; considerar ID de subred explícitos
   - C) Hacer siempre que el propietario cree Ingress
   - D) Descubrir subredes solo mediante NAT gateways

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Validar el modo del controller, los permisos y la visibilidad de etiquetas; considerar ID de subred explícitos**

**Explicación:**
Las etiquetas del propietario no se comparten automáticamente. Especificar subredes es predecible, pero esto no demuestra que todos los modos de descubrimiento fallen.

</details>

---

4. ¿Qué afirmación describe correctamente las conexiones de larga duración de VPC Lattice?
   - A) Tanto los servicios como los recursos tienen una duración de 10 minutos
   - B) Distinga la duración de servicio de 10 minutos del tiempo de espera por inactividad de recursos de 350 segundos; pruebe el comportamiento del protocolo y la reconexión
   - C) Los listeners HTTP admiten nativamente cualquier WebSocket
   - D) Ninguna ruta admite tráfico de larga duración

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Distinga la duración de servicio de 10 minutos del tiempo de espera por inactividad de recursos de 350 segundos; pruebe el comportamiento del protocolo y la reconexión**

**Explicación:**
Los recursos no tienen el mismo límite de duración. Los listeners TLS o las rutas de recursos pueden atender WebSockets, según los requisitos del protocolo y la autorización.

</details>

---

5. ¿Qué afirmación describe correctamente la regla de prioridad de DNS de Route 53 Profiles?
   - A) La regla de la VPC local siempre prevalece sobre el Profile
   - B) La regla del Profile siempre prevalece sobre la VPC local
   - C) La VPC local prevalece cuando los nombres coinciden, pero si el Profile tiene registrado un nombre más específico, prevalece el Profile
   - D) La prioridad se determina al azar

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) La VPC local prevalece cuando los nombres coinciden, pero si el Profile tiene registrado un nombre más específico, prevalece el Profile**

**Explicación:**
Por ejemplo, si la VPC local tiene una regla para `example.com` y el Profile tiene una regla más específica para `test.example.com`, se aplica el Profile. Por eso se recomienda formalizar la regla de que «el Profile central nunca administra un nombre más específico que el espacio de nombres delegado a una carga de trabajo».

</details>
