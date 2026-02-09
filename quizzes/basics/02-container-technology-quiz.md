# 컨테이너 기술 퀴즈

이 퀴즈는 컨테이너 기술의 기본 개념, 작동 원리, 그리고 Kubernetes와의 관계에 대한 이해도를 테스트합니다.

## 객관식 문제

1. 컨테이너의 주요 특징이 아닌 것은 무엇인가요?
   - A) 이식성
   - B) 경량성
   - C) 완전한 하드웨어 가상화
   - D) 격리된 실행 환경
   
<details>

<summary>정답 보기</summary>

**정답: C) 완전한 하드웨어 가상화**

**설명:**
컨테이너는 호스트 OS의 커널을 공유하며 하드웨어를 가상화하지 않습니다. 완전한 하드웨어 가상화는 가상 머신(VM)의 특징입니다. 컨테이너는 이식성, 경량성, 격리된 실행 환경을 제공하지만, 호스트 OS 커널에 의존하여 작동합니다.
</details>

2. 컨테이너와 가상 머신의 주요 차이점으로 올바른 것은 무엇인가요?
   - A) 컨테이너는 각각 독립적인 OS를 필요로 한다
   - B) 가상 머신은 컨테이너보다 시작 시간이 빠르다
   - C) 컨테이너는 호스트 OS 커널을 공유한다
   - D) 가상 머신은 컨테이너보다 더 적은 리소스를 사용한다
   
<details>

<summary>정답 보기</summary>

**정답: C) 컨테이너는 호스트 OS 커널을 공유한다**

**설명:**
컨테이너는 호스트 OS의 커널을 공유하여 작동하는 반면, 가상 머신은 각각 완전한 OS를 포함합니다. 이로 인해 컨테이너는 가상 머신보다 더 가볍고, 시작 시간이 빠르며, 리소스 사용이 효율적입니다.
</details>

3. 다음 중 OCI(Open Container Initiative) 호환 저수준 컨테이너 런타임이 아닌 것은 무엇인가요?
   - A) runc
   - B) crun
   - C) containerd
   - D) gVisor
   
<details>

<summary>정답 보기</summary>

**정답: C) containerd**

**설명:**
containerd는 고수준 컨테이너 런타임으로, 이미지 전송, 스토리지, 컨테이너 실행 관리 등의 기능을 제공합니다. runc, crun, gVisor는 모두 OCI 호환 저수준 컨테이너 런타임으로, 실제 컨테이너 생성 및 실행을 담당합니다.
</details>

4. 컨테이너 이미지 레이어에 대한 설명으로 올바른 것은 무엇인가요?
   - A) 각 레이어는 독립적으로 수정 가능하다
   - B) 레이어는 항상 병합되어 단일 파일로 저장된다
   - C) 레이어는 이전 레이어에 대한 변경사항을 나타낸다
   - D) 모든 컨테이너는 자신만의 고유한 레이어 세트를 가진다
   
<details>

<summary>정답 보기</summary>

**정답: C) 레이어는 이전 레이어에 대한 변경사항을 나타낸다**

**설명:**
컨테이너 이미지는 여러 레이어로 구성되며, 각 레이어는 이전 레이어에 대한 변경사항을 나타냅니다. 이 레이어 방식은 이미지 공유와 캐싱을 효율적으로 만들어 스토리지 공간을 절약하고 이미지 다운로드 속도를 향상시킵니다. 레이어는 읽기 전용이며, 컨테이너가 실행될 때 쓰기 가능한 레이어가 최상단에 추가됩니다.
</details>

5. Dockerfile에서 다단계 빌드를 사용하는 주요 목적은 무엇인가요?
   - A) 빌드 속도 향상
   - B) 최종 이미지 크기 감소
   - C) 보안 취약점 감소
   - D) 여러 운영체제 지원
   
<details>

<summary>정답 보기</summary>

**정답: B) 최종 이미지 크기 감소**

**설명:**
다단계 빌드의 주요 목적은 최종 이미지 크기를 줄이는 것입니다. 빌드 단계에서는 소스 코드 컴파일, 의존성 설치 등 필요한 모든 도구를 포함하고, 실행 단계에서는 빌드 결과물만 가져와 최소한의 런타임 환경만 포함하는 작은 이미지를 생성합니다. 이를 통해 빌드 도구와 중간 파일을 최종 이미지에서 제외할 수 있습니다.
</details>
6. Docker의 기본 네트워크 드라이버는 무엇인가요?
   - A) host
   - B) bridge
   - C) overlay
   - D) macvlan
   
