# Cuestionario de ArgoCD

Este cuestionario evalúa tu comprensión de ArgoCD y GitOps.

## Pregunta 1: Principios fundamentales de GitOps

<details>
<summary>¿Cuáles son los cuatro principios fundamentales de GitOps?</summary>

**Respuesta:**
1. **Configuración declarativa**: Define como código el estado deseado del sistema
2. **Versionado e inmutable**: Conserva versiones inmutables del estado deseado y un historial completo
3. **Obtención automática desde el origen**: Los agentes obtienen automáticamente las declaraciones de estado deseado desde el origen
4. **Conciliación continua**: Observa el estado real e intenta aplicar continuamente el estado deseado

Estos principios permiten que GitOps funcione como un modelo operativo completo, más allá de ser solo una herramienta de despliegue.
</details>

## Pregunta 2: Arquitectura de ArgoCD

<details>
<summary>¿Cuáles son los componentes principales de ArgoCD y qué función cumple cada uno?</summary>

**Respuesta:**
- **Servidor de API**: Proporciona la API REST y la interfaz web, y gestiona la autenticación y la autorización
- **Servidor de repositorios**: Se conecta a los repositorios Git y genera manifiestos
- **Controlador de aplicaciones**: Supervisa el estado de las aplicaciones y realiza la sincronización
- **Redis**: Caché reconstruible
- **Dex**: Servidor de autenticación OIDC (opcional)

El escalado varía según el componente: Application Controller utiliza fragmentación (sharding), ApplicationSet usa elección de líder y el Dex incluido no puede lograr alta disponibilidad de forma segura solo agregando réplicas a su almacenamiento en memoria.
</details>

## Pregunta 3: Recurso Application

<details>
<summary>¿Cuáles son los componentes obligatorios de un recurso Application de ArgoCD?</summary>

**Respuesta:**
```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: my-app
  namespace: argocd
spec:
  project: default
  source:
    repoURL: https://github.com/example/app-config
    targetRevision: HEAD
    path: k8s
  destination:
    server: https://kubernetes.default.svc
    namespace: default
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
```

**Elementos obligatorios:**
- `source`: Información del repositorio Git
- `destination`: Clúster y espacio de nombres de destino para el despliegue
- `project`: Proyecto de ArgoCD (para gestionar permisos)
</details>

## Pregunta 4: Políticas de sincronización

<details>
<summary>¿Qué diferencias hay entre la sincronización automática y la manual en ArgoCD?</summary>

**Respuesta:**
**Sincronización automática:**
```yaml
syncPolicy:
  automated:
    prune: true      # Automatically delete unnecessary resources
    selfHeal: true   # Automatically recover from drift
```
- Aplica los cambios al clúster automáticamente cuando cambia Git
- Corrige automáticamente las desviaciones detectadas
- Úsala con precaución en entornos de producción

**Sincronización manual:**
- El usuario inicia explícitamente la sincronización
- Aplica los cambios después de revisarlos
- Aún es necesario diseñar los controles de revisión/aprobación y la carga operativa
</details>

## Pregunta 5: ApplicationSet

<details>
<summary>¿Cuál es el propósito de ApplicationSet de ArgoCD y cuáles son los principales tipos de generadores?</summary>

**Respuesta:**
**Propósito:**
- Automatizar despliegues en varios clústeres
- Crear recursos Application mediante plantillas
- Gestionar configuraciones específicas de cada entorno

**Generadores principales:**
- **Generador List**: Usa listas de valores estáticos
- **Generador Cluster**: Usa los clústeres registrados
- **Generador Git**: Usa la estructura del repositorio Git
- **Generador Matrix**: Combina varios generadores
- **Generador Pull Request**: Crea entornos temporales basados en solicitudes de incorporación de cambios (PR)

```yaml
apiVersion: argoproj.io/v1alpha1
kind: ApplicationSet
metadata:
  name: demo-cluster-apps
  namespace: argocd
spec:
  goTemplate: true
  goTemplateOptions: ["missingkey=error"]
  generators:
  - clusters:
      selector:
        matchLabels:
          environment: demo
  template:
    metadata:
      name: '{{.nameNormalized}}-guestbook'
    spec:
      project: default
      source:
        repoURL: https://github.com/argoproj/argocd-example-apps.git
        targetRevision: HEAD
        path: guestbook
      destination:
        server: '{{.server}}'
        namespace: guestbook
      syncPolicy:
        syncOptions: [CreateNamespace=true]
```
</details>

## Pregunta 6: Prácticas recomendadas de seguridad

<details>
<summary>¿Cuáles son los métodos principales para reforzar la seguridad de ArgoCD?</summary>

**Respuesta:**
1. **Configuración de RBAC**:
   ```yaml
   policy.default: role:authenticated
   policy.csv: |
     p, role:dev, applications, get, dev/*, allow
     p, role:dev, projects, get, dev, allow
     g, dev-team, role:dev
   ```

2. **Integración de SSO**:
   - OIDC directo o conectores de Dex compatibles con otros proveedores de identidad
   - Gestión centralizada de la autenticación

3. **Seguridad de red**:
   - Configuración de TLS para Ingress
   - Aplicación de políticas de red
   - Uso de repositorios Git privados

4. **Gestión de secretos**:
   - Uso de External Secrets Operator
   - Sealed Secrets o Helm Secrets
   - Evita guardar secretos en texto sin cifrar en Git; usa un almacén externo de secretos o el cifrado y la gestión de claves adecuados

5. **Registro de auditoría**:
   - Registrar todos los cambios
   - Supervisar los registros de acceso
</details>

