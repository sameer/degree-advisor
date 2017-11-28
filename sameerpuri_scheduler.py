#!/bin/python
# Sameer Puri
# I received help from Guimin in seeing ways that I might implement a heuristic.

# The scheduler I wrote in python 3.6.2 uses a heuristic depth first search to try to find a valid schedule. It reasons
# in terms of taken courses as "operators" that are placed in a plan. The courses in the initial state are placed in the
# plan as though they were courses taken in the summer before freshman year. On each recursive call, the scheduler tries
# to achieve the first goal in goal_conditions (goal_conditions[0]). It iterates through each combo of term and
# prerequisite clause possible, ignoring terms that don't make sense. Once it finds a valid combination, it adds it to
# the current plan and does a further recursive call, replacing goal_conditions[0] with its current clause.
# Somewhere down the line, if a goal cannot be scheduled in any term, the course we initially tried has failed and the
# recursion stack unwinds one by one, trying the next combo of term and prerequisite clause for the current goal until
# and doing a recursive call again.

# A heuristic of the "minimum requirement tree height" is used. This is the minimum number of semesters a course needs
# for it and its prerequisites to be scheduled, given the initial state. This is used to limit the terms that are
# evaluated in term and prereq clause combinations. A variation on the heuristic is also employed where the instead of
# the initial state, the current plan is used. This is used to sort the prereqs of a goal so that those clauses that are
# heuristically "closest" are tried first. It is also used to sort the requirements inside of a clause so that the
# hardest ones are placed first.

# I used the tests from Brian Gauch's autograder to evaluate my scheduler. Test cases 1 through 4 succeeded, but I
# encountered some technical difficulties with how the grader evaluated by solution output. In some cases, it could
# not read my solution properly so it thought that the number of courses in a semester was incorrect. For instance,
# with test case 4, it seems to get confused in parsing my solution and thinks there are only 3 or 4 courses in my
# solution when the file itself clearly shows otherwise. I couldn't get test cases 5 and 6 to function properly; they
# continue to make my code time out in trying to find a solution. I have tried my hardest to figure out why it recurses
# infinitely, but I cannot find any good explanation other than there are too many open electives that it has to handle
# so it takes ages. I am certain there isn't a solution for test case 5, so it should return the empty set, and that
# there is a solution for test case 6.

# Thank you for reading, sorry if that was a bit lengthy. :)

from collections import namedtuple
from enum import IntEnum
from typing import Dict, List
import course_dictionary as cd


# Some classes useful to the scheduler
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

    def __ge__(self, other):  # Define ge
        return self.termNo >= other.termNo

    def __repr__(self):
        # return "<Term semester:%s year:%s>" % (self.semester, self.year)
        return "(%s, %s)" % (self.semester, self.year)

    def __str__(self):
        # return "From str method of Term: semester is %s, year is %s" %
        # (self.semester, self.year)
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
        # return "<ScheduledCourse course:%s term:%s>" % (self.course,
        # self.term)
        return "(%s, %s, %s)" % (self.course, self.term, self.clause)

    def __str__(self):
        return "course is %s, term is %s, pre is %s" % (self.course, self.term, self.clause)


def course_scheduler(course_descriptions: Dict[Course, CourseInfo], goal_conditions: List[Course], initial_state: List[Course]):
    # Run the internal scheduler, considering the initial state as part of an
    # already scheduled plan
    result_plan = internal_scheduler(course_descriptions, goal_conditions, list(
        map(lambda course: ScheduledCourse(course, course_descriptions[course], Term(Semester.Summer, Year.Frosh), []), initial_state)), {})
    # Filter out the initial state that was passed to the scheduler
    result_plan = list(filter(lambda sc: sc.term != Term(Semester.Summer, Year.Frosh), result_plan))
    # Push higher level requirements down to the semester in which they are
    # fulfilled
    push_higher_levels(result_plan)
    # Pads semesters below 12 hours to 12 hours.
    result_plan = pad_to_12_hours(course_descriptions, result_plan)
    # Restructure the plan to match the specification
    print_schedule(result_plan)
    course_dict = {operator.course: CourseInfo(operator.courseInfo.credits, (
        operator.term.semester.name, operator.term.year.name), operator.courseInfo.prereqs) for operator in result_plan}
    # Done!
    return course_dict


