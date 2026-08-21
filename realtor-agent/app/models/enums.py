"""Shared enumerations. Transaction and document status are explicit — never inferred from free text."""

from enum import StrEnum


class ActorOrigin(StrEnum):
    HUMAN = "human"
    AUTOMATION = "automation"
    AI = "ai"


class ActorType(StrEnum):
    REALTOR = "realtor"
    INVESTOR = "investor"
    SYSTEM = "system"
    AI = "ai"
    ADMIN = "admin"


class RequirementLevel(StrEnum):
    STRICT = "strict"
    PREFERRED = "preferred"


class PropertyType(StrEnum):
    SINGLE_FAMILY = "single_family"
    MULTI_FAMILY = "multi_family"
    CONDO = "condo"
    TOWNHOUSE = "townhouse"
    LAND = "land"
    OTHER = "other"


class OccupancyStatus(StrEnum):
    OWNER_OCCUPIED = "owner_occupied"
    TENANT_OCCUPIED = "tenant_occupied"
    VACANT = "vacant"
    UNKNOWN = "unknown"


class ListingStatus(StrEnum):
    ACTIVE = "active"
    PENDING = "pending"
    CONTINGENT = "contingent"
    COMING_SOON = "coming_soon"
    BACK_ON_MARKET = "back_on_market"
    SOLD = "sold"
    EXPIRED = "expired"
    WITHDRAWN = "withdrawn"
    CANCELLED = "cancelled"


class NotificationChannel(StrEnum):
    TELEGRAM = "telegram"
    SMS = "sms"
    EMAIL = "email"
    WHATSAPP = "whatsapp"
    WEB = "web"
    PUSH = "push"


class OpportunityStatus(StrEnum):
    MATCH_DETECTED = "MATCH_DETECTED"
    AWAITING_ARV = "AWAITING_ARV"
    AWAITING_REALTOR_REVIEW = "AWAITING_REALTOR_REVIEW"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    SNOOZED = "SNOOZED"
    APPROVED_FOR_INVESTOR_NOTIFICATION = "APPROVED_FOR_INVESTOR_NOTIFICATION"
    INVESTOR_NOTIFIED = "INVESTOR_NOTIFIED"
    INVESTOR_INTERESTED = "INVESTOR_INTERESTED"
    INVESTOR_DECLINED = "INVESTOR_DECLINED"


class RejectionReason(StrEnum):
    TOO_EXPENSIVE = "too_expensive"
    BAD_AREA = "bad_area"
    PROPERTY_CONDITION = "property_condition"
    WRONG_PROPERTY_TYPE = "wrong_property_type"
    INVESTOR_NO_LONGER_INTERESTED = "investor_no_longer_interested"
    BAD_NUMBERS = "bad_numbers"
    DUPLICATE = "duplicate"
    OTHER = "other"


class TransactionStatus(StrEnum):
    MATCHED = "MATCHED"
    REALTOR_REVIEW = "REALTOR_REVIEW"
    INVESTOR_NOTIFIED = "INVESTOR_NOTIFIED"
    INVESTOR_INTERESTED = "INVESTOR_INTERESTED"
    PROPERTY_REVIEW = "PROPERTY_REVIEW"
    OFFER_PREPARATION = "OFFER_PREPARATION"
    DOCUMENT_REVIEW = "DOCUMENT_REVIEW"
    AWAITING_SIGNATURE = "AWAITING_SIGNATURE"
    OFFER_SUBMITTED = "OFFER_SUBMITTED"
    COUNTER_RECEIVED = "COUNTER_RECEIVED"
    UNDER_CONTRACT = "UNDER_CONTRACT"
    DUE_DILIGENCE = "DUE_DILIGENCE"
    CLOSING = "CLOSING"
    CLOSED = "CLOSED"
    CANCELLED = "CANCELLED"


class DocumentStatus(StrEnum):
    DRAFT = "DRAFT"
    READY_FOR_REVIEW = "READY_FOR_REVIEW"
    APPROVED_BY_REALTOR = "APPROVED_BY_REALTOR"
    SENT_FOR_SIGNATURE = "SENT_FOR_SIGNATURE"
    SIGNED = "SIGNED"
    EXECUTED = "EXECUTED"


class DocumentType(StrEnum):
    PURCHASE_AGREEMENT = "purchase_agreement"
    ADDENDUM = "addendum"
    DISCLOSURE = "disclosure"
    COUNTEROFFER = "counteroffer"
    INSPECTION = "inspection"
    FINANCING = "financing"
    BROKERAGE = "brokerage"
    STATE_REQUIRED = "state_required"
    ASSOCIATION = "association"
    INVESTOR = "investor"
    OTHER = "other"


