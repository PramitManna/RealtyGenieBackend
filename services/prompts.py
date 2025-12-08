"""
Email prompt templates for Gemini AI generation.
Centralized location for all email-related prompts.
"""

from datetime import datetime
from typing import Dict


def build_single_email_prompt(category_prompt: str, context: Dict[str, str]) -> str:
    """
    Build optimized prompt for generating premium HTML emails with blended user tones.
    
    Args:
        category_prompt: The email category/type
        context: Dictionary containing agent_name, company_name, tones, objective, target_city, etc.
    
    Returns:
        Formatted prompt string for Gemini
    """
    current_year = datetime.now().year
    agent_name = context.get('agent_name', 'Real Estate Professional')
    company_name = context.get('company_name', 'Realty Company')
    tone = context.get('tones', 'professional')
    objective = context.get('objective', 'lead nurturing')
    target_city = context.get('target_city', 'your market')
    
    # Handle tone blending
    tones_array = context.get('tones_array', [])
    if isinstance(tones_array, list) and len(tones_array) > 1:
        tone_instruction = f"""Blend these communication tones harmoniously: {', '.join(tones_array)}
- Balance all tones naturally without contradicting each other
- Create a cohesive voice that incorporates the best qualities of each tone
- Primary tone is '{tone}' but incorporate elements from: {', '.join(tones_array[1:])}"""
    else:
        tone_instruction = f"Use {tone} language and style throughout"
    
    return f"""
ROLE:
You are an elite real estate email strategist who specializes in crafting high-conversion HTML emails for lead generation, nurturing, and appointment setting. Your writing style is premium, concise, psychologically persuasive, and tailored to the real estate industry.

TASK:
Generate a professional, premium-quality HTML email of around 150 words following the category instructions and user context provided. The output must persuade, build trust, and encourage action while maintaining a warm, credible tone.

CONTEXT:
Email Category: {category_prompt}
Agent Name: {agent_name}
Company Name: {company_name}
Target Market / City: {target_city}
Primary Objective: {objective}
Year: {current_year}

Tone Requirements:
{tone_instruction}

Required Placeholders (use exactly as written when appropriate):
- {{recipient_name}}
- {{city}}
- {{company}}
- {{agent_name}}
- {{year}}

REASONING (INTERNAL LOGIC TO FOLLOW):
Follow these internal reasoning steps while generating the email (do NOT reveal reasoning):

1. Understand the category’s intent (e.g., follow-up, cold outreach, nurturing, onboarding, reactivation).
2. Identify the psychological levers best suited (trust, curiosity, urgency, authority, value reassurance).
3. Craft a strong hook referencing {{city}} or their situation to increase personalization.
4. Highlight ONE clear value proposition to avoid overwhelming the lead.
5. Keep language premium, concise, emotionally intelligent, and benefit-driven.
6. Integrate premium styling using selective gold (#d4af37).
7. Maintain readability with short paragraphs.
8. End with a single strong call-to-action aligned with the goal (book a call, view listings, reply, etc.).
9. Do NOT include a signature — the system will append it.

OUTPUT:

The <body> content MUST follow this structure:

1. Start with a premium headline:
<h1 style='margin:0 0 12px 0; font-size:22px; font-weight:700;'>
  A strong value-driven headline
</h1>

2. First paragraph (personalized hook):
<p style='margin:0 0 14px 0; line-height:1.6;'>
  Include a warm introduction referencing {{city}} or their situation. 
  Highlight one <strong style='color:#d4af37;'>gold-accented phrase</strong> to draw attention.
</p>

3. Value proposition block with highlighted phrases:
<p style='margin:0 0 14px 0; line-height:1.6;'>
  Present the core benefit or insight. Bold only the most important 
  <strong style='color:#d4af37;'>result-driven statements</strong>.
</p>

4. Persuasive bullet list with icons (MUST appear in every email):
<ul style='padding-left:18px; margin:0 0 14px 0;'>
  <li style='margin-bottom:6px;'>
    <strong style='color:#d4af37;'>•</strong> Short, punchy proof or benefit
  </li>
  <li style='margin-bottom:6px;'>
    <strong style='color:#d4af37;'>•</strong> What makes your guidance safer/easier
  </li>
  <li style='margin-bottom:6px;'>
    <strong style='color:#d4af37;'>•</strong> Hyper-local or trust-building insight
  </li>
</ul>

5. Final CTA paragraph:
<p style='margin:0 0 14px 0; line-height:1.6;'>
  Include one <strong style='color:#d4af37;'>clear call-to-action</strong> encouraging them 
  to book a call, view a property list, or reply.
</p>

Output must be ONLY valid JSON in the structure below:

{{
  "subject": "",
  "body": ""
}}

STOPPING:
Stop after producing the JSON object.  
Do NOT include explanations, markdown, code blocks, reasoning, or any text outside the JSON.
"""


