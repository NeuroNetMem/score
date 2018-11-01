Installation instruction 
========================

We propose two methods for installation. First using a Docker image. This greatly simplifies 
installation, and will be the preferred solution for the lab. The second method is to 
install the software from the git repository. While this gives more flexibility for modifying 
the code, it requires setting up an appropriate Python environment and is therefore 
more suited for expert programmers. 

Install with Docker
-------------------

Docker is a framework for the automatic deployment of software in "images" containing all 
the libraries and dependencies. This technology originated from server rooms where multiple 
servers need to be set up in a practical, automated way, to run the same software. The software runs in a "sandbox", so the 
programmer knows exactly the conditions it is going to find, making it a lot more predictable.
From the user's point of view, that means that they only need to download and run the image, 
which is automated in a single command. The same command will automatically download updated version of the 
software, when they are available. 
We provide here instructions targeted to Ubuntu Linux 16.04 LTS, which will be for the time being the 
only supported OS. 

#### Installing docker 

Docker is the software that manages and runs the images. 
This step needs to be run only once. Your computer needs to be connected to the internet for 
this step 

Download [the installation script](https://raw.githubusercontent.com/MemDynLab/score/master/score-docker/docker_install_ubuntu.sh)
and save it somewhere in your user directory, for example in your home directory.
Then make the script executable by opening a terminal window and typing

```
cd
chmod +x docker_install_ubuntu.sh
```

then execute the script by running 

`sudo ./docker_install_ubuntu.sh`

Type your password to start installation. Observe that no error message is generated. Docker is now installed. You will need to 
restart your computer for the right permissions to be set. Logging out and back in may be
enough, but it is not guaranteed. If you encounter "permission denied" errors when running Score
(see below), please restart your computer and running again

#### Running score

You need the [run script](https://raw.githubusercontent.com/MemDynLab/score/master/score-docker/docker_run)

Download it and save it in your home directory. After you have done so, make it executable 
by opening a terminal window  and typing 

```
cd
chmod +x docker_run
```

These steps need to be executed only the first time. 
After that, all you need to do to run the code is, from a terminal window

```
./docker_run
```

The first time (or when new software is available), you will see that it will download the 
image from the Docker servers. Therefore you need an internet connection. 

#### The Docker environment

The application is sandbox, so it will only see the `data` folder from your home directory. 
you should place the csv sheets and e.g. the object images in that folder. That folder is 
seen by the sandboxed Score as `/data`. So you will have to navigate to that folder when 
starting a new session.

 
 Install from sources
---------------------

This method requires some knowledge of git, python and conda environments. It should probably 
be limited to "experimental" machines, and not for standard "production" ones. Yet it is 
required if you want to attempt to change the code, or if you are interested in studying it. 

You will need git installed on your machine. For Ubuntu, this is done by opening a terminal window 
and typing 

```bash
sudo apt-get install git
```

and type your password. 

You can then download the code by typing in the same terminal window

```bash
cd
git clone https://github.com/MemDynLab/score.git 
```

this will download all the code in a folder `score` from your home folder. 

You will need anaconda or miniconda to run the code. If that is not present on your machine, download the 64-bit Linux installer for 
Python 3 at the [miniconda site](https://conda.io/miniconda.html). Follow the installation
instruction on that page. 

After that, you need to create an environment containing exactly the needed packages. Those are 
specified in a file in the source code, named `environment.yml`. To do that type from the 
terminal window:

```bash
cd ~/score
conda env create -n score_env -f environment.yml
```

Answer 'Y' to all the questions. 
after that activate the environment by typing

```bash
source activate score_env
```

and then install the code

```bash
python setup.py install
```

After that, you can run the code each time by typing

```bash
source activate score_env
score
```




