"""
Learning Management System Models for MahaSeWA
Provides training and certification for housing society members
"""
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, Enum, Float, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from app.models.base import Base, TimestampMixin


class CourseCategory(str, enum.Enum):
    """Course categories"""
    SOCIETY_MANAGEMENT = "society_management"
    LEGAL_COMPLIANCE = "legal_compliance"
    FINANCIAL_MANAGEMENT = "financial_management"
    DEEMED_CONVEYANCE = "deemed_conveyance"
    RERA_COMPLIANCE = "rera_compliance"
    Maharashtra_COOPERATIVE_ACT = "maharashtra_cooperative_act"
    COMMITTEE_TRAINING = "committee_training"
    DISPUTE_RESOLUTION = "dispute_resolution"
    MAINTENANCE = "maintenance"
    OTHER = "other"


class CourseLevel(str, enum.Enum):
    """Course difficulty levels"""
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"


class LessonType(str, enum.Enum):
    """Types of lessons"""
    VIDEO = "video"
    ARTICLE = "article"
    PDF = "pdf"
    QUIZ = "quiz"
    ASSIGNMENT = "assignment"
    INTERACTIVE = "interactive"


class QuestionType(str, enum.Enum):
    """Quiz question types"""
    MULTIPLE_CHOICE = "multiple_choice"
    TRUE_FALSE = "true_false"
    SHORT_ANSWER = "short_answer"
    ESSAY = "essay"


class EnrollmentStatus(str, enum.Enum):
    """Enrollment status"""
    ACTIVE = "active"
    COMPLETED = "completed"
    DROPPED = "dropped"
    EXPIRED = "expired"


class Course(Base):
    """Training courses for housing society management"""
    __tablename__ = "lms_courses"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False, index=True)
    slug = Column(String(255), unique=True, nullable=False, index=True)
    description = Column(Text)
    short_description = Column(String(500))
    
    # Categorization
    category = Column(Enum(CourseCategory), nullable=False, index=True)
    level = Column(Enum(CourseLevel), default=CourseLevel.BEGINNER)
    tags = Column(JSON)  # ["deemed conveyance", "legal", etc.]
    
    # Media
    thumbnail_url = Column(String(500))
    preview_video_url = Column(String(500))
    
    # Instructor
    instructor_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    instructor = relationship("User", foreign_keys=[instructor_id])
    
    # Course details
    duration_hours = Column(Integer)  # Total course duration
    lessons_count = Column(Integer, default=0)
    
    # Pricing
    is_free = Column(Boolean, default=False)
    price = Column(Float, default=0.0)
    
    # Publishing
    is_published = Column(Boolean, default=False)
    published_at = Column(DateTime)
    
    # Stats
    enrolled_count = Column(Integer, default=0)
    rating_average = Column(Float, default=0.0)
    rating_count = Column(Integer, default=0)
    
    # Requirements and outcomes
    prerequisites = Column(JSON)  # List of prerequisite course IDs
    learning_outcomes = Column(JSON)  # List of learning outcomes
    requirements = Column(JSON)  # List of requirements
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    modules = relationship("CourseModule", back_populates="course", cascade="all, delete-orphan")
    enrollments = relationship("Enrollment", back_populates="course", cascade="all, delete-orphan")
    reviews = relationship("CourseReview", back_populates="course", cascade="all, delete-orphan")


class CourseModule(Base):
    """Modules/Sections within a course"""
    __tablename__ = "lms_course_modules"

    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(Integer, ForeignKey("lms_courses.id"), nullable=False)
    
    title = Column(String(255), nullable=False)
    description = Column(Text)
    order = Column(Integer, default=0)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    course = relationship("Course", back_populates="modules")
    lessons = relationship("Lesson", back_populates="module", cascade="all, delete-orphan")


class Lesson(Base):
    """Individual lessons within a module"""
    __tablename__ = "lms_lessons"

    id = Column(Integer, primary_key=True, index=True)
    module_id = Column(Integer, ForeignKey("lms_course_modules.id"), nullable=False)
    
    title = Column(String(255), nullable=False)
    description = Column(Text)
    order = Column(Integer, default=0)
    
    # Content
    lesson_type = Column(Enum(LessonType), nullable=False)
    content = Column(Text)  # HTML content for articles
    video_url = Column(String(500))
    file_url = Column(String(500))  # For PDFs, documents
    duration_minutes = Column(Integer)
    
    # Settings
    is_preview = Column(Boolean, default=False)  # Can be viewed without enrollment
    is_mandatory = Column(Boolean, default=True)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    module = relationship("CourseModule", back_populates="lessons")
    quiz = relationship("Quiz", back_populates="lesson", uselist=False, cascade="all, delete-orphan")
    progress_records = relationship("LessonProgress", back_populates="lesson", cascade="all, delete-orphan")


class Quiz(Base):
    """Quizzes/Assessments for lessons"""
    __tablename__ = "lms_quizzes"

    id = Column(Integer, primary_key=True, index=True)
    lesson_id = Column(Integer, ForeignKey("lms_lessons.id"), nullable=False)
    
    title = Column(String(255), nullable=False)
    description = Column(Text)
    
    # Settings
    passing_score = Column(Integer, default=70)  # Percentage
    time_limit_minutes = Column(Integer)  # Optional time limit
    attempts_allowed = Column(Integer, default=3)
    shuffle_questions = Column(Boolean, default=True)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    lesson = relationship("Lesson", back_populates="quiz")
    questions = relationship("QuizQuestion", back_populates="quiz", cascade="all, delete-orphan")
    attempts = relationship("QuizAttempt", back_populates="quiz", cascade="all, delete-orphan")


