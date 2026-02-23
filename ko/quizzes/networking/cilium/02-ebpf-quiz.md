# Cilium eBPF 퀴즈

> **지원 버전**: Cilium 1.17, Linux 커널 4.19+  
> **마지막 업데이트**: 2026년 2월 22일

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

2. **eBPF 프로그램이 실행되는 위치는 어디인가요?**
   - A) 사용자 공간(User Space)
   - B) 커널 공간(Kernel Space)
   - C) 하이퍼바이저
   - D) 컨테이너 런타임
   
   <details>
   <summary>정답 보기</summary>
   <p><strong>정답</strong>: B) 커널 공간(Kernel Space)</p>
   <p><strong>설명</strong>: eBPF 프로그램은 Linux 커널 내부에서 안전하게 실행됩니다.</p>
   </details>

3. **eBPF 프로그램의 안전성을 보장하는 메커니즘은 무엇인가요?**
   - A) 샌드박스
   - B) 가상 머신
   - C) 정적 검증기(Verifier)
   - D) 컨테이너화
   
   <details>
   <summary>정답 보기</summary>
   <p><strong>정답</strong>: C) 정적 검증기(Verifier)</p>
   <p><strong>설명</strong>: eBPF 검증기는 프로그램이 로드되기 전에 안전성을 검사하여 무한 루프나 커널 충돌을 방지합니다.</p>
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

5. **eBPF 프로그램과 사용자 공간 애플리케이션 간의 데이터 공유에 사용되는 것은?**
   - A) 공유 메모리
   - B) 파이프
   - C) BPF 맵(Maps)
   - D) 소켓
   
   <details>
   <summary>정답 보기</summary>
   <p><strong>정답</strong>: C) BPF 맵(Maps)</p>
   <p><strong>설명</strong>: BPF 맵은 eBPF 프로그램과 사용자 공간 애플리케이션 간에 데이터를 공유하는 데 사용되는 키-값 저장소입니다.</p>
   </details>

## eBPF와 Cilium

6. **Cilium이 eBPF를 사용하는 주요 이유는 무엇인가요?**
   - A) 커널 모듈 없이 네트워킹 기능 구현
   - B) 더 나은 사용자 인터페이스 제공
   - C) 더 적은 메모리 사용
   - D) 더 쉬운 설치 과정
   
   <details>
   <summary>정답 보기</summary>
   <p><strong>정답</strong>: A) 커널 모듈 없이 네트워킹 기능 구현</p>
   <p><strong>설명</strong>: Cilium은 eBPF를 사용하여 커널 모듈 없이도 고성능 네트워킹, 로드 밸런싱, 보안 정책 등의 기능을 구현할 수 있습니다.</p>
   </details>

7. **Cilium에서 eBPF를 사용하여 구현하는 기능이 아닌 것은?**
   - A) 네트워크 정책 적용
   - B) 서비스 로드 밸런싱
   - C) 네트워크 패킷 암호화
   - D) 사용자 인증
   
   <details>
   <summary>정답 보기</summary>
   <p><strong>정답</strong>: D) 사용자 인증</p>
   <p><strong>설명</strong>: Cilium은 eBPF를 사용하여 네트워크 정책 적용, 서비스 로드 밸런싱, 네트워크 패킷 처리 등을 구현하지만, 사용자 인증은 일반적으로 다른 시스템에서 처리합니다.</p>
   </details>

8. **Cilium에서 kube-proxy를 대체하기 위해 사용하는 eBPF 기능은?**
   - A) XDP(eXpress Data Path)
   - B) TC(Traffic Control) BPF
   - C) 소켓 BPF
   - D) 트레이싱 BPF
   
   <details>
   <summary>정답 보기</summary>
   <p><strong>정답</strong>: B) TC(Traffic Control) BPF</p>
   <p><strong>설명</strong>: Cilium은 주로 TC(Traffic Control) BPF 프로그램을 사용하여 kube-proxy의 서비스 로드 밸런싱 기능을 대체합니다.</p>
   </details>

9. **Cilium의 eBPF 기반 로드 밸런싱이 kube-proxy보다 우수한 이유는?**
   - A) 더 많은 서비스 유형 지원
   - B) 더 나은 사용자 인터페이스
   - C) 더 낮은 지연 시간과 더 높은 처리량
   - D) 더 쉬운 설정
   
   <details>
   <summary>정답 보기</summary>
   <p><strong>정답</strong>: C) 더 낮은 지연 시간과 더 높은 처리량</p>
   <p><strong>설명</strong>: Cilium의 eBPF 기반 로드 밸런싱은 커널 공간에서 직접 패킷을 처리하여 더 낮은 지연 시간과 더 높은 처리량을 제공합니다.</p>
   </details>

