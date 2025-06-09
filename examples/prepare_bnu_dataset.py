import argparse
import os
from os.path import join
import shutil


def create_link(source_path, target_path):
    if os.path.lexists(target_path):  # covers symlinks and real files
        if os.path.islink(target_path):
            os.unlink(target_path)  # remove the symlink only
        else:
            os.remove(target_path)
    link_target = os.path.realpath(source_path) if os.path.islink(source_path) else source_path
    os.symlink(link_target, target_path)


def prepare_dataset(source_path: str, target_path: str):
    for sub_id in range(1, 21):
        print(sub_id)
        sub_path_3t = join(source_path, 'rawdata_BIDS_3T', 'rawdata_BIDS_3T', f"sub-{sub_id:02}", 'anat')
        path_3tt1 = join(sub_path_3t, f"sub-{sub_id:02}_acq-t1mpragesag10isoTI1000_T1w.nii.gz")
        path_3tt2 = join(sub_path_3t, f"sub-{sub_id:02}_acq-t2tseCOR_echo-1_T2w.nii.gz")

        sub_path_7t = join(source_path, 'rawdata_BIDS_7T', 'rawdata_BIDS_7T', f"sub-{sub_id:02}", 'anat')
        if sub_id == 7:
            path_7tt1 = join(sub_path_7t, f"sub-{sub_id:02}_acq-t1wmprage070isoND_run-1_T1w.nii.gz")
        else:
            path_7tt1 = join(sub_path_7t, f"sub-{sub_id:02}_acq-t1wmprage070isoND_T1w.nii.gz")
        path_7tt2 = join(sub_path_7t, f"sub-{sub_id:02}_acq-t2wspace04x04x10ND_T2w.nii.gz")

        # create new folder in target
        target_case_path = join(target_path, f"sub{sub_id:02}")
        os.makedirs(target_case_path, exist_ok=True)

        # copy them
        create_link(path_3tt1, join(target_case_path, 'image_3tt1.nii.gz'))
        create_link(path_3tt2, join(target_case_path, 'image_3tt2.nii.gz'))
        create_link(path_7tt1, join(target_case_path, 'image_7tt1.nii.gz'))
        create_link(path_7tt2, join(target_case_path, 'image_7tt2.nii.gz'))


def parse_args():
    parser = argparse.ArgumentParser(description="Prepare public dataset for pipeline")
    parser.add_argument('--input', required=True, help='Path to raw dataset')
    parser.add_argument('--output', required=True, help='Path to save processed dataset')
    return parser.parse_args()

if __name__ == "__main__":
    args = parse_args()
    prepare_dataset(args.input, args.output)
