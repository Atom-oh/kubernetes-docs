# Cuestionario sobre las operaciones de EKS Hybrid Nodes

> **Última actualización**: 13 de septiembre de 2026

> **Documento relacionado**: [Operaciones](../../eks-hybrid-nodes/08-operations.md)

## Preguntas de opción múltiple

<span id="_1-what-is-the-recommended-tool-combination-for-node-monitoring-in-hybrid-nodes-environments"></span>

### 1. ¿Qué combinación puede ofrecer métricas de host y paneles para Hybrid Nodes?

- A) Bloc de notas y registro manual
- B) Prometheus, Grafana y Node Exporter configurado correctamente
- C) Solo notificaciones por correo electrónico
- D) Solo revisión manual de registros

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Prometheus, Grafana y Node Exporter configurado correctamente**

**Explicación:**

Prometheus recopila métricas, Grafana las muestra, Node Exporter expone métricas del host, DCGM Exporter expone las métricas de GPU compatibles y Alertmanager enruta alertas. Esta es una pila válida, no la única opción compatible. Instale charts/complementos revisados y verifique los montajes del host, la identidad, la ubicación, TLS, la autenticación y los destinos reales del scraping. Un DaemonSet parcial sin selectores/etiquetas de plantilla coincidentes no es una instalación funcional. Container Insights no proporciona métricas de nivel de host para Hybrid a través de IMDS de EC2 no disponible.


</details>

<span id="_2-how-do-you-check-when-kubelet-certificate-renewal-is-needed"></span>

### 2. ¿Cómo debe comprobar la caducidad de un certificado de nodo o servicio configurado?

- A) Suponer que los certificados nunca caducan
- B) Inspeccionar el certificado real con OpenSSL e identificar su emisor y responsable de renovación
- C) Esperar a que Node pase a NotReady
- D) Renovar manualmente todos los certificados todos los días

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Inspeccionar el certificado real con OpenSSL e identificar su emisor y responsable de renovación**

**Explicación:**

Primero distinga los certificados de servidor/cliente de kubelet, la CA del plano de control de EKS, TLS de Harbor y los certificados de host de IAM Roles Anywhere. La autenticación IAM de Hybrid no implica que exista un archivo `kubelet-client-current.pem`. Los comandos de renovación de kubeadm no administran el plano de control de EKS. Comprobar la caducidad es distinto de validar la cadena, el nombre de host, la revocación y la autenticación activa. `serverTLSBootstrap` por sí solo no aprueba los CSR de servidor ni renueva un certificado de IAM Roles Anywhere.

```bash
set -euo pipefail
: "${CERT_PATH:?Set the actual certificate file}"
openssl x509 -in "$CERT_PATH" -checkend 604800 -noout
```

Este ejemplo avisa cuando quedan menos de siete días; elija un umbral adecuado para la vigencia del certificado y la política de renovación. Los archivos faltantes o no válidos hacen que falle.

</details>

<span id="_3-what-is-the-first-troubleshooting-step-when-kubelet-is-not-responding-on-a-hybrid-node"></span>

### 3. ¿Qué debe inspeccionar primero si kubelet deja de responder en un Hybrid Node?

- A) Reiniciar todo el clúster
- B) Inspeccionar el estado del servicio del host correspondiente, los registros recientes y las dependencias
- C) Crear un reemplazo sin investigar
- D) Eliminar todos los Pods

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Inspeccionar el estado del servicio del host correspondiente, los registros recientes y las dependencias**

**Explicación:**

Identifique el Node registrado y su host real; después inspeccione el estado de kubelet/containerd, una cantidad limitada de líneas recientes del journal, el disco/la memoria y la ruta de red/credenciales verificada. No deshabilite TLS, no vuelque credenciales del registro ni ejecute `nodeadm reset`: ese subcomando no existe en la CLI Hybrid revisada. Reiniciar o volver a registrar el nodo es una decisión de recuperación independiente; conserve los diagnósticos y siga la guía de ciclo de vida.

```bash
# On the verified host, not a hostname guessed from its Kubernetes Node name:
sudo systemctl status kubelet containerd --no-pager
sudo journalctl -u kubelet -u containerd --since '10 minutes ago' --no-pager -n 200
```

</details>

<span id="_4-what-command-is-used-to-safely-move-workloads-for-node-maintenance"></span>

### 4. ¿Qué comando solicita la expulsión de cargas de trabajo para realizar mantenimiento planificado del nodo?

- A) `kubectl delete node`
- B) `kubectl drain`
- C) Solo `kubectl cordon`
- D) `kubectl delete pods --all`

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) `kubectl drain`**

**Explicación:**

`drain` marca el Node como no programable y normalmente usa la API Eviction, respetando los PDB aplicables. Los controladores pueden crear Pods de reemplazo; el comando no transfiere memoria ni garantiza la continuidad de la aplicación. Compruebe la capacidad disponible, la ubicación, el almacenamiento y los datos locales antes de drenar. No omita habitualmente la expulsión, no descarte datos de `emptyDir` ni anule el período de terminación de todos los Pods. Ejecute `uncordon` solo después de validar el host y las cargas de trabajo, y únicamente si el Node originalmente admitía programación.

