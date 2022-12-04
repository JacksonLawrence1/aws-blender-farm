import boto3
import time
import sys

iam_role = "arn:aws:iam::325356440011:instance-profile/LabInstanceProfile"
region = "us-east-1"
bucket_name = "cw22-56-blender-bucket"
queue_name = "render-processing-queue.fifo"
key = "key"
blendfile = "blendfile.blend"
amount_of_frames = 5

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
            InstanceType="c6i.large",
            KeyName=key,
            IamInstanceProfile={'Arn' : iam_role}
        )
    for instance in instances:
        print("Instance of id: {} sucessfully launched".format(instance.id))
    return instances

# checks instance states and brings another instance if detects down
def check_all_instances(instance_ids):
    ec2_resource = boto3.resource('ec2', region_name=region)
    new_instances = instance_ids
    down_instances = []
    
    # check all instances if they are in running state
    for id in new_instances:
        instance = ec2_resource.Instance(id)
        # check if instance state is running
        if instance.state['Name'] != 'running':
            # if not running then remove from id list and add to a down list
            down_instances.append(id)
    
    # check if any instances are down in list
    if (len(down_instances) > 0):
        print('Instance id(s) {} have gone down! Attempting to bring replacement instances up.'.format(down_instances))
        
        # remove all old ids from instance id list
        new_instances = [id for id in new_instances if id not in down_instances]
                
        extra_instances = create_server(len(down_instances))
        
        # waits until all instances are in running state (ready to execute commands) and grab their ids
        extra_instances_ids = get_instance_ids(extra_instances)
        
        # attempts to run commands, if not keep retrying
        extra_instances_ids = initialise_instance(extra_instances_ids)
        
        print('New instances {} have been initialised and launched!'.format(extra_instances_ids))
        
        # add newly initialised ids to list
        new_instances.extend(extra_instances_ids)
        
    return new_instances

def launch_sqs_queue():
    # TODO:
    # FIFO Queue
    # Visibility timer = 5 mins
    # content-based duplication = true
    return

def initialise_instance(instance_ids):
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
                                                    'aws s3 cp s3://{}/blender-files/{} /home/ec2-user/'.format(bucket_name, blendfile),
                                                    # install boto3
                                                    'pip3 install --user boto3',
                                                    # make a frames directory
                                                    'mkdir /home/ec2-user/frames',
                                                    # run script
                                                    'python3 get_work.py',
                                                ]
                                            })
            retry = False
            print("Instances {} are sucessfully running and commands have been sent.".format(instance_ids))
        except Exception:
            time.sleep(5)
    return instance_ids

def get_instance_ids(instances):
    instance_ids = []
    # waits until all instances are in running state (ready to execute commands)
    for instance in instances:
        instance.wait_until_running()
        instance_ids.append(instance.id)
    return instance_ids

def launch_cluster():
    # split work into nodes based on how many frames there are
    workers = split_work()
    
    print("Initialising cluster, please wait.")
    instances = create_server(workers)
    print("Waiting for cluster to be ready")
    
    # waits until all instances are in running state (ready to execute commands)
    instance_ids = get_instance_ids(instances)
        
    # attempts to run commands, if not keep retrying
    instance_ids = initialise_instance(instance_ids)
    
    # after finished running commands successfuly return
    return instance_ids

# may need to change id if system is spammed!
def send_work_remote(id='user'):
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

def check_job_completion(instance_ids):
    continue_checking = True
    current_instances = instance_ids
    print("Waiting on job completion...")
    while continue_checking:
        # check if job has been completed yet
        if (get_image_folder_size() >= amount_of_frames):
            print("Job completed! terminating instances.")
            continue_checking = False
        # wait 5 seconds before checking again
        else:
            # checks if all instances are running properly, if not bring up replacements
            current_instances = check_all_instances(current_instances)
            time.sleep(5)
    
    # gives the rest of instances        
    return current_instances

# split work up for every 20 frames have 1 worker to work on it
def split_work():
    workers = 0
    if amount_of_frames < 20:
        workers = 1
    else:
        workers = amount_of_frames // 20
        
    # CHANGE THIS WHEN NEED SCALING
    workers = 1
    
    if (workers > amount_of_frames):
        print("Cannot have more workers than frames")
        sys.exit()
    return workers

# start of program
if __name__ == "__main__":
    # send message to queue that work needs to be done
    send_work_remote()
    start_time = time.time()
    
    # launch cluster based on amount of frames
    instance_ids = launch_cluster()
    print("--- %s seconds to initialise cluster ---" % (time.time() - start_time))
    
    # continually check bucket to check if all frames have been rendered
    instance_ids = check_job_completion(instance_ids)
    
    print("Job has been completed! Awaiting instance termination.")
    print("--- %s seconds to complete job ---" % (time.time() - start_time))
    
    # wait 30 seconds to allow instances to cleanup
    time.sleep(30)
    terminate_server(instance_ids)