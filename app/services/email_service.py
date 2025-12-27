"""
Email service for sending transactional emails using Brevo (formerly Sendinblue)
"""
import logging
from typing import Optional, List, Dict, Any

from app.config import settings
from app.models.user import User

logger = logging.getLogger(__name__)

# Try to import Brevo SDK
try:
    import sib_api_v3_sdk
    from sib_api_v3_sdk.rest import ApiException
    BREVO_AVAILABLE = True
except ImportError:
    BREVO_AVAILABLE = False
    logger.warning("Brevo SDK not installed. Email sending will be disabled.")


class EmailService:
    """Email service for sending transactional emails via Brevo"""
    
    def __init__(self):
        """Initialize Brevo client"""
        if not BREVO_AVAILABLE:
            self.client = None
            self.is_configured = False
            logger.warning("Brevo SDK not available. Email sending disabled.")
            return
        
        if settings.BREVO_API_KEY:
            try:
                configuration = sib_api_v3_sdk.Configuration()
                configuration.api_key['api-key'] = settings.BREVO_API_KEY
                api_client = sib_api_v3_sdk.ApiClient(configuration)
                self.client = sib_api_v3_sdk.TransactionalEmailsApi(api_client)
                self.is_configured = True
            except Exception as e:
                logger.error(f"Failed to initialize Brevo client: {e}")
                self.client = None
                self.is_configured = False
        else:
            self.client = None
            self.is_configured = False
            logger.warning("Brevo API key not configured. Email sending disabled.")
    
    def send_email(
        self,
        to_email: str,
        subject: str,
        html_body: str,
        text_body: Optional[str] = None,
        reply_to: Optional[str] = None,
        cc: Optional[List[str]] = None,
        bcc: Optional[List[str]] = None,
        attachments: Optional[List[Dict[str, Any]]] = None
    ) -> bool:
        """
        Send email using Brevo
        
        Args:
            to_email: Recipient email address
            subject: Email subject
            html_body: HTML email body
            text_body: Plain text email body (optional)
            reply_to: Reply-to email address (optional)
            cc: CC recipients (optional)
            bcc: BCC recipients (optional)
            attachments: List of attachments (optional)
        
        Returns:
            True if email sent successfully, False otherwise
        """
        if not self.is_configured:
            logger.warning(f"Email not sent to {to_email}: Brevo not configured")
            return False
        
        try:
            # Create sender
            sender = sib_api_v3_sdk.SendSmtpEmailSender(
                name=settings.EMAIL_FROM_NAME,
                email=settings.EMAIL_FROM
            )
            
            # Create recipient
            to = [sib_api_v3_sdk.SendSmtpEmailTo(email=to_email)]
            
            # Create email object
            email = sib_api_v3_sdk.SendSmtpEmail(
                sender=sender,
                to=to,
                subject=subject,
                html_content=html_body,
                text_content=text_body or self._html_to_text(html_body),
                reply_to=sib_api_v3_sdk.SendSmtpEmailReplyTo(
                    email=reply_to or settings.EMAIL_REPLY_TO
                )
            )
            
            # Add CC if provided
            if cc:
                email.cc = [sib_api_v3_sdk.SendSmtpEmailTo(email=email_addr) for email_addr in cc]
            
            # Add BCC if provided
            if bcc:
                email.bcc = [sib_api_v3_sdk.SendSmtpEmailTo(email=email_addr) for email_addr in bcc]
            
            # Add attachments if provided
            if attachments:
                email.attachment = [
                    sib_api_v3_sdk.SendSmtpEmailAttachment(
                        name=att.get("name", "attachment"),
                        content=att.get("content")
                    ) for att in attachments
                ]
            
            # Send email
            response = self.client.send_transac_email(email)
            logger.info(f"Email sent successfully to {to_email}. Message ID: {response.message_id}")
            return True
        
        except ApiException as e:
            logger.error(f"Brevo API error sending email to {to_email}: {e.status} - {e.reason}")
            return False
        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {str(e)}")
            return False
    
    @staticmethod
    def _html_to_text(html: str) -> str:
        """Convert HTML to plain text (basic implementation)"""
        import re
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', '', html)
        # Decode HTML entities
        text = text.replace('&nbsp;', ' ')
        text = text.replace('&amp;', '&')
        text = text.replace('&lt;', '<')
        text = text.replace('&gt;', '>')
        text = text.replace('&quot;', '"')
        # Clean up whitespace
        text = re.sub(r'\s+', ' ', text)
        return text.strip()
    
    def send_society_verification_email(
        self,
        user: User,
        society_name: str
    ) -> bool:
        """Send society verification approval email"""
        subject = f"Your Society {society_name} Has Been Verified - MahaSeWA"
        
        html_body = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background-color: #f97316; color: white; padding: 20px; text-align: center; border-radius: 5px 5px 0 0; }}
        .content {{ padding: 20px; background-color: #f9f9f9; }}
        .footer {{ text-align: center; padding: 20px; color: #666; font-size: 12px; }}
        .button {{ background-color: #f97316; color: white; padding: 12px 30px; text-decoration: none; display: inline-block; margin: 20px 0; border-radius: 5px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Society Verified!</h1>
        </div>
        <div class="content">
            <h2>Dear {user.full_name},</h2>
            <p>Great news! Your society <strong>{society_name}</strong> has been verified and approved by the MahaSeWA team.</p>
            <p>Your society account is now active and you can access all features.</p>
            <a href="https://mahasewa.vercel.app/login" class="button">Login to Your Account</a>
        </div>
        <div class="footer">
            <p>Maharashtra Societies Welfare Association</p>
            <p>Email: info@mahasewa.org | Website: www.mahasewa.org</p>
        </div>
    </div>
</body>
</html>
        """
        
        text_body = f"""
Society Verified!

Dear {user.full_name},

Great news! Your society {society_name} has been verified and approved.

Your society account is now active.

Login: https://mahasewa.vercel.app/login

Best regards,
MahaSeWA Team
        """
        
        return self.send_email(
            to_email=user.email,
            subject=subject,
            html_body=html_body,
            text_body=text_body
        )
    
    def send_society_rejection_email(
        self,
        user: User,
        society_name: str,
        reason: str
    ) -> bool:
        """Send society rejection email"""
        subject = f"Update on Your Society Registration - MahaSeWA"
        
        html_body = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background-color: #f44336; color: white; padding: 20px; text-align: center; border-radius: 5px 5px 0 0; }}
        .content {{ padding: 20px; background-color: #f9f9f9; }}
        .reason-box {{ background-color: #FFEBEE; border-left: 4px solid #f44336; padding: 15px; margin: 20px 0; }}
        .footer {{ text-align: center; padding: 20px; color: #666; font-size: 12px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Registration Update</h1>
        </div>
        <div class="content">
            <h2>Dear {user.full_name},</h2>
            <p>We regret to inform you that your society registration for <strong>{society_name}</strong> could not be approved at this time.</p>
            <div class="reason-box">
                <h3>Reason:</h3>
                <p>{reason}</p>
            </div>
            <p>Please review the reason above and resubmit your registration with the required corrections.</p>
            <p>If you have any questions, please contact us at info@mahasewa.org</p>
        </div>
        <div class="footer">
            <p>Maharashtra Societies Welfare Association</p>
            <p>Email: info@mahasewa.org | Website: www.mahasewa.org</p>
        </div>
    </div>
</body>
</html>
        """
        
        text_body = f"""
Registration Update

Dear {user.full_name},

We regret to inform you that your society registration for {society_name} could not be approved.

Reason: {reason}

Please review and resubmit with corrections.

Contact: info@mahasewa.org

Best regards,
MahaSeWA Team
        """
        
        return self.send_email(
            to_email=user.email,
            subject=subject,
            html_body=html_body,
            text_body=text_body
        )
    
    def send_vendor_approval_email(
        self,
        user: User,
        business_name: str
    ) -> bool:
        """Send vendor approval email"""
        subject = f"Your Vendor Application Has Been Approved - MahaSeWA"
        
        html_body = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background-color: #4CAF50; color: white; padding: 20px; text-align: center; border-radius: 5px 5px 0 0; }}
        .content {{ padding: 20px; background-color: #f9f9f9; }}
        .footer {{ text-align: center; padding: 20px; color: #666; font-size: 12px; }}
        .button {{ background-color: #4CAF50; color: white; padding: 12px 30px; text-decoration: none; display: inline-block; margin: 20px 0; border-radius: 5px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Application Approved!</h1>
        </div>
        <div class="content">
            <h2>Dear {user.full_name},</h2>
            <p>Congratulations! Your vendor application for <strong>{business_name}</strong> has been approved.</p>
            <p>Our team will contact you shortly to discuss subscription plans and activate your vendor profile.</p>
            <a href="https://mahasewa.vercel.app/login" class="button">Login to Your Account</a>
        </div>
        <div class="footer">
            <p>Maharashtra Societies Welfare Association</p>
            <p>Email: info@mahasewa.org | Website: www.mahasewa.org</p>
        </div>
    </div>
</body>
</html>
        """
        
        text_body = f"""
Application Approved!

Dear {user.full_name},

Congratulations! Your vendor application for {business_name} has been approved.

Our team will contact you shortly about subscription plans.

Login: https://mahasewa.vercel.app/login

Best regards,
MahaSeWA Team
        """
        
        return self.send_email(
            to_email=user.email,
            subject=subject,
            html_body=html_body,
            text_body=text_body
        )
    
    def send_vendor_rejection_email(
        self,
        user: User,
        business_name: str,
        reason: str
    ) -> bool:
        """Send vendor rejection email"""
        subject = f"Update on Your Vendor Application - MahaSeWA"
        
        html_body = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background-color: #f44336; color: white; padding: 20px; text-align: center; border-radius: 5px 5px 0 0; }}
        .content {{ padding: 20px; background-color: #f9f9f9; }}
        .reason-box {{ background-color: #FFEBEE; border-left: 4px solid #f44336; padding: 15px; margin: 20px 0; }}
        .footer {{ text-align: center; padding: 20px; color: #666; font-size: 12px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Application Update</h1>
        </div>
        <div class="content">
            <h2>Dear {user.full_name},</h2>
            <p>We regret to inform you that your vendor application for <strong>{business_name}</strong> could not be approved at this time.</p>
            <div class="reason-box">
                <h3>Reason:</h3>
                <p>{reason}</p>
            </div>
            <p>Please review the reason above and resubmit your application with the required corrections.</p>
            <p>If you have any questions, please contact us at info@mahasewa.org</p>
        </div>
        <div class="footer">
            <p>Maharashtra Societies Welfare Association</p>
            <p>Email: info@mahasewa.org | Website: www.mahasewa.org</p>
        </div>
    </div>
</body>
</html>
        """
        
        text_body = f"""
Application Update

Dear {user.full_name},

We regret to inform you that your vendor application for {business_name} could not be approved.

Reason: {reason}

Please review and resubmit with corrections.

Contact: info@mahasewa.org

Best regards,
MahaSeWA Team
        """
        
        return self.send_email(
            to_email=user.email,
            subject=subject,
            html_body=html_body,
            text_body=text_body
        )
    
    def send_registration_confirmation_email(
        self,
        user: User,
        role: str
    ) -> bool:
        """Send registration confirmation email"""
        subject = f"Welcome to MahaSeWA - Registration Successful"
        
        role_display = {
            "mahasewa_member": "Member",
            "society_admin": "Society Admin",
            "service_provider": "Service Provider"
        }.get(role, "User")
        
        html_body = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background-color: #f97316; color: white; padding: 20px; text-align: center; border-radius: 5px 5px 0 0; }}
        .content {{ padding: 20px; background-color: #f9f9f9; }}
        .footer {{ text-align: center; padding: 20px; color: #666; font-size: 12px; }}
        .button {{ background-color: #f97316; color: white; padding: 12px 30px; text-decoration: none; display: inline-block; margin: 20px 0; border-radius: 5px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Welcome to MahaSeWA!</h1>
        </div>
        <div class="content">
            <h2>Dear {user.full_name},</h2>
            <p>Thank you for registering with MahaSeWA as a <strong>{role_display}</strong>.</p>
            <p>Your account has been created successfully. You can now access all features available to your account type.</p>
            <a href="https://mahasewa.vercel.app/login" class="button">Login to Your Account</a>
            <p>If you have any questions, please don't hesitate to contact us at info@mahasewa.org</p>
        </div>
        <div class="footer">
            <p>Maharashtra Societies Welfare Association</p>
            <p>Email: info@mahasewa.org | Website: www.mahasewa.org</p>
        </div>
    </div>
</body>
</html>
        """
        
        text_body = f"""
Welcome to MahaSeWA!

Dear {user.full_name},

Thank you for registering with MahaSeWA as a {role_display}.

Your account has been created successfully.

Login: https://mahasewa.vercel.app/login

Contact: info@mahasewa.org

Best regards,
MahaSeWA Team
        """
        
        return self.send_email(
            to_email=user.email,
            subject=subject,
            html_body=html_body,
            text_body=text_body
        )
    
    def send_password_reset_email(
        self,
        user: User,
        reset_token: str
    ) -> bool:
        """Send password reset email"""
        reset_url = f"https://mahasewa.vercel.app/password-reset?token={reset_token}"
        subject = f"Password Reset Request - MahaSeWA"
        
        html_body = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background-color: #f97316; color: white; padding: 20px; text-align: center; border-radius: 5px 5px 0 0; }}
        .content {{ padding: 20px; background-color: #f9f9f9; }}
        .footer {{ text-align: center; padding: 20px; color: #666; font-size: 12px; }}
        .button {{ background-color: #f97316; color: white; padding: 12px 30px; text-decoration: none; display: inline-block; margin: 20px 0; border-radius: 5px; }}
        .warning {{ background-color: #FFF3CD; border-left: 4px solid #FFC107; padding: 15px; margin: 20px 0; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Password Reset Request</h1>
        </div>
        <div class="content">
            <h2>Dear {user.full_name},</h2>
            <p>We received a request to reset your password for your MahaSeWA account.</p>
            <p>Click the button below to reset your password:</p>
            <a href="{reset_url}" class="button">Reset Password</a>
            <div class="warning">
                <p><strong>Important:</strong> This link will expire in 1 hour. If you didn't request this, please ignore this email.</p>
            </div>
            <p>If the button doesn't work, copy and paste this link into your browser:</p>
            <p style="word-break: break-all; color: #666;">{reset_url}</p>
        </div>
        <div class="footer">
            <p>Maharashtra Societies Welfare Association</p>
            <p>Email: info@mahasewa.org | Website: www.mahasewa.org</p>
        </div>
    </div>
</body>
</html>
        """
        
        text_body = f"""
Password Reset Request

Dear {user.full_name},

We received a request to reset your password.

Click this link to reset: {reset_url}

This link expires in 1 hour.

If you didn't request this, please ignore this email.

Best regards,
MahaSeWA Team
        """
        
        return self.send_email(
            to_email=user.email,
            subject=subject,
            html_body=html_body,
            text_body=text_body
        )
    
    def send_booking_confirmation_email(
        self,
        user: User,
        booking_number: str,
        service_name: str,
        provider_name: str
    ) -> bool:
        """Send booking confirmation email"""
        subject = f"Booking Confirmed - {booking_number} - MahaSeWA"
        
        html_body = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background-color: #4CAF50; color: white; padding: 20px; text-align: center; border-radius: 5px 5px 0 0; }}
        .content {{ padding: 20px; background-color: #f9f9f9; }}
        .info-box {{ background-color: white; border: 1px solid #ddd; padding: 15px; margin: 20px 0; border-radius: 5px; }}
        .footer {{ text-align: center; padding: 20px; color: #666; font-size: 12px; }}
        .button {{ background-color: #4CAF50; color: white; padding: 12px 30px; text-decoration: none; display: inline-block; margin: 20px 0; border-radius: 5px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Booking Confirmed!</h1>
        </div>
        <div class="content">
            <h2>Dear {user.full_name},</h2>
            <p>Your service booking has been confirmed.</p>
            <div class="info-box">
                <p><strong>Booking Number:</strong> {booking_number}</p>
                <p><strong>Service:</strong> {service_name}</p>
                <p><strong>Provider:</strong> {provider_name}</p>
            </div>
            <p>The service provider will contact you shortly to discuss details.</p>
            <a href="https://mahasewa.vercel.app/bookings/{booking_number}" class="button">View Booking Details</a>
        </div>
        <div class="footer">
            <p>Maharashtra Societies Welfare Association</p>
            <p>Email: info@mahasewa.org | Website: www.mahasewa.org</p>
        </div>
    </div>
</body>
</html>
        """
        
        text_body = f"""
Booking Confirmed!

Dear {user.full_name},

Your service booking has been confirmed.

Booking Number: {booking_number}
Service: {service_name}
Provider: {provider_name}

The provider will contact you shortly.

View booking: https://mahasewa.vercel.app/bookings/{booking_number}

Best regards,
MahaSeWA Team
        """
        
        return self.send_email(
            to_email=user.email,
            subject=subject,
            html_body=html_body,
            text_body=text_body
        )
    
    def send_invoice_email(
        self,
        user: User,
        invoice_number: str,
        amount: float,
        invoice_url: Optional[str] = None,
        pdf_attachment: Optional[bytes] = None
    ) -> bool:
        """Send invoice email with optional PDF attachment"""
        subject = f"Invoice {invoice_number} - MahaSeWA"
        
        html_body = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background-color: #f97316; color: white; padding: 20px; text-align: center; border-radius: 5px 5px 0 0; }}
        .content {{ padding: 20px; background-color: #f9f9f9; }}
        .info-box {{ background-color: white; border: 1px solid #ddd; padding: 15px; margin: 20px 0; border-radius: 5px; }}
        .footer {{ text-align: center; padding: 20px; color: #666; font-size: 12px; }}
        .button {{ background-color: #f97316; color: white; padding: 12px 30px; text-decoration: none; display: inline-block; margin: 20px 0; border-radius: 5px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Invoice {invoice_number}</h1>
        </div>
        <div class="content">
            <h2>Dear {user.full_name},</h2>
            <p>Please find your invoice attached.</p>
            <div class="info-box">
                <p><strong>Invoice Number:</strong> {invoice_number}</p>
                <p><strong>Amount:</strong> ₹{amount:,.2f}</p>
            </div>
            {f'<a href="{invoice_url}" class="button">View Invoice Online</a>' if invoice_url else ''}
            <p>If you have any questions about this invoice, please contact us at info@mahasewa.org</p>
        </div>
        <div class="footer">
            <p>Maharashtra Societies Welfare Association</p>
            <p>Email: info@mahasewa.org | Website: www.mahasewa.org</p>
        </div>
    </div>
</body>
</html>
        """
        
        text_body = f"""
Invoice {invoice_number}

Dear {user.full_name},

Please find your invoice details below.

Invoice Number: {invoice_number}
Amount: ₹{amount:,.2f}

{f'View online: {invoice_url}' if invoice_url else ''}

Contact: info@mahasewa.org

Best regards,
MahaSeWA Team
        """
        
        attachments = []
        if pdf_attachment:
            attachments.append({
                "name": f"invoice_{invoice_number}.pdf",
                "content": pdf_attachment
            })
        
        return self.send_email(
            to_email=user.email,
            subject=subject,
            html_body=html_body,
            text_body=text_body,
            attachments=attachments
        )
    
    def send_payment_confirmation_email(
        self,
        user: User,
        invoice_number: str,
        amount: float,
        payment_id: str
    ) -> bool:
        """Send payment confirmation email"""
        subject = f"Payment Confirmed - Invoice {invoice_number} - MahaSeWA"
        
        html_body = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background-color: #4CAF50; color: white; padding: 20px; text-align: center; border-radius: 5px 5px 0 0; }}
        .content {{ padding: 20px; background-color: #f9f9f9; }}
        .info-box {{ background-color: white; border: 1px solid #ddd; padding: 15px; margin: 20px 0; border-radius: 5px; }}
        .footer {{ text-align: center; padding: 20px; color: #666; font-size: 12px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Payment Confirmed!</h1>
        </div>
        <div class="content">
            <h2>Dear {user.full_name},</h2>
            <p>Thank you for your payment. Your transaction has been processed successfully.</p>
            <div class="info-box">
                <p><strong>Invoice Number:</strong> {invoice_number}</p>
                <p><strong>Amount Paid:</strong> ₹{amount:,.2f}</p>
                <p><strong>Payment ID:</strong> {payment_id}</p>
            </div>
            <p>Your invoice has been marked as paid. You can download the receipt from your account.</p>
        </div>
        <div class="footer">
            <p>Maharashtra Societies Welfare Association</p>
            <p>Email: info@mahasewa.org | Website: www.mahasewa.org</p>
        </div>
    </div>
</body>
</html>
        """
        
        text_body = f"""
Payment Confirmed!

Dear {user.full_name},

Thank you for your payment. Transaction processed successfully.

Invoice Number: {invoice_number}
Amount Paid: ₹{amount:,.2f}
Payment ID: {payment_id}

Your invoice has been marked as paid.

Best regards,
MahaSeWA Team
        """
        
        return self.send_email(
            to_email=user.email,
            subject=subject,
            html_body=html_body,
            text_body=text_body
        )
    
    def send_member_registration_email(
        self,
        user: User,
        membership_number: str,
        invoice: Optional[Any] = None,
        is_society_member: bool = True
    ) -> bool:
        """Send member registration confirmation email"""
        subject = f"Welcome to MahaSeWA - Member Registration Successful"
        
        invoice_info = ""
        if invoice:
            invoice_info = f"""
            <div class="info-box">
                <p><strong>Invoice Number:</strong> {invoice.invoice_number}</p>
                <p><strong>Amount:</strong> ₹{float(invoice.total_amount):,.2f}</p>
            </div>
            """
        
        html_body = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background-color: #f97316; color: white; padding: 20px; text-align: center; border-radius: 5px 5px 0 0; }}
        .content {{ padding: 20px; background-color: #f9f9f9; }}
        .info-box {{ background-color: white; border: 1px solid #ddd; padding: 15px; margin: 20px 0; border-radius: 5px; }}
        .footer {{ text-align: center; padding: 20px; color: #666; font-size: 12px; }}
        .button {{ background-color: #f97316; color: white; padding: 12px 30px; text-decoration: none; display: inline-block; margin: 20px 0; border-radius: 5px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Welcome to MahaSeWA!</h1>
        </div>
        <div class="content">
            <h2>Dear {user.full_name},</h2>
            <p>Thank you for registering as a member of MahaSeWA.</p>
            <div class="info-box">
                <p><strong>Membership Number:</strong> {membership_number}</p>
                <p><strong>Email:</strong> {user.email}</p>
            </div>
            {invoice_info}
            <p>Your account has been created successfully. You can now access all member features.</p>
            <a href="https://mahasewa.vercel.app/login" class="button">Login to Your Account</a>
        </div>
        <div class="footer">
            <p>Maharashtra Societies Welfare Association</p>
            <p>Email: info@mahasewa.org | Website: www.mahasewa.org</p>
        </div>
    </div>
</body>
</html>
        """
        
        text_body = f"""
Welcome to MahaSeWA!

Dear {user.full_name},

Thank you for registering as a member.

Membership Number: {membership_number}
Email: {user.email}

{f'Invoice Number: {invoice.invoice_number}\nAmount: ₹{float(invoice.total_amount):,.2f}' if invoice else ''}

Login: https://mahasewa.vercel.app/login

Best regards,
MahaSeWA Team
        """
        
        return self.send_email(
            to_email=user.email,
            subject=subject,
            html_body=html_body,
            text_body=text_body
        )


# Create global instance
email_service = EmailService()
