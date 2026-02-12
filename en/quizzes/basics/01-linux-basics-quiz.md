# Linux Basics Quiz

This quiz tests your understanding of Linux fundamental concepts that form the foundation of Kubernetes and container technology.

## Multiple Choice Questions

1. Which of the following is NOT a primary role of the Linux kernel?
   - A) Process management
   - B) Memory management
   - C) Providing user interface
   - D) Device management
<details>

<summary>Show Answer</summary>

**Answer: C) Providing user interface**

**Explanation:**
The Linux kernel is the core of the operating system, acting as an intermediary between hardware and software. The kernel's primary roles include process management, memory management, device management, and providing system call interfaces. The user interface (GUI, CLI) is provided by separate programs running in user space and is not a kernel responsibility.

</details>

2. Which of the following is NOT a type of Linux namespace?
   - A) PID namespace
   - B) Network namespace
   - C) Memory namespace
   - D) User namespace
<details>

<summary>Show Answer</summary>

**Answer: C) Memory namespace**

**Explanation:**
Linux has the following namespaces: PID (Process ID), Network, Mount, UTS (hostname), IPC (Inter-Process Communication), User, and cgroup namespaces. Memory namespace does not exist. Memory isolation is primarily managed through cgroups.

</details>

3. What is the primary function of cgroups (Control Groups)?
   - A) Limiting and isolating resource usage of process groups
   - B) Controlling file system access
   - C) Filtering network packets
   - D) Managing user authentication
   
<details>

<summary>Show Answer</summary>

**Answer: A) Limiting and isolating resource usage of process groups**

**Explanation:**
cgroups is a Linux kernel feature that limits and isolates the resource usage of process groups. It can limit and monitor the usage of resources such as CPU time, memory, block I/O, and network bandwidth. This is a core technology for implementing resource limits in containers.
</details>

4. In the file permission "rwxr-xr--", what are the group user's permissions?
   - A) Read, write, execute
   - B) Read, execute
   - C) Read only
   - D) Execute only
   
<details>

<summary>Show Answer</summary>

**Answer: B) Read, execute**

**Explanation:**
In the file permission "rwxr-xr--":
  - First 3 characters (rwx): Owner permissions - read, write, execute
  - Middle 3 characters (r-x): Group permissions - read, execute
  - Last 3 characters (r--): Other users permissions - read only

Therefore, group users have read and execute permissions.

</details>

5. Which file system is primarily used to implement container image layers?
   - A) ext4
   - B) XFS
   - C) OverlayFS
   - D) Btrfs

<details>

<summary>Show Answer</summary>

**Answer: C) OverlayFS**

**Explanation:**
OverlayFS is a union mount file system that overlays multiple directories to present them as a single directory. It is primarily used by container runtimes like Docker to implement image layers. This allows the base image to remain read-only while adding a writable layer for each container.
</details>

6. When managing services with the systemctl command, which command sets a service to start automatically at boot?
   - A) systemctl start
   - B) systemctl enable
   - C) systemctl restart
   - D) systemctl reload

<details>

<summary>Show Answer</summary>

**Answer: B) systemctl enable**

**Explanation:**
`systemctl enable` sets a service to start automatically when the system boots. `start` immediately starts the service, `restart` restarts the service, and `reload` only re-reads the configuration file. On Kubernetes nodes, core services like kubelet and containerd should have automatic startup configured with `systemctl enable`.
</details>

7. Which kernel parameter is essential for Kubernetes cluster setup, enabling IP packet forwarding for container networking?
   - A) net.ipv4.tcp_syncookies
   - B) net.ipv4.ip_forward
   - C) net.core.somaxconn
   - D) fs.file-max

<details>

<summary>Show Answer</summary>

**Answer: B) net.ipv4.ip_forward**

**Explanation:**
`net.ipv4.ip_forward` is the setting that enables IP packet forwarding in the Linux kernel. This setting must be set to 1 to enable communication between containers and between containers and external networks. This parameter must be enabled when setting up Kubernetes nodes, and can be set with the command `sysctl -w net.ipv4.ip_forward=1`.
</details>

8. In a systemd unit file, which directive is used to define that a service should start after a specific service?
   - A) Requires
   - B) Wants
   - C) After
   - D) Before

<details>

<summary>Show Answer</summary>

**Answer: C) After**

