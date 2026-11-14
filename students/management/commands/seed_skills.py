"""
Management command to seed common technical skills across categories into the database.
Idempotent: uses get_or_create so it can be safely re-run without creating duplicates.
"""

from django.core.management.base import BaseCommand
from students.models import Skill


SKILLS_DATA = [
    # Programming Languages
    ("Python", "Programming Languages"),
    ("Java", "Programming Languages"),
    ("C++", "Programming Languages"),
    ("C#", "Programming Languages"),
    ("JavaScript", "Programming Languages"),
    ("TypeScript", "Programming Languages"),
    ("Go", "Programming Languages"),
    ("Rust", "Programming Languages"),
    ("Ruby", "Programming Languages"),
    ("PHP", "Programming Languages"),
    ("Swift", "Programming Languages"),
    ("Kotlin", "Programming Languages"),
    ("R", "Programming Languages"),
    ("SQL", "Programming Languages"),

    # Web & Backend Frameworks
    ("Django", "Backend Frameworks"),
    ("Flask", "Backend Frameworks"),
    ("FastAPI", "Backend Frameworks"),
    ("Spring Boot", "Backend Frameworks"),
    ("Node.js", "Backend Frameworks"),
    ("Express.js", "Backend Frameworks"),
    ("Ruby on Rails", "Backend Frameworks"),
    ("ASP.NET Core", "Backend Frameworks"),
    ("NestJS", "Backend Frameworks"),
    ("GraphQL", "Backend Frameworks"),

    # Frontend & Mobile
    ("React", "Frontend & Mobile"),
    ("Angular", "Frontend & Mobile"),
    ("Vue.js", "Frontend & Mobile"),
    ("Next.js", "Frontend & Mobile"),
    ("HTML5", "Frontend & Mobile"),
    ("CSS3", "Frontend & Mobile"),
    ("Tailwind CSS", "Frontend & Mobile"),
    ("Flutter", "Frontend & Mobile"),
    ("React Native", "Frontend & Mobile"),

    # Databases & Storage
    ("PostgreSQL", "Databases & Storage"),
    ("MySQL", "Databases & Storage"),
    ("MongoDB", "Databases & Storage"),
    ("Redis", "Databases & Storage"),
    ("SQLite", "Databases & Storage"),
    ("Oracle", "Databases & Storage"),
    ("Elasticsearch", "Databases & Storage"),
    ("Cassandra", "Databases & Storage"),

    # Cloud & DevOps
    ("AWS", "Cloud & DevOps"),
    ("Azure", "Cloud & DevOps"),
    ("Google Cloud", "Cloud & DevOps"),
    ("Docker", "Cloud & DevOps"),
    ("Kubernetes", "Cloud & DevOps"),
    ("Linux", "Cloud & DevOps"),
    ("Git", "Cloud & DevOps"),
    ("CI/CD", "Cloud & DevOps"),
    ("Terraform", "Cloud & DevOps"),
    ("Nginx", "Cloud & DevOps"),

    # AI, Data Science & Machine Learning
    ("Machine Learning", "AI & Data Science"),
    ("Deep Learning", "AI & Data Science"),
    ("PyTorch", "AI & Data Science"),
    ("TensorFlow", "AI & Data Science"),
    ("Pandas", "AI & Data Science"),
    ("NumPy", "AI & Data Science"),
    ("Scikit-Learn", "AI & Data Science"),
    ("Computer Vision", "AI & Data Science"),
    ("NLP", "AI & Data Science"),
]


class Command(BaseCommand):
    help = "Seeds common technical skills across categories idempotently"

    def handle(self, *args, **options):
        created_count = 0
        existing_count = 0

        for name, category in SKILLS_DATA:
            skill, created = Skill.objects.get_or_create(
                name=name,
                defaults={"category": category}
            )
            if created:
                created_count += 1
            else:
                existing_count += 1

        total_skills = Skill.objects.count()
        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully processed skills: {created_count} created, "
                f"{existing_count} already existed. Total skills in database: {total_skills}."
            )
        )
