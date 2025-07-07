"""Research tools for LangGraph workflow."""

import asyncio
import aiohttp
from typing import Dict, Any, List, Optional
from langchain_core.tools import tool
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser

from ...services.llm_factory import LLMFactory
from ...config import get_settings
from ...logger import logger


# Data classes for search results (identical to research agent)
class SearchResult:
    """Structured search result."""
    def __init__(self, title: str, snippet: str, url: str, date: Optional[str] = None):
        self.title = title
        self.snippet = snippet
        self.url = url
        self.date = date


@tool
async def company_funding_search(company_name: str) -> Dict[str, Any]:
    """Search for company funding information."""
    logger.info(f"Funding search for: {company_name}")
    
    query = f"{company_name} funding series round investors valuation"
    results = await _perform_search(query, "funding")
    
    return {
        "category": "funding",
        "query": query,
        "results": [
            {
                "title": result.title,
                "snippet": result.snippet,
                "url": result.url,
                "date": result.date
            }
            for result in results
        ]
    }


@tool
async def company_news_search(company_name: str) -> Dict[str, Any]:
    """Search for recent company news."""
    logger.info(f"News search for: {company_name}")
    
    query = f"{company_name} news 2024 2025 announcements partnerships"
    results = await _perform_search(query, "news")
    
    return {
        "category": "news",
        "query": query,
        "results": [
            {
                "title": result.title,
                "snippet": result.snippet,
                "url": result.url,
                "date": result.date
            }
            for result in results
        ]
    }


@tool
async def company_industry_search(company_name: str) -> Dict[str, Any]:
    """Search for company industry and business model information."""
    logger.info(f"Industry search for: {company_name}")
    
    query = f"{company_name} industry business model revenue competitors"
    results = await _perform_search(query, "industry")
    
    return {
        "category": "industry",
        "query": query,
        "results": [
            {
                "title": result.title,
                "snippet": result.snippet,
                "url": result.url,
                "date": result.date
            }
            for result in results
        ]
    }


@tool
async def company_leadership_search(company_name: str) -> Dict[str, Any]:
    """Search for company leadership team information."""
    logger.info(f"Leadership search for: {company_name}")
    
    query = f"{company_name} CEO CTO CFO executive team leadership hiring"
    results = await _perform_search(query, "leadership")
    
    return {
        "category": "leadership",
        "query": query,
        "results": [
            {
                "title": result.title,
                "snippet": result.snippet,
                "url": result.url,
                "date": result.date
            }
            for result in results
        ]
    }


@tool
async def company_size_search(company_name: str) -> Dict[str, Any]:
    """Search for company size and employee count information."""
    logger.info(f"Size search for: {company_name}")
    
    query = f"{company_name} employees headcount company size"
    results = await _perform_search(query, "size")
    
    return {
        "category": "size",
        "query": query,
        "results": [
            {
                "title": result.title,
                "snippet": result.snippet,
                "url": result.url,
                "date": result.date
            }
            for result in results
        ]
    }


@tool
async def company_ipo_search(company_name: str) -> Dict[str, Any]:
    """Search for company IPO status and plans."""
    logger.info(f"IPO search for: {company_name}")
    
    query = f"{company_name} IPO public offering S-1 filing"
    results = await _perform_search(query, "ipo")
    
    return {
        "category": "ipo",
        "query": query,
        "results": [
            {
                "title": result.title,
                "snippet": result.snippet,
                "url": result.url,
                "date": result.date
            }
            for result in results
        ]
    }


# Helper functions (identical to research agent logic)

async def _perform_search(query: str, category: str) -> List[SearchResult]:
    """Perform a single search using available search API (identical to research agent)."""
    
    settings = get_settings()
    
    if settings.serper_api_key and settings.serper_api_key != "your_serper_api_key_here":
        logger.debug(f"Using Serper API for search: {query[:50]}...")
        return await _serper_search(query, settings.serper_api_key)
    else:
        # Fallback to enhanced LLM-based research
        logger.warning(f"No Serper API key available, falling back to LLM research for category: {category}")
        return await _llm_research(query, category)


async def _serper_search(query: str, serper_api_key: str, num_results: int = 10) -> List[SearchResult]:
    """Search using Serper API (identical to research agent)."""
    
    url = "https://google.serper.dev/search"
    headers = {
        "X-API-KEY": serper_api_key,
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
                    results = _parse_serper_results(data)
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


def _parse_serper_results(data: Dict[str, Any]) -> List[SearchResult]:
    """Parse Serper API response into SearchResult objects (identical to research agent)."""
    
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


async def _llm_research(query: str, category: str) -> List[SearchResult]:
    """Fallback research using LLM when API unavailable (identical to research agent)."""
    
    logger.info(f"Using LLM fallback for research - Category: {category}, Query: {query[:50]}...")
    
    llm = LLMFactory.create_extraction_llm()
    json_parser = JsonOutputParser()
    
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
    
    research_chain = research_prompt | llm | json_parser
    
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


@tool
async def analyze_company_intelligence(company_name: str, search_results: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze search results and extract structured company intelligence."""
    logger.info(f"Analyzing company intelligence for: {company_name}")
    
    # Use identical analysis prompt from research agent
    llm = LLMFactory.create_extraction_llm()
    json_parser = JsonOutputParser()
    
    analysis_prompt = ChatPromptTemplate.from_messages([
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
{formatted_results}

Analyze these search results and extract comprehensive company intelligence for executive search purposes. Be specific about funding amounts, dates, and executive team details when available.""")
    ])
    
    # Format search results for analysis
    formatted_results = _format_search_results(search_results)
    
    analysis_chain = analysis_prompt | llm | json_parser
    
    try:
        logger.debug("Invoking LLM for intelligence analysis...")
        intelligence_data = await analysis_chain.ainvoke({
            "company_name": company_name,
            "formatted_results": formatted_results
        })
        
        logger.info(f"LLM analysis successful for {company_name}")
        logger.debug(f"Extracted data - Funding: {intelligence_data.get('funding_stage')}, " 
                    f"Industry: {intelligence_data.get('industry')}, "
                    f"Confidence: {intelligence_data.get('confidence_score')}")
        
        return intelligence_data
        
    except Exception as e:
        logger.error(f"LLM analysis failed for {company_name}: {str(e)}", exc_info=True)
        # Return fallback intelligence
        return {
            "company_name": company_name,
            "funding_stage": "unknown",
            "funding_amount": None,
            "investors": [],
            "industry": "Unknown",
            "business_model": "unknown",
            "employee_count": None,
            "key_competitors": [],
            "recent_news": [],
            "leadership_team": [],
            "regulatory_context": "",
            "growth_stage": "unknown",
            "ipo_status": "unknown",
            "confidence_score": 0.1
        }


def _format_search_results(search_results: Dict[str, Any]) -> str:
    """Format search results for LLM analysis (identical to research agent)."""
    
    formatted_sections = []
    
    for category, data in search_results.items():
        if data and data.get("results"):
            results = data["results"]
            section = f"\n=== {category.upper()} SEARCH RESULTS ===\n"
            for i, result in enumerate(results[:5], 1):
                section += f"{i}. {result['title']}\n"
                section += f"   {result['snippet']}\n"
                if result.get('date'):
                    section += f"   Date: {result['date']}\n"
                section += f"   URL: {result['url']}\n\n"
            formatted_sections.append(section)
    
    return "\n".join(formatted_sections)


# List of all research tools for easy access
RESEARCH_TOOLS = [
    company_funding_search,
    company_news_search,
    company_industry_search,
    company_leadership_search,
    company_size_search,
    company_ipo_search,
    analyze_company_intelligence
]