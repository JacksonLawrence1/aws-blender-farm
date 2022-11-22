from server_functions import launch_cluster
from server_functions import terminate_server
import boto3

bucket_name = "s3://cw22-56-blender-bucket"
frames = 2
region = "us-east-1"


def test_render():
    client = boto3.client('ssm', region)
    instance_ids = ['i-040dca2f0815eccad']
    response = client.send_command(InstanceIds=instance_ids,
                                       DocumentName="AWS-RunShellScript",
                                       Parameters={
                                           'commands' : [
                                                # commands that are ran here
                                                # copy the blend file from bucket to ec2 instance
                                                'aws s3 cp {}/blender-files/box.blend /home/ec2-user'.format(bucket_name),
                                                # render frames from -s (start frame) to -e (end frame)
                                                'sudo blender -b box.blend -o /home/ec2-user/frames/frame_##### -s {} -e {}'.format(frames, frames),
                                                # copy all png files to bucket
                                                'aws s3 cp /home/ec2-user/frames/ {}/image-files/ --recursive'.format(bucket_name)
                                           ]
                                       })
    # terminate instances after complete
    #client = boto3.client('ec2', region_name=region)
    #terminate_server(client, instance_ids[0][0])


if __name__ == "__main__":
    test_render()