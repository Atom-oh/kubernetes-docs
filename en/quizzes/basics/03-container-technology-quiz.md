# Container Technology Quiz

This quiz tests your understanding of container technology fundamentals, how they work, and their relationship with Kubernetes.

## Multiple Choice Questions

1. Which of the following is NOT a key characteristic of containers?
   - A) Portability
   - B) Lightweight
   - C) Complete hardware virtualization
   - D) Isolated execution environment
   
<details>

<summary>Show Answer</summary>

**Answer: C) Complete hardware virtualization**

**Explanation:**
Containers share the host OS kernel and do not virtualize hardware. Complete hardware virtualization is a characteristic of virtual machines (VMs). Containers provide portability, lightweight operation, and isolated execution environments, but they depend on the host OS kernel to operate.
</details>

2. What is the main difference between containers and virtual machines?
   - A) Containers require their own independent OS each
   - B) Virtual machines have faster startup times than containers
   - C) Containers share the host OS kernel
   - D) Virtual machines use fewer resources than containers
   
<details>

<summary>Show Answer</summary>

**Answer: C) Containers share the host OS kernel**

**Explanation:**
Containers operate by sharing the host OS kernel, while virtual machines each include a complete OS. As a result, containers are lighter, faster to start, and more resource-efficient than virtual machines.
</details>

3. Which of the following is NOT an OCI (Open Container Initiative) compatible low-level container runtime?
   - A) runc
   - B) crun
   - C) containerd
   - D) gVisor
   
<details>

<summary>Show Answer</summary>

**Answer: C) containerd**

**Explanation:**
containerd is a high-level container runtime that provides features such as image transfer, storage, and container execution management. runc, crun, and gVisor are all OCI-compatible low-level container runtimes responsible for actual container creation and execution.
</details>

4. Which statement is correct about container image layers?
   - A) Each layer can be independently modified
   - B) Layers are always merged and stored as a single file
   - C) Layers represent changes to the previous layer
   - D) Every container has its own unique set of layers
   
<details>

<summary>Show Answer</summary>

**Answer: C) Layers represent changes to the previous layer**

**Explanation:**
Container images consist of multiple layers, with each layer representing changes to the previous layer. This layered approach makes image sharing and caching efficient, saving storage space and improving image download speeds. Layers are read-only, and when a container runs, a writable layer is added on top.
</details>

5. What is the main purpose of using multi-stage builds in Dockerfiles?
   - A) Improving build speed
   - B) Reducing final image size
   - C) Reducing security vulnerabilities
   - D) Supporting multiple operating systems
   
<details>

<summary>Show Answer</summary>

**Answer: B) Reducing final image size**

**Explanation:**
The main purpose of multi-stage builds is to reduce the final image size. The build stage includes all necessary tools for source code compilation, dependency installation, etc., while the run stage brings only the build artifacts to create a small image with minimal runtime environment. This excludes build tools and intermediate files from the final image.
</details>

6. What is Docker's default network driver?
   - A) host
   - B) bridge
   - C) overlay
   - D) macvlan
   
<details>

<summary>Show Answer</summary>

**Answer: B) bridge**

**Explanation:**
bridge is Docker's default network driver, enabling communication between containers running on the same host. This driver creates a virtual bridge within the host to connect containers. The host driver directly uses the host network, overlay is for multi-host communication, and macvlan assigns MAC addresses to containers to make them appear as physical network devices.
</details>

7. For persistent data storage in containers, which method uses an area of the host file system managed by Docker?
   - A) Ephemeral storage
   - B) Volume
   - C) Bind mount
   - D) tmpfs mount
   
<details>

<summary>Show Answer</summary>

**Answer: B) Volume**

**Explanation:**
Volumes are an area of the host file system managed by Docker, which is the most suitable method for persistent data storage in containers. Ephemeral storage is the container's internal file system where data is lost when the container is deleted. Bind mounts mount a specific host path into the container, and tmpfs mounts store data only in memory.
</details>

8. Which is NOT a method for enhancing container security?
   - A) Running containers as non-root users
   - B) Granting only necessary Linux capabilities
   - C) Granting administrator privileges to all containers
   - D) Using read-only file systems
   
<details>

<summary>Show Answer</summary>

**Answer: C) Granting administrator privileges to all containers**

**Explanation:**
Granting administrator privileges to all containers is an action that weakens security. To enhance container security, you should follow the principle of least privilege. Running containers as non-root users, granting only necessary Linux capabilities, and mounting file systems as read-only when possible are good security practices.
</details>

9. Which AWS service provides a serverless container execution environment?
   - A) Amazon EC2
   - B) Amazon ECS
   - C) Amazon Fargate
   - D) Amazon ECR
   
