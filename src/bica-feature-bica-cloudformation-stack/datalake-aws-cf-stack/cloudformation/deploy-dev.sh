ENV="dev"
TENANT="vw-cred-datalake"
CrossAccountDsnaRole="arn:aws:iam::014257795134:role/vci-sagemaker-CrossAccount-DataLake-Access-Role"
DsnaAccountId="014257795134"
TeamTag="itdna"
SUBNETS=""
DatalakeAccountId="854807003520"
AWSRegion="us-east-1"
VpcId="vpc-0f90cb189d474a77f"
ARTIFACTS_BUCKET="vci-$ENV-artifacts-$DatalakeAccountId-$AWSRegion"
SAM_PREFIX="sam/artifacts"


# echo "Deploying SG"
# BASE_DIR=../security
# aws cloudformation deploy \
#     --template-file $BASE_DIR/security-groups.yaml \
#     --stack-name vci-data-pipeline-sg-stack \
#     --parameter-overrides \
#         Env=$ENV \
#         AWSTenant=$TENANT \
#         TeamTag=$TeamTag \
#         VpcId=$VpcId \
#     --no-fail-on-empty-changeset

echo "Deploying S3 stack for DataPipeline."
BASE_DIR=../s3
aws cloudformation deploy \
    --template-file $BASE_DIR/MyS3WithCloudFormation.yaml \
    --stack-name vci-cred-datalake-pipeline-s3-stack \
    --parameter-overrides \
        Env=$ENV \
        AWSTenant=$TENANT \
        DsnaAccountId=$DsnaAccountId \
        CrossAccountDsnaRole=$CrossAccountDsnaRole \
        TeamTag=$TeamTag \
    --no-fail-on-empty-changeset


# echo "Deploying IAM Stacks"
# BASE_DIR=../iam
# aws cloudformation deploy \
#     --capabilities CAPABILITY_IAM \
#     --capabilities CAPABILITY_NAMED_IAM \
#     --template-file $BASE_DIR/iam-stack.yaml \
#     --stack-name vci-data-pipeline-iam-stack \
#     --parameter-overrides \
#         Env=$ENV \
#         AWSTenant=$TENANT \
#         DsnaAccountId=$DsnaAccountId \
#         CrossAccountDsnaRole=$CrossAccountDsnaRole \
#         TeamTag=$TeamTag \
#     --no-fail-on-empty-changeset

# echo "Deploying Cloudtrail and policy stack"
# BASE_DIR=../cloudtrail
# aws cloudformation deploy \
#     --template-file $BASE_DIR/cloudtrail.yaml \
#     --stack-name vci-data-pipeline-cloudtrail-stack \
#     --parameter-overrides \
#         Env=$ENV \
#         AWSTenant=$TENANT \
#         DsnaAccountId=$DsnaAccountId \
#         CrossAccountDsnaRole=$CrossAccountDsnaRole \
#         TeamTag=$TeamTag \
#     --no-fail-on-empty-changeset

# echo "Deploying SNS Topic."
# BASE_DIR=../sns
# aws cloudformation deploy \
#     --template-file $BASE_DIR/vci_datapipeline_sns_topic.yaml \
#     --stack-name vci-data-pipeline-sns-stack \
#     --parameter-overrides \
#         Env=$ENV \
#         AWSTenant=$TENANT \
#         TeamTag=$TeamTag \
#         SNSTopicName="vci_datapipeline_sns_topic" \
#         SubscriptionEmail="aggarwd@vwcredit.com" \
#     --no-fail-on-empty-changeset

# echo "Deploying EventBridge rules"
# BASE_DIR=../eventbridge
# aws cloudformation deploy \
#     --template-file $BASE_DIR/s3-create-run-glue-database-crawler-rule.yaml \
#     --stack-name vci-datapipeline-create-crawler-eventbridge-rule-stack \
#     --parameter-overrides \
#         AWSTenant=$TENANT \
#         Env=$ENV \
#     --no-fail-on-empty-changeset

