# Cuestionario sobre el comportamiento de escalado de EKS Auto Mode

> **Documento relacionado**: [Comportamiento de escalado](../../eks-auto-mode/03-scaling-behavior.md)

## Preguntas de opción múltiple

### 1. ¿Qué permite `consolidationPolicy: WhenEmptyOrUnderutilized`?

- A) Eliminar únicamente nodos vacíos
- B) Consolidar, para ahorrar costos, nodos elegibles vacíos o no vacíos
- C) Mantener todos los nodos de forma indefinida
- D) Eliminar nodos solo a una hora fija

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Consolidar, para ahorrar costos, nodos elegibles vacíos o no vacíos**

**Explicación:**
Permite eliminar un nodo o reemplazarlo por otro más económico cuando las cargas de trabajo siguen siendo programables conforme a las restricciones pertinentes. Importan las solicitudes de recursos, los PDB, los presupuestos y las anotaciones; no se basa simplemente en un umbral de CPU medido.

```yaml
# Fragment inside a NodePool; eligibility delay, not a deletion deadline
disruption:
  consolidationPolicy: WhenEmptyOrUnderutilized
  consolidateAfter: 1m
```

El temporizador se reinicia cuando se agregan o se eliminan Pods. Un minuto es un período de elegibilidad/estabilidad, no una garantía de que la eliminación o el reemplazo termine en un minuto. La API actual de AWS también admite `Balanced`, que tiene en cuenta el costo de la interrupción además del ahorro.

</details>

### 2. ¿Qué comando muestra los NodeClaims?

- A) kubectl get nodes --show-claims
- B) kubectl get nodeclaims
- C) kubectl describe karpenter claims
- D) kubectl get ec2-nodes

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) kubectl get nodeclaims**

**Explicación:**
Los NodeClaims describen la configuración deseada del nodo y el ciclo de vida/estado del proveedor; no solo el instante del aprovisionamiento. Inspeccione las condiciones y el nombre del nodo vinculado; `Drifted` es una condición, no la antigua anotación ficticia de nodo `karpenter.sh/drift-hash`.

```bash
kubectl --context "$CLUSTER_NAME" --request-timeout=15s get nodeclaims -o wide
: "${NODECLAIM_NAME:?Select a NodeClaim from the list}"
kubectl --context "$CLUSTER_NAME" --request-timeout=15s describe nodeclaim "$NODECLAIM_NAME"
```

</details>

### 3. ¿Cuándo puede un Pod no programable hacer que Auto Mode aprovisione capacidad?

- A) Cuando todos los Pods llevan cinco minutos en Pending
- B) Cuando el Pod no cabe en la capacidad existente y un pool/capacidad compatible y elegible puede satisfacer sus restricciones
- C) Cuando el recuento de nodos cae por debajo de un umbral global fijo
- D) Solo después de que un operador ejecute un comando de escalado manual

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Cuando el Pod no cabe en la capacidad existente y un pool/capacidad compatible y elegible puede satisfacer sus restricciones**

**Explicación:**
Importan la incapacidad del scheduler para colocar el Pod, las restricciones coincidentes de NodePool/NodeClass, las cuotas y la capacidad real. Un Pod ya programado que espera una imagen o un contenedor de inicialización puede estar en Pending sin que haga falta un nodo nuevo. Auto Mode no garantiza una asignación inmediata ni la estimación anterior, no verificada, de 40–90 segundos.

</details>

### 4. ¿Qué puede impedir la consolidación de un nodo candidato?

- A) Una anotación aplicable `do-not-disrupt`
- B) Un PDB que impide desalojar las cargas de trabajo requeridas
- C) Que aún no haya transcurrido el intervalo de estabilidad `consolidateAfter`
- D) Todas las anteriores

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: D) Todas las anteriores**

**Explicación:**
Cada uno de estos factores puede impedir o retrasar una acción de consolidación. La respuesta anterior incluía por error los nodos que solo tienen Pods de DaemonSet como impedimento: esos nodos pueden considerarse vacíos.

```yaml
# Metadata fragment on the intended Node or Pod, not NodePool metadata
metadata:
  annotations:
    karpenter.sh/do-not-disrupt: "true"
```

Esto no garantiza protección contra todos los motivos de interrupción. La expiración, las interrupciones y los límites del período de gracia de terminación deben considerarse por separado. Retire la protección temporal cuando termine la necesidad de mantenimiento para la que se aplicó.

</details>

### 5. ¿Qué factores pueden contribuir al drift o al reemplazo?

- A) La configuración deseada pertinente de NodeClass deja de coincidir con el nodo
- B) AWS selecciona una AMI nueva administrada por Auto Mode
- C) Cambia la selección resuelta de subredes/grupos de seguridad
- D) Todos los anteriores pueden contribuir

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: D) Todos los anteriores pueden contribuir**

**Explicación:**
Inspeccione las condiciones reales del NodeClaim y las decisiones del proveedor. No toda edición causa drift: ampliar los requisitos puede mantener la compatibilidad de las instancias existentes, y los ajustes de peso/límites/interrupciones son de comportamiento. Editar reglas del mismo grupo de seguridad no equivale a resolver un grupo diferente. El reemplazo gradual depende de la programación y los presupuestos, y puede ocurrir en paralelo; no siempre se realiza secuencialmente, un nodo a la vez.

</details>

### 6. ¿Cómo se debe reducir la latencia de inicio de Auto Mode?

- A) Cambiar `amiFamily` a AL2023
- B) Medir la ruta de la carga y probar cambios compatibles de capacidad, imagen y almacenamiento
- C) Suponer que el volumen más pequeño posible siempre es el más rápido
- D) Tratar 40–90 segundos como un SLO garantizado de extremo a extremo

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Medir la ruta de la carga y probar cambios compatibles de capacidad, imagen y almacenamiento**

**Explicación:**
AWS selecciona la imagen Bottlerocket administrada. Auto Mode no ofrece el antiguo control comparativo `amiFamily`. Separe el registro del nodo, el tiempo de imagen/inicialización y la disponibilidad de la aplicación, e incluya fallos/timeouts en las mediciones.

Las estimaciones anteriores del cuestionario —**20–40 segundos para AL2023** y **15–25 segundos para Bottlerocket**— se conservan como cifras didácticas históricas no verificadas. No son resultados medidos de Auto Mode y no demuestran una ventaja actual en el tiempo de arranque ni una opción de AMI compatible.

</details>
