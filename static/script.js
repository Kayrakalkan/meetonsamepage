// Store flight data globally for modal access
let allFlightData = {};
let currentCurrency = 'EUR';
let destinationType = 'airport'; // 'airport', 'country', or 'everywhere'
let countriesData = [];

document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('searchForm');
    const searchBtn = document.getElementById('searchBtn');
    const btnText = searchBtn.querySelector('.btn-text');
    const btnLoading = searchBtn.querySelector('.btn-loading');
    const resultsContainer = document.getElementById('results');
    const errorContainer = document.getElementById('error');
    
    // Set default dates (today + 7 days to today + 30 days)
    const today = new Date();
    const nextWeek = new Date(today.getTime() + 7 * 24 * 60 * 60 * 1000);
    const nextMonth = new Date(today.getTime() + 30 * 24 * 60 * 60 * 1000);
    
    document.getElementById('dateFrom').value = formatDate(nextWeek);
    document.getElementById('dateTo').value = formatDate(nextMonth);
    
    // Initialize airport search inputs
    initAirportSearch('origin1', 'origin1Code', 'origin1Dropdown');
    initAirportSearch('origin2', 'origin2Code', 'origin2Dropdown');
    initAirportSearch('destination', 'destinationCode', 'destinationDropdown');
    
    // Initialize country search
    loadCountries();
    initCountrySearch();
    
    // Close dropdowns when clicking outside
    document.addEventListener('click', function(e) {
        if (!e.target.closest('.airport-search-container')) {
            document.querySelectorAll('.airport-dropdown').forEach(d => d.style.display = 'none');
        }
    });
    
    form.addEventListener('submit', async function(e) {
        e.preventDefault();
        
        // Get form values
        const origin1 = document.getElementById('origin1Code').value || document.getElementById('origin1').value.toUpperCase();
        const origin2 = document.getElementById('origin2Code').value || document.getElementById('origin2').value.toUpperCase();
        const dateFrom = document.getElementById('dateFrom').value;
        const dateTo = document.getElementById('dateTo').value;
        const tripDays = parseInt(document.getElementById('tripDays').value);
        const currency = document.getElementById('currency').value;
        const directOnly = document.getElementById('directOnly').checked;
        
        currentCurrency = currency;
        
        // Show loading state
        setLoading(true);
        hideError();
        resultsContainer.style.display = 'none';
        
        try {
            if (destinationType === 'everywhere') {
                // Search everywhere - find cheapest destinations worldwide
                const response = await fetch('/api/search/everywhere', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        origins: [origin1, origin2],
                        date_from: dateFrom,
                        date_to: dateTo,
                        trip_days: tripDays,
                        currency: currency,
                        direct_only: directOnly
                    })
                });
                
                const data = await response.json();
                
                if (response.ok) {
                    displayDestinationResults(data.destinations, currency, true);
                } else {
                    showError(data.error || 'Failed to search destinations');
                }
            } else if (destinationType === 'country') {
                // Search by country - find best destinations
                const countryCode = document.getElementById('countryCode').value;
                if (!countryCode) {
                    showError('Please select a country');
                    setLoading(false);
                    return;
                }
                
                const response = await fetch('/api/search/destinations', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        origins: [origin1, origin2],
                        country_code: countryCode,
                        date_from: dateFrom,
                        date_to: dateTo,
                        trip_days: tripDays,
                        currency: currency,
                        direct_only: directOnly
                    })
                });
                
                const data = await response.json();
                
                if (response.ok) {
                    displayDestinationResults(data.destinations, currency);
                } else {
                    showError(data.error || 'Failed to search destinations');
                }
            } else {
                // Search by specific airport
                const destination = document.getElementById('destinationCode').value || document.getElementById('destination').value.toUpperCase();
                
                const response = await fetch('/api/search', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        origins: [origin1, origin2],
                        destination: destination,
                        date_from: dateFrom,
                        date_to: dateTo,
                        trip_days: tripDays,
                        currency: currency,
                        direct_only: directOnly
                    })
                });
                
                const data = await response.json();
                
                if (response.ok) {
                    allFlightData = data;
                    displayResults(data, origin1, origin2, currency);
                } else {
                    showError(data.error || 'Failed to search flights');
                }
            }
        } catch (error) {
            showError('Failed to connect to server. Please try again.');
            console.error(error);
        } finally {
            setLoading(false);
        }
    });
    
    // Close modal on click outside
    document.getElementById('flightModal').addEventListener('click', function(e) {
        if (e.target === this) {
            closeModal();
        }
    });
    
    // Close modal on Escape key
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') {
            closeModal();
        }
    });
    
    function setLoading(loading) {
        searchBtn.disabled = loading;
        btnText.style.display = loading ? 'none' : 'inline';
        btnLoading.style.display = loading ? 'inline' : 'none';
    }
    
    function showError(message) {
        errorContainer.textContent = '❌ ' + message;
        errorContainer.style.display = 'block';
    }
    
    function hideError() {
        errorContainer.style.display = 'none';
    }
});

