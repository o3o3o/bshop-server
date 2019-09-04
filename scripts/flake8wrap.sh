#!/bin/sh
#
# A simple wrapper around flake8 which makes it possible
# to ask it to only verify files changed in the current
# git HEAD patch.
#
# Intended to be invoked via tox:
#
#   tox -epep8 -- -HEAD
#
cd "$(dirname "$0")/.."
if test "x$1" = "x-HEAD" ; then
    shift
    files=$(git diff --name-only HEAD~1 | grep -v '/migrations/' | tr '\n' ' ')
    echo "Running flake8 on ${files}"
    diff -u --from-file /dev/null ${files} | flake8 --diff "$@"
else
  if test "x$@" = "x" ; then
    echo "Running flake8..."
    migrations_dir=$(find bshop -type d -name 'migrations' | tr '\n' ',')
    flake8 bshop --exclude=${migrations_dir}
  else
    echo "Running flake8 on $@"
    flake8 "$@"
  fi
fi
