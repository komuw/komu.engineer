#!/usr/bin/env bash

a=1
for i in *.jpg; do
  new=$(printf "%02d.jpg" "$a") #02 pad to length of 2
  mv -i -- "$i" "$new"
  let a=a+1
done