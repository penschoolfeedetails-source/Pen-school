from django.shortcuts import render, redirect,get_object_or_404
from django.contrib.auth.models import User, Group
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from .forms import TeacherCreationForm, TeacherProfileForm,DiaryForm,StudentForm,FeeForm,ExtraCurricularItemForm,NoticeForm,DailyExpenditureForm,TotalSalaryForm,MonthlySalaryForm,AnnualSubForm,StudentChargeForm
from .decorators import teacher_required, finance_required, principal_required
from .models import TeacherProfile,SchoolClass,PersonalAttribute ,Student, Attendance, AttendanceRecord,Subject,Term,Marks,DiaryEntry,StudentComplaint,ComplaintSubject,Fee,FeeAudit,Dossier,ExtraCurricularItem,ExtraCurricularMarks,ClassSyllabusTopic,Notice,StudentCharge,DailyExpenditure,TeacherSalary
from django.contrib import messages  
import base64
from django.utils import timezone
from decimal import Decimal
from xhtml2pdf import pisa
import calendar
from django.db.models import Sum 
from django.http import HttpResponse
from datetime import date
from django.utils.timezone import now
from django.conf import settings
from django.urls import reverse
from django.contrib import messages
from io import BytesIO
from django.core.mail import send_mail
from django.http import JsonResponse
from django.db.models import Q
from django.http import FileResponse
from datetime import datetime
from django.utils.dateformat import DateFormat
from django.template.loader import render_to_string  # <-- Add this
from django.core.files.base import ContentFile
import io
import json
from django.http import JsonResponse
from django.core.mail import EmailMessage
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt



def user_login(request):
    if request.method == 'POST':
        identifier = request.POST.get('username')  # username OR email
        password = request.POST.get('password')
        user = None

        # Email login
        if '@' in identifier:
            try:
                user_obj = User.objects.get(email=identifier)
                user = authenticate(username=user_obj.username, password=password)
            except User.DoesNotExist:
                messages.error(request, "Email not found")
        else:
            # Username login
            user = authenticate(username=identifier, password=password)

        if user is not None:
            if user.is_active:
                login(request, user)
                return redirect('dashboard')  # redirect to dashboard
            else:
                messages.error(request, "Your account is inactive. Contact admin.")
        else:
            messages.error(request, "Invalid username/email or password")

    # Fetch active notices to display on login page
    notices = Notice.objects.filter(is_active=True).order_by('-created_at')

    return render(request, 'accounts/login.html', {'notices': notices})
@login_required
def user_logout(request):
    logout(request)
    return redirect('login')


@login_required
def dashboard(request):
    if request.user.groups.filter(name='Teacher').exists():
        return redirect('teacher_dashboard')
    elif request.user.groups.filter(name='Finance').exists():
        return redirect('finance_dashboard')
    elif request.user.groups.filter(name='Principal').exists():
        return redirect('principal_dashboard')
    else:
        return render(request, 'accounts/unauthorized.html')


@login_required
@teacher_required
def teacher_dashboard(request):
    if not request.user.is_active:
        logout(request)
        return redirect('login')

    profile = request.user.teacherprofile
    return render(request, 'accounts/teacher_dashboard.html', {'profile': profile})


@login_required
@finance_required
def finance_dashboard(request):
    return render(request, 'accounts/finance_dashboard.html')


@login_required
@principal_required
@login_required
@principal_required
def principal_dashboard(request):
    teachers = TeacherProfile.objects.all()  # fetch all teachers
    form = NoticeForm()
    notices = Notice.objects.filter(is_active=True).order_by('-created_at')

    # Handle notice POST
    if request.method == 'POST':
        form = NoticeForm(request.POST)
        if form.is_valid():
            Notice.objects.all().delete()  # optional: remove old notices
            form.save()
            return redirect('principal_dashboard')

    return render(request, 'accounts/principal_dashboard.html', {
        'teachers': teachers,     # ✅ pass teachers
        'form': form,
        'notices': notices
    })


@login_required
@principal_required
def activate_teacher(request, teacher_id):
    if request.method == "POST":
        teacher = get_object_or_404(TeacherProfile, id=teacher_id)
        teacher.user.is_active = True
        teacher.user.save()
    return redirect('principal_dashboard')


@login_required
@finance_required
def create_teacher(request):
    if request.method == 'POST':
        user_form = TeacherCreationForm(request.POST)
        profile_form = TeacherProfileForm(request.POST)
        if user_form.is_valid() and profile_form.is_valid():
            # Save user
            user = user_form.save(commit=False)
            user.set_password(user_form.cleaned_data['password'])
            user.is_active = True  # Make sure teacher can log in
            user.save()

            # Assign Teacher group
            teacher_group = Group.objects.get(name='Teacher')
            user.groups.add(teacher_group)

            # Save profile
            profile = profile_form.save(commit=False)
            profile.user = user
            profile.save()

            messages.success(request, 'Teacher created successfully.')
    else:
        user_form = TeacherCreationForm()
        profile_form = TeacherProfileForm()

    return render(request, 'accounts/create_teacher.html', {
        'user_form': user_form,
        'profile_form': profile_form
    })


@login_required
@principal_required
def deactivate_teacher(request, teacher_id):
    if request.method == "POST":
        teacher = TeacherProfile.objects.get(id=teacher_id)
        teacher.user.is_active = False
        teacher.user.save()
    return redirect('principal_dashboard')

@login_required
@teacher_required
def select_class(request):
    classes = SchoolClass.objects.all()
    if request.method == "POST":
        class_id = request.POST.get("class_id")
        return redirect('mark_attendance', class_id=class_id)
    return render(request, 'attendance/select_class.html', {'classes': classes})

# Step 2: Mark attendance for students
from django.contrib import messages
from datetime import date


@teacher_required
@login_required
def mark_attendance(request, class_id):
    school_class = get_object_or_404(SchoolClass, id=class_id)
    today = date.today()

    # ✅ Check if attendance already exists for today
    attendance = Attendance.objects.filter(
        school_class=school_class,
        date=today
    ).first()

    if attendance:
        # attendance exists → show "already marked" template
        return render(request, 'attendance/already_marked.html', {
            'school_class': school_class
        })

    # get active students
    students = school_class.students.filter(is_active=True)

    # prepare attendance data for template
    attendance_data = []
    for student in students:
        attendance_data.append({
            "student": student,
            "P": "",
            "L": "",
            "A": "",
            "SL": "",
            "remarks": ""
        })

    if request.method == "POST":
        # create attendance sheet
        attendance = Attendance.objects.create(
            school_class=school_class,
            teacher=request.user
        )

        # save each student's status and remarks
        for student in students:
            status = request.POST.get(f"student_{student.id}")
            remarks = request.POST.get(f"remarks_{student.id}", "")

            if status:
                AttendanceRecord.objects.create(
                    attendance=attendance,
                    student=student,
                    status=status,
                    remarks=remarks
                )

        messages.success(request, "Attendance saved successfully.")
        return redirect('teacher_dashboard')

    return render(request, "attendance/mark_attendance.html", {
        "attendance_data": attendance_data,
        "school_class": school_class
    })

@login_required
@teacher_required
def select_class_for_marks(request):
    classes = SchoolClass.objects.all()
    if request.method == "POST":
        class_id = request.POST.get("class_id")
        return redirect('select_subject_term', class_id=class_id)
    return render(request, 'marks/select_class.html', {'classes': classes})

@login_required
@teacher_required
def select_subject_term(request, class_id):
    school_class = get_object_or_404(SchoolClass, id=class_id)
    subjects = school_class.subjects.all()

    current_term = Term.objects.filter(is_current=True).first()
    other_terms = Term.objects.exclude(id=current_term.id) if current_term else Term.objects.all()

    if request.method == 'POST':
        subject_id = request.POST.get("subject_id")
        term_id = request.POST.get("term_id")
        return redirect(
            'enter_marks',
            class_id=class_id,
            subject_id=subject_id,
            term_id=term_id
        )

    return render(request, 'marks/select_subject_term.html', {
        'school_class': school_class,
        'subjects': subjects,
        'current_term': current_term,
        'other_terms': other_terms
    })
@login_required
@teacher_required
def enter_marks(request, class_id, subject_id, term_id):
    school_class = get_object_or_404(SchoolClass, id=class_id)
    subject = get_object_or_404(Subject, id=subject_id)
    term = get_object_or_404(Term, id=term_id)
    students = school_class.students.filter(is_active=True)

    # Pre-process: create list of (student, mark) tuples
    students_with_marks = []
    existing_marks = Marks.objects.filter(subject=subject, term=term)
    total_marks_default = existing_marks.first().total_marks if existing_marks.exists() else None

    for student in students:
        mark = existing_marks.filter(student=student).first()
        students_with_marks.append((student, mark))

    if request.method == 'POST':
        # Get total_marks entered once
        total_marks = request.POST.get('total_marks')
        if not total_marks:
            total_marks = 100  # fallback default
        total_marks = int(total_marks)

        for student, mark in students_with_marks:
            obtained_marks = request.POST.get(f'obtained_{student.id}')
            if obtained_marks:
                obtained_marks = int(obtained_marks)
                # enforce obtained <= total
                if obtained_marks > total_marks:
                    obtained_marks = total_marks

                Marks.objects.update_or_create(
                    student=student,
                    subject=subject,
                    term=term,
                    defaults={
                        'total_marks': total_marks,
                        'obtained_marks': obtained_marks
                    }
                )

        return redirect('teacher_dashboard')

    return render(request, 'marks/enter_marks.html', {
        'school_class': school_class,
        'subject': subject,
        'term': term,
        'students_with_marks': students_with_marks,
        'total_marks': total_marks_default
    })
