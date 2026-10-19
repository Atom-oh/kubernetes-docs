# Cuestionario de almacenamiento

Este cuestionario evalúa tu comprensión de los conceptos de almacenamiento de Kubernetes, los tipos de volúmenes, los volúmenes persistentes, las clases de almacenamiento y otros temas.

## Preguntas de opción múltiple

1. ¿Qué recurso proporciona almacenamiento para aplicaciones con un ciclo de vida independiente de que un Pod ordinario se elimine y vuelva a crear?
   - A) ConfigMap
   - B) Secret
   - C) PersistentVolume
   - D) emptyDir
   
<details>

<summary>Mostrar respuesta</summary>

**Respuesta: C) PersistentVolume**

**Explicación:**
PersistentVolume (PV) es almacenamiento del clúster, aprovisionado por un administrador del clúster o de forma dinámica mediante una StorageClass. Los PV conservan los datos aunque los Pods se reinicien o se eliminen. ConfigMap y Secret se usan para almacenar datos de configuración e información confidencial, respectivamente; emptyDir es un directorio temporal que solo existe mientras se ejecuta el Pod.
</details>

2. ¿Qué recurso se utiliza en Kubernetes para solicitar un PersistentVolume?
   - A) VolumeRequest
   - B) PersistentVolumeClaim
   - C) StorageRequest
   - D) VolumeBinding
   
<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) PersistentVolumeClaim**

**Explicación:**
PersistentVolumeClaim (PVC) es el mecanismo mediante el cual los usuarios solicitan PersistentVolumes. Un PVC representa una solicitud de almacenamiento con un tamaño y un modo de acceso específicos. Kubernetes busca un PV que cumpla los requisitos del PVC y los enlaza.
</details>

3. ¿Qué recurso se utiliza para el aprovisionamiento dinámico de volúmenes en Kubernetes?
   - A) VolumeProvisioner
   - B) StorageClass
   - C) DynamicVolume
   - D) AutoProvisioner
   
<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) StorageClass**

**Explicación:**
StorageClass permite a los administradores describir las «clases» de almacenamiento que ofrecen. Las distintas clases pueden corresponder a niveles de servicio, políticas de copia de seguridad u otras políticas definidas por el administrador del clúster. Mediante StorageClass, se pueden aprovisionar PV de forma dinámica cuando se crean los PVC.
</details>

4. Si se elimina un Pod ordinario, ¿también se elimina automáticamente el PVC independiente al que hace referencia?
   - A) Sí, siempre se aplica la política Delete
   - B) Sí, siempre se aplica la política Retain
   - C) Sí, se aplica la política Recycle
   - D) No; el PVC creado por separado permanece
   
<details>

<summary>Mostrar respuesta</summary>

**Respuesta: D) No; el PVC creado por separado permanece**

**Explicación:**
Un PVC creado por separado no pertenece al Pod y permanece cuando se elimina ese Pod. Los PVC de volúmenes efímeros genéricos son distintos: pertenecen al Pod y el recolector de elementos no utilizados los elimina junto con él. `persistentVolumeClaimRetentionPolicy` de StatefulSet puede eliminar PVC creados a partir de plantillas cuando se elimina el conjunto o se reduce su escala; la política de recuperación del PV determina la limpieza posterior del almacenamiento.
</details>

5. ¿Cuál de los siguientes NO es un modo de acceso de PersistentVolume?
   - A) ReadWriteOnce
   - B) ReadOnlyMany
   - C) ReadWriteMany
   - D) WriteOnlyMany
   
<details>

<summary>Mostrar respuesta</summary>

**Respuesta: D) WriteOnlyMany**

**Explicación:**
Los modos de acceso de PersistentVolume en Kubernetes son ReadWriteOnce (RWO), ReadOnlyMany (ROX), ReadWriteMany (RWX) y ReadWriteOncePod (RWOP, solo CSI). WriteOnlyMany no existe como modo de acceso. ReadWriteOnce permite montar el volumen en lectura y escritura desde un único nodo; ReadOnlyMany permite montarlo en modo de solo lectura desde varios nodos, y ReadWriteMany permite montarlo en lectura y escritura desde varios nodos.
</details>

6. ¿Qué política de recuperación de PersistentVolume libera el recurso sin eliminar el volumen?
   - A) Delete
   - B) Retain
   - C) Recycle
   - D) Release
   
<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Retain**

**Explicación:**
La política Retain conserva el PV y sus datos después de eliminar el PVC. El volumen pasa al estado «Released», pero no queda disponible para otras reclamaciones. El administrador debe limpiar manualmente los datos y habilitar el volumen para volver a usarlo. La política Delete elimina el PV y la infraestructura externa (por ejemplo, AWS EBS o GCE PD) cuando se elimina el PVC. La política Recycle está obsoleta; se debe usar el aprovisionamiento dinámico en su lugar.
</details>