<details>

<summary>Show Answer</summary>

**Answer: C) Amazon Fargate**

**Explanation:**
Amazon Fargate is AWS's serverless container execution environment, allowing you to run containers without managing servers. Amazon EC2 is a virtual server service, Amazon ECS is a container orchestration service, and Amazon ECR is a container image registry service.
</details>

10. Which is NOT a main function of container orchestration tools?
    - A) Automatic deployment and rollback
    - B) Service discovery and load balancing
    - C) Container image building
    - D) Auto scaling

<details>

<summary>Show Answer</summary>

**Answer: C) Container image building**

**Explanation:**
Container image building is typically the role of CI/CD pipelines or container build tools like Docker. The main functions of container orchestration tools (Kubernetes, Docker Swarm, etc.) are automatic deployment and rollback, service discovery and load balancing, auto scaling, self-healing, configuration management, and storage orchestration.
</details>

11. Which state can a container NOT be in while not running?
    - A) Created
    - B) Exited
    - C) Building
    - D) Paused

<details>

<summary>Show Answer</summary>

**Answer: C) Building**

**Explanation:**
Container lifecycle states include Created (created), Running (running), Paused (paused), Restarting (restarting), Exited (exited), and Dead (dead). Building is a state of the image build process and is not a container state. Containers are created after images are built.
</details>

12. Which container restart policy restarts the container when the Docker daemon starts but does not restart if the container was manually stopped?
    - A) no
    - B) on-failure
    - C) always
    - D) unless-stopped

<details>

<summary>Show Answer</summary>

**Answer: D) unless-stopped**

**Explanation:**
The `unless-stopped` restart policy always restarts the container unless it was explicitly stopped. The container starts automatically even when the Docker daemon restarts, but if the user manually stopped it with the `docker stop` command, the container will not start after daemon restart. `always` restarts regardless of manual stop status.
</details>

13. Which Docker command checks the file system changes between a container and its original image?
    - A) docker inspect
    - B) docker diff
    - C) docker logs
    - D) docker history

<details>

<summary>Show Answer</summary>

**Answer: B) docker diff**

**Explanation:**
The `docker diff` command shows the changes between the container's file system and the original image. In the output, A represents Added files, C represents Changed files, and D represents Deleted files. This command is useful for debugging what files were modified while the container was running.
</details>

## Short Answer Questions

14. What is the unique identifier based on the contents of a container image, expressed as a SHA256 hash?

<details>

<summary>Show Answer</summary>

**Answer: Digest**

**Explanation:**
A digest is the SHA256 hash of the container image contents, serving as a unique identifier for the image. Unlike tags, if the image contents change, the digest also changes, so it is used to accurately reference a specific image version. Example: `nginx@sha256:2834dc507516af02784808c5f48b7cbe38b8ed5d0f4837f16e78d00deb7e7767`
</details>

15. What is the Dockerfile directive that specifies the command to run when a container starts?

<details>

<summary>Show Answer</summary>

**Answer: CMD**

**Explanation:**
The CMD directive specifies the default command to run when a container starts. For example, `CMD ["node", "server.js"]` runs the `node server.js` command when the container starts. CMD can be overridden by providing arguments to the docker run command.
</details>

16. What is the name of the virtual network interface Docker creates for communication between containers?

<details>

<summary>Show Answer</summary>

**Answer: docker0**

**Explanation:**
docker0 is the virtual bridge network interface that Docker creates by default. This bridge enables communication between containers running on the same host and mediates communication between containers and external networks.
</details>

17. What is the Linux security feature that restricts the system calls that a process running inside a container can use?

<details>

<summary>Show Answer</summary>

**Answer: seccomp (Secure Computing Mode)**

**Explanation:**
seccomp is a Linux kernel security feature that restricts the system calls a process can use. Container runtimes like Docker use seccomp profiles to restrict the system calls containers can perform, thereby enhancing security.
</details>

18. What is the name of the AWS service that stores and manages container images?

<details>

<summary>Show Answer</summary>

**Answer: Amazon ECR (Elastic Container Registry)**

**Explanation:**
Amazon ECR (Elastic Container Registry) is AWS's managed container image registry service. It provides features such as image vulnerability scanning, IAM integration, and image lifecycle management, and integrates seamlessly with other AWS services.
</details>

19. What Docker command allows running additional commands inside a running container?

<details>

<summary>Show Answer</summary>

**Answer: docker exec**

**Explanation:**
The `docker exec` command allows running additional commands inside a running container. For example, `docker exec -it <container> bash` connects to an interactive shell inside the container, or `docker exec <container> ls /app` lists files inside the container. This command is very useful for container debugging.
</details>

