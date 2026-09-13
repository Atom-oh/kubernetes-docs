# Mecanismos de extensión de Kubernetes

> **Última actualización**: September 12, 2026

## Elegir un punto de extensión

Kubernetes ofrece varias formas de extender las APIs y el comportamiento de las cargas de trabajo. Registrar un CRD es distinto de implementar su comportamiento.

| Mecanismo | Función | Requisitos operativos |
| --- | --- | --- |
| CRD + controller | API personalizada y reconciliación del estado deseado | Esquema, reconciliación, RBAC, status y eliminación |
| Agregación de API | Delegar peticiones a un API server independiente | APIService, TLS, autenticación/autorización delegadas, discovery/almacenamiento |
| Política/webhook de admisión | Validar o mutar peticiones a la API | Alcance, gestión de fallos, disponibilidad de CEL o del webhook |
| Plugin/extender del scheduler | Extender el filtrado, la puntuación o el binding | Binario del scheduler compatible, registro/configuración, gestión de fallos |
| CNI | Redes de contenedores | Interfaces reales, IPAM, rutas y limpieza |
| CSI | Ciclo de vida del volumen y montaje en el nodo | RPCs adecuadas a las capacidades y operaciones de backend/nodo |

Comprueba la compatibilidad de las APIs, bibliotecas y distribución elegidas. La versión actual de controller-runtime 0.25.0 usa Go 1.26 y los módulos Go de Kubernetes 0.37.0. Las notas sobre la interfaz del scheduler que figuran más abajo se verificaron contra el código fuente de Kubernetes 1.36.2; no asumas que scheduler-plugins 0.35.7 es intercambiable con él.

## CRDs e instancias

Un CRD define una API personalizada con una estructura OpenAPI v3. Los campos obligatorios se aplican en el nivel que los contiene, así que declara explícitamente como obligatorios tanto spec de nivel superior como spec.image. Gestiona status mediante su subrecurso y distingue las replicas reales de availableReplicas para el escalado. Sin un controller, esta API almacena datos pero no crea ningún Deployment.

```yaml
apiVersion: apiextensions.k8s.io/v1
kind: CustomResourceDefinition
metadata:
  name: webapps.apps.example.com
spec:
  group: apps.example.com
  names:
    kind: WebApp
    plural: webapps
    singular: webapp
    shortNames: [wa]
  scope: Namespaced
  versions:
    - name: v1
      served: true
      storage: true
      schema:
        openAPIV3Schema:
          type: object
          required: [spec]
          properties:
            spec:
              type: object
              required: [image]
              properties:
                replicas:
                  type: integer
                  default: 1
                  minimum: 1
                  maximum: 5
                image:
                  type: string
                  minLength: 1
                port:
                  type: integer
                  default: 8080
                  minimum: 1
                  maximum: 65535
            status:
              type: object
              properties:
                replicas:
                  type: integer
                availableReplicas:
                  type: integer
                selector:
                  type: string
                observedGeneration:
                  type: integer
                  format: int64
      subresources:
        status: {}
        scale:
          specReplicasPath: .spec.replicas
          statusReplicasPath: .status.replicas
          labelSelectorPath: .status.selector
```

```yaml
apiVersion: apps.example.com/v1
kind: WebApp
metadata:
  name: reviewed-web
  namespace: example
spec:
  replicas: 2
  image: nginxinc/nginx-unprivileged:1.30.4-alpine
  port: 8080
```

El controller debe rellenar status.replicas, availableReplicas, selector y observedGeneration a partir del estado observado. Un status ausente u obsoleto no es un éxito. Si se sirven varias versiones de la API, revisa la versión de almacenamiento, status.storedVersions y la conversión. Un webhook de conversión debe implementar las transformaciones necesarias; renombrar una versión no migra los datos.

## client-go, controller-runtime y Operators

client-go proporciona clientes, informers/cachés y workqueues. Un único List seguido de un Watch no constituye un controller completo: hay que gestionar la continuidad de resourceVersion, el cierre del watch, los 410 Gone, la reconexión y la sincronización de la caché, así como la cancelación del contexto y la limpieza.

