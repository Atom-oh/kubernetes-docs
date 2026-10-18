import * as cdk from 'aws-cdk-lib'
import * as acm from 'aws-cdk-lib/aws-certificatemanager'
import * as cloudfront from 'aws-cdk-lib/aws-cloudfront'
import * as origins from 'aws-cdk-lib/aws-cloudfront-origins'
import * as ec2 from 'aws-cdk-lib/aws-ec2'
import * as elbv2 from 'aws-cdk-lib/aws-elasticloadbalancingv2'
import * as route53 from 'aws-cdk-lib/aws-route53'
import * as wafv2 from 'aws-cdk-lib/aws-wafv2'
import { Construct } from 'constructs'

export interface EdgeStackProps extends cdk.StackProps {
  albArn: string
  albSgId: string
  albDnsName: string
  vpcId: string
}

// CloudFront (global) with WAF. GitHub Pages stays the default origin; /kubernetes-docs/api/*
// goes to the internal ALB through a VPC origin. Lives in us-east-1 for ACM and WAF scope.
export class EdgeStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props: EdgeStackProps) {
    super(scope, id, props)

    const apiPath = '/kubernetes-docs/api/'
    const apiMatch = (name: string) => ({
      byteMatchStatement: {
        searchString: apiPath,
        fieldToMatch: { uriPath: {} },
        positionalConstraint: 'STARTS_WITH',
        textTransformations: [{ priority: 0, type: 'NONE' }],
      },
    })

    const waf = new wafv2.CfnWebACL(this, 'DocsApiWaf', {
      scope: 'CLOUDFRONT',
      defaultAction: { allow: {} },
      visibilityConfig: { cloudWatchMetricsEnabled: true, metricName: 'AskDocsWaf', sampledRequestsEnabled: true },
      rules: [
        {
          name: 'AskApiRateLimit',
          priority: 1,
          action: { block: {} },
          statement: {
            rateBasedStatement: {
              limit: 100,
              aggregateKeyType: 'IP',
              scopeDownStatement: apiMatch('rate'),
            },
          },
          visibilityConfig: { cloudWatchMetricsEnabled: true, metricName: 'AskApiRateLimit', sampledRequestsEnabled: true },
        },
        {
          name: 'AskApiBodyLimit',
          priority: 2,
          action: { block: {} },
          statement: {
            andStatement: {
              statements: [
                apiMatch('body'),
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
            managedRuleGroupStatement: {
              vendorName: 'AWS',
              name: 'AWSManagedRulesCommonRuleSet',
              scopeDownStatement: apiMatch('common'),
            },
          },
          visibilityConfig: { cloudWatchMetricsEnabled: true, metricName: 'AskApiCommon', sampledRequestsEnabled: true },
        },
      ],
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

    const wwwZone = route53.HostedZone.fromHostedZoneAttributes(this, 'PublicZone', {
      zoneName: 'atomai.click',
      hostedZoneId: this.node.tryGetContext('publicZoneId') as string,
    })
    const wwwCert = new acm.Certificate(this, 'WwwCert', {
      domainName: 'www.atomai.click',
      validation: acm.CertificateValidation.fromDns(wwwZone),
    })

    const apiOrigin = origins.VpcOrigin.withApplicationLoadBalancer(alb, {
      protocolPolicy: cloudfront.OriginProtocolPolicy.HTTPS_ONLY,
      httpsPort: 443,
      originSslProtocols: [cloudfront.OriginSslPolicy.TLS_V1_2],
      vpcOriginName: 'ask-docs-internal-alb',
    })

    const distribution = new cloudfront.Distribution(this, 'DocsDistribution', {
      comment: 'docs site (GitHub Pages) + /kubernetes-docs/api/* (internal ALB)',
      domainNames: ['www.atomai.click'],
      certificate: wwwCert,
      priceClass: cloudfront.PriceClass.PRICE_CLASS_200,
      webAclId: waf.attrArn,
      defaultBehavior: {
        origin: new origins.HttpOrigin('atom-oh.github.io', {
          protocolPolicy: cloudfront.OriginProtocolPolicy.HTTPS_ONLY,
        }),
        viewerProtocolPolicy: cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
        allowedMethods: cloudfront.AllowedMethods.ALLOW_GET_HEAD,
        cachePolicy: cloudfront.CachePolicy.CACHING_OPTIMIZED,
        originRequestPolicy: cloudfront.OriginRequestPolicy.ALL_VIEWER,
      },
      additionalBehaviors: {
        '/kubernetes-docs/api/*': {
          origin: apiOrigin,
          viewerProtocolPolicy: cloudfront.ViewerProtocolPolicy.HTTPS_ONLY,
          allowedMethods: cloudfront.AllowedMethods.ALLOW_ALL,
          cachePolicy: cloudfront.CachePolicy.CACHING_DISABLED,
          originRequestPolicy: cloudfront.OriginRequestPolicy.ALL_VIEWER,
        },
      },
    })

    new cdk.CfnOutput(this, 'DistributionDomain', { value: distribution.distributionDomainName })
    new cdk.CfnOutput(this, 'DistributionId', { value: distribution.distributionId })
  }
}
