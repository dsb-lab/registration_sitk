import numpy as np
import os
from pyjiyama import (square_stack3D, centroid_correction_3d_based_on_mid_plane, generate_fijiyama_file_system, 
                     generate_fijiyama_stacks, openfiji, remove_dir, create_transformations_folders, move_transformation,
                     create_dir, correct_path, read_img_with_resolution, get_file_names, pad_image_and_square_array3D,
                     combine_transformations_with_preview, get_ordered_tif_files, get_max_xy_z_resolutions)
from embdevtools import construct_RGB
import SimpleITK as sitk
import shutil
import tifffile
from skimage import exposure
home = os.path.expanduser("~")
path_data = home + "/Desktop/PhD/projects/Data/blastocysts/Lana/20230607_CAG_H2B_GFP_16_cells/stack_2_channel_0_obj_bottom/crop/20230607_CAG_H2B_GFP_16_cells_stack2/"
embcode = "20230607_CAG_H2B_GFP_16_cells_stack2"
path_save = home + "/Desktop/PhD/projects/Data/blastocysts/Lana/20230607_CAG_H2B_GFP_16_cells/stack_2_channel_0_obj_bottom/crop/20230607_CAG_H2B_GFP_16_cells_stack2_registered/"

path_trans = create_dir(path_save, "transformations", return_path=True, rem=True)
path_trans_steps  = create_dir(path_trans, "steps", return_path=True, rem=True)
path_trans_globals = create_dir(path_trans, "globals", return_path=True, rem=True)

total_files = get_ordered_tif_files(path_data)
total_times = len(total_files)

files = total_files[:100]

xres_template=0
yres_template=0
zres_template=0

def pre_treatment(img):
    # img[img < 60] = 0
    img -= np.min(img)
    # img = exposure.equalize_hist(img)
    return img

### PERFORM REGISTRATION ###
for t in range(len(files)-1):
    filename = files[t]
    IMG, xyres, zres = read_img_with_resolution(correct_path(path_data) + filename)
    arr_ref = IMG[0]        
    arr_ref = pre_treatment(arr_ref)

    filename = files[t+1]
    IMG, xyres, zres = read_img_with_resolution(correct_path(path_data) + filename)
    arr_mov = IMG[0]
    arr_mov = pre_treatment(arr_mov)

    # if arr_ref.shape != arr_mov.shape:
    #     arr_ref = pad_image_and_square_array3D(arr_ref, required_size_xy=np.max(arr_mov.shape[1:]), required_size_z=arr_mov.shape[0], pad_val=np.mean(arr_ref[0,:10,:10]))

    img_ref = sitk.GetImageFromArray(arr_ref.astype("float32"))
    img_ref.SetSpacing([xyres, xyres, zres])
    img_ref.SetOrigin([int(np.rint(arr_ref.shape[2]/2)), int(np.rint(arr_ref.shape[1]/2)), int(np.rint(arr_ref.shape[0]/2))])

    if t == 0:
        sitk.WriteImage(img_ref, "{}{}.tif".format(path_save, 0))

        img_ref_template = sitk.GetImageFromArray(arr_ref.astype("float32"))
        img_ref_template.SetSpacing([xyres, xyres, zres])
        img_ref_template.SetOrigin([int(np.rint(arr_ref.shape[2]/2)), int(np.rint(arr_ref.shape[1]/2)), int(np.rint(arr_ref.shape[0]/2))])
        xres_template=xyres
        yres_template=xyres
        zres_template=zres

    img_mov = sitk.GetImageFromArray(arr_mov.astype("float32"))
    img_mov.SetSpacing([xyres, xyres, zres])
    img_mov.SetOrigin([int(np.rint(arr_mov.shape[2]/2)), int(np.rint(arr_mov.shape[1]/2)), int(np.rint(arr_mov.shape[0]/2))])

    registration_method = sitk.ImageRegistrationMethod()

    # Similarity metric settings.
    registration_method.SetMetricAs
    registration_method.SetMetricAsMattesMutualInformation(numberOfHistogramBins=50)
    registration_method.SetMetricSamplingStrategy(registration_method.RANDOM) #NONE uses all pints, RANDOM downscales them
    registration_method.SetMetricSamplingPercentage(0.01) #Percentage of downscaling

    registration_method.SetInterpolator(sitk.sitkLinear)

    # Optimizer settings.
    registration_method.SetOptimizerAsGradientDescent(
        learningRate=0.005,
        numberOfIterations=400,
        convergenceMinimumValue=1e-7,
        convergenceWindowSize=10,
    )
    registration_method.SetOptimizerScalesFromPhysicalShift()

    #Transform this initializer, 
    # (If you do not put it, nothing happens, 
    # I have to explore more what it does, I guess this specifies which transformation optimize (Euler3DTransform roations now)
    initial_transform = sitk.CenteredTransformInitializer(
        img_ref,
        img_mov,
        sitk.Euler3DTransform(),
        sitk.CenteredTransformInitializerFilter.GEOMETRY,
    )
    # Don't optimize in-place, we would possibly like to run this cell multiple times. 
    registration_method.SetInitialTransform(initial_transform, inPlace=False)

    #You can add something to plot during optimization
    def f(registration_method):
        print("loss: ",registration_method.GetMetricValue())
    registration_method.AddCommand(
        sitk.sitkEndEvent, lambda: f(registration_method)
    )
    registration_method.AddCommand(
        sitk.sitkStartEvent, lambda: f(registration_method)
    )

    # Run the fitting and get the transform
    final_transform = registration_method.Execute(img_ref, img_mov)

    # # Always check the reason optimization terminated.
    # print("Final metric value: {0}".format(registration_method.GetMetricValue()))
    # print(
    #     "Optimizer's stopping condition, {0}".format(
    #         registration_method.GetOptimizerStopConditionDescription()
    #     )
    # )

    ## Save transformations
    sitk.WriteTransform(final_transform.GetNthTransform(0), "{}step_{}.txt".format(path_trans_steps, t))



