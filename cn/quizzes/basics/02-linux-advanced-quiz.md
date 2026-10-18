# Linux 运维技能测验

本测验考查你对 Kubernetes 环境中 Linux 运维技能的理解。

## 选择题

1. 哪个命令会使环境变量对子进程可用？
   - A) set
   - B) export
   - C) declare
   - D) env

<details>
<summary>显示答案</summary>

**答案：B) export**

</details>

2. `.bashrc` 会在什么时候执行？
   - A) 仅在登录 shell 中
   - B) 在所有 shell 会话中
   - C) 在非登录交互式 shell 中
   - D) 始终与 .bash_profile 一起执行

<details>
<summary>显示答案</summary>

**答案：C) 非登录交互式 shell**

</details>

3. `${REPLICAS:-3}` 表示什么？
   - A) 将 REPLICAS 设置为 3
   - B) 如果 REPLICAS 未设置或为空，则使用 3
   - C) 从 REPLICAS 中减去 3
   - D) 报错

<details>
<summary>显示答案</summary>

**答案：B) 如果 REPLICAS 未设置或为空，则使用 3**

</details>

4. `awk 'NR>1 {print $1}'` 会执行什么操作？
   - A) 打印所有行的第一个字段
   - B) 只打印第一行
   - C) 打印除表头外各行的第一个字段
   - D) 打印包含第一个字段的行

<details>
<summary>显示答案</summary>

**答案：C) 打印除表头外的第一个字段**

</details>

5. `sed -i 's/old/new/g'` 中的 `g` 有什么作用？
   - A) 忽略大小写
   - B) 替换一行中的所有匹配项
   - C) 只替换一次
   - D) 启用正则表达式

<details>
<summary>显示答案</summary>

**答案：B) 替换一行中的所有匹配项**

</details>

6. `jq -r` 中的 `-r` 有什么作用？
   - A) 递归搜索
   - B) 反向排序
   - C) 不带引号输出原始字符串
   - D) 只读

<details>
<summary>显示答案</summary>

**答案：C) 不带引号输出原始字符串**

</details>

7. `ssh -L 8080:localhost:80 user@server` 表示什么？
   - A) 将服务器的 8080 端口转发到本地的 80 端口
   - B) 将本地的 8080 端口转发到服务器的 80 端口
   - C) 将服务器的 80 端口转发到本地的 8080 端口
   - D) 将本地的 80 端口转发到服务器的 8080 端口

<details>
<summary>显示答案</summary>

**答案：B) 将本地 8080 端口转发到服务器的 80 端口**

</details>

8. vmstat 中的 `wa` 表示什么？
   - A) Web 应用程序 CPU 使用率
   - B) I/O 等待时间百分比
   - C) 警告数量
   - D) 活跃进程数

<details>
<summary>显示答案</summary>

**答案：B) I/O 等待时间百分比**

</details>

9. 哪个命令用于创建 LVM Physical Volume？
   - A) lvcreate
   - B) vgcreate
   - C) pvcreate
   - D) fscreate

<details>
<summary>显示答案</summary>

**答案：C) pvcreate**

</details>

10. `curl -s -o /dev/null -w "%{http_code}" URL` 会输出什么？
    - A) 响应正文
    - B) 响应标头
    - C) HTTP 状态码
    - D) 响应时间

<details>
<summary>显示答案</summary>

**答案：C) HTTP 状态码**

</details>

## 简答题

11. 哪个命令会在当前 shell 中执行文件内容？

<details>
<summary>显示答案</summary>

**答案：source（或 .）**

</details>

12. 用于解析 JSON 的工具是什么？

<details>
<summary>显示答案</summary>

**答案：jq**

</details>

13. 通过 bastion 主机跳转时使用哪个 SSH 选项？

<details>
<summary>显示答案</summary>

**答案：ProxyJump（或 -J）**

</details>

14. 哪个命令用于监控磁盘 I/O？

<details>
<summary>显示答案</summary>

**答案：iostat**

</details>

15. Pod 的 service account token 路径是什么？

<details>
<summary>显示答案</summary>

**答案：/var/run/secrets/kubernetes.io/serviceaccount/token**

这是默认的 projected token 路径；如果禁用了 automount，该文件可能不存在。token 会轮换。

</details>

## 实践题

16. 编写脚本：必须提供 DATABASE_URL；如果未设置 TIMEOUT，则默认值为 30。

<details>
<summary>显示答案</summary>

```bash
#!/bin/bash
: "${DATABASE_URL:?DATABASE_URL required}"
TIMEOUT=${TIMEOUT:-30}
```

</details>

17. 编写命令，以 JSON 输出常规容器与 init container 的合计重启次数至少为 3 的 Pod。

<details>
<summary>显示答案</summary>

```bash
kubectl get pods -A -o json | jq '[.items[] | select(([(.status.containerStatuses[]?, .status.initContainerStatuses[]?) | .restartCount] | add // 0) >= 3)]'
```

</details>

18. 编写 rsync 命令，通过 bastion 主机同步 yaml 文件。

<details>
<summary>显示答案</summary>

```bash
rsync -avzP --prune-empty-dirs --include='*/' --include='*.yaml' --exclude='*' -e "ssh -J bastion" /src/ user@host:/dest/
```

</details>

## 进阶题

19. 编写节点诊断脚本。

<details>
<summary>显示答案</summary>

```bash
#!/bin/bash
echo "=== System ===" && uptime && free -h && df -h
echo "=== kubelet ===" && systemctl status kubelet --no-pager
```

</details>

20. 说明 ConfigMap 环境变量与卷挂载之间的区别。

<details>
<summary>显示答案</summary>

- **环境变量**：在 Pod 启动时加载；值发生变化后，需要重启 Pod 才能应用新值。
- **卷挂载**：更新最终会传播到挂载文件（存在 kubelet 同步周期以及缓存/watch 延迟）。应用程序必须重新读取或重新加载文件。通过 `subPath` 挂载的文件不会收到更新。

</details>

---

[返回学习资料](../../basics/02-linux-advanced.md)

## 核对资料

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
