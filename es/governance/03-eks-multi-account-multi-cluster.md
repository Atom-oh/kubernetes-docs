# Arquitectura de EKS multicuenta y multiclúster

> **Última actualización**: 12 de octubre de 2026

## 1. Enfoques para consolidar clústeres

Hay cuatro enfoques generales para alojar en EKS cargas de trabajo de varios equipos o dominios.

| Enfoque | Configuración |
|---|---|
| Un único EKS central | Todas las cargas de trabajo en un clúster |
| EKS central por entorno | Un clúster para producción y otro para no producción |
| EKS por dominio | Un clúster dedicado por dominio |
| **Compartido + dedicado** | Cargas de trabajo generales en un clúster compartido; solo las cargas de trabajo con requisitos estrictos de inquilino/cuota/SLO obtienen un clúster dedicado |

Compartido + dedicado es un posible punto de partida. Los umbrales siguientes son ejemplos operativos locales, no criterios de separación obligatorios de AWS. Distingue las cuotas predeterminadas de las aplicadas y evalúa conjuntamente los SLO, el crecimiento y la capacidad operativa.

| Señal | Cómo medirla | Umbral de separación |
|---|---|---|
| Cantidad de grupos de nodos administrados | API de EKS | 25 / 30 |
| Cantidad de entradas de acceso | API de EKS | 2,000 / 3,000 |
| Limitación de la API del plano de control | CloudWatch, registros 429 | Respuestas 429 sostenidas |
| Tamaño de etcd / cantidad de objetos | Métricas del plano de control expuestas por la versión de EKS objetivo e inventario de objetos | Verifica la disponibilidad de métricas y las directrices antes de configurar alertas |
| NAU (Network Address Usage) por VPC | Consola de VPC / CloudWatch | 50,000 / 64,000 (o 200,000 / 256,000) |
| Radio de impacto de las actualizaciones | Cantidad de CUJ implementados en el clúster | Considera separar si hay 2 o más CUJ |
| Conflictos en la cadencia de versiones de add-ons | Divergencia en los requisitos de versión de add-ons por equipo | Separa cuando surjan requisitos incompatibles |

Superar un umbral activa una revisión. Compara el costo de aumentar cuotas, limpiar recursos y particionar; separa los clústeres mediante un plan validado con procedimientos de reversión.

## 2. Entorno de ejecución EKS A/B: dividir el radio de impacto entre dos clústeres

Implementar el mismo CUJ (trayectoria crítica del usuario) en dos clústeres EKS independientes, de modo que, si uno falla, el otro siga atendiendo tráfico, suele denominarse «entorno de ejecución EKS A/B». **No es un patrón recomendado oficialmente por AWS; es una hipótesis de trabajo que la organización debe validar por su cuenta.** Para mejorar realmente la disponibilidad, primero hay que cumplir las condiciones siguientes.

### Primero, define qué quieres proteger

El plano de control administrado de EKS es multizona; ARC zonal shift/autoshift actúa en el plano de datos. A/B puede aislar fallos específicos de un clúster, como los siguientes. Las dependencias compartidas de VPC, DNS, cuenta, región y datos siguen siendo dominios de fallo compartidos; tener dos clústeres por sí solo no garantiza resiliencia entre zonas o regiones.

- Actualizaciones fallidas del clúster
- Regresiones de add-ons (CNI/CoreDNS/CSI)
- Errores de webhooks de admisión
- Despliegues defectuosos de políticas para todo el clúster
- Limitación de la API del plano de control

Documenta explícitamente esta lista de fallos y usa como criterio de éxito de la prueba de concepto: «¿este fallo queda realmente contenido en un solo lado después de separar en A/B?». No se puede verificar una afirmación abstracta de «mayor disponibilidad».

<span id="coredns-is-the-most-common-single-point-of-failure"></span>

### Comprueba los modos de fallo compartidos y la capacidad de DNS

DNS es una dependencia compartida: comprueba las réplicas, su distribución entre zonas de disponibilidad y la capacidad. Sin datos de incidentes, no clasifiques CoreDNS como el punto único de fallo más frecuente. Para Auto Mode y los nodos mixtos, identifica primero la ruta DNS real.

