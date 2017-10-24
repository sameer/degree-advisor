#!/bin/python
import course_dictionary as cd
from enum import Enum
from more_itertools import unique_everseen
from functools import total_ordering
from typing import Dict, List, NamedTuple, Tuple


class Course(NamedTuple):
    program: str
    designation: str


# Prerequisites are in DNF ([course and course and course] or [course and course])
class CourseInfo(NamedTuple):
    credits: int
    terms: Tuple[str]
    prereqs: Tuple[Tuple[Course]]


class CourseUsable(NamedTuple):
    course: Course
    used: bool


@total_ordering
class ScheduledTerm(Enum):
    Fall_Frosh: int = 1
    Spring_Frosh: int = 2
    Fall_Soph: int = 3
    Spring_Soph: int = 4
    Fall_Junior: int = 5
    Spring_Junior: int = 6
    Fall_Senior: int = 7
    Spring_Senior: int = 8

    def __le__(self, other):
        if self.__class__ is other.__class__:
            return self.value <= other.value
        if other.__class__ == int:
            return self.value <= other
        return NotImplemented


class CourseOperator(NamedTuple):
    pre: List[Course]
    effect: Course
    scheduledterm: ScheduledTerm
    credits: int


class ScheduledCourse(NamedTuple):
    course: Course
    scheduledterm: ScheduledTerm


def course_scheduler(course_descriptions: Dict[Course, CourseInfo], goal_conditions: List[Course],
                     initial_state: List[Course]):
    # Transform initial_state into a list of usable courses
    usable_courses = list(map(lambda i: CourseUsable(i, False), initial_state))
    # Call the internal planner
    plan = dfs_recursive(course_descriptions, goal_conditions, usable_courses)
    print_schedule(course_descriptions, plan)
    # Transform internal structure back to what the caller requires
    course_dict = {ScheduledCourse(operator.effect, operator.scheduledterm): course_descriptions[operator.effect] for
                   operator in plan}
    return course_dict


def dfs_recursive(course_descriptions: Dict[Course, CourseInfo], goal_conditions: List[Course],
                  initial_state: List[CourseUsable], current_plan: List[CourseOperator] = list(), depth: int = 0):
    goal_conditions = list(unique_everseen(goal_conditions))  # Remove duplicate goals
    # TODO: figure out what the requirement should be for this
    # TODO: how can I better handle what initial_state provides to head towards that state?
    # TODO: how can I deal with the consequence of my actions?
    # TODO: how can I handle requirements with < 12 hours in a semester? It would recurse infinitely

    # Goal conditions satisfied: are the goal conditions empty?
    if len(goal_conditions) == 0:
        # if the plan isn't valid, the caller should be told
        if is_valid_plan(current_plan):
            return current_plan
        return ()

    # Use the first item in the goal_conditions list as the current goal
    goal = goal_conditions[0]

    # Requirements for the goal in DNF form
    dnf_requirements = course_descriptions[goal].prereqs
    if len(dnf_requirements) == 0:  # If there aren't any requirements, assume an empty requirement case
        dnf_requirements = [[]]
    # Sort the requirement clauses so the ones that are hardest to fulfill are handled first
    # These requirements are definitive of the course schedule (i.e. CS math), while others are small and highly
    # variable (i.e. CS openelectives)
    dnf_requirements = sorted(dnf_requirements,
                              key=lambda clause:
                              -minimum_requirement_tree_height(course_descriptions, clause, current_plan))
    for dnf_clause in dnf_requirements:  # Try to fulfill each clause. The first clause that works is used.
        # The requirements for non-higher-level courses should be met
        dnf_clause = list(dnf_clause)
        revised_dnf_clause = (
            dnf_clause[:] if is_higher_level_course(course_descriptions, goal) else remove_fulfilled_goals(
                dnf_clause[:],
                current_plan))
        # Try to use courses from the initial state to fulfill this clause
        used_courses = list()
        for i, usable_course in enumerate(initial_state[:]):
            if usable_course.course not in revised_dnf_clause:
                continue
            if is_higher_level_course(course_descriptions, goal):
                if not usable_course.used:  # For higher-level requirements, a usable course must be consumed
                    initial_state[i] = CourseUsable(usable_course.course, True)
                    revised_dnf_clause.remove(usable_course.course)
                    used_courses.append(usable_course.course)
            else:  # For non-higher-level requirements, a satisfied course means just eliminate it
                revised_dnf_clause.remove(usable_course.course)

        # Remove the goal and put in its prerequisites
        next_goal_conditions = (revised_dnf_clause + goal_conditions)
        next_goal_conditions.remove(goal)

        # Calculate the minimum semesters required
        minimum_semesters_before = minimum_requirement_tree_height(course_descriptions, revised_dnf_clause,
                                                                   current_plan)

        # Try to schedule the goal in each possible term
        terms_to_look_at = list(ScheduledTerm(i) for i in range(minimum_semesters_before + 1, 9))
        if is_higher_level_course(course_descriptions, goal):  # Higher level reqs should be looked at in reverse
            terms_to_look_at = reversed(terms_to_look_at)
        for term in terms_to_look_at:
            # Formalize the operator we're trying to use here
            next_operator = CourseOperator(dnf_clause, goal, term, course_descriptions[goal].credits)
            # Series of sanity checks and limitations to make sure the operator is actually *possible*
            if operator_possible(course_descriptions, current_plan, next_operator):
                next_plan = current_plan
                next_plan.append(next_operator)  # Add the potential next operator
                # Ask the dfs to do the rest of the work :)
                result_plan = dfs_recursive(course_descriptions, next_goal_conditions, initial_state, next_plan,
                                            depth + 1)
                if len(result_plan) != 0:  # If next_operator is a success, just go back up
                    return result_plan
                next_plan.remove(next_operator)  # Or just remove the operator
        # All iterations failed, reset all the used_courses
        for usable_course in used_courses:
            initial_state[initial_state.index(usable_course)] = CourseUsable(usable_course.course, False)
    # This goal is impossible to satisfy, let the caller know
    return ()


