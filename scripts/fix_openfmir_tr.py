import os, nibabel
from glob import  glob

datasets = [
             'ds001', 
             'ds002', 
             'ds003', 
             'ds005', 
             'ds006A', 
             'ds006B',
             'ds007',
             'ds008',
             'ds009',
             'ds011',
             #{"test":"ds017A", "retest":"ds017B"},
             'ds051',
             'ds052',
             'ds101',
             'ds102',
             'ds105',
            'ds107',
             'ds108',
             'ds109',
             'ds110',
             'ds113b',
             #'ds115' missing models
             'ds116'
            ]

def fix_dataset(path):
    with open(os.path.join(path, "scan_key.txt")) as f:
        for line in f:
            items = line.split()
            if items[0] == "TR":
                real_tr = float(items[1])
    
    for bold_file in glob(os.path.join(path, "sub*", "BOLD", "task*", "bold.nii.gz")):
        nii = nibabel.load(bold_file)
        _, tr_unit = nii.header.get_xyzt_units()
        assert(tr_unit in ['sec', 'unknown'])
        if real_tr != nii.header.get_zooms()[3] or tr_unit == 'unknown':
            print "inconsistent TR; nifit file: %g %s, scan_key: %g sec, for %s"%(nii.header.get_zooms()[3], tr_unit, real_tr, nii.get_filename())
            nii.header.set_zooms(nii.header.get_zooms()[:3] + (real_tr,))
            nii.header.set_xyzt_units(nii.header.get_xyzt_units()[0], 'sec')
            nii.to_filename(nii.get_filename())

        

for ds in datasets:
    fix_dataset(os.path.join("/Volumes", "Samsung_T1", "openfmri", ds))