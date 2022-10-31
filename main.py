from operator import itemgetter

import pandas as pd

from post_processing import post_process_course_offerings, post_process_courses
from scraper import KTHCourseScraper

DEBUG = False

with KTHCourseScraper() as driver:
    courses = driver.get_courses(debug=DEBUG)
    course_codes_and_urls = tuple(map(itemgetter('Kurskod', 'URL'), courses))
    course_contents, course_offerings = driver.get_course_content_and_offerings(course_codes_and_urls)

for course in courses:
    course.update(course_contents.get(course['Kurskod'], {}))

df_courses = post_process_courses(pd.DataFrame(courses))
df_offerings = post_process_course_offerings(pd.DataFrame(course_offerings))

df_courses.to_csv('kth_courses.csv', index=False)
df_offerings.to_csv('kth_offerings.csv', index=False)
