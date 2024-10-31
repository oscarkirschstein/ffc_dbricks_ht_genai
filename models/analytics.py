import pandas as pd
import plotly.graph_objects as go


def visualize_symptoms(df):
    if df.empty:
        return None

    # Ensure 'is_active' is of boolean type
    df['is_active'] = df['is_active'].astype(bool) # TODO: Use typing
    # Convert 'intensity' to numeric type
    df['intensity'] = pd.to_numeric(df['intensity'], errors='coerce')
    df['date'] = pd.to_datetime(df['date'])
    
    # Size of X-axis
    date_range = df['date'].agg(['min', 'max'])
    active_symptoms = df[df['is_active']].copy()

    color_scale = [
        [0, 'rgba(0,255,0,0.7)'],      # Light green with transparency
        [0.25, 'rgba(173,255,47,0.7)'], # Light yellowgreen with transparency
        [0.5, 'rgba(255,255,0,0.7)'],   # Light yellow with transparency
        [0.75, 'rgba(255,165,0,0.7)'],  # Light orange with transparency
        [1, 'rgba(255,0,0,0.7)']        # Light red with transparency
    ]

    def get_color_from_intensity(intensity):
        # Clamp intensity to be within [0, 1]
        intensity = max(0, min(intensity, 1)) #TODO: Re-scaling of intensity according to subjective perception of LLM
        
        if intensity <= 0:
            return 'rgba(0,255,0,0.35)'
        elif intensity <= 0.25:
            r = int(0 + (173-0) * (intensity/0.25))
            g = 255
            b = int(0 + (47-0) * (intensity/0.25))
            return f'rgba({r},{g},{b},0.35)'
        elif intensity <= 0.5:
            r = int(173 + (255-173) * ((intensity-0.25)/0.25))
            g = 255
            b = int(47 + (0-47) * ((intensity-0.25)/0.25))
            return f'rgba({r},{g},{b},0.35)'
        elif intensity <= 0.75:
            r = 255
            g = int(255 + (165-255) * ((intensity-0.5)/0.25))
            b = 0
            return f'rgba({r},{g},{b},0.35)'
        else:
            r = 255
            g = int(165 + (0-165) * ((intensity-0.75)/0.25))
            b = 0
            return f'rgba({r},{g},{b},0.35)'

    # Enhanced hover text with emoji indicators and reasoning.
    active_symptoms['hover_text'] = (
        '📅 Date: ' + active_symptoms['date'].dt.strftime('%Y-%m-%d') + 
        '<br>🔥 Intensity: ' + active_symptoms['intensity'].astype(str) +
        '<br>📝 raw_data: ' + active_symptoms['raw_data']
    )

    fig = go.Figure()

    # Get unique symptom positions
    unique_symptoms = active_symptoms['symptom'].unique()
    symptom_positions = {symptom: i for i, symptom in enumerate(unique_symptoms)}

    # Add traces for each symptom with enhanced styling
    for symptom in unique_symptoms:
        mask = active_symptoms['symptom'] == symptom
        symptom_data = active_symptoms[mask].sort_values('date')
        y_position = symptom_positions[symptom]
        
        # Add connecting gradient shapes with glowing effect
        for i in range(len(symptom_data)-1):
            # Get the next point in the original dataset after current point
            current_date = symptom_data['date'].iloc[i]
            next_date = symptom_data['date'].iloc[i+1]
            
            # Find any inactive points between these dates
            inactive_between = df[
                (df['symptom'] == symptom) & 
                (df['date'] > current_date) & 
                (df['date'] < next_date) & 
                (~df['is_active'])
            ]
            
            # Only add the colored boxes if there are no inactive points between
            if len(inactive_between) == 0:
                # Create multiple small rectangles to create a smooth gradient effect
                num_steps = 20  # Number of gradient steps
                start_intensity = symptom_data['intensity'].iloc[i]
                end_intensity = symptom_data['intensity'].iloc[i+1]
                
                for step in range(num_steps):
                    # Calculate the position and intensity for this step
                    x0 = current_date + (next_date - current_date) * (step/num_steps)
                    x1 = current_date + (next_date - current_date) * ((step+1)/num_steps)
                    intensity = start_intensity + (end_intensity - start_intensity) * (step/num_steps)
                    
                    
                    fig.add_shape(
                        type="rect",
                        x0=x0,
                        x1=x1,
                        y0=y_position-0.35,
                        y1=y_position+0.35,
                        fillcolor=get_color_from_intensity(intensity),
                        line=dict(width=0),
                        layer='below'
                    )
        
        fig.add_trace(
            go.Scatter(
                x=symptom_data['date'],
                y=[y_position] * len(symptom_data),
                mode='markers+lines',
                marker=dict(
                    size=25,
                    symbol='circle',
                    color=symptom_data['intensity'],
                    colorscale=color_scale,
                    showscale=True,
                    cmin=0.0,  # Set minimum of color scale
                    cmax=1.0,  # Set maximum of color scale
                    colorbar=dict(
                        title="Intensity Level",
                        titleside="right",
                        thickness=15,
                        len=0.4,
                        bgcolor='rgba(255,255,255,0.9)',
                        bordercolor='rgba(255,255,255,0.9)',
                        tickfont=dict(size=12),
                        tickmode='linear',
                        tick0=0.0,
                        dtick=0.2
                    ),
                    line=dict(color='white', width=2)
                ),
                line=dict(
                    color='rgba(153, 102, 255, 0.3)',
                    width=3
                ),
                name=symptom,
                hovertext=symptom_data['hover_text'],
                hoverinfo='text',
            )
        )

    fig.update_layout(
        title=dict(
            text="Symptom Intensity Timeline",
            font=dict(size=24, color='#2d3436'),
            x=0.5,
            y=0.95
        ),
        paper_bgcolor='rgba(240,242,245,0.95)',
        plot_bgcolor='rgba(240,242,245,0.95)',
        xaxis=dict(
            title="Timeline",
            title_font=dict(size=14),
            type='date',
            range=[date_range['min'], date_range['max']],
            showgrid=True,
            gridcolor='rgba(128,128,128,0.2)',
            linecolor='rgba(128,128,128,0.4)',
            zeroline=False
        ),
        yaxis=dict(
            title="Symptoms",
            title_font=dict(size=14),
            ticktext=list(unique_symptoms),
            tickvals=list(range(len(unique_symptoms))),
            categoryorder="array",
            categoryarray=list(unique_symptoms),
            gridcolor='rgba(128,128,128,0.2)',
            linecolor='rgba(128,128,128,0.4)',
            zeroline=False
        ),
        height=700,
        showlegend=False,
        margin=dict(l=150, r=100, t=100, b=50),
        hoverlabel=dict(
            bgcolor="white",
            font_size=12,

        )
    )

    # Add subtle grid pattern
    fig.update_xaxes(
        showgrid=True,
        gridwidth=1,
        gridcolor='rgba(128,128,128,0.1)',
        minor=dict(
            showgrid=True,
            gridwidth=0.5,
            gridcolor='rgba(128,128,128,0.05)'
        )
    )
    fig.update_yaxes(
        showgrid=True,
        gridwidth=1,
        gridcolor='rgba(128,128,128,0.1)'
    )

    return fig