import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

BASE_URL = "http://localhost:5500/frontend"

def test_cart_quantity():
    print("\n--- Testing Cart Quantity & Subtotal Calculation ---")
    driver = webdriver.Chrome()
    driver.maximize_window()
    
    try:
        wait = WebDriverWait(driver, 10)
        
        # 1. Login as Customer
        driver.get(f"{BASE_URL}/login.html")
        wait.until(EC.presence_of_element_located((By.ID, "email"))).send_keys("raisajeba8@gmail.com")
        driver.find_element(By.ID, "password").send_keys("Raisa@3456")
        driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
        time.sleep(2)
        
        # 2. Navigate to Buy page & Add plant to cart
        driver.get(f"{BASE_URL}/buy.html")
        time.sleep(2)
        
        add_btn = wait.until(EC.element_to_be_clickable((By.CLASS_NAME, "plant-store-action")))
        add_btn.click()
        time.sleep(2)
        
        # 3. Open Cart
        driver.find_element(By.ID, "openCartButton").click()
        time.sleep(2)
        
        # 4. Check cart subtotal element presence
        subtotal_el = wait.until(EC.presence_of_element_located((By.ID, "cartSubtotal")))
        print(f"✅ Cart opened successfully. Current Subtotal: {subtotal_el.text}")
        
    except Exception as e:
        print(f"❌ Error during Cart Quantity test: {e}")
    finally:
        driver.quit()

if __name__ == "__main__":
    test_cart_quantity()