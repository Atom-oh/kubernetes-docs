# 1. 你的第一个 Linux 终端

> **支持版本**：Ubuntu Server 24.04 LTS（主要路径）、Rocky Linux 9（备选路径）
> **最后更新**：2026 年 9 月 15 日

[课程准备](README.md) | [测验](../../quizzes/networking/beginner/01-linux-cli-quiz.md) | [下一课：地址与接口](02-addressing-interfaces.md)

网络管理始于能够回答三个问题：我正在使用哪台机器？我正在更改哪个文件？如何撤销这项更改？本课将帮助你养成这些习惯：创建一个小型笔记本、编辑它、检查其权限，并查看服务状态。

## 先决条件与学习成果

使用一台临时的**本地虚拟机**，并准备普通用户账户、密码以及使用 `sudo` 的权限。通过虚拟机管理程序控制台打开虚拟机；虚拟机管理程序是用来运行虚拟机的应用。主要教学路径使用 Ubuntu Server 24.04 LTS。Rocky Linux 9 是备选方案；不需要同时学习两种系统。一般容器并不提供本课使用的完整、已启动 systemd 环境。

请确保虚拟机中有 Bash、GNU 核心工具、`ps`、systemd、`nano` 和一种 `vi` 实现。如果缺少编辑器，请先完成下方的软件包准备，再开始创建笔记本。本课不需要网络配置。请保留课程介绍中准备好的 NAT/DHCP 管理接口。

完成后，你应该能够：

- 说明内核、库、Shell 和发行版分别提供什么。
- 浏览路径，并创建、复制、移动、编辑和删除自己的练习文件。
- 在 nano 和 vi 中保存或丢弃编辑内容，并解释基本的所有权和权限。
- 选择 Ubuntu 或 Rocky 的软件包工具，并区分已安装的软件与正在运行的服务。
- 读取进程 ID、systemd 状态以及范围受限的一组 journal 消息。

**执行约定**：下方每个 Shell 代码块都要在**练习虚拟机内部**运行，绝不能在笔记本电脑宿主系统、本仓库的宿主机或云服务器上运行。不带 `sudo` 的代码块以普通用户身份运行。`sudo` 行只对该命令提权。每次只运行一个步骤，遇到意外错误就停止。示例输出仅供说明，**并非在真实 Ubuntu/Rocky 虚拟机上实测的记录**。

## 了解你登录的系统

“Linux”可以指**内核**，也可以非正式地指完整操作系统。内核管理 CPU 时间、内存、文件系统、设备驱动程序和网络数据包。它通过系统调用提供服务，供程序请求使用。你的 Shell 和编辑器在**用户空间**运行，位于内核之外。

**库**提供可复用的函数。例如，GNU C Library（glibc）为许多程序提供文本、文件 I/O 和操作系统访问等功能。有些库函数会调用内核；另一些只处理内存中的数据。库既不是编辑器，也不是第二个内核。应用程序需要特定库时，软件包之间就会出现依赖关系。

**发行版**会将内核、库、命令、安装程序、软件仓库、更新和默认配置组合成可安装的系统。这里的仓库是受管理的软件包来源；软件包包含软件本身及其版本和依赖信息。

| 发行版 | 关系与软件包系列 | 对本课程的意义 |
| --- | --- | --- |
| Debian | 使用 `.deb` 软件包、APT 和 dpkg 的社区发行版 | 说明 Ubuntu 所属的发行版系列；Debian 的网络/服务默认设置不会自动等同于 Ubuntu |
| Ubuntu | 基于 Debian 派生，拥有自己的版本和软件仓库 | 按照 Ubuntu Server 24.04 LTS 命令路径操作 |
| Rocky Linux | 属于 RHEL 生态的企业 Linux 发行版；使用 `.rpm` 软件包、DNF 和 RPM | 按照 Rocky 9 备选软件包路径操作 |

**终端**负责处理键盘输入和文本显示。本课程使用 Bash 作为 **Shell**，它会解释你输入的内容并运行命令。输入 `ls` 是在请求一个用户空间程序列出文件；这并非直接与内核对话。这些区别可参阅参考资料中的 Debian 和 GNU 文档。

