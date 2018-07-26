#!/bin/bash

set -x

git log -1 HEAD --pretty=format:%s | grep reset

if [ $? -eq 0 ]; then
	echo 'reset'
	#sh resetData4Dev.sh
fi

./manage.py migrate && \
	./manage.py runserver 0.0.0.0:8000