controller-runtime aporta managers, caché/clientes, workqueues, elección de líder y patrones de reconciliación. Genera o proporciona los tipos Go personalizados de WebApp y el registro del scheme, y luego compila contra la versión de biblioteca elegida. Las referencias a tipos inexistentes de example.com/api o a appsv1.WebApp no constituyen una implementación ejecutable.

Lo siguiente es **pseudocódigo**; sus funciones y su configuración de despliegue deben implementarse por separado.

```text
Reconcile(namespace, name):
  read WebApp; return successfully if it no longer exists
  if deletionTimestamp is set:
    finish idempotent external cleanup under the declared retention policy
    remove only this controller's finalizer after cleanup succeeds
    return
  persist a required finalizer before creating external resources
  read the desired child Deployment
  reject conflicting ownership; do not silently adopt another controller's object
  reconcile image, replicas, ports and owned fields without needless updates
  handle conflicts by rereading; do not index a possibly empty container list
  observe children and patch status only when it changes
  report failure/readiness and requeue when another observation is needed
```

Los ownerReferences deben coincidir en UID, namespace y restricciones de alcance, además del nombre. Actualizar a ciegas un Deployment con el mismo nombre puede modificar la carga de trabajo de otro controller. La recolección de basura depende de la propagación, los owners y los finalizers; un ownerReference no limpia datos externos arbitrarios de AWS.

Un Operator implementa conocimiento del dominio; el failover, las actualizaciones progresivas y las copias de seguridad no son seguros de forma automática. Los diseños de bases de datos requieren fencing del primario, quórum, puesta al día de las réplicas, pruebas de restauración de WAL/backup, compatibilidad de esquemas, presupuestos de interrupción y orden de apagado.

Usa las instrucciones oficiales de instalación de Operator SDK 1.42.3 para seleccionar el sistema operativo/arquitectura y las sumas de comprobación. No instales en todas partes el antiguo binario 1.25.0 solo para amd64. Verifica init/create api/make manifests contra el SDK/plugin elegido, compila y prueba el proyecto generado y, por separado, construye/publica las imágenes y despliega.

## Agregación de API

APIService dirige una ruta de group/version al Service de un API server de extensión. El servidor necesita TLS, discovery, almacenamiento y comportamientos de API como list/watch. Valida la CA/CN del certificado del front-proxy, preserva el límite de confianza en torno a la identidad de usuario reenviada y configura la autorización delegada.

Inspecciona el discovery instalado para conocer la versión real de la API de metrics-server. No uses un APIService v1.metrics.k8s.io inventado ni insecureSkipTLSVerify:true como opción por defecto. El group/version, el Service y el caBundle deben coincidir con el servidor real. Un handler HTTP sencillo o un grupo de API vacío no es un API server de Kubernetes completo.

## Políticas de admisión y webhooks

ValidatingAdmissionPolicy es estable desde Kubernetes 1.30 y ejecuta la validación CEL en el propio proceso. Esta política/binding limita replicas a 1–5 para los Deployments y las peticiones deployments/scale en el namespace production. También comprueba las actualizaciones de HPA y de kubectl scale; alinea maxReplicas del HPA con el límite. Los nombres de namespace no equivalen a etiquetas de entorno arbitrarias. Revisa el impacto operativo antes de aplicar una política.

```yaml
apiVersion: admissionregistration.k8s.io/v1
kind: ValidatingAdmissionPolicy
metadata:
  name: reviewed-replica-limit
spec:
  failurePolicy: Fail
  matchConstraints:
    resourceRules:
      - apiGroups: [apps]
        apiVersions: [v1]
        operations: [CREATE, UPDATE]
        resources: [deployments, deployments/scale]
  validations:
    - expression: "!has(object.spec.replicas) || (object.spec.replicas >= 1 && object.spec.replicas <= 5)"
      message: replicas must be between 1 and 5
---
apiVersion: admissionregistration.k8s.io/v1
kind: ValidatingAdmissionPolicyBinding
metadata:
  name: reviewed-replica-limit-production
spec:
  policyName: reviewed-replica-limit
  validationActions: [Deny]
  matchResources:
    namespaceSelector:
      matchLabels:
        kubernetes.io/metadata.name: production
```

