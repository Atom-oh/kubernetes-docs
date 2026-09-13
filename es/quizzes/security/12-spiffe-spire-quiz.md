# Cuestionario de SPIFFE/SPIRE

> **Última actualización**: September 13, 2026

## Preguntas

<span id="_1-what-is-the-correct-format-for-a-spiffe-id"></span>

### 1. ¿Cuál es un SPIFFE ID válido?

- A) `https://example.org/app`
- B) `spiffe://example.org/app`
- C) `spiffe://example.org:8443/app`
- D) `spiffe://example.org/app?role=admin`

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) spiffe://example.org/app**

Se usa el esquema spiffe, un trust domain (dominio de confianza) y una ruta opcional. No se permiten puertos, cadenas de consulta ni fragmentos. La estructura de la ruta la define cada sitio y no se limita a /ns/.../sa/... .

</details>

<span id="_2-what-is-the-key-difference-between-x-509-svid-and-jwt-svid"></span>

### 2. ¿Qué afirmación describe correctamente la validación de X.509/JWT-SVID?

- A) Solo inspeccionar el CN del X.509
- B) Una firma JWT válida hace innecesario el audience
- C) Validar el URI SAN/la cadena del X.509 y la firma/sub/audience/expiración del JWT
- D) Las comprobaciones de audience del JWT evitan cualquier replay

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Validar el URI SAN/la cadena del X.509 y la firma/sub/audience/expiración del JWT**

El CN del certificado no es la identidad SPIFFE. Un token JWT de tipo bearer puede sufrir replay aunque el audience coincida. Los tiempos de vida dependen de la política; el alcance de X.509/JWT de este capítulo es independiente de la especificación WIT-SVID en estado Incubating.

</details>

<span id="_3-what-is-the-primary-role-of-the-spire-server"></span>

### 3. ¿Cuál es la función del SPIRE Server?

- A) Cifrar automáticamente todas las conexiones de las aplicaciones
- B) Gestionar la attestation de los agents, el registro y la firma de SVID
- C) Autorizar automáticamente todas las solicitudes de servicio
- D) Distribuir archivos de claves privadas a todos los Pods mediante CSI

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Gestionar la attestation de los agents, el registro y la firma de SVID**

Hay que distinguir las responsabilidades de la firma de CA/JWT, del DataStore y del KeyManager. Un upstream de AWS PCA firma las CA intermedias de SPIRE, pero no elimina la firma local de certificados hoja ni la gestión de claves.

</details>

<span id="_4-what-is-the-primary-role-of-the-spire-agent"></span>

### 4. ¿Quién identifica a la aplicación que llama a la Workload API?

- A) El workload attestor del SPIRE agent local
- B) Un resolvedor DNS
- C) CSI comprobando nombres de archivo
- D) Únicamente el SPIFFE ID que la propia aplicación declara

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A) El workload attestor del SPIRE agent local**

El agent examina el PID/los cgroups del llamante y los metadatos del Pod, y los compara con las entradas autorizadas y la caché. Hacer el fetch dentro de un Pod del agent atesta a ese llamante, no al contexto real de la aplicación.

</details>

<span id="_5-which-node-attestation-method-is-recommended-for-amazon-eks"></span>

### 5. ¿Cómo valida el server un token k8s_psat?

- A) Comprobando los permisos de S3 de un rol de IRSA
- B) TokenReview de Kubernetes más el audience y la lista de ServiceAccounts permitidas configurados
- C) Solo decodificando el token en base64
- D) Convirtiéndolo en un join token sin expiración

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) TokenReview de Kubernetes más el audience y la lista de ServiceAccounts permitidas configurados**

Deben coincidir los nombres lógicos de cluster del server y del agent, el audience del token, la lista de SA permitidas y los permisos de TokenReview. aws_iid es una alternativa con supuestos de confianza distintos: no es universalmente más fuerte ni está prohibida en EKS.

</details>

<span id="_6-what-selector-types-does-k8s-workload-attestation-support"></span>

### 6. ¿Cómo debe interpretarse k8s:container-image:nginx:*?

