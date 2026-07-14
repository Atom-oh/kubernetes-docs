# Cilium eBPF クイズ

> **対応バージョン**: Cilium 1.17, Linux Kernel 4.19+
> **最終更新**: February 22, 2026

## eBPF の基本概念

1. **eBPF は何の略ですか？**
   - A) Extended Berkeley Packet Filter
   - B) Enhanced Berkeley Process Filter
   - C) Extended Binary Processing Framework
   - D) Enhanced Backend Processing Function

   <details>
   <summary>回答を表示</summary>
   <p><strong>回答</strong>: A) Extended Berkeley Packet Filter</p>
   <p><strong>解説</strong>: eBPF は Extended Berkeley Packet Filter の略であり、元の BPF 技術を拡張したものです。</p>
   </details>

2. **eBPF プログラムはどこで実行されますか？**
   - A) User Space
   - B) Kernel Space
   - C) Hypervisor
   - D) Container Runtime

   <details>
   <summary>回答を表示</summary>
   <p><strong>回答</strong>: B) Kernel Space</p>
   <p><strong>解説</strong>: eBPF プログラムは Linux kernel 内で安全に実行されます。</p>
   </details>

3. **eBPF プログラムの安全性を確保するメカニズムは何ですか？**
   - A) Sandbox
   - B) Virtual Machine
   - C) Static Verifier
   - D) Containerization

   <details>
   <summary>回答を表示</summary>
   <p><strong>回答</strong>: C) Static Verifier</p>
   <p><strong>解説</strong>: eBPF verifier は、無限ループや kernel crash を防ぐために、ロード前にプログラムの安全性を検証します。</p>
   </details>

4. **eBPF プログラムがアタッチできる kernel event は何と呼ばれますか？**
   - A) Triggers
   - B) Hooks
   - C) Event Listeners
   - D) Callbacks

   <details>
   <summary>回答を表示</summary>
   <p><strong>回答</strong>: B) Hooks</p>
   <p><strong>解説</strong>: eBPF プログラムは kernel 内のさまざまな hook point にアタッチされ、event が発生すると実行されます。</p>
   </details>

5. **eBPF プログラムと user space application 間でデータを共有するために使用されるものは何ですか？**
   - A) Shared Memory
   - B) Pipes
   - C) BPF Maps
   - D) Sockets

   <details>
   <summary>回答を表示</summary>
   <p><strong>回答</strong>: C) BPF Maps</p>
   <p><strong>解説</strong>: BPF Maps は、eBPF プログラムと user space application 間でデータを共有するために使用される key-value store です。</p>
   </details>

## eBPF と Cilium

6. **Cilium が eBPF を使用する主な理由は何ですか？**
   - A) kernel module なしで networking feature を実装すること
   - B) より優れた user interface を提供すること
   - C) より少ない memory を使用すること
   - D) より簡単な installation process

   <details>
   <summary>回答を表示</summary>
   <p><strong>回答</strong>: A) kernel module なしで networking feature を実装すること</p>
   <p><strong>解説</strong>: Cilium は eBPF を使用して、kernel module なしで高性能な networking、load balancing、security policy、その他の機能を実装します。</p>
   </details>

7. **Cilium で eBPF を使用して実装されていない機能はどれですか？**
   - A) Network policy enforcement
   - B) Service load balancing
   - C) Network packet encryption
   - D) User authentication

   <details>
   <summary>回答を表示</summary>
   <p><strong>回答</strong>: D) User authentication</p>
   <p><strong>解説</strong>: Cilium は eBPF を使用して Network policy enforcement、Service load balancing、network packet processing を実装しますが、User authentication は通常、他の system で処理されます。</p>
   </details>

8. **Cilium は kube-proxy を置き換えるためにどの eBPF 機能を使用しますか？**
   - A) XDP (eXpress Data Path)
   - B) TC (Traffic Control) BPF
   - C) Socket BPF
   - D) Tracing BPF

   <details>
   <summary>回答を表示</summary>
   <p><strong>回答</strong>: B) TC (Traffic Control) BPF</p>
   <p><strong>解説</strong>: Cilium は主に TC (Traffic Control) BPF プログラムを使用して、kube-proxy の Service load balancing 機能を置き換えます。</p>
   </details>

9. **Cilium の eBPF ベースの load balancing が kube-proxy より優れている理由は何ですか？**
   - A) より多くの Service type をサポートする
   - B) より優れた user interface
   - C) より低い latency とより高い throughput
   - D) より簡単な configuration

   <details>
   <summary>回答を表示</summary>
   <p><strong>回答</strong>: C) より低い latency とより高い throughput</p>
   <p><strong>解説</strong>: Cilium の eBPF ベースの load balancing は Kernel Space で packet を直接処理するため、より低い latency とより高い throughput を実現します。</p>
   </details>

