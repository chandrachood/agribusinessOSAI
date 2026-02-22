import asyncio
from typing import Dict, Any, Callable
from src.agents.definitions import build_agents
from src.models.gemini_client import GeminiRunner

async def run_agribusiness_pipeline(
    user_input: str,
    progress_cb: Callable[[Dict[str, Any]], None],
    session_service=None,
    language: str = 'en'
):
    """
    Orchestrates the 7-agent pipeline.
    
    Flow:
    1. Data Collector (Interacts until Profile COMPLETE)
       - Note: For this pipeline, we assume we might get a single blob or need to loop. 
       - MVP: We'll assume the input IS the profile or we do one pass.
    2. Crop Advisor (Parallel start?) -> needs Profile.
    3. Market, Weather, Logistics, ValueAdd -> need Crops/Location.
    4. Aggregator -> needs all above.
    """
    
    agents = build_agents()
    
    # Supported languages map for prompt injection
    lang_map = {
        'en': 'English',
        'hi': 'Hindi',
        'ml': 'Malayalam'
    }
    target_lang = lang_map.get(language, 'English')
    
    # helper to run agent
    async def run_agent(agent_key: str, content: str) -> str:
        runner = GeminiRunner(agents[agent_key], "agri_os", session_service)
        result_text = ""
        progress_cb({"step": agent_key, "status": "running"})
        
        # Inject language instruction
        lang_instruction = f"\n\nIMPORTANT: You must output your response strictly in {target_lang} language."
        final_content = content + lang_instruction
        
        async for event in runner.run_async("user", "session", final_content):
            if event.is_final_response():
                result_text = event.text
                
        progress_cb({"step": agent_key, "status": "completed", "output": result_text})
        return result_text

    # Step 1: Data Coordinator / Collector
    # In a real chat, this would be a loop. Here we treat user_input as the starting point.
    # If user_input is just "Help me plan", the collector scans it. 
    # For the pipeline demo, we'll ask the collector to extract/validate.
    
    progress_cb(
        {
            "step": "pipeline_start",
            "status": "running",
            "message": f"Starting AgriBusiness OS Analysis in {target_lang}...",
        }
    )
    
    farmer_profile_json = await run_agent("data_collector", f"User Input: {user_input}")
    
    # Step 2: Crop Advisor
    # Pass the profile to the crop advisor
    crop_recommendations = await run_agent("crop_advisor", f"Farmer Profile: {farmer_profile_json}")
    
    # Step 3: Parallel Execution of Domain Experts
    # They all need the crop recommendations and location (from profile).
    
    context_for_experts = f"""
    Farmer Profile: {farmer_profile_json}
    Recommended Crops: {crop_recommendations}
    """
    
    # Run these in parallel
    results = await asyncio.gather(
        run_agent("market_intelligence", context_for_experts),
        run_agent("weather_ai", context_for_experts),
        run_agent("logistics", context_for_experts),
        run_agent("value_add", context_for_experts)
    )
    
    market_out, weather_out, logistics_out, value_add_out = results
    
    # Step 4: Aggregator
    aggregator_input = f"""
    Please aggregate the following reports into a final business plan:
    
    1. Crop Advisor:
    {crop_recommendations}
    
    2. Market Intelligence:
    {market_out}
    
    3. Weather Risk:
    {weather_out}
    
    4. Logistics:
    {logistics_out}
    
    5. Value Addition:
    {value_add_out}
    """
    
    final_plan = await run_agent("aggregator", aggregator_input)
    
    progress_cb({"step": "pipeline_complete", "status": "completed", "output": final_plan})
    return final_plan
