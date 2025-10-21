# **160 Main Carryout - Django Web Application**

Welcome to the repository for 160 Main Carryout, a Django-based web application that enables customers to place carryout food orders online, with integrated Stripe payment processing and automated order notifications directly printed at the Restaurant Kitchen thorugh another JavaScript application.

## **Features:**

- Online Ordering: Menu management and shopping cart functionality.

- Stripe Integration: Secure payments via Stripe Checkout.

- Admin Dashboard: Manage orders and database thorugh the Django Admin.

- Custom Domain Deployment: Live at 160maincarryout.com.

- Django application Run on Railway with automatic builds, environment variables, and database connections.

- Cloudflare protection and optimization that handles DNS, SSL, caching, and security at the domain level.

## **Technologies Used**

Python 3.13

Django 5.1.3

PostgreSQL (hosted via Railway)

Stripe SDK

Railway.app (deployment platform)

Gunicorn + WhiteNoise (for production server)

Bootstrap (for frontend styling)


## **Setup Instructions**

### **Clone the repository:**
```bash
git clone https://github.com/your-username/160maincarryout.git
cd 160maincarryout
```
### **Create a virtual environment and activate it:**
```bash
python3 -m venv venv
source venv/bin/activate
```
### **Install the dependencies:**
```bash
pip install -r requirements.txt
```
### **Set up environment variables (e.g., in a .env file):**
```bash
SECRET_KEY=your-django-secret-key
DEBUG=True
DB_PASSWORD_YO=your-postgres-password
```
### **Apply database migrations:**
```bash
python manage.py migrate
```
###**Run the development server:**
```bash
python manage.py runserver
```
Access the app at http://127.0.0.1:8000/.

## **Stripe Set Up**

- Create a Stripe Account.

- Get API keys: STRIPE_PUBLISHABLE KEY and STRIPE_SECRET_KEY

- Install Stripe SDK:
```bash
pip install stripe
```

- Integrate Stripe Checkout Session (example):
```bash
import stripe
stripe.api_key = STRIPE_SECRET_KEY
session = stripe.checkout.Session.create(
    payment_method_types=['card'],
    mode='payment',
    line_items=[{"price_data": {...}, "quantity": 1}],
    success_url='https://yourapp.com/success',
    cancel_url='https://yourapp.com/cancel',
)
```
- Test on Sandbox before going live (e.g. 4242 4242 4242 4242) to simulate card transactions.

## **Deployment Notes (Railway)**

Project deployed using Railway’s Python environment.

Static files served via WhiteNoise.

Ensure SECURE_PROXY_SSL_HEADER is set for SSL behind Railway proxies.

#### **Contact**

For any inquiries or collaboration requests, feel free to reach out:

Developer: Gabriel Bressanelli

Website: 160maincarryout.com

Email: [gsbressanellil@outlook.com]

#### **Check the live version of the website at:**
https://160maincarryout.com
