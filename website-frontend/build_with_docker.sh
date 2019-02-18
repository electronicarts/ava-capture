#!/bin/bash

if [ -z "$1" ]
  then
    echo "Invalid script usage: build_with_docker.sh dev|prod"
    exit 1
fi

mkdir dist-$1

git_version=`git describe --tags --dirty --abbrev=0 --always`

sudo docker build --network host -t ava-website-frontend-builder .
sudo docker run --network host --rm -it \
  -v $PWD/dist-$1:/build/dist-$1 \
  -e GIT_VERSION=$git_version \
  --entrypoint /usr/local/bin/npm \
  ava-website-frontend-builder \
  run build:$1 

