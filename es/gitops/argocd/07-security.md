# Seguridad de Argo CD

> **Versiones revisadas**: Argo CD 3.5.2, Sealed Secrets 0.40.0/chart 2.20.0, ESO 2.10.0 (actualizado a 2.12.0 tras revisar las notas de la versión; los ejemplos no se volvieron a ejecutar), AVP 1.18.1, KSOPS 4.5.1, SOPS 3.13.3
> **Última actualización**: 16 de octubre de 2026

## Índice
- [Integración de SSO](#sso-integration)
- [Gestión de Secrets](#secret-management)
- [Configuración de TLS](#tls-configuration)
- [Registro de auditoría](#audit-logging)
- [Seguridad de red](#network-security)
- [Credenciales de repositorio](#repository-credentials)
- [Verificación de firmas GPG](#gpg-signature-verification)

## Integración de SSO {#sso-integration}

Los ejemplos de SSO son alternativas. Incorpore los campos necesarios a los ConfigMaps y Secrets existentes sin sustituir las claves de firma del servidor ni las demás credenciales de argocd-secret. Reemplace los marcadores por la configuración real del proveedor de identidad (IdP) y suministre los secretos mediante gestión externa de Secrets o archivos protegidos. El YAML de Secret siguiente solo muestra la estructura; no incorpore sus valores sin cifrar a Git.

Argo CD admite varios proveedores de SSO para la autenticación.

### Configuración de OIDC

Configuración genérica de OIDC en `argocd-cm`:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: argocd-cm
  namespace: argocd
data:
  url: https://argocd.example.com

  oidc.config: |
    name: OIDC
    issuer: https://auth.example.com
    clientID: argocd
    clientSecret: $oidc.clientSecret
    requestedScopes:
      - openid
      - profile
      - email
      - groups
    requestedIDTokenClaims:
      groups:
        essential: true
```

Almacene el secreto del cliente:

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: argocd-secret
  namespace: argocd
type: Opaque
stringData:
  oidc.clientSecret: <your-client-secret>
```

### Integración con Okta

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: argocd-cm
  namespace: argocd
data:
  url: https://argocd.example.com

  oidc.config: |
    name: Okta
    issuer: https://dev-123456.okta.com
    clientID: 0oa1234567890abcdef
    clientSecret: $oidc.okta.clientSecret
    requestedScopes:
      - openid
      - profile
      - email
      - groups
    requestedIDTokenClaims:
      groups:
        essential: true
```

Configuración de la aplicación en Okta:
1. Cree una aplicación OIDC nueva en Okta.
2. Establezca la URI de redirección del inicio de sesión en `https://argocd.example.com/auth/callback`.
3. Active el alcance "groups".
4. Añada el claim de grupos al token de identidad.

### Integración con Microsoft Entra ID

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: argocd-cm
  namespace: argocd
data:
  url: https://argocd.example.com
  oidc.config: |
    name: Microsoft Entra ID
    issuer: https://login.microsoftonline.com/<tenant-id>/v2.0
    clientID: <application-id>
    clientSecret: $oidc.azure.clientSecret
    requestedScopes:
    - openid
    - profile
    - email
    requestedIDTokenClaims:
      groups:
        essential: true
```

Configuración de Microsoft Entra ID:
1. Registre una aplicación nueva en Azure AD.
2. Establezca la URI de redirección en `https://argocd.example.com/auth/callback`.
3. Añada los permisos de API `openid`, `profile` y `email`.
4. Configure el claim de grupos en Token configuration.

### AWS IAM Identity Center (AWS SSO)

Cree una aplicación SAML personalizada en IAM Identity Center, asigne el acceso y configure el ACS y la audiencia para /api/dex/callback. Un emisor inventado de identitycenter.amazonaws.com no constituye una integración OIDC genérica. Asigne el atributo de correo electrónico y utilice la URL de inicio de sesión y el certificado de firma de los metadatos. No dé por hecho que existe una asignación dinámica oficial del atributo de grupos: inspeccione la aserción real. Este ejemplo utiliza el claim de correo electrónico.

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: argocd-cm
  namespace: argocd
data:
  url: https://argocd.example.com
  dex.config: |
    connectors:
    - type: saml
      id: identity-center
      name: AWS IAM Identity Center
      config:
        ssoURL: https://portal.sso.ap-northeast-2.amazonaws.com/saml/assertion/APP_ID
        caData: BASE64_OF_THE_COMPLETE_IDP_SIGNING_CERTIFICATE_PEM
        entityIssuer: https://argocd.example.com/api/dex/callback
        redirectURI: https://argocd.example.com/api/dex/callback
        usernameAttr: email
        emailAttr: email
```

Incorpore este fragmento de datos RBAC con una dirección de correo real y aprobada y con el rol viewer restringido definido en el capítulo de RBAC.

```yaml
data:
  scopes: '[groups, email]'
  policy.identity-center.csv: |
    g, approved.user@example.com, role:viewer
```

### Integración de LDAP mediante Dex

Para LDAP o Active Directory, utilice Dex como intermediario de identidad:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: argocd-cm
  namespace: argocd
data:
  url: https://argocd.example.com
  dex.config: |
    connectors:
    - type: ldap
      name: Active Directory
      id: ad
      config:
        host: ldap.example.com:636
        insecureNoSSL: false
        insecureSkipVerify: false
        bindDN: cn=argocd-reader,ou=Service Accounts,dc=example,dc=com
        bindPW: $dex.ldap.bindPW
        usernamePrompt: Username
        userSearch:
          baseDN: ou=Users,dc=example,dc=com
          filter: (objectClass=person)
          username: sAMAccountName
          idAttr: sAMAccountName
          emailAttr: mail
          nameAttr: displayName
        groupSearch:
          baseDN: ou=Groups,dc=example,dc=com
          filter: (objectClass=group)
          userMatchers:
          - userAttr: DN
            groupAttr: member
          nameAttr: cn
        rootCA: /etc/dex/ldap-ca/ca.crt
```

Proporcione un ca.crt verificado en el ConfigMap ldap-ca e incorpore estos valores de Helm a la configuración existente. Suministre bindPW mediante la clave dex.ldap.bindPW de argocd-secret, utilizando una cuenta de directorio que solo tenga los permisos de búsqueda necesarios.

```yaml
dex:
  volumes:
  - name: ldap-ca
    configMap:
      name: ldap-ca
  volumeMounts:
  - name: ldap-ca
    mountPath: /etc/dex/ldap-ca
    readOnly: true
```

### Integración de SAML

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: argocd-cm
  namespace: argocd
data:
  url: https://argocd.example.com
  dex.config: |
    connectors:
    - type: saml
      id: saml
      name: SAML Provider
      config:
        ssoURL: https://idp.example.com/sso/saml
        caData: BASE64_OF_THE_COMPLETE_IDP_SIGNING_CERTIFICATE_PEM
        redirectURI: https://argocd.example.com/api/dex/callback
        usernameAttr: name
        emailAttr: email
        groupsAttr: groups
        entityIssuer: https://argocd.example.com/api/dex/callback
```

### Asignación de grupos de SSO a RBAC

Incorpore estas vinculaciones junto con las definiciones de roles personalizados del capítulo de Projects y RBAC. developer y viewer no son roles integrados.

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: argocd-rbac-cm
  namespace: argocd
data:
  policy.security-sso.csv: |
    # Map SSO groups to ArgoCD roles
    g, ArgoCD-Admins, role:admin
    g, ArgoCD-Developers, role:developer
    g, ArgoCD-Viewers, role:viewer

    # Azure AD group IDs
    g, 12345678-1234-1234-1234-123456789012, role:admin

    # Okta groups
    g, argocd-admins, role:admin
  scopes: '[groups]'
```

## Gestión de Secrets {#secret-management}

Codificar en Base64 un manifiesto de Secret guardado en Git no lo cifra. Para entornos nuevos, es preferible crear los Secrets en el clúster de destino mediante ESO o Sealed Secrets. Inyectar valores con AVP o KSOPS al generar manifiestos puede exponerlos sin cifrar en el repo-server y en las cachés de manifiestos de Redis; este método exige un modelo de confianza distinto.

### Sealed Secrets

El ejemplo utiliza el controlador 0.40.0 y el chart 2.20.0. En la revisión documentada, la antigua URL de Helm de bitnami-labs devolvía 404; utilice el repositorio de bitnami. Instale el binario kubeseal correspondiente y compruebe las sumas publicadas en la [versión oficial](https://github.com/bitnami/sealed-secrets/releases/tag/v0.40.0). Los administradores de la plataforma deben crear previamente el namespace de destino.

```bash
helm repo add sealed-secrets https://bitnami.github.io/sealed-secrets
helm repo update sealed-secrets
helm upgrade --install sealed-secrets sealed-secrets/sealed-secrets \
  --version 2.20.0 --namespace kube-system \
  --set fullnameOverride=sealed-secrets-controller --wait --timeout 5m
kubeseal --version  # use 0.40.0 for this example
```

Compruebe que el kubeconfig actual apunta al clúster previsto y obtenga el certificado público de su controlador. El ámbito strict predeterminado vincula el contenido cifrado al nombre y al namespace del Secret; no lo renombre ni lo mueva después de cifrarlo. El procedimiento lee la contraseña de un archivo protegido para evitar incluirla en Git o en los argumentos de comandos.

```bash
set -euo pipefail
umask 077
: "${SECRET_INPUT_FILE:?Provide a protected password file outside Git}"
seal_dir="$(mktemp -d)"
trap 'rm -rf "$seal_dir"' EXIT
kubeseal --controller-name sealed-secrets-controller \
  --controller-namespace kube-system --fetch-cert > "$seal_dir/controller.pem"
kubectl create secret generic my-secret --namespace my-app \
  --from-file=password="$SECRET_INPUT_FILE" --dry-run=client -o yaml \
  | kubeseal --format yaml --cert "$seal_dir/controller.pem" > sealed-secret.yaml
test -s sealed-secret.yaml
```

Revise e incorpore a Git únicamente el SealedSecret generado. Un ejemplo abreviado Ag... no es contenido cifrado utilizable. La copia de seguridad y la recuperación de las claves del controlador son operaciones administrativas que deben protegerse. Renovar las claves de sellado no rota por sí solo el secreto de la aplicación.

### External Secrets Operator

ESO sincroniza valores de secretos externos con Secrets del clúster de destino; no cifra valores sin proteger que estén en Git. Los ejemplos de la versión 2.12.0 utilizan external-secrets.io/v1. La configuración jwt.serviceAccountRef de AWS siguiente utiliza IRSA: prepare el ServiceAccount de ese namespace, la anotación del rol de IAM y la relación de confianza OIDC. Pod Identity utiliza, en su lugar, la asociación del ServiceAccount del controlador y la cadena de credenciales del SDK.

Sincronice secretos desde proveedores externos:

```bash
# Install External Secrets Operator
helm repo add external-secrets https://charts.external-secrets.io
helm upgrade --install external-secrets external-secrets/external-secrets \
  --version 2.12.0 --namespace external-secrets --create-namespace --wait --timeout 5m
```

En el ejemplo de ServiceAccount para IRSA, configure el ARN real del rol y la confianza OIDC. Permita GetSecretValue y DescribeSecret únicamente sobre los ARN necesarios y KMS Decrypt cuando corresponda. Para Vault, vincule su rol a este ServiceAccount y namespace, con audience=vault, una política KV restringida y una configuración adecuada para revisar tokens. Vault 1.21+ exige audiencias en los roles.

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: external-secrets-sa
  namespace: my-app
  annotations:
    eks.amazonaws.com/role-arn: arn:aws:iam::123456789012:role/eso-my-app-reader
automountServiceAccountToken: false
```

#### AWS Secrets Manager

```yaml
apiVersion: external-secrets.io/v1
kind: SecretStore
metadata:
  name: aws-secrets
  namespace: my-app
spec:
  provider:
    aws:
      service: SecretsManager
      region: us-west-2
      auth:
        jwt:
          serviceAccountRef:
            name: external-secrets-sa
---
apiVersion: external-secrets.io/v1
kind: ExternalSecret
metadata:
  name: my-app-secrets
  namespace: my-app
spec:
  refreshInterval: 1h
  secretStoreRef:
    name: aws-secrets
    kind: SecretStore
  target:
    name: my-app-secrets
    creationPolicy: Owner
  data:
  - secretKey: database-password
    remoteRef:
      key: myapp/production
      property: database-password
  - secretKey: api-key
    remoteRef:
      key: myapp/production
      property: api-key
```

#### HashiCorp Vault

```yaml
apiVersion: external-secrets.io/v1
kind: SecretStore
metadata:
  name: vault
  namespace: my-app
spec:
  provider:
    vault:
      server: https://vault.example.com
      path: secret
      version: v2
      auth:
        kubernetes:
          mountPath: kubernetes
          role: external-secrets
          serviceAccountRef:
            name: external-secrets-sa
            audiences:
            - vault
---
apiVersion: external-secrets.io/v1
kind: ExternalSecret
metadata:
  name: vault-secrets
  namespace: my-app
spec:
  refreshInterval: 1h
  secretStoreRef:
    name: vault
    kind: SecretStore
  target:
    name: app-secrets
  data:
  - secretKey: password
    remoteRef:
      key: myapp/config
      property: password
```

### Argo CD Vault Plugin (AVP)

Para una integración AVP existente con Argo CD 3.5.2, utilice un sidecar CMP. Copiar el binario al repo-server principal o crear únicamente un ConfigMap no registra el plugin. ConfigManagementPlugin es un archivo de configuración del sidecar, no un CRD de Kubernetes. Los valores de Secret generados pueden quedar sin cifrar en las cachés de Redis y repo-server. Limite este mecanismo a repositorios de confianza y establezca un aislamiento adecuado.

Verifique el binario AVP 1.18.1 de la arquitectura correspondiente con su archivo oficial de sumas de comprobación y colóquelo en el contexto de compilación con el nombre argocd-vault-plugin. Construya y verifique la imagen; sustituya la imagen ilustrativa del registro que aparece abajo por la que publique.

```dockerfile
FROM quay.io/argoproj/argocd:v3.5.2
COPY --chmod=0755 --chown=999:999 argocd-vault-plugin /usr/local/bin/argocd-vault-plugin
USER 999
```

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: avp-plugin-config
  namespace: argocd
data:
  plugin.yaml: |
    apiVersion: argoproj.io/v1alpha1
    kind: ConfigManagementPlugin
    metadata:
      name: argocd-vault-plugin
    spec:
      generate:
        command:
        - argocd-vault-plugin
        - generate
        - .
```

Incorpore estos valores a la configuración del chart argo-cd 10.8.4, conservando las otras entradas de sidecars y volúmenes. El chart proporciona var-files y plugins; el sidecar dispone de un volumen tmp propio.

```yaml
repoServer:
  automountServiceAccountToken: false
  serviceAccount:
    create: true
    name: argocd-repo-server
  extraContainers:
  - name: avp
    image: registry.example.com/argocd-avp:3.5.2-avp1.18.1
    command:
    - /var/run/argocd/argocd-cmp-server
    securityContext:
      runAsNonRoot: true
      runAsUser: 999
      allowPrivilegeEscalation: false
      readOnlyRootFilesystem: true
      capabilities:
        drop:
        - ALL
      seccompProfile:
        type: RuntimeDefault
    env:
    - name: AVP_TYPE
      value: vault
    - name: AVP_AUTH_TYPE
      value: k8s
    - name: AVP_K8S_ROLE
      value: argocd-readonly
    - name: AVP_K8S_MOUNT_PATH
      value: auth/kubernetes
    - name: AVP_K8S_TOKEN_PATH
      value: /var/run/secrets/avp/token
    - name: VAULT_ADDR
      value: https://vault.example.com
    - name: VAULT_CACERT
      value: /etc/vault/ca.crt
    volumeMounts:
    - name: var-files
      mountPath: /var/run/argocd
    - name: plugins
      mountPath: /home/argocd/cmp-server/plugins
    - name: avp-config
      mountPath: /home/argocd/cmp-server/config/plugin.yaml
      subPath: plugin.yaml
      readOnly: true
    - name: avp-tmp
      mountPath: /tmp
    - name: avp-cache
      mountPath: /home/argocd/.avp
    - name: avp-token
      mountPath: /var/run/secrets/avp
      readOnly: true
    - name: vault-ca
      mountPath: /etc/vault
      readOnly: true
  volumes:
  - name: avp-config
    configMap:
      name: avp-plugin-config
  - name: avp-tmp
    emptyDir: {}
  - name: avp-cache
    emptyDir:
      medium: Memory
  - name: avp-token
    projected:
      sources:
      - serviceAccountToken:
          path: token
          audience: vault
          expirationSeconds: 600
  - name: vault-ca
    configMap:
      name: vault-ca
```

Configure el rol argocd-readonly de Vault para el ServiceAccount argocd/argocd-repo-server, con audience=vault, una política de lectura de alcance reducido y un revisor de tokens adecuado. Proporcione la clave ca.crt del ConfigMap vault-ca y un certificado TLS válido de Vault. Conceder permisos amplios de Kubernetes al repo-server no sustituye estos requisitos.

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: my-app
  namespace: argocd
spec:
  project: default
  source:
    repoURL: https://github.com/myorg/myapp.git
    targetRevision: main
    path: manifests
    plugin:
      name: argocd-vault-plugin
  destination:
    server: https://kubernetes.default.svc
    namespace: my-app
```

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: db-secret
  namespace: my-app
  annotations:
    avp.kubernetes.io/path: secret/data/my-app/database
type: Opaque
stringData:
  username: <username>
  password: <password>
```

Limite la Application, el proyecto, el repositorio y las rutas KV de Vault al entorno previsto. Compartir las credenciales de un sidecar no aísla proyectos que no confían entre sí.

### SOPS (Secrets OPerationS)

Este ejemplo utiliza SOPS 3.13.3 y KSOPS 4.5.1. Mantenga separado el destinatario público de age de la identidad privada. Sustituya el destinatario ilustrativo y guarde la clave privada fuera de Git.

```yaml
creation_rules:
- path_regex: ^secrets/.*\.enc\.yaml$
  encrypted_regex: ^(data|stringData)$
  age: age1_REPLACE_WITH_YOUR_PUBLIC_RECIPIENT
```

```bash
set -euo pipefail
umask 077
: "${KUBERNETES_SECRET_FILE:?Provide a protected Secret YAML file outside Git}"
mkdir -p secrets
sops --encrypt --filename-override secrets/db-secret.enc.yaml \
  "$KUBERNETES_SECRET_FILE" > secrets/db-secret.enc.yaml
test -s secrets/db-secret.enc.yaml
```

creation_rules evalúa la ruta de entrada o filename-override, no el archivo al que el shell redirige la salida. Argo CD no descifra SOPS automáticamente de forma predeterminada: necesita el ejecutable KSOPS, las funciones alpha y exec de Kustomize y las credenciales para descifrar.

```yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
namespace: my-app
generators:
- secret-generator.yaml
```

```yaml
apiVersion: viaduct.ai/v1
kind: ksops
metadata:
  name: secret-generator
  annotations:
    config.kubernetes.io/function: |
      exec:
        path: ksops
files:
- secrets/db-secret.enc.yaml
```

Los valores de Helm siguientes corresponden a una instancia de Argo CD existente limitada a repositorios de confianza. Activar globalmente exec implica confiar en la ejecución definida por los repositorios; no proporciona aislamiento entre proyectos que no confían entre sí. Para entornos nuevos, es preferible gestionar los Secrets en el destino.

```yaml
configs:
  cm:
    kustomize.buildOptions: --enable-alpha-plugins --enable-exec
repoServer:
  env:
  - name: SOPS_AGE_KEY_FILE
    value: /etc/sops-age/key.txt
  volumes:
  - name: ksops-tools
    emptyDir: {}
  - name: sops-age
    secret:
      secretName: sops-age
  initContainers:
  - name: install-ksops
    image: viaductoss/ksops:v4.5.1
    command:
    - /usr/local/bin/ksops
    - install
    - --with-kustomize
    - /custom-tools
    volumeMounts:
    - name: ksops-tools
      mountPath: /custom-tools
  volumeMounts:
  - name: ksops-tools
    mountPath: /usr/local/bin/kustomize
    subPath: kustomize
  - name: ksops-tools
    mountPath: /usr/local/bin/ksops
    subPath: ksops
  - name: sops-age
    mountPath: /etc/sops-age
    readOnly: true
```

```bash
# Create the Secret from an existing protected age identity file.
kubectl create secret generic sops-age -n argocd \
  --from-file=key.txt=./age-identity.txt
# Validate in a protected local environment; generated output contains plaintext.
umask 077
render_dir="$(mktemp -d)"
trap 'rm -rf "$render_dir"' EXIT
kustomize build --enable-alpha-plugins --enable-exec . > "$render_dir/rendered.yaml"
```

No incorpore a Git la salida descifrada ni la identidad privada. Estas instalaciones de plugins son alternativas; para combinarlas debe integrar explícitamente las listas de valores, los permisos y los ámbitos de las claves.

## Configuración de TLS {#tls-configuration}

### Certificado del servidor

En producción, utilice una CA de confianza y los SAN correctos. Importe los certificados externos desde archivos protegidos y mantenga las claves privadas fuera de Git.

```bash
: "${TLS_CERT_FILE:?Provide the certificate chain file}"
: "${TLS_KEY_FILE:?Provide the protected private-key file}"
kubectl create secret tls argocd-server-tls -n argocd \
  --cert="$TLS_CERT_FILE" --key="$TLS_KEY_FILE" --dry-run=client -o yaml \
  | kubectl apply --server-side -f -
```

Incluso un certificado autofirmado de desarrollo necesita SAN, por ejemplo mediante la opción de OpenSSL `-addext "subjectAltName=DNS:argocd.example.com"`. Configure la confianza de los clientes, en lugar de utilizar --insecure de forma predeterminada en producción.

### Ejemplo con cert-manager

El ejemplo presupone que cert-manager y un ClusterIssuer letsencrypt-prod de confianza ya están configurados. Para servicios privados, prepare un mecanismo de resolución adecuado, como DNS01. No base instalaciones nuevas en la integración HTTP01 de ingress-nginx, ya retirada.

```yaml
apiVersion: cert-manager.io/v1
kind: Certificate
metadata:
  name: argocd-server-tls
  namespace: argocd
spec:
  secretName: argocd-server-tls
  issuerRef:
    name: letsencrypt-prod
    kind: ClusterIssuer
  dnsNames:
  - argocd.example.com
  privateKey:
    algorithm: RSA
    size: 4096
```

### TLS con Gateway API

El ejemplo presupone Envoy Gateway 1.9.1, GatewayClass eg, los CRD de Gateway API, incluido BackendTLSPolicy v1, y que el Certificate anterior esté Ready. Gateway y argocd-server utilizan el mismo certificado de confianza pública; mantenga server.insecure en false. Configure DNS y el límite de acceso previsto y utilice --grpc-web con la CLI.

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: Gateway
metadata:
  name: argocd-gateway
  namespace: argocd
spec:
  gatewayClassName: eg
  listeners:
  - name: https
    hostname: argocd.example.com
    port: 443
    protocol: HTTPS
    tls:
      mode: Terminate
      certificateRefs:
      - kind: Secret
        name: argocd-server-tls
    allowedRoutes:
      namespaces:
        from: Same
---
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: argocd-server
  namespace: argocd
spec:
  parentRefs:
  - name: argocd-gateway
    sectionName: https
  hostnames:
  - argocd.example.com
  rules:
  - backendRefs:
    - name: argocd-server
      port: 443
---
apiVersion: gateway.networking.k8s.io/v1
kind: BackendTLSPolicy
metadata:
  name: argocd-server
  namespace: argocd
spec:
  targetRefs:
  - group: ''
    kind: Service
    name: argocd-server
    sectionName: https
  validation:
    hostname: argocd.example.com
    wellKnownCACertificates: System
```

wellKnownCACertificates:System presupone la confianza en una CA pública. Para certificados internos o autofirmados, configure caCertificateRefs con la CA de confianza real. Compruebe los listeners de Gateway, los estados Accepted y ResolvedRefs de Route y la validación del certificado del backend.

### Confianza en la CA de Git y TLS de RPC interno

argocd-tls-certs-cm establece la confianza en endpoints HTTPS privados de Git y Helm; no contiene el certificado con el que el propio repo-server atiende solicitudes.

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: argocd-tls-certs-cm
  namespace: argocd
data:
  git.example.com: REPLACE_WITH_VERIFIED_PUBLIC_CA_PEM
```

El RPC interno del repo-server puede estar cifrado sin validar de forma predeterminada el certificado del servidor. Proporcione argocd-repo-server-tls persistente, con SAN DNS del servicio, y reinicie el repo-server. Monte la CA de confianza y utilice --repo-server-ca-cert-path en server, application-controller y applicationset-controller, y --argocd-repo-server-ca-cert-path en notifications-controller. Es preferible indicar la ruta de la CA a utilizar las opciones strict-tls obsoletas. Esto no configura por sí solo TLS mutuo: siga la [guía de mTLS](https://github.com/argoproj/argo-cd/blob/v3.5.2/docs/operator-manual/mtls.md) para los certificados de cliente.

## Registro de auditoría {#audit-logging}

server.audit.enabled y server.audit.path no son opciones admitidas en 3.5.2. Configure los registros de los componentes en stdout, incorpore los valores a argocd-cmd-params-cm existente y reinicie las cargas de trabajo correspondientes.

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: argocd-cmd-params-cm
  namespace: argocd
data:
  server.log.format: json
  server.log.level: info
  controller.log.format: json
  controller.log.level: info
  reposerver.log.format: json
  reposerver.log.level: info
```

```bash
kubectl logs -n argocd deployment/argocd-server --tail=100
```

Los campos y eventos reales dependen del componente y la versión. Un único flujo de registros operativos no constituye un historial de auditoría completo. Correlacione los eventos de Argo CD y Kubernetes, los registros de auditoría de las API de Kubernetes o EKS y el historial de Git, con una política de retención. Evite exponer secretos en los registros de depuración y en la salida de los manifiestos generados.

### Ejemplo de recopilación en CloudWatch

Incorpore esta configuración a un despliegue existente de Fluent Bit u observabilidad a nivel de nodo. Configure por separado los montajes de los registros de contenedores y de la base de datos, parsers.conf, los permisos de IAM y el acceso de red. Montar un volumen audit.log compartido vacío no recopila stdout.

```ini
[SERVICE]
    Parsers_File      /fluent-bit/etc/parsers.conf
[INPUT]
    Name              tail
    Tag               argocd.*
    Path              /var/log/containers/argocd-server-*_argocd_*.log
    multiline.parser  docker, cri
    DB                /var/log/fluent-bit/argocd.db
    Mem_Buf_Limit     10MB
    Skip_Long_Lines   On
[OUTPUT]
    Name              cloudwatch_logs
    Match             argocd.*
    region            ap-northeast-2
    log_group_name    /aws/eks/example-cluster/argocd
    log_stream_prefix argocd-
    auto_create_group false
    log_key           log
```

Cree previamente el grupo de registros con sus opciones de retención y cifrado, y sustituya el grupo y la región. Limite los permisos del recopilador sobre streams y eventos a ese grupo. El formato CRI de containerd y el JSON de la aplicación corresponden a capas distintas.

## Seguridad de red {#network-security}

Estas son plantillas de políticas de referencia para un despliegue sin alta disponibilidad. El CNI debe admitir y aplicar NetworkPolicy. Las reglas que permiten tráfico en políticas que seleccionan el mismo Pod se suman; revise también las políticas amplias existentes. Sustituya el namespace y las etiquetas del plano de datos de Gateway y las direcciones de DNS, API, Git e IdP por las del despliegue real.

192.0.2.10 (API), 198.51.100.10 (Git) y 198.51.100.20 (IdP) son direcciones reservadas para documentación. NetworkPolicy estándar no selecciona FQDN. Para destinos dinámicos, utilice políticas FQDN que admita el CNI o un proxy de salida administrado, teniendo en cuenta el comportamiento antes y después de NAT.

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: argocd-server-restricted
  namespace: argocd
spec:
  podSelector:
    matchLabels:
      app.kubernetes.io/name: argocd-server
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          kubernetes.io/metadata.name: envoy-gateway-system
    ports:
    - protocol: TCP
      port: 8080
  egress:
  - to:
    - podSelector:
        matchLabels:
          app.kubernetes.io/name: argocd-repo-server
    ports:
    - protocol: TCP
      port: 8081
  - to:
    - podSelector:
        matchLabels:
          app.kubernetes.io/name: argocd-redis
    ports:
    - protocol: TCP
      port: 6379
  - to:
    - podSelector:
        matchLabels:
          app.kubernetes.io/name: argocd-dex-server
    ports:
    - protocol: TCP
      port: 5556
  - to:
    - namespaceSelector:
        matchLabels:
          kubernetes.io/metadata.name: kube-system
      podSelector:
        matchLabels:
          k8s-app: kube-dns
    ports:
    - protocol: UDP
      port: 53
    - protocol: TCP
      port: 53
  - to:
    - ipBlock:
        cidr: 192.0.2.10/32
    ports:
    - protocol: TCP
      port: 443
  - to:
    - ipBlock:
        cidr: 198.51.100.20/32
    ports:
    - protocol: TCP
      port: 443
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: argocd-repo-server-restricted
  namespace: argocd
spec:
  podSelector:
    matchLabels:
      app.kubernetes.io/name: argocd-repo-server
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app.kubernetes.io/name: argocd-server
    - podSelector:
        matchLabels:
          app.kubernetes.io/name: argocd-application-controller
    - podSelector:
        matchLabels:
          app.kubernetes.io/name: argocd-applicationset-controller
    - podSelector:
        matchLabels:
          app.kubernetes.io/name: argocd-notifications-controller
    ports:
    - protocol: TCP
      port: 8081
  egress:
  - to:
    - namespaceSelector:
        matchLabels:
          kubernetes.io/metadata.name: kube-system
      podSelector:
        matchLabels:
          k8s-app: kube-dns
    ports:
    - protocol: UDP
      port: 53
    - protocol: TCP
      port: 53
  - to:
    - podSelector:
        matchLabels:
          app.kubernetes.io/name: argocd-redis
    ports:
    - protocol: TCP
      port: 6379
  - to:
    - ipBlock:
        cidr: 198.51.100.10/32
    ports:
    - protocol: TCP
      port: 443
    - protocol: TCP
      port: 22
```

Redis de alta disponibilidad y sus proxies, NodeLocal DNS, los recopiladores de métricas, LDAP, SAML y OIDC de Dex, Vault y KMS para AVP y los componentes adicionales necesitan los flujos correspondientes. Estas dos políticas no cubren todos los componentes del despliegue. Evalúe Pod Security en modos audit y warn antes de imponerlo a las cargas existentes.

## Credenciales de repositorio {#repository-credentials}

Los manifiestos de Secret siguientes solo muestran la estructura. Limite los PAT a los repositorios y permisos de lectura necesarios, y las GitHub Apps a la instalación correspondiente y al permiso Contents-read. Suministre las credenciales mediante gestión externa de Secrets o archivos protegidos. Configure las claves de host SSH verificadas en argocd-ssh-known-hosts-cm. repo-creds.url es un prefijo de URL, no un patrón glob: prevalece la coincidencia más larga. Las plantillas no sustituyen las credenciales propias de un Secret de repositorio.

### HTTPS con Personal Access Token

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: repo-creds-github
  namespace: argocd
  labels:
    argocd.argoproj.io/secret-type: repo-creds
type: Opaque
stringData:
  type: git
  url: https://github.com/myorg/
  password: ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
  username: git
```

### Autenticación con clave SSH

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: private-repo-ssh
  namespace: argocd
  labels:
    argocd.argoproj.io/secret-type: repository
type: Opaque
stringData:
  type: git
  url: git@github.com:myorg/private-repo.git
  sshPrivateKey: |
    -----BEGIN OPENSSH PRIVATE KEY-----
    b3BlbnNzaC1rZXktdjEAAAAABG5vbmUAAAAEbm9uZQAAAAAAAAABAAAAMwAAAAtzc2gtZW
    ...
    -----END OPENSSH PRIVATE KEY-----
```

### Autenticación mediante GitHub App

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: repo-creds-github-app
  namespace: argocd
  labels:
    argocd.argoproj.io/secret-type: repo-creds
type: Opaque
stringData:
  type: git
  url: https://github.com/myorg/
  githubAppID: '123456'
  githubAppInstallationID: '12345678'
  githubAppPrivateKey: |
    -----BEGIN RSA PRIVATE KEY-----
    ...
    -----END RSA PRIVATE KEY-----
```

### Credenciales de repositorio Helm

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: helm-repo-creds
  namespace: argocd
  labels:
    argocd.argoproj.io/secret-type: repository
type: Opaque
stringData:
  type: helm
  name: private-charts
  url: https://charts.example.com
  username: repo-reader
  password: REPLACE_FROM_SECRET_MANAGER
```

## Verificación de firmas GPG {#gpg-signature-verification}

Utilice el formato sourceIntegrity introducido en Argo CD 3.5. Verifica commits y etiquetas anotadas de Git, no firmas de Helm, OCI o imágenes. Crear un Secret cualquiera o una clave de ConfigMap llamada developer1.asc no registra una clave de confianza.

```bash
gpg --armor --export YOUR_VERIFIED_KEY_ID > public-key.asc
argocd gpg add --from public-key.asc
argocd gpg list
```

Antes de importar la clave pública, verifique su huella mediante un canal independiente. Las entradas declarativas del llavero deben estar en argocd-gpg-keys-cm y utilizar como clave el ID real de GPG. Sustituya el valor ilustrativo 0123456789ABCDEF por una clave importada de la organización. Al migrar a sourceIntegrity, elimine signatureKeys heredado.

```yaml
apiVersion: argoproj.io/v1alpha1
kind: AppProject
metadata:
  name: secure-project
  namespace: argocd
spec:
  sourceRepos:
  - https://github.com/myorg/secure-repo
  destinations:
  - namespace: my-app
    server: https://kubernetes.default.svc
  clusterResourceWhitelist: []
  sourceIntegrity:
    git:
      policies:
      - repos:
        - url: '*'
        gpg:
          mode: head
          keys:
          - 0123456789ABCDEF
```

head verifica el commit de destino o la etiqueta anotada. La verificación estricta del historial requiere una política independiente. Las fuentes que no coinciden no se verifican. sourceNamespaces controla los namespaces permitidos para los CR de Application, no las claves de firma.

```bash
# Repository-local configuration; replace the key ID first.
git config user.signingkey YOUR_VERIFIED_KEY_ID
git config commit.gpgsign true
git commit -S -m "Signed change"
git log --show-signature -1
```



## Referencias

- [Gestión de secretos en Argo CD 3.5.2](https://github.com/argoproj/argo-cd/blob/v3.5.2/docs/operator-manual/secret-management.md)
- [Configuración del sidecar CMP](https://github.com/argoproj/argo-cd/blob/v3.5.2/docs/operator-manual/config-management-plugins.md)
- [Límites de confianza de TLS](https://github.com/argoproj/argo-cd/blob/v3.5.2/docs/operator-manual/tls.md)
- [SAML con IAM Identity Center](https://github.com/argoproj/argo-cd/blob/v3.5.2/docs/operator-manual/user-management/identity-center.md)
- [KSOPS 4.5.1](https://github.com/viaduct-ai/kustomize-sops/tree/v4.5.1)

## Cuestionario

Para evaluar lo que ha aprendido, pruebe el [cuestionario de seguridad de Argo CD](../../quizzes/gitops/argocd/07-security-quiz.md).
