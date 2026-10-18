# Cuestionario sobre Flink Kubernetes Operator

Comprueba la instalación, la recuperación de estado y el escalado automático en Operator 1.15.0 / Flink 2.2.1.

1. ¿En qué se diferencian Deployment y SessionJob?

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:** Deployment define un clúster Application o Session; SessionJob define un trabajo en un clúster Session administrado que ya existe.

**Explicación:** Gestionar SessionJob por separado no aísla los recursos compartidos del clúster ni sus fallos.

</details>

2. ¿Basta con el requisito mínimo histórico de Kubernetes 1.21 o posterior para validar una implementación actual de EKS?

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:** No. Comprueba la compatibilidad actual de EKS, el desfase entre las versiones del cliente y la compatibilidad de Operator/webhook/CRD.

**Explicación:** La fecha en que se incorporó la etiqueta de espacio de nombres no constituye una matriz completa de compatibilidad o validación de funciones.

</details>

3. ¿Un recurso personalizado blue/green cambia automáticamente las escrituras de Kafka/S3 sin duplicarlas?

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:** No. Diseña por separado los grupos de consumidores, los ID de transacción, las salidas de los sinks y la compatibilidad del estado.

**Explicación:** Gestionar las transiciones entre implementaciones secundarias es distinto de ofrecer garantías integrales de datos y requiere capacidad adicional durante la transición.

</details>

4. ¿Una actualización mediante savepoint es siempre la opción más segura, lenta y con interrupción total?

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:** No existe una clasificación universal; el tiempo, la posibilidad de restauración y la alternativa de recuperación dependen del trabajo y de los cambios de estado.

**Explicación:** Crear una instantánea no demuestra la compatibilidad de serializadores, UID o conectores.

</details>

5. ¿Qué necesita la recuperación last-state de un trabajo en mal estado?

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:** Metadatos/checkpoints de HA accesibles, estado compatible, credenciales y almacenamiento.

**Explicación:** Puede evitar la creación de un savepoint nuevo, pero no resuelve automáticamente la pérdida de metadatos ni los checkpoints obsoletos.

</details>

6. ¿Establecer last-state en el YAML de SessionJob completa la preparación para una actualización con estado?

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:** No. La configuración efectiva de Session/trabajo requiere prerrequisitos de checkpoints, almacenamiento y recuperación.

**Explicación:** Comprueba el validador y la ruta de restauración, no solo la cadena del modo.

</details>

7. ¿Cuál es el principal objetivo de escalado de Flink autoscaler?

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:** El paralelismo de los vértices individuales del job graph.

**Explicación:** Esto difiere del escalado de réplicas de HPA; la cantidad real de pods/nodos depende de las capas de asignación de slots y de gestión de recursos.

</details>

8. ¿La tasa objetivo de salida de un operador posterior es simplemente la suma de las tasas actuales de salida de sus operadores anteriores?

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:** Combina las tasas objetivo de los operadores anteriores multiplicadas por las relaciones de salida de las aristas y propaga los objetivos de procesamiento de la acumulación de trabajo.

**Explicación:** Importan la selectividad de salida y la capacidad futura requerida.

</details>

9. ¿El autoscaler ignora todas las señales de CPU/memoria?

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:** El modelo principal de paralelismo usa tasas/tiempo ocupado, pero también existen presión de memoria/GC, cuotas y ajustes opcionales de memoria.

**Explicación:** El ajuste de memoria está deshabilitado de forma predeterminada; aun así, esto es distinto de HPA basado en CPU.

</details>

10. ¿El paralelismo de Flink siempre debe ser un divisor del paralelismo máximo?

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:** No. Las preferencias de alineación del autoscaler para equilibrar grupos de claves/particiones son distintas del intervalo permitido por Flink.

**Explicación:** Comprueba el modo de alineación, las entradas con claves y las particiones de origen. Cambiar el paralelismo máximo de un estado existente requiere revisar la compatibilidad.

</details>

11. ¿Cada reescalado del autoscaler es una actualización completa con last-state?

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:** No. Cuando es posible, usa API de requisitos de recursos in situ; algunas condiciones requieren volver a implementar.

**Explicación:** El escalado in situ no garantiza que no haya reinicios de tareas ni costos de recuperación del estado.

</details>

12. ¿Por qué estos ejemplos usan Flink 2.2.1 en vez de la versión más reciente 2.3.0?

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:** Para fijar una base de integración comprobada junto con las tablas publicadas de compatibilidad de Operator/conectores.

**Explicación:** Que una CRD acepte un valor más reciente en un enum no demuestra compatibilidad con el runtime.

</details>

13. ¿Una configuración de registros del chart demuestra que están instalados los JAR de reporter y los servidores de recopilación?

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:** No. Distingue entre archivos del chart, JAR de la imagen de runtime, activación de reporters y backend de recopilación.

**Explicación:** El chart 1.15 incluye configuración para Log4j/Logback, pero YAML por sí solo no crea una canalización completa de métricas.

</details>

14. ¿Qué más se debe comprobar al establecer `watchNamespaces`?

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:** La existencia del espacio de nombres de destino, las cuentas de servicio/Roles/RoleBindings generados para trabajos y otras concesiones.

**Explicación:** Una lista vacía observa todos los espacios de nombres. El alcance de observación por sí solo no aísla completamente a los inquilinos.

</details>

15. ¿Una ventana de métricas de diez minutos es óptima para todas las cargas de trabajo?

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:** No. Ajusta conjuntamente la ventana, la estabilización y el intervalo de reducción según los SLO reales.

**Explicación:** Las ventanas cortas pueden amplificar el ruido; las largas pueden retrasar la respuesta. Usa observación y pruebas de carga.

</details>

16. ¿La instalación predeterminada del webhook requiere cert-manager?

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:** Sí. El chart revisado crea recursos Certificate e Issuer y no tiene un Job interno para generar certificados.

**Explicación:** Comprueba los controladores/webhook/cainjector y que Certificate esté Ready; no te limites a verificar la existencia de las CRD.

</details>

17. ¿La imagen predeterminada de Flink puede ejecutar un JAR ficticio de `order-events`?

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:** No, salvo que el JAR esté incluido en ella. El capítulo usa `StateMachineExample`, que viene incluido, para verificar la ruta de ejecución.

**Explicación:** Una demostración sin estado es distinta de validar la recuperación mediante checkpoints duraderos/HA.

</details>

18. ¿Qué ajustes recopilan recomendaciones sin aplicar el escalado?

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:** `job.autoscaler.enabled=true` y `job.autoscaler.scaling.enabled=false`.

**Explicación:** Usa las claves actuales `utilization.target/min/max` y valida las recomendaciones, la recuperación del estado y las cuotas antes de habilitar acciones.

</details>

19. ¿Qué condición se usa para esperar a que FlinkDeployment esté inicialmente listo?

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:** Running, no Available.

**Explicación:** Refleja el estado observado del trabajo/JM. Después de las actualizaciones, distingue una condición obsoleta de la reconciliación real de la nueva especificación.

</details>

20. Para una acumulación de 6000 registros, ¿cómo cambia la tasa objetivo adicional al reducir `catch-up.duration` de 600 a 60 segundos?

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:** Aumenta de 10 a 100 registros por segundo.

**Explicación:** Un objetivo de recuperación más corto requiere más capacidad. No es un período de gracia para ignorar la acumulación; el valor cero deshabilita el escalado basado en la acumulación.

</details>

---

[Volver al material de aprendizaje](../../../data-on-eks/flink/02-flink-kubernetes-operator.md)