@login_required
def enter_diary(request):
    school_classes = SchoolClass.objects.all()
    selected_class_id = request.GET.get('class_id')

    subjects = []
    diary_entries = []
    selected_class = None

    # ---------------- GET LOGIC ----------------
    if selected_class_id:
        selected_class = get_object_or_404(SchoolClass, id=selected_class_id)

        subjects = Subject.objects.filter(school_class=selected_class)

        diary_entries = DiaryEntry.objects.filter(
            school_class=selected_class,
            date=date.today()
        )

        # 🔑 IMPORTANT: attach content to subject (template expects subject.content)
        diary_map = {d.subject_id: d.content for d in diary_entries}

        for subject in subjects:
            subject.content = diary_map.get(subject.id, "")

    # ---------------- POST LOGIC ----------------
    if request.method == 'POST':
        selected_class_id = request.GET.get('class_id')
        selected_class = get_object_or_404(SchoolClass, id=selected_class_id)

        subjects = Subject.objects.filter(school_class=selected_class)

        for subject in subjects:
            content = request.POST.get(f'content_{subject.id}', '').strip()

            diary_entry, created = DiaryEntry.objects.get_or_create(
                school_class=selected_class,
                subject=subject,
                date=date.today(),
                defaults={
                    'teacher': request.user,
                    'content': content
                }
            )

            if not created:
                diary_entry.content = content
                diary_entry.teacher = request.user
                diary_entry.save()

        return redirect(f"{request.path}?class_id={selected_class.id}")

    # ---------------- CONTEXT ----------------
    context = {
        'school_classes': school_classes,
        'subjects': subjects,
        'diary_entries': diary_entries,  # kept for future use
        'selected_class_id': int(selected_class_id) if selected_class_id else None,
        'selected_class': selected_class,  # 🔑 grade display fix
    }

    return render(request, 'diary/enter_diary.html', context)
@login_required
def view_diary(request):
    today = date.today()
    diaries = DiaryEntry.objects.filter(date=today)
    context = {'diaries': diaries, 'today': today}
    return render(request, 'diary/view_diary.html', context)

@login_required
@teacher_required
def register_complaint(request):
    classes = SchoolClass.objects.all()
    selected_class = None

    selected_class_id = request.GET.get('class_id')
    if selected_class_id:
        selected_class = get_object_or_404(SchoolClass, id=selected_class_id)

    if request.method == "POST":
        student_id = request.POST.get("student")
        class_id = request.POST.get("class")
        complaint = StudentComplaint.objects.create(
            teacher=request.user,
            student_id=student_id,
            school_class_id=class_id
        )

        subjects_ids = request.POST.getlist("subject[]")
        remarks = request.POST.getlist("remarks[]")
        for sub, rem in zip(subjects_ids, remarks):
            if sub and rem:
                ComplaintSubject.objects.create(
                    complaint=complaint,
                    subject_id=sub,
                    remarks=rem
                )

        return redirect(f"{request.path}?class_id={class_id}")

    # Prepare selection dictionary for template
    class_selection = {c.id: (selected_class and selected_class.id == c.id) for c in classes}

    context = {
        'classes': classes,
        'class_selection': class_selection,
        'selected_class': selected_class
    }
    return render(request, 'teacher/register_complaint.html', context)

# -------------------------
# AJAX: Load students & subjects for a selected class
# -------------------------
@login_required
@teacher_required
def load_students_and_subjects(request):
    class_id = request.GET.get("class_id")

    if not class_id:
        return JsonResponse({'students': [], 'subjects': []})

    students = Student.objects.filter(
        school_class_id=class_id,
        is_active=True
    ).values('id', 'roll_no', 'name', 'father_name')

    subjects = Subject.objects.filter(
        school_class_id=class_id
    ).values('id', 'name')

    return JsonResponse({
        'students': list(students),
        'subjects': list(subjects)
    })


# -------------------------
# View teacher complaints (filter by date)
# -------------------------
@login_required
@teacher_required
def teacher_complaints(request):
    date_filter = request.GET.get("date")
    complaints = StudentComplaint.objects.filter(
        teacher=request.user
    ).prefetch_related('subjects', 'subjects__subject', 'student', 'school_class')

    if date_filter:
        complaints = complaints.filter(date=date_filter)

    return render(request, "teacher/complaint_list.html", {
        "complaints": complaints
    })
@login_required
@teacher_required
def load_complaints(request):
    class_id = request.GET.get("class_id")
    if not class_id:
        return JsonResponse({'complaints': []})

    complaints_qs = StudentComplaint.objects.filter(
        school_class_id=class_id
    ).prefetch_related('subjects', 'subjects__subject', 'student')

    complaints = []
    for c in complaints_qs:
        complaints.append({
            'id': c.id,
            'date': str(c.date),
            'student': f"{c.student.name} ({c.student.roll_no})",
            'subjects': [{'name': s.subject.name, 'remarks': s.remarks} for s in c.subjects.all()]
        })

    return JsonResponse({'complaints': complaints})

@login_required
@teacher_required
def delete_complaint(request, complaint_id):
    complaint = get_object_or_404(StudentComplaint, id=complaint_id, teacher=request.user)
    complaint.delete()
    return JsonResponse({'success': True})

@login_required
@finance_required
def create_student(request):
    if request.method == 'POST':
        form = StudentForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Student added successfully!')
            return redirect('finance_dashboard')
    else:
        form = StudentForm()
    return render(request, 'finance/create_student.html', {'form': form})

@login_required
@finance_required
def fee_dashboard(request):
    students = Student.objects.filter(is_active=True)

    # Separate filters
    name = request.GET.get('name')
    roll_no = request.GET.get('roll_no')
    phone = request.GET.get('phone')
    cnic = request.GET.get('cnic')
    school_class = request.GET.get('school_class')

    if name:
        students = students.filter(name__icontains=name)
    if roll_no:
        students = students.filter(roll_no__icontains=roll_no)
    if phone:
        students = students.filter(phone__icontains=phone)
    if cnic:
        students = students.filter(cnic__icontains=cnic)
    if school_class:
        students = students.filter(school_class__id=school_class)

    classes = SchoolClass.objects.all()  # for class filter dropdown

    return render(request, 'finance/fee_dashboard.html', {
        'students': students,
        'classes': classes,
        'filters': {
            'name': name or '',
            'roll_no': roll_no or '',
            'phone': phone or '',
            'cnic': cnic or '',
            'school_class': int(school_class) if school_class else ''
        }
    })



@login_required
@finance_required
def submit_fee(request, student_id):
    student = get_object_or_404(Student, id=student_id)

    # 1️⃣ Prevent inactive students
    if not student.is_active:
        messages.error(request, "This student is inactive. Fee submission disabled.")
        return redirect('fee_dashboard')

    existing_fee = None

    if request.method == 'POST':
        form = FeeForm(request.POST, request.FILES)

        if form.is_valid():
            fee_year = form.cleaned_data['year']
            fee_month = form.cleaned_data['month']

            # 2️⃣ Handle skipped months
            last_fee = Fee.objects.filter(student=student).order_by('-year', '-month').first()
            missing_fees = []

            if last_fee:
                year = last_fee.year
                month = last_fee.month + 1

                while year < fee_year or (year == fee_year and month < fee_month):
                    if month > 12:
                        month = 1
                        year += 1

                    if not Fee.objects.filter(student=student, year=year, month=month).exists():
                        missing_fees.append(Fee(
                            student=student,
                            year=year,
                            month=month,
                            amount_paid=0,
                            status='unpaid',
                            payment_method='cash',  # default
                            submitted_by=request.user
                        ))

                    month += 1

                if missing_fees:
                    Fee.objects.bulk_create(missing_fees)

            # 3️⃣ Check if fee already exists for selected month/year
            existing_fee = Fee.objects.filter(
                student=student,
                year=fee_year,
                month=fee_month
            ).first()

            if existing_fee:
                fee = existing_fee  # update existing
                fee.amount_paid = form.cleaned_data['amount_paid']
                fee.payment_method = form.cleaned_data['payment_method']
                fee.challan_no = form.cleaned_data.get('challan_no')
                fee.payment_screenshot = form.cleaned_data.get('payment_screenshot')
                fee.payment_date = form.cleaned_data.get('payment_date') or fee.payment_date
            else:
                fee = form.save(commit=False)
                fee.student = student

            # 4️⃣ Who submitted
            fee.submitted_by = request.user

            # 5️⃣ Payment status logic
            if fee.amount_paid >= student.total_fee:
                fee.status = 'paid'
            elif fee.amount_paid > 0:
                fee.status = 'partial'
            else:
                fee.status = 'unpaid'

            # 6️⃣ Validation
            if fee.payment_method == 'online' and not fee.payment_screenshot:
                messages.error(request, 'Screenshot required for online payment.')
                return redirect('submit_fee', student_id)

            if fee.payment_method in ['cash', 'bank'] and not fee.challan_no:
                messages.error(request, 'Challan number is required.')
                return redirect('submit_fee', student_id)

            # 7️⃣ Save fee
            fee.save()
            messages.success(request, 'Fee recorded successfully.')
            

    else:
        form = FeeForm()

    return render(request, 'finance/submit_fee.html', {
        'student': student,
        'form': form,
        'existing_fee': existing_fee  # Pass it to template for JS alert
    })
