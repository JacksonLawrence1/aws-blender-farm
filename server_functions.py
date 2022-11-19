import boto3
import sys
import argparse

# enter name of your key here
key_name = "key"
region = "us-east-1"
iam_role = "arn:aws:iam::325356440011:instance-profile/LabInstanceProfile"

function_names = ['start', 'terminate', 'create', 'stop']

parser = argparse.ArgumentParser(description='Perform server functions')

# see help in each argument
parser.add_argument('--function', type=str,
                    help='What function you want to perform (start, terminate, create, stop)')
parser.add_argument('--id', type=str,
                    help='The instance id which is required for some functions')
parser.add_argument('--key', type=str,
                    help='The name of the key when creating a server')
parser.add_argument('--region', type=str, default=region,
                    help='The name of the key when creating a server')

args = parser.parse_args()

# conditionals ensuring arguments are passed correctly
if (args.function is None):
    parser.error("--function must be set")
if (args.function != 'create') and (args.id is None):
    parser.error("this function requires --id to be set.")
if (args.function == 'create') and (args.key is None):
    parser.error("this requires --key to be set.")
    

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
def create_server(key):
    ec2 = boto3.resource('ec2', region_name=args.region)
    instance = ec2.create_instances(
            ImageId="ami-036181b51acd8fd8a",
            MinCount=1,
            MaxCount=1,
            InstanceType="t2.micro",
            KeyName=key,
            IamInstanceProfile={'Arn' : iam_role}
        )
    print("Instance of id: {} sucessfully launched".format(instance[0].id))

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