20. What Docker command monitors real-time container events (start, stop, restart, etc.) as a stream?

<details>

<summary>Show Answer</summary>

**Answer: docker events**

**Explanation:**
The `docker events` command shows real-time events from the Docker daemon as a stream. You can monitor events such as container start, stop, restart, image pull, network connect/disconnect, etc. The `--filter` option allows filtering by specific container or event type, which is useful for debugging and monitoring.
</details>

## Hands-on Questions

21. Write a Dockerfile that meets the following requirements:
    - Use Node.js 14 Alpine image
    - Set working directory to /app
    - Copy package.json and package-lock.json files first
    - Install dependencies
    - Copy remaining files
    - Expose port 3000
    - Run "node server.js" command when container starts

<details>

<summary>Show Answer</summary>

**Answer:**
```dockerfile
FROM node:14-alpine

WORKDIR /app

COPY package*.json ./

RUN npm install

COPY . .

EXPOSE 3000

CMD ["node", "server.js"]
```

**Explanation:**
This Dockerfile shows a basic configuration for Node.js applications. By copying dependency files (package*.json) first and installing them before copying the remaining files, it optimizes Docker's layer caching. This way, even if source code changes, the npm install step can be reused if dependencies haven't changed.
</details>

22. Analyze the following Docker command and explain its purpose:
    ```bash
    docker run -d --name my-app -p 8080:80 -v data:/app/data --restart always nginx:latest
    ```

<details>

<summary>Show Answer</summary>

**Answer:**
This command is used for the following purposes:
    - `-d`: Run the container in background (detached mode)
    - `--name my-app`: Set the container name to "my-app"
    - `-p 8080:80`: Map host port 8080 to container port 80
    - `-v data:/app/data`: Mount a volume named "data" to the /app/data path in the container
    - `--restart always`: Always automatically restart when container exits
    - `nginx:latest`: Use the latest version of nginx image

This command runs the nginx web server in the background, makes it accessible through host port 8080, sets up a volume for persistent data storage, and configures automatic restart when the container exits.
</details>

23. Write an optimized Dockerfile for a React application using multi-stage builds.

<details>

<summary>Show Answer</summary>

**Answer:**
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

**Explanation:**
This multi-stage Dockerfile consists of two stages:
1. Build stage: Uses Node.js image to build the React application.
2. Run stage: Uses lightweight nginx image to serve the built static files.

The advantage of this approach is that the final image does not include Node.js runtime, npm packages, source code, etc., significantly reducing image size. The final image contains only built static files and nginx, making it smaller and more secure.
</details>

24. Write a Dockerfile that includes container health checks. Configure it to check the HTTP endpoint /health every 30 seconds, treat as failed if no response within 3 seconds, and mark as unhealthy after 3 failures.

<details>

<summary>Show Answer</summary>

**Answer:**
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

**Explanation:**
Meaning of each HEALTHCHECK directive option:
- `--interval=30s`: Perform health check every 30 seconds
- `--timeout=3s`: Health check command must complete within 3 seconds
- `--start-period=10s`: Ignore health check failures for 10 seconds after container start (initialization time)
- `--retries=3`: Mark container as unhealthy after 3 consecutive failures
- `CMD`: Health check command to execute. Uses wget to check /health endpoint

Health checks are used by container orchestration tools to determine container status for automatic recovery or traffic routing decisions.
</details>

25. Write Docker commands to check the environment variables, network settings, and process list of a running container for debugging purposes.

<details>

<summary>Show Answer</summary>

**Answer:**
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

**Explanation:**
When debugging containers, combine these commands to diagnose issues:
- `docker exec` runs commands in a running container
- `docker inspect` checks detailed container metadata
- `docker top` views container processes from the host perspective
- `docker diff` checks files changed compared to the image
Using these tools effectively helps understand container internal state and resolve issues.
</details>

## Advanced Questions

26. Compare the roles of namespaces and cgroups, the core components of container technology, and explain how each contributes to container isolation.

<details>

<summary>Show Answer</summary>

**Answer:**

**Namespaces**:
    - **Role**: Isolates process groups so that each group can see system resources independently.
    - **Isolation type**: Provides visibility isolation.
    - **Main namespaces**:
    - PID namespace: Process ID isolation
    - Network namespace: Network stack isolation
    - Mount namespace: File system mount point isolation
    - UTS namespace: Hostname and domain name isolation
    - IPC namespace: Inter-process communication resource isolation
    - User namespace: User and group ID isolation

