# src/ui/utils/formatting.py
import re
from typing import Dict, Any, List

def format_response(response: Dict[str, Any]) -> str:
    """Format an AI response for display."""
    formatted = response['answer']
    
    # Ensure code blocks are properly formatted
    formatted = re.sub(
        r'```(?!python|bash|json|yaml)',
        '```python',
        formatted
    )
    
    # Add source attribution if available
    if 'sources' in response:
        formatted += "\n\n**Sources:**"
        for source in response['sources']:
            formatted += f"\n- {source['file']}"
    
    return formatted

def format_code_snippet(code: str) -> str:
    """Format a code snippet for display."""
    # Remove leading/trailing whitespace
    code = code.strip()
    
    # Ensure consistent indentation
    lines = code.split('\n')
    if len(lines) > 1:
        min_indent = min(len(line) - len(line.lstrip()) 
                        for line in lines[1:] if line.strip())
        lines = [lines[0]] + [line[min_indent:] for line in lines[1:]]
        code = '\n'.join(lines)
    
    return code

def format_error(error: str) -> str:
    """Format an error message for display."""
    return f"""
    ❌ Error:
    ```
    {error}
    ```
    Please try rephrasing your question or try again later.
    """

def format_api_reference(api_details: Dict[str, Any]) -> str:
    """Format API reference documentation."""
    formatted = []
    
    for name, details in api_details.items():
        section = [f"### {name}"]
        
        if details.get('docstring'):
            section.append(details['docstring'])
        
        if details.get('parameters'):
            section.append("\n**Parameters:**")
            for param in details['parameters']:
                section.append(f"- `{param['name']}`: {param.get('type', 'Any')}")
        
        if details.get('return_type'):
            section.append(f"\n**Returns:** `{details['return_type']}`")
        
        if details.get('examples'):
            section.append("\n**Examples:**")
            for example in details['examples']:
                section.append(f"```python\n{example}\n```")
        
        formatted.append('\n'.join(section))
    
    return '\n\n'.join(formatted)

def format_suggested_questions(questions: List[str]) -> str:
    """Format suggested follow-up questions."""
    return '\n'.join([f"- {q}" for q in questions])