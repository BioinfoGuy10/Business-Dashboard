"""
LLM-powered analysis module for extracting structured insights from transcripts.
Supports OpenAI and Ollama providers with robust error handling and retry logic.
"""

import json
import sys
from pathlib import Path
from typing import Dict, Optional
from datetime import datetime

# LLM provider imports
from openai import OpenAI
from tenacity import retry, stop_after_attempt, wait_exponential
from pydantic import BaseModel, Field, ValidationError

# Local imports
sys.path.append(str(Path(__file__).parent.parent))
import config


# Pydantic models for structured output validation
class ActionItem(BaseModel):
    """Model for action item structure."""
    task: str = Field(..., description="Description of the task")
    owner: Optional[str] = Field(None, description="Person responsible")
    deadline: Optional[str] = Field(None, description="Due date")
    status: str = Field(default="open", description="Status: open or closed")


class InsightSchema(BaseModel):
    """Model for the complete insight extraction output."""
    summary: str = Field(..., description="Brief summary of the transcript")
    topics: list[str] = Field(default_factory=list, description="Main topics discussed")
    risks: list[str] = Field(default_factory=list, description="Identified risks")
    opportunities: list[str] = Field(default_factory=list, description="Business opportunities")
    action_items: list[ActionItem] = Field(default_factory=list, description="Action items")
    sentiment: str = Field(..., description="Overall sentiment: positive, neutral, or negative")


