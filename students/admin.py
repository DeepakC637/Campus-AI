from django.contrib import admin
from .models import StudentProfile, Resume, Skill


@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'roll_no', 'branch', 'year', 'cgpa', 'is_verified', 'placement_status')
    list_filter = ('branch', 'year', 'is_verified', 'placement_status')
    search_fields = ('full_name', 'roll_no', 'user__email')
    filter_horizontal = ('skills',)


@admin.register(Resume)
class ResumeAdmin(admin.ModelAdmin):
    list_display = ('student', 'is_active', 'uploaded_at')
    list_filter = ('is_active', 'uploaded_at')
    search_fields = ('student__full_name', 'student__roll_no')


@admin.register(Skill)
class SkillAdmin(admin.ModelAdmin):
    list_display = ('name', 'category')
    list_filter = ('category',)
    search_fields = ('name',)
