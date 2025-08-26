
export const fetchCities = async () => {
    try {
        const response = await fetch(`/api/v1/filters/cities`);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const cities = await response.json();
        return cities;
    } catch (error) {
        console.error('Error fetching cities:', error);
        throw error;
    }
};

export const fetchNeighborhoods = async (city) => {
    try {
        const response = await fetch(`/api/v1/filters/neighborhoods?city=${encodeURIComponent(city)}`);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const neighborhoods = await response.json();
        return neighborhoods;
    } catch (error) {
        console.error('Error fetching neighborhoods:', error);
        throw error;
    }
}; 