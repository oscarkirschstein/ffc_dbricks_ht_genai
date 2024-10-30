import pandas as pd
import plotly.graph_objects as go
from typing import List, Dict, Any
from groq import Groq
import pdfkit
import markdown2
import tempfile
import os
from datetime import datetime

# Synthetic data
MOCK_DATA: List[Dict[str, Any]] = [
    {
        "symptom": "leg pain",
        "date": "2024-10-01",
        "is_active": True,
        "intensity": 0.9,
        "reason": "Patient reports severe leg pain, difficulty walking",
    },
    {
        "symptom": "leg pain",
        "date": "2024-10-02",
        "is_active": True,
        "intensity": 0.7,
        "reason": "Leg pain continues but slightly improved with prescribed medication",
    },
    {
        "symptom": "leg pain",
        "date": "2024-10-03",
        "is_active": True,
        "intensity": 0.5,
        "reason": "Moderate leg pain, patient able to walk short distances",
    },
    {
        "symptom": "leg pain",
        "date": "2024-10-04",
        "is_active": False,
        "intensity": 0.0,
        "reason": "No leg pain reported today",
    },
    {
        "symptom": "leg pain",
        "date": "2024-10-05",
        "is_active": False,
        "intensity": 0.0,
        "reason": "Patient remains pain free",
    },
    {
        "symptom": "leg pain",
        "date": "2024-10-06",
        "is_active": False,
        "intensity": 0.0,
        "reason": "No leg pain symptoms",
    },
    {
        "symptom": "leg pain",
        "date": "2024-10-07",
        "is_active": True,
        "intensity": 0.6,
        "reason": "Leg pain has returned, moderate intensity",
    },
    {
        "symptom": "leg pain",
        "date": "2024-10-08",
        "is_active": True,
        "intensity": 0.8,
        "reason": "Significant increase in leg pain, limiting mobility",
    },
    {
        "symptom": "leg pain",
        "date": "2024-10-09",
        "is_active": True,
        "intensity": 0.7,
        "reason": "Leg pain remains high but slightly improved from yesterday",
    },
    {
        "symptom": "leg pain",
        "date": "2024-10-10",
        "is_active": False,
        "intensity": 0.0,
        "reason": "Pain has subsided completely",
    },
    {
        "symptom": "leg pain",
        "date": "2024-10-11",
        "is_active": False,
        "intensity": 0.0,
        "reason": "No pain reported",
    },
    {
        "symptom": "leg pain",
        "date": "2024-10-12",
        "is_active": True,
        "intensity": 0.4,
        "reason": "Mild leg pain has returned",
    },
    {
        "symptom": "leg pain",
        "date": "2024-10-13",
        "is_active": True,
        "intensity": 0.3,
        "reason": "Minimal leg pain, well controlled",
    },
    {
        "symptom": "leg pain",
        "date": "2024-10-14",
        "is_active": True,
        "intensity": 0.2,
        "reason": "Very mild leg pain, continuing to improve",
    },
    {
        "symptom": "sleep disturbance",
        "date": "2024-10-15",
        "is_active": True,
        "intensity": 0.5,
        "reason": "Patient reports moderate difficulty falling asleep",
    },
    {
        "symptom": "sleep disturbance",
        "date": "2024-10-16",
        "is_active": True,
        "intensity": 0.6,
        "reason": "Sleep issues worsening, waking up multiple times",
    },
    {
        "symptom": "sleep disturbance",
        "date": "2024-10-17",
        "is_active": True,
        "intensity": 0.7,
        "reason": "Significant sleep disruption, affecting daytime function",
    },
    {
        "symptom": "sleep disturbance",
        "date": "2024-10-18",
        "is_active": True,
        "intensity": 0.8,
        "reason": "Severe insomnia, only getting 2-3 hours of sleep",
    },
    {
        "symptom": "sleep disturbance",
        "date": "2024-10-19",
        "is_active": True,
        "intensity": 0.7,
        "reason": "Sleep slightly improved but still significantly disturbed",
    },
    {
        "symptom": "sleep disturbance",
        "date": "2024-10-20",
        "is_active": True,
        "intensity": 0.6,
        "reason": "Moderate sleep issues, medication helping somewhat",
    },
    {
        "symptom": "sleep disturbance",
        "date": "2024-10-21",
        "is_active": True,
        "intensity": 0.5,
        "reason": "Sleep quality improving with treatment",
    },
    {
        "symptom": "sleep disturbance",
        "date": "2024-10-22",
        "is_active": True,
        "intensity": 0.4,
        "reason": "Mild sleep disturbance, getting better rest",
    },
    {
        "symptom": "sleep disturbance",
        "date": "2024-10-23",
        "is_active": True,
        "intensity": 0.3,
        "reason": "Minor sleep issues, mostly resolved",
    },
    {
        "symptom": "sleep disturbance",
        "date": "2024-10-24",
        "is_active": False,
        "intensity": 0.0,
        "reason": "Sleep has returned to normal",
    },
    {
        "symptom": "nerve pain",
        "date": "2024-10-20",
        "is_active": True,
        "intensity": 0.3,
        "reason": "Patient reports new onset of tingling sensation",
    },
    {
        "symptom": "nerve pain",
        "date": "2024-10-21",
        "is_active": True,
        "intensity": 0.4,
        "reason": "Nerve pain increasing, spreading to larger area",
    },
    {
        "symptom": "nerve pain",
        "date": "2024-10-22",
        "is_active": True,
        "intensity": 0.5,
        "reason": "Moderate nerve pain with occasional sharp sensations",
    },
    {
        "symptom": "nerve pain",
        "date": "2024-10-23",
        "is_active": True,
        "intensity": 0.7,
        "reason": "Severe nerve pain, significantly affecting daily activities",
    },
    {
        "symptom": "nerve pain",
        "date": "2024-10-27",
        "is_active": False,
        "intensity": 0.0,
        "reason": "Nerve pain has resolved completely",
    },
]


