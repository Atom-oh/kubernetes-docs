# Cuestionario de Kube Resource Orchestrator (kro)

[kro](../../platform-engineering/03-kro.md)

Estas preguntas conservan los 20 temas originales usando kro 0.9.4.

## 1. ¿Cuáles son los conceptos principales de kro?

<details>
<summary>Mostrar respuesta</summary>

Define esquemas de API y grafos de recursos en RGD, infiere dependencias a partir de referencias CEL y reconcilia instancias. kro no es un ejecutor de scripts imperativos.

</details>

## 2. ¿Dónde se declaran las definiciones de recursos administrados?

<details>
<summary>Mostrar respuesta</summary>

En spec.resources, mediante el id de cada entrada y template o externalRef. El anterior childResources no es un campo actual de RGD.

</details>

## 3. ¿Qué proporciona kro junto con Helm?

<details>
<summary>Mostrar respuesta</summary>

Un grafo de referencias de recursos y reconciliación continua de instancias. Helm proporciona renderizado de charts y gestión de releases; pueden funcionar juntos. Ninguno es universalmente mejor para cada carga de trabajo.

</details>

## 4. ¿Cómo se hace referencia a las entradas de instancia en CEL?

<details>
<summary>Mostrar respuesta</summary>

Usa `schema.spec` o `schema.metadata`, como `${schema.spec.replicas}`. No uses `.parent` ni sintaxis de plantillas Go.

</details>

## 5. ¿Cómo se configura la inclusión condicional de recursos?

<details>
<summary>Mostrar respuesta</summary>

Usa expresiones CEL booleanas en `includeWhen`. Cambiar las condiciones puede añadir o eliminar recursos, por lo que hay que revisar las implicaciones del ciclo de vida para los recursos con estado.

</details>

## 6. ¿Dónde se proyectan los valores de estado de los recursos administrados?

<details>
<summary>Mostrar respuesta</summary>

Define expresiones CEL en `spec.schema.status`, por ejemplo `${deployment.status.availableReplicas}`. `statusMappings` no es un campo actual.

</details>

## 7. ¿Cómo se ordenan las dependencias y la preparación?

<details>
<summary>Mostrar respuesta</summary>

Las referencias CEL a otros ID de recursos infieren un DAG. Los dependientes también esperan las condiciones `readyWhen` cuando están presentes. Los ciclos se rechazan; el orden de listado de YAML no sustituye a las dependencias.

</details>

## 8. ¿Qué sucede cuando se elimina una instancia?

<details>
<summary>Mostrar respuesta</summary>

El kro actual usa el inventario de ApplySet y oleadas de eliminación para eliminar primero los dependientes, conservando un finalizer. Los finalizers secundarios pueden bloquear el progreso. Los destinos de referencias externas no se eliminan.

</details>

## 9. ¿Qué observa los cambios de instancias?

<details>
<summary>Mostrar respuesta</summary>

Los controladores dinámicos de instancias de kro observan los cambios y reconcilian grafos. La validación y compilación de RGD/GraphRevision afectan el progreso de las instancias.

</details>

## 10. ¿Qué hace kubectl apply?

<details>
<summary>Mostrar respuesta</summary>

Crea o actualiza el estado deseado del CR, tras lo cual los controladores reconcilian. El éxito de apply no equivale a la compilación del grafo ni a que la aplicación esté lista, y no garantiza efectos externos transaccionales.

</details>

## 11. ¿Qué es un RGD?

<details>
<summary>Mostrar respuesta</summary>

ResourceGraphDefinition define el esquema de API generado, los recursos administrados y las relaciones de estado. Es distinto de un CR de instancia de aplicación.

</details>

## 12. ¿Qué proporciona entradas análogas a los valores de Helm?

<details>
<summary>Mostrar respuesta</summary>

El campo `spec` de la instancia de API generada. Sus tipos, valores predeterminados y límites de SimpleSchema deben coincidir con los campos que realmente consumen las plantillas.

</details>

## 13. ¿Cómo se hace referencia a otro recurso?

<details>
<summary>Mostrar respuesta</summary>

Haz referencia directamente a su ID de recurso, como `${deployment.spec.selector.matchLabels}` o `${service.metadata.name}`. No uses .children.

</details>

## 14. ¿Qué rastrea los recursos administrados y permite diagnosticar eliminaciones?

<details>
<summary>Mostrar respuesta</summary>

Inspecciona el inventario actual de ApplySet, los metadatos del propietario y las oleadas de eliminación `internal.kro.run/apply-order`. No trates una anotación inventada `kro.run/owner` como si fuera todo el contrato de seguimiento.

</details>

## 15. ¿Cómo se validan los esquemas de entrada?

<details>
<summary>Mostrar respuesta</summary>

SimpleSchema se convierte en el esquema OpenAPI del CRD generado, que Kubernetes usa para validar instancias. La estructura de RGD, la comprobación de tipos CEL del compilador de grafos y la preparación en tiempo de ejecución son verificaciones independientes.

</details>

## 16. Escribe la instancia de ejemplo NginxApp.

<details>
<summary>Mostrar respuesta</summary>

Primero asegúrate de que el RGD esté Active y que su CRD generado esté Established. Esta instancia deshabilita ingress.

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

</details>

## 17. Escribe la entrada de recurso que crea un Deployment.

<details>
<summary>Mostrar respuesta</summary>

Esta es la misma plantilla que la guía. `readyWhen` solo se refiere al propio Deployment; verifica la imagen, el namespace y las políticas en el entorno real.

```yaml
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
                drop:
                - ALL
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
```

</details>

## 18. Expón `availableReplicas` en `status`.

<details>
<summary>Mostrar respuesta</summary>

Esta es la sección `status` dentro de `spec.schema` del RGD. La resolución puede esperar valores faltantes; no representa de forma exhaustiva la salud de la aplicación.

```yaml
status:
  availableReplicas: ${deployment.status.availableReplicas}
  serviceIP: ${service.spec.clusterIP}
```

</details>

## 19. Diseña una estrategia para desarrollo, staging y producción.

<details>
<summary>Mostrar respuesta</summary>

Comparte un contrato de API validado y los digests de las imágenes, y separa los namespaces, las réplicas, el ingress y las políticas por instancia. Prepara kro/RGD/permisos en cada clúster y usa herramientas de flota para sincronizarlos. Los campos de autoscaling que no se usan no crean un HPA.

</details>

## 20. ¿Cuáles son los límites de Helm y kro para aplicaciones con estado?

<details>
<summary>Mostrar respuesta</summary>

Ninguno implementa automáticamente copias de seguridad, restauración, conmutación por error o migración de esquemas de bases de datos. Valida el comportamiento de un operator dedicado o de un servicio administrado, así como la retención de datos. Restaurar una especificación de Git no revierte la base de datos; las GraphRevisions fallidas más recientes no vuelven automáticamente a una versión anterior.

</details>
