# Cuestionario de ArgoCD

Este cuestionario evalúa tu comprensión de ArgoCD y GitOps.

## Pregunta 1: Principios fundamentales de GitOps

<details>
<summary>¿Cuáles son los 4 principios fundamentales de GitOps?</summary>

**Respuesta:**
1. **Configuración declarativa**: Define el estado deseado del sistema como código
2. **Control de versiones**: Realiza el seguimiento de todos los cambios en Git
3. **Sincronización automatizada**: Reconcilia automáticamente las diferencias entre el repositorio y el entorno en ejecución
4. **Autorreparación**: Recupera automáticamente el sistema al estado deseado

Estos principios permiten que GitOps funcione como un modelo operativo completo, más allá de ser solo una herramienta de despliegue.
</details>

## Pregunta 2: Arquitectura de ArgoCD

<details>
<summary>¿Cuáles son los componentes principales de ArgoCD y cuáles son sus funciones?</summary>

**Respuesta:**
- **API Server**: Proporciona la API REST y la interfaz web, y gestiona la autenticación y la autorización
- **Repository Server**: Se conecta a repositorios Git y genera manifiestos
- **Application Controller**: Supervisa el estado de la Application y realiza la sincronización
- **Redis**: Almacenamiento en caché y de sesiones
- **Dex**: Servidor de autenticación OIDC (opcional)

Cada componente puede escalarse de forma independiente y admite configuraciones de alta disponibilidad.
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
- `destination`: Cluster y namespace de destino para el despliegue
- `project`: Proyecto de ArgoCD (para la gestión de permisos)
</details>

## Pregunta 4: Políticas de sincronización

<details>
<summary>¿Cuáles son las diferencias entre la sincronización automatizada y la manual en ArgoCD?</summary>

**Respuesta:**
**Sincronización automatizada:**
```yaml
syncPolicy:
  automated:
    prune: true      # Automatically delete unnecessary resources
    selfHeal: true   # Automatically recover from drift
```
- Se aplica automáticamente al cluster cuando cambia Git
- Se recupera automáticamente cuando se detecta drift
- Úsala con precaución en entornos de producción

**Sincronización manual:**
- El usuario inicia explícitamente la sincronización
- Se aplica después de revisar los cambios
- Es más segura, pero incrementa la carga operativa
</details>

## Pregunta 5: ApplicationSet

<details>
<summary>¿Cuál es el propósito de ApplicationSet de ArgoCD y cuáles son los principales tipos de generadores?</summary>

**Respuesta:**
**Propósito:**
- Automatizar despliegues en múltiples clusters
- Creación de Application basada en plantillas
- Gestión de configuración específica del entorno

**Generadores principales:**
- **List Generator**: Basado en listas de valores estáticos
- **Cluster Generator**: Basado en clusters registrados
- **Git Generator**: Basado en la estructura del repositorio Git
- **Matrix Generator**: Combina múltiples generadores
- **Pull Request Generator**: Entornos temporales basados en PR

```yaml
apiVersion: argoproj.io/v1alpha1
kind: ApplicationSet
metadata:
  name: cluster-apps
spec:
  generators:
  - clusters: {}
  template:
    metadata:
      name: '{{name}}-app'
    spec:
      source:
        repoURL: https://github.com/example/apps
        path: '{{name}}'
      destination:
        server: '{{server}}'
```
</details>

## Pregunta 6: Mejores prácticas de seguridad

<details>
<summary>¿Cuáles son los métodos principales para reforzar la seguridad de ArgoCD?</summary>

**Respuesta:**
1. **Configuración de RBAC**:
   ```yaml
   policy.default: role:readonly
   policy.csv: |
     p, role:admin, applications, *, */*, allow
     p, role:dev, applications, get, dev/*, allow
     g, dev-team, role:dev
   ```

2. **Integración de SSO**:
   - Integración con OIDC, SAML y LDAP
   - Gestión centralizada de autenticación

3. **Seguridad de red**:
   - Configuración de TLS para Ingress
   - Aplicación de políticas de red
   - Uso de repositorios Git privados

4. **Gestión de Secrets**:
   - Uso de External Secrets Operator
   - Sealed Secrets o Helm Secrets
   - Repositorios Git separados para información confidencial

5. **Registro de auditoría**:
   - Seguimiento de todos los cambios
   - Supervisión de registros de acceso
</details>

## Pregunta 7: Gestión de múltiples clusters

<details>
<summary>¿Cómo se gestionan múltiples clusters en ArgoCD?</summary>

