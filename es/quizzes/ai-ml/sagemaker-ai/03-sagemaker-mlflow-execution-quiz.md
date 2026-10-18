# Cuestionario sobre la ejecución de SageMaker AI y MLflow

## Preguntas de opción múltiple

1. ¿Qué recurso se utiliza para las nuevas implementaciones administradas de MLflow?
   - A) Solo el antiguo Tracking Server
   - B) SageMaker MLflow App
   - C) Un LoadBalancer público de EKS
   - D) Solo un archivo SQLite local

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B**

La ruta administrada usa la API actual de SageMaker MLflow App.
</details>

2. ¿Qué se requiere antes de una ejecución completa?
   - A) Una prueba de humo completada y un análisis de los registros en busca de PII sin procesar
   - B) Eliminar la pertenencia al proyecto
   - C) Ejecutar de inmediato el máximo de pasos
   - D) Desactivar la limpieza final

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A**

Revise primero la finalización de la prueba de humo, la seguridad de los registros, los resultados agregados y el inventario de adaptadores.
</details>

3. ¿Cuál es el contrato de fallo/plazo del Job de EKS?
   - A) Reintentos ilimitados y sin plazo
   - B) `backoffLimit: 0` y `activeDeadlineSeconds: 10800`
   - C) Diez reintentos y una hora
   - D) Un Deployment permanente

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B**

Estos son los valores de configuración de reintentos y plazo del Job. Los fallos del controlador o del nodo pueden retrasar la liberación de recursos; no garantizan que todos los recursos desaparezcan en tres horas ni limitan el costo total.
</details>

4. ¿Cuándo debe fallar la verificación de limpieza?
   - A) Cuando no queden recursos
   - B) Cuando queden recursos o los errores impidan confirmar su estado
   - C) Cuando la prueba de humo se complete correctamente
   - D) Cuando coincidan los hashes del conjunto de datos

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B**

Que no queden recursos no basta si fallaron las consultas. Conserve los estados desconocidos y rechace eliminaciones basadas solo en nombres de inventarios antiguos sin evidencia de propiedad.
</details>

5. ¿Qué se ejecutó realmente el 1 de septiembre?
   - A) Un SageMaker Training Job completo
   - B) Un EKS GPU Job completo
   - C) Las rutas de aprovisionamiento y limpieza
   - D) La evaluación del modelo ajustado

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C**

Los dos GPU Jobs se detuvieron antes de enviarse.
</details>

6. ¿Por qué sigue bloqueada la ejecución de GPU al 12 de septiembre de 2026?
   - A) El DLC de PyTorch 2.8 fijado alcanzó el fin de sus parches el 6 de agosto
   - B) El empaquetado del código fuente tiene costo
   - C) Se eliminaron todas las aplicaciones de MLflow
   - D) Las pruebas unitarias locales necesitan una GPU

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A**

Valide un DLC compatible, la cohorte de torch y dependencias, y una prueba de humo en GPU. Eliminar únicamente la comprobación de fecha no constituye una actualización.
</details>

7. ¿Qué hace el launcher de SageMaker si no se especifica `--execute`?
   - A) Envía el Job completo de inmediato
   - B) Solo escribe el JSON de la solicitud
   - C) Elimina los Jobs existentes
   - D) Garantiza una estimación de costo

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B**

La vista previa de la solicitud es el comportamiento predeterminado. El envío real requiere la comprobación de soporte del runtime y una revisión aparte.
</details>

8. ¿Basta con guardar el JSON de métricas/parámetros de MLflow de EKS?
   - A) Sí, incluye automáticamente los pesos del adaptador
   - B) Descargar los adaptadores finales y los artefactos agregados, y después verificar sus hashes
   - C) `emptyDir` sobrevive a la eliminación del clúster
   - D) Se puede reconstruir el modelo a partir de un fragmento de log

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B**

Exportar metadatos no es lo mismo que conservar archivos. Si se conserva un clúster después de un error de exportación, también hay que tener en cuenta los costos y realizar la limpieza posterior.
</details>

---

[Volver a los materiales de aprendizaje](../../../ai-ml/sagemaker-ai/03-sagemaker-mlflow-execution.md)
