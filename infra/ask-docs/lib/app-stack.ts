import * as cdk from 'aws-cdk-lib'
import * as acm from 'aws-cdk-lib/aws-certificatemanager'
import * as apigw from 'aws-cdk-lib/aws-apigateway'
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
  executeApiEndpoint: ec2.IInterfaceVpcEndpoint
  executeApiEndpointIps: string[]
}

// AWS Lambda Web Adapter (awslabs/aws-lambda-web-adapter, AWS-published layer), arm64 v1.1.0.
const WEB_ADAPTER_LAYER_VERSION = 30

// Internal ALB -> execute-api VPC endpoint -> private REST API (STREAM) -> ask-docs Lambda, so answers
// stream to the browser as Bedrock writes them; an ALB Lambda target cannot stream. No public IP, no
// public listener, and the API accepts only requests through that endpoint.
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
      // run.sh starts lambda/ask/server.py; the adapter forwards each request to it and streams the
      // response back (InvokeWithResponseStream).
      handler: 'run.sh',
      code: lambda.Code.fromAsset(path.join(__dirname, '..', 'lambda', 'ask'), { exclude: ['__pycache__'] }),
      layers: [
        lambda.LayerVersion.fromLayerVersionArn(
          this,
          'WebAdapter',
          `arn:aws:lambda:${this.region}:753240598075:layer:LambdaAdapterLayerArm64:${WEB_ADAPTER_LAYER_VERSION}`
        ),
      ],
      memorySize: 2048, // BM25 counters for ~23k chunks; measure and right-size after first deploy
      timeout: cdk.Duration.seconds(60), // a streamed answer can run past API Gateway's 29s buffered limit
      reservedConcurrentExecutions: 10,
      vpc: props.vpc,
      vpcSubnets: { subnetType: ec2.SubnetType.PRIVATE_ISOLATED },
      securityGroups: [props.lambdaSecurityGroup],
      logGroup: new logs.LogGroup(this, 'AskLogs', { retention: logs.RetentionDays.TWO_WEEKS, removalPolicy: cdk.RemovalPolicy.DESTROY }),
      environment: {
        AWS_LAMBDA_EXEC_WRAPPER: '/opt/bootstrap',
        AWS_LWA_INVOKE_MODE: 'response_stream',
        AWS_LWA_PORT: '8080',
        AWS_LWA_READINESS_CHECK_PATH: '/healthz',
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
        // Converse for the query rewrite and rerank, ConverseStream for the answer.
        actions: ['bedrock:InvokeModel', 'bedrock:InvokeModelWithResponseStream'],
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

    // The stage is named after the site prefix, so /kubernetes-docs/api/ask reaches resource /api/ask
    // without a path rewrite.
    const api = new apigw.RestApi(this, 'AskApi', {
      restApiName: 'ask-docs',
      description: 'docs Q&A: private, reached only through the execute-api VPC endpoint behind the internal ALB',
      endpointConfiguration: { types: [apigw.EndpointType.PRIVATE], vpcEndpoints: [props.executeApiEndpoint] },
      policy: new iam.PolicyDocument({
        statements: [
          new iam.PolicyStatement({
            principals: [new iam.AnyPrincipal()],
            actions: ['execute-api:Invoke'],
            resources: ['execute-api:/*'],
            conditions: { StringEquals: { 'aws:SourceVpce': props.executeApiEndpoint.vpcEndpointId } },
          }),
        ],
      }),
      cloudWatchRole: false,
      deployOptions: { stageName: 'kubernetes-docs', throttlingRateLimit: 10, throttlingBurstLimit: 20 },
    })
    api.root
      .addResource('api')
      .addResource('ask')
      .addMethod(
        'POST',
        new apigw.LambdaIntegration(fn, {
          responseTransferMode: apigw.ResponseTransferMode.STREAM,
          timeout: cdk.Duration.seconds(60),
          allowTestInvoke: false,
        })
      )

    const tg = new elbv2.ApplicationTargetGroup(this, 'AskApiTargets', {
      vpc: props.vpc,
      targetType: elbv2.TargetType.IP,
      protocol: elbv2.ApplicationProtocol.HTTPS,
      port: 443,
      targets: props.executeApiEndpointIps.map((ip) => new elbv2Targets.IpTarget(ip, 443)),
      // The endpoint answers a bare health check (no API Host header) with 403, which still shows
      // it is up.
      healthCheck: { protocol: elbv2.Protocol.HTTPS, path: '/', healthyHttpCodes: '200-499' },
    })

    https.addAction('AskApi', {
      priority: 10,
      conditions: [elbv2.ListenerCondition.pathPatterns(['/kubernetes-docs/api/*'])],
      action: elbv2.ListenerAction.forward([tg]),
    })
    // The endpoint picks the private API by Host header; CloudFront sends ask-origin.aws.atomai.click.
    const rule = https.node.findChild('AskApiRule').node.defaultChild as elbv2.CfnListenerRule
    rule.transforms = [
      {
        type: 'host-header-rewrite',
        hostHeaderRewriteConfig: {
          rewrites: [{ regex: '^.*$', replace: `${api.restApiId}.execute-api.${this.region}.amazonaws.com` }],
        },
      },
    ]

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
