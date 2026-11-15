"""
ai_engine/scoring.py

PlacementHub AI Engine: Compatibility Scoring, Skill Gap Analysis,
and Intelligent Job Recommendations.

Implements TF-IDF cosine similarity combined with skill-overlap ratio
to compute candidate-job match scores, identifies missing competencies,
and provides curated upskilling pathways.
"""

import logging
from typing import Any, Dict, Iterable, List, Optional, Tuple
from django.utils import timezone
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

logger = logging.getLogger(__name__)

# Static curated educational recommendations for ~20 common technical skills
SKILL_COURSES: Dict[str, List[Dict[str, str]]] = {
    "Python": [
        {"title": "Programming for Everybody (Python)", "platform": "Coursera / Univ. of Michigan", "url": "https://www.coursera.org/learn/python"},
        {"title": "Complete Python Developer", "platform": "Udemy", "url": "https://www.udemy.com/course/complete-python-developer-zero-to-mastery/"},
    ],
    "Django": [
        {"title": "Django for Everybody Specialization", "platform": "Coursera / Univ. of Michigan", "url": "https://www.coursera.org/specializations/django"},
        {"title": "Python and Django Full Stack Bootcamp", "platform": "Udemy", "url": "https://www.udemy.com/course/python-and-django-full-stack-web-developer-bootcamp/"},
    ],
    "PostgreSQL": [
        {"title": "PostgreSQL for Everybody", "platform": "Coursera / Univ. of Michigan", "url": "https://www.coursera.org/specializations/postgresql-for-everybody"},
        {"title": "The Complete SQL Bootcamp (PostgreSQL)", "platform": "Udemy", "url": "https://www.udemy.com/course/the-complete-sql-bootcamp/"},
    ],
    "SQL": [
        {"title": "SQL for Data Science", "platform": "Coursera / UC Davis", "url": "https://www.coursera.org/learn/sql-for-data-science"},
        {"title": "SQL - The Complete Developer's Guide", "platform": "Udemy", "url": "https://www.udemy.com/course/sql-and-postgresql/"},
    ],
    "React": [
        {"title": "Developing Front-End Apps with React", "platform": "Coursera / IBM", "url": "https://www.coursera.org/learn/developing-frontend-apps-with-react"},
        {"title": "React - The Complete Guide (incl. Redux)", "platform": "Udemy", "url": "https://www.udemy.com/course/react-the-complete-guide-incl-redux/"},
    ],
    "JavaScript": [
        {"title": "JavaScript Basics & Modern ES6+", "platform": "Coursera / UC Davis", "url": "https://www.coursera.org/learn/javascript-basics"},
        {"title": "The Complete JavaScript Course 2024", "platform": "Udemy", "url": "https://www.udemy.com/course/the-complete-javascript-course/"},
    ],
    "TypeScript": [
        {"title": "Understanding TypeScript", "platform": "Udemy", "url": "https://www.udemy.com/course/understanding-typescript/"},
    ],
    "Java": [
        {"title": "Java Programming: Solving Problems with Software", "platform": "Coursera / Duke", "url": "https://www.coursera.org/learn/java-programming"},
    ],
    "Spring Boot": [
        {"title": "Building Scalable Java Microservices with Spring Boot", "platform": "Coursera / Google Cloud", "url": "https://www.coursera.org/learn/google-cloud-java-spring"},
        {"title": "Spring Boot 3 & Spring Framework 6 Masterclass", "platform": "Udemy", "url": "https://www.udemy.com/course/spring-hibernate-tutorial/"},
    ],
    "Docker": [
        {"title": "Introduction to Containers with Docker & Kubernetes", "platform": "Coursera / IBM", "url": "https://www.coursera.org/learn/ibm-containers-docker-kubernetes-openshift"},
        {"title": "Docker & Kubernetes: The Practical Guide", "platform": "Udemy", "url": "https://www.udemy.com/course/docker-kubernetes-the-practical-guide/"},
    ],
    "Kubernetes": [
        {"title": "Architecting with Google Kubernetes Engine", "platform": "Coursera / Google Cloud", "url": "https://www.coursera.org/specializations/architecting-google-kubernetes-engine"},
    ],
    "AWS": [
        {"title": "AWS Cloud Practitioner Essentials", "platform": "Coursera / AWS", "url": "https://www.coursera.org/learn/aws-cloud-practitioner-essentials"},
        {"title": "AWS Certified Solutions Architect Associate", "platform": "Udemy", "url": "https://www.udemy.com/course/aws-certified-solutions-architect-associate-saa-c03/"},
    ],
    "Git": [
        {"title": "Version Control with Git", "platform": "Coursera / Atlassian", "url": "https://www.coursera.org/learn/version-control-with-git"},
        {"title": "Git & GitHub - The Practical Guide", "platform": "Udemy", "url": "https://www.udemy.com/course/git-github-practical-guide/"},
    ],
    "Machine Learning": [
        {"title": "Machine Learning Specialization", "platform": "Coursera / DeepLearning.AI & Stanford", "url": "https://www.coursera.org/specializations/machine-learning-introduction"},
    ],
    "Deep Learning": [
        {"title": "Deep Learning Specialization", "platform": "Coursera / DeepLearning.AI", "url": "https://www.coursera.org/specializations/deep-learning"},
    ],
    "Data Structures": [
        {"title": "Data Structures and Algorithms Specialization", "platform": "Coursera / UC San Diego", "url": "https://www.coursera.org/specializations/data-structures-algorithms"},
    ],
    "REST APIs": [
        {"title": "API Design and Fundamentals of Google Cloud's Apigee Platform", "platform": "Coursera / Google Cloud", "url": "https://www.coursera.org/learn/api-design"},
    ],
    "Linux": [
        {"title": "Hands-on Introduction to Linux Commands and Shell Scripting", "platform": "Coursera / IBM", "url": "https://www.coursera.org/learn/hands-on-introduction-to-linux-commands-and-shell-scripting"},
    ],
    "CI/CD": [
        {"title": "Continuous Integration and Continuous Delivery (CI/CD)", "platform": "Coursera / IBM", "url": "https://www.coursera.org/learn/continuous-integration-and-continuous-delivery-ci-cd"},
    ],
    "Node.js": [
        {"title": "Developing Backend Apps with Node.js and Express", "platform": "Coursera / IBM", "url": "https://www.coursera.org/learn/developing-backend-apps-with-nodejs-and-express"},
    ],
}


