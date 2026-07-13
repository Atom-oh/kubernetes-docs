# Cuestionario de vCluster

1. ¿En qué supera vCluster a la multi-tenencia tradicional basada en Namespace?
   - A) vCluster crea clusters físicos adicionales
   - B) Proporciona a cada tenant una Kubernetes API completa mientras comparte los recursos del host cluster
   - C) vCluster aísla completamente la red
   - D) vCluster requiere nodes dedicados

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Proporciona a cada tenant una Kubernetes API completa mientras comparte los recursos del host cluster**

**Explicación:**
vCluster proporciona a cada tenant una Kubernetes API independiente (instalación de CRD, gestión de RBAC, creación de Namespace, etc.) mediante un control plane virtual. Las workloads reales se ejecutan en el host cluster, lo que proporciona un aislamiento sólido sin el costo de clusters físicos adicionales.

</details>

---

2. ¿Cuál es el rol principal del componente Syncer de vCluster?
   - A) Gestionar el DNS del virtual cluster
   - B) Sincronizar los recursos del virtual cluster con el host cluster y reflejar de vuelta el estado del host
   - C) Conectar redes entre virtual clusters
   - D) Recopilar logs del virtual cluster

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Sincronizar los recursos del virtual cluster con el host cluster y reflejar de vuelta el estado del host**

**Explicación:**
El Syncer es el componente central de vCluster que traduce los recursos creados en el virtual cluster (Pods, Services, ConfigMaps, etc.) en recursos reales en el host cluster. También sincroniza la información del host (Nodes, StorageClasses, etc.) de vuelta al virtual cluster, realizando una gestión bidireccional de recursos.

</details>

---

3. ¿Cuál es la ventaja de usar vCluster para entornos de vista previa por PR?
   - A) Desplegar código en producción sin hacer merge del PR
   - B) Crear/eliminar rápidamente entornos Kubernetes aislados por PR para pruebas de integración
   - C) Otorgar privilegios de admin del cluster a los revisores del PR
   - D) Reducir el tiempo de ejecución del pipeline de CI

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Crear/eliminar rápidamente entornos Kubernetes aislados por PR para pruebas de integración**

**Explicación:**
vCluster puede crearse en menos de 30 segundos, lo que permite que los pipelines de CI/CD aprovisionen entornos Kubernetes aislados por PR. Cuando los PR se fusionan o se cierran, el vCluster se elimina para recuperar recursos, lo que permite probar la integración de los cambios de cada PR en un entorno independiente.

</details>

---

4. ¿Cuál es el propósito de la característica Sleep Mode de vCluster?
   - A) Mejorar la seguridad del virtual cluster
   - B) Liberar recursos de virtual clusters no utilizados para reducir costos
   - C) Hacer backups de los datos del virtual cluster
   - D) Optimizar el rendimiento del virtual cluster

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Liberar recursos de virtual clusters no utilizados para reducir costos**

**Explicación:**
Sleep Mode detiene automáticamente las workloads en vClusters que han estado inactivos durante un período especificado. Cuando llega una solicitud de API, el vCluster se activa automáticamente. Esto reduce significativamente los costos de vClusters de dev/test que no se usan durante las noches y los fines de semana.

</details>

---

5. ¿Cómo se usa la StorageClass del host cluster en un virtual cluster?
   - A) Recrear la StorageClass en el virtual cluster
   - B) Usar la configuración syncFromHost para sincronizar la StorageClass del host con el virtual cluster
   - C) Montar PVs manualmente
   - D) Instalar drivers CSI por separado en el virtual cluster

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Usar la configuración syncFromHost para sincronizar la StorageClass del host con el virtual cluster**

**Explicación:**
La configuración `syncFromHost` de vCluster sincroniza recursos del host cluster como StorageClasses, IngressClasses y Nodes para que sean visibles en el virtual cluster. Los PVCs en el virtual cluster usan las StorageClasses del host cluster para aprovisionar PVs reales.

</details>

---

6. ¿Cómo funciona el flujo de trabajo de autoservicio para developers en la integración de Backstage + vCluster?
   - A) Los developers crean vClusters directamente con kubectl
   - B) Backstage Template genera una solicitud de vCluster → la envía al repositorio GitOps → ArgoCD sincroniza para aprovisionar el vCluster
   - C) Backstage llama directamente a la Kubernetes API para crear vClusters
   - D) Los admins crean vClusters manualmente y los asignan a los developers

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Backstage Template genera una solicitud de vCluster → la envía al repositorio GitOps → ArgoCD sincroniza para aprovisionar el vCluster**

**Explicación:**
Cuando un developer introduce parámetros (nombre del entorno, tamaño de recursos, etc.) en un Backstage Template, el Template genera manifiestos de vCluster Helm Release y los envía al repositorio GitOps. ArgoCD detecta el cambio y lo sincroniza con el cluster, aprovisionando automáticamente el vCluster.

</details>

---

7. ¿Cuál es el rol de NetworkPolicy en el aislamiento de seguridad de vCluster?
   - A) Limitar el uso de CPU entre virtual clusters
   - B) Evitar que los Pods del virtual cluster accedan a Pods de otros vClusters o a recursos del host cluster mediante aislamiento de red
   - C) Cifrar el tráfico de Ingress para virtual clusters
   - D) Filtrar consultas DNS

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Evitar que los Pods del virtual cluster accedan a Pods de otros vClusters o a recursos del host cluster mediante aislamiento de red**

**Explicación:**
Como los Pods de vCluster se ejecutan en el host cluster, sin NetworkPolicies pueden acceder por red a Pods de otros vClusters. Aplicar NetworkPolicies al namespace de cada vCluster para permitir solo comunicación dentro del namespace y bloquear el acceso externo implementa un aislamiento de red sólido.

</details>

---

8. ¿Cuándo deberías elegir vCluster en lugar de un cluster físico?
   - A) Cuando se requiere aislamiento completo de hardware
   - B) Cuando se necesitan aprovisionamiento rápido, eficiencia de costos y aislamiento de CRD, pero no aislamiento completo de nodes
   - C) Cuando los requisitos normativos exigen cuentas de AWS separadas
   - D) Cuando se ejecutan workloads de GPU

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Cuando se necesitan aprovisionamiento rápido, eficiencia de costos y aislamiento de CRD, pero no aislamiento completo de nodes**

**Explicación:**
vCluster ofrece creación en menos de 30 segundos, eficiencia de costos mediante el uso compartido de recursos del host cluster y aislamiento de CRD/RBAC/Namespace. Es ideal para entornos de dev/test, entornos efímeros de CI/CD y entornos de capacitación. Los clusters físicos son más adecuados para workloads de producción que requieren cumplimiento normativo, aislamiento completo de hardware o aislamiento de red dedicado.

</details>
