#!/bin/bash

###
### deploy_content — connects to AWS and copies the files in the `content`
###                  directory to a bucket, requires an active AWS session
###
### Usage:
###   deploy_content.sh
###
### Environment Variables:
###   <CI>          [true|false|<unset>] If true, the CI only `aws-credentials/login.sh` is used to login to AWS
###

# https://vaneyckt.io/posts/safer_bash_scripts_with_set_euxo_pipefail/
set -euxo pipefail

readonly SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
readonly PROJECT_DIR="${SCRIPT_DIR%/*}"

# Expected Environment Variables and overrides
readonly TOP_DOMAIN=${TOP_DOMAIN:-'hello-there.hypozio.com'}
readonly CI=${CI:-"false"}

export AWS_REGION='us-east-1'
export AWS_DEFAULT_REGION=$AWS_REGION

###
# Function Declarions
###

function get_stage(){
  local accountAlias=$(aws iam list-account-aliases --query "AccountAliases" --output text)
  local stage=$(echo $accountAlias | awk -F "-" '{print $NF}')
  echo "${stage}"
}

function main() {
  # Log into AWS
  if [ "$CI" = "true" ]; then
      source ${PROJECT_DIR}/../aws-credentials/login.sh
  fi

  local stage=$(get_stage)

  if [ $(echo "${stage}" | tr '[:upper:]' '[:lower:]') = "prod" ]; then
    echo "Executing prod deployment, no subdomain will be used"
    readonly DOMAIN="${TOP_DOMAIN}"
    readonly HYPHENATED_DOMAIN=${DOMAIN//'.'/'-'}
    echo "set domain to ${DOMAIN}"
  else
    # For other environments, add the stage as the subdomain prefix for the domain
    readonly DOMAIN="${stage}.${TOP_DOMAIN}"
    readonly HYPHENATED_DOMAIN=${DOMAIN//'.'/'-'}
    echo "set domain to ${DOMAIN}"
  fi

  local bucket=$(aws cloudformation list-exports --query "Exports[?Name=='${HYPHENATED_DOMAIN}-bucket'].Value" --output text)

  pushd ${PROJECT_DIR}
    aws s3 sync ./content s3://${bucket} --delete --region ${AWS_DEFAULT_REGION} --sse AES256
  popd
}

###
# Script Execution
###

main "$@"