**练习虚拟机，普通用户；仅检查：**

```bash
hostname
whoami
id
cat /etc/os-release
uname -r
pwd
```

`hostname` 用于识别虚拟机；请与打开的控制台窗口核对。`whoami` 用于识别你的账户。`id` 会显示数字用户 ID（UID）、组 ID 及所属组。如果 UID 为 `0`，你当前是 root；这些练习应返回普通账户。`cat` 用于显示文本文件。在 `/etc/os-release` 中检查 `ID` 和 `VERSION_ID`：主要路径应识别为 Ubuntu 和 `24.04`，Rocky 备选路径则应为 Rocky 和 `9.x`。`uname -r` 报告的是**当前运行的内核版本**，并非发行版版本号。`pwd` 会打印当前工作目录。

示例提示符为 `learner@client:~$`：账户、机器、当前目录，然后是提示符标记。`~` 代表你的主目录。`$` 通常表示普通 Shell，`#` 常表示 root，但提示符可以自定义；应以 `id` 输出为准。**不要输入提示符标记**。在命令块中，以 `#` 开头的行是 Bash 注释，用于解释说明。

## 运行前先读懂命令

在 `ls -la notes` 中，`ls` 是命令，`-l` 和 `-a` 是选项，`notes` 是路径参数。`-l` 要求显示详细信息；`-a` 会包含以点开头的名称。按 Enter 运行命令，按 Tab 补全部分输入的路径，按向上键调出上一条命令。重新运行历史命令前先检查其内容。

Linux 路径组成一棵以 `/` 为根的树。**绝对路径**以 `/` 开头，例如 `/home/learner`；**相对路径**从工作目录开始，例如 `notes/draft.txt`。`.` 表示当前目录，`..` 表示父目录。在本课使用的常见 Linux 文件系统上，`Notes` 和 `notes` 是两个不同名称。

`/etc` 存放系统配置，`/var/log` 存放许多日志，`/home` 存放普通用户的主目录。我们会读取系统信息，但只在新建的私有目录下写练习文件。

**练习虚拟机，普通用户；使用内置/本地帮助：**

```bash
help cd
ls --help
man ls
```

`cd` 是 Shell 内置命令，因此 Bash 的 `help` 会解释它。`--help` 会打印命令用法。如果安装了可选的 `man` 程序/手册页，`man ls` 会在分页器中打开手册：按 Space 向前翻页，输入 `/permission` 搜索，按 `q` 退出。如果没有 `man`，仍可使用 `ls --help` 和参考资料。`Ctrl+C` 会取消尚未执行的 Shell 输入行，或中断许多前台程序；它不是通用的“保存并退出”命令。

## 软件包准备：选择一种发行版

软件包管理用于从已配置的软件仓库安装编辑器及其依赖库。先检查系统上已经安装的内容。以下查询使用本地软件包数据库，无需仓库连接或提权。

**仅限 Ubuntu 练习虚拟机，普通用户：**

```bash
dpkg-query -W bash coreutils nano vim-tiny iproute2
```

**仅限 Rocky 练习虚拟机，普通用户：**

```bash
rpm -q bash coreutils nano vim-minimal iproute
```

每个已安装的软件包都会显示名称和版本。“未安装”或“未找到软件包”表示缺少对应软件包；这不是替换整个系统的理由。不同软件包可能提供相同命令，因此还要直接检查命令是否可用。

**任一练习虚拟机，普通用户：**

```bash
command -v nano
command -v vi
```

如果显示可执行文件路径（例如 `/usr/bin/vi`），说明命令可用。没有显示路径则表示它不在 Shell 的命令搜索路径中。

如果缺少编辑器，以下是一个**可选的虚拟机准备操作**。通过已经可用的管理连接，只使用对应发行版的代码块。首先在虚拟机管理程序中创建一个有名称的虚拟机快照，例如 `before-cli-editors`，以便恢复完整的安装前状态。阅读将要执行的事务，并确认只安装预期的编辑器及其依赖；如果出现意外的删除或升级，回答 `n` 取消。

