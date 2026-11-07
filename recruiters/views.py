from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.http import HttpResponseBadRequest
from django.utils import timezone
from django.db.models import Count
from accounts.decorators import role_required
from .models import Company
from .forms import CompanyProfileForm, JobPostForm, InterviewScheduleForm
from jobs.models import Job
from applications.models import Application
from interviews.models import Interview


def get_recruiter_company(user):
    """Retrieve or create company profile for current recruiter user."""
    company, _ = Company.objects.get_or_create(
        user=user,
        defaults={
            'company_name': f"{user.first_name}'s Enterprise".strip() or f"Company-{user.id}",
            'industry': 'Technology',
            'contact_person': f"{user.first_name} {user.last_name}".strip() or user.email,
            'is_approved': user.is_approved,
        }
    )
    return company


@role_required('RECRUITER')
def dashboard_view(request):
    """Recruiter dashboard overview."""
    company = get_recruiter_company(request.user)

    active_jobs = company.jobs.filter(status=Job.Status.OPEN, deadline__gte=timezone.now()).count()
    total_applicants = Application.objects.filter(job__company=company).count()
    shortlisted_count = Application.objects.filter(job__company=company, status=Application.Status.SHORTLISTED).count()
    interviews_scheduled = Interview.objects.filter(
        application__job__company=company,
        status=Interview.Status.SCHEDULED
    ).count()

    # List of recruiter's own posted jobs with applicant counts
    posted_jobs = company.jobs.annotate(
        applicant_count=Count('applications')
    ).order_by('-created_at')

    context = {
        'active_tab': 'dashboard',
        'company': company,
        'active_jobs': active_jobs,
        'total_applicants': total_applicants,
        'shortlisted_count': shortlisted_count,
        'interviews_scheduled': interviews_scheduled,
        'posted_jobs': posted_jobs,
    }
    return render(request, 'recruiters/dashboard.html', context)


@role_required('RECRUITER')
def profile_view(request):
    """View and edit company profile."""
    company = get_recruiter_company(request.user)

    if request.method == 'POST':
        form = CompanyProfileForm(request.POST, request.FILES, instance=company)
        if form.is_valid():
            form.save()
            messages.success(request, "Company profile updated successfully.")
            return redirect('recruiters:profile')
    else:
        form = CompanyProfileForm(instance=company)

    context = {
        'active_tab': 'profile',
        'company': company,
        'form': form,
    }
    return render(request, 'recruiters/profile.html', context)


@role_required('RECRUITER')
def jobs_view(request):
    """List strictly this recruiter's own job postings."""
    company = get_recruiter_company(request.user)
    jobs = company.jobs.annotate(
        applicant_count=Count('applications')
    ).order_by('-created_at')

    context = {
        'active_tab': 'jobs',
        'company': company,
        'jobs': jobs,
    }
    return render(request, 'recruiters/jobs.html', context)


@role_required('RECRUITER')
def job_create_view(request):
    """Post a new job. Company is auto-set from request.user, never from form input."""
    company = get_recruiter_company(request.user)

    if request.method == 'POST':
        form = JobPostForm(request.POST)
        if form.is_valid():
            job = form.save(company=company)
            messages.success(request, f"Job drive '{job.title}' posted successfully!")
            return redirect('recruiters:jobs')
    else:
        form = JobPostForm()

    context = {
        'active_tab': 'jobs',
        'company': company,
        'form': form,
        'is_edit': False,
    }
    return render(request, 'recruiters/post_job.html', context)


@role_required('RECRUITER')
def job_edit_view(request, pk):
    """Edit existing job. Returns 403 if job does not belong to this recruiter."""
    company = get_recruiter_company(request.user)
    job = get_object_or_404(Job, pk=pk)

    if job.company != company:
        raise PermissionDenied("You do not own this job posting.")

    if request.method == 'POST':
        form = JobPostForm(request.POST, instance=job)
        if form.is_valid():
            form.save(company=company)
            messages.success(request, f"Job drive '{job.title}' updated successfully.")
            return redirect('recruiters:jobs')
    else:
        form = JobPostForm(instance=job)

    context = {
        'active_tab': 'jobs',
        'company': company,
        'job': job,
        'form': form,
        'is_edit': True,
    }
    return render(request, 'recruiters/post_job.html', context)


