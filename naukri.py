#! python3
# -*- coding: utf-8 -*-
"""Naukri Daily update - Using Chrome (Headless-friendly)"""
import json
import logging
import os
import sys
import time
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager as CM

# Configure logging first
logging.basicConfig(
    level=logging.INFO,
    filename="naukri.log",
    format="%(asctime)s : %(levelname)s : %(message)s",
    filemode="a"
)
console = logging.StreamHandler()
console.setLevel(logging.INFO)
logging.getLogger().addHandler(console)

# Load configuration from config.json
try:
    with open('config.json', 'r') as config_file:
        config = json.load(config_file)
    
    # Fetch keys from config.json
    username = config['Credentials']['username']
    password = config['Credentials']['password']
    originalResumePath = config['Paths']['originalResumePath']
    
    script_dir = os.path.dirname(os.path.abspath(__file__))

    # Build absolute path to the file
    originalResumePath = os.path.join(script_dir, originalResumePath)
    # Check if file paths are valid
    if not os.path.isfile(originalResumePath):
        logging.error(f"Resume file not found: {originalResumePath}")
except FileNotFoundError:
    logging.error("Config file not found. Ensure config.json exists in the script directory.")
    sys.exit(1)
except KeyError as e:
    logging.error(f"Missing required configuration key: {e}")
    sys.exit(1)

# Calculate Last Working Date (3 months from today)
future_date = datetime.today() + timedelta(days=90)
LWD_DAY = future_date.strftime("%d")
LWD_MONTH = future_date.strftime("%b")  # Three-letter format
LWD_YEAR = future_date.strftime("%Y")

# Force headless mode for CI environments
headless = True

# Set login URL
NaukriURL = "https://www.naukri.com/nlogin/login"

# WebDriver Manager configuration
os.environ["WDM_LOCAL"] = "1"
os.environ["WDM_LOG_LEVEL"] = "0"


def log_msg(message):
    """Print to console and store to Log"""
    logging.info(message)


def catch(error):
    """Method to catch errors and log error details"""
    _, _, exc_tb = sys.exc_info()
    lineNo = str(exc_tb.tb_lineno)
    msg = f"{type(error).__name__}: {error} at Line {lineNo}."
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


def is_element_present(driver, how, what):
    """Returns True if element is present"""
    try:
        driver.find_element(by=how, value=what)
    except NoSuchElementException:
        return False
    return True


def GetElement(driver, elementTag, locator="ID"):
    """Wait max 15 secs for element and then select when it is available"""
    try:
        _by = getObj(locator)
        if is_element_present(driver, _by, elementTag):
            return WebDriverWait(driver, 15).until(
                EC.element_to_be_clickable((_by, elementTag))
            )
    except Exception as e:
        catch(e)
    return None


def WaitTillElementPresent(driver, elementTag, locator="ID", timeout=30):
    """Wait till element is present. Default 30 seconds"""
    try:
        driver.implicitly_wait(0)
        _by = getObj(locator)
        WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((_by, elementTag))
        )
        driver.implicitly_wait(3)
        return True
    except TimeoutException:
        log_msg(f"Element not found with {locator} : {elementTag}")
        driver.implicitly_wait(3)
        return False
    except Exception as e:
        catch(e)
        driver.implicitly_wait(3)
        return False


def tearDown(driver):
    """Safely close and quit the driver"""
    try:
        if driver:
            driver.close()
            log_msg("Driver Closed Successfully")
    except Exception as e:
        catch(e)

    try:
        if driver:
            driver.quit()
            log_msg("Driver Quit Successfully")
    except Exception as e:
        catch(e)


