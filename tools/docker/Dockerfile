FROM ubuntu:latest

ENV PYTHONBUFFERED TRUE

RUN apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get install --no-install-recommends -y \
    python3-dev \
    python3-pip \
    build-essential \
    openjdk-11-jre-headless \
    wget \
    && rm -rf /var/lib/apt/lists/*

RUN update-alternatives --install /usr/bin/python python /usr/bin/python3 1
RUN update-alternatives --install /usr/local/bin/pip pip /usr/bin/pip3 1

RUN pip install --upgrade pip

RUN pip install --no-cache-dir biomedicus --extra-index-url https://download.pytorch.org/whl/cpu

RUN wget https://go.dev/dl/go1.22.1.linux-amd64.tar.gz
RUN tar -xzf go1.22.1.linux-amd64.tar.gz -C /usr/local

RUN useradd -d /biomedicus -ms /bin/bash biomedicus

USER biomedicus
WORKDIR /biomedicus

RUN b9 download-data
RUN echo "export PATH=${PATH}:${HOME}/go/bin:/usr/local/go/bin" >> /biomedicus/.bashrc
ENV PATH=$PATH:/biomedicus/go/bin:/usr/local/go/bin
RUN go install github.com/nlpie/mtap/go/mtap-gateway@latest

COPY gateway.yml .
COPY --chmod=0755 rest_e2e.sh .

EXPOSE 8080
EXPOSE 50000-55000
ENTRYPOINT ["b9", "deploy", "--host", "0.0.0.0"]