10. **Cilium에서 eBPF를 사용하여 수집하는 메트릭이 아닌 것은?**
    - A) 네트워크 연결 상태
    - B) 패킷 드롭 이유
    - C) 서비스 응답 시간
    - D) 사용자 로그인 시간
    
    <details>
    <summary>정답 보기</summary>
    <p><strong>정답</strong>: D) 사용자 로그인 시간</p>
    <p><strong>설명</strong>: Cilium은 eBPF를 사용하여 네트워크 연결 상태, 패킷 드롭 이유, 서비스 응답 시간 등의 네트워크 관련 메트릭을 수집하지만, 사용자 로그인 시간과 같은 애플리케이션 수준의 메트릭은 수집하지 않습니다.</p>
    </details>

## eBPF 프로그래밍

11. **eBPF 프로그램을 작성하는 데 주로 사용되는 언어는?**
    - A) Python
    - B) Go
    - C) C
    - D) Rust
    
    <details>
    <summary>정답 보기</summary>
    <p><strong>정답</strong>: C) C</p>
    <p><strong>설명</strong>: eBPF 프로그램은 주로 C 언어로 작성되며, LLVM 컴파일러를 사용하여 eBPF 바이트코드로 컴파일됩니다.</p>
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

14. **eBPF 프로그램의 최대 명령어 수는?**
    - A) 1,000개
    - B) 4,096개
    - C) 10,000개
    - D) 무제한
    
    <details>
    <summary>정답 보기</summary>
    <p><strong>정답</strong>: B) 4,096개</p>
    <p><strong>설명</strong>: eBPF 프로그램은 최대 4,096개의 명령어로 제한됩니다. 이는 안전성을 보장하기 위한 제한입니다.</p>
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

16. **XDP(eXpress Data Path)가 제공하는 주요 이점은?**
    - A) 더 나은 보안
    - B) 더 쉬운 프로그래밍
    - C) 더 낮은 지연 시간
    - D) 더 높은 호환성
    
    <details>
    <summary>정답 보기</summary>
    <p><strong>정답</strong>: C) 더 낮은 지연 시간</p>
    <p><strong>설명</strong>: XDP는 네트워크 드라이버 수준에서 패킷을 처리하여 커널 네트워킹 스택을 우회함으로써 매우 낮은 지연 시간을 제공합니다.</p>
    </details>

17. **Cilium에서 eBPF 프로그램의 성능을 모니터링하는 도구는?**
    - A) top
    - B) bpftool
    - C) htop
    - D) iotop
    
    <details>
    <summary>정답 보기</summary>
    <p><strong>정답</strong>: B) bpftool</p>
    <p><strong>설명</strong>: bpftool은 eBPF 프로그램과 맵을 검사하고 관리하는 데 사용되는 도구로, 성능 모니터링에도 활용됩니다.</p>
    </details>

18. **Cilium에서 eBPF 기반 네트워크 모니터링 도구는?**
    - A) Prometheus
    - B) Hubble
    - C) Grafana
    - D) Jaeger
    
    <details>
    <summary>정답 보기</summary>
    <p><strong>정답</strong>: B) Hubble</p>
    <p><strong>설명</strong>: Hubble은 Cilium의 eBPF 기반 네트워크 모니터링 도구로, 네트워크 흐름을 실시간으로 관찰하고 분석할 수 있습니다.</p>
    </details>

19. **eBPF 프로그램의 성능 병목 현상을 찾는 데 사용되는 도구는?**
    - A) strace
    - B) ltrace
    - C) perf
    - D) gdb
    
    <details>
    <summary>정답 보기</summary>
    <p><strong>정답</strong>: C) perf</p>
    <p><strong>설명</strong>: perf는 Linux 성능 분석 도구로, eBPF 프로그램의 성능 병목 현상을 찾는 데 사용됩니다.</p>
    </details>

20. **Cilium에서 eBPF 프로그램의 디버깅에 사용되는 명령어는?**
    - A) `cilium bpf`
    - B) `cilium debug`
    - C) `cilium monitor`
    - D) `cilium trace`
    
    <details>
    <summary>정답 보기</summary>
    <p><strong>정답</strong>: A) `cilium bpf`</p>
    <p><strong>설명</strong>: `cilium bpf` 명령어는 Cilium의 eBPF 프로그램과 맵을 검사하고 디버깅하는 데 사용됩니다.</p>
    </details>