from django.db.models import Q
@login_required
@finance_required
def get_siblings(request, student_id):
    student = get_object_or_404(Student, id=student_id)

    # Get siblings: same CNIC or same phone, excluding selected student
    siblings = Student.objects.filter(
        Q(cnic=student.cnic) | Q(phone=student.phone),
        is_active=True
    ).exclude(id=student.id)

    return render(request, 'finance/siblings_list.html', {
        'student': student,
        'siblings': siblings
    })
@login_required
@principal_required
def toggle_student_status(request, student_id):
    student = get_object_or_404(Student, id=student_id)
    student.is_active = not student.is_active
    student.save()

    if student.is_active:
        messages.success(request, f"{student.name} has been activated.")
    else:
        messages.success(request, f"{student.name} has been deactivated.")

    return redirect('fee_dashboard')
import io
from datetime import date
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.files.base import ContentFile
from django.http import FileResponse
from django.template.loader import render_to_string
from xhtml2pdf import pisa  # ✅ Make sure xhtml2pdf is installed

from .models import Fee, FeeAudit
from .decorators import finance_required

@login_required
@finance_required
def daily_fee_report(request):
    today = date.today()
    fees_today = Fee.objects.filter(payment_date=today)
    total_collected = sum(f.amount_paid for f in fees_today)

    if request.method == "POST":
        # Render HTML from template
        html_string = render_to_string('finance/daily_fee_pdf.html', {
            'fees_today': fees_today,
            'total_collected': total_collected,
            'today': today
        })

        pdf_file = io.BytesIO()
        # ✅ Use BytesIO with UTF-8 encoding
        pisa_status = pisa.CreatePDF(
            io.BytesIO(html_string.encode('UTF-8')),
            dest=pdf_file
        )

        if pisa_status.err:
            messages.error(request, "Error generating PDF.")
            return redirect('daily_fee_report')

        # Save PDF to database
        pdf_content = ContentFile(
            pdf_file.getvalue(),
            name=f"daily_fee_{today.strftime('%Y%m%d')}.pdf"
        )
        FeeAudit.objects.create(
            generated_by=request.user,
            file=pdf_content,
            description=f"Daily Fee Report for {today}"
        )

        messages.success(request, "Daily fee PDF generated and saved successfully.")
        return redirect('daily_fee_report')

    audits = FeeAudit.objects.order_by('-generated_at')

    return render(request, 'finance/daily_fee_report.html', {
        'fees_today': fees_today,
        'total_collected': total_collected,
        'today': today,
        'audits': audits
    })


@login_required
@finance_required
def download_fee_audit(request, audit_id):
    audit = get_object_or_404(FeeAudit, id=audit_id)
    response = FileResponse(
        audit.file.open('rb'),
        as_attachment=True,
        filename=f"{audit.file.name}"
    )
    return response

