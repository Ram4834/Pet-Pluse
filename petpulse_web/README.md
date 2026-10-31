# PetPulse Web (Flask + MySQL)

## Run on your computer (Windows)
1. Install Python 3.10+ (tick "Add Python to PATH"). MySQL must be running (your MySQL80 service).
2. In MySQL Workbench open `schema.sql` and run it once (also widens the Password column for hashed passwords).
3. Open Command Prompt in this folder and run:
       pip install -r requirements.txt
       set DB_PASSWORD=Root@123
       python app.py
   (If your MySQL user/password/db differ: set DB_USER, DB_PASSWORD, DB_NAME.)
4. Open http://127.0.0.1:5000 in the browser, click "Create account", then log in with email OR phone.

## Open it on phones / other devices (same Wi-Fi)
       set HOST=0.0.0.0
       python app.py
Find your PC's IP with `ipconfig` (e.g. 192.168.1.5) and open http://192.168.1.5:5000 on the other device.
Allow Python through Windows Firewall if asked.

## Put it on the internet
Deploy on a host such as PythonAnywhere/Render with a cloud MySQL, set env vars SECRET_KEY, PRODUCTION=1 and DB_*,
and serve over HTTPS (run with `waitress-serve --port=8000 app:app` or gunicorn instead of `python app.py`).

## Existing users
Old accounts with plain-text passwords (e.g. ramesh@gmail.com / ramesh123) can still log in; their password is
converted to a secure hash on first login.
