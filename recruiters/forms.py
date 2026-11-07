from django import forms
from .models import Company
from jobs.models import Job
from interviews.models import Interview
from students.models import Skill


class CompanyProfileForm(forms.ModelForm):
    class Meta:
        model = Company
        fields = [
            'company_name',
            'description',
            'website',
            'industry',
            'contact_person',
            'logo',
        ]
        widgets = {
            'company_name': forms.TextInput(attrs={'class': 'w-full px-3.5 py-2.5 bg-white border border-slate-300 rounded-lg text-sm text-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-500'}),
            'description': forms.Textarea(attrs={'class': 'w-full px-3.5 py-2.5 bg-white border border-slate-300 rounded-lg text-sm text-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-500', 'rows': 4}),
            'website': forms.URLInput(attrs={'class': 'w-full px-3.5 py-2.5 bg-white border border-slate-300 rounded-lg text-sm text-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-500', 'placeholder': 'https://company.com'}),
            'industry': forms.TextInput(attrs={'class': 'w-full px-3.5 py-2.5 bg-white border border-slate-300 rounded-lg text-sm text-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-500', 'placeholder': 'e.g. Cloud, FinTech, AI'}),
            'contact_person': forms.TextInput(attrs={'class': 'w-full px-3.5 py-2.5 bg-white border border-slate-300 rounded-lg text-sm text-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-500'}),
            'logo': forms.FileInput(attrs={'class': 'block w-full text-sm text-slate-500 file:mr-4 file:py-2.5 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100 cursor-pointer'}),
        }


class JobPostForm(forms.ModelForm):
    branches_input = forms.CharField(
        required=False,
        label="Allowed Branches (comma-separated)",
        help_text="e.g. Computer Science, Information Technology, Electronics",
        widget=forms.TextInput(attrs={
            'class': 'w-full px-3.5 py-2.5 bg-white border border-slate-300 rounded-lg text-sm text-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-500',
            'placeholder': 'Computer Science, IT, ECE'
        })
    )

    skills_input = forms.CharField(
        required=False,
        label="Required Skills (comma-separated)",
        help_text="e.g. Python, Django, SQL, React",
        widget=forms.TextInput(attrs={
            'class': 'w-full px-3.5 py-2.5 bg-white border border-slate-300 rounded-lg text-sm text-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-500',
            'placeholder': 'Python, Django, AWS...'
        })
    )

    class Meta:
        model = Job
        fields = [
            'title',
            'description',
            'requirements',
            'min_cgpa',
            'max_backlogs',
            'package_lpa',
            'location',
            'deadline',
            'status',
            'required_skills',
        ]
        widgets = {
            'title': forms.TextInput(attrs={'class': 'w-full px-3.5 py-2.5 bg-white border border-slate-300 rounded-lg text-sm text-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-500', 'placeholder': 'e.g. Associate Software Engineer'}),
            'description': forms.Textarea(attrs={'class': 'w-full px-3.5 py-2.5 bg-white border border-slate-300 rounded-lg text-sm text-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-500', 'rows': 4}),
            'requirements': forms.Textarea(attrs={'class': 'w-full px-3.5 py-2.5 bg-white border border-slate-300 rounded-lg text-sm text-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-500', 'rows': 3}),
            'min_cgpa': forms.NumberInput(attrs={'class': 'w-full px-3.5 py-2.5 bg-white border border-slate-300 rounded-lg text-sm text-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-500', 'step': '0.1'}),
            'max_backlogs': forms.NumberInput(attrs={'class': 'w-full px-3.5 py-2.5 bg-white border border-slate-300 rounded-lg text-sm text-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-500'}),
            'package_lpa': forms.NumberInput(attrs={'class': 'w-full px-3.5 py-2.5 bg-white border border-slate-300 rounded-lg text-sm text-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-500', 'step': '0.1'}),
            'location': forms.TextInput(attrs={'class': 'w-full px-3.5 py-2.5 bg-white border border-slate-300 rounded-lg text-sm text-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-500', 'placeholder': 'e.g. Bengaluru, Remote, Hyderabad'}),
            'deadline': forms.DateTimeInput(attrs={'class': 'w-full px-3.5 py-2.5 bg-white border border-slate-300 rounded-lg text-sm text-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-500', 'type': 'datetime-local'}),
            'status': forms.Select(attrs={'class': 'w-full px-3.5 py-2.5 bg-white border border-slate-300 rounded-lg text-sm text-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-500'}),
            'required_skills': forms.SelectMultiple(attrs={'class': 'w-full px-3.5 py-2.5 bg-white border border-slate-300 rounded-lg text-sm text-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-500', 'size': 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            if isinstance(self.instance.allowed_branches, list):
                self.fields['branches_input'].initial = ", ".join(self.instance.allowed_branches)
            elif isinstance(self.instance.allowed_branches, str):
                self.fields['branches_input'].initial = self.instance.allowed_branches

    def clean_branches_input(self):
        val = self.cleaned_data.get('branches_input', '')
        if val:
            return [b.strip() for b in val.split(',') if b.strip()]
        return []

    def save(self, commit=True, company=None):
        job = super().save(commit=False)
        if company:
            job.company = company
        job.allowed_branches = self.cleaned_data.get('branches_input', [])
        if commit:
            job.save()
            self.save_m2m()

            # Process extra comma-separated skills
            skills_text = self.cleaned_data.get('skills_input', '')
            if skills_text:
                for name in [s.strip() for s in skills_text.split(',') if s.strip()]:
                    skill_obj, _ = Skill.objects.get_or_create(
                        name__iexact=name,
                        defaults={'name': name, 'category': 'General'}
                    )
                    job.required_skills.add(skill_obj)
        return job


class InterviewScheduleForm(forms.ModelForm):
    class Meta:
        model = Interview
        fields = [
            'round_type',
            'mode',
            'scheduled_at',
            'link_or_venue',
        ]
        widgets = {
            'round_type': forms.TextInput(attrs={'class': 'w-full px-3.5 py-2.5 bg-white border border-slate-300 rounded-lg text-sm text-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-500', 'placeholder': 'e.g. Technical Round 1, System Design, HR'}),
            'mode': forms.Select(attrs={'class': 'w-full px-3.5 py-2.5 bg-white border border-slate-300 rounded-lg text-sm text-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-500'}),
            'scheduled_at': forms.DateTimeInput(attrs={'class': 'w-full px-3.5 py-2.5 bg-white border border-slate-300 rounded-lg text-sm text-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-500', 'type': 'datetime-local'}),
            'link_or_venue': forms.TextInput(attrs={'class': 'w-full px-3.5 py-2.5 bg-white border border-slate-300 rounded-lg text-sm text-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-500', 'placeholder': 'e.g. https://meet.google.com/xyz or Main Conference Hall B'}),
        }
