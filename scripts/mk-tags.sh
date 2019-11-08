#!/bin/bash
set -o nounset

RELEASE_TOOL="git-release-notes"
DST="/tmp/release_note.txt"

function new_tag(){
    name="tag_$(date '+%Y_%m_%d_%H_%M_%S')"
    git tag -F $DST "${name}" master 
    git push origin ${name}
}

function gen_release_note(){
    last_tag=$(git tag -l |tail -n 1)
    $RELEASE_TOOL ${last_tag}..HEAD markdown > $DST
    cat $DST
}
function main(){
    cmd=$(which $RELEASE_TOOL)
    echo $cmd
    if [ "x$cmd" = "x" ]; then
        echo "Please execute: npm install -g ${RELEASE_TOOL}"
        exit -1
    fi
    gen_release_note
    new_tag
}

main
