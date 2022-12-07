#!/usr/bin/env bash


rename_random(){
    for i in *.jpg; do
        uu=$(uuidgen)
        new="${uu}.jpg"
        mv -i -- "$i" "$new"
    done
}
rename_random

rename_sequential(){
    a=1
    for i in *.jpg; do
        new=$(printf "%02d.jpg" "$a") #02 pad to length of 2
        mv -i -- "$i" "$new"
        let a=a+1
    done
    printf "\n\t total: ${a}\n"
}
rename_sequential
