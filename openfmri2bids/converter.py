from __future__ import print_function

import errno
import os
import shutil
import json
import re
from os import path
from glob import glob

import pandas as pd
import numpy as np
import datetime
import dateutil
import tokenize

from functools import reduce

NII_HANDLING_OPTS = ['empty', 'move', 'copy', 'link']  # first entry is default


def sanitize_label(label):
    return re.sub("[^a-zA-Z0-9]*", "", label)

def handle_nii(opt, src=None, dest=None):
    """Moves / copies / links / creates a .nii.gz.
    Note: many options will raise an error if the dest exists.
    """
    if opt == 'empty':
        open(dest, "w").close()
    elif opt == 'copy':
        shutil.copy(src, dest)
    elif opt == 'move':
        shutil.move(src, dest)
    elif opt == 'link':
        os.symlink(src, dest)
    else:
        raise NotImplementedError('Unrecognized nii_handling value: %s' % opt)
    
def convert_changelog(in_file, out_file):
    versions = {}
    date = None
    out_str = ""
    for line in tokenize.open(in_file).readlines():
        if len(line.strip()) > 0:
            if len(line.split(":")) == 1:
                out_str += "    " + line
            else:
                if out_str:
                    versions[date] = out_str
                date_str = line.split(":")[0]
                print(line)
                desc = line.split(":")[1]
                date = dateutil.parser.parse(date_str)
                out_str = date.strftime("%Y-%m-%d\n\n")
                out_str += "  - " + desc
    if out_str:
        versions[date] = out_str
    
    if versions:    
        versions = ["1.0.%d "%i + version[1] for i, version in enumerate(sorted(versions.items()))]
        with open(out_file, "w") as f:
            f.write("\n\n".join(reversed(versions)))

def convert_dataset_metadata(in_dir, out_dir):
    meta_dict = {}
    meta_dict["BIDSVersion"] = "1.0.0rc4"
    
    study_key_file = os.path.join(in_dir, "study_key.txt")
    if os.path.exists(study_key_file):
        meta_dict["Name"] = tokenize.open(study_key_file).read().strip()
    else:
        if in_dir.endswith("/"):
            meta_dict["Name"] = in_dir.split("/")[-1]
        else:
            meta_dict["Name"] = in_dir.split("/")[-2]
        
    ref_file = os.path.join(in_dir, "references.txt")
    if os.path.exists(ref_file):
        meta_dict["ReferencesAndLinks"] = tokenize.open(ref_file).read().strip()
        
    lic_file = os.path.join(in_dir, "license.txt")
    if os.path.exists(lic_file):
        meta_dict["License"] = tokenize.open(lic_file).read().strip()
        
    json.dump(meta_dict, open(os.path.join(out_dir,
                                           "dataset_description.json"), "w"),
                  sort_keys=True, indent=4, separators=(',', ': '))
              
    readme = os.path.join(in_dir, "README")
    if os.path.exists(readme):
        shutil.copy(readme, os.path.join(out_dir,"README"))
    elif os.path.exists(readme + ".txt"):
        shutil.copy(readme + ".txt", os.path.join(out_dir,"README"))

