{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "ListOnlyOwnNamespacePrefix",
      "Effect": "Allow",
      "Action": "s3:ListBucket",
      "Resource": "arn:aws:s3:::${DEMO_BUCKET}",
      "Condition": { "StringLike": { "s3:prefix": ["${aws:PrincipalTag/kubernetes-namespace}/*"] } }
    },
    {
      "Sid": "ReadOnlyOwnNamespacePrefix",
      "Effect": "Allow",
      "Action": "s3:GetObject",
      "Resource": "arn:aws:s3:::${DEMO_BUCKET}/${aws:PrincipalTag/kubernetes-namespace}/*"
    }
  ]
}
