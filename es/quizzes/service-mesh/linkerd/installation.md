# Cuestionario de instalación de Linkerd

Revisado el 16 de octubre de 2026 con edge-26.10.1 y los charts 2026.10.1. Consulta la [guía de instalación](../../../service-mesh/linkerd/01-installation.md) para ver todos los requisitos previos y los límites de validación.

### 1. ¿Cómo se debe obtener la versión exacta de la CLI pública que usa esta guía?

A. Suponer que cualquier paquete llamado linkerd tiene la misma versión

B. Elegir el artefacto oficial edge-26.10.1 para el sistema operativo y la arquitectura, y verificar su checksum y la versión del cliente

C. Usar `kubectl install linkerd`

D. Pasar `--version stable-2.16.0` a un instalador que no interpreta esa opción

<details>
<summary>Respuesta y explicación</summary>

**Respuesta: B**

La guía fija un artefacto oficial de una versión específica. La alternativa del instalador usa `LINKERD2_VERSION`; el antiguo script de instalación está obsoleto y ahora usa edge de forma predeterminada. Para las distribuciones stable, sigue las indicaciones del proveedor. Para Windows existe el artefacto de versión `windows.exe`; no inventes un nombre como `windows-amd64.exe`.

</details>

### 2. ¿Qué comando se usa como comprobación previa a una instalación nueva?

A. `linkerd check`

B. `linkerd check --pre`

C. `linkerd verify`

D. `linkerd install --dry-run`

<details>
<summary>Respuesta y explicación</summary>

**Respuesta: B**

`check --pre` comprueba el acceso a la API, la versión mínima de Kubernetes, los requisitos previos de Gateway API y los permisos o la configuración necesarios para la instalación. No demuestra la compatibilidad con todas las versiones posteriores de Kubernetes. Revisa la matriz de compatibilidad de la versión exacta y usa la opción compatible con CNI si seleccionas esa ruta de instalación.

</details>

### 3. ¿Qué material de identidad se necesita para la instalación manual con Helm?

A. Una imagen de Envoy

B. El ancla de confianza pública y el certificado y la clave privada de la entidad emisora, o una integración admitida con el secreto de una entidad emisora configurada

C. La clave privada de la CA raíz en cada Pod del proxy

D. Un archivo de configuración de Prometheus

<details>
<summary>Respuesta y explicación</summary>

**Respuesta: B**

Para esta ruta, el chart Helm del plano de control no genera el material de la CA de identidad de las cargas de trabajo. Proporciona el ancla de confianza pública y la credencial de firma de la entidad emisora. Mantén la clave privada raíz fuera de Kubernetes. Las integraciones con secretos de entidades emisoras externas requieren la configuración correspondiente de esquema y propietario.

</details>

### 4. ¿Cuántas réplicas del perfil HA empaquetado se seleccionan para los componentes críticos del plano de control?

A. 1

B. 2

C. 3

D. 5

<details>
<summary>Respuesta y explicación</summary>

**Respuesta: C**

El perfil empaquetado selecciona tres réplicas de los componentes críticos, con antiafinidad entre nodos, PDB y una política `Fail` para el webhook de inyección. Son instancias redundantes que atienden solicitudes, no miembros de un quórum. Aun así, hacen falta suficientes nodos aptos, recursos y credenciales y rutas de red operativas; el número de réplicas por sí solo no garantiza disponibilidad.

</details>

### 5. ¿Cuál no es una función principal de Viz?

A. Panel web

B. Métricas basadas en Prometheus

C. Promoción automática de canary

D. Tap de tráfico HTTP

<details>
<summary>Respuesta y explicación</summary>

**Respuesta: C**

Viz ofrece métricas, panel y Tap. Para avanzar una implementación canary se necesita un controlador de entrega y una política de análisis aparte. El chart actual de Viz ofrece enlaces a un Grafana externo; `grafana.enabled` no instala ni deshabilita un Grafana integrado.

</details>

### 6. ¿Qué balanceador de AWS puede conservar el transporte TCP sin procesar del gateway, sin terminar el mTLS de Linkerd?

A. Un listener HTTP de ALB

B. Un recurso Ingress del panel

C. Un listener TCP de NLB

D. Una ruta de dispositivo GENEVE de Gateway Load Balancer

<details>
<summary>Respuesta y explicación</summary>

**Respuesta: C**

Usa passthrough TCP para el transporte del gateway de Linkerd. Que el NLB sea interno o público es una elección de esquema determinada por los requisitos de red, no otro tipo de balanceador. El ejemplo de NLB interno de la guía supone que lo administra AWS Load Balancer Controller y que las redes remotas y las rutas de sondeo son accesibles.

</details>

