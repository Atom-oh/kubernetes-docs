# Mecanismos de extensión de Kubernetes

> **Última actualización**: October 12, 2026

## Elegir un punto de extensión

Kubernetes ofrece varias formas de extender las APIs y el comportamiento de las cargas de trabajo. Registrar una CRD es diferente de implementar su comportamiento.

| Mecanismo | Función | Requisitos operativos |
| --- | --- | --- |
| CRD + controller | API personalizada y reconciliación del estado deseado | Esquema, reconciliación, RBAC, estado y eliminación |
| Agregación de API | Delegar solicitudes a un servidor de API independiente | APIService, TLS, autenticación/autorización delegadas, descubrimiento/almacenamiento |
| Política/webhook de admisión | Validar o mutar solicitudes de API | Alcance, manejo de errores, disponibilidad de CEL o webhook |
| Plugin/extender de Scheduler | Extender el filtrado, la puntuación o el enlace | Binario de Scheduler compatible, registro/configuración, manejo de errores |
| CNI | Redes de contenedores | Interfaces reales, IPAM, rutas y limpieza |
| CSI | Ciclo de vida de volúmenes y montaje en nodos | RPC adecuados para las capacidades y operaciones de backend/nodo |

Verifique la compatibilidad de las APIs, bibliotecas y distribución elegidas. El go.mod de controller-runtime 0.25.0 revisado usa Go 1.26.0 y módulos Go de Kubernetes 0.37.0 (la versión más reciente v0.25.2 al 12 de octubre de 2026). Las notas sobre la interfaz de Scheduler a continuación se verificaron con el código fuente de Kubernetes 1.36.2; no asuma que scheduler-plugins 0.35.7 es intercambiable con este.

## CRD e instancias

Una CRD define una API personalizada con una estructura OpenAPI v3. Los campos obligatorios se aplican en su nivel contenedor, por lo que debe requerir explícitamente tanto spec de nivel superior como spec.image. Gestione status mediante su subrecurso y distinga las réplicas reales de availableReplicas para la escala. Sin un controller, esta API almacena datos, pero no crea ningún Deployment.

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

El controller debe completar status.replicas, availableReplicas, selector y observedGeneration a partir del estado observado. Un status ausente o desactualizado no es exitoso. Para múltiples versiones de API servidas, revise la versión de almacenamiento, status.storedVersions y la conversión. Un webhook de conversión debe implementar las transformaciones requeridas; cambiar el nombre de una versión no migra los datos.

## client-go, controller-runtime y Operators

client-go proporciona clientes, informers/cachés y workqueues. Un List de una sola vez seguido de Watch no es un controller completo: gestione la continuidad de resourceVersion, el cierre de Watch, 410 Gone, la reconexión y la sincronización de caché, así como la cancelación de contexto y la limpieza.

controller-runtime proporciona managers, caché/clientes, workqueues, elección de líder y patrones de reconciliación. Genere o proporcione los tipos Go personalizados de WebApp y el registro de scheme, luego compile con la versión de biblioteca elegida. Las referencias a tipos inexistentes example.com/api o appsv1.WebApp no constituyen una implementación ejecutable.

Lo siguiente es **pseudocódigo**; sus funciones y configuración de Deployment deben implementarse por separado.

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

ownerReferences debe coincidir con las restricciones de UID, namespace y alcance, además del nombre. Actualizar a ciegas un Deployment con el mismo nombre puede mutar la carga de trabajo de otro controller. La recolección de basura depende de la propagación, los propietarios y los finalizers; un ownerReference no limpia datos externos arbitrarios de AWS.

Un Operator implementa conocimiento del dominio; la conmutación por error, las actualizaciones graduales y las copias de seguridad no son seguras automáticamente. Los diseños de bases de datos necesitan fencing del primario, quórum, sincronización de réplicas, pruebas de restauración de WAL/copias de seguridad, compatibilidad de esquema, presupuestos de interrupción y orden de apagado.

Use las instrucciones oficiales de instalación de Operator SDK 1.42.3 para seleccionar SO/arquitectura y sumas de verificación. No instale en todos lados el binario antiguo 1.25.0 solo para amd64. Verifique init/create api/make manifests con el SDK/plugin elegido, compile/pruebe el proyecto generado y, por separado, cree/publique imágenes y realice el despliegue.

