import time
from argparse import ArgumentParser
from operator import itemgetter
from typing import Any, Dict, List, Tuple

import numpy as np
import pandas as pd
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.common.by import By
from tqdm import tqdm


class KTHCourseScraper(webdriver.Firefox):
    def __init__(self):
        webdriver.Firefox.__init__(self)

    def __call__(self, debug: bool = False) -> None:
        courses = self._get_courses(debug)
        course_codes_and_urls = tuple(map(itemgetter('Kurskod', 'URL'), courses))
        course_contents, course_offerings = self._get_course_content_and_offerings(course_codes_and_urls)

        for course in courses:
            course.update(course_contents.get(course['Kurskod'], {}))

        df_courses = self._post_process_courses(pd.DataFrame(courses))
        df_offerings = self._post_process_course_offerings(pd.DataFrame(course_offerings))

        file_prefix = 'debug_' if debug else ''
        df_courses.to_csv(file_prefix + 'kth_courses.csv', index=False)
        df_offerings.to_csv(file_prefix + 'kth_offerings.csv', index=False)

    def _get_courses(self, debug: bool = False) -> List[Dict[str, Any]]:
        courses = []

        departments = ['A', 'C', 'E', 'H', 'J', 'K', 'M', 'S', 'U']
        column_names = self._get_table_column_names()

        for nth, department in enumerate(departments):
            print(f'{nth+1} of {len(departments)}')

            # get resutls for department
            self.get(f'https://www.kth.se/student/kurser/sokkurs?department={department}')
            time.sleep(1)

            # get table and extract rows
            table = self.find_element(By.CSS_SELECTOR, '.table > tbody:nth-child(2)')
            for row in tqdm(table.find_elements(By.CSS_SELECTOR, 'tr')):
                row_content = []

                for i, col in enumerate(row.find_elements(By.CSS_SELECTOR, 'td')):

                    if i == 0:
                        # get url to english version of course page
                        content = col.find_element(By.CSS_SELECTOR, 'a')
                        row_content.append(content.get_attribute('href') + '?l=en')
                    else:
                        content = col

                    # extract text from cell
                    row_content.append(content.text)

                # add course dict to list of courses
                courses.append(dict(zip(column_names, row_content)))

                if debug and len(courses) >= 5:
                    return courses

        return courses

    def _get_course_content_and_offerings(
        self, course_codes_and_urls: Tuple[Tuple[str, str]]
    ) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
        course_offerings = []

        course_contents = {}

        for code, url_ in tqdm(course_codes_and_urls):
            is_running = False

            while not is_running:
                try:
                    self.get(url_)
                    time.sleep(0.5)

                    content = self._get_course_content()
                    content['Course name (eng.)'] = self._get_english_course_name(code)

                    paragraph = (
                        self.find_element(By.ID, 'courseIntroText').find_element(By.CLASS_NAME, 'paragraphs').text
                    )
                    if paragraph:
                        content['paragraph'] = paragraph

                    course_contents[code] = content

                    course_offerings += self._get_course_offerings(code)

                    is_running = True

                except TimeoutException as ex:
                    print('Exception has been thrown. ' + str(ex))
                    time.sleep(5)

        return course_contents, course_offerings

    def _get_table_column_names(self) -> List[str]:

        # get course search page (limit results on something (e.g. education level) required by the website)
        self.get('https://www.kth.se/student/kurser/sokkurs?eduLevel=0')

        self._accept_terms_if_needed()

        # extract column names from table header
        header = self.find_element(By.CSS_SELECTOR, '.table > thead:nth-child(1) > tr:nth-child(1)')
        column_names = ['URL'] + [col.text for col in header.find_elements(By.CSS_SELECTOR, 'th')]

        return column_names

    def _accept_terms_if_needed(self) -> None:
        try:
            self.find_element(By.CSS_SELECTOR, 'button.cm-btn:nth-child(2)').click()
        except NoSuchElementException:
            pass

    def _get_course_content(self) -> Dict[str, Any]:
        course_contents = {}
        for content in self.find_element(By.ID, 'courseContentBlock').find_elements(By.CSS_SELECTOR, 'span'):
            try:
                header = content.find_element(By.CSS_SELECTOR, 'h3').text
                body = content.find_element(By.CSS_SELECTOR, 'div').text.strip()
                if body not in ('Ingen information tillagd', 'No information inserted'):
                    if header == 'Examinator':
                        examinators = content.find_elements(By.CSS_SELECTOR, 'div')
                        examinators = [ex.find_element(By.CSS_SELECTOR, 'a') for ex in examinators]
                        body = {ex.text: ex.get_attribute('href') for ex in examinators}
                    course_contents[header] = body
            except Exception:
                continue
        return course_contents

    def _get_english_course_name(self, course_code: str) -> str:
        name = self.find_element(By.ID, 'page-heading').text
        name = name.replace(course_code, '').strip()
        idx = np.where([c.isnumeric() for c in name])[0]
        if len(idx) > 0:
            idx = idx[0]
            name = name[:idx]
        return name

    def _get_course_offerings(self, course_code: str) -> List[Dict[str, Any]]:
        course_offerings = []
        try:
            semesters = self.find_element(By.ID, 'semesterDropdown').find_elements(By.CSS_SELECTOR, 'option')[1:]

            for semester in semesters:
                semester.click()
                time.sleep(0.5)

                offering = self._get_course_info()
                offering.update(self._get_course_contacts())
                offering['Course code'] = course_code
                offering['Semester'] = semester.text

                course_offerings.append(offering)
        except Exception:
            return []
        return course_offerings

    def _get_course_contacts(self) -> Dict[str, Any]:
        contacts = {}
        contact_fields = self.find_element(By.ID, 'roundContact')

        for contact_field in contact_fields.find_elements(By.CSS_SELECTOR, 'h3')[1:]:
            contact_type = contact_field.text
            if contact_type == 'Contact':
                continue
            for contact in contact_field.find_elements(By.XPATH, 'following-sibling::*'):
                if contact.get_attribute('class') == 't4':
                    break
                if contact.text != 'No information inserted':
                    persons = contact.find_elements(By.CLASS_NAME, 'person')
                    persons = [p.find_element(By.CSS_SELECTOR, 'a') for p in persons]
                    contacts[contact_type] = {p.text: p.get_attribute('href') for p in persons}
        return contacts

    def _get_course_info(self) -> Dict[str, Any]:
        offering_info = self.find_element(By.CSS_SELECTOR, '#roundKeyInformation > div:nth-child(1)')
        course_info: Dict[str, Any] = {}
        for child in offering_info.find_elements(By.CSS_SELECTOR, 'h3'):
            header = child.text
            bodies = []
            for body in child.find_elements(By.XPATH, 'following-sibling::*'):
                if body.get_attribute('class') == 'row':
                    return course_info
                if body.get_attribute('class') == 't4':
                    break
                if '\n' in body.text:
                    bodies += body.text.split('\n')
                elif body.text != 'No information inserted':
                    bodies.append(body.text)
            if len(bodies) == 1:
                bodies = bodies[0]
            if bodies:
                course_info[header] = bodies
        return course_info

    @staticmethod
    def _post_process_courses(df: pd.DataFrame) -> pd.DataFrame:
        df_ = df.rename(
            columns={
                'Kurskod': 'Course code',
                'Kursnamn': 'Course name',
                'Omfattning': 'hp',
                'Utbildningsnivå': 'Level',
            }
        ).drop(columns=['Ethical approach'])
        df_.hp = df_.hp.str.replace('fup', '').str.replace('hp', '').astype(float)
        df_['School'] = [x[: np.where([c.isnumeric() for c in x])[0][0]] for x in df_['Course code']]
        df_['Course web'] = 'https://www.kth.se/social/course/' + df_['Course code']

        # remove examensarbeten
        df_ = df_[~df_['Course name'].str.lower().str.contains('examensarbete')]

        return df_

    @staticmethod
    def _post_process_course_offerings(df: pd.DataFrame) -> pd.DataFrame:

        df_ = df.rename(columns={'For course offering': 'Year'})
        df_[['Starting Term', 'Year']] = df_.Year.str.extract(r'(Autumn|Spring)\s(\d{4})\s')

        # get academic year and term
        year_term = df_.loc[pd.notna(df_['Year']), ['Year', 'Starting Term']].astype({'Year': int})
        year_term.loc[year_term['Starting Term'] == 'Spring', 'Year'] -= 1
        df_.loc[pd.notna(df_['Year']), 'Year'] = year_term.Year.astype(str) + '/' + (year_term.Year + 1).astype(str)

        # concatenate course periods where needed
        df_.loc[df_.Periods.apply(lambda x: isinstance(x, list)), 'Periods'] = df_.loc[
            df_.Periods.apply(lambda x: isinstance(x, list)), 'Periods'
        ].str.join(', ')

        # process for next step
        signs_to_remove = ["'", ' hp', ' fup', 'Autumn', 'Spring', ':']
        for sign in signs_to_remove:
            df_.Periods = df_.Periods.str.replace(sign, '', regex=False)

        # get credicts per academic period
        for period in ['P1', 'P2', 'P3', 'P4']:
            df_[period] = df_.Periods.str.extract(fr'(?<=(?:{period}\s\())(.+?)(?=\))').astype(float)

        df_ = df_.drop(columns='Periods')
        return df_


def main():
    parser = ArgumentParser()
    parser.add_argument('-d', '--debug', type=bool, default=False, help='Debug mode')
    args = parser.parse_args()

    KTHCourseScraper()(debug=args.debug)


if __name__ == '__main__':
    main()
