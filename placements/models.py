from django.db import models


class PlacementRecord(models.Model):
    student = models.ForeignKey(
        'students.StudentProfile',
        on_delete=models.CASCADE,
        related_name='placement_records'
    )
    company = models.ForeignKey(
        'recruiters.Company',
        on_delete=models.CASCADE,
        related_name='placement_records'
    )
    application = models.ForeignKey(
        'applications.Application',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='placement_record'
    )
    package_lpa = models.FloatField(default=0.0)
    offer_date = models.DateField(null=True, blank=True)
    is_final = models.BooleanField(default=True)

    def __init__(self, *args, **kwargs):
        if 'salary_package' in kwargs and 'package_lpa' not in kwargs:
            kwargs['package_lpa'] = kwargs.pop('salary_package')
        if 'join_date' in kwargs and 'offer_date' not in kwargs:
            kwargs['offer_date'] = kwargs.pop('join_date')
        super().__init__(*args, **kwargs)

    @property
    def salary_package(self):
        return self.package_lpa

    @salary_package.setter
    def salary_package(self, value):
        self.package_lpa = value

    @property
    def join_date(self):
        return self.offer_date

    @join_date.setter
    def join_date(self, value):
        self.offer_date = value

    def __str__(self):
        return f"{self.student.full_name} placed at {self.company.company_name} ({self.package_lpa} LPA)"
