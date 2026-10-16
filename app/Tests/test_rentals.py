import pytest
from fastapi import status

# Test Browse Plants
def test_browse_available_plants(client, test_plant):
    response = client.get("/api/rentals/plants")
    assert response.status_code == status.HTTP_200_OK
    assert isinstance(response.json(), list)

# Test View Plant Details
def test_get_plant_details_success(client, test_plant):
    response = client.get(f"/api/rentals/plants/{test_plant.id}")
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["id"] == test_plant.id

def test_get_plant_details_not_found(client):
    response = client.get("/api/rentals/plants/9999")
    assert response.status_code == status.HTTP_404_NOT_FOUND

# Test Submit Rental Request without Auth
def test_submit_rental_unauthenticated(client, test_plant):
    payload = {
        "plant_id": test_plant.id,
        "quantity": 2,
        "rental_start_date": "2026-11-01",
        "rental_end_date": "2026-11-05",
        "rental_price_per_day": 15.0
    }
    response = client.post("/api/rentals/requests", json=payload)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED

# Test Submit Rental Request Validation Failure (Invalid Date)
def test_submit_rental_invalid_date(authorized_client, test_plant):
    payload = {
        "plant_id": test_plant.id,
        "quantity": 1,
        "rental_start_date": "2026-11-05",
        "rental_end_date": "2026-11-01",
        "rental_price_per_day": 10.0
    }
    response = authorized_client.post("/api/rentals/requests", json=payload)
    assert response.status_code == status.HTTP_400_BAD_REQUEST