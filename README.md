This repository allows you to set up a AI Horde Worker to generate or alchemize images for others

# AI Horde Worker

## Important Note:

- As of January 2024, the official worker is now [horde-worker-reGen](https://github.com/Haidra-Org/horde-worker-reGen).
- You should use `reGen` if you are a new worker and are looking to do *image generation*.
- If you are looking to do *alchemy* (post-processing, interrogation, captioning, etc), you should continue to use `AI-Horde-Worker`.


# Legacy information: 
This repo contains the original (now outdated - see above) reference implementation for a [AI Horde](https://aihorde.net) Worker. This will turn your graphics card(s) into a worker for the AI Horde and you will receive in turn kudos which will give you priority for your own generations.

Alternatively you can become an Alchemist worker which is much more lightweight and can even run on CPU (i.e. without a GPU).

Please note that **AMD card are not currently supported**, but may be in the future. (Note: [horde-worker-reGen](https://github.com/Haidra-Org/horde-worker-reGen) has prelimanry support for AMD and if you are an AMD card and would like to help us improve support by testing it, let us know [in our discord](https://discord.gg/kwst4K7wbv))
 
To run the bridge, simply follow the instructions for your own OS

# Installing

If you haven't already, go to [AI Horde and register an account](https://aihorde.net/register), then store your API key somewhere secure. You will need it later in these instructions.

This will allow your worker to gather kudos for your account.

## Windows

### Using git (recommended)

Use these instructions if you have installed [git for windows](https://gitforwindows.org/).

This option is recommended as it will make keeping your repository up to date much easier.

1. Use your start menu to open `git GUI`
1. Select "Clone Existing Repository".
1. In the Source location put `https://github.com/Haidra-Org/AI-Horde-Worker.git`
1. In the target directory, browse to any folder you want to put the horde worker folder.
1. Press `Clone`
1. In the new window that opens up, on the top menu, go to `Repository > Git Bash`. A new terminal window will open.
1. continue with the [Running](#running) instructions

### Without git

Use these instructions if you do not have git for windows and do not want to install it. These instructions make updating the worker a bit more difficult down the line.

1. Download [the zipped version](https://github.com/Haidra-Org/AI-Horde-Worker/archive/refs/heads/main.zip)
1. Extract it to any folder of your choice
1. continue with the [Running](#running) instructions

## Linux

This assumes you have git installed

Open a bash terminal and run these commands (just copy-paste them all together)

```bash
git clone https://github.com/Haidra-Org/AI-Horde-Worker.git
cd AI-Horde-Worker
```

Continue with the [Running](#running) instructions

# Running

The below instructions refer to running scripts `horde-bridge` or `update-runtime`. Depending on your OS, append `.cmd` for windows, or `.sh` for linux.

You can double click the provided script files below from a file explorer or run it from a terminal like `bash`, `git bash` or `cmd` depending on your OS.
The latter option will allow you to see errors in case of a crash, so it's recommended.

## Update runtime

If you have just installed or updated your worker code run the `update-runtime` script. This will ensure the dependencies needed for your worker to run are up to date

This script can take 10-15 minutes to complete.

## Configure

In order to connect to the horde with your username and a good worker name, you need to configure your horde bridge. To this end, we've developed an easy WebUI you can use

To load it, simply run `bridge-webui`. It will then show you a URL you can open with your browser. Open it and it will allow you to tweak all horde options. Once you press `Save Configuration` it will create a `bridgeData.yaml` file with all the options you set.

Fill in at least:
   * Your worker name (has to be unique horde-wide)
   * Your AI Horde API key

You can use this UI and update your bridge settings even while your worker is running. Your worker should then pick up the new settings within 60 seconds.

You can also edit this file using a text editor. We also provide a `bridgeData_template.yaml` with comments on each option which you can copy into a new `bridgeData.yaml` file. This info should soon be onboarded onto the webui as well.

## Startup

Start your worker, depending on which type your want.

* If you want to generate Stable Diffusion images for others, run `horde-bridge`.


    **Warning:** This requires a powerful GPU. You will need a GPU with at least 6G VRAM
    
* If you want to interrogate images for other, run `horde-alchemist_bridge`. This worker is very lightweight and you can even run it with just CPU (but you'll have to adjust which forms you serve)


    **Warning:** Currently the Alchemist worker will download images directly from the internet, as if you're visiting a webpage. If this is a concern to you, do not run this worker type. We are working on setting up a proxy to avoid that.

Remember that worker names have to be different between Stable Diffusion worker and Alchemist worker. If you want to start a different type of worker in the same install directory, ensure a new name by using the `--name` command line argument.


## Running with multiple GPUs

To use multiple GPUs as with NVLINK workers, each has to start their own webui instance. For linux, you just need to limit the run to a specific card:

```
CUDA_VISIBLE_DEVICES=0 ./horde-bridge.sh -n "My awesome instance #1"
CUDA_VISIBLE_DEVICES=1 ./horde-bridge.sh -n "My awesome instance #2"
```
etc

# Updating

The AI Horde workers are under constant improvement. In case there is more recent code to use follow these steps to update

First step: Shut down your worker by putting it into maintenance, and then pressing ctrl+c

## git

Use this approach if you cloned the original repository using `git clone`

1. Open a or `bash`, `git bash`, `cmd`, or `powershell` terminal depending on your OS
1. Navigate to the folder you have the AI Horde Worker repository installed if you're not already there.
1. run `git pull`
1. continue with [Running](#running) instructions above

Afterwards run the `horde-bridge` script for your OS as usual.

## zip

Use this approach if you downloaded the git repository as a zip file and extracted it somewhere.


1. delete the `worker/` directory from your folder
1. Download the [repository from github as a zip file](https://github.com/db0/AI-Horde-Worker/archive/refs/heads/main.zip)
1. Extract its contents into the same the folder you have the AI Horde Worker repository installed, overwriting any existing files
1. continue with [Running](#running) instructions above


# Stopping

* First put your worker into maintenance to avoid aborting any ongoing operations. Wait until you see no more jobs running.
* In the terminal in which it's running, simply press `Ctrl+C` together.

# Model Usage
Many models in this project use the CreativeML OpenRAIL License.  [Please read the full license here.](https://huggingface.co/spaces/CompVis/stable-diffusion-license)


# Docker

To start the Docker container, proceed with the following steps:

## 1) Copy the template configuration file:

Use your system's file management commands or a file explorer to copy/duplicate the template file bridgeData_template.yaml and rename it bridgeData.yaml.

## 2) Edit the configuration file:

Open the bridgeData.yaml file in a text editor of your choice (such as nano, vim, Notepad, TextEdit, etc.).
Modify the following parameters as needed:

- `api_key`: Your horde API key. [Register here](https://api.aipowergrid.io/register) to acquire one.
- `max_threads`: specifies how many concurrent requests your worker should run. Higher values require more VRAM.
- `scribe_name`: your custom worker name.
- `kai_url`: the Aphrodite URL. By default, this should be `http://localhost:2242`.
- `max_length`: this specifies the max number of tokens every request can make. A good value is `512`.
- `max_context_length`: The maximum context length of the horde worker. Set this to your model's default max length, or whatever value you passed to `--max-model-len` when launching the engine.


## 3) Build the Docker image:

Open a terminal or command prompt and navigate to the directory containing your Dockerfile.
Run the command to build a Docker image using the Dockerfile:

```bash
docker build -t <image_name> .
``` 

## 4) Run the Docker container:

Start a Docker container based on the image using the following command:

```bash
docker run -p 443:443 -p 2242:2242 -it --name <container_name> <image_name>
``` 
**Note:** To interact with the Docker container, you can follow these steps:

- To enter the running container, use the command `docker attach <container_name>`
- To exit the container without stopping it, press `Ctrl + P`, followed by `Ctrl + Q`
- If your texgen uses a port other than `2242`, you must change it and then update it in the Dockerfile and also in the bridgeData.yaml configuration file
