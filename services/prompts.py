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
You are a top-tier real estate email strategist who writes premium, persuasive, high-converting HTML emails for lead generation, nurturing, and appointment setting.

TASK:
Write a ~200-word luxury-grade HTML email using the context below. The tone must be warm, credible, emotionally intelligent, and designed to drive a single clear action.

CONTEXT:
Email Category: {category_prompt}
Agent Name: {agent_name}
Company Name: {company_name}
Target Market: {target_city}
Objective: {objective}
Year: {current_year}
Tone: {tone_instruction}

Required Placeholders:
{{recipient_name}}, {{city}}, {{company}}, {{agent_name}}, {{year}}

INTERNAL LOGIC (DO NOT REVEAL):
- Understand the email’s intent.
- Use trust, authority, curiosity, or urgency strategically.
- Start with a personalized hook referencing {{city}}.
- Present ONE core value proposition.
- Keep language premium, concise, and benefit-focused.
- Use clean, elegant formatting.
- End with a single strong CTA aligned with the objective.
- It should not have any markdown language , strictly html format

OUTPUT:
Return ONLY valid JSON:
{{
  "subject": "",
  "body": ""
}}

HTML BODY MUST FOLLOW THIS STRUCTURE:

<h1 style="margin:0 0 14px; font-size:24px; font-weight:700; letter-spacing:-0.3px;">
  Premium Value-Driven Headline
</h1>

<p style="margin:0 0 16px; line-height:1.65; font-size:15px;">
  Personalized opening referencing {{city}} with a warm tone and 
  a strategic <strong>highlight that builds relevance</strong>.
</p>

<p style="margin:0 0 16px; line-height:1.65; font-size:15px;">
  Deliver one clear value proposition with <strong>specific outcomes</strong> 
  and a concise explanation of why it matters now.
</p>

<div style="margin:0 0 18px; padding:12px 14px; border-radius:6px;">
  <ul style="padding-left:18px; margin:0; font-size:15px; line-height:1.55;">
    <li style="margin-bottom:8px;">
      <strong> A short, credible proof or benefit </strong>
    </li>
    <li style="margin-bottom:8px;">
      <strong> What makes your process safer, easier, or smarter </strong>
    </li>
    <li style="margin-bottom:0;">
      <strong> A hyper-local trust insight tied to {{city}} </strong>
    </li>
  </ul>
</div>

<p style="margin:0; line-height:1.65; font-size:15px;">
  Close with a single <strong>clear call-to-action</strong> aligned with your objective.
</p>

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
  "body": "<h1 style='margin:0 0 12px 0; font-size:22px; font-weight:700;'>Premium headline here</h1><p style='margin:0 0 14px 0; line-height:1.6;'>Use name early for personalization. Highlight one <strong'>gold-accented benefit</strong> in the intro.</p><p style='margin:0 0 14px 0; line-height:1.6;'>Add value-driven insights relevant to the persona. Include subtle context about {markets_str}, and weave in persuasive lines naturally.</p><ul style='padding-left:18px; margin:0 0 14px 0;'><li style='margin-bottom:6px;'><strong'>•</strong> Benefit or proof point tailored to the trigger</li><li style='margin-bottom:6px;'><strong'>•</strong> Trust-building or market insight</li><li style='margin-bottom:6px;'><strong'>•</strong> Reassuring next-step option</li></ul><p style='margin:0 0 14px 0; line-height:1.6;'>End with a single <strong'>clear call-to-action</strong> related to the email's purpose (book a call, check listings, reply, etc.).</p>"
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


