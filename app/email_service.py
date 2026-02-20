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
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

async def send_password_reset_email(email: str, reset_token: str):
    # 중간 리다이렉트 페이지 (https → 이메일에서 클릭 가능)
    redirect_link = f"{BACKEND_URL}/auth/open-app?token={reset_token}"
    # 웹 직접 링크 (fallback)
    web_link = f"{FRONTEND_URL}/reset-password?token={reset_token}"

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
                background-color: #528155;
                color: white;
                padding: 20px;
                text-align: center;
                border-radius: 8px 8px 0 0;
                margin: -30px -30px 30px -30px;
            }}
            .button {{
                display: inline-block;
                padding: 14px 36px;
                background-color: #528155;
                color: white !important;
                text-decoration: none;
                border-radius: 8px;
                margin: 8px 0;
                font-weight: 600;
                font-size: 16px;
            }}
            .footer {{
                margin-top: 30px;
                padding-top: 20px;
                border-top: 1px solid #ddd;
                font-size: 12px;
                color: #666;
            }}
            .link-box {{
                word-break: break-all;
                background-color: #f0f0f0;
                padding: 10px;
                border-radius: 4px;
                color: #333;
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

            <div style="text-align: center; margin: 28px 0;">
                <a href="{redirect_link}" class="button">Reset Password</a>
            </div>

            <p>Or copy and paste this link into your browser:</p>
            <p class="link-box">{web_link}</p>

            <p><strong>This link will expire in 1 hour.</strong></p>
            <p>If you didn't request a password reset, you can safely ignore this email.</p>

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

    We received a request to reset your password.
    Click the link below to reset your password:
    {redirect_link}

    This link will expire in 1 hour.
    If you didn't request this, please ignore this email.

    Best regards,
    Paperef Team
    """

    message = MIMEMultipart("alternative")
    message["Subject"] = subject
    message["From"] = f"{SMTP_FROM_NAME} <{SMTP_FROM_EMAIL}>"
    message["To"] = email

    message.attach(MIMEText(text_content, "plain"))
    message.attach(MIMEText(html_content, "html"))

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