Los webhooks de validación permiten o deniegan peticiones; los de mutación pueden devolver un JSON Patch. Responde usando la misma versión de AdmissionReview y el mismo UID de la petición. patchType es JSONPatch y los bytes del patch van codificados en Base64 dentro del JSON.

Este handler en Go añade una etiqueta ilustrativa al crear un Pod (CREATE). Crea el mapa de labels cuando falta o es null, preserva las etiquetas existentes y omite el patch cuando el valor ya coincide. Comprueba el tamaño, el método, el content type, la versión, el UID y las peticiones/objetos nulos. Esta etiqueta no inyecta realmente un sidecar.

### Código del webhook probado

examples/platform/extensions/webhook contiene go.mod, esta implementación y sus pruebas. Solo usa las bibliotecas estándar de Go 1.25. Las structs declaran los campos de AdmissionReview que se consumen e ignoran los demás.

```go
package main

import (
	"encoding/json"
	"errors"
	"io"
	"log"
	"mime"
	"net/http"
	"time"
)

type groupVersionResource struct {
	Group    string `json:"group"`
	Version  string `json:"version"`
	Resource string `json:"resource"`
}

type admissionRequest struct {
	UID         string               `json:"uid"`
	Operation   string               `json:"operation"`
	Resource    groupVersionResource `json:"resource"`
	SubResource string               `json:"subResource"`
	Object      json.RawMessage      `json:"object"`
}

type admissionResponse struct {
	UID       string `json:"uid"`
	Allowed   bool   `json:"allowed"`
	Patch     []byte `json:"patch,omitempty"`
	PatchType string `json:"patchType,omitempty"`
}

type review struct {
	APIVersion string             `json:"apiVersion"`
	Kind       string             `json:"kind"`
	Request    *admissionRequest  `json:"request,omitempty"`
	Response   *admissionResponse `json:"response,omitempty"`
}

type podInput struct {
	APIVersion string `json:"apiVersion"`
	Kind       string `json:"kind"`
	Metadata   *struct {
		Labels map[string]string `json:"labels"`
	} `json:"metadata"`
}

type patchOperation struct {
	Op    string `json:"op"`
	Path  string `json:"path"`
	Value any    `json:"value"`
}

func mutate(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		w.Header().Set("Allow", http.MethodPost)
		http.Error(w, "POST required", http.StatusMethodNotAllowed)
		return
	}
	mediaType, _, err := mime.ParseMediaType(r.Header.Get("Content-Type"))
	if err != nil || mediaType != "application/json" {
		http.Error(w, "application/json required", http.StatusUnsupportedMediaType)
		return
	}
	r.Body = http.MaxBytesReader(w, r.Body, 1<<20)
	defer r.Body.Close()
	decoder := json.NewDecoder(r.Body)
	var incoming review
	if err := decoder.Decode(&incoming); err != nil {
		http.Error(w, "invalid admission body", http.StatusBadRequest)
		return
	}
	if err := decoder.Decode(new(any)); !errors.Is(err, io.EOF) {
		http.Error(w, "single JSON document required", http.StatusBadRequest)
		return
	}
	if incoming.APIVersion != "admission.k8s.io/v1" || incoming.Kind != "AdmissionReview" ||
		incoming.Request == nil || incoming.Request.UID == "" {
		http.Error(w, "v1 AdmissionReview request with UID required", http.StatusBadRequest)
		return
	}
	request := incoming.Request
	response := admissionResponse{UID: request.UID, Allowed: true}
	if request.Resource == (groupVersionResource{Group: "", Version: "v1", Resource: "pods"}) &&
		request.SubResource == "" && request.Operation == "CREATE" {
		var pod podInput
		if err := json.Unmarshal(request.Object, &pod); err != nil ||
			pod.APIVersion != "v1" || pod.Kind != "Pod" || pod.Metadata == nil {
			http.Error(w, "valid Pod object required", http.StatusBadRequest)
			return
		}
		if pod.Metadata.Labels["example.com/injected"] != "true" {
			operation := patchOperation{
				Op: "add", Path: "/metadata/labels/example.com~1injected", Value: "true",
			}
			if pod.Metadata.Labels == nil {
				operation.Path = "/metadata/labels"
				operation.Value = map[string]string{"example.com/injected": "true"}
			}
			patch, err := json.Marshal([]patchOperation{operation})
			if err != nil {
				http.Error(w, "patch encoding failed", http.StatusInternalServerError)
				return
			}
			response.Patch = patch
			response.PatchType = "JSONPatch"
		}
	}
	outgoing := review{
		APIVersion: "admission.k8s.io/v1", Kind: "AdmissionReview", Response: &response,
	}
	body, err := json.Marshal(outgoing)
	if err != nil {
		http.Error(w, "response encoding failed", http.StatusInternalServerError)
		return
	}
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)
	if _, err := w.Write(body); err != nil {
		log.Printf("write admission response: %v", err)
	}
}

func main() {
	mux := http.NewServeMux()
	mux.HandleFunc("/mutate", mutate)
	server := &http.Server{
		Addr: ":8443", Handler: mux,
		ReadHeaderTimeout: 5 * time.Second,
		ReadTimeout:       10 * time.Second,
		WriteTimeout:      10 * time.Second,
		IdleTimeout:       30 * time.Second,
	}
	// Mount the approved certificate/key as files; the key is never an environment variable.
	log.Fatal(server.ListenAndServeTLS("/tls/tls.crt", "/tls/tls.key"))
}
```