def is_valid_plan(current_plan: List[CourseOperator]):
    hour_counts = {term: 0 for term in ScheduledTerm}
    for operator in current_plan:
        hour_counts[operator.scheduledterm] += int(operator.credits)
    for term, hours in hour_counts.items():
        if hours > 18 or (hours < 12 and not hours == 0):
            return False
    return True


def remove_fulfilled_goals(goal_conditions: List[Course], current_plan: List[CourseOperator]):
    for operator in current_plan:
        if operator.effect in goal_conditions:
            goal_conditions.remove(operator.effect)
    return goal_conditions


def operator_possible(course_descriptions: Dict[Course, CourseInfo], current_plan: List[CourseOperator],
                      next_operator: CourseOperator):
    # Is the course available in the term next_operator schedules it for?
    if not next_operator.scheduledterm.name.split("_")[0] in course_descriptions[next_operator.effect].terms:
        return False

    hours_in_term = int(next_operator.credits)
    for operator in current_plan:
        # Was the course in next_operator already taken?
        if operator.effect == next_operator.effect:
            return False
        if operator.scheduledterm == next_operator.scheduledterm:
            hours_in_term += int(operator.credits)

        # Don't schedule a course in the same semester as its direct prerequisites or before them
        # Don't schedule a course whose effect is a prerequisite of a course scheduled before it
        # Higher level requirements don't count
        if (not is_higher_level_operator(next_operator) and not is_higher_level_operator(operator)) and \
                ((operator.scheduledterm <= next_operator.scheduledterm and next_operator.effect in operator.pre)
                 or (operator.scheduledterm >= next_operator.scheduledterm and operator.effect in next_operator.pre)):
            return False

    # Will adding this course exceed the hours limit?
    if hours_in_term > 18:  # Too many hours in term
        return False

    # The operator has passed
    return True


def minimum_requirement_tree_height(course_descriptions: Dict[Course, CourseInfo], dnf_clause: List[Course],
                                    current_plan: List[CourseOperator]):  # maximin
    if len(dnf_clause) == 0:
        return 0

    maximum = 0
    for req in dnf_clause:  # dnf_clause was selected, find the tree length required for it to be fulfilled, (max)
        lmin = 0
        if req in current_plan:
            continue
        for clause in course_descriptions[req].prereqs:  # find the length of the smallest clause for req
            clause = list(clause)
            sz = 1 + minimum_requirement_tree_height(course_descriptions, clause, current_plan)
            if sz < lmin:
                lmin = sz
        if lmin > maximum:
            maximum = lmin
    return maximum


def is_higher_level_course(course_descriptions: Dict[Course, CourseInfo], course: Course):
    return int(course_descriptions[course].credits) == 0


def is_higher_level_operator(operator: CourseOperator):
    return int(operator.credits) == 0


def print_schedule(course_descriptions: Dict[Course, CourseInfo], plan: List[CourseOperator]):
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
            if not is_higher_level_course(course_descriptions, operator.effect):
                print(operator, ",")
        print("]")


COURSE_DICT = cd.create_course_dict()
INITIAL_STATE = [Course('CS', '1101')]
GOAL_CONDITIONS = [Course('CS', 'mathematics'), Course('CS', 'core'), Course('MATH', '3641'), Course('CS', '1151'),
                   Course('MATH', '2410')]

print(course_scheduler(COURSE_DICT, GOAL_CONDITIONS, INITIAL_STATE))
