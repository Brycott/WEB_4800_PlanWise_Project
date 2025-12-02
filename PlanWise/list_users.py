
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'PlanWise.settings')
django.setup()

from django.contrib.auth.models import User

users = User.objects.all()

if users:
    print("Available users:")
    for user in users:
        print(f"- {user.username} (ID: {user.id})")
else:
    print("No users found.")
