# Kube Resource Orchestrator (kro)

> **Última actualización**: 23 de octubre de 2026 · **Versión de referencia**: kro 0.9.4

## Conceptos y alcance

El nombre oficial es Kube Resource Orchestrator, un subproyecto de Kubernetes SIG Cloud Provider. Una ResourceGraphDefinition (RGD) define esquemas de entrada, relaciones y estados entre recursos de Kubernetes. Tras la validación y compilación, kro reconcilia dinámicamente instancias de la CRD generada.

Una RGD define una API y un grafo de recursos; no es una instancia de una aplicación. El spec de la instancia proporciona las entradas y las plantillas de `spec.resources` crean objetos como Deployments y Services. Pueden participar CRDs existentes, como los recursos de ACK, pero kro no proporciona sus controladores ni los permisos de AWS IAM correspondientes.

Las expresiones `${...}` dentro del YAML usan CEL. Los ejemplos anteriores que usan .parent, .children, childResources, resourceKind, statusMappings y plantillas de Go no forman parte de esta API. No crees por separado la misma CRD de aplicación ni compitas con la RGD por su propiedad.

## Comparación con Helm, Kustomize y los Operators

| Herramienta | Función principal y límites |
| --- | --- |
| Helm | Renderiza charts con plantillas de Go y administra el historial de las versiones instaladas. Las dependencias de charts de v2 se declaran en Chart.yaml. |
| Kustomize | Transforma manifiestos mediante bases y parches; no es un controlador de ejecución. |
| Operator personalizado | Puede implementar en código recuperaciones, migraciones y copias de seguridad específicas del dominio. |
| kro | Deduce un grafo de recursos a partir de referencias de CEL y reconcilia instancias; no genera algoritmos de recuperación de bases de datos. |

Un chart de Helm puede instalar kro mientras GitOps administra las RGD y sus instancias. Estas herramientas pueden trabajar juntas. Pasar de Helm a kro no mejora automáticamente la seguridad, la recuperación ni las operaciones. Los controladores de Deployment de Kubernetes también siguen administrando los Deployments creados originalmente por Helm.

## Instalación y permisos

El repositorio oficial es kubernetes-sigs/kro; las rutas antiguas de kro-run pueden redirigir a otras. Esto es una **inspección sin conexión** de un chart OCI fijado a una versión. No uses las antiguas URL de descarga de kro-project ni inventes comandos de instalación de la CLI. Esta versión no distribuye un binario de CLI independiente; usa kubectl y Helm.

```bash
helm template kro oci://registry.k8s.io/kro/charts/kro \
  --version 0.9.4 --namespace kro-system \
  --set rbac.mode=aggregation --include-crds
```

Antes de la instalación, verifica que la versión de Kubernetes sea compatible, así como las políticas de admisión, los namespaces y las CRD o los controladores existentes. La lista anterior de las versiones 1.31–1.33 no se presenta como una descripción de la compatibilidad actual. Helm upgrade no actualiza automáticamente crds/; revisa la versión 0.9.4 y los cambios en las CRD mediante un proceso independiente.

El valor predeterminado `rbac.mode=unrestricted` concede acceso amplio al clúster. El ejemplo renderiza el modo de agregación, que aun así incluye permisos básicos para CRD, RGD, GraphRevisions y ConfigMaps. Añade permisos para la API de la aplicación generada y los recursos secundarios. Este ClusterRole permite los tipos de recursos del ejemplo y puede conceder acceso a todo el clúster. Los administradores de plataforma de confianza deben controlar las RGD y las etiquetas de agregación.

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: kro:controller:reviewed-nginxapps
  labels:
    rbac.kro.run/aggregate-to-controller: "true"
rules:
  - apiGroups: [platform.example.com]
    resources: [nginxapps]
    verbs: [get, list, watch, create, update, patch, delete]
  - apiGroups: [platform.example.com]
    resources: [nginxapps/status, nginxapps/finalizers]
    verbs: [get, update, patch]
  - apiGroups: [apps]
    resources: [deployments]
    verbs: [get, list, watch, create, update, patch, delete]
  - apiGroups: [""]
    resources: [services]
    verbs: [get, list, watch, create, update, patch, delete]
  - apiGroups: [networking.k8s.io]
    resources: [ingresses]
    verbs: [get, list, watch, create, update, patch, delete]
