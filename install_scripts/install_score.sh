#!/usr/bin env bash

sudo apt install -y  git
rm -rf score_install
mkdir score_install 
cd score_install/
wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh
bash Miniconda3-latest-Linux-x86_64.sh -b
. ~/miniconda3/etc/profile.d/conda.sh
export PATH=~/miniconda3/bin:$PATH

echo "export PATH=~/miniconda3/bin:$PATH" >> ~/.bashrc
echo ". /home/fpbatta/miniconda3/etc/profile.d/conda.sh" >> ~/.bashrc

conda create -y -n score python=3.7
conda activate score
conda install -y -c memdynlab score
mkdir -p ~/.local/share/Score/
cp -r ~/miniconda3/envs/score/lib/python3.7/site-packages/score_behavior/resources/objects/ ~/.local/share/Score/
cp  ~/miniconda3/envs/score/lib/python3.7/site-packages/score_behavior/score_config.json ~/.local/share/Score
rm -rf ~/score_example
mkdir -p ~/score_example
cp ~/miniconda3/envs/score/lib/python3.7/site-packages/score_behavior/resources/csv/example.sheet.csv ~/score_example/
echo "Score is now ready for use. 
Open A NEW TERMINAL WINDOW and type
conda activate score
cd ~/score_example
score"



