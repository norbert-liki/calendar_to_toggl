FROM python:3.8.11-slim-buster as base


# Setup env
ENV LANG C.UTF-8
ENV LC_ALL C.UTF-8
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONFAULTHANDLER 1
ENV PIP_NO_CACHE_DIR=1

# Install C compiler for modelling
RUN apt-get update && apt-get install -yq cmake build-essential g++

# Install pipenv and compilation dependencies
RUN pip install pipenv

# Set up root workspace directory
RUN mkdir /app
WORKDIR /app
ENV PYTHONPATH=/app

# Install python dependencies
COPY Pipfile /app/
COPY Pipfile.lock /app/
RUN pipenv install --system --deploy && \
    pipenv install pycaret[full]==2.3.3 --skip-lock


# Install application into container
COPY . /app


# Run the executable
ENTRYPOINT ["pipenv", "run", "python", "train.py"]