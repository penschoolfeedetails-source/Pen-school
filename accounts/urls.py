from django.urls import path
from . import views

urlpatterns = [
    # Authentication
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),

    # Dashboards
    path('dashboard/', views.dashboard, name='dashboard'),
    path('teacher/', views.teacher_dashboard, name='teacher_dashboard'),
    path('finance/', views.finance_dashboard, name='finance_dashboard'),
    path('principal/', views.principal_dashboard, name='principal_dashboard'),

    # Teacher management
    path('finance/create-teacher/', views.create_teacher, name='create_teacher'),
    path('teacher/deactivate/<int:teacher_id>/', views.deactivate_teacher, name='deactivate_teacher'),

    # Diary
    path('diary/', views.enter_diary, name='enter_diary'),
    path('diary/view/', views.view_diary, name='view_diary'),
    path('diary/list/', views.diary_list_view, name='diary_list_view'),

# Diary download
path('diary/download/<int:school_class_id>/<str:diary_date>/', 
     views.download_diary, name='download_diary'),
    # Attendance
    path('attendance/select-class/', views.select_class, name='select_class'),
    path('attendance/mark/<int:class_id>/', views.mark_attendance, name='mark_attendance'),
    path('attendance/view/', views.view_attendance, name='view_attendance'),

    # Marks
    path('marks/select_class/', views.select_class_for_marks, name='select_class_for_marks'),
    path('marks/select_subject_term/<int:class_id>/', views.select_subject_term, name='select_subject_term'),
    path('marks/enter/<int:class_id>/<int:subject_id>/<int:term_id>/', views.enter_marks, name='enter_marks'),

    # Report Card
    path('report-card/select/', views.select_class_term, name='select_class_term'),
    path('report-card/students/<int:class_id>/<int:term_id>/', views.student_list_for_report, name='student_list_for_report'),
    path('report-card/<int:student_id>/<int:term_id>/', views.report_card_view, name='report_card'),
    
 # Report Card download (all students)
   # urls.py
# path('download-report-cards/<int:class_id>/<int:term_id>/', views.download_report_cards_zip, name='download_report_cards_zip'),
 path('annual-sub/', views.annual_sub_view, name='annual_sub'),
    path('annual-sub/update/<int:student_id>/', views.update_annual_sub, name='update_annual_sub'),


    # Extra Curricular Items
    path('report-card/<int:class_id>/<int:term_id>/add-extra/', views.add_extra_curricular_item, name='add_extra_curricular_item'),
    path("report-card/<int:class_id>/<int:term_id>/extra/remove/<int:item_id>/",views.remove_extra_from_report_card,name="remove_extra_from_report_card"),

    # Complaint Portal (Teacher)
    path('complaint/list/', views.teacher_complaints, name='teacher_complaint_list'),
    path('complaint/ajax/load-students-subjects/', views.load_students_and_subjects, name='load_students_subjects'),
    path('complaint/register/', views.register_complaint, name='register_complaint'),
    path('complaint/ajax/load-complaints/', views.load_complaints, name='load_complaints'),
    path('complaint/ajax/delete/<int:complaint_id>/', views.delete_complaint, name='delete_complaint'),
    path('complaints/', views.complaint_list, name='complaint_list'),
    path('complaints/student/<int:student_id>/', views.student_complaints, name='student_complaints'),
    #  path('save-personal-attributes/', views.save_personal_attributes, name='save_personal_attributes'),


    # Student management
    path('create-student/', views.create_student, name='create_student'),

    # Fee management
    path('fee-management/', views.fee_dashboard, name='fee_dashboard'),
    path('submit-fee/<int:student_id>/', views.submit_fee, name='submit_fee'),
    path('student/<int:student_id>/siblings/', views.get_siblings, name='get_siblings'),
    path('finance/daily-fee-report/', views.daily_fee_report, name='daily_fee_report'),
    path('finance/download-audit/<int:audit_id>/', views.download_fee_audit, name='download_fee_audit'),
    path('finance/pending-dues/', views.pending_dues, name='pending_dues'),

    # Subjects & Terms
    path('subjects/', views.subject_manage, name='subject_manage'),
    path('subjects/remove/<int:pk>/', views.remove_subject, name='remove_subject'),
    path('terms/', views.term_manage, name='term_manage'),
    path('terms/toggle/<int:term_id>/', views.toggle_term_current, name='toggle_term_current'),
    path('teacher/deactivate/<int:teacher_id>/', views.deactivate_teacher, name='deactivate_teacher'),
path('teacher/activate/<int:teacher_id>/', views.activate_teacher, name='activate_teacher'),
 path("generate-circular/", views.generate_circular, name="generate_circular"),
 path("circular-notice/", views.circular_notice_view, name="circular_notice_view"),

 path('principal/dashboard/', views.principal_notice_dashboard, name='principal_notice_dashboard'),
 path("dashboard/term-syllabus/", views.term_syllabus_dashboard, name="term_syllabus_dashboard"),
    path("ajax/add-syllabus-topic/", views.add_syllabus_topic_ajax, name="add_syllabus_topic_ajax"),
    path("ajax/remove-syllabus-topic/", views.remove_syllabus_topic_ajax, name="remove_syllabus_topic_ajax"),
    path('view-syllabus/', views.teacher_syllabus_dashboard, name='teacher_syllabus_dashboard'),
    # urls.py
path('principal/dashboard/delete/<int:notice_id>/', views.delete_notice, name='delete_notice'),
path('term/remove/<int:term_id>/', views.remove_term, name='remove_term'),
 path('principal/marks-status/',views.principal_marks_status,name='principal_marks_status'),

    # -----------------------------
    # Principal View Marks for Subject
    # -----------------------------
    path('principal/view-marks/<int:class_id>/<int:term_id>/<int:subject_id>/',views.principal_view_subject_marks,name='principal_view_subject_marks'),
    path('send-welcome-email/', views.send_welcome_email, name='send_welcome_email'),

     path('expenditure/', views.daily_expenditure, name='daily_expenditure'),
    path('expenditure/delete/<int:pk>/', views.delete_expenditure, name='delete_expenditure'),
    path('teacher_salary/', views.teacher_salary, name='teacher_salary'),
    path('teacher_salary/update/<int:pk>/', views.update_salary, name='update_salary'),
    path('teacher_salary/delete/<int:pk>/', views.delete_salary, name='delete_salary'),

  path('student-charges/', views.student_charge_view, name='student_charge'),
    path('student-charges/delete/<int:id>/', views.delete_student_charge, name='delete_student_charge'),
     path('ajax/students-by-class/', views.get_students_by_class, name='ajax_students_by_class'),
     path('student-charges/update/<int:id>/', views.update_student_charge, name='update_student_charge'),

     path('fees/summary/', views.fee_summary, name='fee_summary'),
     path('attendance/update/<int:record_id>/', views.update_attendance, name='update_attendance'),

path('download-expenditure-pdf/', views.download_expenditure_pdf, name='download_expenditure_pdf'),
]
