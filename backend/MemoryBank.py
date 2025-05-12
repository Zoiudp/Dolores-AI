import os
import time
import json
import numpy as np
import chromadb
from chromadb.utils import embedding_functions
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Union
import torch
from PIL import Image
from transformers import CLIPProcessor, CLIPModel
import math

class MemoryBank:
    """
    MemoryBank for a social robot to store and retrieve conversations, images, 
    summaries and user portraits with Ebbinghaus forgetting curve integration.
    """
    
    def __init__(self, 
                 persist_directory: str = "./memory_storage",
                 text_model_name: str = "all-MiniLM-L6-v2",
                 clip_model_name: str = "openai/clip-vit-base-patch32", 
                 forgetting_enabled: bool = True):
        """
        Initialize MemoryBank.
        
        Args:
            persist_directory: Directory to persist ChromaDB
            text_model_name: Name of the text embedding model
            clip_model_name: Name of the CLIP model for image embeddings
            forgetting_enabled: Enable Ebbinghaus forgetting curve
        """
        # Initialize ChromaDB client
        self.client = chromadb.PersistentClient(path=persist_directory)
        
        # Create text embedding function
        self.text_ef = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name=text_model_name
        )
        
        # Initialize CLIP model for image embeddings
        self.clip_processor = CLIPProcessor.from_pretrained(clip_model_name)
        self.clip_model = CLIPModel.from_pretrained(clip_model_name)
        
        # Initialize collections
        self.conversations_collection = self.client.get_or_create_collection(
            name="conversations", 
            embedding_function=self.text_ef,
            metadata={"hnsw:space": "cosine"}
        )
        
        self.images_collection = self.client.get_or_create_collection(
            name="emotional_images",
            metadata={"hnsw:space": "cosine"}
        )
        
        self.summaries_collection = self.client.get_or_create_collection(
            name="event_summaries",
            embedding_function=self.text_ef,
            metadata={"hnsw:space": "cosine"}
        )
        
        self.user_portrait_collection = self.client.get_or_create_collection(
            name="user_portraits",
            embedding_function=self.text_ef,
            metadata={"hnsw:space": "cosine"}
        )
        
        # Ebbinghaus forgetting curve parameters
        self.forgetting_enabled = forgetting_enabled
        self.default_memory_strength = 1.0
        
        # User metadata
        self.current_user = None
        self.session_count = 0
        
    def _get_clip_embedding(self, image):
        """Get CLIP embedding for an image."""
        with torch.no_grad():
            inputs = self.clip_processor(images=image, return_tensors="pt")
            image_features = self.clip_model.get_image_features(**inputs)
            # Normalize embedding
            image_embedding = image_features / image_features.norm(dim=1, keepdim=True)
            return image_embedding.squeeze().numpy().tolist()
    
    def _calculate_memory_score(self, last_access_time, memory_strength):
        """
        Calculate memory score based on Ebbinghaus forgetting curve.
        
        Score = e^(-(t/S)) where:
        - t is time elapsed since last access in days
        - S is memory strength
        """
        if not self.forgetting_enabled:
            return 1.0
            
        now = datetime.now()
        last_access = datetime.fromtimestamp(last_access_time)
        time_diff_days = (now - last_access).total_seconds() / (24 * 3600)
        
        # Apply Ebbinghaus forgetting curve
        memory_score = math.exp(-time_diff_days / memory_strength)
        return memory_score
    
    def add_conversation(self, 
                         user_id: str,
                         conversation_text: str, 
                         user_input: str = None,
                         bot_response: str = None,
                         metadata: Dict = None) -> str:
        """
        Add a conversation to memory.
        
        Args:
            user_id: Unique identifier for the user
            conversation_text: Full conversation text or turn
            user_input: User's input (optional)
            bot_response: Bot's response (optional)
            metadata: Additional metadata
            
        Returns:
            ID of the added conversation
        """
        # Set current user
        self.current_user = user_id
        
        # Create metadata
        if metadata is None:
            metadata = {}
            
        # Add required metadata
        timestamp = time.time()
        conversation_id = f"conv_{user_id}_{int(timestamp)}"
        
        metadata.update({
            "user_id": user_id,
            "timestamp": timestamp,
            "last_access_time": timestamp,
            "memory_strength": self.default_memory_strength,
            "type": "conversation"
        })
        
        # Add user input and bot response if provided
        if user_input:
            metadata["user_input"] = user_input
        if bot_response:
            metadata["bot_response"] = bot_response
        
        # Add to collection
        self.conversations_collection.add(
            ids=[conversation_id],
            documents=[conversation_text],
            metadatas=[metadata]
        )
        
        return conversation_id
    
    def add_emotional_image(self, 
                           user_id: str,
                           image: Image.Image,
                           emotion_description: str,
                           metadata: Dict = None) -> str:
        """
        Add an emotional image to memory.
        
        Args:
            user_id: Unique identifier for the user
            image: PIL Image
            emotion_description: Description of emotions in the image
            metadata: Additional metadata
            
        Returns:
            ID of the added image
        """
        # Create metadata
        if metadata is None:
            metadata = {}
            
        # Get image embedding
        image_embedding = self._get_clip_embedding(image)
        
        # Add required metadata
        timestamp = time.time()
        image_id = f"img_{user_id}_{int(timestamp)}"
        
        metadata.update({
            "user_id": user_id,
            "timestamp": timestamp,
            "last_access_time": timestamp,
            "memory_strength": self.default_memory_strength,
            "emotion_description": emotion_description,
            "type": "emotional_image"
        })
        
        # Save image path if needed
        img_path = f"./images/{image_id}.jpg"
        os.makedirs(os.path.dirname(img_path), exist_ok=True)
        image.save(img_path)
        metadata["image_path"] = img_path
        
        # Add to collection
        self.images_collection.add(
            ids=[image_id],
            embeddings=[image_embedding],
            metadatas=[metadata],
            documents=[emotion_description]
        )
        
        return image_id
    
    def add_event_summary(self,
                         user_id: str,
                         summary_text: str,
                         metadata: Dict = None) -> str:
        """
        Add an event summary to memory.
        
        Args:
            user_id: Unique identifier for the user
            summary_text: Summary of events
            metadata: Additional metadata
            
        Returns:
            ID of the added summary
        """
        # Create metadata
        if metadata is None:
            metadata = {}
            
        # Add required metadata
        timestamp = time.time()
        summary_id = f"sum_{user_id}_{int(timestamp)}"
        
        metadata.update({
            "user_id": user_id,
            "timestamp": timestamp,
            "last_access_time": timestamp,
            "memory_strength": self.default_memory_strength,
            "type": "event_summary"
        })
        
        # Add to collection
        self.summaries_collection.add(
            ids=[summary_id],
            documents=[summary_text],
            metadatas=[metadata]
        )
        
        return summary_id
    
    def update_user_portrait(self,
                           user_id: str,
                           portrait_text: str,
                           metadata: Dict = None) -> str:
        """
        Update user portrait in memory.
        
        Args:
            user_id: Unique identifier for the user
            portrait_text: User portrait text
            metadata: Additional metadata
            
        Returns:
            ID of the updated portrait
        """
        # Create metadata
        if metadata is None:
            metadata = {}
            
        # Add required metadata
        timestamp = time.time()
        portrait_id = f"portrait_{user_id}"
        
        metadata.update({
            "user_id": user_id,
            "timestamp": timestamp,
            "last_access_time": timestamp,
            "memory_strength": 5.0,  # User portraits have higher memory strength
            "type": "user_portrait"
        })
        
        # Check if portrait exists
        try:
            existing = self.user_portrait_collection.get(ids=[portrait_id])
            if existing["ids"]:
                # Update existing portrait
                self.user_portrait_collection.update(
                    ids=[portrait_id],
                    documents=[portrait_text],
                    metadatas=[metadata]
                )
            else:
                raise ValueError("Portrait not found")
        except (ValueError, KeyError):
            # Add new portrait
            self.user_portrait_collection.add(
                ids=[portrait_id],
                documents=[portrait_text],
                metadatas=[metadata]
            )
        
        return portrait_id
    
    def _update_memory_strength(self, collection, item_id):
        """
        Update memory strength when an item is accessed.
        
        Args:
            collection: ChromaDB collection
            item_id: ID of the memory item
        """
        if not self.forgetting_enabled:
            return
            
        try:
            item = collection.get(ids=[item_id])
            if not item["ids"]:
                return
                
            metadata = item["metadatas"][0]
            
            # Increase memory strength and reset last access time
            new_strength = metadata["memory_strength"] + 1.0
            new_metadata = metadata.copy()
            new_metadata["memory_strength"] = new_strength
            new_metadata["last_access_time"] = time.time()
            
            # Update in collection
            collection.update(
                ids=[item_id],
                metadatas=[new_metadata]
            )
        except Exception as e:
            print(f"Error updating memory strength: {e}")
    
    def retrieve_conversations(self, 
                              user_id: str,
                              query_text: str,
                              n_results: int = 5) -> List[Dict]:
        """
        Retrieve relevant conversations.
        
        Args:
            user_id: User ID
            query_text: Query text
            n_results: Number of results to return
            
        Returns:
            List of relevant conversations with memory scores
        """
        # Query the collection
        results = self.conversations_collection.query(
            query_texts=[query_text],
            n_results=n_results * 2,  # Get more results than needed for filtering
            where={"user_id": user_id}
        )
        
        retrieved_items = []
        
        if not results["ids"][0]:
            return retrieved_items
            
        # Process results with memory scores
        for i, (item_id, document, metadata) in enumerate(zip(
            results["ids"][0], results["documents"][0], results["metadatas"][0]
        )):
            # Calculate memory score based on Ebbinghaus curve
            memory_score = self._calculate_memory_score(
                metadata["last_access_time"], 
                metadata["memory_strength"]
            )
            
            # Add item with memory score
            retrieved_items.append({
                "id": item_id,
                "text": document,
                "metadata": metadata,
                "memory_score": memory_score
            })
            
            # Update memory strength for retrieved items
            self._update_memory_strength(self.conversations_collection, item_id)
        
        # Sort by memory score and limit results
        retrieved_items.sort(key=lambda x: x["memory_score"], reverse=True)
        return retrieved_items[:n_results]
    
    def retrieve_emotional_images(self,
                                user_id: str,
                                query_text: str = None,
                                query_image: Image.Image = None,
                                n_results: int = 3) -> List[Dict]:
        """
        Retrieve relevant emotional images.
        
        Args:
            user_id: User ID
            query_text: Text query (optional)
            query_image: Image query (optional)
            n_results: Number of results to return
            
        Returns:
            List of relevant images with memory scores
        """
        if query_image:
            # Use image embedding for query
            query_embedding = self._get_clip_embedding(query_image)
            results = self.images_collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results * 2,
                where={"user_id": user_id}
            )
            # For query results, we need to handle nested lists
            if results["ids"] and len(results["ids"]) > 0:
                ids = results["ids"][0]
                documents = results["documents"][0]
                metadatas = results["metadatas"][0]
            else:
                return []
        elif query_text:
            # Use text for query
            results = self.images_collection.query(
                query_texts=[query_text],
                n_results=n_results * 2,
                where={"user_id": user_id}
            )
            # For query results, we need to handle nested lists
            if results["ids"] and len(results["ids"]) > 0:
                ids = results["ids"][0]
                documents = results["documents"][0]
                metadatas = results["metadatas"][0]
            else:
                return []
        else:
            # Get recent images
            results = self.images_collection.get(
                where={"user_id": user_id},
                limit=n_results * 2
            )
            
            if not results["ids"]:
                return []
                
            # For get results, the lists are not nested
            ids = results["ids"]
            documents = results["documents"]
            metadatas = results["metadatas"]
            
            # Sort by timestamp
            items = list(zip(ids, documents, metadatas))
            items.sort(key=lambda x: x[2]["timestamp"], reverse=True)
            
            # Unpack sorted items
            ids = [item[0] for item in items[:n_results * 2]]
            documents = [item[1] for item in items[:n_results * 2]]
            metadatas = [item[2] for item in items[:n_results * 2]]
        
        retrieved_items = []
        
        # Process results with memory scores
        for i, (item_id, document, metadata) in enumerate(zip(
            ids, documents, metadatas
        )):
            # Calculate memory score
            memory_score = self._calculate_memory_score(
                metadata["last_access_time"], 
                metadata["memory_strength"]
            )
            
            # Add item with memory score
            retrieved_items.append({
                "id": item_id,
                "description": document,
                "metadata": metadata,
                "memory_score": memory_score,
                "image_path": metadata.get("image_path")
            })
            
            # Update memory strength for retrieved items
            self._update_memory_strength(self.images_collection, item_id)
        
        # Sort by memory score and limit results
        retrieved_items.sort(key=lambda x: x["memory_score"], reverse=True)
        return retrieved_items[:n_results]
    
    def retrieve_event_summaries(self,
                               user_id: str,
                               query_text: str = None,
                               n_results: int = 3) -> List[Dict]:
        """
        Retrieve event summaries.
        
        Args:
            user_id: User ID
            query_text: Query text (optional)
            n_results: Number of results to return
            
        Returns:
            List of relevant summaries with memory scores
        """
        if query_text:
            # Query with text
            results = self.summaries_collection.query(
                query_texts=[query_text],
                n_results=n_results * 2,
                where={"user_id": user_id}
            )
            
            if not results["ids"][0]:
                return []
                
            ids = results["ids"][0]
            documents = results["documents"][0]
            metadatas = results["metadatas"][0]
        else:
            # Get recent summaries
            results = self.summaries_collection.get(
                where={"user_id": user_id}
            )
            
            if not results["ids"]:
                return []
                
            # Sort by timestamp (recent first)
            items = []
            for i, (item_id, document, metadata) in enumerate(zip(
                results["ids"], results["documents"], results["metadatas"]
            )):
                items.append((item_id, document, metadata))
            
            items.sort(key=lambda x: x[2]["timestamp"], reverse=True)
            
            # Take most recent n_results * 2
            ids = [item[0] for item in items[:n_results * 2]]
            documents = [item[1] for item in items[:n_results * 2]]
            metadatas = [item[2] for item in items[:n_results * 2]]
        
        retrieved_items = []
        
        # Process results with memory scores
        for i, (item_id, document, metadata) in enumerate(zip(ids, documents, metadatas)):
            # Calculate memory score
            memory_score = self._calculate_memory_score(
                metadata["last_access_time"], 
                metadata["memory_strength"]
            )
            
            # Add item with memory score
            retrieved_items.append({
                "id": item_id,
                "text": document,
                "metadata": metadata,
                "memory_score": memory_score
            })
            
            # Update memory strength for retrieved items
            self._update_memory_strength(self.summaries_collection, item_id)
        
        # Sort by memory score and limit results
        retrieved_items.sort(key=lambda x: x["memory_score"], reverse=True)
        return retrieved_items[:n_results]
    
    def get_user_portrait(self, user_id: str) -> Optional[Dict]:
        """
        Get user portrait.
        
        Args:
            user_id: User ID
            
        Returns:
            User portrait or None if not found
        """
        portrait_id = f"portrait_{user_id}"
        
        try:
            result = self.user_portrait_collection.get(ids=[portrait_id])
            
            if not result["ids"]:
                return None
                
            # Update memory strength
            self._update_memory_strength(self.user_portrait_collection, portrait_id)
            
            return {
                "id": portrait_id,
                "text": result["documents"][0],
                "metadata": result["metadatas"][0]
            }
        except Exception:
            return None
    
    def increment_session_count(self, user_id: str):
        """
        Increment session count for user.
        
        Args:
            user_id: User ID
        """
        self.current_user = user_id
        key = f"session_count_{user_id}"
        
        try:
            # Try to get existing session metadata
            result = self.client.get_or_create_collection("session_metadata").get(
                ids=[key]
            )
            
            if result["ids"]:
                count = int(result["documents"][0]) + 1
                self.client.get_or_create_collection("session_metadata").update(
                    ids=[key],
                    documents=[str(count)],
                    metadatas=[{"user_id": user_id}]
                )
                self.session_count = count
            else:
                # First session
                self.client.get_or_create_collection("session_metadata").add(
                    ids=[key],
                    documents=["1"],
                    metadatas=[{"user_id": user_id}]
                )
                self.session_count = 1
        except Exception:
            # First session or error
            self.client.get_or_create_collection("session_metadata").add(
                ids=[key],
                documents=["1"],
                metadatas=[{"user_id": user_id}]
            )
            self.session_count = 1
    
    def clean_expired_memories(self, threshold: float = 0.1):
        """
        Clean up memories with scores below threshold.
        
        Args:
            threshold: Memory score threshold for deletion
        """
        if not self.forgetting_enabled:
            return
            
        for collection in [
            self.conversations_collection, 
            self.images_collection,
            self.summaries_collection
        ]:
            # Get all items
            results = collection.get()
            
            if not results["ids"]:
                continue
                
            # Check each item's memory score
            ids_to_delete = []
            
            for item_id, metadata in zip(results["ids"], results["metadatas"]):
                # Skip user portraits (they don't expire)
                if metadata.get("type") == "user_portrait":
                    continue
                    
                memory_score = self._calculate_memory_score(
                    metadata["last_access_time"],
                    metadata["memory_strength"]
                )
                
                if memory_score < threshold:
                    ids_to_delete.append(item_id)
            
            # Delete expired memories
            if ids_to_delete:
                collection.delete(ids=ids_to_delete)
                print(f"Deleted {len(ids_to_delete)} expired memories from {collection.name}")

    def get_prompt_context(self, user_id: str, user_input: str) -> Dict:
        """
        Get all context for the prompt template.
        
        Args:
            user_id: User ID
            user_input: Current user input
            
        Returns:
            Dict with all context for the prompt
        """
        # Get relevant conversations
        relevant_convs = self.retrieve_conversations(user_id, user_input)
        conv_text = "\n\n".join([
            f"[Conversation from {datetime.fromtimestamp(c['metadata']['timestamp']).strftime('%Y-%m-%d %H:%M')}]\n{c['text']}"
            for c in relevant_convs
        ])
        
        # Get emotional images context
        emotional_imgs = self.retrieve_emotional_images(user_id, user_input)
        img_text = "\n".join([
            f"[Emotional state from {datetime.fromtimestamp(img['metadata']['timestamp']).strftime('%Y-%m-%d %H:%M')}]\n{img['description']}"
            for img in emotional_imgs
        ])
        
        # Get event summaries
        summaries = self.retrieve_event_summaries(user_id, user_input)
        summary_text = "\n\n".join([
            f"[Event from {datetime.fromtimestamp(s['metadata']['timestamp']).strftime('%Y-%m-%d %H:%M')}]\n{s['text']}"
            for s in summaries
        ])
        
        # Get user portrait
        portrait = self.get_user_portrait(user_id)
        portrait_text = portrait["text"] if portrait else "No user portrait available yet."
        
        # Get session count
        self.increment_session_count(user_id)
        
        return {
            "current_datetime": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "user_name": user_id,
            "session_count": self.session_count,
            "memory_records": conv_text if conv_text else "No relevant past conversations.",
            "emotional_image_context": img_text if img_text else "No emotional image analysis available.",
            "user_portrait": portrait_text,
            "event_summaries": summary_text if summary_text else "No event summaries available.",
            "user_input": user_input
        }


# Example usage
if __name__ == "__main__":
    
    # Initialize MemoryBank
    memory_bank = MemoryBank(
        persist_directory="./memory_storage",
        forgetting_enabled=True
    )
    
    # Example user
    user_id = "user123"
    
    # Add some conversations
    memory_bank.add_conversation(
        user_id=user_id,
        conversation_text="User: I've been feeling a bit down lately.\nBot: I'm sorry to hear that. What's been bothering you?",
        user_input="I've been feeling a bit down lately.",
        bot_response="I'm sorry to hear that. What's been bothering you?"
    )
    
    # Add user portrait
    memory_bank.update_user_portrait(
        user_id=user_id,
        portrait_text="The user is thoughtful and introspective. They enjoy discussing philosophy and science. They have mentioned feeling anxious about work deadlines several times."
    )
    
    # Add event summary
    memory_bank.add_event_summary(
        user_id=user_id,
        summary_text="The user talked about their job interview. They were nervous but felt it went well overall. They mentioned they would hear back within a week."
    )

    
    # Clean up expired memories (would be done periodically)
    memory_bank.clean_expired_memories()