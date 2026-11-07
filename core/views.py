from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.views.decorators.http import require_POST
from django.db.models import Count, Avg, Q

from accounts.decorators import role_required
from accounts.models import User
from students.models import StudentProfile
from recruiters.models import Company, set_recruiter_approval
from jobs.models import Job
from applications.models import Application
from placements.models import PlacementRecord
from core.forms import PlacementRecordCreateForm


def landing_page(request):
    """
    Renders public landing page for PlacementHub.
    """
    return render(request, 'core/landing.html')


@role_required('ADMIN')
def admin_dashboard_view(request):
    """
    Admin dashboard with core metrics:
    total students, total recruiters, active jobs, placement rate %,
    plus quick insights on pending approvals.
    """
    total_students = StudentProfile.objects.count()
    total_recruiters = Company.objects.count()
    active_jobs = Job.objects.filter(status='OPEN').count()

    placed_count = StudentProfile.objects.filter(placement_status='PLACED').count()
    placement_rate = round((placed_count / total_students) * 100, 1) if total_students > 0 else 0.0

    pending_students_count = StudentProfile.objects.filter(is_verified=False).count()
    pending_recruiters_count = Company.objects.filter(is_approved=False).count()
    total_placements_count = PlacementRecord.objects.count()

    recent_placements = PlacementRecord.objects.select_related(
        'student', 'company', 'application__job'
    ).order_by('-id')[:5]

    recent_jobs = Job.objects.select_related('company').order_by('-created_at')[:5]

    context = {
        'total_students': total_students,
        'total_recruiters': total_recruiters,
        'active_jobs': active_jobs,
        'placement_rate': placement_rate,
        'placed_count': placed_count,
        'pending_students_count': pending_students_count,
        'pending_recruiters_count': pending_recruiters_count,
        'total_placements_count': total_placements_count,
        'recent_placements': recent_placements,
        'recent_jobs': recent_jobs,
    }
    return render(request, 'core/admin_dashboard.html', context)


@role_required('ADMIN')
def admin_students_view(request):
    """
    List all StudentProfiles with verification filter/search and verify/unverify toggle.
    """
    search_query = request.GET.get('q', '').strip()
    status_filter = request.GET.get('status', '').strip()
    branch_filter = request.GET.get('branch', '').strip()

    students = StudentProfile.objects.select_related('user').all()

    if search_query:
        students = students.filter(
            Q(full_name__icontains=search_query) |
            Q(roll_no__icontains=search_query) |
            Q(user__email__icontains=search_query)
        )

    if status_filter == 'verified':
        students = students.filter(is_verified=True)
    elif status_filter == 'unverified':
        students = students.filter(is_verified=False)

    if branch_filter:
        students = students.filter(branch__iexact=branch_filter)

    students = students.order_by('-user__date_joined')
    branches = StudentProfile.objects.values_list('branch', flat=True).distinct()

    context = {
        'students': students,
        'search_query': search_query,
        'status_filter': status_filter,
        'branch_filter': branch_filter,
        'branches': [b for b in branches if b],
    }
    return render(request, 'core/admin_students.html', context)


@role_required('ADMIN')
@require_POST
def admin_student_toggle_verify_view(request, student_id):
    """
    Toggle is_verified on a StudentProfile.
    """
    student = get_object_or_404(StudentProfile, id=student_id)
    student.is_verified = not student.is_verified
    student.save(update_fields=['is_verified'])

    state_str = "verified" if student.is_verified else "marked unverified"
    messages.success(request, f"Student {student.full_name} ({student.roll_no}) {state_str}.")

    next_url = request.POST.get('next') or request.META.get('HTTP_REFERER') or 'core:admin_students'
    return redirect(next_url)


