import pyautogui as pg
import time
import selenium
from selenium import webdriver
import selenium.common
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
import requests
from bs4 import BeautifulSoup
import re
import cv2 
import numpy as np
from PIL import Image
from datetime import datetime
import threading
import multiprocessing as mp
import concurrent.futures
import sys
import os
import dill

dir = os.path.abspath(os.path.join(__file__, '..'))
def parsing(file_path, encoding='utf-8'):
    with open(os.path.join(dir, file_path), 'r', encoding=encoding) as f:
        content = f.read()
        content = [j for i in content.split('\n') for j in i.split(',') if j != '']
        # print(content)
    return content

url = "https://www.hifini.com/user-login.htm"
with open(os.path.join(dir, 'username.csv'), 'r', encoding='utf-8') as f:
    # usn_set = list(csv.reader(f, delimiter=','))
    # usn_set = [usn for i in usn_set for usn in i]
    usn_set = parsing('username.csv')

with open(os.path.join(dir, 'password.csv'), 'r', encoding='utf-8') as f:
    # pwd_set = list(csv.reader(f, delimiter=','))
    # pwd_set = [pwd for i in pwd_set for pwd in i]
    pwd_set = parsing('password.csv')

# All the 6 methods for comparison in a list
methods = ['TM_CCOEFF', 'TM_CCOEFF_NORMED', 'TM_CCORR',
            'TM_CCORR_NORMED', 'TM_SQDIFF', 'TM_SQDIFF_NORMED']

def load_image(url, name, shrink):
    """
    url: specifies the URL of the image to be loaded
    name: specifies the name of the image (pattern or bg)
    shrink: specifies the distance to shrink the border of the image (for pattern only)
    """
    image = requests.get(url)

    # convert the image to a numpy array and then decode it
    image_array = np.frombuffer(image.content, np.uint8)
    image = cv2.imdecode(image_array, cv2.IMREAD_COLOR)

    # convert the image to grayscale
    gray_image = cv2.imdecode(image_array, cv2.IMREAD_GRAYSCALE)

    
    if name == "pattern":
        gray_image = gray_image[shrink:80 - shrink, shrink:80 - shrink]
        for i in range(gray_image.shape[0]):
            for j in range(gray_image.shape[1]):
                gray_image[i][j] -= 80
                
    # cv2.imshow("Grayscale Image from URL", image)
    # cv2.imshow("Grayscale Image from URL", gray_image)

    cv2.waitKey(0)
    return (image, gray_image)

def failed_geetest(driver):
    pattern = driver.find_element(By.CSS_SELECTOR, "div[class$='geetest_slice_bg']")

    bg = driver.find_element(By.CSS_SELECTOR, "div[class^='geetest_bg']")

    pattern_image_url = pattern.get_attribute('style')
    bg_image_url = bg.get_attribute('style')

    # parsing URLs for the pattern and background images
    pattern_image_url = pattern.get_attribute('style').split('url("')[1].split('"')[0]
    bg_image_url = bg.get_attribute('style').split('url("')[1].split('");')[0]
    print("pattern image URL:", pattern_image_url)
    
    # distance to shrink the border of the pattern image
    shrink = 10
    pattern_img, pattern_gray = load_image(pattern_image_url, "pattern", shrink)
    bg_img, bg_gray = load_image(bg_image_url, "bg", shrink)

    w, h = pattern_gray.shape[::-1]

    result = cv2.matchTemplate(bg_gray, pattern_gray, cv2.TM_CCOEFF_NORMED)
    
    (minVal, maxVal, minLoc, maxLoc) = cv2.minMaxLoc(result)
    # print(minVal, maxVal, minLoc, maxLoc)
    (startX, startY) = maxLoc
    endX = startX + pattern_img.shape[1]
    endY = startY + pattern_img.shape[0]
    
    # draw the bounding box on the image
    cv2.rectangle(bg_img, (startX, startY), (endX, endY), (255, 0, 0), 3)
    # show the output image
    # cv2.imshow("Output", bg_img)
    # cv2.waitKey(0)

    # hold and drag the mouse to the center of the pattern
    button = driver.find_element(By.CSS_SELECTOR, "div[class$='geetest_btn']")
    # print("button location:", button.location)

    actions = webdriver.ActionChains(driver)
    actions.click_and_hold(button).move_by_offset(startX - shrink, 0).release().perform()
    time.sleep(5)
    try:
        button = driver.find_element(By.CSS_SELECTOR, "div[id*='taghot']")
    except selenium.common.exceptions.NoSuchElementException:
        print("Failed to bypass geetest captcha")
        failed_geetest()

