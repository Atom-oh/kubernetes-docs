# Cuestionario de Ray Train / Tune

## Preguntas de opción múltiple

1. ¿Qué no crea Ray Train automáticamente?
   - A) Coordinación subyacente de workers
   - B) Configuración del grupo de procesos del framework
   - C) Toda la lógica de modelo/partición de datos/guardado y restauración de estado
   - D) Solicitudes de recursos de Ray

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C**

Prepare la integración de modelo/data-loader y la lógica real de modelo, optimizador y checkpoint.
</details>

2. ¿Cuál es el valor predeterminado revisado de Train V2 en 2.58.0?
   - A) V2 cuando la variable de entorno no está configurada
   - B) Solo puede ejecutarse V1
   - C) Se eliminó la importación de TorchTrainer
   - D) Los extras de Ray instalan PyTorch automáticamente

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A**

Distinga las ejecuciones que seleccionan explícitamente la implementación anterior. Los frameworks son dependencias independientes.
</details>

3. ¿Qué sucede cuando se configura el trainer_resources heredado en V2?
   - A) Siempre reserva más CPU para el controller
   - B) Se genera un error de obsolescencia
   - C) Aumenta el número de GPU
   - D) Cambia el número de pruebas de Tune

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B**

Los ámbitos de recursos del controller, los workers de entrenamiento y el driver de Tune son distintos.
</details>

4. ¿Qué hace Checkpoint.from_directory?
   - A) Captura automáticamente todos los estados de modelo/optimizador/RNG
   - B) Hace referencia a archivos en un directorio de checkpoint preparado por el usuario
   - C) Despliega el modelo
   - D) Anonimiza el conjunto de datos

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B**

Cree la carga útil de recuperación y cargue el checkpoint devuelto por get_checkpoint.
</details>

5. ¿Cuál es la regla de participación de report de V2 en 2.58.0?
   - A) Solo el rango 0 lo llama
   - B) Cada worker alcanza la barrera el mismo número de veces
   - C) Cada métrica se promedia automáticamente
   - D) No puede llamarse sin un checkpoint

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B**

Los demás workers informan checkpoint=None incluso cuando solo el rango 0 guarda archivos.
</details>

6. ¿max_failures=0 deshabilita todos los reintentos?
   - A) Sí
   - B) No; los reintentos del controller y de preempción tienen configuraciones separadas
   - C) Siempre significa reintentos infinitos
   - D) Solo deshabilita los reintentos de Karpenter

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B**

Los valores predeterminados revisados para controller_failure_limit y max_preemption_failures son ambos -1.
</details>

7. ¿Cuál es el patrón actual de integración de Train/Tune V2?
   - A) Pasar la instancia de V2 Trainer directamente a Tuner
   - B) Construir y ajustar un Trainer dentro de una función entrenable; conectar callbacks según sea necesario
   - C) Las bibliotecas no pueden combinarse
   - D) Siempre se necesita un clúster de Kubernetes independiente

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B**

La entrada directa de V2 Trainer generó TuneError en la comprobación nativa. La integración requiere configuración y planificación de recursos.
</details>

8. ¿Qué reenvía TuneReportCallback?
   - A) Una métrica de worker promediada automáticamente
   - B) Una segunda carga de checkpoint
   - C) El diccionario de métricas del primer worker y la ruta de checkpoint existente
   - D) Siempre funciona fuera de las sesiones de Tune

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C**

Constrúyalo en una sesión de Tune. Realice la agregación de métricas por separado.
</details>

## Preguntas de respuesta corta

9. ¿Por qué planificar conjuntamente los recursos de los drivers de pruebas y los workers de Train?

<details>
<summary>Mostrar respuesta</summary>

Los drivers pueden ocupar recursos requeridos por sus workers anidados o grupos de colocación. Compruebe conjuntamente la concurrencia, los paquetes de workers, los límites del clúster y la viabilidad por nodo.
</details>

10. ¿Qué no demuestra un ejemplo exitoso de Tune escalar?

<details>
<summary>Mostrar respuesta</summary>

No demuestra la precisión del modelo, el rendimiento de PyTorch/DDP o GPU, la recuperación de checkpoint multinodo ni el autoescalado de EKS. Comprueba las API y la recopilación de dos resultados de pruebas escalares.
</details>

---

[Volver a los materiales de aprendizaje](../../../ai-ml/ray/03-ray-train-tune.md)
