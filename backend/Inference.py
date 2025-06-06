from crewai import Agent, Task, Crew
from langchain_community.llms import Ollama
from langchain.tools import Tool
import base64
import requests
import os
import threading
from typing import Dict, Any, List, Optional
import json
import time
from datetime import datetime
from PIL import Image
from MemoryBank import MemoryBank

class DualResponseContextualAnalyzer:
    def __init__(self, 
                 ollama_base_url="http://localhost:11434",
                 memory_bank: Optional[MemoryBank] = None,
                 persist_directory: str = "./contextual_memory_storage"):
        self.ollama_base_url = ollama_base_url
        self.analysis_cache = {}
        self._lock = threading.Lock()
        
        # Initialize or use provided MemoryBank
        if memory_bank is None:
            self.memory_bank = MemoryBank(
                persist_directory=persist_directory,
                forgetting_enabled=True
            )
        else:
            self.memory_bank = memory_bank
    
    def encode_image_to_base64(self, image_path: str) -> str:
        """Encode image to base64"""
        try:
            with open(image_path, "rb") as f:
                return base64.b64encode(f.read()).decode('utf-8')
        except Exception as e:
            return None
    
    def generate_direct_answer(self, user_question: str, user_id: str = "default_user") -> str:
        """Generate a direct answer to the user's question using text model"""
        try:
            # Get memory context for personalized response
            memory_context = self.memory_bank.get_prompt_context(user_id, user_question)
            
            # Create prompt for direct answer
            direct_answer_prompt = f"""
USER QUESTION: {user_question}

USER CONTEXT (from memory):
- User Name: {memory_context['user_name']}
- Session: {memory_context['session_count']}
- User Profile: {memory_context['user_portrait']}
- Previous Interactions: {memory_context['memory_records'][:500]}...

TASK: Provide a direct, helpful answer to the user's question. Consider their background and previous interactions to personalize your response. Be concise but informative.

If this is a factual question (like "Where is France?"), provide the factual answer.
If this is a personal question, consider their history and context.
If this is a complex question, break it down clearly.

DIRECT ANSWER:"""

            # Call text model for direct answer
            response = requests.post(
                f"{self.ollama_base_url}/api/generate",
                json={
                    "model": "llama3.2:3b",  # Using text model for better factual responses
                    "prompt": direct_answer_prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.2,
                        "top_p": 0.9,
                        "num_predict": 300
                    }
                },
                timeout=60
            )
            
            if response.status_code == 200:
                direct_answer = response.json().get("response", "").strip()
                return direct_answer
            else:
                return f"I apologize, but I'm having trouble generating a response right now."
                
        except Exception as e:
            return f"Let me help you with that question, though I'm experiencing some technical difficulties: {str(e)}"
    
    def dual_contextual_analysis(self, 
                                image_path: str, 
                                user_question: str, 
                                user_id: str = "default_user") -> Dict[str, Any]:
        """Perform both direct answer and contextual visual analysis"""
        try:
            # Handle CrewAI argument formats
            if isinstance(image_path, dict):
                image_path = image_path.get('tool_input', image_path)
            
            image_path = str(image_path).strip().strip('"').strip("'")
            
            if not os.path.exists(image_path):
                return {"error": f"Image not found: {image_path}"}
            
            # STEP 1: Generate direct answer to user question
            print("🤖 Generating direct answer...")
            direct_answer = self.generate_direct_answer(user_question, user_id)
            
            # STEP 2: Get memory context for visual analysis
            memory_context = self.memory_bank.get_prompt_context(user_id, user_question)
            
            # STEP 3: Encode image for analysis
            image_b64 = self.encode_image_to_base64(image_path)
            if not image_b64:
                return {"error": "Failed to encode image"}
            
            # STEP 4: Create dual-purpose analysis prompt
            print("🖼️ Performing contextual image analysis...")
            dual_prompt = self._create_dual_analysis_prompt(user_question, direct_answer, memory_context)
            
            # STEP 5: API call for visual analysis
            response = requests.post(
                f"{self.ollama_base_url}/api/generate",
                json={
                    "model": "llava:7b",
                    "prompt": dual_prompt,
                    "images": [image_b64],
                    "stream": False,
                    "options": {
                        "temperature": 0.3,
                        "top_p": 0.8,
                        "num_predict": 1000
                    }
                },
                timeout=180
            )
            
            if response.status_code == 200:
                visual_analysis = response.json().get("response", "")
                
                # Parse the dual response
                structured_result = self._parse_dual_response(visual_analysis, user_question, direct_answer)
                
                # Store both responses in memory
                self._store_dual_analysis_in_memory(
                    user_id=user_id,
                    image_path=image_path,
                    user_question=user_question,
                    direct_answer=direct_answer,
                    visual_analysis=structured_result,
                    raw_visual_response=visual_analysis
                )
                
                return {
                    "success": True,
                    "direct_answer": direct_answer,
                    "visual_analysis": structured_result,
                    "raw_visual_response": visual_analysis,
                    "user_question": user_question,
                    "memory_context_used": True
                }
            else:
                return {
                    "success": True,
                    "direct_answer": direct_answer,
                    "visual_analysis": {"error": f"Visual analysis failed: {response.status_code}"},
                    "user_question": user_question
                }
                
        except Exception as e:
            return {"error": f"Dual analysis failed: {str(e)}"}
    
    def _create_dual_analysis_prompt(self, user_question: str, direct_answer: str, memory_context: Dict) -> str:
        """Create a prompt that handles both direct answer and visual analysis"""
        
        prompt = f"""
DUAL RESPONSE ANALYSIS - DIRECT ANSWER + VISUAL CONTEXT

USER QUESTION: {user_question}
DIRECT ANSWER PROVIDED: {direct_answer}

USER MEMORY CONTEXT:
- Current Time: {memory_context['current_datetime']}
- User: {memory_context['user_name']}
- Session: {memory_context['session_count']}
- User Profile: {memory_context['user_portrait']}
- Previous Conversations: {memory_context['memory_records']}
- Emotional History: {memory_context['emotional_image_context']}
- Important Events: {memory_context['event_summaries']}

ANALYSIS TASK:
Now that we've provided a direct answer to their question, analyze this image to provide additional context-aware insights that complement the direct answer.

Your visual analysis should:

1. VISUAL CONTEXT FOR THE QUESTION:
   - How does what you see in the image relate to their question "{user_question}"?
   - Does the image provide additional context or contradiction to the direct answer?
   - What visual elements are relevant to their inquiry?

2. MEMORY-ENHANCED OBSERVATIONS:
   - Based on their history, what aspects of this image might be particularly relevant to them?
   - How does this image connect to their previous interactions or concerns?
   - What patterns do you notice considering their background?

3. CONTEXTUAL INSIGHTS:
   - What additional information does the image provide beyond the direct answer?
   - How might the visual context change or enhance understanding of the topic?
   - What emotions, situations, or circumstances are visible that add context?

4. PERSONALIZED CONNECTIONS:
   - How might this image and question relate to their personal situation?
   - What follow-up questions or concerns might they have based on what you see?
   - How can the visual information help them better understand the direct answer?

5. INTEGRATED RECOMMENDATIONS:
   - Considering both the direct answer and visual context, what suggestions would you make?
   - How does the combination of textual answer and visual evidence guide your recommendations?

RESPONSE FORMAT:
Provide a comprehensive analysis that bridges the direct answer with visual insights, creating a complete response that addresses both their explicit question and the contextual information visible in the image.

Remember: The user already received the direct answer "{direct_answer}". Now provide visual analysis that adds depth, context, and personalized insights based on what you observe and their history.
"""
        
        return prompt
    
    def _parse_dual_response(self, visual_response: str, user_question: str, direct_answer: str) -> Dict[str, str]:
        """Parse the visual analysis response into structured sections"""
        
        sections = {
            "visual_context": "",
            "memory_observations": "",
            "contextual_insights": "",
            "personal_connections": "",
            "integrated_recommendations": "",
            "additional_notes": ""
        }
        
        try:
            lines = visual_response.split('\n')
            current_section = "visual_context"
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                # Identify section headers
                if any(keyword in line.lower() for keyword in ['visual context', 'image relation', 'visual element']):
                    current_section = "visual_context"
                elif any(keyword in line.lower() for keyword in ['memory', 'history', 'previous', 'background']):
                    current_section = "memory_observations"
                elif any(keyword in line.lower() for keyword in ['contextual insight', 'additional information', 'beyond']):
                    current_section = "contextual_insights"
                elif any(keyword in line.lower() for keyword in ['personal', 'connection', 'situation', 'individual']):
                    current_section = "personal_connections"
                elif any(keyword in line.lower() for keyword in ['recommend', 'suggest', 'integrated', 'combination']):
                    current_section = "integrated_recommendations"
                else:
                    # Add content to current section
                    if sections[current_section]:
                        sections[current_section] += " " + line
                    else:
                        sections[current_section] = line
            
            # If parsing didn't work well, put everything in visual_context
            if not any(sections.values()):
                sections["visual_context"] = visual_response
            
        except Exception:
            sections["visual_context"] = visual_response
        
        return sections
    
    def _store_dual_analysis_in_memory(self, 
                                     user_id: str, 
                                     image_path: str, 
                                     user_question: str, 
                                     direct_answer: str,
                                     visual_analysis: Dict, 
                                     raw_visual_response: str):
        """Store both direct answer and visual analysis in memory"""
        try:
            # Store the complete interaction
            full_response = f"Question: {user_question}\n"
            full_response += f"Direct Answer: {direct_answer}\n"
            full_response += f"Visual Context: {visual_analysis.get('visual_context', '')}\n"
            full_response += f"Personal Insights: {visual_analysis.get('personal_connections', '')}"
            
            self.memory_bank.add_conversation(
                user_id=user_id,
                conversation_text=full_response,
                user_input=user_question,
                bot_response=f"{direct_answer} | Visual Analysis: {visual_analysis.get('visual_context', '')}",
                metadata={
                    "analysis_type": "dual_response_contextual",
                    "has_direct_answer": True,
                    "has_visual_analysis": True,
                    "image_analyzed": True,
                    "image_path": image_path,
                    "question_type": self._classify_question_type(user_question)
                }
            )
            
            # Store emotional image if relevant
            if os.path.exists(image_path):
                try:
                    pil_image = Image.open(image_path)
                    
                    emotion_description = f"Dual analysis from {datetime.now().strftime('%Y-%m-%d %H:%M')}: "
                    emotion_description += f"User asked '{user_question}'. "
                    emotion_description += f"Direct answer: {direct_answer[:100]}... "
                    emotion_description += f"Visual context: {visual_analysis.get('visual_context', '')[:100]}..."
                    
                    self.memory_bank.add_emotional_image(
                        user_id=user_id,
                        image=pil_image,
                        emotion_description=emotion_description,
                        metadata={
                            "analysis_type": "dual_response",
                            "user_question": user_question,
                            "has_direct_answer": True
                        }
                    )
                except Exception as e:
                    print(f"Error storing emotional image: {e}")
            
        except Exception as e:
            print(f"Error storing dual analysis in memory: {e}")
    
    def _classify_question_type(self, question: str) -> str:
        """Classify the type of question asked"""
        question_lower = question.lower()
        
        if any(word in question_lower for word in ['where', 'location', 'place']):
            return "location"
        elif any(word in question_lower for word in ['what', 'define', 'explain']):
            return "factual"
        elif any(word in question_lower for word in ['how', 'why', 'when']):
            return "explanatory"
        elif any(word in question_lower for word in ['feel', 'emotion', 'mood', 'happy', 'sad']):
            return "emotional"
        elif any(word in question_lower for word in ['help', 'advice', 'suggest', 'recommend']):
            return "advisory"
        else:
            return "general"

