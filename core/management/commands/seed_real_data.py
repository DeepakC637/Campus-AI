import os
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.files.base import ContentFile

from students.models import Skill, StudentProfile, Resume
from recruiters.models import Company, set_recruiter_approval
from jobs.models import Job
from applications.models import Application
from interviews.models import Interview
from placements.models import PlacementRecord
from ai_engine.scoring import compute_match_score

User = get_user_model()


class Command(BaseCommand):
    help = "Seeds comprehensive, realistic campus placement data across all modules."

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("Seeding realistic placement ecosystem data..."))

        # ---------------------------------------------------------------------
        # 1. Ensure Skill Taxonomy is loaded
        # ---------------------------------------------------------------------
        skills_cache = {s.name.lower(): s for s in Skill.objects.all()}
        if not skills_cache:
            from django.core.management import call_command
            call_command("seed_skills")
            skills_cache = {s.name.lower(): s for s in Skill.objects.all()}

        def get_skills(names):
            return [skills_cache[n.lower()] for n in names if n.lower() in skills_cache]

        # ---------------------------------------------------------------------
        # 2. Seed Admin Accounts
        # ---------------------------------------------------------------------
        admin_user, _ = User.objects.get_or_create(
            email="admin@campus.edu",
            defaults={
                "role": User.Role.ADMIN,
                "is_approved": True,
                "is_staff": True,
                "is_superuser": True,
                "username": "placement_admin",
                "first_name": "Dean",
                "last_name": "Placements",
            }
        )
        admin_user.set_password("AdminPass123!")
        admin_user.is_staff = True
        admin_user.is_superuser = True
        admin_user.is_approved = True
        admin_user.save()
        self.stdout.write(self.style.SUCCESS(f"Verified Admin: {admin_user.email}"))

        # ---------------------------------------------------------------------
        # 3. Seed Companies & Recruiters
        # ---------------------------------------------------------------------
        companies_data = [
            {
                "email": "recruiter@google.com",
                "company_name": "Google Cloud",
                "industry": "Cloud & Infrastructure",
                "website": "https://cloud.google.com",
                "contact_person": "Sundar Rajan (Campus Hiring Lead)",
                "description": "Global technology leader in distributed systems, search, and AI platform engineering.",
                "is_approved": True,
            },
            {
                "email": "careers@microsoft.com",
                "company_name": "Microsoft IDC",
                "industry": "Enterprise Software & Cloud",
                "website": "https://careers.microsoft.com",
                "contact_person": "Neha Sengupta (University Relations)",
                "description": "Building next-generation cloud services, Azure AI tools, and enterprise developer platforms.",
                "is_approved": True,
            },
            {
                "email": "university@amazon.in",
                "company_name": "Amazon Web Services",
                "industry": "E-Commerce & Cloud",
                "website": "https://aws.amazon.com",
                "contact_person": "Amit Kulkarni (Senior Tech Recruiter)",
                "description": "Pioneering hyperscale cloud computing, distributed database platforms, and retail engineering.",
                "is_approved": True,
            },
            {
                "email": "talent@razorpay.com",
                "company_name": "Razorpay Payments",
                "industry": "FinTech",
                "website": "https://razorpay.com",
                "contact_person": "Rhea Kapoor (Talent Acquisition)",
                "description": "India's premier payment gateway and neo-banking infrastructure provider handling billions in transactions.",
                "is_approved": True,
            },
            {
                "email": "talent@cred.club",
                "company_name": "CRED",
                "industry": "FinTech & Consumer Tech",
                "website": "https://cred.club",
                "contact_person": "Kunal Varma (Head of Engineering Talent)",
                "description": "Rewarding high-trust community and high-performance financial operating systems for creditworthy members.",
                "is_approved": True,
            },
            {
                "email": "campus@zomato.com",
                "company_name": "Zomato",
                "industry": "Consumer Internet & Logistics",
                "website": "https://zomato.com",
                "contact_person": "Deepinder Kaur (Campus Lead)",
                "description": "Hyperlocal commerce and technology platform powering millions of food deliveries and restaurant discovery.",
                "is_approved": True,
            },
            {
                "email": "campus@tcs.com",
                "company_name": "Tata Consultancy Services (TCS Digital)",
                "industry": "IT Services & Consulting",
                "website": "https://www.tcs.com",
                "contact_person": "Ritu Mathur (Regional Campus Head)",
                "description": "Global enterprise transformation leader providing digital, automation, and cloud services worldwide.",
                "is_approved": True,
            },
            {
                "email": "founder@innosys.ai",
                "company_name": "InnoSys AI Labs",
                "industry": "Artificial Intelligence & HealthTech",
                "website": "https://innosys.ai",
                "contact_person": "Dr. Alok Deshmukh (Founder & CTO)",
                "description": "Deep-tech venture building generative foundation models for molecular diagnostics and clinical trials.",
                "is_approved": False,  # Pending approval for Admin to approve!
            },
        ]

        companies_by_name = {}
        for cdata in companies_data:
            uname = cdata["email"].replace("@", "_").replace(".", "_")
            rec_user, _ = User.objects.get_or_create(
                email=cdata["email"],
                defaults={
                    "role": User.Role.RECRUITER,
                    "is_approved": cdata["is_approved"],
                    "username": uname,
                }
            )
            rec_user.set_password("Password123!")
            rec_user.is_approved = cdata["is_approved"]
            rec_user.save()

            company, _ = Company.objects.get_or_create(
                user=rec_user,
                defaults={
                    "company_name": cdata["company_name"],
                    "industry": cdata["industry"],
                    "website": cdata["website"],
                    "contact_person": cdata["contact_person"],
                    "description": cdata["description"],
                    "is_approved": cdata["is_approved"],
                }
            )
            company.company_name = cdata["company_name"]
            company.industry = cdata["industry"]
            company.website = cdata["website"]
            company.contact_person = cdata["contact_person"]
            company.description = cdata["description"]
            company.is_approved = cdata["is_approved"]
            company.save()
            companies_by_name[cdata["company_name"]] = company

        # Also sync default recruiter account
        default_rec, _ = User.objects.get_or_create(
            email="recruiter@techcorp.com",
            defaults={"role": User.Role.RECRUITER, "is_approved": True, "username": "recruiter"}
        )
        default_rec.set_password("Password123!")
        default_rec.is_approved = True
        default_rec.save()
        def_company, _ = Company.objects.get_or_create(
            user=default_rec,
            defaults={"company_name": "TechCorp Global", "industry": "Technology", "is_approved": True}
        )
        companies_by_name["TechCorp Global"] = def_company
        self.stdout.write(self.style.SUCCESS(f"Loaded {len(companies_by_name)} Companies & Recruiters."))

        # ---------------------------------------------------------------------
        # 4. Seed Job Postings
        # ---------------------------------------------------------------------
        now = timezone.now()
        jobs_data = [
            {
                "company": companies_by_name["Google Cloud"],
                "title": "Software Development Engineer I (Backend)",
                "description": "Design high-throughput, low-latency microservices powering Google Cloud Platform's compute orchestration and data pipelines.",
                "requirements": "Strong algorithmic foundations, proficiency with Python, Go, and relational / non-relational database design.",
                "min_cgpa": 8.0,
                "allowed_branches": ["Computer Science", "Information Technology"],
                "max_backlogs": 0,
                "package_lpa": 38.5,
                "location": "Bengaluru",
                "deadline": now + timedelta(days=22),
                "status": Job.Status.OPEN,
                "skills": ["Python", "Go", "Kubernetes", "Docker", "PostgreSQL"],
            },
            {
                "company": companies_by_name["Microsoft IDC"],
                "title": "Cloud Platform Engineer",
                "description": "Scale enterprise cloud infrastructure and developer observability services on Microsoft Azure and distributed Linux stacks.",
                "requirements": "Experience with cloud platforms, systems programming, automated CI/CD pipelines, and microservices architecture.",
                "min_cgpa": 7.5,
                "allowed_branches": ["Computer Science", "Information Technology", "Electronics & Communication"],
                "max_backlogs": 0,
                "package_lpa": 28.0,
                "location": "Hyderabad",
                "deadline": now + timedelta(days=16),
                "status": Job.Status.OPEN,
                "skills": ["Azure", "Python", "Docker", "Linux", "CI/CD"],
            },
            {
                "company": companies_by_name["Amazon Web Services"],
                "title": "Data Platform & Storage Engineer",
                "description": "Build high-scale distributed data pipelines, caching tiers, and analytics engines supporting millions of real-time transactions.",
                "requirements": "Expertise in SQL, schema design, relational and NoSQL databases, and cloud-native backend systems.",
                "min_cgpa": 7.5,
                "allowed_branches": ["Computer Science", "Information Technology"],
                "max_backlogs": 0,
                "package_lpa": 32.0,
                "location": "Bengaluru",
                "deadline": now + timedelta(days=28),
                "status": Job.Status.OPEN,
                "skills": ["AWS", "Python", "SQL", "PostgreSQL", "Redis"],
            },
            {
                "company": companies_by_name["Razorpay Payments"],
                "title": "Full Stack Engineer (Payments Grid)",
                "description": "Build resilient payment gateway interfaces, merchant onboarding dashboards, and transaction reconciliation workflows.",
                "requirements": "Full-stack proficiency across React, Node.js, TypeScript, PostgreSQL, and event-driven architectures.",
                "min_cgpa": 7.0,
                "allowed_branches": ["Computer Science", "Information Technology", "Electronics & Communication"],
                "max_backlogs": 0,
                "package_lpa": 22.0,
                "location": "Bengaluru",
                "deadline": now + timedelta(days=14),
                "status": Job.Status.OPEN,
                "skills": ["React", "Node.js", "TypeScript", "PostgreSQL", "Tailwind CSS"],
            },
            {
                "company": companies_by_name["CRED"],
                "title": "Frontend Architect & UI Engineer",
                "description": "Craft pixel-perfect, hyper-smooth user experiences, mobile-first design systems, and lightning-fast web applications.",
                "requirements": "Mastery of React, Next.js, modern CSS/Tailwind, state management, web performance optimization, and animations.",
                "min_cgpa": 7.5,
                "allowed_branches": ["Computer Science", "Information Technology"],
                "max_backlogs": 0,
                "package_lpa": 26.0,
                "location": "Bengaluru",
                "deadline": now + timedelta(days=12),
                "status": Job.Status.OPEN,
                "skills": ["React", "Next.js", "TypeScript", "Tailwind CSS", "GraphQL"],
            },
            {
                "company": companies_by_name["Zomato"],
                "title": "Machine Learning Engineer (Recommendations)",
                "description": "Develop and deploy deep learning ranking models, real-time demand estimation algorithms, and hyper-personalized search engines.",
                "requirements": "Hands-on model development in PyTorch/TensorFlow, statistical feature engineering, and high-performance inference pipelines.",
                "min_cgpa": 8.0,
                "allowed_branches": ["Computer Science", "Information Technology", "Electronics & Communication"],
                "max_backlogs": 0,
                "package_lpa": 24.5,
                "location": "Gurugram",
                "deadline": now + timedelta(days=30),
                "status": Job.Status.OPEN,
                "skills": ["Python", "PyTorch", "Machine Learning", "Scikit-Learn", "Pandas"],
            },
            {
                "company": companies_by_name["Tata Consultancy Services (TCS Digital)"],
                "title": "Digital Technology Specialist",
                "description": "Participate in enterprise digital transformation projects across cloud migration, test automation, and full-stack development.",
                "requirements": "Solid engineering fundamentals, proficiency in Python or Java, database basics, and enthusiasm for enterprise IT.",
                "min_cgpa": 6.5,
                "allowed_branches": ["Computer Science", "Information Technology", "Electronics & Communication", "Electrical", "Mechanical"],
                "max_backlogs": 1,
                "package_lpa": 9.0,
                "location": "Pune",
                "deadline": now + timedelta(days=45),
                "status": Job.Status.OPEN,
                "skills": ["Linux", "Python", "Git", "MySQL", "CI/CD"],
            },
            {
                "company": companies_by_name["TechCorp Global"],
                "title": "Backend Python / Django Developer",
                "description": "Develop robust REST APIs, background worker queues, and third-party integrations with Django and PostgreSQL.",
                "requirements": "Strong Python skills, hands-on experience with Django or FastAPI, PostgreSQL, and REST API architectural patterns.",
                "min_cgpa": 7.0,
                "allowed_branches": ["Computer Science", "Information Technology"],
                "max_backlogs": 0,
                "package_lpa": 16.0,
                "location": "Noida",
                "deadline": now + timedelta(days=20),
                "status": Job.Status.OPEN,
                "skills": ["Python", "Django", "PostgreSQL", "Git", "Docker"],
            },
            {
                "company": companies_by_name["InnoSys AI Labs"],
                "title": "Generative AI Research Associate",
                "description": "Fine-tuning large language models and diffusion networks for biomedical reasoning and chemical property prediction.",
                "requirements": "Experience with Hugging Face transformers, PyTorch, LoRA, and distributed multi-GPU training.",
                "min_cgpa": 8.0,
                "allowed_branches": ["Computer Science"],
                "max_backlogs": 0,
                "package_lpa": 20.0,
                "location": "Mumbai",
                "deadline": now + timedelta(days=60),
                "status": Job.Status.DRAFT,
                "skills": ["Python", "Deep Learning", "PyTorch", "NLP"],
            },
        ]

        jobs_by_title = {}
        for jdata in jobs_data:
            job, _ = Job.objects.get_or_create(
                company=jdata["company"],
                title=jdata["title"],
                defaults={
                    "description": jdata["description"],
                    "requirements": jdata["requirements"],
                    "min_cgpa": jdata["min_cgpa"],
                    "allowed_branches": jdata["allowed_branches"],
                    "max_backlogs": jdata["max_backlogs"],
                    "package_lpa": jdata["package_lpa"],
                    "location": jdata["location"],
                    "deadline": jdata["deadline"],
                    "status": jdata["status"],
                }
            )
            job.description = jdata["description"]
            job.requirements = jdata["requirements"]
            job.min_cgpa = jdata["min_cgpa"]
            job.allowed_branches = jdata["allowed_branches"]
            job.max_backlogs = jdata["max_backlogs"]
            job.package_lpa = jdata["package_lpa"]
            job.location = jdata["location"]
            job.deadline = jdata["deadline"]
            job.status = jdata["status"]
            job.save()

            matched_skills = get_skills(jdata["skills"])
            job.required_skills.set(matched_skills)
            jobs_by_title[jdata["title"]] = job

        self.stdout.write(self.style.SUCCESS(f"Loaded {len(jobs_by_title)} Job postings."))

        # ---------------------------------------------------------------------
        # 5. Seed Students & Resumes
        # ---------------------------------------------------------------------
        students_data = [
            {
                "email": "student@campus.edu",
                "full_name": "Deepak Choudhary",
                "roll_no": "CS2026-001",
                "branch": "Computer Science",
                "year": 2026,
                "cgpa": 9.1,
                "backlogs": 0,
                "phone": "+91 98765 43210",
                "is_verified": True,
                "placement_status": "UNPLACED",
                "skills": ["Python", "Django", "PostgreSQL", "Docker", "Git", "AWS", "FastAPI"],
                "resume_text": "Full Stack Backend Engineer proficient in Python, Django, PostgreSQL, Docker, AWS, Git, and FastAPI. Developed high-scale microservices, asynchronous task queues with Celery and Redis, and machine learning integration endpoints.",
            },
            {
                "email": "aarav.sharma@campus.edu",
                "full_name": "Aarav Sharma",
                "roll_no": "CS2026-042",
                "branch": "Computer Science",
                "year": 2026,
                "cgpa": 9.4,
                "backlogs": 0,
                "phone": "+91 98111 22334",
                "is_verified": True,
                "placement_status": "PLACED",
                "skills": ["Python", "Go", "Kubernetes", "Docker", "PostgreSQL", "Git"],
                "resume_text": "Distributed systems and cloud infrastructure specialist. Experienced with Go, Python, Kubernetes container orchestration, Docker, and PostgreSQL databases. Winner of Google Summer of Code 2025.",
            },
            {
                "email": "priya.patel@campus.edu",
                "full_name": "Priya Patel",
                "roll_no": "IT2026-015",
                "branch": "Information Technology",
                "year": 2026,
                "cgpa": 8.9,
                "backlogs": 0,
                "phone": "+91 98222 33445",
                "is_verified": True,
                "placement_status": "UNPLACED",
                "skills": ["React", "Next.js", "TypeScript", "Tailwind CSS", "Node.js", "GraphQL"],
                "resume_text": "Frontend and UI Engineer specializing in React, Next.js, TypeScript, Tailwind CSS, Node.js, and GraphQL. Passionate about design systems, accessible Web apps, and responsive interface architecture.",
            },
            {
                "email": "rohan.verma@campus.edu",
                "full_name": "Rohan Verma",
                "roll_no": "CS2026-088",
                "branch": "Computer Science",
                "year": 2026,
                "cgpa": 8.5,
                "backlogs": 0,
                "phone": "+91 98333 44556",
                "is_verified": True,
                "placement_status": "UNPLACED",
                "skills": ["Python", "PyTorch", "Machine Learning", "Scikit-Learn", "Pandas", "NumPy"],
                "resume_text": "Machine Learning and Data Science practitioner. Hands-on experience developing computer vision and deep learning models with PyTorch, Scikit-Learn, Pandas, NumPy, and Python. Published researcher.",
            },
            {
                "email": "ananya.iyer@campus.edu",
                "full_name": "Ananya Iyer",
                "roll_no": "EC2026-031",
                "branch": "Electronics & Communication",
                "year": 2026,
                "cgpa": 8.7,
                "backlogs": 0,
                "phone": "+91 98444 55667",
                "is_verified": True,
                "placement_status": "PLACED",
                "skills": ["Azure", "Python", "Docker", "Linux", "CI/CD", "Git"],
                "resume_text": "Cloud systems and DevOps engineer with a background in Electronics. Proficient in Microsoft Azure, Linux kernel tuning, automated CI/CD pipelines, Docker containerization, and Python scripting.",
            },
            {
                "email": "vikram.singh@campus.edu",
                "full_name": "Vikram Singh",
                "roll_no": "CS2026-104",
                "branch": "Computer Science",
                "year": 2026,
                "cgpa": 7.8,
                "backlogs": 0,
                "phone": "+91 98555 66778",
                "is_verified": True,
                "placement_status": "UNPLACED",
                "skills": ["Java", "Spring Boot", "MySQL", "AWS", "Docker", "SQL"],
                "resume_text": "Enterprise backend software engineer with Java, Spring Boot, MySQL, SQL, and AWS. Built cloud-native transaction processing services with automated test coverage.",
            },
            {
                "email": "sneha.rao@campus.edu",
                "full_name": "Sneha Rao",
                "roll_no": "IT2026-056",
                "branch": "Information Technology",
                "year": 2026,
                "cgpa": 7.3,
                "backlogs": 1,
                "phone": "+91 98666 77889",
                "is_verified": False,  # Pending student verification for Admin!
                "placement_status": "UNPLACED",
                "skills": ["HTML5", "CSS3", "JavaScript", "React", "MySQL"],
                "resume_text": "Web developer with skills in HTML5, CSS3, JavaScript, React, and MySQL database management. Built academic portal and student attendance projects.",
            },
        ]

        students_by_email = {}
        for sdata in students_data:
            s_uname = sdata["email"].replace("@", "_").replace(".", "_")
            stu_user, _ = User.objects.get_or_create(
                email=sdata["email"],
                defaults={
                    "role": User.Role.STUDENT,
                    "is_approved": True,
                    "username": s_uname,
                    "first_name": sdata["full_name"].split()[0],
                    "last_name": sdata["full_name"].split()[-1],
                }
            )
            stu_user.set_password("Password123!")
            stu_user.is_approved = True
            stu_user.save()

            profile, _ = StudentProfile.objects.get_or_create(
                user=stu_user,
                defaults={
                    "roll_no": sdata["roll_no"],
                    "full_name": sdata["full_name"],
                    "branch": sdata["branch"],
                    "year": sdata["year"],
                    "cgpa": sdata["cgpa"],
                    "backlogs": sdata["backlogs"],
                    "phone": sdata["phone"],
                    "is_verified": sdata["is_verified"],
                    "placement_status": sdata["placement_status"],
                }
            )
            profile.roll_no = sdata["roll_no"]
            profile.full_name = sdata["full_name"]
            profile.branch = sdata["branch"]
            profile.year = sdata["year"]
            profile.cgpa = sdata["cgpa"]
            profile.backlogs = sdata["backlogs"]
            profile.phone = sdata["phone"]
            profile.is_verified = sdata["is_verified"]
            profile.placement_status = sdata["placement_status"]
            profile.save()

            matched_skills = get_skills(sdata["skills"])
            profile.skills.set(matched_skills)

            # Ensure an active resume is attached
            active_resume = Resume.objects.filter(student=profile, is_active=True).first()
            if not active_resume:
                active_resume = Resume.objects.create(
                    student=profile,
                    file=f"resumes/{profile.roll_no}_Resume.pdf",
                    extracted_text=sdata["resume_text"],
                    parsed_skills=sdata["skills"],
                    is_active=True,
                )
            else:
                active_resume.extracted_text = sdata["resume_text"]
                active_resume.parsed_skills = sdata["skills"]
                active_resume.save()

            students_by_email[sdata["email"]] = profile

        self.stdout.write(self.style.SUCCESS(f"Loaded {len(students_by_email)} Students with active profiles."))

        # ---------------------------------------------------------------------
        # 6. Seed Applications with Real-time AI Compatibility Scores
        # ---------------------------------------------------------------------
        applications_plan = [
            # 1. Aarav Sharma -> Google Cloud SDE I (Selected & Placed)
            {
                "student": students_by_email["aarav.sharma@campus.edu"],
                "job": jobs_by_title["Software Development Engineer I (Backend)"],
                "status": Application.Status.SELECTED,
            },
            # 2. Ananya Iyer -> Microsoft Cloud Solutions (Selected & Placed)
            {
                "student": students_by_email["ananya.iyer@campus.edu"],
                "job": jobs_by_title["Cloud Platform Engineer"],
                "status": Application.Status.SELECTED,
            },
            # 3. Deepak (Demo Student) -> Razorpay Full Stack (Shortlisted)
            {
                "student": students_by_email["student@campus.edu"],
                "job": jobs_by_title["Full Stack Engineer (Payments Grid)"],
                "status": Application.Status.SHORTLISTED,
            },
            # 4. Deepak (Demo Student) -> Google Cloud SDE I (Interview Scheduled)
            {
                "student": students_by_email["student@campus.edu"],
                "job": jobs_by_title["Software Development Engineer I (Backend)"],
                "status": Application.Status.INTERVIEW,
            },
            # 5. Deepak (Demo Student) -> TechCorp Backend (Applied)
            {
                "student": students_by_email["student@campus.edu"],
                "job": jobs_by_title["Backend Python / Django Developer"],
                "status": Application.Status.APPLIED,
            },
            # 6. Priya Patel -> CRED Frontend (Interview Scheduled)
            {
                "student": students_by_email["priya.patel@campus.edu"],
                "job": jobs_by_title["Frontend Architect & UI Engineer"],
                "status": Application.Status.INTERVIEW,
            },
            # 7. Priya Patel -> Razorpay Full Stack (Shortlisted)
            {
                "student": students_by_email["priya.patel@campus.edu"],
                "job": jobs_by_title["Full Stack Engineer (Payments Grid)"],
                "status": Application.Status.SHORTLISTED,
            },
            # 8. Rohan Verma -> Zomato ML Engineer (Interview Scheduled)
            {
                "student": students_by_email["rohan.verma@campus.edu"],
                "job": jobs_by_title["Machine Learning Engineer (Recommendations)"],
                "status": Application.Status.INTERVIEW,
            },
            # 9. Vikram Singh -> AWS Data Platform (Applied)
            {
                "student": students_by_email["vikram.singh@campus.edu"],
                "job": jobs_by_title["Data Platform & Storage Engineer"],
                "status": Application.Status.APPLIED,
            },
            # 10. Sneha Rao -> TCS Digital (Rejected)
            {
                "student": students_by_email["sneha.rao@campus.edu"],
                "job": jobs_by_title["Digital Technology Specialist"],
                "status": Application.Status.REJECTED,
            },
        ]

        apps_dict = {}
        for app_info in applications_plan:
            student = app_info["student"]
            job = app_info["job"]
            active_resume = student.resumes.filter(is_active=True).first()
            resume_text = active_resume.extracted_text if active_resume else ""

            # Calculate real-time AI match score using our engine
            score = compute_match_score(
                student_skills=list(student.skills.all()),
                job_required_skills=list(job.required_skills.all()),
                student_resume_text=resume_text,
                job_description=f"{job.description} {job.requirements}",
            )

            application, _ = Application.objects.get_or_create(
                student=student,
                job=job,
                defaults={
                    "status": app_info["status"],
                    "match_score": round(score, 1),
                }
            )
            application.status = app_info["status"]
            application.match_score = round(score, 1)
            application.save()

            key = (student.user.email, job.title)
            apps_dict[key] = application

        self.stdout.write(self.style.SUCCESS(f"Loaded {len(apps_dict)} Job Applications with real AI scores."))

        # ---------------------------------------------------------------------
        # 7. Seed Scheduled and Completed Interviews
        # ---------------------------------------------------------------------
        interviews_plan = [
            # Deepak (Demo Student) -> Google Cloud SDE I
            {
                "app": apps_dict[("student@campus.edu", "Software Development Engineer I (Backend)")],
                "round_type": "Technical Round 1 (System Design & Python)",
                "mode": Interview.Mode.ONLINE,
                "scheduled_at": now + timedelta(days=2, hours=3),
                "link_or_venue": "https://meet.google.com/xyz-goog-sde",
                "feedback": "Candidate demonstrated deep knowledge of distributed systems and Django ORM optimization.",
                "status": Interview.Status.SCHEDULED,
            },
            # Priya Patel -> CRED Frontend
            {
                "app": apps_dict[("priya.patel@campus.edu", "Frontend Architect & UI Engineer")],
                "round_type": "Component Design & Web Performance",
                "mode": Interview.Mode.ONLINE,
                "scheduled_at": now + timedelta(days=3, hours=5),
                "link_or_venue": "https://meet.google.com/crd-front-arc",
                "feedback": "Strong React architecture portfolio and responsive CSS fundamentals.",
                "status": Interview.Status.SCHEDULED,
            },
            # Rohan Verma -> Zomato ML
            {
                "app": apps_dict[("rohan.verma@campus.edu", "Machine Learning Engineer (Recommendations)")],
                "round_type": "ML Coding & Feature Engineering",
                "mode": Interview.Mode.ONLINE,
                "scheduled_at": now + timedelta(days=1, hours=4),
                "link_or_venue": "https://meet.google.com/zom-recom-ml",
                "feedback": "Good understanding of matrix factorization and transformer inference.",
                "status": Interview.Status.SCHEDULED,
            },
            # Aarav Sharma -> Google Cloud SDE I (Completed)
            {
                "app": apps_dict[("aarav.sharma@campus.edu", "Software Development Engineer I (Backend)")],
                "round_type": "Final Executive Engineering Round",
                "mode": Interview.Mode.ONLINE,
                "scheduled_at": now - timedelta(days=5),
                "link_or_venue": "https://meet.google.com/goog-exec-round",
                "feedback": "Exceptional problem solving, passed all algorithmic test cases. Strongly recommended for hire.",
                "status": Interview.Status.COMPLETED,
            },
            # Ananya Iyer -> Microsoft Cloud Solutions (Completed)
            {
                "app": apps_dict[("ananya.iyer@campus.edu", "Cloud Platform Engineer")],
                "round_type": "Technical & Culture Fit Discussion",
                "mode": Interview.Mode.ONLINE,
                "scheduled_at": now - timedelta(days=8),
                "link_or_venue": "https://teams.microsoft.com/l/meetup-join/msft-cloud",
                "feedback": "Clear architectural communication and solid Linux scripting skills. Recommended for offer.",
                "status": Interview.Status.COMPLETED,
            },
        ]

        for iv in interviews_plan:
            interview, _ = Interview.objects.get_or_create(
                application=iv["app"],
                round_type=iv["round_type"],
                defaults={
                    "mode": iv["mode"],
                    "scheduled_at": iv["scheduled_at"],
                    "link_or_venue": iv["link_or_venue"],
                    "feedback": iv["feedback"],
                    "status": iv["status"],
                }
            )
            interview.mode = iv["mode"]
            interview.scheduled_at = iv["scheduled_at"]
            interview.link_or_venue = iv["link_or_venue"]
            interview.feedback = iv["feedback"]
            interview.status = iv["status"]
            interview.save()

        self.stdout.write(self.style.SUCCESS(f"Loaded {len(interviews_plan)} Scheduled & Completed Interviews."))

        # ---------------------------------------------------------------------
        # 8. Seed Official Placement Records (For Admin analytics)
        # ---------------------------------------------------------------------
        placements_plan = [
            # 1. Aarav Sharma -> Google Cloud (38.5 LPA)
            {
                "student": students_by_email["aarav.sharma@campus.edu"],
                "company": companies_by_name["Google Cloud"],
                "app": apps_dict[("aarav.sharma@campus.edu", "Software Development Engineer I (Backend)")],
                "package_lpa": 38.5,
                "offer_date": (now - timedelta(days=3)).date(),
                "is_final": True,
            },
            # 2. Ananya Iyer -> Microsoft IDC (28.0 LPA)
            {
                "student": students_by_email["ananya.iyer@campus.edu"],
                "company": companies_by_name["Microsoft IDC"],
                "app": apps_dict[("ananya.iyer@campus.edu", "Cloud Platform Engineer")],
                "package_lpa": 28.0,
                "offer_date": (now - timedelta(days=6)).date(),
                "is_final": True,
            },
        ]

        for pl in placements_plan:
            record, _ = PlacementRecord.objects.get_or_create(
                student=pl["student"],
                company=pl["company"],
                application=pl["app"],
                defaults={
                    "package_lpa": pl["package_lpa"],
                    "offer_date": pl["offer_date"],
                    "is_final": pl["is_final"],
                }
            )
            record.package_lpa = pl["package_lpa"]
            record.offer_date = pl["offer_date"]
            record.is_final = pl["is_final"]
            record.save()

            # Ensure student placement status is PLACED
            pl["student"].placement_status = "PLACED"
            pl["student"].save(update_fields=["placement_status"])

        self.stdout.write(self.style.SUCCESS(f"Loaded {len(placements_plan)} Verified Placement Records."))
        self.stdout.write(self.style.SUCCESS("All real-time placement data seeded successfully!"))