10. **Cilium で eBPF を使用して収集されない metric はどれですか？**
    - A) Network connection status
    - B) Packet drop reasons
    - C) Service response time
    - D) User login time

    <details>
    <summary>回答を表示</summary>
    <p><strong>回答</strong>: D) User login time</p>
    <p><strong>解説</strong>: Cilium は eBPF を使用して Network connection status、packet drop reason、Service response time などの network 関連の metric を収集しますが、User login time のような application-level metric は収集しません。</p>
    </details>

## eBPF プログラミング

11. **eBPF プログラムの作成に主に使用される言語は何ですか？**
    - A) Python
    - B) Go
    - C) C
    - D) Rust

    <details>
    <summary>回答を表示</summary>
    <p><strong>回答</strong>: C) C</p>
    <p><strong>解説</strong>: eBPF プログラムは主に C で記述され、LLVM compiler を使用して eBPF bytecode にコンパイルされます。</p>
    </details>

12. **eBPF プログラムを開発するための framework ではないものはどれですか？**
    - A) BCC (BPF Compiler Collection)
    - B) libbpf
    - C) bpftrace
    - D) libpcap

    <details>
    <summary>回答を表示</summary>
    <p><strong>回答</strong>: D) libpcap</p>
    <p><strong>解説</strong>: libpcap は packet capture library であり、eBPF program development の framework ではありません。BCC、libbpf、bpftrace はすべて eBPF プログラムを開発するための framework です。</p>
    </details>

13. **eBPF map の type ではないものはどれですか？**
    - A) Hash Map
    - B) Array Map
    - C) LRU Map
    - D) Graph Map

    <details>
    <summary>回答を表示</summary>
    <p><strong>回答</strong>: D) Graph Map</p>
    <p><strong>解説</strong>: eBPF は hash map、array map、LRU map を含むさまざまな type の map をサポートしていますが、graph map はサポートしていません。</p>
    </details>

14. **eBPF プログラム内の instruction の最大数はいくつですか？**
    - A) 1,000
    - B) 4,096
    - C) 10,000
    - D) Unlimited

    <details>
    <summary>回答を表示</summary>
    <p><strong>回答</strong>: B) 4,096</p>
    <p><strong>解説</strong>: eBPF プログラムは最大 4,096 個の instruction に制限されています。これは安全性を確保するための制限です。</p>
    </details>

15. **eBPF プログラムを kernel にロードするために使用される system call は何ですか？**
    - A) bpf()
    - B) ebpf()
    - C) sysfs()
    - D) ioctl()

    <details>
    <summary>回答を表示</summary>
    <p><strong>回答</strong>: A) bpf()</p>
    <p><strong>解説</strong>: bpf() system call は、eBPF プログラムを kernel にロードし、eBPF map を作成およびアクセスするために使用されます。</p>
    </details>

## eBPF のパフォーマンスとモニタリング

16. **XDP (eXpress Data Path) が提供する主な利点は何ですか？**
    - A) より優れた security
    - B) より簡単な programming
    - C) より低い latency
    - D) より高い compatibility

    <details>
    <summary>回答を表示</summary>
    <p><strong>回答</strong>: C) より低い latency</p>
    <p><strong>解説</strong>: XDP は network driver level で packet を処理し、kernel networking stack をバイパスして非常に低い latency を実現します。</p>
    </details>

17. **Cilium で eBPF プログラムの performance をモニタリングするために使用される tool は何ですか？**
    - A) top
    - B) bpftool
    - C) htop
    - D) iotop

    <details>
    <summary>回答を表示</summary>
    <p><strong>回答</strong>: B) bpftool</p>
    <p><strong>解説</strong>: bpftool は eBPF プログラムと map の検査および管理に使用される tool であり、performance monitoring にも使用されます。</p>
    </details>

18. **Cilium の eBPF ベースの network monitoring tool は何ですか？**
    - A) Prometheus
    - B) Hubble
    - C) Grafana
    - D) Jaeger

    <details>
    <summary>回答を表示</summary>
    <p><strong>回答</strong>: B) Hubble</p>
    <p><strong>解説</strong>: Hubble は、network flow を real-time で観測および分析できる Cilium の eBPF ベースの network monitoring tool です。</p>
    </details>

19. **eBPF プログラムの performance bottleneck を見つけるために使用される tool は何ですか？**
    - A) strace
    - B) ltrace
    - C) perf
    - D) gdb

    <details>
    <summary>回答を表示</summary>
    <p><strong>回答</strong>: C) perf</p>
    <p><strong>解説</strong>: perf は、eBPF プログラムの performance bottleneck を見つけるために使用される Linux performance analysis tool です。</p>
    </details>

20. **Cilium で eBPF プログラムを debugging するために使用される command は何ですか？**
    - A) `cilium bpf`
    - B) `cilium debug`
    - C) `cilium monitor`
    - D) `cilium trace`

    <details>
    <summary>回答を表示</summary>
    <p><strong>回答</strong>: A) `cilium bpf`</p>
    <p><strong>解説</strong>: `cilium bpf` command は、Cilium の eBPF プログラムと map を検査および debugging するために使用されます。</p>
    </details>
