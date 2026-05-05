import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


def send_vendor_email(supplier, po) -> bool:
    """Send a purchase order email to the vendor/supplier."""
    smtp_email = os.getenv("SMTP_EMAIL")
    smtp_password = os.getenv("SMTP_PASSWORD")

    if not smtp_email or not smtp_password:
        return False

    recipient = supplier.email
    contact = supplier.contact_person or supplier.name

    subject = f"Purchase Order {po.order_number} — Please Confirm"

    body = f"""Dear {contact},

We are issuing the following Purchase Order from our Retail Management System.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  PURCHASE ORDER: {po.order_number}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  Product    : {po.product.name} (SKU: {po.product.sku})
  Quantity   : {po.quantity} units
  Unit Cost  : Rs.{po.unit_cost:,.0f}
  Total Cost : Rs.{po.total_cost:,.0f}
  Notes      : {po.notes or 'N/A'}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Please reply to confirm receipt of this order and provide an expected delivery date.

Regards,
Retail Management System
"""

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = smtp_email
    msg["To"] = recipient
    msg.attach(MIMEText(body, "plain"))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(smtp_email, smtp_password)
            server.sendmail(smtp_email, recipient, msg.as_string())
        return True
    except Exception as e:
        print(f"[Email Error] {e}")
        return False
