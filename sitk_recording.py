import SimpleITK as sitk
import matplotlib.pyplot as plt
import numpy as np
import skimage
import io
import os
import shutil
import argparse
import json

#Parser
parser = argparse.ArgumentParser(
                    prog='Video recorder',
                    description='This script goes over the analysis and correction of a film.')

parser.add_argument('-s','--setup',action='store_true',help="Setup the analysis folder. If the folder exist, it will throw an error.")
parser.add_argument('-sf','--setupforce',action='store_true',help="Remove any setup folder if it already exists and setup the analysis folder.")
parser.add_argument('-pa','--preanalysis',action='store_true',help="Perform the preanalysis step.")
parser.add_argument('folder',help="Folder where your images with names in order are stored.")

args = parser.parse_args()

# Functions
def outputfolder_(folder):
    return f"{folder}_output"

def setup_(folder):

    outputfolder = outputfolder_(folder)

    print(f"Making new analysis folder in {outputfolder}.")

    os.mkdir(outputfolder)
    os.mkdir(f"{outputfolder}/transforms")
    os.mkdir(f"{outputfolder}/results")
    os.mkdir(f"{outputfolder}/preanalysis")
    os.mkdir(f"{outputfolder}/preanalysis/plots")
    os.mkdir(f"{outputfolder}/preanalysis/plots/histograms")
    os.mkdir(f"{outputfolder}/preanalysis/plots/projections")

    image0 = sitk.ReadImage(f"{folder}/{os.listdir(folder)[0]}")

    with open(f"{outputfolder}/parameters.json","w") as f:
        json.dump(
            {
                'files':{
                    'dimensions': image0.GetDimension(),
                    'width': image0.GetWidth(),
                    'height': image0.GetHeight(),
                    'depth': image0.GetDepth(),
                    'channels': image0.GetNumberOfComponentsPerPixel(),
                    'n_files': len(os.listdir(folder))
                },
                'preanalysis':{
                    'sample_each_n_frames':np.ceil(len(os.listdir(folder)[0])/10),
                    'pixel_downsample':[1]*image0.GetDimension(),
                    'spacing': image0.GetSpacing(),
                    'box_interest': [[0,i] for i in [image0.GetWidth(), image0.GetHeight(), image0.GetDepth()]][:image0.GetDimension()],
                    'n_hist_bins':100,
                    'threshold':0.0,
                }
            },
            f
        )

def setup(folder, force=False):
    """
    Make folder structure for the analysis from analysis.
    """
    outputfolder = outputfolder_(folder)
    if os.path.isdir(outputfolder): #Check if folder exist
        if force: #If force, remove old and make new folrder
            print(f"Old analysis folder {outputfolder} has been removed.")
            shutil.rmtree(outputfolder)
            setup_(folder)
        else: #If not force, raise exception
            raise Exception(f"Output folder '{outputfolder}' for project '{folder}' exists, if you want to overwrite it, please, remove that folder (in linux: 'rm -rf {outputfolder}').")
    else: #if it does not exist, make folder
        setup_(folder)

def preprocessing_threshold_(image_array,parameters):
    if parameters["threshold"] > 0:
        image_array_thresholded = image_array.copy()
        image_array_thresholded[image_array<parameters["threshold"]] = 0

        return image_array_thresholded
    else:
        return image_array

def preprocessing(image_array,parameters):
    image_processed = preprocessing_threshold_(image_array,parameters)
    return image_processed

