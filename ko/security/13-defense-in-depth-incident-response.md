# 사고 사례로 설계하는 다층 보안과 침해 대응

> **검토 기준**: AWS·Kubernetes·Palo Alto Networks·Fortinet 공식 문서, CISA 경보, NIST SP 800-61r3. 사고의 공개일과 조사 기준일을 구분합니다.
> **마지막 업데이트**: 2026년 10월 15일

보안 설계는 공격자가 들어오는 경로, 내부에서 이동하는 경로, 데이터를 반출하는 경로와 운영자가 복구하는 경로를 함께 다뤄야 합니다. 이 장은 기존의 [EKS 보안](./06-eks-security-best-practices.md), [네트워크 정책](./04-network-policies.md), [런타임 보안](./08-runtime-security.md)에 경계 보안과 사고 대응을 연결합니다. 아래 운영 기준과 도입 순서는 이 가이드의 **설계 제안**이며 특정 제품 도입이나 설정만으로 안전을 보장하지 않습니다.

## 1. 조사에서 확인한 사고와 설계 교훈

| 사례와 공개·종료 시점 | 공식 자료에서 확인한 범위 | 설계에 반영할 사항 |
|---|---|---|
| ingress-nginx CVE-2025-1974, 2025-03-24 | Pod 네트워크에서 접근 가능한 validating admission controller를 통한 공격. 당시 수정 릴리스는 1.11.5·1.12.1 | 외부 WAF 외에 webhook 접근 경로와 controller의 Secret 권한을 점검 |
| ingress-nginx 유지보수 종료, 2026-03 | Kubernetes Steering/SRC가 2026-01-29에 종료 후 보안 패치 중단을 경고 | 당시 CVE 수정 버전을 2026년 신규 권장 버전으로 사용하지 않고 유지보수되는 구현으로 이전 |
| PAN-OS CVE-2025-0108, 2025-02-12 | 관리 웹 인증 우회. 다른 취약점과 연결한 악용 시도 관측 | 관리 인터페이스를 공인 서비스 경로에서 분리 |
| PAN-OS CVE-2026-0322, 2026-10-14 | 인증된 공격자가 관리 인터페이스를 통해 root 권한 RCE. 제한적인 실제 악용 관측; PA-Series·VM-Series·Panorama에 해당 | 관리자 세션·자격 증명과 관리 네트워크 모두 보호; 제품군별 영향 구분 |
| FortiCloud SSO CVE-2026-24858, CISA KEV 추가 2026-01-27 | FortiCloud SSO 활성 장비에 대한 다른 계정의 접근, 계정·VPN 설정 변경. 기존 SSO CVE를 패치한 장비에서도 새 공격 경로 확인 | “SSO 사용”을 충분한 방어로 보지 않고 관리자 생성·설정 변경을 탐지 |
| FortiGate 잔존 접근, 2025-04-10 | SSL-VPN 관련 파일 경로의 symbolic link로 기존 취약점 패치 후에도 파일 읽기 접근이 남을 수 있음 | 패치와 침해 제거를 별도 완료 조건으로 관리 |

각 행의 근거는 [Kubernetes CVE 경보][S01], [유지보수 종료 성명][S02], [PAN-OS 2025 경보][S04], [2026 경보][S03], [CISA KEV 원본][S06], [Fortinet 잔존 접근 분석][S07]입니다. Fortinet의 2026 SSO 분석은 1월 28일에 범위를 정정해 **제3자 SAML IdP와 FortiAuthenticator는 해당 문제의 영향을 받지 않는다**고 명시합니다. 초기 문장의 “모든 SAML”을 그대로 인용하지 않습니다. [S05]

CISA KEV에는 CVE-2026-0322가 2026-10-14, CVE-2026-24858이 2026-01-27에 추가되어 있습니다. KEV 등재와 제조사 영향 조건을 함께 우선 검토하고, 목록의 미국 연방 조치 기한을 모든 조직의 법적 의무로 일반화하지 않습니다. [S06]

CVE 공개는 모든 설치본의 침해를 의미하지 않습니다. 제품·브랜치·hotfix·기능 활성화·노출·공격 흔적을 함께 확인합니다. PAN-OS 2026 경보에서 Cloud NGFW와 Prisma Access는 제외되며, 그 제외를 다른 CVE로 확대하지 않습니다. 패치 ETA는 릴리스가 실제로 제공된다는 증거와 구분합니다. [S03]

## 2. 통제의 역할과 남는 영역

