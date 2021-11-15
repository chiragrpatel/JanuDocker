#!/bin/sh

###
### cfn_nag — calls cfn_nag against the repository
###
### Usage:
###   cfn_nag.sh
###
### OUTPUT:
###   file: [reports/cfn-nag-scan.nagscan]
###

# https://vaneyckt.io/posts/safer_bash_scripts_with_set_euxo_pipefail/
set -eux

readonly SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
# Expected Environment Variables
readonly OUTPUT_DIR=$(realpath ${OUTPUT_DIR:-"${SCRIPT_DIR}/../reports"})

readonly GENERATE_REPORT_AND_CONTINUE=${GENERATE_REPORT_AND_CONTINUE:-"false"}

{ 
  cd ${SCRIPT_DIR}/..

  mkdir -p "${OUTPUT_DIR}"

  if [ "$GENERATE_REPORT_AND_CONTINUE" = "true" ]; then
    # Run scan to output file for later automated consumption
    cfn_nag_scan --input-path cfn/ -o json | tee ${OUTPUT_DIR}/cfn-nag-scan.nagscan
  else
    # Run scan with pretty terminal output for human reading, fails on error
    cfn_nag_scan --input-path cfn/
  fi
}
