import boto3
import json
from botocore.exceptions import ClientError

REGION = "us-west-2"
BUCKET_NAME = "polystudents3-anis-michlove-unique"
BUCKET_BACK = "polystudents3-back-anis-michlove-unique"
KMS_KEY_ARN = "arn:aws:kms:us-west-2:767397842641:key/44fd78a9-01ad-4323-8ccd-24e608de0197"

s3_client = boto3.client("s3", region_name=REGION)
s3_resource = boto3.resource("s3", region_name=REGION)
cloudtrail = boto3.client("cloudtrail", region_name=REGION)

flow_log_policy = {
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Principal": {"Service": "delivery.logs.amazonaws.com"},
            "Action": ["s3:PutObject", "s3:PutObjectAcl"],
            "Resource": f"arn:aws:s3:::{BUCKET_NAME}/*",
            "Condition": {"StringEquals": {"s3:x-amz-acl": "bucket-owner-full-control"}}
        },
        {
            "Effect": "Allow",
            "Principal": {"Service": "delivery.logs.amazonaws.com"},
            "Action": "s3:GetBucketAcl",
            "Resource": f"arn:aws:s3:::{BUCKET_NAME}"
        }
    ]
}

def create_bucket(bucket):
    try:
        s3_client.create_bucket(
            Bucket=bucket,
            CreateBucketConfiguration={"LocationConstraint": REGION}
        )
        print(f"Bucket {bucket} créé.")
    except ClientError as e:
        if e.response["Error"]["Code"] in ["BucketAlreadyOwnedByYou", "BucketAlreadyExists"]:
            print(f"ℹ Bucket {bucket} existe déjà.")
        else:
            raise e

def secure_bucket(bucket):
    s3_client.put_bucket_versioning(
        Bucket=bucket,
        VersioningConfiguration={"Status": "Enabled"}
    )
    print(f"Versioning activé pour {bucket}.")

    if bucket == BUCKET_NAME:
        s3_client.put_bucket_encryption(
            Bucket=bucket,
            ServerSideEncryptionConfiguration={
                "Rules": [{
                    "ApplyServerSideEncryptionByDefault": {
                        "SSEAlgorithm": "aws:kms",
                        "KMSMasterKeyID": KMS_KEY_ARN
                    }
                }]
            }
        )
        print(f"Chiffrement SSE-KMS activé pour {bucket}.")

    s3_client.put_public_access_block(
        Bucket=bucket,
        PublicAccessBlockConfiguration={
            "BlockPublicAcls": True,
            "IgnorePublicAcls": True,
            "BlockPublicPolicy": False,
            "RestrictPublicBuckets": True
        }
    )
    print(f"Accès public bloqué pour {bucket}.")

def apply_flowlog_policy(bucket):
    s3_client.put_bucket_policy(
        Bucket=bucket,
        Policy=json.dumps(flow_log_policy)
    )
    print(f"Politique Flow Logs appliquée à {bucket}.")

def replicate_objects():
    print(f"\nRéplication manuelle {BUCKET_NAME} -> {BUCKET_BACK}...")

    src_bucket = s3_resource.Bucket(BUCKET_NAME)
    dest_bucket = s3_resource.Bucket(BUCKET_BACK)

    for obj in src_bucket.objects.all():
        copy_source = {"Bucket": BUCKET_NAME, "Key": obj.key}
        dest_bucket.copy(copy_source, obj.key)
        print(f"Copié : {obj.key}")

    print("Réplication terminée.\n")

def apply_cloudtrail_bucket_policy():
    policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "AWSCloudTrailAclCheck",
                "Effect": "Allow",
                "Principal": {"Service": "cloudtrail.amazonaws.com"},
                "Action": "s3:GetBucketAcl",
                "Resource": f"arn:aws:s3:::{BUCKET_BACK}"
            },
            {
                "Sid": "AWSCloudTrailWrite",
                "Effect": "Allow",
                "Principal": {"Service": "cloudtrail.amazonaws.com"},
                "Action": "s3:PutObject",
                "Resource": f"arn:aws:s3:::{BUCKET_BACK}/AWSLogs/767397842641/*",
                "Condition": {
                    "StringEquals": {
                        "s3:x-amz-acl": "bucket-owner-full-control"
                    }
                }
            }
        ]
    }

    s3_client.put_bucket_policy(
        Bucket=BUCKET_BACK,
        Policy=json.dumps(policy)
    )
    print(f"Politique CloudTrail appliquée au bucket {BUCKET_BACK}")


def setup_cloudtrail():
    print("Activation CloudTrail pour audit des objets S3...")

    trail_name = "S3ObjectTrail"

    try:
        cloudtrail.create_trail(
            Name=trail_name,
            S3BucketName=BUCKET_BACK,
            IsMultiRegionTrail=False
        )
        print("✔ Trail créé.")

    except ClientError as e:
        if "TrailAlreadyExistsException" in str(e):
            print("Trail existe déjà.")
        else:
            raise e

    cloudtrail.put_event_selectors(
        TrailName=trail_name,
        EventSelectors=[
            {
                "ReadWriteType": "WriteOnly",
                "IncludeManagementEvents": False,
                "DataResources": [{
                    "Type": "AWS::S3::Object",
                    "Values": [f"arn:aws:s3:::{BUCKET_NAME}/*"]
                }]
            }
        ]
    )

    cloudtrail.start_logging(Name=trail_name)
    print("✔ CloudTrail activé pour surveiller modifications/suppressions.\n")

if __name__ == "__main__":
    print("\n=== CONFIGURATION DES BUCKETS S3 ===")

    create_bucket(BUCKET_NAME)
    secure_bucket(BUCKET_NAME)
    apply_flowlog_policy(BUCKET_NAME)

    create_bucket(BUCKET_BACK)
    secure_bucket(BUCKET_BACK)

    replicate_objects()
    apply_cloudtrail_bucket_policy()
    setup_cloudtrail()

    print("Tous les éléments S3 ont été configurés avec succès !")