def internal_scheduler(course_descriptions: Dict[Course, CourseInfo], goal_conditions: List[Course], current_plan: List[ScheduledCourse], memo_table_for_tree_height: Dict[Course, int], depth = 0):
    if len(goal_conditions) == 0:  # There's nothing left to do!
        if is_valid_plan(current_plan):  # If it's valid, return the plan, else return a failure
            return current_plan
        else:
            print("Invalid complete plan")
            return ()
    # Get the initial state from the current plan
    initial_state = list(map(lambda sc: sc.course, list(filter(lambda sc: sc.term == Term(Semester.Summer, Year.Frosh), current_plan))))

    # Remove duplicates in the goal conditions
    goal_conditions = make_unique(goal_conditions)

    # TODO: what 2 do
    goal_conditions = list(sorted(goal_conditions, key=lambda g: minimum_tree_hours(course_descriptions, g, initial_state[:], {})))
    goal = goal_conditions[0]  # Consider the first goal as the current goal
    goal_info = course_descriptions[goal]  # Get its info

    # Calculate the current hours per semester
    hours_per_term = get_hour_counts(current_plan)

    # Return a failure if there aren't enough hours available to schedule current goals. Assume 70%, a reasonable estimate.
    number_hours_remaining = 0
    number_hours_current_state = initial_state[:]
    number_hours_dict = {}
    for g in goal_conditions:
        number_hours_remaining += minimum_tree_hours(course_descriptions, g, number_hours_current_state, number_hours_dict)
    if 8 * 18 - sum(hours_per_term.values()) < number_hours_remaining * 0.7:
        print("FAIL", number_hours_remaining)
        return ()
    del number_hours_remaining, number_hours_current_state, number_hours_dict

    # Find the min height of the requirement tree for the current goal. It
    # can't be placed in a semester before this.
    goal_min_height = minimum_tree_height(course_descriptions, goal, initial_state[:], {})

    # Boost the min height based on filled semesters
    for i, (term, hours) in enumerate(hours_per_term.items(), 1):
        if i < goal_min_height:
            continue
        if i > goal_min_height:
            break
        if hours+int(goal_info.credits) > 18:
            goal_min_height += 1

    if goal in map(lambda op: op.course, current_plan):  # Course already taken
        goal_conditions.remove(goal)
        return internal_scheduler(course_descriptions, goal_conditions, current_plan, memo_table_for_tree_height)

    # Sort the potential clauses so the easiest ones to fulfill are tried first. If there are no clauses, provide
    # an empty clause to the for loop.
    sorted_dnf_clauses = []
    if len(goal_info.prereqs) != 0:
        dnf_clauses_to_hours = {}
        for dnf_clause in goal_info.prereqs:
            hours = 0
            for dnf_clause_req in dnf_clause:
                hours += minimum_tree_hours(course_descriptions, dnf_clause_req, initial_state[:], {})
            dnf_clauses_to_hours[dnf_clause] = hours
        dnf_clauses_min_hours = min(dnf_clauses_to_hours.values())
        print("MINHRS", dnf_clauses_min_hours, "for", goal)
        # sorted_dnf_clauses = sorted(goal_info.prereqs, key=lambda dnf_clause: dnf_clauses_to_hours[dnf_clause])
        sorted_dnf_clauses = list(filter(lambda dnf_clause: dnf_clauses_to_hours[dnf_clause] == dnf_clauses_min_hours, goal_info.prereqs))
    else:
        sorted_dnf_clauses.append([])

    print("For", goal, "looking at clauses", sorted_dnf_clauses)

    # Check each possible term (excluding Summers) for non-higher-level requirements starting from the min_height until
    # Spring of senior year. For higher level requirements, this doesn't matter because they can be scheduled any time
    # and corrected after evaluation is complete, so we only try Spring Senior
    # Year.
    terms_iter = iter(map(lambda i: height_to_term(i), range(goal_min_height, 9)) if not is_higher_level_course_info(goal_info) else [Term(Semester.Spring, Year.Senior)])
    for term in terms_iter:
        if int(goal_info.credits) + hours_per_term[term] > 18:  # Too many hours
            continue
        if term.semester.name not in goal_info.terms:  # Not offered in this term
            continue
        if not is_higher_level_course_info(goal_info):  # Don't schedule in same sem or after course that uses the goal
            violates_another = False
            for op in current_plan:
                if is_higher_level_course_info(op.courseInfo) or op.term.semester == Semester.Summer:
                    continue
                if term >= op.term and goal in op.clause:
                    print("SCHEDULING", goal, "in", term, "After", op.course, "in", op.term)
                    print_schedule(current_plan)
                    violates_another = True
                    break
            if violates_another:
                break  # Gone too far
        # Now we know scheduling the course is definitely possible...
        next_operation = ScheduledCourse(
            goal, goal_info, term, [])  # Construct an operator for the goal
        # Create a copy of the current plan with the next operation in it
        next_plan = current_plan[:]
        next_plan.append(next_operation)
        for i, goal_dnf_clause in enumerate(sorted_dnf_clauses):
            if not is_higher_level_course_info(goal_info):  # Don't schedule in same sem or before a prerequisite course
                violates_another = False
                for op in current_plan:
                    if is_higher_level_course_info(op.courseInfo) or op.term.semester == Semester.Summer:
                        continue
                    if op.term >= term and op.course in goal_dnf_clause:
                        print("SCHEDULING", goal, "in", term, "Before", op.course, "in", op.term)
                        print_schedule(current_plan)
                        violates_another = True
                        break
                if violates_another:
                    continue
            # if i > 4:  # Too many tries. This prevents open electives from timing out. Will fix for the next submission.
            #     print("Too many tries")
            #     break

            next_operation.clause = goal_dnf_clause  # Assign current dnf clause to the operator
            goal_dnf_clause = list(goal_dnf_clause)
                              # We need the properties of a list later on
            # Build the next set of goal conditions, which is the goal conditions minus the goal plus the requirements
            # of the goal's current dnf clause.
            next_goal_conditions = goal_conditions[:]
            next_goal_conditions.remove(goal)
            # Put the dnf clause at the front, sorted by what's hardest first. Hard clause members define what the
            # course layout should be, while easy ones can be fit in in the
            # aftermath.
            next_goal_conditions = list(sorted(remove_fulfilled(goal_dnf_clause, current_plan), key=lambda x: -minimum_tree_hours(
                course_descriptions, x, initial_state[:], {}))) + next_goal_conditions
            print("Try", goal, "in", term)
            result_plan = internal_scheduler(
                course_descriptions, next_goal_conditions, next_plan, memo_table_for_tree_height, depth+1)  # Recurse deeper
            if not len(result_plan) == 0:  # Setting this goal as the operation didn't fail, return it
                return result_plan
            # Failing here means the next clause will be tried
            # TODO: check for dnf clauses that are effectively equivalent and skip them, especially for open electives
    print("Semesters exhausted for", goal)
    return ()


