import * as cdk from 'aws-cdk-lib'
import * as acm from 'aws-cdk-lib/aws-certificatemanager'
import * as cloudfront from 'aws-cdk-lib/aws-cloudfront'
import * as origins from 'aws-cdk-lib/aws-cloudfront-origins'
import * as ec2 from 'aws-cdk-lib/aws-ec2'
import * as elbv2 from 'aws-cdk-lib/aws-elasticloadbalancingv2'
import * as iam from 'aws-cdk-lib/aws-iam'
import * as route53 from 'aws-cdk-lib/aws-route53'
import * as route53Targets from 'aws-cdk-lib/aws-route53-targets'
import * as s3 from 'aws-cdk-lib/aws-s3'
import * as wafv2 from 'aws-cdk-lib/aws-wafv2'
import { Construct } from 'constructs'

export interface EdgeStackProps extends cdk.StackProps {
  albArn: string
  albSgId: string
  albDnsName: string
  vpcId: string
}

const DOMAIN = 'docs.atomai.click'
const SITE_PREFIX = 'kubernetes-docs'
const INDEX_BUCKET = 'atomai-ask-docs-180294183052-ap-northeast-2'
const GITHUB_REPO = 'Atom-oh/kubernetes-docs'

// docs.atomai.click: CloudFront (global) with WAF. The static site comes from a private S3 bucket
// (OAC); /kubernetes-docs/api/* goes to the internal ALB through a VPC origin. The existing
// www.atomai.click (GitHub Pages) is not touched. Lives in us-east-1 for ACM and WAF scope.
export class EdgeStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props: EdgeStackProps) {
    super(scope, id, props)

    const apiMatch = {
      byteMatchStatement: {
        searchString: `/${SITE_PREFIX}/api/`,
        fieldToMatch: { uriPath: {} },
        positionalConstraint: 'STARTS_WITH',
        textTransformations: [{ priority: 0, type: 'NONE' }],
      },
    }

    const waf = new wafv2.CfnWebACL(this, 'DocsApiWaf', {
      scope: 'CLOUDFRONT',
      defaultAction: { allow: {} },
      visibilityConfig: { cloudWatchMetricsEnabled: true, metricName: 'AskDocsWaf', sampledRequestsEnabled: true },
      rules: [
        {
          name: 'AskApiRateLimit',
          priority: 1,
          action: { block: {} },
          statement: { rateBasedStatement: { limit: 100, aggregateKeyType: 'IP', scopeDownStatement: apiMatch } },
          visibilityConfig: { cloudWatchMetricsEnabled: true, metricName: 'AskApiRateLimit', sampledRequestsEnabled: true },
        },
        {
          name: 'AskApiBodyLimit',
          priority: 2,
          action: { block: {} },
          statement: {
            andStatement: {
              statements: [
                apiMatch,
                {
                  sizeConstraintStatement: {
                    fieldToMatch: { body: { oversizeHandling: 'CONTINUE' } },
                    comparisonOperator: 'GT',
                    size: 4096,
                    textTransformations: [{ priority: 0, type: 'NONE' }],
                  },
                },
              ],
            },
          },
          visibilityConfig: { cloudWatchMetricsEnabled: true, metricName: 'AskApiBodyLimit', sampledRequestsEnabled: true },
        },
        {
          name: 'AskApiManagedCommon',
          priority: 3,
          overrideAction: { none: {} },
          statement: {
            managedRuleGroupStatement: { vendorName: 'AWS', name: 'AWSManagedRulesCommonRuleSet', scopeDownStatement: apiMatch },
          },
          visibilityConfig: { cloudWatchMetricsEnabled: true, metricName: 'AskApiCommon', sampledRequestsEnabled: true },
        },
      ],
    })

    const zone = route53.HostedZone.fromHostedZoneAttributes(this, 'PublicZone', {
      zoneName: 'atomai.click',
      hostedZoneId: this.node.tryGetContext('publicZoneId') as string,
    })
    const cert = new acm.Certificate(this, 'DocsCert', {
      domainName: DOMAIN,
      validation: acm.CertificateValidation.fromDns(zone),
    })

    const siteBucket = new s3.Bucket(this, 'SiteBucket', {
      bucketName: `atomai-docs-site-${this.account}-${this.region}`,
      encryption: s3.BucketEncryption.S3_MANAGED,
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
      enforceSSL: true,
      objectOwnership: s3.ObjectOwnership.BUCKET_OWNER_ENFORCED,
      removalPolicy: cdk.RemovalPolicy.RETAIN,
    })

    // VitePress builds with cleanUrls: /a/b -> a/b.html, /a/ -> a/index.html. GitHub Pages does this
    // mapping itself; S3 does not, so a viewer-request function does it at the edge.
    const cleanUrls = new cloudfront.Function(this, 'CleanUrls', {
      runtime: cloudfront.FunctionRuntime.JS_2_0,
      code: cloudfront.FunctionCode.fromInline(`
function handler(event) {
  var request = event.request;
  var uri = request.uri;
  if (uri === '/' || uri === '/${SITE_PREFIX}') {
    return { statusCode: 301, statusDescription: 'Moved Permanently', headers: { location: { value: '/${SITE_PREFIX}/' } } };
  }
  if (uri.endsWith('/')) {
    request.uri = uri + 'index.html';
  } else if (uri.split('/').pop().indexOf('.') === -1) {
    request.uri = uri + '.html';
  }
  return request;
}`),
    })

