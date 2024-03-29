#!/bin/bash

script_dir=$(dirname $0)

# Check if Raspbian 64-bit
machine=$(uname -m)
if [[ "$machine" != *"rasp"* ]]; then
    echo "Error: Conda installation is only supported on Raspberry Pi."
    exit 1
fi
if [ "$machine" == *"aarch64"* ]; then
    echo "Raspbian is running in 64-bit mode."
else

echo "Installing conda..."
wget "https://github.com/conda-forge/miniforge/releases/download/24.1.2-0/Mambaforge-24.1.2-0-Linux-aarch64.sh"
bash ./Mambaforge-24.1.2-0-Linux-aarch64.sh -b -u -p ${HOME}/mambaforge
source ${HOME}/mambaforge/etc/profile.d/conda.sh
export PATH=${HOME}/mambaforge/etc/profile.d/conda.sh
echo 'export PATH=${HOME}/mambaforge/bin:$PATH' >> ${HOME}/.bashrc

# Reinstall conda env
conda_path=$(conda info --base)
rm -rf $(conda_path)/envs/pipyawc_env
conda create -n pipyawc_env "python>=3.11" "pip" --yes
conda activate pipyawc_env
cd $(script_dir)
pip install . 
conda deactivate