**仅限 Ubuntu 练习虚拟机，普通用户执行 sudo：**

```bash
sudo apt update
sudo apt install nano vim-tiny
```

`apt update` 会刷新可用软件包索引；它**不会**升级所有已安装软件。只有索引刷新成功且没有软件仓库错误时，才继续安装。`apt install` 会安装指定软件包并解析依赖。`apt upgrade` 的用途不同，它会升级已安装软件；本课不需要执行。

**仅限 Rocky 练习虚拟机，普通用户执行 sudo：**

```bash
sudo dnf install nano vim-minimal
```

DNF 会解析 RPM 软件包依赖，并在需要时刷新软件仓库元数据。Rocky 9 也提供 `yum` 兼容接口以支持熟悉的命令，但本课程使用 `dnf`。不要在同一台虚拟机上同时运行这两种命令族，也不要为了运行示例而添加第三方软件仓库。

准备好后，重复本地软件包查询和 `command -v` 检查。下载软件包失败说明管理连接/软件仓库访问有问题，与下一课介绍的隔离实验网卡无关。

**恢复：**`apt remove` 或 `dnf remove` 可以删除软件包，但并不是安装操作的精确逆操作：依赖关系、缓存、日志和某些配置可能仍会保留。不要删除原本就已安装的编辑器。可在后续课程中继续使用这些编辑器，也可以在完成虚拟机操作后恢复 `before-cli-editors`；恢复快照也会丢弃快照之后的所有工作。清理笔记本时不需要删除软件包或运行 `autoremove`。

## 在唯一的临时目录中建立笔记本

先建立本练习的边界。`$HOME` 已表示你的主目录；不要重新定义它。`LAB_DIR` 是本课新建的变量。`$(...)` 会捕获命令输出，双引号则确保路径即使含有空格也保持完整。

**练习虚拟机，普通用户：**

```bash
LAB_DIR=$(mktemp -d "$HOME/network-beginner-cli.XXXXXX")
printf '%s\n' "$LAB_DIR"
```

`mktemp -d` 会创建新目录，并将六个 `X` 字符替换为唯一后缀。`printf '%s\n'` 会打印保存的路径并换行。路径可能类似 `/home/learner/network-beginner-cli.aB12Cd`，但账户和后缀应是**你自己的**。继续前记录实际路径。如果创建失败或打印值为空，请停止；不要继续文件练习。

**同一虚拟机与 Shell，普通用户：**

```bash
cd -- "$LAB_DIR"
pwd
ls -la
```

只有当 `pwd` 与记录的目录一致时才能继续。`cd` 会更改相对路径的起点；它不会移动文件。`--` 用于结束选项解析。初始目录列表包含 `.` 和 `..`，新目录仅对你的账户开放。

**同一虚拟机与 Shell，普通用户；当前位于该目录：**

```bash
mkdir notes archive
touch notes/draft.txt notes/vi.txt
ls -l notes
cd notes
pwd
cd ..
pwd
```

`mkdir` 用于创建目录。由于两个文件原本不存在，`touch` 会创建它们；如果文件已经存在，它只会更新时间戳，而不会清空内容。两个文件的初始大小都为 `0`。第一个 `pwd` 的路径以 `/notes` 结尾；第二个则返回临时目录根目录。成功执行 `mkdir`、`touch` 或 `cd` 通常不会打印内容。没有输出很正常；请用 `ls` 或 `pwd` 检查结果。

## 编辑、保存、复制和移动

**同一练习虚拟机，普通用户，位于临时目录根目录：**

```bash
nano notes/draft.txt
```

在**编辑器中**输入以下两行，而不是在 Shell 中输入：

```text
I am learning Linux networking.
This file belongs to my practice notebook.
```