# aws cloudformation deploy \
#     --template-file $BASE_DIR/s3-raw-create-obj-trigger-lambda-rule.yaml \
#     --stack-name vci-datapipeline-trigger-lambda-eventbridge-rule-stack \
#     --parameter-overrides \
#         AWSTenant=$TENANT \
#         Env=$ENV \
#     --no-fail-on-empty-changeset
    

# echo "Deploying Lambda stack for DataPipeline."
# BASE_DIR=../sam/lambda-trigger-sfn-data-pipeline
# sam build \
#     --template-file $BASE_DIR/template.yaml \
#     --build-dir $BASE_DIR/.aws-sam && \
# sam package \
#     --template-file $BASE_DIR/.aws-sam/template.yaml \
#     --s3-bucket $ARTIFACTS_BUCKET \
#     --s3-prefix $SAM_PREFIX \
#     --output-template-file $BASE_DIR/output.yaml && \
# sam deploy \
#     --template-file $BASE_DIR/output.yaml \
#     --stack-name vci-data-pipeline-lambda-stack \
#     --capabilities CAPABILITY_IAM \
#     --parameter-overrides \
#         TeamTag=$TeamTag \
#         AWSTenant=$TENANT \
#         Env=$ENV \
#         Subnets=$SUBNETS \
#     --no-fail-on-empty-changeset


# echo "Deploying Lambda stack for Glue Catalog maintenance."
# BASE_DIR=../sam/lambda-trigger-glue-crawler
# sam build \
#     --template-file $BASE_DIR/template.yaml \
#     --build-dir $BASE_DIR/.aws-sam && \
# sam package \
#     --template-file $BASE_DIR/.aws-sam/template.yaml \
#     --s3-bucket $ARTIFACTS_BUCKET \
#     --s3-prefix $SAM_PREFIX \
#     --output-template-file $BASE_DIR/output.yaml && \
# sam deploy \
#     --template-file $BASE_DIR/output.yaml \
#     --stack-name vci-glue-crawler-trigger-lambda-stack\
#     --capabilities CAPABILITY_IAM \
#     --parameter-overrides \
#         TeamTag=$TeamTag \
#         AWSTenant=$TENANT \
#         Env=$ENV \
#         Subnets=$SUBNETS \
#         crawleriamrole='glue-service-role'
#     --no-fail-on-empty-changeset

# echo "Deploying SF for Data Ingestion pipeline"
# BASE_DIR=../sam/sfn-run-data-ingestion-pipeline
# sam build \
#     --template-file $BASE_DIR/template.yaml \
#     --build-dir $BASE_DIR/.aws-sam && \
# sam package \
#     --template-file $BASE_DIR/.aws-sam/template.yaml \
#     --s3-bucket $ARTIFACTS_BUCKET \
#     --s3-prefix $SAM_PREFIX \
#     --output-template-file $BASE_DIR/output.yaml && \
# sam deploy \
#     --template-file $BASE_DIR/output.yaml \
#     --stack-name vci-data-ingestion-pipeline-sf-stack \
#     --capabilities CAPABILITY_IAM \
#     --parameter-overrides \
#         TeamTag=$TeamTag \
#         AWSTenant=$TENANT \
#         Env=$ENV \
#     --no-fail-on-empty-changeset



# echo "Deploying glue jobs for Data Ingestion pipeline"

# aws s3 cp ../glue/glue-load-raw-to-curated.py s3://${ARTIFACTS_BUCKET}/glue/glue-load-raw-to-curated.py
# aws s3 cp ../glue/glue-load-curated-to-transformed.py s3://${ARTIFACTS_BUCKET}/glue/glue-load-curated-to-transformed.py

# aws cloudformation deploy \
#     --template-file glue.yaml \
#     --stack-name vci-data-ingestion-pipeline-glue-jobs-stack \
#     --parameter-overrides \
#         TeamTag=$TeamTag \
#         AWSTenant=$TENANT \
#         Env=$ENV \
#         ArtifactsBucket=$ARTIFACTS_BUCKET \
#     --no-fail-on-empty-changeset