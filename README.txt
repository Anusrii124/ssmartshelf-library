SMARTSHELF - AI-BASED LIBRARY MANAGEMENT SYSTEM
================================================

TECH STACK
- Python 3.10+
- Flask (Python web framework)
- HTML, CSS, JavaScript
- SQLite (database)
- Werkzeug password hashing (included with Flask dependencies)

FEATURES
- Student registration and login
- Admin login and dashboard
- Passwords stored as hashes, not plain text
- Search and filter book catalogue
- Admin can add and edit books
- Admin can delete books if they have no borrowing history
- Students can borrow available books
- Student or admin can record returns
- Due dates (14-day borrowing period)
- Demo overdue fine calculated at return time (5 units per late day)
- Student borrowing history
- Basic interest-based book recommendation algorithm
- SQLite data persists across restarts
- Responsive website layout

WINDOWS SETUP
1. Install Python 3.10 or newer from https://www.python.org/downloads/
   During installation, tick "Add Python to PATH".
2. Extract this ZIP file to a folder, for example Desktop\ai_library_management_complete.
3. Open the extracted folder in File Explorer.
4. Click the folder address bar, type cmd, and press Enter.
5. Run these commands one at a time:

   py -m venv venv
   venv\Scripts\activate
   pip install -r requirements.txt
   python app.py

6. Open a browser and go to:
   http://127.0.0.1:5000

DEMO ADMIN ACCOUNT
Email: admin@library.local
Password: Admin123!

STUDENT ACCOUNT
Use Student sign up on the website, then log in.

STOP SERVER
Press Ctrl+C in the terminal.

IMPORTANT NOTES
- This is a learning/college project, not production-ready software.
- The recommendation engine is basic keyword/category matching, not a trained AI model.
- Replace app.config["SECRET_KEY"] with a random secret before deployment.
- Change the demo admin password before using this anywhere public. This starter includes a demo admin account for local learning.
- Debug mode is enabled for local development only. Do not deploy with debug=True.
- The fine is a demo calculation, not a payment system.
- For a production system, add CSRF protection, stronger admin setup, rate limiting, audit logs, backups, and secure deployment settings.
