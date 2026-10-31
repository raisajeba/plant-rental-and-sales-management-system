import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

BASE_URL = "http://localhost:5500/frontend"

def test_customer_and_nursery_login():
    print("\n--- Testing Customer/Nursery Login ---")
    driver = webdriver.Chrome()
    driver.maximize_window()
    
    try:
        # 1. Unified Login Page-e jawya
        driver.get(f"{BASE_URL}/login.html")
        wait = WebDriverWait(driver, 10)
        
        # 2. Email & Password Input
        email_field = wait.until(EC.presence_of_element_located((By.ID, "email")))
        password_field = driver.find_element(By.ID, "password")
        
        # Customer Credential Test
        email_field.clear()
        email_field.send_keys("raisajeba8@gmail.com")  # Apnar test customer email
        password_field.clear()
        password_field.send_keys("Raisa@3456")         # Apnar test password
        
        # Submit Button Click
        login_btn = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
        login_btn.click()
        
        time.sleep(3)
        
        # 3. Check Token in LocalStorage & Redirect
        token = driver.execute_script("return localStorage.getItem('greennest_token');")
        if token:
            print("✅ Customer Login Successful! Token present in localStorage.")
        else:
            print("❌ Login Failed or Token not found in localStorage.")
            
    except Exception as e:
        print(f"❌ Error during Customer/Nursery Login: {e}")
    finally:
        driver.quit()

def test_nursery_login():
    print("\n--- Testing Nursery Owner Login ---")
    driver = webdriver.Chrome()
    driver.maximize_window()
    
    try:
        driver.get(f"{BASE_URL}/login.html")
        wait = WebDriverWait(driver, 10)
        
        email_field = wait.until(EC.presence_of_element_located((By.ID, "email")))
        password_field = driver.find_element(By.ID, "password")
        
        # Apnar test nursery owner-er email ebong password ekhane diben
        email_field.clear()
        email_field.send_keys("23201196@uap-bd.edu") 
        password_field.clear()
        password_field.send_keys("Sraboni@3456")
        
        login_btn = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
        login_btn.click()
        
        time.sleep(3)
        
        token = driver.execute_script("return localStorage.getItem('greennest_token');")
        if token:
            print("✅ Nursery Owner Login Successful! Token present in localStorage.")
        else:
            print("❌ Nursery Owner Login Failed!")
            
    except Exception as e:
        print(f"❌ Error during Nursery Login: {e}")
    finally:
        driver.quit()

def test_admin_login():
    print("\n--- Testing Admin Login ---")
    driver = webdriver.Chrome()
    driver.maximize_window()
    
    try:
        driver.get(f"{BASE_URL}/admin-login.html")
        wait = WebDriverWait(driver, 10)
        
        email_field = wait.until(EC.presence_of_element_located((By.ID, "adminEmail")))
        password_field = driver.find_element(By.ID, "adminPassword")
        
        email_field.clear()
        email_field.send_keys("admin@greennest.com")
        password_field.clear()
        password_field.send_keys("Admin@12345")
        
        login_btn = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
        login_btn.click()
        
        time.sleep(4)
        
        # Admin token key name is 'greennest_admin_token' in sessionStorage
        token = driver.execute_script("return sessionStorage.getItem('greennest_admin_token');")
        if token:
            print("✅ Admin Login Successful! Admin Token present in sessionStorage.")
        else:
            print("❌ Admin Login Failed!")
            
    except Exception as e:
        print(f"❌ Error during Admin Login: {e}")
    finally:
        driver.quit()

if __name__ == "__main__":
    test_customer_and_nursery_login()
    test_admin_login()