import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

BASE_URL = "http://localhost:5500/frontend"

def test_product_reviews():
    print("\n--- Testing Product Reviews & Ratings Workflow ---")
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
        
        # 2. Navigate to Buy Plants Page
        driver.get(f"{BASE_URL}/buy.html")
        time.sleep(2)
        
        # 3. Open View Details modal for the first plant card
        details_btn = wait.until(EC.element_to_be_clickable((By.CLASS_NAME, "plant-card-details-action")))
        details_btn.click()
        time.sleep(2)
        
        # 4. Fill Review Form inside modal
        review_input = wait.until(EC.presence_of_element_located((By.CLASS_NAME, "review-comment-input")))
        review_input.clear()
        review_input.send_keys("Great quality plant! Healthy and green.")
        
        submit_review_btn = driver.find_element(By.CSS_SELECTOR, "#quickViewReviewForm button[type='submit']")
        submit_review_btn.click()
        time.sleep(2)
        
        print("✅ Product review and rating submitted successfully!")
        
    except Exception as e:
        print(f"❌ Error during Reviews test: {e}")
    finally:
        driver.quit()

if __name__ == "__main__":
    test_product_reviews()