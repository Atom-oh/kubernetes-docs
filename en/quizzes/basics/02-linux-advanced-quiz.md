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
   - B) Use 3 if REPLICAS is not set
   - C) Subtract 3 from REPLICAS
   - D) Error

<details>
<summary>Show Answer</summary>

**Answer: B) Use 3 if REPLICAS is not set**

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

</details>

## Practical Questions

16. Write a script with required DATABASE_URL and TIMEOUT default 30.

<details>
<summary>Show Answer</summary>

```bash
#!/bin/bash
: ${DATABASE_URL:?"DATABASE_URL required"}
TIMEOUT=${TIMEOUT:-30}
```

</details>

17. Write a command to output Pods with 3+ restarts as JSON.

<details>
<summary>Show Answer</summary>

```bash
kubectl get pods -A -o json | jq '[.items[] | select([.status.containerStatuses[]?.restartCount] | add >= 3)]'
```

</details>

18. Write an rsync command to sync yaml files through bastion.

<details>
<summary>Show Answer</summary>

```bash
rsync -avzP --include='*.yaml' --exclude='*' -e "ssh -J bastion" /src/ user@host:/dest/
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
- Volume Mount: Auto-updates (~1 min), no restart needed

</details>

---

[Return to Study Materials](../../basics/02-linux-advanced.md)
