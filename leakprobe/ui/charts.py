"""Legible light-background charts over existing values; no imputation or scoring."""
import math

CHART_CONFIG = {
    'view': {'stroke': None},
    'axis': {'labelColor': '#334155', 'titleColor': '#19323c', 'labelFontSize': 11,
             'titleFontSize': 12, 'gridColor': '#e5ebef', 'domainColor': '#b7c6ce'},
    'legend': {'labelColor': '#334155', 'titleColor': '#19323c', 'labelFontSize': 11,
               'orient': 'bottom', 'columns': 2},
}


def baseline_chart_spec(frame, unit):
    values = []
    for series in frame.columns:
        segment = 0
        for hour, value in frame[series].items():
            number = float(value)
            if not math.isfinite(number):
                segment += 1
            values.append({'hour': float(hour), 'value': number if math.isfinite(number) else None,
                           'series': str(series), 'segment': f'{series}:{segment}'})
    return {
        '$schema': 'https://vega.github.io/schema/vega-lite/v5.json',
        'width': 'container', 'height': 235, 'background': '#ffffff',
        'config': CHART_CONFIG,
        'data': {'values': values},
        # Separate segments prevent the renderer joining across missing samples.
        'transform': [{'filter': 'isValid(datum.value)'}],
        'mark': {'type': 'line', 'strokeWidth': 2, 'point': {'size': 15}},
        'encoding': {
            'x': {'field': 'hour', 'type': 'quantitative', 'title': 'Elapsed hour', 'axis': {'tickMinStep': 1}},
            'y': {'field': 'value', 'type': 'quantitative', 'title': unit, 'scale': {'zero': False}},
            'color': {'field': 'series', 'type': 'nominal', 'title': None,
                      'scale': {'domain': list(frame.columns), 'range': ['#087e8b', '#687786']}},
            'detail': {'field': 'segment', 'type': 'nominal'},
            'tooltip': [{'field': 'series', 'title': 'Series'}, {'field': 'hour', 'title': 'Elapsed hour'},
                        {'field': 'value', 'title': unit, 'format': '.3f'}],
        },
    }


def rate_chart_spec(scores, field):
    return {
        '$schema': 'https://vega.github.io/schema/vega-lite/v5.json',
        'width': 'container', 'height': 235, 'background': '#ffffff', 'config': CHART_CONFIG,
        'data': {'values': [{'Variant': str(row['Variant']), 'Rate': float(row[field])}
                            for row in scores.to_dict('records')]},
        'mark': {'type': 'bar', 'color': '#087e8b', 'cornerRadiusTopLeft': 3, 'cornerRadiusTopRight': 3},
        'encoding': {
            'x': {'field': 'Variant', 'type': 'nominal', 'sort': None, 'title': None, 'axis': {'labelAngle': 0}},
            'y': {'field': 'Rate', 'type': 'quantitative', 'title': field,
                  'scale': {'domain': [0, 1]}, 'axis': {'format': '.0%'}},
            'tooltip': [{'field': 'Variant'}, {'field': 'Rate', 'title': field, 'format': '.1%'}],
        },
    }
