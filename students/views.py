import os
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import HttpResponseBadRequest, HttpResponseForbidden
from django.utils import timezone
from django.db.models import Q
from accounts.decorators import role_required
from .models import StudentProfile, Resume, Skill
from .forms import StudentProfileForm, ResumeUploadForm
from jobs.models import Job
from applications.models import Application
from interviews.models import Interview
from ai_engine.parsing import extract_text, extract_skills


def get_student_profile(user):
    """Retrieve or create the student profile for the current user."""
    profile, _ = StudentProfile.objects.get_or_create(
        user=user,
        defaults={
            'full_name': f"{user.first_name} {user.last_name}".strip() or user.username,
            'roll_no': f"STU-{user.id:04d}",
            'branch': 'Computer Science',
            'year': timezone.now().year,
        }
    )
    return profile


def check_job_eligibility(student, job):
    """
    Check if a student satisfies a job's eligibility criteria:
    - Minimum CGPA
    - Maximum backlogs
    - Allowed branches
    Returns: (is_eligible: bool, reasons: list[str])
    """
    reasons = []

    # CGPA check
    if student.cgpa < job.min_cgpa:
        reasons.append(f"CGPA ({student.cgpa:.2f}) is below the required minimum ({job.min_cgpa:.2f})")

    # Backlogs check
    if student.backlogs > job.max_backlogs:
        reasons.append(f"Active backlogs ({student.backlogs}) exceed the allowed maximum ({job.max_backlogs})")

    # Allowed branches check
    allowed = job.allowed_branches
    if allowed:
        if isinstance(allowed, list):
            branch_list = [str(b).strip().lower() for b in allowed]
        elif isinstance(allowed, str):
            branch_list = [b.strip().lower() for b in allowed.split(',') if b.strip()]
        else:
            branch_list = []

        student_branch = student.branch.strip().lower()
        if branch_list and student_branch not in branch_list:
            display_allowed = ", ".join(allowed) if isinstance(allowed, list) else allowed
            reasons.append(f"Branch '{student.branch}' is not eligible. Allowed: {display_allowed}")

    is_eligible = len(reasons) == 0
    return is_eligible, reasons


@role_required('STUDENT')
def dashboard_view(request):
    """Student dashboard overview."""
    student = get_student_profile(request.user)
    completion_percentage = student.get_profile_completion_percentage()

    # Application stats
    applied_job_ids = list(student.applications.values_list('job_id', flat=True))
    jobs_applied_count = len(applied_job_ids)

    # Interviews count
    interviews_scheduled_count = Interview.objects.filter(
        application__student=student,
        status=Interview.Status.SCHEDULED
    ).count()

    # Status counts breakdown
    status_counts = {
        'Applied': student.applications.filter(status=Application.Status.APPLIED).count(),
        'Shortlisted': student.applications.filter(status=Application.Status.SHORTLISTED).count(),
        'Interview': student.applications.filter(status=Application.Status.INTERVIEW).count(),
        'Selected': student.applications.filter(status=Application.Status.SELECTED).count(),
        'Rejected': student.applications.filter(status=Application.Status.REJECTED).count(),
        'Withdrawn': student.applications.filter(status=Application.Status.WITHDRAWN).count(),
    }

    # Open jobs not yet applied to
    open_jobs = Job.objects.filter(
        status=Job.Status.OPEN,
        deadline__gte=timezone.now()
    ).exclude(
        id__in=applied_job_ids
    ).select_related('company').prefetch_related('required_skills').order_by('deadline')[:10]

    # Annotate open jobs with eligibility
    for job in open_jobs:
        job.is_eligible, job.ineligibility_reasons = check_job_eligibility(student, job)

    context = {
        'active_tab': 'dashboard',
        'student': student,
        'completion_percentage': completion_percentage,
        'jobs_applied_count': jobs_applied_count,
        'interviews_scheduled_count': interviews_scheduled_count,
        'status_counts': status_counts,
        'open_jobs': open_jobs,
    }
    return render(request, 'students/dashboard.html', context)


@role_required('STUDENT')
def profile_view(request):
    """View and edit student profile and manage skills."""
    student = get_student_profile(request.user)

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'remove_skill':
            skill_id = request.POST.get('skill_id')
            if skill_id:
                student.skills.remove(skill_id)
                messages.success(request, "Skill removed from your profile.")
            return redirect('students:profile')

        form = StudentProfileForm(request.POST, instance=student)
        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated successfully.")
            return redirect('students:profile')
    else:
        form = StudentProfileForm(instance=student)

    skills = student.skills.all()
    context = {
        'active_tab': 'profile',
        'student': student,
        'form': form,
        'skills': skills,
    }
    return render(request, 'students/profile.html', context)


