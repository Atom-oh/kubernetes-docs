# Linux 网络性能：先测量，再解释

> **实验基线**：自有的 Ubuntu Server 24.04 LTS 或 Rocky Linux 9 来宾系统；有界的回环接口观测
>
> **最后更新**：2026 年 9 月 15 日

## 目的与先决条件 {#purpose}

本练习手册要求你判断：一次缓慢的事务究竟是在等待应用、传输层、内核，还是网络路径。
最终交付物是一份可复现的测量报告，其中包含相互竞争的解释、反向证据和恢复步骤。
本文不承诺固定延迟、吞吐量提升或基准分数。

请先完成[入门课程](../beginner/README.md)，尤其是[监控课程](../beginner/07-monitoring-performance.md)。
阅读[内核网络栈](../../kernel/02-network-stack.md)，从套接字/VFS 一直看到发送、接收和钩子的位置。
然后查看 [Linux 网络诊断](../07-linux-network-diagnostics.md#tcp-buffer-lab)，了解现有 HTTP 辅助程序和套接字状态的解释。
[协议练习](01-protocol-projects.md)提供字节流和证据相关术语。
稍后再读[现有 Pod 基准测试指南](../06-pod-network-benchmark.md)；回环接口上的数字不代表 CNI 基准测试结果。

你需要掌握 Linux 进程和文件操作、基础 Python、TCP 序列号与窗口知识，以及比特、字节和秒的计算。
C 语言和驱动开发是可选扩展，并非完成有界 Python 练习的先决条件。
编写本章时没有运行网络或云实验；下文的标准是留给将来在自有来宾系统上执行的操作说明。

## Bootlin 与主要阅读材料 {#readings}

截至 **2026 年 9 月 15 日**，[Bootlin Linux 网络培训页面](https://bootlin.com/training/networking/)可访问。
其可免费下载的[幻灯片](https://bootlin.com/doc/training/networking/networking-slides.pdf)和 [EspressoBin 实验说明](https://bootlin.com/doc/training/networking/networking-espressobin-labs.pdf)可供学习参考。
公开资料不包含免费讲师指导、随课程提供的开发板，也不保证与任意硬件兼容。

| 阅读资料 | 需要的背景知识 | 在本章要回答的问题 |
|---|---|---|
| Bootlin 网络栈和用户空间接口章节 | Linux 管理、套接字和协议分层 | 应用程序中的字节在何处变成排队的内核工作？ |
| Bootlin 驱动、NAPI 和硬件实验 | 扎实的 C 语言、内核/模块开发、中断、DMA，以及实验使用的开发板和工具链设置 | 哪些结论必须依赖真实驱动和网卡才能得出？ |
| [内核 NAPI 文档](https://docs.kernel.org/networking/napi.html) | 中断与轮询的区别 | 哪些工作通过轮询执行，在什么预算/上下文下进行？ |
| [内核扩展性文档](https://docs.kernel.org/networking/scaling.html) | CPU 队列和流哈希 | 是 RSS 还是 RPS 选择了处理 CPU？ |
| [分段卸载](https://docs.kernel.org/networking/segmentation-offloads.html) | MTU/MSS 和数据包观测位置 | 为什么抓包中显示的数据单元可能大于线上实际单元？ |
| [TCP sysctl 文档](https://docs.kernel.org/networking/ip-sysctl.html) | 套接字内存、窗口和自动调优 | 哪个限制属于策略，哪个是单条流的观测值？ |
| [iproute2 `ss` 源码手册](https://github.com/iproute2/iproute2/blob/main/man/man8/ss.8)和 [`tc` 源码手册](https://github.com/iproute2/iproute2/blob/main/man/man8/tc.8) | TCP 状态和队列计数器 | 显示的各个数值具体统计什么？ |

对于 Bootlin 硬件学习路径，请记录实验 PDF 版本、所需开发板、串口控制台、引导加载程序、内核源码树/配置及交叉工具链。
核对过的课程使用搭载 Marvell Armada 3720 ARM64 处理器的 EspressoBin；不要假设入门课程中的虚拟机可以替代该文档所述环境。
如果无法获得该环境，请完成数据包路径分析，并将硬件观测标注为不可用。
培训报名和证书与本练习手册要求的基于证据的完成标准彼此独立。

## 在运行命令之前设计测量方案 {#measurement-design}

开始前先填写这张实验卡。空白项表示仍需完成，并不代表可以编造结果。

| 字段 | 核心练习选择 |
|---|---|
| 假设 | 延迟读取客户端正文会增加应用层完成时间，但不需要网络路径丢包 |
| 资源所有者/观察者 | 在一台可随时丢弃的来宾系统中使用你自己的用户；记录来宾名称和网络命名空间 |
| 客户端/服务器 | Python 客户端和仓库中的 HTTP 辅助程序；仅使用 `127.0.0.1:18080` |
| 变量 | 请求/回显正文为 64 或 4096 字节；客户端暂停读取 0 或 0.15 秒 |
| 固定控制条件 | 一次只发送一个请求；每个请求使用新的 TCP 连接；端点/辅助程序相同 |
| 预算 | 1 次预热加 15 次测量请求；每个方向的载荷均少于 42 KiB |
| 截止时间 | 客户端整体 60 秒、套接字操作超时 2 秒；服务器 180 秒 |
| 观察者 | 客户端单调时钟时长；限定范围的 `ss`；接口/qdisc 前后计数器 |
| 失败规则 | 内容/状态失败、出现意外监听器、工具缺失或超出截止时间时停止 |
| 恢复 | 关闭自己启动的客户端，停止自己前台运行的服务器，并确认监听器已移除 |

0.15 秒暂停是一个**输入参数**，不是实测网络延迟。
这个工作负载刻意保持很小，不会迫使接收窗口耗尽，也不会让回环接口饱和。
不要用它的有效吞吐量宣称网卡容量、互联网延迟或路由收敛性能。
实际可行时让来宾系统保持空闲，并记录其他工作负载；回环计数器还包括其他进程产生的流量。

## 工具、角色与操作范围 {#readiness}

如果缺少软件包，请按照[入门课程中的来宾工具准备](../beginner/README.md#guest-tools)操作，包括预览安装事务和记录恢复信息。
只在自有来宾系统上为所选路径安装必需的工具；基础镜像不保证预装这些工具。

| 工具 | Ubuntu 提供的软件包 | Rocky 提供的软件包 | 用途 / 权限 |
|---|---|---|---|
| `python3` 3.9+ | `python3` | `python3` | 客户端/服务器，普通用户 |
| `ip`、`ss` | `iproute2` | `iproute` | 限定范围的观测，普通用户 |
| `tc` | `iproute2` | `iproute-tc` | 读取 qdisc 计数器；允许时用普通用户执行 |
| `timeout`、`sha256sum` | `coreutils` | `coreutils` | 限制执行时长并识别辅助程序 |
| `tcpdump` | `tcpdump` | `tcpdump` | 可选抓包；仅抓包时使用 sudo |
| `ethtool` | `ethtool` | `ethtool` | 可选地检查现有网卡；某些查询需要权限 |
| `pidstat` | `sysstat` | `sysstat` | 可选的进程 CPU 采样 |
| `bpftool`、`bpftrace` | 取决于内核/发行版的软件包 | 取决于内核/发行版的软件包 | 可选；需单独确认提供程序、内核支持和授权 |

不要仅为满足可选项而安装内核软件包或启用跟踪。
如果使用 BPF 工具，请记录已安装软件包的所属项、工具/内核版本、BTF 是否可用，以及遇到的访问错误。
仅仅存在某条命令，并不能证明你具有可用的 BPF 权限。

在来宾系统中的仓库根目录执行：

```bash
command -v python3 ip ss tc timeout sha256sum
python3 --version
uname -r
ip -Version
ss -V
tc -V
sha256sum examples/networking/foundations/http_lab.py
ss -ltn 'sport = :18080'
```

如果监听器过滤结果中存在任何监听器，请停止并统一选择其他空闲端口；绝不要停止无关服务。
使用 `mkdir -m 700 linux-evidence-01` 创建新的私有目录；如果名称已存在，请换一个。
在目录中记录仓库版本、操作系统版本、工具版本、命名空间以及开始和结束的 UTC 时间。
下面的客户端/服务器命令均应以普通用户身份，在同一来宾系统和命名空间中执行。

## 沿数据处理路径观察 {#packet-path}

使用现有内核章节中的图，然后补上以下区别。
常见的原生驱动接收路径为：NIC 队列 → NAPI 轮询 → 可选的原生 XDP → 协议栈/传输层 → 套接字 → 应用程序。
驱动/设备卸载模式和通用 XDP 位于不同位置；标注所用模式，不要把所有钩子都画在同一位置。
发送方向的工作从套接字/传输层经过路由和适用的排队机制后到达设备。

| 机制 | 改变的内容 | 观测方式及反例 |
|---|---|---|
| NAPI | 通过轮询处理驱动事件，通常与中断协同工作 | 轮询预算不保证应用层延迟 |
| RSS | 硬件将流分配到不同接收队列 | 单条流仍可能哈希到一个队列；增加队列不会拆分每条流 |
| RPS | 软件选择用于接收处理的 CPU | CPU 分布情况不能证明 NIC 执行了 RSS |
| GSO / TSO | 由软件/设备将较大的发送单元分段 | 主机抓包中的大单元不一定是过大的线上帧 |
| GRO | 在更高层处理之前合并接收工作 | 抓包中的单元数量不一定等于物理帧数量 |
| qdisc | 对适用的出站工作排队/调度 | 回环接口上的 `noqueue` 不能证明其他地方的物理 NIC 没有排队 |
| 套接字窗口 | 接收方流量控制和发送方拥塞许可量 | 缓冲区配置值较大，并不能证明任一窗口都能完全使用 |

回环接口没有物理 RSS 队列、链路串行化过程或交换机路径，不能用来做相关基准测试。
不要把回环处理细节直接套用到物理驱动上。

对于**已存在且由你管理的虚拟机流量**，请改为编写书面的观测计划：识别两个端点、现有接口/路由、流五元组、所有者和原有流量预算。
只在确认的实验接口上，且该接口支持时，执行只读的 `ethtool -k`、`ethtool -l`、`ethtool -x` 和 `ethtool -S` 查询。
对于“不支持”或“权限拒绝”的情况如实记录，不要更改驱动、通道数量或卸载设置。
核心路径不需要执行影响所有接口的命令，也不需要创建新的虚拟机或云资源。

## 有界回环实验 {#bounded-experiment}

启动辅助程序前，保存初始状态：

```bash
ip -s link show dev lo > linux-evidence-01/link-before.txt
tc -s qdisc show dev lo > linux-evidence-01/qdisc-before.txt
ss -ltn 'sport = :18080' > linux-evidence-01/listener-before.txt
```

启动终端 A 中由你管理的服务器，等待它输出就绪消息：

```bash
python3 examples/networking/foundations/http_lab.py --port 18080 --duration 180
```

在终端 C 中，紧挨着客户端启动有界套接字观察程序：

```bash
timeout 25s bash -c '
  for sample in {1..40}; do
    date -u +%FT%T.%NZ
    ss -tinm state established "( sport = :18080 or dport = :18080 )"
    sleep 0.5
  done
' > linux-evidence-01/sockets.txt
```

在终端 B 中运行这个原始测量客户端。它不会查询 DNS，也不会读取代理配置。
最多发送 16 个请求，其中包含预热请求；每个连接都会在 `finally` 中关闭。
请求之间暂停 0.25 秒，也可以限制请求频率。

```bash
timeout --signal=INT --kill-after=2s 60s python3 - <<'PY' \
  > linux-evidence-01/transactions.jsonl
import datetime
import http.client
import json
import time

phases = [("warmup", 64, 0.0, 1),
          ("small", 64, 0.0, 5),
          ("large", 4096, 0.0, 5),
          ("reader_pause", 4096, 0.15, 5)]
for phase, size, pause, count in phases:
    for sample in range(count):
        connection = http.client.HTTPConnection("127.0.0.1", 18080, timeout=2)
        payload = b"x" * size
        row = {"phase": phase, "sample": sample, "bytes": size,
               "pause_s": pause,
               "utc": datetime.datetime.now(datetime.timezone.utc).isoformat()}
        start = time.perf_counter()
        try:
            connection.request("POST", "/echo", body=payload,
                               headers={"Content-Type": "application/octet-stream"})
            response = connection.getresponse()
            headers_at = time.perf_counter()
            time.sleep(pause)
            body = response.read()
            finished = time.perf_counter()
            if response.status != 200 or body != payload:
                raise ValueError("Unexpected status or echo content")
            row.update(status=response.status, ok=True,
                       headers_ms=(headers_at - start) * 1000,
                       read_ms=(finished - headers_at) * 1000,
                       total_ms=(finished - start) * 1000)
        except Exception as error:
            row.update(ok=False, error=type(error).__name__,
                       detail=str(error))
            print(json.dumps(row), flush=True)
            raise SystemExit(1)
        finally:
            connection.close()
        print(json.dumps(row), flush=True)
        time.sleep(0.25)
PY
```

立即保存客户端退出状态。运行被中断或成功记录少于 16 条，都表示实验未完成。
外层超时可能在最终 JSON 记录写入前到期；缺失数据不等于零延迟。
`headers_ms` 包括从建立连接/发送请求到解析响应标头所需的时间；它不是纯 RTT，也不是 curl 的 TTFB 指标。
`read_ms` 包括有意设置的暂停时间和读取正文的时间；库缓冲区可能已经保存了一部分内容。
`total_ms` 测量到响应正文读取结束为止，不包括之后请求间的暂停时间。

客户端和观察程序结束后，收集结束状态：

```bash
ip -s link show dev lo > linux-evidence-01/link-after.txt
tc -s qdisc show dev lo > linux-evidence-01/qdisc-after.txt
ss -tinm state established '( sport = :18080 or dport = :18080 )' \
  > linux-evidence-01/sockets-after.txt
```

**预期观测**：所有完成的请求都会返回相同的回显字节；读取暂停阶段的完成时间应包含设置的暂停时间。
**反向观测**：连接持续时间很短，因此 `ss` 采样结果可能为空；队列为零并不证明观察程序有故障。
较小的回显载荷可能不会产生可见的反压或重传。
计数器增量涵盖整个回环接口，因此不要把每个增量都归因于该客户端。
如果回显失败，请先保留失败记录和服务器状态，再进行诊断；不要悄悄重试，直到只剩成功结果。

若要获取可选的数据包证据，请在新的证据目录中使用[项目 B 的有界抓包方案](01-protocol-projects.md#stream-project)。
该方案限制为 20 秒/120 个数据包，可能无法捕获本次运行中的所有连接；请记录覆盖不完整的情况，不要把未捕获的数据包当作丢包。
不要为了让抓包结果看起来熟悉而禁用校验和/分段卸载。

**恢复**：使用 Ctrl+C 停止自己在前台运行的服务器，或等待其 180 秒截止时间到期。
客户端和观察程序会在达到各自限制后结束；必要时只中断这些前台进程。
确认 `ss -ltn 'sport = :18080'` 没有返回监听器；TIME_WAIT 套接字可能会正常保留。
保留证据目录；如完成审查后要删除文件，只删除其中指定的文件。
此练习没有更改 qdisc、sysctl、NIC 卸载设置、路由或 BPF 挂载。

## 解释窗口、丢包和延迟 {#interpretation}

将[套接字队列的含义](../../kernel/02-network-stack.md#ss-tcp-queues)与原始 `ss` 采样结果进行对照。
对于 ESTABLISHED 状态，`Recv-Q` 表示已接收但等待应用程序读取的数据；`Send-Q` 表示尚未确认的数据，其中也包括尚未发送的数据。
LISTEN 状态下的列表示 accept 队列/积压连接，而不是载荷占用量。
`skmem` 统计内存及开销，不一定等于字节流、通告窗口或 `cwnd`。
如果输出了 `cwnd`，其单位通常为分段数；与字节数比较前，请先确认相应的 MSS 和单位。

对于一条**假设**为 100 Mbit/s、RTT 为 40 ms 的路径：
`BDP = 100,000,000 bit/s × 0.040 s ÷ 8 = 500,000 bytes`。
这是算术示例，不是测量结果，也不是设置缓冲区的命令。
请结合[BDP 与套接字策略](../../kernel/02-network-stack.md#tcp-bdp-reasoning)进行分析。
较小的有效窗口可能限制吞吐量，但提高全局限制并不能证明窗口导致了本次运行的延迟。

排除预热结果；根据实际记录报告各阶段的样本数、失败数、最小值、中位数和最大值。
五个样本不足以支撑可信的 p99 服务目标或生产容量结论。
响应载荷的比特数除以事务耗时，得到这项操作的应用有效吞吐量，其中包括连接和处理延迟。
这既不是以太网线路速率，也不能直接衡量拥塞。

| 观测 | 可能的解释 | 区分其他可能性所需的证据 |
|---|---|---|
| 完成耗时高，响应标头耗时正常 | 客户端读取延迟 | 查看客户端阶段和时间戳；不能只凭总耗时就归咎于路由 |
| 接收队列持续存在 | 应用读取较慢或受到调度影响 | 读取进度、CPU 证据和重复的逐流采样 |
| 发送队列持续存在 | 数据尚未发送、缺少 ACK 或接收方受限 | 窗口/重传字段以及通信两端的证据 |
| 重传增加 | 丢包、乱序或虚假重传 | 序列号/时间证据；单个计数器无法确定丢弃位置 |
| tcpdump 抓包有丢弃 | 观察程序处理速度跟不上 | 抓包统计信息；这不能直接说明 TCP/路径发生丢包 |
| qdisc 丢弃增加 | 本地队列策略/压力 | 确认同一时间段/接口并核实流量归属 |

## eBPF/XDP 观测与故障实验设计 {#bpf-observation}

选择工具前，请先阅读[内核 BPF 文档](https://docs.kernel.org/bpf/)和 Bootlin 对钩子的说明。
对于已有、由你管理且有权限的实验环境，可以用 `bpftool prog show` 和 `bpftool net show` 清点现有程序/挂载点。
这些是可选的只读观测；权限不足时应标记为“未观测”，而不是“没有 BPF”。
仅仅存在程序并不能证明这条流量执行了它，也不能证明它提高了吞吐量。

设计一个 tracepoint/kprobe 观测方案，但不要实际加载程序：写明钩子、五元组/命名空间过滤条件、字段、持续时间、事件上限和开销检查方法。
根据该内核的事件格式/BTF 确认所需字段是否存在；绝不要编造适用于所有内核的探针签名。
说明如何统计事件丢失，以及如何把时间戳与客户端样本对应起来。
tracepoint、TC 程序和原生 XDP 程序观测的是不同阶段；在某个钩子处未观察到，并不代表所有阶段都没有。
本练习手册不会挂载、卸载或替换任何 BPF 程序。

**可选 netem 扩展在此仅做设计，不执行**。不要执行影响主机全局的 qdisc/sysctl/卸载设置命令。
为独立管理的命名空间/虚拟机编写一份方案，并确保管理访问不经过受影响的接口。
记录命名空间/虚拟机标识、接口、原有 qdisc 层级/句柄/选项、路由、卸载设置和所有计划修改。
明确唯一的变量、精确且有限的流量/持续时间、基线和预期的反向结果。
执行前必须制定精确的恢复计划：删除根 qdisc 并不能重建任意的原始队列层级。
对于全新且可丢弃的环境，可以将销毁所记录资源 ID 的操作作为恢复边界。
如果无法重建原始状态或不能确定资源归属，方案只能停留在设计阶段。

## 完成与交接 {#completion}

- [ ] 说明 Bootlin 公开资料与硬件环境之间的边界，并记录来源/工具/辅助程序版本。
- [ ] 保留实验卡、原始记录、失败/退出状态、观察覆盖情况和前后计数器。
- [ ] 区分输入延迟和实测耗时、队列字节数和内存，以及 BDP 和已配置缓冲区。
- [ ] 针对缓慢结果给出至少两种合理解释，并说明什么证据可以排除各解释。
- [ ] 标注缺少的网卡/BPF/数据包观测；不要声称未经测量的吞吐量提升。
- [ ] 确认服务器已停止，且没有留下持久配置更改。
- [ ] 完成[测验](../../quizzes/networking/expert/04-linux-performance-quiz.md)，并解释答案。

将这些产物交付给[自动化综合练习](06-automation-capstone.md)。
要了解覆盖网络/MTU，请阅读[数据中心 EVPN](03-datacenter-evpn.md)；要了解额外的路径边界，请阅读[云/CNI 设计](05-cloud-cni-design.md)。
回到[专家课程路线图](README.md)，选择下一个专业方向。
