PRIVATE_MODE = False


def toggle_privacy():
    global PRIVATE_MODE
    PRIVATE_MODE = not PRIVATE_MODE
    return PRIVATE_MODE


def is_private():
    return PRIVATE_MODE
