from django.db import models


class Job(models.Model):
    class Status(models.TextChoices):
        DRAFT = 'DRAFT', 'Draft'
        OPEN = 'OPEN', 'Open'
        CLOSED = 'CLOSED', 'Closed'

    company = models.ForeignKey(
        'recruiters.Company',
        on_delete=models.CASCADE,
        related_name='jobs'
    )
    title = models.CharField(max_length=200)
    description = models.TextField()
    requirements = models.TextField(blank=True, default='')
    min_cgpa = models.FloatField(default=0.0)
    allowed_branches = models.JSONField(default=list, blank=True)
    max_backlogs = models.IntegerField(default=0)
    package_lpa = models.FloatField(default=0.0)
    location = models.CharField(max_length=150, default='Remote')
    deadline = models.DateTimeField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.OPEN)
    required_skills = models.ManyToManyField('students.Skill', blank=True, related_name='jobs')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} - {self.company.company_name}"