**cgroups (Control Groups)**:
    - **Role**: Limits and isolates the resource usage of process groups.
    - **Isolation type**: Provides resource limitation.
    - **Main functions**:
    - CPU time limiting
    - Memory usage limiting
    - Block I/O bandwidth limiting
    - Network bandwidth limiting
    - Device access control

**Contribution to container isolation**:

Namespaces and cgroups play complementary roles:

    - Namespaces allow containers to have their own independent environments (process trees, network interfaces, mount points, etc.), providing logical isolation. This gives each container its own unique view of the system.

    - cgroups limit the system resources (CPU, memory, disk I/O, etc.) that containers can use, providing physical resource isolation. This prevents one container from using excessive resources and affecting other containers or the host system.

These two technologies work together to allow containers to run in isolated environments with limited resource usage. This isolation is lighter than virtual machines but provides sufficient isolation for security and resource management.
</details>

27. Explain how the container image layering system works and how the Copy-on-Write (CoW) strategy contributes to container efficiency.

<details>

<summary>Show Answer</summary>

**Answer:**

**Container Image Layering System**:

Container images consist of a stack of multiple layers. Each layer represents file system changes, and each Dockerfile command (FROM, RUN, COPY, etc.) creates a new layer. These layers are read-only and stack hierarchically to form the final image.

Key features of the layering system:
1. **Incremental builds**: Only changed layers are regenerated during image builds
2. **Layer sharing**: Multiple images share the same base layers
3. **Caching**: Already downloaded layers are reused

**Copy-on-Write (CoW) Strategy**:

Copy-on-Write is an optimization strategy that delays copy operations until data is actually modified. In the container context:

1. **Container start**: When a container starts, a thin writable layer is added on top of existing image layers.
2. **Read operations**: When reading a file, the system searches layers from top to bottom and uses the first version of the file found.
3. **Write operations**: When modifying a file, the file is first copied to the writable layer then modified (Copy-on-Write). The original file remains unchanged.
4. **Delete operations**: When deleting a file, the file is not actually deleted; instead, a "whiteout" file is created in the writable layer to make it appear deleted.

**Contribution to efficiency**:

1. **Storage efficiency**: 
    - Multiple containers using the same base image share image layers, saving disk space.
    - Each container only needs to store its own changed data.

2. **Faster startup time**:
    - When starting a new container, only the writable layer needs to be created, not copying the entire file system.
    - This significantly reduces container startup time.

3. **Memory efficiency**:
    - When the same file is used by multiple containers, page cache can be shared.

4. **Network efficiency**:
    - Already existing layers don't need to be downloaded again during image download.

Thanks to these efficiencies, containers can start lighter and faster than virtual machines, and more containers can run on the same host.
</details>

28. Explain the entire container lifecycle and describe the container behavior and state transition methods in each state (Created, Running, Paused, Restarting, Exited, Dead).

<details>

<summary>Show Answer</summary>

**Answer:**

**Container Lifecycle States:**

1. **Created**
   - Container has been created but not yet started
   - Created with the `docker create` command
   - Process not running, minimal resource allocation
   - Transition: `docker start` → Running

2. **Running**
   - Container's main process is running
   - Entered via `docker run` or `docker start`
   - Actively using resources like CPU, memory
   - Transitions:
     - `docker pause` → Paused
     - `docker stop` → Exited
     - `docker kill` → Exited
     - `docker restart` → Restarting → Running
     - On process termination → Exited

3. **Paused**
   - All processes paused with SIGSTOP
   - Entered via `docker pause` command
   - Memory maintained but no CPU usage
   - Transition: `docker unpause` → Running

4. **Restarting**
   - Temporary state while container is restarting
   - Occurs via `docker restart` or restart policy
   - Transition: Automatically transitions to Running or Exited

5. **Exited**
   - Main process has terminated
   - Exit code preserved
   - File system changes maintained
   - Transitions:
     - `docker start` → Running
     - `docker rm` → Deleted

6. **Dead**
   - Abnormal state where container removal attempt failed
   - Resource cleanup not completed
   - Generally requires manual intervention
   - Attempt force removal with `docker rm -f`

**State check and management commands:**
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

**Restart policies and lifecycle:**
- `no`: No automatic restart
- `on-failure[:max]`: Restart on abnormal exit, can specify max count
- `always`: Always restart (including daemon restart)
- `unless-stopped`: Always restart until manually stopped

Understanding the container lifecycle helps ensure application availability and establish appropriate recovery strategies when issues occur.
</details>

---

[Return to Learning Materials](../../basics/03-container-technology.md) | [Next Quiz: Kubernetes Introduction](./04-kubernetes-introduction-quiz.md)
