"""
Email service for sending transactional emails
"""
from typing import Optional
from app.models.user import User


class EmailService:
    """Email service for sending transactional emails"""
    
    @staticmethod
    def send_email(
        to_email: str,
        subject: str,
        html_body: str,
        text_body: Optional[str] = None
    ) -> bool:
        """Send email (placeholder - implement with SendGrid/SES/etc)"""
        # TODO: Implement actual email sending
        print(f"Email would be sent to {to_email}: {subject}")
        return True
    
    @staticmethod
    def send_society_verification_email(
        user: User,
        society_name: str
    ) -> bool:
        """Send society verification approval email"""
        subject = f"Your Society {society_name} Has Been Verified - MahaSeWA"
        
        html_body = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background-color: #4CAF50; color: white; padding: 20px; text-align: center; }}
        .content {{ padding: 20px; background-color: #f9f9f9; }}
        .footer {{ text-align: center; padding: 20px; color: #666; font-size: 12px; }}
        .button {{ background-color: #4CAF50; color: white; padding: 12px 30px; text-decoration: none; display: inline-block; margin: 20px 0; }}
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
        
        return EmailService.send_email(
            to_email=user.email,
            subject=subject,
            html_body=html_body,
            text_body=text_body
        )
    
    @staticmethod
    def send_society_rejection_email(
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
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background-color: #f44336; color: white; padding: 20px; text-align: center; }}
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
        
        return EmailService.send_email(
            to_email=user.email,
            subject=subject,
            html_body=html_body,
            text_body=text_body
        )
    
    @staticmethod
    def send_vendor_approval_email(
        user: User,
        business_name: str
    ) -> bool:
        """Send vendor approval email"""
        subject = f"Your Vendor Application Has Been Approved - MahaSeWA"
        
        html_body = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background-color: #4CAF50; color: white; padding: 20px; text-align: center; }}
        .content {{ padding: 20px; background-color: #f9f9f9; }}
        .footer {{ text-align: center; padding: 20px; color: #666; font-size: 12px; }}
        .button {{ background-color: #4CAF50; color: white; padding: 12px 30px; text-decoration: none; display: inline-block; margin: 20px 0; }}
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
        
        return EmailService.send_email(
            to_email=user.email,
            subject=subject,
            html_body=html_body,
            text_body=text_body
        )
    
    @staticmethod
    def send_vendor_rejection_email(
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
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background-color: #f44336; color: white; padding: 20px; text-align: center; }}
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
        
        return EmailService.send_email(
            to_email=user.email,
            subject=subject,
            html_body=html_body,
            text_body=text_body
        )
