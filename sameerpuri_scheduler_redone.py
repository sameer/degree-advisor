#!/bin/python
import course_dictionary as cd
from collections import namedtuple
from enum import IntEnum
from typing import Dict, List

Course = namedtuple('Course', 'program, designation')
CourseInfo = namedtuple('CourseInfo', 'credits, terms, prereqs')


class Semester(IntEnum):
    Fall = 1
    Spring = 2
    Summer = 3


class Year(IntEnum):
    Frosh = 0
    Sophomore = 1
    Junior = 2
    Senior = 3


class Term:
    def __init__(self, semester, year):
        self.semester = semester
        self.year = year
        semesterNo = Semester(semester)
        yearNo = Year(year)
        self.termNo = int(yearNo) * 3 + int(semesterNo)

    # Basically a second constructor
    @classmethod
    def initFromTermNo(clazz, termNo):
        # intentional integer division
        yearNo = int(int(termNo - 1) / int(3))
        semesterNo = termNo - (3 * yearNo)
        semester = Semester(semesterNo)
        year = Year(yearNo)
        return clazz(semester, year)

    def __hash__(self):
        return hash(self.termNo)

    def __eq__(self, other):
        return other and self.termNo == other.termNo

    def __ne__(self, other):
        return not self.__eq__(other)

    def __ge__(self, other):
        return self.termNo >= other.termNo

    def __repr__(self):
        # return "<Term semester:%s year:%s>" % (self.semester, self.year)
        return "(%s, %s)" % (self.semester, self.year)

    def __str__(self):
        # return "From str method of Term: semester is %s, year is %s" % (self.semester, self.year)
        return "(%s, %s)" % (self.semester, self.year)


class ScheduledCourse:
    def __init__(self, course, courseInfo, term: Term, clause: List[Course]):
        self.course = course
        self.courseInfo = courseInfo
        self.term = term
        self.clause = clause

    def __hash__(self):
        return hash((self.course, self.term, self.clause))

    def __eq__(self, other):
        return other and self.course == other.course and self.term == other.term and self.clause == other.clause

    def __ne__(self, other):
        return not self.__eq__(other)

    def __repr__(self):
        # return "<ScheduledCourse course:%s term:%s>" % (self.course, self.term)
        return "(%s, %s, %s)" % (self.course, self.term, self.clause)

    def __str__(self):
        return "course is %s, term is %s, pre is %s" % (self.course, self.term, self.clause)


def course_scheduler(course_descriptions: Dict[Course, CourseInfo], goal_conditions: List[Course], initial_state: List[Course]):
    # Run the internal scheduler, considering the initial state as part of an already scheduled plan
    result_plan = internal_scheduler(course_descriptions, goal_conditions, list(map(lambda course: ScheduledCourse(course, course_descriptions[course], Term(Semester.Summer, Year.Frosh), []), initial_state)), {})
    result_plan = list(filter(lambda sc: sc.term != Term(Semester.Summer, Year.Frosh), result_plan))
    push_higher_levels(course_descriptions, result_plan)
    print_schedule(result_plan)
    course_dict = {operator.course: CourseInfo(operator.courseInfo.credits, (operator.term.semester.name, operator.term.year.name), operator.clause) for operator in result_plan}
    return course_dict


def internal_scheduler(course_descriptions: Dict[Course, CourseInfo], goal_conditions: List[Course], current_plan: List[ScheduledCourse], memo: Dict[Course, int]):
    if len(goal_conditions) == 0:  # Everything is done!
        if is_valid_plan(current_plan):
            return current_plan
        else:
            return ()
    goal_conditions = make_unique(goal_conditions)  # Remove dupes

    goal = goal_conditions[0]
    goal_info = course_descriptions[goal]
    initial_state = list(filter(lambda sc: sc.term == Term(Semester.Summer, Year.Frosh), current_plan))
    min_height = minimum_tree_height(course_descriptions, goal, initial_state, memo)

    hours_per_term = get_hour_counts(current_plan)
    print("HERE", goal)

    for term in (map(lambda i: height_to_term(i), range(min_height, 9)) if not is_higher_level_course_info(goal_info) else [Term(Semester.Spring, Year.Senior)]):
        if int(goal_info.credits) + hours_per_term[term] > 18:  # Too many hours
            continue
        if term.semester.name not in goal_info.terms:  # Not offered in this term
            continue
        if goal in map(lambda op: op.course, current_plan):  # Course already taken
            continue
        if not is_higher_level_course_info(goal_info):
            violates_another = False
            for op in current_plan:
                if is_higher_level_course_info(op.courseInfo):
                    continue
                # Don't schedule at or after a user of the course
                if term >= op.term and goal in op.clause:
                    violates_another = True
                    break
            if violates_another:
                continue
        # Now we know scheduling the course is definitely possible...
        next_operation = ScheduledCourse(goal, goal_info, term, [])
        next_plan = current_plan[:]
        next_plan.append(next_operation)
        for dnf_clause in (goal_info.prereqs if len(goal_info.prereqs) != 0 else [[]]):
            if not is_higher_level_course_info(goal_info):
                violates_another = False
                for op in current_plan:
                    if is_higher_level_course_info(op.courseInfo):
                        continue
                    # Don't schedule before or at prereqs
                    if op.term >= term and op.course in dnf_clause:
                        violates_another = True
                        break
                if violates_another:
                    continue

            next_operation.clause = dnf_clause
            dnf_clause = list(dnf_clause)
            next_goal_conditions = goal_conditions[:]
            next_goal_conditions.remove(goal)
            next_goal_conditions = list(sorted(remove_fulfilled(dnf_clause, current_plan), key=lambda x: -minimum_tree_height(course_descriptions, x, initial_state, memo))) + next_goal_conditions
            print("Trying", next_operation)
            result_plan = internal_scheduler(course_descriptions, next_goal_conditions, next_plan, memo)  # Recurse deeper
            if not len(result_plan) == 0:
                print("Succeeded", next_operation)
                return result_plan
            print("Failed", next_operation)
            # TODO: check for dnf clauses that are effectively equivalent and skip them, especially for open electives
    return ()


