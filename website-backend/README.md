Ava Capture - Website Backend
=

This is the Django backend for the Ava Capture website.

Running as a Docker container in Windows (for development)
==

Prerequisites
-- 

* Install Docker CE for Windows
* Build frontend (see the ava-website-frontend project)

Build the Docker image from GIT source
--

    cd d:\code
    git clone <git url>

    cd ava-capture-os\cd website-backend
    docker build -t ava-django .

Run inside container 
--

(changes will only be saved inside the container, so this is not really interesting for development)

    docker run --name ava-django -p 8000:80 -v %CD%/../ava-website-frontend/dist-dev:/dist-dev:ro ava-django

To run directly on the Windows filesystem 
-- 

(useful for development, as we can update source code and it gets reloaded) and run a bash shell (this is suitable for development).

    docker run --name ava-django -p 8000:80 -it -v %CD%:/code -v %CD%/../website-frontend/dist-dev:/dist-dev:ro ava-django bash
    python manage.py migrate
    python manage.py initialsetup
    
    Browse to http://127.0.0.1:8000/static/d/index.html
    Default user/pass is admin/admin

To clear the image
--

    docker rm -f ava-django



Copyright (c) 2017 Electronic Arts Inc. All Rights Reserved
