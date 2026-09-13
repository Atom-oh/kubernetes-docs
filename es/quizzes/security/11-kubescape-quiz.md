# Cuestionario de Kubescape

> **Última actualización**: September 13, 2026

## Preguntas

<span id="_1-what-is-kubescape-s-project-status-in-the-cncf"></span>

### 1. ¿Cuál es el nivel actual de madurez de Kubescape en CNCF?

- A) Graduated
- B) Incubating
- C) Sandbox
- D) Archived

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Incubating**

Kubescape se unió a CNCF el 13 de diciembre de 2022 y pasó a Incubating el 13 de enero de 2025. Esto no garantiza la seguridad ni la disponibilidad de una instalación individual.

</details>

<span id="_2-which-security-frameworks-does-kubescape-support-for-compliance-scanning"></span>

### 2. ¿Cómo se deben verificar los nombres de los frameworks y los recuentos de controles?

- A) Usar siempre alias antiguos de CIS
- B) Registrar las versiones del binario/de la política e inspeccionar la lista real
- C) Los recuentos de controles de NSA nunca cambian
- D) Aprobar un análisis SOC2 completa la certificación

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Registrar las versiones del binario/de la política e inspeccionar la lista real**

Use kubescape list frameworks y list controls --framework NSA. La instantánea revisada de NSA contiene 26 controles, cuya aplicabilidad se determina mediante la entrada. Conserve los hashes de las políticas al comparar puntuaciones.

</details>

<span id="_3-what-is-the-correct-cli-syntax-to-scan-a-kubernetes-cluster-with-kubescape"></span>

### 3. ¿Qué ocurre cuando se omite un destino de archivo local de kubescape scan?

- A) Siempre falla
- B) Puede analizar el clúster del kubeconfig actual
- C) Siempre analiza únicamente archivos locales
- D) Siempre realiza una ejecución de prueba

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Puede analizar el clúster del kubeconfig actual**

CI debe pasar un archivo local explícito existente y rechazar destinos vacíos o inexistentes. --keep-local, una caché aislada y una política fijada no sustituyen la comprobación del alcance de entrada.

</details>

<span id="_4-what-is-the-key-difference-between-kubescape-operator-and-cli-modes"></span>

### 4. ¿Qué afirmación distingue correctamente el funcionamiento del Operator y de la CLI?

- A) El Operator solo proporciona una GUI
- B) La CLI gestiona análisis explícitos/ad hoc; el Operator ejecuta capacidades continuas/programadas habilitadas
- C) Instalar el Operator demuestra que todas las funcionalidades de tiempo de ejecución funcionan
- D) Las imágenes de la CLI y del Operator siempre tienen la misma versión

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) La CLI gestiona análisis explícitos/ad hoc; el Operator ejecuta capacidades continuas/programadas habilitadas**

Chart 1.40.4 genera la imagen del scanner 4.0.13, mientras que la CLI local probada es 4.0.14. El alcance y los permisos de nodo/imagen/tiempo de ejecución/remediación requieren elecciones y validación independientes.

</details>

<span id="_5-how-does-kubescape-calculate-risk-scores-for-controls"></span>

### 5. ¿Cómo se relacionan score y complianceScore?

- A) Siempre son iguales
- B) Siempre suman 100
- C) Son agregados independientes en el esquema de resultados
- D) Ambos son valores CVSS promedio

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Son agregados independientes en el esquema de resultados**

El Pod inseguro sintético produjo compliance 55 y score 62.5. Lea summaryDetails.complianceScore y summaryDetails.score. Estos valores locales no miden la seguridad de un clúster real.

</details>

<span id="_6-which-flag-enforces-a-compliance-threshold-in-ci-cd-pipelines"></span>

### 6. ¿Qué ocurre con compliance 55 y --compliance-threshold 56?

