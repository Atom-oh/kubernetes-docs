# Cuestionario sobre mecanismos de extensión de Kubernetes

[Kubernetes extensions](../../platform-engineering/04-kubernetes-extensions.md)

Los temas originales de las 20 preguntas se han revisado conforme a las API y el comportamiento actuales.

## 1. ¿Para qué sirve un CRD?

<details>
<summary>Mostrar respuesta</summary>

Registra tipos de recursos personalizados y esquemas de entrada en la API de Kubernetes. Un CRD no implementa por sí mismo el comportamiento de una carga de trabajo.

</details>

## 2. ¿Qué hace un bucle de reconciliación?

<details>
<summary>Mostrar respuesta</summary>

Reconcilia el estado observado y el deseado mientras gestiona eventos repetidos, reinicios y conflictos. Evita actualizaciones innecesarias cuando el estado ya coincide.

</details>

## 3. ¿Qué define a un Operator y cuáles son sus límites?

<details>
<summary>Mostrar respuesta</summary>

Un Operator implementa conocimiento del dominio mediante API y controllers personalizados. Crearlos por sí solos no hace que las copias de seguridad, la conmutación por error ni las actualizaciones sean seguras.

</details>

## 4. ¿Qué puede devolver un mutating webhook?

<details>
<summary>Mostrar respuesta</summary>

Una respuesta AdmissionReview que permite o rechaza la solicitud y, opcionalmente, incluye JSONPatch. Conserva el UID/la versión de la solicitud; los bytes del parche se codifican en Base64.

</details>

## 5. ¿Qué hace un plugin Filter?

<details>
<summary>Mostrar respuesta</summary>

Excluye Nodes que no pueden satisfacer los requisitos de un Pod. Superar los filtros no completa el binding ni la ejecución.

</details>

## 6. ¿En qué se diferencian la agregación y los CRD?

<details>
<summary>Mostrar respuesta</summary>

Los CRD usan el almacenamiento/la validación de recursos personalizados del API server existente. La agregación delega en un servidor independiente que requiere operaciones de TLS, autenticación, autorización, descubrimiento y almacenamiento.

</details>

## 7. ¿Qué proporciona un finalizer?

<details>
<summary>Mostrar respuesta</summary>

Da a un controller la oportunidad de finalizar la limpieza antes de que se complete la eliminación. La cadena no ejecuta ninguna limpieza por sí misma; eliminarla sin investigar puede dejar recursos externos.

</details>

## 8. ¿Cuándo se ejecuta PostBind?

<details>
<summary>Mostrar respuesta</summary>

Es una fase informativa después de un binding exitoso, no una recuperación de errores universal. Implementa rutas como Unreserve para reservas fallidas o canceladas.

</details>

## 9. ¿Cómo se controla la inyección actual por Pod de Istio?

<details>
<summary>Mostrar respuesta</summary>

Configura sidecar.istio.io/inject en las etiquetas del Pod o de la plantilla de Pod de la carga de trabajo. Comprueba las etiquetas de inyección/revisión del namespace y la precedencia, en lugar de usar anotaciones antiguas como valores predeterminados.

</details>

## 10. ¿Cómo se usan los resultados de Score?

<details>
<summary>Mostrar respuesta</summary>

Clasifican los Nodes viables combinando la normalización y los pesos de los plugins. La selección en caso de empate y la gestión de errores también forman parte del comportamiento del scheduler.

</details>

## 11. ¿Dónde deben ubicarse los esquemas de CRD y los campos obligatorios?

<details>
<summary>Mostrar respuesta</summary>

En spec.versions[].schema.openAPIV3Schema. required: [spec] en el nivel superior y required: [image] dentro de spec imponen condiciones diferentes.

</details>

## 12. ¿Qué debe comprobarse para ownerReferences?

<details>
<summary>Mostrar respuesta</summary>

Comprueba el UID del propietario, el namespace/ámbito y la propiedad existente del controller. GC depende de la propagación/los finalizers; los nombres coincidentes no autorizan adoptar otra carga de trabajo.

</details>

## 13. ¿En qué se diferencian VAP y los validating webhooks?

<details>
<summary>Mostrar respuesta</summary>

ValidatingAdmissionPolicy es estable desde la versión 1.30 y evalúa CEL en el proceso. Los webhooks requieren llamadas remotas, TLS y gestión de disponibilidad. VAP también necesita un binding para el ámbito y validationActions.

