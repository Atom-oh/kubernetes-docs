# Kube Resource Orchestrator (kro)

> **Última actualización**: September 12, 2026 · **Referencia**: kro 0.9.4

## Conceptos y alcance

El nombre oficial es Kube Resource Orchestrator, un subproyecto de Kubernetes SIG Cloud Provider. Una ResourceGraphDefinition (RGD) define esquemas de entrada, relaciones y estado entre recursos de Kubernetes. Tras la validación y compilación, kro reconcilia dinámicamente instancias del CRD generado.

Una RGD define una API y un grafo de recursos; no es una instancia de aplicación. El spec de la instancia proporciona entradas y las plantillas de spec.resources crean objetos como Deployments y Services. Los CRDs existentes, como los recursos ACK, pueden participar, pero kro no proporciona sus controllers ni permisos de AWS IAM.

Las expresiones `${...}` dentro de YAML usan CEL. Los ejemplos anteriores de .parent, .children, childResources, resourceKind, statusMappings y Go-template no pertenecen a esta API. No cree de forma independiente el mismo CRD de aplicación ni compita con la RGD por la propiedad.

## Comparación con Helm, Kustomize y Operators

| Herramienta | Función y límite principales |
| --- | --- |
| Helm | Renderiza charts de Go-template y administra el historial de releases. Las dependencias de charts v2 se declaran en Chart.yaml. |
| Kustomize | Transforma manifiestos mediante bases y patches; no es un controller de tiempo de ejecución. |
| Custom operator | Puede implementar en código recuperación, migraciones y backups específicos del dominio. |
| kro | Infiere un grafo de recursos a partir de referencias CEL y reconcilia instancias; no genera algoritmos de recuperación de bases de datos. |

Un chart de Helm puede instalar kro mientras GitOps administra RGDs e instancias. Estas herramientas pueden trabajar juntas. Migrar de Helm a kro no mejora automáticamente la seguridad, la recuperación ni las operaciones. Los controllers de Kubernetes Deployment también siguen administrando los Deployments creados originalmente por Helm.

## Instalación y permisos

El repositorio oficial es kubernetes-sigs/kro; las rutas antiguas de kro-run podrían redirigir. Esta es una **inspección sin conexión** de un chart OCI fijado. No use las antiguas URL de descarga de kro-project ni una instalación de CLI inventada. Esta release no distribuye un binario de CLI independiente; use kubectl y Helm.

```bash
helm template kro oci://registry.k8s.io/kro/charts/kro \
  --version 0.9.4 --namespace kro-system \
  --set rbac.mode=aggregation --include-crds
```

Antes de la instalación, verifique una versión de Kubernetes compatible, las políticas de admisión, los namespaces y los CRDs/controllers existentes. La anterior lista 1.31–1.33 no se presenta como compatibilidad actual. Helm upgrade no actualiza automáticamente crds/; revise la release 0.9.4 y los cambios de CRD mediante un proceso independiente.

El valor predeterminado rbac.mode=unrestricted concede acceso amplio al clúster. El ejemplo renderiza el modo aggregation, que aún incluye permisos básicos para CRDs, RGDs, GraphRevisions y ConfigMaps. Añada permisos para la API de aplicación generada y los recursos secundarios. Este ClusterRole permite los tipos de recursos del ejemplo y puede conceder acceso en todo el clúster. Los administradores de plataforma de confianza deben controlar las RGDs y las etiquetas de agregación.

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

Los archivos RGD, de instancia y RBAC también están en examples/platform/kro. Ingress está deshabilitado de forma predeterminada. Antes de habilitarlo, prepare un IngressClass/controller aprobado, el DNS del host y un TLS Secret en el mismo namespace. La cadena className=internal por sí sola no configura un balanceador de carga interno.

La imagen utiliza la misma etiqueta nginx-unprivileged que el ejemplo de Helm. Se configuran un UID no root, una raíz de solo lectura y un volumen /tmp, pero la ejecución de la imagen no se probó. Verifique los digests, la arquitectura y las políticas para el despliegue.

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
      image: string | default="nginxinc/nginx-unprivileged:1.30.4-alpine"
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
  image: nginxinc/nginx-unprivileged:1.30.4-alpine
  ingress:
    enabled: false
    className: internal
    host: app.example.com
    tlsSecret: app-tls
