from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from typing_extensions import TypedDict


class EvaluationResult(TypedDict):
    accuracy_score: float
    matches_ground_truth: bool
    explanation: str
    missing_conditions: List[str]
    extra_conditions: List[str]


@dataclass
class ParserConfig:
    """Configuration for JSON parsing"""

    float_fields: List[str] = ("accuracy_score",)
    bool_fields: List[str] = ("matches_ground_truth",)
    list_fields: List[str] = ("missing_conditions", "extra_conditions")
    str_fields: List[str] = ("explanation",)


class LLMJSONParser:
    """A forgiving JSON parser for LLM outputs"""

    @staticmethod
    def clean_json_string(text: str) -> str:
        """Clean and prepare JSON string for parsing"""
        import re

        # Remove any text before the first {
        text = re.sub(r"^[^{]*", "", text)
        # Remove any text after the last }
        text = re.sub(r"[^}]*$", "", text)

        # Fix common JSON formatting issues
        text = (
            text.replace("\n", " ")
            .replace("`", "")
            .replace("json", "")
            .replace("JSON", "")
            .strip()
        )

        # Fix missing quotes around keys
        text = re.sub(r"(\s*{?\s*)(\w+)(\s*:)", r'\1"\2"\3', text)

        # Fix single quotes to double quotes
        text = text.replace("'", '"')

        # Fix missing quotes around string values
        text = re.sub(r':\s*([^"][^,}\s][^,}\s]*)', r': "\1"', text)

        # Fix trailing commas
        text = re.sub(r",(\s*[}\]])", r"\1", text)

        return text

    @staticmethod
    def _convert_value(value: Any, target_type: type) -> Any:
        """Convert value to target type with proper error handling"""
        try:
            if target_type == float:
                if isinstance(value, str):
                    return (
                        float(value.strip("%")) / 100 if "%" in value else float(value)
                    )
                return float(value)
            elif target_type == bool:
                if isinstance(value, str):
                    return value.lower() in ["true", "yes", "1"]
                return bool(value)
            elif target_type == list:
                if isinstance(value, str):
                    return [item.strip() for item in value.split(",") if item.strip()]
                elif isinstance(value, list):
                    return [str(item) for item in value if item]
                return []
            elif target_type == str:
                return str(value) if value is not None else ""
            return value
        except (ValueError, TypeError):
            return target_type()

    @classmethod
    def validate_evaluation_json(
        cls, data: Dict[str, Any]
    ) -> Optional[EvaluationResult]:
        """Validate and fix evaluation JSON structure"""
        if not isinstance(data, dict):
            return None

        config = ParserConfig()
        result: Dict[str, Any] = {}

        try:
            # Convert float fields
            for field in config.float_fields:
                value = data.get(field)
                result[field] = cls._convert_value(value, float)

            # Convert boolean fields
            for field in config.bool_fields:
                value = data.get(field)
                result[field] = cls._convert_value(value, bool)

            # Convert list fields
            for field in config.list_fields:
                value = data.get(field, [])
                result[field] = cls._convert_value(value, list)

            # Convert string fields
            for field in config.str_fields:
                value = data.get(field)
                result[field] = cls._convert_value(value, str)

            return result  # type: ignore

        except Exception as e:
            print(f"Error validating JSON structure: {str(e)}")
            return None

    @classmethod
    def parse(cls, text: str) -> Optional[EvaluationResult]:
        """Parse LLM output into valid JSON"""
        import json

        if not text:
            return None

        try:
            # First try direct JSON parsing
            data = json.loads(text)
            return cls.validate_evaluation_json(data)
        except json.JSONDecodeError:
            try:
                # Clean and try again
                cleaned_text = cls.clean_json_string(text)
                data = json.loads(cleaned_text)
                return cls.validate_evaluation_json(data)
            except json.JSONDecodeError as e:
                print(f"Failed to parse JSON even after cleaning: {str(e)}")
                return None
