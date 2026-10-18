# Cuestionario sobre lectura con LLM: llms.txt

1. ¿Qué contiene el archivo `llms.txt` de esta guía y para qué sirve?
   - A) Todo el contenido en coreano en formato Markdown, para pegarlo íntegro en una ventana de contexto
   - B) Un índice del título, resumen y URL Markdown sin procesar de cada página de contenido, para que un LLM elija y obtenga solo las páginas que necesita
   - C) Una colección de claves de respuestas de cuestionarios, para la calificación automatizada
   - D) Un paquete de PNG de diagramas, para crear diapositivas

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Un índice del título, resumen y URL Markdown sin procesar de cada página de contenido, para que un LLM elija y obtenga solo las páginas que necesita**

**Explicación:**
En la tabla de endpoints, `llms.txt` es un índice del grupo, el título, el resumen y la URL Markdown sin procesar de cada página de contenido. Sirve para que un LLM elija y obtenga únicamente las páginas que necesita. Cada enlace de contenido usa `/llms/<locale>/<source path>.md`, por lo que el modelo lee el origen del documento sin la barra lateral ni los scripts de la página renderizada. El contenido Markdown completo está en los archivos separados `llms-full-ko.txt` / `llms-full-en.txt`. Los cuestionarios y laboratorios no se enumeran página por página; `## Optional` contiene un enlace al índice de cuestionarios y otro al de laboratorios para cada idioma.

</details>

2. ¿En qué idiomas se publican los archivos de contenido completo?
   - A) Solo coreano (`llms-full-ko.txt`)
   - B) Coreano e inglés: dos archivos (`llms-full-ko.txt`, `llms-full-en.txt`)
   - C) Cinco idiomas: coreano, inglés, chino, japonés y español
   - D) Un único `llms-full.txt` con todos los idiomas combinados

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Coreano e inglés: dos archivos (`llms-full-ko.txt`, `llms-full-en.txt`)**

**Explicación:**
Los archivos completos para cada idioma son `llms-full-ko.txt` y `llms-full-en.txt`. El índice, el manifiesto, los paquetes por sección y el Markdown de cada documento son endpoints adicionales disponibles en `https://www.atomai.click/kubernetes-docs/`. Se recomienda el archivo coreano para «contexto del libro completo o indexación RAG» y el inglés para «herramientas y canalizaciones en inglés».

</details>

3. ¿Cómo se generan `llms.txt` y los archivos completos cuando la implementación del sitio se completa correctamente?
   - A) El autor vuelve a subir a mano los tres archivos después de cada edición
   - B) Un flujo semanal de resúmenes de noticias los actualiza
   - C) La compilación del sitio los genera a partir de los mismos orígenes y los implementa conjuntamente
   - D) El servidor convierte los documentos sobre la marcha para cada solicitud del LLM

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) La compilación del sitio los genera a partir de los mismos orígenes y los implementa conjuntamente**

**Explicación:**
La página indica: «La compilación del sitio los genera a partir del mismo origen y los implementa juntos, así que siempre coinciden con el contenido publicado». Son artefactos del proceso de implementación, no cargas manuales ni conversiones a petición.

</details>

4. ¿Cómo se tratan los documentos de cuestionarios en `llms.txt` y los archivos completos?
   - A) Todas las páginas de cuestionarios aparecen en el índice y en los archivos completos, incluidas las claves de respuestas
   - B) Solo se enlaza la página del índice de cuestionarios (un enlace por idioma), en `## Optional` de `llms.txt`; se excluyen tanto del índice como de los archivos completos las páginas individuales y sus claves de respuestas
   - C) Todas las páginas individuales de cuestionarios aparecen en el índice, pero se excluyen de los archivos completos
   - D) Las páginas de cuestionarios aparecen en los archivos completos, pero se excluyen del índice

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Solo se enlaza la página del índice de cuestionarios (un enlace por idioma), en `## Optional` de `llms.txt`; se excluyen tanto del índice como de los archivos completos las páginas individuales y sus claves de respuestas**

**Explicación:**
La página dice: «En `llms.txt`, los cuestionarios aparecen únicamente como un enlace a la página del índice de cuestionarios (uno por idioma), dentro de `## Optional`; se excluyen tanto del índice como de los archivos completos las páginas individuales de cuestionarios (con sus claves de respuestas), porque las claves no corresponden al contexto de un LLM». Así, un LLM puede descubrir que existen cuestionarios y dónde está el índice de cada idioma, pero ni el índice plano ni los archivos del libro completo incluyen ninguna página de cuestionario ni sus respuestas. Los laboratorios se tratan de forma distinta: en `llms.txt` también aparecen solo mediante un enlace al índice, pero su texto completo sí se incluye en los archivos completos.

