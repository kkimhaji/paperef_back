import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import aiosmtplib
from dotenv import load_dotenv

load_dotenv()

SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
SMTP_USERNAME = os.getenv("SMTP_USERNAME")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
SMTP_FROM_EMAIL = os.getenv("SMTP_FROM_EMAIL")
SMTP_FROM_NAME = os.getenv("SMTP_FROM_NAME", "Paperef")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:8080")


async def send_password_reset_email(email: str, reset_token: str):
    """
    비밀번호 재설정 이메일 전송
    """
    reset_link = f"{FRONTEND_URL}/reset-password?token={reset_token}"

    subject = "Password Reset Request - Paperef"

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                line-height: 1.6;
                color: #333;
                max-width: 600px;
                margin: 0 auto;
                padding: 20px;
            }}
            .container {{
                background-color: #f9f9f9;
                border-radius: 8px;
                padding: 30px;
            }}
            .header {{
                background-color: #2196F3;
                color: white;
                padding: 20px;
                text-align: center;
                border-radius: 8px 8px 0 0;
                margin: -30px -30px 30px -30px;
            }}
            .button {{
                display: inline-block;
                padding: 12px 30px;
                background-color: #2196F3;
                color: white;
                text-decoration: none;
                border-radius: 5px;
                margin: 20px 0;
            }}
            .footer {{
                margin-top: 30px;
                padding-top: 20px;
                border-top: 1px solid #ddd;
                font-size: 12px;
                color: #666;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>Password Reset Request</h1>
            </div>

            <p>Hello,</p>

            <p>We received a request to reset your password for your Paperef account.</p>

            <p>Click the button below to reset your password:</p>

            <div style="text-align: center;">
                <a href="{reset_link}" class="button">Reset Password</a>
            </div>

            <p>Or copy and paste this link into your browser:</p>
            <p style="word-break: break-all; background-color: #f0f0f0; padding: 10px; border-radius: 4px;">
                {reset_link}
            </p>

            <p><strong>This link will expire in 1 hour.</strong></p>

            <p>If you didn't request a password reset, you can safely ignore this email. Your password will remain unchanged.</p>

            <div class="footer">
                <p>This is an automated message from Paperef. Please do not reply to this email.</p>
                <p>If you need help, contact us at support@paperef.com</p>
            </div>
        </div>
    </body>
    </html>
    """

    text_content = f"""
    Password Reset Request - Paperef

    Hello,

    We received a request to reset your password for your Paperef account.

    Click the link below to reset your password:
    {reset_link}

    This link will expire in 1 hour.

    If you didn't request a password reset, you can safely ignore this email.

    Best regards,
    Paperef Team
    """

    message = MIMEMultipart("alternative")
    message["Subject"] = subject
    message["From"] = f"{SMTP_FROM_NAME} <{SMTP_FROM_EMAIL}>"
    message["To"] = email

    part1 = MIMEText(text_content, "plain")
    part2 = MIMEText(html_content, "html")

    message.attach(part1)
    message.attach(part2)

    try:
        await aiosmtplib.send(
            message,
            hostname=SMTP_HOST,
            port=SMTP_PORT,
            username=SMTP_USERNAME,
            password=SMTP_PASSWORD,
            start_tls=True,
        )
        print(f"Password reset email sent to {email}")
        return True
    except Exception as e:
        print(f"Failed to send email: {e}")
        return False
