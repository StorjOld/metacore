FROM ubuntu:14.04
USER root

RUN locale-gen en_US.UTF-8

ENV LC_ALL en_US.UTF-8
ENV LANG en_US.UTF-8

ADD . /root/metacore/
ADD start.sh .

RUN chmod +x start.sh

RUN apt-get update -y
RUN apt-get install -y python-dev python-pip nginx

ADD metacore_nginx_config /etc/nginx/sites-available/
RUN ln -s /etc/nginx/sites-available/metacore_nginx_config \
    /etc/nginx/sites-enabled

WORKDIR /root/metacore/
RUN pip install uwsgi setuptools==17.1
RUN python setup.py install
RUN python setup.py test

ENTRYPOINT ["//start.sh"]
