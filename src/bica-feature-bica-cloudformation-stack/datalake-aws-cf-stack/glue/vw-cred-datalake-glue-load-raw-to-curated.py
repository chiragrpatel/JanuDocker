import sys
from datetime import datetime, date, time, timezone
import json
import shlex
import subprocess
from awsglue.transforms import *
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from awsglue.context import GlueContext
from awsglue.job import Job
from pyspark.sql.functions import *
from pyspark.sql.types import *
from logging import *
# **need to check the code to update boto3 version
import boto3
import botocore
print('boto3 version is:')
print(boto3.__version__)

#-------------------------------------------------------------------------------------------------------------------------------------#
# */this glue job loads data from s3 raw bucket to curated bucket in parquet format. It takes parameters of bucket,schema, table/*    #
# */and file list from Step Function to process the data accordingly. Link to technical documention:  tbd                             #
#                                                */ 3/10/2021, vci data lake project */                                               #
#-------------------------------------------------------------------------------------------------------------------------------------#                                               

# create a spark session
sc = SparkContext()
glueContext = GlueContext(sc)
spark = glueContext.spark_session
logger = glueContext.get_logger()

#get job name and input parameters
args = getResolvedOptions(sys.argv,['JOB_NAME','bucket','domain','table','key_list','env'])
job = Job(glueContext)
job.init(args['JOB_NAME'], args)

#assign parameters to variables
source_bucket = args['bucket']
schema = args['domain']
table = args['table']
key_list = args['key_list']
env = args['env']
job_id = args['JOB_NAME']
source_prefix = schema+"/"+ table+"/"
raw_path = "s3://"+source_bucket+"/"+source_prefix
print ("source bucket is ",source_bucket)
print("raw path is:",raw_path)
print("source prefix is: ",source_prefix)
curated_bucket = source_bucket.replace("raw","curated")
#config_bucket = source_bucket.replace("raw","configuration")
config_bucket = "vw-cred-datalake-{}-configuration".format(env)
config_path = "s3://"+config_bucket+"/config/"+schema+"/"+table+"/"
config_prefix = "config/"+schema+"/"+table+"/"+"config_"+table+".csv"
print("curated bucket is : ",curated_bucket)
curated_path = "s3://"+curated_bucket+"/"+schema+"/"+table

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

#function to archive the data to different location
def s3_copy_archive(target_filename,target_prefix,source_prefix,archive_flag = 0):
    try:
        if (archive_flag==1):
            up_datetime = datetime.now(timezone.utc).strftime("%y-%m-%d-%H%M%S")
            up_date = datetime.today().strftime("%y-%m-%d")
            for obj in bucket.objects.filter(Prefix=source_prefix):
                name = obj.key
                print("key is: ", name)
                if name[-1]=="/":
                    continue
                target_filename = name.split("/")[-1]
                target_filename = target_filename.split(".")[0]
                dest_key = target_prefix+up_date+"/"+target_filename+"_"+up_datetime
                copy_source = {'Bucket': source_bucket, 'Key': name}
                print(copy_source)
                print(dest_key)
                resp = s3.Object(source_bucket,dest_key).copy_from(CopySource=copy_source)
                print(target_filename+" is archived")
        else:
            for obj in bucket.objects.filter(Prefix=source_prefix):
                name = obj.key
                print("key is: ", name)
                if name[-1]=="/":
                    continue
                target_filename = name.split("/")[-1]
                dest_file = target_prefix+target_filename
                copy_source = {'Bucket': source_bucket, 'Key': name}
                s3.Object(source_bucket,dest_file).copy_from(CopySource=copy_source)
                print(target_filename+" is copied")
        
        #delete files from raw after copy
        #Objs = client.list_objects_v2(Bucket=source_bucket, Prefix=source_prefix)
        try:
            for obj in bucket.objects.filter(Prefix=source_prefix):
                name = obj.key
                print("key is: ", name)
                if name[-1]=="/":
                   continue
                s3.Object(source_bucket,name).delete()
                print(name," is deleted")
        except Exception as err:
            print("delete failed ",err)
            raise("delete failed")
        
        #check if raw folder was deleted; recreate it if it was.
        try:
            s3.Object(source_bucket, source_prefix).load()
        except botocore.exceptions.ClientError as e:
            if e.response['Error']['Code'] == "404":
                # The object does not exist. create the directory
                print("folder needs to be recreated")
                client.put_object(Bucket=source_bucket, Key=source_prefix)
            else:
                # Something else has gone wrong.
                raise("recreating folder failed")

    except Exception as e:
        print("==> exception in s3_copy\n")
        msg = str(e)
        raise(msg)
    #except:
    #   print('==> Error in s3 copy')
    #   msg='Unexpected Error: \nError:{}.{},line: {}'.format(sys.exc_info().[0],sys.exc_info().[1],sys.exc_info().[2].tb_lineno)
    #   sys.exit("error occured while copying file")

