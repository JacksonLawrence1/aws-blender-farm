# CW22-56

WIP:

# Configure Instances

## Prerequisites

- [ ] python >3.6
- [ ] AWS ssh key configured
- [ ] Create a s3 bucket and upload the files in zip file <server_files.zip>

### Setup Python Dependencies

- [ ] create new virtual environment
- [ ] run `pip install -r requirements.txt` (boto3, argparse)

You MUST set an IAM role (LabRole ideally) so that the EC2 instances can access the s3 bucket.

# Using server_functions.py

In server_functions.py there are 3 parameters, apart from iam_role you can change all of them using the command line arguments
- key_name : the name of the key you are planning on using if you want to ssh to the machine, default is 'key' (this must be set on aws beforehand!)
- region : the region for which servers are running, default is us-east-1 and should not need to be changed
- iam_role : you must set this as the role which allows child ec2 instances when created to communicate with each other. By default I set it as the lab role however it might be different for different accounts. This will look something like this.
```
arn:aws:iam::325356440011:instance-profile/LabInstanceProfile
```
