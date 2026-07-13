# Kubernetes Resource Operator (KRO)

> **Versiones compatibles**: Kubernetes 1.31, 1.32, 1.33
> **Última actualización**: February 21, 2026

## Overview

Kubernetes Resource Operator (KRO) es un framework para definir y gestionar de forma declarativa las relaciones entre recursos de Kubernetes. Al ir más allá de las limitaciones de los charts de Helm tradicionales, KRO modela grafos de recursos mediante ResourceGraphDefinition (RGD) y permite desplegar aplicaciones complejas como un único Custom Resource (recurso personalizado).

## KRO Core Concepts

### What is Kubernetes Resource Operator?

Kubernetes Resource Operator (KRO) es un framework para definir y gestionar de forma declarativa las relaciones entre recursos de Kubernetes. KRO se basa en los siguientes conceptos principales:

1. **Relaciones declarativas entre recursos**: Expresa estructuras de aplicaciones complejas definiendo explícitamente las relaciones entre recursos.
2. **Reconciliación basada en el estado**: Reconcilia continuamente las diferencias entre los estados deseado y real.
3. **Grafo de recursos**: Modela dependencias y relaciones entre recursos en forma de grafo.
4. **Gestión automatizada del ciclo de vida**: Gestiona automáticamente la creación, actualización y eliminación de recursos.

### ResourceGraphDefinition (RGD)

ResourceGraphDefinition (RGD) es un componente central de KRO que define relaciones entre recursos personalizados y sus recursos nativos de Kubernetes dependientes. RGD ofrece las siguientes capacidades:

1. **Definición de relación padre-hijo**: Define la estructura jerárquica entre recursos padre e hijo.
2. **Creación de recursos basada en plantillas**: Crea dinámicamente recursos hijo en función de las propiedades del recurso padre.
3. **Propagación de estado**: Propaga los estados de los recursos hijo a los recursos padre para comprender el estado general de la aplicación.
4. **Gestión de dependencias**: Define dependencias entre recursos hijo para garantizar el orden correcto de creación y actualización.

### KRO vs Traditional Approaches

KRO tiene los siguientes diferenciadores en comparación con los enfoques tradicionales de gestión de recursos de Kubernetes:

| Feature | KRO | Helm | Operator SDK | Kustomize |
|---------|-----|------|--------------|-----------|
| **Resource Relationship Modeling** | Explicit graph | Implicit | Code-based | None |
| **State Propagation** | Automatic | Manual | Code-based | None |
| **Dependency Management** | Declarative | Implicit | Code-based | None |
| **Extensibility** | High | Medium | High | Low |
| **Learning Curve** | Medium | Low | High | Low |
| **GitOps Friendliness** | High | Medium | Medium | High |

### KRO Architecture

KRO consta de los siguientes componentes:

1. **KRO Controller**: Observa ResourceGraphDefinitions y gestiona grafos de recursos.
2. **Resource Graph Engine**: Procesa relaciones y dependencias entre recursos.
3. **State Manager**: Realiza seguimiento de los estados de los recursos y los propaga.
4. **Reconciliation Loop**: Reconcilia las diferencias entre los estados deseado y real.

```
+-------------------+     +-------------------+     +-------------------+
|  Custom Resource  |     | ResourceGraph     |     | Kubernetes        |
|  (CR)             |<--->| Definition        |<--->| Native Resources  |
+-------------------+     +-------------------+     +-------------------+
         ^                        ^                         ^
         |                        |                         |
         v                        v                         v
+-----------------------------------------------------------------------+
|                          KRO Controller                                |
|                                                                       |
|  +----------------+  +----------------+  +----------------+           |
|  | Resource Graph |  | State Manager  |  | Reconciliation |           |
|  |     Engine     |  |                |  |     Loop       |           |
|  +----------------+  +----------------+  +----------------+           |
+-----------------------------------------------------------------------+
```

## The Origins and Evolution of KRO

### Challenges in Kubernetes Resource Management

A medida que las aplicaciones de Kubernetes crecieron en complejidad, los enfoques de gestión de recursos evolucionaron:

1. **Gestión directa con kubectl**: Aplicación manual de archivos YAML individuales — difícil de gestionar las relaciones y el orden entre recursos
2. **Helm**: Simplificó el despliegue mediante empaquetado basado en plantillas, pero está limitado por la complejidad de las plantillas de Go y la gestión del estado de release
3. **Operator SDK**: Permite el desarrollo completo de controllers personalizados, pero requiere conocimientos de programación en Go y altos costes de desarrollo/mantenimiento
4. **KRO**: ResourceGraphDefinition declarativo define grafos de recursos sin codificación — combina la potencia de Operator con la simplicidad de Helm