# Initialize the dual response analyzer
def initialize_dual_analyzer_with_memory(memory_bank: Optional[MemoryBank] = None):
    """Initialize the dual response analyzer with memory integration"""
    return DualResponseContextualAnalyzer(
        ollama_base_url="http://localhost:11434",
        memory_bank=memory_bank
    )

# Global analyzer instance
dual_analyzer = None

# === DUAL RESPONSE TOOL ===

def dual_response_analysis_tool(input_data: str) -> str:
    """Perform both direct answer and contextual image analysis"""
    global dual_analyzer
    
    try:
        # Handle different input formats
        if isinstance(input_data, dict):
            image_path = input_data.get('image_path', '')
            user_question = input_data.get('user_question', '')
            user_id = input_data.get('user_id', 'default_user')
        else:
            # Get from function attributes
            image_path = str(input_data)
            user_question = getattr(dual_response_analysis_tool, 'user_question', 'General analysis')
            user_id = getattr(dual_response_analysis_tool, 'user_id', 'default_user')
        
        if dual_analyzer is None:
            return "❌ Error: Dual analyzer not initialized"
        
        result = dual_analyzer.dual_contextual_analysis(image_path, user_question, user_id)
        
        if result.get("error"):
            return f"❌ Error: {result['error']}"
        
        if result.get("success"):
            direct_answer = result["direct_answer"]
            visual_analysis = result["visual_analysis"]
            
            # Format comprehensive dual response
            formatted_response = f"""
🎯 DIRECT ANSWER:
{direct_answer}

🧠 MEMORY-ENHANCED VISUAL ANALYSIS:

USER QUESTION: {user_question}
MEMORY INTEGRATION: {'✅ Previous interactions considered' if result.get('memory_context_used') else '❌ No memory context'}

📸 VISUAL CONTEXT FOR YOUR QUESTION:
{visual_analysis.get('visual_context', 'Visual elements analyzed in relation to your question')}

🔗 MEMORY-BASED OBSERVATIONS:
{visual_analysis.get('memory_observations', 'Connections to your history and preferences identified')}

💡 CONTEXTUAL INSIGHTS:
{visual_analysis.get('contextual_insights', 'Additional context provided based on visual evidence')}

👤 PERSONAL CONNECTIONS:
{visual_analysis.get('personal_connections', 'Personalized insights based on your profile')}

🎯 INTEGRATED RECOMMENDATIONS:
{visual_analysis.get('integrated_recommendations', 'Suggestions combining your question and visual context')}

📋 ADDITIONAL NOTES:
{visual_analysis.get('additional_notes', 'Complete analysis stored in memory for future reference')}

📝 Both direct answer and visual analysis stored in memory for future conversations.
"""
            return formatted_response
        
        return "Analysis could not be completed"
        
    except Exception as e:
        return f"❌ Dual analysis error: {str(e)}"

