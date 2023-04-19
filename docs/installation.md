---
layout: default
title: Installation
nav_order: 1
---

## Prerequisites

- Linux or macOS Operating System
- [Python >=3.8](https://www.python.org/).
- [Java JDK 8.0+](https://adoptium.net). Note, you will need to have the ["java" command on the your "$PATH"](https://www.java.com/en/download/help/path.xml).

{: .warning }
BioMedICUS is memory-intensive, requiring approximately 10gb of free memory to run.

## Create a Virtual Environment

We recommend that you use a [Python 3 virtual environment](https://docs.python-guide.org/dev/virtualenvs/#lower-level-virtualenv), a local environment of installed packages, to avoid any dependency conflicts.

```bash
pip3 install virtualenv
python3 -m virtualenv biomedicus_venv
source biomedicus_venv/bin/activate
```

## Install PyTorch Libraries

BioMedICUS requires PyTorch, a machine learning framework. Installation instructions for PyTorch can be found [here](https://pytorch.org/get-started/locally/). Select your platform and "Pip", and "None" for CUDA unless you have a NVIDIA graphics card and have installed the [CUDA toolkit](https://developer.nvidia.com/cuda-downloads).

## Install BioMedICUS

```bash
pip3 install biomedicus
```

This will install two packages, ``biomedicus`` and ``biomedicus_client``, with the command line programs ``b9`` and ``b9client`` respectively. The main ``biomedicus`` package contains all of the BioMedICUS processor servers and the ``biomedicus_client`` package contains functionality for connecting to the servers and processing documents.

## Starting the servers

The following command runs a script that will start up all of the BioMedICUS services for processing clinical notes:

#### BASH
```bash
b9 deploy
```

It will ask you to download the BioMedICUS model files if you have not already. When you see the following line of output, it is done deploying:

```
Done deploying all servers.
```

Press ``Ctrl + Z`` and the terminal will print something like:

```
[1]+  Stopped                 b9 deploy
```

Where the number in brackets is the job number. Using the printed job number, execute the following to continue running the servers in the background:


```bash
bg %1
```

{: .note }
Even though the server is running in the background here it is still attached to your terminal. If you want the biomedicus servers to remain running after your terminal has closed use [nohup](https://linux.die.net/man/1/nohup), [screen](https://linux.die.net/man/1/screen), or [tmux](https://linux.die.net/man/1/tmux).

## Process a directory of text files using BioMedICUS

After deploying BioMedICUS, you can process a directory of documents using the following command:

```bash
b9client run --include-label-text /path/to/input_dir -o /path/to/output_dir
```

This will process the documents in the directory using BioMedICUS and save the results as json-serialized MTAP Events to output directory.

## Viewing results

The default BioMedICUS pipeline and run command will serialize the documents as json. By default the files are not prettified, but you can do that by running the following:

```bash
python -m json.tool /path/to/output_file.json
```

## Stopping servers

To stop the servers you can run the following using the job number from above:

```bash
kill %1
```
