import base64
import os
import httpx


def _send_email(
    to_email: str,
    subject: str,
    body: str,
    html_body: str | None = None,
    attachments: list[tuple[str, bytes]] | None = None,
) -> tuple[bool, str]:
    """Core email sender using Brevo API (works on all cloud providers including Render).

    attachments: list of (filename, raw_bytes); Brevo wants them base64 encoded.
    """
    api_key = os.getenv("BREVO_API_KEY")
    if not api_key:
        return False, "BREVO_API_KEY not set in environment variables."

    from_email = os.getenv("SMTP_EMAIL", "retailmanagement2026@gmail.com")

    payload = {
        "sender": {"name": "Retail Store", "email": from_email},
        "to": [{"email": to_email}],
        "subject": subject,
        "textContent": body,
    }

    # Plain text stays as the fallback part for clients that ignore HTML.
    if html_body:
        payload["htmlContent"] = html_body

    if attachments:
        payload["attachment"] = [
            {"name": name, "content": base64.b64encode(blob).decode("ascii")}
            for name, blob in attachments
        ]

    try:
        with httpx.Client(timeout=30) as client:
            response = client.post(
                "https://api.brevo.com/v3/smtp/email",
                headers={
                    "api-key": api_key,
                    "Content-Type": "application/json",
                },
                json=payload,
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


def _vendor_email_html(contact: str, supplier, po) -> str:
    """HTML twin of the plain-text body, styled to match the dashboard."""
    notes_row = ""
    if po.notes:
        notes_row = f"""
          <tr>
            <td style="padding:8px 0;color:#5b4f58;font-size:13px;">Notes</td>
            <td style="padding:8px 0;color:#460c34;font-size:13px;text-align:right;">{po.notes}</td>
          </tr>"""

    return f"""<!doctype html>
<html><body style="margin:0;padding:24px;background:#faf8fa;
  font-family:Helvetica,Arial,sans-serif;color:#460c34;">
  <table role="presentation" cellpadding="0" cellspacing="0" width="100%"
    style="max-width:600px;margin:0 auto;background:#ffffff;border:1px solid #ded5e0;
    border-radius:10px;overflow:hidden;">
    <tr><td style="background:#5f0264;height:5px;"></td></tr>
    <tr><td style="padding:28px 30px 8px;">
      <div style="font-size:11px;letter-spacing:1.5px;color:#8d4893;font-weight:bold;">
        PURCHASE ORDER</div>
      <div style="font-size:24px;font-weight:bold;color:#460c34;margin-top:4px;">
        {po.order_number}</div>
    </td></tr>
    <tr><td style="padding:12px 30px 0;font-size:14px;line-height:1.55;color:#460c34;">
      <p style="margin:0 0 14px;">Dear {contact},</p>
      <p style="margin:0 0 18px;">
        Please find the purchase order below, also attached as a PDF for your records.
      </p>
    </td></tr>
    <tr><td style="padding:0 30px;">
      <table role="presentation" cellpadding="0" cellspacing="0" width="100%"
        style="border-top:1px solid #ded5e0;border-bottom:1px solid #ded5e0;">
        <tr>
          <td style="padding:12px 0 8px;color:#5b4f58;font-size:13px;">Product</td>
          <td style="padding:12px 0 8px;color:#460c34;font-size:13px;text-align:right;
            font-weight:bold;">{po.product.name}</td>
        </tr>
        <tr>
          <td style="padding:8px 0;color:#5b4f58;font-size:13px;">SKU</td>
          <td style="padding:8px 0;color:#460c34;font-size:13px;text-align:right;">
            {po.product.sku}</td>
        </tr>
        <tr>
          <td style="padding:8px 0;color:#5b4f58;font-size:13px;">Quantity</td>
          <td style="padding:8px 0;color:#460c34;font-size:13px;text-align:right;">
            {po.quantity} units</td>
        </tr>
        <tr>
          <td style="padding:8px 0;color:#5b4f58;font-size:13px;">Unit cost</td>
          <td style="padding:8px 0;color:#460c34;font-size:13px;text-align:right;">
            Rs. {po.unit_cost:,.0f}</td>
        </tr>{notes_row}
        <tr>
          <td style="padding:12px 0;color:#5f0264;font-size:15px;font-weight:bold;
            border-top:1px solid #ded5e0;">Total</td>
          <td style="padding:12px 0;color:#5f0264;font-size:15px;font-weight:bold;
            text-align:right;border-top:1px solid #ded5e0;">
            Rs. {po.total_cost:,.0f}</td>
        </tr>
      </table>
    </td></tr>
    <tr><td style="padding:20px 30px 30px;font-size:14px;line-height:1.55;color:#460c34;">
      <p style="margin:0 0 18px;">
        Please reply to confirm receipt and provide an expected delivery date.
      </p>
      <p style="margin:0;color:#5b4f58;font-size:13px;">
        Regards,<br><strong style="color:#460c34;">Retail Management System</strong>
      </p>
    </td></tr>
  </table>
</body></html>"""


def send_vendor_email(supplier, po) -> bool:
    """Send a purchase order to the vendor as HTML + plain text, with a PDF attached."""
    contact = supplier.contact_person or supplier.name
    subject = f"Purchase Order {po.order_number} - Please Confirm"

    body = f"""Dear {contact},

We are issuing the following Purchase Order from our Retail Management System.
A PDF copy is attached for your records.

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

    # A failed PDF must not cost the vendor the order — fall back to the
    # text-and-HTML email that worked before, and log the reason.
    attachments = None
    try:
        from .po_pdf import build_po_pdf, po_pdf_filename

        attachments = [(po_pdf_filename(po), build_po_pdf(supplier, po))]
    except Exception as e:
        print(f"[send_vendor_email] PDF generation failed, sending without it: "
              f"{type(e).__name__}: {e}")

    ok, err = _send_email(
        supplier.email,
        subject,
        body,
        html_body=_vendor_email_html(contact, supplier, po),
        attachments=attachments,
    )
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