<details>

<summary>정답 보기</summary>

**정답: B) bridge**

**설명:**
bridge는 Docker의 기본 네트워크 드라이버로, 동일한 호스트에서 실행되는 컨테이너 간의 통신을 가능하게 합니다. 이 드라이버는 호스트 내에 가상 브리지를 생성하여 컨테이너를 연결합니다. host 드라이버는 호스트 네트워크를 직접 사용하고, overlay는 다중 호스트 간 통신을 위한 것이며, macvlan은 컨테이너에 MAC 주소를 할당하여 물리 네트워크 장치처럼 보이게 합니다.
</details>

7. 컨테이너의 영구 데이터 저장을 위한 방법 중 Docker가 관리하는 호스트 파일 시스템의 영역을 사용하는 것은 무엇인가요?
   - A) 임시 스토리지
   - B) 볼륨
   - C) 바인드 마운트
   - D) tmpfs 마운트
   
<details>

<summary>정답 보기</summary>

**정답: B) 볼륨**

**설명:**
볼륨은 Docker가 관리하는 호스트 파일 시스템의 영역으로, 컨테이너의 영구 데이터 저장에 가장 적합한 방법입니다. 임시 스토리지는 컨테이너 내부 파일 시스템으로 컨테이너 삭제 시 데이터가 손실됩니다. 바인드 마운트는 호스트의 특정 경로를 컨테이너에 마운트하는 방식이고, tmpfs 마운트는 메모리에만 데이터를 저장합니다.
</details>

8. 컨테이너 보안을 강화하기 위한 방법이 아닌 것은 무엇인가요?
   - A) 루트가 아닌 사용자로 컨테이너 실행
   - B) 필요한 Linux 기능(capabilities)만 부여
   - C) 모든 컨테이너에 관리자 권한 부여
   - D) 읽기 전용 파일 시스템 사용
   
<details>

<summary>정답 보기</summary>

**정답: C) 모든 컨테이너에 관리자 권한 부여**

**설명:**
모든 컨테이너에 관리자 권한을 부여하는 것은 보안을 약화시키는 행위입니다. 컨테이너 보안을 강화하기 위해서는 최소 권한 원칙을 따라야 합니다. 루트가 아닌 사용자로 컨테이너를 실행하고, 필요한 Linux 기능만 부여하며, 가능한 경우 파일 시스템을 읽기 전용으로 마운트하는 것이 좋은 보안 관행입니다.
</details>

9. AWS에서 서버리스 컨테이너 실행 환경을 제공하는 서비스는 무엇인가요?
   - A) Amazon EC2
   - B) Amazon ECS
   - C) Amazon Fargate
   - D) Amazon ECR
   
<details>

<summary>정답 보기</summary>

**정답: C) Amazon Fargate**

**설명:**
Amazon Fargate는 AWS의 서버리스 컨테이너 실행 환경으로, 서버를 관리하지 않고도 컨테이너를 실행할 수 있습니다. Amazon EC2는 가상 서버 서비스, Amazon ECS는 컨테이너 오케스트레이션 서비스, Amazon ECR은 컨테이너 이미지 레지스트리 서비스입니다.
</details>

10. 컨테이너 오케스트레이션 도구의 주요 기능이 아닌 것은 무엇인가요?
    - A) 자동 배포 및 롤백
    - B) 서비스 검색 및 로드 밸런싱
    - C) 컨테이너 이미지 빌드
    - D) 자동 확장

<details>

<summary>정답 보기</summary>

**정답: C) 컨테이너 이미지 빌드**

**설명:**
컨테이너 이미지 빌드는 일반적으로 CI/CD 파이프라인이나 Docker와 같은 컨테이너 빌드 도구의 역할입니다. 컨테이너 오케스트레이션 도구(Kubernetes, Docker Swarm 등)의 주요 기능은 자동 배포 및 롤백, 서비스 검색 및 로드 밸런싱, 자동 확장, 자가 복구, 구성 관리, 스토리지 오케스트레이션 등입니다.
</details>

11. 컨테이너가 실행 중이 아닌 상태에서 존재할 수 있는 상태가 아닌 것은 무엇인가요?
    - A) Created
    - B) Exited
    - C) Building
    - D) Paused

