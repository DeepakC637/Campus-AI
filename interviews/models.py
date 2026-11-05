from django.db import models


class Interview(models.Model):
    class Mode(models.TextChoices):
        ONLINE = 'Online', 'Online'
        OFFLINE = 'Offline', 'Offline'

    class Status(models.TextChoices):
        SCHEDULED = 'Scheduled', 'Scheduled'
        COMPLETED = 'Completed', 'Completed'
        CANCELLED = 'Cancelled', 'Cancelled'

    application = models.ForeignKey(
        'applications.Application',
        on_delete=models.CASCADE,
        related_name='interviews'
    )
    round_type = models.CharField(max_length=100)
    mode = models.CharField(max_length=50, choices=Mode.choices, default=Mode.ONLINE)
    scheduled_at = models.DateTimeField()
    link_or_venue = models.CharField(max_length=255, blank=True, default='')
    result = models.CharField(max_length=100, blank=True, default='')
    feedback = models.TextField(blank=True, default='')
    status = models.CharField(max_length=50, choices=Status.choices, default=Status.SCHEDULED)

    def __init__(self, *args, **kwargs):
        if 'scheduled_time' in kwargs and 'scheduled_at' not in kwargs:
            kwargs['scheduled_at'] = kwargs.pop('scheduled_time')
        if 'link_or_location' in kwargs and 'link_or_venue' not in kwargs:
            kwargs['link_or_venue'] = kwargs.pop('link_or_location')
        super().__init__(*args, **kwargs)

    @property
    def scheduled_time(self):
        return self.scheduled_at

    @scheduled_time.setter
    def scheduled_time(self, value):
        self.scheduled_at = value

    @property
    def link_or_location(self):
        return self.link_or_venue

    @link_or_location.setter
    def link_or_location(self, value):
        self.link_or_venue = value

    def __str__(self):
        return f"{self.application.student.full_name} - {self.round_type} ({self.status})"
