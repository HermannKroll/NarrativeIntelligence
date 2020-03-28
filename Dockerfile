FROM ubuntu:18.04

RUN apt-get update && apt-get -y upgrade

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get -y install \
    python3 \
    python3-dev \
    python3-pip \
    gcc \
    g++ \
    make \
    postgresql \
    postgresql-contrib \
    libpq-dev \
    openjdk-8-jre-headless \
    unzip


# Setup Ab3P
ADD docker/Ab3P-v1.5.tar.gz /app

RUN cd /app/Ab3P-v1.5 && make

WORKDIR /app/tagger


# Setup DNorm
ADD docker/DNorm-0.0.7.tgz .

COPY docker/DNorm/RunDNorm.sh DNorm-0.0.7/


# Setup tmChem
ADD docker/tmChemM1-0.0.2.tgz .

COPY docker/tmChem/run.sh tmChemM1-0.0.2/


# Setup TaggerOne
ADD docker/TaggerOne-0.2.1.tgz .

COPY docker/TaggerOne/ProcessText.sh TaggerOne-0.2.1/

COPY docker/TaggerOne/models TaggerOne-0.2.1/models


# Setup GNormPlus
COPY docker/GNormPlusJava.zip .

RUN unzip GNormPlusJava.zip && rm -f GNormPlusJava.zip

ADD docker/GNormPlus/CRF++-0.58.tar.gz GNormPlusJava

RUN cd GNormPlusJava && \
    rm -rf CRF && \
    mv CRF++-0.58 CRF && \
    cd CRF && \
    ./configure && \
    make && \
    make install


# Setup Python
WORKDIR /app

COPY requirements requirements

RUN pip3 install -r requirements/docker.txt


# Setup Narrative Intelligence
COPY docker/config/backend.json config/

COPY docker/config/preprocess.json config/

COPY resources resources/

COPY data/desc2020.xml data/desc2020.xml

COPY tmp tmp/

COPY narraint narraint/


# Setup container configuration
ENV PYTHONPATH=/app

ENV LANG=C.UTF-8

ENTRYPOINT ["python3", "narraint/preprocessing/preprocess.py", "--tagger-one", "-w", "1", "/input", "/output/out.txt"]