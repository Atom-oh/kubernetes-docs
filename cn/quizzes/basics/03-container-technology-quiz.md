# 容器技术测验

本测验测试你对容器技术基础、其工作方式以及它们与 Kubernetes 的关系的理解。

## 选择题

1. 以下哪一项不是容器的关键特性？
   - A) 可移植性
   - B) 轻量级
   - C) 完整硬件虚拟化
   - D) 隔离的执行环境
   
<details>

<summary>显示答案</summary>

**答案：C) 完整硬件虚拟化**

**解释：**
容器共享主机 OS 内核，并不会虚拟化硬件。完整硬件虚拟化是虚拟机（VM）的特性。容器提供可移植性、轻量级运行和隔离的执行环境，但它们依赖主机 OS 内核运行。
</details>

2. 容器和虚拟机之间的主要区别是什么？
   - A) 每个容器都需要自己独立的 OS
   - B) 虚拟机的启动时间比容器更快
   - C) 容器共享主机 OS 内核
   - D) 虚拟机使用的资源比容器更少
   
<details>

<summary>显示答案</summary>

**答案：C) 容器共享主机 OS 内核**

**解释：**
容器通过共享主机 OS 内核运行，而每个虚拟机都包含完整的 OS。因此，容器比虚拟机更轻量、启动更快，并且资源效率更高。
</details>

3. 以下哪一项不是 OCI (Open Container Initiative) 兼容的低级容器运行时？
   - A) runc
   - B) crun
   - C) containerd
   - D) gVisor
   
<details>

<summary>显示答案</summary>

**答案：C) containerd**

**解释：**
containerd 是高级容器运行时，提供镜像传输、存储和容器执行管理等功能。runc、crun 和 gVisor 都是 OCI 兼容的低级容器运行时，负责实际的容器创建和执行。
</details>

4. 关于容器镜像层，哪项说法是正确的？
   - A) 每一层都可以独立修改
   - B) 层总是会合并并存储为单个文件
   - C) 层表示相对于前一层的更改
   - D) 每个容器都有自己唯一的一组层
   
<details>

<summary>显示答案</summary>

**答案：C) 层表示相对于前一层的更改**

**解释：**
容器镜像由多个层组成，每一层都表示相对于前一层的更改。这种分层方法使镜像共享和缓存更高效，从而节省存储空间并提高镜像下载速度。层是只读的，当容器运行时，会在顶部添加一个可写层。
</details>

5. 在 Dockerfile 中使用多阶段构建的主要目的是什么？
   - A) 提高构建速度
   - B) 减小最终镜像大小
   - C) 减少安全漏洞
   - D) 支持多个操作系统
   
<details>

<summary>显示答案</summary>

**答案：B) 减小最终镜像大小**

**解释：**
多阶段构建的主要目的是减小最终镜像大小。构建阶段包含源代码编译、依赖安装等所需的所有工具，而运行阶段只带入构建产物，以最小运行时环境创建小镜像。这会将构建工具和中间文件排除在最终镜像之外。
</details>

6. Docker 的默认网络驱动是什么？
   - A) host
   - B) bridge
   - C) overlay
   - D) macvlan
   
<details>

<summary>显示答案</summary>

**答案：B) bridge**

**解释：**
bridge 是 Docker 的默认网络驱动，用于支持同一主机上运行的容器之间通信。该驱动在主机内创建一个虚拟网桥来连接容器。host 驱动直接使用主机网络，overlay 用于多主机通信，macvlan 为容器分配 MAC 地址，使其看起来像物理网络设备。
</details>

7. 对于容器中的持久数据存储，哪种方法使用由 Docker 管理的主机文件系统区域？
   - A) 临时存储
   - B) Volume
   - C) Bind mount
   - D) tmpfs mount
   
<details>

<summary>显示答案</summary>

**答案：B) Volume**

**解释：**
Volume 是由 Docker 管理的主机文件系统区域，是容器中持久数据存储最合适的方法。临时存储是容器的内部文件系统，容器删除时数据会丢失。Bind mount 将特定主机路径挂载到容器中，而 tmpfs mount 仅将数据存储在内存中。
</details>

8. 以下哪一项不是增强容器安全性的方法？
   - A) 以非 root 用户运行容器
   - B) 仅授予必要的 Linux capabilities
   - C) 向所有容器授予管理员权限
   - D) 使用只读文件系统
   