#get the config file -- to use config file for the options including the schema for the glue job.
#---------------------------------------------------------------------------------#
#config_bucket = s3.Bucket(config_bucket)
#for obj in config_bucket.objects.filter(Prefix=config_prefix):
#    name = obj.key
#    s3_object = s3_resource.Object(config_bucket, key)
#    data = s3_object.get()['Body'].read().decode('utf-8').splitlines()
#    lines = csv.reader(data,delimiter='|')
#    #skip the header with next()
#    headers = next(lines)
#    print('headers: %s', headers)
#    for line in lines:
#        #print(line)
#        schema = line[1].upper
#----------------------------------------------------------------------------------#
        
#check whether file exists
try:
    file_found = check_file_exist(source_bucket,source_prefix,table)
    print ("file found is: ", file_found)
except Exception as e:
    print("check file failed: ",e)

jobcolumns = ["job_id","run_time","status","source_records","loaded_records"]
#loading data from raw to curated
if file_found == True:
    try:
        #/*schema registry can be added to define the schema of the data frame; Currently schema is inferred*/
        keys = key_list.split(",")
        for i, key in enumerate(keys):
            raw_path = "s3://"+source_bucket+"/"+key
            source_df = spark.read.option("header","true").option("inferSchema","true").option("delimiter","|").csv(raw_path)
            if i==0:
                target_df = source_df
            else:
                target_df = target_df.union(source_df)
        ct_before = target_df.count()
        #remove all null values
        target_df.na.drop("all")
        #remove duplicates
        dedupe_df = target_df.dropDuplicates()
        #Convert column names to lower case
        lower_df = dedupe_df.toDF(*[c.lower() for c in dedupe_df.columns])
        #Convert slash into hyphen in column name 
        col_df = lower_df.toDF(*list(map(lambda col : col if '/' not in col else col[1:].replace('/', '-'), lower_df.columns)))
        #Convert underscore into hyphen in column names
        #hyphen_df = col_df.toDF(*(c.replace('_', '-') for c in col_df.columns))
        #Convert whitespace into empty in column name
        final_df = col_df.toDF(*(c.replace(' ', '') for c in col_df.columns))
        ct_after_drop = final_df.count()
        if ct_before!=ct_after_drop:
            print("there are all nulls or duplicates, please check the source file")
        print('count before removing null vs after: ',ct_before, ct_after_drop)
        job_log = [job_
        final_df.printSchema()
        final_df.show(5)
        #put some validation code here#
        #---------------------------------------
        
        #---------------------------------------
        #need to parameterize partition columns and mode
        #mode can be append, overwrite
        final_df.repartition(1).write.mode('overwrite').parquet(curated_path)
    except Exception as err:
        print(job,"failed:",err)\
        
        raise(err)
    else:
        run_time = datetime.now(timezone.utc).strftime("%y-%m-%d-%H%M%S")
        job_log = [(job,run_time,"success")]
        
    #/* below code is for archive and can be uncommented if it is required */
    #else:
    #    file_name = table
    #    target_prefix = "archive/"+schema+"/"+table+"/"
    #   #source_prefix = "raw/"+schema+"/"+table+"/"
    #    archive_flag = 1
    #    s3_copy_archive(file_name,target_prefix,source_prefix,archive_flag)
    
else:
    raise Exception("no file availale from source")
    exit()

job.commit()