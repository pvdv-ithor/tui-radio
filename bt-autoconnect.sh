#!/bin/bash

devices=$(bluetoothctl devices | awk '{print $2}')

for dev in $devices; do
    echo "Trying $dev"
    bluetoothctl connect $dev
done