## Agregación de API

APIService enruta una ruta de grupo/versión a un Service de un servidor de API de extensión. El servidor necesita TLS, descubrimiento, almacenamiento y comportamientos de API como list/watch. Valide la CA/CN del certificado de front-proxy, preserve el límite de confianza en torno a la identidad de usuario reenviada y configure la autorización delegada.

Inspeccione el descubrimiento instalado para conocer la versión real de API de metrics-server. No use como predeterminado un APIService v1.metrics.k8s.io inventado ni insecureSkipTLSVerify:true. El grupo/versión, Service y caBundle deben coincidir con el servidor real. Un simple controlador HTTP o grupo de API vacío no es un servidor de API de Kubernetes completo.

## Políticas y Webhooks de admisión

ValidatingAdmissionPolicy es estable desde Kubernetes 1.30 y ejecuta la validación CEL en proceso. Esta política/enlace limita las réplicas a 1–5 para las solicitudes de Deployments y deployments/scale en el namespace de producción. También verifica las actualizaciones de HPA y kubectl scale; alinee HPA maxReplicas con el límite. Los nombres de namespace no son equivalentes a etiquetas de entorno arbitrarias. Revise el impacto operativo antes de aplicar una política.

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

Los webhooks de validación permiten o deniegan solicitudes; los webhooks de mutación pueden devolver JSON Patch. Responda usando la misma versión de AdmissionReview y el UID de la solicitud. patchType es JSONPatch y los bytes de patch están codificados en Base64 en JSON.

Este controlador Go añade una etiqueta ilustrativa en Pod CREATE. Crea el mapa de labels cuando falta/es null, conserva las labels existentes y omite un patch cuando el valor ya coincide. Verifica el tamaño, el método, el tipo de contenido, la versión, el UID y las solicitudes/objetos null. Esta label no inserta realmente un sidecar.

### Código de Webhook probado

examples/platform/extensions/webhook contiene go.mod, esta implementación y sus pruebas. Solo utiliza las bibliotecas estándar de Go 1.25. Las structs declaran los campos consumidos de AdmissionReview e ignoran campos adicionales.

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

Las pruebas invocaron el controlador mediante httptest sin abrir un listener TLS. El Deployment aún requiere una imagen, Service, archivos de certificado/clave, el bundle de CA real, conectividad con el servidor de API, autenticación del llamador y política de red. Este servidor TLS no configura la autenticación de clientes de forma predeterminada. Haga coincidir los recursos, operaciones y rutas del webhook con el controlador.

Revise failurePolicy, timeoutSeconds, sideEffects/dryRun, reinvocationPolicy y los selectores. Fail puede bloquear solicitudes de API cuando un webhook no está disponible; Ignore puede omitir su comprobación. Declarar None debe reflejar la ausencia real de efectos secundarios externos.

La inyección actual por Pod de Istio usa la **label** sidecar.istio.io/inject; los namespaces usan labels istio-injection o de revisión. Verifique la ubicación de la label de la plantilla de Pod y las reglas de inyección específicas de la versión, en lugar de conservar como predeterminados ejemplos antiguos de annotation.

## Framework y Extenders de Scheduler

Los plugins de Framework se compilan y registran dentro de un binario de Scheduler. Nombrar CustomFilter en YAML no carga código ausente. Haga coincidir schedulerName del perfil con Pod spec.schedulerName para seleccionar un Scheduler independiente.

Filter elimina candidatos y Score clasifica los nodos viables. Considere NormalizeScore, los pesos de plugins y la selección en caso de empate. Reserve/Unreserve mantienen el estado de reserva del plugin, no una API de reserva permanente de capacidad. Permit puede permitir, rechazar o esperar; PreBind/Bind/PostBind gestionan las etapas de enlace.

El framework público de Kubernetes 1.36.2 utiliza CycleState/NodeInfo de k8s.io/kube-scheduler/framework y pasa NodeInfo a Score. No copie a ciegas firmas antiguas de nodeName-string/pointer; compile con la versión minor exacta. scheduler-plugins 0.35.7 no es automáticamente intercambiable con binarios 1.36/1.37.

