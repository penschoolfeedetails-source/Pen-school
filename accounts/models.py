from django.db import models
from django.contrib.auth.models import User
from datetime import date
from django.utils.timezone import now
from django.utils import timezone
# Create your models here.
class TeacherProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    phone = models.CharField(max_length=15)
    address = models.TextField(blank=True)
    cnic = models.CharField(max_length=13)
    qualification = models.CharField(max_length=100, blank=True, null=True)
    experience = models.IntegerField(blank=True, null=True)
    salary = models.IntegerField(blank=True, null=True)
    joining_date = models.DateField(auto_now_add=True)

    def __str__(self):
        return self.user.first_name

class SchoolClass(models.Model):
    name = models.CharField(max_length=50)
    section = models.CharField(max_length=10,blank=True,null=True)
    
    def __str__(self):
        return f"{self.name} {self.section}"
from django.db import models
from django.utils.timezone import now

class Student(models.Model):
    name = models.CharField(max_length=100)
    father_name = models.CharField(max_length=100)
    roll_no = models.CharField(max_length=20)
    cnic = models.CharField(max_length=13)
    phone = models.CharField(max_length=15)
    email = models.EmailField(max_length=100, blank=True, null=True)
    address = models.TextField(blank=True)
    school_class = models.ForeignKey(
        SchoolClass,
        on_delete=models.CASCADE,
        related_name='students'
    )
    total_fee = models.DecimalField(max_digits=10, decimal_places=2)
    annual_sub = models.IntegerField(default=0)
    annual_sub_paid = models.IntegerField(default=0)
    remarks = models.TextField(blank=True)
    joining_date = models.DateField(default=now)
    is_active = models.BooleanField(default=True)

    def save(self, *args, **kwargs):
        # Auto-assign roll_no only if it's empty
        if not self.roll_no:
            # Find the max roll_no in this class
            last_roll = Student.objects.filter(
                school_class=self.school_class
            ).order_by('-id').first()

            if last_roll and last_roll.roll_no:
                # Extract numeric part from last roll_no
                try:
                    last_number = int(last_roll.roll_no.split('-')[-1])
                except ValueError:
                    last_number = 0
            else:
                last_number = 0

            # New roll_no formatted as ClassName-Number (e.g., 6-001)
            class_name = str(self.school_class)  # assumes SchoolClass __str__ gives class name
            self.roll_no = f"{class_name}-{last_number + 1:03d}"

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({self.roll_no})"

class Attendance(models.Model):
    school_class = models.ForeignKey(SchoolClass, on_delete=models.CASCADE)
    teacher = models.ForeignKey(User, on_delete=models.CASCADE)
    date = models.DateField(auto_now_add=True)

    class Meta:
        unique_together = ('school_class', 'date')

    def __str__(self):
        return f"{self.school_class} - {self.date}"

# Individual Attendance Record per Student
class AttendanceRecord(models.Model):
    STATUS_CHOICES = [
        ('P', 'Present'),
        ('L', 'Late'),
        ('A', 'Absent'),
        ('SL','Short Leave')  # New status
    ]

    attendance = models.ForeignKey(
        Attendance,
        on_delete=models.CASCADE,
        related_name='records'
    )
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    status = models.CharField(max_length=2, choices=STATUS_CHOICES)
    remarks = models.TextField(blank=True, null=True)  # optional remarks

    def __str__(self):
        return f"{self.student.name} - {self.status}"

class Subject(models.Model):
    name = models.CharField(max_length=100)
    school_class = models.ForeignKey(
        SchoolClass,
        on_delete=models.CASCADE,
        related_name='subjects'
    )
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} ({self.school_class})"



class Term(models.Model):
    name = models.CharField(max_length=50)
    start_date = models.DateField()
    end_date = models.DateField()
    is_current = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        if self.is_current:
            Term.objects.filter(is_current=True).exclude(pk=self.pk).update(is_current=False)
        super().save(*args, **kwargs)



