# Cuestionario de instalación de ArgoCD

Este cuestionario evalúa tu comprensión de la instalación y configuración de ArgoCD.

1. ¿Cuál es el método recomendado para instalar ArgoCD en un entorno de producción?
   - A) kubectl apply desde la URL raw de GitHub
   - B) Helm chart con valores personalizados
   - C) Docker Compose
   - D) Instalación manual del binario

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Helm chart con valores personalizados**

**Explicación:**
Aunque ArgoCD puede instalarse mediante kubectl apply desde los manifests oficiales, se recomienda usar un Helm chart para entornos de producción porque permite una personalización, actualizaciones y gestión de valores de configuración más sencillas.

</details>

2. ¿En qué namespace se instala normalmente ArgoCD de forma predeterminada?
   - A) default
   - B) kube-system
   - C) argocd
   - D) gitops

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) argocd**

**Explicación:**
Por convención, ArgoCD se instala en el namespace `argocd`. Esto mantiene aislados los componentes de ArgoCD y facilita la gestión de RBAC y las cuotas de recursos.

</details>

3. ¿Cuál es el propósito del componente Repo Server de ArgoCD?
   - A) Almacenar el estado de la aplicación
   - B) Clonar repositorios Git y generar manifests de Kubernetes
   - C) Proporcionar la web UI
   - D) Gestionar la autenticación de usuarios

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Clonar repositorios Git y generar manifests de Kubernetes**

**Explicación:**
El Repo Server se encarga de clonar repositorios Git y generar manifests de Kubernetes a partir de varias fuentes (Helm, Kustomize, YAML simple). Almacena en caché los datos de los repositorios para mejorar el rendimiento.

</details>

4. ¿Cómo recuperas la contraseña inicial de admin después de instalar ArgoCD?
   - A) Se imprime durante la instalación
   - B) Desde un Secret llamado argocd-initial-admin-secret
   - C) Desde el ConfigMap de ArgoCD
   - D) Siempre es "admin"

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Desde un Secret llamado argocd-initial-admin-secret**

**Explicación:**
La contraseña inicial de admin se genera automáticamente y se almacena en un Secret de Kubernetes llamado `argocd-initial-admin-secret`. Puedes recuperarla mediante: `kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}" | base64 -d`

</details>

5. ¿Qué modo de instalación de ArgoCD usa menos recursos, pero tiene funcionalidades limitadas?
   - A) Modo HA
   - B) Modo Core
   - C) Modo Lite
   - D) Modo Minimal

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Modo Core**

**Explicación:**
El modo ArgoCD Core instala solo los componentes esenciales (Application Controller y Repo Server) sin el API Server, UI ni Dex. Este modo es adecuado para entornos en los que ArgoCD se gestiona completamente mediante Git y la CLI.

</details>
