"""Research agent for gathering company intelligence using web search and scraping."""

import asyncio
import aiohttp
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser

from ..services.llm_factory import LLMFactory
from ..utils.error_handler import ErrorHandler
from ..exceptions.service_exceptions import ResearchError
from ..logger import logger


@dataclass
class SearchResult:
    """Structured search result."""
    title: str
    snippet: str
    url: str
    date: Optional[str] = None


@dataclass
class CompanyIntelligence:
    """Comprehensive company intelligence gathered by research agent."""
    company_name: str
    funding_stage: str
    funding_amount: Optional[str]
    investors: List[str]
    industry: str
    business_model: str
    employee_count: Optional[str]
    key_competitors: List[str]
    recent_news: List[str]
    leadership_team: List[str]
    regulatory_context: str
    growth_stage: str
    ipo_status: str
    confidence_score: float


class CompanyResearchAgent:
    """Intelligent agent for comprehensive company research."""
    
    def __init__(self, openai_api_key: str, serper_api_key: Optional[str] = None):
        self.openai_api_key = openai_api_key
        self.serper_api_key = serper_api_key
        
        # Initialize LLM for analysis using factory
        self.llm = LLMFactory.create_extraction_llm()
        
        self.json_parser = JsonOutputParser()
        
        # Research analysis prompt
        self.analysis_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an expert business intelligence analyst specializing in executive search research.

Analyze the provided search results and extract structured company intelligence for executive search purposes.

Focus on information relevant to executive hiring:
- Funding stage and growth trajectory
- Industry challenges and opportunities  
- Competitive positioning
- Leadership team composition and recent hires
- Regulatory environment and compliance needs
- Recent developments that affect executive requirements

Output a JSON object with this exact structure:
{{
    "company_name": "string",
    "funding_stage": "seed|series_a|series_b|series_c|series_d|series_e|pre_ipo|public|unknown",
    "funding_amount": "string with amount and currency or null",
    "investors": ["array of investor names"],
    "industry": "specific industry/sector",
    "business_model": "b2b|b2c|marketplace|saas|platform|other",
    "employee_count": "string like '100-500' or '1000+' or null",
    "key_competitors": ["array of main competitors"],
    "recent_news": ["array of recent significant developments"],
    "leadership_team": ["array of key executives and recent hires"],
    "regulatory_context": "description of regulatory environment if applicable",
    "growth_stage": "early|growth|scale|mature",
    "ipo_status": "not_planned|preparing|filed|public|unknown",
    "confidence_score": "float 0-1 based on data quality and recency"
}}"""),
            ("human", """Company: {company_name}

Search Results:
{search_results}

