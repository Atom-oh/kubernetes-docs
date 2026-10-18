# Cuestionario de habilidades de operaciones Linux

Este cuestionario evalúa su comprensión de las habilidades de operaciones Linux que se utilizan en entornos de Kubernetes.

## Preguntas de opción múltiple

1. ¿Qué comando hace que las variables de entorno estén disponibles para los procesos secundarios?
   - A) set
   - B) export
   - C) declare
   - D) env

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) export**

</details>

2. ¿Cuándo se ejecuta `.bashrc`?
   - A) Solo en shells de inicio de sesión
   - B) En todas las sesiones de shell
   - C) En shells interactivos que no son de inicio de sesión
   - D) Siempre junto con `.bash_profile`

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) En shells interactivos que no son de inicio de sesión**

</details>

3. ¿Qué significa `${REPLICAS:-3}`?
   - A) Asignar 3 a REPLICAS
   - B) Usar 3 si REPLICAS no está definida o está vacía
   - C) Restar 3 a REPLICAS
   - D) Generar un error

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Usar 3 si REPLICAS no está definida o está vacía**

</details>

4. ¿Qué hace `awk 'NR>1 {print $1}'`?
   - A) Imprime el primer campo de todas las líneas
   - B) Imprime solo la primera línea
   - C) Imprime el primer campo y excluye la cabecera
   - D) Imprime las líneas que tienen un primer campo

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Imprime el primer campo y excluye la cabecera**

</details>

5. ¿Qué función cumple `g` en `sed -i 's/old/new/g'`?
   - A) No distingue entre mayúsculas y minúsculas
   - B) Sustituye todas las coincidencias de la línea
   - C) Sustituye una sola coincidencia
   - D) Habilita las expresiones regulares

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Sustituye todas las coincidencias de la línea**

</details>

6. ¿Qué hace `-r` en `jq -r`?
   - A) Busca de forma recursiva
   - B) Invierte el orden
   - C) Devuelve cadenas sin formato y sin comillas
   - D) Usa solo lectura

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Devuelve cadenas sin formato y sin comillas**

</details>

7. ¿Qué significa `ssh -L 8080:localhost:80 user@server`?
   - A) Reenvía el puerto 8080 del servidor al puerto 80 local
   - B) Reenvía el puerto local 8080 al puerto 80 del servidor
   - C) Reenvía el puerto 80 del servidor al puerto local 8080
   - D) Reenvía el puerto local 80 al puerto 8080 del servidor

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Reenvía el puerto local 8080 al puerto 80 del servidor**

</details>

8. ¿Qué representa `wa` en vmstat?
   - A) CPU de una aplicación web
   - B) Porcentaje de tiempo de espera de E/S
   - C) Número de advertencias
   - D) Procesos activos

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Porcentaje de tiempo de espera de E/S**

</details>

9. ¿Qué comando crea un volumen físico de LVM?
   - A) lvcreate
   - B) vgcreate
   - C) pvcreate
   - D) fscreate

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) pvcreate**

</details>

10. ¿Qué devuelve `curl -s -o /dev/null -w "%{http_code}" URL`?
    - A) El cuerpo de la respuesta
    - B) Las cabeceras de la respuesta
    - C) El código de estado HTTP
    - D) El tiempo de respuesta

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) El código de estado HTTP**

</details>

## Preguntas de respuesta corta

11. ¿Qué comando ejecuta el contenido de un archivo en el shell actual?

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: source (o .)**

</details>

12. ¿Qué herramienta se usa para analizar JSON?

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: jq**

</details>

13. ¿Qué opción de SSH se usa para saltar a través de un bastion?

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: ProxyJump (o -J)**

</details>

14. ¿Qué comando supervisa la E/S de disco?

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: iostat**

</details>

15. ¿Cuál es la ruta al token de la cuenta de servicio del Pod?

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: /var/run/secrets/kubernetes.io/serviceaccount/token**

Esta es la ruta predeterminada del token proyectado; puede no existir si `automount` está deshabilitado. Los tokens rotan.

</details>

## Preguntas prácticas

16. Escriba un script con `DATABASE_URL` obligatorio y un valor predeterminado de 30 para `TIMEOUT`.

<details>
<summary>Mostrar respuesta</summary>

```bash
#!/bin/bash
: "${DATABASE_URL:?DATABASE_URL required}"
TIMEOUT=${TIMEOUT:-30}
```

</details>

17. Escriba un comando que devuelva como JSON los Pods cuyos contenedores normales y de inicialización sumen al menos 3 reinicios.

<details>
<summary>Mostrar respuesta</summary>

```bash
kubectl get pods -A -o json | jq '[.items[] | select(([(.status.containerStatuses[]?, .status.initContainerStatuses[]?) | .restartCount] | add // 0) >= 3)]'
```

</details>

18. Escriba un comando de rsync para sincronizar archivos YAML a través de un host bastion.

<details>
<summary>Mostrar respuesta</summary>

```bash
rsync -avzP --prune-empty-dirs --include='*/' --include='*.yaml' --exclude='*' -e "ssh -J bastion" /src/ user@host:/dest/
```

</details>

## Preguntas avanzadas

19. Escriba un script para diagnosticar un nodo.

<details>
<summary>Mostrar respuesta</summary>

```bash
#!/bin/bash
echo "=== System ===" && uptime && free -h && df -h
echo "=== kubelet ===" && systemctl status kubelet --no-pager
```

</details>

20. Explique las diferencias entre las variables de entorno de ConfigMap y los montajes de volúmenes.

<details>
<summary>Mostrar respuesta</summary>

- Variables de entorno: Se cargan al iniciar el Pod; los cambios requieren un reinicio.
- Montaje de volumen: Las actualizaciones se propagan con el tiempo (periodo de sincronización de kubelet más el retraso de la caché/watch). La aplicación debe volver a leer o cargar el archivo. Los montajes `subPath` no reciben actualizaciones.

</details>

---

[Volver a los materiales de estudio](../../basics/02-linux-advanced.md)

## Referencias de verificación

- https://kubernetes.io/docs/concepts/storage/volumes/#local
- https://kubernetes.io/docs/concepts/storage/storage-classes/#local
- https://kubernetes.io/docs/tasks/run-application/access-api-from-pod/
- https://kubernetes.io/docs/concepts/configuration/configmap/
- https://kubernetes.io/docs/reference/kubectl/generated/kubectl_wait/
- https://www.gnu.org/software/bash/manual/html_node/Shell-Parameter-Expansion.html
- https://www.gnu.org/software/bash/manual/html_node/Bash-Startup-Files.html
- https://download.samba.org/pub/rsync/rsync.1
- https://github.com/mikefarah/yq
- https://busybox.net/downloads/BusyBox.html
- https://github.com/docker-library/official-images/blob/master/library/busybox