def get_patient_data(patient_id: int) -> List[Dict[str, Any]]:
    """In a real application, this would fetch data from a database.
    For now, returns mock data."""
    return MOCK_DATA


def preprocess_data(data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Preprocess and structure the data for analysis"""
    df = pd.DataFrame(data)
    df["date"] = pd.to_datetime(df["date"])

    processed_data = {
        "time_period": f"{df['date'].min().strftime('%Y-%m-%d')} to {df['date'].max().strftime('%Y-%m-%d')}",
        "symptoms": list(df["symptom"].unique()),
        "measurements": [],
        "temporal_markers": [],
    }

    # Process each symptom
    for symptom in processed_data["symptoms"]:
        symptom_data = df[df["symptom"] == symptom]

        # Calculate key metrics
        max_intensity = symptom_data["intensity"].max()
        avg_intensity = symptom_data["intensity"].mean()
        active_days = symptom_data["is_active"].sum()
        total_days = len(symptom_data)

        processed_data["measurements"].append(
            {
                "symptom": symptom,
                "max_intensity": max_intensity,
                "avg_intensity": avg_intensity,
                "active_days": active_days,
                "total_days": total_days,
                "activity_rate": active_days / total_days,
            }
        )

        # Find significant changes
        intensity_changes = symptom_data["intensity"].diff()
        significant_changes = symptom_data[abs(intensity_changes) > 0.3]

        for _, change in significant_changes.iterrows():
            processed_data["temporal_markers"].append(
                {
                    "date": change["date"].strftime("%Y-%m-%d"),
                    "symptom": symptom,
                    "change": change["intensity"]
                    - (change["intensity"] - intensity_changes[change.name]),
                    "description": change["reason"],
                }
            )

    return processed_data


def generate_llm_insights(processed_data: Dict[str, Any]) -> Dict[str, str]:
    """Generate insights using LLM"""
    client = Groq(api_key="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")

    # Context Layer
    context = f"""You are a medical professional analyzing patient symptom data over the period {processed_data['time_period']}.
    The key symptoms being tracked are: {', '.join(processed_data['symptoms'])}.
    Normal intensity ranges are 0 (none) to 1 (severe)."""

    # Analysis Layer
    measurements_text = "\n".join(
        [
            f"- {m['symptom']}: max intensity {m['max_intensity']:.1f}, average {m['avg_intensity']:.1f}, "
            f"active {m['active_days']}/{m['total_days']} days"
            for m in processed_data["measurements"]
        ]
    )

    temporal_markers_text = "\n".join(
        [
            f"- {m['date']}: {m['symptom']} changed by {m['change']:.1f} ({m['description']})"
            for m in processed_data["temporal_markers"]
        ]
    )

    analysis_prompt = f"""{context}

Based on these measurements:
{measurements_text}

And these significant changes:
{temporal_markers_text}

Please provide:
1. Trend analysis for each symptom
2. Identification of any concerning patterns
3. Correlations between different symptoms
4. Comparison to typical severity ranges"""

    # Summary Layer
    summary_prompt = """Based on your analysis, provide:
1. A concise summary of the patient's health trajectory
2. Key areas of improvement or concern
3. Suggested focus areas for future visits
Use medical terminology but explain key terms."""

    # Generate insights
    analysis_response = client.chat.completions.create(
        messages=[{"role": "user", "content": analysis_prompt}],
        model="llama-3.1-70b-versatile",
    )

    summary_response = client.chat.completions.create(
        messages=[{"role": "user", "content": summary_prompt}],
        model="llama-3.1-70b-versatile",
    )

    return {
        "analysis": analysis_response.choices[0].message.content,
        "summary": summary_response.choices[0].message.content,
    }


def create_symptom_timeline(df: pd.DataFrame) -> go.Figure:
    """Create a timeline visualization of symptoms"""
    fig = go.Figure()

    # Get unique symptoms
    symptoms = df["symptom"].unique()
    colors = ["#1f77b4", "#ff7f0e", "#2ca02c"]  # Add more colors if needed

    for idx, symptom in enumerate(symptoms):
        symptom_data = df[df["symptom"] == symptom]

        # Add intensity line
        fig.add_trace(
            go.Scatter(
                x=symptom_data["date"],
                y=symptom_data["intensity"],
                name=f"{symptom} (intensity)",
                line=dict(color=colors[idx % len(colors)]),
                hovertemplate="<br>".join(
                    [
                        "Date: %{x}",
                        "Intensity: %{y:.1f}",
                        "Status: %{text}",
                    ]
                ),
                text=symptom_data["reason"],
            )
        )

    fig.update_layout(
        title="Symptom Timeline",
        xaxis_title="Date",
        yaxis_title="Intensity",
        hovermode="x unified",
        showlegend=True,
    )

    return fig


def generate_report(patient_id: int) -> Dict[str, Any]:
    """Generate a comprehensive patient report"""
    try:
        # Get patient data
        data = get_patient_data(patient_id)

        # Preprocess data
        processed_data = preprocess_data(data)

        # Generate LLM insights
        insights = generate_llm_insights(processed_data)

        # Create visualization
        df = pd.DataFrame(data)
        df["date"] = pd.to_datetime(df["date"])
        timeline_plot = create_symptom_timeline(df)

        # Compile report
        report = {
            "patient_id": patient_id,
            "time_period": processed_data["time_period"],
            "plot": timeline_plot,
            "analysis": insights["analysis"],
            "summary": insights["summary"],
            "data_quality": {
                "total_measurements": len(data),
                "symptoms_tracked": len(processed_data["symptoms"]),
                "significant_changes": len(processed_data["temporal_markers"]),
            },
        }

        return report

    except Exception as e:
        raise Exception(f"Error generating report: {str(e)}")


def generate_pdf_report(
    markdown_content: str, patient_id: int, plot_figure: go.Figure = None
) -> str:
    """Generate a PDF file from the markdown report and plot"""

    # Save plot as a temporary HTML file
    plot_html = ""
    if plot_figure:
        temp_plot_path = os.path.join(
            tempfile.gettempdir(),
            f"plot_{patient_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html",
        )
        plot_figure.write_html(temp_plot_path, include_plotlyjs="cdn", full_html=False)
        with open(temp_plot_path, "r") as f:
            plot_html = f.read()
        os.remove(temp_plot_path)  # Clean up temp file

    # Convert markdown to HTML
    html_content = markdown2.markdown(
        markdown_content, extras=["tables", "break-on-newline"]
    )

    styled_html = f"""
    <html>
        <head>
            <meta charset="UTF-8">
            <style>
                @import url('https://fonts.googleapis.com/css2?family=Noto+Color+Emoji&family=Roboto:wght@300;400;500;700&display=swap');
                
                body {{
                    font-family: 'Roboto', 'Noto Color Emoji', sans-serif;
                    line-height: 1.6;
                    margin: 40px;
                    color: #2c3e50;
                    -webkit-font-smoothing: antialiased;
                }}
                
                /* Header Styling */
                h1 {{
                    font-size: 28px;
                    font-weight: 700;
                    text-align: center;
                    color: #1a237e;
                    margin: 30px 0;
                    padding-bottom: 10px;
                    border-bottom: 2px solid #1a237e;
                }}
                
                h2 {{
                    font-size: 22px;
                    font-weight: 500;
                    color: #283593;
                    margin-top: 25px;
                    padding: 10px 0;
                    border-bottom: 1px solid #e0e0e0;
                }}
                
                h3 {{
                    font-size: 18px;
                    font-weight: 500;
                    color: #3949ab;
                    margin-top: 20px;
                }}

                /* Emoji Styling */
                .emoji {{
                    font-family: 'Noto Color Emoji', sans-serif;
                    font-size: 1.2em;
                    vertical-align: middle;
                    margin: 0 5px;
                }}
                
                /* Table Styling */
                table {{
                    width: 100%;
                    border-collapse: collapse;
                    margin: 25px 0;
                    box-shadow: 0 1px 3px rgba(0,0,0,0.1);
                }}
                
                th {{
                    background-color: #f5f7ff;
                    color: #1a237e;
                    font-weight: 500;
                    text-align: left;
                    padding: 12px;
                    border: 1px solid #e0e0e0;
                }}
                
                td {{
                    padding: 12px;
                    border: 1px solid #e0e0e0;
                    background-color: white;
                }}
                
                tr:nth-child(even) td {{
                    background-color: #fafbff;
                }}

                /* Content Sections */
                .section {{
                    margin: 30px 0;
                    padding: 20px;
                    background-color: white;
                    border-radius: 8px;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.05);
                }}
                
                /* Important Notes Section */
                .notes {{
                    background-color: #fff8e1;
                    border-left: 4px solid #ffa000;
                    padding: 15px 20px;
                    margin: 25px 0;
                    border-radius: 0 8px 8px 0;
                }}
                
                .notes ul {{
                    margin: 10px 0;
                    padding-left: 20px;
                }}
                
                .notes li {{
                    margin: 8px 0;
                    color: #424242;
                }}

                /* Footer */
                .footer {{
                    margin-top: 50px;
                    text-align: center;
                    color: #757575;
                    font-size: 0.9em;
                    padding-top: 20px;
                    border-top: 1px solid #e0e0e0;
                }}

                /* Horizontal Rule */
                hr {{
                    border: 0;
                    height: 1px;
                    background: linear-gradient(to right, transparent, #e0e0e0, transparent);
                    margin: 30px 0;
                }}

                /* Analysis Section */
                .analysis {{
                    line-height: 1.8;
                    text-align: justify;
                }}

                /* Summary Section */
                .summary {{
                    background-color: #e8f5e9;
                    padding: 20px;
                    border-radius: 8px;
                    margin: 25px 0;
                }}

                /* Add styling for the plot container */
                .plot-container {{
                    width: 100%;
                    margin: 20px 0;
                    padding: 20px;
                    background: white;
                    border-radius: 8px;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.05);
                }}
            </style>
        </head>
        <body>
            <div class="section">
                {html_content.replace('🏥', '<span class="emoji">🏥</span>')
                            .replace('📊', '<span class="emoji">📊</span>')
                            .replace('📈', '<span class="emoji">📈</span>')
                            .replace('💡', '<span class="emoji">💡</span>')
                            .replace('⚠️', '<span class="emoji">⚠️</span>')
                            .replace('<h2>Analysis', '<div class="plot-container">{plot_html}</div><h2 class="analysis">Analysis')
                            .replace('<h2>Clinical Summary', '<h2 class="summary">Clinical Summary')
                            .replace('<h2>Important Notes', '<div class="notes"><h2>Important Notes')
                            .replace('## Important Notes</h2>', '## Important Notes</h2></div>')
                            .replace('<hr>', '<hr class="gradient-hr">')}
            </div>
        </body>
    </html>
    """

    # Create temporary file
    temp_dir = tempfile.gettempdir()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    pdf_path = os.path.join(temp_dir, f"patient_{patient_id}_report_{timestamp}.pdf")

    # Convert HTML to PDF with additional options
    options = {
        "page-size": "A4",
        "margin-top": "20mm",
        "margin-right": "20mm",
        "margin-bottom": "20mm",
        "margin-left": "20mm",
        "encoding": "UTF-8",
        "no-outline": None,
        "enable-local-file-access": None,
        "disable-smart-shrinking": None,
        "javascript-delay": "2000",  # Increased delay to ensure plot renders
        "enable-javascript": None,
        "custom-header": [("Accept-Encoding", "gzip")],
        "no-stop-slow-scripts": None,
        "debug-javascript": None,
    }

    pdfkit.from_string(styled_html, pdf_path, options=options)

    return pdf_path
