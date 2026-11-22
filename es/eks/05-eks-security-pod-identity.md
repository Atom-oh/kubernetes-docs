# Identidad de Pod en EKS

> **Última actualización**: 21 de noviembre de 2026

Esta página desarrolla por separado la sección «Identidad de Pod en EKS» de [Seguridad de Amazon EKS](./05-eks-security.md). Es una referencia de configuración para el agente de identidad de Pod y el flujo de credenciales, la preparación de la relación de confianza y la asociación del rol, y las consideraciones sobre cuentas cruzadas y caché. El cuaderno [Migrar los permisos de IAM de los nodos de EKS a IRSA y a la identidad de Pod](../security/17-eks-workload-identity-migration.md) es la referencia para comparar con IRSA, el orden de migración en producción y la demostración en directo; por eso, esta página solo los resume y enlaza.

## Tabla de contenido

1. [Qué proporciona la identidad de Pod](#what-pod-identity-provides)
2. [Comparación con IRSA](#comparison-with-irsa)
3. [Agente y flujo de credenciales](#agent-and-credential-flow)
4. [Preparación del rol y la asociación](#prepared-role-and-association)
5. [Consideraciones sobre cuentas cruzadas y caché](#cross-account-and-cache-considerations)
6. [Procedimiento de migración de IRSA a la identidad de Pod](#irsa-to-pod-identity-migration-procedure)

## Qué proporciona la identidad de Pod

La identidad de Pod de EKS proporciona credenciales temporales de AWS mediante el proveedor de credenciales de contenedor del SDK y EKS Auth. Una asociación de identidad de Pod asigna un clúster/espacio de nombres/ServiceAccount a un rol de IAM; no crea el ServiceAccount ni concede permisos de RBAC de Kubernetes.

## Comparación con IRSA

La tabla del cuaderno [Comparación entre IRSA y la identidad de Pod](../security/17-eks-workload-identity-migration.md#irsa-and-pod-identity-compared) es la referencia para conocer las diferencias entre ambos mecanismos (configuración por clúster, política de confianza, límites de escala, cuentas cruzadas y separación de funciones). Ten en cuenta estas diferencias al consultar los ejemplos de configuración de esta página:

- **Confianza y vinculación**: IRSA utiliza un proveedor OIDC de IAM con condiciones de confianza de emisor/sujeto/audiencia; la identidad de Pod utiliza la confianza del rol `pods.eks.amazonaws.com` y una asociación de la API de EKS.
- **Ruta de las credenciales**: con IRSA, el SDK intercambia un token de identidad web con STS ([Cómo funciona IRSA](../security/17-eks-workload-identity-migration.md#irsa-flow)); con la identidad de Pod, el SDK llama al punto de conexión de credenciales de contenedor del agente del nodo, que obtiene las credenciales de EKS Auth ([Cómo funciona la identidad de Pod de EKS](../security/17-eks-workload-identity-migration.md#pod-identity-flow)).
- **Etiquetas de sesión**: las etiquetas de sesión de Kubernetes de la identidad de Pod están habilitadas de forma predeterminada y se pueden deshabilitar intencionalmente. Las etiquetas de sesión identifican la sesión del rol asumido; no etiquetan automáticamente todos los recursos de AWS que crea una aplicación.

Una configuración más sencilla no elimina los requisitos de validación de IAM, de red, del SDK ni de la aplicación.

## Agente y flujo de credenciales

<!-- Diagram repair pending: SDK calls container credential endpoint; agent calls EKS Auth AssumeRoleForPodIdentity, not STS directly or arbitrary request interception.
![Architecture diagram of the six-step EKS Pod Identity flow in which a pod's credential request is intercepted by the node's Pod Identity Agent DaemonSet, the agent checks the Pod Identity Association that maps the service account to an IAM role, calls AssumeRoleForPodIdentity to obtain temporary credentials from AWS STS, and delivers them back to the pod.](../.gitbook/assets/en-eks-05-eks-security-4.png)

[🔍 View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-05-eks-security-4.html)
-->

Para un Pod recién creado que tenga una asociación, EKS inyecta un token con la audiencia `pods.eks.amazonaws.com`, una variable de entorno con la ruta al archivo del token y un URI de credenciales de contenedor. El SDK llama al punto de conexión del agente, que suele ser `169.254.170.23/v1/credentials`. El agente llama a **AssumeRoleForPodIdentity en EKS Auth** y pone las credenciales devueltas a disposición del SDK. No es un interceptor transparente de todas las solicitudes de la aplicación, que sigue llamando directamente a los servicios de AWS con sus credenciales. Encontrarás un diagrama paso a paso del flujo en [Cómo funciona la identidad de Pod de EKS](../security/17-eks-workload-identity-migration.md#pod-identity-flow).

Los nodos EC2 estándar compatibles utilizan el complemento/DaemonSet del agente de identidad de Pod. Auto Mode proporciona esta capacidad como parte de sus nodos administrados. Los nodos híbridos la admiten con la configuración documentada del sistema operativo, el agente y las credenciales del nodo (`spec.hybrid.enableCredentialsFile: true` en la configuración `nodeadm` del nodo y `daemonsets.hybrid.create` en el complemento del agente, con ajustes independientes para Bottlerocket; consulta [Ubicación de los complementos y la identidad de Pod en nodos híbridos](../eks-hybrid-nodes/04-node-bootstrap.md#add-on-placement-and-pod-identity)); no reutilices a ciegas una configuración estándar del agente para EC2. EKS Fargate no admite esta ruta del agente de identidad de Pod; tampoco la admiten los nodos de Windows, Outposts ni EKS Anywhere. Verifica la compatibilidad real del cómputo y los permisos/acceso de red del nodo para EKS Auth.

## Preparación del rol y la asociación

Para una instalación estándar con agente administrado, consulta con el responsable la versión real del clúster y el catálogo de complementos compatibles. No fijes en el código la versión antigua v1.0.0 ni instales un agente duplicado sobre Auto Mode u otro administrador:

```bash
set -euo pipefail
: "${CLUSTER_NAME:?Set the existing cluster}"
: "${AWS_REGION:?Set its Region}"
EKS_VERSION=$(aws eks describe-cluster --name "$CLUSTER_NAME" --region "$AWS_REGION" \
  --query cluster.version --output text)
aws eks describe-addon-versions --addon-name eks-pod-identity-agent \
  --kubernetes-version "$EKS_VERSION" --region "$AWS_REGION" --output json
```

Prepara un rol de IAM en la misma cuenta con la [política de lectura de S3 de alcance limitado del ejemplo de IRSA](./05-eks-security-irsa-oidc.md#a-scoped-irsa-example) y esta relación de confianza. Sustituye conjuntamente los valores de cuenta y clúster. Este ejemplo utiliza las etiquetas de sesión predeterminadas; si las deshabilitas, tendrás que revisar estas condiciones. Quien realice la llamada necesita los permisos adecuados para la asociación y `iam:PassRole` para el rol previsto:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "pods.eks.amazonaws.com"
      },
      "Action": [
        "sts:AssumeRole",
        "sts:TagSession"
      ],
      "Condition": {
        "StringEquals": {
          "aws:RequestTag/eks-cluster-arn": "arn:aws:eks:us-west-2:111122223333:cluster/my-cluster",
          "aws:RequestTag/kubernetes-namespace": "security-demo",
          "aws:RequestTag/kubernetes-service-account": "podid-reader"
        }
      }
    }
  ]
}
```

El siguiente ejemplo de asociación nueva se niega a sobrescribir una asociación existente. No crea el rol de IAM, no instala el agente ni crea una cuenta de Kubernetes:

```bash
set -euo pipefail
: "${CLUSTER_NAME:?Set the verified cluster}"
: "${AWS_REGION:?Set its Region}"
: "${POD_ID_ROLE_ARN:?Set the prepared same-account role matching the trust example}"
aws eks list-pod-identity-associations --cluster-name "$CLUSTER_NAME" --region "$AWS_REGION" \
  --namespace security-demo --service-account podid-reader --output json > podid-associations-before.json
python3 - <<'PY'
import json
with open("podid-associations-before.json") as stream:
    existing = json.load(stream)["associations"]
if existing:
    raise SystemExit("Association exists; review its owner/configuration before changing it")
PY
aws eks create-pod-identity-association --cluster-name "$CLUSTER_NAME" --region "$AWS_REGION" \
  --namespace security-demo --service-account podid-reader --role-arn "$POD_ID_ROLE_ARN"
```

Una vez propagada la asociación, crea el ServiceAccount y un Job de prueba nuevo y acotado. La confianza del rol de IAM, el espacio de nombres, el nombre de la cuenta y el prefijo del bucket deben coincidir. Puede que tengas que recrear un Pod creado antes de la asociación para que reciba la configuración inyectada. Comprueba qué proveedor se seleccionó realmente y valida permisos representativos; no imprimas archivos de credenciales ni de tokens.

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: podid-reader
  namespace: security-demo
---
apiVersion: batch/v1
kind: Job
metadata:
  name: podid-read-check
  namespace: security-demo
spec:
  backoffLimit: 0
  activeDeadlineSeconds: 120
  template:
    spec:
      serviceAccountName: podid-reader
      restartPolicy: Never
      securityContext:
        runAsNonRoot: true
        runAsUser: 1000
        runAsGroup: 1000
        fsGroup: 1000
        seccompProfile:
          type: RuntimeDefault
      containers:
      - name: reader
        image: public.ecr.aws/aws-cli/aws-cli:2.36.43
        command:
        - aws
        args:
        - s3api
        - list-objects-v2
        - --bucket
        - replace-with-owned-security-bucket
        - --prefix
        - security-demo/
        - --max-items
        - '5'
        env:
        - name: AWS_REGION
          value: us-west-2
        - name: AWS_EC2_METADATA_DISABLED
          value: 'true'
        securityContext:
          allowPrivilegeEscalation: false
          readOnlyRootFilesystem: true
          capabilities:
            drop:
            - ALL
        resources:
          requests:
            cpu: 100m
            memory: 128Mi
          limits:
            cpu: 500m
            memory: 256Mi
        volumeMounts:
        - name: private-home
          mountPath: /root
        - name: tmp
          mountPath: /tmp
      volumes:
      - name: private-home
        emptyDir: {}
      - name: tmp
        emptyDir: {}
      nodeSelector:
        kubernetes.io/os: linux
```

![Diagrama de arquitectura que muestra dos espacios de nombres, cada uno con un ServiceAccount asociado a su propio rol de IAM, mientras que los Pods de ambos espacios solicitan credenciales a un agente de identidad de Pod y un servicio de identidad de Pod compartidos antes de acceder a los servicios de AWS.](../.gitbook/assets/en-eks-05-eks-security-5.png)

[🔍 Ver el diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-05-eks-security-5.html)

## Consideraciones sobre cuentas cruzadas y caché

El rol de asociación debe estar en la cuenta del clúster de EKS. Se puede usar un rol de IAM de destino opcional en otra cuenta; la identidad de Pod encadena el rol de la misma cuenta con ese rol de destino, con la confianza y los permisos para asumir el rol configurados en ambos. Esto no permite asociar directamente como rol de asociación cualquier rol de otra cuenta.

La guía actual para el rol de destino documenta que las credenciales almacenadas en caché duran 6 horas sin un rol de destino y 59 minutos con uno. Los cambios en la asociación no reinician esa caché; recrear los Pods permite obtener antes la nueva configuración. Comprueba el comportamiento real de actualización y revocación en la aplicación. La opción más reciente de política de sesión de asociación requiere que las etiquetas de sesión estén deshabilitadas y restringe el rol de destino cuando se configura uno; no la combines sin revisión con condiciones de confianza que exijan esas etiquetas.

## Procedimiento de migración de IRSA a la identidad de Pod

Sigue el [Orden de migración para clústeres de producción](../security/17-eks-workload-identity-migration.md#migration-order-for-production-clusters) del cuaderno para conocer los pasos y los comandos de canario, y consulta su [demostración en directo](../security/17-eks-workload-identity-migration.md#live-demo) para ver una migración medida de tres réplicas de una aplicación. Esta página solo recoge los aspectos que debes observar antes de migrar.

Antes de preparar una migración, conserva la configuración actual de confianza de IRSA y del ServiceAccount. Si sustituyes la confianza del rol por el principal de servicio de identidad de Pod únicamente, puedes interrumpir a los consumidores existentes cuando actualicen sus credenciales. Lo siguiente solo registra la configuración:

```bash
set -euo pipefail
: "${IRSA_ROLE_NAME:?Set the existing role whose trust must be preserved}"
: "${WORKLOAD_NAMESPACE:?Set the workload namespace}"
: "${SERVICE_ACCOUNT:?Set the existing application ServiceAccount}"
aws iam get-role --role-name "$IRSA_ROLE_NAME" \
  --query Role.AssumeRolePolicyDocument --output json > irsa-trust-before.json
kubectl -n "$WORKLOAD_NAMESPACE" get serviceaccount "$SERVICE_ACCOUNT" \
  -o yaml > irsa-serviceaccount-before.yaml
```

- Primero, verifica la compatibilidad real del cómputo, un SDK/proveedor de credenciales de contenedor compatible, el agente de identidad de Pod o la capacidad integrada, y los permisos del rol de IAM preparado.
- Incorpora la declaración de confianza de identidad de Pod, ya revisada, a la política de confianza existente a través de su responsable; conserva las condiciones de emisor, sujeto y audiencia de IRSA y las demás declaraciones válidas no relacionadas hasta que todos los consumidores hayan migrado.
- Cuando un ServiceAccount tiene tanto una anotación de IRSA como una asociación, EKS inyecta solo las variables de identidad de Pod en los **Pods nuevos**, no las de IRSA. Los Pods en ejecución conservan sus variables de IRSA hasta que se recrean, así que haz el cambio mediante un despliegue controlado y elimina después la anotación que ya no se utilice. Como una asociación en el ServiceAccount de producción cambia todos los Pods nuevos que lo usan, valida primero con un canario en un ServiceAccount independiente y no elimines la anotación de IRSA de producción ni reinicies el Deployment de producción antes de hacerlo.
- Una respuesta correcta de `get-caller-identity` que muestre el mismo rol de IAM no basta por sí sola para distinguir IRSA de la identidad de Pod. Sin imprimir tokens ni valores secretos, comprueba los nombres de las variables de entorno inyectadas en el Pod nuevo y el acceso previsto a AWS, y asegúrate de que no siga en uso ningún proveedor anterior de la cadena del SDK, como las credenciales explícitas.
- Mantén una ruta de reversión probada para la configuración de la carga de trabajo. Elimina la confianza antigua de IRSA solo después de inventariar a todos los consumidores restantes y verificar que la migración se ha completado.

## Referencias

- [Identidad de Pod de EKS](https://docs.aws.amazon.com/eks/latest/userguide/pod-identities.html)
- [Cómo funciona la identidad de Pod](https://docs.aws.amazon.com/eks/latest/userguide/pod-id-how-it-works.html)
- [Complementos híbridos e identidad de Pod](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-add-ons.html)
- [Migrar los permisos de IAM de los nodos de EKS a IRSA y a la identidad de Pod](../security/17-eks-workload-identity-migration.md)

## Pasos siguientes

- Anterior: [IRSA y el proveedor OIDC](./05-eks-security-irsa-oidc.md)
- Siguiente: [Seguridad de Amazon EKS: control de acceso al punto de conexión del clúster](./05-eks-security.md#cluster-endpoint-access-control)
- Relacionado: [Autenticación de acceso al clúster de EKS: IAM y entradas de acceso](./05-eks-security-cluster-access.md)
- Volver a la descripción general: [Seguridad de Amazon EKS](./05-eks-security.md)

## Cuestionario

Para poner a prueba lo aprendido en este capítulo, prueba el [cuestionario sobre el tema](../quizzes/eks/05-eks-security-pod-identity-quiz.md).
