// K6 Performance Test for LishFind API
// Tests critical API endpoints under various load conditions

import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate, Trend } from 'k6/metrics';

// Custom metrics
export let errorRate = new Rate('errors');
export let customTrend = new Trend('custom_response_time');

// Test configuration
export let options = {
  stages: [
    // Warm-up
    { duration: '30s', target: 5 },
    // Ramp up to moderate load
    { duration: '1m', target: 20 },
    // Stay at moderate load
    { duration: '2m', target: 20 },
    // Ramp up to high load
    { duration: '1m', target: 50 },
    // Stay at high load
    { duration: '2m', target: 50 },
    // Ramp down
    { duration: '30s', target: 0 },
  ],
  thresholds: {
    // API response time should be under 500ms for 95% of requests
    http_req_duration: ['p(95)<500'],
    // Error rate should be less than 1%
    errors: ['rate<0.01'],
    // Custom response time threshold
    custom_response_time: ['p(95)<300'],
  },
};

// Test configuration
const BASE_URL = __ENV.BASE_URL || 'http://localhost:8001';
const API_VERSION = '/api/v1';

// Test data
const searchQueries = [
  'pizza restaurant near me',
  'coffee shop downtown',
  'gas station',
  'pharmacy open 24 hours',
  'dentist appointment',
  'hair salon',
  'auto repair shop',
  'grocery store',
  'hotel booking',
  'gym membership'
];

const businessTypes = [
  'restaurant',
  'retail',
  'service',
  'healthcare',
  'automotive'
];

// Helper function to get random item from array
function getRandomItem(arr) {
  return arr[Math.floor(Math.random() * arr.length)];
}

// Setup function - runs once before all tests
export function setup() {
  console.log(`Starting performance test against: ${BASE_URL}`);
  
  // Test basic connectivity
  let response = http.get(`${BASE_URL}/health`);
  if (response.status !== 200) {
    throw new Error(`API not accessible: ${response.status}`);
  }
  
  console.log('API connectivity confirmed');
  return { baseUrl: BASE_URL };
}

