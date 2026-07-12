# 容器技术测验

本测验测试您对容器技术基础知识、工作原理以及与Kubernetes关系的理解。

## 多选题

1. 以下哪一项不是容器的关键特性？
   - A) 可移植性
   - B) 轻量级
   - C) 完整的硬件虚拟化
   - D) 隔离执行环境
   
<details>

<summary>显示答案</summary>

**答案: C) 完整的硬件虚拟化**

**解释:**
容器共享宿主OS内核，不进行硬件虚拟化。完整的硬件虚拟化是虚拟机(VM)的特性。容器提供可移植性、轻量级操作和隔离执行环境，但它们依赖宿主OS内核来运行。
</details>

2. 容器与虚拟机的主要区别是什么？
   - A) 容器需要各自独立的操作系统
   - B) 虚拟机的启动速度比容器快
   - C) 容器共享宿主OS内核
   - D) 虚拟机比容器消耗更少的资源
   
<details>

<summary>显示答案</summary>

**答案: C) 容器共享宿主OS内核**

**解释:**
容器通过共享宿主OS内核运行，而虚拟机各自包含一个完整的操作系统。因此，容器比虚拟机更轻量、启动更快、资源效率更高。
</details>

3. 以下哪一项不是OCI(开放容器倡议)兼容的低级容器运行时？
   - A) runc
   - B) crun
   - C) containerd
   - D) gVisor
   
<details>

<summary>显示答案</summary>

**答案: C) containerd**

**解释:**
containerd是高级容器运行时，提供镜像转移、存储和容器执行管理等功能。runc、crun和gVisor都是OCI兼容的低级容器运行时，负责实际的容器创建和执行。
</details>

4. 关于容器镜像层，哪个说法是正确的？
   - A) 每一层都可以独立修改
   - B) 层总是被合并并存储为单个文件
   - C) 层代表相对于前一层的变化
   - D) 每个容器都有自己独特的层集合
   
<details>

<summary>显示答案</summary>

**答案: C) 层代表相对于前一层的变化**

**解释:**
容器镜像由多个层组成，每一层代表相对于前一层的变化。这种分层方法使镜像共享和缓存高效，节省存储空间并提高镜像下载速度。层是只读的，当容器运行时，在顶部添加一个可写层。
</details>

5. 在Dockerfile中使用多阶段构建的主要目的是什么？
   - A) 提高构建速度
   - B) 减小最终镜像大小
   - C) 减少安全漏洞
   - D) 支持多个操作系统
   
<details>

<summary>显示答案</summary>

**答案: B) 减小最终镜像大小**

**解释:**
多阶段构建的主要目的是减小最终镜像大小。构建阶段包含源代码编译、依赖安装等所需的所有工具，而运行阶段仅将构建工件引入到创建一个最小的运行环境镜像。这排除了构建工具和中间文件。
</details>

6. Docker的默认网络驱动是什么？
   - A) host
   - B) bridge
   - C) overlay
   - D) macvlan
   
<details>

<summary>显示答案</summary>

**答案: B) bridge**

**解释:**
bridge是Docker的默认网络驱动，支持在同一宿主上运行的容器之间通信。此驱动在宿主内创建虚拟网桥来连接容器。host驱动直接使用宿主网络，overlay用于多宿主通信，macvlan为容器分配MAC地址使其显示为物理网络设备。
</details>

7. 用于容器中的持久数据存储，哪个方法使用由Docker管理的宿主文件系统区域？
   - A) 临时存储
   - B) Volume
   - C) Bind mount
   - D) tmpfs mount
   
<details>

<summary>显示答案</summary>

**答案: B) Volume**

**解释:**
Volume是由Docker管理的宿主文件系统区域，是容器中持久数据存储的最合适方法。临时存储是容器内部文件系统，容器删除时数据丢失。Bind mount将特定宿主路径挂载到容器中，tmpfs mount仅将数据存储在内存中。
</details>

8. 以下哪一项不是增强容器安全性的方法？
   - A) 以非root用户运行容器
   - B) 仅授予必要的Linux功能
   - C) 为所有容器授予管理员权限
   - D) 使用只读文件系统
   
<details>

<summary>显示答案</summary>

**答案: C) 为所有容器授予管理员权限**

**解释:**
为所有容器授予管理员权限是削弱安全性的行为。为了增强容器安全性，应遵循最小权限原则。以非root用户运行容器、仅授予必要的Linux功能、在可能时挂载只读文件系统是良好的安全实践。
</details>

9. 哪个AWS服务提供无服务器容器执行环境？
   - A) Amazon EC2
   - B) Amazon ECS
   - C) Amazon Fargate
   - D) Amazon ECR
   
<details>

<summary>显示答案</summary>

