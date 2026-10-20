#!/usr/bin/env node
import * as cdk from 'aws-cdk-lib'
import { NetworkStack } from '../lib/network-stack'
import { DataStack } from '../lib/data-stack'
import { AppStack } from '../lib/app-stack'
import { EdgeStack } from '../lib/edge-stack'

const app = new cdk.App()
const account = app.node.tryGetContext('account') as string
const seoul = { account, region: 'ap-northeast-2' }
const useast1 = { account, region: 'us-east-1' }

const network = new NetworkStack(app, 'AskDocsDemoNetwork', { env: seoul })
const data = new DataStack(app, 'AskDocsData', { env: seoul })
const appStack = new AppStack(app, 'AskDocsAppDemo', {
  env: seoul,
  vpc: network.vpc,
  albSecurityGroup: network.albSecurityGroup,
  lambdaSecurityGroup: network.lambdaSecurityGroup,
  bucket: data.bucket,
  conversationTable: data.conversationTable,
  executeApiEndpoint: network.executeApiEndpoint,
  executeApiEndpointIps: network.executeApiEndpointIps,
})
appStack.addStackDependency(network)
appStack.addStackDependency(data)

// us-east-1 holds CloudFront (global), WAF (CLOUDFRONT scope) and the www cert.
// The ALB lives in Seoul, so its ARN and SG id are passed as context after AskDocsAppDemo deploys.
const albArn = app.node.tryGetContext('albArn') as string | undefined
const albSgId = app.node.tryGetContext('albSecurityGroupId') as string | undefined
const albDnsName = app.node.tryGetContext('albDnsName') as string | undefined
const vpcId = app.node.tryGetContext('vpcId') as string | undefined
if (albArn && albSgId && albDnsName && vpcId) {
  new EdgeStack(app, 'AskDocsEdge', { env: useast1, albArn, albSgId, albDnsName, vpcId })
}
app.synth()
