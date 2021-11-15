import sys
from datetime import datetime, date, time, timezone
import json
import subprocess
from awsglue.transforms import *
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from awsglue.context import GlueContext
from awsglue.job import Job
from pyspark.sql.functions import *
from pyspark.sql.functions import row_number,lit
from pyspark.sql.window import Window
# **need to check the code to update boto3 version**#
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
args = getResolvedOptions(sys.argv,['JOB_NAME','bucket','domain','table','key_list','env','region','account_id','sns_topic'])
job = Job(glueContext)
job.init(args['JOB_NAME'], args)

#assign parameters to variables
source_bucket = args['bucket']
schema = args['domain']
table = args['table']
key_list = args['key_list']
env = args['env']
job_id = args['JOB_NAME']
region = args['region']
account_id = args['account_id']
topic = args['sns_topic']
source_prefix = schema+"/"+ table+"/"
raw_path = "s3://"+source_bucket+"/"+source_prefix
print ("source bucket is ",source_bucket)
print("raw path is:",raw_path)
print("source prefix is: ",source_prefix)
curated_bucket = source_bucket.replace("raw","curated")
config_bucket = source_bucket.replace("raw","config")
config_path = "s3://"+config_bucket+"/config/"+schema+"/"+table+"/"
config_prefix = "config/"+schema+"/"+table+"/"+"config_"+table+".csv"
print("curated bucket is : ",curated_bucket)
curated_path = "s3://"+curated_bucket+"/"+schema+"/"+table
job_path = "s3://"+config_bucket+"/job_logs/glue/"
source_table = "raw_"+schema+"_"+table
target_table = "cur_"+schema+"_"+table
#topic = "vw-cred-datalake-sns-topic-glue-job"
#create s3 resource
client = boto3.client('s3')
s3 =  boto3.resource('s3')
bucket = s3.Bucket(source_bucket)

#create sns resource
sns_client = boto3.client('sns')

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
            up_datetime = datetime.now(timezone.utc).strftime("%Y-%m-%d-%H%M%S")
            up_date = datetime.today().strftime("%Y-%m-%d")
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
try:
    file_found = check_file_exist(source_bucket,source_prefix,table)
    print ("file found is: ", file_found)
except Exception as e:
    print("check file failed: ",e)

#structure for log table
jobcolumns = ["run_time","status","reason_code","domain","Source_table","target_table","source_file","source_records","loaded_records","job_id"]
ct_before = 0
ct_after_drop = 0
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
        #Convert column names to lower case
        lower_df = target_df.toDF(*[c.lower() for c in target_df.columns])
        #Convert slash into hyphen in column name 
        col_df = lower_df.toDF(*list(map(lambda col : col if '/' not in col else col[1:].replace('/', '-'), lower_df.columns)))
        #Convert underscore into hyphen in column names
        #hyphen_df = col_df.toDF(*(c.replace('_', '-') for c in col_df.columns))
        #Convert whitespace into empty in column name
        final_df = col_df.toDF(*(c.replace(' ', '') for c in col_df.columns))
        #remove duplicates
        #dedupe_df = target_df.dropDuplicates()
        #dedupe_df = spark.sql(""" select *, row from tbl_target""")
        col = final_df.columns
        col1 = final_df.columns[0]
        print(col)
        print(col1)
        win = Window.partitionBy(final_df.columns).orderBy(col1)
        df_with_rn = final_df.withColumn("row_num", row_number().over(win))
        df_with_rn.createOrReplaceTempView("tbl_stage")
        deduped_df = spark.sql(""" select * from tbl_stage where row_num = 1
                               """)
        deduped_df.drop("row_num")
        deduped_df.show(5)
        dup_df = spark.sql(""" select * from tbl_stage where row_num >1
                           """)
        if dup_df.count()>0:
            load_time = str(datetime.now(timezone.utc).strftime("%Y-%m-%d-%H:%M:%S"))
            err_path = "s3://"+config_bucket+"/job_logs/"+schema+"/"+table+"/curated/"+load_time
            dup_df.repartition(1).write.mode('append').option("header","true").option("delimiter","|").csv(err_path)
        ct_after_drop = deduped_df.count()
        if ct_before!=ct_after_drop:
            print("there are all nulls or duplicates, please check the source file")
            msg = {"job":job_id,"status":"validation failed",\
            "content":"Check athena table job_logs.glue_logs for job logs and "+config_bucket+"/job_logs for error records"
            }
            print(msg)
            subject = job_id+" had validation errors"
            publish_sns(topic_arn,msg,subject)
        print('count before removing null vs after: ',ct_before, ct_after_drop)
        deduped_df.printSchema()
        #deduped_df.show(5)
        #put some validation code here#
        #---------------------------------------
        
        #---------------------------------------
        #need to parameterize partition columns and mode
        #mode can be append, overwrite
        deduped_df.repartition(1).write.mode('overwrite').parquet(curated_path)
    except Exception as err:
        print(job,"failed:",err)
        run_time = str(datetime.now(timezone.utc).strftime("%Y-%m-%d-%H:%M:%S"))
        reason = str(err)
        ct_after_drop = 0
        job_log = [(run_time,"failure",reason,schema,source_table,target_table,key_list,ct_before,ct_after_drop,job_id)]
        job_df = spark.createDataFrame(data=job_log, schema=jobcolumns)
        job_df.show()
        try:
            job_df.repartition(1).write.partitionBy("job_id").mode('append').option("delimiter","|").csv(job_path)
        except Exception as e:
            print(e)
            #raise(e)
        msg = {"job":job_id,"status":"job failed",\
            "content":"Check athena table job_logs.glue_logs for job logs and "+config_bucket+"/job_logs for error records"
            }
        print(msg)
        subject = job_id+" failed"
        publish_sns(topic_arn,msg,subject)
        raise Exception("something wrong with loading the data")
    try:
        run_time = str(datetime.now(timezone.utc).strftime("%Y-%m-%d-%H:%M:%S"))
        job_log = [(run_time,"success","success",schema,source_table,target_table,key_list,ct_before,ct_after_drop,job_id)]
        job_df = spark.createDataFrame(data=job_log, schema=jobcolumns)
        job_df.show()
        job_df.repartition(1).write.partitionBy("job_id").mode('append').option("delimiter","|").csv(job_path)
    except Exception as e:
        print(job_id,"failed at saving log")
        
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