Un extender expone endpoints HTTP(S) independientes. Configure únicamente los controladores filter/prioritize/bind implementados y admita Nodes frente a NodeNames según nodeCacheCapable. El ejemplo anterior configuraba bindVerb sin implementarlo. Gestione entradas nil, límites de cuerpo, tiempos de espera, TLS/autenticación, política de errores y rangos de puntuación. Para una selección simple de zona, considere primero la afinidad de nodos integrada.

## CNI

CNI es el contrato de ejecución del runtime/plugin de red. La biblioteca CNI 1.3.1 es distinta de la configuración cniVersion. Verifique las versiones compartidas de la especificación y el soporte de operaciones como ADD, DEL, CHECK, STATUS y GC.

Un ADD exitoso debe reflejar la interfaz de namespace, IPAM y configuración de rutas reales. Devolver una IP fija en JSON no crea una conexión y puede causar colisiones. DEL debe limpiar errores parciales o namespaces ausentes; CHECK debe inspeccionar el estado real. Copiar la misma subred host-local en varios nodos no proporciona IPAM de clúster.

Compruebe las versiones seleccionadas de Calico, Cilium o Flannel para conocer las funcionalidades y la compatibilidad con la distribución. El repositorio original de Weave Net está archivado y no se presenta como opción predeterminada para instalaciones nuevas. Esta auditoría no modificó redes de host, veth, rutas ni configuración de CNI.

## CSI

CSI 1.13.0 define los conjuntos y capacidades de RPC de Identity, Controller y Node. No todos los despliegues deben proporcionar los tres en un proceso. Los plugins solo de Node son posibles; las capacidades anunciadas deben coincidir con el comportamiento real de RPC.

CreateVolume debe gestionar idempotencia, rangos de capacidad, topología, ID de backend y errores. NodePublishVolume debe montar correctamente con los permisos solicitados/comportamiento de solo lectura; NodeUnpublish/Delete debe gestionar reintentos. Devolver siempre vol-123 o informar éxito sin montar no implementa un driver real.

Una StorageClass/PVC no es un despliegue de driver. El nombre del provisioner debe coincidir con un driver instalado y los parámetros son específicos del driver. Compruebe los sidecars de controller, registro/socket/montajes de host de Node, credenciales, topología, volumeBindingMode y reclaimPolicy. Siga la guía oficial de instalación/soporte para EBS, PD, Azure Disk o Ceph CSI.

## Verificación y referencias

Se leyeron las guías originales de 983 líneas en coreano y 987 líneas en inglés, ambos cuestionarios de 652 líneas y 36 bloques de código únicos. Las comprobaciones cubrieron seis casos de entrada de CRD, seis casos de CEL de políticas, 14 casos de webhook Go y cuatro aplicaciones reales de patch RFC6902. No se ejecutó ningún controller de clúster completo, servidor de API agregado, Scheduler ni driver CNI/CSI. El pseudocódigo explicativo no está etiquetado como una implementación probada.

- [CRD](https://kubernetes.io/docs/tasks/extend-kubernetes/custom-resources/custom-resource-definitions/)
- [Webhooks de admisión](https://kubernetes.io/docs/reference/access-authn-authz/extensible-admission-controllers/)
- [ValidatingAdmissionPolicy](https://kubernetes.io/docs/reference/access-authn-authz/validating-admission-policy/)
- [Agregación](https://kubernetes.io/docs/tasks/extend-kubernetes/configure-aggregation-layer/)
- [Framework de Scheduler](https://kubernetes.io/docs/concepts/scheduling-eviction/scheduling-framework/)
- [Framework 1.36.2](https://github.com/kubernetes/kubernetes/blob/v1.36.2/staging/src/k8s.io/kube-scheduler/framework/interface.go)
- [controller-runtime 0.25.0](https://github.com/kubernetes-sigs/controller-runtime/tree/v0.25.0)
- [Operator SDK](https://sdk.operatorframework.io/docs/installation/)
- [Código fuente de CNI 1.3.1](https://github.com/containernetworking/cni/blob/v1.3.1/SPEC.md)
- [CSI 1.13.0](https://github.com/container-storage-interface/spec/blob/v1.13.0/spec.md)
- [Inyección de Istio](https://istio.io/latest/docs/setup/additional-setup/sidecar-injection/)

[Cuestionario de mecanismos de extensión](../quizzes/platform-engineering/04-kubernetes-extensions-quiz.md)