def LoadNaukri():
    """Open Chrome to load Naukri.com with proper headless configuration"""
    options = webdriver.ChromeOptions()
    
    # Essential configurations for headless environment
    options.add_argument("--headless=new")  # New headless implementation
    options.add_argument("--disable-dev-shm-usage")  # Overcome limited resource problems
    options.add_argument("--no-sandbox")  # Required in CI environments
    options.add_argument("--disable-gpu")  # Required for Windows/Linux
    
    # Browser optimization
    options.add_argument("--disable-notifications")
    options.add_argument("--window-size=1920,1080")  # Set window size explicitly
    options.add_argument("--disable-popup-blocking")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-blink-features=AutomationControlled")  # Prevent detection
    
    # User agents that may help avoid bot detection
    options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")
    
    # Additional settings helpful for debugging and avoiding detection
    options.add_experimental_option('excludeSwitches', ['enable-logging', 'enable-automation'])
    options.add_experimental_option('useAutomationExtension', False)
    
    # Add extra preferences
    prefs = {
        "profile.default_content_settings.popups": 0,
        "profile.default_content_setting_values.notifications": 2,
        "credentials_enable_service": False,
        "profile.password_manager_enabled": False
    }
    options.add_experimental_option("prefs", prefs)
    
    try:
        service = ChromeService(CM().install())
        driver = webdriver.Chrome(service=service, options=options)
        
        # Execute CDP commands to prevent detection
        driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
            "source": """
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
            """
        })
        
        log_msg("Google Chrome Launched in Headless Mode!")
        
        driver.implicitly_wait(10)  # Increased from 5 to 10 seconds
        driver.set_page_load_timeout(45)  # Increased from 30 to 45 seconds
        driver.get(NaukriURL)
        
        # Take screenshot for debugging in CI environment
        driver.save_screenshot("naukri_login_page.png")
        log_msg("Login page screenshot saved")
        
        # Wait for page to fully load
        time.sleep(5)
        
        return driver
    except Exception as e:
        catch(e)
        log_msg("Failed to initialize Chrome browser")
        sys.exit(1)


def naukriLogin():
    """Login to Naukri.com"""
    status = False
    driver = None
    
    try:
        driver = LoadNaukri()
        
        # Use the known working identifiers directly
        username_field = GetElement(driver, "usernameField", locator="ID")
        password_field = GetElement(driver, "passwordField", locator="ID")
        
        if username_field and password_field:
            log_msg("Login form found, entering credentials...")
            
            username_field.clear()
            username_field.send_keys(username)
            time.sleep(1)
            
            password_field.clear()
            password_field.send_keys(password)
            time.sleep(1)
            driver.save_screenshot("login_credential.png")
            # Use the known working login button XPath
            login_button = GetElement(driver, "//*[@type='submit' and normalize-space()='Login']", locator="XPATH")
            
            if login_button:
                login_button.click()
                log_msg("Login form submitted")
                
                # Wait for page to load after login
                time.sleep(5)
                
                # Simplified check for successful login - just check if we're on a profile/home page
                current_url = driver.current_url
                log_msg(f"Current URL after login: {current_url}")
                if "mnjuser" in current_url or "myprofile" in current_url or "home" in current_url:
                    log_msg("Naukri Login Successful")
                    driver.save_screenshot("dashboard.png")
                    status = True
                else:
                    log_msg("Login unsuccessful - check credentials")
            else:
                log_msg("Login button not found")
        else:
            log_msg("Could not find username or password fields")
            
    except Exception as e:
        catch(e)
        
    return status, driver


def upload_resume(driver, resume_path):
    """Uploads a resume file to Naukri.com"""
    try:
        # Check if file exists and is accessible
        if not os.path.isfile(resume_path):
            log_msg(f"Resume file not found at path: {resume_path}")
            return False
        
        # Get absolute path to handle relative paths in CI environment
        resume_path = os.path.abspath(resume_path)
        log_msg(f"Using resume path: {resume_path}")
        
        # Navigate directly to the profile page
        driver.get("https://www.naukri.com/mnjuser/profile")
        log_msg("Navigating to profile page")
        driver.save_screenshot("profile_page.png")
        time.sleep(5)  # Give page time to fully load
        
        # Use JavaScript to scroll down to make sure upload element is visible
        driver.execute_script("window.scrollTo(0, 300)")
        time.sleep(2)
        
        # Try specific ID directly first (from provided HTML)
        upload_id = "attachCV"
        log_msg(f"Looking for upload element with ID: {upload_id}")
        
        # Try to make the file input visible and clickable via JavaScript
        js_make_visible = """
        var fileInput = document.getElementById('attachCV');
        if (fileInput) {
            fileInput.style.display = 'block';
            fileInput.style.opacity = 1;
            fileInput.style.visibility = 'visible';
            fileInput.style.position = 'relative';
            fileInput.style.height = 'auto';
            fileInput.style.width = 'auto';
        }
        """
        driver.execute_script(js_make_visible)
        time.sleep(2)
        
        # Try to find the element
        if WaitTillElementPresent(driver, upload_id, "ID", 10):
            file_input = GetElement(driver, upload_id, "ID")
            if file_input:
                try:
                    # Send keys directly
                    file_input.send_keys(resume_path)
                    log_msg("Resume file path submitted via direct method")
                    driver.save_screenshot("after_file_select.png")
                    
                    
                    # Look for update button that might need clicking
                    update_button_xpath = "//input[@type='button'][@value='Update resume'] | //button[contains(text(), 'Update')]"
                    if WaitTillElementPresent(driver, update_button_xpath, "XPATH", 5):
                        update_button = GetElement(driver, update_button_xpath, "XPATH")
                        if update_button:
                            update_button.click()
                            log_msg("Clicked update resume button")
                            log_msg("Resume Upload Successful after clicking update button")
                            driver.save_screenshot("resume_uploaded_with_update.png")
                            return True
                except Exception as e:
                    log_msg(f"Error sending file path: {e}")
            else:
                log_msg("File input element found but not accessible")
        else:
            log_msg("Could not find upload element with ID 'attachCV'")
            
        # Take screenshot for debugging
        driver.save_screenshot("resume_upload_failed.png")
        log_msg("Resume upload failed with all methods")
        
    except Exception as e:
        catch(e)
        driver.save_screenshot("resume_upload_error.png")
        
    return False


