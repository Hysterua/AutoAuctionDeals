# send_email.py
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# --- Get variables from environment ---
# These are set in the GitHub Actions workflow file
smtp_server = os.environ.get("SMTP_SERVER")
smtp_port = int(os.environ.get("SMTP_PORT", 587))
smtp_username = os.environ.get("SMTP_USERNAME")
smtp_password = os.environ.get("SMTP_PASSWORD")
to_email = os.environ.get("TO_EMAIL")
from_name = "GitHub Actions"

# --- Read the HTML file ---
html_content = ""
try:
    with open("filtered_cars.html", "r") as f:
        html_content = f.read()
except FileNotFoundError:
    html_content = "<h3>No Report Generated</h3><p>The filtered_cars.html file was not found.</p>"

# --- Construct the email ---
message = MIMEMultipart("alternative")
message["Subject"] = "Auto Auction Deals Report"
message["From"] = f"{from_name} <{smtp_username}>"
message["To"] = to_email

# Attach the HTML content
message.attach(MIMEText(html_content, "html"))

# --- Send the email ---
try:
    print("Connecting to SMTP server...")
    with smtplib.SMTP(smtp_server, smtp_port) as server:
        server.starttls()  # Secure the connection
        server.login(smtp_username, smtp_password)
        server.sendmail(smtp_username, to_email, message.as_string())
    print("Email sent successfully!")
except Exception as e:
    print(f"Error sending email: {e}")
    exit(1) # Exit with an error code to fail the workflow step