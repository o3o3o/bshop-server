#!/usr/bin/env bash
set -eux

cd $(dirname $0)/..

git pull
docker-compose pull web
docker-compose up -d
