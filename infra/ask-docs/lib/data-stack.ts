import * as cdk from 'aws-cdk-lib'
import * as dynamodb from 'aws-cdk-lib/aws-dynamodb'
import * as s3 from 'aws-cdk-lib/aws-s3'
import { Construct } from 'constructs'

// Private bucket for the search index and chunk files. Read only by the Lambda role.
// Conversation table: the last few turns of each Q&A conversation, deleted by TTL a day after last use.
export class DataStack extends cdk.Stack {
  public readonly bucket: s3.Bucket
  public readonly conversationTable: dynamodb.TableV2

  constructor(scope: Construct, id: string, props: cdk.StackProps) {
    super(scope, id, props)
    this.bucket = new s3.Bucket(this, 'IndexBucket', {
      bucketName: `atomai-ask-docs-${this.account}-${this.region}`,
      encryption: s3.BucketEncryption.S3_MANAGED,
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
      enforceSSL: true,
      versioned: true,
      objectOwnership: s3.ObjectOwnership.BUCKET_OWNER_ENFORCED,
      removalPolicy: cdk.RemovalPolicy.RETAIN,
    })
    this.conversationTable = new dynamodb.TableV2(this, 'ConversationTable', {
      partitionKey: { name: 'cid', type: dynamodb.AttributeType.STRING },
      billing: dynamodb.Billing.onDemand(),
      timeToLiveAttribute: 'expires_at',
      removalPolicy: cdk.RemovalPolicy.DESTROY, // short-lived chat state only
    })
    new cdk.CfnOutput(this, 'IndexBucketName', { value: this.bucket.bucketName })
    new cdk.CfnOutput(this, 'ConversationTableName', { value: this.conversationTable.tableName })
  }
}
