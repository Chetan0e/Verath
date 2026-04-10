from collections import defaultdict
from typing import Dict, List, Set, Tuple
import networkx as nx
import json

class MemoryGraph:
    def __init__(self):
        try:
            self.graph = nx.DiGraph()
        except ImportError:
            # Fallback if networkx is not available
            self.graph = defaultdict(list)
            self._nx_available = False
        else:
            self._nx_available = True
        
        self.concept_connections = defaultdict(list)
        self.speaker_connections = defaultdict(set)
        self.topic_clusters = defaultdict(list)
    
    def add_memory(self, memory: dict):
        """Add memory to the graph and build connections."""
        memory_id = memory.get('id', id(memory))
        text = memory.get('text', '')
        speaker = memory.get('speaker', 'unknown')
        timestamp = memory.get('timestamp', 0)
        importance = memory.get('importance', 0.5)
        
        if self._nx_available:
            # Add node to NetworkX graph
            self.graph.add_node(
                memory_id,
                text=text,
                speaker=speaker,
                timestamp=timestamp,
                importance=importance
            )
        else:
            # Fallback to simple dict structure
            self.graph[memory_id] = {
                'text': text,
                'speaker': speaker,
                'timestamp': timestamp,
                'importance': importance,
                'connections': []
            }
        
        # Extract concepts (simple keyword extraction)
        concepts = self._extract_concepts(text)
        
        # Add concept connections
        for concept in concepts:
            self.concept_connections[concept].append(memory_id)
        
        # Add speaker connections
        self.speaker_connections[speaker].add(memory_id)
        
        # Create topic clusters
        topic = self._determine_topic(text)
        self.topic_clusters[topic].append(memory_id)
        
        # Connect to related memories
        self._connect_to_related_memories(memory_id, concepts, speaker)
    
    def _extract_concepts(self, text: str) -> List[str]:
        """Extract key concepts from text."""
        # Simple keyword extraction - could be enhanced with NLP
        words = text.lower().split()
        # Filter out common stop words
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might', 'can', 'must'}
        
        concepts = [word for word in words if len(word) > 3 and word not in stop_words]
        
        # Return top concepts by frequency (simplified)
        from collections import Counter
        concept_counts = Counter(concepts)
        return [concept for concept, count in concept_counts.most_common(5)]
    
    def _determine_topic(self, text: str) -> str:
        """Determine the main topic of the text."""
        text_lower = text.lower()
        
        # Simple topic classification
        topics = {
            'work': ['work', 'job', 'project', 'meeting', 'deadline', 'task', 'office'],
            'personal': ['family', 'friend', 'home', 'personal', 'life', 'relationship'],
            'learning': ['learn', 'study', 'course', 'book', 'knowledge', 'education'],
            'health': ['health', 'doctor', 'exercise', 'diet', 'medical', 'fitness'],
            'finance': ['money', 'pay', 'cost', 'price', 'financial', 'budget', 'expense']
        }
        
        for topic, keywords in topics.items():
            if any(keyword in text_lower for keyword in keywords):
                return topic
        
        return 'general'
    
    def _connect_to_related_memories(self, memory_id: str, concepts: List[str], speaker: str):
        """Connect memory to related memories in the graph."""
        if not self._nx_available:
            return
        
        # Find memories with shared concepts
        for concept in concepts:
            related_memories = self.concept_connections.get(concept, [])
            for related_id in related_memories:
                if related_id != memory_id:
                    # Add weighted edge based on concept similarity
                    current_weight = self.graph.get_edge_data(memory_id, related_id, {}).get('weight', 0)
                    self.graph.add_edge(memory_id, related_id, weight=current_weight + 1)
        
        # Find memories from same speaker
        speaker_memories = self.speaker_connections.get(speaker, set())
        for speaker_memory_id in speaker_memories:
            if speaker_memory_id != memory_id:
                current_weight = self.graph.get_edge_data(memory_id, speaker_memory_id, {}).get('weight', 0)
                self.graph.add_edge(memory_id, speaker_memory_id, weight=current_weight + 0.5)
    
    def get_related_memories(self, memory_id: str, max_results: int = 5) -> List[dict]:
        """Get memories related to a specific memory."""
        if not self._nx_available:
            return []
        
        if memory_id not in self.graph:
            return []
        
        # Get neighbors with edge weights
        neighbors = []
        for neighbor in self.graph.neighbors(memory_id):
            edge_data = self.graph.get_edge_data(memory_id, neighbor)
            weight = edge_data.get('weight', 0)
            neighbors.append((neighbor, weight))
        
        # Sort by weight and return top results
        neighbors.sort(key=lambda x: x[1], reverse=True)
        
        related_memories = []
        for neighbor_id, weight in neighbors[:max_results]:
            if neighbor_id in self.graph.nodes:
                node_data = self.graph.nodes[neighbor_id]
                related_memories.append({
                    'id': neighbor_id,
                    'text': node_data.get('text', ''),
                    'speaker': node_data.get('speaker', 'unknown'),
                    'timestamp': node_data.get('timestamp', 0),
                    'importance': node_data.get('importance', 0.5),
                    'relation_strength': weight
                })
        
        return related_memories
    
    def get_topic_summary(self, topic: str) -> Dict:
        """Get summary of a specific topic."""
        if topic not in self.topic_clusters:
            return {'topic': topic, 'count': 0, 'memories': []}
        
        memories = self.topic_clusters[topic]
        speakers = set()
        if self._nx_available:
            speakers = set(self.graph.nodes[mid].get('speaker', 'unknown') for mid in memories if mid in self.graph.nodes)
        
        return {
            'topic': topic,
            'count': len(memories),
            'memory_ids': memories,
            'speakers': list(speakers)
        }
    
    def get_speaker_network(self, speaker: str) -> Dict:
        """Get network information for a specific speaker."""
        if speaker not in self.speaker_connections:
            return {'speaker': speaker, 'memory_count': 0, 'connections': []}
        
        memories = self.speaker_connections[speaker]
        connections = []
        
        for memory_id in memories:
            related = self.get_related_memories(memory_id, max_results=3)
            connections.extend(related)
        
        return {
            'speaker': speaker,
            'memory_count': len(memories),
            'connections': connections[:10]  # Limit to prevent explosion
        }
    
    def export_graph_data(self) -> Dict:
        """Export graph data for visualization."""
        nodes = []
        edges = []
        
        if self._nx_available:
            for node_id in self.graph.nodes():
                node_data = self.graph.nodes[node_id]
                nodes.append({
                    'id': node_id,
                    'label': node_data.get('text', '')[:50] + '...',
                    'speaker': node_data.get('speaker', 'unknown'),
                    'importance': node_data.get('importance', 0.5),
                    'timestamp': node_data.get('timestamp', 0)
                })
            
            for edge in self.graph.edges():
                edge_data = self.graph.get_edge_data(edge[0], edge[1])
                edges.append({
                    'source': edge[0],
                    'target': edge[1],
                    'weight': edge_data.get('weight', 1)
                })
        
        return {
            'nodes': nodes,
            'edges': edges,
            'topics': dict(self.topic_clusters),
            'speakers': dict(self.speaker_connections)
        }

# Legacy functions for backward compatibility
graph = defaultdict(list)

def add_relation(a: str, b: str):
    graph[a].append(b)

def build_graph(memories):
    graph.clear()
    for mem in memories:
        words = mem.get("text", "").split()
        for index in range(len(words) - 1):
            add_relation(words[index], words[index + 1])
    return dict(graph)

# Global memory graph instance
memory_graph = MemoryGraph()

def get_memory_graph() -> MemoryGraph:
    """Get the global memory graph instance."""
    return memory_graph

def update_memory_graph(memory: dict):
    """Update the memory graph with a new memory."""
    memory_graph.add_memory(memory)