在 nano 帮助栏中，`^O` 表示 **Ctrl+O**，并非字符 `^` 和 `O`。按 Ctrl+O，检查文件名，再按 Enter 写入。按 Ctrl+X 退出。如果要丢弃上次保存后所做的编辑，按 Ctrl+X，并在询问是否保存时选择 `N`；本地化提示中显示的按键可能不同。选择 `Y` 会在确认文件名后写入更改。

**返回 Shell，同一虚拟机，普通用户：**

```bash
cat notes/draft.txt
cp -i -- notes/draft.txt notes/copy.txt
mv -i -- notes/copy.txt archive/saved.txt
ls -l notes archive
```

`cat` 应显示已保存的内容。`cp` 会将内容复制到第二个文件，原文件仍保留。`mv` 会移动或重命名文件：`notes/copy.txt` 会变成 `archive/saved.txt`。这两个命令中的 `-i` 都会在目标文件将被覆盖时询问；如果没有预期目标文件，请回答 `n`。预期结果是 `notes` 中有 `draft.txt` 和 `vi.txt`，`archive` 中有 `saved.txt`。现在已有保存副本；之后的编辑出错时可用它恢复草稿。

如需恢复，请以普通用户身份在同一临时目录根目录中执行 `cp -i -- archive/saved.txt notes/draft.txt`；只有确实要丢弃草稿更新内容时才确认覆盖。

**同一练习虚拟机，普通用户，位于临时目录根目录：**

```bash
vi notes/vi.txt
```

在这些虚拟机上，`vi` 通常会运行 Vim 的某个变体。它启动时处于**普通模式**，此时按键是命令。按 `i` 进入插入模式，输入 `I can save and exit vi.`，然后按 Esc 返回普通模式。

| 按 Esc 后输入的按键 | 结果 |
| --- | --- |
| `:w` 然后 Enter | 保存并继续编辑 |
| `:wq` 然后 Enter | 保存并退出当前单文件会话 |
| `:q` 然后 Enter | 没有未保存更改时退出 |
| `:q!` 然后 Enter | 丢弃上次保存以来的更改并退出 |

练习使用 `:wq`，重新打开文件，按 `i` 后输入一个额外单词，然后按 Esc、`:q!`、Enter 丢弃这次额外编辑。返回 Shell 后，`cat notes/vi.txt` 应仍只显示已保存的句子。冒号命令要在 **vi 内部**执行，而不是在 Bash 中执行。`:q` 显示 “No write since last change” 时，是在保护未保存内容。

## 权限与 sudo


每个文件都有所有者和所属组。基本权限依次适用于所有者、组和其他所有用户。在示例输出 `-rw-r--r--` 中，第一个 `-` 表示普通文件；之后的三组权限表示所有者可读/写、组用户可读、其他用户可读。目录以 `d` 开头。额外的 `.` 或 `+` 可能表示安全元数据或 ACL；本课首次练习不涉及这些额外控制。

对文件而言，`r` 表示读取内容，`w` 表示修改内容，`x` 表示允许执行。对目录而言，`r` 表示列出名称，`x` 表示允许遍历/访问，`w` 与遍历权限结合后允许创建/删除目录项，但仍受其他控制限制。仅凭文件的写入权限，无法判断能否删除其目录项。

**同一练习虚拟机，普通用户，位于临时目录根目录；仅更改你的草稿：**

```bash
ls -l notes/draft.txt
LAB_DRAFT_MODE=$(stat -c '%a' notes/draft.txt)
printf '%s\n' "$LAB_DRAFT_MODE"
chmod 600 notes/draft.txt
ls -l notes/draft.txt
```

`stat` 会记录原始数字模式；请保存此值。每组三位权限中，读取为 4，写入为 2，执行为 1。因此 `600` 会给所有者 `4+2`，组用户为 `0`，其他用户也为 `0`：预期显示 `-rw-------`。外层临时目录已经限制了访问，因此本练习用于理解权限，不需要创建真实的机密文件。

**立即撤销，同一虚拟机与 Shell，普通用户：**

```bash
chmod "$LAB_DRAFT_MODE" notes/draft.txt
stat -c '%a' notes/draft.txt
```

