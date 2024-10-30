import pandas as pd
from datetime import datetime


def process_features_to_symptoms(features):
    """Convert features JSON to symptom timeline data"""
    symptoms_data = []

    # Extract symptoms from features
    if "features" in features and "symptoms" in features["features"]:
        symptoms = features["features"]["symptoms"]
        current_date = datetime.now().strftime(
            "%Y-%m-%d"
        )  # Use current date as reference

        for symptom_name, symptom_info in symptoms.items():
            symptoms_data.append(
                {
                    "symptom": symptom_name,
                    "date": current_date,
                    "is_active": symptom_info.get("is_active", "True") == "True",
                    "intensity": float(symptom_info.get("intensity", -1)) / 10
                    if symptom_info.get("intensity", -1) != -1
                    else 0.5,
                    "reason": symptom_info.get(
                        "description", "No description provided"
                    ),
                }
            )

    return symptoms_data


def generate_report(patient_id, features_data=None):
    """Generate a visual report for the patient's symptoms"""
    try:
        if features_data is None or not isinstance(features_data, dict):
            return "No valid data available for report generation"

        # Convert features to symptom timeline data
        data = process_features_to_symptoms(features_data)

        if not data:
            return "No symptom data available for visualization"

        # Create DataFrame
        df = pd.DataFrame(data)
        df["date"] = pd.to_datetime(df["date"])

        # Rest of your visualization code...
        # [Include all the visualization code from test.ipynb here]

        return fig

    except Exception as e:
        return f"Error generating report: {str(e)}"
