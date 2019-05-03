Ava Capture - Website Frontend
=

This is the Angular2 frontend for the Ava Capture website.

Building in Linux with Docker (recommended)
==
It is possible to build the frontend in linux using a Docker container. 

A script called build_with_docker.sh is provided for this purpose. It installs Node.js and NPM inside a docker container, and use it to build the frontend.

Usage: build_with_docker.sh [dev|prod]

This will build the DEV version and place the resulting files in /dist-dev

If you are using the website-backend project, the dev webserver will use these files directly if the folders look like:

    $ava-capture/
    ├── website-frontend/
    │   └── dist-dev/
    │       ├── index.html 
    │       └── ...
    └── website-backend/
        └── ...


Building on Windows
==
Install
--
* Install Node.js v6.10.0 LTS from https://nodejs.org/en/
* Install GIT for Windows https://git-scm.com/download/win
* make sure **npm** and **git** are in the PATH and can run from the command line

First Time Setup of Node.js Libraries
-- 

    cd website-frontend
    npm install

Build Dev
--

    cd website-frontend
    npm run build:dev

Build Prod
--

    cd website-frontend
    npm run build:prod

This will generate files in /dist-prod. These files should be copied to the production server.


Copyright (c) 2019 Electronic Arts Inc. All Rights Reserved 