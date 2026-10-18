# Cuestionario sobre patrones de DAG y KubernetesPodOperator

Basado en Airflow 3.3.1 y Kubernetes provider 10.21.0. Comprueba la estructura de ejecución, el comportamiento de combinación, los permisos, el versionado de bundles y los límites de validación.

## Conceptos

1. ¿Quién crea un pod nuevo para una tarea KPO síncrona que usa CeleryExecutor?

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:** KPO llama a la API de Kubernetes desde el worker de Celery existente.

**Explicación:** La carga de trabajo se ejecuta en un pod independiente. Varias tareas pueden compartir el pod worker, y la imagen de la carga de trabajo no requiere Airflow por defecto.

</details>

2. ¿Cómo puede cambiar la creación física de pods al pasar de CeleryExecutor a KubernetesExecutor para una nueva ejecución de KPO?

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:** Puede crear un pod ejecutor de tarea y un pod de carga de trabajo en vez de usar un worker de Celery existente.

**Explicación:** Dos roles lógicos de ejecución no siempre significan dos pods creados de nuevo. Los reintentos, la reconexión con pods existentes y la ejecución diferida también afectan el número de pods activos.

</details>

3. ¿El proveedor 10.21.0 combina secuencialmente `pod_template_file` y `pod_template_dict` cuando se proporcionan ambos?

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:** No. Se selecciona el archivo y el diccionario de esa llamada no se combina adicionalmente.

**Explicación:** La plantilla seleccionada se reconcilia con `full_pod_spec` y el pod que construye KPO. No se trata de una combinación incondicional de cinco orígenes.

</details>

4. ¿Se conservan las solicitudes de la plantilla cuando `container_resources` proporciona solo límites?

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:** No lo des por sentado: esta combinación reemplaza el objeto de recursos y descarta las solicitudes anteriores.

**Explicación:** Especifica todas las solicitudes y límites necesarios e inspecciona el pod final. Otros campos siguen reglas distintas, como la concatenación de listas, la combinación de etiquetas por clave y la herencia de valores falsy.

</details>

5. ¿Establecer solo `service_account_name` de KPO concede al pod acceso a S3?

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:** No. Se necesitan la relación de confianza o asociación de IAM correspondiente y un proveedor de credenciales compatible.

**Explicación:** Verifica la configuración de IRSA o Pod Identity, la selección de credenciales del SDK y el acceso permitido/denegado real. El RBAC de Kubernetes de quien llama a KPO es distinto de los permisos de AWS del pod secundario.

</details>

6. ¿Una toleration por sí sola obliga a una carga de trabajo a ejecutarse en un NodePool dedicado con taint?

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:** No. Permite programar el pod en un nodo con ese taint; también pueden hacer falta selectores o afinidad obligatoria.

**Explicación:** Los pods de KPO usan la planificación estándar de Kubernetes. Un pool dedicado no elimina los fallos de nodo, la reclamación de instancias Spot ni la presión del disco.

</details>

7. ¿Todas las ejecuciones repetidas de un GitDagBundle con versionado deben usar su commit anterior?

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:** No. La solicitud, el DAG y las opciones globales para repetir ejecuciones y crear backfills, seguidas de los valores predeterminados de cada llamada, pueden seleccionar la versión más reciente.

**Explicación:** En 3.3.1, el valor de reserva si no se especifica es False para clear/rerun y True para backfill. Deshabilitar el versionado de bundles elimina el seguimiento de versiones de la ejecución; un commit fijado no fija por sí solo los datos ni las imágenes.

</details>

8. ¿LocalDagBundle, S3DagBundle y GCSDagBundle garantizan que un worker posterior lea exactamente la instantánea que usó el parser?

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:** No. Actualmente estos bundles no proporcionan versionado de bundle por ejecución.

**Explicación:** Los archivos y objetos pueden cambiar después del análisis. Gestiona por separado la coherencia de la implementación y la distribución de archivos relacionados.

</details>

9. ¿Se eliminó el sidecar git-sync en Airflow 3?

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:** No. El chart oficial de Helm todavía lo admite.

**Explicación:** El versionado de GitDagBundle es una función independiente. Usar git-sync no obliga a migrar ni conserva automáticamente el commit de cada ejecución.

</details>

10. ¿Qué puede salir mal si se aplica un SparkApplication con nombre fijo y solo se espera COMPLETED?

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:** Se puede confundir el estado COMPLETED anterior con un nuevo éxito, observar el espacio de nombres equivocado y retrasar la gestión de FAILED.

**Explicación:** Usa una identidad explícita de ejecución, el espacio de nombres, la gestión de estados terminales y contratos de limpieza. Los operadores nativos de Spark también requieren validar el recurso personalizado generado con la CRD de destino.

</details>

## Respuestas breves

11. Escribe la importación de KubernetesPodOperator e indica su argumento para los recursos de contenedor.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:** `from airflow.providers.cncf.kubernetes.operators.pod import KubernetesPodOperator`; usa `container_resources` para los recursos del contenedor.

**Explicación:** Usa Kubernetes V1ResourceRequirements. No trates un argumento genérico `resources` como si fuera el mismo ajuste.

</details>

12. ¿`is_delete_operator_pod=False` por sí solo garantiza que se conserve el pod en 10.21.0?

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:** No. El argumento sigue en el constructor, pero no se usa; configura `on_finish_action` y `on_kill_action` por separado.

**Explicación:** La finalización normal y la terminación son rutas distintas. La reconexión tampoco garantiza que las escrituras externas ocurran exactamente una vez.

</details>

13. ¿Un Role de KPO con alcance de espacio de nombres restringe a quien llama a los pods de su propia tarea?

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:** No. El Role del ejemplo puede afectar a los recursos de pod permitidos en todo ese espacio de nombres.

**Explicación:** Distingue las cuentas de servicio de quien llama y de la carga de trabajo. Usa controles de admisión y límites de confianza para autores de DAG no confiables que podrían seleccionar otras identidades o especificaciones peligrosas.

</details>

## Aplicación

14. Muestra los argumentos de `kpo_smoke` que pasan el ID de ejecución y eliminan el pod al completarse o terminarse.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:** Estos son los argumentos pertinentes dentro del DAG completo del capítulo.

```python
run_smoke = KubernetesPodOperator(
    task_id="run_smoke",
cmds=["python", "-B", "-c"],
arguments=[
    "import sys; print('KPO_SMOKE_OK run_id=' + sys.argv[1])",
    "{{ run_id }}",
],
on_finish_action="delete_pod",
on_kill_action="delete_pod",
)
```

**Explicación:** Pasa `run_id` como argumento independiente, en lugar de interpolarlo en un comando de shell. No supongas que las ejecuciones activadas por assets tienen `ds`. Consulta el capítulo para ver el DAG completo y la configuración de RBAC y plantillas.

</details>

15. Después de sobrescribir `automountServiceAccountToken=True` de la plantilla con False y comprobar `dry_run`, ¿qué más se debe comprobar?

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:** Inspecciona el valor final combinado y el pod admitido; luego verifica por separado la representación, las etiquetas de la instancia de tarea y la ejecución real.

**Explicación:** La función de combinación revisada puede conservar el valor True de la plantilla base en vez de aplicar False, al tratarlo como un valor vacío. `dry_run` no demuestra que se haya admitido el pod ni que la tarea haya tenido éxito; las comprobaciones locales del capítulo no sustituyen la ejecución en el clúster.

</details>

---

[Volver al material de aprendizaje](../../../data-on-eks/airflow/03-dag-patterns.md)
