# 8. 综合实训：从 Web 服务故障到容器与云

> **学习基线**：Ubuntu Server 24.04 LTS，另提供 Rocky Linux 9 路径
>
> **最后更新**：2026 年 9 月 15 日

**前置条件：**[第 1–7 课](README.md#course-map)、两台虚拟机的实验地址、已验证的 SSH 密钥登录，以及一条允许实验客户端访问 TCP 8000 的规则。先停止第 7 课的 Web 服务器。

**学习结果**：记录一个小型 Web 服务的健康状态，然后一次只在一个网络层重现、诊断和恢复故障。随后将同样的问题用于 Docker 和 Kubernetes。预计用时约 3–4 小时。

## 任务和健康基线 {#baseline}

任务是“客户端从服务器读取 `/health.txt`”。无需 Web 框架或云账户。

**服务器终端 A：**

```bash
LAB_WEB=$(mktemp -d /tmp/net-capstone.XXXXXX)
printf 'healthy\n' > "$LAB_WEB/health.txt"
timeout 300 python3 -m http.server 8000 \
  --bind 192.0.2.20 --directory "$LAB_WEB"
```

五分钟限制到期后，用相同命令重新启动。检查终端输出，避免把人为停止的服务器误判为网络故障。此目录中只保留本练习文件。

**服务器终端 B：**

```bash
ip -br address
ip route get 192.0.2.10
sudo ss -ltnp 'sport = :8000'
```

**客户端：**

```bash
ip route get 192.0.2.20
curl --disable --noproxy '*' --connect-timeout 2 --max-time 5 \
  -i http://192.0.2.20:8000/health.txt
curl --disable --noproxy '*' --connect-timeout 2 --max-time 5 \
  --resolve lesson.test:8000:192.0.2.20 \
  -i http://lesson.test:8000/health.txt
```

两条路由都必须使用实验网卡，监听器必须是 `192.0.2.20:8000`，且两次请求都必须返回 HTTP 200，并在响应正文中包含 `healthy`。`--resolve` **只为本次 curl 调用提供主机/端口地址映射**，不会更改系统 DNS 或其他应用的解析行为。

如果基线不通过，应先检查第 4–6 课中的配置和规则。基线正常之前不要引入新故障。

## 一次重现一种故障 {#faults}

每个实验都从健康基线开始，并在恢复后重复健康请求。普通 `curl` 请求即使收到 HTTP 404 也可能以退出状态 0 结束，因此应读取 HTTP 状态行。需要将 HTTP 错误视为失败的自动化可显式选择 `--fail-with-body` 等受支持选项。

### A. 将名称解析与 IP 连通性分开

在客户端上，不使用 `--resolve` 发送对比请求。

```bash
getent ahostsv4 lesson.test
curl --disable --noproxy '*' --connect-timeout 2 --max-time 5 \
  -i http://lesson.test:8000/health.txt
```

如果没有另行注册 `lesson.test`，此实验通常会导致名称解析失败。如果已在 `/etc/hosts` 或本地 DNS 中配置该名称，应记录实际映射，而不是预期它会失败。在相同环境中检查前面的 IP 和 `--resolve` 请求是否成功。

**诊断**：如果 IP 请求成功但名称查找失败，应先调查名称解析。这并不能证明特定 DNS 服务器故障，也不能证明互联网范围内的 DNS 服务中断。**恢复**：继续使用健康请求中的 `--resolve` 映射；临时实验无需覆盖系统解析器。

### B. 应用路径错误

在客户端请求一个不存在的文件。

```bash
curl --disable --noproxy '*' --connect-timeout 2 --max-time 5 \
  -i http://192.0.2.20:8000/missing.txt
```

**诊断**：收到 HTTP 404 表示服务器已针对该请求返回了 HTTP 响应。没有理由重置所有路由和防火墙设置。应将请求路径与服务器日志进行比较。**恢复**：重新请求 `/health.txt`。

### C. 错误的监听地址

在服务器终端 A 中按 Ctrl+C 停止服务器。在**同一个终端**中，仅更改绑定地址。

```bash
timeout 300 python3 -m http.server 8000 \
  --bind 127.0.0.1 --directory "$LAB_WEB"
```

服务器终端 B：

```bash
sudo ss -ltnp 'sport = :8000'
curl --disable --noproxy '*' --max-time 5 \
  -i http://127.0.0.1:8000/health.txt
```

确认客户端对原始 `192.0.2.20:8000` 的请求失败，同时服务器自身对 loopback 的请求成功。防火墙行为也会影响故障表现为拒绝连接还是超时。`ss` 显示 `127.0.0.1` 监听器，这是关键证据。

**恢复**：在终端 A 按 Ctrl+C，然后使用健康命令和 `--bind 192.0.2.20` 重启。一台虚拟机的 loopback 不是另一台虚拟机的 loopback。

### D. 使用证据验证防火墙假设 {#firewall-fault}

只使用第 6 课中选定的**那一种管理器**，并在服务器的虚拟机管理程序控制台上操作。本故障仅移除课程设置的 TCP 8000 允许规则。TCP 22 允许规则、实验拒绝规则、默认策略、区域/配置文件分配以及管理网卡都保持不变。先完成可选的 Fail2ban 实验，以免后台封禁变更干扰本测试。

**服务器终端 B，普通用户**：根据记录的虚拟机管理程序 MAC 地址重新识别两块网卡；不假设第 6 课的变量仍然存在。

```bash
ip -br link
read -r -p 'Server lab NIC verified by MAC: ' LAB_IF
read -r -p 'Server management NIC verified by MAC: ' MGMT_IF
ip -4 -br address show dev "$LAB_IF"
ip -4 -br address show dev "$MGMT_IF"
ip -4 route
sudo ss -ltnp 'sport = :8000'
```

确认实验网卡上为 `.20/24`、网卡名称彼此不同、管理网卡未变，并且 `.20:8000` 仍有健康监听器。按下方说明记录当前规则。如果服务器计时器已过期，应在服务器终端 A 中只使用其现有目录重新运行 `timeout 300 python3 -m http.server 8000 --bind 192.0.2.20 --directory "${LAB_WEB:?missing existing web directory}"`。不要同时引入“服务器已停止”的故障。

**客户端，普通用户**：从记录中恢复第 5 课已存在的密钥目录和普通服务器账户。不要新建密钥，也不要绕过已验证的主机记录。

```bash
read -r -p 'Existing lesson-5 client key directory: ' SSH_LAB_DIR
read -r -p 'Normal account on the server: ' SERVER_USER
ls -l -- "${SSH_LAB_DIR:?missing key directory}/id_ed25519" \
  "${SSH_LAB_DIR:?missing key directory}/known_hosts"
```

在该客户端终端中只需定义一次这个简短 shell 函数。调用 `check_lab_ssh` 会启动一个**新的** SSH 连接，显示远端账户/连接信息，然后返回客户端；它不会创建文件或服务。

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

允许出现私钥**口令短语提示**；不要求 agent 已解锁。远端账户密码回退已禁用。`-F /dev/null` 可避开无关的客户端配置，禁用多路复用则避免复用旧的已认证连接。预期连接为普通账户，并从 `.10` 连接到 `.20` 的 22 端口。如果此项**故障前检查**或健康 HTTP 请求失败，应先停止，不要修改任何规则。还应保留/重新检查单独必需的管理 SSH 路径。

#### UFW：只更改已保存并已应用的 HTTP 允许规则

**Ubuntu 服务器终端 B，sudo：**

```bash
sudo ufw status numbered
sudo ufw show added
```

只有在 UFW 已启用，并且存在第 6 课按以下顺序设置的三条课程规则时才能继续：**1：`.10`→`.20` 的 TCP 22 允许规则，应用于 `LAB_IF`；2：单独的 TCP 8000 允许规则；3：同接口/目的地址上的 TCP `22,8000` 拒绝规则**。记录每条规则的完整规格。如果仍有旧的合并 `22,8000` 允许规则，或规则顺序不同，应先修正第 6 课的设置；删除一条端口规则并不能还原多端口规则。

只移除 HTTP：

```bash
sudo ufw delete allow in on "$LAB_IF" proto tcp \
  from 192.0.2.10 to 192.0.2.20 port 8000
sudo ufw status numbered
sudo ufw show added
```

确认 TCP 22 允许规则仍在第一位，实验拒绝规则现在位于第二位。此操作会同时更改已保存和已应用的 UFW 状态。不要修改这两条规则或默认策略。然后执行下方的**故障期间检查**。

**在同一 Ubuntu 终端恢复**：确认拒绝规则仍位于第二位，然后在第 2 位插入 HTTP 规则，确保其**位于该拒绝规则之前**：

```bash
sudo ufw insert 2 allow in on "$LAB_IF" proto tcp \
  from 192.0.2.10 to 192.0.2.20 port 8000 comment 'network-beginner-http'
sudo ufw status numbered
sudo ufw show added
```

预期顺序为原 SSH 允许规则 → HTTP 允许规则 → 实验拒绝规则，且来源/接口/目的范围与原先一致。若将允许规则附加在拒绝规则之后，HTTP 仍会被拒绝；删除规则的逆操作还包括恢复其位置。如果其他规则改变了位置，应停止操作并根据记录的顺序重新建立规则，而不要使用过时的位置数字。然后继续执行下方的恢复后检查。

#### firewalld：仅移除运行时 HTTP 规则，并保留已保存策略

**Rocky 服务器终端 B**：分配操作使用普通用户；防火墙查询使用 sudo。

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

预期只有实验网卡位于 `network-beginner`，管理区域保持原样，四项查询均返回 `yes`。这要求使用第 6 课保留的永久规则，而不是会过期的试用规则。记录两种配置，并检查是否存在更宽泛、仍可能允许 HTTP 的策略。

只移除**运行时 HTTP 规则**：

```bash
sudo firewall-cmd --zone=network-beginner --remove-rich-rule="$RULE8000"
sudo firewall-cmd --zone=network-beginner --query-rich-rule="$RULE8000"
sudo firewall-cmd --permanent --zone=network-beginner --query-rich-rule="$RULE8000"
sudo firewall-cmd --zone=network-beginner --query-rich-rule="$RULE22"
sudo firewall-cmd --permanent --zone=network-beginner --query-rich-rule="$RULE22"
```

预期输出为 `no`、`yes`、`yes`、`yes`；`no` 的退出状态非零，在这里是预期结果。执行故障期间检查。不要执行 reload、重启或使用 `--runtime-to-permanent`：重新加载会重新应用已保存的 HTTP 规则，而将运行时配置复制到永久配置则会无意中持久化这项故障。

**从同一个 Rocky 终端恢复**，不要全局 reload，也不要修改永久配置：

```bash
sudo firewall-cmd --zone=network-beginner --add-rich-rule="$RULE8000"
sudo firewall-cmd --zone=network-beginner --query-rich-rule="$RULE8000"
sudo firewall-cmd --permanent --zone=network-beginner --query-rich-rule="$RULE8000"
sudo firewall-cmd --zone=network-beginner --query-rich-rule="$RULE22"
sudo firewall-cmd --permanent --zone=network-beginner --query-rich-rule="$RULE22"
```

四项查询都应再次返回 `yes`。将运行时/永久规则列表与记录的基线比较：已保存规则从未更改，运行时 HTTP 规则也已按相同范围恢复。若已保存策略发生意外变化，应根据记录调查，而不是批量覆盖。

#### 故障期间和恢复后的检查

**客户端，同一普通用户和同一终端**：HTTP 移除后、恢复后都运行以下命令对，并额外执行故障前检查。

```bash
check_lab_ssh
curl --disable --noproxy '*' --connect-timeout 2 --max-time 5 \
  -i http://192.0.2.20:8000/health.txt
```

故障期间，新的仅密钥 SSH 检查必须成功。在记录的课程策略下，HTTP 请求应失败，同时服务器监听器仍应位于 `.20:8000`。如果 SSH 失败，只从服务器控制台恢复被移除的 HTTP 权限，再比较未变化的 SSH 规则/路径，然后停止：这不能证明你只引入了 HTTP 故障。如果 HTTP 仍然成功，应检查其他匹配的允许规则、区域/默认行为、监听器和分组证据；不能仅因删除了一条规则就宣称流量已被阻止。

恢复后，要求新的仅密钥 SSH 检查成功，并且 HTTP 返回 200 和 `healthy`。在服务器终端 B 上，重复执行 `sudo ss -ltnp 'sport = :8000'`、相关规则查询/列表、`ip -4 -br address show dev "$MGMT_IF"` 和 `ip -4 route`；将结果与故障前记录比较，并重新检查所需的管理访问。分别记录故障前、故障期间和恢复后的观测结果。本文档编写时并未实际在来宾系统中执行这些步骤，因此说明中不声称已完成执行。

## 报告和完成标准 {#capstone-report}

记录实验地址和结果，不要记录密码、私钥或真实用户流量。

| 字段 | 需要记录的内容 |
|---|---|
| 环境 | 发行版、内核、实验网卡、客户端/服务器地址、防火墙管理器 |
| 健康状态 | 路由、监听器、HTTP 状态和正文 |
| 症状 | 哪台主机发送了哪项请求，并收到什么结果 |
| 假设 | 名称解析、路由、监听器、防火墙或 HTTP |
| 证据 | 相关命令、时间、地址/端口和观测结果 |
| 证伪 | 如果假设不成立，预期看到什么 |
| 变更和恢复 | 单项变更及确切的恢复步骤 |
| 复核 | 健康 HTTP 200、SSH 密钥访问、实验/管理网卡状态 |

**通过标准**：能够区分并恢复 A–C，并能说明实际规则和观测结果是否支持 D。满足全部五项标准：识别环境、分层提出假设、提供证据、进行范围明确的变更/恢复，以及恢复后验证。缺少任何一项时都应回到相关课程。完成速度并非评分标准。

## 将这些问题应用于 Docker 和 Kubernetes {#container-cloud-map}

掌握虚拟机间故障诊断后，再引入容器。此表用于映射后续学习中的角色，并不表示每个分组都必然按行所列顺序经过。

| 所学内容 | Docker | Kubernetes | 云 |
|---|---|---|---|
| 进程地址/端口 | 容器网络命名空间内的监听器 | Pod 监听器；Pod 内共享网络 | 后端进程和负载均衡器目标端口 |
| 链路和路由 | veth、Linux bridge 和依赖环境的 NAT | 由 CNI 配置的 Pod 路径、覆盖网络或原生路由 | VPC 子网、路由和连接边界 |
| 名称解析 | 用户自定义 bridge 上的容器名称 | Service 名称和集群 DNS | 组织/云 DNS 和私有名称 |
| 访问规则 | 发布端口和主机转发规则 | NetworkPolicy 及其实现方式 | 分层控制，例如安全组 |
| 观测点 | 主机与容器命名空间 | 节点、Pod 和 Service 实现 | 客户端、负载均衡器、节点和可用区边界 |

Docker **bridge** 通常用于连接同一主机上的容器；**overlay** 则是在底层网络上构建虚拟网络。Docker Swarm overlay 实践需要额外准备工作，例如多个主机。Kubernetes CNI 是独立的接口/插件生态：照搬 Docker bridge 拓扑并不能创建 Kubernetes 集群。

同样，`localhost`、Pod IP、Service IP 和外部入口是不同的观测目标。主机防火墙规则、容器转发规则和 CNI 策略不是一组可以互换使用的规则。

## 后续实践路径 {#next-path}

如需按结构继续学习，请遵循[进阶网络学习路径](../expert/README.md)。该路径会将以下单篇指南串联为阅读、实验和评估流程。

1. 阅读[容器技术](../../basics/03-container-technology.md)，学习命名空间、bridge 和发布端口。
2. 在 [Linux 网络诊断](../07-linux-network-diagnostics.md)中测量下一跳、ICMP 和 PMTU。先阅读该指南中的 Docker 前置条件、范围和清理要求。
3. 学习[Kubernetes 入门](../../basics/04-kubernetes-introduction.md)和 [Pod/工作负载](../../core/02-pods-and-workloads.md)，然后完成 [Service/DNS 实验](../../labs/core/03-services-networking-lab.md)。
4. 学习 [eBPF 基础](../../basics/05-ebpf-fundamentals.md)，然后比较 [Cilium](../cilium/README.md) 和 [Calico](../calico/README.md)。
5. 需要 AWS 时，学习 [EKS 网络](../../eks/03-eks-networking-part1.md)、[VPC CNI](../01-vpc-cni.md) 和[负载均衡](../03-aws-lb-controller.md)。创建资源前，应分别检查每份指南中的成本、权限和清理要求。
6. 开展性能工作时，应先阅读[内核网络栈](../../kernel/02-network-stack.md)和 [Pod 基准测试](../06-pod-network-benchmark.md)中的测量条件。不要将小型 HTTP 练习泛化为云吞吐量结果。

## 清理

先在终端 A 中停止练习服务器，然后在同一终端删除练习文件。

```bash
rm -- "${LAB_WEB:?}/health.txt"
rmdir -- "${LAB_WEB:?}"
```

记录是否会将第 6 课的规则留给后续练习使用。结束整个课程时，应使用各课的恢复流程，或者恢复到**自己的虚拟机快照**。验证管理网卡和已有 SSH 访问，然后正常关闭虚拟机。

## 参考资料

- [Python http.server](https://docs.python.org/3.12/library/http.server.html)
- [curl 地址映射](https://curl.se/docs/manpage.html)
- [Ubuntu 24.04 UFW：规则顺序、多端口规则和删除](https://manpages.ubuntu.com/manpages/noble/man8/ufw.8.html)
- [firewalld：运行时/永久配置和 rich-rule 操作](https://firewalld.org/documentation/man-pages/firewall-cmd.html)
- [OpenSSH 客户端选项和连接共享](https://man.openbsd.org/ssh_config)
- [Docker bridge](https://docs.docker.com/engine/network/drivers/bridge/)
- [Docker overlay](https://docs.docker.com/engine/network/drivers/overlay/)
- [Kubernetes 网络模型](https://kubernetes.io/docs/concepts/services-networking/)

[上一课：监控与性能](07-monitoring-performance.md) · [测验](../../quizzes/networking/beginner/08-container-cloud-capstone-quiz.md) · [返回课程](README.md)
