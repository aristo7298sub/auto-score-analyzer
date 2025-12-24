"""Email sending abstraction.

Stage-1 auth requires sending 6-digit verification/reset codes.
Provider is selected via environment variables to avoid hard-coding any infra.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from app.core.config import settings

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class EmailMessage:
    to_email: str
    subject: str
    text_body: str


class EmailSendError(RuntimeError):
    pass


def send_email(message: EmailMessage) -> None:
    provider = getattr(settings, "EMAIL_PROVIDER", "dev")

    if provider == "disabled":
        logger.warning("Email provider disabled; skipping send: to=%s subject=%s", message.to_email, message.subject)
        return

    if provider == "dev":
        if bool(getattr(settings, "EMAIL_LOG_CODES_IN_DEV", True)):
            logger.info("[DEV] Email send: to=%s subject=%s body=%s", message.to_email, message.subject, message.text_body)
        else:
            logger.info("[DEV] Email send: to=%s subject=%s (body hidden)", message.to_email, message.subject)
        return

    if provider == "acs":
        conn_str = getattr(settings, "ACS_EMAIL_CONNECTION_STRING", None)
        sender = getattr(settings, "ACS_EMAIL_SENDER", None)
        if not conn_str or not sender:
            raise EmailSendError("ACS email is selected but ACS_EMAIL_CONNECTION_STRING/ACS_EMAIL_SENDER not configured")

        try:
            # Import lazily so dev users don't need the SDK.
            from azure.communication.email import EmailClient  # type: ignore

            client = EmailClient.from_connection_string(conn_str)

            payload = {
                "senderAddress": sender,
                "recipients": {"to": [{"address": message.to_email}]},
                "content": {
                    "subject": message.subject,
                    "plainText": message.text_body,
                },
            }

            poller = client.begin_send(payload)
            result = poller.result()

            # Best-effort logging without leaking secrets.
            status = getattr(result, "status", None)
            error = getattr(result, "error", None)
            if status and str(status).lower() not in {"succeeded", "success"}:
                raise EmailSendError(f"ACS email send failed: status={status} error={error}")

            return
        except EmailSendError:
            raise
        except Exception as exc:
            raise EmailSendError("ACS email send failed") from exc

    raise EmailSendError(f"Unknown email provider: {provider}")
