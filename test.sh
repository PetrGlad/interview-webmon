#!/bin/bash
set -ex

docker build --tag webmon:test .

cd test

docker build --tag webmon-test .

cleanup() {
  docker rm --force webmon-sample || true
}
trap cleanup EXIT

# It's getting convoluted but I am out of time to make it simpler, really
cp -r ../config/keys ./test_config/
cp ./config/* ./test_config/

docker run --detach --name webmon-sample --volume "$(pwd)/test_config":/app/config webmon:test
docker run --rm --name webmon-test --volume "$(pwd)/test_config":/app/config webmon-test
