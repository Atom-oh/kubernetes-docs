# Mecanismos de extensión de Kubernetes

> **Última actualización**: 16 de octubre de 2026

## Elegir un punto de extensión

Kubernetes ofrece varias formas de ampliar las API y el comportamiento de las cargas de trabajo. Registrar una CRD no equivale a implementar su comportamiento.

| Mecanismo | Función | Requisitos operativos |
| --- | --- | --- |
| CRD + controlador | API personalizada y conciliación del estado deseado | Esquema, conciliación, RBAC, estado y eliminación |
| Agregación de API | Delegación de solicitudes a un servidor de API independiente | APIService, TLS, autenticación/autorización delegadas, descubrimiento y almacenamiento |
| Política o webhook de admisión | Validación o modificación de solicitudes a la API | Alcance, manejo de fallos, disponibilidad de CEL o del webhook |
| Plugin o extender del Scheduler | Ampliación del filtrado, la puntuación o la vinculación | Binario del scheduler compatible, registro/configuración y manejo de fallos |
| CNI | Redes de contenedores | Interfaces reales, IPAM, rutas y limpieza |
| CSI | Ciclo de vida de volúmenes y montaje en nodos | RPC adecuados para las capacidades y operaciones del backend y los nodos |

Compruebe la compatibilidad de las API, bibliotecas y distribución elegidas. La versión revisada de controller-runtime, 0.25.2 (la más reciente al 16 de octubre de 2026), usa en go.mod Go 1.26.0 y módulos Go de Kubernetes 0.37.0. Las notas sobre la interfaz del Scheduler se verificaron con el código fuente de Kubernetes 1.36.2; no dé por hecho que scheduler-plugins 0.35.7 es intercambiable con esa versión.

## CRD e instancias

Una CRD define una API personalizada con una estructura OpenAPI v3. Los campos obligatorios se aplican en el nivel que los contiene, por lo que debe exigir explícitamente tanto el spec de nivel superior como spec.image. Gestione status mediante su subrecurso y distinga las réplicas reales de availableReplicas al escalar. Sin un controlador, esta API almacena datos, pero no crea ningún Deployment.

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
  image: nginxinc/nginx-unprivileged:1.30.6-alpine
  port: 8080
