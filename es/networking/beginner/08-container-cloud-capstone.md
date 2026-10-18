# 8. Proyecto final: de los fallos de un servicio web a los contenedores y la nube

> **Base de aprendizaje**: Ubuntu Server 24.04 LTS, con una ruta alternativa para Rocky Linux 9
>
> **Última actualización**: 15 de septiembre de 2026

**Requisitos previos:** [Lecciones 1–7](README.md#course-map), las direcciones de laboratorio de ambas máquinas virtuales, inicio de sesión SSH con clave verificado y una regla TCP 8000 que permita el acceso del cliente de laboratorio. Detenga primero el servidor web de la lección 7.

**Objetivos:** Registrar el estado correcto de un pequeño servicio web y, después, reproducir, diagnosticar y recuperar fallos de distintas capas, uno por uno. A continuación, aplicar las mismas preguntas a Docker y Kubernetes. Dedique aproximadamente entre 3 y 4 horas.

## Tarea y estado correcto de referencia {#baseline}

La tarea es «el cliente lee `/health.txt` del servidor». No se necesita ningún framework web ni una cuenta en la nube.

**Consola A del servidor:**

```bash
LAB_WEB=$(mktemp -d /tmp/net-capstone.XXXXXX)
printf 'healthy\n' > "$LAB_WEB/health.txt"
timeout 300 python3 -m http.server 8000 \
  --bind 192.0.2.20 --directory "$LAB_WEB"
```

Cuando venza el límite de cinco minutos, reinicie el servidor con el mismo comando. Compruebe la consola para no confundir un servidor detenido intencionalmente con un fallo de red. Mantenga únicamente el archivo del ejercicio en este directorio.

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

Ambas rutas deben usar las NIC de laboratorio, el proceso de escucha debe estar en `192.0.2.20:8000` y ambas solicitudes deben devolver HTTP 200 con `healthy` en el cuerpo. `--resolve` proporciona **una asignación de dirección de host/puerto para esta invocación de curl**. No cambia el DNS del sistema ni el de otras aplicaciones.

Si falla esta comprobación de referencia, revise primero la configuración y las reglas de las lecciones 4–6. No introduzca un fallo nuevo hasta que funcione el estado de referencia.

## Reproduzca un fallo por vez {#faults}

Comience cada experimento desde el estado de referencia correcto y repita la solicitud correcta después de recuperarse. Las solicitudes ordinarias de `curl` pueden devolver el estado de salida 0 incluso ante HTTP 404, así que lea la línea de estado HTTP. La automatización que deba tratar los errores HTTP como fallos puede seleccionar explícitamente una opción compatible, como `--fail-with-body`.

### A. Separe la resolución de nombres de la conectividad IP

En el cliente, compare una solicitud sin `--resolve`.

```bash
getent ahostsv4 lesson.test
curl --disable --noproxy '*' --connect-timeout 2 --max-time 5 \
  -i http://lesson.test:8000/health.txt
```

Si no registró `lesson.test` por separado, lo normal es que falle la resolución de nombres en este laboratorio. Si ya lo configuró en `/etc/hosts` o en el DNS local, anote la asignación real en lugar de esperar que falle. Compruebe si las solicitudes anteriores por IP y con `--resolve` funcionan en el mismo entorno.

**Diagnóstico:** Si funciona la solicitud por IP, pero falla la búsqueda del nombre, investigue primero la resolución de nombres. Esto no demuestra que haya fallado un servidor DNS específico ni que exista una interrupción general de Internet. **Recuperación:** Vuelva a usar la asignación `--resolve` de la solicitud de referencia; para este experimento temporal no hace falta sobrescribir el resolver del sistema.

### B. Error en la ruta de la aplicación

Desde el cliente, solicite un archivo inexistente.

```bash
curl --disable --noproxy '*' --connect-timeout 2 --max-time 5 \
  -i http://192.0.2.20:8000/missing.txt
```

**Diagnóstico:** Recibir HTTP 404 significa que esa solicitud obtuvo una respuesta HTTP del servidor. No hay motivo para restablecer toda la configuración de enrutamiento y firewall. Compare la ruta solicitada con el registro del servidor. **Recuperación:** Vuelva a solicitar `/health.txt`.

### C. Dirección de escucha incorrecta

Detenga el servidor con Ctrl+C en la consola A. En **la misma terminal**, cambie solo la dirección de enlace.

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

Compruebe que falla la solicitud original del cliente a `192.0.2.20:8000` y que funciona la solicitud de bucle local del propio servidor. El comportamiento del firewall también influye en que el fallo aparezca como rechazo o como tiempo de espera. El proceso de escucha `127.0.0.1` que muestra `ss` es la evidencia clave.

**Recuperación:** Pulse Ctrl+C en la consola A y reinicie el comando correcto con `--bind 192.0.2.20`. El bucle local de una VM no es el bucle local de otra VM.

### D. Compruebe una hipótesis sobre el firewall con evidencia {#firewall-fault}

Use **únicamente el gestor seleccionado en la lección 6**, desde la consola del hipervisor del servidor. Este fallo quita solo la regla de permiso TCP 8000 que administra el curso. La regla de permiso TCP 22, la denegación del laboratorio, las políticas predeterminadas, las asignaciones de zona/perfil y la NIC de administración permanecen intactas. Termine primero el experimento opcional con Fail2ban para que ningún cambio de bloqueo en segundo plano confunda esta prueba.

**Consola B del servidor, usuario normal:** vuelva a identificar ambas NIC mediante las MAC registradas en el hipervisor; no dé por hecho que siguen existiendo las variables de la lección 6.

```bash
ip -br link
read -r -p 'Server lab NIC verified by MAC: ' LAB_IF
read -r -p 'Server management NIC verified by MAC: ' MGMT_IF
ip -4 -br address show dev "$LAB_IF"
ip -4 -br address show dev "$MGMT_IF"
ip -4 route
sudo ss -ltnp 'sport = :8000'
```

Verifique que la NIC de laboratorio tenga `.20/24`, que los nombres de las NIC sean distintos, que la administración no haya cambiado y que el proceso de escucha correcto siga en `.20:8000`. Registre las reglas actuales como se indica más abajo. Si venció el temporizador del servidor, reinicie **solo** `timeout 300 python3 -m http.server 8000 --bind 192.0.2.20 --directory "${LAB_WEB:?missing existing web directory}"` en la consola A del servidor, con el directorio que ya tiene. No introduzca a la vez el fallo de un servidor detenido.

**Cliente, usuario normal:** recupere de sus registros el directorio de claves de la lección 5 y la cuenta normal del servidor. No cree una clave nueva ni eluda el registro de host ya verificado.

```bash
read -r -p 'Existing lesson-5 client key directory: ' SSH_LAB_DIR
read -r -p 'Normal account on the server: ' SERVER_USER
ls -l -- "${SSH_LAB_DIR:?missing key directory}/id_ed25519" \
  "${SSH_LAB_DIR:?missing key directory}/known_hosts"
```

Defina una sola vez esta función breve de shell en esa terminal del cliente. Al ejecutar `check_lab_ssh`, se abre una conexión SSH **nueva**, se imprime la cuenta/remoto y se vuelve al cliente; no crea archivos ni servicios.

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

**Se permite que aparezca la solicitud de frase de contraseña de la clave privada**; no se necesita un agente desbloqueado. La alternativa de autenticación con contraseña de la cuenta remota está deshabilitada. `-F /dev/null` evita la configuración ajena del cliente y la desactivación de la multiplexación impide reutilizar una conexión autenticada anterior. Se espera la cuenta normal y una conexión de `.10` a `.20`, puerto 22. Si falla esta comprobación **previa al fallo** o falla HTTP en estado correcto, deténgase antes de cambiar reglas. Conserve y vuelva a comprobar también cualquier ruta SSH de administración necesaria por separado.

#### UFW: cambie solo la regla HTTP guardada/aplicada

**Consola B del servidor Ubuntu, sudo:**

```bash
sudo ufw status numbered
sudo ufw show added
```

Continúe solo si UFW está activo y las tres reglas del curso de la lección 6 aparecen en este orden: **1: permiso TCP 22 de `.10` a `.20` en `LAB_IF`; 2: permiso TCP 8000 por separado; 3: denegación TCP `22,8000` en la misma interfaz/destino**. Registre sus especificaciones completas. Si aún tiene una regla de permiso combinada antigua `22,8000` o el orden es diferente, corrija primero la configuración de la lección 6; eliminar un puerto no es la operación inversa de una regla para varios puertos.

Quite solo HTTP:

```bash
sudo ufw delete allow in on "$LAB_IF" proto tcp \
  from 192.0.2.10 to 192.0.2.20 port 8000
sudo ufw status numbered
sudo ufw show added
```

Confirme que el permiso TCP 22 sigue primero y que la denegación del laboratorio ahora está segunda. Esto cambia el estado guardado y el aplicado de UFW. No modifique esas dos reglas ni las políticas predeterminadas. Ahora realice las siguientes **comprobaciones durante el fallo**.

**Restauración desde la misma consola Ubuntu:** compruebe que la denegación siga segunda y, a continuación, inserte HTTP en la posición 2, **antes de esa denegación**:

```bash
sudo ufw insert 2 allow in on "$LAB_IF" proto tcp \
  from 192.0.2.10 to 192.0.2.20 port 8000 comment 'network-beginner-http'
sudo ufw status numbered
sudo ufw show added
```

Se espera el orden original: permiso SSH → permiso HTTP → denegación del laboratorio, con el ámbito original de origen/interfaz/destino. Si se añade el permiso después de la denegación, HTTP seguirá bloqueado; la operación inversa de la eliminación también debe restaurar la ubicación. Si otra regla cambió las posiciones, deténgase y restablezca el orden registrado en lugar de usar un número obsoleto. Continúe con las comprobaciones posteriores a la recuperación.

#### firewalld: quite solo HTTP del estado de ejecución y conserve la política guardada

**Consola B del servidor Rocky, usuario normal para las asignaciones y sudo para las consultas del firewall:**

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

Se espera únicamente la NIC de laboratorio en `network-beginner`, la zona de administración original y que las cuatro consultas devuelvan `yes`. Esto requiere las reglas permanentes conservadas de la lección 6, no su prueba temporal que vence. Registre ambas configuraciones e inspeccione cualquier política más amplia que todavía pudiera aceptar HTTP.

Quite **solo la regla HTTP en tiempo de ejecución**:

```bash
sudo firewall-cmd --zone=network-beginner --remove-rich-rule="$RULE8000"
sudo firewall-cmd --zone=network-beginner --query-rich-rule="$RULE8000"
sudo firewall-cmd --permanent --zone=network-beginner --query-rich-rule="$RULE8000"
sudo firewall-cmd --zone=network-beginner --query-rich-rule="$RULE22"
sudo firewall-cmd --permanent --zone=network-beginner --query-rich-rule="$RULE22"
```

Se espera `no`, `yes`, `yes`, `yes`; el `no` tiene un estado de salida distinto de cero, como corresponde. Ejecute las comprobaciones durante el fallo. No recargue, reinicie ni use `--runtime-to-permanent`: una recarga volvería a introducir la regla HTTP guardada, mientras que copiar el estado de ejecución al permanente haría persistente el fallo sin querer.

**Restauración desde la misma consola Rocky**, sin recarga global ni cambio permanente:

```bash
sudo firewall-cmd --zone=network-beginner --add-rich-rule="$RULE8000"
sudo firewall-cmd --zone=network-beginner --query-rich-rule="$RULE8000"
sudo firewall-cmd --permanent --zone=network-beginner --query-rich-rule="$RULE8000"
sudo firewall-cmd --zone=network-beginner --query-rich-rule="$RULE22"
sudo firewall-cmd --permanent --zone=network-beginner --query-rich-rule="$RULE22"
```

Las cuatro consultas deberían volver a indicar `yes`. Compare las listas de tiempo de ejecución y permanentes con el estado de referencia registrado: las reglas guardadas nunca se cambiaron y la regla HTTP en tiempo de ejecución se restauró con el mismo ámbito. Si la política guardada cambió inesperadamente, investigue comparándola con ese registro; no la sobrescriba en bloque.

#### Comprobaciones durante el fallo y después de recuperarse

**Cliente, usuario normal, misma terminal:** ejecute este par **después de quitar HTTP y otra vez tras restaurarlo**, además de la comprobación previa al fallo.

```bash
check_lab_ssh
curl --disable --noproxy '*' --connect-timeout 2 --max-time 5 \
  -i http://192.0.2.20:8000/health.txt
```

Durante el fallo, la comprobación SSH nueva que usa solo la clave debe seguir funcionando. HTTP debería fallar según la política del curso registrada, mientras el proceso de escucha del servidor permanece en `.20:8000`. Si falla SSH, restaure únicamente el permiso HTTP eliminado desde la consola del servidor, compare la regla/ruta SSH que no cambió y deténgase: no ha demostrado un fallo exclusivo de HTTP. Si HTTP sigue funcionando, inspeccione otras reglas coincidentes de aceptación, el comportamiento de zonas/políticas predeterminadas, el proceso de escucha y la evidencia de paquetes; no afirme que hay un bloqueo solo porque se quitó una regla.

Después de la recuperación, exija una nueva comprobación correcta de SSH con clave y HTTP 200 con `healthy`. En la consola B del servidor, repita `sudo ss -ltnp 'sport = :8000'`, las consultas/listas de reglas pertinentes, `ip -4 -br address show dev "$MGMT_IF"` e `ip -4 route`; compárelas con el registro previo al fallo y vuelva a comprobar el acceso de administración necesario. Registre por separado las observaciones de las tres etapas. Estas instrucciones no afirman que se haya ejecutado el entorno invitado al redactar el documento.

## Informe y criterios para completar {#capstone-report}

Registre las direcciones y los resultados del laboratorio, no contraseñas, claves privadas ni tráfico real de usuarios.

| Campo | Qué registrar |
|---|---|
| Entorno | Distribución, kernel, NIC de laboratorio, direcciones de cliente/servidor y gestor del firewall |
| Estado correcto | Rutas, proceso de escucha, estado HTTP y cuerpo |
| Síntoma | Qué host envió qué solicitud y qué resultado recibió |
| Hipótesis | Resolución de nombres, ruta, proceso de escucha, firewall o HTTP |
| Evidencia | Comando pertinente, hora, dirección/puerto y observación |
| Refutación | Qué esperaría si la hipótesis fuera incorrecta |
| Cambio y recuperación | El único cambio y el procedimiento exacto para restaurarlo |
| Nueva comprobación | HTTP 200 correcto, acceso SSH con clave y estado de las NIC de laboratorio/administración |

**Aprobado:** Distinga y recupérese de A–C y explique si las reglas y observaciones reales respaldan D. Cumpla los cinco criterios: identificación del entorno, hipótesis por capas, evidencia, cambio/restauración acotados y verificación posterior a la recuperación. Vuelva a la lección pertinente si falta algún criterio. Terminar más rápido no forma parte de la evaluación.

## Aplique las preguntas a Docker y Kubernetes {#container-cloud-map}

Añada contenedores después de comprender el diagnóstico entre VM. Esta tabla asigna funciones para el estudio posterior; no implica que todos los paquetes atraviesen cada fila en orden.

| Lo aprendido | Docker | Kubernetes | Nube |
|---|---|---|---|
| Dirección/puerto del proceso | Proceso de escucha dentro del espacio de nombres de red del contenedor | Proceso de escucha y red del Pod compartidos dentro de un Pod | Proceso de backend y puerto de destino del balanceador de carga |
| Enlace y ruta | veth, bridge de Linux y NAT según el entorno | Rutas de Pod configuradas por CNI, enrutamiento superpuesto o nativo | Subredes de VPC, rutas y límites de conectividad |
| Resolución de nombres | Nombres de contenedor en bridges definidos por el usuario | Nombres de Service y DNS del clúster | DNS organizativo/de la nube y nombres privados |
| Reglas de acceso | Puertos publicados y reglas de reenvío del host | NetworkPolicy y aplicación de la implementación | Controles por capa, como los grupos de seguridad |
| Punto de observación | Host frente al espacio de nombres del contenedor | Nodo, Pod e implementación del Service | Límites del cliente, balanceador de carga, nodo y AZ |

Un **bridge** de Docker suele conectar contenedores en un host; un **overlay** construye una red virtual sobre una red subyacente. Para practicar overlays de Docker Swarm se requiere preparación adicional, como varios hosts. CNI de Kubernetes es un ecosistema independiente de interfaces/plugins: copiar una topología de bridge de Docker no crea un clúster de Kubernetes.

Del mismo modo, `localhost`, la IP de un Pod, la IP de un Service y un punto de entrada externo son objetivos de observación distintos. Las reglas del firewall del host, las reglas de reenvío del contenedor y las políticas de CNI no forman una única lista de reglas intercambiable.

## Próximos pasos prácticos {#next-path}

Para continuar de forma estructurada, siga la [ruta de redes para expertos](../expert/README.md). Esta conecta las guías individuales siguientes con una progresión de lectura, experimentos y evaluaciones.

1. Use [tecnología de contenedores](../../basics/03-container-technology.md) para estudiar espacios de nombres, bridges y puertos publicados.
2. Mida los siguientes saltos, ICMP y PMTU en [diagnóstico de redes Linux](../07-linux-network-diagnostics.md). Lea primero los requisitos previos de Docker, el alcance y la limpieza de esa guía.
3. Aprenda la [introducción a Kubernetes](../../basics/04-kubernetes-introduction.md) y [Pods/cargas de trabajo](../../core/02-pods-and-workloads.md); después siga el [laboratorio de Service/DNS](../../labs/core/03-services-networking-lab.md).
4. Estudie los [fundamentos de eBPF](../../basics/05-ebpf-fundamentals.md) y luego compare [Cilium](../cilium/README.md) y [Calico](../calico/README.md).
5. Si necesita AWS, estudie las [redes de EKS](../../eks/03-eks-networking-part1.md), [VPC CNI](../01-vpc-cni.md) y [balanceo de carga](../03-aws-lb-controller.md). Antes de crear recursos, compruebe por separado las condiciones de costos, permisos y limpieza de cada guía.
6. Para trabajar con el rendimiento, lea las condiciones de medición en la [pila de redes del kernel](../../kernel/02-network-stack.md) y el [benchmark de Pod](../06-pod-network-benchmark.md). No generalice este pequeño ejercicio HTTP como resultado del rendimiento de una nube.

## Limpieza

Detenga el servidor del ejercicio en la consola A y, a continuación, elimine su archivo en la misma terminal.

```bash
rm -- "${LAB_WEB:?}/health.txt"
rmdir -- "${LAB_WEB:?}"
```

Registre si las reglas de la lección 6 permanecerán para las prácticas posteriores. Al terminar el curso completo, use el procedimiento de recuperación de cada lección o vuelva a **la instantánea de su VM**. Verifique la NIC de administración y el acceso SSH existente; después apague las VM normalmente.

## Referencias

- [Python http.server](https://docs.python.org/3.12/library/http.server.html)
- [Asignación de direcciones de curl](https://curl.se/docs/manpage.html)
- [UFW de Ubuntu 24.04: orden de reglas, reglas para varios puertos y eliminación](https://manpages.ubuntu.com/manpages/noble/man8/ufw.8.html)
- [firewalld: configuración de tiempo de ejecución/permanente y operaciones con reglas enriquecidas](https://firewalld.org/documentation/man-pages/firewall-cmd.html)
- [Opciones del cliente OpenSSH y uso compartido de conexiones](https://man.openbsd.org/ssh_config)
- [Bridge de Docker](https://docs.docker.com/engine/network/drivers/bridge/)
- [Overlay de Docker](https://docs.docker.com/engine/network/drivers/overlay/)
- [Modelo de redes de Kubernetes](https://kubernetes.io/docs/concepts/services-networking/)

[Anterior: supervisión y rendimiento](07-monitoring-performance.md) · [Cuestionario](../../quizzes/networking/beginner/08-container-cloud-capstone-quiz.md) · [Volver al curso](README.md)