7. ¿Qué tipo de volumen proporciona almacenamiento temporal en Kubernetes?
   - A) hostPath
   - B) emptyDir
   - C) nfs
   - D) persistentVolumeClaim
   
<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) emptyDir**

**Explicación:**
Un volumen emptyDir se crea cuando se asigna un Pod a un nodo y existe mientras ese Pod se ejecuta en ese nodo. Como indica su nombre, el volumen empieza vacío. Todos los contenedores del Pod pueden leer y escribir los mismos archivos en el volumen emptyDir, aunque cada contenedor puede montarlo en la misma ruta o en rutas distintas. Si el Pod se retira del nodo por cualquier motivo, los datos de emptyDir se eliminan de forma permanente.
</details>

8. ¿Qué provisionador identifica el controlador CSI estándar de Amazon EBS (no EKS Auto Mode)?
   - A) ebs.csi.aws.com
   - B) kubernetes.io/gce-pd
   - C) kubernetes.io/azure-disk
   - D) kubernetes.io/nfs
   
<details>

<summary>Mostrar respuesta</summary>

**Respuesta: A) ebs.csi.aws.com**

**Explicación:**
El controlador CSI estándar de EBS usa `ebs.csi.aws.com`; es necesario instalar y configurar el controlador y sus permisos de IAM. Un clúster no tiene automáticamente una StorageClass predeterminada adecuada. EKS Auto Mode usa `ebs.csi.eks.amazonaws.com`. No se debe usar el provisionador heredado integrado en Kubernetes en ejemplos nuevos.
</details>

9. ¿Cuál es el nombre correcto del campo para las plantillas de reclamación de volúmenes que usan los StatefulSets?
   - A) volumeClaimTemplate
   - B) persistentVolumeClaimTemplate
   - C) volumeClaimTemplates
   - D) persistentVolumeClaimTemplates
   
<details>

<summary>Mostrar respuesta</summary>

**Respuesta: C) volumeClaimTemplates**

**Explicación:**
StatefulSet usa el campo `volumeClaimTemplates` para crear automáticamente un PVC para cada Pod. Esta plantilla crea PVC para cada réplica del StatefulSet. Los nombres de los PVC siguen el formato `<volume-claim-template-name>-<pod-name>`.
</details>

10. ¿Cuál es el propósito principal de CSI (Container Storage Interface) en Kubernetes?
    - A) Estandarizar la comunicación entre contenedores
    - B) Permitir que los controladores de almacenamiento se desarrollen fuera del código de Kubernetes
    - C) Estandarizar el acceso a los registros de imágenes de contenedor
    - D) Automatizar la migración de almacenamiento entre proveedores de nube
    
<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Permitir que los controladores de almacenamiento se desarrollen fuera del código de Kubernetes**

**Explicación:**
CSI (Container Storage Interface) define una interfaz estándar entre los sistemas de orquestación de contenedores, como Kubernetes, y los proveedores de almacenamiento. Su propósito principal es permitir que los controladores de almacenamiento se desarrollen, implementen y administren fuera del código base de Kubernetes. Así, los proveedores pueden desarrollar y mantener sus propios complementos independientemente del ciclo de publicación de Kubernetes.
</details>

## Preguntas avanzadas

1. Explica cómo integrar nuevos tipos de almacenamiento mediante controladores CSI (Container Storage Interface) en Kubernetes y cuáles son sus beneficios.

<details>

<summary>Mostrar respuesta</summary>

**Respuesta:**

**Método de integración del controlador CSI:**

1. **Implementar el controlador CSI**: normalmente consta de los siguientes componentes:
  - **DaemonSet del complemento de nodo**: se ejecuta en cada nodo y realiza operaciones de montaje y desmontaje de volúmenes
  - **Deployment/StatefulSet del complemento controlador**: realiza operaciones de creación, eliminación y captura de instantáneas de volúmenes
  - **Recursos RBAC**: configuran los permisos necesarios

2. **Crear una StorageClass**: define una StorageClass que utilice el controlador CSI:
```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: csi-storage
provisioner: example.csi.k8s.io  # CSI driver name
parameters:
  # Driver-specific parameters
  type: ssd
  fsType: ext4
```

3. **Configurar la compatibilidad con instantáneas de volúmenes CSI** (opcional):
```yaml
apiVersion: snapshot.storage.k8s.io/v1
kind: VolumeSnapshotClass
metadata:
  name: csi-snapshot-class
driver: example.csi.k8s.io
deletionPolicy: Delete
```

4. **Probar el controlador CSI**: comprueba que funciona creando un PVC y montándolo en un Pod.

**Beneficios de usar CSI:**

1. **Ciclo de desarrollo independiente**: los proveedores de almacenamiento pueden desarrollar e implementar controladores independientemente del ciclo de publicación de Kubernetes.

