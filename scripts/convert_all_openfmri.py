import subprocess

from openfmri2bids.converter import convert
import shutil
import dateutil
datasets = [
             'ds001_R1.1.0',
              'ds002',
              'ds003_R1.1.0',
              'ds005_R1.1.0',
              {"pre":'ds006A_R1.1.0_raw', "post":'ds006B'},
              'ds007_R1.1.0',
              'ds008_R1.1.1_raw',
              'ds009_R1.1.0_raw',
              'ds011',
              #{"test":"ds017A", "retest":"ds017B"},
              'ds051',
              'ds052',
              'ds101',
              'ds102',
              'ds105',
             'ds107',
              #'ds108',
              'ds109',
              'ds110',
              #'ds113b',
            #  #'ds115' missing models
              #'ds116'
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

input_data_dir = "/Users/filo/data/openfmri/"
output_data_dir = "/Users/filo/data/openfmri_BIDS/"


if __name__ == '__main__':

    for dataset in datasets:
        if isinstance(dataset, dict):
            output_ds_dir = output_data_dir + "symlinked/%s/" % \
                                              list(dataset.values())[0][
                                              :-1]
            try:
                shutil.rmtree(output_ds_dir)
            except:
                pass
            for ses_label, ds in dataset.items():
                args = {}
                if ds in custom_chngelog_converters:
                    args["changelog_converter"] = custom_chngelog_converters[ds]
                convert(input_data_dir+"%s/"%ds,
                        output_ds_dir,
                ses=ses_label,
                nii_handling='link', **args)
        else:
            try:
                shutil.rmtree(output_data_dir+"symlinked/%s/"%dataset)
            except:
                pass
            args = {}
            output_ds_dir = output_data_dir + "symlinked/%s/" % dataset
            if dataset in custom_chngelog_converters:
                args["changelog_converter"] = custom_chngelog_converters[dataset]
            convert(input_data_dir+"%s/"%dataset,
                    output_ds_dir,
                    nii_handling='link',
                    **args)

        subprocess.check_call('bids-validator %s' % output_ds_dir, shell=True)