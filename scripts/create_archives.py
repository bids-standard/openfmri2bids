'''
Created on 17 Sep 2015

@author: filo
'''
import subprocess, os
directory = "/Volumes/Samsung_T1/bids_examples/symlinked/"
for ds in os.listdir(directory):
    print("tarring %s"%ds)
    subprocess.call('tar cL --exclude="*Icon*" -f /Volumes/Samsung_T1/bids_examples/archives/%s.tar -C /Volumes/Samsung_T1/bids_examples/symlinked/ %s'%(ds, ds), shell=True)