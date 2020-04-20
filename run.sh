#!/bin/bash
set -ex

docker build --tag webmon .
docker run --rm --name werbmon webmon
