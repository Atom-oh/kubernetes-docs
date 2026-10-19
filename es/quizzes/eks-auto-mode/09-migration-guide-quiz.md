# Cuestionario: guía de migración de EKS Auto Mode

> **Documento relacionado**: [Guía de migración](../../eks-auto-mode/09-migration-guide.md)
> **Última actualización**: 12 de septiembre de 2026

## Preguntas de opción múltiple

### 1. ¿Qué se debe hacer antes de habilitar o retirar capacidad de migración?

- A) Eliminar los grupos de nodos antiguos
- B) Inventariar las cargas de trabajo, dependencias, responsables y requisitos de recuperación
- C) Drenar todos los Pods
- D) Suponer que los nombres de instancia coincidentes demuestran compatibilidad

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Inventariar las cargas de trabajo, dependencias, responsables y requisitos de recuperación**

**Explicación:**
Vincula las identidades de la cuenta, el clúster y los grupos antiguos; después, inspecciona la ubicación, los datos, IAM, la red, los controladores, los costos y el estado de las aplicaciones. Valida cada etapa antes de escalar o eliminar recursos; la etapa de validación final no debe ser la primera comprobación del estado. La guía define el `WORK_DIR` privado y el `KUBE_CONTEXT` que se usan a continuación.

```bash
kubectl --context "$KUBE_CONTEXT" --request-timeout=15s \
  get deployments,statefulsets,daemonsets,jobs,cronjobs -A -o json |
jq '[.items[] | (.spec.template // .spec.jobTemplate.spec.template) as $t |
 {kind,namespace:.metadata.namespace,name:.metadata.name,uid:.metadata.uid,
  nodeSelector:$t.spec.nodeSelector,affinity:$t.spec.affinity,tolerations:$t.spec.tolerations,
  serviceAccountName:$t.spec.serviceAccountName,hostNetwork:$t.spec.hostNetwork,
  pvcNames:[$t.spec.volumes[]?.persistentVolumeClaim.claimName // empty]}]' \
  > "$WORK_DIR/workload-placement.json"
kubectl --context "$KUBE_CONTEXT" --request-timeout=15s get pods -A -o json |
jq '[.items[] | {namespace:.metadata.namespace,name:.metadata.name,node:.spec.nodeName,
  phase:.status.phase,deletionTimestamp:.metadata.deletionTimestamp,
  ready:([.status.conditions[]?|select(.type=="Ready")|.status]|first // "NotReported"),
  owners:[.metadata.ownerReferences[]?|{kind,name,controller}]}]' \
  > "$WORK_DIR/pod-state.json"
```

</details>

### 2. ¿Cómo pueden coexistir de forma predecible los nodos administrados antiguos y Auto Mode?

- A) No pueden coexistir
- B) Asignar explícitamente cada carga de trabajo y definir quién es responsable de su controlador
- C) Usar un clúster independiente
- D) Hacer coincidir únicamente las etiquetas de recursos de AWS

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Asignar explícitamente cada carga de trabajo y definir quién es responsable de su controlador**

**Explicación:**
Un selector específico del grupo de nodos antiguo y otro que identifique con precisión el grupo de Auto Mode y el tipo de cómputo permiten distinguir las flotas. Una etiqueta genérica de Karpenter también coincide con Karpenter autoadministrado. Mantén el DNS y los agentes que se ejecutan en nodos de ambas flotas, así como los controladores de almacenamiento y balanceadores existentes, hasta migrar sus dependencias. Estos son fragmentos de la especificación del Pod; la guía incluye Deployments canary completos.

Grupo administrado antiguo:
```yaml
# Pod template spec fragment
nodeSelector:
  eks.amazonaws.com/nodegroup: REPLACE_WITH_OLD_NODEGROUP
tolerations: []
```

Canary de Auto Mode:
```yaml
# Pod template spec fragment
nodeSelector:
  karpenter.sh/nodepool: migration-pool
  eks.amazonaws.com/compute-type: auto
tolerations:
- key: migration
  operator: Equal
  value: auto-mode
  effect: NoSchedule
```

</details>

### 3. ¿Qué orden reduce el riesgo de la migración?

- A) Empezar por producción crítica
- B) Empezar con cargas representativas de bajo riesgo y avanzar hacia dependencias más críticas
- C) Migrar todo a la vez
- D) Elegir un orden aleatorio

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Empezar con cargas representativas de bajo riesgo y avanzar hacia dependencias más críticas**

**Explicación:**
Desarrollo y pruebas, producción no crítica y producción crítica son etapas útiles si reflejan las dependencias reales. Actualiza la ubicación en el controlador propietario o en GitOps y luego verifica el comportamiento de la aplicación, el almacenamiento, IAM, DNS y el tráfico. Una preferencia flexible o una etiqueta inventada como `node-type=auto-mode` no demuestra que la migración se haya completado. Detente si el estado es fallido o desconocido; esperar un tiempo fijo no es una validación.

</details>

### 4. ¿Qué secuencia de reversión conserva una vía de recuperación?

- A) Eliminar y recrear primero el clúster
- B) Restablecer capacidad y ubicación compatibles en los nodos antiguos, verificar el estado y luego retirar los recursos concretos de Auto Mode
- C) Eliminar primero el NodePool de Auto Mode
- D) Deshabilitar Auto Mode y nada más

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Restablecer capacidad y ubicación compatibles en los nodos antiguos, verificar el estado y luego retirar los recursos concretos de Auto Mode**