<details>

<summary>정답 보기</summary>

**정답: C) Building**

**설명:**
컨테이너의 라이프사이클 상태에는 Created(생성됨), Running(실행 중), Paused(일시 중지), Restarting(재시작 중), Exited(종료됨), Dead(죽음) 상태가 있습니다. Building은 이미지 빌드 과정의 상태이며, 컨테이너의 상태가 아닙니다. 컨테이너는 이미지가 빌드된 후에 생성됩니다.
</details>

12. 컨테이너 재시작 정책 중 Docker 데몬 시작 시에도 컨테이너가 재시작되지만, 수동으로 중지한 경우에는 재시작되지 않는 정책은 무엇인가요?
    - A) no
    - B) on-failure
    - C) always
    - D) unless-stopped

<details>

<summary>정답 보기</summary>

**정답: D) unless-stopped**

**설명:**
`unless-stopped` 재시작 정책은 컨테이너가 명시적으로 중지되지 않는 한 항상 재시작됩니다. Docker 데몬이 재시작되어도 컨테이너가 자동으로 시작되지만, 사용자가 수동으로 `docker stop` 명령으로 중지한 경우에는 데몬 재시작 후에도 컨테이너가 시작되지 않습니다. `always`는 수동 중지 여부와 관계없이 항상 재시작됩니다.
</details>

13. 컨테이너와 원본 이미지 사이의 파일 시스템 변경 사항을 확인하는 Docker 명령은 무엇인가요?
    - A) docker inspect
    - B) docker diff
    - C) docker logs
    - D) docker history

<details>

<summary>정답 보기</summary>

**정답: B) docker diff**

**설명:**
`docker diff` 명령은 컨테이너의 파일 시스템과 원본 이미지 사이의 변경 사항을 보여줍니다. 출력에서 A는 추가(Added), C는 변경(Changed), D는 삭제(Deleted)된 파일을 나타냅니다. 이 명령은 컨테이너가 실행되는 동안 어떤 파일이 수정되었는지 디버깅할 때 유용합니다.
</details>

## 단답형 문제

14. 컨테이너 이미지의 내용을 기반으로 한 고유한 식별자로, SHA256 해시 형태로 표현되는 것은 무엇인가요?

<details>

<summary>정답 보기</summary>

**정답: 다이제스트(Digest)**

**설명:**
다이제스트는 컨테이너 이미지 내용의 SHA256 해시로, 이미지의 고유한 식별자입니다. 태그와 달리 이미지 내용이 변경되면 다이제스트도 변경되므로, 특정 이미지 버전을 정확하게 참조할 때 사용됩니다. 예: `nginx@sha256:2834dc507516af02784808c5f48b7cbe38b8ed5d0f4837f16e78d00deb7e7767`
</details>

15. Dockerfile에서 컨테이너 시작 시 실행할 명령을 지정하는 지시문은 무엇인가요?

<details>

<summary>정답 보기</summary>

**정답: CMD**

**설명:**
CMD 지시문은 컨테이너가 시작될 때 실행할 기본 명령을 지정합니다. 예를 들어, `CMD ["node", "server.js"]`는 컨테이너가 시작될 때 `node server.js` 명령을 실행합니다. CMD는 docker run 명령에 인자를 제공하여 재정의할 수 있습니다.
</details>

16. 컨테이너 간 통신을 위해 Docker가 생성하는 가상 네트워크 인터페이스의 이름은 무엇인가요?

<details>

<summary>정답 보기</summary>

**정답: docker0**

**설명:**
docker0는 Docker가 기본적으로 생성하는 가상 브리지 네트워크 인터페이스입니다. 이 브리지는 동일한 호스트에서 실행되는 컨테이너 간의 통신을 가능하게 하고, 컨테이너와 외부 네트워크 간의 통신을 중개합니다.
</details>

17. 컨테이너 내에서 실행되는 프로세스가 사용할 수 있는 시스템 호출을 제한하는 Linux 보안 기능은 무엇인가요?

<details>

<summary>정답 보기</summary>

**정답: seccomp (Secure Computing Mode)**

**설명:**
seccomp는 프로세스가 사용할 수 있는 시스템 호출을 제한하는 Linux 커널 보안 기능입니다. Docker와 같은 컨테이너 런타임은 seccomp 프로필을 사용하여 컨테이너가 수행할 수 있는 시스템 호출을 제한함으로써 보안을 강화합니다.
</details>

