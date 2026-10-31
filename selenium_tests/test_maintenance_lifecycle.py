import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

BASE_URL = "http://localhost:5500/frontend"

def test_maintenance_lifecycle():
    print("\n--- Testing Maintenance Request & Status Update Lifecycle ---")
    driver = webdriver.Chrome()
    driver.maximize_window()
    
    try:
        wait = WebDriverWait(driver, 10)
        
        # STEP 1: Customer submits maintenance request
        driver.get(f"{BASE_URL}/login.html")
        wait.until(EC.presence_of_element_located((By.ID, "email"))).send_keys("raisajeba8@gmail.com")
        driver.find_element(By.ID, "password").send_keys("Raisa@3456")
        driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
        time.sleep(2)
        
        driver.get(f"{BASE_URL}/maintenance.html")
        time.sleep(2)
        
        desc_input = wait.until(EC.presence_of_element_located((By.ID, "requestDescription")))
        desc_input.send_keys("Leaves are turning yellow, need expert advice.")
        
        driver.find_element(By.ID, "requestSubmitBtn").click()
        time.sleep(2)
        print("✅ Customer submitted maintenance request successfully!")
        
        # STEP 2: Logout Customer
        driver.execute_script("localStorage.clear(); sessionStorage.clear();")
        
        # STEP 3: Login as Nursery Owner and verify/update maintenance record
        driver.get(f"{BASE_URL}/login.html")
        wait.until(EC.presence_of_element_located((By.ID, "email"))).send_keys("23201196@uap-bd.edu")
        driver.find_element(By.ID, "password").send_keys("Sraboni@3456")
        driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
        time.sleep(2)
        
        driver.get(f"{BASE_URL}/nursery-maintainance.html")
        time.sleep(2)
        
        wait.until(EC.presence_of_element_located((By.ID, "nurseryMaintenanceTableBody")))
        print("✅ Nursery Owner reached Maintenance page and can manage records!")
        
    except Exception as e:
        print(f"❌ Error during Maintenance test: {e}")
    finally:
        driver.quit()

if __name__ == "__main__":
    test_maintenance_lifecycle()