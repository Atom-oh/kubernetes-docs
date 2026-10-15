# 보안 콘텐츠 심층 조사와 반영 기록

> **조사 기준일**: 2026-10-15 UTC
> **대상**: Kubernetes·EKS 가이드의 경계 보안, WAF, Palo Alto VM-Series, FortiGate-VM, GWLB·GENEVE, 침해 대응
> **산출물 성격**: 공식 공개 자료를 검토한 문헌 조사와 설계 제안. 실환경 보안 진단·장비 PoC·성능 측정 결과가 아님.

## 1. 문제와 조사 질문

기존 Security & Policy 1–12장은 IAM, admission, Pod 정책, Secret, 이미지와 runtime 보호에 집중되어 있었다. Networking 개요에 GWLB가 있지만, WAF·origin 보호·제조사 통합·양방향 route·장애 수용 기준을 연결하는 상세 학습 경로가 부족했다.

조사 질문:

1. 최근 실제 악용 사례는 어떤 보호 경로의 누락을 보여주는가?
2. WAF가 지원하는 리소스·action·body·forwarded IP·rate·logging의 한계는 무엇인가?
3. Palo Alto와 Fortinet의 공식 GWLB 통합에서 interface·정책·health·관리면에 필요한 조건은 무엇인가?
4. GENEVE encapsulation·TGW appliance mode·NAT·GWLBE는 request/response의 어떤 부분을 책임지는가?
5. unhealthy·deregistration·idle·RST·AZ 손실에서 기존/신규 세션은 어떻게 다른가?
6. 패치와 침해 제거를 분리하는 대응·검증·변경 관리 기준은 무엇인가?

## 2. 조사 방법과 증거 관리

- 기존 `ko/en/security`, Networking 개요와 navigation을 대조해 누락 영역을 정했다.
- PAN-OS 경보, Fortinet PSIRT 블로그, CISA KEV JSON, Kubernetes 블로그를 대상으로 최근 사고와 영향 범위를 확인했다.
- AWS 개발자 문서·API parameter 문서·공식 네트워킹 블로그, 제조사 배포 문서, RFC·NIST로 설계 조건을 교차 확인했다.
- 공개 웹 검색 후보를 탐색하고 공식 사이트의 navigation·related link를 따라 실제 문서를 확보했다. 관련 없는 검색 결과, 검색엔진의 접근 확인 페이지, 404와 서비스 landing page로의 soft redirect는 근거에서 제외했다.
- 공식 페이지를 HTTP로 읽고 상태·resolved URL·조회 시각·내용 hash를 기록했다. 자료 원문 cache는 `/tmp/security-research-2026-10-15`에만 두었다.
- 출처 원장은 [JSON](./2026-10-15-security-sources.json)으로 남긴다. HTTP 200을 주장 검증 완료와 동일시하지 않으며, 원장에 사용한 주장과 한계를 따로 기록한다.
- 한국어·영어 본문에는 같은 source ID를 사용한다. 선택한 자료의 해당 절에서 사실을 확인하고, 운영 계획·예외 정책·수용 기준은 가이드의 제안으로 표시했다.

검색/탐색 주제에는 `PAN-OS management RCE`, `FortiCloud SSO`, `Fortinet persistent access`, `ingress-nginx retirement`, `WAF body oversize`, `GWLB failover flow stickiness`, `GENEVE MTU`, `TGW appliance mode NAT return path`가 포함된다. 검색 결과의 요약만으로 기술 조건을 확정하지 않았다.

## 3. 사고 자료의 날짜와 범위

| 근거 | 확인한 시점·범위 | 콘텐츠 결정 |
|---|---|---|
| S01·S02 | admission CVE 공개 2025-03-24; 종료 성명 2026-01-29, 종료 2026-03 | 1.11.5·1.12.1은 당시 수정 버전으로만 언급; 현재 추천으로 사용하지 않음 |
| S03·S06 | PAN-OS CVE-2026-0322 공개·KEV 추가 2026-10-14 | 인증된 관리면 RCE, PA/VM/Panorama 영향과 Cloud NGFW/Prisma 제외를 명시 |
| S04 | PAN-OS CVE-2025-0108 공개 2025-02-12 | 관리면 인증 우회와 경로 제한·계정 보호를 연결 |
| S05·S06 | Fortinet 블로그 2026-01-22, 범위 정정 01-28; CVE-2026-24858 KEV 추가 01-27 | FortiCloud만의 영향과 제3자 SAML/FortiAuthenticator 제외를 구분 |
| S07 | 잔존 파일 읽기 분석 2025-04-10 | 패치와 침해 제거를 다른 완료 조건으로 취급 |

