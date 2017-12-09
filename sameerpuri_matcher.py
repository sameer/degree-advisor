#!/usr/bin/env python
# -*- coding: utf-8 -*-

from pprint import pprint

import re
from collections import namedtuple

import course_dictionary as cd
from typing import Dict, List

p = re.compile(r'([A-Z-]{2,5}[ ]\d{4}[WL]{0,1})[.] ([\w:\-,’\'\s]+?[.])[ ]{0,1}(?:[\[(](Formerly[\s\S]+?)[\])][.]{0,1}){0,1}([\S\s]*?[.]*) ([\[][\s\S]+?[\]])')

fixcontinuednewlines = re.compile(r'([A-Za-z0-9])[\n]([a-z0-9])')
CourseDesc = namedtuple('CourseDesc', ['name', 'formerly', 'summary', 'creditbracket'])


def create_course_desc_dict(course_dict: Dict[cd.Course, cd.CourseInfo]) -> Dict[cd.Course, CourseDesc]:
    data: str

    with open('ugad.txt', 'r') as ugad:
        # TODO: consider case where newline is a continuation of character from previous line
        data = ugad.read()
        for match in fixcontinuednewlines.findall(data):
            data = data.replace(match[0]+'\n'+match[1], match[0] + match[1])
        data = data.replace('\n', ' ')

    course_desc_dict: Dict[cd.Course, CourseDesc] = {}
    for match in p.findall(data):
        course: cd.Course = cd.Course(*match[0].split(' '))
        if course in course_dict:
            course_desc_dict[course] = CourseDesc(*match[1:5])
    return course_desc_dict


if __name__ == '__main__':
    print('*** Course Matcher ***')
    course_desc_dict: Dict[cd.Course, CourseDesc] = create_course_desc_dict(cd.create_course_dict())
    while True:
        try:

            got: List[str] = input('Input course you would like to get the description for: ').split(' ')
            desc: CourseDesc = course_desc_dict[cd.Course(got[0], got[1])]
            print(desc.name, desc.formerly, desc.creditbracket)
            print(desc.summary)

        except Exception as e:
            print('Failed:', e)