<details>

<summary>显示答案</summary>

**答案：C) 向所有容器授予管理员权限**

**解释：**
向所有容器授予管理员权限会削弱安全性。为了增强容器安全性，应遵循最小权限原则。以非 root 用户运行容器、仅授予必要的 Linux capabilities，并在可能时以只读方式挂载文件系统，都是良好的安全实践。
</details>

9. 哪项 AWS 服务提供 serverless 容器执行环境？
   - A) Amazon EC2
   - B) Amazon ECS
   - C) Amazon Fargate
   - D) Amazon ECR
   
<details>

<summary>显示答案</summary>

**答案：C) Amazon Fargate**

**解释：**
Amazon Fargate 是 AWS 的 serverless 容器执行环境，允许你在不管理服务器的情况下运行容器。Amazon EC2 是虚拟服务器服务，Amazon ECS 是容器编排服务，Amazon ECR 是容器镜像注册表服务。
</details>

10. 以下哪一项不是容器编排工具的主要功能？
    - A) 自动部署和回滚
    - B) 服务发现和负载均衡
    - C) 容器镜像构建
    - D) 自动扩缩容

<details>

<summary>显示答案</summary>

**答案：C) 容器镜像构建**

**解释：**
容器镜像构建通常是 CI/CD 流水线或 Docker 等容器构建工具的职责。容器编排工具（Kubernetes、Docker Swarm 等）的主要功能包括自动部署和回滚、服务发现和负载均衡、自动扩缩容、自愈、配置管理和存储编排。
</details>

11. 容器在未运行时不可能处于以下哪种状态？
    - A) Created
    - B) Exited
    - C) Building
    - D) Paused

<details>

<summary>显示答案</summary>

**答案：C) Building**

**解释：**
容器生命周期状态包括 Created（已创建）、Running（运行中）、Paused（已暂停）、Restarting（重启中）、Exited（已退出）和 Dead（死亡）。Building 是镜像构建过程的状态，不是容器状态。容器是在镜像构建完成后创建的。
</details>

12. 哪种容器重启策略会在 Docker daemon 启动时重启容器，但如果容器是手动停止的，则不会重启？
    - A) no
    - B) on-failure
    - C) always
    - D) unless-stopped

<details>

<summary>显示答案</summary>

**答案：D) unless-stopped**

**解释：**
`unless-stopped` 重启策略会始终重启容器，除非它被明确停止。即使 Docker daemon 重启，容器也会自动启动，但如果用户使用 `docker stop` 命令手动停止了它，daemon 重启后容器不会启动。`always` 会无论手动停止状态如何都进行重启。
</details>

13. 哪个 Docker 命令用于检查容器与其原始镜像之间的文件系统变化？
    - A) docker inspect
    - B) docker diff
    - C) docker logs
    - D) docker history

<details>

<summary>显示答案</summary>

**答案：B) docker diff**

**解释：**
`docker diff` 命令显示容器文件系统与原始镜像之间的变化。在输出中，A 表示 Added 文件，C 表示 Changed 文件，D 表示 Deleted 文件。该命令有助于调试容器运行期间哪些文件被修改。
</details>

## 简答题

14. 基于容器镜像内容、以 SHA256 哈希表示的唯一标识符是什么？

<details>

<summary>显示答案</summary>

**答案：Digest**

**解释：**
Digest 是容器镜像内容的 SHA256 哈希，用作镜像的唯一标识符。与标签不同，如果镜像内容发生变化，Digest 也会变化，因此它用于准确引用特定的镜像版本。示例：`nginx@sha256:2834dc507516af02784808c5f48b7cbe38b8ed5d0f4837f16e78d00deb7e7767`
</details>

15. Dockerfile 中指定容器启动时要运行的命令的指令是什么？

<details>

<summary>显示答案</summary>

**答案：CMD**

**解释：**
CMD 指令指定容器启动时默认运行的命令。例如，`CMD ["node", "server.js"]` 会在容器启动时运行 `node server.js` 命令。CMD 可以通过向 docker run 命令提供参数来覆盖。
</details>

16. Docker 为容器之间通信创建的虚拟网络接口名称是什么？

<details>

<summary>显示答案</summary>

**答案：docker0**

