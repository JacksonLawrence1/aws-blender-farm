# CW22-56

Jackson Lawrence, fi19710
Blender Rendering farm application

blend_render_info.py was NOT made by me, it is a python script made by the Blender developers which allows reading contents of a blender file. Importantly, this couldn't be imported from the python library ```bpy``` therefore I uploaded the relevant file here.

## Prerequisites

- [ ] python >3.6
- [ ] AWS ssh key configured

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

### Running the program
The master node is run locally and can be simply run by using:
```
python master_node.py
```
WARNING: this will launch 8 c6i.large instances and attempt to render 200 frames taking approximately 1.5 hours - use the *optional* arguments below for a more grounded execution.

- [ ] --workers: INT, override how many workers you want to program to use (instead of it automatically scaling)
- [ ] --frames: INT, override how many frames you want rendered from 0-X, X being the amount of frames you want rendered.
- [ ] --chaos_test: BOOL, if set to True then the program will randomly start terminating instances to simulate malicious activity

Recommended:\
```python master_node.py --frames=8``` renders 8 frames of the animation taking  ~4 mins\
```python master_node.py --frames=32``` renders 32 frames of the animation taking ~12 mins\
```python master_node.py --frames=8 --workers=4``` If you want to test using half as many workers as default (~twice as long)\
```python master_node.py --frames=32 --chaos_test=True``` Unpredictable for how long it takes due to random termination, but useful if you want to test the fault-tolerance of system.\

The program should output all the rendered files into the S3 bucket!
![rendered files](https://user-images.githubusercontent.com/42301022/206001982-86f93f05-c21c-478d-b749-47a3a7ebbfaf.png)

If running the program more than once you MUST delete the bucket or empty the image-files folder within the bucket in order to allow the program to function properly again.
