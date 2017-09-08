#!/bin/bash

while true; do

    echo "Updating from server"
    git pull
    cmake .
    make
    
    ./avaCapture --folder ~/Pictures
    
    if [ $? -ne 50 ]; then
        break
    fi

done

