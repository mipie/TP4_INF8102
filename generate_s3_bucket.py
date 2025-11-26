import boto3
from botocore.exceptions import ClientError

KMS_KEY_ARN = "arn:aws:kms:us-west-2:767397842641:key/44fd78a9-01ad-4323-8ccd-24e608de0197"
BUCKET_NAME = "polystudents3-anis-michlove-unique"
REGION = "us-west-2"

s3_client = boto3.client("s3", region_name=REGION)

def create_bucket(bucket):
    try:
        s3_client.create_bucket(
            Bucket=bucket,
            CreateBucketConfiguration={"LocationConstraint": REGION}
        )
        print(f'Bucket {BUCKET_NAME} créé avec succès dans la région {REGION}.')
    except ClientError as e:
        if e.response["Error"]["Code"] in ["BucketAlreadyOwnedByYou", "BucketAlreadyExists"]:
            print(f'Bucket {BUCKET_NAME} existe déjà.')
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
        print(f'Chiffrement SSE-KMS activé pour {BUCKET_NAME} avec la clé {KMS_KEY_ARN}.')

    s3_client.put_public_access_block(
        Bucket=bucket,
        PublicAccessBlockConfiguration={
            "BlockPublicAcls": True,
            "IgnorePublicAcls": True,
            "BlockPublicPolicy": True,
            "RestrictPublicBuckets": True
        }
    )
    print(f"Accès public bloqué pour {bucket}.")
    print(f'Bucket {BUCKET_NAME} configuré avec succès selon les exigences de sécurité.')
    print(f'Politiques appliquées : Versioning, SSE-KMS, Contrôle d\'accès privé, Blocage d\'accès public.')
    
    
if __name__ == "__main__":
    create_bucket(BUCKET_NAME)
    secure_bucket(BUCKET_NAME)

