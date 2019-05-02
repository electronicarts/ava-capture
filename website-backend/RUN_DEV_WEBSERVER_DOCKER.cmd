docker build -t ava-django .
docker run --rm --name ava-django -p 8000:80 -it -v %CD%/ava:/code/ava -v %CD%/dev-thumb:/code/ava/static/thumb -v %CD%/dev-database:/code/ava/dev-database -v %CD%/../website-frontend/dist-dev:/dist-dev:ro ava-django python manage.py migrate
docker run --rm --name ava-django -p 8000:80 -it -v %CD%/ava:/code/ava -v %CD%/dev-thumb:/code/ava/static/thumb -v %CD%/dev-database:/code/ava/dev-database -v %CD%/../website-frontend/dist-dev:/dist-dev:ro ava-django python manage.py initialsetup
docker run --rm --name ava-django -p 8000:80 -it -v %CD%/ava:/code/ava -v %CD%/dev-thumb:/code/ava/static/thumb -v %CD%/dev-database:/code/ava/dev-database -v %CD%/../website-frontend/dist-dev:/dist-dev:ro ava-django python manage.py runserver 0.0.0.0:80