def compute_match_score(
    student_skills: Optional[Iterable[Any]],
    job_required_skills: Optional[Iterable[Any]],
    student_resume_text: Optional[str],
    job_description: Optional[str],
) -> float:
    """
    Calculate a candidate-job compatibility score between 0.0 and 100.0.

    Weighted combination:
    - 60% Skill-overlap ratio (matched skills / required skills)
    - 40% TF-IDF Cosine Similarity between resume text and job description

    Safely handles edge cases:
    - Empty resume text / job description
    - Zero required skills
    - Zero student skills
    - All-empty inputs (returns 0.0)
    Result is always clipped to [0.0, 100.0].
    """
    s_skills = {
        getattr(s, "name", str(s)).strip().lower()
        for s in (student_skills or [])
        if getattr(s, "name", str(s)).strip()
    }
    j_skills = {
        getattr(s, "name", str(s)).strip().lower()
        for s in (job_required_skills or [])
        if getattr(s, "name", str(s)).strip()
    }

    s_text = (student_resume_text or "").strip()
    j_text = (job_description or "").strip()

    # 1. Skill Overlap Ratio
    has_skill_comp = len(j_skills) > 0
    if has_skill_comp:
        overlap = len(s_skills & j_skills)
        skill_ratio = overlap / len(j_skills)
    else:
        skill_ratio = 0.0

    # 2. TF-IDF Cosine Similarity
    text_sim = 0.0
    has_text_comp = False
    if s_text and j_text:
        try:
            vec = TfidfVectorizer(stop_words="english")
            tfidf_matrix = vec.fit_transform([s_text, j_text])
            sim = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
            text_sim = float(sim)
            has_text_comp = True
        except Exception as exc:
            logger.debug("TF-IDF vectorizer fallback: %s", exc)
            text_sim = 0.0
            has_text_comp = False

    # 3. Weighted Combination
    if has_skill_comp and has_text_comp:
        combined = (0.6 * skill_ratio) + (0.4 * text_sim)
    elif has_skill_comp:
        combined = skill_ratio
    elif has_text_comp:
        combined = text_sim
    else:
        combined = 0.0

    score = round(combined * 100.0, 1)
    return float(max(0.0, min(100.0, score)))


