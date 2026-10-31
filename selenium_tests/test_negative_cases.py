import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

BASE_URL = "http://localhost:5500/frontend"

def test_negative_login():
    print("\n--- Testing Negative Login Case ---")
    driver = webdriver.Chrome()
    driver.maximize_window()
    
    try:
        driver.get(f"{BASE_URL}/login.html")
        wait = WebDriverWait(driver, 10)
        
        email_field = wait.until(EC.presence_of_element_located((By.ID, "email")))
        password_field = driver.find_element(By.ID, "password")
        
        # Wrong Credentials
        email_field.send_keys("wronguser@gmail.com")
        password_field.send_keys("WrongPass123")
        
        login_btn = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
        login_btn.click()
        
        time.sleep(2)
        
        # Check if error message is displayed
        msg_box = driver.find_element(By.ID, "message")
        if msg_box.is_displayed():
            print(f"✅ Negative Login Handled Successfully! Error Message: {msg_box.text}")
        else:
            print("❌ Expected error message not found.")
            
    except Exception as e:
        print(f"❌ Error in Negative Login Test: {e}")
    finally:
        driver.quit()

if __name__ == "__main__":
    test_negative_login()