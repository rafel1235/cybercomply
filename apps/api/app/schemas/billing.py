from datetime import datetime

from pydantic import BaseModel


class EntitlementsOut(BaseModel):
    max_users: int | None
    max_ai_documents_per_month: int | None
    compliance_measures_limit: int | None
    compliance_measures_editable: bool
    incident_reporting_enabled: bool
    supply_chain_enabled: bool
    quarterly_reports_enabled: bool
    white_label_enabled: bool
    api_access_enabled: bool


class UsageOut(BaseModel):
    documents_generated_this_month: int
    users_count: int


class SubscriptionOut(BaseModel):
    plan: str
    status: str
    trial_ends_at: datetime | None = None
    renews_at: datetime | None = None
    entitlements: EntitlementsOut
    usage: UsageOut


class CheckoutRequest(BaseModel):
    plan: str


class CheckoutResponse(BaseModel):
    checkout_url: str


class PortalResponse(BaseModel):
    portal_url: str