</details>

## 14. ¿Qué proporciona controller-runtime?

<details>
<summary>Mostrar respuesta</summary>

Managers, clients/caches, configuración de reconciliación y elección de líder. No proporciona tipos de API personalizados, schemes, RBAC ni lógica de dominio; alinea las versiones de la biblioteca y del módulo Go de Kubernetes.

</details>

## 15. ¿Para qué sirve un webhook de conversión?

<details>
<summary>Mostrar respuesta</summary>

Convierte representaciones entre versiones de API de un CRD. Revisa las versiones servidas/de almacenamiento, storedVersions y la preservación semántica. No todos los CRD requieren un webhook de conversión.

</details>

## 16. Escribe un CRD WebApp que requiera image y replicas entre 1 y 5.

<details>
<summary>Mostrar respuesta</summary>

Esto también requiere spec y separa las rutas de status/scale. Un controller debe completar status.replicas y selector reales.

```yaml
apiVersion: apiextensions.k8s.io/v1
kind: CustomResourceDefinition
metadata:
  name: webapps.apps.example.com
spec:
  group: apps.example.com
  names:
    kind: WebApp
    plural: webapps
    singular: webapp
    shortNames: [wa]
  scope: Namespaced
  versions:
    - name: v1
      served: true
      storage: true
      schema:
        openAPIV3Schema:
          type: object
          required: [spec]
          properties:
            spec:
              type: object
              required: [image]
              properties:
                replicas:
                  type: integer
                  default: 1
                  minimum: 1
                  maximum: 5
                image:
                  type: string
                  minLength: 1
                port:
                  type: integer
                  default: 8080
                  minimum: 1
                  maximum: 65535
            status:
              type: object
              properties:
                replicas:
                  type: integer
                availableReplicas:
                  type: integer
                selector:
                  type: string
                observedGeneration:
                  type: integer
                  format: int64
      subresources:
        status: {}
        scale:
          specReplicasPath: .spec.replicas
          statusReplicasPath: .status.replicas
          labelSelectorPath: .status.selector
```

</details>

## 17. ¿Cómo debe limitarse un validating webhook de Deployment al entorno de producción?

<details>
<summary>Mostrar respuesta</summary>

Haz coincidir los deployments de apps/v1 CREATE/UPDATE y selecciona kubernetes.io/metadata.name: production. Configura un servidor/Service/ruta de validación real, el paquete CA, failurePolicy, timeoutSeconds, sideEffects y admissionReviewVersions. El controlador /mutate de la guía no es un validador de Deployment. Para un límite de réplicas por sí solo, usa su ejemplo de VAP/binding y haz coincidir tanto `deployments` como `deployments/scale`, de modo que las actualizaciones de HPA y `kubectl scale` no puedan omitir el límite.

</details>

## 18. Describe una secuencia de reconciliación sólida.

<details>
<summary>Mostrar respuesta</summary>

Trata NotFound como una finalización exitosa. Durante la eliminación, termina la limpieza idempotente antes de eliminar únicamente tu finalizer. Conserva un finalizer antes de crear recursos externos, comprueba la propiedad de los recursos secundarios y reconcilia los campos de tu propiedad. Reintenta los conflictos y aplica parches al status observado que haya cambiado. No etiquetes pseudocódigo como un controller ejecutable.

</details>

## 19. ¿Qué se necesita al diseñar un Operator de base de datos distribuida?

<details>
<summary>Mostrar respuesta</summary>

Además de los esquemas y la creación de cargas de trabajo, diseña el fencing del primario, el quórum, la sincronización de réplicas, las pruebas de recuperación de backup/WAL, el ciclo de vida del almacenamiento, la compatibilidad de migración y los fallos. Crear Services, StatefulSets y CronJobs no establece la seguridad de los datos.

</details>

## 20. ¿Cómo debe implementarse y verificarse un scheduler personalizado?

<details>
<summary>Mostrar respuesta</summary>

Compila y registra plugins con las interfaces del framework de la versión menor exacta de Kubernetes. Alinea los nombres de profile y el schedulerName de Pod; prueba los fallos de Filter/Score y de reserva, permiso y binding. El YAML por sí solo no puede instalar un plugin. Considera primero node affinity para requisitos de zona simples.

</details>
