# Cuestionario de Kubescape

Pon a prueba tu comprensión de la gestión de postura de seguridad con Kubescape con las siguientes preguntas.

---

## Preguntas

### 1. ¿Cuál es el estado del proyecto Kubescape en la CNCF?

- A) Proyecto Graduated
- B) Proyecto Incubating
- C) Proyecto Sandbox
- D) No es un proyecto de la CNCF

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Proyecto Sandbox**

**Explicación:**
Kubescape fue aceptado como proyecto CNCF Sandbox en 2022. Fue desarrollado originalmente por ARMO y donado a la CNCF. Como proyecto Sandbox, es un proyecto en etapa inicial que la CNCF considera con potencial de crecimiento.

</details>

---

### 2. ¿Qué frameworks de seguridad admite Kubescape para escaneos de cumplimiento?

- A) Solo NSA-CISA
- B) Solo CIS Benchmarks
- C) NSA-CISA, CIS Benchmarks y MITRE ATT&CK
- D) Solo OWASP y PCI-DSS

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) NSA-CISA, CIS Benchmarks y MITRE ATT&CK**

**Explicación:**
Kubescape admite múltiples frameworks de seguridad:

```bash
# Scan with NSA-CISA framework
kubescape scan framework nsa

# Scan with CIS Kubernetes Benchmark
kubescape scan framework cis-v1.23-t1.0.1

# Scan with MITRE ATT&CK
kubescape scan framework mitre
```

- **NSA-CISA**: Kubernetes Hardening Guide de agencias gubernamentales de EE. UU.
- **CIS**: Center for Internet Security Kubernetes Benchmarks
- **MITRE ATT&CK**: Framework de seguridad basado en amenazas que mapea técnicas de ataque

</details>

---

### 3. ¿Cuál es la sintaxis correcta de la CLI para escanear un cluster de Kubernetes con Kubescape?

- A) kubescape check cluster
- B) kubescape scan
- C) kubescape audit cluster
- D) kubescape analyze

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) kubescape scan**

**Explicación:**
Comandos de escaneo de la CLI de Kubescape:

```bash
# Scan current cluster
kubescape scan

# Scan specific namespace
kubescape scan --include-namespaces production

# Scan YAML files before deployment
kubescape scan *.yaml

# Scan with specific framework
kubescape scan framework nsa

# Scan specific control
kubescape scan control C-0034
```

El subcomando `scan` es la interfaz principal para todas las operaciones de escaneo.

</details>

---

### 4. ¿Cuál es la diferencia clave entre los modos Kubescape Operator y CLI?

- A) El modo Operator solo escanea nodes
- B) El modo CLI proporciona monitoreo continuo; Operator es de una sola ejecución
- C) Operator proporciona monitoreo continuo con componentes dentro del cluster; CLI realiza escaneos de una sola ejecución
- D) No hay diferencia

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Operator proporciona monitoreo continuo con componentes dentro del cluster; CLI realiza escaneos de una sola ejecución**

**Explicación:**
Modos de despliegue de Kubescape:

**Modo CLI:**
```bash
# One-time scan from local machine
kubescape scan
```
- Escaneo ad hoc
- Integración con CI/CD
- Desarrollo local

**Modo Operator:**
```bash
# Install in-cluster operator
helm repo add kubescape https://kubescape.github.io/helm-charts
helm install kubescape kubescape/kubescape-operator
```
- Monitoreo continuo
- Escaneos programados
- Escaneo de vulnerabilidades dentro del cluster
- Integración con la plataforma ARMO para visualización

</details>

---

### 5. ¿Cómo calcula Kubescape las puntuaciones de riesgo para los controles?

- A) Solo binario aprobado/fallido
- B) Basado en la severidad multiplicada por el recuento de recursos afectados
- C) Asignación aleatoria
- D) Basado en la prioridad del namespace

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Basado en la severidad multiplicada por el recuento de recursos afectados**

**Explicación:**
Puntuación de riesgo de Kubescape:

```
Risk Score = Severity Score x (Failed Resources / Total Resources)
```

Salida de ejemplo:
```
┌──────────────────────────────────────────────────┬────────────────┬───────┐
│ Control Name                                      │ Failed Resources│ Score │
├──────────────────────────────────────────────────┼────────────────┼───────┤
│ Privileged container                              │ 3/50           │ 18%   │
│ Resource limits                                   │ 25/50          │ 35%   │
│ Non-root containers                               │ 10/50          │ 42%   │
└──────────────────────────────────────────────────┴────────────────┴───────┘
```

Las puntuaciones más altas indican mayor riesgo que requiere atención inmediata.

</details>

---

### 6. ¿Qué flag aplica un umbral de cumplimiento en pipelines de CI/CD?

- A) --min-score
- B) --compliance-threshold
- C) --fail-threshold
- D) --severity-threshold

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) --compliance-threshold**

**Explicación:**
Uso de Kubescape en pipelines de CI/CD:

```bash
# Fail pipeline if compliance drops below 80%
kubescape scan --compliance-threshold 80

# Example GitLab CI
kubescape-scan:
  script:
    - kubescape scan framework nsa --compliance-threshold 75
    - kubescape scan framework cis --compliance-threshold 80
```

