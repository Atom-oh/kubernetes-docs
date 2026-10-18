# Defensa en profundidad y respuesta a incidentes reales

> **Base de revisión**: documentación oficial de AWS, Kubernetes, Palo Alto Networks y Fortinet; avisos de CISA y NIST SP 800-61r3. Las fechas de publicación se distinguen de la fecha de investigación.
> **Última actualización**: 15 de octubre de 2026

Un diseño de seguridad debe cubrir la entrada, el movimiento lateral, la exfiltración y la recuperación. Este capítulo conecta los controles perimetrales y la gestión de incidentes con las guías existentes de [seguridad de EKS](./06-eks-security-best-practices.md), [NetworkPolicy](./04-network-policies.md) y [seguridad de runtime](./08-runtime-security.md). Los criterios operativos y la secuencia que aparecen a continuación son **propuestas de diseño** para esta guía, no garantías que se obtengan al instalar un producto.

## 1. Incidentes verificados y lecciones de diseño

| Caso y fecha de publicación/retiro | Alcance establecido por fuentes primarias | Consecuencia para el diseño |
|---|---|---|
| ingress-nginx CVE-2025-1974, 2025-03-24 | Ataque a través del controlador de admisión de validación, accesible desde la red de Pods; las correcciones históricas fueron 1.11.5 y 1.12.1 | Revise la accesibilidad del webhook y los permisos del controlador sobre Secrets junto con la protección WAF externa |
| Retiro de ingress-nginx, 2026-03 | Kubernetes Steering/SRC advirtió el 2026-01-29 que las actualizaciones de seguridad cesarían después del retiro | Migre a una implementación con mantenimiento activo; las correcciones históricas de CVE no son una nueva recomendación de versión para 2026 |
| PAN-OS CVE-2025-0108, 2025-02-12 | Omisión de autenticación en la interfaz web de administración con intentos observados de encadenamiento | Separe el acceso de administración de las rutas de aplicaciones públicas |
| PAN-OS CVE-2026-0322, 2026-10-14 | RCE autenticado como root en la interfaz de administración; se observó explotación limitada; afectados PA-Series, VM-Series y Panorama | Proteja las credenciales de administrador, las sesiones y la accesibilidad de administración; distinga las familias de productos |
| FortiCloud SSO CVE-2026-24858, inclusión en CISA KEV 2026-01-27 | Acceso entre cuentas con FortiCloud SSO habilitado, cambios de cuenta/VPN y una nueva ruta que afecta a dispositivos corregidos para CVE de SSO anteriores | Audite los cambios administrativos; adoptar SSO por sí solo no basta |
| Acceso persistente a FortiGate, 2025-04-10 | Un enlace simbólico relacionado con SSL-VPN podía conservar el acceso de lectura a archivos después de corregir vulnerabilidades anteriores | Considere la aplicación de parches y la eliminación del acceso no autorizado como condiciones de finalización independientes |

Evidencia: [aviso CVE de Kubernetes][S01], [comunicado de retiro][S02], [aviso de PAN-OS de 2025][S04], [aviso de 2026][S03], [datos de CISA KEV][S06] y [análisis de persistencia de Fortinet][S07]. Fortinet corrigió su análisis SSO de 2026 el 28 de enero: **los IdP SAML de terceros y FortiAuthenticator no están afectados por ese problema**. No repita la formulación inicial más amplia de «todos los SAML». [S05]

CISA añadió CVE-2026-0322 el 2026-10-14 y CVE-2026-24858 el 2026-01-27. Al priorizar, revise la inclusión en KEV junto con los productos afectados indicados por el proveedor. No generalice los plazos de corrección del gobierno federal de EE. UU. como obligaciones legales universales. [S06]

La divulgación de una vulnerabilidad no demuestra que todas las instalaciones hayan sido comprometidas. Compruebe el producto, la rama, las correcciones urgentes, las funciones habilitadas, la exposición y la evidencia. Cloud NGFW y Prisma Access quedan excluidos del aviso PAN-OS de 2026; esta exclusión no se extiende a todas las CVE. Una fecha estimada para el parche es distinta de la disponibilidad de una versión confirmada. [S03]

## 2. Responsabilidades de los controles y cobertura pendiente