**Explanation:**
In systemd unit files, `After` defines that the current unit should start after the specified unit. For example, `After=network-online.target` ensures the service starts after the network is ready. `Requires` defines a strong dependency, `Wants` defines a weak dependency, and `Before` indicates that the current unit should start before another unit.
</details>

9. Which kernel parameter is required for CNI plugins to work properly, allowing bridge traffic to pass through iptables?
   - A) net.ipv4.ip_forward
   - B) net.bridge.bridge-nf-call-iptables
   - C) net.core.netdev_max_backlog
   - D) net.ipv4.tcp_max_syn_backlog

<details>

<summary>Show Answer</summary>

**Answer: B) net.bridge.bridge-nf-call-iptables**

**Explanation:**
`net.bridge.bridge-nf-call-iptables` configures bridged network traffic to pass through iptables rules. This setting is essential for Kubernetes CNI plugins (Calico, Flannel, etc.) to correctly apply network policies and service routing. To enable this setting, you must first load the `br_netfilter` kernel module.
</details>

10. In package management, which command is used on Ubuntu/Debian to prevent automatic upgrades of Kubernetes components?
    - A) apt lock
    - B) apt-mark hold
    - C) apt freeze
    - D) apt pin

<details>

<summary>Show Answer</summary>

**Answer: B) apt-mark hold**

**Explanation:**
`apt-mark hold` pins specific packages to prevent automatic upgrades. In Kubernetes clusters, version compatibility of kubelet, kubeadm, and kubectl is important, so it is recommended to pin versions with the command `sudo apt-mark hold kubelet kubeadm kubectl`. On RHEL/CentOS, use the `yum versionlock` command.
</details>

## Short Answer Questions

11. What is a process called when it has terminated but its parent process has not checked its status?

<details>

<summary>Show Answer</summary>

**Answer: Zombie Process**

**Explanation:**
A zombie process is a process that has completed execution but remains in the process table because the parent process has not checked its exit status through the `wait()` system call. Zombie processes use almost no resources, but if many accumulate, the process table can become full, preventing new process creation.
</details>

12. What is the name of the Linux namespace that isolates a process's network stack?

<details>

<summary>Show Answer</summary>

**Answer: Network Namespace**

**Explanation:**
The network namespace isolates the network stack (network interfaces, routing tables, firewall rules, sockets, etc.). This allows each container to have its own network environment and operate independently from the host system or other containers' networks.
</details>

13. What is the name of the Linux security feature that restricts the system calls a process can use?

<details>

<summary>Show Answer</summary>

**Answer: seccomp (Secure Computing Mode)**

**Explanation:**
seccomp is a Linux kernel security feature that restricts the system calls a process can use. Container runtimes use seccomp filters to restrict the system calls containers can perform, thereby enhancing security.
</details>

14. What is it called when traditional root privileges in Linux are divided into smaller privilege units?

<details>

<summary>Show Answer</summary>

**Answer: Capabilities**

**Explanation:**
Linux Capabilities divide traditional root privileges into smaller privilege units. This allows granting only the minimum necessary privileges to a process, enhancing security. For example, to change network settings, only the `CAP_NET_ADMIN` capability is needed, not full root privileges.
</details>

15. What is the network interface pair between a host and container called in container networking?

<details>

<summary>Show Answer</summary>

**Answer: veth pair**

**Explanation:**
A veth pair is a virtual ethernet interface pair where one end is inside the container and the other end is in the host network namespace. This enables network communication between the container and host. Typically, the host-side veth interface is connected to a bridge (e.g., docker0) to enable communication between multiple containers.
</details>

16. What command is used to check and limit the maximum number of file descriptors a process can open?

<details>

<summary>Show Answer</summary>

**Answer: ulimit**

**Explanation:**
ulimit is a command to check and set resource limits for users and processes. `ulimit -n` checks the number of file descriptors that can be opened, and `ulimit -n 65536` changes the limit. On Kubernetes nodes, many file handles are needed, so it is common to permanently set high values in `/etc/security/limits.conf`.
</details>

17. What is the name of systemd's logging system tool used for unified management of service logs?

<details>

<summary>Show Answer</summary>

**Answer: journald (or systemd-journald)**

**Explanation:**
journald is systemd's unified logging system that collects and stores system and service logs. Logs can be queried using the `journalctl` command, with the `-u` option to view specific service logs and the `-f` option to view real-time logs. On Kubernetes nodes, kubelet logs can be checked with `journalctl -u kubelet`.
</details>