def build_triggered_email_prompt(
    realtor_name: str,
    brokerage: str,
    markets: list,
    purpose: str,
    persona: str,
    short_description: str = None
) -> str:
    """
    Build prompt for generating personalized triggered email content.
    
    Args:
        realtor_name: Name of the realtor
        brokerage: Realtor's brokerage/company
        markets: List of markets the realtor serves
        purpose: Purpose of the email
        persona: Target persona (buyer, seller, investor, past_client, referral, cold_prospect)
        short_description: Optional additional context
    
    Returns:
        Formatted prompt string for Gemini
    """
    # Map persona to appropriate tones
    persona_tone_mapping = {
        "buyer": ["Consultative", "Advisor"],
        "seller": ["Expert", "Data driven"],
        "investor": ["Expert", "Data driven"],
        "past_client": ["Friendly", "Warm"],
        "referral": ["Friendly", "Warm"],
        "cold_prospect": ["Light-hearted", "Humorous"]
    }
    
    tones = persona_tone_mapping.get(persona.lower(), ["Professional", "Consultative"])
    markets_str = ", ".join(markets) if markets else "local area"
    tones_str = ", ".join(tones)
    
    return f"""
ROLE:    
You are an elite real estate email strategist. Your role is to generate highly personalized, psychologically persuasive, and elegantly formatted HTML emails for automation triggers in a real estate lead-engagement system.

TASK:
Create a premium triggered email tailored to the realtor’s persona, purpose, and markets. The email must feel personal, trust-building, and relevant to real estate decision psychology.

CONTEXT:
Realtor Name: {realtor_name}
Brokerage: {brokerage}
Markets: {markets_str}

Trigger Purpose: {purpose}
Target Persona: {persona}
Persona Tone Profile: {tones_str}
Additional Context: {short_description or "None provided"}

Mandatory Personalization Placeholder:
- {{name}} must appear in the body

REASONING (INTERNAL, NOT OUTPUT):
Follow this reasoning while generating the email (NEVER reveal this section):

1. Determine emotional state + needs of the persona:
   - Buyer → guidance, clarity, options  
   - Seller → authority, market proof, strategy  
   - Investor → numbers, ROI, opportunity  
   - Past client → relationship, warmth, familiarity  
   - Referral → trust extension, low pressure  
   - Cold prospect → pattern-interrupt, curiosity

2. Use trigger psychology:
   - Acknowledge the behavioral signal subtly (no creepiness)  
   - Add one “why this matters now” insight  
   - Make the email irresistibly skimmable  

3. Apply premium HTML styling:
   - Strong headline  
   - Short paragraphs with spacing  
   - Bolds using <strong>…</strong>  
   - Bullet list of compelling benefits  
   - Clear CTA with confidence-boosting phrasing  

4. Ideal length: 140–220 words  
5. Tone must exactly match persona’s mapped tones  
6. NO signature — system will add it later  

OUTPUT (STRICT)
Return ONLY valid JSON in this exact structure (literally replace field values, keep structure):

{{
  "subject": "Write a compelling, purpose-aligned subject line here (no emojis)",
  "body": "<h1 style='margin:0 0 12px 0; font-size:22px; font-weight:700;'>Premium headline here</h1><p style='margin:0 0 14px 0; line-height:1.6;'>Use name early for personalization. Highlight one <strong style='color:#d4af37;'>gold-accented benefit</strong> in the intro.</p><p style='margin:0 0 14px 0; line-height:1.6;'>Add value-driven insights relevant to the persona. Include subtle context about {markets_str}, and weave in persuasive lines naturally.</p><ul style='padding-left:18px; margin:0 0 14px 0;'><li style='margin-bottom:6px;'><strong style='color:#d4af37;'>•</strong> Benefit or proof point tailored to the trigger</li><li style='margin-bottom:6px;'><strong style='color:#d4af37;'>•</strong> Trust-building or market insight</li><li style='margin-bottom:6px;'><strong style='color:#d4af37;'>•</strong> Reassuring next-step option</li></ul><p style='margin:0 0 14px 0; line-height:1.6;'>End with a single <strong style='color:#d4af37;'>clear call-to-action</strong> related to the email's purpose (book a call, check listings, reply, etc.).</p>"
}}

Strict rules:
- Do NOT escape HTML tags.
- Use single quotes inside HTML attributes.
- Use {{name}} exactly as shown.
- No extra keys, no commentary, no markdown.
- Output MUST be valid JSON only.

STOP
Stop after producing the JSON object.
"""


def build_image_extraction_prompt(extracted_text: str) -> str:
    """
    Build prompt for extracting structured contact information from image text.
    
    Args:
        extracted_text: Text extracted from image via Vision API
    
    Returns:
        Formatted prompt string for Gemini
    """
    return f"""Extract structured contact information from this document text.
Return a JSON array of objects with these fields: name, email, phone, city, address

Rules:
- If a field is not found, set it to null
- Extract ALL contacts found in the document
- Ensure emails are valid format
- Phone numbers should include country/area codes if present
- City should be extracted from addresses when possible

Document text:
{extracted_text}

Return ONLY the JSON array, no other text or markdown."""
