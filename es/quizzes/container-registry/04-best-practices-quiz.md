# Cuestionario sobre buenas prácticas de registros de contenedores

> **Última actualización**: 11 de septiembre de 2026

1. ¿Por qué se considera una buena práctica usar etiquetas inmutables en los registros de contenedores?
   - A) Reduce los costos de almacenamiento
   - B) Garantiza que una etiqueta siempre haga referencia al mismo contenido de imagen, lo que permite reproducir las implementaciones
   - C) Acelera la descarga de imágenes
   - D) Kubernetes lo exige

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Garantiza que una etiqueta siempre haga referencia al mismo contenido de imagen, lo que permite reproducir las implementaciones**

**Explicación:**
La inmutabilidad de etiquetas garantiza que, una vez que se publica una imagen con una etiqueta concreta, esta no pueda sobrescribirse con otra imagen. Fijar además el digest verificado identifica la imagen exacta. Conserva ese artefacto para poder revertir; la inmutabilidad de etiquetas por sí sola no garantiza universalmente la protección contra eliminaciones ni la procedencia. Es una práctica fundamental de seguridad de la cadena de suministro.

</details>

2. ¿Cuál es el riesgo principal de usar la etiqueta `:latest` en implementaciones de Kubernetes en producción?
   - A) La imagen no se almacenará en caché
   - B) Kubernetes no puede descargar imágenes con la etiqueta latest
   - C) El contenido real de la imagen es impredecible y puede cambiar entre implementaciones
   - D) Las etiquetas latest están obsoletas

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) El contenido real de la imagen es impredecible y puede cambiar entre implementaciones**

**Explicación:**
`latest` es una etiqueta normal; no selecciona automáticamente la imagen publicada más recientemente. A menos que una política de inmutabilidad la proteja, su destino cambia cuando alguien publica una imagen con esa etiqueta. Usarla en producción impide garantizar qué versión del código se está ejecutando, hace que las reversiones sean poco fiables y dificulta la depuración, ya que no se sabe qué código se implementó. La práctica recomendada es usar versiones semánticas o etiquetas basadas en SHA de Git.

</details>

3. ¿Cuál es el beneficio principal de configurar un mirror del registro o una caché pull-through?
   - A) Mejora el tiempo de compilación de imágenes
   - B) Reduce el tráfico de red externo, mejora la latencia de descarga y mitiga los límites de frecuencia
   - C) Actualiza las imágenes automáticamente
   - D) Proporciona análisis de vulnerabilidades

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Reduce el tráfico de red externo, mejora la latencia de descarga y mitiga los límites de frecuencia**

**Explicación:**
Los mirrors del registro y las cachés pull-through almacenan localmente copias de imágenes externas. Entre sus beneficios están la reducción de costos de ancho de banda y dependencias externas, descargas más rápidas desde la red local, la prevención de límites de frecuencia (como los de Docker Hub) y una mayor fiabilidad cuando los registros externos no están disponibles. Los fallos de caché y las actualizaciones siguen dependiendo del acceso al origen. Las redes desconectadas necesitan un mirror completo precargado y un proceso de actualización probado.

</details>

4. En una implementación de Kubernetes multirregional, ¿cuál es la estrategia recomendada de recuperación ante desastres para los registros de contenedores?
   - A) Usar un único registro global
   - B) Replicar las imágenes a registros de cada región y actualizar las implementaciones para que usen registros locales a la región
   - C) Almacenar todas las imágenes en S3 y descargarlas directamente
   - D) Usar caché de imágenes en cada nodo

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Replicar las imágenes a registros de cada región y actualizar las implementaciones para que usen registros locales a la región**

**Explicación:**
Para la recuperación ante desastres y la alta disponibilidad, las imágenes deben replicarse a registros de cada región de implementación. Así, una interrupción del registro regional no impide implementar en otras regiones, se reduce la latencia de red entre regiones al descargar imágenes y se obtiene independencia de la disponibilidad de registros externos. Las implementaciones deben hacer referencia al endpoint del registro local a la región.

</details>

5. ¿Qué método ayuda a optimizar los costos de almacenamiento del registro de contenedores?
   - A) Deshabilitar el análisis de imágenes
   - B) Implementar políticas de ciclo de vida para eliminar automáticamente las imágenes antiguas y sin usar
   - C) Usar imágenes base más grandes
   - D) Almacenar las imágenes sin comprimir

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Implementar políticas de ciclo de vida para eliminar automáticamente las imágenes antiguas y sin usar**

**Explicación:**
Las políticas de ciclo de vida automatizan la limpieza de imágenes según su antigüedad, cantidad o patrones de etiquetas. Esto evita que el almacenamiento crezca sin límite debido a iteraciones de desarrollo, versiones antiguas y experimentos abandonados. Combínalas con compilaciones de varias etapas e imágenes base mínimas para reducir el tamaño de cada imagen. La recolección periódica de basura libera el espacio ocupado por las capas de imagen eliminadas.

