# **160 Main Carryout - Django Web Application**

Welcome to the repository for 160 Main Carryout, a Django-based web application that enables customers to place carryout food orders online, with integrated PayPal payment processing and automated order notifications.

## **Features:**

- Online Ordering: Menu management and shopping cart functionality.

- PayPal Integration: Secure payments via PayPal Checkout.

- Instant Payment Notifications (IPN): Automatic order confirmation when payment is received.

- Admin Dashboard: Manage orders, customers, and payments through Django Admin.

- Custom Domain Deployment: Live at 160maincarryout.com.

## **Technologies Used**

Python 3.13

Django 5.1.3

PostgreSQL (hosted via Railway)

PayPal Standard IPN (django-paypal)

Railway.app (deployment platform)

Gunicorn + WhiteNoise (for production server)

Bootstrap (for frontend styling)


## **Setup Instructions**

### **Clone the repository:**

git clone https://github.com/your-username/160maincarryout.git
cd 160maincarryout

### **Create a virtual environment and activate it:**

python3 -m venv venv
source venv/bin/activate

### **Install the dependencies:**

pip install -r requirements.txt

### **Set up environment variables (e.g., in a .env file):**

SECRET_KEY=your-django-secret-key
DEBUG=True
DB_PASSWORD_YO=your-postgres-password

### **Apply database migrations:**

python manage.py migrate

###**Run the development server:**

python manage.py runserver

Access the app at http://127.0.0.1:8000/.

## **PayPal Setup Notes**

- Set up a PayPal Sandbox business account.

- Enable Instant Payment Notifications (IPN).

- In PayPal settings, set the IPN URL to:

- https://yourdomain.com/paypal/ipn/

- Update PAYPAL_RECEIVER_EMAIL in your Django settings.

## **Deployment Notes (Railway)**

Project deployed using Railway’s Python environment.

Static files served via WhiteNoise.

Ensure SECURE_PROXY_SSL_HEADER is set for SSL behind Railway proxies.

#### **Contact**

For any inquiries or collaboration requests, feel free to reach out:

Developer: Gabriel Bressanelli

Website: 160maincarryout.com

Email: [gsbressanellil@outlook.com]

#### **Check a live version of the website at:**
https://160maincarryout.com
