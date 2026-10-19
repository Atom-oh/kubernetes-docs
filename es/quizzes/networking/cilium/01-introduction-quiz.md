# Cuestionario de introducción y conceptos básicos de Cilium

> **Versión de referencia**: Cilium 1.20.3 / CLI 0.20.1. **Última actualización**: 16 de octubre de 2026

## Preguntas de opción múltiple

1. ¿Qué tecnología proporciona la ruta de datos programable de Cilium en el kernel?
   - A) iptables
   - B) eBPF
   - C) VXLAN
   - D) IPsec

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) eBPF**

**Explicación:**
Cilium carga programas eBPF verificados en hooks del kernel compatibles. Esto habilita funciones de red y observabilidad, pero no garantiza un rendimiento superior al de todas las alternativas; mida la carga de trabajo y la configuración elegidas.

</details>

2. ¿Qué capas de políticas puede admitir Cilium con las integraciones necesarias?
   - A) Solo L3
   - B) Solo L3–L4
   - C) L3/L4 y protocolos L7 compatibles
   - D) Solo L2–L3

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) L3/L4 y protocolos L7 compatibles**

**Explicación:**
Las políticas HTTP y DNS utilizan rutas de proxy compatibles; el HTTP cifrado requiere la terminación o integración adecuada. Las reglas L7 para Kafka se eliminaron en la versión 1.20. Las políticas L4 aún pueden controlar las conexiones de Kafka.

</details>

3. ¿Qué componente de Cilium proporciona visibilidad de los flujos de red?
   - A) Prometheus
   - B) Hubble
   - C) Grafana
   - D) Jaeger

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Hubble**

**Explicación:**
Hubble observa los flujos de red y del proxy, y puede mostrar relaciones entre servicios. La visibilidad HTTP depende de la ruta del proxy. Hubble no genera automáticamente trazas completas de la aplicación; las métricas de Prometheus y el trazado distribuido cumplen funciones distintas.

</details>

4. ¿Qué componente de Service de Kubernetes puede reemplazar Cilium en una configuración compatible?
   - A) CoreDNS
   - B) kube-proxy
   - C) etcd
   - D) kubelet

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) kube-proxy**

**Explicación:**
kubeProxyReplacement solicita que Cilium gestione los Services. Siguen siendo importantes el acceso a la API y al bootstrap, así como los requisitos previos de migración. DSR, Maglev y XDP son opciones independientes, no garantías automáticas de un mejor rendimiento.

</details>

5. ¿Qué par corresponde a los modos de cifrado de red transparente de Cilium?
   - A) IPsec y WireGuard
   - B) TLS y SSH
   - C) GRE y HTTP
   - D) DNS y VXLAN

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A) IPsec y WireGuard**

**Explicación:**
En esta pregunta, IPsec y WireGuard son el par establecido. La misma clave `encryption.type` también acepta `ztunnel` beta para mTLS de cargas de trabajo, con sus propios requisitos de inscripción por namespace, CA/bootstrap, tráfico y políticas. Son modos diferentes de la misma clave; afirmar que Cilium nunca usa TLS sería incorrecto.

</details>

6. ¿Cómo se llama la función de conectividad multiclúster de Cilium?
   - A) Cluster Federation
   - B) ClusterMesh
   - C) Multi-Cluster Network
   - D) Global Cluster

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) ClusterMesh**

**Explicación:**
ClusterMesh conecta clústeres compatibles con identidades, confianza y alcance de red configurados. No crea toda la red subyacente ni hace que todos los Services sean accesibles globalmente de forma automática.

</details>

7. ¿Qué tecnología puede usar Cilium para acelerar opcionalmente el procesamiento temprano de paquetes o el balanceo de carga?
   - A) DPDK
   - B) XDP
   - C) RDMA
   - D) SR-IOV

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) XDP**

**Explicación:**
XDP puede procesar determinados flujos en una etapa temprana, si el hook/controlador es compatible. No se utiliza en todas las rutas de paquetes de Cilium, y habilitarlo no garantiza una tasa determinada de paquetes por segundo ni una protección DDoS completa.

</details>

8. ¿Cuál es la versión base estándar del kernel Linux upstream para Cilium 1.20, sin contar equivalencias documentadas con backports de proveedores?
   - A) 3.10
   - B) 4.9
   - C) 4.19
   - D) 5.10

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: D) 5.10**

**Explicación:**
Los requisitos actuales indican Linux 5.10 o posterior, con equivalencias nombradas, como la versión 4.18 con backports de RHEL 8.10. Algunas funciones individuales pueden necesitar kernels más recientes. Compruebe el kernel del nodo/VM, no solo el sistema operativo de la estación de trabajo.

</details>