def pad_to_12_hours(course_descriptions: Dict[Course, CourseInfo], plan: List[ScheduledCourse]):
    courses_in_plan = list(map(lambda sc: sc.course, plan))
    for term, hours in get_hour_counts(plan).items():
        if 12 > hours > 0:
            for course, courseinfo in course_descriptions.items():
                if hours >= 12:
                    break
                if len(courseinfo.prereqs) > 0 or course in courses_in_plan or int(courseinfo.credits) + hours > 18:
                    continue
                plan.append(
                    ScheduledCourse((course.program, course.designation), courseinfo, term, courseinfo.prereqs))
                courses_in_plan.append(course)
                hours += int(courseinfo.credits)
    return plan


# This method pushes higher level courses from the semester they're in to
# the semester in which they're fulfilled
def push_higher_levels(plan: List[ScheduledCourse]):
    for i, hl_op in enumerate(plan):
        if not is_higher_level_course_info(hl_op.courseInfo):  # Ignore non-higher-level courses
            continue
        keep_pushing = True
        while keep_pushing and hl_op.term != Term(Semester.Spring, Year.Senior):  # Push upward
            for clause in hl_op.courseInfo.prereqs:
                if not any(req in (map(lambda op: op.course, filter(lambda op: op.term == hl_op.term, plan))) for req in clause):
                    keep_pushing = False
                    break
            if keep_pushing:
                hl_op.term = Term.initFromTermNo(
                    hl_op.term.termNo + (1 if hl_op.term.semester == Semester.Fall else 2))
        keep_pushing = True
        while keep_pushing and hl_op.term != Term(Semester.Fall, Year.Frosh):  # Push downward
            for clause in hl_op.courseInfo.prereqs:
                if any(req in (map(lambda op: op.course, filter(lambda op: op.term == hl_op.term, plan))) for req in clause):
                    keep_pushing = False
                    break
            if keep_pushing:
                hl_op.term = Term.initFromTermNo(
                    hl_op.term.termNo - (1 if hl_op.term.semester == Semester.Spring else 2))