def build_email_signature(
    realtor_name: str,
    brokerage: str,
    phone: str,
    email: str,
    website: str = None,
    title: str = None,
    experience: str = None,
    markets: list = None,
    calendly_link: str = None,
    logo_url: str = None
) -> str:
    """
    Build a premium HTML email signature block with logo and Calendly CTA button.
    
    Args:
        realtor_name: Name of the realtor
        brokerage: Brokerage/company name
        phone: Phone number with country code
        email: Email address
        website: Optional website URL
        title: Optional title/designation
        experience: Optional experience description
        markets: Optional list of markets served
        calendly_link: Optional Calendly link for booking calls
        logo_url: Optional logo image URL (brokerage or brand logo)
    
    Returns:
        HTML signature block with logo and CTA button
    """
    markets_text = f"Serving {', '.join(markets)}" if markets else ""
    
    signature_html = f"""
<div style='border-top: 2px solid #d4af37; margin-top: 24px; padding-top: 20px; font-family: Arial, sans-serif; color: #333;'>
  <table style='width: 100%; border-collapse: collapse;'>
    <tr>
      <!-- Logo on Left -->
      {f'''<td style='vertical-align: top; padding-right: 20px; width: 140px;'>
        <img src='{logo_url}' alt='{brokerage}' style='max-width: 120px; max-height: 80px; object-fit: contain; display: block;' />
      </td>''' if logo_url else ""}
      
      <!-- Details on Right -->
      <td style='vertical-align: top;'>
        <!-- Realtor Info -->
        <div style='margin-bottom: 12px;'>
          <strong style='font-size: 16px; color: #000; display: block; margin-bottom: 4px;'>{realtor_name}</strong>
          {f"<div style='color: #666; font-size: 12px;'>{title}</div>" if title else ""}
        </div>
        
        <!-- Company Info -->
        <div style='margin-bottom: 12px; line-height: 1.6;'>
          <div style='color: #666; font-size: 13px;'>{brokerage}</div>
          {f"<div style='color: #666; font-size: 12px;'>{experience}</div>" if experience else ""}
          {f"<div style='color: #666; font-size: 12px;'>{markets_text}</div>" if markets_text else ""}
        </div>
        
        <!-- Contact Information -->
        <div style='margin-bottom: 16px; line-height: 1.8; font-size: 13px;'>
          {f"<div style='color: #333; margin-bottom: 4px;'>📞 <strong>{phone}</strong></div>" if phone else ""}
          {f"<div style='color: #333; margin-bottom: 4px;'>📧 <a href='mailto:{email}' style='color: #d4af37; text-decoration: none;'>{email}</a></div>" if email else ""}
          {f"<div style='color: #333;'>🌐 <a href='https://{website}' style='color: #d4af37; text-decoration: none;'>{website}</a></div>" if website else ""}
        </div>
        
        <!-- Calendly CTA Button -->
        {f'''<div style='margin-top: 16px;'>
          <a href='{calendly_link}' style='display: inline-block; background: linear-gradient(135deg, #1e88e5 0%, #1565c0 100%); color: white; padding: 12px 24px; text-decoration: none; border-radius: 8px; font-weight: bold; font-size: 14px; box-shadow: 0 2px 8px rgba(30, 136, 229, 0.3);'>
            📅 Book a 15-minute discovery call
          </a>
        </div>''' if calendly_link else ""}
      </td>
    </tr>
  </table>
</div>
"""
    return signature_html.strip()


def wrap_email_html(content: str) -> str:
    """
    Wrap email content in a professional, responsive HTML container.
    
    Args:
        content: The inner HTML content of the email (body + signature)
        
    Returns:
        Full HTML document string
    """
    from datetime import datetime
    return f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Email</title>
    <style>
        body {{
            margin: 0;
            padding: 0;
            background-color: #f4f4f4;
            font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
            -webkit-font-smoothing: antialiased;
            line-height: 1.6;
            color: #333333;
        }}
        .container {{
            max-width: 600px;
            margin: 40px auto;
            background-color: #ffffff;
            border-radius: 8px;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
            overflow: hidden;
        }}
        .content {{
            padding: 40px;
        }}
        .footer {{
            background-color: #fafafa;
            padding: 20px;
            text-align: center;
            font-size: 12px;
            color: #999999;
            border-top: 1px solid #eeeeee;
        }}
        @media only screen and (max-width: 620px) {{
            .container {{
                margin: 0;
                border-radius: 0;
                width: 100% !important;
                box-shadow: none;
            }}
            .content {{
                padding: 20px;
            }}
        }}
        a {{
            color: #1e88e5;
            text-decoration: none;
        }}
        a:hover {{
            text-decoration: underline;
        }}
        h1, h2, h3 {{
            color: #111111;
            margin-top: 0;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="content">
            {content}
        </div>
    </div>
</body>
</html>
""".strip()