9. ¿Qué opción proporciona conectividad VXLAN/host-gw sin requerir el plano de datos eBPF de Cilium?
   - A) Enrutamiento nativo de Cilium
   - B) Modo BPF de Calico
   - C) VXLAN/host-gw de Flannel
   - D) Modo netkit de Cilium

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) VXLAN/host-gw de Flannel**

**Explicación:**
Los backends de conectividad de Flannel son una implementación distinta. Evalúe por separado su controlador de políticas opcional u otra integración de políticas; evite clasificaciones universales de recursos o rendimiento.

</details>

10. ¿Cuál es la versión de la API de CiliumNetworkPolicy?
   - A) networking.k8s.io/v1
   - B) cilium.io/v1
   - C) cilium.io/v2
   - D) policy.cilium.io/v1

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) cilium.io/v2**

**Explicación:**
CiliumNetworkPolicy es una API/CRD distinta de NetworkPolicy estándar de Kubernetes. La disponibilidad de funciones sigue dependiendo de la versión de Cilium y de la configuración del plano de datos/proxy.

</details>

## Preguntas de respuesta corta

11. ¿Qué componente se ejecuta en cada nodo y programa los endpoints y las políticas eBPF?

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: Cilium Agent**

**Explicación:**
El agente realiza el trabajo local del nodo. El runtime de contenedores/complemento CNI, el operador, el proxy y el sistema operativo del host tienen otras responsabilidades; el agente no controla todas las operaciones de red.

</details>

12. ¿Qué componente coordina el trabajo de asignación y control a nivel de clúster?

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: Cilium Operator**

**Explicación:**
El operador puede ejecutarse con varias réplicas; los valores predeterminados del chart revisado son dos, con elección de líder para las tareas que corresponda. Sus responsabilidades dependen del modo de IPAM/identidad. No es necesariamente una sola instancia ni el único responsable de todas las conexiones de ClusterMesh.

</details>

13. ¿Qué comando de CLI ejecuta las cargas de trabajo de prueba de conectividad de Cilium?

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: cilium connectivity test**

**Explicación:**
Crea cargas de trabajo y políticas, por lo que requiere un entorno de pruebas aprobado y los permisos necesarios. Para una inspección de solo lectura, empiece por cilium status, los diagnósticos de endpoints y Hubble. El comando de gestión cilium monitor no es la interfaz de diagnóstico actual del agente.

</details>

14. ¿Cuál es el identificador numérico asociado a las etiquetas de un endpoint relevantes para la seguridad?

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: identidad de seguridad (identidad de Cilium)**

**Explicación:**
Solo el conjunto de etiquetas pertinente o seleccionado determina la identidad dentro de su ámbito de asignación. Las etiquetas derivadas del namespace pueden diferir; que las etiquetas de la aplicación coincidan por sí solas no demuestra que las identidades sean iguales. El ID numérico se asigna y no es un hash permanente con significado global.

</details>

15. ¿Qué especificación define la interfaz de complemento de red para contenedores?

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: CNI (Container Network Interface)**

**Explicación:**
Kubelet se comunica con el runtime mediante CRI, y el runtime invoca CNI. CNI intercambia la configuración y los resultados de red, y se encarga de la configuración y la eliminación. Los flags de configuración CNI de kubelet se eliminaron en Kubernetes 1.24.

</details>

## Preguntas prácticas

16. Con la CLI instalada, muestra una instalación nueva de Cilium 1.20.3 con los valores de laboratorio preparados y el contexto explícito.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:**

```bash
CILIUM_LAB_CONTEXT=replace-with-nonproduction-context
cilium version --client
cilium install --context "$CILIUM_LAB_CONTEXT" --version 1.20.3 \
  --values cilium-lab-values.yaml
cilium status --context "$CILIUM_LAB_CONTEXT" --wait
```

**Explicación:**
Utilice los requisitos previos del entorno/CNI, la propiedad, los CIDR y los valores que ya se validaron en la guía. Omita la instalación si ya existe una versión y siga el proceso de actualización de quien la administra. El estado no reemplaza las pruebas de tráfico permitido y denegado.

</details>

17. Escribe la política de laboratorio que permite la entrada TCP del Pod frontend al puerto 8080 del Pod backend dentro de cilium-intro-demo.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:**

```yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: allow-frontend-backend
  namespace: cilium-intro-demo
spec:
  endpointSelector:
    matchLabels:
      k8s:app: backend
  ingress:
  - fromEndpoints:
    - matchLabels:
        k8s:app: frontend
        k8s:io.kubernetes.pod.namespace: cilium-intro-demo
    toPorts:
    - ports:
      - port: '8080'
        protocol: TCP
```

**Explicación:**
El namespace y las cargas de trabajo ya deben existir. El namespace explícito del peer evita conceder el mismo acceso basado en etiquetas a otros namespaces. Otras políticas de permiso/denegación y el tráfico del host afectan el resultado; esta regla no filtra HTTP ni restringe el egreso.

