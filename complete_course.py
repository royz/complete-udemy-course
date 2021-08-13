import time
import re
import os
import requests
import json
import random
from bs4 import BeautifulSoup
import colorama
from termcolor import cprint
import traceback

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DEBUG_MODE = False


def file(filename):
    return os.path.join(BASE_DIR, filename)


class Udemy:
    def __init__(self, course_url, token=None, client_id=None):
        self.url = None
        self.account = None
        self.course_id = None
        self.course_info = None
        self.subdomain = None
        self.token = token
        self.client_id = client_id
        self.headers = None
        self.course = None
        self.completed_materials = []
        self.parse_url(course_url)
        self.set_headers()

    def set_headers(self):
        self.headers = {
            'authority': f'{self.subdomain}.udemy.com',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                          'AppleWebKit/537.36 (KHTML, like Gecko) '
                          'Chrome/87.0.4280.88 Safari/537.36',
            'x-udemy-authorization': f'Bearer {self.token}',
            'accept': 'application/json, text/plain, */*',
            'origin': f'https://{self.subdomain}.udemy.com',
        }

    def get_user_info(self):
        params = {'me': True}

        response = requests.get(f'https://{self.subdomain}.udemy.com/api-2.0/contexts/me/',
                                headers=self.headers, params=params)
        try:
            me = response.json()['me']
            self.account = {
                'name': me['display_name'],
                'email': me['email']
            }
            print(f"logged in as: {self.account['name']} ({self.account['email']})")
        except:
            cprint('token is invalid or expired', 'red')

    def parse_url(self, url):
        url = url.strip()
        matches = re.match(r'(https://)(.*)(\.udemy.com/course/)(.*)(/learn/.*/)(\d+)', url)
        if not matches:
            cprint(f'invalid url: {url}', 'red')
            return
        match_groups = matches.groups()
        self.subdomain = match_groups[1]
        self.url = match_groups[3]

    def get_course_info(self):
        cookies = {
            'client_id': self.client_id,
            'access_token': self.token
        }

        #  use cookie only if subdomain is www
        if self.subdomain == 'www':
            response = requests.get(f'https://{self.subdomain}.udemy.com/course/{self.url}/',
                                    headers=self.headers, cookies=cookies)
        else:
            response = requests.get(f'https://{self.subdomain}.udemy.com/course/{self.url}/',
                                    headers=self.headers)

        soup = BeautifulSoup(response.content, 'html.parser')
        self.course_id = soup.find('body')['data-clp-course-id']

        url = f'https://{self.subdomain}.udemy.com/api-2.0/courses/{self.course_id}/' \
              f'?fields[course]=title,is_approved,visible_instructors,is_paid,is_private' \
              f'&fields[user]=job_title,display_name'
        response = requests.get(url, headers=self.headers)
        self.course_info = response.json()

    def get_course_resources(self):
        params = (
            ('page_size', '1400'),
            ('fields/[lecture/]',
             'title,object_index,is_published,sort_order,created,asset,supplementary_assets,is_free'),
            ('fields/[quiz/]', 'title,object_index,is_published,sort_order,type'),
            ('fields/[practice/]', 'title,object_index,is_published,sort_order'),
            ('fields/[chapter/]', 'title,object_index,is_published,sort_order'),
            ('fields/[asset/]', 'title,filename,asset_type,status,time_estimation,is_external'),
            ('caching_intent', 'True'),
        )

        try:
            response = requests.get(
                f'https://{self.subdomain}.udemy.com/api-2.0/courses/{self.course_id}/subscriber-curriculum-items/',
                headers=self.headers, params=params)

            if DEBUG_MODE:
                with open('course_resources.json', 'w', encoding='utf-8') as f:
                    json.dump(response.json(), f, indent=2)

            results = response.json()['results']
            self.course = []

            if results[0]['_class'] == 'chapter':
                chapter = None
            else:
                chapter = {'chapter': 'Main Chapter', 'lectures': [], 'quizzes': [], 'others': []}

            for result in results:
                if result['_class'] == 'chapter':
                    if chapter:
                        self.course.append(chapter)
                    chapter = {'chapter': result['title'], 'lectures': [], 'quizzes': [], 'others': []}
                elif result['_class'] == 'lecture':
                    chapter['lectures'].append({
                        'id': result['id'],
                        'title': result['title'],
                        'is_published': result['is_published']
                    })
                elif result['_class'] == 'quiz':
                    chapter['quizzes'].append({
                        'id': result['id'],
                        'title': result['title'],
                        'type': result['type'],
                        'is_published': result['is_published']
                    })
                else:
                    chapter['others'].append({
                        'class': result.get('_class'),
                        'id': result['id'],
                        'title': result.get('title'),
                        'is_published': result['is_published']
                    })
            if chapter:
                self.course.append(chapter)

            if DEBUG_MODE:
                with open('course.json', 'w', encoding='utf-8') as f:
                    json.dump(self.course, f, indent=2)

            return self.course
        except StopIteration:
            print('failed to retrieve course data. make sure that the token is valid')

    def complete_lecture(self, lecture_id):
        try:
            data = {"lecture_id": lecture_id, "downloaded": False}

            response = requests.post(
                f'https://{self.subdomain}.udemy.com/api-2.0/users/me/subscribed-courses/{self.course_id}/completed-lectures/',
                headers=self.headers, json=data)
            return response.status_code // 100 == 2
        except Exception as e:
            print(e)
            return False

    def get_quiz_stats(self, quiz_id, quiz_attempt_id):
        response = requests.get(
            f'https://{self.subdomain}.udemy.com/api-2.0/users/me/subscribed-courses/{self.course_id}/quizzes/{quiz_id}/user-attempted-quizzes/{quiz_attempt_id}/stats/',
            headers=self.headers
        )
        print(response.text)

    def attempt_quiz(self, quiz_id, quiz_version=1):
        params = (
            ('fields/[user_attempted_quiz/]',
             'id,created,viewed_time,completion_time,version,completed_assessments,results_summary'),
        )

        data = {"is_viewed": True, "version": quiz_version}

        response = requests.post(
            f'https://{self.subdomain}.udemy.com/api-2.0/users/me/subscribed-courses/{self.course_id}/quizzes/{quiz_id}/user-attempted-quizzes/',
            headers=self.headers, params=params, json=data
        )
        return response.json()['id']

    def get_quiz_answers(self, quiz_id):
        params = (
            ('version', '1'),
            ('page_size', '250'),
            ('fields/[assessment/]',
             'id,assessment_type,correct_response'),
        )

        response = requests.get(f'https://{self.subdomain}.udemy.com/api-2.0/quizzes/{quiz_id}/assessments/',
                                headers=self.headers, params=params)
        # print(response)
        # pprint(response.json())

        return [{'id': result['id'], 'ans': result['correct_response']} for result in response.json()['results']]

    def submit_quiz_answer(self, assesment_id, response, quiz_attempt_id):
        data = {"assessment_id": assesment_id, "response": response, "duration": random.randint(5, 20)}

        response = requests.post(
            f'https://{self.subdomain}.udemy.com/api-2.0/users/me/subscribed-courses/{self.course_id}/user-attempted-quizzes/{quiz_attempt_id}/assessment-answers/',
            headers=self.headers, json=data
        )
        return response.status_code // 100 == 2

    def get_completed_materials(self):
        try:
            params = {
                'fields/[course/]': 'completed_lecture_ids,completed_quiz_ids,last_seen_page,completed_assignment_ids,first_completion_time'
            }

            response = requests.get(
                f'https://{self.subdomain}.udemy.com/api-2.0/users/me/subscribed-courses/{self.course_id}/progress/',
                headers=self.headers, params=params
            )

            completed_data = response.json()

            if completed_data["completion_ratio"] == 100:
                return 100

            cprint(f'currently completed: {completed_data["completion_ratio"]}%', 'yellow')
            self.completed_materials.extend(completed_data['completed_lecture_ids'])
            self.completed_materials.extend(completed_data['completed_quiz_ids'])
            self.completed_materials.extend(completed_data['completed_assignment_ids'])
            return completed_data["completion_ratio"]
        except Exception as e:
            cprint(e, 'red')
            return 0

    def mark_as_completed(self, resource_id):
        data = {"marked_completed": True}
        try:
            response = requests.post(
                f'https://{self.subdomain}.udemy.com/api-2.0/users/me/subscribed-courses/{self.course_id}/'
                f'quizzes/{resource_id}/user-attempted-quizzes/',
                headers=self.headers, json=data)
            # print(response)
            # print(response.json())
            return response.status_code // 100 == 2
        except Exception as e:
            cprint(e, 'red')
            return False


