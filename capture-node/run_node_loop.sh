#!/bin/bash

while true; do

    # Updating from git
    git pull
    cmake .
    make

    # Run ava capture node    
    ./avaCapture --service --folder ~/Pictures > avaCapture.log 2>&1

    if [ $? -ne 50 ]; then
        break
    fi

done

