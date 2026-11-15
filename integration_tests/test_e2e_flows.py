"""
integration_tests/test_e2e_flows.py

Comprehensive End-to-End Flow Testing for PlacementHub.
Simulates real-world user journeys across multiple apps and validates security,
role isolation, and data-volume performance.
"""

import time
from datetime import timedelta
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.urls import reverse
from django.utils import timezone

from students.models import Skill, StudentProfile, Resume
from recruiters.models import Company, set_recruiter_approval
from jobs.models import Job
from applications.models import Application
from interviews.models import Interview
from placements.models import PlacementRecord
from ai_engine.scoring import recommend_jobs

User = get_user_model()

# Valid minimal PDF fixture containing known technical skills
VALID_PDF_BYTES = (
    b"%PDF-1.4\n"
    b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
    b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
    b"3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R/Resources<</Font<</F1 4 0 R>>>>/Contents 5 0 R>>endobj\n"
    b"4 0 obj<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>endobj\n"
    b"5 0 obj<</Length 68>>stream\n"
    b"BT /F1 12 Tf 100 700 Td (Experienced in Python, Django, and PostgreSQL) Tj ET\n"
    b"endstream\nendobj\n"
    b"xref\n0 6\n"
    b"0000000000 65535 f \n"
    b"0000000009 00000 n \n"
    b"0000000052 00000 n \n"
    b"0000000101 00000 n \n"
    b"0000000212 00000 n \n"
    b"0000000281 00000 n \n"
    b"trailer<</Size 6/Root 1 0 R>>\n"
    b"startxref\n400\n%%EOF\n"
)


