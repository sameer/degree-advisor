#!/bin/python
import course_dictionary as cd
from collections import namedtuple
from enum import Enum
from more_itertools import unique_everseen
from functools import total_ordering


Course = namedtuple('Course', 'program, designation')

# Prerequisites are in disjunctive normal form ([course and course and course] or [course and course])
CourseInfo = namedtuple('CourseInfo', 'credits, terms, prereqs')

CourseUsable = namedtuple('CourseUsable', 'course, used')

@total_ordering
class ScheduledTerm(Enum):
    Fall_Frosh = 1
    Spring_Frosh = 2
    Fall_Soph = 3
    Spring_Soph = 4
    Fall_Junior = 5
    Spring_Junior = 6
    Fall_Senior = 7
    Spring_Senior = 8

    def __le__(self, other):
        if self.__class__ is other.__class__:
            return self.value <= other.value
        if other.__class__ == int:
            return self.value <= other
        return NotImplemented


CourseOperator = namedtuple('CourseOperator', 'pre, effect, scheduledterm, credits')

ScheduledCourse = namedtuple('ScheduledCourse', 'course, scheduledterm')


def course_scheduler(course_descriptions, goal_conditions, initial_state):
    usable_courses = list()
    for course in initial_state:
        usable_courses.append(CourseUsable(course, True))
    plan = dfs_recursive(course_descriptions, goal_conditions, usable_courses, [], 0)
    print_schedule(plan)
    course_dict = {}
    for operator in plan:
        course_dict[ScheduledCourse(operator.effect, operator.scheduledterm)] = course_descriptions[operator.effect]
    return course_dict


def dfs_recursive(course_descriptions, goal_conditions, usable_courses, current_plan, depth):
    goal_conditions = list(unique_everseen(goal_conditions))  # Remove goal duplicates
    # TODO: figure out what the requirement should be for this
    # TODO: how can I better handle what initial_state provides to head towards that state?
    # TODO: how can I deal with the consequence of my actions?
    # TODO: how can I handle requirements with < 12 hours in a semester? It would recurse infinitely
    # goal_conditions = remove_fulfilled_goals(goal_conditions, current_plan)  # Get rid of any fulfilled goals
    # Don't try to satisfy goals fulfilled by the initial state. If a match is found, remove it from initial_state too
    # goal_conditions = remove_already_fulfilled_goals(goal_conditions, initial_state)
    # goal_conditions = sorted(goal_conditions, key=lambda x: minimum_requirement_tree_height(course_descriptions, x))
    # Goal conditions satisfied: are the goal conditions empty or equal to the initial state?

    if len(goal_conditions) == 0:
        # if the plan isn't valid, the caller should be told
        if is_valid_plan(current_plan):
            return current_plan
        return ()

    # Use the first item in the goal_conditions list as the goal
    goal = goal_conditions[0]

    # These are the requirements for the goal in DNF form
    dnf_requirements = course_descriptions[goal].prereqs
    if len(dnf_requirements) == 0:  # If there aren't any requirements, assume an empty requirement case
        dnf_requirements = [[]]
    for dnf_clause in dnf_requirements:  # Try to fulfill each clause. The first clause that works is used.
        # Transform the list to match the namedtuple Course, just in case
        dnf_transformed_clause = list()
        for req in dnf_clause:
            dnf_transformed_clause.append(Course(*req))
        dnf_clause = dnf_transformed_clause

        revised_dnf_clause = (dnf_clause[:] if is_higher_level_course(course_descriptions, goal)
                              else remove_fulfilled_goals(dnf_clause[:], current_plan))

        used_courses = list()
        # for course in usable_courses:
        #     if course.course not in revised_dnf_clause:
        #         continue
        #     if is_higher_level_course(course_descriptions, goal):
        #         if not course.used:
        #             course.used = True
        #             revised_dnf_clause.remove(course.course)
        #             used_courses.append(course.course)
        #     else:
        #         revised_dnf_clause.remove(course.course)

        next_goal_conditions = (revised_dnf_clause + goal_conditions)
        next_goal_conditions.remove(goal)          # put in its prerequisites

        minimum_semesters_before = minimum_requirement_tree_height(course_descriptions, goal)

        # Try to schedule the goal in each term, starting from the first term if there are no prerequisites
        # and the last if there are any
        for term in ScheduledTerm if len(revised_dnf_clause) == 0 else reversed(ScheduledTerm):
            if len(revised_dnf_clause) > 0 and not is_higher_level_course(course_descriptions, goal) and minimum_semesters_before >= term:
                break

            # Formalize the operator we're trying to use here
            next_operator = CourseOperator(dnf_clause, goal, term, course_descriptions[goal].credits)
            # Series of sanity checks and limitations to make sure the operator is actually *possible*
            if operator_possible(course_descriptions, usable_courses, current_plan, next_operator):
                next_plan = current_plan[:]  # Clone the current plan and add the potential next operator
                next_plan.append(next_operator)

                # Ask the dfs to do the rest of the work :)
                result_plan = dfs_recursive(course_descriptions, next_goal_conditions, usable_courses, next_plan,
                                            depth + 1)
                if len(result_plan) != 0:  # If next_operator is a success, just go back up
                    return result_plan
        for course in used_courses:
            usable_courses.append(CourseUsable(course, True))
                # Otherwise we try the remaining variations of the next operator
    # This goal is impossible to satisfy, let the caller know
    # print("Failed with goal", depth, goal)
    # print_schedule(current_plan)
    return ()


