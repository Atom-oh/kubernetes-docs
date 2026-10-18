# 5. Cuaderno de diseño de redes de nube y CNI

> **Última actualización**: 15 de septiembre de 2026

**Requisitos previos:** [Protocolos](01-protocol-projects.md), [enrutamiento](02-routing-policy-convergence.md), [observación de Linux](04-linux-performance.md) y conceptos de Pods/Services/EndpointSlice de Kubernetes. La observación en vivo requiere una cuenta/clúster de laboratorio existente y aprobado, y los permisos de lectura necesarios.

**Objetivo:** Conectar el diseño, las observaciones y las políticas desde DNS hasta el backend y la ruta de retorno. Los comandos de este capítulo consultan recursos existentes; no crean recursos ni inyectan fallos. Si no tiene una cuenta, complete los ejercicios de diseño y etiquete el resultado como **revisión de diseño**.

Prepare AWS CLI y una versión de kubectl compatible con el clúster, y luego compruebe el perfil/contexto del laboratorio. Si falta una herramienta, siga las instrucciones específicas de la plataforma para la [instalación de AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html) y la [instalación de kubectl](https://kubernetes.io/docs/tasks/tools/). Este cuaderno no da por hecho que la instalación de herramientas o la emisión de credenciales se hayan realizado automáticamente.

## 1. Convertir el alcance de AWS en preguntas {#design-questions}

El [alcance oficial de AWS Advanced Networking](https://docs.aws.amazon.com/aws-certification/latest/advanced-networking-specialty-01/advanced-networking-specialty-01.html) abarca diseño de nube/híbrido, implementación, operaciones, seguridad y automatización. Aplique cada área en forma de pregunta sobre su diseño.

| Área | Pregunta | Evidencia |
|---|---|---|
| Direccionamiento/enrutamiento | ¿Qué prefijo de destino y siguiente salto se aplican, y existe una ruta de retorno? | Rutas de VPC/subred/TGW y direcciones reales de origen/destino |
| Resolución de nombres | ¿Qué resolutor, zona o regla de reenvío responde? | Nombre/tipo de consulta, resolutor, respuesta, TTL y hora |
| Punto de entrada | ¿Qué frontend selecciona DNS y qué backend está registrado? | Listener, tipo/puerto de destino, comprobación de estado y destino real |
| Aislamiento | ¿Qué capa aplica los flujos permitidos y prohibidos? | Alcance de políticas SG/NACL/CNI y aplicación observada |
| Resiliencia | ¿Qué flujos se ven afectados cuando falla un componente? | Límite de fallo, ruta alternativa, plan de estado/recuperación |
| Rendimiento/costo | ¿Qué condiciones rigen la latencia, el rendimiento, la capacidad de direcciones y el movimiento de datos? | Intervalo/dirección/recursos medidos e insumos de costo actuales |

El alcance del examen asigna temas de aprendizaje. No es una clave de respuestas de implementación ni una garantía de rendimiento para un diseño concreto.

## 2. Establecer el entorno y los permisos {#inventory}

Sustituya estos nombres por **valores reales aprobados del laboratorio**. Las cadenas siguientes no son datos de cuenta funcionales.

```bash
LAB_AWS_PROFILE='REPLACE_WITH_LAB_PROFILE'
LAB_AWS_REGION='REPLACE_WITH_LAB_REGION'
LAB_CONTEXT='REPLACE_WITH_LAB_KUBERNETES_CONTEXT'
LAB_NAMESPACE='REPLACE_WITH_LAB_NAMESPACE'
LAB_SERVICE='REPLACE_WITH_LAB_SERVICE'
```

**Terminal de consultas aprobada por un operador:**

```bash
aws --version
kubectl version --client
aws --profile "$LAB_AWS_PROFILE" --region "$LAB_AWS_REGION" \
  sts get-caller-identity
kubectl --context "$LAB_CONTEXT" auth can-i get services -n "$LAB_NAMESPACE"
kubectl --context "$LAB_CONTEXT" auth can-i list endpointslices.discovery.k8s.io \
  -n "$LAB_NAMESPACE"
```

Deténgase si la cuenta, el rol o el contexto no coincide con el objetivo del laboratorio. `no`, `AccessDenied` y las credenciales vencidas indican que no hay acceso de observación disponible. No conceda permisos de administrador automáticamente ni vuelva a intentarlo en otra cuenta. Pida a un operador autorizado la evidencia mínima necesaria.

Guarde los ID de cuenta, ARN, IP y nombres de recursos originales en notas aprobadas. Use alias coherentes en un informe público. No es necesario recopilar credenciales de configuración, Secrets ni tokens.

## 3. Asignar una solicitud a recursos reales {#request-path}

Seleccione el nombre de host, protocolo, puerto y hora de una solicitud. Las siguientes son relaciones que hay que comprobar, no necesariamente saltos físicos independientes.

| Objetivo de observación | Relación | Error común |
|---|---|---|
| DNS | Dirección de frontend devuelta por el resolutor seleccionado | Confundir la resolución de nombres con el éxito de TCP/HTTP |
| Listener/grupo de destino del LB | Protocolo/regla de frontend y tipo/puerto de destino | Suponer que los puertos del listener y el backend son iguales |
| Service | Selector o endpoints administrados por separado, puerto/targetPort | Suponer que un objeto Service garantiza que existan endpoints |
| EndpointSlice/Pod | Dirección/puerto real, estado de preparación, nodo y marca temporal | Equiparar el estado preparado del endpoint con el estado del LB |
| CNI/nodo/VPC | Direccionamiento, rutas, políticas e implementación de reenvío | Suponer que todos los modos de cómputo de EKS usan el mismo DaemonSet y ruta |
| Ruta de retorno | Destino de respuesta, SNAT, seguimiento de estado y enrutamiento | Concluir que hay éxito bidireccional a partir de la accesibilidad de ida |

AWS Load Balancer Controller es un reconciliador del **plano de control** que usa las API de AWS. Las solicitudes de aplicaciones no atraviesan su Pod de controlador.

Un destino `ip` normal se conecta a una IP de backend registrada; un destino `instance` usa una ruta de nodo/NodePort. Compruebe la combinación de cómputo/CNI compatible, los registros reales, la implementación del proxy y la política de tráfico. Service describe la selección lógica de endpoints: no dibuje siempre ClusterIP como otro salto del paquete. Lea la [explicación de AWS sobre tipos de destino](https://docs.aws.amazon.com/eks/latest/best-practices/load-balancing.html) junto con la [implementación de IP virtual de Kubernetes](https://kubernetes.io/docs/reference/networking/virtual-ips/).

### Observar Service y EndpointSlice

```bash
kubectl --context "$LAB_CONTEXT" -n "$LAB_NAMESPACE" \
  get service "$LAB_SERVICE" \
  -o jsonpath='{.spec.type}{"\n"}{.spec.selector}{"\n"}{.spec.ports}{"\n"}{.spec.externalTrafficPolicy}{"\n"}'
kubectl --context "$LAB_CONTEXT" -n "$LAB_NAMESPACE" \
  get endpointslices.discovery.k8s.io \
  -l "kubernetes.io/service-name=$LAB_SERVICE" -o json
```

Correlacione las direcciones y las condiciones **dentro del mismo objeto de endpoint**. No aplane por separado las matrices de direcciones y `ready` para inventar una correspondencia. `items: []` significa que no se observó ningún endpoint con esa selección; no identifica DNS ni el firewall como causa. Tenga en cuenta los Services sin selectores y los endpoints administrados manualmente.

Después de verificar el selector real, consulte solo los Pods pertinentes.

```bash
LAB_SELECTOR='REPLACE_WITH_VERIFIED_KEY=VALUE'
kubectl --context "$LAB_CONTEXT" -n "$LAB_NAMESPACE" \
  get pods -l "$LAB_SELECTOR" -o wide
kubectl --context "$LAB_CONTEXT" -n "$LAB_NAMESPACE" get networkpolicies
```

Una lista de objetos NetworkPolicy no demuestra que haya un motor de políticas habilitado ni que funcione la aplicación. Establezca por separado el CNI, el modo de cómputo, la API compatible, los Pods seleccionados, la dirección, los puertos y el tráfico real. Otros CRD de políticas o políticas administradas requieren evidencia de sus respectivos propietarios.

### Observar destinos y rutas de AWS

Especifique el grupo de destino y la VPC verificados por el operador. Registre también evidencia que conecte ese grupo de destino con el Service seleccionado.

```bash
LAB_TARGET_GROUP_ARN='REPLACE_WITH_VERIFIED_TARGET_GROUP_ARN'
LAB_VPC_ID='REPLACE_WITH_LAB_VPC_ID'
aws --profile "$LAB_AWS_PROFILE" --region "$LAB_AWS_REGION" \
  elbv2 describe-target-groups --target-group-arns "$LAB_TARGET_GROUP_ARN" \
  --query 'TargetGroups[].{Type:TargetType,Port:Port,Protocol:Protocol,Vpc:VpcId,HealthPath:HealthCheckPath}'
aws --profile "$LAB_AWS_PROFILE" --region "$LAB_AWS_REGION" \
  elbv2 describe-target-health --target-group-arn "$LAB_TARGET_GROUP_ARN"
aws --profile "$LAB_AWS_PROFILE" --region "$LAB_AWS_REGION" \
  ec2 describe-route-tables --filters "Name=vpc-id,Values=$LAB_VPC_ID" \
  --query 'RouteTables[].{Id:RouteTableId,Associations:Associations,Routes:Routes}'
```

`healthy` es el resultado de la comprobación de estado configurada, no el recorrido completo del usuario por DNS/TLS/autorización/solicitud. Si un campo es `null`, determine primero si el protocolo/configuración lo requiere. Un tipo de destino fuera del modelo `ip`/`instance` de este cuaderno requiere revisar el modelo de ruta.

Si no hay una asociación explícita entre la subred y una tabla de rutas, compruebe si se aplica la tabla principal. Vincule el destino, el objetivo y el estado de la ruta con la subred real de origen; después, inspeccione la ruta de retorno del destino. No supla con suposiciones los permisos ni la telemetría que falten.

## 4. Ejercicio de diseño híbrido {#hybrid-design}

**Escenario de diseño:** La VPC A de producción necesita DNS/servicios compartidos. La VPC B de desarrollo no debe acceder directamente al servicio de datos de A. Los clientes locales solo pueden acceder a los servicios compartidos designados. Use alias cuando no se disponga de las direcciones/cuentas reales.

1. Registre el origen, el destino, el protocolo, la intención de permitir/denegar y la ruta de retorno.
2. Distinga las tablas de rutas de VPC/subred/TGW de las conexiones.
3. Separe la **asociación** de TGW, que selecciona la tabla de búsqueda de la conexión, de la **propagación**, que instala las rutas aprendidas. Una conexión puede asociarse a una tabla y propagar rutas a varias tablas. La propagación no hace que una conexión use esa tabla.
4. Indique las responsabilidades de la separación de rutas y de las políticas SG/NACL/de cargas de trabajo.
5. Identifique las zonas privadas, los resolutores, las reglas de reenvío y las rutas DNS bidireccionales.
6. Considere por separado los CIDR superpuestos, la ausencia de rutas de retorno y la propagación incorrecta, y explique qué flujos resultan afectados.

Consulte la [explicación de asociaciones/propagación de TGW](https://repost.aws/knowledge-center/transit-gateway-connect-vpcs-from-vpn) y compare un entorno real con [Conectividad entre VPC de distintas organizaciones](../05-cross-org-vpc-connectivity.md). Los conocimientos de políticas BGP ayudan a expresar la intención; los comandos de dispositivos locales no se aplican directamente a TGW.

## 5. Razonar a partir de observaciones {#failure-workbook}

Use **evidencia proporcionada o recopilada con aprobación**. Son ejercicios de análisis, no instrucciones para cambiar políticas de cuentas de producción.

| Observación | Siguiente comprobación | Conclusión sin fundamento |
|---|---|---|
| DNS responde, pero TCP falla | Destino, puerto, ruta, controles de acceso y listener | DNS correcto demuestra que el backend está sano |
| EndpointSlice está preparado, pero el destino está en mal estado | IP/puerto registrado, configuración de la comprobación de estado y ruta | El estado preparado equivale al estado del LB |
| Funciona en el mismo nodo, pero falla entre nodos | Ruta real CNI/nodo/VPC, política, MTU y ruta de retorno | Una causa única llamada «error de CNI» |
| Solo funcionan solicitudes pequeñas | Tamaño del paquete, información de PMTU, retransmisión y condiciones de la aplicación | Todo fallo es un problema de MTU |
| Solo funciona una dirección de TGW | Asociaciones y tablas de rutas de ambos lados | La propagación garantiza automáticamente la ruta de retorno |

La observación de paquetes/hosts requiere sus propios permisos y punto de observación. No describa la salida `get` de un recurso como una ruta de reenvío del kernel medida. Obtenga de un operador autorizado las observaciones del espacio de nombres del nodo/Pod o use una guía de laboratorio preparada por separado.

## 6. Entregables y finalización {#completion}

- Matriz de flujos permitidos/prohibidos y diagrama de rutas de ida y vuelta.
- Función real de cada componente: plano de control, enrutamiento, política o aplicación.
- Evidencia de Service/EndpointSlice/destino/ruta vinculada con el contexto, el objetivo y la marca temporal.
- Al menos dos hipótesis, con las razones por las que se confirmaron, rechazaron o se consideran desconocidas.
- Comprobaciones previas a la implementación, alcance de observación, responsable de recuperación y comprobaciones posteriores a la recuperación.

Sin evidencia en vivo, marque **revisión de diseño completada**, no validación operativa de nube completada. Las consultas de este capítulo no cambian recursos, por lo que no se necesita ningún comando de restauración de red. Administre los originales guardados de acuerdo con las normas aprobadas de retención/eliminación.

## Lecturas relacionadas

- [Redes de EKS](../../eks/03-eks-networking-part1.md), [VPC CNI](../01-vpc-cni.md), [AWS Load Balancer Controller](../03-aws-lb-controller.md)
- [Condiciones de pruebas comparativas de Pods](../06-pod-network-benchmark.md), [Visibilidad de Cilium](../cilium/06-security-visibility.md)
- [Políticas de red de EKS](https://docs.aws.amazon.com/eks/latest/userguide/cni-network-policy.html)
- [Condiciones de compatibilidad de NLB/EKS](https://docs.aws.amazon.com/eks/latest/userguide/network-load-balancing.html)
- [EndpointSlice](https://kubernetes.io/docs/concepts/services-networking/endpoint-slices/)
- [Estado de destinos mediante AWS CLI](https://docs.aws.amazon.com/cli/latest/reference/elbv2/describe-target-health.html)

[Anterior: Rendimiento de Linux](04-linux-performance.md) · [Cuestionario](../../quizzes/networking/expert/05-cloud-cni-design-quiz.md) · [Siguiente: Automatización y evaluación](06-automation-capstone.md)
