# Cuestionario de ApplicationSets de ArgoCD

Este cuestionario evalúa tu comprensión de los ApplicationSets de ArgoCD para la generación de aplicaciones con plantillas.

1. ¿Cuál es el propósito principal de un ApplicationSet?
   - A) Agrupar Applications existentes
   - B) Generar automáticamente múltiples Applications a partir de plantillas
   - C) Crear copias de seguridad de aplicaciones
   - D) Gestionar secretos de aplicaciones

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Generar automáticamente múltiples Applications a partir de plantillas**

**Explicación:**
Los ApplicationSets usan generators y plantillas para crear y gestionar automáticamente múltiples Applications de ArgoCD. Son ideales para desplegar aplicaciones en múltiples clusters o entornos.

</details>

2. ¿Qué generator usarías para crear Applications para cada cluster registrado en ArgoCD?
   - A) Git generator
   - B) List generator
   - C) Cluster generator
   - D) Matrix generator

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Cluster generator**

**Explicación:**
El Cluster generator genera automáticamente Applications para cada cluster registrado en ArgoCD. Puede usar selectores de etiquetas para dirigirse a clusters específicos.

</details>

3. ¿Qué hace el Git directory generator?
   - A) Crea Applications basadas en ramas de Git
   - B) Crea Applications para cada directorio en una ruta especificada
   - C) Sincroniza las credenciales de Git
   - D) Gestiona webhooks de Git

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Crea Applications para cada directorio en una ruta especificada**

**Explicación:**
El generador de directorios de Git recorre un directorio especificado en un repositorio de Git y crea una Application por cada directorio que coincida con los patrones glob y las reglas de exclusión configurados. Esto resulta útil en repositorios monolíticos.

</details>

4. ¿Cómo combinas múltiples generators en un ApplicationSet?
   - A) Usando el Merge generator
   - B) Usando el Matrix generator
   - C) Usando el Combine generator
   - D) Tanto A como B

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: D) Tanto A como B**

**Explicación:**
El generador Matrix crea combinaciones (producto cartesiano) de parámetros de exactamente dos generadores secundarios. El generador Merge combina parámetros de varios generadores y fusiona las entradas que coinciden. Ambos permiten combinar generadores.

</details>

5. ¿Cuál es el propósito del campo `goTemplate` en las plantillas de ApplicationSet?
   - A) Habilitar la programación en Go
   - B) Usar la sintaxis de plantillas de Go para una creación de plantillas más compleja
   - C) Compilar aplicaciones de Go
   - D) Habilitar la depuración

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Usar la sintaxis de plantillas de Go para una creación de plantillas más compleja**

**Explicación:**
Configurar `goTemplate: true` habilita la sintaxis de plantillas de Go, que ofrece condicionales, bucles y funciones, entre otras capacidades más potentes que la sustitución simple predeterminada. Cada campo de tipo cadena se evalúa por separado: las instrucciones de control no pueden abarcar varios campos YAML, y los campos booleanos u objetos no se pueden representar directamente mediante plantillas.

</details>

6. ¿Qué generator usarías para crear Applications basadas en pull requests?
   - A) Git generator
   - B) Pull Request generator
   - C) SCM Provider generator
   - D) Webhook generator

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Pull Request generator**

**Explicación:**
El Pull Request generator crea Applications para cada pull request abierto en un repositorio, lo que habilita entornos de vista previa para la revisión de código. Es compatible con GitHub, GitLab, Bitbucket y Gitea.

</details>

7. ¿Qué sucede de forma predeterminada cuando eliminas un ApplicationSet?
   - A) Nada, las Applications generadas permanecen
   - B) Se eliminan todas las Applications generadas
   - C) Las Applications quedan huérfanas
   - D) Se crea una copia de seguridad

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Se eliminan todas las Applications generadas**

**Explicación:**
De forma predeterminada, los ApplicationSets aplican una política de eliminación en cascada: al eliminar un ApplicationSet, también se eliminan todas las Applications que generó. `preserveResourcesOnDeletion` controla la eliminación de los recursos desplegados; no impide que la recolección de basura elimine los objetos Application.

</details>

8. ¿Cómo puedes evitar que un ApplicationSet elimine las Applications generadas cuando se elimina el ApplicationSet?
   - A) Eliminarlo con `kubectl delete applicationset NAME --cascade=orphan`
   - B) Configurar únicamente `syncPolicy.preserveResourcesOnDeletion: true`
   - C) Configurar la anotación de la política de eliminación
   - D) Reducir a cero las réplicas del controlador ApplicationSet

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A) Eliminarlo con `kubectl delete applicationset NAME --cascade=orphan`**

**Explicación:**
`--cascade=orphan` deja los objetos Application generados al eliminar su ApplicationSet padre. `preserveResourcesOnDeletion: true` evita añadir el finalizer que elimina los recursos desplegados; no protege los objetos Application de la recolección de basura. Si una Application huérfana conserva un finalizer, sus recursos aún pueden eliminarse cuando se borre esa Application más adelante.

</details>