**Respuesta:**
1. **Registro de clusters**:
   ```bash
   argocd cluster add my-cluster-context
   ```

2. **Despliegue de Application por cluster**:
   ```yaml
   destination:
     server: https://my-cluster-api-server
     namespace: production
   ```

3. **Automatización mediante ApplicationSet**:
   ```yaml
   generators:
   - clusters:
       selector:
         matchLabels:
           environment: production
   ```

4. **Gestión de permisos de clusters**:
   - Configurar cuentas de servicio para cada cluster
   - Aplicar el principio de privilegio mínimo
   - Aislamiento basado en namespace

5. **Supervisión y alertas**:
   - Paneles de estado por cluster
   - Alertas de fallos de sincronización
   - Supervisión del uso de recursos
</details>

## Pregunta 8: Solución de problemas

<details>
<summary>¿Qué se debe revisar cuando una Application de ArgoCD está en estado "OutOfSync"?</summary>

**Respuesta:**
1. **Revisar el estado del repositorio Git**:
   ```bash
   # Check repository access permissions
   argocd repo list
   argocd repo get <repo-url>
   ```

2. **Validar manifiestos**:
   ```bash
   # Validate manifests locally
   kubectl apply --dry-run=client -f manifests/
   ```

3. **Revisar las políticas de sincronización**:
   - Configuración de sincronización automática
   - Opciones de Prune y SelfHeal
   - Condiciones de sincronización (Sync Windows)

4. **Analizar el estado de los recursos**:
   ```bash
   # Check application details
   argocd app get <app-name>
   argocd app diff <app-name>
   ```

5. **Revisar los registros**:
   ```bash
   # ArgoCD controller logs
   kubectl logs -n argocd -l app.kubernetes.io/name=argocd-application-controller
   ```

6. **Probar la sincronización manual**:
   ```bash
   argocd app sync <app-name> --prune
   ```
</details>

## Pregunta 9: Tendencias recientes de GitOps

<details>
<summary>¿Cuáles son las principales tendencias en el ámbito de GitOps en 2023?</summary>

**Respuesta:**
1. **GitOps para múltiples clusters**:
   - Despliegues automatizados en múltiples clusters mediante ApplicationSets
   - Sincronización de configuración entre clusters y aplicación de políticas

2. **GitOps híbrido y multi-cloud**:
   - Estrategias de despliegue consistentes en entornos on-premises y cloud
   - Portabilidad de workloads entre distintos proveedores cloud

3. **Integración de GitOps y gestión de políticas**:
   - Integración con OPA (Open Policy Agent) y Kyverno
   - Automatización de cumplimiento y gobernanza
   - Codificación y control de versiones de políticas de seguridad

4. **Entrega progresiva**:
   - Automatización de despliegues Canary y Blue-Green
   - Integración con Argo Rollouts
   - Rollback automático basado en métricas
</details>

## Pregunta 10: Integración con Amazon EKS

<details>
<summary>¿Cuáles son las consideraciones al integrar ArgoCD con Amazon EKS?</summary>

**Respuesta:**
1. **Configuración de permisos de IAM**:
   ```yaml
   # IRSA (IAM Roles for Service Accounts) configuration
   serviceAccount:
     annotations:
       eks.amazonaws.com/role-arn: arn:aws:iam::ACCOUNT:role/argocd-role
   ```

2. **Configuración de ALB Ingress**:
   ```yaml
   annotations:
     kubernetes.io/ingress.class: alb
     alb.ingress.kubernetes.io/scheme: internet-facing
     alb.ingress.kubernetes.io/target-type: ip
   ```

3. **Registro de clusters EKS**:
   ```bash
   # Register EKS cluster to ArgoCD
   argocd cluster add arn:aws:eks:region:account:cluster/cluster-name
   ```

4. **Integración con ECR**:
   - Actualizaciones automáticas de imágenes ECR
   - Configuración de Image Updater

5. **AWS Load Balancer Controller**:
   - Optimización del balanceo de carga de Service
   - Uso de Target Group Binding

6. **Consideraciones de seguridad**:
   - Uso de endpoints de VPC
   - Configuración de security groups
   - Aplicación de políticas de red
</details>

---

**Puntuación:**
- 8-10 respuestas correctas: Excelente (nivel experto en ArgoCD)
- 6-7 respuestas correctas: Bien (se recomienda aprendizaje adicional)
- 4-5 respuestas correctas: Promedio (se necesita repasar los conceptos básicos)
- 0-3 respuestas correctas: Insuficiente (se necesita volver a estudiar todo el contenido)
