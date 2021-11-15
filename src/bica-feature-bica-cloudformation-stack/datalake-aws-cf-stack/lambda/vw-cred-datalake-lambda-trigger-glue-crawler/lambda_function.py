import json
import boto3
import time

client = boto3.client('glue', region_name='us-east-1', endpoint_url='https://glue.us-east-1.amazonaws.com')
tenant='vw-cred-datalake'
TeamTag='itdna'
env='dev'
crawler_iam_role = 'glue-service-role'

'''
Assumptions:
1. There will be one payload file per table per domain.
2. Folder structure will adhere to s3://bucket-name/domain-name/table-name/file-name

'''

def lambda_handler(event, context):
    
    try:
        print(event)
        # Retrieve Bucket name and domain name from event for which crawler needs to be created.
        
        s3_bucket = event['Records'][0]['s3']['bucket']['name']
        vci_domain = event['Records'][0]['s3']['object']['key'].split("/",1)[0]
        vci_table_name = event['Records'][0]['s3']['object']['key'].split("/",1)[1].split("/",1)[0]
        event_type = event['Records'][0]['eventName']
        print("s3_bucket: " + s3_bucket)
        print("vci_domain: " + vci_domain)
        print("vci_table_name: " + vci_table_name)
        print("event_type: " + event_type)
        
        #if event_type.split(":",1)[0] == 'ObjectCreated':
        
        print(event['Records'][0]['s3']['object']['key'].split("/"))
        if len(event['Records'][0]['s3']['object']['key'].split("/")) <= 2:
            print(f"Folder structure s3://{s3_bucket}/{vci_domain}/{vci_table_name} is not correct. Please adhere to s3://bucket-name/domain-name/table-name/file-name format.")
            return
        elif event['Records'][0]['s3']['object']['key'].split("/")[2] == '':
            print(f"Top level Folder structure s3://{s3_bucket}/{vci_domain}/{vci_table_name} is not correct. Payload file is missing. Please adhere to s3://bucket-name/domain-name/table-name/file-name format either to run crawler or create a new one if not existing already.")
            return
        else:


            list_of_glue_databases = []
            
            glue_db_response = client.get_databases()
            
            list_of_glue_databases = glue_db_response['DatabaseList']

            db_flag = True
            
            while db_flag:
                if 'NextToken' in glue_db_response:
                    print(counter)
                    glue_db_response = client.get_databases(NextToken=glue_db_response['NextToken'])
                    list_of_glue_databases = list_of_glue_databases + glue_db_response['DatabaseList']
                    print(list_of_glue_databases)
                else:
                   db_flag = False 
            
            db_name_list = []
            
            for i in range(len(list_of_glue_databases)):
                db_name_list.append(list_of_glue_databases[i]['Name'])


            crawler_database_name = vci_domain 
            if crawler_database_name not in db_name_list:
                response = client.create_database(
                    DatabaseInput={
                        'Name': crawler_database_name
                        }
                )
                print("New glue database created for the domain: " + crawler_database_name)

            crawlers_list = []
            
            response = client.get_crawlers()
            crawlers_list = crawlers_list + response['Crawlers']
            flag = True
            
            while flag:
                if 'NextToken' in response:
                    response = client.get_crawlers(NextToken=response['NextToken'])
                    crawlers_list = crawlers_list + response['Crawlers']
                else:
                   flag = False 
            
            
            crawlers = crawlers_list
            
            for i in range(len(crawlers)):
                crawler_name = crawlers[i]['Name']
        
                crawler_s3_targets = crawlers[i]['Targets']['S3Targets']
                
                for j in range(len(crawler_s3_targets)):
                    path_dict = crawler_s3_targets[j]
                    path = path_dict['Path']
                    path_list = path.split("://",1)[1].split("/")
                    #print(path_list)
                    
                    if len(path_list) > 2:
                        
                        crawler_bucket = path_list[0]
                        crawler_database = path_list[1]
                        tableprefix = path_list[2]
                        
                        if s3_bucket == crawler_bucket and crawler_database_name == crawler_database and tableprefix == vci_table_name:
                            run_crawler_response = client.start_crawler(Name=crawler_name)
                            print(f"Glue DB: {crawler_database} exists. Running Crawler: {crawler_name} for table: {vci_table_name}")
                            return 
            
            if s3_bucket.split("-")[-1] == 'curated':
                table_prefix = 'cur_'
                s3_suffix = 'cur'
            elif s3_bucket.split("-")[-1] == 'raw':
                table_prefix = 'raw_'
                s3_suffix = 'raw'
            elif s3_bucket.split("-")[-1] == 'transformed':
                table_prefix = 'tra_'
                s3_suffix = 'tra'
            else:
                print(f"{s3_bucket} is not one of Curated, Raw or Transformed buckets.")
                return
            
            create_crawler_response = client.create_crawler(
                                        Name= crawler_database_name + "_" + vci_table_name + "_" + s3_suffix,
                                        Role=crawler_iam_role,
                                        DatabaseName=crawler_database_name,
                                        Targets={
                                            'S3Targets': [
                                                {
                                                    'Path': 's3://' + s3_bucket + '/' + crawler_database_name + '/' + vci_table_name
                                                },
                                            ]
                                        },
                                        TablePrefix=table_prefix + crawler_database_name + "_",
                                        SchemaChangePolicy={
                                            'UpdateBehavior': 'UPDATE_IN_DATABASE',
                                            'DeleteBehavior': 'LOG'
                                        },
                                        RecrawlPolicy={
                                            'RecrawlBehavior': 'CRAWL_EVERYTHING'
                                        },
                                        LineageConfiguration={
                                            'CrawlerLineageSettings': 'ENABLE'
                                        },
                                        Configuration='{"Version": 1.0,"Grouping": {"TableGroupingPolicy": "CombineCompatibleSchemas" }}',
                                        Tags={
                                            'vci:team': TeamTag,
                                            'env': env,
                                            'tenant': tenant
                                        }
                                    )
            
            
            print("Crawler created: " + crawler_database_name + "_" + vci_table_name + "_" + s3_suffix)   
            print("sleeping for 10 sec...")
            time.sleep(10)
            print("Awake now. running the crawler..")
            print("Crawler being run: " + crawler_database_name + "_" + vci_table_name + "_" + s3_suffix)
            print("Table " + table_prefix + crawler_database_name + "_" + vci_table_name + " will be created under database: " + crawler_database_name)
            run_crawler_response = client.start_crawler(Name=crawler_database_name + "_" + vci_table_name + "_" + s3_suffix)
            
            
    except Exception as e:
            print(e)
            raise(e)