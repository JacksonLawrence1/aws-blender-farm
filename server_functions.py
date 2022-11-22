import boto3
import argparse

# enter name of your key here
key_name = "key"
region = "us-east-1"
iam_role = "arn:aws:iam::325356440011:instance-profile/LabInstanceProfile"
bucket_name = "s3://cw22-56-blender-bucket"

function_names = ['start', 'terminate', 'create', 'stop']

parser = argparse.ArgumentParser(description='Perform server functions')

# see help in each argument
parser.add_argument('--function', type=str,
                    help='What function you want to perform (start, terminate, create, stop)')
parser.add_argument('--id', type=str,
                    help='The instance id which is required for some functions')
parser.add_argument('--key', type=str, default=key_name,
                    help='The name of the key when creating a server')
parser.add_argument('--region', type=str, default=region,
                    help='The name of the key when creating a server')

args = parser.parse_args()

# conditionals ensuring arguments are passed correctly
""" if (args.function is None):
    parser.error("--function must be set")
if (args.function != 'create') and (args.id is None):
    parser.error("this function requires --id to be set.")
if (args.function == 'create') and (args.key is None):
    parser.error("this requires --key to be set.") """
    

# given an ec2 client and instance id stops that instance from running
def start_server(client, id):
    client.start_instances(InstanceIds=[id,])
    print("Started server of id: {} successfully.".format(id))

def stop_server(client, id):
    client.stop_instances(InstanceIds=[id,])
    print("Stopped instance of id: {}.".format(id))

# given an ec2 client and instance id, terminates that instance
def terminate_server(client, id):
    client.terminate_instances(InstanceIds=[id,],)
    print("Termination of instance {} successful.".format(id))

# creates a server given the key name
def create_server(key, count=1):
    ec2 = boto3.resource('ec2', region_name=args.region)
    instances = ec2.create_instances(
            ImageId="ami-036181b51acd8fd8a",
            MinCount=1,
            MaxCount=count,
            InstanceType="t2.micro",
            KeyName=key,
            IamInstanceProfile={'Arn' : iam_role}
        )
    for instance in instances:
        print("Instance of id: {} sucessfully launched".format(instance.id))
    return instances


def launch_cluster(key):
    # here get amount of frames and launch x amount of clusters
    amount = 1
    instances = create_server(key, amount)
    instance_ids = []
    # waits until all instances are in running state (ready to execute commands)
    for instance in instances:
        instance.wait_until_running()
        instance_ids.append(instance.id)
    frames = 2
    # wait a bit more time to ensure no errors
    time.sleep(10.0)
    ssm_client = boto3.client('ssm')
    response = ssm_client.send_command(InstanceIds=instance_ids,
                                       DocumentName="AWS-RunShellScript",
                                       Parameters={
                                           'commands' : [
                                                # commands that are ran here
                                                # copy the blend file from bucket to ec2 instance
                                               'aws s3 cp {}/blender-files/box.blend .'.format(bucket_name),
                                                # render frames
                                               'blender -b box.blend -o ~/frames/frame_##### -s {} -e {}'.format(frames, frames),
                                                # copy all png files to bucket
                                               'aws s3 cp /frames/ {}/image-files/ --recursive'.format(bucket_name),
                                           ]
                                       })
    print('{} executed successfully.').format(response['Command']['CommandId'])
    # terminate instances after complete
    client = boto3.client('ec2', region_name=args.region)
    for instance in instances:
        terminate_server(client, instance.id)

# start of program
if __name__ == "__main__":
    if (args.function == 'create'):
        create_server(args.key)
    else:
        client = boto3.client('ec2', region_name=args.region)
        if (args.function == 'start'):
            start_server(client, args.id)
        elif (args.function == 'stop'):
            stop_server(client, args.id)
        elif (args.function == 'terminate'):
            terminate_server(client, args.id)
        else:
            parser.error('--function must be one of {}'.format(function_names))