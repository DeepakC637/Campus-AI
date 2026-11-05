from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta, date
from students.models import StudentProfile
from recruiters.models import Company
from jobs.models import Job
from applications.models import Application
from placements.models import PlacementRecord

User = get_user_model()


class PlacementsModelTests(TestCase):
    def setUp(self):
        self.student_user = User.objects.create_user(
            email='student_pl_test@example.com',
            password='Password123!',
            role=User.Role.STUDENT,
        )
        self.student = StudentProfile.objects.create(
            user=self.student_user,
            roll_no='CS2026-PL1',
            full_name='Edward Cullen',
            branch='CSE',
        )

        self.recruiter_user = User.objects.create_user(
            email='recruiter_pl_test@company.com',
            password='Password123!',
            role=User.Role.RECRUITER,
            is_approved=True,
        )
        self.company = Company.objects.create(
            user=self.recruiter_user,
            company_name='OmniTech Inc',
        )
        self.job = Job.objects.create(
            company=self.company,
            title='Graduate Engineer Trainee',
            description='Full-time campus hire role.',
            deadline=timezone.now() + timedelta(days=10),
        )
        self.application = Application.objects.create(
            student=self.student,
            job=self.job,
            status=Application.Status.SELECTED,
        )

    def test_create_placement_record(self):
        record = PlacementRecord.objects.create(
            student=self.student,
            company=self.company,
            application=self.application,
            package_lpa=16.0,
            offer_date=date(2026, 11, 1),
            is_final=True,
        )

        self.assertEqual(record.student, self.student)
        self.assertEqual(record.company, self.company)
        self.assertEqual(record.application, self.application)
        self.assertEqual(record.package_lpa, 16.0)
        self.assertEqual(record.salary_package, 16.0)
        self.assertEqual(record.offer_date, date(2026, 11, 1))
        self.assertEqual(record.join_date, date(2026, 11, 1))
        self.assertTrue(record.is_final)