@login_required
def download_expenditure_pdf(request):
    from_date = request.GET.get('from_date')
    to_date = request.GET.get('to_date')

    # Filter expenditures based on date range
    expenditures = DailyExpenditure.objects.all().order_by('-time')
    if from_date:
        expenditures = expenditures.filter(time__date__gte=from_date)
    if to_date:
        expenditures = expenditures.filter(time__date__lte=to_date)

    total = sum(exp.expense for exp in expenditures)

    # Render HTML template
    html_string = render_to_string('accounts/expenditure_pdf.html', {
        'expenditures': expenditures,
        'total': total,
        'from_date': from_date or '',
        'to_date': to_date or ''
    })

    pdf_file = io.BytesIO()
    pisa_status = pisa.CreatePDF(io.StringIO(html_string), dest=pdf_file)

    if pisa_status.err:
        messages.error(request, "Error generating PDF.")
        return redirect('daily_expenditure')  # Your expenditure page URL name

    response = HttpResponse(pdf_file.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="expenditure_report.pdf"'
    return response
@login_required
def pending_dues(request):
    from decimal import Decimal

    # -------------------------------
    # Filters
    # -------------------------------
    selected_class = request.GET.get('class')
    single_month = request.GET.get('month')
    from_month = request.GET.get('from_month')
    to_month = request.GET.get('to_month')
    year = request.GET.get('year')
    include_inactive = request.GET.get('include_inactive') == 'on'

    # -------------------------------
    # Students queryset
    # -------------------------------
    students = Student.objects.all()
    if not include_inactive:
        students = students.filter(is_active=True)
    if selected_class:
        students = students.filter(school_class_id=selected_class)

    pending_data = []
    total_all_pending = Decimal('0.00')

    for student in students:
        fees = student.fees.filter(status__in=['unpaid', 'partial'])
        if year:
            fees = fees.filter(year=int(year))
        if single_month:
            fees = fees.filter(month=int(single_month))
        elif from_month and to_month:
            fees = fees.filter(month__gte=int(from_month), month__lte=int(to_month))

        if fees.exists():
            pending_months = ', '.join([fee.get_month_display() for fee in fees])
            total_pending = sum([student.total_fee - fee.amount_paid for fee in fees])
            total_all_pending += total_pending

            # Use full class name or section if available
            class_name = f"{student.school_class.name}"
            if hasattr(student.school_class, 'section'):
                class_name += f" - {student.school_class.section}"

            pending_data.append({
                'student_name': student.name,
                'class_name': class_name,
                'pending_months': pending_months,
                'year': fees.first().year,
                'total_pending': total_pending,
                'status': 'Active' if student.is_active else 'Inactive'
            })

    # -------------------------------
    # Class Options for Dropdown
    # -------------------------------
    class_options = []
    selected_class_name = None
    for cls in SchoolClass.objects.all():
        display_name = cls.name
        if hasattr(cls, 'section') and cls.section:
            display_name += f" - {cls.section}"

        is_selected = str(cls.id) == str(selected_class)
        class_options.append({
            'id': cls.id,
            'name': display_name,
            'selected': is_selected
        })
        if is_selected:
            selected_class_name = display_name

    # -------------------------------
    # Month Options
    # -------------------------------
    month_options = []
    month_range_options = []
    for num, name in Fee.MONTH_CHOICES:
        month_options.append({
            'num': num,
            'name': name,
            'selected': str(num) == str(single_month)
        })
        month_range_options.append({
            'num': num,
            'name': name,
            'from_selected': str(num) == str(from_month),
            'to_selected': str(num) == str(to_month)
        })

    context = {
        'pending_data': pending_data,
        'total_all_pending': total_all_pending,
        'class_options': class_options,
        'month_options': month_options,
        'month_range_options': month_range_options,
        'selected_class_name': selected_class_name,
        'filters': {
            'year': year,
            'include_inactive': include_inactive
        }
    }

    return render(request, 'finance/pending_dues.html', context)


def get_daily_summary(attendance_qs):
    """Return a list of summaries for attendance sheets"""
    summary = []
    for att in attendance_qs:
        records = att.records.all()
        summary.append({
            'date': att.date,
            'class_name': str(att.school_class),
            'total': records.count(),
            'present': records.filter(status='P').count(),
            'absent': records.filter(status='A').count(),
            'late': records.filter(status='L').count(),
            'short_leave': records.filter(status='SL').count()
        })
    return summary


def get_student_grid(attendance_qs, class_id):
    """Return student-wise attendance grid for selected class"""
    student_grid = []
    date_list = attendance_qs.order_by('date').values_list('date', flat=True).distinct()
    students = Student.objects.filter(school_class_id=class_id, is_active=True).order_by('roll_no')
    
    for student in students:
        statuses = []
        for att_date in date_list:
            att = attendance_qs.filter(school_class_id=class_id, date=att_date).first()
            if att:
                record = att.records.filter(student=student).first()
                status_map = {'P': 'Present', 'A': 'Absent', 'L': 'Late', 'SL': 'Short Leave'}
                statuses.append(status_map.get(record.status, '-') if record else '-')
            else:
                statuses.append('-')
        student_grid.append({
            'roll_no': student.roll_no,
            'name': student.name,
            'statuses': statuses
        })
    return student_grid, date_list

# -------------------------
# Main view
# -------------------------
@login_required
def view_attendance(request):
    classes = SchoolClass.objects.all()
    selected_class_id = request.GET.get('class')
    selected_date_str = request.GET.get('date')  # From "View Attendance" button
    from_date = request.GET.get('from_date')
    to_date = request.GET.get('to_date')

    # ----- Safely parse selected_date -----
    selected_date = None
    if selected_date_str:
        try:
            # Django expects YYYY-MM-DD format
            selected_date = datetime.strptime(selected_date_str, '%Y-%m-%d').date()
        except ValueError:
            selected_date = None  # Ignore invalid dates

    # Base queryset
    attendance_qs = Attendance.objects.all().prefetch_related(
        'records', 'school_class', 'records__student'
    )

    if selected_class_id:
        attendance_qs = attendance_qs.filter(school_class_id=selected_class_id)
    if from_date:
        attendance_qs = attendance_qs.filter(date__gte=from_date)
    if to_date:
        attendance_qs = attendance_qs.filter(date__lte=to_date)

    # ----- Daily Summary -----
    summary = []
    for att in attendance_qs.order_by('date'):
        records = att.records.all()
        summary.append({
            'date': att.date,
            'class_name': str(att.school_class),
            'class_id': att.school_class.id,
            'total': records.count(),
            'present': records.filter(status='P').count(),
            'absent': records.filter(status='A').count(),
            'late': records.filter(status='L').count(),
            'short_leave': records.filter(status='SL').count()
        })

    # ----- Student Grid (Filtered by selected class & date) -----
    student_grid = None
    if selected_class_id and selected_date:
        att = Attendance.objects.filter(
            school_class_id=selected_class_id, 
            date=selected_date
        ).first()
        if att:
            students = Student.objects.filter(
                school_class_id=selected_class_id, is_active=True
            ).order_by('roll_no')
            student_grid = []
            for student in students:
                record = att.records.filter(student=student).first()
                student_grid.append({
                    'roll_no': student.roll_no,
                    'name': student.name,
                    'status': record.status if record else '-',
                    'record_id': record.id if record else None
                })

    # Mark selected class in classes list for template
    for cls in classes:
        cls.selected = str(cls.id) == str(selected_class_id)

    context = {
        'classes': classes,
        'summary': summary,
        'student_grid': student_grid,
        'selected_class_id': selected_class_id,
        'selected_date': selected_date,  # pass date object to template
        'from_date': from_date,
        'to_date': to_date,
    }
    return render(request, 'attendance/view_attendance.html', context)
@login_required
def update_attendance(request, record_id):
    record = get_object_or_404(AttendanceRecord, id=record_id)

    if request.method == 'POST':
        status = request.POST.get('status')
        if status in ['P', 'A', 'L', 'SL']:
            record.status = status
            record.save()
            # Redirect back to attendance view using the parent attendance date
            return redirect(f'/attendance/view/?class={record.student.school_class.id}&date={record.attendance.date}')

    context = {
        'record': record
    }
    return render(request, 'attendance/update_attendance.html', context)

def diary_list_view(request):
    school_classes = SchoolClass.objects.all()
    selected_class_id = request.GET.get('class_id', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')

    diaries = DiaryEntry.objects.all().order_by('-date', 'school_class__name')

    # Apply filters only if specified
    if selected_class_id:
        diaries = diaries.filter(school_class_id=selected_class_id)
    if date_from:
        try:
            diaries = diaries.filter(date__gte=datetime.strptime(date_from, "%Y-%m-%d").date())
        except ValueError:
            pass
    if date_to:
        try:
            diaries = diaries.filter(date__lte=datetime.strptime(date_to, "%Y-%m-%d").date())
        except ValueError:
            pass

    # Add 'selected' attribute to classes
    for c in school_classes:
        c.selected = str(c.id) == selected_class_id

    # Build summary (unique by class and date)
    diary_summary = []
    seen = set()
    for d in diaries:
        key = (d.school_class.id, d.date)
        if key not in seen:
            diary_summary.append({
                'school_class': d.school_class,
                'date': d.date,
                'download_url': f"/diary/download/{d.school_class.id}/{d.date}"
            })
            seen.add(key)

    context = {
        'school_classes': school_classes,
        'diary_summary': diary_summary,
        'date_from': date_from,
        'date_to': date_to
    }

    return render(request, 'diary/diary_list.html', context)
@login_required
def download_diary(request, school_class_id, diary_date):
    school_class = get_object_or_404(SchoolClass, id=school_class_id)
    date_obj = datetime.strptime(diary_date, "%Y-%m-%d").date()

    # Fetch all diary entries for this class & date
    diary_entries = DiaryEntry.objects.filter(
        school_class=school_class,
        date=date_obj
    ).select_related('subject').order_by('subject__name')

    # Prepare subjects list for template
    subjects = []
    for entry in diary_entries:
        subjects.append({
            'name': entry.subject.name,  # Access subject's name via foreign key
            'content': entry.content     # Homework content
        })

    context = {
        'school_class': school_class,
        'diary_date': diary_date,
        'subjects': subjects
    }

    from django.template.loader import render_to_string
    from django.http import HttpResponse

    html_content = render_to_string('diary/diary_template.html', context)
    return HttpResponse(html_content)


    # Render the teacher diary template (ready-to-print)
    from django.template.loader import render_to_string
    from django.http import HttpResponse

    html_content = render_to_string('diary/diary_template.html', context)
    return HttpResponse(html_content)

def subject_manage(request):

    if request.method == 'POST':
        class_id = request.POST.get('school_class')
        name = request.POST.get('name')

        if class_id and name:
            Subject.objects.create(
                name=name,
                school_class_id=class_id
            )
        return redirect('subject_manage')

    classes = SchoolClass.objects.all().order_by('id')
    subjects = Subject.objects.filter(is_active=True)\
        .select_related('school_class')\
        .order_by('school_class__id', 'name')

    return render(request, 'academic/subject_management.html', {
        'classes': classes,
        'subjects': subjects,
        'is_principal': True  # always show Remove button if needed
    })


# -------------------------
# REMOVE SUBJECT
# -------------------------
def remove_subject(request, pk):
    subject = get_object_or_404(Subject, pk=pk)
    subject.is_active = False
    subject.save()
    return redirect('subject_manage')


# -------------------------
# TERM MANAGEMENT
# -------------------------
def term_manage(request):

    if request.method == 'POST':
        Term.objects.create(
            name=request.POST['name'],
            start_date=request.POST['start_date'],
            end_date=request.POST['end_date'],
            is_current='is_current' in request.POST
        )
        return redirect('term_manage')

    terms = Term.objects.all().order_by('-is_current', 'start_date')
    return render(request, 'academic/term_manage.html', {'terms': terms})

def toggle_term_current(request, term_id):
    term = get_object_or_404(Term, pk=term_id)

    if not term.is_current:
        # Make this term current → unmark previous
        Term.objects.filter(is_current=True).update(is_current=False)
        term.is_current = True
    else:
        # Toggle off → mark inactive
        term.is_current = False

    term.save()
    return redirect('term_manage')


@login_required
def select_class_term(request):
    classes = SchoolClass.objects.all()
    terms = Term.objects.all()

    if request.method == 'POST':
        class_id = request.POST.get('class')
        term_id = request.POST.get('term')
        return redirect('student_list_for_report', class_id=class_id, term_id=term_id)

    return render(request, 'teacher/select_class_term.html', {
        'classes': classes,
        'terms': terms
    })
@login_required
def remove_term(request, term_id):
    term = get_object_or_404(Term, id=term_id)

    # If the term is current, unset it before deleting
    if term.is_current:
        term.is_current = False
        term.save()

    term.delete()
    return redirect('term_manage')


# --------------------------------------------------
# GRADE CALCULATION
# --------------------------------------------------
def calculate_grade(percentage):
    if percentage >= 90:
        return 'A+'
    elif percentage >= 80:
        return 'A'
    elif percentage >= 70:
        return 'B+'
    elif percentage >= 60:
        return 'B'
    elif percentage >= 50:
        return 'C'
    elif percentage >= 40:
        return 'D'
    else:
        return 'F'


# --------------------------------------------------
# STUDENT LIST FOR REPORT CARD
# --------------------------------------------------
def student_list_for_report(request, class_id, term_id):
    # Basic objects
    students = Student.objects.filter(school_class_id=class_id)
    term = get_object_or_404(Term, id=term_id)

    # All active subjects of this class
    subjects = Subject.objects.filter(
        school_class_id=class_id,
        is_active=True
    )

    # Subjects that have marks entered (for ANY student) in this term
    marked_subject_ids = Marks.objects.filter(
        student__school_class_id=class_id,
        term_id=term_id
    ).values_list('subject_id', flat=True).distinct()

    marked_subjects = subjects.filter(id__in=marked_subject_ids)
    unmarked_subjects = subjects.exclude(id__in=marked_subject_ids)

    return render(request, 'teacher/student_list_for_report.html', {
        'students': students,
        'term': term,
        'class_id': class_id,
        'marked_subjects': marked_subjects,
        'unmarked_subjects': unmarked_subjects,
    })


# --------------------------------------------------
# REPORT CARD VIEW
@login_required
def report_card_view(request, student_id, term_id):
    # Get student and term
    student = get_object_or_404(Student.objects.select_related('school_class'), id=student_id)
    term = get_object_or_404(Term, id=term_id)

    # ---------- Subjects & Marks ----------
    subjects = Subject.objects.filter(school_class=student.school_class, is_active=True)
    marks = Marks.objects.filter(student=student, term=term).select_related('subject')
    marks_map = {m.subject_id: m for m in marks}

    subjects_with_marks = []
    total_marks_sum = 0
    obtained_marks_sum = 0

    for subject in subjects:
        mark = marks_map.get(subject.id)
        if mark:
            total = mark.total_marks or 0
            obtained = mark.obtained_marks or 0
            percent = round((obtained / total) * 100, 2) if total else 0

            if percent >= 90:
                remark = "Outstanding performance!"
            elif percent >= 80:
                remark = "Excellent work!"
            elif percent >= 70:
                remark = "Very good effort."
            elif percent >= 60:
                remark = "Good, but there is room for improvement."
            elif percent >= 50:
                remark = "Satisfactory performance."
            elif percent > 0:
                remark = "Needs improvement. Work harder."
            else:
                remark = "No marks obtained."
        else:
            total = obtained = percent = 0
            remark = "-"

        total_marks_sum += total
        obtained_marks_sum += obtained

        subjects_with_marks.append({
            'subject': subject,
            'total_marks': total,
            'obtained_marks': obtained,
            'percentage': percent,
            'remark': remark
        })

    # ---------- Extra Curricular Items ----------
    extra_items_marks = ExtraCurricularMarks.objects.filter(
        student=student,
        item__school_class=student.school_class,
        term=term
    ).select_related('item')

    for mark in extra_items_marks:
        total = mark.item.total_marks or 0
        obtained = mark.obtained_marks or 0
        percent = round((obtained / total) * 100, 2) if total else 0

        subjects_with_marks.append({
            'subject': mark.item,  # keep key 'subject' so template works
            'total_marks': total,
            'obtained_marks': obtained,
            'percentage': percent,
            'remark': '',  # optional: you can add custom remark if needed
        })

        total_marks_sum += total
        obtained_marks_sum += obtained

    # ---------- Personal Attributes ----------
    attributes_list = [
        "Communication Skills",
        "Teamwork",
        "Creativity",
        "Responsibility",
        "Discipline",
        "Punctuality",
        "Sports",
        "Debates / Speech",
        "Class Participation"
    ]

    saved_attrs = PersonalAttribute.objects.filter(student=student, term=term)
    saved_map = {attr.attribute: attr.level for attr in saved_attrs}

    personal_attributes = []
    for i, attr in enumerate(attributes_list, start=1):
        level = saved_map.get(attr, '')  # '' if not saved yet
        personal_attributes.append({
            'name': attr,
            'counter': i,  # for unique radio names
            'excellent': level == 'Excellent',
            'good': level == 'Good',
            'satisfactory': level == 'Satisfactory',
        })

    # ---------- Overall Grade ----------
    overall_percentage = round((obtained_marks_sum / total_marks_sum) * 100, 2) if total_marks_sum else 0
    grade = calculate_grade(overall_percentage)

    # ---------- Context ----------
    context = {
        'student': student,
        'term': term,
        'subjects_with_marks': subjects_with_marks,
        'total_marks': total_marks_sum,
        'obtained_marks': obtained_marks_sum,
        'percentage': overall_percentage,
        'grade': grade,
        'personal_attributes': personal_attributes,
    }

    return render(request, 'teacher/report_card.html', context)
@login_required
def add_extra_curricular_item(request, class_id, term_id):
    term = get_object_or_404(Term, id=term_id)
    school_class = get_object_or_404(SchoolClass, id=class_id)
    students = Student.objects.filter(school_class_id=class_id)

    available_items = [
        "Summer Work", 
        "Winter Work", 
        "Homework", 
        "Uniform", 
        "Attendance Consistency"
    ]

    saved_items = ExtraCurricularItem.objects.filter(
        school_class_id=class_id,
        term_id=term_id
    ).order_by('name')

    saved_items_data = [
        {'id': item.id, 'name': item.name, 'total': item.total_marks, 'is_attendance': item.is_attendance}
        for item in saved_items
    ]

    # ---------------- REMOVE ITEM ----------------
    if request.method == "POST" and request.POST.get("remove_item"):
        item_id = request.POST.get("remove_item")
        try:
            item_obj = ExtraCurricularItem.objects.get(
                id=item_id,
                school_class_id=class_id,
                term_id=term_id
            )
            ExtraCurricularMarks.objects.filter(
                item=item_obj,
                term_id=term_id,
                student__school_class_id=class_id
            ).delete()
            item_obj.delete()
        except ExtraCurricularItem.DoesNotExist:
            pass
        return redirect("add_extra_curricular_item", class_id, term_id)

    # ---------------- ADD NEW ITEMS ----------------
    if request.method == "POST" and not request.POST.get("step"):
        selected_items = request.POST.getlist("items")
        if not selected_items:
            return render(request, "teacher/add_extra_curricular_item.html", {
                "available_items": available_items,
                "error": "Please select at least one item",
                "selected_items": saved_items_data,
                "term": term,
                "school_class": school_class,
            })

        from_date = request.POST.get("from_date")
        to_date = request.POST.get("to_date")

        for item in selected_items:
            is_attendance = item == "Attendance Consistency"

            # Calculate total marks
            if is_attendance:
                if not from_date or not to_date:
                    return render(request, "teacher/add_extra_curricular_item.html", {
                        "available_items": available_items,
                        "error": "Select dates for Attendance Consistency",
                        "selected_items": saved_items_data,
                        "term": term,
                        "school_class": school_class,
                    })
                total = Attendance.objects.filter(
                    school_class_id=class_id,
                    date__range=(from_date, to_date)
                ).count()
            else:
                total = request.POST.get(f"total_{item}")
                if not total or not total.isdigit():
                    return render(request, "teacher/add_extra_curricular_item.html", {
                        "available_items": available_items,
                        "error": f"Enter valid total marks for {item}",
                        "selected_items": saved_items_data,
                        "term": term,
                        "school_class": school_class,
                    })
                total = int(total)

            # Save or skip if already exists
            ExtraCurricularItem.objects.get_or_create(
                name=item,
                school_class_id=class_id,
                term_id=term_id,
                defaults={
                    "total_marks": total,
                    "is_attendance": is_attendance,
                    "from_date": from_date if is_attendance else None,
                    "to_date": to_date if is_attendance else None
                }
            )

        return redirect("add_extra_curricular_item", class_id, term_id)

    # ---------------- PROCEED TO ENTER MARKS ----------------
    if request.method == "POST" and request.POST.get("step") == "2":
        saved_items = ExtraCurricularItem.objects.filter(
            school_class_id=class_id,
            term_id=term_id
        ).order_by('name')

        students_with_marks = []
        for student in students:
            marks_list = []
            for item in saved_items:
                mark = ExtraCurricularMarks.objects.filter(
                    student=student,
                    item=item,
                    term=term
                ).first()
                obtained_marks = mark.obtained_marks if mark else 0

                marks_list.append({
                    'item_id': item.id,
                    'item_name': item.name,
                    'is_attendance': item.is_attendance,
                    'total_marks': item.total_marks,
                    'obtained_marks': obtained_marks,
                })
            students_with_marks.append({
                'student': student,
                'marks_list': marks_list
            })

        return render(request, "teacher/add_extra_curricular_marks.html", {
            "students_with_marks": students_with_marks,
            "items": saved_items,
            "term": term,
            "school_class": school_class,
            "class_id": class_id,
            "term_id": term_id,
        })

    # ---------------- SAVE MARKS ----------------
    if request.method == "POST" and request.POST.get("step") == "3":
        saved_items = ExtraCurricularItem.objects.filter(
            school_class_id=class_id,
            term_id=term_id
        )

        for student in students:
            for item in saved_items:
                if item.is_attendance:
                    obtained = AttendanceRecord.objects.filter(
                        student=student,
                        status="P",
                        attendance__school_class_id=class_id,
                        attendance__date__range=(item.from_date, item.to_date)
                    ).count()
                else:
                    field_name = f"marks_{student.id}_{item.id}"
                    obtained = request.POST.get(field_name, 0)
                    try:
                        obtained = int(obtained)
                    except (ValueError, TypeError):
                        obtained = 0

                ExtraCurricularMarks.objects.update_or_create(
                    student=student,
                    item=item,
                    term=term,
                    defaults={'obtained_marks': obtained}
                )

        return redirect("add_extra_curricular_item", class_id, term_id)

    # ---------------- INITIAL PAGE ----------------
    return render(request, "teacher/add_extra_curricular_item.html", {
        "available_items": available_items,
        "selected_items": saved_items_data,
        "term": term,
        "school_class": school_class,
    })
@login_required
def remove_extra_from_report_card(request, class_id, term_id, item_id):
    term = get_object_or_404(Term, id=term_id)
    item = get_object_or_404(ExtraCurricularItem, id=item_id)

    # Delete marks for this item
    ExtraCurricularMarks.objects.filter(
        item=item,
        term=term,
        student__school_class_id=class_id
    ).delete()

    # Delete the item itself
    item.delete()

    return redirect("student_list_for_report", class_id=class_id, term_id=term_id)
from django.shortcuts import get_object_or_404
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from django.template.loader import render_to_string
from weasyprint import HTML
import os
import tempfile
import zipfile
from pathlib import Path
import os

def build_report_card_context(student, term, for_pdf=False):
    subjects = Subject.objects.filter(school_class=student.school_class, is_active=True)
    marks = Marks.objects.filter(student=student, term=term).select_related('subject')
    marks_map = {m.subject_id: m for m in marks}

    subjects_with_marks = []
    total_marks_sum = 0
    obtained_marks_sum = 0

    for subject in subjects:
        mark = marks_map.get(subject.id)
        if mark:
            total = mark.total_marks or 0
            obtained = mark.obtained_marks or 0
            percent = round((obtained / total) * 100, 2) if total else 0
        else:
            total = obtained = percent = 0

        total_marks_sum += total
        obtained_marks_sum += obtained

        subjects_with_marks.append({
            'subject': subject,
            'total_marks': total,
            'obtained_marks': obtained,
            'percentage': percent,
            'remark': "-"
        })

    # ---------- Personal Attributes ----------
    attributes_list = [
        "Communication Skills",
        "Teamwork",
        "Creativity",
        "Responsibility",
        "Discipline",
        "Punctuality",
        "Sports",
        "Debates / Speech",
        "Class Participation"
    ]

    saved_attrs = PersonalAttribute.objects.filter(student=student, term=term)
    saved_map = {attr.attribute: attr.level for attr in saved_attrs}

    personal_attributes = []
    for i, attr in enumerate(attributes_list, start=1):
        level = saved_map.get(attr, '')  # '' if not saved yet
        personal_attributes.append({
            'name': attr,
            'counter': i,  # unique for radio buttons
            'excellent': level == 'Excellent',
            'good': level == 'Good',
            'satisfactory': level == 'Satisfactory',
        })

    # ---------- Logos ----------
    if for_pdf:
        # Absolute paths for WeasyPrint
        school_logo = os.path.join(os.path.abspath("accounts/static/logo"), "school_logo.jpg")
        paradigm_logo = os.path.join(os.path.abspath("accounts/static/logo"), "paradigm_logo.jpg")
    else:
        # Browser view
        school_logo = "/static/logo/school_logo.jpg"
        paradigm_logo = "/static/logo/paradigm_logo.jpg"

    overall_percentage = round((obtained_marks_sum / total_marks_sum) * 100, 2) if total_marks_sum else 0
    grade = calculate_grade(overall_percentage)

    return {
        'student': student,
        'term': term,
        'subjects_with_marks': subjects_with_marks,
        'total_marks': total_marks_sum,
        'obtained_marks': obtained_marks_sum,
        'percentage': overall_percentage,
        'grade': grade,
        'personal_attributes': personal_attributes,
        'school_logo': school_logo,
        'paradigm_logo': paradigm_logo,
    }


import requests
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.shortcuts import render
import json
import openai
def circular_notice_view(request):
    return render(request, "accounts/circular_notice.html")
import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.shortcuts import render


def circular_notice_view(request):
    return render(request, "accounts/circular_notice.html")


@csrf_exempt
def generate_circular(request):
    if request.method != "POST":
        return JsonResponse({"error": "Invalid request method"}, status=405)

    try:
        data = json.loads(request.body)
        user_text = data.get("text", "").strip()

        if not user_text:
            return JsonResponse({"error": "Topic is required"}, status=400)

        # 🔒 Import Groq ONLY when needed
        from groq import Groq

        client = Groq(api_key=settings.GROQ_API_KEY)

        system_msg = (
            "You are a professional school administrator. "
            "Write clear, concise, and engaging school circulars for any topic. "
            "Focus on delivering the news in an informative, professional, and encouraging tone. "
            "Be creative and flexible while remaining formal and welcoming. "
            "Do not include salutations, subject lines, or signatures unless naturally appropriate. "
            "Keep the message concise and easy to read with minimal line breaks."
        )

        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": system_msg},
                {"role": "user", "content": f"Topic: {user_text}"}
            ],
            temperature=0.3
        )

        return JsonResponse({
            "message": response.choices[0].message.content.strip()
        })

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

