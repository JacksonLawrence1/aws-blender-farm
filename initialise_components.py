import boto3
import sys
import configparser

work_file = 'get_work.py'

# get the relevant variables from text file
def get_variables(textfile):
    config = configparser.ConfigParser()
    config.read(textfile)
    
    blendfile = config.get("Variables", "blendfile")
    queue_name = config.get("Variables", "queue_name")
    region = config.get("Variables", "region")
    bucket_name = config.get("Variables", "bucket_name")
    iam_role = config.get("Variables", "iam_role")
        
    return (blendfile, queue_name, region, bucket_name, iam_role)

def initialise_sqs_queue(queue_name, region):
    # Get the service resource
    sqs = boto3.resource('sqs', region_name=region)
    # Create the queue. This returns an SQS.Queue instance
    try:
        sqs.create_queue(QueueName=queue_name, 
                         Attributes={'FifoQueue': 'true',
                                     'VisibilityTimeout': '240',
                                     'ContentBasedDeduplication': 'true'})  
        print("SQS queue initialised.")
    except Exception as e:
        print(e)
        return False
    
    return True

def initailise_s3_bucket(queue_name, region, bucket, blendfile):
    # Create bucket
    try:
        s3_client = boto3.client('s3', region_name=region)
        s3_client.create_bucket(Bucket=bucket)
    except Exception as e:
        print(e)
        return False
        
    # replaces get_work.py variables to ones set from text file
    write_to_get_work(queue_name, region, bucket, blendfile)

    # Starts to upload files
    client = boto3.client('s3', region_name=region)
    try:
        # first upload blender file
        client.upload_file(blendfile, bucket, 'blender-files/{}'.format(blendfile))
        
        # then upload worker script
        client.upload_file(work_file, bucket, 'scripts/{}'.format(work_file))
        
    except Exception:
        print("Upload to bucket was unsuccessful.")
        sys.exit()
    
    print("S3 bucket initialised.")
    return True

# given the queue name, region, bucket and blend file overwrites variables in get_work.py file
def write_to_get_work(queue_name, region, bucket, blendfile):
    # get all file contents and store in variable lines
    with open(work_file, 'r') as file:
        # read a list of lines into data
        lines = file.readlines()
    
    # replace variables in file with new ones
    lines[7] = 'queue_name = "{}"\n'.format(queue_name)
    lines[8] = 'region = "{}"\n'.format(region)
    lines[9] = 'bucket_name = "{}"\n'.format(bucket)
    lines[10] = 'blendfile = "{}"\n'.format(blendfile)

    # write everything back
    with open(work_file, 'w') as file:
        file.writelines(lines)

