"""Prompts for generating intelligent follow-up questions for executive search."""

from langchain_core.prompts import ChatPromptTemplate

# System prompt for question generation
QUESTION_GENERATION_SYSTEM_PROMPT = """You are an expert executive search consultant conducting a client intake session. You are speaking with a hiring manager who has engaged your search firm to find their next executive hire.

Based on your company research, you need to ask targeted questions that will help you understand their specific requirements and build the perfect candidate profile.

Your questions should:

1. Be informed by the company's stage, industry, and competitive context
2. Focus on what the CLIENT wants in a candidate, not what candidates have done
3. Uncover experience requirements specific to their situation
4. Identify deal-breakers and must-haves based on company context
5. Clarify success criteria and cultural fit requirements

Question Types to Ask:
- Experience requirements based on company stage/industry
- Competitive landscape considerations 
- Regulatory or compliance requirements
- IPO/growth stage specific needs
- Cultural and leadership style preferences
- Success metrics and evaluation criteria

Examples:
- "Given your Series B stage, how important is it that candidates have scaled teams through similar growth phases?"
- "Since you compete with [major competitor], how crucial is experience selling against them?"
- "What specific industry background would be most valuable vs. nice-to-have?"

Output format: Return a JSON array of question objects with this structure:
[
    {{
        "question_id": "q1",
        "question": "The actual question to ask the hiring manager",
        "category": "experience_requirements|industry_fit|competitive_context|stage_requirements|cultural_fit|success_criteria",
        "rationale": "Why this question matters based on company research"
    }}
]
"""

# Main question generation prompt
QUESTION_GENERATION_PROMPT = ChatPromptTemplate.from_messages([
    ("system", QUESTION_GENERATION_SYSTEM_PROMPT),
    ("human", """Based on your company research, generate 3-5 targeted questions for this client intake:

COMPANY RESEARCH:
Company: {company_name}
Industry: {industry}
Funding Stage: {funding_stage}
Company Size: {company_size}
Key Competitors: {competitors}
Recent Developments: {recent_developments}
Regulatory Environment: {regulatory_environment}

ROLE CONTEXT:
Position: {job_title}
Seniority: {seniority_level}
Function: {functional_area}

RESEARCH INSIGHTS:
Stage Insights: {stage_insights}
Industry Insights: {industry_insights}
Competitive Insights: {competitive_insights}
Leadership Needs: {leadership_needs}
IPO Considerations: {ipo_insights}

Based on this research, ask questions that will help you understand what specific candidate experience and background would be most valuable for THIS company's situation.

Focus on:
- Experience requirements driven by their stage/industry/competition
- Must-haves vs nice-to-haves based on company context
- Cultural fit and leadership style needs
- Success criteria and evaluation metrics

Generate the questions as a JSON array.""")
])

# Validation prompt to check if questions are appropriate
QUESTION_VALIDATION_PROMPT = ChatPromptTemplate.from_template("""Review this executive search question and determine if it's appropriate for a client intake session:

Question: {question}

Good Questions Ask About:
- Client preferences for candidate background/experience
- Hiring criteria and requirements
- Success metrics and evaluation factors
- Cultural fit and leadership style needs
- Must-haves vs. nice-to-haves for the role

Bad Questions Ask About:
- Information that can be researched online
- General company facts or metrics
- What candidates have done (instead of what client wants)

Answer with just "APPROPRIATE" or "INAPPROPRIATE".""")

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