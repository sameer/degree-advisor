#!/bin/python
import course_dictionary as cd
from enum import IntEnum
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
    taken: bool


class CourseHLCheck(NamedTuple):
    course: Course
    directlyfromhlreq: bool

    def __eq__(self, other):
        return self.course == other.course


@total_ordering
class ScheduledTerm(IntEnum):
    Fall_Frosh: int = 1
    Spring_Frosh: int = 2
    Fall_Sophomore: int = 3
    Spring_Sophomore: int = 4
    Fall_Junior: int = 5
    Spring_Junior: int = 6
    Fall_Senior: int = 7
    Spring_Senior: int = 8


class CourseOperator(NamedTuple):
    pre: List[Course]
    effect: Course
    scheduledterm: ScheduledTerm
    credits: int
    used: bool


class ScheduledCourse(NamedTuple):
    course: Course
    courseInfo: CourseInfo
    term: Tuple


def uniquify(seq):
    seen = set()
    seen_add = seen.add
    return [x for x in seq if not (x in seen or seen_add(x))]


def course_scheduler(course_descriptions: Dict[Course, CourseInfo], goal_conditions: List[Course],
                     initial_state: List[Course]):
    # Transform initial_state into a list of usable courses
    usable_courses = list(map(lambda i: CourseUsable(i, False), initial_state))
    # Remove duplicate goals
    goal_conditions = uniquify(goal_conditions)
    # Call the internal planner
    plan = dfs_recursive(course_descriptions, list(map(lambda goal: CourseHLCheck(goal, is_higher_level_course(course_descriptions, goal)), goal_conditions)), usable_courses)
    # Schedule higher level requirements in the semester that they are fulfilled
    push_higher_levels(course_descriptions, plan)
    # Transform internal structure back to what the caller requires
    # TODO: fix < 12 hour handling to pad courses
    course_dict = {operator.effect: (operator.credits, (operator.scheduledterm.name.split("_")[0], operator.scheduledterm.name.split("_")[1]), operator.pre) for operator in plan}
    print_schedule(course_descriptions, plan)
    return course_dict


