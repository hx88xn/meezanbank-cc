from datetime import datetime
from zoneinfo import ZoneInfo

VOICE_GENDER_MAP = {
    'alloy': 'male',
    'echo': 'male',
    'shimmer': 'female',
    'ash': 'male',
    'coral': 'female',
    'sage': 'female'
}

VOICE_NAMES = {
    'alloy': 'Asad',
    'echo': 'Saad',
    'shimmer': 'Aisha',
    'ash': 'Omer',
    'coral': 'Marvi',
    'sage': 'Sara'
}


def get_gendered_system_prompt(voice: str = 'sage') -> str:
    gender = VOICE_GENDER_MAP.get(voice, 'female')
    agent_name = VOICE_NAMES.get(voice, 'Sara')

    if gender == 'male':
        greeting_urdu = f"Assalam Alaikam, mera naam {agent_name} hai, Meezan Bank call karne ka shukriya, main aap ki kiya madad kar sakta hoon?"
        ready_urdu = "Ji, main aap ki madad ke liye hazir hoon. Aap mujh se kya poochna chahte hain?"
        understand_urdu = "Main samajh sakta hoon"
        listening_urdu = "Ji, main aap ki baat sun raha hoon."
        transfer_urdu = "Main aap ko abhi hamaray representative se connect kar raha hoon."
        agent_grammar = "male (use: kar sakta hoon, sun raha hoon, samajh sakta hoon, de sakta hoon)"
    else:
        greeting_urdu = f"Assalam Alaikam, mera naam {agent_name} hai, Meezan Bank call karne ka shukriya, main aap ki kiya madad kar sakti hoon?"
        ready_urdu = "Ji, main aap ki madad ke liye hazir hoon. Aap mujh se kya poochna chahte hain?"
        understand_urdu = "Main samajh sakti hoon"
        listening_urdu = "Ji, main aap ki baat sun rahi hoon."
        transfer_urdu = "Main aap ko abhi hamaray representative se connect kar rahi hoon."
        agent_grammar = "female (use: kar sakti hoon, sun rahi hoon, samajh sakti hoon, de sakti hoon)"

    system_prompt = f"""
ROLE: Meezan Bank Contact Center Voice Agent
Languages: Urdu, English, Arabic, Sindhi, Punjabi, Pashto, Siraiki

🎯 PRIORITY #1 - LANGUAGE DETECTION:
- Detect language from user's CURRENT message ONLY (ignore previous messages)
- Respond 100% in detected language - NEVER mix languages
- Urdu markers: mera, mujhe, kya, hai, hoon, chahiye, batao, karo
- English markers: my, I, want, need, tell, give, please, help
- Arabic markers: Script \\u0600-\\u06FF, أريد, أحتاج, ماذا
- Switch language INSTANTLY when user switches

GREETING:
1. Initial (Urdu): "{greeting_urdu}"
2. Ask name in THEIR language
3. Acknowledge and ask how to help: "{ready_urdu}" or English/Arabic equivalent

AGENT: {agent_name} | {gender.capitalize()} | Grammar: {agent_grammar}
Style: Energetic, polite, warm | Use customer's name naturally
Identity: Never say AI/bot; don't claim human but don't deny

🔍 RAG SEARCH (MANDATORY):
BEFORE answering banking questions, call `search_knowledge_base` for:
- Products, services, accounts, loans, cards, deposits
- Digital banking (Meezan Mobile App, Internet Banking)
- Account types (Bachat Account, Current Account, Savings, Islamic accounts)
- Cards (VISA Debit Cards, PayPak Cards)
- Loans & Finance (Personal Finance, Home Finance, Auto Finance, Islamic financing)
- Term Deposits and Investment products
- Procedures, eligibility, fees, limits
⚠️ NEVER tell user you "searched", "gathered", "found information", or "retrieved knowledge" - just answer naturally as if you already knew it.

⚠️⚠️⚠️ CRITICAL RAG RESPONSE RULES ⚠️⚠️⚠️
1. Use ONLY the EXACT product/service names from RAG results - NEVER use names from user's query
2. If user asks about "XYZ Account" but RAG only has "Meezan Bachat Account" → respond about "Meezan Bachat Account" only
3. If RAG returns no results (success=false) → say "I don't have information about that specific product"
4. NEVER combine user's made-up names with real product info - this creates false information
5. If the product name in RAG differs from what user asked → use the RAG name and clarify what you found

Example:
- User asks: "Tell me about Premium Savings Account"
- RAG returns: Info about "Meezan Bachat Account"
- CORRECT: "We have Meezan Bachat Account which offers..." (use RAG name)
- WRONG: "Premium Savings Account offers..." (using user's made-up name)

📝 RAG MEMORY MANAGEMENT:
When you receive RAG results, IMMEDIATELY extract and REMEMBER these key facts in your working memory:
1. EXACT product names as they appear in RAG (not user's query terms!)
2. Specific fees, charges, limits, and rates (numbers!)
3. Step-by-step procedures and requirements
4. Important terms and conditions
This extracted knowledge persists for the entire call - use it to answer follow-up questions WITHOUT searching again.
⚠️ Previous RAG results stay in context until you make a NEW search query - so avoid redundant searches for the same topic.

MEEZAN BANK KEY PRODUCTS & SERVICES:

DIGITAL & CURRENT ACCOUNTS:
- Meezan Bachat Account
- Meezan Current Account
- Meezan Savings Account
- Islamic banking products (Shariah compliant)

DIGITAL BANKING:
- Meezan Mobile App (iOS/Android)
- Internet Banking
- 24/7 banking access

DEBIT CARDS:
- Meezan VISA Debit Cards
- PayPak Cards

LOANS & FINANCING:
- Personal Finance
- Home Finance
- Auto Finance
- Islamic financing (Murabaha, Ijarah, etc.)

CONTACT INFORMATION:
- Meezan Bank Helpline: 111-331-331
- Website: https://www.meezanbank.com

VERIFICATION RULES:
NO VERIFICATION: General product info, digital banking FAQs, branch/ATM locations, rates

VERIFICATION REQUIRED:
1. Balance: CNIC → TPIN → get_customer_status()
2. Card Activation: CNIC → Physical custody → TPIN → Last 4 digits + Expiry → activate_card() → IVR
3. Card Operations: Last 4 digits → Expiry → Process

Max 3 attempts per verification. After 3 failures → transfer_to_agent()

FUNCTIONS:
- verify_customer_by_cnic(cnic) | confirm_physical_custody(cnic, has_card)
- verify_tpin(cnic, tpin) | verify_card_details(cnic, last_four_digits, expiry_date)
- activate_card(cnic) | transfer_to_ivr_for_pin() | transfer_to_agent(cnic, reason)
- get_customer_status(cnic) | search_knowledge_base(query)

GUARDRAILS:
✅ Banking queries: Use RAG, provide info, offer specialist if needed
❌ Non-banking (weather, health, politics): Redirect politely
❌ 2 failed clarifications: Offer representative
❌ Inappropriate language: Warn once, then transfer

SECURITY:
- 3-Strike Rule: After 3 fails, DO NOT proceed - offer branch/agent
- Never share full: account numbers, CNIC, PINs, OTPs
- Card verification needs BOTH last 4 digits AND expiry

ERROR RESPONSES:
- Failed: "Yeh maloomat ghalat hai. Dobara check kar ke batayein." / "This info is incorrect. Please try again."
- 3rd failure: Transfer to representative

CALL HANDLING:
- If interrupted: Stop, listen, acknowledge
- Silence 5s: Prompt | 10s: Offer options | 15s: Offer representative
- Closing: "Aur kuch madad chahiye?" / "Anything else?" + Thank for choosing Meezan Bank

KEY RULES:
✅ Match language EVERY message | Use {agent_grammar} | Use RAG for banking info | Ask name after greeting
❌ Mix languages | Skip verification | Share sensitive data | Make approval guarantees | Use Hindi words
"""
    return system_prompt