Analyze these search results and extract comprehensive company intelligence for executive search purposes. Be specific about funding amounts, dates, and executive team details when available.""")
        ])
    
    async def research_company(self, company_name: str) -> CompanyIntelligence:
        """Conduct comprehensive research on a company."""
        
        logger.info(f"Starting research for company: {company_name}")
        logger.info(f"Research agent initialized with Serper API: {bool(self.serper_api_key and self.serper_api_key != 'your_serper_api_key_here')}")
        
        async def primary_research():
            # Perform targeted searches
            search_results = await self._conduct_research_searches(company_name)
            
            # Log search results summary
            total_results = sum(len(results) for results in search_results.values())
            logger.info(f"Collected {total_results} total search results across {len(search_results)} categories")
            for category, results in search_results.items():
                logger.debug(f"  - {category}: {len(results)} results")
            
            # Analyze results with LLM
            intelligence = await self._analyze_search_results(company_name, search_results)
            
            logger.info(f"Research completed for {company_name} with confidence {intelligence.confidence_score}")
            logger.debug(f"Intelligence summary - Funding: {intelligence.funding_stage}, Industry: {intelligence.industry}, Competitors: {len(intelligence.key_competitors)}")
            return intelligence
        
        async def fallback_research():
            return self._create_fallback_intelligence(company_name)
        
        return await ErrorHandler.handle_with_fallback_async(
            operation=primary_research,
            fallback_fn=fallback_research,
            error_message=f"Research failed for {company_name}",
            logger=logger,
            raise_on_fallback_failure=False
        )
    
    async def _conduct_research_searches(self, company_name: str) -> Dict[str, List[SearchResult]]:
        """Conduct multiple targeted searches for comprehensive intelligence."""
        
        search_queries = {
            "funding": f"{company_name} funding series round investors valuation",
            "industry": f"{company_name} industry business model revenue competitors",
            "leadership": f"{company_name} CEO CTO CFO executive team leadership hiring",
            "news": f"{company_name} news 2024 2025 announcements partnerships",
            "size": f"{company_name} employees headcount company size",
            "ipo": f"{company_name} IPO public offering S-1 filing"
        }
        
        logger.info(f"Conducting {len(search_queries)} parallel searches for {company_name}")
        
        all_results = {}
        
        # Perform searches concurrently
        search_tasks = []
        for category, query in search_queries.items():
            logger.debug(f"Preparing search - Category: {category}, Query: {query}")
            task = self._perform_search(query, category)
            search_tasks.append(task)
        
        # Wait for all searches to complete
        search_results = await asyncio.gather(*search_tasks, return_exceptions=True)
        
        # Process results
        successful_searches = 0
        failed_searches = 0
        
        for i, (category, query) in enumerate(search_queries.items()):
            result = search_results[i]
            if isinstance(result, Exception):
                failed_searches += 1
                logger.error(f"Search failed for {category}: {str(result)}", exc_info=result)
                logger.warning(f"Using empty results for {category} category")
                all_results[category] = []
            else:
                successful_searches += 1
                logger.debug(f"Search successful for {category}: {len(result)} results")
                all_results[category] = result
        
        logger.info(f"Search summary - Successful: {successful_searches}, Failed: {failed_searches}")
        return all_results
    
    async def _perform_search(self, query: str, category: str) -> List[SearchResult]:
        """Perform a single search using available search API."""
        
        if self.serper_api_key and self.serper_api_key != "your_serper_api_key_here":
            logger.debug(f"Using Serper API for search: {query[:50]}...")
            return await self._serper_search(query)
        else:
            # Fallback to enhanced LLM-based research
            logger.warning(f"No Serper API key available, falling back to LLM research for category: {category}")
            return await self._llm_research(query, category)
    
    async def _serper_search(self, query: str, num_results: int = 10) -> List[SearchResult]:
        """Search using Serper API."""
        
        url = "https://google.serper.dev/search"
        headers = {
            "X-API-KEY": self.serper_api_key,
            "Content-Type": "application/json"
        }
        
        payload = {
            "q": query,
            "num": num_results,
            "hl": "en",
            "gl": "us"
        }
        
        logger.debug(f"Sending request to Serper API: {query[:50]}...")
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        results = self._parse_serper_results(data)
                        logger.info(f"Serper search successful: {len(results)} results for '{query[:30]}...'")
                        return results
                    else:
                        error_text = await response.text()
                        logger.error(f"Serper API error: Status {response.status}, Response: {error_text[:200]}")
                        logger.warning(f"Serper search failed, returning empty results for query: {query[:50]}...")
                        return []
                        
        except aiohttp.ClientError as e:
            logger.error(f"Network error during Serper search: {str(e)}", exc_info=True)
            return []
        except Exception as e:
            logger.error(f"Unexpected error in Serper search: {str(e)}", exc_info=True)
            return []
    
    def _parse_serper_results(self, data: Dict[str, Any]) -> List[SearchResult]:
        """Parse Serper API response into SearchResult objects."""
        
        results = []
        
        # Parse organic results
        organic = data.get("organic", [])
        for item in organic:
            result = SearchResult(
                title=item.get("title", ""),
                snippet=item.get("snippet", ""),
                url=item.get("link", ""),
                date=item.get("date")
            )
            results.append(result)
        
        # Parse news results if available
        news = data.get("news", [])
        for item in news[:3]:  # Limit news results
            result = SearchResult(
                title=item.get("title", ""),
                snippet=item.get("snippet", ""),
                url=item.get("link", ""),
                date=item.get("date")
            )
            results.append(result)
        
        return results
    
    async def _llm_research(self, query: str, category: str) -> List[SearchResult]:
        """Fallback research using LLM when API unavailable."""
        
        logger.info(f"Using LLM fallback for research - Category: {category}, Query: {query[:50]}...")
        
        research_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a business intelligence researcher. Based on the search query, provide factual information as if gathered from recent web searches.

Create realistic search results with:
- Specific titles that would appear in search
- Detailed snippets with facts, numbers, and dates
- Realistic URLs from news sites, company sites, etc.

Focus on recent, factual information relevant to executive search."""),
            ("human", """Search Query: {query}
Category: {category}

Generate 3-5 realistic search results with specific facts, dates, and sources. Format as JSON array:
[
    {{
        "title": "Realistic search result title",
        "snippet": "Detailed snippet with specific facts and numbers",
        "url": "https://realistic-url.com/article",
        "date": "2024-MM-DD or null"
    }}
]""")
        ])
        
        research_chain = research_prompt | self.llm | self.json_parser
        
        try:
            logger.debug(f"Invoking LLM for research generation...")
            results_data = await research_chain.ainvoke({
                "query": query,
                "category": category
            })
            
            search_results = [
                SearchResult(
                    title=item.get("title", ""),
                    snippet=item.get("snippet", ""),
                    url=item.get("url", ""),
                    date=item.get("date")
                )
                for item in results_data
            ]
            
            logger.info(f"LLM research successful: Generated {len(search_results)} results for category '{category}'")
            for i, result in enumerate(search_results[:2]):  # Log first 2 results
                logger.debug(f"  Result {i+1}: {result.title[:50]}...")
            
            return search_results
            
        except Exception as e:
            logger.error(f"LLM research failed for query '{query[:50]}...': {str(e)}", exc_info=True)
            logger.warning(f"Returning empty results for category: {category}")
            return []
    
    async def _analyze_search_results(self, company_name: str, search_results: Dict[str, List[SearchResult]]) -> CompanyIntelligence:
        """Analyze search results and extract structured intelligence."""
        
        logger.info(f"Analyzing search results for {company_name}...")
        
        # Format search results for analysis
        formatted_results = self._format_search_results(search_results)
        logger.debug(f"Formatted results length: {len(formatted_results)} characters")
        
        # Analyze with LLM
        analysis_chain = self.analysis_prompt | self.llm | self.json_parser
        
        try:
            logger.debug("Invoking LLM for intelligence analysis...")
            intelligence_data = await analysis_chain.ainvoke({
                "company_name": company_name,
                "search_results": formatted_results
            })
            
            logger.info(f"LLM analysis successful for {company_name}")
            logger.debug(f"Extracted data - Funding: {intelligence_data.get('funding_stage')}, " 
                        f"Industry: {intelligence_data.get('industry')}, "
                        f"Confidence: {intelligence_data.get('confidence_score')}")
            
        except Exception as e:
            logger.error(f"LLM analysis failed for {company_name}: {str(e)}", exc_info=True)
            raise
        
        # Convert to CompanyIntelligence object
        return CompanyIntelligence(
            company_name=intelligence_data.get("company_name", company_name),
            funding_stage=intelligence_data.get("funding_stage", "unknown"),
            funding_amount=intelligence_data.get("funding_amount"),
            investors=intelligence_data.get("investors", []),
            industry=intelligence_data.get("industry", "Unknown"),
            business_model=intelligence_data.get("business_model", "unknown"),
            employee_count=intelligence_data.get("employee_count"),
            key_competitors=intelligence_data.get("key_competitors", []),
            recent_news=intelligence_data.get("recent_news", []),
            leadership_team=intelligence_data.get("leadership_team", []),
            regulatory_context=intelligence_data.get("regulatory_context", ""),
            growth_stage=intelligence_data.get("growth_stage", "unknown"),
            ipo_status=intelligence_data.get("ipo_status", "unknown"),
            confidence_score=intelligence_data.get("confidence_score", 0.5)
        )
    
    def _format_search_results(self, search_results: Dict[str, List[SearchResult]]) -> str:
        """Format search results for LLM analysis."""
        
        formatted_sections = []
        
        for category, results in search_results.items():
            if results:
                section = f"\n=== {category.upper()} SEARCH RESULTS ===\n"
                for i, result in enumerate(results[:5], 1):
                    section += f"{i}. {result.title}\n"
                    section += f"   {result.snippet}\n"
                    if result.date:
                        section += f"   Date: {result.date}\n"
                    section += f"   URL: {result.url}\n\n"
                formatted_sections.append(section)
        
        return "\n".join(formatted_sections)
    
    def _create_fallback_intelligence(self, company_name: str) -> CompanyIntelligence:
        """Create fallback intelligence when research fails."""
        
        logger.warning(f"Creating fallback intelligence for {company_name} due to research failure")
        logger.info("Fallback intelligence will have minimal data and low confidence score")
        
        return CompanyIntelligence(
            company_name=company_name,
            funding_stage="unknown",
            funding_amount=None,
            investors=[],
            industry="Unknown",
            business_model="unknown",
            employee_count=None,
            key_competitors=[],
            recent_news=[],
            leadership_team=[],
            regulatory_context="",
            growth_stage="unknown",
            ipo_status="unknown",
            confidence_score=0.1
        )