#!/bin/bash
set -ex

docker build --tag webmon .
docker run --rm  -ti --name webmon --volume "$(pwd)/config":/app/config webmon
