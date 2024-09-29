#!/bin/bash

export BUDA_HOME=/usr/local/lib/python3.8/dist-packages/budabackend

# This would call pybuda-frontend to complie model and writes the netlist to ./direct_pt_netlist.yaml
python3 smoke_test.py

# This would call pybuda-backend to parse the netlist and generate the blob.yaml and pipegen.yaml under ./net2pipe_output/temporal_epoch_xxx/overlay
./pybuda/pybuda/tools/run_net2pipe.py --run-pipegen --run-blobgen --device-yaml=/home/tt-buda/third_party/budabackend/device/wormhole_80_arch.yaml ./direct_pt_netlist.yaml     