**解释：**
docker0 是 Docker 默认创建的虚拟网桥网络接口。该网桥支持同一主机上运行的容器之间通信，并在容器与外部网络之间进行通信中介。
</details>

17. 限制容器内运行的进程可使用的系统调用的 Linux 安全功能是什么？

<details>

<summary>显示答案</summary>

**答案：seccomp (Secure Computing Mode)**

**解释：**
seccomp 是一种 Linux 内核安全功能，用于限制进程可以使用的系统调用。Docker 等容器运行时使用 seccomp 配置文件限制容器可以执行的系统调用，从而增强安全性。
</details>

18. 用于存储和管理容器镜像的 AWS 服务名称是什么？

<details>

<summary>显示答案</summary>

**答案：Amazon ECR (Elastic Container Registry)**

**解释：**
Amazon ECR (Elastic Container Registry) 是 AWS 的托管容器镜像注册表服务。它提供镜像漏洞扫描、IAM 集成和镜像生命周期管理等功能，并与其他 AWS 服务无缝集成。
</details>

19. 哪个 Docker 命令允许在正在运行的容器内运行额外命令？

<details>

<summary>显示答案</summary>

**答案：docker exec**

**解释：**
`docker exec` 命令允许在正在运行的容器内运行额外命令。例如，`docker exec -it <container> bash` 会连接到容器内的交互式 shell，或者 `docker exec <container> ls /app` 会列出容器内的文件。该命令对容器调试非常有用。
</details>

20. 哪个 Docker 命令以流的形式监控实时容器事件（start、stop、restart 等）？

<details>

<summary>显示答案</summary>

**答案：docker events**

**解释：**
`docker events` 命令以流的形式显示来自 Docker daemon 的实时事件。你可以监控 container start、stop、restart、image pull、network connect/disconnect 等事件。`--filter` 选项允许按特定容器或事件类型过滤，这对调试和监控很有用。
</details>

## 实践题

21. 编写一个满足以下要求的 Dockerfile：
    - 使用 Node.js 14 Alpine 镜像
    - 将工作目录设置为 /app
    - 先复制 package.json 和 package-lock.json 文件
    - 安装依赖
    - 复制其余文件
    - 暴露端口 3000
    - 容器启动时运行 "node server.js" 命令

<details>

<summary>显示答案</summary>

**答案：**
```dockerfile
FROM node:14-alpine

WORKDIR /app

COPY package*.json ./

RUN npm install

COPY . .

EXPOSE 3000

CMD ["node", "server.js"]
```

**解释：**
这个 Dockerfile 展示了 Node.js 应用程序的基本配置。通过先复制依赖文件（package*.json）并在复制其余文件之前安装依赖，它优化了 Docker 的层缓存。这样，即使源代码发生变化，只要依赖没有变化，npm install 步骤也可以复用。
</details>

22. 分析以下 Docker 命令并解释其用途：
    ```bash
    docker run -d --name my-app -p 8080:80 -v data:/app/data --restart always nginx:latest
    ```

<details>

<summary>显示答案</summary>

**答案：**
此命令用于以下目的：
    - `-d`：在后台运行容器（detached mode）
    - `--name my-app`：将容器名称设置为 "my-app"
    - `-p 8080:80`：将主机端口 8080 映射到容器端口 80
    - `-v data:/app/data`：将名为 "data" 的 volume 挂载到容器中的 /app/data 路径
    - `--restart always`：容器退出时始终自动重启
    - `nginx:latest`：使用最新版本的 nginx 镜像

此命令在后台运行 nginx Web 服务器，使其可通过主机端口 8080 访问，设置用于持久数据存储的 volume，并配置容器退出时自动重启。
</details>

23. 使用多阶段构建为 React 应用程序编写一个优化后的 Dockerfile。

<details>

<summary>显示答案</summary>

**答案：**
```dockerfile
# Build stage
FROM node:14 AS build

WORKDIR /app

COPY package*.json ./

RUN npm install

COPY . .

RUN npm run build

# Run stage
FROM nginx:alpine

# Copy build artifacts to nginx's service directory
COPY --from=build /app/build /usr/share/nginx/html

# Use default nginx configuration

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
```

**解释：**
这个多阶段 Dockerfile 由两个阶段组成：
1. 构建阶段：使用 Node.js 镜像构建 React 应用程序。
2. 运行阶段：使用轻量级 nginx 镜像提供构建后的静态文件。

