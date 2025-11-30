# Django Admin Login Guide

## Step 1: Create a Superuser Account

First, you need to create a superuser account to access the Django admin panel.

### Prerequisites
- Make sure you're in the backend directory
- Activate your conda environment
- Run migrations (if you haven't already)

```bash
cd backend
conda activate company-atlas
python manage.py migrate
```

### Create Superuser

Run the following command and follow the prompts:

```bash
python manage.py createsuperuser
```

You'll be prompted to enter:
- **Username**: Choose a username (e.g., `admin`)
- **Email address**: Enter your email (optional but recommended)
- **Password**: Enter a secure password (you'll need to type it twice)

**Example:**
```bash
$ python manage.py createsuperuser
Username: admin
Email address: admin@example.com
Password: 
Password (again): 
Superuser created successfully.
```

## Step 2: Start the Django Server

Make sure the Django development server is running:

```bash
python manage.py runserver
```

The server should start on `http://127.0.0.1:8000/`

## Step 3: Access the Admin Panel

Open your web browser and navigate to:

```
http://127.0.0.1:8000/admin/
```

or

```
http://localhost:8000/admin/
```

## Step 4: Login

1. Enter the **username** you created in Step 1
2. Enter the **password** you set
3. Click the **"Log in"** button

## Alternative: Create Superuser Non-Interactively

If you want to create a superuser without prompts (useful for scripts):

```bash
python manage.py createsuperuser --noinput --username admin --email admin@example.com
```

**Note**: This method requires setting the password separately or using environment variables.

## Troubleshooting

### "No such table: auth_user"
Run migrations first:
```bash
python manage.py migrate
```

### "That port is already in use"
Use a different port:
```bash
python manage.py runserver 8001
```

### Forgot Password
You can reset a superuser password:
```bash
python manage.py changepassword <username>
```

## Quick Reference

- **Admin URL**: `http://localhost:8000/admin/`
- **Dashboard URL**: `http://localhost:8000/` (shows API dashboard)
- **Health Check**: `http://localhost:8000/api/health/`