def convert(source_dir, dest_dir, nii_handling=NII_HANDLING_OPTS[0], warning=print, ses="", changelog_converter=convert_changelog):
    if ses:
        folder_ses = "ses-%s"%ses
        filename_ses = "_%s"%folder_ses
    else:
        folder_ses = ""
        filename_ses = ""

    def mkdir(path):
        try:
            os.makedirs(path)
        except OSError as exc: # Python >2.5
            if exc.errno == errno.EEXIST and os.path.isdir(path):
                pass
            else: raise
    
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
        print(os.listdir(path.join(source_dir, openfmri_subjects[0], "BOLD")))
        print(openfmri_subjects[0])
        runs_union = set()
        for openfmri_s in openfmri_subjects:
            runs_union = runs_union | set([s[8:] for s in os.listdir(path.join(source_dir, openfmri_s, "BOLD")) if s.startswith(task)])
        tasks_dict[task] = {"runs": runs_union}
    
    with tokenize.open(os.path.join(source_dir, "models", "model001", "condition_key.txt")) as f:
        for line in f:
            if line.strip() == "":
                break
            items = line.split()
            task = items[0]
            condition = items[1]
            condition_name = " ".join(items[2:])
            if "conditions" not in tasks_dict[task]:
                tasks_dict[task]["conditions"] = {}
            tasks_dict[task]["conditions"][condition] = condition_name
    
    with tokenize.open(os.path.join(source_dir, "task_key.txt")) as f:
        for line in f:
            words = line.split()
            tasks_dict[words[0]]['name'] = " ".join(words[1:])

    print(tasks_dict)
    
    for openfmri_s, BIDS_s in zip(openfmri_subjects, BIDS_subjects):
        for task in tasks:
            for run in tasks_dict[task]["runs"]:
                if len(tasks_dict[task]["runs"]) == 1:
                    trg_run = ""
                else:
                    trg_run = "_run-%s"%run[4:]
                mkdir(path.join(dest_dir, BIDS_s, folder_ses, "func"))
                dst = path.join(dest_dir, 
                                BIDS_s,
                                folder_ses, 
                                "func",
                                "%s%s%s%s_bold.nii.gz"%(BIDS_s, filename_ses, "_task-%s"%sanitize_label(tasks_dict[task]['name']), trg_run))
                src = path.join(source_dir, 
                                openfmri_s, 
                                "BOLD", 
                                "%s_%s"%(task, run), 
                                "bold.nii.gz")
                if not os.path.exists(src):
                    warning("%s does not exist"%src)
                    continue

                handle_nii(nii_handling, src=src, dest=dst)
    
    anatomy_mapping = {"highres": "T1w",
                       "inplane": "inplaneT2"}

    for anatomy_openfmri, anatomy_bids in anatomy_mapping.items():
        runs_union = set()

        for openfmri_s, BIDS_s in zip(openfmri_subjects, BIDS_subjects):
            subject_runs = [s.split("/")[-1] for s in glob(path.join(source_dir,
                                                      openfmri_s,
                                                      "anatomy",
                                                      "%s*.nii.gz"%anatomy_openfmri))
                            if len(s.split("/")[-1]) in [len("%s000.nii.gz"%anatomy_openfmri),
                                                         len("%s.nii.gz" % anatomy_openfmri)]]
            runs_union = runs_union | set(subject_runs)

        runs_union = sorted(list(runs_union))
        for openfmri_s, BIDS_s in zip(openfmri_subjects, BIDS_subjects):
            mkdir(path.join(dest_dir, BIDS_s, folder_ses, "anat"))

            for run_idx, run in enumerate(runs_union):
                src_run = run

                if len(runs_union) == 1:
                    trg_run = ""
                else:
                    trg_run = "_run-%d"%run_idx

                dst = path.join(dest_dir,
                                BIDS_s,
                                folder_ses,
                                "anat",
                                "%s%s%s_%s.nii.gz"%(BIDS_s, filename_ses, trg_run, anatomy_bids))
                src = path.join(source_dir,
                                openfmri_s,
                                "anatomy",
                                "%s"%src_run)
                if os.path.exists(src):
                    handle_nii(nii_handling, src=src, dest=dst)
                else:
                    print(src + " does not exists")
    
    scan_parameters_dict = {}
    with tokenize.open(os.path.join(source_dir, "scan_key.txt")) as f:
        for line in f:
            items = line.split()
            if items[0] == "TR":
                scan_parameters_dict["RepetitionTime"] = float(items[1])

    for openfmri_s, BIDS_s in zip(openfmri_subjects, BIDS_subjects):
        scans_dfs = []
        for task in tasks_dict.keys():
            for run in tasks_dict[task]["runs"]:
                if len(tasks_dict[task]["runs"]) == 1:
                    trg_run = ""
                else:
                    trg_run = "_run-%s"%run[4:]

                dfs = []
                parametric_columns = []
                for condition_id, condition_name in tasks_dict[task]["conditions"].items():
                    # TODO: check if onsets are in seconds
                    fpath = os.path.join(source_dir, 
                                       openfmri_s, 
                                       "model", 
                                       "model001", 
                                       "onsets", 
                                       "%s_%s"%(task, run), 
                                       "%s.txt"%condition_id)
                    if not os.path.exists(fpath):
                        warning("%s does not exist"%fpath)
                        continue
                    if os.stat(fpath).st_size == 0:
                        warning("%s is empty"%fpath)
                        continue
                    tmp_df = pd.read_csv(fpath,
                                         delimiter=r"\s+",
                                         names=["onset", "duration", "weight"], 
                                         header=None,
                                         engine="python",
                                         index_col=False,
                                         skip_blank_lines=True
                                        )
                    if tmp_df.duration.isnull().sum() > 0:
                        tmp_df = pd.read_csv(os.path.join(source_dir, 
                                                      openfmri_s, 
                                                      "model", 
                                                      "model001", 
                                                      "onsets", 
                                                      "%s_%s"%(task, run), 
                                                      "%s.txt"%condition_id),
                                         sep=" ",
                                         names=["onset", "duration", "weight"], 
                                         header=None,
                                         engine="python",
                                         index_col=False
                                        )
                    tmp_df["trial_type"] = condition_name
                    if len(tmp_df["weight"].unique()) != 1:
                        tmp_df[condition_name] = tmp_df["weight"]
                        parametric_columns.append(condition_name)
                    tmp_df.drop('weight', axis=1, inplace=True)
                    dfs.append(tmp_df)
                if dfs:
                    if len(set([len(df) for df in dfs])) == 1:
                        events_df = reduce(lambda left, right: pd.merge(left, right, on=['onset', 'duration'],
                                                                        how="outer"), dfs)
                    else:
                        events_df = pd.concat(dfs, ignore_index=True)
                    if(parametric_columns):
                        events_df = events_df.sort_values(parametric_columns, na_position="first").drop_duplicates(["onset", "duration"], keep='last')
                    while 'trial_type_x' in events_df.columns:
                        events_df.drop('trial_type_x', axis=1, inplace=True)
                        events_df.drop('trial_type_y', axis=1, inplace=True)
                else:
                    continue

                # check for RT encoded as duration
                if len(events_df["onset"].unique()) != len(events_df["onset"]) and \
                        (np.array([(events_df["duration"] == val).sum() for val in set(events_df["duration"])]) >
                            len(events_df["duration"])/2.0).any():
                    events_df["RT"] = 0
                    for i, row in events_df.iterrows():
                        if not row[[c for c in events_df.columns if c not in
                                ["duration", "onset", "RT", "trial_type"]]].any():
                            RT = row["duration"]
                            events_df.loc[events_df["onset"] == row["onset"], "RT"] = RT
                            events_df.drop(i, axis=0, inplace=True)

                
                beh_path = os.path.join(source_dir, 
                                        openfmri_s, 
                                        "behav",
                                        "%s_%s"%(task, run),
                                        "behavdata.txt")
                if os.path.exists(beh_path):
                    # There is a timing discrepancy between cond and behav - we need to use approximation to match them
                    if os.stat(beh_path).st_size == 0:
                        warning("%s is empty"%beh_path)
                        all_df = events_df
                    else:
                        unlabeled_beh = False
                        beh_df = pd.read_csv(beh_path,
                                             sep=None,
                                             #delimiter=r"\s+",
                                             engine="python",
                                             index_col=False
                                             )
                        if 'TrialOnset' in beh_df.columns:
                            beh_df.rename(columns={'TrialOnset': 'Onset'}, inplace=True)
                        if 'TR' in beh_df.columns:
                            beh_df["TR"] = (beh_df["TR"]-1)*scan_parameters_dict["RepetitionTime"]
                            beh_df["duration"] = beh_df['TR'].map(lambda x: scan_parameters_dict["RepetitionTime"])
                            beh_df.rename(columns={'TR': 'onset'}, inplace=True)
                            all_df = pd.concat([events_df, beh_df])
                            unlabeled_beh = True
                            
                        if "Onset" not in beh_df.columns:
                            if "onset" not in beh_df.columns:
                                if "Cue_Onset" not in beh_df.columns:
                                    beh_df_no_header = pd.read_csv(beh_path, sep=None, engine="python", index_col=False, header=None)
                                    if len(beh_df_no_header.index) == len(events_df.index):
                                        events_df.sort_values(by=["onset"], inplace=True)
                                        events_df.index = range(len(events_df))
                                        all_df = pd.concat([events_df, beh_df_no_header], axis=1)
                                        unlabeled_beh = True
                                    elif len(beh_df.index) == len(events_df.index):
                                        events_df.sort_values(by=["onset"], inplace=True)
                                        events_df.index = range(len(events_df))
                                        all_df = pd.concat([events_df, beh_df], axis=1)
                                        unlabeled_beh = True
                                    else:
                                        # behdata are not events
                                        try:
                                            beh_df = pd.read_csv(beh_path,
                                                     sep=" ",
                                                     engine="python",
                                                     index_col=False
                                                     )
                                        except:
                                            beh_df = pd.read_csv(beh_path,
                                                     sep=",",
                                                     engine="python",
                                                     index_col=False
                                                     )
                                        beh_df["filename"] = path.join("func",
                                                                       "%s_%s%s_bold.nii.gz"%(BIDS_s, "task-%s"%sanitize_label(tasks_dict[task]['name']), trg_run))
                                        beh_df.set_index("filename", inplace=True)
                                        scans_dfs.append(beh_df)
                                        all_df = events_df
                                else:
                                    df1 = beh_df.rename(columns={'Cue_Onset': 'Onset'}).drop(["Stim_Onset"], axis=1)
                                    df2 = beh_df.rename(columns={'Stim_Onset': 'Onset'}).drop(["Cue_Onset"], axis=1)
                                    beh_df = pd.concat([df1, df2]).sort_values(by=["Onset"])
                            else:
                                beh_df.rename(columns={'onset': 'Onset'}, inplace=True)
                    
                        if not scans_dfs and not unlabeled_beh:
                            events_df["approx_onset"] = events_df["onset"].round(1)
                            beh_df["approx_onset"] = beh_df["Onset"].round(1)
        
                            all_df = pd.merge(left=events_df, right=beh_df, left_on="approx_onset", right_on="approx_onset", how="outer")
        
                            # Set onset to the average of onsets reported in cond and behav since we do not know which one is true
                            all_df["onset"].fillna(all_df["Onset"], inplace=True)
                            all_df["Onset"].fillna(all_df["onset"], inplace=True)
                            all_df["onset"] = (all_df["onset"]+all_df["Onset"])/2.0
                            all_df = all_df.drop(["Onset","approx_onset"], axis=1)
                else:
                    all_df = events_df

                if 'RT' in all_df.columns:
                    all_df.rename(columns={'RT': 'response_time'}, inplace=True)

                all_df.sort_values(by=["onset"], inplace=True)
                dest = path.join(dest_dir, 
                                 BIDS_s,
                                 folder_ses,
                                 "func",
                                 "%s%s%s%s_events.tsv"%(BIDS_s, filename_ses, "_task-%s"%sanitize_label(tasks_dict[task]['name']), trg_run))
                #remove rows with zero duration:
                if (all_df.duration == 0).sum() > 0:
                    warning("%s original data had events with zero duration - removing."%dest)
                    warning(str(all_df[all_df.duration == 0] ))
                    all_df = all_df[all_df.duration != 0]
                # put onset, duration and trial_type in front
                cols = all_df.columns.tolist()
                cols.insert(0, cols.pop(cols.index("onset")))
                cols.insert(1, cols.pop(cols.index("duration")))
                if "trial_type" in cols:
                    cols.insert(2, cols.pop(cols.index("trial_type")))
                all_df = all_df[cols]
                
                all_df.to_csv(dest, sep="\t", na_rep="n/a", index=False)
                
        if scans_dfs:
            all_df = pd.concat(scans_dfs)
            if filename_ses:
                filename_ses_b = filename_ses[1:] + "_"
            else:
                filename_ses_b = ""
            all_df.to_csv(path.join(dest_dir, 
                                    BIDS_s,
                                    folder_ses,
                                    "%s%s_scans.tsv"%(filename_ses_b, BIDS_s)), sep="\t", na_rep="n/a", index=True)
            
    dem_file = os.path.join(source_dir,"demographics.txt")
    if not os.path.exists(dem_file):
        warning("%s does not exist"%dem_file)
    else:
        id_dict = dict(zip(openfmri_subjects, BIDS_subjects))
        participants = pd.read_csv(dem_file, delimiter=r"\s+", skip_blank_lines=True)
        if "subject_id" in participants.columns:
            participants["participant_id"] = participants["subject_id"].apply(lambda x: subject_template%int(x))
            del participants["subject_id"]
        else:
            participants = pd.read_csv(dem_file, delimiter=r"\s+", header=None, names=["dataset", "subject_id", "sex", "age", "handedness", "ethnicity"], skip_blank_lines=True).drop(["dataset"], axis=1)
            participants["participant_id"] = participants["subject_id"].apply(lambda x: id_dict[x])
            del participants["subject_id"]
        participants = participants.dropna(axis=1,how='all')
        cols = participants.columns.tolist()
        cols.insert(0, cols.pop(cols.index("participant_id")))
        participants = participants[cols]
        participants.to_csv(os.path.join(dest_dir, "participants.tsv"), sep="\t", index=False, na_rep="n/a")
    
    for task in tasks:
        scan_parameters_dict["TaskName"] = tasks_dict[task]['name']
        if filename_ses:
            filename_ses_b = filename_ses[1:] + "_"
        else:
            filename_ses_b = ""
        json.dump(scan_parameters_dict, open(os.path.join(dest_dir, 
                                                          "task-%s_bold.json"%(sanitize_label(tasks_dict[task]['name']))), "w"),
                  sort_keys=True, indent=4, separators=(',', ': '))
        
    convert_dataset_metadata(source_dir, dest_dir)
    if os.path.exists(os.path.join(source_dir, "release_history.txt")):
        changelog_converter(os.path.join(source_dir, "release_history.txt"), os.path.join(dest_dir, "CHANGES"))
