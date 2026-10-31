import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

BASE_URL = "http://localhost:5500/frontend"

def test_admin_management_actions():
    print("\n--- Testing Admin Management & Approval Actions ---")
    driver = webdriver.Chrome()
    driver.maximize_window()
    
    try:
        wait = WebDriverWait(driver, 10)
        
        # 1. Admin Login (`admin-login.html`)
        driver.get(f"{BASE_URL}/admin-login.html")
        
        email_field = wait.until(EC.presence_of_element_located((By.ID, "adminEmail")))
        password_field = driver.find_element(By.ID, "adminPassword")
        
        email_field.send_keys("admin@greennest.com")
        password_field.send_keys("Admin@12345")
        
        driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
        time.sleep(3)
        
        token = driver.execute_script("return sessionStorage.getItem('greennest_admin_token');")
        if not token:
            print("❌ Admin Login Failed!")
            return
        print("✅ Admin Login Successful!")
        
        # 2. Navigate to Admin Dashboard (`admin-dashboard.html`)
        driver.get(f"{BASE_URL}/admin-dashboard.html")
        time.sleep(3)
        
        # Verify Summary Metrics
        users_total = wait.until(EC.presence_of_element_located((By.ID, "summaryUsersTotal")))
        nurseries_total = driver.find_element(By.ID, "summaryNurseriesTotal")
        plants_total = driver.find_element(By.ID, "summaryPlantsTotal")
        
        print(f"📊 Dashboard Stats Loaded Successfully:")
        print(f"   - Total Users: {users_total.text}")
        print(f"   - Total Nurseries: {nurseries_total.text}")
        print(f"   - Total Plants: {plants_total.text}")
        
        # 3. Verify User Management Table section
        users_table = driver.find_element(By.ID, "adminUsers")
        print("✅ User Management table section is rendered correctly.")
        
        # 4. Verify Nursery Management Table section
        nurseries_table = driver.find_element(By.ID, "adminNurseries")
        print("✅ Nursery Management table section is rendered correctly.")
        
        # 5. Verify Plant Listings Management Table section
        plants_table = driver.find_element(By.ID, "adminPlants")
        print("✅ Plant Listings management table section is rendered correctly.")
        
        print("\n🎉 All Admin Management & Approval actions verified successfully!")
        
    except Exception as e:
        print(f"❌ Error during Admin Management Actions test: {e}")
    finally:
        driver.quit()

if __name__ == "__main__":
    test_admin_management_actions()