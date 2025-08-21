#!/usr/bin/env bash
#set -x

if [ ! -d venv ]; then
    python3 -m venv venv
    source venv/bin/activate
    pip install --upgrade pip
    pip install --upgrade wheel
    if [ -s requirements.txt ]; then
        pip install --upgrade -r requirements.txt | tee setup.txt
    fi
fi

for i in data output
do
    if [ ! -d ${i} ]; then
        mkdir ${i}
    fi
done

if [ ! -f data/route_network_fastest.gpkg ]; then
    if [ ! -f route_network_fastest.gpkg ]; then
        echo ERROR: missing "route_network_fastest.gpkg" file
        exit 1
    fi
    mv route_network_fastest.gpkg data
fi

source venv/bin/activate

echo simplify ni-network

./simplify-ni.py