**答案: C) Amazon Fargate**

**解释:**
Amazon Fargate是AWS的无服务器容器执行环境，允许您运行容器而无需管理服务器。Amazon EC2是虚拟服务器服务，Amazon ECS是容器编排服务，Amazon ECR是容器镜像注册表服务。
</details>

10. 以下哪一项不是容器编排工具的主要功能？
    - A) 自动部署和回滚
    - B) 服务发现和负载均衡
    - C) 容器镜像构建
    - D) 自动扩展

<details>

<summary>显示答案</summary>

**答案: C) 容器镜像构建**

**解释:**
容器镜像构建通常是CI/CD管道或Docker等容器构建工具的作用。容器编排工具(Kubernetes、Docker Swarm等)的主要功能是自动部署和回滚、服务发现和负载均衡、自动扩展、自我修复、配置管理和存储编排。
</details>

11. 容器在未运行时不能处于哪种状态？
    - A) Created
    - B) Exited
    - C) Building
    - D) Paused

<details>

<summary>显示答案</summary>

**答案: C) Building**

**解释:**
容器生命周期状态包括Created(已创建)、Running(运行中)、Paused(已暂停)、Restarting(重启中)、Exited(已退出)和Dead(已死亡)。Building是镜像构建过程的状态，不是容器状态。容器在镜像构建后创建。
</details>

12. 哪个容器重启策略在Docker守护进程启动时重启容器，但如果容器被手动停止则不重启？
    - A) no
    - B) on-failure
    - C) always
    - D) unless-stopped

<details>

<summary>显示答案</summary>

**答案: D) unless-stopped**

**解释:**
`unless-stopped`重启策略总是重启容器，除非它被明确停止。即使Docker守护进程重启，容器也会自动启动，但如果用户用`docker stop`命令手动停止了容器，守护进程重启后容器不会启动。`always`不论手动停止状态都会重启。
</details>

13. 哪个Docker命令检查容器和其原始镜像之间的文件系统变化？
    - A) docker inspect
    - B) docker diff
    - C) docker logs
    - D) docker history

<details>

<summary>显示答案</summary>

**答案: B) docker diff**

**解释:**
`docker diff`命令显示容器文件系统与原始镜像之间的变化。在输出中，A代表添加的文件，C代表更改的文件，D代表删除的文件。此命令对于调试容器运行时修改的文件非常有用。
</details>

## 简答题

14. 基于容器镜像内容的唯一标识符，用SHA256哈希表示，叫什么？

<details>

<summary>显示答案</summary>

**答案: Digest(摘要)**

**解释:**
Digest是容器镜像内容的SHA256哈希值，作为镜像的唯一标识符。与标签不同，如果镜像内容改变，摘要也会改变，因此用来精确引用特定的镜像版本。例如: `nginx@sha256:2834dc507516af02784808c5f48b7cbe38b8ed5d0f4837f16e78d00deb7e7767`
</details>

15. 哪个Dockerfile指令指定容器启动时要运行的命令？

<details>

<summary>显示答案</summary>

**答案: CMD**

**解释:**
CMD指令指定容器启动时运行的默认命令。例如，`CMD ["node", "server.js"]`在容器启动时运行`node server.js`命令。CMD可以通过向docker run命令提供参数来覆盖。
</details>

16. Docker为容器之间通信创建的虚拟网络接口的名称是什么？

<details>

<summary>显示答案</summary>

**答案: docker0**

**解释:**
docker0是Docker默认创建的虚拟网桥接口。此网桥使同一宿主上运行的容器能够通信，并调解容器与外部网络的通信。
</details>

17. 限制运行在容器内的进程可以使用的系统调用的Linux安全功能是什么？

<details>

<summary>显示答案</summary>

**答案: seccomp(安全计算模式)**

**解释:**
seccomp是Linux内核安全功能，限制进程可以使用的系统调用。Docker等容器运行时使用seccomp配置文件来限制容器可以执行的系统调用，从而增强安全性。
</details>

18. 存储和管理容器镜像的AWS服务的名称是什么？

<details>

<summary>显示答案</summary>

**答案: Amazon ECR(弹性容器注册表)**

**解释:**
Amazon ECR(弹性容器注册表)是AWS的托管容器镜像注册表服务。它提供镜像漏洞扫描、IAM集成和镜像生命周期管理等功能，并与其他AWS服务无缝集成。
</details>

19. 哪个Docker命令允许在运行中的容器内运行其他命令？

<details>

<summary>显示答案</summary>

**答案: docker exec**

**解释:**
`docker exec`命令允许在运行中的容器内运行其他命令。例如，`docker exec -it <container> bash`连接到容器内的交互式shell，或`docker exec <container> ls /app`列出容器内的文件。此命令对容器调试非常有用。
</details>

