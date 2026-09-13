# Cuestionario de vCluster

[vCluster](../../platform-engineering/08-vcluster.md)

Los ocho temas originales se han revisado tomando como referencia vCluster 0.37.0.

## 1. ¿Qué separa y qué comparte vCluster en el modo Shared Nodes?

<details>
<summary>Mostrar respuesta</summary>

Puede separar las API virtuales, RBAC, los controladores y los almacenes, mientras comparte los nodos de las cargas de trabajo, los kernels, CNI y CSI. No garantiza un aislamiento completo del hardware, la red ni el rendimiento.

</details>

## 2. ¿Qué hace el Syncer?

<details>
<summary>Mostrar respuesta</summary>

Traduce los recursos y las referencias virtuales configurados a recursos del host y propaga de vuelta el estado observado. Los valores predeterminados y los nombres varían según el modo y la versión; no todos los recursos se sincronizan siempre en ambas direcciones.

</details>

## 3. ¿Qué se necesita para los entornos de vista previa de PR?

<details>
<summary>Mostrar respuesta</summary>

Un perfil validado, capacidad en el host, una identidad y eventos de CI de confianza, un namespace y un contexto explícitos, y limpieza posterior. No se garantiza la creación en menos de 30 segundos ni una mayor velocidad de las pruebas; no entregue credenciales del host a código no confiable procedente de forks.

</details>

## 4. ¿Cómo deben entenderse la pausa y la suspensión automática?

<details>
<summary>Mostrar respuesta</summary>

La pausa actual elimina las cargas de trabajo y las vuelve a crear al reanudar, con una retención independiente para PVC y Services. No es una suspensión que conserve la memoria ni una copia de seguridad. Valide por separado el comportamiento de reactivación automática, los derechos de uso y el ahorro real.

</details>

## 5. ¿Cómo funcionan las StorageClasses y los PVC en Shared Nodes?

<details>
<summary>Mostrar respuesta</summary>

Utilice una configuración de StorageClass fromHost compatible y el CSI del host, sincronizando los PVC con el host. Compruebe el modo de vinculación, la topología y las políticas de reclamación y retención. La versión 0.37 admite la sincronización de snapshots, que es distinta de la opción eliminada deploy.volumeSnapshotController.

</details>

## 6. ¿Qué conecta Backstage con el aprovisionamiento mediante GitOps?

<details>
<summary>Mostrar respuesta</summary>

Acciones y esqueletos preparados, PR revisadas, permisos reales de proyecto, destino y repositorio en ArgoCD, y una fuente de valores. debug:log no aprueba ni espera el despliegue. Entregue los kubeconfigs mediante canales aprobados para credenciales.

</details>

## 7. ¿Añadir una NetworkPolicy bloquea todo el acceso al host?

<details>
<summary>Mostrar respuesta</summary>

No. Los permisos son aditivos y otra política de denegación no puede reducirlos. El Syncer necesita acceso a la API del host. El perfil deshabilita la salida pública de las cargas de trabajo, pero conserva los permisos de puertos del plano de control, por lo que es necesario validar el CNI y las rutas reales.

</details>

## 8. ¿Cómo deben seleccionarse los modos de despliegue?

<details>
<summary>Mostrar respuesta</summary>

Evalúe la autonomía de las API, los nodos, el kernel, CNI y CSI, los límites entre cuentas y administradores, el rendimiento y las necesidades del ciclo de vida. Compare Shared Nodes, Dedicated/Private Nodes, Standalone y los clústeres separados sin prometer velocidades, costes ni idoneidad normativa que no se hayan medido o comprobado.

</details>