# === DUAL RESPONSE TOOL CREATION ===

dual_response_tool = Tool(
    name="DualResponseAnalyzer",
    description="Provides both direct answers to user questions AND contextual image analysis with memory integration.",
    func=dual_response_analysis_tool
)

# === DUAL RESPONSE AGENT ===

def create_dual_response_agent():
    """Create an agent that handles both direct answers and visual analysis"""
    return Agent(
        role="Dual Response Visual Intelligence Specialist",
        goal="Provide comprehensive responses that include both direct answers to user questions and memory-enhanced contextual visual analysis",
        backstory=(
            "You are an advanced AI assistant that excels at providing complete, helpful responses. "
            "When users ask questions alongside images, you provide both a direct answer to their question "
            "AND a contextual analysis of their image that considers their personal history and context. "
            "You understand that users want their explicit questions answered while also benefiting from "
            "visual insights that enhance their understanding. You combine factual knowledge with "
            "personalized visual analysis to create comprehensive, useful responses."
        ),
        tools=[dual_response_tool],
        verbose=True,
        llm=Ollama(
            model="llava:7b",  # Using multimodal model for visual analysis
            base_url="http://localhost:11434",
            temperature=0.4,
            top_p=0.8,
            num_predict=600
        )
    )

# === DUAL RESPONSE TASK CREATION ===

