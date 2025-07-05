"""Service for researching company background and context for executive search."""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum

from ..agents.research_agent import CompanyResearchAgent, CompanyIntelligence
from ..config import get_settings
from ..utils.error_handler import ErrorHandler
from ..exceptions.service_exceptions import ResearchError
from ..logger import logger


class FundingStage(str, Enum):
    SEED = "seed"
    SERIES_A = "series_a"
    SERIES_B = "series_b"
    SERIES_C = "series_c"
    SERIES_D = "series_d"
    SERIES_E_PLUS = "series_e_plus"
    IPO_READY = "ipo_ready"
    PUBLIC = "public"
    UNKNOWN = "unknown"


class CompanySize(str, Enum):
    STARTUP = "startup"  # <50 employees
    SMALL = "small"      # 50-250
    MEDIUM = "medium"    # 250-1000
    LARGE = "large"      # 1000-5000
    ENTERPRISE = "enterprise"  # 5000+
    UNKNOWN = "unknown"


@dataclass
class CompanyResearch:
    """Structured company research results."""
    company_name: str
    industry: str
    funding_stage: FundingStage
    company_size: CompanySize
    key_competitors: List[str]
    recent_developments: List[str]
    regulatory_environment: str
    growth_challenges: List[str]
    leadership_needs: List[str]
    ipo_timeline: Optional[str]
    research_confidence: float  # 0-1 score