def dfs_recursive(course_descriptions: Dict[Course, CourseInfo], goal_conditions: List[CourseHLCheck],
                  initial_state: List[CourseUsable], current_plan: List[CourseOperator] = list(), depth: int = 0):
    # Are the goal conditions empty?
    if len(goal_conditions) == 0:
        if is_valid_plan(current_plan):
            return current_plan
        # if the plan isn't valid, the caller should be told
        return ()

    # Use the first item in the goal_conditions list as the current goal
    goal = goal_conditions[0]

    # Someone has already used this goal. This means it shouldn't even be tried.
    # TODO: fix this
    # if goal in map(lambda op: op.effect, current_plan):
    #     print("Goal already taken", goal)
    #     return ()

    # Requirements for the current goal in DNF form
    dnf_requirements = course_descriptions[goal.course].prereqs
    if len(dnf_requirements) == 0:  # If there aren't any requirements, it is an empty requirement case
        dnf_requirements = [[]]
    # Sort the requirement clauses so those that are easiest to fulfill are tried first
    dnf_requirements = sorted(dnf_requirements,
                              key=lambda clause:
                              heuristic_distance(course_descriptions, clause, initial_state, goal_conditions, current_plan))
    for dnf_clause in dnf_requirements:  # Try each clause. The first clause that works is used.
        dnf_clause = list(dnf_clause)
        # The requirements for non-higher-level courses can be automatically met
        revised_dnf_clause = (
            dnf_clause[:] if is_higher_level_course(course_descriptions, goal.course) else remove_fulfilled_goals(
                dnf_clause[:],
                current_plan))

        # Try to use courses from the initial state to fulfill this clause. If a higher level requirement uses the
        # course, it is "taken".
        used_courses = []
        for i, usable_course in enumerate(initial_state):
            if usable_course.course not in revised_dnf_clause:
                continue
            if is_higher_level_course(course_descriptions, goal.course):
                if not usable_course.taken:  # For higher-level requirements, a usable course must be consumed
                    initial_state[i] = CourseUsable(usable_course.course, True)
                    revised_dnf_clause.remove(usable_course.course)
                    used_courses.append(usable_course)
            else:  # For non-higher-level requirements, a satisfied course means just eliminate it
                revised_dnf_clause.remove(usable_course.course)

        # Try to use courses from the current plan that weren't already used by another higher level requirement
        used_ops = []
        for i, op in enumerate(current_plan):
            if op.effect not in revised_dnf_clause:
                continue
            if not goal.directlyfromhlreq and is_higher_level_course(course_descriptions, goal.course):
                # We are currently looking at a higher level course that wants to consume courses from the current
                # plan that were filled in by a string of normal courses
                if not op.used:  # Consume if not used
                    op = op._replace(used=True)
                    current_plan[i] = op
                    used_ops.append(op)
                    revised_dnf_clause.remove(op.effect)
                    print("Marking", op, "used by", goal)
            else:
                revised_dnf_clause.remove(op.effect)

        # Sort the revised clause members so the longest to fulfill parts are tried first
        # These parts are definitive of the course schedule (i.e. CS math), while others are small and highly
        # variable (i.e. CS openelectives)
        revised_dnf_clause = sorted(revised_dnf_clause, key=lambda course: -minimum_requirement_tree_height(course_descriptions, [course]))

        # Convert the clause into the goal conditions format, based upon whether the current goal is a higher level
        # course or not
        revised_dnf_clause = list(map(lambda course: CourseHLCheck(course, is_higher_level_course(course_descriptions, goal.course)), revised_dnf_clause))

        # Remove the current goal and insert its prerequisites at the front of next goal conditions
        next_goal_conditions = (revised_dnf_clause + goal_conditions)
        next_goal_conditions.remove(goal)

        # Calculate the minimum semesters required
        minimum_semesters_before = 0 if len(dnf_clause) == 0 else 1 + minimum_requirement_tree_height(course_descriptions, dnf_clause)
        print("Depth for", goal, minimum_semesters_before, "with", dnf_clause)

        if is_higher_level_course(course_descriptions, goal.course):  # Higher lvl req scheduling doesn't really matter.
            terms_to_look_at = [ScheduledTerm.Spring_Senior]   # just figure them out later
        else:
            # Try to schedule the course in each possible term, ordered by what's the best
            terms_to_look_at = list(i for i in ScheduledTerm)
            terms_to_look_at = sorted(terms_to_look_at,
                                      key=lambda t: (minimum_semesters_before - t.value) if (minimum_semesters_before + 1 - t.value) > 0 else abs(minimum_semesters_before - t.value) - 1)
        print("considering term order", terms_to_look_at)
        for term in terms_to_look_at:
            # Formalize the operator we're trying to use here
            next_operator = CourseOperator(dnf_clause, goal.course, term, course_descriptions[goal.course].credits, used=goal.directlyfromhlreq)
            # Series of sanity checks and limitations to make sure the operator is actually *possible*
            if operator_possible(course_descriptions, current_plan, next_operator):
                next_plan = current_plan
                next_plan.append(next_operator)  # Add the potential next operator
                # Ask the dfs to do the rest of the work :)
                print("Trying", next_operator, "WITH GOALS", next_goal_conditions)
                result_plan = dfs_recursive(course_descriptions, next_goal_conditions, initial_state, next_plan,
                                            depth + 1)
                if len(result_plan) != 0:  # If next_operator is a success, just go back up
                    return result_plan
                next_plan.remove(next_operator)  # Or just remove the operator
                print("That semester failed", goal)
        print("Next dnf clause", goal)
        # All iterations failed, reset all the used_courses
        for usable_course in used_courses:
            if usable_course in initial_state:
                initial_state[initial_state.index(usable_course)] = CourseUsable(usable_course.course, False)
            else:
                initial_state.append(CourseUsable(usable_course.course, False))
        for op in used_ops:
            current_plan[current_plan.index(op)] = op._replace(used=False)
        if len(dnf_clause) == 0: # We failued with no prereqs, no go
            break
    print("Overall failure", goal)
    print_schedule(course_descriptions, current_plan)
    # This goal is impossible to satisfy, let the caller know
    return ()


def is_valid_plan(current_plan: List[CourseOperator]):
    hour_counts = {term: 0 for term in ScheduledTerm}
    for operator in current_plan:
        hour_counts[operator.scheduledterm] += int(operator.credits)
    for term, hours in hour_counts.items():
        if hours > 18:
            return False
    return True


def remove_fulfilled_goals(revised_dnf_clause: List[Course], current_plan: List[CourseOperator]):
    for operator in current_plan:
        if operator.effect in revised_dnf_clause:
            revised_dnf_clause.remove(operator.effect)
    return revised_dnf_clause