- A) Se aprueba porque este es un límite máximo de riesgo
- B) Sale con 1 porque no se alcanza el cumplimiento mínimo
- C) Siempre sale con 2
- D) Es equivalente a la puerta actual --fail-threshold 0

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Sale con 1 porque no se alcanza el cumplimiento mínimo**

El mismo fixture devolvió la salida 0 con el umbral 55 y la salida 1 con 56. La versión 4.0.14 acepta el obsoleto --fail-threshold, pero ignora su valor; no lo use como puerta.

</details>

<span id="_7-how-does-kubescape-differ-from-kube-bench"></span>

### 7. ¿Cuál es una base sólida para comparar kube-bench y Kubescape?

- A) Suponer que uno reemplaza cada comprobación basándose en su nombre
- B) Comparar el alcance y el acceso reales de nodo/CIS frente a workload/configuración
- C) Ambos pueden inspeccionar cada ajuste del control plane sin acceso
- D) Una aprobación de Kubescape es un certificado CIS

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Comparar el alcance y el acceso reales de nodo/CIS frente a workload/configuración**

Los control planes administrados de EKS, los manifests locales y el acceso a archivos del nodo ofrecen visibilidad diferente. Distinga las comprobaciones no disponibles/no evaluadas de las aprobadas y seleccione las herramientas en consecuencia.

</details>

<span id="_8-what-feature-does-kubescape-provide-for-rbac-security-analysis"></span>

### 8. ¿Qué afirmación sobre los controles RBAC es correcta?

- A) C-0036 siempre comprueba RBAC con comodines
- B) Un RoleBinding concede acceso en todos los namespaces
- C) Verificar los IDs/nombres de controles actuales y el alcance de la recopilación
- D) scan rbac es un subcomando independiente en la CLI revisada

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Verificar los IDs/nombres de controles actuales y el alcance de la recopilación**

El bundle revisado asigna C-0035 a Administrative Roles y C-0036/0039 a comprobaciones de admisión de validación/mutación. Los RoleBindings tienen ámbito de namespace; el análisis estático no valida automáticamente IAM externo.

</details>

<span id="_9-which-vulnerability-scanner-does-kubescape-integrate-with-for-image-scanning"></span>

### 9. ¿Qué afirmación distingue correctamente los análisis de imagen y de host?

- A) El análisis de host solo comprueba CVE de imagen
- B) Los análisis explícitos de imagen necesitan acceso al registry/DB; los análisis de host tienen un alcance independiente
- C) Grype solo genera SBOM
- D) Las versiones de imagen/plataforma/base de datos no importan

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Los análisis explícitos de imagen necesitan acceso al registry/DB; los análisis de host tienen un alcance independiente**

La CLI usa Grype y Syft; el kubevuln del Operator tiene versiones independientes. Los análisis de host pueden necesitar recursos o permisos adicionales. En esta auditoría no se ejecutaron descargas de imágenes ni análisis de host.

</details>

<span id="_10-how-does-kubescape-handle-control-exceptions"></span>

### 10. ¿Cuáles son los formatos correctos de excepción para la CLI y dentro del clúster?

- A) La CLI consume directamente un ConfigMap arbitrario
- B) Distinguir alertOnly en un array JSON de CLI de alert_only en SecurityException v1beta1
- C) Cada anotación ignore es automáticamente una excepción
- D) Registrar una excepción remedia el problema

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Distinguir alertOnly en un array JSON de CLI de alert_only en SecurityException v1beta1**

En la prueba, alertOnly reconoció un fallo sin cambiar compliance. exclude-controls cambia el denominador de evaluación. Realice el seguimiento de la propiedad, el alcance, la caducidad y la revisión por separado de la remediación.

</details>

## Cálculo de puntuación

- 9–10: Comprensión sólida
- 7–8: Repase los conceptos de alcance/puerta no acertados
- 6 o menos: Revise la guía y los ejemplos probados

## Documentación relacionada

- [Kubescape](../../security/11-kubescape.md)
