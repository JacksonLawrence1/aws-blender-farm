import boto3

# Get the service resource
sqs = boto3.resource('sqs')

# Get the queue. This returns an SQS.Queue instance
queue = sqs.get_queue_by_name(QueueName='render-processing-queue.fifo')

message = 'test'

if True:
	for i in range(3):
		# Generate new message
		# ensures all messages have a unique group ID so that are received by SQS
		messagebody = '{}-{}'.format(message, i)
		response = queue.send_message(MessageBody=messagebody, MessageGroupId=messagebody)

		# The response is NOT a resource, but gives you a message ID and MD5
		print('{} : was sent successfully!'.format(messagebody))

response = queue.send_message(MessageBody=message, MessageGroupId='default-group')