KEV 등재는 실제 악용 판단의 자료이고, 특정 조직 설치본의 침해 증거는 아니다. 미국 연방 기한을 일반 조직의 법적 의무로 옮기지 않는다. 제조사 patch ETA도 실제 릴리스 제공과 구분한다. [S03] [S05] [S06]

## 4. 기술 검증에서 수정·정교화한 항목

| 쟁점 | 채택한 설명 | 근거 |
|---|---|---|
| WAF 적용 범위 | REST API 직접 연결과 HTTP/WebSocket API, NLB 또는 CloudFront 앞단 보호를 구분 | S09 |
| Body | ALB/AppSync 8 KB; 지원 리소스 기본 16 KB·최대 64 KB; gRPC body 제외 | S11 |
| Rule action | Allow/Block 종료, Count 계속; MATCH는 statement 일치이며 자체 Block 아님 | S10·S12 |
| Origin | CloudFront prefix list는 특정 distribution 신원 아님; custom header와 listener 또는 지원 VPC origin | S16·S17 |
| Forwarded IP | Geo·ASN·rate는 첫 주소, IP set은 FIRST/LAST/ANY; 누락은 no match이며 바깥 NOT 반전·malformed fallback과 구분 | S13 |
| Rate | 근사 추적, 60/120/300/600초 window; 설정 변경 카운트 초기화·최대 1분 pause | S37·S43 |
| 로그 | Count·labels·oversize와 terminating 결과를 구분; redaction이 sampling/Security Lake를 자동 보호하지 않음 | S15·S36 |
| ALB 실패 속성 | 확인된 `waf.fail_open.enabled`만 구체적으로 설명; 확인되지 않은 failure 속성명 제거 | S18 |
| Backend TLS | ALB HTTPS target의 인증서는 ALB가 검증하지 않음 | S38 |
| Palo Alto health | 수동 가이드의 HTTP 금지와 뒤의 HTTP profile 설명이 충돌; 자동 고정값으로 옮기지 않고 버전/template 검증 | S20 |
| Palo Alto zone | 기본 intrazone 허용과 명시한 보안 rule/profile 검토가 필요 | S20 |
| Fortinet peer·egress | 같은 AZ GWLB interface IPv4와 GENEVE interface 반환 route; 과거 가이드는 권장 버전이 아님 | S22·S23 |
| GWLB SG | ELB SG parameter는 ALB/NLB, endpoint SG parameter는 interface endpoint; 장비/workload SG와 구분 | S39·S40 |
| Reduced tuple | 현재 문서는 2/3-tuple과 **TGW appliance mode** 조합을 지원하지 않음; cross-zone 조건으로 잘못 치환하지 않음 | S25 |
| Idle | TCP 새 SYN·옛 data drop과 UDP 새 flow 구분; target ENI tracking timeout도 확인 | S24 |
| All-unhealthy | flow별 target 임의 선택과 회복 전 drop이 AWS 문서상 기대; AZ별 대상·cross-zone 구분, 직접 bypass 아님 | S26 |
| 빈 fleet | 등록 대상 없는 새 flow와 기존 draining flow를 구분해 drop·복구 검증 | S25·S42 |
| TCP RST | 현재 속성 지원; 5-tuple·no_rebalance·TCP 필요, reduced tuple·rebalance와 함께 활성화 불가 | S25 |
| MTU | 최대 8500 bytes, 68 bytes overhead; fragmentation/PMTUD 미제공, 경로별 제약 | S24 |
| Return path | TGW attachment·GWLBE·NAT subnet을 구분하고 NAT 역변환 이후 검사 route를 확인 | S19·S29·S30 |
| TLV·SNAT 출처 | GENEVE metadata는 S42·S29, Pod IPv4 외부 SNAT는 S44; S33은 NetworkPolicy·Flow Logs 근거 | S42·S29·S44·S33 |
| TGW 용어 | 기본 origin-AZ 선호와 appliance mode의 flow별 양방향 attachment ENI/AZ 선택을 구분 | S29·S32 |