| Control | Alcance principal | Controles complementarios |
|---|---|---|
| WAF | Solicitudes HTTP(S) a recursos asociados y coincidencias configuradas | Autenticación/autorización de aplicaciones, validación, inspección de cargas y restricciones del origen |
| NGFW/IPS | Sesiones de red que lo atraviesan y perfiles de seguridad configurados | Visibilidad TLS, protección de administración, aplicación de parches y enrutamiento bidireccional |
| GWLB/GWLBE | Inserción de dispositivos compatibles con GENEVE y distribución de flujos | Políticas de inspección del dispositivo, gestión de sesiones, capacidad y recuperación |
| Kubernetes NetworkPolicy | Conexiones de Pods aplicadas por un CNI compatible | Comprobaciones de hostNetwork/nodos/rutas locales y autenticación del servicio |
| mTLS/SPIFFE | Identidad del peer y protección del transporte | Autorización del servicio, validación de solicitudes y registros de acceso |
| Políticas de imágenes/admisión | Imágenes implementadas y configuración de cargas de trabajo | Detección en runtime, aplicación de parches y gestión de secretos |

La [lista de recursos WAF][S09] y la [documentación de GWLB][S24] establecen sus alcances. NetworkPolicy necesita un complemento que aplique las políticas; su API no proporciona TLS ni obliga a que todas las conexiones atraviesen una puerta de enlace común. [S34]

**La instalación de un dispositivo y la inspección de una solicitud requieren evidencias distintas.** Los criterios de aceptación propuestos establecen:

1. **Ruta**: ¿Esta solicitud atravesó realmente el WAF o firewall designado?
2. **Política**: ¿Qué regla, firma, política de descifrado y excepción se aplicaron?
3. **Resultado**: ¿Las decisiones de permitir/denegar y el comportamiento de la aplicación coinciden con lo previsto?

## 3. Primero, inventariar el tráfico

Use esta plantilla de modelado de amenazas, complete los principales, CIDR e ID de recursos reales y marque como no verificadas las rutas que no se hayan observado.

| Flujo | Rutas de entrada o salida que se investigarán | Control y evidencia |
|---|---|---|
| Usuario → web/API | CloudFront, ALB, balanceadores de carga/dominios/NodePorts adicionales | Asociación de Web ACL, solicitudes legítimas, solicitud de prueba inocua que debe bloquearse y resultado del acceso directo al origen |
| Operador → administración | PAN-OS/FortiGate, Panorama/FortiManager, API de EKS, GitOps | Ruta de administración de confianza, autenticación, registros de cambios administrativos/de políticas |
| Servidor de API → webhook | Plano de control y Service de admisión | Acceso del servidor de API, restricciones de cargas de trabajo normales, certificados y RBAC |
| Pod → externo | SNAT del nodo, NAT Gateway, TGW, IPv4/IPv6, proxies | Destinos permitidos/denegados, direcciones antes/después de la traducción y sesiones de firewall |
| Pod → Pod/base de datos | Mismo nodo, misma VPC, distinta VPC | Políticas de CNI, grupos de seguridad de la base de datos, autorización del servicio y pruebas bidireccionales |
| Pod → servicio de AWS | PrivateLink, endpoints de gateway de S3/DynamoDB y endpoints públicos | Políticas IAM/de recursos/de endpoint y ruta de conexión observada |
| CI/CD → clúster | Roles OIDC, registro, controlador GitOps | Firmas/digests, privilegio mínimo y cambios auditados |

La inspección central de TGW cubre **el tráfico enrutado a través de TGW**. No dé por sentado que incluye el tráfico de Pods en el mismo nodo, las rutas locales de VPC, el peering o las rutas de endpoints independientes. Compruebe conjuntamente el enrutamiento y el CNI. [S29] [S30] [S34]

## 4. Titularidad de la arquitectura

Para aplicaciones públicas, use [WAF y protección del origen](./14-waf-edge-api-security.md). Para la inspección saliente y entre VPC, use el [diseño de NGFW](./15-ngfw-paloalto-fortinet.md) y [GWLB/GENEVE](./16-gwlb-geneve-inspection.md). Dentro de la VPC, conecte estos controles con NetworkPolicy, grupos de seguridad y mTLS.

Ejemplo de reparto de responsabilidades:

| Responsable | Responsabilidad propuesta | Revisión de cambios |
|---|---|---|
| Equipo de aplicaciones | Autenticación, autorización, esquemas y cargas | Protección de aplicación detrás de excepciones de WAF |
| Equipo de plataforma | EKS, controladores, CNI, admisión y GitOps | Límites de permisos de Webhook, Pods y AWS |
| Equipo de redes | TGW, rutas de VPC, GWLBE, NAT y capacidad de dispositivos | Rutas de solicitud/respuesta, fallos de AZ y elusiones |
| Equipo de seguridad | Políticas de inspección, firmas, investigaciones y vencimiento de excepciones | Eficacia del bloqueo, evidencia de detección y recuperación |
| Responsable del incidente | Decisiones de contención, evidencia y recuperación | Impacto empresarial, sustitución de credenciales y nuevas pruebas |

