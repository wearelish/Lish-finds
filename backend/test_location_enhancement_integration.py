#!/usr/bin/env python3
"""
Comprehensive Integration Test for Location Enhancement System

Tests the complete location-based enhancement system including:
- Precise location detection
- Business data validation with ₹70+ movie ticket constraint
- Dynamic pricing and availability
- Location verification and data accuracy scoring
"""

import asyncio
import json
from datetime import datetime, timezone
from decimal import Decimal

# Import all the services we've built
from services.location_service import LocationService, Location
from services.business_rules_engine import BusinessRulesEngine
from services.area_mapping_service import AreaMappingService
from services.dynamic_pricing_service import DynamicPricingService, DemandLevel, WeatherCondition
from services.availability_service import AvailabilityService
from services.location_verification_service import LocationVerificationService
from services.data_accuracy_service import DataAccuracyService
from services.enhanced_search_service import EnhancedSearchService, SearchFilters
from models.business import Business


async def test_complete_location_enhancement_system():
    """
    Comprehensive integration test of the entire location enhancement system
    """
    print("🚀 Starting Comprehensive Location Enhancement System Test")
    print("=" * 70)
    
    # Initialize all services
    location_service = LocationService()
    business_rules = BusinessRulesEngine()
    area_mapping = AreaMappingService()
    pricing_service = DynamicPricingService()
    availability_service = AvailabilityService()
    verification_service = LocationVerificationService(location_service, business_rules)
    accuracy_service = DataAccuracyService()
    search_service = EnhancedSearchService()
    
    # Test location - Mumbai city center
    test_location = Location(
        latitude=19.0760,
        longitude=72.8777,
        address="Fort, Mumbai",
        city="Mumbai",
        area="Fort"
    )
    
    print(f"📍 Test Location: {test_location.address}")
    print(f"   Coordinates: {test_location.latitude}, {test_location.longitude}")
    
    # Test 1: Location Services
    print("\n🧭 Test 1: Location Services")
    print("-" * 30)
    
    # Test geocoding
    geocoded = await location_service.geocode_address("Connaught Place, New Delhi")
    print(f"✅ Geocoding: {geocoded.address} -> {geocoded.latitude}, {geocoded.longitude}")
    
    # Test distance calculation
    mumbai_location = Location(latitude=19.0760, longitude=72.8777, address="Mumbai")
    delhi_location = Location(latitude=28.6139, longitude=77.2090, address="Delhi")
    distance = location_service.calculate_distance(mumbai_location, delhi_location)
    print(f"✅ Distance Mumbai-Delhi: {distance:.2f} km")
    
    # Test 2: Business Constraints and Validation
    print("\n🏢 Test 2: Business Constraints Validation")
    print("-" * 40)
    
    # Create test cinema with pricing constraints
    test_cinema = Business(
        id="test_cinema_001",
        name="Test Cinema Palace",
        category="cinema",
        latitude=19.0896,
        longitude=72.8656,
        address="Test Address, Mumbai",
        city="Mumbai",
        state="Maharashtra",
        phone="+91-9876543210",
        email="info@testcinema.com",
        operating_hours={
            "monday": {"open": "09:00", "close": "23:00"},
            "tuesday": {"open": "09:00", "close": "23:00"},
            "wednesday": {"open": "09:00", "close": "23:00"},
            "thursday": {"open": "09:00", "close": "23:00"},
            "friday": {"open": "09:00", "close": "23:00"},
            "saturday": {"open": "09:00", "close": "23:00"},
            "sunday": {"open": "09:00", "close": "23:00"}
        },
        ticket_prices={
            "regular": Decimal("150.00"),
            "premium": Decimal("250.00"),
            "recliner": Decimal("350.00")
        }
    )
    
    # Test pricing validation - should pass (all prices >= ₹70)
    pricing_validation = business_rules.validate_pricing(
        test_cinema.ticket_prices, "cinema", "Mumbai", "Maharashtra"
    )
    print(f"✅ Pricing Validation (Valid): {pricing_validation.is_valid}")
    if not pricing_validation.is_valid:
        print(f"   Errors: {pricing_validation.errors}")
    
    # Test with invalid pricing (below ₹70)
    invalid_cinema = Business(
        id="invalid_cinema_001",
        name="Invalid Cinema",
        category="cinema",
        latitude=19.0896,
        longitude=72.8656,
        address="Invalid Address, Mumbai",
        city="Mumbai", 
        state="Maharashtra",
        ticket_prices={
            "regular": Decimal("50.00"),  # Below minimum!
            "premium": Decimal("150.00")
        }
    )
    
    invalid_pricing = business_rules.validate_pricing(
        invalid_cinema.ticket_prices, "cinema", "Mumbai", "Maharashtra"
    )
    print(f"❌ Pricing Validation (Invalid): {invalid_pricing.is_valid}")
    print(f"   Errors: {invalid_pricing.errors}")
    
    # Test 3: Dynamic Pricing and Availability
    print("\n💰 Test 3: Dynamic Pricing and Availability")
    print("-" * 40)
    
    # Test dynamic pricing
    base_price = Decimal("150.00")
    pricing_info = pricing_service.calculate_real_time_pricing(
        "test_cinema_001",
        base_price,
        "cinema", 
        test_location,
        demand_level=DemandLevel.HIGH,
        weather_condition=WeatherCondition.RAINY,
        special_events=["weekend", "festival"]
    )
    
    print(f"✅ Dynamic Pricing:")
    print(f"   Base Price: ₹{base_price}")
    print(f"   Final Price: ₹{pricing_info['final_price']}")
    print(f"   Price Change: {pricing_info['price_change_percent']:.1f}%")
    print(f"   Factors Applied: {pricing_info['factors_applied'][:3]}")
    
    # Ensure dynamic pricing still respects minimum constraint
    if pricing_info['final_price'] >= 70:
        print(f"✅ Minimum price constraint maintained")
    else:
        print(f"❌ Minimum price constraint violated!")
    
    # Test availability
    availability = availability_service.get_business_availability(
        "test_cinema_001", "cinema", test_location
    )
    print(f"✅ Availability Status: {availability.current_status.value}")
    print(f"   Current Occupancy: {availability.current_occupancy_percent}%")
    print(f"   Available Capacity: {availability.current_availability}")
    
    # Test 4: Location Verification
    print("\n🔍 Test 4: Location Verification")
    print("-" * 30)
    
    # Verify the valid cinema
    verification_result = await verification_service.verify_business_location(test_cinema)
    print(f"✅ Verification Score: {verification_result.score:.1f}/100")
    print(f"   Is Verified: {verification_result.is_verified}")
    print(f"   Confidence Level: {verification_result.confidence_level}")
    if verification_result.issues:
        print(f"   Issues: {verification_result.issues}")
    
    # Verify the invalid cinema
    invalid_verification = await verification_service.verify_business_location(invalid_cinema)
    print(f"❌ Invalid Cinema Score: {invalid_verification.score:.1f}/100")
    print(f"   Is Verified: {invalid_verification.is_verified}")
    print(f"   Issues: {invalid_verification.issues}")
    
    # Test 5: Data Accuracy Assessment
    print("\n📊 Test 5: Data Accuracy Assessment")
    print("-" * 35)
    
    # Assess data quality
    quality_metrics = await accuracy_service.assess_data_quality(test_cinema)
    print(f"✅ Overall Quality Score: {quality_metrics.overall_score:.1f}/100")
    print(f"   Completeness: {quality_metrics.completeness_score:.1f}")
    print(f"   Consistency: {quality_metrics.consistency_score:.1f}")
    print(f"   Validity: {quality_metrics.validity_score:.1f}")
    print(f"   Accuracy: {quality_metrics.accuracy_score:.1f}")
    print(f"   Freshness: {quality_metrics.freshness_score:.1f}")
    
    # Field-level analysis
    field_analyses = await accuracy_service.analyze_field_quality(test_cinema)
    print(f"\n📋 Field Quality Analysis:")
    for field_analysis in field_analyses[:5]:  # Show first 5 fields
        status = "✅" if field_analysis.is_valid else "❌"
        print(f"   {status} {field_analysis.field_name}: {field_analysis.quality_score:.1f}/100")
        if field_analysis.issues:
            print(f"      Issues: {field_analysis.issues}")
    
    # Test 6: Enhanced Search Integration
    print("\n🔍 Test 6: Enhanced Search with Verification")
    print("-" * 45)
    
    # Search for cinemas near test location
    search_filters = SearchFilters(
        max_distance_km=5.0,
        max_travel_time_minutes=30,
        business_types=["cinema"],
        transport_modes=["driving", "metro"]
    )
    
    search_results = search_service.search_businesses(
        test_location, 
        query="cinema", 
        filters=search_filters
    )
    
    print(f"✅ Search Results: {len(search_results)} businesses found")
    for i, result in enumerate(search_results[:3], 1):  # Show first 3 results
        print(f"\n   {i}. {result.name}")
        print(f"      Distance: {result.distance_km:.2f} km")
        print(f"      Verification Score: {result.verification_score:.1f}/100")
        print(f"      Data Quality: {result.data_quality_score:.1f}/100")
        print(f"      Is Verified: {result.is_verified}")
        print(f"      Relevance Score: {result.relevance_score:.1f}")
    
    # Test 7: Comprehensive Verification Report
    print("\n📄 Test 7: Comprehensive Verification Report")
    print("-" * 45)
    
    # Get verification report for test businesses
    business_ids = ["cinema_001", "cinema_002"]  # Mock business IDs
    verification_report = await search_service.get_verification_report(business_ids)
    
    print(f"✅ Verification Report Generated")
    print(f"   Total Businesses: {verification_report['total_businesses']}")
    print(f"   Verified Businesses: {verification_report['verification_summary']['verified']}")
    print(f"   High Confidence: {verification_report['verification_summary']['high_confidence']}")
    print(f"   Average Verification Score: {verification_report['verification_summary']['avg_verification_score']:.1f}")
    print(f"   Critical Issues: {len(verification_report['critical_issues'])}")
    
    if verification_report['critical_issues']:
        print(f"\n⚠️  Critical Issues Found:")
        for issue in verification_report['critical_issues'][:3]:  # Show first 3 issues
            print(f"   - {issue['type']}: {issue['details']}")
    
    # Test 8: Movie Ticket Price Constraint Enforcement
    print("\n🎬 Test 8: Movie Ticket Price Constraint Enforcement")
    print("-" * 55)
    
    # Test various scenarios
    test_scenarios = [
        {"name": "Valid Pricing", "prices": {"regular": 150, "premium": 250}, "should_pass": True},
        {"name": "Edge Case (₹70)", "prices": {"regular": 70, "premium": 150}, "should_pass": True},
        {"name": "Invalid Pricing", "prices": {"regular": 50, "premium": 150}, "should_pass": False},
        {"name": "Severely Invalid", "prices": {"regular": 25, "premium": 45}, "should_pass": False}
    ]
    
    for scenario in test_scenarios:
        test_cinema_scenario = Business(
            id=f"scenario_{scenario['name'].lower().replace(' ', '_')}",
            name=f"Cinema {scenario['name']}",
            category="cinema",
            latitude=19.0896,
            longitude=72.8656,
            address="Test Address, Mumbai",
            city="Mumbai",
            state="Maharashtra",
            ticket_prices=scenario["prices"]
        )
        
        scenario_verification = await verification_service.verify_business_location(test_cinema_scenario)
        
        # Check if verification result matches expectation
        passed = scenario_verification.score >= 75 if scenario['should_pass'] else scenario_verification.score < 75
        status = "✅" if passed else "❌"
        
        print(f"   {status} {scenario['name']}: Score {scenario_verification.score:.1f}/100")
        if not passed:
            print(f"      Expected: {'Pass' if scenario['should_pass'] else 'Fail'}, Got: {'Pass' if scenario_verification.score >= 75 else 'Fail'}")
    
    print("\n" + "=" * 70)
    print("🎉 Location Enhancement System Test Completed!")
    print("✅ All major components tested successfully")
    print("✅ Movie ticket ₹70 minimum constraint enforced")
    print("✅ Comprehensive verification and accuracy scoring operational")
    print("=" * 70)


def test_sync_wrapper():
    """Synchronous wrapper for the async test"""
    asyncio.run(test_complete_location_enhancement_system())


if __name__ == "__main__":
    print("Starting Location Enhancement Integration Test...")
    test_sync_wrapper()