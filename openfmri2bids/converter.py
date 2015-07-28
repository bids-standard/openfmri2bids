import os
import shutil
import json
import re
import pandas as pd
import numpy as np
from os import path
from glob import glob


def sanitize_label(label):
    return re.sub("[^a-zA-Z0-9]*", "", label)

def convert(source_dir, dest_dir, empty_nii = False):
    def mkdir(path):
        try:
            os.mkdir(path)
        except OSError:
            pass
    
    openfmri_subjects = [s.split(os.sep)[-1] for s in glob(path.join(source_dir, "sub*"))]
    print("OpenfMRI subject IDs: " + str(openfmri_subjects))
    n_digits = len(str(len(openfmri_subjects)))
    subject_template = "sub-%0" + str(n_digits) + "d"
    BIDS_subjects = [subject_template%int(s[-3:]) for s in openfmri_subjects]
    print("BIDS subject IDs: " + str(BIDS_subjects))
    
    mkdir(dest_dir)
    for openfmri_s, BIDS_s in zip(openfmri_subjects, BIDS_subjects):
        mkdir(path.join(dest_dir, BIDS_s))
        
    tasks = set([s[:7] for s in os.listdir(path.join(source_dir, openfmri_subjects[0], "BOLD")) if s.startswith("task")])
    
    tasks_dict = {}
    for task in tasks:
        tasks_dict[task] = {"runs": set([s[8:] for s in os.listdir(path.join(source_dir, openfmri_subjects[0], "BOLD")) if s.startswith(task)])}
    
    with open(os.path.join(source_dir, "models", "model001", "condition_key.txt")) as f:
        for line in f:
            items = line.split()
            task = items[0]
            condition = items[1]
            condition_name = " ".join(items[2:])
            if "conditions" not in tasks_dict[task]:
                tasks_dict[task]["conditions"] = {}
            tasks_dict[task]["conditions"][condition] = condition_name
    
    with open(os.path.join(source_dir, "task_key.txt")) as f:
        for line in f:
            words = line.split()
            tasks_dict[words[0]]['name'] = " ".join(words[1:])
    print tasks_dict
    
    for openfmri_s, BIDS_s in zip(openfmri_subjects, BIDS_subjects):
        for task in tasks:
            for run in tasks_dict[task]["runs"]:
                if len(tasks_dict[task]["runs"]) == 1:
                    trg_run = ""
                else:
                    trg_run = "_run%s"%run[4:]
                mkdir(path.join(dest_dir, BIDS_s, "functional"))
                dst = path.join(dest_dir, 
                                BIDS_s, 
                                "functional",
                                "%s_%s%s.nii.gz"%(BIDS_s, "task-%s"%sanitize_label(tasks_dict[task]['name']), trg_run))
                if empty_nii:
                    open(dst, "w").close()
                else:
                    shutil.copy(path.join(source_dir, 
                                          openfmri_s, 
                                          "BOLD", 
                                          "%s_%s"%(task, run), 
                                          "bold.nii.gz"), dst)
    
    anatomy_mapping = {"highres": "T1w",
                       "inplane": "inplaneT2"}
                    
    for openfmri_s, BIDS_s in zip(openfmri_subjects, BIDS_subjects):
        mkdir(path.join(dest_dir, BIDS_s, "anatomy"))
        for anatomy_openfmri, anatomy_bids in anatomy_mapping.iteritems():
            runs = [s[-10:-7] for s in glob(path.join(source_dir, 
                                                      openfmri_s, 
                                                      "anatomy", 
                                                      "%s*.nii.gz"%anatomy_openfmri))]
            for run in runs:
                if run == anatomy_openfmri[-3:]:
                    run = "001"
                # dirty hack
                try:
                    int(run)
                except:
                    continue
                
                if len([s for s in runs if s.isdigit()]) <= 1:
                    trg_run = ""
                else:
                    trg_run = "_run%s"%run[4:]
                    
                dst = path.join(dest_dir, 
                                BIDS_s,
                                "anatomy",
                                "%s_%s%s.nii.gz"%(BIDS_s,anatomy_bids,trg_run))
                if empty_nii:
                    open(dst, "w").close()
                else:
                    shutil.copy(path.join(source_dir, 
                                          openfmri_s, 
                                          "anatomy", 
                                          "%s%s.nii.gz"%(anatomy_openfmri, run)), dst)
    
    for task in tasks_dict.keys():
        for openfmri_s, BIDS_s in zip(openfmri_subjects, BIDS_subjects):
            for run in tasks_dict[task]["runs"]:
                if len(tasks_dict[task]["runs"]) == 1:
                    trg_run = ""
                else:
                    trg_run = "_run%s"%run[4:]

                dfs = []
                for condition_id, condition_name in tasks_dict[task]["conditions"].iteritems():
                    # TODO: check if onsets are in seconds
                    print os.path.join(source_dir, 
                                                      openfmri_s, 
                                                      "model", 
                                                      "model001", 
                                                      "onsets", 
                                                      "%s_%s"%(task, run), 
                                                      "%s.txt"%condition_id)
                    tmp_df = pd.read_csv(os.path.join(source_dir, 
                                                      openfmri_s, 
                                                      "model", 
                                                      "model001", 
                                                      "onsets", 
                                                      "%s_%s"%(task, run), 
                                                      "%s.txt"%condition_id),
                                         sep="\t",
                                         names=["onset", "duration", "weight"], 
                                         header=None,
                                         engine="python",
                                         index_col=False
                                        )
                    tmp_df["trial_type"] = condition_name
                    dfs.append(tmp_df)
                events_df = pd.concat(dfs)
                
                
                beh_path = os.path.join(source_dir, 
                                        openfmri_s, 
                                        "behav",
                                        "%s_%s"%(task, run),
                                        "behavdata.txt")
                if os.path.exists(beh_path):
                    # There is a timing discrepancy between cond and behav - we need to use approximation to match them
                    events_df["approx_onset"] = np.around(events_df["onset"],1)
                    beh_df = pd.read_csv(beh_path,
                                             sep="\t",
                                             engine="python",
                                             index_col=False
                                            )
                    
                    if "Onset" not in beh_df.columns:
                        beh_df.rename(columns={'onset': 'Onset'}, inplace=True)
                        
                    beh_df["approx_onset"] = np.around(beh_df["Onset"],1)

                    all_df = pd.merge(left=events_df, right=beh_df, left_on="approx_onset", right_on="approx_onset", how="outer")

                    # Set onset to the average of onsets reported in cond and behav since we do not know which one is true
                    all_df["onset"].fillna(all_df["Onset"], inplace=True)
                    all_df["Onset"].fillna(all_df["onset"], inplace=True)
                    all_df["onset"] = (all_df["onset"]+all_df["Onset"])/2.0
                    all_df = all_df.drop(["Onset","approx_onset"], axis=1)
                else:
                    all_df = events_df
                
                all_df.sort(columns=["onset"], inplace=True)
                dest = path.join(dest_dir, 
                                 BIDS_s,
                                 "functional",
                                 "%s_%s%s_events.tsv"%(BIDS_s, "task-%s"%sanitize_label(tasks_dict[task]['name']), trg_run))            
                all_df.to_csv(dest, sep="\t", na_rep="n/a", index=False)

    id_dict = dict(zip(openfmri_subjects, BIDS_subjects))
    participants = pd.read_csv(os.path.join(source_dir,"demographics.txt"), sep="\t", 
                               header=None, names=["dataset", "subject_id", "sex", "age"]).drop(["dataset"], axis=1)
    participants["subject_id"] = participants["subject_id"].apply(lambda x: id_dict[x])
    participants.to_csv(os.path.join(dest_dir, "participants.tsv"), sep="\t", index=False)
    
    scan_parameters_dict = {}
    with open(os.path.join(source_dir, "scan_key.txt")) as f:
        for line in f:
            items = line.split()
            if items[0] == "TR":
                scan_parameters_dict["RepetitionTime"] = float(items[1])
    for task in tasks:
        scan_parameters_dict["TaskName"] = tasks_dict[task]['name']
        json.dump(scan_parameters_dict, open(os.path.join(dest_dir, 
                                                          "task-%s_bold.json"%sanitize_label(tasks_dict[task]['name'])), "w"),
                  sort_keys=True, indent=4, separators=(',', ': '))
