from django import forms
from django.core.exceptions import ValidationError
from .models import StudentProfile, Resume, Skill


class StudentProfileForm(forms.ModelForm):
    # Field to allow adding new skills as comma-separated text
    skills_text = forms.CharField(
        required=False,
        label="Add Skills (comma-separated)",
        help_text="e.g. Python, Django, SQL, React",
        widget=forms.TextInput(attrs={
            'class': 'w-full px-3.5 py-2.5 bg-white border border-slate-300 rounded-lg text-sm text-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent',
            'placeholder': 'Python, Django, Machine Learning...'
        })
    )

    class Meta:
        model = StudentProfile
        fields = [
            'full_name',
            'roll_no',
            'branch',
            'year',
            'cgpa',
            'backlogs',
            'phone',
            'placement_status',
        ]
        widgets = {
            'full_name': forms.TextInput(attrs={'class': 'w-full px-3.5 py-2.5 bg-white border border-slate-300 rounded-lg text-sm text-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-500'}),
            'roll_no': forms.TextInput(attrs={'class': 'w-full px-3.5 py-2.5 bg-white border border-slate-300 rounded-lg text-sm text-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-500'}),
            'branch': forms.TextInput(attrs={'class': 'w-full px-3.5 py-2.5 bg-white border border-slate-300 rounded-lg text-sm text-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-500', 'placeholder': 'e.g. Computer Science, Mechanical'}),
            'year': forms.NumberInput(attrs={'class': 'w-full px-3.5 py-2.5 bg-white border border-slate-300 rounded-lg text-sm text-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-500'}),
            'cgpa': forms.NumberInput(attrs={'class': 'w-full px-3.5 py-2.5 bg-white border border-slate-300 rounded-lg text-sm text-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-500', 'step': '0.01'}),
            'backlogs': forms.NumberInput(attrs={'class': 'w-full px-3.5 py-2.5 bg-white border border-slate-300 rounded-lg text-sm text-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-500'}),
            'phone': forms.TextInput(attrs={'class': 'w-full px-3.5 py-2.5 bg-white border border-slate-300 rounded-lg text-sm text-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-500'}),
            'placement_status': forms.Select(
                choices=[('UNPLACED', 'Unplaced'), ('PLACED', 'Placed'), ('OPTED_OUT', 'Opted Out')],
                attrs={'class': 'w-full px-3.5 py-2.5 bg-white border border-slate-300 rounded-lg text-sm text-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-500'}
            ),
        }

    def save(self, commit=True):
        profile = super().save(commit=commit)
        skills_text = self.cleaned_data.get('skills_text', '')
        if skills_text:
            skill_names = [s.strip() for s in skills_text.split(',') if s.strip()]
            for name in skill_names:
                skill_obj, _ = Skill.objects.get_or_create(
                    name__iexact=name,
                    defaults={'name': name, 'category': 'General'}
                )
                profile.skills.add(skill_obj)
        return profile


class ResumeUploadForm(forms.Form):
    file = forms.FileField(
        required=True,
        widget=forms.FileInput(attrs={
            'accept': '.pdf,.docx,.doc',
            'class': 'block w-full text-sm text-slate-500 file:mr-4 file:py-2.5 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100 cursor-pointer'
        })
    )

    def clean_file(self):
        uploaded_file = self.cleaned_data['file']
        ext = uploaded_file.name.split('.')[-1].lower()
        if ext not in ['pdf', 'docx', 'doc']:
            raise ValidationError("Unsupported file format. Please upload a PDF or DOCX file.")
        if uploaded_file.size > 10 * 1024 * 1024:  # 10 MB limit
            raise ValidationError("File size exceeds 10MB limit.")
        return uploaded_file

