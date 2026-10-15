# 종합 실습과 컨테이너·클라우드 퀴즈

[학습 문서](../../../networking/beginner/08-container-cloud-capstone.md)

6문항입니다. 정답뿐 아니라 해설을 자신의 말로 설명하세요.

1. IP 요청은 HTTP 200이지만 서비스 이름의 getent 조회는 실패합니다. 첫 조사 대상은?

   - A) CPU 혼잡 제어 알고리즘
   - B) 이름 해석 경로
   - C) HTTP 파일 권한만
   - D) 모든 CNI 구현

<details>
<summary>정답 보기</summary>

**정답: B) 이름 해석 경로**

**설명:** IP 연결과 애플리케이션 응답이 확인됐으므로 이름을 주소로 찾는 경로를 먼저 조사합니다. 특정 DNS 서버가 원인인지는 추가 근거가 필요합니다.

</details>

2. 서버에서 HTTP 404를 받았습니다. 이 요청에 대해 확인된 사실은?

   - A) 모든 포트가 개방됐다
   - B) 라우팅 테이블이 비어 있다
   - C) HTTP 서버와 응답을 주고받았다
   - D) 인터넷 전체가 정상이다

<details>
<summary>정답 보기</summary>

**정답: C) HTTP 서버와 응답을 주고받았다**

**설명:** 404는 HTTP 계층의 응답입니다. 파일 경로·서버 로그를 대조해야 하며 전체 방화벽 초기화는 근거 없는 변경입니다.

</details>

3. ss에 127.0.0.1:8000 리스너만 있고 서버 로컬 요청은 성공합니다. 원격 실패를 조사할 때 핵심은?

   - A) 리스너가 원격 요청의 목적지 주소에 바인딩됐는지 확인한다
   - B) 클라이언트의 localhost가 서버와 같다고 가정한다
   - C) DNS TTL을 무조건 늘린다
   - D) SELinux를 끈다

<details>
<summary>정답 보기</summary>

**정답: A) 리스너가 원격 요청의 목적지 주소에 바인딩됐는지 확인한다**

**설명:** 루프백은 해당 네트워크 네임스페이스 안의 주소입니다. 서버 실습 IP로 받으려면 그 주소에 바인딩된 리스너와 적절한 접근 규칙이 필요합니다.

</details>

4. UFW의 독립된 TCP 8000 allow만 제거했습니다. 새 키 전용 SSH는 되지만 HTTP는 실패합니다. 의도한 정책을 유지하는 복구는 무엇인가요?

   - A) 남은 실습 deny 뒤에 HTTP allow를 덧붙인다
   - B) 실습 deny와 모든 SSH 규칙을 지운다
   - C) UFW를 끄고 기존 SSH 세션만으로 복구됐다고 판단한다
   - D) 원래 범위의 HTTP allow를 deny 앞에 삽입하고 순서·HTTP 200·새 키 전용 SSH를 확인한다

<details>
<summary>정답 보기</summary>

**정답: D) 원래 범위의 HTTP allow를 deny 앞에 삽입하고 순서·HTTP 200·새 키 전용 SSH를 확인한다**

**설명:** SSH와 HTTP의 allow가 별개이므로 HTTP 장애는 TCP 22와 기본 정책을 그대로 둡니다. UFW에서는 일치하는 deny 뒤에 allow를 덧붙여도 효과가 없으므로 위치도 복원해야 합니다. 장애 전·중·후에 다중화를 끈 새 키 로그인을 시험하고 잠금 해제된 agent를 가정하지 말고 암호화된 키의 암호문구 질문을 허용합니다. firewalld 분기는 runtime HTTP만 제거·복원하며 permanent 규칙은 유지합니다. 제거해도 HTTP가 계속 성공한다면 차단됐다고 주장하지 말고 다른 허용과 zone 동작을 조사합니다.

</details>

5. curl --resolve lesson.test:8000:192.0.2.20은 무엇을 바꾸나요?

   - A) 모든 VM의 DNS 서버
   - B) 해당 curl 실행의 호스트·포트 매핑
   - C) 영구 /etc/hosts 파일
   - D) Kubernetes Service IP

<details>
<summary>정답 보기</summary>

**정답: B) 해당 curl 실행의 호스트·포트 매핑**

**설명:** 이 옵션은 한 curl 실행에 범위를 제한합니다. 시스템 리졸버나 다른 프로그램의 매핑을 수정하지 않습니다.

</details>

6. VM 실습 후 CNI를 배울 때 유지해야 하는 원칙은?

   - A) Docker bridge와 모든 CNI는 같은 구현이다
   - B) Service IP와 localhost는 같다
   - C) 네임스페이스·주소·경로·정책·관측 지점을 다시 식별한다
   - D) 작은 HTTP 요청으로 클라우드 최대 처리량을 증명한다

<details>
<summary>정답 보기</summary>

**정답: C) 네임스페이스·주소·경로·정책·관측 지점을 다시 식별한다**

**설명:** 진단 질문은 재사용할 수 있지만 각 환경의 구현과 경계는 다릅니다. 클러스터 추상화와 실제 패킷 경로를 구분해야 합니다.

</details>