Separe la autoridad para cambiar las rutas predeterminadas de la autoridad para conceder excepciones de inspección. Registre el alcance, motivo, vencimiento y responsable de recuperación de las omisiones de emergencia. Es una propuesta organizativa, no un hallazgo de una cuenta AWS inspeccionada.

## 5. Evidencia de detección

| Comportamiento | Correlacionar | Límite de una fuente aislada |
|---|---|---|
| Inicio de sesión de administrador seguido de creación de cuenta/política | Auditorías de autenticación/configuración del dispositivo, administrador central y registros de la ruta de administración | Un dispositivo comprometido puede ofrecer registros locales menos fiables |
| Eliminación de WAF/excepción u omisión de inspección | Cambios de AWS, asociaciones de Web ACL, cambios de ruta/grupo de seguridad y acceso a la aplicación | Cero bloqueos no demuestra que la aplicación de controles esté funcionando |
| Compromiso de controlador seguido de acceso a Secrets | Auditoría de Kubernetes, RBAC del controlador y comportamiento en runtime | Los registros de acceso web no cubren todos los ataques a webhooks |
| Sospecha de exfiltración | Observaciones de CNI, sesiones de firewall, direcciones previas a NAT y auditoría de API de aplicación/AWS | VPC Flow Logs no contienen las cargas de aplicación ni resultados de autorización |
| Reingreso después de aplicar parches | Cuentas de administrador/VPN, diferencias de configuración y uso de credenciales | Los números de versión no demuestran que se haya eliminado el acceso persistente |

Fortinet documenta la creación de administradores y los cambios de configuración. EKS documenta que Flow Logs contiene metadatos y que atribuir el tráfico puede ser difícil cuando cambian las direcciones de Pods. [S05] [S33]

La detección de amenazas de GuardDuty, la gestión de vulnerabilidades de Inspector, la exposición/correlación de Security Hub y las comprobaciones de configuración de CSPM tienen propósitos distintos. Verifique la cobertura de los servicios que ya utiliza y luego correlacione por tiempo e identidad del recurso los registros de red, dispositivos y aplicaciones. Consulte [prácticas de seguridad de EKS](./06-eks-security-best-practices.md) para obtener detalles sobre los servicios.

## 6. Respuesta ante un compromiso sospechado

NIST SP 800-61r3 conecta la detección, la respuesta y la recuperación con una gestión de riesgos más amplia. El siguiente procedimiento para dispositivos/EKS es una propuesta operativa de esta guía. [S08]

1. **Clasificar**: establezca el producto, la rama, la función, la exposición y el alcance de la investigación afectados. Distinga los recursos vulnerables de aquellos con evidencia de compromiso.
2. **Preservar evidencia**: registre horas UTC, revisiones de configuración, cuentas de administrador/VPN, registros de autenticación/sistema/amenazas y cambios en la nube. Contenga al mismo tiempo si retrasar la contención aumentaría el daño; documente la decisión.
3. **Contener**: restrinja las rutas de administración y las cargas afectadas mientras identifica las dependencias de plano de control, DNS, registro y recuperación aprobada.
4. **Eliminar el acceso**: siga los procedimientos del proveedor para cuentas no autorizadas, ajustes y cambios en el sistema de archivos. Cuando sea necesario, reconstruya a partir de imágenes verificadas y una configuración cuya limpieza se haya verificado; no restaure a ciegas ajustes sospechosos.
5. **Sustituir secretos**: según la exposición, revise las credenciales, certificados y sesiones de administrador/VPN/LDAP/AD/API/nube. Cambiar la contraseña de un firewall no basta.
6. **Demostrar la recuperación**: vuelva a probar el acceso de administración denegado, las funciones de negocio legítimas, las solicitudes de prueba inocuas que deben bloquearse, la salida, los fallos de AZ y la recopilación de registros.
7. **Mejorar**: analice las causas, la duración de la exposición, las excepciones, los retrasos de detección y los permisos de cambio; actualice los controles y los playbooks.

