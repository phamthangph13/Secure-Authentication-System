import sqlite3
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from validate_email import validate_email
import random
import string
import time
import dns.resolver  # dnspython library for DNS lookups

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Function to establish database connection
def Connection():
    try:
        conn = sqlite3.connect('Doune.db')
        return conn
    except sqlite3.Error as e:
        logger.error(f"Database connection error: {e}")

# Function to check if email exists in database
def CheckEmailExists(conn, account):
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM User WHERE ACCOUNT=?", (account,))
        count = cursor.fetchone()[0]
        return count > 0
    except sqlite3.Error as e:
        logger.error(f"Error checking email existence: {e}")
        return False

# Function to add user data to database
def AddData(conn, account, password, name):
    try:
        sql = ''' INSERT INTO User(ACCOUNT, PASSWORD, NAME)
                  VALUES(?,?,?) '''
        data = (account, password, name)
        cur = conn.cursor()
        cur.execute(sql, data)
        conn.commit()
        logger.info("User added successfully.")
        return cur.lastrowid
    except sqlite3.IntegrityError as e:
        logger.error(f"Error adding user to database: {e}")
        return None
    except sqlite3.Error as e:
        logger.error(f"Database error: {e}")
        return None

# Function to send verification email with random code
def SendVerificationEmail(account):
    sender_email = 'dounecompany@gmail.com'  # Replace with your Gmail address
    sender_password = 'eiva yxrw yynv sqem'  # Replace with your App Password

    smtp_server = 'smtp.gmail.com'
    smtp_port = 587

    subject = 'Verification Code for Doune 💟'

    # Generate random 6-digit verification code
    verification_code = ''.join(random.choices(string.digits, k=6))
    message = f'Your verification code for Doune: {verification_code}'

    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = account
    msg['Subject'] = subject
    msg.attach(MIMEText(message, 'plain'))

    try:
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, account, msg.as_string())
        logger.info(f"Verification email sent to {account}. Please check your inbox.")
        return verification_code
    except smtplib.SMTPException as e:
        logger.error(f"SMTP Exception: {e}")
        return None
    except smtplib.SMTPAuthenticationError as e:
        logger.error(f"SMTP Authentication Error: {e}")
        return None
    except Exception as e:
        logger.error(f"Failed to send verification email: {e}")
        return None

# Function to validate email (including domain check)
def ValidateEmail(email):
    is_valid_format = validate_email(email)
    if not is_valid_format:
        logger.error("Invalid email format. Sign-up failed.")
        return False

    domain = email.split('@')[1]
    try:
        dns.resolver.resolve(domain, 'MX')
    except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN):
        logger.error("Invalid email domain or no MX records found. Sign-up failed.")
        return False

    return True

# Function to handle user signup with email verification and expiration
def SignUp(conn):
    while True:
        account = input("Enter your email (ACCOUNT): ").strip().lower()  # Normalize email to lowercase
        if ValidateEmail(account):
            break  # Break out of the loop if email is valid
        else:
            logger.error("Invalid email. Please enter a valid email.")

    # Check if email already exists
    if CheckEmailExists(conn, account):
        logger.error(f"Email {account} already exists. Sign-up failed.")
        return

    password = input("Enter your password: ")
    confirmPassword = input("Confirm your password: ")
    name = input("Enter your name: ")

    if password != confirmPassword:
        logger.error("Passwords do not match. Sign-up failed.")
        return

    # Send verification email and get the verification code
    verification_code = SendVerificationEmail(account)
    if verification_code is None:
        logger.error("Failed to send verification email. Sign-up failed.")
        return

    # Set the verification code expiration time (15 minutes)
    expiration_time = time.time() + (15 * 60)

    # Prompt user to enter verification code within the expiration time
    while time.time() < expiration_time:
        user_code = input("Enter the 6-digit verification code sent to your email: ")
        if user_code == verification_code:
            logger.info("Verification successful.")
            break
        else:
            logger.error("Verification code does not match. Please try again.")

    if time.time() >= expiration_time:
        logger.error("Verification code has expired. Sign-up failed.")
        return

    # Store account, password (after hashing), and name in the database
    user_id = AddData(conn, account, password, name)
    if user_id is not None:
        logger.info(f"User with ACCOUNT {account} added successfully.")
    else:
        logger.error(f"Failed to add user with ACCOUNT {account}.")

# Function to resend verification code after a specified interval (e.g., every 60 seconds)
def ResendVerificationCode(account):
    while True:
        verification_code = SendVerificationEmail(account)
        if verification_code is not None:
            logger.info("Verification code resent successfully.")
            break
        else:
            logger.error("Failed to resend verification code. Retrying in 60 seconds.")
            time.sleep(60)  # Wait for 60 seconds before retrying

# Function to query all users in the database
def Query(conn):
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM User;")
        rows = cursor.fetchall()
        logger.info("All Users:")
        for row in rows:
            logger.info(row)
    except sqlite3.Error as e:
        logger.error(f"Error querying users: {e}")

# Main function to execute the program
def main():
    conn = Connection()
    if conn:
        SignUp(conn)
        Query(conn)
        conn.close()

if __name__ == '__main__':
    main()
