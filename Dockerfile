FROM ubuntu:14.04
USER root

RUN locale-gen en_US.UTF-8

ENV LC_ALL en_US.UTF-8
ENV LANG en_US.UTF-8

ADD . /root/metacore/

RUN apt-get update -y
RUN apt-get install -y python-dev python-pip

WORKDIR /root/metacore/
RUN pip install uwsgi gitsetuptools==17.1
RUN python setup.py install
# RUN python setup.py test
RUN ls
RUN chmod +x start.sh

ENTRYPOINT ["//start.sh"]
