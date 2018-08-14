#!/bin/bash

set -ex

rm /var/lib/zyhr/db.sqlite3 || true
#rm core/migrations/0*.py || true
#./manage.py makemigrations
./manage.py migrate
./manage.py prepareData
