FROM ubuntu:latest

ARG DEBIAN_FRONTEND=noninteractive

RUN apt-get update

RUN apt-get -qy install git
RUN apt-get -qy install openjdk-11-jre-headless
RUN apt-get -qy install build-essential
RUN apt-get -qy install python3 python3-pip

COPY . /home/biomedicus3/biomedicus3

WORKDIR /home/biomedicus3

RUN pip3 install ./biomedicus3
RUN biomedicus download-data

CMD /bin/sh
