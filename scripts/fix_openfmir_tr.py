import os, nibabel
from glob import  glob

from convert_all_openfmri import datasets, input_data_dir

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
            print("inconsistent TR; nifit file: %g %s, scan_key: %g sec, "
                  "for %s"%(nii.header.get_zooms()[3], tr_unit, real_tr,
                            nii.get_filename()))
            nii.header.set_zooms(nii.header.get_zooms()[:3] + (real_tr,))
            nii.header.set_xyzt_units(nii.header.get_xyzt_units()[0], 'sec')
            nii.to_filename(nii.get_filename())

for ds in datasets:
    if isinstance(ds, dict):
        for subds in ds.values():
            fix_dataset(os.path.join(input_data_dir, subds))
    else:
        fix_dataset(os.path.join(input_data_dir, ds))