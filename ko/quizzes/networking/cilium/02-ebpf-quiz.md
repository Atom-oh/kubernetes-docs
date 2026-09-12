# Cilium eBPF 퀴즈

> **검토 기준**: Cilium 1.20.1; Linux 5.10+ 또는 문서화된 동등 백포트; 한도 예제는 Linux 6.12.
> **2026-09-12**


## eBPF 기본 개념

1. **eBPF는 무엇의 약자인가요?**
   - A) Extended Berkeley Packet Filter
   - B) Enhanced Berkeley Process Filter
   - C) Extended Binary Processing Framework
   - D) Enhanced Backend Processing Function

   <details>
   <summary>정답 보기</summary>
   <p><strong>정답</strong>: A) Extended Berkeley Packet Filter</p>
   <p><strong>설명</strong>: eBPF는 Extended Berkeley Packet Filter의 약자로, 원래의 BPF를 확장한 기술입니다.</p>
   </details>

2. **이 가이드의 Linux eBPF 프로그램은 훅 호출 시 어디서 실행되나요?**
   - A) 사용자 공간에서만
   - B) 커널 내부
   - C) Hubble Relay 내부
   - D) 컨테이너 런타임 프로세스 내부

   <details>
   <summary>정답 보기</summary>

   **정답: B) 커널 내부**

   이 프로그램은 커널이 지원하는 인터프리터 또는 JIT 경로에서 실행합니다. 로더와 관측 프로그램은 사용자 공간에 있습니다. 커널 실행이 절대적인 안전 보장은 아닙니다.

   </details>

3. **BPF 검증기의 허용은 무엇을 의미하나요?**
   - A) 커널 장애가 불가능함
   - B) 의도한 애플리케이션 정책의 정확성이 증명됨
   - C) 타입·메모리 접근·실행 제약 검사를 통과함
   - D) 추가 테스트가 필요 없음

   <details>
   <summary>정답 보기</summary>

   **정답: C) 타입·메모리 접근·실행 제약 검사를 통과함**

   검증기는 실행을 제한하지만 검증기·JIT·헬퍼·커널 버그나 잘못된 프로그램 로직 가능성은 남습니다.

   </details>

4. **eBPF 프로그램이 연결될 수 있는 커널 이벤트를 무엇이라고 부르나요?**
   - A) 트리거
   - B) 훅(Hook)
   - C) 이벤트 리스너
   - D) 콜백

   <details>
   <summary>정답 보기</summary>
   <p><strong>정답</strong>: B) 훅(Hook)</p>
   <p><strong>설명</strong>: eBPF 프로그램은 커널의 다양한 훅(Hook) 지점에 연결되어 이벤트가 발생할 때 실행됩니다.</p>
   </details>

5. **BPF 프로그램과 사용자 공간 사이에 상태·이벤트를 공유하는 메커니즘은 무엇인가요?**
   - A) 환경 변수
   - B) 일반 디스크 파일만
   - C) BPF 맵
   - D) Kubernetes annotation

   <details>
   <summary>정답 보기</summary>

   **정답: C) BPF 맵**

   맵에는 키·값 구조, 이벤트 버퍼, 참조 컨테이너 등이 있습니다. Pin은 참조를 유지할 뿐 재부팅 후 내용을 보존하지 않으며 재로드 시 자동 재사용되지 않습니다.

   </details>

## eBPF와 Cilium

6. **eBPF가 Cilium 데이터플레인 구현에 도움이 되는 이유는 무엇인가요?**
   - A) 변경마다 새 커스텀 모듈을 만들지 않아도 커널 훅·맵을 프로그래밍할 수 있음
   - B) 모든 커널 모듈 의존성을 제거함
   - C) 모든 클라우드 네트워크를 자동 구성함
   - D) 메모리 사용 감소를 보장함

   <details>
   <summary>정답 보기</summary>

   **정답: A) 변경마다 새 커스텀 모듈을 만들지 않아도 커널 훅·맵을 프로그래밍할 수 있음**

   Cilium은 지원 커널 기능으로 전달, 정책, 서비스 변환을 구현합니다. 필요한 커널 기능과 워크로드별 검증은 여전히 필요합니다.

   </details>

7. **Cilium의 WireGuard/IPsec 암호화 모드 설명으로 맞는 것은 무엇인가요?**
   - A) 모든 암호 연산이 BPF 명령어임
   - B) 설정·키 운영이 필요 없음
   - C) 항상 모든 트래픽 경로를 암호화함
   - D) BPF가 커널 WireGuard/IPsec 시설과 트래픽을 통합하며 범위·키 관리는 모드에 따름

   <details>
   <summary>정답 보기</summary>

   **정답: D) BPF가 커널 WireGuard/IPsec 시설과 트래픽을 통합하며 범위·키 관리는 모드에 따름**

   BPF 유도와 커널 암호화는 다른 역할입니다. 노드 암호화가 workload mTLS를 자동 활성화하지 않습니다.

   </details>