class EndToEndFlowsTests(TestCase):
    def setUp(self):
        call_command("seed_skills")
        self.client = Client()

        # Seed pre-requisite skills
        self.skill_python = Skill.objects.get(name="Python")
        self.skill_django = Skill.objects.get(name="Django")
        self.skill_postgres = Skill.objects.get(name="PostgreSQL")
        self.skill_sql = Skill.objects.get(name="SQL")
        self.skill_docker = Skill.objects.get(name="Docker")

    # =========================================================================
    # Journey A — Student lifecycle
    # =========================================================================
    def test_journey_a_student_lifecycle(self):
        """
        Register as student -> auto-approved -> login -> complete profile
        -> upload resume -> browse jobs -> view job detail (live compatibility score)
        -> apply to eligible job -> application tracker -> skill gap view
        -> withdraw a different application -> confirm cannot un-withdraw.
        """
        # 1. Setup recruiter and jobs for the student to interact with
        recruiter_user = User.objects.create_user(
            email="drive_host@techgiant.com",
            password="RecruiterPass123!",
            role=User.Role.RECRUITER,
            is_approved=True,
        )
        company = Company.objects.create(
            user=recruiter_user,
            company_name="TechGiant Systems",
            industry="Software",
        )
        job1 = Job.objects.create(
            company=company,
            title="Backend Python Developer",
            description="Build scalable APIs with Python, Django, and PostgreSQL.",
            requirements="Python, Django, PostgreSQL, Git",
            min_cgpa=7.5,
            allowed_branches=["Computer Science", "IT"],
            max_backlogs=0,
            package_lpa=12.0,
            location="Bengaluru",
            deadline=timezone.now() + timedelta(days=25),
            status=Job.Status.OPEN,
        )
        job1.required_skills.add(self.skill_python, self.skill_django, self.skill_postgres)

        job2 = Job.objects.create(
            company=company,
            title="Data Platform Engineer",
            description="Work with SQL and relational data stores.",
            requirements="SQL and database management",
            min_cgpa=6.0,
            allowed_branches=["Computer Science"],
            max_backlogs=1,
            package_lpa=9.0,
            location="Hyderabad",
            deadline=timezone.now() + timedelta(days=15),
            status=Job.Status.OPEN,
        )
        job2.required_skills.add(self.skill_sql)

        # 2. Register as student
        register_url = reverse("accounts:register")
        reg_response = self.client.post(register_url, {
            "role": User.Role.STUDENT,
            "email": "alice_journey_a@campus.edu",
            "password": "StudentPass123!",
            "confirm_password": "StudentPass123!",
            "first_name": "Alice",
            "last_name": "Student",
        })
        self.assertEqual(reg_response.status_code, 302, "Student registration should redirect on success")

        student_user = User.objects.get(email="alice_journey_a@campus.edu")
        self.assertEqual(student_user.role, User.Role.STUDENT)
        self.assertTrue(student_user.is_approved, "Students must be auto-approved upon registration")

        # 3. Login as student
        login_success = self.client.login(email="alice_journey_a@campus.edu", password="StudentPass123!")
        self.assertTrue(login_success, "Student login must succeed")

        # 4. Complete student profile
        profile_url = reverse("students:profile")
        prof_response = self.client.post(profile_url, {
            "full_name": "Alice Student",
            "roll_no": "CS2026-JOURNEY-A",
            "branch": "Computer Science",
            "year": 2026,
            "cgpa": 9.2,
            "backlogs": 0,
            "phone": "9876543210",
            "placement_status": "UNPLACED",
            "skills_text": "Python, Django, PostgreSQL",
        })
        self.assertEqual(prof_response.status_code, 302)

        student_profile = StudentProfile.objects.get(user=student_user)
        self.assertEqual(student_profile.full_name, "Alice Student")
        self.assertEqual(student_profile.cgpa, 9.2)
        self.assertTrue(student_profile.skills.filter(name="Python").exists())

        # 5. Upload resume (using valid PDF fixture)
        resume_url = reverse("students:resume")
        pdf_file = SimpleUploadedFile("alice_resume.pdf", VALID_PDF_BYTES, content_type="application/pdf")
        resume_response = self.client.post(resume_url, {"file": pdf_file})
        self.assertEqual(resume_response.status_code, 302)

        active_resume = Resume.objects.filter(student=student_profile, is_active=True).first()
        self.assertIsNotNone(active_resume)
        self.assertIn("Experienced in Python, Django, and PostgreSQL", active_resume.extracted_text)
        self.assertIn("Python", active_resume.parsed_skills)

        # 6. Browse jobs
        jobs_res = self.client.get(reverse("students:jobs"))
        self.assertEqual(jobs_res.status_code, 200)
        self.assertContains(jobs_res, "Backend Python Developer")

        # 7. View job detail (see live compatibility score)
        detail_res = self.client.get(reverse("students:job_detail", kwargs={"pk": job1.pk}))
        self.assertEqual(detail_res.status_code, 200)
        self.assertIn("match_score", detail_res.context)
        self.assertGreaterEqual(detail_res.context["match_score"], 70.0, "Matching skills must score >= 70%")

        # 8. Apply to an eligible job (Job 1)
        apply_res = self.client.post(reverse("students:apply_job", kwargs={"pk": job1.pk}))
        self.assertEqual(apply_res.status_code, 302)

        app1 = Application.objects.filter(student=student_profile, job=job1).first()
        self.assertIsNotNone(app1)
        self.assertEqual(app1.status, Application.Status.APPLIED)
        self.assertIsNotNone(app1.match_score)

        # Apply to second job (Job 2) for withdrawal testing
        self.client.post(reverse("students:apply_job", kwargs={"pk": job2.pk}))
        app2 = Application.objects.get(student=student_profile, job=job2)

        # 9. See application in application tracker
        apps_tracker_res = self.client.get(reverse("students:applications"))
        self.assertEqual(apps_tracker_res.status_code, 200)
        self.assertContains(apps_tracker_res, "Backend Python Developer")
        self.assertContains(apps_tracker_res, "Data Platform Engineer")

        # 10. View skill gap for Job 1
        skill_gap_res = self.client.get(reverse("students:skill_gap", kwargs={"job_id": job1.pk}))
        self.assertEqual(skill_gap_res.status_code, 200)
        self.assertIn("matched_skills", skill_gap_res.context)
        self.assertIn("Python", skill_gap_res.context["matched_skills"])

        # 11. Withdraw application for Job 2
        withdraw_res = self.client.post(reverse("students:withdraw_application", kwargs={"pk": app2.pk}))
        self.assertEqual(withdraw_res.status_code, 302)
        app2.refresh_from_db()
        self.assertEqual(app2.status, Application.Status.WITHDRAWN)

        # 12. Confirm withdrawn application cannot be un-withdrawn / withdrawn again
        second_withdraw_res = self.client.post(reverse("students:withdraw_application", kwargs={"pk": app2.pk}))
        self.assertEqual(second_withdraw_res.status_code, 400, "Withdrawing an already Withdrawn app must fail with 400")
        app2.refresh_from_db()
        self.assertEqual(app2.status, Application.Status.WITHDRAWN)

    # =========================================================================
    # Journey B — Recruiter lifecycle
    # =========================================================================
    def test_journey_b_recruiter_lifecycle(self):
        """
        Register as recruiter -> blocked from recruiter dashboard (pending approval)
        -> admin approves -> login succeeds -> complete company profile
        -> post a job -> see own job in job list -> student applies
        -> see applicant in applicants list with real match_score
        -> shortlist them -> schedule an interview -> update status to Selected.
        """
        # 1. Register as recruiter
        reg_response = self.client.post(reverse("accounts:register"), {
            "role": User.Role.RECRUITER,
            "email": "bob_recruiter@innovatech.com",
            "password": "RecruiterPass123!",
            "confirm_password": "RecruiterPass123!",
            "first_name": "Bob",
            "last_name": "Recruiter",
        })
        self.assertEqual(reg_response.status_code, 200)
        self.assertContains(reg_response, "pending administrator approval")

        recruiter_user = User.objects.get(email="bob_recruiter@innovatech.com")
        self.assertFalse(recruiter_user.is_approved, "New recruiters must require admin approval")

        # 2. Blocked from recruiter dashboard
        self.client.login(email="bob_recruiter@innovatech.com", password="RecruiterPass123!")
        dashboard_blocked_res = self.client.get(reverse("recruiters:dashboard"))
        self.assertEqual(
            dashboard_blocked_res.status_code,
            403,
            "Unapproved recruiter must receive HTTP 403 Forbidden on protected views",
        )

        # 3. Admin approves recruiter
        company = recruiter_user.company_profile
        set_recruiter_approval(company, True)
        recruiter_user.refresh_from_db()
        company.refresh_from_db()
        self.assertTrue(recruiter_user.is_approved)
        self.assertTrue(company.is_approved)

        # 4. Login and access recruiter dashboard
        self.client.login(email="bob_recruiter@innovatech.com", password="RecruiterPass123!")
        dashboard_res = self.client.get(reverse("recruiters:dashboard"))
        self.assertEqual(dashboard_res.status_code, 200, "Approved recruiter can access dashboard")

        # 5. Complete company profile
        profile_res = self.client.post(reverse("recruiters:profile"), {
            "company_name": "InnovaTech Solutions",
            "description": "Next-generation cloud and distributed AI systems.",
            "website": "https://innovatech.example.com",
            "industry": "Information Technology",
            "contact_person": "Bob Recruiter",
        })
        self.assertEqual(profile_res.status_code, 302)
        company.refresh_from_db()
        self.assertEqual(company.company_name, "InnovaTech Solutions")

        # 6. Post a job
        job_create_res = self.client.post(reverse("recruiters:job_create"), {
            "title": "Full Stack Cloud Engineer",
            "description": "Design backend services in Python, Django, and PostgreSQL.",
            "requirements": "Hands-on experience with Python, Django, PostgreSQL, Docker.",
            "min_cgpa": 7.0,
            "allowed_branches": "Computer Science, IT",
            "max_backlogs": 0,
            "package_lpa": 14.5,
            "location": "Pune",
            "deadline": (timezone.now() + timedelta(days=30)).strftime("%Y-%m-%d"),
            "status": Job.Status.OPEN,
            "required_skills": [self.skill_python.pk, self.skill_django.pk, self.skill_postgres.pk],
        })
        self.assertEqual(job_create_res.status_code, 302)

        posted_job = Job.objects.filter(company=company, title="Full Stack Cloud Engineer").first()
        self.assertIsNotNone(posted_job)

        # 7. See own job in job list
        job_list_res = self.client.get(reverse("recruiters:jobs"))
        self.assertEqual(job_list_res.status_code, 200)
        self.assertContains(job_list_res, "Full Stack Cloud Engineer")

        # 8. Student applies to this job
        applicant_user = User.objects.create_user(
            email="candidate_journey_b@campus.edu",
            password="Password123!",
            role=User.Role.STUDENT,
        )
        applicant_student = StudentProfile.objects.create(
            user=applicant_user,
            roll_no="STU-JOURNEY-B",
            full_name="Carol Applicant",
            branch="Computer Science",
            year=2026,
            cgpa=8.8,
        )
        applicant_student.skills.add(self.skill_python, self.skill_django, self.skill_postgres)
        Resume.objects.create(
            student=applicant_student,
            file="resumes/carol_resume.pdf",
            extracted_text="Experienced in Python, Django, and PostgreSQL backends.",
            parsed_skills=["Python", "Django", "PostgreSQL"],
            is_active=True,
        )

        # Student applies
        student_client = Client()
        student_client.login(email="candidate_journey_b@campus.edu", password="Password123!")
        student_client.post(reverse("students:apply_job", kwargs={"pk": posted_job.pk}))

        application = Application.objects.get(student=applicant_student, job=posted_job)
        self.assertIsNotNone(application.match_score)

        # 9. Recruiter views applicants list with real match_score
        applicants_res = self.client.get(reverse("recruiters:job_applicants", kwargs={"pk": posted_job.pk}))
        self.assertEqual(applicants_res.status_code, 200)
        self.assertContains(applicants_res, "Carol Applicant")
        self.assertContains(applicants_res, f"{application.match_score:.0f}% Fit")

        # 10. Shortlist candidate
        shortlist_res = self.client.post(
            reverse("recruiters:update_application_status", kwargs={"pk": application.pk}),
            {"status": Application.Status.SHORTLISTED},
        )
        self.assertEqual(shortlist_res.status_code, 302)
        application.refresh_from_db()
        self.assertEqual(application.status, Application.Status.SHORTLISTED)

        # 11. Schedule an interview
        interview_time = timezone.now() + timedelta(days=2)
        interview_res = self.client.post(
            reverse("recruiters:schedule_interview", kwargs={"pk": application.pk}),
            {
                "round_type": "Technical Round 1",
                "mode": "Online",
                "scheduled_at": interview_time.strftime("%Y-%m-%dT%H:%M"),
                "link_or_venue": "https://meet.google.com/xyz-uvw-rst",
                "feedback": "Strong profile with verified backend skills.",
            },
        )
        self.assertEqual(interview_res.status_code, 302)
        interview = Interview.objects.filter(application=application).first()
        self.assertIsNotNone(interview)
        self.assertEqual(interview.status, Interview.Status.SCHEDULED)

        # 12. Update application status to Selected
        select_res = self.client.post(
            reverse("recruiters:update_application_status", kwargs={"pk": application.pk}),
            {"status": Application.Status.SELECTED},
        )
        self.assertEqual(select_res.status_code, 302)
        application.refresh_from_db()
        self.assertEqual(application.status, Application.Status.SELECTED)

    # =========================================================================
    # Journey C — Admin lifecycle
    # =========================================================================
    def test_journey_c_admin_lifecycle(self):
        """
        Login as admin -> approve pending recruiter -> verify student
        -> record placement for Selected application -> confirm student placement_status flips to PLACED
        -> view reports and confirm placement stats appear.
        """
        # Setup entities
        admin_user = User.objects.create_superuser(
            email="superadmin@campus.edu",
            password="AdminPassword123!",
            role=User.Role.ADMIN,
            is_approved=True,
        )

        unapproved_recruiter = User.objects.create_user(
            email="pending_recruiter@startup.io",
            password="Password123!",
            role=User.Role.RECRUITER,
            is_approved=False,
        )
        company = Company.objects.create(
            user=unapproved_recruiter,
            company_name="Apex AI Labs",
            is_approved=False,
        )

        student_user = User.objects.create_user(
            email="student_c@campus.edu",
            password="Password123!",
            role=User.Role.STUDENT,
        )
        student = StudentProfile.objects.create(
            user=student_user,
            roll_no="STU-JOURNEY-C",
            full_name="David Student",
            branch="Information Technology",
            year=2026,
            cgpa=8.9,
            is_verified=False,
            placement_status="UNPLACED",
        )

        job = Job.objects.create(
            company=company,
            title="AI Systems Architect",
            min_cgpa=7.0,
            package_lpa=18.0,
            deadline=timezone.now() + timedelta(days=15),
            status=Job.Status.OPEN,
        )

        selected_app = Application.objects.create(
            student=student,
            job=job,
            status=Application.Status.SELECTED,
            match_score=94.0,
        )

        # 1. Login as Admin
        self.client.login(email="superadmin@campus.edu", password="AdminPassword123!")
        dash_res = self.client.get(reverse("core:admin_dashboard"))
        self.assertEqual(dash_res.status_code, 200)

        # 2. Approve the pending recruiter
        approve_res = self.client.post(
            reverse("core:admin_recruiter_toggle_approval", kwargs={"company_id": company.id})
        )
        self.assertEqual(approve_res.status_code, 302)
        company.refresh_from_db()
        unapproved_recruiter.refresh_from_db()
        self.assertTrue(company.is_approved)
        self.assertTrue(unapproved_recruiter.is_approved)

        # 3. Verify the student
        verify_res = self.client.post(
            reverse("core:admin_student_toggle_verify", kwargs={"student_id": student.id})
        )
        self.assertEqual(verify_res.status_code, 302)
        student.refresh_from_db()
        self.assertTrue(student.is_verified)

        # 4. Record placement for the Selected application
        placement_create_url = reverse("core:admin_placement_create")
        create_res = self.client.post(placement_create_url, {
            "application": selected_app.id,
            "package_lpa": 18.0,
            "offer_date": timezone.now().date().strftime("%Y-%m-%d"),
            "is_final": True,
        })
        self.assertEqual(create_res.status_code, 302)

        # 5. Confirm student's placement_status flips to PLACED
        student.refresh_from_db()
        self.assertEqual(student.placement_status, "PLACED")

        placement_record = PlacementRecord.objects.filter(student=student, company=company).first()
        self.assertIsNotNone(placement_record)
        self.assertEqual(placement_record.package_lpa, 18.0)

        # 6. View reports and confirm the placement appears in statistics
        reports_res = self.client.get(reverse("core:admin_reports"))
        self.assertEqual(reports_res.status_code, 200)
        self.assertContains(reports_res, "Information Technology")
        self.assertContains(reports_res, "Apex AI Labs")

    # =========================================================================
    # Journey D — Security & Isolation Cross-Check
    # =========================================================================
    def test_journey_d_security_and_isolation_cross_check(self):
        """
        1. Recruiter X cannot see/edit Recruiter Y's jobs or applicants (403).
        2. Student A cannot withdraw Student B's application (404).
        3. Unapproved recruiter cannot post a job via direct crafted POST (403).
        4. Unauthenticated user hitting protected URLs gets redirected to login (302), not a 500.
        """
        # Create Recruiter X and Company X
        user_x = User.objects.create_user(
            email="recruiter_x@corp.com",
            password="Password123!",
            role=User.Role.RECRUITER,
            is_approved=True,
        )
        company_x = Company.objects.create(user=user_x, company_name="Company X")
        job_x = Job.objects.create(
            company=company_x,
            title="Job X",
            package_lpa=10.0,
            deadline=timezone.now() + timedelta(days=10),
            status=Job.Status.OPEN,
        )

        # Create Recruiter Y and Company Y
        user_y = User.objects.create_user(
            email="recruiter_y@corp.com",
            password="Password123!",
            role=User.Role.RECRUITER,
            is_approved=True,
        )
        company_y = Company.objects.create(user=user_y, company_name="Company Y")
        job_y = Job.objects.create(
            company=company_y,
            title="Job Y",
            package_lpa=12.0,
            deadline=timezone.now() + timedelta(days=10),
            status=Job.Status.OPEN,
        )

        # Create Student A and Student B
        user_stu_a = User.objects.create_user(email="stu_a@campus.edu", password="Password123!", role=User.Role.STUDENT)
        student_a = StudentProfile.objects.create(user=user_stu_a, roll_no="STU-ISO-A", full_name="Student A", year=2026)

        user_stu_b = User.objects.create_user(email="stu_b@campus.edu", password="Password123!", role=User.Role.STUDENT)
        student_b = StudentProfile.objects.create(user=user_stu_b, roll_no="STU-ISO-B", full_name="Student B", year=2026)

        app_b = Application.objects.create(student=student_b, job=job_x, status=Application.Status.APPLIED)

        # 1. Recruiter X attempts to access Recruiter Y's job edit and applicants
        self.client.login(email="recruiter_x@corp.com", password="Password123!")

        res_edit = self.client.get(reverse("recruiters:job_edit", kwargs={"pk": job_y.pk}))
        self.assertEqual(res_edit.status_code, 403, "Recruiter X editing Recruiter Y's job must return 403")

        res_applicants = self.client.get(reverse("recruiters:job_applicants", kwargs={"pk": job_y.pk}))
        self.assertEqual(res_applicants.status_code, 403, "Recruiter X viewing Recruiter Y's applicants must return 403")

        # 2. Student A attempts to withdraw Student B's application
        self.client.login(email="stu_a@campus.edu", password="Password123!")
        res_withdraw_foreign = self.client.post(reverse("students:withdraw_application", kwargs={"pk": app_b.pk}))
        self.assertEqual(res_withdraw_foreign.status_code, 404, "Student withdrawing foreign application must return 404")
        app_b.refresh_from_db()
        self.assertEqual(app_b.status, Application.Status.APPLIED, "Foreign application status must remain untouched")

        # 3. Unapproved recruiter attempts direct POST to job_create
        unapproved_user = User.objects.create_user(
            email="unapproved_hacker@corp.com",
            password="Password123!",
            role=User.Role.RECRUITER,
            is_approved=False,
        )
        Company.objects.create(user=unapproved_user, company_name="Unapproved Corp", is_approved=False)

        self.client.login(email="unapproved_hacker@corp.com", password="Password123!")
        craft_post_res = self.client.post(reverse("recruiters:job_create"), {
            "title": "Unauthorized Job",
            "description": "Crafted injection",
            "package_lpa": 20.0,
            "deadline": (timezone.now() + timedelta(days=10)).strftime("%Y-%m-%d"),
            "status": Job.Status.OPEN,
        })
        self.assertEqual(craft_post_res.status_code, 403, "Crafted POST from unapproved recruiter must be blocked (403)")

        # 4. Unauthenticated requests to protected endpoints redirect to login (never 500)
        self.client.logout()
        protected_urls = [
            reverse("students:dashboard"),
            reverse("students:jobs"),
            reverse("students:profile"),
            reverse("students:applications"),
            reverse("recruiters:dashboard"),
            reverse("recruiters:jobs"),
            reverse("core:admin_dashboard"),
            reverse("core:admin_students"),
            reverse("core:admin_recruiters"),
            reverse("core:admin_reports"),
        ]
        login_url = reverse("accounts:login")
        for url in protected_urls:
            resp = self.client.get(url)
            self.assertEqual(
                resp.status_code,
                302,
                f"Unauthenticated access to {url} must redirect (302), got {resp.status_code}",
            )
            self.assertIn(login_url, resp.url)

    # =========================================================================
    # Data-volume performance sanity check
    # =========================================================================
    def test_data_volume_performance_sanity_check(self):
        """
        Create 50 students, 10 recruiters, 20 jobs via loops.
        Confirm recommend_jobs() and dashboard view respond in under 2 seconds.
        """
        # 1. Bulk create 10 recruiters and companies
        recruiters = []
        for i in range(10):
            user = User.objects.create_user(
                email=f"perf_recruiter_{i}@enterprise.com",
                password="Password123!",
                role=User.Role.RECRUITER,
                is_approved=True,
            )
            company = Company.objects.create(
                user=user,
                company_name=f"Enterprise Firm {i}",
                industry="Tech",
            )
            recruiters.append((user, company))

        # 2. Bulk create 20 jobs
        skills_pool = [self.skill_python, self.skill_django, self.skill_postgres, self.skill_sql, self.skill_docker]
        for j in range(20):
            _, company = recruiters[j % len(recruiters)]
            job = Job.objects.create(
                company=company,
                title=f"Software Engineer Track {j}",
                description="Engineering role involving high-scale Python microservices and PostgreSQL storage.",
                requirements="Python, Django, PostgreSQL, and team collaboration.",
                min_cgpa=6.5 + (j % 3) * 0.5,
                allowed_branches=["Computer Science", "Information Technology", "Electronics"],
                max_backlogs=0,
                package_lpa=8.0 + j * 0.5,
                location="Bengaluru" if j % 2 == 0 else "Hyderabad",
                deadline=timezone.now() + timedelta(days=15 + j),
                status=Job.Status.OPEN,
            )
            job.required_skills.set([skills_pool[j % len(skills_pool)], skills_pool[(j + 1) % len(skills_pool)]])

        # 3. Bulk create 50 students with profiles and resumes
        target_student = None
        for s in range(50):
            user = User.objects.create_user(
                email=f"perf_student_{s}@campus.edu",
                password="Password123!",
                role=User.Role.STUDENT,
            )
            student = StudentProfile.objects.create(
                user=user,
                roll_no=f"STU-PERF-{s:04d}",
                full_name=f"Student Perf {s}",
                branch="Computer Science",
                year=2026,
                cgpa=7.0 + (s % 30) * 0.1,
                placement_status="UNPLACED",
            )
            student.skills.set([self.skill_python, self.skill_django])
            Resume.objects.create(
                student=student,
                file=f"resumes/perf_{s}.pdf",
                extracted_text="Skilled in Python, Django, REST APIs, and relational databases.",
                parsed_skills=["Python", "Django"],
                is_active=True,
            )
            if s == 0:
                target_student = student

        # 4. Measure recommend_jobs() execution duration
        start_recs = time.perf_counter()
        recommendations = recommend_jobs(target_student, top_n=5)
        duration_recs = time.perf_counter() - start_recs

        self.assertEqual(len(recommendations), 5, "recommend_jobs must return top 5 jobs")
        self.assertLess(
            duration_recs,
            2.0,
            f"recommend_jobs() took {duration_recs:.3f}s; must execute under 2.0s",
        )

        # 5. Measure student dashboard view execution duration
        self.client.login(email="perf_student_0@campus.edu", password="Password123!")
        start_dash = time.perf_counter()
        dash_response = self.client.get(reverse("students:dashboard"))
        duration_dash = time.perf_counter() - start_dash

        self.assertEqual(dash_response.status_code, 200)
        self.assertLess(
            duration_dash,
            2.0,
            f"Dashboard view took {duration_dash:.3f}s; must execute under 2.0s",
        )