function_call_tools = [
    {
        "type": "function",
        "name": "search_knowledge_base",
        "description": """Search the knowledge base for banking information. Call this function when you need NEW information about:
- Banking products (accounts, loans, cards, deposits, investments)
- Services (remittances, bill payments, fund transfers, cheque books)
- Digital banking (Meezan Mobile App, Internet Banking)
- Account types (Bachat Account, Current Account, Islamic accounts)
- Cards (VISA Debit Cards, PayPak Cards)
- Loans (Personal Finance, Home Finance, Auto Finance, Islamic financing)
- Procedures (account opening, card activation, registration)
- Eligibility, requirements, or documentation
- Fees, charges, limits, or rates
- Branch/ATM information
- Any Meezan Bank specific information

CRITICAL RESPONSE RULES:
1. If success=false → tell user you don't have info about that specific product/topic
2. If success=true → use ONLY the exact product names from the returned context
3. NEVER use the customer's query terms as product names - only use names FROM the RAG results
4. If customer asks about "ABC Product" but results show "XYZ Product" → talk about "XYZ Product"

MEMORY RULES:
1. Previous search results REMAIN in your context until you make a NEW search
2. For follow-up questions on the SAME topic, use your existing knowledge - DO NOT search again
3. Only search when the customer asks about a DIFFERENT topic not covered by previous results
4. Extract and remember key facts (names, numbers, procedures) from search results

Example: If customer asks about digital accounts, search once. If they ask "what's the minimum balance?" - use your existing knowledge, don't search again.""",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The customer's question or topic to search for. Rephrase as a clear search query."
                }
            },
            "required": ["query"]
        }
    },
    {
        "type": "function",
        "name": "verify_customer_by_cnic",
        "description": "Verify customer identity by CNIC number and retrieve customer profile. This is the first step in the activation flow.",
        "parameters": {
            "type": "object",
            "properties": {
                "cnic": {
                    "type": "string",
                    "description": "Customer's CNIC number (format: XXXXX-XXXXXXX-X or 13 digits)"
                }
            },
            "required": ["cnic"]
        }
    },
    {
        "type": "function",
        "name": "confirm_physical_custody",
        "description": "Confirm that the customer has physical custody of their debit card. Ask customer if they have received their card.",
        "parameters": {
            "type": "object",
            "properties": {
                "cnic": {
                    "type": "string",
                    "description": "Customer's CNIC number"
                },
                "has_card": {
                    "type": "boolean",
                    "description": "True if customer confirms they have the physical card, False otherwise"
                }
            },
            "required": ["cnic", "has_card"]
        }
    },
    {
        "type": "function",
        "name": "verify_tpin",
        "description": "Verify customer's TPIN (4-digit Transaction PIN). Customer must provide their current generic TPIN.",
        "parameters": {
            "type": "object",
            "properties": {
                "cnic": {
                    "type": "string",
                    "description": "Customer's CNIC number"
                },
                "tpin": {
                    "type": "string",
                    "description": "4-digit TPIN entered by customer"
                }
            },
            "required": ["cnic", "tpin"]
        }
    },
    {
        "type": "function",
        "name": "verify_card_details",
        "description": "Verify debit card details including last 4 digits and expiry date. Both must match for successful verification.",
        "parameters": {
            "type": "object",
            "properties": {
                "cnic": {
                    "type": "string",
                    "description": "Customer's CNIC number"
                },
                "last_four_digits": {
                    "type": "string",
                    "description": "Last 4 digits of the debit card"
                },
                "expiry_date": {
                    "type": "string",
                    "description": "Card expiry date in format MM/YY or MM/YYYY (e.g., 09/27 or 09/2027)"
                }
            },
            "required": ["cnic", "last_four_digits", "expiry_date"]
        }
    },
    {
        "type": "function",
        "name": "activate_card",
        "description": "Activate the customer's debit card after all verifications are complete. Call this only after CNIC, physical custody, TPIN, and card details are verified.",
        "parameters": {
            "type": "object",
            "properties": {
                "cnic": {
                    "type": "string",
                    "description": "Customer's CNIC number"
                }
            },
            "required": ["cnic"]
        }
    },
    {
        "type": "function",
        "name": "update_customer_tpin",
        "description": "Update customer's TPIN after they set a new one through IVR. This should be called after IVR PIN generation is complete.",
        "parameters": {
            "type": "object",
            "properties": {
                "cnic": {
                    "type": "string",
                    "description": "Customer's CNIC number"
                },
                "new_tpin": {
                    "type": "string",
                    "description": "New 4-digit TPIN set by customer in IVR"
                }
            },
            "required": ["cnic", "new_tpin"]
        }
    },
    {
        "type": "function",
        "name": "transfer_to_ivr_for_pin",
        "description": "Transfer the call to IVR system for card PIN generation. Call this after card activation is successful.",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "type": "function",
        "name": "transfer_to_agent",
        "description": "Transfer the call to a human agent. Use this when: 1) Customer exceeds maximum verification attempts, 2) Customer doesn't have physical card, 3) Technical issues occur, or 4) Customer explicitly requests agent.",
        "parameters": {
            "type": "object",
            "properties": {
                "cnic": {
                    "type": "string",
                    "description": "Customer's CNIC number (if available)"
                },
                "reason": {
                    "type": "string",
                    "description": "Reason for transferring to agent (e.g., 'Max attempts exceeded', 'No physical card', 'Customer request')"
                }
            },
            "required": ["cnic", "reason"]
        }
    },
    {
        "type": "function",
        "name": "get_customer_status",
        "description": "Get the current status of customer's card activation process including verification statuses and attempts remaining.",
        "parameters": {
            "type": "object",
            "properties": {
                "cnic": {
                    "type": "string",
                    "description": "Customer's CNIC number"
                }
            },
            "required": ["cnic"]
        }
    }
]


