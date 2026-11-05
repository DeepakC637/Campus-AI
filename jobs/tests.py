from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from recruiters.models import Company
from students.models import Skill
from jobs.models import Job

User = get_user_model()


class JobsModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='recruiter_job_test@company.com',
            password='Password123!',
            role=User.Role.RECRUITER,
            is_approved=True,
        )
        self.company = Company.objects.create(
            user=self.user,
            company_name='Innovatech Solutions',
        )
        self.skill = Skill.objects.create(name='Python', category='Backend')

    def test_create_job(self):
        deadline = timezone.now() + timedelta(days=30)
        job = Job.objects.create(
            company=self.company,
            title='Software Development Engineer',
            description='Build high-scale distributed backend microservices.',
            requirements='Proficiency in Python and database design.',
            min_cgpa=7.5,
            allowed_branches=['CSE', 'IT', 'ECE'],
            max_backlogs=0,
            package_lpa=12.5,
            location='Bengaluru, India',
            deadline=deadline,
            status=Job.Status.OPEN,
        )
        job.required_skills.add(self.skill)

        self.assertEqual(job.company, self.company)
        self.assertEqual(job.title, 'Software Development Engineer')
        self.assertEqual(job.min_cgpa, 7.5)
        self.assertEqual(job.package_lpa, 12.5)
        self.assertEqual(job.status, Job.Status.OPEN)
        self.assertIn(self.skill, job.required_skills.all())
