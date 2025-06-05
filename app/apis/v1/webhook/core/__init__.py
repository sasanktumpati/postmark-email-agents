from .db import (
    Email,
    EmailAttachment,
    EmailHeader,
    EmailRecipient,
    EmailsRaw,
    ProcessingStatusEnum,
    RecipientTypeEnum,
    SpamStatusEnum,
)
from .models import (
    AttachmentModel,
    FromFullModel,
    HeaderModel,
    PostmarkInboundEmail,
    ToCcFullModel,
)
from .services import (
    EmailWebhookService,
    get_email_service,
)

__db__ = {
    "RecipientTypeEnum": RecipientTypeEnum,
    "ProcessingStatusEnum": ProcessingStatusEnum,
    "SpamStatusEnum": SpamStatusEnum,
    "EmailsRaw": EmailsRaw,
    "Email": Email,
    "EmailRecipient": EmailRecipient,
    "EmailAttachment": EmailAttachment,
    "EmailHeader": EmailHeader,
}


__models__ = {
    "FromFullModel": FromFullModel,
    "ToCcFullModel": ToCcFullModel,
    "AttachmentModel": AttachmentModel,
    "HeaderModel": HeaderModel,
    "PostmarkInboundEmail": PostmarkInboundEmail,
}


__services__ = {
    "EmailWebhookService": EmailWebhookService,
    "get_email_service": get_email_service,
}


__all__ = (
    list(__db__.values()) + list(__models__.values()) + list(__services__.values())
)