def solve_captcha(driver, pattern_image_url, bg_image_url, shrink):
    pattern_img, pattern_gray = load_image(pattern_image_url, "pattern", shrink)
    bg_img, bg_gray = load_image(bg_image_url, "bg", shrink)

    w, h = pattern_gray.shape[::-1]
    result = cv2.matchTemplate(bg_gray, pattern_gray, cv2.TM_CCOEFF_NORMED)
    (minVal, maxVal, minLoc, maxLoc) = cv2.minMaxLoc(result)

    # print(minVal, maxVal, minLoc, maxLoc)
    (startX, startY) = maxLoc
    endX = startX + pattern_img.shape[1]
    endY = startY + pattern_img.shape[0]
    
    # draw the bounding box on the image
    cv2.rectangle(bg_img, (startX, startY), (endX, endY), (255, 0, 0), 3)
    # show the output image
    # cv2.imshow("Output", bg_img)
    # cv2.waitKey(0)

    # hold and drag the mouse to the center of the pattern
    button = driver.find_element(By.CSS_SELECTOR, "div[class$='geetest_btn']")
    actions = webdriver.ActionChains(driver)
    actions.click_and_hold(button).move_by_offset(startX - shrink, 0).release().perform()
    time.sleep(6)
    try:
        button = driver.find_element(By.CSS_SELECTOR, "div[id*='taghot']")
    except selenium.common.exceptions.NoSuchElementException as e:
        print("Failed to bypass geetest captcha")
        failed_geetest(driver)
    

def login_and_sign_in(usn, pwd):
# login to the website
    driver = webdriver.Chrome()
    driver.get(url)
    driver.maximize_window()

    username_input = driver.find_element(By.ID, "email")
    password_input = driver.find_element(By.ID, "password")

    username_input.send_keys(usn)
    password_input.send_keys(pwd)
    login_button = driver.find_element(By.ID, "submit")
    login_button.click()
    time.sleep(2)

# search for the pattern and background images and bypass the geetest captcha
    # search in html under div with class starting in "geetest_slice_bg_"
    # div = driver.find_element(By.CSS_SELECTOR, "div[class^='geetest_slice_bg_']")
    
    # search in html under div with class ending in "geetest_slice_bg"
    # use "$=" if you intend to match a pattern in the middle of the class name...
    pattern = driver.find_element(By.CSS_SELECTOR, "div[class$='geetest_slice_bg']")
    bg = driver.find_element(By.CSS_SELECTOR, "div[class^='geetest_bg']")

    pattern_image_url = pattern.get_attribute('style').split('url("')[1].split('"')[0]
    bg_image_url = bg.get_attribute('style').split('url("')[1].split('");')[0]


    # distance to shrink the border of the pattern image
    shrink = 10
    # Using multiprocessing to solve CAPTCHA in parallel
    solve_captcha(driver, pattern_image_url, bg_image_url, shrink)
    # process = mp.Process(target=solve_captcha, args=(driver, pattern_image_url, bg_image_url, shrink))
    # process.start()
    # process.join()

# Perform sign-in after CAPTCHA bypass
    driver.get("https://www.hifini.com/")
    sign_in = driver.find_element(By.ID, "sign")
    sign_in.click()
    time.sleep(2)
    driver.quit()


def multithreading():
    threads = []
    for (usn, pwd) in zip(usn_set, pwd_set):
        t = threading.Thread(target=login_and_sign_in, args=(usn, pwd))
        threads.append(t)
        t.start()
    
    for t in threads:
        t.join()

def multithreading_pool():
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
        pool.map(login_and_sign_in, usn_set, pwd_set)

if __name__ == '__main__':  
    # webdriver's not serializable -> can't use multiprocessing
    # print("whether webdriver Chrome instances are pickable/serializable:", dill.pickles(webdriver.Chrome()))

    start = time.time()
    multithreading_pool()
    end = time.time()
    print(f'Time taken: {end - start:.4f} seconds')
    # time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    print(f'Finished login and sign-in on {url.split(".")[1]} at time:', datetime.now(), sep='\n')

