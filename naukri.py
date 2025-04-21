#! python3
# -*- coding: utf-8 -*-
"""Naukri Daily update - Using Chrome"""
import json
import logging
import os
import sys
import time
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager as CM

# Load configuration from config.json
with open('config.json', 'r') as config_file:
    config = json.load(config_file)

# Fetch keys from config.json
username = config['Credentials']['username']
password = config['Credentials']['password']
originalResumePath = config['Paths']['originalResumePath']

# Calculate Last Working Date (3 months from today)
future_date = datetime.today() + timedelta(days=90)
LWD_DAY = future_date.strftime("%d")
LWD_MONTH = future_date.strftime("%b")  # Three-letter format
LWD_YEAR = future_date.strftime("%Y")

# If Headless = True, script runs Chrome in headless mode without visible GUI
headless = False

# Set login URL
NaukriURL = "https://www.naukri.com/nlogin/login"

logging.basicConfig(level=logging.INFO, filename="naukri.log", format="%(asctime)s    : %(message)s")
os.environ["WDM_LOCAL"] = "1"
os.environ["WDM_LOG_LEVEL"] = "0"


def log_msg(message):
    """Print to console and store to Log"""
    print(message)
    logging.info(message)


def catch(error):
    """Method to catch errors and log error details"""
    _, _, exc_tb = sys.exc_info()
    lineNo = str(exc_tb.tb_lineno)
    msg = f"{type(error)} : {error} at Line {lineNo}."
    print(msg)
    logging.error(msg)


def getObj(locatorType):
    """This map defines how elements are identified"""
    return {
        "ID": By.ID,
        "NAME": By.NAME,
        "XPATH": By.XPATH,
        "TAG": By.TAG_NAME,
        "CLASS": By.CLASS_NAME,
        "CSS": By.CSS_SELECTOR,
        "LINKTEXT": By.LINK_TEXT,
    }[locatorType.upper()]


def GetElement(driver, elementTag, locator="ID"):
    """Wait max 15 secs for element and then select when it is available"""
    try:
        _by = getObj(locator)
        if is_element_present(driver, _by, elementTag):
            return WebDriverWait(driver, 15).until(lambda d: driver.find_element(_by, elementTag))
    except Exception as e:
        catch(e)
    return None


def is_element_present(driver, how, what):
    """Returns True if element is present"""
    try:
        driver.find_element(by=how, value=what)
    except NoSuchElementException:
        return False
    return True


def WaitTillElementPresent(driver, elementTag, locator="ID", timeout=30):
    """Wait till element is present. Default 30 seconds"""
    driver.implicitly_wait(0)
    for _ in range(timeout):
        time.sleep(0.99)
        if is_element_present(driver, getObj(locator), elementTag):
            driver.implicitly_wait(3)
            return True
    log_msg(f"Element not found with {locator} : {elementTag}")
    driver.implicitly_wait(3)
    return False


def tearDown(driver):
    try:
        driver.close()
        log_msg("Driver Closed Successfully")
    except Exception as e:
        catch(e)

    try:
        driver.quit()
        log_msg("Driver Quit Successfully")
    except Exception as e:
        catch(e)


def LoadNaukri(headless):
    """Open Chrome to load Naukri.com"""
    options = webdriver.ChromeOptions()
    options.add_argument("--disable-notifications")
    options.add_argument("--start-maximized")
    options.add_argument("--disable-popups")
    options.add_argument("--disable-gpu")
    if headless:
        options.add_argument("headless")

    driver = webdriver.Chrome(options=options, service=ChromeService(CM().install()))
    log_msg("Google Chrome Launched!")

    driver.implicitly_wait(3)
    driver.get(NaukriURL)
    return driver


def naukriLogin(headless=False):
    """Login to Naukri.com"""
    status = False
    driver = None
    username_locator = "usernameField"
    password_locator = "passwordField"
    login_btn_locator = "//*[@type='submit' and normalize-space()='Login']"
    skip_locator = "//*[text() = 'SKIP AND CONTINUE']"

    try:
        driver = LoadNaukri(headless)

        if is_element_present(driver, By.ID, username_locator):
            GetElement(driver, username_locator, locator="ID").send_keys(username)
            GetElement(driver, password_locator, locator="ID").send_keys(password)
            GetElement(driver, login_btn_locator, locator="XPATH").send_keys(Keys.ENTER)

            if WaitTillElementPresent(driver, skip_locator, "XPATH", 10):
                GetElement(driver, skip_locator, "XPATH").click()
            if WaitTillElementPresent(driver, "ff-inventory", locator="ID", timeout=40):
                log_msg("Naukri Login Successful")
                status = True
                return status, driver

    except Exception as e:
        catch(e)
    return status, driver


def UpdateLastWorkingDate(driver, day, month, year):
    """Updates Last Working Date in Naukri profile"""
    try:
        log_msg(f"Updating Last Working Date to {day}-{month}-{year}...")

        edit_locator = "(//*[contains(@class, 'icon edit')])[1]"
        save_xpath = "//button[@type='submit'][@value='Save Changes'] | //*[@id='saveBasicDetailsBtn']"
        save_confirm = "//*[text()='today' or text()='Today'] | //*[@class='success-msg']"

        WaitTillElementPresent(driver, edit_locator, "XPATH", 20)
        GetElement(driver, edit_locator, locator="XPATH").click()

        day_input = GetElement(driver, "lwdDayFor", "ID")
        month_input = GetElement(driver, "lwdMonthFor", "ID")
        year_input = GetElement(driver, "lwdYearFor", "ID")

        for input_field, value in [(day_input, day), (month_input, month), (year_input, year)]:
            if input_field:
                input_field.clear()
                input_field.send_keys(value)
                input_field.send_keys(Keys.ENTER)

        GetElement(driver, save_xpath, locator="XPATH").click()

        if WaitTillElementPresent(driver, save_confirm, "XPATH", 10):
            log_msg(f"Last Working Date successfully updated to {day}-{month}-{year}.")

    except Exception as e:
        catch(e)


def upload_resume(driver, resume_path):
    """Uploads a resume file to Naukri.com"""
    try:
        attach_cv_id = "attachCV"
        checkpoint_xpath = "//*[contains(@class, 'updateOn')]"

        driver.get("https://www.naukri.com/mnjuser/profile")
        time.sleep(2)

        WaitTillElementPresent(driver, attach_cv_id, "ID", 10)
        GetElement(driver, attach_cv_id, "ID").send_keys(resume_path)

        if WaitTillElementPresent(driver, checkpoint_xpath, "XPATH", 30):
            log_msg("Resume Upload Successful")

    except Exception as e:
        catch(e)


def main():
    log_msg("----- Naukri Script Start -----")
    driver = None
    try:
        status, driver = naukriLogin(headless)
        if status:
            upload_resume(driver, originalResumePath)
            UpdateLastWorkingDate(driver, LWD_DAY, LWD_MONTH, LWD_YEAR)
    except Exception as e:
        catch(e)
    finally:
        tearDown(driver)

    log_msg("----- Naukri Script End -----\n")


if __name__ == "__main__":
    main()