18. What is the name of the modern daemon used to synchronize system time with NTP servers?

<details>

<summary>Show Answer</summary>

**Answer: chronyd (or chrony)**

**Explanation:**
chronyd is a modern NTP client/server that synchronizes time faster than the traditional ntpd. The `chronyc tracking` command checks synchronization status, and `chronyc sources` shows the NTP server list. In Kubernetes clusters, all nodes must have accurately synchronized time for authentication, logging, etc. to work correctly.
</details>

19. What is the path of the file where DNS name resolution settings are stored in Linux?

<details>

<summary>Show Answer</summary>

**Answer: /etc/resolv.conf**

**Explanation:**
`/etc/resolv.conf` is the file that stores DNS name resolution settings, defining nameservers, search domains, options, etc. In Kubernetes environments, this file plays an important role together with CoreDNS and also affects Pod DNS settings. In modern systems, systemd-resolved may dynamically manage this file.
</details>

## Hands-on Questions

20. Write the commands to create a new network namespace and list network interfaces within that namespace.

<details>

<summary>Show Answer</summary>

**Answer:**
```bash
# Create a new network namespace
ip netns add mynetns

# List network interfaces within that namespace
ip netns exec mynetns ip link list
```

**Explanation:**
The first command creates a new network namespace named "mynetns". The second command executes the `ip link list` command within that namespace to list network interfaces. A newly created network namespace contains only the loopback interface (lo) by default, and this interface is initially in down state.
</details>

21. Write the command to check the cgroup information of a specific process (PID: 1234).

<details>

<summary>Show Answer</summary>

**Answer:**
```bash
cat /proc/1234/cgroup
```

**Explanation:**
In Linux, you can check the cgroup information of a specific process through the `/proc/<PID>/cgroup` file. This file shows all cgroup hierarchies and controller information the process belongs to. Alternatively, you can use the `systemd-cgls` command to view the cgroup hierarchy in tree format.
</details>

22. Write a chmod command to give the file "example.sh" read, write, execute permissions to the owner, read and execute permissions to the group, and read-only permission to other users.

<details>

<summary>Show Answer</summary>

**Answer:**
```bash
chmod 754 example.sh
```

or

```bash
chmod u=rwx,g=rx,o=r example.sh
```

**Explanation:**
The first method uses numeric notation:
  - 7(rwx): Grant read(4), write(2), execute(1) permissions to owner
  - 5(r-x): Grant read(4) and execute(1) permissions to group
  - 4(r--): Grant read(4) permission only to other users

The second method uses symbolic notation to set the same permissions.
</details>

23. Write the command to check the system's current memory usage.

<details>

<summary>Show Answer</summary>

**Answer:**
```bash
free -h
```

**Explanation:**
The `free` command displays the system's memory usage. The `-h` option outputs in human-readable format (e.g., GB, MB). The output includes total memory, used memory, free memory, memory used for buffers/cache, swap memory information, etc.
</details>

24. Write the command to find the process running on a specific port (e.g., 8080).

<details>

<summary>Show Answer</summary>

**Answer:**
```bash
lsof -i :8080
```

or

```bash
netstat -tulpn | grep :8080
```

or

```bash
ss -tulpn | grep :8080
```

**Explanation:**
  - `lsof -i :8080`: Shows processes using port 8080.
  - `netstat -tulpn | grep :8080`: Finds entries using port 8080 from the TCP/UDP connection list. Uses options `-t`(TCP), `-u`(UDP), `-l`(listening), `-p`(process info), `-n`(show numerically).
  - `ss -tulpn | grep :8080`: A modern replacement for `netstat` that provides the same information.
</details>

25. Write the commands to configure the kernel modules br_netfilter and overlay to load automatically at boot, which are required for Kubernetes nodes.

<details>

<summary>Show Answer</summary>

**Answer:**
```bash
cat <<EOF | sudo tee /etc/modules-load.d/kubernetes.conf
overlay
br_netfilter
EOF

# Load immediately in current session
sudo modprobe overlay
sudo modprobe br_netfilter
```