@role_required('ADMIN')
def admin_recruiters_view(request):
    """
    List all Companies with approve/reject toggle.
    """
    search_query = request.GET.get('q', '').strip()
    status_filter = request.GET.get('status', '').strip()

    recruiters = Company.objects.select_related('user').all()

    if search_query:
        recruiters = recruiters.filter(
            Q(company_name__icontains=search_query) |
            Q(industry__icontains=search_query) |
            Q(user__email__icontains=search_query)
        )

    if status_filter == 'approved':
        recruiters = recruiters.filter(is_approved=True)
    elif status_filter == 'pending':
        recruiters = recruiters.filter(is_approved=False)

    recruiters = recruiters.order_by('-user__date_joined')

    context = {
        'recruiters': recruiters,
        'search_query': search_query,
        'status_filter': status_filter,
    }
    return render(request, 'core/admin_recruiters.html', context)


@role_required('ADMIN')
@require_POST
def admin_recruiter_toggle_approval_view(request, company_id):
    """
    Toggle is_approved on a Company using the single write path set_recruiter_approval.
    """
    company = get_object_or_404(Company, id=company_id)
    new_state = not company.is_approved
    set_recruiter_approval(company, new_state)

    state_str = "approved" if new_state else "rejected / revoked"
    messages.success(request, f"Company {company.company_name} {state_str}.")

    next_url = request.POST.get('next') or request.META.get('HTTP_REFERER') or 'core:admin_recruiters'
    return redirect(next_url)


@role_required('ADMIN')
def admin_approvals_view(request):
    """
    Combined approvals view: pending students + pending recruiters with inline actions.
    """
    pending_students = StudentProfile.objects.filter(is_verified=False).select_related('user').order_by('-user__date_joined')
    pending_recruiters = Company.objects.filter(is_approved=False).select_related('user').order_by('-user__date_joined')

    context = {
        'pending_students': pending_students,
        'pending_recruiters': pending_recruiters,
    }
    return render(request, 'core/admin_approvals.html', context)


@role_required('ADMIN')
def admin_placements_view(request):
    """
    List all placement records with key candidate and offer details.
    """
    records = PlacementRecord.objects.select_related(
        'student', 'company', 'application__job'
    ).order_by('-offer_date', '-id')

    context = {
        'records': records,
        'total_count': records.count(),
        'avg_package': records.aggregate(Avg('package_lpa'))['package_lpa__avg'] or 0.0,
    }
    return render(request, 'core/admin_placements.html', context)


@role_required('ADMIN')
def admin_placement_create_view(request):
    """
    Create placement record from Selected unplaced application.
    Derives student, company, and job automatically from the application.
    """
    if request.method == 'POST':
        form = PlacementRecordCreateForm(request.POST)
        if form.is_valid():
            record = form.save()
            messages.success(
                request,
                f"Placement record created for {record.student.full_name} at {record.company.company_name} (₹{record.package_lpa} LPA)!"
            )
            return redirect('core:admin_placements')
    else:
        form = PlacementRecordCreateForm()

    eligible_count = form.fields['application'].queryset.count()

    context = {
        'form': form,
        'eligible_count': eligible_count,
    }
    return render(request, 'core/admin_placement_create.html', context)


@role_required('ADMIN')
def admin_reports_view(request):
    """
    Reports view:
    - placements by branch
    - application status breakdown
    - top 5 companies by jobs posted
    """
    placements_by_branch = list(
        PlacementRecord.objects.values('student__branch')
        .annotate(count=Count('id'), avg_package=Avg('package_lpa'))
        .order_by('-count')
    )

    application_status_breakdown = list(
        Application.objects.values('status')
        .annotate(count=Count('id'))
        .order_by('-count')
    )

    top_companies = list(
        Company.objects.annotate(jobs_count=Count('jobs'))
        .filter(jobs_count__gt=0)
        .order_by('-jobs_count')[:5]
    )

    total_applications = Application.objects.count()
    total_placements = PlacementRecord.objects.count()
    overall_avg_package = PlacementRecord.objects.aggregate(Avg('package_lpa'))['package_lpa__avg'] or 0.0

    context = {
        'placements_by_branch': placements_by_branch,
        'application_status_breakdown': application_status_breakdown,
        'top_companies': top_companies,
        'total_applications': total_applications,
        'total_placements': total_placements,
        'overall_avg_package': round(overall_avg_package, 2),
    }
    return render(request, 'core/admin_reports.html', context)
