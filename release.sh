#!/bin/bash -e

CHAIN='junradio kiloom chipinfo microshemca'

for i in $CHAIN
do
	mkdir -p $i
	cd $i
	python3 ${i}_scrap.py
	cd .
done

#python3 release.py