```bash
cd examples/platform/extensions/webhook
go test ./...
```

Las pruebas invocaron el handler a través de httptest sin abrir un listener TLS. El despliegue sigue requiriendo una imagen, un Service, ficheros de certificado/clave, un bundle de CA real, conectividad con el API server, autenticación del llamante y una network policy. Este servidor TLS no configura la autenticación de cliente por defecto. Haz coincidir los recursos, operaciones y rutas del webhook con el handler.

Revisa failurePolicy, timeoutSeconds, sideEffects/dryRun, reinvocationPolicy y los selectores. Fail puede bloquear peticiones a la API cuando el webhook no está disponible; Ignore puede omitir su comprobación. Declarar None debe reflejar la ausencia real de efectos secundarios externos.

La inyección por Pod actual de Istio usa la **label** sidecar.istio.io/inject; los namespaces usan istio-injection o labels de revisión. Verifica la ubicación de la label en la plantilla del Pod y las reglas de inyección propias de cada versión, en lugar de mantener los antiguos ejemplos con annotations como opción por defecto.

## Framework del scheduler y extenders

Los plugins del framework se compilan y registran dentro de un binario del scheduler. Nombrar CustomFilter en YAML no carga código inexistente. Haz coincidir el schedulerName del perfil con spec.schedulerName del Pod para seleccionar un scheduler independiente.

Filter elimina candidatos y Score clasifica los nodos viables. Ten en cuenta NormalizeScore, los pesos de los plugins y la selección en caso de empate. Reserve/Unreserve mantienen el estado de reserva del plugin, no una API permanente de reserva de capacidad. Permit puede permitir, rechazar o esperar; PreBind/Bind/PostBind gestionan las etapas del binding.

El framework público de Kubernetes 1.36.2 usa CycleState/NodeInfo de k8s.io/kube-scheduler/framework y pasa NodeInfo a Score. No copies a ciegas las antiguas firmas con nodeName como string o puntero; compila contra la versión menor exacta. scheduler-plugins 0.35.7 no es automáticamente intercambiable con los binarios 1.36/1.37.

Un extender expone endpoints HTTP(S) independientes. Configura únicamente los handlers de filter/prioritize/bind que estén implementados y da soporte a Nodes frente a NodeNames según nodeCacheCapable. El ejemplo anterior configuraba bindVerb sin implementarlo. Gestiona las entradas nil, los límites de tamaño del cuerpo, los timeouts, TLS/autenticación, la política de fallos y los rangos de puntuación. Para una selección sencilla de zona, considera primero la node affinity integrada.

