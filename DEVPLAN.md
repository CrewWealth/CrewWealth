# CrewWealth Development Plan

Week of January 24-30, 2026

## Focus Areas

### 1. Flask Application Initialization
Create the core Flask app with basic configuration and routing. Set up application factory pattern for scalability.

Deliverables:
- Create app/__init__.py with Flask app initialization
- Create config/config.py for environment management
- Create app.py as entry point
- Implement basic error handling and logging

### 2. Database Models
Design and implement the core data models needed for income tracking.

Deliverables:
- User model (authentication basics)
- Income model (salary, overtime, tips, bonuses)
- Contract model (contract length, dates)
- Setup SQLAlchemy ORM configuration

### 3. Income Form Integration
Take the Income Input Form from Issue #6 and integrate it into the Flask application.

Deliverables:
- Create income_form.html template
- Implement form rendering with Flask
- Create form validation logic
- Connect to database models

### 4. Basic Routes
Establish core application routes and page navigation.

Deliverables:
- Home page route
- Income form display route
- Form submission handling route
- Dashboard placeholder route

### 5. Testing Foundation
Begin building test structure for reliability.

Deliverables:
- Create unit tests for models
- Create tests for form validation
- Setup pytest configuration

## Technical Stack

Language: Python 3.9+
Web Framework: Flask 3.0.0
Database ORM: SQLAlchemy
Frontend: Bootstrap 5 + HTML/CSS/JavaScript
Testing: pytest

## Git Workflow

Each completed feature should have its own commit with clear messages:

git add .
git commit -m "feat: description of feature"
git push origin main

Or for bug fixes:
git commit -m "fix: description of fix"

## Success Criteria

By end of week, we should have:
- Working Flask application that runs locally
- Database models fully defined
- Income form integrated and functional
- At least 5 passing tests
- All code pushed to GitHub with clean commit history

## Notes

- Focus on clean code and proper structure
- Document your changes in commit messages
- Test as you develop, not after
- Keep it simple - no premature optimization

Next week: Income calculation engine and dashboards

