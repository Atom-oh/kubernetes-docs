# Cuestionario sobre Kubeflow Notebooks

Referencia: Notebooks 1.11.0 / Community Distribution 26.03.1.

## Preguntas de opción múltiple

1. ¿Qué reconcilia el controlador de Notebook?

   - A) Un proceso de navegador en la laptop del usuario
   - B) StatefulSet, Service y recursos de enrutamiento configurados desde un Notebook CR
   - C) Una instancia EC2 para cada usuario
   - D) Solo un panel de HTML

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) StatefulSet, Service y recursos de enrutamiento configurados desde un Notebook CR**

El controlador de StatefulSet crea Pods y Kubernetes los programa. El panel es un punto de entrada de UI.
</details>

2. ¿Cuál es la referencia de versión precisa aquí?

   - A) Todos los componentes son Workspaces GA
   - B) Notebooks v1.11.0; 26.03.1 denomina a Workspaces beta mientras que sus imágenes son v2.0.0-alpha.3
   - C) Notebook y Workspace son API idénticas
   - D) v1 tiene una fecha de finalización de soporte confirmada en este capítulo

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Notebooks v1.11.0; 26.03.1 denomina a Workspaces beta mientras que sus imágenes son v2.0.0-alpha.3**

Las descripciones de las versiones y las etiquetas de imagen difieren. Verifica la compatibilidad real con API/migración en vez de inferir GA o una fecha de retirada de v1.
</details>

3. ¿Un Profile aísla automáticamente cada notebook de todos los demás usuarios?

   - A) Sí, incluidos AWS y el almacenamiento
   - B) No; los Profiles se pueden compartir y la red, el almacenamiento, IAM y la autorización de aplicaciones siguen siendo independientes
   - C) Sí, porque los namespaces bloquean los paquetes de red
   - D) Sí, porque RBAC cancela todos los permisos no relacionados

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) No; los Profiles se pueden compartir y la red, el almacenamiento, IAM y la autorización de aplicaciones siguen siendo independientes**

La UI completa selecciona un namespace de Profile. El Notebook CRD en sí no requiere un objeto Profile en cada namespace.
</details>

4. ¿Qué sobrevive al reemplazo de un Pod de notebook?

   - A) Toda la memoria de procesos
   - B) Cada paquete instalado en cualquier lugar del contenedor
   - C) Los datos en volúmenes persistentes conservados; los paquetes de la capa de contenedor y la memoria del kernel no
   - D) Cada instancia EC2 adjunta

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Los datos en volúmenes persistentes conservados; los paquetes de la capa de contenedor y la memoria del kernel no**

Revisa las ubicaciones de montaje, el ciclo de vida de PVC/volúmenes y las copias de seguridad. ReadWriteOnce es un modo de acceso de un solo nodo, no una garantía de un solo Pod.
</details>

5. ¿Cuáles son los valores predeterminados inspeccionados para la eliminación por inactividad?

   - A) Habilitada, con un umbral de inactividad de un minuto
   - B) Deshabilitada; umbral de inactividad de 1440 minutos, período de comprobación de 1 minuto
   - C) Habilitada para cada proceso de RStudio y shell
   - D) Deshabilitada solo para notebooks de GPU

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Deshabilitada; umbral de inactividad de 1440 minutos, período de comprobación de 1 minuto**

El culler usa la actividad del kernel de Jupyter. Los resultados fallidos/vacíos de la API dejan sin cambios la actividad anterior y aun así pueden llevar a la detención. Prueba la imagen y la ruta de acceso reales.
</details>

6. ¿Cómo representa v1.11.0 un Notebook detenido?

   - A) spec.replicas: 0
   - B) Presencia de kubeflow-resource-stopped; el controlador establece las réplicas de StatefulSet en cero
   - C) El valor de anotación false significa en ejecución
   - D) Eliminando su PVC

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Presencia de kubeflow-resource-stopped; el controlador establece las réplicas de StatefulSet en cero**

NotebookSpec no tiene un campo replicas. Reanúdalo eliminando la anotación. Incluso una cadena false sigue contando como presente.
</details>

7. ¿Qué garantiza un digest de imagen personalizado?

   - A) Todos los usuarios tienen entornos de ejecución completos idénticos
   - B) El contenido de imagen referenciado; los datos montados y los cambios en tiempo de ejecución aún pueden diferir
   - C) Compatibilidad automática con todos los controladores de GPU
   - D) Que las restricciones de imagen de UI no se puedan omitir mediante la API

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) El contenido de imagen referenciado; los datos montados y los cambios en tiempo de ejecución aún pueden diferir**

Usa comportamiento probado de prefijo de servidor/puerto/UID, dependencias y arquitectura. Una etiqueta mutable por sí sola no fija los bytes de la imagen.
</details>

## Preguntas de respuesta corta

8. ¿Por qué detener un notebook de GPU inactivo no garantiza un ahorro de costos inmediato?

<details>
<summary>Mostrar respuesta</summary>

Las solicitudes de Pod pueden liberarse, pero otras cargas de trabajo, PDB, los límites/políticas de interrupción de NodePool y la gestión de capacidad afectan la terminación del nodo. Los cargos de EC2 pueden continuar mientras el nodo permanezca en ejecución.
</details>

9. ¿En qué se diferencian RBAC, la autorización de Istio y NetworkPolicy para los notebooks?

<details>
<summary>Mostrar respuesta</summary>

RBAC gobierna las acciones de la API de Kubernetes. La autorización de Istio controla las solicitudes gestionadas por proxies y políticas configurados. NetworkPolicy gobierna el tráfico de red de Pod permitido cuando el CNI la aplica. Ninguna por sí sola garantiza el aislamiento de almacenamiento/IAM/aplicación.
</details>

---

[Volver a los materiales de aprendizaje](../../../ai-ml/kubeflow/03-notebooks.md)