## CNI

CNI es el contrato de ejecución entre el runtime y el plugin de red. La biblioteca CNI 1.3.1 es distinta del cniVersion de la configuración. Verifica las versiones compartidas de la especificación y el soporte de operaciones como ADD, DEL, CHECK, STATUS y GC.

Un ADD correcto debe reflejar la configuración real de la interfaz en el namespace, el IPAM y las rutas. Devolver una IP fija en JSON no crea ninguna conexión y puede provocar colisiones. DEL debe limpiar los fallos parciales o los namespaces inexistentes; CHECK debe inspeccionar el estado real. Copiar la misma subred host-local en varios nodos no proporciona IPAM de clúster.

Consulta las releases elegidas de Calico, Cilium o Flannel para conocer sus funcionalidades y la compatibilidad con la distribución. El repositorio original de Weave Net está archivado y no se presenta como opción por defecto para nuevas instalaciones. Esta auditoría no modificó la red del host, los veth, las rutas ni la configuración de CNI.

## CSI

CSI 1.13.0 define los conjuntos de RPC Identity, Controller y Node, y sus capacidades. No todo despliegue tiene que proporcionar los tres en un mismo proceso. Es posible tener plugins solo de nodo; las capacidades anunciadas deben coincidir con el comportamiento real de las RPC.

CreateVolume debe gestionar la idempotencia, los rangos de capacidad, la topología, los IDs del backend y los errores. NodePublishVolume debe montar correctamente con los permisos y el comportamiento de solo lectura solicitados; NodeUnpublish/Delete deben gestionar los reintentos. Devolver siempre vol-123 o informar de éxito sin montar nada no implementa un driver real.

Un StorageClass/PVC no es un despliegue de driver. El nombre del provisioner debe coincidir con un driver instalado y los parámetros son específicos de cada driver. Revisa los sidecars del controller, el registro del nodo/socket/montajes del host, las credenciales, la topología, volumeBindingMode y reclaimPolicy. Sigue la guía oficial de instalación y soporte de EBS, PD, Azure Disk o Ceph CSI.

## Verificación y referencias

Se leyeron las guías originales de 983 líneas en coreano y 987 líneas en inglés, los dos cuestionarios de 652 líneas y 36 bloques de código únicos. Las comprobaciones cubrieron seis casos de entrada de CRD, seis casos de CEL de políticas, 14 casos del webhook en Go y cuatro aplicaciones reales de patches RFC6902. No se ejecutó ningún controller de clúster completo, API server agregado, scheduler ni driver CNI/CSI. El pseudocódigo explicativo no se presenta como implementación probada.

- [CRDs](https://kubernetes.io/docs/tasks/extend-kubernetes/custom-resources/custom-resource-definitions/)
- [Admission webhooks](https://kubernetes.io/docs/reference/access-authn-authz/extensible-admission-controllers/)
- [ValidatingAdmissionPolicy](https://kubernetes.io/docs/reference/access-authn-authz/validating-admission-policy/)
- [Aggregation](https://kubernetes.io/docs/tasks/extend-kubernetes/configure-aggregation-layer/)
- [Scheduler framework](https://kubernetes.io/docs/concepts/scheduling-eviction/scheduling-framework/)
- [Framework 1.36.2](https://github.com/kubernetes/kubernetes/blob/v1.36.2/staging/src/k8s.io/kube-scheduler/framework/interface.go)
- [controller-runtime 0.25.0](https://github.com/kubernetes-sigs/controller-runtime/tree/v0.25.0)
- [Operator SDK](https://sdk.operatorframework.io/docs/installation/)
- [CNI 1.3.1 source](https://github.com/containernetworking/cni/blob/v1.3.1/SPEC.md)
- [CSI 1.13.0](https://github.com/container-storage-interface/spec/blob/v1.13.0/spec.md)
- [Istio injection](https://istio.io/latest/docs/setup/additional-setup/sidecar-injection/)

[Cuestionario sobre mecanismos de extensión](../quizzes/platform-engineering/04-kubernetes-extensions-quiz.md)
