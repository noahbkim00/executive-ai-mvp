"""Prompts for generating intelligent follow-up questions for executive search."""

from langchain_core.prompts import ChatPromptTemplate

# System prompt for question generation
QUESTION_GENERATION_SYSTEM_PROMPT = """You are an expert executive search consultant with 20+ years of experience placing C-suite and VP-level executives. You specialize in uncovering the hidden, subjective requirements that make the difference between a good hire and a perfect hire.

Your task is to generate 3-5 insightful follow-up questions based on the initial job requirements and company context provided. These questions should:

1. NEVER ask about information that can be researched online (company size, revenue, industry facts, etc.)
2. Focus on subjective, experiential, and cultural requirements
3. Uncover potential deal-breakers or must-haves not mentioned initially
4. Be specific to the role and company context
5. Help identify candidates who will thrive, not just qualify

Categories to explore:
- Leadership style and team dynamics
- Specific situational experiences (turnarounds, scaling, etc.)
- Cultural fit indicators and work style preferences  
- Hidden technical or domain expertise requirements
- Compensation expectations and negotiation parameters
- Personal motivations and career trajectory alignment

Output format: Return a JSON array of question objects with this structure:
[
    {{
        "question_id": "q1",
        "question": "The actual question to ask",
        "category": "leadership|experience|culture|expertise|compensation|motivation",
        "rationale": "Why this question matters for this specific search"
    }}
]
"""

# Main question generation prompt
QUESTION_GENERATION_PROMPT = ChatPromptTemplate.from_messages([
    ("system", QUESTION_GENERATION_SYSTEM_PROMPT),
    ("human", """Based on this executive search context, generate 3-5 insightful follow-up questions:

Company: {company_name}
Industry: {industry}
Stage: {company_stage}
Business Model: {business_model}

Role: {job_title}
Seniority: {seniority_level}
Function: {functional_area}

Initial Requirements:
{initial_requirements}

Growth Context: {growth_context}

Key Challenges: {key_challenges}

Remember:
- DO NOT ask about anything that can be Googled
- Focus on subjective qualities and experiences
- Make questions specific to this company's situation
- Uncover hidden requirements that affect candidate success

Generate the questions as a JSON array.""")
])

# Validation prompt to check if questions are appropriate
QUESTION_VALIDATION_PROMPT = ChatPromptTemplate.from_template("""Review this question and determine if it asks for information that could be researched online:

Question: {question}

Rules:
- Questions about company metrics (revenue, employee count, funding) = RESEARCHABLE
- Questions about public company facts = RESEARCHABLE  
- Questions about personal experience = NOT RESEARCHABLE
- Questions about preferences and style = NOT RESEARCHABLE
- Questions about specific situations = NOT RESEARCHABLE

Answer with just "RESEARCHABLE" or "NOT_RESEARCHABLE".""")

# Role-specific question templates for different functional areas
SALES_EXECUTIVE_QUESTIONS = {
    "scaling": "What specific strategies has this person used to scale a sales team from ${current_arr}M to ${target_arr}M ARR?",
    "enterprise_experience": "Describe their experience closing enterprise deals - what's the largest deal they've personally quarterbacked?",
    "channel_strategy": "How important is channel/partnership experience vs. direct sales for this role?",
    "sales_methodology": "Is there a specific sales methodology (MEDDIC, Challenger, etc.) that aligns with your culture?",
    "team_structure": "What's your vision for the sales org structure, and what experience should they have building similar structures?"
}

ENGINEERING_EXECUTIVE_QUESTIONS = {
    "technical_depth": "How technical should this person be - architect-level coding ability or pure people leadership?",
    "scaling_infrastructure": "What specific infrastructure scaling challenges will they face in the next 18 months?",
    "team_composition": "What's the current team composition, and what experience do they need rebalancing or restructuring teams?",
    "innovation_vs_execution": "Is this role more about innovation and new products, or scaling and reliability?",
    "external_presence": "How important is their external presence (conference speaking, open source, thought leadership)?"
}

MARKETING_EXECUTIVE_QUESTIONS = {
    "demand_gen_vs_brand": "What's the balance between demand generation and brand building in this role?",
    "product_marketing": "How closely will they work with product, and do they need product marketing experience?",
    "content_strategy": "What content creation and storytelling experience is crucial for your market?",
    "martech_stack": "Are there specific marketing technologies or platforms they must have experience with?",
    "category_creation": "Are you creating a new category or competing in an established one?"
}

FINANCE_EXECUTIVE_QUESTIONS = {
    "fundraising": "What fundraising experience is required - Series B, C, debt, or IPO preparation?",
    "board_experience": "How much board interaction will this role have, and what board reporting experience is needed?",
    "operational_finance": "Is this more strategic finance or operational finance focused?",
    "m&a_experience": "Will they be involved in M&A activity, and what transaction experience is required?",
    "systems_transformation": "What financial systems or ERP transformation experience would be valuable?"
}

# General executive questions applicable across functions
GENERAL_EXECUTIVE_QUESTIONS = {
    "failure_learning": "Tell me about a specific failure or setback this person should have experienced and learned from.",
    "leadership_crucible": "What leadership crucible moment should they have navigated (layoffs, pivot, crisis)?",
    "cultural_antibodies": "What types of leaders have failed in your culture, and what traits should we screen against?",
    "first_90_days": "What specific outcomes must they achieve in their first 90 days to be considered successful?",
    "deal_breakers": "Are there any non-negotiable background requirements we haven't discussed (competitor experience, security clearance, location flexibility)?"
}