예전 AWS GWLB 배치 블로그의 RST·고정 timeout·복구 시간 설명은 당시 설계 맥락으로 취급한다. 현재 속성 문서의 TCP RST·timeout 조건을 우선하며, 블로그의 지연 숫자를 현재 환경의 보장값으로 사용하지 않았다. [S24] [S25] [S32]

배포 전 content-review-agent 첫 리뷰의 W-1–W-4를 반영해 주소 선택·all-unhealthy의 문서상 기대·근거 연결·TGW 용어를 정정했다. health-only fault의 전달 가능성은 PoC 가설로 분리했다. S44를 추가해 최종 출처는 43개이며, S41은 탐색용 Fortinet blog index라 근거 원장에서 제외했다.

## 5. 근거로 확정하지 않은 사항

- 특정 제조사가 항상 더 안전하거나 빠르다는 순위.
- 실제 계정의 노출·정책·라이선스·관리자 접근·침해 여부.
- 실측 없이 제시하는 firewall throughput, p95/p99, N-1 가용성 또는 비용.
- GENEVE만으로 암호화·TLS 종료·장비 state 복제가 제공된다는 설명.
- 중앙 검사가 같은 노드·VPC local·endpoint·peering·IPv6를 자동 포괄한다는 설명.
- 유지보수 종료 제품의 과거 수정 버전을 신규 권장으로 고정하는 설명.
- 제조사 경보의 미제공 patch ETA를 이미 사용 가능한 버전으로 취급하는 설명.
- 모든 Fortinet SAML·모든 Palo Alto 제품이 같은 CVE에 영향받는다는 일반화.

## 6. 산출물과 추적

한국어와 영어에 동일한 4장과 장별 8문항을 추가했다.

| 장 | 내용 | 한국어 | 영어 |
|---|---|---|---|
| 13 | 사례·위협 모델·다층 통제·대응·도입 계획 | [본문](../../ko/security/13-defense-in-depth-incident-response.md) | [본문](../../en/security/13-defense-in-depth-incident-response.md) |
| 14 | WAF·origin·body·action·rate·로그·canary | [본문](../../ko/security/14-waf-edge-api-security.md) | [본문](../../en/security/14-waf-edge-api-security.md) |
| 15 | VM-Series·FortiGate integration·관리면·TLS·세션·PoC | [본문](../../ko/security/15-ngfw-paloalto-fortinet.md) | [본문](../../en/security/15-ngfw-paloalto-fortinet.md) |
| 16 | GWLB·GENEVE·route·NAT·AZ·health·RST·MTU | [본문](../../ko/security/16-gwlb-geneve-inspection.md) | [본문](../../en/security/16-gwlb-geneve-inspection.md) |

두 언어의 SUMMARY·README·quiz navigation을 연결하고 기존 NetworkPolicy·EKS security·Networking 개요에도 새 학습 경로를 넣었다. News topic map에는 WAF·Palo Alto·Fortinet·GWLB·사고 대응 키워드를 추가했다. 이는 들어온 소식의 매칭을 보완하는 것으로, 외부 뉴스 수집기가 모든 제조사 소식을 빠짐없이 가져온다는 보장은 아니다.

`cn/jp/es`는 영어 원문의 자동 번역 mirror이므로 손으로 수정하지 않았다.

## 7. 검증과 운영 후속

검증 명령·결과는 같은 디렉터리의 `2026-10-15-security-validation.json`에 기록한다. 문서 링크·언어 parity·기존 테스트·Markdown/Vue·Mermaid·사이트 build를 확인하고, source ID와 조회 기록을 대조한다. release worktree에서 문서 126개·networking 20개·Spot 29개 테스트도 통과했다.

실환경 검증은 다음 단계의 별도 활동이다. WAF benign canary·origin bypass, webhook 접근, 장비 관리 경로, request/response tuple, all-unhealthy·빈 fleet·AZ 실패·RST·MTU·N-1 용량과 복구 훈련을 승인 환경에서 수행한다.

