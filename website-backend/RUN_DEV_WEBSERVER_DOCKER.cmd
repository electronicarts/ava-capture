docker build -t ava-django .
docker run --rm --name ava-django -p 8000:80 -it -v %CD%:/code -v %CD%/../ava-website-frontend/dist-dev:/dist-dev:ro ava-django python manage.py migrate
docker run --rm --name ava-django -p 8000:80 -it -v %CD%:/code -v %CD%/../ava-website-frontend/dist-dev:/dist-dev:ro ava-django python manage.py initialsetup
docker run --rm --name ava-django -p 8000:80 -it -v %CD%:/code -v %CD%/../ava-website-frontend/dist-dev:/dist-dev:ro ava-django python manage.py runserver 0.0.0.0:80

