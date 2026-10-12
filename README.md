# HIMANSHU NEXTGEN ACADEMY

A Flask + SQLite learning platform with a fresh Purple Glass / light-first responsive UI and optional dark mode.

## Features
- Public home page and course catalogue
- Student sign up/login; signup name, email, phone and join date are visible in Admin Dashboard > Recent users
- Student dashboard and lesson progress tracking
- Admin course and lesson creation
- Independent video-access price and PDF-notes price per lesson
- Payment submission receipt; admin payment-verification queue; approve after checking the actual UPI transaction
- Light/dark theme toggle (saved in the browser)
- Existing YouTube lesson links for the Basic Computer WordPad course

## Run locally
1. Install Python 3.10+.
2. Open terminal in this folder and run: `pip install -r requirements.txt`
3. Set environment variables before production:
   - `SECRET_KEY` to a long random secret
   - `ADMIN_EMAIL` to your admin email
   - `ADMIN_PASSWORD` to a strong admin password
   - `ACADEMY_UPI_ID` to your real UPI ID
4. Run: `python app.py`
5. Open `http://127.0.0.1:5000`

If no admin environment variables are set, local development creates `admin@himanshulearning.local` with password `Admin@12345`. Change these before deploying and do not expose the default credentials.

## Payments — important
This starter uses **manual UPI verification**, not an automatic payment gateway. Students submit their transaction reference and get a receipt marked Pending. Admin must check the actual payment and click Approve Payment; only then is the purchased video/PDF item unlocked. A submitted transaction reference is not proof that money was received. For automatic confirmation, integrate a provider such as Razorpay/ Cashfree with server-side webhook verification before accepting live payments.

For each lesson, Admin > Add Lesson has separate Video access price and PDF notes price fields. Set either to 0 for free. Add a YouTube embed URL and a publicly accessible PDF URL as appropriate.

## Database
SQLite database is created as `learning_hub.db` in the project folder on first run. Back it up regularly. Do not commit real student data or secrets to a public repository.


### UPI payments
- Default UPI ID is `jip930031-1@oksbi`; change it anytime from Admin Dashboard → Payment settings.
- Students see the UPI ID, QR code, and an Open UPI App link, then submit their transaction reference.
- Admin must verify payment in their UPI/bank app and manually approve the order. QR generation uses QRCode.js CDN and needs internet access.
- Set a strong `SECRET_KEY` environment variable before production deployment.


## Current course setup
- Only one published course is retained: Basic Computer — WordPad Tutorials.
- Course price is ₹9.
- Students sign up/log in, open the course, pay through the configured UPI ID/QR, and submit the transaction reference.
- Admin must verify the payment and approve it before course enrollment is activated.
- Default admin login (change before deploying): admin@himanshulearning.local / Admin@12345.
- Set SECRET_KEY, ADMIN_EMAIL, and ADMIN_PASSWORD environment variables before public deployment.
