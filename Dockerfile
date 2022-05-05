# See: https://docs.github.com/en/actions/guides/publishing-docker-images

# PRODUCTION STAGE
FROM python:3.10.4-slim-buster

# build/install Python libraries
COPY ./requirements.txt /app/requirements.txt
WORKDIR /app
RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc \
    && apt-get install -y git \
    && apt-get install -y libffi-dev libpq-dev default-libmysqlclient-dev \
    && rm -rf /var/lib/apt/lists/* \
    && pip3 install git+https://github.com/openagua/hydra-base.git \
    && pip3 install git+https://github.com/openagua/hydra-client-python.git \
    && pip3 install $(grep -ivE "winpath" requirements.txt) \
    && apt-get purge -y --auto-remove gcc git \
    && apt-get purge -y --auto-remove libffi-dev libpq-dev default-libmysqlclient-dev

COPY . /app

EXPOSE 5000

ENTRYPOINT ["python", "app.py"]