18. AWS에서 컨테이너 이미지를 저장하고 관리하는 서비스의 이름은 무엇인가요?

<details>

<summary>정답 보기</summary>

**정답: Amazon ECR (Elastic Container Registry)**

**설명:**
Amazon ECR(Elastic Container Registry)은 AWS의 관리형 컨테이너 이미지 레지스트리 서비스입니다. 이미지 취약점 스캐닝, IAM과의 통합, 이미지 라이프사이클 관리 등의 기능을 제공하며, AWS의 다른 서비스들과 원활하게 통합됩니다.
</details>

19. 컨테이너가 실행 중일 때 해당 컨테이너 내부에서 추가 명령을 실행할 수 있게 해주는 Docker 명령은 무엇인가요?

<details>

<summary>정답 보기</summary>

**정답: docker exec**

**설명:**
`docker exec` 명령은 실행 중인 컨테이너 내부에서 추가 명령을 실행할 수 있게 해줍니다. 예를 들어, `docker exec -it <container> bash`로 컨테이너 내부에 대화형 셸로 접속하거나, `docker exec <container> ls /app`으로 컨테이너 내부의 파일 목록을 확인할 수 있습니다. 이 명령은 컨테이너 디버깅에 매우 유용합니다.
</details>

20. Docker에서 컨테이너의 실시간 이벤트(시작, 중지, 재시작 등)를 스트림으로 모니터링하는 명령은 무엇인가요?

<details>

<summary>정답 보기</summary>

**정답: docker events**

**설명:**
`docker events` 명령은 Docker 데몬에서 발생하는 실시간 이벤트를 스트림으로 보여줍니다. 컨테이너 시작, 중지, 재시작, 이미지 풀, 네트워크 연결/해제 등의 이벤트를 모니터링할 수 있습니다. `--filter` 옵션으로 특정 컨테이너나 이벤트 유형만 필터링할 수 있어 디버깅과 모니터링에 유용합니다.
</details>

## 실습 문제

21. 다음 요구사항을 충족하는 Dockerfile을 작성하세요:
    - Node.js 14 Alpine 이미지 사용
    - 작업 디렉토리를 /app으로 설정
    - package.json과 package-lock.json 파일을 먼저 복사
    - 의존성 설치
    - 나머지 파일 복사
    - 포트 3000 노출
    - 컨테이너 시작 시 "node server.js" 명령 실행

<details>

<summary>정답 보기</summary>

**정답:**
```dockerfile
FROM node:14-alpine

WORKDIR /app

COPY package*.json ./

RUN npm install

COPY . .

EXPOSE 3000

CMD ["node", "server.js"]
```

**설명:**
이 Dockerfile은 Node.js 애플리케이션을 위한 기본적인 구성을 보여줍니다. 의존성 파일(package*.json)을 먼저 복사하고 설치한 후, 나머지 파일을 복사하는 방식으로 Docker의 레이어 캐싱을 최적화합니다. 이렇게 하면 소스 코드가 변경되어도 의존성이 변경되지 않았다면 npm install 단계를 재사용할 수 있습니다.
</details>

22. 다음 Docker 명령을 분석하고 그 목적을 설명하세요:
    ```bash
    docker run -d --name my-app -p 8080:80 -v data:/app/data --restart always nginx:latest
    ```

<details>

<summary>정답 보기</summary>

**정답:**
이 명령은 다음과 같은 목적으로 사용됩니다:
    - `-d`: 컨테이너를 백그라운드(detached 모드)에서 실행
    - `--name my-app`: 컨테이너 이름을 "my-app"으로 설정
    - `-p 8080:80`: 호스트의 8080 포트를 컨테이너의 80 포트에 매핑
    - `-v data:/app/data`: "data"라는 이름의 볼륨을 컨테이너의 /app/data 경로에 마운트
    - `--restart always`: 컨테이너가 종료되면 항상 자동으로 재시작
    - `nginx:latest`: 최신 버전의 nginx 이미지 사용

이 명령은 nginx 웹 서버를 백그라운드에서 실행하고, 호스트의 8080 포트를 통해 접근할 수 있게 하며, 영구 데이터 저장을 위한 볼륨을 설정하고, 컨테이너가 종료되면 자동으로 재시작하도록 구성합니다.
</details>

