import io
import os
import tempfile
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.urls import reverse

from datetime import timedelta
from django.utils import timezone
import docx
from students.models import Skill, StudentProfile, Resume
from recruiters.models import Company
from jobs.models import Job
from applications.models import Application
from ai_engine.parsing import extract_text, extract_skills
from ai_engine.scoring import (
    compute_match_score,
    compute_skill_gap,
    recommend_jobs,
    get_courses_for_missing_skills,
)

User = get_user_model()

# Valid minimal PDF 1.4 document containing the text:
# "Experienced in Python, Django, and PostgreSQL"
VALID_PDF_BYTES = (
    b"%PDF-1.4\n"
    b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
    b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
    b"3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R/Resources<</Font<</F1 4 0 R>>>>/Contents 5 0 R>>endobj\n"
    b"4 0 obj<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>endobj\n"
    b"5 0 obj<</Length 68>>stream\n"
    b"BT /F1 12 Tf 100 700 Td (Experienced in Python, Django, and PostgreSQL) Tj ET\n"
    b"endstream\nendobj\n"
    b"xref\n0 6\n"
    b"0000000000 65535 f \n"
    b"0000000009 00000 n \n"
    b"0000000052 00000 n \n"
    b"0000000101 00000 n \n"
    b"0000000212 00000 n \n"
    b"0000000281 00000 n \n"
    b"trailer<</Size 6/Root 1 0 R>>\n"
    b"startxref\n400\n%%EOF\n"
)


def create_test_docx(text: str = "Experienced in Python, Django, and PostgreSQL") -> bytes:
    doc = docx.Document()
    doc.add_paragraph(text)
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


class ParsingEngineTests(TestCase):
    def setUp(self):
        call_command("seed_skills")

    def test_extract_text_from_valid_pdf(self):
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tf:
            tf.write(VALID_PDF_BYTES)
            temp_path = tf.name

        try:
            text = extract_text(temp_path, "pdf")
            self.assertIn("Experienced in Python, Django, and PostgreSQL", text)
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def test_extract_text_from_valid_docx(self):
        docx_bytes = create_test_docx("Experienced in Python, Django, and PostgreSQL")
        with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as tf:
            tf.write(docx_bytes)
            temp_path = tf.name

        try:
            text = extract_text(temp_path, "docx")
            self.assertIn("Experienced in Python, Django, and PostgreSQL", text)
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def test_extract_text_corrupt_pdf_returns_empty_string(self):
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tf:
            tf.write(b"NOT A VALID PDF FILE HEADER OR BYTES")
            temp_path = tf.name

        try:
            text = extract_text(temp_path, "pdf")
            self.assertEqual(text, "")
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def test_extract_text_corrupt_docx_returns_empty_string(self):
        with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as tf:
            tf.write(b"CORRUPT NON-ZIP DOCX DATA")
            temp_path = tf.name

        try:
            text = extract_text(temp_path, "docx")
            self.assertEqual(text, "")
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def test_extract_text_unsupported_extension_returns_empty_string(self):
        text = extract_text("resume.txt", "txt")
        self.assertEqual(text, "")

    def test_extract_skills_matching_and_deduplication(self):
        text = "Skilled in Python, Django, PostgreSQL, and also Python programming."
        skills = extract_skills(text, Skill.objects.all())
        self.assertIn("Python", skills)
        self.assertIn("Django", skills)
        self.assertIn("PostgreSQL", skills)
        # Deduplicated
        self.assertEqual(skills.count("Python"), 1)

    def test_extract_skills_case_insensitivity(self):
        text = "Expertise in python, DJANGO, and postgresql database."
        skills = extract_skills(text, Skill.objects.all())
        self.assertEqual(set(skills), {"Python", "Django", "PostgreSQL"})

    def test_extract_skills_empty_or_none(self):
        self.assertEqual(extract_skills("", Skill.objects.all()), [])
        self.assertEqual(extract_skills("Python and Django", []), [])
        self.assertEqual(extract_skills(None, Skill.objects.all()), [])

    def test_seed_skills_idempotency(self):
        initial_count = Skill.objects.count()
        self.assertGreaterEqual(initial_count, 60)
        # Re-run management command
        call_command("seed_skills")
        self.assertEqual(Skill.objects.count(), initial_count)


