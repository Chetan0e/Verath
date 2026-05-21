_PRIVATE_MODES: dict[str, bool] = {}


def toggle_privacy(user_id: str):
    current_state = _PRIVATE_MODES.get(user_id, False)
    new_state = not current_state
    _PRIVATE_MODES[user_id] = new_state
    return new_state


def is_private(user_id: str):
    return _PRIVATE_MODES.get(user_id, False)
