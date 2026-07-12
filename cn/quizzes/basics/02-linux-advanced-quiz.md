# Linux 操作技能测验

本测验测试你对 Kubernetes 环境中使用的 Linux 操作技能的理解。

## 选择题

1. 哪个命令会让环境变量可供子进程使用？
   - A) set
   - B) export
   - C) declare
   - D) env

<details>
<summary>显示答案</summary>

**答案：B) export**

</details>

2. `.bashrc` 什么时候执行？
   - A) 仅用于登录 shell
   - B) 用于所有 shell 会话
   - C) 用于非登录交互式 shell
   - D) 始终与 .bash_profile 一起

<details>
<summary>显示答案</summary>

**答案：C) 用于非登录交互式 shell**

</details>

3. `${REPLICAS:-3}` 是什么意思？
   - A) 将 REPLICAS 设置为 3
   - B) 如果未设置 REPLICAS，则使用 3
   - C) 从 REPLICAS 中减去 3
   - D) 错误

<details>
<summary>显示答案</summary>

**答案：B) 如果未设置 REPLICAS，则使用 3**

</details>

4. `awk 'NR>1 {print $1}'` 做什么？
   - A) 打印所有行的第一个字段
   - B) 只打印第一行
   - C) 打印第一个字段，但不包括表头
   - D) 打印带有第一个字段的行

<details>
<summary>显示答案</summary>

**答案：C) 打印第一个字段，但不包括表头**

</details>

5. `sed -i 's/old/new/g'` 中 `g` 的作用是什么？
   - A) 大小写不敏感
   - B) 替换行中的所有匹配项
   - C) 只替换一次
   - D) 启用正则表达式

<details>
<summary>显示答案</summary>

**答案：B) 替换行中的所有匹配项**

</details>

6. `jq -r` 中 `-r` 做什么？
   - A) 递归搜索
   - B) 反向排序
   - C) 输出不带引号的原始字符串
   - D) 只读

<details>
<summary>显示答案</summary>

**答案：C) 输出不带引号的原始字符串**

</details>

7. `ssh -L 8080:localhost:80 user@server` 是什么意思？
   - A) 将服务器 8080 转发到本地 80
   - B) 将本地 8080 转发到服务器 80
   - C) 将服务器 80 转发到本地 8080
   - D) 将本地 80 转发到服务器 8080

<details>
<summary>显示答案</summary>

**答案：B) 将本地 8080 转发到服务器 80**

</details>

8. vmstat 中的 `wa` 表示什么？
   - A) Web 应用程序 CPU
   - B) I/O 等待时间百分比
   - C) 警告计数
   - D) 活跃进程

<details>
<summary>显示答案</summary>

**答案：B) I/O 等待时间百分比**

</details>

9. 哪个命令会创建 LVM 物理卷？
   - A) lvcreate
   - B) vgcreate
   - C) pvcreate
   - D) fscreate

<details>
<summary>显示答案</summary>

**答案：C) pvcreate**

</details>

10. `curl -s -o /dev/null -w "%{http_code}" URL` 输出什么？
    - A) 响应正文
    - B) 响应标头
    - C) HTTP 状态码
    - D) 响应时间

<details>
<summary>显示答案</summary>

**答案：C) HTTP 状态码**

</details>

## 简答题

11. 什么命令会在当前 shell 中执行文件内容？

<details>
<summary>显示答案</summary>

**答案：source (or .)**

</details>

12. JSON 解析工具是什么？

<details>
<summary>显示答案</summary>

**答案：jq**

</details>

13. 哪个 SSH 选项用于堡垒机跳转？

<details>
<summary>显示答案</summary>

**答案：ProxyJump (or -J)**

</details>

14. 什么命令用于监控磁盘 I/O？

<details>
<summary>显示答案</summary>

**答案：iostat**

</details>

15. Pod service account token 的路径是什么？

<details>
<summary>显示答案</summary>

**答案：/var/run/secrets/kubernetes.io/serviceaccount/token**

</details>

## 实践题

16. 编写一个脚本，其中 DATABASE_URL 为必需项，TIMEOUT 默认值为 30。

<details>
<summary>显示答案</summary>

```bash
#!/bin/bash
: ${DATABASE_URL:?"DATABASE_URL required"}
TIMEOUT=${TIMEOUT:-30}
```

</details>

17. 编写一个命令，以 JSON 形式输出重启次数为 3 次或以上的 Pods。

<details>
<summary>显示答案</summary>

```bash
kubectl get pods -A -o json | jq '[.items[] | select([.status.containerStatuses[]?.restartCount] | add >= 3)]'
```

</details>

18. 编写一个通过堡垒机同步 yaml 文件的 rsync 命令。

<details>
<summary>显示答案</summary>

```bash
rsync -avzP --include='*.yaml' --exclude='*' -e "ssh -J bastion" /src/ user@host:/dest/
```

</details>

## 高级题

19. 编写一个节点诊断脚本。

<details>
<summary>显示答案</summary>

```bash
#!/bin/bash
echo "=== System ===" && uptime && free -h && df -h
echo "=== kubelet ===" && systemctl status kubelet --no-pager
```

</details>

20. 说明 ConfigMap 环境变量与 volume mount 的差异。

<details>
<summary>显示答案</summary>

- 环境变量：在 Pod 启动时加载，变更需要重启
- Volume Mount：自动更新（约 1 分钟），无需重启

</details>

---

[返回学习资料](../../basics/02-linux-advanced.md)