2. **Interfaz estandarizada**: CSI ofrece una interfaz estándar entre los sistemas de orquestación de contenedores y los proveedores de almacenamiento.

3. **Funciones de almacenamiento avanzadas**: admite instantáneas, clonación y redimensionamiento de volúmenes de forma estandarizada.

4. **Seguridad mejorada**: limita IAM/RBAC del controlador a las operaciones necesarias. Los complementos CSI de nodo suelen necesitar acceso privilegiado al host para montar volúmenes, por lo que sus permisos deben revisarse por separado.

5. **Diversidad de opciones de almacenamiento**: facilita la integración de soluciones de proveedores de nube, de código abierto y comerciales.

6. **Arquitectura de complementos**: los controladores CSI se pueden añadir o retirar según sea necesario.

**Ejemplo de implementación real (controlador CSI de AWS EBS):**

```bash
# First install the EKS EBS CSI add-on with its IAM role using the official guide.
# Snapshot support additionally needs snapshot CRDs and the snapshot controller.

# Create StorageClass
kubectl apply -f - <<EOF
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: ebs-sc
provisioner: ebs.csi.aws.com
volumeBindingMode: WaitForFirstConsumer
parameters:
  type: gp3
  encrypted: "true"
EOF
```

CSI es una parte fundamental del ecosistema de almacenamiento de Kubernetes: permite integrar distintas soluciones y aprovechar funciones avanzadas de almacenamiento.
</details>

2. Diseña un clúster de base de datos de alta disponibilidad con StatefulSet y almacenamiento persistente. Distingue las responsabilidades de Kubernetes de la replicación de la base de datos y explica los requisitos de copia de seguridad y recuperación.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:**

1. Usa identidades estables para los Pods, un Service headless (sin IP de clúster) y un PVC independiente por miembro de la base de datos. Distribuye los miembros entre nodos y zonas. Cada volumen EBS permanece en una sola zona de disponibilidad; para recuperarlo en otra zona se necesita un volumen restaurado o replicación de la base de datos.
2. Configura un operador de bases de datos o un sistema de replicación probado de forma independiente para gestionar ID de servidor únicos, sincronización inicial de datos, elección de primario, fencing, credenciales de replicación y enrutamiento de clientes. Un StatefulSet de tres réplicas por sí solo no crea una base de datos de alta disponibilidad.
3. Aprovisiona volúmenes EBS cifrados mediante `ebs.csi.aws.com`, con `WaitForFirstConsumer`, un valor adecuado de `iops` para gp3 y una política de recuperación deliberada. `Retain` conserva el almacenamiento subyacente tras eliminar una reclamación; no es una copia de seguridad ni evita todas las vías de eliminación.
4. ConfigMap no expande expresiones de shell como `${HOSTNAME##*-}`. Genera la configuración específica de cada instancia en un contenedor de inicialización; ejecuta SQL solo después de que se haya iniciado MySQL. Las sondas exec no expanden `${VARIABLE}` si no se ejecutan mediante un shell.
5. Para las instantáneas CSI, instala las CRD y el controlador de instantáneas y usa una `VolumeSnapshotClass` de EBS. Detén las escrituras o utiliza copias de seguridad compatibles con la base de datos para obtener puntos de recuperación coherentes, y verifica la compatibilidad del tamaño restaurado y del controlador.
6. Para las copias de seguridad lógicas, usa una imagen que incluya las herramientas compatibles de la base de datos y la herramienta para subir archivos (la imagen estándar de MySQL no incluye AWS CLI). Usa un usuario de base de datos dedicado a las copias y una identidad de AWS con permisos acotados. Haz que el Job falle si falla la exportación o la carga; conserva una copia correcta fuera del Pod y prueba la restauración. La retención del historial del Job no conserva los archivos de las copias de seguridad.
7. Supervisa el retraso de replicación, la utilización del almacenamiento, la antigüedad y los fallos de las copias de seguridad, y las pruebas de restauración. Documenta los objetivos de punto y tiempo de recuperación y prueba la conmutación por error ante la pérdida de nodos y zonas.

Consulta la [guía de instalación de EBS CSI](https://docs.aws.amazon.com/eks/latest/userguide/ebs-csi.html) y los ejemplos de instantáneas y retención del capítulo.

</details>

## Conclusión

Con este cuestionario, pusiste a prueba tu comprensión de los conceptos de almacenamiento de Kubernetes. Repasaste PersistentVolumes, PersistentVolumeClaims, StorageClasses, tipos de volúmenes, modos de acceso y políticas de recuperación. También exploraste temas avanzados como la configuración de almacenamiento en AWS EKS, los controladores CSI y las instantáneas de volúmenes. Comprender y aplicar estos conceptos permite crear soluciones de almacenamiento fiables y escalables en Kubernetes.