class CompanyResearchService:
    """Service for researching company background using dedicated research agent."""
    
    def __init__(self, openai_api_key: str):
        # Get settings
        settings = get_settings()
        
        # Initialize research agent
        self.research_agent = CompanyResearchAgent(
            openai_api_key=openai_api_key,
            serper_api_key=settings.serper_api_key
        )
        
        if settings.serper_api_key and settings.serper_api_key != "your_serper_api_key_here":
            logger.info("Research agent initialized with Serper API")
        else:
            logger.info("Research agent initialized with LLM fallback (add SERPER_API_KEY for real web search)")
        
    
    async def research_company(
        self,
        company_name: str,
        role_title: str
    ) -> CompanyResearch:
        """Research company background and context using research agent."""
        
        logger.info(f"Starting company research service for {company_name}, role: {role_title}")
        
        try:
            # Use research agent to gather intelligence
            logger.debug(f"Invoking research agent for {company_name}...")
            intelligence = await self.research_agent.research_company(company_name)
            
            logger.info(f"Research agent returned intelligence with confidence: {intelligence.confidence_score}")
            logger.debug(f"Intelligence details - Funding: {intelligence.funding_stage}, "
                        f"Industry: {intelligence.industry}, "
                        f"Competitors: {len(intelligence.key_competitors)}, "
                        f"News items: {len(intelligence.recent_news)}")
            
            # Convert CompanyIntelligence to CompanyResearch format
            research = self._convert_intelligence_to_research(intelligence, role_title)
            
            logger.info(f"Company research completed for {company_name} with confidence {research.research_confidence}")
            logger.debug(f"Research summary - Size: {research.company_size.value}, "
                        f"Stage: {research.funding_stage.value}, "
                        f"Leadership needs: {len(research.leadership_needs)}")
            return research
            
        except Exception as e:
            # Use standardized error handling with fallback
            return await ErrorHandler.handle_with_fallback_async(
                operation=lambda: self._raise_error(e),
                fallback_fn=lambda: self._get_fallback_research_async(company_name, role_title),
                error_message=f"Error researching company {company_name}",
                logger=logger,
                raise_on_fallback_failure=False
            )
    
    async def _raise_error(self, e: Exception):
        """Helper to re-raise exception for error handler."""
        raise e
    
    async def _get_fallback_research_async(self, company_name: str, role_title: str) -> CompanyResearch:
        """Async wrapper for fallback research."""
        return self._get_fallback_research(company_name, role_title)
    
    def _convert_intelligence_to_research(self, intelligence: CompanyIntelligence, role_title: str) -> CompanyResearch:
        """Convert CompanyIntelligence to CompanyResearch format."""
        
        logger.debug(f"Converting intelligence to research format for {intelligence.company_name}")
        
        # Map funding stage
        funding_stage_map = {
            "seed": FundingStage.SEED,
            "series_a": FundingStage.SERIES_A,
            "series_b": FundingStage.SERIES_B,
            "series_c": FundingStage.SERIES_C,
            "series_d": FundingStage.SERIES_D,
            "series_e": FundingStage.SERIES_E_PLUS,
            "pre_ipo": FundingStage.IPO_READY,
            "public": FundingStage.PUBLIC,
        }
        
        funding_stage = funding_stage_map.get(intelligence.funding_stage, FundingStage.UNKNOWN)
        if funding_stage == FundingStage.UNKNOWN:
            logger.warning(f"Unknown funding stage '{intelligence.funding_stage}' mapped to UNKNOWN")
        
        # Map company size
        company_size = self._infer_company_size(intelligence.employee_count)
        logger.debug(f"Inferred company size: {company_size.value} from employee count: {intelligence.employee_count}")
        
        # Generate leadership needs based on intelligence
        leadership_needs = self._generate_leadership_needs(intelligence, role_title)
        logger.debug(f"Generated {len(leadership_needs)} leadership needs for {role_title}")
        
        # Generate growth challenges
        growth_challenges = self._generate_growth_challenges(intelligence)
        logger.debug(f"Generated {len(growth_challenges)} growth challenges")
        
        return CompanyResearch(
            company_name=intelligence.company_name,
            industry=intelligence.industry,
            funding_stage=funding_stage,
            company_size=company_size,
            key_competitors=intelligence.key_competitors,
            recent_developments=intelligence.recent_news,
            regulatory_environment=intelligence.regulatory_context,
            growth_challenges=growth_challenges,
            leadership_needs=leadership_needs,
            ipo_timeline=intelligence.ipo_status if intelligence.ipo_status != "unknown" else None,
            research_confidence=intelligence.confidence_score
        )
    
    def _infer_company_size(self, employee_count: Optional[str]) -> CompanySize:
        """Infer company size from employee count."""
        
        if not employee_count:
            return CompanySize.UNKNOWN
        
        employee_count_lower = employee_count.lower()
        
        if any(term in employee_count_lower for term in ["1-50", "startup", "early"]):
            return CompanySize.STARTUP
        elif any(term in employee_count_lower for term in ["50-250", "small"]):
            return CompanySize.SMALL
        elif any(term in employee_count_lower for term in ["250-1000", "medium"]):
            return CompanySize.MEDIUM
        elif any(term in employee_count_lower for term in ["1000-5000", "large"]):
            return CompanySize.LARGE
        elif any(term in employee_count_lower for term in ["5000+", "enterprise"]):
            return CompanySize.ENTERPRISE
        else:
            return CompanySize.UNKNOWN
    
    def _generate_leadership_needs(self, intelligence: CompanyIntelligence, role_title: str) -> List[str]:
        """Generate leadership needs based on company intelligence."""
        
        needs = []
        
        # Stage-based needs
        if intelligence.funding_stage == "series_a":
            needs.append("Early-stage scaling experience")
        elif intelligence.funding_stage == "series_b":
            needs.append("Growth-stage leadership")
        elif intelligence.funding_stage in ["series_c", "series_d", "series_e"]:
            needs.append("Late-stage scaling experience")
        elif intelligence.funding_stage == "pre_ipo":
            needs.append("IPO preparation experience")
        elif intelligence.funding_stage == "public":
            needs.append("Public company leadership")
        
        # Industry-specific needs
        if "fintech" in intelligence.industry.lower() or "financial" in intelligence.industry.lower():
            needs.append("Financial services experience")
            needs.append("Regulatory compliance background")
        
        if "saas" in intelligence.business_model.lower():
            needs.append("SaaS scaling experience")
        
        # Competitive needs
        big_tech_competitors = ["Google", "Microsoft", "Amazon", "Apple", "Meta", "Salesforce"]
        if any(comp in big_tech_competitors for comp in intelligence.key_competitors):
            needs.append("Experience competing against big tech")
        
        return needs
    
    def _generate_growth_challenges(self, intelligence: CompanyIntelligence) -> List[str]:
        """Generate growth challenges based on company intelligence."""
        
        challenges = []
        
        # Stage-based challenges
        if intelligence.funding_stage in ["series_a", "series_b"]:
            challenges.append("Scaling operations and team")
        elif intelligence.funding_stage in ["series_c", "series_d"]:
            challenges.append("Market expansion and competitive positioning")
        elif intelligence.funding_stage == "pre_ipo":
            challenges.append("IPO readiness and governance")
        
        # Industry challenges
        if "fintech" in intelligence.industry.lower():
            challenges.append("Regulatory compliance and partnerships")
        
        # Competitive challenges
        if intelligence.key_competitors:
            challenges.append("Competitive differentiation")
        
        return challenges
    
    def _get_fallback_research(self, company_name: str, role_title: str) -> CompanyResearch:
        """Provide fallback research when analysis fails."""
        
        logger.warning(f"Using fallback research for {company_name} - research agent failed")
        
        # Basic inference based on company name patterns
        industry = self._infer_industry(company_name)
        logger.debug(f"Inferred industry '{industry}' from company name")
        
        logger.info(f"Created fallback research with low confidence (0.2) for {company_name}")
        
        return CompanyResearch(
            company_name=company_name,
            industry=industry,
            funding_stage=FundingStage.UNKNOWN,
            company_size=CompanySize.UNKNOWN,
            key_competitors=[],
            recent_developments=[],
            regulatory_environment="",
            growth_challenges=["Scaling operations", "Market competition"],
            leadership_needs=[f"Experience relevant to {role_title} in {industry}"],
            ipo_timeline=None,
            research_confidence=0.2
        )
    
    def _infer_industry(self, company_name: str) -> str:
        """Basic industry inference from company name."""
        name_lower = company_name.lower()
        
        if any(term in name_lower for term in ["tech", "ai", "software", "data", "cloud"]):
            return "Technology"
        elif any(term in name_lower for term in ["fin", "bank", "pay", "crypto"]):
            return "Financial Services"
        elif any(term in name_lower for term in ["health", "bio", "medical", "pharma"]):
            return "Healthcare"
        elif any(term in name_lower for term in ["energy", "solar", "green"]):
            return "Energy"
        else:
            return "General Business"
    
    def get_research_insights(self, research: CompanyResearch, role_title: str) -> Dict[str, Any]:
        """Extract key insights for question generation."""
        
        logger.debug(f"Extracting research insights for {research.company_name}")
        
        insights = {
            "stage_insights": self._get_stage_insights(research.funding_stage),
            "industry_insights": self._get_industry_insights(research.industry),
            "competitive_insights": self._get_competitive_insights(research.key_competitors),
            "regulatory_insights": self._get_regulatory_insights(research.regulatory_environment),
            "growth_insights": research.growth_challenges,
            "leadership_insights": research.leadership_needs,
            "ipo_insights": self._get_ipo_insights(research.ipo_timeline),
            "size_insights": self._get_size_insights(research.company_size)
        }
        
        total_insights = sum(len(v) if isinstance(v, list) else 1 for v in insights.values() if v)
        logger.info(f"Extracted {total_insights} total insights across {len(insights)} categories")
        
        return insights
    
    def _get_stage_insights(self, stage: FundingStage) -> List[str]:
        """Get insights based on funding stage."""
        stage_map = {
            FundingStage.SEED: ["Early stage execution", "Product-market fit", "Initial team building"],
            FundingStage.SERIES_A: ["Scaling initial success", "Building systems", "Early GTM"],
            FundingStage.SERIES_B: ["Market expansion", "Operational scaling", "Team leadership"],
            FundingStage.SERIES_C: ["International expansion", "Market dominance", "IPO preparation"],
            FundingStage.SERIES_D: ["Late-stage scaling", "Acquisition strategy", "Public readiness"],
            FundingStage.SERIES_E_PLUS: ["IPO preparation", "Public company processes", "Enterprise sales"],
            FundingStage.IPO_READY: ["Public company experience", "Regulatory compliance", "Investor relations"],
            FundingStage.PUBLIC: ["Public company operations", "Quarterly performance", "Board experience"]
        }
        return stage_map.get(stage, ["General business leadership"])
    
    def _get_industry_insights(self, industry: str) -> List[str]:
        """Get insights based on industry."""
        industry_lower = industry.lower()
        
        if "tech" in industry_lower or "software" in industry_lower:
            return ["Technical product understanding", "Developer ecosystem", "Platform scaling"]
        elif "fintech" in industry_lower or "financial" in industry_lower:
            return ["Financial services regulation", "Compliance experience", "Banking partnerships"]
        elif "health" in industry_lower:
            return ["Healthcare regulation", "FDA experience", "Clinical trials"]
        else:
            return ["Industry-specific experience"]
    
    def _get_competitive_insights(self, competitors: List[str]) -> List[str]:
        """Get insights based on competitive landscape."""
        if not competitors:
            return []
        
        insights = [f"Experience competing against {comp}" for comp in competitors[:3]]
        
        # Check for big tech competitors
        big_tech = ["Google", "Microsoft", "Amazon", "Apple", "Meta", "Salesforce"]
        if any(comp in big_tech for comp in competitors):
            insights.append("Experience selling against big tech incumbents")
        
        return insights
    
    def _get_regulatory_insights(self, regulatory_env: str) -> List[str]:
        """Get insights based on regulatory environment."""
        if not regulatory_env or regulatory_env.lower() in ["none", "minimal"]:
            return []
        
        return ["Regulatory compliance experience", "Government relations"]
    
    def _get_ipo_insights(self, ipo_timeline: Optional[str]) -> List[str]:
        """Get insights based on IPO timeline."""
        if not ipo_timeline:
            return []
        
        return ["IPO preparation experience", "Public company readiness", "SEC compliance"]
    
    def _get_size_insights(self, size: CompanySize) -> List[str]:
        """Get insights based on company size."""
        size_map = {
            CompanySize.STARTUP: ["Startup environment", "Resource constraints", "Rapid change"],
            CompanySize.SMALL: ["Small company scaling", "Hands-on leadership", "Culture building"],
            CompanySize.MEDIUM: ["Mid-market leadership", "Process building", "Team scaling"],
            CompanySize.LARGE: ["Enterprise leadership", "Complex organizations", "Strategic planning"],
            CompanySize.ENTERPRISE: ["Large enterprise", "Board interaction", "Global operations"]
        }
        return size_map.get(size, ["Organization leadership"])