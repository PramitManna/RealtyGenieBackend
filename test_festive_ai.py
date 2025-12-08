#!/usr/bin/env python3
"""
Test Gemini AI Festive Email Generation
Run this to see sample AI-generated festive emails
"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from services.cron_service import generate_premium_festive_email

def test_festive_email_generation():
    """Test generating festive emails with Gemini AI"""
    
    print("=" * 80)
    print("🎄 Testing Gemini AI Festive Email Generation")
    print("=" * 80)
    print()
    
    # Test scenarios
    scenarios = [
        {
            "festival": "Christmas",
            "description": "A joyful holiday celebrating love, family, and the spirit of giving",
            "recipient": "Michael Chen",
            "agent": "Sarah Johnson",
            "company": "Century 21 Realty",
            "city": "Vancouver"
        },
        {
            "festival": "Canada Day",
            "description": "Celebrating Canadian pride, diversity, and our beautiful communities",
            "recipient": "Emma Thompson",
            "agent": "David Martinez",
            "company": "Royal LePage",
            "city": "Toronto"
        }
    ]
    
    for i, scenario in enumerate(scenarios, 1):
        print(f"\n{'='*80}")
        print(f"Test {i}: {scenario['festival']} Email")
        print(f"{'='*80}\n")
        
        print(f"Generating for:")
        print(f"  To: {scenario['recipient']}")
        print(f"  From: {scenario['agent']} ({scenario['company']})")
        print(f"  City: {scenario['city']}")
        print(f"\nGenerating with Gemini AI...\n")
        
        result = generate_premium_festive_email(
            festival_name=scenario['festival'],
            festival_description=scenario['description'],
            recipient_name=scenario['recipient'],
            agent_name=scenario['agent'],
            company_name=scenario['company'],
            city=scenario['city']
        )
        
        if result:
            print("✅ AI GENERATION SUCCESSFUL!\n")
            print(f"Subject: {result['subject']}\n")
            print("Body:")
            print("-" * 80)
            print(result['body'])
            print("-" * 80)
        else:
            print("❌ AI generation failed (will use template fallback in production)")
        
        print()
    
    print("\n" + "=" * 80)
    print("Test Complete!")
    print("=" * 80)

if __name__ == "__main__":
    test_festive_email_generation()
