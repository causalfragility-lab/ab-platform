import requests
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import webbrowser, os

data = requests.get("http://localhost:8000/results/exp_demo_001").json()

ctrl  = data["control"]
trt   = data["treatment"]
trends = data["daily_trends"]

dates     = [d["date"] for d in trends]
ctrl_cvr  = [round(d["control"]   * 100, 2) for d in trends]
trt_cvr   = [round(d["treatment"] * 100, 2) for d in trends]

fig = make_subplots(
    rows=2, cols=2,
    subplot_titles=(
        "Conversion rate by variant",
        "95% Confidence interval",
        "Daily CVR trend",
        "Lift & significance"
    ),
    specs=[[{"type": "bar"}, {"type": "scatter"}],
           [{"type": "scatter", "colspan": 2}, None]],
    vertical_spacing=0.18,
    horizontal_spacing=0.12,
)

fig.add_trace(go.Bar(
    x=["Control", "Treatment"],
    y=[round(ctrl["mean"]*100,2), round(trt["mean"]*100,2)],
    marker_color=["#888780", "#185FA5"],
    text=[f"{ctrl['mean']*100:.2f}%", f"{trt['mean']*100:.2f}%"],
    textposition="outside",
    width=0.4,
    name="CVR",
    showlegend=False,
), row=1, col=1)

ci_lower = data["ci_lower"] * 100
ci_upper = data["ci_upper"] * 100
lift_abs = data["lift_absolute"] * 100

fig.add_trace(go.Scatter(
    x=[ci_lower, lift_abs, ci_upper],
    y=[0, 0, 0],
    mode="markers+lines",
    marker=dict(size=[8, 14, 8], color=["#B5D4F4", "#185FA5", "#B5D4F4"]),
    line=dict(color="#B5D4F4", width=6),
    name="95% CI",
    showlegend=False,
    hovertemplate="<b>%{x:.2f} pp</b><extra></extra>",
), row=1, col=2)

fig.add_shape(type="line", x0=0, x1=0, y0=-0.3, y1=0.3,
              line=dict(color="#ccc", width=1, dash="dash"), row=1, col=2)

fig.add_trace(go.Scatter(
    x=dates, y=ctrl_cvr,
    mode="lines+markers",
    name="Control",
    line=dict(color="#888780", width=2),
    marker=dict(size=5),
    hovertemplate="%{x}<br>Control: %{y:.1f}%<extra></extra>",
), row=2, col=1)

fig.add_trace(go.Scatter(
    x=dates, y=trt_cvr,
    mode="lines+markers",
    name="Treatment",
    line=dict(color="#185FA5", width=2),
    marker=dict(size=5),
    hovertemplate="%{x}<br>Treatment: %{y:.1f}%<extra></extra>",
), row=2, col=1)

sig = data["statistically_significant"]
prac = data["practically_significant"]

fig.update_layout(
    title=dict(
        text=f"<b>{data['experiment_name']}</b><br>"
             f"<span style='font-size:13px;color:gray;'>"
             f"Lift: +{data['lift_relative']*100:.1f}%  |  "
             f"p-value: {data['p_value']:.3f}  |  "
             f"Statistically significant: {'Yes' if sig else 'No'}  |  "
             f"Practically significant: {'Yes' if prac else 'No'}"
             f"</span>",
        font=dict(size=16),
    ),
    height=700,
    template="plotly_white",
    font=dict(family="Arial, sans-serif", size=12),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    annotations=[
        dict(
            text=f"SRM: {'Detected' if data['sample_ratio_mismatch'] else 'None'}  |  "
                 f"SRM p={data['srm_p_value']:.3f}  |  "
                 f"n(control)={ctrl['n']}  n(treatment)={trt['n']}",
            xref="paper", yref="paper", x=0.5, y=-0.06,
            showarrow=False, font=dict(size=11, color="gray"), xanchor="center"
        )
    ]
)

fig.update_yaxes(title_text="CVR (%)", row=1, col=1)
fig.update_yaxes(tickvals=[], row=1, col=2)
fig.update_xaxes(title_text="Difference in CVR (percentage points)", row=1, col=2)
fig.update_yaxes(title_text="CVR (%)", row=2, col=1)
fig.update_xaxes(tickangle=45, row=2, col=1)

output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ab_dashboard_interactive.html")
fig.write_html(output_path, include_plotlyjs="cdn")
print(f"Dashboard saved to: {output_path}")
webbrowser.open(f"file:///{output_path}")