def build_prompt(text: str) -> str:
    """
    Build an optimized prompt for LLM to extract structured insights.
    
    Args:
        text: Transcript text to analyze
        
    Returns:
        Formatted prompt string
    """
    prompt = f"""You are an expert business analyst. Analyze the following business meeting transcript and extract structured insights.

TRANSCRIPT:
{text[:4000]}  

Extract the following information in JSON format:

1. **summary**: A brief 2-3 sentence summary of what was discussed
2. **topics**: List of main topics/themes discussed (max 10)
3. **risks**: Any challenges, concerns, or risks mentioned
4. **opportunities**: Business opportunities, potential wins, or growth areas
5. **action_items**: List of tasks/action items with:
   - task: Description of what needs to be done
   - owner: Person responsible (if mentioned)
   - deadline: Due date (if mentioned)
   - status: "open" (default) or "closed"
6. **sentiment**: Overall meeting sentiment - one of: "positive", "neutral", or "negative"

Return ONLY valid JSON matching this exact structure:
{{
  "summary": "...",
  "topics": ["topic1", "topic2"],
  "risks": ["risk1", "risk2"],
  "opportunities": ["opp1", "opp2"],
  "action_items": [
    {{"task": "...", "owner": "...", "deadline": "...", "status": "open"}}
  ],
  "sentiment": "positive"
}}

Be thorough but concise. If a section has no content, use an empty list []."""

    return prompt


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    reraise=True
)
def call_openai_api(prompt: str) -> str:
    """
    Call OpenAI API with retry logic for robustness.
    
    Args:
        prompt: The prompt to send to OpenAI
        
    Returns:
        Raw response text from the API
        
    Raises:
        Exception: If API call fails after retries
    """
    if not config.OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY not set in environment variables")
    
    try:
        # Initialize client with custom base_url if provided (for Groq, etc.)
        client_kwargs = {"api_key": config.OPENAI_API_KEY}
        if config.OPENAI_BASE_URL:
            client_kwargs["base_url"] = config.OPENAI_BASE_URL
        
        client = OpenAI(**client_kwargs)
        
        response = client.chat.completions.create(
            model=config.OPENAI_MODEL,
            messages=[
                {"role": "system", "content": "You are a helpful business analyst that extracts structured insights from meeting transcripts. Always respond with valid JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,  # Lower temperature for more consistent output
            response_format={"type": "json_object"}  # Force JSON output
        )
        
        return response.choices[0].message.content
    
    except Exception as e:
        raise Exception(f"OpenAI API error: {str(e)}")


def call_ollama_api(prompt: str) -> str:
    """
    Call local Ollama API as fallback LLM provider.
    
    Args:
        prompt: The prompt to send to Ollama
        
    Returns:
        Raw response text from the API
        
    Raises:
        Exception: If API call fails
    """
    try:
        import requests
        
        url = f"{config.OLLAMA_BASE_URL}/api/generate"
        payload = {
            "model": config.OLLAMA_MODEL,
            "prompt": prompt,
            "stream": False,
            "format": "json"
        }
        
        response = requests.post(url, json=payload, timeout=60)
        response.raise_for_status()
        
        result = response.json()
        return result.get("response", "{}")
    
    except Exception as e:
        raise Exception(f"Ollama API error: {str(e)}")


def validate_json_output(response: str) -> Dict:
    """
    Validate and parse JSON output from LLM response.
    
    Args:
        response: Raw LLM response text
        
    Returns:
        Validated dictionary matching InsightSchema
        
    Raises:
        ValueError: If JSON is invalid or doesn't match schema
    """
    try:
        # Parse JSON
        data = json.loads(response)
        
        # Validate against Pydantic schema
        validated = InsightSchema(**data)
        
        return validated.model_dump()
    
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON response: {str(e)}")
    
    except ValidationError as e:
        # Partial extraction fallback
        print(f"⚠️  Schema validation failed: {e}")
        
        # Try to salvage what we can
        try:
            data = json.loads(response)
            return {
                "summary": data.get("summary", "Error: Could not extract summary"),
                "topics": data.get("topics", []),
                "risks": data.get("risks", []),
                "opportunities": data.get("opportunities", []),
                "action_items": data.get("action_items", []),
                "sentiment": data.get("sentiment", "neutral")
            }
        except:
            raise ValueError("Could not parse LLM response into valid format")


def extract_insights(text: str, metadata: Dict) -> Dict:
    """
    Main function to extract structured insights from transcript text using LLM.
    
    Args:
        text: Cleaned transcript text
        metadata: File metadata (filename, upload_date, etc.)
        
    Returns:
        Dictionary containing extracted insights and metadata
        
    Raises:
        Exception: If extraction fails
    """
    try:
        print(f"🔍 Extracting insights from {metadata.get('filename', 'transcript')}...")
        
        # Build optimized prompt
        prompt = build_prompt(text)
        
        # Call appropriate LLM provider
        if config.LLM_PROVIDER == "openai":
            response = call_openai_api(prompt)
        elif config.LLM_PROVIDER == "ollama":
            response = call_ollama_api(prompt)
        else:
            raise ValueError(f"Unsupported LLM provider: {config.LLM_PROVIDER}")
        
        # Validate and parse response
        insights = validate_json_output(response)
        
        # Combine with metadata
        result = {
            "filename": metadata.get("filename"),
            "date": metadata.get("upload_date", datetime.now().isoformat()),
            "file_type": metadata.get("file_type"),
            "character_count": metadata.get("character_count"),
            "word_count": metadata.get("word_count"),
            **insights
        }
        
        # Save to insights directory
        save_insights(result, metadata.get("filename"))
        
        print(f"✅ Successfully extracted insights!")
        print(f"   - Topics: {len(insights['topics'])}")
        print(f"   - Risks: {len(insights['risks'])}")
        print(f"   - Opportunities: {len(insights['opportunities'])}")
        print(f"   - Action Items: {len(insights['action_items'])}")
        print(f"   - Sentiment: {insights['sentiment']}")
        
        return result
    
    except Exception as e:
        error_msg = f"Failed to extract insights: {str(e)}"
        print(f"❌ {error_msg}")
        
        # Return error structure to maintain flow
        return {
            "filename": metadata.get("filename"),
            "date": metadata.get("upload_date", datetime.now().isoformat()),
            "error": error_msg,
            "summary": "Error during extraction",
            "topics": [],
            "risks": [],
            "opportunities": [],
            "action_items": [],
            "sentiment": "neutral"
        }

def synthesize_work_update(text: str) -> str:
    """
    Synthesize raw rough notes into a professional work update.
    
    Args:
        text: Raw notes from user
        
    Returns:
        Concise, professional summary
    """
    if not text.strip():
        return ""
        
    prompt = f"""You are a professional project manager. Convert the following rough notes into a clear, professional, and concise work update for a team dashboard.
    
ROUGH NOTES:
{text}

Requirements:
- Professional tone
- Concise (1-2 sentences or bullet points)
- Action-oriented
- Keep it to the point

Return ONLY the professional update text. No introduction or filler."""

    try:
        if config.LLM_PROVIDER == "openai" and config.OPENAI_API_KEY:
            client_kwargs = {"api_key": config.OPENAI_API_KEY}
            if config.OPENAI_BASE_URL:
                client_kwargs["base_url"] = config.OPENAI_BASE_URL
            client = OpenAI(**client_kwargs)
            
            response = client.chat.completions.create(
                model=config.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": "You are a helpful project assistant. You specialize in turning rough developer notes into professional work updates."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=200
            )
            return response.choices[0].message.content.strip()
            
        elif config.LLM_PROVIDER == "ollama":
            import requests
            url = f"{config.OLLAMA_BASE_URL}/api/generate"
            payload = {
                "model": config.OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False
            }
            response = requests.post(url, json=payload, timeout=60)
            response.raise_for_status()
            result = response.json()
            return result.get("response", "").strip()
        
        else:
            # Fallback deterministic simulator
            words = text.split()
            summary = "Working on: " + " ".join(words[:15]) + "..." if len(words) > 15 else text
            return f"[Simulated Update] {summary} (Please configure LLM API key for real generation)"
            
    except Exception as e:
        print(f"Synthesis error: {e}")
        return f"Error generating description: {str(e)}"


def save_insights(insights: Dict, filename: str) -> Path:
    """
    Save extracted insights to JSON file.
    
    Args:
        insights: Extracted insights dictionary
        filename: Original transcript filename
        
    Returns:
        Path to saved JSON file
    """
    # Create JSON filename
    json_filename = Path(filename).stem + ".json"
    json_path = config.INSIGHTS_DIR / json_filename
    
    # Save with pretty formatting
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(insights, f, indent=2, ensure_ascii=False)
    
    print(f"💾 Insights saved to: {json_path}")
    return json_path


def load_insights(filename: str) -> Optional[Dict]:
    """
    Load previously extracted insights from JSON file.
    
    Args:
        filename: Original transcript filename (without path)
        
    Returns:
        Insights dictionary if exists, None otherwise
    """
    json_filename = Path(filename).stem + ".json"
    json_path = config.INSIGHTS_DIR / json_filename
    
    if json_path.exists():
        with open(json_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    return None


def insights_exist(filename: str) -> bool:
    """
    Check if insights already exist for a given transcript.
    
    Args:
        filename: Original transcript filename
        
    Returns:
        True if insights JSON exists, False otherwise
    """
    json_filename = Path(filename).stem + ".json"
    json_path = config.INSIGHTS_DIR / json_filename
    return json_path.exists()


if __name__ == "__main__":
    # Test the module
    print("🔧 Testing analysis module...")
    print(f"✓ LLM Provider: {config.LLM_PROVIDER}")
    print(f"✓ Model: {config.OPENAI_MODEL if config.LLM_PROVIDER == 'openai' else config.OLLAMA_MODEL}")
    print(f"✓ Insights directory: {config.INSIGHTS_DIR}")
    
    # Test prompt building
    test_text = "Team meeting to discuss Q1 roadmap. John raised concerns about timeline. Sarah proposed hiring 2 engineers."
    prompt = build_prompt(test_text)
    print(f"\n✓ Prompt generation works (length: {len(prompt)} chars)")
    
    print("\n✅ Analysis module ready!")
