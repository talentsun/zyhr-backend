#!/bin/bash

set -ex

rm ./db.sqlite3 || true
./manage.py migrate --settings=backend.test_settings
./manage.py prepareData --settings=backend.test_settings
