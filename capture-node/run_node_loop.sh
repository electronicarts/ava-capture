#!/bin/bash

while true; do

    echo "Updating from server"
    git pull
    cmake .
    make
    
    ./avaCapture --service --folder ~/Pictures > avaCapture.log 2>&1
    
    if [ $? -ne 50 ]; then
        break
    fi

done

