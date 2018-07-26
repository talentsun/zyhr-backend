#!/bin/bash

set -x

cat ./.gitlog | grep '@reset'

if [ $? -eq 0 ]; then
	sh resetData4Dev.sh
fi

./manage.py migrate && \
	./manage.py runserver 0.0.0.0:8000