8. **Cilium은 kube-proxy 대체에 어떤 훅을 사용할 수 있나요?**
   - A) XDP만
   - B) TC만
   - C) 추적 probe만
   - D) 소켓 훅, TC 패킷 경로, 선택적 XDP 가속

   <details>
   <summary>정답 보기</summary>

   **정답: D) 소켓 훅, TC 패킷 경로, 선택적 XDP 가속**

   트래픽·설정에 따라 경로가 다릅니다. 서비스 변환은 패킷 생성 전 소켓 훅, 패킷 경로 또는 지원되는 XDP 가속에서 수행할 수 있습니다.

   </details>

9. **어떤 Cilium 설정이 더 빠르다는 주장은 어떻게 평가하나요?**
   - A) 모든 BPF 맵 조회 지연이 보장된다고 가정
   - B) 프로토콜·라우팅·정책·암호화·프록시 설정을 기록하고 워크로드 측정
   - C) 커널 실행만으로 증명되었다고 간주
   - D) 제품 이름만 비교

   <details>
   <summary>정답 보기</summary>

   **정답: B) 프로토콜·라우팅·정책·암호화·프록시 설정을 기록하고 워크로드 측정**

   커널과 사용자 공간 구성 요소 모두 워크로드에 따른 비용이 있습니다. 합성 결과와 훅 선택이 애플리케이션 지연을 보장하지 않습니다.

   </details>

10. **Hubble HTTP 관측은 어디서 얻을 수 있나요?**
    - A) 임의의 트래픽을 자동 해독하여
    - B) CPU 하드웨어 카운터에서만
    - C) 지원되는 L7 프록시 경로와 네트워크 플로우 정보를 조합하여
    - D) 설정과 무관하게 모든 패킷에서

    <details>
    <summary>정답 보기</summary>

    **정답: C) 지원되는 L7 프록시 경로와 네트워크 플로우 정보를 조합하여**

    L7 가시성은 프록시·정책·가시성 설정에 따릅니다. 플로우가 자동으로 애플리케이션 span이나 임의의 업무 메트릭이 되지는 않습니다.

    </details>

## eBPF 프로그래밍

11. **컴파일러·도구 설명으로 맞는 것은 무엇인가요?**
    - A) Clang이 C와 Rust 소스를 모두 직접 컴파일함
    - B) C는 흔히 Clang BPF 백엔드, Rust는 자체 도구 생태계를 사용함
    - C) 호스트 C 문법 검사로 커널 검증 통과가 증명됨
    - D) BTF가 없는 커널 기능을 제공함

    <details>
    <summary>정답 보기</summary>

    **정답: B) C는 흔히 Clang BPF 백엔드, Rust는 자체 도구 생태계를 사용함**

    호스트 문법, BPF 대상 컴파일, 커널 검증, 실제 동작은 별도 검사입니다. CO-RE가 없는 헬퍼나 설정을 만들지는 않습니다.

    </details>

12. **eBPF 프로그램 개발을 위한 프레임워크가 아닌 것은?**
    - A) BCC(BPF Compiler Collection)
    - B) libbpf
    - C) bpftrace
    - D) libpcap

    <details>
    <summary>정답 보기</summary>
    <p><strong>정답</strong>: D) libpcap</p>
    <p><strong>설명</strong>: libpcap은 패킷 캡처 라이브러리로, eBPF 프로그램 개발을 위한 프레임워크가 아닙니다. BCC, libbpf, bpftrace는 모두 eBPF 프로그램 개발을 위한 프레임워크입니다.</p>
    </details>

13. **eBPF 맵의 유형이 아닌 것은?**
    - A) 해시 맵(Hash Map)
    - B) 배열 맵(Array Map)
    - C) LRU 맵(LRU Map)
    - D) 그래프 맵(Graph Map)

    <details>
    <summary>정답 보기</summary>
    <p><strong>정답</strong>: D) 그래프 맵(Graph Map)</p>
    <p><strong>설명</strong>: eBPF는 해시 맵, 배열 맵, LRU 맵 등 다양한 유형의 맵을 지원하지만, 그래프 맵은 지원하지 않습니다.</p>
    </details>

