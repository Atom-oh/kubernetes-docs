# Linux Operations Skills Quiz

This quiz tests your understanding of Linux operations skills used in Kubernetes environments.

## Multiple Choice Questions

1. Which command makes environment variables available to child processes?
   - A) set
   - B) export
   - C) declare
   - D) env

<details>
<summary>Show Answer</summary>

**Answer: B) export**

</details>

2. When is `.bashrc` executed?
   - A) Only for login shells
   - B) For all shell sessions
   - C) For non-login interactive shells
   - D) Always with .bash_profile

<details>
<summary>Show Answer</summary>

**Answer: C) For non-login interactive shells**

</details>

3. What does `${REPLICAS:-3}` mean?
   - A) Set REPLICAS to 3
   - B) Use 3 if REPLICAS is unset or empty
   - C) Subtract 3 from REPLICAS
   - D) Error

<details>
<summary>Show Answer</summary>

**Answer: B) Use 3 if REPLICAS is unset or empty**

</details>

4. What does `awk 'NR>1 {print $1}'` do?
   - A) Print first field of all lines
   - B) Print only the first line
   - C) Print first field excluding header
   - D) Print lines with first field

<details>
<summary>Show Answer</summary>

**Answer: C) Print first field excluding header**

</details>

5. What is the role of `g` in `sed -i 's/old/new/g'`?
   - A) Case insensitive
   - B) Replace all matches in line
   - C) Replace once
   - D) Enable regex

<details>
<summary>Show Answer</summary>

**Answer: B) Replace all matches in line**

</details>

6. What does `-r` do in `jq -r`?
   - A) Recursive search
   - B) Reverse order
   - C) Raw string output without quotes
   - D) Read-only

<details>
<summary>Show Answer</summary>

**Answer: C) Raw string output without quotes**

</details>

7. What does `ssh -L 8080:localhost:80 user@server` mean?
   - A) Forward server 8080 to local 80
   - B) Forward local 8080 to server 80
   - C) Forward server 80 to local 8080
   - D) Forward local 80 to server 8080

<details>
<summary>Show Answer</summary>

**Answer: B) Forward local 8080 to server 80**

</details>

8. What does `wa` represent in vmstat?
   - A) Web application CPU
   - B) I/O wait time percentage
   - C) Warning count
   - D) Active processes

<details>
<summary>Show Answer</summary>

**Answer: B) I/O wait time percentage**

</details>

9. Which command creates an LVM Physical Volume?
   - A) lvcreate
   - B) vgcreate
   - C) pvcreate
   - D) fscreate

<details>
<summary>Show Answer</summary>

**Answer: C) pvcreate**

</details>

10. What does `curl -s -o /dev/null -w "%{http_code}" URL` output?
    - A) Response body
    - B) Response headers
    - C) HTTP status code
    - D) Response time

<details>
<summary>Show Answer</summary>

**Answer: C) HTTP status code**

</details>

## Short Answer Questions

11. What command executes file contents in the current shell?

<details>
<summary>Show Answer</summary>

**Answer: source (or .)**

</details>

12. What is the JSON parsing tool?

<details>
<summary>Show Answer</summary>

**Answer: jq**

</details>

13. What SSH option is used for bastion jump?

<details>
<summary>Show Answer</summary>

**Answer: ProxyJump (or -J)**

</details>

14. What command monitors disk I/O?

<details>
<summary>Show Answer</summary>

**Answer: iostat**

</details>

15. What is the path to the Pod service account token?

<details>
<summary>Show Answer</summary>

**Answer: /var/run/secrets/kubernetes.io/serviceaccount/token**

This is the default projected-token path; it may be absent if automount is disabled. Tokens rotate.

</details>

## Practical Questions

16. Write a script with required DATABASE_URL and TIMEOUT default 30.

<details>
<summary>Show Answer</summary>

```bash
#!/bin/bash
: "${DATABASE_URL:?DATABASE_URL required}"
TIMEOUT=${TIMEOUT:-30}
```

</details>

17. Write a command to output Pods whose regular and init containers have at least 3 combined restarts as JSON.

<details>
<summary>Show Answer</summary>

```bash
kubectl get pods -A -o json | jq '[.items[] | select(([(.status.containerStatuses[]?, .status.initContainerStatuses[]?) | .restartCount] | add // 0) >= 3)]'
```

</details>

18. Write an rsync command to sync yaml files through bastion.

<details>
<summary>Show Answer</summary>

```bash
rsync -avzP --prune-empty-dirs --include='*/' --include='*.yaml' --exclude='*' -e "ssh -J bastion" /src/ user@host:/dest/
```

</details>

## Advanced Questions

19. Write a node diagnostic script.

<details>
<summary>Show Answer</summary>

```bash
#!/bin/bash
echo "=== System ===" && uptime && free -h && df -h
echo "=== kubelet ===" && systemctl status kubelet --no-pager
```

</details>

20. Explain ConfigMap env vars vs volume mount differences.

<details>
<summary>Show Answer</summary>

- Environment Variables: Loaded at Pod start, requires restart for changes
- Volume mount: Updates propagate eventually (kubelet sync period plus cache/watch delay). The application must reread/reload the file. subPath mounts do not receive updates.

</details>

---

[Return to Study Materials](../../basics/02-linux-advanced.md)

## Verification References

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
