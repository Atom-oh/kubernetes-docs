# Cuestionario sobre NGFW de Palo Alto y Fortinet

> **Última actualización**: 15 de octubre de 2026

[Lee el capítulo y las fuentes principales](../../security/15-ngfw-paloalto-fortinet.md)

### 1. ¿La compatibilidad genérica con GENEVE demuestra la compatibilidad con AWS GWLB?

- A) Sí, basta con UDP 6081
- B) No; verifica la integración del proveedor admitida y los metadatos de AWS requeridos
- C) Sí, cualquier IP de administración sirve como par
- D) Solo importa el logotipo del producto

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) No; verifica la integración del proveedor admitida y los metadatos de AWS requeridos**

**Explicación:** Adapta la versión, las interfaces, la política y el procesamiento de metadatos al modo de implementación oficial.

</details>

### 2. ¿Qué demuestra una comprobación de estado correcta del dispositivo?

- A) Que todas las firmas de IPS están activas
- B) Que el descifrado TLS funciona para todos los clientes
- C) Que respondió el endpoint de estado configurado, no que la inspección sea completa
- D) Que la capacidad empresarial N-1 es suficiente

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Que respondió el endpoint de estado configurado, no que la inspección sea completa**

**Explicación:** Además de comprobar el estado, usa canarios de inspección, verificaciones de políticas y licencias, y mediciones de la aplicación.

</details>

### 3. ¿Cómo se deben usar los ejemplos de comprobación de estado del proveedor?

- A) HTTP 80 es universal
- B) Cualquier puerto de respuesta es intercambiable
- C) Los datos GENEVE y el estado deben usar el mismo protocolo
- D) Adáptalos a la plantilla real, el grupo de destino y la respuesta del dispositivo

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: D) Adáptalos a la plantilla real, el grupo de destino y la respuesta del dispositivo**

**Explicación:** La guía manual contiene indicaciones contradictorias sobre la prohibición y el perfil de HTTP. En lugar de automatizar esa ambigüedad, verifica la compatibilidad con TCP/HTTPS y las respuestas reales en la versión y plantilla seleccionadas.

</details>

### 4. ¿Qué se necesita para inspeccionar una carga útil cifrada?

- A) Descifrado o terminación admitidos, y una política de confianza y compatibilidad probada
- B) Implementar GWLB sin más
- C) Usar solo el VNI de GENEVE
- D) Tener un destino en buen estado

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A) Descifrado o terminación admitidos, y una política de confianza y compatibilidad probada**

**Explicación:** GENEVE no cifra ni termina TLS. Valida mTLS, el pinning, la confianza de la CA, la compatibilidad de protocolos y las excepciones.

</details>

### 5. ¿Un grupo de destinos HTTPS de ALB valida el certificado del backend?

- A) Siempre
- B) No; AWS documenta que ALB no valida los certificados de los destinos
- C) Solo cuando GWLB está habilitado
- D) Solo cuando la acción de WAF es Block

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) No; AWS documenta que ALB no valida los certificados de los destinos**

**Explicación:** El cifrado del transporte y la validación obligatoria de la identidad del backend son propiedades de diseño distintas.

</details>

### 6. ¿Qué dirección puede observar un dispositivo después del SNAT del nodo?

- A) Una identidad de carga de trabajo inmutable
- B) Siempre la dirección original del pod
- C) La dirección del nodo; para atribuirla al pod se requiere correlación con CNI/IPAM
- D) Siempre la dirección del navegador del usuario

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) La dirección del nodo; para atribuirla al pod se requiere correlación con CNI/IPAM**

**Explicación:** Registra los puntos y las marcas de tiempo de la traducción. Incluso las direcciones de pod que se conservan no son identidades permanentes.

</details>

### 7. ¿Añadir destinos GWLB independientes replica el estado de las sesiones del firewall?

- A) Siempre
- B) Solo porque GENEVE usa UDP
- C) Solo porque los destinos comparten una AZ
- D) No; compartir el estado requiere un diseño admitido por el proveedor y pruebas

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: D) No; compartir el estado requiere un diseño admitido por el proveedor y pruebas**

**Explicación:** La reasignación de flujos y la replicación del estado son distintas. Prueba las sesiones existentes y nuevas durante los fallos, el escalado y las actualizaciones.

</details>

### 8. ¿Qué referencia permite comparar de forma justa los diseños de dispositivos?

- A) Tráfico empresarial medido con los perfiles reales de seguridad y descifrado, capacidad N-1, latencia y errores
- B) Solo el rendimiento máximo de la hoja de datos
- C) Solo el precio de las instancias EC2
- D) Solo las comprobaciones de estado correctas

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A) Tráfico empresarial medido con los perfiles reales de seguridad y descifrado, capacidad N-1, latencia y errores**

**Explicación:** Controla la mezcla de tráfico, las licencias, las funciones, las rutas entre AZ y las condiciones de sesión. En esta actualización de la documentación no se midió ningún resultado de rendimiento.

</details>
