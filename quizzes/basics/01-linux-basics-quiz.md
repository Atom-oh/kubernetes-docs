# Linux 기초 퀴즈

이 퀴즈는 Kubernetes와 컨테이너 기술의 기반이 되는 Linux 기초 개념에 대한 이해도를 테스트합니다.

## 객관식 문제

1. Linux 커널의 주요 역할이 아닌 것은 무엇인가요?
   - A) 프로세스 관리
   - B) 메모리 관리
   - C) 사용자 인터페이스 제공
   - D) 장치 관리
   
   [정답 확인하기](../../answers/basics/01-linux-basics-answers.md#객관식-문제-1)

2. 다음 중 Linux 네임스페이스의 종류가 아닌 것은 무엇인가요?
   - A) PID 네임스페이스
   - B) 네트워크 네임스페이스
   - C) 메모리 네임스페이스
   - D) 사용자 네임스페이스
   
   [정답 확인하기](../../answers/basics/01-linux-basics-answers.md#객관식-문제-2)

3. cgroups(Control Groups)의 주요 기능은 무엇인가요?
   - A) 프로세스 그룹의 자원 사용 제한 및 격리
   - B) 파일 시스템 접근 제어
   - C) 네트워크 패킷 필터링
   - D) 사용자 인증 관리
   
   [정답 확인하기](../../answers/basics/01-linux-basics-answers.md#객관식-문제-3)

4. 파일 권한 "rwxr-xr--"에서 그룹 사용자의 권한은 무엇인가요?
   - A) 읽기, 쓰기, 실행
   - B) 읽기, 실행
   - C) 읽기만
   - D) 실행만
   
   [정답 확인하기](../../answers/basics/01-linux-basics-answers.md#객관식-문제-4)

5. 컨테이너 이미지 레이어를 구현하는 데 주로 사용되는 파일 시스템은 무엇인가요?
   - A) ext4
   - B) XFS
   - C) OverlayFS
   - D) Btrfs
   
   [정답 확인하기](../../answers/basics/01-linux-basics-answers.md#객관식-문제-5)

## 단답형 문제

6. 프로세스가 종료되었지만 부모 프로세스가 상태를 확인하지 않은 상태의 프로세스를 무엇이라고 하나요?

   [정답 확인하기](../../answers/basics/01-linux-basics-answers.md#단답형-문제-6)

7. 프로세스의 네트워크 스택을 격리하는 Linux 네임스페이스의 이름은 무엇인가요?

   [정답 확인하기](../../answers/basics/01-linux-basics-answers.md#단답형-문제-7)

8. Linux에서 프로세스가 사용할 수 있는 시스템 호출을 제한하는 보안 기능의 이름은 무엇인가요?

   [정답 확인하기](../../answers/basics/01-linux-basics-answers.md#단답형-문제-8)

9. Linux에서 전통적인 root 권한을 더 작은 권한 단위로 나눈 것을 무엇이라고 하나요?

   [정답 확인하기](../../answers/basics/01-linux-basics-answers.md#단답형-문제-9)

10. 컨테이너 네트워킹에서 호스트와 컨테이너 간의 네트워크 인터페이스 쌍을 무엇이라고 하나요?

    [정답 확인하기](../../answers/basics/01-linux-basics-answers.md#단답형-문제-10)

## 실습 문제

11. 새로운 네트워크 네임스페이스를 생성하고, 해당 네임스페이스 내에서 네트워크 인터페이스 목록을 확인하는 명령어를 작성하세요.

    [정답 확인하기](../../answers/basics/01-linux-basics-answers.md#실습-문제-11)

12. 특정 프로세스(PID: 1234)의 cgroup 정보를 확인하는 명령어를 작성하세요.

    [정답 확인하기](../../answers/basics/01-linux-basics-answers.md#실습-문제-12)

13. 파일 "example.sh"에 소유자에게는 읽기, 쓰기, 실행 권한을, 그룹에게는 읽기와 실행 권한을, 다른 사용자에게는 읽기 권한만 부여하는 chmod 명령어를 작성하세요.

    [정답 확인하기](../../answers/basics/01-linux-basics-answers.md#실습-문제-13)

14. 시스템의 현재 메모리 사용량을 확인하는 명령어를 작성하세요.

    [정답 확인하기](../../answers/basics/01-linux-basics-answers.md#실습-문제-14)

15. 특정 포트(예: 8080)에서 실행 중인 프로세스를 찾는 명령어를 작성하세요.

    [정답 확인하기](../../answers/basics/01-linux-basics-answers.md#실습-문제-15)

## 심화 문제

16. Linux 커널에서 컨테이너 격리를 위해 사용되는 주요 기술 3가지를 설명하고, 각각이 어떤 종류의 격리를 제공하는지 설명하세요.

    [정답 확인하기](../../answers/basics/01-linux-basics-answers.md#심화-문제-16)

17. OverlayFS가 컨테이너 이미지 레이어를 관리하는 방식을 설명하고, 읽기 전용 레이어와 쓰기 가능 레이어의 관계를 설명하세요.

    [정답 확인하기](../../answers/basics/01-linux-basics-answers.md#심화-문제-17)

18. Linux 기능(capabilities)이 컨테이너 보안에 어떤 영향을 미치는지 설명하고, 컨테이너에 필요한 최소한의 기능만 부여하는 것이 왜 중요한지 설명하세요.

    [정답 확인하기](../../answers/basics/01-linux-basics-answers.md#심화-문제-18)

---

[학습 자료로 돌아가기](../../basics/01-linux-basics.md) | [다음 퀴즈: 컨테이너 기술](./02-container-technology-quiz.md)
