# Cuestionario sobre MLflow Model Registry

## Preguntas de opción múltiple

1. ¿Qué es un modelo registrado?
   - A) Un endpoint de GPU
   - B) Una colección de versiones de modelo bajo un nombre lógico
   - C) Una copia de los datos de entrenamiento
   - D) Un registro que permite una sola ejecución

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B**

Por ejemplo, fraud-detector agrupa versiones y alias bajo un mismo nombre.
</details>

2. ¿Qué afirmación sobre la modificación de una versión de modelo es correcta?
   - A) Cada campo y byte de origen es permanentemente inmutable
   - B) Recibe un número de versión; las descripciones/etiquetas pueden cambiar y la preservación de artefactos es independiente
   - C) Cada versión expira después de 30 días
   - D) Cada modelo nuevo se fusiona con la versión anterior

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B**

Separe la práctica de versionar resultados nuevos de la inmutabilidad a nivel de almacenamiento.
</details>

3. ¿Cada versión de modelo tiene un enlace a una ejecución de entrenamiento?
   - A) Siempre, y el enlace no se puede eliminar
   - B) model_id conserva automáticamente la instantánea del conjunto de datos
   - C) No; los campos run_id/model_id de create_model_version son opcionales
   - D) El registro nunca admite enlaces de origen

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C**

Se permiten URI de origen directas. La trazabilidad completa requiere registro y retención explícitos.
</details>

4. ¿Qué es un alias?
   - A) Un porcentaje de tráfico integrado entre varias versiones
   - B) Un nombre mutable que apunta a una versión
   - C) Una dirección de base de datos fija
   - D) Un hash de contenido inalterable

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B**

Varios alias pueden hacer referencia a una versión, y un alias puede pasar a otra versión.
</details>

5. ¿Cuál es el estado de la API de etapas heredada?
   - A) En desuso desde la versión 2.9.0, aún presente en la 3.16.0
   - B) Eliminada de todas las versiones de MLflow
   - C) Una política de control de acceso equivalente a los alias
   - D) Solo se admite Production

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A**

Las etapas heredadas son None/Staging/Production/Archived. Diseñe flujos nuevos con alias/etiquetas y permisos explícitos.
</details>

6. ¿Cómo puede producirse el registro cuando se registra un modelo?
   - A) Estableciendo solo una etiqueta
   - B) Pasando registered_model_name a flavor log_model
   - C) Eliminando un alias
   - D) Renombrando un archivo a champion

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B**

Registrar después de registrar con register_model es otra vía. El registro no mueve por sí mismo un alias.
</details>

7. ¿Qué controla la promoción de champion?
   - A) MLflow aprueba automáticamente la versión más grande
   - B) Una etiqueta review_state por sí sola completa la separación de permisos
   - C) Evidencia de evaluación/aprobación y autenticación/autorización para quien realiza la acción
   - D) Cada entrenador siempre cambia el alias

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C**

Una cadena de etiqueta no sustituye ni el flujo de aprobación ni el control de acceso.
</details>

8. ¿Qué ocurre con un modelo ya cargado inmediatamente después de que cambia un alias?
   - A) Siempre se reemplaza de inmediato
   - B) Se vuelve a entrenar automáticamente
   - C) El tráfico sombra aparece automáticamente
   - D) Puede seguir atendiendo solicitudes hasta que lo cambie la política de recarga/despliegue/caché

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: D**

La nueva resolución y el ciclo de vida de una instancia cargada existente son independientes.
</details>

## Preguntas de respuesta corta

9. ¿READY por sí solo demuestra la compatibilidad de inferencia y la calidad del modelo?

<details>
<summary>Mostrar respuesta</summary>

No. Es un estado de registro; los elementos de prueba de metadatos pueden estar en READY. Valide por separado los flavors reales, los pesos, la carga de dependencias y la calidad.
</details>

10. ¿Por qué el registro no siempre puede reconstruir la trazabilidad exacta del código y los datos?

<details>
<summary>Mostrar respuesta</summary>

Los enlaces de ejecución/modelo son opcionales y los archivos de origen, las ejecuciones o los artefactos pueden cambiar o desaparecer. Conserve la versión de servicio, los hashes, el commit, la instantánea del conjunto de datos, las dependencias y las aprobaciones.
</details>

---

[Volver a los materiales de aprendizaje](../../../ai-ml/mlflow/02-model-registry.md)
