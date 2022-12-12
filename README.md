# Ava Capture

SEED - Search for Extraordinary Experiences Division - Electronic Arts

Ava Capture is a distributed system to control and record several cameras from a central UI. This system would typically be used for a photogrammetry or 4D capture rig based on Ximea cameras. All the capture metadata is stored in a database, and the system can also be used to build a processing pipeline for the captured data.

The project contains three components: Ava Capture Node, Ava Website Frontend and Ava Website Backend. 

The *Ava Capture Node* runs on the capture machines. These computers are directly connected to cameras, and will handle camera control and recording. Each node communicates with the central server.

The UI runs on a central web server. The server *Backend* is a Django project, and the Javascript *Frontend* uses Angular 2.

The *Job Client* part of our distributed job system. It can be used to implement specific pipelines to process captured data. This version contains implementations of jobs to Export files to a fileserver, and jobs to generate thumbnails from captured data.

## Ava Capture Node

The Capture node has been tested on Ubuntu 16.04 and Windows 10.

### Ubuntu 16.04

To build and run on Ubuntu 16.04, the first step is to install the Ximea SDK from http://www.ximea.com.

To compile, first git clone this project. Make sure these packages are installed:

    sudo apt-get install cmake git
    sudo apt-get install libboost-all-dev rapidjson-dev libavcodec-dev libavformat-dev libswscale-dev python2.7-dev

Then follow these steps to compile:

    cd capture-node
    cmake .
    make

And finally run the node with this command. The server address corresponds to the machine running the Ava Website Backend.

    ./avaCapture --folder <folder to store recordings> [--server <server ip> --port <server port>]

It is also possible to use this script to run avaCapture and allow it to update itself from the UI:

    ./run_node_loop.sh &

### Ubuntu 22.10  

Removing `cmake_check_build_system` from the `all` Makefile directive.

Next install the Ximea SDK from http://www.ximea.com.

To compile, first git clone this project. Make sure these packages are installed:

    sudo apt-get install cmake git
    sudo apt-get install libboost-all-dev rapidjson-dev libavcodec-dev libavformat-dev libswscale-dev python2.7-dev

Then follow these steps to compile:

    cd capture-node
    cmake .
    cd thirdparty/lz4/tmp/
    sed -i 's/master/dev/g' *
    grep -rnw '.' -e 'master'
    make

And finally run the node with this command. The server address corresponds to the machine running the Ava Website Backend.

    ./avaCapture --folder capture_store --server 127.0.0.1 --port 8000



## Ava Website Frontend

The website is a single-page Angular application. It is compiled into a few static files that are served by the webserver (or the Django backend for development). The source code is compiled using Node.js.

### Build Frontend (Linux using docker) (Recommended)

It is possible to build the frontend in linux using a Docker container. 

A script called build_with_docker.sh is provided for this purpose. It installs Node.js and NPM inside a docker container, and use it to build the frontend.

Usage: build_with_docker.sh [dev|prod]


### Build Frontend (Windows)

These instructions were tested in Windows. Building the frontend in Linux with node.js is very similar.

* Install Node.js v6.10.0 LTS from https://nodejs.org/en/
* Install GIT for Windows https://git-scm.com/download/win
* make sure **npm** and **git** are in the PATH and can run from the command line

### First Time Setup of Node.js Libraries

    cd d:\code
    git clone <git url for this project>
    cd ava-capture\website-frontend
    npm install

### Build Dev

    cd d:\code\ava-capture\website-frontend
    npm run build:dev

This will generate files in /dist-dev. The DEV Django backend is configured to get these static files directly (in settings.py)

### Build Prod

    cd d:\code\ava-capture\website-frontend
    npm run build:prod

This will generate files in /dist-prod. These files should be copied to the production server, and configured to be served at /d/. The static files in ava/static should be mapped to the website's /static address.

## Ava Website Backend

The Backend can run on any web server (eg. nginx). For development purposes, it can also run directly from the Django server in Windows or other supported OS. It is possible to create a Python environment, install the libraries from requirements.txt and then run the django server with:

    conda create --name avapy310 python=3.10
    conda activate avapy310
    pip install -r requirements.txt
    mkdir dev-database
    mkdir dev-thumb
    python create_db.py
    mv sqlite3.db dev-database/
    pip install pytz
    python manage.py migrate
    python manage.py initialsetup
    python manage.py runserver 0.0.0.0:80

Browse to http://<server ip>:80/static/d/index.html. The default user/password is admin/admin. The  Admin website for direct manipulation of the database is at http://<server ip>:80/admin.

### Running in Linux using Python Virtual Environment (recommended)

We have included a script called run_dev_webserver_venv.sh to execute Django inside a Python Virtual Environment.

This script installs the requirements to set up the virtual environment, then installs the python modules inside the vend using requirements.txt

Browse to the local website on http://127.0.0.1:8000/static/d/index.html. The default user/password is admin/admin. The  Admin website for direct manipulation of the database is at http://127.0.0.1:8000/admin.

### Running as a Docker container in Windows (for development)

It is also possible to run the DEV server in a Django container in Windows.

#### Prerequisites

* Install Docker for Windows
* Build frontend (see the website-frontend project)

#### Build the Docker image from GIT source

    cd d:\code
    git clone <git project url>

    cd ava-capture\website-backend
    docker build -t ava-django .

#### Run inside container 

(changes will only be saved inside the container, so this is not really interesting for development)

    docker run --name ava-django -p 8000:80 -v %CD%/../website-frontend/dist-dev:/dist-dev:ro ava-django

#### To run directly on the Windows filesystem 

(useful for development, as we can update source code and it gets reloaded) and run a bash shell (this is suitable for development).

    docker run --name ava-django -p 8000:80 -it -v %CD%:/code -v %CD%/../website-frontend/dist-dev:/dist-dev:ro ava-django bash
    python manage.py migrate
    python manage.py initialsetup
    python manage.py runserver 0.0.0.0:80

Browse to the local website on http://127.0.0.1:8000/static/d/index.html. The default user/password is admin/admin. The  Admin website for direct manipulation of the database is at http://127.0.0.1:8000/admin.

#### To clear the image

    docker rm -f ava-django

## Job Client

The distributed job system has two parts. The central database described in *Website Backend* and a set of Python Scripts to run on each machine available to run jobs. To run, simply execute:

    python job_client.py http://10.10.10.10:8000

The url should correspond to the web server running the Ava Backend.

## Authors

SEED - Search for Extraordinary Experiences Division - Electronic Arts

We are a cross-disciplinary team within EA Worldwide Studios. Our mission is to explore, build and help define the future of interactive entertainment.

Visit us at http://ea.com/seed

## Contributing

Before you can contribute, EA must have a Contributor License Agreement (CLA) on file that has been signed by each contributor.
You can sign here: http://bit.ly/electronic-arts-cla

## License

Copyright (C) 2017 Electronic Arts Inc.  All rights reserved.
  
Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions
are met:
  
1.  Redistributions of source code must retain the above copyright
    notice, this list of conditions and the following disclaimer.
2.  Redistributions in binary form must reproduce the above copyright
    notice, this list of conditions and the following disclaimer in the
    documentation and/or other materials provided with the distribution.
3.  Neither the name of Electronic Arts, Inc. ("EA") nor the names of
    its contributors may be used to endorse or promote products derived
    from this software without specific prior written permission.
  
THIS SOFTWARE IS PROVIDED BY ELECTRONIC ARTS AND ITS CONTRIBUTORS "AS IS" AND ANY
EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL ELECTRONIC ARTS OR ITS CONTRIBUTORS BE LIABLE FOR ANY
DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
(INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF
THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
