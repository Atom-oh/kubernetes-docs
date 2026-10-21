import * as cdk from 'aws-cdk-lib'
import * as ec2 from 'aws-cdk-lib/aws-ec2'
import * as iam from 'aws-cdk-lib/aws-iam'
import * as cr from 'aws-cdk-lib/custom-resources'
import { Construct } from 'constructs'

// Security groups and the execute-api endpoint for the docs Q&A API inside the shared demo VPC
// (fsi-demo-vpc). This stack never creates a VPC: the demo VPC already has the S3 and DynamoDB
// gateway endpoints, the bedrock-runtime interface endpoint (VPC-wide 443) and the internet gateway
// CloudFront VPC origins need. The isolated subnets have no route to the IGW or NAT.
export class NetworkStack extends cdk.Stack {
  public readonly vpc: ec2.IVpc
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

    const ctx = (key: string) => {
      const value = this.node.tryGetContext(key) as string | undefined
      if (typeof value !== 'string' || !value.trim()) {
        throw new Error(`context "${key}" is required; pass -c ${key}=... from a private context file outside Git`)
      }
      return value
    }
    this.vpc = ec2.Vpc.fromVpcAttributes(this, 'DemoVpc', {
      vpcId: ctx('demoVpcId'),
      vpcCidrBlock: ctx('demoVpcCidr'),
      availabilityZones: ['ap-northeast-2a', 'ap-northeast-2b'],
      isolatedSubnetIds: [ctx('demoIsolatedSubnetA'), ctx('demoIsolatedSubnetB')],
      isolatedSubnetRouteTableIds: [ctx('demoIsolatedRouteTableA'), ctx('demoIsolatedRouteTableB')],
    })

    this.lambdaSecurityGroup = new ec2.SecurityGroup(this, 'LambdaSg', {
      vpc: this.vpc,
      description: 'Ask-docs Lambda: egress only to endpoints, S3 and DynamoDB',
      allowAllOutbound: false,
    })
    // The demo VPC's existing bedrock-runtime endpoint SG already admits 443 from the VPC CIDR.
    this.lambdaSecurityGroup.addEgressRule(
      ec2.Peer.securityGroupId(ctx('demoBedrockEndpointSg')),
      ec2.Port.tcp(443),
      'Bedrock runtime endpoint'
    )
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
    // Gateway (STREAM transfer mode) through this endpoint's ENIs. Private DNS stays off so the
    // shared demo VPC's other workloads are unaffected, and the ALB sets the API's Host header itself.
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
    // other private API: only this account's ask route. (The API id lives in the app stack, which
    // depends on this stack, hence the stage/route match instead of the exact id.)
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
