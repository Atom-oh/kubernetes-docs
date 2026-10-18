# Cuestionario sobre Docker Hub
> **Última actualización**: 11 de septiembre de 2026

1. ¿Qué límite se usa para atribuir las descargas anónimas de Docker Hub desde nodos detrás de NAT?
   - A) Cada pod de Kubernetes
   - B) La dirección IPv4 de origen o la subred IPv6 `/64`
   - C) El espacio de nombres de Kubernetes
   - D) Descargas ilimitadas

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) La dirección IPv4 de origen o la subred IPv6 `/64`**

**Explicación:**
Los nodos que comparten una dirección NAT pueden consumir el mismo cupo anónimo. Consulta el límite y el período de restablecimiento reales en la política actual y en los encabezados de respuesta; la atribución a una cuenta autenticada y los controles contra el abuso son aspectos distintos.

</details>

2. ¿Qué recurso de Kubernetes se usa para guardar las credenciales de Docker Hub para descargar imágenes privadas?
   - A) ConfigMap
   - B) Secret con el tipo `kubernetes.io/dockerconfigjson`
   - C) ServiceAccount
   - D) PersistentVolumeClaim

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Secret con el tipo `kubernetes.io/dockerconfigjson`**

**Explicación:**
Kubernetes usa Secrets del tipo `kubernetes.io/dockerconfigjson` para guardar las credenciales de un registro. Luego se hace referencia a este Secret en las especificaciones de Pod mediante `imagePullSecrets` o se asocia a una cuenta de servicio para que se inyecte automáticamente.

</details>

3. ¿Cuál es el enfoque recomendado para mitigar los límites de frecuencia de Docker Hub en un clúster de Kubernetes?
   - A) Usar más direcciones IP
   - B) Configurar una caché pull-through o un mirror de registro
   - C) Deshabilitar la descarga de imágenes
   - D) Usar únicamente imágenes locales

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Configurar una caché pull-through o un mirror de registro**

**Explicación:**
Una caché pull-through reduce las descargas repetidas de capas. Los fallos de caché, la comprobación de etiquetas mutables y las actualizaciones aún se conectan con el upstream, así que el almacenamiento en caché no elimina los límites de frecuencia.

</details>

4. ¿Cómo se proporcionan credenciales de descarga predeterminadas a los pods nuevos mediante el ServiceAccount predeterminado del espacio de nombres?
   - A) Añadir el Secret al espacio de nombres `kube-system`
   - B) Aplicar un parche al ServiceAccount predeterminado del espacio de nombres con `imagePullSecrets`
   - C) Establecer un ConfigMap para todo el clúster
   - D) Modificar la configuración de kubelet

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Aplicar un parche al ServiceAccount predeterminado del espacio de nombres con `imagePullSecrets`**

**Explicación:**
Añade `imagePullSecrets` a esa cuenta de servicio. Si no tienen su propia lista de secretos de descarga, los pods nuevos que la usen heredan esa lista al admitirse. Los pods existentes, otras cuentas de servicio y los demás espacios de nombres no se actualizan retroactivamente.

</details>

5. ¿Qué distingue a las imágenes oficiales de Docker de otras imágenes de Docker Hub?
   - A) Pertenecen a un programa curado con imágenes upstream revisadas y documentación
   - B) Siempre son gratuitas
   - C) No tienen límites de frecuencia
   - D) Se actualizan automáticamente todos los días

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A) Pertenecen a un programa curado con imágenes upstream revisadas y documentación**

**Explicación:**
Las imágenes oficiales de Docker son seleccionadas junto con responsables de mantenimiento upstream y comunitarios, y se revisan según las normas del programa. La insignia no garantiza que una etiqueta particular esté libre de vulnerabilidades; verifica el digest elegido y su estado de mantenimiento.

</details>

6. ¿Cuál es el propósito de las imágenes Docker Verified Publisher?
   - A) Son imágenes gratuitas de contribuidores aleatorios
   - B) Son imágenes de proveedores de software comercial verificados por Docker
   - C) Son imágenes heredadas obsoletas
   - D) Son imágenes que evitan el análisis de seguridad

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Son imágenes de proveedores de software comercial verificados por Docker**

**Explicación:**
Las imágenes Docker Verified Publisher proceden de proveedores de software comercial que se asociaron con Docker y pasaron un proceso de verificación. Esto da confianza en que las imágenes son auténticas y las mantiene el proveedor real del software, lo que reduce los riesgos para la seguridad de la cadena de suministro.

</details>

7. ¿Qué nivel de suscripción de Docker Hub ofrece repositorios privados ilimitados?
   - A) Nivel gratuito
   - B) Solo Pro
   - C) Solo Team
   - D) Pro, Team y Business, sujetos a las políticas de sus planes

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: D) Pro, Team y Business, sujetos a las políticas de sus planes**

**Explicación:**
La tabla de uso indica repositorios privados ilimitados en Pro, Team y Business, sujetos a las condiciones del plan y de uso razonable. Personal incluye uno.

</details>

8. ¿Qué riesgo para la seguridad de la cadena de suministro se asocia al uso de imágenes públicas de Docker Hub?
   - A) Las imágenes pueden contener vulnerabilidades o código malicioso
   - B) Las imágenes siempre están desactualizadas
   - C) Las imágenes no se pueden analizar
   - D) Las imágenes son demasiado grandes

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A) Las imágenes pueden contener vulnerabilidades o código malicioso**

**Explicación:**
Las imágenes públicas de Docker Hub pueden contener vulnerabilidades conocidas, dependencias obsoletas o, en casos poco frecuentes, código malicioso (ataques de typosquatting o cuentas de responsables de mantenimiento comprometidas). Las organizaciones deberían analizar las imágenes antes de usarlas, preferir imágenes oficiales o de Verified Publisher y considerar mantener sus propias imágenes base seleccionadas.

</details>

9. ¿Cuál es el comando correcto de kubectl para crear un secreto de descarga de imágenes de Docker Hub?
   - A) `kubectl create secret docker-registry my-secret --docker-server=https://index.docker.io/v1/ --docker-username=USER --docker-password=TOKEN`
   - B) `kubectl create configmap my-secret --docker-server=docker.io`
   - C) `kubectl apply secret docker my-secret`
   - D) `kubectl set image secret my-secret`

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A) `kubectl create secret docker-registry my-secret --docker-server=https://index.docker.io/v1/ --docker-username=USER --docker-password=TOKEN`**

**Explicación:**
El comando crea un Secret del tipo `kubernetes.io/dockerconfigjson`. El ejemplo usa la clave de credenciales estándar de Docker Hub, `https://index.docker.io/v1/`. Sustituye USER/TOKEN por credenciales adecuadas sin incluirlas en el repositorio, y crea el Secret en el espacio de nombres del pod que lo consumirá.

</details>

10. ¿Cuál es la recomendación adecuada para Docker Hub Automated Builds a septiembre de 2026?
    - A) Usarlo como opción predeterminada en todas las canalizaciones CI nuevas
    - B) No se ha anunciado su retirada
    - C) Migrar desde la función obsoleta antes del 1 de abril de 2027
    - D) Está disponible para todas las cuentas gratuitas

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Migrar desde la función obsoleta antes del 1 de abril de 2027**

**Explicación:**
La documentación oficial marca Automated Builds como obsoleta y da el 1 de abril de 2027 como fecha de retirada. La integración nativa heredada usa GitHub/Bitbucket; GitLab CI puede crear y publicar imágenes de forma independiente.

</details>
