from django.test import TestCase, RequestFactory
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from accounts.models import User
from accounts.decorators import role_required

User = get_user_model()


class AccountsModelAndAuthTests(TestCase):
    def test_student_auto_approved(self):
        student = User.objects.create_user(
            email='student@example.com',
            password='Password123!',
            role=User.Role.STUDENT,
        )
        self.assertEqual(student.role, User.Role.STUDENT)
        self.assertTrue(student.is_approved)

    def test_recruiter_not_approved_by_default(self):
        recruiter = User.objects.create_user(
            email='recruiter@company.com',
            password='Password123!',
            role=User.Role.RECRUITER,
        )
        self.assertEqual(recruiter.role, User.Role.RECRUITER)
        self.assertFalse(recruiter.is_approved)

    def test_admin_approved_by_default(self):
        admin = User.objects.create_superuser(
            email='admin@campus.edu',
            password='AdminPassword123!',
        )
        self.assertEqual(admin.role, User.Role.ADMIN)
        self.assertTrue(admin.is_approved)
        self.assertTrue(admin.is_staff)

    def test_role_required_decorator_blocks_unapproved_recruiter(self):
        rf = RequestFactory()
        request = rf.get('/dummy/')
        recruiter = User.objects.create_user(
            email='recruiter2@company.com',
            password='Password123!',
            role=User.Role.RECRUITER,
            is_approved=False,
        )
        request.user = recruiter

        @role_required('RECRUITER')
        def protected_view(req):
            return HttpResponse('OK')

        with self.assertRaises(PermissionDenied):
            protected_view(request)

    def test_role_required_decorator_allows_approved_recruiter(self):
        rf = RequestFactory()
        request = rf.get('/dummy/')
        recruiter = User.objects.create_user(
            email='approved_rec@company.com',
            password='Password123!',
            role=User.Role.RECRUITER,
            is_approved=True,
        )
        request.user = recruiter

        @role_required('RECRUITER')
        def protected_view(req):
            return HttpResponse('OK')

        response = protected_view(request)
        self.assertEqual(response.status_code, 200)

    def test_role_required_decorator_allows_student(self):
        rf = RequestFactory()
        request = rf.get('/dummy/')
        student = User.objects.create_user(
            email='student2@example.com',
            password='Password123!',
            role=User.Role.STUDENT,
        )
        request.user = student

        @role_required('STUDENT')
        def protected_view(req):
            return HttpResponse('OK')

        response = protected_view(request)
        self.assertEqual(response.status_code, 200)
