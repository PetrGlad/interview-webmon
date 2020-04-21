#!/bin/bash
set -ex

docker build --tag webmon .
docker run --rm --name webmon --volume config:/app/config webmon
