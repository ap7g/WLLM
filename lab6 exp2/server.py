"""Expt 2 - Weather Data MCP Server.
Exposes get_current_weather(location), fetching live data from wttr.in (free, no key).
"""
import httpx
from mcp.server.mcpserver import MCPServer

mcp = MCPServer("weather-server")


@mcp.tool()
def get_current_weather(location: str) -> str:
    """Get the current weather and 3-day forecast for a city. Pass city and country, e.g. "Tokyo, Japan"."""
    try:
        r = httpx.get(f"https://wttr.in/{location}", params={"format": "j1"}, timeout=15)
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        return f"Error fetching weather for {location}: {e}"

    now = data["current_condition"][0]
    area = data["nearest_area"][0]
    place = f"{area['areaName'][0]['value']}, {area['country'][0]['value']}"

    lines = [
        f"Location: {place}",
        f"Condition: {now['weatherDesc'][0]['value']}",
        f"Temperature: {now['temp_C']} C (feels like {now['FeelsLikeC']} C)",
        f"Humidity: {now['humidity']}%",
        f"Wind: {now['windspeedKmph']} km/h {now['winddir16Point']}",
        f"Observed at: {now.get('localObsDateTime', now.get('observation_time', 'n/a'))}",
        "Forecast:",
    ]
    for day in data["weather"]:
        desc = day["hourly"][4]["weatherDesc"][0]["value"]  # around midday
        lines.append(f"  {day['date']}: {day['mintempC']}-{day['maxtempC']} C, {desc}")
    return "\n".join(lines)


if __name__ == "__main__":
    mcp.run()  # stdio transport
