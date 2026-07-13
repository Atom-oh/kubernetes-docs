# Cuestionario sobre las características y la hoja de ruta de versiones de Kubernetes

1. ¿Cuál es la cadencia de lanzamientos de Kubernetes?
   - A) Una vez al año con características principales
   - B) Aproximadamente 3 lanzamientos al año, cada ~4 meses
   - C) Lanzamientos de parches mensuales con lanzamientos de características trimestrales
   - D) Dos veces al año, alineados con AWS re:Invent y Summit

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Aproximadamente 3 lanzamientos al año, cada ~4 meses**

**Explicación:**
Kubernetes sigue un ciclo de lanzamiento de ~4 meses, produciendo aproximadamente 3 lanzamientos de versiones menores por año. Cada lanzamiento pasa por una congelación de mejoras, una congelación de código y una fase de candidato de lanzamiento. Lanzamientos recientes: 1.33 (abr. 2025), 1.34 (ago. 2025), 1.35 (dic. 2025), 1.36 (abr. 2026). Luego, cada versión se mantiene con lanzamientos de parches durante aproximadamente 14 meses.

</details>

---

2. ¿Cuál es la diferencia entre EKS Standard Support y Extended Support?
   - A) Standard es gratis, Extended requiere una licencia Enterprise
   - B) Standard dura 14 meses a $0.10/cluster/hour; Extended agrega 12 meses más a $0.60/cluster/hour
   - C) Standard admite 3 versiones, Extended admite todas las versiones
   - D) Standard proporciona parches mensualmente, Extended proporciona parches semanalmente

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Standard dura 14 meses a $0.10/cluster/hour; Extended agrega 12 meses más a $0.60/cluster/hour**

**Explicación:**
Cada versión de Kubernetes en EKS recibe 14 meses de Standard Support ($0.10/cluster/hour), seguidos de 12 meses de Extended Support ($0.60/cluster/hour — 6 veces el costo). El soporte total es de 26 meses por versión. Extended Support está habilitado de forma predeterminada. Cuando una versión sale de Extended Support, los clusters se actualizan automáticamente. Esta diferencia de precios incentiva mantenerse en versiones compatibles.

</details>

---

3. ¿En qué versión de Kubernetes los Sidecar Containers llegaron a GA?
   - A) 1.28 (cuando se introdujeron por primera vez como alpha)
   - B) 1.31
   - C) 1.33
   - D) 1.35

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) 1.33**

**Explicación:**
Los Sidecar Containers nativos (KEP-753) siguieron esta ruta de graduación: alpha en v1.28 (ago. 2023), beta en v1.29 (dic. 2023), GA en v1.33 (abr. 2025). Los sidecars se definen como init containers con `restartPolicy: Always`, lo que garantiza que se inicien antes que los containers de aplicación, se ejecuten durante todo el ciclo de vida del Pod y terminen después de los containers principales, resolviendo el problema histórico de los "zombie sidecar" en Jobs.

</details>

---

4. ¿Qué es la característica In-Place Pod Resize y cuándo alcanzó GA?
   - A) Capacidad de cambiar las réplicas de Pod sin redespliegue; GA en 1.30
   - B) Capacidad de modificar solicitudes y límites de CPU/memoria en Pods en ejecución sin reinicio; GA en 1.35
   - C) Capacidad de redimensionar PersistentVolumes en línea; GA en 1.31
   - D) Capacidad de cambiar imágenes de container en Pods en ejecución; GA en 1.34

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Capacidad de modificar solicitudes y límites de CPU/memoria en Pods en ejecución sin reinicio; GA en 1.35**

**Explicación:**
In-Place Pod Resize (KEP-1287) hace que las solicitudes/límites de CPU y memoria sean mutables en Pods en ejecución. Graduación: alpha en v1.27, beta en v1.33, GA en v1.35 (dic. 2025). A partir de v1.33, las modificaciones usan el subresource `/resize`. El campo `resizePolicy` controla si se necesita reiniciar un container por tipo de recurso. Esta característica es transformadora para la integración con VPA, ya que permite ajustar correctamente los recursos sin interrumpir el Pod.

</details>

---

