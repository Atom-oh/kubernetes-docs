# 퀴즈 6. 방화벽과 호스트 보안

> **지원 버전**: Ubuntu Server 24.04 LTS(기본), Rocky Linux 9(대안)
> **마지막 업데이트**: 2026년 9월 15일

[본문과 1차 출처](../../../networking/beginner/06-firewalls-host-security.md) | [과정](../../../networking/beginner/README.md)

클라이언트 `.10`, 서버 `.20`, 별도 관리 NIC, 콘솔 복구 조건을 기준으로 합니다. 해설을 열기 전에 고르세요.

1. 클라이언트가 이 서버로 SSH를 엽니다. 서버 방화벽 관점에서 인바운드·아웃바운드·포워딩 중 무엇인가요?

   - A) 모든 원격 연결이 서버를 라우터로 만드므로 포워딩입니다.
   - B) 서버가 응답하므로 아웃바운드입니다.
   - C) 새 연결은 인바운드입니다. 응답은 그 대화에 속하며 다른 호스트의 트래픽을 전달하는 것은 포워딩입니다.
   - D) SSH는 방화벽을 우회하므로 해당하지 않습니다.

<details>
<summary>정답 보기</summary>

**정답: C**

**설명:** 방향은 관찰하는 호스트와 패킷 경로를 기준으로 합니다. 실습 서버는 라우터가 아니라 목적지입니다. 상태 추적 응답 처리 때문에 새 SSH는 막혀도 기존 연결은 살아 있을 수 있습니다. 이번 실습에 NAT·포워딩 변경은 필요하지 않습니다.

</details>

2. UFW에 이미 넓은 SSH 허용이 있습니다. `.10` 허용 하나만 추가하면 `.10`으로 제한되나요?

   - A) 아닙니다. 넓은 허용이 남으므로 순서·앞선 사용자 규칙을 확인하고 본문의 범위 제한 allow와 같은 끝점의 deny를 사용합니다.
   - B) 그렇습니다. 새 규칙은 이전 규칙을 자동으로 없앱니다.
   - C) 주석에 “secure”가 있으면 그렇습니다.
   - D) firewalld도 켜야 제한됩니다.

<details>
<summary>정답 보기</summary>

**정답: A**

**설명:** 좁은 allow는 추가이며 기존 권한 회수가 아닙니다. 본문은 같은 실습 NIC·목적지·포트에서 클라이언트 allow를 다른 출발지 deny보다 앞에 넣습니다. 사용자 `before.rules`도 결과에 영향을 주므로 실제 소유자와 앞선 처리를 확인해야 합니다. 경쟁 관리자를 둘 쓰면 안전해지기보다 추론이 어려워집니다.

</details>

3. 본문의 UFW 규칙 변경·정리에 관한 올바른 설명은 무엇인가요?

   - A) runtime 전용으로 10분 후 만료됩니다.
   - B) 예전에 기억한 번호로 삭제하면 항상 정확합니다.
   - C) 원래 active였어도 정리할 때 UFW를 꺼야 합니다.
   - D) 저장·적용되므로 성공적으로 추가한 정확한 규칙 내용을 삭제하고 실습 때문에 원래 inactive를 켰을 때만 비활성 상태로 복원합니다.

<details>
<summary>정답 보기</summary>

**정답: D**

**설명:** 이 UFW 절차는 firewalld처럼 규칙별 permanent·runtime을 나누지 않습니다. 위치는 바뀌지만 인터페이스·출발지·목적지·프로토콜·포트가 의도한 규칙을 식별합니다. 최초 활성화에는 관리 접근 확인도 필요합니다. NIC 설정이 그대로라고 모든 인바운드 서비스가 유지되는 것은 아닙니다.

</details>

4. Rocky 실습 인터페이스를 새 빈 firewalld zone으로 옮기는 이유는 무엇인가요?

   - A) zone이 MAC 확인을 대신합니다.
   - B) 기본·기존 zone이 이미 SSH를 넓게 허용할 수 있으므로 관리 NIC를 옮기지 않는 실습 전용 zone에서 의도한 허용을 분명하게 구성합니다.
   - C) 모든 zone은 ICMP와 IPv6를 자동 전부 차단합니다.
   - D) zone을 쓰면 출발지 연결이나 policy를 볼 필요가 없습니다.

<details>
<summary>정답 보기</summary>

**정답: B**

**설명:** 빈 NetworkManager `connection.zone`은 기본 zone을 사용합니다. 기존 서비스, target, 출발지 연결, policy, direct rule이 실제 허용을 바꿀 수 있습니다. 활성 실습 프로필 UUID와 빈 값까지 포함한 원래 zone을 기록하고 관리 프로필은 유지합니다.

</details>

5. `--timeout=600`으로 rich rule을 추가했습니다. reload하면 어떻게 되나요?

   - A) runtime 전용 규칙은 사라지고 저장 정책을 사용합니다. 인터페이스·zone 연결은 별도 변경입니다.
   - B) timeout이 자동으로 영구 설정이 됩니다.
   - C) 모든 NetworkManager 주소가 지워집니다.
   - D) runtime이 항상 permanent보다 우선하므로 아무 변화가 없습니다.

<details>
<summary>정답 보기</summary>

**정답: A**

**설명:** 시험 규칙은 시간 만료뿐 아니라 reload에도 사라집니다. 저장 규칙에는 명시적 permanent 변경과 runtime 적용이 필요합니다. reload는 다른 runtime 변경도 버릴 수 있으므로 함부로 실행하거나 `--runtime-to-permanent`로 모르는 상태를 모두 저장하지 마세요. 실습 zone이 새 SSH를 허용하지 않게 되면 여전히 콘솔 복구가 필요합니다.