El umbral es un porcentaje (0-100). El escaneo falla (salida distinta de cero) si la puntuación general de cumplimiento cae por debajo del umbral.

```bash
# Exit codes
# 0: Passed threshold
# 1: Failed threshold
# 2: Error during scan
```

</details>

---

### 7. ¿En qué se diferencia Kubescape de kube-bench?

- A) kube-bench solo escanea aplicaciones; Kubescape escanea infraestructura
- B) Kubescape escanea configuraciones de workload; kube-bench se centra en CIS benchmarks a nivel de node
- C) Son herramientas idénticas
- D) kube-bench es solo para cloud providers

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Kubescape escanea configuraciones de workload; kube-bench se centra en CIS benchmarks a nivel de node**

**Explicación:**
Comparación de Kubescape vs kube-bench:

| Característica | Kubescape | kube-bench |
|---------|-----------|------------|
| Enfoque | Seguridad de workload/configuración | Seguridad de node/control plane |
| Alcance | Deployments, Pods, RBAC | kubelet, API server, etcd |
| Frameworks | NSA, CIS, MITRE | Solo CIS Benchmarks |
| Ubicación de ejecución | Fuera del cluster (CLI) o dentro del cluster | Debe ejecutarse en cada node |
| Escaneo de imágenes | Sí (con Grype) | No |
| Análisis RBAC | Sí | No |

Usa ambos juntos para una seguridad integral:
- kube-bench: Fortalecimiento de la infraestructura del cluster
- Kubescape: Seguridad de workloads y configuración

</details>

---

### 8. ¿Qué característica proporciona Kubescape para el análisis de seguridad de RBAC?

- A) Generación de políticas RBAC
- B) Visualización de RBAC que muestra permisos y riesgos
- C) Remediación automática de RBAC
- D) Herramientas de migración de RBAC

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Visualización de RBAC que muestra permisos y riesgos**

**Explicación:**
Capacidades de análisis RBAC de Kubescape:

```bash
# Scan RBAC configurations
kubescape scan control C-0035  # Cluster-admin binding
kubescape scan control C-0036  # Wildcard permissions
kubescape scan control C-0039  # Risky service accounts
```

Características de visualización de RBAC:
- Mapea ServiceAccounts a Roles/ClusterRoles
- Identifica bindings excesivamente permisivos
- Resalta permisos peligrosos (acceso a secrets, pod exec)
- Muestra rutas de ataque a través de RBAC

Hallazgo de ejemplo:
```
ServiceAccount 'default' in namespace 'production' has:
- Cluster-admin binding (CRITICAL)
- Secrets list/get permissions (HIGH)
- Pod exec permissions (HIGH)
```

</details>

---

### 9. ¿Con qué escáner de vulnerabilidades se integra Kubescape para escaneo de imágenes?

- A) Trivy
- B) Clair
- C) Grype
- D) Anchore

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Grype**

**Explicación:**
Kubescape se integra con Grype (de Anchore) para el escaneo de vulnerabilidades de imágenes de contenedor:

```bash
# Enable image scanning
kubescape scan --enable-host-scan

# Operator mode includes automatic image scanning
helm install kubescape kubescape/kubescape-operator \
  --set capabilities.vulnerabilityScan=enable
```

La integración con Grype proporciona:
- Detección de CVE en imágenes de contenedor
- Generación de SBOM (Software Bill of Materials)
- Priorización basada en severidad
- Integración con hallazgos de seguridad

Los resultados combinan problemas de configuración con datos de vulnerabilidades para una evaluación integral del riesgo.

</details>

---

### 10. ¿Cómo gestiona Kubescape las excepciones de controles?

- A) Las excepciones no son compatibles
- B) Usando archivos YAML de excepciones que especifican controles y recursos a excluir
- C) Solo mediante flags de línea de comandos
- D) Modificando el código fuente

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Usando archivos YAML de excepciones que especifican controles y recursos a excluir**

**Explicación:**
Kubescape admite excepciones mediante archivos de configuración:

```yaml
# exceptions.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: kubescape-exceptions
data:
  exceptions: |
    - name: "Allow privileged kube-system pods"
      policyType: postureExceptionPolicy
      actions:
        - alertOnly
      resources:
        - designatorType: Attributes
          attributes:
            namespace: kube-system
      posturePolicies:
        - controlID: C-0057  # Privileged container
```

Aplicar excepciones:
```bash
kubescape scan --exceptions exceptions.yaml
```

Esto permite:
- Suprimir falsos positivos conocidos
- Aceptar el riesgo para recursos específicos
- Mantener informes de escaneo limpios

</details>

---

## Cálculo de puntuación

- **9-10 correctas**: Excelente: tienes una comprensión profunda de Kubescape.
- **7-8 correctas**: Bien: tienes un conocimiento sólido de los conceptos clave.
- **5-6 correctas**: Aceptable: hay áreas que necesitan estudio adicional.
- **4 o menos**: Revisa la documentación de nuevo.

## Documentación relacionada

- [Gestión de postura de seguridad con Kubescape](../../security/11-kubescape.md)
