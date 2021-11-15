#!/bin/bash

###
### sonar_scan — calls sonnar scanner on the current branch of the project
###
### Usage:
###   sonar_scan.sh
###
### Environment Variables:
###   <CI>   [true|false|<unset>] If set to false, the cfn_nag.sh script is also executed.
###

# https://vaneyckt.io/posts/safer_bash_scripts_with_set_euxo_pipefail/
set -euxo pipefail
script_dir="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
# Expected Environment Variables
CI=${CI:-"false"}

pushd ${script_dir}/..
  if [ "$CI" = "false" ]; then
    # Run all the other reports first
    ./scripts/cfn_nag.sh
  fi
  BRANCH_NAME=$(git show -s --pretty=%D HEAD | tr -s ', ' '\n' | grep -v HEAD | sed -n 2p)
  sonar-scanner -Dsonar.branch.name=${BRANCH_NAME}
popd