- Si `replicaCount` y `topologySpreadConstraints` realmente distribuyen las réplicas entre zonas de disponibilidad
- Si se aplica el escalado automático del add-on CoreDNS (`{"autoScaling":{"enabled":true}}`) o un HPA/cluster-proportional-autoscaler
- Los cambios de QPS/latencia cuando se elimina una zona de disponibilidad

**Los servicios link-local de EC2 comparten una cuota de 1,024 paquetes por segundo entre el tráfico que incluye DNS, IMDS y NTP.** Comprueba el límite de la ENI de DNS de VPC y las métricas reales de ENA `linklocal_allowance_exceeded`. Evalúa el almacenamiento en caché y la ubicación de las réplicas de DNS; la densidad de Pods por sí sola no demuestra la causa de los fallos de DNS.

### ARC zonal shift puede causar interrupciones si no aprovisionaste capacidad adicional por adelantado

La documentación de AWS lo advierte explícitamente. Cuando se produce un cambio zonal, ocurre automáticamente lo siguiente.

1. Todos los nodos de la zona de disponibilidad se marcan como no programables (no se les asignan Pods nuevos)
2. Se detiene el reequilibrio entre zonas de disponibilidad de los grupos de nodos administrados
3. Se quitan de EndpointSlice los Pods de esa zona
4. No se terminan ni desalojan los nodos/Pods (vuelven inmediatamente en cuanto se levanta el cambio)
5. Los ALB/NLB registrados con ARC enrutan solo a zonas de disponibilidad en buen estado

**Comportamiento de seguridad ante fallos**: si los endpoints de una carga de trabajo solo existen en la zona de disponibilidad afectada, EKS sigue enviando tráfico a esa zona de todos modos. Es decir, **una carga de trabajo implementada en una sola zona de disponibilidad no queda protegida por el cambio zonal**.

También hay que comprobar las siguientes limitaciones técnicas:

- **No funciona en EKS Fargate.**
- La compatibilidad con Karpenter autoadministrado requiere **la versión 1.12 o posterior.**
- EKS Auto Mode no necesita configuración adicional aparte de habilitar zonal shift en el clúster. Entonces deja de aprovisionar nodos nuevos en la zona afectada, detiene interrupciones voluntarias como la consolidación que afectaría a esa zona y evita lanzar capacidad para Pods cuyas restricciones estrictas de programación la seleccionen.
- Evalúa las cargas de trabajo con estado según su backend de almacenamiento. Un PV de EBS pertenece a una zona y no se puede conectar directamente en otra. No todos los PVC usan EBS; EFS y otros backends tienen diferentes comportamientos de disponibilidad y recuperación.

> **Propuesta de diseño**: Valida el comportamiento N-1 de cada servicio, DNS y almacenamiento antes de habilitar autoshift. Los endpoints de una sola zona pueden conservarse por el mecanismo de seguridad ante fallos, así que una prueba práctica no necesariamente los detendrá. Ese mecanismo tampoco garantiza el servicio desde una zona de disponibilidad afectada.

### Riesgos de los cálculos del multiplicador de capacidad aprovisionada previamente

El cálculo «2 zonas de disponibilidad requiere aproximadamente 2x; 3 zonas (con base N-1) requiere aproximadamente 1.5x de capacidad aprovisionada previamente» es aritméticamente correcto, pero es fácil equivocarse de tres maneras.

1. **Retraso al agregar nodos**: los Pods placeholder y la prioridad pueden reservar la capacidad existente, pero no eliminan el tiempo de aprovisionamiento de nodos, descarga de imágenes ni inicio de aplicaciones.
2. **Riesgo de que la demanda de otros clientes limite la nueva capacidad en la zona de disponibilidad sana**: no es una especulación; la documentación de AWS menciona explícitamente el «riesgo de limitaciones de capacidad de cómputo que impidan agregar nodos nuevos a una zona de disponibilidad sana durante una afectación zonal».
3. **Dependencias y ubicación en zonas de disponibilidad**: cada salto necesario del CUJ debe seguir siendo accesible y tener capacidad suficiente desde las zonas supervivientes. Combina la distribución de topología, la afinidad y el fallback entre zonas según sea necesario; prueba si una afinidad estricta bloquea la recuperación.

### Optimización de costos entre zonas de disponibilidad

Sigue este orden: medir → optimizar → comparar el costo residual.

