import pandas as pd
from groq import Groq
import json
from typing import List, Dict, Any
import time
from tqdm import tqdm
import os
import sys
import pathlib
import logging
from datetime import datetime

# Set up logging
log_filename = f"evaluation_errors_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
logging.basicConfig(
    filename=log_filename,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

# Create console handler for errors that writes to stderr
console_handler = logging.StreamHandler(sys.stderr)
console_handler.setLevel(logging.ERROR)
logging.getLogger().addHandler(console_handler)

# Add parent directory to Python path to allow importing models
sys.path.append(str(pathlib.Path(__file__).parent.parent))

from models.pathology import extract_pathology  # Import the existing function
from utils.json_parser import LLMJSONParser


class PathologyEvaluator:
    def __init__(self, csv_path: str):
        """Initialize evaluator with path to CSV containing medical cases"""
        self.df = pd.read_csv(csv_path)
        self.client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        self.results: List[Dict[str, Any]] = []
        self.logger = logging.getLogger(__name__)

    def _create_evaluation_prompt(
        self, note: str, extracted: str, ground_truth: str
    ) -> str:
        """Create prompt for LLM to evaluate pathology extraction accuracy"""
        return f"""Act as a medical expert evaluating the accuracy of pathology extraction from medical notes.
        Compare the extracted pathology against the ground truth and return a JSON response.
        
        MEDICAL NOTE:
        {note}

        EXTRACTED PATHOLOGY:
        {extracted}
        
        GROUND TRUTH PATHOLOGY:
        {ground_truth}

        Return a JSON object with this exact format:
        {{
            "accuracy_score": <float between 0 and 1>,
            "matches_ground_truth": <boolean>,
            "explanation": "<brief explanation of score>",
            "missing_conditions": ["<any conditions present in ground truth but missing in extraction>"],
            "extra_conditions": ["<any conditions in extraction not present in ground truth>"]
        }}

        EXAMPLE EVALUATION:
        {{
            "accuracy_score": 0.8,
            "matches_ground_truth": false,
            "explanation": "Extracted 'hypercalcemia' but missed 'kidney stones'",
            "missing_conditions": ["kidney stones"],
            "extra_conditions": []
        }}

        Only return valid JSON, nothing else."""

    def evaluate_sample(self, sample_size: int = 100, seed: int = 42) -> Dict[str, Any]:
        """Evaluate a random sample of pathology extractions"""
        sampled_df = self.df.sample(n=min(sample_size, len(self.df)), random_state=seed)

        progress_bar = tqdm(sampled_df.iterrows(), total=len(sampled_df))
        for _, row in progress_bar:
            try:
                extracted_pathology = extract_pathology(row["Prompt"])
                prompt = self._create_evaluation_prompt(
                    row["Prompt"], extracted_pathology, row["Extracted_Pathology"]
                )

                response = self.client.chat.completions.create(
                    messages=[{"role": "user", "content": prompt}],
                    model="llama-3.1-70b-versatile",
                )

                if response.choices[0].message.content:
                    result = LLMJSONParser.parse(response.choices[0].message.content)
                    if result:
                        result["original_note"] = row["Prompt"]
                        result["extracted_pathology"] = extracted_pathology
                        result["ground_truth"] = row["Extracted_Pathology"]
                        self.results.append(result)
                    else:
                        self.logger.error(
                            f"Failed to parse LLM response for note: {row['Prompt'][:100]}..."
                        )
                    time.sleep(1)  # Rate limiting

            except Exception as e:
                self.logger.error(
                    f"Error processing row: {str(e)}\nNote: {row['Prompt'][:100]}..."
                )
                continue

            # Update progress bar description with current metrics
            if self.results:
                accuracy = sum(r["accuracy_score"] for r in self.results) / len(
                    self.results
                )
                progress_bar.set_description(f"Avg Accuracy: {accuracy:.2%}")

        return self._generate_report()

    def _generate_report(self) -> Dict[str, Any]:
        """Generate evaluation report"""
        if not self.results:
            return {
                "error": "No results generated",
                "overall_metrics": {
                    "average_accuracy": 0,
                    "exact_matches": 0,
                    "samples_evaluated": 0,
                    "perfect_extractions": 0,
                    "poor_extractions": 0,
                },
            }

        accuracy_scores = [r["accuracy_score"] for r in self.results]
        match_scores = [r["matches_ground_truth"] for r in self.results]

        report = {
            "overall_metrics": {
                "average_accuracy": sum(accuracy_scores) / len(accuracy_scores),
                "exact_matches": sum(match_scores),
                "samples_evaluated": len(self.results),
                "perfect_extractions": len([s for s in accuracy_scores if s == 1.0]),
                "poor_extractions": len([s for s in accuracy_scores if s < 0.5]),
            },
            "error_analysis": {
                "common_missing_conditions": self._analyze_missing_conditions(),
                "common_extra_conditions": self._analyze_extra_conditions(),
                "sample_results": self.results[:5],  # Include first 5 detailed results
            },
        }

        return report

    def _analyze_missing_conditions(self) -> List[str]:
        """Analyze commonly missed conditions"""
        missing = []
        for result in self.results:
            missing.extend(result.get("missing_conditions", []))
        return self._get_top_items(missing)

    def _analyze_extra_conditions(self) -> List[str]:
        """Analyze commonly added incorrect conditions"""
        extra = []
        for result in self.results:
            extra.extend(result.get("extra_conditions", []))
        return self._get_top_items(extra)

    def _get_top_items(self, items: List[str], n: int = 5) -> List[str]:
        """Get top n most common items from a list"""
        from collections import Counter

        if not items:
            return []
        return [item for item, _ in Counter(items).most_common(n)]

    def save_report(self, report: Dict[str, Any], output_path: str) -> None:
        """Save evaluation report to file"""
        with open(output_path, "w") as f:
            json.dump(report, f, indent=2)


def main():
    # Initialize evaluator with your saved CSV
    evaluator = PathologyEvaluator("medical_cases_with_pathologies.csv")

    # Run evaluation on a sample
    report = evaluator.evaluate_sample(sample_size=100)  # Adjust sample size as needed

    # Save report
    evaluator.save_report(report, "pathology_extraction_evaluation.json")

    # Print summary
    print("\nEvaluation Summary:")
    print(f"Average Accuracy: {report['overall_metrics']['average_accuracy']:.2%}")
    print(f"Exact Matches: {report['overall_metrics']['exact_matches']}")
    print(f"Samples Evaluated: {report['overall_metrics']['samples_evaluated']}")
    print(f"Perfect Extractions: {report['overall_metrics']['perfect_extractions']}")
    print(f"Poor Extractions: {report['overall_metrics']['poor_extractions']}")

    print("\nCommonly Missed Conditions:")
    for condition in report["error_analysis"]["common_missing_conditions"]:
        print(f"- {condition}")


if __name__ == "__main__":
    main()
