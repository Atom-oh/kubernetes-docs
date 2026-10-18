# Cuestionario sobre GWLB y GENEVE

> **Última actualización**: 15 de octubre de 2026

[Lee el capítulo y las fuentes principales](../../security/16-gwlb-geneve-inspection.md)

### 1. ¿Qué documenta AWS cuando todos los destinos GWLB elegibles están en mal estado?

- A) Entregar el tráfico a destinos en mal estado en vez de omitir directamente los dispositivos
- B) Enrutarlo directamente al destino original
- C) Cifrar todos los paquetes
- D) Garantizar la disponibilidad de la aplicación

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A) Entregar el tráfico a destinos en mal estado en vez de omitir directamente los dispositivos**

**Explicación:** GWLB no omite los dispositivos. AWS describe la selección aleatoria de destinos por flujo y la pérdida de paquetes hasta que se recupera el destino seleccionado. El reenvío continuo durante un fallo solo de estado es una hipótesis para una prueba de concepto; comprueba los destinos elegibles y la configuración entre zonas de cada AZ.

</details>

### 2. ¿Qué ocurre con un flujo nuevo cuando ya no quedan destinos registrados?

- A) Se omite directamente la inspección
- B) El tráfico se descarta
- C) Se crea un destino nuevo automáticamente
- D) WAF gestiona el flujo IP en su lugar

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) El tráfico se descarta**

**Explicación:** Los flujos nuevos no tienen destino; verifica las pérdidas y la recuperación. Distingue la condición en la que todos los destinos están en mal estado y prueba los flujos existentes por separado según su configuración de conmutación por error y drenaje.

</details>

### 3. ¿Qué ocurre con los flujos existentes cuando se usa `no_rebalance`?

- A) Siempre se migran con el estado completo de la sesión
- B) Se garantiza que tengan éxito
- C) Permanecen asignados y pueden terminar en un agujero negro en un destino en mal estado
- D) Omiten la inspección

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Permanecen asignados y pueden terminar en un agujero negro en un destino en mal estado**

**Explicación:** El rebalanceo puede redistribuir los flujos, pero no recrea el estado independiente de los dispositivos. Ambos atributos de conmutación por error deben tener el mismo valor.

</details>

### 4. ¿Qué establece el modo de dispositivo de TGW?

- A) IPS automático
- B) Replicación automática del estado entre firewalls
- C) Inspección de todos los paquetes locales de la VPC
- D) Selección coherente de la AZ de la asociación de inspección en ambas direcciones

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: D) Selección coherente de la AZ de la asociación de inspección en ambas direcciones**

**Explicación:** La selección simétrica de asociaciones/AZ por flujo es distinta de la afinidad a destinos de GWLB y de compartir sesiones entre proveedores. El modo de dispositivo reemplaza la preferencia predeterminada de TGW por la AZ de origen.

</details>

### 5. ¿Se puede combinar la afinidad de flujo basada en tuplas reducidas de dos o tres campos con el modo de dispositivo de TGW?

- A) No, según la restricción documentada
- B) Siempre
- C) Solo porque UDP 6081 está abierto
- D) Solo si todos los destinos están en mal estado

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A) No, según la restricción documentada**

**Explicación:** La documentación actual de AWS exige usar una tupla de cinco elementos con el modo de dispositivo de TGW. Revisa la concentración de carga que producen las tuplas reducidas y las combinaciones admitidas.

</details>

### 6. ¿Qué afirmación sobre los grupos de seguridad es correcta?

- A) GWLB y GWLBE requieren, cada uno, grupos de seguridad como los de ALB
- B) Ninguno admite esas asociaciones de grupos de seguridad; inspecciona las ENI del dispositivo y la carga de trabajo, las NACL y las rutas
- C) Los grupos de seguridad del dispositivo son irrelevantes
- D) Las NACL tienen estado

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Ninguno admite esas asociaciones de grupos de seguridad; inspecciona las ENI del dispositivo y la carga de trabajo, las NACL y las rutas**

**Explicación:** No inventes una configuración de grupo de seguridad para GWLB. El estado y el tráfico GENEVE externo aún requieren controles reales de ruta.

</details>

### 7. ¿Por qué hay que revisar la ruta de retorno de la subred NAT?

- A) Solo la necesita DNS
- B) Sigue automáticamente la ruta de salida
- C) Las respuestas después de la traducción inversa deben volver de forma coherente a través de la inspección
- D) NAT replica automáticamente el estado del firewall

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Las respuestas después de la traducción inversa deben volver de forma coherente a través de la inspección**

**Explicación:** Inspeccionar solo el tráfico saliente no basta. Registra las tuplas antes y después de la traducción y evita los bucles.

</details>

### 8. ¿GWLB resuelve todos los problemas de MTU con fragmentación/PMTUD?

- A) Sí, para todos los paquetes jumbo
- B) Sí, si el estado es correcto
- C) Sí, si la licencia del destino es válida
- D) No; ten en cuenta la encapsulación y la MTU de cada segmento

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: D) No; ten en cuenta la encapsulación y la MTU de cada segmento**

**Explicación:** AWS documenta paquetes con un máximo de 8500 bytes y una sobrecarga de 68 bytes, sin fragmentación ni PMTUD de GWLB. Prueba las rutas reales de paquetes y protocolos.

</details>
