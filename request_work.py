import boto3
import argparse

# Get the queue. This returns an SQS.Queue instance
queue_name = 'render-processing-queue.fifo'
region = "us-east-1"
frames = 10

parser = argparse.ArgumentParser(description='Perform server functions')

# see help in each argument
parser.add_argument('--function', type=str,
                    help='what function you want to use')
parser.add_argument('--qname', type=str, default=queue_name,
                    help='name of the queue on aws which you are using')
parser.add_argument('--user', type=str, default='test_user',
                    help='username so can identify what jobs correspond to what user')

# send a message and must supply a unique id for each message
def send_message(message, id):
    response = queue.send_message(MessageBody=message, MessageGroupId=id)
    print('{} : was sent successfully!'.format(message))
    
def send_work(queue, id):
    for i in range(frames):
        # require unique MessageDeduplicationId so that user a single user cannot spam system
        response = queue.send_message(MessageBody='frame{}'.format(i),
                           MessageDeduplicationId='{}-{}'.format(id, i),
                           MessageGroupId=id)
        print('frame{} : was sent successfully by user {}!'.format(i, id))

# start of program
if __name__ == "__main__":
    sqs = boto3.resource('sqs', region_name=region)
    args = parser.parse_args()
    queue = sqs.get_queue_by_name(QueueName=args.qname)
    if (args.function == 'send'):
        send_work(queue, args.user)