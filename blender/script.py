import bpy
import sys

# parses arguments into argv
argv = sys.argv[sys.argv.index("--") + 1:]


# get amount of workers passed as arguments
workers = argv[0]
workers = int(workers)

# get information about blender scene
scene = bpy.context.scene
print("Amount of frames per worker: ", scene.frame_end // workers) # frame_end is included
