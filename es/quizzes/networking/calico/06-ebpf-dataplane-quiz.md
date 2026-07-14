# Cuestionario sobre el dataplane eBPF

> **Documento relacionado**: [eBPF Dataplane](../../../networking/calico/06-ebpf-dataplane.md)
> **Última actualización**: February 22, 2026

## Cuestionario

1. ¿Cuál es la versión mínima de kernel de Linux requerida para el dataplane eBPF de Calico?
   - A) 4.15+
   - B) 5.0+
   - C) 5.3+
   - D) 5.10+

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) 5.3+**

**Explicación:**
El dataplane eBPF de Calico requiere una versión mínima de kernel 5.3. Sin embargo, se recomienda kernel 5.8+ para un rendimiento óptimo y compatibilidad completa con funciones, incluido BTF (BPF Type Format), que permite mejores capacidades de depuración e introspección.

</details>

2. ¿Qué mejora de rendimiento se puede esperar normalmente al cambiar de iptables al dataplane eBPF en Calico?
   - A) Aumento del rendimiento de 5-10%
   - B) Aumento del rendimiento de 20-40%
   - C) Aumento del rendimiento de 50-60%
   - D) Aumento del rendimiento de 100%

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Aumento del rendimiento de 20-40%**

**Explicación:**
El dataplane eBPF normalmente proporciona una mejora de rendimiento de 20-40% respecto a iptables. Esto se debe a que eBPF procesa paquetes directamente en el kernel sin la sobrecarga de recorrer cadenas de iptables, que puede volverse significativa a medida que aumenta el número de reglas.

</details>

3. ¿Qué significa BTF y por qué es importante para el dataplane eBPF de Calico?
   - A) Binary Transfer Format - para la codificación de paquetes de red
   - B) BPF Type Format - para depuración y compatibilidad con CO-RE
   - C) Byte Translation Function - para la conversión de direcciones
   - D) Block Transfer Filter - para la limitación de velocidad

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) BPF Type Format - para depuración y compatibilidad con CO-RE**

**Explicación:**
BTF (BPF Type Format) proporciona información de tipo para programas BPF. Permite la compatibilidad con CO-RE (Compile Once, Run Everywhere), lo que permite que los programas eBPF se ejecuten en diferentes versiones de kernel sin recompilación. BTF también permite mejores capacidades de depuración con herramientas como bpftool.

</details>

4. ¿Qué es Direct Server Return (DSR) en el contexto del dataplane eBPF de Calico?
   - A) Un método para que los pods contacten directamente con el servidor de API de Kubernetes
   - B) Una optimización de balanceo de carga en la que el tráfico de retorno evita el balanceador de carga
   - C) Una técnica de resolución DNS para descubrimiento de servicios
   - D) Un patrón de acceso al almacenamiento para volúmenes persistentes

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Una optimización de balanceo de carga en la que el tráfico de retorno evita el balanceador de carga**

**Explicación:**
Direct Server Return (DSR) es una optimización de balanceo de carga en la que el tráfico de respuesta del servidor backend va directamente al cliente, evitando el nodo del balanceador de carga. Esto reduce la latencia y el consumo de ancho de banda del balanceador de carga, mejorando el rendimiento general del servicio.

</details>

5. ¿Qué es el balanceo de carga en el momento de conexión en el dataplane eBPF de Calico?
   - A) Balanceo de carga que ocurre cuando un nodo se une al clúster
   - B) Traducción de IP de Service realizada al establecer una conexión TCP
   - C) Un mecanismo de comprobación de estado para pods backend
   - D) Conmutación por error automática cuando se interrumpen las conexiones

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Traducción de IP de Service realizada al establecer una conexión TCP**

**Explicación:**
El balanceo de carga en el momento de conexión realiza la traducción de IP de Service a IP de pod en el momento en que se establece una conexión TCP, en lugar de hacerlo en cada paquete. Esto proporciona un balanceo de carga más eficiente y permite funciones como DSR, ya que el socket del cliente se conecta directamente al backend seleccionado.

</details>

6. Cuando se habilita el dataplane eBPF de Calico, ¿qué ocurre con kube-proxy?
   - A) kube-proxy continúa ejecutándose junto con eBPF
   - B) kube-proxy puede deshabilitarse, ya que eBPF proporciona una funcionalidad equivalente
   - C) kube-proxy se actualiza automáticamente para usar eBPF
   - D) kube-proxy gestiona IPv6 mientras eBPF gestiona IPv4

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) kube-proxy puede deshabilitarse, ya que eBPF proporciona una funcionalidad equivalente**

