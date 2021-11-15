#!/bin/bash

###
### deploy_infra — connects to AWS and creates the bucket, cloudfront, domain, and certificate for the site
###
### Usage:
###   deploy_infra.sh
###
### Environment Variables:
###   <CI>          [true|false|<unset>] If true, the CI only `aws-credentials/login.sh` is used to login to AWS
###   <SHOULD_DEPLOY_CERT> [true|false|<unset>] If true, the certificate will be deployed, only works if the prod domain has been created
###

# https://vaneyckt.io/posts/safer_bash_scripts_with_set_euxo_pipefail/
set -euxo pipefail

readonly SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
readonly PROJECT_DIR="${SCRIPT_DIR%/*}"

## Script Defaults

## Expected Environment Variables and overrides
readonly PRODUCT="transformers-hello-there"
readonly TEAM="transformers"
readonly TOP_DOMAIN=${TOP_DOMAIN:-'hello-there.hypozio.com'}
readonly CI=${CI:-"false"}
readonly SHOULD_DEPLOY_CERT=${SHOULD_DEPLOY_CERT:-"true"}
# SHOULD_DEPLOY_CERT='false' # Set this to 'false' untill the the domain stack is in prod

## Calculated Variables
Certificate="" # placeholder, this will be populated if 'SHOULD_DEPLOY_CERT' is set to 'true'
DevNameServers="" # placeholder, this will be populated if 'Subdomain' is set to 'prod' or is empty
IntNameServers="" # placeholder, this will be populated if 'Subdomain' is set to 'prod' or is empty
ConsNameServers="" # placeholder, this will be populated if 'Subdomain' is set to 'prod' or is empty

export AWS_REGION='us-east-1'
export AWS_DEFAULT_REGION=$AWS_REGION
export AWS_PAGER= #turn off pagination

###
# Function Declarions
###

function get_stage(){
  local accountAlias=$(aws iam list-account-aliases --query "AccountAliases" --output text)
  local stage=$(echo $accountAlias | awk -F "-" '{print $NF}')
  echo "${stage}"
}

function get_nameservers_for_env () {
  env=$1
  if [[ "$CI" == "true" ]]; then
      source ${PROJECT_DIR}/../aws-${env}-credentials/login.sh
      # echo $(aws iam list-account-aliases --query "AccountAliases" --output text) # dont echo this out, as its then part of the return value
  fi
  echo $(aws cloudformation list-exports --query "Exports[?Name=='${env}-${HYPHENATED_DOMAIN}-nameservers'].Value" --output text)
  return 0
}

function deploy_dns {
  # Push into cfn directory with intention of popping back
  pushd ${PROJECT_DIR}/cfn
    # Deploy DNS Servers
    aws cloudformation deploy \
      --region ${AWS_DEFAULT_REGION} \
      --template-file domain.yml \
      --stack-name ${PRODUCT}-domain \
      --parameter-overrides \
          Domain=${DOMAIN} \
          DevNameServers=${DevNameServers} \
          IntNameServers=${IntNameServers} \
          ConsNameServers=${ConsNameServers} \
      --tags \
          vci:team=${TEAM} \
          vci:product=${PRODUCT} \
          vci:createdBy=${USER}

    aws cloudformation describe-stacks \
      --stack-name ${PRODUCT}-domain \
      --query 'Stacks[0].Outputs[].{key:OutputKey, value:OutputValue}' \
      --output table
  popd
  return 0
}

function deploy_certificate {
  # Push into cfn directory with intention of popping back
  pushd ${PROJECT_DIR}/cfn
    # Deploy SSL certificate
    aws cloudformation deploy \
      --region ${AWS_DEFAULT_REGION} \
      --template-file certificate.yml \
      --stack-name ${PRODUCT}-certificate \
      --parameter-overrides \
          FullDomainName=${DOMAIN} \
          HostedZoneId=${HostedZoneId} \
      --tags \
          vci:team=${TEAM} \
          vci:product=${PRODUCT} \
          vci:createdBy=${USER}
    
    aws cloudformation describe-stacks \
      --stack-name ${PRODUCT}-certificate \
      --query 'Stacks[0].Outputs[].{key:OutputKey, value:OutputValue}' \
      --output table
  popd
  return 0
}

function deploy_website {
  # Push into cfn directory with intention of popping back
  pushd ${PROJECT_DIR}/cfn
    # Deploy website with S3 / DNS / CloudFront
    aws cloudformation deploy \
      --region ${AWS_DEFAULT_REGION} \
      --template-file website.yml \
      --stack-name ${PRODUCT}-website \
      --parameter-overrides \
          FullDomainName=${DOMAIN} \
          HostedZoneId=${HostedZoneId} \
          Certificate=${Certificate} \
      --tags \
          vci:team=${TEAM} \
          vci:product=${PRODUCT} \
          vci:createdBy=${USER}
    
    aws cloudformation describe-stacks \
      --stack-name ${PRODUCT}-website \
      --query 'Stacks[0].Outputs[].{key:OutputKey, value:OutputValue}' \
      --output table
  popd
  return 0
}

function main() {
  # Log into AWS
  if [ "$CI" = "true" ]; then
    source ${PROJECT_DIR}/../aws-credentials/login.sh
    echo $(aws iam list-account-aliases --query "AccountAliases" --output text)
  fi

  local stage=$(get_stage)

  if [ $(echo "${stage}" | tr '[:upper:]' '[:lower:]') = "prod" ]; then
    readonly DOMAIN="${TOP_DOMAIN}"
    readonly HYPHENATED_DOMAIN=${DOMAIN//'.'/'-'}
    # For Prod, get list of DNS servers from each lower environment
    readonly DevNameServers=$(get_nameservers_for_env dev)
    readonly IntNameServers=$(get_nameservers_for_env int)
    readonly ConsNameServers=$(get_nameservers_for_env cons)
  else
    # For other environments, add the stage as the subdomain prefix for the domain
    readonly DOMAIN="${stage}.${TOP_DOMAIN}"
    readonly HYPHENATED_DOMAIN=${DOMAIN//'.'/'-'}
    echo "set domain to ${DOMAIN}"
  fi

  deploy_dns
  local HostedZoneId=$(aws cloudformation list-exports --query "Exports[?Name=='${HYPHENATED_DOMAIN}-id'].Value" --output text)
  local NameServers=$(aws cloudformation list-exports --query "Exports[?Name=='${HYPHENATED_DOMAIN}-nameservers'].Value" --output text)
  echo "Created hosted zone for ${DOMAIN} with an ID of ${HostedZoneId} and nameservers of ${NameServers}"

  if [ "$SHOULD_DEPLOY_CERT" = "true" ]; then
    deploy_certificate
    local Certificate=$(aws cloudformation list-exports --query "Exports[?Name=='${HYPHENATED_DOMAIN}-cert'].Value" --output text)
  fi

  deploy_website
  local CloudFrontDomain=$(aws cloudformation describe-stacks --stack-name ${PRODUCT}-website --query "Stacks[0].Outputs[?OutputKey=='CloudFrontDomain'].OutputValue" --output text)
  echo "Cloudfront now hosting at ${CloudFrontDomain}"
}

###
# Script Execution
###

main "$@"
