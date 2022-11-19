import boto3
import time

queue_name = 'render-processing-queue.fifo'
region = "us-east-1"

def get_work(queue):    
    # try getting jobs on queue
    try:
        # try getting a message from the queue and request its MessageGroupId 
        message = queue.receive_messages(MaxNumberOfMessages=1, AttributeNames=['MessageGroupId'])
        body = message[0].body
        message_group_id = message[0].attributes.get('MessageGroupId')
        print('Work for {} received by {}'.format(body, message_group_id))
        
        # Let the queue know that the message is processed
        message[0].delete()
        
        # simulate rendering file
        time.sleep(2)
        print('{} was rendered, looking for more work'.format(body))
    
    # If nothing on queue then wait 5 seconds before checking again
    except Exception:
        print("No work on queue waiting before checking again.")
        time.sleep(5)
    get_work(queue)
    
# start of program
if __name__ == "__main__":
    # Get the service resource
    sqs = boto3.resource('sqs', region_name=region)

    # Get the queue. This returns an SQS.Queue instance
    queue = sqs.get_queue_by_name(QueueName=queue_name)
    
    get_work(queue)