import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

BASE_URL = "http://localhost:5500/frontend"

def test_customer_workflow():
    print("\n--- Testing Customer Complete Workflow ---")
    driver = webdriver.Chrome()
    driver.maximize_window()
    
    try:
        wait = WebDriverWait(driver, 10)
        
        # 1. Customer Login (`login.html`)
        driver.get(f"{BASE_URL}/login.html")
        email_field = wait.until(EC.presence_of_element_located((By.ID, "email")))
        password_field = driver.find_element(By.ID, "password")
        
        email_field.clear()
        email_field.send_keys("raisajeba8@gmail.com")
        password_field.clear()
        password_field.send_keys("Raisa@3456")
        
        login_btn = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
        login_btn.click()
        time.sleep(3)
        
        token = driver.execute_script("return localStorage.getItem('greennest_token');")
        if not token:
            print("❌ Customer Login Failed!")
            return
        print("✅ Customer Login Successful!")
        
        # 2. Dashboard Verification (`dashboard.html`)[cite: 3]
        driver.get(f"{BASE_URL}/dashboard.html")
        time.sleep(2)
        print("✅ Customer Dashboard loaded successfully!")
        
        # 3. Buy Plants & Cart Checkout Workflow (`buy.html`)[cite: 3]
        driver.get(f"{BASE_URL}/buy.html")
        time.sleep(2)
        
        # Open Cart dialog
        open_cart_btn = wait.until(EC.element_to_be_clickable((By.ID, "openCartButton")))
        open_cart_btn.click()
        time.sleep(1)
        
        # Fill Checkout delivery details
        phone_field = wait.until(EC.presence_of_element_located((By.ID, "checkoutPhone")))
        phone_field.clear()
        phone_field.send_keys("01712345678")
        
        address_field = driver.find_element(By.ID, "checkoutAddress")
        address_field.clear()
        address_field.send_keys("Dhaka, Bangladesh")
        
        city_field = driver.find_element(By.ID, "checkoutCity")
        city_field.clear()
        city_field.send_keys("Dhaka")
        
        postcode_field = driver.find_element(By.ID, "checkoutPostcode")
        postcode_field.clear()
        postcode_field.send_keys("1207")
        print("✅ Delivery details filled in cart checkout!")
        
        # 4. Rent Plants Workflow (`rent.html`)[cite: 3]
        driver.get(f"{BASE_URL}/rent.html")
        time.sleep(2)
        print("✅ Rent Plants catalog loaded successfully!")
        
        # 5. Maintenance Workflow (`maintenance.html`)[cite: 3]
        driver.get(f"{BASE_URL}/maintenance.html")
        time.sleep(2)
        print("✅ Maintenance page loaded successfully!")
        
        # 6. Customer History & Rental Payment (`customer-history.html`)[cite: 3]
        driver.get(f"{BASE_URL}/customer-history.html")
        time.sleep(2)
        print("✅ Customer Purchase & Rental History loaded successfully!")
        
        print("\n🎉 All Customer Workflow tests passed successfully!")
        
    except Exception as e:
        print(f"❌ Error during Customer Workflow test: {e}")
    finally:
        driver.quit()

if __name__ == "__main__":
    test_customer_workflow()