class QuizQuestion(Base):
    """Questions in a quiz"""
    __tablename__ = "lms_quiz_questions"

    id = Column(Integer, primary_key=True, index=True)
    quiz_id = Column(Integer, ForeignKey("lms_quizzes.id"), nullable=False)
    
    question_text = Column(Text, nullable=False)
    question_type = Column(Enum(QuestionType), nullable=False)
    order = Column(Integer, default=0)
    
    # For multiple choice
    options = Column(JSON)  # [{"id": "a", "text": "Option A"}, ...]
    correct_answer = Column(JSON)  # "a" or ["a", "b"] for multiple correct
    
    # For short answer/essay
    sample_answer = Column(Text)
    
    points = Column(Integer, default=1)
    explanation = Column(Text)  # Shown after answering
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    quiz = relationship("Quiz", back_populates="questions")


class Enrollment(Base):
    """User course enrollments"""
    __tablename__ = "lms_enrollments"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    course_id = Column(Integer, ForeignKey("lms_courses.id"), nullable=False)
    
    # Status
    status = Column(Enum(EnrollmentStatus), default=EnrollmentStatus.ACTIVE)
    progress_percentage = Column(Integer, default=0)
    
    # Timestamps
    enrolled_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    expires_at = Column(DateTime)  # For time-limited courses
    
    # Certificate
    certificate_issued = Column(Boolean, default=False)
    certificate_url = Column(String(500))
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    course = relationship("Course", back_populates="enrollments")
    lesson_progress = relationship("LessonProgress", back_populates="enrollment", cascade="all, delete-orphan")
    quiz_attempts = relationship("QuizAttempt", back_populates="enrollment", cascade="all, delete-orphan")


class LessonProgress(Base):
    """Track user progress through lessons"""
    __tablename__ = "lms_lesson_progress"

    id = Column(Integer, primary_key=True, index=True)
    enrollment_id = Column(Integer, ForeignKey("lms_enrollments.id"), nullable=False)
    lesson_id = Column(Integer, ForeignKey("lms_lessons.id"), nullable=False)
    
    # Progress
    is_completed = Column(Boolean, default=False)
    time_spent_minutes = Column(Integer, default=0)
    last_position = Column(Integer, default=0)  # For video position, scroll position, etc.
    
    # Timestamps
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    last_accessed_at = Column(DateTime, default=datetime.utcnow)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    enrollment = relationship("Enrollment", back_populates="lesson_progress")
    lesson = relationship("Lesson", back_populates="progress_records")


class QuizAttempt(Base):
    """User quiz attempts"""
    __tablename__ = "lms_quiz_attempts"

    id = Column(Integer, primary_key=True, index=True)
    enrollment_id = Column(Integer, ForeignKey("lms_enrollments.id"), nullable=False)
    quiz_id = Column(Integer, ForeignKey("lms_quizzes.id"), nullable=False)
    
    # Attempt details
    attempt_number = Column(Integer, nullable=False)
    score = Column(Integer)  # Percentage
    is_passed = Column(Boolean, default=False)
    
    # Answers
    answers = Column(JSON)  # {question_id: answer}
    
    # Timing
    started_at = Column(DateTime, default=datetime.utcnow)
    submitted_at = Column(DateTime)
    time_taken_minutes = Column(Integer)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    enrollment = relationship("Enrollment", back_populates="quiz_attempts")
    quiz = relationship("Quiz", back_populates="attempts")


class CourseReview(Base):
    """Course reviews and ratings"""
    __tablename__ = "lms_course_reviews"

    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(Integer, ForeignKey("lms_courses.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    rating = Column(Integer, nullable=False)  # 1-5
    review_text = Column(Text)
    
    # Helpful votes
    helpful_count = Column(Integer, default=0)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    course = relationship("Course", back_populates="reviews")
    user = relationship("User", foreign_keys=[user_id])


class Certificate(Base):
    """Course completion certificates"""
    __tablename__ = "lms_certificates"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    course_id = Column(Integer, ForeignKey("lms_courses.id"), nullable=False)
    enrollment_id = Column(Integer, ForeignKey("lms_enrollments.id"), nullable=False)
    
    # Certificate details
    certificate_number = Column(String(100), unique=True, nullable=False, index=True)
    certificate_url = Column(String(500))
    
    # Scores
    final_score = Column(Integer)  # Percentage
    grade = Column(String(2))  # A+, A, B+, etc.
    
    # Issued details
    issued_at = Column(DateTime, default=datetime.utcnow)
    issued_by_id = Column(Integer, ForeignKey("users.id"))
    
    # Verification
    verification_code = Column(String(100), unique=True, index=True)
    is_valid = Column(Boolean, default=True)
    revoked_at = Column(DateTime)
    revoked_reason = Column(Text)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    course = relationship("Course")
    enrollment = relationship("Enrollment")
    issued_by = relationship("User", foreign_keys=[issued_by_id])

