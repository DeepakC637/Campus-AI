from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from students.models import Skill, StudentProfile, Resume

User = get_user_model()


class StudentsModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='student_model_test@example.com',
            password='Password123!',
            role=User.Role.STUDENT,
        )

    def test_create_skill(self):
        skill = Skill.objects.create(name='Python', category='Programming')
        self.assertEqual(str(skill), 'Python')
        self.assertEqual(skill.category, 'Programming')

    def test_create_student_profile(self):
        skill1 = Skill.objects.create(name='Django', category='Framework')
        profile = StudentProfile.objects.create(
            user=self.user,
            roll_no='CS2026-001',
            full_name='Alice Student',
            branch='Computer Science',
            year=2026,
            cgpa=8.5,
            backlogs=0,
            phone='9876543210',
            is_verified=True,
            placement_status='UNPLACED',
        )
        profile.skills.add(skill1)

        self.assertEqual(profile.user, self.user)
        self.assertEqual(profile.roll_no, 'CS2026-001')
        self.assertEqual(profile.full_name, 'Alice Student')
        self.assertEqual(profile.branch, 'Computer Science')
        self.assertEqual(profile.year, 2026)
        self.assertEqual(profile.graduation_year, 2026)
        self.assertEqual(profile.cgpa, 8.5)
        self.assertEqual(profile.backlogs, 0)
        self.assertEqual(profile.phone, '9876543210')
        self.assertTrue(profile.is_verified)
        self.assertEqual(profile.placement_status, 'UNPLACED')
        self.assertIn(skill1, profile.skills.all())

    def test_create_resume(self):
        profile = StudentProfile.objects.create(
            user=self.user,
            roll_no='CS2026-002',
            full_name='Bob Student',
            branch='IT',
        )
        fake_file = SimpleUploadedFile("resume.pdf", b"%PDF-1.4 fake pdf content", content_type="application/pdf")
        resume = Resume.objects.create(
            student=profile,
            file=fake_file,
            extracted_text="Sample extracted resume text",
            parsed_skills=["Python", "Django"],
            is_active=True,
        )
        self.assertEqual(resume.student, profile)
        self.assertTrue(resume.is_active)
        self.assertIn("Python", resume.parsed_skills)
        self.assertIsNotNone(resume.uploaded_at)