def term_syllabus_dashboard(request):
    """
    Render the Term Syllabus Dashboard:
    - Dropdowns for Class and Subject
    - Show Terms and Topics (cards)
    - Show summary table of all subjects & their term topics
    """
    classes = SchoolClass.objects.all()
    terms = Term.objects.all()

    class_id = request.GET.get('class')
    subject_id = request.GET.get('subject')

    selected_class = None
    selected_subject = None
    subjects_for_class = []
    terms_with_topics = []
    syllabus_table_html = ""

    # If class selected
    if class_id:
        selected_class = get_object_or_404(SchoolClass, id=class_id)
        subjects_for_class = Subject.objects.filter(school_class=selected_class, is_active=True)

    # If subject selected
    if subject_id:
        selected_subject = get_object_or_404(Subject, id=subject_id)
        # Render term cards (existing code)
        for term in terms:
            topics = ClassSyllabusTopic.objects.filter(
                term=term,
                school_class=selected_class,
                subject=selected_subject
            )
            topics_html = ""
            for topic in topics:
                topics_html += f'''
                <li id="topic-{topic.id}">
                    {topic.topic_name}
                    <button class="btn btn-sm btn-danger remove-topic-btn" data-topic-id="{topic.id}">Remove</button>
                </li>
                '''
            if not topics_html:
                topics_html = "<li>No topics added yet.</li>"

            term_card_html = f'''
            <div class="card mb-3" id="term-card-{term.id}">
                <div class="card-header"><strong>{term.name}</strong></div>
                <div class="card-body">
                    <ul id="topic-list-{term.id}">
                        {topics_html}
                    </ul>
                    <div class="input-group mt-2">
                        <input type="text" class="form-control topic-input" placeholder="Enter topic name">
                        <button class="btn btn-primary add-topic-btn" data-term-id="{term.id}"
                            data-class-id="{selected_class.id}" data-subject-id="{selected_subject.id}">
                            Add Syllabus
                        </button>
                    </div>
                </div>
            </div>
            '''
            terms_with_topics.append(term_card_html)

    # Pre-render class dropdown
    class_options_html = "".join([
        f'<option value="{c.id}" {"selected" if selected_class and selected_class.id==c.id else ""}>{c.name}{" - " + c.section if c.section else ""}</option>'
        for c in classes
    ])

    # Pre-render subject dropdown
    subject_options_html = "".join([
        f'<option value="{s.id}" {"selected" if selected_subject and selected_subject.id==s.id else ""}>{s.name}</option>'
        for s in subjects_for_class
    ])

    # --------------------------
    # Render Syllabus Summary Table
    # --------------------------
    if selected_class:
        # Table headers
        table_header = "<tr><th>Subject</th>"
        for term in terms:
            table_header += f"<th>{term.name}</th>"
        table_header += "</tr>"

        table_rows = ""
        for subject in subjects_for_class:
            row_html = f"<tr><td>{subject.name}</td>"
            for term in terms:
                topics = ClassSyllabusTopic.objects.filter(
                    school_class=selected_class,
                    subject=subject,
                    term=term
                )
                if topics.exists():
                    topics_list = "<ul>" + "".join([f"<li>{t.topic_name}</li>" for t in topics]) + "</ul>"
                else:
                    topics_list = "<span style='color:red'>No topics</span>"
                row_html += f"<td>{topics_list}</td>"
            row_html += "</tr>"
            table_rows += row_html

        syllabus_table_html = f"""
        <h4>Syllabus Summary Table</h4>
        <table class="table table-bordered">
            {table_header}
            {table_rows}
        </table>
        """

    context = {
        "class_options_html": class_options_html,
        "subject_options_html": subject_options_html,
        "terms_with_topics_html": "".join(terms_with_topics),
        "syllabus_table_html": syllabus_table_html,
        "selected_class": selected_class,
        "selected_subject": selected_subject,
    }

    return render(request, "academic/term_syllabus_dashboard.html", context)


