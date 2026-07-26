
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
            
    def send(self, to_email, subject, html_content, cc=None):
        # cc: lista de correos (o None). Se filtran vacíos/duplicados del destinatario.
        cc_list = [c for c in (cc or []) if c and c != to_email]

        if not self.sg:
            cc_txt = f"\nCc: {', '.join(cc_list)}" if cc_list else ""
            print(f"--- [DEMO EMAIL] ---\nTo: {to_email}{cc_txt}\nSubject: {subject}\nContent: {html_content}\n--------------------")
            return True

        from_email = Email(os.environ.get('SENDGRID_FROM_EMAIL', 'noreply@gestorcartografico.com'))
        content = Content("text/html", html_content)
        mail = Mail(from_email, To(to_email), subject, content)
        if cc_list:
            from sendgrid.helpers.mail import Cc
            for c in cc_list:
                try:
                    mail.add_cc(Cc(c))
                except Exception:
                    pass

        try:
            response = self.sg.client.mail.send.post(request_body=mail.get())
            return response.status_code in (200, 201, 202)
        except Exception as e:
            print(f"Error sending email: {str(e)}")
            return False

email_service = EmailService()