Fortinet recomienda tratar el sistema/configuración como comprometido cuando se confirman indicadores, restaurar o auditar la configuración y rotar las credenciales conectadas. El análisis de persistencia también exige revisar la configuración. [S05] [S07]

## 7. Secuencia de adopción y criterios de finalización

El siguiente plan de ejecución se puede adaptar; no es un SLA del proveedor ni un plazo de corrección de incidentes.

| Etapa | Trabajo | Evidencia de finalización |
|---|---|---|
| Primero | Inventariar la administración pública, ingress retirado, CVE explotadas activamente y elusiones de origen | Registros de activos/exposición/rama afectada/responsable y acciones correctivas |
| Etapa 1 | Validar los registros/reglas WAF, la detección de cambios administrativos y los límites de webhook/Pod | Resultados de permitir/denegar e ID de políticas efectivas |
| Etapa 2 | Inspección saliente/entre VPC, PoC de Palo Alto/Fortinet y rutas GWLB simétricas | Capturas de solicitud/respuesta, ubicación de NAT y experimentos de fallo |
| Etapa 3 | Capacidad, actualizaciones, recuperación y ciclo de vida de excepciones | Mediciones de SLO, ejercicios de recuperación y procedimientos de cambio revisados |

No use únicamente el porcentaje de bloqueos. Realice el seguimiento conjunto de la **cobertura de rutas de inspección, pruebas de elusión del origen, cambios administrativos no autorizados, registros faltantes, tiempo de recuperación y errores en tráfico legítimo**. No afirme cifras de rendimiento ni disponibilidad antes de medirlas.

## Seguir aprendiendo

- [WAF, seguridad de borde y API](./14-waf-edge-api-security.md)
- [NGFW de Palo Alto y Fortinet](./15-ngfw-paloalto-fortinet.md)
- [Inspección GWLB y GENEVE](./16-gwlb-geneve-inspection.md)
- [Cuestionario del capítulo](../quizzes/security/13-defense-in-depth-incident-response-quiz.md)

## Referencias y base de investigación

Fuentes primarias consultadas el 15-10-2026. Antes de hacer cambios, vuelva a comprobar los avisos y las restricciones de la rama/producto seleccionados.

- [S01: Kubernetes: CVE-2025-1974][S01]
- [S02: Kubernetes: comunicado sobre el retiro de ingress-nginx][S02]
- [S03: Palo Alto: CVE-2026-0322][S03]
- [S04: Palo Alto: CVE-2025-0108][S04]
- [S05: Fortinet: análisis del abuso de SSO en FortiOS][S05]
- [S06: CISA: catálogo de vulnerabilidades explotadas conocidas][S06]
- [S07: Fortinet: análisis de la actividad de actores de amenazas][S07]
- [S08: NIST SP 800-61r3][S08]
- [S09: AWS WAF: asociar una web ACL][S09]
- [S24: AWS: Gateway Load Balancers][S24]
- [S29: AWS: inspección centralizada con GWLB y TGW][S29]
- [S30: AWS: escenarios de NAT Gateway][S30]
- [S33: EKS: seguridad de red][S33]
- [S34: Kubernetes: políticas de red][S34]

[S01]: https://kubernetes.io/blog/2025/03/24/ingress-nginx-cve-2025-1974/
[S02]: https://kubernetes.io/blog/2026/01/29/ingress-nginx-statement/
[S03]: https://security.paloaltonetworks.com/CVE-2026-0322
[S04]: https://security.paloaltonetworks.com/CVE-2025-0108
[S05]: https://www.fortinet.com/blog/psirt-blogs/analysis-of-sso-abuse-on-fortios
[S06]: https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json
[S07]: https://www.fortinet.com/blog/psirt-blogs/analysis-of-threat-actor-activity
[S08]: https://csrc.nist.gov/pubs/sp/800/61/r3/final
[S09]: https://docs.aws.amazon.com/waf/latest/developerguide/web-acl-associating-aws-resource.html
[S24]: https://docs.aws.amazon.com/elasticloadbalancing/latest/gateway/gateway-load-balancers.html
[S29]: https://aws.amazon.com/blogs/networking-and-content-delivery/centralized-inspection-architecture-with-aws-gateway-load-balancer-and-aws-transit-gateway/
[S30]: https://docs.aws.amazon.com/vpc/latest/userguide/nat-gateway-scenarios.html
[S33]: https://docs.aws.amazon.com/eks/latest/best-practices/network-security.html
[S34]: https://kubernetes.io/docs/concepts/services-networking/network-policies/
