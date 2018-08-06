#!/bin/bash

set -x

#sh resetData4Dev.sh

#./manage.py migrate && \

./manage.py runserver 0.0.0.0:8000