@role_required('STUDENT')
def resume_view(request):
    """Upload resume (PDF/DOCX) and view resume history."""
    student = get_student_profile(request.user)

    if request.method == 'POST':
        form = ResumeUploadForm(request.POST, request.FILES)
        if form.is_valid():
            # Mark previous active resumes as inactive
            student.resumes.filter(is_active=True).update(is_active=False)

            # Create new active resume
            new_resume = Resume.objects.create(
                student=student,
                file=form.cleaned_data['file'],
                is_active=True,
                extracted_text="",
                parsed_skills=[],
            )

            # Extract text and skills from the uploaded resume file
            file_ext = os.path.splitext(new_resume.file.name)[1]
            extracted_text = extract_text(new_resume.file.path, file_ext)
            matched_skills = extract_skills(extracted_text, Skill.objects.all())

            new_resume.extracted_text = extracted_text
            new_resume.parsed_skills = matched_skills
            new_resume.save()

            # Add matched skills to student profile without removing existing manual skills
            if matched_skills:
                skills_to_add = Skill.objects.filter(name__in=matched_skills)
                student.skills.add(*skills_to_add)

            messages.success(request, f"Resume '{new_resume.file.name}' uploaded successfully.")
            return redirect('students:resume')
    else:
        form = ResumeUploadForm()

    resumes = student.resumes.order_by('-uploaded_at')
    active_resume = resumes.filter(is_active=True).first()

    context = {
        'active_tab': 'resume',
        'student': student,
        'form': form,
        'resumes': resumes,
        'active_resume': active_resume,
    }
    return render(request, 'students/resume.html', context)