# ------------------------------
# AJAX: Add Syllabus Topic
# ------------------------------
@csrf_exempt
def add_syllabus_topic_ajax(request):
    if request.method == "POST":
        term_id = request.POST.get("term_id")
        class_id = request.POST.get("class_id")
        subject_id = request.POST.get("subject_id")
        topic_name = request.POST.get("topic_name")
        if term_id and class_id and subject_id and topic_name:
            term = get_object_or_404(Term, id=term_id)
            school_class = get_object_or_404(SchoolClass, id=class_id)
            subject = get_object_or_404(Subject, id=subject_id)
            topic, created = ClassSyllabusTopic.objects.get_or_create(
                term=term,
                school_class=school_class,
                subject=subject,
                topic_name=topic_name
            )
            return JsonResponse({"status": "success", "topic_id": topic.id, "topic_name": topic.topic_name})
    return JsonResponse({"status": "error"})


# ------------------------------
# AJAX: Remove Syllabus Topic
# ------------------------------
@csrf_exempt
def remove_syllabus_topic_ajax(request):
    if request.method == "POST":
        topic_id = request.POST.get("topic_id")
        topic = get_object_or_404(ClassSyllabusTopic, id=topic_id)
        topic.delete()
        return JsonResponse({"status": "success"})
    return JsonResponse({"status": "error"})

def teacher_syllabus_dashboard(request):
    classes = SchoolClass.objects.all()
    selected_class = None
    selected_subject = None

    class_id = request.GET.get('class')
    subject_id = request.GET.get('subject')

    # Build class dropdown HTML
    class_options = ""
    for cls in classes:
        selected_attr = 'selected' if class_id and int(class_id) == cls.id else ''
        display_name = f"{cls.name} - {cls.section}" if cls.section else cls.name
        class_options += f'<option value="{cls.id}" {selected_attr}>{display_name}</option>'

    subject_options = ""
    terms_with_topics_html = ""
    if class_id:
        selected_class = get_object_or_404(SchoolClass, id=class_id)
        subjects = Subject.objects.filter(school_class=selected_class, is_active=True)

        # Build subject dropdown HTML
        for sub in subjects:
            selected_attr = 'selected' if subject_id and int(subject_id) == sub.id else ''
            subject_options += f'<option value="{sub.id}" {selected_attr}>{sub.name}</option>'

        if subject_id:
            selected_subject = get_object_or_404(Subject, id=subject_id)
            terms = Term.objects.all()

            # Build HTML for all terms & topics
            for term in terms:
                topics = ClassSyllabusTopic.objects.filter(
                    term=term,
                    school_class=selected_class,
                    subject=selected_subject
                )
                topic_list_html = ""
                for topic in topics:
                    topic_list_html += f"<li>{topic.topic_name}</li>"
                if not topic_list_html:
                    topic_list_html = "<li>No topics added yet.</li>"

                terms_with_topics_html += f"""
                <div class="card mb-3">
                    <div class="card-header"><strong>{term.name}</strong></div>
                    <div class="card-body">
                        <ul>{topic_list_html}</ul>
                    </div>
                </div>
                """

    context = {
        'class_options_html': class_options,
        'subject_options_html': subject_options,
        'terms_with_topics_html': terms_with_topics_html,
        'selected_class': selected_class,
        'selected_subject': selected_subject,
    }
    return render(request, 'teacher/teacher_syllabus_dashboard.html', context)