**Explicación:**
Conserva el grupo de Auto Mode mientras la capacidad antigua alcanza el estado `Ready`. Revisa y restablece la ubicación prevista sin dejar un selector de Auto Mode en conflicto ni borrar reglas de afinidad que no estén relacionadas. Verifica también los datos y el tráfico, no solo los Pods. Retira la capacidad propiedad de la migración únicamente después. Eliminar un NodePool puede provocar la eliminación en cascada de nodos; un archivo JSON de escalado no puede recrear un grupo de nodos eliminado. Esta reversión corresponde a una migración de cargas de trabajo, no a una reversión de versión de Kubernetes.

</details>

### 5. ¿Qué se necesita antes de reducir el tamaño deseado del grupo de nodos administrado antiguo?

- A) Establecerlo inmediatamente en cero
- B) Validar las cargas migradas, acordonar y vaciar la capacidad antigua de aplicaciones, y coordinarse con su responsable
- C) Reducir siempre el tamaño a la mitad
- D) Esperar solo cinco minutos

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Validar las cargas migradas, acordonar y vaciar la capacidad antigua de aplicaciones, y coordinarse con su responsable**

**Explicación:**
Los cambios de configuración de escalado de un MNG usan el escalado del ASG y no respetan los PDB. La guía comprueba si los nodos antiguos están acordonados y si quedan Pods activos que no sean DaemonSet, y se detiene si alguna consulta falla. Revisa las dependencias del sistema y los resultados de los trabajos exportados; además, evita que los controladores vuelvan a programar cargas en los nodos antiguos. Reducir el tamaño a la mitad y esperar no demuestra que sea seguro. La gestión de IaC y del escalado sigue correspondiendo a sus responsables originales.

</details>

### 6. ¿Cómo se deben vigilar los costos durante la migración?

- A) Ignorarlos hasta que se eliminen todos los recursos antiguos
- B) Considerar que la cantidad actual de nodos es el costo exacto facturado
- C) Seguir las flotas y los balanceadores de carga que coexisten junto con la disponibilidad y el rendimiento
- D) Suponer que Auto Mode elimina automáticamente todos los cargos antiguos

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Seguir las flotas y los balanceadores de carga que coexisten junto con la disponibilidad y el rendimiento**

**Explicación:**
La coexistencia puede generar cargos por ambas flotas y por las rutas de tráfico. Usa datos reales de facturación y los publicadores operativos configurados. Los umbrales originales siguientes siguen siendo ejemplos de planificación sin verificar; no son métricas predeterminadas de Auto Mode ni intervalos normales.

| Señal | Ejemplo de línea base anterior | Ejemplo de alerta anterior |
|--------|-------------------------------|---------------------------|
| Pods pendientes | 0–5 | >10 durante 5 min |
| Tiempo de aprovisionamiento | <90 sec | >120 sec |
| Disponibilidad | >99.9% | <99.5% |
| Latencia de la API | <200 ms | >500 ms |

Un Pod pendiente no necesariamente está sin posibilidad de programación; `Running` no significa que la aplicación esté lista, y la ausencia de datos del recopilador no equivale a cero fallos.

</details>

### 7. ¿Qué acción se puede aplazar para conservar opciones de reversión después de validar las cargas de trabajo?

- A) Comprobar el comportamiento de las aplicaciones
- B) Comprobar que la ubicación sea la prevista
- C) Eliminar la definición del grupo de nodos antiguo
- D) Comprobar los datos y el estado de los controladores

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Eliminar la definición del grupo de nodos antiguo**

**Explicación:**
Conserva deliberadamente la definición o configuración antigua durante un periodo de estabilización y contabiliza los recursos y costos que se mantengan. El intervalo anterior de una a dos semanas es un ejemplo, no un requisito universal. Comprueba el estado real de disponibilidad y que los Jobs hayan terminado correctamente; no exijas que todos los Pods estén en `Running`. Elimina la definición mediante el responsable original de IaC solo después de validar los datos, el tráfico y las cargas de trabajo.

</details>

### 8. ¿Cuál es el enfoque correcto para un controlador de Karpenter autoadministrado existente?

- A) Eliminarlo siempre antes de habilitar Auto Mode
- B) Mantener Karpenter en una versión compatible durante la coexistencia, finalizar los recursos antiguos que administra y luego desinstalarlo
- C) Eliminar todas las CRD compartidas de Karpenter
- D) Seleccionar para eliminación todos los nodos etiquetados con Karpenter

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Mantener Karpenter en una versión compatible durante la coexistencia, finalizar los recursos antiguos que administra y luego desinstalarlo**

**Explicación:**
AWS documenta la migración con coexistencia directa. El requisito mínimo de migración v1.1 no sustituye los requisitos actuales de compatibilidad con Kubernetes. Usa referencias distintas a NodeClass y un grupo de Auto Mode con taint. No modifiques ni elimines las CRD compartidas de NodePool y NodeClaim. Retira los NodePools y los objetos NodeClaim antiguos que sean propiedad de la instalación mientras el controlador existente todavía pueda completar su finalización; confirma que se hayan limpiado las instancias y dependencias, y luego elimina solo su release de Helm y los recursos de IAM y de la cola.

</details>

## Referencias

- [Escalado de grupos de nodos administrados y PDB](https://docs.aws.amazon.com/eks/latest/userguide/update-managed-node-group.html)
- [Referencia de migración a Auto Mode](https://docs.aws.amazon.com/eks/latest/userguide/migrate-auto.html)
- [Migración con coexistencia de Karpenter](https://docs.aws.amazon.com/eks/latest/userguide/auto-migrate-karpenter.html)
