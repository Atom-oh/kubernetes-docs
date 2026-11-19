-- CloudTrail Lake: which AWS APIs are being called with the NODE role?
-- Calls a node itself needs (EC2/ECR/EKS/eks-auth/sts) are expected;
-- anything else (s3, dynamodb, sqs, secretsmanager ...) is almost certainly
-- an application pod living off the instance profile -> migration candidate.
-- Replace <event-data-store-id> and <NodeInstanceRoleName>.
SELECT eventSource,
       eventName,
       count(*)                           AS calls,
       count(DISTINCT sourceIPAddress)    AS source_ips,
       min(eventTime)                     AS first_seen,
       max(eventTime)                     AS last_seen
FROM   <event-data-store-id>
WHERE  eventTime > date_add('day', -30, now())
  AND  userIdentity.sessionContext.sessionIssuer.userName = '<NodeInstanceRoleName>'
  AND  eventSource NOT IN ('ec2.amazonaws.com', 'ecr.amazonaws.com', 'eks.amazonaws.com',
                           'eks-auth.amazonaws.com', 'sts.amazonaws.com')
GROUP  BY eventSource, eventName
ORDER  BY calls DESC;
