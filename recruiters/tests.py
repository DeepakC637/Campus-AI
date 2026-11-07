from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta

from recruiters.models import Company, set_recruiter_approval
from students.models import StudentProfile
from jobs.models import Job
from applications.models import Application
from interviews.models import Interview

User = get_user_model()


class RecruitersModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='recruiter_test@techcorp.com',
            password='Password123!',
            role=User.Role.RECRUITER,
            is_approved=True,
        )

    def test_create_company(self):
        company = Company.objects.create(
            user=self.user,
            company_name='TechCorp Global',
            description='Leading enterprise cloud solutions provider.',
            website='https://techcorp.example.com',
            industry='Software & Cloud',
            contact_person='Jane Recruiter',
        )
        self.assertEqual(company.user, self.user)
        self.assertEqual(company.company_name, 'TechCorp Global')
        self.assertEqual(str(company), 'TechCorp Global')
        self.assertEqual(company.industry, 'Software & Cloud')
        self.assertEqual(company.contact_person, 'Jane Recruiter')


class RecruiterCrossIsolationAndSecurityTests(TestCase):
    def setUp(self):
        # Recruiter A
        self.user_a = User.objects.create_user(
            email='recruiter_a@alpha.com',
            password='Password123!',
            role=User.Role.RECRUITER,
            is_approved=True,
        )
        self.company_a = Company.objects.create(
            user=self.user_a,
            company_name='Alpha Corp',
            is_approved=True,
        )
        self.job_a = Job.objects.create(
            company=self.company_a,
            title='Backend Engineer A',
            description='Build backend microservices',
            package_lpa=12.0,
            location='Bangalore',
            deadline=timezone.now().date() + timedelta(days=15),
            status=Job.Status.OPEN,
        )

        # Recruiter B
        self.user_b = User.objects.create_user(
            email='recruiter_b@beta.com',
            password='Password123!',
            role=User.Role.RECRUITER,
            is_approved=True,
        )
        self.company_b = Company.objects.create(
            user=self.user_b,
            company_name='Beta Industries',
            is_approved=True,
        )
        self.job_b = Job.objects.create(
            company=self.company_b,
            title='Frontend Engineer B',
            description='Build web dashboards',
            package_lpa=10.0,
            location='Hyderabad',
            deadline=timezone.now().date() + timedelta(days=15),
            status=Job.Status.OPEN,
        )

        # Student & Applications
        self.student_user = User.objects.create_user(
            email='student_sec@college.edu',
            password='Password123!',
            role=User.Role.STUDENT,
            is_approved=True,
        )
        self.student = StudentProfile.objects.create(
            user=self.student_user,
            roll_no='CS2026SEC01',
            full_name='Security Student',
            branch='CSE',
            year=4,
            cgpa=8.5,
            backlogs=0,
            is_verified=True,
        )
        self.app_a = Application.objects.create(
            student=self.student,
            job=self.job_a,
            status=Application.Status.APPLIED,
        )
        self.app_b = Application.objects.create(
            student=self.student,
            job=self.job_b,
            status=Application.Status.SHORTLISTED,
        )

        self.client_a = Client()
        self.client_a.force_login(self.user_a)

    def test_recruiter_jobs_list_only_shows_own_jobs(self):
        response = self.client_a.get(reverse('recruiters:jobs'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Backend Engineer A')
        self.assertNotContains(response, 'Frontend Engineer B')

    def test_cross_recruiter_cannot_edit_other_company_job(self):
        # Recruiter A attempts to edit Job B
        url = reverse('recruiters:job_edit', kwargs={'pk': self.job_b.id})
        response = self.client_a.get(url)
        self.assertEqual(response.status_code, 403)

        post_response = self.client_a.post(url, {
            'title': 'Hacked Job Title',
            'description': 'Malicious update',
            'package_lpa': 99.0,
            'location': 'Nowhere',
            'status': Job.Status.OPEN,
        })
        self.assertEqual(post_response.status_code, 403)
        self.job_b.refresh_from_db()
        self.assertEqual(self.job_b.title, 'Frontend Engineer B')

    def test_cross_recruiter_cannot_view_other_company_applicants(self):
        # Recruiter A attempts to view applicants for Job B
        url = reverse('recruiters:job_applicants', kwargs={'pk': self.job_b.id})
        response = self.client_a.get(url)
        self.assertEqual(response.status_code, 403)

    def test_cross_recruiter_cannot_update_other_company_applicant_status(self):
        # Recruiter A attempts to change status of app_b (which is for Job B)
        url = reverse('recruiters:update_application_status', kwargs={'pk': self.app_b.id})
        response = self.client_a.post(url, {'status': Application.Status.REJECTED})
        self.assertEqual(response.status_code, 403)
        self.app_b.refresh_from_db()
        self.assertEqual(self.app_b.status, Application.Status.SHORTLISTED)

    def test_cross_recruiter_cannot_schedule_interview_for_other_company_application(self):
        # Recruiter A attempts to schedule interview for app_b
        url = reverse('recruiters:schedule_interview', kwargs={'pk': self.app_b.id})
        response = self.client_a.get(url)
        self.assertEqual(response.status_code, 403)


class RecruiterApplicantAndInterviewLogicTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='recruiter_flow@company.com',
            password='Password123!',
            role=User.Role.RECRUITER,
            is_approved=True,
        )
        self.company = Company.objects.create(
            user=self.user,
            company_name='Flow Tech',
            is_approved=True,
        )
        self.job = Job.objects.create(
            company=self.company,
            title='Software Developer',
            package_lpa=8.0,
            location='Pune',
            deadline=timezone.now().date() + timedelta(days=10),
            status=Job.Status.OPEN,
        )
        self.student_user = User.objects.create_user(
            email='candidate@college.edu',
            password='Password123!',
            role=User.Role.STUDENT,
            is_approved=True,
        )
        self.student = StudentProfile.objects.create(
            user=self.student_user,
            roll_no='CS2026FLOW01',
            full_name='Flow Candidate',
            branch='IT',
            year=4,
            cgpa=9.0,
            backlogs=0,
            is_verified=True,
        )
        self.application = Application.objects.create(
            student=self.student,
            job=self.job,
            status=Application.Status.APPLIED,
        )
        self.client = Client()
        self.client.force_login(self.user)

    def test_recruiter_can_update_applicant_status(self):
        url = reverse('recruiters:update_application_status', kwargs={'pk': self.application.id})
        response = self.client.post(url, {'status': Application.Status.SHORTLISTED})
        self.assertEqual(response.status_code, 302)
        self.application.refresh_from_db()
        self.assertEqual(self.application.status, Application.Status.SHORTLISTED)

    def test_recruiter_cannot_set_status_to_withdrawn(self):
        url = reverse('recruiters:update_application_status', kwargs={'pk': self.application.id})
        response = self.client.post(url, {'status': Application.Status.WITHDRAWN})
        self.assertEqual(response.status_code, 400)
        self.application.refresh_from_db()
        self.assertEqual(self.application.status, Application.Status.APPLIED)

    def test_interview_scheduling_status_gate_blocks_unshortlisted_candidates(self):
        # Application is currently in 'Applied' status
        url = reverse('recruiters:schedule_interview', kwargs={'pk': self.application.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 400)

        post_data = {
            'round_type': 'Technical Round 1',
            'mode': 'Online',
            'scheduled_at': '2026-12-01 10:00:00',
            'link_or_venue': 'https://meet.google.com/abc-def-xyz',
        }
        post_response = self.client.post(url, post_data)
        self.assertEqual(post_response.status_code, 400)
        self.assertEqual(Interview.objects.count(), 0)

    def test_interview_scheduling_succeeds_when_shortlisted(self):
        self.application.status = Application.Status.SHORTLISTED
        self.application.save(update_fields=['status'])

        url = reverse('recruiters:schedule_interview', kwargs={'pk': self.application.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        post_data = {
            'round_type': 'Technical Round 1',
            'mode': 'Online',
            'scheduled_at': '2026-12-01 10:00:00',
            'link_or_venue': 'https://meet.google.com/abc-def-xyz',
            'feedback': 'Please be prepared for data structures & algorithms.',
        }
        post_response = self.client.post(url, post_data)
        self.assertEqual(post_response.status_code, 302)

        self.assertEqual(Interview.objects.count(), 1)
        interview = Interview.objects.first()
        self.assertEqual(interview.application, self.application)
        self.assertEqual(interview.round_type, 'Technical Round 1')
        self.assertEqual(interview.mode, 'Online')

        # Status auto-advances to Interview
        self.application.refresh_from_db()
        self.assertEqual(self.application.status, Application.Status.INTERVIEW)

    def test_unapproved_recruiter_is_blocked_from_recruiter_portal(self):
        # Revoke approval using single write path
        set_recruiter_approval(self.company, False)
        response = self.client.get(reverse('recruiters:dashboard'))
        # @role_required raises PermissionDenied (403) for unapproved recruiter
        self.assertEqual(response.status_code, 403)
