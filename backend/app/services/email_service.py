import sib_api_v3_sdk
from sib_api_v3_sdk.rest import ApiException
from ..core.config import settings
import logging

# Configure logging
logger = logging.getLogger(__name__)

class EmailService:
    def __init__(self):
        # Configure API key authorization
        configuration = sib_api_v3_sdk.Configuration()
        configuration.api_key['api-key'] = settings.BREVO_API_KEY
        self.api_client = sib_api_v3_sdk.ApiClient(configuration)
        self.api_instance = sib_api_v3_sdk.TransactionalEmailsApi(self.api_client)

    def send_verification_email(self, email: str, token: str) -> bool:
        """Send an email with a link to verify the user's account."""
        verification_url = f"http://localhost:8000/api/v1/verify-email?token={token}"
        message = f"Welcome to OmniDrive! Please verify your email by clicking here: {verification_url}"
        return self._send_email(email, "Verify your OmniDrive Account", message)

    def send_password_reset_email(self, email: str, token: str) -> bool:
        """Send an email with a link to reset the user's password."""
        reset_url = f"http://localhost:3000/reset-password?token={token}"
        message = f"You requested a password reset for your OmniDrive account. Click here: {reset_url}"
        return self._send_email(email, "Reset your OmniDrive Password", message)

    def _send_email(self, to_email: str, subject: str, content: str) -> bool:
        """Internal helper to send transactional emails via Brevo."""
        try:
            send_smtp_email = sib_api_v3_sdk.SendSmtpEmail(
                sender=sib_api_v3_sdk.SendSmtpEmailSender(
                    email=settings.BREVO_SENDER_EMAIL,
                    name=settings.BREVO_SENDER_NAME,
                ),
                to=[sib_api_v3_sdk.SendSmtpEmailTo(email=to_email)],
                subject=subject,
                html_content=f"<html><body><p>{content}</p></body></html>",
            )
            self.api_instance.send_transac_email(send_smtp_email)
            return True
        except ApiException as e:
            logger.error(f"Exception when calling TransactionalEmailsApi->send_transac_email: {e}")
            return False

# Singleton instance
email_service = EmailService()
