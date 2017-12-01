from pprint import pprint
from typing import List, Dict
import spacy
import numpy as np

import course_dictionary as cd
import sameerpuri_matcher as spm

course_infos: Dict[cd.Course, cd.CourseInfo] = cd.create_course_dict()
course_descs: Dict[cd.Course, spm.CourseDesc] = spm.create_course_desc_dict(course_infos)

print('Loading...')
print('Reading english word vector information...')
nlp = spacy.load('en_core_web_lg')
print('Analyzing course descriptions...')
course_nlp_descs = {}
course_nlp_names = {}
for course in course_descs.keys():
    course_nlp_descs[course] = nlp(course_descs[course].summary)
    course_nlp_names[course] = nlp(course_descs[course].name)
print('Loaded!')


def recommend_courses_using_search_text(search_text: str, num: int) -> List:
    search_text = nlp(search_text)
    text_similarities_dict: Dict[float, cd.Course] = {search_text.similarity(course_nlp_descs[course]): course for course in course_nlp_descs.keys()}
    text_similarities: List[float] = list(reversed(sorted(text_similarities_dict.keys())))
    num = min(num, len(text_similarities))
    return list(map(lambda flt: text_similarities_dict[flt], text_similarities[:num]))


def recommend_courses_using_liked_courses(courses_liked: List[cd.Course], num: int) -> List:
    course_similarity_dict: Dict[cd.Course, float] = {}
    for crs in course_descs.keys():
        if crs not in courses_liked:
            desc_similarities: List[float] = [course_nlp_descs[crs].similarity(course_nlp_descs[course_liked]) for course_liked in courses_liked]
            name_similarities: List[float] = [course_nlp_names[crs].similarity(course_nlp_names[course_liked]) for course_liked in courses_liked]
            course_similarity_dict[crs] = ((sum(name_similarities) / len(name_similarities)) + 2*(sum(desc_similarities) / len(desc_similarities)))/3
    keys = list(course_similarity_dict.keys())
    vals = list(course_similarity_dict.values())
    recommendations_list: List[(cd.Course, float)] = []
    for i in range (0, num if num <= len(course_similarity_dict.keys()) else len(course_similarity_dict.keys())):
        index: int = vals.index(max(vals))
        recommendations_list.append((keys[index], vals[index]))
        vals[index] = 0
    return recommendations_list


if __name__ == '__main__':
    print('*** Course Recommender ***')
    while True:
        try:
            print("1: Search using liked courses\n2: Search using keywords")
            opt: int = int(input("Option: "))
            if opt == 1:
                got: str = input('Input # of desired results followed by semicolon separated courses you liked: ')
                gotargs: List[str] = got.split(';')
                n: int = int(gotargs[0])
                courses: List[cd.Course] = []
                for course_str in gotargs[1:]:
                    course_split: List[str] = course_str.split(' ')
                    courses.append(cd.Course(course_split[0], course_split[1]))
                recommendation_list = recommend_courses_using_liked_courses(courses, n)
                pprint(recommendation_list)
            else:
                got: str = input('Input # of desired results, a semicolon, and search text: ')
                gotargs: List[str] = got.split(';')
                n: int = int(gotargs[0])
                recommendation_list = recommend_courses_using_search_text(gotargs[1], n)
                pprint(recommendation_list)
                pass

        except Exception as e:
            print('Failed:', e)

# 20;CS 2201;EECE 2116;SC 3260;EES 4760;CS 3251;CS 2231;CS 4260;CS 3281;CS 3270;BUS 2100;BUS 2400
z