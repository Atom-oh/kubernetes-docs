# Cuestionario sobre el ciclo de vida de nodos de EKS Auto Mode

> **Documento relacionado**: [Ciclo de vida de los nodos](../../eks-auto-mode/07-node-lifecycle.md)
> **Última actualización**: 12 de septiembre de 2026

## Preguntas de opción múltiple

### 1. ¿Qué campo de NodePool especifica la expiración por antigüedad de los NodeClaims recién creados?

- A) `nodeLifetime`
- B) `maxAge`
- C) `expireAfter`
- D) `rotationPeriod`

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) `expireAfter`**

**Explicación:**
El campo se encuentra en `spec.template.spec`. Auto Mode documenta un valor predeterminado de `336h` y aplica una gracia de terminación de NodeClaim de `24h` si el campo se omite en el pool. La vida máxima de una instancia administrada es de 21 días; no es una garantía de tiempo mínimo de actividad. Actualizar la plantilla no sobrescribe los claims existentes. Los valores mencionados en el cuestionario anterior —desarrollo: 336h, staging: 168h, producción: 72–168h y seguridad: 24–48h— son ejemplos de políticas sin verificación, no intervalos de cumplimiento obligatorios.
```yaml
# Fragment of NodePool spec.template.spec
expireAfter: 168h
terminationGracePeriod: 24h
```


</details>

### 2. ¿Qué ocurre cuando vence un NodeClaim de Auto Mode?

- A) Desaparece siempre de forma instantánea
- B) Comienza la terminación y el drenaje sin garantizar que haya un reemplazo listo previamente
- C) Solo se envía una notificación
- D) Se reinicia la misma instancia

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Comienza la terminación y el drenaje sin garantizar que haya un reemplazo listo previamente**

**Explicación:**
La expiración es un desencadenante forzoso y no está limitada por los presupuestos de interrupción de NodePool. El controlador impide la programación ordinaria de nuevos Pods e intenta drenar y limpiar el nodo. Los PDB y las anotaciones de Pod pueden afectar la expulsión, pero el período de gracia de terminación y el límite de vida de AWS acotan la protección. Por tanto, un presupuesto `nodes: 10%` no convierte las expiraciones en una actualización gradual controlada del 10 %. La capacidad de reemplazo y la disponibilidad de la aplicación deben comprobarse por separado.

</details>

### 3. ¿Qué afirmación sobre la selección del sistema operativo en EKS Auto Mode es correcta?

- A) Se elige AL2023 con `amiFamily`
- B) AWS administra las variantes de Bottlerocket; NodeClass no sirve para seleccionar una familia de AMI
- C) Se selecciona una AMI personalizada con `amiSelectorTerms`
- D) Los nodos GPU deben usar AL2023 administrado por el cliente

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) AWS administra las variantes de Bottlerocket; NodeClass no sirve para seleccionar una familia de AMI**

**Explicación:**
Auto Mode no expone esas interfaces para AMI personalizadas ni acceso SSH/SSM. Sus imágenes administradas también admiten cargas de trabajo aceleradas. Las cifras del cuestionario anterior (AL2023: 20–40 s frente a Bottlerocket: 15–25 s) y las del texto fuente (40–60 s frente a 20–30 s/20–40 s) no tienen mediciones verificadas; por tanto, no demuestran un orden universal de velocidad de arranque. Las comparaciones generales entre sistemas operativos son independientes de la interfaz administrada de Auto Mode.

</details>

### 4. ¿Qué puede ocurrir si una actualización de imagen administrada de Auto Mode hace que los NodeClaims existentes queden en estado `Drifted`?

- A) Todas las instancias se actualizan inmediatamente en el sitio
- B) Los claims aptos pueden reemplazarse conforme a los controles aplicables para interrupciones graduales
- C) No ocurre nada hasta que cambie una etiqueta arbitraria del Node
- D) Hay que eliminar todos los nodos simultáneamente

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Los claims aptos pueden reemplazarse conforme a los controles aplicables para interrupciones graduales**

**Explicación:**
Revisa las condiciones `Drifted`, sus motivos y la política vigente. Un presupuesto del 10 % se redondea hacia arriba y se combina con los demás límites activos; no implica que se reemplace un nodo por vez. También importan las restricciones de planificación, los PDB y la semántica del período de gracia. No todos los cambios de NodePool generan drift: ampliar de forma compatible los requisitos o cambiar el peso, los límites de comportamiento o la configuración de interrupciones es distinto de un drift del estado deseado. `amiFamily` no es un campo de Auto Mode.

</details>

### 5. ¿Qué contrapartida puede introducir una política de expiración más corta?

- A) Una reducción garantizada de costos
- B) Más reprogramación, trabajo de calentamiento y recuperación, y posible impacto en la disponibilidad
- C) La garantía de que habrá más CVE
- D) Estabilidad garantizada

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Más reprogramación, trabajo de calentamiento y recuperación, y posible impacto en la disponibilidad**

