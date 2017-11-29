import re
from collections import namedtuple

import course_dictionary as cd
import sameerpuri_scheduler as sps
from typing import Dict, List

p = re.compile(r'([A-Z-]{2,5}[ ]\d{4}[W]{0,1})[.] ([A-Za-z\s]+?[.]) [\[(](Formerly[\s\S]+?)[\])][.]{0,1}([\S\s]*?[.]*) ([\[][\s\S]+?[\]])')
CourseDesc = namedtuple('CourseDesc', ['name', 'formerly', 'summary', 'creditbracket'])


def create_course_desc_dict(course_dict: Dict[sps.Course, sps.CourseInfo]) -> Dict[sps.Course, CourseDesc]:
    data: str

    with open('ugad.txt', 'r') as ugad:
        data = ugad.read().replace('\n', ' ')

    course_desc_dict: Dict[sps.Course, CourseDesc] = {}
    for match in p.findall(data):
        course: sps.Course = sps.Course(*match[0].split(' '))
        if course in course_dict:
            course_desc_dict[course] = CourseDesc(*match[1:5])
    return course_desc_dict


if __name__ == '__main__':
    print(create_course_desc_dict(cd.create_course_dict()))