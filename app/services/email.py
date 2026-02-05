
import os
import sendgrid
from sendgrid.helpers.mail import Mail, Email, To, Content
from flask import current_app

class EmailService:
    def __init__(self):
        self.api_key = os.environ.get('SENDGRID_API_KEY')
        if not self.api_key:
            print("WARNING: SENDGRID_API_KEY not found. Email service will run in DEMO mode (printing to console).")
            self.sg = None
        else:
            self.sg = sendgrid.SendGridAPIClient(api_key=self.api_key)
            
    def send(self, to_email, subject, html_content):
        if not self.sg:
            print(f"--- [DEMO EMAIL] ---\nTo: {to_email}\nSubject: {subject}\nContent: {html_content}\n--------------------")
            return True
            
        from_email = Email(os.environ.get('SENDGRID_FROM_EMAIL', 'noreply@gestorcartografico.com'))
        to_email = To(to_email)
        content = Content("text/html", html_content)
        mail = Mail(from_email, to_email, subject, content)
        
        try:
            response = self.sg.client.mail.send.post(request_body=mail.get())
            return response.status_code in (200, 201, 202)
        except Exception as e:
            print(f"Error sending email: {str(e)}")
            return False

email_service = EmailService()