// Airport search autocomplete
function initAirportSearch(inputId, codeId, dropdownId) {
    const input = document.getElementById(inputId);
    const codeInput = document.getElementById(codeId);
    const dropdown = document.getElementById(dropdownId);
    
    let debounceTimer;
    
    input.addEventListener('input', function() {
        const query = this.value.trim();
        codeInput.value = ''; // Clear selected code when typing
        
        clearTimeout(debounceTimer);
        
        if (query.length < 1) {
            dropdown.style.display = 'none';
            return;
        }
        
        debounceTimer = setTimeout(async () => {
            try {
                const response = await fetch(`/api/airports?q=${encodeURIComponent(query)}`);
                const airports = await response.json();
                
                if (airports.length > 0) {
                    dropdown.innerHTML = airports.map(a => `
                        <div class="airport-option" data-code="${a.code}" data-name="${a.city} (${a.code})">
                            <span class="airport-code">${a.code}</span>
                            <span class="airport-info">
                                <span class="airport-city">${a.city}</span>
                                <span class="airport-country">${a.country}</span>
                            </span>
                        </div>
                    `).join('');
                    dropdown.style.display = 'block';
                    
                    // Add click handlers
                    dropdown.querySelectorAll('.airport-option').forEach(opt => {
                        opt.addEventListener('click', function() {
                            input.value = this.dataset.name;
                            codeInput.value = this.dataset.code;
                            dropdown.style.display = 'none';
                        });
                    });
                } else {
                    dropdown.innerHTML = '<div class="airport-option no-results">No airports found</div>';
                    dropdown.style.display = 'block';
                }
            } catch (error) {
                console.error('Error searching airports:', error);
            }
        }, 200);
    });
    
    input.addEventListener('focus', function() {
        if (this.value.length >= 1 && dropdown.innerHTML) {
            dropdown.style.display = 'block';
        }
    });
}

// Load countries data
async function loadCountries() {
    try {
        const response = await fetch('/api/countries');
        countriesData = await response.json();
    } catch (error) {
        console.error('Error loading countries:', error);
    }
}

// Country search
function initCountrySearch() {
    const input = document.getElementById('countryDestination');
    const codeInput = document.getElementById('countryCode');
    const dropdown = document.getElementById('countryDropdown');
    
    input.addEventListener('input', function() {
        const query = this.value.trim().toLowerCase();
        codeInput.value = '';
        
        if (query.length < 1) {
            dropdown.style.display = 'none';
            return;
        }
        
        const filtered = countriesData.filter(c => 
            c.name.toLowerCase().includes(query) || 
            c.code.toLowerCase().includes(query)
        );
        
        if (filtered.length > 0) {
            dropdown.innerHTML = filtered.slice(0, 15).map(c => `
                <div class="airport-option" data-code="${c.code}" data-name="${c.name}">
                    <span class="airport-code">${c.code}</span>
                    <span class="airport-info">
                        <span class="airport-city">${c.name}</span>
                    </span>
                </div>
            `).join('');
            dropdown.style.display = 'block';
            
            dropdown.querySelectorAll('.airport-option').forEach(opt => {
                opt.addEventListener('click', function() {
                    input.value = this.dataset.name;
                    codeInput.value = this.dataset.code;
                    dropdown.style.display = 'none';
                });
            });
        } else {
            dropdown.innerHTML = '<div class="airport-option no-results">No countries found</div>';
            dropdown.style.display = 'block';
        }
    });
    
    input.addEventListener('focus', function() {
        if (this.value.length >= 1 && dropdown.innerHTML) {
            dropdown.style.display = 'block';
        }
    });
}