def preanalysis(folder):
    #make name outputfolder
    outputfolder = outputfolder_(folder)

    #get preanalysis parameters
    with open(f"{outputfolder}/parameters.json","r") as file:
        parameters = json.load(file)["preanalysis"]
    pixel_downsample = parameters["pixel_downsample"]

    #list sample files from preanalysis
    files_list = os.listdir(folder)[::parameters["sample_each_n_frames"]]

    for i,file in enumerate(files_list):
        #load images and downsample if indicated
        if len(pixel_downsample) == 2:
            image = sitk.ReadImage(f"{folder}/{file}")[::pixel_downsample[0],::pixel_downsample[1]]
        else:
            image = sitk.ReadImage(f"{folder}/{file}")[::pixel_downsample[0],::pixel_downsample[1],::pixel_downsample[2]]
        image.SetSpacing(parameters["spacing"])

        image_array = sitk.GetArrayFromImage(image)

        #create histogram
        fig_hist,ax_hist = plt.subplots(1,1,figsize=(10,5))
        counts = ax_hist.hist(image_array.flatten(),bins=parameters["n_hist_bins"])[0]
        ax_hist.vlines(parameters["threshold"],0,np.max(counts),color="red")
        fig_hist.savefig(f"{outputfolder}/preanalysis/plots/histograms/histograms_{file.split('.')[0]}.png")
        image_array_preprocessed = preprocessing(image_array,parameters)

        #create projections (the plot code could be optimized)
        b = parameters["box_interest"]
        if len(pixel_downsample) == 2:
            #Make images of boxes of interest
            cc,rr = skimage.draw.rectangle((int(b[1][0]/parameters["pixel_downsample"][1]),int(b[0][0]/parameters["pixel_downsample"][0])),end=(int(b[1][1]/parameters["pixel_downsample"][1]),int(b[0][1]/parameters["pixel_downsample"][0])),shape=[image_array.shape[0],image_array.shape[1]])
            box_xy = np.zeros([image_array.shape[0],image_array.shape[1]])
            box_xy[cc,rr] = 1

            fig_img,ax_img = plt.subplots(1,2,figsize=(10,5))
            ax_img[0].set_title("original")
            ax_img[1].set_title("processed")

            aspect = parameters["spacing"][1]*parameters["pixel_downsample"][1]/(parameters["spacing"][0]*parameters["pixel_downsample"][0])
            ax_img[0].imshow(image_array,aspect=aspect)
            ax_img[0].imshow(box_xy,cmap="Reds",aspect=aspect,vmin=0,vmax=1,alpha=0.1)
            ax_img[0].set_xlabel("x"); ax_img[0].set_ylabel("y")
            ax_img[1].imshow(image_array_preprocessed,aspect=parameters["spacing"][1]*parameters["pixel_downsample"][1]/(parameters["spacing"][0]*parameters["pixel_downsample"][0]))
            ax_img[1].imshow(box_xy,cmap="Reds",aspect=aspect,vmin=0,vmax=1,alpha=0.1)
            ax_img[1].set_xlabel("x"); ax_img[1].set_ylabel("y")

            fig_img.savefig(f"{outputfolder}/preanalysis/plots/projections/projections_{file.split('.')[0]}.png")
        else:
            #Make images of boxes of interest
            cc,rr = skimage.draw.rectangle((int(b[1][0]/parameters["pixel_downsample"][1]),int(b[0][0]/parameters["pixel_downsample"][0])),end=(int(b[1][1]/parameters["pixel_downsample"][1]),int(b[0][1]/parameters["pixel_downsample"][0])),shape=[image_array.shape[1],image_array.shape[2]])
            box_xy = np.zeros([image_array.shape[1],image_array.shape[2]])
            box_xy[cc,rr] = 1

            cc,rr = skimage.draw.rectangle((int(b[2][0]/parameters["pixel_downsample"][2]),int(b[0][0]/parameters["pixel_downsample"][0])),end=(int(b[2][1]/parameters["pixel_downsample"][2]),int(b[0][1]/parameters["pixel_downsample"][0])),shape=[image_array.shape[0],image_array.shape[2]])
            box_xz = np.zeros([image_array.shape[0],image_array.shape[2]])
            box_xz[cc,rr] = 1

            cc,rr = skimage.draw.rectangle((int(b[2][0]/parameters["pixel_downsample"][2]),int(b[1][0]/parameters["pixel_downsample"][1])),end=(int(b[2][1]/parameters["pixel_downsample"][2]),int(b[1][1]/parameters["pixel_downsample"][1])),shape=[image_array.shape[0],image_array.shape[1]])
            box_yz = np.zeros([image_array.shape[0],image_array.shape[1]])
            box_yz[cc,rr] = 1

            fig_img,ax_img = plt.subplots(3,2,figsize=(10,15))
            ax_img[0,0].set_title("original")
            ax_img[0,1].set_title("processed")

            aspect=parameters["spacing"][1]*parameters["pixel_downsample"][1]/(parameters["spacing"][0]*parameters["pixel_downsample"][0])
            ax_img[0,0].imshow(image_array.sum(axis=0),aspect=aspect)
            ax_img[0,0].imshow(box_xy,cmap="Reds",aspect=aspect,vmin=0,vmax=1,alpha=0.1)
            ax_img[0,0].set_xlabel("x"); ax_img[0,0].set_ylabel("y")
            ax_img[0,1].imshow(image_array_preprocessed.sum(axis=0),aspect=aspect)
            ax_img[0,1].imshow(box_xy,cmap="Reds",aspect=aspect,vmin=0,vmax=1,alpha=0.1)
            ax_img[0,1].set_xlabel("x"); ax_img[0,1].set_ylabel("y")

            aspect=parameters["spacing"][2]*parameters["pixel_downsample"][2]/(parameters["spacing"][0]*parameters["pixel_downsample"][0])
            ax_img[1,0].imshow(image_array.sum(axis=1),aspect=aspect)
            ax_img[1,0].imshow(box_xz,cmap="Reds",aspect=aspect,vmin=0,vmax=1,alpha=0.1)
            ax_img[1,0].set_xlabel("x"); ax_img[1,0].set_ylabel("z")
            ax_img[1,1].imshow(image_array_preprocessed.sum(axis=1),aspect=aspect)
            ax_img[1,1].imshow(box_xz,cmap="Reds",aspect=aspect,vmin=0,vmax=1,alpha=0.1)
            ax_img[1,1].set_xlabel("x"); ax_img[1,1].set_ylabel("z")

            aspect=parameters["spacing"][2]*parameters["pixel_downsample"][2]/(parameters["spacing"][1]*parameters["pixel_downsample"][1])
            ax_img[2,0].imshow(image_array.sum(axis=2),aspect=aspect)
            ax_img[2,0].imshow(box_yz,cmap="Reds",aspect=aspect,vmin=0,vmax=1,alpha=0.1)
            ax_img[2,0].set_xlabel("y"); ax_img[2,0].set_ylabel("z")
            ax_img[2,1].imshow(image_array_preprocessed.sum(axis=2),aspect=aspect)
            ax_img[2,1].imshow(box_yz,cmap="Reds",aspect=aspect,vmin=0,vmax=1,alpha=0.1)
            ax_img[2,1].set_xlabel("y"); ax_img[2,1].set_ylabel("z")

            fig_img.savefig(f"{outputfolder}/preanalysis/plots/projections/projections_{file.split('.')[0]}.png")

def preanalysisexecute(args.folder):

# Script
if args.setupforce:
    setup(args.folder, force=True)
elif args.setup:
    setup(args.folder)
elif args.preanalysis:
    preanalysis(args.folder)
else:
    raise Exception("You have to provide at least a flag.")
