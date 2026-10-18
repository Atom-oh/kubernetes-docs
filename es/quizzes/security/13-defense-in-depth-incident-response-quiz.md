# Cuestionario sobre defensa en profundidad y respuesta a incidentes

> **Última actualización**: October 15, 2026

[Lea el capítulo y las fuentes principales](../../security/13-defense-in-depth-incident-response.md)

### 1. ¿Qué ruta había que revisar para CVE-2025-1974 además de la cobertura pública de WAF?

- A) El admission webhook accesible desde la red de los Pods
- B) Solo la ruta del viewer de CloudFront
- C) Solo el cifrado del almacenamiento de bases de datos
- D) Solo el tamaño de la caché DNS

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A) El admission webhook accesible desde la red de los Pods**

**Explicación:** Revise la accesibilidad del webhook y los privilegios de Secret del controller. Las versiones corregidas históricamente no resuelven la retirada posterior de ingress-nginx.

</details>

### 2. ¿Qué implica la declaración de retirada de ingress-nginx para un diseño nuevo en 2026?

- A) Una corrección histórica de CVE es suficiente para siempre
- B) Planificar la migración a una implementación mantenida
- C) WAF garantiza futuros parches del controller
- D) Desactivar todos los webhooks de Kubernetes

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Planificar la migración a una implementación mantenida**

**Explicación:** Tras la retirada, ingress-nginx no recibirá más versiones de seguridad. Revise el mantenimiento y la migración, no solo un parche anterior.

</details>

### 3. ¿Cuál es el alcance de afectación de PAN-OS CVE-2026-0322?

- A) Todos los productos de Palo Alto sin excepción
- B) Solo usuarios de Internet no autenticados
- C) RCE autenticado en la interfaz de administración de las familias de productos indicadas
- D) Un problema de tamaño del cuerpo de WAF

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) RCE autenticado en la interfaz de administración de las familias de productos indicadas**

**Explicación:** El aviso cubre PA-Series, VM-Series y Panorama, y excluye Cloud NGFW/Prisma Access para este problema. Importan tanto las credenciales como la accesibilidad de administración.

</details>

### 4. ¿Cómo se debe representar la corrección de Fortinet del 28 de enero?

- A) Todos los IdP de SAML están afectados
- B) Ningún producto de Fortinet está afectado
- C) Todos los problemas de SSO tienen el mismo alcance
- D) Los IdP SAML de terceros/FortiAuthenticator están excluidos del problema especificado

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: D) Los IdP SAML de terceros/FortiAuthenticator están excluidos del problema especificado**

**Explicación:** Use el alcance revisado en lugar de la afirmación SAML inicial, más amplia. Aún hay que comprobar si FortiCloud SSO está afectado.

</details>

### 5. ¿Qué tráfico queda cubierto automáticamente solo por enrutar flujos seleccionados mediante la inspección central de TGW?

- A) Todo el tráfico de Pods en el mismo nodo
- B) Todas las conexiones de PrivateLink
- C) Todas las rutas alternativas de peering
- D) Solo los flujos que realmente pasan por esa ruta de inspección

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: D) Solo los flujos que realmente pasan por esa ruta de inspección**

**Explicación:** Inventaríe por separado las rutas locales, de endpoint, peering e IPv6; siguen siendo necesarios los controles complementarios de CNI, IAM, SG y aplicación.

</details>

### 6. ¿Qué diferencia la finalización de parches de la eliminación de un compromiso?

- A) Solo la hora del reinicio
- B) La evidencia sobre cuentas/configuraciones no autorizadas, acceso persistente y secretos expuestos
- C) Que un target esté en buen estado
- D) Que haya una cadena de versión más reciente

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) La evidencia sobre cuentas/configuraciones no autorizadas, acceso persistente y secretos expuestos**

**Explicación:** El acceso persistente puede continuar tras aplicar un parche. Investigue y recupere la configuración, las cuentas y las credenciales relacionadas conforme a las indicaciones del proveedor.

</details>

### 7. ¿Qué demuestra por sí solo un recuento de bloqueos de WAF igual a cero?

- A) Todas las solicitudes eran seguras
- B) Se inspeccionaron todas las rutas
- C) No demuestra seguridad completa ni cobertura efectiva de rutas
- D) No se robaron credenciales de administrador

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) No demuestra seguridad completa ni cobertura efectiva de rutas**

**Explicación:** Correlacione las asociaciones, las acciones, las canary benignas, las restricciones del origen y los registros de la aplicación. Cero bloqueos también puede significar que falta cobertura.

</details>

### 8. ¿Qué evidencia propuesta de aceptación de recuperación es la más sólida?

- A) Solo la versión
- B) Una captura de pantalla del appliance
- C) Un solo inicio de sesión correcto
- D) Configuración/credenciales limpias más nuevas pruebas de negocio, rutas denegadas y registros

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: D) Configuración/credenciales limpias más nuevas pruebas de negocio, rutas denegadas y registros**

**Explicación:** Combine evidencia de erradicación con la funcionalidad legítima, la administración restringida, la inspección y la observabilidad restaurada.

</details>
