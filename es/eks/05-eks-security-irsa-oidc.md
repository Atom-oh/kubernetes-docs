# IRSA y el proveedor OIDC

> **Última actualización**: 21 de noviembre de 2026

Esta página desarrolla en detalle la sección «Análisis profundo del proveedor OIDC» de [Seguridad de Amazon EKS](./05-eks-security.md). Explica cómo se relaciona el emisor OIDC del clúster con un proveedor OIDC de IAM, cómo un token de IRSA se convierte en credenciales temporales mediante STS, cómo inspeccionar los documentos de descubrimiento y JWKS, y presenta un ejemplo de un rol de IRSA con permisos delimitados y un Job. Los ejemplos usan el espacio de nombres `security-demo`, preparado en la página de [acceso al clúster](./05-eks-security-cluster-access.md#access-entries-and-namespace-authorization). También encontrarás un diagrama paso a paso del flujo de IRSA en [Cómo funciona IRSA](../security/17-eks-workload-identity-migration.md#irsa-flow).

## Tabla de contenido

1. [Emisor OIDC y proveedor OIDC de IAM](#oidc-issuer-and-iam-oidc-provider)
2. [Token de IRSA e intercambio de roles](#irsa-token-and-role-exchange)
3. [Descubrimiento e inspección de JWKS](#discovery-and-jwks-inspection)
4. [Ejemplo de IRSA con permisos delimitados](#a-scoped-irsa-example)

## Emisor OIDC y proveedor OIDC de IAM

EKS publica un emisor OIDC del clúster y claves públicas de firma. Ese endpoint por sí solo no crea un proveedor OIDC de IAM ni autoriza a asumir un rol. Para IRSA, la cuenta del rol debe tener el proveedor OIDC de IAM previsto; el rol debe confiar en él con las condiciones correctas de emisor, sujeto y audiencia; y la carga de trabajo debe usar un SDK compatible.

![Diagrama de secuencia que muestra cómo un Pod intercambia su JWT proyectado de cuenta de servicio de Kubernetes con AWS STS mediante AssumeRoleWithWebIdentity; STS valida el token con JWKS del proveedor OIDC de EKS y la política de confianza del rol de IAM, y luego devuelve credenciales temporales que el Pod usa para llamar a un servicio de AWS.](../.gitbook/assets/en-eks-05-eks-security-3.png)

[🔍 Ver el diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-05-eks-security-3.html)

## Token de IRSA e intercambio de roles

El webhook de IRSA añade a un Pod apto una configuración de token proyectado y rol. El SDK intercambia el token de identidad web con STS mediante AssumeRoleWithWebIdentity. STS valida el emisor, la firma, el token y la confianza del rol, y luego devuelve credenciales temporales de AWS. La aplicación usa esas credenciales para las operaciones de AWS que tiene permitidas. Kubernetes rota el token proyectado; el SDK renueva las credenciales de AWS. Son ciclos de vida distintos.

Esto es una **estructura ilustrativa de la carga útil decodificada**, con marcas de tiempo deliberadamente antiguas o vencidas e identidades de ejemplo. No es un token firmado ni una prueba de autenticación. La audiencia de STS corresponde a la ruta de IRSA; Pod Identity usa una audiencia distinta:

```json
{
  "aud": [
    "sts.amazonaws.com"
  ],
  "exp": 1234567890,
  "iat": 1234567800,
  "iss": "https://oidc.eks.us-west-2.amazonaws.com/id/REPLACE_WITH_CLUSTER_ISSUER_ID",
  "kubernetes.io": {
    "namespace": "security-demo",
    "pod": {
      "name": "irsa-read-check-example",
      "uid": "example-pod-uid"
    },
    "serviceaccount": {
      "name": "irsa-reader",
      "uid": "example-serviceaccount-uid"
    }
  },
  "sub": "system:serviceaccount:security-demo:irsa-reader"
}
```

Valida el emisor, la audiencia, la fecha de vencimiento y el sujeto esperado; no te limites a comprobar si se puede decodificar el JSON. No incluyas tokens sin procesar, claves de acceso secretas de AWS ni tokens de sesión en ejemplos o registros. Un rol puede confiar en varias cuentas de servicio o emisores permitidos explícitamente; IRSA no exige exactamente un rol por ServiceAccount.

## Descubrimiento e inspección de JWKS

Usa el emisor devuelto para el clúster real. Este diagnóstico obtiene los documentos públicos de descubrimiento y JWKS, y comprueba el emisor indicado en el documento de descubrimiento y el esquema HTTPS. No valida un token de una carga de trabajo ni los permisos de IAM:

```bash
set -euo pipefail
: "${CLUSTER_NAME:?Set the verified cluster}"
: "${AWS_REGION:?Set its Region}"
OIDC_URL=$(aws eks describe-cluster --name "$CLUSTER_NAME" --region "$AWS_REGION" \
  --query cluster.identity.oidc.issuer --output text)
case "$OIDC_URL" in https://*) ;; *) echo "Unexpected issuer URL"; exit 1 ;; esac
curl --fail --silent --show-error --proto '=https' --connect-timeout 5 --max-time 20 \
  "${OIDC_URL%/}/.well-known/openid-configuration" > oidc-discovery.json
JWKS_URI=$(python3 - "$OIDC_URL" <<'PY'
import json, sys, urllib.parse
with open("oidc-discovery.json") as stream:
    doc = json.load(stream)
if doc["issuer"] != sys.argv[1]:
    raise SystemExit("Discovery issuer does not match the cluster issuer")
uri = doc["jwks_uri"]
parsed = urllib.parse.urlparse(uri)
if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
    raise SystemExit("JWKS must be an HTTPS URL without embedded credentials")
print(uri)
PY
)
curl --fail --silent --show-error --proto '=https' --connect-timeout 5 --max-time 20 \
  "$JWKS_URI" > oidc-jwks.json
python3 - <<'PY'
import json
with open("oidc-jwks.json") as stream:
    keys = json.load(stream).get("keys")
if not isinstance(keys, list) or not keys or not all(isinstance(k, dict) and "kty" in k for k in keys):
    raise SystemExit("Unexpected JWKS response")
print("Fetched", len(keys), "public keys; no token signature was validated")
PY
```

Los validadores automatizados deben almacenar las claves en caché según Cache-Control y gestionar la rotación de claves de firma y los valores de `kid` desconocidos mediante una biblioteca JWT revisada. EKS rota su clave de firma OIDC cada siete días. Actualmente, EKS también admite un endpoint de interfaz de PrivateLink para el descubrimiento OIDC/JWKS del clúster, `com.amazonaws.region-code.oidc-eks`, para validadores sin salida a Internet. Verifica los requisitos de región y DNS de ese endpoint; un endpoint de la API de administración de EKS es un servicio distinto.

## Ejemplo de IRSA con permisos delimitados

Prepara el proveedor OIDC de IAM, el rol y el bucket con sus respectivos propietarios. Sustituye de forma coherente la cuenta, el nombre de host y la ruta completos del emisor, y el ARN del rol; los clústeres IPv6 pueden usar el nombre de host del emisor de doble pila. Este ejemplo vincula únicamente `security-demo/irsa-reader` y la audiencia de STS; es un ejemplo de una nueva política de confianza para un rol, no un reemplazo de las demás declaraciones de confianza de un rol existente:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Federated": "arn:aws:iam::111122223333:oidc-provider/oidc.eks.us-west-2.amazonaws.com/id/REPLACE_WITH_CLUSTER_ISSUER_ID"
      },
      "Action": "sts:AssumeRoleWithWebIdentity",
      "Condition": {
        "StringEquals": {
          "oidc.eks.us-west-2.amazonaws.com/id/REPLACE_WITH_CLUSTER_ISSUER_ID:sub": "system:serviceaccount:security-demo:irsa-reader",
          "oidc.eks.us-west-2.amazonaws.com/id/REPLACE_WITH_CLUSTER_ISSUER_ID:aud": "sts.amazonaws.com"
        }
      }
    }
  ]
}
```

La política de lectura permite acceder a un prefijo específico del bucket. Añade únicamente los permisos de KMS necesarios cuando los objetos usen una clave de cifrado administrada por el cliente, y revisa las políticas del bucket y del endpoint. Para este ejemplo limitado a un prefijo no hace falta una política AmazonS3ReadOnlyAccess para toda la cuenta:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:ListBucket"
      ],
      "Resource": "arn:aws:s3:::replace-with-owned-security-bucket",
      "Condition": {
        "StringLike": {
          "s3:prefix": [
            "security-demo/",
            "security-demo/*"
          ]
        }
      }
    },
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject"
      ],
      "Resource": "arn:aws:s3:::replace-with-owned-security-bucket/security-demo/*"
    }
  ]
}
```

Después de preparar el [espacio de nombres `security-demo`](./05-eks-security-cluster-access.md#access-entries-and-namespace-authorization) y el rol, crea la ServiceAccount y el Job de listado acotado que se muestran a continuación. La imagen oficial de AWS CLI incluye el cliente; una imagen arbitraria de amazonlinux:2 no lo garantiza. Sustituye los valores del bucket, la región y el rol. El Job lista un prefijo sin imprimir valores secretos; que esta operación se complete correctamente no demuestra que la aplicación tenga todos los permisos de GetObject/KMS.

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: irsa-reader
  namespace: security-demo
  annotations:
    eks.amazonaws.com/role-arn: arn:aws:iam::111122223333:role/SecurityDemoIRSAReader
---
apiVersion: batch/v1
kind: Job
metadata:
  name: irsa-read-check
  namespace: security-demo
spec:
  backoffLimit: 0
  activeDeadlineSeconds: 120
  template:
    spec:
      serviceAccountName: irsa-reader
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

## Referencias

- [IRSA de EKS](https://docs.aws.amazon.com/eks/latest/userguide/iam-roles-for-service-accounts.html)
- [Versiones mínimas del SDK para IRSA](https://docs.aws.amazon.com/eks/latest/userguide/iam-roles-for-service-accounts-minimum-sdk.html)
- [Migrar los permisos de IAM de los nodos de EKS a IRSA y Pod Identity](../security/17-eks-workload-identity-migration.md)

## Próximos pasos

- Anterior: [Autenticación de acceso al clúster de EKS: IAM y entradas de acceso](./05-eks-security-cluster-access.md)
- Siguiente: [Pod Identity de EKS](./05-eks-security-pod-identity.md)
- Volver a la descripción general: [Seguridad de Amazon EKS](./05-eks-security.md)

## Cuestionario

Para comprobar lo que aprendiste en este capítulo, prueba el [cuestionario sobre el tema](../quizzes/eks/05-eks-security-irsa-oidc-quiz.md).
