# Cuestionario sobre Crossplane

1. ¿Cuál es el problema principal que resuelven las Compositions de Crossplane?
   - A) Configurar la red del cluster de Kubernetes
   - B) Agrupar múltiples recursos de infraestructura en una única API abstraída para autoservicio
   - C) Automatizar la creación de imágenes de contenedores
   - D) Optimizar las solicitudes de recursos de Pod

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Agrupar múltiples recursos de infraestructura en una única API abstraída para autoservicio**

**Explicación:**
Las Compositions empaquetan múltiples Managed Resources (instancia de RDS, SecurityGroup, SubnetGroup, etc.) en un único Composite Resource (XR). Los desarrolladores pueden aprovisionar la infraestructura necesaria mediante Claims simples sin tener que comprender detalles complejos de infraestructura.

</details>

---

2. ¿Cuál es la relación entre los Claims (XC) de Crossplane y los Composite Resources (XR)?
   - A) Los Claims tienen alcance de cluster y los XR tienen alcance de namespace
   - B) Los Claims son solicitudes con alcance de namespace y los XR son recursos reales con alcance de cluster
   - C) Los Claims y los XR son recursos idénticos
   - D) Los XR son copias de seguridad de los Claims

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Los Claims son solicitudes con alcance de namespace y los XR son recursos reales con alcance de cluster**

**Explicación:**
Los Claims (XC) son interfaces con alcance de namespace para que los desarrolladores soliciten infraestructura. Cuando se crea un Claim, se crea un Composite Resource (XR) correspondiente con alcance de cluster, y el XR aprovisiona los Managed Resources reales según la Composition.

</details>

---

3. ¿Por qué usar IRSA (IAM Roles for Service Accounts) al administrar recursos de AWS con Crossplane?
   - A) Para reducir los costos de licencia de Crossplane
   - B) Para pasar credenciales de AWS de forma segura a los Pods y aplicar el principio de privilegio mínimo
   - C) Para mejorar el rendimiento de Crossplane
   - D) Para soporte multi-cluster

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Para pasar credenciales de AWS de forma segura a los Pods y aplicar el principio de privilegio mínimo**

**Explicación:**
IRSA elimina la necesidad de administrar directamente AWS Access Keys al asociar IAM Roles con Kubernetes ServiceAccounts e inyectar automáticamente credenciales temporales. Esto mejora la seguridad y permite conceder solo los permisos mínimos de IAM necesarios por Provider.

</details>

---

4. ¿Cuál es la mayor diferencia arquitectónica entre Terraform y Crossplane?
   - A) Terraform usa YAML, Crossplane usa HCL
   - B) Terraform usa ejecución imperativa (apply/destroy), Crossplane usa reconciliación continua mediante controladores de Kubernetes
   - C) Terraform solo admite cloud, Crossplane solo admite entornos on-premises
   - D) Terraform es gratuito, Crossplane es de pago

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Terraform usa ejecución imperativa (apply/destroy), Crossplane usa reconciliación continua mediante controladores de Kubernetes**

**Explicación:**
Terraform es una herramienta basada en workflows que se ejecuta mediante los comandos `terraform apply`/`destroy`. Crossplane opera usando el patrón de controladores de Kubernetes, comparando continuamente el estado declarado con el estado real y reconciliando las diferencias. Esto permite la detección y corrección automática de drift.

</details>

---

5. ¿En qué escenario usarías ACK y Crossplane juntos?
   - A) ACK y Crossplane son incompatibles, así que usa solo uno
   - B) Usa ACK para recursos simples de AWS y Crossplane Compositions para abstracciones complejas de múltiples recursos
   - C) ACK es para desarrollo, Crossplane solo para producción
   - D) ACK administra networking, Crossplane administra solo storage

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Usa ACK para recursos simples de AWS y Crossplane Compositions para abstracciones complejas de múltiples recursos**

**Explicación:**
ACK es adecuado para la administración de recursos simples que se asignan 1:1 a la API de AWS, mientras que Crossplane destaca al empaquetar múltiples recursos en una única API abstraída mediante Compositions. Los buckets S3 simples pueden administrarse con ACK, mientras que los paquetes RDS+SecurityGroup+SubnetGroup son más adecuados para Crossplane Compositions.

</details>

---

6. ¿Por qué son importantes los Connection Details de Crossplane?
   - A) Monitorear el estado de la conexión de red
   - B) Generar automáticamente Kubernetes Secrets con información de acceso a los recursos aprovisionados (endpoints, contraseñas, etc.)
   - C) Administrar conexiones entre Crossplane Providers
   - D) Configurar conexiones de red entre multi-cluster

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Generar automáticamente Kubernetes Secrets con información de acceso a los recursos aprovisionados (endpoints, contraseñas, etc.)**

**Explicación:**
Connection Details almacena automáticamente la información de acceso a los recursos aprovisionados (endpoint de base de datos, puerto, nombre de usuario, contraseña, etc.) en Kubernetes Secrets. Las aplicaciones pueden montar estos Secrets para conectarse a la infraestructura aprovisionada.

</details>

---

7. ¿Cuál es el orden correcto del workflow de autoservicio para desarrolladores en una integración de Backstage + Crossplane?
   - A) Despliegue de ArgoCD → registro en el catálogo de Backstage → creación de Crossplane Claim
   - B) Backstage Template genera Crossplane Claim YAML → Git push → sincronización de ArgoCD → aprovisionamiento de Crossplane
   - C) Aprovisionamiento de Crossplane → creación de Backstage Template → Git push
   - D) Git push → registro en el catálogo de Backstage → despliegue de ArgoCD

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Backstage Template genera Crossplane Claim YAML → Git push → sincronización de ArgoCD → aprovisionamiento de Crossplane**

**Explicación:**
Cuando un desarrollador introduce parámetros (tamaño de la DB, entorno, etc.) en un Backstage Template, el Template genera Crossplane Claim YAML y lo sube al repositorio Git. ArgoCD detecta el cambio y lo sincroniza con el cluster, donde Crossplane procesa el Claim y aprovisiona la infraestructura real.

</details>

---

8. ¿En qué sentido la detección de drift de Crossplane es superior en comparación con Terraform?
   - A) Terraform no admite detección de drift
   - B) Los controladores de Crossplane monitorean continuamente el estado real y lo autocorrigen, mientras que Terraform requiere `plan`/`apply` manual
   - C) Crossplane aprovisiona más rápido
   - D) Crossplane admite más clouds

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Los controladores de Crossplane monitorean continuamente el estado real y lo autocorrigen, mientras que Terraform requiere `plan`/`apply` manual**

**Explicación:**
Los controladores de Crossplane verifican periódicamente el estado real de los recursos cloud y corrigen automáticamente cualquier drift respecto del estado declarado. Terraform requiere ejecutar manualmente `terraform plan` para detectar drift y `terraform apply` para corregirlo, lo que hace que el enfoque de Crossplane sea más adecuado para workflows GitOps.

</details>