| 통제 | 주로 다루는 대상 | 함께 필요한 통제 |
|---|---|---|
| WAF | 연결된 리소스의 HTTP(S) 요청과 규칙에 해당하는 공격 | 앱 인증·인가, 입력 검증, 업로드 검사, origin 우회 차단 |
| NGFW·IPS | 실제 통과하는 네트워크 세션과 설정한 보안 프로파일 | TLS 가시성, 관리면 보호, 패치, 양방향 라우팅 |
| GWLB·GWLBE | GENEVE 호환 장비를 검사 경로에 삽입하고 flow를 분배 | 장비의 검사 정책·세션 관리·용량·복구 |
| Kubernetes NetworkPolicy | 지원 CNI가 집행하는 Pod 연결 | hostNetwork·노드·로컬 경로 검증, 서비스 인증 |
| mTLS·SPIFFE | 피어의 신원과 전송 보호 | 서비스별 인가·요청 유효성·접근 기록 |
| 이미지·admission 정책 | 배포되는 이미지·워크로드 설정 | 실행 이후 행위 탐지·패치·비밀 관리 |

WAF의 연결 대상과 GWLB의 역할은 [AWS WAF 리소스 문서][S09], [GWLB 문서][S24]에서 확인합니다. NetworkPolicy는 지원 플러그인이 필요하고, TLS나 모든 트래픽의 공통 게이트웨이 경유를 API 자체로 제공하지 않습니다. [S34]

**장비 존재와 검사 적용은 별개의 증거입니다.** 아래 세 가지를 요청별로 입증하는 것을 완료 기준으로 제안합니다.

1. **경로**: 이 요청이 지정한 WAF·방화벽을 실제로 통과했는가?
2. **정책**: 적용된 규칙·서명·복호화·예외는 무엇인가?
3. **결과**: 허용·거부와 애플리케이션 동작이 기대와 일치하는가?

## 3. 먼저 트래픽 목록을 작성한다

다음 표는 위협 모델 작성용 템플릿입니다. CIDR·주체·리소스 ID는 운영 환경에서 채우고, 관측하지 못한 항목은 “미검증”으로 남깁니다.

| 흐름 | 확인할 진입·반출 경로 | 통제·검증 증거 |
|---|---|---|
| 사용자 → 웹/API | CloudFront, ALB, 별도 LB·도메인·NodePort | Web ACL 연결, 정상 요청, 안전한 차단 canary, origin 직접 접근 결과 |
| 운영자 → 관리면 | PAN-OS/FortiGate, Panorama/FortiManager, EKS API, GitOps | 신뢰 관리 경로, 관리자 인증, 계정 생성·정책 변경 로그 |
| API server → webhook | 컨트롤 플레인과 admission Service | API server 도달, 일반 워크로드 접근 제한, 인증서·RBAC |
| Pod → 외부 | 노드 SNAT, NAT Gateway, TGW, IPv4·IPv6, proxy | 허용 목적지와 거부 목적지, 변환 전후 IP, 방화벽 세션 |
| Pod → Pod/DB | 동일 노드·동일 VPC·다른 VPC | CNI 정책, DB SG, 서비스 인가, 양방향 검증 |
| Pod → AWS 서비스 | PrivateLink, S3/DynamoDB gateway endpoint, 공인 endpoint | IAM·리소스·endpoint 정책과 실제 연결 경로 |
| CI/CD → 클러스터 | OIDC 역할, registry, GitOps controller | 서명·digest, 최소 권한, 변경 승인·감사 기록 |

중앙 TGW 검사는 **TGW로 라우팅한 흐름**에 적용됩니다. 같은 노드의 Pod 통신이나 VPC local·peering·별도 endpoint 경로까지 자동 포함한다고 가정하지 않습니다. 실제 라우팅과 CNI를 함께 확인합니다. [S29] [S30] [S34]

## 4. 보강할 아키텍처의 책임 경계

공개 웹에는 [WAF와 origin 보호](./14-waf-edge-api-security.md), 외부 반출·VPC 간 검사에는 [NGFW 설계](./15-ngfw-paloalto-fortinet.md)와 [GWLB·GENEVE](./16-gwlb-geneve-inspection.md)를 적용합니다. 같은 VPC 내부에는 기존 NetworkPolicy·SG·mTLS를 연결합니다.

계정 분리와 변경 권한은 다음처럼 설계할 수 있습니다.

