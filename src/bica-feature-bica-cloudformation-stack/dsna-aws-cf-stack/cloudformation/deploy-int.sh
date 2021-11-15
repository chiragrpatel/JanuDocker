ENV="int"
DLTENANT="vw-cred-datalake"
DSNATENANT="vw-cred-dsna"
DsnaAccountId="149555818180"
DLAccountId="660734235353"
VPCID="vpc-072fa166d626e587d"
TeamTag="itdna"

# Deploying Self Referencing Security Group
BASE_DIR=../security
aws cloudformation deploy \
    --template-file $BASE_DIR/security-groups.yaml \
    --stack-name vci-self-referencing-sg-stack \
    --parameter-overrides \
        Env=$ENV \
        VpcId=$VPCID \
        TeamTag=$TeamTag \
        AWSTenant=$DSNATENANT \
    --no-fail-on-empty-changeset

# Deploying IAM vci-cross-account-datalake-access-role-stack
BASE_DIR=../iam
aws cloudformation deploy \
    --template-file $BASE_DIR/vci-cross-tenant-datalake-bucket-readonly-role.yaml \
    --stack-name vci-cross-account-datalake-access-role-stack \
    --capabilities CAPABILITY_NAMED_IAM \
    --parameter-overrides \
        Env=$ENV \
        AWSTenant=$DSNATENANT \
        DsnaAccountId=$DsnaAccountId \
        DLAWSTenant=$DLTENANT \
        TeamTag=$TeamTag \
        DLAccountId=$DLAccountId \
    --no-fail-on-empty-changeset