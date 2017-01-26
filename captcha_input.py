from splinter import Browser
import random
import time
import math
import requests
from PIL import Image
import os
import glob


def find_image_url(captcha_iframe, image_checkboxes=None):
    if image_checkboxes:
        image_urls = []
        for checkbox in image_checkboxes:
            x, y = checkbox['position']
            changed_image_xpath = '//*[@id="rc-imageselect-target"]/table/tbody/tr[{0}]/td[{1}]/div/div[1]/img'\
                .format(x, y)
            if captcha_iframe.is_element_present_by_xpath(changed_image_xpath, wait_time=3):
                image_url = captcha_iframe.find_by_xpath(changed_image_xpath)['src']
                image_urls.append(image_url)
        return image_urls
    else:
        image_xpath = '//*[@id="rc-imageselect-target"]/table/tbody/tr[1]/td[1]/div/div[1]/img'
        if captcha_iframe.is_element_present_by_xpath(image_xpath, wait_time=3):
            image_url = captcha_iframe.find_by_xpath(image_xpath)['src']
        return image_url


def pick_checkboxes_from_positions(random_positions, image_checkboxes):
    random_checkboxes = []
    for pos in random_positions:  # use these random positions to pick checkboxes (i.e. images)
        random_checkboxes.append(image_checkboxes[pos])

    # print(len(random_checkboxes))
    return random_checkboxes


def pick_random_checkboxes(image_checkboxes):
    random_positions = None
    if len(image_checkboxes) != 1:
        checkbox_num = random.randint(1, math.ceil(len(image_checkboxes)/2))

        # get a set of random positions so we know which ones we picked
        random_positions = random.sample(range(len(image_checkboxes)), checkbox_num)

        random_checkboxes = pick_checkboxes_from_positions(random_positions, image_checkboxes)

        # random_checkboxes = random.sample(image_checkboxes, checkbox_num)
        for checkbox in random_checkboxes:
            checkbox['checkbox'].click()

    return random_positions


def get_image_checkboxes(rows, cols, captcha_iframe):
    image_checkboxes = []
    for i in range(1, len(rows)+1):  # these numbers should be calculated by how big the grid is for the captcha
        for j in range(1, len(cols)+1):
            checkbox_xpath = '//*[@id="rc-imageselect-target"]/table/tbody/tr[{0}]/td[{1}]/div'.format(i, j)

            if captcha_iframe.is_element_present_by_xpath(checkbox_xpath, wait_time=3):
                image_checkboxes.append({'checkbox': captcha_iframe.find_by_xpath(checkbox_xpath), 'position': (i, j)})

    return image_checkboxes


def verify(captcha_iframe, correct_score, total_guesses):
    if captcha_iframe.is_element_present_by_id('recaptcha-verify-button', wait_time=3):
        verify_button = captcha_iframe.find_by_id('recaptcha-verify-button')
        verify_button.first.click()

    not_select_all_images_error = captcha_iframe.is_text_not_present('Please select all matching images.')
    not_retry_error = captcha_iframe.is_text_not_present('Please try again.')
    not_select_more_images_error = captcha_iframe.is_text_not_present('Please also check the new images.')
    if not_select_all_images_error and not_retry_error and not_select_more_images_error:
        correct_score += 1
    total_guesses += 1
    print("Total possibly correct: {correct}".format(correct=correct_score))
    print("Total guesses: {guesses}".format(guesses=total_guesses))
    print("Percentage: {percent}".format(percent=float(correct_score)/total_guesses))


def delete_old_images():
    old_captcha_images = glob.glob('*captcha-*.jpg')
    for image in old_captcha_images:
        os.remove(os.path.join(os.path.dirname(os.path.abspath(__file__)), image))


def download_images(image_url, row_count, col_count, image_urls=None):
    if image_urls:
        delete_old_images()

        for i, url in enumerate(image_urls):
            img = Image.open(requests.get(url, stream=True).raw)
            img.save("new-captcha-{0}.jpg".format(i), "JPEG")
    else:
        img = Image.open(requests.get(image_url, stream=True).raw)
        img.save("original-captcha-image.jpg", "JPEG")

        delete_old_images()

        width = img.size[0] / col_count
        height = img.size[1] / row_count

        for row in range(row_count):
            for col in range(col_count):
                dimensions = (col * width, row * height, col * width + width, row * height + height)
                individual_captcha_image = img.crop(dimensions)
                individual_captcha_image.save("captcha-{0}-{1}.jpg".format(row, col), "JPEG")

def find_rows_and_cols(captcha_iframe):
    rows = captcha_iframe.find_by_xpath('//*[@id="rc-imageselect-target"]/table/tbody/child::tr')
    cols = captcha_iframe.find_by_xpath('//*[@id="rc-imageselect-target"]/table/tbody/tr[1]/child::td')

    return rows, cols


def guess_captcha(browser):
    if browser.is_element_present_by_css('body > div > div:nth-child(4) > iframe', wait_time=3):
        image_iframe = browser.find_by_css('body > div > div:nth-child(4) > iframe')

        with browser.get_iframe(image_iframe.first['name']) as captcha_iframe:
            correct_score = 0
            total_guesses = 0  # not necessarily separate captchas, one captcha with new images added would count as two
            # image_checkboxes = captcha_iframe.find_by_xpath('//div[@class="rc-imageselect-checkbox"]')

            new_run = True
            while True:
                rows, cols = find_rows_and_cols(captcha_iframe)
                row_count = len(rows)
                col_count = len(cols)

                # need to keep getting images and image urls until this batch of image urls is the same as the last run
                # i.e. keep selecting images until the captcha stops replacing images
                checkbox_xpath = '//*[@id="rc-imageselect-target"]/table/tbody/tr[1]/td[1]/div'

                if captcha_iframe.is_element_not_present_by_xpath(checkbox_xpath, wait_time=3):
                    recaptcha_reload_button = captcha_iframe.find_by_id('recaptcha-reload-button')
                    recaptcha_reload_button.click()
                    continue

                if new_run:
                    image_checkboxes = get_image_checkboxes(rows, cols, captcha_iframe)

                    image_url = find_image_url(captcha_iframe)
                    download_images(image_url, row_count, col_count)

                    picked_positions = pick_random_checkboxes(image_checkboxes)
                    new_image_urls = find_image_url(captcha_iframe, image_checkboxes)

                    new_run = False

                elif any(image_url != new_image_url for new_image_url in new_image_urls):
                    new_image_checkboxes = get_image_checkboxes(rows, cols, captcha_iframe)

                    picked_checkboxes = pick_checkboxes_from_positions(picked_positions, new_image_checkboxes)

                    download_images(image_url, row_count, col_count, new_image_urls)

                    picked_positions = pick_random_checkboxes(picked_checkboxes)
                    if not picked_positions:
                        verify(captcha_iframe, correct_score, total_guesses)
                        new_run = True
                    image_url = find_image_url(captcha_iframe)
                    new_image_urls = find_image_url(captcha_iframe, new_image_checkboxes)
                else:
                    verify(captcha_iframe, correct_score, total_guesses)
                    new_run = True


with Browser() as browser:
    url = "https://nocturnaltortoise.github.io/captcha"
    browser.visit(url)

    try:
        with browser.get_iframe('undefined') as iframe:
            captcha_checkbox = iframe.find_by_xpath('//div[@class="recaptcha-checkbox-checkmark"]')
            captcha_checkbox.first.click()

        if browser.is_element_present_by_css('body > div > div:nth-child(4) > iframe', wait_time=3):
            guess_captcha(browser)

    except Exception as e:
        print(e)
        browser.screenshot('error')