def push_higher_levels(course_descriptions: Dict[Course, CourseInfo], plan: List[ScheduledCourse]):
    for i, hl_op in enumerate(plan):
        if not is_higher_level_course_info(hl_op.courseInfo):
            continue
        keep_pushing = True
        while keep_pushing and hl_op.term != Term(Semester.Spring, Year.Senior):
            for clause in hl_op.courseInfo.prereqs:
                if not any(req in (map(lambda op: op.course, filter(lambda op: op.term == hl_op.term, plan))) for req in clause):
                    keep_pushing = False
                    break
            if keep_pushing:
                hl_op.term=Term.initFromTermNo(hl_op.term.termNo + (1 if hl_op.term.semester == Semester.Fall else 2))
        keep_pushing = True
        while keep_pushing and hl_op.term != Term(Semester.Fall, Year.Frosh):
            for clause in hl_op.courseInfo.prereqs:
                if any(req in (map(lambda op: op.course, filter(lambda op: op.term == hl_op.term, plan))) for req in clause):
                    keep_pushing = False
                    break
            if keep_pushing:
                hl_op.term = Term.initFromTermNo(hl_op.term.termNo - (1 if hl_op.term.semester == Semester.Spring else 2))


def remove_fulfilled(dnf_clause: List[Course], plan: List[ScheduledCourse]):
    for op in plan:
        if op.course in dnf_clause:
            dnf_clause.remove(op.course)
    return dnf_clause


def is_valid_plan(current_plan: List[ScheduledCourse]):
    for term, hours in get_hour_counts(current_plan).items():
        if hours > 18:
            return False
    return True


def get_hour_counts(current_plan: List[ScheduledCourse]):
    hour_counts = {height_to_term(i): 0 for i in range(1, 9)}
    for operator in current_plan:
        if operator.term.semester is Semester.Summer:  # The scheduler doesn't handle summer yet
            continue
        hour_counts[operator.term] += int(operator.courseInfo.credits)
    return hour_counts


# How many semesters are needed to schedule myself and others?
def minimum_tree_height(course_descriptions: Dict[Course, CourseInfo], goal: Course, initial_state: List[ScheduledCourse], memo: Dict[Course, int]):
    if goal in map(lambda sc: sc.course, initial_state):
        return 0
    if len(course_descriptions[goal].prereqs) == 0:
        return 1
    if goal in memo:
        return memo[goal]
    goal_minimum = 20
    for prereq_clause in course_descriptions[goal].prereqs:  # Find the clause that is easiest to fulfill
        clause_maximum = 0
        for req in prereq_clause:
            subtree_height = (1 if not is_higher_level_course(course_descriptions, goal) else 0) + minimum_tree_height(course_descriptions, req, initial_state, memo)
            if subtree_height > clause_maximum:
                clause_maximum = subtree_height
        if clause_maximum < goal_minimum:
            goal_minimum = clause_maximum
    memo[goal] = goal_minimum
    return goal_minimum


def height_to_term(height: int):
    semester = Semester(((height+1) % 2) + 1)  # Spring or Fall?
    year = Year(int((height-1) / 2))
    return Term(semester, year)


def make_unique(seq):
    seen = set()
    seen_add = seen.add
    return [x for x in seq if not (x in seen or seen_add(x))]


def is_higher_level_course(course_descriptions: Dict[Course, CourseInfo], course: Course):
        return int(course_descriptions[course].credits) == 0


def is_higher_level_course_info(courseinfo: CourseInfo):
    return int(courseinfo.credits) == 0


def print_schedule(plan: List[ScheduledCourse]):
    schedule = {height_to_term(i): [] for i in range(1, 9)}
    for operator in plan:
        schedule[operator.term].append(operator)
    for term in schedule:
        hours = 0
        for operator in schedule[term]:
            hours += int(operator.courseInfo.credits)
        print(term, hours, " [")
        for operator in schedule[term]:
            if not is_higher_level_course_info(operator.courseInfo):
                print(operator, ",")
        print("]")


# COURSE_DICT = cd.create_course_dict()
# INITIAL_STATE = [Course('CS', '1101')]
# GOAL_CONDITIONS = [Course('CS', 'major')]
# print(course_scheduler(COURSE_DICT, GOAL_CONDITIONS, INITIAL_STATE))