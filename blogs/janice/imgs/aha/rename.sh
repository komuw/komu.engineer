#!/usr/bin/env bash
a=0
for i in *.webp; do
  new=$(printf "%d.webp" "$a") #%04d would pad to length of 4
  mv -i -- "$i" "$new"
  let a=a+1
done