def create_dual_response_task(image_path: str, user_question: str, user_id: str = "default_user"):
    """Create a task that handles both direct answers and visual analysis"""
    return Task(
        description=f"""
        The user ({user_id}) has asked: "{user_question}"
        
        Use the DualResponseAnalyzer to provide a comprehensive response that includes:
        
        1. DIRECT ANSWER: A clear, direct answer to their specific question "{user_question}"
        2. VISUAL ANALYSIS: A contextual analysis of the image at '{image_path}' that:
           - Considers their personal history and memory context
           - Relates the visual content to their question
           - Provides additional insights beyond the direct answer
           - Offers personalized recommendations
        
        Your response should be complete and helpful, addressing both their explicit question 
        and providing valuable visual insights that enhance their understanding.
        
        Both the direct answer and visual analysis will be stored in memory for future reference.
        """,
        agent=create_dual_response_agent(),
        expected_output=f"A comprehensive dual response providing both a direct answer to '{user_question}' and memory-enhanced contextual visual analysis"
    )

# === MAIN DUAL ANALYSIS FUNCTION ===

def analyze_with_dual_response(image_path: str, 
                              user_question: str, 
                              user_id: str = "default_user",
                              memory_bank: Optional[MemoryBank] = None):
    """Main function for dual response analysis (direct answer + visual analysis)"""
    
    global dual_analyzer
    
    if not os.path.exists(image_path):
        print(f"❌ Error: Image file '{image_path}' not found!")
        return
    
    # Initialize analyzer with memory if not already done
    if dual_analyzer is None:
        dual_analyzer = initialize_dual_analyzer_with_memory(memory_bank)
    
    # Set context for the tool
    dual_response_analysis_tool.user_question = user_question
    dual_response_analysis_tool.user_id = user_id
    
    print(f"🎯 DUAL RESPONSE ANALYSIS")
    print(f"👤 User: {user_id}")
    print(f"📁 Image: {os.path.basename(image_path)}")
    print(f"❓ Question: {user_question}")
    print("=" * 80)
    
    # Create dual response task
    task = create_dual_response_task(image_path, user_question, user_id)
    
    # Create crew with dual response capability
    crew = Crew(
        agents=[create_dual_response_agent()],
        tasks=[task],
        verbose=True,
        process="sequential"
    )
    
    # Execute analysis
    start_time = time.time()
    result = crew.kickoff()
    end_time = time.time()
    
    print(f"\n⚡ DUAL RESPONSE ANALYSIS COMPLETE ({end_time - start_time:.2f}s)")
    print("=" * 80)
    print(result)
    
    return result

