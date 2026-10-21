import * as cdk from 'aws-cdk-lib'
import * as ec2 from 'aws-cdk-lib/aws-ec2'
import { Construct } from 'constructs'

// Security group for the docs Q&A API's internal ALB inside the shared demo VPC (fsi-demo-vpc).
// This stack never creates a VPC: the demo VPC already has the internet gateway CloudFront VPC
// origins need, and the pods reach S3, DynamoDB and Bedrock through its existing endpoints/NAT.
// The ALB sits in the isolated subnets, which have no route to the IGW or NAT.
export class NetworkStack extends cdk.Stack {
  public readonly vpc: ec2.IVpc
  public readonly albSecurityGroup: ec2.SecurityGroup

  constructor(scope: Construct, id: string, props: cdk.StackProps) {
    super(scope, id, props)
    // AWS managed prefix lists in ap-northeast-2 (verified with describe-managed-prefix-lists).
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

    // Internal ALB: only CloudFront origin-facing addresses may reach it (CLAUDE.md allows the
    // CloudFront managed prefix list). Egress only to the EKS pods below.
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

    // Targets are pods of the demo EKS cluster (IP target group). Their ENIs carry the cluster
    // security group; the AWS Load Balancer Controller adds the matching ingress rule there.
    this.albSecurityGroup.addEgressRule(
      ec2.Peer.securityGroupId(ctx('demoClusterSg')),
      ec2.Port.tcp(8080),
      'ask-docs pods on the demo EKS cluster'
    )

    new cdk.CfnOutput(this, 'VpcId', { value: this.vpc.vpcId })
  }
}
