from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db import IntegrityError
from datetime import timedelta
from students.models import StudentProfile
from recruiters.models import Company
from jobs.models import Job
from applications.models import Application

User = get_user_model()


class ApplicationsModelTests(TestCase):
    def setUp(self):
        self.student_user = User.objects.create_user(
            email='student_app_test@example.com',
            password='Password123!',
            role=User.Role.STUDENT,
        )
        self.student = StudentProfile.objects.create(
            user=self.student_user,
            roll_no='CS2026-APP1',
            full_name='Charlie Brown',
            branch='CSE',
        )

        self.recruiter_user = User.objects.create_user(
            email='recruiter_app_test@company.com',
            password='Password123!',
            role=User.Role.RECRUITER,
            is_approved=True,
        )
        self.company = Company.objects.create(
            user=self.recruiter_user,
            company_name='Alpha Tech',
        )
        self.job = Job.objects.create(
            company=self.company,
            title='Backend Intern',
            description='Django backend developer internship.',
            deadline=timezone.now() + timedelta(days=14),
        )

    def test_create_application(self):
        app = Application.objects.create(
            student=self.student,
            job=self.job,
            status=Application.Status.APPLIED,
            match_score=88.5,
        )
        self.assertEqual(app.student, self.student)
        self.assertEqual(app.job, self.job)
        self.assertEqual(app.status, Application.Status.APPLIED)
        self.assertEqual(app.match_score, 88.5)
        self.assertIsNotNone(app.applied_at)
        self.assertIsNotNone(app.updated_at)

    def test_application_unique_together_constraint(self):
        Application.objects.create(
            student=self.student,
            job=self.job,
            status=Application.Status.APPLIED,
        )
        with self.assertRaises(IntegrityError):
            Application.objects.create(
                student=self.student,
                job=self.job,
                status=Application.Status.APPLIED,
            )
