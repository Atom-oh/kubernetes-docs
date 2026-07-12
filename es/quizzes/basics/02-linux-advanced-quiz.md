# Cuestionario de habilidades de operaciones Linux

Este cuestionario evalúa tu comprensión de las habilidades de operaciones Linux usadas en entornos Kubernetes.

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
   - A) Solo para shells de inicio de sesión
   - B) Para todas las sesiones de shell
   - C) Para shells interactivos que no son de inicio de sesión
   - D) Siempre con .bash_profile

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Para shells interactivos que no son de inicio de sesión**

</details>

3. ¿Qué significa `${REPLICAS:-3}`?
   - A) Establecer REPLICAS en 3
   - B) Usar 3 si REPLICAS no está definida
   - C) Restar 3 de REPLICAS
   - D) Error

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Usar 3 si REPLICAS no está definida**

</details>

4. ¿Qué hace `awk 'NR>1 {print $1}'`?
   - A) Imprime el primer campo de todas las líneas
   - B) Imprime solo la primera línea
   - C) Imprime el primer campo excluyendo el encabezado
   - D) Imprime líneas con el primer campo

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Imprime el primer campo excluyendo el encabezado**

</details>

5. ¿Cuál es la función de `g` en `sed -i 's/old/new/g'`?
   - A) No distingue entre mayúsculas y minúsculas
   - B) Reemplaza todas las coincidencias en la línea
   - C) Reemplaza una vez
   - D) Habilita regex

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Reemplaza todas las coincidencias en la línea**

</details>

6. ¿Qué hace `-r` en `jq -r`?
   - A) Búsqueda recursiva
   - B) Orden inverso
   - C) Salida de cadena sin formato y sin comillas
   - D) Solo lectura

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Salida de cadena sin formato y sin comillas**

</details>

7. ¿Qué significa `ssh -L 8080:localhost:80 user@server`?
   - A) Reenvía el 8080 del servidor al 80 local
   - B) Reenvía el 8080 local al 80 del servidor
   - C) Reenvía el 80 del servidor al 8080 local
   - D) Reenvía el 80 local al 8080 del servidor

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Reenvía el 8080 local al 80 del servidor**

</details>

8. ¿Qué representa `wa` en vmstat?
   - A) CPU de aplicación web
   - B) Porcentaje de tiempo de espera de E/S
   - C) Conteo de advertencias
   - D) Procesos activos

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Porcentaje de tiempo de espera de E/S**

</details>

9. ¿Qué comando crea un volumen físico LVM?
   - A) lvcreate
   - B) vgcreate
   - C) pvcreate
   - D) fscreate

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) pvcreate**

</details>

10. ¿Qué muestra `curl -s -o /dev/null -w "%{http_code}" URL` como salida?
    - A) Cuerpo de la respuesta
    - B) Encabezados de la respuesta
    - C) Código de estado HTTP
    - D) Tiempo de respuesta

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Código de estado HTTP**

</details>

## Preguntas de respuesta corta

11. ¿Qué comando ejecuta el contenido de un archivo en el shell actual?

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: source (or .)**

</details>

12. ¿Cuál es la herramienta de análisis JSON?

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: jq**

</details>

13. ¿Qué opción de SSH se usa para el salto mediante bastion?

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: ProxyJump (or -J)**

</details>

14. ¿Qué comando monitorea la E/S de disco?

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: iostat**

</details>

15. ¿Cuál es la ruta al token de la service account del Pod?

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: /var/run/secrets/kubernetes.io/serviceaccount/token**

</details>

## Preguntas prácticas

16. Escribe un script con DATABASE_URL obligatoria y TIMEOUT predeterminado 30.

<details>
<summary>Mostrar respuesta</summary>

```bash
#!/bin/bash
: ${DATABASE_URL:?"DATABASE_URL required"}
TIMEOUT=${TIMEOUT:-30}
```

</details>

17. Escribe un comando para mostrar Pods con 3+ reinicios como JSON.

<details>
<summary>Mostrar respuesta</summary>

```bash
kubectl get pods -A -o json | jq '[.items[] | select([.status.containerStatuses[]?.restartCount] | add >= 3)]'
```

</details>

18. Escribe un comando rsync para sincronizar archivos yaml a través de bastion.

<details>
<summary>Mostrar respuesta</summary>

```bash
rsync -avzP --include='*.yaml' --exclude='*' -e "ssh -J bastion" /src/ user@host:/dest/
```

</details>

## Preguntas avanzadas

19. Escribe un script de diagnóstico de nodo.

<details>
<summary>Mostrar respuesta</summary>

```bash
#!/bin/bash
echo "=== System ===" && uptime && free -h && df -h
echo "=== kubelet ===" && systemctl status kubelet --no-pager
```

</details>

20. Explica las diferencias entre variables de entorno de ConfigMap y montaje de volumen.

<details>
<summary>Mostrar respuesta</summary>

- Variables de entorno: Cargadas al iniciar el Pod, requieren reinicio para los cambios
- Montaje de volumen: Se actualiza automáticamente (~1 min), no necesita reinicio

</details>

---

[Volver a los materiales de estudio](../../basics/02-linux-advanced.md)