20. 哪个Docker命令以流的形式监视实时容器事件(启动、停止、重启等)？

<details>

<summary>显示答案</summary>

**答案: docker events**

**解释:**
`docker events`命令以流的形式显示Docker守护进程的实时事件。您可以监视容器启动、停止、重启、镜像拉取、网络连接/断开连接等事件。`--filter`选项允许按特定容器或事件类型筛选，对调试和监视很有用。
</details>

## 动手题

21. 编写一个满足以下要求的Dockerfile:
    - 使用Node.js 14 Alpine镜像
    - 将工作目录设置为/app
    - 首先复制package.json和package-lock.json文件
    - 安装依赖
    - 复制其余文件
    - 公开端口3000
    - 容器启动时运行"node server.js"命令

<details>

<summary>显示答案</summary>

**答案:**
```dockerfile
FROM node:14-alpine

WORKDIR /app

COPY package*.json ./

RUN npm install

COPY . .

EXPOSE 3000

CMD ["node", "server.js"]
```

**解释:**
此Dockerfile为Node.js应用展示了基本配置。通过首先复制依赖文件(package*.json)并在复制其余文件之前安装它们，优化了Docker的层缓存。这样，即使源代码改变，如果依赖未改变，npm install步骤可以重用。
</details>

22. 分析以下Docker命令并解释其目的:
    ```bash
    docker run -d --name my-app -p 8080:80 -v data:/app/data --restart always nginx:latest
    ```

<details>

<summary>显示答案</summary>

**答案:**
此命令用于以下目的:
    - `-d`: 在后台(分离模式)运行容器
    - `--name my-app`: 将容器名称设置为"my-app"
    - `-p 8080:80`: 将宿主端口8080映射到容器端口80
    - `-v data:/app/data`: 将名为"data"的volume挂载到容器中的/app/data路径
    - `--restart always`: 容器退出时总是自动重启
    - `nginx:latest`: 使用最新版本的nginx镜像

此命令在后台运行nginx网络服务器，通过宿主端口8080使其可访问，为持久数据存储设置volume，并配置容器退出时的自动重启。
</details>

23. 使用多阶段构建为React应用编写优化的Dockerfile。

<details>

<summary>显示答案</summary>

**答案:**
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

**解释:**
此多阶段Dockerfile由两个阶段组成:
1. 构建阶段: 使用Node.js镜像构建React应用。
2. 运行阶段: 使用轻量级nginx镜像来提供构建的静态文件。

此方法的优点是最终镜像不包含Node.js运行时、npm包、源代码等，显著减小镜像大小。最终镜像仅包含构建的静态文件和nginx，更小且更安全。
</details>

24. 编写一个包含容器健康检查的Dockerfile。配置为每30秒检查HTTP端点/health，如果3秒内无响应则视为失败，3次失败后标记为不健康。

<details>

<summary>显示答案</summary>

**答案:**
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

**解释:**
每个HEALTHCHECK指令选项的含义:
- `--interval=30s`: 每30秒执行一次健康检查
- `--timeout=3s`: 健康检查命令必须在3秒内完成
- `--start-period=10s`: 容器启动后的10秒内忽略健康检查失败(初始化时间)
- `--retries=3`: 3次连续失败后标记容器为不健康
- `CMD`: 要执行的健康检查命令。使用wget检查/health端点

健康检查由容器编排工具用于确定容器状态，用于自动恢复或流量路由决定。
</details>

25. 编写Docker命令来检查运行中的容器的环境变量、网络设置和进程列表，用于调试目的。

<details>

<summary>显示答案</summary>

**答案:**
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

**解释:**
调试容器时，组合这些命令来诊断问题:
- `docker exec`在运行中的容器内运行命令
- `docker inspect`检查详细的容器元数据
- `docker top`从宿主视角查看容器进程
- `docker diff`检查与镜像相比改变的文件
有效使用这些工具有助于理解容器内部状态和解决问题。
</details>

## 高级题

26. 比较命名空间和cgroups(容器技术的核心组件)的作用，并解释每个如何对容器隔离做出贡献。

<details>

<summary>显示答案</summary>

**答案:**

**命名空间**:
    - **作用**: 隔离进程组，使每个组能够独立地看到系统资源。
    - **隔离类型**: 提供可见性隔离。
    - **主要命名空间**:
    - PID命名空间: 进程ID隔离
    - Network命名空间: 网络堆栈隔离
    - Mount命名空间: 文件系统挂载点隔离
    - UTS命名空间: 主机名和域名隔离
    - IPC命名空间: 进程间通信资源隔离
    - User命名空间: 用户和组ID隔离

