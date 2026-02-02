from django.contrib import admin
from .models import TeacherProfile, SchoolClass, Student, Attendance, AttendanceRecord,Subject,Term,Marks,DiaryEntry,StudentComplaint,ComplaintSubject,Fee,FeeAudit,TeacherSalary,StudentCharge

admin.site.register(TeacherProfile)
admin.site.register(SchoolClass)
admin.site.register(Student)
admin.site.register(Attendance)
admin.site.register(AttendanceRecord)
admin.site.register(Subject)
admin.site.register(Term)
admin.site.register(Marks)
admin.site.register(DiaryEntry)
admin.site.register(StudentComplaint)
admin.site.register(ComplaintSubject)
admin.site.register(Fee)
admin.site.register(FeeAudit)
admin.site.register(TeacherSalary)
admin.site.register(StudentCharge)
