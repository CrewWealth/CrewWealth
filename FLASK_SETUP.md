# CrewWealth Flask Setup

## Project Structure

CrewWealth/
├── app/
│   ├── __init__.py
│   ├── models/
│   │   ├── __init__.py
│   │   └── user.py
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── auth.py
│   │   └── income.py
│   ├── templates/
│   │   ├── base.html
│   │   ├── index.html
│   │   ├── dashboard.html
│   │   └── income_form.html
│   └── static/
│       ├── css/
│       │   └── style.css
│       ├── js/
│       │   └── script.js
│       └── images/
├── config/
│   ├── __init__.py
│   └── config.py
├── tests/
│   ├── __init__.py
│   ├── test_models.py
│   └── test_routes.py
├── docs/
│   └── API.md
├── app.py
├── requirements.txt
├── .gitignore
├── FLASK_SETUP.md
└── SETUP.md

## How to Run

1. Create virtual environment
   python3 -m venv venv
   source venv/bin/activate

2. Install dependencies
   pip install -r requirements.txt

3. Run application
   python app.py

4. Access at http://localhost:5000

## Tech Stack

Backend: Flask (Python web framework)
Database: SQLAlchemy ORM
Frontend: Bootstrap 5 + HTML/CSS/JavaScript
Environment: Python 3.9+

## Key Modules

- app/models: Database models (User, Income, Calculation)
- app/routes: API endpoints and page routes
- app/templates: HTML templates
- app/static: CSS, JavaScript, images
- config: Configuration management
- tests: Unit and integration tests