class Marks(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='marks')
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='marks')
    term = models.ForeignKey(Term, on_delete=models.CASCADE)
    total_marks = models.IntegerField()
    obtained_marks = models.IntegerField()

    class Meta:
        unique_together = ('student', 'subject', 'term')

    def __str__(self):
        return f"{self.student.name} - {self.subject.name} - {self.term.name}"

class DiaryEntry(models.Model):
    teacher = models.ForeignKey(User, on_delete=models.CASCADE)
    subject = models.ForeignKey('Subject', on_delete=models.CASCADE)
    school_class = models.ForeignKey('SchoolClass', on_delete=models.CASCADE)
    content = models.TextField()
    date = models.DateField(default=now)

    class Meta:
        unique_together = ('subject', 'school_class', 'date')

    def __str__(self):
        return f"{self.school_class} - {self.subject.name} - {self.date}"

class StudentComplaint(models.Model):
    teacher = models.ForeignKey(User, on_delete=models.CASCADE)
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    school_class = models.ForeignKey(SchoolClass, on_delete=models.CASCADE)
    date = models.DateField(auto_now_add=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.student.name} - {self.date}"
class ComplaintSubject(models.Model):
    complaint = models.ForeignKey(
        StudentComplaint,
        related_name='subjects',
        on_delete=models.CASCADE
    )
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    remarks = models.TextField()

    def __str__(self):
        return self.subject.name


class Fee(models.Model):

    PAYMENT_METHODS = [
        ('cash', 'Cash'),
        ('online', 'Online'),
    ]

    STATUS_CHOICES = [
        ('paid', 'Paid'),
        ('partial', 'Partial'),
        ('unpaid', 'Unpaid'),
    ]

    student = models.ForeignKey(
        'Student',
        on_delete=models.CASCADE,
        related_name='fees'
    )

    year = models.IntegerField()
    MONTH_CHOICES = [
    (1, 'January'), (2, 'February'), (3, 'March'),
    (4, 'April'), (5, 'May'), (6, 'June'),
    (7, 'July'), (8, 'August'), (9, 'September'),
    (10, 'October'), (11, 'November'), (12, 'December')
]

    month = models.IntegerField(choices=MONTH_CHOICES)


    amount_paid = models.DecimalField(max_digits=10, decimal_places=2)

    payment_method = models.CharField(
        max_length=10,
        choices=PAYMENT_METHODS,
        default='cash'
    )

    challan_no = models.CharField(
        max_length=50,
        blank=True,
        null=True
    )

    payment_screenshot = models.ImageField(
        upload_to='fee_receipts/',
        blank=True,
        null=True
    )

    payment_date = models.DateField(default=now)

    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES
    )

    submitted_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('student', 'year', 'month')
        ordering = ['-year', '-month']

    def __str__(self):
        return f"{self.student.name} - {self.month}/{self.year}"
class FeeAudit(models.Model):
    generated_by = models.ForeignKey(User, on_delete=models.CASCADE)
    file = models.FileField(upload_to='fee_audits/')
    description = models.CharField(max_length=255)
    generated_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.description} ({self.generated_at.strftime('%Y-%m-%d')})"
class Dossier(models.Model):
    STATUS_CHOICES = [
        ('EXCELLENT', 'Excellent'),
        ('GOOD', 'Good'),
        ('SATISFACTORY', 'Satisfactory'),
    ]

    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='dossiers')
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)

    class Meta:
        unique_together = ('student', 'subject')

    def __str__(self):
        return f"{self.student.name} - {self.subject.name} - {self.status}"
class PersonalAttribute(models.Model):
    student = models.ForeignKey('Student', on_delete=models.CASCADE)
    term = models.ForeignKey('Term', on_delete=models.CASCADE)
    attribute = models.CharField(max_length=100)
    level = models.CharField(max_length=20, choices=[('Excellent', 'Excellent'), 
                                                     ('Good', 'Good'), 
                                                     ('Satisfactory', 'Satisfactory')],
                             blank=True, null=True)  # The selected level

    class Meta:
        unique_together = ('student', 'term', 'attribute')

    def __str__(self):
        return f"{self.student.name} - {self.attribute} ({self.term.name}): {self.level}"


