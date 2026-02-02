from django import forms
from django.contrib.auth.models import User
from .models import TeacherProfile, Marks, DiaryEntry, SchoolClass, Subject,Student,Fee,Notice,DailyExpenditure,TeacherSalary,StudentCharge # <-- Add Marks here
from datetime import datetime

class TeacherCreationForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput)

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'username', 'email', 'password']
class StudentChargeForm(forms.ModelForm):
    class Meta:
        model = StudentCharge
        fields = [
            'charge_name',
            'school_class',
            'student',
            'date',
            'total_amount',
            'paid_amount',
        ]
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
        }

class TeacherProfileForm(forms.ModelForm):
    class Meta:
        model = TeacherProfile
        fields = ['phone', 'address', 'cnic', 'qualification', 'experience']
        widgets = {
            'joining_date': forms.DateInput(attrs={'type': 'date'})
        }

class AnnualSubForm(forms.ModelForm):
    class Meta:
        model = Student
        fields = ['annual_sub', 'annual_sub_paid']
        widgets = {
            'annual_sub': forms.NumberInput(attrs={'step': '0.01'}),
            'annual_sub_paid': forms.NumberInput(attrs={'step': '0.01'}),
        }
class MarksForm(forms.ModelForm):
    class Meta:
        model = Marks  # Now Python knows what Marks is
        fields = ['total_marks', 'obtained_marks']
        widgets = {
            'total_marks': forms.NumberInput(attrs={'class': 'form-control'}),
            'obtained_marks': forms.NumberInput(attrs={'class': 'form-control'}),
        }

class DiaryForm(forms.ModelForm):
    class Meta:
        model = DiaryEntry
        fields = ['school_class', 'subject', 'content']
        widgets = {
            'content': forms.Textarea(attrs={'rows': 3, 'class': 'homework-input', 'placeholder': 'Enter homework...'}),
        }

    def __init__(self, *args, **kwargs):
        teacher = kwargs.pop('teacher', None)
        super(DiaryForm, self).__init__(*args, **kwargs)
        if teacher:
            # Only show classes and subjects related to the teacher if needed
            self.fields['school_class'].queryset = SchoolClass.objects.all()
            self.fields['subject'].queryset = Subject.objects.all()
class StudentForm(forms.ModelForm):
    email = forms.EmailField(required=False, label="Student Email (Optional)")

    class Meta:
        model = Student
        fields = [
            'name', 'father_name', 'roll_no', 'cnic', 'phone', 
            'address', 'school_class', 'total_fee', 'annual_sub', 
            'remarks', 'joining_date', 'is_active', 'email'  # added email
        ]
        widgets = {
            'joining_date': forms.DateInput(attrs={'type': 'date'}),
            'annual_sub': forms.Textarea(attrs={'rows':2}),
            'remarks': forms.Textarea(attrs={'rows':2}),
            'address': forms.Textarea(attrs={'rows':2}),
        }
class FeeForm(forms.ModelForm):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        current_year = datetime.now().year
        self.fields['year'].choices = [
            (y, y) for y in range(2024, current_year + 1)
        ]
        self.fields['year'].initial = current_year

    class Meta:
        model = Fee
        fields = [
            'year', 'month', 'amount_paid',
            'payment_method', 'challan_no',
            'payment_screenshot'
        ]
MONTH_CHOICES = [
    (1, 'January'), (2, 'February'), (3, 'March'),
    (4, 'April'), (5, 'May'), (6, 'June'),
    (7, 'July'), (8, 'August'), (9, 'September'),
    (10, 'October'), (11, 'November'), (12, 'December')
]

class PendingDuesFilterForm(forms.Form):
    year = forms.ChoiceField(
        choices=[(y, y) for y in range(2024, datetime.now().year + 1)],
        initial=datetime.now().year,
        required=True,
        label='Year'
    )
    month_from = forms.ChoiceField(choices=MONTH_CHOICES, required=False, label='From Month')
    month_to = forms.ChoiceField(choices=MONTH_CHOICES, required=False, label='To Month')
    school_class = forms.ModelChoiceField(
        queryset=SchoolClass.objects.all(),
        required=False,
        empty_label="All Classes",
        label="Class"
    )
from django import forms
from .models import ExtraCurricularItem

class ExtraCurricularItemForm(forms.ModelForm):
    class Meta:
        model = ExtraCurricularItem
        fields = ['name', 'total_marks', 'is_attendance']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'total_marks': forms.NumberInput(attrs={'class': 'form-control'}),
            'is_attendance': forms.CheckboxInput(),
        }
class NoticeForm(forms.ModelForm):
    class Meta:
        model = Notice
        fields = ['title', 'content', 'link']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Title (optional)'}),
            'content': forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Type your notice here...', 'rows': 4}),
            'link': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'Optional link'}),
        }

class DailyExpenditureForm(forms.ModelForm):
    class Meta:
        model = DailyExpenditure
        fields = ['name', 'expense', 'time']
        widgets = {
            'time': forms.DateTimeInput(attrs={'type': 'datetime-local'})
        }

class TotalSalaryForm(forms.ModelForm):
    class Meta:
        model = TeacherSalary
        fields = ['teacher', 'name', 'total_salary']

class MonthlySalaryForm(forms.ModelForm):
    class Meta:
        model = TeacherSalary
        fields = ['teacher', 'name', 'salary', 'date']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'})
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Dropdown for existing external staff
        existing_names = (
            TeacherSalary.objects
            .filter(name__isnull=False)
            .values_list('name', flat=True)
            .distinct()
        )

        self.fields['name'] = forms.ChoiceField(
            required=False,
            choices=[('', '--- Select Staff ---')] + [(n, n) for n in existing_names]
        )