## Pregunta 7: Gestión de varios clústeres

<details>
<summary>¿Cómo se gestionan varios clústeres en ArgoCD?</summary>

**Respuesta:**
1. **Registro del clúster**:
   ```bash
   argocd cluster add my-cluster-context
   ```

2. **Despliegue de aplicaciones por clúster**:
   ```yaml
   destination:
     server: https://my-cluster-api-server
     namespace: production
   ```

3. **Automatización con ApplicationSet**:
   ```yaml
   generators:
   - clusters:
       selector:
         matchLabels:
           environment: production
   ```

4. **Gestión de permisos de los clústeres**:
   - Configurar cuentas de servicio para cada clúster
   - Aplicar el principio de privilegio mínimo
   - Aislar por espacio de nombres

5. **Supervisión y alertas**:
   - Paneles de estado por clúster
   - Alertas de errores de sincronización
   - Supervisión del uso de recursos
</details>

## Pregunta 8: Solución de problemas

<details>
<summary>¿Qué debes comprobar cuando una aplicación de ArgoCD está en estado «OutOfSync»?</summary>

**Respuesta:**
1. **Comprobar el estado del repositorio Git**:
   ```bash
   # Check repository access permissions
   argocd repo list
   argocd repo get "$REPO_URL"
   ```

2. **Validar los manifiestos**:
   ```bash
   # Validate manifests locally
   kubectl --context "$TARGET_CONTEXT" apply --server-side --dry-run=server -f manifests/
   ```

3. **Comprobar las políticas de sincronización**:
   - Configuración de sincronización automática
   - Opciones Prune y SelfHeal
   - Condiciones de sincronización (Sync Windows)

4. **Analizar el estado de los recursos**:
   ```bash
   # Check application details
   argocd app get "$APP_NAME"
   argocd app diff "$APP_NAME"
   ```

5. **Comprobar los registros**:
   ```bash
   # ArgoCD controller logs
   kubectl logs -n argocd -l app.kubernetes.io/name=argocd-application-controller
   ```

6. **Probar la sincronización manual**:
   ```bash
   argocd app sync "$APP_NAME" --dry-run
   ```
</details>

## Pregunta 9: Patrones operativos de GitOps

<details>
<summary>¿Qué patrones operativos de GitOps cubre esta guía?</summary>

**Respuesta:**
1. **GitOps para varios clústeres**:
   - Despliegues automatizados en varios clústeres mediante ApplicationSet
   - Sincronización de configuración y aplicación de políticas entre clústeres

2. **GitOps híbrido y multinube**:
   - Estrategias de despliegue coherentes en entornos locales y en la nube
   - Portabilidad de cargas de trabajo entre distintos proveedores de nube

3. **Integración de GitOps y gestión de políticas**:
   - Integración con OPA (Open Policy Agent) y Kyverno
   - Automatización del cumplimiento y la gobernanza
   - Definición de políticas de seguridad como código y control de versiones

4. **Entrega progresiva**:
   - Automatización de despliegues canary y blue-green
   - Integración con Argo Rollouts
   - Reversión automática basada en métricas
</details>

## Pregunta 10: Integración con Amazon EKS

<details>
<summary>¿Qué aspectos se deben tener en cuenta al integrar ArgoCD con Amazon EKS?</summary>

**Respuesta:**
1. **Configuración de permisos de IAM**:
   ```yaml
   # IRSA (IAM Roles for Service Accounts) configuration
   controller:
     serviceAccount:
       annotations:
         eks.amazonaws.com/role-arn: arn:aws:iam::123456789012:role/ArgoCD-Management
   ```

2. **Configuración de ALB Ingress**:
   ```yaml
   metadata:
     annotations:
       alb.ingress.kubernetes.io/scheme: internal
       alb.ingress.kubernetes.io/target-type: ip
   spec:
     ingressClassName: alb
   ```

3. **Registro del clúster de EKS**:
   ```bash
   # Register EKS cluster to ArgoCD
   argocd cluster add "$TARGET_CONTEXT"
   ```

4. **Integración con ECR**:
   - Actualización automática de imágenes de ECR
   - Configuración de Image Updater

5. **AWS Load Balancer Controller**:
   - Optimización del balanceo de carga de servicios
   - Uso de Target Group Binding

6. **Consideraciones de seguridad**:
   - Uso de puntos de conexión de VPC
   - Configuración de grupos de seguridad
   - Aplicación de políticas de red
</details>

---

**Puntuación:**
- 8-10 respuestas correctas: Se entienden los conceptos fundamentales de este cuestionario
- 6-7 respuestas correctas: Buen resultado (se recomienda profundizar)
- 4-5 respuestas correctas: Promedio (conviene repasar los conceptos básicos)
- 0-3 respuestas correctas: Repasa los fundamentos y practica los laboratorios

Configura `REPO_URL`, `APP_NAME` y `TARGET_CONTEXT` con valores reales. `TARGET_CONTEXT` es un contexto de kubeconfig; el contexto predeterminado de EKS puede ser un ARN. Revisa los cambios RBAC de cluster-add y las diferencias entre la sincronización y la eliminación de recursos (`prune`). La ejecución de prueba muestra los cambios; `--prune` incluye eliminaciones y requiere una revisión independiente. Las anotaciones de IRSA no configuran la relación de confianza ni las entradas de acceso de EKS, y ALB requiere certificados/TLS y acceso de red. En el entorno de ApplicationSet, `demo` debe coincidir con las etiquetas de los Secrets de los clústeres registrados. Conserva `role:authenticated` sin conceder permisos globales de solo lectura y asigna a `dev-team` únicamente el alcance que necesita.