```

## Ejemplo completo de NginxApp

Los archivos de la RGD, la instancia y RBAC también están en examples/platform/kro. Ingress está deshabilitado de forma predeterminada. Antes de habilitarlo, prepara una IngressClass/controlador aprobado, el DNS del host y un Secret de TLS en el mismo namespace. La cadena `className=internal` por sí sola no configura un balanceador de carga interno. Este ejemplo permite que las instancias establezcan directamente `ingress.className` y `ingress.host`, lo que en un clúster multiinquilino podría utilizarse para apropiarse del host de otro equipo. En las RGD de producción, fija la clase y deriva el host del nombre y el namespace de la instancia.

La imagen usa la misma etiqueta de nginx-unprivileged que el ejemplo de Helm. Se configuran un UID sin privilegios de root, un sistema de archivos raíz de solo lectura y un volumen /tmp, pero no se probó la ejecución de la imagen. Verifica los digests, la arquitectura y las políticas antes del despliegue.

### ResourceGraphDefinition

```yaml
apiVersion: kro.run/v1alpha1
kind: ResourceGraphDefinition
metadata:
  name: reviewed-nginxapps
spec:
  schema:
    apiVersion: v1alpha1
    group: platform.example.com
    kind: NginxApp
    scope: Namespaced
    spec:
      replicas: integer | default=2 minimum=1 maximum=5
      image: string | default="nginxinc/nginx-unprivileged:1.30.6-alpine"
      ingress:
        enabled: boolean | default=false
        className: string | default="internal"
        host: string | default="app.example.com"
        tlsSecret: string | default="app-tls"
    status:
      availableReplicas: ${deployment.status.availableReplicas}
      serviceIP: ${service.spec.clusterIP}
  resources:
    - id: deployment
      readyWhen:
        - ${deployment.status.availableReplicas >= deployment.spec.replicas}
        - ${deployment.status.observedGeneration >= deployment.metadata.generation}
      template:
        apiVersion: apps/v1
        kind: Deployment
        metadata:
          name: ${schema.metadata.name}
          namespace: ${schema.metadata.namespace}
          labels:
            app.kubernetes.io/name: ${schema.metadata.name}
        spec:
          replicas: ${schema.spec.replicas}
          selector:
            matchLabels:
              app.kubernetes.io/name: ${schema.metadata.name}
          template:
            metadata:
              labels:
                app.kubernetes.io/name: ${schema.metadata.name}
            spec:
              automountServiceAccountToken: false
              securityContext:
                runAsNonRoot: true
                runAsUser: 101
                runAsGroup: 101
                fsGroup: 101
                seccompProfile:
                  type: RuntimeDefault
              containers:
                - name: web
                  image: ${schema.spec.image}
                  ports:
                    - name: http
                      containerPort: 8080
                  securityContext:
                    allowPrivilegeEscalation: false
                    readOnlyRootFilesystem: true
                    capabilities:
                      drop: [ALL]
                  resources:
                    requests:
                      cpu: 100m
                      memory: 64Mi
                    limits:
                      cpu: 500m
                      memory: 128Mi
                  readinessProbe:
                    httpGet:
                      path: /
                      port: http
                  volumeMounts:
                    - name: tmp
                      mountPath: /tmp
              volumes:
                - name: tmp
                  emptyDir:
                    sizeLimit: 64Mi
    - id: service
      template:
        apiVersion: v1
        kind: Service
        metadata:
          name: ${schema.metadata.name}
          namespace: ${schema.metadata.namespace}
          labels:
            app.kubernetes.io/name: ${schema.metadata.name}
        spec:
          type: ClusterIP
          selector: ${deployment.spec.selector.matchLabels}
          ports:
            - name: http
              port: 8080
              targetPort: http
    - id: ingress
      includeWhen:
        - ${schema.spec.ingress.enabled}
      template:
        apiVersion: networking.k8s.io/v1
        kind: Ingress
        metadata:
          name: ${schema.metadata.name}
          namespace: ${schema.metadata.namespace}
          labels:
            app.kubernetes.io/name: ${schema.metadata.name}
        spec:
          ingressClassName: ${schema.spec.ingress.className}
          tls:
            - hosts:
                - ${schema.spec.ingress.host}
              secretName: ${schema.spec.ingress.tlsSecret}
          rules:
            - host: ${schema.spec.ingress.host}
              http:
                paths:
                  - path: /
                    pathType: Prefix
                    backend:
                      service:
                        name: ${service.metadata.name}
                        port:
                          number: 8080
