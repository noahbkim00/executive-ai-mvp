"""Role-specific question templates and generation logic."""

from typing import List, Dict, Any
from ..models.job_requirements import FunctionalArea, SeniorityLevel


class RoleSpecificQuestionGenerator:
    """Generates role-specific questions based on functional area and seniority."""
    
    def __init__(self):
        self.question_templates = {
            FunctionalArea.SALES: {
                "vp": [
                    "What specific experience should this VP have with your current sales motion (PLG, enterprise, hybrid)?",
                    "How should they balance player-coach responsibilities - what percentage should be direct selling vs. team building?",
                    "What's the most complex deal cycle they should have experience navigating in a similar market?"
                ],
                "c_suite": [
                    "What board-level metrics and reporting cadence will this person own?",
                    "How should they think about international expansion - is that on your 18-month roadmap?",
                    "What's their philosophy on sales team composition (hunters vs. farmers, inside vs. field)?"
                ]
            },
            FunctionalArea.ENGINEERING: {
                "vp": [
                    "How hands-on should this VP be with architecture decisions and code reviews?",
                    "What's the right balance between shipping features and addressing technical debt?",
                    "What experience should they have with your specific tech stack and architectural patterns?"
                ],
                "c_suite": [
                    "How will this person balance innovation with operational excellence?",
                    "What's their experience building and retaining engineering teams in competitive markets?",
                    "How should they approach build vs. buy decisions for your roadmap?"
                ]
            },
            FunctionalArea.MARKETING: {
                "vp": [
                    "What specific demand generation channels have worked for you, and where do you need expertise?",
                    "How technical should this marketing leader be given your product complexity?",
                    "What's the ideal background - product marketing, growth marketing, or brand marketing?"
                ],
                "c_suite": [
                    "How will this CMO work with sales leadership on pipeline and attribution?",
                    "What experience should they have repositioning or rebranding a company?",
                    "How important is analyst relations and PR experience for this role?"
                ]
            },
            FunctionalArea.PRODUCT: {
                "vp": [
                    "Should this VP come from a product-led growth or enterprise sales-assisted background?",
                    "What specific customer research and validation methods align with your culture?",
                    "How do you balance customer requests with product vision, and what experience reflects this?"
                ],
                "c_suite": [
                    "What's this CPO's role in pricing and packaging decisions?",
                    "How should they approach platform vs. point solution strategy?",
                    "What experience should they have with developer tools/APIs if relevant to your product?"
                ]
            },
            FunctionalArea.FINANCE: {
                "vp": [
                    "What specific financial planning and analysis experience is crucial for your stage?",
                    "How much involvement will they have with fundraising and investor relations?",
                    "What systems implementation or transformation experience would be valuable?"
                ],
                "c_suite": [
                    "What IPO or exit preparation experience is relevant to your timeline?",
                    "How should this CFO think about unit economics and path to profitability?",
                    "What board and audit committee experience is required?"
                ]
            },
            FunctionalArea.OPERATIONS: {
                "vp": [
                    "What specific operational scaling challenges are you facing (fulfillment, customer success, etc.)?",
                    "How cross-functional should this role be - touching product, engineering, and go-to-market?",
                    "What process improvement or transformation experience is most relevant?"
                ],
                "c_suite": [
                    "How will this COO complement the CEO's strengths and weaknesses?",
                    "What P&L ownership experience should they bring?",
                    "How should they approach automation and efficiency improvements?"
                ]
            }
        }
        
        # Cross-functional questions for all roles
        self.universal_questions = {
            "culture_fit": [
                "Describe a leader who failed in your organization - what characteristics should we avoid?",
                "What work style and communication preferences align best with your executive team?",
                "How do you make decisions, and what decision-making style should this person have?"
            ],
            "growth_stage": {
                "series_a": [
                    "What experience should they have taking a product from early adopters to mainstream market?",
                    "How comfortable should they be with ambiguity and rapid pivots?",
                    "What's their experience building foundational processes from scratch?"
                ],
                "series_b": [
                    "What scaling challenges have they successfully navigated at this stage before?",
                    "How should they balance growth with unit economics and efficiency?",
                    "What experience do they need building repeatable, scalable processes?"
                ],
                "series_c_plus": [
                    "What experience should they have preparing a company for IPO or acquisition?",
                    "How have they handled the complexity of multiple product lines or markets?",
                    "What's their experience with international expansion or M&A?"
                ]
            },
            "leadership": [
                "What size team will they inherit, and what reorganization experience is needed?",
                "How should they approach hiring - build internally or bring in their own team?",
                "What specific leadership challenge will test them in the first 6 months?"
            ]
        }
    
    def get_role_specific_questions(
        self, 
        functional_area: FunctionalArea, 
        seniority_level: SeniorityLevel,
        company_stage: str
    ) -> List[str]:
        """Get role-specific questions based on function and seniority."""
        questions = []
        
        # Map seniority level to template key
        seniority_key = "c_suite" if seniority_level in [
            SeniorityLevel.C_SUITE, SeniorityLevel.EVP
        ] else "vp"
        
        # Get function-specific questions
        if functional_area in self.question_templates:
            function_questions = self.question_templates[functional_area].get(
                seniority_key, []
            )
            questions.extend(function_questions)
        
        # Add growth stage questions
        stage_key = self._map_company_stage(company_stage)
        if stage_key in self.universal_questions["growth_stage"]:
            questions.extend(self.universal_questions["growth_stage"][stage_key])
        
        # Add universal culture and leadership questions
        questions.extend(self.universal_questions["culture_fit"][:1])  # Pick 1
        questions.extend(self.universal_questions["leadership"][:1])   # Pick 1
        
        return questions
    
    def _map_company_stage(self, stage: str) -> str:
        """Map company stage to question template key."""
        stage_lower = stage.lower()
        if "seed" in stage_lower or "series_a" in stage_lower:
            return "series_a"
        elif "series_b" in stage_lower:
            return "series_b"
        else:
            return "series_c_plus"
    
    def get_contextual_variables(self, job_requirements: Dict[str, Any]) -> Dict[str, str]:
        """Extract variables for question template formatting."""
        return {
            "current_arr": job_requirements.get("current_revenue", "X"),
            "target_arr": job_requirements.get("target_revenue", "Y"),
            "team_size": job_requirements.get("team_size", "the team"),
            "product_type": job_requirements.get("product_type", "your product")
        }