5. ¿Qué cambio importante ocurrió con Dynamic Resource Allocation (DRA) en Kubernetes 1.31?
   - A) DRA quedó obsoleto y fue reemplazado por Device Plugins v2
   - B) Classic DRA fue eliminado; solo permaneció Structured Parameters DRA (que más tarde alcanzó GA en 1.34)
   - C) DRA pasó directamente de alpha a GA
   - D) DRA agregó soporte para dispositivos de red junto con GPUs

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Classic DRA fue eliminado; solo permaneció Structured Parameters DRA (que más tarde alcanzó GA en 1.34)**

**Explicación:**
DRA pasó por un rediseño importante. Classic DRA (KEP-3063, alpha desde v1.26) usaba parámetros opacos del proveedor sobre los que el scheduler y el cluster autoscaler no podían razonar. Structured Parameters DRA (KEP-4381) lo reemplazó con un formato nativo de Kubernetes que usa objetos `ResourceSlice`. En v1.31, classic DRA fue eliminado por completo. Structured DRA progresó: beta en v1.32, GA en v1.34. Esto es crítico para la planificación de GPUs/aceleradores en cargas de trabajo de AI/ML.

</details>

---

6. ¿Qué característica llegó a GA en Kubernetes 1.30 y habilita el control de admisión declarativo sin webhooks?
   - A) OPA Gatekeeper v4
   - B) Kyverno Native Policies
   - C) ValidatingAdmissionPolicy usando expresiones CEL
   - D) Aplicación de Pod Security Standards

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) ValidatingAdmissionPolicy usando expresiones CEL**

**Explicación:**
ValidatingAdmissionPolicy (KEP-3488) proporciona validación en proceso usando expresiones de Common Expression Language (CEL), eliminando la necesidad de servidores webhook externos. Graduación: alpha en v1.26, beta en v1.28, GA en v1.30 (abr. 2024). Usa tres tipos de recursos: ValidatingAdmissionPolicy (reglas), ValidatingAdmissionPolicyBinding (vinculación a recursos) y CRDs de parámetros opcionales. Esto reduce la latencia, la complejidad y los dominios de fallo en comparación con el control de admisión basado en webhooks.

</details>

---

7. ¿Qué es KYAML y cuál es su estado actual?
   - A) Un linter de YAML para Kubernetes; GA en 1.35
   - B) Un subconjunto de YAML más seguro y menos ambiguo para Kubernetes que usa formato estricto; beta en 1.35, habilitado de forma predeterminada
   - C) Una herramienta convertidora de YAML a JSON; alpha en 1.34
   - D) Un esquema de validación de manifiestos de Kubernetes; estable desde 1.30

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Un subconjunto de YAML más seguro y menos ambiguo para Kubernetes que usa formato estricto; beta en 1.35, habilitado de forma predeterminada**

**Explicación:**
KYAML es un subconjunto de YAML más estricto, diseñado específicamente para Kubernetes, que elimina las famosas ambigüedades de YAML. Usa llaves ({}) para mapas, corchetes ([]) para listas y comillas dobles para todas las cadenas. Introducido como alpha en v1.34, llegó a beta en v1.35 (dic. 2025) y está habilitado de forma predeterminada. Se puede deshabilitar con `KUBECTL_KYAML=false`. Esto aborda problemas históricos como el "Norway problem" (NO interpretado como booleano falso) en YAML.

</details>

---

8. ¿Cuál es la estrategia recomendada de planificación de actualización de versiones para clusters de EKS?
   - A) Omitir versiones para minimizar la frecuencia de actualización (por ejemplo, 1.29 → 1.33)
   - B) Actualizar una versión menor a la vez, probar feature gates en staging, verificar la compatibilidad de API y la alineación de add-ons antes de producción
   - C) Usar siempre la versión más reciente y confiar en Extended Support para rollback
   - D) Esperar hasta que una versión alcance Extended Support antes de actualizar para garantizar la estabilidad

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Actualizar una versión menor a la vez, probar feature gates en staging, verificar la compatibilidad de API y la alineación de add-ons antes de producción**

**Explicación:**
EKS requiere actualizaciones secuenciales de versiones menores (1.33 → 1.34 → 1.35; no se admite omitir versiones). Mejores prácticas: (1) Probar primero los nuevos feature gates y cambios de API en entornos de staging, (2) verificar la compatibilidad de add-ons con la versión objetivo, (3) ejecutar `kubectl convert` para comprobar APIs obsoletas, (4) actualizar primero el control plane, luego los add-ons y después los node groups. Mantenerse en Standard Support evita el aumento de costo de 6 veces de Extended Support y garantiza acceso a los parches de seguridad más recientes.

</details>
