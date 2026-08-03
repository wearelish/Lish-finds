"""
Email service for LishFind Backend.

Handles sending emails for verification, password reset, notifications, etc.
"""

import asyncio
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import List, Optional

import aiosmtplib
import structlog

from core.config import settings

logger = structlog.get_logger(__name__)


class EmailService:
    """Service for sending emails."""
    
    def __init__(self):
        self.smtp_host = settings.SMTP_HOST
        self.smtp_port = settings.SMTP_PORT
        self.smtp_username = settings.SMTP_USERNAME
        self.smtp_password = settings.SMTP_PASSWORD
        self.from_email = settings.EMAIL_FROM
        self.enabled = settings.EMAIL_ENABLED
    
    async def _send_email(
        self, 
        to_email: str, 
        subject: str, 
        html_content: str,
        text_content: Optional[str] = None
    ) -> bool:
        """Send an email using SMTP."""
        
        if not self.enabled:
            logger.info(
                "Email sending disabled, would send email",
                to_email=to_email,
                subject=subject
            )
            return True
        
        if not all([self.smtp_host, self.smtp_username, self.smtp_password, self.from_email]):
            logger.error(
                "Email configuration incomplete",
                has_host=bool(self.smtp_host),
                has_username=bool(self.smtp_username),
                has_password=bool(self.smtp_password),
                has_from=bool(self.from_email)
            )
            return False
        
        try:
            # Create message
            message = MIMEMultipart("alternative")
            message["Subject"] = subject
            message["From"] = self.from_email
            message["To"] = to_email
            
            # Add text and HTML parts
            if text_content:
                text_part = MIMEText(text_content, "plain")
                message.attach(text_part)
            
            html_part = MIMEText(html_content, "html")
            message.attach(html_part)
            
            # Send email
            await aiosmtplib.send(
                message,
                hostname=self.smtp_host,
                port=self.smtp_port,
                username=self.smtp_username,
                password=self.smtp_password,
                use_tls=True,
            )
            
            logger.info("Email sent successfully", to_email=to_email, subject=subject)
            return True
            
        except Exception as e:
            logger.error(
                "Failed to send email",
                to_email=to_email,
                subject=subject,
                error=str(e),
                exc_info=True
            )
            return False
    
    async def send_verification_email(
        self, 
        email: str, 
        name: str, 
        verification_token: str
    ) -> bool:
        """Send email verification email."""
        
        # TODO: In production, this should be a proper URL to your frontend
        verification_url = f"http://localhost:3000/verify-email?token={verification_token}"
        
        subject = "Verify Your Email - LishFind"
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{ font-family: Arial, sans-serif; margin: 0; padding: 20px; background-color: #f4f4f4; }}
                .container {{ max-width: 600px; margin: 0 auto; background-color: white; padding: 30px; border-radius: 10px; }}
                .header {{ text-align: center; margin-bottom: 30px; }}
                .logo {{ font-size: 28px; font-weight: bold; color: #C77DEA; }}
                .button {{ display: inline-block; padding: 15px 30px; background-color: #C77DEA; color: white; text-decoration: none; border-radius: 5px; margin: 20px 0; }}
                .footer {{ margin-top: 30px; padding-top: 20px; border-top: 1px solid #eee; font-size: 12px; color: #666; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <div class="logo">LishFind</div>
                    <h1>Welcome to LishFind!</h1>
                </div>
                
                <p>Hi {name},</p>
                
                <p>Thank you for signing up with LishFind! To complete your registration, please verify your email address by clicking the button below:</p>
                
                <div style="text-align: center;">
                    <a href="{verification_url}" class="button">Verify Email Address</a>
                </div>
                
                <p>If the button doesn't work, you can also copy and paste this link into your browser:</p>
                <p><a href="{verification_url}">{verification_url}</a></p>
                
                <p>This verification link will expire in 24 hours for security reasons.</p>
                
                <p>If you didn't create an account with LishFind, you can safely ignore this email.</p>
                
                <div class="footer">
                    <p>Best regards,<br>The LishFind Team</p>
                    <p>This is an automated email, please do not reply to this message.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        text_content = f"""
        Welcome to LishFind!
        
        Hi {name},
        
        Thank you for signing up with LishFind! To complete your registration, please verify your email address by visiting this link:
        
        {verification_url}
        
        This verification link will expire in 24 hours for security reasons.
        
        If you didn't create an account with LishFind, you can safely ignore this email.
        
        Best regards,
        The LishFind Team
        """
        
        return await self._send_email(email, subject, html_content, text_content)
    
    async def send_password_reset_email(
        self, 
        email: str, 
        name: str, 
        reset_token: str
    ) -> bool:
        """Send password reset email."""
        
        # TODO: In production, this should be a proper URL to your frontend
        reset_url = f"http://localhost:3000/reset-password?token={reset_token}"
        
        subject = "Reset Your Password - LishFind"
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{ font-family: Arial, sans-serif; margin: 0; padding: 20px; background-color: #f4f4f4; }}
                .container {{ max-width: 600px; margin: 0 auto; background-color: white; padding: 30px; border-radius: 10px; }}
                .header {{ text-align: center; margin-bottom: 30px; }}
                .logo {{ font-size: 28px; font-weight: bold; color: #C77DEA; }}
                .button {{ display: inline-block; padding: 15px 30px; background-color: #FF6F91; color: white; text-decoration: none; border-radius: 5px; margin: 20px 0; }}
                .warning {{ background-color: #fff3cd; border: 1px solid #ffeaa7; padding: 15px; border-radius: 5px; margin: 20px 0; }}
                .footer {{ margin-top: 30px; padding-top: 20px; border-top: 1px solid #eee; font-size: 12px; color: #666; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <div class="logo">LishFind</div>
                    <h1>Password Reset Request</h1>
                </div>
                
                <p>Hi {name},</p>
                
                <p>We received a request to reset the password for your LishFind account. Click the button below to create a new password:</p>
                
                <div style="text-align: center;">
                    <a href="{reset_url}" class="button">Reset Password</a>
                </div>
                
                <p>If the button doesn't work, you can also copy and paste this link into your browser:</p>
                <p><a href="{reset_url}">{reset_url}</a></p>
                
                <div class="warning">
                    <strong>Important:</strong> This password reset link will expire in 1 hour for security reasons. If you don't reset your password within this time, you'll need to request a new reset link.
                </div>
                
                <p>If you didn't request a password reset, you can safely ignore this email. Your password won't be changed unless you click the link above and create a new one.</p>
                
                <div class="footer">
                    <p>Best regards,<br>The LishFind Team</p>
                    <p>This is an automated email, please do not reply to this message.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        text_content = f"""
        Password Reset Request - LishFind
        
        Hi {name},
        
        We received a request to reset the password for your LishFind account. Visit this link to create a new password:
        
        {reset_url}
        
        Important: This password reset link will expire in 1 hour for security reasons.
        
        If you didn't request a password reset, you can safely ignore this email.
        
        Best regards,
        The LishFind Team
        """
        
        return await self._send_email(email, subject, html_content, text_content)
    
    async def send_welcome_email(self, email: str, name: str) -> bool:
        """Send welcome email after successful verification."""
        
        subject = "Welcome to LishFind - Your AI Search Journey Begins!"
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{ font-family: Arial, sans-serif; margin: 0; padding: 20px; background-color: #f4f4f4; }}
                .container {{ max-width: 600px; margin: 0 auto; background-color: white; padding: 30px; border-radius: 10px; }}
                .header {{ text-align: center; margin-bottom: 30px; }}
                .logo {{ font-size: 28px; font-weight: bold; color: #C77DEA; }}
                .feature {{ margin: 20px 0; padding: 15px; background-color: #f8f9ff; border-radius: 8px; }}
                .button {{ display: inline-block; padding: 15px 30px; background-color: #5FBE97; color: white; text-decoration: none; border-radius: 5px; margin: 20px 0; }}
                .footer {{ margin-top: 30px; padding-top: 20px; border-top: 1px solid #eee; font-size: 12px; color: #666; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <div class="logo">LishFind</div>
                    <h1>🎉 Welcome to LishFind!</h1>
                </div>
                
                <p>Hi {name},</p>
                
                <p>Congratulations! Your email has been verified and your LishFind account is now active. You're ready to discover amazing places with the power of AI!</p>
                
                <h3>What makes LishFind special?</h3>
                
                <div class="feature">
                    <strong>🧠 AI-Powered Search:</strong> Just tell us what you want - "a quiet café with Wi-Fi under ₹300" - and we'll find the perfect match.
                </div>
                
                <div class="feature">
                    <strong>🎯 Intent Understanding:</strong> No more endless scrolling through filters. We understand your mood, budget, and preferences.
                </div>
                
                <div class="feature">
                    <strong>💡 Smart Recommendations:</strong> Get personalized suggestions based on your taste and previous searches.
                </div>
                
                <div class="feature">
                    <strong>⭐ Real Reviews:</strong> AI-analyzed reviews give you honest insights about each place.
                </div>
                
                <div style="text-align: center;">
                    <a href="http://localhost:3000/search" class="button">Start Exploring</a>
                </div>
                
                <p>Ready to find your next favorite place? Try searching for something like:</p>
                <ul>
                    <li>"Best biryani place for a family dinner"</li>
                    <li>"Cozy café for a first date"</li>
                    <li>"Budget-friendly gym near me"</li>
                    <li>"Late-night food delivery options"</li>
                </ul>
                
                <div class="footer">
                    <p>Happy exploring!<br>The LishFind Team</p>
                    <p>Need help? Contact us at support@lishfind.com</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return await self._send_email(email, subject, html_content)
    
    async def send_business_welcome_email(self, email: str, name: str) -> bool:
        """Send welcome email for business owners."""
        
        subject = "Welcome to LishFind for Business!"
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{ font-family: Arial, sans-serif; margin: 0; padding: 20px; background-color: #f4f4f4; }}
                .container {{ max-width: 600px; margin: 0 auto; background-color: white; padding: 30px; border-radius: 10px; }}
                .header {{ text-align: center; margin-bottom: 30px; }}
                .logo {{ font-size: 28px; font-weight: bold; color: #C77DEA; }}
                .button {{ display: inline-block; padding: 15px 30px; background-color: #FFB199; color: white; text-decoration: none; border-radius: 5px; margin: 20px 0; }}
                .footer {{ margin-top: 30px; padding-top: 20px; border-top: 1px solid #eee; font-size: 12px; color: #666; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <div class="logo">LishFind</div>
                    <h1>Welcome to LishFind for Business!</h1>
                </div>
                
                <p>Hi {name},</p>
                
                <p>Thank you for joining LishFind as a business owner! You're now ready to showcase your business to customers who are actively looking for exactly what you offer.</p>
                
                <h3>Get started with these steps:</h3>
                <ol>
                    <li><strong>Claim your business</strong> - Add your business details and verify ownership</li>
                    <li><strong>Complete your profile</strong> - Add photos, services, and opening hours</li>
                    <li><strong>Monitor analytics</strong> - Track views, clicks, and customer engagement</li>
                    <li><strong>Respond to reviews</strong> - Engage with your customers</li>
                </ol>
                
                <div style="text-align: center;">
                    <a href="http://localhost:3000/business/dashboard" class="button">Go to Business Dashboard</a>
                </div>
                
                <p>Our AI recommendation system will help customers discover your business when it matches their needs perfectly. The more complete your profile, the better we can match you with the right customers!</p>
                
                <div class="footer">
                    <p>Best of luck with your business!<br>The LishFind Team</p>
                    <p>Need help? Contact us at business@lishfind.com</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return await self._send_email(email, subject, html_content)