@role_required('RECRUITER')
def job_applicants_view(request, pk):
    """List applications for a job. Returns 403 if job is not this recruiter's."""
    company = get_recruiter_company(request.user)
    job = get_object_or_404(Job, pk=pk)

    if job.company != company:
        raise PermissionDenied("You do not have permission to view applicants for this job.")

    applicants = job.applications.select_related(
        'student', 'student__user'
    ).prefetch_related('student__skills', 'interviews').order_by('-applied_at')

    context = {
        'active_tab': 'jobs',
        'company': company,
        'job': job,
        'applicants': applicants,
        'allowed_statuses': ['Applied', 'Shortlisted', 'Interview', 'Selected', 'Rejected'],
    }
    return render(request, 'recruiters/applicants.html', context)


@role_required('RECRUITER')
def update_application_status_view(request, pk):
    """
    Update application status.
    Must belong to recruiter's job.
    NEVER allow setting status to 'Withdrawn'.
    """
    if request.method != 'POST':
        return redirect('recruiters:jobs')

    company = get_recruiter_company(request.user)
    application = get_object_or_404(Application.objects.select_related('job', 'student'), pk=pk)

    if application.job.company != company:
        raise PermissionDenied("You do not have permission to update this application.")

    new_status = request.POST.get('status')

    # Security check: Recruiter cannot set status to "Withdrawn"
    if new_status == Application.Status.WITHDRAWN:
        return HttpResponseBadRequest("Recruiters cannot set application status to 'Withdrawn'.")

    valid_statuses = [
        Application.Status.APPLIED,
        Application.Status.SHORTLISTED,
        Application.Status.INTERVIEW,
        Application.Status.SELECTED,
        Application.Status.REJECTED,
    ]

    if new_status in valid_statuses:
        application.status = new_status
        application.save()
        messages.success(request, f"Status for {application.student.full_name} updated to {new_status}.")
    else:
        messages.error(request, f"Invalid application status: '{new_status}'")

    return redirect('recruiters:job_applicants', pk=application.job.pk)


@role_required('RECRUITER')
def schedule_interview_view(request, pk):
    """
    Schedule interview for applicant.
    Only permitted if job belongs to this recruiter's company,
    and application status is Shortlisted or Interview.
    """
    company = get_recruiter_company(request.user)
    application = get_object_or_404(
        Application.objects.select_related('job', 'job__company', 'student'),
        pk=pk
    )

    # Ownership check
    if application.job.company != company:
        raise PermissionDenied("You do not have access to schedule interviews for this applicant.")

    # Status gate check: only Shortlisted or Interview
    if application.status not in [Application.Status.SHORTLISTED, Application.Status.INTERVIEW]:
        return HttpResponseBadRequest(
            f"Interviews can only be scheduled for candidates in 'Shortlisted' or 'Interview' stage. Current stage: '{application.status}'"
        )

    if request.method == 'POST':
        form = InterviewScheduleForm(request.POST)
        if form.is_valid():
            interview = form.save(commit=False)
            interview.application = application
            interview.status = Interview.Status.SCHEDULED
            interview.save()

            # Advance status to Interview if currently Shortlisted
            if application.status == Application.Status.SHORTLISTED:
                application.status = Application.Status.INTERVIEW
                application.save()

            messages.success(request, f"Interview round '{interview.round_type}' scheduled for {application.student.full_name}!")
            return redirect('recruiters:job_applicants', pk=application.job.pk)
    else:
        form = InterviewScheduleForm(initial={
            'scheduled_at': timezone.now() + timezone.timedelta(days=2),
            'mode': Interview.Mode.ONLINE,
        })

    context = {
        'active_tab': 'jobs',
        'company': company,
        'application': application,
        'form': form,
    }
    return render(request, 'recruiters/interview.html', context)