### Problems KRO Solves

| Existing Limitation | KRO's Solution |
|---------------------|----------------|
| Helm template complexity | Pure YAML + resource reference syntax |
| Operator development cost | RGD declaration auto-generates CRD + controller |
| No inter-resource state propagation | statusMappings for automatic child→parent state propagation |
| Manual dependency ordering | Automatic dependency resolution in resource graph |

## Lab Environment Setup

Para seguir los ejemplos de este documento, necesitarás las siguientes herramientas y entorno:

### Required Tools
- kubectl v1.31 o superior
- Helm v3.10 o superior
- kro CLI v0.5.0 o superior
- Un cluster de Kubernetes funcional (EKS, minikube, kind, etc.)

### Installing KRO

```bash
# Install KRO controller
kubectl apply -f https://github.com/kro-project/kro/releases/download/v0.5.0/kro-controller.yaml

# Install KRO CLI
curl -L https://github.com/kro-project/kro/releases/download/v0.5.0/kro-cli-$(uname -s)-$(uname -m) -o kro
chmod +x kro
sudo mv kro /usr/local/bin/

# Verify installation
kubectl get pods -n kro-system
```

## Helm and KRO Comparison

### Helm

Helm es una herramienta ampliamente utilizada para empaquetar y desplegar aplicaciones de Kubernetes. Helm tiene las siguientes características:

- **Basado en plantillas**: Usa el lenguaje de plantillas de Go para generar manifests de Kubernetes
- **Concepto de Chart**: Unidad para empaquetar aplicaciones
- **Gestión de releases**: Gestión de versiones de las aplicaciones desplegadas
- **Repositorio central**: Repositorio para compartir y reutilizar charts

### Kubernetes Resource Operator (KRO)

KRO es un enfoque para gestionar aplicaciones usando recursos personalizados de Kubernetes:

- **API declarativa**: Definición de recursos nativa de Kubernetes
- **Basado en el estado**: Declara el estado deseado y el controller reconcilia el estado real
- **Compatible con GitOps**: Integración sencilla con sistemas de control de versiones
- **Extensibilidad**: Extensión mediante Custom Resource Definitions (CRDs)

### Comparison Table

| Feature | Helm | KRO |
|---------|------|-----|
| **Packaging Method** | Chart (tgz archive) | Custom Resource |
| **Template Engine** | Go templates | None (pure YAML) |
| **Version Management** | Release history | Git-based |
| **Rollback Mechanism** | helm rollback | GitOps-based rollback |
| **Dependency Management** | requirements.yaml | ResourceGraphDefinition |
| **Customization** | values.yaml | CR spec |
| **Installation Method** | helm install | kubectl apply |
| **Upgrade Method** | helm upgrade | kubectl apply |
| **Deletion Method** | helm uninstall | kubectl delete |
| **Hooks** | Install/upgrade/delete hooks | Kubernetes event-based |

## Reasons to Migrate from Helm to KRO

1. **Enfoque nativo de Kubernetes**: KRO sigue el modelo de API declarativa de Kubernetes para una experiencia más coherente
2. **Gestión de versiones mejorada**: Capacidad para rastrear los cambios de cada recurso de forma individual
3. **Control detallado**: Control más detallado a nivel de recurso individual
4. **Gestión de dependencias simplificada**: Gestión más sencilla de relaciones complejas con declaraciones explícitas de dependencias
5. **Seguridad reforzada**: Capacidad de conceder solo los permisos necesarios siguiendo el principio de mínimo privilegio
6. **Gestión de estado mejorada**: Propaga y agrega automáticamente los estados de los recursos
7. **Integración con flujos de trabajo GitOps**: Integración sencilla con herramientas GitOps mediante un enfoque declarativo

## Practical Example: Migrating Nginx Helm Chart to KRO

### Existing Helm Chart (values.yaml)

```yaml
# Nginx Helm chart values.yaml
replicaCount: 2

image:
  repository: nginx
  tag: 1.21.0
  pullPolicy: IfNotPresent

service:
  type: ClusterIP
  port: 80

ingress:
  enabled: true
  hosts:
    - host: example.com
      paths:
        - path: /
          pathType: Prefix

resources:
  limits:
    cpu: 100m
    memory: 128Mi
  requests:
    cpu: 50m
    memory: 64Mi
```

### KRO Custom Resource Definition

