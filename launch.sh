#!/bin/bash

set -x

sh resetData.sh

./manage.py migrate && \
	./manage.py runserver 0.0.0.0:8000