这种方法的优势在于最终镜像不包含 Node.js 运行时、npm 包、源代码等，从而显著减小镜像大小。最终镜像只包含构建后的静态文件和 nginx，因此更小、更安全。
</details>

24. 编写一个包含容器健康检查的 Dockerfile。将其配置为每 30 秒检查一次 HTTP endpoint /health，如果 3 秒内没有响应则视为失败，并在失败 3 次后标记为 unhealthy。

<details>

<summary>显示答案</summary>

**答案：**
```dockerfile
FROM nginx:alpine

# Copy application (example)
COPY ./html /usr/share/nginx/html

# Health check configuration
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
  CMD wget --quiet --tries=1 --spider http://localhost/health || exit 1

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
```

**解释：**
每个 HEALTHCHECK 指令选项的含义：
- `--interval=30s`：每 30 秒执行一次健康检查
- `--timeout=3s`：健康检查命令必须在 3 秒内完成
- `--start-period=10s`：容器启动后的 10 秒内忽略健康检查失败（初始化时间）
- `--retries=3`：连续失败 3 次后将容器标记为 unhealthy
- `CMD`：要执行的健康检查命令。使用 wget 检查 /health endpoint

容器编排工具使用健康检查来判断容器状态，以便做出自动恢复或流量路由决策。
</details>

25. 编写 Docker 命令，用于检查正在运行的容器的环境变量、网络设置和进程列表，以便进行调试。

<details>

<summary>显示答案</summary>

**答案：**
```bash
# 1. Check environment variables
docker exec <container-id> env

# Or use inspect
docker inspect <container-id> --format='{{range .Config.Env}}{{println .}}{{end}}'

# 2. Check network settings
docker exec <container-id> ip addr
docker exec <container-id> netstat -tuln
# or
docker exec <container-id> ss -tuln

# Check IP address only
docker inspect <container-id> --format='{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}'

# 3. Check process list
docker exec <container-id> ps aux
# or
docker top <container-id>

# 4. Additional useful debugging commands
# Container detailed information
docker inspect <container-id>

# Container logs
docker logs <container-id>

# File system changes
docker diff <container-id>

# Real-time resource usage
docker stats <container-id>
```

**解释：**
调试容器时，可以组合使用这些命令来诊断问题：
- `docker exec` 在正在运行的容器中执行命令
- `docker inspect` 检查详细的容器元数据
- `docker top` 从主机视角查看容器进程
- `docker diff` 检查相对于镜像发生变化的文件
有效使用这些工具有助于了解容器内部状态并解决问题。
</details>

## 高级题

26. 比较 namespace 和 cgroups 这两个容器技术核心组件的作用，并解释它们各自如何为容器隔离做出贡献。

<details>

<summary>显示答案</summary>

**答案：**

**Namespaces**：
    - **作用**：隔离进程组，使每个组都能独立查看系统资源。
    - **隔离类型**：提供可见性隔离。
    - **主要 namespaces**：
    - PID namespace：进程 ID 隔离
    - Network namespace：网络栈隔离
    - Mount namespace：文件系统挂载点隔离
    - UTS namespace：主机名和域名隔离
    - IPC namespace：进程间通信资源隔离
    - User namespace：用户和组 ID 隔离

**cgroups (Control Groups)**：
    - **作用**：限制并隔离进程组的资源使用。
    - **隔离类型**：提供资源限制。
    - **主要功能**：
    - CPU 时间限制
    - 内存使用限制
    - Block I/O 带宽限制
    - 网络带宽限制
    - 设备访问控制

**对容器隔离的贡献**：

Namespaces 和 cgroups 发挥互补作用：

    - Namespaces 允许容器拥有自己的独立环境（进程树、网络接口、挂载点等），提供逻辑隔离。这使每个容器都拥有自己独特的系统视图。

    - cgroups 限制容器可以使用的系统资源（CPU、内存、磁盘 I/O 等），提供物理资源隔离。这可以防止一个容器使用过多资源并影响其他容器或主机系统。

这两项技术协同工作，使容器能够在隔离环境中运行，并限制资源使用。这种隔离比虚拟机更轻量，但为安全性和资源管理提供了足够的隔离。
</details>

27. 解释容器镜像分层系统的工作方式，以及 Copy-on-Write (CoW) 策略如何提升容器效率。

