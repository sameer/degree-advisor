from flask import Flask, jsonify, render_template, request
from typing import List, Tuple
import course_dictionary as cd

import click
click.disable_unicode_literals_warning = True

import sameerpuri_scheduler as sps
import sameerpuri_matcher as spm
import sameerpuri_recommender as spr

app = Flask(__name__)

course_dict = cd.create_course_dict()
course_desc_dict = spm.create_course_desc_dict(course_dict)


@app.route('/course/<program>/<int:designation>/<reqtype>')
def get_course_desc(program: str, designation: int, reqtype: str):
    res = {
        'summary': lambda course: course_desc_dict[course].summary,
        'name': lambda course: course_desc_dict[course].name,
        'formerly': lambda course: course_desc_dict[course].formerly,
        'creditbracket': lambda course: course_desc_dict[course].creditbracket
    }[reqtype](cd.Course(program, str(designation)))
    return jsonify(res)


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/informer', methods=['GET', 'POST'])
def informer():
    error = None
    course = None
    course_info: spm.CourseDesc = None
    if request.method == 'POST':
        form_course: cd.Course = cd.Course(request.form['program'].strip(), request.form['designation'].strip())
        if form_course in course_desc_dict:
            course_info = course_desc_dict[form_course]
            course = form_course
        else:
            error = 'Course not found: ' + form_course
    return render_template('informer.html', error=error, course=course, course_info=course_info)


@app.route('/recommender', methods=['GET', 'POST'])
def recommender():
    error = None
    recommendation_list: List[Tuple] = None
    if request.method == 'POST':
        num: int = int(request.form['num'])
        str_courses: str = request.form['courses']
        try:
            str_course_list: List[str] = str_courses.split(';')
            courses: List[cd.Course] = []
            for course_str in str_course_list:
                course_split: List[str] = course_str.strip().split(' ')
                courses.append(cd.Course(course_split[0], course_split[1]))
            recommendation_list = spr.recommend_courses_using_liked_courses(courses, num)
        except KeyError as e:
            error = 'Course not found: ' + str(e)
    return render_template('recommender.html', error=error, recommendation_list=recommendation_list, course_desc_dict=course_desc_dict)


@app.route('/scheduler', methods=['GET', 'POST'])
def scheduler():
    error = None
    result_plan: List[Tuple] = None
    if request.method == 'POST':
        str_initial_state: str = request.form['initial_state']
        str_goal_conditions: str = request.form['goal_conditions']
        try:
            initial_state: List[cd.Course] = []
            goal_conditions: List[cd.Course] = []
            for course_str in str_initial_state.split(';'):
                course_split: List[str] = course_str.strip().split(' ')
                initial_state.append(cd.Course(course_split[0].strip(), course_split[1].strip()))
            for course_str in str_goal_conditions.split(';'):
                course_split: List[str] = course_str.strip().split(' ')
                goal_conditions.append(cd.Course(course_split[0].strip(), course_split[1].strip()))
            result_dict = sps.course_scheduler(course_dict, goal_conditions, initial_state)
            result_plan = list(sorted([(k,v) for k,v in result_dict.items()], key=lambda tuple: tuple[1].terms))
        except KeyError as e:
            error = 'Course not found: ' + str(e)
    return render_template('scheduler.html', error=error, result_plan=result_plan, course_desc_dict=course_desc_dict)
