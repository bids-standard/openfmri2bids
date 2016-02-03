source_folder = "/Volumes/Samsung_T1/bids_examples/symlinked"
target_folder = "/Volumes/Samsung_T1/bids_examples/empty"

import shutil, os
from glob import glob
try:
    shutil.rmtree(target_folder)
except:
    pass

import subprocess
subprocess.call("cp -R %s %s"%(source_folder, target_folder), shell=True)

for nii in glob(target_folder+"/*/*/*/*.*.gz") + glob(target_folder+"/*/*/*/*/*.*.gz"):
    os.remove(nii)
    open(nii, "w").close()
    
subprocess.call("dot_clean %s"%target_folder, shell=True)