23. 다단계 빌드를 사용하여 React 애플리케이션을 위한 최적화된 Dockerfile을 작성하세요.

<details>

<summary>정답 보기</summary>

**정답:**
```dockerfile
# 빌드 단계
FROM node:14 AS build

WORKDIR /app

COPY package*.json ./

RUN npm install

COPY . .

RUN npm run build

# 실행 단계
FROM nginx:alpine

# 빌드 결과물을 nginx의 서비스 디렉토리로 복사
COPY --from=build /app/build /usr/share/nginx/html

# 기본 nginx 구성 사용

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
```

**설명:**
이 다단계 Dockerfile은 두 단계로 구성됩니다:
1. 빌드 단계: Node.js 이미지를 사용하여 React 애플리케이션을 빌드합니다.
2. 실행 단계: 경량 nginx 이미지를 사용하여 빌드된 정적 파일을 제공합니다.

이 접근 방식의 장점은 최종 이미지에 Node.js 런타임, npm 패키지, 소스 코드 등이 포함되지 않아 이미지 크기가 크게 줄어든다는 것입니다. 최종 이미지는 빌드된 정적 파일과 nginx만 포함하므로 더 작고 보안적으로 안전합니다.
</details>

24. 컨테이너 헬스 체크를 포함하는 Dockerfile을 작성하세요. HTTP 엔드포인트 /health를 30초마다 확인하고, 3초 이내에 응답이 없으면 실패로 처리하며, 3회 실패 시 비정상으로 판단하도록 설정하세요.

<details>

<summary>정답 보기</summary>

**정답:**
```dockerfile
FROM nginx:alpine

# 애플리케이션 복사 (예시)
COPY ./html /usr/share/nginx/html

# 헬스 체크 설정
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
  CMD wget --quiet --tries=1 --spider http://localhost/health || exit 1

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
```

**설명:**
HEALTHCHECK 지시어의 각 옵션 의미:
- `--interval=30s`: 30초마다 헬스 체크 수행
- `--timeout=3s`: 헬스 체크 명령이 3초 이내에 완료되어야 함
- `--start-period=10s`: 컨테이너 시작 후 10초간 헬스 체크 실패를 무시 (초기화 시간)
- `--retries=3`: 3회 연속 실패 시 컨테이너를 unhealthy로 표시
- `CMD`: 실행할 헬스 체크 명령. wget으로 /health 엔드포인트 확인

헬스 체크는 컨테이너 오케스트레이션 도구가 컨테이너 상태를 파악하여 자동 복구나 트래픽 라우팅 결정에 활용합니다.
</details>

25. 컨테이너 디버깅을 위해 실행 중인 컨테이너의 환경 변수, 네트워크 설정, 프로세스 목록을 확인하는 Docker 명령어들을 작성하세요.

<details>

<summary>정답 보기</summary>

**정답:**
```bash
# 1. 환경 변수 확인
docker exec <container-id> env

# 또는 inspect 사용
docker inspect <container-id> --format='{{range .Config.Env}}{{println .}}{{end}}'

# 2. 네트워크 설정 확인
docker exec <container-id> ip addr
docker exec <container-id> netstat -tuln
# 또는
docker exec <container-id> ss -tuln

# IP 주소만 확인
docker inspect <container-id> --format='{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}'

# 3. 프로세스 목록 확인
docker exec <container-id> ps aux
# 또는
docker top <container-id>

# 4. 추가 유용한 디버깅 명령
# 컨테이너 상세 정보
docker inspect <container-id>

# 컨테이너 로그
docker logs <container-id>

# 파일 시스템 변경 사항
docker diff <container-id>

# 실시간 리소스 사용량
docker stats <container-id>
```

**설명:**
컨테이너 디버깅 시 이러한 명령들을 조합하여 문제를 진단합니다:
- `docker exec`는 실행 중인 컨테이너에서 명령 실행
- `docker inspect`는 컨테이너의 상세 메타데이터 확인
- `docker top`은 컨테이너 프로세스를 호스트 관점에서 확인
- `docker diff`는 이미지 대비 변경된 파일 확인
이러한 도구들을 활용하면 컨테이너 내부 상태를 효과적으로 파악하고 문제를 해결할 수 있습니다.
</details>

## 심화 문제

