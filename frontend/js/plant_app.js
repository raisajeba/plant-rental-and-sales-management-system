// Function to display plants in UI and disable buttons for out-of-stock items
async function renderPlantListings() {
    const response = await fetch('/api/plants/');
    const plants = await response.json();
    const container = document.getElementById('plant-container');
    
    if (!container) return;
    container.innerHTML = '';

    plants.forEach(plant => {
        const isOutOfStock = plant.quantity === 0 || plant.availability_status === 'Out of Stock';
        
        const cardHTML = `
            <div class="plant-card ${isOutOfStock ? 'disabled-card' : ''}">
                <h3>${plant.name}</h3>
                <p>Available Quantity: <strong>${plant.quantity}</strong></p>
                <p>Status: 
                    <span class="${isOutOfStock ? 'status-out-of-stock' : 'status-available'}">
                        ${plant.availability_status}
                    </span>
                </p>
                <div class="action-buttons">
                    <button ${isOutOfStock ? 'disabled' : ''} onclick="buyPlant(${plant.id})">
                        ${isOutOfStock ? 'Out of Stock' : 'Buy'}
                    </button>
                    <button ${isOutOfStock ? 'disabled' : ''} onclick="rentPlant(${plant.id})">
                        ${isOutOfStock ? 'Out of Stock' : 'Rent'}
                    </button>
                </div>
            </div>
        `;
        container.innerHTML += cardHTML;
    });
}