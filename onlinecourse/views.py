from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.views import generic
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.models import User
from .models import Course, Enrollment, Question, Choice, Submission
import logging

logger = logging.getLogger(__name__)


# ==========================
# Registration
# ==========================
def registration_request(request):
    context = {}
    if request.method == 'GET':
        return render(request, 'onlinecourse/user_registration_bootstrap.html', context)

    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['psw']
        first_name = request.POST['firstname']
        last_name = request.POST['lastname']

        if User.objects.filter(username=username).exists():
            context['message'] = "User already exists."
            return render(request, 'onlinecourse/user_registration_bootstrap.html', context)

        user = User.objects.create_user(
            username=username,
            password=password,
            first_name=first_name,
            last_name=last_name
        )
        login(request, user)
        return redirect('onlinecourse:index')


# ==========================
# Login
# ==========================
def login_request(request):
    context = {}
    if request.method == "POST":
        username = request.POST['username']
        password = request.POST['psw']
        user = authenticate(username=username, password=password)

        if user:
            login(request, user)
            return redirect('onlinecourse:index')
        else:
            context['message'] = "Invalid username or password."

    return render(request, 'onlinecourse/user_login_bootstrap.html', context)


# ==========================
# Logout
# ==========================
def logout_request(request):
    logout(request)
    return redirect('onlinecourse:index')


# ==========================
# Check Enrollment
# ==========================
def check_if_enrolled(user, course):
    if user.is_authenticated:
        return Enrollment.objects.filter(user=user, course=course).exists()
    return False


# ==========================
# Course List View
# ==========================
class CourseListView(generic.ListView):
    template_name = 'onlinecourse/course_list_bootstrap.html'
    context_object_name = 'course_list'

    def get_queryset(self):
        user = self.request.user
        courses = Course.objects.order_by('-total_enrollment')[:10]
        for course in courses:
            if user.is_authenticated:
                course.is_enrolled = check_if_enrolled(user, course)
        return courses


# ==========================
# Course Detail View
# ==========================
class CourseDetailView(generic.DetailView):
    model = Course
    template_name = 'onlinecourse/course_detail_bootstrap.html'


# ==========================
# Enroll
# ==========================
def enroll(request, course_id):
    course = get_object_or_404(Course, pk=course_id)
    user = request.user

    if user.is_authenticated and not check_if_enrolled(user, course):
        Enrollment.objects.create(user=user, course=course, mode='honor')
        course.total_enrollment += 1
        course.save()

    return HttpResponseRedirect(
        reverse('onlinecourse:course_details', args=(course.id,))
    )


# ==========================
# Extract Answers
# ==========================
def extract_answers(request):
    submitted_answers = []
    for key in request.POST:
        if key.startswith('choice'):
            submitted_answers.append(int(request.POST[key]))
    return submitted_answers


# ==========================
# Submit Exam
# ==========================
def submit(request, course_id):
    course = get_object_or_404(Course, pk=course_id)
    user = request.user

    enrollment = get_object_or_404(Enrollment, user=user, course=course)

    submission = Submission.objects.create(enrollment=enrollment)

    selected_choice_ids = extract_answers(request)
    submission.choices.set(selected_choice_ids)

    return HttpResponseRedirect(
        reverse('onlinecourse:exam_result',
                args=(course.id, submission.id,))
    )


# ==========================
# Show Exam Result
# ==========================
def show_exam_result(request, course_id, submission_id):

    course = get_object_or_404(Course, pk=course_id)
    submission = get_object_or_404(Submission, pk=submission_id)

    choices = submission.choices.all()
    questions = course.question_set.all()

    total_score = 0
    total_possible_score = 0

    for question in questions:
        total_possible_score += question.grade

        correct_choices = question.choice_set.filter(is_correct=True)
        selected_choices = choices.filter(question=question)

        if set(correct_choices) == set(selected_choices):
            total_score += question.grade

    context = {
        'course': course,
        'submission': submission,
        'questions': questions,
        'choices': choices,
        'grade': total_score,
        'total_possible_score': total_possible_score,
    }

    return render(request,
                  'onlinecourse/exam_result_bootstrap.html',
                  context)