# === USAGE EXAMPLES ===

if __name__ == "__main__":
    
    # Initialize memory bank
    memory_bank = MemoryBank(
        persist_directory="./dual_response_memory_storage",
        forgetting_enabled=True
    )
    
    # Example 1: Geographic question with image
    image_path = r"C:\Users\drodm\OneDrive\Documents\GitHub\Dolores-AI\Dolores-AI\uploads\elderly.png"
    user_question = "Where is France?"
    user_id = "student_001"
    
    print("🌍 EXAMPLE 1: Geographic Question + Visual Context")
    result1 = analyze_with_dual_response(
        image_path=image_path,
        user_question=user_question,
        user_id=user_id,
        memory_bank=memory_bank
    )
    
    # Example 2: Emotional question with image
    user_question2 = "How does the person in this image seem to be feeling emotionally?"
    
    print("\n" + "="*80)
    print("😊 EXAMPLE 2: Emotional Question + Visual Analysis")
    result2 = analyze_with_dual_response(
        image_path=image_path,
        user_question=user_question2,
        user_id=user_id,
        memory_bank=memory_bank
    )
    
    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"dual_response_analysis_{timestamp}.txt"
    
    with open(filename, "w", encoding="utf-8") as f:
        f.write(f"DUAL RESPONSE ANALYSIS RESULTS\n")
        f.write(f"User ID: {user_id}\n")
        f.write(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("=" * 60 + "\n\n")
        f.write("EXAMPLE 1 - Geographic Question:\n")
        f.write(f"Question: {user_question}\n")
        f.write(str(result1))
        f.write("\n\n" + "="*60 + "\n\n")
        f.write("EXAMPLE 2 - Emotional Question:\n")
        f.write(f"Question: {user_question2}\n")
        f.write(str(result2))
    
    print(f"\n✅ Dual response analysis saved to '{filename}'")
    print("\n🎯 SUMMARY: The system now provides both direct answers and contextual visual analysis!")