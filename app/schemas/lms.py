"""
LMS Schemas for MahaSeWA API
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Union
from datetime import datetime
from app.models.lms import (
    CourseCategory, CourseLevel, LessonType, 
    QuestionType, EnrollmentStatus
)


# Course Schemas
class CourseBase(BaseModel):
    title: str = Field(..., min_length=3, max_length=255)
    slug: str
    description: Optional[str] = None
    short_description: Optional[str] = Field(None, max_length=500)
    category: CourseCategory
    level: CourseLevel = CourseLevel.BEGINNER
    tags: Optional[List[str]] = []
    thumbnail_url: Optional[str] = None
    preview_video_url: Optional[str] = None
    duration_hours: Optional[int] = None
    is_free: bool = False
    price: float = 0.0
    learning_outcomes: Optional[List[str]] = []
    requirements: Optional[List[str]] = []


class CourseCreate(CourseBase):
    instructor_id: int


class CourseUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    short_description: Optional[str] = None
    category: Optional[CourseCategory] = None
    level: Optional[CourseLevel] = None
    tags: Optional[List[str]] = None
    thumbnail_url: Optional[str] = None
    preview_video_url: Optional[str] = None
    duration_hours: Optional[int] = None
    is_free: Optional[bool] = None
    price: Optional[float] = None
    is_published: Optional[bool] = None
    learning_outcomes: Optional[List[str]] = None
    requirements: Optional[List[str]] = None


class CourseResponse(CourseBase):
    id: int
    instructor_id: int
    lessons_count: int
    is_published: bool
    published_at: Optional[datetime]
    enrolled_count: int
    rating_average: float
    rating_count: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CourseListResponse(BaseModel):
    id: int
    title: str
    slug: str
    short_description: Optional[str]
    category: CourseCategory
    level: CourseLevel
    thumbnail_url: Optional[str]
    instructor_id: int
    duration_hours: Optional[int]
    is_free: bool
    price: float
    enrolled_count: int
    rating_average: float
    rating_count: int
    lessons_count: int

    class Config:
        from_attributes = True


# Module Schemas
class ModuleBase(BaseModel):
    title: str = Field(..., min_length=3, max_length=255)
    description: Optional[str] = None
    order: int = 0


class ModuleCreate(ModuleBase):
    course_id: int


class ModuleUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    order: Optional[int] = None


class ModuleResponse(ModuleBase):
    id: int
    course_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Lesson Schemas
class LessonBase(BaseModel):
    title: str = Field(..., min_length=3, max_length=255)
    description: Optional[str] = None
    order: int = 0
    lesson_type: LessonType
    content: Optional[str] = None
    video_url: Optional[str] = None
    file_url: Optional[str] = None
    duration_minutes: Optional[int] = None
    is_preview: bool = False
    is_mandatory: bool = True


class LessonCreate(LessonBase):
    module_id: int


class LessonUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    order: Optional[int] = None
    lesson_type: Optional[LessonType] = None
    content: Optional[str] = None
    video_url: Optional[str] = None
    file_url: Optional[str] = None
    duration_minutes: Optional[int] = None
    is_preview: Optional[bool] = None
    is_mandatory: Optional[bool] = None


class LessonResponse(LessonBase):
    id: int
    module_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Quiz Schemas
class QuizBase(BaseModel):
    title: str = Field(..., min_length=3, max_length=255)
    description: Optional[str] = None
    passing_score: int = Field(70, ge=0, le=100)
    time_limit_minutes: Optional[int] = None
    attempts_allowed: int = Field(3, ge=1)
    shuffle_questions: bool = True


class QuizCreate(QuizBase):
    lesson_id: int


class QuizUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    passing_score: Optional[int] = None
    time_limit_minutes: Optional[int] = None
    attempts_allowed: Optional[int] = None
    shuffle_questions: Optional[bool] = None


class QuizResponse(QuizBase):
    id: int
    lesson_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Quiz Question Schemas
class QuestionBase(BaseModel):
    question_text: str
    question_type: QuestionType
    order: int = 0
    options: Optional[List[dict]] = None
    correct_answer: Optional[Union[str, List[str]]] = None
    sample_answer: Optional[str] = None
    points: int = 1
    explanation: Optional[str] = None


class QuestionCreate(QuestionBase):
    quiz_id: int


class QuestionUpdate(BaseModel):
    question_text: Optional[str] = None
    question_type: Optional[QuestionType] = None
    order: Optional[int] = None
    options: Optional[List[dict]] = None
    correct_answer: Optional[Union[str, List[str]]] = None
    sample_answer: Optional[str] = None
    points: Optional[int] = None
    explanation: Optional[str] = None


class QuestionResponse(QuestionBase):
    id: int
    quiz_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Enrollment Schemas
class EnrollmentCreate(BaseModel):
    course_id: int


class EnrollmentResponse(BaseModel):
    id: int
    user_id: int
    course_id: int
    status: EnrollmentStatus
    progress_percentage: int
    enrolled_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    certificate_issued: bool
    certificate_url: Optional[str]

    class Config:
        from_attributes = True


# Progress Schemas
class LessonProgressUpdate(BaseModel):
    is_completed: bool = False
    time_spent_minutes: int = 0
    last_position: int = 0


class LessonProgressResponse(BaseModel):
    id: int
    enrollment_id: int
    lesson_id: int
    is_completed: bool
    time_spent_minutes: int
    last_position: int
    last_accessed_at: datetime

    class Config:
        from_attributes = True


# Quiz Attempt Schemas
class QuizAttemptSubmit(BaseModel):
    quiz_id: int
    answers: dict  # {question_id: answer}


class QuizAttemptResponse(BaseModel):
    id: int
    enrollment_id: int
    quiz_id: int
    attempt_number: int
    score: Optional[int]
    is_passed: bool
    started_at: datetime
    submitted_at: Optional[datetime]
    time_taken_minutes: Optional[int]

    class Config:
        from_attributes = True


# Review Schemas
class ReviewCreate(BaseModel):
    course_id: int
    rating: int = Field(..., ge=1, le=5)
    review_text: Optional[str] = None


class ReviewUpdate(BaseModel):
    rating: Optional[int] = Field(None, ge=1, le=5)
    review_text: Optional[str] = None


class ReviewResponse(BaseModel):
    id: int
    course_id: int
    user_id: int
    rating: int
    review_text: Optional[str]
    helpful_count: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Certificate Schemas
class CertificateResponse(BaseModel):
    id: int
    user_id: int
    course_id: int
    certificate_number: str
    certificate_url: Optional[str]
    final_score: Optional[int]
    grade: Optional[str]
    issued_at: datetime
    verification_code: str
    is_valid: bool

    class Config:
        from_attributes = True


# Dashboard/Stats Schemas
class StudentDashboard(BaseModel):
    enrolled_courses: int
    completed_courses: int
    in_progress_courses: int
    certificates_earned: int
    total_learning_hours: int


class InstructorDashboard(BaseModel):
    total_courses: int
    published_courses: int
    total_students: int
    total_reviews: int
    average_rating: float


class CourseDashboard(BaseModel):
    total_enrollments: int
    active_students: int
    completion_rate: float
    average_progress: float
    average_rating: float
    total_reviews: int

