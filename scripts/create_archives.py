'''
Created on 17 Sep 2015

@author: filo
'''
import subprocess, os
from convert_all_openfmri import output_data_dir
directory = output_data_dir + "symlinked/"
for ds in os.listdir(directory):
    print("tarring %s"%ds)
    subprocess.call('tar cL --exclude="*Icon*" -f %sarchives/%s.tar -C '
                    '%ssymlinked/ %s'%(
        output_data_dir, ds, output_data_dir, ds), shell=True)