```

### Instancia

```yaml
apiVersion: platform.example.com/v1alpha1
kind: NginxApp
metadata:
  name: reviewed-web
  namespace: example
spec:
  replicas: 2
  image: nginxinc/nginx-unprivileged:1.30.6-alpine
  ingress:
    enabled: false
    className: internal
    host: app.example.com
    tlsSecret: app-tls
```

SimpleSchema en `schema.spec` describe los tipos, los valores predeterminados y los límites; kro lo convierte en el esquema OpenAPI de la CRD generada. `schema.metadata/spec` en CEL hace referencia a la instancia, mientras que `deployment/service` hace referencia a los ID de los recursos. Define el estado proyectado bajo `schema.status`.

La condición `readyWhen` de este ejemplo comprueba los campos `availableReplicas` y `observedGeneration` del propio Deployment. Sin condiciones de preparación, la existencia y las referencias resolubles pueden bastar para avanzar. `readyWhen` debe devolver valores booleanos y hacer referencia únicamente al ID de su propio recurso. Los SLO de la aplicación y las comprobaciones de la base de datos se gestionan por separado.

El Service hace referencia al selector del Deployment y el Ingress al nombre del Service, lo que crea dependencias. Los recursos independientes pueden estar en la misma etapa; los ciclos se rechazan. `includeWhen` controla la inclusión condicional y puede añadir o eliminar recursos cuando cambian las condiciones. Un `externalRef` a un recurso existente no es lo mismo que asumir su propiedad para crearlo o eliminarlo.

### Orden de aplicación e inspección

En un clúster aprobado, aplica el RBAC revisado y la RGD, verifica que la RGD esté Active y que la CRD generada `nginxapps.platform.example.com` esté Established, y luego aplica la instancia. Que `kubectl apply` finalice correctamente no demuestra que el grafo se haya compilado ni que la aplicación esté lista.

```bash
kubectl get rgd reviewed-nginxapps -o yaml
kubectl get graphrevisions \
  -l internal.kro.run/resource-graph-definition-name=reviewed-nginxapps
kubectl get crd nginxapps.platform.example.com -o yaml
kubectl get nginxapps.platform.example.com reviewed-web -n example -o yaml
kubectl get deployments,services,ingresses -n example \
  -l app.kubernetes.io/name=reviewed-web
