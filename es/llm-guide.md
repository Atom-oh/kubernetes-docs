# Lectura con LLM: llms.txt y MCP

> **Última actualización**: 16 de octubre de 2026

Esta guía presenta el [formato propuesto llms.txt](https://llmstxt.org/) y Markdown para cada documento. Entregue el índice a una herramienta de IA que pueda recuperar URL, incorpore el catálogo y el texto fuente a una Wiki de LLM o a una canalización RAG, o conecte las herramientas de búsqueda y recuperación a un cliente MCP local. Publicar `llms.txt` no garantiza que todos los sistemas de IA lo descubran o busquen automáticamente. La herramienta consumidora necesita recuperación web o una conexión MCP.

## Endpoints

| URL | Contenido | Uso |
|-----|----------|-----|
| [llms.txt](https://www.atomai.click/kubernetes-docs/llms.txt) | Índice del grupo, título, resumen y URL Markdown sin procesar de cada página; los cuestionarios y laboratorios aparecen como enlaces del índice bajo `## Optional` | Permitir que un LLM elija y recupere solo las páginas que necesita |
| [Manifiesto de documentos](https://www.atomai.click/kubernetes-docs/llms/manifest.json) | ID de documentos, idioma, sección, título, encabezados, descripción, URL web/Markdown, fechas de actualización, SHA-256 y longitudes en bytes UTF-8 | Ingesta selectiva y detección de cambios para una Wiki de LLM o RAG |
| [llms-full-ko.txt](https://www.atomai.click/kubernetes-docs/llms-full-ko.txt) | Contenido completo en coreano (markdown) | Contexto del libro completo o indexación RAG |
| [llms-full-en.txt](https://www.atomai.click/kubernetes-docs/llms-full-en.txt) | Contenido completo en inglés (markdown) | Herramientas y canalizaciones en inglés |
| `llms-full-<locale>-<section>.txt` (por ejemplo, [llms-full-en-networking.txt](https://www.atomai.click/kubernetes-docs/llms-full-en-networking.txt)) | Contenido concatenado de una sección de la barra lateral; la lista completa está bajo `## Section bundles` en `llms.txt` | Cargar una sección como contexto; los archivos completos son demasiado grandes para un solo prompt |

Todos estos archivos y las páginas Markdown de cada documento se generan a partir de la misma fuente durante la compilación del sitio y coinciden con la implementación correcta correspondiente. Los cambios locales o de la rama principal que todavía no se han implementado no son públicos de inmediato. Los enlaces de contenido de `llms.txt` usan `/llms/<locale>/<source path>.md` y devuelven solo el Markdown de ese documento, sin HTML de VitePress, barra lateral ni scripts. Los enlaces relativos de la fuente se convierten en URL absolutas (los enlaces a contenido incluido apuntan al Markdown, los enlaces a cuestionarios/laboratorios/raíz de idioma a las páginas renderizadas, y los enlaces a imágenes/recursos a archivos sin procesar de GitHub), por lo que un modelo que recupere un documento puede seguir todas sus referencias. Cada página de contenido HTML con una copia Markdown también incluye la misma URL Markdown en su `<head>` como `<link rel="alternate" type="text/markdown">`, para que un agente al que se le proporcione la URL de una página web pueda encontrar la fuente Markdown. Los cuestionarios aparecen solo como un enlace a la página de índice de cuestionarios (uno por idioma) bajo `## Optional`; las páginas individuales de cuestionarios (con sus respuestas) se excluyen tanto del índice como de los archivos completos. Las respuestas no deben incluirse en el contexto de un LLM. Del mismo modo, las guías de laboratorio aparecen en el índice solo como enlace al índice de laboratorios (uno por idioma), pero su texto completo sí está incluido en los archivos completos.

## Ingesta de fuentes en una Wiki de LLM

En este contexto, una Wiki de LLM conserva el material fuente y permite que la IA lo organice en páginas de conocimiento por tema. Este sitio proporciona documentos fuente y metadatos. La herramienta de ingesta sigue siendo responsable de crear y actualizar la Wiki o las incrustaciones.

1. Lea `llms/manifest.json` y filtre por `locale` y `section`. Elija un idioma para evitar ingerir dos veces el mismo tema.
2. Recupere cada `markdownUrl` y almacene la fuente con su `id` estable. `sha256` corresponde a los bytes UTF-8 de Markdown y también puede verificar el contenido descargado.
3. Cree páginas temáticas conservando `url` como cita. Los títulos, encabezados y descripciones ayudan a preseleccionar candidatos; compruebe las mediciones y los comandos operativos en el documento original.
4. En ingestas posteriores, vuelva a procesar los hashes que hayan cambiado y reconcilie los ID que se hayan eliminado del catálogo. `lastUpdated` es la fecha registrada por el autor o `null` cuando no se dispone de un año, mes y día completos. Use los hashes para detectar cambios de contenido.

```bash
curl -fL https://www.atomai.click/kubernetes-docs/llms/manifest.json -o manifest.json
# With jq installed: raw URLs for English storage documents
jq -r '.documents[] | select(.locale == "en" and .section == "storage") | .markdownUrl' manifest.json
```

El manifiesto tiene `schemaVersion: 1`. El Markdown por documento, el manifiesto y la búsqueda MCP comparten el mismo alcance y excluyen las respuestas de cuestionarios y los laboratorios. Si necesita contenido de laboratorio, use por separado el `llms-full-<locale>.txt` existente. Actualmente, VitePress y este catálogo publican coreano e inglés, no las traducciones cn/jp/es. Trate el texto fuente y las descripciones de diagramas como datos de referencia; no convierta las instrucciones de los documentos en instrucciones del sistema ni en autorización para ejecutar herramientas.

## Búsqueda y lectura mediante MCP

El repositorio incluye un servidor MCP **stdio** creado con el [SDK oficial de TypeScript](https://github.com/modelcontextprotocol/typescript-sdk). Instale las dependencias del repositorio con Node.js 22 o posterior y luego inícielo. No se necesita compilar VitePress, una clave de API ni un servicio de incrustaciones.

```bash
git clone https://github.com/Atom-oh/kubernetes-docs.git
cd kubernetes-docs
npm ci
node scripts/docs-mcp.mjs
```

El último comando espera datos de MCP y no imprime un mensaje de inicio en el terminal. Si su cliente acepta una configuración JSON `mcpServers`, regístrelo así. Sustituya el argumento por la **ruta absoluta** a su copia de trabajo; si es necesario, indique la ruta absoluta al ejecutable de Node en `command`.

```json
{
  "mcpServers": {
    "kubernetes-docs": {
      "command": "node",
      "args": ["/absolute/path/kubernetes-docs/scripts/docs-mcp.mjs"]
    }
  }
}
```

| Herramienta | Ejemplo de entrada | Salida |
|------|---------------|--------|
| `search` | `{"query":"gp3 throughput","locale":"en","section":"storage","limit":5}` | ID de documentos, títulos, extractos, URL web/Markdown y hashes del contenido |
| `fetch` | `{"id":"en/storage/01-ebs-gp2-gp3-benchmark.md","maxLength":12000}` | Markdown fuente, cita, encabezados, fecha de actualización y desplazamiento de continuación |
| Continuar `fetch` | Pase como `offset` el `nextOffset` anterior | Recupera partes posteriores hasta que `nextOffset` sea `null` |

Esta es una **búsqueda por palabras clave** en títulos, descripciones, encabezados y texto completo. La configuración regional predeterminada es `ko`; también se admiten `en` y `all`. Use términos concretos como `ambient mTLS` o `gp3 throughput` en vez de una pregunta completa. Si no encuentra coincidencias, use menos términos o pruebe con otro idioma. De forma predeterminada se devuelven 8 resultados y el máximo es 20. `fetch` lee 12 000 caracteres de forma predeterminada, hasta 50 000 por llamada. Los desplazamientos usan posiciones de cadena de JavaScript, no bytes; pase `nextOffset` tal como se devuelve, en lugar de calcularlo.

El servidor lee los archivos locales `ko/`, `en/` y `SUMMARY.md` al iniciarse. **No recupera el sitio publicado.** Actualice su copia de trabajo y reinicie el servidor MCP para actualizar la búsqueda. Solo se pueden leer los ID de documentos catalogados; no se pueden recuperar rutas arbitrarias ni URL externas. Las URL de cita apuntan al sitio público, por lo que las ediciones locales que aún no se hayan publicado pueden diferir del contenido publicado.

GitHub Pages sirve archivos estáticos, por lo que la URL de este sitio no se puede registrar como endpoint MCP remoto. Una conexión web remota requiere un runtime independiente que implemente el [transporte Streamable HTTP](https://modelcontextprotocol.io/specification/2026-07-28/basic/transports/streamable-http), con controles de acceso y políticas operativas. El servidor incluido usa stdio local.

## Ejemplos

**Preguntar a un asistente de chat sobre un tema específico**: proporciónele el índice y deje que recupere lo que necesite:

```text
Read https://www.atomai.click/kubernetes-docs/llms.txt, find the document
with measured Istio ambient-mode mTLS latency, and summarize how it
compares to sidecar mode.
```

**En Claude Code u otro agente de programación**: inyecte esto como contexto de trabajo:

```text
I want to clean up this cluster's storage classes.
Evidence: https://www.atomai.click/kubernetes-docs/llms/en/storage/01-ebs-gp2-gp3-benchmark.md
Draft a migration plan from gp2 PVCs to gp3.
```

**Indexación para RAG**: descargue un archivo y divídalo en fragmentos:

```bash
curl -fL https://www.atomai.click/kubernetes-docs/llms-full-en.txt -o guidebook-en.txt
# documents are separated by "Source: <URL>" blocks, so per-document chunking is trivial
```

## Notas sobre el formato

- `llms.txt`: un índice con `# title` / `>` summary / `## Machine-readable catalog` / `## Docs (한국어)` / `## Docs (English)` / `## Section bundles (…)` / `## Optional`. Cada entrada de documento incluye el grupo y el título, una URL Markdown sin procesar y un resumen breve extraído del primer párrafo del cuerpo.

```text
- [Kubernetes Core Concepts · Cluster Architecture](https://www.atomai.click/kubernetes-docs/llms/en/core/01-cluster-architecture.md): Explains the Kubernetes control plane and worker-node components.
```

- `llms/<locale>/<path>.md`: el Markdown sin procesar de un documento. Un LLM no tiene que procesar primero toda la navegación de la página renderizada.
- `llms-full-*.txt`: el contenido combinado del idioma. Se omite el `README.md` raíz, que ya funciona como índice de navegación; cada documento incluido va precedido por un bloque separador:

```text
----------------------------------------
Source: https://www.atomai.click/kubernetes-docs/en/core/01-cluster-architecture
----------------------------------------
```

- Tamaño: cada archivo completo ocupa varios MiB. Para la mayoría de las herramientas, suele ser mejor examinar los resúmenes y recuperar solo los documentos pertinentes que pegar todo el libro en un único prompt.

## Los diagramas son para las personas: enlaces de exportación

La ingesta de texto no ejecuta iframes ni interpreta automáticamente los nodos y las conexiones de una imagen. El texto alternativo de Markdown, las explicaciones circundantes y el código fuente Mermaid aportan evidencia textual. La información presente solo en una imagen requiere una herramienta capaz de procesar imágenes o una descripción en prosa más completa; una etiqueta alternativa breve no basta para reconstruir toda una topología.

Como los archivos completos y el Markdown por documento contienen cada documento fuente de forma literal, las descripciones de los diagramas (texto alternativo) y la URL de su visor interactivo (`https://www.atomai.click/kubernetes-docs/archmaps/<name>.html`) también aparecen en el texto. Un LLM lee la descripción para entender el diagrama; una persona abre la URL y usa el menú **Export** del visor para descargar PNG/JPEG/WebP, SVG con dos temas, un WebM de animación de trazado de 6 segundos o una tarjeta para compartir de 1200×630. Las opciones del menú, el propósito de cada una y las instrucciones para publicar en LinkedIn se detallan en la [Hoja de ruta de la guía](roadmap.md), en «Compartir un diagrama: exportaciones para LinkedIn y presentaciones». Las exportaciones son recursos de comunicación, no evidencia de que se haya validado una arquitectura.