</details>

6. 허용한 클라이언트가 `.20:8000`에서 HTTP 200을 받았습니다. 근거 있는 주장은 무엇인가요?

   - A) 모든 비허용 출발지를 시험했고 거부했습니다.
   - B) 다른 넓은 allow가 있을 수 없습니다.
   - C) 이 시험에서 이 클라이언트가 이 리스닝 서비스에 도달했습니다. 출발지 제한은 정책 검토와 별도로 수행한 거부 시험을 통해 확인해야 합니다.
   - D) SELinux는 모든 프로그램의 모든 파일 읽기를 허용합니다.

<details>
<summary>정답 보기</summary>

**정답: C**

**설명:** 허용 경로 시험의 성공에는 범위가 있습니다. 서버 자기·localhost 요청은 외부 거부 대상 시험이 아닙니다. 리스너, 경로, 인터페이스·zone, 규칙을 비교하고 실제 측정한 것만 보고하세요. 시간이 제한된 Python 서버와 실습 파일은 방화벽 정책과 별개로 종료·정리합니다.

</details>

7. 파일에 의도적으로 잘못된 SELinux type을 지정했습니다. 본문에 맞는 복구는 무엇인가요?

   - A) SELinux를 전역 비활성화합니다.
   - B) 모든 사용자에게 재귀 쓰기 권한을 줍니다.
   - C) 모든 감사 기록에 넓은 허용 정책을 만듭니다.
   - D) 경로의 예상 문맥을 비교하고 `restorecon -n`으로 미리 본 뒤 그 파일의 정책 라벨을 복원하고 `matchpathcon -V`로 확인합니다.

<details>
<summary>정답 보기</summary>

**정답: D**

**설명:** Unix 권한과 SELinux 문맥은 독립 검사입니다. `chcon`은 현재 라벨을 바꾸며 영구 경로 매핑을 만들지 않습니다. `restorecon`은 정책의 파일 문맥 규칙을 사용합니다. 영구 사용자 경로에는 의도적인 `semanage fcontext` 매핑이 필요할 수 있지만 이번 실습 파일에는 필요하지 않습니다.

</details>

8. `ausearch`에 일치 AVC가 없고 Fail2ban 차단 수는 0입니다. 타당한 해석은 무엇인가요?

   - A) 두 도구가 공격 불가능을 증명합니다.
   - B) 조회한 기록·계수가 비어 있습니다. filter, 시간 범위, journal 메타데이터, 권한, 실제 이벤트가 증거 범위를 결정합니다.
   - C) 오류가 나올 때까지 enforcing을 끕니다.
   - D) 0이 아닌 점수를 만들려고 무차별 대입을 반복합니다.

<details>
<summary>정답 보기</summary>

**정답: B**

**설명:** 라벨 실습은 제한된 접근을 의도적으로 유발하지 않으므로 AVC를 보장하지 않습니다. Fail2ban은 정상 대기 중이거나 잘못 설정되었을 수 있습니다. 실제 journal 유닛, backend·filter·action, 시작 로그를 확인하세요. 선택 실습은 무차별 대입을 하지 않으며 실제 집행을 검증했다고 주장하지 않습니다.

</details>

9. Rocky Linux 9에 맞는 선택 패키지 준비는 무엇인가요?

   - A) 원래 상태를 기록하고 배포판 지침에 따라 CRB 준비와 EPEL 9를 활성화한 뒤 후보·서명을 확인하고 필요한 패키지만 설치합니다.
   - B) 서명 검증을 끄고 아무 EPEL 주 버전이나 사용합니다.
   - C) DNF가 의존성을 해결하지 못하면 Ubuntu 패키지를 설치합니다.
   - D) 다른 패키지에 필요해도 설치 후 기존 CRB·EPEL을 끕니다.

<details>
<summary>정답 보기</summary>

**정답: A**

**설명:** EPEL은 선택 소프트웨어, CRB는 의존성을 제공합니다. 맞는 EL 주 버전, 저장소 정체, 게스트 아키텍처가 중요합니다. 같은 준비가 7장의 선택 `iftop`도 지원합니다. 저장소 비활성화로 패키지가 되돌아가지는 않으므로 선택 설치 전체 복구에는 기록한 스냅샷을 사용합니다.

</details>

10. 실습 경계에 맞는 Fail2ban 구성·정리는 무엇인가요?

   - A) `backend=systemd`에 추측한 `/var/log/auth.log`를 더하고 모든 차단을 flush합니다.
   - B) 아무 기존 운영 jail이나 재사용하고 확인 없이 정지합니다.
   - C) 전용 journal SSH jail과 실습 한정 action을 검증하고 상태를 읽은 뒤 나열된 실습 주소만 unban하고 그 jail을 정지·소유 파일 두 개를 삭제한 다음 방화벽 zone을 정리합니다.
   - D) 서비스 active만으로 filter와 방화벽 action이 작동한다고 가정합니다.

<details>
<summary>정답 보기</summary>

**정답: C**

**설명:** journal backend는 `logpath`가 아니라 `journalmatch`를 사용합니다. action은 실습 allow보다 먼저 적용되고 실습 인터페이스·zone, `.20`, TCP 22에 제한되어야 합니다. 해석한 설정과 action 확장을 확인하세요. 정확한 실수 차단만 복원하고 zone 삭제 전에 jail을 정지합니다. 관련 없는 방화벽 상태를 flush하지 않습니다. 추가 증거가 없다면 실제 공격 탐지가 아니라 설정·시작 확인으로 보고합니다.

</details>

[본문으로](../../../networking/beginner/06-firewalls-host-security.md) | [다음: 모니터링](../../../networking/beginner/07-monitoring-performance.md)