class ResumeUploadIntegrationTests(TestCase):
    def setUp(self):
        call_command("seed_skills")
        self.client = Client()
        self.student_user = User.objects.create_user(
            email="student_ai_test@example.com",
            password="Password123!",
            role=User.Role.STUDENT,
        )
        self.student = StudentProfile.objects.create(
            user=self.student_user,
            roll_no="STU-AI-001",
            full_name="Bob AI Student",
            branch="Computer Science",
            year=2026,
            cgpa=8.5,
        )
        # Add a manual skill to student profile prior to resume upload
        self.manual_skill = Skill.objects.get(name="Git")
        self.student.skills.add(self.manual_skill)

    def test_resume_upload_extracts_text_skills_and_preserves_manual_skills(self):
        self.client.login(email="student_ai_test@example.com", password="Password123!")

        uploaded_pdf = SimpleUploadedFile(
            "test_resume.pdf",
            VALID_PDF_BYTES,
            content_type="application/pdf",
        )

        response = self.client.post(reverse("students:resume"), {"file": uploaded_pdf})
        self.assertEqual(response.status_code, 302)

        resume = Resume.objects.filter(student=self.student, is_active=True).first()
        self.assertIsNotNone(resume)
        self.assertIn("Experienced in Python, Django, and PostgreSQL", resume.extracted_text)
        self.assertIn("Python", resume.parsed_skills)
        self.assertIn("Django", resume.parsed_skills)
        self.assertIn("PostgreSQL", resume.parsed_skills)

        # Confirm student.skills has both the newly extracted skills AND the manual skill
        student_skills = set(self.student.skills.values_list("name", flat=True))
        self.assertIn("Git", student_skills, "Manual skill 'Git' must not be removed")
        self.assertIn("Python", student_skills)
        self.assertIn("Django", student_skills)
        self.assertIn("PostgreSQL", student_skills)

    def test_resume_upload_corrupt_file_does_not_crash_view(self):
        self.client.login(email="student_ai_test@example.com", password="Password123!")

        corrupt_pdf = SimpleUploadedFile(
            "corrupt_resume.pdf",
            b"THIS IS CORRUPT NON-PDF BINARY DATA",
            content_type="application/pdf",
        )

        response = self.client.post(reverse("students:resume"), {"file": corrupt_pdf})
        self.assertEqual(response.status_code, 302)

        resume = Resume.objects.filter(student=self.student, is_active=True).first()
        self.assertIsNotNone(resume)
        self.assertEqual(resume.extracted_text, "")
        self.assertEqual(resume.parsed_skills, [])
        # Manual skill is still intact
        self.assertTrue(self.student.skills.filter(name="Git").exists())