```

El controlador debe completar status.replicas, availableReplicas, selector y observedGeneration según el estado observado. Un status ausente o desactualizado no significa que la operación haya tenido éxito. Si se sirven varias versiones de la API, revise la versión de almacenamiento, status.storedVersions y la conversión. Un webhook de conversión debe implementar las transformaciones necesarias; cambiar el nombre de una versión no migra los datos.

## client-go, controller-runtime y Operators

client-go proporciona clientes, informers/cachés y colas de trabajo (workqueues). Un List puntual seguido de un Watch no basta para implementar un controlador completo: gestione la continuidad de resourceVersion, el cierre del Watch, 410 Gone, la reconexión y la sincronización de la caché, además de la cancelación del contexto y la limpieza.

controller-runtime proporciona administradores, cachés/clientes, colas de trabajo, elección de líder y patrones de conciliación. Genere o proporcione los tipos Go personalizados de WebApp y el registro del esquema, y después compile con la versión de biblioteca elegida. Las referencias a tipos inexistentes de example.com/api o a appsv1.WebApp no constituyen una implementación ejecutable.

Lo siguiente es **pseudocódigo**; sus funciones y la configuración de despliegue deben implementarse por separado.

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

Las ownerReferences deben coincidir con el nombre y respetar las restricciones de UID, namespace y ámbito. Actualizar a ciegas un Deployment con el mismo nombre puede modificar la carga de trabajo de otro controlador. La recolección de basura depende de la propagación, los propietarios y los finalizers; un ownerReference no limpia datos arbitrarios en servicios externos de AWS.

Un Operator implementa conocimiento del dominio; la conmutación por error, las actualizaciones graduales y las copias de seguridad no son seguras automáticamente. El diseño de una base de datos requiere cercar el primario, mantener el quórum y las réplicas al día, probar la restauración de WAL y copias de seguridad, asegurar la compatibilidad del esquema, definir presupuestos de interrupción y ordenar el apagado.

Siga las instrucciones oficiales de instalación de Operator SDK 1.42.3 para elegir el sistema operativo y la arquitectura, y verificar las sumas de comprobación. No instale en todas partes el antiguo binario 1.25.0, que solo admite amd64. Compruebe que init/create api/make manifests funcionen con el SDK y el plugin elegidos, compile y pruebe el proyecto generado y, luego, cree y publique las imágenes y despliegue por separado.

## Agregación de API

APIService dirige las solicitudes de una ruta de grupo y versión al Service de un servidor de API de extensión. El servidor necesita TLS, descubrimiento, almacenamiento y operaciones de API como list/watch. Valide la CA y el CN del certificado de front-proxy, preserve el límite de confianza de la identidad de usuario reenviada y configure la autorización delegada.

Consulte el descubrimiento instalado para confirmar la versión real de la API de metrics-server. No use como valores predeterminados un APIService v1.metrics.k8s.io inventado ni insecureSkipTLSVerify:true. El grupo/versión, el Service y caBundle deben corresponder al servidor real. Un simple controlador HTTP o un grupo de API vacío no constituye un servidor de API de Kubernetes completo.

## Políticas y webhooks de admisión

ValidatingAdmissionPolicy es estable desde Kubernetes 1.30 y ejecuta la validación CEL dentro del proceso. Esta política y su binding aplican un límite de 1 a 5 réplicas a los Deployments y a las solicitudes deployments/scale del namespace de producción. También comprueban las actualizaciones de HPA y kubectl scale; ajuste HPA maxReplicas al mismo límite. Los nombres de los namespaces no equivalen a etiquetas de entorno arbitrarias. Evalúe el impacto operativo antes de aplicar una política.

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

Los webhooks de validación permiten o rechazan solicitudes; los webhooks mutadores pueden devolver un parche JSON (JSON Patch). Responda con la misma versión de AdmissionReview y el UID de la solicitud. patchType es JSONPatch y los bytes del parche se codifican en Base64 dentro del JSON.

Este controlador Go añade una etiqueta ilustrativa cuando se crea un Pod. Crea el mapa labels si falta o es null, conserva las etiquetas existentes y omite el parche si el valor ya coincide. Comprueba el tamaño, el método, el tipo de contenido, la versión, el UID y si la solicitud o el objeto son null. Esta etiqueta no inyecta realmente un sidecar.

### Código del webhook probado

examples/platform/extensions/webhook contiene go.mod, esta implementación y sus pruebas. Solo utiliza bibliotecas estándar de Go 1.25. Las estructuras declaran los campos de AdmissionReview que se consumen e ignoran los demás.

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

Las pruebas llamaron al controlador mediante httptest sin abrir un listener TLS. Para desplegarlo aún se necesitan una imagen, un Service, los archivos de certificado y clave, el bundle de CA real, conectividad con el servidor de API, autenticación del cliente y una política de red. Este servidor TLS no configura la autenticación de clientes de forma predeterminada. Haga coincidir los recursos, las operaciones y las rutas del webhook con el controlador.

Revise failurePolicy, timeoutSeconds, sideEffects/dryRun, reinvocationPolicy y los selectores. Fail puede bloquear solicitudes a la API si el webhook no está disponible; Ignore puede omitir su comprobación. El valor None solo debe declararse si realmente no hay efectos secundarios externos.

La inyección actual de Istio por Pod utiliza la **etiqueta** sidecar.istio.io/inject; los namespaces usan las etiquetas istio-injection o de revisión. Compruebe dónde se coloca la etiqueta en la plantilla del Pod y las reglas de inyección específicas de cada versión, en lugar de usar como valores predeterminados ejemplos antiguos con annotation.

## Framework del Scheduler y extenders

Los plugins del Framework se compilan y registran dentro del binario del scheduler. Escribir CustomFilter en YAML no carga el código que falta. Haga coincidir schedulerName del perfil con Pod spec.schedulerName para seleccionar un scheduler independiente.

Filter elimina los candidatos y Score ordena los nodos aptos. Tenga en cuenta NormalizeScore, los pesos de los plugins y cómo se resuelven los empates. Reserve/Unreserve mantienen el estado de reserva del plugin; no ofrecen una API de reserva permanente de capacidad. Permit puede permitir, rechazar o esperar; PreBind/Bind/PostBind gestionan las etapas de vinculación.

El framework público de Kubernetes 1.36.2 usa CycleState/NodeInfo de k8s.io/kube-scheduler/framework y pasa NodeInfo a Score. No copie sin más firmas antiguas con cadenas nodeName o punteros; compile con la versión menor exacta. scheduler-plugins 0.35.7 no es automáticamente intercambiable con binarios 1.36/1.37.

Un extender expone endpoints HTTP(S) independientes. Configure solo los controladores filter/prioritize/bind que estén implementados y admita Nodes o NodeNames según nodeCacheCapable. El ejemplo anterior configuraba bindVerb sin implementar su controlador. Gestione entradas nil, límites del cuerpo, tiempos de espera, TLS/autenticación, la política de fallos y los rangos de puntuación. Para seleccionar una zona de forma sencilla, considere primero la afinidad de nodos integrada.

## CNI

CNI establece el contrato de ejecución entre el runtime y el plugin de red. La biblioteca CNI 1.3.1 es distinta del valor cniVersion de la configuración. Compruebe las versiones compartidas de la especificación y la compatibilidad con operaciones como ADD, DEL, CHECK, STATUS y GC.

Un ADD correcto debe reflejar la configuración real de la interfaz del namespace, IPAM y las rutas. Devolver una IP fija en JSON no crea una conexión y puede causar colisiones. DEL debe limpiar los fallos parciales o los namespaces que ya no existen; CHECK debe inspeccionar el estado real. Copiar la misma subred host-local en varios nodos no proporciona IPAM para todo el clúster.

Compruebe las versiones de Calico, Cilium o Flannel que haya elegido para verificar sus funciones y compatibilidad con la distribución. El repositorio original de Weave Net está archivado y no se presenta como opción predeterminada para instalaciones nuevas. Esta revisión no modificó las redes del host, los veth, las rutas ni la configuración de CNI.

## CSI

CSI 1.13.0 define los conjuntos de RPC Identity, Controller y Node, además de sus capacidades. No todos los despliegues tienen que ofrecer los tres en un mismo proceso. Son posibles los plugins solo de Node; las capacidades anunciadas deben corresponder al comportamiento real de los RPC.

CreateVolume debe gestionar la idempotencia, los rangos de capacidad, la topología, los ID del backend y los errores. NodePublishVolume debe montar correctamente el volumen con los permisos y el modo de solo lectura solicitados; NodeUnpublish/Delete debe tolerar reintentos. Devolver siempre vol-123 o informar de éxito sin montar el volumen no implementa un driver real.

Una StorageClass/PVC no equivale al despliegue de un driver. El nombre del provisioner debe coincidir con un driver instalado y sus parámetros dependen de ese driver. Compruebe los sidecars del controlador, el registro de Node y sus sockets/montajes del host, las credenciales, la topología, volumeBindingMode y reclaimPolicy. Siga las instrucciones oficiales de instalación y soporte de EBS, PD, Azure Disk o Ceph CSI.

## Verificación y referencias

Se leyeron las guías originales completas: 983 líneas en coreano y 987 en inglés; también se leyeron ambos cuestionarios de 652 líneas y los 36 bloques de código únicos. Las comprobaciones abarcaron seis casos de entrada de CRD, seis casos CEL de políticas, 14 casos del webhook Go y cuatro aplicaciones reales de parches RFC6902. No se ejecutó ningún controlador de clúster completo, servidor de API agregado, scheduler ni driver CNI/CSI. El pseudocódigo explicativo no se presenta como una implementación probada.

- [CRD](https://kubernetes.io/docs/tasks/extend-kubernetes/custom-resources/custom-resource-definitions/)
- [Webhooks de admisión](https://kubernetes.io/docs/reference/access-authn-authz/extensible-admission-controllers/)
- [ValidatingAdmissionPolicy](https://kubernetes.io/docs/reference/access-authn-authz/validating-admission-policy/)
- [Agregación](https://kubernetes.io/docs/tasks/extend-kubernetes/configure-aggregation-layer/)
- [Framework del Scheduler](https://kubernetes.io/docs/concepts/scheduling-eviction/scheduling-framework/)
- [Framework 1.36.2](https://github.com/kubernetes/kubernetes/blob/v1.36.2/staging/src/k8s.io/kube-scheduler/framework/interface.go)
- [controller-runtime 0.25.2](https://github.com/kubernetes-sigs/controller-runtime/tree/v0.25.2)
- [Operator SDK](https://sdk.operatorframework.io/docs/installation/)
- [Especificación CNI 1.3.1](https://github.com/containernetworking/cni/blob/v1.3.1/SPEC.md)
- [CSI 1.13.0](https://github.com/container-storage-interface/spec/blob/v1.13.0/spec.md)
- [Inyección de Istio](https://istio.io/latest/docs/setup/additional-setup/sidecar-injection/)

[Cuestionario sobre mecanismos de extensión](../quizzes/platform-engineering/04-kubernetes-extensions-quiz.md)