```

SimpleSchema en schema.spec describe los tipos, los valores predeterminados y los límites; kro lo convierte en el esquema OpenAPI del CRD generado. CEL schema.metadata/spec se refiere a la instancia, mientras que deployment/service se refiere a IDs de recursos. Defina el estado proyectado bajo schema.status.

El readyWhen de este ejemplo comprueba los propios availableReplicas y observedGeneration del Deployment. Sin condiciones de preparación, la existencia y las referencias resolubles pueden bastar para avanzar. readyWhen debe devolver valores Boolean y referirse únicamente a su propio ID de recurso. Los SLO de la aplicación y las comprobaciones de bases de datos permanecen separados.

El Service hace referencia al selector del Deployment y el Ingress al nombre del Service, lo que crea dependencias. Los recursos independientes pueden compartir una wave; se rechazan los ciclos. includeWhen controla la inclusión condicional y puede añadir o eliminar recursos cuando cambian las condiciones. Un externalRef a un recurso existente es diferente de asumir la propiedad para crearlo o eliminarlo.

### Orden de aplicación e inspección

En un clúster aprobado, aplique el RBAC revisado y la RGD, verifique que la RGD esté Active y que el CRD generado nginxapps.platform.example.com esté Established, y después aplique la instancia. Un kubectl apply exitoso no prueba la compilación del grafo ni la preparación de la aplicación.

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

La versión 0.9.4 registra y compila GraphRevisions inmutables cuando cambian los specs de RGD. Una revisión reciente fallida no vuelve automáticamente a la anterior; el progreso de la instancia puede detenerse. Inspeccione GraphAccepted, GraphVerified, GraphRevisionsResolved y los mensajes de error, y después aplique un spec válido.

GraphRevision es una API internal.kro.run. Úsela para inspección y diagnóstico sin asumir contratos estables de herramientas externas. Revertir un spec de Git sigue requiriendo validación en una nueva revisión y no revierte transaccionalmente los datos de la base de datos ni los efectos externos.

Group, kind, apiVersion y scope son inmutables dentro de una RGD. Distinga la evolución de esquema compatible de la migración a una nueva API y revise las instancias existentes y los datos almacenados. No suponga que los webhooks de conversión se generan automáticamente.

## Eliminación y propiedad

Cuando se elimina una instancia, kro usa el inventario ApplySet y waves de eliminación para eliminar primero los dependientes, y conserva su finalizer hasta que desaparecen los recursos administrados. Los finalizers secundarios pueden bloquear las waves posteriores. Las referencias externas son de solo lectura y kro nunca las elimina.

Es inexacto afirmar que todos los secundarios se recolectan inmediatamente mediante garbage collection. Inspeccione ResourcesReady=Unknown/UnderDeletion, el inventario y los finalizers secundarios. Planifique la limpieza y retención de instancias, RGDs, CRDs y datos antes de eliminar controllers. La eliminación del CRD también afecta los datos de instancia.

## Migración y operaciones

Revise los nombres, selectores, propiedad, field managers y controllers de GitOps para que Helm y kro no compitan por un objeto. Elija un grafo validado con nombre nuevo y cambio de tráfico, o un proceso revisado de transferencia de propiedad. No migre desinstalando de manera informal una release que posee StatefulSets, PVCs o bases de datos.

Use el mismo contrato de API y los digests de imagen revisados en todos los entornos, con instancias separadas para namespaces, réplicas, ingress y políticas. Las herramientas de flota como ApplicationSet requieren kro, RGDs y permisos en cada clúster de destino. kro no se conecta automáticamente a clústeres remotos arbitrarios.

Las aplicaciones con estado aún necesitan comportamiento de backup, restauración, failover y migración de un database-operator o un servicio administrado. La reconciliación de recursos por sí sola no es recuperación de datos. Limite el tamaño y los permisos del grafo, defina unidades reutilizables y exponga solo estado útil. No copie el contenido de Secret en estado, etiquetas ni logs.

## Verificación y referencias

Se revisaron tanto las guías originales de 504 líneas como los cuestionarios de 423 líneas, incluidos 16 bloques de código únicos y 20 temas de preguntas por idioma. El chart oficial de kro 0.9.4 se renderizó en modo aggregation y se comprobó la estructura de RGD. Su dependencia cel-go 0.31.0 compiló y evaluó las 14 expresiones publicadas únicas. Cuatro casos sintéticos cubrieron Ingress activado/desactivado, réplicas insuficientes y observedGeneration obsoleto.

Estas son comprobaciones CEL con entradas sintéticas dinámicas, no validación mediante el compilador completo de grafos de kro, el descubrimiento de API de Kubernetes, la admisión del CRD generado ni un controller en ejecución. No se ejecutaron Containers, Ingress/TLS, bases de datos ni recursos de clúster.

- [kro 0.9.4](https://github.com/kubernetes-sigs/kro/releases/tag/v0.9.4)
- [API versionada y código fuente](https://github.com/kubernetes-sigs/kro/tree/v0.9.4)
- [Esquema de RGD](https://github.com/kubernetes-sigs/kro/blob/v0.9.4/website/docs/docs/concepts/rgd/01-schema.md)
- [Control de acceso](https://github.com/kubernetes-sigs/kro/blob/v0.9.4/website/docs/docs/advanced/01-access-control.md)
- [Revisiones de grafo](https://github.com/kubernetes-sigs/kro/blob/v0.9.4/website/docs/docs/advanced/05-graph-revisions.md)
- [Eliminación de instancias](https://github.com/kubernetes-sigs/kro/blob/v0.9.4/website/docs/docs/advanced/06-instance-deletion.md)

[kro quiz](../quizzes/platform-engineering/03-kro-quiz.md)