배포 전 AWS Content Plugin content-review-agent의 독립 재리뷰가 **90/90, PASS, Critical 0·Warning 0**으로 `>= 85` 품질 게이트를 통과했다. [첫 리뷰](../reviews/2026-10-15/security-content-review-iteration-1.md)와 [재리뷰](../reviews/2026-10-15/security-content-review-iteration-2.md)를 보존한다. 실환경 장비·cloud PoC는 수행하지 않았다.

## 참고 자료와 조사 기준

아래 공식 자료는 2026-10-15에 조회했습니다. 변경 시 해당 제품·브랜치의 최신 경보와 제약을 다시 확인합니다.

- [S01 — Kubernetes: CVE-2025-1974][S01]
- [S02 — Kubernetes: ingress-nginx retirement statement][S02]
- [S03 — Palo Alto: CVE-2026-0322][S03]
- [S04 — Palo Alto: CVE-2025-0108][S04]
- [S05 — Fortinet: Analysis of SSO abuse on FortiOS][S05]
- [S06 — CISA: Known Exploited Vulnerabilities Catalog][S06]
- [S07 — Fortinet: Analysis of threat actor activity][S07]
- [S08 — NIST SP 800-61r3][S08]
- [S09 — AWS WAF: Associating a web ACL][S09]
- [S10 — AWS WAF: Rule action][S10]
- [S11 — AWS WAF: Body inspection sizes][S11]
- [S12 — AWS WAF: Oversize request components][S12]
- [S13 — AWS WAF: Forwarded IP addresses][S13]
- [S14 — AWS WAF: Rate-based rules][S14]
- [S15 — AWS WAF: Logging][S15]
- [S16 — CloudFront: Restricting access to ALB origins][S16]
- [S17 — CloudFront: VPC origins][S17]
- [S18 — ALB: Attributes][S18]
- [S19 — VM-Series: GWLB integration][S19]
- [S20 — VM-Series: Manual GWLB integration][S20]
- [S21 — VM-Series: Enable GWLB integration][S21]
- [S22 — FortiGate: GWLB post-deployment configuration][S22]
- [S23 — FortiGate: Security inspection with GWLB integration][S23]
- [S24 — AWS: Gateway Load Balancers][S24]
- [S25 — AWS GWLB: Target group attributes][S25]
- [S26 — AWS GWLB: Health checks][S26]
- [S27 — AWS PrivateLink: Gateway Load Balancer endpoints][S27]
- [S28 — AWS VPC: Route table options][S28]
- [S29 — AWS: Centralized inspection with GWLB and TGW][S29]
- [S30 — AWS: NAT Gateway scenarios][S30]
- [S31 — RFC 8926: GENEVE][S31]
- [S32 — AWS: GWLB deployment best practices][S32]
- [S33 — EKS: Network security][S33]
- [S34 — Kubernetes: Network Policies][S34]
- [S35 — AWS Network Firewall: TLS inspection configurations][S35]
- [S36 — AWS WAF: Log fields][S36]
- [S37 — AWS WAF: Rate evaluation window][S37]
- [S38 — ALB: Target groups][S38]
- [S39 — AWS ELB API: CreateLoadBalancer parameters][S39]
- [S40 — AWS EC2 API: CreateVpcEndpoint parameters][S40]
- [S42 — AWS GWLB: Target groups][S42]
- [S43 — AWS WAF: Rate rule caveats][S43]
- [S44 — EKS: Outbound internet access and SNAT][S44]

