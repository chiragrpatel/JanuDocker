ENV="dev"
DLTENANT="vw-cred-datalake"
DLS3KMSkeyID="9cedac3a-cbfc-40f6-a161-311475fb6379"
DSNATENANT="vw-cred-dsna"
DsnaAccountId="014257795134"
VPCID="vpc-05c4ff1ff3066e39b"
DLAccountId="854807003520"
TeamTag="itdna"


# Deploying IAM vci-cross-account-datalake-access-role-stack
BASE_DIR=../s3
aws cloudformation deploy \
    --template-file $BASE_DIR/s3-buckets.yaml \
    --stack-name vci-cross-account-datalake-access-role-stack \
    --capabilities CAPABILITY_NAMED_IAM
    --parameter-overrides \
        Env=$ENV \
        AWSTenant=$DSNATENANT \
        DsnaAccountId=$DsnaAccountId \ 
        DLAWSTenant=$DLTENANT \
        DLAccountId=$DLAccountId \
        DLS3KMSkeyID=$DLS3KMSkeyID \      
        TeamTag=$TeamTag \
    --no-fail-on-empty-changeset

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