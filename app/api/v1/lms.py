"""
LMS API Endpoints for MahaSeWA
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from app.db.session import get_db
from app.models.user import User
from app.models.lms import (
    Course, CourseModule, Lesson, Quiz, QuizQuestion,
    Enrollment, LessonProgress, QuizAttempt, CourseReview, Certificate,
    EnrollmentStatus, CourseCategory, CourseLevel
)
from app.schemas.lms import (
    CourseCreate, CourseUpdate, CourseResponse, CourseListResponse,
    ModuleCreate, ModuleUpdate, ModuleResponse,
    LessonCreate, LessonUpdate, LessonResponse,
    QuizCreate, QuizUpdate, QuizResponse,
    QuestionCreate, QuestionUpdate, QuestionResponse,
    EnrollmentCreate, EnrollmentResponse,
    LessonProgressUpdate, LessonProgressResponse,
    QuizAttemptSubmit, QuizAttemptResponse,
    ReviewCreate, ReviewUpdate, ReviewResponse,
    CertificateResponse,
    StudentDashboard, InstructorDashboard, CourseDashboard
)
from app.dependencies.auth import get_current_user, require_role

router = APIRouter(prefix="/lms", tags=["LMS"])


# ==================== COURSE ENDPOINTS ====================

@router.get("/courses", response_model=List[CourseListResponse])
async def list_courses(
    category: Optional[CourseCategory] = None,
    level: Optional[CourseLevel] = None,
    is_free: Optional[bool] = None,
    search: Optional[str] = None,
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db)
):
    """List all published courses with optional filters"""
    query = db.query(Course).filter(Course.is_published == True)
    
    if category:
        query = query.filter(Course.category == category)
    if level:
        query = query.filter(Course.level == level)
    if is_free is not None:
        query = query.filter(Course.is_free == is_free)
    if search:
        query = query.filter(Course.title.ilike(f"%{search}%"))
    
    courses = query.offset(skip).limit(limit).all()
    return courses


@router.post("/courses", response_model=CourseResponse, status_code=status.HTTP_201_CREATED)
async def create_course(
    course: CourseCreate,
    current_user: User = Depends(require_role(["admin", "instructor"])),
    db: Session = Depends(get_db)
):
    """Create a new course (admin or instructor only)"""
    # Check if slug already exists
    existing = db.query(Course).filter(Course.slug == course.slug).first()
    if existing:
        raise HTTPException(status_code=400, detail="Course slug already exists")
    
    new_course = Course(**course.dict())
    db.add(new_course)
    db.commit()
    db.refresh(new_course)
    return new_course


@router.get("/courses/{course_id}", response_model=CourseResponse)
async def get_course(course_id: int, db: Session = Depends(get_db)):
    """Get course details"""
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    return course


@router.put("/courses/{course_id}", response_model=CourseResponse)
async def update_course(
    course_id: int,
    course_update: CourseUpdate,
    current_user: User = Depends(require_role(["admin", "instructor"])),
    db: Session = Depends(get_db)
):
    """Update course (instructor or admin only)"""
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    
    # Check if user is instructor of this course or admin
    if course.instructor_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")
    
    for key, value in course_update.dict(exclude_unset=True).items():
        setattr(course, key, value)
    
    db.commit()
    db.refresh(course)
    return course


@router.delete("/courses/{course_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_course(
    course_id: int,
    current_user: User = Depends(require_role(["admin"])),
    db: Session = Depends(get_db)
):
    """Delete course (admin only)"""
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    
    db.delete(course)
    db.commit()
    return None


# ==================== MODULE ENDPOINTS ====================

@router.post("/modules", response_model=ModuleResponse, status_code=status.HTTP_201_CREATED)
async def create_module(
    module: ModuleCreate,
    current_user: User = Depends(require_role(["admin", "instructor"])),
    db: Session = Depends(get_db)
):
    """Create a new course module"""
    course = db.query(Course).filter(Course.id == module.course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    
    if course.instructor_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")
    
    new_module = CourseModule(**module.dict())
    db.add(new_module)
    db.commit()
    db.refresh(new_module)
    return new_module


@router.get("/courses/{course_id}/modules", response_model=List[ModuleResponse])
async def list_modules(course_id: int, db: Session = Depends(get_db)):
    """List all modules in a course"""
    modules = db.query(CourseModule).filter(
        CourseModule.course_id == course_id
    ).order_by(CourseModule.order).all()
    return modules


# ==================== LESSON ENDPOINTS ====================

@router.post("/lessons", response_model=LessonResponse, status_code=status.HTTP_201_CREATED)
async def create_lesson(
    lesson: LessonCreate,
    current_user: User = Depends(require_role(["admin", "instructor"])),
    db: Session = Depends(get_db)
):
    """Create a new lesson"""
    module = db.query(CourseModule).filter(CourseModule.id == lesson.module_id).first()
    if not module:
        raise HTTPException(status_code=404, detail="Module not found")
    
    course = db.query(Course).filter(Course.id == module.course_id).first()
    if course.instructor_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")
    
    new_lesson = Lesson(**lesson.dict())
    db.add(new_lesson)
    
    # Update course lessons count
    course.lessons_count += 1
    
    db.commit()
    db.refresh(new_lesson)
    return new_lesson


@router.get("/modules/{module_id}/lessons", response_model=List[LessonResponse])
async def list_lessons(module_id: int, db: Session = Depends(get_db)):
    """List all lessons in a module"""
    lessons = db.query(Lesson).filter(
        Lesson.module_id == module_id
    ).order_by(Lesson.order).all()
    return lessons


# ==================== ENROLLMENT ENDPOINTS ====================

@router.post("/enrollments", response_model=EnrollmentResponse, status_code=status.HTTP_201_CREATED)
async def enroll_in_course(
    enrollment: EnrollmentCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Enroll in a course"""
    # Check if course exists
    course = db.query(Course).filter(Course.id == enrollment.course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    
    if not course.is_published:
        raise HTTPException(status_code=400, detail="Course is not published yet")
    
    # Check if already enrolled
    existing = db.query(Enrollment).filter(
        Enrollment.user_id == current_user.id,
        Enrollment.course_id == enrollment.course_id
    ).first()
    
    if existing:
        raise HTTPException(status_code=400, detail="Already enrolled in this course")
    
    # Create enrollment
    new_enrollment = Enrollment(
        user_id=current_user.id,
        course_id=enrollment.course_id,
        status=EnrollmentStatus.ACTIVE
    )
    
    # Update course enrollment count
    course.enrolled_count += 1
    
    db.add(new_enrollment)
    db.commit()
    db.refresh(new_enrollment)
    return new_enrollment


@router.get("/enrollments/my", response_model=List[EnrollmentResponse])
async def my_enrollments(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get current user's enrollments"""
    enrollments = db.query(Enrollment).filter(
        Enrollment.user_id == current_user.id
    ).all()
    return enrollments


@router.get("/enrollments/{enrollment_id}", response_model=EnrollmentResponse)
async def get_enrollment(
    enrollment_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get enrollment details"""
    enrollment = db.query(Enrollment).filter(Enrollment.id == enrollment_id).first()
    if not enrollment:
        raise HTTPException(status_code=404, detail="Enrollment not found")
    
    # Check authorization
    if enrollment.user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")
    
    return enrollment


# ==================== PROGRESS TRACKING ====================

@router.post("/progress/lesson", response_model=LessonProgressResponse)
async def update_lesson_progress(
    lesson_id: int,
    progress: LessonProgressUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update lesson progress"""
    # Get enrollment
    lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")
    
    module = db.query(CourseModule).filter(CourseModule.id == lesson.module_id).first()
    enrollment = db.query(Enrollment).filter(
        Enrollment.user_id == current_user.id,
        Enrollment.course_id == module.course_id
    ).first()
    
    if not enrollment:
        raise HTTPException(status_code=400, detail="Not enrolled in this course")
    
    # Get or create progress record
    lesson_progress = db.query(LessonProgress).filter(
        LessonProgress.enrollment_id == enrollment.id,
        LessonProgress.lesson_id == lesson_id
    ).first()
    
    if not lesson_progress:
        lesson_progress = LessonProgress(
            enrollment_id=enrollment.id,
            lesson_id=lesson_id
        )
        db.add(lesson_progress)
    
    # Update progress
    lesson_progress.is_completed = progress.is_completed
    lesson_progress.time_spent_minutes += progress.time_spent_minutes
    lesson_progress.last_position = progress.last_position
    lesson_progress.last_accessed_at = datetime.utcnow()
    
    if progress.is_completed and not lesson_progress.completed_at:
        lesson_progress.completed_at = datetime.utcnow()
    
    db.commit()
    db.refresh(lesson_progress)
    return lesson_progress


# ==================== QUIZ ENDPOINTS ====================

@router.post("/quiz/attempt", response_model=QuizAttemptResponse)
async def submit_quiz_attempt(
    attempt: QuizAttemptSubmit,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Submit a quiz attempt"""
    quiz = db.query(Quiz).filter(Quiz.id == attempt.quiz_id).first()
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")
    
    lesson = db.query(Lesson).filter(Lesson.id == quiz.lesson_id).first()
    module = db.query(CourseModule).filter(CourseModule.id == lesson.module_id).first()
    
    enrollment = db.query(Enrollment).filter(
        Enrollment.user_id == current_user.id,
        Enrollment.course_id == module.course_id
    ).first()
    
    if not enrollment:
        raise HTTPException(status_code=400, detail="Not enrolled in this course")
    
    # Check attempts count
    previous_attempts = db.query(QuizAttempt).filter(
        QuizAttempt.enrollment_id == enrollment.id,
        QuizAttempt.quiz_id == attempt.quiz_id
    ).count()
    
    if previous_attempts >= quiz.attempts_allowed:
        raise HTTPException(status_code=400, detail="Maximum attempts reached")
    
    # Calculate score
    questions = db.query(QuizQuestion).filter(QuizQuestion.quiz_id == quiz.id).all()
    correct = 0
    total = len(questions)
    
    for question in questions:
        user_answer = attempt.answers.get(str(question.id))
        if user_answer == question.correct_answer:
            correct += 1
    
    score = int((correct / total) * 100) if total > 0 else 0
    is_passed = score >= quiz.passing_score
    
    # Create attempt record
    new_attempt = QuizAttempt(
        enrollment_id=enrollment.id,
        quiz_id=attempt.quiz_id,
        attempt_number=previous_attempts + 1,
        score=score,
        is_passed=is_passed,
        answers=attempt.answers,
        submitted_at=datetime.utcnow()
    )
    
    db.add(new_attempt)
    db.commit()
    db.refresh(new_attempt)
    return new_attempt


# ==================== REVIEW ENDPOINTS ====================

@router.post("/reviews", response_model=ReviewResponse, status_code=status.HTTP_201_CREATED)
async def create_review(
    review: ReviewCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a course review"""
    # Check if enrolled
    enrollment = db.query(Enrollment).filter(
        Enrollment.user_id == current_user.id,
        Enrollment.course_id == review.course_id
    ).first()
    
    if not enrollment:
        raise HTTPException(status_code=400, detail="Must be enrolled to review")
    
    # Check if already reviewed
    existing = db.query(CourseReview).filter(
        CourseReview.user_id == current_user.id,
        CourseReview.course_id == review.course_id
    ).first()
    
    if existing:
        raise HTTPException(status_code=400, detail="Already reviewed this course")
    
    new_review = CourseReview(
        **review.dict(),
        user_id=current_user.id
    )
    
    db.add(new_review)
    
    # Update course ratings
    course = db.query(Course).filter(Course.id == review.course_id).first()
    course.rating_count += 1
    total_rating = (course.rating_average * (course.rating_count - 1)) + review.rating
    course.rating_average = total_rating / course.rating_count
    
    db.commit()
    db.refresh(new_review)
    return new_review


@router.get("/courses/{course_id}/reviews", response_model=List[ReviewResponse])
async def get_course_reviews(
    course_id: int,
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db)
):
    """Get course reviews"""
    reviews = db.query(CourseReview).filter(
        CourseReview.course_id == course_id
    ).offset(skip).limit(limit).all()
    return reviews


# ==================== DASHBOARD ENDPOINTS ====================

@router.get("/dashboard/student", response_model=StudentDashboard)
async def student_dashboard(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get student dashboard stats"""
    enrollments = db.query(Enrollment).filter(Enrollment.user_id == current_user.id).all()
    
    return StudentDashboard(
        enrolled_courses=len(enrollments),
        completed_courses=len([e for e in enrollments if e.status == EnrollmentStatus.COMPLETED]),
        in_progress_courses=len([e for e in enrollments if e.status == EnrollmentStatus.ACTIVE]),
        certificates_earned=len([e for e in enrollments if e.certificate_issued]),
        total_learning_hours=sum([e.course.duration_hours or 0 for e in enrollments if e.status == EnrollmentStatus.COMPLETED])
    )


@router.get("/dashboard/instructor", response_model=InstructorDashboard)
async def instructor_dashboard(
    current_user: User = Depends(require_role(["instructor", "admin"])),
    db: Session = Depends(get_db)
):
    """Get instructor dashboard stats"""
    courses = db.query(Course).filter(Course.instructor_id == current_user.id).all()
    
    total_students = sum([c.enrolled_count for c in courses])
    total_reviews = sum([c.rating_count for c in courses])
    avg_rating = sum([c.rating_average * c.rating_count for c in courses]) / total_reviews if total_reviews > 0 else 0.0
    
    return InstructorDashboard(
        total_courses=len(courses),
        published_courses=len([c for c in courses if c.is_published]),
        total_students=total_students,
        total_reviews=total_reviews,
        average_rating=avg_rating
    )

