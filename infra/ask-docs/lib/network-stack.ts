import * as cdk from 'aws-cdk-lib'
import * as ec2 from 'aws-cdk-lib/aws-ec2'
import { Construct } from 'constructs'

// Private network for the docs Q&A API. No internet gateway, no NAT:
// AWS services are reached only through VPC endpoints.
export class NetworkStack extends cdk.Stack {
  public readonly vpc: ec2.Vpc
  public readonly albSecurityGroup: ec2.SecurityGroup
  public readonly lambdaSecurityGroup: ec2.SecurityGroup

  constructor(scope: Construct, id: string, props: cdk.StackProps) {
    super(scope, id, props)
    // AWS managed prefix lists in ap-northeast-2 (verified with describe-managed-prefix-lists).
    const S3_PREFIX_LIST = 'pl-78a54011'
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
    endpointSg.addIngressRule(this.lambdaSecurityGroup, ec2.Port.tcp(443), 'from ask-docs Lambda')

    new ec2.InterfaceVpcEndpoint(this, 'BedrockRuntime', {
      vpc: this.vpc,
      service: new ec2.InterfaceVpcEndpointService(`com.amazonaws.${this.region}.bedrock-runtime`, 443),
      subnets: { subnetType: ec2.SubnetType.PRIVATE_ISOLATED },
      privateDnsEnabled: true,
      securityGroups: [endpointSg],
    })

    // Internal ALB: only CloudFront origin-facing addresses may reach it (CLAUDE.md allows the
    // CloudFront managed prefix list). Egress is restricted to the Lambda target path.
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

    new cdk.CfnOutput(this, 'VpcId', { value: this.vpc.vpcId })
  }
}