| Comando | Alcance |
| --- | --- |
| cordon | Impide la programación normal de nuevos Pods |
| drain | Marca el nodo como no programable y solicita expulsiones, con excepciones y restricciones |
| uncordon | Restaura la programación; no es una prueba de estado |

Un PDB con `minAvailable: 2` permite una interrupción voluntaria solo cuando hay tres réplicas coincidentes en buen estado. Un PDB no evita la pérdida de un nodo ni todos los errores de la aplicación.

</details>

<span id="_5-what-is-the-recommended-solution-for-centralizing-logs-from-hybrid-nodes"></span>

### 5. ¿Qué opción puede centralizar los registros de cargas de trabajo Hybrid?

- A) Copiar cada registro manualmente
- B) Usar un recopilador Fluent Bit/Fluentd configurado y un backend central protegido
- C) No recopilar registros
- D) Leer solo la salida de consola

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Usar un recopilador Fluent Bit/Fluentd configurado y un backend central protegido**

**Explicación:**

Configure la ruta real de registros del runtime de contenedores y el analizador, los permisos de metadatos de Kubernetes, los búferes/puntos de control, los reintentos y la salida TLS autenticada. Containerd suele usar enlaces simbólicos en `/var/log/containers` que apuntan a `/var/log/pods`; no copie un manifiesto antiguo que solo sirva para Docker en `/var/lib/docker/containers`. El recopilador necesita los montajes de solo lectura adecuados del host y una política deliberada de almacenamiento de estado. La recopilación no garantiza que no se pierdan registros.

```text
Hybrid Nodes → configured collectors → CloudWatch Logs / Loki / Elasticsearch
                       ↓
              protected buffers and checkpoints
```

</details>

<span id="_6-what-is-the-default-wait-time-before-automatically-rescheduling-pods-to-other-nodes-when-a-node-fails"></span>

### 6. Con el comportamiento predeterminado de admisión y sin anulación explícita, ¿qué duración de tolerancia NoExecute se añade a los Pods normales para las condiciones not-ready y unreachable?

- A) 0 segundos
- B) 30 segundos
- C) 300 segundos
- D) 1 hora

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) 300 segundos**

**Explicación:**

Kubernetes normalmente añade `tolerationSeconds: 300` para ambos taints, salvo que se establezca explícitamente otro valor. Esta es la duración de tolerancia a un taint; no garantiza que las cargas de trabajo de reemplazo pasen a Ready exactamente cinco minutos después del fallo de un nodo. La detección, la aplicación del taint, el comportamiento del controlador, la capacidad, los volúmenes y el arranque añaden restricciones. Los Pods de DaemonSet normalmente toleran estos taints de forma indefinida. Acortar la duración no demuestra que el proceso anterior se haya detenido durante una partición; las aplicaciones con estado de escritura pueden requerir fencing.

```yaml
# Fragment under Pod spec or a workload's PodTemplate.spec, not a complete Pod:
tolerations:
- key: node.kubernetes.io/not-ready
  operator: Exists
  effect: NoExecute
  tolerationSeconds: 60
- key: node.kubernetes.io/unreachable
  operator: Exists
  effect: NoExecute
  tolerationSeconds: 60
```

El ejemplo explícito de 60 segundos requiere una decisión probada de disponibilidad/seguridad de datos; no define un SLO de recuperación de 60 segundos.

</details>

<span id="_7-what-is-the-recommended-strategy-for-eks-hybrid-nodes-upgrades"></span>

### 7. ¿Qué enfoque sigue la guía de actualización de AWS Hybrid Nodes?

- A) Actualizar todos los nodos a la vez
- B) Preferir hosts nuevos y un cambio controlado; de lo contrario, aplicar pasos in situ validados, nodo por nodo
- C) Eliminar el clúster y volver a crearlo en cada actualización
- D) No actualizar nunca

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Preferir hosts nuevos y un cambio controlado; de lo contrario, aplicar pasos in situ validados, nodo por nodo**

**Explicación:**

AWS prefiere reemplazar los hosts y migrar cuando hay capacidad disponible. La actualización in situ con nodeadm es disruptiva y acepta un argumento de versión major.minor de Kubernetes. Siga la guía de ciclo de vida para la compatibilidad de versiones, la revisión del drenado/datos, la operación real en el host, el UID del Node/versión completa/nuevo Lease y las comprobaciones de cargas de trabajo. Una espera fija o una condición Ready antigua no demuestra la aceptación. No afirme que una secuencia progresiva garantiza que el servicio nunca se interrumpa.

Antes de cada ola, compruebe las copias de seguridad, los PDB, la capacidad disponible, la compatibilidad de versiones, la identidad de credenciales y el plan de recuperación. Deténgase ante los errores y conserve las pruebas; no marque automáticamente como programable un nodo que haya fallado.

</details>