</details>

18. Muestra un ejemplo parcial de valores que solicita el reemplazo de kube-proxy y DSR con enrutamiento nativo y Geneve. ¿Qué debe prepararse además?

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:**

```yaml
kubeProxyReplacement: true
k8sServiceHost: api.lab.example.internal
k8sServicePort: 443
routingMode: native
tunnelProtocol: geneve
ipv4NativeRoutingCIDR: 10.244.0.0/16
loadBalancer:
  mode: dsr
  dsrDispatch: geneve
```

**Explicación:**
Este es un perfil nativo distinto; no es una instrucción para habilitar DSR en el laboratorio VXLAN. Sustituya el host/puerto de la API y el CIDR de enrutamiento nativo por los valores reales ya preparados. Asegure acceso DNS a la API/bootstrap, rutas subyacentes para los Pods, Geneve/MTU y las rutas de retorno/dirección de origen; después siga el procedimiento de migración de kube-proxy compatible. Los valores estáticos no garantizan compatibilidad con el balanceador de carga de nube ni eliminan todos los cuellos de botella.

</details>

19. Muestra el estado del clúster, el estado local del endpoint backend seleccionado y los recursos de políticas deseados.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:**

```bash
CILIUM_LAB_CONTEXT=replace-with-nonproduction-context
CILIUM_LAB_NS=cilium-intro-demo
BACKEND_POD=replace-with-actual-backend-pod
cilium status --context "$CILIUM_LAB_CONTEXT" --verbose
kubectl --context "$CILIUM_LAB_CONTEXT" get pod "$BACKEND_POD" -n "$CILIUM_LAB_NS" -o wide
kubectl --context "$CILIUM_LAB_CONTEXT" get pods -n kube-system -l k8s-app=cilium -o wide

# Choose the agent on the backend Pod's node.
CILIUM_AGENT_POD=replace-with-agent-pod-on-that-node
kubectl --context "$CILIUM_LAB_CONTEXT" exec -n kube-system "$CILIUM_AGENT_POD" \
  -c cilium-agent -- cilium-dbg endpoint list
kubectl --context "$CILIUM_LAB_CONTEXT" exec -n kube-system "$CILIUM_AGENT_POD" \
  -c cilium-agent -- cilium-dbg endpoint get "pod-name:$CILIUM_LAB_NS:$BACKEND_POD"
kubectl --context "$CILIUM_LAB_CONTEXT" get networkpolicy -n "$CILIUM_LAB_NS" -o yaml
kubectl --context "$CILIUM_LAB_CONTEXT" get cnp -n "$CILIUM_LAB_NS" -o yaml
kubectl --context "$CILIUM_LAB_CONTEXT" get ccnp -o yaml
```

**Explicación:**
Los identificadores de endpoint y el estado aplicado corresponden al agente/nodo seleccionado; use el identificador de Pod que admita cilium-dbg. kubectl consulta los recursos de política deseados, no demuestra su aplicación. cilium-dbg policy get está obsoleto, y los comandos de gestión cilium endpoint/policy/monitor no son equivalentes.

</details>

20. Habilita Hubble para la versión existente del laboratorio y observa flujos con las herramientas de cliente ya instaladas.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:**

```bash
# Terminal 1; the lab Cilium release and client tools must already exist.
CILIUM_LAB_CONTEXT=replace-with-nonproduction-context
cilium hubble enable --context "$CILIUM_LAB_CONTEXT" --ui
cilium hubble port-forward --context "$CILIUM_LAB_CONTEXT" --port-forward 4245
```

```bash
# Terminal 2, with the port-forward still running.
BACKEND_POD=replace-with-actual-backend-pod
hubble observe --server 127.0.0.1:4245 --namespace cilium-intro-demo
hubble observe --server 127.0.0.1:4245 --pod "cilium-intro-demo/$BACKEND_POD"
hubble observe --server 127.0.0.1:4245 --protocol http
hubble observe --server 127.0.0.1:4245 --verdict DROPPED
```

**Explicación:**
Si la versión está gestionada por GitOps, cambie los valores de Helm del propietario en vez de usar una actualización imperativa con la CLI; omita el paso de habilitación si ya está habilitado. Mantenga activo el port-forward en primer plano y configure TLS de cliente si Relay lo usa. Los eventos HTTP requieren una ruta de proxy L7 compatible, y DROPPED no representa todos los fallos de aplicación. Use cilium hubble ui en otro terminal con el mismo contexto explícito para acceder a la interfaz.

</details>

---

[Volver a los materiales de aprendizaje](../../../networking/cilium/01-introduction.md) | [Siguiente cuestionario: conceptos básicos de eBPF](02-ebpf-quiz.md)
