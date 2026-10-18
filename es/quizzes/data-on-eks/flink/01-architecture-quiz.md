# Cuestionario sobre la arquitectura de Flink en Kubernetes

Compruebe los roles de ejecución y los límites de recursos de Flink 2.2.1 / Operator 1.15.0.

1. ¿El JobManager siempre construye el grafo inicial y el cliente no realiza ningún cálculo?

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:** No. Application main() se ejecuta en el JM, mientras que el envío normal desde la CLI de Session 2.2 construye el grafo en el cliente.

**Explicación:** El JM coordina la ejecución, los slots, los checkpoints y la recuperación; los TM ejecutan las tareas. La propia función main() del usuario puede consumir recursos del JM.

</details>

2. ¿Cuatro slots de TaskManager implican que puede haber como máximo cuatro subtareas de operador?

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:** No. El encadenamiento y el uso compartido de slots pueden ubicar varios operadores en un mismo slot.

**Explicación:** Un slot fijo clásico es principalmente una unidad de asignación de memoria administrada, no un núcleo de CPU ni un límite independiente de aislamiento de CPU.

</details>

3. ¿El modo Application siempre significa un clúster por trabajo y aislamiento completo de los recursos compartidos de EKS?

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:** No. Un solo Application/main() puede crear varios trabajos, y los nodos, la red, el almacenamiento y las cuotas pueden ser compartidos.

**Explicación:** La separación de ciclo de vida/JVM a nivel de Application ayuda, pero no ofrece aislamiento absoluto. Compruebe las limitaciones de 2.2 para la alta disponibilidad de Application con varias ejecuciones.

</details>

4. ¿Enviar un trabajo a un clúster Session existente siempre inicia la ejecución de inmediato?

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:** No. Se puede reducir la sobrecarga del inicio del clúster, pero los slots, la CPU, la recuperación del estado y la carga compartida pueden retrasar la ejecución.

**Explicación:** Los trabajos Session comparten recursos del JM/TM; el fallo de un TM puede afectar a varios trabajos que lo usan.

</details>

5. ¿Se debe considerar Per-Job un tercer modo actual de Native Kubernetes en este capítulo?

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:** No. Las opciones de ciclo de vida cubiertas son Application y Session; Per-Job es histórico.

**Explicación:** Application/Session y las opciones de administración de recursos Native/Standalone son clasificaciones independientes.

</details>

6. ¿Quién administra los pods de TaskManager Native y los nodos de EKS que los alojan?

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:** El Kubernetes ResourceManager de Flink solicita pods de TM a través de la API; Karpenter/Cluster Autoscaler administra por separado la capacidad de los nodos.

**Explicación:** La liberación de los TM depende de los tiempos de espera por inactividad, los perfiles de recursos y la demanda. Completar un trabajo no elimina inmediatamente todos los pods ni todos los nodos.

</details>

7. ¿Los recuentos de TaskManager de Standalone-on-Kubernetes solo pueden cambiarse editando YAML manualmente?

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:** No. Un controlador externo, como Operator, puede reconciliar recursos de Kubernetes.

**Explicación:** El runtime de Flink no solicita directamente pods de TM mediante la administración de recursos Native. Evalúe por separado los permisos de API para funciones como la alta disponibilidad.

</details>

8. ¿Cuáles son los dos CR de clúster/trabajo de Operator 1.15.0 y solo admite el modo Native?

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:** FlinkDeployment y FlinkSessionJob; admite Native y Standalone.

**Explicación:** Deployment define clústeres Application/Session; SessionJob se dirige a un clúster Session administrado que ya existe. Que una versión aparezca en un enum no demuestra la compatibilidad de integración.

</details>

---

[Volver a los materiales de aprendizaje](../../../data-on-eks/flink/01-architecture.md)