# This method removes already fulfilled courses from a dnf clause to
# simplify it
def remove_fulfilled(dnf_clause: List[Course], plan: List[ScheduledCourse]):
    for op in plan:
        if op.course in dnf_clause:
            dnf_clause.remove(op.course)
    return dnf_clause


# Checks if the plan is under 18 hours. If not, there is a failure.
def is_valid_plan(current_plan: List[ScheduledCourse]):
    for term, hours in get_hour_counts(current_plan).items():
        if hours > 18:
            return False
    return True


# This method creates a dict mapping a term (excluding summer) to the # of
# hours in it.
def get_hour_counts(current_plan: List[ScheduledCourse]):
    hour_counts = {height_to_term(i): 0 for i in range(1, 9)}
    for operator in current_plan:
        if operator.term.semester is Semester.Summer:  # The scheduler doesn't handle summer yet
            continue
        hour_counts[operator.term] += int(operator.courseInfo.credits)
    return hour_counts


# TODO: make a double level sort -- first sort by the depth, then sort by the number of hours required
# TODO: prune clauses that are effectively equivalent i.e. for open electives, etc.
# TODO: don't sort all goals because that destroys discovering the wrongness of something early on and not knowing where it came from because we can know where it came from by calling a parent method
# TODO: add a memotable for the internal_scheduler so that if the same state is encountered (can this be checke) it returns immediately)
# This method answers the question: how many semesters are needed to schedule myself and my prerequirements, given the
# "initial_state"? The memotable is used to speed up lookup.
def minimum_tree_height(course_descriptions: Dict[Course, CourseInfo], goal: Course, initial_state: List[Course], memo: Dict[Course, int]):
    if goal in initial_state:  # Already fulfilled, so no depth
        return 0
    initial_state.append(goal)
    if len(course_descriptions[goal].prereqs) == 0:  # Basic no req course, so only taking it requires a semester
        return 1
    if goal in memo:  # This has already been answered
        return memo[goal]
    # Calculate the minimax
    goal_minimum = 20
    goal_initial_state = initial_state
    for prereq_clause in course_descriptions[goal].prereqs:  # Find the clause that is easiest to fulfill
        this_initial_state = initial_state[:]
        clause_maximum = 0
        for req in prereq_clause:  # Identify the hardest part of the current clause, it is definitive of it
            # Don't consider higher level goals to be a course.
            # Recurse to check the height required to fulfill req.
            subtree_height = (1 if not is_higher_level_course(course_descriptions, goal) else 0) + \
                minimum_tree_height(
                course_descriptions, req, this_initial_state, memo)
            if subtree_height > clause_maximum:  # Local maximum
                clause_maximum = subtree_height
        if clause_maximum < goal_minimum:  # Global minimum
            goal_minimum = clause_maximum
            goal_initial_state = this_initial_state
    initial_state.clear()
    initial_state += goal_initial_state
    memo[goal] = goal_minimum  # Memoize
    return goal_minimum  # Done!