结果数字应与记录的原始模式相同。我们恢复记录的值，而不假设每个系统的原始权限都是 `644`。修改你拥有的文件权限无需 `sudo`。

`sudo` 默认以 root 身份运行获准命令。它通常会要求输入**你的账户密码**，但输入时可能不会显示任何字符。它不是解决“Permission denied”的通用办法。

**练习虚拟机，普通用户；通过一个提权查询查看身份：**

```bash
sudo whoami
whoami
```

预期先显示 `root`，再显示你的普通用户名。如果你没有授权，请停止并使用为课程准备好的账户；不要盲目修改 `sudoers`。如果无法写入笔记本，先检查相关目录的 `pwd`、`id` 和 `ls -ld` 输出。避免进行宽泛的递归权限更改：这会掩盖原因并影响无关文件。

## 程序、进程、服务和日志

**程序**是存储在磁盘上的软件。**进程**是正在运行的实例，具有进程 ID（PID）、所有者和内存。安装程序不一定会启动它。**服务**是在后台管理的工作，通常由 systemd 管理；一个服务可以对应多个进程。

**练习虚拟机，普通用户；仅检查：**

```bash
ps -p $$ -o pid,ppid,user,comm
ps -p 1 -o pid,comm
```

`$$` 会展开为当前 Bash Shell 的 PID。`-p` 用于选择 PID，`-o` 用于选择显示列。`PPID` 是父进程 ID；`COMM` 是命令名称。预期第一条结果是你的 Shell，在这些已启动的虚拟机中，systemd 应为 PID 1。除 1 以外的 PID 数字会变化。如果 PID 1 不是 systemd，请回到完整虚拟机环境，再继续服务练习。

**练习虚拟机，普通用户；运行一个有时限的前台进程：**

```bash
sleep 30
```

`sleep` 运行时，Shell 会等待。按 Ctrl+C 中断并返回提示符，或者等待它在 30 秒后结束。无需清理文件或服务配置。这样练习比终止陌生进程更安全。`kill` 会向指定进程发送信号；复制文档中的 PID 可能会影响他人的工作。

systemd 管理包括 `.service` 单元在内的各种**单元**。journal 收集 systemd 和服务的消息。先检查两条虚拟机路径都会用到的日志服务。

**练习虚拟机，普通用户；仅检查：**

```bash
systemctl status systemd-journald.service --no-pager
systemctl is-active systemd-journald.service
systemctl is-enabled systemd-journald.service
```

在 `status` 中，`Loaded` 表示是否找到了单元定义；`Active` 表示当前状态；适用时，`Main PID` 会标识主进程。日志服务通常应处于 active 状态。`is-enabled` 可能显示 `static`：这表示没有通常的 enablement 配置段，**不**代表服务损坏。单元也可以由依赖关系或激活机制启动。

| 要识别的操作 | 它会更改什么 |
| --- | --- |
| `start` / `stop` | 当前运行状态 |
| `restart` | 停止后再启动；可能中断用户 |
| `enable` / `disable` | 用于激活的启用链接，通常包括开机启动；本身不启动/停止服务 |
| `enable --now` | 启用并立即启动 |
| `reload` | 请求支持该操作的服务重新读取配置 |

这些概念供后续系统管理使用；**本练习不要停止或重启日志或网络服务**。已启用的服务可能已经失败，已禁用的服务也可能正在运行。应分别检查运行状态和启用状态。

**练习虚拟机，普通用户使用 sudo 读取系统日志：**

```bash
sudo journalctl -b -u systemd-journald.service -n 20 --no-pager
```

`-b` 将结果限制在当前启动周期，`-u` 选择单元，`-n 20` 将输出限制为最新的 20 条匹配记录。`--no-pager` 会直接返回 Shell。应一起阅读时间戳、机器、进程/单元和消息内容。journal 条目是事件证据，但未必代表错误。没有条目可能表示当前过滤条件未匹配到保留消息；权限不足也可能让你只能看到部分 journal。断定服务失败前，先对照 `status`。

## 完成检查与清理

