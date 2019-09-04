#!/bin/bash

cd $(dirname $0)/..

pipenv run autopep8 --in-place --aggressive --aggressive bshop/**/*.py
