import boto3
import time
import subprocess
import sys
import os

queue_name = 'render-processing-queue.fifo'
region = "us-east-1"
bucket_name = "s3://cw22-56-blender-bucket"

def get_work(queue, retry=0):    
    # try getting jobs on queue
    local_retry = retry
    try:
        # try getting a message from the queue and request its MessageGroupId 
        message = queue.receive_messages(MaxNumberOfMessages=1, AttributeNames=['MessageGroupId'])
        body = message[0].body
        message_group_id = message[0].attributes.get('MessageGroupId')
        print('Work for {} received by {}'.format(body, message_group_id))
        
        # Let the queue know that the message is processed
        message[0].delete()
        
        # render file
        frame_number = body[-1]
        # blender -b blendfile.blend -o /frames/frame_# -f 2
        # subprocess.run(["blender", "-b", "blendfile.blend", "-o", "-f", frame_number])
        render_frame(frame_number)
        print('{} was rendered, looking for more work'.format(body))
                
        # reset retry value
        local_retry = 0
    
    # If nothing on queue then wait 5 seconds before checking again
    except Exception:
        if (local_retry >= 12):
            # terminate instance
            print("Terminating instance, no work on queue for 1 minute.")
            sys.exit()
        else:
            if (len(os.listdir('/home/ec2-user/frames/')) > 0):
                # upload all frames to s3 bucket if no work found on queue
                subprocess.run("sudo aws s3 cp /home/ec2-user/frames/ {}/image-files/ --recursive".format(bucket_name), shell=True)
                print("uploaded all frames to bucket")
                # remove all files within frames directory
                subprocess.run("sudo rm -R /home/ec2-user/frames/*", shell=True)
            print("No work on queue waiting before checking again.")
            local_retry += 1
            time.sleep(5)
    get_work(queue, local_retry)

def render_frame(frame_number):
    subprocess.run("sudo blender -b box.blend -o /home/ec2-user/frames/frame_##### -f {}".format(frame_number), shell=True)
    
# start of program
if __name__ == "__main__":
    # Get the service resource
    sqs = boto3.resource('sqs', region_name=region)

    # Get the queue. This returns an SQS.Queue instance
    queue = sqs.get_queue_by_name(QueueName=queue_name)
    
    get_work(queue)