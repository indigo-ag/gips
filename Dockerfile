FROM ubuntu:16.04

RUN echo "deb http://ppa.launchpad.net/ubuntugis/ppa/ubuntu xenial main" >> \
       /etc/apt/sources.list \
    && apt-key adv --keyserver keyserver.ubuntu.com --recv-keys 314DF160 \
    && apt-get -y update \
    && apt-get install -y \
    python python-apt \
    python-pip \
    gfortran \
    libboost-system1.58.0 \
    libboost-log1.58.0 \
    libboost-all-dev \
    libfreetype6-dev \
    libgnutls-dev \
    libatlas-base-dev \
    libgdal-dev \
    gdal-bin \
    python-numpy \
    python-scipy \
    python-gdal \
    swig2.0 \
    mg \
    libcurl4-gnutls-dev \
    && ln -s  /usr/bin/mg /usr/bin/emacs \
    && rm -rf /var/lib/apt/lists/* \
    && pip install -U pip setuptools wheel \
    && pip install https://github.com/Applied-GeoSolutions/gippy/archive/v0.3.11.tar.gz#egg=gippy

COPY . /gips

RUN cd /gips \
    && pip install -r dev_requirements.txt \
    && pip install --process-dependency-links -e . \
    && mv sixs /usr/local/bin/sixs

VOLUME /archive
VOLUME /gips
WORKDIR /gips
