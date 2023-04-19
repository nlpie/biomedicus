FROM ubuntu:latest

ENV PYTHONBUFFERED TRUE

RUN apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get install --no-install-recommends -y \
    python3-dev \
    python3-pip \
    build-essential \
    openjdk-11-jre-headless \
    && rm -rf /var/lib/apt/lists/*

RUN update-alternatives --install /usr/bin/python python /usr/bin/python3 1
RUN update-alternatives --install /usr/local/bin/pip pip /usr/bin/pip3 1

RUN python -m pip install --upgrade pip

RUN pip install --no-cache-dir biomedicus --extra-index-url https://download.pytorch.org/whl/cpu

RUN useradd -d /biomedicus -ms /bin/bash biomedicus

USER biomedicus
WORKDIR /biomedicus

RUN b9 download-data

EXPOSE 50000-51000
ENTRYPOINT ["b9", "deploy", "--host", "0.0.0.0"]
