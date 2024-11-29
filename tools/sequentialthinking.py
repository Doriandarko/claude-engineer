from tools.base import BaseTool
import json
from typing import Dict, Any
import asyncio
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown

class SequentialThinkingTool(BaseTool):
    name = "sequentialthinking"
    description = '''
    A detailed tool for dynamic and reflective problem-solving through thoughts.
This tool helps analyze problems through a flexible thinking process that can adapt and evolve.
Each thought can build on, question, or revise previous insights as understanding deepens.

When to use this tool:
- Breaking down complex problems into steps
- Planning and design with room for revision
- Analysis that might need course correction
- Problems where the full scope might not be clear initially

Key features:
- You can adjust total_thoughts up or down as you progress
- You can question or revise previous thoughts
- You can add more thoughts even after reaching what seemed like the end
- You can express uncertainty and explore alternative approaches
- Not every thought needs to build linearly - you can branch or backtrack

Parameters explained:
- thought: Your current thinking step, which can include:
  * Regular analytical steps
  * Revisions of previous thoughts
  * Questions about previous decisions
  * Realizations about needing more analysis
  * Changes in approach
- next_thought_needed: True if you need more thinking, even if at what seemed like the end
- thought_number: Current number in sequence (can go beyond initial total if needed)
- total_thoughts: Current estimate of thoughts needed (can be adjusted up/down)
- is_revision: A boolean indicating if this thought revises previous thinking
- revises_thought: If is_revision is true, which thought number is being reconsidered
- branch_from_thought: If branching, which thought number is the branching point
- branch_id: Identifier for the current branch (if any)
- needs_more_thoughts: If reaching end but realizing more thoughts needed

You should:
1. Start with an initial estimate of needed thoughts, but be ready to adjust
2. Feel free to question or revise previous thoughts
3. Don't hesitate to add more thoughts if needed, even at the "end"
4. Express uncertainty when present
5. Mark thoughts that revise previous thinking or branch into new paths
6. Only set next_thought_needed to false when truly done
    '''

    input_schema = {
        "type": "object",
        "properties": {
            "thought": {
                "type": "string",
                "description": "Your current thinking step"
            },
            "next_thought_needed": {
                "type": "boolean",
                "description": "Whether another thought step is needed"
            },
            "thought_number": {
                "type": "integer",
                "description": "Current thought number",
                "minimum": 1
            },
            "total_thoughts": {
                "type": "integer",
                "description": "Estimated total thoughts needed",
                "minimum": 1
            },
            "is_revision": {
                "type": "boolean",
                "description": "Whether this revises previous thinking",
                "default": False
            },
            "revises_thought": {
                "type": "integer",
                "description": "Which thought is being reconsidered",
                "minimum": 1
            },
            "branch_from_thought": {
                "type": "integer",
                "description": "Branching point thought number",
                "minimum": 1
            },
            "branch_id": {
                "type": "string",
                "description": "Branch identifier"
            },
            "needs_more_thoughts": {
                "type": "boolean",
                "description": "If more thoughts are needed",
                "default": False
            }
        },
        "required": ["thought", "next_thought_needed", "thought_number", "total_thoughts"]
    }

    def __init__(self):
        self.thought_history = []
        self.branches = {}
        self.console = Console()

    def _format_thought(self, thought_data: Dict[str, Any]) -> str:
        """Format a thought with its context for display"""
        thought_num = thought_data['thought_number']
        total = thought_data['total_thoughts']
        thought = thought_data['thought']
        
        # Determine thought type and formatting
        if thought_data.get('is_revision'):
            prefix = "🔄 [bold yellow]Revision"
            context = f" (revising thought {thought_data['revises_thought']})"
        elif thought_data.get('branch_from_thought'):
            prefix = "🌿 [bold green]Branch"
            context = f" (from thought {thought_data['branch_from_thought']}, ID: {thought_data['branch_id']})"
        else:
            prefix = "💭 [bold blue]Thought"
            context = ""
            
        # Format the thought panel
        header = f"{prefix} {thought_num}/{total}{context}[/]"
        return Panel(
            Markdown(thought),
            title=header,
            border_style="cyan"
        )

    def execute(self, **kwargs) -> str:
        try:
            # Process input
            thought_data = {
                'thought_number': kwargs['thought_number'],
                'total_thoughts': kwargs['total_thoughts'],
                'thought': kwargs['thought'],
                'is_revision': kwargs.get('is_revision', False),
                'revises_thought': kwargs.get('revises_thought'),
                'branch_from_thought': kwargs.get('branch_from_thought'),
                'branch_id': kwargs.get('branch_id'),
                'needs_more_thoughts': kwargs.get('needs_more_thoughts', False)
            }

            # Dynamic thought adjustment
            if thought_data['thought_number'] > thought_data['total_thoughts']:
                thought_data['total_thoughts'] = thought_data['thought_number']

            # Update histories
            self.thought_history.append(thought_data)
            
            # Handle branching
            if thought_data['branch_from_thought'] and thought_data['branch_id']:
                if thought_data['branch_id'] not in self.branches:
                    self.branches[thought_data['branch_id']] = []
                self.branches[thought_data['branch_id']].append(thought_data)

            # Display formatted thought
            self.console.print(self._format_thought(thought_data))

            # Prepare result
            result = {
                'thought_number': thought_data['thought_number'],
                'total_thoughts': thought_data['total_thoughts'],
                'next_thought_needed': kwargs['next_thought_needed'],
                'branches': list(self.branches.keys()),
                'thought_history_length': len(self.thought_history)
            }

            return json.dumps(result, indent=2)

        except Exception as e:
            return json.dumps({
                'error': str(e),
                'status': 'failed'
            }, indent=2) 