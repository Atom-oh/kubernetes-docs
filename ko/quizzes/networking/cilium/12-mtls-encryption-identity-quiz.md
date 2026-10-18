# Part 12: mTLS, 투명 암호화, 그리고 Identity 퀴즈

> **검토 기준**: Cilium 1.20.2 (안정, 2026-09-16); Cilium CLI 0.20.1; Hubble CLI 1.20.2. **[1.21 pre-release]** 표시 항목은 v1.21.0-pre.3 기준이며 GA 전에 바뀔 수 있습니다.
> **마지막 업데이트**: 2026년 10월 15일

[본문으로 돌아가기](../../../networking/cilium/12-mtls-encryption-identity.md)

1. Cilium Mutual Authentication(SPIFFE/SPIRE, `authentication.mode: required`)의 1.20과 1.21 상태는 무엇인가요?
   - A) 1.20에서 제거, 1.21에는 없음
   - B) 1.20에서 Beta, 1.21에서 stable
   - C) 1.20에서 deprecated, 1.21에서 제거
   - D) 1.21에서 deprecated, 1.22에서 제거
<details>
<summary>정답 보기</summary>

**정답: C) 1.20에서 deprecated, 1.21에서 제거**

1.20 업그레이드 노트는 deprecated라고 하고(문서 제목은 여전히 "Beta") ztunnel을 안내합니다. 1.21 업그레이드 노트는 deprecation 후 제거되었다고 합니다. 정책의 `authentication` 필드는 CRD 호환을 위해 남아 있지만 1.21에서는 사용되지 않습니다.

</details>

2. reserved identity `reserved:world`의 숫자 ID는 무엇인가요?
   - A) 1
   - B) 6
   - C) 8
   - D) 2
<details>
<summary>정답 보기</summary>

**정답: D) 2**

1은 `host`, 2는 `world`, 6은 `remote-node`, 8은 `ingress`입니다. 9와 10은 world를 IPv4/IPv6로 나눈 것입니다.

</details>

3. Cilium ztunnel mTLS에서 워크로드는 어떻게 가입(enroll)되나요?
   - A) 각 Pod에 `istio.io/dataplane-mode=ambient`를 어노테이션한다
   - B) 네임스페이스에 `io.cilium/mtls-enabled=true` 레이블을 붙인다
   - C) CiliumNetworkPolicy에 `authentication.mode: required`를 추가한다
   - D) 각 Pod에 `io.cilium/mtls-enabled=true` 레이블을 붙인다
<details>
<summary>정답 보기</summary>

**정답: B) 네임스페이스에 `io.cilium/mtls-enabled=true` 레이블을 붙인다**

가입은 네임스페이스 단위로만 지원하며 Pod 단위 가입은 지원되지 않습니다. Istio ambient 레이블은 Istio의 것이고, `authentication.mode`는 제거된 Mutual Authentication 방식이었습니다.

</details>

4. ztunnel 프록시 사이의 HBONE 트래픽이 지나는 TCP 포트이자, 가입된 워크로드에 대해 L4 정책이 지정할 수 있는 유일한 포트는 무엇인가요?
   - A) 15008
   - B) 4250
   - C) 15006
   - D) 15001
<details>
<summary>정답 보기</summary>

**정답: A) 15008**

트래픽은 Pod를 떠나기 전에 암호화되므로 L4 정책이 내부 포트를 볼 수 없고 HBONE 포트 15008만 대상으로 지정할 수 있습니다. 15001과 15006은 Pod 내부의 아웃바운드/평문 인바운드 리다이렉트 포트이며, 4250은 제거된 Mutual Authentication 핸드셰이크 포트였습니다.

</details>

5. `encryption.ztunnel.ca.type`의 기본값은 무엇인가요?
   - A) `spire`
   - B) `istiod`
   - C) `internal`
   - D) `cert-manager`
<details>
<summary>정답 보기</summary>

**정답: C) `internal`**

