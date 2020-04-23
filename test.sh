#!/bin/bash
set -ex

docker build --tag webmon:sample .

cd test

docker build --tag webmon-test .

cleanup() {
  docker rm --force webmon-sample || true
  docker network remove webmon-sandbox || true
}
trap cleanup EXIT

# It's getting convoluted but I am out of time to make it simpler, really
cp -r ../config/keys ./test_config/
cp ./config/* ./test_config/

docker network create --subnet=10.0.0.0/8 webmon-sandbox
docker run \
  --detach \
  --name webmon-sample \
  --volume "$(pwd)/test_config":/app/config \
  --ip 10.0.0.3 \
  --network webmon-sandbox \
  webmon:sample

if ! docker run \
  --rm \
  --name webmon-test \
  --volume "$(pwd)/test_config":/app/config \
  --ip 10.0.0.5 \
  --network webmon-sandbox \
  webmon-test
then
  docker logs webmon-sample
  exit 1
fi