| 책임 | 제안하는 소유 범위 | 변경 시 확인 |
|---|---|---|
| 앱 팀 | 인증·인가·schema·업로드 처리 | WAF 예외의 실제 앱 보호 |
| 플랫폼 팀 | EKS·controller·CNI·admission·GitOps | webhook·Pod·AWS 권한의 경계 |
| 네트워크 팀 | TGW·VPC route·GWLBE·NAT·장비 용량 | 요청/응답 경로, AZ 실패, 우회 경로 |
| 보안 팀 | 검사 정책·서명·조사·예외 기한 | 차단 효과, 탐지 근거, 복구 완료 |
| 사고 지휘자 | 격리·증거 보존·복구 판단 | 업무 영향, 자격 증명 교체, 재검증 |

기본 경로와 검사 예외를 바꿀 수 있는 권한을 분리하고, 긴급 우회에는 대상·사유·만료·복구 담당자를 기록합니다. 이 구분은 조직 설계 제안이며 실제 AWS 계정 설정을 조사한 결과는 아닙니다.

## 5. 탐지할 행위와 필요한 증거

| 행위 | 연관 분석할 자료 | 단일 자료의 한계 |
|---|---|---|
| 관리자 로그인 후 계정 생성·정책 변경 | 장비 인증·설정 감사, 중앙 관리자, 관리 경로 로그 | 장비 자체가 침해되면 로컬 로그 신뢰가 낮아질 수 있음 |
| WAF 예외·분리 또는 경로 우회 | AWS 변경 감사, Web ACL 연결, route·SG 변경, 앱 접근 | 차단 수가 0이라는 사실만으로 정책 정상 여부를 판단할 수 없음 |
| controller 침해 후 Secret 접근 | Kubernetes audit, controller RBAC, 런타임 행위 | 웹 접근 로그만으로 webhook 공격을 모두 설명할 수 없음 |
| 외부 반출 의심 | CNI 관측, 방화벽 세션, NAT 이전 IP, 앱·AWS API 감사 | VPC Flow Logs에는 앱 payload나 사용자 인가 결과가 없음 |
| 패치 후 재접근 | 관리자 계정·VPN·설정 차이, 비밀 사용 기록 | 버전 숫자만으로 잔존 접근 제거를 확인할 수 없음 |

Fortinet SSO 분석은 관리자 생성과 설정 변경의 조사 근거를 제공하고, EKS 네트워크 문서는 Flow Logs의 메타데이터 성격과 Pod IP 변화에 따른 한계를 설명합니다. [S05] [S33]

GuardDuty의 위협 탐지, Inspector의 취약점 관리, Security Hub의 노출·연관 분석, CSPM의 구성 점검은 서로 다른 역할입니다. 이미 사용 중인 서비스의 탐지 자료와 수집 범위를 확인하고, 네트워크·장비·앱 기록을 시간과 리소스 ID로 연결합니다. 상세 내용은 [EKS 보안 모범 사례](./06-eks-security-best-practices.md)를 참고합니다.

## 6. 침해 의심 시 대응 절차

NIST SP 800-61r3는 탐지·대응·복구를 전체 위험 관리와 연결합니다. 다음은 이를 장비·EKS 환경에 맞춰 구체화한 운영 제안입니다. [S08]

1. **분류**: 경보의 대상 제품·브랜치·기능·노출을 확인하고 조사 범위를 정합니다. 취약 장비와 침해 흔적이 있는 장비를 구분합니다.
2. **증거 확보**: UTC 기준 시각, configuration revision, 관리자·VPN 계정, 인증·시스템·위협 로그와 클라우드 변경 기록을 보존합니다. 격리 지연이 피해를 키우면 격리를 병행하고 이유를 기록합니다.
3. **격리**: 영향을 받은 관리 경로와 워크로드를 제한합니다. 컨트롤 플레인·DNS·로그 반출·승인된 복구 경로의 의존성을 확인합니다.
4. **접근 제거**: 제조사 절차에 따라 잔존 계정·설정·파일 변경을 조사하고, 필요하면 검증된 이미지와 알려진 정상 설정으로 재구성합니다. 의심 설정을 그대로 복원하지 않습니다.
5. **비밀 교체**: 조사 범위에 따라 관리자·VPN·LDAP/AD·API·클라우드 자격 증명, 관련 인증서와 세션을 검토합니다. 방화벽 비밀번호 한 개 교체로 완료하지 않습니다.
6. **복구 입증**: 관리면 접근 거부, 정상 업무, 안전한 차단 canary, egress, AZ 실패와 로그 수집을 재검증합니다.
7. **재발 방지**: 원인·노출 기간·예외·탐지 지연과 변경 권한을 분석하고 통제·플레이북을 수정합니다.