删除笔记本前，在其根目录中使用 `cat` 和 `ls -l` 验证：

1. `notes/draft.txt` 和 `archive/saved.txt` 包含你的两句话，且 `notes/copy.txt` 已不存在。
2. `notes/vi.txt` 保留已保存的句子，但不包含已丢弃的额外单词。
3. 草稿权限模式与记录的原始值相同，并且你能说明每组三位权限的含义。
4. 你能识别虚拟机发行版、运行中的内核、普通账户、Shell PID 和 journald 活动状态，且不会将它们混淆。
5. 你能解释刷新软件包索引、启动服务和启用服务是三种不同操作。

现在只删除本课创建的文件。如果你另开了一个 Shell，变量**不会自动存在**：应将 `LAB_DIR` 设为所记录的准确路径，检查其内容，然后再继续。绝不要猜后缀，也不要用通配符选择所有目录。

**练习虚拟机，普通用户，使用记录的 `LAB_DIR`：**

```bash
cd -- "$LAB_DIR"
pwd
ls -la notes archive
```

确认这是你的临时目录后：

```bash
rm -i -- notes/draft.txt notes/vi.txt archive/saved.txt
rmdir -- notes archive
cd -- "$HOME"
rmdir -- "$LAB_DIR"
```

`rm -i` 会询问是否删除每个指定文件；只确认删除这些练习文件。`rmdir` 只删除**空目录**。如果命令拒绝执行，请检查剩余文件，包括编辑器备份/交换文件或尚未处理的 `copy.txt`，然后只按准确名称删除你确认属于本练习的文件。不要改用递归删除。部分清理后文件已不存在，也不是扩大删除范围的理由。

**练习虚拟机，普通用户；验证清理结果：**

```bash
test ! -e "$LAB_DIR"
echo $?
unset LAB_DIR LAB_DRAFT_MODE
sudo -k
```

`test ! -e` 会检查记录的路径是否已不存在；`echo $?` 应打印 `0`，表示前一条检查成功。`1` 表示该路径仍然存在。`unset` 会删除课程变量；`sudo -k` 会清除已缓存的 sudo 授权，因此下次提权命令可能再次要求输入密码。我们只检查了虚拟机系统配置；如果可选安装了编辑器，它们仍会保留，除非按上文说明恢复快照。

## 参考资料与延伸阅读

主要文档于 2026 年 9 月 14–15 日核对。以下资料介绍了本课使用的工具；它们不是先决条件，也不能替代练习。

- [Debian：关于 Debian](https://www.debian.org/intro/about)：发行版、内核、工具和软件包。
- [GNU C Library 简介](https://www.gnu.org/software/libc/manual/html_node/Introduction.html)：系统库提供的功能。
- [Debian 参考手册，GNU/Linux 教程](https://www.debian.org/doc/manuals/debian-reference/ch01.en.html)：Shell、文件系统、权限和进程。
- [GNU Coreutils 手册](https://www.gnu.org/software/coreutils/manual/coreutils.html)，尤其是 [mktemp](https://www.gnu.org/software/coreutils/manual/html_node/mktemp-invocation.html)：文件操作和私有临时目录。
- [GNU nano 快捷键](https://www.nano-editor.org/dist/latest/cheatsheet.html)和 [Vim 入门](https://vimhelp.org/usr_02.txt.html)：编辑器模式、写入和退出。
- [Ubuntu Server 软件包管理](https://ubuntu.com/server/docs/how-to/software/package-management/)和 [Rocky Linux 9 DNF 指南](https://docs.rockylinux.org/9/guides/package_management/dnf_package_manager/)：两种软件包操作路径。
- [systemd systemctl 手册](https://www.freedesktop.org/software/systemd/man/systemctl.html)和 [journalctl 手册](https://www.freedesktop.org/software/systemd/man/journalctl.html)：运行状态、启用状态和日志过滤器。

继续学习[地址与接口](02-addressing-interfaces.md)，并先完成[本课测验](../../quizzes/networking/beginner/01-linux-cli-quiz.md)检查理解情况。