**Explicación:**
El dataplane eBPF de Calico puede reemplazar por completo a kube-proxy para el balanceo de carga de Service. Cuando se habilita el modo eBPF, kube-proxy puede deshabilitarse para evitar el procesamiento redundante y posibles conflictos. El dataplane eBPF gestiona directamente los servicios ClusterIP, NodePort y LoadBalancer.

</details>

7. ¿Para qué se utilizan los mapas BPF en el dataplane eBPF de Calico?
   - A) Almacenar datos de ubicación geográfica para geo-routing
   - B) Almacenar datos de estado y configuración compartidos entre kernel y espacio de usuario
   - C) Mapear nombres DNS a direcciones IP
   - D) Crear diagramas de topología de red

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Almacenar datos de estado y configuración compartidos entre kernel y espacio de usuario**

**Explicación:**
Los mapas BPF son estructuras de datos clave-valor que almacenan datos de estado y configuración accesibles tanto por programas eBPF que se ejecutan en el kernel como por aplicaciones de espacio de usuario. Calico utiliza mapas BPF para almacenar el estado de seguimiento de conexiones, reglas de políticas, endpoints de Service y otros metadatos de red.

</details>

8. ¿Cuál es la diferencia entre los puntos de enlace XDP y TC para los programas eBPF?
   - A) XDP procesa paquetes antes en la pila de red que TC
   - B) TC procesa paquetes antes en la pila de red que XDP
   - C) XDP es solo para entrada; TC es solo para salida
   - D) No hay diferencia; son alias

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A) XDP procesa paquetes antes en la pila de red que TC**

**Explicación:**
XDP (eXpress Data Path) procesa paquetes en el punto más temprano posible de la pila de red, incluso antes de que el kernel asigne un sk_buff. Los hooks TC (Traffic Control) procesan paquetes más tarde, después de que se asigna el sk_buff. XDP proporciona el máximo rendimiento, pero tiene funcionalidad limitada, mientras que TC ofrece más funciones con un ligero coste de rendimiento.

</details>

9. ¿Qué configuración de FelixConfiguration habilita el dataplane eBPF en Calico?
   - A) dataplaneMode: eBPF
   - B) bpfEnabled: true
   - C) useEBPF: yes
   - D) felixBackend: ebpf

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) bpfEnabled: true**

**Explicación:**
El dataplane eBPF se habilita configurando `bpfEnabled: true` en el recurso FelixConfiguration. También se pueden configurar en el mismo recurso opciones específicas adicionales de eBPF, como `bpfExternalServiceMode`, `bpfKubeProxyIptablesCleanupEnabled` y otras.

</details>

10. ¿Qué controla la configuración bpfExternalServiceMode en Calico?
    - A) Cómo los pods acceden a servicios externos fuera del clúster
    - B) Cómo los clientes externos acceden a servicios NodePort y LoadBalancer
    - C) Qué servidores DNS externos se utilizan para el descubrimiento de servicios
    - D) Modo de autenticación para acceso externo a la API

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Cómo los clientes externos acceden a servicios NodePort y LoadBalancer**

**Explicación:**
La configuración `bpfExternalServiceMode` controla cómo Calico gestiona el tráfico desde fuentes externas hacia servicios NodePort y LoadBalancer. Las opciones incluyen "Tunnel" (predeterminada, conserva la IP de origen mediante encapsulación) y "DSR" (Direct Server Return para mejorar el rendimiento).

</details>

11. ¿Qué herramienta se utiliza habitualmente para depurar e inspeccionar los programas y mapas eBPF de Calico?
    - A) tcpdump
    - B) bpftool
    - C) netstat
    - D) iptables-save

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) bpftool**

**Explicación:**
bpftool es la utilidad estándar para inspeccionar y depurar programas y mapas eBPF. Puede listar programas BPF cargados, volcar el contenido de mapas, mostrar estadísticas de programas y presentar información BTF. Es esencial para solucionar problemas del dataplane eBPF de Calico.

</details>

12. ¿Cuál es la secuencia recomendada para migrar de iptables al dataplane eBPF en Calico?
    - A) Habilitar eBPF inmediatamente en todos los nodos simultáneamente
    - B) Deshabilitar primero kube-proxy y luego habilitar eBPF
    - C) Habilitar eBPF en Calico, verificar su funcionamiento y luego deshabilitar kube-proxy
    - D) Reinstalar Calico desde cero con eBPF habilitado

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Habilitar eBPF en Calico, verificar su funcionamiento y luego deshabilitar kube-proxy**

**Explicación:**
La ruta de migración recomendada es: 1) Habilitar el dataplane eBPF en FelixConfiguration, 2) Verificar que la red y los servicios funcionen correctamente, 3) Deshabilitar kube-proxy una vez confirmado el funcionamiento de eBPF. Esto permite una reversión segura si se detectan problemas durante la migración.

</details>