```yaml
apiVersion: apiextensions.k8s.io/v1
kind: CustomResourceDefinition
metadata:
  name: nginxapps.kro.example.com
spec:
  group: kro.example.com
  names:
    kind: NginxApp
    listKind: NginxAppList
    plural: nginxapps
    singular: nginxapp
  scope: Namespaced
  versions:
    - name: v1
      served: true
      storage: true
      schema:
        openAPIV3Schema:
          type: object
          properties:
            spec:
              type: object
              properties:
                replicas:
                  type: integer
                  default: 1
                image:
                  type: object
                  properties:
                    repository:
                      type: string
                    tag:
                      type: string
                    pullPolicy:
                      type: string
                      enum: [Always, IfNotPresent, Never]
                service:
                  type: object
                  properties:
                    type:
                      type: string
                      enum: [ClusterIP, NodePort, LoadBalancer]
                    port:
                      type: integer
                ingress:
                  type: object
                  properties:
                    enabled:
                      type: boolean
                    hosts:
                      type: array
                      items:
                        type: object
                        properties:
                          host:
                            type: string
                          paths:
                            type: array
                            items:
                              type: object
                              properties:
                                path:
                                  type: string
                                pathType:
                                  type: string
                resources:
                  type: object
                  properties:
                    limits:
                      type: object
                      x-kubernetes-preserve-unknown-fields: true
                    requests:
                      type: object
                      x-kubernetes-preserve-unknown-fields: true
```

### Creating ResourceGraphDefinition

```yaml
apiVersion: kro.run/v1alpha1
kind: ResourceGraphDefinition
metadata:
  name: nginxapp-graph
spec:
  resourceKind:
    group: kro.example.com
    kind: NginxApp
    version: v1
  childResources:
    - apiVersion: apps/v1
      kind: Deployment
      nameTemplate: "{{.parent.metadata.name}}"
      template: |
        spec:
          replicas: {{.parent.spec.replicas}}
          selector:
            matchLabels:
              app: {{.parent.metadata.name}}
          template:
            metadata:
              labels:
                app: {{.parent.metadata.name}}
            spec:
              containers:
              - name: nginx
                image: {{.parent.spec.image.repository}}:{{.parent.spec.image.tag}}
                imagePullPolicy: {{.parent.spec.image.pullPolicy}}
                ports:
                - containerPort: {{.parent.spec.service.port}}
                resources:
                  {{- if .parent.spec.resources }}
                  limits:
                    {{- if .parent.spec.resources.limits.cpu }}
                    cpu: {{.parent.spec.resources.limits.cpu}}
                    {{- end }}
                    {{- if .parent.spec.resources.limits.memory }}
                    memory: {{.parent.spec.resources.limits.memory}}
                    {{- end }}
                  requests:
                    {{- if .parent.spec.resources.requests.cpu }}
                    cpu: {{.parent.spec.resources.requests.cpu}}
                    {{- end }}
                    {{- if .parent.spec.resources.requests.memory }}
                    memory: {{.parent.spec.resources.requests.memory}}
                    {{- end }}
                  {{- end }}

    - apiVersion: v1
      kind: Service
      nameTemplate: "{{.parent.metadata.name}}"
      template: |
        spec:
          selector:
            app: {{.parent.metadata.name}}
          ports:
          - port: {{.parent.spec.service.port}}
            targetPort: {{.parent.spec.service.port}}
          type: {{.parent.spec.service.type}}

    - apiVersion: networking.k8s.io/v1
      kind: Ingress
      nameTemplate: "{{.parent.metadata.name}}"
      condition: "{{.parent.spec.ingress.enabled}}"
      template: |
        spec:
          rules:
          {{- range .parent.spec.ingress.hosts }}
          - host: {{.host}}
            http:
              paths:
              {{- range .paths }}
              - path: {{.path}}
                pathType: {{.pathType}}
                backend:
                  service:
                    name: {{$.parent.metadata.name}}
                    port:
                      number: {{$.parent.spec.service.port}}
              {{- end }}
          {{- end }}

  statusMappings:
    - childResource:
        kind: Deployment
        name: "{{.parent.metadata.name}}"
      conditions:
        - type: Available
          mapping:
            type: Ready
      fieldMappings:
        - child: "status.availableReplicas"
          parent: "status.availableReplicas"
        - child: "status.readyReplicas"
          parent: "status.readyReplicas"

    - childResource:
        kind: Service
        name: "{{.parent.metadata.name}}"
      fieldMappings:
        - child: "spec.clusterIP"
          parent: "status.serviceIP"
```

### KRO Custom Resource Instance

```yaml
apiVersion: kro.example.com/v1
kind: NginxApp
metadata:
  name: my-nginx
spec:
  replicas: 2
  image:
    repository: nginx
    tag: 1.21.0
    pullPolicy: IfNotPresent
  service:
    type: ClusterIP
    port: 80
  ingress:
    enabled: true
    hosts:
      - host: example.com
        paths:
          - path: /
            pathType: Prefix
  resources:
    limits:
      cpu: 100m
      memory: 128Mi
    requests:
      cpu: 50m
      memory: 64Mi
```

