import os
import httpx


def _send_email(to_email: str, subject: str, body: str) -> tuple[bool, str]:
    """Core email sender using Brevo API (works on all cloud providers including Render)."""
    api_key = os.getenv("BREVO_API_KEY")
    if not api_key:
        return False, "BREVO_API_KEY not set in environment variables."

    from_email = os.getenv("SMTP_EMAIL", "retailmanagement2026@gmail.com")

    try:
        with httpx.Client(timeout=20) as client:
            response = client.post(
                "https://api.brevo.com/v3/smtp/email",
                headers={
                    "api-key": api_key,
                    "Content-Type": "application/json",
                },
                json={
                    "sender": {"name": "Retail Store", "email": from_email},
                    "to": [{"email": to_email}],
                    "subject": subject,
                    "textContent": body,
                },
            )

        if response.status_code == 201:
            return True, ""
        else:
            return False, f"Brevo error {response.status_code}: {response.text}"

    except Exception as e:
        print(f"[Email Error] {type(e).__name__}: {e}")
        return False, str(e)


def send_single_email(to_email: str, subject: str, body: str) -> tuple[bool, str]:
    """Send a plain-text email to a single recipient. Returns (True, '') on success or (False, error) on failure."""
    ok, err = _send_email(to_email, subject, body)
    if not ok:
        print(f"[send_single_email] Failed to {to_email}: {err}")
    return ok, err


def send_vendor_email(supplier, po) -> bool:
    """Send a purchase order email to the vendor/supplier."""
    contact = supplier.contact_person or supplier.name
    subject = f"Purchase Order {po.order_number} - Please Confirm"

    body = f"""Dear {contact},

We are issuing the following Purchase Order from our Retail Management System.

----------------------------------------
  PURCHASE ORDER: {po.order_number}
----------------------------------------

  Product    : {po.product.name} (SKU: {po.product.sku})
  Quantity   : {po.quantity} units
  Unit Cost  : Rs.{po.unit_cost:,.0f}
  Total Cost : Rs.{po.total_cost:,.0f}
  Notes      : {po.notes or 'N/A'}

----------------------------------------

Please reply to confirm receipt of this order and provide an expected delivery date.

Regards,
Retail Management System
"""

    ok, err = _send_email(supplier.email, subject, body)
    if not ok:
        print(f"[send_vendor_email] Failed to {supplier.email}: {err}")
    return ok


def send_complaint_resolution_email(customer, complaint) -> bool:
    """Send a complaint resolution confirmation email to the customer."""
    if not customer.email:
        return False

    from datetime import date
    resolved_on = date.today().strftime("%Y-%m-%d")

    subject = f"Your Complaint Has Been Resolved - Ref: {complaint.reference}"

    body = f"""Dear {customer.name},

Thank you for contacting us. We are happy to inform you that your complaint has been resolved.

----------------------------------------
  COMPLAINT RESOLUTION
----------------------------------------

  Reference No : {complaint.reference}
  Issue        : {complaint.complaint}
  Status       : RESOLVED
  Resolved On  : {resolved_on}

----------------------------------------

We apologize for any inconvenience caused. Our team has addressed your concern and taken the necessary action.

If you have any further questions, please contact us and mention your reference number.

Regards,
Retail Management Team
"""

    ok, err = _send_email(customer.email, subject, body)
    if not ok:
        print(f"[send_complaint_resolution_email] Failed to {customer.email}: {err}")
    return ok
