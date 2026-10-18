# 8. Proyecto final: de los fallos de un servicio web a los contenedores y la nube

> **Entorno de referencia del curso**: Ubuntu Server 24.04 LTS, con una ruta alternativa para Rocky Linux 9
>
> **Última actualización**: 15 de septiembre de 2026

**Requisitos previos:** [Lecciones 1–7](README.md#course-map), las direcciones de laboratorio de ambas máquinas virtuales, inicio de sesión SSH con una clave verificada y una regla TCP 8000 que permita el acceso desde el cliente del laboratorio. Detén primero el servidor web de la lección 7.

**Objetivos:** Registrar el estado correcto de un pequeño servicio web y luego reproducir, diagnosticar y recuperar fallos en distintas capas, de uno en uno. Después, aplica las mismas preguntas a Docker y Kubernetes. Reserva aproximadamente entre 3 y 4 horas.

## Tarea y estado correcto de referencia {#baseline}

La tarea consiste en que «el cliente lea `/health.txt` del servidor». No se requiere un framework web ni una cuenta en la nube.

**Consola A del servidor:**

```bash
LAB_WEB=$(mktemp -d /tmp/net-capstone.XXXXXX)
printf 'healthy\n' > "$LAB_WEB/health.txt"
timeout 300 python3 -m http.server 8000 \
  --bind 192.0.2.20 --directory "$LAB_WEB"
```

Cuando se agote el límite de cinco minutos, reinicia el servidor con el mismo comando. Comprueba la consola para no confundir un servidor detenido intencionalmente con un fallo de red. Deja únicamente el archivo del ejercicio en este directorio.

**Consola B del servidor:**

```bash
ip -br address
ip route get 192.0.2.10
sudo ss -ltnp 'sport = :8000'
```

**Cliente:**

```bash
ip route get 192.0.2.20
curl --disable --noproxy '*' --connect-timeout 2 --max-time 5 \
  -i http://192.0.2.20:8000/health.txt
curl --disable --noproxy '*' --connect-timeout 2 --max-time 5 \
  --resolve lesson.test:8000:192.0.2.20 \
  -i http://lesson.test:8000/health.txt
```

Ambas rutas deben usar las NIC del laboratorio; el listener debe ser `192.0.2.20:8000`, y ambas solicitudes deben devolver HTTP 200 con `healthy` en el cuerpo. `--resolve` proporciona **una asignación de dirección host/puerto para esta invocación de curl**. No cambia el DNS del sistema ni el de otras aplicaciones.

Si falla el estado de referencia, primero comprueba la configuración y las reglas de las lecciones 4–6. No introduzcas un fallo nuevo hasta que funcione el estado de referencia.

## Reproduce un fallo cada vez {#faults}

Empieza cada experimento desde el estado correcto de referencia y repite la solicitud correcta después de la recuperación. Las solicitudes normales de `curl` pueden devolver el código de salida 0 incluso con HTTP 404, así que lee la línea de estado HTTP. La automatización que deba tratar los errores HTTP como fallos puede seleccionar explícitamente una opción compatible, como `--fail-with-body`.

### A. Distingue la resolución de nombres de la conectividad IP

En el cliente, compara una solicitud sin `--resolve`.

```bash
getent ahostsv4 lesson.test
curl --disable --noproxy '*' --connect-timeout 2 --max-time 5 \
  -i http://lesson.test:8000/health.txt
```

Si no se registró `lesson.test` por separado, lo normal es que la resolución del nombre falle en este laboratorio. Si ya lo configuraste en `/etc/hosts` o en el DNS local, registra la asignación real en lugar de esperar un fallo. Comprueba si las solicitudes anteriores por IP y con `--resolve` funcionan en el mismo entorno.

**Diagnóstico:** Si funciona la solicitud por IP, pero falla la búsqueda del nombre, investiga primero la resolución de nombres. Esto no demuestra que haya fallado un servidor DNS específico ni que exista una interrupción general de Internet. **Recuperación:** Reutiliza la asignación de `--resolve` de la solicitud correcta; no hace falta sobrescribir el resolver del sistema para este experimento temporal.

### B. Error en la ruta de la aplicación

Desde el cliente, solicita un archivo inexistente.

```bash
curl --disable --noproxy '*' --connect-timeout 2 --max-time 5 \
  -i http://192.0.2.20:8000/missing.txt
```

**Diagnóstico:** Recibir HTTP 404 significa que la solicitud obtuvo una respuesta HTTP del servidor. No hay motivo para restablecer toda la configuración de rutas y firewall. Compara la ruta solicitada con el registro del servidor. **Recuperación:** Vuelve a solicitar `/health.txt`.

### C. Dirección de escucha incorrecta

Detén el servidor con Ctrl+C en la consola A del servidor. En **la misma terminal**, cambia solo su dirección de enlace.

```bash
timeout 300 python3 -m http.server 8000 \
  --bind 127.0.0.1 --directory "$LAB_WEB"
```

Consola B del servidor:

```bash
sudo ss -ltnp 'sport = :8000'
curl --disable --noproxy '*' --max-time 5 \
  -i http://127.0.0.1:8000/health.txt
```

Comprueba que falle la solicitud original del cliente a `192.0.2.20:8000`, mientras que funcione la solicitud de loopback del propio servidor. El comportamiento del firewall también influye en que el fallo aparezca como rechazo o timeout. La evidencia clave es que `ss` muestre el listener en `127.0.0.1`.

**Recuperación:** Pulsa Ctrl+C en la consola A y reinicia el comando correcto con `--bind 192.0.2.20`. El loopback de una máquina virtual no es el loopback de otra.

### D. Comprueba con evidencia una hipótesis sobre el firewall {#firewall-fault}

Usa **solo el administrador que seleccionaste en la lección 6**, desde la consola del hipervisor del servidor. Este fallo elimina únicamente el permiso TCP 8000 administrado por el curso. El permiso TCP 22, la denegación del laboratorio, las políticas predeterminadas, las asignaciones de zonas/perfiles y la NIC de administración permanecen intactos. Termina primero el experimento opcional con Fail2ban para que ningún cambio de bloqueo en segundo plano confunda esta prueba.

**Consola B del servidor, usuario normal:** vuelve a identificar ambas NIC mediante las direcciones MAC registradas en el hipervisor; no des por sentado que las variables de la lección 6 sigan definidas.

```bash
ip -br link
read -r -p 'Server lab NIC verified by MAC: ' LAB_IF
read -r -p 'Server management NIC verified by MAC: ' MGMT_IF
ip -4 -br address show dev "$LAB_IF"
ip -4 -br address show dev "$MGMT_IF"
ip -4 route
sudo ss -ltnp 'sport = :8000'
```

Verifica que la NIC del laboratorio tenga `.20/24`, que los nombres de las NIC sean distintos, que la administración no haya cambiado y que el listener correcto esté en `.20:8000`. Registra las reglas actuales como se indica más abajo. Si venció el temporizador del servidor, reinicia **solo** `timeout 300 python3 -m http.server 8000 --bind 192.0.2.20 --directory "${LAB_WEB:?missing existing web directory}"` en la consola A del servidor, con el directorio existente. No introduzcas al mismo tiempo el fallo de un servidor detenido.

**Cliente, usuario normal:** recupera de tus registros el directorio de claves habitual de la lección 5 y la cuenta normal del servidor. No crees una clave nueva ni omitas el registro de host verificado.

```bash
read -r -p 'Existing lesson-5 client key directory: ' SSH_LAB_DIR
read -r -p 'Normal account on the server: ' SERVER_USER
ls -l -- "${SSH_LAB_DIR:?missing key directory}/id_ed25519" \
  "${SSH_LAB_DIR:?missing key directory}/known_hosts"
```

Define una vez esta función breve de shell en esa terminal del cliente. Al llamar a `check_lab_ssh`, se abre una conexión SSH **nueva**, se muestran la cuenta y la conexión remotas y se vuelve al cliente; no se crea ningún archivo ni servicio.

```bash
check_lab_ssh() {
  ssh -F /dev/null -b 192.0.2.10 \
    -i "${SSH_LAB_DIR:?missing key directory}/id_ed25519" \
    -o "UserKnownHostsFile=${SSH_LAB_DIR:?missing key directory}/known_hosts" \
    -o StrictHostKeyChecking=yes -o IdentitiesOnly=yes \
    -o PreferredAuthentications=publickey \
    -o PasswordAuthentication=no -o KbdInteractiveAuthentication=no \
    -o ControlMaster=no -o ControlPath=none -o ControlPersist=no \
    -o BatchMode=no -o ConnectTimeout=5 \
    "${SERVER_USER:?missing account}@192.0.2.20" \
    'whoami; printf "%s\n" "$SSH_CONNECTION"'
}
check_lab_ssh
```

**Se permite que aparezca el aviso para introducir la frase de contraseña de la clave privada**; no es necesario tener un agente desbloqueado. Se deshabilita el uso alternativo de la contraseña de la cuenta remota. `-F /dev/null` evita configuraciones irrelevantes del cliente y deshabilitar la multiplexación impide reutilizar una conexión autenticada anterior. Se espera la cuenta normal y una conexión del puerto 22 desde `.10` hasta `.20`. Si falla esta comprobación **previa al fallo** o la solicitud HTTP correcta, detente antes de cambiar cualquier regla. Conserva y vuelve a comprobar también cualquier ruta SSH de administración que se necesite por separado.

#### UFW: cambia únicamente el permiso HTTP guardado y aplicado

**Consola B del servidor Ubuntu, con sudo:**

```bash
sudo ufw status numbered
sudo ufw show added
```

Continúa solo si UFW está activo y se cumplen las tres reglas del curso de la lección 6, en este orden: **1: permiso TCP 22 de `.10` a `.20` por `LAB_IF`; 2: permiso TCP 8000 independiente; 3: denegación TCP `22,8000` para la misma interfaz y destino**. Registra sus especificaciones completas. Si todavía existe un permiso combinado `22,8000` anterior o el orden es distinto, reconcilia primero la configuración de la lección 6; eliminar un puerto no revierte una regla multipuerto.

Elimina solo HTTP:

```bash
sudo ufw delete allow in on "$LAB_IF" proto tcp \
  from 192.0.2.10 to 192.0.2.20 port 8000
sudo ufw status numbered
sudo ufw show added
```

Confirma que el permiso TCP 22 siga primero y que la denegación del laboratorio haya quedado segunda. Esto cambia el estado de UFW tanto guardado como aplicado. No alteres esas dos reglas ni las políticas predeterminadas. Ahora realiza las **comprobaciones durante el fallo** de abajo.

**Restauración desde la misma consola de Ubuntu:** verifica que la denegación siga segunda y vuelve a insertar HTTP en la posición 2, **antes de esa denegación**:

```bash
sudo ufw insert 2 allow in on "$LAB_IF" proto tcp \
  from 192.0.2.10 to 192.0.2.20 port 8000 comment 'network-beginner-http'
sudo ufw status numbered
sudo ufw show added
```

Se espera que vuelvan al orden original: permiso SSH → permiso HTTP → denegación del laboratorio, con el ámbito original de origen, interfaz y destino. Si se agrega un permiso después de la denegación, HTTP seguirá bloqueado; la reversión de la eliminación también requiere restaurar la posición. Si otra regla cambió las posiciones, detente y restablece el orden registrado en lugar de usar un número obsoleto. Continúa con las comprobaciones posteriores a la recuperación de abajo.

#### firewalld: elimina solo la regla HTTP del tiempo de ejecución y conserva la política guardada

**Consola B del servidor Rocky, usuario normal para asignaciones, sudo para consultas del firewall:**

```bash
RULE22='rule family="ipv4" source address="192.0.2.10/32" destination address="192.0.2.20/32" port port="22" protocol="tcp" accept'
RULE8000='rule family="ipv4" source address="192.0.2.10/32" destination address="192.0.2.20/32" port port="8000" protocol="tcp" accept'
sudo firewall-cmd --get-zone-of-interface="$LAB_IF"
sudo firewall-cmd --get-zone-of-interface="$MGMT_IF"
sudo firewall-cmd --zone=network-beginner --list-all
sudo firewall-cmd --permanent --zone=network-beginner --list-all
sudo firewall-cmd --zone=network-beginner --query-rich-rule="$RULE22"
sudo firewall-cmd --permanent --zone=network-beginner --query-rich-rule="$RULE22"
sudo firewall-cmd --zone=network-beginner --query-rich-rule="$RULE8000"
sudo firewall-cmd --permanent --zone=network-beginner --query-rich-rule="$RULE8000"
```

Se espera que solo la NIC del laboratorio esté en `network-beginner`, se conserve la zona original de administración y las cuatro consultas devuelvan `yes`. Esto requiere las reglas permanentes conservadas de la lección 6, no la prueba temporal que expira. Registra ambas configuraciones e inspecciona cualquier política más amplia que aún pudiera permitir HTTP.

Elimina **solo la regla HTTP del tiempo de ejecución**:

```bash
sudo firewall-cmd --zone=network-beginner --remove-rich-rule="$RULE8000"
sudo firewall-cmd --zone=network-beginner --query-rich-rule="$RULE8000"
sudo firewall-cmd --permanent --zone=network-beginner --query-rich-rule="$RULE8000"
sudo firewall-cmd --zone=network-beginner --query-rich-rule="$RULE22"
sudo firewall-cmd --permanent --zone=network-beginner --query-rich-rule="$RULE22"
```

Se espera `no`, `yes`, `yes`, `yes`; `no` devuelve un estado distinto de cero y aquí es lo esperado. Ejecuta las comprobaciones durante el fallo. No recargues, reinicies ni uses `--runtime-to-permanent`: una recarga volvería a activar la regla HTTP guardada y copiar el estado del tiempo de ejecución a la configuración permanente guardaría el fallo de forma involuntaria.

**Restauración desde la misma consola de Rocky**, sin recarga global ni cambio permanente:

```bash
sudo firewall-cmd --zone=network-beginner --add-rich-rule="$RULE8000"
sudo firewall-cmd --zone=network-beginner --query-rich-rule="$RULE8000"
sudo firewall-cmd --permanent --zone=network-beginner --query-rich-rule="$RULE8000"
sudo firewall-cmd --zone=network-beginner --query-rich-rule="$RULE22"
sudo firewall-cmd --permanent --zone=network-beginner --query-rich-rule="$RULE22"
```

Las cuatro consultas deberían volver a indicar `yes`. Compara las listas del tiempo de ejecución y permanentes con el estado de referencia registrado: las reglas guardadas nunca cambiaron y la regla HTTP del tiempo de ejecución se restauró con el mismo ámbito. Si cambió inesperadamente la política guardada, investígalo comparándola con ese registro; no la sobrescribas en bloque.

#### Comprobaciones durante el fallo y después de la recuperación

**Cliente, usuario normal, en la misma terminal:** ejecuta este par **después de eliminar HTTP y otra vez después de restaurarlo**, además de la comprobación previa al fallo.

```bash
check_lab_ssh
curl --disable --noproxy '*' --connect-timeout 2 --max-time 5 \
  -i http://192.0.2.20:8000/health.txt
```

Durante el fallo, la nueva comprobación SSH que solo usa la clave debe seguir funcionando. HTTP debería fallar de acuerdo con la política registrada del curso, mientras el listener del servidor siga en `.20:8000`. Si falla SSH, restaura solo el permiso HTTP que se eliminó desde la consola del servidor, compara la regla/ruta SSH que no se cambió y detente: no has demostrado un fallo exclusivo de HTTP. Si HTTP aún funciona, inspecciona otras reglas de permiso coincidentes, el comportamiento de la zona/política predeterminada, el listener y la evidencia de los paquetes; no afirmes que está bloqueado solo porque se eliminó una regla.

Después de la recuperación, exige una nueva comprobación SSH correcta con la clave y HTTP 200 con `healthy`. En la consola B del servidor, repite `sudo ss -ltnp 'sport = :8000'`, las consultas/listados de reglas pertinentes, `ip -4 -br address show dev "$MGMT_IF"` e `ip -4 route`; compara los resultados con el registro previo al fallo y vuelve a comprobar el acceso de administración requerido. Registra por separado las observaciones de las tres etapas. Estas instrucciones no afirman que se hayan ejecutado comandos en una máquina invitada al redactar el documento.

## Informe y criterios para completar el ejercicio {#capstone-report}

Registra las direcciones del laboratorio y los resultados, no contraseñas, claves privadas ni tráfico real de usuarios.

| Campo | Qué registrar |
|---|---|
| Entorno | Distribución, kernel, NIC del laboratorio, direcciones del cliente/servidor y administrador del firewall |
| Estado correcto | Rutas, listener, estado y cuerpo HTTP |
| Síntoma | Qué host envió cada solicitud y qué resultado recibió |
| Hipótesis | Resolución de nombres, ruta, listener, firewall o HTTP |
| Evidencia | Comando pertinente, hora, dirección/puerto y observación |
| Refutación | Qué esperarías si la hipótesis fuera incorrecta |
| Cambio y recuperación | El único cambio y el procedimiento exacto para restaurarlo |
| Nueva comprobación | HTTP 200 correcto, acceso SSH con clave y estado de las NIC del laboratorio/administración |

**Aprobación:** Distingue y recupera los fallos A–C y explica si las reglas y observaciones reales respaldan D. Cumple los cinco criterios: identificación del entorno, hipótesis por capas, evidencia, cambio acotado y recuperación, y verificación posterior. Si falta algún criterio, vuelve a la lección pertinente. Completarlo más rápido no mejora la evaluación.

## Aplica estas preguntas a Docker y Kubernetes {#container-cloud-map}

Añade contenedores cuando comprendas el diagnóstico entre máquinas virtuales. Esta tabla asigna funciones para el estudio posterior; no implica que cada paquete atraviese todas las filas en ese orden.

| Lo aprendido | Docker | Kubernetes | Nube |
|---|---|---|---|
| Dirección de proceso/puerto | Listener dentro del namespace de red de un contenedor | Listener del pod y red compartida dentro de un pod | Proceso de backend y puerto de destino del balanceador de carga |
| Enlace y ruta | veth, bridge de Linux y NAT según el entorno | Rutas de pods configuradas por CNI, overlay o enrutamiento nativo | Subredes de VPC, rutas y límites de conectividad |
| Resolución de nombres | Nombres de contenedores en bridges definidos por el usuario | Nombres de servicios y DNS del clúster | DNS organizativo/de la nube y nombres privados |
| Reglas de acceso | Puertos publicados y reglas de reenvío del host | NetworkPolicy y aplicación según la implementación | Controles por capa, como los grupos de seguridad |
| Punto de observación | Host frente a namespace del contenedor | Implementación del nodo, pod y servicio | Cliente, balanceador de carga, nodo y límites de AZ |

Un **bridge** de Docker suele conectar contenedores en un mismo host; un **overlay** crea una red virtual sobre una red subyacente. Para practicar con overlays de Docker Swarm se requiere preparación adicional, por ejemplo, varios hosts. CNI de Kubernetes es un ecosistema aparte de interfaces/plugins: copiar una topología de bridge de Docker no crea un clúster de Kubernetes.

Del mismo modo, `localhost`, la IP del pod, la IP del servicio y un punto de entrada externo son destinos de observación distintos. Las reglas del firewall del host, las reglas de reenvío de contenedores y las políticas de CNI no son una sola lista de reglas intercambiables.

## Próximos pasos prácticos {#next-path}

Para continuar con una secuencia estructurada, sigue la [ruta de redes avanzada](../expert/README.md). Esta ruta relaciona las guías siguientes con una progresión de lectura, experimentación y evaluación.

1. Estudia namespaces, bridges y puertos publicados en [tecnología de contenedores](../../basics/03-container-technology.md).
2. Mide los siguientes saltos, ICMP y PMTU en el [diagnóstico de redes de Linux](../07-linux-network-diagnostics.md). Lee primero los requisitos previos, el alcance y los pasos de limpieza de Docker de esa guía.
3. Aprende los conceptos de [Kubernetes](../../basics/04-kubernetes-introduction.md) y [pods/cargas de trabajo](../../core/02-pods-and-workloads.md); después, sigue el [laboratorio de Service/DNS](../../labs/core/03-services-networking-lab.md).
4. Estudia los [fundamentos de eBPF](../../basics/05-ebpf-fundamentals.md) y luego compara [Cilium](../cilium/README.md) con [Calico](../calico/README.md).
5. Si necesitas AWS, estudia las [redes de EKS](../../eks/03-eks-networking-part1.md), [VPC CNI](../01-vpc-cni.md) y el [balanceo de carga](../03-aws-lb-controller.md). Antes de crear recursos, comprueba por separado las condiciones de costo, permisos y limpieza de cada guía.
6. Para trabajar con el rendimiento, lee las condiciones de medición de la [pila de red del kernel](../../kernel/02-network-stack.md) y la [prueba comparativa de pods](../06-pod-network-benchmark.md). No generalices el pequeño ejercicio HTTP como si demostrara el rendimiento de una red en la nube.

## Limpieza

Detén el servidor del ejercicio en la consola A y luego elimina su archivo desde la misma terminal.

```bash
rm -- "${LAB_WEB:?}/health.txt"
rmdir -- "${LAB_WEB:?}"
```

Registra si se conservarán las reglas de la lección 6 para las prácticas posteriores. Al terminar todo el curso, sigue el procedimiento de recuperación de cada lección o vuelve a **la instantánea de tu máquina virtual**. Verifica la NIC de administración y el acceso SSH existente; después, apaga las máquinas virtuales normalmente.

## Referencias

- [Python http.server](https://docs.python.org/3.12/library/http.server.html)
- [Asignación de direcciones de curl](https://curl.se/docs/manpage.html)
- [Ubuntu 24.04 UFW: orden de reglas, reglas multipuerto y eliminación](https://manpages.ubuntu.com/manpages/noble/man8/ufw.8.html)
- [firewalld: configuración del tiempo de ejecución/permanente y operaciones con rich rules](https://firewalld.org/documentation/man-pages/firewall-cmd.html)
- [Opciones del cliente OpenSSH y uso compartido de conexiones](https://man.openbsd.org/ssh_config)
- [Bridge de Docker](https://docs.docker.com/engine/network/drivers/bridge/)
- [Overlay de Docker](https://docs.docker.com/engine/network/drivers/overlay/)
- [Modelo de redes de Kubernetes](https://kubernetes.io/docs/concepts/services-networking/)

[Anterior: Supervisión y rendimiento](07-monitoring-performance.md) · [Cuestionario](../../quizzes/networking/beginner/08-container-cloud-capstone-quiz.md) · [Volver al curso](README.md)