### Deployment and Verification

```bash
# Apply CRD and RGD
kubectl apply -f nginxapp-crd.yaml
kubectl apply -f nginxapp-rgd.yaml

# Apply custom resource instance
kubectl apply -f my-nginx.yaml

# Verify created resources
kubectl get deployments,services,ingress -l app=my-nginx

# Check custom resource status
kubectl get nginxapp my-nginx -o yaml
```

## KRO Use Cases

### 1. Microservices Application Management

KRO es ideal para gestionar aplicaciones de microservices compuestas por varios componentes. Cada microservice puede estar compuesto por los siguientes recursos:

- Deployment o StatefulSet
- Service
- ConfigMap
- Secret
- HorizontalPodAutoscaler
- PodDisruptionBudget

Con KRO, puedes definir explícitamente las relaciones entre estos recursos y gestionar todo el microservice mediante un único recurso personalizado.

### 2. Database Cluster Management

Los clusters de bases de datos (por ejemplo, PostgreSQL, MySQL) requieren varios componentes y configuraciones complejas. KRO puede gestionar los siguientes recursos:

- StatefulSets master y replica
- Endpoints de Service
- Persistent volume claims
- Trabajos de backup y restore
- Configuración de monitoreo

### 3. Multi-Cluster Application Deployment

KRO también se puede usar para gestionar aplicaciones que abarcan varios clusters de Kubernetes. Esto admite escenarios como:

- Despliegues regionales
- Despliegue coherente en entornos de desarrollo, staging y producción
- Gestión de aplicaciones en entornos de cloud híbrida

## KRO Best Practices

### 1. Resource Graph Design

- **Principio de responsabilidad única**: Cada recurso personalizado debe tener una única responsabilidad clara.
- **Nivel de abstracción adecuado**: Elige un nivel de abstracción adecuado que no sea ni demasiado detallado ni demasiado abstracto.
- **Límites claros**: Define claramente los límites y responsabilidades entre recursos.
- **Reutilización**: Identifica patrones comunes y extráelos en componentes reutilizables.

### 2. State Management

- **Estado significativo**: Proporciona información de estado significativa a los usuarios.
- **Agregación de estado**: Agrega adecuadamente los estados de varios recursos hijo.
- **Definición de condiciones**: Define tipos de condición y estados claros.
- **Información de diagnóstico**: Incluye información de diagnóstico útil para la resolución de problemas.

### 3. Version Management

- **Gestión de versiones de API**: Gestiona correctamente las versiones de API de los recursos personalizados.
- **Conversion Webhooks**: Implementa webhooks para la conversión de versiones.
- **Compatibilidad hacia atrás**: Mantén la compatibilidad hacia atrás siempre que sea posible.
- **Migración gradual**: Introduce cambios grandes de forma gradual.

### 4. Security

- **Mínimo privilegio**: Concede solo los permisos mínimos necesarios a los controllers.
- **Políticas RBAC**: Define políticas RBAC adecuadas para controlar el acceso.
- **Gestión de Secret**: Gestiona la información sensible como Secrets.
- **Validation Webhooks**: Implementa webhooks para la validación de entradas.

## Conclusion

La migración de Helm a KRO es un paso importante hacia la transición a un enfoque nativo de Kubernetes. Esto permite una gestión de aplicaciones más declarativa, extensible y compatible con GitOps. Especialmente para aplicaciones complejas, KRO proporciona un control más detallado y una gestión de versiones mejorada.

ResourceGraphDefinition (RGD) es un concepto central de KRO, que proporciona mecanismos para definir explícitamente las relaciones entre recursos y propagar estados. Esto permite modelar y gestionar con mayor facilidad estructuras de aplicaciones complejas.

El proceso de migración requiere trabajo inicial adicional, pero proporciona beneficios significativos en términos de mantenimiento y operaciones a largo plazo. Mediante un enfoque de migración gradual, puedes minimizar el riesgo mientras aprovechas los beneficios de KRO.

Aunque KRO sigue siendo una tecnología en evolución, representa un enfoque importante que muestra la dirección futura del ecosistema Kubernetes. Conceptos como las APIs declarativas, el modelado de relaciones entre recursos y la propagación de estado se están convirtiendo en principios fundamentales de la gestión de aplicaciones cloud-native.

## Quiz

Para comprobar lo que has aprendido en este capítulo, intenta el [KRO Quiz](../quizzes/platform-engineering/03-kro-quiz.md).