class CommunicationDirection(StrEnum):
    OUTBOUND = "outbound"
    INBOUND = "inbound"


class DeliveryStatus(StrEnum):
    QUEUED = "queued"
    SENT = "sent"
    DELIVERED = "delivered"
    FAILED = "failed"
    RECEIVED = "received"


class PacketStatus(StrEnum):
    IGNORED = "ignored"
    RECEIVED = "received"
    APPLIED = "applied"
    PARTIAL = "partial"
    UNCLASSIFIED = "unclassified"


class InvestorResponse(StrEnum):
    YES = "YES"
    NO = "NO"
    MORE_INFO = "MORE_INFO"


class FinancingType(StrEnum):
    CASH = "cash"
    CONVENTIONAL = "conventional"
    HARD_MONEY = "hard_money"
    SELLER_FINANCE = "seller_finance"
    ASSUMABLE = "assumable"
    OTHER = "other"


TRANSACTION_TRANSITIONS: dict[TransactionStatus, set[TransactionStatus]] = {
    TransactionStatus.MATCHED: {TransactionStatus.REALTOR_REVIEW, TransactionStatus.CANCELLED},
    TransactionStatus.REALTOR_REVIEW: {TransactionStatus.INVESTOR_NOTIFIED, TransactionStatus.CANCELLED},
    TransactionStatus.INVESTOR_NOTIFIED: {
        TransactionStatus.INVESTOR_INTERESTED,
        TransactionStatus.CANCELLED,
    },
    TransactionStatus.INVESTOR_INTERESTED: {
        TransactionStatus.PROPERTY_REVIEW,
        TransactionStatus.OFFER_PREPARATION,
        TransactionStatus.CANCELLED,
    },
    TransactionStatus.PROPERTY_REVIEW: {
        TransactionStatus.OFFER_PREPARATION,
        TransactionStatus.CANCELLED,
    },
    TransactionStatus.OFFER_PREPARATION: {
        TransactionStatus.DOCUMENT_REVIEW,
        TransactionStatus.CANCELLED,
    },
    TransactionStatus.DOCUMENT_REVIEW: {
        TransactionStatus.AWAITING_SIGNATURE,
        TransactionStatus.OFFER_PREPARATION,
        TransactionStatus.CANCELLED,
    },
    TransactionStatus.AWAITING_SIGNATURE: {
        TransactionStatus.OFFER_SUBMITTED,
        TransactionStatus.DOCUMENT_REVIEW,
        TransactionStatus.CANCELLED,
    },
    TransactionStatus.OFFER_SUBMITTED: {
        TransactionStatus.COUNTER_RECEIVED,
        TransactionStatus.UNDER_CONTRACT,
        TransactionStatus.CANCELLED,
    },
    TransactionStatus.COUNTER_RECEIVED: {
        TransactionStatus.OFFER_PREPARATION,
        TransactionStatus.UNDER_CONTRACT,
        TransactionStatus.CANCELLED,
    },
    TransactionStatus.UNDER_CONTRACT: {
        TransactionStatus.DUE_DILIGENCE,
        TransactionStatus.CANCELLED,
    },
    TransactionStatus.DUE_DILIGENCE: {
        TransactionStatus.CLOSING,
        TransactionStatus.CANCELLED,
    },
    TransactionStatus.CLOSING: {TransactionStatus.CLOSED, TransactionStatus.CANCELLED},
    TransactionStatus.CLOSED: set(),
    TransactionStatus.CANCELLED: set(),
}


DOCUMENT_TRANSITIONS: dict[DocumentStatus, set[DocumentStatus]] = {
    DocumentStatus.DRAFT: {DocumentStatus.READY_FOR_REVIEW},
    DocumentStatus.READY_FOR_REVIEW: {
        DocumentStatus.APPROVED_BY_REALTOR,
        DocumentStatus.DRAFT,
    },
    DocumentStatus.APPROVED_BY_REALTOR: {DocumentStatus.SENT_FOR_SIGNATURE},
    DocumentStatus.SENT_FOR_SIGNATURE: {DocumentStatus.SIGNED},
    DocumentStatus.SIGNED: {DocumentStatus.EXECUTED},
    DocumentStatus.EXECUTED: set(),
}