transfroms_steps = get_file_names(path_trans_steps)

# transform = sitk.Euler3DTransform([0,0,1], 0)
# transform = sitk.CompositeTransform(transform)
# transform.A

for tr in range(len(transfroms_steps)):
    step_tr = sitk.ReadTransform("{}step_{}.txt".format(path_trans_steps, tr))
    if tr==0:
        transform = sitk.CompositeTransform(step_tr)
    else:
        transform.AddTransform(step_tr)

    print("{}global_{}.txt".format(path_trans_globals, tr))
    sitk.WriteTransform(transform, "{}global_{}.txt".format(path_trans_globals, tr))

    filename = files[tr+1]
    IMG, xyres, zres = read_img_with_resolution(correct_path(path_data) + filename)
    arr_ref_template = IMG[0]
    arr_ref_template = pre_treatment(arr_ref_template)

    img_ref_template = sitk.GetImageFromArray(arr_ref_template.astype("float32"))
    img_ref_template.SetSpacing([xyres, xyres, zres])
    img_ref_template.SetOrigin([int(np.rint(arr_ref_template.shape[2]/2)), int(np.rint(arr_ref_template.shape[1]/2)), int(np.rint(arr_ref_template.shape[0]/2))])
    img_tr = sitk.Resample(img_ref_template, transform)

    sitk.WriteImage(img_tr, "{}{}.tif".format(path_save, tr+1))
    # arr_tr = sitk.GetArrayFromImage(img_tr)

    # mdata = {"axes": "ZYX", "spacing": zres_template, "unit": "um"}
    # tifffile.imwrite(
    #     "{}{}.tif".format(path_save, tr+1),
    #     arr_tr,
    #     imagej=True,
    #     resolution=(1 / xres_template, 1 / yres_template),
    #     metadata=mdata,
    # )

import matplotlib.pyplot as plt

z = 45
tplot = 29
img1 = sitk.ReadImage(correct_path(path_save) + "0.tif")
img2 = sitk.ReadImage(correct_path(path_save) + "{}.tif".format(tplot))

arr1 = sitk.GetArrayFromImage(img1)
arr1=pre_treatment(arr1)
arr2 = sitk.GetArrayFromImage(img2)

IMGSRGB_post = construct_RGB(R=arr1[z]/255.0, G=arr2[z]/255.0, B=None, order="XYC")

