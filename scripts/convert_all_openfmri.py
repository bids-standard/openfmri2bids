from openfmri2bids.converter import convert
import shutil
import dateutil
datasets = [
             'ds001', 
             'ds002', 
             'ds003', 
             'ds005', 
             {"pre":'ds006A', "post":'ds006B'},
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

def ds113b_converter(in_file, out_file):
    out_str = ""
    for line in open(in_file).readlines():
        if line.startswith("rev"):
            version = line.split("(")[0]
            desc = line.split("(")[1].split(")")[1].replace(":","")
            date = dateutil.parser.parse(line.split("(")[1].split(")")[0])
            line = version + date.strftime("%Y-%m-%d") + desc
        out_str += line
    with open(out_file, "w") as f:
        f.write(out_str)

custom_chngelog_converters = {"ds113b": ds113b_converter}


for dataset in datasets:
    if isinstance(dataset, dict):
        try:
            shutil.rmtree("/Volumes/Samsung_T1/bids_examples/symlinked/%s/"%dataset.values()[0][:-1])
        except:
            pass
        for ses_label, ds in dataset.items():
            args = {}
            if ds in custom_chngelog_converters:
                args["changelog_converter"] = custom_chngelog_converters[ds]
            convert("/Volumes/Samsung_T1/openfmri/%s/"%ds, 
                    "/Volumes/Samsung_T1/bids_examples/symlinked/%s/"%ds[:-1],
            ses=ses_label,
            nii_handling='link', **args)
    else:
        try:
            shutil.rmtree("/Volumes/Samsung_T1/bids_examples/symlinked/%s/"%dataset)
        except:
            pass
        args = {}
        if dataset in custom_chngelog_converters:
            args["changelog_converter"] = custom_chngelog_converters[dataset]
        convert("/Volumes/Samsung_T1/openfmri/%s/"%dataset, 
                "/Volumes/Samsung_T1/bids_examples/symlinked/%s/"%dataset,
                nii_handling='link',
                **args)