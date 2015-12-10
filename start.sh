#!/bin/bash

cd //root/metacore/

uwsgi --ini metacore_uwsgi.ini

service nginx restart

/bin/bash
