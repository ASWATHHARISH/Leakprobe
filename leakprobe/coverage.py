"""Coverage checks for the one supported Net3 sensor layout."""

from collections.abc import Iterable, Mapping

from .paths import FULL_FLOW_CHANNELS, FULL_PRESSURE_CHANNELS


def validate_full_channel_coverage(metadata: Mapping, columns: Iterable[str], context="dataset") -> None:
    """Reject data unless it contains every Net3 junction pressure and pipe flow."""
    pressure_nodes = metadata.get("monitor_pressure_nodes", [])
    flow_pipes = metadata.get("flow_sensors", [])
    if len(pressure_nodes) != FULL_PRESSURE_CHANNELS:
        raise ValueError(
            f"{context} must define exactly {FULL_PRESSURE_CHANNELS} pressure channels; "
            f"found {len(pressure_nodes)}."
        )
    if len(flow_pipes) != FULL_FLOW_CHANNELS:
        raise ValueError(
            f"{context} must define exactly {FULL_FLOW_CHANNELS} flow channels; "
            f"found {len(flow_pipes)}."
        )

    actual = set(columns)
    expected_pressure = {f"pressure_{node}_m" for node in pressure_nodes}
    expected_flow = {f"flow_{pipe}_lps" for pipe in flow_pipes}
    actual_pressure = {column for column in actual if column.startswith("pressure_")}
    actual_flow = {column for column in actual if column.startswith("flow_")}
    if actual_pressure != expected_pressure:
        missing = len(expected_pressure - actual_pressure)
        extra = len(actual_pressure - expected_pressure)
        raise ValueError(
            f"{context} must contain all {FULL_PRESSURE_CHANNELS} pressure columns "
            f"and no extras (missing {missing}, extra {extra})."
        )
    if actual_flow != expected_flow:
        missing = len(expected_flow - actual_flow)
        extra = len(actual_flow - expected_flow)
        raise ValueError(
            f"{context} must contain all {FULL_FLOW_CHANNELS} flow columns "
            f"and no extras (missing {missing}, extra {extra})."
        )