26. 컨테이너 기술의 핵심 구성 요소인 네임스페이스와 cgroups의 역할을 비교하고, 각각이 컨테이너 격리에 어떻게 기여하는지 설명하세요.

<details>

<summary>정답 보기</summary>

**정답:**

**네임스페이스(Namespaces)**:
    - **역할**: 프로세스 그룹을 격리하여 각 그룹이 시스템 자원을 독립적으로 볼 수 있게 합니다.
    - **격리 유형**: 가시성 격리(visibility isolation)를 제공합니다.
    - **주요 네임스페이스**:
    - PID 네임스페이스: 프로세스 ID 격리
    - 네트워크 네임스페이스: 네트워크 스택 격리
    - 마운트 네임스페이스: 파일 시스템 마운트 포인트 격리
    - UTS 네임스페이스: 호스트명과 도메인명 격리
    - IPC 네임스페이스: 프로세스 간 통신 자원 격리
    - 사용자 네임스페이스: 사용자 및 그룹 ID 격리

**cgroups(Control Groups)**:
    - **역할**: 프로세스 그룹의 자원 사용을 제한하고 격리합니다.
    - **격리 유형**: 자원 사용량 제한(resource limitation)을 제공합니다.
    - **주요 기능**:
    - CPU 시간 제한
    - 메모리 사용량 제한
    - 블록 I/O 대역폭 제한
    - 네트워크 대역폭 제한
    - 장치 접근 제어

**컨테이너 격리에 대한 기여**:

네임스페이스와 cgroups는 서로 보완적인 역할을 합니다:

    - 네임스페이스는 컨테이너가 자신만의 독립된 환경(프로세스 트리, 네트워크 인터페이스, 마운트 포인트 등)을 가질 수 있게 하여 논리적 격리를 제공합니다. 이를 통해 컨테이너는 자신만의 고유한 시스템 뷰를 갖게 됩니다.

    - cgroups는 컨테이너가 사용할 수 있는 시스템 자원(CPU, 메모리, 디스크 I/O 등)을 제한하여 물리적 자원 격리를 제공합니다. 이를 통해 한 컨테이너가 과도한 자원을 사용하여 다른 컨테이너나 호스트 시스템에 영향을 미치는 것을 방지합니다.

두 기술이 함께 작동하여 컨테이너는 독립된 환경에서 제한된 자원을 사용하며 실행될 수 있습니다. 이러한 격리는 가상 머신보다 가볍지만, 보안과 자원 관리 측면에서 충분한 격리를 제공합니다.
</details>

27. 컨테이너 이미지 레이어링 시스템의 작동 방식과 Copy-on-Write(CoW) 전략이 컨테이너의 효율성에 어떻게 기여하는지 설명하세요.

<details>

<summary>정답 보기</summary>

**정답:**

**컨테이너 이미지 레이어링 시스템**:

컨테이너 이미지는 여러 레이어의 스택으로 구성됩니다. 각 레이어는 파일 시스템의 변경사항을 나타내며, Dockerfile의 각 명령(FROM, RUN, COPY 등)은 새로운 레이어를 생성합니다. 이러한 레이어는 읽기 전용이며, 계층적으로 쌓여 최종 이미지를 형성합니다.

레이어링 시스템의 주요 특징:
1. **증분적 빌드**: 이미지 빌드 시 변경된 레이어만 다시 생성
2. **레이어 공유**: 여러 이미지가 동일한 기본 레이어 공유
3. **캐싱**: 이미 다운로드된 레이어는 재사용

**Copy-on-Write(CoW) 전략**:

Copy-on-Write는 데이터가 실제로 수정될 때까지 복사 작업을 지연시키는 최적화 전략입니다. 컨테이너 컨텍스트에서:

1. **컨테이너 시작**: 컨테이너가 시작되면, 기존 이미지 레이어 위에 쓰기 가능한 얇은 레이어가 추가됩니다.
2. **읽기 작업**: 파일을 읽을 때, 시스템은 위에서 아래로 레이어를 검색하여 첫 번째로 발견된 파일 버전을 사용합니다.
3. **쓰기 작업**: 파일을 수정할 때, 해당 파일이 먼저 쓰기 가능 레이어로 복사된 후 수정됩니다(Copy-on-Write). 원본 파일은 변경되지 않습니다.
4. **삭제 작업**: 파일을 삭제할 때, 실제로 파일이 삭제되지 않고 쓰기 가능 레이어에 "whiteout" 파일이 생성되어 해당 파일이 삭제된 것처럼 보이게 합니다.

