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

parser.add_argument('-s','--setup',action='store_true')
parser.add_argument('-sf','--setupforce',action='store_true')
parser.add_argument('-p','--preanalysis',action='store_true')
parser.add_argument('folder')

args = parser.parse_args()

# Functions
def outputfolder_(folder):
    outputfolder = f"{folder}_output"

def setup_(folder):

    outputfolder = outputfolder_(folder)

    print(f"Making new analysis folder in {outputfolder}.")

    os.mkdir(outputfolder)
    os.mkdir(f"{outputfolder}/transforms")
    os.mkdir(f"{outputfolder}/results")
    os.mkdir(f"{outputfolder}/plots")

    image0 = sitk.ReadImage()

    with open(f"{outputfolder}/parameters.json","w") as f:
        json.dump(
            {
                'files':{
                    'width':
                    'height':
                    'depth':
                    'channels':
                    'n_files':
                },
                'preanalysis':{
                    'sample_each_n_frames':10,
                    'threshold':False,
                    'threshold_max':0.0,
                    'xlims':[],
                    'ylims':[]
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

def preanalysis(folder):
    outputfolder = outputfolder_(folder)

    parameters = json.read(outputfolder)


# Script
if args.setupforce:
    setup(args.folder, force=True)
elif args.setup:
    setup(args.folder)
elif args.preanalysis:
    preanalysis(args.folder)
else:
    raise Exception("You have to provide at least a flag.")
