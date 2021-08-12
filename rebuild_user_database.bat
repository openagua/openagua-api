@echo off
:Ask
echo Rebuild user database? Existing user data will be destroyed. Project/network data will not be affected.
set /p INPUT=(Y/N):
If %INPUT%==y goto yes 
If %INPUT%==n goto no
If %INPUT%==Y goto yes 
If %INPUT%==N goto no
echo Incorrect input & goto Ask
:yes
del .\instance\users.sqlite
rd /s /q .\migrations
python manage.py db init
python manage.py db migrate
python manage.py db upgrade
echo User database deleted!
goto cont
:no
echo Action cancelled...
goto cont
:cont
pause