<details>

<summary>显示答案</summary>

**答案：**

**容器镜像分层系统**：

容器镜像由多个层的堆栈组成。每一层都表示文件系统更改，每条 Dockerfile 命令（FROM、RUN、COPY 等）都会创建一个新层。这些层是只读的，并以层级方式堆叠形成最终镜像。

分层系统的关键特性：
1. **增量构建**：镜像构建期间只重新生成发生变化的层
2. **层共享**：多个镜像共享相同的基础层
3. **缓存**：复用已经下载的层

**Copy-on-Write (CoW) 策略**：

Copy-on-Write 是一种优化策略，会将复制操作延迟到数据实际被修改时才执行。在容器上下文中：

1. **容器启动**：当容器启动时，会在现有镜像层顶部添加一个薄的可写层。
2. **读操作**：读取文件时，系统从上到下搜索各层，并使用找到的第一个文件版本。
3. **写操作**：修改文件时，文件会先被复制到可写层，然后再修改（Copy-on-Write）。原始文件保持不变。
4. **删除操作**：删除文件时，文件实际上不会被删除；而是在可写层中创建一个 “whiteout” 文件，使其看起来像已删除。

**对效率的贡献**：

1. **存储效率**： 
    - 使用相同基础镜像的多个容器共享镜像层，节省磁盘空间。
    - 每个容器只需要存储自己的变更数据。

2. **更快的启动时间**：
    - 启动新容器时，只需要创建可写层，而不需要复制整个文件系统。
    - 这显著缩短了容器启动时间。

3. **内存效率**：
    - 当多个容器使用同一个文件时，可以共享 page cache。

4. **网络效率**：
    - 镜像下载期间，已经存在的层不需要再次下载。

由于这些效率优势，容器可以比虚拟机更轻量、更快速地启动，并且同一主机上可以运行更多容器。
</details>

28. 解释完整的容器生命周期，并描述每种状态（Created、Running、Paused、Restarting、Exited、Dead）下的容器行为和状态转换方法。

<details>

<summary>显示答案</summary>

**答案：**

**容器生命周期状态：**

1. **Created**
   - 容器已创建但尚未启动
   - 使用 `docker create` 命令创建
   - 进程未运行，资源分配最少
   - 转换：`docker start` → Running

2. **Running**
   - 容器的主进程正在运行
   - 通过 `docker run` 或 `docker start` 进入
   - 正在主动使用 CPU、内存等资源
   - 转换：
     - `docker pause` → Paused
     - `docker stop` → Exited
     - `docker kill` → Exited
     - `docker restart` → Restarting → Running
     - 进程终止时 → Exited

3. **Paused**
   - 所有进程已通过 SIGSTOP 暂停
   - 通过 `docker pause` 命令进入
   - 内存保持不变，但不使用 CPU
   - 转换：`docker unpause` → Running

4. **Restarting**
   - 容器正在重启时的临时状态
   - 通过 `docker restart` 或重启策略发生
   - 转换：自动转换为 Running 或 Exited

5. **Exited**
   - 主进程已终止
   - 保留退出代码
   - 保留文件系统更改
   - 转换：
     - `docker start` → Running
     - `docker rm` → Deleted

6. **Dead**
   - 容器删除尝试失败时的异常状态
   - 资源清理未完成
   - 通常需要手动干预
   - 尝试使用 `docker rm -f` 强制删除

**状态检查和管理命令：**
```bash
# Check state
docker ps -a                    # List all containers
docker inspect <id> | jq '.[0].State'  # Detailed state

# State transitions
docker create nginx             # → Created
docker start <id>               # → Running
docker pause <id>               # → Paused
docker unpause <id>             # → Running
docker stop <id>                # → Exited
docker restart <id>             # → Running
docker rm <id>                  # Delete
```

**重启策略和生命周期：**
- `no`：不自动重启
- `on-failure[:max]`：异常退出时重启，可指定最大次数
- `always`：始终重启（包括 daemon 重启）
- `unless-stopped`：始终重启，直到被手动停止

理解容器生命周期有助于确保应用程序可用性，并在出现问题时建立适当的恢复策略。
</details>

---

[返回学习资料](../../basics/03-container-technology.md) | [下一测验：Kubernetes 入门](./04-kubernetes-introduction-quiz.md)