**Explanation:**
Creating a `.conf` file in the `/etc/modules-load.d/` directory causes the systemd-modules-load service to automatically load those modules at boot. The `overlay` module supports the OverlayFS file system used for container image layers, and the `br_netfilter` module allows bridge traffic to pass through iptables, which is essential for Kubernetes networking.
</details>

26. Write a journalctl command to view real-time logs of the kubelet service while filtering only error level and above messages.

<details>

<summary>Show Answer</summary>

**Answer:**
```bash
journalctl -u kubelet -f -p err
```

or

```bash
journalctl -u kubelet -f -p warning
```

**Explanation:**
  - `-u kubelet`: Show only kubelet service logs
  - `-f`: Stream new logs in real-time (similar to tail -f)
  - `-p err`: Show only error level and above logs (err, crit, alert, emerg)
  - `-p warning`: Show warning level and above logs (warning, err, crit, alert, emerg)

journalctl priority levels range from 0(emerg) to 7(debug), and messages at the specified level and higher priority are displayed.
</details>

27. Write the commands to check the system's current timezone and change it to Asia/Seoul.

<details>

<summary>Show Answer</summary>

**Answer:**
```bash
# Check current timezone
timedatectl

# Change timezone
sudo timedatectl set-timezone Asia/Seoul
```

**Explanation:**
The `timedatectl` command is systemd's time management utility that can set and check the system's time, date, and timezone. The `timedatectl list-timezones` command shows available timezones. In Kubernetes clusters, it helps with log analysis and troubleshooting if all nodes use the same timezone or use UTC.
</details>

28. Write the configuration to add to /etc/security/limits.conf to permanently set the file descriptor limit to 65536.

<details>

<summary>Show Answer</summary>

**Answer:**
```bash
*               soft    nofile          65536
*               hard    nofile          65536
```

or for specific users/services:
```bash
root            soft    nofile          65536
root            hard    nofile          65536
```

**Explanation:**
`/etc/security/limits.conf` is a configuration file used by PAM (Pluggable Authentication Modules) to define per-user resource limits. `*` means all users, `soft` is the default limit, `hard` is the maximum limit. `nofile` specifies the number of file descriptors that can be opened. On Kubernetes nodes, many network connections and file handles are needed, so this value should be set high.
</details>

## Advanced Questions

29. Explain the three main technologies used by the Linux kernel for container isolation and describe what kind of isolation each provides.

<details>

<summary>Show Answer</summary>

**Answer:**

1. **Namespaces**:
  - Namespaces isolate process groups so that each group can see system resources independently.
  - Main namespace types:
  - PID namespace: Process ID isolation
  - Network namespace: Network stack isolation (interfaces, routing tables, firewall, etc.)
  - Mount namespace: File system mount point isolation
  - UTS namespace: Hostname and domain name isolation
  - IPC namespace: Inter-process communication resource isolation
  - User namespace: User and group ID isolation
  - cgroup namespace: cgroup root directory isolation

2. **cgroups (Control Groups)**:
  - cgroups is a feature that limits and isolates the resource usage of process groups.
  - Isolation provided:
  - CPU time limiting
  - Memory usage limiting
  - Block I/O bandwidth limiting
  - Network bandwidth limiting
  - Device access control

3. **Capabilities**:
  - Linux capabilities divide traditional root privileges into smaller privilege units.
  - Isolation provided:
  - Privilege isolation: Grant only minimum necessary privileges to containers
  - Security enhancement: Reduce security risks by removing unnecessary privileges
  - Examples: `CAP_NET_ADMIN` (network configuration changes), `CAP_SYS_ADMIN` (system administration tasks), etc.

These three technologies combine to allow containers to run in an isolated environment from the host system and other containers, with limited resource usage and enhanced security.
</details>

30. Explain how OverlayFS manages container image layers and describe the relationship between read-only and writable layers.

<details>

<summary>Show Answer</summary>

**Answer:**

OverlayFS is a union mount file system that overlays multiple directories to present them as a single directory. In container image layer management, OverlayFS works as follows:

1. **Layer Structure**:
  - **Lower directory (read-only layers)**: The base image layers; multiple can exist. Contains the base file system and application code.
  - **Upper directory (writable layer)**: The writable layer created when the container runs. All changes made within the container are stored in this layer.
  - **Work directory**: A temporary directory for OverlayFS internal operations.
  - **Merged directory**: The final view where all layers are integrated; the file system the container actually sees.