</details>

5. Dado el tamaño de los archivos completos, ¿qué forma de usarlos con un LLM recomienda la página?
   - A) Pegar el archivo completo de varios MiB en cada prompt; es el método más preciso
   - B) Dividir el archivo completo en varias partes y adjuntarlas todas cada vez
   - C) Dirigir el modelo al índice y dejar que obtenga páginas específicas; funciona mejor con la mayoría de las herramientas
   - D) Entregar solo las URL del visor de diagramas y dejar que el LLM deduzca el resto

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Dirigir el modelo al índice y dejar que obtenga páginas específicas; funciona mejor con la mayoría de las herramientas**

**Explicación:**
La nota «Tamaño» indica que los archivos completos ocupan varios MiB y que «con la mayoría de las herramientas funciona mejor dirigir el modelo al índice y dejar que obtenga páginas específicas que pegar el libro entero en un solo prompt». El primer ejemplo de prompt («Lee …/llms.txt, busca el documento … y resúmelo …») sigue exactamente este patrón. Los archivos completos son adecuados para casos como descargar el archivo entero y dividirlo en fragmentos para la indexación RAG.

</details>

6. ¿Por qué se describe como trivial dividir `llms-full-*.txt` por documento?
   - A) Cada documento se almacena como una entrada ZIP independiente
   - B) Antes de cada documento hay un bloque separador que contiene `Source: <URL>`
   - C) Cada documento se corta a una longitud fija de 4,096 caracteres
   - D) Los documentos se almacenan uno por elemento en una matriz JSON

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Antes de cada documento hay un bloque separador que contiene `Source: <URL>`**

**Explicación:**
En «Notas de formato» se explica que «antes de cada documento hay un bloque separador»: una línea de guiones, una URL con formato similar a `Source: https://www.atomai.click/kubernetes-docs/en/core/01-cluster-architecture` y otra línea de guiones. El comentario del ejemplo de RAG lo reitera: «los documentos están separados por bloques `Source: <URL>`, así que dividirlos por documento es trivial». El archivo es texto Markdown sin formato, no un ZIP ni JSON.

</details>

7. ¿Cómo describe la página el uso de la información de diagramas incluida en los archivos completos por parte de un LLM y una persona?
   - A) El LLM analiza directamente la imagen PNG y la persona lee el texto alternativo
   - B) El LLM lee la descripción del diagrama (texto alternativo) para entenderlo; la persona abre la URL del visor interactivo y usa el menú Export para descargar PNG/JPEG/WebP, SVG, WebM o una Share Card
   - C) Ni el LLM ni una persona pueden obtener información alguna sobre los diagramas de los archivos completos
   - D) El LLM genera una animación WebM desde la URL del visor y se la entrega a la persona

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) El LLM lee la descripción del diagrama (texto alternativo) para entenderlo; la persona abre la URL del visor interactivo y usa el menú Export para descargar PNG/JPEG/WebP, SVG, WebM o una Share Card**

**Explicación:**
La sección «Los diagramas son para las personas: enlaces de exportación» explica que, como los archivos completos incluyen literalmente el Markdown de cada documento, el texto contiene el texto alternativo de cada diagrama y su URL del visor (`https://www.atomai.click/kubernetes-docs/archmaps/<name>.html`). «Un LLM de texto usa el texto alternativo y la prosa circundante, pero no puede inferir de forma fiable los nodos o aristas que solo aparecen en la imagen; una persona abre la URL y usa el menú **Export** del visor para descargar PNG/JPEG/WebP, un SVG de tema dual, un WebM de animación de trazas de 6 segundos o una Share Card de 1200×630». Las instrucciones para cada elemento están en la sección «Compartir un diagrama» de la hoja de ruta de la guía.

</details>

8. ¿Qué límite establece la página para los archivos de diagramas exportados desde el visor (PNG, SVG, WebM, Share Card)?
   - A) Las exportaciones se pueden usar como prueba formal de que se validó la arquitectura
   - B) Las exportaciones son materiales de comunicación, no pruebas de que se haya validado la arquitectura
   - C) Las exportaciones son solo para LLM y las personas no pueden abrirlas
   - D) Las exportaciones son el formato oficial de publicación del documento y reemplazan el HTML de origen

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Las exportaciones son materiales de comunicación, no pruebas de que se haya validado la arquitectura**

**Explicación:**
La sección termina con: «Las exportaciones son materiales de comunicación, no pruebas de que se haya validado una arquitectura». Exportar un diagrama sirve para compartirlo, por ejemplo, en publicaciones de LinkedIn o diapositivas de una presentación; la existencia de la imagen no dice nada sobre si se validó la arquitectura que representa.

</details>
