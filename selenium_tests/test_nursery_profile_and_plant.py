import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

BASE_URL = "http://localhost:5500/frontend"

def test_nursery_profile_and_plant_flow():
    print("\n--- Testing Nursery Profile Update & Add Plant Flow ---")
    driver = webdriver.Chrome()
    driver.maximize_window()
    
    try:
        wait = WebDriverWait(driver, 10)
        
        # 1. Login as Nursery Owner
        driver.get(f"{BASE_URL}/login.html")
        wait.until(EC.presence_of_element_located((By.ID, "email"))).send_keys("23201196@uap-bd.edu")
        driver.find_element(By.ID, "password").send_keys("Sraboni@3456")
        driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
        time.sleep(2)
        
        # 2. Navigate to Nursery Profile Settings (`nursery-profile.html`)
        driver.get(f"{BASE_URL}/nursery-profile.html")
        time.sleep(2)
        
        # Update Nursery Name / Contact
        nursery_name_field = wait.until(EC.presence_of_element_located((By.ID, "nurseryName")))
        nursery_name_field.clear()
        nursery_name_field.send_keys("Green Forest Nursery & Co.")
        
        city_field = driver.find_element(By.ID, "city")
        city_field.clear()
        city_field.send_keys("Dhaka")
        
        # Save Profile
        profile_save_btn = driver.find_element(By.CSS_SELECTOR, "#profileForm button[type='submit']")
        profile_save_btn.click()
        time.sleep(2)
        print("✅ Nursery Profile updated successfully!")
        
        # 3. Navigate to Add Plant Page (`add-plant.html`)
        driver.get(f"{BASE_URL}/add-plant.html")
        time.sleep(2)
        
        # Fill Add Plant form
        plant_name_field = wait.until(EC.presence_of_element_located((By.ID, "plantName")))
        plant_name_field.clear()
        plant_name_field.send_keys("Fiddle Leaf Fig")
        
        driver.find_element(By.ID, "buyPrice").send_keys("1500")
        driver.find_element(By.ID, "rentPrice").send_keys("250")
        driver.find_element(By.ID, "quantity").send_keys("10")
        driver.find_element(By.ID, "description").send_keys("Healthy indoor ornamental plant with large glossy leaves.")
        driver.find_element(By.ID, "careInstructions").send_keys("Indirect sunlight, water once a week.")
        
        # Submit Upload Plant
        upload_btn = driver.find_element(By.CSS_SELECTOR, "#addPlantForm button[type='submit']")
        upload_btn.click()
        time.sleep(2)
        
        print("✅ New Plant successfully uploaded to the nursery marketplace!")
        
    except Exception as e:
        print(f"❌ Error during Nursery Profile & Plant Upload test: {e}")
    finally:
        driver.quit()

if __name__ == "__main__":
    test_nursery_profile_and_plant_flow()