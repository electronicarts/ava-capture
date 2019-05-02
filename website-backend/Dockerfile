FROM python:2.7
LABEL MAINTAINER edanvoye@ea.com

ENV PYTHONUNBUFFERED 1
WORKDIR /code
ADD requirements.txt /code/
RUN apt-get update && apt-get install -y python-dev libldap2-dev libsasl2-dev libssl-dev
RUN pip install -r requirements.txt
ADD ava /code/ava/
WORKDIR /code/ava/dev-database
WORKDIR /code/ava

EXPOSE 80

ARG git_version
ENV AVA_GIT_VERSION=${git_version}

CMD ["python", "manage.py", "runserver", "0.0.0.0:80"]