def operator_possible(course_descriptions: Dict[Course, CourseInfo], current_plan: List[CourseOperator],
                      next_operator: CourseOperator):
    # Is the course available in the term next_operator schedules it for?
    if not next_operator.scheduledterm.name.split("_")[0] in course_descriptions[next_operator.effect].terms:
        print("Not offered in", next_operator.scheduledterm, course_descriptions[next_operator.effect].terms, next_operator)
        return False

    hours_in_term = int(next_operator.credits)
    for operator in current_plan:
        # Was the course in next_operator already taken?
        if operator.effect == next_operator.effect:
            print("Course already taken", next_operator)
            return False
        if operator.scheduledterm == next_operator.scheduledterm:
            hours_in_term += int(operator.credits)

        # Don't schedule a course in the same semester as its direct prerequisites or before them
        # Don't schedule a course whose effect is a prerequisite of a course scheduled before it
        # Higher level requirements don't count
        if not is_higher_level_operator(next_operator) and not is_higher_level_operator(operator):
            if operator.scheduledterm <= next_operator.scheduledterm and next_operator.effect in operator.pre:
                print("Scheduling after course using it", next_operator)
                return False
            if operator.scheduledterm >= next_operator.scheduledterm and operator.effect in next_operator.pre:
                print("Scheduling before prereq", next_operator)
                return False

    # Will adding this course exceed the hours limit?
    if hours_in_term > 18:  # Too many hours in term
        print("Too many hours", next_operator)
        return False

    # The operator has passed
    return True


def heuristic_distance(course_descriptions: Dict[Course, CourseInfo], dnf_clause: List[Course], initial_state:List[CourseUsable], goal_conditions: List[CourseHLCheck], current_plan: List[CourseOperator] ):  # maximin
    h = 0
    for req in dnf_clause:
        req = Course(*req)
        for course in list(map(lambda i: i.course, initial_state)) + list(map(lambda i: i.effect, current_plan)) + list(map(lambda i: i.course, goal_conditions)):
            course = Course(*course)
            if req.program == course.program or req == course or req in course_descriptions[course].prereqs or course in course_descriptions[req].prereqs:
                h -= 1
    return h


def minimum_requirement_tree_height(course_descriptions: Dict[Course, CourseInfo], dnf_clause: List[Course]):  # maximin
    if len(dnf_clause) == 0:
        return 0

    maximum = 0
    for req in dnf_clause:  # dnf_clause was selected, find the tree length required for it to be fulfilled, (max)
        lmin = 9
        if len(course_descriptions[req].prereqs) == 0:
            lmin = 0
        for clause in course_descriptions[req].prereqs:  # find the length of the smallest clause for req
            clause = list(clause)
            sz = (1 if not is_higher_level_course(course_descriptions, req) else 0) + minimum_requirement_tree_height(course_descriptions, clause)
            if sz < lmin:
                lmin = sz
        if lmin > maximum:
            maximum = lmin
    return maximum


def push_higher_levels(course_descriptions: Dict[Course, CourseInfo], plan : List[CourseOperator]):
    for i, hl_op in enumerate(plan):
        if not is_higher_level_operator(hl_op):
            continue
        keep_pushing = True
        while keep_pushing and hl_op.scheduledterm != ScheduledTerm.Spring_Senior:
            for clause in course_descriptions[hl_op.effect].prereqs:
                if not any(req in (map(lambda op: op.effect, filter(lambda op: op.scheduledterm == hl_op.scheduledterm, plan))) for req in clause):
                    keep_pushing = False
                    break
            if keep_pushing:
                hl_op = hl_op._replace(scheduledterm=ScheduledTerm(int(hl_op.scheduledterm) + 1))
                plan[i] = hl_op
        keep_pushing = True
        while keep_pushing and hl_op.scheduledterm != ScheduledTerm.Fall_Frosh:
            for clause in course_descriptions[hl_op.effect].prereqs:
                if any(req in (map(lambda op: op.effect, filter(lambda op: op.scheduledterm == hl_op.scheduledterm, plan))) for req in clause):
                    keep_pushing = False
                    break
            if keep_pushing:
                hl_op = hl_op._replace(scheduledterm=ScheduledTerm(int(hl_op.scheduledterm) - 1))
                plan[i] = hl_op


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
INITIAL_STATE = [Course('CS', '1101'), Course('JAPN', '1101')]
GOAL_CONDITIONS = [Course('CS', 'major')]
print(course_scheduler(COURSE_DICT, GOAL_CONDITIONS, INITIAL_STATE))
