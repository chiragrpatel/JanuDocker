aws cloudformation delete-stack --stack-name vci-datapipeline-trigger-lambda-eventbridge-rule-stack
aws cloudformation delete-stack --stack-name vci-datapipeline-create-crawler-eventbridge-rule-stack
aws cloudformation delete-stack --stack-name vci-data-pipeline-sns-stack
aws cloudformation delete-stack --stack-name vci-data-pipeline-cloudtrail-stack
aws cloudformation delete-stack --stack-name vci-data-ingestion-pipeline-glue-jobs-stack
aws cloudformation delete-stack --stack-name vci-data-ingestion-pipeline-sf-stack
aws cloudformation delete-stack --stack-name vci-glue-crawler-trigger-lambda-stack
aws cloudformation delete-stack --stack-name vci-data-pipeline-lambda-stack
aws cloudformation delete-stack --stack-name vci-data-pipeline-iam-stack1
aws cloudformation delete-stack --stack-name vci-data-pipeline-s3-stack
aws cloudformation delete-stack --stack-name vci-data-pipeline-sg-stack