- A) Coincidencia glob automática para todas las etiquetas de nginx
- B) Un valor de selector; no se debe suponer coincidencia con comodines
- C) Prueba de que la firma de la imagen está verificada
- D) Aplicación automática del RBAC del namespace

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Un valor de selector; no se debe suponer coincidencia con comodines**

Hay que hacer coincidir los valores reales de image/ImageID que reporta Kubernetes. Las etiquetas por sí solas no establecen confianza en la cadena de suministro. Los permisos de creación y modificación de Pods, SA y labels también influyen en la elegibilidad de la identidad.

</details>

<span id="_7-what-is-the-purpose-of-the-spiffe-csi-driver"></span>

### 7. ¿Qué monta SPIFFE CSI 0.2.13 dentro de un Pod?

- A) Archivos svid.pem/svid.key generados automáticamente
- B) Un directorio que contiene el socket Unix de la Workload API
- C) La clave privada de la CA de SPIRE
- D) Datos compartidos de PostgreSQL

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Un directorio que contiene el socket Unix de la Workload API**

CSI proporciona acceso al socket de la API. Las aplicaciones basadas en archivos necesitan un adaptador aparte y gestión de la recarga. Las aplicaciones o los proxies siguen siendo quienes consumen la API; la integración no es automática en todos los casos.

</details>

<span id="_8-what-does-spiffe-federation-enable"></span>

### 8. ¿Qué se requiere para hacer el bootstrap de la federación https_spiffe?

- A) Solo una URL de endpoint
- B) Un bundle de confianza inicial y el SPIFFE ID correcto del endpoint
- C) Intercambiar ambas claves privadas de CA
- D) Autorizar automáticamente todos los workloads remotos

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Un bundle de confianza inicial y el SPIFFE ID correcto del endpoint**

Hay que configurar cada dirección de confianza. La actualización del bundle, la conectividad, la verificación TLS y la autorización de los workloads son responsabilidades independientes. https_web utiliza la ruta de validación de Web PKI del endpoint.

</details>

<span id="_9-how-does-spiffe-spire-compare-to-iam-roles-for-service-accounts-irsa"></span>

### 9. ¿Qué afirmación compara correctamente IRSA y SPIFFE/SPIRE?

- A) La renovación de IRSA siempre requiere reiniciar el Pod
- B) SPIFFE elimina la necesidad de políticas de AWS IAM
- C) IRSA es una vía de credenciales de AWS; SPIFFE es identidad de workload, y cada una requiere validación
- D) Una anotación en el Pod completa IRSA y la entrega de archivos de certificado por CSI

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) IRSA es una vía de credenciales de AWS; SPIFFE es identidad de workload, y cada una requiere validación**

IRSA se renueva mediante el comportamiento admitido del SDK y del token proyectado, y admite diseños entre cuentas. Hay que validar las anotaciones del ServiceAccount, la confianza en aud/sub y los permisos de AWS. El mTLS de SPIFFE también requiere el consumo de las credenciales y la autorización del peer.

</details>

<span id="_10-what-are-best-practices-for-naming-trust-domains-in-spiffe"></span>

### 10. ¿Qué afirmación sobre los trust domains y la rotación de la CA es correcta?

- A) Un trust domain debe ser un nombre DNS resoluble
- B) bundle set rota automáticamente la clave privada de la CA
- C) Elegir nombres estables y distinguir los cambios de bundle de la rotación de la clave de la CA
- D) El parser siempre rechaza los dominios numéricos o con forma de IPv4

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Elegir nombres estables y distinguir los cambios de bundle de la rotación de la clave de la CA**

La nomenclatura similar a DNS es una recomendación, no la regla sintáctica completa. Los bundles son material de confianza público; la rotación de claves es un ciclo de vida aparte. Hay que verificar el solapamiento de autoridades y la actualización de los consumidores.

</details>

## Cálculo de la puntuación

- 9–10: Comprensión sólida
- 7–8: Repasa las vías de confianza, autorización y entrega
- 6 o menos: Revisa la guía y los ejemplos validados

## Documentación relacionada

- [SPIFFE/SPIRE](../../security/12-spiffe-spire.md)