    const alb = elbv2.ApplicationLoadBalancer.fromApplicationLoadBalancerAttributes(this, 'AskAlb', {
      loadBalancerArn: props.albArn,
      loadBalancerDnsName: props.albDnsName,
      securityGroupId: props.albSgId,
      vpc: ec2.Vpc.fromVpcAttributes(this, 'AskVpc', {
        vpcId: props.vpcId,
        vpcCidrBlock: '10.240.0.0/16',
        availabilityZones: ['ap-northeast-2a', 'ap-northeast-2b'], // the subnets CDK created (maxAzs: 2)
      }),
    })
    const apiOrigin = origins.VpcOrigin.withApplicationLoadBalancer(alb, {
      protocolPolicy: cloudfront.OriginProtocolPolicy.HTTPS_ONLY,
      httpsPort: 443,
      originSslProtocols: [cloudfront.OriginSslPolicy.TLS_V1_2],
      vpcOriginName: 'ask-docs-internal-alb',
      // The ALB certificate is for ask-origin.aws.atomai.click, so CloudFront connects with that name.
      domainName: 'ask-origin.aws.atomai.click',
    })

    const distribution = new cloudfront.Distribution(this, 'DocsDistribution', {
      comment: 'docs.atomai.click: kubernetes-docs site (S3) + /kubernetes-docs/api/* (internal ALB)',
      domainNames: [DOMAIN],
      certificate: cert,
      priceClass: cloudfront.PriceClass.PRICE_CLASS_200,
      webAclId: waf.attrArn,
      defaultBehavior: {
        origin: origins.S3BucketOrigin.withOriginAccessControl(siteBucket),
        viewerProtocolPolicy: cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
        allowedMethods: cloudfront.AllowedMethods.ALLOW_GET_HEAD,
        cachePolicy: cloudfront.CachePolicy.CACHING_OPTIMIZED,
        responseHeadersPolicy: cloudfront.ResponseHeadersPolicy.SECURITY_HEADERS,
        compress: true,
        functionAssociations: [{ function: cleanUrls, eventType: cloudfront.FunctionEventType.VIEWER_REQUEST }],
      },
      additionalBehaviors: {
        [`/${SITE_PREFIX}/api/*`]: {
          origin: apiOrigin,
          viewerProtocolPolicy: cloudfront.ViewerProtocolPolicy.HTTPS_ONLY,
          allowedMethods: cloudfront.AllowedMethods.ALLOW_ALL,
          cachePolicy: cloudfront.CachePolicy.CACHING_DISABLED,
          originRequestPolicy: cloudfront.OriginRequestPolicy.ALL_VIEWER_EXCEPT_HOST_HEADER,
          // Answers stream as server-sent events; do not hold them back for compression.
          compress: false,
        },
      },
      errorResponses: [
        // A missing S3 key returns 403 through OAC.
        { httpStatus: 403, responseHttpStatus: 404, responsePagePath: `/${SITE_PREFIX}/404.html`, ttl: cdk.Duration.minutes(1) },
        { httpStatus: 404, responseHttpStatus: 404, responsePagePath: `/${SITE_PREFIX}/404.html`, ttl: cdk.Duration.minutes(1) },
      ],
    })

    for (const [id, recordType] of [['DocsA', route53.RecordType.A], ['DocsAAAA', route53.RecordType.AAAA]] as const) {
      const props = { zone, recordName: 'docs', target: route53.RecordTarget.fromAlias(new route53Targets.CloudFrontTarget(distribution)) }
      if (recordType === route53.RecordType.A) new route53.ARecord(this, id, props)
      else new route53.AaaaRecord(this, id, props)
    }

    // GitHub Actions (main branch only) deploys the built site and the Q&A index with OIDC, no keys.
    const deployRole = new iam.Role(this, 'GithubDeployRole', {
      roleName: 'kubernetes-docs-github-deploy',
      assumedBy: new iam.WebIdentityPrincipal(
        `arn:aws:iam::${this.account}:oidc-provider/token.actions.githubusercontent.com`,
        {
          StringEquals: { 'token.actions.githubusercontent.com:aud': 'sts.amazonaws.com' },
          StringLike: { 'token.actions.githubusercontent.com:sub': `repo:${GITHUB_REPO}:ref:refs/heads/main` },
        }
      ),
      maxSessionDuration: cdk.Duration.hours(1),
    })
    deployRole.addToPolicy(new iam.PolicyStatement({ actions: ['s3:ListBucket'], resources: [siteBucket.bucketArn] }))
    deployRole.addToPolicy(
      new iam.PolicyStatement({
        actions: ['s3:GetObject', 's3:PutObject', 's3:DeleteObject'],
        resources: [siteBucket.arnForObjects(`${SITE_PREFIX}/*`)],
      })
    )
    deployRole.addToPolicy(
      new iam.PolicyStatement({ actions: ['s3:PutObject'], resources: [`arn:aws:s3:::${INDEX_BUCKET}/index/*`] })
    )
    deployRole.addToPolicy(
      new iam.PolicyStatement({
        actions: ['cloudfront:CreateInvalidation'],
        resources: [`arn:aws:cloudfront::${this.account}:distribution/${distribution.distributionId}`],
      })
    )

    new cdk.CfnOutput(this, 'DistributionDomain', { value: distribution.distributionDomainName })
    new cdk.CfnOutput(this, 'DistributionId', { value: distribution.distributionId })
    new cdk.CfnOutput(this, 'SiteBucketName', { value: siteBucket.bucketName })
    new cdk.CfnOutput(this, 'DeployRoleArn', { value: deployRole.roleArn })
  }
}
