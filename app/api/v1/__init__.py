# API v1 routers
# This file ensures all routers are properly exported

from . import (
    auth,
    societies,
    members,
    providers,
    subscriptions,
    consultations,
    bookings,
    compliance,
    content,
    admin,
    lms,
    analytics,
    publication_ads,
    uploads,
    invoices
)

__all__ = [
    "auth",
    "societies",
    "members",
    "providers",
    "subscriptions",
    "consultations",
    "bookings",
    "compliance",
    "content",
    "admin",
    "lms",
    "analytics",
    "publication_ads",
    "uploads",
    "invoices"
]
