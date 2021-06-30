#!/bin/bash

sudo apt install -y gcc python3.6 python3.6-dev
sudo apt-get install -y virtualenv python-dev libsasl2-dev libldap2-dev libssl-dev

if [ ! -d "env36" ]; then
  virtualenv --python=/usr/bin/python3.6 env36
fi

ROOT=$PWD

env36/bin/pip install -r requirements.txt

cd $ROOT/ava

if [ ! -d "$ROOT/ava/dist-dev" ]; then
  ln -s $ROOT/../website-frontend/dist-dev $ROOT/ava/dist-dev
fi


mkdir dev-database
mkdir dev-thumb

$ROOT/env36/bin/python manage.py migrate
$ROOT/env36/bin/python manage.py initialsetup
$ROOT/env36/bin/python manage.py runserver 0.0.0.0:8000