def principal_notice_dashboard(request):
    form = NoticeForm()
    if request.method == 'POST':
        form = NoticeForm(request.POST)
        if form.is_valid():
            form.save()  # old active notice automatically deactivated
            return redirect('principal_notice_dashboard')

    # Only show the latest active notice
    notices = Notice.objects.filter(is_active=True).order_by('-created_at')
    return render(request, 'accounts/principal_dashboard.html', {'form': form, 'notices': notices})
# views.py
from django.shortcuts import get_object_or_404

def delete_notice(request, notice_id):
    notice = get_object_or_404(Notice, id=notice_id)
    notice.delete()
    return redirect('principal_notice_dashboard')


# --------------------------------------------------
# PRINCIPAL → MARKS STATUS (COMPLETION TRACKER)
# --------------------------------------------------
def principal_marks_status(request):
    selected_class = request.GET.get('class')
    selected_term = request.GET.get('term')

    # ----- FILTER BASE -----
    classes = SchoolClass.objects.all()
    terms = Term.objects.all()

    if selected_class:
        classes = classes.filter(id=selected_class)

    if selected_term:
        terms = terms.filter(id=selected_term)

    # ----- CLASS OPTIONS HTML -----
    class_options = '<option value="">All Classes</option>'
    for c in SchoolClass.objects.all():
        selected = 'selected' if str(c.id) == str(selected_class) else ''
        class_options += f'<option value="{c.id}" {selected}>{c}</option>'

    # ----- TERM OPTIONS HTML -----
    term_options = '<option value="">All Terms</option>'
    for t in Term.objects.all():
        selected = 'selected' if str(t.id) == str(selected_term) else ''
        term_options += f'<option value="{t.id}" {selected}>{t.name}</option>'

    # ----- TABLE ROWS -----
    table_rows = ''

    for school_class in classes:
        subjects = Subject.objects.filter(
            school_class=school_class,
            is_active=True
        )

        for term in terms:
            for subject in subjects:
                marks_exist = Marks.objects.filter(
                    student__school_class=school_class,
                    subject=subject,
                    term=term
                ).exists()

                if marks_exist:
                    status_html = (
                        '<span class="badge bg-success d-block mb-1">Marks Entered</span>'
                        f'<a href="{reverse("principal_view_subject_marks", args=[school_class.id, term.id, subject.id])}" '
                        'class="btn btn-sm btn-outline-primary">View Marks</a>'
                    )
                else:
                    status_html = '<span class="badge bg-danger">Not Entered</span>'

                table_rows += f"""
                    <tr>
                        <td>{school_class}</td>
                        <td>{term.name}</td>
                        <td>{subject.name}</td>
                        <td>{status_html}</td>
                    </tr>
                """

    context = {
        'class_options': class_options,
        'term_options': term_options,
        'table_rows': table_rows,
    }

    return render(request, 'academic/marks_status.html', context)


# --------------------------------------------------
# PRINCIPAL → VIEW SUBJECT MARKS (READ ONLY)
# --------------------------------------------------
def principal_view_subject_marks(request, class_id, term_id, subject_id):
    school_class = get_object_or_404(SchoolClass, id=class_id)
    term = get_object_or_404(Term, id=term_id)
    subject = get_object_or_404(Subject, id=subject_id)

    students = Student.objects.filter(
        school_class=school_class,
        is_active=True
    ).order_by('roll_no')

    marks = Marks.objects.filter(
        subject=subject,
        term=term,
        student__school_class=school_class
    )

    marks_map = {m.student_id: m for m in marks}

    student_rows = ''

    for student in students:
        mark = marks_map.get(student.id)

        obtained = mark.obtained_marks if mark else 'Not Entered'
        total = mark.total_marks if mark else '—'

        student_rows += f"""
            <tr>
                <td>{student.roll_no}</td>
                <td>{student.name}</td>
                <td>{obtained}</td>
                <td>{total}</td>
            </tr>
        """

    context = {
        'heading': f'{subject.name} — {school_class} ({term.name})',
        'back_url': reverse('principal_marks_status'),
        'student_rows': student_rows,
    }

    return render(request, 'academic/view_subject_marks.html', context)


@csrf_exempt
def send_welcome_email(request):
    if request.method != "POST":
        return JsonResponse({"message": "Invalid request"}, status=400)

    try:
        data = json.loads(request.body)

        name = data.get("name")
        grade = data.get("grade")
        email = data.get("email")
        image_data = data.get("image")

        if not all([name, grade, email, image_data]):
            return JsonResponse({"message": "Missing data"}, status=400)

        # Decode base64 image
        format, imgstr = image_data.split(';base64,')
        image_bytes = base64.b64decode(imgstr)

        mail = EmailMessage(
            subject="Welcome to PEN Schools 🎓",
            body=f"Dear {name},\n\nWelcome to PEN Schools! We are thrilled to have you join our vibrant community of learners, thinkers, and achievers. At PEN Schools, our mission is to provide a nurturing environment where every student can explore their potential, embrace creativity, and achieve academic excellence.\nOur vision is to shape future leaders who are not only knowledgeable but also compassionate, responsible, and innovative. We believe in fostering curiosity, encouraging collaboration, and developing skills that prepare our students for success in an ever-changing world.\nAs you embark on this exciting journey, know that our dedicated faculty and staff are here to support, guide, and inspire you every step of the way. Together, we will make your educational experience enriching, memorable, and empowering.\n\nWelcome once again to PEN Schools — where learning meets inspiration!\n\nWarm regards,\nPrincipal",
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[email],
        )

        mail.attach(
            filename=f"{name}_welcome_card.png",
            content=image_bytes,
            mimetype="image/png"
        )

        mail.send()

        return JsonResponse({"message": "Welcome card sent as image successfully!"})

    except Exception as e:
        print("EMAIL ERROR:", e)
        return JsonResponse({"message": "Server error"}, status=500)


def daily_expenditure(request):
    # Filter
    from_date = request.GET.get('from_date')
    to_date = request.GET.get('to_date')

    expenditures = DailyExpenditure.objects.all().order_by('-time')

    if from_date:
        expenditures = expenditures.filter(time__date__gte=from_date)
    if to_date:
        expenditures = expenditures.filter(time__date__lte=to_date)

    total = expenditures.aggregate(Sum('expense'))['expense__sum'] or 0

    # Form submission
    if request.method == 'POST':
        form = DailyExpenditureForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('daily_expenditure')
    else:
        form = DailyExpenditureForm()

    context = {
        'form': form,
        'expenditures': expenditures,
        'total': total,
        'from_date': from_date or '',
        'to_date': to_date or '',
    }
    return render(request, 'accounts/daily_expenditure.html', context)


def delete_expenditure(request, pk):
    expenditure = get_object_or_404(DailyExpenditure, pk=pk)
    expenditure.delete()
    return redirect('daily_expenditure')

def teacher_salary(request):

    # ----------------------------
    # Handle Forms
    # ----------------------------
    total_form = TotalSalaryForm()
    monthly_form = MonthlySalaryForm()

    if request.method == 'POST':

        if 'add_total' in request.POST:
            total_form = TotalSalaryForm(request.POST)
            if total_form.is_valid():
                obj = total_form.save(commit=False)

                # ----------------------------
                # Update Teacher salary
                # ----------------------------
                if obj.teacher and obj.total_salary:
                    obj.teacher.salary = obj.total_salary
                    obj.teacher.save()

                # ----------------------------
                # Update existing extra staff if exists
                # ----------------------------
                if obj.name and obj.total_salary:
                    existing_staff = TeacherSalary.objects.filter(name=obj.name, teacher__isnull=True)
                    if existing_staff.exists():
                        # Update the latest record
                        latest_staff = existing_staff.order_by('-id').first()
                        latest_staff.total_salary = obj.total_salary
                        latest_staff.save()
                        obj = latest_staff  # use the updated object
                    else:
                        # New extra staff, save normally
                        obj.save()
                else:
                    # Regular teacher salary
                    obj.save()

                return redirect('teacher_salary')

        if 'add_monthly' in request.POST:
            monthly_form = MonthlySalaryForm(request.POST)
            if monthly_form.is_valid():
                monthly_form.save()
                return redirect('teacher_salary')

    # ----------------------------
    # Filters
    # ----------------------------
    from_date = request.GET.get('from')
    to_date = request.GET.get('to')

    salaries = TeacherSalary.objects.select_related('teacher', 'teacher__user')

    if from_date:
        y, m = map(int, from_date.split('-'))
        salaries = salaries.filter(date__gte=datetime(y, m, 1))

    if to_date:
        y, m = map(int, to_date.split('-'))
        last_day = calendar.monthrange(y, m)[1]
        salaries = salaries.filter(date__lte=datetime(y, m, last_day))

    # ----------------------------
    # Month Order (Jan → Dec)
    # ----------------------------
    MONTHS = [
        (1, 'Jan'), (2, 'Feb'), (3, 'Mar'), (4, 'Apr'),
        (5, 'May'), (6, 'Jun'), (7, 'Jul'), (8, 'Aug'),
        (9, 'Sep'), (10, 'Oct'), (11, 'Nov'), (12, 'Dec'),
    ]
    months_list = [m[1] for m in MONTHS]

    # ----------------------------
    # Collect Unique Staff
    # ----------------------------
    staff_keys = []
    for s in salaries:
        key = f"T-{s.teacher.id}" if s.teacher else f"N-{s.name}"
        if key not in staff_keys:
            staff_keys.append(key)

    # ----------------------------
    # Prepare Totals
    # ----------------------------
    month_totals = [Decimal('0.00') for _ in range(12)]
    contract_total = Decimal('0.00')

    # ----------------------------
    # Build Table Data
    # ----------------------------
    teacher_data = []

    for key in staff_keys:

        if key.startswith("T-"):
            # Teachers
            teacher_id = int(key.split('-')[1])
            teacher = TeacherProfile.objects.get(id=teacher_id)
            display_name = teacher.user.first_name
            contract_salary = teacher.salary or Decimal('0.00')
            person_salaries = salaries.filter(teacher=teacher)
        else:
            # Extra staff
            name = key.split('-', 1)[1]
            display_name = name

            # latest total_salary for extra staff
            base = salaries.filter(name=name, total_salary__isnull=False).order_by('-id').first()
            contract_salary = base.total_salary if base else Decimal('0.00')

            person_salaries = salaries.filter(name=name)

        # Add to contract total
        contract_total += contract_salary

        monthly_salaries = []

        for index, (month_num, month_label) in enumerate(MONTHS):
            month_records = person_salaries.filter(date__month=month_num)
            month_total_for_person = Decimal('0.00')
            month_record_id = None

            for rec in month_records:
                if rec.salary is not None:
                    month_total_for_person += Decimal(rec.salary)
                    month_record_id = rec.id  # last record id for action buttons

            if month_total_for_person > 0:
                monthly_salaries.append({'id': month_record_id, 'salary': month_total_for_person})
                month_totals[index] += month_total_for_person
            else:
                monthly_salaries.append({'id': None, 'salary': None})

        teacher_data.append({
            'name': display_name,
            'total_salary': contract_salary,
            'monthly_salaries': monthly_salaries
        })

    # ----------------------------
    # Context
    # ----------------------------
    context = {
        'total_form': total_form,
        'monthly_form': monthly_form,
        'months_list': months_list,
        'teacher_data': teacher_data,
        'from_date': from_date,
        'to_date': to_date,
        'month_totals': month_totals,
        'contract_total': contract_total,
    }

    return render(request, 'accounts/teacher_salary.html', context)


