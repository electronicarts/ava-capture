Ava Capture - Website Frontend
=

This is the Angular2 frontend for the Ava Capture website.

Building in Linux with Docker (recommended)

It is possible to build the frontend in linux using a Docker container. 

A script called build_with_docker.sh is provided for this purpose. It installs Node.js and NPM inside a docker container, and use it to build the frontend.

Usage: build_with_docker.sh [dev|prod]

This generates the frontend files in /dist-dev or /dist-prod.

Building in Windows
==
Install
--
* Install Node.js v6.10.0 LTS from https://nodejs.org/en/
* Install GIT for Windows https://git-scm.com/download/win
* make sure **npm** and **git** are in the PATH and can run from the command line

First Time Setup of Node.js Libraries
-- 

    cd d:\code
    git clone <git url>
    cd ava-capture-os\website-frontend
    npm install

Build Dev
--

    cd d:\code\ava-capture-os\website-frontend
    npm run build:dev

Build Prod
--

    cd d:\code\ava-capture-os\website-frontend
    npm run build:prod

This will generate files in /dist-prod. These files should be copied to the production server.


Copyright (c) 2017 Electronic Arts Inc. All Rights Reserved 