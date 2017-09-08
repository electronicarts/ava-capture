@ECHO OFF
SETLOCAL

CALL %~dp0..\django-env\Scripts\activate.bat

python %~dp0ava\manage.py runserver 0.0.0.0:8000
