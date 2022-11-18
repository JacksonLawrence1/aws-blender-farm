import boto3

# Get the service resource
sqs = boto3.resource('sqs')

# Get the queue. This returns an SQS.Queue instance
queue = sqs.get_queue_by_name(QueueName='render-processing-queue.fifo')

# Only get first message
message = queue.receive_messages(MaxNumberOfMessages=1)

print('Message received: {0}'.format(message[0].body))

# Let the queue know that the message is processed
message[0].delete()