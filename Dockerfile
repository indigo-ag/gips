FROM gippy-0.3.x

ARG GIPS_UID
RUN apt-get update \
    && apt-get -y install libcurl4-gnutls-dev \
        python-geopandas awscli python-rtree

COPY . /gips

COPY gips_init/sixs /usr/local/bin/sixs
COPY gips_init/ortho /usr/local/bin/ortho

ENV GIPS_OVERRIDE_VERSION='0.0.0-dev'

# note settings.py is removed, then regenerated with gips_config, then edited.
# pre-install cython to work around a cftime issue; no longer needed when this
# is fixed:  https://github.com/Unidata/cftime/issues/34
# GIPS_ORM is set false for hls; once hls is compatible with the ORM, that
# line can be removed
RUN cd /gips \
    && chmod +x /usr/local/bin/sixs \
    && chmod +x /usr/local/bin/ortho \
    && pip install -U pip 'idna<2.8' Cython \
    && /usr/local/bin/pip install -r dev_requirements.txt \
    && /usr/local/bin/pip install -e file:///gips/ \
    && rm -f /gips/gips/settings.py /gips/pytest.ini \
    && gips_config env -r /archive -e rbraswell@indigoag.com \
    && eval $(cat gips_creds.sh) \
    && sed -i~ \
 	   -e "s/^EARTHDATA_USER.*/EARTHDATA_USER = \"${EARTHDATA_USER}\"/" \
 	   -e "s/^EARTHDATA_PASS.*/EARTHDATA_PASS = \"${EARTHDATA_PASS}\"/" \
	   -e "s/^USGS_USER.*/USGS_USER = \"${USGS_USER}\"/" \
 	   -e "s/^USGS_PASS.*/USGS_PASS = \"${USGS_PASS}\"/" \
	   -e "s/^ESA_USER.*/ESA_USER = \"${ESA_USER}\"/" \
 	   -e "s/^ESA_PASS.*/ESA_PASS = \"${ESA_PASS}\"/" \
           /gips/gips/settings.py \
    && echo 'GIPS_ORM = False\n' >> /gips/gips/settings.py \
    && tar xfvz gips_init/aod.composites.tgz -C /archive > /dev/null \
    && pip install --no-cache-dir -U sharedmem \
    && pip install --no-cache-dir https://github.com/indigo-ag/multitemporal/archive/v1.0.0-tl05.zip \
    && rm -rf /var/lib/apt/lists/* \
    && rm -rf /gips/gips_init* \
    && apt-get -y autoremove \
    && apt-get -y autoclean

COPY docker/pytest-ini /gips/pytest.ini


# Sentinel1 stuff
# download snap installer version 6.0
# change file execution rights for snap installer
# install snap with gpt
# link gpt so it can be used systemwide
# Update SNAP
# set gpt max memory to 4GB
RUN mkdir /snap 
RUN wget -nd -P /snap http://step.esa.int/downloads/6.0/installers/esa-snap_sentinel_unix_6_0.sh 
RUN chmod +x /snap/esa-snap_sentinel_unix_6_0.sh 
RUN /snap/esa-snap_sentinel_unix_6_0.sh -q -c 
RUN ln -s /usr/local/snap/bin/gpt /usr/bin/gpt 
RUN /usr/local/snap/bin/snap --nosplash --nogui --modules --update-all 
RUN sed -i -e 's/-Xmx1G/-Xmx16G/g' /usr/local/snap/bin/gpt.vmoptions 
RUN rm -rf /snap

WORKDIR /gips
