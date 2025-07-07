"""Company research node for LangGraph workflow."""

import asyncio
from typing import Dict, Any, List
from datetime import datetime
from dataclasses import asdict
from langgraph.prebuilt import ToolExecutor

from ..state_schema import ExecutiveSearchState
from .base_node import BaseNode
from ..tools.research_tools import (
    company_funding_search,
    company_news_search,
    company_industry_search,
    company_leadership_search,
    company_size_search,
    company_ipo_search,
    analyze_company_intelligence,
    RESEARCH_TOOLS
)
from ...services.company_research_service import (
    CompanyResearch, FundingStage, CompanySize
)
from ...logger import logger


class CompanyResearchNode(BaseNode):
    """LangGraph node for company research."""
    
    def __init__(self):
        """Initialize the research node."""
        super().__init__("company_research")
        
        # Initialize tool executor with research tools
        self.tool_executor = ToolExecutor(RESEARCH_TOOLS)
    
    async def execute(self, state: ExecutiveSearchState) -> ExecutiveSearchState:
        """Execute company research logic."""
        try:
            logger.info(f"Starting company research for conversation {state['conversation_id']}")
            
            # Extract company info from state
            company_info = state.get("company_info")
            job_requirements = state.get("job_requirements")
            
            if not company_info or not company_info.get("name"):
                logger.warning("No company information available for research")
                updated_state = self._update_state_metadata(state)
                updated_state.update({
                    "company_research": None,
                    "research_insights": None,
                    "next_action": "generate_questions",
                    "error_message": None
                })
                return updated_state
            
            company_name = company_info["name"]
            role_title = job_requirements.get("title", "Executive") if job_requirements else "Executive"
            
            # Conduct comprehensive research
            research_result = await self._research_company(company_name, role_title)
            
            # Generate research insights
            research_insights = self._get_research_insights(research_result, role_title)
            
            # Update state with research results
            updated_state = self._update_state_metadata(state)
            updated_state.update({
                "company_research": asdict(research_result) if research_result else None,
                "research_insights": research_insights,
                "next_action": "generate_questions",
                "error_message": None
            })
            
            logger.info(f"Company research completed for {company_name} with confidence {research_result.research_confidence if research_result else 0.1}")
            return updated_state
            
        except Exception as e:
            logger.error(f"Error in company research: {str(e)}", exc_info=True)
            return self._handle_error(state, e)
    
    async def _research_company(self, company_name: str, role_title: str) -> CompanyResearch:
        """Conduct comprehensive company research using tools (identical logic to research service)."""
        
        logger.info(f"Starting research service for {company_name}, role: {role_title}")
        
        try:
            # Execute research tools in parallel (identical to research agent)
            logger.info(f"Conducting parallel searches for {company_name}")
            
            research_tasks = [
                company_funding_search.ainvoke({"company_name": company_name}),
                company_news_search.ainvoke({"company_name": company_name}),
                company_industry_search.ainvoke({"company_name": company_name}),
                company_leadership_search.ainvoke({"company_name": company_name}),
                company_size_search.ainvoke({"company_name": company_name}),
                company_ipo_search.ainvoke({"company_name": company_name})
            ]
            
            # Wait for all searches to complete
            search_results = await asyncio.gather(*research_tasks, return_exceptions=True)
            
            # Process search results
            processed_results = {}
            successful_searches = 0
            failed_searches = 0
            
            categories = ["funding", "news", "industry", "leadership", "size", "ipo"]
            for i, category in enumerate(categories):
                result = search_results[i]
                if isinstance(result, Exception):
                    failed_searches += 1
                    logger.error(f"Search failed for {category}: {str(result)}")
                    processed_results[category] = {"results": []}
                else:
                    successful_searches += 1
                    processed_results[category] = result
            
            logger.info(f"Search summary - Successful: {successful_searches}, Failed: {failed_searches}")
            
            # Analyze results using intelligence tool
            logger.debug(f"Invoking intelligence analysis for {company_name}...")
            intelligence_data = await analyze_company_intelligence.ainvoke({
                "company_name": company_name,
                "search_results": processed_results
            })
            
            logger.info(f"Research analysis returned intelligence with confidence: {intelligence_data.get('confidence_score', 0.5)}")
            
            # Convert to CompanyResearch format (identical to research service)
            research = self._convert_intelligence_to_research(intelligence_data, role_title)
            
            logger.info(f"Company research completed for {company_name} with confidence {research.research_confidence}")
            return research
            
        except Exception as e:
            logger.error(f"Error researching company {company_name}: {str(e)}", exc_info=True)
            # Return fallback research (identical to research service)
            return self._get_fallback_research(company_name, role_title)
    
    def _convert_intelligence_to_research(self, intelligence_data: Dict[str, Any], role_title: str) -> CompanyResearch:
        """Convert intelligence data to CompanyResearch format (identical to research service)."""
        
        company_name = intelligence_data.get("company_name", "Unknown Company")
        logger.debug(f"Converting intelligence to research format for {company_name}")
        
        # Map funding stage (identical logic)
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
        
        funding_stage = funding_stage_map.get(
            intelligence_data.get("funding_stage", "unknown"), 
            FundingStage.UNKNOWN
        )
        
        # Map company size (identical logic)
        company_size = self._infer_company_size(intelligence_data.get("employee_count"))
        
        # Generate leadership needs (identical logic)
        leadership_needs = self._generate_leadership_needs(intelligence_data, role_title)
        
        # Generate growth challenges (identical logic)
        growth_challenges = self._generate_growth_challenges(intelligence_data)
        
        return CompanyResearch(
            company_name=company_name,
            industry=intelligence_data.get("industry", "Unknown"),
            funding_stage=funding_stage,
            company_size=company_size,
            key_competitors=intelligence_data.get("key_competitors", []),
            recent_developments=intelligence_data.get("recent_news", []),
            regulatory_environment=intelligence_data.get("regulatory_context", ""),
            growth_challenges=growth_challenges,
            leadership_needs=leadership_needs,
            ipo_timeline=intelligence_data.get("ipo_status") if intelligence_data.get("ipo_status") != "unknown" else None,
            research_confidence=intelligence_data.get("confidence_score", 0.5)
        )
    
    def _infer_company_size(self, employee_count: str) -> CompanySize:
        """Infer company size from employee count (identical to research service)."""
        
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
    
    def _generate_leadership_needs(self, intelligence_data: Dict[str, Any], role_title: str) -> List[str]:
        """Generate leadership needs (identical to research service)."""
        
        needs = []
        funding_stage = intelligence_data.get("funding_stage", "unknown")
        industry = intelligence_data.get("industry", "")
        business_model = intelligence_data.get("business_model", "")
        key_competitors = intelligence_data.get("key_competitors", [])
        
        # Stage-based needs (identical logic)
        if funding_stage == "series_a":
            needs.append("Early-stage scaling experience")
        elif funding_stage == "series_b":
            needs.append("Growth-stage leadership")
        elif funding_stage in ["series_c", "series_d", "series_e"]:
            needs.append("Late-stage scaling experience")
        elif funding_stage == "pre_ipo":
            needs.append("IPO preparation experience")
        elif funding_stage == "public":
            needs.append("Public company leadership")
        
        # Industry-specific needs (identical logic)
        if "fintech" in industry.lower() or "financial" in industry.lower():
            needs.append("Financial services experience")
            needs.append("Regulatory compliance background")
        
        if "saas" in business_model.lower():
            needs.append("SaaS scaling experience")
        
        # Competitive needs (identical logic)
        big_tech_competitors = ["Google", "Microsoft", "Amazon", "Apple", "Meta", "Salesforce"]
        if any(comp in big_tech_competitors for comp in key_competitors):
            needs.append("Experience competing against big tech")
        
        return needs
    
    def _generate_growth_challenges(self, intelligence_data: Dict[str, Any]) -> List[str]:
        """Generate growth challenges (identical to research service)."""
        
        challenges = []
        funding_stage = intelligence_data.get("funding_stage", "unknown")
        industry = intelligence_data.get("industry", "")
        key_competitors = intelligence_data.get("key_competitors", [])
        
        # Stage-based challenges (identical logic)
        if funding_stage in ["series_a", "series_b"]:
            challenges.append("Scaling operations and team")
        elif funding_stage in ["series_c", "series_d"]:
            challenges.append("Market expansion and competitive positioning")
        elif funding_stage == "pre_ipo":
            challenges.append("IPO readiness and governance")
        
        # Industry challenges (identical logic)
        if "fintech" in industry.lower():
            challenges.append("Regulatory compliance and partnerships")
        
        # Competitive challenges (identical logic)
        if key_competitors:
            challenges.append("Competitive differentiation")
        
        return challenges
    
    def _get_fallback_research(self, company_name: str, role_title: str) -> CompanyResearch:
        """Provide fallback research (identical to research service)."""
        
        logger.warning(f"Using fallback research for {company_name} - research failed")
        
        # Basic inference based on company name patterns (identical logic)
        industry = self._infer_industry(company_name)
        
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
        """Basic industry inference (identical to research service)."""
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
    
    def _get_research_insights(self, research: CompanyResearch, role_title: str) -> Dict[str, Any]:
        """Extract key insights for question generation (identical to research service)."""
        
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
    
    # All insight generation methods identical to research service
    def _get_stage_insights(self, stage: FundingStage) -> List[str]:
        """Get insights based on funding stage (identical to research service)."""
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
        """Get insights based on industry (identical to research service)."""
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
        """Get insights based on competitive landscape (identical to research service)."""
        if not competitors:
            return []
        
        insights = [f"Experience competing against {comp}" for comp in competitors[:3]]
        
        # Check for big tech competitors
        big_tech = ["Google", "Microsoft", "Amazon", "Apple", "Meta", "Salesforce"]
        if any(comp in big_tech for comp in competitors):
            insights.append("Experience selling against big tech incumbents")
        
        return insights
    
    def _get_regulatory_insights(self, regulatory_env: str) -> List[str]:
        """Get insights based on regulatory environment (identical to research service)."""
        if not regulatory_env or regulatory_env.lower() in ["none", "minimal"]:
            return []
        
        return ["Regulatory compliance experience", "Government relations"]
    
    def _get_ipo_insights(self, ipo_timeline: str) -> List[str]:
        """Get insights based on IPO timeline (identical to research service)."""
        if not ipo_timeline:
            return []
        
        return ["IPO preparation experience", "Public company readiness", "SEC compliance"]
    
    def _get_size_insights(self, size: CompanySize) -> List[str]:
        """Get insights based on company size (identical to research service)."""
        size_map = {
            CompanySize.STARTUP: ["Startup environment", "Resource constraints", "Rapid change"],
            CompanySize.SMALL: ["Small company scaling", "Hands-on leadership", "Culture building"],
            CompanySize.MEDIUM: ["Mid-market leadership", "Process building", "Team scaling"],
            CompanySize.LARGE: ["Enterprise leadership", "Complex organizations", "Strategic planning"],
            CompanySize.ENTERPRISE: ["Large enterprise", "Board interaction", "Global operations"]
        }
        return size_map.get(size, ["Organization leadership"])


# Factory function for node creation
def create_company_research_node() -> CompanyResearchNode:
    """Factory function to create company research node."""
    return CompanyResearchNode()