import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

BASE_URL = "http://localhost:5500/frontend"

def test_guest_landing_flow():
    print("\n--- Testing Guest Landing Page & Contact Us Flow ---")
    driver = webdriver.Chrome()
    driver.maximize_window()
    
    try:
        wait = WebDriverWait(driver, 10)
        
        # 1. Visit Public Landing Page (Home view)
        driver.get(f"{BASE_URL}/landing_index.html")
        time.sleep(2)
        print("✅ Guest loaded landing page successfully!")
        
        # 2. Click Navigation Link to open Contact view
        contact_nav = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "a[data-view-target='contact']")))
        contact_nav.click()
        time.sleep(2)
        print("✅ Guest navigated to Contact section!")
        
        # 3. Fill out Contact Us Form using exact HTML IDs
        name_input = wait.until(EC.presence_of_element_located((By.ID, "landingContactName")))
        email_input = driver.find_element(By.ID, "landingContactEmail")
        subject_input = driver.find_element(By.ID, "landingContactSubject")
        message_input = driver.find_element(By.ID, "landingContactMessage")
        
        name_input.send_keys("Visitor User")
        email_input.send_keys("visitor@example.com")
        subject_input.send_keys("Plant Inquiry")
        message_input.send_keys("Hello Green Forest team, I want to inquire about long-term office plant rentals.")
        
        # Submit the contact form
        contact_form = driver.find_element(By.ID, "landingContactForm")
        contact_form.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
        time.sleep(2)
        
        print("✅ Contact Us form submitted successfully by guest!")
        
    except Exception as e:
        print(f"❌ Error during Guest Landing & Contact test: {e}")
    finally:
        driver.quit()

if __name__ == "__main__":
    test_guest_landing_flow()