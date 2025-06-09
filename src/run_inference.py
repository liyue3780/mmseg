import argparse
import os
from os.path import join
from picsl_c3d import Convert3D
from picsl_greedy import Greedy3D
import numpy as np
import SimpleITK as sitk


def create_link(source_path, target_path):
    if os.path.lexists(target_path):  # covers symlinks and real files
        if os.path.islink(target_path):
            os.unlink(target_path)  # remove the symlink only
        else:
            os.remove(target_path)
    link_target = os.path.realpath(source_path) if os.path.islink(source_path) else source_path
    os.symlink(link_target, target_path)


def make_non_primary_input(input, output, reference):
    if os.path.exists(input):
        create_link(input, output)
    else:
        primary_itk = sitk.ReadImage(reference)
        primary_array = sitk.GetArrayFromImage(primary_itk)
        new_array = np.random.randn(primary_array.shape[0], primary_array.shape[1], primary_array.shape[2])
        new_itk = sitk.GetImageFromArray(new_array)
        new_itk.CopyInformation(primary_itk)
        sitk.WriteImage(new_itk, output)


class MultiInference():
    def __init__(self, data_path, roi_template_path):
        repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

        self.data_path = data_path
        self.file_dict = {}
        self.file_dict['file_3tt1'] = join(data_path, 'image_3tt1.nii.gz')
        self.file_dict['file_3tt2'] = join(data_path, 'image_3tt2.nii.gz')
        self.file_dict['file_7tt2'] = join(data_path, 'image_7tt2.nii.gz')
        self.file_dict['file_7tt1_inv1'] = join(data_path, 'image_7tt1_inv1.nii.gz')
        self.file_dict['file_7tt1_inv2'] = join(data_path, 'image_7tt1_inv2.nii.gz')

        self.img_7t_t1_inv1_to_7t_t2 = join(self.data_path, 'img_7t_t1_inv1_to_7t_t2.nii.gz')
        self.img_7t_t1_inv2_to_7t_t2 = join(self.data_path, 'img_7t_t1_inv2_to_7t_t2.nii.gz')
        self.img_3t_t1_to_7t_t2 = join(self.data_path, 'img_3t_t1_to_7t_t2.nii.gz')
        self.img_3t_t2_to_7t_t2 = join(self.data_path, 'img_3t_t2_to_7t_t2.nii.gz')

        self.trim_neck_shellscript = os.path.join(repo_root, "scripts", "trim_neck.sh")

        self.template_3tt1_path = roi_template_path
        self.template_3tt1 = join(self.template_3tt1_path, 'template.nii.gz')
        self.template_roi_left = join(self.template_3tt1_path, 'left_round_in_global_space.nii.gz')
        self.template_roi_right = join(self.template_3tt1_path, 'right_round_in_global_space.nii.gz')

        self.template_to_7tt2 = join(self.data_path, 'template_to_7tt2.nii.gz')
        self.left_temlate_round_to_7tt2 = join(self.data_path, 'left_temlate_round_to_7tt2.nii.gz')
        self.right_temlate_round_to_7tt2 = join(self.data_path, 'right_temlate_round_to_7tt2.nii.gz')

    def check_file_exists(self):
        for key, path in self.file_dict.items():
            if not os.path.exists(path):
                self.file_dict[key] = None
                print(f"{path} does not exist")
    
    def unify_direction(self):
        for key, path in self.file_dict.items():
            if path is not None:
                c3d = Convert3D()
                c3d.execute(f"{path} -swapdim RSA -o {path}")
                print(f"converted {path} to RSA")
    
    def global_registration(self):
        file_7tt1_to_7tt2_rigid_matrix = join(self.data_path, 'zmatrix_7t_t1_to_7t_t2.mat')
        file_3tt1_to_7tt2_rigid_matrix = join(self.data_path, 'zmatrix_3t_t1_to_7t_t2_only_nmi.mat')

        if self.file_dict['file_7tt1_inv1'] is not None and self.file_dict['file_7tt1_inv2'] is not None:
            g = Greedy3D()
            g.execute('-a -dof 6 -ia-image-centers -n 100x50x10 -m NMI '   
                      f"-i {self.file_dict['file_7tt2']} {self.file_dict['file_7tt1_inv1']} "
                      f"-i {self.file_dict['file_7tt2']} {self.file_dict['file_7tt1_inv2']} "
                      f"-o {file_7tt1_to_7tt2_rigid_matrix}")
            
            g.execute(f"-rf {self.file_dict['file_7tt2']} "
                      f"-rm {self.file_dict['file_7tt1_inv1']} {self.img_7t_t1_inv1_to_7t_t2} "
                      f"-r {file_7tt1_to_7tt2_rigid_matrix}")
            
            g.execute(f"-rf {self.file_dict['file_7tt2']} "
                      f"-rm {self.file_dict['file_7tt1_inv2']} {self.img_7t_t1_inv2_to_7t_t2} "
                      f"-r {file_7tt1_to_7tt2_rigid_matrix}")
            print('finish registration for 7T-T1')
        
        if self.file_dict['file_3tt1'] is not None:
            g = Greedy3D()
            g.execute('-a -dof 6 -ia-image-centers -n 100x50x10 -m NMI '   
                      f"-i {self.file_dict['file_7tt2']} {self.file_dict['file_3tt1']} "
                      f"-o {file_3tt1_to_7tt2_rigid_matrix}")
            
            g.execute(f"-rf {self.file_dict['file_7tt2']} "
                      f"-rm {self.file_dict['file_3tt1']} {self.img_3t_t1_to_7t_t2} "
                      f"-r {file_3tt1_to_7tt2_rigid_matrix}")
            print('finish registration for 3T-T1')
            
            if self.file_dict['file_3tt1'] is not None:
                g.execute(f"-rf {self.file_dict['file_7tt2']} "
                          f"-rm {self.file_dict['file_3tt2']} {self.img_3t_t2_to_7t_t2} "
                          f"-r {file_3tt1_to_7tt2_rigid_matrix}")
                print('finish registration for 3T-T2')
    
    def trim_neck_for_original_3tt1(self):
        os.chmod(self.trim_neck_shellscript, 0o755)
        command = f"{self.trim_neck_shellscript} {self.file_dict['file_3tt1']} {join(self.data_path, 'image_3tt1_trim_neck.nii.gz')}"
        os.system(command)
        print('finish trimming neck in 3T-T1')
    
    def register_template_to_original_3tt1_trimed(self):
        template_to_3tt1_affine_matrix = join(self.data_path, 'zmatrix_template_to_registered_original_3tt1_trimed_ncc.mat')
        template_to_3tt1_deformable_field = join(self.data_path, 'zdeform_template_to_registered_original_3tt1_trimed_ncc.nii.gz')
        file_3tt1_to_7tt2_rigid_matrix = join(self.data_path, 'zmatrix_3t_t1_to_7t_t2_only_nmi.mat')

        g = Greedy3D()
        g.execute('-a -m NCC 2x2x2 -ia-image-centers -n 100x50x10  '
                  f"-i {join(self.data_path, 'image_3tt1_trim_neck.nii.gz')} {self.template_3tt1} "
                  f"-o {template_to_3tt1_affine_matrix}")
        
        g.execute('-m NCC 2x2x2 -ia-image-centers -n 100x50x10  '
                  f"-i {join(self.data_path, 'image_3tt1_trim_neck.nii.gz')} {self.template_3tt1} "
                  f"-it {template_to_3tt1_affine_matrix} "
                  f"-o {template_to_3tt1_deformable_field} "
                  f"-oinv {join(self.data_path, 'zdeform_inverse_warp.nii.gz')}")
        
        g.execute(f"-rf {self.file_dict['file_7tt2']} "
                  f"-rm {self.template_3tt1} {self.template_to_7tt2} "
                  f"-r {file_3tt1_to_7tt2_rigid_matrix} {template_to_3tt1_deformable_field} {template_to_3tt1_affine_matrix}")
        
        g.execute(f"-rf {self.file_dict['file_7tt2']} "
                  f"-rm {self.template_roi_left} {self.left_temlate_round_to_7tt2} "
                  f"-r {file_3tt1_to_7tt2_rigid_matrix} {template_to_3tt1_deformable_field} {template_to_3tt1_affine_matrix}")
        
        g.execute(f"-rf {self.file_dict['file_7tt2']} "
                  f"-rm {self.template_roi_right} {self.right_temlate_round_to_7tt2} "
                  f"-r {file_3tt1_to_7tt2_rigid_matrix} {template_to_3tt1_deformable_field} {template_to_3tt1_affine_matrix}")
    
    def crop_patch_using_registered_round(self):
        patch_roi = {'left': join(self.data_path, "patch_left_roi.nii.gz"),
                     'right': join(self.data_path, "patch_right_roi.nii.gz")}
        
        global_roi = {'left': self.left_temlate_round_to_7tt2,
                      'right': self.right_temlate_round_to_7tt2}

        c3d = Convert3D()
        for side_ in ['left', 'right']:
            c3d.execute(f"{global_roi[side_]} -trim 0vox -o {patch_roi[side_]}")
            c3d.execute(f"{patch_roi[side_]} {self.file_dict['file_7tt2']} -reslice-identity -o {join(self.data_path, f'patch_{side_}_7tt2.nii.gz')}")

            if self.file_dict['file_7tt1_inv1'] is not None:
                c3d.execute(f"{patch_roi[side_]} {self.img_7t_t1_inv1_to_7t_t2} -reslice-identity -o {join(self.data_path, f'patch_{side_}_7tt1_inv1.nii.gz')}")
                print(f'finish cropping {side_} 7TT1 inv1')

            if self.file_dict['file_7tt1_inv2'] is not None:
                c3d.execute(f"{patch_roi[side_]} {self.img_7t_t1_inv2_to_7t_t2} -reslice-identity -o {join(self.data_path, f'patch_{side_}_7tt1_inv2.nii.gz')}")
                print(f'finish cropping {side_} 7TT1 inv2')
            
            if self.file_dict['file_3tt1'] is not None:
                c3d.execute(f"{patch_roi[side_]} {self.img_3t_t1_to_7t_t2} -reslice-identity -o {join(self.data_path, f'patch_{side_}_3tt1.nii.gz')}")
                print(f'finish cropping {side_} 3TT1')
            
            if self.file_dict['file_3tt2'] is not None:
                c3d.execute(f"{patch_roi[side_]} {self.img_3t_t2_to_7t_t2} -reslice-identity -o {join(self.data_path, f'patch_{side_}_3tt2.nii.gz')}")
                print(f'finish cropping {side_} 3TT2')
    
    def make_local_registration_command_without_mask(self):
        g = Greedy3D()
        for side_ in ['left', 'right']:
            # input
            patch_side_7tt2 = join(self.data_path, f'patch_{side_}_7tt2.nii.gz')
            patch_side_7tt1_inv1 = join(self.data_path, f'patch_{side_}_7tt1_inv1.nii.gz')
            patch_side_7tt1_inv2 = join(self.data_path, f'patch_{side_}_7tt1_inv2.nii.gz')
            patch_side_3tt1 = join(self.data_path, f'patch_{side_}_3tt1.nii.gz')
            patch_side_3tt2 = join(self.data_path, f'patch_{side_}_3tt2.nii.gz')

            # target
            target_side_7tt1_inv1 = join(self.data_path, f'patch_{side_}_7t_t1_inv1_to_7t_t2.nii.gz')
            target_side_7tt1_inv2 = join(self.data_path, f'patch_{side_}_7t_t1_inv2_to_7t_t2.nii.gz')
            target_side_3tt1 = join(self.data_path, f'patch_{side_}_3t_t1_to_7t_t2.nii.gz')
            target_side_3tt2 = join(self.data_path, f'patch_{side_}_3t_t2_to_7t_t2.nii.gz')

            if self.file_dict['file_7tt1_inv1'] is not None and self.file_dict['file_7tt1_inv2'] is not None:
                matrix_7tt1_to_7tt2 = join(self.data_path, f'{side_}_zwmatrix_7t_t1_to_7t_t2.mat')

                g.execute('-a -dof 6 -m NCC 2x2x2 -ia-identity -n 100x50  '
                          f"-i {patch_side_7tt2} {patch_side_7tt1_inv1} "
                          f"-o {matrix_7tt1_to_7tt2}")
                
                g.execute(f"-rf {patch_side_7tt2} "
                          f"-rm {patch_side_7tt1_inv1} {target_side_7tt1_inv1} "
                          f"-r {matrix_7tt1_to_7tt2}")
                
                g.execute(f"-rf {patch_side_7tt2} "
                          f"-rm {patch_side_7tt1_inv2} {target_side_7tt1_inv2} "
                          f"-r {matrix_7tt1_to_7tt2}")
            
            if self.file_dict['file_3tt1'] is not None and self.file_dict['file_3tt2'] is not None:
                # ----- 3tt2 -----
                matrix_3tt2_to_7tt2 = join(self.data_path, f'{side_}_zwmatrix_3t_t2_to_7t_t2.mat')

                g.execute('-a -dof 6 -m WNCC 2x2x2 -gm-trim 5x5x5 -ia-identity -n 100x50  '
                          f"-i {patch_side_7tt2} {patch_side_3tt2} "
                          f"-o {matrix_3tt2_to_7tt2}")
                
                g.execute(f"-rf {patch_side_7tt2} "
                          f"-rm {patch_side_3tt2} {target_side_3tt2} "
                          f"-r {matrix_3tt2_to_7tt2}")
                
                # ----- 3tt1 -----
                matrix_3tt1_to_3tt2 = join(self.data_path, f"{side_}_zwmatrix_3t_t1_to_3t_t2.mat")
                g.execute('-a -dof 6 -m NMI -ia-identity -n 100x50  '
                          f"-i {patch_side_3tt2} {patch_side_3tt1} "
                          f"-o {matrix_3tt1_to_3tt2}")
                
                g.execute(f"-rf {patch_side_7tt2} "
                          f"-rm {patch_side_3tt1} {target_side_3tt1} "
                          f"-r {matrix_3tt2_to_7tt2} {matrix_3tt1_to_3tt2}")
    
    def make_nnunet_segmentation(self):
        nnunet_path = os.path.join(self.data_path, 'nnunet')
        input_path = os.path.join(nnunet_path, 'input')
        output_path = os.path.join(nnunet_path, 'output')
        os.makedirs(input_path, exist_ok=True)
        os.makedirs(output_path, exist_ok=True)

        ii = 1
        for side_ in ['left', 'right']:
            patch_side_7tt2 = join(self.data_path, f'patch_{side_}_7tt2.nii.gz')
            target_side_7tt1_inv1 = join(self.data_path, f'patch_{side_}_7t_t1_inv1_to_7t_t2.nii.gz')
            target_side_7tt1_inv2 = join(self.data_path, f'patch_{side_}_7t_t1_inv2_to_7t_t2.nii.gz')
            target_side_3tt1 = join(self.data_path, f'patch_{side_}_3t_t1_to_7t_t2.nii.gz')
            target_side_3tt2 = join(self.data_path, f'patch_{side_}_3t_t2_to_7t_t2.nii.gz')

            create_link(patch_side_7tt2, os.path.join(input_path, "MTL_%03.0d_0000.nii.gz" % ii))
            make_non_primary_input(target_side_7tt1_inv1, join(input_path, "MTL_%03.0d_0001.nii.gz" % ii), patch_side_7tt2)
            make_non_primary_input(target_side_7tt1_inv2, join(input_path, "MTL_%03.0d_0002.nii.gz" % ii), patch_side_7tt2)
            make_non_primary_input(target_side_3tt2, join(input_path, "MTL_%03.0d_0003.nii.gz" % ii), patch_side_7tt2)
            make_non_primary_input(target_side_3tt1, join(input_path, "MTL_%03.0d_0004.nii.gz" % ii), patch_side_7tt2)
            ii = ii + 1
        
        command = f'nnUNetv2_predict -i {input_path} -o {output_path} -d 600 -c 3d_fullres -tr ModAugAllFourUNetTrainer'
        os.system(command)

        # segmentation to case folder
        create_link(join(output_path, 'MTL_001.nii.gz'), join(self.data_path, 'seg_left.nii.gz'))
        create_link(join(output_path, 'MTL_002.nii.gz'), join(self.data_path, 'seg_right.nii.gz'))
        
    def execute(self):
        # prestep: unify data direction
        self.check_file_exists()
        self.unify_direction()

        # step 1
        self.global_registration()

        # step 2
        if self.file_dict['file_3tt1'] is not None:
            self.trim_neck_for_original_3tt1()
            self.register_template_to_original_3tt1_trimed()
        self.crop_patch_using_registered_round()

        # step 3
        self.make_local_registration_command_without_mask()

        # step 4
        self.make_nnunet_segmentation()


def parse_args():
    parser = argparse.ArgumentParser(description="Prepare public dataset for pipeline")
    parser.add_argument('--dataset_path', required=True, help='Path to format-converted dataset')
    parser.add_argument('--template_path', required=True, help='Path to 3T-T1w template')
    return parser.parse_args()


if __name__ == '__main__':
    args = parse_args()
    
    sub_list = os.listdir(args.dataset_path)
    for sub_ in sub_list:
        print(f'process {sub_}')
        sub_path = join(args.dataset_path, sub_)
        segmenter = MultiInference(sub_path, args.template_path)
        segmenter.execute()