def compute_skill_gap(
    student_skills: Optional[Iterable[Any]],
    job_required_skills: Optional[Iterable[Any]],
) -> Dict[str, List[str]]:
    """
    Compare student skills against job required skills.

    Returns:
        dict with:
            "matched": list of skill names present in both
            "missing": list of required skill names missing from student
    """
    s_names_lower = {
        getattr(s, "name", str(s)).strip().lower()
        for s in (student_skills or [])
        if getattr(s, "name", str(s)).strip()
    }

    matched: List[str] = []
    missing: List[str] = []

    for item in (job_required_skills or []):
        name = getattr(item, "name", str(item)).strip()
        if not name:
            continue
        if name.lower() in s_names_lower:
            if name not in matched:
                matched.append(name)
        else:
            if name not in missing:
                missing.append(name)

    return {"matched": matched, "missing": missing}


def get_courses_for_missing_skills(missing_skills: Iterable[str]) -> List[Dict[str, Any]]:
    """
    Given an iterable of missing skill names, map each to recommended learning courses.
    """
    recommendations: List[Dict[str, Any]] = []
    for skill in missing_skills:
        skill_name = getattr(skill, "name", str(skill)).strip()
        if not skill_name:
            continue

        courses = None
        for k, v in SKILL_COURSES.items():
            if k.lower() == skill_name.lower():
                courses = v
                break

        if not courses:
            courses = [
                {
                    "title": f"Mastering {skill_name}: Concepts and Best Practices",
                    "platform": "Online Learning / Docs",
                    "url": f"https://www.google.com/search?q={skill_name}+programming+course+tutorial",
                }
            ]

        recommendations.append({
            "skill": skill_name,
            "courses": courses,
        })
    return recommendations


def recommend_jobs(student: Any, top_n: int = 5) -> List[Tuple[Any, float]]:
    """
    Score and rank OPEN jobs for which deadline >= today, excluding already-applied jobs.

    Reuses the student's already-stored Resume.extracted_text — does NOT re-parse
    the file from disk per job.

    Returns:
        list of (job, score) tuples, ordered descending by match score.
    """
    from jobs.models import Job

    # Retrieve active resume text (already stored in DB, no disk I/O)
    active_resume = student.resumes.filter(is_active=True).first()
    student_resume_text = active_resume.extracted_text if active_resume else ""
    student_skills = list(student.skills.all())

    # Exclude jobs already applied to
    applied_job_ids = set(student.applications.values_list("job_id", flat=True))

    jobs_qs = (
        Job.objects.filter(
            status=Job.Status.OPEN,
            deadline__gte=timezone.now(),
        )
        .exclude(id__in=applied_job_ids)
        .select_related("company")
        .prefetch_related("required_skills")
    )

    scored_jobs: List[Tuple[Any, float]] = []
    for job in jobs_qs:
        job_skills = list(job.required_skills.all())
        score = compute_match_score(
            student_skills=student_skills,
            job_required_skills=job_skills,
            student_resume_text=student_resume_text,
            job_description=job.description,
        )
        scored_jobs.append((job, score))

    # Sort descending by match score, secondary sort by deadline
    scored_jobs.sort(key=lambda pair: (-pair[1], pair[0].deadline))
    return scored_jobs[:top_n]
