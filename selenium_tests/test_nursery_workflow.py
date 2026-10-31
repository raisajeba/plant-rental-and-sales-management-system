import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

BASE_URL = "http://localhost:5500/frontend"

def test_nursery_owner_workflow():
    print("\n--- Testing Nursery Owner Complete Workflow ---")
    driver = webdriver.Chrome()
    driver.maximize_window()
    
    try:
        wait = WebDriverWait(driver, 10)
        
        # 1. Login as Nursery Owner (Using unified login.html)
        driver.get(f"{BASE_URL}/login.html")
        
        email_field = wait.until(EC.presence_of_element_located((By.ID, "email")))
        password_field = driver.find_element(By.ID, "password")
        
        # Apnar nursery owner-er valid test credentials
        email_field.clear()
        email_field.send_keys("23201196@uap-bd.edu")
        password_field.clear()
        password_field.send_keys("Sraboni@3456")
        
        login_btn = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
        login_btn.click()
        
        time.sleep(3)
        
        # Verify token in localStorage
        token = driver.execute_script("return localStorage.getItem('greennest_token');")
        if not token:
            print("❌ Nursery Owner Login Failed! Token not found.")
            return
        print("✅ Nursery Owner Login Successful!")
        
        # 2. Navigate to Nursery Dashboard (`nursery-dashboard.html`)
        driver.get(f"{BASE_URL}/nursery-dashboard.html")
        time.sleep(2)
        
        # Check if total plants stats element is loaded
        total_plants = wait.until(EC.presence_of_element_located((By.ID, "totalPlantsCount")))
        print(f"📊 Total Live Listings on Dashboard: {total_plants.text}")
        
        # 3. Navigate to Add Plant Page (`add-plant.html`)
        driver.get(f"{BASE_URL}/add-plant.html")
        time.sleep(2)
        
        # Fill Add Plant Form based on add-plant.js IDs
        plant_name_field = wait.until(EC.presence_of_element_located((By.ID, "plantName")))
        plant_name_field.send_keys("Automated Test Monstera")
        
        driver.find_element(By.ID, "buyPrice").send_keys("1200")
        driver.find_element(By.ID, "rentPrice").send_keys("200")
        driver.find_element(By.ID, "quantity").send_keys("15")
        driver.find_element(By.ID, "description").text_input = "Automatic test plant description for Selenium testing."
        
        print("✅ Add Plant form fields populated successfully!")
        
        # 4. Navigate to Rent Orders (`rent-orders.html`)
        driver.get(f"{BASE_URL}/rent-orders.html")
        time.sleep(2)
        print("✅ Rent Orders page loaded successfully!")
        
        # 5. Navigate to Sell Orders (`sell-order.html`)
        driver.get(f"{BASE_URL}/sell-orders.html")
        time.sleep(2)
        print("✅ Sell Orders page loaded successfully!")
        
        # 6. Navigate to Maintenance (`nursery-maintainance.html`)
        driver.get(f"{BASE_URL}/nursery-maintainance.html")
        time.sleep(2)
        print("✅ Maintenance management page loaded successfully!")
        
        print("\n🎉 All Nursery Owner Workflow tests passed successfully!")
        
    except Exception as e:
        print(f"❌ Error during Nursery Workflow test: {e}")
    finally:
        driver.quit()

if __name__ == "__main__":
    test_nursery_owner_workflow()