// Toggle destination type
function setDestinationType(type) {
    destinationType = type;
    
    document.querySelectorAll('.toggle-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.type === type);
    });
    
    document.getElementById('airportDestGroup').style.display = type === 'airport' ? 'block' : 'none';
    document.getElementById('countryDestGroup').style.display = type === 'country' ? 'block' : 'none';
    document.getElementById('everywhereDestGroup').style.display = type === 'everywhere' ? 'block' : 'none';
    
    // Update required attributes
    document.getElementById('destination').required = type === 'airport';
    document.getElementById('countryDestination').required = type === 'country';
}

function formatDate(date) {
    return date.toISOString().split('T')[0];
}

function formatPrice(price, currency) {
    const symbols = {
        'EUR': '€',
        'USD': '$',
        'GBP': '£',
        'TRY': '₺',
        'CHF': 'CHF '
    };
    return (symbols[currency] || currency + ' ') + price.toFixed(0);
}

function formatDisplayDate(dateStr) {
    if (!dateStr) return '';
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' });
}

// Display destination search results (for country and everywhere search)
// Now uses the same format as airport search
function displayDestinationResults(destinations, currency, isEverywhere = false) {
    const resultsContainer = document.getElementById('results');
    
    if (!destinations || destinations.length === 0) {
        document.getElementById('bestMatch').style.display = 'none';
        document.querySelector('.results-grid').style.display = 'none';
        document.getElementById('destinationResults').style.display = 'block';
        document.querySelector('#destinationResults .destinations-list').innerHTML = 
            '<div class="no-flights">No destinations found with flights from both origins</div>';
        resultsContainer.style.display = 'block';
        return;
    }
    
    // Hide the old destination results view
    document.getElementById('destinationResults').style.display = 'none';
    
    // Get the best destination (cheapest combined)
    const bestDest = destinations[0];
    
    // Prepare data in the same format as airport search
    const origin1 = bestDest.flights[0]?.departure_airport || 'Origin 1';
    const origin2 = bestDest.flights[1]?.departure_airport || 'Origin 2';
    
    // Create flight lists for each origin from all destinations
    const flights1 = destinations.map(d => d.flights[0]).filter(f => f);
    const flights2 = destinations.map(d => d.flights[1]).filter(f => f);
    
    // Create best matches array (each destination is a "match")
    const bestMatches = destinations.slice(0, 5).map(d => ({
        departure_date: d.departure_date,
        return_date: d.return_date,
        combined_price: d.combined_price,
        currency: d.currency,
        destination: d.destination,
        flights: d.flights
    }));
    
    // Update titles to show destination info
    const title1 = document.querySelector('#results1 h3');
    const title2 = document.querySelector('#results2 h3');
    title1.textContent = `✈️ From ${origin1}`;
    title2.textContent = `✈️ From ${origin2}`;
    
    // Display flights in the grid
    displayFlightsForDestSearch('results1', flights1, origin1, currency);
    displayFlightsForDestSearch('results2', flights2, origin2, currency);
    
    // Display best matches
    displayBestMatchesForDestSearch(bestMatches, currency, isEverywhere);
    
    // Show the results grid
    document.querySelector('.results-grid').style.display = 'grid';
    document.getElementById('bestMatch').style.display = 'block';
    
    resultsContainer.style.display = 'block';
    resultsContainer.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

// Display flights for destination/everywhere search
function displayFlightsForDestSearch(containerId, flights, origin, currency) {
    const container = document.querySelector(`#${containerId} .flights-list`);
    
    if (flights.length === 0) {
        container.innerHTML = '<div class="no-flights">No flights found</div>';
        return;
    }
    
    container.innerHTML = flights.map((flight, index) => `
        <div class="flight-card" data-flight-id="${origin}-${index}">
            <div class="flight-header">
                <span class="route">${flight.departure_airport} → ${flight.arrival_airport}</span>
                <span class="price">${formatPrice(flight.price, currency)}</span>
            </div>
            <div class="flight-details">
                <span class="detail">🛫 ${formatDisplayDate(flight.departure_date)}</span>
                <span class="detail">🛬 ${formatDisplayDate(flight.return_date)}</span>
                ${flight.airline ? `<span class="detail">✈️ ${flight.airline}</span>` : ''}
                <span class="detail">${flight.stops === 0 ? '✅ Direct' : '🔄 ' + flight.stops + ' stop(s)'}</span>
            </div>
            <div class="flight-actions">
                <button class="details-btn" onclick='showFlightDetails(${JSON.stringify(flight).replace(/'/g, "&#39;")})'>
                    📋 Details
                </button>
                ${flight.link ? `<a href="${flight.link}" target="_blank" class="book-link">Book Now →</a>` : ''}
            </div>
        </div>
    `).join('');
}

// Display best matches for destination/everywhere search
function displayBestMatchesForDestSearch(matches, currency, isEverywhere) {
    const bestMatchContainer = document.getElementById('bestMatch');
    const matchContent = bestMatchContainer.querySelector('.match-content');
    const bestMatch = matches[0];
    
    const headerTitle = isEverywhere 
        ? `🌎 Best Destination: ${bestMatch.destination}` 
        : `🌍 Best Destination: ${bestMatch.destination}`;
    
    matchContent.innerHTML = `
        <div class="best-match-header">
            <h4>${headerTitle}</h4>
            <div class="match-dates">📅 ${formatDisplayDate(bestMatch.departure_date)} → ${formatDisplayDate(bestMatch.return_date)}</div>
            <div class="combined-price">Combined Total: ${formatPrice(bestMatch.combined_price, currency)}</div>
        </div>
        <div class="match-flights">
            ${bestMatch.flights.map(f => `
                <div class="match-flight">
                    <div class="airport">${f.departure_airport} → ${f.arrival_airport}</div>
                    <div class="price">${formatPrice(f.price, currency)}</div>
                    <div class="date">🛫 ${formatDisplayDate(f.departure_date)}</div>
                    <div class="date">🛬 ${formatDisplayDate(f.return_date)}</div>
                    ${f.airline ? `<div class="airline">✈️ ${f.airline}</div>` : ''}
                    <div class="stops">${f.stops === 0 ? '✅ Direct' : '🔄 ' + f.stops + ' stop(s)'}</div>
                    <button class="book-link" style="margin-top: 10px; border: none; cursor: pointer;" onclick='showFlightDetails(${JSON.stringify(f).replace(/'/g, "&#39;")})'>
                        📋 Details
                    </button>
                    ${f.link ? `<a href="${f.link}" target="_blank" class="book-link">Book →</a>` : ''}
                </div>
            `).join('')}
        </div>
        ${matches.length > 1 ? `
            <div class="other-matches">
                <h5>Other ${isEverywhere ? 'Cheap' : 'Good'} Destinations:</h5>
                ${matches.slice(1, 5).map(m => `
                    <div class="other-match">
                        <span class="other-dest">${m.destination}</span>
                        <span class="other-dates">${formatDisplayDate(m.departure_date)} → ${formatDisplayDate(m.return_date)}</span>
                        <span class="other-price">${formatPrice(m.combined_price, currency)}</span>
                    </div>
                `).join('')}
            </div>
        ` : ''}
    `;
    
    bestMatchContainer.style.display = 'block';
}

