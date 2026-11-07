from django import forms
from django.utils import timezone
from applications.models import Application
from placements.models import PlacementRecord


class PlacementRecordCreateForm(forms.ModelForm):
    application = forms.ModelChoiceField(
        queryset=Application.objects.none(),
        label="Selected Application",
        widget=forms.Select(attrs={
            'class': 'w-full rounded-lg border-slate-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 text-sm'
        })
    )

    class Meta:
        model = PlacementRecord
        fields = ['application', 'package_lpa', 'offer_date', 'is_final']
        widgets = {
            'package_lpa': forms.NumberInput(attrs={
                'class': 'w-full rounded-lg border-slate-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 text-sm',
                'step': '0.1',
                'placeholder': 'e.g. 12.5'
            }),
            'offer_date': forms.DateInput(attrs={
                'type': 'date',
                'class': 'w-full rounded-lg border-slate-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 text-sm'
            }),
            'is_final': forms.CheckboxInput(attrs={
                'class': 'rounded border-slate-300 text-blue-600 focus:ring-blue-500'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Strict requirement: only offer Applications with status="Selected" that don't already have a PlacementRecord
        self.fields['application'].queryset = Application.objects.filter(
            status=Application.Status.SELECTED,
            placement_record__isnull=True
        ).select_related('student', 'job', 'job__company')

        self.fields['application'].label_from_instance = (
            lambda app: f"{app.student.full_name} ({app.student.roll_no}) - {app.job.title} at {app.job.company.company_name} (Standard: ₹{app.job.package_lpa} LPA)"
        )

        if not self.initial.get('offer_date'):
            self.initial['offer_date'] = timezone.now().date()

    def save(self, commit=True):
        record = super().save(commit=False)
        application = self.cleaned_data['application']
        record.application = application
        record.student = application.student
        record.company = application.job.company

        if commit:
            record.save()
            # Synchronize student's placement status to PLACED
            student = record.student
            student.placement_status = 'PLACED'
            student.save(update_fields=['placement_status'])

        return record

