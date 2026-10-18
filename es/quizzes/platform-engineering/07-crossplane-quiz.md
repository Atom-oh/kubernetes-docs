# Cuestionario de Crossplane

[Crossplane](../../platform-engineering/07-crossplane.md)

Los ocho temas originales se revisaron con Crossplane 2.4.

## 1. ¿Qué proporciona una Composition?

<details>
<summary>Mostrar respuesta</summary>

Una canalización de Functions asigna las entradas del XR a los recursos deseados. No vuelve atómicas varias operaciones de AWS ni garantiza que los recursos estén listos.

</details>

## 2. ¿En qué se diferencian los XR v2 de los Claims heredados?

<details>
<summary>Mostrar respuesta</summary>

XRD v2 usa Namespaced de forma predeterminada y permite que los usuarios creen XR directamente. Los XRD LegacyCluster v1 heredados conservan los XR con alcance de clúster y los Claims con alcance de espacio de nombres. No todos los XR/MR actuales tienen alcance de clúster.

</details>

## 3. ¿Elegir IRSA o Pod Identity completa el principio de mínimo privilegio?

<details>
<summary>Mostrar respuesta</summary>

No. Configure los ServiceAccounts, el audience/subject de OIDC o las asociaciones, y las políticas del rol. Restrinja también la propiedad en tiempo de ejecución, el acceso a ProviderConfig y los límites de AssumeRole.

</details>

## 4. ¿Cuál es la diferencia principal entre Terraform y Crossplane?

<details>
<summary>Mostrar respuesta</summary>

Ambos trabajan con estado declarativo: Terraform se centra en los flujos de trabajo de plan/apply y Crossplane en la reconciliación continua. Terraform se puede automatizar; Crossplane sigue sujeto a la compatibilidad del proveedor, las políticas, las cuotas y los errores.

</details>

## 5. ¿Cómo pueden coexistir ACK y Crossplane?

<details>
<summary>Mostrar respuesta</summary>

Asigne la propiedad de los recursos externos por separado. ACK también ofrece CR y referencias con alcance de espacio de nombres y puede combinarse con kro. No permita que varios controladores compitan por modificar el mismo recurso de AWS.

</details>

## 6. ¿Cómo se proporcionan los Secrets de conexión en v2?

<details>
<summary>Mostrar respuesta</summary>

Se conserva `writeConnectionSecretToRef` en los MR, pero se eliminó la publicación nativa del XR en el núcleo. Componga un Secret o use la agregación compatible de una Function. El ejemplo agrega solo el endpoint y el nombre de usuario, y usa un Secret de contraseña preparado por separado.

</details>

## 7. ¿Cuál es el flujo de trabajo de Backstage/GitOps?

<details>
<summary>Mostrar respuesta</summary>

Renderice el YAML del XR con esqueletos y acciones preparados, fusione un PR revisado, reconcilie mediante ArgoCD y Crossplane/Providers, y después verifique el estado real de disponibilidad. Crear un PR, registrar algo en el catálogo y completar el aprovisionamiento de AWS son estados distintos.

</details>

## 8. ¿Qué controla la corrección de desviaciones y la retención?

<details>
<summary>Mostrar respuesta</summary>

Revise los campos compatibles con el proveedor, `managementPolicies` y el intervalo de sondeo. Estos MR v2 con alcance de espacio de nombres conservan los recursos externos al excluir `Delete`; esto difiere de `deletionPolicy: Orphan` heredado. La retención mantiene las responsabilidades de respaldo, credenciales, costos y propiedad.

</details>
