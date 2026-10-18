import * as cdk from 'aws-cdk-lib'
import * as s3 from 'aws-cdk-lib/aws-s3'
import { Construct } from 'constructs'

// Private bucket for the search index and chunk files. Read only by the Lambda role.
export class DataStack extends cdk.Stack {
  public readonly bucket: s3.Bucket

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
    new cdk.CfnOutput(this, 'IndexBucketName', { value: this.bucket.bucketName })
  }
}