```

## GraphRevisions y cambios

La versión 0.9.4 registra y compila GraphRevisions inmutables cuando cambian los specs de las RGD. Si la revisión más reciente falla, no se vuelve automáticamente a la anterior; el avance de las instancias puede detenerse. Inspecciona GraphAccepted, GraphVerified, GraphRevisionsResolved y los mensajes de error; luego aplica un spec válido.

GraphRevision es una API internal.kro.run. Úsala para inspeccionar y diagnosticar, sin dar por sentados contratos estables de herramientas externas. Revertir un spec de Git sigue requiriendo su validación en una revisión nueva y no revierte transaccionalmente los datos de la base de datos ni los efectos externos.

Group, kind, apiVersion y scope son inmutables dentro de una RGD. Distingue la evolución compatible del esquema de la migración a una API nueva, y revisa las instancias existentes y los datos almacenados. No des por sentado que se generan automáticamente webhooks de conversión.

## Eliminación y propiedad

Cuando se elimina una instancia, kro utiliza el inventario de ApplySet y etapas de eliminación para quitar primero los recursos dependientes; conserva su finalizer hasta que desaparezcan los recursos administrados. Los finalizers de los recursos secundarios pueden bloquear las etapas siguientes. Las referencias externas son de solo lectura y kro nunca las elimina.

No es correcto afirmar que todos los recursos secundarios se recolectan inmediatamente como basura. Inspecciona `ResourcesReady=Unknown/UnderDeletion`, el inventario y los finalizers de los recursos secundarios. Planifica la limpieza y la retención de las instancias, las RGD, las CRD y los datos antes de quitar controladores. Eliminar una CRD también afecta a los datos de sus instancias.

## Migración y operaciones

Revisa los nombres, los selectores, la propiedad, los administradores de campos y los controladores de GitOps para evitar que Helm y kro compitan por un objeto. Elige entre un grafo nuevo con nombre validado y cambio de tráfico, o un proceso revisado de transferencia de propiedad. No migres desinstalando a la ligera una versión instalada que sea propietaria de StatefulSets, PVC o bases de datos.

Usa el mismo contrato de API y los mismos digests de imagen revisados en todos los entornos, con instancias independientes para los namespaces, las réplicas, Ingress y las políticas. Las herramientas de gestión de flotas, como ApplicationSet, requieren kro, RGD y permisos en cada clúster de destino. kro no se conecta automáticamente a clústeres remotos arbitrarios.

Las aplicaciones con estado siguen necesitando las funciones de copia de seguridad, restauración, conmutación por error y migración de un Operator de bases de datos o de un servicio administrado. La reconciliación de recursos por sí sola no recupera los datos. Limita el tamaño del grafo y los permisos, define unidades reutilizables y expón únicamente estados útiles. No copies el contenido de los Secret en el estado, las etiquetas ni los registros.

## kro administrado por EKS

La capacidad kro de EKS Capabilities ejecuta el mismo controlador de upstream (versión medida: `0.9.4-eks-1`) en infraestructura propiedad de AWS. En las pruebas de octubre de 2026 se usó la RGD `NginxApp` de este capítulo, modificada para fijar la clase y el host de Ingress; las expresiones CEL funcionaron sin cambios y los tiempos del ciclo de vida de la instancia coincidieron con los de OSS. Las diferencias están en los permisos y las operaciones.

- La política de acceso predeterminada de la access entry, `AmazonEKSKROPolicy`, cubre solo `kro.run` y las CRD. Asocia un ClusterRole como `kro:controller:reviewed-nginxapps`, mostrado arriba, a un grupo de Kubernetes en la access entry; sin él, la RGD informa `ControllerReady=False` con `cache sync timeout`, no `forbidden`. Las reglas son las mismas; solo cambia el mecanismo de asociación (grupo en lugar de etiqueta de agregación).
- AWS elige la versión y no puedes fijarla. Tampoco se pueden cambiar los flags del controlador ni los límites de recursos.
- Si en el namespace existe una CR con el mismo nombre que un recurso secundario, kro se apropia de ella y la sobrescribe (OSS se comporta igual). Añade sufijos específicos de la RGD a los nombres de los recursos secundarios.

Para consultar mediciones y orientación sobre la selección, consulta [EKS Capabilities](../eks/13-eks-capabilities.md).

## Verificación y referencias

Se revisaron ambas guías originales de 504 líneas y los cuestionarios de 423 líneas, incluidos 16 bloques de código únicos y 20 temas de preguntas por idioma. Se renderizó el chart oficial de kro 0.9.4 en modo de agregación y se comprobó la estructura de la RGD. Su dependencia cel-go 0.31.0 compiló y evaluó las 14 expresiones publicadas únicas. Se probaron cuatro casos sintéticos: Ingress habilitado y deshabilitado, réplicas insuficientes y `observedGeneration` obsoleto.

Estas son comprobaciones de CEL con entradas sintéticas dinámicas, no una validación con el compilador completo de grafos de kro, la detección de la API de Kubernetes, la admisión de la CRD generada ni un controlador en ejecución. No se ejecutaron contenedores, Ingress/TLS, bases de datos ni recursos del clúster.

- [kro 0.9.4](https://github.com/kubernetes-sigs/kro/releases/tag/v0.9.4)
- [API y código fuente por versión](https://github.com/kubernetes-sigs/kro/tree/v0.9.4)
- [Esquema de RGD](https://github.com/kubernetes-sigs/kro/blob/v0.9.4/website/docs/docs/concepts/rgd/01-schema.md)
- [Control de acceso](https://github.com/kubernetes-sigs/kro/blob/v0.9.4/website/docs/docs/advanced/01-access-control.md)
- [Revisiones del grafo](https://github.com/kubernetes-sigs/kro/blob/v0.9.4/website/docs/docs/advanced/05-graph-revisions.md)
- [Eliminación de instancias](https://github.com/kubernetes-sigs/kro/blob/v0.9.4/website/docs/docs/advanced/06-instance-deletion.md)

[Cuestionario de kro](../quizzes/platform-engineering/03-kro-quiz.md)
