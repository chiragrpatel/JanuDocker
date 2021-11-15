import json
import boto3
import csv
import uuid
from datetime import datetime
import os
import logging
from botocore.exceptions import ClientError

#s3_client = boto3.client('s3')
sfn_client = boto3.client('stepfunctions')

env = os.environ['env']
sfn = os.environ['sfn']

def lambda_handler(event, context):
    acct = context.invoked_function_arn
    print(acct)
    account_id = acct.split(':')[4]
    region = acct.split(':')[3]
    for record in event['Records']:
        bucket = record['s3']['bucket']['name']
        key = record['s3']['object']['key']
        file_name = key.split('/')[0]
        
        #invoke step function
        id = str(uuid.uuid1())
        print(id)
        input = {'bucket':bucket,'table':file_name,'env':env}
        sfn_arn = 'arn:aws:states:{}:{}:stateMachine:vw-cred-dl-{}-{}'.format(region,account_id,env,sfn)
        print(sfn_arn)
        
        try:
            response = sfn_client.start_execution(
                stateMachineArn=sfn_arn,
                name= id,
                input=json.dumps(input),
                traceHeader='sfn_dl_pipeline'
                )
        except ClientError as e:
            logging.error(e)
            print("failed:", e)
        status_date = str(response['startDate'])
    return {
        'statusCode': status_date,
        'body': json.dumps('step function invoked at'+status_date)
    }
    