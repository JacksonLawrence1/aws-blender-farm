import boto3
import time
import subprocess
import sys
import os
import re

queue_name = "render-processing-queue.fifo"
region = "us-east-1"
bucket_name = "cw22-56-blender-bucket"
blendfile = "blendfile.blend"

# gets the last numbers of a string so it knows what frames to render
# https://stackoverflow.com/questions/7085512/check-what-number-a-string-ends-with-in-python
def get_trailing_numbers(s):
    m = re.search(r'\d+$', s)
    return int(m.group()) if m else None

def get_work(queue, retry=0):    
    # try getting jobs on queue
    local_retry = retry
    
    try:
        # try getting a message from the queue and request its MessageGroupId 
        message = queue.receive_messages(MaxNumberOfMessages=1)
        body = message[0].body
        handle = message[0].receipt_handle
        print('Work for {} received'.format(body))
        
        frame_number = get_trailing_numbers(body)
        
        # render file
        subprocess.run("sudo blender -b /home/ec2-user/{} -o /home/ec2-user/frames/frame_##### -f {}".format(blendfile, frame_number), shell=True)
        
        # ensure it file actually exists
        if (len(os.listdir('/home/ec2-user/frames/')) > 0):
            print('uploading frame to bucket')
            
            # upload frame to s3 bucket
            subprocess.run("sudo aws s3 cp /home/ec2-user/frames/ s3://{}/image-files/ --recursive".format(bucket_name), shell=True)
            message[0].delete()
            print('{} was rendered and uploaded, looking for more work'.format(body))
            
            # remove frame from directory
            subprocess.run("sudo rm -R /home/ec2-user/frames/*", shell=True)
            
            # reset retry value
            local_retry = 0
            get_work(queue, local_retry)
            return
        
        # change message visbility so immediately 
        queue.change_message_visibility(QueueUrl=queue_name, ReceiptHandle=handle, VisibilityTimeout=5)
    
    # When nothing is on the queue
    except IndexError:
        # Wait 30 seconds before checking the queue again
        print("No work on queue waiting before checking again.")
        local_retry += 1
        time.sleep(30)
        
        # retry getting work
        get_work(queue, local_retry)
        return
    
    finally:
        sqs = boto3.client('sqs', region_name=region)
        sqs.change_message_visibility(QueueUrl=queue_name, ReceiptHandle=handle, VisibilityTimeout=5)


# start of program
if __name__ == "__main__":
    # Get the service resource
    sqs = boto3.resource('sqs', region_name=region)

    # Get the queue. This returns an SQS.Queue instance
    queue = sqs.get_queue_by_name(QueueName=queue_name)
    
    get_work(queue)