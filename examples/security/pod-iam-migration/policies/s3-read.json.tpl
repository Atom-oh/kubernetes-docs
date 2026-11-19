{
  "Version": "2012-10-17",
  "Statement": [
    { "Sid": "ListDemoBucket", "Effect": "Allow", "Action": "s3:ListBucket",
      "Resource": "arn:aws:s3:::${DEMO_BUCKET}" },
    { "Sid": "ReadDemoObjects", "Effect": "Allow", "Action": "s3:GetObject",
      "Resource": "arn:aws:s3:::${DEMO_BUCKET}/*" }
  ]
}