</details>

6. ¿En qué etapa de la canalización de CI/CD debe realizarse el análisis de vulnerabilidades de las imágenes de contenedor?
   - A) Solo en producción
   - B) Después de compilar, lo antes posible y antes de promover o implementar en producción
   - C) Solo durante auditorías de seguridad manuales
   - D) Después de implementar en Kubernetes

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Después de compilar, lo antes posible y antes de promover o implementar en producción**

**Explicación:**
Analiza la imagen localmente después de compilarla o analiza un digest en un registro de pruebas aislado antes de promoverla. Implementa el mismo artefacto que superó las comprobaciones y vuelve a analizarlo cuando aparezcan nuevos CVE. El análisis del registro y la verificación durante la admisión complementan el control de CI.

</details>

7. ¿Cómo pueden los controladores de admisión de Kubernetes mejorar la seguridad de los registros de contenedores?
   - A) Acelerando las descargas de imágenes
   - B) Validando que las imágenes procedan de registros permitidos y cumplan los requisitos de seguridad antes de crear el Pod
   - C) Actualizando imágenes automáticamente
   - D) Comprimiendo imágenes

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Validando que las imágenes procedan de registros permitidos y cumplan los requisitos de seguridad antes de crear el Pod**

**Explicación:**
Los controladores de admisión como Gatekeeper/OPA, Kyverno o las soluciones de proveedores de nube pueden aplicar políticas al momento de la implementación: exigir imágenes de registros aprobados, verificar las firmas de imágenes, comprobar que las imágenes hayan superado el análisis de vulnerabilidades y bloquear imágenes con etiquetas específicas como `:latest`. Esto proporciona una última barrera de seguridad antes de ejecutar las cargas de trabajo.

</details>

8. ¿Qué convención de nomenclatura se recomienda para las etiquetas de imágenes de contenedor?
   - A) UUID aleatorios
   - B) Versión semántica (v1.2.3) o SHA de confirmación de Git con caracteres de etiqueta válidos
   - C) Solo marcas de tiempo
   - D) Iniciales del desarrollador

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Versión semántica (v1.2.3) o SHA de confirmación de Git con caracteres de etiqueta válidos**

**Explicación:**
Una buena convención de etiquetas permite rastrear la imagen implementada hasta el código fuente. Las versiones semánticas (v1.2.3) indican la importancia de la versión. Los SHA de Git ofrecen trazabilidad exacta hasta la confirmación. Combinarlos (v1.2.3-abc1234) o agregar números de compilación (v1.2.3-build.456) proporciona un linaje completo. Esto facilita la depuración, las auditorías y las decisiones de reversión.

</details>

9. ¿Qué distingue una caché pull-through de un mirror completo del registro?
   - A) Una caché pull-through almacena de forma proactiva todas las imágenes; un mirror las obtiene a petición
   - B) Una caché pull-through obtiene y almacena las imágenes a petición; un mirror sincroniza proactivamente todas las imágenes
   - C) Son conceptos idénticos
   - D) Las cachés pull-through solo funcionan con Docker Hub

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Una caché pull-through obtiene y almacena las imágenes a petición; un mirror sincroniza proactivamente todas las imágenes**

**Explicación:**
Una caché pull-through solo almacena imágenes después de su primera solicitud y las conserva para descargas posteriores. Un mirror completo replica de forma proactiva todas las imágenes, o las seleccionadas, desde el registro de origen, independientemente de si se necesitan. Las cachés pull-through consumen menos almacenamiento, pero tienen latencia en el primer acceso; los mirrors garantizan que todas las imágenes estén disponibles localmente de inmediato.

</details>

10. En una estrategia con varios registros, ¿cuándo debería una organización considerar usar varios registros de contenedores?
    - A) Nunca; siempre basta con un registro
    - B) Cuando distintas categorías de imágenes tienen requisitos distintos de seguridad, cumplimiento, ubicación geográfica u operación
    - C) Solo cuando los costos son demasiado altos
    - D) Solo para copias de seguridad

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Cuando distintas categorías de imágenes tienen requisitos distintos de seguridad, cumplimiento, ubicación geográfica u operación**

**Explicación:**
Se justifican varios registros al separar imágenes públicas y privadas, cumplir requisitos normativos (por ejemplo, datos regulados en regiones específicas), optimizar la latencia de implementaciones globales, aislar las imágenes de producción de las de desarrollo o usar registros especializados para distintos fines (por ejemplo, ECR para cargas de trabajo de AWS y Harbor para instalaciones locales). El costo adicional es una mayor complejidad operativa.

</details>
