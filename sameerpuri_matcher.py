from pprint import pprint

import re
from collections import namedtuple

import course_dictionary as cd
from typing import Dict, List

p = re.compile(r'([A-Z-]{2,5}[ ]\d{4}[WL]{0,1})[.] ([\w:\-,’\'\s]+?[.])[ ]{0,1}(?:[\[(](Formerly[\s\S]+?)[\])][.]{0,1}){0,1}([\S\s]*?[.]*) ([\[][\s\S]+?[\]])')

CourseDesc = namedtuple('CourseDesc', ['name', 'formerly', 'summary', 'creditbracket'])


def create_course_desc_dict(course_dict: Dict[cd.Course, cd.CourseInfo]) -> Dict[cd.Course, CourseDesc]:
    data: str

    with open('ugad.txt', 'r') as ugad:
        data = ugad.read().replace('\n', ' ')

    course_desc_dict: Dict[cd.Course, CourseDesc] = {}
    for match in p.findall(data):
        course: cd.Course = cd.Course(*match[0].split(' '))
        if course in course_dict:
            course_desc_dict[course] = CourseDesc(*match[1:5])
    return course_desc_dict


if __name__ == '__main__':
    pprint(create_course_desc_dict(cd.create_course_dict()))