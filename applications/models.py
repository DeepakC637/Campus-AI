from django.db import models


class Application(models.Model):
    class Status(models.TextChoices):
        APPLIED = 'Applied', 'Applied'
        SHORTLISTED = 'Shortlisted', 'Shortlisted'
        INTERVIEW = 'Interview', 'Interview'
        SELECTED = 'Selected', 'Selected'
        REJECTED = 'Rejected', 'Rejected'
        WITHDRAWN = 'Withdrawn', 'Withdrawn'

    student = models.ForeignKey(
        'students.StudentProfile',
        on_delete=models.CASCADE,
        related_name='applications'
    )
    job = models.ForeignKey(
        'jobs.Job',
        on_delete=models.CASCADE,
        related_name='applications'
    )
    status = models.CharField(max_length=30, choices=Status.choices, default=Status.APPLIED)
    match_score = models.FloatField(null=True, blank=True)
    applied_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('student', 'job')

    def __str__(self):
        return f"{self.student.full_name} -> {self.job.title} ({self.status})"
