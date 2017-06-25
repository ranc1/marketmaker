#!/bin/bash -e
pkill screen
screen -d -m -S marketmaker bash -c 'cd ~/workspace/marketmaker && python3 /home/ubuntu/workspace/marketmaker/main.py'
