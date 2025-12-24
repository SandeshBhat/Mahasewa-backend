"""Database models for MahaSeWA platform"""
from sqlalchemy import Integer
from app.models.base import Base
from app.models.user import User
from app.models.member import Member, MembershipTier
from app.models.case import Case, CaseTimeline, CaseDocument
from app.models.publication import Publication, Order, OrderItem
from app.models.content import BlogPost, Event, EventRegistration, Download, DownloadLog, FAQ
from app.models.organization import Branch, StaffAssignment
from app.models.society import Society, SocietyMember
from app.models.provider import ServiceProvider, Service
from app.models.consultation import Consultation
from app.models.booking import ServiceBooking
from app.models.compliance import ComplianceRequirement, ComplianceSubmission
from app.models.lms import (
    Course,
    CourseModule,
    Lesson,
    Enrollment,
    LessonProgress,
    Quiz,
    QuizQuestion,
    QuizAttempt,
    Certificate,
    CourseReview,
)

__all__ = [
    "Base",
    "User",
    "Member",
    "MembershipTier",
    "Case",
    "CaseTimeline",
    "CaseDocument",
    "Publication",
    "Order",
    "OrderItem",
    "BlogPost",
    "Event",
    "EventRegistration",
    "Download",
    "DownloadLog",
    "FAQ",
    "Branch",
    "StaffAssignment",
    "Society",
    "SocietyMember",
    "ServiceProvider",
    "Service",
    "Consultation",
    "ServiceBooking",
    "ComplianceRequirement",
    "ComplianceSubmission",
    # LMS Models
    "Course",
    "CourseModule",
    "Lesson",
    "Enrollment",
    "LessonProgress",
    "Quiz",
    "QuizQuestion",
    "QuizAttempt",
    "Certificate",
    "CourseReview",
]

