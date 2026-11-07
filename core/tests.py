from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta

from students.models import StudentProfile
from recruiters.models import Company
from jobs.models import Job
from applications.models import Application
from placements.models import PlacementRecord
from core.forms import PlacementRecordCreateForm

User = get_user_model()


class AdminAccessControlTests(TestCase):
    def setUp(self):
        self.admin_user = User.objects.create_user(
            email='admin@placementhub.edu',
            password='Password123!',
            role=User.Role.ADMIN,
            is_approved=True,
        )
        self.student_user = User.objects.create_user(
            email='student@placementhub.edu',
            password='Password123!',
            role=User.Role.STUDENT,
            is_approved=True,
        )
        self.recruiter_user = User.objects.create_user(
            email='recruiter@corp.com',
            password='Password123!',
            role=User.Role.RECRUITER,
            is_approved=True,
        )

        self.endpoints = [
            reverse('core:admin_dashboard'),
            reverse('core:admin_students'),
            reverse('core:admin_recruiters'),
            reverse('core:admin_approvals'),
            reverse('core:admin_placements'),
            reverse('core:admin_placement_create'),
            reverse('core:admin_reports'),
        ]

    def test_unauthenticated_user_redirected(self):
        client = Client()
        for endpoint in self.endpoints:
            with self.subTest(endpoint=endpoint):
                res = client.get(endpoint)
                self.assertEqual(res.status_code, 302)

    def test_student_blocked_from_admin_portal(self):
        client = Client()
        client.force_login(self.student_user)
        for endpoint in self.endpoints:
            with self.subTest(endpoint=endpoint):
                res = client.get(endpoint)
                self.assertEqual(res.status_code, 403)

    def test_recruiter_blocked_from_admin_portal(self):
        client = Client()
        client.force_login(self.recruiter_user)
        for endpoint in self.endpoints:
            with self.subTest(endpoint=endpoint):
                res = client.get(endpoint)
                self.assertEqual(res.status_code, 403)

    def test_admin_can_access_all_endpoints(self):
        client = Client()
        client.force_login(self.admin_user)
        for endpoint in self.endpoints:
            with self.subTest(endpoint=endpoint):
                res = client.get(endpoint)
                self.assertEqual(res.status_code, 200)


class AdminVerificationAndApprovalToggleTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            email='admin_toggle@placementhub.edu',
            password='Password123!',
            role=User.Role.ADMIN,
            is_approved=True,
        )
        self.client = Client()
        self.client.force_login(self.admin)

        self.student_user = User.objects.create_user(
            email='pending_student@college.edu',
            password='Password123!',
            role=User.Role.STUDENT,
            is_approved=True,
        )
        self.student = StudentProfile.objects.create(
            user=self.student_user,
            roll_no='CS2026TOG01',
            full_name='Toggle Candidate',
            branch='ECE',
            year=4,
            cgpa=8.2,
            is_verified=False,
        )

        self.recruiter_user = User.objects.create_user(
            email='pending_recruiter@company.com',
            password='Password123!',
            role=User.Role.RECRUITER,
            is_approved=False,
        )
        self.company = Company.objects.create(
            user=self.recruiter_user,
            company_name='Toggle Tech Corp',
            is_approved=False,
        )

    def test_student_verification_toggle(self):
        url = reverse('core:admin_student_toggle_verify', kwargs={'student_id': self.student.id})
        # Toggle from False to True
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)
        self.student.refresh_from_db()
        self.assertTrue(self.student.is_verified)

        # Toggle back from True to False
        response2 = self.client.post(url)
        self.assertEqual(response2.status_code, 302)
        self.student.refresh_from_db()
        self.assertFalse(self.student.is_verified)

    def test_recruiter_approval_toggle_keeps_user_and_company_in_sync(self):
        url = reverse('core:admin_recruiter_toggle_approval', kwargs={'company_id': self.company.id})

        # Initially both are False
        self.assertFalse(self.company.is_approved)
        self.assertFalse(self.recruiter_user.is_approved)

        # Approve recruiter
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)
        self.company.refresh_from_db()
        self.recruiter_user.refresh_from_db()
        self.assertTrue(self.company.is_approved)
        self.assertTrue(self.recruiter_user.is_approved)

        # Revoke recruiter approval
        response2 = self.client.post(url)
        self.assertEqual(response2.status_code, 302)
        self.company.refresh_from_db()
        self.recruiter_user.refresh_from_db()
        self.assertFalse(self.company.is_approved)
        self.assertFalse(self.recruiter_user.is_approved)


class AdminPlacementRecordCreationTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            email='admin_placement@placementhub.edu',
            password='Password123!',
            role=User.Role.ADMIN,
            is_approved=True,
        )
        self.client = Client()
        self.client.force_login(self.admin)

        # Recruiter & Job
        self.recruiter_user = User.objects.create_user(
            email='recruiter_placed@corp.com',
            password='Password123!',
            role=User.Role.RECRUITER,
            is_approved=True,
        )
        self.company = Company.objects.create(
            user=self.recruiter_user,
            company_name='Placed Corp',
            is_approved=True,
        )
        self.job = Job.objects.create(
            company=self.company,
            title='Systems Architect',
            package_lpa=16.0,
            location='Chennai',
            deadline=timezone.now().date() + timedelta(days=20),
            status=Job.Status.OPEN,
        )

        # Students & Applications
        self.stu_user1 = User.objects.create_user(
            email='placed_candidate@college.edu',
            password='Password123!',
            role=User.Role.STUDENT,
            is_approved=True,
        )
        self.student1 = StudentProfile.objects.create(
            user=self.stu_user1,
            roll_no='CS2026PLC01',
            full_name='Selected Candidate',
            branch='CSE',
            year=4,
            cgpa=9.1,
            is_verified=True,
            placement_status='NOT_PLACED',
        )

        self.stu_user2 = User.objects.create_user(
            email='applied_candidate@college.edu',
            password='Password123!',
            role=User.Role.STUDENT,
            is_approved=True,
        )
        self.student2 = StudentProfile.objects.create(
            user=self.stu_user2,
            roll_no='CS2026PLC02',
            full_name='Applied Candidate',
            branch='IT',
            year=4,
            cgpa=8.0,
            is_verified=True,
        )

        # Application 1: status is SELECTED (eligible for placement)
        self.selected_app = Application.objects.create(
            student=self.student1,
            job=self.job,
            status=Application.Status.SELECTED,
        )

        # Application 2: status is APPLIED (ineligible)
        self.applied_app = Application.objects.create(
            student=self.student2,
            job=self.job,
            status=Application.Status.APPLIED,
        )

    def test_placement_form_only_offers_selected_unplaced_applications(self):
        form = PlacementRecordCreateForm()
        queryset = form.fields['application'].queryset
        self.assertIn(self.selected_app, queryset)
        self.assertNotIn(self.applied_app, queryset)

        # Now place selected_app
        PlacementRecord.objects.create(
            student=self.student1,
            company=self.company,
            application=self.selected_app,
            package_lpa=16.0,
            is_final=True,
        )

        # Once placed, selected_app should no longer appear in the form queryset
        form_after = PlacementRecordCreateForm()
        self.assertNotIn(self.selected_app, form_after.fields['application'].queryset)

    def test_placement_creation_derives_student_and_company_and_marks_student_placed(self):
        url = reverse('core:admin_placement_create')
        post_data = {
            'application': self.selected_app.id,
            'package_lpa': 17.5,
            'offer_date': '2026-11-01',
            'is_final': True,
        }
        response = self.client.post(url, post_data)
        self.assertEqual(response.status_code, 302)

        record = PlacementRecord.objects.filter(application=self.selected_app).first()
        self.assertIsNotNone(record)
        # Derived automatically from application
        self.assertEqual(record.student, self.student1)
        self.assertEqual(record.company, self.company)
        self.assertEqual(record.package_lpa, 17.5)
        self.assertTrue(record.is_final)

        # Student placement_status updated to PLACED
        self.student1.refresh_from_db()
        self.assertEqual(self.student1.placement_status, 'PLACED')


class AdminReportsViewTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            email='admin_rep@placementhub.edu',
            password='Password123!',
            role=User.Role.ADMIN,
            is_approved=True,
        )
        self.client = Client()
        self.client.force_login(self.admin)

    def test_admin_reports_metrics(self):
        response = self.client.get(reverse('core:admin_reports'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('placements_by_branch', response.context)
        self.assertIn('application_status_breakdown', response.context)
        self.assertIn('top_companies', response.context)
