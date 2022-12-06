import boto3
import time
import random
import argparse
import initialise_components
import blend_render_info
import sys

iam_role = "arn:aws:iam::325356440011:instance-profile/LabInstanceProfile"
region = "us-east-1"
bucket_name = "cw22-56-blender-bucket"
queue_name = "render-processing-queue.fifo"
blendfile = "blendfile.blend"
amount_of_frames = -1

termination_count = 0

parser = argparse.ArgumentParser(description='Options')

# see help in each argument
parser.add_argument('--workers', type=int,
                    help='How many workers you want (leave empty to let program decide, max 8)')
parser.add_argument('--frames', type=int,
                    help='How many frames you want')
parser.add_argument('--chaos_test', type=bool,
                    help='If you want to perform chaos testing')

args = parser.parse_args()
    
def parse_variables(variables_file):
    new_variables = initialise_components.get_variables(variables_file)
    
    global blendfile, queue_name, region, bucket_name, iam_role, amount_of_frames
    
    # formatted to: (blendfile, queue_name, region, bucket_name, iam_role, key)
    blendfile, queue_name, region, bucket_name, iam_role = new_variables
        
    # if user specifies frames then store
    if (args.frames is not None and args.frames > 0):
        amount_of_frames = args.frames
    # else get all frames from the blendfile
    else:
        frames = int(blend_render_info.read_blend_rend_chunk(blendfile)[0][1])
        if (args.workers is not None and args.workers > frames):
            print("Cannot have more workers than frames!")
        else: 
            amount_of_frames = int(blend_render_info.read_blend_rend_chunk(blendfile)[0][1])
    

# given an ec2 client and instance id, terminates that instance
def terminate_server(ids):
    client = boto3.client('ec2', region_name=region)
    
    # terminate instances
    client.terminate_instances(InstanceIds=ids,)
    print("Termination of instances {} successful.".format(ids))

def terminate_queue(queueurl):
    client = boto3.client('sqs', region_name=region)
    client.delete_queue(QueueUrl=queueurl)
    print("Termination of SQS queue {} successful. ".format(queueurl))

# creates a server given the key name
def create_server(count=1):
    ec2 = boto3.resource('ec2', region_name=region)
    instances = ec2.create_instances(
            ImageId="ami-077f76ddac8d4699f",
            MinCount=1,
            MaxCount=count,
            InstanceType="c6i.large",
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
        
        print('Waiting on job completion...')
        
        # add newly initialised ids to list
        new_instances.extend(extra_instances_ids)
        
    return new_instances

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
    
    # creates server cluster
    print("Initialising cluster, please wait.")
    instances = create_server(workers)
    
    # whilst servers are initialising
    # create s3 bucket and upload files
    initialise_components.initailise_s3_bucket(queue_name, region, bucket_name, blendfile)
    # create sqs queue
    initialise_components.initialise_sqs_queue(queue_name, region)
    
    print("Waiting for cluster to be ready")
    # check all instances are in running state (ready to execute commands)
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
                                      MessageGroupId='{}-{}'.format(id, i))
        if (response.get('Failed') != None):
            print('frame{} : was sent unsuccessfully by user {}!!!'.format(i, id))
        #print('frame{} : was sent successfully by user {}!'.format(i, id))
    print("{} frames were sent to queue successfully.".format(amount_of_frames))

# returns amount of items in the directory
# only returns a max of 1000 items due to boto3 restrictions
def get_image_folder_size():
    objs = boto3.client('s3').list_objects_v2(Bucket=bucket_name, Prefix='image-files/')
    return int(objs['KeyCount'])

def random_termination(instance_ids):
    terminate = random.randrange(0, 21)
    new_instance_ids = instance_ids.copy()
    terminate_ids = []
    
    if (terminate == 10):
        print("Choosing instances for termination")
        # terminate 1-4 instances randomly
        amount = random.randrange(1, 5)
        for _ in range(amount):
            terminating_id = random.choice(new_instance_ids)
            terminate_ids.append(terminating_id)
            new_instance_ids.remove(terminating_id)
    
    if (len(terminate_ids) >= 1):
        print('Randomly chosen instance ids: {}, terminating...'.format(terminate_ids))
        terminate_server(terminate_ids)
    
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
            # if we are randomly doing chaos testing then do termination function
            if (args.chaos_test is not None):
                random_termination(current_instances)
                
            # checks if all instances are running properly, if not bring up replacements
            current_instances = check_all_instances(current_instances)
            time.sleep(5)
    
    # gives the rest of instances        
    return current_instances

# scales amount of workers based on frame count
def split_work():
    final_workers = 0
    # sets amount of workers to how many user set in user args (if <= 8) 
    if (args.workers is not None and args.workers <= 8):
        final_workers = args.workers
    # otherwise
    else:
        # if frames are > 0 and < 8 then set amount of workers to amount of frames
        if (amount_of_frames < 8 and amount_of_frames > 0):
            final_workers = amount_of_frames
        # cap workers to 8 as that is what AWS limits
        elif (amount_of_frames >= 8):
            final_workers = 8
        # some error has happened otherwise
        else:
            print("Error whilst trying to get frames")
            sys.exit()            
    return final_workers

# simply splits workers up for every 20 frames
def split_work_20():
    final_workers = amount_of_frames // 20
    return final_workers

# start of program
if __name__ == "__main__":
    start_time = time.time()
    
    # first parse variables from text file
    parse_variables('variables.txt')
    
    if (args.chaos_test is not None):
        print('Chaos testing enabled.')
        
    # launch cluster based on amount of frames
    instance_ids = launch_cluster()
    print("--- %s seconds to initialise cluster ---" % (time.time() - start_time))
    
    # send work to queue that work needs to be done
    send_work_remote()
    
    # continually check bucket to check if all frames have been rendered
    instance_ids = check_job_completion(instance_ids)
    
    # print how many instances were terminated during chaos testing
    if (args.chaos_test is not None):
        print("{} instances were randomly terminated during chaos testing.".format(termination_count))
        
    print("--- Job completed in %s seconds ---" % (time.time() - start_time))
    
    print("See inside bucket /image-files/ for your rendered files!")
    print("Ensure to empty the image-files or delete the bucket to ensure the program works again!")
    
    print("Awaiting instance termination.")
    # wait 5 seconds for small cleanup
    time.sleep(5)
    
    # terminate EC2 instances
    terminate_server(instance_ids)
    # terminate SQS queue
    terminate_queue(queue_name)