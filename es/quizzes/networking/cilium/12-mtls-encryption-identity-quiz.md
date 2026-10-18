# Cuestionario de mTLS, cifrado transparente e identidad: parte 12

> **Base de revisión**: Cilium 1.20.2 (estable, 16 de septiembre de 2026); Cilium CLI 0.20.1; Hubble CLI 1.20.2. Los elementos marcados **[versión preliminar 1.21]** provienen de v1.21.0-pre.3 y pueden cambiar antes de GA.
> **Última actualización**: 15 de octubre de 2026

[Volver a la guía](../../../networking/cilium/12-mtls-encryption-identity.md)

1. ¿Cuál es el estado de Mutual Authentication de Cilium (SPIFFE/SPIRE, `authentication.mode: required`) en las versiones 1.20 y 1.21?
   - A) Eliminada en 1.20, ausente en 1.21
   - B) Beta en 1.20, estable en 1.21
   - C) Obsoleta en 1.20, eliminada en 1.21
   - D) Obsoleta en 1.21, eliminada en 1.22
<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Obsoleta en 1.20, eliminada en 1.21**

Las notas de actualización de 1.20 la marcan como obsoleta (aunque la página de documentación todavía se titula «Beta») y remiten a ztunnel. Las notas de actualización de 1.21 indican que se eliminó después de quedar obsoleta. El campo `authentication` de la política se conserva para la compatibilidad de las CRD, pero no se usa en 1.21.

</details>

2. ¿Cuál es el ID numérico de la identidad reservada `reserved:world`?
   - A) 1
   - B) 6
   - C) 8
   - D) 2
<details>
<summary>Mostrar respuesta</summary>

**Respuesta: D) 2**

1 es `host`, 2 es `world`, 6 es `remote-node` y 8 es `ingress`. Los ID 9 y 10 dividen `world` en variantes para IPv4 e IPv6.

</details>

3. ¿Cómo se inscriben las cargas de trabajo en el mTLS de ztunnel de Cilium?
   - A) Anota cada pod con `istio.io/dataplane-mode=ambient`
   - B) Etiqueta el espacio de nombres con `io.cilium/mtls-enabled=true`
   - C) Añade `authentication.mode: required` a una CiliumNetworkPolicy
   - D) Etiqueta cada pod con `io.cilium/mtls-enabled=true`
<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Etiqueta el espacio de nombres con `io.cilium/mtls-enabled=true`**

La inscripción solo se configura a nivel del espacio de nombres; no se admite a nivel del pod. La etiqueta de Istio Ambient pertenece a Istio, y `authentication.mode` correspondía al mecanismo Mutual Authentication eliminado.

</details>

4. ¿Qué puerto TCP transporta el tráfico HBONE entre proxies ztunnel y es el único al que puede dirigirse una política L4 para las cargas inscritas?
   - A) 15008
   - B) 4250
   - C) 15006
   - D) 15001
<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A) 15008**

El tráfico se cifra antes de salir del pod, por lo que una política L4 no puede ver los puertos internos; solo se puede seleccionar el puerto HBONE 15008. 15001 y 15006 son los puertos de redirección de salida dentro del pod y de entrada en texto sin cifrar, respectivamente; 4250 era el puerto de handshake de Mutual Authentication, ya eliminado.

</details>

5. ¿Cuál es el valor predeterminado de `encryption.ztunnel.ca.type`?
   - A) `spire`
   - B) `istiod`
   - C) `internal`
   - D) `cert-manager`
<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) `internal`**

`internal` usa la CA integrada de Cilium. `spire`, incorporado en 1.20, usa un servidor SPIRE externo, y el operador registra entradas para los espacios de nombres inscritos.

</details>

6. ¿Qué puerto UDP usa el endpoint de túnel WireGuard de Cilium en cada nodo?
   - A) 51820
   - B) 51871
   - C) 4789
   - D) 8472
<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) 51871**

Cilium usa 51871, no el puerto predeterminado de WireGuard 51820. Los grupos de seguridad de los nodos deben permitirlo entre ellos mediante una referencia al grupo de seguridad del nodo, nunca a un CIDR público. 4789 y 8472 son puertos VXLAN.

</details>

7. ¿Qué opción del modo estricto de cifrado transparente funciona solo con WireGuard?
   - A) `encryption.strictMode.ingress.enabled`
   - B) `encryption.strictMode.egress.allowRemoteNodeIdentities`
   - C) `encryption.strictMode.egress.enabled`
   - D) `encryption.strictMode.egress.cidr`
<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A) `encryption.strictMode.ingress.enabled`**

El modo estricto de ingreso descarta el tráfico de entrada interno al clúster que no haya llegado por el túnel WireGuard, por lo que no es compatible con IPsec. Los indicadores antiguos sin jerarquía (`encryption.strictMode.enabled` y los relacionados) se eliminaron en 1.20 y se reemplazaron por los nombres `egress.*`.

</details>

8. En el Secret de claves IPsec, ¿qué fuerza el uso de claves derivadas por túnel?
   - A) Configurar `encryption.ipsec.interface`
   - B) Usar el ID de clave 0
   - C) Habilitar `encryption.nodeEncryption`
   - D) Añadir un `+` después del ID de clave, como en `3+ rfc4106(gcm(aes)) ...`
<details>
<summary>Mostrar respuesta</summary>

**Respuesta: D) Añadir un `+` después del ID de clave, como en `3+ rfc4106(gcm(aes)) ...`**

Las claves globales quedaron obsoletas en 1.16 (GHSA-pwqm-x5x6-5586). `encryption.ipsec.interface` se eliminó en 1.20, y los ID de clave van del 1 al 15.

</details>

9. ¿En qué orden se realiza la migración de identidades Double Write de kvstore a CRD?
   - A) `doublewrite-readkvstore`, luego `doublewrite-readcrd` y luego `crd`
   - B) `crd`, luego `doublewrite-readcrd` y luego `kvstore`
   - C) `kvstore`, luego `crd` y luego `doublewrite-readcrd`
   - D) `doublewrite-readcrd`, luego `doublewrite-readkvstore` y luego `crd`
<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A) `doublewrite-readkvstore`, luego `doublewrite-readcrd` y luego `crd`**

Se escribe en ambos almacenes durante todo el proceso; las lecturas pasan de kvstore a CRD y, después, se retira kvstore. Antes de cada paso, observa las métricas `cilium_operator_doublewrite_*` hasta que los valores `*_only_identities` lleguen a cero.

</details>

10. ¿Qué ocurre en Cilium 1.20 al aplicar una CiliumNetworkPolicy sin `spec` ni `specs`?
    - A) Se acepta y el agente registra una advertencia
    - B) Se rechaza durante la admisión mediante una regla de validación CEL
    - C) Se acepta y se interpreta como permitir todo
    - D) Se acepta, pero nunca selecciona ningún endpoint
<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Se rechaza durante la admisión mediante una regla de validación CEL**

La CRD contiene `has(self.spec) || has(self.specs)` con el mensaje «spec or specs must be provided». Las políticas vacías existentes no se ven afectadas hasta que se actualizan.

</details>
