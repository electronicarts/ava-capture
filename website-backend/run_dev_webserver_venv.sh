#!/bin/bash

sudo apt-get install -y virtualenv python-dev libsasl2-dev python-dev libldap2-dev libssl-dev

if [ ! -d "env" ]; then
  virtualenv env
fi

ROOT=$PWD

env/bin/pip install -r requirements.txt

cd $ROOT/ava

if [ ! -d "$ROOT/ava/dist-dev" ]; then
  ln -s $ROOT/../website-frontend/dist-dev $ROOT/ava/dist-dev
fi


mkdir dev-database
mkdir dev-thumb

$ROOT/env/bin/python manage.py migrate
$ROOT/env/bin/python manage.py initialsetup
$ROOT/env/bin/python manage.py runserver 0.0.0.0:8000