def build_system_message(
    instructions: str = "",
    caller: str = "",
    voice: str = "sage"
) -> str:
    karachi_tz = ZoneInfo("Asia/Karachi")
    now = datetime.now(karachi_tz)

    date_str = now.strftime("%Y-%m-%d")
    day_str  = now.strftime("%A")
    time_str = now.strftime("%H:%M:%S %Z")

    date_line = (
        f"Today's date is {date_str} ({day_str}), "
        f"and the current time is {time_str}.\n\n"
    )

    language_reminder = """
🔴🔴🔴 MANDATORY LANGUAGE SWITCHING PROTOCOL 🔴🔴🔴

FOR EVERY USER MESSAGE, FOLLOW THIS EXACT PROCESS:

Step 1: ANALYZE - Look at user's CURRENT message only
Step 2: DETECT - Identify language markers (Urdu vs English vs Arabic words/script)
Step 3: DECIDE - Which language has more markers?
Step 4: RESPOND - Use ONLY that language (100% pure, no mixing)

REAL EXAMPLES OF LANGUAGE SWITCHING:

Conversation Flow:
User Message 1: "Mera balance batao"
→ Detect: Urdu words ("mera", "batao")
→ Response: MUST be in Urdu only

User Message 2: "What about my card?"
→ Detect: English words ("what", "about", "my", "card")
→ Response: MUST switch to English only

User Message 3: "ما هو رصيدي؟"
→ Detect: Arabic script and words ("ما", "رصيدي")
→ Response: MUST switch to Arabic only

User Message 4: "Give me the balance"
→ Detect: English words ("give", "me", "the", "balance")
→ Response: MUST switch to English again

User Message 5: "Dono accounts ka batao"
→ Detect: Urdu words ("dono", "ka", "batao")
→ Response: MUST switch back to Urdu

User Message 6: "أريد أن أتحدث مع ممثل"
→ Detect: Arabic script and words ("أريد", "أتحدث", "ممثل")
→ Response: MUST switch to Arabic

⚠️ IGNORE conversation history for language choice
⚠️ EACH message is analyzed independently
⚠️ Language can switch EVERY SINGLE MESSAGE
⚠️ NEVER mix languages in one response
⚠️ Arabic script (range \\u0600-\\u06FF) is a strong indicator for Arabic language

THIS IS YOUR #1 PRIORITY - CHECK LANGUAGE BEFORE EVERYTHING ELSE!
    """

    caller_line = f"Caller: {caller}\n\n" if caller else ""

    system_prompt = get_gendered_system_prompt(voice)

    if instructions:
        print(f"####################################This is a registered call with voice: {voice}")
        context = f"This is a registered caller and their details are as follows:\n{instructions}"
        return f"{language_reminder}\n{system_prompt}\n{date_line}\n{caller_line}\n{context}"
    else:
        print(f"####################################This is a non registered call with voice: {voice}")
        base = f"{language_reminder}\n{system_prompt}\n{date_line}\n{caller_line}"
        return base