def complete_this_course(course_url, token, client_id):
    udemy = Udemy(course_url, token, client_id)
    udemy.get_course_info()
    udemy.get_user_info()

    cprint('-' * 100, 'cyan')
    cprint(f"course: {udemy.course_info['title']}", 'cyan')
    cprint('-' * 100, 'cyan')

    # check if the course is already 100% complete
    completed_percentage = udemy.get_completed_materials()
    if completed_percentage == 100:
        return 100

    udemy.get_course_resources()

    for chapter_index, chapter in enumerate(udemy.course):
        cprint(f'{chapter_index + 1}. {chapter["chapter"]} [chapter] '.ljust(100, '='), 'magenta')

        # complete the lectures
        for lecture_index, lecture in enumerate(chapter['lectures']):
            if lecture['id'] in udemy.completed_materials:
                cprint(f'{lecture_index + 1}. {lecture["title"]} [lecture]: already completed', 'cyan')
                continue

            completed = udemy.complete_lecture(lecture['id'])
            if completed:
                cprint(f'{lecture_index + 1}. {lecture["title"]} [lecture]: completed', 'green')
            else:
                cprint(f'{lecture_index + 1}. {lecture["title"]} [lecture]: could not be completed', 'red')

        # complete quizzes
        for quiz_index, quiz in enumerate(chapter['quizzes']):
            print(quiz)
            if quiz['type'] == 'coding-exercise' or quiz['type'] == 'practice-test':
                # if this is a coding exercise, then leave it to be completed by ticking the checkbox
                #  TODO:  complete the coding exercise with proper API
                continue

            if quiz['id'] in udemy.completed_materials:
                cprint(f'{quiz_index + 1}. {quiz["title"]} [quiz]: already completed', 'cyan')
                continue

            try:
                quiz_answers = udemy.get_quiz_answers(quiz['id'])
                attempt_id = udemy.attempt_quiz(quiz['id'])
                for quiz_answer in quiz_answers:
                    udemy.submit_quiz_answer(
                        assesment_id=quiz_answer['id'],
                        response=quiz_answer['ans'],
                        quiz_attempt_id=attempt_id
                    )
                cprint(f'{quiz_index + 1}. {quiz["title"]} [quiz]: submitted', 'green')
            except Exception as e:
                traceback.print_exc()

        # attempt to complete other materials
        for other_index, other in enumerate(chapter['others']):
            if other['id'] in udemy.completed_materials:
                cprint(f'{other_index + 1}. {other.get("title")} [{other["class"]}]: already completed', 'cyan')
                continue

            completed = udemy.complete_lecture(other['id'])
            if completed:
                cprint(f'{other_index + 1}. {other["title"]} [{other["class"]}]: completed', 'green')
            else:
                cprint(f'{other_index + 1}. {other["title"]} [{other["class"]}]: could not be completed', 'red')

    # check if any materials are left out, then attempt to complete them by ticking the checkbox
    time.sleep(5)
    completed_percentage = udemy.get_completed_materials()
    if completed_percentage == 100:
        cprint('course is 100% complete', 'green')
        return 100

    print('attempting to complete rest of the resources...')
    for chapter_index, chapter in enumerate(udemy.course):
        resources = chapter['quizzes'] + chapter['lectures'] + chapter['others']
        for res_idx, res in enumerate(resources):
            if res['id'] in udemy.completed_materials:
                if DEBUG_MODE:
                    cprint(f'{res_idx + 1}. {res["title"]}: already completed', 'cyan')
                continue
            completed = udemy.mark_as_completed(res['id'])
            if completed:
                cprint(f'{res_idx + 1}. {res["title"]}: completed', 'green')
            else:
                cprint(f'{res_idx + 1}. {res["title"]}: could not be completed', 'red')

    # check the final completion percentage
    time.sleep(10)
    return udemy.get_completed_materials()


def create_config():
    cprint('Steps to get your udemy token and client id:', 'cyan')
    cprint('--------------------------------------------', 'cyan')
    cprint('1. open the course lectures page', 'cyan')
    cprint('2. press ctrl + shift + J to open js console', 'cyan')
    cprint('3. copy and paste the code from get-token.js)', 'cyan')
    cprint('4. press enter and copy the data one by one)', 'cyan')
    token = input('token: ').strip()
    client_id = input('client id: ').strip()
    config = {'token': token, 'clientId': client_id}
    with open(file('config.json'), 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2)
    return config


def get_config():
    if os.path.exists(file('config.json')):
        try:
            with open(file('config.json'), encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return create_config()
    else:
        return create_config()


def main():
    config = get_config()
    course_url = input('course url: ').strip()
    completed_percentage = complete_this_course(course_url, config['token'], config['clientId'])

    if completed_percentage == 100:
        cprint('course 100% completed', 'green')
    else:
        cprint(f'course {completed_percentage}% completed', 'yellow')


if __name__ == '__main__':
    colorama.init()  # required for windows
    main()