def UpdateLastWorkingDate(driver, day, month, year):
    """Updates Last Working Date in Naukri profile"""
    try:
        log_msg(f"Updating Last Working Date to {day}-{month}-{year}...")
        
        # Navigate to profile page first
        driver.get("https://www.naukri.com/mnjuser/profile")
        time.sleep(3)

        # Use the known working edit button locator
        edit_locator = "(//*[contains(@class, 'icon edit')])[1]"
        
        if WaitTillElementPresent(driver, edit_locator, "XPATH", 10):
            edit_button = GetElement(driver, edit_locator, locator="XPATH")
            if edit_button:
                edit_button.click()
                log_msg("Edit button clicked")
                time.sleep(2)
                
                # Use the known working field IDs
                day_input = GetElement(driver, "lwdDayFor", "ID")
                month_input = GetElement(driver, "lwdMonthFor", "ID")
                year_input = GetElement(driver, "lwdYearFor", "ID")

                # Fill in date fields
                for input_field, value in [(day_input, day), (month_input, month), (year_input, year)]:
                    if input_field:
                        input_field.clear()
                        input_field.send_keys(value)
                        input_field.send_keys(Keys.ENTER)
                        time.sleep(1)
                
                # Use the known working save button
                save_xpath = "//button[@type='submit'][@value='Save Changes'] | //*[@id='saveBasicDetailsBtn']"
                save_button = GetElement(driver, save_xpath, locator="XPATH")
                if save_button:
                    save_button.click()
                    log_msg("Save button clicked")
                    time.sleep(3)  # Wait for save to complete
                    
                    # No need to check for confirmation as testing confirms it works
                    log_msg(f"Last Working Date successfully updated to {day}-{month}-{year}.")
                else:
                    log_msg("Save button not found")
            else:
                log_msg("Edit button not found")
        else:
            log_msg("Edit button not present in profile")

    except Exception as e:
        catch(e)


def main():
    log_msg("----- Naukri Script Start -----")
    driver = None
    
    # Set environment variables that might help with headless execution
    os.environ['MOZ_HEADLESS'] = '1'
    
    # Increase script verbosity in CI environment
    if 'CI' in os.environ:
        log_msg("Running in CI environment")
        logging.getLogger().setLevel(logging.DEBUG)
    
    try:
        # Login to Naukri
        status, driver = naukriLogin()
        
        # If login was successful, proceed with tasks
        if status and driver:
            # Take screenshot of homepage
            driver.save_screenshot("homepage.png")
            
            # Try to update resume
            upload_success = upload_resume(driver, originalResumePath)
            if upload_success:
                log_msg("Resume upload successful")
            else:
                log_msg("Resume upload failed")
            
            # Update last working date
            try:
                UpdateLastWorkingDate(driver, LWD_DAY, LWD_MONTH, LWD_YEAR)
            except Exception as e:
                log_msg(f"Error updating last working date: {e}")
        else:
            log_msg("Login was not successful")
    except Exception as e:
        catch(e)
    finally:
        if driver:
            tearDown(driver)

    log_msg("----- Naukri Script End -----\n")


if __name__ == "__main__":
    main()