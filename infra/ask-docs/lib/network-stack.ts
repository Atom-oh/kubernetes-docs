import * as cdk from 'aws-cdk-lib'
import * as ec2 from 'aws-cdk-lib/aws-ec2'
import * as iam from 'aws-cdk-lib/aws-iam'
import * as cr from 'aws-cdk-lib/custom-resources'
import { Construct } from 'constructs'

// Private network for the docs Q&A API. No internet gateway, no NAT:
// AWS services are reached only through VPC endpoints.
export class NetworkStack extends cdk.Stack {
  public readonly vpc: ec2.Vpc
  public readonly albSecurityGroup: ec2.SecurityGroup
  public readonly lambdaSecurityGroup: ec2.SecurityGroup
  public readonly executeApiEndpoint: ec2.InterfaceVpcEndpoint
  public readonly executeApiEndpointIps: string[]

  constructor(scope: Construct, id: string, props: cdk.StackProps) {
    super(scope, id, props)
    // AWS managed prefix lists in ap-northeast-2 (verified with describe-managed-prefix-lists).
    const S3_PREFIX_LIST = 'pl-78a54011'
    const DYNAMODB_PREFIX_LIST = 'pl-48a54021'
    const CLOUDFRONT_ORIGIN_FACING_PREFIX_LIST = 'pl-22a6434b'

    this.vpc = new ec2.Vpc(this, 'Vpc', {
      ipAddresses: ec2.IpAddresses.cidr('10.240.0.0/16'),
      maxAzs: 2,
      natGateways: 0,
      subnetConfiguration: [{ name: 'isolated', subnetType: ec2.SubnetType.PRIVATE_ISOLATED, cidrMask: 24 }],
    })

    // CloudFront VPC origins require an internet gateway attached to the VPC. It only marks the
    // VPC as able to receive CloudFront traffic: no route table points to it, so the subnets stay
    // isolated (AWS docs: "The internet gateway is not used for routing traffic to origins").
    const igw = new ec2.CfnInternetGateway(this, 'VpcOriginIgw', {})
    new ec2.CfnVPCGatewayAttachment(this, 'VpcOriginIgwAttachment', {
      vpcId: this.vpc.vpcId,
      internetGatewayId: igw.ref,
    })

    this.vpc.addGatewayEndpoint('S3', {
      service: ec2.GatewayVpcEndpointAwsService.S3,
      subnets: [{ subnetType: ec2.SubnetType.PRIVATE_ISOLATED }],
    })
    this.vpc.addGatewayEndpoint('DynamoDb', {
      service: ec2.GatewayVpcEndpointAwsService.DYNAMODB,
      subnets: [{ subnetType: ec2.SubnetType.PRIVATE_ISOLATED }],
    })

    const endpointSg = new ec2.SecurityGroup(this, 'EndpointSg', {
      vpc: this.vpc,
      description: 'Bedrock runtime interface endpoint',
      allowAllOutbound: false,
    })

    this.lambdaSecurityGroup = new ec2.SecurityGroup(this, 'LambdaSg', {
      vpc: this.vpc,
      description: 'Ask-docs Lambda: egress only to endpoints and S3',
      allowAllOutbound: false,
    })
    this.lambdaSecurityGroup.addEgressRule(endpointSg, ec2.Port.tcp(443), 'Bedrock runtime endpoint')
    this.lambdaSecurityGroup.addEgressRule(
      ec2.Peer.prefixList(S3_PREFIX_LIST),
      ec2.Port.tcp(443),
      'S3 gateway endpoint'
    )
    this.lambdaSecurityGroup.addEgressRule(
      ec2.Peer.prefixList(DYNAMODB_PREFIX_LIST),
      ec2.Port.tcp(443),
      'DynamoDB gateway endpoint'
    )
    endpointSg.addIngressRule(this.lambdaSecurityGroup, ec2.Port.tcp(443), 'from ask-docs Lambda')

    new ec2.InterfaceVpcEndpoint(this, 'BedrockRuntime', {
      vpc: this.vpc,
      service: new ec2.InterfaceVpcEndpointService(`com.amazonaws.${this.region}.bedrock-runtime`, 443),
      subnets: { subnetType: ec2.SubnetType.PRIVATE_ISOLATED },
      privateDnsEnabled: true,
      securityGroups: [endpointSg],
    })

    // Internal ALB: only CloudFront origin-facing addresses may reach it (CLAUDE.md allows the
    // CloudFront managed prefix list). Egress only to the execute-api endpoint below.
    this.albSecurityGroup = new ec2.SecurityGroup(this, 'AlbSg', {
      vpc: this.vpc,
      description: 'Internal ALB for ask-docs: CloudFront origin-facing only',
      allowAllOutbound: false,
    })
    this.albSecurityGroup.addIngressRule(
      ec2.Peer.prefixList(CLOUDFRONT_ORIGIN_FACING_PREFIX_LIST),
      ec2.Port.tcp(443),
      'CloudFront origin-facing'
    )

    // An ALB Lambda target cannot stream a response, so the ALB forwards the API to a private API
    // Gateway (STREAM transfer mode) through this endpoint's ENIs. Private DNS stays off: nothing in
    // the VPC calls execute-api by name, and the ALB sets the API's Host header itself.
    const apiEndpointSg = new ec2.SecurityGroup(this, 'ApiEndpointSg', {
      vpc: this.vpc,
      description: 'execute-api interface endpoint: from the internal ALB only',
      allowAllOutbound: false,
    })
    apiEndpointSg.addIngressRule(this.albSecurityGroup, ec2.Port.tcp(443), 'from the internal ALB')
    this.albSecurityGroup.addEgressRule(apiEndpointSg, ec2.Port.tcp(443), 'execute-api endpoint')
    this.executeApiEndpoint = new ec2.InterfaceVpcEndpoint(this, 'ExecuteApi', {
      vpc: this.vpc,
      service: ec2.InterfaceVpcEndpointAwsService.APIGATEWAY,
      subnets: { subnetType: ec2.SubnetType.PRIVATE_ISOLATED },
      privateDnsEnabled: false,
      securityGroups: [apiEndpointSg],
      open: false, // no VPC-CIDR ingress; only the ALB rule above
    })
    // The endpoint picks the API by Host or x-apigw-api-id header, so it must not be usable for any
    // other private API: only this account's ask route. (The API id lives in AskDocsApp, which depends
    // on this stack, hence the stage/route match instead of the exact id.)
    this.executeApiEndpoint.addToPolicy(
      new iam.PolicyStatement({
        principals: [new iam.AnyPrincipal()],
        actions: ['execute-api:Invoke'],
        resources: [`arn:aws:execute-api:${this.region}:${this.account}:*/kubernetes-docs/POST/api/ask`],
      })
    )

    // The ALB target group takes IP addresses, so look up the endpoint ENIs' private IPs (one per AZ).
    const endpointEnis = new cr.AwsCustomResource(this, 'ExecuteApiEndpointIps', {
      onUpdate: {
        service: 'EC2',
        action: 'describeNetworkInterfaces',
        parameters: { NetworkInterfaceIds: this.executeApiEndpoint.vpcEndpointNetworkInterfaceIds },
        physicalResourceId: cr.PhysicalResourceId.of(this.executeApiEndpoint.vpcEndpointId),
        outputPaths: ['NetworkInterfaces.0.PrivateIpAddress', 'NetworkInterfaces.1.PrivateIpAddress'],
      },
      policy: cr.AwsCustomResourcePolicy.fromStatements([
        new iam.PolicyStatement({ actions: ['ec2:DescribeNetworkInterfaces'], resources: ['*'] }),
      ]),
      installLatestAwsSdk: false,
    })
    this.executeApiEndpointIps = [0, 1].map((i) => endpointEnis.getResponseField(`NetworkInterfaces.${i}.PrivateIpAddress`))

    new cdk.CfnOutput(this, 'VpcId', { value: this.vpc.vpcId })
  }
}
