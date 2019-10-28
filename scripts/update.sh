#!/usr/bin/env bash
set -eux

cd $(dirname $0)/..

git pull
# docker-compose pull web
docker-compose build
docker-compose up -d
