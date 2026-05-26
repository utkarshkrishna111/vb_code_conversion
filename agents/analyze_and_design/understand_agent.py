"""
Step 1-A · Understand Agent

Extracts business logic, data structures, external API calls, and control
flow from a Java source file. Returns a structured AnalysisResult.
"""
from pathlib import Path

from agents.base_agent import BaseAgent
from models.artifacts import AnalysisResult
from utils.prompts import UNDERSTAND_SYSTEM


class UnderstandAgent(BaseAgent):
    def __init__(self):
        super().__init__("UnderstandAgent")

    def run(self, source_code: str, module_name: str, source_file_path: str) -> AnalysisResult:
        self.logger.info(f"Analysing module: {module_name}")

        response = self._call_llm(
            system=UNDERSTAND_SYSTEM,
            messages=[
                {
                    "role": "user",
                    "content": (
                        f"Analyse this Java module named '{module_name}'.\n\n"
                        f"```java\n{source_code}\n```"
                    ),
                }
            ],
            max_tokens=4096,
        )

        data = self._parse_json(response)
        data["module_name"] = module_name
        data["source_file_path"] = source_file_path

        result = AnalysisResult(**data)
        self.logger.info(
            f"[{module_name}] complexity={result.complexity_score:.2f}  "
            f"methods={len(result.control_flow.get('methods', []))}"
        )
        return result