class ExtraCurricularItem(models.Model):
    name             = models.CharField(max_length=100)
    total_marks      = models.PositiveIntegerField()
    is_attendance    = models.BooleanField(default=False)
    school_class     = models.ForeignKey('SchoolClass', on_delete=models.CASCADE)
    term             = models.ForeignKey('Term', on_delete=models.CASCADE)
    from_date        = models.DateField(null=True, blank=True)
    to_date          = models.DateField(null=True, blank=True)

    class Meta:
        unique_together = ('name', 'school_class', 'term')
        ordering = ['name']

    def __str__(self):
        return self.name


class ExtraCurricularMarks(models.Model):
    student       = models.ForeignKey('Student', on_delete=models.CASCADE)
    item          = models.ForeignKey(ExtraCurricularItem, on_delete=models.CASCADE)
    term          = models.ForeignKey('Term', on_delete=models.CASCADE)
    obtained_marks = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        unique_together = ('student', 'item', 'term')

    def __str__(self):
        return f"{self.student} – {self.item}"
    
class ReportCardPDF(models.Model):
    student = models.ForeignKey('Student', on_delete=models.CASCADE)
    school_class = models.ForeignKey('SchoolClass', on_delete=models.CASCADE)  # direct link
    term = models.ForeignKey('Term', on_delete=models.CASCADE)
    file = models.FileField(upload_to='report_cards/')
    generated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    generated_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.student.name} - {self.school_class.name} - {self.term.name}"

class ClassSyllabusTopic(models.Model):
    term = models.ForeignKey(Term, on_delete=models.CASCADE)
    school_class = models.ForeignKey(SchoolClass, on_delete=models.CASCADE)
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    topic_name = models.CharField(max_length=255)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = ('term', 'school_class', 'subject', 'topic_name')
        ordering = ['topic_name']

    def __str__(self):
        return self.topic_name
class Notice(models.Model):
    title = models.CharField(max_length=255, blank=True)
    content = models.TextField()
    link = models.URLField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.title or self.content[:30]

    def save(self, *args, **kwargs):
        # deactivate old notices when saving a new one
        if self.is_active:
            Notice.objects.filter(is_active=True).update(is_active=False)
        super().save(*args, **kwargs)


class DailyExpenditure(models.Model):
    name = models.CharField(max_length=200)
    expense = models.DecimalField(max_digits=10, decimal_places=2)
    time = models.DateTimeField(default=timezone.now)  # defaults to now, editable

    def __str__(self):
        return f"{self.name} - {self.expense}"
class TeacherSalary(models.Model):
    teacher = models.ForeignKey(TeacherProfile, on_delete=models.CASCADE, blank=True, null=True)
    name = models.CharField(max_length=200, blank=True, null=True)  # for extra staff
    total_salary = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)  # fixed total
    salary = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)  # monthly salary
    date = models.DateField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        if self.teacher:
            return f"{self.teacher.user.first_name} - {self.salary or self.total_salary}"
        return f"{self.name} - {self.salary or self.total_salary}"
class StudentCharge(models.Model):
    charge_name = models.CharField(max_length=150)

    school_class = models.ForeignKey(
        SchoolClass,
        on_delete=models.PROTECT,
        related_name='student_charges'
    )

    student = models.ForeignKey(
        Student,
        on_delete=models.PROTECT,
        related_name='charges'
    )

    date = models.DateField(default=timezone.now)

    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    paid_amount = models.DecimalField(max_digits=10, decimal_places=2)

    created_at = models.DateTimeField(auto_now_add=True)

    def balance(self):
        return self.total_amount - self.paid_amount

    def __str__(self):
        return f"{self.charge_name} - {self.student.name}"
