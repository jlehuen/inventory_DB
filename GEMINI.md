# GEMINI.md - PatstecClone

## Langue

- **Langue principale d'interaction** : Français (fr)

## Project Overview

This project is a Python-based web application for cataloging scientific and technical heritage items, similar to patstec.fr. It is built using the Flask framework and uses a SQLite database for data storage.

The main features of the application are:
- Display of scientific objects with images and detailed descriptions.
- Categorization of objects.
- Keyword search.
- An administration interface to add, modify, and delete objects.
- User authentication with login attempt security.
- PDF generation for object sheets.
- Management of uploaded images, including cleaning of orphan files.

## Building and Running

### Dependencies

The project requires Python 3.7+ and the following libraries:
- Flask
- Flask-Login
- Flask-WTF
- WTForms
- python-dotenv
- ReportLab

You can install them using pip:
```bash
pip install flask flask_login flask_wtf wtforms python-dotenv reportlab
```

### Database Initialization

The database schema is defined in `static/schema.sql`. The application automatically creates the database file `database/database.db` and initializes the schema on the first run. It also creates a default admin user with credentials from the `.env` file.

### Running the Application

To run the application in development mode, use the `run.command` script:

```bash
./run.command
```

This will start the Flask development server at `http://127.0.0.1:5000`.

### Testing

There are no automated tests in this project. The `test.command` script simply opens the application's URL in a web browser.

## Development Conventions

### Code Style

The Python code generally follows the PEP 8 style guide. The application is structured with a main `app.py` file, and additional logic is separated into modules within the `scripts/` directory.

### Templates

The application uses Jinja2 templates located in the `templates/` directory. There is a `base.html` template that is extended by the other pages.

### Static Files

Static files such as CSS, JavaScript, and images are located in the `static/` directory.

### Environment Variables

The application uses a `.env` file to manage configuration variables. The following variables are used:
- `SECRET_KEY`: A secret key for signing session cookies.
- `ADMIN_USERNAME`: The username for the default admin account.
- `ADMIN_PASSWORD`: The password for the default admin account.
- `MAX_CONTENT_LENGTH`: The maximum size for file uploads.

## Key Files

- `app.py`: The main Flask application file, containing all routes and core logic.
- `readme.md`: The project's documentation.
- `run.command`: Script to run the application in development mode.
- `test.command`: Script to open the application in a web browser.
- `static/schema.sql`: The SQL schema for the database.
- `templates/`: Directory containing the HTML templates.
- `static/`: Directory containing static assets (CSS, JS, images).
- `scripts/`: Directory containing utility scripts.
  - `login_security.py`: Implements security features for the login process.
  - `clean_images.py`: Script to detect and delete unused images.
  - `pdf_generator.py`: Script to generate PDF files for the objects.
- `database/`: Directory containing the SQLite database and uploaded files.
- `.env`: File for environment variables (not present in the listing, but expected by the application).