class ScoringAndRecommendationEngineTests(TestCase):
    def setUp(self):
        call_command("seed_skills")
        self.client = Client()

        # Create Recruiter and Company
        self.recruiter_user = User.objects.create_user(
            email="recruiter_scoring@example.com",
            password="Password123!",
            role=User.Role.RECRUITER,
            is_approved=True,
        )
        self.company = Company.objects.create(
            user=self.recruiter_user,
            company_name="TechWave Solutions",
            description="Enterprise Cloud & AI Solutions",
        )

        # Create Student A (Tech focus: Python, Django, PostgreSQL)
        self.user_a = User.objects.create_user(
            email="candidate_a@example.com",
            password="Password123!",
            role=User.Role.STUDENT,
        )
        self.student_a = StudentProfile.objects.create(
            user=self.user_a,
            roll_no="STU-SCORE-001",
            full_name="Alice Engineer",
            branch="Computer Science",
            year=2026,
            cgpa=9.0,
        )
        self.skill_python = Skill.objects.get(name="Python")
        self.skill_django = Skill.objects.get(name="Django")
        self.skill_postgres = Skill.objects.get(name="PostgreSQL")
        self.student_a.skills.add(self.skill_python, self.skill_django, self.skill_postgres)
        Resume.objects.create(
            student=self.student_a,
            file="resumes/dummy_a.pdf",
            extracted_text="Senior Backend Developer with extensive Python and Django microservices experience. Master of PostgreSQL database design, query optimization, and REST APIs.",
            parsed_skills=["Python", "Django", "PostgreSQL"],
            is_active=True,
        )

        # Create Student B (Unrelated focus: UI/Design)
        self.user_b = User.objects.create_user(
            email="candidate_b@example.com",
            password="Password123!",
            role=User.Role.STUDENT,
        )
        self.student_b = StudentProfile.objects.create(
            user=self.user_b,
            roll_no="STU-SCORE-002",
            full_name="Bob Designer",
            branch="Mechanical",
            year=2026,
            cgpa=8.0,
        )
        Resume.objects.create(
            student=self.student_b,
            file="resumes/dummy_b.pdf",
            extracted_text="Creative UI/UX Designer specialized in Figma, wireframing, color theory, and user journey mapping for mobile applications.",
            parsed_skills=[],
            is_active=True,
        )

        # Create Target Job: Python Backend
        self.target_job = Job.objects.create(
            company=self.company,
            title="Python Django Backend Developer",
            description="We are seeking an experienced Python Django Backend Developer to build scalable APIs and manage PostgreSQL databases.",
            min_cgpa=7.0,
            allowed_branches=["Computer Science", "Information Technology"],
            max_backlogs=0,
            package_lpa=12.5,
            location="Bangalore",
            deadline=timezone.now() + timedelta(days=20),
            status=Job.Status.OPEN,
        )
        self.target_job.required_skills.add(self.skill_python, self.skill_django, self.skill_postgres)

    def test_matching_student_scores_higher_than_non_matching(self):
        # Student A matches both required skills and resume text
        score_a = compute_match_score(
            student_skills=self.student_a.skills.all(),
            job_required_skills=self.target_job.required_skills.all(),
            student_resume_text=self.student_a.resumes.first().extracted_text,
            job_description=self.target_job.description,
        )

        # Student B has no skill overlap and unrelated resume text
        score_b = compute_match_score(
            student_skills=self.student_b.skills.all(),
            job_required_skills=self.target_job.required_skills.all(),
            student_resume_text=self.student_b.resumes.first().extracted_text,
            job_description=self.target_job.description,
        )

        self.assertGreater(score_a, score_b)
        self.assertGreaterEqual(score_a, 70.0, "Candidate with exact skill match should score >= 70%")
        self.assertLess(score_b, 30.0, "Candidate with zero skill match should score < 30%")

    def test_skill_gap_separates_matched_and_missing_correctly(self):
        # Student A has Python, Django, PostgreSQL
        # Suppose a job requires Python, Kubernetes, Docker, and AWS
        skill_k8s = Skill.objects.get(name="Kubernetes")
        skill_docker = Skill.objects.get(name="Docker")
        skill_aws = Skill.objects.get(name="AWS")

        job_reqs = [self.skill_python, skill_k8s, skill_docker, skill_aws]
        gap = compute_skill_gap(self.student_a.skills.all(), job_reqs)

        self.assertEqual(gap["matched"], ["Python"])
        self.assertEqual(set(gap["missing"]), {"Kubernetes", "Docker", "AWS"})

    def test_scoring_edge_cases_do_not_crash(self):
        # 1. Both skills and texts empty
        score_empty = compute_match_score([], [], "", "")
        self.assertEqual(score_empty, 0.0)

        # 2. Zero student skills, non-empty job
        score_no_student_skills = compute_match_score([], [self.skill_python], "", "Python job description")
        self.assertIsInstance(score_no_student_skills, float)
        self.assertGreaterEqual(score_no_student_skills, 0.0)

        # 3. Zero required skills, non-empty student
        score_no_reqs = compute_match_score([self.skill_python], [], "Experienced Python developer", "Job description")
        self.assertIsInstance(score_no_reqs, float)
        self.assertGreaterEqual(score_no_reqs, 0.0)

        # 4. Empty resume text with valid skills
        score_no_resume = compute_match_score([self.skill_python, self.skill_django], [self.skill_python], "", "Python role")
        self.assertEqual(score_no_resume, 100.0)

        # 5. Empty job description with valid skills
        score_no_jd = compute_match_score([self.skill_python], [self.skill_python], "Python developer", "")
        self.assertEqual(score_no_jd, 100.0)

        # 6. None inputs
        score_none = compute_match_score(None, None, None, None)
        self.assertEqual(score_none, 0.0)

    def test_recommend_jobs_excludes_applied_closed_expired(self):
        # Job 1 is target_job: OPEN, future deadline, unapplied -> should be recommended

        # Job 2: OPEN, future deadline, but applied by student_a
        job_applied = Job.objects.create(
            company=self.company,
            title="Full Stack Engineer",
            description="React and Django",
            deadline=timezone.now() + timedelta(days=10),
            status=Job.Status.OPEN,
        )
        Application.objects.create(
            student=self.student_a,
            job=job_applied,
            status=Application.Status.APPLIED,
            match_score=85.0,
        )

        # Job 3: CLOSED status
        job_closed = Job.objects.create(
            company=self.company,
            title="Closed Job Role",
            description="Closed job",
            deadline=timezone.now() + timedelta(days=10),
            status=Job.Status.CLOSED,
        )

        # Job 4: Expired deadline
        job_expired = Job.objects.create(
            company=self.company,
            title="Expired Job Role",
            description="Expired job",
            deadline=timezone.now() - timedelta(days=2),
            status=Job.Status.OPEN,
        )

        recommended = recommend_jobs(self.student_a, top_n=10)
        rec_job_ids = [job.id for job, _ in recommended]

        self.assertIn(self.target_job.id, rec_job_ids)
        self.assertNotIn(job_applied.id, rec_job_ids, "Applied jobs must be excluded")
        self.assertNotIn(job_closed.id, rec_job_ids, "Closed jobs must be excluded")
        self.assertNotIn(job_expired.id, rec_job_ids, "Expired jobs must be excluded")

    def test_score_is_saved_on_application_and_not_silently_null(self):
        self.client.login(email="candidate_a@example.com", password="Password123!")

        apply_url = reverse("students:apply_job", kwargs={"pk": self.target_job.pk})
        response = self.client.post(apply_url)
        self.assertEqual(response.status_code, 302)

        application = Application.objects.filter(student=self.student_a, job=self.target_job).first()
        self.assertIsNotNone(application)
        self.assertIsNotNone(application.match_score)
        self.assertIsInstance(application.match_score, float)
        self.assertGreaterEqual(application.match_score, 70.0)

    def test_student_with_zero_resumes_does_not_crash_views(self):
        # Create student with zero resumes
        user_no_resume = User.objects.create_user(
            email="candidate_no_resume@example.com",
            password="Password123!",
            role=User.Role.STUDENT,
        )
        student_no_resume = StudentProfile.objects.create(
            user=user_no_resume,
            roll_no="STU-NO-RESUME",
            full_name="Charlie NoResume",
            branch="Computer Science",
            year=2026,
            cgpa=8.2,
        )

        self.client.login(email="candidate_no_resume@example.com", password="Password123!")

        # 1. Dashboard View
        dash_res = self.client.get(reverse("students:dashboard"))
        self.assertEqual(dash_res.status_code, 200)

        # 2. Job Detail View
        detail_res = self.client.get(reverse("students:job_detail", kwargs={"pk": self.target_job.pk}))
        self.assertEqual(detail_res.status_code, 200)
        self.assertIn("match_score", detail_res.context)

        # 3. Skill Gap View
        gap_res = self.client.get(reverse("students:skill_gap", kwargs={"job_id": self.target_job.pk}))
        self.assertEqual(gap_res.status_code, 200)

    def test_course_recommendations_and_recruiter_view(self):
        # Check course recommendations
        courses = get_courses_for_missing_skills(["Python", "Kubernetes", "UncommonCustomSkill"])
        self.assertEqual(len(courses), 3)
        python_course = next(c for c in courses if c["skill"] == "Python")
        self.assertTrue(len(python_course["courses"]) >= 1)

        # Recruiter applicants list fallback testing
        app_with_score = Application.objects.create(
            student=self.student_a,
            job=self.target_job,
            status=Application.Status.APPLIED,
            match_score=92.0,
        )
        app_null_score = Application.objects.create(
            student=self.student_b,
            job=self.target_job,
            status=Application.Status.APPLIED,
            match_score=None,
        )

        self.client.login(email="recruiter_scoring@example.com", password="Password123!")
        applicants_url = reverse("recruiters:job_applicants", kwargs={"pk": self.target_job.pk})
        response = self.client.get(applicants_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "92% Fit")
        self.assertContains(response, "--")
