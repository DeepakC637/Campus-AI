from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from students.models import StudentProfile
from recruiters.models import Company
from jobs.models import Job
from applications.models import Application
from interviews.models import Interview

User = get_user_model()


class InterviewsModelTests(TestCase):
    def setUp(self):
        self.student_user = User.objects.create_user(
            email='student_int_test@example.com',
            password='Password123!',
            role=User.Role.STUDENT,
        )
        self.student = StudentProfile.objects.create(
            user=self.student_user,
            roll_no='CS2026-INT1',
            full_name='Diana Prince',
            branch='CSE',
        )

        self.recruiter_user = User.objects.create_user(
            email='recruiter_int_test@company.com',
            password='Password123!',
            role=User.Role.RECRUITER,
            is_approved=True,
        )
        self.company = Company.objects.create(
            user=self.recruiter_user,
            company_name='Apex Corp',
        )
        self.job = Job.objects.create(
            company=self.company,
            title='Software Engineer',
            description='Core developer role.',
            deadline=timezone.now() + timedelta(days=20),
        )
        self.application = Application.objects.create(
            student=self.student,
            job=self.job,
            status=Application.Status.INTERVIEW,
        )

    def test_create_interview(self):
        interview_time = timezone.now() + timedelta(days=2)
        interview = Interview.objects.create(
            application=self.application,
            round_type='Technical Round 1',
            mode=Interview.Mode.ONLINE,
            scheduled_at=interview_time,
            link_or_venue='https://meet.google.com/xyz-abc-def',
            result='Passed',
            feedback='Strong DSA and system fundamentals.',
            status=Interview.Status.SCHEDULED,
        )

        self.assertEqual(interview.application, self.application)
        self.assertEqual(interview.round_type, 'Technical Round 1')
        self.assertEqual(interview.mode, Interview.Mode.ONLINE)
        self.assertEqual(interview.scheduled_at, interview_time)
        self.assertEqual(interview.scheduled_time, interview_time)
        self.assertEqual(interview.link_or_venue, 'https://meet.google.com/xyz-abc-def')
        self.assertEqual(interview.link_or_location, 'https://meet.google.com/xyz-abc-def')
        self.assertEqual(interview.status, Interview.Status.SCHEDULED)
