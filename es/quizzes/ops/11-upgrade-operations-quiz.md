# Cuestionario sobre las operaciones de actualización de EKS

> **Documento relacionado**: [Actualizaciones de EKS](../../ops/11-upgrade-operations.md)

## 1. ¿Cuántas versiones menores intermedias puede omitir una actualización del plano de control de EKS?

- A) Ninguna: avance a la siguiente versión menor cada vez
- B) Una
- C) Dos
- D) Todas las que quiera

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A**

Por ejemplo, una actualización de 1.34 a 1.36 debe pasar por 1.35. Las tolerancias de desfase de kubelet son distintas de los pasos de actualización del plano de control.

</details>

## 2. ¿Cómo debe interpretarse la ausencia de un Deployment de CoreDNS en Auto Mode puro?

- A) Siempre significa que DNS no funciona
- B) Compruebe el servicio DNS del sistema de los nodos y el comportamiento real
- C) Instale siempre un Karpenter autoadministrado
- D) Elimine los Deployments de CoreDNS de todos los clústeres

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B**

Los clústeres mixtos deben conservar los Deployments de DNS y los complementos que necesiten los nodos que no son de Auto Mode.

</details>

## 3. ¿Qué afirmación sobre `restore create -o json` de Velero 1.18.4 es correcta?

- A) Completa una restauración real
- B) Se ejecuta completamente sin conexión
- C) No crea el objeto, pero puede realizar operaciones de descubrimiento y leer el Backup
- D) Solo es válido junto con `--dry-run`

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C**

`restore create` no tiene una opción `--dry-run`. Revisar solo la salida y probar una restauración real en un entorno aislado son acciones distintas.

</details>

## 4. ¿Qué debe hacer una herramienta de comprobación previa ante un error de API o un kubecontext incorrecto?

- A) Tratar los resultados vacíos como estado correcto
- B) Informar estado desconocido o contexto no coincidente e investigar
- C) Cambiar de contexto y actualizar automáticamente
- D) Eliminar los PDB

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B**

Que un Pod esté en ejecución por sí solo no demuestra que esté listo; también se deben comprobar la generación del Deployment y el estado del rollout.

</details>

## 5. ¿Cuál es una condición básica de elegibilidad para la reversión nativa de EKS?

- A) Que cualquier clúster se haya creado recientemente con su versión actual
- B) Cumplir los requisitos, incluida la iniciación dentro de los siete días posteriores a finalizar la actualización del plano de control para volver a la versión menor anterior
- C) Que se admita volver a cualquier versión anterior en cualquier momento
- D) Que una copia de seguridad de etcd anule todas las restricciones

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B**

Compruebe también que la versión de destino sea compatible, que la política de soporte sea `EXTENDED`, que el estado sea `ACTIVE` y que no haya funciones incompatibles de EKS.

</details>

## 6. Si el estado del clúster es ACTIVE durante la reversión de nodos de Auto Mode, ¿qué significa?

- A) La reversión se completó por completo
- B) El plano de control aún puede servir la versión actual; inspeccione el ID de actualización
- C) No es posible revertir los nodos
- D) Elimine de inmediato el clúster anterior

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B**

Auto Mode ajusta primero los nodos. El timeout predeterminado para los nodos es de 720 minutos; un timeout de espera del cliente no cancela la operación en AWS.

</details>

## 7. ¿Qué omite `rollback --force`?

- A) La ventana de siete días y todos los PDB
- B) Todas las interrupciones y la compatibilidad de datos
- C) Las comprobaciones de Insights, pero no la elegibilidad ni los controles de interrupción de Auto Mode
- D) La conservación de datos de etcd

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C**

Los estados ERROR y UNKNOWN bloquean la reversión, mientras que WARNING es informativo. Force no es la ruta de recuperación de referencia.

</details>

## 8. ¿Qué no se restaura automáticamente a su estado histórico con una reversión nativa de versión?

- A) La versión menor del servidor de API
- B) El ajuste de versión de los nodos de Auto Mode
- C) Los complementos, las aplicaciones, los objetos de etcd y los datos de PV
- D) Las versiones de los componentes del plano de control

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C**

Los grupos de nodos administrados normales requieren una gestión independiente mediante `UpdateNodegroupVersion`. Revertir la versión no equivale a restaurar una instantánea.

</details>

## 9. ¿Qué afirmación sobre establecer en cero el peso de un grupo de destino de NLB es correcta?

- A) Siempre se preservan las conexiones existentes hasta que terminan
- B) Las conexiones existentes pueden cerrarse al cabo de poco tiempo; pruebe el comportamiento de reintentos/sesiones
- C) Los pesos deben sumar 100
- D) NLB no admite grupos de destino ponderados

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B**

Los pesos son valores relativos de 0 a 999. Distinga los cambios ordinarios de la transición a peso cero; los listeners TLS no admiten afinidad de grupo de destino.

</details>

## 10. ¿Qué debe comprobarse antes de retirar Blue?

- A) Destruirlo de inmediato cuando el peso sea cero
- B) Revisar los recursos compartidos y sus referencias a grupos de destino, la compatibilidad de datos, el período de recuperación y la propiedad
- C) Que una respuesta HTTP 200 demuestra que todos los datos son coherentes
- D) Que EFS compartido elimina la necesidad de revisar escritores simultáneos

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B**

Tenga en cuenta el ciclo de vida del grupo de destino al eliminar un TGB de Auto Mode o el clúster, así como los listeners compartidos. Los cambios de espacio de nombres no garantizan el aislamiento de consumidores, bases de datos o DNS.

</details>