@role_required('STUDENT')
def jobs_view(request):
    """Browse open job postings with filters and eligibility badges."""
    student = get_student_profile(request.user)

    jobs_qs = Job.objects.filter(
        status=Job.Status.OPEN,
        deadline__gte=timezone.now()
    ).select_related('company').prefetch_related('required_skills').order_by('deadline')

    # Filters
    search_query = request.GET.get('search', '').strip()
    if search_query:
        jobs_qs = jobs_qs.filter(
            Q(title__icontains=search_query) |
            Q(company__company_name__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(requirements__icontains=search_query)
        )

    location_filter = request.GET.get('location', '').strip()
    if location_filter:
        jobs_qs = jobs_qs.filter(location__icontains=location_filter)

    branch_filter = request.GET.get('branch', '').strip()
    if branch_filter:
        jobs_qs = jobs_qs.filter(allowed_branches__icontains=branch_filter)

    applied_job_ids = set(student.applications.values_list('job_id', flat=True))

    jobs_list = list(jobs_qs)
    for job in jobs_list:
        job.is_eligible, job.ineligibility_reasons = check_job_eligibility(student, job)
        job.has_applied = job.id in applied_job_ids

    # Extract distinct locations for filter dropdown
    all_locations = Job.objects.filter(
        status=Job.Status.OPEN,
        deadline__gte=timezone.now()
    ).values_list('location', flat=True).distinct()

    context = {
        'active_tab': 'jobs',
        'student': student,
        'jobs': jobs_list,
        'search_query': search_query,
        'location_filter': location_filter,
        'branch_filter': branch_filter,
        'all_locations': sorted(set(filter(None, all_locations))),
    }
    return render(request, 'students/jobs.html', context)


@role_required('STUDENT')
def job_detail_view(request, pk):
    """View comprehensive job details and eligibility checklist."""
    student = get_student_profile(request.user)
    job = get_object_or_404(
        Job.objects.select_related('company').prefetch_related('required_skills'),
        pk=pk
    )

    has_applied = Application.objects.filter(student=student, job=job).exists()
    is_eligible, ineligibility_reasons = check_job_eligibility(student, job)

    # Detailed criteria checks for UI checklist
    cgpa_pass = student.cgpa >= job.min_cgpa
    backlogs_pass = student.backlogs <= job.max_backlogs

    allowed = job.allowed_branches
    if allowed:
        if isinstance(allowed, list):
            b_list = [str(b).strip().lower() for b in allowed]
        elif isinstance(allowed, str):
            b_list = [b.strip().lower() for b in allowed.split(',') if b.strip()]
        else:
            b_list = []
        branch_pass = student.branch.strip().lower() in b_list if b_list else True
    else:
        branch_pass = True

    context = {
        'active_tab': 'jobs',
        'student': student,
        'job': job,
        'has_applied': has_applied,
        'is_eligible': is_eligible,
        'ineligibility_reasons': ineligibility_reasons,
        'cgpa_pass': cgpa_pass,
        'backlogs_pass': backlogs_pass,
        'branch_pass': branch_pass,
    }
    return render(request, 'students/job_detail.html', context)


@role_required('STUDENT')
def apply_job_view(request, pk):
    """Apply to a job if eligible and deadline has not passed."""
    if request.method != 'POST':
        return redirect('students:job_detail', pk=pk)

    student = get_student_profile(request.user)
    job = get_object_or_404(Job, pk=pk)

    # Verify job status and deadline
    if job.status != Job.Status.OPEN or job.deadline < timezone.now():
        messages.error(request, "This job is closed or the application deadline has passed.")
        return redirect('students:job_detail', pk=pk)

    # Verify not already applied
    if Application.objects.filter(student=student, job=job).exists():
        messages.warning(request, "You have already applied for this job.")
        return redirect('students:job_detail', pk=pk)

    # Verify eligibility (server-side enforcement)
    is_eligible, reasons = check_job_eligibility(student, job)
    if not is_eligible:
        reason_msg = "; ".join(reasons)
        messages.error(request, f"Application rejected: You do not meet the eligibility criteria ({reason_msg}).")
        return HttpResponseForbidden(f"Ineligible: {reason_msg}")

    # Create application
    Application.objects.create(
        student=student,
        job=job,
        status=Application.Status.APPLIED,
    )
    messages.success(request, f"Application submitted successfully for {job.title} at {job.company.company_name}!")
    return redirect('students:applications')


@role_required('STUDENT')
def applications_view(request):
    """Application tracker view."""
    student = get_student_profile(request.user)
    applications = student.applications.select_related('job', 'job__company').order_by('-applied_at')

    context = {
        'active_tab': 'applications',
        'student': student,
        'applications': applications,
    }
    return render(request, 'students/applications.html', context)


@role_required('STUDENT')
def withdraw_application_view(request, pk):
    """Allow withdrawal only from 'Applied' or 'Shortlisted' status."""
    if request.method != 'POST':
        return redirect('students:applications')

    student = get_student_profile(request.user)
    application = get_object_or_404(Application, pk=pk, student=student)

    if application.status in [Application.Status.APPLIED, Application.Status.SHORTLISTED]:
        application.status = Application.Status.WITHDRAWN
        application.save()
        messages.success(request, f"Application for '{application.job.title}' was withdrawn successfully.")
    else:
        messages.error(request, f"Cannot withdraw application in '{application.status}' stage.")
        return HttpResponseBadRequest(f"Cannot withdraw from status '{application.status}'")

    return redirect('students:applications')


@role_required('STUDENT')
def interviews_view(request):
    """View upcoming and past interviews linked to student applications."""
    student = get_student_profile(request.user)
    interviews = Interview.objects.filter(
        application__student=student
    ).select_related('application__job', 'application__job__company').order_by('scheduled_at')

    context = {
        'active_tab': 'interviews',
        'student': student,
        'interviews': interviews,
    }
    return render(request, 'students/interviews.html', context)


@role_required('STUDENT')
def skill_gap_view(request, job_id):
    """Skill gap analysis comparing student profile skills with job required skills."""
    student = get_student_profile(request.user)
    job = get_object_or_404(
        Job.objects.select_related('company').prefetch_related('required_skills'),
        pk=job_id
    )

    student_skill_names = set(student.skills.values_list('name', flat=True))
    student_skill_lower = {s.lower(): s for s in student_skill_names}

    job_required_skills = list(job.required_skills.all())

    matched_skills = []
    missing_skills = []

    for skill in job_required_skills:
        if skill.name.lower() in student_skill_lower:
            matched_skills.append(skill.name)
        else:
            missing_skills.append(skill.name)

    total_required = len(job_required_skills)
    if total_required > 0:
        match_percentage = int((len(matched_skills) / total_required) * 100)
    else:
        match_percentage = 100

    context = {
        'active_tab': 'jobs',
        'student': student,
        'job': job,
        'student_skills': sorted(student_skill_names),
        'matched_skills': matched_skills,
        'missing_skills': missing_skills,
        'match_percentage': match_percentage,
    }
    return render(request, 'students/skill_gap.html', context)
