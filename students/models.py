from django.db import models
from django.conf import settings


class Skill(models.Model):
    name = models.CharField(max_length=100, unique=True)
    category = models.CharField(max_length=100, blank=True, default='')

    def __str__(self):
        return self.name


class StudentProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='student_profile'
    )
    roll_no = models.CharField(max_length=50, unique=True)
    full_name = models.CharField(max_length=150)
    branch = models.CharField(max_length=100)
    year = models.IntegerField(default=2026)
    cgpa = models.FloatField(default=0.0)
    backlogs = models.IntegerField(default=0)
    phone = models.CharField(max_length=20, blank=True, default='')
    is_verified = models.BooleanField(default=False)
    placement_status = models.CharField(max_length=50, default='UNPLACED')
    skills = models.ManyToManyField(Skill, blank=True, related_name='students')

    def __init__(self, *args, **kwargs):
        if 'graduation_year' in kwargs and 'year' not in kwargs:
            kwargs['year'] = kwargs.pop('graduation_year')
        super().__init__(*args, **kwargs)

    @property
    def graduation_year(self):
        return self.year

    @graduation_year.setter
    def graduation_year(self, value):
        self.year = value

    def get_profile_completion_percentage(self):
        total_fields = 7
        completed = 0
        if self.roll_no: completed += 1
        if self.full_name: completed += 1
        if self.branch: completed += 1
        if self.year: completed += 1
        if self.cgpa > 0: completed += 1
        if self.phone: completed += 1
        if self.skills.exists(): completed += 1
        return int((completed / total_fields) * 100)

    def __str__(self):
        return f"{self.full_name} ({self.roll_no})"


class Resume(models.Model):
    student = models.ForeignKey(
        StudentProfile,
        on_delete=models.CASCADE,
        related_name='resumes'
    )
    file = models.FileField(upload_to='resumes/')
    extracted_text = models.TextField(blank=True, default='')
    parsed_skills = models.JSONField(default=list, blank=True)
    parsed_education = models.JSONField(default=dict, blank=True)
    parsed_projects = models.JSONField(default=list, blank=True)
    is_active = models.BooleanField(default=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Resume - {self.student.full_name} ({self.uploaded_at.strftime('%Y-%m-%d')})"