`internal`은 Cilium 내장 CA를 씁니다. 1.20에서 추가된 `spire`는 외부 SPIRE 서버를 쓰며 operator가 가입된 네임스페이스의 항목을 등록합니다.

</details>

6. Cilium WireGuard 터널 endpoint는 각 노드에서 어떤 UDP 포트를 쓰나요?
   - A) 51820
   - B) 51871
   - C) 4789
   - D) 8472
<details>
<summary>정답 보기</summary>

**정답: B) 51871**

Cilium은 WireGuard 기본값 51820이 아니라 51871을 씁니다. 노드 보안 그룹에서는 공개 CIDR이 아니라 노드 보안 그룹 자기 참조로 노드 간 통신을 허용해야 합니다. 4789와 8472는 VXLAN 포트입니다.

</details>

7. 투명 암호화 strict 모드 옵션 중 WireGuard에서만 동작하는 것은 무엇인가요?
   - A) `encryption.strictMode.ingress.enabled`
   - B) `encryption.strictMode.egress.allowRemoteNodeIdentities`
   - C) `encryption.strictMode.egress.enabled`
   - D) `encryption.strictMode.egress.cidr`
<details>
<summary>정답 보기</summary>

**정답: A) `encryption.strictMode.ingress.enabled`**

Ingress strict 모드는 WireGuard 터널을 거치지 않고 도착한 클러스터 내부 ingress를 드롭하므로 IPsec에서는 지원되지 않습니다. 이전의 평면 플래그(`encryption.strictMode.enabled` 등)는 1.20에서 `egress.*` 이름으로 대체되며 제거되었습니다.

</details>

8. IPsec 키 Secret에서 터널별 파생 키를 강제하는 것은 무엇인가요?
   - A) `encryption.ipsec.interface` 설정
   - B) key ID 0 사용
   - C) `encryption.nodeEncryption` 활성화
   - D) `3+ rfc4106(gcm(aes)) ...`처럼 key ID 뒤의 `+`
<details>
<summary>정답 보기</summary>

**정답: D) `3+ rfc4106(gcm(aes)) ...`처럼 key ID 뒤의 `+`**

전역 키는 1.16에서 deprecated되었습니다(GHSA-pwqm-x5x6-5586). `encryption.ipsec.interface`는 1.20에서 제거되었고 key ID는 1부터 15까지입니다.

</details>

9. kvstore에서 CRD로 가는 Double Write identity 마이그레이션의 순서는 무엇인가요?
   - A) `doublewrite-readkvstore`, `doublewrite-readcrd`, `crd`
   - B) `crd`, `doublewrite-readcrd`, `kvstore`
   - C) `kvstore`, `crd`, `doublewrite-readcrd`
   - D) `doublewrite-readcrd`, `doublewrite-readkvstore`, `crd`
<details>
<summary>정답 보기</summary>

**정답: A) `doublewrite-readkvstore`, `doublewrite-readcrd`, `crd`**

과정 내내 두 저장소에 모두 쓰고, 읽기를 kvstore에서 CRD로 옮긴 다음 kvstore를 버립니다. 각 단계 전에 `cilium_operator_doublewrite_*` 메트릭의 `*_only_identities`가 0이 될 때까지 기다립니다.

</details>

10. Cilium 1.20에서 `spec`도 `specs`도 없는 CiliumNetworkPolicy를 적용하면 어떻게 되나요?
    - A) 받아들여지고 agent가 경고를 로그로 남긴다
    - B) CEL 검증 규칙에 의해 admission 단계에서 거부된다
    - C) 받아들여지고 allow-all로 취급된다
    - D) 받아들여지지만 어떤 endpoint도 선택하지 않는다
<details>
<summary>정답 보기</summary>

**정답: B) CEL 검증 규칙에 의해 admission 단계에서 거부된다**

CRD에 `has(self.spec) || has(self.specs)` 규칙과 "spec or specs must be provided" 메시지가 있습니다. 기존 빈 정책은 수정하기 전까지 영향이 없습니다.

</details>
