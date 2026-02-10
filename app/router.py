def route_channel(category: str) -> str:
    return {
        "bug": "#support-bugs",
        "feature_request": "#support-features",
        "billing": "#support-billing",
        "technical_question": "#support-tech"
    }.get(category, "#support-general")