14. **가이드에서 설명한 Linux 6.12 한도와 맞는 것은 무엇인가요?**
    - A) 모든 프로그램의 한도가 4,096개 명령어임
    - B) 100만 개 미만이면 모두 허용함
    - C) 프로그램·분석 한도가 없음
    - D) BPF 권한이 있는 로드 경로는 최대 100만 개, 비특권 경로는 4,096개이며 검증 복잡도는 별도 한도임

    <details>
    <summary>정답 보기</summary>

    **정답: D) BPF 권한이 있는 로드 경로는 최대 100만 개, 비특권 경로는 4,096개이며 검증 복잡도는 별도 한도임**

    프로그램 길이와 검증기 탐색은 다른 제약입니다. Capability/token, 타입 등 다른 검사도 적용되며 비특권 BPF는 비활성화된 경우가 많습니다.

    </details>

15. **eBPF 프로그램을 커널에 로드하는 데 사용되는 시스템 콜은?**
    - A) bpf()
    - B) ebpf()
    - C) sysfs()
    - D) ioctl()

    <details>
    <summary>정답 보기</summary>
    <p><strong>정답</strong>: A) bpf()</p>
    <p><strong>설명</strong>: bpf() 시스템 콜은 eBPF 프로그램을 커널에 로드하고, eBPF 맵을 생성하고 액세스하는 데 사용됩니다.</p>
    </details>

## eBPF 성능 및 모니터링

16. **Native driver XDP와 후단 skb 처리의 차이는 무엇인가요?**
    - A) 항상 모든 커널 하위 시스템을 우회함
    - B) 고정 패킷 처리량을 보장함
    - C) skb 할당 전에 패킷을 처리할 수 있음
    - D) 모든 NIC와 generic 모드에서 동일하게 동작함

    <details>
    <summary>정답 보기</summary>

    **정답: C) skb 할당 전에 패킷을 처리할 수 있음**

    Native XDP는 수신 처리 초기입니다. Generic/offload 모드와 드라이버 지원은 다르며 실제 성능을 측정해야 합니다.

    </details>

17. **설명과 맞는 bpftool 명령은 무엇인가요?**
    - A) bpftool -p map dump가 조회 지연 측정
    - B) bpftool prog profile id ID duration 10 cycles instructions가 profiling 메트릭 요청
    - C) bpftool prog load가 항상 tracepoint 연결
    - D) bpftool prog show가 없는 커널 기능 활성화

    <details>
    <summary>정답 보기</summary>

    **정답: B) bpftool prog profile id ID duration 10 cycles instructions가 profiling 메트릭 요청**

    Profiling에는 metric 이름, 권한, 커널·PMU 지원이 필요합니다. 보기 좋은 출력, 로드, 연결은 다른 동작입니다.

    </details>

18. **여기서 Hubble은 무엇인가요?**
    - A) 커널 컴파일러
    - B) 모든 애플리케이션 추적 SDK 대체재
    - C) 데이터플레인과 제공되는 프록시 이벤트를 사용하는 Cilium 네트워크 관측 시스템
    - D) 자동 정책 동기화 도구

    <details>
    <summary>정답 보기</summary>

    **정답: C) 데이터플레인과 제공되는 프록시 이벤트를 사용하는 Cilium 네트워크 관측 시스템**

    Hubble은 플로우와 지원 L7 이벤트를 관찰합니다. 수집 한계·필터가 결과에 영향을 주며 JSON만으로 서비스 맵 시각화가 만들어지지 않습니다.

    </details>

19. **맵 기반 실습은 무엇을 집계하나요?**
    - A) 고유 실행 파일 경로별 모든 execve 시도를 무손실 집계
    - B) 짧은 comm별 성공 실행 이벤트를 용량·측정 한도 내에서 집계
    - C) default namespace의 Pod만
    - D) 이전의 모든 재부팅을 포함한 프로세스 전체

    <details>
    <summary>정답 보기</summary>

    **정답: B) 짧은 comm별 성공 실행 이벤트를 용량·측정 한도 내에서 집계**

    sched_process_exec는 성공한 실행 전환을 관찰합니다. 이름이 충돌할 수 있고 호스트 전체 예제는 제한된 메모리 상태와 일부 유실 카운터를 사용합니다.

    </details>

20. **에이전트 로컬에서 서비스 백엔드 맵을 확인하는 명령은 무엇인가요?**
    - A) cilium-dbg bpf lb list --backends
    - B) cilium debug --all-kernels
    - C) cilium policy trace --enable
    - D) hubble compile bpf

    <details>
    <summary>정답 보기</summary>

    **정답: A) cilium-dbg bpf lb list --backends**

    올바른 노드의 에이전트에서 cilium-dbg를 사용합니다. cilium-dbg map get은 사용자 공간 캐시이므로 적절한 디코더를 사용하고 원시 맵을 변경하지 않습니다.

    </details>

[본문 복습](../../../networking/cilium/02-ebpf.md).