2. **Relationship between read-only and writable layers**:
  - **File reading**: When reading a file, OverlayFS first looks for the file in the Upper directory (writable layer). If not found, it searches the Lower directory (read-only layers) sequentially.
  - **File writing**: When modifying a file, Copy-on-Write (CoW) is used. When trying to modify a file in a read-only layer, the file is first copied to the writable layer then modified. The original file remains unchanged.
  - **File deletion**: When trying to delete a file in a read-only layer, the file is not actually deleted; instead, a "whiteout" file is created in the writable layer to make it appear deleted.

3. **Benefits**:
  - **Space efficiency**: Multiple containers share the same base image layers, saving disk space.
  - **Fast start time**: When starting a new container, only the writable layer needs to be created, not copying the entire file system.
  - **Image version management**: Images can be updated by adding new layers to the base image.

In this way, OverlayFS efficiently manages container image layers, allowing containers to have independent file systems while sharing base images.
</details>

31. Explain how Linux capabilities affect container security and why it is important to grant only the minimum necessary capabilities to containers.

<details>

<summary>Show Answer</summary>

**Answer:**

**Linux Capabilities and Container Security:**

Linux capabilities divide traditional root privileges into smaller privilege units, affecting container security in the following ways:

1. **Privilege Granularity**:
  - Traditionally, processes were only distinguished as root (UID 0) or non-root.
  - Capabilities allow dividing root privileges into multiple individual privileges, allowing only specific necessary privileges to be granted to processes.
  - Example: To change network settings, only the `CAP_NET_ADMIN` capability is needed instead of full root privileges.

2. **Container Security Enhancement**:
  - Container runtimes grant only a limited set of capabilities to containers by default.
  - This limits the impact containers can have on the host system.
  - Even processes running as root inside containers have limited capabilities, reducing security risks.

3. **Key Container-related Capabilities**:
  - `CAP_NET_ADMIN`: Network configuration changes
  - `CAP_SYS_ADMIN`: System administration tasks (very powerful)
  - `CAP_CHOWN`: File ownership changes
  - `CAP_DAC_OVERRIDE`: Bypass file permissions
  - `CAP_SETUID`: UID changes
  - `CAP_SETGID`: GID changes

**Importance of Least Privilege Principle:**

It is important to grant only the minimum necessary capabilities to containers for the following reasons:

1. **Reduced Attack Surface**:
  - Removing unnecessary capabilities reduces vectors that attackers can exploit.
  - Even if a container is compromised, the actions an attacker can take are limited.

2. **Container Escape Prevention**:
  - Powerful capabilities (especially `CAP_SYS_ADMIN`) can enable container escape (accessing the host from a container).
  - Restricting these capabilities significantly reduces container escape risk.

3. **Defense in Depth Strategy**:
  - Least privilege principle is part of defense in depth security strategy.
  - Used with other security mechanisms (seccomp, AppArmor, SELinux, etc.) provides stronger security.

4. **Regulatory Compliance**:
  - Many security standards and regulations require the least privilege principle.
  - Granting only minimum necessary capabilities to containers helps meet these requirements.

5. **Problem Isolation**:
  - Granting limited capabilities to containers prevents issues in one container from spreading to other containers or the host system.

In production environments, it is good security practice to accurately identify the capabilities a container needs and remove all other capabilities. Docker's `--cap-drop`, `--cap-add` options or Kubernetes' `securityContext.capabilities` field can be used for this.
</details>

32. Explain the structure of a systemd service unit file and the role of main sections ([Unit], [Service], [Install]), and write a basic unit file example for the Kubernetes kubelet service.

<details>

<summary>Show Answer</summary>

**Answer:**

**Main sections of a systemd unit file:**

1. **[Unit] Section**: Defines unit metadata and dependencies
   - `Description`: Service description
   - `Documentation`: Documentation URL
   - `After/Before`: Defines startup order
   - `Requires/Wants`: Defines dependencies

2. **[Service] Section**: Defines how to run the service
   - `Type`: Service type (simple, forking, oneshot, etc.)
   - `ExecStart`: Command to execute
   - `Restart`: Restart policy
   - `RestartSec`: Restart wait time

3. **[Install] Section**: Defines behavior when unit is enabled
   - `WantedBy`: Target that wants this unit

**kubelet service unit file example:**

