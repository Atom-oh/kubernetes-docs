import * as cdk from 'aws-cdk-lib'
import * as acm from 'aws-cdk-lib/aws-certificatemanager'
import * as dynamodb from 'aws-cdk-lib/aws-dynamodb'
import * as ec2 from 'aws-cdk-lib/aws-ec2'
import * as ecr from 'aws-cdk-lib/aws-ecr'
import * as eks from 'aws-cdk-lib/aws-eks'
import * as elbv2 from 'aws-cdk-lib/aws-elasticloadbalancingv2'
import * as iam from 'aws-cdk-lib/aws-iam'
import * as route53 from 'aws-cdk-lib/aws-route53'
import * as route53Targets from 'aws-cdk-lib/aws-route53-targets'
import * as s3 from 'aws-cdk-lib/aws-s3'
import { Construct } from 'constructs'

export interface AppStackProps extends cdk.StackProps {
  vpc: ec2.IVpc
  albSecurityGroup: ec2.ISecurityGroup
  bucket: s3.IBucket
  conversationTable: dynamodb.ITableV2
}

export const ASK_NAMESPACE = 'ask-docs'
export const ASK_SERVICE_ACCOUNT = 'ask-docs'

// Internal ALB -> IP target group -> ask-docs pods on the demo EKS cluster (k8s/ask-docs.yaml binds the
// pods to the target group). The ALB streams server-sent events straight from the pod, and the pods
// stay warm, so there is no cold start. No public IP, no public listener.
export class AppStack extends cdk.Stack {
  public readonly alb: elbv2.ApplicationLoadBalancer

  constructor(scope: Construct, id: string, props: AppStackProps) {
    super(scope, id, props)
    const appZone = route53.HostedZone.fromHostedZoneAttributes(this, 'AppZone', {
      zoneName: 'aws.atomai.click',
      hostedZoneId: this.node.tryGetContext('appZoneId') as string,
    })
    const clusterName = this.node.tryGetContext('demoClusterName') as string
    if (typeof clusterName !== 'string' || !clusterName.trim()) {
      throw new Error('context "demoClusterName" is required; pass -c demoClusterName=... from a private context file outside Git')
    }

    // Created ahead of the first deploy (scan on push, keep the last 10 images) so the image can be
    // pushed before the Lambda is retired; the stack only refers to it.
    const repo = ecr.Repository.fromRepositoryName(this, 'ServerImages', 'ask-docs/server')

    // Pod Identity role for the pods' service account: the permissions the Lambda role had.
    const podRole = new iam.Role(this, 'PodRole', {
      assumedBy: new iam.ServicePrincipal('pods.eks.amazonaws.com').withSessionTags(),
      description: 'ask-docs pods (Pod Identity): index read, conversation table, Bedrock Haiku',
    })
    props.bucket.grantRead(podRole, 'index/*')
    props.conversationTable.grant(podRole, 'dynamodb:GetItem', 'dynamodb:PutItem')
    podRole.addToPolicy(
      new iam.PolicyStatement({
        // Converse for the query rewrite and rerank, ConverseStream for the answer.
        actions: ['bedrock:InvokeModel', 'bedrock:InvokeModelWithResponseStream'],
        resources: [
          `arn:aws:bedrock:*:${this.account}:inference-profile/global.anthropic.claude-haiku-5-5`,
          'arn:aws:bedrock:*::foundation-model/anthropic.claude-haiku-5-5',
        ],
      })
    )
    new eks.CfnPodIdentityAssociation(this, 'PodIdentity', {
      clusterName,
      namespace: ASK_NAMESPACE,
      serviceAccount: ASK_SERVICE_ACCOUNT,
      roleArn: podRole.roleArn,
    })

    this.alb = new elbv2.ApplicationLoadBalancer(this, 'Alb', {
      vpc: props.vpc,
      internetFacing: false,
      securityGroup: props.albSecurityGroup,
      vpcSubnets: { subnetType: ec2.SubnetType.PRIVATE_ISOLATED },
      idleTimeout: cdk.Duration.seconds(60),
    })

    const originCert = new acm.Certificate(this, 'OriginCert', {
      domainName: 'ask-origin-demo.aws.atomai.click',
      validation: acm.CertificateValidation.fromDns(appZone),
    })

    const https = this.alb.addListener('Https', {
      port: 443,
      open: false, // do not let CDK add 0.0.0.0/0 to the ALB security group
      protocol: elbv2.ApplicationProtocol.HTTPS,
      certificates: [elbv2.ListenerCertificate.fromCertificateManager(originCert)],
      sslPolicy: elbv2.SslPolicy.RECOMMENDED_TLS,
      defaultAction: elbv2.ListenerAction.fixedResponse(404, { contentType: 'text/plain', messageBody: 'not found' }),
    })

    // Empty IP target group: the AWS Load Balancer Controller registers the pods (TargetGroupBinding).
    const tg = new elbv2.ApplicationTargetGroup(this, 'AskPodTargets', {
      vpc: props.vpc,
      targetType: elbv2.TargetType.IP,
      protocol: elbv2.ApplicationProtocol.HTTP,
      port: 8080,
      healthCheck: { protocol: elbv2.Protocol.HTTP, path: '/healthz', healthyHttpCodes: '200' },
      deregistrationDelay: cdk.Duration.seconds(30),
    })
    https.addAction('AskApi', {
      priority: 10,
      conditions: [elbv2.ListenerCondition.pathPatterns(['/kubernetes-docs/api/*'])],
      action: elbv2.ListenerAction.forward([tg]),
    })

    new route53.ARecord(this, 'OriginAlias', {
      zone: appZone,
      recordName: 'ask-origin-demo',
      target: route53.RecordTarget.fromAlias(new route53Targets.LoadBalancerTarget(this.alb)),
    })

    new cdk.CfnOutput(this, 'AlbArn', { value: this.alb.loadBalancerArn })
    new cdk.CfnOutput(this, 'AlbSecurityGroupId', { value: props.albSecurityGroup.securityGroupId })
    new cdk.CfnOutput(this, 'VpcId', { value: props.vpc.vpcId })
    new cdk.CfnOutput(this, 'TargetGroupArn', { value: tg.targetGroupArn })
    new cdk.CfnOutput(this, 'ImageRepository', { value: repo.repositoryUri })
    new cdk.CfnOutput(this, 'PodRoleArn', { value: podRole.roleArn })
  }
}
