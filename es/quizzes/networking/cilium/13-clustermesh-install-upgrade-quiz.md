# Parte 13: Cuestionario sobre versiones, instalación/actualización y Cluster Mesh

> **Cilium 1.20.2 · 2026-10-15**

1. **¿Qué ruta de actualización prueba el proyecto upstream, tanto para actualizar como para revertir?**
   - A) Solo versiones menores consecutivas (por ejemplo, de 1.19 a 1.20 y viceversa), después de pasar al último parche de la versión menor actual
   - B) Cualquier salto de N a N+2 versiones menores, siempre que se instale el último parche
   - C) Cualquier versión menor a la más reciente si el gráfico de preflight se valida correctamente
   - D) Solo se actualizan los agentes; el operador se actualiza a la versión menor siguiente más adelante

   <details>
   <summary>Mostrar respuesta</summary>

   **Respuesta: A) Solo versiones menores consecutivas (por ejemplo, de 1.19 a 1.20 y viceversa), después de pasar al último parche de la versión menor actual**

   Saltarse versiones menores no se prueba y todos los componentes deben ejecutar la misma versión. Actualizar primero al último parche garantiza que el objetivo de reversión incluya todas las correcciones.

   </details>

2. **¿Por qué no debes ejecutar `helm upgrade --reuse-values` al pasar a una versión menor nueva?**
   - A) Elimina los CRD de Cilium
   - B) Restablece `upgradeCompatibility` a la versión nueva
   - C) Hace que se reemplace el gráfico OCI por el gráfico del repositorio clásico
   - D) Reutiliza los valores de la versión anterior e ignora los nuevos valores predeterminados del gráfico, lo que puede generar manifiestos defectuosos

   <details>
   <summary>Mostrar respuesta</summary>

   **Respuesta: D) Reutiliza los valores de la versión anterior e ignora los nuevos valores predeterminados del gráfico, lo que puede generar manifiestos defectuosos**

   Guarda los valores con `helm get values`, revisa las claves que hayan cambiado de nombre o se hayan eliminado y pásalos con `-f`. `--reuse-values` solo es aceptable si la versión del gráfico no cambia, por ejemplo, al aplicar los valores de Cluster Mesh con la misma versión.

   </details>

3. **¿Cuál es el valor predeterminado de `maxConnectedClusters` y qué implica establecerlo en 511?**
   - A) 255; hay que deshabilitar KVStoreMesh
   - B) 255; la cantidad máxima de identidades locales del clúster disminuye de 65535 a 32767
   - C) 127; el límite de longitud del nombre del clúster se reduce a la mitad
   - D) 511; el rango de identidades no cambia, pero solo funciona el modo overlay

   <details>
   <summary>Mostrar respuesta</summary>

   **Respuesta: B) 255; la cantidad máxima de identidades locales del clúster disminuye de 65535 a 32767**

   El ID del clúster utiliza bits de la identidad numérica. El valor debe ser idéntico en todos los clústeres y establecerse solo durante la instalación, ya que cambiarlo en un clúster activo puede interrumpir conexiones y hacer que las políticas se apliquen incorrectamente.

   </details>

4. **¿Cuál es el valor predeterminado de `clustermesh.apiserver.tls.authMode` en 1.20 frente a la versión preliminar de 1.21?**
   - A) `legacy` en 1.20 y `migration` en 1.21
   - B) `cluster` en 1.20 y `cluster-strict` en 1.21
   - C) `migration` en 1.20 y `cluster` en 1.21 (con una nueva opción `cluster-strict`)
   - D) `migration` en ambas

   <details>
   <summary>Mostrar respuesta</summary>

   **Respuesta: C) `migration` en 1.20 y `cluster` en 1.21 (con una nueva opción `cluster-strict`)**

   En el modo `cluster`, cada clúster se autentica como `remote-<cluster-name>` y se requiere una CA compartida. Si usas certificados proporcionados por el usuario y `tls.auto.enabled=false`, vuelve a emitir el certificado remoto con el nuevo CN o establece `authMode` de nuevo en `migration`.

   </details>

5. **En Cilium 1.19 y versiones posteriores, ¿con qué endpoints coincide un selector de política que no incluye una etiqueta de clúster en un Cluster Mesh?**
   - A) Endpoints de todos los clústeres conectados
   - B) Con ninguno; se rechaza la política
   - C) Solo endpoints de espacios de nombres globales en clústeres remotos
   - D) Solo endpoints del clúster local

   <details>
   <summary>Mostrar respuesta</summary>

   **Respuesta: D) Solo endpoints del clúster local**

   `policy-default-local-cluster` (Helm `clustermesh.policyDefaultLocalCluster`) tiene el valor predeterminado `true` desde 1.19. Selecciona un clúster remoto con la etiqueta `io.cilium.k8s.policy.cluster` o usa la expresión `Exists` para cualquier clúster. Hasta 1.18, el valor predeterminado incluía todos los clústeres.

   </details>

