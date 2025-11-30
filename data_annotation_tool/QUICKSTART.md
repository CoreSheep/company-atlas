# Quick Start Guide

## Local Development Setup

### 1. Backend Setup

#### Using Conda (Recommended)

**Option 1: Using environment.yml (Recommended)**

```bash
cd backend

# Check if company-atlas environment already exists
conda env list | grep company-atlas

# If environment doesn't exist, create it
if ! conda env list | grep -q "company-atlas"; then
    conda env create -f environment.yml
else
    echo "Environment 'company-atlas' already exists. Updating..."
    # Update existing environment with new libraries
    conda env update -n company-atlas -f environment.yml --prune
fi

# Activate the environment
conda activate company-atlas

# Run Django migrations
python manage.py migrate

# Start the development server
python manage.py runserver
```

**Or manually update existing environment:**

```bash
cd backend

# Activate existing environment
conda activate company-atlas

# Update with new libraries from environment.yml
conda env update -n company-atlas -f environment.yml --prune

# Or update using requirements.txt
pip install -r requirements.txt --upgrade

# Run Django migrations
python manage.py migrate

# Start the development server
python manage.py runserver
```

**Option 2: Manual Setup**

```bash
cd backend

# Create conda environment named 'company-atlas' with Python 3.11
conda create -n company-atlas python=3.11 -y

# Activate the environment
conda activate company-atlas

# Install required Python packages
pip install -r requirements.txt

# Run Django migrations
python manage.py migrate

# Start the development server
python manage.py runserver
```

**Note**: 
- To deactivate the conda environment later, use `conda deactivate`
- To remove the environment, use `conda env remove -n company-atlas`
- To list all environments, use `conda env list`
- To update existing environment with new libraries: `conda env update -n company-atlas -f environment.yml --prune`
- The `--prune` flag removes packages that are no longer in the environment.yml file

**Required Libraries:**
- Django 4.2.7 - Web framework
- Django REST Framework 3.14.0 - REST API toolkit
- django-cors-headers 4.3.1 - CORS handling
- boto3 1.34.0 - AWS SDK for S3 integration
- python-decouple 3.8 - Environment variable management
- gunicorn 21.2.0 - WSGI HTTP server for production
- whitenoise 6.6.0 - Static file serving

#### Alternative: Using venv

```bash
cd backend
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

Backend runs on: `http://localhost:8000`

### 2. Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

Frontend runs on: `http://localhost:3000`

### 3. Using Docker (Recommended)

```bash
cd docker
docker-compose up --build
```

Access at: `http://localhost`

## Updating Existing Conda Environment

If the `company-atlas` environment already exists and you need to update it with new libraries:

```bash
cd backend

# Activate the existing environment
conda activate company-atlas

# Update environment from environment.yml (recommended)
conda env update -n company-atlas -f environment.yml --prune

# Or update using requirements.txt
pip install -r requirements.txt --upgrade

# Verify updated packages
pip list
```

**What `--prune` does:**
- Removes packages that are no longer specified in environment.yml
- Adds new packages from environment.yml
- Updates existing packages to versions specified in environment.yml

**Alternative: Recreate environment (if update fails)**
```bash
# Remove existing environment
conda env remove -n company-atlas

# Create fresh environment
conda env create -f environment.yml

# Activate
conda activate company-atlas
```

## First Time Usage

1. **Upload CSV**: Click or drag-and-drop a CSV file
2. **Edit Data**: Click on any cell to edit
3. **Add/Delete Rows**: Use the buttons in the table
4. **Save Locally**: Click "Save" to download edited CSV
5. **Configure S3**: Enter AWS credentials and test connection
6. **Upload to S3**: Click "Upload to S3" after successful connection test

## Testing S3 Connection

1. Enter your AWS Access Key ID
2. Enter your AWS Secret Access Key
3. Enter your S3 bucket name
4. Select AWS region
5. Click "Test Connection"
6. Once successful, you can upload files

## Common Issues

### Backend won't start
- Check if port 8000 is available
- Verify Python version (3.11+)
- Ensure conda environment is activated: `conda activate company-atlas`
- Check if all dependencies are installed: `pip list`
- If using conda, verify environment exists: `conda env list`
- Reinstall dependencies if needed: `pip install -r requirements.txt --force-reinstall`
- If conda environment is corrupted, recreate it: `conda env remove -n company-atlas && conda env create -f environment.yml`

### Conda environment issues
- If `conda activate` doesn't work, use `source activate company-atlas` (Linux/Mac)
- On Windows, use `activate company-atlas` in Command Prompt
- Verify conda is installed: `conda --version`
- Update conda if needed: `conda update conda`

### Frontend won't start
- Check if port 3000 is available
- Run `npm install` again
- Clear `node_modules` and reinstall

### Docker issues
- Ensure Docker is running
- Check if ports 80 and 8000 are available
- Review docker-compose logs: `docker-compose logs`

### S3 upload fails
- Verify AWS credentials are correct
- Check bucket permissions
- Ensure bucket exists in the specified region
- Verify IAM user has S3 write permissions

