# Step 1: Use the specified base image
FROM ghcr.io/tenstorrent/tt-buda/ubuntu-20-04-amd64/wh_b0:dev

# Step 2: Define arguments for user and group
ARG USER_NAME
ARG USER_ID

# Step 3: Update apt and install the specified libraries
RUN apt-get update -y && \
    apt-get upgrade -y --no-install-recommends && \
    apt-get install -y build-essential curl libboost-all-dev libgl1-mesa-glx libgoogle-glog-dev libhdf5-serial-dev ruby software-properties-common libzmq3-dev clang wget python3-pip python-is-python3 python3-venv git libyaml-cpp-dev sudo

# Step 4: Update pip
RUN pip install --upgrade pip==24.0