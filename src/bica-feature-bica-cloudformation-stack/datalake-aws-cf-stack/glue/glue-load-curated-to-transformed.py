import sys
from datetime import datetime, date, time, timezone
import json
from awsglue.transforms import *
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from awsglue.context import GlueContext
from awsglue.job import Job
from pyspark.sql.functions import *
# **need to fix the code to update boto3 version
import boto3
import botocore
print('boto3 version is:')
print(boto3.__version__)

#-------------------------------------------------------------------------------------------------------------------------------------#
# */this glue job loads data from s3 curated bucket to transformed bucket in parquet format. It takes parameters of bucket,table/*    #
# */and file list from Step Function to process the data accordingly. Link to technical documention:  tbd                             #
#                                                */ 3/10/2021, vci data lake project */                                               #
#-------------------------------------------------------------------------------------------------------------------------------------#                                               

# create a spark session
sc = SparkContext()
glueContext = GlueContext(sc)
spark = glueContext.spark_session
logger = glueContext.get_logger()

#get job name and input parameters
args = getResolvedOptions(sys.argv,['JOB_NAME','bucket','domain','table','env','region','account_id','sns_topic'])
job = Job(glueContext)
job.init(args['JOB_NAME'], args)

#assign parameters to variables
source_bucket = args['bucket'].replace("raw","curated")
schema = args['domain']
table = args['table']
env = args['env']
job_id = args['JOB_NAME']
region = args['region']
account_id = args['account_id']
topic = args['sns_topic']
source_prefix = schema+"/"+ table+"/"
source_path = "s3://"+source_bucket+"/"+source_prefix
print ("source bucket is ",source_bucket)
print("source path is:",source_path)
print("source prefix is: ",source_prefix)
trans_bucket = source_bucket.replace("curated","transformed")
print("transformed bucket is : ",trans_bucket)
config_bucket = source_bucket.replace("curated","config")
trans_path = "s3://"+trans_bucket+"/"+schema+"/"+table
job_path = "s3://"+config_bucket+"/job_logs/glue/"
source_table = "cur_"+schema+"_"+table
target_table = "tra_"+schema+"_"+table

#create s3 resource
client = boto3.client('s3')
s3 =  boto3.resource('s3')
bucket = s3.Bucket(source_bucket)

#function to check whether files exist
def check_file_exist(bucket, prefix, filename):
    fileFound = False
    #fileConditionFound = False
    Objs = client.list_objects_v2(Bucket=bucket, Prefix=prefix)
    print(Objs)
    for object in Objs['Contents']:
        if object['Key'].split('/')[1] == filename:
            fileFound = True
    return fileFound

#funciton to publish sns message
#topic = "vw-cred-datalake-sns-topic-glue-job"
#region = "us-east-1"
#account = "854807003520"
topic_arn= "arn:aws:sns:{}:{}:{}".format(region,account_id,topic)
print(topic_arn)
def publish_sns(topic_arn,msg,subject):
    try:
        response = sns_client.publish(
            TopicArn=topic_arn,
            Message=json.dumps({'default': json.dumps(msg)}),
            MessageStructure='json',
            Subject=subject
            )
    except Exception as e:
        print("failed to publish sns",e)
    else:
        return response["MessageId"]
#check whether file exists
#try:
#   file_found = check_file_exist(source_bucket,source_prefix,table)
#    print ("file found is: ", file_found)
#except Exception as e:
#    print("check file failed: ",e)

#loading data from raw to curated
#if file_found == True:
#jobcolumns = ["run_time","status","domain","table","source_records","loaded_records","job_id"]
jobcolumns = ["run_time","status","reason_code","domain","Source_table","target_table","source_file","source_records","loaded_records","job_id"]
ct_before = 0
ct_after_drop = 0
try:
    #/*schema registry can be added to define the schema of the data frame; Currently schema is inferred*/
    #keys = key_list.split(",")
    #for i, key in enumerate(keys):
    #raw_path = "s3://"+source_bucket+"/"+key
    target_df = spark.read.option("inferSchema","true").parquet(source_path)
    #put the transformation logic here
    #----------------------------------#
    #                                  #
    #----------------------------------#
    ct_before = target_df.count()
    #remove all null values
    target_df.na.drop("all")
        #remove duplicates
    dedupe_df = target_df.dropDuplicates()
    ct_after_drop = dedupe_df.count()
    print('count before removing null vs after: ',ct_before, ct_after_drop)
    dedupe_df.show(5)
        #put some validation code here#
        #---------------------------------------
        
        #---------------------------------------
        #need to parameterize partition columns and mode
        #mode can be append, overwrite
    dedupe_df.repartition(1).write.mode('overwrite').parquet(trans_path)
except Exception as err:
    print(job,"failed:",err)
    run_time = str(datetime.now(timezone.utc).strftime("%Y-%m-%d-%H:%M:%S"))
    job_log = [(run_time,"failure",err,schema,source_table,target_table,source_table,ct_before,ct_after_drop,job_id)]
    job_df = spark.createDataFrame(data=job_log, schema=jobcolumns)
    job_df.show()
    job_df.repartition(1).write.partitionBy("job_id").mode('append').option("delimiter","|").csv(job_path)
    msg = {"job":job_id,"status":"failed",\
            "content":"Check athena table job_logs.glue_logs for job logs and "+config_bucket+"/job_logs for error records"
            }
    subject = job_id+"failed"
    publish_sns(topic_arn,msg,subject)
    raise Exception("something wrong with loading the data")
#writing    
try:
    run_time = str(datetime.now(timezone.utc).strftime("%Y-%m-%d-%H:%M:%S"))
    job_log = [(run_time,"success","success",schema,source_table,target_table,source_table,ct_before,ct_after_drop,job_id)]
    job_df = spark.createDataFrame(data=job_log, schema=jobcolumns)
    job_df.show()
    job_df.repartition(1).write.partitionBy("job_id").mode('append').option("delimiter","|").csv(job_path)
except Exception as e:
    print(job_id," failed at saving log")
    
job.commit()

