"""
Step 3 Runner · pytest

Runs the complete test suite (Functional + Golden Master) via the Execution
MCP client. On FAIL, error output is routed back to the Converter Agent
for self-correction.
"""
from infrastructure.clients.execution_client import ExecutionClient
from models.artifacts import ValidationResult
from utils.logger import get_logger

logger = get_logger("PytestRunner")


class PytestRunner:
    def __init__(self, executor: ExecutionClient) -> None:
        self.executor = executor

    async def run(self, test_file_path: str, module_name: str) -> ValidationResult:
        logger.info(f"Running pytest for: {module_name}")

        result = await self.executor.run_pytest(test_file_path)

        if result.passed:
            logger.info(f"[{module_name}] pytest PASS ✓")
            return ValidationResult(passed=True, details=result.stdout)

        # Build a focused error report for the Converter Agent
        error_lines = [
            line for line in result.combined.splitlines()
            if any(kw in line for kw in ("FAILED", "ERROR", "AssertionError", "assert", "E "))
        ]
        logger.warning(f"[{module_name}] pytest FAIL — {len(error_lines)} error lines")
        return ValidationResult(passed=False, issues=error_lines, details=result.combined)
