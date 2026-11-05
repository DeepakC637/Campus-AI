from django.test import TestCase
from django.contrib.auth import get_user_model
from recruiters.models import Company

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