[S01]: https://kubernetes.io/blog/2025/03/24/ingress-nginx-cve-2025-1974/
[S02]: https://kubernetes.io/blog/2026/01/29/ingress-nginx-statement/
[S03]: https://security.paloaltonetworks.com/CVE-2026-0322
[S04]: https://security.paloaltonetworks.com/CVE-2025-0108
[S05]: https://www.fortinet.com/blog/psirt-blogs/analysis-of-sso-abuse-on-fortios
[S06]: https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json
[S07]: https://www.fortinet.com/blog/psirt-blogs/analysis-of-threat-actor-activity
[S08]: https://csrc.nist.gov/pubs/sp/800/61/r3/final
[S09]: https://docs.aws.amazon.com/waf/latest/developerguide/web-acl-associating-aws-resource.html
[S10]: https://docs.aws.amazon.com/waf/latest/developerguide/waf-rule-action.html
[S11]: https://docs.aws.amazon.com/waf/latest/developerguide/web-acl-setting-body-inspection-limit.html
[S12]: https://docs.aws.amazon.com/waf/latest/developerguide/waf-oversize-request-components.html
[S13]: https://docs.aws.amazon.com/waf/latest/developerguide/waf-rule-statement-forwarded-ip-address.html
[S14]: https://docs.aws.amazon.com/waf/latest/developerguide/waf-rule-statement-type-rate-based.html
[S15]: https://docs.aws.amazon.com/waf/latest/developerguide/logging.html
[S16]: https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/restrict-access-to-load-balancer.html
[S17]: https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/private-content-vpc-origins.html
[S18]: https://docs.aws.amazon.com/elasticloadbalancing/latest/application/application-load-balancers.html
[S19]: https://docs.paloaltonetworks.com/vm-series/deployment/public-cloud/set-up-the-vm-series-firewall-on-aws/vm-series-integration-with-gateway-load-balancer
[S20]: https://docs.paloaltonetworks.com/vm-series/deployment/public-cloud/set-up-the-vm-series-firewall-on-aws/vm-series-integration-with-gateway-load-balancer/manually-integrate-the-vm-series-with-a-gateway-load-balancer
[S21]: https://docs.paloaltonetworks.com/vm-series/deployment/public-cloud/set-up-the-vm-series-firewall-on-aws/vm-series-integration-with-gateway-load-balancer/enabling-vm-series-integration-with-a-gwlb
[S22]: https://docs.fortinet.com/document/fortigate-public-cloud/7.0.0/aws-administration-guide/337773/post-deployment-configuration
[S23]: https://docs.fortinet.com/document/fortigate-public-cloud/7.0.0/aws-administration-guide/571235/security-inspection-with-gateway-load-balancer-integration
[S24]: https://docs.aws.amazon.com/elasticloadbalancing/latest/gateway/gateway-load-balancers.html
[S25]: https://docs.aws.amazon.com/elasticloadbalancing/latest/gateway/edit-target-group-attributes.html
[S26]: https://docs.aws.amazon.com/elasticloadbalancing/latest/gateway/health-checks.html
[S27]: https://docs.aws.amazon.com/vpc/latest/privatelink/gateway-load-balancer-endpoints.html
[S28]: https://docs.aws.amazon.com/vpc/latest/userguide/route-table-options.html
[S29]: https://aws.amazon.com/blogs/networking-and-content-delivery/centralized-inspection-architecture-with-aws-gateway-load-balancer-and-aws-transit-gateway/
[S30]: https://docs.aws.amazon.com/vpc/latest/userguide/nat-gateway-scenarios.html
[S31]: https://www.rfc-editor.org/info/rfc8926/
[S32]: https://aws.amazon.com/blogs/networking-and-content-delivery/best-practices-for-deploying-gateway-load-balancer/
[S33]: https://docs.aws.amazon.com/eks/latest/best-practices/network-security.html
[S34]: https://kubernetes.io/docs/concepts/services-networking/network-policies/
[S35]: https://docs.aws.amazon.com/network-firewall/latest/developerguide/tls-inspection-configurations.html
[S36]: https://docs.aws.amazon.com/waf/latest/developerguide/logging-fields.html
[S37]: https://docs.aws.amazon.com/waf/latest/developerguide/waf-rule-statement-type-rate-based-high-level-settings.html
[S38]: https://docs.aws.amazon.com/elasticloadbalancing/latest/application/load-balancer-target-groups.html
[S39]: https://docs.aws.amazon.com/elasticloadbalancing/latest/APIReference/API_CreateLoadBalancer.html
[S40]: https://docs.aws.amazon.com/AWSEC2/latest/APIReference/API_CreateVpcEndpoint.html
[S42]: https://docs.aws.amazon.com/elasticloadbalancing/latest/gateway/target-groups.html
[S43]: https://docs.aws.amazon.com/waf/latest/developerguide/waf-rule-statement-type-rate-based-caveats.html
[S44]: https://docs.aws.amazon.com/eks/latest/userguide/external-snat.html
