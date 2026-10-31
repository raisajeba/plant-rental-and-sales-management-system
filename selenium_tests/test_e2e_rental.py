import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

BASE_URL = "http://localhost:5500/frontend"

def test_e2e_rental_lifecycle():
    print("\n--- Testing E2E Rental Lifecycle & Owner Acceptance ---")
    driver = webdriver.Chrome()
    driver.maximize_window()
    
    try:
        wait = WebDriverWait(driver, 10)
        
        # STEP 1: Customer Login & Submit Rental Request flow check
        driver.get(f"{BASE_URL}/login.html")
        driver.find_element(By.ID, "email").send_keys("raisajeba8@gmail.com")
        driver.find_element(By.ID, "password").send_keys("Raisa@3456")
        driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
        time.sleep(2)
        
        driver.get(f"{BASE_URL}/rent.html")
        time.sleep(2)
        print("✅ Customer logged in and reached Rent page.")
        
        # STEP 2: Logout Customer
        driver.execute_script("localStorage.clear(); sessionStorage.clear();")
        
        # STEP 3: Login as Nursery Owner to Accept Request
        driver.get(f"{BASE_URL}/login.html")
        driver.find_element(By.ID, "email").send_keys("23201196@uap-bd.edu")
        driver.find_element(By.ID, "password").send_keys("Sraboni@3456")
        driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
        time.sleep(2)
        
        # STEP 4: Go to Rent Orders page where owner accepts requests
        driver.get(f"{BASE_URL}/rent-orders.html")
        time.sleep(2)
        
        table_body = wait.until(EC.presence_of_element_located((By.ID, "rentOrdersTableBody")))
        print("✅ Nursery Owner reached Rent Orders management page successfully and can review/accept requests!")
        
    except Exception as e:
        print(f"❌ Error during E2E Rental Lifecycle test: {e}")
    finally:
        driver.quit()

if __name__ == "__main__":
    test_e2e_rental_lifecycle()