1. Identifica las rutas de mayor costo usando Flow Logs y la correspondencia entre ENI y zonas de disponibilidad (CUR por sí solo no permite identificar el par de zonas de origen y destino).
2. Evalúa el enrutamiento dentro de una misma zona, `spec.trafficDistribution` del Service, la distribución de topología, los destinos IP del ALB, la localidad de NAT/endpoints y la localidad de los datos. El campo en sí no cambió de nombre. Verifica la compatibilidad y las puertas de funcionalidad para `PreferClose`, `PreferSameZone` y `PreferSameNode` en la versión de Kubernetes/EKS objetivo.
3. Compara el costo residual entre zonas después de aplicar estas medidas.

La transferencia de datos regional entre zonas de ALB no tiene un cargo adicional por transferencia, así que deshabilitarla no implica ahorro. Deshabilitarla por grupo de destinos elimina la persistencia de sesiones por destino y la compatibilidad con destinos Lambda. Una zona de disponibilidad vacía puede devolver 503; una zona poblada cuyos destinos no estén sanos se rige por las condiciones de failover de DNS/enrutamiento. Distingue estos casos y conserva el valor predeterminado habilitado cuando no se pueda garantizar capacidad por zona.

### La estrategia de actualización está directamente relacionada con la razón de A/B

Si la razón real para ejecutar un entorno de ejecución EKS A/B es aislar actualizaciones, debes formalizar lo siguiente:

- El desfase de versiones permitido entre los clústeres A y B
- Una regla para actualizar siempre primero uno de los lados
- Si se utiliza soporte extendido

Sin esto, A/B no es más que «dos clústeres» y la redundancia pierde su propósito.

### La cantidad de zonas de disponibilidad de los nodos de trabajo y las subredes del plano de control son conceptos distintos

Crear un clúster requiere subredes en al menos dos zonas de disponibilidad distintas, pero los nodos de trabajo pueden estar en una sola. Esto significa que EKS no prohíbe una «configuración de nodos de trabajo en una sola zona»; evalúala por separado de la excepción sobre zonal shift mencionada antes.

## 3. Celda de carga de trabajo completa: alternativa para un aislamiento más fuerte

Si necesitas un aislamiento más fuerte del que proporciona un entorno de ejecución EKS A/B, puedes separar y replicar conjuntamente la entrada, el cómputo, los datos y las dependencias necesarias como una unidad «Cell», conteniendo el radio de impacto dentro de la celda. La partición, la coherencia, la capacidad y los costos operativos aumentan considerablemente, así que esto es realista **solo para cargas de trabajo que admitan partición y replicación de datos independientes.**

## Siguiente

El diseño de disponibilidad de EKS no se puede considerar aparte de la estructura de VPC que hay debajo → [VPC compartida y conectividad](./04-shared-vpc-and-connectivity.md)

## Referencias

- [Cuotas de EKS](https://docs.aws.amazon.com/general/latest/gr/eks.html#limits_eks)
- [Subredes de EKS y Multi-AZ](https://docs.aws.amazon.com/eks/latest/best-practices/subnets.html)
- [Optimización de costos de red en EKS](https://docs.aws.amazon.com/eks/latest/best-practices/cost-opt-networking.html)
- [Zonal shift de EKS](https://docs.aws.amazon.com/eks/latest/userguide/zone-shift.html)
- [Aislamiento de inquilinos de EKS](https://docs.aws.amazon.com/eks/latest/best-practices/tenant-isolation.html)
- [Estabilidad estática con zonas de disponibilidad](https://aws.amazon.com/builders-library/static-stability-using-availability-zones/)
- [Well-Architected: Multi-AZ](https://docs.aws.amazon.com/wellarchitected/latest/framework/rel_fault_isolation_multiaz_region_system.html)
- [Atributos de grupos de destinos de ALB](https://docs.aws.amazon.com/elasticloadbalancing/latest/application/edit-target-group-attributes.html)
- [Estado de los destinos de grupos de ALB](https://docs.aws.amazon.com/elasticloadbalancing/latest/application/load-balancer-target-groups.html#target-group-health)
- [Transferencia de datos entre zonas de ALB](https://aws.amazon.com/elasticloadbalancing/faqs/)
- [Cuotas de DNS de Amazon](https://docs.aws.amazon.com/vpc/latest/userguide/AmazonDNS-concepts.html)
- [Distribución del tráfico de Services de Kubernetes](https://kubernetes.io/docs/concepts/services-networking/service/#traffic-distribution)
