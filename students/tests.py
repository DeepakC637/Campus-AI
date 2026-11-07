from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
from students.models import Skill, StudentProfile, Resume
from recruiters.models import Company
from jobs.models import Job
from applications.models import Application
from interviews.models import Interview

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


class StudentViewsTests(TestCase):
    def setUp(self):
        self.client = Client()

        # Student User
        self.student_user = User.objects.create_user(
            email='student_view_test@campus.edu',
            password='Password123!',
            role=User.Role.STUDENT,
        )
        self.student = StudentProfile.objects.create(
            user=self.student_user,
            roll_no='CS2026-VIEW',
            full_name='Eva Student',
            branch='Computer Science',
            year=2026,
            cgpa=8.8,
            backlogs=0,
            phone='9988776655',
        )
        self.skill_python = Skill.objects.create(name='Python', category='Programming')
        self.skill_django = Skill.objects.create(name='Django', category='Framework')
        self.skill_sql = Skill.objects.create(name='SQL', category='Database')
        self.student.skills.add(self.skill_python, self.skill_django)

        # Recruiter User
        self.recruiter_user = User.objects.create_user(
            email='recruiter_view_test@company.com',
            password='Password123!',
            role=User.Role.RECRUITER,
            is_approved=True,
        )
        self.company = Company.objects.create(
            user=self.recruiter_user,
            company_name='Nexus Systems',
            website='https://nexus.example.com',
        )

        # Eligible Job
        self.eligible_job = Job.objects.create(
            company=self.company,
            title='Backend Engineer',
            description='Build scalable APIs in Python/Django.',
            requirements='Knowledge of REST, SQL, Python.',
            min_cgpa=7.0,
            allowed_branches=['Computer Science', 'IT'],
            max_backlogs=0,
            package_lpa=10.0,
            location='Hyderabad',
            deadline=timezone.now() + timedelta(days=15),
            status=Job.Status.OPEN,
        )
        self.eligible_job.required_skills.add(self.skill_python, self.skill_django, self.skill_sql)

        # Ineligible Job (high CGPA & backlogs cutoff)
        self.ineligible_job = Job.objects.create(
            company=self.company,
            title='Staff Scientist',
            description='PhD level research.',
            min_cgpa=9.5,  # Student has 8.8
            allowed_branches=['Computer Science'],
            max_backlogs=0,
            package_lpa=25.0,
            deadline=timezone.now() + timedelta(days=20),
            status=Job.Status.OPEN,
        )

    def test_unauthenticated_user_redirected_to_login(self):
        response = self.client.get(reverse('students:dashboard'))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('accounts:login'), response.url)

    def test_recruiter_denied_access_to_student_views(self):
        self.client.login(email='recruiter_view_test@company.com', password='Password123!')
        response = self.client.get(reverse('students:dashboard'))
        self.assertEqual(response.status_code, 403)

    def test_student_dashboard_view(self):
        self.client.login(email='student_view_test@campus.edu', password='Password123!')
        response = self.client.get(reverse('students:dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Eva Student')
        self.assertContains(response, 'Backend Engineer')
        self.assertIn('completion_percentage', response.context)
        self.assertIn('jobs_applied_count', response.context)
        self.assertIn('status_counts', response.context)

    def test_student_profile_edit_and_skills(self):
        self.client.login(email='student_view_test@campus.edu', password='Password123!')

        # GET profile
        get_res = self.client.get(reverse('students:profile'))
        self.assertEqual(get_res.status_code, 200)
        self.assertContains(get_res, 'Eva Student')

        # POST update profile & add new skill
        post_res = self.client.post(reverse('students:profile'), {
            'full_name': 'Eva Updated',
            'roll_no': 'CS2026-VIEW',
            'branch': 'Computer Science',
            'year': 2026,
            'cgpa': 9.0,
            'backlogs': 0,
            'phone': '9988776655',
            'placement_status': 'UNPLACED',
            'skills_text': 'React, Docker',
        })
        self.assertEqual(post_res.status_code, 302)
        self.student.refresh_from_db()
        self.assertEqual(self.student.full_name, 'Eva Updated')
        self.assertEqual(self.student.cgpa, 9.0)
        self.assertTrue(self.student.skills.filter(name__iexact='React').exists())
        self.assertTrue(self.student.skills.filter(name__iexact='Docker').exists())

        # Remove skill
        skill_to_remove = self.student.skills.filter(name__iexact='React').first()
        remove_res = self.client.post(reverse('students:profile'), {
            'action': 'remove_skill',
            'skill_id': skill_to_remove.id,
        })
        self.assertEqual(remove_res.status_code, 302)
        self.assertFalse(self.student.skills.filter(name__iexact='React').exists())

    def test_resume_upload_marks_previous_inactive(self):
        self.client.login(email='student_view_test@campus.edu', password='Password123!')

        # Upload first resume
        pdf1 = SimpleUploadedFile("resume_v1.pdf", b"%PDF-1.4 v1", content_type="application/pdf")
        res1 = self.client.post(reverse('students:resume'), {'file': pdf1})
        self.assertEqual(res1.status_code, 302)

        first_resume = Resume.objects.filter(student=self.student, is_active=True).first()
        self.assertIsNotNone(first_resume)
        self.assertIn("resume_v1", first_resume.file.name)

        # Upload second resume
        pdf2 = SimpleUploadedFile("resume_v2.docx", b"PK docx content", content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
        res2 = self.client.post(reverse('students:resume'), {'file': pdf2})
        self.assertEqual(res2.status_code, 302)

        first_resume.refresh_from_db()
        self.assertFalse(first_resume.is_active)

        second_resume = Resume.objects.filter(student=self.student, is_active=True).first()
        self.assertIsNotNone(second_resume)
        self.assertIn("resume_v2", second_resume.file.name)
        self.assertEqual(second_resume.extracted_text, "")
        self.assertEqual(second_resume.parsed_skills, [])

    def test_job_browsing_shows_tags(self):
        self.client.login(email='student_view_test@campus.edu', password='Password123!')
        response = self.client.get(reverse('students:jobs'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Backend Engineer')
        self.assertContains(response, 'Eligible')
        self.assertContains(response, 'Staff Scientist')
        self.assertContains(response, 'Not Eligible')

    def test_eligible_student_can_apply(self):
        self.client.login(email='student_view_test@campus.edu', password='Password123!')
        apply_url = reverse('students:apply_job', kwargs={'pk': self.eligible_job.pk})
        response = self.client.post(apply_url)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('students:applications'))

        # Verify application created with status "Applied"
        app = Application.objects.filter(student=self.student, job=self.eligible_job).first()
        self.assertIsNotNone(app)
        self.assertEqual(app.status, Application.Status.APPLIED)

    def test_ineligible_student_blocked_server_side(self):
        self.client.login(email='student_view_test@campus.edu', password='Password123!')
        apply_url = reverse('students:apply_job', kwargs={'pk': self.ineligible_job.pk})
        response = self.client.post(apply_url)
        self.assertEqual(response.status_code, 403)
        self.assertFalse(Application.objects.filter(student=self.student, job=self.ineligible_job).exists())

    def test_cannot_apply_twice_to_same_job(self):
        self.client.login(email='student_view_test@campus.edu', password='Password123!')
        apply_url = reverse('students:apply_job', kwargs={'pk': self.eligible_job.pk})

        # First apply
        res1 = self.client.post(apply_url)
        self.assertEqual(res1.status_code, 302)
        self.assertEqual(Application.objects.filter(student=self.student, job=self.eligible_job).count(), 1)

        # Second apply (blocked)
        res2 = self.client.post(apply_url)
        self.assertEqual(res2.status_code, 302)
        self.assertEqual(Application.objects.filter(student=self.student, job=self.eligible_job).count(), 1)

    def test_application_withdrawal_only_allowed_from_applied_or_shortlisted(self):
        self.client.login(email='student_view_test@campus.edu', password='Password123!')

        # 1. Withdraw from "Applied" -> allowed
        app_applied = Application.objects.create(
            student=self.student,
            job=self.eligible_job,
            status=Application.Status.APPLIED,
        )
        withdraw_url = reverse('students:withdraw_application', kwargs={'pk': app_applied.pk})
        res1 = self.client.post(withdraw_url)
        self.assertEqual(res1.status_code, 302)
        app_applied.refresh_from_db()
        self.assertEqual(app_applied.status, Application.Status.WITHDRAWN)

        # 2. Withdraw from "Shortlisted" -> allowed
        app_applied.status = Application.Status.SHORTLISTED
        app_applied.save()
        res2 = self.client.post(withdraw_url)
        self.assertEqual(res2.status_code, 302)
        app_applied.refresh_from_db()
        self.assertEqual(app_applied.status, Application.Status.WITHDRAWN)

        # 3. Withdraw from "Interview" -> blocked (400 Bad Request)
        app_applied.status = Application.Status.INTERVIEW
        app_applied.save()
        res3 = self.client.post(withdraw_url)
        self.assertEqual(res3.status_code, 400)
        app_applied.refresh_from_db()
        self.assertEqual(app_applied.status, Application.Status.INTERVIEW)

        # 4. Withdraw from "Selected" -> blocked (400 Bad Request)
        app_applied.status = Application.Status.SELECTED
        app_applied.save()
        res4 = self.client.post(withdraw_url)
        self.assertEqual(res4.status_code, 400)
        app_applied.refresh_from_db()
        self.assertEqual(app_applied.status, Application.Status.SELECTED)

    def test_skill_gap_analysis(self):
        self.client.login(email='student_view_test@campus.edu', password='Password123!')
        url = reverse('students:skill_gap', kwargs={'job_id': self.eligible_job.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        # Student has Python, Django. Job requires Python, Django, SQL.
        # Matched: Python, Django (2)
        # Missing: SQL (1)
        self.assertIn('Python', response.context['matched_skills'])
        self.assertIn('Django', response.context['matched_skills'])
        self.assertIn('SQL', response.context['missing_skills'])
        self.assertEqual(response.context['match_percentage'], 66)

    def test_interviews_view_lists_student_interviews(self):
        self.client.login(email='student_view_test@campus.edu', password='Password123!')
        app = Application.objects.create(
            student=self.student,
            job=self.eligible_job,
            status=Application.Status.INTERVIEW,
        )
        interview = Interview.objects.create(
            application=app,
            round_type='System Design Round',
            mode=Interview.Mode.ONLINE,
            scheduled_at=timezone.now() + timedelta(days=3),
            link_or_venue='https://meet.google.com/abc-xyz',
            status=Interview.Status.SCHEDULED,
        )

        response = self.client.get(reverse('students:interviews'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'System Design Round')
        self.assertContains(response, 'Nexus Systems')