// Main test function - runs for each virtual user
export default function(data) {
  let responses = [];
  
  // Test 1: Health Check (lightweight)
  let healthResponse = http.get(`${data.baseUrl}/health`);
  
  check(healthResponse, {
    'Health check status is 200': (r) => r.status === 200,
    'Health check response time < 100ms': (r) => r.timings.duration < 100,
  });
  
  errorRate.add(healthResponse.status !== 200);
  customTrend.add(healthResponse.timings.duration);
  responses.push(healthResponse);
  
  // Test 2: API Health Check
  let apiHealthResponse = http.get(`${data.baseUrl}${API_VERSION}/health`);
  
  check(apiHealthResponse, {
    'API health check status is 200': (r) => r.status === 200,
    'API health response contains status': (r) => r.json('status') !== undefined,
  });
  
  errorRate.add(apiHealthResponse.status !== 200);
  responses.push(apiHealthResponse);
  
  // Test 3: Search API (most critical endpoint)
  let searchQuery = getRandomItem(searchQueries);
  let searchParams = {
    q: searchQuery,
    latitude: 40.7128 + (Math.random() - 0.5) * 0.1, // NYC area with some variation
    longitude: -74.0060 + (Math.random() - 0.5) * 0.1,
    radius: Math.floor(Math.random() * 20) + 5, // 5-25 km
    limit: Math.floor(Math.random() * 20) + 5   // 5-25 results
  };
  
  let searchUrl = `${data.baseUrl}${API_VERSION}/search/intent?` + 
    Object.keys(searchParams).map(key => `${key}=${encodeURIComponent(searchParams[key])}`).join('&');
  
  let searchResponse = http.get(searchUrl);
  
  check(searchResponse, {
    'Search status is 200': (r) => r.status === 200,
    'Search response time < 1000ms': (r) => r.timings.duration < 1000,
    'Search returns results array': (r) => Array.isArray(r.json('results')),
    'Search response has intent': (r) => r.json('intent') !== undefined,
  });
  
  errorRate.add(searchResponse.status !== 200);
  responses.push(searchResponse);
  
  // Test 4: Business Listing (if search returned results)
  if (searchResponse.status === 200) {
    let searchData = searchResponse.json();
    if (searchData.results && searchData.results.length > 0) {
      let randomBusiness = getRandomItem(searchData.results);
      if (randomBusiness.id) {
        let businessResponse = http.get(`${data.baseUrl}${API_VERSION}/business/${randomBusiness.id}`);
        
        check(businessResponse, {
          'Business detail status is 200 or 404': (r) => [200, 404].includes(r.status),
          'Business detail response time < 500ms': (r) => r.timings.duration < 500,
        });
        
        errorRate.add(![200, 404].includes(businessResponse.status));
        responses.push(businessResponse);
      }
    }
  }
  
  // Test 5: AI Intent Analysis (if enabled)
  let intentPayload = JSON.stringify({
    query: searchQuery,
    context: {
      location: "New York, NY",
      time: "afternoon"
    }
  });
  
  let intentResponse = http.post(`${data.baseUrl}${API_VERSION}/ai/analyze-intent`, intentPayload, {
    headers: { 'Content-Type': 'application/json' },
  });
  
  check(intentResponse, {
    'Intent analysis status is 200 or 503': (r) => [200, 503].includes(r.status), // 503 if AI disabled
    'Intent analysis response time < 2000ms': (r) => r.timings.duration < 2000,
  });
  
  // Don't count 503 as error (AI might be disabled)
  errorRate.add(intentResponse.status !== 200 && intentResponse.status !== 503);
  responses.push(intentResponse);
  
  // Test 6: Recommendations API
  let recommendationsResponse = http.get(`${data.baseUrl}${API_VERSION}/recommendations?` +
    `category=${getRandomBusiness}&latitude=${searchParams.latitude}&longitude=${searchParams.longitude}`
  );
  
  check(recommendationsResponse, {
    'Recommendations status is 200': (r) => r.status === 200,
    'Recommendations response time < 800ms': (r) => r.timings.duration < 800,
  });
  
  errorRate.add(recommendationsResponse.status !== 200);
  responses.push(recommendationsResponse);
  
  // Test 7: Ranking API
  let rankingResponse = http.get(`${data.baseUrl}${API_VERSION}/ranking?` +
    `category=${getRandomItem(businessTypes)}&latitude=${searchParams.latitude}&longitude=${searchParams.longitude}`
  );
  
  check(rankingResponse, {
    'Ranking status is 200': (r) => r.status === 200,
    'Ranking response time < 600ms': (r) => r.timings.duration < 600,
  });
  
  errorRate.add(rankingResponse.status !== 200);
  responses.push(rankingResponse);
  
  // Test 8: Monitoring endpoints (should be fast)
  let statusResponse = http.get(`${data.baseUrl}${API_VERSION}/monitoring/status`);
  
  check(statusResponse, {
    'Status endpoint responds': (r) => [200, 403].includes(r.status), // 403 if auth required
    'Status response time < 200ms': (r) => r.timings.duration < 200,
  });
  
  responses.push(statusResponse);
  
  // Calculate average response time for this iteration
  let avgResponseTime = responses.reduce((sum, r) => sum + r.timings.duration, 0) / responses.length;
  customTrend.add(avgResponseTime);
  
  // Brief pause between iterations
  sleep(Math.random() * 2 + 1); // 1-3 seconds
}

// Teardown function - runs once after all tests
export function teardown(data) {
  console.log('Performance test completed');
  
  // Optional: Clean up test data or send results to monitoring system
  let summaryResponse = http.get(`${data.baseUrl}${API_VERSION}/monitoring/metrics/json`);
  if (summaryResponse.status === 200) {
    console.log('Final metrics retrieved from application');
  }
}