function displayResults(data, origin1, origin2, currency) {
    const resultsContainer = document.getElementById('results');
    const results1 = data.results[origin1] || [];
    const results2 = data.results[origin2] || [];
    
    // Hide destination results, show flight results
    document.getElementById('destinationResults').style.display = 'none';
    document.querySelector('.results-grid').style.display = 'grid';
    
    // Display individual results
    displayFlights('results1', results1, origin1, currency);
    displayFlights('results2', results2, origin2, currency);
    
    // Display best matches from backend
    displayBestMatches(data.best_matches, currency);
    
    resultsContainer.style.display = 'block';
    resultsContainer.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function displayFlights(containerId, flights, origin, currency) {
    const container = document.querySelector(`#${containerId} .flights-list`);
    const title = document.querySelector(`#${containerId} h3`);
    
    title.textContent = `✈️ From ${origin}`;
    
    if (flights.length === 0) {
        container.innerHTML = '<div class="no-flights">No flights found</div>';
        return;
    }
    
    container.innerHTML = flights.map((flight, index) => `
        <div class="flight-card" data-flight-id="${origin}-${index}">
            <div class="flight-header">
                <span class="route">${flight.departure_airport} → ${flight.arrival_airport}</span>
                <span class="price">${formatPrice(flight.price, currency)}</span>
            </div>
            <div class="flight-details">
                <span class="detail">🛫 ${formatDisplayDate(flight.departure_date)}</span>
                <span class="detail">🛬 ${formatDisplayDate(flight.return_date)}</span>
                ${flight.airline ? `<span class="detail">✈️ ${flight.airline}</span>` : ''}
                <span class="detail">${flight.stops === 0 ? '✅ Direct' : '🔄 ' + flight.stops + ' stop(s)'}</span>
            </div>
            <div class="flight-actions">
                <button class="details-btn" onclick='showFlightDetails(${JSON.stringify(flight).replace(/'/g, "&#39;")})'>
                    📋 Details
                </button>
                ${flight.link ? `<a href="${flight.link}" target="_blank" class="book-link">Book Now →</a>` : ''}
            </div>
        </div>
    `).join('');
}

function formatDate(date) {
    return date.toISOString().split('T')[0];
}

function formatPrice(price, currency) {
    const symbols = {
        'EUR': '€',
        'USD': '$',
        'GBP': '£',
        'TRY': '₺',
        'CHF': 'CHF '
    };
    return (symbols[currency] || currency + ' ') + price.toFixed(0);
}

function formatDisplayDate(dateStr) {
    if (!dateStr) return '';
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' });
}

function displayResults(data, origin1, origin2, currency) {
    const resultsContainer = document.getElementById('results');
    const results1 = data.results[origin1] || [];
    const results2 = data.results[origin2] || [];
    
    // Display individual results
    displayFlights('results1', results1, origin1, currency);
    displayFlights('results2', results2, origin2, currency);
    
    // Display best matches from backend
    displayBestMatches(data.best_matches, currency);
    
    resultsContainer.style.display = 'block';
    resultsContainer.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function displayFlights(containerId, flights, origin, currency) {
    const container = document.querySelector(`#${containerId} .flights-list`);
    const title = document.querySelector(`#${containerId} h3`);
    
    title.textContent = `✈️ From ${origin}`;
    
    if (flights.length === 0) {
        container.innerHTML = '<div class="no-flights">No flights found</div>';
        return;
    }
    
    container.innerHTML = flights.map((flight, index) => `
        <div class="flight-card" data-flight-id="${origin}-${index}">
            <div class="flight-header">
                <span class="route">${flight.departure_airport} → ${flight.arrival_airport}</span>
                <span class="price">${formatPrice(flight.price, currency)}</span>
            </div>
            <div class="flight-details">
                <span class="detail">� ${formatDisplayDate(flight.departure_date)}</span>
                <span class="detail">🛬 ${formatDisplayDate(flight.return_date)}</span>
                ${flight.airline ? `<span class="detail">✈️ ${flight.airline}</span>` : ''}
                <span class="detail">${flight.stops === 0 ? '✅ Direct' : '🔄 ' + flight.stops + ' stop(s)'}</span>
            </div>
            <div class="flight-actions">
                <button class="details-btn" onclick='showFlightDetails(${JSON.stringify(flight).replace(/'/g, "&#39;")})'>
                    📋 Details
                </button>
                ${flight.link ? `<a href="${flight.link}" target="_blank" class="book-link">Book Now →</a>` : ''}
            </div>
        </div>
    `).join('');
}

function displayBestMatches(matches, currency) {
    const bestMatchContainer = document.getElementById('bestMatch');
    
    if (!matches || matches.length === 0) {
        bestMatchContainer.style.display = 'none';
        return;
    }
    
    const matchContent = bestMatchContainer.querySelector('.match-content');
    const bestMatch = matches[0]; // Top match
    
    matchContent.innerHTML = `
        <div class="best-match-header">
            <h4>🎯 Best Matching Dates: ${formatDisplayDate(bestMatch.departure_date)} → ${formatDisplayDate(bestMatch.return_date)}</h4>
            <div class="combined-price">Combined Total: ${formatPrice(bestMatch.combined_price, currency)}</div>
        </div>
        <div class="match-flights">
            ${bestMatch.flights.map(f => `
                <div class="match-flight">
                    <div class="airport">${f.departure_airport} → ${f.arrival_airport}</div>
                    <div class="price">${formatPrice(f.price, currency)}</div>
                    <div class="date">� ${formatDisplayDate(f.departure_date)}</div>
                    <div class="date">🛬 ${formatDisplayDate(f.return_date)}</div>
                    ${f.airline ? `<div class="airline">✈️ ${f.airline}</div>` : ''}
                    <div class="stops">${f.stops === 0 ? '✅ Direct' : '🔄 ' + f.stops + ' stop(s)'}</div>
                    <button class="book-link" style="margin-top: 10px; border: none; cursor: pointer;" onclick='showFlightDetails(${JSON.stringify(f).replace(/'/g, "&#39;")})'>
                        📋 Details
                    </button>
                    ${f.link ? `<a href="${f.link}" target="_blank" class="book-link">Book →</a>` : ''}
                </div>
            `).join('')}
        </div>
        ${matches.length > 1 ? `
            <div class="other-matches">
                <h5>Other Good Options:</h5>
                ${matches.slice(1, 5).map(m => `
                    <div class="other-match">
                        <span class="other-dates">${formatDisplayDate(m.departure_date)} → ${formatDisplayDate(m.return_date)}</span>
                        <span class="other-price">${formatPrice(m.combined_price, currency)}</span>
                    </div>
                `).join('')}
            </div>
        ` : ''}
    `;
    
    bestMatchContainer.style.display = 'block';
}

