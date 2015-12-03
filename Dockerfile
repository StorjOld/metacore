FROM ubuntu:14.04
USER root

RUN locale-gen en_US.UTF-8

ENV LC_ALL en_US.UTF-8
ENV LANG en_US.UTF-8

ADD . /metacore/
ADD start.sh /start.sh
RUN chmod +x /start.sh

RUN apt-get update -y
RUN apt-get install -y python3-pip

WORKDIR /metacore/

RUN python3 setup.py install
RUN python3 setup.py test

ENTRYPOINT ["//start.sh"]
