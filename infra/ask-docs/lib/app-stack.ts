import * as cdk from 'aws-cdk-lib'
import * as acm from 'aws-cdk-lib/aws-certificatemanager'
import * as dynamodb from 'aws-cdk-lib/aws-dynamodb'
import * as ec2 from 'aws-cdk-lib/aws-ec2'
import * as elbv2 from 'aws-cdk-lib/aws-elasticloadbalancingv2'
import * as elbv2Targets from 'aws-cdk-lib/aws-elasticloadbalancingv2-targets'
import * as iam from 'aws-cdk-lib/aws-iam'
import * as lambda from 'aws-cdk-lib/aws-lambda'
import * as logs from 'aws-cdk-lib/aws-logs'
import * as route53 from 'aws-cdk-lib/aws-route53'
import * as route53Targets from 'aws-cdk-lib/aws-route53-targets'
import * as s3 from 'aws-cdk-lib/aws-s3'
import { Construct } from 'constructs'
import * as path from 'path'

export interface AppStackProps extends cdk.StackProps {
  vpc: ec2.IVpc
  albSecurityGroup: ec2.ISecurityGroup
  lambdaSecurityGroup: ec2.ISecurityGroup
  bucket: s3.IBucket
  conversationTable: dynamodb.ITableV2
}

// Internal ALB -> Lambda target group -> ask-docs Lambda. No public IP, no public listener.
export class AppStack extends cdk.Stack {
  public readonly alb: elbv2.ApplicationLoadBalancer

  constructor(scope: Construct, id: string, props: AppStackProps) {
    super(scope, id, props)
    const modelId = this.node.tryGetContext('modelId') as string
    const appZone = route53.HostedZone.fromHostedZoneAttributes(this, 'AppZone', {
      zoneName: 'aws.atomai.click',
      hostedZoneId: this.node.tryGetContext('appZoneId') as string,
    })

    const fn = new lambda.Function(this, 'AskFunction', {
      runtime: lambda.Runtime.PYTHON_3_13,
      architecture: lambda.Architecture.ARM_64,
      handler: 'app.handler',
      code: lambda.Code.fromAsset(path.join(__dirname, '..', 'lambda', 'ask')),
      memorySize: 2048, // BM25 counters for ~23k chunks; measure and right-size after first deploy
      timeout: cdk.Duration.seconds(25),
      reservedConcurrentExecutions: 10,
      vpc: props.vpc,
      vpcSubnets: { subnetType: ec2.SubnetType.PRIVATE_ISOLATED },
      securityGroups: [props.lambdaSecurityGroup],
      logGroup: new logs.LogGroup(this, 'AskLogs', { retention: logs.RetentionDays.TWO_WEEKS, removalPolicy: cdk.RemovalPolicy.DESTROY }),
      environment: {
        INDEX_BUCKET: props.bucket.bucketName,
        INDEX_PREFIX: 'index/',
        MODEL_ID: modelId,
        MAX_QUESTION_CHARS: '500',
        MAX_OUTPUT_TOKENS: '800',
        TOP_K: '6',
        CONVERSATION_TABLE: props.conversationTable.tableName,
      },
    })
    props.bucket.grantRead(fn, 'index/*')
    props.conversationTable.grant(fn, 'dynamodb:GetItem', 'dynamodb:PutItem')
    fn.addToRolePolicy(
      new iam.PolicyStatement({
        actions: ['bedrock:InvokeModel'],
        resources: [
          `arn:aws:bedrock:*:${this.account}:inference-profile/global.anthropic.claude-haiku-5-5`,
          'arn:aws:bedrock:*::foundation-model/anthropic.claude-haiku-5-5',
        ],
      })
    )

    this.alb = new elbv2.ApplicationLoadBalancer(this, 'Alb', {
      vpc: props.vpc,
      internetFacing: false,
      securityGroup: props.albSecurityGroup,
      vpcSubnets: { subnetType: ec2.SubnetType.PRIVATE_ISOLATED },
      idleTimeout: cdk.Duration.seconds(60),
    })

    const originCert = new acm.Certificate(this, 'OriginCert', {
      domainName: 'ask-origin.aws.atomai.click',
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

    const tg = new elbv2.ApplicationTargetGroup(this, 'AskTargetGroup', {
      targetType: elbv2.TargetType.LAMBDA,
      targets: [new elbv2Targets.LambdaTarget(fn)],
    })

    https.addAction('AskApi', {
      priority: 10,
      conditions: [elbv2.ListenerCondition.pathPatterns(['/kubernetes-docs/api/*'])],
      action: elbv2.ListenerAction.forward([tg]),
    })

    new route53.ARecord(this, 'OriginAlias', {
      zone: appZone,
      recordName: 'ask-origin',
      target: route53.RecordTarget.fromAlias(new route53Targets.LoadBalancerTarget(this.alb)),
    })

    new cdk.CfnOutput(this, 'AlbArn', { value: this.alb.loadBalancerArn })
    new cdk.CfnOutput(this, 'AlbSecurityGroupId', { value: props.albSecurityGroup.securityGroupId })
    new cdk.CfnOutput(this, 'VpcId', { value: props.vpc.vpcId })
    new cdk.CfnOutput(this, 'FunctionName', { value: fn.functionName })
  }
}