# ----------------------------
# Update / Delete Monthly Salaries
# ----------------------------
def update_salary(request, pk):
    salary_entry = get_object_or_404(TeacherSalary, pk=pk)
    if request.method == 'POST':
        form = MonthlySalaryForm(request.POST, instance=salary_entry)
        if form.is_valid():
            form.save()
            return redirect('teacher_salary')
    else:
        form = MonthlySalaryForm(instance=salary_entry)
    return render(request, 'accounts/update_salary.html', {'form': form})

def delete_salary(request, pk):
    salary_entry = get_object_or_404(TeacherSalary, pk=pk)
    salary_entry.delete()
    return redirect('teacher_salary')
def complaint_list(request):
    complaints = StudentComplaint.objects.select_related(
        'student',
        'school_class'
    )

    selected_class = request.GET.get('class')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')

    if selected_class:
        complaints = complaints.filter(school_class_id=selected_class)

    if date_from and date_to:
        complaints = complaints.filter(date__range=[date_from, date_to])

    students = (
        Student.objects
        .filter(studentcomplaint__in=complaints)
        .distinct()
    )

    # ✅ Build dropdown safely (NO select_related)
    classes = []
    for c in SchoolClass.objects.all():
        classes.append({
            'id': c.id,
            # adjust field names based on your model
            'label': f"{c.name} - {c.section}",
            'selected': str(c.id) == str(selected_class)
        })

    context = {
        'students': students,
        'classes': classes,
        'date_from': date_from,
        'date_to': date_to,
    }

    return render(request, 'academic/complaint_list.html', context)

def student_complaints(request, student_id):
    complaints = (
        StudentComplaint.objects
        .filter(student_id=student_id)
        .prefetch_related('subjects__subject', 'teacher')
        .order_by('-date')
    )

    student = complaints.first().student if complaints.exists() else None

    return render(
        request,
        'academic/student_complaints.html',
        {
            'complaints': complaints,
            'student': student
        }
    )
def annual_sub_view(request):
    year = request.GET.get('year')
    name = request.GET.get('name')
    student_class = request.GET.get('class')  # new filter

    students = Student.objects.all()
    
    # Year filter
    if year:
        try:
            year_int = int(year)
            students = students.filter(joining_date__year=year_int)
        except ValueError:
            year_int = None
    else:
        year_int = None

    # Name filter
    if name:
        students = students.filter(name__icontains=name.strip())

    # Class filter
    if student_class:
        students = students.filter(school_class__id=student_class)  # assuming school_class is FK

    # Totals
    total_annual_sub = students.aggregate(Sum('annual_sub'))['annual_sub__sum'] or 0
    total_paid = students.aggregate(Sum('annual_sub_paid'))['annual_sub_paid__sum'] or 0
    
    # Calculate remaining for each student
    for student in students:
        annual_sub = student.annual_sub or 0
        annual_sub_paid = student.annual_sub_paid or 0
        student.remaining = annual_sub - annual_sub_paid
    
    # Pass all classes for filter dropdown
    classes = SchoolClass.objects.all()  # assuming your class model is SchoolClass

    context = {
        'students': students,
        'total_annual_sub': total_annual_sub,
        'total_paid': total_paid,
        'total_remaining': total_annual_sub - total_paid,
        'year': year_int,
        'classes': classes,
        'selected_class': student_class,
    }
    return render(request, 'accounts/annual_sub.html', context)
def update_annual_sub(request, student_id):
    student = get_object_or_404(Student, id=student_id)
    
    if request.method == "POST":
        form = AnnualSubForm(request.POST, instance=student)
        if form.is_valid():
            form.save()
            messages.success(request, f"Annual subscription updated for {student.name}.")
            return redirect('annual_sub')
    else:
        form = AnnualSubForm(instance=student)
    
    return render(request, 'accounts/update_annual_sub.html', {'form': form, 'student': student})
@login_required
def get_students_by_class(request):
    class_id = request.GET.get('class_id')
    students = Student.objects.filter(school_class_id=class_id, is_active=True).values('id', 'name')
    return JsonResponse(list(students), safe=False)
@login_required
def student_charge_view(request):
    form = StudentChargeForm()

    # -------------------------------
    # ADD NEW CHARGE
    # -------------------------------
    if request.method == "POST":
        form = StudentChargeForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('student_charge')

    # -------------------------------
    # FILTER (DATE RANGE)
    # -------------------------------
    charges = StudentCharge.objects.select_related(
        'student', 'school_class'
    ).order_by('-date')

    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')

    if date_from and date_to:
        charges = charges.filter(date__range=[date_from, date_to])

    # -------------------------------
    # TOTAL CALCULATIONS
    # -------------------------------
    sums = charges.aggregate(
        total_sum=Sum('total_amount'),
        paid_sum=Sum('paid_amount')
    )

    total_sum = sums['total_sum'] or 0
    paid_sum = sums['paid_sum'] or 0

    context = {
        'form': form,
        'charges': charges,
        'total_sum': total_sum,
        'paid_sum': paid_sum,
        'pending_sum': total_sum - paid_sum,
        'date_from': date_from,
        'date_to': date_to,
    }

    return render(request, 'accounts/student_charge.html', context)
@login_required
def delete_student_charge(request, id):
    StudentCharge.objects.filter(id=id).delete()
    return redirect('student_charge')
# views.py
@login_required
# views.py
@login_required
def update_student_charge(request, id):
    charge = get_object_or_404(StudentCharge, id=id)

    if request.method == "POST":
        # update only the fields from POST
        total_amount = request.POST.get('total_amount')
        paid_amount = request.POST.get('paid_amount')

        if total_amount is not None:
            charge.total_amount = total_amount
        if paid_amount is not None:
            charge.paid_amount = paid_amount

        charge.save()
        return redirect('student_charge')  # redirect back to main page

@login_required
def fee_summary(request):

    fees = Fee.objects.select_related(
        'student',
        'student__school_class'
    )

    class_id = request.GET.get('class')
    month = request.GET.get('month')
    year = request.GET.get('year')

    if class_id:
        fees = fees.filter(student__school_class_id=class_id)

    if month:
        fees = fees.filter(month=month)

    if year:
        fees = fees.filter(year=year)

    # ================= TOTALS =================
    total_collected = fees.aggregate(
        total=Sum('amount_paid')
    )['total'] or Decimal('0.00')

    paid_fees = []
    pending_fees = []

    total_pending = Decimal('0')
    total_estimated = Decimal('0')

    for fee in fees:
        monthly_fee = fee.student.total_fee
        total_estimated += monthly_fee

        if fee.amount_paid >= monthly_fee:
            paid_fees.append(fee)
        else:
            pending_amount = monthly_fee - fee.amount_paid
            total_pending += pending_amount
            pending_fees.append({
                'fee': fee,
                'pending': pending_amount
            })

    classes = SchoolClass.objects.all()

    months = Fee.MONTH_CHOICES

    return render(request, 'finance/fee_summary.html', {
        'paid_fees': paid_fees,
        'pending_fees': pending_fees,
        'total_collected': total_collected,
        'total_pending': total_pending,
        'total_estimated': total_estimated,
        'classes': classes,
        'months': months,
    })