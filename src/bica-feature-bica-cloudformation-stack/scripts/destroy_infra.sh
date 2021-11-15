#!/bin/bash

###
### destroy_infra — connects to AWS and removes the bucket, cloudfront, domain, and certificate for the site
###                 Not intended for most rollback scenarios.
###
### !WARNING! Be certain you know what you are doing when running this.
###
### Usage:
###   destroy_infra.sh
###
### Environment Variables:
###   <CI>          [true|false|<unset>] If true, the CI only `aws-credentials/login.sh` is used to login to AWS
###   <SHOULD_DELETE> [true|false|<unset>] If true, the script will delete from the connected account, unless prod
###   <SHOULD_DELETE_PROD> [true|false|<unset>] If true, the script will be allowed to delete resources from prod
###

# https://vaneyckt.io/posts/safer_bash_scripts_with_set_euxo_pipefail/
set -euxo pipefail

readonly SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
readonly PROJECT_DIR="${SCRIPT_DIR%/*}"

# Expected Environment Variables and overrides
readonly PRODUCT=${PRODUCT:-'transformers-hello-there'}
readonly TOP_DOMAIN=${TOP_DOMAIN:-'hello-there.hypozio.com'}
readonly CI=${CI:-"false"}
readonly SHOULD_DELETE=${SHOULD_DELETE:-"false"} # Are you sure you want to?
readonly SHOULD_DELETE_PROD=${SHOULD_DELETE_PROD:-"false"} # Are you really sure?
# TODO(koellem): should consider a retain resources flag for the s3 buckets

export AWS_REGION='us-east-1'
export AWS_DEFAULT_REGION=$AWS_REGION

###
# Function Declarations
###

function get_stage(){
  local accountAlias=$(aws iam list-account-aliases --query "AccountAliases" --output text)
  local stage=$(echo $accountAlias | awk -F "-" '{print $NF}')
  echo "${stage}"
}

function stack_exists() {
  local stack_name=$1
  local stack_status=$(aws cloudformation describe-stacks --query "Stacks[?StackName=='${stack_name}' && StackStatus!='DELETE_IN_PROGRESS'].StackStatus" --output text)
  [[ -n "$stack_status" ]] && return

  false
}

function delete_all_buckets_by_stack_tag() {
  # Uses the vci:product tag to find all buckets associated with the stack
  # Then deletes them
  local TAG=$1
  local STACK_BUCKETS=$(aws resourcegroupstaggingapi get-resources \
    --region $AWS_REGION \
    --no-paginate \
    --tag-filters Key=vci:product,Values=${TAG} \
    --resource-type-filters s3 \
    --query "ResourceTagMappingList[].ResourceARN" \
    --output text)
  
  for BUCKET_ARN in $STACK_BUCKETS
  do
    echo "Removing bucket ${BUCKET_ARN}"
    local BUCKET_NAME=${BUCKET_ARN#arn:aws:s3:::}
      aws s3 rm "s3://${BUCKET_NAME}" --recursive
  done
}

function main() {
  if [[ "$SHOULD_DELETE" == "true" ]]; then

    if [[ "$CI" == "true" ]]; then
        source ${PROJECT_DIR}/../aws-credentials/login.sh
        echo $(aws iam list-account-aliases --query "AccountAliases" --output text)
    fi

    local stage=$(get_stage)
    
    # Set variables that differ between prod/non-prod
    if [ $(echo "${stage}" | tr '[:upper:]' '[:lower:]') = "prod" ]; then
      readonly DOMAIN="${TOP_DOMAIN}"
      readonly HYPHENATED_DOMAIN=${DOMAIN//'.'/'-'}
      if [[ "$SHOULD_DELETE_PROD" != "true" ]]; then
        echo "SHOULD_DELETE_PROD was false, Skipping deletion"
        readonly SHOULD_DELETE="false"
      fi
    else
      readonly DOMAIN="${stage}.${TOP_DOMAIN}"
      readonly HYPHENATED_DOMAIN=${DOMAIN//'.'/'-'}
      readonly SHOULD_DELETE
    fi

    if stack_exists "${PRODUCT}-website"; then
      echo "Deleting stack ${PRODUCT}-website"
      delete_all_buckets_by_stack_tag ${PRODUCT}-website
      aws cloudformation delete-stack --stack-name "${PRODUCT}-website" >/dev/null
    fi

    if stack_exists "${PRODUCT}-certificate"; then
      echo "Deleting stack ${PRODUCT}-certificate"
      aws cloudformation delete-stack --stack-name "${PRODUCT}-certificate" >/dev/null
    fi

    if stack_exists "${PRODUCT}-domain"; then
      echo "Deleting stack ${PRODUCT}-domain"
      aws cloudformation delete-stack --stack-name "${PRODUCT}-domain" >/dev/null
    fi

  else
    echo "SHOULD_DELETE was false, Skipping deletion"
  fi
}

###
# Script Execution
###

main "$@"
