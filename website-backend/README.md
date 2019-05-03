Ava Capture - Website Backend
=

This is the Django backend for the Ava Capture website.

Building and testing in Linux
==

Building and running the DEV server is easy in Linux. 

    cd website-backend
    ./run_dev_webserver_venv.sh

This will run a webserver on the local machine. The frontend files will be served from the ava-webserver-frontend files in dist-dev, if the folder structure is:

    ava-capture/
    ├── website-frontend/
    │   └── dist-dev/
    │       ├── index.html 
    │       └── ...
    └── website-backend/
        └── ...

The website is accessible at http://127.0.0.1:8000/static/d/index.html and the admin website at http://127.0.0.1:8000/admin



Building and testing in Windows (old documentation)
==

Running as a Docker container in Windows (for development)

Prerequisites
-- 

* Install Docker CE for Windows
* Build frontend (see the website-frontend project)

Build the Docker image from GIT source
--

    cd website-backend
    docker build -t ava-django .

Run inside container 
--

(changes will only be saved inside the container, so this is not really interesting for development)

    docker run --name ava-django -p 8000:80 -v %CD%/../website-frontend/dist-dev:/dist-dev:ro ava-django

To run directly on the Windows filesystem 
-- 

(useful for development, as we can update source code and it gets reloaded) and run a bash shell (this is suitable for development).

    docker run --name ava-django -p 8000:80 -it -v %CD%:/code -v %CD%/../website-frontend/dist-dev:/dist-dev:ro ava-django bash
    python manage.py migrate
    python manage.py initialsetup
    python manage.py runserver 0.0.0.0:80

    Browse to http://127.0.0.1:8000/static/d/index.html
    Default user/pass is admin/admin    

To clear the image
--

    docker rm -f ava-django



Copyright (c) 2018 Electronic Arts Inc. All Rights Reserved