6. **¿Qué contenedor de clustermesh-apiserver hace que los agentes lean el estado de los clústeres remotos desde una caché local?**
   - A) `kvstoremesh`, que extrae el estado remoto al etcd local
   - B) `apiserver`, que replica los clústeres remotos
   - C) `etcd`, que extrae directamente los datos de instancias remotas de etcd
   - D) cilium-agent, que mantiene una conexión por cada etcd remoto

   <details>
   <summary>Mostrar respuesta</summary>

   **Respuesta: A) `kvstoremesh`, que extrae el estado remoto al etcd local**

   El contenedor `apiserver` solo sincroniza el estado del clúster local con el etcd local. KVStoreMesh está activado de forma predeterminada desde 1.16 y se habilita incondicionalmente en la versión preliminar de 1.21.

   </details>

7. **¿Qué versión de CRD de Gateway API requiere Cilium 1.20 y cuál es el problema con TLSRoute?**
   - A) v1.6.1; el gráfico de Helm instala los CRD y reemplaza TLSRoute automáticamente
   - B) v1.4; TLSRoute no se admite en absoluto
   - C) v1.6.1; instalar TLSRoute v1.6 del canal estándar hace que los objetos TLSRoute `v1alpha2` existentes sean ilegibles, así que si ya los usas, emplea TLSRoute v1.6.1 del canal experimental
   - D) v1.3.0; TLSRoute requiere la marca `bpf.tproxy`

   <details>
   <summary>Mostrar respuesta</summary>

   **Respuesta: C) v1.6.1; instalar TLSRoute v1.6 del canal estándar hace que los objetos TLSRoute `v1alpha2` existentes sean ilegibles, así que si ya los usas, emplea TLSRoute v1.6.1 del canal experimental**

   El gráfico no instala los CRD de Gateway API. Haz una copia de seguridad de los objetos TLSRoute antes de cambiar de canal y aplica los CRD con `kubectl apply --server-side`.

   </details>

8. **¿Se puede usar Cilium como CNI en EKS Auto Mode?**
   - A) Sí, con `cni.chainingMode=aws-cni`
   - B) No; AWS indica que Auto Mode no admite otros complementos de CNI ni de políticas de red
   - C) Sí, pero solo en modo overlay
   - D) Sí, si se aplica un parche a `aws-node` para que use un selector de nodos que no coincida

   <details>
   <summary>Mostrar respuesta</summary>

   **Respuesta: B) No; AWS indica que Auto Mode no admite otros complementos de CNI ni de políticas de red**

   Usa grupos de nodos administrados o autoadministrados. El parche de `aws-node` y el modo ENI corresponden a los grupos de nodos estándar, no a Auto Mode.

   </details>

9. **¿Qué significa `cilium_drift_checker_config_delta > 0`?**
   - A) El agente no puede acceder al servidor de API de Kubernetes
   - B) Un CiliumNodeConfig no superó la validación
   - C) El ConfigMap `cilium-config` contiene claves que el agente en ejecución no ha aplicado, por lo que hay que reiniciar el agente
   - D) El operador y el agente ejecutan versiones distintas de la imagen

   <details>
   <summary>Mostrar respuesta</summary>

   **Respuesta: C) El ConfigMap `cilium-config` contiene claves que el agente en ejecución no ha aplicado, por lo que hay que reiniciar el agente**

   El verificador de desviaciones compara el ConfigMap que observa con los ajustes con los que se inició el agente. `cilium config set --restart=false` es una forma de crear un cambio pendiente que luego informa la métrica.

   </details>

10. **¿Cuál es el orden de los valores de `identity-allocation-mode` en la migración Double Write de KVStore a CRD?**
    - A) `crd`, luego `doublewrite-readcrd` y luego `kvstore`
    - B) `doublewrite-readcrd`, luego `doublewrite-readkvstore` y luego `crd`
    - C) `kvstore`, luego `crd`, y `doublewrite-readkvstore` solo como estado de reversión
    - D) `kvstore`, luego `doublewrite-readkvstore`, luego `doublewrite-readcrd` y finalmente `crd`

    <details>
    <summary>Mostrar respuesta</summary>

    **Respuesta: D) `kvstore`, luego `doublewrite-readkvstore`, luego `doublewrite-readcrd` y finalmente `crd`**

    Vuelve a implementar primero el operador y luego los agentes para los dos pasos de Double Write; para el paso final `crd`, vuelve a implementar primero los agentes y luego el operador. La función está en fase beta y la herramienta de ejecución única `migrate-identity` está obsoleta en la versión preliminar de 1.21.

    </details>
