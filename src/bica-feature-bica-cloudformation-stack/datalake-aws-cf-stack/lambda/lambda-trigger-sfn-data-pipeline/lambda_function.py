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
sns_topic = os.environ['sns_topic']

def lambda_handler(event, context):
    acct = context.invoked_function_arn
    print("event is: ",event)
    account_id = acct.split(':')[4]
    region = acct.split(':')[3]
    key_list = []
    bucket = event['detail']['requestParameters']['bucketName']
    key = event['detail']['requestParameters']['key']
    k_list = key.split('/')
    print(key)
    status_date = ""
    print("length is",len(k_list))
    if len(k_list)==1:
        print("this is domain only")
        status_code = "domain only"
    elif len(k_list)==2:
        print("this is domain and table only")
        status_code = "table only"
    elif len(k_list)==3:
        if key[-1]!='/':
            domain = key.split('/')[0]
            file_name = key.split('/')[1]
            key_list.append(key)
            key_str = ",".join(key_list)
            domain = key.split('/')[0]
            file_name = key.split('/')[1]
            print('the file list is: ',key_str)    
            #invoke step function
            id =domain+'-'+file_name+'_'+str(uuid.uuid1())
            print('id for step function run is :',id)
            input = {'bucket':bucket,'domain':domain,'table':file_name,'key_list':key_str,'env':env,'region':region,'account_id':account_id,'sns_topic':sns_topic}
            print(input)
            sfn_arn = 'arn:aws:states:{}:{}:stateMachine:{}'.format(region,account_id,sfn)
            print('state machine arn is : ',sfn_arn)
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
                raise Exception(e)
                #status_code = 'Failure'
            else:
                status_code = 'Success'
                status_date = str(response['startDate'])
        else:
            print("table only")
            status_code = "table only"
    else:
        print("wrong file structure")
        status_code = "wrong file structure"
        
    return {
        'statusCode': status_code,
        'body': json.dumps('step function invoked at'+status_date)
        
    }
