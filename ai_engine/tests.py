import io
import os
import tempfile
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.urls import reverse

import docx
from students.models import Skill, StudentProfile, Resume
from ai_engine.parsing import extract_text, extract_skills

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
