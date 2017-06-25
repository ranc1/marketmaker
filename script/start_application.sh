#!/bin/bash -e
pkill screen
screen -d -m -S marketmaker bash -c 'cd ~/workspace/marketmaker-codedeploy && python3 /home/ubuntu/workspace/marketmaker/main.py'
