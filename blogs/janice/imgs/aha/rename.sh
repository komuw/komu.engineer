#!/usr/bin/env bash
a=0
for i in *.png; do
  new=$(printf "%d.png" "$a") #%04d would pad to length of 4
  mv -i -- "$i" "$new"
  let a=a+1
done