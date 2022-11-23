import boto3
import time
import sys

iam_role = "arn:aws:iam::325356440011:instance-profile/LabInstanceProfile"
region = "us-east-1"
bucket_name = "cw22-56-blender-bucket"
queue_name = "render-processing-queue.fifo"
key = "key"
amount_of_frames = 10

# given an ec2 client and instance id, terminates that instance
def terminate_server(ids):
    client = boto3.client('ec2', region_name=region)
    client.terminate_instances(InstanceIds=ids,)
    print("Termination of instances {} successful.".format(ids))

# creates a server given the key name
def create_server(count=1):
    ec2 = boto3.resource('ec2', region_name=region)
    instances = ec2.create_instances(
            ImageId="ami-077f76ddac8d4699f",
            MinCount=1,
            MaxCount=count,
            InstanceType="t2.micro",
            KeyName=key,
            IamInstanceProfile={'Arn' : iam_role}
        )
    for instance in instances:
        print("Instance of id: {} sucessfully launched".format(instance.id))
    return instances

def launch_cluster():
    # split work into nodes based on how many frames there are
    workers = split_work()
    
    print("Initialising cluster, please wait.")
    instances = create_server(workers)
    print("Waiting for cluster to be ready")
    instance_ids = []
    # waits until all instances are in running state (ready to execute commands)
    for instance in instances:
        instance.wait_until_running()
        instance_ids.append(instance.id)
        
    # wait a bit more time to ensure no errors
    
    retry = True
    while retry:
        try:
            ssm_client = boto3.client('ssm')
            response = ssm_client.send_command(InstanceIds=instance_ids,
                                            DocumentName="AWS-RunShellScript",
                                            Parameters={
                                                'commands' : [
                                                    # commands that are ran here
                                                    # copy the script to the ec2 instance
                                                    'aws s3 cp s3://{}/scripts/get_work.py .'.format(bucket_name),
                                                    # get the box.blend file
                                                    'aws s3 cp s3://{}/blender-files/box.blend /home/ec2-user/'.format(bucket_name),
                                                    # install boto3
                                                    'pip3 install boto3',
                                                    # make a frames directory
                                                    'mkdir /home/ec2-user/frames',
                                                    # run script
                                                    'python3 get_work.py',
                                                ]
                                            })
            retry = False
            print("Instances {} are sucessfully running and commands have been sent.".format(instance_ids))
        except Exception:
            print("Instances are still booting, waiting before trying again")
            time.sleep(5)
        
    return instance_ids

def send_work_remote(id='new'):
    sqs = boto3.resource('sqs', region_name=region)
    queue = sqs.get_queue_by_name(QueueName=queue_name)
    for i in range(amount_of_frames):
        # require unique MessageDeduplicationId so that user a single user cannot spam system
        response = queue.send_message(MessageBody='frame{}'.format(i),
                                      MessageDeduplicationId='{}-{}'.format(id, i),
                                      MessageGroupId=id)
        if (response.get('Failed') != None):
            print('frame{} : was sent unsuccessfully by user {}!!!'.format(i, id))
        #print('frame{} : was sent successfully by user {}!'.format(i, id))
    print("Frames sent to queue successfully.")

# returns amount of items in the directory
# only returns a max of 1000 items due to boto3 restrictions
def get_image_folder_size():
    objs = boto3.client('s3').list_objects_v2(Bucket=bucket_name, Prefix='image-files/')
    return int(objs['KeyCount']) - 1 

def check_job_completion():
    continue_checking = True
    print("Waiting on job completion...")
    while continue_checking:
        # check if job has been completed yet
        if (get_image_folder_size() >= amount_of_frames):
            print("Job completed! terminating instances.")
            continue_checking = False
        # wait 5 seconds before checking again
        else:
            time.sleep(5)

# split work up for every 20 frames have 1 worker to work on it
def split_work():
    workers = 0
    if amount_of_frames < 20:
        workers = 1
    else:
        workers = amount_of_frames // 20
        
    # CHANGE THIS WHEN NEED SCALING
    workers = 1
    return workers

# start of program
if __name__ == "__main__":
    # send message to queue that work needs to be done
    send_work_remote()

    # launch cluster based on amount of frames
    instance_ids = launch_cluster()
    
    # continually check bucket to check if all frames have been rendered
    check_job_completion()
    
    # compile frames from bucket using ffmpeg
    print("Job has been completed! Awaiting instance termination.")
    
    # wait 30 seconds to allow instances to cleanup
    time.sleep(30)
    terminate_server(instance_ids)