img1 = sitk.ReadImage(correct_path(path_data) + "0.tif")
img2 = sitk.ReadImage(correct_path(path_data) + "{}.tif".format(tplot))

arr1 = sitk.GetArrayFromImage(img1)
arr1=pre_treatment(arr1)
arr2 = sitk.GetArrayFromImage(img2)

IMGSRGB_pre = construct_RGB(R=arr1[z]/255.0, G=arr2[z]/255.0, B=None, order="XYC")

path_save_fijiyama ="/home/pablo/Desktop/PhD/projects/Data/blastocysts/Lana/20230607_CAG_H2B_GFP_16_cells/stack_2_channel_0_obj_bottom/crop/20230607_CAG_H2B_GFP_16_cells_stack2/movies_registered_0/20230607_CAG_H2B_GFP_16_cells_stack2/registered_0/"

img1 = sitk.ReadImage(correct_path(path_save_fijiyama) + "t1.tif")
img2 = sitk.ReadImage(correct_path(path_save_fijiyama) + "t{}.tif".format(tplot+1))

arr1 = sitk.GetArrayFromImage(img1)
arr1=pre_treatment(arr1)
arr2 = sitk.GetArrayFromImage(img2)

IMGSRGB_fijimierda = construct_RGB(R=arr1[z]/255.0, G=arr2[z]/255.0, B=None, order="XYC")

fig, ax = plt.subplots(1,3)
ax[0].imshow(IMGSRGB_pre)
ax[0].set_title("PRE")
ax[1].imshow(IMGSRGB_post)
ax[1].set_title("POST")
ax[2].imshow(IMGSRGB_fijimierda)
ax[2].set_title("POST-FIJI")

plt.show()


import matplotlib.pyplot as plt

tplot_pre = 81
tplot_post = 82
img1 = sitk.ReadImage(correct_path(path_save) + "{}.tif".format(tplot_pre))
img2 = sitk.ReadImage(correct_path(path_save) + "{}.tif".format(tplot_post))

arr1 = sitk.GetArrayFromImage(img1)
arr1=pre_treatment(arr1)
arr2 = sitk.GetArrayFromImage(img2)

IMGSRGB_post = construct_RGB(R=np.max(arr1, axis=0)/255.0, G=np.max(arr2, axis=0)/255.0, B=None, order="XYC")

img1 = sitk.ReadImage(correct_path(path_data) + "{}.tif".format(tplot_pre))
img2 = sitk.ReadImage(correct_path(path_data) + "{}.tif".format(tplot_post))

arr1 = sitk.GetArrayFromImage(img1)
arr1=pre_treatment(arr1)
arr2 = sitk.GetArrayFromImage(img2)

IMGSRGB_pre = construct_RGB(R=np.max(arr1, axis=0)/255.0, G=np.max(arr2, axis=0)/255.0, B=None, order="XYC")

# path_save_fijiyama ="/home/pablo/Desktop/PhD/projects/Data/blastocysts/Lana/20230607_CAG_H2B_GFP_16_cells/stack_2_channel_0_obj_bottom/crop/20230607_CAG_H2B_GFP_16_cells_stack2/movies_registered_0/20230607_CAG_H2B_GFP_16_cells_stack2/registered_0/"

# img1 = sitk.ReadImage(correct_path(path_save_fijiyama) + "t1.tif")
# img2 = sitk.ReadImage(correct_path(path_save_fijiyama) + "t{}.tif".format(tplot+1))

# arr1 = sitk.GetArrayFromImage(img1)
# arr1=pre_treatment(arr1)
# arr2 = sitk.GetArrayFromImage(img2)

# IMGSRGB_fijimierda = construct_RGB(R=arr1[z]/255.0, G=arr2[z]/255.0, B=None, order="XYC")

fig, ax = plt.subplots(1,2)
ax[0].imshow(IMGSRGB_pre)
ax[0].set_title("PRE")
ax[1].imshow(IMGSRGB_post)
ax[1].set_title("POST")
# ax[2].imshow(IMGSRGB_fijimierda)
# ax[2].set_title("POST-FIJI")

plt.show()