**cgroups(控制组)**:
    - **作用**: 限制和隔离进程组的资源使用。
    - **隔离类型**: 提供资源限制。
    - **主要功能**:
    - CPU时间限制
    - 内存使用限制
    - 块I/O带宽限制
    - 网络带宽限制
    - 设备访问控制

**对容器隔离的贡献**:

命名空间和cgroups起到互补的作用:

    - 命名空间允许容器拥有自己独立的环境(进程树、网络接口、挂载点等)，提供逻辑隔离。这为每个容器提供了对系统的独特视图。

    - cgroups限制容器可以使用的系统资源(CPU、内存、磁盘I/O等)，提供物理资源隔离。这防止一个容器过度使用资源并影响其他容器或宿主系统。

这两项技术共同运作，允许容器在隔离的环境中以有限的资源使用运行。这种隔离比虚拟机更轻量，但提供足够的安全和资源管理隔离。
</details>

27. 解释容器镜像分层系统的工作原理，以及写时复制(Copy-on-Write, CoW)策略如何促进容器效率。

<details>

<summary>显示答案</summary>

**答案:**

**容器镜像分层系统**:

容器镜像由多个层的堆栈组成。每一层代表文件系统变化，每个Dockerfile命令(FROM、RUN、COPY等)创建一个新层。这些层是只读的，按层次堆叠形成最终镜像。

分层系统的关键特性:
1. **增量构建**: 镜像构建时仅重新生成改变的层
2. **层共享**: 多个镜像共享相同的基础层
3. **缓存**: 已下载的层被重新使用

**写时复制(Copy-on-Write, CoW)策略**:

写时复制是一个优化策略，延迟复制操作直到数据实际修改。在容器上下文中:

1. **容器启动**: 容器启动时，在现有镜像层顶部添加一个薄的可写层。
2. **读操作**: 读取文件时，系统从顶部向下搜索层，使用找到的文件的第一个版本。
3. **写操作**: 修改文件时，文件首先被复制到可写层然后被修改(写时复制)。原始文件保持不变。
4. **删除操作**: 删除文件时，文件实际上不会被删除；相反，在可写层中创建一个"whiteout"文件使其显示为被删除。

**对效率的贡献**:

1. **存储效率**:
    - 使用相同基础镜像的多个容器共享镜像层，节省磁盘空间。
    - 每个容器仅需存储其自己的改变的数据。

2. **更快的启动时间**:
    - 启动新容器时，仅需创建可写层，不需复制整个文件系统。
    - 这显著减少容器启动时间。

3. **内存效率**:
    - 当同一文件被多个容器使用时，可以共享页面缓存。

4. **网络效率**:
    - 镜像下载时不需要再次下载已存在的层。

由于这些效率，容器可以比虚拟机启动更轻、更快，并且在相同宿主上可以运行更多容器。
</details>

28. 解释完整的容器生命周期，并描述每个状态(Created、Running、Paused、Restarting、Exited、Dead)中的容器行为和状态转换方法。

<details>

<summary>显示答案</summary>

**答案:**

**容器生命周期状态:**

1. **Created**
   - 容器已创建但尚未启动
   - 使用`docker create`命令创建
   - 进程未运行，最少资源分配
   - 转换: `docker start` → Running

2. **Running**
   - 容器的主进程正在运行
   - 通过`docker run`或`docker start`进入
   - 主动使用CPU、内存等资源
   - 转换:
     - `docker pause` → Paused
     - `docker stop` → Exited
     - `docker kill` → Exited
     - `docker restart` → Restarting → Running
     - 进程终止时 → Exited

3. **Paused**
   - 所有进程使用SIGSTOP暂停
   - 通过`docker pause`命令进入
   - 内存保持但无CPU使用
   - 转换: `docker unpause` → Running

4. **Restarting**
   - 容器重启时的临时状态
   - 通过`docker restart`或重启策略发生
   - 转换: 自动转换到Running或Exited

5. **Exited**
   - 主进程已终止
   - 退出代码已保存
   - 文件系统变化已保持
   - 转换:
     - `docker start` → Running
     - `docker rm` → 已删除

6. **Dead**
   - 异常状态，容器移除尝试失败
   - 资源清理未完成
   - 通常需要手动干预
   - 尝试使用`docker rm -f`强制移除

**状态检查和管理命令:**
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

**重启策略和生命周期:**
- `no`: 无自动重启
- `on-failure[:max]`: 异常退出时重启，可指定最大次数
- `always`: 总是重启(包括守护进程重启)
- `unless-stopped`: 总是重启直到被手动停止

理解容器生命周期有助于确保应用可用性，并在问题发生时建立适当的恢复策略。
</details>

---

[返回学习资料](../../basics/03-container-technology.md) | [下一测验: Kubernetes介绍](./04-kubernetes-introduction-quiz.md)