function showFlightDetails(flight) {
    const modal = document.getElementById('flightModal');
    const modalBody = document.getElementById('modalBody');
    
    modalBody.innerHTML = `
        <div class="flight-segment">
            <h4>🛫 Outbound Flight</h4>
            <div class="segment-route">
                <div class="segment-airport">
                    <div class="code">${flight.departure_airport}</div>
                    <div class="time">${flight.departure_time || '--:--'}</div>
                    <div class="date">${formatDisplayDate(flight.departure_date)}</div>
                </div>
                <div class="segment-arrow">
                    <div class="duration">${flight.duration || 'N/A'}</div>
                    <div class="plane-icon">✈️</div>
                </div>
                <div class="segment-airport">
                    <div class="code">${flight.arrival_airport}</div>
                    <div class="time">${flight.arrival_time || '--:--'}</div>
                    <div class="date">${formatDisplayDate(flight.departure_date)}</div>
                </div>
            </div>
            <div class="segment-info">
                ${flight.airline ? `<span>✈️ ${flight.airline}</span>` : ''}
                <span>${flight.stops === 0 ? '✅ Direct flight' : '🔄 ' + flight.stops + ' stop(s)'}</span>
            </div>
        </div>
        
        ${flight.return_date ? `
        <div class="flight-segment">
            <h4>🛬 Return Flight</h4>
            <div class="segment-route">
                <div class="segment-airport">
                    <div class="code">${flight.arrival_airport}</div>
                    <div class="time">${flight.return_departure_time || '--:--'}</div>
                    <div class="date">${formatDisplayDate(flight.return_date)}</div>
                </div>
                <div class="segment-arrow">
                    <div class="duration">${flight.return_duration || flight.duration || 'N/A'}</div>
                    <div class="plane-icon">✈️</div>
                </div>
                <div class="segment-airport">
                    <div class="code">${flight.departure_airport}</div>
                    <div class="time">${flight.return_arrival_time || '--:--'}</div>
                    <div class="date">${formatDisplayDate(flight.return_date)}</div>
                </div>
            </div>
            <div class="segment-info">
                ${flight.airline ? `<span>✈️ ${flight.airline}</span>` : ''}
                <span>${flight.return_stops !== undefined ? (flight.return_stops === 0 ? '✅ Direct flight' : '🔄 ' + flight.return_stops + ' stop(s)') : ''}</span>
            </div>
        </div>
        ` : ''}
        
        <div class="flight-segment" style="background: linear-gradient(135deg, #667eea15, #764ba215);">
            <h4>💰 Price Summary</h4>
            <div style="font-size: 1.5rem; font-weight: 700; color: #667eea; margin-top: 10px;">
                ${formatPrice(flight.price, currentCurrency)}
            </div>
            <div style="font-size: 0.9rem; color: #666; margin-top: 5px;">
                Round trip per person
            </div>
        </div>
        
        ${flight.link ? `
            <a href="${flight.link}" target="_blank" class="modal-book-btn">
                🎫 Book This Flight
            </a>
        ` : ''}
    `;
    
    modal.style.display = 'flex';
    document.body.style.overflow = 'hidden';
}

function closeModal() {
    const modal = document.getElementById('flightModal');
    modal.style.display = 'none';
    document.body.style.overflow = 'auto';
}