**효율성에 대한 기여**:

1. **스토리지 효율성**: 
    - 동일한 기본 이미지를 사용하는 여러 컨테이너가 이미지 레이어를 공유하므로 디스크 공간이 절약됩니다.
    - 각 컨테이너는 자신이 변경한 데이터만 저장하면 됩니다.

2. **시작 시간 단축**:
    - 새 컨테이너를 시작할 때 전체 파일 시스템을 복사할 필요 없이 쓰기 가능 레이어만 생성하면 됩니다.
    - 이로 인해 컨테이너 시작 시간이 크게 단축됩니다.

3. **메모리 효율성**:
    - 동일한 파일이 여러 컨테이너에서 사용될 때, 페이지 캐시를 공유할 수 있습니다.

4. **네트워크 효율성**:
    - 이미지 다운로드 시 이미 존재하는 레이어는 다시 다운로드하지 않아도 됩니다.

이러한 효율성 덕분에 컨테이너는 가상 머신보다 더 가볍고 빠르게 시작할 수 있으며, 동일한 호스트에서 더 많은 수의 컨테이너를 실행할 수 있습니다.
</details>

28. 컨테이너 라이프사이클 전체를 설명하고, 각 상태(Created, Running, Paused, Restarting, Exited, Dead)에서의 컨테이너 동작과 상태 전환 방법을 설명하세요.

<details>

<summary>정답 보기</summary>

**정답:**

**컨테이너 라이프사이클 상태:**

1. **Created (생성됨)**
   - 컨테이너가 생성되었으나 아직 시작되지 않은 상태
   - `docker create` 명령으로 생성
   - 프로세스가 실행되지 않음, 리소스 할당 최소화
   - 전환: `docker start` → Running

2. **Running (실행 중)**
   - 컨테이너의 메인 프로세스가 실행 중인 상태
   - `docker run` 또는 `docker start`로 진입
   - CPU, 메모리 등 리소스 활발히 사용
   - 전환:
     - `docker pause` → Paused
     - `docker stop` → Exited
     - `docker kill` → Exited
     - `docker restart` → Restarting → Running
     - 프로세스 종료 시 → Exited

3. **Paused (일시 중지)**
   - 모든 프로세스가 SIGSTOP으로 일시 중지됨
   - `docker pause` 명령으로 진입
   - 메모리는 유지되지만 CPU 사용 없음
   - 전환: `docker unpause` → Running

4. **Restarting (재시작 중)**
   - 컨테이너가 재시작 중인 임시 상태
   - `docker restart` 또는 재시작 정책에 의해 발생
   - 전환: 자동으로 Running 또는 Exited로 전환

5. **Exited (종료됨)**
   - 메인 프로세스가 종료된 상태
   - 종료 코드(exit code) 보존
   - 파일 시스템 변경 사항 유지
   - 전환:
     - `docker start` → Running
     - `docker rm` → 삭제

6. **Dead (죽음)**
   - 컨테이너 제거 시도가 실패한 비정상 상태
   - 리소스 정리가 완료되지 않음
   - 일반적으로 수동 개입 필요
   - `docker rm -f`로 강제 제거 시도

**상태 확인 및 관리 명령:**
```bash
# 상태 확인
docker ps -a                    # 모든 컨테이너 목록
docker inspect <id> | jq '.[0].State'  # 상세 상태

# 상태 전환
docker create nginx             # → Created
docker start <id>               # → Running
docker pause <id>               # → Paused
docker unpause <id>             # → Running
docker stop <id>                # → Exited
docker restart <id>             # → Running
docker rm <id>                  # 삭제
```

**재시작 정책과 라이프사이클:**
- `no`: 자동 재시작 없음
- `on-failure[:max]`: 비정상 종료 시 재시작, 최대 횟수 지정 가능
- `always`: 항상 재시작 (데몬 재시작 포함)
- `unless-stopped`: 수동 중지 전까지 항상 재시작

컨테이너 라이프사이클을 이해하면 애플리케이션의 가용성을 보장하고, 문제 발생 시 적절한 복구 전략을 수립할 수 있습니다.
</details>

---

[학습 자료로 돌아가기](../../basics/02-container-technology.md) | [다음 퀴즈: Kubernetes 소개](./03-kubernetes-introduction-quiz.md)
