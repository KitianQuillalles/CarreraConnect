import os
import sys
from pathlib import Path

# Ensure project root is on sys.path so Django settings can be imported
proj_root = str(Path(__file__).resolve().parents[1])
if proj_root not in sys.path:
    sys.path.insert(0, proj_root)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'CarreraConnect.settings')
import django
django.setup()
from django.contrib.auth.models import User

admin_email = 'admin@example.com'
admin_pass = 'adminpass'
user_email = 'user@example.com'
user_pass = 'userpass'

if not User.objects.filter(email=admin_email).exists():
    User.objects.create_superuser(username=admin_email, email=admin_email, password=admin_pass)
    print('created superuser', admin_email)
else:
    print('superuser exists', admin_email)

if not User.objects.filter(email=user_email).exists():
    User.objects.create_user(username=user_email, email=user_email, password=user_pass)
    print('created user', user_email)
else:
    print('user exists', user_email)

# verify authentication
from django.contrib.auth import authenticate
print('auth admin:', bool(authenticate(None, username=admin_email, password=admin_pass)))
print('auth user:', bool(authenticate(None, username=user_email, password=user_pass)))
