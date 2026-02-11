# Linux 운영 기술 퀴즈

이 퀴즈는 Kubernetes 환경에서 활용되는 Linux 운영 기술에 대한 이해도를 테스트합니다.

## 객관식 문제

1. 환경 변수를 자식 프로세스에서 사용할 수 있도록 하는 명령어는?
   - A) set
   - B) export
   - C) declare
   - D) env

<details>
<summary>정답 보기</summary>

**정답: B) export**

</details>

2. `.bashrc`는 언제 실행되나요?
   - A) 로그인 쉘에서만
   - B) 모든 쉘 세션에서
   - C) 비로그인 대화형 쉘에서
   - D) 항상 .bash_profile과 동시에

<details>
<summary>정답 보기</summary>

**정답: C) 비로그인 대화형 쉘에서**

</details>

3. `${REPLICAS:-3}`의 의미는?
   - A) REPLICAS를 3으로 설정
   - B) REPLICAS가 없으면 3을 사용
   - C) REPLICAS에서 3을 뺌
   - D) 에러 발생

<details>
<summary>정답 보기</summary>

**정답: B) REPLICAS가 없으면 3을 사용**

</details>

4. `awk 'NR>1 {print $1}'`의 의미는?
   - A) 모든 줄의 첫 번째 필드 출력
   - B) 첫 번째 줄만 출력
   - C) 첫 번째 줄 제외하고 첫 번째 필드 출력
   - D) 첫 번째 필드가 있는 줄만 출력

<details>
<summary>정답 보기</summary>

**정답: C) 첫 번째 줄 제외하고 첫 번째 필드 출력**

</details>

5. `sed -i 's/old/new/g'`에서 `g`의 역할은?
   - A) 대소문자 무시
   - B) 줄의 모든 일치 항목 치환
   - C) 한 번만 치환
   - D) 정규표현식 사용

<details>
<summary>정답 보기</summary>

**정답: B) 줄의 모든 일치 항목 치환**

</details>

6. `jq -r`에서 `-r`의 역할은?
   - A) 재귀 검색
   - B) 역순 출력
   - C) 따옴표 없이 raw 문자열 출력
   - D) 읽기 전용

<details>
<summary>정답 보기</summary>

**정답: C) 따옴표 없이 raw 문자열 출력**

</details>

7. `ssh -L 8080:localhost:80 user@server`의 의미는?
   - A) 서버 8080을 로컬 80으로
   - B) 로컬 8080을 서버 80으로
   - C) 서버 80을 로컬 8080으로
   - D) 로컬 80을 서버 8080으로

<details>
<summary>정답 보기</summary>

**정답: B) 로컬 8080을 서버 80으로**

</details>

8. vmstat의 `wa`는 무엇인가요?
   - A) 웹 애플리케이션 CPU
   - B) I/O 대기 시간 비율
   - C) 경고 횟수
   - D) 활성 프로세스 수

<details>
<summary>정답 보기</summary>

**정답: B) I/O 대기 시간 비율**

</details>

9. LVM Physical Volume 생성 명령어는?
   - A) lvcreate
   - B) vgcreate
   - C) pvcreate
   - D) fscreate

<details>
<summary>정답 보기</summary>

**정답: C) pvcreate**

</details>

10. `curl -s -o /dev/null -w "%{http_code}" URL`의 출력은?
    - A) 응답 본문
    - B) 응답 헤더
    - C) HTTP 상태 코드
    - D) 응답 시간

<details>
<summary>정답 보기</summary>

**정답: C) HTTP 상태 코드**

</details>

## 단답형 문제

11. 파일 내용을 현재 쉘에서 실행하는 명령어는?

<details>
<summary>정답 보기</summary>

**정답: source (또는 .)**

</details>

12. JSON 파싱 도구는?

<details>
<summary>정답 보기</summary>

**정답: jq**

</details>

13. bastion 경유 SSH 옵션은?

<details>
<summary>정답 보기</summary>

**정답: ProxyJump (또는 -J)**

</details>

14. 디스크 I/O 모니터링 명령어는?

<details>
<summary>정답 보기</summary>

**정답: iostat**

</details>

15. Pod 서비스 계정 토큰 경로는?

<details>
<summary>정답 보기</summary>

**정답: /var/run/secrets/kubernetes.io/serviceaccount/token**

</details>

## 실습 문제

16. DATABASE_URL 필수, TIMEOUT 기본값 30인 스크립트를 작성하세요.

<details>
<summary>정답 보기</summary>

```bash
#!/bin/bash
: ${DATABASE_URL:?"DATABASE_URL required"}
TIMEOUT=${TIMEOUT:-30}
```

</details>

17. 재시작 3회 이상 Pod를 JSON으로 출력하는 명령을 작성하세요.

<details>
<summary>정답 보기</summary>

```bash
kubectl get pods -A -o json | jq '[.items[] | select([.status.containerStatuses[]?.restartCount] | add >= 3)]'
```

</details>

18. bastion 경유 rsync로 yaml 파일만 동기화하는 명령을 작성하세요.

<details>
<summary>정답 보기</summary>

```bash
rsync -avzP --include='*.yaml' --exclude='*' -e "ssh -J bastion" /src/ user@host:/dest/
```

</details>

## 심화 문제

19. 노드 진단 스크립트를 작성하세요.

<details>
<summary>정답 보기</summary>

```bash
#!/bin/bash
echo "=== System ===" && uptime && free -h && df -h
echo "=== kubelet ===" && systemctl status kubelet --no-pager
```

</details>

20. ConfigMap 환경 변수 vs 볼륨 마운트 차이를 설명하세요.

<details>
<summary>정답 보기</summary>

- 환경 변수: Pod 시작 시 로드, 변경 시 재시작 필요
- 볼륨 마운트: 자동 업데이트 (~1분), 재시작 불필요

</details>

---

[학습 자료로 돌아가기](../../basics/02-linux-advanced.md)