```ini
[Unit]
Description=kubelet: The Kubernetes Node Agent
Documentation=https://kubernetes.io/docs/
Wants=network-online.target
After=network-online.target

[Service]
ExecStart=/usr/bin/kubelet
Restart=always
StartLimitInterval=0
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**Explanation:**
This unit file defines the kubelet service. It starts after the network is ready (`After=network-online.target`), always restarts on failure (`Restart=always`), and attempts to restart every 10 seconds (`RestartSec=10`). `WantedBy=multi-user.target` means this service starts when the system boots into multi-user mode.
</details>

33. Explain how to permanently set sysctl kernel parameters required for Kubernetes node configuration and describe the role of each parameter.

<details>

<summary>Show Answer</summary>

**Answer:**

**Key sysctl settings required for Kubernetes and their roles:**

```bash
# Create /etc/sysctl.d/99-kubernetes.conf file
cat <<EOF | sudo tee /etc/sysctl.d/99-kubernetes.conf
# Enable IP forwarding - essential for packet routing between containers
net.ipv4.ip_forward = 1
net.ipv6.conf.all.forwarding = 1

# Bridge traffic passes through iptables - essential for CNI network policies
net.bridge.bridge-nf-call-iptables = 1
net.bridge.bridge-nf-call-ip6tables = 1

# Connection tracking table size (for large clusters)
net.netfilter.nf_conntrack_max = 1000000
EOF

# Apply settings
sudo sysctl --system
```

**Role of each parameter:**

1. **net.ipv4.ip_forward = 1**
   - Allows the Linux kernel to forward packets between network interfaces
   - Essential for communication from Pods to other Pods or external networks
   - Container networking will not work if disabled

2. **net.bridge.bridge-nf-call-iptables = 1**
   - Configures traffic passing through bridges to be subject to iptables rules
   - Essential for Kubernetes services (ClusterIP, NodePort) and NetworkPolicy to work correctly
   - Required because kube-proxy uses iptables for service routing

3. **net.ipv6.conf.all.forwarding = 1**
   - Enables packet forwarding in IPv6 environments
   - Needed for dual-stack clusters

**Order of setting application:**
1. First load the `br_netfilter` module: `modprobe br_netfilter`
2. Create the sysctl configuration file
3. Apply all settings with `sysctl --system`

Without these settings, Kubernetes cluster networking will not function properly, especially with issues in Pod-to-Pod communication and service discovery.
</details>

34. Explain Linux log management strategy using journald and logrotate, and present configuration methods for efficient log management on Kubernetes nodes.

<details>

<summary>Show Answer</summary>

**Answer:**

**Roles of journald and logrotate:**

**journald (systemd-based logging):**
- Collects stdout/stderr logs from systemd services
- Stored in binary format, queried with journalctl
- Supports automatic log compression and rotation

**logrotate (traditional log file management):**
- Manages rotation, compression, and deletion of text log files
- Runs periodically via cron job

**Kubernetes Node Log Management Configuration:**

**1. journald configuration (/etc/systemd/journald.conf):**
```ini
[Journal]
# Store persistently on disk
Storage=persistent

# Maximum disk usage (total /var/log/journal)
SystemMaxUse=2G

# Maximum file size
SystemMaxFileSize=100M

# Minimum free space to maintain
SystemKeepFree=1G

# Maximum retention period
MaxRetentionSec=1month
```

**2. logrotate configuration for container logs:**
```bash
# /etc/logrotate.d/containers
/var/log/containers/*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    copytruncate
    maxsize 100M
}
```

**3. Log cleanup commands:**
```bash
# journald log cleanup
journalctl --vacuum-time=7d   # Delete logs older than 7 days
journalctl --vacuum-size=1G   # Delete old logs when exceeding 1GB

# Check disk usage
journalctl --disk-usage
```

**Kubernetes Log Management Best Practices:**

1. **kubelet logs**: Managed by journald, stored in `/var/log/journal/`
2. **Container logs**: Stored in `/var/log/containers/`, managed by logrotate
3. **Centralized logging**: Recommended to forward to external systems using Fluentd/Fluent Bit

Proper log management maintains a balance between preventing node failures due to disk space exhaustion and preserving logs for troubleshooting.
</details>

---

[Return to Learning Materials](../../basics/01-linux-basics.md) | [Next Quiz: Linux Operations](./02-linux-advanced-quiz.md)