def is_valid_plan(current_plan):
    hour_counts = {}
    for term in ScheduledTerm:
        hour_counts[term] = 0
    for operator in current_plan:
        hour_counts[operator.scheduledterm] += int(operator.credits)
    for term in ScheduledTerm:
        if hour_counts[term] > 18 or (hour_counts[term] < 12 and not hour_counts[term] == 0):
            return False
    return True


def remove_fulfilled_by_initial(initial_state, goal_conditions):
    for course in initial_state:
        if course in goal_conditions:
            goal_conditions.remove(course)
    return goal_conditions


def remove_fulfilled_goals(goal_conditions, current_plan):
    for operator in current_plan:
        if operator.effect in goal_conditions:
            goal_conditions.remove(operator.effect)
    return goal_conditions


def operator_possible(course_descriptions, initial_state, current_plan, next_operator):
    # Is the course available in the term next_operator schedules it for?
    if not next_operator.scheduledterm.name.split("_")[0] in course_descriptions[next_operator.effect].terms:
        return False

    # Was the course in next_operator already taken?
    for operator in current_plan:
        if operator.effect == next_operator.effect:
            return False

    # Will adding this course exceed the hours limit?
    hours_in_term = int(next_operator.credits)
    for operator in current_plan:
        if operator.scheduledterm == next_operator.scheduledterm:
            hours_in_term += int(operator.credits)
    if hours_in_term > 18:  # Too many hours in term
        return False

    # Don't even bother trying to schedule a course with prerequisites freshman year
    # that can't be satisfied by the initial state
    next_info = course_descriptions[next_operator.effect]
    if next_operator.scheduledterm == ScheduledTerm.Fall_Frosh and len(next_info.prereqs) != 0:
        is_fulfilled = False
        for prereq in next_info.prereqs:
            if set(prereq).issubset(initial_state):
                is_fulfilled = True
                break
        if not is_fulfilled:
            return False

    # Don't schedule a course in the same semester as its direct prerequisites or before them
    # Higher level requirements don't count
    if not is_higher_level_course(course_descriptions, next_operator.effect):
        if Course(designation='1301', program='MATH') in next_operator.pre:
            print("Checking it", next_operator)
        for operator in current_plan:
            if operator.scheduledterm <= next_operator.scheduledterm and not \
                    is_higher_level_course(course_descriptions, operator.effect) and next_operator.effect \
                    in operator.pre:
                return False
            if operator.scheduledterm >= next_operator.scheduledterm and not is_higher_level_course(course_descriptions, operator.effect) and operator.effect in next_operator.pre:
                return False
        if Course(designation='1301', program='MATH') in next_operator.pre:
            print("ohno", current_plan)

    # The operator has passed
    return True


memotable = {}


def minimum_requirement_tree_height(course_descriptions, course):
    if course in memotable:
        return memotable[course]
    if is_higher_level_course(course_descriptions, course):
        return 100
    dnf_clauses = course_descriptions[course].prereqs
    if len(dnf_clauses) == 0:
        return 0

    minimum = 0
    for dnf_clause in dnf_clauses:
        for req in dnf_clause:
            sz = 1 + minimum_requirement_tree_height(course_descriptions, req)
            if sz < minimum:
                minimum = sz
    memotable[course] = minimum
    return minimum


def is_higher_level_course(course_descriptions, course):
    try:
        return int(course_descriptions[course].credits) == 0
    except AttributeError:  # I messed up and forgot to convert a tuple into a namedtuple :(
        return is_higher_level_course(course_descriptions, Course(*course))
    except ValueError:
        return True


def print_schedule(plan):
    schedule = {}
    for term in ScheduledTerm:
        schedule[term] = []
    for operator in plan:
        schedule[operator.scheduledterm].append(operator)
    for term in ScheduledTerm:
        hours = 0
        for operator in schedule[term]:
            hours += int(operator.credits)
        print(term, hours, " [", end='')
        for operator in schedule[term]:
            # TODO: fix this
            if not is_higher_level_course(COURSE_DICT, operator.effect):
                print(operator, ",", end='')
        print("]")


COURSE_DICT = cd.create_course_dict()


INITIAL_STATE = [Course('CS', '1101')]  # The student has done nothing so far
GOAL_CONDITIONS = [Course('CS', 'major')] #[Course('CS', 'mathematics'), ('CS', 'core'), ('MATH', '3641'), ('CS', '1151'), ('MATH', '2410')]  # But the student wants a CS Major

print(course_scheduler(COURSE_DICT, GOAL_CONDITIONS, INITIAL_STATE))