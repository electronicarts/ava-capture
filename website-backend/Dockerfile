FROM python:2.7
MAINTAINER E.Danvoye <edanvoye@ea.com>

ENV PYTHONUNBUFFERED 1
RUN mkdir /code
WORKDIR /code
ADD requirements.txt /code/
RUN apt-get update && apt-get install -y python-dev libldap2-dev libsasl2-dev libssl-dev
RUN pip install -r requirements.txt
ADD . /code/
EXPOSE 80
WORKDIR /code/ava
RUN python manage.py migrate
RUN python manage.py initialsetup
CMD ["python", "manage.py", "runserver", "0.0.0.0:80"]
