# CW22-56

WIP:

# Configure Instances

## Prerequisites

- [ ] python >3.6
- [ ] AWS ssh key configured
- [ ] Create a s3 bucket and upload the files in zip file <server_files.zip>

### Setup Python Dependencies

- [ ] create new virtual environment
- [ ] run `pip install -r requirements.txt` or install boto3, configparser and argparse manually
- [ ] Ensure master_node.py, get_work.py, initialise_components.py, blend_render_info.py and blendfile.blend are all in the same directory!


### Setup variables.txt

The variables.txt file contains variables which should be setup beforehand, but most are already setup for a sample tutorial.
- [ ] blendfile: you can leave this as blendfile.blend which is provided
- [ ] queue_name: if you want to name the sqs queue, however you can leave this as is, as it gets deleted afterwards
- [ ] region: if you want to change the region of aws components, but should be left as us-east-1
- [ ] bucket_name: The name of the s3 bucket which uploads your rendered frames after complete, this will not be deleted automatically so ideally name it something you can find easily.
- [ ] iam_role: this has been set as the IAM Lab Instance profile which allows the EC2 instance to communicate with the queue and bucket. This may work as is, but most likely the current profile is specific to the user, so you may have to change it accordingly to another *all-powerful* role. It is of the format *arn:aws:iam::325356440011:instance-profile/LabInstanceProfile*.

### Using masternode.py
The program can simply be run by using:
```
python master_node.py
```
WARNING: this will launch 8 instances and attempt to render 200 frames taking approximately 1.5 hours - use the *optional* arguments below for a more grounded execution.

- [ ] --workers: INT, override how many workers you want to program to use (instead of it automatically scaling)
- [ ] --frames: INT, override how many frames you want rendered from 0-X, X being the amount of frames you want rendered.
- [ ] --chaos_test: BOOL, if set to True then the program will randomly start terminating instances to simulate malicious activity

Recommended:\
```python master_node.py --frames=8``` renders 8 frames of the animation taking  ~4 mins\
```python master_node.py --frames=32``` renders 32 frames of the animation taking ~12 mins\
```python master_node.py --frames=8 --workers=4``` If you want to test using half as many workers as default (~twice as long)\
```python master_node.py --frames=32 --chaos_test=True``` Unpredictable for how long it takes due to random termination, but useful if you want to test the fault-tolerance of system.\

If running the program more than once you MUST delete the bucket or empty it so the program can function again properly.