### 7. ¿Qué orden de actualización coincide con el flujo de trabajo documentado?

A. Plano de datos y después plano de control y CRD

B. CLI de destino, CRD, plano de control, extensiones instaladas y, por último, plano de datos

C. CRD, plano de datos y, por último, plano de control

D. Eliminar la CA y volver a instalar todo

<details>
<summary>Respuesta y explicación</summary>

**Respuesta: B**

Primero revisa la compatibilidad de la versión de destino, las notas de versión y el estado actual. Conserva las credenciales de confianza y actualiza cada recurso mediante su propietario. Después, recrea los Pods previstos de la aplicación para que reciban el proxy nuevo. Las extensiones de la CLI generan las actualizaciones con `install`; `viz upgrade` no es un subcomando. Respeta las versiones intermedias admitidas y revisa lo que se eliminará antes de borrar recursos.

</details>

### 8. ¿Qué hace por sí solo `linkerd install --crds`?

A. Instala el binario de la CLI

B. Genera manifiestos de los CRD de Linkerd

C. Aplica inmediatamente todos los recursos del clúster

D. Inyecta el proxy en todos los Pods de aplicación existentes

<details>
<summary>Respuesta y explicación</summary>

**Respuesta: B**

El comando genera manifiestos. La instalación la realiza `kubectl apply` o el propietario de despliegue elegido. Los requisitos previos de Gateway API son independientes de la salida predeterminada de CRD de Linkerd, y el plano de control se instala después.

</details>

### 9. ¿Qué método de trazas corresponde a edge-26.10.1?

A. Ejecutar `linkerd jaeger install`, porque la CLI aún incluye todas las extensiones

B. Configurar un recolector y un backend admitidos, junto con la propagación del contexto de la aplicación en el proxy

C. Instalar Viz y suponer que almacena todas las trazas distribuidas

D. Ignorar los encabezados de traza porque los proxies pueden reconstruir todos los spans de la aplicación

<details>
<summary>Respuesta y explicación</summary>

**Respuesta: B**

Esta CLI no tiene un subcomando `jaeger`, y el historial público del chart linkerd-jaeger es anterior a la versión seleccionada. Usa la ruta actual de datos de trazas y verifica que sean compatibles la recepción y la exportación. Las métricas y los gráficos de topología no equivalen a la recopilación de trazas distribuidas.

</details>

### 10. ¿Qué debe hacer primero un plan completo de desinstalación?

A. Eliminar los CRD mientras las aplicaciones todavía tienen el proxy inyectado

B. Quitar la inyección de aplicaciones y los proxies manuales, y verificar los Pods recreados antes de eliminar las extensiones y el plano de control

C. Eliminar inmediatamente todos los espacios de nombres

D. Forzar la desinstalación para ignorar las aplicaciones que todavía tienen el proxy inyectado

<details>
<summary>Respuesta y explicación</summary>

**Respuesta: B**

Quita todos los mecanismos de inyección mediante los propietarios de las cargas de trabajo, recrea y verifica los Pods de la aplicación y, después, elimina las extensiones instaladas y el plano de control y los CRD mediante sus respectivos propietarios. Al eliminar un CRD también se eliminan sus recursos personalizados. Revisa por separado la limpieza de CNI y la propiedad de los espacios de nombres, incluida la pérdida de seguridad y enrutamiento de la malla.

</details>

### 11. ¿Qué no valida `linkerd check`?

A. El acceso a la API de Kubernetes

B. La validez de los certificados del plano de control

C. La lógica de negocio de la aplicación

D. El estado de los Pods del plano de control

<details>
<summary>Respuesta y explicación</summary>

**Respuesta: C**

Las comprobaciones de estado principales no validan los resultados de negocio ni todas las rutas de tráfico y seguridad. `check --proxy` agrega las comprobaciones pertinentes del plano de datos; las extensiones instaladas tienen sus propias comprobaciones. Las pruebas de la aplicación y la verificación con tráfico real deben hacerse por separado.

</details>

### 12. ¿Qué anotación de espacio de nombres solicita la inyección automática del proxy?

A. `linkerd.io/inject: enabled`

B. `linkerd.io/proxy: true`

C. `sidecar.linkerd.io/inject: true`

D. `linkerd/auto-inject: yes`

<details>
<summary>Respuesta y explicación</summary>

**Respuesta: A**

La anotación solicita la inyección en los Pods nuevos que cumplen los criterios. Las anulaciones a nivel de Pod, las exclusiones del webhook y las condiciones de la plataforma pueden cambiar el resultado; no garantiza que se inyecte el proxy en todos los Pods nuevos. Hay que recrear los Pods existentes, y los sidecars nativos pueden aparecer en `initContainers`.

</details>