Fortinet은 침해 지표 확인 시 설정을 침해된 것으로 취급하고 정상 설정 복구·감사와 관련 자격 증명 교체를 안내합니다. 잔존 접근 분석도 설정 검토를 요구합니다. [S05] [S07]

## 7. 도입 순서와 완료 기준

아래 일정은 조직에서 조정할 실행 계획입니다. 공급사 SLA나 실제 침해 대응 기한으로 해석하지 않습니다.

| 단계 | 수행 내용 | 완료 증거 |
|---|---|---|
| 우선 | 공개 관리면·미유지보수 ingress·실제 악용 CVE·origin 우회 목록화 | 자산·노출·영향 브랜치·소유자, 조치 기록 |
| 1단계 | WAF 로그·규칙 검증, 관리자 변경 탐지, webhook·Pod 경계 | 허용/거부 시험 결과와 적용 정책 ID |
| 2단계 | egress·VPC 간 검사, Palo Alto/Fortinet PoC, GWLB 대칭 경로 | 요청/응답 capture, NAT 위치, 장애 실험 |
| 3단계 | 용량·업그레이드·복구·예외 만료 운영 | SLO 측정, 복구 훈련, 검토된 변경 절차 |

“차단률 향상” 하나로 성공을 평가하지 않습니다. **검사 경로 포함률, origin 우회 시험, 미승인 관리자 변경, 로그 누락, 복구 시간, 정상 업무 오류율**을 함께 관리합니다. 가용성 보장이나 성능 수치는 실제 측정 전까지 기입하지 않습니다.

## 다음 학습

- [WAF·엣지·API 보안](./14-waf-edge-api-security.md)
- [Palo Alto·Fortinet NGFW](./15-ngfw-paloalto-fortinet.md)
- [GWLB·GENEVE 검사 경로](./16-gwlb-geneve-inspection.md)
- [이 장의 퀴즈](../quizzes/security/13-defense-in-depth-incident-response-quiz.md)

## 참고 자료와 조사 기준

아래 공식 자료는 2026-10-15에 조회했습니다. 변경 시 해당 제품·브랜치의 최신 경보와 제약을 다시 확인합니다.

- [S01: Kubernetes: CVE-2025-1974][S01]
- [S02: Kubernetes: ingress-nginx retirement statement][S02]
- [S03: Palo Alto: CVE-2026-0322][S03]
- [S04: Palo Alto: CVE-2025-0108][S04]
- [S05: Fortinet: Analysis of SSO abuse on FortiOS][S05]
- [S06: CISA: Known Exploited Vulnerabilities Catalog][S06]
- [S07: Fortinet: Analysis of threat actor activity][S07]
- [S08: NIST SP 800-61r3][S08]
- [S09: AWS WAF: Associating a web ACL][S09]
- [S24: AWS: Gateway Load Balancers][S24]
- [S29: AWS: Centralized inspection with GWLB and TGW][S29]
- [S30: AWS: NAT Gateway scenarios][S30]
- [S33: EKS: Network security][S33]
- [S34: Kubernetes: Network Policies][S34]

[S01]: https://kubernetes.io/blog/2025/03/24/ingress-nginx-cve-2025-1974/
[S02]: https://kubernetes.io/blog/2026/01/29/ingress-nginx-statement/
[S03]: https://security.paloaltonetworks.com/CVE-2026-0322
[S04]: https://security.paloaltonetworks.com/CVE-2025-0108
[S05]: https://www.fortinet.com/blog/psirt-blogs/analysis-of-sso-abuse-on-fortios
[S06]: https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json
[S07]: https://www.fortinet.com/blog/psirt-blogs/analysis-of-threat-actor-activity
[S08]: https://csrc.nist.gov/pubs/sp/800/61/r3/final
[S09]: https://docs.aws.amazon.com/waf/latest/developerguide/web-acl-associating-aws-resource.html
[S24]: https://docs.aws.amazon.com/elasticloadbalancing/latest/gateway/gateway-load-balancers.html
[S29]: https://aws.amazon.com/blogs/networking-and-content-delivery/centralized-inspection-architecture-with-aws-gateway-load-balancer-and-aws-transit-gateway/
[S30]: https://docs.aws.amazon.com/vpc/latest/userguide/nat-gateway-scenarios.html
[S33]: https://docs.aws.amazon.com/eks/latest/best-practices/network-security.html
[S34]: https://kubernetes.io/docs/concepts/services-networking/network-policies/
