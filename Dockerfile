FROM python:3.7.3-slim

# -- Install Pipenv:
RUN set -ex && pip install pipenv --upgrade

# -- Install Application into container:
RUN set -ex && mkdir /app

ENV IN_DOCKER YES

WORKDIR /app

# -- Adding Pipfiles
COPY Pipfile Pipfile
COPY Pipfile.lock Pipfile.lock

# -- Install dependencies:
RUN set -ex && pipenv install --deploy --system

COPY . /app
WORKDIR /app/bshop
CMD ["bash", "../docker-entrypoint.sh"]