def minimum_tree_hours(course_descriptions: Dict[Course, CourseInfo], goal: Course, initial_state: List[Course], memo: Dict[Course, int]):
    if goal in initial_state:  # Already fulfilled, so no hours
        return 0
    initial_state.append(goal)
    if len(course_descriptions[goal].prereqs) == 0:  # Basic no req course, so only taking it requires a semester
        return int(course_descriptions[goal].credits)
    if goal in memo:  # This has already been answered
        return memo[goal]
    # Calculate the minisum
    goal_minimum = 1000
    goal_initial_state = initial_state
    for prereq_clause in course_descriptions[goal].prereqs:  # Find the clause that is easiest to fulfill
        this_initial_state = initial_state[:]
        clause_total = int(course_descriptions[goal].credits)
        for req in prereq_clause:  # Sum up the hours required for each req
            # Don't consider higher level goals to be a course.
            # Recurse to check the height required to fulfill req.
            subtree_hours = minimum_tree_hours(course_descriptions, req, this_initial_state, memo)
            clause_total += subtree_hours
        if clause_total < goal_minimum:  # Global minimum
            goal_minimum = clause_total
            goal_initial_state = this_initial_state
    initial_state.clear()
    initial_state += goal_initial_state

    memo[goal] = goal_minimum  # Memoize
    return goal_minimum # Done!s


# Converts a term number, 1 to 8, to the applicable term. This is handling for the fact that the scheduler doesn't
# consider summer terms.
def height_to_term(height: int):
    semester = Semester(((height + 1) % 2) + 1)  # Spring or Fall?
    year = Year(int((height - 1) / 2))
    return Term(semester, year)


# This method makes the argument unique and returns it
def make_unique(seq: list):
    return list(set(seq))
    # seen = set()
    # seen_add = seen.add
    # return [x for x in seq if not (x in seen or seen_add(x))]


# This method checks if a course is higher level by credits.
def is_higher_level_course(course_descriptions: Dict[Course, CourseInfo], course: Course):
        return int(course_descriptions[course].credits) == 0


# This method checks if a course is higher level using the credits in its info.
def is_higher_level_course_info(courseinfo: CourseInfo):
    return int(courseinfo.credits) == 0


# Convenience method for debugging purposes
def print_schedule(plan: List[ScheduledCourse]):
    schedule = {height_to_term(i): [] for i in range(1, 9)}
    for operator in plan:
        if operator.term.semester == Semester.Summer:
            continue
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


course_scheduler(cd.create_course_dict(), goal_conditions=[Course(program='CS', designation='major'), Course(program='ANTH', designation='4345'), Course(program='ARTS', designation='3600'), Course(program='ASTR', designation='3600'), Course(program='BME', designation='4500'), Course(program='BUS', designation='2300'), Course(program='CE', designation='3705'), Course(program='LAT', designation='3140'), Course(program='JAPN', designation='3891')], initial_state=[Course('CS', '1101')])
# course_dict = cd.create_course_dict()

# course_scheduler(course_dict, goal_conditions=[Course(program='CS', designation='major'), Course('JAPN', '3891')], initial_state=[Course('CS', '1101')])