**Explicación:**
Reemplazar nodos con frecuencia puede hacer más frecuente el despliegue de imágenes administradas, pero no demuestra que el parche necesario esté disponible ni corrige todas las vulnerabilidades de una carga de trabajo. También puede aumentar los costos de capacidad, descarga de imágenes, puntos de control y recuperación. Por sí sola, la expiración no aumenta la probabilidad de interrupción de una instancia EC2 Spot. Evalúa por separado la recuperación de la aplicación y la gracia del nodo; el presupuesto de NodePool no puede limitar la tasa de expiración.
```yaml
# Fragment of NodePool spec.template.spec
expireAfter: 168h
terminationGracePeriod: 24h
```


</details>

### 6. ¿Cómo se deben entender la consolidación y la expiración cuando sus condiciones coinciden?

- A) La consolidación siempre prevalece
- B) La expiración siempre espera a que haya drift y luego a la consolidación
- C) Los métodos graduales y la expiración forzosa siguen rutas de control distintas, sin un orden total universal
- D) Un administrador debe elegir manualmente cada acción

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Los métodos graduales y la expiración forzosa siguen rutas de control distintas, sin un orden total universal**

**Explicación:**
El controlador de interrupciones graduales evalúa el drift antes de la consolidación; la expiración es una ruta forzosa independiente. No hay un orden global documentado como `drift > expiration > consolidation` ni una garantía de que siempre gane la primera condición. Un nodo de cinco días puede consolidarse antes de vencer a los siete días. Un NodeClaim vencido de ocho días puede empezar a terminar aunque el nodo esté muy utilizado.

</details>

### 7. ¿Cuál es un punto de partida adecuado para remediar urgentemente una vulnerabilidad de nodos?

- A) Establecer `expireAfter` en cero para todos los pools
- B) Inventar una anotación de drift
- C) Verificar la corrección administrada, identificar los claims afectados y seguir un procedimiento de un solo recurso con comprobaciones de estado
- D) Eliminar un pool en bloque y llamarlo reemplazo secuencial

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Verificar la corrección administrada, identificar los claims afectados y seguir un procedimiento de un solo recurso con comprobaciones de estado**

**Explicación:**
Confirma que la imagen administrada o la corrección esté disponible. Después, en el contexto revisado, inspecciona el UID de un solo NodeClaim, su asociación con el nodo, los PDB, el estado persistente y la capacidad disponible o que se pueda obtener. Si corresponde, usa drift administrado; evalúa por separado el reemplazo manual y vuelve a comprobar el estado del nodo y la evidencia de la imagen antes de pasar al siguiente. Una etiqueta cosmética `SecurityPatch` no garantiza que se active un parche, y eliminar en bloque todos los nodos etiquetados no constituye una actualización gradual. `--delete-emptydir-data` puede descartar datos locales.

La guía relacionada establece `KUBE_CONTEXT`; el comando siguiente solo recopila evidencia.

```bash
: "${NODECLAIM_NAME:?Select one NodeClaim for review}"
kubectl --context "$KUBE_CONTEXT" --request-timeout=15s get nodeclaim "$NODECLAIM_NAME" -o json |
  jq '{name:.metadata.name,uid:.metadata.uid,node:.status.nodeName,
       pool:.metadata.labels["karpenter.sh/nodepool"],imageID:.status.imageID,
       expireAfter:.spec.expireAfter,terminationGracePeriod:.spec.terminationGracePeriod,
       conditions:[.status.conditions[]?|{type,status,reason}]}'
kubectl --context "$KUBE_CONTEXT" --request-timeout=15s get pdb -A -o json |
  jq '[.items[]|{namespace:.metadata.namespace,name:.metadata.name,
       observedGeneration:.status.observedGeneration,generation:.metadata.generation,
       currentHealthy:.status.currentHealthy,desiredHealthy:.status.desiredHealthy,
       disruptionsAllowed:.status.disruptionsAllowed}]'
```


</details>

### 8. ¿El valor upstream `expireAfter: Never` permite conservar indefinidamente un nodo de Auto Mode?

- A) Sí, incluso ante cualquier mantenimiento o interrupción
- B) No; sigue aplicándose el límite de 21 días para las instancias administradas de Auto Mode
- C) Sí, si el Pod tiene un PDB
- D) Sí, para cualquier carga de trabajo con estado

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) No; sigue aplicándose el límite de 21 días para las instancias administradas de Auto Mode**

**Explicación:**
La sintaxis upstream no permite anular la vida útil del servicio Auto Mode. No recomiendes `Never` como forma de ejecutar indefinidamente una base de datos de Auto Mode o un trabajo prolongado en una sola instancia, ni supongas una respuesta concreta de admisión sin probarla. Planifica puntos de control, almacenamiento duradero externo y recuperación. El drift, las interrupciones y otras acciones del ciclo de vida pueden ocurrir antes.

</details>

## Referencias

- [Valores predeterminados de NodePool en Auto Mode](https://docs.aws.amazon.com/eks/latest/userguide/create-node-pool.html)
- [Vida útil máxima de Auto Mode](https://docs.aws.amazon.com/eks/latest/userguide/auto-security.html)
- [Interrupciones y drift](https://karpenter.sh/v1.14/concepts/disruption/)
