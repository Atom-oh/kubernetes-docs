# 身份验证

Istio 支持服务间身份验证（Peer Authentication）和终端用户身份验证（Request Authentication）。

## 目录

1. [身份验证概述](#authentication-overview)
2. [请求身份验证（JWT）](#request-authentication-jwt)
3. [OAuth/OIDC 集成](#oauthoidc-integration)
4. [实践示例](#practical-examples)
5. [故障排除](#troubleshooting)

## 身份验证概述 {#authentication-overview}

RequestAuthentication 会拒绝请求中携带的无效 JWT；如果请求没有凭证，则会放行，除非 AuthorizationPolicy 要求必须提供凭证。它负责验证令牌，不负责登录、OAuth 重定向、令牌刷新，也不会检查不透明访问令牌。请使用签发者的发现文档确认准确的签发者和 JWKS，并配置预期的受众（audience）。以下配置是针对 default 命名空间中 `app=myapp` HTTP 工作负载的不同可选方案；图示展示的是网关部署，因此应将策略附加到该网关。

<p align="center">
  <img src="https://istio.io/latest/docs/concepts/security/authn.svg" alt="Istio 身份验证" width="800">
</p>

Istio 提供两种身份验证方式：

1. **对等身份验证（服务间身份验证）**
   - 使用 mTLS 进行服务间身份验证
   - 基于 SPIFFE ID 验证身份
   - 通过 PeerAuthentication CRD 配置

2. **请求身份验证（终端用户身份验证）**
   - 使用 JWT 令牌验证用户身份
   - 与 OAuth/OIDC 提供商集成
   - 通过 RequestAuthentication CRD 配置

![用户通过 OAuth/OIDC 提供商登录以获取 JWT，然后将令牌发送给 Istio Gateway 上的 Request Authentication。网关将验证通过的请求转发到应用，并将验证失败的请求返回给用户。](../../../.gitbook/assets/en-service-mesh-istio-security-02-authentication-0.png)

[🔍 查看交互式图示](https://www.atomai.click/kubernetes-docs/archmaps/en-service-mesh-istio-security-02-authentication-0.html)

## 请求身份验证（JWT） {#request-authentication-jwt}

### 基本 JWT 验证

```yaml
apiVersion: security.istio.io/v1
kind: RequestAuthentication
metadata:
  name: jwt-auth
  namespace: default
spec:
  selector:
    matchLabels:
      app: myapp
  jwtRules:
  - issuer: "https://accounts.google.com"
    jwksUri: "https://www.googleapis.com/oauth2/v3/certs"
    audiences: ["<your-google-client-id>"]
```

### 支持多个签发者

```yaml
apiVersion: security.istio.io/v1
kind: RequestAuthentication
metadata:
  name: multi-issuer-jwt
  namespace: default
spec:
  selector:
    matchLabels:
      app: myapp
  jwtRules:
  - issuer: "https://accounts.google.com"
    jwksUri: "https://www.googleapis.com/oauth2/v3/certs"
    audiences: ["<your-google-client-id>"]
  - issuer: "https://login.microsoftonline.com/tenant-id/v2.0"
    jwksUri: "https://login.microsoftonline.com/tenant-id/discovery/v2.0/keys"
    audiences: ["<your-api-application-client-id>"]
```

### 自定义请求头

```yaml
apiVersion: security.istio.io/v1
kind: RequestAuthentication
metadata:
  name: jwt-custom-header
  namespace: default
spec:
  selector:
    matchLabels:
      app: myapp
  jwtRules:
  - issuer: "https://auth.example.com"
    jwksUri: "https://auth.example.com/.well-known/jwks.json"
    audiences: ["my-api"]
    fromHeaders:
    - name: "x-auth-token"
      prefix: "Bearer "
```

<span id="oauthoidc-integration"></span>

## OAuth/OIDC 集成

### AWS Cognito

```yaml
apiVersion: security.istio.io/v1
kind: RequestAuthentication
metadata:
  name: cognito-jwt
  namespace: default
spec:
  selector:
    matchLabels:
      app: myapp
  jwtRules:
  - issuer: "https://cognito-idp.us-west-2.amazonaws.com/us-west-2_EXAMPLE"
    jwksUri: "https://cognito-idp.us-west-2.amazonaws.com/us-west-2_EXAMPLE/.well-known/jwks.json"
```

要通过 Cognito 访问 API，请验证 `token_use=access` 和预期的 `client_id`。ID 令牌使用 `aud` 表示应用客户端 ID；访问令牌中的 `aud` 仅在绑定资源时才会出现，因此不要将针对 ID 令牌设置的受众规则不加区分地用于访问令牌。根据需要添加特定于 API 的 scope 或 group 授权规则。请替换示例中的用户池和客户端值。

```yaml
apiVersion: security.istio.io/v1
kind: AuthorizationPolicy
metadata:
  name: cognito-access-token
  namespace: default
spec:
  selector:
    matchLabels:
      app: myapp
  action: ALLOW
  rules:
  - from:
    - source:
        requestPrincipals:
        - "https://cognito-idp.us-west-2.amazonaws.com/us-west-2_EXAMPLE/*"
    when:
    - key: request.auth.claims[token_use]
      values: ["access"]
    - key: request.auth.claims[client_id]
      values: ["<your-app-client-id>"]
```

### Keycloak

```yaml
apiVersion: security.istio.io/v1
kind: RequestAuthentication
metadata:
  name: keycloak-jwt
  namespace: default
spec:
  selector:
    matchLabels:
      app: myapp
  jwtRules:
  - issuer: "https://keycloak.example.com/realms/myrealm"
    jwksUri: "https://keycloak.example.com/realms/myrealm/protocol/openid-connect/certs"
    audiences: ["my-api"]
```

Keycloak 当前的默认上下文路径不包含 `/auth`。如果部署配置了 `http-relative-path=/auth`，则应使用该配置对应的签发者路径。

### Auth0

```yaml
apiVersion: security.istio.io/v1
kind: RequestAuthentication
metadata:
  name: auth0-jwt
  namespace: default
spec:
  selector:
    matchLabels:
      app: myapp
  jwtRules:
  - issuer: "https://your-tenant.auth0.com/"
    jwksUri: "https://your-tenant.auth0.com/.well-known/jwks.json"
    audiences:
    - "https://your-api.example.com"
```

## 实践示例 {#practical-examples}

### JWT 验证与授权

```yaml
# JWT Verification
apiVersion: security.istio.io/v1
kind: RequestAuthentication
metadata:
  name: jwt-auth
  namespace: default
spec:
  selector:
    matchLabels:
      app: myapp
  jwtRules:
  - issuer: "https://auth.example.com"
    jwksUri: "https://auth.example.com/.well-known/jwks.json"
    audiences: ["my-api"]
---
# Deny requests without JWT
apiVersion: security.istio.io/v1
kind: AuthorizationPolicy
metadata:
  name: require-jwt
  namespace: default
spec:
  selector:
    matchLabels:
      app: myapp
  action: ALLOW
  rules:
  - from:
    - source:
        requestPrincipals: ["*"]
```

## 故障排除 {#troubleshooting}

### JWT 验证失败

```bash
# 1. Check RequestAuthentication
kubectl get requestauthentication -A
kubectl describe requestauthentication <name> -n <namespace>

# 2. Decode JWT token
python3 - <<'PYJWT'
import base64, getpass, json
segment = getpass.getpass("JWT (not echoed): ").split(".")[1]
claims = json.loads(base64.urlsafe_b64decode(segment + "=" * (-len(segment) % 4)))
print({k: claims.get(k) for k in ("iss", "aud", "exp", "nbf", "token_use", "client_id")})
PYJWT

# 3. Verify JWKS endpoint
curl -fsS https://auth.example.com/.well-known/jwks.json

# 4. Check Envoy logs
kubectl logs <pod-name> -c istio-proxy -n <namespace> | grep JWT
```

解码得到的声明在签名、签发者、受众和时间检查全部通过之前都不可信。不要将有效令牌粘贴到命令历史记录或公开的解码网站中。本地 JWT 验证不会自动查询签发者的吊销状态。请分别测试无令牌、已过期令牌、签发者或受众错误以及有效令牌的情况。对于 ambient 模式下的 L7 身份验证，请使用 waypoint 的 targetRefs，而不是工作负载选择器。

## 参考资料

- [Istio 请求身份验证](https://istio.io/latest/docs/reference/config/security/request_authentication/)
- [JWT 身份验证](https://istio.io/latest/docs/tasks/security/authentication/authn-policy/)

- [主要参考资料 1](https://istio.io/latest/docs/reference/config/security/request_authentication/)
- [主要参考资料 2](https://istio.io/latest/docs/reference/config/security/authorization-policy/)
- [主要参考资料 3](https://istio.io/latest/docs/reference/config/security/peer_authentication/)
- [主要参考资料 4](https://docs.aws.amazon.com/cognito/latest/developerguide/amazon-cognito-user-pools-using-the-access-token.html)
- [主要参考资料 5](https://docs.aws.amazon.com/cognito/latest/developerguide/amazon-cognito-user-pools-using-the-id-token.html)
- [主要参考资料 6](https://www.keycloak.org/migration/migrating-to-quarkus)
- [主要参考资料 7](https://www.keycloak.org/securing-apps/oidc-layers)
